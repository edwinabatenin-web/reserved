"""Deterministic current-date coverage for the durable PAYE forecast bridge."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

import reserved.auth as auth
import reserved.database as db
import reserved.paye_durable_forecast_bridge as bridge
from reserved.engines.annual_to_cash_integration import AnnualToCashStatus
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayFrequency, FuturePaySource,
    PeriodCompleteness, make_future_pay_forecast_policy,
)
from tests.test_paye_annual_bridge import durable_annual
from tests.test_paye_annual_bridge import app as app_fixture


OBSERVED = date(2026, 10, 1)
RECONCILIATION_POLICY = make_paye_reconciliation_policy(45, Decimal("1.00"))
FORECAST_POLICY = make_future_pay_forecast_policy(30, Decimal("100.00"))


@pytest.fixture
def app(tmp_path, monkeypatch):
    return app_fixture.__wrapped__(tmp_path, monkeypatch)


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


def _fact(owner=41, **changes):
    values = {
        "source": FuturePaySource.CUSTOMER_CONFIRMED,
        "fact_id": "future-pay-1", "source_evidence_id": "confirmation-1",
        "source_evidence_digest": "a" * 64, "owner_id": str(owner),
        "business_id": "business-1", "tax_year": "2026-27",
        "employment_id": "manual-employment-1", "gross_pay": "5000.00",
        "expected_tax_deduction": "750.00", "pay_date": date(2026, 10, 31),
        "period_start": date(2026, 10, 2), "period_end": date(2026, 10, 31),
        "confirmed_on": OBSERVED, "frequency": FuturePayFrequency.MONTHLY,
        "period_completeness": PeriodCompleteness.COMPLETE,
    }
    values.update(changes)
    return ConfirmedFuturePayFact(**values)


def _compose(app, monkeypatch, *, today=OBSERVED, facts=None):
    annual, repository = durable_annual(41)
    db.save_paye_manual_entry(41, _entry())
    monkeypatch.setattr(bridge, "_server_date", lambda: today)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        return bridge.compose_durable_authenticated_paye_forecast(
            repository=repository, annual_position=annual, business_reference="business-1",
            tax_year="2026/27", nation="England", audit_reference="audit:paye-forecast-test",
            reconciliation_policy=RECONCILIATION_POLICY,
            future_pay_facts=tuple(facts or (_fact(),)), future_pay_policy=FORECAST_POLICY,
        )


def test_in_year_observation_composes_earlier_paye_evidence_and_later_confirmed_pay(app, monkeypatch):
    result = _compose(app, monkeypatch)
    assert result.forecast.reconciled_tax_paid_to_date == Decimal("1200.00")
    assert result.forecast.expected_future_tax_deduction == Decimal("750.00")


@pytest.mark.parametrize("today", [date(2026, 4, 5), date(2027, 4, 5), date(2027, 4, 6)])
def test_outside_or_at_period_end_is_suppressed(app, monkeypatch, today):
    with pytest.raises(ValueError):
        _compose(app, monkeypatch, today=today)


def test_date_change_during_composition_is_suppressed(app, monkeypatch):
    values = iter((OBSERVED, date(2026, 10, 2)))
    monkeypatch.setattr(bridge, "_server_date", lambda: next(values))
    annual, repository = durable_annual(41)
    db.save_paye_manual_entry(41, _entry())
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="changed"):
            bridge.compose_durable_authenticated_paye_forecast(
                repository=repository, annual_position=annual, business_reference="business-1",
                tax_year="2026/27", nation="England", audit_reference="audit:paye-forecast-test",
                reconciliation_policy=RECONCILIATION_POLICY, future_pay_facts=(_fact(),),
                future_pay_policy=FORECAST_POLICY,
            )


def test_future_or_stale_paye_evidence_is_suppressed(app, monkeypatch):
    annual, repository = durable_annual(41)
    entry = _entry()
    entry["observed_on"] = "2026-11-15"
    entry["effective_through"] = "2026-11-15"
    db.save_paye_manual_entry(41, entry)
    monkeypatch.setattr(bridge, "_server_date", lambda: OBSERVED)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError):
            bridge.compose_durable_authenticated_paye_forecast(
                repository=repository, annual_position=annual, business_reference="business-1",
                tax_year="2026/27", nation="England", audit_reference="audit:paye-forecast-test",
                reconciliation_policy=RECONCILIATION_POLICY, future_pay_facts=(_fact(),),
                future_pay_policy=FORECAST_POLICY,
            )


def test_nonqualified_or_double_counted_source_misrepresentation_is_suppressed(app, monkeypatch):
    annual, repository = durable_annual(41)
    db.save_paye_manual_entry(41, _entry())
    monkeypatch.setattr(bridge, "_server_date", lambda: OBSERVED)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        # A current-observation/HMRC-final implication is not admitted here.
        with pytest.raises(ValueError):
            bridge.compose_durable_authenticated_paye_forecast(
                repository=repository,
                annual_position=replace(annual, status=AnnualToCashStatus.CALCULATED),
                business_reference="business-1", tax_year="2026/27", nation="England",
                audit_reference="audit:paye-forecast-test", reconciliation_policy=RECONCILIATION_POLICY,
                future_pay_facts=(_fact(),), future_pay_policy=FORECAST_POLICY,
            )
        # A future fact cannot reuse selected PAYE evidence provenance.
        with pytest.raises(ValueError):
            bridge.compose_durable_authenticated_paye_forecast(
                repository=repository, annual_position=annual, business_reference="business-1",
                tax_year="2026/27", nation="England", audit_reference="audit:paye-forecast-test",
                reconciliation_policy=RECONCILIATION_POLICY,
                future_pay_facts=(_fact(source_evidence_id="paye-manual-00000000000000000000000000000001"),),
                future_pay_policy=FORECAST_POLICY,
            )
