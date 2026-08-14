from datetime import date
from decimal import Decimal

import pytest

from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis,
    LoanBasisEvidence,
    DeductionRepresentation,
    LoanComponent,
    LoanDeductionEvidence,
    reconcile_annual_student_loans as _reconcile_annual_student_loans,
)


AS_OF = date(2027, 4, 5)


def reconcile_annual_student_loans(income_basis, plans, evidence, **kwargs):
    return _reconcile_annual_student_loans(
        income_basis,
        plans,
        evidence,
        as_of=kwargs.pop("as_of", AS_OF),
        declared_employment_ids=kwargs.pop("declared_employment_ids", ("synthetic-job-a",)),
        **kwargs,
    )


def basis(amount="103000", **changes):
    basis_evidence = LoanBasisEvidence(
        "E-SYNTHETIC-ANNUAL-BASIS", "synthetic_annual_calculation",
        "synthetic://annual-basis", "synthetic-person", date(2027, 4, 5),
        "2026/27 annual Self Assessment basis", True,
    )
    values = {
        "amount": amount,
        "evidence_ids": ("E-SYNTHETIC-ANNUAL-BASIS",),
        "qualifying_pension_relief_confirmed": True,
        "taxable_income_scope_confirmed": True,
        "evidence": (basis_evidence,),
        **changes,
    }
    return AnnualLoanIncomeBasis(**values)


def deduction(component, amount, evidence_id, *, employment="synthetic-job-a", effective=date(2027, 4, 5)):
    return LoanDeductionEvidence(
        evidence_id=evidence_id,
        component=component,
        amount=amount,
        tax_year="2026/27",
        observed_on=effective,
        effective_through=effective,
        employment_id=employment,
        representation=DeductionRepresentation.EMPLOYMENT_CUMULATIVE,
        complete_for_representation=True,
        source_kind="synthetic_document",
        source_reference=f"synthetic://{evidence_id}",
    )


def test_admitted_hmx_002_plan_2_and_pgl_components_reconcile_separately():
    result = reconcile_annual_student_loans(
        basis(),
        [2, "postgraduate"],
        [
            deduction(LoanComponent.PLAN_2, "3000", "E-SL-PLAN2"),
            deduction(LoanComponent.POSTGRADUATE, "1800", "E-SL-PGL"),
        ],
    )
    plan_2 = result.component(LoanComponent.PLAN_2)
    pgl = result.component(LoanComponent.POSTGRADUATE)
    assert result.income_basis == Decimal("103000.00")
    assert (plan_2.annual_liability, plan_2.evidenced_deductions, plan_2.remaining_self_assessment_amount) == (
        Decimal("6625.00"), Decimal("3000.00"), Decimal("3625.00")
    )
    assert (pgl.annual_liability, pgl.evidenced_deductions, pgl.remaining_self_assessment_amount) == (
        Decimal("4920.00"), Decimal("1800.00"), Decimal("3120.00")
    )
    assert not hasattr(result, "remaining_combined_self_assessment_amount")
    assert "customer_combined_balance" in result.prohibited_uses


def test_annual_liability_is_floored_before_deduction_reconciliation():
    result = reconcile_annual_student_loans(
        basis("103000"), [2], [deduction(LoanComponent.PLAN_2, "0", "E-SL-ZERO")]
    )
    assert result.component(LoanComponent.PLAN_2).annual_liability == Decimal("6625.00")


def test_simultaneous_undergraduate_plans_fail_closed_without_partial_result():
    result = reconcile_annual_student_loans(basis(), [1, 2, "postgraduate"], [])
    assert result.calculation_status == "unsupported_plan_combination"
    assert result.components == ()
    assert result.income_basis is None
    assert "1" in result.unsupported_plans


@pytest.mark.parametrize("plans", [["mystery"], [2, "mystery"]])
def test_unknown_plan_reconciliation_fails_closed_without_partial_result(plans):
    result = reconcile_annual_student_loans(basis(), plans, [])
    assert result.calculation_status == "unsupported_plan_combination"
    assert result.components == ()
    assert result.income_basis is None
    assert "mystery" in result.unsupported_plans
    assert "no_student_loan_or_total_monetary_result_available" in result.limitations


def test_incomplete_basis_provenance_prevents_liability_calculation():
    result = reconcile_annual_student_loans(
        basis(qualifying_pension_relief_confirmed=False), [2], []
    )
    assert result.calculation_status == "insufficient_facts"
    assert result.components == ()
    assert "annual_loan_income_basis_not_fully_evidenced" in result.limitations


def test_missing_deduction_evidence_preserves_liability_but_not_remaining_amount():
    result = reconcile_annual_student_loans(basis(), [2], [])
    component = result.component(LoanComponent.PLAN_2)
    assert component.annual_liability == Decimal("6625.00")
    assert component.evidenced_deductions is None
    assert component.remaining_self_assessment_amount is None
    assert result.calculation_status == "insufficient_facts"


def test_separate_employment_evidence_is_summed_without_losing_provenance():
    result = reconcile_annual_student_loans(
        basis(), [2], [
            deduction(LoanComponent.PLAN_2, "1000", "E-SL-A", employment="job-a"),
            deduction(LoanComponent.PLAN_2, "2000", "E-SL-B", employment="job-b"),
        ], declared_employment_ids=("job-a", "job-b")
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.evidenced_deductions == Decimal("3000.00")
    assert component.selected_evidence_ids == ("E-SL-A", "E-SL-B")


def test_conflicting_same_period_cumulative_evidence_is_not_selected():
    result = reconcile_annual_student_loans(
        basis(), [2], [
            deduction(LoanComponent.PLAN_2, "2900", "E-SL-A"),
            deduction(LoanComponent.PLAN_2, "3000", "E-SL-B"),
        ]
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.calculation_status == "conflict_requires_review"
    assert component.evidenced_deductions is None
    assert component.retained_evidence_ids == ("E-SL-A", "E-SL-B")
    assert component.conflict_candidate_amounts == (Decimal("2900.00"), Decimal("3000.00"))
    assert component.conflict_difference == Decimal("100.00")
    assert component.remaining_amount_low == Decimal("3625.00")
    assert component.remaining_amount_high == Decimal("3725.00")


def test_newer_cumulative_evidence_supersedes_older_same_employment_observation():
    result = reconcile_annual_student_loans(
        basis(), [2], [
            deduction(LoanComponent.PLAN_2, "2500", "E-SL-OLD", effective=date(2027, 3, 1)),
            deduction(LoanComponent.PLAN_2, "3000", "E-SL-NEW", effective=date(2027, 4, 5)),
        ]
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.evidenced_deductions == Decimal("3000.00")
    assert component.selected_evidence_ids == ("E-SL-NEW",)
    assert component.retained_evidence_ids == ("E-SL-OLD", "E-SL-NEW")
    assert "effective_through:2027-04-05" in component.selection_reasons[0]


def test_deductions_above_liability_are_not_reported_as_confirmed_refund():
    result = reconcile_annual_student_loans(
        basis("30000"), [2], [deduction(LoanComponent.PLAN_2, "100", "E-SL-EXCESS")]
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.annual_liability == Decimal("55.00")
    assert component.remaining_self_assessment_amount == Decimal("0.00")
    assert component.apparent_excess_deductions == Decimal("45.00")
    assert "apparent_excess_is_not_a_confirmed_refund" in component.uncertainties


def test_declared_employment_scope_must_be_completely_evidenced():
    result = reconcile_annual_student_loans(
        basis(), [2], [deduction(LoanComponent.PLAN_2, "3000", "E-SL-A")],
        declared_employment_ids=("synthetic-job-a", "synthetic-job-b"),
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.calculation_status == "insufficient_facts"
    assert component.remaining_self_assessment_amount is None


def test_future_period_evidence_is_rejected_and_stale_evidence_is_qualified():
    early_basis = AnnualLoanIncomeBasis(
        "103000", ("E-SYNTHETIC-ANNUAL-BASIS",), True, True,
        (LoanBasisEvidence("E-SYNTHETIC-ANNUAL-BASIS", "synthetic", "synthetic://basis", "person", date(2027, 3, 1), "2026/27 basis as known", True),),
    )
    future = reconcile_annual_student_loans(
        early_basis, [2], [deduction(LoanComponent.PLAN_2, "3000", "E-FUTURE", effective=date(2027, 4, 5))],
        as_of=date(2027, 3, 1),
    )
    assert future.component(LoanComponent.PLAN_2).calculation_status == "insufficient_facts"
    assert future.component(LoanComponent.PLAN_2).evidence_decisions[0].decision == "excluded"

    stale = reconcile_annual_student_loans(
        basis(), [2], [deduction(LoanComponent.PLAN_2, "3000", "E-STALE", effective=date(2026, 12, 1))],
        as_of=date(2027, 4, 5),
    )
    component = stale.component(LoanComponent.PLAN_2)
    assert component.calculation_status == "calculated_with_material_uncertainty"
    assert "deduction_evidence_may_be_stale" in component.uncertainties
    assert component.stale_reconciliation_effect == Decimal("3000.00")
    assert component.range_completeness == "partial"


def test_stale_reconciliation_effect_is_capped_by_annual_liability():
    result = reconcile_annual_student_loans(
        basis("30000"), [2], [
            deduction(LoanComponent.PLAN_2, "100", "E-STALE-EXCESS", effective=date(2026, 12, 1))
        ],
        as_of=date(2027, 4, 5),
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.annual_liability == Decimal("55.00")
    assert component.remaining_self_assessment_amount == Decimal("0.00")
    assert component.stale_reconciliation_effect == Decimal("55.00")


def test_stale_effect_accounts_for_fresh_deductions_already_covering_liability():
    # £31,112 gives a £155 Plan 2 liability. Fresh £145 leaves only £10 for
    # stale £50 evidence to affect: with both residual is nil, without stale £10.
    result = reconcile_annual_student_loans(
        basis("31112"), [2], [
            deduction(LoanComponent.PLAN_2, "145", "E-FRESH", employment="job-fresh", effective=date(2027, 4, 5)),
            deduction(LoanComponent.PLAN_2, "50", "E-STALE", employment="job-stale", effective=date(2026, 12, 1)),
        ],
        as_of=date(2027, 4, 5),
        declared_employment_ids=("job-fresh", "job-stale"),
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.annual_liability == Decimal("155.00")
    assert component.remaining_self_assessment_amount == Decimal("0.00")
    assert component.stale_reconciliation_effect == Decimal("10.00")


def test_multi_employment_conflict_range_includes_non_conflicting_selected_deductions():
    result = reconcile_annual_student_loans(
        basis(), [2], [
            deduction(LoanComponent.PLAN_2, "1000", "E-JOB-A", employment="job-a"),
            deduction(LoanComponent.PLAN_2, "2900", "E-JOB-B-1", employment="job-b"),
            deduction(LoanComponent.PLAN_2, "3000", "E-JOB-B-2", employment="job-b"),
        ], declared_employment_ids=("job-a", "job-b"),
    )
    component = result.component(LoanComponent.PLAN_2)
    assert component.selected_evidence_ids == ("E-JOB-A",)
    assert component.remaining_amount_low == Decimal("2625.00")
    assert component.remaining_amount_high == Decimal("2725.00")
    decisions = {item.evidence_id: item for item in component.evidence_decisions}
    assert decisions["E-JOB-A"].decision == "selected"
    assert decisions["E-JOB-B-1"].decision == "conflict"
    assert decisions["E-JOB-B-1"].original_amount == Decimal("2900.00")
    assert component.range_completeness == "complete_for_identified_conflicts_only"


def test_observation_before_effective_period_is_timeline_incoherent_and_excluded():
    item = deduction(LoanComponent.PLAN_2, "3000", "E-INCOHERENT")
    object.__setattr__(item, "observed_on", date(2027, 3, 1))
    result = reconcile_annual_student_loans(basis(), [2], [item])
    component = result.component(LoanComponent.PLAN_2)
    assert component.calculation_status == "insufficient_facts"
    assert component.evidence_decisions[0].decision == "excluded"
    assert component.evidence_decisions[0].effective_through == date(2027, 4, 5)


def test_basis_ids_without_complete_matching_structured_provenance_fail_closed():
    for evidence_items in (
        (),
        (LoanBasisEvidence("OTHER", "synthetic", "synthetic://other", "person", date(2027, 4, 5), "2026/27", True),),
        (LoanBasisEvidence("E-SYNTHETIC-ANNUAL-BASIS", "synthetic", "synthetic://basis", "person", date(2027, 4, 5), "2026/27", False),),
    ):
        result = reconcile_annual_student_loans(
            AnnualLoanIncomeBasis("103000", ("E-SYNTHETIC-ANNUAL-BASIS",), True, True, evidence_items),
            [2], [deduction(LoanComponent.PLAN_2, "3000", "E-SL")],
            as_of=AS_OF, declared_employment_ids=("synthetic-job-a",),
        )
        assert result.calculation_status == "insufficient_facts"
        assert result.components == ()
