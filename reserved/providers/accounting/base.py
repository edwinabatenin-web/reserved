from abc import ABC, abstractmethod

from .contracts import ProviderCapabilities, SyncPage, SyncStatus


class AccountingProvider(ABC):
    """Normalised interface for FreeAgent, Xero and QuickBooks.

    The concrete providers are currently disabled placeholders; any future
    implementation must emit ``SourceObservation`` and ``SemanticAdapterResult``
    for the provider-neutral canonical accounting pipeline.

    `credential_reference` is an opaque identifier for encrypted server-side
    tokens. Raw refresh/access tokens must not cross this interface in logs or
    persisted sync records.
    """

    capabilities = ProviderCapabilities()

    @abstractmethod
    def authorisation_url(self, user_id: str, redirect_uri: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        raise NotImplementedError

    def disconnect(self, credential_reference: str) -> None:
        """Revoke provider access where supported and delete stored tokens."""
        raise NotImplementedError

    def refresh_authorisation(self, credential_reference: str) -> None:
        raise NotImplementedError

    def list_businesses(self, credential_reference: str) -> tuple[dict, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_invoices(self, credential_reference: str) -> list[dict]:
        """Legacy list boundary using an opaque server-side token reference."""
        raise NotImplementedError

    def sync_invoices(self, credential_reference: str, business_id: str,
                      cursor: str | None = None) -> SyncPage:
        raise NotImplementedError

    def sync_entries(self, credential_reference: str, business_id: str,
                     cursor: str | None = None) -> SyncPage:
        raise NotImplementedError

    def get_sync_status(self, business_id: str) -> SyncStatus:
        raise NotImplementedError
