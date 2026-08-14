"""Provider-neutral internal composition of independently bounded results.

Composition does not recalculate, reconcile or aggregate money. It links an
annual tax-position result to an annual student-loan reconciliation by stable
references and preserves each producer's status and limitations. There is no
customer balance, amount-due, reserve, filing or payment output.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re

from .annual_loan_reconciliation import (
    AnnualLoanReconciliation,
    LoanComponent,
    LoanBasisEvidence,
    LoanEvidenceDecision,
)
from .integrated_annual_position import AnnualPositionResult


@dataclass(frozen=True)
class ReferencedAnnualTaxComponents:
    reference: str
    ruleset_version: str
    calculation_status: str
    income_tax_before_limitations: Decimal | None
    class_4_ni: Decimal
    hicbc: Decimal | None
    tax_total: Decimal | None
    included_families: tuple[str, ...]
    unsupported_families: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ReferencedLoanComponent:
    component: LoanComponent
    annual_liability: Decimal
    evidenced_deductions: Decimal | None
    remaining_self_assessment_amount: Decimal | None
    calculation_status: str
    selected_evidence_ids: tuple[str, ...]
    retained_evidence_ids: tuple[str, ...]
    selection_reasons: tuple[str, ...]
    evidence_decisions: tuple[LoanEvidenceDecision, ...]
    uncertainties: tuple[str, ...]
    conflict_candidate_amounts: tuple[Decimal, ...]
    conflict_difference: Decimal | None
    remaining_amount_low: Decimal | None
    remaining_amount_high: Decimal | None
    range_completeness: str | None
    apparent_excess_deductions: Decimal | None
    stale_reconciliation_effect: Decimal | None


@dataclass(frozen=True)
class ReferencedAnnualLoanComponents:
    reference: str
    ruleset_version: str
    calculation_status: str
    income_basis: Decimal | None
    basis_evidence_ids: tuple[str, ...]
    basis_evidence: tuple[LoanBasisEvidence, ...]
    unsupported_plans: tuple[str, ...]
    as_of: date | None
    declared_employment_ids: tuple[str, ...]
    components: tuple[ReferencedLoanComponent, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]
    stale_after_days: int


@dataclass(frozen=True)
class InternalAnnualComposition:
    contract_version: str
    tax_year: str
    composition_status: str
    component_set_complete: bool
    annual_tax: ReferencedAnnualTaxComponents
    student_loans: ReferencedAnnualLoanComponents
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _reference(value: str, name: str, namespace: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a stable typed reference")
    prefix = f"{namespace}:"
    if not value.startswith(prefix) or not _REFERENCE_ID.fullmatch(value[len(prefix):]):
        raise ValueError(
            f"{name} must use {namespace}: followed by an immutable identifier"
        )
    return value


def _composition_status(tax_status: str, loan_status: str, complete: bool) -> str:
    if complete:
        return "components_available"
    statuses = {tax_status, loan_status}
    if "conflict_requires_review" in statuses:
        return "conflict_requires_review"
    if statuses & {"unsupported_rule", "unsupported_plan_combination"}:
        return "unsupported_rule"
    if "insufficient_facts" in statuses:
        return "insufficient_facts"
    if "calculated_with_material_uncertainty" in statuses:
        return "calculated_with_material_uncertainty"
    return "insufficient_facts"


def compose_internal_annual_position(
    annual_tax: AnnualPositionResult,
    student_loans: AnnualLoanReconciliation,
    *,
    annual_tax_reference: str,
    student_loan_reference: str,
) -> InternalAnnualComposition:
    """Reference two results without converting them into a combined balance."""
    if annual_tax.tax_year != student_loans.tax_year:
        raise ValueError("Referenced results must have the same tax year")

    tax_ref = _reference(annual_tax_reference, "annual_tax_reference", "annual-position")
    loan_ref = _reference(student_loan_reference, "student_loan_reference", "loan-reconciliation")
    if tax_ref == loan_ref:
        raise ValueError("Producer references must be distinct")
    tax_complete = annual_tax.calculation_status == "calculated" and annual_tax.total_liability is not None
    loan_complete = (
        student_loans.calculation_status == "calculated"
        and bool(student_loans.components)
        and all(
            component.calculation_status == "calculated"
            and component.evidenced_deductions is not None
            and component.remaining_self_assessment_amount is not None
            for component in student_loans.components
        )
    )
    complete = tax_complete and loan_complete
    composition_status = _composition_status(
        annual_tax.calculation_status, student_loans.calculation_status, complete
    )

    loan_components = tuple(
        ReferencedLoanComponent(
            component=item.component,
            annual_liability=item.annual_liability,
            evidenced_deductions=item.evidenced_deductions,
            remaining_self_assessment_amount=item.remaining_self_assessment_amount,
            calculation_status=item.calculation_status,
            selected_evidence_ids=item.selected_evidence_ids,
            retained_evidence_ids=item.retained_evidence_ids,
            selection_reasons=item.selection_reasons,
            evidence_decisions=item.evidence_decisions,
            uncertainties=item.uncertainties,
            conflict_candidate_amounts=item.conflict_candidate_amounts,
            conflict_difference=item.conflict_difference,
            remaining_amount_low=item.remaining_amount_low,
            remaining_amount_high=item.remaining_amount_high,
            range_completeness=item.range_completeness,
            apparent_excess_deductions=item.apparent_excess_deductions,
            stale_reconciliation_effect=item.stale_reconciliation_effect,
        )
        for item in student_loans.components
    )
    limitations = (
        "components_are_linked_not_aggregated",
        "no_combined_customer_balance_or_amount_due",
    )
    if not tax_complete:
        limitations += ("annual_tax_component_not_complete",)
    if not loan_complete:
        limitations += ("student_loan_reconciliation_not_complete",)
    return InternalAnnualComposition(
        contract_version="reserved-internal-annual-composition/1.0",
        tax_year=annual_tax.tax_year,
        composition_status=composition_status,
        component_set_complete=complete,
        annual_tax=ReferencedAnnualTaxComponents(
            reference=tax_ref,
            ruleset_version=annual_tax.ruleset_version,
            calculation_status=annual_tax.calculation_status,
            income_tax_before_limitations=annual_tax.income_tax_before_limitations,
            class_4_ni=annual_tax.class_4_ni,
            hicbc=annual_tax.hicbc,
            tax_total=annual_tax.total_liability,
            included_families=annual_tax.included_families,
            unsupported_families=annual_tax.unsupported_families,
            limitations=annual_tax.limitations,
        ),
        student_loans=ReferencedAnnualLoanComponents(
            reference=loan_ref,
            ruleset_version=student_loans.ruleset_version,
            calculation_status=student_loans.calculation_status,
            income_basis=student_loans.income_basis,
            basis_evidence_ids=student_loans.basis_evidence_ids,
            basis_evidence=student_loans.basis_evidence,
            unsupported_plans=student_loans.unsupported_plans,
            as_of=student_loans.as_of,
            declared_employment_ids=student_loans.declared_employment_ids,
            components=loan_components,
            limitations=student_loans.limitations,
            prohibited_uses=student_loans.prohibited_uses,
            stale_after_days=student_loans.stale_after_days,
        ),
        limitations=limitations,
        prohibited_uses=("customer_presentation", "reserve_guidance", "filing", "payment", "refund"),
    )
