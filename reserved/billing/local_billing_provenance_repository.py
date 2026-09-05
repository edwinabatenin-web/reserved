"""Disposable exact-instant paid-lineage store, never a live authority.

Version two preserves the accepted sequence-one receipt meaning while adding one
immutable ordinary successor and one independently readable current head. There
is deliberately no v1 migration or durable RAM-authority reconstruction.
"""
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path

VERSION = 'reserved-paid-lineage-provenance/2'
_DOMAIN = b'reserved-paid-lineage-receipt/2\x00'
_TABLES = (
    'CREATE TABLE metadata (version TEXT NOT NULL, store TEXT NOT NULL)',
    'CREATE TABLE units (binding TEXT NOT NULL, sequence INTEGER NOT NULL,'
    ' event_id TEXT UNIQUE NOT NULL, object_key TEXT UNIQUE NOT NULL,'
    ' line_id TEXT UNIQUE NOT NULL, payment_id TEXT UNIQUE NOT NULL,'
    ' intent_id TEXT UNIQUE NOT NULL, charge_id TEXT UNIQUE NOT NULL,'
    ' receipt_id TEXT UNIQUE NOT NULL, fact_id TEXT UNIQUE NOT NULL,'
    ' receipt TEXT NOT NULL, mac TEXT NOT NULL, head TEXT UNIQUE NOT NULL,'
    ' PRIMARY KEY(binding, sequence), CHECK(sequence IN (1,2)))',
    'CREATE TABLE current_heads (binding TEXT PRIMARY KEY, sequence INTEGER NOT NULL,'
    ' receipt_id TEXT UNIQUE NOT NULL, fact_id TEXT UNIQUE NOT NULL, head TEXT UNIQUE NOT NULL,'
    ' CHECK(sequence IN (1,2)))',
    'CREATE TABLE dispositions (identity TEXT PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)',
)


def _schema_rows():
    tables = [('table', name, name, statement) for name, statement in (
        ('metadata', _TABLES[0]), ('units', _TABLES[1]),
        ('current_heads', _TABLES[2]), ('dispositions', _TABLES[3]))]
    indexes = [('index', 'sqlite_autoindex_units_' + str(n), 'units', None) for n in range(1, 11)]
    indexes += [('index', 'sqlite_autoindex_current_heads_' + str(n), 'current_heads', None)
                for n in range(1, 5)]
    indexes += [('index', 'sqlite_autoindex_dispositions_1', 'dispositions', None)]
    return sorted(tables + indexes)


_SCHEMA = _schema_rows()


class ProvenanceError(ValueError):
    pass


class CommitOutcomeError(ProvenanceError):
    """Repository-observed outcome, distinct from an arbitrary delegate error."""
    def __init__(self, committed):
        super().__init__('paid-lineage transaction did not publish a readable unit')
        self.committed = committed


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def identity(domain, value):
    return domain + ':' + hashlib.sha256(canonical(value)).hexdigest()


def _receipt_head(receipt):
    if receipt['sequence'] == 1:
        return identity('initial-head/1', receipt)
    return identity('paid-lineage-head/2', {
        'receipt_id': receipt['receipt_id'], 'fact_id': receipt['fact_id'],
        'predecessor_head': receipt['predecessor_head'], 'sequence': receipt['sequence'],
    })


class ProvenanceRepository:
    """Exactly one immutable two-period lineage per independent binding."""
    def __init__(self, path, *, create=False):
        if type(path) is not Path and not isinstance(path, Path):
            raise ProvenanceError('explicit local path required')
        if not path.is_absolute() or (not create and not path.is_file()):
            raise ProvenanceError('invalid explicit store')
        if create:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except OSError:
                raise ProvenanceError('exclusive store creation failed') from None
        self._lock = threading.RLock()
        self._poisoned = False
        self._closed = False
        self.path = path.resolve()
        info = self.path.stat()
        self.physical_identity = (str(self.path), info.st_dev, info.st_ino)
        self._db = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        try:
            if create:
                self._db.execute('BEGIN IMMEDIATE')
                for statement in _TABLES:
                    self._db.execute(statement)
                self._db.execute('INSERT INTO metadata VALUES (?, ?)', (VERSION, uuid.uuid4().hex))
                self._db.execute('COMMIT')
            rows = self._db.execute('SELECT version, store FROM metadata').fetchall()
            if len(rows) != 1 or rows[0][0] != VERSION or type(rows[0][1]) is not str:
                raise ProvenanceError('unsupported store')
            self.store_id = rows[0][1]
            self._metadata()
        except Exception:
            self._db.close()
            raise ProvenanceError('unsupported store') from None

    def close(self):
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True

    def _usable(self):
        if self._poisoned or self._closed:
            raise ProvenanceError('repository unavailable')

    def _metadata(self):
        self._usable()
        info = self.path.stat()
        if (str(self.path), info.st_dev, info.st_ino) != self.physical_identity:
            raise ProvenanceError('replaced physical store')
        schema = sorted(self._db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master').fetchall())
        if schema != _SCHEMA:
            raise ProvenanceError('changed schema or executable objects')
        if self._db.execute('SELECT version, store FROM metadata').fetchall() != [(VERSION, self.store_id)]:
            raise ProvenanceError('changed store')

    def empty(self):
        with self._lock:
            self._metadata()
            # Pristine eligibility never comes from this diagnostic. Preserve
            # its accepted meaning as absence of immutable receipt units.
            return self._db.execute('SELECT count(*) FROM units').fetchone()[0] == 0

    def _decode(self, binding, row, key):
        if type(key) is not bytes or len(key) < 32:
            raise ProvenanceError('invalid receipt key')
        raw = row[9].encode('ascii')
        if (len(raw) > 16384
                or not hmac.compare_digest(row[10], hmac.new(key, _DOMAIN + raw, 'sha256').hexdigest())):
            raise ProvenanceError('inauthentic receipt')
        receipt = json.loads(raw)
        if (canonical(receipt) != raw or receipt['store'] != self.store_id
                or receipt['binding'] != binding or receipt['sequence'] != row[0]):
            raise ProvenanceError('receipt scope mismatch')
        expected = (receipt['event_id'], receipt['object_key'], receipt['evidence']['line'],
                    receipt['evidence']['payment'], receipt['evidence']['intent'],
                    receipt['evidence']['charge'], receipt['receipt_id'], receipt['fact_id'])
        if tuple(row[1:9]) != expected or row[11] != _receipt_head(receipt):
            raise ProvenanceError('changed receipt identities')
        return receipt, row[11]

    def read_lineage(self, binding, key):
        """Authenticate every immutable unit and the sole current-head record."""
        with self._lock:
            self._metadata()
            rows = self._db.execute(
                'SELECT sequence,event_id,object_key,line_id,payment_id,intent_id,charge_id,'
                ' receipt_id,fact_id,receipt,mac,head FROM units WHERE binding=? ORDER BY sequence',
                (binding,)).fetchall()
            total = self._db.execute('SELECT count(*) FROM units').fetchone()[0]
            heads = self._db.execute(
                'SELECT sequence,receipt_id,fact_id,head FROM current_heads WHERE binding=?', (binding,)).fetchall()
            if total != len(rows) or len(rows) not in (0, 1, 2):
                raise ProvenanceError('ambiguous store lineage')
            if not rows:
                if heads:
                    raise ProvenanceError('detached current head')
                return ()
            if len(heads) != 1:
                raise ProvenanceError('missing or ambiguous current head')
            units = tuple(self._decode(binding, row, key) for row in rows)
            for index, (receipt, head) in enumerate(units, 1):
                if receipt['sequence'] != index:
                    raise ProvenanceError('noncontiguous lineage')
                if index == 1:
                    if any(receipt.get(name) is not None for name in
                           ('predecessor', 'predecessor_receipt_id', 'predecessor_fact_id', 'predecessor_head')):
                        raise ProvenanceError('invalid initial predecessor')
                else:
                    previous, previous_head = units[index - 2]
                    if (receipt.get('predecessor') != previous['sequence']
                            or receipt.get('predecessor_receipt_id') != previous['receipt_id']
                            or receipt.get('predecessor_fact_id') != previous['fact_id']
                            or receipt.get('predecessor_head') != previous_head
                            or receipt['service_start'] != previous['service_end']):
                        raise ProvenanceError('broken immutable lineage')
            receipt, head = units[-1]
            if heads[0] != (receipt['sequence'], receipt['receipt_id'], receipt['fact_id'], head):
                raise ProvenanceError('changed current head')
            return units

    def read(self, binding, key):
        lineage = self.read_lineage(binding, key)
        return lineage[-1] if lineage else None

    def read_sequence(self, binding, sequence, key):
        lineage = self.read_lineage(binding, key)
        if type(sequence) is not int or sequence < 1 or sequence > len(lineage):
            return None
        return lineage[sequence - 1]

    @staticmethod
    def _values(receipt, raw, mac, head):
        evidence = receipt['evidence']
        return (receipt['binding'], receipt['sequence'], receipt['event_id'], receipt['object_key'],
                evidence['line'], evidence['payment'], evidence['intent'], evidence['charge'],
                receipt['receipt_id'], receipt['fact_id'], raw.decode('ascii'), mac, head)

    def commit_initial(self, receipt, key, predecessor=None):
        with self._lock:
            self._usable()
        if type(receipt) is not dict or type(key) is not bytes or len(key) < 32:
            raise ProvenanceError('invalid receipt input')
        raw = canonical(receipt)
        if len(raw) > 16384 or receipt['store'] != self.store_id or receipt['sequence'] not in (1, 2):
            raise ProvenanceError('invalid receipt scope')
        head = _receipt_head(receipt)
        mac = hmac.new(key, _DOMAIN + raw, 'sha256').hexdigest()
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                lineage = self.read_lineage(receipt['binding'], key)
                if receipt['sequence'] == 1:
                    if predecessor is not None:
                        raise ProvenanceError('initial predecessor forbidden')
                    if lineage:
                        if lineage != ((receipt, head),):
                            raise ProvenanceError('reconciliation required')
                    else:
                        self._db.execute('INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                         self._values(receipt, raw, mac, head))
                        self._db.execute('INSERT INTO current_heads VALUES (?,?,?,?,?)',
                            (receipt['binding'], 1, receipt['receipt_id'], receipt['fact_id'], head))
                else:
                    if type(predecessor) is not tuple or len(predecessor) != 2:
                        raise ProvenanceError('exact predecessor required')
                    if len(lineage) == 2:
                        if lineage[1] != (receipt, head) or lineage[0] != predecessor:
                            raise ProvenanceError('reconciliation required')
                    else:
                        if lineage != (predecessor,):
                            raise ProvenanceError('prior-head mismatch')
                        prior_receipt, prior_head = predecessor
                        cursor = self._db.execute(
                            'UPDATE current_heads SET sequence=?,receipt_id=?,fact_id=?,head=? '
                            'WHERE binding=? AND sequence=? AND receipt_id=? AND fact_id=? AND head=?',
                            (2, receipt['receipt_id'], receipt['fact_id'], head, receipt['binding'], 1,
                             prior_receipt['receipt_id'], prior_receipt['fact_id'], prior_head))
                        if cursor.rowcount != 1:
                            raise ProvenanceError('current-head compare-and-swap failed')
                        self._db.execute('INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                         self._values(receipt, raw, mac, head))
                self._db.execute('COMMIT')
                outcome = True
                unit = self.read(receipt['binding'], key)
                if unit != (receipt, head):
                    raise ProvenanceError('committed unit unavailable')
                return unit
            except Exception:
                if outcome is not True:
                    try:
                        if self._db.in_transaction:
                            self._db.execute('ROLLBACK')
                            outcome = False
                    except Exception:
                        outcome = None
                if outcome is None:
                    self._poisoned = True
                    self.close()
                raise CommitOutcomeError(outcome) from None

    def commit_successor(self, receipt, predecessor, key):
        return self.commit_initial(receipt, key, predecessor)

    def record_conflict(self, binding, *, event_id, raw_digest, object_key, key):
        """Durable minimised reconciliation disposition; never changes the head."""
        with self._lock:
            self._usable()
            self._db.execute('BEGIN IMMEDIATE')
            try:
                unit = self.read(binding, key)
                if unit is None:
                    raise ProvenanceError('no scoped historical unit')
                body = dict(version=VERSION, store=self.store_id, binding=binding, event_id=event_id,
                            raw_digest=raw_digest, object_key=object_key, compared_head=unit[1],
                            disposition='reconciliation_required')
                raw = canonical(body)
                if len(raw) > 2048 or self._db.execute('SELECT count(*) FROM dispositions').fetchone()[0] >= 1000:
                    raise ProvenanceError('disposition bound')
                digest = identity('paid-lineage-conflict/2', body)
                mac = hmac.new(key, b'paid-lineage-conflict/2\x00' + raw, 'sha256').hexdigest()
                existing = self._db.execute('SELECT body,mac FROM dispositions WHERE identity=?', (digest,)).fetchall()
                if existing and existing != [(raw.decode('ascii'), mac)]:
                    raise ProvenanceError('changed disposition')
                if not existing:
                    self._db.execute('INSERT INTO dispositions VALUES (?,?,?)', (digest, raw.decode('ascii'), mac))
                self._db.execute('COMMIT')
            except Exception:
                try:
                    if self._db.in_transaction:
                        self._db.execute('ROLLBACK')
                except Exception:
                    self._poisoned = True
                    self.close()
                raise
