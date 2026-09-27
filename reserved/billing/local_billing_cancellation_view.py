"""Explicit non-production scheduled-cancellation panel for authenticated plans."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from flask import Flask, before_render_template, g, request

from reserved.auth import is_production_environment
import reserved.database as database
from reserved.web.v2 import billing_plans
from .cancellation_presentation import (
    FACTS_VERSION,
    build_cancellation_presentation,
    validate_cancellation_presentation,
)
from .local_stripe_initial_payment import cancellation_presentation_facts


VERSION = 'reserved-w10-local-billing-cancellation-view/1.0'
_KEY = 'reserved.billing.local_billing_cancellation_view'
_CONTEXT = 'local_billing_cancellation_copy'
_ENDPOINT = 'v2.billing_plans'
_TEMPLATE = 'v2/plans.html'
_CODE = billing_plans.__code__


class LocalBillingCancellationViewError(ValueError):
    """Value-free installation refusal."""


@dataclass(frozen=True)
class _Access:
    membership_resolver: object
    live_cancellation_fact_resolver: object


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
    first_fact = access.live_cancellation_fact_resolver(*first_scope)
    first = cancellation_presentation_facts(first_fact)

    # Re-resolve identity and the opaque live handle after the first projection.
    # Any source, membership or durable lifecycle change suppresses the claim.
    if database.get_user(user_id) is None:
        return None
    second_scope = _scope(access.membership_resolver(user_id))
    if second_scope != first_scope:
        return None
    second_fact = access.live_cancellation_fact_resolver(*second_scope)
    second = cancellation_presentation_facts(second_fact)
    if second_fact is not first_fact or second != first:
        return None

    owner, account, subscription = first_scope
    if (set(first) != {
            'owner', 'billing_account', 'subscription',
            'paid_period_started_at_utc', 'cancellation_verified_at_utc',
            'paid_through_exclusive_utc', 'paid_receipt_id', 'paid_fact_id',
            'disposition'}
            or (first['owner'], first['billing_account'], first['subscription'])
            != first_scope
            or first['disposition']
            != 'subscription_scheduled_to_end_at_paid_period_boundary'
            or not all(type(first[name]) is str and first[name]
                       for name in ('paid_receipt_id', 'paid_fact_id'))):
        return None
    started = _parsed(first['paid_period_started_at_utc'])
    verified = _parsed(first['cancellation_verified_at_utc'])
    end = _parsed(first['paid_through_exclusive_utc'])
    if not started <= verified <= now < end:
        return None
    if any(value.microsecond for value in (started, verified, end)):
        return None
    facts = dict(
        schema_version=FACTS_VERSION,
        owner_reference=owner,
        billing_account_reference=account,
        subscription_reference=subscription,
        state='cancellation_confirmed_end_of_paid_period',
        future_renewal_stopped=True,
        paid_period_started_at_utc=_stamp(started),
        cancellation_verified_at_utc=_stamp(verified),
        paid_through_exclusive_utc=_stamp(end),
        cancellation_effective_at_utc=_stamp(end),
        evaluated_at_utc=_stamp(now),
    )
    result = validate_cancellation_presentation(build_cancellation_presentation(
        facts=facts,
        expected_owner_reference=owner,
        expected_subscription_reference=subscription,
    ))
    copy = dict(dict(result)['copy'])
    if copy['paid_through_exclusive_utc'] != _stamp(end):
        return None
    return copy


def install_local_billing_cancellation_view(app, *, membership_resolver,
        live_cancellation_fact_resolver, clock=None):
    """Install an exact endpoint/template-scoped, zero-action context supplier."""
    if (type(app) is not Flask or is_production_environment() or app._got_first_request
            or _KEY in app.extensions or not _registered(app)):
        raise LocalBillingCancellationViewError(
            'local unambiguous pre-request installation required')
    if not callable(membership_resolver) or not callable(live_cancellation_fact_resolver):
        raise LocalBillingCancellationViewError('explicit dependencies required')
    if clock is not None and not callable(clock):
        raise LocalBillingCancellationViewError('invalid clock dependency')
    access = _Access(membership_resolver, live_cancellation_fact_resolver)
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
