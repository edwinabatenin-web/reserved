"""Opt-in local current-paid-period panel from a live successful-renewal fact.

This module neither contacts a provider nor changes billing, access or
entitlement.  It only contributes fixed customer copy to the authenticated
plans template after rechecking one exact, owner-bound live fact twice.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from flask import Flask, before_render_template, g, request

import reserved.database as database
from reserved.auth import is_production_environment
from reserved.web.v2 import billing_plans
from . import exact_utc_entitlement as exact


VERSION = 'reserved-w10-local-billing-successful-renewal-view/1.0'
_KEY = 'reserved.billing.local_billing_successful_renewal_view'
_CONTEXT = 'local_billing_successful_renewal_copy'
_ENDPOINT = 'v2.billing_plans'
_TEMPLATE = 'v2/plans.html'
_CODE = billing_plans.__code__


class LocalBillingSuccessfulRenewalViewError(ValueError):
    """Value-free installation refusal."""


@dataclass(frozen=True)
class _Access:
    membership_resolver: object
    live_successful_renewal_fact_resolver: object


def _registered(app):
    rules = [rule for rule in app.url_map.iter_rules()
             if rule.endpoint == _ENDPOINT or rule.rule == '/v2/plans']
    return (app.view_functions.get(_ENDPOINT) is billing_plans
            and billing_plans.__code__ is _CODE
            and len(rules) == 1 and rules[0].endpoint == _ENDPOINT
            and rules[0].rule == '/v2/plans'
            and rules[0].methods == {'GET', 'HEAD', 'OPTIONS'}
            and not rules[0].defaults and not rules[0].host
            and not rules[0].subdomain and rules[0].redirect_to is None
            and not any(fn is billing_plans and name != _ENDPOINT
                        for name, fn in app.view_functions.items()))


def _scope(value):
    if (type(value) is not tuple or len(value) != 3
            or not all(type(part) is str and part for part in value)):
        return None
    return value


def _utc(value):
    if (type(value) is not datetime or value.tzinfo is not timezone.utc
            or value.utcoffset() != timedelta(0)):
        raise ValueError('exact UTC instant required')
    return value


def _parsed(value):
    if type(value) is not str:
        raise ValueError('exact timestamp required')
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not timezone.utc or parsed.isoformat() != value:
        raise ValueError('canonical UTC timestamp required')
    return parsed


def _display(value):
    return value.strftime('%-d %B %Y at %H:%M:%S UTC')


def _stamp(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _copy(access, now):
    now = _utc(now)
    user_id = g.get('user_id')
    if type(user_id) is not int or database.get_user(user_id) is None:
        return None
    first_scope = _scope(access.membership_resolver(user_id))
    if first_scope is None:
        return None
    first_fact = access.live_successful_renewal_fact_resolver(*first_scope)
    first = exact.successful_renewal_presentation_facts(first_fact, now=now)

    # Re-read both scope and opaque live fact before rendering.  Any ownership,
    # lifecycle, authority or source change suppresses the panel.
    if database.get_user(user_id) is None:
        return None
    second_scope = _scope(access.membership_resolver(user_id))
    if second_scope != first_scope:
        return None
    second_fact = access.live_successful_renewal_fact_resolver(*second_scope)
    second = exact.successful_renewal_presentation_facts(second_fact, now=now)
    if second_fact is not first_fact or second != first:
        return None

    if (set(first) != {
            'owner', 'billing_account', 'subscription', 'renewal_verified_at_utc',
            'current_paid_period_started_at_utc', 'paid_through_exclusive_utc',
            'receipt_id', 'fact_id', 'disposition'}
            or (first['owner'], first['billing_account'], first['subscription'])
            != first_scope
            or first['disposition'] != 'verified_successful_renewal'
            or not all(type(first[name]) is str and first[name]
                       for name in ('receipt_id', 'fact_id'))):
        return None
    verified = _parsed(first['renewal_verified_at_utc'])
    paid_start = _parsed(first['current_paid_period_started_at_utc'])
    paid_end = _parsed(first['paid_through_exclusive_utc'])
    if (any(value.microsecond for value in (verified, paid_start, paid_end))
            or not verified <= now < paid_end
            or not paid_start <= now < paid_end):
        return None
    return {
        'heading': 'Current paid period',
        'summary': 'This current paid period is based on a verified successful renewal fact.',
        'verified_label': 'Renewal fact verified at',
        'verified_display': _display(verified),
        'verified_utc': _stamp(verified),
        'paid_period_message': (
            f"Current paid period: {_display(paid_start)} until {_display(paid_end)}."
        ),
        'paid_period_start_utc': _stamp(paid_start),
        'paid_through_exclusive_utc': _stamp(paid_end),
        'scope_caveat': 'This panel makes no statement beyond this current paid period.',
    }


def install_local_billing_successful_renewal_view(
        app, *, membership_resolver, live_successful_renewal_fact_resolver,
        clock=None):
    """Install one local, fixed-copy supplier; it is absent by default."""
    if (type(app) is not Flask or is_production_environment() or app._got_first_request
            or _KEY in app.extensions or not _registered(app)):
        raise LocalBillingSuccessfulRenewalViewError(
            'local unambiguous pre-request installation required')
    if not callable(membership_resolver) or not callable(live_successful_renewal_fact_resolver):
        raise LocalBillingSuccessfulRenewalViewError('explicit dependencies required')
    if clock is not None and not callable(clock):
        raise LocalBillingSuccessfulRenewalViewError('invalid clock dependency')
    access = _Access(membership_resolver, live_successful_renewal_fact_resolver)
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
