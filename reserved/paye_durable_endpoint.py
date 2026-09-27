"""Disabled-first authenticated HTTP installation for durable PAYE composition.

This module exposes no UI and performs no provider, network, payment, refund,
or deployment action. The application composition root must inject a durable
repository, an admitted live annual-to-cash reader, and an exact owner scope
resolver. A browser cannot select a business, year, nation or future-pay fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from flask import Flask

from reserved.engines.paye_reconciliation import PayeReconciliationPolicy
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition,
    annual_to_cash_position_provenance,
)
from reserved.paye_annual_bridge import compose_durable_authenticated_manual_paye


_KEY = "reserved.paye.durable_endpoint"
_RULE = "/v2/paye/current-position"
_ENDPOINT = "v2.paye_durable_current_position"


class DurablePayeEndpointError(ValueError):
    """Installation failed before modifying the Flask application."""


@dataclass(frozen=True, slots=True)
class DurablePayeRuntime:
    """Complete server-owned dependencies for the current-position route."""

    repository: object
    annual_position_provider: object
    owner_scope_resolver: object
    reconciliation_policy: object
    clock: object

    def __post_init__(self):
        from reserved.annual_position_durable_repository import DurableAnnualPositionRepository

        if type(self.repository) is not DurableAnnualPositionRepository:
            raise DurablePayeEndpointError("exact durable repository is required")
        if not callable(self.annual_position_provider) or not callable(self.owner_scope_resolver):
            raise DurablePayeEndpointError(
                "explicit annual and owner-scope dependencies are required"
            )
        if type(self.reconciliation_policy) is not PayeReconciliationPolicy:
            raise DurablePayeEndpointError("exact reconciliation policy is required")
        if not callable(self.clock):
            raise DurablePayeEndpointError("explicit server clock is required")


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if not all(type(item) is str and item for item in value):
        return None
    if len(tax_year) != 7 or tax_year[4] != "/":
        return None
    return business, tax_year, nation


def install_durable_paye_composition_endpoint(app: Flask, runtime: DurablePayeRuntime):
    """Bind complete dependencies to the pre-registered, paid-only route."""
    if (type(app) is not Flask or app._got_first_request or _KEY in app.extensions
            or type(runtime) is not DurablePayeRuntime):
        raise DurablePayeEndpointError("exact pre-request runtime installation is required")
    rules = tuple(
        rule for rule in app.url_map.iter_rules()
        if rule.endpoint == _ENDPOINT or rule.rule == _RULE
    )
    if (len(rules) != 1 or rules[0].endpoint != _ENDPOINT or rules[0].rule != _RULE
            or rules[0].methods != {"GET", "HEAD", "OPTIONS"}):
        raise DurablePayeEndpointError("PAYE endpoint registration is ambiguous")
    from reserved.billing.stripe_runtime import StripeBillingRuntime

    billing_key = "reserved.billing.stripe_runtime"
    disabled_key = billing_key + ".paid_surface.disabled"
    active_key = billing_key + ".paid_surface"
    billing = app.extensions.get(billing_key)
    originals = app.extensions.get(disabled_key)
    guarded = app.view_functions.get(_ENDPOINT)
    if (
        type(billing) is not StripeBillingRuntime
        or app.extensions.get(active_key) is not True
        or type(originals) is not dict
        or _ENDPOINT not in originals
        or not callable(originals[_ENDPOINT])
        or not callable(guarded)
        or getattr(guarded, "__wrapped__", None) is not originals[_ENDPOINT]
    ):
        raise DurablePayeEndpointError("active exact paid-surface enforcement is required")
    app.extensions[_KEY] = runtime
    return runtime


def current_position_payload(runtime: DurablePayeRuntime, owner: int) -> dict:
    """Compose the value-bounded response from exact server-owned inputs."""
    if type(runtime) is not DurablePayeRuntime or type(owner) is not int or owner <= 0:
        raise DurablePayeEndpointError("durable PAYE runtime is unavailable")
    scope = _scope(runtime.owner_scope_resolver(owner))
    if scope is None:
        raise DurablePayeEndpointError("owner scope is unavailable")
    business, tax_year, nation = scope
    annual = runtime.annual_position_provider(owner, business, tax_year, nation)
    if type(annual) is not AnnualToCashPosition:
        raise DurablePayeEndpointError("annual position is unavailable")
    try:
        provenance = annual_to_cash_position_provenance(annual)
        evaluated_on = runtime.clock()
    except Exception:
        raise DurablePayeEndpointError("annual freshness evidence is unavailable") from None
    if (
        type(evaluated_on) is not date
        or type(provenance.as_of) is not date
        or type(provenance.stale_after_days) is not int
        or provenance.stale_after_days < 0
        or annual.as_of != provenance.as_of
        or not provenance.as_of
        <= evaluated_on
        <= provenance.as_of + timedelta(days=provenance.stale_after_days)
    ):
        raise DurablePayeEndpointError("annual position is outside its freshness horizon")
    result = compose_durable_authenticated_manual_paye(
        repository=runtime.repository, annual_position=annual,
        authenticated_owner_user_id=owner, business_reference=business,
        tax_year=tax_year, nation=nation, audit_reference="audit:paye-current-position",
        reconciliation_policy=runtime.reconciliation_policy,
    )
    return {
        "tax_year": tax_year,
        "paye_evidence_status": result.reconciliation.calculation_status,
        "tax_paid_known": result.reconciliation.tax_paid_known,
        "future_pay_status": (
            "unknown" if result.future_pay_forecast is None else "confirmed_periods_only"
        ),
    }


__all__ = [
    "DurablePayeEndpointError", "DurablePayeRuntime",
    "current_position_payload", "install_durable_paye_composition_endpoint",
]
