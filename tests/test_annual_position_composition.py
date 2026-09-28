from datetime import date
from decimal import Decimal

import pytest

from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis,
    LoanBasisEvidence,
    DeductionRepresentation,
    LoanComponent,
    LoanDeductionEvidence,
    reconcile_annual_student_loans,
)
from reserved.engines.annual_position_composition import compose_internal_annual_position
from reserved.engines.integrated_annual_position import calculate_annual_position


def loans(*, evidence=True):
    deductions = []
    if evidence:
        deductions = [LoanDeductionEvidence(
            evidence_id="E-SYNTHETIC-SL",
            component=LoanComponent.PLAN_2,
            amount="3000",
            tax_year="2026/27",
            observed_on=date(2027, 4, 5),
            effective_through=date(2027, 4, 5),
            employment_id="synthetic-job-a",
            representation=DeductionRepresentation.EMPLOYMENT_CUMULATIVE,
            complete_for_representation=True,
            source_kind="synthetic_document",
            source_reference="synthetic://student-loan",
        )]
    return reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-SYNTHETIC-BASIS",), True, True, (
            LoanBasisEvidence("E-SYNTHETIC-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),
        )),
        [2],
        deductions,
        as_of=date(2027, 4, 5),
        declared_employment_ids=("synthetic-job-a",),
    )


def test_complete_components_are_linked_without_combining_money():
    result = compose_internal_annual_position(
        calculate_annual_position({
            "employment_income": "30000",
            "blind_persons_allowance_entitled": False,
            "blind_persons_allowance_transferred_in": "0",
            "blind_persons_allowance_transferred_out": "0",
        }),
        loans(),
        annual_tax_reference="annual-position:synthetic-1",
        student_loan_reference="loan-reconciliation:synthetic-1",
    )
    assert result.component_set_complete is True
    assert result.composition_status == "components_available"
    assert result.annual_tax.tax_total == Decimal("3486.00")
    component = result.student_loans.components[0]
    assert component.annual_liability == Decimal("6625.00")
    assert component.remaining_self_assessment_amount == Decimal("3625.00")
    assert not hasattr(result, "combined_balance")
    assert not hasattr(result, "amount_due")
    assert "customer_presentation" in result.prohibited_uses
    assert result.annual_tax.ruleset_version == "uk-2026-27-v4"
    assert result.annual_tax.included_families == ("income_tax", "class_4_ni")
    assert result.student_loans.ruleset_version == "uk-2026-27-v4"
    assert result.student_loans.basis_evidence_ids == ("E-SYNTHETIC-BASIS",)
    assert result.student_loans.as_of == date(2027, 4, 5)
    assert result.student_loans.declared_employment_ids == ("synthetic-job-a",)
    assert result.student_loans.prohibited_uses == (
        "customer_combined_balance", "filing", "payment", "refund"
    )


def test_unsupported_annual_tax_withholds_complete_component_set():
    result = compose_internal_annual_position(
        calculate_annual_position({
            "uk_resident": True,
            "employment_income": "30000",
            "foreign_property_profit": "10000",
            "foreign_tax_paid": "1500",
        }),
        loans(),
        annual_tax_reference="annual-position:synthetic-ftcr",
        student_loan_reference="loan-reconciliation:synthetic-2",
    )
    assert result.component_set_complete is False
    assert result.composition_status == "unsupported_rule"
    assert result.annual_tax.tax_total is None
    assert result.annual_tax.unsupported_families == ("foreign_tax_credit_relief",)
    assert "annual_tax_component_not_complete" in result.limitations


def test_incomplete_loan_evidence_preserves_separate_liability_and_uncertainty():
    result = compose_internal_annual_position(
        calculate_annual_position({"employment_income": "30000"}),
        loans(evidence=False),
        annual_tax_reference="annual-position:synthetic-3",
        student_loan_reference="loan-reconciliation:synthetic-incomplete",
    )
    assert result.component_set_complete is False
    component = result.student_loans.components[0]
    assert component.annual_liability == Decimal("6625.00")
    assert component.evidenced_deductions is None
    assert component.remaining_self_assessment_amount is None
    assert component.calculation_status == "insufficient_facts"
    assert result.composition_status == "insufficient_facts"


def test_mismatched_tax_year_and_blank_references_fail_closed():
    annual = calculate_annual_position({"employment_income": "30000"})
    loan = loans()
    object.__setattr__(loan, "tax_year", "2025/26")
    with pytest.raises(ValueError, match="same tax year"):
        compose_internal_annual_position(
            annual, loan, annual_tax_reference="annual:1", student_loan_reference="loan:1"
        )

    object.__setattr__(loan, "tax_year", "2026/27")
    with pytest.raises(ValueError, match="immutable identifier"):
        compose_internal_annual_position(
            annual, loan, annual_tax_reference=" ", student_loan_reference="loan:1"
        )


@pytest.mark.parametrize(
    "tax_ref,loan_ref",
    [
        ("annual-position:display label", "loan-reconciliation:id"),
        ("wrong:tax", "loan-reconciliation:id"),
        ("annual-position:id", "loan-reconciliation:"),
        ("annual-position:id", "annual-position:id"),
    ],
)
def test_references_require_typed_immutable_identifier_syntax(tax_ref, loan_ref):
    with pytest.raises(ValueError):
        compose_internal_annual_position(
            calculate_annual_position({"employment_income": "30000"}),
            loans(),
            annual_tax_reference=tax_ref,
            student_loan_reference=loan_ref,
        )


def test_conflict_provenance_bounds_and_decisions_are_preserved_losslessly():
    conflict = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (
            LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),
        )),
        [2],
        [
            LoanDeductionEvidence("E-A", LoanComponent.PLAN_2, "999", "2026/27", date(2027, 4, 5), date(2027, 4, 5), "job-a", DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True, "document", "synthetic://a"),
            LoanDeductionEvidence("E-B", LoanComponent.PLAN_2, "3000", "2026/27", date(2027, 4, 5), date(2027, 4, 5), "job-a", DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True, "document", "synthetic://b"),
        ],
        as_of=date(2027, 4, 5),
        declared_employment_ids=("job-a",),
    )
    result = compose_internal_annual_position(
        calculate_annual_position({"employment_income": "30000"}), conflict,
        annual_tax_reference="annual-position:conflict",
        student_loan_reference="loan-reconciliation:conflict",
    )
    component = result.student_loans.components[0]
    assert result.composition_status == "conflict_requires_review"
    assert component.retained_evidence_ids == ("E-A", "E-B")
    assert component.conflict_candidate_amounts == (Decimal("999.00"), Decimal("3000.00"))
    assert component.conflict_difference == Decimal("100.00")
    assert (component.remaining_amount_low, component.remaining_amount_high) == (
        Decimal("3625.00"), Decimal("3725.00")
    )
    assert component.range_completeness == "complete_for_identified_conflicts_only"
    assert {item.decision for item in component.evidence_decisions} == {"conflict"}
    assert component.evidence_decisions[0].source_reference == "synthetic://a"


def test_material_uncertainty_effects_and_exact_prohibitions_survive_composition():
    stale = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("30000", ("E-BASIS",), True, True, (
            LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),
        )), [2],
        [LoanDeductionEvidence("E-STALE", LoanComponent.PLAN_2, "100", "2026/27", date(2026, 12, 1), date(2026, 12, 1), "job-a", DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True, "document", "synthetic://stale")],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    result = compose_internal_annual_position(
        calculate_annual_position({
            "employment_income": "30000",
            "blind_persons_allowance_entitled": False,
            "blind_persons_allowance_transferred_in": "0",
            "blind_persons_allowance_transferred_out": "0",
        }), stale,
        annual_tax_reference="annual-position:stale",
        student_loan_reference="loan-reconciliation:stale",
    )
    component = result.student_loans.components[0]
    assert result.composition_status == "calculated_with_material_uncertainty"
    assert component.apparent_excess_deductions == Decimal("45.00")
    assert component.stale_reconciliation_effect == Decimal("55.00")
    assert component.range_completeness == "partial"


def test_unsupported_plans_and_status_propagate_without_components():
    unsupported = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("40000", ("E-BASIS",), True, True), [1, 2], [],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    result = compose_internal_annual_position(
        calculate_annual_position({"employment_income": "30000"}), unsupported,
        annual_tax_reference="annual-position:unsupported",
        student_loan_reference="loan-reconciliation:unsupported",
    )
    assert result.composition_status == "unsupported_rule"
    assert result.student_loans.unsupported_plans == ("1", "2")
    assert result.student_loans.components == ()
