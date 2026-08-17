import logging
import os

from flask import Flask, render_template, request as _req, session as _session
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import is_production_environment
from .config import Config, hicbc_enabled
from .database import init_db
from .extensions import csrf
from .web.routes import web
from .web.founder import founder
from .web.hicbc import hicbc
from .web.v2 import v2
from .api.routes import api

log = logging.getLogger(__name__)


def create_app() -> Flask:
    # ── Logging ───────────────────────────────────────────────────────────────
    _log_level = logging.DEBUG if os.environ.get("FLASK_DEBUG") == "1" else logging.INFO
    logging.basicConfig(
        level=_log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )

    # ── Production SESSION_SECRET enforcement ─────────────────────────────────
    if is_production_environment() and not os.environ.get("SESSION_SECRET"):
        log.critical(
            "Startup aborted: SESSION_SECRET is not set in a production environment. "
            "Set the SESSION_SECRET environment variable to a strong random value "
            "before starting the application in production."
        )
        raise RuntimeError(
            "SESSION_SECRET must be set in production. "
            "Refusing to start with an insecure fallback session key."
        )

    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Proxy trust ───────────────────────────────────────────────────────────
    # Replit's infrastructure places one reverse proxy in front of the app.
    # ProxyFix rewrites request.remote_addr (and scheme/host) from the
    # X-Forwarded-For / X-Forwarded-Proto / X-Forwarded-Host headers so that
    # rate limiters, logging, and IP-keyed logic see the real client IP rather
    # than the proxy's address.  x_for=1 trusts exactly one hop.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(founder)
    app.register_blueprint(v2)  # V2 preview — not linked from public nav
    if hicbc_enabled():
        app.register_blueprint(hicbc)  # October v1 HICBC — feature-gated

    # ── Template globals ──────────────────────────────────────────────────────
    # Expose canonical_base and turnstile_site_key to every template so that
    # OG/canonical tags and Turnstile widgets render correctly without
    # per-route boilerplate.
    @app.context_processor
    def inject_template_globals():
        canonical = os.environ.get("CANONICAL_BASE_URL", "").rstrip("/")
        if not canonical:
            try:
                scheme = "https" if is_production_environment() else _req.scheme
                canonical = f"{scheme}://{_req.host}"
            except RuntimeError:
                canonical = ""
        return {
            "canonical_base": canonical,
            "turnstile_site_key": os.environ.get("TURNSTILE_SITE_KEY", ""),
        }

    # ── Favicon ───────────────────────────────────────────────────────────────
    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.ico")

    # ── Security headers ──────────────────────────────────────────────────────
    # Applied to every response.  Values are deliberately permissive for
    # 'unsafe-inline' on scripts/styles because the app uses inline handlers
    # and <style> blocks throughout.  Tightening CSP further is a separate
    # architectural task once nonces or hash-based CSP can be introduced.
    @app.after_request
    def set_security_headers(response):
        h = response.headers

        # Prevent MIME-type sniffing
        h.setdefault("X-Content-Type-Options", "nosniff")

        # Prevent clickjacking
        h.setdefault("X-Frame-Options", "SAMEORIGIN")

        # Reduce referrer leakage
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Disable browser features not needed by the app
        h.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )

        # HSTS — only in production where HTTPS is guaranteed
        if is_production_environment():
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        # Content Security Policy — permissive baseline that doesn't break
        # inline scripts/styles.  'unsafe-inline' is required until the
        # codebase is refactored to use nonces; frame-ancestors blocks
        # embedding in foreign pages regardless of X-Frame-Options support.
        csp_parts = [
            "default-src 'self'",
            # app.js, charts.js + Clerk component bundle + Turnstile widget
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://*.clerk.accounts.dev https://clerk.reserved.fyi https://challenges.cloudflare.com",
            # inline styles + <style> blocks
            "style-src 'self' 'unsafe-inline'",
            # favicons and chart images
            "img-src 'self' data: https:",
            # web fonts loaded from /static/
            "font-src 'self' data:",
            # API calls + Clerk JWKS endpoint
            "connect-src 'self' https://*.clerk.accounts.dev https://clerk.reserved.fyi",
            # no plugins
            "object-src 'none'",
            # prevent base-tag injection
            "base-uri 'self'",
            # submissions must remain on this origin
            "form-action 'self'",
            # constrain less common fetch contexts explicitly rather than
            # allowing them to inherit a future broader default
            "manifest-src 'self'",
            "media-src 'self'",
            "worker-src 'self'",
            # stronger clickjacking protection than X-Frame-Options;
            # Cloudflare Turnstile renders its challenge inside an iframe
            "frame-src https://challenges.cloudflare.com",
            "frame-ancestors 'self'",
        ]
        h.setdefault("Content-Security-Policy", "; ".join(csp_parts))

        # Authenticated, sign-in and founder responses can contain account,
        # financial or submission data. Prevent browser history and shared
        # intermediaries from retaining reusable copies. Applying this to the
        # complete route prefixes also covers login/error responses before a
        # session exists and future protected endpoints added beneath them.
        has_sensitive_session = (
            _session.get("_v2_user_id") is not None
            or _session.get("_founder_authed") is True
        )
        if has_sensitive_session or _req.path.startswith(("/v2/", "/founder")):
            h["Cache-Control"] = "no-store, max-age=0"
            h["Pragma"] = "no-cache"
            h["Expires"] = "0"
            h.add("Vary", "Cookie")

        return response

    # ── Custom error handlers ─────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(exc):
        log.info("400 Bad Request: %s", exc)
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(exc):
        log.warning("403 Forbidden: %s", exc)
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(exc):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(exc):
        log.error("500 Internal Server Error: %s", exc, exc_info=True)
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def too_many_requests(exc):
        return render_template("errors/403.html"), 429  # reuse access-denied page

    # ── DB init ───────────────────────────────────────────────────────────────
    with app.app_context():
        init_db()

    return app
