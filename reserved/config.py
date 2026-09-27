import os
from datetime import timedelta


def _parse_hicbc_enabled(raw: str) -> bool:
    """Parse the HICBC gate strictly: only an explicit true value enables it."""
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def hicbc_enabled() -> bool:
    """Return whether the HICBC feature gate is enabled for this process.

    Read at call time so the gate reflects the process environment rather than
    an import-time snapshot.
    """
    return _parse_hicbc_enabled(os.environ.get("HICBC_ENABLED", ""))


def hicbc_annual_preview_enabled() -> bool:
    """Separate disabled-first switch, never inferred from the HICBC gate."""
    return os.environ.get("HICBC_ANNUAL_PREVIEW_ENABLED", "") == "1"


def durable_hicbc_annual_enabled() -> bool:
    """Explicit switch for the trusted HICBC annual read API only."""
    return os.environ.get("HICBC_DURABLE_ANNUAL_ENABLED", "") == "1"


def paye_manual_baseline_enabled() -> bool:
    """Independent disabled-first manual capture switch, read at request time."""
    return os.environ.get("PAYE_MANUAL_BASELINE_ENABLED", "") == "1"


def paye_manual_journey_enabled() -> bool:
    """Independent disabled-first switch for the structured PAYE journey."""
    return os.environ.get("PAYE_MANUAL_JOURNEY_ENABLED", "") == "1"


def durable_paye_composition_enabled() -> bool:
    """Explicit activation switch for the authenticated PAYE composition API."""
    return os.environ.get("PAYE_DURABLE_COMPOSITION_ENABLED", "") == "1"


def mtd_manual_scope_enabled() -> bool:
    """Independent disabled-first manual MTD journey; never enabled implicitly."""
    return os.environ.get("MTD_MANUAL_SCOPE_ENABLED", "") == "1"


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY        = os.environ.get("SESSION_SECRET", "reserved-local-preview-only")
    JSON_SORT_KEYS    = False
    DEMO_MODE         = os.environ.get("RESERVED_DEMO_MODE", "1") == "1"
    DATABASE_URL      = os.environ.get("DATABASE_URL")

    # ── CSRF ──────────────────────────────────────────────────────────────────
    WTF_CSRF_TIME_LIMIT = 7200          # tokens expire after 2 hours

    # ── Session & cookies ─────────────────────────────────────────────────────
    # Cookies are always HttpOnly (Flask default).
    # Secure flag is set so cookies are only sent over HTTPS.  In local dev
    # (HTTP) Werkzeug still sets the flag but the browser ignores it — no
    # functional impact on development.
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"    # CSRF protection without breaking OAuth flows
    SESSION_COOKIE_SECURE    = True     # require HTTPS in transit; browsers ignore on localhost
    SESSION_COOKIE_NAME      = "rsvd_session"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ── Cloudflare Turnstile (bot protection on public forms) ─────────────────
    # Set both vars to activate Turnstile.  When unset the widget is hidden and
    # server-side verification is skipped — dev/test previews work unchanged.
    TURNSTILE_SITE_KEY   = os.environ.get("TURNSTILE_SITE_KEY",   "")
    TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")

    # ── HICBC feature gate (disabled by default) ───────────────────────────────
    # HICBC routes (manual partner estimate + linked accounts) are registered
    # only when the gate is explicitly enabled.  Absent, empty, malformed or
    # false values keep the feature disabled.  It must never be inferred from
    # database rows, credentials, the environment name or any other flag.
    # Read at ``create_app()`` time via :func:`hicbc_enabled` so tests and
    # deployments can set it deliberately and deterministically.
    HICBC_ENABLED = _parse_hicbc_enabled(os.environ.get("HICBC_ENABLED", ""))
