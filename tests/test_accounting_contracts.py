from datetime import date
from decimal import Decimal

from reserved.providers.accounting.contracts import AccountingProviderName
from reserved.providers.accounting.normalisation import normalise_invoice


def valid_invoice():
    return {
        "external_business_id": "synthetic-business",
        "external_invoice_id": "synthetic-invoice",
        "invoice_number": "INV-001",
        "issue_date": "2026-08-01",
        "due_date": "2026-08-31",
        "currency": "gbp",
        "gross_amount": "120.00",
        "net_amount": "100.00",
        "tax_amount": "20.00",
        "amount_paid": "50.00",
        "status": "PART_PAID",
    }


def test_invoice_is_normalised_to_provider_neutral_contract():
    result = normalise_invoice(provider="xero", payload=valid_invoice())
    assert result.provider is AccountingProviderName.XERO
    assert result.issue_date == date(2026, 8, 1)
    assert result.currency == "GBP"
    assert result.outstanding_amount == Decimal("70.00")


def test_missing_business_identity_fails_closed():
    payload = valid_invoice()
    payload.pop("external_business_id")
    try:
        normalise_invoice(provider="freeagent", payload=payload)
    except ValueError as exc:
        assert "external_business_id" in str(exc)
    else:
        raise AssertionError("Business identity is required")


def test_paid_amount_above_gross_is_rejected():
    payload = valid_invoice()
    payload["amount_paid"] = "121"
    try:
        normalise_invoice(provider="quickbooks", payload=payload)
    except ValueError as exc:
        assert "cannot exceed" in str(exc)
    else:
        raise AssertionError("Invalid provider data must be rejected")

