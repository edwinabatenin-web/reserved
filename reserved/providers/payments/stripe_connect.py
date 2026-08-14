class StripeConnectClient:
    """
    Production integration boundary.

    No payment should be initiated from the preview application. Add the reviewed
    Stripe implementation only after authentication, reconciliation and webhook
    verification are complete.
    """

    def create_onboarding_link(self, user_id: str) -> str:
        raise NotImplementedError("Stripe Connect is disabled in local preview mode.")
