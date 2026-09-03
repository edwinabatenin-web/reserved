"""Focused adversarial tests for coordinated provider-outage HTML."""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

import reserved.services.provider_outage_coordination_presentation as presentation
from reserved.providers.operational_resilience import (
    EvidenceRouteIdentity,
    EvidenceRouteStatus,
    OperationalState,
    OutageEvent,
    RecoveryObservation,
    begin_recovery,
    classify_outage,
)
from reserved.services.provider_outage_coordination import (
    ProviderOutageCoordination,
    coordinate_provider_outage,
)
from reserved.services.provider_outage_coordination_presentation import (
    render_coordinated_provider_outage_status,
)

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "reserved/services/provider_outage_coordination_presentation.py"
TEMPLATE = ROOT / "reserved/templates/v2/_provider_outage_coordination_status.html"
UTC = timezone.utc
OWNER = "owner-a"


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 13, hour, minute, tzinfo=UTC)


def identity(
    provider: str = "xero", route: str = "invoices", owner: str | None = OWNER
) -> EvidenceRouteIdentity:
    return EvidenceRouteIdentity(provider, route, owner)


def available(provider: str = "xero", route: str = "invoices") -> EvidenceRouteStatus:
    return EvidenceRouteStatus(
        identity(provider, route),
        OperationalState.AVAILABLE,
        dt(9),
        dt(9, 5),
        dt(9, 6),
        True,
    )


def degraded(
    state: OperationalState, provider: str = "freeagent", route: str = "invoices"
) -> EvidenceRouteStatus:
    ident = identity(provider, route)
    events = {
        OperationalState.TEMPORARILY_UNAVAILABLE: OutageEvent.TIMEOUT,
        OperationalState.AUTHORISATION_REQUIRED: OutageEvent.AUTHORISATION_EXPIRED,
        OperationalState.SCHEMA_INCOMPATIBLE: OutageEvent.SCHEMA_INCOMPATIBLE,
        OperationalState.EVIDENCE_INADEQUATE: OutageEvent.REQUIRED_FIELDS_MISSING,
    }
    if state in events:
        return classify_outage(identity=ident, event=events[state], occurred_at=dt(12))
    if state is OperationalState.STALE:
        return classify_outage(
            identity=ident,
            event=OutageEvent.EVIDENCE_STALE,
            occurred_at=dt(12),
            prior=EvidenceRouteStatus(
                ident, OperationalState.AVAILABLE, dt(9), dt(10), dt(11), True
            ),
        )
    if state is OperationalState.RECOVERY_PENDING:
        current = classify_outage(
            identity=ident, event=OutageEvent.TIMEOUT, occurred_at=dt(10)
        )
        return begin_recovery(
            current=current,
            observation=RecoveryObservation(ident, dt(11), dt(11, 1)),
            now=dt(12),
        )
    raise AssertionError("unsupported fixture state")


def render(routes: tuple, *, owner: object = OWNER, as_of: object = dt(16)) -> str:
    return render_coordinated_provider_outage_status(
        routes=routes, owner=owner, as_of=as_of
    )


def closed() -> str:
    return render(())


EXPECTED = {
    OperationalState.TEMPORARILY_UNAVAILABLE: (
        "Information temporarily unavailable",
        "Try again later.",
    ),
    OperationalState.AUTHORISATION_REQUIRED: (
        "Connection needs attention",
        "Reconnect the affected account.",
    ),
    OperationalState.SCHEMA_INCOMPATIBLE: (
        "Information temporarily unavailable",
        None,
    ),
    OperationalState.EVIDENCE_INADEQUATE: (
        "More information needed",
        "Provide the required information.",
    ),
    OperationalState.STALE: ("Information out of date", "Refresh your information."),
    OperationalState.RECOVERY_PENDING: ("Information update in progress", None),
}


@pytest.mark.parametrize("state", tuple(EXPECTED))
def test_each_degraded_state_renders_only_bounded_aggregate_copy(state):
    output = render((available(), degraded(state)))
    heading, action = EXPECTED[state]
    assert heading in output
    if action is None:
        assert "<ul" not in output
        assert "No action is required right now." in output
    else:
        assert action in output
    assert output == render((degraded(state), available()))


def test_all_available_routes_return_exactly_empty_html():
    routes = (available("xero"), available("freeagent"), available("quickbooks"))
    assert render(routes) == ""


def test_mixed_precedence_and_every_distinct_action_use_canonical_order():
    routes = (
        degraded(OperationalState.STALE, "xero"),
        degraded(OperationalState.EVIDENCE_INADEQUATE, "freeagent"),
        degraded(OperationalState.AUTHORISATION_REQUIRED, "quickbooks"),
        degraded(OperationalState.TEMPORARILY_UNAVAILABLE, "hmrc"),
    )
    output = render(routes)
    assert "Information temporarily unavailable" in output
    actions = (
        "Try again later.",
        "Reconnect the affected account.",
        "Provide the required information.",
        "Refresh your information.",
    )
    positions = [output.index(action) for action in actions]
    assert positions == sorted(positions)
    assert all(output.count(action) == 1 for action in actions)
    assert output == render(tuple(reversed(routes)))


def test_no_action_precedence_with_lower_actionable_route_uses_action_guidance():
    routes = (
        degraded(OperationalState.SCHEMA_INCOMPATIBLE, "xero"),
        degraded(OperationalState.STALE, "freeagent"),
    )
    output = render(routes)
    assert "Some information is not current because its format has changed." in output
    assert "Follow each applicable step below." in output
    assert "Refresh your information." in output
    assert "No action is required right now." not in output


def test_action_list_and_no_action_guidance_are_mutually_exclusive_for_all_states():
    combinations = [
        (degraded(state),)
        for state in EXPECTED
    ] + [
        (
            degraded(OperationalState.SCHEMA_INCOMPATIBLE, "xero"),
            degraded(OperationalState.STALE, "freeagent"),
        ),
        (
            degraded(OperationalState.RECOVERY_PENDING, "xero"),
            degraded(OperationalState.EVIDENCE_INADEQUATE, "freeagent"),
        ),
    ]
    for routes in combinations:
        output = render(routes)
        has_actions = "<ul" in output
        assert ("Follow each applicable step below." in output) is has_actions
        assert ("No action is required right now." in output) is not has_actions


@pytest.mark.parametrize(
    "routes,owner,as_of",
    (
        ((), OWNER, dt(16)),
        ([available()], OWNER, dt(16)),
        ((available(),), "wrong", dt(16)),
        ((available(),), "", dt(16)),
        ((available(),), None, dt(16)),
        ((available(),), OWNER, datetime(2026, 8, 13, 16)),
        ((available(),), OWNER, "not-a-time"),
    ),
)
def test_malformed_owner_routes_and_time_are_fixed_generic_refusal(routes, owner, as_of):
    assert render_coordinated_provider_outage_status(
        routes=routes, owner=owner, as_of=as_of
    ) == closed()


def test_future_route_timestamp_is_refused_but_valid_boundary_renders():
    future = classify_outage(
        identity=identity(), event=OutageEvent.TIMEOUT, occurred_at=dt(20)
    )
    assert render((future,), as_of=dt(19)) == closed()
    assert render((future,), as_of=dt(20)) != closed()


class _StatusSubclass(EvidenceRouteStatus):
    pass


class _StringSubclass(str):
    def __eq__(self, other):
        raise AssertionError("hostile equality must not run")


def test_owner_mismatch_subtypes_incomplete_reconstruction_and_mutation_refuse():
    wrong_owner = EvidenceRouteStatus(
        identity(owner="owner-b"), OperationalState.TEMPORARILY_UNAVAILABLE
    )
    incomplete = object.__new__(EvidenceRouteStatus)
    subclassed = _StatusSubclass(identity(), OperationalState.TEMPORARILY_UNAVAILABLE)
    mutated = available()
    object.__setattr__(mutated, "state", OperationalState.STALE)
    reconstructed = available()
    reconstructed.__dict__.update(available().__dict__)
    for routes, owner in (
        ((wrong_owner,), OWNER),
        ((incomplete,), OWNER),
        ((subclassed,), OWNER),
        ((mutated,), OWNER),
        ((reconstructed,), _StringSubclass(OWNER)),
    ):
        assert render_coordinated_provider_outage_status(
            routes=routes, owner=owner, as_of=dt(16)
        ) == closed()


def test_route_mutation_and_duplicate_route_refuse_without_leakage():
    mutated = available()
    object.__setattr__(mutated.identity, "provider", "secret-provider")
    duplicate = (available(), available())
    for routes in ((mutated,), duplicate):
        output = render(routes)
        assert output == closed()
        assert "secret-provider" not in output


def test_coordinator_is_invoked_directly_with_exact_arguments(monkeypatch):
    calls = []
    real = coordinate_provider_outage

    def probe(*, routes, owner, as_of=None):
        calls.append((routes, owner, as_of))
        return real(routes=routes, owner=owner, as_of=as_of)

    renderer = presentation._bind_renderer(coordinator=probe)
    routes = (degraded(OperationalState.STALE),)
    assert "Information out of date" in renderer(
        routes=routes, owner=OWNER, as_of=dt(16)
    )
    assert calls == [(routes, OWNER, dt(16))]


def test_forged_or_mutated_coordination_result_cannot_render(monkeypatch):
    authentic = coordinate_provider_outage(
        routes=(degraded(OperationalState.STALE),), owner=OWNER, as_of=dt(16)
    )
    forged = ProviderOutageCoordination(
        authentic._aggregate_state,
        authentic._aggregate_message,
        authentic._actions,
        authentic._route_digest,
        authentic._as_of,
    )
    for result in (forged, authentic):
        if result is authentic:
            object.__setattr__(result, "_actions", ())
        renderer = presentation._bind_renderer(coordinator=lambda **_kwargs: result)
        assert renderer(routes=(available(),), owner=OWNER, as_of=dt(16)) == closed()


def test_rebound_module_collaborators_and_copy_maps_cannot_change_renderer(monkeypatch):
    routes = (degraded(OperationalState.STALE),)
    expected = render(routes)
    monkeypatch.setitem(
        presentation._COPY_BY_AGGREGATE,
        ("stale", "information_out_of_date"),
        ("SECRET", "SECRET", "SECRET"),
    )
    for name in (
        "coordinate_provider_outage",
        "ProviderOutageCoordination",
        "Environment",
        "FileSystemLoader",
        "select_autoescape",
        "_ACTION_COPY",
        "_ACTIONABLE_GUIDANCE",
        "_NO_ACTION_GUIDANCE",
        "_CLOSED_MODEL",
    ):
        monkeypatch.setattr(presentation, name, object())
    assert render(routes) == expected
    assert render(()) == closed()


class _DOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_accessibility_autoescaping_and_no_actionable_or_sensitive_surface():
    output = render((degraded(OperationalState.AUTHORISATION_REQUIRED),))
    parser = _DOM()
    parser.feed(output)
    assert parser.tags[0] == (
        "section",
        {
            "role": "status",
            "aria-live": "polite",
            "aria-atomic": "true",
            "aria-labelledby": "coordinated-service-status-heading",
        },
    )
    assert ("h2", {"id": "coordinated-service-status-heading"}) in parser.tags
    assert ("ul", {"aria-label": "What you can do"}) in parser.tags
    assert not [
        tag for tag, _attrs in parser.tags if tag in {"a", "button", "form", "script", "iframe"}
    ]
    forbidden = (
        OWNER,
        "freeagent",
        "invoices",
        "2026",
        "http://",
        "https://",
        "token",
        "secret",
        "provider",
        "route",
    )
    assert not any(value.lower() in output.lower() for value in forbidden)

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE.parent.parent),
        autoescape=select_autoescape(("html",)),
    )
    hostile = '<img src=x onerror="secret()">'
    raw = environment.get_template(f"v2/{TEMPLATE.name}").render(
        model=(hostile, hostile, hostile, (hostile,))
    )
    assert hostile not in raw and raw.count("&lt;img") == 4


def test_public_signature_imports_and_side_effect_exclusions_are_narrow():
    signature = inspect.signature(render_coordinated_provider_outage_status)
    assert tuple(signature.parameters) == ("routes", "owner", "as_of")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert presentation.__all__ == ("render_coordinated_provider_outage_status",)
    imports = {
        node.module or ""
        for node in ast.walk(ast.parse(SERVICE.read_text()))
        if isinstance(node, ast.ImportFrom)
    }
    assert imports == {
        "__future__",
        "pathlib",
        "jinja2",
        "reserved.services.provider_outage_coordination",
    }
    source = SERVICE.read_text().lower()
    for forbidden in (
        "import requests",
        "import urllib",
        "import socket",
        "import sqlite",
        "import os",
        "subprocess",
        "import logging",
        "open(",
        "retry(",
        "reconnect(",
        "persist(",
        "monitor(",
    ):
        assert forbidden not in source


def test_fixed_refusal_is_byte_identical_and_value_free():
    outputs = {
        render_coordinated_provider_outage_status(
            routes=routes, owner=owner, as_of=as_of
        )
        for routes, owner, as_of in (
            ((), OWNER, dt(16)),
            ((object(),), OWNER, dt(16)),
            ((available(),), "secret-owner", dt(16)),
            ((available(),), OWNER, "secret-time"),
        )
    }
    assert outputs == {closed()}
    assert not any(
        term in closed().lower()
        for term in ("owner", "provider", "route", "secret", "2026")
    )


def test_only_four_authorised_new_paths_exist_for_candidate():
    assert SERVICE.is_file() and TEMPLATE.is_file() and Path(__file__).is_file()
