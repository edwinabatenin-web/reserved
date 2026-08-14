"""Bounded annual Self Assessment student-loan reconciliation.

Only a single Plan 2 undergraduate component and an optional postgraduate
component are supported. Annual liabilities are rounded down to whole pounds
before separately evidenced deductions are reconciled. This internal result is
not a customer bill, refund, collection instruction or combined reserve figure.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from enum import Enum
from typing import Any, Iterable

from .tax_config import get_config


ZERO = Decimal("0")
PENNY = Decimal("0.01")


class LoanComponent(str, Enum):
    PLAN_2 = "plan_2"
    POSTGRADUATE = "postgraduate"


class DeductionRepresentation(str, Enum):
    EMPLOYMENT_CUMULATIVE = "employment_cumulative"


@dataclass(frozen=True)
class AnnualLoanIncomeBasis:
    amount: Decimal | str | int
    evidence_ids: tuple[str, ...]
    qualifying_pension_relief_confirmed: bool
    taxable_income_scope_confirmed: bool
    evidence: tuple["LoanBasisEvidence", ...] = ()


@dataclass(frozen=True)
class LoanBasisEvidence:
    evidence_id: str
    source_kind: str
    source_reference: str
    subject_reference: str
    observed_on: date
    effective_period: str
    complete_for_basis: bool


@dataclass(frozen=True)
class LoanDeductionEvidence:
    evidence_id: str
    component: LoanComponent
    amount: Decimal | str | int
    tax_year: str
    observed_on: date
    effective_through: date
    employment_id: str
    representation: DeductionRepresentation
    complete_for_representation: bool
    source_kind: str
    source_reference: str


@dataclass(frozen=True)
class LoanEvidenceDecision:
    evidence_id: str
    decision: str
    reason: str
    original_amount: Decimal
    observed_on: date
    effective_through: date
    employment_id: str
    source_kind: str
    source_reference: str
    complete_for_representation: bool


@dataclass(frozen=True)
class AnnualLoanComponentResult:
    component: LoanComponent
    annual_liability: Decimal
    evidenced_deductions: Decimal | None
    remaining_self_assessment_amount: Decimal | None
    calculation_status: str
    selected_evidence_ids: tuple[str, ...]
    retained_evidence_ids: tuple[str, ...]
    uncertainties: tuple[str, ...]
    apparent_excess_deductions: Decimal | None = None
    selection_reasons: tuple[str, ...] = ()
    conflict_candidate_amounts: tuple[Decimal, ...] = ()
    conflict_difference: Decimal | None = None
    remaining_amount_low: Decimal | None = None
    remaining_amount_high: Decimal | None = None
    evidence_decisions: tuple[LoanEvidenceDecision, ...] = ()
    range_completeness: str | None = None
    stale_reconciliation_effect: Decimal | None = None


@dataclass(frozen=True)
class AnnualLoanReconciliation:
    contract_version: str
    tax_year: str
    ruleset_version: str
    income_basis: Decimal | None
    calculation_status: str
    components: tuple[AnnualLoanComponentResult, ...]
    basis_evidence_ids: tuple[str, ...]
    unsupported_plans: tuple[str, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]
    as_of: date | None = None
    declared_employment_ids: tuple[str, ...] = ()
    basis_evidence: tuple[LoanBasisEvidence, ...] = ()
    stale_after_days: int = 45

    def component(self, component: LoanComponent) -> AnnualLoanComponentResult:
        return next(item for item in self.components if item.component is component)


def _amount(value: Any, name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not amount.is_finite() or amount < ZERO:
        raise ValueError(f"{name} must be finite and non-negative")
    return amount


def _money(value: Decimal) -> Decimal:
    return value.quantize(PENNY)


def _normalise_plan(plan: Any) -> LoanComponent | None:
    if plan in (2, "2", "plan_2", LoanComponent.PLAN_2):
        return LoanComponent.PLAN_2
    if plan in ("postgraduate", "pgl", LoanComponent.POSTGRADUATE):
        return LoanComponent.POSTGRADUATE
    return None


def _reconcile_component(
    component: LoanComponent,
    liability: Decimal,
    supplied: tuple[LoanDeductionEvidence, ...],
    tax_year: str,
    as_of: date,
    declared_employment_ids: tuple[str, ...],
    stale_after_days: int,
) -> AnnualLoanComponentResult:
    retained = tuple(item for item in supplied if item.component is component)
    def excluded_reason(item):
        if item.tax_year != tax_year or not (
            date(2026, 4, 6) <= item.effective_through <= date(2027, 4, 5)
        ) or item.effective_through > item.observed_on or item.observed_on > as_of:
            return "outside_tax_year_as_of_or_coherent_timeline"
        return "incomplete_or_incompatible_representation_for_declared_scope"

    usable = tuple(item for item in retained if (
        item.tax_year == tax_year
        and item.evidence_id
        and item.employment_id
        and item.source_kind
        and item.source_reference
        and item.complete_for_representation
        and item.representation is DeductionRepresentation.EMPLOYMENT_CUMULATIVE
        and date(2026, 4, 6) <= item.effective_through <= date(2027, 4, 5)
        and item.effective_through <= item.observed_on <= as_of
    ))
    retained_ids = tuple(item.evidence_id for item in retained if item.evidence_id)
    usable_employments = {item.employment_id for item in usable}
    if not usable or usable_employments != set(declared_employment_ids):
        scope_decisions = tuple(
            LoanEvidenceDecision(
                item.evidence_id,
                "excluded" if item not in usable else "not_selected",
                excluded_reason(item) if item not in usable
                else "declared_employment_scope_incomplete",
                _money(_amount(item.amount, "deduction amount")), item.observed_on,
                item.effective_through, item.employment_id, item.source_kind,
                item.source_reference, item.complete_for_representation,
            )
            for item in retained
        )
        return AnnualLoanComponentResult(
            component, liability, None, None, "insufficient_facts", (), retained_ids,
            ("deduction_evidence_incomplete_for_declared_employment_scope",),
            evidence_decisions=scope_decisions,
            range_completeness="partial",
        )

    selected: list[LoanDeductionEvidence] = []
    superseded: list[LoanDeductionEvidence] = []
    conflict_groups: list[tuple[LoanDeductionEvidence, ...]] = []
    for employment_id in dict.fromkeys(item.employment_id for item in usable):
        candidates = tuple(item for item in usable if item.employment_id == employment_id)
        newest_date = max(item.effective_through for item in candidates)
        newest = tuple(item for item in candidates if item.effective_through == newest_date)
        amounts = {_money(_amount(item.amount, "deduction amount")) for item in newest}
        if len(amounts) != 1:
            conflict_groups.append(newest)
        else:
            chosen = max(newest, key=lambda item: (item.observed_on, item.evidence_id))
            selected.append(chosen)
            superseded.extend(item for item in candidates if item is not chosen)

    rejected = tuple(item for item in retained if item not in usable)
    decisions = tuple(
        LoanEvidenceDecision(
            item.evidence_id, decision,
            excluded_reason(item) if decision == "excluded" else reason,
            _money(_amount(item.amount, "deduction amount")),
            item.observed_on, item.effective_through, item.employment_id,
            item.source_kind, item.source_reference, item.complete_for_representation,
        )
        for decision, reason, items in (
            ("selected", "latest_complete_cumulative_for_declared_employment", tuple(selected)),
            ("superseded", "older_or_duplicate_cumulative_observation_retained", tuple(superseded)),
            ("conflict", "same_effective_period_has_different_values", tuple(item for group in conflict_groups for item in group)),
            ("excluded", "item_specific", rejected),
        )
        for item in items
    )
    if conflict_groups:
        fixed_paid = sum((_amount(item.amount, "deduction amount") for item in selected), ZERO)
        group_amounts = [
            tuple(sorted({_money(_amount(item.amount, "deduction amount")) for item in group}))
            for group in conflict_groups
        ]
        possible_paid = [fixed_paid]
        for amounts in group_amounts:
            possible_paid = [base + amount for base in possible_paid for amount in amounts]
        low_paid, high_paid = min(possible_paid), max(possible_paid)
        candidates = tuple(sorted({amount for amounts in group_amounts for amount in amounts}))
        return AnnualLoanComponentResult(
            component, liability, None, None, "conflict_requires_review",
            tuple(item.evidence_id for item in selected), retained_ids,
            ("conflicting_cumulative_deduction_evidence",),
            selection_reasons=tuple(
                f"selected_latest_complete_cumulative_evidence_for:{item.employment_id}:effective_through:{item.effective_through.isoformat()}"
                for item in selected
            ) + ("no_conflicting_candidate_selected",),
            conflict_candidate_amounts=candidates,
            conflict_difference=_money(high_paid - low_paid),
            remaining_amount_low=_money(max(ZERO, liability - high_paid)),
            remaining_amount_high=_money(max(ZERO, liability - low_paid)),
            evidence_decisions=decisions,
            range_completeness="complete_for_identified_conflicts_only",
        )

    deductions = _money(sum((_amount(item.amount, "deduction amount") for item in selected), ZERO))
    remaining = _money(max(ZERO, liability - deductions))
    excess = _money(max(ZERO, deductions - liability))
    status = "calculated" if excess == ZERO else "calculated_with_material_uncertainty"
    stale = tuple(item for item in selected if (as_of - item.effective_through).days > stale_after_days)
    uncertainties = (() if excess == ZERO else ("apparent_excess_is_not_a_confirmed_refund",)) + (
        ("deduction_evidence_may_be_stale",) if stale else ()
    )
    if stale and status == "calculated":
        status = "calculated_with_material_uncertainty"
    return AnnualLoanComponentResult(
        component, liability, deductions, remaining, status,
        tuple(item.evidence_id for item in selected), retained_ids, uncertainties,
        excess if excess > ZERO else None,
        tuple(
            f"selected_latest_complete_cumulative_evidence_for:{item.employment_id}:effective_through:{item.effective_through.isoformat()}"
            for item in selected
        ),
        evidence_decisions=decisions,
        range_completeness="partial" if stale else "complete_for_declared_employment_scope_as_of_evidence_dates",
        stale_reconciliation_effect=_money(min(
            sum((_amount(item.amount, "deduction amount") for item in stale), ZERO),
            max(ZERO, liability - sum(
                (_amount(item.amount, "deduction amount") for item in selected if item not in stale),
                ZERO,
            )),
        )) if stale else None,
    )


def reconcile_annual_student_loans(
    income_basis: AnnualLoanIncomeBasis,
    plans: Iterable[Any],
    deduction_evidence: Iterable[LoanDeductionEvidence],
    *,
    tax_year: str = "2026/27",
    as_of: date,
    declared_employment_ids: Iterable[str],
    stale_after_days: int = 45,
) -> AnnualLoanReconciliation:
    """Calculate and reconcile supported annual loan components.

    The caller must establish the annual Self Assessment income basis. This
    module does not infer whether pension relief qualifies or whether supplied
    property/unearned income is valid step-1 income.
    """
    if tax_year != "2026/27":
        raise ValueError("This bounded reconciliation supports 2026/27 only")
    cfg = get_config(tax_year)
    declared = tuple(dict.fromkeys(declared_employment_ids))
    if not declared:
        raise ValueError("declared_employment_ids must define the deduction evidence scope")
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")
    supplied_plans = tuple(plans)
    normalised = tuple(_normalise_plan(plan) for plan in supplied_plans)
    known_plan_inputs = {
        1, 2, 4, 5, "1", "2", "4", "5", "plan_1", "plan_2", "plan_4", "plan_5",
        "postgraduate", "pgl", "postgraduate_loan",
    }
    unsupported = tuple(str(plan) for plan in supplied_plans if plan not in known_plan_inputs)
    undergraduate_count = sum(parsed is LoanComponent.PLAN_2 for parsed in normalised)
    other_undergraduate = tuple(
        str(plan) for plan in supplied_plans
        if plan in (1, 4, 5, "1", "4", "5", "plan_1", "plan_4", "plan_5")
    )
    if undergraduate_count > 1 or other_undergraduate or unsupported:
        if unsupported:
            unsupported_kind = (
                "mixed_known_and_unknown_student_loan_plans"
                if len(unsupported) < len(supplied_plans)
                else "unknown_student_loan_plan"
            )
        elif undergraduate_count > 1 or len(other_undergraduate) + undergraduate_count > 1:
            unsupported_kind = "simultaneous_multiple_undergraduate_plans"
        else:
            unsupported_kind = "unsupported_undergraduate_plan"
        return AnnualLoanReconciliation(
            "reserved-annual-loan-reconciliation/1.0", tax_year, cfg["rules_version"], None,
            "unsupported_plan_combination", (), income_basis.evidence_ids,
            tuple(dict.fromkeys(str(plan) for plan in supplied_plans)),
            (
                unsupported_kind,
                "annual_plan_treatment_requires_external_verification",
                "no_student_loan_or_total_monetary_result_available",
            ),
            ("customer_combined_balance", "filing", "payment", "refund"),
            as_of, declared, income_basis.evidence, stale_after_days,
        )
    requested = tuple(dict.fromkeys(parsed for parsed in normalised if parsed is not None))
    if not requested:
        return AnnualLoanReconciliation(
            "reserved-annual-loan-reconciliation/1.0", tax_year, cfg["rules_version"], None,
            "insufficient_facts", (), income_basis.evidence_ids, (), ("no_supported_plan_supplied",),
            ("customer_combined_balance", "filing", "payment", "refund"),
            as_of, declared, income_basis.evidence, stale_after_days,
        )

    basis = _amount(income_basis.amount, "annual loan income basis")
    basis_ids = tuple(item.evidence_id for item in income_basis.evidence)
    basis_provenance_coherent = (
        bool(income_basis.evidence_ids)
        and len(set(income_basis.evidence_ids)) == len(income_basis.evidence_ids)
        and len(basis_ids) == len(income_basis.evidence_ids)
        and set(basis_ids) == set(income_basis.evidence_ids)
        and all(
            item.evidence_id and item.source_kind and item.source_reference
            and item.subject_reference and item.effective_period and item.complete_for_basis
            and item.observed_on <= as_of
            for item in income_basis.evidence
        )
    )
    if (
        not basis_provenance_coherent
        or not income_basis.qualifying_pension_relief_confirmed
        or not income_basis.taxable_income_scope_confirmed
    ):
        return AnnualLoanReconciliation(
            "reserved-annual-loan-reconciliation/1.0", tax_year, cfg["rules_version"], None,
            "insufficient_facts", (), income_basis.evidence_ids, (),
            ("annual_loan_income_basis_not_fully_evidenced",),
            ("customer_combined_balance", "filing", "payment", "refund"),
            as_of, declared, income_basis.evidence, stale_after_days,
        )

    evidence = tuple(deduction_evidence)
    results = []
    for component in requested:
        key = 2 if component is LoanComponent.PLAN_2 else "postgraduate"
        rules = cfg["STUDENT_LOANS"][key]
        raw = max(ZERO, basis - rules["threshold"]) * rules["rate"]
        liability = _money(raw.to_integral_value(rounding=ROUND_FLOOR))
        results.append(_reconcile_component(
            component, liability, evidence, tax_year, as_of, declared, stale_after_days
        ))
    statuses = {item.calculation_status for item in results}
    if "conflict_requires_review" in statuses:
        status = "conflict_requires_review"
    elif "insufficient_facts" in statuses:
        status = "insufficient_facts"
    elif "calculated_with_material_uncertainty" in statuses:
        status = "calculated_with_material_uncertainty"
    else:
        status = "calculated"
    return AnnualLoanReconciliation(
        "reserved-annual-loan-reconciliation/1.0", tax_year, cfg["rules_version"], _money(basis),
        status, tuple(results), income_basis.evidence_ids, (),
        (
            "annual_self_assessment_liability_not_payroll_period_calculation",
            "components_must_not_be_combined_for_customer_presentation",
        ),
        ("customer_combined_balance", "filing", "payment", "refund"),
        as_of,
        declared,
        income_basis.evidence,
        stale_after_days,
    )
