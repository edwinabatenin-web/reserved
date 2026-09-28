"""Bootstrap Stripe billing runtime for Flask application deployment.

This module initializes the complete Stripe billing runtime with all
dependencies: Stripe API client, webhook signature verification,
event reconciliation, and price bindings.

Usage in production:

    from deploy.initialize_billing import create_billing_runtime
    from reserved import create_app
    
    billing_runtime = create_billing_runtime()
    app = create_app(billing_runtime=billing_runtime)
"""

import os
import logging
from datetime import datetime, timezone

import stripe

from reserved.billing.stripe_runtime import (
    StripeBillingRuntime,
    SQLiteBillingRuntimeRepository,
    HostedUrlPolicy,
    PriceBinding,
    BillingRuntimeError,
)
from reserved.billing.price_bindings import PRICE_BINDINGS
from reserved.billing.stripe_event_reconciler import StripeEventReconciler
from reserved.providers.payments.stripe_provider_client import StripeProviderClient

log = logging.getLogger(__name__)


def create_billing_runtime() -> StripeBillingRuntime:
    """Initialize and return a complete Stripe billing runtime.
    
    This function:
    1. Validates all required environment variables are set
    2. Initializes the Stripe API client with production credentials
    3. Creates the billing event repository with SQLite backing
    4. Instantiates the provider client for Stripe API calls
    5. Sets up webhook signature verification
    6. Creates the event reconciler for state transitions
    7. Configures hosted URL policy for checkout/portal redirects
    8. Composes and returns the complete StripeBillingRuntime
    
    Returns:
        StripeBillingRuntime: Fully initialized billing runtime ready for use
        
    Raises:
        ValueError: If required environment variables are missing
        BillingRuntimeError: If runtime composition fails validation
    """
    
    # ─── Environment Variable Validation ──────────────────────────────────
    stripe_secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_secret_key:
        raise ValueError(
            "STRIPE_SECRET_KEY environment variable not set. "
            "This must be set to your Stripe production secret key (sk_live_...)"
        )
    
    stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not stripe_webhook_secret:
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET environment variable not set. "
            "This must be set to your webhook signing secret (whsec_...) "
            "from the Stripe dashboard."
        )
    
    billing_database_path = os.environ.get(
        "BILLING_DATABASE_PATH",
        "/var/lib/reserved/billing.db"
    )
    
    log.info(f"Initializing Stripe billing runtime with database at {billing_database_path}")
    
    # ─── Stripe API Client Initialization ──────────────────────────────────
    stripe.api_key = stripe_secret_key
    log.debug("Stripe API client configured with production secret key")
    
    # ─── Billing Repository ──────────────────────────────────────────────────
    try:
        repository = SQLiteBillingRuntimeRepository(path=billing_database_path)
        log.info("Billing repository initialized")
    except Exception as e:
        raise BillingRuntimeError(f"Failed to initialize billing repository: {e}")
    
    # ─── Stripe Provider Client ──────────────────────────────────────────────
    try:
        provider_client = StripeProviderClient(stripe_api_key=stripe_secret_key)
        log.debug("Stripe provider client initialized")
    except Exception as e:
        raise BillingRuntimeError(f"Failed to initialize provider client: {e}")
    
    # ─── Webhook Signature Verification ──────────────────────────────────────
    verify_signature = _create_stripe_signature_verifier(stripe_webhook_secret)
    log.debug("Webhook signature verifier configured")
    
    # ─── Event Reconciler ────────────────────────────────────────────────────
    reconciler = StripeEventReconciler()
    log.debug("Event reconciler initialized")
    
    # ─── Hosted URL Policy ───────────────────────────────────────────────────
    # These are the official Stripe-owned domains where checkout and portal
    # sessions redirect. We explicitly allow only these hosts for security.
    hosted_url_policy = HostedUrlPolicy(
        checkout_hosts=("checkout.stripe.com",),
        portal_hosts=("billing.stripe.com",)
    )
    log.debug("Hosted URL policy configured")
    
    # ─── Clock (for testing time-dependent logic) ───────────────────────────
    def utc_clock():
        """Return current UTC time for billing reconciliation."""
        return datetime.now(timezone.utc)
    
    # ─── Runtime Composition ────────────────────────────────────────────────
    try:
        billing_runtime = StripeBillingRuntime(
            repository=repository,
            provider=provider_client,
            verify_signature=verify_signature,
            reconciler=reconciler,
            price_bindings=tuple(PRICE_BINDINGS),
            hosted_url_policy=hosted_url_policy,
            clock=utc_clock,
        )
        log.info("Stripe billing runtime successfully initialized")
        return billing_runtime
    except Exception as e:
        log.error(f"Failed to compose billing runtime: {e}")
        raise


def _create_stripe_signature_verifier(signing_secret: str):
    """Create a webhook signature verification function.
    
    Args:
        signing_secret: Stripe webhook signing secret (whsec_...)
        
    Returns:
        Callable: Function that verifies and returns the webhook event dict
        
    Raises:
        ValueError: If signing_secret is invalid
    """
    if not signing_secret or not signing_secret.startswith("whsec_"):
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET must start with 'whsec_' and be non-empty"
        )
    
    def verify_signature(payload: bytes, signature_header: str) -> bool:
        """Verify Stripe webhook signature using the signing secret.
        
        Args:
            payload: Raw webhook payload bytes
            signature_header: Stripe-Signature header value
            
        Returns:
            bool: True if signature is valid
            
        Raises:
            ValueError: If signature verification fails
        """
        if not signature_header:
            raise ValueError("Stripe-Signature header is missing")
        
        try:
            # This constructs the event and verifies the signature.
            # Raises stripe.error.SignatureVerificationError if invalid.
            stripe.Webhook.construct_event(
                payload,
                signature_header,
                signing_secret
            )
            return True
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            log.warning(f"Webhook signature verification failed: {e}")
            return False
    
    return verify_signature


if __name__ == "__main__":
    # For testing: initialize billing runtime in isolation
    import sys
    
    try:
        runtime = create_billing_runtime()
        print("✓ Billing runtime initialized successfully")
        print(f"  - Database: {runtime.repository.path}")
        print(f"  - Price bindings: {len(runtime.price_bindings)} plans configured")
        print(f"  - Webhook policy: {runtime.hosted_url_policy.checkout_hosts} (checkout), {runtime.hosted_url_policy.portal_hosts} (portal)")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Failed to initialize billing runtime: {e}", file=sys.stderr)
        sys.exit(1)
