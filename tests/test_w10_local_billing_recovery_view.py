"""Real signed requests; disposable databases; genuine unchanged S3C issuance."""
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest
from flask import render_template
import reserved.database as db
from reserved.billing import local_billing_recovery_view as local
from reserved.billing import local_paid_surface_access as paid
from reserved.billing import runtime_entitlement_admission as admission
from tests import test_w10_local_dashboard_access as f
from tests import test_w10_local_paid_surface_access as p

app = p.app
repo = p.repo
START = datetime(2026, 11, 1, tzinfo=timezone.utc)
END = datetime(2026, 11, 8, tzinfo=timezone.utc)
MARKER = 'id="w10-local-recovery-heading"'


def history(repo):
    return f._append_recovery(repo, f._append(repo))


def install(app, repo, **overrides):
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid, clock=lambda: f.CLOCK_RECOVERY, **overrides)
    local.install_local_billing_recovery_view(app, **args)
    return client, uid


def page(client, present=False, path='/v2/plans'):
    response = client.get(path)
    assert response.status_code == 200
    assert (MARKER in response.text) is present
    assert 'Purchasing a plan or changing access is not available in this preview.' in response.text
    assert 'no-store' in response.headers['Cache-Control']
    for private in f.SCOPE:
        assert private not in response.text
    return response


def test_real_recovery_page_alongside_prices(app, repo):
    history(repo)
    client, _ = install(app, repo)
    response = page(client, True)
    for text in ('Your subscription payment is being recovered',
                 'We could not verify your renewal payment.',
                 '8 November 2026 at 00:00:00 UTC', '2026-11-08T00:00:00Z',
                 '£29 per month', '£156 for six months', '£288 per year',
                 'unless payment recovery has been verified'):
        assert text in response.text
    assert '<form' not in response.text.split(MARKER)[1].split('</section>')[0]


@pytest.mark.parametrize('now,visible', [
    (START - timedelta(microseconds=1), False), (START, True),
    (START + timedelta(microseconds=1), True),
    (END - timedelta(microseconds=1), True), (END, False),
    (END + timedelta(microseconds=1), False), (END + timedelta(days=1), False),
    (START.replace(tzinfo=None), False), ('2026-11-02', False),
])
def test_exact_request_time_before_formatting(app, repo, now, visible):
    history(repo)
    client, uid = f._authenticated_client(app)
    local.install_local_billing_recovery_view(app, **p.bindings(repo, uid, clock=lambda: now))
    page(client, visible)


def test_no_cached_claim_after_clock_expiry(app, repo):
    history(repo)
    now = [f.CLOCK_RECOVERY]
    client, uid = f._authenticated_client(app)
    local.install_local_billing_recovery_view(app, **p.bindings(repo, uid, clock=lambda: now[0]))
    page(client, True)
    now[0] = END
    page(client)


@pytest.mark.parametrize('state', ['missing', 'paid', 'withdrawal', 'restoration', 'ambiguous_paid'])
def test_other_states_do_not_invent_status(app, repo, state):
    if state != 'missing':
        initial = f._append(repo)
        if state in ('withdrawal', 'restoration'):
            withdrawn = f._append_withdrawal(repo, initial)
            if state == 'restoration':
                f._append_restoration(repo, withdrawn)
        elif state == 'ambiguous_paid':
            f._append_ambiguous(repo, initial)
    client, uid = f._authenticated_client(app)
    local.install_local_billing_recovery_view(app, **p.bindings(repo, uid, clock=lambda: f.CLOCK_RESTORATION))
    page(client)


def successor(repo, prior, *, withdrawal=False):
    return f._append(repo, source_event_id='evt-local-successor', source_event_digest=f.DIGEST_C,
        observation_kind='cancellation_confirmed' if withdrawal else 'renewal_payment_confirmed',
        effective_date=date(2026, 11, 3), paid_through=None if withdrawal else date(2026, 11, 30),
        state='suspended' if withdrawal else 'paid',
        valid_until_exclusive=date(2026, 11, 8) if withdrawal else date(2026, 12, 1),
        transition_effective_at_utc=datetime(2026, 11, 3, tzinfo=timezone.utc),
        derivation_kind='verified_full_withdrawal' if withdrawal else 'verified_renewal_payment',
        withdrawal_attribution='current_subscription_period' if withdrawal else 'not_applicable',
        expected_predecessor_identity=prior.content_identity, expected_sequence=3)


@pytest.mark.parametrize('withdrawal', [False, True])
def test_verified_successor_removes_recovery_claim(app, repo, withdrawal):
    recovery = history(repo)
    now = [f.CLOCK_RECOVERY]
    client, uid = f._authenticated_client(app)
    local.install_local_billing_recovery_view(app, **p.bindings(repo, uid, clock=lambda: now[0]))
    page(client, True)
    successor(repo, recovery, withdrawal=withdrawal)
    now[0] = datetime(2026, 11, 4, tzinfo=timezone.utc)
    page(client)


@pytest.mark.parametrize('fault', ['membership', 'owner', 'account', 'subscription', 'deleted',
                                  'lookup_exception', 'clock_exception', 'malformed', 'changed', 'unadmitted', 'source'])
def test_failed_evidence_produces_no_status(app, repo, monkeypatch, fault):
    history(repo)
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid, clock=lambda: f.CLOCK_RECOVERY)
    if fault in ('membership', 'owner', 'account', 'subscription'):
        scope = list(f.SCOPE)
        if fault != 'membership':
            scope[['owner', 'account', 'subscription'].index(fault)] = 'other'
        args['membership_resolver'] = lambda _: None if fault == 'membership' else tuple(scope)
    elif fault == 'deleted':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    elif fault in ('lookup_exception', 'clock_exception'):
        def fail(*args):
            raise ValueError('private synthetic error')
        if fault == 'lookup_exception':
            monkeypatch.setattr(db, 'get_user', fail)
        else:
            args['clock'] = fail
    elif fault == 'unadmitted':
        args['live_fact_resolver'] = lambda *args: {'state': 'payment_recovery'}
    elif fault == 'source':
        resolve = args['live_fact_resolver']
        def changed(*values):
            fact = resolve(*values)
            view = dict(fact.view)
            view['fact_identity'] = 'billing-fact:sha256-' + '0' * 64
            fact.view = tuple((key, view[key]) for key in f.FACT_KEYS)
            return fact
        args['live_fact_resolver'] = changed
    else:
        read = args['snapshot_reader']
        calls = []
        def altered(*scope):
            snapshot = read(*scope)
            calls.append(True)
            if fault == 'malformed':
                return replace(snapshot, entries=(None,))
            return replace(snapshot, subscription_id='changed') if len(calls) > 1 else snapshot
        args['snapshot_reader'] = altered
    local.install_local_billing_recovery_view(app, **args)
    response = page(client)
    assert 'private synthetic error' not in response.text


def test_anonymous_and_forged_session_never_claim(app, repo):
    history(repo)
    client, _ = install(app, repo)
    assert app.test_client().get('/v2/plans').status_code == 302
    with client.session_transaction() as session:
        session['_v2_user_id'] = '17'
    response = client.get('/v2/plans')
    assert MARKER not in response.text


def test_request_scope_is_not_membership(app, repo):
    history(repo)
    client, _ = install(app, repo, membership_resolver=lambda _: None)
    page(client, path='/v2/plans?owner=users:17&billing_account=billing:17&subscription=subscription:17')


@pytest.mark.parametrize('order', ['recovery_first', 'paid_first'])
def test_composes_with_paid_installer_and_preserves_route(app, repo, order):
    history(repo)
    client, uid = f._authenticated_client(app)
    original = app.view_functions['v2.billing_plans']
    now = [f.CLOCK_RECOVERY]
    args = p.bindings(repo, uid, clock=lambda: now[0])
    installers = [local.install_local_billing_recovery_view, paid.install_local_paid_surface_access]
    if order == 'paid_first':
        installers.reverse()
    for installer in installers:
        installer(app, **args)
    assert app.view_functions['v2.billing_plans'] is original
    page(client, True)
    assert client.get('/v2/settings').status_code == 200
    now[0] = END
    page(client)
    p.denied(client.get('/v2/settings'))
    assert client.post('/v2/plans').status_code == 405


@pytest.mark.parametrize('fault', ['duplicate', 'late', 'replacement', 'alias', 'method', 'binding'])
def test_invalid_installation_is_atomic(app, repo, fault):
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid)
    if fault == 'duplicate':
        local.install_local_billing_recovery_view(app, **args)
    elif fault == 'late':
        client.get('/v2/plans')
    elif fault == 'replacement':
        app.view_functions['v2.billing_plans'] = lambda: 'changed'
    elif fault == 'alias':
        app.add_url_rule('/alias', 'alias', app.view_functions['v2.billing_plans'])
    elif fault == 'method':
        next(r for r in app.url_map.iter_rules() if r.endpoint == 'v2.billing_plans').methods.add('POST')
    else:
        args['validate_admitted_billing_fact'] = None
    before = dict(app.extensions), dict(app.view_functions)
    with pytest.raises(local.LocalBillingRecoveryViewError):
        local.install_local_billing_recovery_view(app, **args)
    assert before == (app.extensions, app.view_functions)


@pytest.mark.parametrize('key,value', [('FLASK_ENV', 'production'), ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic')])
def test_production_install_and_request_closed(app, repo, monkeypatch, key, value):
    history(repo)
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid, clock=lambda: f.CLOCK_RECOVERY)
    with monkeypatch.context() as scoped:
        scoped.setenv(key, value)
        with pytest.raises(local.LocalBillingRecoveryViewError):
            local.install_local_billing_recovery_view(app, **args)
    local.install_local_billing_recovery_view(app, **args)
    page(client, True)
    monkeypatch.setenv(key, value)
    page(client)


def test_exact_endpoint_and_template_only(app, repo):
    history(repo)
    client, _ = install(app, repo)
    with app.test_request_context('/v2/plans'):
        from flask import g
        g.user_id = 1
        assert MARKER not in render_template('v2/settings.html', profile={})
    response = client.get('/v2/plans/monthly')
    assert MARKER not in response.text
    assert client.head('/v2/plans').data == b''


def test_hostile_presenter_copy_rejected(app, repo, monkeypatch):
    history(repo)
    original = local.build_payment_recovery_presentation
    def hostile(**kwargs):
        result = dict(original(**kwargs))
        copy = dict(result['copy'])
        copy['heading'] = '<script>private-owner</script>'
        result['copy'] = tuple(copy.items())
        return tuple(result.items())
    monkeypatch.setattr(local, 'build_payment_recovery_presentation', hostile)
    client, _ = install(app, repo)
    response = page(client)
    assert '<script>private-owner</script>' not in response.text


def test_admission_time_lineage_mutation_never_claims(app, repo):
    history(repo)
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid, clock=lambda: f.CLOCK_RECOVERY)
    validate = args['validate_admitted_billing_fact']
    local.install_local_billing_recovery_view(app, **args)
    touched = []
    def trace(frame, event, value):
        if frame.f_code is validate.__code__ and event == 'call':
            fact = frame.f_locals['value']
            values = dict(fact.view)
            if values['decision_sequence'] == 2:
                values['predecessor_fact_identity'] = 'billing-fact:sha256-' + '0' * 64
                values['fact_identity'] = f._fact_identity(values)
                fact.view = tuple((key, values[key]) for key in f.FACT_KEYS)
                touched.append(True)
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        page(client)
    finally:
        sys.settrace(prior)
    assert touched


def test_duplicate_failure_does_not_extend_deadline(app, repo):
    initial = f._append(repo)
    first = f._append_recovery(repo, initial)
    repeated = f._append_recovery(repo, initial)
    assert first.content_identity == repeated.content_identity
    now = [f.CLOCK_RECOVERY]
    client, uid = f._authenticated_client(app)
    local.install_local_billing_recovery_view(app, **p.bindings(repo, uid, clock=lambda: now[0]))
    assert '2026-11-08T00:00:00Z' in page(client, True).text
    now[0] = END
    page(client)


def test_unsupported_ambiguous_recovery_is_not_reinterpreted(app, repo):
    history(repo)
    client, uid = f._authenticated_client(app)
    args = p.bindings(repo, uid, clock=lambda: f.CLOCK_RECOVERY)
    resolver = args['live_fact_resolver']
    def ambiguous(*values):
        fact = resolver(*values)
        view = dict(fact.view)
        if view['decision_sequence'] == 2:
            view['derivation_kind'] = 'withdrawal_ambiguous'
            view['withdrawal_attribution'] = 'unknown'
            view['fact_identity'] = f._fact_identity(view)
            fact.view = tuple((key, view[key]) for key in f.FACT_KEYS)
        return fact
    args['live_fact_resolver'] = ambiguous
    local.install_local_billing_recovery_view(app, **args)
    page(client)


def test_conflicting_context_does_not_create_status(app, repo):
    history(repo)
    app.context_processor(lambda: {'local_billing_recovery_copy': {'heading': '<script>hostile</script>'}})
    client, _ = install(app, repo)
    response = page(client)
    assert 'hostile' not in response.text


def test_panel_template_autoescapes_all_supplied_fields(app):
    # Supplemental template test, not an alternative request admission path.
    hostile = '<script>synthetic</script>" onerror="synthetic'
    copy = {key: hostile for key in ('heading', 'summary', 'access_message', 'deadline_label',
            'deadline_exclusive_utc', 'deadline_display', 'deadline_consequence', 'verified_recovery_consequence')}
    with app.test_request_context('/v2/plans'):
        rendered = render_template('v2/plans.html', local_billing_recovery_copy=copy)
    assert '<script>synthetic</script>' not in rendered
    assert '&lt;script&gt;synthetic&lt;/script&gt;' in rendered
    assert 'datetime="&lt;script&gt;' in rendered


def test_coherent_alternate_copy_deadline_cannot_replace_admitted_deadline(app, repo, monkeypatch):
    history(repo)
    original = local.build_payment_recovery_presentation
    def substitute(**kwargs):
        facts = dict(kwargs['facts'])
        facts['recovery_started_at_utc'] = '2026-11-02T00:00:00Z'
        facts['recovery_deadline_exclusive_utc'] = '2026-11-09T00:00:00Z'
        return original(facts=facts, expected_owner_reference=kwargs['expected_owner_reference'])
    monkeypatch.setattr(local, 'build_payment_recovery_presentation', substitute)
    client, _ = install(app, repo)
    page(client)
