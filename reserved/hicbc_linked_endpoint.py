"""Disabled local HTTP adapter for accepted linked-HICBC annual composition.

The adapter supplies no provider, scope, identity, network, activation or
release authority.  Every dependency is injected by the application root and
the route remains behind independent HICBC, linked-source and paid-access gates.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask

from reserved.annual_position_durable_repository import (
    DurableAnnualPositionRepository,
    RECORD_PURPOSE,
)
from reserved.engines.annual_to_cash_integration import AnnualToCashPosition
from reserved.engines.integrated_annual_position import AnnualPositionResult
from reserved.hicbc_linked_annual_composition import (
    LinkedAnnualLiveSource,
    compose_linked_durable_authenticated_hicbc_preview,
    preflight_linked_durable_authenticated_hicbc,
)


_KEY = "reserved.hicbc.linked_annual_endpoint"
_RULE = "/v2/hicbc/linked-current-annual-position"
_ENDPOINT = "hicbc.linked_current_annual_position"


class LinkedHicbcEndpointError(ValueError):
    """Installation or server-owned dependency admission failed closed."""


@dataclass(frozen=True, slots=True)
class LinkedHicbcRuntime:
    repository: object
    owner_scope_resolver: object
    owner_annual_provider: object
    partner_annual_provider: object

    def __post_init__(self):
        if type(self.repository) is not DurableAnnualPositionRepository:
            raise LinkedHicbcEndpointError("exact durable repository is required")
        if not all(callable(value) for value in (
            self.owner_scope_resolver,
            self.owner_annual_provider,
            self.partner_annual_provider,
        )):
            raise LinkedHicbcEndpointError(
                "complete server-owned linked HICBC dependencies are required"
            )


def _scope(value):
    if type(value) is not tuple or len(value) != 3:
        return None
    business, tax_year, nation = value
    if (type(business) is not str or not business
            or type(tax_year) is not str or len(tax_year) != 7 or tax_year[4] != "/"
            or type(nation) is not str or not nation):
        return None
    return business, tax_year, nation


def _live_source(value) -> LinkedAnnualLiveSource:
    if (type(value) is not tuple or len(value) != 2
            or type(value[0]) is not AnnualToCashPosition
            or type(value[1]) is not AnnualPositionResult):
        raise LinkedHicbcEndpointError("exact live annual source is unavailable")
    return LinkedAnnualLiveSource(value[0], value[1])


def _unavailable_payload(tax_year: str) -> dict:
    return {
        "tax_year": tax_year,
        "calculation_status": "insufficient_facts",
        "responsibility_status": None,
        "projected_user_hicbc": None,
        "possible_charge_low": None,
        "possible_charge_high": None,
    }


def linked_current_annual_position_payload(runtime: LinkedHicbcRuntime, owner: int) -> dict:
    """Resolve only server-owned sources and compose the receiving user's result."""
    if type(runtime) is not LinkedHicbcRuntime or type(owner) is not int or owner <= 0:
        raise LinkedHicbcEndpointError("linked HICBC runtime is unavailable")
    scope = _scope(runtime.owner_scope_resolver(owner))
    if scope is None:
        raise LinkedHicbcEndpointError("owner scope is unavailable")
    business, tax_year, nation = scope

    # No annual producer runs before exact owner authority and the durable head
    # have been admitted.  The linked service separately admits link permission
    # before invoking the partner producer and repeats all facts atomically.
    runtime.repository.assert_external_authority_available()
    runtime.repository.read_current(
        authenticated_user_id=owner,
        business_reference=business,
        tax_year=tax_year,
        nation=nation,
        record_purpose=RECORD_PURPOSE,
        audit_reference="audit:linked-hicbc-preflight",
    )
    if not preflight_linked_durable_authenticated_hicbc(
        repository=runtime.repository,
        owner_business_reference=business,
        tax_year=tax_year,
        nation=nation,
    ):
        return _unavailable_payload(tax_year)
    try:
        owner_source = _live_source(
            runtime.owner_annual_provider(owner, business, tax_year, nation)
        )

        def partner_source(partner_id, derived_tax_year, derived_nation):
            return _live_source(
                runtime.partner_annual_provider(
                    partner_id, derived_tax_year, derived_nation,
                )
            )

        result = compose_linked_durable_authenticated_hicbc_preview(
            repository=runtime.repository,
            owner_source=owner_source,
            partner_source_provider=partner_source,
            owner_business_reference=business,
            tax_year=tax_year,
            nation=nation,
        )
        return dict(result.public_value())
    except Exception:
        # Once exact owner authority is admitted, every unavailable linked or
        # live-source state has one value-free result; no exception detail or
        # partner-state distinction reaches the route.
        return _unavailable_payload(tax_year)


def install_linked_hicbc_annual_endpoint(app: Flask, runtime: LinkedHicbcRuntime):
    """Bind the exact runtime only after paid enforcement protects the route."""
    if (type(app) is not Flask or app._got_first_request or _KEY in app.extensions
            or type(runtime) is not LinkedHicbcRuntime):
        raise LinkedHicbcEndpointError("exact pre-request Flask installation is required")
    rules = tuple(
        rule for rule in app.url_map.iter_rules()
        if rule.endpoint == _ENDPOINT or rule.rule == _RULE
    )
    if (len(rules) != 1 or rules[0].endpoint != _ENDPOINT
            or rules[0].rule != _RULE
            or rules[0].methods != {"GET", "HEAD", "OPTIONS"}):
        raise LinkedHicbcEndpointError("linked HICBC registration is ambiguous")

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
        raise LinkedHicbcEndpointError("active exact paid-surface enforcement is required")
    app.extensions[_KEY] = runtime
    return runtime


__all__ = [
    "LinkedHicbcEndpointError",
    "LinkedHicbcRuntime",
    "install_linked_hicbc_annual_endpoint",
    "linked_current_annual_position_payload",
]
