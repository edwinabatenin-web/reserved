"""Disabled-first HTTP installer for the trusted durable HICBC annual read.

There is no UI, provider call, credential use, payment authority or activation
in this module.  The application root must explicitly inject every trusted
dependency.  Browser input cannot select owner, business, tax year, nation or
calculation time.
"""

from __future__ import annotations

from flask import Flask, abort, jsonify, request

from reserved.auth import require_auth
from reserved.config import durable_hicbc_annual_enabled
from reserved.engines.annual_to_cash_integration import AnnualToCashPosition
from reserved.engines.integrated_annual_position import AnnualPositionResult
from reserved.hicbc_durable_annual_bridge import compose_durable_authenticated_hicbc_preview


_KEY = "reserved.hicbc.durable_annual_endpoint"
_RULE = "/v2/hicbc/current-annual-position"
_ENDPOINT = "hicbc_durable_current_annual_position"


class DurableHicbcEndpointError(ValueError):
    """Installation failed before modifying the Flask application."""


class DurableHicbcEndpointHandle:
    __slots__ = ()

    def __new__(cls):
        raise TypeError("durable HICBC endpoint handles are installer-issued only")


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if (type(business) is not str or not business or type(tax_year) is not str
            or len(tax_year) != 7 or tax_year[4] != "/"
            or type(nation) is not str or not nation):
        return None
    return business, tax_year, nation


def install_durable_hicbc_annual_endpoint(
    app: Flask, *, repository, owner_scope_resolver, live_annual_provider,
):
    """Install one read-only GET endpoint after complete preflight validation."""
    from reserved.annual_position_durable_repository import DurableAnnualPositionRepository

    if type(app) is not Flask or app._got_first_request or _KEY in app.extensions:
        raise DurableHicbcEndpointError("exact pre-request Flask installation is required")
    if type(repository) is not DurableAnnualPositionRepository:
        raise DurableHicbcEndpointError("exact durable repository is required")
    if not callable(owner_scope_resolver) or not callable(live_annual_provider):
        raise DurableHicbcEndpointError("explicit owner-scope and annual dependencies are required")
    if _ENDPOINT in app.view_functions or any(rule.rule == _RULE for rule in app.url_map.iter_rules()):
        raise DurableHicbcEndpointError("HICBC endpoint registration is ambiguous")

    @require_auth
    def current_annual_position():
        if (not durable_hicbc_annual_enabled() or request.args
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
            pair = live_annual_provider(owner, business, tax_year, nation)
            if (type(pair) is not tuple or len(pair) != 2
                    or type(pair[0]) is not AnnualToCashPosition
                    or type(pair[1]) is not AnnualPositionResult):
                raise ValueError
            result = compose_durable_authenticated_hicbc_preview(
                repository=repository, annual_position=pair[0], annual_tax_position=pair[1],
                business_reference=business, tax_year=tax_year, nation=nation,
                audit_reference="audit:hicbc-durable-current-position",
            )
        except Exception:
            abort(404)
        return jsonify(result.public_value())

    app.add_url_rule(_RULE, endpoint=_ENDPOINT, view_func=current_annual_position, methods=("GET",))
    handle = object.__new__(DurableHicbcEndpointHandle)
    app.extensions[_KEY] = handle
    return handle
