from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .contracts import AccountingInvoice, AccountingProviderName


def _required(payload: dict, key: str):
    value = payload.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required canonical invoice field: {key}")
    return value


def _date(value, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc


def _optional_date(value, field: str) -> date | None:
    return None if value in (None, "") else _date(value, field)


def _amount(value, field: str) -> Decimal:
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


def normalise_invoice(*, provider: str, payload: dict) -> AccountingInvoice:
    """
    Convert provider-specific data into Reserved's canonical invoice shape.

    Required canonical inputs are external_business_id, external_invoice_id,
    issue_date, currency, gross_amount and status. Optional inputs include
    invoice_number, due_date, net_amount, tax_amount, amount_paid, contact_name,
    paid_date and source_updated_at. ``outstanding_amount`` is derived by the
    canonical ``AccountingInvoice`` contract rather than accepted from an
    untrusted provider payload.
    """
    provider_name = AccountingProviderName(provider)
    gross = _amount(_required(payload, "gross_amount"), "gross_amount")
    paid = _amount(payload.get("amount_paid", 0), "amount_paid")
    if paid > gross:
        raise ValueError("amount_paid cannot exceed gross_amount")
    updated = payload.get("source_updated_at")
    if updated and not isinstance(updated, datetime):
        try:
            updated = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid source_updated_at") from exc
    return AccountingInvoice(
        provider=provider_name,
        external_business_id=str(_required(payload, "external_business_id")),
        external_invoice_id=str(_required(payload, "external_invoice_id")),
        invoice_number=(str(payload["invoice_number"]) if payload.get("invoice_number") else None),
        issue_date=_date(_required(payload, "issue_date"), "issue_date"),
        due_date=_optional_date(payload.get("due_date"), "due_date"),
        currency=str(_required(payload, "currency")).upper(),
        gross_amount=gross,
        net_amount=(_amount(payload["net_amount"], "net_amount") if payload.get("net_amount") is not None else None),
        tax_amount=(_amount(payload["tax_amount"], "tax_amount") if payload.get("tax_amount") is not None else None),
        amount_paid=paid,
        status=str(_required(payload, "status")),
        contact_name=payload.get("contact_name"),
        paid_date=_optional_date(payload.get("paid_date"), "paid_date"),
        source_updated_at=updated,
    )
