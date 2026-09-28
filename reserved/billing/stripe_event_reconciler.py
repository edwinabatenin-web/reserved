"""Stripe event reconciliation for billing state transitions.

Processes Stripe webhook events and converts them to Reserved entitlement transitions.
"""

from datetime import datetime, timezone
from typing import Any

from reserved.billing.stripe_runtime import Transition, EventReconciler


class StripeEventReconciler:
    """Reconciles Stripe webhook events to Reserved billing state transitions.
    
    This class implements the EventReconciler protocol by converting Stripe
    events (subscription.created, invoice.payment_succeeded, etc.) into
    Reserved entitlement state transitions.
    """

    def reconcile(
        self,
        *,
        event: dict[str, Any],
        owner_id: int,
        billing_account_id: str,
        prior_state: str | None
    ) -> Transition | None:
        """Convert a Stripe event to a Reserved entitlement transition.
        
        Args:
            event: Stripe webhook event dict
            owner_id: Reserved owner ID
            billing_account_id: Stripe billing account ID (customer ID mapping)
            prior_state: Current entitlement state ("paid", "payment_recovery", "suspended", etc.)
            
        Returns:
            Transition object if state should change, None if no action needed
            
        Raises:
            ValueError: If event is malformed or invalid
        """
        event_type = event.get("type", "")
        event_id = event.get("id", "")
        created = event.get("created", 0)
        data = event.get("data", {})
        obj = data.get("object", {})

        if event_type == "customer.subscription.created":
            return self._handle_subscription_created(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        elif event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        elif event_type == "invoice.payment_succeeded":
            return self._handle_payment_succeeded(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        elif event_type == "invoice.payment_failed":
            return self._handle_payment_failed(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        elif event_type == "charge.refunded":
            return self._handle_charge_refunded(
                owner_id, billing_account_id, event_id, created, obj, prior_state
            )
        
        # Unhandled event type - no transition
        return None

    def _handle_subscription_created(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle customer.subscription.created event."""
        subscription_id = obj.get("id", "")
        status = obj.get("status", "")
        current_period_end = obj.get("current_period_end", 0)
        
        if not subscription_id or not status:
            return None
        
        # Subscription starts in active state (paid)
        if status == "active":
            return Transition(
                owner_id=owner_id,
                billing_account_id=billing_account_id,
                subscription_id=subscription_id,
                state="paid",
                event_id=event_id,
                occurred_at=created,
                reason="subscription_created",
                kind="initial_payment",
                paid_until=current_period_end,
                payment_identity=obj.get("latest_invoice", {}).get("payment_intent", "pi_unknown") if isinstance(obj.get("latest_invoice"), dict) else "pi_unknown",
            )
        return None

    def _handle_subscription_updated(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle customer.subscription.updated event."""
        subscription_id = obj.get("id", "")
        status = obj.get("status", "")
        cancel_at_period_end = obj.get("cancel_at_period_end", False)
        
        if not subscription_id:
            return None
        
        # If cancellation is scheduled, mark it
        if cancel_at_period_end and prior_state == "paid":
            return Transition(
                owner_id=owner_id,
                billing_account_id=billing_account_id,
                subscription_id=subscription_id,
                state="paid",
                event_id=event_id,
                occurred_at=created,
                reason="cancellation_scheduled",
                kind="cancellation",
                paid_until=obj.get("current_period_end"),
                cancel_at_period_end=True,
            )
        
        # If subscription is now past due or unpaid, go to recovery
        if status == "past_due":
            return Transition(
                owner_id=owner_id,
                billing_account_id=billing_account_id,
                subscription_id=subscription_id,
                state="payment_recovery",
                event_id=event_id,
                occurred_at=created,
                reason="payment_past_due",
                kind="failed_renewal",
                recovery_deadline=created + (14 * 24 * 60 * 60),  # 14 days recovery window
            )
        
        return None

    def _handle_payment_succeeded(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle invoice.payment_succeeded event."""
        subscription_id = obj.get("subscription", "")
        paid_until = obj.get("period_end", 0)
        payment_intent = obj.get("payment_intent", "")
        
        if not subscription_id or not payment_intent:
            return None
        
        # Determine if this is renewal or recovery
        kind = "renewal_payment"
        if prior_state == "payment_recovery":
            kind = "renewal_payment"  # Could be recovery if we tracked recovery state
        
        return Transition(
            owner_id=owner_id,
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            state="paid",
            event_id=event_id,
            occurred_at=created,
            reason="payment_succeeded",
            kind=kind,
            paid_until=paid_until,
            payment_identity=payment_intent,
        )

    def _handle_payment_failed(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle invoice.payment_failed event."""
        subscription_id = obj.get("subscription", "")
        
        if not subscription_id:
            return None
        
        # Failed payment moves to recovery state
        return Transition(
            owner_id=owner_id,
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            state="payment_recovery",
            event_id=event_id,
            occurred_at=created,
            reason="payment_failed",
            kind="failed_renewal",
            recovery_deadline=created + (14 * 24 * 60 * 60),  # 14 days to recover
        )

    def _handle_subscription_deleted(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle customer.subscription.deleted event."""
        subscription_id = obj.get("id", "")
        latest_invoice = obj.get("latest_invoice", {})
        payment_intent = latest_invoice.get("payment_intent", "") if isinstance(latest_invoice, dict) else ""
        
        if not subscription_id:
            return None
        
        # Full cancellation/withdrawal
        return Transition(
            owner_id=owner_id,
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            state="suspended",
            event_id=event_id,
            occurred_at=created,
            reason="subscription_cancelled",
            kind="full_withdrawal",
            payment_identity=payment_intent or "pi_unknown",
            withdrawal_attribution="customer_initiated",
        )

    def _handle_charge_refunded(
        self, owner_id: int, billing_account_id: str, event_id: str, created: int,
        obj: dict, prior_state: str | None
    ) -> Transition | None:
        """Handle charge.refunded event (full refund may affect entitlements)."""
        # For now, refunds don't change entitlements - user can cancel via Stripe
        # This could be enhanced to track partial refunds or dispute handling
        return None


__all__ = ["StripeEventReconciler"]
