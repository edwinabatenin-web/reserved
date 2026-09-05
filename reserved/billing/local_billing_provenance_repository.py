"""Disposable exact-instant initial provenance store, not a live authority.

Receipt MAC keys are supplied independently and never stored. Authentic history
alone is intentionally insufficient for current access. No legacy migration.
"""
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path

VERSION = 'reserved-initial-provenance/1'
_DOMAIN = b'reserved-initial-receipt/1\x00'
_TABLES = (
    'CREATE TABLE metadata (version TEXT NOT NULL, store TEXT NOT NULL)',
    'CREATE TABLE units (binding TEXT PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,'
    ' object_key TEXT UNIQUE NOT NULL, receipt TEXT NOT NULL, mac TEXT NOT NULL,'
    ' head TEXT NOT NULL)',
    'CREATE TABLE dispositions (identity TEXT PRIMARY KEY, body TEXT NOT NULL, mac TEXT NOT NULL)',
)
_SCHEMA = sorted([('table', 'metadata', 'metadata', _TABLES[0]),
                  ('table', 'units', 'units', _TABLES[1]),
                  ('table', 'dispositions', 'dispositions', _TABLES[2]),
                  ('index', 'sqlite_autoindex_dispositions_1', 'dispositions', None)]
                 + [('index', 'sqlite_autoindex_units_' + str(n), 'units', None) for n in (1, 2, 3)])


class ProvenanceError(ValueError):
    pass


class CommitOutcomeError(ProvenanceError):
    """Repository-observed outcome, distinct from an arbitrary delegate error."""
    def __init__(self, committed):
        super().__init__('initial transaction did not publish a readable unit')
        self.committed = committed


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def identity(domain, value):
    return domain + ':' + hashlib.sha256(canonical(value)).hexdigest()


class ProvenanceRepository:
    """One immutable receipt/fact/head unit per independent binding.

    Public storage methods cannot issue a live fact or populate a RAM witness.
    SQLite transaction and independent RAM publication are separate domains.
    """
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
            return self._db.execute('SELECT count(*) FROM units').fetchone()[0] == 0

    def read(self, binding, key):
        with self._lock:
            self._metadata()
            rows = self._db.execute('SELECT event_id, object_key, receipt, mac, head FROM units WHERE binding=?',
                                   (binding,)).fetchall()
            if len(rows) > 1 or self._db.execute('SELECT count(*) FROM units').fetchone()[0] > 1:
                raise ProvenanceError('ambiguous store units')
            if not rows:
                return None
            row = rows[0]
            if type(key) is not bytes or len(key) < 32:
                raise ProvenanceError('invalid receipt key')
            raw = row[2].encode('ascii')
            if len(raw) > 16384 or not hmac.compare_digest(row[3], hmac.new(key, _DOMAIN + raw, 'sha256').hexdigest()):
                raise ProvenanceError('inauthentic receipt')
            receipt = json.loads(raw)
            if canonical(receipt) != raw or receipt['store'] != self.store_id or receipt['binding'] != binding:
                raise ProvenanceError('receipt scope mismatch')
            if (row[0] != receipt['event_id'] or row[1] != receipt['object_key']
                    or row[4] != identity('initial-head/1', receipt)):
                raise ProvenanceError('changed head')
            return receipt, row[4]

    def commit_initial(self, receipt, key):
        """Atomic historical receipt+fact+head; never live admission.

        Exact retries return the original unit. Collisions are refused with a
        fixed disposition, without editing an already accepted unit.
        """
        with self._lock:
            self._usable()
        if type(receipt) is not dict or type(key) is not bytes or len(key) < 32:
            raise ProvenanceError('invalid receipt input')
        raw = canonical(receipt)
        if len(raw) > 16384 or receipt['store'] != self.store_id:
            raise ProvenanceError('invalid receipt scope')
        head = identity('initial-head/1', receipt)
        mac = hmac.new(key, _DOMAIN + raw, 'sha256').hexdigest()
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                existing = self._db.execute('SELECT receipt FROM units WHERE binding=? OR event_id=? OR object_key=?',
                    (receipt['binding'], receipt['event_id'], receipt['object_key'])).fetchall()
                if existing:
                    if existing != [(raw.decode('ascii'),)]:
                        raise ProvenanceError('reconciliation required')
                else:
                    self._db.execute('INSERT INTO units VALUES (?, ?, ?, ?, ?, ?)',
                        (receipt['binding'], receipt['event_id'], receipt['object_key'], raw.decode('ascii'), mac, head))
                self._db.execute('COMMIT')
                outcome = True
                unit = self.read(receipt['binding'], key)
                if unit is None:
                    raise ProvenanceError('committed unit unavailable')
                return unit
            except Exception:
                # Empty readback is never proof of noncommit. Only a still-live
                # transaction followed by successful rollback establishes False.
                if outcome is not True:
                    try:
                        if self._db.in_transaction:
                            self._db.execute('ROLLBACK')
                            outcome = False
                    except Exception:
                        outcome = None
                if outcome is None:
                    # A connection with an unresolved transaction can see its
                    # own uncommitted unit. It can never again be an
                    # authoritative reader or publisher, even if callers later
                    # change its authorizer or attempt another rollback.
                    self._poisoned = True
                    self.close()
                raise CommitOutcomeError(outcome) from None

    def record_conflict(self, binding, *, event_id, raw_digest, object_key, key):
        """Durable minimised reconciliation disposition; never change the head."""
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
                digest = identity('initial-conflict/1', body)
                mac = hmac.new(key, b'initial-conflict/1\x00' + raw, 'sha256').hexdigest()
                existing = self._db.execute('SELECT body,mac FROM dispositions WHERE identity=?', (digest,)).fetchall()
                if existing and existing != [(raw.decode('ascii'), mac)]:
                    raise ProvenanceError('changed disposition')
                if not existing:
                    self._db.execute('INSERT INTO dispositions VALUES (?,?,?)', (digest, raw.decode('ascii'), mac))
                self._db.execute('COMMIT')
            except Exception:
                self._db.execute('ROLLBACK')
                raise
