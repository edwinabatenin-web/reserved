"""Disposable exact-instant paid-lineage/lifecycle store, never a live authority.

Version six preserves every version-five meaning and admits one deliberately
narrow sequence-two paid successor after a sequence-one full withdrawal.  The
withdrawal stays immutable in the lifecycle chain; the new paid unit becomes
the shared lifecycle head.  There is no older-store migration, sequence three,
or durable RAM-authority reconstruction.
"""
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = 'reserved-paid-lineage-provenance/6'
_DOMAIN = b'reserved-paid-lineage-receipt/2\x00'
_CONTROL_DOMAIN = b'reserved-paid-lineage-lifecycle-control/2\x00'
_CONTROL_SCOPE = 'paid-lineage-lifecycle-scope/2:'
_CONFLICT_DOMAIN = b'paid-lineage-conflict/2\x00'
_CONFLICT_PREFIX = 'paid-lineage-conflict/2:'
_CONFLICT_FIELDS = frozenset({
    'version', 'store', 'binding', 'event_id', 'raw_digest', 'object_key',
    'compared_head', 'disposition',
})
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


def _decode_conflict(store, row, key):
    """Authenticate one bounded reconciliation row before using its event ID."""
    if (type(row) is not tuple or len(row) != 3 or type(key) is not bytes
            or len(key) < 32):
        raise ProvenanceError('invalid reconciliation row')
    row_identity, text, mac = row
    try:
        raw = text.encode('ascii')
        body = json.loads(raw)
    except (AttributeError, UnicodeError, ValueError, TypeError):
        raise ProvenanceError('invalid reconciliation row') from None
    if (type(row_identity) is not str or not row_identity.startswith(_CONFLICT_PREFIX)
            or len(raw) > 2048 or type(mac) is not str
            or not hmac.compare_digest(mac, hmac.new(key, _CONFLICT_DOMAIN + raw,
                                                     'sha256').hexdigest())
            or type(body) is not dict or set(body) != _CONFLICT_FIELDS
            or canonical(body) != raw
            or row_identity != identity('paid-lineage-conflict/2', body)
            or body.get('version') != VERSION or body.get('store') != store
            or body.get('disposition') != 'reconciliation_required'
            or any(type(body.get(name)) is not str or not body[name] for name in
                   ('binding', 'event_id', 'raw_digest', 'object_key', 'compared_head'))
            or len(body['raw_digest']) != 64
            or any(character not in '0123456789abcdef'
                   for character in body['raw_digest'])):
        raise ProvenanceError('inauthentic reconciliation row')
    return body


def _receipt_head(receipt):
    if receipt['sequence'] == 1:
        return identity('initial-head/1', receipt)
    return identity('paid-lineage-head/2', {
        'receipt_id': receipt['receipt_id'], 'fact_id': receipt['fact_id'],
        'predecessor_head': receipt['predecessor_head'], 'sequence': receipt['sequence'],
    })


def _control_scope(store, binding):
    return _CONTROL_SCOPE + hashlib.sha256(canonical((store, binding))).hexdigest()


def _control_head(receipt):
    domains = {
        'reserved-scheduled-cancellation-receipt/1': 'paid-lineage-cancellation-head/1',
        'reserved-failed-renewal-receipt/1': 'paid-lineage-failed-renewal-head/1',
        'reserved-full-withdrawal-receipt/1': 'paid-lineage-full-withdrawal-head/1',
    }
    domain = domains.get(receipt.get('version'))
    if domain is None:
        raise ProvenanceError('unsupported lifecycle control')
    return identity(domain, {
        'receipt_id': receipt['receipt_id'], 'fact_id': receipt['fact_id'],
        'predecessor_lifecycle_head': receipt['predecessor_lifecycle_head'],
        'paid_head': receipt['paid_head'],
    })


def _control_identity_domains(receipt):
    if receipt.get('version') == 'reserved-scheduled-cancellation-receipt/1':
        return 'scheduled-cancellation-receipt/1', 'scheduled-cancellation-fact/1'
    if receipt.get('version') == 'reserved-failed-renewal-receipt/1':
        return 'failed-renewal-receipt/1', 'failed-renewal-fact/1'
    if receipt.get('version') == 'reserved-full-withdrawal-receipt/1':
        return 'full-withdrawal-receipt/1', 'full-withdrawal-fact/1'
    raise ProvenanceError('unsupported lifecycle control')


_FAILED_RENEWAL_ADMISSION_FIELDS = frozenset({
    'failure_verified_at_utc', 'recovery_deadline_exclusive_at_utc',
    'receipt_id', 'fact_id',
})

_WITHDRAWAL_ADMISSION_FIELDS = frozenset({
    'withdrawal_verified_at_utc', 'receipt_id', 'fact_id',
})

_RESTORATION_ADMISSION_FIELDS = frozenset({
    'restoration_verified_at_utc', 'access_start', 'receipt_id', 'fact_id',
})


def _withdrawal_proposal(receipt):
    return {name: value for name, value in receipt.items()
            if name not in _WITHDRAWAL_ADMISSION_FIELDS}


def _validate_withdrawal_evidence(receipt):
    required = {
        'version', 'store', 'binding', 'epoch', 'binding_revision', 'owner',
        'scope', 'endpoint', 'account', 'api_version', 'livemode',
        'receipt_key_id', 'signing_key_ids', 'event_id', 'object_key',
        'raw_digest', 'source_evidence_digest', 'received_at',
        'source_created_at', 'subscription', 'customer', 'invoice', 'line',
        'payment', 'intent', 'charge', 'refunds', 'amount', 'currency',
        'paid_sequence', 'paid_receipt_id', 'paid_fact_id', 'paid_head',
        'predecessor_lifecycle_head', 'disposition', 'source_shape',
        'paid_service_start', 'paid_service_end',
    }
    if (not required <= receipt.keys()
            or receipt.get('version') != 'reserved-full-withdrawal-receipt/1'
            or receipt.get('disposition') != 'verified_full_withdrawal'
            or receipt.get('source_shape') != 'successful_full_refund'):
        raise ProvenanceError('invalid full-withdrawal control')
    identities = ('invoice', 'line', 'payment', 'intent', 'charge')
    if any(type(receipt[name]) is not str or not receipt[name] for name in identities):
        raise ProvenanceError('invalid full-withdrawal evidence identity')
    refunds = receipt['refunds']
    if (type(refunds) is not list or not 1 <= len(refunds) <= 100
            or any(type(value) is not str or not value for value in refunds)
            or len(set(refunds)) != len(refunds) or refunds != sorted(refunds)
            or type(receipt['amount']) is not int or not 0 < receipt['amount'] <= 10**12
            or type(receipt['currency']) is not str or not receipt['currency']
            or type(receipt.get('paid_sequence')) is not int
            or receipt['paid_sequence'] not in (1, 2)
            or type(receipt.get('binding_revision')) is not int
            or receipt['binding_revision'] < 1):
        raise ProvenanceError('invalid full-withdrawal evidence values')
    for name in ('raw_digest', 'source_evidence_digest'):
        value = receipt[name]
        if (type(value) is not str or len(value) != 64
                or any(character not in '0123456789abcdef' for character in value)):
            raise ProvenanceError('invalid full-withdrawal digest')
    try:
        received = datetime.fromisoformat(receipt['received_at'])
        source_created = datetime.fromisoformat(receipt['source_created_at'])
        paid_start = datetime.fromisoformat(receipt['paid_service_start'])
        paid_end = datetime.fromisoformat(receipt['paid_service_end'])
    except (TypeError, ValueError):
        raise ProvenanceError('invalid full-withdrawal instants') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (received, source_created, paid_start, paid_end))
            or source_created > received or not paid_start < paid_end):
        raise ProvenanceError('invalid full-withdrawal instant values')


def _validate_withdrawal(receipt):
    _validate_withdrawal_evidence(receipt)
    if not _WITHDRAWAL_ADMISSION_FIELDS <= receipt.keys():
        raise ProvenanceError('invalid full-withdrawal admission fields')
    try:
        verified = datetime.fromisoformat(receipt['withdrawal_verified_at_utc'])
        paid_start = datetime.fromisoformat(receipt['paid_service_start'])
        paid_end = datetime.fromisoformat(receipt['paid_service_end'])
        received = datetime.fromisoformat(receipt['received_at'])
    except (TypeError, ValueError):
        raise ProvenanceError('invalid full-withdrawal admission instant') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (verified, paid_start, paid_end, received))
            or verified < received or not paid_start <= verified < paid_end):
        raise ProvenanceError('withdrawal is not in current paid period')


def _restoration_proposal(receipt):
    return {name: value for name, value in receipt.items()
            if name not in _RESTORATION_ADMISSION_FIELDS}


def _validate_restoration_evidence(receipt):
    required = {
        'version', 'store', 'binding', 'epoch', 'binding_revision', 'owner',
        'scope', 'endpoint', 'account', 'api_version', 'livemode',
        'receipt_key_id', 'signing_key_ids', 'event_id', 'object_key',
        'raw_digest', 'source_evidence_digest', 'received_at',
        'source_created_at', 'evidence', 'service_start', 'service_end',
        'sequence', 'predecessor', 'predecessor_receipt_id',
        'predecessor_fact_id', 'predecessor_head',
        'withdrawal_receipt_id', 'withdrawal_fact_id', 'withdrawal_head',
        'predecessor_lifecycle_head', 'disposition',
    }
    accepted_keys = (required, required | _RESTORATION_ADMISSION_FIELDS)
    if (set(receipt) not in accepted_keys
            or receipt.get('version') != 'reserved-later-period-restoration-receipt/1'
            or receipt.get('disposition') != 'verified_later_period_restoration'
            or receipt.get('sequence') != 2 or receipt.get('predecessor') != 1
            or receipt.get('livemode') is not False
            or type(receipt.get('binding_revision')) is not int
            or receipt['binding_revision'] < 1):
        raise ProvenanceError('invalid later-period restoration evidence')
    for name in ('event_id', 'object_key', 'predecessor_receipt_id',
                 'predecessor_fact_id', 'predecessor_head',
                 'withdrawal_receipt_id', 'withdrawal_fact_id',
                 'withdrawal_head', 'predecessor_lifecycle_head'):
        if type(receipt.get(name)) is not str or not receipt[name]:
            raise ProvenanceError('invalid later-period restoration identity')
    for name in ('raw_digest', 'source_evidence_digest'):
        value = receipt.get(name)
        if (type(value) is not str or len(value) != 64
                or any(character not in '0123456789abcdef' for character in value)):
            raise ProvenanceError('invalid later-period restoration digest')
    evidence = receipt.get('evidence')
    evidence_keys = {
        'invoice', 'line', 'payment', 'intent', 'charge', 'amount', 'currency',
        'service_start', 'service_end', 'plan', 'price', 'item',
        'invoice_paid_at', 'payment_paid_at',
    }
    if type(evidence) is not dict or set(evidence) != evidence_keys:
        raise ProvenanceError('invalid later-period restoration source evidence')
    for name in ('invoice', 'line', 'payment', 'intent', 'charge'):
        if type(evidence.get(name)) is not str or not evidence[name]:
            raise ProvenanceError('invalid later-period restoration source identity')
    if (evidence.get('currency') != 'gbp'
            or type(evidence.get('amount')) is not int
            or evidence['amount'] <= 0
            or evidence.get('service_start') != receipt.get('service_start')
            or evidence.get('service_end') != receipt.get('service_end')):
        raise ProvenanceError('invalid later-period restoration source values')
    try:
        received = datetime.fromisoformat(receipt['received_at'])
        created = datetime.fromisoformat(receipt['source_created_at'])
        start = datetime.fromisoformat(receipt['service_start'])
        end = datetime.fromisoformat(receipt['service_end'])
        invoice_paid = datetime.fromisoformat(evidence['invoice_paid_at'])
        payment_paid = datetime.fromisoformat(evidence['payment_paid_at'])
    except (KeyError, TypeError, ValueError):
        raise ProvenanceError('invalid later-period restoration instants') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (received, created, start, end, invoice_paid, payment_paid))
            or created > received or not start < end
            or invoice_paid > created or payment_paid > created):
        raise ProvenanceError('invalid later-period restoration instant values')


def _validate_restoration(receipt):
    _validate_restoration_evidence(receipt)
    if not _RESTORATION_ADMISSION_FIELDS <= receipt.keys():
        raise ProvenanceError('invalid later-period restoration admission fields')
    try:
        verified = datetime.fromisoformat(receipt['restoration_verified_at_utc'])
        access = datetime.fromisoformat(receipt['access_start'])
        start = datetime.fromisoformat(receipt['service_start'])
        end = datetime.fromisoformat(receipt['service_end'])
        received = datetime.fromisoformat(receipt['received_at'])
    except (TypeError, ValueError):
        raise ProvenanceError('invalid later-period restoration admission instant') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (verified, access, start, end, received))
            or verified < received or access != max(start, verified)
            or not access < end):
        raise ProvenanceError('invalid later-period restoration admission values')


def _failed_renewal_proposal(receipt):
    """Return the source-owned material that precedes atomic admission."""
    return {name: value for name, value in receipt.items()
            if name not in _FAILED_RENEWAL_ADMISSION_FIELDS}


def _validate_failed_renewal_evidence(receipt):
    """Validate source-owned optional-artifact material before clock admission."""
    required = {
        'artifact_shape', 'invoice', 'line', 'payment', 'intent', 'charge',
        'failed_service_start', 'failed_service_end', 'source_evidence_digest',
        'disposition',
    }
    if not required <= receipt.keys() or receipt.get('disposition') != 'verified_renewal_failure':
        raise ProvenanceError('invalid failed-renewal control')
    values = tuple(receipt[name] for name in ('invoice', 'line'))
    if any(type(value) is not str or not value for value in values):
        raise ProvenanceError('invalid failed-renewal evidence identity')
    try:
        failed_start = datetime.fromisoformat(receipt['failed_service_start'])
        failed_end = datetime.fromisoformat(receipt['failed_service_end'])
    except (TypeError, ValueError):
        raise ProvenanceError('invalid failed-renewal instants') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (failed_start, failed_end)) or not failed_start < failed_end
            or type(receipt.get('paid_sequence')) is not int
            or receipt['paid_sequence'] not in (1, 2)
            or type(receipt.get('binding_revision')) is not int
            or receipt['binding_revision'] < 1
            or type(receipt['source_evidence_digest']) is not str
            or len(receipt['source_evidence_digest']) != 64
            or any(character not in '0123456789abcdef'
                   for character in receipt['source_evidence_digest'])):
        raise ProvenanceError('invalid failed-renewal control values')
    artifacts = tuple(receipt[name] for name in ('payment', 'intent', 'charge'))
    shape = receipt['artifact_shape']
    if shape == 'no_payment_artifact':
        if artifacts != (None, None, None):
            raise ProvenanceError('failed-renewal artifact shape mismatch')
    elif shape == 'unresolved_payment_intent':
        if (any(type(value) is not str or not value for value in artifacts[:2])
                or artifacts[2] is not None):
            raise ProvenanceError('failed-renewal artifact shape mismatch')
    elif shape == 'failed_charge':
        if any(type(value) is not str or not value for value in artifacts):
            raise ProvenanceError('failed-renewal artifact shape mismatch')
    else:
        raise ProvenanceError('unsupported failed-renewal artifact shape')


def _validate_failed_renewal(receipt):
    """Validate the final durable control, including its admission instant."""
    _validate_failed_renewal_evidence(receipt)
    if not _FAILED_RENEWAL_ADMISSION_FIELDS <= receipt.keys():
        raise ProvenanceError('invalid failed-renewal admission fields')
    try:
        verified = datetime.fromisoformat(receipt['failure_verified_at_utc'])
        deadline = datetime.fromisoformat(receipt['recovery_deadline_exclusive_at_utc'])
        received = datetime.fromisoformat(receipt['received_at'])
        failed_start = datetime.fromisoformat(receipt['failed_service_start'])
    except (TypeError, ValueError):
        raise ProvenanceError('invalid failed-renewal admission instants') from None
    if (any(type(value) is not datetime or value.tzinfo is not timezone.utc
            for value in (verified, deadline, received, failed_start))
            or verified < received or verified < failed_start
            or deadline != verified + timedelta(days=7)):
        raise ProvenanceError('invalid failed-renewal admission values')


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

    def _poison_unproven_outcome(self):
        """Permanently refuse this handle after an unprovable commit outcome."""
        with self._lock:
            self._poisoned = True
            self.close()

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
        if receipt.get('version') == 'reserved-later-period-restoration-receipt/1':
            _validate_restoration(receipt)
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

    def read_lifecycle(self, binding, key):
        """Authenticate the paid lineage and its optional immutable control head."""
        lineage, controls, lifecycle_head = self.read_lifecycle_chain(binding, key)
        return lineage, (controls[-1] if controls else None), lifecycle_head

    def read_lifecycle_chain(self, binding, key):
        """Authenticate the complete bounded lifecycle-control chain."""
        with self._lock:
            self._metadata()
            lineage = self.read_lineage(binding, key)
            if not lineage:
                return (), (), None
            scope = _control_scope(self.store_id, binding)
            rows = self._db.execute(
                'SELECT identity,body,mac FROM dispositions WHERE identity LIKE ?',
                (scope + '%',)).fetchall()
            foreign = self._db.execute(
                'SELECT count(*) FROM dispositions WHERE identity LIKE ? AND identity NOT LIKE ?',
                (_CONTROL_SCOPE + '%', scope + '%')).fetchone()[0]
            if foreign:
                raise ProvenanceError('ambiguous lifecycle control')
            if not rows:
                return lineage, (), lineage[-1][1]
            if len(rows) not in (1, 2):
                raise ProvenanceError('ambiguous lifecycle control')
            decoded = []
            for row_identity, body, stored_mac in rows:
                raw = body.encode('ascii')
                if (len(raw) > 16384 or not hmac.compare_digest(
                        stored_mac, hmac.new(key, _CONTROL_DOMAIN + raw, 'sha256').hexdigest())):
                    raise ProvenanceError('inauthentic lifecycle control')
                receipt = json.loads(raw)
                try:
                    receipt_domain, fact_domain = _control_identity_domains(receipt)
                    if receipt.get('version') == 'reserved-failed-renewal-receipt/1':
                        _validate_failed_renewal(receipt)
                    elif receipt.get('version') == 'reserved-full-withdrawal-receipt/1':
                        _validate_withdrawal(receipt)
                except ProvenanceError:
                    raise ProvenanceError('lifecycle control scope mismatch') from None
                material = {key: value for key, value in receipt.items()
                            if key not in ('receipt_id', 'fact_id')}
                paid_sequence = receipt.get('paid_sequence')
                paid_unit = next((item for item in lineage
                                  if item[0].get('sequence') == paid_sequence), None)
                if paid_unit is None:
                    raise ProvenanceError('lifecycle control scope mismatch')
                paid, paid_head = paid_unit
                if (canonical(receipt) != raw
                        or receipt.get('store') != self.store_id
                        or receipt.get('binding') != binding
                        or receipt.get('paid_receipt_id') != paid['receipt_id']
                        or receipt.get('paid_fact_id') != paid['fact_id']
                        or receipt.get('paid_head') != paid_head
                        or receipt.get('paid_sequence') != paid['sequence']
                        or receipt.get('receipt_id') != identity(receipt_domain, material)
                        or receipt.get('fact_id') != identity(fact_domain, material)):
                    raise ProvenanceError('lifecycle control scope mismatch')
                decoded.append((receipt, _control_head(receipt), row_identity))
            first = next((item for item in decoded if
                          item[0].get('predecessor_lifecycle_head') == paid_head), None)
            if first is None or first[2] != scope:
                raise ProvenanceError('lifecycle control scope mismatch')
            chain = [first]
            if len(decoded) == 2:
                second = next((item for item in decoded if item is not first), None)
                if (second is None
                        or second[0].get('version') != 'reserved-full-withdrawal-receipt/1'
                        or first[0].get('version') != 'reserved-scheduled-cancellation-receipt/1'
                        or second[0].get('predecessor_lifecycle_head') != first[1]
                        or second[2] != scope + ':' + hashlib.sha256(
                            second[0]['predecessor_lifecycle_head'].encode('ascii')).hexdigest()):
                    raise ProvenanceError('broken lifecycle-control chain')
                chain.append(second)
            if len(chain) != len(decoded):
                raise ProvenanceError('ambiguous lifecycle control')
            controls = tuple(item[0] for item in chain)
            current_paid, current_paid_head = lineage[-1]
            if current_paid.get('version') == 'reserved-later-period-restoration-receipt/1':
                if (len(lineage) != 2 or len(chain) != 1
                        or chain[0][0].get('version') !=
                            'reserved-full-withdrawal-receipt/1'
                        or current_paid.get('withdrawal_receipt_id') !=
                            chain[0][0].get('receipt_id')
                        or current_paid.get('withdrawal_fact_id') !=
                            chain[0][0].get('fact_id')
                        or current_paid.get('withdrawal_head') != chain[0][1]
                        or current_paid.get('predecessor_lifecycle_head') != chain[0][1]
                        or current_paid.get('predecessor_head') != lineage[0][1]):
                    raise ProvenanceError('broken later-period restoration lineage')
                return lineage, controls, current_paid_head
            if chain[-1][0].get('paid_sequence') != current_paid.get('sequence'):
                raise ProvenanceError('obsolete lifecycle control without restoration')
            return lineage, controls, chain[-1][1]

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
                        if self._db.execute(
                                'SELECT count(*) FROM dispositions WHERE identity LIKE ?',
                                (_CONTROL_SCOPE + '%',)).fetchone()[0] != 0:
                            raise ProvenanceError('lifecycle-head compare-and-swap failed')
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

    def commit_later_period_restoration(self, proposal, predecessor, key,
                                        admission_clock):
        """Atomically append the one supported paid successor to a withdrawal.

        ``predecessor`` is ``(paid_unit, withdrawal_receipt, withdrawal_head)``.
        Exact replay returns the original durable unit without sampling time.
        """
        with self._lock:
            self._usable()
        if (type(proposal) is not dict or type(predecessor) is not tuple
                or len(predecessor) != 3 or type(predecessor[0]) is not tuple
                or len(predecessor[0]) != 2 or type(predecessor[1]) is not dict
                or type(predecessor[2]) is not str
                or type(key) is not bytes or len(key) < 32
                or not callable(admission_clock)
                or any(name in proposal for name in _RESTORATION_ADMISSION_FIELDS)):
            raise ProvenanceError('invalid later-period restoration proposal')
        _validate_restoration_evidence(proposal)
        paid_unit, withdrawal, withdrawal_head = predecessor
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                conflicts = tuple(item for item in self._conflicts(key)
                                  if item['binding'] == proposal['binding'])
                if any(item['event_id'] == proposal['event_id']
                       or item['object_key'] == proposal['object_key']
                       for item in conflicts):
                    raise ProvenanceError('consumed reconciliation identity')
                lineage, controls, lifecycle_head = self.read_lifecycle_chain(
                    proposal['binding'], key)
                if len(lineage) == 2:
                    receipt, head = lineage[-1]
                    if (_restoration_proposal(receipt) != proposal
                            or lineage[0] != paid_unit
                            or controls != (withdrawal,)):
                        raise ProvenanceError('reconciliation required')
                else:
                    if (lineage != (paid_unit,) or controls != (withdrawal,)
                            or lifecycle_head != withdrawal_head
                            or withdrawal.get('version') !=
                                'reserved-full-withdrawal-receipt/1'
                            or withdrawal.get('paid_sequence') != 1
                            or proposal.get('store') != self.store_id
                            or proposal.get('predecessor_receipt_id') !=
                                paid_unit[0]['receipt_id']
                            or proposal.get('predecessor_fact_id') != paid_unit[0]['fact_id']
                            or proposal.get('predecessor_head') != paid_unit[1]
                            or proposal.get('withdrawal_receipt_id') !=
                                withdrawal['receipt_id']
                            or proposal.get('withdrawal_fact_id') != withdrawal['fact_id']
                            or proposal.get('withdrawal_head') != withdrawal_head
                            or proposal.get('predecessor_lifecycle_head') != withdrawal_head):
                        raise ProvenanceError('lifecycle-head compare-and-swap failed')
                    verified = admission_clock()
                    if (type(verified) is not datetime
                            or verified.tzinfo is not timezone.utc
                            or verified.utcoffset() != timedelta(0)):
                        raise ProvenanceError('invalid later-period restoration clock')
                    receipt = dict(proposal)
                    receipt['restoration_verified_at_utc'] = verified.isoformat()
                    start = datetime.fromisoformat(receipt['service_start'])
                    receipt['access_start'] = max(start, verified).isoformat()
                    material = dict(receipt)
                    receipt['fact_id'] = identity(
                        'later-period-restoration-fact/1', material)
                    receipt['receipt_id'] = identity(
                        'later-period-restoration-receipt/1', material)
                    _validate_restoration(receipt)
                    raw = canonical(receipt)
                    if len(raw) > 16384:
                        raise ProvenanceError('oversized later-period restoration')
                    head = _receipt_head(receipt)
                    mac = hmac.new(key, _DOMAIN + raw, 'sha256').hexdigest()
                    prior, prior_head = paid_unit
                    cursor = self._db.execute(
                        'UPDATE current_heads SET sequence=?,receipt_id=?,fact_id=?,head=? '
                        'WHERE binding=? AND sequence=? AND receipt_id=? AND fact_id=? AND head=?',
                        (2, receipt['receipt_id'], receipt['fact_id'], head,
                         receipt['binding'], 1, prior['receipt_id'],
                         prior['fact_id'], prior_head))
                    if cursor.rowcount != 1:
                        raise ProvenanceError('current-head compare-and-swap failed')
                    self._db.execute('INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                     self._values(receipt, raw, mac, head))
                self._db.execute('COMMIT')
                outcome = True
                readback = self.read_lifecycle_chain(proposal['binding'], key)
                if readback != ((paid_unit, (receipt, head)), (withdrawal,), head):
                    raise ProvenanceError('committed later-period restoration unavailable')
                return receipt, head
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

    def commit_cancellation(self, receipt, predecessor, key):
        """CAS the exact paid/lifecycle head to one immutable tagged control."""
        with self._lock:
            self._usable()
        if (type(receipt) is not dict or type(predecessor) is not tuple or len(predecessor) != 2
                or type(key) is not bytes or len(key) < 32):
            raise ProvenanceError('invalid lifecycle control input')
        material = {name: value for name, value in receipt.items()
                    if name not in ('receipt_id', 'fact_id')}
        try:
            receipt_domain, fact_domain = _control_identity_domains(receipt)
            if receipt.get('version') == 'reserved-failed-renewal-receipt/1':
                _validate_failed_renewal(receipt)
        except ProvenanceError:
            raise ProvenanceError('invalid lifecycle control scope') from None
        if (receipt.get('store') != self.store_id
                or receipt.get('receipt_id') != identity(receipt_domain, material)
                or receipt.get('fact_id') != identity(fact_domain, material)):
            raise ProvenanceError('invalid lifecycle control scope')
        raw = canonical(receipt)
        if len(raw) > 16384:
            raise ProvenanceError('oversized lifecycle control')
        head = _control_head(receipt)
        mac = hmac.new(key, _CONTROL_DOMAIN + raw, 'sha256').hexdigest()
        scope = _control_scope(self.store_id, receipt['binding'])
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                lineage, control, lifecycle_head = self.read_lifecycle(receipt['binding'], key)
                if control is not None:
                    if control != receipt or lifecycle_head != head:
                        raise ProvenanceError('reconciliation required')
                else:
                    if not lineage or lineage[-1] != predecessor or lifecycle_head != predecessor[1]:
                        raise ProvenanceError('lifecycle-head compare-and-swap failed')
                    if (receipt.get('paid_receipt_id') != predecessor[0]['receipt_id']
                            or receipt.get('paid_fact_id') != predecessor[0]['fact_id']
                            or receipt.get('paid_head') != predecessor[1]
                            or receipt.get('paid_sequence') != predecessor[0]['sequence']
                            or receipt.get('predecessor_lifecycle_head') != predecessor[1]):
                        raise ProvenanceError('wrong lifecycle predecessor')
                    self._db.execute('INSERT INTO dispositions VALUES (?,?,?)',
                                     (scope, raw.decode('ascii'), mac))
                self._db.execute('COMMIT')
                outcome = True
                readback = self.read_lifecycle(receipt['binding'], key)
                if readback[1:] != (receipt, head):
                    raise ProvenanceError('committed lifecycle control unavailable')
                return receipt, head
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

    def commit_failed_renewal(self, proposal, predecessor, key, admission_clock):
        """Atomically establish the Reserved clock and failed-renewal control.

        Source reconciliation is complete before this seam.  The transaction
        first authenticates the durable predecessor/replay state, then samples
        the source-owned admission clock exactly once for a new control.  Exact
        replay returns the stored control without consulting that clock.
        """
        with self._lock:
            self._usable()
        if (type(proposal) is not dict or type(predecessor) is not tuple
                or len(predecessor) != 2 or type(key) is not bytes or len(key) < 32
                or not callable(admission_clock)
                or any(name in proposal for name in _FAILED_RENEWAL_ADMISSION_FIELDS)):
            raise ProvenanceError('invalid failed-renewal proposal')
        _validate_failed_renewal_evidence(proposal)
        if proposal.get('version') != 'reserved-failed-renewal-receipt/1':
            raise ProvenanceError('invalid failed-renewal proposal')
        scope = _control_scope(self.store_id, proposal['binding'])
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                lineage, control, lifecycle_head = self.read_lifecycle(
                    proposal['binding'], key)
                if control is not None:
                    if (_failed_renewal_proposal(control) != proposal
                            or control.get('version') !=
                                'reserved-failed-renewal-receipt/1'):
                        raise ProvenanceError('reconciliation required')
                    receipt, head = control, lifecycle_head
                else:
                    if (not lineage or lineage[-1] != predecessor
                            or lifecycle_head != predecessor[1]):
                        raise ProvenanceError('lifecycle-head compare-and-swap failed')
                    if (proposal.get('store') != self.store_id
                            or proposal.get('paid_receipt_id') !=
                                predecessor[0]['receipt_id']
                            or proposal.get('paid_fact_id') != predecessor[0]['fact_id']
                            or proposal.get('paid_head') != predecessor[1]
                            or proposal.get('paid_sequence') !=
                                predecessor[0]['sequence']
                            or proposal.get('predecessor_lifecycle_head') !=
                                predecessor[1]):
                        raise ProvenanceError('wrong lifecycle predecessor')

                    # This is the authoritative lifecycle-admission boundary:
                    # all source and durable CAS predicates have passed while
                    # the write transaction is held, but no control exists yet.
                    verified = admission_clock()
                    if (type(verified) is not datetime
                            or verified.tzinfo is not timezone.utc
                            or verified.utcoffset() != timedelta(0)):
                        raise ProvenanceError('invalid failed-renewal admission clock')
                    receipt = dict(proposal)
                    receipt['failure_verified_at_utc'] = verified.isoformat()
                    receipt['recovery_deadline_exclusive_at_utc'] = (
                        verified + timedelta(days=7)).isoformat()
                    material = dict(receipt)
                    receipt['fact_id'] = identity('failed-renewal-fact/1', material)
                    receipt['receipt_id'] = identity('failed-renewal-receipt/1', material)
                    _validate_failed_renewal(receipt)
                    raw = canonical(receipt)
                    if len(raw) > 16384:
                        raise ProvenanceError('oversized lifecycle control')
                    head = _control_head(receipt)
                    mac = hmac.new(key, _CONTROL_DOMAIN + raw, 'sha256').hexdigest()
                    self._db.execute('INSERT INTO dispositions VALUES (?,?,?)',
                                     (scope, raw.decode('ascii'), mac))
                self._db.execute('COMMIT')
                outcome = True
                readback = self.read_lifecycle(proposal['binding'], key)
                if readback[1:] != (receipt, head):
                    raise ProvenanceError('committed failed renewal unavailable')
                return receipt, head
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

    def commit_full_withdrawal(self, proposal, predecessor, key, admission_clock):
        """Atomically admit one verified full withdrawal at the Reserved clock.

        ``predecessor`` is the exact paid unit plus the expected current
        lifecycle head and optional compatible cancellation receipt. Exact
        replay returns the durable receipt without sampling the clock.
        """
        with self._lock:
            self._usable()
        if (type(proposal) is not dict or type(predecessor) is not tuple
                or len(predecessor) != 3 or type(predecessor[0]) is not tuple
                or len(predecessor[0]) != 2 or type(key) is not bytes or len(key) < 32
                or not callable(admission_clock)
                or any(name in proposal for name in _WITHDRAWAL_ADMISSION_FIELDS)):
            raise ProvenanceError('invalid full-withdrawal proposal')
        _validate_withdrawal_evidence(proposal)
        paid_unit, expected_head, expected_control = predecessor
        scope = _control_scope(self.store_id, proposal['binding'])
        with self._lock:
            outcome = None
            try:
                self._db.execute('BEGIN IMMEDIATE')
                self._metadata()
                lineage, controls, lifecycle_head = self.read_lifecycle_chain(
                    proposal['binding'], key)
                current = controls[-1] if controls else None
                if (current is not None
                        and current.get('version') == 'reserved-full-withdrawal-receipt/1'):
                    if _withdrawal_proposal(current) != proposal:
                        raise ProvenanceError('reconciliation required')
                    receipt, head = current, lifecycle_head
                else:
                    if (not lineage or lineage[-1] != paid_unit
                            or lifecycle_head != expected_head
                            or current != expected_control
                            or (current is not None and current.get('version') !=
                                'reserved-scheduled-cancellation-receipt/1')):
                        raise ProvenanceError('lifecycle-head compare-and-swap failed')
                    paid, paid_head = paid_unit
                    if (proposal.get('store') != self.store_id
                            or proposal.get('paid_receipt_id') != paid['receipt_id']
                            or proposal.get('paid_fact_id') != paid['fact_id']
                            or proposal.get('paid_head') != paid_head
                            or proposal.get('paid_sequence') != paid['sequence']
                            or proposal.get('predecessor_lifecycle_head') != expected_head):
                        raise ProvenanceError('wrong lifecycle predecessor')
                    verified = admission_clock()
                    if (type(verified) is not datetime
                            or verified.tzinfo is not timezone.utc
                            or verified.utcoffset() != timedelta(0)):
                        raise ProvenanceError('invalid full-withdrawal admission clock')
                    receipt = dict(proposal)
                    receipt['withdrawal_verified_at_utc'] = verified.isoformat()
                    material = dict(receipt)
                    receipt['fact_id'] = identity('full-withdrawal-fact/1', material)
                    receipt['receipt_id'] = identity('full-withdrawal-receipt/1', material)
                    _validate_withdrawal(receipt)
                    raw = canonical(receipt)
                    if len(raw) > 16384:
                        raise ProvenanceError('oversized lifecycle control')
                    head = _control_head(receipt)
                    mac = hmac.new(key, _CONTROL_DOMAIN + raw, 'sha256').hexdigest()
                    row_identity = (scope if current is None else scope + ':' +
                        hashlib.sha256(expected_head.encode('ascii')).hexdigest())
                    self._db.execute('INSERT INTO dispositions VALUES (?,?,?)',
                                     (row_identity, raw.decode('ascii'), mac))
                self._db.execute('COMMIT')
                outcome = True
                readback = self.read_lifecycle(proposal['binding'], key)
                if readback[1:] != (receipt, head):
                    raise ProvenanceError('committed full withdrawal unavailable')
                return receipt, head
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

    def _conflicts(self, key):
        rows = self._db.execute(
            "SELECT identity,body,mac FROM dispositions WHERE identity LIKE ? ORDER BY identity",
            (_CONFLICT_PREFIX + '%',)).fetchall()
        if len(rows) > 1000:
            raise ProvenanceError('disposition bound')
        return tuple(_decode_conflict(self.store_id, row, key) for row in rows)

    def read_conflict(self, binding, *, event_id, key):
        """Return the sole authenticated disposition consuming this scoped event ID."""
        if (type(binding) is not str or not binding or type(event_id) is not str
                or not event_id):
            raise ProvenanceError('invalid reconciliation lookup')
        with self._lock:
            self._metadata()
            matches = tuple(body for body in self._conflicts(key)
                            if body['binding'] == binding and body['event_id'] == event_id)
            if len(matches) > 1:
                raise ProvenanceError('ambiguous reconciled event')
            return None if not matches else dict(matches[0])

    def read_conflicts(self, binding, *, key):
        """Return every bounded authenticated disposition for one binding."""
        if type(binding) is not str or not binding:
            raise ProvenanceError('invalid reconciliation lookup')
        with self._lock:
            self._metadata()
            return tuple(dict(body) for body in self._conflicts(key)
                         if body['binding'] == binding)

    def record_conflict(self, binding, *, event_id, raw_digest, object_key, key):
        """Durable minimised reconciliation disposition; never changes the head."""
        with self._lock:
            self._usable()
            self._db.execute('BEGIN IMMEDIATE')
            try:
                lineage, _, compared_head = self.read_lifecycle(binding, key)
                if not lineage:
                    raise ProvenanceError('no scoped historical unit')
                body = dict(version=VERSION, store=self.store_id, binding=binding, event_id=event_id,
                            raw_digest=raw_digest, object_key=object_key, compared_head=compared_head,
                            disposition='reconciliation_required')
                raw = canonical(body)
                if len(raw) > 2048 or self._db.execute('SELECT count(*) FROM dispositions').fetchone()[0] >= 1000:
                    raise ProvenanceError('disposition bound')
                digest = identity('paid-lineage-conflict/2', body)
                mac = hmac.new(key, _CONFLICT_DOMAIN + raw, 'sha256').hexdigest()
                prior = tuple(item for item in self._conflicts(key)
                              if item['binding'] == binding and item['event_id'] == event_id)
                if len(prior) > 1 or (prior and prior[0] != body):
                    raise ProvenanceError('changed reconciled event')
                if not prior:
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
