"""Durable version-six later-period restoration evidence."""
import json
import shutil
import sqlite3
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    CommitOutcomeError, ProvenanceError, ProvenanceRepository, VERSION,
)
from reserved.billing import local_billing_provenance_repository as provenance
from tests.test_w10_stripe_initial_payment_ingress import (
    RECEIPT_KEY, encoded, signature,
)
from tests.test_w10_stripe_later_period_restoration import RestorationHarness


def test_v6_preserves_withdrawal_and_appends_one_domain_separated_paid_unit(tmp_path):
    h = RestorationHarness(tmp_path/'v6.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        before = h.repo.read_lifecycle_chain(h.authority.snapshot().instance,
                                             RECEIPT_KEY)
        h.prepare_restoration(); result = h.restore()
        assert result.disposition == 'admitted'
        lineage, controls, head = h.repo.read_lifecycle_chain(
            h.authority.snapshot().instance, RECEIPT_KEY)
        assert VERSION == 'reserved-paid-lineage-provenance/6'
        assert len(lineage) == 2 and controls == before[1]
        assert lineage[1][0]['version'] == 'reserved-later-period-restoration-receipt/1'
        assert lineage[1][0]['disposition'] == 'verified_later_period_restoration'
        assert lineage[1][0]['withdrawal_fact_id'] == controls[0]['fact_id']
        snapshot = h.authority.snapshot()
        assert head == lineage[1][1] == snapshot.lifecycle_head
        assert snapshot.accepted == (
            h.repo.store_id, lineage[1][0]['receipt_id'],
            lineage[1][0]['fact_id'], head)
        # The repository current head and the independently published
        # lifecycle/accepted heads identify one indivisible successor.
        assert h.repo.read_sequence(snapshot.instance, 2, RECEIPT_KEY) == lineage[1]
    finally:
        h.repo.close()


def test_v5_store_is_refused_without_migration(tmp_path):
    path = tmp_path/'old.db'
    h = RestorationHarness(path)
    h.repo.close()
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE metadata SET version='reserved-paid-lineage-provenance/5'")
    with pytest.raises(ProvenanceError, match='unsupported store'):
        ProvenanceRepository(path)


def test_exact_key_validation_rejects_proposal_and_receipt_supersets(tmp_path):
    h = RestorationHarness(tmp_path/'exact-keys.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        admitted = h.restore()
        assert admitted.disposition == 'admitted'
        receipt = h.repo.read_sequence(
            h.authority.snapshot().instance, 2, RECEIPT_KEY)[0]
        proposal = source._restoration_proposal(receipt)
        with pytest.raises(ProvenanceError,
                           match='invalid later-period restoration evidence'):
            provenance._validate_restoration_evidence(
                dict(proposal, caller_injected_authority=True))
        with pytest.raises(ProvenanceError,
                           match='invalid later-period restoration evidence'):
            provenance._validate_restoration(
                dict(receipt, caller_injected_authority=True))
    finally:
        h.repo.close()


@pytest.mark.parametrize('target', ['unit', 'control', 'head'])
def test_row_control_and_head_tamper_fail_closed(tmp_path, target):
    h = RestorationHarness(tmp_path/(target + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); assert h.restore().disposition == 'admitted'
        with sqlite3.connect(h.repo.path) as connection:
            if target == 'unit':
                connection.execute("UPDATE units SET mac='forged' WHERE sequence=2")
            elif target == 'control':
                connection.execute("UPDATE dispositions SET mac='forged' "
                    "WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
            else:
                connection.execute("UPDATE current_heads SET head='forged'")
        with pytest.raises(ProvenanceError):
            h.repo.read_lifecycle_chain(h.authority.snapshot().instance, RECEIPT_KEY)
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
                                              now=h.initial_end)
    finally:
        h.repo.close()


def test_admission_clock_samples_once_inside_commit_and_exact_replay_does_not(tmp_path):
    h = RestorationHarness(tmp_path/'clock.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        values = [h.initial_end - timedelta(minutes=1),
                  h.initial_end - timedelta(seconds=1)]
        calls = []
        def clock():
            value = values[len(calls)]
            calls.append(value)
            return value
        first = h.restore(clock=clock)
        assert first.disposition == 'admitted' and calls == values
        original = source.later_period_restoration_fact_details(first.fact)
        assert h.restore(now=h.initial_end + timedelta(days=1)).fact is first.fact
        assert source.later_period_restoration_fact_details(first.fact) == original
    finally:
        h.repo.close()


def test_commit_then_wrapper_failure_recovers_only_exact_durable_successor(
        tmp_path, monkeypatch):
    h = RestorationHarness(tmp_path/'recovery.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        original = ProvenanceRepository.commit_later_period_restoration
        def commit_then_raise(self, *args):
            original(self, *args)
            raise RuntimeError('synthetic wrapper interruption')
        monkeypatch.setattr(ProvenanceRepository,
            'commit_later_period_restoration', commit_then_raise)
        first = h.restore()
        assert first.disposition == 'committed_but_unadmitted'
        monkeypatch.undo()
        replay = h.restore()
        assert replay.disposition == 'admitted'
    finally:
        h.repo.close()


def test_pre_transaction_interruption_poison_closes_unproved_repository(
        tmp_path, monkeypatch):
    path = tmp_path/'pre-transaction-interruption.db'
    h = RestorationHarness(path)
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        binding = h.authority.snapshot().instance

        def interrupt_before_transaction(*args, **kwargs):
            raise RuntimeError('synthetic interruption before repository entry')

        monkeypatch.setattr(h.repo, 'commit_later_period_restoration',
                            interrupt_before_transaction)
        result = h.restore()
        assert result.disposition == 'commit_outcome_unknown'
        assert result.committed is None
        with pytest.raises(ProvenanceError, match='repository unavailable'):
            h.repo.read_sequence(binding, 2, RECEIPT_KEY)

        # A separate read-only handle proves that no sequence-two successor
        # reached durable state and the original withdrawal remains current.
        inspector = ProvenanceRepository(path)
        try:
            lineage, controls, lifecycle_head = inspector.read_lifecycle_chain(
                binding, RECEIPT_KEY)
            assert len(lineage) == 1
            assert len(controls) == 1
            assert controls[0]['version'] == \
                'reserved-full-withdrawal-receipt/1'
            assert lifecycle_head == provenance._control_head(controls[0])
        finally:
            inspector.close()

        # Identical retry cannot append or publish through the poisoned handle,
        # and the paid surface remains denied.
        retry = h.restore()
        assert retry.disposition == 'refused' and retry.committed is False
        assert not source.allows_paid_request(
            h.authority, h.repo, user_id=1, now=h.initial_end)
    finally:
        h.repo.close()


def test_known_rollback_retains_only_exact_retryable_reservation(
        tmp_path, monkeypatch):
    h = RestorationHarness(tmp_path/'known-rollback.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        raw = encoded(h.event)
        header = signature(raw, h.initial_end - timedelta(minutes=1))
        original = h.repo.commit_later_period_restoration
        calls = []

        def rollback_then_succeed(*args, **kwargs):
            calls.append(True)
            if len(calls) == 1:
                raise CommitOutcomeError(False)
            return original(*args, **kwargs)

        monkeypatch.setattr(h.repo, 'commit_later_period_restoration',
                            rollback_then_succeed)
        first = h.restore(raw=raw, header=header)
        assert first.disposition == 'refused' and first.committed is False
        binding = h.authority.snapshot().instance
        assert h.repo.read_conflict(
            binding, event_id=h.event['id'], key=RECEIPT_KEY) is None
        assert h.repo.read_sequence(binding, 2, RECEIPT_KEY) is None

        changed_event = dict(h.event, pending_webhooks=0)
        changed_raw = encoded(changed_event)
        changed = h.restore(raw=changed_raw,
            header=signature(changed_raw, h.initial_end - timedelta(minutes=1)))
        assert changed.disposition == 'refused' and changed.committed is False
        assert h.repo.read_conflict(
            binding, event_id=h.event['id'], key=RECEIPT_KEY) is None

        invoice = h.data['/v1/invoices/in_Renewal']
        invoice['amount_paid'] -= 1
        changed_source = h.restore(raw=raw, header=header)
        assert changed_source.disposition == 'refused'
        assert changed_source.committed is False
        invoice['amount_paid'] += 1

        retry = h.restore(raw=raw, header=header)
        assert retry.disposition == 'admitted' and retry.committed is True
        assert len(calls) == 2
    finally:
        h.repo.close()


def test_same_physical_reopen_preserves_result_but_copy_is_rejected(tmp_path):
    path = tmp_path/'reopen.db'
    h = RestorationHarness(path)
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); first = h.restore()
        copied = tmp_path/'copy.db'; shutil.copy2(path, copied)
        h.repo.close(); h.repo = ProvenanceRepository(path)
        assert h.restore(now=h.initial_end + timedelta(days=1)).fact is first.fact
        foreign = ProvenanceRepository(copied)
        try:
            assert source.ingest_later_period_restoration(h.authority, foreign,
                b'{}', '', clock=lambda: h.initial_end).disposition == 'refused'
        finally:
            foreign.close()
    finally:
        h.repo.close()


def test_failed_transaction_preserves_withdrawal_and_both_heads_atomically(tmp_path):
    h = RestorationHarness(tmp_path/'atomic.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        before_snapshot = h.authority.snapshot()
        before_chain = h.repo.read_lifecycle_chain(before_snapshot.instance,
                                                    RECEIPT_KEY)
        calls = []
        def clock():
            calls.append(True)
            if len(calls) == 1:
                return h.initial_end - timedelta(minutes=1)
            raise RuntimeError('synthetic admission-clock failure')
        result = h.restore(clock=clock)
        if result.disposition == 'admitted':
            pytest.fail('transaction unexpectedly admitted')
        assert h.repo.read_lifecycle_chain(before_snapshot.instance,
                                           RECEIPT_KEY) == before_chain
        current = h.authority.snapshot()
        assert current.accepted == before_snapshot.accepted
        assert current.lifecycle_head == before_snapshot.lifecycle_head
        assert current.withdrawal == before_snapshot.withdrawal
    finally:
        h.repo.close()
