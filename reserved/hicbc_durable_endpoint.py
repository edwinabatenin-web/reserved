"""Disabled-first runtime for the trusted durable HICBC annual read.

There is no UI, built-in provider client, network access, credential use,
payment authority or activation in this module. The application root must
explicitly inject every trusted dependency. Browser input cannot select owner,
business, tax year, nation or calculation time.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask

from reserved.engines.annual_to_cash_integration import AnnualToCashPosition
from reserved.engines.integrated_annual_position import AnnualPositionResult
from reserved.hicbc_durable_annual_bridge import compose_durable_authenticated_hicbc_preview


_KEY = "reserved.hicbc.durable_annual_endpoint"
_RULE = "/v2/hicbc/current-annual-position"
_ENDPOINT = "hicbc.durable_current_annual_position"


class DurableHicbcEndpointError(ValueError):
    """Installation failed before modifying the Flask application."""


@dataclass(frozen=True, slots=True)
class DurableHicbcRuntime:
    """Complete server-owned dependencies for the durable HICBC route."""

    repository: object
    owner_scope_resolver: object
    live_annual_provider: object

    def __post_init__(self):
        from reserved.annual_position_durable_repository import DurableAnnualPositionRepository

        if type(self.repository) is not DurableAnnualPositionRepository:
            raise DurableHicbcEndpointError("exact durable repository is required")
        if not callable(self.owner_scope_resolver) or not callable(self.live_annual_provider):
            raise DurableHicbcEndpointError(
                "explicit owner-scope and annual dependencies are required"
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


def current_annual_position_payload(runtime: DurableHicbcRuntime, owner: int) -> dict:
    """Compose the bounded response from exact server-owned dependencies."""
    from reserved.annual_position_durable_repository import RECORD_PURPOSE

    if type(runtime) is not DurableHicbcRuntime or type(owner) is not int or owner <= 0:
        raise DurableHicbcEndpointError("durable HICBC runtime is unavailable")
    scope = _scope(runtime.owner_scope_resolver(owner))
    if scope is None:
        raise DurableHicbcEndpointError("owner scope is unavailable")
    business, tax_year, nation = scope
    # Do not invoke an annual provider for an owner/scope that lacks a currently
    # readable durable authority. The bridge repeats this read after provider
    # return and performs its final atomic binding check.
    runtime.repository.assert_external_authority_available()
    runtime.repository.read_current(
        authenticated_user_id=owner, business_reference=business,
        tax_year=tax_year, nation=nation, record_purpose=RECORD_PURPOSE,
        audit_reference="audit:hicbc-durable-preflight",
    )
    pair = runtime.live_annual_provider(owner, business, tax_year, nation)
    if (type(pair) is not tuple or len(pair) != 2
            or type(pair[0]) is not AnnualToCashPosition
            or type(pair[1]) is not AnnualPositionResult):
        raise DurableHicbcEndpointError("live annual result is unavailable")
    result = compose_durable_authenticated_hicbc_preview(
        repository=runtime.repository, annual_position=pair[0], annual_tax_position=pair[1],
        business_reference=business, tax_year=tax_year, nation=nation,
        audit_reference="audit:hicbc-durable-current-position",
    )
    return dict(result.public_value())


def install_durable_hicbc_annual_endpoint(app: Flask, runtime: DurableHicbcRuntime):
    """Bind complete dependencies to the pre-registered, paid-only route."""

    if (type(app) is not Flask or app._got_first_request or _KEY in app.extensions
            or type(runtime) is not DurableHicbcRuntime):
        raise DurableHicbcEndpointError("exact pre-request Flask installation is required")
    rules = tuple(
        rule for rule in app.url_map.iter_rules()
        if rule.endpoint == _ENDPOINT or rule.rule == _RULE
    )
    if (len(rules) != 1 or rules[0].endpoint != _ENDPOINT or rules[0].rule != _RULE
            or rules[0].methods != {"GET", "HEAD", "OPTIONS"}):
        raise DurableHicbcEndpointError("HICBC endpoint registration is ambiguous")
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
        raise DurableHicbcEndpointError("active exact paid-surface enforcement is required")
    app.extensions[_KEY] = runtime
    return runtime


__all__ = [
    "DurableHicbcEndpointError", "DurableHicbcRuntime",
    "current_annual_position_payload", "install_durable_hicbc_annual_endpoint",
]
