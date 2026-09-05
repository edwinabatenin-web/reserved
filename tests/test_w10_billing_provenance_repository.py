"""Synthetic store integrity and retained-witness tests, never production data."""
import shutil
import sqlite3
import threading

import pytest
from reserved.billing.local_billing_provenance_repository import ProvenanceRepository, ProvenanceError
from reserved.billing import local_stripe_initial_payment as source
from tests.test_w10_stripe_initial_payment_ingress import Harness, NOW, RECEIPT_KEY, harness


def allowed(h):
    return source.allows_paid_request(h.authority, h.repo, user_id=1, now=NOW)


def test_close_reopen_with_retained_authority(harness):
    assert harness.ingest().disposition == 'admitted'
    path = harness.repo.path
    harness.repo.close()
    harness.repo = ProvenanceRepository(path)
    assert allowed(harness)
    harness.authority.lose()
    assert not allowed(harness)


def test_new_authority_cannot_adopt_existing_store(harness):
    assert harness.ingest().disposition == 'admitted'
    with pytest.raises(source.InitialIngressError):
        source.SyntheticInitialAuthority(**{**harness.kwargs, 'account': 'different-independent-account'})


@pytest.mark.parametrize('change', ['body', 'mac', 'head', 'missing', 'metadata'])
def test_tamper_or_missing_state_denies(harness, change):
    assert harness.ingest().disposition == 'admitted'
    sql = {'body': "UPDATE units SET receipt='{}'", 'mac': "UPDATE units SET mac='invalid'",
           'head': "UPDATE units SET head='changed'", 'missing': 'DELETE FROM units',
           'metadata': "UPDATE metadata SET store='changed'"}[change]
    with sqlite3.connect(harness.repo.path) as conn:
        conn.execute(sql)
    assert not allowed(harness)


@pytest.mark.parametrize('change', ['trigger', 'extra_table', 'missing_unique', 'duplicate_units', 'duplicate_metadata'])
def test_exact_schema_open_and_use_refuses(harness, change):
    assert harness.ingest().disposition == 'admitted'
    with sqlite3.connect(harness.repo.path) as conn:
        if change == 'trigger':
            conn.execute('CREATE TRIGGER untrusted AFTER UPDATE ON units BEGIN DELETE FROM units; END')
        elif change == 'extra_table':
            conn.execute('CREATE TABLE extra(x)')
        elif change == 'duplicate_metadata':
            conn.execute('INSERT INTO metadata SELECT * FROM metadata')
        else:
            conn.execute('ALTER TABLE units RENAME TO original_units')
            conn.execute('CREATE TABLE units AS SELECT * FROM original_units')
            if change == 'duplicate_units':
                conn.execute('INSERT INTO units SELECT * FROM original_units')
            conn.execute('DROP TABLE original_units')
    assert not allowed(harness)
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(harness.repo.path)


def test_exact_authentic_copy_is_not_a_replacement_store(harness, tmp_path):
    assert harness.ingest().disposition == 'admitted'
    copy = tmp_path / 'copy.db'
    shutil.copyfile(harness.repo.path, copy)
    other = ProvenanceRepository(copy)
    try:
        assert other.read(harness.authority.snapshot().instance, RECEIPT_KEY) is not None
        assert not source.allows_paid_request(harness.authority, other, user_id=1, now=NOW)
    finally:
        other.close()


def test_physical_replacement_under_open_handle_denies(harness, tmp_path):
    assert harness.ingest().disposition == 'admitted'
    replacement = tmp_path / 'replacement.db'
    shutil.copyfile(harness.repo.path, replacement)
    replacement.replace(harness.repo.path)
    assert not allowed(harness)


def test_wrong_receipt_key_denies(harness):
    assert harness.ingest().disposition == 'admitted'
    with pytest.raises(ProvenanceError):
        harness.repo.read(harness.authority.snapshot().instance, b'different-synthetic-receipt-key-0000')


def test_conflict_disposition_atomic_without_head_change(harness):
    assert harness.ingest().disposition == 'admitted'
    before = harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY)
    harness.event['id'] = 'evt_Another'
    assert harness.ingest().disposition == 'reconciliation_required'
    assert harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY) == before
    with sqlite3.connect(harness.repo.path) as conn:
        row = conn.execute('SELECT body FROM dispositions').fetchone()[0]
        assert 'reconciliation_required' in row and 'evt_Another' in row
        assert conn.execute('SELECT count(*) FROM units').fetchone()[0] == 1


def test_no_raw_objects_or_keys_durable(harness):
    assert harness.ingest().disposition == 'admitted'
    raw = harness.repo.path.read_bytes()
    for forbidden in (b'payment_method_details', b'billing_details', b'client_secret', RECEIPT_KEY):
        assert forbidden not in raw


def test_legacy_schema_never_migrated(tmp_path):
    path = tmp_path/'legacy.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE repository_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(path)
    assert path.read_bytes() == before


def test_creation_is_exclusive_under_race(tmp_path):
    path = tmp_path/'new.db'
    barrier = threading.Barrier(2)
    outcomes = []
    def create():
        barrier.wait()
        try:
            repo = ProvenanceRepository(path, create=True)
            outcomes.append('created')
            repo.close()
        except ProvenanceError:
            outcomes.append('refused')
    threads = [threading.Thread(target=create) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ['created', 'refused']
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM metadata').fetchone()[0] == 1


def test_incomplete_creation_metadata_not_adopted(tmp_path):
    path = tmp_path/'incomplete.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE metadata(version TEXT NOT NULL,store TEXT NOT NULL)')
    with pytest.raises(ProvenanceError):
        ProvenanceRepository(path)
