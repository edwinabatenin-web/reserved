"""Closed synthetic source admission for one later paid period after withdrawal."""
import copy
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import ProvenanceError
from tests.test_w10_stripe_initial_payment_ingress import (
    RECEIPT_KEY, encoded, signature,
)
from tests.test_w10_stripe_successful_renewal import RenewalHarness, SUCCESSOR_ENDS
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


class RestorationHarness(RenewalHarness):
    def withdraw_initial(self):
        paid, _ = self.repo.read(self.authority.snapshot().instance, RECEIPT_KEY)
        WithdrawalHarness.prepare_withdrawal(self, split=(paid['evidence']['amount'],))
        return WithdrawalHarness.withdraw(self)

    def prepare_restoration(self, *, start=None, end=None,
                            event_id='evt_LaterRestoration'):
        self.prepare_renewal(start=start, end=end, event_id=event_id)
        charge = self.data['/v1/charges/ch_Renewal']
        charge.update(refunded=False, amount_refunded=0, disputed=False,
                      paid=True, captured=True, status='succeeded')
        self.event['type'] = 'invoice.payment_succeeded'

    def restore(self, *, now=None, raw=None, header=None, clock=None):
        now = self.initial_end - timedelta(minutes=1) if now is None else now
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_later_period_restoration(
            self.authority, self.repo, raw,
            signature(raw, now) if header is None else header,
            clock=clock or (lambda: now))


@pytest.fixture
def restoration(tmp_path):
    h = RestorationHarness(tmp_path/'restoration.db')
    assert h.ingest().disposition == 'admitted'
    assert h.withdraw_initial().disposition == 'admitted'
    h.prepare_restoration()
    yield h
    h.repo.close()


@pytest.mark.parametrize('plan', ['monthly', 'six_month', 'yearly'])
def test_exact_next_period_restores_only_at_new_access_start(tmp_path, plan):
    h = RestorationHarness(tmp_path/(plan + '.db'), plan=plan)
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(end=SUCCESSOR_ENDS[plan])
        result = h.restore()
        assert result.disposition == 'admitted' and result.committed is True
        details = source.later_period_restoration_fact_details(result.fact)
        assert details['service_start'] == h.initial_end.isoformat()
        assert details['access_start'] == h.initial_end.isoformat()
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=h.initial_end - timedelta(microseconds=1))
        assert source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=h.initial_end)
    finally:
        h.repo.close()


def test_delayed_verification_never_backfills_and_expired_purchase_refuses(restoration):
    delayed = restoration.initial_end + timedelta(days=2)
    result = restoration.restore(now=delayed)
    assert result.disposition == 'admitted'
    details = source.later_period_restoration_fact_details(result.fact)
    assert details['access_start'] == delayed.isoformat()
    assert not source.allows_paid_request(restoration.authority, restoration.repo,
        user_id=1, now=delayed - timedelta(microseconds=1))
    assert source.allows_paid_request(restoration.authority, restoration.repo,
        user_id=1, now=delayed)

    expired = RestorationHarness(
        restoration.repo.path.parent/'expired-restoration.db')
    try:
        assert expired.ingest().disposition == 'admitted'
        assert expired.withdraw_initial().disposition == 'admitted'
        expired.prepare_restoration()
        before = expired.authority.snapshot()
        result = expired.restore(now=SUCCESSOR_ENDS['monthly'])
        assert result.disposition == 'refused'
        assert result.committed is False
        after = expired.authority.snapshot()
        assert after.accepted == before.accepted
        assert after.lifecycle_head == before.lifecycle_head
        assert after.withdrawal == before.withdrawal
        assert not source.allows_paid_request(
            expired.authority, expired.repo, user_id=1, now=expired.initial_end)
    finally:
        expired.repo.close()


def test_exact_replay_preserves_fact_head_and_clock_without_refetch(restoration):
    first = restoration.restore()
    details = source.later_period_restoration_fact_details(first.fact)
    snapshot = restoration.authority.snapshot()
    restoration.hook = lambda request: (_ for _ in ()).throw(AssertionError('refetch'))
    replay = restoration.restore(
        now=restoration.initial_end + timedelta(days=1),
        clock=lambda: (_ for _ in ()).throw(AssertionError('resample')))
    assert replay.disposition == 'admitted' and replay.fact is first.fact
    assert source.later_period_restoration_fact_details(replay.fact) == details
    assert restoration.authority.snapshot() == snapshot

    refused = restoration.restore(
        header='t=1,v1=' + ('0' * 64),
        clock=lambda: (_ for _ in ()).throw(AssertionError('resample')))
    assert refused.disposition == 'refused' and refused.committed is False


@pytest.mark.parametrize('event_type', [
    'invoice.paid', 'refund.updated', 'charge.refund.updated',
    'charge.dispute.funds_reinstated',
])
def test_provider_labels_never_restore(event_type, restoration):
    before = restoration.authority.snapshot()
    restoration.event['type'] = event_type
    result = restoration.restore()
    assert result.disposition == 'refused' and result.committed is False
    assert restoration.authority.snapshot() == before


@pytest.mark.parametrize('mutation', [
    'wrong_signature', 'stale_signature', 'version', 'account', 'mode',
    'event_object', 'invoice_object', 'customer', 'subscription', 'invoice_id',
])
def test_trigger_signature_and_binding_refusals_have_zero_effect(
        restoration, mutation):
    before = restoration.authority.snapshot()
    if mutation == 'version': restoration.event['api_version'] = '2024-01-01'
    elif mutation == 'account': restoration.event['account'] = 'acct_Other'
    elif mutation == 'mode': restoration.event['livemode'] = True
    elif mutation == 'event_object': restoration.event['object'] = 'invoice'
    elif mutation == 'invoice_object':
        restoration.event['data']['object']['object'] = 'charge'
    elif mutation == 'customer':
        restoration.event['data']['object']['customer'] = 'cus_Other'
    elif mutation == 'subscription':
        restoration.event['data']['object']['parent'][
            'subscription_details']['subscription'] = 'sub_Other'
    elif mutation == 'invoice_id':
        restoration.event['data']['object']['id'] = 'in_Other'
    raw = encoded(restoration.event)
    if mutation == 'wrong_signature':
        header = 't=' + str(int(restoration.initial_end.timestamp())) + \
                 ',v1=' + ('0' * 64)
    elif mutation == 'stale_signature':
        header = signature(raw, restoration.initial_end - timedelta(minutes=7))
    else:
        header = signature(raw, restoration.initial_end)
    result = restoration.restore(raw=raw, header=header)
    assert result.disposition == 'refused' and result.committed is False
    assert restoration.authority.snapshot() == before


@pytest.mark.parametrize('mutation', [
    'invoice_amount', 'invoice_collection', 'invoice_discount',
    'line_quantity', 'line_proration', 'subscription_status',
    'item_count', 'price_amount', 'payment_amount', 'payment_type',
    'intent_status', 'intent_amount', 'charge_uncaptured', 'charge_refunded',
    'charge_disputed', 'charge_method',
])
def test_fresh_source_payment_chain_refusals_have_zero_entitlement_effect(
        restoration, mutation):
    invoice = restoration.data['/v1/invoices/in_Renewal']
    line = restoration.data['/v1/invoices/in_Renewal/lines']['data'][0]
    subscription = restoration.data['/v1/subscriptions/sub_Synthetic']
    price = restoration.data['/v1/prices/price_Synthetic']
    payment = restoration.data['/v1/invoice_payments']['data'][0]
    intent = restoration.data['/v1/payment_intents/pi_Renewal']
    charge = restoration.data['/v1/charges/ch_Renewal']
    if mutation == 'invoice_amount': invoice['amount_paid'] -= 1
    elif mutation == 'invoice_collection': invoice['collection_method'] = 'send_invoice'
    elif mutation == 'invoice_discount': invoice['discounts'] = ['di_Synthetic']
    elif mutation == 'line_quantity': line['quantity'] = 2
    elif mutation == 'line_proration':
        line['parent']['subscription_item_details']['proration'] = True
    elif mutation == 'subscription_status': subscription['status'] = 'past_due'
    elif mutation == 'item_count': subscription['items']['total_count'] = 2
    elif mutation == 'price_amount': price['unit_amount'] -= 1
    elif mutation == 'payment_amount': payment['amount_paid'] -= 1
    elif mutation == 'payment_type': payment['payment']['type'] = 'charge'
    elif mutation == 'intent_status': intent['status'] = 'requires_action'
    elif mutation == 'intent_amount': intent['amount_received'] -= 1
    elif mutation == 'charge_uncaptured': charge['captured'] = False
    elif mutation == 'charge_refunded':
        charge.update(refunded=True, amount_refunded=charge['amount'])
    elif mutation == 'charge_disputed': charge['disputed'] = True
    else: charge['payment_method_details']['type'] = 'us_bank_account'
    before = restoration.authority.snapshot()
    result = restoration.restore()
    assert result.disposition == 'reconciliation_required'
    assert result.committed is True
    after = restoration.authority.snapshot()
    assert after.accepted == before.accepted
    assert after.lifecycle_head == before.lifecycle_head
    assert after.withdrawal == before.withdrawal


@pytest.mark.parametrize('delta', [
    timedelta(seconds=-1), timedelta(seconds=1), timedelta(days=31),
])
def test_same_period_overlap_gap_and_skip_have_zero_effect(restoration, delta):
    before = restoration.authority.snapshot()
    restoration.prepare_restoration(start=restoration.initial_end + delta)
    assert restoration.restore().disposition == 'reconciliation_required'
    assert restoration.authority.snapshot() == before


def test_changed_two_pass_projection_and_unknown_field_semantics(restoration):
    calls = {'invoice': 0}
    def mutate(request):
        if request.path == '/v1/invoices/in_Renewal':
            calls['invoice'] += 1
            if calls['invoice'] == 2:
                restoration.data[request.path]['amount_paid'] -= 1
    restoration.hook = mutate
    assert restoration.restore().disposition == 'reconciliation_required'

    other = RestorationHarness(restoration.repo.path.parent/'unknown.db')
    try:
        assert other.ingest().disposition == 'admitted'
        assert other.withdraw_initial().disposition == 'admitted'
        other.prepare_restoration()
        calls = {'invoice': 0}
        def unknown(request):
            if request.path == '/v1/invoices/in_Renewal':
                calls['invoice'] += 1
                if calls['invoice'] == 2:
                    other.data[request.path]['unrelated_future_field'] = 'ignored'
        other.hook = unknown
        assert other.restore().disposition == 'admitted'
    finally:
        other.repo.close()


def test_no_sequence_three_after_restoration(restoration):
    assert restoration.restore().disposition == 'admitted'
    prior = restoration.authority.snapshot()
    restoration.event['id'] = 'evt_SequenceThree'
    raw = encoded(restoration.event)
    result = restoration.restore(raw=raw, header=signature(raw, restoration.initial_end))
    assert result.disposition in ('refused', 'reconciliation_required')
    assert restoration.authority.snapshot() == prior


def test_prior_scheduled_cancellation_is_not_overridden_by_restoration(tmp_path):
    from tests.test_w10_stripe_cancellation import CancellationHarness
    h = CancellationHarness(tmp_path/'cancel-withdraw-restore.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_cancellation()
        assert h.cancel().disposition == 'admitted'
        WithdrawalHarness.prepare_withdrawal(h)
        h.withdrawal_time = h.cancellation_now() + timedelta(seconds=1)
        assert WithdrawalHarness.withdraw(h,
            now=h.withdrawal_time).disposition == 'admitted'
        h.prepare_renewal()
        h.event['type'] = 'invoice.payment_succeeded'
        before = h.authority.snapshot()
        raw = encoded(h.event)
        result = source.ingest_later_period_restoration(
            h.authority, h.repo, raw, signature(raw, h.initial_end),
            clock=lambda: h.initial_end)
        assert result.disposition == 'refused' and result.committed is False
        assert h.authority.snapshot() == before
    finally:
        h.repo.close()


def test_changed_raw_bytes_for_admitted_event_never_reissues(restoration):
    assert restoration.restore().disposition == 'admitted'
    before = restoration.authority.snapshot()
    restoration.event['pending_webhooks'] = 0
    changed = restoration.restore()
    assert changed.disposition == 'reconciliation_required'
    assert restoration.authority.snapshot() == before


def test_source_secondary_id_reuse_refuses(restoration):
    paid, _ = restoration.repo.read_sequence(
        restoration.authority.snapshot().instance, 1, RECEIPT_KEY)
    restoration.data['/v1/invoices/in_Renewal/lines']['data'][0]['id'] = (
        paid['evidence']['line'])
    assert restoration.restore().disposition == 'reconciliation_required'


def test_tombstoned_invoice_object_cannot_admit_under_new_event_id(restoration):
    invoice = restoration.data['/v1/invoices/in_Renewal']
    invoice['amount_paid'] -= 1
    first = restoration.restore()
    assert first.disposition == 'reconciliation_required'
    invoice['amount_paid'] += 1
    first_event = restoration.event['id']
    restoration.event['id'] = 'evt_CorrectedRestoration'
    second = restoration.restore()
    assert second.disposition == 'refused' and second.committed is False
    binding = restoration.authority.snapshot().instance
    assert restoration.repo.read_conflict(
        binding, event_id=first_event, key=RECEIPT_KEY)['object_key'] == \
        'in_Renewal:invoice.payment_succeeded'
    assert restoration.repo.read_sequence(binding, 2, RECEIPT_KEY) is None
    assert not source.allows_paid_request(
        restoration.authority, restoration.repo, user_id=1,
        now=restoration.initial_end)


@pytest.mark.parametrize(
    'collision', ['event_id', 'object_key', 'neither', 'inauthentic'])
def test_transaction_rechecks_authenticated_conflicts_after_preflight(
        restoration, monkeypatch, collision):
    original = restoration.repo.read_conflicts
    inserted = []

    def insert_after_preflight(binding, *, key):
        conflicts = original(binding, key=key)
        if not inserted:
            inserted.append(True)
            restoration.repo.record_conflict(
                binding,
                event_id=(restoration.event['id'] if collision == 'event_id'
                          else 'evt_ConcurrentReconciliation'),
                raw_digest='0' * 64,
                object_key=(
                    'in_Renewal:invoice.payment_succeeded'
                    if collision == 'object_key'
                    else 'in_Unrelated:invoice.payment_succeeded'),
                key=key,
            )
            if collision == 'inauthentic':
                restoration.repo._db.execute(
                    "UPDATE dispositions SET mac='forged' "
                    "WHERE identity LIKE 'paid-lineage-conflict/2:%'")
        return conflicts

    monkeypatch.setattr(restoration.repo, 'read_conflicts',
                        insert_after_preflight)
    result = restoration.restore()
    binding = restoration.authority.snapshot().instance
    if collision == 'neither':
        assert result.disposition == 'admitted' and result.committed is True
        assert restoration.repo.read_sequence(
            binding, 2, RECEIPT_KEY)[0]['event_id'] == restoration.event['id']
    else:
        assert result.disposition == 'refused' and result.committed is False
        assert restoration.repo.read_sequence(binding, 2, RECEIPT_KEY) is None
        assert not source.allows_paid_request(
            restoration.authority, restoration.repo, user_id=1,
            now=restoration.initial_end)


def test_full_withdrawal_event_identity_cannot_be_reused_for_restoration(
        restoration):
    restoration.event['id'] = 'evt_FullWithdrawal'
    result = restoration.restore()
    assert result.disposition == 'refused' and result.committed is False
    binding = restoration.authority.snapshot().instance
    assert restoration.repo.read_sequence(binding, 2, RECEIPT_KEY) is None
    assert not source.allows_paid_request(
        restoration.authority, restoration.repo, user_id=1,
        now=restoration.initial_end)


@pytest.mark.parametrize('target,mutation', [
    ('lines', 'has_more'), ('lines', 'empty'), ('lines', 'multiple'),
    ('payments', 'has_more'), ('payments', 'empty'), ('payments', 'multiple'),
    ('items', 'has_more'), ('items', 'empty'), ('items', 'multiple'),
    ('items', 'boolean_count'), ('items', 'nondict'),
])
def test_every_required_singleton_list_shape_fails_closed(
        restoration, target, mutation):
    values = {
        'lines': restoration.data['/v1/invoices/in_Renewal/lines'],
        'payments': restoration.data['/v1/invoice_payments'],
        'items': restoration.data['/v1/subscriptions/sub_Synthetic']['items'],
    }[target]
    if mutation == 'has_more': values['has_more'] = True
    elif mutation == 'empty': values['data'] = []
    elif mutation == 'multiple': values['data'].append(copy.deepcopy(values['data'][0]))
    elif mutation == 'boolean_count': values['total_count'] = True
    else: values['data'][0] = 'not-an-object'
    assert restoration.restore().disposition == 'reconciliation_required'


@pytest.mark.parametrize('late', ['invoice', 'payment'])
def test_each_paid_instant_must_not_follow_signed_success_event(restoration, late):
    if late == 'invoice':
        transition = restoration.data['/v1/invoices/in_Renewal']['status_transitions']
    else:
        transition = restoration.data['/v1/invoice_payments']['data'][0][
            'status_transitions']
    transition['paid_at'] = restoration.event['created'] + 1
    assert restoration.restore().disposition == 'reconciliation_required'


def test_superset_injection_in_reserved_proposal_is_rejected(restoration, monkeypatch):
    before = restoration.repo.read_lifecycle_chain(
        restoration.authority.snapshot().instance, RECEIPT_KEY)
    original = restoration.repo.commit_later_period_restoration
    def inject(proposal, *args):
        proposal = dict(proposal, caller_injected_authority=True)
        return original(proposal, *args)
    monkeypatch.setattr(restoration.repo, 'commit_later_period_restoration', inject)
    result = restoration.restore()
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    with pytest.raises(ProvenanceError, match='repository unavailable'):
        restoration.repo.read_lifecycle_chain(
            restoration.authority.snapshot().instance, RECEIPT_KEY)
    inspector = source.ProvenanceRepository(restoration.repo.path)
    try:
        assert inspector.read_lifecycle_chain(
            restoration.authority.snapshot().instance, RECEIPT_KEY) == before
    finally:
        inspector.close()
