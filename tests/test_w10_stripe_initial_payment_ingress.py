"""Independent synthetic wire fixtures -> actual local paid application requests."""
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import linecache
import re
import sys
import uuid

import pytest
from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
from reserved.billing import local_paid_surface_access as surfaces
from tests import test_w10_local_paid_surface_access as old
from tests import test_w10_local_dashboard_access as dashboard

app = old.app
SIGNING_KEY = b'synthetic-webhook-only-key-000000000000'
RECEIPT_KEY = b'synthetic-receipt-only-key-111111111111'
START = datetime(2026, 10, 15, 13, 25, 17, tzinfo=timezone.utc)
NOW = START + timedelta(seconds=100)
ENDS = {'monthly': datetime(2026, 11, 15, 13, 25, 17, tzinfo=timezone.utc),
        'six_month': datetime(2027, 4, 15, 13, 25, 17, tzinfo=timezone.utc),
        'yearly': datetime(2027, 10, 15, 13, 25, 17, tzinfo=timezone.utc)}


def encoded(value):
    return json.dumps(value, separators=(',', ':')).encode()


def signature(raw, now=NOW, key=SIGNING_KEY):
    # Construct wire HMAC independently of the product verifier.
    timestamp = str(int(now.timestamp()))
    digest = hmac.new(key, timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    return 't=' + timestamp + ',v1=' + digest


def one(value):
    return {'object': 'list', 'data': [value], 'has_more': False}


def objects(plan='monthly'):
    amount, interval, count = {'monthly': (2900, 'month', 1), 'six_month': (15600, 'month', 6),
                               'yearly': (28800, 'year', 1)}[plan]
    end = ENDS[plan]
    invoice = dict(id='in_Synthetic', object='invoice', livemode=False, customer='cus_Synthetic',
        status='paid', billing_reason='subscription_create', currency='gbp', collection_method='charge_automatically',
        parent={'type': 'subscription_details', 'subscription_details': {'subscription': 'sub_Synthetic'}},
        amount_paid=amount, amount_due=amount, total=amount, amount_remaining=0, amount_overpaid=0,
        starting_balance=0, pre_payment_credit_notes_amount=0, post_payment_credit_notes_amount=0,
        discounts=[], total_discount_amounts=[])
    line = dict(id='il_Synthetic', object='line_item', livemode=False, currency='gbp', quantity=1, amount=amount,
        invoice='in_Synthetic', discounts=[], discount_amounts=[],
        parent={'type': 'subscription_item_details', 'subscription_item_details':
                {'subscription_item': 'si_Synthetic', 'subscription': 'sub_Synthetic', 'proration': False}},
        pricing={'type': 'price_details', 'price_details': {'price': 'price_Synthetic'}},
        period={'start': int(START.timestamp()), 'end': int(end.timestamp())})
    subscription = dict(id='sub_Synthetic', object='subscription', livemode=False, customer='cus_Synthetic',
        status='active', latest_invoice='in_Synthetic', discounts=[], collection_method='charge_automatically',
        items=one(dict(id='si_Synthetic', object='subscription_item', subscription='sub_Synthetic', quantity=1,
             price={'id': 'price_Synthetic'}, current_period_start=int(START.timestamp()), current_period_end=int(end.timestamp()))))
    price = dict(id='price_Synthetic', object='price', livemode=False, currency='gbp', unit_amount=amount,
        type='recurring', billing_scheme='per_unit', recurring={'interval': interval, 'interval_count': count, 'usage_type': 'licensed'})
    payment = dict(id='inpay_Synthetic', object='invoice_payment', livemode=False, invoice='in_Synthetic',
        status='paid', currency='gbp', amount_paid=amount, amount_requested=amount,
        payment={'type': 'payment_intent', 'payment_intent': 'pi_Synthetic'})
    intent = dict(id='pi_Synthetic', object='payment_intent', livemode=False, status='succeeded',
        customer='cus_Synthetic', currency='gbp', amount_received=amount, amount=amount, latest_charge='ch_Synthetic')
    charge = dict(id='ch_Synthetic', object='charge', livemode=False, payment_intent='pi_Synthetic',
        customer='cus_Synthetic', currency='gbp', paid=True, captured=True, status='succeeded',
        payment_method_details={'type': 'card'}, amount_captured=amount, amount=amount,
        amount_refunded=0, refunded=False, disputed=False)
    for obj in (invoice, payment, intent, charge):
        obj['created'] = int(START.timestamp())
    for obj in (invoice, payment):
        obj['status_transitions'] = {'paid_at': int(START.timestamp())}
    return {'/v1/invoices/in_Synthetic': invoice, '/v1/invoices/in_Synthetic/lines': one(line),
        '/v1/subscriptions/sub_Synthetic': subscription, '/v1/prices/price_Synthetic': price,
        '/v1/invoice_payments': one(payment), '/v1/payment_intents/pi_Synthetic': intent, '/v1/charges/ch_Synthetic': charge}


class Harness:
    def __init__(self, path, uid=1, plan='monthly'):
        self.repo = ProvenanceRepository(path, create=True)
        self.data = objects(plan)
        self.requests = []
        self.hook = None
        self.response_hook = None
        def retrieve(request):
            self.requests.append(request)
            assert request.origin == 'https://api.stripe.com' and request.api_version == '2025-03-31.basil'
            assert request.livemode is False and request.account == self.account
            if self.hook:
                self.hook(request)
            response = source.SourceResponse(request, encoded(self.data[request.path]))
            return self.response_hook(response) if self.response_hook else response
        self.account = 'synthetic-account-' + uuid.uuid4().hex
        self.kwargs = dict(repository=self.repo, user_id=uid, owner='synthetic-owner', billing_account='synthetic-billing',
            subscription='sub_Synthetic', customer='cus_Synthetic', item='si_Synthetic', price='price_Synthetic', plan=plan,
            endpoint='synthetic-endpoint', account=self.account, signing_keys=(SIGNING_KEY,), receipt_key=RECEIPT_KEY,
            signing_key_ids=('synthetic-webhook-key-id',), receipt_key_id='synthetic-receipt-key-id',
            retrieve=retrieve, pristine_initial_eligible=True)
        self.authority = source.SyntheticInitialAuthority(**self.kwargs)
        self.event = dict(id='evt_Synthetic', object='event', type='invoice.paid', livemode=False,
            api_version='2025-03-31.basil', created=int(START.timestamp()),
            data={'object': copy.deepcopy(self.data['/v1/invoices/in_Synthetic'])})

    def ingest(self, *, now=NOW, raw=None, header=None, clock=None):
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_initial_payment(self.authority, self.repo, raw,
            signature(raw, now) if header is None else header, clock=clock or (lambda: now))


@pytest.fixture
def harness(tmp_path):
    value = Harness(tmp_path / 'source.db')
    yield value
    value.repo.close()


@pytest.mark.parametrize('plan', ['monthly', 'six_month', 'yearly'])
def test_real_signed_payment_to_settings_csrf_and_exact_end(app, tmp_path, plan):
    import reserved.database as db
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path / 'source.db', uid, plan)
    try:
        result = h.ingest()
        assert result.disposition == 'admitted' and result.committed is True and result.fact is not None
        assert len(h.requests) == 14
        assert h.requests[1].query == (('limit', '100'),)
        assert h.requests[4].query == (('invoice', 'in_Synthetic'), ('limit', '100'))
        now = [NOW]
        app.config['WTF_CSRF_ENABLED'] = True
        surfaces.install_local_exact_utc_paid_surface_access(app, authority=h.authority, repository=h.repo, clock=lambda: now[0])
        response = client.get('/v2/settings')
        assert response.status_code == 200
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        values = dict(first_name='Synthetic Paid', entity_type='sole_trader', student_loan='none',
                      accounting_method='cash_basis', vat_status='not_vat_registered')
        assert client.post('/v2/settings', data=values).status_code == 400
        assert client.post('/v2/settings', data={**values, 'csrf_token': 'forged'}).status_code == 400
        assert client.post('/v2/settings', data={**values, 'csrf_token': token}).status_code == 302
        assert db.get_profile_by_user(uid)['display_name'] == 'Synthetic Paid'
        now[0] = ENDS[plan] - timedelta(microseconds=1)
        assert client.get('/v2/settings').status_code == 200
        now[0] = ENDS[plan]
        old.denied(client.get('/v2/settings'))
        assert client.get('/v2/plans').status_code == 200
    finally:
        h.repo.close()


MUTATIONS = [
    ('/v1/invoices/in_Synthetic', ('customer',), 'cus_Other'),
    ('/v1/invoices/in_Synthetic', ('livemode',), True),
    ('/v1/invoices/in_Synthetic', ('status',), 'open'),
    ('/v1/invoices/in_Synthetic', ('billing_reason',), 'subscription_cycle'),
    ('/v1/invoices/in_Synthetic', ('amount_paid',), True),
    ('/v1/invoices/in_Synthetic', ('amount_due',), 0),
    ('/v1/invoices/in_Synthetic', ('amount_remaining',), 10),
    ('/v1/invoices/in_Synthetic', ('starting_balance',), 1),
    ('/v1/invoices/in_Synthetic', ('post_payment_credit_notes_amount',), 1),
    ('/v1/invoices/in_Synthetic', ('discounts',), ['di_Synthetic']),
    ('/v1/invoices/in_Synthetic/lines', ('has_more',), True),
    ('/v1/invoices/in_Synthetic/lines', ('data', 0, 'quantity'), True),
    ('/v1/invoices/in_Synthetic/lines', ('data', 0, 'parent', 'subscription_item_details', 'proration'), True),
    ('/v1/invoices/in_Synthetic/lines', ('data', 0, 'pricing', 'price_details', 'price'), 'price_Other'),
    ('/v1/subscriptions/sub_Synthetic', ('latest_invoice',), 'in_Other'),
    ('/v1/subscriptions/sub_Synthetic', ('items', 'data', 0, 'current_period_end'), int(ENDS['monthly'].timestamp())+1),
    ('/v1/subscriptions/sub_Synthetic', ('items', 'has_more'), True),
    ('/v1/prices/price_Synthetic', ('recurring', 'interval_count'), 6),
    ('/v1/prices/price_Synthetic', ('currency',), 'usd'),
    ('/v1/invoice_payments', ('has_more',), True),
    ('/v1/invoice_payments', ('data', 0, 'invoice'), 'in_Other'),
    ('/v1/invoice_payments', ('data', 0, 'payment', 'type'), 'payment_record'),
    ('/v1/invoice_payments', ('data', 0, 'amount_paid'), 100),
    ('/v1/payment_intents/pi_Synthetic', ('status',), 'requires_capture'),
    ('/v1/payment_intents/pi_Synthetic', ('latest_charge',), 'https://evil.invalid/path'),
    ('/v1/charges/ch_Synthetic', ('captured',), False),
    ('/v1/charges/ch_Synthetic', ('amount_captured',), 100),
    ('/v1/charges/ch_Synthetic', ('payment_intent',), 'pi_Other'),
    ('/v1/charges/ch_Synthetic', ('disputed',), True),
    ('/v1/charges/ch_Synthetic', ('amount_refunded',), 1),
    ('/v1/charges/ch_Synthetic', ('payment_method_details', 'type'), 'bacs_debit'),
    ('/v1/invoice_payments', ('data', 0, 'status_transitions', 'paid_at'), int(NOW.timestamp())+1),
    ('/v1/charges/ch_Synthetic', ('created',), int(NOW.timestamp())+1),
]


@pytest.mark.parametrize('path,keys,value', MUTATIONS)
def test_source_negatives(harness, path, keys, value):
    target = harness.data[path]
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    result = harness.ingest()
    assert result.disposition == 'refused' and result.fact is None
    assert harness.repo.empty() and harness.authority.snapshot().accepted is None


@pytest.mark.parametrize('key,value', [('api_version', '2025-05-28.basil'), ('livemode', True),
    ('account', 'acct_Connect'), ('type', 'invoice.payment_failed'), ('created', True),
    ('created', int(NOW.timestamp())+1)])
def test_event_negatives_before_retrieval(harness, key, value):
    harness.event[key] = value
    assert harness.ingest().disposition == 'refused'
    assert harness.requests == []


@pytest.mark.parametrize('raw', [b'{"id":1,"id":2}', b'{"x":NaN}', b'[]', b'{', b'{"x":1.2}'])
def test_hostile_json(harness, raw):
    assert harness.ingest(raw=raw).disposition == 'refused'
    assert harness.requests == []


def test_signature_precedes_parser(harness, monkeypatch):
    def tripwire(raw):
        raise AssertionError('parser must not execute')
    monkeypatch.setattr(source, '_parse', tripwire)
    result = harness.ingest(raw=b'invalid', header=signature(b'invalid', key=b'wrong-synthetic-key'))
    assert result.disposition == 'refused' and harness.requests == []


@pytest.mark.parametrize('path', ['/v1/invoices/in_Synthetic/lines', '/v1/invoice_payments'])
def test_multiple_or_empty_enumeration(harness, path):
    harness.data[path]['data'] *= 2
    assert harness.ingest().disposition == 'refused'
    harness.data[path]['data'] = []
    assert harness.ingest().disposition == 'refused'


def test_changed_objects_deny_before_commit(harness):
    def hook(request):
        if len(harness.requests) == 8:
            harness.data[request.path]['description'] = 'changed while reconciling'
    harness.hook = hook
    assert harness.ingest().disposition == 'refused'
    assert harness.repo.empty()


def test_identical_replay_preserves_verification_and_head(harness):
    assert harness.ingest().disposition == 'admitted'
    before = harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY)
    assert harness.ingest(now=NOW+timedelta(seconds=100)).disposition == 'admitted'
    assert harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY) == before
    assert before[0]['verification_completed_at'] == NOW.isoformat()
    assert before[0]['source_created_at'] == START.isoformat()


@pytest.mark.parametrize('change', ['bytes', 'secondary'])
def test_conflicting_or_secondary_event_requires_reconciliation(harness, change):
    assert harness.ingest().disposition == 'admitted'
    before = harness.authority.snapshot()
    if change == 'bytes':
        harness.event['pending_webhooks'] = 2
    else:
        harness.event['id'] = 'evt_Second'
    result = harness.ingest()
    assert result.disposition == 'reconciliation_required' and result.fact is None
    assert harness.authority.snapshot() == before


@pytest.mark.parametrize('when', ['before_commit', 'after_commit', 'before_cas', 'after_cas'])
def test_publication_crashes_and_exact_retry(harness, monkeypatch, when):
    method = ProvenanceRepository.commit_initial
    prior_trace = sys.gettrace()
    if when in ('before_commit', 'after_commit'):
        def crashing(self, *args):
            if when == 'after_commit':
                method(self, *args)
            raise RuntimeError('synthetic crash')
        monkeypatch.setattr(ProvenanceRepository, 'commit_initial', crashing)
    else:
        def trace(frame, event, arg):
            if (frame.f_code.co_name == '_publish' and frame.f_code.co_filename == source.__file__
                    and event == ('call' if when == 'before_cas' else 'return')):
                raise RuntimeError('synthetic publication crash')
            return trace
        sys.settrace(trace)
    try:
        result = harness.ingest()
    finally:
        sys.settrace(prior_trace)
    assert result.fact is None
    # An arbitrary wrapper exception does not certify that COMMIT never ran.
    # The old empty-readback=False assumption was the reviewed false-rollback gap.
    assert result.committed is (None if when == 'before_commit' else True)
    assert result.disposition == ('commit_outcome_unknown' if when == 'before_commit' else 'committed_but_unadmitted')
    if when != 'after_cas':
        assert harness.authority.snapshot().accepted is None
    monkeypatch.undo()
    if when == 'before_commit':
        assert harness.ingest(now=NOW+timedelta(seconds=1)).disposition == 'refused'
        assert harness.repo.empty()
        return
    assert harness.ingest(now=NOW+timedelta(seconds=1)).disposition == 'admitted'
    receipt, _ = harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY)
    assert receipt['verification_completed_at'] == NOW.isoformat()


def test_genuine_precommit_rollback_allows_only_exact_reserved_retry(harness):
    touched = []
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository._metadata.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_initial.__code__):
            touched.append(True)
            assert harness.repo._db.in_transaction
            raise RuntimeError('synthetic precommit failure inside real transaction')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = harness.ingest()
    finally:
        sys.settrace(prior)
    assert touched == [True]
    assert result.disposition == 'refused' and result.committed is False
    assert not harness.repo._db.in_transaction and harness.repo.empty()
    assert harness.ingest(now=NOW+timedelta(seconds=1)).disposition == 'admitted'
    receipt, _ = harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY)
    assert receipt['verification_completed_at'] == NOW.isoformat()


def test_denied_precommit_rollback_poisoned_repository_never_admits(app, tmp_path):
    import sqlite3
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path/'source.db', uid)
    db = h.repo._db
    denied = []
    inserted = []

    def authorizer(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_TRANSACTION and first == 'ROLLBACK':
            denied.append((first, database, trigger))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is ProvenanceRepository.commit_initial.__code__
                and "self._db.execute('COMMIT')" in linecache.getline(frame.f_code.co_filename, frame.f_lineno)):
            assert db.in_transaction
            assert db.execute('SELECT count(*) FROM units').fetchone()[0] == 1
            inserted.append(True)
            raise RuntimeError('synthetic interruption immediately before COMMIT')
        return trace

    db.set_authorizer(authorizer)
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = h.ingest()
    finally:
        sys.settrace(prior)
    assert inserted == [True] and len(denied) == 1
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    assert result.fact is None and h.authority.snapshot().consumed is True
    with sqlite3.connect(h.repo.path) as independent:
        assert independent.execute('SELECT count(*) FROM units').fetchone()[0] == 0

    # Neither resetting the old connection's policy nor an attempted retry can
    # resurrect private transaction visibility as committed provenance.
    with pytest.raises(sqlite3.ProgrammingError):
        db.set_authorizer(None)
    for operation in (
            lambda: h.repo.empty(),
            lambda: h.repo.read(h.authority.snapshot().instance, RECEIPT_KEY),
            lambda: h.repo.commit_initial({}, RECEIPT_KEY),
            lambda: h.repo.record_conflict(h.authority.snapshot().instance,
                event_id='evt_Other', raw_digest='0' * 64,
                object_key='in_Other:invoice.paid', key=RECEIPT_KEY)):
        with pytest.raises((source.InitialIngressError, ValueError)):
            operation()
    assert h.ingest(now=NOW+timedelta(seconds=1)).disposition == 'refused'

    surfaces.install_local_exact_utc_paid_surface_access(
        app, authority=h.authority, repository=h.repo, clock=lambda: NOW)
    old.denied(client.get('/v2/settings'))
    with sqlite3.connect(h.repo.path) as independent:
        assert independent.execute('SELECT count(*) FROM units').fetchone()[0] == 0
    h.repo.close()
    h.repo.close()


@pytest.mark.parametrize('raise_after_delete', [False, True])
def test_commit_readback_row_loss_cannot_claim_noncommit_or_reset(harness, raise_after_delete):
    import sqlite3
    observed = []
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository.read.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_initial.__code__):
            # Independent connection establishes durable visibility before loss.
            with sqlite3.connect(harness.repo.path) as other:
                assert other.execute('SELECT count(*) FROM units').fetchone()[0] == 1
                other.execute('DELETE FROM units')
            observed.append(True)
            if raise_after_delete:
                raise RuntimeError('synthetic readback interruption after durable row loss')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = harness.ingest()
    finally:
        sys.settrace(prior)
    assert observed == [True]
    assert result.disposition == 'committed_but_unadmitted' and result.committed is True
    assert result.fact is None and harness.authority.snapshot().accepted is None
    assert harness.authority.snapshot().consumed is True
    assert harness.repo.empty()
    assert harness.ingest(now=NOW+timedelta(seconds=1)).disposition == 'refused'
    assert harness.repo.empty()


def test_committed_pre_cas_unit_loss_cannot_reset_initial_eligibility(harness):
    import sqlite3
    def trace(frame, event, arg):
        if frame.f_code.co_name == '_publish' and frame.f_code.co_filename == source.__file__ and event == 'call':
            raise RuntimeError('synthetic pre-CAS interruption')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = harness.ingest()
    finally:
        sys.settrace(prior)
    assert result.committed is True and result.fact is None
    assert harness.authority.snapshot().consumed is True
    with sqlite3.connect(harness.repo.path) as conn:
        conn.execute('DELETE FROM units')
    assert harness.ingest(now=NOW+timedelta(seconds=1)).disposition == 'refused'
    assert harness.repo.empty()


def test_revocation_between_commit_and_cas_is_not_rollback(harness, monkeypatch):
    original = ProvenanceRepository.commit_initial
    def revoke(self, *args):
        result = original(self, *args)
        harness.authority.revoke()
        return result
    monkeypatch.setattr(ProvenanceRepository, 'commit_initial', revoke)
    result = harness.ingest()
    assert result.committed is True and result.disposition == 'committed_but_unadmitted'
    assert not harness.repo.empty()
    assert not source.allows_paid_request(harness.authority, harness.repo, user_id=1, now=NOW)


@pytest.mark.parametrize('stage', [1, 14])
def test_binding_revocation_during_reconciliation(harness, stage):
    harness.hook = lambda _: harness.authority.revoke() if len(harness.requests) == stage else None
    assert harness.ingest().disposition == 'refused'
    assert harness.repo.empty()


def test_all_31_actual_endpoints_deny_without_source(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path/'source.db', uid)
    try:
        originals = {name: app.view_functions[name].__wrapped__.__code__ for name, _, _ in old.CASES}
        surfaces.install_local_exact_utc_paid_surface_access(app, authority=h.authority, repository=h.repo, clock=lambda: NOW)
        touched = []
        def trace(frame, event, value):
            if event == 'call' and frame.f_code in originals.values():
                touched.append(True)
                raise AssertionError('financial handler executed')
            return trace
        prior = sys.gettrace()
        try:
            sys.settrace(trace)
            for _, path, method in old.CASES:
                old.denied(client.open(path, method=method))
        finally:
            sys.settrace(prior)
        assert touched == [] and len(originals) == 31
    finally:
        h.repo.close()


@pytest.mark.parametrize('mode', ['duplicate', 'late', 'legacy_first', 'dashboard_first', 'exact_first', 'route_changed'])
def test_exact_installer_conflicts_without_partial_change(app, tmp_path, mode):
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path/'source.db', uid)
    legacy = dashboard.LocalBillingRepository.create(tmp_path/'legacy.db')
    args = dict(authority=h.authority, repository=h.repo, clock=lambda: NOW)
    try:
        if mode in ('duplicate', 'exact_first'):
            surfaces.install_local_exact_utc_paid_surface_access(app, **args)
        elif mode == 'late':
            client.get('/v2/plans')
        elif mode == 'legacy_first':
            surfaces.install_local_paid_surface_access(app, **old.bindings(legacy, uid))
        elif mode == 'dashboard_first':
            dashboard.install_local_dashboard_access(app, **old.bindings(legacy, uid))
        else:
            app.view_functions['v2.settings_page'] = lambda: 'replacement'
        before = dict(app.view_functions), dict(app.extensions)
        with pytest.raises((surfaces.LocalPaidSurfaceAccessError, dashboard.LocalDashboardAccessError)):
            if mode == 'exact_first':
                dashboard.install_local_dashboard_access(app, **old.bindings(legacy, uid))
            else:
                surfaces.install_local_exact_utc_paid_surface_access(app, **args)
        assert before == (app.view_functions, app.extensions)
    finally:
        h.repo.close()
        legacy.close()


@pytest.mark.parametrize('key,value', [('FLASK_ENV', 'production'), ('CLERK_PUBLISHABLE_KEY', 'pk_live_synthetic')])
def test_exact_production_denial(app, tmp_path, monkeypatch, key, value):
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path/'source.db', uid)
    try:
        assert h.ingest().disposition == 'admitted'
        args = dict(authority=h.authority, repository=h.repo, clock=lambda: NOW)
        with monkeypatch.context() as scoped:
            scoped.setenv(key, value)
            with pytest.raises(surfaces.LocalPaidSurfaceAccessError):
                surfaces.install_local_exact_utc_paid_surface_access(app, **args)
        surfaces.install_local_exact_utc_paid_surface_access(app, **args)
        assert client.get('/v2/settings').status_code == 200
        monkeypatch.setenv(key, value)
        old.denied(client.get('/v2/settings'))
        assert h.ingest().disposition == 'refused'
    finally:
        h.repo.close()


def test_deleted_and_anonymous_session_denied(app, tmp_path, monkeypatch):
    import reserved.database as db
    client, uid = dashboard._authenticated_client(app)
    h = Harness(tmp_path/'source.db', uid)
    try:
        assert h.ingest().disposition == 'admitted'
        surfaces.install_local_exact_utc_paid_surface_access(app, authority=h.authority, repository=h.repo, clock=lambda: NOW)
        assert app.test_client().get('/v2/settings').status_code == 302
        monkeypatch.setattr(db, 'get_user', lambda _: None)
        old.denied(client.get('/v2/settings'))
    finally:
        h.repo.close()


def test_wrong_response_context_is_not_authenticated(harness):
    from dataclasses import replace
    harness.response_hook = lambda response: source.SourceResponse(
        replace(response.request, api_version='2025-05-28.basil'), response.body)
    assert harness.ingest().disposition == 'refused'
