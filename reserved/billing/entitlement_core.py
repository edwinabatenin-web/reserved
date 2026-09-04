"""Provider-neutral W10-S3A entitlement transition policy kernel.

This module models FD-W10-003 over observations already verified and reconciled
by a later provider/event-inbox boundary.  It does not verify signatures,
ingest webhooks, persist state, grant route access, contact Stripe, charge money
or activate billing.  Its access result is a policy projection for later S5
enforcement, never evidence that a provider event was authentic.
"""

from __future__ import annotations

import copy as _copy_module
import weakref as _weakref_module
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


CONTRACT_VERSION = "reserved-w10-entitlement-transition/1.0"
RECOVERY_DAYS = 7


class EntitlementState(str, Enum):
    NO_ENTITLEMENT = "no_entitlement"
    PAID = "paid"
    PAYMENT_RECOVERY = "payment_recovery"
    SUSPENDED = "suspended"


class BillingObservationKind(str, Enum):
    INITIAL_PAYMENT_CONFIRMED = "initial_payment_confirmed"
    RENEWAL_PAYMENT_CONFIRMED = "renewal_payment_confirmed"
    RENEWAL_PAYMENT_FAILED = "renewal_payment_failed"
    CANCELLATION_CONFIRMED = "cancellation_confirmed"


@dataclass(frozen=True, slots=True)
class ReconciledBillingObservation:
    """Canonical shape for a separately verified/reconciled observation.

    Construction proves shape only. Authenticity, provider signature, account
    ownership and source verification remain S3/S4 responsibilities.
    """

    contract_version: str
    event_id: str
    owner_id: str
    billing_account_id: str
    subscription_id: str
    kind: BillingObservationKind
    effective_date: date
    paid_through: date | None
    evidence_reference: str

    def __post_init__(self) -> None:
        _validate_observation_shape(self)


@dataclass(frozen=True, slots=True)
class AccessProjection:
    state: EntitlementState
    ordinary_access: bool
    reason: str
    valid_from_inclusive: date | None
    valid_until_exclusive: date | None


def _validate_observation_shape(value: object) -> ReconciledBillingObservation:
    if type(value) is not ReconciledBillingObservation:
        raise TypeError("observation must be an exact reconciled observation")
    if value.contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported billing observation contract")
    for name in (
        "event_id",
        "owner_id",
        "billing_account_id",
        "subscription_id",
        "evidence_reference",
    ):
        field_value = getattr(value, name)
        if type(field_value) is not str or not field_value or len(field_value) > 160:
            raise ValueError(f"invalid billing observation {name}")
    if type(value.kind) is not BillingObservationKind:
        raise ValueError("invalid billing observation kind")
    if type(value.effective_date) is not date:
        raise ValueError("invalid billing observation effective date")
    if value.paid_through is not None and type(value.paid_through) is not date:
        raise ValueError("invalid billing observation paid-through date")
    if value.kind in (
        BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
        BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
    ):
        if value.paid_through is None or value.paid_through < value.effective_date:
            raise ValueError("confirmed payment requires a current paid period")
    elif value.paid_through is not None:
        raise ValueError("non-payment observation must not invent a paid period")
    return value


def _build_entitlement_kernel():
    _type = type
    _id = id
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _dict = dict
    _zip = zip
    _len = len
    _str = str
    _bool = bool
    _date = date
    _timedelta = timedelta
    _TypeError = TypeError
    _ValueError = ValueError
    _AttributeError = AttributeError
    _WeakValueDictionary = _weakref_module.WeakValueDictionary
    _copy = _copy_module.copy
    _deepcopy = _copy_module.deepcopy
    _contract_version = CONTRACT_VERSION
    _recovery_days = RECOVERY_DAYS
    _State = EntitlementState
    _Kind = BillingObservationKind
    _Observation = ReconciledBillingObservation
    _Access = AccessProjection
    _observation_field_names = (
        "contract_version",
        "event_id",
        "owner_id",
        "billing_account_id",
        "subscription_id",
        "kind",
        "effective_date",
        "paid_through",
        "evidence_reference",
    )
    _observation_descriptors = _tuple(
        _Observation.__dict__[name] for name in _observation_field_names
    )

    def _observation_field(value, name):
        descriptor = _observation_descriptors[_observation_field_names.index(name)]
        return descriptor.__get__(value, _Observation)

    def _validate_observation(value):
        if _type(value) is not _Observation:
            raise _TypeError("observation must be an exact reconciled observation")
        if _observation_field(value, "contract_version") != _contract_version:
            raise _ValueError("unsupported billing observation contract")
        for name in (
            "event_id",
            "owner_id",
            "billing_account_id",
            "subscription_id",
            "evidence_reference",
        ):
            field_value = _observation_field(value, name)
            if _type(field_value) is not _str or not field_value or _len(field_value) > 160:
                raise _ValueError(f"invalid billing observation {name}")
        kind = _observation_field(value, "kind")
        effective = _observation_field(value, "effective_date")
        paid_through = _observation_field(value, "paid_through")
        if _type(kind) is not _Kind:
            raise _ValueError("invalid billing observation kind")
        if _type(effective) is not _date:
            raise _ValueError("invalid billing observation effective date")
        if paid_through is not None and _type(paid_through) is not _date:
            raise _ValueError("invalid billing observation paid-through date")
        if kind in (_Kind.INITIAL_PAYMENT_CONFIRMED, _Kind.RENEWAL_PAYMENT_CONFIRMED):
            if paid_through is None or paid_through < effective:
                raise _ValueError("confirmed payment requires a current paid period")
        elif paid_through is not None:
            raise _ValueError("non-payment observation must not invent a paid period")
        return value

    _state_keys = (
        "contract_version",
        "owner_id",
        "billing_account_id",
        "subscription_id",
        "state",
        "renews_automatically",
        "entitlement_started_on",
        "paid_through",
        "recovery_started_on",
        "recovery_deadline_exclusive",
        "last_effective_date",
        "processed_observations",
    )

    class EntitlementTransitionProjection:
        """Opaque producer-issued transition state; project for immutable facts."""

        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _token:
                raise _TypeError("entitlement projections are producer-issued only")
            return _object_new(cls)

        def __getattr__(self, name):
            state = _state_dict(_validated_state(self))
            if name == "processed_event_ids":
                return _tuple(item[0] for item in state["processed_observations"])
            if name == "evidence_references":
                return _tuple(item[7] for item in state["processed_observations"])
            if name not in _state_keys:
                raise _AttributeError(name)
            return state[name]

        def __copy__(self):
            return copy_entitlement_transition(self)

        def __deepcopy__(self, memo):
            return copy_entitlement_transition(self)

        def __reduce__(self):
            raise _TypeError("entitlement projections are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("entitlement projections are not serialisable")

    _Handle = EntitlementTransitionProjection
    _token = _object()
    _registry = {}
    _live = _WeakValueDictionary()

    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _bool, _date) or value is None:
            return value
        if _type(value) is _State:
            return value
        raise _ValueError("entitlement projection contains unsupported state")

    def _state_dict(state):
        return _dict(_zip(_state_keys, state, strict=True))

    def _issue(state):
        state = _clone(state)
        handle = _object_new(_Handle)
        identity = _id(handle)
        _registry[identity] = state
        _live[identity] = handle
        return handle

    def _validated_state(value):
        if _type(value) is not _Handle:
            raise _TypeError("current value must be an exact entitlement projection")
        identity = _id(value)
        if _live.get(identity) is not value or identity not in _registry:
            raise _ValueError("entitlement projection is not producer-issued or is stale")
        state = _registry[identity]
        if _type(state) is not _tuple or _len(state) != _len(_state_keys):
            raise _ValueError("entitlement projection registry binding is invalid")
        return _clone(state)

    def _observation_fingerprint(observation):
        _validate_observation(observation)
        event_id = _observation_field(observation, "event_id")
        owner_id = _observation_field(observation, "owner_id")
        billing_account_id = _observation_field(observation, "billing_account_id")
        subscription_id = _observation_field(observation, "subscription_id")
        kind = _observation_field(observation, "kind")
        effective = _observation_field(observation, "effective_date")
        paid_through = _observation_field(observation, "paid_through")
        evidence = _observation_field(observation, "evidence_reference")
        return (
            event_id,
            owner_id,
            billing_account_id,
            subscription_id,
            kind.value,
            effective.isoformat(),
            paid_through.isoformat() if paid_through is not None else None,
            evidence,
        )

    def _replace_state(current_state, **updates):
        values = _state_dict(current_state)
        values.update(updates)
        return _tuple(values[key] for key in _state_keys)

    def empty_entitlement(*, owner_id, billing_account_id, subscription_id):
        for name, value in (
            ("owner_id", owner_id),
            ("billing_account_id", billing_account_id),
            ("subscription_id", subscription_id),
        ):
            if _type(value) is not _str or not value or _len(value) > 160:
                raise _ValueError(f"invalid entitlement {name}")
        return _issue(
            (
                _contract_version,
                owner_id,
                billing_account_id,
                subscription_id,
                _State.NO_ENTITLEMENT,
                False,
                None,
                None,
                None,
                None,
                None,
                (),
            )
        )

    def validate_entitlement_transition(value):
        return _validated_state(value)

    def project_entitlement_transition(value):
        return _tuple(zip(_state_keys, _validated_state(value), strict=True))

    def copy_entitlement_transition(value):
        return _issue(_validated_state(value))

    def apply_reconciled_observation(current, observation):
        state = _validated_state(current)
        values = _state_dict(state)
        if _type(observation) is not _Observation:
            raise _TypeError("observation must be an exact reconciled observation")
        fingerprint = _observation_fingerprint(observation)
        event_id = fingerprint[0]
        owner_id = fingerprint[1]
        billing_account_id = fingerprint[2]
        subscription_id = fingerprint[3]
        kind = _Kind(fingerprint[4])
        effective_date = _date.fromisoformat(fingerprint[5])
        paid_through = (
            _date.fromisoformat(fingerprint[6]) if fingerprint[6] is not None else None
        )
        if (
            owner_id != values["owner_id"]
            or billing_account_id != values["billing_account_id"]
            or subscription_id != values["subscription_id"]
        ):
            raise _ValueError("billing observation ownership boundary mismatch")

        for previous in values["processed_observations"]:
            if previous[0] == event_id:
                if previous == fingerprint:
                    return current
                raise _ValueError("billing event identity was reused with different content")
        if (
            values["last_effective_date"] is not None
            and effective_date <= values["last_effective_date"]
        ):
            raise _ValueError(
                "out-of-order or same-day billing observation requires reconciliation"
            )

        processed = values["processed_observations"] + (fingerprint,)
        if kind is _Kind.INITIAL_PAYMENT_CONFIRMED:
            if values["state"] is not _State.NO_ENTITLEMENT:
                raise _ValueError("initial payment cannot replace existing lifecycle state")
            return _issue(
                _replace_state(
                    state,
                    state=_State.PAID,
                    renews_automatically=True,
                    entitlement_started_on=effective_date,
                    paid_through=paid_through,
                    last_effective_date=effective_date,
                    processed_observations=processed,
                )
            )

        if kind is _Kind.RENEWAL_PAYMENT_CONFIRMED:
            recoverable_suspension = (
                values["state"] is _State.SUSPENDED
                and values["recovery_started_on"] is not None
                and values["recovery_deadline_exclusive"] is not None
            )
            if values["state"] not in (_State.PAID, _State.PAYMENT_RECOVERY) and not recoverable_suspension:
                raise _ValueError("renewal payment cannot create initial entitlement")
            if not values["renews_automatically"]:
                raise _ValueError("renewal payment after cancellation requires reconciliation")
            if paid_through <= values["paid_through"]:
                raise _ValueError("renewal payment must advance the paid period")
            return _issue(
                _replace_state(
                    state,
                    state=_State.PAID,
                    paid_through=paid_through,
                    recovery_started_on=None,
                    recovery_deadline_exclusive=None,
                    last_effective_date=effective_date,
                    processed_observations=processed,
                )
            )

        if kind is _Kind.RENEWAL_PAYMENT_FAILED:
            if values["state"] is _State.PAYMENT_RECOVERY:
                if effective_date >= values["recovery_deadline_exclusive"]:
                    return _issue(
                        _replace_state(
                            state,
                            state=_State.SUSPENDED,
                            last_effective_date=effective_date,
                            processed_observations=processed,
                        )
                    )
                return _issue(
                    _replace_state(
                        state,
                        last_effective_date=effective_date,
                        processed_observations=processed,
                    )
                )
            if values["state"] is not _State.PAID:
                raise _ValueError("failed renewal cannot create entitlement")
            if not values["renews_automatically"]:
                raise _ValueError("failed renewal after cancellation requires reconciliation")
            if effective_date <= values["paid_through"]:
                raise _ValueError("failed renewal cannot truncate an already-paid period")
            return _issue(
                _replace_state(
                    state,
                    state=_State.PAYMENT_RECOVERY,
                    recovery_started_on=effective_date,
                    recovery_deadline_exclusive=effective_date
                    + _timedelta(days=_recovery_days),
                    last_effective_date=effective_date,
                    processed_observations=processed,
                )
            )

        if kind is _Kind.CANCELLATION_CONFIRMED:
            if values["state"] is not _State.PAID:
                raise _ValueError("cancellation outside paid state requires reconciliation")
            if effective_date > values["paid_through"]:
                raise _ValueError("late cancellation requires reconciliation")
            return _issue(
                _replace_state(
                    state,
                    renews_automatically=False,
                    last_effective_date=effective_date,
                    processed_observations=processed,
                )
            )
        raise _ValueError("unsupported billing observation")

    def project_ordinary_access(current, *, as_of):
        values = _state_dict(_validated_state(current))
        if _type(as_of) is not _date:
            raise _TypeError("an exact date is required")
        if values["state"] is _State.PAID:
            allowed = (
                values["entitlement_started_on"] <= as_of <= values["paid_through"]
            )
            return _Access(
                values["state"],
                allowed,
                "verified_paid_period" if allowed else "outside_verified_paid_period",
                values["entitlement_started_on"] if allowed else None,
                values["paid_through"] + _timedelta(days=1) if allowed else None,
            )
        if values["state"] is _State.PAYMENT_RECOVERY:
            in_paid_period = (
                values["entitlement_started_on"] <= as_of <= values["paid_through"]
            )
            in_recovery_period = (
                values["recovery_started_on"] <= as_of
                and as_of < values["recovery_deadline_exclusive"]
            )
            allowed = in_paid_period or in_recovery_period
            return _Access(
                values["state"],
                allowed,
                (
                    "verified_paid_period"
                    if in_paid_period
                    else "bounded_payment_recovery"
                    if in_recovery_period
                    else "outside_paid_and_recovery_periods"
                ),
                (
                    values["entitlement_started_on"]
                    if in_paid_period
                    else values["recovery_started_on"]
                    if in_recovery_period
                    else None
                ),
                (
                    values["paid_through"] + _timedelta(days=1)
                    if in_paid_period
                    else values["recovery_deadline_exclusive"]
                    if in_recovery_period
                    else None
                ),
            )
        return _Access(
            values["state"], False, "no_ordinary_paid_access", None, None
        )

    def materialise_time_boundary(current, *, as_of):
        state = _validated_state(current)
        values = _state_dict(state)
        if _type(as_of) is not _date:
            raise _TypeError("an exact date is required")
        expired = (
            values["state"] is _State.PAID and as_of > values["paid_through"]
        ) or (
            values["state"] is _State.PAYMENT_RECOVERY
            and as_of >= values["recovery_deadline_exclusive"]
        )
        if not expired:
            return current
        return _issue(_replace_state(state, state=_State.SUSPENDED))

    authority_probe = empty_entitlement(
        owner_id="kernel-probe-owner",
        billing_account_id="kernel-probe-account",
        subscription_id="kernel-probe-subscription",
    )
    validate_entitlement_transition(_copy(authority_probe))
    validate_entitlement_transition(_deepcopy(authority_probe))

    return (
        EntitlementTransitionProjection,
        empty_entitlement,
        validate_entitlement_transition,
        project_entitlement_transition,
        copy_entitlement_transition,
        apply_reconciled_observation,
        project_ordinary_access,
        materialise_time_boundary,
    )


(
    EntitlementTransitionProjection,
    empty_entitlement,
    validate_entitlement_transition,
    project_entitlement_transition,
    copy_entitlement_transition,
    apply_reconciled_observation,
    project_ordinary_access,
    materialise_time_boundary,
) = _build_entitlement_kernel()

EntitlementTransitionProjection.__module__ = __name__
EntitlementTransitionProjection.__qualname__ = EntitlementTransitionProjection.__name__


__all__ = (
    "AccessProjection",
    "BillingObservationKind",
    "CONTRACT_VERSION",
    "EntitlementState",
    "EntitlementTransitionProjection",
    "RECOVERY_DAYS",
    "ReconciledBillingObservation",
    "apply_reconciled_observation",
    "copy_entitlement_transition",
    "empty_entitlement",
    "materialise_time_boundary",
    "project_entitlement_transition",
    "project_ordinary_access",
    "validate_entitlement_transition",
)
