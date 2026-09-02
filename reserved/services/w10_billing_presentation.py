"""Fail-closed W10-S6A customer price-presentation boundary.

This module is the smallest pure, network-inert customer-presentation slice of
the W10-S6 customer billing journeys. It derives one immutable customer-facing
view from the already-integrated W10-S1A ``BillingAuthority``: exactly three
ordered plan cards and the settled VAT-inclusive qualification copy.

It revalidates the complete authority and every nested price value before
deriving anything, accepts only the exact integrated contract types, preserves
the authority version and a deterministic source identity internally, and fails
closed without exposing internal evidence references, identifiers, provider or
implementation objects in the customer copy.

It does not calculate savings, equivalents, discounts, VAT rate or
applicability, does not select a provider, create checkout/portal/action URLs,
grant access or entitlement, persist anything, or import routes, templates,
auth, database, provider, payment or networking code. It is a view-model
sub-boundary only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType

from reserved.billing.contracts import (
    AUTHORITY_VERSION,
    INITIAL_BILLING_AUTHORITY,
    BillingAuthority,
    PlanKey,
    PlanPrice,
)

CONTRACT_VERSION = "reserved-w10-billing-presentation/1.0"
VAT_QUALIFICATION = "Prices include VAT where applicable."

_PLAN_TERMS = MappingProxyType(
    {
        PlanKey.MONTHLY: "per month",
        PlanKey.SIX_MONTH: "for six months",
        PlanKey.YEARLY: "per year",
    }
)


def _customer_label(plan: PlanPrice) -> str:
    """Return the exact settled customer copy for one validated plan."""
    return f"£{plan.amount} {_PLAN_TERMS[plan.key]}"


_EXPECTED_LABELS = tuple(_customer_label(plan) for plan in INITIAL_BILLING_AUTHORITY.plans)


def _authority_components(value: BillingAuthority) -> tuple[object, ...]:
    """Project the settled authority to deterministic, JSON-safe components."""
    return (
        value.decision_id,
        value.decision_date.isoformat(),
        value.authority_version,
        value.launch_model.value,
        tuple(
            (plan.key.value, str(plan.amount), plan.currency.value)
            for plan in value.plans
        ),
        value.vat_price_statement.value,
        value.price_change_rule.value,
        value.offer_capability_rule.value,
    )


def _source_digest(value: BillingAuthority) -> str:
    payload = json.dumps(
        _authority_components(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_SETTLED_SOURCE_IDENTITY = f"w10-billing-source:sha256-{_source_digest(INITIAL_BILLING_AUTHORITY)}"


@dataclass(frozen=True, slots=True)
class PlanCard:
    """One settled customer-facing plan card; exactly one exact string label."""

    label: str

    def __post_init__(self) -> None:
        _validate_plan_card(self)

    def __copy__(self) -> PlanCard:
        _validate_plan_card(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> PlanCard:
        _validate_plan_card(self)
        memo[id(self)] = self
        return self

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:
        _validate_plan_card(self)
        return (PlanCard, (self.label,))

    def __repr__(self) -> str:
        try:
            _validate_plan_card(self)
        except Exception:
            return "PlanCard(<invalid-state>)"
        return "PlanCard(<validated>)"

    def __eq__(self, other: object) -> bool:
        _validate_plan_card(self)
        if type(other) is not PlanCard:
            return False
        _validate_plan_card(other)
        return object.__getattribute__(self, "label") == object.__getattribute__(
            other, "label"
        )

    def __hash__(self) -> int:
        _validate_plan_card(self)
        return hash(object.__getattribute__(self, "label"))


def _validate_plan_card(value: object) -> PlanCard:
    if type(value) is not PlanCard:
        raise TypeError("plan card must be an exact PlanCard")
    label = object.__getattribute__(value, "label")
    if type(label) is not str:
        raise TypeError("plan card label must be an exact string")
    if label not in _EXPECTED_LABELS:
        raise ValueError("plan card label must be one of the settled plan labels")
    return value


class W10BillingPresentation:
    """Immutable provider-neutral customer price-presentation view.

    ``contract_version``, ``plans`` and ``vat_qualification`` are the exact
    customer-facing copy. ``_authority_version`` and ``_source_identity`` are
    internal provenance bindings; they never appear in the customer copy or any
    routine serialization surface (representation, ``asdict``, iteration,
    mapping conversion or pickle payload), while still binding internal
    equality and hash to the settled authority.
    """

    __slots__ = (
        "contract_version",
        "plans",
        "vat_qualification",
        "_authority_version",
        "_source_identity",
    )

    def __init__(
        self,
        contract_version: str,
        plans: tuple[PlanCard, ...],
        vat_qualification: str,
    ) -> None:
        object.__setattr__(self, "contract_version", contract_version)
        object.__setattr__(self, "plans", plans)
        object.__setattr__(self, "vat_qualification", vat_qualification)
        _validate_public_state(self)
        object.__setattr__(self, "_authority_version", AUTHORITY_VERSION)
        object.__setattr__(self, "_source_identity", _SETTLED_SOURCE_IDENTITY)
        _validate_view(self)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("W10BillingPresentation is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("W10BillingPresentation is immutable")

    def __repr__(self) -> str:
        try:
            _validate_view(self)
        except Exception:
            return "W10BillingPresentation(<invalid-state>)"
        return "W10BillingPresentation(<validated>)"

    def __copy__(self) -> "W10BillingPresentation":
        _validate_view(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> "W10BillingPresentation":
        _validate_view(self)
        memo[id(self)] = self
        return self

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:
        _validate_view(self)
        return (
            W10BillingPresentation,
            (self.contract_version, self.plans, self.vat_qualification),
        )

    def __eq__(self, other: object) -> bool:
        _validate_view(self)
        if type(other) is not W10BillingPresentation:
            return False
        _validate_view(other)
        return _view_components(self) == _view_components(other)

    def __hash__(self) -> int:
        _validate_view(self)
        return hash(_view_components(self))


def _validate_public_state(value: object) -> W10BillingPresentation:
    if type(value) is not W10BillingPresentation:
        raise TypeError("billing presentation must be an exact W10BillingPresentation")
    contract_version = object.__getattribute__(value, "contract_version")
    plans = object.__getattribute__(value, "plans")
    vat_qualification = object.__getattribute__(value, "vat_qualification")
    if type(contract_version) is not str or contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported billing presentation contract version")
    if type(plans) is not tuple:
        raise TypeError("plans must be an exact tuple")
    labels: list[str] = []
    for card in plans:
        _validate_plan_card(card)
        labels.append(card.label)
    if tuple(labels) != _EXPECTED_LABELS:
        raise ValueError("plans must preserve the settled catalogue order and copy")
    if type(vat_qualification) is not str or vat_qualification != VAT_QUALIFICATION:
        raise ValueError("VAT qualification must preserve the settled wording")
    return value


def _validate_view(value: object) -> W10BillingPresentation:
    _validate_public_state(value)
    authority_version = getattr(value, "_authority_version", None)
    source_identity = getattr(value, "_source_identity", None)
    if type(authority_version) is not str or authority_version != AUTHORITY_VERSION:
        raise ValueError("billing presentation authority version was altered")
    if type(source_identity) is not str or source_identity != _SETTLED_SOURCE_IDENTITY:
        raise ValueError("billing presentation source identity was altered")
    return value


def _view_components(value: W10BillingPresentation) -> tuple[object, ...]:
    return (
        value.contract_version,
        tuple(card.label for card in value.plans),
        value.vat_qualification,
        value._authority_version,
        value._source_identity,
    )


def _revalidate_authority(value: object) -> BillingAuthority | None:
    """Revalidate a candidate authority through the public constructor path."""
    if type(value) is not BillingAuthority:
        return None
    try:
        return BillingAuthority(
            value.decision_id,
            value.decision_date,
            value.authority_version,
            value.launch_model,
            value.plans,
            value.vat_price_statement,
            value.price_change_rule,
            value.offer_capability_rule,
        )
    except (AttributeError, TypeError, ValueError):
        return None


def present_w10_billing_presentation(
    authority: object,
) -> W10BillingPresentation | None:
    """Derive the settled customer presentation, or fail closed with ``None``."""
    try:
        validated = _revalidate_authority(authority)
        if validated is None:
            return None
        if f"w10-billing-source:sha256-{_source_digest(validated)}" != _SETTLED_SOURCE_IDENTITY:
            return None
        plans = tuple(PlanCard(_customer_label(plan)) for plan in validated.plans)
        return W10BillingPresentation(CONTRACT_VERSION, plans, VAT_QUALIFICATION)
    except (AttributeError, TypeError, ValueError):
        return None


def w10_billing_presentation_authority_version(value: W10BillingPresentation) -> str:
    """Return the validated internal authority version reference."""
    _validate_view(value)
    return value._authority_version


def w10_billing_presentation_source_identity(value: W10BillingPresentation) -> str:
    """Return the validated deterministic source identity of the settled authority."""
    _validate_view(value)
    return value._source_identity


__all__ = (
    "CONTRACT_VERSION",
    "VAT_QUALIFICATION",
    "PlanCard",
    "W10BillingPresentation",
    "present_w10_billing_presentation",
    "w10_billing_presentation_authority_version",
    "w10_billing_presentation_source_identity",
)
