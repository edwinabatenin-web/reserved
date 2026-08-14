"""
reserved/auth.py — Authentication module for Reserved V2.

Design
------
After sign-in via Clerk JS, the browser POSTs the short-lived Clerk session
token to POST /v2/auth/verify.  Flask verifies it against Clerk's JWKS
endpoint, creates or retrieves the DB user, and stores the internal user_id
in the HMAC-signed Flask session.

The @require_auth decorator reads the Flask session.  No JWT is verified on
every request — the Flask session cookie is tamper-proof (HMAC + SESSION_SECRET).

Demo login
----------
GET /v2/demo-login creates a fixed demo user session without going through
Clerk.  Only available when FLASK_ENV != 'production'.

Session keys (internal — do not depend on these in templates)
-------------------------------------------------------------
  _v2_user_id      int   — internal DB user id
  _v2_clerk_id     str   — Clerk user_id ("user_XXXXX") or demo sentinel
  _v2_email        str   — primary email
  _v2_display_name str   — display name
  _v2_is_demo      bool  — True for demo login sessions

Clerk JWKS verification
-----------------------
Requires PyJWT + cryptography packages (already in requirements.txt).
Only CLERK_PUBLISHABLE_KEY is needed — the Frontend API URL is decoded
from it to reach the JWKS endpoint.  CLERK_SECRET_KEY is NOT required
for this implementation (it would only be needed for Clerk Backend API
calls such as force-sign-out or user deletion, which are not used here).
If the env var is absent, verify_clerk_session_token() returns None
gracefully; only demo login is available.
"""
from __future__ import annotations

import os
from functools import wraps
from urllib.parse import urlparse

from flask import g, redirect, session, url_for


# ── Session key constants ─────────────────────────────────────────────────────

_SK_USER_ID      = "_v2_user_id"
_SK_CLERK_ID     = "_v2_clerk_id"
_SK_EMAIL        = "_v2_email"
_SK_DISPLAY_NAME = "_v2_display_name"
_SK_IS_DEMO      = "_v2_is_demo"

# Demo user identity
# Each browser session gets its own demo user (per-session UUID as suffix)
# so data is truly isolated across browsers. The prefix identifies demo rows
# in the users table; the suffix is stored in _SK_DEMO_SESSION_ID.
DEMO_CLERK_ID_PREFIX = "demo_session_"
DEMO_EMAIL_DOMAIN    = "demo.reserved.internal"
DEMO_DISPLAY         = "Demo User"

# Legacy constant — kept for existing DB rows from early WS5 testing.
# New demo logins use DEMO_CLERK_ID_PREFIX + uuid.
DEMO_CLERK_ID = "demo_user_reserved_ws5"
DEMO_EMAIL    = "demo@reserved.internal"

# Additional session key for demo session identity (preserved across re-logins
# in the same browser so the same demo user is returned)
_SK_DEMO_SESSION_ID = "_v2_demo_session_id"


# ── Session helpers ───────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Return True if the current request has a valid V2 session."""
    return session.get(_SK_USER_ID) is not None


def current_user_id() -> int | None:
    """Return the internal DB user_id from the session, or None."""
    return session.get(_SK_USER_ID)


def is_demo_session() -> bool:
    """Return True if this is a demo login session."""
    return bool(session.get(_SK_IS_DEMO))


def is_production_environment() -> bool:
    """
    Return True when the application is running in a production environment.

    Uses a dual-lock so that a misconfigured FLASK_ENV alone cannot enable
    sandbox-only behaviours if a live Clerk key is present:

      1. FLASK_ENV == "production"              (explicit environment label)
      2. CLERK_PUBLISHABLE_KEY starts with      (live Clerk key — present
         "pk_live_"                              once real auth is deployed)

    Either condition is sufficient.  Both must be absent for the application
    to be treated as a development/staging environment.

    This is the single authoritative production check in Reserved.  All
    places that previously inlined the dual-lock logic call this function.
    """
    flask_env = os.environ.get("FLASK_ENV", "development")
    clerk_key = os.environ.get("CLERK_PUBLISHABLE_KEY", "")
    return flask_env.lower() == "production" or clerk_key.startswith("pk_live_")


def set_user_session(
    user_id: int,
    clerk_id: str,
    email: str | None = None,
    display_name: str | None = None,
    is_demo: bool = False,
) -> None:
    """Write auth data into the Flask session."""
    session[_SK_USER_ID]      = user_id
    session[_SK_CLERK_ID]     = clerk_id
    session[_SK_EMAIL]        = email
    session[_SK_DISPLAY_NAME] = display_name
    session[_SK_IS_DEMO]      = is_demo
    session.modified = True


def clear_user_session() -> None:
    """
    Sign out: wipe the entire Flask session.

    Calling session.clear() rather than popping individual keys ensures
    no pre-login session state (Yapily OAuth state, legacy session key,
    demo session ID, CSRF token remnants) survives into the next session.
    The client will receive a fresh, empty signed cookie on the next request.
    """
    session.clear()
    session.modified = True


def load_user_into_g() -> None:
    """
    Populate Flask's g with the current user's data from the session.
    Called by @require_auth on every protected request.
    """
    g.user_id        = session.get(_SK_USER_ID)
    g.clerk_user_id  = session.get(_SK_CLERK_ID)
    g.user_email     = session.get(_SK_EMAIL)
    g.user_name      = session.get(_SK_DISPLAY_NAME)
    g.is_demo        = bool(session.get(_SK_IS_DEMO))


# ── Auth decorator ────────────────────────────────────────────────────────────

def require_auth(f):
    """
    Route decorator: ensure the user has an authenticated session.

    Non-production: unauthenticated visitors are silently started as a demo
    user (redirected to /v2/demo-login) so they land straight in the preview
    without a manual login step.

    Production: unauthenticated visitors are redirected to /v2/login as normal.

    On success, populates g.user_id, g.clerk_user_id, g.user_email,
    g.user_name, g.is_demo for use in route handlers.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            if is_production_environment():
                return redirect(url_for("v2.login"))
            return redirect(url_for("v2.demo_login"))
        load_user_into_g()
        return f(*args, **kwargs)
    return decorated


# ── Clerk JWKS verification ───────────────────────────────────────────────────

def _clerk_frontend_api_url() -> str | None:
    """
    Derive the Clerk Frontend API URL from CLERK_PUBLISHABLE_KEY.

    Publishable key format: pk_test_BASE64 or pk_live_BASE64
    where the base64 payload decodes to:
        https://XXXXXX.clerk.accounts.dev$    (development)
        https://clerk.YOURDOMAIN.com$         (production)

    Returns the URL (without trailing $), or None if the key is absent
    or cannot be parsed.
    """
    key = os.environ.get("CLERK_PUBLISHABLE_KEY", "").strip()
    if not key:
        return None
    try:
        import base64
        parts = key.split("_")
        if len(parts) < 3:
            return None
        encoded = parts[2]
        # Base64 padding
        padded = encoded + "=" * (4 - len(encoded) % 4)
        decoded = base64.b64decode(padded).decode("utf-8").rstrip("$")
        if decoded.startswith("https://"):
            return decoded
    except Exception:
        pass
    return None


def _clerk_authorized_parties() -> tuple[str, ...]:
    """Return configured browser origins accepted in Clerk's ``azp`` claim."""
    raw = os.environ.get("CLERK_AUTHORIZED_PARTIES", "")
    if not raw.strip():
        raw = os.environ.get("AUTH_PUBLIC_ORIGIN", "")
    parties: list[str] = []
    for item in raw.split(","):
        origin = item.strip().rstrip("/")
        parsed = urlparse(origin)
        local_http = parsed.scheme == "http" and parsed.hostname in {
            "localhost", "127.0.0.1", "::1",
        }
        if (
            (parsed.scheme == "https" or local_http)
            and parsed.netloc
            and parsed.path in {"", "/"}
            and not parsed.params
            and not parsed.query
            and not parsed.fragment
            and parsed.username is None
            and parsed.password is None
        ):
            parties.append(origin)
    return tuple(dict.fromkeys(parties))


def _clerk_claims_are_accepted(
    claims: dict,
    *,
    frontend_api: str,
    authorized_parties: tuple[str, ...],
    audience: str | None = None,
) -> bool:
    """Apply Reserved's instance and browser-origin boundary to verified claims.

    Clerk documents ``iss`` as the instance Frontend API URL and ``azp`` as the
    browser Origin.  Clerk also documents that ``azp`` can be absent; when it is
    present it must match Reserved's configured allowlist.  ``aud`` is not a
    default Clerk session-token claim, so it is checked only when Reserved has
    explicitly configured a custom audience.
    """
    if claims.get("iss", "").rstrip("/") != frontend_api.rstrip("/"):
        return False
    if not claims.get("sub") or not claims.get("sid"):
        return False
    azp = claims.get("azp")
    if azp is not None and azp.rstrip("/") not in authorized_parties:
        return False
    if audience is not None:
        token_audience = claims.get("aud")
        if isinstance(token_audience, str):
            accepted = token_audience == audience
        elif isinstance(token_audience, (list, tuple)):
            accepted = audience in token_audience
        else:
            accepted = False
        if not accepted:
            return False
    return True


def verify_clerk_session_token(session_token: str) -> dict | None:
    """
    Verify a Clerk short-lived session token (RS256 JWT) and return its claims.

    Returns None if:
    - CLERK_PUBLISHABLE_KEY is not set
    - The token signature is invalid or expired
    - Any other error occurs during verification
    - no authorised browser origin is configured
    - issuer, authorised-party, subject or session claims fail validation

    Successful claims dict includes:
        sub         — Clerk user ID (e.g. "user_2abc…")
        email       — primary email (if included in token)
        first_name  — first name (if included in token)
        last_name   — last name (if included in token)
        exp         — expiry timestamp

    Clerk session tokens do not include ``aud`` by default. Audience checking
    is enabled only when CLERK_JWT_AUDIENCE identifies a custom token audience.
    """
    frontend_api = _clerk_frontend_api_url()
    if not frontend_api:
        return None
    authorized_parties = _clerk_authorized_parties()
    if not authorized_parties:
        # Do not accept tokens until the permitted browser origins have been
        # explicitly configured.  A valid signature alone is insufficient.
        return None
    audience = os.environ.get("CLERK_JWT_AUDIENCE", "").strip() or None
    try:
        import jwt
        client = jwt.PyJWKClient(f"{frontend_api}/.well-known/jwks.json")
        signing_key = client.get_signing_key_from_jwt(session_token)
        claims = jwt.decode(
            session_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=frontend_api,
            audience=audience,
            options={
                "verify_aud": audience is not None,
                "require": ["exp", "nbf", "iss", "sub", "sid"],
            },
        )
        if not _clerk_claims_are_accepted(
            claims,
            frontend_api=frontend_api,
            authorized_parties=authorized_parties,
            audience=audience,
        ):
            return None
        return claims
    except Exception:
        return None
