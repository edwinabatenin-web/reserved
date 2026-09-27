"""Disabled-first authenticated durable PAYE confirmed-future-pay read.

This installer has no provider integration, network access, UI, credential,
payment, refund or filing authority.  Composition injects all trusted inputs;
the browser supplies no owner, scope, date, annual position or future facts.
"""
from __future__ import annotations

from dataclasses import dataclass

from flask import Flask

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
_ENDPOINT = "v2.paye_durable_current_forecast"


class DurablePayeForecastEndpointError(ValueError):
    """Installer validation failed before any Flask mutation."""


@dataclass(frozen=True, slots=True)
class DurablePayeForecastRuntime:
    """Complete server-owned dependencies for the forecast route."""

    repository: object
    annual_position_provider: object
    future_facts_provider: object
    owner_scope_resolver: object
    reconciliation_policy: object
    future_pay_policy: object

    def __post_init__(self):
        from reserved.annual_position_durable_repository import DurableAnnualPositionRepository

        if type(self.repository) is not DurableAnnualPositionRepository:
            raise DurablePayeForecastEndpointError("exact durable repository is required")
        if not all(callable(value) for value in (
            self.annual_position_provider, self.future_facts_provider,
            self.owner_scope_resolver,
        )):
            raise DurablePayeForecastEndpointError(
                "explicit annual, future-facts and scope dependencies are required"
            )
        if (type(self.reconciliation_policy) is not PayeReconciliationPolicy
                or type(self.future_pay_policy) is not FuturePayForecastPolicy):
            raise DurablePayeForecastEndpointError(
                "exact reconciliation and future-pay policies are required"
            )


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


def current_forecast_payload(runtime: DurablePayeForecastRuntime, owner: int) -> dict:
    """Compose the bounded response from exact server-owned dependencies."""
    from reserved.annual_position_durable_repository import RECORD_PURPOSE

    if type(runtime) is not DurablePayeForecastRuntime or type(owner) is not int or owner <= 0:
        raise DurablePayeForecastEndpointError("durable PAYE forecast runtime is unavailable")
    scope = _scope(runtime.owner_scope_resolver(owner))
    if scope is None:
        raise DurablePayeForecastEndpointError("owner scope is unavailable")
    business, tax_year, nation = scope
    runtime.repository.assert_external_authority_available()
    record = runtime.repository.read_current(
        authenticated_user_id=owner, business_reference=business,
        tax_year=tax_year, nation=nation, record_purpose=RECORD_PURPOSE,
        audit_reference="audit:paye-forecast-preflight",
    )
    annual = runtime.annual_position_provider(owner, business, tax_year, nation)
    _preflight_annual_matches_current_durable_record(
        record, annual, owner=owner, business=business, tax_year=tax_year, nation=nation,
    )
    facts = runtime.future_facts_provider(owner, business, tax_year, nation, annual)
    if (type(facts) is not tuple or not facts
            or any(type(item) is not ConfirmedFuturePayFact for item in facts)):
        raise DurablePayeForecastEndpointError("future-pay facts are unavailable")
    result = compose_durable_authenticated_paye_forecast(
        repository=runtime.repository, annual_position=annual,
        business_reference=business, tax_year=tax_year, nation=nation,
        reconciliation_policy=runtime.reconciliation_policy,
        future_pay_facts=facts, future_pay_policy=runtime.future_pay_policy,
        audit_reference="audit:paye-forecast-current",
    )
    return _response(result.forecast)


def install_durable_paye_forecast_endpoint(
    app: Flask, runtime: DurablePayeForecastRuntime,
):
    """Bind complete dependencies to the pre-registered, paid-only route."""

    if (type(app) is not Flask or app._got_first_request or _KEY in app.extensions
            or type(runtime) is not DurablePayeForecastRuntime):
        raise DurablePayeForecastEndpointError("exact pre-request Flask installation is required")
    rules = tuple(
        rule for rule in app.url_map.iter_rules()
        if rule.endpoint == _ENDPOINT or rule.rule == _RULE
    )
    if (len(rules) != 1 or rules[0].endpoint != _ENDPOINT or rules[0].rule != _RULE
            or rules[0].methods != {"GET", "HEAD", "OPTIONS"}):
        raise DurablePayeForecastEndpointError("PAYE forecast endpoint registration is ambiguous")
    from reserved.billing.stripe_runtime import StripeBillingRuntime

    billing_key = "reserved.billing.stripe_runtime"
    originals = app.extensions.get(billing_key + ".paid_surface.disabled")
    guarded = app.view_functions.get(_ENDPOINT)
    if (
        type(app.extensions.get(billing_key)) is not StripeBillingRuntime
        or app.extensions.get(billing_key + ".paid_surface") is not True
        or type(originals) is not dict
        or _ENDPOINT not in originals
        or not callable(originals[_ENDPOINT])
        or not callable(guarded)
        or getattr(guarded, "__wrapped__", None) is not originals[_ENDPOINT]
    ):
        raise DurablePayeForecastEndpointError(
            "active exact paid-surface enforcement is required"
        )
    app.extensions[_KEY] = runtime
    return runtime


__all__ = [
    "DurablePayeForecastEndpointError", "DurablePayeForecastRuntime",
    "current_forecast_payload", "install_durable_paye_forecast_endpoint",
]
