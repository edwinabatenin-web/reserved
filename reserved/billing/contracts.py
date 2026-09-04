"""Provider-neutral authority and policy-completeness contracts for W10-S1A.

This module is deliberately network-inert and persistence-free.  It records the
commercial facts settled by FD-W10-001 and reports whether every separately
required billing-policy input has a traceable decision.  It does not calculate
discounts or VAT, select a provider, derive entitlement, grant access or enable
billing.

Integrity boundary (W10-S1 authority-integrity correction)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The exact Founder constants, the exact domain/enum and decimal/date/datetime
types, the compiled reference grammars, the placeholder vocabulary, the whole
recursive validation graph, and the raw ``__slots__`` member descriptors are
captured once in private closure state at module construction.  Constructors and
the public validation/projection/copy surface below resolve those captured
validators and captured slot descriptors, never a mutable module-global name and
never a rebindable class-level attribute view.  Rebinding module constants,
module validator/helper names, class methods or slot attribute descriptors
therefore cannot re-authorise a forged or low-level-mutated value.

The authoritative consumer protocol is explicit:

* ``validate_*`` returns only independently validated primitive/leaf values and
  raises on any forged, mutated, subclassed or incomplete state;
* ``project_*`` returns a freshly validated canonical instance of the same type;
  and
* ``copy_*`` returns a freshly validated copy of the same type.

Raw attribute reads are NOT part of the authoritative protocol: after
``object.__setattr__`` or arbitrary memory-level tampering a raw read can still
observe the tampered slot, and rebinding a class attribute descriptor (for
example replacing ``PlanPrice.amount`` with a property) can change what an
ordinary attribute read observes.  Likewise the ordinary ``copy.copy``,
``copy.deepcopy`` and ``pickle`` protocols -- implemented as rebindable
``__copy__``/``__deepcopy__``/``__reduce__`` class methods -- are best-effort
revalidation only and are NOT part of the authoritative boundary; they cannot be
made trustworthy under class-method rebinding, so no such compatibility is
claimed.  Consumers that must trust a value must go through a
``validate_*``/``project_*``/``copy_*`` call.  This is a same-process integrity
boundary, not a defence against a hostile process with full memory access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from types import MappingProxyType


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


class PolicyCompletenessStatus(str, Enum):
    POLICY_INCOMPLETE = "policy_incomplete"
    POLICY_INPUTS_COMPLETE = "policy_inputs_complete"


def _build_authority():
    """Construct the immutable authority kernel and its validation graph.

    Everything returned from this function is bound in private closure state, so
    later rebinding of module-global names or class attributes cannot replace
    the captured types, constants, grammars, validators or raw slot descriptors.
    """

    # Exact Founder-settled types captured into closure locals.
    _PlanKey = PlanKey
    _Currency = Currency
    _LaunchModel = LaunchModel
    _VatPriceStatement = VatPriceStatement
    _PriceChangeRule = PriceChangeRule
    _OfferCapabilityRule = OfferCapabilityRule
    _BillingPolicyKey = BillingPolicyKey
    _PolicyCompletenessStatus = PolicyCompletenessStatus
    _Decimal = Decimal
    _Date = date
    _Datetime = datetime
    _Timedelta = timedelta

    # Acceptance-critical builtins/primitive captured into closure locals so
    # later module-level shadowing of ``type``, ``object``, ``len``, ``set``,
    # ``any``, ``str``, ``tuple`` or ``next`` cannot re-authorise forged state.
    _type = type
    _object = object
    _object_getattribute = object.__getattribute__
    _object_setattr = object.__setattr__
    _object_new = object.__new__
    _tuple = tuple
    _len = len
    _set = set
    _any = any
    _str = str
    _next = next
    _frozenset = frozenset
    _TypeError = TypeError
    _ValueError = ValueError
    _AttributeError = AttributeError

    # Exact Founder-settled identity/version facts.
    _founder_decision_id = "FD-W10-001"
    _founder_decision_date = date(2026, 9, 2)
    _authority_version = "FD-W10-001/2026-09-02/v1"

    # Exact Founder-settled price catalogue (immutable).
    _expected_amounts = MappingProxyType(
        {
            _PlanKey.MONTHLY: _Decimal("29"),
            _PlanKey.SIX_MONTH: _Decimal("156"),
            _PlanKey.YEARLY: _Decimal("288"),
        }
    )
    _expected_plan_order = (_PlanKey.MONTHLY, _PlanKey.SIX_MONTH, _PlanKey.YEARLY)

    _required_billing_policy_keys = _tuple(_BillingPolicyKey)

    # Exact provenance/placeholder grammars (immutable).
    _identifier = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}$")
    _record_reference = re.compile(
        r"^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+#[A-Za-z0-9_.:-]+$"
    )
    _placeholder_outcomes = _frozenset(
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
    _placeholder_terminal_punctuation = ".,!?;:"
    _tbd_tbc_placeholder = re.compile(r"^t\s*\.?\s*b\s*\.?\s*[dc]$")

    def _capture_slots(cls: type, names: tuple[str, ...]) -> tuple[object, ...]:
        """Capture the raw ``__slots__`` member descriptors for one dataclass."""
        descriptors: list[object] = []
        for name in names:
            descriptors.append(cls.__dict__[name])
        return _tuple(descriptors)

    def _read_slots(
        value: object,
        owner: type,
        descriptors: tuple[object, ...],
        context: str,
    ) -> tuple[object, ...]:
        """Read exact raw slot values without invoking a rebound class view."""
        if _type(value) is not owner:
            raise _TypeError(f"{context} must be an exact {owner.__name__}")
        values: list[object] = []
        for descriptor in descriptors:
            try:
                values.append(descriptor.__get__(value, owner))
            except _AttributeError:
                raise _ValueError(f"{context} state is incomplete") from None
        return _tuple(values)

    def _rebuild(cls: type, names: tuple[str, ...], values: tuple[object, ...]) -> object:
        """Reconstruct one canonical instance directly from validated raw values."""
        instance = _object_new(cls)
        index = 0
        for name in names:
            _object_setattr(instance, name, values[index])
            index += 1
        return instance

    def _bounded_text(value: object, field: str, *, maximum: int) -> str:
        if _type(value) is not _str:
            raise _TypeError(f"{field} must be an exact string")
        if not value or value != value.strip() or _len(value) > maximum or not value.isprintable():
            raise _ValueError(
                f"{field} must be non-empty, trimmed, printable and at most {maximum} chars"
            )
        return value

    def _placeholder_form(value: str) -> str:
        """Normalize only case, whitespace and harmless terminal punctuation."""
        normalized = " ".join(value.strip().casefold().split())
        return normalized.rstrip(" " + _placeholder_terminal_punctuation)

    def _is_placeholder_outcome(value: str) -> bool:
        normalized = _placeholder_form(value)
        return (
            normalized in _placeholder_outcomes
            or _tbd_tbc_placeholder.fullmatch(normalized) is not None
        )

    @dataclass(frozen=True, slots=True)
    class PlanPrice:
        """One exact, Founder-authorised initial customer price."""

        key: PlanKey
        amount: Decimal
        currency: Currency

        def __post_init__(self) -> None:
            validate_plan_price(self)

        def __copy__(self) -> "PlanPrice":
            return copy_plan_price(self)

        def __deepcopy__(self, memo: dict) -> "PlanPrice":
            return self.__copy__()

        def __reduce__(self):
            key, amount, currency = validate_plan_price(self)
            return (PlanPrice, (key, amount, currency))

    _plan_price_slot_names = ("key", "amount", "currency")
    _plan_price_slots = _capture_slots(PlanPrice, _plan_price_slot_names)

    def validate_plan_price(value: object) -> tuple[_PlanKey, _Decimal, _Currency]:
        key, amount, currency = _read_slots(
            value, PlanPrice, _plan_price_slots, "plan"
        )
        if _type(key) is not _PlanKey:
            raise _TypeError("key must be an exact PlanKey")
        if _type(amount) is not _Decimal:
            raise _TypeError("amount must be an exact Decimal")
        if not amount.is_finite():
            raise _ValueError("amount must be finite")
        if amount != _expected_amounts[key]:
            raise _ValueError(f"amount does not match {_authority_version} for {key.value}")
        if _type(currency) is not _Currency or currency is not _Currency.GBP:
            raise _ValueError("currency must be the exact settled GBP value")
        return key, amount, currency

    def copy_plan_price(value: object) -> PlanPrice:
        key, amount, currency = validate_plan_price(value)
        return _rebuild(PlanPrice, _plan_price_slot_names, (key, amount, currency))

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
            validate_billing_authority(self)

        def plan(self, key: PlanKey) -> PlanPrice:
            values = validate_billing_authority(self)
            if _type(key) is not _PlanKey:
                raise _TypeError("key must be an exact PlanKey")
            plans = values[4]
            return plans[_expected_plan_order.index(key)]

        def __copy__(self) -> "BillingAuthority":
            return copy_billing_authority(self)

        def __deepcopy__(self, memo: dict) -> "BillingAuthority":
            return self.__copy__()

        def __reduce__(self):
            return (BillingAuthority, validate_billing_authority(self))

    _billing_authority_slot_names = (
        "decision_id",
        "decision_date",
        "authority_version",
        "launch_model",
        "plans",
        "vat_price_statement",
        "price_change_rule",
        "offer_capability_rule",
    )
    _billing_authority_slots = _capture_slots(
        BillingAuthority, _billing_authority_slot_names
    )

    def validate_billing_authority(value: object) -> tuple:
        (
            decision_id,
            decision_date,
            authority_version,
            launch_model,
            plans,
            vat_price_statement,
            price_change_rule,
            offer_capability_rule,
        ) = _read_slots(
            value,
            BillingAuthority,
            _billing_authority_slots,
            "billing authority",
        )
        if _type(decision_id) is not _str or decision_id != _founder_decision_id:
            raise _ValueError("decision_id must bind exactly to FD-W10-001")
        if _type(decision_date) is not _Date or decision_date != _founder_decision_date:
            raise _ValueError("decision_date must bind exactly to FD-W10-001")
        if _type(authority_version) is not _str or authority_version != _authority_version:
            raise _ValueError("authority_version must bind exactly to FD-W10-001")
        if (
            _type(launch_model) is not _LaunchModel
            or launch_model is not _LaunchModel.PAID_SUBSCRIPTION
        ):
            raise _ValueError("launch_model must be the settled paid-subscription model")
        if _type(plans) is not _tuple:
            raise _TypeError("plans must be an exact tuple")
        validated_plans = _tuple(validate_plan_price(plan)[0] for plan in plans)
        if validated_plans != _expected_plan_order:
            raise _ValueError(
                "plans must contain each settled key exactly once in canonical order"
            )
        if (
            _type(vat_price_statement) is not _VatPriceStatement
            or vat_price_statement is not _VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE
        ):
            raise _ValueError(
                "VAT metadata must preserve the settled where-applicable statement"
            )
        if (
            _type(price_change_rule) is not _PriceChangeRule
            or price_change_rule
            is not _PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION
        ):
            raise _ValueError("price changes must require later Founder authority")
        if (
            _type(offer_capability_rule) is not _OfferCapabilityRule
            or offer_capability_rule
            is not _OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY
        ):
            raise _ValueError(
                "offers must remain a capability requirement without policy semantics"
            )
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

    def copy_billing_authority(value: object) -> BillingAuthority:
        return _rebuild(
            BillingAuthority,
            _billing_authority_slot_names,
            validate_billing_authority(value),
        )

    @dataclass(frozen=True, slots=True)
    class DecisionProvenance:
        """Minimum immutable evidence needed to trace one policy outcome."""

        decision_id: str
        decided_by: str
        decided_at: datetime
        record_reference: str

        def __post_init__(self) -> None:
            validate_decision_provenance(self)

        def __copy__(self) -> "DecisionProvenance":
            return copy_decision_provenance(self)

        def __deepcopy__(self, memo: dict) -> "DecisionProvenance":
            return self.__copy__()

        def __reduce__(self):
            return (DecisionProvenance, validate_decision_provenance(self))

    _decision_provenance_slot_names = (
        "decision_id",
        "decided_by",
        "decided_at",
        "record_reference",
    )
    _decision_provenance_slots = _capture_slots(
        DecisionProvenance, _decision_provenance_slot_names
    )

    def validate_decision_provenance(value: object) -> tuple[str, str, _Datetime, str]:
        decision_id, decided_by, decided_at, record_reference = _read_slots(
            value,
            DecisionProvenance,
            _decision_provenance_slots,
            "decision provenance",
        )
        decision_id = _bounded_text(decision_id, "decision_id", maximum=128)
        if _identifier.fullmatch(decision_id) is None:
            raise _ValueError("decision_id must be a stable uppercase hyphenated identifier")
        decided_by = _bounded_text(decided_by, "decided_by", maximum=128)
        if _type(decided_at) is not _Datetime:
            raise _TypeError("decided_at must be an exact datetime")
        if decided_at.tzinfo is None or decided_at.utcoffset() != _Timedelta(0):
            raise _ValueError("decided_at must be timezone-aware UTC")
        record_reference = _bounded_text(
            record_reference, "record_reference", maximum=256
        )
        if _record_reference.fullmatch(record_reference) is None:
            raise _ValueError("record_reference must identify a local record and section")
        record_path, _section = record_reference.rsplit("#", 1)
        if _any(segment in {".", ".."} for segment in record_path.split("/")):
            raise _ValueError("record_reference path must not contain dot segments")
        return decision_id, decided_by, decided_at, record_reference

    def copy_decision_provenance(value: object) -> DecisionProvenance:
        return _rebuild(
            DecisionProvenance,
            _decision_provenance_slot_names,
            validate_decision_provenance(value),
        )

    @dataclass(frozen=True, slots=True)
    class BillingPolicyDecision:
        """An explicit policy input; it has no executable billing or access effect."""

        key: BillingPolicyKey
        outcome: str
        provenance: DecisionProvenance

        def __post_init__(self) -> None:
            validate_billing_policy_decision(self)

        def __copy__(self) -> "BillingPolicyDecision":
            return copy_billing_policy_decision(self)

        def __deepcopy__(self, memo: dict) -> "BillingPolicyDecision":
            return self.__copy__()

        def __reduce__(self):
            return (BillingPolicyDecision, validate_billing_policy_decision(self))

    _billing_policy_decision_slot_names = ("key", "outcome", "provenance")
    _billing_policy_decision_slots = _capture_slots(
        BillingPolicyDecision, _billing_policy_decision_slot_names
    )

    def validate_billing_policy_decision(
        value: object,
    ) -> tuple[_BillingPolicyKey, str, DecisionProvenance]:
        key, outcome, provenance = _read_slots(
            value,
            BillingPolicyDecision,
            _billing_policy_decision_slots,
            "billing policy decision",
        )
        if _type(key) is not _BillingPolicyKey:
            raise _TypeError("key must be an exact BillingPolicyKey")
        outcome = _bounded_text(outcome, "outcome", maximum=2000)
        if _is_placeholder_outcome(outcome):
            raise _ValueError("outcome must be explicit, not a placeholder or provider default")
        validate_decision_provenance(provenance)
        return key, outcome, provenance

    def copy_billing_policy_decision(value: object) -> BillingPolicyDecision:
        return _rebuild(
            BillingPolicyDecision,
            _billing_policy_decision_slot_names,
            validate_billing_policy_decision(value),
        )

    @dataclass(frozen=True, slots=True)
    class BillingPolicyRegister:
        """Validated explicit decisions and their fail-closed completeness status."""

        decisions: tuple[BillingPolicyDecision, ...] = ()

        def __post_init__(self) -> None:
            validate_billing_policy_register(self)

        @property
        def missing_policy_keys(self) -> tuple[BillingPolicyKey, ...]:
            decisions = validate_billing_policy_register(self)
            decided = {decision.key for decision in decisions}
            return _tuple(
                key for key in _required_billing_policy_keys if key not in decided
            )

        @property
        def status(self) -> PolicyCompletenessStatus:
            if self.missing_policy_keys:
                return _PolicyCompletenessStatus.POLICY_INCOMPLETE
            return _PolicyCompletenessStatus.POLICY_INPUTS_COMPLETE

        def decision_for(self, key: BillingPolicyKey) -> BillingPolicyDecision | None:
            decisions = validate_billing_policy_register(self)
            if _type(key) is not _BillingPolicyKey:
                raise _TypeError("key must be an exact BillingPolicyKey")
            return _next((decision for decision in decisions if decision.key is key), None)

        def __copy__(self) -> "BillingPolicyRegister":
            return copy_billing_policy_register(self)

        def __deepcopy__(self, memo: dict) -> "BillingPolicyRegister":
            return self.__copy__()

        def __reduce__(self):
            return (BillingPolicyRegister, (validate_billing_policy_register(self),))

    _billing_policy_register_slot_names = ("decisions",)
    _billing_policy_register_slots = _capture_slots(
        BillingPolicyRegister, _billing_policy_register_slot_names
    )

    def validate_billing_policy_register(
        value: object,
    ) -> tuple[BillingPolicyDecision, ...]:
        (decisions,) = _read_slots(
            value,
            BillingPolicyRegister,
            _billing_policy_register_slots,
            "billing policy register",
        )
        if _type(decisions) is not _tuple:
            raise _TypeError("decisions must be an exact tuple")
        if _any(_type(decision) is not BillingPolicyDecision for decision in decisions):
            raise _TypeError(
                "decisions must contain only exact BillingPolicyDecision values"
            )
        keys = _tuple(validate_billing_policy_decision(decision)[0] for decision in decisions)
        if _len(keys) != _len(_set(keys)):
            raise _ValueError("duplicate billing policy keys are not allowed")
        return decisions

    def copy_billing_policy_register(value: object) -> BillingPolicyRegister:
        return _rebuild(
            BillingPolicyRegister,
            _billing_policy_register_slot_names,
            (validate_billing_policy_register(value),),
        )

    initial_billing_authority = BillingAuthority(
        decision_id=_founder_decision_id,
        decision_date=_founder_decision_date,
        authority_version=_authority_version,
        launch_model=_LaunchModel.PAID_SUBSCRIPTION,
        plans=_tuple(
            PlanPrice(key=key, amount=_expected_amounts[key], currency=_Currency.GBP)
            for key in _expected_plan_order
        ),
        vat_price_statement=_VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE,
        price_change_rule=_PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION,
        offer_capability_rule=_OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY,
    )

    def project_plan_price(value: object) -> PlanPrice:
        key, amount, currency = validate_plan_price(value)
        return _rebuild(PlanPrice, _plan_price_slot_names, (key, amount, currency))

    def project_billing_authority(value: object) -> BillingAuthority:
        return _rebuild(
            BillingAuthority,
            _billing_authority_slot_names,
            validate_billing_authority(value),
        )

    def project_decision_provenance(value: object) -> DecisionProvenance:
        return _rebuild(
            DecisionProvenance,
            _decision_provenance_slot_names,
            validate_decision_provenance(value),
        )

    def project_billing_policy_decision(value: object) -> BillingPolicyDecision:
        return _rebuild(
            BillingPolicyDecision,
            _billing_policy_decision_slot_names,
            validate_billing_policy_decision(value),
        )

    def project_billing_policy_register(value: object) -> BillingPolicyRegister:
        return _rebuild(
            BillingPolicyRegister,
            _billing_policy_register_slot_names,
            (validate_billing_policy_register(value),),
        )

    return {
        "founder_decision_id": _founder_decision_id,
        "founder_decision_date": _founder_decision_date,
        "authority_version": _authority_version,
        "required_billing_policy_keys": _required_billing_policy_keys,
        "PlanPrice": PlanPrice,
        "BillingAuthority": BillingAuthority,
        "DecisionProvenance": DecisionProvenance,
        "BillingPolicyDecision": BillingPolicyDecision,
        "BillingPolicyRegister": BillingPolicyRegister,
        "initial_billing_authority": initial_billing_authority,
        "validate_plan_price": validate_plan_price,
        "validate_billing_authority": validate_billing_authority,
        "validate_decision_provenance": validate_decision_provenance,
        "validate_billing_policy_decision": validate_billing_policy_decision,
        "validate_billing_policy_register": validate_billing_policy_register,
        "project_plan_price": project_plan_price,
        "project_billing_authority": project_billing_authority,
        "project_decision_provenance": project_decision_provenance,
        "project_billing_policy_decision": project_billing_policy_decision,
        "project_billing_policy_register": project_billing_policy_register,
        "copy_plan_price": copy_plan_price,
        "copy_billing_authority": copy_billing_authority,
        "copy_decision_provenance": copy_decision_provenance,
        "copy_billing_policy_decision": copy_billing_policy_decision,
        "copy_billing_policy_register": copy_billing_policy_register,
    }


_kernel = _build_authority()

FOUNDER_DECISION_ID = _kernel["founder_decision_id"]
FOUNDER_DECISION_DATE = _kernel["founder_decision_date"]
AUTHORITY_VERSION = _kernel["authority_version"]
REQUIRED_BILLING_POLICY_KEYS = _kernel["required_billing_policy_keys"]

PlanPrice = _kernel["PlanPrice"]
BillingAuthority = _kernel["BillingAuthority"]
DecisionProvenance = _kernel["DecisionProvenance"]
BillingPolicyDecision = _kernel["BillingPolicyDecision"]
BillingPolicyRegister = _kernel["BillingPolicyRegister"]

INITIAL_BILLING_AUTHORITY = _kernel["initial_billing_authority"]

validate_plan_price = _kernel["validate_plan_price"]
validate_billing_authority = _kernel["validate_billing_authority"]
validate_decision_provenance = _kernel["validate_decision_provenance"]
validate_billing_policy_decision = _kernel["validate_billing_policy_decision"]
validate_billing_policy_register = _kernel["validate_billing_policy_register"]

project_plan_price = _kernel["project_plan_price"]
project_billing_authority = _kernel["project_billing_authority"]
project_decision_provenance = _kernel["project_decision_provenance"]
project_billing_policy_decision = _kernel["project_billing_policy_decision"]
project_billing_policy_register = _kernel["project_billing_policy_register"]

copy_plan_price = _kernel["copy_plan_price"]
copy_billing_authority = _kernel["copy_billing_authority"]
copy_decision_provenance = _kernel["copy_decision_provenance"]
copy_billing_policy_decision = _kernel["copy_billing_policy_decision"]
copy_billing_policy_register = _kernel["copy_billing_policy_register"]

# Classes are built inside the closure; make them importable/pickleable under
# their ordinary module-level names.
for _class in (
    PlanPrice,
    BillingAuthority,
    DecisionProvenance,
    BillingPolicyDecision,
    BillingPolicyRegister,
):
    _class.__qualname__ = _class.__name__

del _class, _kernel

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
    "copy_billing_authority",
    "copy_billing_policy_decision",
    "copy_billing_policy_register",
    "copy_decision_provenance",
    "copy_plan_price",
    "project_billing_authority",
    "project_billing_policy_decision",
    "project_billing_policy_register",
    "project_decision_provenance",
    "project_plan_price",
    "validate_billing_authority",
    "validate_billing_policy_decision",
    "validate_billing_policy_register",
    "validate_decision_provenance",
    "validate_plan_price",
)
