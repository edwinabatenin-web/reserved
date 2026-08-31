"""Internal annual-liability contract for the final W2 cash composition.

This boundary classifies annual tax and remaining Self Assessment student-loan
amounts without importing Payments on Account, PAYE tax deducted, payments,
credits, refunds or HMRC account state. It is not a customer bill, reserve
recommendation, filing instruction or payment authority.
"""

from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
import hashlib
import hmac
import json
import re

from .annual_loan_reconciliation import (
    AnnualLoanReconciliation,
    AnnualLoanComponentResult,
    LoanBasisEvidence,
    LoanComponent,
)
from .integrated_annual_position import AnnualPositionResult


ZERO = Decimal("0")
TAX_YEAR_END = date(2027, 4, 5)
_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DIGEST_REFERENCE = re.compile(r"^[a-z-]+:sha256-[0-9a-f]{64}$")
_POA_ELIGIBLE_FAMILIES = {"income_tax", "class_4_ni", "hicbc"}
_PROHIBITED_USES = (
    "customer_presentation",
    "direct_reserve_guidance",
    "filing",
    "payment",
    "refund",
    "current_forecast_as_hmrc_poa_basis",
)


@dataclass(frozen=True)
class NoStudentLoanEvidence:
    """Explicit evidence that no student-loan/PGL component applies."""

    evidence_id: str
    tax_year: str
    ruleset_version: str
    as_of: date
    subject_reference: str
    source_kind: str
    source_reference: str
    complete_for_tax_year: bool


@dataclass(frozen=True)
class CashReadyLoanComponent:
    component: LoanComponent
    annual_liability: Decimal
    evidenced_deductions: Decimal
    remaining_self_assessment_amount: Decimal
    selected_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class CashReadyAnnualPosition:
    contract_version: str
    tax_year: str
    ruleset_version: str
    calculation_status: str
    component_set_complete: bool
    as_of: date
    annual_tax_reference: str
    student_loan_reference: str
    annual_tax_liability: Decimal | None
    student_loan_self_assessment_amount: Decimal | None
    final_self_assessment_liability: Decimal | None
    annual_tax_families: tuple[str, ...]
    poa_eligible_families: tuple[str, ...]
    poa_excluded_families: tuple[str, ...]
    loan_components: tuple[CashReadyLoanComponent, ...]
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


def _canonical(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": type(value).__name__,
            "fields": {item.name: _canonical(getattr(value, item.name)) for item in fields(value)},
        }
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if type(value) is date:
        return {"date": value.isoformat()}
    if isinstance(value, Enum):
        return {"enum": f"{type(value).__name__}:{value.value}"}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError(f"Unsupported identity value type: {type(value).__name__}")


def _content_digest(value: object) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def annual_position_identity(value: AnnualPositionResult) -> str:
    """Return the immutable content identity to persist with a reviewed result."""
    if type(value) is not AnnualPositionResult:
        raise ValueError("annual position identity requires an exact AnnualPositionResult")
    return f"annual-position:sha256-{_content_digest(value)}"


def student_loan_position_identity(
    value: AnnualLoanReconciliation | NoStudentLoanEvidence,
) -> str:
    """Return the immutable content identity to persist with reviewed loan evidence."""
    if type(value) is AnnualLoanReconciliation:
        namespace = "loan-reconciliation"
    elif type(value) is NoStudentLoanEvidence:
        namespace = "loan-applicability"
    else:
        raise ValueError("student loan identity requires an exact supported evidence type")
    return f"{namespace}:sha256-{_content_digest(value)}"


def _bound_reference(value: object, supplied: str, name: str, namespace: str) -> str:
    if not isinstance(supplied, str) or not _DIGEST_REFERENCE.fullmatch(supplied):
        raise ValueError(f"{name} must be a SHA-256 content identity")
    expected = f"{namespace}:sha256-{_content_digest(value)}"
    if not hmac.compare_digest(supplied, expected):
        raise ValueError(f"{name} does not match the exact supplied content")
    return supplied


def _non_negative_money(value: object) -> bool:
    return (
        isinstance(value, Decimal)
        and value.is_finite()
        and value >= ZERO
        and value == value.quantize(Decimal("0.01"))
    )


def _tax_limitations(annual_tax: AnnualPositionResult) -> tuple[str, ...]:
    limitations: list[str] = []
    if type(annual_tax) is not AnnualPositionResult:
        return ("annual_tax_type_invalid",)
    if annual_tax.contract_version != "reserved-estimate-envelope/1.1-internal":
        limitations.append("annual_tax_contract_version_invalid")
    if annual_tax.tax_year != "2026/27":
        limitations.append("annual_tax_year_invalid")
    if annual_tax.ruleset_version != "uk-2026-27-v4":
        limitations.append("annual_tax_ruleset_invalid")
    monetary = (
        annual_tax.non_savings_tax,
        annual_tax.savings_tax,
        annual_tax.dividend_tax,
        annual_tax.class_4_ni,
    )
    if not all(_non_negative_money(value) for value in monetary):
        limitations.append("annual_tax_component_invalid")
    income_tax = sum(monetary[:3], ZERO) if all(
        _non_negative_money(value) for value in monetary[:3]
    ) else None
    if (
        annual_tax.income_tax_before_limitations is None
        or not _non_negative_money(annual_tax.income_tax_before_limitations)
        or income_tax is None
        or annual_tax.income_tax_before_limitations != income_tax
    ):
        limitations.append("annual_income_tax_reconciliation_failed")
    hicbc = annual_tax.hicbc
    if hicbc is not None and not _non_negative_money(hicbc):
        limitations.append("annual_hicbc_invalid")
    expected_total = (
        income_tax + annual_tax.class_4_ni + (hicbc or ZERO)
        if income_tax is not None and _non_negative_money(annual_tax.class_4_ni)
        else None
    )
    if (
        annual_tax.calculation_status != "calculated"
        or annual_tax.total_liability is None
        or not _non_negative_money(annual_tax.total_liability)
        or expected_total is None
        or annual_tax.total_liability != expected_total
    ):
        limitations.append("annual_tax_component_not_complete")
    if annual_tax.blind_persons_allowance is None:
        limitations.append("annual_allowance_evidence_not_complete")
    if annual_tax.unsupported_families:
        limitations.append("annual_tax_has_unsupported_families")
    families = annual_tax.included_families
    if (
        not families
        or len(families) != len(set(families))
        or not set(families).issubset(_POA_ELIGIBLE_FAMILIES)
        or "income_tax" not in families
        or "class_4_ni" not in families
        or ((hicbc is not None) != ("hicbc" in families))
    ):
        limitations.append("annual_tax_family_classification_invalid")
    return tuple(dict.fromkeys(limitations))


def _loan_component_valid(component: AnnualLoanComponentResult) -> bool:
    selected_decision_ids = tuple(
        decision.evidence_id
        for decision in component.evidence_decisions
        if decision.decision == "selected"
    )
    return (
        type(component) is AnnualLoanComponentResult
        and component.calculation_status == "calculated"
        and _non_negative_money(component.annual_liability)
        and _non_negative_money(component.evidenced_deductions)
        and _non_negative_money(component.remaining_self_assessment_amount)
        and component.remaining_self_assessment_amount
        == max(ZERO, component.annual_liability - component.evidenced_deductions)
        and component.apparent_excess_deductions is None
        and component.range_completeness
        == "complete_for_declared_employment_scope_as_of_evidence_dates"
        and bool(component.selected_evidence_ids)
        and len(component.selected_evidence_ids) == len(set(component.selected_evidence_ids))
        and set(selected_decision_ids) == set(component.selected_evidence_ids)
    )


def _reconciled_loan_position(
    loans: AnnualLoanReconciliation,
    reference: str,
    tax_year: str,
    ruleset_version: str,
    as_of: date,
) -> tuple[
    bool,
    tuple[CashReadyLoanComponent, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    limitations: list[str] = []
    if type(loans) is not AnnualLoanReconciliation:
        return False, (), (), (), ("student_loan_type_invalid",)
    _bound_reference(loans, reference, "student_loan_reference", "loan-reconciliation")
    if loans.contract_version != "reserved-annual-loan-reconciliation/1.0":
        limitations.append("student_loan_contract_version_invalid")
    if loans.tax_year != tax_year or loans.ruleset_version != ruleset_version:
        limitations.append("student_loan_tax_year_or_ruleset_mismatch")
    if loans.as_of != as_of or as_of != TAX_YEAR_END:
        limitations.append("student_loan_period_not_final")
    if loans.calculation_status != "calculated" or not loans.components:
        limitations.append("student_loan_reconciliation_not_complete")
    basis_ids = tuple(item.evidence_id for item in loans.basis_evidence)
    if (
        not loans.basis_evidence_ids
        or len(loans.basis_evidence_ids) != len(set(loans.basis_evidence_ids))
        or set(basis_ids) != set(loans.basis_evidence_ids)
        or not all(
            type(item) is LoanBasisEvidence
            and item.complete_for_basis
            and item.evidence_id
            and item.source_kind
            and item.source_reference
            and item.subject_reference
            and item.effective_period
            and item.observed_on <= as_of
            for item in loans.basis_evidence
        )
    ):
        limitations.append("student_loan_basis_provenance_invalid")
    if len({component.component for component in loans.components}) != len(loans.components):
        limitations.append("duplicate_student_loan_component")
    if not all(_loan_component_valid(component) for component in loans.components):
        limitations.append("student_loan_component_reconciliation_invalid")
    if loans.unsupported_plans:
        limitations.append("unsupported_student_loan_plan")
    components = () if limitations else tuple(
        CashReadyLoanComponent(
            component=component.component,
            annual_liability=component.annual_liability,
            evidenced_deductions=component.evidenced_deductions,
            remaining_self_assessment_amount=component.remaining_self_assessment_amount,
            selected_evidence_ids=component.selected_evidence_ids,
        )
        for component in loans.components
    )
    evidence_ids = () if limitations else loans.basis_evidence_ids + tuple(
        evidence_id for component in components for evidence_id in component.selected_evidence_ids
    )
    if len(evidence_ids) != len(set(evidence_ids)):
        limitations.append("student_loan_evidence_identity_reused")
        components = ()
        evidence_ids = ()
    excluded = () if limitations else tuple(component.component.value for component in components)
    return not limitations, components, evidence_ids, excluded, tuple(limitations)


def _no_loan_position(
    evidence: NoStudentLoanEvidence,
    reference: str,
    tax_year: str,
    ruleset_version: str,
    as_of: date,
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    limitations: list[str] = []
    _bound_reference(evidence, reference, "student_loan_reference", "loan-applicability")
    if type(evidence) is not NoStudentLoanEvidence:
        return False, (), ("student_loan_applicability_type_invalid",)
    if type(evidence.evidence_id) is not str or not _REFERENCE_ID.fullmatch(evidence.evidence_id):
        limitations.append("student_loan_applicability_evidence_id_invalid")
    if (
        evidence.tax_year != tax_year
        or evidence.ruleset_version != ruleset_version
        or evidence.as_of != as_of
        or as_of != TAX_YEAR_END
    ):
        limitations.append("student_loan_applicability_period_or_ruleset_mismatch")
    if not (
        type(evidence.complete_for_tax_year) is bool
        and evidence.complete_for_tax_year is True
        and all(
            type(value) is str and value == value.strip() and bool(value)
            for value in (
                evidence.subject_reference,
                evidence.source_kind,
                evidence.source_reference,
            )
        )
    ):
        limitations.append("student_loan_applicability_evidence_incomplete")
    return not limitations, ((evidence.evidence_id,) if not limitations else ()), tuple(limitations)


def compose_cash_ready_annual_position(
    annual_tax: AnnualPositionResult,
    student_loan_position: AnnualLoanReconciliation | NoStudentLoanEvidence,
    *,
    annual_tax_reference: str,
    student_loan_reference: str,
    as_of: date,
) -> CashReadyAnnualPosition:
    """Compose the one annual-liability input accepted by W2-S6.

    No current annual amount is labelled as an HMRC-issued Payments on Account
    basis. W2 must supply tax deducted, prior PoA, payments, credits and account
    obligations through their separate evidence contracts.
    """
    tax_ref = _bound_reference(
        annual_tax, annual_tax_reference, "annual_tax_reference", "annual-position"
    )
    tax_limitations = _tax_limitations(annual_tax)
    tax_year = annual_tax.tax_year if type(annual_tax) is AnnualPositionResult else "unknown"
    ruleset = annual_tax.ruleset_version if type(annual_tax) is AnnualPositionResult else "unknown"

    loan_components: tuple[CashReadyLoanComponent, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()
    if type(student_loan_position) is AnnualLoanReconciliation:
        loan_complete, loan_components, evidence_ids, excluded, loan_limitations = (
            _reconciled_loan_position(
                student_loan_position,
                student_loan_reference,
                tax_year,
                ruleset,
                as_of,
            )
        )
    elif type(student_loan_position) is NoStudentLoanEvidence:
        loan_complete, evidence_ids, loan_limitations = _no_loan_position(
            student_loan_position,
            student_loan_reference,
            tax_year,
            ruleset,
            as_of,
        )
    else:
        raise ValueError("student_loan_position must be a supported typed evidence result")

    limitations = tuple(dict.fromkeys(tax_limitations + loan_limitations))
    complete = not limitations and loan_complete and as_of == TAX_YEAR_END
    annual_amount = annual_tax.total_liability if complete else None
    loan_amount = (
        sum((component.remaining_self_assessment_amount for component in loan_components), ZERO)
        if complete
        else None
    )
    final_amount = annual_amount + loan_amount if complete else None
    families = annual_tax.included_families if complete else ()
    return CashReadyAnnualPosition(
        contract_version="reserved-cash-ready-annual-position/1.0",
        tax_year=tax_year,
        ruleset_version=ruleset,
        calculation_status="ready_for_w2_s6" if complete else "unresolved",
        component_set_complete=complete,
        as_of=as_of,
        annual_tax_reference=tax_ref,
        student_loan_reference=student_loan_reference,
        annual_tax_liability=annual_amount,
        student_loan_self_assessment_amount=loan_amount,
        final_self_assessment_liability=final_amount,
        annual_tax_families=families,
        poa_eligible_families=families,
        poa_excluded_families=excluded,
        loan_components=loan_components if complete else (),
        evidence_ids=evidence_ids if complete else (),
        limitations=limitations,
        prohibited_uses=_PROHIBITED_USES,
    )
