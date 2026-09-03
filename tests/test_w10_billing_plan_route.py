"""W10-S6C authenticated, presentation-only billing-plan route."""

from __future__ import annotations

import re
import importlib
from pathlib import Path

import pytest
from markupsafe import Markup

import reserved.database as db
from reserved import create_app
from reserved.billing.contracts import INITIAL_BILLING_AUTHORITY


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "reserved" / "templates" / "v2" / "dashboard.html"
PLANS = ROOT / "reserved" / "templates" / "v2" / "plans.html"
V2 = ROOT / "reserved" / "web" / "v2.py"

EXPECTED_LABELS = (
    "£29 per month",
    "£156 for six months",
    "£288 per year",
)
VAT = "Prices include VAT where applicable."


@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "w10_s6c.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client) -> None:
    response = client.get("/v2/demo-login")
    assert response.status_code == 302


def _body(client, path: str = "/v2/plans") -> str:
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_route_requires_the_existing_authentication_boundary(client):
    response = client.get("/v2/plans")
    assert response.status_code == 302
    assert "/v2/demo-login" in response.location


def test_authenticated_route_shows_only_settled_ordered_prices_and_vat(client):
    _login(client)
    body = _body(client)
    positions = [body.index(label) for label in EXPECTED_LABELS]
    assert positions == sorted(positions)
    assert all(body.count(label) == 1 for label in EXPECTED_LABELS)
    assert body.count(VAT) == 1
    assert not re.search(r"£(?!29\b|156\b|288\b)\d", body)


def test_page_truthfully_has_no_purchase_or_access_change_action(client):
    _login(client)
    body = _body(client)
    assert "Purchasing a plan or changing access is not available in this preview." in body
    lowered = body.lower()
    for forbidden in (
        "checkout",
        "payment intent",
        "customer portal",
        "buy now",
        "subscribe now",
        "change plan",
        "discount code",
    ):
        assert forbidden not in lowered


def test_query_is_inert_and_unsupported_methods_are_rejected(client):
    _login(client)
    baseline = _body(client)
    hostile = _body(
        client,
        "/v2/plans?plan=free&price=1&checkout=https://evil.invalid&discount=100",
    )
    assert hostile == baseline
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/v2/plans").status_code == 405


def test_route_has_no_store_and_application_security_headers(client):
    _login(client)
    response = client.get("/v2/plans")
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    assert "Cookie" in response.headers.getlist("Vary")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "payment=()" in response.headers["Permissions-Policy"]
    assert "form-action 'self'" in response.headers["Content-Security-Policy"]


def test_module_global_rebinding_cannot_replace_bound_authority_or_renderers(
    client, monkeypatch
):
    route_module = importlib.import_module("reserved.web.v2")

    _login(client)
    baseline = _body(client)
    monkeypatch.setattr(route_module, "INITIAL_BILLING_AUTHORITY", object())
    monkeypatch.setattr(route_module, "present_w10_billing_presentation", lambda value: object())
    monkeypatch.setattr(route_module, "render_w10_billing_plans_fragment", lambda value: "<script>bad()</script>")
    monkeypatch.setattr(route_module, "_w10_plan_fragment", lambda: "<script>alsoBad()</script>")
    assert _body(client) == baseline


def test_decorated_route_metadata_cannot_substitute_trusted_html(client, monkeypatch):
    route_module = importlib.import_module("reserved.web.v2")
    route = route_module.billing_plans
    attack = lambda: Markup("<script id='route-default-attack'>bad()</script>")

    assert route.__defaults__ is None
    assert route.__kwdefaults__ is None
    assert "__wrapped__" not in route.__dict__

    _login(client)
    baseline = _body(client)

    # Function metadata is mutable Python state. None of it is consulted by the
    # zero-argument handler or the require_auth closure during route execution.
    monkeypatch.setattr(route, "__defaults__", (attack,))
    monkeypatch.setattr(route, "__kwdefaults__", {"fragment_supplier": attack})
    monkeypatch.setitem(route.__dict__, "fragment_supplier", attack)
    monkeypatch.setitem(route.__dict__, "template_renderer", lambda *args, **kwargs: attack())
    monkeypatch.setitem(route.__dict__, "__wrapped__", attack)

    body = _body(client)
    assert body == baseline
    assert "route-default-attack" not in body
    assert "bad()" not in body
    assert all(body.count(label) == 1 for label in EXPECTED_LABELS)


def test_bound_application_view_has_no_exposed_wrapped_handler(app):
    route = app.view_functions["v2.billing_plans"]
    assert route.__defaults__ is None
    assert route.__kwdefaults__ is None
    assert "__wrapped__" not in route.__dict__


def test_tampered_captured_authority_fails_to_fixed_review_required_state(client):
    _login(client)
    original = object.__getattribute__(INITIAL_BILLING_AUTHORITY, "authority_version")
    try:
        object.__setattr__(INITIAL_BILLING_AUTHORITY, "authority_version", "tampered")
        body = _body(client)
    finally:
        object.__setattr__(INITIAL_BILLING_AUTHORITY, "authority_version", original)

    assert "Review required — billing plans are temporarily unavailable." in body
    assert all(label not in body for label in EXPECTED_LABELS)
    assert VAT not in body


def test_trusted_fragment_has_one_internal_source_and_template_never_marks_input_safe():
    source = V2.read_text(encoding="utf-8")
    template = PLANS.read_text(encoding="utf-8")
    assert "trusted_html_type(renderer(presentation))" in source
    assert "billing_plans_fragment|safe" not in template
    assert "INITIAL_BILLING_AUTHORITY" not in template
    assert not any(label in template for label in EXPECTED_LABELS)
    assert VAT not in template


def test_dashboard_has_exactly_one_price_free_plans_link():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert source.count("url_for('v2.billing_plans')") == 1
    assert source.count("View plans") == 1
    assert not any(label in source for label in EXPECTED_LABELS)
    assert VAT not in source


def test_route_performs_no_billing_or_domain_state_or_network_actions(
    app, client, monkeypatch
):
    route_module = importlib.import_module("reserved.web.v2")
    app.config["WTF_CSRF_ENABLED"] = True

    _login(client)

    def forbidden(*args, **kwargs):
        raise AssertionError("plans route attempted an unrelated state or network action")

    for name in (
        "get_or_create_user",
        "list_connections_for_user",
        "persist_match_result",
        "seed_demo_data",
        "YapilyClient",
    ):
        monkeypatch.setattr(route_module, name, forbidden)
    with client.session_transaction() as flask_session:
        before = dict(flask_session)

    body = _body(client)

    with client.session_transaction() as flask_session:
        after = dict(flask_session)

    assert EXPECTED_LABELS[0] in body
    assert set(before) <= set(after)
    assert set(after) - set(before) <= {"csrf_token"}
    assert all(after[key] == value for key, value in before.items())


def test_owned_templates_contain_no_billing_control_identifiers_or_calculations():
    combined = (PLANS.read_text(encoding="utf-8") + DASHBOARD.read_text(encoding="utf-8")).lower()
    for forbidden in (
        "checkout_id",
        "payment_intent",
        "portal_session",
        "entitlement_id",
        "discount_percent",
        "vat_rate",
        "annual saving",
        "monthly equivalent",
    ):
        assert forbidden not in combined
