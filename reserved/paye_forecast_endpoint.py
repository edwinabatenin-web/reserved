"""Disabled-first authenticated durable PAYE confirmed-future-pay read.

This installer has no provider integration, network access, UI, credential,
payment, refund or filing authority.  Composition injects all trusted inputs;
the browser supplies no owner, scope, date, annual position or future facts.
"""
from __future__ import annotations

from flask import Flask, abort, jsonify, request

from reserved.auth import require_auth
from reserved.config import durable_paye_forecast_enabled
from reserved.engines.annual_to_cash_integration import AnnualToCashPosition
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashStatus, annual_to_cash_position_identity,
)
from reserved.engines.paye_reconciliation import PayeReconciliationPolicy
from reserved.paye_durable_forecast_bridge import (
    compose_durable_authenticated_paye_forecast,
)
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayForecastPolicy,
    project_paye_future_pay_forecast,
)

_KEY = "reserved.paye.durable_forecast_endpoint"
_RULE = "/v2/paye/current-forecast"
_ENDPOINT = "paye_durable_current_forecast"


class DurablePayeForecastEndpointError(ValueError):
    """Installer validation failed before any Flask mutation."""


class DurablePayeForecastEndpointHandle:
    __slots__ = ()

    def __new__(cls):
        raise TypeError("durable PAYE forecast endpoint handles are installer-issued only")


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if (type(business) is not str or not business or type(tax_year) is not str
            or len(tax_year) != 7 or tax_year[4] != "/"
            or type(nation) is not str or not nation):
        return None
    return business, tax_year, nation


def _response(forecast):
    values = dict(project_paye_future_pay_forecast(forecast))
    return {
        "tax_year": values["tax_year"],
        "as_of": values["as_of"].isoformat(),
        "forecast_status": values["forecast_status"],
        "coverage_scope": values["coverage_scope"],
        "confirmed_fact_count": values["fact_count"],
        "reconciled_paye_tax_paid": f"{values['reconciled_tax_paid_to_date']:.2f}",
        "expected_future_tax_deduction": f"{values['expected_future_tax_deduction']:.2f}",
        "projected_tax_deducted_total": f"{values['projected_tax_deducted_total']:.2f}",
        "material_threshold_reached": values["material_threshold_reached"],
        "uncertainties": list(values["uncertainties"]),
    }


def _preflight_annual_matches_current_durable_record(record, annual, *, owner, business, tax_year, nation):
    """Bind the provider-issued annual input before any future-facts call."""
    from reserved.annual_position_repository_contract import project_annual_position_record

    if (type(annual) is not AnnualToCashPosition
            or annual.status is not AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
            or annual.tax_year != tax_year or annual.nation != nation
            or "annual_liability_is_local_estimate_not_hmrc_issued" not in annual.limitations):
        raise ValueError("live annual input is unavailable")
    row = dict(project_annual_position_record(record)[2])
    if (row.get("user_id") != str(owner) or row.get("business_id") != business
            or row.get("tax_year") != tax_year or row.get("nation") != nation
            or row.get("annual_cash_identity") != annual_to_cash_position_identity(annual)):
        raise ValueError("live annual input is not current durable issuance")


def install_durable_paye_forecast_endpoint(
    app: Flask, *, repository, annual_position_provider, future_facts_provider,
    owner_scope_resolver, reconciliation_policy, future_pay_policy,
):
    """Install a GET-only forecast endpoint after complete dependency preflight."""
    from reserved.annual_position_durable_repository import DurableAnnualPositionRepository, RECORD_PURPOSE

    if type(app) is not Flask or app._got_first_request or _KEY in app.extensions:
        raise DurablePayeForecastEndpointError("exact pre-request Flask installation is required")
    if type(repository) is not DurableAnnualPositionRepository:
        raise DurablePayeForecastEndpointError("exact durable repository is required")
    if not all(callable(value) for value in (annual_position_provider, future_facts_provider, owner_scope_resolver)):
        raise DurablePayeForecastEndpointError("explicit annual, future-facts and scope dependencies are required")
    if type(reconciliation_policy) is not PayeReconciliationPolicy or type(future_pay_policy) is not FuturePayForecastPolicy:
        raise DurablePayeForecastEndpointError("exact reconciliation and future-pay policies are required")
    if _ENDPOINT in app.view_functions or any(rule.rule == _RULE for rule in app.url_map.iter_rules()):
        raise DurablePayeForecastEndpointError("PAYE forecast endpoint registration is ambiguous")

    @require_auth
    def current_forecast():
        if (not durable_paye_forecast_enabled() or request.args
                or request.content_length not in (None, 0)):
            abort(404)
        from reserved.auth import current_user_id
        try:
            owner = current_user_id()
            if type(owner) is not int or owner <= 0:
                raise ValueError
            scope = _scope(owner_scope_resolver(owner))
            if scope is None:
                raise ValueError
            business, tax_year, nation = scope
            # Provider calls are gated behind current verifier/membership/record.
            repository.assert_external_authority_available()
            record = repository.read_current(
                authenticated_user_id=owner, business_reference=business,
                tax_year=tax_year, nation=nation, record_purpose=RECORD_PURPOSE,
                audit_reference="audit:paye-forecast-preflight",
            )
            annual = annual_position_provider(owner, business, tax_year, nation)
            _preflight_annual_matches_current_durable_record(
                record, annual, owner=owner, business=business, tax_year=tax_year, nation=nation,
            )
            facts = future_facts_provider(owner, business, tax_year, nation, annual)
            if (type(facts) is not tuple or not facts
                    or any(type(item) is not ConfirmedFuturePayFact for item in facts)):
                raise ValueError
            result = compose_durable_authenticated_paye_forecast(
                repository=repository, annual_position=annual,
                business_reference=business, tax_year=tax_year, nation=nation,
                reconciliation_policy=reconciliation_policy,
                future_pay_facts=facts, future_pay_policy=future_pay_policy,
                audit_reference="audit:paye-forecast-current",
            )
            payload = _response(result.forecast)
        except Exception:
            abort(404)
        return jsonify(payload)

    app.add_url_rule(_RULE, endpoint=_ENDPOINT, view_func=current_forecast, methods=("GET",))
    handle = object.__new__(DurablePayeForecastEndpointHandle)
    app.extensions[_KEY] = handle
    return handle
