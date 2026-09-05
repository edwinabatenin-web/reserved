"""Durable v5 full-withdrawal lifecycle evidence."""
import json
import sqlite3
import shutil
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    ProvenanceError, ProvenanceRepository, VERSION,
)
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY


def test_v5_stores_minimised_authenticated_terminal_control(tmp_path):
    h = WithdrawalHarness(tmp_path/'withdrawal.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(split=(1000, 1900))
        assert h.withdraw().disposition == 'admitted'
        lineage, control, head = h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)
        assert VERSION == 'reserved-paid-lineage-provenance/5'
        assert len(lineage) == 1 and control['version'] == 'reserved-full-withdrawal-receipt/1'
        assert head.startswith('paid-lineage-full-withdrawal-head/1:')
        assert control['refunds'] == ['re_1Synthetic', 're_2Synthetic']
        text = json.dumps(control)
        assert 'balance_transaction' not in text and 'signature' not in text
    finally:
        h.repo.close()


@pytest.mark.parametrize('field', ['body', 'mac'])
def test_control_tamper_fails_closed(tmp_path, field):
    h = WithdrawalHarness(tmp_path/'tamper.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(); assert h.withdraw().disposition == 'admitted'
        with sqlite3.connect(h.repo.path) as conn:
            if field == 'body':
                conn.execute("UPDATE dispositions SET body=body || ' ' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
            else:
                conn.execute("UPDATE dispositions SET mac='forged' WHERE identity LIKE 'paid-lineage-lifecycle-scope/2:%'")
        with pytest.raises(ProvenanceError):
            h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
                                              now=h.withdrawal_time)
    finally:
        h.repo.close()


def test_v4_reader_identity_is_refused_without_migration(tmp_path):
    path = tmp_path/'old.db'
    h = WithdrawalHarness(path)
    h.repo.close()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE metadata SET version='reserved-paid-lineage-provenance/4'")
    with pytest.raises(ProvenanceError, match='unsupported store'):
        ProvenanceRepository(path)


def test_admission_clock_is_sampled_once_only_after_durable_predecessor_check(tmp_path):
    h = WithdrawalHarness(tmp_path/'clock.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal()
        instants = [h.withdrawal_time, h.withdrawal_time.replace(microsecond=321)]
        calls = []
        def clock():
            value = instants[len(calls)]
            calls.append(value)
            return value
        result = h.withdraw(clock=clock)
        assert result.disposition == 'admitted' and calls == instants
        assert source.full_withdrawal_fact_details(result.fact)[
            'withdrawal_verified_at_utc'] == instants[1].isoformat()
    finally:
        h.repo.close()


def test_unknown_commit_consumes_withdrawal_authority_without_durable_control(
        tmp_path, monkeypatch):
    h = WithdrawalHarness(tmp_path/'unknown.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal()

        def unknown(*args, **kwargs):
            raise RuntimeError('caller cannot prove withdrawal transaction outcome')

        monkeypatch.setattr(ProvenanceRepository, 'commit_full_withdrawal', unknown)
        first = h.withdraw()
        assert first.disposition == 'commit_outcome_unknown' and first.committed is None
        monkeypatch.undo()
        replay = h.withdraw()
        assert replay.disposition == 'refused' and replay.committed is False
        assert h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)[1] is None
    finally:
        h.repo.close()


def test_unknown_wrapper_with_exact_durable_control_replays_original_commit(
        tmp_path, monkeypatch):
    h = WithdrawalHarness(tmp_path/'durable-unknown.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal()
        original = ProvenanceRepository.commit_full_withdrawal

        def commit_then_raise(self, *args):
            original(self, *args)
            raise RuntimeError('synthetic interruption after durable commit')

        monkeypatch.setattr(ProvenanceRepository, 'commit_full_withdrawal',
                            commit_then_raise)
        first = h.withdraw()
        assert first.disposition == 'committed_but_unadmitted' and first.committed is True
        durable = h.repo.read_lifecycle(
            h.authority.snapshot().instance, RECEIPT_KEY)
        monkeypatch.undo()
        replay = h.withdraw()
        assert replay.disposition == 'admitted'
        assert source.full_withdrawal_fact_details(replay.fact)[
            'withdrawal_verified_at_utc'] == durable[1]['withdrawal_verified_at_utc']
    finally:
        h.repo.close()


def test_reconciliation_disposition_mac_is_authenticated_before_replay(tmp_path):
    h = WithdrawalHarness(tmp_path/'conflict-mac.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal()
        h.data['/v1/refunds']['data'][0]['amount'] = 2899
        assert h.withdraw().disposition == 'reconciliation_required'
        with sqlite3.connect(h.repo.path) as connection:
            connection.execute("UPDATE dispositions SET mac='forged' "
                "WHERE identity LIKE 'paid-lineage-conflict/2:%'")
        replay = h.withdraw()
        assert replay.disposition == 'refused' and replay.committed is False
    finally:
        h.repo.close()


def test_same_physical_store_reopen_replays_but_copied_store_refuses(tmp_path):
    path = tmp_path/'reopen.db'
    h = WithdrawalHarness(path)
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(); first = h.withdraw()
        details = source.full_withdrawal_fact_details(first.fact)
        copied = tmp_path/'copied.db'
        shutil.copy2(path, copied)
        h.repo.close(); h.repo = ProvenanceRepository(path)
        replay = h.withdraw(now=h.withdrawal_time + timedelta(minutes=1))
        assert replay.disposition == 'admitted'
        assert source.full_withdrawal_fact_details(replay.fact) == details
        foreign = ProvenanceRepository(copied)
        try:
            assert source.ingest_full_withdrawal(h.authority, foreign,
                b'{}', '', clock=lambda: h.withdrawal_time).disposition == 'refused'
        finally:
            foreign.close()
    finally:
        h.repo.close()
