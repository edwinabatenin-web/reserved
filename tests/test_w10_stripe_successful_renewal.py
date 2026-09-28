"""Signed sequence-two renewal through the unchanged real paid installer."""
import copy
from datetime import datetime, timedelta, timezone
import linecache
import re
import sys
import threading

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import local_paid_surface_access as surfaces
from tests import test_w10_local_paid_surface_access as old
from tests import test_w10_local_dashboard_access as dashboard
from tests.test_w10_stripe_initial_payment_ingress import (
    Harness, NOW, RECEIPT_KEY, encoded, signature,
)

app = old.app
SUCCESSOR_ENDS = {
    'monthly': datetime(2026, 12, 15, 13, 25, 17, tzinfo=timezone.utc),
    'six_month': datetime(2027, 10, 15, 13, 25, 17, tzinfo=timezone.utc),
    'yearly': datetime(2028, 10, 15, 13, 25, 17, tzinfo=timezone.utc),
}


def _rename(value, old, new):
    if type(value) is dict:
        return {key: _rename(child, old, new) for key, child in value.items()}
    if type(value) is list:
        return [_rename(child, old, new) for child in value]
    return new if value == old else value


def _set_initial_period(harness, start, end):
    line = harness.data['/v1/invoices/in_Synthetic/lines']['data'][0]
    item = harness.data['/v1/subscriptions/sub_Synthetic']['items']['data'][0]
    line['period'] = {'start': int(start.timestamp()), 'end': int(end.timestamp())}
    item['current_period_start'] = int(start.timestamp())
    item['current_period_end'] = int(end.timestamp())
    harness.initial_end = end


class RenewalHarness(Harness):
    def __init__(self, path, uid=1, plan='monthly'):
        super().__init__(path, uid, plan)
        self.plan = plan
        self.initial_end = datetime.fromtimestamp(
            self.data['/v1/invoices/in_Synthetic/lines']['data'][0]['period']['end'], timezone.utc)

    def prepare_renewal(self, *, start=None, end=None, reuse=None, event_id='evt_Renewal'):
        start = self.initial_end if start is None else start
        end = SUCCESSOR_ENDS[self.plan] if end is None else end
        replacements = (
            ('in_Synthetic', 'in_Renewal'), ('il_Synthetic', 'il_Renewal'),
            ('inpay_Synthetic', 'inpay_Renewal'), ('pi_Synthetic', 'pi_Renewal'),
            ('ch_Synthetic', 'ch_Renewal'))
        current = copy.deepcopy(self.data)
        for old_id, new_id in replacements:
            current = _rename(current, old_id, new_id)
        renamed = {}
        for path, body in current.items():
            for old_id, new_id in replacements:
                path = path.replace(old_id, new_id)
            renamed[path] = body
        self.data = renamed
        invoice = self.data['/v1/invoices/in_Renewal']
        invoice['billing_reason'] = 'subscription_cycle'
        line = self.data['/v1/invoices/in_Renewal/lines']['data'][0]
        line['period'] = {'start': int(start.timestamp()), 'end': int(end.timestamp())}
        subscription = self.data['/v1/subscriptions/sub_Synthetic']
        subscription['latest_invoice'] = 'in_Renewal'
        item = subscription['items']['data'][0]
        item['current_period_start'] = int(start.timestamp())
        item['current_period_end'] = int(end.timestamp())
        observed = self.initial_end - timedelta(minutes=2)
        for obj in (invoice, self.data['/v1/invoice_payments']['data'][0],
                    self.data['/v1/payment_intents/pi_Renewal'],
                    self.data['/v1/charges/ch_Renewal']):
            obj['created'] = int(observed.timestamp())
        invoice['status_transitions']['paid_at'] = int(observed.timestamp())
        self.data['/v1/invoice_payments']['data'][0]['status_transitions']['paid_at'] = int(observed.timestamp())
        if reuse:
            field, old_id = reuse
            paths = {
                'invoice': (invoice, 'id'), 'line': (line, 'id'),
                'payment': (self.data['/v1/invoice_payments']['data'][0], 'id'),
                'intent': (self.data['/v1/invoice_payments']['data'][0]['payment'], 'payment_intent'),
                'charge': (self.data['/v1/payment_intents/pi_Renewal'], 'latest_charge'),
            }
            paths[field][0][paths[field][1]] = old_id
        self.event = dict(id=event_id, object='event', type='invoice.paid', livemode=False,
            api_version=source.API_VERSION, created=int(observed.timestamp()),
            data={'object': copy.deepcopy(invoice)})

    def renew(self, *, now=None, raw=None, header=None, clock=None):
        now = self.initial_end - timedelta(minutes=1) if now is None else now
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_successful_renewal(
            self.authority, self.repo, raw,
            signature(raw, now) if header is None else header,
            clock=clock or (lambda: now))


@pytest.fixture
def renewal(tmp_path):
    value = RenewalHarness(tmp_path/'renewal.db')
    assert value.ingest().disposition == 'admitted'
    value.prepare_renewal()
    yield value
    value.repo.close()


@pytest.mark.parametrize('plan', ['monthly', 'six_month', 'yearly'])
def test_signed_initial_and_renewal_real_get_csrf_post_save(app, tmp_path, plan):
    import reserved.database as db
    client, uid = dashboard._authenticated_client(app)
    h = RenewalHarness(tmp_path/'renewal.db', uid, plan)
    now = [NOW]
    try:
        assert h.ingest().disposition == 'admitted'
        surfaces.install_local_exact_utc_paid_surface_access(
            app, authority=h.authority, repository=h.repo, clock=lambda: now[0])
        app.config['WTF_CSRF_ENABLED'] = True
        response = client.get('/v2/settings')
        assert response.status_code == 200
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        form = dict(first_name='Initial Period', entity_type='sole_trader', student_loan='none',
                    accounting_method='cash_basis', vat_status='not_vat_registered', csrf_token=token)
        assert client.post('/v2/settings', data=form).status_code == 302
        assert db.get_profile_by_user(uid)['display_name'] == 'Initial Period'

        h.prepare_renewal()
        assert h.renew().disposition == 'admitted'
        now[0] = h.initial_end - timedelta(microseconds=1)
        response = client.get('/v2/settings')
        assert response.status_code == 200
        now[0] = h.initial_end
        response = client.get('/v2/settings')
        assert response.status_code == 200
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        form['first_name'], form['csrf_token'] = 'Renewed Period', token
        assert client.post('/v2/settings', data=form).status_code == 302
        assert db.get_profile_by_user(uid)['display_name'] == 'Renewed Period'
        now[0] = SUCCESSOR_ENDS[plan]
        old.denied(client.get('/v2/settings'))
    finally:
        h.repo.close()


@pytest.mark.parametrize('offset', [timedelta(microseconds=-1), timedelta(0)])
def test_predecessor_exclusive_boundary_selects_authenticated_period(renewal, offset):
    assert renewal.renew().disposition == 'admitted'
    when = renewal.initial_end + offset
    assert source.allows_paid_request(renewal.authority, renewal.repo, user_id=1, now=when)
    fact = source.current_fact(renewal.authority, renewal.repo, user_id=1, now=when)
    from reserved.billing import exact_utc_entitlement as exact
    admitted = exact.admit_initial(fact, authority=renewal.authority,
                                   owner='synthetic-owner', now=when)
    assert exact._projection(admitted)[4] == (NOW if offset < timedelta(0) else renewal.initial_end)


def test_delayed_renewal_has_no_backfill_but_expired_predecessor_is_admissible(renewal):
    delayed = renewal.initial_end + timedelta(days=2)
    result = renewal.renew(now=delayed)
    assert result.disposition == 'admitted'
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end + timedelta(days=1))
    assert source.allows_paid_request(renewal.authority, renewal.repo, user_id=1, now=delayed)
    receipt, _ = renewal.repo.read(renewal.authority.snapshot().instance, RECEIPT_KEY)
    assert receipt['access_start'] == delayed.isoformat()


@pytest.mark.parametrize('delta', [timedelta(seconds=-1), timedelta(seconds=1), timedelta(days=31)])
def test_overlap_gap_and_skipped_period_refuse_without_head_change(renewal, delta):
    before = renewal.authority.snapshot()
    renewal.prepare_renewal(start=renewal.initial_end + delta)
    assert renewal.renew().disposition == 'refused'
    assert renewal.authority.snapshot() == before
    assert len(renewal.repo.read_lineage(before.instance, RECEIPT_KEY)) == 1


@pytest.mark.parametrize('period', ['one_second', 'ten_year'])
def test_monthly_short_or_ten_year_successor_refuses_before_reservation(renewal, period):
    before_snapshot = renewal.authority.snapshot()
    before_lineage = renewal.repo.read_lineage(before_snapshot.instance, RECEIPT_KEY)
    end = (renewal.initial_end + timedelta(seconds=1) if period == 'one_second'
           else renewal.initial_end.replace(year=renewal.initial_end.year + 10))
    renewal.data['/v1/invoices/in_Renewal/lines']['data'][0]['period']['end'] = int(end.timestamp())
    renewal.data['/v1/subscriptions/sub_Synthetic']['items']['data'][0]['current_period_end'] = int(end.timestamp())
    result = renewal.renew()
    assert result.disposition == 'refused' and result.committed is False and result.fact is None
    assert renewal.authority.snapshot() == before_snapshot
    assert source._state(renewal.authority)['publication'] == (before_snapshot, None)
    assert renewal.repo.read_lineage(before_snapshot.instance, RECEIPT_KEY) == before_lineage
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)


@pytest.mark.parametrize('plan,predecessor_end,successor_end', [
    ('monthly', datetime(2027, 1, 31, 13, 25, 17, tzinfo=timezone.utc),
     datetime(2027, 2, 28, 13, 25, 17, tzinfo=timezone.utc)),
    ('monthly', datetime(2028, 1, 31, 13, 25, 17, tzinfo=timezone.utc),
     datetime(2028, 2, 29, 13, 25, 17, tzinfo=timezone.utc)),
    ('six_month', datetime(2027, 8, 31, 13, 25, 17, tzinfo=timezone.utc),
     datetime(2028, 2, 29, 13, 25, 17, tzinfo=timezone.utc)),
    ('yearly', datetime(2028, 2, 29, 13, 25, 17, tzinfo=timezone.utc),
     datetime(2029, 2, 28, 13, 25, 17, tzinfo=timezone.utc)),
])
def test_exact_catalogue_calendar_successor_month_end_and_leap_rules(
        tmp_path, plan, predecessor_end, successor_end):
    h = RenewalHarness(tmp_path/(plan + predecessor_end.date().isoformat() + '.db'), plan=plan)
    try:
        _set_initial_period(h, predecessor_end - timedelta(days=20), predecessor_end)
        assert h.ingest().disposition == 'admitted'
        h.prepare_renewal(start=predecessor_end, end=successor_end)
        result = h.renew()
        assert result.disposition == 'admitted' and result.fact is not None
        receipt, _ = h.repo.read(h.authority.snapshot().instance, RECEIPT_KEY)
        assert receipt['service_start'] == predecessor_end.isoformat()
        assert receipt['service_end'] == successor_end.isoformat()
    finally:
        h.repo.close()


@pytest.mark.parametrize('change', ['customer', 'item', 'price', 'plan'])
def test_changed_scope_plan_item_or_price_refuses_without_head_change(renewal, change):
    before = renewal.authority.snapshot()
    if change == 'customer':
        renewal.data['/v1/invoices/in_Renewal']['customer'] = 'cus_Other'
    elif change == 'item':
        renewal.data['/v1/invoices/in_Renewal/lines']['data'][0]['parent'][
            'subscription_item_details']['subscription_item'] = 'si_Other'
    elif change == 'price':
        renewal.data['/v1/invoices/in_Renewal/lines']['data'][0]['pricing'][
            'price_details']['price'] = 'price_Other'
    else:
        renewal.data['/v1/prices/price_Synthetic']['unit_amount'] = 499
    result = renewal.renew()
    assert result.disposition == 'refused' and result.fact is None
    assert renewal.authority.snapshot() == before
    assert len(renewal.repo.read_lineage(before.instance, RECEIPT_KEY)) == 1


def test_sequence_three_refuses_without_head_change(renewal):
    assert renewal.renew().disposition == 'admitted'
    before = renewal.authority.snapshot()
    lineage = renewal.repo.read_lineage(before.instance, RECEIPT_KEY)
    renewal.prepare_renewal(start=SUCCESSOR_ENDS['monthly'],
                            end=SUCCESSOR_ENDS['monthly'] + timedelta(days=31),
                            event_id='evt_Third')
    renewal.event['data']['object']['billing_reason'] = 'subscription_cycle'
    assert renewal.renew(now=SUCCESSOR_ENDS['monthly'] - timedelta(minutes=1)).disposition != 'admitted'
    assert renewal.authority.snapshot() == before
    assert renewal.repo.read_lineage(before.instance, RECEIPT_KEY) == lineage


def test_identical_replay_preserves_successor_receipt_verification_and_head(renewal):
    assert renewal.renew().disposition == 'admitted'
    before = renewal.repo.read_lineage(renewal.authority.snapshot().instance, RECEIPT_KEY)
    result = renewal.renew(now=renewal.initial_end + timedelta(minutes=1))
    assert result.disposition == 'admitted'
    assert renewal.repo.read_lineage(renewal.authority.snapshot().instance, RECEIPT_KEY) == before


def test_renewal_reverifies_signature_through_the_single_call_site(renewal, monkeypatch):
    original = source.verify_stripe_signature
    calls = []
    def counted(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(source, 'verify_stripe_signature', counted)
    assert renewal.renew().disposition == 'admitted'
    assert calls == [True, True]


def _interrupt_reservation_publication(harness, marker):
    touched = []
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is source._ingest_paid_invoice.__code__
                and marker in linecache.getline(frame.f_code.co_filename, frame.f_lineno)):
            touched.append(frame.f_lineno)
            raise RuntimeError('synthetic reservation publication interruption')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = harness.renew()
    finally:
        sys.settrace(prior)
    assert len(touched) == 1
    return result


def test_interruption_before_atomic_reservation_leaves_no_partial_publication(renewal):
    before = renewal.authority.snapshot()
    lineage = renewal.repo.read_lineage(before.instance, RECEIPT_KEY)
    result = _interrupt_reservation_publication(
        renewal, "state['publication'] = (reserved, reservation)")
    assert result.disposition == 'refused' and result.committed is False and result.fact is None
    assert source._state(renewal.authority)['publication'] == (before, None)
    assert renewal.repo.read_lineage(before.instance, RECEIPT_KEY) == lineage
    assert renewal.renew().disposition == 'admitted'


@pytest.mark.parametrize('different', ['event', 'evidence'])
def test_interruption_after_atomic_reservation_fixes_only_first_exact_proposal(renewal, different):
    initial = renewal.authority.snapshot()
    original_event = copy.deepcopy(renewal.event)
    result = _interrupt_reservation_publication(renewal, 'snapshot = reserved')
    reserved, reservation = source._state(renewal.authority)['publication']
    assert result.disposition == 'refused' and result.committed is False and result.fact is None
    assert reserved.revision == initial.revision + 1 and reserved.accepted == initial.accepted
    assert reservation['revision'] == reserved.revision
    assert reservation['predecessor'] == initial.accepted
    assert len(renewal.repo.read_lineage(initial.instance, RECEIPT_KEY)) == 1

    if different == 'event':
        renewal.event['id'] = 'evt_DifferentAfterReservation'
    else:
        renewal.data['/v1/invoices/in_Renewal/lines']['data'][0]['id'] = 'il_DifferentAfterReservation'
    changed = renewal.renew()
    assert changed.disposition == 'refused' and changed.fact is None
    assert source._state(renewal.authority)['publication'] == (reserved, reservation)
    assert len(renewal.repo.read_lineage(initial.instance, RECEIPT_KEY)) == 1
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)

    renewal.event = original_event
    renewal.data['/v1/invoices/in_Renewal/lines']['data'][0]['id'] = 'il_Renewal'
    retry = renewal.renew(now=renewal.initial_end)
    assert retry.disposition == 'admitted' and retry.fact is not None
    assert len(renewal.repo.read_lineage(initial.instance, RECEIPT_KEY)) == 2


def test_competing_successors_and_same_proposal_concurrency_have_one_head(tmp_path):
    h = RenewalHarness(tmp_path/'race.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_renewal()
        barrier = threading.Barrier(2)
        outcomes = []
        def run():
            barrier.wait()
            outcomes.append(h.renew())
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert any(result.disposition == 'admitted' for result in outcomes)
        lineage = h.repo.read_lineage(h.authority.snapshot().instance, RECEIPT_KEY)
        assert len(lineage) == 2 and lineage[-1][0]['sequence'] == 2
        before = h.authority.snapshot()
        h.event['id'] = 'evt_Competing'
        assert h.renew().disposition == 'reconciliation_required'
        assert h.authority.snapshot() == before
    finally:
        h.repo.close()
