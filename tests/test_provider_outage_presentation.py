"""Focused adversarial tests for the owner-bound outage status fragment."""

from __future__ import annotations

import ast
import copy
import pickle
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

import reserved.services.provider_outage_presentation as presentation
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
)
from reserved.services.provider_outage_presentation import render_provider_outage_status

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "reserved/services/provider_outage_presentation.py"
TEMPLATE = ROOT / "reserved/templates/v2/_provider_outage_status.html"
UTC = timezone.utc
OWNER = "owner-123"


def _dt(hour: int) -> datetime:
    return datetime(2026, 8, 13, hour, tzinfo=UTC)


def _identity(owner: str | None = OWNER) -> EvidenceRouteIdentity:
    return EvidenceRouteIdentity("hostile-provider-secret", "hostile-route", owner)


def _available() -> EvidenceRouteStatus:
    return EvidenceRouteStatus(
        _identity(), OperationalState.AVAILABLE, _dt(9), _dt(10), _dt(11), True
    )


def _statuses() -> dict[OperationalState, EvidenceRouteStatus]:
    identity = _identity()
    ordinary = {
        OperationalState.TEMPORARILY_UNAVAILABLE: OutageEvent.TIMEOUT,
        OperationalState.AUTHORISATION_REQUIRED: OutageEvent.AUTHORISATION_EXPIRED,
        OperationalState.SCHEMA_INCOMPATIBLE: OutageEvent.SCHEMA_INCOMPATIBLE,
        OperationalState.EVIDENCE_INADEQUATE: OutageEvent.REQUIRED_FIELDS_MISSING,
    }
    result = {
        state: classify_outage(identity=identity, event=event, occurred_at=_dt(12))
        for state, event in ordinary.items()
    }
    result[OperationalState.STALE] = classify_outage(
        identity=identity, event=OutageEvent.EVIDENCE_STALE, occurred_at=_dt(12), prior=_available()
    )
    result[OperationalState.RECOVERY_PENDING] = begin_recovery(
        current=result[OperationalState.TEMPORARILY_UNAVAILABLE],
        observation=RecoveryObservation(identity, _dt(13), _dt(14)),
        now=_dt(15),
    )
    return result


EXPECTED = {
    OperationalState.TEMPORARILY_UNAVAILABLE: (CustomerMessage.TEMPORARILY_UNAVAILABLE, CustomerAction.RETRY_LATER, "Information temporarily unavailable", "Please try again later."),
    OperationalState.AUTHORISATION_REQUIRED: (CustomerMessage.RECONNECT_REQUIRED, CustomerAction.RECONNECT, "Connection needs attention", "Please reconnect your account to continue."),
    OperationalState.SCHEMA_INCOMPATIBLE: (CustomerMessage.DATA_FORMAT_CHANGED, CustomerAction.NONE, "Information temporarily unavailable", "You do not need to do anything right now."),
    OperationalState.EVIDENCE_INADEQUATE: (CustomerMessage.INFORMATION_INCOMPLETE, CustomerAction.PROVIDE_EVIDENCE, "More information needed", "Please provide the required information."),
    OperationalState.STALE: (CustomerMessage.INFORMATION_OUT_OF_DATE, CustomerAction.REFRESH, "Information out of date", "Please refresh your information."),
    OperationalState.RECOVERY_PENDING: (CustomerMessage.RECOVERY_IN_PROGRESS, CustomerAction.NONE, "Information update in progress", "You do not need to do anything right now."),
}


class _DOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_available_renders_no_banner_or_warning_content():
    assert render_provider_outage_status(_available(), OWNER) == ""


def test_all_six_degraded_states_map_exhaustively_and_deterministically():
    statuses = _statuses()
    assert set(statuses) == set(EXPECTED)
    for state, status in statuses.items():
        message, action, heading, guidance = EXPECTED[state]
        output = render_provider_outage_status(status, OWNER)
        assert status.customer_message_key is message
        assert status.customer_action is action
        assert status.may_use_as_current is False
        assert heading in output and guidance in output
        assert output == render_provider_outage_status(status, OWNER)


def test_stale_and_recovery_copy_never_promotes_or_exposes_retained_data():
    statuses = _statuses()
    stale = render_provider_outage_status(statuses[OperationalState.STALE], OWNER)
    pending = render_provider_outage_status(statuses[OperationalState.RECOVERY_PENDING], OWNER)
    assert "retained information is out of date" in stale.lower()
    assert "refreshed information is still being checked and is not yet usable" in pending.lower()
    for output in (stale, pending):
        assert not any(word in output.lower() for word in ("verified", "ready", "£", "999.99"))
        assert not any(value.isoformat() in output for value in (_dt(9), _dt(10), _dt(11)))


class _StringSubclass(str):
    def __eq__(self, other):
        raise AssertionError("subclass equality must not run")


class _StatusSubclass(EvidenceRouteStatus):
    pass


class _IdentitySubclass(EvidenceRouteIdentity):
    pass


class _EqualityProbe:
    calls = 0

    def __eq__(self, other):
        type(self).calls += 1
        raise AssertionError("attacker equality must never run")


def _closed() -> str:
    return render_provider_outage_status(None, None)


@pytest.mark.parametrize("owner", [None, "", "wrong", _StringSubclass(OWNER), object()])
def test_wrong_missing_empty_subclass_and_malformed_owners_fail_identically(owner):
    assert render_provider_outage_status(_available(), owner) == _closed()


def test_swapped_owner_fails_and_exact_owner_succeeds():
    a = EvidenceRouteStatus(_identity("owner-a"), OperationalState.TEMPORARILY_UNAVAILABLE)
    b = EvidenceRouteStatus(_identity("owner-b"), OperationalState.TEMPORARILY_UNAVAILABLE)
    assert render_provider_outage_status(a, "owner-a") != _closed()
    assert render_provider_outage_status(a, b.identity.owner_scope) == _closed()


def test_forged_mutated_subclassed_and_incomplete_values_fail_before_projection():
    incomplete_status = object.__new__(EvidenceRouteStatus)
    incomplete_identity = object.__new__(EvidenceRouteIdentity)
    with_bad_identity = _available()
    object.__setattr__(with_bad_identity, "identity", incomplete_identity)
    mutated = _available()
    object.__setattr__(mutated, "state", OperationalState.STALE)
    subclassed = object.__new__(_StatusSubclass)
    identity_subclass = object.__new__(_IdentitySubclass)
    identity_status = _available()
    object.__setattr__(identity_status, "identity", identity_subclass)
    forged_pending = EvidenceRouteStatus(
        _identity(), OperationalState.RECOVERY_PENDING, _dt(13), _dt(14)
    )
    invalid = (incomplete_status, with_bad_identity, mutated, subclassed, identity_status, forged_pending)
    assert {render_provider_outage_status(value, OWNER) for value in invalid} == {_closed()}


def test_owner_mutation_with_equality_spoofed_bindings_fails_closed_without_equality():
    status = EvidenceRouteStatus(
        _identity("owner-a"), OperationalState.TEMPORARILY_UNAVAILABLE
    )
    object.__setattr__(status.identity, "owner_scope", "owner-b")
    spoof = _EqualityProbe()
    object.__setattr__(status.identity, "_identity_binding", (spoof, spoof, spoof))
    object.__setattr__(status, "_status_binding", ((spoof, spoof, spoof), spoof) + (spoof,) * 6)
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, "owner-b") == _closed()
    assert _EqualityProbe.calls == 0


def test_state_mutation_with_equality_spoofed_status_binding_fails_closed_without_equality():
    status = EvidenceRouteStatus(
        _identity(), OperationalState.TEMPORARILY_UNAVAILABLE
    )
    object.__setattr__(status, "state", OperationalState.AUTHORISATION_REQUIRED)
    binding = list(status._status_binding)
    binding[1] = _EqualityProbe()
    object.__setattr__(status, "_status_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("index", range(3))
def test_identity_binding_rejects_equality_probe_in_every_slot(index):
    status = _available()
    binding = list(status.identity._identity_binding)
    binding[index] = _EqualityProbe()
    object.__setattr__(status.identity, "_identity_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("index", range(8))
def test_status_binding_rejects_equality_probe_in_every_slot(index):
    status = _available()
    binding = list(status._status_binding)
    binding[index] = _EqualityProbe()
    object.__setattr__(status, "_status_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("index", range(3))
def test_status_nested_identity_binding_rejects_every_equality_probe(index):
    status = _available()
    binding = list(status._status_binding)
    nested = list(binding[0])
    nested[index] = _EqualityProbe()
    binding[0] = tuple(nested)
    object.__setattr__(status, "_status_binding", tuple(binding))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("layer,index", [("current", index) for index in range(8)] + [("observation", index) for index in range(3)])
def test_recovery_bindings_reject_equality_probe_in_every_replaceable_slot(layer, index):
    status = _statuses()[OperationalState.RECOVERY_PENDING]
    recovery = list(status._recovery_binding)
    target_index = 1 if layer == "current" else 2
    target = list(recovery[target_index])
    target[index] = _EqualityProbe()
    recovery[target_index] = tuple(target)
    object.__setattr__(status, "_recovery_binding", tuple(recovery))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


@pytest.mark.parametrize("layer,index", [("current", index) for index in range(3)] + [("observation", index) for index in range(3)])
def test_recovery_nested_identity_bindings_reject_every_equality_probe(layer, index):
    status = _statuses()[OperationalState.RECOVERY_PENDING]
    recovery = list(status._recovery_binding)
    target_index = 1 if layer == "current" else 2
    target = list(recovery[target_index])
    nested = list(target[0])
    nested[index] = _EqualityProbe()
    target[0] = tuple(nested)
    recovery[target_index] = tuple(target)
    object.__setattr__(status, "_recovery_binding", tuple(recovery))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


def test_recovery_authority_spoof_fails_closed_by_identity_without_equality():
    status = _statuses()[OperationalState.RECOVERY_PENDING]
    recovery = list(status._recovery_binding)
    recovery[0] = _EqualityProbe()
    object.__setattr__(status, "_recovery_binding", tuple(recovery))
    _EqualityProbe.calls = 0
    assert render_provider_outage_status(status, OWNER) == _closed()
    assert _EqualityProbe.calls == 0


def test_sensitive_and_hostile_upstream_fields_never_reach_output_or_model_repr():
    hostile = '<script>secret-token https://evil.test/path</script>'
    status = EvidenceRouteStatus(
        EvidenceRouteIdentity("secret-provider", "secret-route", OWNER),
        OperationalState.TEMPORARILY_UNAVAILABLE,
    )
    object.__setattr__(status.identity, "provider", hostile)
    output = render_provider_outage_status(status, OWNER)
    forbidden = ("secret-provider", "secret-route", "secret-token", "evil.test", "<script>")
    assert not any(value in output for value in forbidden)
    assert not any(value in repr(presentation._CLOSED_MODEL) for value in forbidden)


def test_autoescaping_accessibility_and_no_actionable_surface():
    output = render_provider_outage_status(_statuses()[OperationalState.AUTHORISATION_REQUIRED], OWNER)
    parser = _DOM(); parser.feed(output)
    section = parser.tags[0]
    assert section == ("section", {"role": "status", "aria-live": "polite", "aria-atomic": "true", "aria-labelledby": "service-status-heading"})
    assert ("h2", {"id": "service-status-heading"}) in parser.tags
    assert not [tag for tag, _ in parser.tags if tag in {"a", "button", "form", "script", "iframe"}]
    assert not any(term in output.lower() for term in ("http://", "https://", "javascript:", "provider"))
    environment = Environment(loader=FileSystemLoader(TEMPLATE.parent.parent), autoescape=select_autoescape(("html",)))
    hostile = '<img src=x onerror="secret()">'
    raw = environment.get_template("v2/_provider_outage_status.html").render(model=(hostile,) * 3)
    assert hostile not in raw and raw.count("&lt;img") == 3


def test_upstream_copy_deepcopy_and_pickle_contract_is_unchanged():
    status = _statuses()[OperationalState.RECOVERY_PENDING]
    assert copy.copy(status) is status and copy.deepcopy(status) is status
    with pytest.raises(OperationalResilienceError):
        pickle.dumps(status)


def test_rebound_public_collaborators_cannot_change_supported_boundary(monkeypatch):
    expected = render_provider_outage_status(_statuses()[OperationalState.STALE], OWNER)
    for name in ("EvidenceRouteStatus", "EvidenceRouteIdentity", "OperationalState", "CustomerMessage", "CustomerAction", "Environment", "FileSystemLoader", "select_autoescape", "_COPY_BY_STATE", "_CLOSED_MODEL"):
        monkeypatch.setattr(presentation, name, object())
    assert render_provider_outage_status(_statuses()[OperationalState.STALE], OWNER) == expected
    assert render_provider_outage_status(None, None) == _closed()


def test_only_supported_renderer_is_public_and_imports_are_narrow():
    assert presentation.__all__ == ("render_provider_outage_status",)
    imports = {node.module or "" for node in ast.walk(ast.parse(SERVICE.read_text())) if isinstance(node, ast.ImportFrom)}
    assert imports == {"__future__", "datetime", "pathlib", "jinja2", "reserved.providers.operational_resilience"}
    forbidden_modules = ("flask", "requests", "urllib", "socket", "database", "reserved.web", "reserved.auth")
    assert not [name for name in imports if any(term in name.lower() for term in forbidden_modules)]


def test_invalid_inputs_are_byte_identical_and_value_free():
    outputs = {
        render_provider_outage_status(value, owner)
        for value, owner in ((None, None), (object(), OWNER), (_available(), "wrong"), ("secret-token", OWNER), (_available(), ""))
    }
    assert outputs == {_closed()}
    assert "secret" not in _closed().lower() and "owner" not in _closed().lower()


def test_candidate_uses_only_the_three_authorised_paths():
    assert SERVICE.is_file() and TEMPLATE.is_file() and Path(__file__).is_file()
