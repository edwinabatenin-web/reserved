from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis,
    DeductionRepresentation,
    LoanBasisEvidence,
    LoanComponent,
    LoanDeductionEvidence,
    reconcile_annual_student_loans,
)
from reserved.engines.cash_ready_annual_position import (
    NoStudentLoanEvidence,
    annual_position_identity,
    compose_cash_ready_annual_position,
    student_loan_position_identity,
)
from reserved.engines.integrated_annual_position import calculate_annual_position


AS_OF = date(2027, 4, 5)
BPA = {
    "blind_persons_allowance_entitled": False,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}


def annual(**facts):
    return calculate_annual_position({"employment_income": "30000", **BPA, **facts})


def loans(plans=(2,), deductions=((LoanComponent.PLAN_2, "3000", "E-PLAN2"),)):
    basis_evidence = LoanBasisEvidence(
        "E-BASIS", "synthetic", "synthetic://basis", "person-a", AS_OF,
        "2026/27 annual basis", True,
    )
    evidence = tuple(
        LoanDeductionEvidence(
            evidence_id,
            component,
            amount,
            "2026/27",
            AS_OF,
            AS_OF,
            "job-a",
            DeductionRepresentation.EMPLOYMENT_CUMULATIVE,
            True,
            "synthetic",
            f"synthetic://{evidence_id}",
        )
        for component, amount, evidence_id in deductions
    )
    return reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (basis_evidence,)),
        plans,
        evidence,
        as_of=AS_OF,
        declared_employment_ids=("job-a",),
    )


def compose(tax=None, loan_position=None, **changes):
    tax = tax or annual()
    loan_position = loan_position or loans()
    return compose_cash_ready_annual_position(
        tax,
        loan_position,
        annual_tax_reference=changes.pop(
            "annual_tax_reference", annual_position_identity(tax)
        ),
        student_loan_reference=changes.pop(
            "student_loan_reference", student_loan_position_identity(loan_position)
        ),
        as_of=changes.pop("as_of", AS_OF),
        **changes,
    )


def test_complete_tax_and_plan_2_create_one_classified_final_liability():
    result = compose()

    assert result.calculation_status == "ready_for_w2_s6"
    assert result.component_set_complete is True
    assert result.annual_tax_liability == Decimal("3486.00")
    assert result.student_loan_self_assessment_amount == Decimal("3625.00")
    assert result.final_self_assessment_liability == Decimal("7111.00")
    assert result.poa_eligible_families == ("income_tax", "class_4_ni")
    assert result.poa_excluded_families == ("plan_2",)
    assert result.evidence_ids == ("E-BASIS", "E-PLAN2")
    assert not hasattr(result, "poa_basis_amount")
    assert not hasattr(result, "tax_deducted_at_source")
    assert "current_forecast_as_hmrc_poa_basis" in result.prohibited_uses
    assert "payment" in result.prohibited_uses


def test_plan_2_and_pgl_are_summed_once_but_remain_separate_components():
    result = compose(
        loan_position=loans(
            (2, "postgraduate"),
            (
                (LoanComponent.PLAN_2, "3000", "E-PLAN2"),
                (LoanComponent.POSTGRADUATE, "1800", "E-PGL"),
            ),
        )
    )

    assert result.student_loan_self_assessment_amount == Decimal("6745.00")
    assert result.final_self_assessment_liability == Decimal("10231.00")
    assert result.poa_excluded_families == ("plan_2", "postgraduate")
    assert tuple(item.remaining_self_assessment_amount for item in result.loan_components) == (
        Decimal("3625.00"),
        Decimal("3120.00"),
    )


def test_explicit_complete_no_loan_evidence_supports_tax_only_position():
    evidence = NoStudentLoanEvidence(
        "E-NO-LOAN",
        "2026/27",
        "uk-2026-27-v4",
        AS_OF,
        "person-a",
        "customer_declaration",
        "synthetic://no-loan",
        True,
    )
    result = compose(
        loan_position=evidence,
    )

    assert result.component_set_complete is True
    assert result.student_loan_self_assessment_amount == Decimal("0")
    assert result.final_self_assessment_liability == Decimal("3486.00")
    assert result.loan_components == ()
    assert result.poa_excluded_families == ()
    assert result.evidence_ids == ("E-NO-LOAN",)


def test_unsupported_tax_suppresses_every_cash_amount():
    result = compose(
        tax=annual(
            uk_resident=True,
            foreign_property_profit="10000",
            foreign_tax_paid="1500",
        )
    )

    assert result.calculation_status == "unresolved"
    assert result.component_set_complete is False
    assert result.annual_tax_liability is None
    assert result.student_loan_self_assessment_amount is None
    assert result.final_self_assessment_liability is None
    assert result.poa_eligible_families == ()
    assert "annual_tax_component_not_complete" in result.limitations


def test_incomplete_or_stale_loan_reconciliation_suppresses_all_amounts():
    incomplete = loans(deductions=())
    incomplete_result = compose(loan_position=incomplete)
    assert incomplete_result.final_self_assessment_liability is None
    assert "student_loan_reconciliation_not_complete" in incomplete_result.limitations

    stale = loans(
        deductions=((LoanComponent.PLAN_2, "3000", "E-STALE"),)
    )
    object.__setattr__(stale.components[0], "range_completeness", "partial")
    stale_result = compose(loan_position=stale)
    assert stale_result.final_self_assessment_liability is None
    assert "student_loan_component_reconciliation_invalid" in stale_result.limitations


def test_tax_year_ruleset_and_final_period_must_match():
    wrong_rules = replace(loans(), ruleset_version="other")
    result = compose(loan_position=wrong_rules)
    assert result.final_self_assessment_liability is None
    assert "student_loan_tax_year_or_ruleset_mismatch" in result.limitations

    early = compose(as_of=date(2027, 4, 4))
    assert early.final_self_assessment_liability is None
    assert "student_loan_period_not_final" in early.limitations


def test_forged_tax_and_loan_arithmetic_fail_closed():
    original_tax = annual()
    tax_reference = annual_position_identity(original_tax)
    forged_tax = replace(
        original_tax,
        non_savings_tax=original_tax.non_savings_tax + Decimal("100.00"),
        income_tax_before_limitations=(
            original_tax.income_tax_before_limitations + Decimal("100.00")
        ),
        total_liability=original_tax.total_liability + Decimal("100.00"),
    )
    with pytest.raises(ValueError, match="exact supplied content"):
        compose(tax=forged_tax, annual_tax_reference=tax_reference)

    original = loans()
    loan_reference = student_loan_position_identity(original)
    forged_component = replace(
        original.components[0],
        annual_liability=original.components[0].annual_liability + Decimal("100.00"),
        remaining_self_assessment_amount=(
            original.components[0].remaining_self_assessment_amount + Decimal("100.00")
        ),
    )
    forged_loans = replace(original, components=(forged_component,))
    with pytest.raises(ValueError, match="exact supplied content"):
        compose(loan_position=forged_loans, student_loan_reference=loan_reference)

    forged_rules = replace(annual(), ruleset_version="other")
    rules_result = compose(tax=forged_rules)
    assert rules_result.final_self_assessment_liability is None
    assert "annual_tax_ruleset_invalid" in rules_result.limitations


def test_reused_or_forged_loan_provenance_fails_closed():
    original = loans()
    duplicate_id_component = replace(
        original.components[0],
        selected_evidence_ids=("E-BASIS",),
        evidence_decisions=tuple(
            replace(decision, evidence_id="E-BASIS")
            if decision.decision == "selected"
            else decision
            for decision in original.components[0].evidence_decisions
        ),
    )
    reused = replace(original, components=(duplicate_id_component,))
    reused_result = compose(loan_position=reused)
    assert reused_result.final_self_assessment_liability is None
    assert "student_loan_evidence_identity_reused" in reused_result.limitations

    forged_basis = replace(original, basis_evidence=())
    basis_result = compose(loan_position=forged_basis)
    assert basis_result.final_self_assessment_liability is None
    assert "student_loan_basis_provenance_invalid" in basis_result.limitations


@pytest.mark.parametrize(
    "changes, limitation",
    [
        ({"complete_for_tax_year": False}, "student_loan_applicability_evidence_incomplete"),
        ({"as_of": date(2027, 4, 4)}, "student_loan_applicability_period_or_ruleset_mismatch"),
        ({"ruleset_version": "other"}, "student_loan_applicability_period_or_ruleset_mismatch"),
    ],
)
def test_no_loan_evidence_must_be_complete_and_exact(changes, limitation):
    values = {
        "evidence_id": "E-NO-LOAN",
        "tax_year": "2026/27",
        "ruleset_version": "uk-2026-27-v4",
        "as_of": AS_OF,
        "subject_reference": "person-a",
        "source_kind": "customer_declaration",
        "source_reference": "synthetic://no-loan",
        "complete_for_tax_year": True,
        **changes,
    }
    result = compose(
        loan_position=NoStudentLoanEvidence(**values),
    )
    assert result.final_self_assessment_liability is None
    assert limitation in result.limitations


@pytest.mark.parametrize(
    "changes",
    [
        {"complete_for_tax_year": 1},
        {"subject_reference": "   "},
        {"source_kind": " synthetic"},
        {"source_reference": ""},
    ],
)
def test_no_loan_evidence_rejects_truthy_non_boolean_and_blank_provenance(changes):
    values = {
        "evidence_id": "E-NO-LOAN",
        "tax_year": "2026/27",
        "ruleset_version": "uk-2026-27-v4",
        "as_of": AS_OF,
        "subject_reference": "person-a",
        "source_kind": "customer_declaration",
        "source_reference": "synthetic://no-loan",
        "complete_for_tax_year": True,
        **changes,
    }
    result = compose(loan_position=NoStudentLoanEvidence(**values))
    assert result.final_self_assessment_liability is None
    assert "student_loan_applicability_evidence_incomplete" in result.limitations


@pytest.mark.parametrize(
    "annual_ref,loan_ref",
    [
        ("wrong:tax", None),
        (None, "wrong:loan"),
        ("annual-position:display-label", None),
    ],
)
def test_source_references_must_be_typed_and_immutable(annual_ref, loan_ref):
    tax = annual()
    loan_position = loans()
    with pytest.raises(ValueError):
        compose(
            tax=tax,
            loan_position=loan_position,
            annual_tax_reference=annual_ref or annual_position_identity(tax),
            student_loan_reference=loan_ref or student_loan_position_identity(loan_position),
        )
