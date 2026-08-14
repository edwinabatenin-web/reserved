import json
import logging
import os
from decimal import Decimal, InvalidOperation

import requests as _http

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from reserved.auth import current_user_id
from reserved.database import (
    check_rate_limit,
    get_profile_by_user,
    record_rate_attempt,
    save_profile_by_user,
)
from reserved.engines.capital_gains import CapitalDisposal, estimate_cgt
from reserved.engines import tax_config
from reserved.services.dashboard import build_dashboard, DEFAULT_PROFILE
from reserved.services.roadmap import FEATURES

log = logging.getLogger(__name__)
web = Blueprint("web", __name__)

_TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v1/siteverify"


def _verify_turnstile() -> tuple[bool, str | None]:
    """Verify a Cloudflare Turnstile token from the current request.

    Returns (ok, error_message).  Verification is skipped only when neither
    Turnstile key is set, so local previews work without Cloudflare credentials.
    A partial configuration is treated as unavailable rather than bypassed.

    Once configured, verification fails closed: a missing token, rejected
    challenge, malformed response, HTTP error, or network error blocks the
    submission.  Bot protection must not silently disappear during an outage.
    """
    secret = os.environ.get("TURNSTILE_SECRET_KEY", "")
    site_key = os.environ.get("TURNSTILE_SITE_KEY", "")
    if not secret and not site_key:
        return True, None  # explicit dev/test bypass — entirely unconfigured
    if not secret:
        log.error("Turnstile site key is configured without a verification secret")
        return False, "The security check is temporarily unavailable. Please try again."
    token = request.form.get("cf-turnstile-response", "").strip()
    if not token:
        return False, "Please complete the security check."
    try:
        resp = _http.post(
            _TURNSTILE_URL,
            data={"secret": secret, "response": token, "remoteip": request.remote_addr},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return True, None
        codes = data.get("error-codes", [])
        log.warning("Turnstile verification failed: %s", codes)
        return False, "Please complete the security check."
    except Exception as exc:  # noqa: BLE001
        log.warning("Turnstile verification unavailable (failing closed): %s", exc)
        return False, "The security check is temporarily unavailable. Please try again."


# ── Settings normalisation helpers ────────────────────────────────────────────

_STUDENT_LOAN_MAP: dict[str, list] = {
    "none":          [],
    "plan_1":        [1],
    "plan_2":        [2],
    "plan_4":        [4],
    "plan_5":        [5],
    "postgraduate":  ["postgraduate"],
}

_STUDENT_LOAN_REVERSE: dict[str, str] = {
    "":             "none",
    "[]":           "none",
    "[1]":          "plan_1",
    "[2]":          "plan_2",
    "[4]":          "plan_4",
    "[5]":          "plan_5",
    "['postgraduate']": "postgraduate",
}


def _plans_to_form_value(plans: list) -> str:
    """Return the form <select> value for a student_loan_plans list."""
    if not plans:
        return "none"
    if plans == [1]:
        return "plan_1"
    if plans == [2]:
        return "plan_2"
    if plans == [4]:
        return "plan_4"
    if plans == [5]:
        return "plan_5"
    if plans == ["postgraduate"]:
        return "postgraduate"
    # Dual/unsupported combo — show first recognised plan
    for p in plans:
        key = [k for k, v in _STUDENT_LOAN_MAP.items() if v == [p]]
        if key:
            return key[0]
    return "none"


def _safe_decimal_str(raw) -> str:
    """Parse a form value to a non-negative decimal string, defaulting to '0'."""
    try:
        val = Decimal(str(raw or "0"))
        return str(max(Decimal("0"), val))
    except (InvalidOperation, TypeError):
        return "0"


def _normalise_settings(form) -> dict:
    """Convert the raw settings form data to a profile dict suitable for the engine."""
    # Child Benefit annual override — empty string or "0" → None (use standard rates)
    cb_annual_raw = _safe_decimal_str(form.get("child_benefit_annual"))
    cb_annual = float(cb_annual_raw) if float(cb_annual_raw) > 0 else None
    return {
        "first_name": (form.get("first_name") or "").strip() or DEFAULT_PROFILE["first_name"],
        "trading_name": (form.get("trading_name") or "").strip(),
        "entity_type": form.get("entity_type", "sole_trader"),
        "day_job_salary": _safe_decimal_str(form.get("day_job_salary")),
        "ytd_freelance_profit": _safe_decimal_str(form.get("ytd_freelance_profit")),
        "personal_pension_contributions": _safe_decimal_str(form.get("pension")),
        "student_loan_plans": _STUDENT_LOAN_MAP.get(
            form.get("student_loan", "none"), []
        ),
        "accounting_method": form.get("accounting_method", "cash_basis"),
        "vat_registered": form.get("vat_status") == "vat_registered",
        "child_benefit_children": int(form.get("child_benefit_children") or 0),
        "child_benefit_annual": cb_annual,
    }


def _profile_to_form_values(profile: dict) -> dict:
    """Add form-friendly display keys to a profile dict for template pre-filling."""
    return {
        **profile,
        "pension": profile.get("personal_pension_contributions", "0"),
        "student_loan": _plans_to_form_value(profile.get("student_loan_plans") or []),
        "vat_status": "vat_registered" if profile.get("vat_registered") else "not_vat_registered",
        "child_benefit_children": int(profile.get("child_benefit_children") or 0),
        "child_benefit_annual": profile.get("child_benefit_annual") or "",
    }


def _profile_to_db_data(profile: dict) -> dict:
    """
    Map the settings form profile dict to user_profiles table fields.

    The critical financial fields are stored in named columns for easy querying.
    The full profile dict (entity_type, day_job_salary, etc.) is serialised to
    the `notes` JSON column so no data is lost on round-trip.
    """
    extra = {
        "entity_type":              profile.get("entity_type"),
        "day_job_salary":           str(profile.get("day_job_salary") or "0"),
        "trading_name":             profile.get("trading_name"),
        "accounting_method":        profile.get("accounting_method"),
        "vat_registered":           profile.get("vat_registered"),
        "first_name":               profile.get("first_name"),
        "child_benefit_children":   int(profile.get("child_benefit_children") or 0),
        "child_benefit_annual":     profile.get("child_benefit_annual"),
    }
    return {
        "display_name":             profile.get("first_name"),
        "income_estimate":          float(profile.get("ytd_freelance_profit") or 0),
        "pension_contribution":     float(profile.get("personal_pension_contributions") or 0),
        "student_loan_plans":       profile.get("student_loan_plans") or [],
        "notes":                    json.dumps(extra),
        "child_benefit_children":   int(profile.get("child_benefit_children") or 0),
        "child_benefit_annual":     profile.get("child_benefit_annual"),
    }


def _db_data_to_profile(row: dict) -> dict:
    """
    Convert a user_profiles DB row back to the settings form profile dict.

    Restores the full profile from the `notes` JSON field when available,
    falling back to the named columns for the critical financial fields.
    """
    result = dict(DEFAULT_PROFILE)
    # Restore from notes JSON (full round-trip fidelity)
    notes = row.get("notes")
    if notes:
        try:
            extra = json.loads(notes)
            for key in ("entity_type", "day_job_salary", "trading_name",
                        "accounting_method", "vat_registered", "first_name",
                        "child_benefit_children", "child_benefit_annual"):
                if key in extra and extra[key] is not None:
                    result[key] = extra[key]
        except (ValueError, TypeError):
            pass
    # Named columns override (authoritative for financial values)
    if row.get("display_name"):
        result["first_name"] = row["display_name"]
    if row.get("income_estimate") is not None:
        result["ytd_freelance_profit"] = str(row["income_estimate"])
    if row.get("pension_contribution") is not None:
        result["personal_pension_contributions"] = str(row["pension_contribution"])
    if row.get("student_loan_plans"):
        result["student_loan_plans"] = row["student_loan_plans"]
    return result


def _get_profile() -> tuple[dict, bool]:
    """
    Return (profile, is_demo).  is_demo is True if the user has never saved.

    Priority:
    1. Authenticated user → DB (user_profiles table via save_profile_by_user)
    2. Anonymous → Flask session (backward-compatible public preview path)
    """
    uid = current_user_id()
    if uid is not None:
        row = get_profile_by_user(uid)
        if row:
            return _db_data_to_profile(row), False
    saved = session.get("profile")
    if saved and isinstance(saved, dict):
        return {**DEFAULT_PROFILE, **saved}, False
    return dict(DEFAULT_PROFILE), True


# ── Routes ────────────────────────────────────────────────────────────────────

def _parse_user_agent(ua: str) -> tuple[str, str]:
    """Return (browser, device) derived from a User-Agent string."""
    ua_lower = (ua or "").lower()

    # Device (check mobile first — most specific)
    if any(tok in ua_lower for tok in ("iphone", "android", "mobile", "blackberry", "windows phone")):
        device = "Mobile"
    elif any(tok in ua_lower for tok in ("ipad", "tablet")):
        device = "Tablet"
    else:
        device = "Desktop"

    # Browser (order matters — Edge/Chrome share tokens)
    if "edg/" in ua_lower or "edge/" in ua_lower:
        browser = "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "firefox/" in ua_lower:
        browser = "Firefox"
    elif "chrome/" in ua_lower:
        browser = "Chrome"
    elif "safari/" in ua_lower:
        browser = "Safari"
    elif "msie" in ua_lower or "trident/" in ua_lower:
        browser = "IE"
    else:
        browser = "Unknown"

    return browser, device


@web.post("/feedback")
def feedback():
    """Validate and persist a feedback submission."""
    from reserved.database import save_feedback
    from reserved.services.email import notify_feedback

    # ── Bot protection ────────────────────────────────────────────────────────
    ts_ok, ts_err = _verify_turnstile()
    if not ts_ok:
        return jsonify({"ok": False, "error": ts_err}), 400

    # ── Rate limiting: 20 submissions per IP per hour ─────────────────────────
    ip = request.remote_addr
    if not check_rate_limit("feedback", ip, max_attempts=20, window_seconds=3600):
        log.warning("Feedback submission rate-limited")
        return jsonify({"ok": False, "error": "Too many submissions. Please try again later."}), 429

    intuitive   = request.form.get("intuitive",   "").strip()
    useful      = request.form.get("useful",      "").strip()
    trustworthy = request.form.get("trustworthy", "").strip()

    def _valid_score(v):
        try:
            return 1 <= int(v) <= 5
        except (TypeError, ValueError):
            return False

    # At least one rating must be present
    scores = [intuitive, useful, trustworthy]
    if not any(_valid_score(s) for s in scores):
        return jsonify({"ok": False, "error": "Please rate at least one question."}), 400

    # Input length limits
    comments_raw = request.form.get("confusing", "").strip()[:2000]
    area_raw     = request.form.get("area",      "").strip()[:200]
    would_use    = request.form.get("would_use", "").strip()[:50]
    email_raw    = request.form.get("email",     "").strip()[:254]

    # Browser / device context
    ua = request.headers.get("User-Agent", "")
    browser, device = _parse_user_agent(ua)
    page_url = (request.referrer or request.form.get("page_url", "") or "")[:500]

    data = {
        "intuitive":   intuitive,
        "useful":      useful,
        "trustworthy": trustworthy,
        "area":        area_raw,
        "comments":    comments_raw,
        "would_use":   would_use,
        "email":       email_raw,
        "browser":     browser,
        "device":      device,
        "page_url":    page_url,
    }

    try:
        save_feedback(data, ip=ip)
        record_rate_attempt("feedback", ip, success=True)
        log.info("Feedback saved [browser=%s device=%s]", browser, device)
    except Exception:
        log.exception("Failed to save feedback submission")
        return jsonify({"ok": False, "error": "Something went wrong — please try again."}), 500

    # Email notification — fire-and-forget; a delivery failure must never cause
    # the form to falsely report an error after the data has been stored.
    email_sent = False
    try:
        email_sent = notify_feedback(data)
    except Exception:  # noqa: BLE001
        log.warning("Feedback notification email raised unexpectedly")
    if not email_sent:
        log.info("Feedback notification email not sent (SMTP unconfigured or failed)")

    return jsonify({"ok": True})


@web.get("/")
def dashboard():
    return redirect(url_for("v2.index"))


@web.post("/calculate")
def calculate():
    raw = request.form.get("invoice_amount", "4800")
    try:
        amount = Decimal(raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        flash("Enter an invoice amount greater than £0.", "error")
        return redirect(url_for("web.dashboard"))
    profile, is_demo = _get_profile()
    return render_template(
        "dashboard.html",
        **build_dashboard(profile, str(amount), is_demo=is_demo),
        features=FEATURES,
    )


@web.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        from reserved.settings_validation import settings_error_values, settings_field_errors
        settings_error_fields = settings_field_errors(request.form)
        if settings_error_fields:
            profile, _ = _get_profile()
            form_profile = settings_error_values(
                request.form, _profile_to_form_values(profile)
            )
            return render_template(
                "settings.html", profile=form_profile,
                settings_errors=list(settings_error_fields.values()),
                settings_error_fields=settings_error_fields,
            ), 400
        profile = _normalise_settings(request.form)
        uid = current_user_id()
        if uid is not None:
            # Authenticated user — persist to DB (survives browser restarts and
            # new devices once the user signs in again).
            save_profile_by_user(uid, _profile_to_db_data(profile))
        # Also write to session for fast reads on the same request cycle.
        session["profile"] = profile
        session.modified = True
        flash("Settings saved — your dashboard now reflects your profile.", "success")
        # If the user has an active V2 session send them to the V2 dashboard;
        # otherwise fall back to the legacy public dashboard.
        from reserved.auth import _SK_USER_ID
        if _SK_USER_ID in session:
            return redirect("/v2/")
        return redirect(url_for("web.dashboard"))
    profile, _ = _get_profile()
    form_profile = _profile_to_form_values(profile)
    return render_template("settings.html", profile=form_profile)


@web.route("/capital-gains", methods=["GET", "POST"])
def capital_gains():
    # Capital Gains Tax is outside the founder-approved v1 scope. Keep the
    # engine for later development without exposing a customer calculator via
    # this legacy direct URL.
    abort(404)

    # Dormant post-v1 implementation retained for future reactivation.
    result = None
    if request.method == "POST":
        try:
            disposal = CapitalDisposal(
                asset_type=request.form.get("asset_type", "shares"),
                description=request.form.get("description", "Example disposal"),
                disposal_date=request.form.get("disposal_date", ""),
                proceeds=Decimal(request.form.get("proceeds", "0")),
                allowable_cost=Decimal(request.form.get("allowable_cost", "0")),
                acquisition_costs=Decimal(request.form.get("acquisition_costs", "0")),
                disposal_costs=Decimal(request.form.get("disposal_costs", "0")),
            )
            result = estimate_cgt(
                [disposal],
                taxable_income_before_gains=Decimal(request.form.get("taxable_income", "0")),
                brought_forward_losses=Decimal(request.form.get("brought_forward_losses", "0")),
                tax_already_paid=Decimal(request.form.get("tax_already_paid", "0")),
            )
        except Exception:
            flash("Check the values entered and try again.", "error")
    return render_template("capital_gains.html", result=result)


@web.get("/connections")
def connections():
    return render_template("connections.html")


@web.get("/about")
def about():
    return render_template("about.html")


@web.get("/privacy")
def privacy():
    return render_template("privacy.html")


@web.get("/robots.txt")
def robots_txt():
    """Serve robots.txt from the static directory at the canonical path."""
    import flask
    return send_from_directory(flask.current_app.static_folder, "robots.txt",
                               mimetype="text/plain")


@web.post("/early-access")
def early_access():
    """Validate and persist an early-access registration."""
    from reserved.database import save_early_access
    from reserved.services.email import notify_early_access
    import re

    # ── Bot protection ────────────────────────────────────────────────────────
    ts_ok, ts_err = _verify_turnstile()
    if not ts_ok:
        return jsonify({"ok": False, "error": ts_err}), 400

    # ── Rate limiting: 10 registrations per IP per hour ───────────────────────
    ip = request.remote_addr
    if not check_rate_limit("early_access", ip, max_attempts=10, window_seconds=3600):
        log.warning("Early-access registration rate-limited")
        return jsonify({"ok": False, "error": "Too many submissions. Please try again later."}), 429

    name  = request.form.get("name",  "").strip()[:100]
    email = request.form.get("email", "").strip()[:254]

    if not name:
        return jsonify({"ok": False, "error": "Please enter your name."}), 400
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    data = {
        "name":             name,
        "email":            email,
        "occupation":       request.form.get("occupation",       "").strip()[:100],
        "working_style":    request.form.get("working_style",    "").strip()[:100],
        "referral_source":  request.form.get("referral_source",  "").strip()[:200],
        "comments":         request.form.get("comments",         "").strip()[:2000],
    }

    try:
        result = save_early_access(data, ip=ip)
        record_rate_attempt("early_access", ip, success=True)
        log.info(
            "Early-access registration stored [duplicate=%s]",
            result.get("duplicate", False),
        )
    except Exception:
        log.exception("Failed to save early-access registration")
        return jsonify({"ok": False, "error": "Something went wrong — please try again."}), 500

    # Email notification — fire-and-forget; delivery failure must not falsely
    # report an error after the registration has been stored successfully.
    if not result.get("duplicate"):
        email_sent = False
        try:
            email_sent = notify_early_access(data)
        except Exception:  # noqa: BLE001
            log.warning("Early access notification email raised unexpectedly")
        if not email_sent:
            log.info("Early access notification email not sent (SMTP unconfigured or failed)")

    return jsonify(result)


@web.get("/future")
def future():
    return render_template("future.html", features=FEATURES)


# ── Dev-only tax assurance page ───────────────────────────────────────────────
# Not linked from the main nav. Access via /tax-assurance directly.

@web.get("/tax-assurance")
def tax_assurance():
    """Internal tax-assurance page showing engine metadata and test status."""
    import json
    from pathlib import Path

    meta_path = Path(__file__).resolve().parent.parent / "assurance_metadata.json"
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text())
    else:
        metadata = {
            "tax_year": tax_config.TAX_YEAR,
            "rules_version": tax_config.RULES_VERSION,
            "verified_date": None,
            "test_counts": None,
            "all_tests_passed": None,
            "scope": {
                "in_scope": [
                    "Income tax — England/Wales/NI sole traders",
                    "Class 4 National Insurance",
                    "Student loan Plans 1, 2, 4, 5 and Postgraduate",
                    "Pension Relief at Source (basic-rate band extension)",
                    "Capital Gains Tax — basic/higher rate split",
                    "Annual Exempt Amount offset",
                    "Brought-forward loss relief",
                ],
                "out_of_scope": [
                    "Scottish income tax",
                    "Dividend and savings income",
                    "PAYE coding interactions",
                    "VAT-registered traders",
                    "Residential property CGT rates",
                    "BADR / Investors' Relief",
                    "Share pooling and same-day/30-day matching",
                ],
            },
            "assumptions": [
                "Illustrative sole-trader estimate only; not a tax return or professional advice.",
                "Scottish income tax, dividend tax, and savings income are outside scope.",
                "Pension contributions are treated as Relief at Source (gross figure expected).",
            ],
        }
    return render_template("tax_assurance.html", meta=metadata)
