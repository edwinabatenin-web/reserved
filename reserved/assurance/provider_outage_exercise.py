"""Deterministic, network-inert W9 provider-outage exercise evidence.

This module adds no I/O and performs no request-time I/O. It exercises the
reviewed S4A-D contracts with synthetic identities. The captured S4D renderer
loads its existing template at upstream module import; this package does not
claim transitive import-time filesystem absence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType
import weakref

from reserved.providers.operational_resilience import (
    EvidenceRouteIdentity, EvidenceRouteStatus, OperationalResilienceError,
    OperationalState, OutageEvent, RecoveryObservation, begin_recovery,
    classify_outage, complete_recovery,
)
from reserved.services.provider_outage_coordination import (
    ProviderOutageCoordination, ProviderOutageCoordinationRefusal,
    coordinate_provider_outage,
)
from reserved.services.provider_outage_coordination_presentation import (
    render_coordinated_provider_outage_status,
)


class ProviderOutageExerciseError(RuntimeError):
    """The bounded synthetic exercise failed closed."""


def _bind_exercise(
    *, identity_type=EvidenceRouteIdentity, status_type=EvidenceRouteStatus,
    state_type=OperationalState, event_type=OutageEvent,
    observation_type=RecoveryObservation, classify=classify_outage,
    begin=begin_recovery, complete=complete_recovery,
    coordinate=coordinate_provider_outage,
    coordination_type=ProviderOutageCoordination,
    refusal_type=ProviderOutageCoordinationRefusal,
    render=render_coordinated_provider_outage_status,
    upstream_error=OperationalResilienceError,
    error_type=ProviderOutageExerciseError, datetime_type=datetime,
    utc=timezone.utc, object_type=object, tuple_type=tuple, str_type=str,
    dict_type=dict, type_fn=type, id_fn=id, enumerate_fn=enumerate,
    range_fn=range, exception_type=Exception, weakref_ref=weakref.ref,
    mapping_proxy=MappingProxyType,
):
    constructor_authority = object_type()  # deliberately never stored on a result
    failure_message = "provider outage exercise failed closed"
    schema = "w9-s4e-provider-outage-exercise-v1"
    event_order = tuple_type(event_type)
    expected_cases = (
        ("timeout", "temporarily_unavailable", "retry_later", "temporarily_unavailable", "recovery_pending", "available"),
        ("temporarily_unavailable", "temporarily_unavailable", "retry_later", "temporarily_unavailable", "recovery_pending", "available"),
        ("authorisation_expired", "authorisation_required", "reconnect", "reconnect_required", "recovery_pending", "available"),
        ("authorisation_revoked", "authorisation_required", "reconnect", "reconnect_required", "recovery_pending", "available"),
        ("schema_incompatible", "schema_incompatible", "none", "data_format_changed", "recovery_pending", "available"),
        ("required_fields_missing", "evidence_inadequate", "provide_evidence", "information_incomplete", "recovery_pending", "available"),
        ("required_fields_invalid", "evidence_inadequate", "provide_evidence", "information_incomplete", "recovery_pending", "available"),
        ("evidence_stale", "stale", "refresh", "information_out_of_date", "recovery_pending", "available"),
    )
    expected_recovery = ("recovery_pending", "available")
    expected_aggregate = (
        "temporarily_unavailable", "temporarily_unavailable",
        "retry_later,reconnect",
    )
    expected_negative = (
        "stale_observation", "future_observation", "cross_owner",
        "subtyped_status", "mutated_status", "replayed_event",
        "duplicate_route",
    )
    expected_presentation = (
        '<section role="status" aria-live="polite" aria-atomic="true" '
        'aria-labelledby="coordinated-service-status-heading">\n'
        '  <h2 id="coordinated-service-status-heading">Information temporarily unavailable</h2>\n'
        '  <p>Some information is not currently available.</p>\n'
        '  <p>Follow each applicable step below.</p>\n'
        '  <ul aria-label="What you can do">\n'
        '    <li>Try again later.</li>\n'
        '    <li>Reconnect the affected account.</li>\n'
        '  </ul>\n'
        '</section>'
    )
    canonical = (
        schema, expected_cases, expected_recovery, expected_aggregate,
        expected_negative, True, True,
    )
    issued: dict[int, tuple[object, tuple]] = {}

    class ProviderOutageExerciseResult:
        """Opaque process-local handle to canonical issued evidence."""
        __slots__ = ("__weakref__",)

        def __new__(cls, *, _authority: object = None):
            if cls is not ProviderOutageExerciseResult or _authority is not constructor_authority:
                raise error_type(failure_message)
            return object_type.__new__(cls)

        def __repr__(self) -> str:
            try:
                validate_result(self)
                return "ProviderOutageExerciseResult([ISSUED])"
            except exception_type:
                return "ProviderOutageExerciseResult([INVALID])"

        def __copy__(self):
            validate_result(self)
            return self

        def __deepcopy__(self, memo: dict[int, object]):
            validate_result(self)
            memo[id_fn(self)] = self
            return self

        def __reduce_ex__(self, protocol: int):
            validate_result(self)
            raise error_type(failure_message)

    def validate_result(result: object) -> tuple:
        if type_fn(result) is not ProviderOutageExerciseResult:
            raise error_type(failure_message)
        entry = issued.get(id_fn(result))
        if entry is None or entry[0]() is not result or entry[1] is not canonical:
            raise error_type(failure_message)
        return canonical

    def as_provider_outage_exercise_summary(result: object) -> dict:
        """Return the fixed redacted projection of an issued opaque handle."""
        binding = validate_result(result)
        return mapping_proxy(dict_type(
            schema_version=binding[0], event_results=binding[1],
            recovery_states=binding[2], aggregate_projection=binding[3],
            negative_controls=binding[4], safe_presentation_verified=binding[5],
            all_invariants_verified=binding[6],
        ))

    def fail() -> None:
        raise error_type(failure_message)

    def run_provider_outage_exercise() -> ProviderOutageExerciseResult:
        """Run the fixed synthetic S4A-D exercise and issue opaque evidence."""
        try:
            owner = "synthetic-owner"
            first = identity_type("synthetic-a", "annual-evidence", owner)
            second = identity_type("synthetic-b", "business-evidence", owner)
            other = identity_type("synthetic-c", "annual-evidence", "other-owner")
            times = tuple_type(
                datetime_type(2026, 1, 1, 9, minute, tzinfo=utc)
                for minute in range_fn(9)
            )
            t0, t1, t2, t3, t4, t5, t6, t7, t8 = times
            base = status_type(
                identity=first, state=state_type.AVAILABLE, observed_at=t0,
                retrieved_at=t1, last_verified_at=t2,
                required_fields_validated=True, last_transition_at=t2,
            )
            actual_cases = []
            degraded_by_event = {}
            for index, event in enumerate_fn(event_order):
                degraded = classify(identity=first, event=event, occurred_at=t3, prior=base)
                if type_fn(degraded) is not status_type or degraded.may_use_as_current is not False:
                    fail()
                pending = begin(
                    current=degraded,
                    observation=observation_type(first, t4, t5), now=t6,
                )
                if type_fn(pending) is not status_type or pending.may_use_as_current is not False:
                    fail()
                recovered = complete(
                    pending=pending, required_fields_validated=True,
                    schema_compatible=True, verified_at=t6, now=t7,
                )
                if type_fn(recovered) is not status_type or recovered.may_use_as_current is not True:
                    fail()
                actual = (
                    event.value, degraded.state.value, degraded.customer_action.value,
                    degraded.customer_message_key.value, pending.state.value,
                    recovered.state.value,
                )
                if actual != expected_cases[index]:
                    fail()
                actual_cases.append(actual)
                degraded_by_event[event] = degraded
            if tuple_type(actual_cases) != expected_cases:
                fail()

            timeout = degraded_by_event[event_type.TIMEOUT]
            revoked = classify(
                identity=second, event=event_type.AUTHORISATION_REVOKED,
                occurred_at=t3,
            )
            aggregate = coordinate(routes=(timeout, revoked), owner=owner, as_of=t8)
            if type_fn(aggregate) is not coordination_type:
                fail()
            projection = aggregate.customer_projection()
            if type_fn(projection) is not dict_type:
                fail()
            actual_aggregate = (
                projection.get("aggregate_state"),
                projection.get("customer_message_key"),
                ",".join(projection.get("customer_actions", ())),
            )
            if actual_aggregate != expected_aggregate:
                fail()
            rendered = render(routes=(timeout, revoked), owner=owner, as_of=t8)
            if type_fn(rendered) is not str_type or rendered != expected_presentation:
                fail()

            try:
                begin(current=timeout, observation=observation_type(first, t0, t1), now=t8)
                fail()
            except upstream_error:
                pass
            try:
                begin(current=timeout, observation=observation_type(first, t7, t8), now=t6)
                fail()
            except upstream_error:
                pass
            foreign = classify(identity=other, event=event_type.TIMEOUT, occurred_at=t3)
            if type_fn(coordinate(routes=(timeout, foreign), owner=owner, as_of=t8)) is not refusal_type:
                fail()

            class StatusSubtype(status_type):
                pass
            subtyped = StatusSubtype(
                identity=first, state=state_type.TEMPORARILY_UNAVAILABLE,
                last_verified_at=t2, required_fields_validated=False,
                last_transition_at=t3, last_accepted_observed_at=t0,
            )
            if type_fn(coordinate(routes=(subtyped,), owner=owner, as_of=t8)) is not refusal_type:
                fail()
            mutated = classify(identity=first, event=event_type.TIMEOUT, occurred_at=t3, prior=base)
            object_type.__setattr__(mutated, "state", state_type.AVAILABLE)
            if type_fn(coordinate(routes=(mutated,), owner=owner, as_of=t8)) is not refusal_type:
                fail()
            try:
                classify(identity=first, event=event_type.TIMEOUT, occurred_at=t3, prior=timeout)
                fail()
            except upstream_error:
                pass
            if type_fn(coordinate(routes=(timeout, timeout), owner=owner, as_of=t8)) is not refusal_type:
                fail()

            result = ProviderOutageExerciseResult(_authority=constructor_authority)
            reference = weakref_ref(
                result, lambda _ref, key=id_fn(result): issued.pop(key, None)
            )
            issued[id_fn(result)] = (reference, canonical)
            validate_result(result)
            return result
        except error_type:
            raise
        except exception_type:
            raise error_type(failure_message) from None

    return ProviderOutageExerciseResult, run_provider_outage_exercise, as_provider_outage_exercise_summary


(
    ProviderOutageExerciseResult,
    run_provider_outage_exercise,
    as_provider_outage_exercise_summary,
) = _bind_exercise()

__all__ = (
    "ProviderOutageExerciseError", "ProviderOutageExerciseResult",
    "run_provider_outage_exercise", "as_provider_outage_exercise_summary",
)
