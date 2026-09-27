"""Authenticated plans panel from one exact live successful-renewal fact."""
from datetime import datetime, timedelta
from html import unescape

import pytest

import reserved.database as db
from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_billing_successful_renewal_view as local
from tests import test_w10_local_dashboard_access as dashboard
from tests import test_w10_local_paid_surface_access as paid
from tests.test_w10_stripe_initial_payment_ingress import NOW
from tests.test_w10_stripe_successful_renewal import RenewalHarness


app = paid.app
MARKER = 'id="w10-local-successful-renewal-heading"'


@pytest.fixture
def renewal(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    harness = RenewalHarness(tmp_path / 'renewal-panel.db', uid)
    assert harness.ingest().disposition == 'admitted'
    harness.prepare_renewal()
    result = harness.renew(now=harness.initial_end)
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
        live_successful_renewal_fact_resolver=(
            lambda owner, account, subscription: fact
            if (owner, account, subscription) == scope else None),
        clock=clock or (lambda: harness.initial_end),
    )
    result.update(overrides)
    return result


def _page(client, present):
    response = client.get('/v2/plans')
    assert response.status_code == 200
    assert (MARKER in response.text) is present
    assert 'no-store' in response.headers['Cache-Control']
    return response


def test_verified_live_successful_renewal_renders_current_period_only(renewal):
    client, uid, harness, fact = renewal
    facts = exact.successful_renewal_presentation_facts(
        fact, now=harness.initial_end)
    assert facts['disposition'] == 'verified_successful_renewal'
    local.install_local_billing_successful_renewal_view(
        client.application, **_args(uid, harness, fact))
    response = _page(client, True)
    panel = unescape(response.text.split(MARKER)[1].split('</section>')[0])
    for value in (
        'Current paid period',
        'verified successful renewal fact',
        'Renewal fact verified at',
        'Current paid period:',
        'This panel makes no statement beyond this current paid period.',
    ):
        assert value in panel
    assert '<form' not in panel
    assert all(value not in panel for value in _scope(harness))
    assert facts['receipt_id'] not in panel and facts['fact_id'] not in panel
    assert all(value not in panel.lower() for value in (
        'future', 'cancellation', 'entitlement', 'access', 'refund',
        'provider', 'automatic', 'payment successful', 'w10', 'closure',
    ))


@pytest.mark.parametrize('offset,visible', [
    (timedelta(microseconds=-1), True),
    (timedelta(0), False),
    (timedelta(microseconds=1), False),
])
def test_exclusive_renewal_paid_end_suppresses_panel(renewal, offset, visible):
    client, uid, harness, fact = renewal
    # The source-issued facts provide the authoritative successor boundary.
    end = datetime.fromisoformat(
        exact.successful_renewal_presentation_facts(fact, now=harness.initial_end)[
            'paid_through_exclusive_utc'])
    local.install_local_billing_successful_renewal_view(
        client.application, **_args(uid, harness, fact, clock=lambda: end + offset))
    _page(client, visible)


@pytest.mark.parametrize('fault', [
    'missing_membership', 'wrong_scope', 'deleted_user', 'resolver_error',
    'missing_fact', 'changed_source', 'naive_clock', 'initial_fact',
])
def test_nonrenewal_cross_scope_or_changed_evidence_is_value_free(renewal, monkeypatch, fault):
    client, uid, harness, fact = renewal
    args = _args(uid, harness, fact)
    if fault == 'missing_membership':
        args['membership_resolver'] = lambda _: None
    elif fault == 'wrong_scope':
        args['membership_resolver'] = lambda _: ('other-owner', *_scope(harness)[1:])
    elif fault == 'deleted_user':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    elif fault == 'resolver_error':
        args['live_successful_renewal_fact_resolver'] = lambda *values: (_ for _ in ()).throw(
            ValueError('private source detail'))
    elif fault == 'missing_fact':
        args['live_successful_renewal_fact_resolver'] = lambda *values: None
    elif fault == 'changed_source':
        calls = []
        def changed(*values):
            calls.append(True)
            return fact if len(calls) == 1 else None
        args['live_successful_renewal_fact_resolver'] = changed
    elif fault == 'naive_clock':
        args['clock'] = lambda: harness.initial_end.replace(tzinfo=None)
    else:
        args['live_successful_renewal_fact_resolver'] = lambda *values: harness.ingest().fact
    local.install_local_billing_successful_renewal_view(client.application, **args)
    response = _page(client, False)
    assert 'private source detail' not in response.text


def test_production_install_and_request_fail_closed(renewal, monkeypatch):
    client, uid, harness, fact = renewal
    with monkeypatch.context() as scoped:
        scoped.setenv('FLASK_ENV', 'production')
        with pytest.raises(local.LocalBillingSuccessfulRenewalViewError):
            local.install_local_billing_successful_renewal_view(
                client.application, **_args(uid, harness, fact))
    local.install_local_billing_successful_renewal_view(
        client.application, **_args(uid, harness, fact))
    _page(client, True)
    monkeypatch.setenv('FLASK_ENV', 'production')
    _page(client, False)


def test_uninstalled_app_has_no_panel(app):
    client, _ = dashboard._authenticated_client(app)
    _page(client, False)


@pytest.mark.parametrize('fault', ['duplicate', 'late', 'replacement', 'alias', 'method'])
def test_invalid_installation_is_atomic(app, tmp_path, fault):
    client, uid = dashboard._authenticated_client(app)
    harness = RenewalHarness(tmp_path / 'renewal-installation.db', uid)
    try:
        assert harness.ingest().disposition == 'admitted'
        harness.prepare_renewal()
        fact = harness.renew(now=harness.initial_end).fact
        args = _args(uid, harness, fact)
        if fault == 'duplicate':
            local.install_local_billing_successful_renewal_view(app, **args)
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
        with pytest.raises(local.LocalBillingSuccessfulRenewalViewError):
            local.install_local_billing_successful_renewal_view(app, **args)
        assert before == (app.extensions, app.view_functions)
    finally:
        harness.repo.close()
