"""Explicit local recovery panel on the existing authenticated plans template.

No default installation, provider operation, storage or authority from rows.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from flask import Flask, before_render_template, request
from reserved.auth import is_production_environment
from reserved.web.v2 import billing_plans
from . import local_dashboard_access as shared
from . import runtime_entitlement_admission as admission
from .payment_recovery_presentation import (
    FACTS_VERSION, build_payment_recovery_presentation,
    validate_payment_recovery_presentation,
)

VERSION = 'reserved-w10-local-billing-recovery-view/1.0'
_KEY = 'reserved.billing.local_billing_recovery_view'
_CONTEXT = 'local_billing_recovery_copy'
_ENDPOINT = 'v2.billing_plans'
_TEMPLATE = 'v2/plans.html'
_CODE = billing_plans.__code__


class LocalBillingRecoveryViewError(ValueError):
    """Value-free installation refusal."""


@dataclass(frozen=True)
class _Access:
    membership_resolver: object
    snapshot_reader: object
    live_fact_resolver: object
    admission_binding: object
    project_admitted_billing_fact: object


def _registered(app):
    rules = [r for r in app.url_map.iter_rules()
             if r.endpoint == _ENDPOINT or r.rule == '/v2/plans']
    return (app.view_functions.get(_ENDPOINT) is billing_plans
            and billing_plans.__code__ is _CODE
            and len(rules) == 1 and rules[0].endpoint == _ENDPOINT
            and rules[0].rule == '/v2/plans'
            and rules[0].methods == {'GET', 'HEAD', 'OPTIONS'}
            and not rules[0].defaults and not rules[0].host
            and not rules[0].subdomain and rules[0].redirect_to is None
            and not any(fn is billing_plans and name != _ENDPOINT
                        for name, fn in app.view_functions.items()))


def _copy(access, now):
    # Validate the full request instant before formatting to S6E's seconds.
    # Never truncate a future transition or expired deadline into eligibility.
    if type(now) is not datetime or now.tzinfo is None or now.utcoffset() != timedelta(0):
        return None
    admitted = shared._rechecked_admission(access, evaluated_at_utc=now)
    if admitted is False:
        return None
    scope, _, current = admitted
    outcome = dict(admission.project_runtime_entitlement(current))
    if (outcome['state'] != 'payment_recovery'
            or outcome['derivation_kind'] != 'verified_renewal_failure'
            or outcome['ordinary_access'] is not True
            or outcome['owner_id'] != scope[0]):
        return None
    started = outcome['transition_effective_at_utc']
    deadline = outcome['recovery_deadline_exclusive_at_utc']
    if not started <= now < deadline:
        return None
    if started.microsecond or deadline.microsecond:
        return None
    def stamp(value):
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')
    facts = dict(schema_version=FACTS_VERSION, owner_reference=scope[0],
                 billing_account_reference=scope[1], subscription_reference=scope[2],
                 state=outcome['state'], recovery_started_at_utc=stamp(started),
                 recovery_deadline_exclusive_utc=stamp(deadline), evaluated_at_utc=stamp(now))
    result = validate_payment_recovery_presentation(build_payment_recovery_presentation(
        facts=facts, expected_owner_reference=scope[0]))
    # Fixed copy only; references, runtime handles and authority flags never
    # enter template context. S6E flags remain false, without modification.
    copy = dict(dict(result)['copy'])
    if copy['deadline_exclusive_utc'] != stamp(deadline):
        return None
    return copy


def install_local_billing_recovery_view(app, *, membership_resolver, snapshot_reader,
        live_fact_resolver, validate_admitted_billing_fact,
        project_admitted_billing_fact, clock=None):
    """Install only an exact endpoint/template-scoped local context supplier."""
    if (type(app) is not Flask or is_production_environment() or app._got_first_request
            or _KEY in app.extensions or not _registered(app)):
        raise LocalBillingRecoveryViewError('local unambiguous pre-request installation required')
    if not all(callable(fn) for fn in (membership_resolver, snapshot_reader, live_fact_resolver)):
        raise LocalBillingRecoveryViewError('explicit dependencies required')
    if clock is not None and not callable(clock):
        raise LocalBillingRecoveryViewError('invalid clock dependency')
    try:
        binding = admission.bind_runtime_entitlement_admission(
            validate_admitted_billing_fact=validate_admitted_billing_fact,
            project_admitted_billing_fact=project_admitted_billing_fact)
    except Exception:
        raise LocalBillingRecoveryViewError('invalid admission binding') from None
    access = _Access(membership_resolver, snapshot_reader, live_fact_resolver,
                     binding, project_admitted_billing_fact)
    effective_clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def supply(sender, template, context, **extra):
        conflict = _CONTEXT in context
        context.pop(_CONTEXT, None)
        if (is_production_environment() or request.endpoint != _ENDPOINT
                or request.method != 'GET' or template.name != _TEMPLATE
                or conflict or not _registered(app)):
            return
        try:
            copy = _copy(access, effective_clock())
        except Exception:
            return
        if copy is not None and not is_production_environment():
            context[_CONTEXT] = copy

    before_render_template.connect(supply, app, weak=False)
    app.extensions[_KEY] = supply
    return None
