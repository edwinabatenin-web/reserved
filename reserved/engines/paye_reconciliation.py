"""Evidence-based PAYE reconciliation for Reserved.

This module does not call HMRC and does not calculate PAYE from net bank
deposits. It combines normalised evidence supplied by an adapter or fallback
journey and preserves conflicts for user review.

Evidence is selected by what it represents, recency and completeness. Source
kind is only a final tie-breaker; HMRC is never given unconditional precedence.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable

from .utils import money


class EvidenceKind(str, Enum):
    HMRC = "hmrc"
    DOCUMENT = "document"
    MANUAL = "manual"
    BANK_INFERENCE = "bank_inference"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INCOMPLETE = "incomplete"


class EvidenceRepresentation(str, Enum):
    EMPLOYMENT_CUMULATIVE = "employment_cumulative"
    EMPLOYMENTS_AGGREGATE_CUMULATIVE = "employments_aggregate_cumulative"


class Completeness(str, Enum):
    COMPLETE_FOR_REPRESENTATION = "complete_for_representation"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PayeEvidence:
    kind: EvidenceKind
    tax_year: str
    tax_paid_to_date: Decimal | str | int | float | None
    gross_pay_to_date: Decimal | str | int | float | None = None
    employment_id: str | None = None
    tax_code: str | None = None
    observed_on: date | None = None
    source_reference: str | None = None
    evidence_id: str | None = None
    representation: EvidenceRepresentation | None = None
    completeness: Completeness = Completeness.UNKNOWN
    effective_through: date | None = None
    covered_employment_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceConflict:
    field: str
    selected_kind: EvidenceKind
    other_kind: EvidenceKind
    difference: Decimal
    employment_id: str | None


@dataclass(frozen=True)
class PayeReconciliation:
    tax_year: str
    tax_paid_to_date: Decimal | None
    estimated_remaining_liability: Decimal | None
    confidence: Confidence
    selected_kind: EvidenceKind | None
    selected_observed_on: date | None
    conflicts: tuple[EvidenceConflict, ...]
    warnings: tuple[str, ...]
    evidence_count: int
    selected_evidence: tuple[PayeEvidence, ...] = ()
    considered_evidence: tuple[PayeEvidence, ...] = ()
    estimated_remaining_liability_low: Decimal | None = None
    estimated_remaining_liability_high: Decimal | None = None
    calculation_status: str = "calculated"
    selected_evidence_ids: tuple[str, ...] = ()
    selection_reasons: tuple[str, ...] = ()
    tax_paid_known: bool = True
    conservative_assumed_tax_paid: Decimal | None = None
    apparent_overpayment: Decimal | None = None
    range_completeness: str | None = None
    indeterminable_effect: bool = False


_PRIORITY = {
    EvidenceKind.HMRC: 4,
    EvidenceKind.DOCUMENT: 3,
    EvidenceKind.MANUAL: 2,
    EvidenceKind.BANK_INFERENCE: 1,
}


def _amount(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = money(value)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed >= 0 else None


def _quality(kind: EvidenceKind) -> Confidence:
    if kind in {EvidenceKind.HMRC, EvidenceKind.DOCUMENT}:
        return Confidence.HIGH
    if kind is EvidenceKind.MANUAL:
        return Confidence.MEDIUM
    return Confidence.LOW


def _reduce_confidence(confidence: Confidence) -> Confidence:
    if confidence is Confidence.HIGH:
        return Confidence.MEDIUM
    if confidence is Confidence.MEDIUM:
        return Confidence.LOW
    return confidence


def _completeness(item: PayeEvidence) -> int:
    """Count useful supplied facts without treating source brand as certainty."""
    fact_count = sum(value not in (None, "") for value in (
        item.tax_paid_to_date,
        item.gross_pay_to_date,
        item.tax_code,
        item.source_reference,
    ))
    return fact_count + {
        Completeness.UNKNOWN: 0,
        Completeness.PARTIAL: 1,
        Completeness.COMPLETE_FOR_REPRESENTATION: 2,
    }[item.completeness]


def _selection_key(item: PayeEvidence):
    """Prefer dated, recent and complete evidence; source kind breaks exact ties."""
    return (
        item.observed_on is not None,
        item.observed_on or date.min,
        _completeness(item),
        _PRIORITY[item.kind],
    )


def _remaining_range(liability: Decimal, aggregates, per_employment):
    """Bound the effect of known conflicting evidence without guessing omissions."""
    possible_paid: list[Decimal] = []
    aggregate_amounts = [
        _amount(item.tax_paid_to_date) for item in aggregates
        if _amount(item.tax_paid_to_date) is not None
    ]
    possible_paid.extend(aggregate_amounts)

    by_employment: dict[str, list[Decimal]] = {}
    for item in per_employment:
        amount = _amount(item.tax_paid_to_date)
        if amount is not None:
            by_employment.setdefault(item.employment_id or "", []).append(amount)
    if by_employment:
        possible_paid.extend((
            sum((min(values) for values in by_employment.values()), Decimal("0")),
            sum((max(values) for values in by_employment.values()), Decimal("0")),
        ))
    if not possible_paid:
        return None, None
    low_paid, high_paid = min(possible_paid), max(possible_paid)
    return (
        money(max(Decimal("0"), liability - high_paid)),
        money(max(Decimal("0"), liability - low_paid)),
    )


def reconcile_paye(
    estimated_total_liability,
    evidence: Iterable[PayeEvidence],
    *,
    tax_year: str,
    as_of: date | None = None,
    stale_after_days: int = 45,
    conflict_tolerance=Decimal("1.00"),
) -> PayeReconciliation:
    """Reconcile PAYE tax paid without silently overwriting any evidence.

    One highest-quality observation is selected per employment. Evidence with
    no employment identifier is treated as an aggregate observation, so it is
    never added to employment-level observations (which would double count).
    """
    liability = _amount(estimated_total_liability)
    if liability is None:
        raise ValueError("estimated_total_liability must be a non-negative amount")

    supplied = tuple(item for item in evidence if item.tax_year == tax_year)
    usable = tuple(item for item in supplied if (
        _amount(item.tax_paid_to_date) is not None
        and item.evidence_id
        and item.representation is not None
        and item.completeness is not Completeness.UNKNOWN
        and item.effective_through is not None
    ))
    warnings: list[str] = []
    if not usable:
        return PayeReconciliation(
            tax_year, None, None, Confidence.INCOMPLETE,
            None, None, (),
            ("No direct evidence of PAYE tax paid is available.",), len(supplied),
            calculation_status="insufficient_facts",
            tax_paid_known=False,
            conservative_assumed_tax_paid=Decimal("0.00"),
            range_completeness="partial",
            indeterminable_effect=True,
        )

    aggregates = tuple(item for item in usable if not item.employment_id)
    per_employment = tuple(item for item in usable if item.employment_id)

    employment_ids = {item.employment_id for item in per_employment if item.employment_id}
    linked_aggregates = tuple(item for item in aggregates if (
        item.representation is EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE
        and employment_ids
        and set(item.covered_employment_ids) == employment_ids
    ))

    # Use an aggregate only when its declared representation explicitly covers
    # the same employment entities. Equal totals alone never prove equivalence.
    if linked_aggregates:
        selected_items = (max(
            linked_aggregates,
            key=_selection_key,
        ),)
        if per_employment:
            warnings.append(
                "Aggregate and employment-level evidence were both supplied; "
                "the aggregate was used to avoid double counting."
            )
    elif aggregates and per_employment:
        return PayeReconciliation(
            tax_year, None, None, Confidence.INCOMPLETE,
            None, None, (),
            ("Aggregate and employment evidence cannot be reconciled without an explicit representation link.",),
            len(supplied), considered_evidence=usable,
            calculation_status="insufficient_facts", tax_paid_known=False,
            range_completeness="partial", indeterminable_effect=True,
        )
    elif aggregates:
        selected_items = (max(aggregates, key=_selection_key),)
    else:
        selected_by_employment: dict[str, PayeEvidence] = {}
        for item in per_employment:
            existing = selected_by_employment.get(item.employment_id or "")
            if existing is None or (
                _selection_key(item) > _selection_key(existing)
            ):
                selected_by_employment[item.employment_id or ""] = item
        selected_items = tuple(selected_by_employment.values())

    conflicts: list[EvidenceConflict] = []
    for selected in selected_items:
        selected_amount = _amount(selected.tax_paid_to_date) or Decimal("0")
        comparable = (
            aggregates if not selected.employment_id
            else tuple(item for item in per_employment if item.employment_id == selected.employment_id)
        )
        for other in comparable:
            if other is selected:
                continue
            other_amount = _amount(other.tax_paid_to_date)
            if other_amount is None:
                continue
            difference = money(abs(selected_amount - other_amount))
            if difference > money(conflict_tolerance):
                conflicts.append(EvidenceConflict(
                    "tax_paid_to_date", selected.kind, other.kind,
                    difference, selected.employment_id,
                ))

    if conflicts:
        range_low, range_high = _remaining_range(liability, aggregates, per_employment)
        return PayeReconciliation(
            tax_year, None, None, Confidence.INCOMPLETE,
            None, None, tuple(conflicts),
            ("Conflicting PAYE evidence requires review; neither candidate was selected.",),
            len(supplied), (), tuple(usable), range_low, range_high,
            calculation_status="conflict_requires_review",
            tax_paid_known=False,
            range_completeness="complete_for_identified_uncertainties",
        )

    tax_paid = money(sum(
        (_amount(item.tax_paid_to_date) or Decimal("0") for item in selected_items),
        Decimal("0"),
    ))
    remaining = money(max(Decimal("0"), liability - tax_paid))
    weakest_selected = min(selected_items, key=lambda item: _PRIORITY[item.kind])
    confidence = _quality(weakest_selected.kind)

    today = as_of or date.today()
    stale = any(
        item.observed_on is None or (today - item.observed_on).days > stale_after_days
        for item in selected_items
    )
    if stale:
        warnings.append("Selected PAYE evidence is missing a date or may be out of date.")
        confidence = _reduce_confidence(confidence)
    if conflicts:
        warnings.append("Conflicting PAYE evidence requires user review; no source was overwritten.")
        confidence = _reduce_confidence(confidence)
    if any(item.kind is EvidenceKind.BANK_INFERENCE for item in selected_items):
        warnings.append("Bank-payment inference is a last-resort estimate, not direct PAYE evidence.")

    strongest = max(selected_items, key=_selection_key)
    latest = max((item.observed_on for item in selected_items if item.observed_on), default=None)
    range_low, range_high = _remaining_range(liability, aggregates, per_employment)
    if range_low == range_high:
        range_low = range_high = None
    apparent_overpayment = money(max(Decimal("0"), tax_paid - liability)) or None
    incomplete_period = any(
        item.effective_through is not None and item.effective_through < today
        for item in selected_items
    )
    selection_reasons = tuple(
        "explicit aggregate coverage prevents double counting"
        if item in linked_aggregates else "only usable direct evidence for represented scope"
        for item in selected_items
    )
    return PayeReconciliation(
        tax_year, tax_paid, remaining, confidence, strongest.kind, latest,
        tuple(conflicts), tuple(warnings), len(supplied), tuple(selected_items), tuple(usable),
        range_low, range_high,
        calculation_status="calculated_with_material_uncertainty" if stale or incomplete_period else "calculated",
        selected_evidence_ids=tuple(item.evidence_id for item in selected_items if item.evidence_id),
        selection_reasons=selection_reasons,
        apparent_overpayment=apparent_overpayment,
        range_completeness="partial" if incomplete_period else None,
        indeterminable_effect=incomplete_period,
    )
