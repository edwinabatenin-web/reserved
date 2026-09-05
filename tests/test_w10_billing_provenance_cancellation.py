"""Durable cancellation control, CAS, replay and transaction outcomes."""
import json
import linecache
import sqlite3
import sys

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    ProvenanceError, ProvenanceRepository,
)
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY
from tests.test_w10_stripe_cancellation import cancellation


def test_one_domain_separated_control_advances_lifecycle_not_paid_lineage(cancellation):
    before = cancellation.repo.read_lineage(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    result = cancellation.cancel()
    assert result.disposition == 'admitted'
    lineage, control, lifecycle_head = cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert lineage == before and control['paid_head'] == before[-1][1]
    assert lifecycle_head != before[-1][1]
    assert control['service_start'] == before[-1][0]['evidence']['service_start']
    assert control['service_end'] == before[-1][0]['service_end']
    with sqlite3.connect(cancellation.repo.path) as conn:
        rows = conn.execute(
            "SELECT identity,body,mac FROM dispositions WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'"
        ).fetchall()
    assert len(rows) == 1
    stored = json.loads(rows[0][1])
    assert stored == control and len(rows[0][2]) == 64
    assert 'canceled_at' not in control and 'metadata' not in control


def test_changed_event_or_object_after_control_records_only_reconciliation(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    cancellation.event['id'] = 'evt_CompetingCancellation'
    result = cancellation.cancel()
    assert result.disposition == 'reconciliation_required'
    after = cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert after == before
    with sqlite3.connect(cancellation.repo.path) as conn:
        assert conn.execute('SELECT count(*) FROM dispositions').fetchone()[0] == 2


def test_known_rollback_allows_only_exact_reserved_retry(cancellation):
    touched = []
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository._metadata.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_cancellation.__code__):
            touched.append(True)
            raise RuntimeError('synthetic cancellation precommit failure')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = cancellation.cancel()
    finally:
        sys.settrace(prior)
    assert touched == [True]
    assert result.disposition == 'refused' and result.committed is False
    assert cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)[1] is None
    original = json.loads(source._state(cancellation.authority)['publication'][1]['material'])
    cancellation.event['id'] = 'evt_DifferentReservedCancellation'
    assert cancellation.cancel().disposition == 'refused'
    cancellation.event['id'] = original['event_id']
    retry = cancellation.cancel()
    assert retry.disposition == 'admitted' and retry.committed is True
    assert source.cancellation_fact_details(retry.fact)['exclusive_service_end'] == original['service_end']


def test_arbitrary_precommit_exception_is_unknown_and_consumes_attempt(cancellation, monkeypatch):
    def uncertain(*args, **kwargs):
        raise RuntimeError('caller cannot prove transaction outcome')
    monkeypatch.setattr(ProvenanceRepository, 'commit_cancellation', uncertain)
    result = cancellation.cancel()
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    monkeypatch.undo()
    assert cancellation.cancel().disposition == 'refused'
    assert cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)[1] is None


def test_committed_then_wrapper_exception_is_durable_and_exact_retry_publishes(
        cancellation, monkeypatch):
    original = ProvenanceRepository.commit_cancellation
    def committed_then_raise(self, *args):
        original(self, *args)
        raise RuntimeError('synthetic wrapper interruption')
    monkeypatch.setattr(ProvenanceRepository, 'commit_cancellation', committed_then_raise)
    result = cancellation.cancel()
    assert result.disposition == 'committed_but_unadmitted' and result.committed is True
    assert cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)[1] is not None
    monkeypatch.undo()
    assert cancellation.cancel().disposition == 'admitted'


def test_denied_rollback_poisons_and_closes_repository(cancellation):
    db = cancellation.repo._db
    reached = []
    def authorizer(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_TRANSACTION and first == 'ROLLBACK':
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is ProvenanceRepository.commit_cancellation.__code__
                and "self._db.execute('COMMIT')" in linecache.getline(
                    frame.f_code.co_filename, frame.f_lineno)):
            reached.append(True)
            raise RuntimeError('interrupt before cancellation commit')
        return trace
    db.set_authorizer(authorizer)
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = cancellation.cancel()
    finally:
        sys.settrace(prior)
    assert reached == [True]
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    with pytest.raises(ProvenanceError):
        cancellation.repo.read_lifecycle(cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert cancellation.cancel().disposition == 'refused'


@pytest.mark.parametrize('stage', ['before_publish', 'after_publish'])
def test_publication_failure_never_uses_uncommitted_visibility(cancellation, stage):
    touched = []
    def trace(frame, event, arg):
        if (frame.f_code.co_name == 'publish' and frame.f_code.co_filename == source.__file__
                and event == ('call' if stage == 'before_publish' else 'return')):
            touched.append(True)
            raise RuntimeError('synthetic publication interruption')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = cancellation.cancel()
    finally:
        sys.settrace(prior)
    assert touched == [True]
    assert result.disposition == 'committed_but_unadmitted' and result.committed is True
    if stage == 'before_publish':
        assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                              user_id=1, now=cancellation.cancellation_now())
        assert cancellation.cancel().disposition == 'admitted'
    else:
        assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())


def test_authority_cas_failure_after_commit_requires_exact_reconciliation(cancellation):
    original = cancellation.authority.snapshot()
    original_commit = ProvenanceRepository.commit_cancellation
    def revoke_after(self, *args):
        unit = original_commit(self, *args)
        cancellation.authority.revoke()
        return unit
    cancellation.repo.commit_cancellation = revoke_after.__get__(
        cancellation.repo, ProvenanceRepository)
    result = cancellation.cancel()
    assert result.disposition == 'committed_but_unadmitted' and result.committed is True
    assert cancellation.authority.snapshot().revision > original.revision
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())


@pytest.mark.parametrize('change', ['body', 'mac', 'extra_control', 'paid_head'])
def test_control_or_paid_head_tamper_fails_closed(cancellation, change):
    assert cancellation.cancel().disposition == 'admitted'
    with sqlite3.connect(cancellation.repo.path) as conn:
        if change == 'body':
            conn.execute("UPDATE dispositions SET body=body || ' ' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
        elif change == 'mac':
            conn.execute("UPDATE dispositions SET mac='forged' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
        elif change == 'extra_control':
            conn.execute("INSERT INTO dispositions VALUES ('paid-lineage-lifecycle-scope/2:forged','{}','forged')")
        else:
            conn.execute("UPDATE current_heads SET head='forged'")
    with pytest.raises(ProvenanceError):
        cancellation.repo.read_lifecycle(cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())


def test_control_survives_reopen_only_with_retained_authority(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    path = cancellation.repo.path
    cancellation.repo.close()
    cancellation.repo = ProvenanceRepository(path)
    assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                      user_id=1, now=cancellation.cancellation_now())
    cancellation.authority.lose()
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())
