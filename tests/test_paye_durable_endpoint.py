"""Real-request tests for disabled-first durable PAYE composition installation."""
from datetime import date
from decimal import Decimal

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.paye_durable_endpoint import (
    DurablePayeEndpointError, DurablePayeRuntime,
    install_durable_paye_composition_endpoint,
)
from tests.test_billing_composition import paid_event, runtime as billing_runtime
from tests.test_paye_annual_bridge import durable_annual, entry


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "endpoint.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("PAYE_DURABLE_COMPOSITION_ENABLED", raising=False)
    billing = billing_runtime(tmp_path)
    app = create_app(billing_runtime=billing)
    app.config.update(TESTING=True)
    owner = db.get_or_create_user("endpoint-owner", email="endpoint@example.test")
    other = db.get_or_create_user("endpoint-other", email="other@example.test")
    annual, repository = durable_annual(owner)
    stored = entry(1, "1200.00", user_id=owner)
    stored.pop("user_id")
    db.save_paye_manual_entry(owner, stored)
    paid_event(billing, owner)
    return app, owner, other, annual, repository, tmp_path


def install(app, annual, repository, scope=None, provider=None, clock=None):
    runtime = DurablePayeRuntime(
        repository=repository,
        annual_position_provider=provider or (lambda *_: annual),
        owner_scope_resolver=scope or (lambda _: ("business-1", "2026/27", "England")),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        clock=clock or (lambda: date(2027, 5, 20)),
    )
    return install_durable_paye_composition_endpoint(app, runtime)


def signed_client(app, owner):
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return client


def test_disabled_route_is_value_free_and_enablement_is_explicit(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    install(app, annual, repository)
    client = signed_client(app, owner)
    assert client.get("/v2/paye/current-position").status_code == 404
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    response = client.get("/v2/paye/current-position")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"tax_year", "paye_evidence_status", "tax_paid_known", "future_pay_status"}
    forbidden = {"payment", "refund", "reserve", "transfer", "action", "liability", "amount"}
    assert not forbidden.intersection(body)


def test_owner_and_year_scope_mismatches_and_cross_session_fail_closed(prepared, monkeypatch):
    app, owner, other, annual, repository, tmp_path = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    install(app, annual, repository)
    assert signed_client(app, other).get("/v2/paye/current-position").status_code == 403

    second_billing = billing_runtime(tmp_path / "second")
    app2 = create_app(billing_runtime=second_billing); app2.config.update(TESTING=True)
    paid_event(second_billing, owner)
    install(app2, annual, repository, scope=lambda _: ("business-1", "2025/26", "England"))
    assert signed_client(app2, owner).get("/v2/paye/current-position").status_code == 404


def test_unavailable_or_identity_mismatched_annual_provider_fails_closed(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    install(app, annual, repository, provider=lambda *_: None)
    assert signed_client(app, owner).get("/v2/paye/current-position").status_code == 404


def test_invalid_installation_leaves_flask_unmodified(prepared):
    app, _, _, annual, repository, _ = prepared
    before_rules = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules())
    before_extensions = dict(app.extensions)
    with pytest.raises(DurablePayeEndpointError):
        DurablePayeRuntime(
            repository=repository, annual_position_provider=lambda *_: annual,
            owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
            reconciliation_policy=object(),
            clock=lambda: date(2027, 5, 20),
        )
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == before_rules
    assert app.extensions == before_extensions


def test_duplicate_runtime_installation_is_refused_without_replacement(prepared):
    app, _, _, annual, repository, _ = prepared
    first = install(app, annual, repository)
    with pytest.raises(DurablePayeEndpointError):
        install(app, annual, repository)
    assert app.extensions["reserved.paye.durable_endpoint"] is first


def test_runtime_installation_without_active_paid_boundary_is_refused(prepared):
    _, _, _, annual, repository, _ = prepared
    app = create_app()
    runtime = DurablePayeRuntime(
        repository=repository,
        annual_position_provider=lambda *_: annual,
        owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        clock=lambda: date(2027, 5, 20),
    )
    with pytest.raises(DurablePayeEndpointError, match="paid-surface"):
        install_durable_paye_composition_endpoint(app, runtime)
    assert "reserved.paye.durable_endpoint" not in app.extensions


def test_expired_annual_position_is_not_presented_as_current(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    install(app, annual, repository, clock=lambda: date(2027, 5, 21))
    assert signed_client(app, owner).get("/v2/paye/current-position").status_code == 404
