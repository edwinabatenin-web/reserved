"""
Founder-only dashboard blueprint.

Routes
------
GET  /founder/login      — show login form
POST /founder/login      — authenticate with FOUNDER_PASSWORD secret
GET  /founder/           — dashboard (requires auth)
POST /founder/logout     — clear founder session
GET  /founder/export/feedback     — download all feedback as CSV
GET  /founder/export/early-access — download all registrations as CSV

Rate limiting
-------------
Login attempts are tracked by IP address using the persistent SQLite
rate_limit_log table.  Limits survive worker restarts and are shared
across all Gunicorn workers.  ProxyFix (applied at app factory) ensures
request.remote_addr is the real client IP, not the proxy's address.
"""

from __future__ import annotations

import csv
import hmac
import io
import logging
import os
from functools import wraps

from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from reserved.database import (
    check_rate_limit,
    get_all_feedback,
    get_all_registrations,
    get_early_access_stats,
    get_feedback_stats,
    get_recent_feedback,
    get_recent_registrations,
    record_rate_attempt,
)
from reserved.security import spreadsheet_safe_row

log = logging.getLogger(__name__)

founder = Blueprint("founder", __name__, url_prefix="/founder")

_SESSION_KEY = "_founder_authed"

# ── Persistent DB-backed rate limiting ────────────────────────────────────────
# Limits are enforced across all workers and survive restarts.
_RL_ACTION = "founder_login"
_RL_MAX    = 5     # failed attempts before lockout
_RL_WINDOW = 3600  # rolling window in seconds (1 hour)


def _client_ip() -> str:
    """Return the real client IP.

    ProxyFix (applied in the app factory) rewrites request.remote_addr from
    X-Forwarded-For so this is already the actual client IP — no manual header
    inspection required or safe here.
    """
    return request.remote_addr or "unknown"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _is_authenticated() -> bool:
    return session.get(_SESSION_KEY) is True


def _check_password(provided: str) -> bool:
    expected = os.environ.get("FOUNDER_PASSWORD", "")
    if not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def require_founder(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _is_authenticated():
            return redirect(url_for("founder.login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes ────────────────────────────────────────────────────────────────────

@founder.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if _is_authenticated():
        return redirect(url_for("founder.dashboard"))

    if request.method == "POST":
        ip = _client_ip()

        if not check_rate_limit(_RL_ACTION, ip, _RL_MAX, _RL_WINDOW):
            log.warning("Founder login: rate-limited")
            error = "Too many failed attempts. Please try again later."
        else:
            password = request.form.get("password", "")
            if _check_password(password):
                record_rate_attempt(_RL_ACTION, ip, success=True)
                # Privilege boundary: do not elevate any pre-login session
                # state supplied by the browser. Start a clean founder session
                # just as the customer authentication flow does.
                session.clear()
                session[_SESSION_KEY] = True
                session.permanent = True
                log.info("Founder login: success")
                return redirect(url_for("founder.dashboard"))
            else:
                record_rate_attempt(_RL_ACTION, ip, success=False)
                log.warning("Founder login: failed attempt")
                error = "Incorrect password."

    return render_template("founder/login.html", error=error)


@founder.get("/")
@require_founder
def dashboard():
    feedback_stats = get_feedback_stats()
    ea_stats       = get_early_access_stats()
    recent_fb      = get_recent_feedback(limit=20)
    recent_ea      = get_recent_registrations(limit=50)

    # Filter to submissions that have at least one comment
    fb_with_comments = [r for r in recent_fb if r.get("comments")]

    return render_template(
        "founder/dashboard.html",
        feedback_stats   = feedback_stats,
        ea_stats         = ea_stats,
        recent_feedback  = recent_fb,
        recent_ea        = recent_ea,
        fb_with_comments = fb_with_comments,
    )


@founder.post("/logout")
@require_founder
def logout():
    # Founder access is privileged and can expose personal submissions.
    # Clear the complete browser session so OAuth state, profile data or an
    # unrelated authenticated identity cannot survive a founder sign-out.
    session.clear()
    session.modified = True
    log.info("Founder logout")
    return redirect(url_for("founder.login"))


@founder.get("/export/feedback")
@require_founder
def export_feedback():
    rows = get_all_feedback()
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id", "submitted_at", "intuitive", "useful", "trustworthy",
            "area", "comments", "would_use", "email", "browser", "device", "page_url",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(spreadsheet_safe_row(row) for row in rows)
    resp = make_response(output.getvalue())
    resp.headers["Content-Type"]        = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="feedback.csv"'
    return resp


@founder.get("/export/early-access")
@require_founder
def export_early_access():
    rows = get_all_registrations()
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id", "submitted_at", "name", "email",
            "occupation", "working_style", "referral_source", "comments",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(spreadsheet_safe_row(row) for row in rows)
    resp = make_response(output.getvalue())
    resp.headers["Content-Type"]        = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="early-access.csv"'
    return resp
