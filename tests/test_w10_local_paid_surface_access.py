"""Actual registered requests with disposable data and original S3C admission.

Reuse synthetic issuer/journal fixtures, never an admitted-success replacement.
"""
import re
import sys
from dataclasses import replace
from datetime import datetime, timezone
from functools import wraps

import pytest
import reserved.database as db
from reserved import create_app
from reserved.billing import local_paid_surface_access as local
from reserved.billing import paid_access_guard as paid
from reserved.billing import runtime_entitlement_admission as admission
from tests import test_w10_local_dashboard_access as f

CASES = (
    ('v2.index', '/v2/', 'GET'),
    ('v2.connections', '/v2/connections', 'GET'),
    ('v2.dashboard_view', '/v2/dashboard', 'GET'),
    ('v2.paye_manual_baseline', '/v2/paye/manual-baseline', 'POST'),
    ('v2.paye_manual_journey', '/v2/paye/manual', 'GET'),
    ('v2.delete_paye_manual_journey_entry', '/v2/paye/manual/entries/synthetic/delete', 'POST'),
    ('v2.paye_durable_current_position', '/v2/paye/current-position', 'GET'),
    ('v2.paye_durable_current_forecast', '/v2/paye/current-forecast', 'GET'),
    ('v2.hicbc_durable_current_annual_position', '/v2/hicbc/current-annual-position', 'GET'),
    ('v2.mtd_manual_scope', '/v2/mtd/scope-indication', 'POST'),
    ('v2.invoices', '/v2/invoices', 'GET'),
    ('v2.invoices_seed', '/v2/invoices/seed', 'POST'),
    ('v2.optimise_view', '/v2/optimise', 'GET'),
    ('v2.optimise_calculate', '/v2/optimise/calculate', 'POST'),
    ('v2.optimise_save_scenario', '/v2/optimise/save-scenario', 'POST'),
    ('v2.optimise_delete_scenario', '/v2/optimise/saved/1', 'DELETE'),
    ('v2.review_queue', '/v2/review', 'GET'),
    ('v2.settings_page', '/v2/settings', 'POST'),
    ('v2.transactions', '/v2/transactions', 'GET'),
    ('v2.transactions_seed', '/v2/transactions/seed', 'POST'),
    ('v2.yapily_callback', '/v2/yapily/callback', 'GET'),
    ('v2.yapily_connect', '/v2/yapily/connect', 'POST'),
    ('v2.yapily_disconnect', '/v2/yapily/disconnect', 'POST'),
    ('v2.yapily_refresh', '/v2/yapily/refresh', 'POST'),
    ('hicbc.index', '/v2/hicbc/', 'GET'),
    ('hicbc.delete_estimate', '/v2/hicbc/delete', 'POST'),
    ('hicbc.save_estimate', '/v2/hicbc/estimate', 'POST'),
    ('hicbc.link_page', '/v2/hicbc/link', 'POST'),
    ('hicbc.link_accept', '/v2/hicbc/link/accept', 'POST'),
    ('hicbc.link_invite', '/v2/hicbc/link/invite', 'POST'),
    ('hicbc.link_revoke', '/v2/hicbc/link/revoke', 'POST'),
    ('hicbc.result_json', '/v2/hicbc/result', 'GET'),
    ('hicbc.annual_preview', '/v2/hicbc/annual-preview', 'POST'),
)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, '_DB_FILE', tmp_path / 'application.db')
    monkeypatch.setattr(db, '_INSTANCE', tmp_path)
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('CLERK_PUBLISHABLE_KEY', raising=False)
    monkeypatch.setenv('HICBC_ENABLED', 'true')
    for key in ('HICBC_ANNUAL_PREVIEW_ENABLED', 'PAYE_MANUAL_BASELINE_ENABLED', 'MTD_MANUAL_SCOPE_ENABLED'):
        monkeypatch.delenv(key, raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def repo(tmp_path):
    value = f.LocalBillingRepository.create(tmp_path / 'billing.db')
    yield value
    value.close()


def bindings(repo, uid, clock=lambda: f.CLOCK, **overrides):
    validate, project, issue = f._authority()
    result = dict(membership_resolver=f._membership_resolver(uid),
                  snapshot_reader=f._snapshot_reader(repo),
                  live_fact_resolver=f._live_fact_resolver(repo, f.SCOPE, issue),
                  validate_admitted_billing_fact=validate,
                  project_admitted_billing_fact=project, clock=clock)
    result.update(overrides)
    return result


def install(app, repo, **overrides):
    client, uid = f._authenticated_client(app)
    local.install_local_paid_surface_access(app, **bindings(repo, uid, **overrides))
    return client, uid


def denied(response):
    assert response.status_code == 403 and response.data == b''
    assert 'no-store' in response.headers['Cache-Control']
    assert not any(value in str(response.headers) for value in f.SCOPE)


@pytest.mark.parametrize('endpoint,path,method', CASES)
@pytest.mark.parametrize('state', ['missing', 'expired', 'withdrawn'])
def test_every_paid_handler_denied_before_body(app, repo, endpoint, path, method, state):
    assert tuple(c[0] for c in CASES) == paid.PAID_ENDPOINTS and len(CASES) == 33
    now = f.CLOCK
    if state != 'missing':
        initial = f._append(repo)
        if state == 'withdrawn':
            f._append_withdrawal(repo, initial)
            now = f.CLOCK_WITHDRAWAL
        else:
            now = f.CLOCK_RECOVERY
    code = app.view_functions[endpoint].__wrapped__.__code__
    calls, evaluated_endpoints = [], []
    def trace(frame, event, arg):
        if frame.f_code is paid.evaluate_paid_access.__code__ and event == 'call':
            evaluated_endpoints.append(frame.f_locals['endpoint'])
        if frame.f_code is code and event == 'call':
            calls.append(True)
            raise AssertionError('paid handler body must not execute')
        return trace
    client, _ = install(app, repo, clock=lambda: now)
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        response = client.open(path, method=method)
    finally:
        sys.settrace(prior)
    denied(response)
    assert calls == []
    if state == 'withdrawn':
        assert evaluated_endpoints == [endpoint]


def test_actual_settings_csrf_save_and_json_delete(app, repo):
    from reserved.tax_year_context import configured_tax_year
    f._append(repo)
    app.config['WTF_CSRF_ENABLED'] = True
    exemptions = set(app.extensions['csrf']._exempt_views)
    client, uid = install(app, repo)
    result = client.get('/v2/settings')
    assert result.status_code == 200
    token = re.search(r'name="csrf_token" value="([^"]+)"', result.text).group(1)
    original = db.get_profile_by_user(uid)
    data = dict(first_name='Synthetic Updated', entity_type='sole_trader', student_loan='none',
                accounting_method='cash_basis', vat_status='not_vat_registered')
    for invalid in (None, 'forged'):
        payload = dict(data)
        if invalid is not None:
            payload['csrf_token'] = invalid
        assert client.post('/v2/settings', data=payload).status_code == 400
        assert db.get_profile_by_user(uid) == original
    result = client.post('/v2/settings', data={**data, 'csrf_token': token})
    assert result.status_code == 302 and result.location.endswith('/v2/dashboard')
    assert db.get_profile_by_user(uid)['display_name'] == 'Synthetic Updated'
    assert client.get('/v2/dashboard').status_code == 200
    calculated = client.post('/v2/optimise/calculate', json=dict(projected_income='110000',
        current_pension='0', additional_pension='1000', opportunity_id='PA_TAPER'))
    assert calculated.status_code == 200 and calculated.json['ok'] is True
    assert calculated.json['before']['ani'] == '110,000.00'
    assert calculated.json['after']['ani'] != calculated.json['before']['ani']
    saved = client.post('/v2/optimise/save-scenario', json=dict(tax_year=configured_tax_year(),
        opportunity_id='PA_TAPER', inputs={'synthetic': 1}, outputs={'synthetic': 2}, label='Synthetic'))
    assert saved.status_code == 200 and saved.json['ok'] is True
    path = '/v2/optimise/saved/' + str(saved.json['id'])
    assert client.delete(path).json == {'ok': True}
    assert client.delete(path).json == {'ok': False}
    assert app.extensions['csrf']._exempt_views == exemptions


def test_existing_feature_controls_and_json(app, repo):
    f._append(repo)
    client, _ = install(app, repo)
    assert client.get('/v2/hicbc/result').status_code == 200
    assert client.post('/v2/hicbc/annual-preview', json={}).status_code == 404
    assert client.get('/v2/paye/manual-baseline').status_code == 404
    assert client.get('/v2/mtd/scope-indication').status_code == 404


def test_conditional_absence_never_registers_hicbc(app, repo, monkeypatch):
    monkeypatch.setenv('HICBC_ENABLED', 'false')
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    before = dict(application.view_functions)
    client, _ = install(application, repo)
    assert len([n for n in before if n in paid.PAID_ENDPOINTS]) == 24
    assert application.view_functions.keys() == before.keys()
    assert not any(n.startswith('hicbc.') for n in before)
    assert client.get('/v2/hicbc/').status_code == 404


def test_exact_wrappers_rules_exclusions_and_methods(app, repo):
    before = dict(app.view_functions)
    rules = str(app.url_map)
    client, _ = install(app, repo)
    for name, original in before.items():
        current = app.view_functions[name]
        if name in paid.PAID_ENDPOINTS:
            assert current.__wrapped__.__wrapped__ is original
            assert (current.__name__, current.__module__) == (original.__name__, original.__module__)
        else:
            assert current is original
    assert str(app.url_map) == rules
    assert client.post('/v2/dashboard').status_code == 405
    assert client.options('/v2/settings').status_code == 200
    denied(client.head('/v2/settings'))
    assert app.test_client().get('/v2/settings').status_code == 302


@pytest.mark.parametrize('fault', ['missing', 'partial_hicbc', 'replaced', 'method', 'alias', 'body_alias', 'wrapped_alias', 'path', 'validator'])
def test_install_failure_is_atomic(app, repo, fault):
    _, uid = f._authenticated_client(app)
    args = bindings(repo, uid)
    if fault == 'missing':
        del app.view_functions['v2.settings_page']
    elif fault == 'partial_hicbc':
        del app.view_functions['hicbc.result_json']
    elif fault == 'replaced':
        original = app.view_functions['v2.settings_page']
        @wraps(original)
        def substitute():
            return original()
        app.view_functions['v2.settings_page'] = substitute
    elif fault == 'method':
        next(r for r in app.url_map.iter_rules() if r.endpoint == 'v2.settings_page').methods.add('DELETE')
    elif fault == 'alias':
        app.add_url_rule('/alias', 'alias', app.view_functions['v2.settings_page'])
    elif fault == 'body_alias':
        app.add_url_rule('/alias', 'alias', app.view_functions['v2.settings_page'].__wrapped__)
    elif fault == 'wrapped_alias':
        original = app.view_functions['v2.settings_page']
        @wraps(original)
        def alias():
            return original()
        app.add_url_rule('/alias', 'alias', alias)
    elif fault == 'path':
        app.add_url_rule('/v2/settings', 'alias', lambda: 'unsafe')
    else:
        args['validate_admitted_billing_fact'] = None
    before, extensions = dict(app.view_functions), dict(app.extensions)
    with pytest.raises(local.LocalPaidSurfaceAccessError):
        local.install_local_paid_surface_access(app, **args)
    assert app.view_functions == before and app.extensions == extensions


@pytest.mark.parametrize('mode', ['duplicate', 'late', 'dashboard'])
def test_install_conflicts(app, repo, mode):
    client, uid = f._authenticated_client(app)
    args = bindings(repo, uid)
    if mode == 'duplicate':
        local.install_local_paid_surface_access(app, **args)
    elif mode == 'late':
        client.get('/v2/login')
    else:
        f.install_local_dashboard_access(app, **args)
    before = dict(app.view_functions)
    with pytest.raises(local.LocalPaidSurfaceAccessError):
        local.install_local_paid_surface_access(app, **args)
    assert before == app.view_functions


@pytest.mark.parametrize('key,value', [('FLASK_ENV', 'production'), ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic')])
def test_production_install_and_request_denial(app, repo, monkeypatch, key, value):
    client, uid = f._authenticated_client(app)
    args = bindings(repo, uid)
    with monkeypatch.context() as scoped:
        scoped.setenv(key, value)
        before = dict(app.view_functions)
        with pytest.raises(local.LocalPaidSurfaceAccessError):
            local.install_local_paid_surface_access(app, **args)
        assert app.view_functions == before
    f._append(repo)
    local.install_local_paid_surface_access(app, **args)
    assert client.get('/v2/settings').status_code == 200
    monkeypatch.setenv(key, value)
    denied(client.get('/v2/settings'))


def test_recovery_exact_boundary(app, repo):
    initial = f._append(repo)
    f._append_recovery(repo, initial)
    now = [f.CLOCK_RECOVERY]
    client, _ = install(app, repo, clock=lambda: now[0])
    assert client.get('/v2/settings').status_code == 200
    now[0] = datetime(2026, 11, 8, tzinfo=timezone.utc)
    denied(client.get('/v2/settings'))


def test_withdrawal_and_verified_restoration(app, repo):
    initial = f._append(repo)
    now = [f.CLOCK]
    client, _ = install(app, repo, clock=lambda: now[0])
    assert client.get('/v2/settings').status_code == 200
    withdrawn = f._append_withdrawal(repo, initial)
    now[0] = f.CLOCK_WITHDRAWAL
    denied(client.get('/v2/settings'))
    f._append_restoration(repo, withdrawn)
    now[0] = f.CLOCK_RESTORATION
    assert client.get('/v2/settings').status_code == 200


def test_ambiguous_preservation_does_not_extend(app, repo):
    initial = f._append(repo)
    f._append_ambiguous(repo, initial)
    now = [f.CLOCK_WITHDRAWAL]
    client, _ = install(app, repo, clock=lambda: now[0])
    assert client.get('/v2/settings').status_code == 200
    now[0] = f.CLOCK_RECOVERY
    denied(client.get('/v2/settings'))


@pytest.mark.parametrize('fault', ['membership', 'cross_scope', 'deleted', 'lookup_error', 'malformed', 'changed'])
def test_request_dependencies_fail_closed(app, repo, monkeypatch, fault):
    f._append(repo)
    client, uid = f._authenticated_client(app)
    args = bindings(repo, uid)
    if fault == 'membership':
        args['membership_resolver'] = lambda _: None
    elif fault == 'cross_scope':
        args['membership_resolver'] = lambda _: ('other', f.ACCOUNT, f.SUBSCRIPTION)
    elif fault == 'deleted':
        monkeypatch.setattr(db, 'get_user', lambda _: None)
    elif fault == 'lookup_error':
        def fail(_):
            raise RuntimeError('synthetic')
        monkeypatch.setattr(db, 'get_user', fail)
    else:
        read = args['snapshot_reader']
        calls = []
        def altered(*scope):
            snapshot = read(*scope)
            calls.append(True)
            if fault == 'malformed':
                return replace(snapshot, entries=(None,))
            return replace(snapshot, billing_account_id='other') if len(calls) > 1 else snapshot
        args['snapshot_reader'] = altered
    local.install_local_paid_surface_access(app, **args)
    denied(client.get('/v2/settings'))


def test_admission_time_mutation_rejected_without_replacing_validator(app, repo):
    initial = f._append(repo)
    f._append_withdrawal(repo, initial)
    records = repo.journal(owner_id=f.OWNER, billing_account_id=f.ACCOUNT, subscription_id=f.SUBSCRIPTION)
    facts = f._facts(records)
    replacement = f._ambiguous_preservation_fact(records[1], dict(facts[0])['fact_identity'])
    client, uid = f._authenticated_client(app)
    args = bindings(repo, uid, clock=lambda: f.CLOCK_WITHDRAWAL)
    validate = args['validate_admitted_billing_fact']
    local.install_local_paid_surface_access(app, **args)
    touched, admitted = [], []
    def trace(frame, event, value):
        if frame.f_code is validate.__code__ and event == 'call':
            fact = frame.f_locals['value']
            if dict(fact.view)['decision_sequence'] == 2:
                assert fact.view == facts[1]
                fact.view = replacement
                touched.append(True)
        if frame.f_code is admission.admit_runtime_entitlement.__code__ and event == 'return' and value is not None:
            admitted.append(dict(admission.project_runtime_entitlement(value)))
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = client.get('/v2/settings')
    finally:
        sys.settrace(prior)
    denied(result)
    assert touched == [True] and len(admitted) == 2
    assert admitted[-1]['ordinary_access'] is True


def test_paid_access_does_not_grant_other_users_scenario(app, repo):
    from reserved.tax_year_context import configured_tax_year
    f._append(repo)
    client, uid = install(app, repo)
    other = db.get_or_create_user('synthetic-other-user')
    assert other != uid
    row = db.save_optimise_scenario(other, 'PA_TAPER', {}, {}, label='Synthetic', tax_year=configured_tax_year())
    response = client.delete('/v2/optimise/saved/' + str(row))
    assert response.status_code == 200 and response.json == {'ok': False}
    assert db.delete_optimise_scenario(row, other) is True


@pytest.mark.parametrize('field', ['billing_account_id', 'subscription_id'])
def test_live_fact_cross_account_or_subscription_rejected(app, repo, field):
    record = f._append(repo)
    validate, project, issue = f._authority()
    values = dict(f._facts([record])[0])
    values[field] = 'synthetic-other-scope'
    values['fact_identity'] = f._fact_identity(values)
    fact = issue(tuple((key, values[key]) for key in f.FACT_KEYS))
    client, _ = install(app, repo, validate_admitted_billing_fact=validate,
                        project_admitted_billing_fact=project,
                        live_fact_resolver=lambda *args: fact)
    denied(client.get('/v2/settings'))
