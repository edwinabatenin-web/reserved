"""Provider-neutral W10-S3A entitlement decision-candidate kernel.

This module models the FD-W10-003 lifecycle over detached structural billing
observation candidates. It does not authenticate provider observations or
provenance, persist state, grant route access, contact a provider, charge money
or activate billing. Every returned value is an exact recursively detached
structural candidate. A separately authenticated adapter must validate the
provider/event-inbox evidence before any live consumer relies on the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


CONTRACT_VERSION = "reserved-w10-entitlement-transition/1.0"
RECOVERY_DAYS = 7
CANDIDATE_CLASSIFICATION = "structural_decision_candidate_not_authenticated"
CANDIDATE_SCHEMA_VERSION = "reserved-w10-entitlement-decision-candidate/1.0"
_MAX_PAID_THROUGH = date.max - timedelta(days=1)
_MAX_RECOVERY_START = date.max - timedelta(days=RECOVERY_DAYS)


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
class BillingObservationCandidate:
    """Shape-only input; construction is never provider or reconciliation proof."""

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


# Compatibility name retained for the already published S3A API. The value is
# still only a structural candidate and is not proof that reconciliation ran.
ReconciledBillingObservation = BillingObservationCandidate


# Both exported decision shapes are exact built-in tuples of exact key/value
# pairs. These aliases preserve old imports without suggesting a private handle.
EntitlementTransitionCandidate = tuple
EntitlementTransitionProjection = EntitlementTransitionCandidate
OrdinaryAccessDecisionCandidate = tuple
AccessProjection = OrdinaryAccessDecisionCandidate


def _validate_observation_shape(value: object) -> BillingObservationCandidate:
    if type(value) is not BillingObservationCandidate:
        raise TypeError("observation must be an exact billing observation candidate")
    if type(value.contract_version) is not str or value.contract_version != CONTRACT_VERSION:
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
    if (
        value.kind is BillingObservationKind.INITIAL_PAYMENT_CONFIRMED
        or value.kind is BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED
    ):
        if value.paid_through is None or value.paid_through < value.effective_date:
            raise ValueError("confirmed payment requires a current paid period")
        if value.paid_through > _MAX_PAID_THROUGH:
            raise ValueError(
                "confirmed payment paid-through date exceeds supported boundary"
            )
    elif value.paid_through is not None:
        raise ValueError("non-payment observation must not invent a paid period")
    if (
        value.kind is BillingObservationKind.RENEWAL_PAYMENT_FAILED
        and value.effective_date > _MAX_RECOVERY_START
    ):
        raise ValueError(
            "failed-renewal effective date exceeds supported recovery boundary"
        )
    return value


def _build_entitlement_kernel():
    _type = type
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
    _contract_version = CONTRACT_VERSION
    _candidate_classification = CANDIDATE_CLASSIFICATION
    _candidate_schema_version = CANDIDATE_SCHEMA_VERSION
    _recovery_days = RECOVERY_DAYS
    _max_paid_through = _date.max - _timedelta(days=1)
    _max_recovery_start = _date.max - _timedelta(days=_recovery_days)
    _State = EntitlementState
    _Kind = BillingObservationKind
    _Observation = BillingObservationCandidate
    _initial_payment_kind = _Kind.INITIAL_PAYMENT_CONFIRMED
    _renewal_payment_kind = _Kind.RENEWAL_PAYMENT_CONFIRMED
    _renewal_failure_kind = _Kind.RENEWAL_PAYMENT_FAILED
    _cancellation_kind = _Kind.CANCELLATION_CONFIRMED
    _no_entitlement_state = "no_entitlement"
    _paid_state = "paid"
    _payment_recovery_state = "payment_recovery"
    _suspended_state = "suspended"
    _initial_payment_value = "initial_payment_confirmed"
    _renewal_payment_value = "renewal_payment_confirmed"
    _renewal_failure_value = "renewal_payment_failed"
    _cancellation_value = "cancellation_confirmed"
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
    _state_keys = (
        "contract_version",
        "candidate_schema_version",
        "candidate_classification",
        "provider_observation_authenticated",
        "provider_provenance_authenticated",
        "provider_status_authority",
        "persistence_authority",
        "runtime_access_authority",
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
    _access_keys = (
        "candidate_schema_version",
        "candidate_classification",
        "provider_observation_authenticated",
        "provider_provenance_authenticated",
        "provider_status_authority",
        "persistence_authority",
        "runtime_access_authority",
        "state",
        "ordinary_access",
        "reason",
        "valid_from_inclusive",
        "valid_until_exclusive",
    )
    _state_values = (
        _no_entitlement_state,
        _paid_state,
        _payment_recovery_state,
        _suspended_state,
    )
    _kind_values = (
        _initial_payment_value,
        _renewal_payment_value,
        _renewal_failure_value,
        _cancellation_value,
    )

    def _observation_field(value, name):
        descriptor = _observation_descriptors[_observation_field_names.index(name)]
        return descriptor.__get__(value, _Observation)

    def _validate_identifier(name, value):
        if _type(value) is not _str or not value or _len(value) > 160:
            raise _ValueError(f"invalid {name}")

    def _validate_observation(value):
        if _type(value) is not _Observation:
            raise _TypeError("observation must be an exact billing observation candidate")
        contract_version = _observation_field(value, "contract_version")
        if _type(contract_version) is not _str or contract_version != _contract_version:
            raise _ValueError("unsupported billing observation contract")
        for name in (
            "event_id",
            "owner_id",
            "billing_account_id",
            "subscription_id",
            "evidence_reference",
        ):
            _validate_identifier(
                f"billing observation {name}", _observation_field(value, name)
            )
        kind = _observation_field(value, "kind")
        effective = _observation_field(value, "effective_date")
        paid_through = _observation_field(value, "paid_through")
        if _type(kind) is not _Kind:
            raise _ValueError("invalid billing observation kind")
        if _type(effective) is not _date:
            raise _ValueError("invalid billing observation effective date")
        if paid_through is not None and _type(paid_through) is not _date:
            raise _ValueError("invalid billing observation paid-through date")
        if kind is _initial_payment_kind or kind is _renewal_payment_kind:
            if paid_through is None or paid_through < effective:
                raise _ValueError("confirmed payment requires a current paid period")
            if paid_through > _max_paid_through:
                raise _ValueError(
                    "confirmed payment paid-through date exceeds supported boundary"
                )
        elif paid_through is not None:
            raise _ValueError("non-payment observation must not invent a paid period")
        if kind is _renewal_failure_kind and effective > _max_recovery_start:
            raise _ValueError(
                "failed-renewal effective date exceeds supported recovery boundary"
            )

    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _bool, _date) or value is None:
            return value
        raise _ValueError("decision candidate contains unsupported state")

    def _pairs(keys, values):
        return _tuple(
            (_str(key), _clone(value))
            for key, value in _zip(keys, values, strict=True)
        )

    def _parse_pairs(value, keys, label):
        if _type(value) is not _tuple or _len(value) != _len(keys):
            raise _ValueError(f"{label} must be an exact detached tuple")
        parsed = []
        for expected, item in _zip(keys, value, strict=True):
            if (
                _type(item) is not _tuple
                or _len(item) != 2
                or _type(item[0]) is not _str
                or item[0] != expected
            ):
                raise _ValueError(f"{label} field order or shape is invalid")
            parsed.append(_clone(item[1]))
        return _dict(_zip(keys, _tuple(parsed), strict=True))

    def _empty_values(owner_id, billing_account_id, subscription_id):
        return {
            "contract_version": _contract_version,
            "candidate_schema_version": _candidate_schema_version,
            "candidate_classification": _candidate_classification,
            "provider_observation_authenticated": False,
            "provider_provenance_authenticated": False,
            "provider_status_authority": False,
            "persistence_authority": False,
            "runtime_access_authority": False,
            "owner_id": owner_id,
            "billing_account_id": billing_account_id,
            "subscription_id": subscription_id,
            "state": _no_entitlement_state,
            "renews_automatically": False,
            "entitlement_started_on": None,
            "paid_through": None,
            "recovery_started_on": None,
            "recovery_deadline_exclusive": None,
            "last_effective_date": None,
            "processed_observations": (),
        }

    def _observation_fingerprint(observation):
        _validate_observation(observation)
        paid_through = _observation_field(observation, "paid_through")
        return (
            _observation_field(observation, "event_id"),
            _observation_field(observation, "owner_id"),
            _observation_field(observation, "billing_account_id"),
            _observation_field(observation, "subscription_id"),
            (
                _initial_payment_value
                if _observation_field(observation, "kind") is _initial_payment_kind
                else _renewal_payment_value
                if _observation_field(observation, "kind") is _renewal_payment_kind
                else _renewal_failure_value
                if _observation_field(observation, "kind") is _renewal_failure_kind
                else _cancellation_value
            ),
            _observation_field(observation, "effective_date").isoformat(),
            paid_through.isoformat() if paid_through is not None else None,
            _observation_field(observation, "evidence_reference"),
        )

    def _validate_fingerprint(value, owner_id, billing_account_id, subscription_id):
        if _type(value) is not _tuple or _len(value) != 8:
            raise _ValueError("processed observation fingerprint is invalid")
        event_id, owner, account, subscription, kind, effective_iso, paid_iso, evidence = value
        for name, field in (
            ("event_id", event_id),
            ("owner_id", owner),
            ("billing_account_id", account),
            ("subscription_id", subscription),
            ("evidence_reference", evidence),
        ):
            _validate_identifier(f"processed observation {name}", field)
        if owner != owner_id or account != billing_account_id or subscription != subscription_id:
            raise _ValueError("processed observation ownership boundary mismatch")
        if _type(kind) is not _str or kind not in _kind_values:
            raise _ValueError("processed observation kind is invalid")
        if _type(effective_iso) is not _str:
            raise _ValueError("processed observation effective date is invalid")
        try:
            effective = _date.fromisoformat(effective_iso)
        except (TypeError, ValueError) as error:
            raise _ValueError("processed observation effective date is invalid") from error
        if effective.isoformat() != effective_iso:
            raise _ValueError("processed observation effective date is non-canonical")
        if paid_iso is None:
            paid_through = None
        else:
            if _type(paid_iso) is not _str:
                raise _ValueError("processed observation paid-through date is invalid")
            try:
                paid_through = _date.fromisoformat(paid_iso)
            except (TypeError, ValueError) as error:
                raise _ValueError("processed observation paid-through date is invalid") from error
            if paid_through.isoformat() != paid_iso:
                raise _ValueError("processed observation paid-through date is non-canonical")
        if kind in (
            _initial_payment_value,
            _renewal_payment_value,
        ):
            if paid_through is None or paid_through < effective:
                raise _ValueError("confirmed payment fingerprint requires a current paid period")
            if paid_through > _max_paid_through:
                raise _ValueError(
                    "confirmed payment fingerprint exceeds supported boundary"
                )
        elif paid_through is not None:
            raise _ValueError("non-payment fingerprint must not invent a paid period")
        if kind == _renewal_failure_value and effective > _max_recovery_start:
            raise _ValueError(
                "failed-renewal fingerprint exceeds supported recovery boundary"
            )
        return value

    def _apply_fingerprint(values, fingerprint):
        (
            event_id,
            owner_id,
            account_id,
            subscription_id,
            kind,
            effective_iso,
            paid_iso,
            _,
        ) = fingerprint
        if (
            owner_id != values["owner_id"]
            or account_id != values["billing_account_id"]
            or subscription_id != values["subscription_id"]
        ):
            raise _ValueError("billing observation ownership boundary mismatch")
        for previous in values["processed_observations"]:
            if previous[0] == event_id:
                if previous == fingerprint:
                    return values, False
                raise _ValueError("billing event identity was reused with different content")
        effective = _date.fromisoformat(effective_iso)
        paid_through = (
            _date.fromisoformat(paid_iso) if paid_iso is not None else None
        )
        if (
            values["last_effective_date"] is not None
            and effective <= values["last_effective_date"]
        ):
            raise _ValueError(
                "out-of-order or same-day billing observation requires reconciliation"
            )
        processed = values["processed_observations"] + (fingerprint,)
        updated = _dict(values)

        if kind == _initial_payment_value:
            if values["state"] != _no_entitlement_state:
                raise _ValueError("initial payment cannot replace existing lifecycle state")
            updated.update(
                state=_paid_state,
                renews_automatically=True,
                entitlement_started_on=effective,
                paid_through=paid_through,
                last_effective_date=effective,
                processed_observations=processed,
            )
            return updated, True

        if kind == _renewal_payment_value:
            suspended_recovery = (
                values["state"] == _suspended_state
                and values["recovery_started_on"] is not None
                and values["recovery_deadline_exclusive"] is not None
            )
            suspended_paid_period = (
                values["state"] == _suspended_state
                and values["entitlement_started_on"] is not None
                and values["paid_through"] is not None
                and values["recovery_started_on"] is None
                and values["recovery_deadline_exclusive"] is None
            )
            if values["state"] not in (
                _paid_state,
                _payment_recovery_state,
            ) and not suspended_recovery and not suspended_paid_period:
                raise _ValueError("renewal payment cannot create initial entitlement")
            if not values["renews_automatically"]:
                raise _ValueError(
                    "renewal payment after cancellation requires reconciliation"
                )
            if (
                suspended_recovery
                and effective < values["recovery_deadline_exclusive"]
            ):
                raise _ValueError(
                    "renewal predating a suspended recovery deadline requires reconciliation"
                )
            if suspended_paid_period and effective <= values["paid_through"]:
                raise _ValueError(
                    "renewal predating a suspended paid boundary requires reconciliation"
                )
            if paid_through <= values["paid_through"]:
                raise _ValueError("renewal payment must advance the paid period")
            paid_period_gap = effective > (
                values["paid_through"] + _timedelta(days=1)
            )
            restoration_after_gap = (
                values["recovery_deadline_exclusive"] is not None
                and effective >= values["recovery_deadline_exclusive"]
            ) or paid_period_gap
            updated.update(
                state=_paid_state,
                entitlement_started_on=(
                    effective
                    if restoration_after_gap
                    else values["entitlement_started_on"]
                ),
                paid_through=paid_through,
                recovery_started_on=None,
                recovery_deadline_exclusive=None,
                last_effective_date=effective,
                processed_observations=processed,
            )
            return updated, True

        if kind == _renewal_failure_value:
            if values["state"] == _payment_recovery_state:
                updated.update(
                    state=(
                        _suspended_state
                        if effective >= values["recovery_deadline_exclusive"]
                        else _payment_recovery_state
                    ),
                    last_effective_date=effective,
                    processed_observations=processed,
                )
                return updated, True
            expired_paid_suspension = (
                values["state"] == _suspended_state
                and values["entitlement_started_on"] is not None
                and values["paid_through"] is not None
                and values["recovery_started_on"] is None
                and values["recovery_deadline_exclusive"] is None
            )
            if values["state"] != _paid_state and not expired_paid_suspension:
                raise _ValueError("failed renewal cannot create entitlement")
            if not values["renews_automatically"]:
                raise _ValueError(
                    "failed renewal after cancellation requires reconciliation"
                )
            if effective <= values["paid_through"]:
                raise _ValueError(
                    "failed renewal cannot truncate an already-paid period"
                )
            updated.update(
                state=_payment_recovery_state,
                recovery_started_on=effective,
                recovery_deadline_exclusive=effective
                + _timedelta(days=_recovery_days),
                last_effective_date=effective,
                processed_observations=processed,
            )
            return updated, True

        if kind == _cancellation_value:
            if values["state"] != _paid_state:
                raise _ValueError(
                    "cancellation outside paid state requires reconciliation"
                )
            if effective > values["paid_through"]:
                raise _ValueError("late cancellation requires reconciliation")
            updated.update(
                renews_automatically=False,
                last_effective_date=effective,
                processed_observations=processed,
            )
            return updated, True
        raise _ValueError("unsupported billing observation")

    def _candidate_from_values(values):
        return _pairs(_state_keys, _tuple(values[key] for key in _state_keys))

    def _validate_state_semantics(values):
        if (
            _type(values["contract_version"]) is not _str
            or values["contract_version"] != _contract_version
        ):
            raise _ValueError("unsupported entitlement candidate contract")
        if values["candidate_schema_version"] != _candidate_schema_version:
            raise _ValueError("unsupported entitlement candidate schema")
        if values["candidate_classification"] != _candidate_classification:
            raise _ValueError("entitlement candidate classification is invalid")
        for name in (
            "provider_observation_authenticated",
            "provider_provenance_authenticated",
            "provider_status_authority",
            "persistence_authority",
            "runtime_access_authority",
        ):
            if _type(values[name]) is not _bool or values[name] is not False:
                raise _ValueError(f"entitlement candidate must carry zero {name}")
        for name in ("owner_id", "billing_account_id", "subscription_id"):
            _validate_identifier(f"entitlement {name}", values[name])
        if _type(values["state"]) is not _str or values["state"] not in _state_values:
            raise _ValueError("entitlement candidate state is invalid")
        if _type(values["renews_automatically"]) is not _bool:
            raise _ValueError("entitlement candidate renewal flag is invalid")
        for name in (
            "entitlement_started_on",
            "paid_through",
            "recovery_started_on",
            "recovery_deadline_exclusive",
            "last_effective_date",
        ):
            if values[name] is not None and _type(values[name]) is not _date:
                raise _ValueError(f"entitlement candidate {name} is invalid")
        processed = values["processed_observations"]
        if _type(processed) is not _tuple:
            raise _ValueError("processed observations must be an exact tuple")
        replay = _empty_values(
            values["owner_id"],
            values["billing_account_id"],
            values["subscription_id"],
        )
        for fingerprint in processed:
            _validate_fingerprint(
                fingerprint,
                values["owner_id"],
                values["billing_account_id"],
                values["subscription_id"],
            )
            replay, _ = _apply_fingerprint(replay, fingerprint)

        if values == replay:
            return values
        # A time-boundary candidate records no new provider observation. The
        # only permitted semantic delta is the fail-closed state change.
        boundary = _dict(replay)
        if replay["state"] in (
            _paid_state,
            _payment_recovery_state,
        ):
            boundary["state"] = _suspended_state
            if values == boundary:
                return values
        raise _ValueError(
            "entitlement candidate is inconsistent with its event history"
        )

    def _validated_state(value):
        values = _parse_pairs(
            value, _state_keys, "entitlement decision candidate"
        )
        return _validate_state_semantics(values)

    def empty_entitlement(*, owner_id, billing_account_id, subscription_id):
        for name, value in (
            ("owner_id", owner_id),
            ("billing_account_id", billing_account_id),
            ("subscription_id", subscription_id),
        ):
            _validate_identifier(f"entitlement {name}", value)
        return _candidate_from_values(
            _empty_values(owner_id, billing_account_id, subscription_id)
        )

    def validate_entitlement_transition(value):
        return _candidate_from_values(_validated_state(value))

    def project_entitlement_transition(value):
        return _candidate_from_values(_validated_state(value))

    def copy_entitlement_transition(value):
        return _candidate_from_values(_validated_state(value))

    def apply_reconciled_observation(current, observation):
        values = _validated_state(current)
        fingerprint = _observation_fingerprint(observation)
        updated, changed = _apply_fingerprint(values, fingerprint)
        return _candidate_from_values(updated) if changed else current

    def _access_candidate(
        state, ordinary_access, reason, valid_from, valid_until
    ):
        return _pairs(
            _access_keys,
            (
                _candidate_schema_version,
                _candidate_classification,
                False,
                False,
                False,
                False,
                False,
                state,
                ordinary_access,
                reason,
                valid_from,
                valid_until,
            ),
        )

    def _history_at(values, as_of):
        historical = _empty_values(
            values["owner_id"],
            values["billing_account_id"],
            values["subscription_id"],
        )
        for fingerprint in values["processed_observations"]:
            if _date.fromisoformat(fingerprint[5]) <= as_of:
                historical, _ = _apply_fingerprint(historical, fingerprint)
        return historical

    def _materialised_values_at(values, as_of):
        expired = (
            values["state"] == _paid_state
            and as_of > values["paid_through"]
        ) or (
            values["state"] == _payment_recovery_state
            and as_of >= values["recovery_deadline_exclusive"]
        )
        if not expired:
            return values
        materialised = _dict(values)
        materialised["state"] = _suspended_state
        return materialised

    def project_ordinary_access(current, *, as_of):
        values = _validated_state(current)
        if _type(as_of) is not _date:
            raise _TypeError("an exact date is required")
        values = _materialised_values_at(_history_at(values, as_of), as_of)
        if values["state"] == _paid_state:
            allowed = (
                values["entitlement_started_on"]
                <= as_of
                <= values["paid_through"]
            )
            return _access_candidate(
                values["state"],
                allowed,
                "structural_paid_period_candidate"
                if allowed
                else "outside_structural_paid_period",
                values["entitlement_started_on"] if allowed else None,
                values["paid_through"] + _timedelta(days=1) if allowed else None,
            )
        if values["state"] == _payment_recovery_state:
            in_paid_period = (
                values["entitlement_started_on"]
                <= as_of
                <= values["paid_through"]
            )
            in_recovery_period = (
                values["recovery_started_on"]
                <= as_of
                < values["recovery_deadline_exclusive"]
            )
            allowed = in_paid_period or in_recovery_period
            return _access_candidate(
                values["state"],
                allowed,
                (
                    "structural_paid_period_candidate"
                    if in_paid_period
                    else "structural_bounded_payment_recovery_candidate"
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
        return _access_candidate(
            values["state"], False, "no_ordinary_paid_access", None, None
        )

    def validate_ordinary_access_candidate(value):
        values = _parse_pairs(
            value, _access_keys, "ordinary-access decision candidate"
        )
        if values["candidate_classification"] != _candidate_classification:
            raise _ValueError("ordinary-access candidate classification is invalid")
        if values["candidate_schema_version"] != _candidate_schema_version:
            raise _ValueError("unsupported ordinary-access candidate schema")
        for name in (
            "provider_observation_authenticated",
            "provider_provenance_authenticated",
            "provider_status_authority",
            "persistence_authority",
            "runtime_access_authority",
        ):
            if _type(values[name]) is not _bool or values[name] is not False:
                raise _ValueError(
                    f"ordinary-access candidate must carry zero {name}"
                )
        if (
            _type(values["state"]) is not _str
            or values["state"] not in _state_values
        ):
            raise _ValueError("ordinary-access candidate state is invalid")
        if _type(values["ordinary_access"]) is not _bool:
            raise _ValueError("ordinary-access candidate flag is invalid")
        if _type(values["reason"]) is not _str or not values["reason"]:
            raise _ValueError("ordinary-access candidate reason is invalid")
        for name in ("valid_from_inclusive", "valid_until_exclusive"):
            if values[name] is not None and _type(values[name]) is not _date:
                raise _ValueError(f"ordinary-access candidate {name} is invalid")
        if values["ordinary_access"]:
            if (
                values["valid_from_inclusive"] is None
                or values["valid_until_exclusive"] is None
                or values["valid_from_inclusive"]
                >= values["valid_until_exclusive"]
            ):
                raise _ValueError("ordinary-access candidate interval is invalid")
        elif (
            values["valid_from_inclusive"] is not None
            or values["valid_until_exclusive"] is not None
        ):
            raise _ValueError(
                "denied ordinary-access candidate must not carry an interval"
            )
        allowed_semantics = (
            (
                _paid_state,
                True,
                "structural_paid_period_candidate",
            ),
            (
                _paid_state,
                False,
                "outside_structural_paid_period",
            ),
            (
                _payment_recovery_state,
                True,
                "structural_paid_period_candidate",
            ),
            (
                _payment_recovery_state,
                True,
                "structural_bounded_payment_recovery_candidate",
            ),
            (
                _payment_recovery_state,
                False,
                "outside_paid_and_recovery_periods",
            ),
            (
                _no_entitlement_state,
                False,
                "no_ordinary_paid_access",
            ),
            (
                _suspended_state,
                False,
                "no_ordinary_paid_access",
            ),
        )
        semantic_key = (
            values["state"],
            values["ordinary_access"],
            values["reason"],
        )
        if semantic_key not in allowed_semantics:
            raise _ValueError("ordinary-access candidate semantics are contradictory")
        return _pairs(
            _access_keys, _tuple(values[key] for key in _access_keys)
        )

    def materialise_time_boundary(current, *, as_of):
        values = _validated_state(current)
        if _type(as_of) is not _date:
            raise _TypeError("an exact date is required")
        materialised = _materialised_values_at(values, as_of)
        if materialised is values:
            return current
        return _candidate_from_values(materialised)

    return (
        empty_entitlement,
        validate_entitlement_transition,
        project_entitlement_transition,
        copy_entitlement_transition,
        apply_reconciled_observation,
        project_ordinary_access,
        validate_ordinary_access_candidate,
        materialise_time_boundary,
    )


(
    empty_entitlement,
    validate_entitlement_transition,
    project_entitlement_transition,
    copy_entitlement_transition,
    apply_reconciled_observation,
    project_ordinary_access,
    validate_ordinary_access_candidate,
    materialise_time_boundary,
) = _build_entitlement_kernel()


__all__ = (
    "AccessProjection",
    "BillingObservationCandidate",
    "BillingObservationKind",
    "CANDIDATE_CLASSIFICATION",
    "CANDIDATE_SCHEMA_VERSION",
    "CONTRACT_VERSION",
    "EntitlementState",
    "EntitlementTransitionCandidate",
    "EntitlementTransitionProjection",
    "OrdinaryAccessDecisionCandidate",
    "RECOVERY_DAYS",
    "ReconciledBillingObservation",
    "apply_reconciled_observation",
    "copy_entitlement_transition",
    "empty_entitlement",
    "materialise_time_boundary",
    "project_entitlement_transition",
    "project_ordinary_access",
    "validate_entitlement_transition",
    "validate_ordinary_access_candidate",
)
