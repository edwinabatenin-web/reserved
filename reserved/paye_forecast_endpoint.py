"""Disabled-first authenticated durable PAYE confirmed-future-pay boundary.

This installer has no provider integration, network access, credential,
payment, refund or filing authority. Composition injects all trusted scope;
the customer may supply only the approved minimum confirmed-period fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import re

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
_MONEY = re.compile(r"^(?:0|[1-9][0-9]{0,18})(?:\.[0-9]{1,2})?$")
_FUTURE_EMPLOYMENT_SOURCE = re.compile(
    r"^future-source:employment-([1-9]|1[0-9]|20)$"
)


class DurablePayeForecastEndpointError(ValueError):
    """Installer validation failed before any Flask mutation."""


@dataclass(frozen=True, slots=True)
class RepositoryFuturePayFactsProvider:
    """Read only customer-confirmed periods from the bound durable repository."""

    repository: object

    def __post_init__(self):
        from reserved.annual_position_durable_repository import DurableAnnualPositionRepository
        if type(self.repository) is not DurableAnnualPositionRepository:
            raise DurablePayeForecastEndpointError("exact durable repository is required")

    def __call__(self, owner, business, tax_year, nation, annual):
        return self.repository.read_confirmed_future_pay_facts(
            authenticated_user_id=owner, business_reference=business,
            tax_year=tax_year, nation=nation, annual_position=annual,
        )


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
        if (type(self.future_facts_provider) is RepositoryFuturePayFactsProvider
                and self.future_facts_provider.repository is not self.repository):
            raise DurablePayeForecastEndpointError(
                "future-pay repository does not match the forecast repository"
            )


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if (type(business) is not str or not business or type(tax_year) is not str
            or len(tax_year) != 7 or tax_year[4] != "/"
            or not tax_year[:4].isdigit() or not tax_year[5:].isdigit()
            or int(tax_year[5:]) != (int(tax_year[:4]) + 1) % 100
            or type(nation) is not str or not nation):
        return None
    return business, tax_year, nation


def _runtime_scope(runtime, owner):
    if type(runtime) is not DurablePayeForecastRuntime or type(owner) is not int or owner <= 0:
        raise DurablePayeForecastEndpointError("durable PAYE forecast runtime is unavailable")
    scope = _scope(runtime.owner_scope_resolver(owner))
    if scope is None:
        raise DurablePayeForecastEndpointError("owner scope is unavailable")
    runtime.repository.assert_external_authority_available()
    return scope


def _date_field(value):
    if type(value) is not str or len(value) != 10:
        raise DurablePayeForecastEndpointError("future-pay date is invalid")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DurablePayeForecastEndpointError("future-pay date is invalid") from exc
    if parsed.isoformat() != value:
        raise DurablePayeForecastEndpointError("future-pay date is invalid")
    return parsed


def _money_field(value, *, allow_zero):
    if type(value) is not str or _MONEY.fullmatch(value) is None:
        raise DurablePayeForecastEndpointError("future-pay amount is invalid")
    amount = Decimal(value).quantize(Decimal("0.01"))
    if (amount > Decimal("1000000000000000000.00")
            or (not allow_zero and amount.is_zero())):
        raise DurablePayeForecastEndpointError("future-pay amount is invalid")
    return amount


def confirmed_future_pay_periods(runtime: DurablePayeForecastRuntime, owner: int) -> dict:
    """Project the minimum owner-bound records for the customer edit screen."""
    business, tax_year, _nation = _runtime_scope(runtime, owner)
    records = runtime.repository.list_confirmed_future_pay_periods(
        authenticated_user_id=owner, business_reference=business,
        tax_year=tax_year, audit_reference="audit:future-pay-customer-list",
    )
    return {
        "tax_year": tax_year,
        "periods": tuple({
            "source_identity": record.source_identity,
            "employment_slot": int(record.source_identity.rsplit("-", 1)[1])
            if _FUTURE_EMPLOYMENT_SOURCE.fullmatch(record.source_identity) else None,
            "period_start": record.period_start.isoformat(),
            "period_end": record.period_end.isoformat(),
            "expected_gross_pay": f"{record.expected_gross_pay:.2f}",
            "expected_tax_deducted": f"{record.expected_tax_deducted:.2f}",
            "confirmed_at": record.confirmed_at.date().isoformat(),
        } for record in records),
    }


def observed_future_pay_coverage(current_entries: list[dict], future_context: dict) -> dict:
    """Describe only recorded date coverage; never certify a complete universe."""
    if type(current_entries) is not list or type(future_context) is not dict:
        raise DurablePayeForecastEndpointError("coverage inputs are invalid")
    tax_year = future_context.get("tax_year")
    scope = _scope(("coverage-only", tax_year, "coverage-only"))
    periods = future_context.get("periods")
    if scope is None or type(periods) is not tuple:
        raise DurablePayeForecastEndpointError("coverage inputs are invalid")
    start_year = int(tax_year[:4])
    year_start, year_end = date(start_year, 4, 6), date(start_year + 1, 4, 5)
    latest_current: dict[int, date] = {}
    future_by_slot: dict[int, list[tuple[date, date]]] = {}
    for entry in current_entries:
        if (type(entry) is not dict or entry.get("tax_year") != tax_year
                or type(entry.get("employment_slot")) is not int
                or not 1 <= entry["employment_slot"] <= 20
                or type(entry.get("effective_through")) is not str):
            raise DurablePayeForecastEndpointError("current coverage evidence is invalid")
        effective = _date_field(entry["effective_through"])
        if not year_start <= effective <= year_end:
            raise DurablePayeForecastEndpointError("current coverage evidence is invalid")
        slot = entry["employment_slot"]
        latest_current[slot] = max(effective, latest_current.get(slot, year_start))
    for period in periods:
        if (type(period) is not dict or type(period.get("employment_slot")) is not int
                or not 1 <= period["employment_slot"] <= 20):
            raise DurablePayeForecastEndpointError("future coverage evidence is invalid")
        interval = (_date_field(period.get("period_start")),
                    _date_field(period.get("period_end")))
        if not year_start <= interval[0] <= interval[1] <= year_end:
            raise DurablePayeForecastEndpointError("future coverage evidence is invalid")
        future_by_slot.setdefault(period["employment_slot"], []).append(interval)

    observed = []
    for slot in sorted(set(latest_current) | set(future_by_slot)):
        future = sorted(future_by_slot.get(slot, ()))
        current = latest_current.get(slot)
        merged = []
        for interval_start, interval_end in future:
            if not merged or interval_start > merged[-1][1] + timedelta(days=1):
                merged.append([interval_start, interval_end])
            else:
                merged[-1][1] = max(merged[-1][1], interval_end)
        cursor = year_start
        uncovered = []
        for interval_start, interval_end in merged:
            if cursor < interval_start:
                uncovered.append((cursor, interval_start - timedelta(days=1)))
            cursor = max(cursor, interval_end + timedelta(days=1))
        if cursor <= year_end:
            uncovered.append((cursor, year_end))
        observed.append({
            "employment_slot": slot,
            "latest_current_effective_through": current.isoformat() if current else None,
            "current_evidence_coverage_status": (
                "point_in_time_observation_only" if current else "not_recorded"
            ),
            "confirmed_future_intervals": tuple({
                "period_start": interval_start.isoformat(),
                "period_end": interval_end.isoformat(),
            } for interval_start, interval_end in future),
            "uncovered_intervals": tuple({
                "period_start": interval_start.isoformat(),
                "period_end": interval_end.isoformat(),
            } for interval_start, interval_end in uncovered),
        })
    return {
        "tax_year": tax_year,
        "coverage_scope": "submitted_confirmed_periods_only",
        "required_coverage_status": "not_established",
        "employment_universe_status": "unverified",
        "observed_employments": tuple(observed),
    }


def save_confirmed_future_pay_period_from_customer(
    runtime: DurablePayeForecastRuntime, owner: int, fields: dict,
) -> str:
    """Validate the exact minimum form and save it under server-owned scope."""
    expected = {
        "employment_slot", "period_start", "period_end", "expected_gross_pay",
        "expected_tax_deducted", "confirmation",
    }
    if type(fields) is not dict or set(fields) != expected or fields["confirmation"] != "yes":
        raise DurablePayeForecastEndpointError("future-pay confirmation is invalid")
    slot = fields["employment_slot"]
    if type(slot) is not str or not slot.isdigit() or not 1 <= int(slot) <= 20:
        raise DurablePayeForecastEndpointError("future-pay employment is invalid")
    business, tax_year, _nation = _runtime_scope(runtime, owner)
    return runtime.repository.save_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference=business,
        tax_year=tax_year, source_identity=f"future-source:employment-{int(slot)}",
        period_start=_date_field(fields["period_start"]),
        period_end=_date_field(fields["period_end"]),
        expected_gross_pay=_money_field(fields["expected_gross_pay"], allow_zero=False),
        expected_tax_deducted=_money_field(
            fields["expected_tax_deducted"], allow_zero=True,
        ),
        audit_reference="audit:future-pay-customer-save",
    )


def delete_confirmed_future_pay_period_from_customer(
    runtime: DurablePayeForecastRuntime, owner: int, fields: dict,
) -> bool:
    """Delete one exact owned row without disclosing whether it existed."""
    expected = {"source_identity", "period_start", "period_end"}
    if type(fields) is not dict or set(fields) != expected:
        raise DurablePayeForecastEndpointError("future-pay deletion is invalid")
    business, tax_year, _nation = _runtime_scope(runtime, owner)
    return runtime.repository.delete_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference=business,
        tax_year=tax_year, source_identity=fields["source_identity"],
        period_start=_date_field(fields["period_start"]),
        period_end=_date_field(fields["period_end"]),
        audit_reference="audit:future-pay-customer-delete",
    )


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

    business, tax_year, nation = _runtime_scope(runtime, owner)
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
    if type(runtime.future_facts_provider) is RepositoryFuturePayFactsProvider:
        final_facts = runtime.future_facts_provider(
            owner, business, tax_year, nation, annual,
        )
        if final_facts != facts:
            raise DurablePayeForecastEndpointError(
                "future-pay facts changed during composition"
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
    "RepositoryFuturePayFactsProvider",
    "confirmed_future_pay_periods", "current_forecast_payload",
    "delete_confirmed_future_pay_period_from_customer",
    "install_durable_paye_forecast_endpoint",
    "observed_future_pay_coverage",
    "save_confirmed_future_pay_period_from_customer",
]
