from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from reserved.providers.accounting.contracts import (
    AccountingBusiness, AccountingMethod, AccountingPayment, AllocationEdge,
    AllocationType, AllowabilityDecision, AllowabilityOutcome,
    CanonicalAccountingEvent, Completeness, CompletenessState, DecisionAuthority,
    DocumentType, EffectiveDatedAccountingMethod, EvidenceState, LifecycleState,
    Money, OwnershipConfidence, OwnershipEvidence, PaymentType, TaxAmountSemantics,
    VatRegistrationPeriod, VatRegistrationState,
)
from reserved.providers.accounting.normalisation import (
    CanonicalQuarantineError, normalise_document, select_recognition_candidate,
    settlement_summary,
)


def payload(**overrides):
    value = {
        "user_id": "user-1", "connected_organisation_id": "org-1",
        "external_business_id": "business-1", "import_run_id": "run-1",
        "external_document_id": "doc-1", "economic_event_id": "event-1",
        "api_name": "synthetic", "api_version": "v1", "resource": "invoices",
        "adapter_version": "canonical-test", "retrieved_at": "2026-08-03T10:00:00+00:00",
        "document_type": "invoice", "issue_date": "2026-08-01", "due_date": "2026-08-31",
        "currency": "GBP", "gross_amount": "120.00", "net_amount": "100.00",
        "tax_amount": "20.00", "tax_semantics": "exclusive", "status": "issued",
        "lines": [{
            "line_id": "line-1", "gross_amount": "120.00", "net_amount": "100.00",
            "tax_amount": "20.00", "tax_semantics": "exclusive", "vat_code": "STANDARD",
            "vat_rate": "0.20", "description": "Management fee",
            "provider_category_id": "cat-1", "provider_account_id": "400",
            "property_allocation_id": "property-1", "tracking_allocation_ids": ["track-1"],
        }],
    }
    value.update(overrides)
    return value


def doc(**overrides):
    return normalise_document(provider="xero", payload=payload(**overrides))


def edge(identity, kind, amount, payment_id="payment-1", reverses=None):
    return AllocationEdge(identity, payment_id, "doc-1", kind, Decimal(amount),
                          date(2026, 8, 3), reverses)


def test_missing_amount_paid_remains_unknown_and_unpaid_invoice_is_not_zeroed():
    result = doc()
    assert result.amount_paid is None
    assert settlement_summary(result, ()).outstanding_amount == Decimal("120.00")
    assert result.cash_candidate.amount is None


def test_part_paid_invoice_uses_multiple_allocation_edges():
    result = settlement_summary(doc(), (
        edge("a1", AllocationType.PAYMENT, "30"),
        edge("a2", AllocationType.PAYMENT, "20", "payment-2"),
    ))
    assert result.allocated_amount == Decimal("50")
    assert result.outstanding_amount == Decimal("70.00")


def test_credit_note_refund_and_write_off_are_explicit_settlement_edges():
    credit = edge("credit", AllocationType.CREDIT, "20", None)
    write_off = edge("wo", AllocationType.WRITE_OFF, "10", None)
    refund = edge("refund", AllocationType.REFUND, "-5", "refund-1")
    result = settlement_summary(doc(), (credit, write_off, refund))
    assert result.allocated_amount == Decimal("25")
    assert result.outstanding_amount == Decimal("95.00")


@pytest.mark.parametrize("write_off,expected", [("45", "75.00"), ("120", "0")])
def test_partial_and_full_write_off(write_off, expected):
    result = settlement_summary(doc(), (edge("wo", AllocationType.WRITE_OFF, write_off, None),))
    assert result.outstanding_amount == Decimal(expected)


def test_cash_refund_has_separate_payment_record_and_event_identity():
    result = doc(document_type="refund", gross_amount="-25", net_amount="-25",
                 tax_amount="0", tax_semantics="not_applicable",
                 lines=[{"line_id": "refund-line", "gross_amount": "-25",
                         "net_amount": "-25", "tax_amount": "0",
                         "tax_semantics": "not_applicable"}])
    payment = AccountingPayment("refund-1", "business-1", PaymentType.REFUND,
                                date(2026, 8, 4), Money(Decimal("-25"), "GBP"),
                                result.provenance, result.economic_event_id)
    assert payment.payment_type is PaymentType.REFUND
    assert payment.money.original_amount == Decimal("-25")


def test_void_delete_and_reclassification_keep_one_economic_event():
    original = doc()
    variants = [
        replace(original, lifecycle_state=LifecycleState.VOIDED),
        replace(original, lifecycle_state=LifecycleState.DELETED),
        replace(original, lifecycle_state=LifecycleState.RECLASSIFIED, replaces_document_id="doc-1"),
    ]
    event = CanonicalAccountingEvent("event-1", "business-1", ("doc-1",),
                                     evidence_state=EvidenceState.SELECTED)
    assert {item.economic_event_id for item in variants} == {event.economic_event_id}


def test_cash_and_accrual_candidates_are_separate_and_unknown_does_not_choose():
    result = doc(cash_recognition_date="2026-08-10", cash_recognition_amount="50")
    assert select_recognition_candidate(result, AccountingMethod.CASH).date == date(2026, 8, 10)
    assert select_recognition_candidate(result, AccountingMethod.TRADITIONAL_ACCRUAL).date == date(2026, 8, 1)
    with pytest.raises(CanonicalQuarantineError, match="unknown"):
        select_recognition_candidate(result, AccountingMethod.UNKNOWN)


def test_vat_registered_inclusive_and_non_vat_semantics_are_explicit():
    inclusive = doc(tax_semantics="inclusive",
                    lines=[{"line_id": "line-1", "gross_amount": "120",
                            "net_amount": "100", "tax_amount": "20",
                            "tax_semantics": "inclusive"}])
    non_vat = doc(gross_amount="100", net_amount="100", tax_amount="0",
                  tax_semantics="not_applicable",
                  lines=[{"line_id": "line-1", "gross_amount": "100",
                          "net_amount": "100", "tax_amount": "0",
                          "tax_semantics": "not_applicable"}])
    history = VatRegistrationPeriod(VatRegistrationState.REGISTERED, date(2026, 4, 6),
                                    scheme="standard", basis="invoice")
    assert inclusive.lines[0].tax.semantics is TaxAmountSemantics.INCLUSIVE
    assert non_vat.lines[0].tax.semantics is TaxAmountSemantics.NOT_APPLICABLE
    assert history.state is VatRegistrationState.REGISTERED


def test_property_allocation_and_share_never_assume_unknown_is_one_hundred_percent():
    result = doc()
    confirmed = OwnershipEvidence("property-1", Decimal("0.5"), OwnershipConfidence.CONFIRMED,
                                  date(2026, 4, 6))
    unknown = OwnershipEvidence("property-1", None, OwnershipConfidence.UNKNOWN, date(2026, 4, 6))
    assert result.lines[0].property_allocation_id == "property-1"
    assert confirmed.share == Decimal("0.5")
    assert unknown.share is None
    with pytest.raises(ValueError, match="unknown ownership"):
        OwnershipEvidence("property-1", Decimal("1"), OwnershipConfidence.UNKNOWN, date(2026, 4, 6))


def test_multiple_businesses_can_have_different_effective_dated_methods():
    cash = EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6))
    accrual = EffectiveDatedAccountingMethod("b2", AccountingMethod.TRADITIONAL_ACCRUAL, date(2026, 4, 6))
    businesses = (
        AccountingBusiness(result_provider(), "b1", "Trade", "GBP", accounting_methods=(cash,)),
        AccountingBusiness(result_provider(), "b2", "Property", "GBP", accounting_methods=(accrual,)),
    )
    assert businesses[0].accounting_methods[0].method is AccountingMethod.CASH
    assert businesses[1].accounting_methods[0].method is AccountingMethod.TRADITIONAL_ACCRUAL


def result_provider():
    return doc().provenance.identity.provider


def test_foreign_currency_requires_complete_fx_provenance():
    money = Money(Decimal("100"), "EUR", Decimal("85"), "GBP", Decimal("0.85"),
                  date(2026, 8, 1), "ECB")
    assert money.base_amount == Decimal("85")
    with pytest.raises(ValueError, match="FX conversion requires"):
        Money(Decimal("100"), "EUR", base_amount=Decimal("85"), base_currency="GBP")


def test_provider_assertion_is_distinct_from_reserved_allowability_decision():
    decision = AllowabilityDecision(
        "decision-1", AllowabilityOutcome.DISALLOWABLE, DecisionAuthority.RESERVED_RULE,
        datetime(2026, 8, 3, tzinfo=timezone.utc), "private-use rule",
        provider_assertion="allowable_for_tax=true",
    )
    assert decision.provider_assertion == "allowable_for_tax=true"
    assert decision.outcome is AllowabilityOutcome.DISALLOWABLE


def test_conflicting_and_corroborating_evidence_share_economic_event():
    conflict = CanonicalAccountingEvent(
        "event-1", "business-1", evidence_observation_ids=("xero-1", "bank-1"),
        evidence_state=EvidenceState.CONFLICTING, evidence_reason="amount differs",
        competing_observation_ids=("bank-1",),
    )
    corroborated = replace(conflict, evidence_state=EvidenceState.CORROBORATING,
                           evidence_reason="amount/date match")
    assert conflict.economic_event_id == corroborated.economic_event_id
    assert conflict.competing_observation_ids == ("bank-1",)


def test_freshness_bookkeeping_and_retrieval_completeness_are_independent():
    state = Completeness(CompletenessState.COMPLETE, CompletenessState.INCOMPLETE,
                         CompletenessState.UNKNOWN, CompletenessState.INCOMPLETE,
                         "pagination stopped on page 2")
    assert state.record_freshness is CompletenessState.COMPLETE
    assert state.retrieval is CompletenessState.INCOMPLETE
    assert state.bookkeeping is CompletenessState.UNKNOWN


def test_missing_required_provider_field_is_quarantined_not_zeroed():
    value = payload()
    value["lines"][0].pop("gross_amount")
    with pytest.raises(CanonicalQuarantineError, match="gross_amount"):
        normalise_document(provider="freeagent", payload=value)


def test_source_identity_provenance_and_digest_are_preserved():
    result = doc()
    identity = result.provenance.identity
    assert (identity.user_id, identity.connected_organisation_id,
            identity.business_id, identity.import_run_id) == (
                "user-1", "org-1", "business-1", "run-1")
    assert len(result.provenance.source_record_digest) == 64
    assert "gross_amount" in result.provenance.source_fields

