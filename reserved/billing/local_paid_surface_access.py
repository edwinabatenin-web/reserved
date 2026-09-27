"""Explicit non-production wiring for the exact settled W10 paid endpoint set.

No registration, storage, provider operation or installation occurs on import.
Caller-supplied membership and billing-fact dependencies remain synthetic; this
module neither authenticates those dependencies nor supplies production custody.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps

from flask import Flask
from reserved.auth import is_production_environment, require_auth
from reserved.web import v2, hicbc
from . import local_dashboard_access as dashboard
from . import runtime_entitlement_admission as admission
from . import paid_access_guard as paid

VERSION = "reserved-w10-local-paid-surface-access/1.0"
_KEY = "reserved.billing.local_paid_surface_access"

# Reviewed actual URL/method registrations, not a caller-selected route list.
# HEAD/OPTIONS are Flask's existing automatic methods, preserved unchanged.
_ROUTES = (
    ("v2.index", "/v2/", "GET"),
    ("v2.connections", "/v2/connections", "GET"),
    ("v2.dashboard_view", "/v2/dashboard", "GET"),
    ("v2.paye_manual_baseline", "/v2/paye/manual-baseline", "GET POST"),
    ("v2.paye_manual_journey", "/v2/paye/manual", "GET POST"),
    ("v2.delete_paye_manual_journey_entry", "/v2/paye/manual/entries/<evidence_id>/delete", "POST"),
    ("v2.paye_durable_current_position", "/v2/paye/current-position", "GET"),
    ("v2.paye_durable_current_forecast", "/v2/paye/current-forecast", "GET"),
    ("v2.mtd_manual_scope", "/v2/mtd/scope-indication", "GET POST"),
    ("v2.invoices", "/v2/invoices", "GET"),
    ("v2.invoices_seed", "/v2/invoices/seed", "POST"),
    ("v2.optimise_view", "/v2/optimise", "GET"),
    ("v2.optimise_calculate", "/v2/optimise/calculate", "POST"),
    ("v2.optimise_save_scenario", "/v2/optimise/save-scenario", "POST"),
    ("v2.optimise_delete_scenario", "/v2/optimise/saved/<int:scenario_id>", "DELETE"),
    ("v2.review_queue", "/v2/review", "GET"),
    ("v2.settings_page", "/v2/settings", "GET POST"),
    ("v2.transactions", "/v2/transactions", "GET"),
    ("v2.transactions_seed", "/v2/transactions/seed", "POST"),
    ("v2.yapily_callback", "/v2/yapily/callback", "GET"),
    ("v2.yapily_connect", "/v2/yapily/connect", "POST"),
    ("v2.yapily_disconnect", "/v2/yapily/disconnect", "POST"),
    ("v2.yapily_refresh", "/v2/yapily/refresh", "POST"),
    ("hicbc.index", "/v2/hicbc/", "GET"),
    ("hicbc.delete_estimate", "/v2/hicbc/delete", "POST"),
    ("hicbc.save_estimate", "/v2/hicbc/estimate", "POST"),
    ("hicbc.link_page", "/v2/hicbc/link", "GET POST"),
    ("hicbc.link_accept", "/v2/hicbc/link/accept", "POST"),
    ("hicbc.link_invite", "/v2/hicbc/link/invite", "POST"),
    ("hicbc.link_revoke", "/v2/hicbc/link/revoke", "POST"),
    ("hicbc.result_json", "/v2/hicbc/result", "GET"),
    ("hicbc.annual_preview", "/v2/hicbc/annual-preview", "POST"),
    ("hicbc.durable_current_annual_position", "/v2/hicbc/current-annual-position", "GET"),
)
_FUNCTIONS = tuple((name, getattr(v2 if name.startswith("v2.") else hicbc,
                                 name.split(".")[1])) for name, _, _ in _ROUTES)
_CODES = tuple((fn, fn.__code__, getattr(fn, "__wrapped__", None)) for _, fn in _FUNCTIONS)


class LocalPaidSurfaceAccessError(ValueError):
    """Value-free installation failure; no implicit partial success."""


class LocalPaidSurfaceAccessHandle:
    __slots__ = ()

    def __new__(cls):
        raise TypeError("installer-issued marker only")


@dataclass(frozen=True)
class _Access:
    membership_resolver: object
    snapshot_reader: object
    live_fact_resolver: object
    admission_binding: object
    guard: object
    project_admitted_billing_fact: object


def _registrations(app):
    if tuple(name for name, _, _ in _ROUTES) != paid.PAID_ENDPOINTS:
        raise LocalPaidSurfaceAccessError("paid inventory differs from reviewed set")
    functions = app.view_functions
    if type(functions) is not dict or type(app.extensions) is not dict:
        raise LocalPaidSurfaceAccessError("ambiguous application mappings")
    conditional = "hicbc" in app.blueprints
    if conditional and app.blueprints["hicbc"] is not hicbc.hicbc:
        raise LocalPaidSurfaceAccessError("ambiguous conditional blueprint")
    expected = {name: fn for name, fn in _FUNCTIONS if conditional or not name.startswith("hicbc.")}
    if any(functions.get(name) is not fn for name, fn in expected.items()):
        raise LocalPaidSurfaceAccessError("missing or changed paid function")
    if any(name in functions for name, _ in _FUNCTIONS if name not in expected):
        raise LocalPaidSurfaceAccessError("partially registered conditional set")
    if any(fn.__code__ is not code or getattr(fn, "__wrapped__", None) is not wrapped
           for fn, code, wrapped in _CODES):
        raise LocalPaidSurfaceAccessError("changed original wrapper")
    # Reject aliases to either an original decorated function or its body,
    # including an alias wrapped using functools.wraps. This is registration
    # validation, not protection against arbitrary hostile in-process code.
    protected = {id(fn) for fn in expected.values()}
    protected.update(id(wrapped) for fn, _, wrapped in _CODES if fn in expected.values())
    for name, fn in functions.items():
        if name in expected:
            continue
        seen = set()
        while fn is not None:
            if id(fn) in protected or id(fn) in seen:
                raise LocalPaidSurfaceAccessError("aliased or cyclic view wrapper")
            seen.add(id(fn))
            fn = getattr(fn, "__wrapped__", None)
    rules = tuple(app.url_map.iter_rules())
    for name, path, method_text in _ROUTES:
        matching = [r for r in rules if r.endpoint == name or r.rule == path]
        if name not in expected:
            if matching:
                raise LocalPaidSurfaceAccessError("unexpected conditional rule")
            continue
        methods = set(method_text.split()) | {"OPTIONS"}
        if "GET" in methods:
            methods.add("HEAD")
        if (len(matching) != 1 or matching[0].endpoint != name or matching[0].rule != path
                or matching[0].methods != methods or matching[0].defaults
                or matching[0].host or matching[0].subdomain
                or matching[0].redirect_to is not None):
            raise LocalPaidSurfaceAccessError("ambiguous paid rule")
    return expected


def install_local_paid_surface_access(app, *, membership_resolver, snapshot_reader,
        live_fact_resolver, validate_admitted_billing_fact,
        project_admitted_billing_fact, clock=None):
    """Validate the complete installation before replacing any registered view.

    Call only from an explicit local synthetic composition root before requests.
    Original decorated views run intact after admission: no route-specific
    wrapper, feature switch, CSRF exemption or method behavior is removed.
    """
    if type(app) is not Flask or is_production_environment():
        raise LocalPaidSurfaceAccessError("local Flask installation required")
    if app._got_first_request or _KEY in app.extensions or dashboard._EXTENSION_KEY in app.extensions:
        raise LocalPaidSurfaceAccessError("late duplicate or conflicting installation")
    originals = _registrations(app)
    if not all(callable(fn) for fn in (membership_resolver, snapshot_reader, live_fact_resolver)):
        raise LocalPaidSurfaceAccessError("explicit server dependencies required")
    if clock is not None and not callable(clock):
        raise LocalPaidSurfaceAccessError("invalid clock dependency")
    try:
        bound = admission.bind_runtime_entitlement_admission(
            validate_admitted_billing_fact=validate_admitted_billing_fact,
            project_admitted_billing_fact=project_admitted_billing_fact)
        guard = paid.bind_paid_access_guard(validate_runtime_entitlement=admission.validate_runtime_entitlement,
                                            project_runtime_entitlement=admission.project_runtime_entitlement)
    except Exception:
        raise LocalPaidSurfaceAccessError("invalid admission dependencies") from None
    access = _Access(membership_resolver, snapshot_reader, live_fact_resolver,
                     bound, guard, project_admitted_billing_fact)
    effective_clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def wrap(endpoint, original):
        @require_auth
        @wraps(original)
        def guarded(*args, **kwargs):
            if is_production_environment():
                return dashboard._denial_response()
            try:
                allowed = dashboard._evaluate(access, evaluated_at_utc=effective_clock(), endpoint=endpoint)
            except Exception:
                allowed = False
            if not allowed or is_production_environment():
                return dashboard._denial_response()
            return original(*args, **kwargs)
        return guarded

    replacements = {name: wrap(name, original) for name, original in originals.items()}
    handle = object.__new__(LocalPaidSurfaceAccessHandle)
    # All potentially failing dependency/registration validation precedes this
    # bounded publication to ordinary Flask dictionaries; no partial installer.
    app.view_functions.update(replacements)
    app.extensions[_KEY] = handle
    return handle


def install_local_exact_utc_paid_surface_access(app, *, authority, repository, clock):
    """Distinct initial-only protocol, using a concrete independent witness.

    No arbitrary allow callback; no legacy protocol coercion or default install.
    The shared marker preserves bidirectional conflicts with the legacy installer.
    """
    from reserved.billing.local_stripe_initial_payment import SyntheticInitialAuthority, allows_paid_request
    from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
    if (type(app) is not Flask or is_production_environment() or app._got_first_request
            or _KEY in app.extensions or dashboard._EXTENSION_KEY in app.extensions
            or type(authority) is not SyntheticInitialAuthority
            or type(repository) is not ProvenanceRepository or not callable(clock)):
        raise LocalPaidSurfaceAccessError('explicit local exact protocol required')
    originals = _registrations(app)
    authority.snapshot()

    def wrap(endpoint, original):
        @require_auth
        @wraps(original)
        def guarded(*args, **kwargs):
            from flask import g
            from reserved.database import get_user
            try:
                user_id = g.get('user_id')
                allowed = (not is_production_environment() and type(user_id) is int
                           and get_user(user_id) is not None
                           and allows_paid_request(authority, repository, user_id=user_id,
                                                   now=clock(), endpoint=endpoint))
            except Exception:
                allowed = False
            if not allowed or is_production_environment():
                return dashboard._denial_response()
            return original(*args, **kwargs)
        return guarded

    replacements = {name: wrap(name, original) for name, original in originals.items()}
    handle = object.__new__(LocalPaidSurfaceAccessHandle)
    app.view_functions.update(replacements)
    app.extensions[_KEY] = handle
    return handle
