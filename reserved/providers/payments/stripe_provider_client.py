"""Production Stripe provider client for checkout and portal creation."""

import os
import stripe
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reserved.billing.stripe_runtime import ProviderClient


class StripeProviderClient:
    """Implements the ProviderClient protocol for Stripe payment processing.
    
    This client handles:
    - Creating checkout sessions for subscription initiation
    - Creating billing portal sessions for customer management
    - Delegating to stripe.Checkout.Session and stripe.BillingPortal.Session
    """

    def __init__(self, stripe_api_key: str = None):
        """Initialize the Stripe provider client.
        
        Args:
            stripe_api_key: Optional Stripe secret key. If not provided,
                          uses STRIPE_SECRET_KEY environment variable.
        """
        if stripe_api_key:
            stripe.api_key = stripe_api_key
        elif not stripe.api_key:
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable not set")

    def create_checkout(
        self,
        *,
        owner_id: int,
        billing_account_id: str,
        plan_key: str,
        price_id: str,
        idempotency_key: str
    ) -> str:
        """Create a Stripe Checkout Session for subscription purchase.
        
        Args:
            owner_id: Reserved owner ID for tracking
            billing_account_id: Billing account identifier
            plan_key: Internal plan key (e.g., "standard_monthly")
            price_id: Stripe price ID from price_bindings
            idempotency_key: Unique key for request deduplication
            
        Returns:
            str: Stripe checkout URL for customer redirect
            
        Raises:
            stripe.error.StripeError: On Stripe API failures
        """
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=f"https://reservedtax.com/v2/billing/success",
            cancel_url=f"https://reservedtax.com/v2/billing/cancelled",
            client_reference_id=str(owner_id),
            metadata={
                "billing_account_id": billing_account_id,
                "plan_key": plan_key,
                "owner_id": str(owner_id),
            },
            idempotency_key=idempotency_key,
        )
        return checkout_session.url

    def create_portal(
        self,
        *,
        owner_id: int,
        billing_account_id: str,
        idempotency_key: str
    ) -> str:
        """Create a Stripe Customer Portal session.
        
        Allows customers to manage their subscription, update payment methods,
        and view billing history without leaving Reserved.
        
        Args:
            owner_id: Reserved owner ID
            billing_account_id: Billing account identifier (Stripe customer ID)
            idempotency_key: Unique key for request deduplication
            
        Returns:
            str: Stripe customer portal URL
            
        Raises:
            stripe.error.StripeError: On Stripe API failures
        """
        # The billing_account_id should be mapped to a Stripe customer ID
        # in the repository or a separate customer mapping table.
        # For now, we assume it's the Stripe customer ID directly.
        portal_session = stripe.billing_portal.Session.create(
            customer=billing_account_id,
            return_url="https://reservedtax.com/v2/account/billing",
        )
        return portal_session.url
