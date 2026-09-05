"""Exact-UTC lifecycle currentness for scheduled cancellation."""
import copy
from datetime import timedelta
import shutil
import sqlite3

import pytest

from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    ProvenanceError, ProvenanceRepository,
)
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY
from tests.test_w10_stripe_cancellation import cancellation


def test_precontrol_paid_fact_and_admission_stale_but_fresh_fact_remains_paid(cancellation):
    now = cancellation.cancellation_now()
    fact = source.current_fact(cancellation.authority, cancellation.repo, user_id=1, now=now)
    admitted = exact.admit_initial(fact, authority=cancellation.authority,
                                   owner='synthetic-owner', now=now)
    before = exact._projection(admitted)
    result = cancellation.cancel(now=now)
    assert result.disposition == 'admitted'
    with pytest.raises(ValueError):
        exact.admit_initial(fact, authority=cancellation.authority,
                            owner='synthetic-owner', now=now)
    with pytest.raises(ValueError):
        exact._projection(admitted)
    fresh = source.current_fact(cancellation.authority, cancellation.repo, user_id=1, now=now)
    fresh_admitted = exact.admit_initial(fresh, authority=cancellation.authority,
                                         owner='synthetic-owner', now=now)
    after = exact._projection(fresh_admitted)
    assert after[4:] == before[4:] and after[2] != before[2]


def test_immediately_before_exactly_at_and_after_exclusive_end(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    _, control, _ = cancellation.repo.read_lifecycle(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    end = source.datetime.fromisoformat(control['service_end'])
    assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                      user_id=1, now=end - timedelta(microseconds=1))
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=end)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=end + timedelta(microseconds=1))


def test_canceled_at_and_source_created_never_choose_access_boundary(cancellation):
    item = cancellation.event['data']['object']['items']['data'][0]
    start = item['current_period_start']
    cancellation.event['created'] = start + 1
    cancellation.event['data']['object']['canceled_at'] = start + 2
    cancellation.data['/v1/subscriptions/sub_Synthetic']['canceled_at'] = start + 2
    when = cancellation.cancellation_now()
    result = cancellation.cancel(now=when)
    assert result.disposition == 'admitted'
    details = source.cancellation_fact_details(result.fact)
    assert details['exclusive_service_end'] == source.datetime.fromtimestamp(
        item['current_period_end'], source.timezone.utc).isoformat()
    assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                      user_id=1, now=when)


def test_forged_copied_stale_and_revoked_cancellation_handles_deny(cancellation):
    fact = cancellation.cancel().fact
    for operation in (copy.copy, copy.deepcopy,
                      lambda value: object.__new__(source.CancellationFact)):
        try:
            forged = operation(fact)
        except TypeError:
            continue
        with pytest.raises(source.InitialIngressError):
            source.cancellation_fact_details(forged)
    cancellation.authority.revoke()
    with pytest.raises(source.InitialIngressError):
        source.cancellation_fact_details(fact)


def test_authority_loss_and_wrong_membership_deny_without_altering_receipts(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    before = cancellation.repo.read_lineage(
        cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=2, now=cancellation.cancellation_now())
    cancellation.authority.lose()
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())
    assert cancellation.repo.read_lineage(before[-1][0]['binding'], RECEIPT_KEY) == before


def test_physical_store_replacement_denies_control_and_paid_access(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    path = cancellation.repo.path
    replacement = path.with_name('replacement.db')
    path.replace(replacement)
    path.write_bytes(replacement.read_bytes())
    with pytest.raises(ProvenanceError):
        cancellation.repo.read_lifecycle(cancellation.authority.snapshot().instance, RECEIPT_KEY)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())


def test_final_paid_decision_reauthenticates_lifecycle_after_fact_resolution(
        cancellation, monkeypatch):
    assert cancellation.cancel().disposition == 'admitted'
    original = source._accepted_lineage
    calls = []
    def changing(authority, repository, snapshot):
        value = original(authority, repository, snapshot)
        calls.append(True)
        if len(calls) == 2:
            authority.revoke()
        return value
    monkeypatch.setattr(source, '_accepted_lineage', changing)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=cancellation.cancellation_now())
    assert len(calls) >= 2


def test_reauthenticated_control_row_tamper_stales_existing_paid_fact(cancellation):
    assert cancellation.cancel().disposition == 'admitted'
    now = cancellation.cancellation_now()
    fact = source.current_fact(cancellation.authority, cancellation.repo, user_id=1, now=now)
    with sqlite3.connect(cancellation.repo.path) as conn:
        conn.execute("UPDATE dispositions SET mac='0' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
    with pytest.raises((ValueError, ProvenanceError)):
        exact.admit_initial(fact, authority=cancellation.authority,
                            owner='synthetic-owner', now=now)
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=now)


def test_exact_replay_rebinds_original_fact_to_authorized_same_store_reopen(
        cancellation, tmp_path):
    admitted = cancellation.cancel()
    assert admitted.disposition == 'admitted'
    original_fact = admitted.fact
    snapshot = cancellation.authority.snapshot()
    lifecycle = cancellation.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY)
    verification_time = lifecycle[1]['verification_completed_at']
    end = source.datetime.fromisoformat(lifecycle[1]['service_end'])
    copied_path = tmp_path/'copied-v3.db'
    shutil.copy2(cancellation.repo.path, copied_path)

    path = cancellation.repo.path
    cancellation.repo.close()
    cancellation.repo = ProvenanceRepository(path)
    before = cancellation.cancellation_now() + timedelta(seconds=1)
    before_replay = cancellation.cancel(now=before)
    assert before_replay.disposition == 'admitted' and before_replay.fact is original_fact
    assert cancellation.authority.snapshot() == snapshot
    assert cancellation.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY) == lifecycle
    assert source.cancellation_fact_details(original_fact)['exclusive_service_end'] == end.isoformat()
    assert source.allows_paid_request(cancellation.authority, cancellation.repo,
                                      user_id=1, now=before)

    at_replay = cancellation.cancel(now=end)
    assert at_replay.disposition == 'admitted' and at_replay.fact is original_fact
    assert cancellation.authority.snapshot() == snapshot
    assert cancellation.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY)[1][
        'verification_completed_at'] == verification_time
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=end)

    after = end + timedelta(seconds=1)
    after_replay = cancellation.cancel(now=after)
    assert after_replay.disposition == 'admitted' and after_replay.fact is original_fact
    assert cancellation.authority.snapshot() == snapshot
    assert cancellation.repo.read_lifecycle(snapshot.instance, RECEIPT_KEY) == lifecycle
    assert not source.allows_paid_request(cancellation.authority, cancellation.repo,
                                          user_id=1, now=after)

    copied = ProvenanceRepository(copied_path)
    live = cancellation.repo
    try:
        cancellation.repo = copied
        mismatch = cancellation.cancel(now=after + timedelta(seconds=1))
        assert mismatch.disposition == 'refused' and mismatch.fact is None
    finally:
        cancellation.repo = live
        copied.close()
    assert source.cancellation_fact_details(original_fact)['paid_fact_id'] == lifecycle[1]['paid_fact_id']
