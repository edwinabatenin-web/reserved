"""Early W8 synthetic assurance across already-integrated workstream boundaries.

These tests deliberately do not create a production adapter between accounting
evidence and annual tax.  That boundary remains separately gated.  They exercise
provider safeguards and W1/W2 cash-and-presentation safeguards separately on the
same integrated lineage; they do not prove a cross-workstream handoff or that
provider assertions have been converted into tax or presentation facts.
"""
from dataclasses import replace
from decimal import Decimal

import pytest

from reserved.providers.accounting.normalisation import derive_settlement_state
from reserved.providers.accounting.contracts import SettlementState
from reserved.providers.accounting.quickbooks_invoice_payment_adapter import (
    QuickBooksAdapterError,
    adapt_payment,
)
from reserved.services.w2_customer_language import (
    PresentationStatus,
    present_w2_customer_language,
)
from tests.test_quickbooks_invoice_payment_adapter import (
    BINDING,
    mapped_invoice,
    observe_p,
)
from tests.test_w2_customer_language_contract import presentation_input


def test_provider_evidence_and_cash_presentation_coexist_as_separate_safe_boundaries():
    """Provider and W1/W2 contracts remain safe when exercised on one lineage."""
    invoice = mapped_invoice()
    payment = adapt_payment(
        observe_p(), invoice=invoice, binding=BINDING, import_run_id="w8-synthetic",
    )

    assert invoice.document.provenance.identity.provider.value == "quickbooks"
    assert invoice.document.provenance.source_record_digest
    assert payment.allocation.document_id == invoice.document.document_id
    assert payment.allocation.amount == Decimal("50.00")
    assert payment.payment.money.original_amount == Decimal("80.00")
    assert payment.payment.unapplied_amount == Decimal("30.00")
    assert derive_settlement_state(
        invoice.document,
        (payment.allocation,),
        {payment.payment.payment_id: payment.payment},
    ) is SettlementState.PART_PAID

    facts = presentation_input()
    view = present_w2_customer_language(facts)
    assert view.safe_to_present
    assert facts.status is PresentationStatus.READY
    assert "does not authorise a payment or transfer" in view.no_payment_authority


def test_provider_uncertainty_fails_before_canonical_or_customer_boundaries():
    """A provider arithmetic conflict cannot be carried forward as usable fact."""
    raw = {
        "Id": "invoice-unsafe", "SyncToken": "1",
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-08-10", "DueDate": "2026-09-10",
        "CurrencyRef": {"value": "GBP"},
        "GlobalTaxCalculation": "TaxExcluded",
        "Line": [{
            "Id": "line-1", "DetailType": "SalesItemLineDetail",
            "Amount": Decimal("100.00"),
            "SalesItemLineDetail": {
                "ItemRef": {"value": "item-1"},
                "TaxCodeRef": {"value": "TAX"},
            },
        }],
        "TxnTaxDetail": {"TotalTax": Decimal("20.00"), "TaxLine": []},
        "TotalAmt": Decimal("120.00"), "Balance": Decimal("120.00"),
        "EmailStatus": "EmailSent",
    }
    with pytest.raises(QuickBooksAdapterError):
        mapped_invoice(raw)


def test_unresolved_cash_evidence_suppresses_customer_money_end_to_end():
    """An annual/cash discrepancy remains review-required at presentation."""
    unresolved = presentation_input(mismatch=True)
    assert unresolved.status is PresentationStatus.REVIEW_REQUIRED
    view = present_w2_customer_language(unresolved)
    assert not view.safe_to_present
    assert view.annual_liability is None
    assert view.obligations == ()


def test_complete_cash_chain_preserves_obligations_and_non_spendable_surplus():
    """The W1/W2 chain retains dates and never presents surplus as spendable."""
    facts = presentation_input(set_aside="5000.00")
    view = present_w2_customer_language(facts)
    assert view.safe_to_present
    assert len(view.obligations) == 3
    assert all(item.due_date for item in view.obligations)
    assert view.funding_heading == "Set-aside surplus"
    assert "not available cash" in view.funding_message
    assert "safe to spend" not in view.funding_message.lower()


def test_unsafe_presentation_status_cannot_be_rescued_by_complete_values():
    """Complete-looking values cannot override an explicit review-required state."""
    facts = presentation_input()
    unsafe = replace(facts, status=PresentationStatus.REVIEW_REQUIRED)
    view = present_w2_customer_language(unsafe)
    assert not view.safe_to_present
    assert view.annual_liability is None
    assert view.obligations == ()
