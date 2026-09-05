"""Sequence-two lineage, uniqueness, CAS and transaction-failure assurance."""
import copy
import linecache
import sqlite3
import sys
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import (
    ProvenanceError, ProvenanceRepository, VERSION,
)
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY
from tests.test_w10_stripe_successful_renewal import RenewalHarness, renewal


def test_exact_v2_store_and_independent_current_head(renewal):
    initial_snapshot = renewal.authority.snapshot()
    initial = renewal.repo.read_lineage(initial_snapshot.instance, RECEIPT_KEY)
    assert len(initial) == 1 and initial[0][0]['version'] == 'reserved-initial-receipt/1'
    assert renewal.renew(now=renewal.initial_end).disposition == 'admitted'
    lineage = renewal.repo.read_lineage(initial_snapshot.instance, RECEIPT_KEY)
    first, second = lineage
    assert VERSION == 'reserved-paid-lineage-provenance/5'
    assert first == initial[0] and second[0]['sequence'] == 2
    assert second[0]['predecessor_receipt_id'] == first[0]['receipt_id']
    assert second[0]['predecessor_fact_id'] == first[0]['fact_id']
    assert second[0]['predecessor_head'] == first[1]
    with sqlite3.connect(renewal.repo.path) as conn:
        assert conn.execute('SELECT sequence,receipt_id,fact_id,head FROM current_heads').fetchone() == (
            2, second[0]['receipt_id'], second[0]['fact_id'], second[1])


def test_exact_v1_metadata_is_rejected_without_migration(tmp_path):
    path = tmp_path/'v1.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE metadata (version TEXT NOT NULL, store TEXT NOT NULL)')
        conn.execute("INSERT INTO metadata VALUES ('reserved-initial-provenance/1','old-store')")
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(path)
    assert path.read_bytes() == before


def test_exact_v2_store_is_rejected_without_mutation_or_migration(tmp_path):
    from reserved.billing import local_billing_provenance_repository as repository
    path = tmp_path/'v2.db'
    with sqlite3.connect(path) as conn:
        for statement in repository._TABLES:
            conn.execute(statement)
        conn.execute("INSERT INTO metadata VALUES ('reserved-paid-lineage-provenance/2','old-v2-store')")
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(path)
    assert path.read_bytes() == before


def test_exact_v3_store_is_rejected_without_mutation_or_migration(tmp_path):
    from reserved.billing import local_billing_provenance_repository as repository
    path = tmp_path/'v3.db'
    with sqlite3.connect(path) as conn:
        for statement in repository._TABLES:
            conn.execute(statement)
        conn.execute("INSERT INTO metadata VALUES ('reserved-paid-lineage-provenance/3','old-v3-store')")
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('change', ['head_rollback', 'successor_loss', 'predecessor_loss', 'mac', 'schema'])
def test_complete_lineage_or_current_head_tamper_denies(renewal, change):
    assert renewal.renew().disposition == 'admitted'
    binding = renewal.authority.snapshot().instance
    with sqlite3.connect(renewal.repo.path) as conn:
        if change == 'head_rollback':
            first = conn.execute('SELECT receipt_id,fact_id,head FROM units WHERE sequence=1').fetchone()
            conn.execute('UPDATE current_heads SET sequence=1,receipt_id=?,fact_id=?,head=?', first)
        elif change == 'successor_loss':
            conn.execute('DELETE FROM units WHERE sequence=2')
        elif change == 'predecessor_loss':
            conn.execute('DELETE FROM units WHERE sequence=1')
        elif change == 'mac':
            conn.execute("UPDATE units SET mac='forged' WHERE sequence=1")
        else:
            conn.execute('CREATE TABLE detached_history(x)')
    with pytest.raises(ProvenanceError):
        renewal.repo.read_lineage(binding, RECEIPT_KEY)
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end)


def _reuse_secondary(harness, field):
    if field == 'event':
        harness.event['id'] = 'evt_Synthetic'
    elif field == 'invoice':
        invoice = harness.data.pop('/v1/invoices/in_Renewal')
        lines = harness.data.pop('/v1/invoices/in_Renewal/lines')
        invoice['id'] = 'in_Synthetic'
        lines['data'][0]['invoice'] = 'in_Synthetic'
        harness.data['/v1/invoices/in_Synthetic'] = invoice
        harness.data['/v1/invoices/in_Synthetic/lines'] = lines
        harness.data['/v1/subscriptions/sub_Synthetic']['latest_invoice'] = 'in_Synthetic'
        harness.data['/v1/invoice_payments']['data'][0]['invoice'] = 'in_Synthetic'
        harness.event['data']['object'] = copy.deepcopy(invoice)
    elif field == 'line':
        harness.data['/v1/invoices/in_Renewal/lines']['data'][0]['id'] = 'il_Synthetic'
    elif field == 'payment':
        harness.data['/v1/invoice_payments']['data'][0]['id'] = 'inpay_Synthetic'
    elif field == 'intent':
        intent = harness.data.pop('/v1/payment_intents/pi_Renewal')
        intent['id'] = 'pi_Synthetic'
        harness.data['/v1/payment_intents/pi_Synthetic'] = intent
        harness.data['/v1/invoice_payments']['data'][0]['payment']['payment_intent'] = 'pi_Synthetic'
        harness.data['/v1/charges/ch_Renewal']['payment_intent'] = 'pi_Synthetic'
    else:
        charge = harness.data.pop('/v1/charges/ch_Renewal')
        charge['id'] = 'ch_Synthetic'
        harness.data['/v1/charges/ch_Synthetic'] = charge
        harness.data['/v1/payment_intents/pi_Renewal']['latest_charge'] = 'ch_Synthetic'


@pytest.mark.parametrize('field', ['event', 'invoice', 'line', 'payment', 'intent', 'charge'])
def test_every_source_and_payment_object_identity_is_unique(tmp_path, field):
    h = RenewalHarness(tmp_path/(field + '.db'))
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_renewal()
        _reuse_secondary(h, field)
        before = h.repo.read_lineage(h.authority.snapshot().instance, RECEIPT_KEY)
        result = h.renew()
        assert result.disposition == 'refused' and result.fact is None
        assert h.repo.read_lineage(h.authority.snapshot().instance, RECEIPT_KEY) == before
    finally:
        h.repo.close()


def test_successor_known_rollback_retries_only_reserved_verification(renewal):
    touched = []
    def trace(frame, event, arg):
        if (event == 'call' and frame.f_code is ProvenanceRepository._metadata.__code__
                and frame.f_back.f_code is ProvenanceRepository.commit_initial.__code__):
            touched.append(True)
            raise RuntimeError('synthetic successor precommit failure')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = renewal.renew()
    finally:
        sys.settrace(prior)
    assert touched == [True]
    assert result.disposition == 'refused' and result.committed is False
    assert len(renewal.repo.read_lineage(renewal.authority.snapshot().instance, RECEIPT_KEY)) == 1
    assert renewal.renew(now=renewal.initial_end).disposition == 'admitted'
    receipt, _ = renewal.repo.read(renewal.authority.snapshot().instance, RECEIPT_KEY)
    assert receipt['verification_completed_at'] == (renewal.initial_end - timedelta(minutes=1)).isoformat()


def test_committed_successor_before_ram_cas_never_falls_back_to_predecessor(renewal):
    def trace(frame, event, arg):
        if frame.f_code.co_name == '_publish' and frame.f_code.co_filename == source.__file__ and event == 'call':
            raise RuntimeError('synthetic pre-publication interruption')
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = renewal.renew()
    finally:
        sys.settrace(prior)
    assert result.disposition == 'committed_but_unadmitted' and result.committed is True
    assert len(renewal.repo.read_lineage(renewal.authority.snapshot().instance, RECEIPT_KEY)) == 2
    assert not source.allows_paid_request(renewal.authority, renewal.repo, user_id=1,
                                          now=renewal.initial_end.replace(second=16))
    assert renewal.renew(now=renewal.initial_end).disposition == 'admitted'


def test_denied_successor_rollback_poison_closes_repository(renewal):
    db = renewal.repo._db
    inserted = []
    def authorizer(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_TRANSACTION and first == 'ROLLBACK':
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code is ProvenanceRepository.commit_initial.__code__
                and "self._db.execute('COMMIT')" in linecache.getline(frame.f_code.co_filename, frame.f_lineno)):
            inserted.append(True)
            raise RuntimeError('interrupt successor before COMMIT')
        return trace
    db.set_authorizer(authorizer)
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        result = renewal.renew()
    finally:
        sys.settrace(prior)
    assert inserted == [True]
    assert result.disposition == 'commit_outcome_unknown' and result.committed is None
    with pytest.raises(ProvenanceError):
        renewal.repo.read_lineage(renewal.authority.snapshot().instance, RECEIPT_KEY)
    assert renewal.renew().disposition == 'refused'
