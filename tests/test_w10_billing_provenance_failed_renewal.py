"""Shared lifecycle-head durability and failure-mode tests for failed renewal."""
import copy
from datetime import timedelta
import json
import linecache
import os
import sqlite3
import sys
import threading

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    CommitOutcomeError, ProvenanceError, ProvenanceRepository, VERSION,
)
from tests.test_w10_stripe_cancellation import CancellationHarness
from tests.test_w10_stripe_failed_renewal import FailedRenewalHarness
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY, encoded, signature


@pytest.fixture
def recovery(tmp_path):
    value = FailedRenewalHarness(tmp_path/'recovery.db')
    assert value.ingest().disposition == 'admitted'
    value.prepare_failure()
    yield value
    value.repo.close()


def test_v4_store_uses_one_tagged_control_head_without_paid_sequence_three(recovery):
    paid = recovery.repo.read_lineage(recovery.authority.snapshot().instance, RECEIPT_KEY)
    assert recovery.fail().disposition == 'admitted'
    lineage, control, lifecycle_head = recovery.repo.read_lifecycle(
        recovery.authority.snapshot().instance, RECEIPT_KEY)
    assert VERSION == 'reserved-paid-lineage-provenance/4'
    assert lineage == paid and len(lineage) == 1
    assert control['version'] == 'reserved-failed-renewal-receipt/1'
    assert control['predecessor_lifecycle_head'] == paid[-1][1]
    assert lifecycle_head.startswith('paid-lineage-failed-renewal-head/1:')
    with sqlite3.connect(recovery.repo.path) as conn:
        rows = conn.execute("SELECT identity,body,mac FROM dispositions WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'").fetchall()
        assert len(rows) == 1 and json.loads(rows[0][1]) == control and len(rows[0][2]) == 64
        assert conn.execute('SELECT count(*) FROM units').fetchone()[0] == 1


@pytest.mark.parametrize('change', ['body', 'mac', 'head', 'extra'])
def test_control_paid_head_and_ambiguity_tamper_fail_closed(recovery, change):
    assert recovery.fail().disposition == 'admitted'
    with sqlite3.connect(recovery.repo.path) as conn:
        if change == 'body':
            conn.execute("UPDATE dispositions SET body=body || ' ' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
        elif change == 'mac':
            conn.execute("UPDATE dispositions SET mac='forged' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
        elif change == 'head':
            conn.execute("UPDATE current_heads SET head='forged'")
        else:
            conn.execute("INSERT INTO dispositions VALUES ('paid-lineage-lifecycle-scope/2:forged','{}','forged')")
    with pytest.raises(ProvenanceError):
        recovery.repo.read_lifecycle(recovery.authority.snapshot().instance, RECEIPT_KEY)
    assert not source.allows_paid_request(recovery.authority, recovery.repo, user_id=1,
                                          now=recovery.failure_time)


def test_known_rollback_allows_only_exact_reserved_retry(recovery):
    touched = []
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository._metadata.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_failed_renewal.__code__):
            touched.append(True)
            raise RuntimeError('synthetic failed-renewal precommit failure')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = recovery.fail()
    finally:
        sys.settrace(prior)
    assert touched == [True]
    assert result.disposition == 'refused' and result.committed is False
    reserved = json.loads(source._state(recovery.authority)['publication'][1]['material'])
    recovery.event['id'] = 'evt_DifferentFailure'
    assert recovery.fail().disposition == 'refused'
    recovery.event['id'] = reserved['event_id']
    assert recovery.fail().disposition == 'admitted'


def test_arbitrary_commit_wrapper_error_is_unknown_and_consumes_attempt(recovery, monkeypatch):
    def uncertain(*args, **kwargs):
        raise RuntimeError('caller cannot prove transaction outcome')
    monkeypatch.setattr(ProvenanceRepository, 'commit_failed_renewal', uncertain)
    result = recovery.fail()
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    monkeypatch.undo()
    assert recovery.fail().disposition == 'refused'
    assert recovery.repo.read_lifecycle(
        recovery.authority.snapshot().instance, RECEIPT_KEY)[1] is None


def test_commit_then_wrapper_error_exact_retry_publishes_original(recovery, monkeypatch):
    original = ProvenanceRepository.commit_failed_renewal
    def committed_then_raise(self, *args):
        original(self, *args)
        raise RuntimeError('synthetic postcommit interruption')
    monkeypatch.setattr(ProvenanceRepository, 'commit_failed_renewal', committed_then_raise)
    first = recovery.fail()
    assert first.disposition == 'committed_but_unadmitted' and first.committed is True
    durable = recovery.repo.read_lifecycle(
        recovery.authority.snapshot().instance, RECEIPT_KEY)
    monkeypatch.undo()
    replay = recovery.fail()
    assert replay.disposition == 'admitted'
    assert source.failed_renewal_fact_details(replay.fact)['failure_verified_at_utc'] == (
        durable[1]['failure_verified_at_utc'])


def test_two_day_delay_inside_commit_starts_full_atomic_recovery_interval(
        recovery, monkeypatch):
    original = ProvenanceRepository.commit_failed_renewal
    timeline = {'now': recovery.failure_time}

    def delayed(self, proposal, predecessor, key, admission_clock):
        timeline['now'] += timedelta(days=2)
        return original(self, proposal, predecessor, key, admission_clock)

    monkeypatch.setattr(ProvenanceRepository, 'commit_failed_renewal', delayed)
    result = recovery.fail(clock=lambda: timeline['now'])
    assert result.disposition == 'admitted' and result.committed is True
    details = source.failed_renewal_fact_details(result.fact)
    admitted = recovery.failure_time + timedelta(days=2)
    deadline = admitted + timedelta(days=7)
    assert details['failure_verified_at_utc'] == admitted.isoformat()
    assert details['recovery_deadline_exclusive_at_utc'] == deadline.isoformat()
    assert source.allows_paid_request(
        recovery.authority, recovery.repo, user_id=1,
        now=deadline - timedelta(microseconds=1))
    assert not source.allows_paid_request(
        recovery.authority, recovery.repo, user_id=1, now=deadline)
    assert not source.allows_paid_request(
        recovery.authority, recovery.repo, user_id=1,
        now=deadline + timedelta(microseconds=1))


def test_denied_rollback_poisons_repository(recovery):
    db = recovery.repo._db
    reached = []
    def authorizer(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_TRANSACTION and first == 'ROLLBACK':
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is ProvenanceRepository.commit_failed_renewal.__code__
                and "self._db.execute('COMMIT')" in linecache.getline(
                    frame.f_code.co_filename, frame.f_lineno)):
            reached.append(True)
            raise RuntimeError('interrupt before failed-renewal commit')
        return trace
    db.set_authorizer(authorizer)
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = recovery.fail()
    finally:
        sys.settrace(prior)
    assert reached == [True]
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    with pytest.raises(ProvenanceError):
        recovery.repo.read_lifecycle(recovery.authority.snapshot().instance, RECEIPT_KEY)


def test_failed_renewal_and_cancellation_contend_for_same_head(tmp_path):
    h = FailedRenewalHarness(tmp_path/'race.db')
    try:
        assert h.ingest().disposition == 'admitted'
        paid_data = copy.deepcopy(h.data)
        h.prepare_failure()
        failure_event = encoded(h.event)
        failure_data = copy.deepcopy(h.data)
        h.data = paid_data
        CancellationHarness.prepare_cancellation(
            h, created=h.initial_end - timedelta(minutes=1))
        cancellation_event = encoded(h.event)
        failure_now = h.failure_time
        cancellation_now = h.initial_end - timedelta(minutes=1)

        # Sequential CAS reproduction is deterministic: the first control wins.
        first = source.ingest_scheduled_cancellation(h.authority, h.repo,
            cancellation_event, signature(cancellation_event, cancellation_now),
            clock=lambda: cancellation_now)
        h.data = failure_data
        second = source.ingest_failed_renewal(h.authority, h.repo, failure_event,
            signature(failure_event, failure_now), clock=lambda: failure_now)
        assert first.disposition == 'admitted'
        assert second.disposition == 'reconciliation_required'
        _, control, head = h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)
        assert control['version'] == 'reserved-scheduled-cancellation-receipt/1'
        assert head == h.authority.snapshot().lifecycle_head
    finally:
        h.repo.close()


@pytest.mark.skipif(not hasattr(os, 'fork'), reason='fork-specific authority check')
def test_forked_process_cannot_reuse_inherited_live_authority(recovery):
    assert recovery.fail().disposition == 'admitted'
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(read_fd)
            allowed = source.allows_paid_request(
                recovery.authority, recovery.repo, user_id=1, now=recovery.failure_time)
            os.write(write_fd, b'1' if allowed else b'0')
        finally:
            os._exit(0)
    os.close(write_fd)
    result = os.read(read_fd, 1)
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    assert status == 0 and result == b'0'
