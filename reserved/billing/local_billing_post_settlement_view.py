"""Default-off local current-status copy for admitted post-settlement facts."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from flask import Flask, before_render_template, g, request

from reserved.auth import is_production_environment
import reserved.database as database
from reserved.web.v2 import billing_plans
from . import local_stripe_initial_payment as source


VERSION = 'reserved-w10-local-billing-post-settlement-view/1.0'
_KEY = 'reserved.billing.local_billing_post_settlement_view'
_WITHDRAWAL_CONTEXT = 'local_billing_full_withdrawal_copy'
_RESTORATION_CONTEXT = 'local_billing_later_period_restoration_copy'
_ENDPOINT = 'v2.billing_plans'
_TEMPLATE = 'v2/plans.html'
_CODE = billing_plans.__code__


class LocalBillingPostSettlementViewError(ValueError):
    """Value-free installation refusal."""


@dataclass(frozen=True, slots=True)
class LocalBillingPostSettlementRuntime:
    """Complete server-owned dependencies for the default-off local panel."""

    membership_resolver: object
    live_full_withdrawal_fact_resolver: object
    live_later_period_restoration_fact_resolver: object
    clock: object = None

    def __post_init__(self):
        if not all(callable(value) for value in (
                self.membership_resolver,
                self.live_full_withdrawal_fact_resolver,
                self.live_later_period_restoration_fact_resolver)):
            raise LocalBillingPostSettlementViewError(
                'complete callable runtime dependencies are required')
        if self.clock is not None and not callable(self.clock):
            raise LocalBillingPostSettlementViewError('runtime clock is invalid')


@dataclass(frozen=True)
class _Access:
    membership_resolver: object
    live_full_withdrawal_fact_resolver: object
    live_later_period_restoration_fact_resolver: object


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


def _display(value):
    return value.strftime('%-d %B %Y at %H:%M:%S UTC')


def _project(access, scope, now):
    withdrawal_fact = access.live_full_withdrawal_fact_resolver(*scope)
    restoration_fact = access.live_later_period_restoration_fact_resolver(*scope)
    withdrawal = (None if withdrawal_fact is None else
                  source.full_withdrawal_presentation_facts(withdrawal_fact, now=now))
    restoration = (None if restoration_fact is None else
                   source.later_period_restoration_presentation_facts(
                       restoration_fact, now=now))
    if (withdrawal is None) == (restoration is None):
        return None
    return withdrawal_fact, restoration_fact, withdrawal, restoration


def _copy(access, now):
    now = _utc(now)
    user_id = g.get('user_id')
    if type(user_id) is not int or database.get_user(user_id) is None:
        return None
    first_scope = _scope(access.membership_resolver(user_id))
    if first_scope is None:
        return None
    first = _project(access, first_scope, now)
    if first is None:
        return None

    # Re-resolve scope and both opaque handles. A changed, stale, conflicting,
    # or ambiguous source is never converted into customer copy.
    if database.get_user(user_id) is None:
        return None
    second_scope = _scope(access.membership_resolver(user_id))
    if second_scope != first_scope:
        return None
    second = _project(access, second_scope, now)
    if second is None or second[:2] != first[:2] or second[2:] != first[2:]:
        return None

    withdrawal, restoration = first[2:]
    if withdrawal is not None:
        if (set(withdrawal) != {
                'owner', 'billing_account', 'subscription',
                'withdrawal_verified_at_utc', 'disposition'}
                or (withdrawal['owner'], withdrawal['billing_account'],
                    withdrawal['subscription']) != first_scope
                or withdrawal['disposition'] != 'verified_full_withdrawal'):
            return None
        verified = _parsed(withdrawal['withdrawal_verified_at_utc'])
        if verified.microsecond or verified > now:
            return None
        return (_WITHDRAWAL_CONTEXT, {
            'heading': 'Paid access is paused',
            'summary': 'Paid access is paused after a verified full refund for this period.',
            'verification_label': 'Full refund verified at',
            'verification_utc': _stamp(verified),
            'verification_display': _display(verified),
        })

    if (set(restoration) != {
            'owner', 'billing_account', 'subscription',
            'restoration_verified_at_utc', 'access_start_utc',
            'service_end_exclusive_utc', 'disposition'}
            or (restoration['owner'], restoration['billing_account'],
                restoration['subscription']) != first_scope
            or restoration['disposition'] != 'verified_later_period_restoration'):
        return None
    verified = _parsed(restoration['restoration_verified_at_utc'])
    start = _parsed(restoration['access_start_utc'])
    end = _parsed(restoration['service_end_exclusive_utc'])
    if (any(value.microsecond for value in (verified, start, end))
            or not start <= now < end or verified > now):
        return None
    return (_RESTORATION_CONTEXT, {
        'heading': 'Current paid access',
        'summary': ('This current paid interval was established by a newly '
                    'verified later-period payment.'),
        'verification_label': 'Later-period payment verified at',
        'verification_utc': _stamp(verified),
        'verification_display': _display(verified),
        'interval_label': 'Current paid interval',
        'access_start_utc': _stamp(start),
        'service_end_exclusive_utc': _stamp(end),
        'interval_display': f'{_display(start)} until {_display(end)}',
    })


def install_local_billing_post_settlement_view(app, *, membership_resolver,
        live_full_withdrawal_fact_resolver,
        live_later_period_restoration_fact_resolver, clock=None):
    """Install one exact non-production, endpoint/template-scoped supplier."""
    if (type(app) is not Flask or is_production_environment() or app._got_first_request
            or _KEY in app.extensions or not _registered(app)):
        raise LocalBillingPostSettlementViewError(
            'local unambiguous pre-request installation required')
    if not all(callable(value) for value in (
            membership_resolver, live_full_withdrawal_fact_resolver,
            live_later_period_restoration_fact_resolver)):
        raise LocalBillingPostSettlementViewError('explicit dependencies required')
    if clock is not None and not callable(clock):
        raise LocalBillingPostSettlementViewError('invalid clock dependency')
    access = _Access(membership_resolver, live_full_withdrawal_fact_resolver,
                     live_later_period_restoration_fact_resolver)
    effective_clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def supply(sender, template, context, **extra):
        conflict = any(name in context for name in
                       (_WITHDRAWAL_CONTEXT, _RESTORATION_CONTEXT))
        context.pop(_WITHDRAWAL_CONTEXT, None)
        context.pop(_RESTORATION_CONTEXT, None)
        if (is_production_environment() or request.endpoint != _ENDPOINT
                or request.method != 'GET' or template.name != _TEMPLATE
                or conflict or not _registered(app)):
            return
        try:
            copy = _copy(access, effective_clock())
        except Exception:
            return
        if copy is not None and not is_production_environment():
            context[copy[0]] = copy[1]

    before_render_template.connect(supply, app, weak=False)
    app.extensions[_KEY] = supply
    return None
