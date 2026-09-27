"""Disabled-first authenticated HTTP installation for durable PAYE composition.

This module exposes no UI and performs no provider, network, payment, refund,
or deployment action. The application composition root must inject a durable
repository, an admitted live annual-to-cash reader, and an exact owner scope
resolver. A browser cannot select a business, year, nation or future-pay fact.
"""

from __future__ import annotations

from flask import Flask, abort, jsonify, request

from reserved.auth import require_auth
from reserved.config import durable_paye_composition_enabled
from reserved.engines.paye_reconciliation import PayeReconciliationPolicy
from reserved.paye_annual_bridge import compose_durable_authenticated_manual_paye


_KEY = "reserved.paye.durable_endpoint"
_RULE = "/v2/paye/current-position"
_ENDPOINT = "paye_durable_current_position"


class DurablePayeEndpointError(ValueError):
    """Installation failed before modifying the Flask application."""


class DurablePayeEndpointHandle:
    __slots__ = ()

    def __new__(cls):
        raise TypeError("durable PAYE endpoint handles are installer-issued only")


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if not all(type(item) is str and item for item in value):
        return None
    if len(tax_year) != 7 or tax_year[4] != "/":
        return None
    return business, tax_year, nation


def install_durable_paye_composition_endpoint(
    app: Flask,
    *,
    repository,
    annual_position_provider,
    owner_scope_resolver,
    reconciliation_policy,
):
    """Install one GET endpoint after complete dependency/route validation.

    The feature switch is read during each request. An unconfigured or disabled
    application returns a value-free 404, so installing the endpoint does not
    activate it. Every other unavailable/mismatched dependency also fails
    closed without a financial result.
    """
    from reserved.annual_position_durable_repository import DurableAnnualPositionRepository

    if type(app) is not Flask or app._got_first_request or _KEY in app.extensions:
        raise DurablePayeEndpointError("exact pre-request Flask installation is required")
    if type(repository) is not DurableAnnualPositionRepository:
        raise DurablePayeEndpointError("exact durable repository is required")
    if not callable(annual_position_provider) or not callable(owner_scope_resolver):
        raise DurablePayeEndpointError("explicit annual and owner-scope dependencies are required")
    if type(reconciliation_policy) is not PayeReconciliationPolicy:
        raise DurablePayeEndpointError("exact reconciliation policy is required")
    if _ENDPOINT in app.view_functions or any(rule.rule == _RULE for rule in app.url_map.iter_rules()):
        raise DurablePayeEndpointError("PAYE endpoint registration is ambiguous")

    @require_auth
    def current_position():
        # No browser-selected scope, optional payload, or future-pay data is
        # accepted. Empty request shape prevents accidental parameter channels.
        if not durable_paye_composition_enabled() or request.args:
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
            annual = annual_position_provider(owner, business, tax_year, nation)
            result = compose_durable_authenticated_manual_paye(
                repository=repository, annual_position=annual,
                authenticated_owner_user_id=owner, business_reference=business,
                tax_year=tax_year, nation=nation, audit_reference="audit:paye-current-position",
                reconciliation_policy=reconciliation_policy,
            )
        except Exception:
            abort(404)
        # This is intentionally evidence-state-only: no tax balance, reserve,
        # payment, refund, transfer, filing, recommendation or action field.
        return jsonify({
            "tax_year": tax_year,
            "paye_evidence_status": result.reconciliation.calculation_status,
            "tax_paid_known": result.reconciliation.tax_paid_known,
            "future_pay_status": "unknown" if result.future_pay_forecast is None else "confirmed_periods_only",
        })

    # All validation occurred before the single bounded Flask mutation below.
    app.add_url_rule(_RULE, endpoint=_ENDPOINT, view_func=current_position, methods=("GET",))
    handle = object.__new__(DurablePayeEndpointHandle)
    app.extensions[_KEY] = handle
    return handle
