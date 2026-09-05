"""Closed signed failed-renewal shapes, replay and real paid-surface expiry."""
import copy
from datetime import datetime, timedelta, timezone
import re
import threading

import pytest

from reserved.billing import local_paid_surface_access as surfaces
from reserved.billing import local_stripe_initial_payment as source
from tests import test_w10_local_dashboard_access as dashboard
from tests import test_w10_local_paid_surface_access as old
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY, encoded, signature
from tests.test_w10_stripe_successful_renewal import RenewalHarness, SUCCESSOR_ENDS, _rename

app = old.app


class FailedRenewalHarness(RenewalHarness):
    def prepare_failure(self, shape='failed_charge', *, event_id='evt_FailedRenewal',
                        now=None):
        self.failure_shape = shape
        if '/v1/invoices/in_Synthetic' in self.data:
            self.prepare_renewal(event_id=event_id)
            suffix = 'Renewal'
        else:
            replacements = (
                ('in_Renewal', 'in_Failed'), ('il_Renewal', 'il_Failed'),
                ('inpay_Renewal', 'inpay_Failed'), ('pi_Renewal', 'pi_Failed'),
                ('ch_Renewal', 'ch_Failed'))
            current = copy.deepcopy(self.data)
            for old_id, new_id in replacements:
                current = _rename(current, old_id, new_id)
            renamed = {}
            for path, body in current.items():
                for old_id, new_id in replacements:
                    path = path.replace(old_id, new_id)
                renamed[path] = body
            self.data = renamed
            suffix = 'Failed'
            end = source._approved_period_end(self.initial_end, self.plan)
            line = self.data['/v1/invoices/in_Failed/lines']['data'][0]
            line['period'] = {'start': int(self.initial_end.timestamp()),
                              'end': int(end.timestamp())}
            subscription = self.data['/v1/subscriptions/sub_Synthetic']
            subscription['latest_invoice'] = 'in_Failed'
            subscription['items']['data'][0]['current_period_start'] = int(
                self.initial_end.timestamp())
            subscription['items']['data'][0]['current_period_end'] = int(end.timestamp())
        self.invoice_id = 'in_' + suffix
        self.intent_id = 'pi_' + suffix
        self.charge_id = 'ch_' + suffix
        invoice = self.data['/v1/invoices/' + self.invoice_id]
        amount = invoice['amount_due']
        invoice.update(status='open', attempted=True, attempt_count=1,
            paid_out_of_band=False, amount_paid=0, amount_remaining=amount,
            default_payment_method=None, default_source=None,
            status_transitions={'paid_at': None})
        subscription = self.data['/v1/subscriptions/sub_Synthetic']
        subscription.update(status='past_due', default_payment_method=None,
            default_source=None, cancel_at_period_end=False, schedule=None,
            pause_collection=None, trial_start=None, trial_end=None,
            trial_settings=None, pending_update=None, discount=None, discounts=[],
            promotion_code=None, promotion_codes=[], offer=None, offers=[],
            cancel_at=None, canceled_at=None, cancellation_details=None)
        item = subscription['items']['data'][0]
        item.update(proration=False, discount=None, discounts=[], promotion_code=None,
                    promotion_codes=[], offer=None, offers=[])
        payment = self.data['/v1/invoice_payments']['data'][0]
        payment.update(status='open', amount_paid=0, status_transitions={'paid_at': None})
        intent = self.data['/v1/payment_intents/' + self.intent_id]
        intent.update(status='requires_payment_method', amount_received=0)
        charge = self.data['/v1/charges/' + self.charge_id]
        charge.update(status='failed', paid=False, captured=False, amount_captured=0)
        if shape == 'no_payment_artifact':
            self.data['/v1/invoice_payments']['data'] = []
            self.data['/v1/invoice_payments']['total_count'] = 0
        elif shape == 'unresolved_payment_intent':
            intent['latest_charge'] = None
        elif shape != 'failed_charge':
            raise ValueError('unsupported fixture shape')
        observed = self.initial_end
        self.failure_time = now or self.initial_end + timedelta(hours=3, seconds=19)
        self.event = dict(id=event_id, object='event', type='invoice.payment_failed',
            livemode=False, api_version=source.API_VERSION,
            created=int(observed.timestamp()), data={'object': copy.deepcopy(invoice)})

    def fail(self, *, now=None, raw=None, header=None, clock=None):
        now = self.failure_time if now is None else now
        raw = encoded(self.event) if raw is None else raw
        return source.ingest_failed_renewal(self.authority, self.repo, raw,
            signature(raw, now) if header is None else header,
            clock=clock or (lambda: now))


@pytest.fixture(params=['no_payment_artifact', 'unresolved_payment_intent', 'failed_charge'])
def failed(request, tmp_path):
    value = FailedRenewalHarness(tmp_path/(request.param + '.db'))
    assert value.ingest().disposition == 'admitted'
    value.prepare_failure(request.param)
    yield value
    value.repo.close()


def test_three_closed_shapes_admit_exact_non_midnight_deadline(failed):
    result = failed.fail()
    assert result.disposition == 'admitted' and result.committed is True
    details = source.failed_renewal_fact_details(result.fact)
    assert details['artifact_shape'] == failed.failure_shape
    assert datetime.fromisoformat(details['failure_verified_at_utc']) == failed.failure_time
    assert datetime.fromisoformat(details['recovery_deadline_exclusive_at_utc']) == (
        failed.failure_time + timedelta(days=7))
    assert datetime.fromisoformat(details['failure_verified_at_utc']).time() != datetime.min.time()


@pytest.mark.parametrize('shape', ['no_payment_artifact', 'unresolved_payment_intent', 'failed_charge'])
def test_each_shape_identity_is_persisted_without_invented_artifacts(tmp_path, shape):
    h = FailedRenewalHarness(tmp_path/(shape + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure(shape)
        result = h.fail()
        _, control, _ = h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)
        assert control['artifact_shape'] == shape
        expected = {
            'no_payment_artifact': (None, None, None),
            'unresolved_payment_intent': ('inpay_Renewal', 'pi_Renewal', None),
            'failed_charge': ('inpay_Renewal', 'pi_Renewal', 'ch_Renewal'),
        }[shape]
        assert tuple(control[name] for name in ('payment', 'intent', 'charge')) == expected
        assert source.failed_renewal_fact_details(result.fact)['fact_id'] == control['fact_id']
    finally:
        h.repo.close()


@pytest.mark.parametrize('shape,mutation', [
    ('no_payment_artifact', 'missing_invoice_default'),
    ('no_payment_artifact', 'non_null_subscription_default'),
    ('unresolved_payment_intent', 'missing_latest_charge'),
    ('unresolved_payment_intent', 'requires_action'),
    ('unresolved_payment_intent', 'boolean_amount'),
    ('failed_charge', 'succeeded_charge'),
    ('failed_charge', 'captured_charge'),
    ('failed_charge', 'mixed_charge'),
])
def test_absent_null_type_status_and_mixed_shapes_reconcile_without_control(
        tmp_path, shape, mutation):
    h = FailedRenewalHarness(tmp_path/(shape + mutation + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure(shape)
        signed = h.event['data']['object']
        if mutation == 'missing_invoice_default':
            del signed['default_source']; del h.data['/v1/invoices/in_Renewal']['default_source']
        elif mutation == 'non_null_subscription_default':
            h.data['/v1/subscriptions/sub_Synthetic']['default_payment_method'] = 'pm_Other'
        elif mutation == 'missing_latest_charge':
            del h.data['/v1/payment_intents/pi_Renewal']['latest_charge']
        elif mutation == 'requires_action':
            h.data['/v1/payment_intents/pi_Renewal']['status'] = 'requires_action'
        elif mutation == 'boolean_amount':
            h.data['/v1/invoice_payments']['data'][0]['amount_paid'] = False
        elif mutation == 'succeeded_charge':
            h.data['/v1/charges/ch_Renewal']['status'] = 'succeeded'
        elif mutation == 'captured_charge':
            h.data['/v1/charges/ch_Renewal']['captured'] = True
        else:
            h.data['/v1/invoice_payments']['data'][0]['payment']['charge'] = 'ch_Renewal'
        before = h.authority.snapshot()
        result = h.fail()
        assert result.disposition == 'refused' and result.committed is False
        assert h.authority.snapshot() == before
        assert h.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None
    finally:
        h.repo.close()


@pytest.mark.parametrize('mutation', [
    'wrong_type', 'wrong_version', 'connect', 'live', 'unattempted', 'bad_count',
    'paid', 'out_of_band', 'part_paid', 'discount', 'proration', 'offer',
    'multiple_lines', 'multiple_payments', 'wrong_period', 'cancellation',
])
def test_unsupported_failure_sources_refuse_without_mutation(tmp_path, mutation):
    h = FailedRenewalHarness(tmp_path/(mutation + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        signed = h.event['data']['object']
        retrieved = h.data['/v1/invoices/in_Renewal']
        if mutation == 'wrong_type': h.event['type'] = 'invoice.finalization_failed'
        elif mutation == 'wrong_version': h.event['api_version'] = '2025-05-28.basil'
        elif mutation == 'connect': h.event['account'] = 'acct_Connected'
        elif mutation == 'live': h.event['livemode'] = True
        elif mutation == 'unattempted': signed['attempted'] = retrieved['attempted'] = False
        elif mutation == 'bad_count': signed['attempt_count'] = retrieved['attempt_count'] = True
        elif mutation == 'paid': signed['status'] = retrieved['status'] = 'paid'
        elif mutation == 'out_of_band': signed['paid_out_of_band'] = retrieved['paid_out_of_band'] = True
        elif mutation == 'part_paid': signed['amount_paid'] = retrieved['amount_paid'] = 1
        elif mutation == 'discount': h.data['/v1/invoices/in_Renewal']['discounts'] = ['di_One']
        elif mutation == 'proration': h.data['/v1/invoices/in_Renewal/lines']['data'][0]['parent']['subscription_item_details']['proration'] = True
        elif mutation == 'offer': h.data['/v1/subscriptions/sub_Synthetic']['offer'] = 'offer_One'
        elif mutation == 'multiple_lines': h.data['/v1/invoices/in_Renewal/lines']['data'] *= 2
        elif mutation == 'multiple_payments': h.data['/v1/invoice_payments']['data'] *= 2
        elif mutation == 'wrong_period': h.data['/v1/invoices/in_Renewal/lines']['data'][0]['period']['start'] += 1
        else: h.data['/v1/subscriptions/sub_Synthetic']['cancel_at_period_end'] = True
        before = h.authority.snapshot()
        assert h.fail().disposition == 'refused'
        assert h.authority.snapshot() == before
    finally:
        h.repo.close()


def test_exact_replay_preserves_fact_head_revision_and_clock_at_all_boundaries(tmp_path):
    h = FailedRenewalHarness(tmp_path/'replay.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        first = h.fail()
        details = source.failed_renewal_fact_details(first.fact)
        snapshot = h.authority.snapshot()
        lifecycle = h.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY)
        deadline = datetime.fromisoformat(details['recovery_deadline_exclusive_at_utc'])
        for when in (h.failure_time + timedelta(seconds=1),
                     deadline - timedelta(microseconds=1), deadline,
                     deadline + timedelta(microseconds=1)):
            replay = h.fail(now=when)
            assert replay.disposition == 'admitted' and replay.fact is first.fact
            assert source.failed_renewal_fact_details(replay.fact) == details
            assert h.authority.snapshot() == snapshot
            assert h.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY) == lifecycle
        assert source.allows_paid_request(h.authority, h.repo, user_id=1,
                                          now=deadline + timedelta(microseconds=1)) is False
    finally:
        h.repo.close()


def test_authorized_reopen_preserves_exact_replay_and_copied_store_refuses(tmp_path):
    from pathlib import Path
    import shutil
    from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
    h = FailedRenewalHarness(tmp_path/'physical.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        admitted = h.fail()
        details = source.failed_renewal_fact_details(admitted.fact)
        h.repo.close()
        copied = Path(tmp_path/'copy.db')
        shutil.copyfile(tmp_path/'physical.db', copied)
        h.repo = ProvenanceRepository(tmp_path/'physical.db')
        replay = h.fail(now=h.failure_time + timedelta(seconds=1))
        assert replay.disposition == 'admitted' and replay.fact is admitted.fact
        assert source.failed_renewal_fact_details(replay.fact) == details
        copied_repo = ProvenanceRepository(copied)
        try:
            assert source.ingest_failed_renewal(h.authority, copied_repo,
                encoded(h.event), signature(encoded(h.event), h.failure_time),
                clock=lambda: h.failure_time).disposition == 'refused'
        finally:
            copied_repo.close()
    finally:
        h.repo.close()


def test_actual_signed_session_access_before_and_denied_at_after_deadline(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    h = FailedRenewalHarness(tmp_path/'surface.db', uid)
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        result = h.fail()
        deadline = datetime.fromisoformat(source.failed_renewal_fact_details(
            result.fact)['recovery_deadline_exclusive_at_utc'])
        now = [h.failure_time]
        surfaces.install_local_exact_utc_paid_surface_access(
            app, authority=h.authority, repository=h.repo, clock=lambda: now[0])
        app.config['WTF_CSRF_ENABLED'] = True
        response = client.get('/v2/settings')
        assert response.status_code == 200
        assert re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        now[0] = deadline - timedelta(microseconds=1)
        assert client.get('/v2/settings').status_code == 200
        now[0] = deadline
        old.denied(client.get('/v2/settings'))
        now[0] = deadline + timedelta(microseconds=1)
        old.denied(client.get('/v2/settings'))
        assert client.get('/v2/plans').status_code == 200
    finally:
        h.repo.close()


def test_failure_after_sequence_two_uses_control_not_paid_sequence_three(tmp_path):
    h = FailedRenewalHarness(tmp_path/'after-renewal.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_renewal()
        assert h.renew().disposition == 'admitted'
        h.initial_end = SUCCESSOR_ENDS['monthly']
        h.prepare_failure(now=h.initial_end + timedelta(minutes=11))
        assert h.fail().disposition == 'admitted'
        lineage, control, head = h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)
        assert len(lineage) == 2 and control['paid_sequence'] == 2
        assert control['predecessor_lifecycle_head'] == lineage[-1][1]
        assert head != lineage[-1][1]
    finally:
        h.repo.close()


def test_concurrent_exact_proposal_has_one_control_and_one_fact(tmp_path):
    h = FailedRenewalHarness(tmp_path/'concurrent.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        barrier = threading.Barrier(2)
        results = []
        def run():
            barrier.wait()
            results.append(h.fail())
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        admitted = [result for result in results if result.disposition == 'admitted']
        assert admitted and all(result.fact is admitted[0].fact for result in admitted)
        _, control, head = h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)
        assert control is not None and head == h.authority.snapshot().lifecycle_head
    finally:
        h.repo.close()


@pytest.mark.parametrize('change', ['bytes', 'event', 'attempt'])
def test_changed_or_later_failure_reconciles_without_extending_deadline(tmp_path, change):
    h = FailedRenewalHarness(tmp_path/(change + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        first = h.fail()
        before = source.failed_renewal_fact_details(first.fact)
        snapshot = h.authority.snapshot()
        if change == 'bytes':
            h.event['pending_webhooks'] = 2
        elif change == 'event':
            h.event['id'] = 'evt_LaterFailure'
        else:
            h.event['id'] = 'evt_LaterAttempt'
            h.event['data']['object']['attempt_count'] = 2
            h.data['/v1/invoices/in_Renewal']['attempt_count'] = 2
        result = h.fail(now=h.failure_time + timedelta(days=1))
        assert result.disposition == 'reconciliation_required' and result.committed is True
        assert h.authority.snapshot() == snapshot
        assert source.failed_renewal_fact_details(first.fact) == before
    finally:
        h.repo.close()


def test_wrong_signature_wrong_store_and_early_verification_refuse(tmp_path):
    h = FailedRenewalHarness(tmp_path/'one.db')
    other = FailedRenewalHarness(tmp_path/'other.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert other.ingest().disposition == 'admitted'
        h.prepare_failure()
        raw = encoded(h.event)
        assert h.fail(header=signature(raw, h.failure_time, key=b'x' * 32)).disposition == 'refused'
        assert source.ingest_failed_renewal(h.authority, other.repo, raw,
            signature(raw, h.failure_time), clock=lambda: h.failure_time).disposition == 'refused'
        early = h.initial_end - timedelta(microseconds=1)
        h.event['created'] = int(early.timestamp())
        assert h.fail(now=early).disposition == 'refused'
    finally:
        h.repo.close(); other.repo.close()


def test_delayed_first_observation_gets_full_interval_without_backdating(tmp_path):
    h = FailedRenewalHarness(tmp_path/'delayed.db')
    try:
        assert h.ingest().disposition == 'admitted'
        delayed = h.initial_end + timedelta(days=3, hours=4, seconds=9)
        h.prepare_failure(now=delayed)
        result = h.fail()
        details = source.failed_renewal_fact_details(result.fact)
        assert datetime.fromisoformat(details['failure_verified_at_utc']) == delayed
        assert datetime.fromisoformat(details['recovery_deadline_exclusive_at_utc']) == (
            delayed + timedelta(days=7))
    finally:
        h.repo.close()


def test_changed_retrieval_between_complete_passes_refuses_before_commit(tmp_path):
    h = FailedRenewalHarness(tmp_path/'changed.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        initial_count = len(h.requests)
        def mutate(request):
            if len(h.requests) == initial_count + 8:
                h.data['/v1/invoices/in_Renewal']['attempt_count'] = 2
        h.hook = mutate
        before = h.authority.snapshot()
        assert h.fail().disposition == 'refused'
        assert h.authority.snapshot() == before
        assert h.repo.read_lifecycle(before.instance, RECEIPT_KEY)[1] is None
    finally:
        h.repo.close()


def test_failed_control_blocks_later_ordinary_success_path(tmp_path):
    h = FailedRenewalHarness(tmp_path/'success-race.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        assert h.fail().disposition == 'admitted'
        before = h.authority.snapshot()
        h.prepare_renewal()
        assert h.renew(now=h.failure_time + timedelta(days=1)).disposition != 'admitted'
        assert h.authority.snapshot() == before
    finally:
        h.repo.close()
