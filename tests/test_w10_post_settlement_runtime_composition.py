"""Application-factory composition for the default-off post-settlement panel."""

from datetime import datetime

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.billing import local_billing_post_settlement_view as view
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


_KEY = 'reserved.billing.local_billing_post_settlement_view'
_MARKER = 'id="w10-local-full-withdrawal-heading"'


def _configure(tmp_path, monkeypatch, *, production=False):
    monkeypatch.setattr(db, '_DB_FILE', tmp_path / 'application.db')
    monkeypatch.setattr(db, '_INSTANCE', tmp_path)
    monkeypatch.setenv('FLASK_ENV', 'production' if production else 'development')
    monkeypatch.delenv('CLERK_PUBLISHABLE_KEY', raising=False)
    if production:
        monkeypatch.setenv('SESSION_SECRET', 'synthetic-production-secret-for-tests')


def _login(app, owner):
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return client


def _scope(harness):
    return tuple(harness.kwargs[name]
                 for name in ('owner', 'billing_account', 'subscription'))


def _runtime(owner, harness, fact, calls=None):
    scope = _scope(harness)
    calls = [] if calls is None else calls

    def membership(value):
        calls.append(('membership', value))
        return scope if value == owner else None

    def withdrawal(*values):
        calls.append(('withdrawal', values))
        return fact if values == scope else None

    def restoration(*values):
        calls.append(('restoration', values))
        return None

    return view.LocalBillingPostSettlementRuntime(
        membership_resolver=membership,
        live_full_withdrawal_fact_resolver=withdrawal,
        live_later_period_restoration_fact_resolver=restoration,
        clock=lambda: harness.withdrawal_time,
    )


def test_absent_invalid_or_incomplete_runtime_keeps_panel_and_dependencies_absent(
        tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    calls = []
    app = create_app()
    assert _KEY not in app.extensions
    assert app.test_client().get('/v2/plans').status_code == 302

    invalid = create_app(post_settlement_runtime=object())
    assert _KEY not in invalid.extensions
    assert invalid.test_client().get('/v2/plans').status_code == 302
    assert calls == []

    incomplete = object.__new__(view.LocalBillingPostSettlementRuntime)
    hostile = create_app(post_settlement_runtime=incomplete)
    assert _KEY not in hostile.extensions
    assert hostile.test_client().get('/v2/plans').status_code == 302
    assert calls == []


@pytest.mark.parametrize('values', [
    (None, lambda *_: None, lambda *_: None, None),
    (lambda *_: None, None, lambda *_: None, None),
    (lambda *_: None, lambda *_: None, None, None),
    (lambda *_: None, lambda *_: None, lambda *_: None, object()),
])
def test_runtime_constructor_requires_every_callable_dependency(values):
    with pytest.raises(view.LocalBillingPostSettlementViewError):
        view.LocalBillingPostSettlementRuntime(*values)


def test_exact_runtime_is_deferred_then_installs_only_the_existing_panel(
        tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    db.init_db()
    owner = db.get_or_create_user('post-settlement-runtime-owner')
    harness = WithdrawalHarness(tmp_path / 'withdrawal.db', owner)
    try:
        assert harness.ingest().disposition == 'admitted'
        harness.prepare_withdrawal(); fact = harness.withdraw().fact
        calls = []
        app = create_app(post_settlement_runtime=_runtime(owner, harness, fact, calls))
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        assert app.extensions[_KEY] is not None
        assert calls == []
        assert 'reserved.billing.stripe_runtime.paid_surface.disabled' not in app.extensions
        assert app.test_client().post('/v2/plans').status_code == 405

        response = _login(app, owner).get('/v2/plans')
        assert response.status_code == 200 and _MARKER in response.text
        assert [name for name, _ in calls] == [
            'membership', 'withdrawal', 'restoration',
            'membership', 'withdrawal', 'restoration',
        ]
        assert all(value not in response.text for value in _scope(harness))
    finally:
        harness.repo.close()


def test_production_exact_runtime_remains_absent_and_never_calls_dependencies(
        tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch, production=True)
    calls = []
    runtime = view.LocalBillingPostSettlementRuntime(
        membership_resolver=lambda *values: calls.append(values),
        live_full_withdrawal_fact_resolver=lambda *values: calls.append(values),
        live_later_period_restoration_fact_resolver=lambda *values: calls.append(values),
    )
    app = create_app(post_settlement_runtime=runtime)
    assert _KEY not in app.extensions
    assert 'reserved.billing.stripe_runtime.paid_surface.disabled' in app.extensions
    assert app.test_client().get('/v2/plans').status_code == 302
    assert calls == []


def test_factory_runtime_does_not_replace_route_or_csrf(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app(post_settlement_runtime=object())
    rule = next(rule for rule in app.url_map.iter_rules()
                if rule.endpoint == 'v2.billing_plans')
    assert rule.rule == '/v2/plans' and rule.methods == {'GET', 'HEAD', 'OPTIONS'}
    assert 'csrf' in app.extensions
    assert app.view_functions['v2.billing_plans'].__name__ == 'billing_plans'
