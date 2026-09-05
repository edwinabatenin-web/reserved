"""Exact-UTC currentness across the accepted initial and successor periods."""
import copy
from datetime import timedelta
import sqlite3
import sys

import pytest

from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY
from tests.test_w10_stripe_successful_renewal import RenewalHarness, renewal


def test_pre_renewal_fact_and_admission_are_stale_after_head_revision(renewal):
    fact = source.current_fact(renewal.authority, renewal.repo, user_id=1,
                               now=renewal.initial_end - timedelta(hours=1))
    admitted = exact.admit_initial(fact, authority=renewal.authority,
                                   owner='synthetic-owner',
                                   now=renewal.initial_end - timedelta(hours=1))
    assert renewal.renew().disposition == 'admitted'
    with pytest.raises(ValueError):
        exact.admit_initial(fact, authority=renewal.authority, owner='synthetic-owner',
                            now=renewal.initial_end - timedelta(minutes=1))
    with pytest.raises(ValueError):
        exact._projection(admitted)


def test_new_fact_selects_authenticated_ancestor_then_successor(renewal):
    assert renewal.renew().disposition == 'admitted'
    before = renewal.initial_end - timedelta(microseconds=1)
    fact = source.current_fact(renewal.authority, renewal.repo, user_id=1, now=before)
    admitted = exact.admit_initial(fact, authority=renewal.authority,
                                   owner='synthetic-owner', now=before)
    assert exact._projection(admitted)[4] < renewal.initial_end
    fact = source.current_fact(renewal.authority, renewal.repo, user_id=1,
                               now=renewal.initial_end)
    admitted = exact.admit_initial(fact, authority=renewal.authority,
                                   owner='synthetic-owner', now=renewal.initial_end)
    assert exact._projection(admitted)[4] == renewal.initial_end


def test_delayed_successor_denies_exact_gap_without_backfill(renewal):
    verified = renewal.initial_end + timedelta(days=3)
    assert renewal.renew(now=verified).disposition == 'admitted'
    for when in (renewal.initial_end, renewal.initial_end + timedelta(days=2, hours=23)):
        assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1, now=when)
    assert source.allows_paid_request(renewal.authority, renewal.repo, user_id=1, now=verified)


def test_reservation_revision_stales_fact_even_after_known_rollback(renewal):
    fact = source.current_fact(renewal.authority, renewal.repo, user_id=1,
                               now=renewal.initial_end - timedelta(hours=1))
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository._metadata.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_initial.__code__):
            raise RuntimeError('known rollback')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = renewal.renew()
    finally:
        sys.settrace(prior)
    assert result.committed is False
    with pytest.raises(ValueError):
        exact.admit_initial(fact, authority=renewal.authority, owner='synthetic-owner',
                            now=renewal.initial_end - timedelta(minutes=1))


def test_revocation_and_authority_loss_deny_complete_lineage(renewal):
    assert renewal.renew().disposition == 'admitted'
    assert source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                      now=renewal.initial_end)
    renewal.authority.revoke()
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)
    assert renewal.renew().disposition == 'refused'


def test_close_reopen_requires_same_retained_authority(renewal):
    assert renewal.renew().disposition == 'admitted'
    path = renewal.repo.path
    renewal.repo.close()
    renewal.repo = ProvenanceRepository(path)
    assert source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                      now=renewal.initial_end)
    renewal.authority.lose()
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)


@pytest.mark.parametrize('operation', [copy.copy, copy.deepcopy, lambda value: object.__new__(exact.Fact)])
def test_copied_or_forged_successor_fact_denied(renewal, operation):
    fact = renewal.renew().fact
    try:
        forged = operation(fact)
    except TypeError:
        return
    with pytest.raises(ValueError):
        exact.admit_initial(forged, authority=renewal.authority,
                            owner='synthetic-owner', now=renewal.initial_end)


def test_old_head_rollback_and_authenticated_row_loss_deny(renewal):
    assert renewal.renew().disposition == 'admitted'
    with sqlite3.connect(renewal.repo.path) as conn:
        first = conn.execute('SELECT receipt_id,fact_id,head FROM units WHERE sequence=1').fetchone()
        conn.execute('UPDATE current_heads SET sequence=1,receipt_id=?,fact_id=?,head=?', first)
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)


def test_final_access_recheck_observes_authority_change(renewal, monkeypatch):
    assert renewal.renew().disposition == 'admitted'
    original = source._accepted_lineage
    calls = []
    def changing(authority, repository, snapshot):
        value = original(authority, repository, snapshot)
        calls.append(True)
        if len(calls) == 2:
            authority.revoke()
        return value
    monkeypatch.setattr(source, '_accepted_lineage', changing)
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)
    assert len(calls) >= 2
