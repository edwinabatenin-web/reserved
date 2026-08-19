"""Accounting canonical-contract adversarial and boundary tests.

Expected values are stated independently from the governing contract, not
derived by calling the implementation under test.
"""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from reserved.providers.accounting.contracts import (
    AccountingBusiness, AccountingDocument, AccountingEntry, AccountingMethod,
    AccountingPayment, AccountingProviderName, AllocationEdge, AllocationType,
    AllowabilityDecision, AllowabilityOutcome, CanonicalAccountingEvent,
    CanonicalAccountingTaxInput, CanonicalDocumentState, Completeness,
    CompletenessState, CorrectionLifecycle, DecisionAuthority, DocumentType,
    EffectiveDatedAccountingMethod, EvidenceState, FxProvenance, Money,
    OwnershipConfidence, OwnershipEvidence, OwnershipSubject, PaymentType,
    RecognitionDecision, RecognitionDecisionOutcome, SettlementState,
    SourceObservation, TaxAmountSemantics, TaxBreakdown, Uncertainty,
    UncertaintyKind, VatCategory, VatRegistrationPeriod, VatRegistrationState,
)
from reserved.providers.accounting.normalisation import (
    CanonicalQuarantineError, adapt_observation, build_canonical_tax_input,
    build_recognition_decision, derive_settlement_state, map_provider_status,
    normalise_document, observe_provider_record, select_recognition_candidate,
    settlement_summary, validate_allocations, validate_effective_period_records,
)

RETRIEVED_AT = datetime(2026, 8, 3, 10, 0, 0)


def raw_line(**overrides):
    value = {
        "provider_line_id": "line-1",
        "provider_line_total": "120.00",
        "provider_line_net": "100.00",
        "provider_line_tax": "20.00",
        "provider_tax_semantics": "exclusive",
        "provider_vat_code": "STANDARD",
        "provider_vat_rate": "0.20",
        "provider_currency": "GBP",
    }
    value.update(overrides)
    return value


def raw_record(**overrides):
    value = {
        "provider_document_id": "doc-1",
        "provider_business_id": "business-1",
        "provider_document_kind": "invoice",
        "provider_issued_on": "2026-08-01",
        "provider_currency": "GBP",
        "provider_total": "120.00",
        "provider_status_text": "issued",
        "provider_event_id": "event-1",
        "provider_lines": [raw_line()],
    }
    value.update(overrides)
    return value


def observe(raw):
    return observe_provider_record(
        provider="xero", raw_record=raw, user_id="user-1",
        connected_organisation_id="org-1", business_id="business-1",
        import_run_id="run-1", api_name="synthetic", api_version="v1",
        resource="invoices", record_id="doc-1", retrieved_at=RETRIEVED_AT,
        adapter_version="syn-1",
    )


def doc(**overrides):
    raw = raw_record(**overrides)
    observation = observe(raw)
    return normalise_document(
        observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw),
    )


def edge(identity, kind, amount, payment_id="payment-1", *, reverses=None,
         business_id="business-1", event_id="event-1", currency="GBP",
         document_id="doc-1"):
    return AllocationEdge(identity, business_id, event_id, currency, payment_id,
                          document_id, kind, Decimal(amount), date(2026, 8, 3), reverses)


# ── Source-observation boundary ───────────────────────────────────────────────

def test_normalise_rejects_raw_dict_without_observation():
    with pytest.raises(CanonicalQuarantineError, match="source observation"):
        normalise_document(observation={"gross_amount": "120.00"}, adapter_result=None)


def test_source_fields_are_provider_paths_not_canonical_keys():
    raw = raw_record()
    observation = observe(raw)
    assert observation.provenance.source_fields == tuple(sorted(raw))
    assert "provider_document_id" in observation.provenance.source_fields
    assert "gross_amount" not in observation.provenance.source_fields


def test_changing_source_observation_changes_source_digest():
    first = observe(raw_record()).provenance.source_record_digest
    second = observe(raw_record(provider_total="121.00")).provenance.source_record_digest
    assert first != second


def test_canonical_transformation_does_not_rewrite_source_digest():
    raw = raw_record()
    observation = observe(raw)
    digest_before = observation.provenance.source_record_digest
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    assert d.provenance.source_record_digest == digest_before


def test_corrected_provider_record_gets_distinct_observation_identity():
    first = observe(raw_record()).observation_id
    second = observe(raw_record(provider_total="121.00")).observation_id
    assert first != second


def test_missing_required_source_facts_quarantine_adapter_result():
    raw = raw_record()
    del raw["provider_total"]
    observation = observe(raw)
    assert "provider_total" in observation.missing_fields
    adapter = adapt_observation(observation=observation, raw_record=raw)
    assert "provider_total" in adapter.missing_facts
    with pytest.raises(CanonicalQuarantineError, match="missing provider facts"):
        normalise_document(observation=observation, adapter_result=adapter)


def test_adapter_result_must_reference_its_observation():
    observation = observe(raw_record())
    adapter = adapt_observation(observation=observation, raw_record=raw_record())
    other = observe(raw_record(provider_document_id="doc-2"))
    with pytest.raises(CanonicalQuarantineError, match="does not reference"):
        normalise_document(observation=other, adapter_result=adapter)


def test_adapter_result_cannot_carry_a_final_decision():
    # The adapter result contract has no recognition/allowability decision field.
    from reserved.providers.accounting.contracts import SemanticAdapterResult
    import dataclasses
    fields = {f.name for f in dataclasses.fields(SemanticAdapterResult)}
    assert "recognition_decision" not in fields
    assert "allowability_decision" not in fields


# ── Recognition: no invented accrual ──────────────────────────────────────────

def test_invoice_issue_date_does_not_invent_accrual_recognition():
    d = doc()
    assert d.accrual_candidate is None


def test_cash_recognition_requires_evidence():
    d = doc()
    assert d.cash_candidate is None


def test_adapter_supplied_cash_candidate_is_preserved():
    raw = raw_record(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    observation = observe(raw)
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    assert d.cash_candidate.amount == Decimal("50.00")
    assert d.cash_candidate.date == date(2026, 8, 10)
    assert observation.observation_id in d.cash_candidate.source_observation_ids


def test_unknown_method_cannot_select_cash_or_accrual():
    d = doc(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    with pytest.raises(CanonicalQuarantineError, match="unknown"):
        select_recognition_candidate(d, AccountingMethod.UNKNOWN)


def test_missing_candidate_remains_missing_not_zero():
    d = doc()
    assert select_recognition_candidate(d, AccountingMethod.TRADITIONAL_ACCRUAL) is None


def test_recognition_decision_requires_candidate_for_selected_outcome():
    d = doc()
    with pytest.raises(ValueError, match="selected candidate"):
        RecognitionDecision(
            "decision-1", d.economic_event_id, d.business_id, AccountingMethod.CASH,
            date(2026, 4, 6), None, RecognitionDecisionOutcome.CASH,
            DecisionAuthority.RESERVED_RULE, "v1",
        )


def test_evidence_ids_survive_observation_to_candidate_to_decision():
    raw = raw_record(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    observation = observe(raw)
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    decision = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    assert observation.observation_id in decision.supporting_observation_ids


def test_build_recognition_decision_is_scoped_to_document_event():
    raw = raw_record(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    observation = observe(raw)
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    decision = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    assert decision.economic_event_id == d.economic_event_id
    assert decision.business_id == d.business_id


def test_only_selected_recognition_produces_canonical_tax_input():
    d = doc(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    unable = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.TRADITIONAL_ACCRUAL,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    with pytest.raises(CanonicalQuarantineError, match="without a selected recognition decision"):
        build_canonical_tax_input(input_id="i1", purpose="income", scope="self-assessment",
                                  document=d, recognition_decision=unable,
                                  tax_year="2026-27", policy_version="v1")


def test_valid_recognition_produces_canonical_tax_input():
    raw = raw_record(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    observation = observe(raw)
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    decision = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    tax_input = build_canonical_tax_input(input_id="i1", purpose="income", scope="self-assessment",
                                          document=d, recognition_decision=decision,
                                          tax_year="2026-27", policy_version="v1")
    assert tax_input.recognised_amount == Decimal("50.00")
    assert tax_input.recognised_date == date(2026, 8, 10)


def test_canonical_tax_input_rejects_cross_event_decision():
    d = doc(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    decision = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    other = doc(provider_document_id="doc-2", provider_event_id="event-2")
    with pytest.raises(CanonicalQuarantineError, match="different economic event"):
        build_canonical_tax_input(input_id="i1", purpose="income", scope="self-assessment",
                                  document=other, recognition_decision=decision,
                                  tax_year="2026-27", policy_version="v1")


# ── Allocation / settlement invariants ────────────────────────────────────────

def test_negative_payment_allocation_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        edge("a1", AllocationType.PAYMENT, "-30")


def test_zero_allocation_is_rejected():
    assert "positive amount" in "; ".join(validate_allocations(doc(), (edge("a1", AllocationType.PAYMENT, "0"),)))


def test_missing_payment_reference_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.PAYMENT, "30", payment_id=None)
    assert "no payment reference" in "; ".join(validate_allocations(d, (bad,)))


def test_missing_document_reference_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.PAYMENT, "30", document_id="other-doc")
    assert "different document" in "; ".join(validate_allocations(d, (bad,)))


def test_cross_business_allocation_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.PAYMENT, "30", business_id="business-2")
    assert "different business" in "; ".join(validate_allocations(d, (bad,)))


def test_cross_event_allocation_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.PAYMENT, "30", event_id="event-2")
    assert "different economic event" in "; ".join(validate_allocations(d, (bad,)))


def test_incompatible_currency_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.PAYMENT, "30", currency="EUR")
    assert "incompatible currency" in "; ".join(validate_allocations(d, (bad,)))


def test_duplicate_allocation_identity_is_rejected():
    d = doc()
    edges = (edge("a1", AllocationType.PAYMENT, "30"), edge("a1", AllocationType.PAYMENT, "20", payment_id="payment-2"))
    assert "duplicate allocation identity" in "; ".join(validate_allocations(d, edges))


def test_same_payment_applied_twice_is_rejected():
    d = doc()
    edges = (edge("a1", AllocationType.PAYMENT, "30"), edge("a2", AllocationType.PAYMENT, "20"))
    assert "applied more than once" in "; ".join(validate_allocations(d, edges))


def test_orphan_reversal_is_rejected():
    d = doc()
    bad = edge("rev", AllocationType.REVERSAL, "30", reverses="missing")
    assert "missing allocation" in "; ".join(validate_allocations(d, (bad,)))


def test_repeated_reversal_is_rejected():
    d = doc()
    edges = (
        edge("a1", AllocationType.PAYMENT, "30"),
        edge("rev1", AllocationType.REVERSAL, "30", payment_id=None, reverses="a1"),
        edge("rev2", AllocationType.REVERSAL, "30", payment_id=None, reverses="a1"),
    )
    errors = "; ".join(validate_allocations(d, edges))
    assert "reversed more than once" in errors


def test_reversal_of_reversal_is_rejected():
    d = doc()
    edges = (
        edge("a1", AllocationType.PAYMENT, "30"),
        edge("rev1", AllocationType.REVERSAL, "30", payment_id=None, reverses="a1"),
        edge("rev2", AllocationType.REVERSAL, "30", payment_id=None, reverses="rev1"),
    )
    errors = "; ".join(validate_allocations(d, edges))
    assert "targets another reversal" in errors


def test_reversal_amount_mismatch_is_rejected():
    d = doc()
    edges = (
        edge("a1", AllocationType.PAYMENT, "30"),
        edge("rev1", AllocationType.REVERSAL, "10", payment_id=None, reverses="a1"),
    )
    errors = "; ".join(validate_allocations(d, edges))
    assert "amount differs" in errors


def test_credit_note_represented_as_payment_is_rejected():
    d = doc()
    bad = edge("a1", AllocationType.CREDIT, "20", payment_id="payment-1")
    assert "must not reference a payment" in "; ".join(validate_allocations(d, (bad,)))


def test_valid_credit_note_allocation():
    d = doc()
    good = edge("credit", AllocationType.CREDIT, "20", payment_id=None)
    summary = settlement_summary(d, (good,))
    assert summary.allocated_amount == Decimal("20")
    assert summary.outstanding_amount == Decimal("100.00")


@pytest.mark.parametrize("write_off,expected_outstanding", [("45", "75.00"), ("120", "0")])
def test_partial_and_full_write_off(write_off, expected_outstanding):
    d = doc()
    summary = settlement_summary(d, (edge("wo", AllocationType.WRITE_OFF, write_off, payment_id=None),))
    assert summary.outstanding_amount == Decimal(expected_outstanding)


def test_refund_unsettles_and_can_overpay():
    d = doc()
    payment = edge("a1", AllocationType.PAYMENT, "120")
    refund = edge("r1", AllocationType.REFUND, "30", payment_id="refund-1")
    summary = settlement_summary(d, (payment, refund))
    assert summary.allocated_amount == Decimal("90")
    assert summary.outstanding_amount == Decimal("30.00")


def test_overpayment_state_is_derived():
    d = doc()
    payment = edge("a1", AllocationType.PAYMENT, "140")
    assert derive_settlement_state(d, (payment,)) is SettlementState.OVERPAID


def test_part_paid_and_paid_states_are_derived():
    d = doc()
    assert derive_settlement_state(d, ()) is SettlementState.UNPAID
    assert derive_settlement_state(d, (edge("a1", AllocationType.PAYMENT, "30"),)) is SettlementState.PART_PAID
    assert derive_settlement_state(d, (edge("a1", AllocationType.PAYMENT, "120"),)) is SettlementState.PAID


def test_full_write_off_state_is_derived():
    d = doc()
    assert derive_settlement_state(d, (edge("wo", AllocationType.WRITE_OFF, "120", payment_id=None),)) is SettlementState.WRITTEN_OFF


def test_settlement_summary_fails_closed_on_invalid_allocations():
    d = doc()
    with pytest.raises(CanonicalQuarantineError, match="invalid allocations"):
        settlement_summary(d, (edge("a1", AllocationType.PAYMENT, "30", document_id="other"),))


# ── Provider status vs canonical state ───────────────────────────────────────

def test_unknown_provider_status_does_not_silently_map_to_active():
    d = doc(provider_status_text="weird_provider_state")
    assert d.provider_status == "weird_provider_state"
    assert d.canonical_state is map_provider_status("weird_provider_state")
    assert d.settlement_state is SettlementState.UNKNOWN


def test_known_provider_status_maps_to_controlled_state():
    assert map_provider_status("issued") is CanonicalDocumentState.ISSUED
    assert map_provider_status("draft") is CanonicalDocumentState.DRAFT
    assert map_provider_status("unknown-status") is CanonicalDocumentState.UNKNOWN


def test_provider_status_is_preserved_as_evidence():
    d = doc(provider_status_text="open")
    assert d.provider_status == "open"
    assert d.canonical_state is CanonicalDocumentState.OPEN


# ── FX provenance ─────────────────────────────────────────────────────────────

def test_fx_provenance_survives_normalisation():
    raw = raw_record()
    raw.update({
        "provider_fx_original_amount": "100.00",
        "provider_fx_original_currency": "EUR",
        "provider_fx_base_amount": "85.00",
        "provider_fx_base_currency": "GBP",
        "provider_fx_rate": "0.85",
        "provider_fx_rate_date": "2026-08-01",
        "provider_fx_source": "ECB",
        "provider_fx_rounding": "half-even",
        "provider_fx_conversion": "direct",
    })
    observation = observe(raw)
    d = normalise_document(observation=observation, adapter_result=adapt_observation(observation=observation, raw_record=raw))
    assert d.fx is not None
    assert d.fx.original_currency == "EUR"
    assert d.fx.base_currency == "GBP"
    assert d.fx.fx_rate == Decimal("0.85")
    assert d.fx.fx_rate_date == date(2026, 8, 1)
    assert d.fx.fx_source == "ECB"
    assert d.fx.rounding_method == "half-even"
    assert d.fx.conversion_method == "direct"
    assert d.fx.observation_id == observation.observation_id


def test_incomplete_fx_conversion_tuple_is_rejected():
    with pytest.raises(ValueError, match="FX conversion requires"):
        Money(Decimal("100"), "EUR", base_amount=Decimal("85"), base_currency="GBP")


def test_same_currency_fx_conversion_is_rejected():
    with pytest.raises(ValueError, match="differ"):
        Money(Decimal("100"), "GBP", base_amount=Decimal("100"), base_currency="GBP",
              fx_rate=Decimal("1"), fx_rate_date=date(2026, 8, 1), fx_source="ECB")


def test_fx_amounts_must_be_finite():
    with pytest.raises(ValueError, match="finite"):
        Money(Decimal("NaN"), "GBP")


# ── Effective periods ─────────────────────────────────────────────────────────

def test_effective_to_before_from_is_rejected():
    with pytest.raises(ValueError, match="precedes"):
        EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6), date(2026, 4, 5))


def test_adjacent_periods_are_permitted():
    cash = EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6), date(2027, 4, 5))
    accrual = EffectiveDatedAccountingMethod("b1", AccountingMethod.TRADITIONAL_ACCRUAL, date(2027, 4, 6))
    assert validate_effective_period_records((cash, accrual)) == []


def test_overlapping_contradictory_periods_are_rejected():
    cash = EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6), date(2027, 4, 5))
    accrual = EffectiveDatedAccountingMethod("b1", AccountingMethod.TRADITIONAL_ACCRUAL, date(2026, 10, 1))
    assert validate_effective_period_records((cash, accrual)) != []


def test_different_businesses_may_use_different_methods():
    cash = EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6))
    accrual = EffectiveDatedAccountingMethod("b2", AccountingMethod.TRADITIONAL_ACCRUAL, date(2026, 4, 6))
    assert validate_effective_period_records((cash, accrual)) == []
    assert cash.method is AccountingMethod.CASH
    assert accrual.method is AccountingMethod.TRADITIONAL_ACCRUAL


def test_accounting_method_and_mtd_basis_are_independent():
    business = AccountingBusiness(
        AccountingProviderName.XERO,
        "b1", "Trade", "GBP",
        accounting_methods=(EffectiveDatedAccountingMethod("b1", AccountingMethod.CASH, date(2026, 4, 6)),),
    )
    assert business.accounting_methods[0].method is AccountingMethod.CASH


# ── VAT ───────────────────────────────────────────────────────────────────────

def test_vat_net_plus_vat_must_equal_gross():
    with pytest.raises(ValueError, match="net_amount \\+ vat_amount"):
        TaxBreakdown(Decimal("100"), Decimal("25"), Decimal("120"), TaxAmountSemantics.EXCLUSIVE)


def test_inclusive_and_exclusive_semantics_are_preserved():
    assert TaxAmountSemantics.INCLUSIVE.value == "inclusive"
    assert TaxAmountSemantics.EXCLUSIVE.value == "exclusive"


def test_not_applicable_vat_cannot_carry_nonzero_vat():
    with pytest.raises(ValueError, match="not-applicable"):
        TaxBreakdown(Decimal("100"), Decimal("20"), Decimal("120"), TaxAmountSemantics.NOT_APPLICABLE)


def test_vat_codes_remain_distinguishable():
    assert {VatCategory.ZERO_RATED.value, VatCategory.EXEMPT.value, VatCategory.OUTSIDE_SCOPE.value} == \
        {"zero_rated", "exempt", "outside_scope"}


# ── Ownership ────────────────────────────────────────────────────────────────

def test_unknown_ownership_never_implies_share():
    with pytest.raises(ValueError, match="unknown ownership"):
        OwnershipEvidence("property-1", OwnershipSubject.PROPERTY, Decimal("1"), OwnershipConfidence.UNKNOWN, date(2026, 4, 6))


def test_ownership_share_must_be_within_unit_interval():
    with pytest.raises(ValueError, match="between zero and one"):
        OwnershipEvidence("property-1", OwnershipSubject.PROPERTY, Decimal("1.5"), OwnershipConfidence.CONFIRMED, date(2026, 4, 6))


def test_ownership_effective_period_is_validated():
    with pytest.raises(ValueError, match="precedes"):
        OwnershipEvidence("property-1", OwnershipSubject.PROPERTY, Decimal("0.5"), OwnershipConfidence.CONFIRMED,
                          date(2026, 4, 6), date(2026, 4, 5))


def test_confirmed_half_share_is_preserved():
    evidence = OwnershipEvidence("property-1", OwnershipSubject.PROPERTY, Decimal("0.5"),
                                 OwnershipConfidence.CONFIRMED, date(2026, 4, 6))
    assert evidence.share == Decimal("0.5")
    assert evidence.subject_type is OwnershipSubject.PROPERTY


# ── Uncertainty ───────────────────────────────────────────────────────────────

def test_uncertainty_range_requires_both_bounds():
    with pytest.raises(ValueError, match="both minimum and maximum"):
        Uncertainty(UncertaintyKind.MISSING, "amount", "missing", minimum_effect=Decimal("10"))


def test_uncertainty_minimum_must_not_exceed_maximum():
    with pytest.raises(ValueError, match="must not exceed"):
        Uncertainty(UncertaintyKind.MISSING, "amount", "bad range",
                    minimum_effect=Decimal("20"), maximum_effect=Decimal("10"))


def test_conflicting_uncertainty_requires_competing_references():
    with pytest.raises(ValueError, match="competing observation"):
        Uncertainty(UncertaintyKind.CONFLICTING, "amount", "two values differ")


# ── Correction lifecycle ─────────────────────────────────────────────────────

def test_void_delete_and_reclassification_keep_one_economic_event():
    d = doc()
    variants = [
        replace(d, correction_lifecycle=CorrectionLifecycle.VOIDED),
        replace(d, correction_lifecycle=CorrectionLifecycle.DELETED),
        replace(d, correction_lifecycle=CorrectionLifecycle.RECLASSIFIED, replaces_document_id="doc-1"),
    ]
    event = CanonicalAccountingEvent("event-1", "business-1", ("doc-1",),
                                     evidence_state=EvidenceState.SELECTED)
    assert {item.economic_event_id for item in variants} == {event.economic_event_id}


# ── Legacy pathway guards ────────────────────────────────────────────────────

def test_accounting_entry_is_still_deprecated_flattened_model():
    entry = AccountingEntry(
        AccountingProviderName.XERO,
        "b1", "e1", date(2026, 8, 1), "GBP", Decimal("10"), "credit", "expense",
    )
    assert entry.direction == "credit"
    assert "Deprecated" in AccountingEntry.__doc__


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


def test_freshness_bookkeeping_and_retrieval_completeness_are_independent():
    state = Completeness(CompletenessState.COMPLETE, CompletenessState.INCOMPLETE,
                         CompletenessState.UNKNOWN, CompletenessState.INCOMPLETE,
                         "pagination stopped on page 2")
    assert state.record_freshness is CompletenessState.COMPLETE
    assert state.retrieval is CompletenessState.INCOMPLETE
    assert state.bookkeeping is CompletenessState.UNKNOWN
