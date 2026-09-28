"""Production entry point for Reserved Flask application with Stripe billing.

This script initializes the complete Stripe billing runtime and starts
the Flask application in production mode.

To run:
    python run_production.py

Or with gunicorn (recommended for production):
    gunicorn -w 4 -b 0.0.0.0:8000 run_production:app
"""

import os
import sys
import logging

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("FLASK_DEBUG") == "1" else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Billing Runtime Initialization ──────────────────────────────────────────
try:
    from deploy import create_billing_runtime
    from reserved import create_app
    
    log.info("Initializing Stripe billing runtime...")
    billing_runtime = create_billing_runtime()
    log.info("✓ Billing runtime initialized successfully")
    
    # Create Flask app with billing runtime injected
    app = create_app(billing_runtime=billing_runtime)
    log.info("✓ Flask application created with billing runtime")
    
except ImportError as e:
    log.error(f"Failed to import deployment modules: {e}")
    log.info("Falling back to app without billing (development mode)")
    from reserved import create_app
    app = create_app()
    
except ValueError as e:
    log.error(f"Environment variable error: {e}")
    log.error("Billing will be unavailable - check environment variables:")
    log.error("  - STRIPE_SECRET_KEY (sk_live_...)")
    log.error("  - STRIPE_WEBHOOK_SECRET (whsec_...)")
    from reserved import create_app
    app = create_app()
    
except Exception as e:
    log.error(f"Failed to initialize billing runtime: {e}", exc_info=True)
    log.warning("Starting application without billing runtime")
    from reserved import create_app
    app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    log.info(f"Starting Reserved Flask application on port {port}")
    log.info(f"Debug mode: {debug_mode}")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
    )
