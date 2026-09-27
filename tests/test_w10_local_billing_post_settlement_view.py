"""Authenticated default-off plans copy from live post-settlement facts only."""

from datetime import datetime, timedelta

import pytest

import reserved.database as db
from reserved.billing import local_billing_post_settlement_view as local
from reserved.billing import local_stripe_initial_payment as source
from tests import test_w10_local_dashboard_access as dashboard
from tests import test_w10_local_paid_surface_access as paid
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness
from tests.test_w10_stripe_later_period_restoration import RestorationHarness


app = paid.app
WITHDRAWAL_MARKER = 'id="w10-local-full-withdrawal-heading"'
RESTORATION_MARKER = 'id="w10-local-later-period-restoration-heading"'


def _scope(harness):
    return tuple(harness.kwargs[name]
                 for name in ('owner', 'billing_account', 'subscription'))


def _args(uid, harness, withdrawal=None, restoration=None, *, clock, **overrides):
    scope = _scope(harness)
    result = dict(
        membership_resolver=lambda value: scope if value == uid else None,
        live_full_withdrawal_fact_resolver=(
            lambda owner, account, subscription: withdrawal
            if (owner, account, subscription) == scope else None),
        live_later_period_restoration_fact_resolver=(
            lambda owner, account, subscription: restoration
            if (owner, account, subscription) == scope else None),
        clock=clock,
    )
    result.update(overrides)
    return result


def _page(client, withdrawal=False, restoration=False):
    response = client.get('/v2/plans')
    assert response.status_code == 200
    assert (WITHDRAWAL_MARKER in response.text) is withdrawal
    assert (RESTORATION_MARKER in response.text) is restoration
    assert 'no-store' in response.headers['Cache-Control']
    return response


@pytest.fixture
def withdrawn(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = WithdrawalHarness(tmp_path / 'withdrawn-status.db', uid)
    assert harness.ingest().disposition == 'admitted'
    harness.prepare_withdrawal()
    result = harness.withdraw()
    assert result.disposition == 'admitted'
    yield client, uid, harness, result.fact
    harness.repo.close()


@pytest.fixture
def restored(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = RestorationHarness(tmp_path / 'restored-status.db', uid)
    assert harness.ingest().disposition == 'admitted'
    assert harness.withdraw_initial().disposition == 'admitted'
    harness.prepare_restoration()
    result = harness.restore()
    assert result.disposition == 'admitted'
    yield client, uid, harness, result.fact
    harness.repo.close()


def test_current_verified_full_withdrawal_renders_only_fixed_status(withdrawn):
    client, uid, harness, fact = withdrawn
    local.install_local_billing_post_settlement_view(
        client.application, **_args(uid, harness, withdrawal=fact,
                                    clock=lambda: harness.withdrawal_time))
    response = _page(client, withdrawal=True)
    panel = response.text.split(WITHDRAWAL_MARKER)[1].split('</section>')[0]
    verified = source.full_withdrawal_presentation_facts(
        fact, now=harness.withdrawal_time)['withdrawal_verified_at_utc']
    assert 'Paid access is paused after a verified full refund for this period.' in panel
    assert verified.replace('+00:00', 'Z') in panel
    assert '<form' not in panel
    assert all(value not in panel for value in (*_scope(harness), 'Stripe', '£',
                                                  'refund_id', 'receipt_id', 'renew'))


def test_current_later_period_restoration_renders_exact_fixed_interval(restored):
    client, uid, harness, fact = restored
    clock = lambda: harness.initial_end
    assert source.later_period_restoration_presentation_facts(fact, now=clock())
    local.install_local_billing_post_settlement_view(
        client.application, **_args(uid, harness, restoration=fact, clock=clock))
    response = _page(client, restoration=True)
    panel = response.text.split(RESTORATION_MARKER)[1].split('</section>')[0]
    details = source.later_period_restoration_presentation_facts(fact, now=clock())
    for value in (
            'This current paid interval was established by a newly verified later-period payment.',
            datetime.fromisoformat(details['access_start_utc']).strftime(
                '%-d %B %Y at %H:%M:%S UTC'),
            datetime.fromisoformat(details['service_end_exclusive_utc']).strftime(
                '%-d %B %Y at %H:%M:%S UTC')):
        assert value in panel
    assert '<form' not in panel
    assert all(value not in panel for value in (*_scope(harness), 'Stripe', '£',
                                                  'receipt_id', 'cancel', 'renew'))


@pytest.mark.parametrize('kind,offset,visible', [
    ('withdrawal', timedelta(microseconds=-1), True),
    ('withdrawal', timedelta(0), False),
    ('restoration', timedelta(microseconds=-1), True),
    ('restoration', timedelta(0), False),
])
def test_current_period_boundaries_fail_closed(app, tmp_path, kind, offset, visible):
    client, uid = dashboard._authenticated_client(app)
    if kind == 'withdrawal':
        harness = WithdrawalHarness(tmp_path / 'withdrawal-boundary.db', uid)
        assert harness.ingest().disposition == 'admitted'
        harness.prepare_withdrawal(); fact = harness.withdraw().fact
        end = datetime.fromisoformat(source.full_withdrawal_fact_details(fact)['paid_service_end'])
        args = _args(uid, harness, withdrawal=fact, clock=lambda: end + offset)
    else:
        harness = RestorationHarness(tmp_path / 'restoration-boundary.db', uid)
        assert harness.ingest().disposition == 'admitted'
        assert harness.withdraw_initial().disposition == 'admitted'
        harness.prepare_restoration(); fact = harness.restore().fact
        end = datetime.fromisoformat(
            source.later_period_restoration_fact_details(fact)['service_end'])
        args = _args(uid, harness, restoration=fact, clock=lambda: end + offset)
    try:
        local.install_local_billing_post_settlement_view(client.application, **args)
        _page(client, withdrawal=visible if kind == 'withdrawal' else False,
              restoration=visible if kind == 'restoration' else False)
    finally:
        harness.repo.close()


@pytest.mark.parametrize('fault', [
    'missing_scope', 'cross_scope', 'missing_fact', 'changed_fact', 'malformed_fact',
    'ambiguous', 'deleted_user', 'bad_clock',
])
def test_hostile_or_changed_evidence_is_suppressed(withdrawn, monkeypatch, fault):
    client, uid, harness, fact = withdrawn
    args = _args(uid, harness, withdrawal=fact, clock=lambda: harness.withdrawal_time)
    if fault == 'missing_scope':
        args['membership_resolver'] = lambda _: None
    elif fault == 'cross_scope':
        args['membership_resolver'] = lambda _: ('other', *_scope(harness)[1:])
    elif fault == 'missing_fact':
        args['live_full_withdrawal_fact_resolver'] = lambda *values: None
    elif fault == 'changed_fact':
        calls = []
        def changed(*values):
            calls.append(True)
            return fact if len(calls) == 1 else None
        args['live_full_withdrawal_fact_resolver'] = changed
    elif fault == 'malformed_fact':
        args['live_full_withdrawal_fact_resolver'] = lambda *values: object()
    elif fault == 'ambiguous':
        args['live_later_period_restoration_fact_resolver'] = lambda *values: fact
    elif fault == 'deleted_user':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    else:
        args['clock'] = lambda: 'not-an-instant'
    local.install_local_billing_post_settlement_view(client.application, **args)
    response = _page(client)
    assert 'private' not in response.text


def test_reconciliation_conflict_suppresses_full_withdrawal(withdrawn):
    client, uid, harness, fact = withdrawn
    local.install_local_billing_post_settlement_view(
        client.application, **_args(uid, harness, withdrawal=fact,
                                    clock=lambda: harness.withdrawal_time))
    _page(client, withdrawal=True)
    harness.event['pending_webhooks'] = 2
    assert harness.withdraw().disposition == 'reconciliation_required'
    _page(client)


@pytest.mark.parametrize('key,value', [
    ('FLASK_ENV', 'production'),
    ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic'),
])
def test_production_install_and_request_fail_closed(withdrawn, monkeypatch, key, value):
    client, uid, harness, fact = withdrawn
    args = _args(uid, harness, withdrawal=fact, clock=lambda: harness.withdrawal_time)
    with monkeypatch.context() as scoped:
        scoped.setenv(key, value)
        with pytest.raises(local.LocalBillingPostSettlementViewError):
            local.install_local_billing_post_settlement_view(client.application, **args)
    local.install_local_billing_post_settlement_view(client.application, **args)
    _page(client, withdrawal=True)
    monkeypatch.setenv(key, value)
    _page(client)


@pytest.mark.parametrize('fault', ['duplicate', 'late', 'replacement', 'alias', 'method'])
def test_installation_cannot_replace_or_alias_route(app, tmp_path, fault):
    client, uid = dashboard._authenticated_client(app)
    harness = WithdrawalHarness(tmp_path / 'post-settlement-install.db', uid)
    try:
        assert harness.ingest().disposition == 'admitted'
        harness.prepare_withdrawal(); fact = harness.withdraw().fact
        args = _args(uid, harness, withdrawal=fact, clock=lambda: harness.withdrawal_time)
        if fault == 'duplicate':
            local.install_local_billing_post_settlement_view(app, **args)
        elif fault == 'late':
            client.get('/v2/plans')
        elif fault == 'replacement':
            app.view_functions['v2.billing_plans'] = lambda: 'changed'
        elif fault == 'alias':
            app.add_url_rule('/alias', 'post-settlement-alias',
                             app.view_functions['v2.billing_plans'])
        else:
            next(rule for rule in app.url_map.iter_rules()
                 if rule.endpoint == 'v2.billing_plans').methods.add('POST')
        before = dict(app.extensions), dict(app.view_functions)
        with pytest.raises(local.LocalBillingPostSettlementViewError):
            local.install_local_billing_post_settlement_view(app, **args)
        assert before == (app.extensions, app.view_functions)
    finally:
        harness.repo.close()


def test_uninstalled_default_is_absent(app):
    client, _ = dashboard._authenticated_client(app)
    _page(client)
