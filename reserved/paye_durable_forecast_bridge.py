"""Current, owner-bound PAYE forecast composition.

The annual-to-cash position remains the qualified local annual estimate used
solely as the reconciliation bound. It is not a final HMRC liability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from decimal import Decimal

from reserved.annual_position_durable_repository import (
    DurableAnnualPositionRepository, RECORD_PURPOSE, project_durable_paye_snapshot,
)
from reserved.annual_position_repository_contract import project_annual_position_record
from reserved.billing.event_inbox_contract import canonical_owner_id_from_users_id
from reserved.engines.annual_to_cash_integration import AnnualToCashPosition, AnnualToCashStatus, annual_to_cash_position_identity
from reserved.engines.paye_reconciliation import (
    PayeReconciliation, PayeReconciliationPolicy, reconcile_paye,
)
from reserved.paye_annual_bridge import _engine_tax_year, _manual_evidence
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayForecastPolicy, PayeFuturePayForecast,
    compose_paye_future_pay_forecast,
)

@dataclass(frozen=True)
class DurablePayeForecast:
    reconciliation: PayeReconciliation
    forecast: PayeFuturePayForecast


def _server_date() -> date:
    """The only forecast observation clock; never supplied by a request."""
    return date.today()


def _tax_year_bounds(value: object) -> tuple[date, date]:
    if (type(value) is not str or len(value) != 7 or value[4] != "/"
            or not value[:4].isdigit() or not value[5:].isdigit()):
        raise ValueError("durable forecast tax year is unavailable")
    start = int(value[:4])
    if int(value[5:]) != (start + 1) % 100:
        raise ValueError("durable forecast tax year is unavailable")
    return date(start, 4, 6), date(start + 1, 4, 5)


def compose_durable_authenticated_paye_forecast(
    *, repository: DurableAnnualPositionRepository, annual_position: AnnualToCashPosition,
    business_reference: str, tax_year: str, nation: str,
    reconciliation_policy: PayeReconciliationPolicy,
    future_pay_facts: tuple[ConfirmedFuturePayFact, ...],
    future_pay_policy: FuturePayForecastPolicy, audit_reference: str,
) -> DurablePayeForecast:
    """Compose after a final serialised durable PAYE snapshot.

    The endpoint preflight avoids provider work for an unauthorised request;
    this function repeats the authority/current-record check after providers
    return, closing the revocation race.
    """
    from reserved.auth import current_user_id
    if (type(repository) is not DurableAnnualPositionRepository
            or type(annual_position) is not AnnualToCashPosition
            or type(reconciliation_policy) is not PayeReconciliationPolicy
            or type(future_pay_policy) is not FuturePayForecastPolicy):
        raise TypeError("exact durable forecast dependencies are required")
    repository.assert_external_authority_available()
    owner = current_user_id()
    if (type(owner) is not int or owner <= 0 or type(business_reference) is not str
            or not business_reference or type(nation) is not str or not nation
            or annual_position.status is not AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
            or annual_position.tax_year != tax_year or annual_position.nation != nation
            or type(annual_position.final_self_assessment_liability) is not Decimal
            # This binding is deliberately to the local full-year estimate, not
            # an asserted current observation or an HMRC-issued final figure.
            or "annual_liability_is_local_estimate_not_hmrc_issued"
            not in annual_position.limitations):
        raise ValueError("durable forecast scope is unavailable")
    first, end = _tax_year_bounds(tax_year)
    observed_on = _server_date()
    # The annual period-end date is not a live observation point.
    if type(observed_on) is not date or not first <= observed_on < end:
        raise ValueError("server forecast date is unavailable")
    if (type(future_pay_facts) is not tuple or not future_pay_facts
            or any(type(item) is not ConfirmedFuturePayFact for item in future_pay_facts)):
        raise ValueError("confirmed future facts are unavailable")
    snapshot = repository.read_current_paye_snapshot(
        authenticated_user_id=owner, business_reference=business_reference,
        tax_year=tax_year, nation=nation, record_purpose=RECORD_PURPOSE,
        audit_reference=audit_reference,
    )
    record, entries = project_durable_paye_snapshot(
        snapshot, authenticated_user_id=owner, business_reference=business_reference,
        tax_year=tax_year, nation=nation,
    )
    row = dict(project_annual_position_record(record)[2])
    if (row.get("user_id") != canonical_owner_id_from_users_id(owner)
            or row.get("business_id") != business_reference
            or row.get("tax_year") != tax_year or row.get("nation") != nation
            or row.get("record_purpose") != RECORD_PURPOSE
            or row.get("annual_cash_identity")
            != annual_to_cash_position_identity(annual_position)):
        raise ValueError("durable annual identity is unavailable")
    engine_tax_year = _engine_tax_year(tax_year)
    reconciliation = reconcile_paye(
        annual_position.final_self_assessment_liability,
        _manual_evidence(entries, engine_tax_year=engine_tax_year,
                         authenticated_owner_user_id=owner),
        tax_year=engine_tax_year, as_of=observed_on, policy=reconciliation_policy,
    )
    forecast = compose_paye_future_pay_forecast(
        reconciliation, future_pay_facts,
        owner_id=canonical_owner_id_from_users_id(owner), business_id=business_reference,
        tax_year=engine_tax_year, as_of=observed_on, policy=future_pay_policy,
    )
    if _server_date() != observed_on:
        raise ValueError("server forecast date changed during composition")
    return DurablePayeForecast(reconciliation=reconciliation, forecast=forecast)
