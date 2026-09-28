from datetime import date
from decimal import Decimal

from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis, DeductionRepresentation, LoanComponent,
    LoanBasisEvidence, LoanDeductionEvidence, reconcile_annual_student_loans,
)
from reserved.engines.annual_loan_wp7u import emit_annual_loan_wp7u_envelopes
from reserved.evidence_uncertainty import (
    CalculationStatus, EffectKind, EvidenceSelection, EstimatePurpose, PurposeFitness,
)


def evidence(eid, amount, *, employment="job-a", effective=date(2027, 4, 5), observed=None):
    return LoanDeductionEvidence(
        eid, LoanComponent.PLAN_2, amount, "2026/27", observed or effective, effective,
        employment, DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True,
        "synthetic_document", f"synthetic://{eid}",
    )


def reconcile(items, *, income="103000", declared=("job-a",), plans=(2,), as_of=date(2027, 4, 5)):
    basis_item = LoanBasisEvidence(
        "E-BASIS", "synthetic_annual_calculation", "synthetic://basis", "person-a",
        date(2027, 4, 5), "2026/27 annual Self Assessment basis", True,
    )
    return reconcile_annual_student_loans(
        AnnualLoanIncomeBasis(income, ("E-BASIS",), True, True, (basis_item,)), plans, items,
        as_of=as_of, declared_employment_ids=declared,
    )


def emit(result):
    return emit_annual_loan_wp7u_envelopes(
        result, emission_id="synthetic-emission", calculated_at="2027-04-05T12:00:00+00:00"
    )[0]


def test_selected_superseded_and_duplicate_evidence_is_losslessly_mapped():
    result = reconcile([
        evidence("E-OLD", "2500", effective=date(2027, 3, 1)),
        evidence("E-NEW-A", "3000"), evidence("E-NEW-B", "3000"),
    ])
    envelope = emit(result)
    selections = {item.evidence_id: item.selection for item in envelope.evidence}
    assert selections["E-NEW-B"] is EvidenceSelection.SELECTED
    assert selections["E-OLD"] is EvidenceSelection.SUPERSEDED
    assert selections["E-NEW-A"] is EvidenceSelection.SUPERSEDED
    assert envelope.point_estimate == Decimal("3625.00")
    assert envelope.purpose.value == "reconciliation"
    assert "customer_combined_balance" in envelope.prohibited_uses


def test_missing_evidence_is_inadequate_and_not_zero():
    envelope = emit(reconcile([]))
    assert envelope.calculation_status is CalculationStatus.INSUFFICIENT_FACTS
    assert envelope.fitness is PurposeFitness.INADEQUATE
    assert envelope.point_estimate is None
    assert envelope.uncertainties[0].effect.kind is EffectKind.NOT_DETERMINABLE


def test_stale_effect_and_excess_not_refund_are_separate_point_effects():
    envelope = emit(reconcile(
        [evidence("E-STALE", "100", effective=date(2026, 12, 1))], income="30000"
    ))
    effects = {issue.issue_id: issue.effect.amount for issue in envelope.uncertainties}
    assert envelope.calculation_status is CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY
    assert effects == {"plan_2-stale": Decimal("55.00"), "plan_2-excess": Decimal("45.00")}
    assert envelope.point_estimate == Decimal("0.00")


def test_conflict_retains_candidates_and_bounded_residual_range():
    envelope = emit(reconcile([evidence("E-A", "999"), evidence("E-B", "3000")]))
    assert envelope.calculation_status is CalculationStatus.CONFLICT_REQUIRES_REVIEW
    assert (envelope.lower_bound, envelope.upper_bound) == (Decimal("3625.00"), Decimal("3725.00"))
    deduction_items = [item for item in envelope.evidence if item.evidence_id != "E-BASIS"]
    assert {item.selection for item in deduction_items} == {EvidenceSelection.UNRESOLVED_CONFLICT}
    assert envelope.uncertainties[0].effect.kind is EffectKind.RANGE


def test_unsupported_multiple_undergraduate_state_emits_no_money():
    envelope = emit(reconcile([], plans=(1, 2)))
    assert envelope.calculation_status is CalculationStatus.UNSUPPORTED_RULE
    assert envelope.point_estimate is None
    assert envelope.purpose is EstimatePurpose.UNSUPPORTED_FOR_DECISION
    assert envelope.unsupported_families == ("simultaneous_multiple_undergraduate_plans",)
    assert envelope.uncertainties[0].effect.kind is EffectKind.NOT_DETERMINABLE
    assert "HMRC or a qualified tax adviser" in envelope.uncertainties[0].customer_action
    assert envelope.uncertainties[0].evidence_references == (
        "E-BASIS", "student-loan-plan-input:0", "student-loan-plan-input:1",
    )
    assert [item.original_value for item in envelope.evidence[-2:]] == ["1", "2"]
    assert "verification_required_before_student_loan_or_total_amount" in envelope.limitation_references
    assert "customer_combined_balance" in envelope.prohibited_uses


def test_unknown_plan_emits_inadequate_not_determinable_envelope_without_money():
    envelope = emit(reconcile([], plans=(2, "mystery")))
    assert envelope.calculation_status is CalculationStatus.UNSUPPORTED_RULE
    assert envelope.purpose is EstimatePurpose.UNSUPPORTED_FOR_DECISION
    assert envelope.fitness is PurposeFitness.INADEQUATE
    assert envelope.point_estimate is None
    assert envelope.uncertainties[0].effect.kind is EffectKind.NOT_DETERMINABLE
    assert "HMRC or a qualified tax adviser" in envelope.uncertainties[0].customer_action
    assert "verification_required_before_student_loan_or_total_amount" in envelope.limitation_references
    assert envelope.unsupported_families == ("mixed_known_and_unknown_student_loan_plans",)
    assert [item.original_value for item in envelope.evidence[-2:]] == ["2", "mystery"]


def test_unknown_only_plan_has_truthful_distinct_family_and_exact_input_provenance():
    envelope = emit(reconcile([], plans=("mystery",)))
    assert envelope.unsupported_families == ("unknown_student_loan_plan",)
    assert envelope.evidence[-1].original_value == "mystery"
    assert envelope.evidence[-1].selection is EvidenceSelection.INCOMPATIBLE_REPRESENTATION


def test_supported_plan_2_keeps_formal_reconciliation_purpose():
    envelope = emit(reconcile([evidence("E-PLAN2", "100")]))
    assert envelope.purpose is EstimatePurpose.RECONCILIATION


def test_plan_2_and_pgl_emit_separate_envelopes_not_combined_money():
    pgl = LoanDeductionEvidence(
        "E-PGL", LoanComponent.POSTGRADUATE, "1800", "2026/27",
        date(2027, 4, 5), date(2027, 4, 5), "job-a",
        DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True, "synthetic_document", "synthetic://pgl",
    )
    result = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),)), (2, "postgraduate"),
        [evidence("E-P2", "3000"), pgl], as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    envelopes = emit_annual_loan_wp7u_envelopes(
        result, emission_id="dual", calculated_at="2027-04-05T12:00:00+00:00"
    )
    assert tuple(item.point_estimate for item in envelopes) == (Decimal("3625.00"), Decimal("3120.00"))
    assert not any(hasattr(item, "combined_balance") for item in envelopes)


def test_incomplete_basis_and_no_plan_root_failures_emit_inadequate_envelopes():
    incomplete = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", (), False, False), (2,), [],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    no_plan = reconcile([], plans=())
    for result in (incomplete, no_plan):
        envelope = emit(result)
        assert envelope.fitness is PurposeFitness.INADEQUATE
        assert envelope.calculation_status is CalculationStatus.INSUFFICIENT_FACTS
        assert envelope.point_estimate is None


def test_full_basis_provenance_and_exact_tax_year_are_emitted():
    basis_evidence = LoanBasisEvidence(
        "E-BASIS", "synthetic_annual_calculation", "synthetic://basis", "person-a",
        date(2027, 4, 5), "2026/27 annual Self Assessment basis", True,
    )
    result = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (basis_evidence,)),
        (2,), [evidence("E-SL", "3000")], as_of=date(2027, 4, 5),
        declared_employment_ids=("job-a",),
    )
    envelope = emit(result)
    mapped = envelope.evidence[0]
    assert mapped.evidence_id == "E-BASIS"
    assert mapped.source_reference == "synthetic://basis"
    assert mapped.subject_reference == "person-a"
    assert mapped.tax_year == "2026/27"
    assert mapped.effective_period == "2026/27 annual Self Assessment basis"


def test_producer_recency_threshold_controls_stale_mapping():
    result = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),)), (2,),
        [evidence("E-SL", "3000", effective=date(2027, 3, 1))],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",), stale_after_days=30,
    )
    envelope = emit(result)
    assert envelope.evidence[-1].recency_state == "stale"
    assert envelope.evidence[-1].tax_year == "2026/27"


def test_exclusion_selection_uses_structured_reason_and_conflict_basis_names_candidates():
    outside = evidence("E-FUTURE", "3000", effective=date(2027, 4, 5), observed=date(2027, 4, 6))
    incomplete = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),)), (2,), [outside],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    excluded = emit(incomplete).evidence[-1]
    assert excluded.selection is EvidenceSelection.OUTSIDE_PERIOD

    conflict = emit(reconcile([evidence("E-A", "999"), evidence("E-B", "3000")]))
    assert "E-A=999.00" in conflict.bound_basis
    assert "E-B=3000.00" in conflict.bound_basis
    assert "range_completeness:complete_for_identified_conflicts_only" in conflict.limitation_references


def test_future_item_maps_outside_period_even_when_valid_item_allows_calculation():
    valid = evidence("E-VALID", "3000")
    future = evidence("E-FUTURE", "3100", effective=date(2027, 4, 5), observed=date(2027, 4, 6))
    envelope = emit(reconcile([valid, future]))
    mapped = {item.evidence_id: item for item in envelope.evidence}
    assert envelope.calculation_status is CalculationStatus.CALCULATED
    assert mapped["E-VALID"].selection is EvidenceSelection.SELECTED
    assert mapped["E-FUTURE"].selection is EvidenceSelection.OUTSIDE_PERIOD


def test_basis_evidence_does_not_duplicate_aggregate_income_as_source_value():
    envelope = emit(reconcile([evidence("E-SL", "3000")]))
    basis_item = next(item for item in envelope.evidence if item.evidence_id == "E-BASIS")
    assert basis_item.original_value is None
    assert basis_item.unit is None
