"""Disabled-first authenticated HTTP installation for durable PAYE composition.

This module exposes no UI and performs no provider, network, payment, refund,
or deployment action. The application composition root must inject a durable
repository, an admitted live annual-to-cash reader, and an exact owner scope
resolver. A browser cannot select a business, year, nation or future-pay fact.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask

from reserved.engines.paye_reconciliation import PayeReconciliationPolicy
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
