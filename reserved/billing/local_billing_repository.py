"""W10-S3D local transactional billing repository.

A caller-supplied, disposable, file-backed SQLite persistence/ordering primitive
for the settled October subscription lifecycle.  It stores only minimised
synthetic identifiers, canonical billing facts, content identities, append-only
ordering and bounded reconciliation dispositions.  It is opt-in: no module-level
database path, no import side effects, no application registration, no HTTP
endpoint and no entitlement grant.

This module is NOT a provider-admission or authenticated-storage boundary.  A
persisted row is a structural projection, never an authenticated fact.  No
producer here stamps ``authenticated=True`` merely from a row or hash; that
remains the independent source-admission responsibility of W10-S3C/S5D and any
future authenticated ingress.  The file is a same-process/co-operating-process
engineering datastore, not a defence against a hostile host administrator who
can rewrite or replace the SQLite file.

Schema ownership belongs exclusively to this module.  It creates a versioned,
digest-verified schema and fails closed on missing, corrupt, unsupported or
partial schema without destructive repair.  Missing/corrupt/unsupported/partial
schema raises ``LocalBillingRepositoryError`` and never migrates the application
database or rewrites history.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re as _re
import sqlite3 as _sqlite3
from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone
from pathlib import Path as _Path


CONTRACT_VERSION = "reserved-w10-local-billing-repository/1.0"
SCHEMA_VERSION = "reserved-w10-local-billing-repository-schema/1.0"
REPOSITORY_PURPOSE = "local_disposable_billing_journal_and_ordering_only"
RECORD_CLASSIFICATION = "structural_persisted_projection_not_authenticated_fact"

# Exact settled catalogue identities (FD-W10-001).  These are the exact
# ``reserved.billing.contracts.PlanKey`` values and are cross-checked in tests;
# the module deliberately avoids importing the application package so that it
# has no Flask/database/routing import side effects of its own.
PLAN_KEYS = frozenset(("monthly", "six_month", "yearly"))

# Exact W10-S3C billing-fact state vocabulary (never a provider status label).
FACT_STATES = frozenset(("paid", "payment_recovery", "suspended"))

# Exact W10-S3B observation kinds: canonical lifecycle kinds plus zero-effect
# reconciliation-only kinds.  None of these is an entitlement flag.
OBSERVATION_KINDS = frozenset(
    (
        "initial_payment_confirmed",
        "renewal_payment_confirmed",
        "renewal_payment_failed",
        "cancellation_confirmed",
        "unknown",
        "refund_observed",
        "dispute_observed",
        "chargeback_observed",
        "reversal_observed",
    )
)
_PAYMENT_KINDS = frozenset(("initial_payment_confirmed", "renewal_payment_confirmed"))

# Exact W10-S3C derivation and withdrawal-attribution vocabulary.
DERIVATION_KINDS = frozenset(
    (
        "verified_initial_payment",
        "verified_renewal_payment",
        "verified_renewal_failure",
        "verified_full_withdrawal",
        "verified_reinstatement",
        "verified_reversal_success",
        "verified_replacement_payment",
        "existing_derived_access",
        "withdrawal_open",
        "withdrawal_partial",
        "withdrawal_ambiguous",
        "withdrawal_contradictory",
        "withdrawal_unresolved",
    )
)
WITHDRAWAL_ATTRIBUTIONS = frozenset(
    ("not_applicable", "current_subscription_period", "other_period", "unknown")
)

# Bounded reconciliation disposition vocabulary for the append-only chain.
RECONCILIATION_DISPOSITION_KINDS = frozenset(
    (
        "pending_reconciliation",
        "quarantined_reused_source_identity",
        "reconciliation_recorded",
    )
)
_QUARANTINE_KIND = "quarantined_reused_source_identity"
_QUARANTINE_REASON = "reused source identity with different content"

# Exact bounded reconciliation reason vocabulary.  Disposition reasons are a
# fixed set of useful reconciliation phrases, never free text, log fragments or
# secret-shaped material.
RECONCILIATION_DISPOSITION_REASONS = frozenset(
    (
        "reused source identity with different content",
        "pending reconciliation",
        "reconciliation recorded",
    )
)

_BUSY_TIMEOUT_SECONDS = 5.0

_IDENTIFIER_RX = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
_SOURCE_IDENTIFIER_RX = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z")
_DIGEST_RX = _re.compile(r"^sha256:[0-9a-f]{64}\Z")
_JOURNAL_IDENTITY_RX = _re.compile(r"^billing-journal:sha256-[0-9a-f]{64}\Z")
_SECRET_MARKERS = (
    "secret",
    "token",
    "password",
    "credential",
    "api_key",
    "apikey",
    "private_key",
    "sk_live",
    "sk_test",
    "bearer",
)


class LocalBillingRepositoryError(ValueError):
    """A repository operation failed closed (schema, identity, ordering, lock)."""


@dataclass(frozen=True, slots=True)
class JournalRecord:
    """Structural projection of one accepted minimised journal entry."""

    sequence: int
    owner_id: str
    billing_account_id: str
    subscription_id: str
    plan_key: str
    source_namespace: str
    source_event_id: str
    source_event_digest: str
    observation_kind: str
    effective_date: _date
    paid_through: _date | None
    evidence_reference: str
    state: str
    valid_from_inclusive: _date
    valid_until_exclusive: _date
    transition_effective_at_utc: _datetime
    recovery_deadline_exclusive_at_utc: _datetime | None
    derivation_kind: str
    withdrawal_attribution: str
    content_identity: str
    predecessor_identity: str | None
    recorded_at_utc: _datetime


@dataclass(frozen=True, slots=True)
class SubscriptionHeadRecord:
    """Structural projection of one current head pointer."""

    owner_id: str
    billing_account_id: str
    subscription_id: str
    sequence: int
    head_identity: str
    state: str
    updated_at_utc: _datetime


@dataclass(frozen=True, slots=True)
class ReconciliationDispositionRecord:
    """Structural projection of one append-only reconciliation disposition."""

    disposition_id: str
    owner_id: str
    billing_account_id: str
    subscription_id: str
    source_namespace: str
    source_event_id: str
    disposition_sequence: int
    kind: str
    evidence_reference: str
    reason: str | None
    recorded_at_utc: _datetime
    predecessor_disposition_identity: str | None
    disposition_identity: str


_SCHEMA_DDL = (
    "CREATE TABLE repository_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE billing_journal ("
    "sequence INTEGER NOT NULL,"
    "owner_id TEXT NOT NULL,"
    "billing_account_id TEXT NOT NULL,"
    "subscription_id TEXT NOT NULL,"
    "plan_key TEXT NOT NULL,"
    "source_namespace TEXT NOT NULL,"
    "source_event_id TEXT NOT NULL,"
    "source_event_digest TEXT NOT NULL,"
    "observation_kind TEXT NOT NULL,"
    "effective_date TEXT NOT NULL,"
    "paid_through TEXT,"
    "evidence_reference TEXT NOT NULL,"
    "state TEXT NOT NULL,"
    "valid_from_inclusive TEXT NOT NULL,"
    "valid_until_exclusive TEXT NOT NULL,"
    "transition_effective_at_utc TEXT NOT NULL,"
    "recovery_deadline_exclusive_at_utc TEXT,"
    "derivation_kind TEXT NOT NULL,"
    "withdrawal_attribution TEXT NOT NULL,"
    "content_identity TEXT NOT NULL,"
    "predecessor_identity TEXT,"
    "recorded_at_utc TEXT NOT NULL,"
    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, sequence))",
    "CREATE UNIQUE INDEX billing_journal_source_identity_unique "
    "ON billing_journal (source_namespace, source_event_id)",
    "CREATE TABLE subscription_head ("
    "owner_id TEXT NOT NULL,"
    "billing_account_id TEXT NOT NULL,"
    "subscription_id TEXT NOT NULL,"
    "sequence INTEGER NOT NULL,"
    "head_identity TEXT NOT NULL,"
    "state TEXT NOT NULL,"
    "updated_at_utc TEXT NOT NULL,"
    "PRIMARY KEY (owner_id, billing_account_id, subscription_id))",
    "CREATE TABLE reconciliation_disposition ("
    "disposition_id TEXT NOT NULL,"
    "owner_id TEXT NOT NULL,"
    "billing_account_id TEXT NOT NULL,"
    "subscription_id TEXT NOT NULL,"
    "source_namespace TEXT NOT NULL,"
    "source_event_id TEXT NOT NULL,"
    "disposition_sequence INTEGER NOT NULL,"
    "kind TEXT NOT NULL,"
    "evidence_reference TEXT NOT NULL,"
    "reason TEXT,"
    "recorded_at_utc TEXT NOT NULL,"
    "predecessor_disposition_identity TEXT,"
    "disposition_identity TEXT NOT NULL,"
    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, "
    "source_namespace, source_event_id, disposition_sequence))",
    "CREATE UNIQUE INDEX reconciliation_disposition_id_unique "
    "ON reconciliation_disposition (disposition_id)",
)

_SCHEMA_DIGEST = _hashlib.sha256(
    "\n".join(_SCHEMA_DDL).encode("utf-8")
).hexdigest()


def _normalise_schema_sql(sql):
    """Collapse whitespace in one owned-schema statement to a canonical form.

    The approved schema contains no string or comment literals whose internal
    whitespace is significant, so this yields a stable identity form for exact
    declaration comparison without parsing SQL.
    """
    return " ".join(sql.split())


def _schema_object_key(statement):
    """Return the ``(type, name)`` identity for one owned CREATE statement.

    Bounded to the two statement shapes this module itself emits
    (``CREATE TABLE ...`` and ``CREATE [UNIQUE] INDEX ...``); it is not a
    general SQL parser.
    """
    tokens = _normalise_schema_sql(statement).split()
    if len(tokens) < 3 or tokens[0].upper() != "CREATE":
        raise LocalBillingRepositoryError("unrecognised owned schema statement")
    if tokens[1].upper() == "TABLE":
        return ("table", tokens[2])
    if tokens[1].upper() == "INDEX":
        return ("index", tokens[2])
    if (
        tokens[1].upper() == "UNIQUE"
        and len(tokens) >= 4
        and tokens[2].upper() == "INDEX"
    ):
        return ("index", tokens[3])
    raise LocalBillingRepositoryError("unrecognised owned schema statement")


# Full expected column semantics per table: (name, declared type, NOT NULL,
# default value).  Compared against the live ``PRAGMA table_info`` rather than
# any stored digest, so an altered declared type, a dropped NOT NULL or an added
# DEFAULT fails closed even when column names and PK/index metadata are intact.
_EXPECTED_COLUMN_SPECS = {
    "repository_meta": (
        ("key", "TEXT", False, None),
        ("value", "TEXT", True, None),
    ),
    "billing_journal": (
        ("sequence", "INTEGER", True, None),
        ("owner_id", "TEXT", True, None),
        ("billing_account_id", "TEXT", True, None),
        ("subscription_id", "TEXT", True, None),
        ("plan_key", "TEXT", True, None),
        ("source_namespace", "TEXT", True, None),
        ("source_event_id", "TEXT", True, None),
        ("source_event_digest", "TEXT", True, None),
        ("observation_kind", "TEXT", True, None),
        ("effective_date", "TEXT", True, None),
        ("paid_through", "TEXT", False, None),
        ("evidence_reference", "TEXT", True, None),
        ("state", "TEXT", True, None),
        ("valid_from_inclusive", "TEXT", True, None),
        ("valid_until_exclusive", "TEXT", True, None),
        ("transition_effective_at_utc", "TEXT", True, None),
        ("recovery_deadline_exclusive_at_utc", "TEXT", False, None),
        ("derivation_kind", "TEXT", True, None),
        ("withdrawal_attribution", "TEXT", True, None),
        ("content_identity", "TEXT", True, None),
        ("predecessor_identity", "TEXT", False, None),
        ("recorded_at_utc", "TEXT", True, None),
    ),
    "subscription_head": (
        ("owner_id", "TEXT", True, None),
        ("billing_account_id", "TEXT", True, None),
        ("subscription_id", "TEXT", True, None),
        ("sequence", "INTEGER", True, None),
        ("head_identity", "TEXT", True, None),
        ("state", "TEXT", True, None),
        ("updated_at_utc", "TEXT", True, None),
    ),
    "reconciliation_disposition": (
        ("disposition_id", "TEXT", True, None),
        ("owner_id", "TEXT", True, None),
        ("billing_account_id", "TEXT", True, None),
        ("subscription_id", "TEXT", True, None),
        ("source_namespace", "TEXT", True, None),
        ("source_event_id", "TEXT", True, None),
        ("disposition_sequence", "INTEGER", True, None),
        ("kind", "TEXT", True, None),
        ("evidence_reference", "TEXT", True, None),
        ("reason", "TEXT", False, None),
        ("recorded_at_utc", "TEXT", True, None),
        ("predecessor_disposition_identity", "TEXT", False, None),
        ("disposition_identity", "TEXT", True, None),
    ),
}

_EXPECTED_COLUMNS = {
    table: tuple(spec[0] for spec in specs)
    for table, specs in _EXPECTED_COLUMN_SPECS.items()
}

# Required primary-key column order per table, validated against the live
# schema rather than trusting any stored digest.
_EXPECTED_PRIMARY_KEYS = {
    "repository_meta": ("key",),
    "billing_journal": (
        "owner_id",
        "billing_account_id",
        "subscription_id",
        "sequence",
    ),
    "subscription_head": (
        "owner_id",
        "billing_account_id",
        "subscription_id",
    ),
    "reconciliation_disposition": (
        "owner_id",
        "billing_account_id",
        "subscription_id",
        "source_namespace",
        "source_event_id",
        "disposition_sequence",
    ),
}

# Required explicit (CREATE [UNIQUE] INDEX) indexes per table: name, uniqueness,
# column order and partial-index predicate.  A partial predicate of ``None``
# means the required index must NOT be partial; a non-None value is the exact
# normalised ``WHERE`` predicate that must be absent/present accordingly.  This
# rejects altered index semantics (e.g. an index silently made partial), not
# only name/column/uniqueness changes.
_EXPECTED_EXPLICIT_INDEXES = {
    "repository_meta": (),
    "billing_journal": (
        (
            "billing_journal_source_identity_unique",
            True,
            ("source_namespace", "source_event_id"),
            None,
        ),
    ),
    "subscription_head": (),
    "reconciliation_disposition": (
        ("reconciliation_disposition_id_unique", True, ("disposition_id",), None),
    ),
}

# Bounded complete approved-schema identity: the exact normalised declaration of
# every owned table and index, derived from ``_SCHEMA_DDL``.  Compared against
# the live ``sqlite_master`` SQL so that any declaration change — table-column
# and index collations, primary/unique conflict policy, generated columns,
# STRICT/WITHOUT ROWID markers and every other CREATE-text difference — fails
# closed, without enumerating a partial list of omitted properties.
_EXPECTED_SCHEMA_OBJECTS = {
    _schema_object_key(statement): _normalise_schema_sql(statement)
    for statement in _SCHEMA_DDL
}

_JOURNAL_CONTENT_FIELDS = (
    "contract_version",
    "owner_id",
    "billing_account_id",
    "subscription_id",
    "plan_key",
    "source_namespace",
    "source_event_id",
    "source_event_digest",
    "observation_kind",
    "effective_date",
    "paid_through",
    "evidence_reference",
    "state",
    "valid_from_inclusive",
    "valid_until_exclusive",
    "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc",
    "derivation_kind",
    "withdrawal_attribution",
    "sequence",
    "predecessor_identity",
)

_DISPOSITION_CONTENT_FIELDS = (
    "contract_version",
    "disposition_id",
    "owner_id",
    "billing_account_id",
    "subscription_id",
    "source_namespace",
    "source_event_id",
    "disposition_sequence",
    "kind",
    "evidence_reference",
    "reason",
    "recorded_at_utc",
    "predecessor_disposition_identity",
)


def _canonical_json_value(value):
    if value is None:
        return None
    if type(value) is _datetime:
        return value.isoformat()
    if type(value) is _date:
        return value.isoformat()
    if type(value) is str or type(value) is int:
        return value
    raise LocalBillingRepositoryError("unsupported canonical content value")


def _content_identity(prefix, material):
    payload = _json.dumps(
        [_canonical_json_value(value) for value in material],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return f"{prefix}:sha256-{_hashlib.sha256(payload).hexdigest()}"


def _bounded_identifier(value, label):
    if type(value) is not str or _IDENTIFIER_RX.fullmatch(value) is None:
        raise LocalBillingRepositoryError(f"invalid {label}")
    lowered = value.casefold()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise LocalBillingRepositoryError(f"{label} is secret-shaped")
    return value


def _source_identifier(value, label):
    if type(value) is not str or _SOURCE_IDENTIFIER_RX.fullmatch(value) is None:
        raise LocalBillingRepositoryError(f"invalid {label}")
    lowered = value.casefold()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise LocalBillingRepositoryError(f"{label} is secret-shaped")
    return value


def _plan_key(value):
    if type(value) is not str or value not in PLAN_KEYS:
        raise LocalBillingRepositoryError(
            "plan_key must be one exact settled catalogue identity"
        )
    return value


def _source_event_digest(value):
    if type(value) is not str or _DIGEST_RX.fullmatch(value) is None:
        raise LocalBillingRepositoryError("source_event_digest must be a sha256 digest")
    return value


def _journal_identity(value, label):
    if value is None:
        return None
    if type(value) is not str or _JOURNAL_IDENTITY_RX.fullmatch(value) is None:
        raise LocalBillingRepositoryError(f"invalid {label}")
    return value


def _exact_date(value, label):
    if type(value) is not _date:
        raise LocalBillingRepositoryError(f"{label} must be an exact date")
    return value


def _exact_utc(value, label):
    if (
        type(value) is not _datetime
        or value.tzinfo is not _timezone.utc
        or value.utcoffset() != _timedelta(0)
    ):
        raise LocalBillingRepositoryError(
            f"{label} must be an exact timezone-aware UTC datetime"
        )
    return value


def _bounded_reason(value):
    if value is None:
        return None
    if type(value) is not str or value not in RECONCILIATION_DISPOSITION_REASONS:
        raise LocalBillingRepositoryError(
            "reason must be an exact bounded reconciliation reason"
        )
    return value


def _coerce_path(path):
    if isinstance(path, _Path):
        candidate = path
    elif type(path) is str:
        if path == "" or "\x00" in path:
            raise LocalBillingRepositoryError("repository path is invalid")
        candidate = _Path(path)
    else:
        raise TypeError("path must be a str or pathlib.Path")
    text = str(candidate)
    if text.startswith("file:") or "?" in text or "#" in text:
        raise LocalBillingRepositoryError(
            "repository path must not be a URI or carry query/fragment"
        )
    if text == ":memory:" or candidate.name == ":memory:":
        raise LocalBillingRepositoryError(
            "in-memory repositories are not supported; a real file is required"
        )
    return candidate


def _validate_new_path(path):
    candidate = _coerce_path(path)
    if candidate.is_symlink() or candidate.exists():
        raise LocalBillingRepositoryError(
            "repository path must not already exist or be a symlink"
        )
    return candidate


def _validate_open_path(path):
    candidate = _coerce_path(path)
    if candidate.is_symlink():
        raise LocalBillingRepositoryError("repository path must not be a symlink")
    if not candidate.exists() or not candidate.is_file():
        raise LocalBillingRepositoryError(
            "repository path does not exist or is not a regular file"
        )
    return candidate


def _bounded_timeout(value):
    if type(value) is not float and type(value) is not int:
        raise TypeError("busy_timeout_seconds must be a number")
    if value < 0 or value > 60:
        raise LocalBillingRepositoryError(
            "busy_timeout_seconds must be bounded between 0 and 60 seconds"
        )
    return float(value)


class LocalBillingRepository:
    """A caller-supplied disposable SQLite billing journal and head store."""

    def __init__(self, connection, path):
        self._connection = connection
        self._path = path

    # -- construction ---------------------------------------------------------

    @classmethod
    def create(cls, path, *, busy_timeout_seconds: float = _BUSY_TIMEOUT_SECONDS) -> "LocalBillingRepository":
        """Create a brand-new repository; fail closed if the path exists."""
        candidate = _validate_new_path(path)
        connection = _sqlite3.connect(
            str(candidate),
            isolation_level=None,
            uri=False,
            timeout=_bounded_timeout(busy_timeout_seconds),
        )
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            try:
                for statement in _SCHEMA_DDL:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO repository_meta (key, value) VALUES (?, ?)",
                    ("schema_version", SCHEMA_VERSION),
                )
                connection.execute(
                    "INSERT INTO repository_meta (key, value) VALUES (?, ?)",
                    ("schema_digest", _SCHEMA_DIGEST),
                )
                connection.execute(
                    "INSERT INTO repository_meta (key, value) VALUES (?, ?)",
                    ("repository_purpose", REPOSITORY_PURPOSE),
                )
                connection.execute(
                    "INSERT INTO repository_meta (key, value) VALUES (?, ?)",
                    (
                        "created_at_utc",
                        _datetime.now(_timezone.utc).isoformat(),
                    ),
                )
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise
        except BaseException:
            connection.close()
            raise
        return cls(connection, candidate)

    @classmethod
    def open(cls, path, *, busy_timeout_seconds: float = _BUSY_TIMEOUT_SECONDS) -> "LocalBillingRepository":
        """Open an existing repository; fail closed on missing/corrupt schema."""
        candidate = _validate_open_path(path)
        connection = _sqlite3.connect(
            str(candidate),
            isolation_level=None,
            uri=False,
            timeout=_bounded_timeout(busy_timeout_seconds),
        )
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            _verify_schema(connection)
        except BaseException:
            connection.close()
            raise
        return cls(connection, candidate)

    # -- lifecycle ------------------------------------------------------------

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "LocalBillingRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -- write path -----------------------------------------------------------

    def append_observation(
        self,
        *,
        owner_id,
        billing_account_id,
        subscription_id,
        plan_key,
        source_namespace,
        source_event_id,
        source_event_digest,
        observation_kind,
        effective_date,
        paid_through,
        evidence_reference,
        state,
        valid_from_inclusive,
        valid_until_exclusive,
        transition_effective_at_utc,
        recovery_deadline_exclusive_at_utc,
        derivation_kind,
        withdrawal_attribution,
        expected_predecessor_identity,
        expected_sequence,
        recorded_at_utc,
    ) -> JournalRecord:
        """Atomically append one accepted observation and advance its head.

        The journal entry and the head advancement commit in one transaction, or
        neither does.  An exact duplicate is idempotent.  A reused source-event
        identity with different content is quarantined and fails closed without
        rewriting accepted history or advancing access.  A stale, out-of-order or
        forked successor fails closed.
        """
        values = self._validate_observation(
            owner_id=owner_id,
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            plan_key=plan_key,
            source_namespace=source_namespace,
            source_event_id=source_event_id,
            source_event_digest=source_event_digest,
            observation_kind=observation_kind,
            effective_date=effective_date,
            paid_through=paid_through,
            evidence_reference=evidence_reference,
            state=state,
            valid_from_inclusive=valid_from_inclusive,
            valid_until_exclusive=valid_until_exclusive,
            transition_effective_at_utc=transition_effective_at_utc,
            recovery_deadline_exclusive_at_utc=recovery_deadline_exclusive_at_utc,
            derivation_kind=derivation_kind,
            withdrawal_attribution=withdrawal_attribution,
            expected_predecessor_identity=expected_predecessor_identity,
            expected_sequence=expected_sequence,
            recorded_at_utc=recorded_at_utc,
        )
        content_identity = _content_identity(
            "billing-journal",
            tuple(values[field] for field in _JOURNAL_CONTENT_FIELDS),
        )
        values["content_identity"] = content_identity

        connection = self._connection
        self._begin_immediate(connection)
        resolved = False
        try:
            self._verify_chain_and_head(
                connection,
                values["owner_id"],
                values["billing_account_id"],
                values["subscription_id"],
            )
            existing = connection.execute(
                "SELECT source_namespace, source_event_id, source_event_digest, "
                "content_identity FROM billing_journal "
                "WHERE source_namespace = ? AND source_event_id = ?",
                (values["source_namespace"], values["source_event_id"]),
            ).fetchone()
            if existing is not None:
                if (
                    existing[2] == values["source_event_digest"]
                    and existing[3] == content_identity
                ):
                    connection.execute("ROLLBACK")
                    resolved = True
                    return self._load_journal_row(
                        connection,
                        values["owner_id"],
                        values["billing_account_id"],
                        values["subscription_id"],
                        values["sequence"],
                    )
                self._append_quarantine_disposition(connection, values)
                connection.execute("COMMIT")
                resolved = True
                raise LocalBillingRepositoryError(
                    "reused source identity with different content; "
                    "observation quarantined and not advanced"
                )

            head = connection.execute(
                "SELECT sequence, head_identity FROM subscription_head "
                "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ?",
                (
                    values["owner_id"],
                    values["billing_account_id"],
                    values["subscription_id"],
                ),
            ).fetchone()
            if values["sequence"] == 1:
                origin = connection.execute(
                    "SELECT 1 FROM billing_journal "
                    "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
                    "LIMIT 1",
                    (
                        values["owner_id"],
                        values["billing_account_id"],
                        values["subscription_id"],
                    ),
                ).fetchone()
                if (
                    head is not None
                    or values["predecessor_identity"] is not None
                    or origin is not None
                ):
                    raise LocalBillingRepositoryError(
                        "originless sequence or unexpected predecessor"
                    )
            else:
                if head is None:
                    raise LocalBillingRepositoryError("missing current head for successor")
                if (
                    head[0] != values["sequence"] - 1
                    or head[1] != values["predecessor_identity"]
                ):
                    raise LocalBillingRepositoryError(
                        "stale, out-of-order or forked predecessor"
                    )
                predecessor = self._load_journal_row(
                    connection,
                    values["owner_id"],
                    values["billing_account_id"],
                    values["subscription_id"],
                    values["sequence"] - 1,
                )
                if predecessor.content_identity != head[1]:
                    raise LocalBillingRepositoryError(
                        "stale, out-of-order or forked predecessor"
                    )
                if predecessor.plan_key != values["plan_key"]:
                    raise LocalBillingRepositoryError(
                        "plan change is not authorised without explicit policy"
                    )
                if values["effective_date"] < predecessor.effective_date:
                    raise LocalBillingRepositoryError(
                        "temporal regression in effective date"
                    )
                if (
                    values["transition_effective_at_utc"]
                    < predecessor.transition_effective_at_utc
                ):
                    raise LocalBillingRepositoryError(
                        "temporal regression in transition effective instant"
                    )

            self._insert_journal_row(connection, values)
            self._upsert_head_row(connection, values)
            connection.execute("COMMIT")
            resolved = True
        except LocalBillingRepositoryError:
            raise
        except _sqlite3.Error as exc:
            raise LocalBillingRepositoryError("repository transaction failed") from exc
        finally:
            if not resolved:
                try:
                    connection.execute("ROLLBACK")
                except _sqlite3.Error:
                    pass

        return _journal_record_from_values(values)

    # -- read path ------------------------------------------------------------

    def current_head(
        self, *, owner_id, billing_account_id, subscription_id
    ) -> SubscriptionHeadRecord | None:
        owner = _bounded_identifier(owner_id, "owner_id")
        account = _bounded_identifier(billing_account_id, "billing_account_id")
        subscription = _bounded_identifier(subscription_id, "subscription_id")

        def read(connection):
            row = connection.execute(
                "SELECT owner_id, billing_account_id, subscription_id, sequence, "
                "head_identity, state, updated_at_utc FROM subscription_head "
                "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ?",
                (owner, account, subscription),
            ).fetchone()
            self._verify_chain_and_head(connection, owner, account, subscription)
            if row is None:
                return None
            return SubscriptionHeadRecord(
                owner_id=row[0],
                billing_account_id=row[1],
                subscription_id=row[2],
                sequence=row[3],
                head_identity=row[4],
                state=row[5],
                updated_at_utc=_parse_utc(row[6]),
            )

        return self._with_read_snapshot(read)

    def journal(
        self, *, owner_id, billing_account_id, subscription_id
    ) -> tuple[JournalRecord, ...]:
        owner = _bounded_identifier(owner_id, "owner_id")
        account = _bounded_identifier(billing_account_id, "billing_account_id")
        subscription = _bounded_identifier(subscription_id, "subscription_id")

        def read(connection):
            self._verify_chain_and_head(connection, owner, account, subscription)
            rows = connection.execute(
                "SELECT owner_id, billing_account_id, subscription_id, sequence "
                "FROM billing_journal "
                "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
                "ORDER BY sequence",
                (owner, account, subscription),
            ).fetchall()
            records = []
            for row in rows:
                records.append(
                    self._load_journal_row(connection, row[0], row[1], row[2], row[3])
                )
            return tuple(records)

        return self._with_read_snapshot(read)

    def reconciliation_dispositions(
        self,
        *,
        owner_id,
        billing_account_id,
        subscription_id,
        source_namespace,
        source_event_id,
    ) -> tuple[ReconciliationDispositionRecord, ...]:
        owner = _bounded_identifier(owner_id, "owner_id")
        account = _bounded_identifier(billing_account_id, "billing_account_id")
        subscription = _bounded_identifier(subscription_id, "subscription_id")
        namespace = _source_identifier(source_namespace, "source_namespace")
        event_id = _source_identifier(source_event_id, "source_event_id")
        connection = self._connection
        rows = connection.execute(
            "SELECT disposition_id, owner_id, billing_account_id, subscription_id, "
            "source_namespace, source_event_id, disposition_sequence, kind, "
            "evidence_reference, reason, recorded_at_utc, "
            "predecessor_disposition_identity, disposition_identity "
            "FROM reconciliation_disposition "
            "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
            "AND source_namespace = ? AND source_event_id = ? "
            "ORDER BY disposition_sequence",
            (owner, account, subscription, namespace, event_id),
        ).fetchall()
        records = []
        for row in rows:
            records.append(_disposition_record_from_row(row))
        return tuple(records)

    def append_reconciliation_disposition(
        self,
        *,
        disposition_id,
        owner_id,
        billing_account_id,
        subscription_id,
        source_namespace,
        source_event_id,
        kind,
        evidence_reference,
        reason=None,
        recorded_at_utc,
    ) -> ReconciliationDispositionRecord:
        disposition_id = _bounded_identifier(disposition_id, "disposition_id")
        owner = _bounded_identifier(owner_id, "owner_id")
        account = _bounded_identifier(billing_account_id, "billing_account_id")
        subscription = _bounded_identifier(subscription_id, "subscription_id")
        namespace = _source_identifier(source_namespace, "source_namespace")
        event_id = _source_identifier(source_event_id, "source_event_id")
        if type(kind) is not str or kind not in RECONCILIATION_DISPOSITION_KINDS:
            raise LocalBillingRepositoryError("invalid reconciliation disposition kind")
        evidence = _source_identifier(evidence_reference, "evidence_reference")
        reason = _bounded_reason(reason)
        recorded_at = _exact_utc(recorded_at_utc, "recorded_at_utc")

        connection = self._connection
        self._begin_immediate(connection)
        resolved = False
        try:
            sequence = _next_disposition_sequence(
                connection, owner, account, subscription, namespace, event_id
            )
            predecessor = _last_disposition_identity(
                connection, owner, account, subscription, namespace, event_id
            )
            disposition_values = {
                "contract_version": CONTRACT_VERSION,
                "disposition_id": disposition_id,
                "owner_id": owner,
                "billing_account_id": account,
                "subscription_id": subscription,
                "source_namespace": namespace,
                "source_event_id": event_id,
                "disposition_sequence": sequence,
                "kind": kind,
                "evidence_reference": evidence,
                "reason": reason,
                "recorded_at_utc": recorded_at,
                "predecessor_disposition_identity": predecessor,
            }
            disposition_identity = _content_identity(
                "reconciliation-disposition",
                tuple(
                    disposition_values[field] for field in _DISPOSITION_CONTENT_FIELDS
                ),
            )
            disposition_values["disposition_identity"] = disposition_identity
            self._insert_disposition_row(connection, disposition_values, disposition_identity)
            connection.execute("COMMIT")
            resolved = True
        except LocalBillingRepositoryError:
            raise
        except _sqlite3.Error as exc:
            raise LocalBillingRepositoryError("repository transaction failed") from exc
        finally:
            if not resolved:
                try:
                    connection.execute("ROLLBACK")
                except _sqlite3.Error:
                    pass

        return ReconciliationDispositionRecord(
            disposition_id=disposition_id,
            owner_id=owner,
            billing_account_id=account,
            subscription_id=subscription,
            source_namespace=namespace,
            source_event_id=event_id,
            disposition_sequence=sequence,
            kind=kind,
            evidence_reference=evidence,
            reason=reason,
            recorded_at_utc=recorded_at,
            predecessor_disposition_identity=predecessor,
            disposition_identity=disposition_identity,
        )

    # -- helpers --------------------------------------------------------------

    def _begin_immediate(self, connection):
        try:
            connection.execute("BEGIN IMMEDIATE")
        except _sqlite3.OperationalError as exc:
            raise LocalBillingRepositoryError(
                "repository is locked or unavailable"
            ) from exc

    def _with_read_snapshot(self, operation):
        """Run ``operation`` inside one bounded DEFERRED read transaction.

        The transaction upgrades to a shared lock on the first read and is
        released on rollback, so a concurrent writer cannot commit between the
        queries that make up a single read and the read never observes a torn
        journal/head state.  The lock is held only for the duration of the read
        (bounded by SQLite's own busy timeout); there is no global lock or retry
        loop, and true corruption checks are unchanged.
        """
        connection = self._connection
        connection.execute("BEGIN")
        try:
            return operation(connection)
        finally:
            try:
                connection.execute("ROLLBACK")
            except _sqlite3.Error:
                pass

    def _validate_observation(
        self,
        *,
        owner_id,
        billing_account_id,
        subscription_id,
        plan_key,
        source_namespace,
        source_event_id,
        source_event_digest,
        observation_kind,
        effective_date,
        paid_through,
        evidence_reference,
        state,
        valid_from_inclusive,
        valid_until_exclusive,
        transition_effective_at_utc,
        recovery_deadline_exclusive_at_utc,
        derivation_kind,
        withdrawal_attribution,
        expected_predecessor_identity,
        expected_sequence,
        recorded_at_utc,
    ):
        owner = _bounded_identifier(owner_id, "owner_id")
        account = _bounded_identifier(billing_account_id, "billing_account_id")
        subscription = _bounded_identifier(subscription_id, "subscription_id")
        plan = _plan_key(plan_key)
        namespace = _source_identifier(source_namespace, "source_namespace")
        event_id = _source_identifier(source_event_id, "source_event_id")
        digest = _source_event_digest(source_event_digest)
        if type(observation_kind) is not str or observation_kind not in OBSERVATION_KINDS:
            raise LocalBillingRepositoryError("invalid observation_kind")
        effective = _exact_date(effective_date, "effective_date")
        if paid_through is None:
            paid_through_date = None
        else:
            paid_through_date = _exact_date(paid_through, "paid_through")
        if observation_kind in _PAYMENT_KINDS:
            if paid_through_date is None or paid_through_date < effective:
                raise LocalBillingRepositoryError(
                    "confirmed payment requires a current paid period"
                )
        elif paid_through_date is not None:
            raise LocalBillingRepositoryError(
                "non-payment observation must not carry paid_through"
            )
        evidence = _source_identifier(evidence_reference, "evidence_reference")
        if type(state) is not str or state not in FACT_STATES:
            raise LocalBillingRepositoryError("invalid billing-fact state")
        valid_from = _exact_date(valid_from_inclusive, "valid_from_inclusive")
        valid_until = _exact_date(valid_until_exclusive, "valid_until_exclusive")
        if valid_from >= valid_until:
            raise LocalBillingRepositoryError("billing-fact validity interval is invalid")
        transition = _exact_utc(transition_effective_at_utc, "transition_effective_at_utc")
        if recovery_deadline_exclusive_at_utc is None:
            deadline = None
        else:
            deadline = _exact_utc(
                recovery_deadline_exclusive_at_utc,
                "recovery_deadline_exclusive_at_utc",
            )
        if type(derivation_kind) is not str or derivation_kind not in DERIVATION_KINDS:
            raise LocalBillingRepositoryError("invalid derivation_kind")
        if (
            type(withdrawal_attribution) is not str
            or withdrawal_attribution not in WITHDRAWAL_ATTRIBUTIONS
        ):
            raise LocalBillingRepositoryError("invalid withdrawal_attribution")
        predecessor = _journal_identity(
            expected_predecessor_identity, "expected_predecessor_identity"
        )
        if type(expected_sequence) is not int or expected_sequence <= 0:
            raise LocalBillingRepositoryError("expected_sequence must be a positive integer")
        recorded_at = _exact_utc(recorded_at_utc, "recorded_at_utc")

        if expected_sequence == 1 and predecessor is not None:
            raise LocalBillingRepositoryError(
                "originless sequence cannot name a predecessor"
            )
        if expected_sequence > 1 and predecessor is None:
            raise LocalBillingRepositoryError("successor must name its predecessor")

        return {
            "contract_version": CONTRACT_VERSION,
            "owner_id": owner,
            "billing_account_id": account,
            "subscription_id": subscription,
            "plan_key": plan,
            "source_namespace": namespace,
            "source_event_id": event_id,
            "source_event_digest": digest,
            "observation_kind": observation_kind,
            "effective_date": effective,
            "paid_through": paid_through_date,
            "evidence_reference": evidence,
            "state": state,
            "valid_from_inclusive": valid_from,
            "valid_until_exclusive": valid_until,
            "transition_effective_at_utc": transition,
            "recovery_deadline_exclusive_at_utc": deadline,
            "derivation_kind": derivation_kind,
            "withdrawal_attribution": withdrawal_attribution,
            "sequence": expected_sequence,
            "predecessor_identity": predecessor,
            "recorded_at_utc": recorded_at,
        }

    def _insert_journal_row(self, connection, values):
        connection.execute(
            "INSERT INTO billing_journal ("
            "sequence, owner_id, billing_account_id, subscription_id, plan_key, "
            "source_namespace, source_event_id, source_event_digest, "
            "observation_kind, effective_date, paid_through, evidence_reference, "
            "state, valid_from_inclusive, valid_until_exclusive, "
            "transition_effective_at_utc, recovery_deadline_exclusive_at_utc, "
            "derivation_kind, withdrawal_attribution, content_identity, "
            "predecessor_identity, recorded_at_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                values["sequence"],
                values["owner_id"],
                values["billing_account_id"],
                values["subscription_id"],
                values["plan_key"],
                values["source_namespace"],
                values["source_event_id"],
                values["source_event_digest"],
                values["observation_kind"],
                values["effective_date"].isoformat(),
                (
                    None
                    if values["paid_through"] is None
                    else values["paid_through"].isoformat()
                ),
                values["evidence_reference"],
                values["state"],
                values["valid_from_inclusive"].isoformat(),
                values["valid_until_exclusive"].isoformat(),
                values["transition_effective_at_utc"].isoformat(),
                (
                    None
                    if values["recovery_deadline_exclusive_at_utc"] is None
                    else values["recovery_deadline_exclusive_at_utc"].isoformat()
                ),
                values["derivation_kind"],
                values["withdrawal_attribution"],
                values["content_identity"],
                values["predecessor_identity"],
                values["recorded_at_utc"].isoformat(),
            ),
        )

    def _upsert_head_row(self, connection, values):
        connection.execute(
            "INSERT INTO subscription_head ("
            "owner_id, billing_account_id, subscription_id, sequence, "
            "head_identity, state, updated_at_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(owner_id, billing_account_id, subscription_id) DO UPDATE SET "
            "sequence = excluded.sequence, "
            "head_identity = excluded.head_identity, "
            "state = excluded.state, "
            "updated_at_utc = excluded.updated_at_utc",
            (
                values["owner_id"],
                values["billing_account_id"],
                values["subscription_id"],
                values["sequence"],
                values["content_identity"],
                values["state"],
                values["recorded_at_utc"].isoformat(),
            ),
        )

    def _append_quarantine_disposition(self, connection, values):
        sequence = _next_disposition_sequence(
            connection,
            values["owner_id"],
            values["billing_account_id"],
            values["subscription_id"],
            values["source_namespace"],
            values["source_event_id"],
        )
        predecessor = _last_disposition_identity(
            connection,
            values["owner_id"],
            values["billing_account_id"],
            values["subscription_id"],
            values["source_namespace"],
            values["source_event_id"],
        )
        # The generated identifier must be deterministically bound to the full
        # bounded disposition identity: ownership plus source namespace/event
        # identity plus per-event sequence.  Omitting the source identity lets
        # two distinct events with the same supplied digest collide on the same
        # disposition_id.  Hashing the identity keeps raw payloads and any
        # cross-owner material out of the identifier.
        identity_token = _hashlib.sha256(
            (
                f"{values['owner_id']}|{values['billing_account_id']}|"
                f"{values['subscription_id']}|{values['source_namespace']}|"
                f"{values['source_event_id']}"
            ).encode("ascii")
        ).hexdigest()[:24]
        disposition_id = f"quarantine-{identity_token}-{sequence}"
        disposition_values = {
            "contract_version": CONTRACT_VERSION,
            "disposition_id": disposition_id,
            "owner_id": values["owner_id"],
            "billing_account_id": values["billing_account_id"],
            "subscription_id": values["subscription_id"],
            "source_namespace": values["source_namespace"],
            "source_event_id": values["source_event_id"],
            "disposition_sequence": sequence,
            "kind": _QUARANTINE_KIND,
            "evidence_reference": values["evidence_reference"],
            "reason": _QUARANTINE_REASON,
            "recorded_at_utc": values["recorded_at_utc"],
            "predecessor_disposition_identity": predecessor,
        }
        disposition_identity = _content_identity(
            "reconciliation-disposition",
            tuple(disposition_values[field] for field in _DISPOSITION_CONTENT_FIELDS),
        )
        self._insert_disposition_row(connection, disposition_values, disposition_identity)

    def _insert_disposition_row(self, connection, values, disposition_identity):
        connection.execute(
            "INSERT INTO reconciliation_disposition ("
            "disposition_id, owner_id, billing_account_id, subscription_id, "
            "source_namespace, source_event_id, disposition_sequence, kind, "
            "evidence_reference, reason, recorded_at_utc, "
            "predecessor_disposition_identity, disposition_identity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                values["disposition_id"],
                values["owner_id"],
                values["billing_account_id"],
                values["subscription_id"],
                values["source_namespace"],
                values["source_event_id"],
                values["disposition_sequence"],
                values["kind"],
                values["evidence_reference"],
                values["reason"],
                values["recorded_at_utc"].isoformat(),
                values["predecessor_disposition_identity"],
                disposition_identity,
            ),
        )

    def _load_journal_row(
        self, connection, owner_id, billing_account_id, subscription_id, sequence
    ):
        row = connection.execute(
            "SELECT sequence, owner_id, billing_account_id, subscription_id, plan_key, "
            "source_namespace, source_event_id, source_event_digest, observation_kind, "
            "effective_date, paid_through, evidence_reference, state, "
            "valid_from_inclusive, valid_until_exclusive, transition_effective_at_utc, "
            "recovery_deadline_exclusive_at_utc, derivation_kind, "
            "withdrawal_attribution, content_identity, predecessor_identity, "
            "recorded_at_utc FROM billing_journal "
            "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
            "AND sequence = ?",
            (owner_id, billing_account_id, subscription_id, sequence),
        ).fetchone()
        if row is None:
            raise LocalBillingRepositoryError("journal row is missing")
        return _journal_record_from_row(row)

    def _verify_chain_and_head(
        self, connection, owner_id, billing_account_id, subscription_id
    ):
        """Validate the complete journal chain and its current head.

        Fails closed on a missing origin/interior/tail sequence, a mismatched
        head state/identity, a broken predecessor link, an orphan journal row
        without a head, or an orphan head without any journal row.  Every row's
        content identity is recomputed (not trusted) through ``_load_journal_row``.
        """
        rows = connection.execute(
            "SELECT sequence FROM billing_journal "
            "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
            "ORDER BY sequence",
            (owner_id, billing_account_id, subscription_id),
        ).fetchall()
        head_row = connection.execute(
            "SELECT sequence, head_identity, state FROM subscription_head "
            "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ?",
            (owner_id, billing_account_id, subscription_id),
        ).fetchone()

        if not rows:
            if head_row is not None:
                raise LocalBillingRepositoryError(
                    "head exists without any journal entry"
                )
            return

        if head_row is None:
            raise LocalBillingRepositoryError(
                "journal entries exist without a current head"
            )

        records = [
            self._load_journal_row(
                connection, owner_id, billing_account_id, subscription_id, row[0]
            )
            for row in rows
        ]

        if records[0].sequence != 1:
            raise LocalBillingRepositoryError("journal chain is missing its origin")
        if records[0].predecessor_identity is not None:
            raise LocalBillingRepositoryError(
                "journal origin must not name a predecessor"
            )

        for index, record in enumerate(records):
            if record.sequence != index + 1:
                raise LocalBillingRepositoryError(
                    "journal chain has a missing interior sequence"
                )
            if index > 0 and record.predecessor_identity != records[index - 1].content_identity:
                raise LocalBillingRepositoryError(
                    "journal chain predecessor link is inconsistent"
                )

        tail = records[-1]
        if head_row[0] != tail.sequence:
            raise LocalBillingRepositoryError("head is inconsistent with journal tail")
        if head_row[1] != tail.content_identity:
            raise LocalBillingRepositoryError(
                "head identity is inconsistent with journal tail"
            )
        if head_row[2] != tail.state:
            raise LocalBillingRepositoryError(
                "head state is inconsistent with journal tail"
            )


def _parse_date(value):
    parsed = _date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise LocalBillingRepositoryError("stored date is non-canonical")
    return parsed


def _parse_utc(value):
    parsed = _datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != _timedelta(0):
        raise LocalBillingRepositoryError("stored datetime is not exact UTC")
    if parsed.isoformat() != value:
        raise LocalBillingRepositoryError("stored datetime is non-canonical")
    return parsed


def _journal_record_from_row(row):
    values = {
        "contract_version": CONTRACT_VERSION,
        "owner_id": row[1],
        "billing_account_id": row[2],
        "subscription_id": row[3],
        "plan_key": row[4],
        "source_namespace": row[5],
        "source_event_id": row[6],
        "source_event_digest": row[7],
        "observation_kind": row[8],
        "effective_date": _parse_date(row[9]),
        "paid_through": None if row[10] is None else _parse_date(row[10]),
        "evidence_reference": row[11],
        "state": row[12],
        "valid_from_inclusive": _parse_date(row[13]),
        "valid_until_exclusive": _parse_date(row[14]),
        "transition_effective_at_utc": _parse_utc(row[15]),
        "recovery_deadline_exclusive_at_utc": (
            None if row[16] is None else _parse_utc(row[16])
        ),
        "derivation_kind": row[17],
        "withdrawal_attribution": row[18],
        "sequence": row[0],
        "predecessor_identity": row[20],
    }
    recomputed = _content_identity(
        "billing-journal",
        tuple(values[field] for field in _JOURNAL_CONTENT_FIELDS),
    )
    if recomputed != row[19]:
        raise LocalBillingRepositoryError("journal content identity does not match")
    return JournalRecord(
        sequence=row[0],
        owner_id=row[1],
        billing_account_id=row[2],
        subscription_id=row[3],
        plan_key=row[4],
        source_namespace=row[5],
        source_event_id=row[6],
        source_event_digest=row[7],
        observation_kind=row[8],
        effective_date=values["effective_date"],
        paid_through=values["paid_through"],
        evidence_reference=row[11],
        state=row[12],
        valid_from_inclusive=values["valid_from_inclusive"],
        valid_until_exclusive=values["valid_until_exclusive"],
        transition_effective_at_utc=values["transition_effective_at_utc"],
        recovery_deadline_exclusive_at_utc=values["recovery_deadline_exclusive_at_utc"],
        derivation_kind=row[17],
        withdrawal_attribution=row[18],
        content_identity=row[19],
        predecessor_identity=row[20],
        recorded_at_utc=_parse_utc(row[21]),
    )


def _journal_record_from_values(values):
    return JournalRecord(
        sequence=values["sequence"],
        owner_id=values["owner_id"],
        billing_account_id=values["billing_account_id"],
        subscription_id=values["subscription_id"],
        plan_key=values["plan_key"],
        source_namespace=values["source_namespace"],
        source_event_id=values["source_event_id"],
        source_event_digest=values["source_event_digest"],
        observation_kind=values["observation_kind"],
        effective_date=values["effective_date"],
        paid_through=values["paid_through"],
        evidence_reference=values["evidence_reference"],
        state=values["state"],
        valid_from_inclusive=values["valid_from_inclusive"],
        valid_until_exclusive=values["valid_until_exclusive"],
        transition_effective_at_utc=values["transition_effective_at_utc"],
        recovery_deadline_exclusive_at_utc=values["recovery_deadline_exclusive_at_utc"],
        derivation_kind=values["derivation_kind"],
        withdrawal_attribution=values["withdrawal_attribution"],
        content_identity=values["content_identity"],
        predecessor_identity=values["predecessor_identity"],
        recorded_at_utc=values["recorded_at_utc"],
    )


def _disposition_record_from_row(row):
    values = {
        "contract_version": CONTRACT_VERSION,
        "disposition_id": row[0],
        "owner_id": row[1],
        "billing_account_id": row[2],
        "subscription_id": row[3],
        "source_namespace": row[4],
        "source_event_id": row[5],
        "disposition_sequence": row[6],
        "kind": row[7],
        "evidence_reference": row[8],
        "reason": row[9],
        "recorded_at_utc": _parse_utc(row[10]),
        "predecessor_disposition_identity": row[11],
    }
    recomputed = _content_identity(
        "reconciliation-disposition",
        tuple(values[field] for field in _DISPOSITION_CONTENT_FIELDS),
    )
    if recomputed != row[12]:
        raise LocalBillingRepositoryError("disposition content identity does not match")
    return ReconciliationDispositionRecord(
        disposition_id=row[0],
        owner_id=row[1],
        billing_account_id=row[2],
        subscription_id=row[3],
        source_namespace=row[4],
        source_event_id=row[5],
        disposition_sequence=row[6],
        kind=row[7],
        evidence_reference=row[8],
        reason=row[9],
        recorded_at_utc=values["recorded_at_utc"],
        predecessor_disposition_identity=row[11],
        disposition_identity=row[12],
    )


def _next_disposition_sequence(
    connection, owner_id, billing_account_id, subscription_id, namespace, event_id
):
    row = connection.execute(
        "SELECT MAX(disposition_sequence) FROM reconciliation_disposition "
        "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
        "AND source_namespace = ? AND source_event_id = ?",
        (owner_id, billing_account_id, subscription_id, namespace, event_id),
    ).fetchone()
    return (row[0] or 0) + 1


def _last_disposition_identity(
    connection, owner_id, billing_account_id, subscription_id, namespace, event_id
):
    row = connection.execute(
        "SELECT disposition_identity FROM reconciliation_disposition "
        "WHERE owner_id = ? AND billing_account_id = ? AND subscription_id = ? "
        "AND source_namespace = ? AND source_event_id = ? "
        "ORDER BY disposition_sequence DESC LIMIT 1",
        (owner_id, billing_account_id, subscription_id, namespace, event_id),
    ).fetchone()
    return None if row is None else row[0]


def _table_exists(connection, table):
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _table_columns(connection, table):
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return tuple(row[1] for row in rows)


def _table_primary_key(connection, table):
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    primary_key = [(row[5], row[1]) for row in rows if row[5] > 0]
    primary_key.sort()
    return tuple(name for _, name in primary_key)


def _index_partial_predicate(connection, index_name):
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    match = _re.search(
        r"\bWHERE\b\s*(.*)\Z", row[0], flags=_re.IGNORECASE | _re.DOTALL
    )
    if match is None:
        return None
    return _re.sub(r"\s+", " ", match.group(1)).strip()


def _table_explicit_indexes(connection, table):
    rows = connection.execute(f"PRAGMA index_list({table})").fetchall()
    indexes = []
    for row in rows:
        # row layout: (seq, name, unique, origin, partial).
        if row[3] != "c":
            continue
        index_name = row[1]
        unique = bool(row[2])
        columns = tuple(
            info[2]
            for info in connection.execute(f"PRAGMA index_info({index_name})").fetchall()
        )
        predicate = _index_partial_predicate(connection, index_name)
        if row[4] and predicate is None:
            # A partial index must expose its WHERE predicate; treat an
            # unparseable partial index as an altered-semantics mismatch.
            predicate = "<partial>"
        indexes.append((index_name, unique, columns, predicate))
    indexes.sort(key=lambda item: item[0])
    return tuple(indexes)


def _table_column_specs(connection, table):
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return tuple((row[1], row[2], bool(row[3]), row[4]) for row in rows)


def _table_unique_constraints(connection, table):
    rows = connection.execute(f"PRAGMA index_list({table})").fetchall()
    return tuple(sorted(row[1] for row in rows if row[3] == "u"))


def _table_check_constraints(connection, table):
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if row is None or row[0] is None:
        raise LocalBillingRepositoryError(
            f"repository schema table {table} is missing"
        )
    return tuple(
        _re.sub(r"\s+", " ", match.group(0)).strip()
        for match in _re.finditer(r"\bCHECK\s*\(", row[0], flags=_re.IGNORECASE)
    )


def _table_foreign_keys(connection, table):
    return tuple(connection.execute(f"PRAGMA foreign_key_list({table})").fetchall())


def _verify_schema(connection):
    try:
        meta_rows = connection.execute(
            "SELECT key, value FROM repository_meta"
        ).fetchall()
    except _sqlite3.Error as exc:
        raise LocalBillingRepositoryError(
            "repository metadata is missing or unreadable"
        ) from exc
    meta = dict(meta_rows)
    if meta.get("schema_version") != SCHEMA_VERSION:
        raise LocalBillingRepositoryError("unsupported repository schema version")
    if meta.get("schema_digest") != _SCHEMA_DIGEST:
        raise LocalBillingRepositoryError(
            "repository schema digest mismatch (partial or altered schema)"
        )
    user_tables = tuple(
        sorted(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )
    )
    if user_tables != tuple(sorted(_EXPECTED_COLUMNS)):
        raise LocalBillingRepositoryError(
            "repository schema has unexpected or missing tables"
        )
    for table, columns in _EXPECTED_COLUMNS.items():
        if _table_columns(connection, table) != columns:
            raise LocalBillingRepositoryError(
                f"repository schema table {table} is inconsistent"
            )
        if _table_column_specs(connection, table) != _EXPECTED_COLUMN_SPECS[table]:
            raise LocalBillingRepositoryError(
                f"repository schema table {table} column semantics are inconsistent"
            )
        if _table_primary_key(connection, table) != _EXPECTED_PRIMARY_KEYS[table]:
            raise LocalBillingRepositoryError(
                f"repository schema table {table} primary key is inconsistent"
            )
        if _table_unique_constraints(connection, table):
            raise LocalBillingRepositoryError(
                f"repository schema table {table} has unexpected unique constraints"
            )
        if _table_check_constraints(connection, table):
            raise LocalBillingRepositoryError(
                f"repository schema table {table} has unexpected check constraints"
            )
        if _table_foreign_keys(connection, table):
            raise LocalBillingRepositoryError(
                f"repository schema table {table} has unexpected foreign keys"
            )
        expected_indexes = tuple(sorted(_EXPECTED_EXPLICIT_INDEXES[table]))
        if _table_explicit_indexes(connection, table) != expected_indexes:
            raise LocalBillingRepositoryError(
                f"repository schema table {table} indexes are inconsistent"
            )
    actual_objects = {}
    for object_type, name, sql in connection.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND type IN ('table', 'index') "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall():
        actual_objects[(object_type, name)] = _normalise_schema_sql(sql)
    if actual_objects != _EXPECTED_SCHEMA_OBJECTS:
        raise LocalBillingRepositoryError(
            "repository schema declaration is inconsistent"
        )
    executable_schema = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type IN ('trigger', 'view') AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if executable_schema:
        raise LocalBillingRepositoryError(
            "repository schema has unexpected executable schema"
        )
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    except _sqlite3.Error as exc:
        raise LocalBillingRepositoryError("repository integrity check failed") from exc
    if integrity != "ok":
        raise LocalBillingRepositoryError("repository integrity check failed")


__all__ = (
    "CONTRACT_VERSION",
    "DERIVATION_KINDS",
    "FACT_STATES",
    "JournalRecord",
    "LocalBillingRepository",
    "LocalBillingRepositoryError",
    "OBSERVATION_KINDS",
    "PLAN_KEYS",
    "RECONCILIATION_DISPOSITION_KINDS",
    "RECONCILIATION_DISPOSITION_REASONS",
    "RECORD_CLASSIFICATION",
    "REPOSITORY_PURPOSE",
    "SCHEMA_VERSION",
    "SubscriptionHeadRecord",
    "ReconciliationDispositionRecord",
    "WITHDRAWAL_ATTRIBUTIONS",
)
