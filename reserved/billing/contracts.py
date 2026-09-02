"""Provider-neutral authority and policy-completeness contracts for W10-S1A.

This module is deliberately network-inert and persistence-free.  It records the
commercial facts settled by FD-W10-001 and reports whether every separately
required billing-policy input has a traceable decision.  It does not calculate
discounts or VAT, select a provider, derive entitlement, grant access or enable
billing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from types import MappingProxyType


FOUNDER_DECISION_ID = "FD-W10-001"
FOUNDER_DECISION_DATE = date(2026, 9, 2)
AUTHORITY_VERSION = "FD-W10-001/2026-09-02/v1"


class PlanKey(str, Enum):
    """Stable internal keys; never provider product or price identifiers."""

    MONTHLY = "monthly"
    SIX_MONTH = "six_month"
    YEARLY = "yearly"


class Currency(str, Enum):
    GBP = "GBP"


class LaunchModel(str, Enum):
    PAID_SUBSCRIPTION = "paid_subscription"


class VatPriceStatement(str, Enum):
    """Settled customer statement, without determining VAT rate/applicability."""

    INCLUSIVE_WHERE_APPLICABLE = "inclusive_of_vat_where_applicable"


class PriceChangeRule(str, Enum):
    INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION = (
        "initial_changeable_only_by_later_founder_decision"
    )


class OfferCapabilityRule(str, Enum):
    """A capability requirement, explicitly not a price or access algorithm."""

    REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY = (
        "special_discounts_and_offers_required_without_calculation_or_access_authority"
    )


_EXPECTED_AMOUNTS = MappingProxyType(
    {
        PlanKey.MONTHLY: Decimal("29"),
        PlanKey.SIX_MONTH: Decimal("156"),
        PlanKey.YEARLY: Decimal("288"),
    }
)
_EXPECTED_PLAN_ORDER = tuple(PlanKey)


def _exact_slot_values(
    value: object,
    expected_type: type,
    names: tuple[str, ...],
    context: str,
) -> tuple[object, ...]:
    """Read one exact slotted value without accepting partial/subclass state."""
    if type(value) is not expected_type:
        raise TypeError(f"{context} must be an exact {expected_type.__name__}")
    values: list[object] = []
    for name in names:
        try:
            values.append(object.__getattribute__(value, name))
        except AttributeError:
            raise ValueError(f"{context} state is incomplete") from None
    return tuple(values)


@dataclass(frozen=True, slots=True)
class PlanPrice:
    """One exact, Founder-authorised initial customer price."""

    key: PlanKey
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        _validate_plan_price(self)

    def __copy__(self) -> "PlanPrice":
        key, amount, currency = _validate_plan_price(self)
        return PlanPrice(key, amount, currency)

    def __deepcopy__(self, memo: dict) -> "PlanPrice":
        return self.__copy__()

    def __reduce__(self):
        key, amount, currency = _validate_plan_price(self)
        return (PlanPrice, (key, amount, currency))


def _validate_plan_price(value: object) -> tuple[PlanKey, Decimal, Currency]:
    key, amount, currency = _exact_slot_values(
        value, PlanPrice, ("key", "amount", "currency"), "plan"
    )
    if type(key) is not PlanKey:
        raise TypeError("key must be an exact PlanKey")
    if type(amount) is not Decimal:
        raise TypeError("amount must be an exact Decimal")
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    if amount != _EXPECTED_AMOUNTS[key]:
        raise ValueError(f"amount does not match {AUTHORITY_VERSION} for {key.value}")
    if type(currency) is not Currency or currency is not Currency.GBP:
        raise ValueError("currency must be the exact settled GBP value")
    return key, amount, currency


@dataclass(frozen=True, slots=True)
class BillingAuthority:
    """Exact reconstruction of FD-W10-001, with no provider or policy fields."""

    decision_id: str
    decision_date: date
    authority_version: str
    launch_model: LaunchModel
    plans: tuple[PlanPrice, ...]
    vat_price_statement: VatPriceStatement
    price_change_rule: PriceChangeRule
    offer_capability_rule: OfferCapabilityRule

    def __post_init__(self) -> None:
        _validate_billing_authority(self)

    def plan(self, key: PlanKey) -> PlanPrice:
        values = _validate_billing_authority(self)
        if type(key) is not PlanKey:
            raise TypeError("key must be an exact PlanKey")
        plans = values[4]
        return plans[_EXPECTED_PLAN_ORDER.index(key)]

    def __copy__(self) -> "BillingAuthority":
        return BillingAuthority(*_validate_billing_authority(self))

    def __deepcopy__(self, memo: dict) -> "BillingAuthority":
        return self.__copy__()

    def __reduce__(self):
        return (BillingAuthority, _validate_billing_authority(self))


def _validate_billing_authority(value: object) -> tuple:
    (
        decision_id,
        decision_date,
        authority_version,
        launch_model,
        plans,
        vat_price_statement,
        price_change_rule,
        offer_capability_rule,
    ) = _exact_slot_values(
        value,
        BillingAuthority,
        (
            "decision_id",
            "decision_date",
            "authority_version",
            "launch_model",
            "plans",
            "vat_price_statement",
            "price_change_rule",
            "offer_capability_rule",
        ),
        "billing authority",
    )
    if type(decision_id) is not str or decision_id != FOUNDER_DECISION_ID:
        raise ValueError("decision_id must bind exactly to FD-W10-001")
    if type(decision_date) is not date or decision_date != FOUNDER_DECISION_DATE:
        raise ValueError("decision_date must bind exactly to FD-W10-001")
    if type(authority_version) is not str or authority_version != AUTHORITY_VERSION:
        raise ValueError("authority_version must bind exactly to FD-W10-001")
    if type(launch_model) is not LaunchModel or launch_model is not LaunchModel.PAID_SUBSCRIPTION:
        raise ValueError("launch_model must be the settled paid-subscription model")
    if type(plans) is not tuple:
        raise TypeError("plans must be an exact tuple")
    validated_plans = tuple(_validate_plan_price(plan)[0] for plan in plans)
    if validated_plans != _EXPECTED_PLAN_ORDER:
        raise ValueError("plans must contain each settled key exactly once in canonical order")
    if (
        type(vat_price_statement) is not VatPriceStatement
        or vat_price_statement is not VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE
    ):
        raise ValueError("VAT metadata must preserve the settled where-applicable statement")
    if (
        type(price_change_rule) is not PriceChangeRule
        or price_change_rule
        is not PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION
    ):
        raise ValueError("price changes must require later Founder authority")
    if (
        type(offer_capability_rule) is not OfferCapabilityRule
        or offer_capability_rule
        is not OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY
    ):
        raise ValueError("offers must remain a capability requirement without policy semantics")
    return (
        decision_id,
        decision_date,
        authority_version,
        launch_model,
        plans,
        vat_price_statement,
        price_change_rule,
        offer_capability_rule,
    )


INITIAL_BILLING_AUTHORITY = BillingAuthority(
    decision_id=FOUNDER_DECISION_ID,
    decision_date=FOUNDER_DECISION_DATE,
    authority_version=AUTHORITY_VERSION,
    launch_model=LaunchModel.PAID_SUBSCRIPTION,
    plans=tuple(
        PlanPrice(key=key, amount=_EXPECTED_AMOUNTS[key], currency=Currency.GBP)
        for key in _EXPECTED_PLAN_ORDER
    ),
    vat_price_statement=VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE,
    price_change_rule=PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION,
    offer_capability_rule=OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY,
)


class BillingPolicyKey(str, Enum):
    """Every subordinate launch policy kept unresolved by the W10 map."""

    BILLING_PROVIDER = "billing_provider"
    RENEWAL_BEHAVIOUR = "renewal_behaviour"
    CANCELLATION_TIMING = "cancellation_timing"
    FAILED_PAYMENT_AND_GRACE = "failed_payment_and_grace"
    ENTITLEMENT_START_AND_END = "entitlement_start_and_end"
    REFUNDS = "refunds"
    TAX_INVOICING_AND_ADDITIONAL_PRESENTATION = "tax_invoicing_and_additional_presentation"
    PROMOTION_AND_DISCOUNT_MECHANICS = "promotion_and_discount_mechanics"
    PARTNER_OFFER_HANDLING = "partner_offer_handling"
    PAID_ACCESS_SURFACE = "paid_access_surface"
    TRIAL_AND_FREE_ACCESS = "trial_and_free_access_if_applicable"
    PLAN_CHANGES_AND_PRORATION = "plan_changes_and_proration"
    BILLING_ACCOUNT_RECOVERY = "billing_account_recovery"
    MANUAL_OVERRIDES = "manual_overrides"
    POST_SETTLEMENT_DISPUTE_CHARGEBACK_REVERSAL = (
        "post_settlement_dispute_chargeback_reversal_consequences"
    )


REQUIRED_BILLING_POLICY_KEYS = tuple(BillingPolicyKey)


class PolicyCompletenessStatus(str, Enum):
    POLICY_INCOMPLETE = "policy_incomplete"
    POLICY_INPUTS_COMPLETE = "policy_inputs_complete"


_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}$")
_RECORD_REFERENCE = re.compile(
    r"^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+#[A-Za-z0-9_.:-]+$"
)
_PLACEHOLDER_OUTCOMES = frozenset(
    {
        "default",
        "not decided",
        "not yet decided",
        "pending",
        "pending decision",
        "decision pending",
        "provider default",
        "provider-default",
        "provider's default",
        "tbc",
        "t b c",
        "t.b.c",
        "t. b. c",
        "tbd",
        "t b d",
        "t.b.d",
        "t. b. d",
        "to be decided",
        "to be confirmed",
        "to be determined",
        "unknown",
        "use provider default",
        "use provider-default",
        "use provider's default",
    }
)
_PLACEHOLDER_TERMINAL_PUNCTUATION = ".,!?;:"
_TBD_TBC_PLACEHOLDER = re.compile(r"^t\s*\.?\s*b\s*\.?\s*[dc]$")


def _bounded_text(value: object, field: str, *, maximum: int) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact string")
    if not value or value != value.strip() or len(value) > maximum or not value.isprintable():
        raise ValueError(
            f"{field} must be non-empty, trimmed, printable and at most {maximum} chars"
        )
    return value


def _placeholder_form(value: str) -> str:
    """Normalize only case, whitespace and harmless terminal punctuation."""
    normalized = " ".join(value.strip().casefold().split())
    return normalized.rstrip(" " + _PLACEHOLDER_TERMINAL_PUNCTUATION)


def _is_placeholder_outcome(value: str) -> bool:
    normalized = _placeholder_form(value)
    return (
        normalized in _PLACEHOLDER_OUTCOMES
        or _TBD_TBC_PLACEHOLDER.fullmatch(normalized) is not None
    )


@dataclass(frozen=True, slots=True)
class DecisionProvenance:
    """Minimum immutable evidence needed to trace one policy outcome."""

    decision_id: str
    decided_by: str
    decided_at: datetime
    record_reference: str

    def __post_init__(self) -> None:
        _validate_decision_provenance(self)

    def __copy__(self) -> "DecisionProvenance":
        return DecisionProvenance(*_validate_decision_provenance(self))

    def __deepcopy__(self, memo: dict) -> "DecisionProvenance":
        return self.__copy__()

    def __reduce__(self):
        return (DecisionProvenance, _validate_decision_provenance(self))


def _validate_decision_provenance(value: object) -> tuple[str, str, datetime, str]:
    decision_id, decided_by, decided_at, record_reference = _exact_slot_values(
        value,
        DecisionProvenance,
        ("decision_id", "decided_by", "decided_at", "record_reference"),
        "decision provenance",
    )
    decision_id = _bounded_text(decision_id, "decision_id", maximum=128)
    if _IDENTIFIER.fullmatch(decision_id) is None:
        raise ValueError("decision_id must be a stable uppercase hyphenated identifier")
    decided_by = _bounded_text(decided_by, "decided_by", maximum=128)
    if type(decided_at) is not datetime:
        raise TypeError("decided_at must be an exact datetime")
    if decided_at.tzinfo is None or decided_at.utcoffset() != timedelta(0):
        raise ValueError("decided_at must be timezone-aware UTC")
    record_reference = _bounded_text(
        record_reference, "record_reference", maximum=256
    )
    if _RECORD_REFERENCE.fullmatch(record_reference) is None:
        raise ValueError("record_reference must identify a local record and section")
    record_path, _section = record_reference.rsplit("#", 1)
    if any(segment in {".", ".."} for segment in record_path.split("/")):
        raise ValueError("record_reference path must not contain dot segments")
    return decision_id, decided_by, decided_at, record_reference


@dataclass(frozen=True, slots=True)
class BillingPolicyDecision:
    """An explicit policy input; it has no executable billing or access effect."""

    key: BillingPolicyKey
    outcome: str
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        _validate_billing_policy_decision(self)

    def __copy__(self) -> "BillingPolicyDecision":
        return BillingPolicyDecision(*_validate_billing_policy_decision(self))

    def __deepcopy__(self, memo: dict) -> "BillingPolicyDecision":
        return self.__copy__()

    def __reduce__(self):
        return (BillingPolicyDecision, _validate_billing_policy_decision(self))


def _validate_billing_policy_decision(
    value: object,
) -> tuple[BillingPolicyKey, str, DecisionProvenance]:
    key, outcome, provenance = _exact_slot_values(
        value,
        BillingPolicyDecision,
        ("key", "outcome", "provenance"),
        "billing policy decision",
    )
    if type(key) is not BillingPolicyKey:
        raise TypeError("key must be an exact BillingPolicyKey")
    outcome = _bounded_text(outcome, "outcome", maximum=2000)
    if _is_placeholder_outcome(outcome):
        raise ValueError("outcome must be explicit, not a placeholder or provider default")
    _validate_decision_provenance(provenance)
    return key, outcome, provenance


@dataclass(frozen=True, slots=True)
class BillingPolicyRegister:
    """Validated explicit decisions and their fail-closed completeness status."""

    decisions: tuple[BillingPolicyDecision, ...] = ()

    def __post_init__(self) -> None:
        _validate_billing_policy_register(self)

    @property
    def missing_policy_keys(self) -> tuple[BillingPolicyKey, ...]:
        decisions = _validate_billing_policy_register(self)
        decided = {decision.key for decision in decisions}
        return tuple(key for key in REQUIRED_BILLING_POLICY_KEYS if key not in decided)

    @property
    def status(self) -> PolicyCompletenessStatus:
        if self.missing_policy_keys:
            return PolicyCompletenessStatus.POLICY_INCOMPLETE
        return PolicyCompletenessStatus.POLICY_INPUTS_COMPLETE

    def decision_for(self, key: BillingPolicyKey) -> BillingPolicyDecision | None:
        decisions = _validate_billing_policy_register(self)
        if type(key) is not BillingPolicyKey:
            raise TypeError("key must be an exact BillingPolicyKey")
        return next((decision for decision in decisions if decision.key is key), None)

    def __copy__(self) -> "BillingPolicyRegister":
        return BillingPolicyRegister(_validate_billing_policy_register(self))

    def __deepcopy__(self, memo: dict) -> "BillingPolicyRegister":
        return self.__copy__()

    def __reduce__(self):
        return (BillingPolicyRegister, (_validate_billing_policy_register(self),))


def _validate_billing_policy_register(
    value: object,
) -> tuple[BillingPolicyDecision, ...]:
    (decisions,) = _exact_slot_values(
        value, BillingPolicyRegister, ("decisions",), "billing policy register"
    )
    if type(decisions) is not tuple:
        raise TypeError("decisions must be an exact tuple")
    if any(type(decision) is not BillingPolicyDecision for decision in decisions):
        raise TypeError("decisions must contain only exact BillingPolicyDecision values")
    keys = tuple(_validate_billing_policy_decision(decision)[0] for decision in decisions)
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate billing policy keys are not allowed")
    return decisions


__all__ = (
    "AUTHORITY_VERSION",
    "FOUNDER_DECISION_DATE",
    "FOUNDER_DECISION_ID",
    "INITIAL_BILLING_AUTHORITY",
    "REQUIRED_BILLING_POLICY_KEYS",
    "BillingAuthority",
    "BillingPolicyDecision",
    "BillingPolicyKey",
    "BillingPolicyRegister",
    "Currency",
    "DecisionProvenance",
    "LaunchModel",
    "OfferCapabilityRule",
    "PlanKey",
    "PlanPrice",
    "PolicyCompletenessStatus",
    "PriceChangeRule",
    "VatPriceStatement",
)
