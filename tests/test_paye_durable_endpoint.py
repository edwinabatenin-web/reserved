"""Real-request tests for disabled-first durable PAYE composition installation."""
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
from tests.test_paye_annual_bridge import durable_annual, entry


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "endpoint.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("PAYE_DURABLE_COMPOSITION_ENABLED", raising=False)
    app = create_app()
    app.config.update(TESTING=True)
    owner = db.get_or_create_user("endpoint-owner", email="endpoint@example.test")
    other = db.get_or_create_user("endpoint-other", email="other@example.test")
    annual, repository = durable_annual(owner)
    stored = entry(1, "1200.00", user_id=owner)
    stored.pop("user_id")
    db.save_paye_manual_entry(owner, stored)
    return app, owner, other, annual, repository


def install(app, annual, repository, scope=None, provider=None):
    runtime = DurablePayeRuntime(
        repository=repository,
        annual_position_provider=provider or (lambda *_: annual),
        owner_scope_resolver=scope or (lambda _: ("business-1", "2026/27", "England")),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
    )
    return install_durable_paye_composition_endpoint(app, runtime)


def signed_client(app, owner):
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return client


def test_disabled_route_is_value_free_and_enablement_is_explicit(prepared, monkeypatch):
    app, owner, _, annual, repository = prepared
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
    app, owner, other, annual, repository = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    install(app, annual, repository)
    assert signed_client(app, other).get("/v2/paye/current-position").status_code == 404

    app2 = create_app(); app2.config.update(TESTING=True)
    install(app2, annual, repository, scope=lambda _: ("business-1", "2025/26", "England"))
    assert signed_client(app2, owner).get("/v2/paye/current-position").status_code == 404


def test_unavailable_or_identity_mismatched_annual_provider_fails_closed(prepared, monkeypatch):
    app, owner, _, annual, repository = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    install(app, annual, repository, provider=lambda *_: None)
    assert signed_client(app, owner).get("/v2/paye/current-position").status_code == 404


def test_invalid_installation_leaves_flask_unmodified(prepared):
    app, _, _, annual, repository = prepared
    before_rules = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules())
    before_extensions = dict(app.extensions)
    with pytest.raises(DurablePayeEndpointError):
        DurablePayeRuntime(
            repository=repository, annual_position_provider=lambda *_: annual,
            owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
            reconciliation_policy=object(),
        )
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == before_rules
    assert app.extensions == before_extensions


def test_duplicate_runtime_installation_is_refused_without_replacement(prepared):
    app, _, _, annual, repository = prepared
    first = install(app, annual, repository)
    with pytest.raises(DurablePayeEndpointError):
        install(app, annual, repository)
    assert app.extensions["reserved.paye.durable_endpoint"] is first
