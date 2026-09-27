"""Real-request tests for the disabled-first durable HICBC installer."""

import pytest

import reserved.database as db
import reserved.hicbc_durable_annual_bridge as bridge
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.annual_position_durable_repository import DurableAnnualPositionRepository
from reserved.hicbc_durable_endpoint import (
    DurableHicbcEndpointError, DurableHicbcRuntime,
    install_durable_hicbc_annual_endpoint,
)
from tests.test_annual_position_durable_repository import _governance, _policy
from tests.test_hicbc_durable_annual_bridge import BUSINESS, NATION, YEAR, _durable, _seed
from tests.test_billing_composition import paid_event, runtime as billing_runtime


URL = "/v2/hicbc/current-annual-position"


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "hicbc-endpoint.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("HICBC_ENABLED", "1")
    monkeypatch.delenv("HICBC_DURABLE_ANNUAL_ENABLED", raising=False)
    monkeypatch.setattr(bridge, "_server_date", lambda: __import__("datetime").date(2027, 4, 5))
    billing = billing_runtime(tmp_path / "billing-primary")
    app = create_app(billing_runtime=billing)
    app.config.update(TESTING=True)
    with db._connection() as conn:
        for user_id in (41, 42):
            conn.execute(
                "INSERT INTO users (id,clerk_user_id,created_at) VALUES (?,?,?)",
                (user_id, f"endpoint-{user_id}", "2026-09-27T00:00:00+00:00"),
            )
    tax, annual, repository = _durable(41)
    _seed(41)
    paid_event(billing, 41)
    return app, tax, annual, repository, tmp_path


def install(app, tax, annual, repository, *, scope=None, provider=None):
    runtime = DurableHicbcRuntime(
        repository=repository,
        owner_scope_resolver=scope or (lambda _: (BUSINESS, YEAR, NATION)),
        live_annual_provider=provider or (lambda *_: (annual, tax)),
    )
    return install_durable_hicbc_annual_endpoint(app, runtime)


def paid_app(tmp_path, name, owner):
    billing = billing_runtime(tmp_path / name)
    app = create_app(billing_runtime=billing)
    app.config.update(TESTING=True)
    paid_event(billing, owner)
    return app


def client(app, owner=None):
    value = app.test_client()
    if owner is not None:
        with value.session_transaction() as session:
            session[_SK_USER_ID] = owner
    return value


def _null_numbers(body):
    return all(body[key] is None for key in (
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    ))


def test_exact_switch_is_independent_and_minimal(prepared, monkeypatch):
    app, tax, annual, repository, _ = prepared
    monkeypatch.setenv("HICBC_ENABLED", "1")
    install(app, tax, annual, repository)
    signed = client(app, 41)
    assert signed.get(URL).status_code == 404
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    response = signed.get(URL)
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {
        "tax_year", "calculation_status", "responsibility_status",
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    }
    assert not {"payment", "refund", "reserve", "transfer", "filing", "action", "source"} & set(body)


def test_auth_owner_scope_and_client_controlled_channels_fail_closed(prepared, monkeypatch):
    app, tax, annual, repository, _ = prepared
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    install(app, tax, annual, repository)
    assert client(app).get(URL).status_code == 302
    assert client(app, 42).get(URL).status_code == 403
    signed = client(app, 41)
    assert signed.get(URL, query_string={"tax_year": "2025/26"}).status_code == 404
    assert signed.open(URL, method="GET", data=b"owner=42").status_code == 404


def test_provider_runs_only_after_durable_authority_and_current_record_preflight(prepared, monkeypatch):
    app, tax, annual, repository, tmp_path = prepared
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    calls = []

    def provider(*args):
        calls.append(args)
        return annual, tax

    install(app, tax, annual, repository, provider=provider)
    assert client(app).get(URL).status_code == 302
    assert client(app, 42).get(URL).status_code == 403
    signed = client(app, 41)
    assert signed.get(URL, query_string={"owner": "42"}).status_code == 404
    assert signed.open(URL, method="GET", data=b"x=1").status_code == 404
    assert calls == []
    assert signed.get(URL).status_code == 200
    assert calls == [(41, BUSINESS, YEAR, NATION)]

    app2 = paid_app(tmp_path, "billing-no-adapter", 41)
    no_adapter = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
        external_authority_adapter=None,
    )
    no_adapter_calls = []
    install(app2, tax, annual, no_adapter, provider=lambda *args: no_adapter_calls.append(args))
    assert client(app2, 41).get(URL).status_code == 404
    assert no_adapter_calls == []

    app3 = paid_app(tmp_path, "billing-invalid-scope", 41)
    invalid_scope_calls = []
    install(
        app3, tax, annual, repository, scope=lambda _: None,
        provider=lambda *args: invalid_scope_calls.append(args),
    )
    assert client(app3, 41).get(URL).status_code == 404
    assert invalid_scope_calls == []

    monkeypatch.delenv("HICBC_DURABLE_ANNUAL_ENABLED", raising=False)
    app4 = paid_app(tmp_path, "billing-disabled", 41)
    disabled_calls = []
    install(app4, tax, annual, repository, provider=lambda *args: disabled_calls.append(args))
    assert client(app4, 41).get(URL).status_code == 404
    assert disabled_calls == []


def test_unavailable_scope_provider_no_adapter_and_invalid_install_leave_no_route(prepared, monkeypatch):
    app, tax, annual, repository, tmp_path = prepared
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    install(app, tax, annual, repository, scope=lambda _: (BUSINESS, "2025/26", NATION))
    assert client(app, 41).get(URL).status_code == 404

    app2 = paid_app(tmp_path, "billing-unavailable-no-adapter", 41)
    no_adapter = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
        external_authority_adapter=None,
    )
    install(app2, tax, annual, no_adapter)
    assert client(app2, 41).get(URL).status_code == 404

    app3 = create_app(); app3.config.update(TESTING=True)
    before_rules = tuple((rule.rule, rule.endpoint) for rule in app3.url_map.iter_rules())
    before_extensions = dict(app3.extensions)
    with pytest.raises(DurableHicbcEndpointError):
        DurableHicbcRuntime(
            repository=repository, owner_scope_resolver=object(),
            live_annual_provider=lambda *_: (annual, tax),
        )
    assert tuple((rule.rule, rule.endpoint) for rule in app3.url_map.iter_rules()) == before_rules
    assert app3.extensions == before_extensions


def test_stale_uncertain_and_active_link_return_minimal_null_preview(prepared, monkeypatch):
    app, tax, annual, repository, _ = prepared
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    install(app, tax, annual, repository)
    signed = client(app, 41)
    _seed(41, representation="range", partner_ani_point=None,
          partner_ani_low="65000", partner_ani_high="75000")
    response = signed.get(URL)
    assert response.status_code == 200 and _null_numbers(response.get_json())

    _seed(41)
    token = db.create_hicbc_link_invitation(41, YEAR)
    assert db.accept_hicbc_link_invitation(42, token, YEAR) is not None
    assert db.record_hicbc_link_consent(41, YEAR, db.HICBC_NOTICE_VERSION)
    assert db.record_hicbc_link_consent(42, YEAR, db.HICBC_NOTICE_VERSION)
    response = signed.get(URL)
    assert response.status_code == 200 and _null_numbers(response.get_json())

    assert db.revoke_hicbc_link(42, YEAR)
    monkeypatch.setattr(bridge, "_server_date", lambda: annual.as_of.fromordinal(annual.as_of.toordinal() + 46))
    response = signed.get(URL)
    assert response.status_code == 200 and _null_numbers(response.get_json())


def test_application_factory_requires_billing_and_composes_exact_runtime(prepared, monkeypatch):
    _app, tax, annual, repository, tmp_path = prepared
    monkeypatch.setenv("HICBC_DURABLE_ANNUAL_ENABLED", "1")
    monkeypatch.setenv("HICBC_ENABLED", "1")
    runtime = DurableHicbcRuntime(
        repository=repository,
        owner_scope_resolver=lambda _: (BUSINESS, YEAR, NATION),
        live_annual_provider=lambda *_: (annual, tax),
    )

    closed = create_app(hicbc_runtime=runtime)
    closed.config.update(TESTING=True)
    assert client(closed, 41).get(URL).status_code == 404

    invalid_billing = create_app(billing_runtime=object(), hicbc_runtime=runtime)
    invalid_billing.config.update(TESTING=True)
    assert client(invalid_billing, 41).get(URL).status_code == 404

    billing = billing_runtime(tmp_path / "billing-factory")
    composed = create_app(billing_runtime=billing, hicbc_runtime=runtime)
    composed.config.update(TESTING=True)
    signed = client(composed, 41)
    assert signed.get(URL).status_code == 403
    paid_event(billing, 41)
    response = signed.get(URL)
    assert response.status_code == 200
    assert set(response.get_json()) == {
        "tax_year", "calculation_status", "responsibility_status",
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    }
