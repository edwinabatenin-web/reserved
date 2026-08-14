"""Normalised accounting connector contracts.

Provider adapters translate external records into these stable shapes. Access
and refresh tokens are deliberately absent: callers pass opaque credential
references resolved by a server-side secret/token store.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class AccountingProviderName(str, Enum):
    FREEAGENT = "freeagent"
    XERO = "xero"
    QUICKBOOKS = "quickbooks"


@dataclass(frozen=True)
class ProviderCapabilities:
    businesses: bool = True
    invoices: bool = True
    expenses: bool = True
    bank_transactions: bool = True
    categories: bool = True
    webhooks: bool = False


@dataclass(frozen=True)
class AccountingBusiness:
    provider: AccountingProviderName
    external_business_id: str
    name: str
    currency: str
    country_code: str | None = None


@dataclass(frozen=True)
class AccountingInvoice:
    provider: AccountingProviderName
    external_business_id: str
    external_invoice_id: str
    invoice_number: str | None
    issue_date: date
    due_date: date | None
    currency: str
    gross_amount: Decimal
    net_amount: Decimal | None
    tax_amount: Decimal | None
    amount_paid: Decimal
    status: str
    contact_name: str | None = None
    paid_date: date | None = None
    source_updated_at: datetime | None = None

    @property
    def outstanding_amount(self) -> Decimal:
        return max(Decimal("0"), self.gross_amount - self.amount_paid)


@dataclass(frozen=True)
class AccountingEntry:
    provider: AccountingProviderName
    external_business_id: str
    external_entry_id: str
    occurred_on: date
    currency: str
    amount: Decimal
    direction: str
    entry_type: str
    description: str | None = None
    category_id: str | None = None
    invoice_id: str | None = None
    source_updated_at: datetime | None = None


@dataclass(frozen=True)
class SyncPage:
    records: tuple[object, ...]
    next_cursor: str | None
    source_watermark: datetime | None = None


@dataclass(frozen=True)
class SyncStatus:
    provider: AccountingProviderName
    external_business_id: str
    last_success_at: datetime | None
    next_cursor: str | None
    last_error_code: str | None = None
    requires_reauthorisation: bool = False

