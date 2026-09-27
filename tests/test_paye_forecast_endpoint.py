"""Hostile real-request coverage for the disabled current PAYE forecast read."""
from datetime import date
from decimal import Decimal

import pytest

import reserved.database as db
import reserved.paye_durable_forecast_bridge as forecast_bridge
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.paye_forecast_endpoint import (
    DurablePayeForecastEndpointError, install_durable_paye_forecast_endpoint,
)
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayFrequency, FuturePaySource,
    PeriodCompleteness, make_future_pay_forecast_policy,
)
from tests.test_paye_annual_bridge import durable_annual


TODAY = date(2026, 10, 1)


def _entry():
    return {
        "tax_year": "2026/27", "employment_slot": 1,
        "evidence_id": "paye-manual-00000000000000000000000000000001",
        "source_kind": "customer_confirmed_manual",
        "provenance": "customer_confirmed_manual_cumulative_entry",
        "gross_to_date": "10000.00", "tax_paid_to_date": "1200.00", "tax_code": "1257L",
        "pay_frequency": "monthly", "pension_treatment": "none",
        "effective_through": "2026-09-30", "observed_on": "2026-10-01",
        "completeness": "partial",
    }


def _fact(owner):
    return ConfirmedFuturePayFact(
        source=FuturePaySource.CUSTOMER_CONFIRMED, fact_id="future-pay-1",
        source_evidence_id="confirmation-1", source_evidence_digest="a" * 64,
        owner_id=str(owner), business_id="business-1", tax_year="2026-27",
        employment_id="manual-employment-1", gross_pay="5000.00",
        expected_tax_deduction="750.00", pay_date=date(2026, 10, 31),
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        confirmed_on=TODAY, frequency=FuturePayFrequency.MONTHLY,
        period_completeness=PeriodCompleteness.COMPLETE,
    )


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "forecast-endpoint.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("PAYE_DURABLE_FORECAST_ENABLED", raising=False)
    monkeypatch.setattr(forecast_bridge, "_server_date", lambda: TODAY)
    app = create_app(); app.config.update(TESTING=True)
    owner = db.get_or_create_user("forecast-owner", email="forecast@example.test")
    other = db.get_or_create_user("forecast-other", email="other@example.test")
    annual, repository = durable_annual(owner)
    db.save_paye_manual_entry(owner, _entry())
    return app, owner, other, annual, repository


def _install(app, annual, repository, *, scope=None, annual_provider=None, future_provider=None):
    return install_durable_paye_forecast_endpoint(
        app, repository=repository,
        annual_position_provider=annual_provider or (lambda *_: annual),
        future_facts_provider=future_provider or (lambda owner, *_: (_fact(owner),)),
        owner_scope_resolver=scope or (lambda _: ("business-1", "2026/27", "England")),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        future_pay_policy=make_future_pay_forecast_policy(30, Decimal("100.00")),
    )


def _client(app, owner):
    value = app.test_client()
    with value.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return value


def test_disabled_and_preflight_failures_do_not_call_providers(prepared, monkeypatch):
    app, owner, other, annual, repository = prepared
    calls = []
    _install(app, annual, repository,
             annual_provider=lambda *args: calls.append(("annual", args)) or annual,
             future_provider=lambda *args: calls.append(("future", args)) or (_fact(owner),))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    assert _client(app, other).get("/v2/paye/current-forecast").status_code == 404
    assert _client(app, owner).get("/v2/paye/current-forecast?year=2020").status_code == 404
    assert _client(app, owner).post("/v2/paye/current-forecast", json={}).status_code == 405
    assert calls == []
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    response = _client(app, owner).get("/v2/paye/current-forecast")
    assert response.status_code == 200
    assert [name for name, _ in calls] == ["annual", "future"]


def test_success_is_minimal_and_never_claims_liability_or_actions(prepared, monkeypatch):
    app, owner, _, annual, repository = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    _install(app, annual, repository)
    response = _client(app, owner).get("/v2/paye/current-forecast")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {
        "tax_year", "as_of", "forecast_status", "coverage_scope", "confirmed_fact_count",
        "reconciled_paye_tax_paid", "expected_future_tax_deduction",
        "projected_tax_deducted_total", "material_threshold_reached", "uncertainties",
    }
    assert body["tax_year"] == "2026-27"
    assert body["as_of"] == "2026-10-01"
    assert body["projected_tax_deducted_total"] == "1950.00"
    forbidden = {"owner", "business", "source", "provenance", "gross", "liability", "refund",
                 "reserve", "payment", "transfer", "filing", "action"}
    assert not forbidden.intersection(body)


def test_bad_scope_or_invalid_provider_output_is_value_free(prepared, monkeypatch):
    app, owner, _, annual, repository = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    _install(app, annual, repository, scope=lambda _: ("business-1", "2025/26", "England"))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    app2 = create_app(); app2.config.update(TESTING=True)
    _install(app2, annual, repository, future_provider=lambda *_: [])
    assert _client(app2, owner).get("/v2/paye/current-forecast").status_code == 404


def test_invalid_installation_does_not_mutate_flask(prepared):
    app, _, _, annual, repository = prepared
    rules, extensions = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()), dict(app.extensions)
    with pytest.raises(DurablePayeForecastEndpointError):
        install_durable_paye_forecast_endpoint(
            app, repository=repository, annual_position_provider=lambda *_: annual,
            future_facts_provider=lambda *_: (), owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
            reconciliation_policy=object(), future_pay_policy=object(),
        )
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == rules
    assert app.extensions == extensions
