"""Bounded HICBC partner-responsibility determination.

October v1 capability (conditionally included).  This module produces a single
coherent internal result that separates the user's individual Adjusted Net
Income, the partner evidence used only for comparison, the responsibility
status, the user's own projected HICBC, any household-level change status,
evidence provenance and uncertainty.

HICBC may contribute to a customer total, reserve/set-aside guidance or payment
journey only when the evidence is adequate for that purpose and the applicable
assurance gates have passed.  This module never exposes a linked partner's raw
ANI, income band or calculated personal tax to the user.

Correctness and safe uncertainty handling are the objectives.  Code reduction
is not.  The module is deliberately provider-neutral: a manual partner estimate
and a future linked-partner source both produce a :class:`PartnerEvidence` and
are consumed by the same responsibility logic without either having
unconditional precedence.

Authority
---------
- Income Tax (Earnings and Pensions) Act 2003 ss.681B–681C (HICBC formula and
  whole-pound staged rounding).
- Finance Act 2012 Sch. 1; Finance (No. 2) Act 2024 s.5 (£60,000/£80,000 and
  £200 per percentage point for 2024/25 onwards).
- HMRC PAYE Manual PAYE14015.

The charge applies to the person in the household with the higher adjusted net
income.  Where the two are equal there is no statutory "higher" person; this
module fails safe as ambiguous rather than inventing a tie-break.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Protocol

from reserved.evidence_uncertainty import (
    CalculationStatus,
    EffectKind,
    EstimateEffect,
    EstimateEvidenceItem,
    EstimateUncertainty,
    EvidenceCompleteness,
    EvidenceRepresentation,
    EvidenceSelection,
    UncertaintyReason,
)

from .tax_config import get_config
from .utils import money

PENNY = Decimal("0.01")
ZERO = Decimal("0")

# ── Responsibility status vocabulary (customer-safe, no partner operands) ─────

RESPONSIBILITY_NO_CHARGE = "no_charge"
RESPONSIBILITY_PERSON_LIABLE = "person_liable"
RESPONSIBILITY_PARTNER_LIABLE = "partner_liable"
RESPONSIBILITY_AMBIGUOUS = "ambiguous"
RESPONSIBILITY_INSUFFICIENT_FACTS = "insufficient_facts"

_RESPONSIBILITY_VALUES = frozenset({
    RESPONSIBILITY_NO_CHARGE,
    RESPONSIBILITY_PERSON_LIABLE,
    RESPONSIBILITY_PARTNER_LIABLE,
    RESPONSIBILITY_AMBIGUOUS,
    RESPONSIBILITY_INSUFFICIENT_FACTS,
})

# Household change status — derived from a previous responsibility status.
HOUSEHOLD_UNCHANGED = "unchanged"
HOUSEHOLD_CHANGED = "changed"
HOUSEHOLD_MOVED_TO_PARTNER = "moved_to_partner"
HOUSEHOLD_MOVED_TO_PERSON = "moved_to_person"
HOUSEHOLD_NOT_APPLICABLE = "not_applicable"

# Source kinds (the future linked-source kind is deliberately opaque here).
SOURCE_MANUAL_PARTNER_ESTIMATE = "user_supplied_partner_estimate"
SOURCE_LINKED_PARTNER = "linked_partner_source"

# Recency states (freshness policy is versioned; no universal cutoff embedded).
RECENCY_CURRENT = "current"
RECENCY_UNCONFIRMED = "unconfirmed"
RECENCY_STALE = "stale"
RECENCY_UNKNOWN = "unknown"

_UNCERTAIN_RECENCY_STATES = frozenset({RECENCY_UNCONFIRMED, RECENCY_STALE, RECENCY_UNKNOWN})

# Uses that remain prohibited until the applicable gate is independently passed.
# ``v1_customer_tax_total`` and ``reserve_or_set_aside_guidance`` are
# *conditional* rather than categorically prohibited: the purpose gate in
# ``hicbc_integration`` decides them and they are not actioned in this package.
_PROHIBITED_USES = (
    "payment_initiation",
    "filing_or_submission",
    "october_launch_claim",
    "personal_allowance_explore_your_options_result",
)

_PERMITTED_USES = (
    "hicbc_responsibility_estimate",
)


def _amount(value, name: str) -> Decimal:
    """Parse a finite, non-negative monetary/ANI amount, rejecting booleans."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not result.is_finite() or result < ZERO:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


@dataclass(frozen=True)
class PartnerEvidence:
    """Source-neutral, provenance-bearing partner ANI comparison evidence.

    A linked source may supply the same shape as a manual estimate; the
    responsibility logic below does not give either source unconditional
    precedence.  ``original_value`` may hold a raw figure and must therefore
    never be serialised into a customer-facing payload; use the customer view
    instead.
    """

    evidence_id: str
    source_kind: str
    source_reference: str
    subject_reference: str
    tax_year: str
    representation: str  # "point" | "range"
    point: Decimal | None
    low: Decimal | None
    high: Decimal | None
    effective_period: str
    observed_at: str
    confirmed_at: str | None
    completeness: str  # complete_for_purpose | partial | unknown
    recency_state: str  # current | unconfirmed | stale | unknown
    consent_state: str  # consented | revoked | not_required (manual)
    ani_components: tuple[str, ...] = ()  # ANI components/adjustments represented
    conflict: bool = False  # sources materially disagree (disjoint evidence)

    def __post_init__(self) -> None:
        if not all((self.evidence_id, self.source_kind, self.source_reference,
                    self.subject_reference, self.tax_year, self.effective_period,
                    self.observed_at, self.completeness, self.recency_state,
                    self.consent_state)):
            raise ValueError("Partner evidence identity, scope, dates and states are required")
        if self.representation == "point":
            if self.point is None or self.low is not None or self.high is not None:
                raise ValueError("A point estimate requires exactly a point value")
        elif self.representation == "range":
            if self.low is None or self.high is None or self.point is not None:
                raise ValueError("A range estimate requires exactly low/high values")
            if self.low > self.high:
                raise ValueError("A range estimate requires low <= high")
        else:
            raise ValueError(f"Unsupported partner representation: {self.representation!r}")
        for label, value in (("point", self.point), ("low", self.low), ("high", self.high)):
            if value is not None:
                if not value.is_finite() or value < ZERO:
                    raise ValueError(f"Partner evidence {label} must be finite and non-negative")

    @property
    def is_range(self) -> bool:
        return self.representation == "range"

    @property
    def is_usable(self) -> bool:
        """A revoked/unusable consent or unknown completeness is not usable."""
        return self.consent_state != "revoked" and self.completeness != EvidenceCompleteness.UNKNOWN.value

    @property
    def has_material_uncertainty(self) -> bool:
        return (
            self.completeness == EvidenceCompleteness.PARTIAL.value
            or self.recency_state in _UNCERTAIN_RECENCY_STATES
            or self.conflict
        )


@dataclass(frozen=True)
class HicbcResponsibilityResult:
    """Single coherent internal HICBC responsibility result.

    ``projected_user_hicbc`` is the user's *own* projected charge (zero when the
    partner carries responsibility).  When responsibility is ambiguous the
    possible charge is bounded by ``possible_charge_low``/``possible_charge_high``
    rather than collapsed into a point.
    """

    contract_version: str
    tax_year: str
    ruleset_version: str
    calculation_status: str
    responsibility_status: str
    user_ani: Decimal
    child_benefit_amount: Decimal | None
    child_benefit_facts_complete: bool
    has_relevant_partner: bool | None
    partner_evidence: PartnerEvidence | None
    hicbc_percentage: int | None
    projected_user_hicbc: Decimal | None
    possible_charge_low: Decimal | None
    possible_charge_high: Decimal | None
    household_change_status: str
    evidence: tuple[EstimateEvidenceItem, ...]
    uncertainties: tuple[EstimateUncertainty, ...]
    limitations: tuple[str, ...]
    permitted_uses: tuple[str, ...]
    prohibited_uses: tuple[str, ...]

    @property
    def user_is_person_liable(self) -> bool:
        return self.responsibility_status == RESPONSIBILITY_PERSON_LIABLE


def _hicbc_charge(ani: Decimal, benefit: Decimal, cfg: dict) -> tuple[int, Decimal]:
    """Return ``(whole_percentage, whole_pound_charge)`` using staged rounding.

    ITEPA 2003 s.681C(3): round the relevant total Child Benefit amount down to
    whole pounds, apply the whole complete-£200 percentage (capped at 100), then
    round the resulting charge down to whole pounds.
    """
    rules = cfg["HICBC"]
    points = int(max(ZERO, ani - rules["lower_threshold"]) // rules["income_per_percentage_point"])
    percentage = min(100, points)
    whole_pound_benefit = benefit.to_integral_value(rounding=ROUND_FLOOR)
    charge = (whole_pound_benefit * Decimal(percentage) / Decimal("100")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return percentage, money(charge)


def _compare_to_user(user_ani: Decimal, evidence: PartnerEvidence) -> str:
    """Return "user_higher" | "partner_higher" | "equal" | "overlap"."""
    if not evidence.is_range:
        partner = evidence.point
        if partner < user_ani:
            return "user_higher"
        if partner > user_ani:
            return "partner_higher"
        return "equal"
    low, high = evidence.low, evidence.high
    if high < user_ani:
        return "user_higher"
    if low > user_ani:
        return "partner_higher"
    return "overlap"


def _material_uncertainty_reason(evidence: PartnerEvidence) -> UncertaintyReason:
    """Choose the uncertainty reason for materially-uncertain partner evidence.

    A genuine source conflict (disjoint manual/linked operands) is reported as
    ``CONFLICTING``, distinct from a merely incomplete or stale-but-usable value.
    """
    if evidence.conflict:
        return UncertaintyReason.CONFLICTING
    if evidence.recency_state in _UNCERTAIN_RECENCY_STATES:
        return UncertaintyReason.STALE
    return UncertaintyReason.INCOMPLETE


def _partner_is_above_threshold(evidence: PartnerEvidence | None, threshold: Decimal) -> bool | None:
    """Return True/False/None for whether the partner is above ``threshold``."""
    if evidence is None:
        return None
    if not evidence.is_range:
        return evidence.point > threshold
    if evidence.low > threshold:
        return True
    if evidence.high <= threshold:
        return False
    return None  # range straddles the threshold


def _evidence_item(evidence: PartnerEvidence) -> EstimateEvidenceItem:
    representation = {
        "point": EvidenceRepresentation.MANUAL_ASSERTION,
        "range": EvidenceRepresentation.FORECAST,
    }[evidence.representation]
    completeness = EvidenceCompleteness(evidence.completeness)
    if evidence.is_range:
        original_value = f"{evidence.low}..{evidence.high}"
    else:
        original_value = str(evidence.point)
    return EstimateEvidenceItem(
        evidence_id=evidence.evidence_id,
        source_kind=evidence.source_kind,
        source_reference=evidence.source_reference,
        subject_reference=evidence.subject_reference,
        tax_year=evidence.tax_year,
        effective_period=evidence.effective_period,
        observed_at=evidence.observed_at,
        representation=representation,
        completeness=completeness,
        recency_state=evidence.recency_state,
        selection=EvidenceSelection.SELECTED,
        selection_reason="partner ANI comparison evidence used for responsibility",
        original_value=original_value,
        unit="GBP",
    )


def _uncertainty(
    issue_id: str,
    reason: UncertaintyReason,
    affected_input: str,
    explanation: str,
    effect: EstimateEffect,
    affected_components: tuple[str, ...] = ("hicbc_responsibility",),
    customer_action: str | None = None,
) -> EstimateUncertainty:
    return EstimateUncertainty(
        issue_id=issue_id,
        reason=reason,
        affected_input=affected_input,
        evidence_references=(),
        explanation=explanation,
        effect=effect,
        affected_components=affected_components,
        customer_action=customer_action,
    )


def _base_limitations() -> tuple[str, ...]:
    return (
        "hicbc_is_october_v1_and_conditionally_included_pending_evidence_and_assurance",
        "partner_responsibility_requires_partner_evidence_or_explicit_absence",
        "equal_or_overlapping_ani_is_not_tie_broken",
    )


def determine_hicbc_responsibility(
    *,
    user_ani,
    child_benefit_amount,
    has_relevant_partner: bool | None,
    partner_evidence: PartnerEvidence | None = None,
    additional_evidence: tuple[PartnerEvidence, ...] = (),
    tax_year: str = "2026/27",
    previous_responsibility_status: str | None = None,
) -> HicbcResponsibilityResult:
    """Determine the user's projected HICBC responsibility.

    ``child_benefit_amount`` is ``None`` when Child Benefit facts are unknown
    (which must never be treated as zero), otherwise a non-negative annual
    amount.  ``has_relevant_partner`` is ``None`` when the user has not stated
    whether they have a partner for HICBC purposes.

    ``partner_evidence`` is the effective evidence used for the comparison.
    ``additional_evidence`` lists further provenance records (for example the
    manual estimate when linked evidence is also present) that are retained for
    audit but do not themselves drive the comparison.  Neither source receives
    unconditional precedence.
    """
    cfg = get_config(tax_year)
    ani = _amount(user_ani, "user_ani")
    benefit = None if child_benefit_amount is None else _amount(child_benefit_amount, "child_benefit_amount")

    limitations = list(_base_limitations())
    uncertainties: list[EstimateUncertainty] = []
    evidence_items: list[EstimateEvidenceItem] = []

    for evidence in (partner_evidence,) + tuple(additional_evidence):
        if evidence is not None:
            if evidence.tax_year != tax_year:
                raise ValueError("Partner evidence tax year must match the requested tax year")
            evidence_items.append(_evidence_item(evidence))

    def _finish(
        *,
        responsibility: str,
        calculation_status: str,
        projected: Decimal | None = None,
        percentage: int | None = None,
        low: Decimal | None = None,
        high: Decimal | None = None,
    ) -> HicbcResponsibilityResult:
        change = household_change_status(previous_responsibility_status, responsibility)
        return HicbcResponsibilityResult(
            contract_version="reserved-hicbc-responsibility/1.0",
            tax_year=tax_year,
            ruleset_version=cfg["rules_version"],
            calculation_status=calculation_status,
            responsibility_status=responsibility,
            user_ani=ani.quantize(PENNY),
            child_benefit_amount=benefit.quantize(PENNY) if benefit is not None else None,
            child_benefit_facts_complete=benefit is not None,
            has_relevant_partner=has_relevant_partner,
            partner_evidence=partner_evidence,
            hicbc_percentage=percentage,
            projected_user_hicbc=projected,
            possible_charge_low=low,
            possible_charge_high=high,
            household_change_status=change,
            evidence=tuple(evidence_items),
            uncertainties=tuple(uncertainties),
            limitations=tuple(limitations),
            permitted_uses=_PERMITTED_USES,
            prohibited_uses=_PROHIBITED_USES,
        )

    # ── 1. Child Benefit facts unknown → insufficient (never zero). ──────────
    if benefit is None:
        uncertainties.append(_uncertainty(
            "hicbc_child_benefit_facts_unknown",
            UncertaintyReason.MISSING,
            "child_benefit_amount",
            "Child Benefit receipt or amount is not known and must not be treated as zero.",
            EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
            customer_action="Add or confirm your Child Benefit information to estimate this charge.",
        ))
        return _finish(
            responsibility=RESPONSIBILITY_INSUFFICIENT_FACTS,
            calculation_status=CalculationStatus.INSUFFICIENT_FACTS.value,
        )

    # ── 2. Affirmatively no Child Benefit → no charge. ───────────────────────
    if benefit == ZERO:
        return _finish(
            responsibility=RESPONSIBILITY_NO_CHARGE,
            calculation_status=CalculationStatus.NOT_APPLICABLE.value,
            projected=ZERO,
            percentage=0,
            low=ZERO,
            high=ZERO,
        )

    threshold = cfg["HICBC"]["lower_threshold"]

    # ── 3. User below threshold → user never liable. ─────────────────────────
    if ani <= threshold:
        partner_above = _partner_is_above_threshold(partner_evidence, threshold)
        if has_relevant_partner is True and partner_above is True:
            limitations.append("hicbc_liability_belongs_to_higher_ani_partner")
            return _finish(
                responsibility=RESPONSIBILITY_PARTNER_LIABLE,
                calculation_status=CalculationStatus.CALCULATED.value,
                projected=ZERO,
                low=ZERO,
                high=ZERO,
            )
        return _finish(
            responsibility=RESPONSIBILITY_NO_CHARGE,
            calculation_status=CalculationStatus.NOT_APPLICABLE.value,
            projected=ZERO,
            percentage=0,
            low=ZERO,
            high=ZERO,
        )

    # ── 4. User above threshold. ─────────────────────────────────────────────
    full_percentage, full_charge = _hicbc_charge(ani, benefit, cfg)

    if has_relevant_partner is False:
        return _finish(
            responsibility=RESPONSIBILITY_PERSON_LIABLE,
            calculation_status=CalculationStatus.CALCULATED.value,
            projected=full_charge,
            percentage=full_percentage,
            low=full_charge,
            high=full_charge,
        )

    if has_relevant_partner is None:
        uncertainties.append(_uncertainty(
            "hicbc_partner_status_unknown",
            UncertaintyReason.MISSING,
            "has_relevant_partner",
            "Whether a partner with a higher adjusted net income exists is not known; "
            "the user must not be assumed liable.",
            EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
            customer_action="Confirm whether you have a partner for High Income Child Benefit Charge purposes.",
        ))
        return _finish(
            responsibility=RESPONSIBILITY_INSUFFICIENT_FACTS,
            calculation_status=CalculationStatus.INSUFFICIENT_FACTS.value,
            low=ZERO,
            high=full_charge,
        )

    # has_relevant_partner is True from here.
    if partner_evidence is None:
        uncertainties.append(_uncertainty(
            "hicbc_partner_estimate_missing",
            UncertaintyReason.MISSING,
            "partner_evidence",
            "A relevant partner was declared but no partner income estimate is available; "
            "the user must not be assumed liable.",
            EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
            customer_action="Add or update your partner's income estimate to determine responsibility.",
        ))
        return _finish(
            responsibility=RESPONSIBILITY_INSUFFICIENT_FACTS,
            calculation_status=CalculationStatus.INSUFFICIENT_FACTS.value,
            low=ZERO,
            high=full_charge,
        )

    if not partner_evidence.is_usable:
        uncertainties.append(_uncertainty(
            "hicbc_partner_evidence_not_usable",
            UncertaintyReason.INCOMPLETE,
            "partner_evidence",
            "The available partner evidence cannot be used (unknown completeness or revoked consent).",
            EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
            customer_action="Reconfirm or replace the partner income estimate.",
        ))
        return _finish(
            responsibility=RESPONSIBILITY_INSUFFICIENT_FACTS,
            calculation_status=CalculationStatus.INSUFFICIENT_FACTS.value,
            low=ZERO,
            high=full_charge,
        )

    comparison = _compare_to_user(ani, partner_evidence)
    material_uncertainty = partner_evidence.has_material_uncertainty

    if comparison == "user_higher":
        if material_uncertainty:
            uncertainties.append(_uncertainty(
                "hicbc_partner_evidence_uncertain",
                _material_uncertainty_reason(partner_evidence),
                "partner_evidence",
                "Partner income evidence is incomplete or not current; the current indication is that the user is the higher-income person.",
                EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
                customer_action="Update or confirm the partner estimate to improve this result.",
            ))
        return _finish(
            responsibility=RESPONSIBILITY_PERSON_LIABLE,
            calculation_status=(
                CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY.value
                if material_uncertainty else CalculationStatus.CALCULATED.value
            ),
            projected=full_charge,
            percentage=full_percentage,
            low=full_charge,
            high=full_charge,
        )

    if comparison == "partner_higher":
        limitations.append("hicbc_liability_belongs_to_higher_ani_partner")
        if material_uncertainty:
            uncertainties.append(_uncertainty(
                "hicbc_partner_evidence_uncertain",
                _material_uncertainty_reason(partner_evidence),
                "partner_evidence",
                "Partner income evidence is incomplete or not current; the current indication is that the partner is the higher-income person.",
                EstimateEffect(kind=EffectKind.NOT_DETERMINABLE),
                customer_action="Update or confirm the partner estimate to improve this result.",
            ))
        return _finish(
            responsibility=RESPONSIBILITY_PARTNER_LIABLE,
            calculation_status=(
                CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY.value
                if material_uncertainty else CalculationStatus.CALCULATED.value
            ),
            projected=ZERO,
            low=ZERO,
            high=ZERO,
        )

    # comparison in {"equal", "overlap"} → ambiguous; bound the possible charge.
    reason = (
        UncertaintyReason.CONFLICTING
        if comparison == "equal" or partner_evidence.conflict
        else UncertaintyReason.REPRESENTATION_UNCLEAR
    )
    explanation = (
        "The user and partner adjusted net incomes are equal; there is no statutory higher-income person, so responsibility is not determined."
        if comparison == "equal" else
        "The partner income range overlaps the user's adjusted net income; responsibility could move between partners."
    )
    uncertainties.append(_uncertainty(
        "hicbc_responsibility_ambiguous",
        reason,
        "partner_evidence",
        explanation,
        EstimateEffect(kind=EffectKind.RANGE, low=ZERO, high=full_charge),
        customer_action="Update or confirm the partner estimate to resolve the overlap or equality.",
    ))
    return _finish(
        responsibility=RESPONSIBILITY_AMBIGUOUS,
        calculation_status=CalculationStatus.BOUNDED_RANGE.value,
        low=ZERO,
        high=full_charge,
    )


def household_change_status(previous: str | None, current: str) -> str:
    """Classify a change between a previous and current responsibility status."""
    if current not in _RESPONSIBILITY_VALUES:
        raise ValueError(f"Unknown responsibility status: {current!r}")
    if previous is None:
        return HOUSEHOLD_NOT_APPLICABLE
    if previous not in _RESPONSIBILITY_VALUES:
        raise ValueError(f"Unknown previous responsibility status: {previous!r}")
    if previous == current:
        return HOUSEHOLD_UNCHANGED
    if previous == RESPONSIBILITY_PERSON_LIABLE and current == RESPONSIBILITY_PARTNER_LIABLE:
        return HOUSEHOLD_MOVED_TO_PARTNER
    if previous == RESPONSIBILITY_PARTNER_LIABLE and current == RESPONSIBILITY_PERSON_LIABLE:
        return HOUSEHOLD_MOVED_TO_PERSON
    return HOUSEHOLD_CHANGED


def annual_child_benefit_amount(
    *,
    children: int,
    annual_override=None,
    weeks_entitled: int | None = None,
    tax_year: str = "2026/27",
) -> Decimal | None:
    """Derive the annual Child Benefit amount from child counts + year rates.

    Returns ``None`` when no children are recorded and no override is supplied
    (unknown, not zero).  ``annual_override`` is an explicit annual total that,
    when supplied, is used verbatim.
    """
    cfg = get_config(tax_year)
    if annual_override is not None:
        return _amount(annual_override, "annual_override")
    if children is None or children <= 0:
        return None
    weekly = cfg["CHILD_BENEFIT"]
    weeks = weekly["weeks_per_year"] if weeks_entitled is None else Decimal(str(weeks_entitled))
    if weeks < ZERO or weeks > Decimal("53"):
        raise ValueError("weeks_entitled must be between 0 and 53")
    eldest = weekly["eldest_weekly"]
    additional = weekly["additional_weekly"]
    return money(eldest * weeks + additional * weeks * Decimal(str(children - 1)))


# ── Future linked-partner hook (provider-neutral) ─────────────────────────────

class LinkedPartnerEvidenceProvider(Protocol):
    """Smallest interface a future authorised linked-partner source implements.

    A linked source supplies a :class:`PartnerEvidence` without exposing the
    other user's raw financial data to the first user, customer payloads,
    templates, logs, analytics or unrelated services.  No account-linking,
    invitation, discovery or relationship-management subsystem is built here.
    """

    def fetch_partner_evidence(self, *, user_id: str, tax_year: str) -> PartnerEvidence | None:
        ...


class SyntheticLinkedPartnerEvidenceProvider:
    """A fake linked source used only to prove the interface and privacy boundary."""

    def __init__(self, evidence: PartnerEvidence | None):
        self._evidence = evidence

    def fetch_partner_evidence(self, *, user_id: str, tax_year: str) -> PartnerEvidence | None:
        if self._evidence is not None and self._evidence.tax_year != tax_year:
            return None
        return self._evidence


# ── Customer-facing, privacy-minimised view ───────────────────────────────────

_CUSTOMER_HEADLINES = {
    RESPONSIBILITY_NO_CHARGE: (
        "Reserved does not estimate a High Income Child Benefit Charge for you "
        "based on the information currently available."
    ),
    RESPONSIBILITY_PERSON_LIABLE: (
        "Based on the information currently available, Reserved estimates that the "
        "High Income Child Benefit Charge may apply to you."
    ),
    RESPONSIBILITY_PARTNER_LIABLE: (
        "Based on the information currently available, Reserved estimates that this "
        "charge may apply to your partner rather than to you."
    ),
    RESPONSIBILITY_AMBIGUOUS: (
        "Responsibility for the High Income Child Benefit Charge cannot currently be "
        "determined because the available income information is equal or overlapping."
    ),
    RESPONSIBILITY_INSUFFICIENT_FACTS: (
        "Reserved needs more information to estimate whether the High Income Child "
        "Benefit Charge applies to you."
    ),
}


def customer_view(result: HicbcResponsibilityResult) -> dict:
    """Return the privacy-minimised, neutral customer payload.

    This deliberately excludes the partner's raw ANI, income band, range
    operands, comparison operands and any calculated personal tax for the
    partner.  It exposes only the responsibility/uncertainty outcome and the
    user's own projected charge or bounded possible charge.
    """
    messages = []
    if result.partner_evidence is not None:
        messages.append("This estimate uses partner information you supplied.")
    if result.household_change_status in {HOUSEHOLD_CHANGED, HOUSEHOLD_MOVED_TO_PARTNER, HOUSEHOLD_MOVED_TO_PERSON}:
        messages.append("Your household tax position has changed.")
    for uncertainty in result.uncertainties:
        if uncertainty.customer_action:
            messages.append(uncertainty.customer_action)

    def _fmt(value: Decimal | None) -> str | None:
        return None if value is None else f"{float(value):,.2f}"

    return {
        "tax_year": result.tax_year,
        "responsibility_status": result.responsibility_status,
        "calculation_status": result.calculation_status,
        "headline": _CUSTOMER_HEADLINES[result.responsibility_status],
        "projected_user_hicbc": _fmt(result.projected_user_hicbc),
        "possible_charge_low": _fmt(result.possible_charge_low),
        "possible_charge_high": _fmt(result.possible_charge_high),
        "household_change_status": result.household_change_status,
        "based_on_partner_estimate": result.partner_evidence is not None,
        "messages": messages,
    }
