"""Actual authenticated plans requests over live scheduled-cancellation evidence."""

from datetime import datetime, timedelta, timezone

import pytest

import reserved.database as db
from reserved.billing import local_billing_cancellation_view as local
from reserved.billing import local_stripe_initial_payment as source
from tests import test_w10_local_dashboard_access as dashboard
from tests import test_w10_local_paid_surface_access as paid
from tests.test_w10_stripe_cancellation import CancellationHarness
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


app = paid.app
MARKER = 'id="w10-local-cancellation-heading"'


@pytest.fixture
def scheduled(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = CancellationHarness(tmp_path / 'scheduled-view.db', uid)
    assert harness.ingest().disposition == 'admitted'
    harness.prepare_cancellation()
    result = harness.cancel()
    assert result.disposition == 'admitted'
    yield client, uid, harness, result.fact
    harness.repo.close()


def _scope(harness):
    return tuple(harness.kwargs[name]
                 for name in ('owner', 'billing_account', 'subscription'))


def _args(uid, harness, fact, *, clock=None, **overrides):
    scope = _scope(harness)
    result = dict(
        membership_resolver=lambda value: scope if value == uid else None,
        live_cancellation_fact_resolver=(
            lambda owner, account, subscription: fact
            if (owner, account, subscription) == scope else None),
        clock=clock or harness.cancellation_now,
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


def test_live_scheduled_end_renders_unchanged_s6f_copy(scheduled):
    client, uid, harness, fact = scheduled
    local.install_local_billing_cancellation_view(
        client.application, **_args(uid, harness, fact))
    response = _page(client, True)
    details = source.cancellation_presentation_facts(fact)
    boundary = datetime.fromisoformat(details['paid_through_exclusive_utc'])
    display = boundary.strftime('%-d %B %Y at %H:%M:%S UTC')
    for value in (
        'Your subscription will not renew',
        'Your cancellation has been recorded for the end of your current paid period.',
        'Future automatic renewals are stopped.',
        details['paid_through_exclusive_utc'].replace('+00:00', 'Z'),
        display,
        'This does not affect any mandatory consumer or statutory rights.',
        '£29 per month', '£156 for six months', '£288 per year',
    ):
        assert value in response.text
    panel = response.text.split(MARKER)[1].split('</section>')[0]
    assert '<form' not in panel and 'paid_receipt_id' not in response.text
    assert all(value not in response.text for value in _scope(harness))


@pytest.mark.parametrize('offset,visible', [
    (timedelta(microseconds=-1), False),
    (timedelta(0), True),
])
def test_claim_starts_only_at_verified_instant(scheduled, offset, visible):
    client, uid, harness, fact = scheduled
    verified = datetime.fromisoformat(
        source.cancellation_presentation_facts(fact)['cancellation_verified_at_utc'])
    local.install_local_billing_cancellation_view(
        client.application, **_args(uid, harness, fact, clock=lambda: verified + offset))
    _page(client, visible)


@pytest.mark.parametrize('offset,visible', [
    (timedelta(microseconds=-1), True),
    (timedelta(0), False),
    (timedelta(microseconds=1), False),
])
def test_exclusive_paid_end_suppresses_panel(scheduled, offset, visible):
    client, uid, harness, fact = scheduled
    end = datetime.fromisoformat(
        source.cancellation_presentation_facts(fact)['paid_through_exclusive_utc'])
    local.install_local_billing_cancellation_view(
        client.application, **_args(uid, harness, fact, clock=lambda: end + offset))
    _page(client, visible)


@pytest.mark.parametrize('fault', [
    'missing_membership', 'wrong_scope', 'deleted_user', 'resolver_error',
    'missing_fact', 'changed_source', 'naive_clock', 'malformed_clock',
])
def test_missing_changed_or_cross_scope_evidence_is_value_free(
        scheduled, monkeypatch, fault):
    client, uid, harness, fact = scheduled
    args = _args(uid, harness, fact)
    if fault == 'missing_membership':
        args['membership_resolver'] = lambda _: None
    elif fault == 'wrong_scope':
        args['membership_resolver'] = lambda _: ('other-owner', *_scope(harness)[1:])
    elif fault == 'deleted_user':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    elif fault == 'resolver_error':
        args['live_cancellation_fact_resolver'] = lambda *values: (_ for _ in ()).throw(
            ValueError('private source detail'))
    elif fault == 'missing_fact':
        args['live_cancellation_fact_resolver'] = lambda *values: None
    elif fault == 'changed_source':
        calls = []
        def changed(*values):
            calls.append(True)
            return fact if len(calls) == 1 else None
        args['live_cancellation_fact_resolver'] = changed
    elif fault == 'naive_clock':
        args['clock'] = lambda: harness.cancellation_now().replace(tzinfo=None)
    else:
        args['clock'] = lambda: '2026-10-01T00:00:00Z'
    local.install_local_billing_cancellation_view(client.application, **args)
    response = _page(client, False)
    assert 'private source detail' not in response.text


def test_later_full_withdrawal_invalidates_prior_cancellation_claim(scheduled):
    client, uid, harness, fact = scheduled
    local.install_local_billing_cancellation_view(
        client.application, **_args(uid, harness, fact,
                                    clock=lambda: harness.cancellation_now() + timedelta(seconds=2)))
    _page(client, True)
    WithdrawalHarness.prepare_withdrawal(harness)
    harness.withdrawal_time = harness.cancellation_now() + timedelta(seconds=1)
    assert WithdrawalHarness.withdraw(
        harness, now=harness.withdrawal_time).disposition == 'admitted'
    _page(client, False)


def test_reconciliation_conflict_invalidates_prior_cancellation_claim(scheduled):
    client, uid, harness, fact = scheduled
    local.install_local_billing_cancellation_view(
        client.application, **_args(uid, harness, fact))
    _page(client, True)
    harness.event['pending_webhooks'] = 2
    result = harness.cancel()
    assert result.disposition == 'reconciliation_required'
    _page(client, False)


@pytest.mark.parametrize('key,value', [
    ('FLASK_ENV', 'production'),
    ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic'),
])
def test_production_install_and_request_fail_closed(scheduled, monkeypatch, key, value):
    client, uid, harness, fact = scheduled
    args = _args(uid, harness, fact)
    with monkeypatch.context() as scoped:
        scoped.setenv(key, value)
        with pytest.raises(local.LocalBillingCancellationViewError):
            local.install_local_billing_cancellation_view(client.application, **args)
    local.install_local_billing_cancellation_view(client.application, **args)
    _page(client, True)
    monkeypatch.setenv(key, value)
    _page(client, False)


@pytest.mark.parametrize('fault', ['duplicate', 'late', 'replacement', 'alias', 'method'])
def test_invalid_installation_is_atomic(app, tmp_path, fault):
    client, uid = dashboard._authenticated_client(app)
    harness = CancellationHarness(tmp_path / 'installation.db', uid)
    try:
        assert harness.ingest().disposition == 'admitted'
        harness.prepare_cancellation(); fact = harness.cancel().fact
        args = _args(uid, harness, fact)
        if fault == 'duplicate':
            local.install_local_billing_cancellation_view(app, **args)
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
        with pytest.raises(local.LocalBillingCancellationViewError):
            local.install_local_billing_cancellation_view(app, **args)
        assert before == (app.extensions, app.view_functions)
    finally:
        harness.repo.close()


def test_import_and_uninstalled_app_have_no_panel(app):
    client, _ = dashboard._authenticated_client(app)
    _page(client, False)
