"""Provider- and calculator-neutral description of estimate input uncertainty.

This module does not calculate tax, infer probabilities or decide customer
wording. It preserves known evidence limitations and their determinable effect
so presentation code cannot mistake a precise calculation for certain inputs.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum


class UncertaintyReason(str, Enum):
    MISSING = "missing"
    STALE = "stale"
    CONFLICTING = "conflicting"
    INCOMPLETE = "incomplete"
    REPRESENTATION_UNCLEAR = "representation_unclear"
    ASSUMPTION = "assumption"
    POSSIBLY_OMITTED = "possibly_omitted"


class EffectKind(str, Enum):
    RANGE = "range"
    POINT_EFFECT = "point_effect"
    NOT_DETERMINABLE = "not_determinable"


class EstimatePurpose(str, Enum):
    INFORMATIONAL_RULE = "informational_rule"
    PERSONALISED_ESTIMATE = "personalised_estimate"
    RESERVE_GUIDANCE = "reserve_guidance"
    RECONCILIATION = "reconciliation"
    ELIGIBILITY_READINESS = "eligibility_readiness"
    UNSUPPORTED_FOR_DECISION = "unsupported_for_decision"


class PurposeFitness(str, Enum):
    ADEQUATE = "adequate"
    ADEQUATE_WITH_MATERIAL_UNCERTAINTY = "adequate_with_material_uncertainty"
    INADEQUATE = "inadequate"


class CalculationStatus(str, Enum):
    CALCULATED = "calculated"
    CALCULATED_WITH_MATERIAL_UNCERTAINTY = "calculated_with_material_uncertainty"
    BOUNDED_RANGE = "bounded_range"
    INSUFFICIENT_FACTS = "insufficient_facts"
    UNSUPPORTED_RULE = "unsupported_rule"
    NOT_APPLICABLE = "not_applicable"
    CONFLICT_REQUIRES_REVIEW = "conflict_requires_review"


class EvidenceRepresentation(str, Enum):
    AGGREGATE = "aggregate"
    ENTITY_LEVEL = "entity_level"
    PERIODIC = "periodic"
    YEAR_TO_DATE = "year_to_date"
    ANNUAL_FINAL = "annual_final"
    FORECAST = "forecast"
    MANUAL_ASSERTION = "manual_assertion"


class EvidenceCompleteness(str, Enum):
    COMPLETE_FOR_PURPOSE = "complete_for_purpose"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class EvidenceSelection(str, Enum):
    SELECTED = "selected"
    AGGREGATED = "aggregated"
    SUPERSEDED = "superseded"
    EXCLUDED_DOUBLE_COUNT = "excluded_double_count"
    OUTSIDE_PERIOD = "outside_period"
    INCOMPATIBLE_REPRESENTATION = "incompatible_representation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"


@dataclass(frozen=True)
class EstimateEvidenceItem:
    evidence_id: str
    source_kind: str
    source_reference: str
    subject_reference: str
    tax_year: str | None
    effective_period: str
    observed_at: str
    representation: EvidenceRepresentation
    completeness: EvidenceCompleteness
    recency_state: str
    selection: EvidenceSelection
    selection_reason: str
    original_value: str | None
    unit: str | None

    def __post_init__(self):
        required = (
            self.evidence_id, self.source_kind, self.source_reference,
            self.subject_reference, self.effective_period, self.observed_at,
            self.recency_state, self.selection_reason,
        )
        if not all(required):
            raise ValueError("Evidence identity, scope, dates and selection reason are required")
        try:
            datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Evidence observed_at must be ISO-8601") from None


@dataclass(frozen=True)
class EstimateEffect:
    kind: EffectKind
    low: Decimal | None = None
    high: Decimal | None = None
    amount: Decimal | None = None

    def __post_init__(self):
        values = (self.low, self.high, self.amount)
        for value in values:
            if value is not None and (not value.is_finite() or value < 0):
                raise ValueError("Effect values must be finite non-negative amounts")
        if self.kind is EffectKind.RANGE:
            if self.low is None or self.high is None or self.amount is not None or self.low > self.high:
                raise ValueError("A range requires ordered low/high values only")
        elif self.kind is EffectKind.POINT_EFFECT:
            if self.amount is None or self.low is not None or self.high is not None:
                raise ValueError("A point effect requires amount only")
        elif any(value is not None for value in values):
            raise ValueError("An indeterminable effect cannot contain invented values")


@dataclass(frozen=True)
class EstimateUncertainty:
    issue_id: str
    reason: UncertaintyReason
    affected_input: str
    evidence_references: tuple[str, ...]
    explanation: str
    effect: EstimateEffect
    known: bool = True
    affected_components: tuple[str, ...] = ()
    customer_action: str | None = None

    def __post_init__(self):
        if not self.issue_id or not self.affected_input or not self.explanation:
            raise ValueError("Uncertainty identity, affected input and explanation are required")


@dataclass(frozen=True)
class EstimateEvidenceAssessment:
    as_of: str
    issues: tuple[EstimateUncertainty, ...]
    purpose: EstimatePurpose | None = None
    fitness: PurposeFitness | None = None
    rationale: str = ""

    def __post_init__(self):
        if (self.purpose is None) != (self.fitness is None):
            raise ValueError("Purpose and fitness must be supplied together")
        if self.fitness is not None and not self.rationale:
            raise ValueError("A purpose-fitness decision requires a rationale")
        if self.fitness is PurposeFitness.ADEQUATE and self.issues:
            raise ValueError("Known uncertainty must not be hidden by an unqualified adequate status")

    @property
    def has_known_uncertainty(self) -> bool:
        return bool(self.issues)

    @property
    def has_indeterminable_effect(self) -> bool:
        return any(issue.effect.kind is EffectKind.NOT_DETERMINABLE for issue in self.issues)


@dataclass(frozen=True)
class EstimateEnvelope:
    contract_version: str
    estimate_id: str
    calculated_at: str
    tax_year: str
    ruleset_version: str
    purpose: EstimatePurpose
    fitness: PurposeFitness
    calculation_status: CalculationStatus
    point_estimate: Decimal | None
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    bound_basis: str | None
    included_families: tuple[str, ...]
    unsupported_families: tuple[str, ...]
    evidence: tuple[EstimateEvidenceItem, ...]
    uncertainties: tuple[EstimateUncertainty, ...]
    policy_version: str
    limitation_references: tuple[str, ...]
    prohibited_uses: tuple[str, ...]

    def __post_init__(self):
        if not all((self.contract_version, self.estimate_id, self.calculated_at,
                    self.tax_year, self.ruleset_version, self.policy_version)):
            raise ValueError("Estimate identity and version fields are required")
        if self.lower_bound is not None or self.upper_bound is not None:
            if self.lower_bound is None or self.upper_bound is None or self.lower_bound > self.upper_bound:
                raise ValueError("Estimate bounds must be an ordered pair")
            if not self.bound_basis:
                raise ValueError("Estimate bounds require a basis")
        if self.fitness is PurposeFitness.ADEQUATE and self.uncertainties:
            raise ValueError("Unqualified adequate fitness cannot hide known uncertainty")
        if self.purpose in {EstimatePurpose.RESERVE_GUIDANCE, EstimatePurpose.RECONCILIATION}:
            if self.fitness is not PurposeFitness.ADEQUATE and not self.prohibited_uses:
                raise ValueError("Restricted higher-consequence estimates must declare prohibited uses")


def amount(value) -> Decimal:
    """Parse an effect literal without applying tax or materiality policy."""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Effect amount must be numeric") from None
    if not parsed.is_finite() or parsed < 0:
        raise ValueError("Effect amount must be finite and non-negative")
    return parsed
