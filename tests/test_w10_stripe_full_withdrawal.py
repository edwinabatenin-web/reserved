"""Closed synthetic Stripe full-refund source-admission evidence."""
import copy
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from tests.test_w10_stripe_initial_payment_ingress import (
    Harness, NOW, RECEIPT_KEY, encoded, signature,
)


class WithdrawalHarness(Harness):
    def prepare_withdrawal(self, *, event_id='evt_FullWithdrawal', split=(999,)):
        paid, _ = self.repo.read(self.authority.snapshot().instance, RECEIPT_KEY)
        charge_id = paid['evidence']['charge']
        intent_id = paid['evidence']['intent']
        amount = paid['evidence']['amount']
        charge = self.data['/v1/charges/' + charge_id]
        charge.update(refunded=True, amount_refunded=amount)
        refunds = []
        for index, value in enumerate(split, 1):
            refunds.append(dict(id=f're_{index}Synthetic', object='refund', amount=value,
                charge=charge_id, payment_intent=intent_id, currency=paid['evidence']['currency'],
                status='succeeded', balance_transaction=f'txn_{index}Synthetic'))
        self.data['/v1/refunds'] = dict(object='list', url='/v1/refunds',
            has_more=False, data=refunds)
        self.withdrawal_time = NOW + timedelta(seconds=17)
        self.event = dict(id=event_id, object='event', type='charge.refunded',
            livemode=False, api_version=source.API_VERSION,
            created=int(NOW.timestamp()), data={'object': copy.deepcopy(charge)})

    def withdraw(self, *, now=None, raw=None, header=None, clock=None):
        now = self.withdrawal_time if now is None else now
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_full_withdrawal(self.authority, self.repo, raw,
            signature(raw, now) if header is None else header,
            clock=clock or (lambda: now))


@pytest.fixture
def withdrawal(tmp_path):
    value = WithdrawalHarness(tmp_path/'withdrawal.db')
    assert value.ingest().disposition == 'admitted'
    value.prepare_withdrawal()
    yield value
    value.repo.close()


@pytest.mark.parametrize('split', [(999,), (1000, 1900), (900, 1000, 1000)])
def test_one_and_multiple_successful_refunds_admit_exact_suspension(tmp_path, split):
    h = WithdrawalHarness(tmp_path/(str(len(split)) + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(split=split)
        result = h.withdraw()
        assert result.disposition == 'admitted' and result.committed is True
        details = source.full_withdrawal_fact_details(result.fact)
        assert details['withdrawal_verified_at_utc'] == h.withdrawal_time.isoformat()
        assert details['refunds'] == tuple(sorted(f're_{i}Synthetic' for i in range(1, len(split)+1)))
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=h.withdrawal_time)
    finally:
        h.repo.close()


@pytest.mark.parametrize('mutation', [
    'partial', 'pending', 'requires_action', 'failed', 'canceled', 'empty',
    'duplicate', 'over', 'has_more', 'wrong_url', 'null_balance', 'wrong_charge',
    'wrong_intent', 'wrong_currency', 'boolean_amount', 'float_amount', 'zero_amount',
    'charge_partial', 'charge_disputed', 'charge_wrong_customer',
])
def test_incomplete_or_contradictory_refund_shapes_have_no_head_effect(
        withdrawal, mutation):
    before = withdrawal.authority.snapshot()
    refunds = withdrawal.data['/v1/refunds']
    charge = withdrawal.data['/v1/charges/ch_Synthetic']
    item = refunds['data'][0]
    if mutation == 'partial': item['amount'] = 2899
    elif mutation in ('pending', 'requires_action', 'failed', 'canceled'): item['status'] = mutation
    elif mutation == 'empty': refunds['data'] = []
    elif mutation == 'duplicate': refunds['data'].append(copy.deepcopy(item))
    elif mutation == 'over': item['amount'] = 2901
    elif mutation == 'has_more': refunds['has_more'] = True
    elif mutation == 'wrong_url': refunds['url'] = '/v1/charges'
    elif mutation == 'null_balance': item['balance_transaction'] = None
    elif mutation == 'wrong_charge': item['charge'] = 'ch_Other'
    elif mutation == 'wrong_intent': item['payment_intent'] = 'pi_Other'
    elif mutation == 'wrong_currency': item['currency'] = 'usd'
    elif mutation == 'boolean_amount': item['amount'] = True
    elif mutation == 'float_amount': item['amount'] = 999.0
    elif mutation == 'zero_amount': item['amount'] = 0
    elif mutation == 'charge_partial': charge['refunded'] = False
    elif mutation == 'charge_disputed': charge['disputed'] = True
    else: charge['customer'] = 'cus_Other'
    result = withdrawal.withdraw()
    assert result.disposition == 'reconciliation_required' and result.committed is True
    assert withdrawal.authority.snapshot() == before
    assert withdrawal.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None


def test_exact_replay_returns_original_fact_head_and_instant(withdrawal):
    first = withdrawal.withdraw()
    details = source.full_withdrawal_fact_details(first.fact)
    snapshot = withdrawal.authority.snapshot()
    replay = withdrawal.withdraw(now=withdrawal.withdrawal_time + timedelta(minutes=1))
    assert replay.disposition == 'admitted' and replay.fact is first.fact
    assert source.full_withdrawal_fact_details(replay.fact) == details
    assert withdrawal.authority.snapshot() == snapshot


def test_two_pass_member_order_is_canonical_not_response_order(withdrawal):
    withdrawal.prepare_withdrawal(split=(1000, 1900))
    calls = {'refunds': 0}
    def reverse_second(request):
        if request.path == '/v1/refunds':
            calls['refunds'] += 1
            if calls['refunds'] == 2:
                withdrawal.data['/v1/refunds']['data'].reverse()
    withdrawal.hook = reverse_second
    assert withdrawal.withdraw().disposition == 'admitted'
    assert calls['refunds'] == 2


def test_material_change_between_complete_passes_refuses(withdrawal):
    calls = {'refunds': 0}
    def mutate_second(request):
        if request.path == '/v1/refunds':
            calls['refunds'] += 1
            if calls['refunds'] == 2:
                withdrawal.data['/v1/refunds']['data'][0]['balance_transaction'] = 'txn_Changed'
    withdrawal.hook = mutate_second
    assert withdrawal.withdraw().disposition == 'reconciliation_required'


def test_reconciled_event_id_cannot_change_into_later_admission(withdrawal):
    before = withdrawal.authority.snapshot()
    withdrawal.data['/v1/refunds']['data'][0]['amount'] = 2899
    first = withdrawal.withdraw()
    assert first.disposition == 'reconciliation_required' and first.committed is True
    assert withdrawal.withdraw().disposition == 'reconciliation_required'

    withdrawal.data['/v1/refunds']['data'][0]['amount'] = 999
    withdrawal.event['pending_webhooks'] = 0
    changed = withdrawal.withdraw()
    assert changed.disposition == 'refused' and changed.committed is False
    assert withdrawal.authority.snapshot() == before
    assert withdrawal.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None


def test_superseded_paid_charge_trigger_records_zero_effect_reconciliation(tmp_path):
    from tests.test_w10_stripe_successful_renewal import RenewalHarness
    h = RenewalHarness(tmp_path/'ancestor-charge.db')
    try:
        assert h.ingest().disposition == 'admitted'
        ancestor_charge = copy.deepcopy(h.data['/v1/charges/ch_Synthetic'])
        h.prepare_renewal()
        assert h.renew().disposition == 'admitted'
        h.withdrawal_time = h.initial_end + timedelta(seconds=17)
        ancestor_charge.update(refunded=True,
                               amount_refunded=ancestor_charge['amount_captured'])
        h.event = dict(id='evt_AncestorFullRefund', object='event',
            type='charge.refunded', livemode=False, api_version=source.API_VERSION,
            created=int(h.withdrawal_time.timestamp()),
            data={'object': ancestor_charge})
        before = h.authority.snapshot()
        result = WithdrawalHarness.withdraw(h, now=h.withdrawal_time)
        assert result.disposition == 'reconciliation_required' and result.committed is True
        assert h.authority.snapshot() == before
        lineage, control, head = h.repo.read_lifecycle(before.instance, RECEIPT_KEY)
        assert len(lineage) == 2 and control is None and head == before.lifecycle_head
        disposition = h.repo.read_conflict(before.instance,
            event_id='evt_AncestorFullRefund', key=RECEIPT_KEY)
        assert disposition['object_key'] == 'ch_Synthetic:charge.refunded'
        assert disposition['compared_head'] == before.lifecycle_head
    finally:
        h.repo.close()


def test_withdrawal_succeeds_compatible_cancellation_and_preserves_its_lineage(tmp_path):
    from tests.test_w10_stripe_cancellation import CancellationHarness
    h = CancellationHarness(tmp_path/'cancel-then-withdraw.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_cancellation(); cancelled = h.cancel()
        cancellation_details = source.cancellation_fact_details(cancelled.fact)
        WithdrawalHarness.prepare_withdrawal(h)
        h.withdrawal_time = h.cancellation_now() + timedelta(seconds=1)
        result = WithdrawalHarness.withdraw(h, now=h.withdrawal_time)
        assert result.disposition == 'admitted'
        controls = h.repo.read_lifecycle_chain(
            h.authority.snapshot().instance, RECEIPT_KEY)[1]
        assert [item['version'] for item in controls] == [
            'reserved-scheduled-cancellation-receipt/1',
            'reserved-full-withdrawal-receipt/1']
        assert controls[0]['paid_receipt_id'] == cancellation_details['paid_receipt_id']
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
                                              now=h.withdrawal_time)
    finally:
        h.repo.close()


def test_sequence_two_current_period_charge_is_selected_receipt_first(tmp_path):
    from tests.test_w10_stripe_successful_renewal import RenewalHarness
    h = RenewalHarness(tmp_path/'renewed-withdrawal.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_renewal(); assert h.renew().disposition == 'admitted'
        WithdrawalHarness.prepare_withdrawal(h)
        h.withdrawal_time = h.initial_end + timedelta(seconds=1)
        assert WithdrawalHarness.withdraw(h, now=h.withdrawal_time).disposition == 'admitted'
        _, control, _ = h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)
        assert control['paid_sequence'] == 2 and control['charge'] == 'ch_Renewal'
    finally:
        h.repo.close()


@pytest.mark.parametrize('event_type,object_id', [
    ('refund.failed', 're_Failed'),
    ('refund.updated', 're_Updated'),
    ('charge.dispute.created', 'dp_Open'),
    ('charge.dispute.funds_withdrawn', 'dp_Withdrawn'),
    ('charge.dispute.funds_reinstated', 'dp_Reinstated'),
])
def test_unresolved_refund_dispute_reversal_and_reinstatement_labels_only_reconcile(
        withdrawal, event_type, object_id):
    before = withdrawal.authority.snapshot()
    withdrawal.event['type'] = event_type
    withdrawal.event['data']['object'] = {'id': object_id, 'object':
        ('refund' if object_id.startswith('re_') else 'dispute')}
    result = withdrawal.withdraw()
    assert result.disposition == 'reconciliation_required' and result.committed is True
    assert withdrawal.authority.snapshot() == before
    assert withdrawal.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None
