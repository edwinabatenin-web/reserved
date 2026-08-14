from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CanonicalInvoice:
    provider: str
    external_invoice_id: str
    invoice_number: str
    customer_name: str
    issue_date: str
    due_date: str | None
    gross_amount: Decimal
    net_amount: Decimal
    vat_amount: Decimal
    amount_paid: Decimal
    outstanding_amount: Decimal
    currency: str
    status: str
    paid_date: str | None = None
