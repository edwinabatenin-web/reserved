"""Owner-bound, provider-neutral multi-route outage coordination.

This module combines several already-validated ``EvidenceRouteStatus`` values
for exactly one owner into one deterministic, customer-safe aggregate. It does
not retry, route, reconnect, monitor, persist or otherwise touch any provider;
it is pure at request time and performs no filesystem, network, credential,
persistence, logging or scheduling work.

The supported operation and every result/projection validator are bound at
import time so ordinary module/helper rebinding cannot alter validation or
projection. Message/action/precedence collaborators are snapshotted into
immutable closure-bound data; the result validator and projection surfaces use
those same captured collaborators, never mutable module globals.

Aggregate results are issued only by the bound coordinator. Issuance is a
process-local producer-held binding keyed to the exact live object and held
outside the consumer-writable dictionary, so direct construction,
reconstruction, field mutation or re-initialisation can never acquire issued
protocol identity. The aggregate carries an exact, order-independent per-route
status/provenance identity (including recovery source/observation provenance)
that is never exposed in the value-free customer projection.
"""

from __future__ import annotations

import re
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType

from reserved.providers.operational_resilience import (
    CustomerAction,
    CustomerMessage,
    EvidenceRouteIdentity,
    EvidenceRouteStatus,
    OperationalResilienceError,
    OperationalState,
)


_SAFE_OWNER = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")

# Documented deterministic aggregate precedence. The first state present among
# the accepted routes wins. ``AVAILABLE`` is last, so a single degraded, stale
# or recovery-pending route is never masked by another available route.
_STATE_PRECEDENCE = (
    OperationalState.TEMPORARILY_UNAVAILABLE,
    OperationalState.AUTHORISATION_REQUIRED,
    OperationalState.SCHEMA_INCOMPATIBLE,
    OperationalState.EVIDENCE_INADEQUATE,
    OperationalState.STALE,
    OperationalState.RECOVERY_PENDING,
    OperationalState.AVAILABLE,
)

# Mirrors the upstream one-route contract: each state has exactly one message
# and one action key.
_MESSAGE_BY_STATE = {
    OperationalState.AVAILABLE: CustomerMessage.AVAILABLE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerMessage.TEMPORARILY_UNAVAILABLE,
    OperationalState.AUTHORISATION_REQUIRED: CustomerMessage.RECONNECT_REQUIRED,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerMessage.DATA_FORMAT_CHANGED,
    OperationalState.EVIDENCE_INADEQUATE: CustomerMessage.INFORMATION_INCOMPLETE,
    OperationalState.STALE: CustomerMessage.INFORMATION_OUT_OF_DATE,
    OperationalState.RECOVERY_PENDING: CustomerMessage.RECOVERY_IN_PROGRESS,
}

_ACTION_BY_STATE = {
    OperationalState.AVAILABLE: CustomerAction.NONE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerAction.RETRY_LATER,
    OperationalState.AUTHORISATION_REQUIRED: CustomerAction.RECONNECT,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerAction.NONE,
    OperationalState.EVIDENCE_INADEQUATE: CustomerAction.PROVIDE_EVIDENCE,
    OperationalState.STALE: CustomerAction.REFRESH,
    OperationalState.RECOVERY_PENDING: CustomerAction.NONE,
}

# Canonical, input-order-independent ordering of the bounded action vocabulary.
_ACTION_ORDER = (
    CustomerAction.NONE,
    CustomerAction.RETRY_LATER,
    CustomerAction.RECONNECT,
    CustomerAction.PROVIDE_EVIDENCE,
    CustomerAction.REFRESH,
)


def _bind_coordinator(
    *,
    status_type: type = EvidenceRouteStatus,
    identity_type: type = EvidenceRouteIdentity,
    state_type: type = OperationalState,
    message_type: type = CustomerMessage,
    action_type: type = CustomerAction,
    error_type: type = OperationalResilienceError,
    datetime_type: type = datetime,
    safe_owner: re.Pattern = _SAFE_OWNER,
    state_precedence: tuple = _STATE_PRECEDENCE,
    message_by_state: dict = _MESSAGE_BY_STATE,
    action_by_state: dict = _ACTION_BY_STATE,
    action_order: tuple = _ACTION_ORDER,
    utc: object = timezone.utc,
    weakref_ref=weakref.ref,
):
    """Capture every collaborator before public module globals can be rebound.

    Mutable message/action mapping collaborators are snapshotted into immutable
    closure-bound views so later in-place mutation of the module globals cannot
    alter accepted semantics. The result class, refusal and the issuance
    registry are all created here so their validators and projections resolve
    the captured collaborators rather than mutable module globals.
    """

    message_by_state = MappingProxyType(dict(message_by_state))
    action_by_state = MappingProxyType(dict(action_by_state))
    state_precedence = tuple(state_precedence)
    action_order = tuple(action_order)

    safe_identifier_characters = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )

    def exact_identifier(value: object, *, nullable: bool = False) -> bool:
        if nullable and value is None:
            return True
        return (
            type(value) is str
            and 1 <= len(value) <= 160
            and all(character in safe_identifier_characters for character in value)
        )

    def exact_timestamp(value: object) -> bool:
        return value is None or type(value) is datetime_type

    # Pure structural validators for the immutable digest payloads. These use
    # only exact type/identity probes (no __eq__/__hash__ dispatch) so hostile
    # values can never run before the producer-held integrity check.
    def exact_status_binding_value(binding: object) -> bool:
        if type(binding) is not tuple or len(binding) != 8:
            return False
        if type(binding[0]) is not tuple or len(binding[0]) != 3:
            return False
        if not exact_identifier(binding[0][0]):
            return False
        if not exact_identifier(binding[0][1]):
            return False
        if not exact_identifier(binding[0][2], nullable=True):
            return False
        if type(binding[1]) is not state_type:
            return False
        if not all(exact_timestamp(binding[i]) for i in (2, 3, 4, 6, 7)):
            return False
        if type(binding[5]) is not bool:
            return False
        return True

    def exact_observation_binding_value(binding: object) -> bool:
        if type(binding) is not tuple or len(binding) != 3:
            return False
        if type(binding[0]) is not tuple or len(binding[0]) != 3:
            return False
        if not exact_identifier(binding[0][0]):
            return False
        if not exact_identifier(binding[0][1]):
            return False
        if not exact_identifier(binding[0][2], nullable=True):
            return False
        if not exact_timestamp(binding[1]):
            return False
        if not exact_timestamp(binding[2]):
            return False
        return True

    def exact_identity_binding(binding: object, identity: object) -> bool:
        if type(binding) is not tuple or len(binding) != 3:
            return False
        provider = object.__getattribute__(identity, "provider")
        route = object.__getattribute__(identity, "route")
        owner = object.__getattribute__(identity, "owner_scope")
        return (
            exact_identifier(provider)
            and exact_identifier(route)
            and exact_identifier(owner, nullable=True)
            and exact_identifier(binding[0])
            and exact_identifier(binding[1])
            and exact_identifier(binding[2], nullable=True)
            and binding[0] == provider
            and binding[1] == route
            and binding[2] == owner
        )

    def exact_status_binding(binding: object, identity: object) -> bool:
        if type(binding) is not tuple or len(binding) != 8:
            return False
        if not exact_identity_binding(binding[0], identity):
            return False
        if type(binding[1]) is not state_type:
            return False
        if not all(exact_timestamp(binding[index]) for index in (2, 3, 4, 6, 7)):
            return False
        if type(binding[5]) is not bool:
            return False
        identity_binding = object.__getattribute__(identity, "_identity_binding")
        if not exact_identity_binding(identity_binding, identity):
            return False
        return all(binding[0][index] == identity_binding[index] for index in range(3))

    def exact_current_status(status: object, identity: object, state: object) -> bool:
        binding = object.__getattribute__(status, "_status_binding")
        fields = (
            object.__getattribute__(status, "observed_at"),
            object.__getattribute__(status, "retrieved_at"),
            object.__getattribute__(status, "last_verified_at"),
            object.__getattribute__(status, "required_fields_validated"),
            object.__getattribute__(status, "last_transition_at"),
            object.__getattribute__(status, "last_accepted_observed_at"),
        )
        if not exact_status_binding(binding, identity):
            return False
        return (
            binding[1] is state
            and all(exact_timestamp(fields[index]) for index in (0, 1, 2, 4, 5))
            and type(fields[3]) is bool
            and all(binding[index] == fields[index - 2] for index in (2, 3, 4, 6, 7))
            and binding[5] is fields[3]
        )

    def exact_recovery_binding(status: object, identity: object) -> bool:
        recovery = object.__getattribute__(status, "_recovery_binding")
        if type(recovery) is not tuple or len(recovery) != 3:
            return False
        current, observation = recovery[1], recovery[2]
        if not exact_status_binding(current, identity):
            return False
        if type(observation) is not tuple or len(observation) != 3:
            return False
        if not exact_identity_binding(observation[0], identity):
            return False
        if type(observation[1]) is not datetime_type or type(observation[2]) is not datetime_type:
            return False
        identity_binding = object.__getattribute__(identity, "_identity_binding")
        observed = object.__getattribute__(status, "observed_at")
        retrieved = object.__getattribute__(status, "retrieved_at")
        verified = object.__getattribute__(status, "last_verified_at")
        transitioned = object.__getattribute__(status, "last_transition_at")
        accepted = object.__getattribute__(status, "last_accepted_observed_at")
        return (
            all(left == right for left, right in zip(current[0], identity_binding))
            and all(left == right for left, right in zip(observation[0], identity_binding))
            and observation[1] == observed
            and observation[2] == retrieved
            and current[4] == verified
            and current[6] == transitioned
            and current[7] == accepted
        )

    def exact_as_of(value: object) -> object:
        if value is None:
            return datetime_type.now(utc)
        if type(value) is not datetime_type:
            return None
        try:
            offset = value.utcoffset()
        except Exception:
            return None
        if offset is None:
            return None
        try:
            return value.astimezone(utc)
        except Exception:
            return None

    # Process-local producer-held issuance registry. ``id(live result)`` maps to
    # the exact live object (via a weak reference) and the immutable binding the
    # coordinator produced for it. The object's own dictionary never holds an
    # issuance authority, so copying or re-initialising fields cannot transfer
    # validity. Entries are removed when the live result is collected.
    issued: dict[int, tuple[weakref.ReferenceType, tuple]] = {}

    @dataclass(frozen=True, repr=False, eq=False)
    class ProviderOutageCoordination:
        """Immutable deterministic multi-route aggregate.

        Issued only by the bound coordinator. Only ``customer_projection`` is a
        public customer-safe surface. Every identifier, digest, timestamp and
        provenance value stays private and is never serialised into the
        projection or ``repr``.
        """

        _aggregate_state: object
        _aggregate_message: object
        _actions: tuple
        _route_digest: frozenset
        _as_of: object

        def __post_init__(self) -> None:
            # Issuance is producer-held and lives outside this dictionary;
            # re-initialisation can therefore never confer validity.
            return None

        def _fields(self) -> tuple:
            return (
                object.__getattribute__(self, "_aggregate_state"),
                object.__getattribute__(self, "_aggregate_message"),
                object.__getattribute__(self, "_actions"),
                object.__getattribute__(self, "_route_digest"),
                object.__getattribute__(self, "_as_of"),
            )

        def _value_fields(self) -> tuple:
            # Value equality/hash intentionally excludes the coordination-time
            # ``_as_of`` boundary, matching the original compare=False semantics:
            # two coordinations of identical route evidence are value-equal even
            # if their wall-clock coordination times differ.
            return (
                object.__getattribute__(self, "_aggregate_state"),
                object.__getattribute__(self, "_aggregate_message"),
                object.__getattribute__(self, "_actions"),
                object.__getattribute__(self, "_route_digest"),
            )

        def _assert_integrity(self) -> None:
            if type(self) is not ProviderOutageCoordination:
                raise error_type(
                    "coordination result must be a ProviderOutageCoordination"
                )
            try:
                state, message, actions, digest, as_of = self._fields()
            except AttributeError:
                raise error_type("coordination result is incomplete") from None
            if type(state) is not state_type:
                raise error_type("coordination result state is invalid")
            if type(message) is not message_type:
                raise error_type("coordination result message is invalid")
            if type(actions) is not tuple:
                raise error_type("coordination result actions are invalid")
            if any(type(action) is not action_type for action in actions):
                raise error_type("coordination result actions are invalid")
            if type(digest) is not frozenset:
                raise error_type("coordination result digest is invalid")
            for entry in digest:
                if type(entry) is not tuple or len(entry) != 2:
                    raise error_type("coordination result digest is invalid")
                if not exact_status_binding_value(entry[0]):
                    raise error_type("coordination result digest is invalid")
                if entry[1] is not None:
                    if type(entry[1]) is not tuple or len(entry[1]) != 2:
                        raise error_type("coordination result digest is invalid")
                    if not exact_status_binding_value(entry[1][0]):
                        raise error_type("coordination result digest is invalid")
                    if not exact_observation_binding_value(entry[1][1]):
                        raise error_type("coordination result digest is invalid")
            if type(as_of) is not datetime_type or as_of.utcoffset() is None:
                raise error_type("coordination result as_of is invalid")

            entry = issued.get(id(self))
            if entry is None or entry[0]() is not self or entry[1] != (state, message, actions, digest, as_of):
                raise error_type("coordination result is not coordinator-issued")

        def customer_projection(self) -> dict:
            """Return a value-free, bounded-vocabulary projection.

            No owner, provider/route identifier, timestamp, URL, payload, action
            target, credential, secret or exception value is exposed here.
            """
            self._assert_integrity()
            return {
                "aggregate_state": object.__getattribute__(
                    self, "_aggregate_state"
                ).value,
                "customer_message_key": object.__getattribute__(
                    self, "_aggregate_message"
                ).value,
                "customer_actions": tuple(
                    action.value
                    for action in object.__getattribute__(self, "_actions")
                ),
            }

        def __repr__(self) -> str:
            try:
                self._assert_integrity()
                state = object.__getattribute__(self, "_aggregate_state").value
                message = object.__getattribute__(self, "_aggregate_message").value
                actions = tuple(
                    action.value
                    for action in object.__getattribute__(self, "_actions")
                )
                return (
                    "ProviderOutageCoordination("
                    f"aggregate_state={state!r}, "
                    f"customer_message_key={message!r}, "
                    f"customer_actions={actions!r})"
                )
            except Exception:
                return "ProviderOutageCoordination([INVALID])"

        def __eq__(self, other: object) -> object:
            self._assert_integrity()
            if type(other) is not ProviderOutageCoordination:
                return False
            other._assert_integrity()
            return self._value_fields() == other._value_fields()

        def __hash__(self) -> int:
            self._assert_integrity()
            return hash(self._value_fields())

        def __copy__(self) -> "ProviderOutageCoordination":
            self._assert_integrity()
            return self

        def __deepcopy__(self, memo: dict[int, object]) -> "ProviderOutageCoordination":
            self._assert_integrity()
            memo[id(self)] = self
            return self

        def __reduce__(self) -> object:
            raise error_type(
                "coordination results are intentionally not serialisable"
            )

    class ProviderOutageCoordinationRefusal:
        """Categorical value-free refusal; never exposes why input was untrusted."""

        _instance: "ProviderOutageCoordinationRefusal | None" = None

        def __new__(cls) -> "ProviderOutageCoordinationRefusal":
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

        def customer_projection(self) -> dict:
            return {"refused": True}

        def __repr__(self) -> str:
            return "ProviderOutageCoordinationRefusal()"

        def __copy__(self) -> "ProviderOutageCoordinationRefusal":
            return self

        def __deepcopy__(
            self, memo: dict[int, object]
        ) -> "ProviderOutageCoordinationRefusal":
            memo[id(self)] = self
            return self

        def __reduce__(self) -> object:
            raise error_type(
                "coordination refusals are intentionally not serialisable"
            )

    refusal = ProviderOutageCoordinationRefusal()

    def coordinate_provider_outage(
        *, routes: tuple, owner: str, as_of: object = None
    ) -> object:
        """Combine exact routes for one exact owner into one safe aggregate.

        Returns ``ProviderOutageCoordination`` on success or the categorical
        value-free refusal when the input cannot be trusted or any route carries
        a timestamp later than the coordination ``as_of`` boundary.
        """
        try:
            if type(owner) is not str or safe_owner.fullmatch(owner) is None:
                return refusal
            if type(routes) is not tuple:
                return refusal
            if not routes:
                return refusal

            reference_as_of = exact_as_of(as_of)
            if reference_as_of is None:
                return refusal

            seen = set()
            digest_entries = []
            present_states = set()

            for status in routes:
                if type(status) is not status_type:
                    return refusal
                identity = object.__getattribute__(status, "identity")
                if type(identity) is not identity_type:
                    return refusal
                identity_binding = object.__getattribute__(identity, "_identity_binding")
                if not exact_identity_binding(identity_binding, identity):
                    return refusal
                bound_owner = object.__getattribute__(identity, "owner_scope")
                if not exact_identifier(bound_owner) or bound_owner != owner:
                    return refusal
                state = object.__getattribute__(status, "state")
                if type(state) is not state_type:
                    return refusal
                if not exact_current_status(status, identity, state):
                    return refusal
                if state is state_type.RECOVERY_PENDING:
                    if not exact_recovery_binding(status, identity):
                        return refusal
                    status_type._assert_recovery_binding(status)
                else:
                    status_type._assert_integrity(status)

                for field_name in (
                    "observed_at",
                    "retrieved_at",
                    "last_verified_at",
                    "last_transition_at",
                    "last_accepted_observed_at",
                ):
                    timestamp = object.__getattribute__(status, field_name)
                    if timestamp is not None and timestamp > reference_as_of:
                        return refusal

                provider = object.__getattribute__(identity, "provider")
                route = object.__getattribute__(identity, "route")
                key = (provider, route)
                if key in seen:
                    return refusal
                seen.add(key)

                status_binding = object.__getattribute__(status, "_status_binding")
                if state is state_type.RECOVERY_PENDING:
                    recovery_binding = object.__getattribute__(
                        status, "_recovery_binding"
                    )
                    recovery_provenance = (recovery_binding[1], recovery_binding[2])
                else:
                    recovery_provenance = None
                digest_entries.append((status_binding, recovery_provenance))
                present_states.add(state)

            aggregate_state = next(
                state for state in state_precedence if state in present_states
            )
            aggregate_message = message_by_state[aggregate_state]
            actions_present = {action_by_state[state] for state in present_states}
            actions_present.discard(action_type.NONE)
            actions = tuple(
                action for action in action_order if action in actions_present
            )

            result = ProviderOutageCoordination(
                aggregate_state,
                aggregate_message,
                actions,
                frozenset(digest_entries),
                reference_as_of,
            )
            binding = result._fields()
            reference = weakref_ref(
                result, lambda _ref, key=id(result): issued.pop(key, None)
            )
            issued[id(result)] = (reference, binding)
            return result
        except Exception:
            return refusal

    return (
        ProviderOutageCoordination,
        ProviderOutageCoordinationRefusal,
        refusal,
        coordinate_provider_outage,
    )


(
    ProviderOutageCoordination,
    ProviderOutageCoordinationRefusal,
    REFUSAL,
    coordinate_provider_outage,
) = _bind_coordinator()


__all__ = (
    "coordinate_provider_outage",
    "ProviderOutageCoordination",
    "ProviderOutageCoordinationRefusal",
)
