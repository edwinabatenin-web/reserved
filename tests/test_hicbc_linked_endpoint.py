"""Real-request tests for the disabled linked-HICBC HTTP adapter."""

from datetime import timedelta

import pytest

import reserved.database as db
import reserved.hicbc_linked_annual_composition as composition
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.hicbc_linked_endpoint import (
    LinkedHicbcEndpointError,
    LinkedHicbcRuntime,
    install_linked_hicbc_annual_endpoint,
)
from tests.test_annual_to_cash_integration import AS_OF
from tests.test_billing_composition import paid_event, runtime as billing_runtime
from tests.test_hicbc_linked_annual_composition import (
    NATION,
    OWNER_BUSINESS,
    YEAR,
    _prepared_linked_composition,
)


URL = "/v2/hicbc/linked-current-annual-position"


def _client(app, owner=None):
    client = app.test_client()
    if owner is not None:
        with client.session_transaction() as session:
            session[_SK_USER_ID] = owner
    return client


def _runtime(repository, source, *, owner_scope=None, owner_provider=None,
             partner_provider=None):
    return LinkedHicbcRuntime(
        repository=repository,
        owner_scope_resolver=owner_scope or (
            lambda owner: (OWNER_BUSINESS, YEAR, NATION)
        ),
        owner_annual_provider=owner_provider or (
            lambda owner, business, tax_year, nation:
            (source.annual_position, source.annual_tax_position)
        ),
        partner_annual_provider=partner_provider or (
            lambda partner, tax_year, nation:
            (source.annual_position, source.annual_tax_position)
        ),
    )


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    _raw, repository, source = _prepared_linked_composition(tmp_path, monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("HICBC_ENABLED", "1")
    monkeypatch.delenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", raising=False)
    billing = billing_runtime(tmp_path / "billing")
    return repository, source, billing


def test_default_off_then_paid_exact_request_returns_only_own_result(prepared, monkeypatch):
    repository, source, billing = prepared
    owner_calls, partner_calls = [], []
    runtime = _runtime(
        repository,
        source,
        owner_provider=lambda *args: (
            owner_calls.append(args) or (source.annual_position, source.annual_tax_position)
        ),
        partner_provider=lambda *args: (
            partner_calls.append(args) or (source.annual_position, source.annual_tax_position)
        ),
    )
    app = create_app(billing_runtime=billing, hicbc_linked_runtime=runtime)
    app.config.update(TESTING=True)
    paid_event(billing, 41)
    signed = _client(app, 41)
    assert signed.get(URL).status_code == 404
    assert owner_calls == [] and partner_calls == []

    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    response = signed.get(URL)
    assert response.status_code == 200
    assert response.get_json() == {
        "tax_year": YEAR,
        "calculation_status": "calculated",
        "responsibility_status": "person_liable",
        "projected_user_hicbc": "703.00",
        "possible_charge_low": "703.00",
        "possible_charge_high": "703.00",
    }
    assert owner_calls == [(41, OWNER_BUSINESS, YEAR, NATION)]
    assert partner_calls == [(42, YEAR, NATION)]
    assert "partner" not in repr(response.get_json()).casefold()


def test_paid_guard_auth_and_every_browser_selected_channel_precede_producers(
    prepared, monkeypatch,
):
    repository, source, billing = prepared
    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    calls = []
    runtime = _runtime(
        repository, source,
        owner_provider=lambda *args: calls.append(("owner", args)),
        partner_provider=lambda *args: calls.append(("partner", args)),
    )
    app = create_app(billing_runtime=billing, hicbc_linked_runtime=runtime)
    app.config.update(TESTING=True)
    assert _client(app).get(URL).status_code == 302
    assert _client(app, 41).get(URL).status_code == 403
    paid_event(billing, 41)
    signed = _client(app, 41)
    assert signed.get(URL, query_string={"partner": "42"}).status_code == 404
    assert signed.open(URL, method="GET", data=b"business=other").status_code == 404
    assert signed.post(URL, json={"tax_year": YEAR}).status_code == 405
    assert calls == []


def test_partner_producer_runs_only_after_current_link_permission(prepared, monkeypatch):
    repository, source, billing = prepared
    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    paid_event(billing, 41)
    owner_calls, partner_calls = [], []
    runtime = _runtime(
        repository, source,
        owner_provider=lambda *args: (
            owner_calls.append(args) or (source.annual_position, source.annual_tax_position)
        ),
        partner_provider=lambda *args: (
            partner_calls.append(args) or (source.annual_position, source.annual_tax_position)
        ),
    )
    app = create_app(billing_runtime=billing, hicbc_linked_runtime=runtime)
    app.config.update(TESTING=True)
    assert db.revoke_hicbc_link(42, YEAR)
    response = _client(app, 41).get(URL)
    assert response.status_code == 200
    assert response.get_json() == {
        "tax_year": YEAR,
        "calculation_status": "insufficient_facts",
        "responsibility_status": None,
        "projected_user_hicbc": None,
        "possible_charge_low": None,
        "possible_charge_high": None,
    }
    assert owner_calls == [] and partner_calls == []


def test_stale_and_revoked_states_share_the_same_unavailable_projection(
    prepared, monkeypatch,
):
    repository, source, billing = prepared
    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    paid_event(billing, 41)
    app = create_app(
        billing_runtime=billing,
        hicbc_linked_runtime=_runtime(repository, source),
    )
    app.config.update(TESTING=True)
    monkeypatch.setattr(composition, "_server_date", lambda: AS_OF + timedelta(days=46))
    stale = _client(app, 41).get(URL)
    assert stale.status_code == 200
    assert db.revoke_hicbc_link(42, YEAR)
    revoked = _client(app, 41).get(URL)
    assert revoked.status_code == 200
    assert stale.get_json() == revoked.get_json()


def test_malformed_partner_source_uses_the_same_value_free_projection(
    prepared, monkeypatch,
):
    repository, source, billing = prepared
    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    paid_event(billing, 41)
    app = create_app(
        billing_runtime=billing,
        hicbc_linked_runtime=_runtime(
            repository, source, partner_provider=lambda *_: object(),
        ),
    )
    app.config.update(TESTING=True)
    response = _client(app, 41).get(URL)
    assert response.status_code == 200
    assert response.get_json() == {
        "tax_year": YEAR,
        "calculation_status": "insufficient_facts",
        "responsibility_status": None,
        "projected_user_hicbc": None,
        "possible_charge_low": None,
        "possible_charge_high": None,
    }


def test_production_and_failed_install_never_execute_sources(prepared, monkeypatch):
    repository, source, billing = prepared
    calls = []
    runtime = _runtime(
        repository, source,
        owner_provider=lambda *args: calls.append(("owner", args)),
        partner_provider=lambda *args: calls.append(("partner", args)),
    )
    monkeypatch.setenv("HICBC_LINKED_DURABLE_ANNUAL_ENABLED", "1")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "synthetic-test-secret")
    app = create_app(billing_runtime=billing, hicbc_linked_runtime=runtime)
    app.config.update(TESTING=True)
    paid_event(billing, 41)
    assert _client(app, 41).get(URL).status_code == 404
    assert calls == []

    monkeypatch.setenv("FLASK_ENV", "development")
    no_billing = create_app(hicbc_linked_runtime=runtime)
    no_billing.config.update(TESTING=True)
    assert _client(no_billing, 41).get(URL).status_code == 404
    assert calls == []


def test_installer_rejects_missing_paid_wrapper_without_partial_mutation(prepared):
    repository, source, _billing = prepared
    app = create_app()
    app.config.update(TESTING=True)
    before = dict(app.extensions)
    with pytest.raises(LinkedHicbcEndpointError, match="paid-surface"):
        install_linked_hicbc_annual_endpoint(app, _runtime(repository, source))
    assert "reserved.hicbc.linked_annual_endpoint" not in app.extensions
    assert app.extensions == before
