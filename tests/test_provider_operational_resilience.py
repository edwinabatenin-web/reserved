"""Focused tests for the provider-outage safe-degradation contract."""

import copy
import pickle
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from reserved.providers.operational_resilience import (
    CustomerAction,
    CustomerMessage,
    EvidenceRouteIdentity,
    EvidenceRouteStatus,
    OperationalResilienceError,
    OperationalState,
    OutageEvent,
    RecoveryObservation,
    begin_recovery,
    classify_outage,
    complete_recovery,
)

UTC = timezone.utc


def dt(**overrides):
    values = dict(year=2026, month=8, day=13, hour=10, minute=0, tzinfo=UTC)
    values.update(overrides)
    return datetime(**values)


def identity(provider="xero", route="invoices", owner_scope=None):
    return EvidenceRouteIdentity(provider, route, owner_scope)


def available_status(identity_value=None, *, observed=None, retrieved=None, verified=None):
    identity_value = identity_value or identity()
    observed = observed or dt(hour=9, minute=0)
    retrieved = retrieved or dt(hour=9, minute=5)
    verified = verified or dt(hour=9, minute=6)
    return EvidenceRouteStatus(
        identity=identity_value,
        state=OperationalState.AVAILABLE,
        observed_at=observed,
        retrieved_at=retrieved,
        last_verified_at=verified,
        required_fields_validated=True,
    )


# ── Invariant 1: degraded evidence is never current ───────────────────────────

def test_every_degraded_state_is_never_current_usable_evidence():
    cases = {
        OperationalState.TEMPORARILY_UNAVAILABLE: EvidenceRouteStatus(
            identity=identity(), state=OperationalState.TEMPORARILY_UNAVAILABLE
        ),
        OperationalState.AUTHORISATION_REQUIRED: EvidenceRouteStatus(
            identity=identity(), state=OperationalState.AUTHORISATION_REQUIRED
        ),
        OperationalState.SCHEMA_INCOMPATIBLE: EvidenceRouteStatus(
            identity=identity(), state=OperationalState.SCHEMA_INCOMPATIBLE
        ),
        OperationalState.EVIDENCE_INADEQUATE: EvidenceRouteStatus(
            identity=identity(), state=OperationalState.EVIDENCE_INADEQUATE
        ),
        OperationalState.STALE: EvidenceRouteStatus(
            identity=identity(),
            state=OperationalState.STALE,
            observed_at=dt(hour=9),
            retrieved_at=dt(hour=9, minute=5),
            last_verified_at=dt(hour=9, minute=6),
            required_fields_validated=True,
        ),
        OperationalState.RECOVERY_PENDING: EvidenceRouteStatus(
            identity=identity(),
            state=OperationalState.RECOVERY_PENDING,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
            required_fields_validated=False,
        ),
    }
    for state, status in cases.items():
        assert status.state is state
        assert not status.may_use_as_current
        assert status.customer_message_key is not CustomerMessage.AVAILABLE


def test_available_requires_validated_fields_and_complete_provenance():
    with pytest.raises(OperationalResilienceError):
        EvidenceRouteStatus(identity=identity(), state=OperationalState.AVAILABLE)
    with pytest.raises(OperationalResilienceError):
        EvidenceRouteStatus(
            identity=identity(),
            state=OperationalState.AVAILABLE,
            observed_at=dt(hour=9),
            retrieved_at=dt(hour=9, minute=5),
            last_verified_at=dt(hour=9, minute=6),
            required_fields_validated=False,
        )
    status = available_status()
    assert status.may_use_as_current


def test_missing_required_fields_event_degrades_not_current():
    status = classify_outage(
        identity=identity(),
        event=OutageEvent.REQUIRED_FIELDS_MISSING,
        occurred_at=dt(hour=10),
    )
    assert status.state is OperationalState.EVIDENCE_INADEQUATE
    assert not status.may_use_as_current
    assert status.customer_action is CustomerAction.PROVIDE_EVIDENCE


# ── Invariant 2 & 6: route isolation and cross-route substitution ─────────────

def test_outage_on_one_route_does_not_contaminate_another():
    route_a = identity(provider="xero", route="invoices")
    route_b = identity(provider="freeagent", route="invoices")

    degraded_a = classify_outage(
        identity=route_a, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    available_b = available_status(identity_value=route_b)

    assert degraded_a.state is OperationalState.TEMPORARILY_UNAVAILABLE
    assert available_b.state is OperationalState.AVAILABLE
    assert available_b.may_use_as_current
    assert degraded_a.identity != available_b.identity


def test_cross_provider_recovery_substitution_fails_closed():
    route_a = identity(provider="xero", route="invoices")
    route_b = identity(provider="freeagent", route="invoices")
    current = classify_outage(
        identity=route_a, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    observation = RecoveryObservation(
        identity=route_b,
        observed_at=dt(hour=11),
        retrieved_at=dt(hour=11, minute=1),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(current=current, observation=observation, now=dt(hour=12))


def test_cross_owner_recovery_substitution_fails_closed():
    route_a = identity(provider="xero", route="invoices", owner_scope="owner-a")
    route_b = identity(provider="xero", route="invoices", owner_scope="owner-b")
    current = classify_outage(
        identity=route_a, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    observation = RecoveryObservation(
        identity=route_b,
        observed_at=dt(hour=11),
        retrieved_at=dt(hour=11, minute=1),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(current=current, observation=observation, now=dt(hour=12))


# ── Invariant 3: last-known evidence is never silently promoted ───────────────

def test_stale_status_is_contextual_but_never_current():
    prior = available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                             verified=dt(hour=9, minute=6))
    stale = classify_outage(
        identity=prior.identity,
        event=OutageEvent.EVIDENCE_STALE,
        occurred_at=dt(hour=12),
        prior=prior,
    )
    assert stale.state is OperationalState.STALE
    assert stale.may_show_stale_context
    assert not stale.may_use_as_current
    assert stale.customer_action is CustomerAction.REFRESH
    assert stale.customer_message_key is CustomerMessage.INFORMATION_OUT_OF_DATE


def test_no_replacement_does_not_promote_stale_to_current():
    stale = classify_outage(
        identity=identity(),
        event=OutageEvent.EVIDENCE_STALE,
        occurred_at=dt(hour=12),
        prior=available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                               verified=dt(hour=9, minute=6)),
    )
    # There is no transition that turns STALE into AVAILABLE without a fresh
    # observation and explicit verification.
    with pytest.raises(OperationalResilienceError):
        complete_recovery(
            pending=stale,
            required_fields_validated=True,
            schema_compatible=True,
            verified_at=dt(hour=12, minute=1),
        )


# ── Invariant 4: recovery requires a fresh valid observation ──────────────────

def test_recovery_requires_a_fresh_observation_and_validated_fields():
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    observation = RecoveryObservation(
        identity=current.identity,
        observed_at=dt(hour=11),
        retrieved_at=dt(hour=11, minute=1),
    )
    pending = begin_recovery(current=current, observation=observation, now=dt(hour=12))

    # A status flag alone cannot recover.
    assert pending.state is OperationalState.RECOVERY_PENDING
    assert not pending.may_use_as_current

    recovered = complete_recovery(
        pending=pending,
        required_fields_validated=True,
        schema_compatible=True,
        verified_at=dt(hour=11, minute=2),
        now=dt(hour=12),
    )
    assert recovered.state is OperationalState.AVAILABLE
    assert recovered.may_use_as_current
    assert recovered.last_verified_at == dt(hour=11, minute=2)


def test_recovery_with_invalid_required_fields_degrades():
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=current.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    result = complete_recovery(
        pending=pending,
        required_fields_validated=False,
        schema_compatible=True,
        verified_at=dt(hour=11, minute=2),
        now=dt(hour=12),
    )
    assert result.state is OperationalState.EVIDENCE_INADEQUATE
    assert not result.may_use_as_current


def test_recovery_with_incompatible_schema_degrades():
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=current.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    result = complete_recovery(
        pending=pending,
        required_fields_validated=True,
        schema_compatible=False,
        verified_at=dt(hour=11, minute=2),
        now=dt(hour=12),
    )
    assert result.state is OperationalState.SCHEMA_INCOMPATIBLE
    assert not result.may_use_as_current


def test_recovery_with_regressive_retrieved_time_fails_closed():
    prior = available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                             verified=dt(hour=9, minute=6))
    current = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=10),
        prior=prior,
    )
    # Re-using the stale retrieval time (or an earlier one) cannot recover.
    observation = RecoveryObservation(
        identity=current.identity,
        observed_at=dt(hour=9),
        retrieved_at=dt(hour=9, minute=5),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(current=current, observation=observation, now=dt(hour=12))


def test_prior_available_outage_then_fresh_recovery_uses_transition_chronology():
    prior = available_status(
        observed=dt(hour=9),
        retrieved=dt(hour=9, minute=5),
        verified=dt(hour=9, minute=6),
    )
    outage = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=10),
        prior=prior,
    )
    pending = begin_recovery(
        current=outage,
        observation=RecoveryObservation(
            identity=outage.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    recovered = complete_recovery(
        pending=pending,
        required_fields_validated=True,
        schema_compatible=True,
        verified_at=dt(hour=11, minute=2),
        now=dt(hour=12),
    )

    assert outage.last_transition_at == dt(hour=10)
    assert pending.last_verified_at == prior.last_verified_at
    assert pending.last_transition_at == outage.last_transition_at
    assert recovered.state is OperationalState.AVAILABLE
    assert recovered.may_use_as_current


def test_begin_recovery_rejects_available_and_directly_forged_pending_sources():
    fresh = RecoveryObservation(
        identity=identity(),
        observed_at=dt(hour=11),
        retrieved_at=dt(hour=11, minute=1),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(current=available_status(), observation=fresh, now=dt(hour=12))

    forged = EvidenceRouteStatus(
        identity=identity(),
        state=OperationalState.RECOVERY_PENDING,
        observed_at=dt(hour=10),
        retrieved_at=dt(hour=10, minute=1),
        last_transition_at=dt(hour=9),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(
            current=forged,
            observation=RecoveryObservation(
                identity=forged.identity,
                observed_at=dt(hour=11),
                retrieved_at=dt(hour=11, minute=1),
            ),
            now=dt(hour=12),
        )


def test_forged_pending_cannot_be_laundered_through_outage_and_recovery():
    forged = EvidenceRouteStatus(
        identity=identity(),
        state=OperationalState.RECOVERY_PENDING,
        observed_at=dt(hour=10),
        retrieved_at=dt(hour=10, minute=1),
        last_transition_at=dt(hour=9),
    )
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=forged.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=11),
            prior=forged,
        )


@pytest.mark.parametrize(
    "occurred_at",
    (dt(hour=10, minute=30), dt(hour=11, minute=1)),
)
def test_outage_cannot_overwrite_newer_or_equal_authentic_pending_retrieval(
    occurred_at,
):
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=current.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )

    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=pending.identity,
            event=OutageEvent.SCHEMA_INCOMPATIBLE,
            occurred_at=occurred_at,
            prior=pending,
        )


@pytest.mark.parametrize("observed", (dt(hour=8), dt(hour=9)))
def test_fresh_retrieval_cannot_rehabilitate_regressive_or_equal_source_fact(observed):
    prior = available_status(
        observed=dt(hour=9),
        retrieved=dt(hour=9, minute=5),
        verified=dt(hour=9, minute=6),
    )
    outage = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=10),
        prior=prior,
    )
    assert outage.last_accepted_observed_at == dt(hour=9)
    with pytest.raises(OperationalResilienceError):
        begin_recovery(
            current=outage,
            observation=RecoveryObservation(
                identity=outage.identity,
                observed_at=observed,
                retrieved_at=dt(hour=11),
            ),
            now=dt(hour=12),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("identity", EvidenceRouteIdentity("freeagent", "invoices", "owner-a")),
        ("identity", EvidenceRouteIdentity("xero", "invoices", "owner-b")),
        ("observed_at", dt(hour=10, minute=30)),
        ("retrieved_at", dt(hour=11, minute=30)),
    ),
)
def test_direct_pending_mutation_cannot_promote_cross_route_or_changed_observation(
    field, value
):
    route = identity(owner_scope="owner-a")
    current = classify_outage(
        identity=route, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=route,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    object.__setattr__(pending, field, value)

    with pytest.raises(OperationalResilienceError):
        complete_recovery(
            pending=pending,
            required_fields_validated=True,
            schema_compatible=True,
            verified_at=dt(hour=11, minute=40),
            now=dt(hour=12),
        )


def test_direct_nested_identity_mutation_and_hostile_summary_fail_closed():
    route = identity(owner_scope="owner-a")
    current = classify_outage(
        identity=route, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=route,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    hostile = "freeagent\n<script>forged</script>"
    object.__setattr__(pending.identity, "provider", hostile)

    with pytest.raises(OperationalResilienceError) as caught:
        pending.evidence_summary()
    assert hostile not in str(caught.value)
    assert "<script>" not in str(caught.value)

    with pytest.raises(OperationalResilienceError):
        complete_recovery(
            pending=pending,
            required_fields_validated=True,
            schema_compatible=True,
            verified_at=dt(hour=11, minute=2),
            now=dt(hour=12),
        )


def test_direct_status_forgery_cannot_create_available_summary():
    status = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    object.__setattr__(status, "state", OperationalState.AVAILABLE)
    object.__setattr__(status, "observed_at", dt(hour=9))
    object.__setattr__(status, "retrieved_at", dt(hour=9, minute=5))
    object.__setattr__(status, "last_verified_at", dt(hour=9, minute=6))
    object.__setattr__(status, "required_fields_validated", True)

    with pytest.raises(OperationalResilienceError):
        status.evidence_summary()


def test_pending_recovery_authority_participates_in_equality_hash_copy_and_pickle():
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    authentic = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=current.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    unbound = EvidenceRouteStatus(
        identity=authentic.identity,
        state=authentic.state,
        observed_at=authentic.observed_at,
        retrieved_at=authentic.retrieved_at,
        last_verified_at=authentic.last_verified_at,
        required_fields_validated=authentic.required_fields_validated,
        last_transition_at=authentic.last_transition_at,
        last_accepted_observed_at=authentic.last_accepted_observed_at,
    )

    assert authentic != unbound
    assert hash(authentic) != hash(unbound)
    assert copy.copy(authentic) is authentic
    assert copy.deepcopy(authentic) is authentic
    with pytest.raises((OperationalResilienceError, TypeError, pickle.PicklingError)):
        pickle.dumps(authentic)
    with pytest.raises(OperationalResilienceError):
        complete_recovery(
            pending=unbound,
            required_fields_validated=True,
            schema_compatible=True,
            verified_at=dt(hour=11, minute=2),
            now=dt(hour=12),
        )

    # Copying the visible structural bindings with a made-up capability cannot
    # authenticate a directly constructed pending value.
    object.__setattr__(
        unbound,
        "_recovery_binding",
        (object(), authentic._recovery_binding[1], authentic._recovery_binding[2]),
    )
    assert authentic != unbound
    assert hash(authentic) != hash(unbound)
    with pytest.raises(OperationalResilienceError):
        complete_recovery(
            pending=unbound,
            required_fields_validated=True,
            schema_compatible=True,
            verified_at=dt(hour=11, minute=2),
            now=dt(hour=12),
        )
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=unbound.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=12, minute=1),
            prior=unbound,
        )


def test_recovery_with_future_timestamps_fails_closed():
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    observation = RecoveryObservation(
        identity=current.identity,
        observed_at=dt(hour=11),
        retrieved_at=dt(hour=11, minute=1),
    )
    with pytest.raises(OperationalResilienceError):
        begin_recovery(current=current, observation=observation, now=dt(hour=10, minute=30))


# ── Invariant 5: late/repeated outage events cannot overwrite verified state ──

def test_late_outage_event_cannot_overwrite_newer_verified_state():
    prior = available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                             verified=dt(hour=10))
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=prior.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=9, minute=59),
            prior=prior,
        )


def test_repeated_outage_event_at_same_time_cannot_overwrite():
    prior = available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                             verified=dt(hour=10))
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=prior.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=10),
            prior=prior,
        )


def test_newer_outage_event_can_override_older_degraded_state():
    prior = available_status(observed=dt(hour=9), retrieved=dt(hour=9, minute=5),
                             verified=dt(hour=10))
    first = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=11),
        prior=prior,
    )
    second = classify_outage(
        identity=prior.identity,
        event=OutageEvent.SCHEMA_INCOMPATIBLE,
        occurred_at=dt(hour=12),
        prior=first,
    )
    assert first.state is OperationalState.TEMPORARILY_UNAVAILABLE
    assert second.state is OperationalState.SCHEMA_INCOMPATIBLE


def test_older_outage_after_newer_degraded_transition_fails_closed():
    prior = available_status(verified=dt(hour=10))
    newer = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=12),
        prior=prior,
    )
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=prior.identity,
            event=OutageEvent.SCHEMA_INCOMPATIBLE,
            occurred_at=dt(hour=11),
            prior=newer,
        )


def test_exact_duplicate_outage_after_degraded_transition_fails_closed():
    prior = available_status(verified=dt(hour=10))
    first = classify_outage(
        identity=prior.identity,
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(hour=12),
        prior=prior,
    )
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=prior.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=12),
            prior=first,
        )


@pytest.mark.parametrize(
    ("required_fields_validated", "schema_compatible", "expected_state"),
    (
        (True, False, OperationalState.SCHEMA_INCOMPATIBLE),
        (False, True, OperationalState.EVIDENCE_INADEQUATE),
    ),
)
def test_failed_recovery_decision_advances_transition_watermark(
    required_fields_validated, schema_compatible, expected_state
):
    current = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(hour=10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=current.identity,
            observed_at=dt(hour=11),
            retrieved_at=dt(hour=11, minute=1),
        ),
        now=dt(hour=12),
    )
    failed = complete_recovery(
        pending=pending,
        required_fields_validated=required_fields_validated,
        schema_compatible=schema_compatible,
        verified_at=dt(hour=11, minute=2),
        now=dt(hour=12),
    )
    assert failed.state is expected_state
    assert failed.last_transition_at == dt(hour=11, minute=2)

    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=failed.identity,
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(hour=11, minute=1),
            prior=failed,
        )


# ── Invariant 7: unknown/malformed/adversarial input fails closed ─────────────

def test_unknown_state_and_event_fail_closed():
    with pytest.raises(OperationalResilienceError):
        EvidenceRouteStatus(identity=identity(), state="available")
    with pytest.raises(OperationalResilienceError):
        classify_outage(identity=identity(), event="timeout", occurred_at=dt())
    with pytest.raises(OperationalResilienceError):
        classify_outage(identity=identity(), event=OperationalState.AVAILABLE, occurred_at=dt())


def test_naive_and_wrong_type_timestamps_fail_closed():
    naive = datetime(2026, 8, 13, 10, 0)
    with pytest.raises(OperationalResilienceError):
        classify_outage(identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=naive)
    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=identity(), event=OutageEvent.TIMEOUT, occurred_at="2026-08-13T10:00:00Z"
        )


def test_hostile_strings_are_rejected_without_leaking():
    hostile = "provider\n<script>alert(1)</script>"
    try:
        EvidenceRouteIdentity(provider=hostile, route="invoices")
    except OperationalResilienceError as exc:
        assert hostile not in str(exc)
        assert "<script>" not in str(exc)
    else:
        raise AssertionError("hostile identity accepted")

    hostile_route = "route?id=1&x=../../etc"
    try:
        EvidenceRouteIdentity(provider="xero", route=hostile_route)
    except OperationalResilienceError as exc:
        assert hostile_route not in str(exc)
    else:
        raise AssertionError("hostile route accepted")


def test_subclasses_and_forged_types_fail_closed():
    class ForgedIdentity(EvidenceRouteIdentity):
        pass

    forged_identity = ForgedIdentity("xero", "invoices")
    with pytest.raises(OperationalResilienceError):
        EvidenceRouteStatus(identity=forged_identity, state=OperationalState.AVAILABLE)

    with pytest.raises(OperationalResilienceError):
        classify_outage(
            identity=forged_identity, event=OutageEvent.TIMEOUT, occurred_at=dt()
        )


def test_missing_and_extra_fields_fail_closed():
    with pytest.raises(TypeError):
        EvidenceRouteStatus(identity=identity())  # missing state
    with pytest.raises(TypeError):
        EvidenceRouteStatus(identity=identity(), state=OperationalState.AVAILABLE, bogus=1)


# ── Invariant 8: construction/copy/replace/hash/eq/serialisation ──────────────

def test_copy_and_deepcopy_preserve_value_and_invariants():
    status = available_status()
    for clone in (copy.copy(status), copy.deepcopy(status)):
        assert clone is status  # immutable value objects are returned as-is
        assert clone == status
        assert hash(clone) == hash(status)
        assert clone.may_use_as_current


def test_replace_revalidates_and_cannot_bypass_invariants():
    status = available_status()
    with pytest.raises(OperationalResilienceError):
        replace(status, state=OperationalState.AVAILABLE, required_fields_validated=False)
    with pytest.raises(OperationalResilienceError):
        replace(status, state=OperationalState.STALE, required_fields_validated=False)

    degraded = replace(
        status,
        state=OperationalState.TEMPORARILY_UNAVAILABLE,
        observed_at=None,
        retrieved_at=None,
        required_fields_validated=False,
    )
    assert not degraded.may_use_as_current


def test_equality_and_hashing_are_value_based():
    a = available_status()
    b = available_status()
    assert a == b
    assert hash(a) == hash(b)
    assert a != classify_outage(
        identity=a.identity, event=OutageEvent.TIMEOUT, occurred_at=dt(hour=12)
    )


def test_pickle_serialisation_is_explicitly_rejected():
    for value in (identity(), available_status()):
        with pytest.raises((OperationalResilienceError, TypeError, pickle.PicklingError)):
            pickle.dumps(value)


def test_evidence_summary_is_safe_and_one_way():
    summary = available_status().evidence_summary()
    assert summary["state"] == "available"
    assert summary["may_use_as_current"] is True
    assert summary["customer_message_key"] == "available"
    assert "observed_at" in summary


# ── Invariant 9: no network/credential/persistence surface ────────────────────

def test_module_is_network_and_persistence_inert():
    import inspect

    import reserved.providers.operational_resilience as module

    source = inspect.getsource(module)
    for forbidden in (
        "import requests",
        "import urllib",
        "import socket",
        "import sqlite3",
        "import os",
        "import pickle",
        "from os",
        "getenv",
        "environ",
    ):
        assert forbidden not in source
