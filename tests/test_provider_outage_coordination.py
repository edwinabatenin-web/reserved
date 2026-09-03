"""Focused adversarial tests for multi-provider outage coordination."""

from __future__ import annotations

import copy
import pickle
from datetime import datetime, timezone

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
from reserved.services.provider_outage_coordination import (
    REFUSAL,
    ProviderOutageCoordination,
    ProviderOutageCoordinationRefusal,
    coordinate_provider_outage,
)

UTC = timezone.utc
OWNER = "owner-a"


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 13, hour, minute, tzinfo=UTC)


def identity(
    provider: str = "xero", route: str = "invoices", owner_scope: str | None = OWNER
) -> EvidenceRouteIdentity:
    return EvidenceRouteIdentity(provider, route, owner_scope)


def available_status(
    identity_value: EvidenceRouteIdentity | None = None,
    *,
    observed: datetime | None = None,
    retrieved: datetime | None = None,
    verified: datetime | None = None,
) -> EvidenceRouteStatus:
    identity_value = identity_value or identity()
    observed = observed or dt(9)
    retrieved = retrieved or dt(9, 5)
    verified = verified or dt(9, 6)
    return EvidenceRouteStatus(
        identity=identity_value,
        state=OperationalState.AVAILABLE,
        observed_at=observed,
        retrieved_at=retrieved,
        last_verified_at=verified,
        required_fields_validated=True,
    )


def degraded_status(
    state: OperationalState,
    identity_value: EvidenceRouteIdentity | None = None,
) -> EvidenceRouteStatus:
    identity_value = identity_value or identity()
    if state is OperationalState.TEMPORARILY_UNAVAILABLE:
        return classify_outage(
            identity=identity_value, event=OutageEvent.TIMEOUT, occurred_at=dt(12)
        )
    if state is OperationalState.AUTHORISATION_REQUIRED:
        return classify_outage(
            identity=identity_value,
            event=OutageEvent.AUTHORISATION_EXPIRED,
            occurred_at=dt(12),
        )
    if state is OperationalState.SCHEMA_INCOMPATIBLE:
        return classify_outage(
            identity=identity_value,
            event=OutageEvent.SCHEMA_INCOMPATIBLE,
            occurred_at=dt(12),
        )
    if state is OperationalState.EVIDENCE_INADEQUATE:
        return classify_outage(
            identity=identity_value,
            event=OutageEvent.REQUIRED_FIELDS_MISSING,
            occurred_at=dt(12),
        )
    if state is OperationalState.STALE:
        return classify_outage(
            identity=identity_value,
            event=OutageEvent.EVIDENCE_STALE,
            occurred_at=dt(12),
            prior=available_status(identity_value),
        )
    if state is OperationalState.RECOVERY_PENDING:
        current = classify_outage(
            identity=identity_value, event=OutageEvent.TIMEOUT, occurred_at=dt(10)
        )
        return begin_recovery(
            current=current,
            observation=RecoveryObservation(
                identity=identity_value, observed_at=dt(11), retrieved_at=dt(11, 1)
            ),
            now=dt(12),
        )
    raise ValueError(f"unexpected state {state!r}")


MESSAGE_BY_STATE = {
    OperationalState.AVAILABLE: CustomerMessage.AVAILABLE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerMessage.TEMPORARILY_UNAVAILABLE,
    OperationalState.AUTHORISATION_REQUIRED: CustomerMessage.RECONNECT_REQUIRED,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerMessage.DATA_FORMAT_CHANGED,
    OperationalState.EVIDENCE_INADEQUATE: CustomerMessage.INFORMATION_INCOMPLETE,
    OperationalState.STALE: CustomerMessage.INFORMATION_OUT_OF_DATE,
    OperationalState.RECOVERY_PENDING: CustomerMessage.RECOVERY_IN_PROGRESS,
}

ACTION_BY_STATE = {
    OperationalState.AVAILABLE: CustomerAction.NONE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerAction.RETRY_LATER,
    OperationalState.AUTHORISATION_REQUIRED: CustomerAction.RECONNECT,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerAction.NONE,
    OperationalState.EVIDENCE_INADEQUATE: CustomerAction.PROVIDE_EVIDENCE,
    OperationalState.STALE: CustomerAction.REFRESH,
    OperationalState.RECOVERY_PENDING: CustomerAction.NONE,
}


def expected_actions(state: OperationalState) -> tuple[str, ...]:
    action = ACTION_BY_STATE[state]
    return () if action is CustomerAction.NONE else (action.value,)


# ── 1-7: one available route plus each individual degraded state ──────────────

@pytest.mark.parametrize(
    "state",
    (
        OperationalState.TEMPORARILY_UNAVAILABLE,
        OperationalState.AUTHORISATION_REQUIRED,
        OperationalState.SCHEMA_INCOMPATIBLE,
        OperationalState.EVIDENCE_INADEQUATE,
        OperationalState.STALE,
        OperationalState.RECOVERY_PENDING,
    ),
)
def test_available_route_never_masks_a_single_degraded_state(state):
    available = available_status()  # xero/invoices
    degraded = degraded_status(state, identity("freeagent", "invoices"))
    result = coordinate_provider_outage(routes=(available, degraded), owner=OWNER)

    assert isinstance(result, ProviderOutageCoordination)
    projection = result.customer_projection()
    assert projection["aggregate_state"] == state.value
    assert projection["customer_message_key"] == MESSAGE_BY_STATE[state].value
    assert projection["customer_actions"] == expected_actions(state)


def test_mixed_available_and_timeout_is_unavailable_with_retry():
    available = available_status()
    timeout = classify_outage(
        identity=identity("freeagent", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(12),
    )
    projection = coordinate_provider_outage(
        routes=(available, timeout), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "temporarily_unavailable"
    assert projection["customer_message_key"] == "temporarily_unavailable"
    assert projection["customer_actions"] == ("retry_later",)


@pytest.mark.parametrize(
    "event", (OutageEvent.AUTHORISATION_EXPIRED, OutageEvent.AUTHORISATION_REVOKED)
)
def test_mixed_available_and_authorisation_requires_reconnect(event):
    available = available_status()
    auth = classify_outage(
        identity=identity("freeagent", "invoices"), event=event, occurred_at=dt(12)
    )
    projection = coordinate_provider_outage(
        routes=(available, auth), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "authorisation_required"
    assert projection["customer_message_key"] == "reconnect_required"
    assert projection["customer_actions"] == ("reconnect",)


def test_mixed_available_and_schema_incompatible_is_not_current():
    available = available_status()
    schema = degraded_status(OperationalState.SCHEMA_INCOMPATIBLE, identity("freeagent", "invoices"))
    projection = coordinate_provider_outage(
        routes=(available, schema), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "schema_incompatible"
    assert projection["customer_message_key"] == "data_format_changed"
    assert projection["customer_actions"] == ()


def test_mixed_available_and_inadequate_evidence_requires_provision():
    available = available_status()
    evidence = degraded_status(OperationalState.EVIDENCE_INADEQUATE, identity("freeagent", "invoices"))
    projection = coordinate_provider_outage(
        routes=(available, evidence), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "evidence_inadequate"
    assert projection["customer_message_key"] == "information_incomplete"
    assert projection["customer_actions"] == ("provide_evidence",)


def test_mixed_available_and_stale_requires_refresh():
    available = available_status()
    stale = degraded_status(OperationalState.STALE, identity("freeagent", "invoices"))
    projection = coordinate_provider_outage(
        routes=(available, stale), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "stale"
    assert projection["customer_message_key"] == "information_out_of_date"
    assert projection["customer_actions"] == ("refresh",)


def test_mixed_available_and_recovery_pending_is_non_current():
    available = available_status()
    pending = degraded_status(OperationalState.RECOVERY_PENDING, identity("freeagent", "invoices"))
    projection = coordinate_provider_outage(
        routes=(available, pending), owner=OWNER
    ).customer_projection()
    assert projection["aggregate_state"] == "recovery_pending"
    assert projection["customer_message_key"] == "recovery_in_progress"
    assert projection["customer_actions"] == ()


# ── 8: multiple degraded states with deterministic precedence/action set ──────

def test_multiple_degraded_states_use_documented_precedence_and_distinct_actions():
    routes = (
        available_status(),
        classify_outage(
            identity=identity("freeagent", "invoices"),
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(12),
        ),
        classify_outage(
            identity=identity("quickbooks", "invoices"),
            event=OutageEvent.AUTHORISATION_EXPIRED,
            occurred_at=dt(12),
        ),
        degraded_status(OperationalState.STALE, identity("xero", "contacts")),
    )
    projection = coordinate_provider_outage(routes=routes, owner=OWNER).customer_projection()
    assert projection["aggregate_state"] == "temporarily_unavailable"
    assert projection["customer_message_key"] == "temporarily_unavailable"
    assert projection["customer_actions"] == ("retry_later", "reconnect", "refresh")


# ── 9: one failed route is never hidden by another available route ────────────

def test_one_failed_route_is_never_hidden_by_available_routes():
    routes = (
        available_status(identity("xero", "invoices")),
        available_status(identity("xero", "contacts")),
        classify_outage(
            identity=identity("freeagent", "invoices"),
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(12),
        ),
    )
    projection = coordinate_provider_outage(routes=routes, owner=OWNER).customer_projection()
    assert projection["aggregate_state"] != "available"
    assert projection["aggregate_state"] == "temporarily_unavailable"


# ── 10: recovery-pending stays non-current and only becomes available upstream ─

def test_recovery_pending_becomes_available_only_after_complete_recovery():
    route = identity("freeagent", "invoices")
    current = classify_outage(
        identity=route, event=OutageEvent.TIMEOUT, occurred_at=dt(10)
    )
    pending = begin_recovery(
        current=current,
        observation=RecoveryObservation(
            identity=route, observed_at=dt(11), retrieved_at=dt(11, 1)
        ),
        now=dt(12),
    )
    available = available_status()

    pending_projection = coordinate_provider_outage(
        routes=(available, pending), owner=OWNER
    ).customer_projection()
    assert pending_projection["aggregate_state"] == "recovery_pending"
    assert pending_projection["customer_actions"] == ()

    recovered = complete_recovery(
        pending=pending,
        required_fields_validated=True,
        schema_compatible=True,
        verified_at=dt(11, 2),
        now=dt(12),
    )
    assert recovered.state is OperationalState.AVAILABLE

    recovered_projection = coordinate_provider_outage(
        routes=(available, recovered), owner=OWNER
    ).customer_projection()
    assert recovered_projection["aggregate_state"] == "available"
    assert recovered_projection["customer_message_key"] == "available"
    assert recovered_projection["customer_actions"] == ()


# ── 11: deterministic ordering and stable result identity ─────────────────────

def test_deterministic_ordering_and_stable_identity_irrespective_of_input_order():
    routes = (
        available_status(identity("xero", "invoices")),
        classify_outage(
            identity=identity("freeagent", "invoices"),
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(12),
        ),
        classify_outage(
            identity=identity("quickbooks", "invoices"),
            event=OutageEvent.AUTHORISATION_EXPIRED,
            occurred_at=dt(12),
        ),
    )
    forward = coordinate_provider_outage(routes=routes, owner=OWNER)
    reverse = coordinate_provider_outage(routes=tuple(reversed(routes)), owner=OWNER)

    assert forward == reverse
    assert hash(forward) == hash(reverse)
    assert forward.customer_projection() == reverse.customer_projection()
    assert forward.customer_projection()["customer_actions"] == ("retry_later", "reconnect")


# ── 12: exact owner isolation, empty input, duplicate rejection ───────────────

def test_exact_owner_isolation_empty_input_and_duplicate_rejection():
    available = available_status()

    assert coordinate_provider_outage(routes=(), owner=OWNER) is REFUSAL
    assert coordinate_provider_outage(routes=(), owner=OWNER) == REFUSAL
    assert coordinate_provider_outage(routes=(available,), owner="") is REFUSAL
    assert coordinate_provider_outage(routes=(available,), owner=None) is REFUSAL
    assert coordinate_provider_outage(routes=[available], owner=OWNER) is REFUSAL

    other_owner = available_status(identity("xero", "invoices", "owner-b"))
    assert coordinate_provider_outage(routes=(other_owner,), owner=OWNER) is REFUSAL

    duplicate = (
        available_status(identity("xero", "invoices")),
        available_status(identity("xero", "invoices")),
    )
    assert coordinate_provider_outage(routes=duplicate, owner=OWNER) is REFUSAL


# ── 13: cross-owner/route, source substitution and mutation rejection ─────────

def test_cross_owner_cross_route_source_substitution_and_mutation_rejected():
    cross_owner = available_status(identity("xero", "invoices", "owner-b"))
    assert coordinate_provider_outage(routes=(cross_owner,), owner=OWNER) is REFUSAL

    # Identical payload reused for a different route: swap the identity after
    # construction so the status binding no longer matches the claimed route.
    substituted = available_status(identity("xero", "invoices"))
    object.__setattr__(
        substituted, "identity", EvidenceRouteIdentity("freeagent", "invoices", OWNER)
    )
    assert coordinate_provider_outage(routes=(substituted,), owner=OWNER) is REFUSAL

    mutated_state = available_status(identity("xero", "invoices"))
    object.__setattr__(mutated_state, "state", OperationalState.STALE)
    assert coordinate_provider_outage(routes=(mutated_state,), owner=OWNER) is REFUSAL

    mutated_timestamp = available_status(identity("xero", "invoices"))
    object.__setattr__(mutated_timestamp, "observed_at", dt(10))
    assert coordinate_provider_outage(routes=(mutated_timestamp,), owner=OWNER) is REFUSAL


# ── 14: subtype, incomplete, equality/hash/repr/copy/deepcopy/pickle, rebinding ─

class _StatusSubclass(EvidenceRouteStatus):
    pass


class _IdentitySubclass(EvidenceRouteIdentity):
    pass


class _EqualityProbe:
    calls = 0

    def __eq__(self, other):
        type(self).calls += 1
        raise AssertionError("attacker equality must never run")


def test_subtype_and_incomplete_upstream_objects_fail_closed():
    subclass_status = _StatusSubclass(identity(), OperationalState.TEMPORARILY_UNAVAILABLE)
    assert coordinate_provider_outage(routes=(subclass_status,), owner=OWNER) is REFUSAL

    bad_identity_status = available_status()
    object.__setattr__(
        bad_identity_status, "identity", _IdentitySubclass("xero", "invoices", OWNER)
    )
    assert coordinate_provider_outage(routes=(bad_identity_status,), owner=OWNER) is REFUSAL

    incomplete = object.__new__(EvidenceRouteStatus)
    assert coordinate_provider_outage(routes=(incomplete,), owner=OWNER) is REFUSAL


@pytest.mark.parametrize("index", range(3))
def test_identity_binding_equality_probe_in_every_slot_fails_closed(index):
    status = available_status()
    binding = list(status.identity._identity_binding)
    binding[index] = _EqualityProbe()
    object.__setattr__(status.identity, "_identity_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert coordinate_provider_outage(routes=(status,), owner=OWNER) is REFUSAL
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("index", range(8))
def test_status_binding_equality_probe_in_every_slot_fails_closed(index):
    status = available_status()
    binding = list(status._status_binding)
    binding[index] = _EqualityProbe()
    object.__setattr__(status, "_status_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert coordinate_provider_outage(routes=(status,), owner=OWNER) is REFUSAL
    assert _EqualityProbe.calls == 0


def test_recovery_binding_authority_probe_fails_closed_by_identity():
    status = degraded_status(OperationalState.RECOVERY_PENDING, identity("freeagent", "invoices"))
    recovery = list(status._recovery_binding)
    recovery[0] = _EqualityProbe()
    object.__setattr__(status, "_recovery_binding", tuple(recovery))
    _EqualityProbe.calls = 0
    assert coordinate_provider_outage(routes=(status,), owner=OWNER) is REFUSAL
    assert _EqualityProbe.calls == 0


def test_result_value_semantics_copy_deepcopy_repr_and_pickle():
    result = coordinate_provider_outage(routes=(available_status(),), owner=OWNER)
    assert isinstance(result, ProviderOutageCoordination)
    assert copy.copy(result) is result
    assert copy.deepcopy(result) is result
    assert "xero" not in repr(result) and "invoices" not in repr(result)
    with pytest.raises((OperationalResilienceError, TypeError, pickle.PicklingError)):
        pickle.dumps(result)

    assert copy.copy(REFUSAL) is REFUSAL
    assert copy.deepcopy(REFUSAL) is REFUSAL
    with pytest.raises((OperationalResilienceError, TypeError, pickle.PicklingError)):
        pickle.dumps(REFUSAL)


def test_result_reconstruction_and_mutation_fail_closed():
    result = coordinate_provider_outage(routes=(available_status(),), owner=OWNER)

    incomplete = object.__new__(ProviderOutageCoordination)
    with pytest.raises(OperationalResilienceError):
        incomplete.customer_projection()

    object.__setattr__(result, "_aggregate_state", OperationalState.STALE)
    with pytest.raises(OperationalResilienceError):
        result.customer_projection()


def test_rebound_public_collaborators_cannot_change_coordination(monkeypatch):
    import reserved.services.provider_outage_coordination as module

    routes = (
        available_status(identity("xero", "invoices")),
        classify_outage(
            identity=identity("freeagent", "invoices"),
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(12),
        ),
    )
    expected = coordinate_provider_outage(routes=routes, owner=OWNER)

    for name in (
        "EvidenceRouteStatus",
        "EvidenceRouteIdentity",
        "OperationalState",
        "CustomerMessage",
        "CustomerAction",
        "OperationalResilienceError",
        "_STATE_PRECEDENCE",
        "_MESSAGE_BY_STATE",
        "_ACTION_BY_STATE",
        "_ACTION_ORDER",
        "_SAFE_OWNER",
        "weakref",
    ):
        monkeypatch.setattr(module, name, object())

    result = coordinate_provider_outage(routes=routes, owner=OWNER)
    assert result == expected
    assert hash(result) == hash(expected)
    # Validator/projection collaborators are also closure-bound: rebinding the
    # module enums must not break the customer projection or repr surfaces.
    assert result.customer_projection() == expected.customer_projection()
    assert repr(result) == repr(expected)
    assert "INVALID" not in repr(result)


# ── 15: no sensitive content reaches the customer-safe boundary ───────────────

def test_no_identifier_payload_timestamp_secret_or_url_reaches_customer_surface():
    routes = (
        available_status(identity("secret-provider", "secret-route")),
        classify_outage(
            identity=identity("freeagent", "invoices"),
            event=OutageEvent.TIMEOUT,
            occurred_at=dt(12),
        ),
    )
    result = coordinate_provider_outage(routes=routes, owner="secret-owner")
    projection = result.customer_projection()
    rendered = repr(result)

    forbidden = (
        "secret-provider",
        "secret-route",
        "secret-owner",
        "freeagent",
        "invoices",
        "2026",
        "http",
        "token",
        "credential",
        "T00",
    )
    for surface in (projection, rendered):
        assert not any(value in str(surface) for value in forbidden)

    refusal = coordinate_provider_outage(routes=(), owner="secret-owner")
    assert refusal is REFUSAL
    assert refusal.customer_projection() == {"refused": True}
    assert "secret" not in str(refusal.customer_projection())
    assert "secret" not in repr(refusal)


# ── 16: no request-time filesystem/network/provider calls ─────────────────────

def test_module_is_network_and_persistence_inert():
    import inspect

    import reserved.services.provider_outage_coordination as module

    source = inspect.getsource(module)
    for forbidden in (
        "import requests",
        "import urllib",
        "import socket",
        "import sqlite3",
        "import os",
        "import pickle",
        "import pathlib",
        "from os",
        "from pathlib",
        "getenv",
        "environ",
        "open(",
        "subprocess",
        "import logging",
    ):
        assert forbidden not in source


# ── 17: coordinator-only issuance — direct/reconstructed construction fails closed ──

def test_direct_construction_fails_closed():
    forged = ProviderOutageCoordination(
        OperationalState.AVAILABLE,
        CustomerMessage.AVAILABLE,
        (),
        frozenset(),
        dt(9),
    )
    with pytest.raises(OperationalResilienceError):
        forged.customer_projection()
    assert "INVALID" in repr(forged)


def test_reconstructed_result_fails_closed():
    result = coordinate_provider_outage(routes=(available_status(),), owner=OWNER)

    # Same exact fields, but reconstructed outside the coordinator, so it has no
    # process-local issuance authority.
    reconstructed = ProviderOutageCoordination(
        result._aggregate_state,
        result._aggregate_message,
        result._actions,
        result._route_digest,
        result._as_of,
    )
    with pytest.raises(OperationalResilienceError):
        reconstructed.customer_projection()


# ── 18: immutable closure-bound mapping collaborators ──────────────────────────

def test_in_place_mapping_mutation_does_not_change_coordination(monkeypatch):
    import reserved.services.provider_outage_coordination as module

    routes = (available_status(),)
    expected = coordinate_provider_outage(routes=routes, owner=OWNER)

    # Mutate the module-global dictionaries in place after binding. The bound
    # coordinator must keep using its immutable snapshot.
    monkeypatch.setitem(
        module._MESSAGE_BY_STATE,
        OperationalState.AVAILABLE,
        CustomerMessage.RECONNECT_REQUIRED,
    )
    monkeypatch.setitem(
        module._ACTION_BY_STATE,
        OperationalState.AVAILABLE,
        CustomerAction.RECONNECT,
    )

    result = coordinate_provider_outage(routes=routes, owner=OWNER)
    assert result.customer_projection() == expected.customer_projection()


# ── 19: exact per-route status/provenance identity ─────────────────────────────

def test_swapped_route_outcomes_yield_distinguishable_identities():
    xero_available = available_status(identity("xero", "invoices"))
    freeagent_timeout = classify_outage(
        identity=identity("freeagent", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(12),
    )
    forward = coordinate_provider_outage(
        routes=(xero_available, freeagent_timeout), owner=OWNER
    )

    xero_timeout = classify_outage(
        identity=identity("xero", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(12),
    )
    freeagent_available = available_status(identity("freeagent", "invoices"))
    swapped = coordinate_provider_outage(
        routes=(xero_timeout, freeagent_available), owner=OWNER
    )

    # The customer-visible aggregate is identical (same precedence winner), but
    # the exact per-route status/provenance identity must distinguish which route
    # carried which validated status.
    assert forward.customer_projection() == swapped.customer_projection()
    assert forward != swapped
    assert forward._route_digest != swapped._route_digest


# ── 20: exact timezone-aware coordination-time boundary ────────────────────────

def test_future_route_timestamps_rejected_relative_to_as_of():
    # Future observation/retrieval/verification on an available route.
    future_available = available_status(
        observed=dt(23), retrieved=dt(23, 5), verified=dt(23, 6)
    )
    assert (
        coordinate_provider_outage(
            routes=(future_available,), owner=OWNER, as_of=dt(20)
        )
        is REFUSAL
    )
    assert isinstance(
        coordinate_provider_outage(
            routes=(future_available,), owner=OWNER, as_of=dt(23, 30)
        ),
        ProviderOutageCoordination,
    )

    # Future transition timestamp on a degraded route.
    future_transition = classify_outage(
        identity=identity("freeagent", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(23),
    )
    assert (
        coordinate_provider_outage(
            routes=(future_transition,), owner=OWNER, as_of=dt(20)
        )
        is REFUSAL
    )


def test_naive_or_non_datetime_as_of_is_refused():
    assert (
        coordinate_provider_outage(
            routes=(available_status(),),
            owner=OWNER,
            as_of=datetime(2026, 8, 13, 12),
        )
        is REFUSAL
    )
    assert (
        coordinate_provider_outage(
            routes=(available_status(),), owner=OWNER, as_of="not-a-time"
        )
        is REFUSAL
    )


# ── 21: issuance/integrity is not transferable ────────────────────────────────

def test_mutation_plus_reinit_does_not_reissue_validity():
    source = classify_outage(
        identity=identity("xero", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(10),
    )
    result = coordinate_provider_outage(routes=(source,), owner=OWNER, as_of=dt(15))

    object.__setattr__(result, "_aggregate_state", OperationalState.AVAILABLE)
    object.__setattr__(result, "_aggregate_message", CustomerMessage.AVAILABLE)
    object.__setattr__(result, "_actions", ())
    # Re-initialisation must not re-issue validity: issuance is producer-held and
    # lives outside the consumer-writable dictionary.
    result.__post_init__()

    with pytest.raises(OperationalResilienceError):
        result.customer_projection()


def test_field_transfer_into_new_instance_fails_closed():
    source = classify_outage(
        identity=identity("xero", "invoices"),
        event=OutageEvent.TIMEOUT,
        occurred_at=dt(10),
    )
    result = coordinate_provider_outage(routes=(source,), owner=OWNER, as_of=dt(15))

    clone = object.__new__(ProviderOutageCoordination)
    clone.__dict__.update(result.__dict__)

    with pytest.raises(OperationalResilienceError):
        clone.customer_projection()
    assert "INVALID" in repr(clone)


# ── 22: equality/hash/copy validate integrity before protocol operations ──────

def test_unissued_result_fails_closed_on_equality_hash_and_copy():
    forged = ProviderOutageCoordination(
        OperationalState.AVAILABLE,
        CustomerMessage.AVAILABLE,
        (),
        frozenset(),
        dt(9),
    )
    valid = coordinate_provider_outage(routes=(available_status(),), owner=OWNER)

    with pytest.raises(OperationalResilienceError):
        _ = forged == valid
    with pytest.raises(OperationalResilienceError):
        _ = valid == forged
    with pytest.raises(OperationalResilienceError):
        hash(forged)
    with pytest.raises(OperationalResilienceError):
        copy.copy(forged)
    with pytest.raises(OperationalResilienceError):
        copy.deepcopy(forged)


def test_valid_result_foreign_equality_does_not_invoke_foreign_hook():
    valid = coordinate_provider_outage(routes=(available_status(),), owner=OWNER)
    _EqualityProbe.calls = 0
    assert (valid == _EqualityProbe()) is False
    assert _EqualityProbe.calls == 0


# ── 23: recovery source/observation provenance is part of the identity ────────

def test_recovery_source_provenance_distinguishes_identities():
    ident = identity("xero", "invoices")

    timeout_source = classify_outage(
        identity=ident, event=OutageEvent.TIMEOUT, occurred_at=dt(10)
    )
    revoked_source = classify_outage(
        identity=ident, event=OutageEvent.AUTHORISATION_REVOKED, occurred_at=dt(10)
    )

    observation = dict(observed_at=dt(11), retrieved_at=dt(12))
    timeout_pending = begin_recovery(
        current=timeout_source,
        observation=RecoveryObservation(identity=ident, **observation),
        now=dt(15),
    )
    revoked_pending = begin_recovery(
        current=revoked_source,
        observation=RecoveryObservation(identity=ident, **observation),
        now=dt(15),
    )

    timeout_result = coordinate_provider_outage(
        routes=(timeout_pending,), owner=OWNER, as_of=dt(15)
    )
    revoked_result = coordinate_provider_outage(
        routes=(revoked_pending,), owner=OWNER, as_of=dt(15)
    )

    # The customer-visible aggregate is identical, but the exact private evidence
    # identity must distinguish which validated source state led to recovery.
    assert timeout_result.customer_projection() == revoked_result.customer_projection()
    assert timeout_result._route_digest != revoked_result._route_digest
    assert timeout_result != revoked_result
