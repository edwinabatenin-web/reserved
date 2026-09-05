"""Bounded signed scheduled-cancellation ingress and paid-surface behavior."""
import copy
from datetime import datetime, timedelta, timezone
import re
import threading

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import local_paid_surface_access as surfaces
from tests import test_w10_local_paid_surface_access as old
from tests import test_w10_local_dashboard_access as dashboard
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY, encoded, signature
from tests.test_w10_stripe_successful_renewal import RenewalHarness, SUCCESSOR_ENDS, _set_initial_period

app = old.app


class CancellationHarness(RenewalHarness):
    def prepare_cancellation(self, *, cancel_at=None, event_id='evt_Cancellation',
                             request_id='req_Cancellation', reason='cancellation_requested',
                             created=None):
        subscription = self.data['/v1/subscriptions/sub_Synthetic']
        subscription.update(cancel_at_period_end=True, cancel_at=cancel_at,
            canceled_at=int((created or self.cancellation_now()).timestamp()),
            cancellation_details={'reason': reason, 'comment': None, 'feedback': None},
            schedule=None, pause_collection=None, trial_start=None, trial_end=None,
            trial_settings=None, pending_update=None, discount=None, discounts=[],
            promotion_code=None, promotion_codes=[], offer=None, offers=[])
        subscription['items']['data'][0].update(
            proration=False, discount=None, discounts=[], promotion_code=None,
            promotion_codes=[], offer=None, offers=[])
        observed = created or self.cancellation_now()
        self.event = dict(id=event_id, object='event',
            type='customer.subscription.updated', livemode=False,
            api_version=source.API_VERSION, created=int(observed.timestamp()),
            request={'id': request_id, 'idempotency_key': None},
            data={'object': copy.deepcopy(subscription),
                  'previous_attributes': {'cancel_at_period_end': False}})

    def cancellation_now(self):
        item = self.data['/v1/subscriptions/sub_Synthetic']['items']['data'][0]
        start = datetime.fromtimestamp(item['current_period_start'], timezone.utc)
        end = datetime.fromtimestamp(item['current_period_end'], timezone.utc)
        return start + min(timedelta(minutes=5), (end - start) / 2)

    def cancel(self, *, now=None, raw=None, header=None, clock=None):
        now = self.cancellation_now() if now is None else now
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_scheduled_cancellation(
            self.authority, self.repo, raw,
            signature(raw, now) if header is None else header,
            clock=clock or (lambda: now))


@pytest.fixture
def cancellation(tmp_path):
    value = CancellationHarness(tmp_path/'cancellation.db')
    assert value.ingest().disposition == 'admitted'
    value.prepare_cancellation()
    yield value
    value.repo.close()


@pytest.mark.parametrize('renewed', [False, True])
def test_exact_scheduled_end_preserves_paid_period_and_exposes_no_actor(tmp_path, renewed):
    h = CancellationHarness(tmp_path/('renewed.db' if renewed else 'initial.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        if renewed:
            h.prepare_renewal()
            assert h.renew().disposition == 'admitted'
        before = h.repo.read_lineage(h.authority.snapshot().instance, RECEIPT_KEY)
        h.prepare_cancellation()
        result = h.cancel()
        assert result.disposition == 'admitted' and result.committed is True
        assert h.repo.read_lineage(h.authority.snapshot().instance, RECEIPT_KEY) == before
        details = source.cancellation_fact_details(result.fact)
        assert details['disposition'] == 'subscription_scheduled_to_end_at_paid_period_boundary'
        assert set(details) == {'disposition', 'exclusive_service_end',
                                'paid_receipt_id', 'paid_fact_id'}
        assert details['exclusive_service_end'] == before[-1][0]['service_end']
    finally:
        h.repo.close()


@pytest.mark.parametrize('plan,start,end', [
    ('monthly', datetime(2028, 1, 31, 4, 5, 7, tzinfo=timezone.utc),
     datetime(2028, 2, 29, 4, 5, 7, tzinfo=timezone.utc)),
    ('six_month', datetime(2027, 8, 31, 19, 20, 21, tzinfo=timezone.utc),
     datetime(2028, 2, 29, 19, 20, 21, tzinfo=timezone.utc)),
    ('yearly', datetime(2028, 2, 29, 23, 59, 31, tzinfo=timezone.utc),
     datetime(2029, 2, 28, 23, 59, 31, tzinfo=timezone.utc)),
])
@pytest.mark.parametrize('explicit_cancel_at', [False, True])
def test_arbitrary_second_month_end_and_leap_boundaries(
        tmp_path, plan, start, end, explicit_cancel_at):
    h = CancellationHarness(tmp_path/(plan + str(explicit_cancel_at) + '.db'), plan=plan)
    try:
        _set_initial_period(h, start, end)
        assert h.ingest(now=start + timedelta(seconds=1)).disposition == 'admitted'
        h.prepare_cancellation(cancel_at=int(end.timestamp()) if explicit_cancel_at else None,
                               created=start + timedelta(seconds=2))
        assert h.cancel(now=start + timedelta(seconds=2)).disposition == 'admitted'
        assert source.allows_paid_request(h.authority, h.repo, user_id=1,
                                          now=end - timedelta(microseconds=1))
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1, now=end)
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
                                              now=end + timedelta(microseconds=1))
    finally:
        h.repo.close()


@pytest.mark.parametrize('renewed', [False, True])
def test_actual_signed_session_settings_get_csrf_post_and_exclusive_end(
        app, tmp_path, renewed):
    import reserved.database as db
    client, uid = dashboard._authenticated_client(app)
    h = CancellationHarness(tmp_path/('surface-renewed.db' if renewed else 'surface.db'), uid)
    try:
        assert h.ingest().disposition == 'admitted'
        if renewed:
            h.prepare_renewal()
            assert h.renew().disposition == 'admitted'
        now = [h.cancellation_now()]
        h.prepare_cancellation(created=now[0])
        assert h.cancel(now=now[0]).disposition == 'admitted'
        surfaces.install_local_exact_utc_paid_surface_access(
            app, authority=h.authority, repository=h.repo, clock=lambda: now[0])
        app.config['WTF_CSRF_ENABLED'] = True
        response = client.get('/v2/settings')
        assert response.status_code == 200
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        form = dict(first_name='Scheduled End', entity_type='sole_trader',
                    student_loan='none', accounting_method='cash_basis',
                    vat_status='not_vat_registered', csrf_token=token)
        assert client.post('/v2/settings', data=form).status_code == 302
        assert db.get_profile_by_user(uid)['display_name'] == 'Scheduled End'
        end = datetime.fromisoformat(source.cancellation_fact_details(
            h.cancel(now=now[0]).fact)['exclusive_service_end'])
        now[0] = end - timedelta(microseconds=1)
        assert client.get('/v2/settings').status_code == 200
        now[0] = end
        old.denied(client.get('/v2/settings'))
    finally:
        h.repo.close()


@pytest.mark.parametrize('mutation', [
    'null_request', 'malformed_request', 'missing_reason', 'unknown_reason',
    'disputed', 'payment_failed', 'missing_previous', 'prior_true', 'flag_false',
    'wrong_type', 'wrong_version', 'connect', 'live', 'wrong_customer', 'wrong_item',
    'wrong_price', 'multiple_items', 'incomplete_items', 'inactive', 'manual_collection',
    'schedule', 'pause', 'trial', 'pending_update', 'discount', 'promotion',
    'offer', 'item_discount', 'proration', 'earlier_cancel_at', 'later_cancel_at',
    'changed_period', 'snapshot_disagreement',
])
def test_missing_contradictory_or_unsupported_source_refuses_without_head_change(
        cancellation, mutation):
    event = cancellation.event
    signed = event['data']['object']
    retrieved = cancellation.data['/v1/subscriptions/sub_Synthetic']
    end = retrieved['items']['data'][0]['current_period_end']
    if mutation == 'null_request': event['request'] = None
    elif mutation == 'malformed_request': event['request'] = {'id': ''}
    elif mutation == 'missing_reason': signed['cancellation_details']['reason'] = None
    elif mutation == 'unknown_reason': signed['cancellation_details']['reason'] = 'other'
    elif mutation == 'disputed':
        signed['cancellation_details']['reason'] = retrieved['cancellation_details']['reason'] = 'payment_disputed'
    elif mutation == 'payment_failed':
        signed['cancellation_details']['reason'] = retrieved['cancellation_details']['reason'] = 'payment_failed'
    elif mutation == 'missing_previous': event['data']['previous_attributes'] = {}
    elif mutation == 'prior_true': event['data']['previous_attributes']['cancel_at_period_end'] = True
    elif mutation == 'flag_false': signed['cancel_at_period_end'] = False
    elif mutation == 'wrong_type': event['type'] = 'customer.subscription.deleted'
    elif mutation == 'wrong_version': event['api_version'] = '2025-05-28.basil'
    elif mutation == 'connect': event['account'] = 'acct_Connect'
    elif mutation == 'live': event['livemode'] = True
    elif mutation == 'wrong_customer': signed['customer'] = 'cus_Other'
    elif mutation == 'wrong_item': signed['items']['data'][0]['id'] = 'si_Other'
    elif mutation == 'wrong_price': signed['items']['data'][0]['price']['id'] = 'price_Other'
    elif mutation == 'multiple_items': signed['items']['data'] *= 2
    elif mutation == 'incomplete_items': signed['items']['has_more'] = True
    elif mutation == 'inactive': signed['status'] = 'canceled'
    elif mutation == 'manual_collection': signed['collection_method'] = 'send_invoice'
    elif mutation == 'schedule': signed['schedule'] = 'sub_sched_One'
    elif mutation == 'pause': signed['pause_collection'] = {'behavior': 'void'}
    elif mutation == 'trial': signed['trial_end'] = end
    elif mutation == 'pending_update': signed['pending_update'] = {}
    elif mutation == 'discount': signed['discounts'] = ['di_One']
    elif mutation == 'promotion': signed['promotion_code'] = 'promo_One'
    elif mutation == 'offer': signed['offer'] = 'offer_One'
    elif mutation == 'item_discount': signed['items']['data'][0]['discounts'] = ['di_One']
    elif mutation == 'proration': signed['items']['data'][0]['proration'] = True
    elif mutation == 'earlier_cancel_at': signed['cancel_at'] = end - 1
    elif mutation == 'later_cancel_at': signed['cancel_at'] = end + 1
    elif mutation == 'changed_period': signed['items']['data'][0]['current_period_end'] = end - 1
    else: retrieved['canceled_at'] -= 1
    before = cancellation.authority.snapshot()
    lineage = cancellation.repo.read_lineage(before.instance, RECEIPT_KEY)
    result = cancellation.cancel()
    assert result.disposition == 'refused' and result.committed is False and result.fact is None
    assert cancellation.authority.snapshot() == before
    assert cancellation.repo.read_lineage(before.instance, RECEIPT_KEY) == lineage
    assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                      user_id=1, now=cancellation.cancellation_now())


@pytest.mark.parametrize('scope,name', [
    ('subscription', 'schedule'), ('subscription', 'pause_collection'),
    ('subscription', 'trial_start'), ('subscription', 'trial_end'),
    ('subscription', 'trial_settings'), ('subscription', 'pending_update'),
    ('subscription', 'discount'), ('subscription', 'discounts'),
    ('subscription', 'promotion_code'), ('subscription', 'promotion_codes'),
    ('subscription', 'offer'), ('subscription', 'offers'),
    ('subscription', 'cancel_at'), ('item', 'proration'), ('item', 'discount'),
    ('item', 'discounts'), ('item', 'promotion_code'), ('item', 'promotion_codes'),
    ('item', 'offer'), ('item', 'offers'),
])
def test_every_explicit_absence_predicate_is_required_in_snapshot_and_retrieval(
        cancellation, scope, name):
    signed = cancellation.event['data']['object']
    retrieved = cancellation.data['/v1/subscriptions/sub_Synthetic']
    signed_target = signed if scope == 'subscription' else signed['items']['data'][0]
    retrieved_target = (retrieved if scope == 'subscription'
                        else retrieved['items']['data'][0])
    del signed_target[name]
    del retrieved_target[name]
    before = cancellation.authority.snapshot()
    result = cancellation.cancel()
    assert result.disposition == 'refused' and result.committed is False
    assert cancellation.authority.snapshot() == before
    assert cancellation.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None


@pytest.mark.parametrize('scope,name,value', [
    ('subscription', 'schedule', []), ('subscription', 'pause_collection', False),
    ('subscription', 'trial_end', False), ('subscription', 'pending_update', []),
    ('subscription', 'discounts', None), ('subscription', 'promotion_codes', {}),
    ('subscription', 'offers', None), ('item', 'proration', 0),
    ('item', 'discounts', None), ('item', 'promotion_codes', {}),
    ('item', 'offers', None),
])
def test_absence_predicates_require_exact_types(cancellation, scope, name, value):
    signed = cancellation.event['data']['object']
    target = signed if scope == 'subscription' else signed['items']['data'][0]
    target[name] = value
    assert cancellation.cancel().disposition == 'refused'


def test_wrong_signature_key_endpoint_account_owner_and_store_refuse(tmp_path):
    from dataclasses import replace
    h = CancellationHarness(tmp_path/'a.db')
    other = CancellationHarness(tmp_path/'b.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert other.ingest().disposition == 'admitted'
        h.prepare_cancellation()
        raw = encoded(h.event)
        assert h.cancel(raw=raw, header=signature(raw, h.cancellation_now(), key=b'x' * 32)).disposition == 'refused'
        assert source.ingest_scheduled_cancellation(
            h.authority, other.repo, raw, signature(raw, h.cancellation_now()),
            clock=lambda: h.cancellation_now()).disposition == 'refused'
        h.response_hook = lambda response: source.SourceResponse(
            replace(response.request, endpoint='wrong-endpoint'), response.body)
        assert h.cancel().disposition == 'refused'
    finally:
        h.repo.close(); other.repo.close()


def test_exact_replay_and_concurrent_same_proposal_are_idempotent(tmp_path):
    h = CancellationHarness(tmp_path/'race.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_cancellation()
        barrier = threading.Barrier(2)
        results = []
        def run():
            barrier.wait()
            results.append(h.cancel())
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        accepted = next(result for result in results if result.disposition == 'admitted')
        before = h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)
        snapshot = h.authority.snapshot()
        replay = h.cancel(now=h.cancellation_now() + timedelta(seconds=1))
        assert (replay.disposition == 'admitted' and replay.fact is accepted.fact
                and h.authority.snapshot() == snapshot)
        assert h.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY) == before
        end = datetime.fromisoformat(before[1]['service_end'])
        boundary_replay = h.cancel(now=end)
        assert (boundary_replay.disposition == 'admitted'
                and boundary_replay.fact is accepted.fact
                and h.authority.snapshot() == snapshot)
        assert h.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY) == before
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1, now=end)
    finally:
        h.repo.close()


def test_request_reason_metadata_and_canceled_at_never_attribute_an_actor(cancellation):
    cancellation.event['data']['object']['metadata'] = {'customer_name': 'Synthetic Person'}
    cancellation.data['/v1/subscriptions/sub_Synthetic']['metadata'] = {
        'customer_name': 'Synthetic Person'}
    result = cancellation.cancel()
    assert result.disposition == 'admitted'
    details = source.cancellation_fact_details(result.fact)
    _, control, _ = cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    forbidden = ('actor', 'customer_name', 'requested_by', 'metadata', 'canceled_at')
    assert all(name not in details and name not in control for name in forbidden)


def test_evaluation_at_or_after_paid_end_refuses_without_control(cancellation):
    before = cancellation.authority.snapshot()
    end = datetime.fromtimestamp(
        cancellation.event['data']['object']['items']['data'][0]['current_period_end'],
        timezone.utc)
    result = cancellation.cancel(now=end)
    assert result.disposition == 'refused' and result.committed is False
    assert cancellation.authority.snapshot() == before
    assert cancellation.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None


def test_changed_duplicate_reconciles_and_does_not_move_head(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.authority.snapshot()
    cancellation.event['pending_webhooks'] = 2
    result = cancellation.cancel()
    assert result.disposition == 'reconciliation_required' and result.committed is True
    assert cancellation.authority.snapshot() == before


def test_changed_duplicate_with_now_unsupported_object_is_reconciliation_only(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.authority.snapshot()
    cancellation.event['data']['object']['status'] = 'canceled'
    result = cancellation.cancel()
    assert result.disposition == 'reconciliation_required' and result.committed is True
    assert cancellation.authority.snapshot() == before


def test_terminal_delivery_after_control_is_reconciliation_not_a_new_boundary(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.authority.snapshot()
    cancellation.event['type'] = 'customer.subscription.deleted'
    result = cancellation.cancel()
    assert result.disposition == 'reconciliation_required' and result.committed is True
    assert cancellation.authority.snapshot() == before


def test_scheduled_control_blocks_later_ordinary_renewal(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.authority.snapshot()
    cancellation.prepare_renewal()
    result = cancellation.renew()
    assert result.disposition == 'refused' and result.fact is None
    assert cancellation.authority.snapshot() == before
    assert len(cancellation.repo.read_lineage(before.instance, RECEIPT_KEY)) == 1


def test_renewal_cancellation_race_has_one_atomic_head_winner(tmp_path):
    h = CancellationHarness(tmp_path/'renewal-cancellation-race.db')
    try:
        assert h.ingest().disposition == 'admitted'
        initial_subscription = copy.deepcopy(h.data['/v1/subscriptions/sub_Synthetic'])
        h.prepare_renewal()
        renewal_event = encoded(h.event)
        renewal_data = copy.deepcopy(h.data)
        race_now = h.initial_end - timedelta(minutes=1)
        cancellation_subscription = initial_subscription
        cancellation_subscription.update(cancel_at_period_end=True, cancel_at=None,
            canceled_at=int(race_now.timestamp()),
            cancellation_details={'reason': 'cancellation_requested', 'comment': None,
                                  'feedback': None},
            schedule=None, pause_collection=None, trial_start=None, trial_end=None,
            trial_settings=None, pending_update=None, discount=None, discounts=[],
            promotion_code=None, promotion_codes=[], offer=None, offers=[])
        cancellation_subscription['items']['data'][0].update(
            proration=False, discount=None, discounts=[], promotion_code=None,
            promotion_codes=[], offer=None, offers=[])
        cancellation_event = encoded(dict(id='evt_CancellationRace', object='event',
            type='customer.subscription.updated', livemode=False,
            api_version=source.API_VERSION, created=int(race_now.timestamp()),
            request={'id': 'req_CancellationRace', 'idempotency_key': None},
            data={'object': copy.deepcopy(cancellation_subscription),
                  'previous_attributes': {'cancel_at_period_end': False}}))

        class ThreadData(dict):
            def __getitem__(self, key):
                if (key == '/v1/subscriptions/sub_Synthetic'
                        and threading.current_thread().name == 'cancellation'):
                    return cancellation_subscription
                return renewal_data[key]

        h.data = ThreadData()
        barrier = threading.Barrier(2)
        outcomes = {}
        def cancel():
            barrier.wait()
            outcomes['cancellation'] = source.ingest_scheduled_cancellation(
                h.authority, h.repo, cancellation_event,
                signature(cancellation_event, race_now), clock=lambda: race_now)
        def renew():
            barrier.wait()
            outcomes['renewal'] = source.ingest_successful_renewal(
                h.authority, h.repo, renewal_event,
                signature(renewal_event, race_now), clock=lambda: race_now)
        threads = [threading.Thread(name='cancellation', target=cancel),
                   threading.Thread(name='renewal', target=renew)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert sorted(result.disposition for result in outcomes.values()) == ['admitted', 'refused']
        lineage, control, lifecycle_head = h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)
        assert (len(lineage), control is not None) in ((1, True), (2, False))
        assert h.authority.snapshot().lifecycle_head == lifecycle_head
    finally:
        h.repo.close()
