"""
V2 Preview Blueprint — internal, not linked from public navigation.
Mount point: /v2/

All routes in this module are part of the "next version" preview batch.
Nothing here is visible to users of the current shared preview.

Authentication (WS5)
--------------------
All V2 routes are protected by @require_auth.  Unauthenticated requests
are redirected to GET /v2/login.

Login flow (when CLERK_PUBLISHABLE_KEY is configured):
  1. User visits /v2/login — Clerk JS mounts the sign-in component.
  2. After sign-in, JS POSTs the short-lived session token to
     POST /v2/auth/verify (CSRF-exempt, protected by Clerk JWT).
  3. Flask verifies the JWT via Clerk's JWKS endpoint, creates/retrieves
     the DB user, and sets a HMAC-signed Flask session.
  4. JS redirects the browser to /v2/.

Demo login (non-production only):
  GET /v2/demo-login — sets a fixed demo user session, no Clerk required.

User data isolation (WS5)
-------------------------
Every bank connection, transaction set, and seeded demo data record is
scoped to the authenticated g.user_id.  Routes that receive a
consent_token from the client verify it belongs to the session user
before taking any action — unauthenticated or wrong-user requests
receive 403, never the other user's data.

Yapily callback URL
-------------------
Set CANONICAL_BASE_URL (e.g. "https://yourrepl.replit.dev") in secrets
to produce a stable, trusted callback URL.  When absent the request's
host is used (acceptable for local dev; must be configured before live
bank consent is tested).
"""

import logging
import os
from decimal import Decimal, InvalidOperation
from flask import (
    Blueprint, abort, g, jsonify, redirect, render_template,
    request, session, url_for,
)

from reserved.auth import (
    DEMO_CLERK_ID, DEMO_DISPLAY, DEMO_EMAIL,
    clear_user_session, is_production_environment, require_auth,
    set_user_session, verify_clerk_session_token,
)
from reserved.database import (
    get_account,
    get_connection_by_token,
    get_invoice_counts_for_user,
    get_matches_for_invoice,
    get_or_create_user,
    get_transactions,
    get_transaction_summary,
    get_user_review_items,
    list_connections_for_user,
    list_accounts,
    list_invoices,
    list_invoices_with_best_match,
    migrate_session_to_user,
    persist_match_result,
)
from reserved.extensions import csrf
from reserved.matching.engine import MatchingEngine
from reserved.providers.banking.classifier import TransactionCategory
from reserved.providers.banking.ingestion import (
    get_demo_transactions,
    seed_demo_data,
    summarise,
)
from reserved.providers.banking.yapily import YapilyClient
from reserved.services.dashboard import build_dashboard, DEFAULT_PROFILE
from reserved.tax_year_context import UnsupportedTaxYear, configured_tax_year, resolve_tax_year

log = logging.getLogger(__name__)

v2 = Blueprint("v2", __name__, url_prefix="/v2")

# ── Illustrative UK bank roster ───────────────────────────────────────────────

FEATURED_BANKS = [
    {"id": "monzo",        "name": "Monzo",       "colour": "#FF3464", "text": "#fff"},
    {"id": "starling",     "name": "Starling",    "colour": "#7DD7C1", "text": "#1a4843"},
    {"id": "revolut",      "name": "Revolut",     "colour": "#0666EB", "text": "#fff"},
    {"id": "barclays",     "name": "Barclays",    "colour": "#00395D", "text": "#fff"},
    {"id": "hsbc",         "name": "HSBC",        "colour": "#DB0011", "text": "#fff"},
    {"id": "lloyds",       "name": "Lloyds",      "colour": "#006A4D", "text": "#fff"},
    {"id": "natwest",      "name": "NatWest",     "colour": "#42145f", "text": "#fff"},
    {"id": "santander",    "name": "Santander",   "colour": "#EC0000", "text": "#fff"},
    {"id": "chase",        "name": "Chase",       "colour": "#0171B6", "text": "#fff"},
    {"id": "wise",         "name": "Wise",        "colour": "#9FE870", "text": "#163b0a"},
    {"id": "first-direct", "name": "first direct","colour": "#1D1D1B", "text": "#fff"},
    {"id": "halifax",      "name": "Halifax",     "colour": "#0057A8", "text": "#fff"},
]

ALL_BANKS = FEATURED_BANKS + [
    {"id": "metro",      "name": "Metro Bank",   "colour": "#e0001a", "text": "#fff"},
    {"id": "tsb",        "name": "TSB",          "colour": "#005BAA", "text": "#fff"},
    {"id": "co-op",      "name": "Co-operative", "colour": "#006030", "text": "#fff"},
    {"id": "virgin",     "name": "Virgin Money", "colour": "#E10A0A", "text": "#fff"},
    {"id": "nationwide", "name": "Nationwide",   "colour": "#0070AC", "text": "#fff"},
    {"id": "tide",       "name": "Tide",         "colour": "#F5A623", "text": "#2a1a00"},
    {"id": "anna",       "name": "ANNA",         "colour": "#F0E6FF", "text": "#6930c3"},
    {"id": "atom",       "name": "Atom Bank",    "colour": "#3D1152", "text": "#fff"},
    {"id": "aldermore",  "name": "Aldermore",    "colour": "#E4003B", "text": "#fff"},
    {"id": "clydesdale", "name": "Clydesdale",   "colour": "#006DB7", "text": "#fff"},
]


def _connections_ctx(state: str) -> dict:
    return {"featured_banks": FEATURED_BANKS, "all_banks": ALL_BANKS, "state": state}


def _yapily_callback_url() -> str:
    """
    Build a trusted callback URL for Yapily's Hosted Pages consent flow.

    Prefers the CANONICAL_BASE_URL environment variable so the URL is stable
    and not derived from the HTTP Host header (which can be spoofed in certain
    configurations).  Falls back to the request's host_url in development.

    Configure CANONICAL_BASE_URL (e.g. "https://yourrepl.replit.dev") in
    Replit Secrets before testing live bank consent flows.
    """
    canonical = os.environ.get("CANONICAL_BASE_URL", "").rstrip("/")
    if canonical:
        return canonical + url_for("v2.yapily_callback")
    # Development fallback — acceptable because Yapily sandbox is also sandboxed.
    log.warning(
        "CANONICAL_BASE_URL not set; deriving Yapily callback from request host. "
        "Set this secret before testing live bank connections."
    )
    return url_for("v2.yapily_callback", _external=True)


def _require_own_connection(consent_token: str) -> dict:
    """
    Look up a bank connection by consent token and verify it belongs to the
    current session user.

    Returns the connection row dict on success.
    Aborts with 403 if the token is not found or belongs to another user.
    Never reveals whether the token exists.
    """
    if not consent_token:
        abort(403)
    row = get_connection_by_token(consent_token)
    if not row or row.get("user_id") != g.user_id:
        abort(403)
    return row


# ── Auth routes ───────────────────────────────────────────────────────────────

@v2.get("/login")
def login():
    """
    Show the V2 login page.

    If the user is already authenticated, redirect to /v2/.
    The page embeds @clerk/clerk-js when CLERK_PUBLISHABLE_KEY is set,
    and shows the demo login button only in non-production environments.
    Uses the same is_production_environment() dual-lock as the demo-login
    route itself, so the button is visible if and only if the route works.
    """
    from reserved.auth import is_authenticated
    if is_authenticated():
        return redirect(url_for("v2.index"))

    clerk_key = os.environ.get("CLERK_PUBLISHABLE_KEY", "")
    demo_available = not is_production_environment()

    return render_template(
        "v2/login.html",
        clerk_publishable_key=clerk_key,
        clerk_js_version="6.25.12",
        demo_available=demo_available,
    )


@v2.post("/auth/verify")
@csrf.exempt
def auth_verify():
    """
    Exchange a Clerk short-lived session token for a Flask session.

    Called by the Clerk JS SDK after a successful sign-in.  CSRF protection
    is disabled for this endpoint because it is protected by Clerk JWT
    verification instead.

    Request body (JSON): { "token": "<clerk-session-jwt>" }
    Response (JSON):     { "ok": true } or { "ok": false, "error": "..." }
    """
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()

    if not token:
        return jsonify({"ok": False, "error": "token is required"}), 400

    claims = verify_clerk_session_token(token)
    if not claims:
        return jsonify({
            "ok": False,
            "error": "Invalid or expired token. Please sign in again.",
        }), 401

    clerk_user_id = claims.get("sub", "")
    if not clerk_user_id:
        return jsonify({"ok": False, "error": "Token missing user ID."}), 401

    email        = claims.get("email")
    first_name   = claims.get("first_name") or claims.get("given_name") or ""
    last_name    = claims.get("last_name") or claims.get("family_name") or ""
    display_name = " ".join(filter(None, [first_name, last_name])) or email or clerk_user_id

    try:
        user_id = get_or_create_user(
            clerk_user_id=clerk_user_id,
            email=email,
            display_name=display_name,
        )
    except Exception:
        return jsonify({"ok": False, "error": "Account lookup failed."}), 500

    # Save anything useful before clearing the pre-login session.
    prior_session_key = session.get("_legacy_session_key")

    # Session fixation prevention: wipe the entire pre-login session state
    # before writing authenticated identity so an attacker cannot fix the
    # session cookie before the user signs in.
    session.clear()
    session.modified = True

    # Migrate any legacy session_key-keyed data to this user's account.
    if prior_session_key:
        migrate_session_to_user(prior_session_key, user_id)

    set_user_session(
        user_id=user_id,
        clerk_id=clerk_user_id,
        email=email,
        display_name=display_name,
        is_demo=False,
    )
    return jsonify({"ok": True})


@v2.get("/demo-login")
def demo_login():
    """
    Set a demo user session without going through Clerk.

    Each browser session gets its own isolated demo user (keyed by a UUID
    stored in the Flask session cookie).  Returning to this route in the
    same browser reuses the same demo user and its data.  A second browser
    or incognito window generates a distinct UUID → distinct user → fully
    isolated data.  This resolves the contradiction between "same fixed user"
    and "isolated across browsers" in earlier handover notes.

    Availability dual-lock:
      1. FLASK_ENV must not be 'production' (explicit environment check)
      2. CLERK_PUBLISHABLE_KEY must not be a live key (pk_live_…) — once
         real auth is configured for live use, demo login is automatically
         blocked even if FLASK_ENV is misconfigured.
    """
    import secrets as _secrets

    if is_production_environment():
        abort(403)

    # Retrieve or generate a per-browser demo session identifier.
    # Stored in the Flask session so the same browser always gets the same
    # demo user, but a fresh browser (no cookie) gets a new UUID → new user.
    from reserved.auth import _SK_DEMO_SESSION_ID, DEMO_CLERK_ID_PREFIX, DEMO_EMAIL_DOMAIN, DEMO_DISPLAY
    demo_session_id = session.get(_SK_DEMO_SESSION_ID)
    if not demo_session_id:
        demo_session_id = _secrets.token_urlsafe(16)

    demo_clerk_id = f"{DEMO_CLERK_ID_PREFIX}{demo_session_id}"
    demo_email    = f"demo+{demo_session_id[:8]}@{DEMO_EMAIL_DOMAIN}"

    user_id = get_or_create_user(
        clerk_user_id=demo_clerk_id,
        email=demo_email,
        display_name=DEMO_DISPLAY,
    )

    # Session fixation prevention: clear any pre-login session state before
    # writing authenticated session data, then restore the demo session ID.
    session.clear()
    session[_SK_DEMO_SESSION_ID] = demo_session_id
    session.modified = True

    set_user_session(
        user_id=user_id,
        clerk_id=demo_clerk_id,
        email=demo_email,
        display_name=DEMO_DISPLAY,
        is_demo=True,
    )
    return redirect(url_for("v2.index"))


@v2.post("/logout")
def logout():
    """Sign out via a CSRF-protected state-changing request."""
    clear_user_session()
    return redirect(url_for("v2.login"))


# ── Protected page routes ─────────────────────────────────────────────────────

@v2.get("/")
@require_auth
def index():
    """
    Overview — the default authenticated landing page for the Preview Release.

    Concise introduction: what Reserved does, who it is for, and where to go
    next.  Uses the same tax-engine data source as the Dashboard so figures
    reconcile exactly, but displays them statically (no count-up animation).
    """
    from reserved.auth import _SK_DISPLAY_NAME
    from reserved.web.routes import _get_profile
    _profile, _is_demo = _get_profile()
    _dash     = build_dashboard(_profile, is_demo=_is_demo)
    display_name = session.get(_SK_DISPLAY_NAME) or "Mesh"

    return render_template(
        "v2/overview.html",
        summary      = _dash["summary"],
        liability    = _dash["liability"],
        is_demo      = _dash["is_demo"],
        display_name = display_name,
    )


@v2.get("/dashboard")
@require_auth
def dashboard_view():
    """
    Dashboard — the animated financial experience.

    Begins with the estimated-tax animated hero, followed by supporting metric
    cards, bank transaction data, invoice progress and action prompts.

    Data source priority (same pattern as /v2/transactions):
      1. DB connections owned by g.user_id — used when the user has seeded
         or connected a real account.
      2. In-memory classified demo pipeline — shown when the user has no DB
         connections yet; no DB reads for transaction data, fully sandboxed.
    """
    user_conns = list_connections_for_user(g.user_id)
    db_source  = False
    sync_label = "Illustrative bank activity loaded"
    tx_summary: dict = {
        "total_income": 0, "total_tax_payments": 0, "total_expenses": 0,
        "unclassified_count": 0, "transaction_count": 0,
    }

    if user_conns:
        accounts = list_accounts(user_conns[0]["id"])
        if accounts:
            tx_summary = dict(
                get_transaction_summary(accounts[0]["id"]),
                transaction_count=len(get_transactions(accounts[0]["id"])),
            )
            db_source = True
            sync_label = "Connected account activity loaded"

    if not db_source:
        all_txns   = get_demo_transactions()
        mem        = summarise(all_txns)
        tx_summary = {
            "total_income":       float(mem["total_income"]),
            "total_tax_payments": float(mem["total_tax_payments"]),
            "total_expenses":     float(mem["total_expenses"]),
            "unclassified_count": mem["unclassified_count"],
            "transaction_count":  len(all_txns),
        }

    # Invoice summary — single efficient query (no N+1)
    inv_counts = get_invoice_counts_for_user(g.user_id)
    review_count = (
        tx_summary["unclassified_count"] + inv_counts.get("needs_review", 0)
    )

    # Tax-engine summary — same source of truth as the Overview.
    # Resolve the authenticated user's persisted profile before falling back to
    # session/default data. This prevents a returning user seeing the example
    # profile after starting a fresh browser session.
    from reserved.web.routes import _get_profile
    _profile, _is_demo = _get_profile()
    _dash     = build_dashboard(_profile, is_demo=_is_demo)

    return render_template(
        "v2/dashboard.html",
        user_conns     = user_conns,
        tx_summary     = tx_summary,
        inv_counts     = inv_counts,
        review_count   = review_count,
        db_source      = db_source,
        sync_label     = sync_label,
        featured_banks = FEATURED_BANKS,
        summary        = _dash["summary"],
        liability      = _dash["liability"],
        is_demo        = _dash["is_demo"],
    )


@v2.get("/connections")
@require_auth
def connections():
    return render_template("v2/connections.html", **_connections_ctx(
        request.args.get("state", "empty")
    ))


@v2.get("/sandbox-checklist")
@require_auth
def sandbox_checklist():
    """Internal sandbox test checklist — not linked from public nav."""
    client = YapilyClient()
    return render_template(
        "v2/sandbox_checklist.html",
        mock_mode=client.mock,
        sandbox_uuid_set=bool(client._uuid),
        sandbox_secret_set=bool(client._secret),
    )


# ── Protected Yapily integration routes ───────────────────────────────────────

@v2.post("/yapily/connect")
@require_auth
def yapily_connect():
    """
    Step 1 — Initiate the Hosted Pages consent flow.

    POST body: institution_id (str)
    Returns:   { hosted_url, consent_token, mock } or { error }

    In production: store consent_token server-side against the user's account
    before redirecting. Never pass it through the browser URL.
    """
    institution_id = request.form.get("institution_id", "").strip()
    if not institution_id:
        return jsonify({"ok": False, "error": "institution_id is required"}), 400

    # Use the authenticated user's internal DB id as the Yapily user identifier.
    yapily_user_id = str(g.user_id)
    callback_url = _yapily_callback_url()

    # OAuth CSRF protection: generate a random state token, store it in the
    # signed session cookie, and pass it to Yapily.  The callback validates
    # the returned state against the stored value before processing anything.
    import secrets as _secrets
    oauth_state = _secrets.token_urlsafe(32)
    session["_yapily_oauth_state"] = oauth_state
    session["_yapily_oauth_institution"] = institution_id
    session.modified = True

    try:
        client = YapilyClient()
        result = client.initiate_consent(
            institution_id=institution_id,
            user_id=yapily_user_id,
            callback_url=callback_url,
            state=oauth_state,
        )
        return jsonify({
            "ok":            True,
            "hosted_url":    result["hosted_url"],
            "consent_token": result["consent_token"],
            "mock":          client.mock,
        })
    except Exception as exc:
        session.pop("_yapily_oauth_state", None)
        session.pop("_yapily_oauth_institution", None)
        return jsonify({"ok": False, "error": str(exc)}), 500


@v2.get("/yapily/callback")
@require_auth
def yapily_callback():
    """
    Step 2 — Handle return from Hosted Pages.

    Yapily redirects here after the user authorises (or declines) on their
    bank's page. The connection is persisted and tied to g.user_id so that
    transaction data is isolated per user.

    Query params:
        consent=<token>        — always present
        institution=<id>       — present in mock and sandbox
        error=<code>           — present on decline (e.g. "access_denied")
    """
    error_code     = request.args.get("error", "")
    consent_token  = request.args.get("consent", "")
    institution_id = request.args.get("institution", "")
    received_state = request.args.get("state", "")

    if error_code:
        # Always consume state on error to prevent replay with the same token.
        session.pop("_yapily_oauth_state", None)
        session.pop("_yapily_oauth_institution", None)
        return redirect(url_for("v2.connections", state="error"))

    # OAuth state validation — prevents CSRF and replayed callbacks.
    expected_state = session.pop("_yapily_oauth_state", None)
    session.pop("_yapily_oauth_institution", None)
    session.modified = True

    if expected_state is not None:
        # A consent flow was initiated from this session — validate state.
        if not received_state or received_state != expected_state:
            log.warning(
                "Yapily callback state mismatch (expected %s, got %s) for user %s",
                expected_state[:8] + "…",
                received_state[:8] + "…" if received_state else "(none)",
                g.user_id,
            )
            return redirect(url_for("v2.connections", state="error"))
    else:
        # No pending state in session.
        # Allow mock=1 for sandbox/demo flows, but NEVER in production.
        # is_production_environment() is the single authoritative dual-lock check.
        # This prevents the sandbox bypass from ever executing against live bank data.
        _is_mock_ok = bool(request.args.get("mock")) and not is_production_environment()

        if not _is_mock_ok:
            log.warning(
                "Yapily callback received with no pending state for user %s — rejecting.",
                g.user_id,
            )
            return redirect(url_for("v2.connections", state="error"))

    if not consent_token:
        return redirect(url_for("v2.connections", state="error"))

    try:
        client = YapilyClient()
        _record = client.handle_callback(consent_token, institution_id)

        # Persist the connection owned by this authenticated user.
        # get_connection_by_token is idempotent — if the token already exists
        # (e.g. mock mode calling callback twice) we reuse the existing row.
        from reserved.database import save_connection as _save_connection
        existing = get_connection_by_token(consent_token)
        if not existing:
            # ConsentRecord is a dataclass; use attribute access, not .get()
            rec_institution_id = getattr(_record, "institution_id", None) or institution_id or "unknown"
            rec_expires_at = getattr(_record, "expires_at", None)
            expires_str = rec_expires_at.isoformat() if rec_expires_at else None
            _save_connection(
                institution_id=rec_institution_id,
                institution_name=rec_institution_id,  # nickname added when WS2 account sync lands
                consent_token=consent_token,
                expires_at=expires_str,
                session_key=f"user:{g.user_id}",
                user_id=g.user_id,
            )

        return redirect(url_for("v2.connections", state="returning"))
    except Exception:
        return redirect(url_for("v2.connections", state="error"))


@v2.post("/yapily/disconnect")
@require_auth
def yapily_disconnect():
    """
    Remove a bank connection.

    POST body: consent_token (str)

    The consent token is looked up in the database and verified to belong
    to the session user before any action is taken.  Tokens belonging to
    other users return 403 — the same response as a missing token so as
    not to reveal existence of other users' connections.
    """
    consent_token = request.form.get("consent_token", "").strip()
    _require_own_connection(consent_token)  # 403 if not owned by g.user_id

    try:
        client = YapilyClient()
        ok = client.revoke_consent(consent_token)
        if ok:
            return jsonify({"ok": True, "mock": client.mock})
        return jsonify({"ok": False, "error": "revoke_failed"}), 502
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@v2.post("/yapily/refresh")
@require_auth
def yapily_refresh():
    """
    Check consent health and refresh transaction data.

    POST body: consent_token (str)

    The consent token is verified to belong to the session user before
    any action is taken.
    """
    consent_token = request.form.get("consent_token", "").strip()
    _require_own_connection(consent_token)  # 403 if not owned by g.user_id

    try:
        client = YapilyClient()
        status = client.check_consent_status(consent_token)
        return jsonify({"ok": True, "status": status, "mock": client.mock})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── Transaction view helpers ──────────────────────────────────────────────────

def _ct_to_display(ct) -> dict:
    """Convert a ClassifiedTransaction to the uniform display dict."""
    return {
        "date": ct.date,
        "description": ct.description,
        "amount": float(ct.amount),
        "is_credit": ct.is_credit,
        "currency": ct.currency,
        "label": ct.classification.label,
        "badge": ct.classification.badge,
        "tax_relevant": ct.classification.tax_relevant,
        "confidence": ct.classification.confidence,
        "subcategory": ct.classification.subcategory,
        "method": ct.classification.method,
    }


def _row_to_display(row: dict) -> dict:
    """Convert a DB transaction row to the uniform display dict."""
    from reserved.providers.banking.classifier import (
        CATEGORY_BADGE, CATEGORY_LABELS, TransactionCategory,
    )
    try:
        cat = TransactionCategory(row["category"])
    except ValueError:
        cat = TransactionCategory.UNKNOWN
    return {
        "date": row["tx_date"],
        "description": row["description"],
        "amount": row["amount"],
        "is_credit": row["amount"] > 0,
        "currency": row.get("currency", "GBP"),
        "label": CATEGORY_LABELS.get(cat, cat.value),
        "badge": CATEGORY_BADGE.get(cat, "unknown"),
        "tax_relevant": bool(row.get("tax_relevant")),
        "confidence": row.get("confidence", 0.0),
        "subcategory": row.get("subcategory"),
        "method": row.get("method", "rules"),
    }


@v2.get("/transactions")
@require_auth
def transactions():
    """
    WS3/WS4 — Transaction intelligence view.

    Data source priority:
    1. DB connections owned by g.user_id — if the user has seeded or connected
       a real account, their own data is shown.
    2. In-memory classified demo pipeline — shown when the user has no DB
       connections yet; no DB reads, fully sandboxed.

    No user can ever see another user's transaction data.
    """
    category_filter = request.args.get("category", "")

    # Try user-scoped DB data first.
    user_conns = list_connections_for_user(g.user_id)
    if user_conns:
        # Use the first active connection's first account.
        conn_row = user_conns[0]
        accounts = list_accounts(conn_row["id"])
        if accounts:
            acc_id = accounts[0]["id"]
            all_raw = get_transactions(acc_id)
            summary = get_transaction_summary(acc_id)

            cat_counts: dict[str, int] = {}
            for r in all_raw:
                cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1

            if category_filter and category_filter in cat_counts:
                display = [_row_to_display(r) for r in all_raw if r["category"] == category_filter]
            else:
                display = [_row_to_display(r) for r in all_raw]
                category_filter = ""

            return render_template(
                "v2/transactions.html",
                transactions=display,
                summary=summary,
                category_filter=category_filter,
                cat_counts=cat_counts,
                db_source=True,
            )

    # Fallback: in-memory classified demo transactions (no DB, no user data).
    all_txns = get_demo_transactions()
    summary = summarise(all_txns)

    cat_counts = {}
    for ct in all_txns:
        key = ct.classification.category.value
        cat_counts[key] = cat_counts.get(key, 0) + 1

    if category_filter:
        try:
            filter_cat = TransactionCategory(category_filter)
            filtered = [ct for ct in all_txns if ct.classification.category == filter_cat]
        except ValueError:
            filtered = all_txns
            category_filter = ""
    else:
        filtered = all_txns

    return render_template(
        "v2/transactions.html",
        transactions=[_ct_to_display(ct) for ct in filtered],
        summary=summary,
        category_filter=category_filter,
        cat_counts=cat_counts,
        db_source=False,
    )


@v2.get("/invoices")
@require_auth
def invoices():
    """
    WS7/WS7A — Combined invoice matching + confirmation view.

    Shows persisted invoices with simplified 3-category status system:
      Matched     — ms == 'matched'
      Needs review — any other match result (partial, likely, currency_missing…)
      Outstanding  — no match row or ms == 'unmatched'

    Ownership is enforced: list_invoices_with_best_match() joins via
    invoices.user_id; get_user_review_items() joins via bank_connections.user_id.
    No client-supplied IDs are trusted.

    The unclassified payment count from get_user_review_items() is surfaced
    inline so the page serves as the combined invoice + confirmation experience.
    """
    rows     = list_invoices_with_best_match(user_id=g.user_id)
    has_data = bool(rows)

    matched     = sum(1 for r in rows if r.get("match_status") == "matched")
    outstanding = sum(
        1 for r in rows
        if r.get("match_id") is None or r.get("match_status") == "unmatched"
    )
    needs_review = len(rows) - matched - outstanding

    # Unclassified payments — shown in the "needs confirmation" strip
    review_items      = get_user_review_items(g.user_id)
    unclassified_count = len(review_items["unclassified_transactions"])
    review_count       = needs_review + unclassified_count

    return render_template(
        "v2/invoices.html",
        invoices           = rows,
        has_data           = has_data,
        inv_matched        = matched,
        inv_outstanding    = outstanding,
        inv_review         = needs_review,
        unclassified_count = unclassified_count,
        review_count       = review_count,
    )


@v2.post("/invoices/seed")
@require_auth
def invoices_seed():
    """
    Seed demo invoices and run the matching engine for this user.

    Idempotent: seed_demo_invoices() skips existing references, and matching
    is only run for invoices that have no existing match rows.  Each user's
    invoice and match rows are isolated via invoices.user_id.
    """
    from reserved.matching.demo_invoices import (
        DEMO_INVOICES,
        seed_demo_invoices,
        get_demo_transactions_for_matching,
    )

    # 1. Persist demo invoices for this user (idempotent).
    seed_demo_invoices(user_id=g.user_id)

    # 2. Run matching for any invoice that has no existing match rows.
    user_invoices = list_invoices(user_id=g.user_id)
    engine        = MatchingEngine()
    all_txns      = get_demo_transactions_for_matching()

    for db_inv in user_invoices:
        if get_matches_for_invoice(db_inv["id"]):
            continue  # already matched — skip (idempotent)

        inv_obj = next(
            (i for i in DEMO_INVOICES if i.reference == db_inv["reference"]),
            None,
        )
        if inv_obj is None:
            continue

        result = engine.match(inv_obj, all_txns)
        persist_match_result(result, invoice_id=db_inv["id"])

    return redirect(url_for("v2.invoices"))


@v2.route("/settings", methods=["GET", "POST"])
@require_auth
def settings_page():
    """
    V2 Settings — profile and tax-year configuration within the V2 experience.

    Reuses the profile helpers from reserved.web.routes to keep a single
    source of truth for normalisation and DB persistence.  After a successful
    POST the user is returned to the V2 dashboard (not the legacy public site).
    """
    from reserved.web.routes import (
        _normalise_settings,
        _get_profile,
        _profile_to_form_values,
        _profile_to_db_data,
    )
    from reserved.database import save_profile_by_user

    if request.method == "POST":
        from reserved.settings_validation import settings_error_values, settings_field_errors
        settings_error_fields = settings_field_errors(request.form)
        if settings_error_fields:
            profile, _ = _get_profile()
            form_profile = settings_error_values(
                request.form, _profile_to_form_values(profile)
            )
            return render_template(
                "v2/settings.html", profile=form_profile,
                settings_errors=list(settings_error_fields.values()),
                settings_error_fields=settings_error_fields,
                tax_year=configured_tax_year(),
            ), 400
        profile = _normalise_settings(request.form)
        save_profile_by_user(g.user_id, _profile_to_db_data(profile))
        session["profile"] = profile
        session.modified = True
        return redirect(url_for("v2.dashboard_view"))

    profile, _ = _get_profile()
    form_profile = _profile_to_form_values(profile)
    return render_template("v2/settings.html", profile=form_profile, tax_year=configured_tax_year())


@v2.get("/review")
@require_auth
def review_queue():
    """
    WS7 — Review queue: items requiring user attention.

    Shows:
    - Unknown or low-confidence transactions (< 60 % confidence)
    - Invoice matches that are unmatched, missing-currency, or pending review

    Data source priority (same pattern as /v2/transactions):
    1. DB-scoped data via get_user_review_items() — all joins enforce ownership.
    2. In-memory demo fallback when no DB data exists.

    Templates tolerate missing transaction_id (orphaned match rows).
    """
    # Review is now combined with the invoice view.  Redirect permanently so
    # bookmarks and existing tests follow the canonical URL.
    return redirect(url_for("v2.invoices"), code=302)


@v2.get("/optimise")
@require_auth
def optimise_view():
    """
    Explore-your-options page — detects the Personal Allowance taper and offers
    modelled pension-contribution scenarios for the current user's profile.

    HICBC is outside the v1 customer scope and is filtered out here.

    Data flow:
      1. _get_profile()         — user's profile (DB-first, session fallback)
      2. assess_opportunities() — checks thresholds, returns opportunities
      3. list_optimise_scenarios() — previously saved comparisons for this user
    """
    from reserved.engines.optimise import assess_opportunities
    from reserved.database import list_optimise_scenarios
    from reserved.web.routes import _get_profile

    profile, is_demo = _get_profile()

    income_raw = request.args.get("income")
    try:
        income_override = Decimal(str(income_raw)) if income_raw else None
    except (InvalidOperation, TypeError, ValueError):
        income_override = None

    pos, opps = assess_opportunities(profile, projected_income_override=income_override)
    # HICBC is outside the v1 customer scope (post-v1).  It must not surface in
    # any customer scenario, total, reserve or personalised warning.
    opps = [o for o in opps if o.id != "HICBC"]
    saved = list_optimise_scenarios(g.user_id)

    return render_template(
        "v2/optimise.html",
        pos=pos,
        opportunities=opps,
        saved_scenarios=saved,
        is_demo=is_demo,
        profile=profile,
        tax_year=resolve_tax_year(
            result_tax_year=pos.tax_year,
            context_tax_year=configured_tax_year(),
        ),
    )


@v2.post("/optimise/calculate")
@require_auth
@csrf.exempt
def optimise_calculate():
    """
    JSON API — calculate a before/after scenario for a given pension addition.

    Request body (JSON):
        opportunity_id     str   — "PA_TAPER" (HICBC is rejected as out of scope)
        projected_income   float
        current_pension    float
        additional_pension float

    Response (JSON):
        ok            bool
        before        dict — ANI, PA, IT, total for current position (income-tax only)
        after         dict — same for scenario position
        it_reduction        str
        total_benefit       str
        basic_rate_relief   str   — HMRC top-up added to pension pot (NOT in total)
        caveats             list[str]

    CSRF is exempted because authentication (@require_auth) already proves
    ownership; this endpoint only reads engine state.
    """
    from reserved.engines.optimise import model_pension_scenario

    data = request.get_json(silent=True) or {}
    try:
        projected_income   = Decimal(str(data.get("projected_income",   "0")))
        current_pension    = Decimal(str(data.get("current_pension",    "0")))
        additional_pension = Decimal(str(data.get("additional_pension", "0")))
        opportunity_id     = str(data.get("opportunity_id", "PA_TAPER"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": f"Invalid numeric input: {exc}"}), 400

    if additional_pension < Decimal("0"):
        return jsonify({"ok": False, "error": "Additional pension must not be negative."}), 400

    # HICBC is outside the v1 customer scope; the customer scenario API must not
    # compute or return it.
    if opportunity_id == "HICBC":
        return jsonify({
            "ok": False,
            "error": "High Income Child Benefit Charge is outside the current scope.",
        }), 400

    try:
        r = model_pension_scenario(
            projected_income, current_pension, additional_pension,
            opportunity_id, annual_cb=Decimal("0"),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    def fmt(v):
        return f"{float(v):,.2f}"

    # Customer-facing figures are income-tax only; HICBC is never included in a
    # customer total or benefit even though the internal engine may model it.
    return jsonify({
        "ok": True,
        "before": {
            "ani":   fmt(r.before.adjusted_net_income),
            "pa":    fmt(r.before.personal_allowance),
            "it":    fmt(r.before.estimated_income_tax),
            "total": fmt(r.before.estimated_income_tax),
        },
        "after": {
            "ani":   fmt(r.after.adjusted_net_income),
            "pa":    fmt(r.after.personal_allowance),
            "it":    fmt(r.after.estimated_income_tax),
            "total": fmt(r.after.estimated_income_tax),
        },
        "it_reduction":      fmt(r.it_reduction),
        "total_benefit":     fmt(r.it_reduction),
        "basic_rate_relief": fmt(r.basic_rate_relief_to_pension),
        "total_pension":     fmt(r.total_pension),
        "tax_year":          r.before.tax_year,
        "caveats":           r.caveats,
    })


@v2.post("/optimise/save-scenario")
@require_auth
@csrf.exempt
def optimise_save_scenario():
    """Save a pension-comparison scenario for the current user.

    The applicable tax year is required and validated fail-closed: a missing,
    malformed, unsupported or contradictory year is rejected rather than silently
    replaced with the currently configured year.
    """
    from reserved.database import save_optimise_scenario

    data     = request.get_json(silent=True) or {}
    label    = (str(data.get("label") or "")).strip()[:80] or None
    inputs   = data.get("inputs")  or {}
    outputs  = data.get("outputs") or {}
    opp_id   = str(data.get("opportunity_id") or "unknown")

    tax_year = data.get("tax_year")
    if tax_year is None:
        return jsonify({"ok": False, "error": "A tax year is required to save a scenario."}), 400
    try:
        resolved_year = resolve_tax_year(
            result_tax_year=tax_year,
            context_tax_year=configured_tax_year(),
        )
    except UnsupportedTaxYear as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    row_id = save_optimise_scenario(
        g.user_id, opp_id, inputs, outputs, label=label, tax_year=resolved_year
    )
    return jsonify({"ok": True, "id": row_id})


@v2.delete("/optimise/saved/<int:scenario_id>")
@require_auth
@csrf.exempt
def optimise_delete_scenario(scenario_id: int):
    """Delete a saved scenario; enforces user ownership."""
    from reserved.database import delete_optimise_scenario
    ok = delete_optimise_scenario(scenario_id, g.user_id)
    return jsonify({"ok": ok})


@v2.post("/transactions/seed")
@require_auth
def transactions_seed():
    """
    Seed demo bank connection + transactions into the DB for the session user.

    Each user gets their own demo connection row; seeding one user's data
    never writes to or overwrites another user's records.  Idempotent.
    """
    result = seed_demo_data(user_id=g.user_id)
    return redirect(url_for("v2.transactions", _seeded=result["tx_count"]))
