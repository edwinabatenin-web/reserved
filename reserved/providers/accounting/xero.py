from .base import AccountingProvider


class XeroProvider(AccountingProvider):
    """
    Documented placeholder for the Xero integration.

    Launch scope:
    - OAuth connection card and demand validation.
    Post-launch scope:
    - secure OAuth callback and token refresh;
    - organisation selection;
    - invoice and payment synchronisation;
    - canonical invoice normalisation;
    - bank-to-invoice confidence matching.
    """

    def authorisation_url(self, user_id: str, redirect_uri: str) -> str:
        raise NotImplementedError("Xero OAuth is not enabled in this release.")

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        raise NotImplementedError("Xero OAuth is not enabled in this release.")

    def list_invoices(self, credential_reference: str) -> list[dict]:
        raise NotImplementedError("Xero invoice sync is not enabled in this release.")
