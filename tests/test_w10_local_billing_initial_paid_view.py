"""Authenticated plans rendering from exact live initial-payment evidence."""

from datetime import datetime, timedelta
from html import unescape

import pytest

import reserved.database as db
from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_billing_initial_paid_view as local
from tests import test_w10_local_dashboard_access as dashboard
from tests import test_w10_local_paid_surface_access as paid
from tests.test_w10_stripe_cancellation import CancellationHarness
from tests.test_w10_stripe_initial_payment_ingress import Harness, NOW
from tests.test_w10_stripe_successful_renewal import RenewalHarness


app = paid.app
MARKER = 'id="w10-local-initial-paid-heading"'


@pytest.fixture
def initial(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = Harness(tmp_path / 'initial-paid-view.db', uid)
    result = harness.ingest()
    assert result.disposition == 'admitted'
    yield client, uid, harness, result.fact
    harness.repo.close()


def _scope(harness):
    return tuple(harness.kwargs[name]
                 for name in ('owner', 'billing_account', 'subscription'))


def _args(uid, harness, fact, *, clock=lambda: NOW, **overrides):
    scope = _scope(harness)
    result = dict(
        membership_resolver=lambda value: scope if value == uid else None,
        live_paid_fact_resolver=(
            lambda owner, account, subscription: fact
            if (owner, account, subscription) == scope else None),
        clock=clock,
    )
    result.update(overrides)
    return result


def _page(client, present):
    response = client.get('/v2/plans')
    assert response.status_code == 200
    assert (MARKER in response.text) is present
    assert 'Purchasing a plan or changing access is not available in this preview.' in response.text
    assert 'no-store' in response.headers['Cache-Control']
    return response


@pytest.mark.parametrize('plan,label', [
    ('monthly', 'monthly plan'),
    ('six_month', 'six-month plan'),
    ('yearly', 'yearly plan'),
])
def test_exact_live_initial_payment_renders_only_bounded_copy(
        app, tmp_path, plan, label):
    client, uid = dashboard._authenticated_client(app)
    harness = Harness(tmp_path / f'{plan}.db', uid, plan)
    try:
        result = harness.ingest()
        fact = exact.initial_payment_presentation_facts(result.fact, now=NOW)
        assert fact['plan'] == plan and fact['disposition'] == 'verified_initial_payment'
        local.install_local_billing_initial_paid_view(
            app, **_args(uid, harness, result.fact))
        response = _page(client, True)
        for value in (
            'Your initial subscription payment is verified',
            f'We verified your initial payment for the {label}.',
            'This confirms the initial payment only.',
            'It does not confirm automatic renewal or any future payment.',
            "Access remains subject to Reserved's entitlement checks.",
            '£29 per month', '£156 for six months', '£288 per year',
        ):
            assert value in unescape(response.text)
        panel = response.text.split(MARKER)[1].split('</section>')[0]
        assert '<form' not in panel
        assert 'set to renew' not in panel and 'Next renewal' not in panel
        assert all(value not in response.text for value in _scope(harness))
        assert fact['receipt_id'] not in response.text and fact['fact_id'] not in response.text
    finally:
        harness.repo.close()


@pytest.mark.parametrize('offset,visible', [
    (timedelta(microseconds=-1), True),
    (timedelta(0), False),
    (timedelta(microseconds=1), False),
])
def test_exclusive_paid_end_suppresses_panel(initial, offset, visible):
    client, uid, harness, fact = initial
    end = datetime.fromisoformat(
        exact.initial_payment_presentation_facts(fact, now=NOW)[
            'paid_through_exclusive_utc'])
    local.install_local_billing_initial_paid_view(
        client.application, **_args(uid, harness, fact, clock=lambda: end + offset))
    _page(client, visible)


@pytest.mark.parametrize('fault', [
    'missing_membership', 'wrong_scope', 'deleted_user', 'resolver_error',
    'missing_fact', 'changed_source', 'naive_clock', 'malformed_clock',
])
def test_missing_changed_or_cross_scope_evidence_is_value_free(
        initial, monkeypatch, fault):
    client, uid, harness, fact = initial
    args = _args(uid, harness, fact)
    if fault == 'missing_membership':
        args['membership_resolver'] = lambda _: None
    elif fault == 'wrong_scope':
        args['membership_resolver'] = lambda _: ('other-owner', *_scope(harness)[1:])
    elif fault == 'deleted_user':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    elif fault == 'resolver_error':
        args['live_paid_fact_resolver'] = lambda *values: (_ for _ in ()).throw(
            ValueError('private source detail'))
    elif fault == 'missing_fact':
        args['live_paid_fact_resolver'] = lambda *values: None
    elif fault == 'changed_source':
        calls = []
        def changed(*values):
            calls.append(True)
            return fact if len(calls) == 1 else None
        args['live_paid_fact_resolver'] = changed
    elif fault == 'naive_clock':
        args['clock'] = lambda: NOW.replace(tzinfo=None)
    else:
        args['clock'] = lambda: '2026-10-01T00:00:00Z'
    local.install_local_billing_initial_paid_view(client.application, **args)
    response = _page(client, False)
    assert 'private source detail' not in response.text


def test_reconciliation_conflict_suppresses_prior_initial_fact(initial):
    client, uid, harness, fact = initial
    local.install_local_billing_initial_paid_view(
        client.application, **_args(uid, harness, fact))
    _page(client, True)
    harness.event['pending_webhooks'] = 2
    assert harness.ingest().disposition == 'reconciliation_required'
    _page(client, False)


def test_scheduled_cancellation_suppresses_initial_payment_panel(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = CancellationHarness(tmp_path / 'initial-then-cancel.db', uid)
    try:
        initial = harness.ingest()
        now = [harness.cancellation_now()]
        local.install_local_billing_initial_paid_view(
            app, **_args(uid, harness, initial.fact, clock=lambda: now[0]))
        _page(client, True)
        harness.prepare_cancellation(created=now[0])
        assert harness.cancel(now=now[0]).disposition == 'admitted'
        _page(client, False)
    finally:
        harness.repo.close()


def test_successful_renewal_suppresses_initial_only_panel(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = RenewalHarness(tmp_path / 'initial-then-renew.db', uid)
    try:
        initial = harness.ingest()
        now = [NOW]
        local.install_local_billing_initial_paid_view(
            app, **_args(uid, harness, initial.fact, clock=lambda: now[0]))
        _page(client, True)
        harness.prepare_renewal()
        assert harness.renew().disposition == 'admitted'
        now[0] = harness.initial_end + timedelta(seconds=1)
        _page(client, False)
    finally:
        harness.repo.close()


@pytest.mark.parametrize('key,value', [
    ('FLASK_ENV', 'production'),
    ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic'),
])
def test_production_install_and_request_fail_closed(initial, monkeypatch, key, value):
    client, uid, harness, fact = initial
    args = _args(uid, harness, fact)
    with monkeypatch.context() as scoped:
        scoped.setenv(key, value)
        with pytest.raises(local.LocalBillingInitialPaidViewError):
            local.install_local_billing_initial_paid_view(client.application, **args)
    local.install_local_billing_initial_paid_view(client.application, **args)
    _page(client, True)
    monkeypatch.setenv(key, value)
    _page(client, False)


@pytest.mark.parametrize('fault', ['duplicate', 'late', 'replacement', 'alias', 'method'])
def test_invalid_installation_is_atomic(app, tmp_path, fault):
    client, uid = dashboard._authenticated_client(app)
    harness = Harness(tmp_path / 'installation.db', uid)
    try:
        fact = harness.ingest().fact
        args = _args(uid, harness, fact)
        if fault == 'duplicate':
            local.install_local_billing_initial_paid_view(app, **args)
        elif fault == 'late':
            client.get('/v2/plans')
        elif fault == 'replacement':
            app.view_functions['v2.billing_plans'] = lambda: 'changed'
        elif fault == 'alias':
            app.add_url_rule('/alias', 'alias', app.view_functions['v2.billing_plans'])
        else:
            next(rule for rule in app.url_map.iter_rules()
                 if rule.endpoint == 'v2.billing_plans').methods.add('POST')
        before = dict(app.extensions), dict(app.view_functions)
        with pytest.raises(local.LocalBillingInitialPaidViewError):
            local.install_local_billing_initial_paid_view(app, **args)
        assert before == (app.extensions, app.view_functions)
    finally:
        harness.repo.close()


def test_uninstalled_app_has_no_panel(app):
    client, uid = dashboard._authenticated_client(app)
    _page(client, False)


def test_non_fact_pending_shape_has_no_panel(app):
    client, uid = dashboard._authenticated_client(app)
    # A Checkout-like pending shape is not a live exact paid fact.
    local.install_local_billing_initial_paid_view(
        app,
        membership_resolver=lambda value: ('owner', 'account', 'subscription'),
        live_paid_fact_resolver=lambda *scope: {
            'status': 'recorded_pending_reconciliation',
        },
        clock=lambda: NOW,
    )
    _page(client, False)
