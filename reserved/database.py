"""
SQLite persistence layer for Reserved.

Tables
------
schema_version              — single-row schema-version stamp; updated by init_db()
                              after applying pending migrations

users                       — stable user identity keyed by Clerk user_id (or demo
                              sentinel); all V2 data references this table via user_id FK

feedback_submissions        — one row per feedback form submission (public / route /)

early_access_registrations  — one row per early-access sign-up, unique on email
                              (public / route /)

bank_connections            — one row per Yapily consent authorisation; a user may
                              have multiple connections (different banks or
                              re-authorisations)

connected_accounts          — one row per Yapily account returned for a connection;
                              a single consent may cover multiple accounts

transactions                — classified transactions from ingestion; upserted on
                              (account_id, yapily_tx_id) so re-ingestion is safe;
                              overriding a category sets method='manual'

transaction_overrides       — audit trail of manual category corrections; the
                              current category lives in transactions.category;
                              this table records the full history

user_profiles               — sole-trader settings (income estimate, pension,
                              student loan plan, etc.) keyed by session_key and
                              optionally by user_id (WS5+)

tax_calculations            — persisted engine outputs; populated by the tax engine
                              after a calculation is requested

invoices                    — invoice records for the matching engine; supports
                              import from accounting software and manual entry

invoice_matches             — one row per matching attempt; records the matched
                              transaction(s), confidence score, status, and method

Conventions
-----------
All timestamps are stored as ISO-8601 strings in UTC.
IP addresses are stored as a short SHA-256 hash (first 16 hex chars) for
anonymous deduplication; the raw IP is never persisted.
Foreign keys are enforced at connection time via PRAGMA foreign_keys=ON.
Write-ahead logging (PRAGMA journal_mode=WAL) is used for better concurrency.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Path ──────────────────────────────────────────────────────────────────────

_INSTANCE = Path(__file__).resolve().parent.parent / "instance"
_DB_FILE  = _INSTANCE / "reserved.db"


def get_db_path() -> Path:
    return _DB_FILE


def ping_db() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with _connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


# ── Connection helper ─────────────────────────────────────────────────────────

@contextmanager
def _connection():
    _INSTANCE.mkdir(exist_ok=True)
    conn = sqlite3.connect(_DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
-- ── Schema version ─────────────────────────────────────────────────────────────
-- Single-row table that records which migrations have been applied.
-- init_db() stamps this after applying all pending migrations.
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- ── Workstream 5: Users ────────────────────────────────────────────────────────
-- Stable user identity keyed by Clerk user_id (or demo sentinel).
-- All V2 data (bank_connections, user_profiles, tax_calculations) references
-- this table via user_id FK.  session_key columns are kept for backward
-- compatibility; user_id is the authoritative identifier from WS5 onward.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    clerk_user_id TEXT    NOT NULL UNIQUE,
    email         TEXT,
    display_name  TEXT,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_submissions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_at TEXT    NOT NULL,
    intuitive    INTEGER,
    useful       INTEGER,
    trustworthy  INTEGER,
    area         TEXT,
    comments     TEXT,
    would_use    TEXT,
    ip_hash      TEXT,
    email        TEXT,
    browser      TEXT,
    device       TEXT,
    page_url     TEXT
);

CREATE TABLE IF NOT EXISTS early_access_registrations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_at     TEXT NOT NULL,
    name             TEXT NOT NULL,
    email            TEXT NOT NULL,
    occupation       TEXT,
    working_style    TEXT,
    referral_source  TEXT,
    comments         TEXT,
    ip_hash          TEXT,
    UNIQUE(email COLLATE NOCASE)
);

-- ── Workstream 4: Bank connections ────────────────────────────────────────────
-- One row per Yapily consent authorisation. A user may have multiple connections
-- (different banks or re-authorisations). Each connection is scoped to a user
-- via the user_id FK (added in _MIGRATIONS[1]). session_key is retained only
-- for backwards-compatible migration of pre-WS5 rows via migrate_session_to_user().
CREATE TABLE IF NOT EXISTS bank_connections (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT    NOT NULL,
    institution_id   TEXT    NOT NULL,
    institution_name TEXT    NOT NULL,
    consent_token    TEXT    NOT NULL UNIQUE,
    consent_id       TEXT,
    status           TEXT    NOT NULL DEFAULT 'active',
    -- status values: active | expiring | expired | revoked
    expires_at       TEXT,
    session_key      TEXT
);

-- ── Connected bank accounts ───────────────────────────────────────────────────
-- One row per Yapily account returned for a connection. A single consent may
-- cover multiple accounts (joint, savings, current).
CREATE TABLE IF NOT EXISTS connected_accounts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id     INTEGER NOT NULL REFERENCES bank_connections(id) ON DELETE CASCADE,
    yapily_account_id TEXT    NOT NULL UNIQUE,
    account_type      TEXT,
    nickname          TEXT,
    currency          TEXT    NOT NULL DEFAULT 'GBP',
    sort_code         TEXT,
    account_number    TEXT,
    balance           REAL,
    balance_at        TEXT    -- ISO-8601 timestamp of last balance snapshot
);

-- ── Transactions ──────────────────────────────────────────────────────────────
-- Classified transactions from ingestion.py. Upserted on (account_id, yapily_tx_id)
-- so re-ingestion is safe. Overriding a category sets method='manual'.
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    yapily_tx_id    TEXT    NOT NULL,
    tx_date         TEXT    NOT NULL,
    description     TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    currency        TEXT    NOT NULL DEFAULT 'GBP',
    category        TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    method          TEXT    NOT NULL DEFAULT 'rules',
    -- method values: rules | ai | manual
    subcategory     TEXT,
    tax_relevant    INTEGER NOT NULL DEFAULT 0,  -- 0=false 1=true
    raw_json        TEXT,
    ingested_at     TEXT    NOT NULL,
    UNIQUE(account_id, yapily_tx_id)
);

-- ── Transaction overrides ─────────────────────────────────────────────────────
-- Audit trail of manual category corrections. The current category lives in
-- transactions.category; this table records the full history.
CREATE TABLE IF NOT EXISTS transaction_overrides (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id    INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    overridden_at     TEXT    NOT NULL,
    original_category TEXT    NOT NULL,
    new_category      TEXT    NOT NULL,
    note              TEXT
);

-- ── User profiles ─────────────────────────────────────────────────────────────
-- Sole-trader settings (income estimate, pension, student loan plan, etc.).
-- Keyed by session_key for backwards-compatible migration of pre-auth rows.
-- User accounts were introduced in WS5; new rows are also linked via user_id
-- (added as a nullable FK column by the schema migration in _MIGRATIONS[1]).
-- session_key is retained so that pre-WS5 rows can be migrated forward via
-- migrate_session_to_user() and is not the authoritative identifier.
CREATE TABLE IF NOT EXISTS user_profiles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key             TEXT    NOT NULL UNIQUE,
    updated_at              TEXT    NOT NULL,
    display_name            TEXT,
    tax_year                TEXT,
    income_estimate         REAL,
    pension_contribution    REAL,
    student_loan_plans      TEXT,  -- JSON array e.g. '["plan2"]'
    notes                   TEXT,
    child_benefit_children  INTEGER DEFAULT 0,
    child_benefit_annual    REAL    -- explicit override; NULL = use standard rates
);

-- ── HICBC partner estimates (October v1) ────────────────────────────────────────
-- One row per (user_id, tax_year) holds the user's bounded manual HICBC inputs:
-- Child Benefit facts and the partner income estimate used only for the
-- responsibility comparison.  Money/ANI values are stored as canonical Decimal
-- strings (TEXT), never binary floating point, so validation-critical values
-- round-trip without precision loss.  The partner's raw figures are persisted
-- only to serve the internal comparison and are never returned in a
-- customer-facing payload.
CREATE TABLE IF NOT EXISTS hicbc_estimates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year                TEXT    NOT NULL,
    receives_child_benefit  INTEGER,              -- legacy; superseded by child_benefit_claimant
    child_benefit_claimant  TEXT,                 -- NULL='person'|'partner'|'none'; NULL=unknown
    child_benefit_children  INTEGER NOT NULL DEFAULT 0,
    child_benefit_annual    TEXT,                 -- Decimal string; NULL = derive from children/weeks
    child_benefit_weeks_entitled INTEGER,         -- NULL=unknown; otherwise 0..53
    has_relevant_partner    INTEGER,              -- NULL=unknown, 0=no, 1=yes
    relationship_covers_full_year INTEGER,        -- NULL=unknown, 0=status changed, 1=status held full year
    partner_status_period_semantics TEXT,         -- NULL=legacy/unknown; 'status_answer_full_year'=defined semantics
    representation          TEXT,                 -- NULL | 'point' | 'range'
    partner_ani_point       TEXT,                 -- Decimal string
    partner_ani_low         TEXT,                 -- Decimal string
    partner_ani_high        TEXT,                 -- Decimal string
    evidence_id             TEXT    NOT NULL,
    source_kind             TEXT    NOT NULL DEFAULT 'user_supplied_partner_estimate',
    observed_at             TEXT    NOT NULL,
    confirmed_at            TEXT,
    completeness            TEXT    NOT NULL DEFAULT 'complete_for_purpose',
    recency_state           TEXT    NOT NULL DEFAULT 'current',
    created_at              TEXT    NOT NULL,
    updated_at              TEXT    NOT NULL,
    UNIQUE(user_id, tax_year)
);

-- ── HICBC linked-account consent ──────────────────────────────────────────────
-- A mutually consented, HICBC-only link between two Reserved users.  user_low_id
-- and user_high_id are the normalised (ordered) pair so a pair has at most one
-- row per tax year.  status is 'active' or 'revoked'.  No partner financial
-- value is stored here — only identity, consent state, purpose, period facts and
-- timestamps.  Relationship start is NULL until the users confirm it (unknown
-- relationship-period facts must not be silently treated as full-year).
CREATE TABLE IF NOT EXISTS hicbc_links (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_low_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_high_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year                TEXT    NOT NULL,
    purpose                 TEXT    NOT NULL DEFAULT 'hicbc_responsibility',
    status                  TEXT    NOT NULL,
    initiator_id            INTEGER NOT NULL,
    relationship_started_at TEXT,
    created_at              TEXT    NOT NULL,
    accepted_at             TEXT    NOT NULL,
    revoked_at              TEXT,
    revoked_by              INTEGER,
    permission_cycle        INTEGER NOT NULL DEFAULT 1 CHECK(permission_cycle >= 1),
    UNIQUE(user_low_id, user_high_id, tax_year)
);

-- ── HICBC link invitations ────────────────────────────────────────────────────
-- Single-use, short-lived, high-entropy invitation tokens.  Only the SHA-256
-- hash of the token is stored; the raw token is returned to the creator exactly
-- once for out-of-band sharing.  No partner financial value is stored.
CREATE TABLE IF NOT EXISTS hicbc_link_invitations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash   TEXT    NOT NULL UNIQUE,
    creator_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year     TEXT    NOT NULL,
    purpose      TEXT    NOT NULL DEFAULT 'hicbc_responsibility',
    status       TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    accepted_at  TEXT,
    accepted_by  INTEGER,
    link_id      INTEGER
);

-- ── HICBC link mutual permission ─────────────────────────────────────────────
-- One row per (link, participant) records the participant's separate,
-- affirmative, versioned linked-HICBC permission.  Missing rows (or a missing
-- notice_version) mean versioned mutual permission has not yet been established
-- and linked evidence must not be treated as adequately consented.
CREATE TABLE IF NOT EXISTS hicbc_link_consents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id        INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notice_version TEXT    NOT NULL,
    consented_at   TEXT    NOT NULL,
    withdrawn_at   TEXT,
    UNIQUE(link_id, user_id)
);

-- Append-only audit evidence for the bounded linked-HICBC permission lifecycle.
-- Current authority continues to live in hicbc_links + hicbc_link_consents;
-- these events are history only and must never revive permission.
CREATE TABLE IF NOT EXISTS hicbc_permission_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id        INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
    permission_cycle INTEGER NOT NULL CHECK(permission_cycle >= 1),
    event_type     TEXT    NOT NULL CHECK(event_type IN ('consent', 'withdraw', 'unlink', 'relink')),
    actor_user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    occurred_at    TEXT    NOT NULL,
    notice_version TEXT    NOT NULL,
    UNIQUE(link_id, permission_cycle, event_type, actor_user_id, notice_version)
);

-- Short-lived opaque bindings between a rendered permission form and the exact
-- active link cycle/participant/tax year/notice it represented.  Only a hash of
-- the browser token is stored.
CREATE TABLE IF NOT EXISTS hicbc_permission_form_bindings (
    token_hash       TEXT    PRIMARY KEY,
    link_id          INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
    permission_cycle INTEGER NOT NULL CHECK(permission_cycle >= 1),
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year         TEXT    NOT NULL,
    notice_version   TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    expires_at       TEXT    NOT NULL
);

-- ── Tax optimisation saved scenarios ─────────────────────────────────────────
-- Stores pension-scenario comparisons the user has chosen to save from the
-- Optimise page.  Linked to users (not profiles) so they survive profile edits.
CREATE TABLE IF NOT EXISTS optimise_scenarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opportunity  TEXT    NOT NULL,   -- "PA_TAPER" | "HICBC"
    label        TEXT,               -- user-provided name (optional)
    tax_year     TEXT,               -- applicable tax year; NULL only for pre-migration records
    inputs_json  TEXT    NOT NULL,   -- JSON: projected_income, pension, extra, annual_cb
    outputs_json TEXT    NOT NULL,   -- JSON: before, after, it_reduction, hicbc_reduction, total
    saved_at     TEXT    NOT NULL
);

-- ── Schema stub: tax calculations ─────────────────────────────────────────────
-- Reserved for a future workstream that persists engine outputs.
-- Populated by the tax engine; not written by WS4.
CREATE TABLE IF NOT EXISTS tax_calculations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    calculated_at   TEXT    NOT NULL,
    session_key     TEXT,
    tax_year        TEXT    NOT NULL,
    income          REAL,
    income_tax      REAL,
    national_ins    REAL,
    student_loan    REAL,
    total_liability REAL,
    inputs_json     TEXT    -- full profile snapshot as JSON
);

-- ── Schema stub: accounting software invoice sources ──────────────────────────
-- Reserved for FreeAgent / Xero / QuickBooks invoice ingestion (post-WS4).
-- provider values: freeagent | xero | quickbooks
CREATE TABLE IF NOT EXISTS invoice_sources (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    provider     TEXT NOT NULL,
    external_id  TEXT NOT NULL,
    invoice_date TEXT,
    gross_amount REAL,
    status       TEXT,
    raw_json     TEXT,
    UNIQUE(provider, external_id)
);

-- ── Workstream 6: Invoices ─────────────────────────────────────────────────────
-- One row per invoice raised by the user.
-- status values: unpaid | partially_paid | paid | overpaid | void
CREATE TABLE IF NOT EXISTS invoices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reference    TEXT    NOT NULL,
    client_name  TEXT    NOT NULL,
    amount_due   REAL    NOT NULL,
    currency     TEXT    NOT NULL DEFAULT 'GBP',
    issue_date   TEXT    NOT NULL,  -- YYYY-MM-DD
    due_date     TEXT    NOT NULL,  -- YYYY-MM-DD
    status       TEXT    NOT NULL DEFAULT 'unpaid',
    notes        TEXT,
    created_at   TEXT    NOT NULL,
    UNIQUE(user_id, reference)
);

-- ── Rate-limit log ───────────────────────────────────────────────────────────
-- Persistent store for IP-keyed rate-limit attempts.  Replaces the previous
-- process-local in-memory dict, making limits survive worker restarts and
-- share state correctly across multiple Gunicorn workers.
-- key_hash is SHA-256(action:ip) truncated to 24 hex chars — raw IPs never stored.
CREATE TABLE IF NOT EXISTS rate_limit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash     TEXT    NOT NULL,
    action       TEXT    NOT NULL,
    attempted_at TEXT    NOT NULL,
    success      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_rate_limit ON rate_limit_log(key_hash, action, attempted_at);

-- ── Workstream 6: Invoice matches ──────────────────────────────────────────────
-- One row per invoice-transaction link produced by the matching engine.
-- Multiple rows per invoice are allowed (e.g. partial or multiple payments).
-- transaction_id is nullable (NULL for UNMATCHED) and intentionally has no FK
-- constraint: matching works on both DB-persisted transactions (with a real
-- transactions.id) and in-memory demo transactions (no DB row).  The relationship
-- is semantic rather than referentially enforced.
-- review_state values: pending_review | confirmed | rejected
CREATE TABLE IF NOT EXISTS invoice_matches (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id     INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    transaction_id INTEGER,   -- soft reference to transactions.id (no FK — see note above)
    matched_at     TEXT    NOT NULL,
    status         TEXT    NOT NULL,
    confidence     INTEGER NOT NULL,
    method         TEXT    NOT NULL,
    explanation    TEXT    NOT NULL,
    matched_amount REAL    NOT NULL,
    review_state   TEXT    NOT NULL DEFAULT 'pending_review'
);

-- Customer-confirmed structured PAYE facts. Raw payslips, employer names,
-- payroll references and National Insurance numbers are deliberately absent.
CREATE TABLE IF NOT EXISTS paye_manual_entries (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year          TEXT    NOT NULL,
    employment_slot   INTEGER NOT NULL CHECK(employment_slot BETWEEN 1 AND 20),
    evidence_id       TEXT    NOT NULL UNIQUE,
    source_kind       TEXT    NOT NULL CHECK(source_kind = 'customer_confirmed_manual'),
    provenance        TEXT    NOT NULL,
    gross_to_date     TEXT,
    tax_paid_to_date  TEXT,
    tax_code          TEXT,
    pay_frequency     TEXT    NOT NULL,
    pension_treatment TEXT    NOT NULL,
    effective_through TEXT    NOT NULL,
    observed_on       TEXT    NOT NULL,
    completeness      TEXT    NOT NULL CHECK(completeness IN ('partial', 'unknown')),
    replaced_at       TEXT,
    deleted_at        TEXT,
    created_at        TEXT    NOT NULL,
    UNIQUE(user_id, tax_year, evidence_id)
);
CREATE INDEX IF NOT EXISTS idx_paye_manual_entries_owner
    ON paye_manual_entries(user_id, tax_year, employment_slot, deleted_at, replaced_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_paye_manual_entries_active_slot
    ON paye_manual_entries(user_id, tax_year, employment_slot)
    WHERE replaced_at IS NULL AND deleted_at IS NULL;

-- ── W9: minimised owner-bound annual positions ──────────────────────────────
-- This schema intentionally has no raw payslip or provider-payload column.
CREATE TABLE IF NOT EXISTS owner_business_memberships (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_reference   TEXT NOT NULL,
    membership_reference TEXT NOT NULL UNIQUE,
    membership_version   INTEGER NOT NULL CHECK(membership_version >= 1),
    status               TEXT NOT NULL CHECK(status IN ('active', 'revoked')),
    authority_expires_at TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    revoked_at           TEXT,
    UNIQUE(user_id, business_reference)
);

CREATE TABLE IF NOT EXISTS annual_position_records (
    record_identity        TEXT PRIMARY KEY,
    user_id                INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_reference     TEXT NOT NULL,
    tax_year               TEXT NOT NULL,
    nation                 TEXT NOT NULL,
    record_purpose         TEXT NOT NULL,
    record_version         INTEGER NOT NULL CHECK(record_version >= 1),
    predecessor_identity   TEXT REFERENCES annual_position_records(record_identity),
    governance_fingerprint TEXT NOT NULL,
    envelope_json          TEXT NOT NULL,
    envelope_sha256        TEXT NOT NULL,
    state                  TEXT NOT NULL CHECK(state IN ('current', 'superseded', 'deleted')),
    created_at             TEXT NOT NULL,
    deleted_at             TEXT,
    UNIQUE(user_id, business_reference, tax_year, nation, record_purpose, record_version)
);
CREATE UNIQUE INDEX IF NOT EXISTS annual_position_one_current_head
    ON annual_position_records(user_id, business_reference, tax_year, nation, record_purpose)
    WHERE state = 'current';

CREATE TABLE IF NOT EXISTS annual_position_evidence_references (
    record_identity      TEXT NOT NULL REFERENCES annual_position_records(record_identity) ON DELETE CASCADE,
    position             INTEGER NOT NULL CHECK(position >= 0),
    evidence_reference   TEXT NOT NULL,
    PRIMARY KEY(record_identity, position),
    UNIQUE(record_identity, evidence_reference)
);

CREATE TABLE IF NOT EXISTS annual_position_lifecycle_events (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    record_identity      TEXT REFERENCES annual_position_records(record_identity) ON DELETE SET NULL,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_kind           TEXT NOT NULL CHECK(event_kind IN ('created', 'superseded', 'erasure_planned', 'erased')),
    audit_reference      TEXT NOT NULL,
    occurred_at          TEXT NOT NULL
);
"""


# ── Schema versioning ────────────────────────────────────────────────────────
#
# How to add a migration
# ----------------------
# 1. Increment _SCHEMA_VERSION by 1.
# 2. Add a new entry to _MIGRATIONS keyed by that new version number.
# 3. List the SQL statements in order.  Each is wrapped in try/except so that
#    "column already exists" errors are treated as a no-op — this keeps
#    init_db() idempotent on both fresh installs and existing databases.
#
# Rules
# -----
# - Use only additive changes (ADD COLUMN, CREATE TABLE IF NOT EXISTS).
#   Destructive changes (DROP COLUMN, RENAME) require a manual migration
#   script outside this mechanism.
# - Never edit a migration that has already shipped.  Add a new version instead.
# - The DDL block above always reflects the full target schema; migrations
#   handle upgrade paths for databases created before the current DDL.
#
_SCHEMA_VERSION = 15   # increment when adding new migration entries below

_MIGRATIONS: dict[int, list[str]] = {
    # Version 1 — Workstream 5: add user_id FK to pre-existing tables.
    # (invoices and invoice_matches are new WS6 tables; no migration needed.)
    1: [
        "ALTER TABLE bank_connections ADD COLUMN user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE user_profiles    ADD COLUMN user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE tax_calculations  ADD COLUMN user_id INTEGER REFERENCES users(id)",
    ],
    # Version 2 — Workstream 8: add richer context columns to public submission
    # tables so the founder dashboard can show browser, device, page, email
    # (feedback) and referral source (early access).
    2: [
        "ALTER TABLE feedback_submissions        ADD COLUMN email    TEXT",
        "ALTER TABLE feedback_submissions        ADD COLUMN browser  TEXT",
        "ALTER TABLE feedback_submissions        ADD COLUMN device   TEXT",
        "ALTER TABLE feedback_submissions        ADD COLUMN page_url TEXT",
        "ALTER TABLE early_access_registrations  ADD COLUMN referral_source TEXT",
    ],
    # Version 3 — Persistent rate-limit log; replaces process-local in-memory
    # dict in founder.py so limits survive restarts and span all workers.
    3: [
        """CREATE TABLE IF NOT EXISTS rate_limit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash     TEXT    NOT NULL,
            action       TEXT    NOT NULL,
            attempted_at TEXT    NOT NULL,
            success      INTEGER NOT NULL DEFAULT 0
        )""",
        "CREATE INDEX IF NOT EXISTS idx_rate_limit ON rate_limit_log(key_hash, action, attempted_at)",
    ],
    # Version 4 — Optimise feature: Child Benefit columns on user_profiles and
    # new optimise_scenarios table for saving pension-contribution comparisons.
    4: [
        "ALTER TABLE user_profiles ADD COLUMN child_benefit_children INTEGER DEFAULT 0",
        "ALTER TABLE user_profiles ADD COLUMN child_benefit_annual    REAL",
        """CREATE TABLE IF NOT EXISTS optimise_scenarios (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            opportunity  TEXT    NOT NULL,
            label        TEXT,
            inputs_json  TEXT    NOT NULL,
            outputs_json TEXT    NOT NULL,
            saved_at     TEXT    NOT NULL
        )""",
    ],
    # Version 5 — Persist the applicable tax year with saved Explore scenarios so
    # a saved comparison cannot silently lose the year it was calculated under.
    5: [
        "ALTER TABLE optimise_scenarios ADD COLUMN tax_year TEXT",
    ],
    # Version 6 — Post-v1 HICBC partner estimates: Child Benefit facts plus the
    # partner ANI estimate used only for the responsibility comparison.
    6: [
        """CREATE TABLE IF NOT EXISTS hicbc_estimates (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tax_year                TEXT    NOT NULL,
            receives_child_benefit  INTEGER,
            child_benefit_children  INTEGER NOT NULL DEFAULT 0,
            child_benefit_annual    TEXT,
            has_relevant_partner    INTEGER,
            representation          TEXT,
            partner_ani_point       TEXT,
            partner_ani_low         TEXT,
            partner_ani_high        TEXT,
            evidence_id             TEXT    NOT NULL,
            source_kind             TEXT    NOT NULL DEFAULT 'user_supplied_partner_estimate',
            observed_at             TEXT    NOT NULL,
            confirmed_at            TEXT,
            completeness            TEXT    NOT NULL DEFAULT 'complete_for_purpose',
            recency_state           TEXT    NOT NULL DEFAULT 'current',
            created_at              TEXT    NOT NULL,
            updated_at              TEXT    NOT NULL,
            UNIQUE(user_id, tax_year)
        )""",
    ],
    # Version 7 — HICBC linked-account consent: a mutually consented, HICBC-only
    # link between two Reserved users plus single-use invitation tokens.
    7: [
        """CREATE TABLE IF NOT EXISTS hicbc_links (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_low_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            user_high_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tax_year                TEXT    NOT NULL,
            purpose                 TEXT    NOT NULL DEFAULT 'hicbc_responsibility',
            status                  TEXT    NOT NULL,
            initiator_id            INTEGER NOT NULL,
            relationship_started_at TEXT,
            created_at              TEXT    NOT NULL,
            accepted_at             TEXT    NOT NULL,
            revoked_at              TEXT,
            revoked_by              INTEGER,
            UNIQUE(user_low_id, user_high_id, tax_year)
        )""",
        """CREATE TABLE IF NOT EXISTS hicbc_link_invitations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash   TEXT    NOT NULL UNIQUE,
            creator_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tax_year     TEXT    NOT NULL,
            purpose      TEXT    NOT NULL DEFAULT 'hicbc_responsibility',
            status       TEXT    NOT NULL,
            expires_at   TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,
            accepted_at  TEXT,
            accepted_by  INTEGER,
            link_id      INTEGER
        )""",
    ],
    # Version 8 — HICBC linked-account versioned mutual permission.  Invitation
    # acceptance alone no longer counts as launch-adequate consent; each
    # participant must separately, affirmatively consent to a recorded notice.
    8: [
        """CREATE TABLE IF NOT EXISTS hicbc_link_consents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id        INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
            user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notice_version TEXT    NOT NULL,
            consented_at   TEXT    NOT NULL,
            withdrawn_at   TEXT,
            UNIQUE(link_id, user_id)
        )""",
    ],
    # Version 9 — HICBC claimant identity and bounded period facts.  The manual
    # estimate must record who is the Child Benefit claimant (person / partner /
    # none), the number of Child Benefit entitlement weeks, and whether the
    # relationship covers the full tax year, so the engine never silently treats
    # a mid-year relationship or partial entitlement as a full-year fact.
    9: [
        "ALTER TABLE hicbc_estimates ADD COLUMN child_benefit_claimant TEXT",
        "ALTER TABLE hicbc_estimates ADD COLUMN child_benefit_weeks_entitled INTEGER",
        "ALTER TABLE hicbc_estimates ADD COLUMN relationship_covers_full_year INTEGER",
    ],
    # Version 10 — distinguish the corrected customer-input semantics from any
    # pre-correction row.  Existing rows remain NULL and therefore fail closed
    # until the customer reconfirms whether their preceding partner-status
    # answer was true for the whole tax year.
    10: [
        "ALTER TABLE hicbc_estimates ADD COLUMN partner_status_period_semantics TEXT",
    ],
    # Version 11 — linked-HICBC permission cycles and append-only lifecycle
    # evidence.  A cycle advances on re-link so permission from an earlier link
    # cannot silently revive.
    11: [
        "ALTER TABLE hicbc_links ADD COLUMN permission_cycle INTEGER NOT NULL DEFAULT 1 CHECK(permission_cycle >= 1)",
        """CREATE TABLE IF NOT EXISTS hicbc_permission_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id          INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
            permission_cycle INTEGER NOT NULL CHECK(permission_cycle >= 1),
            event_type       TEXT    NOT NULL CHECK(event_type IN ('consent', 'withdraw', 'unlink', 'relink')),
            actor_user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            occurred_at      TEXT    NOT NULL,
            notice_version   TEXT    NOT NULL,
            UNIQUE(link_id, permission_cycle, event_type, actor_user_id, notice_version)
        )""",
        """CREATE TABLE IF NOT EXISTS hicbc_permission_form_bindings (
            token_hash       TEXT    PRIMARY KEY,
            link_id          INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
            permission_cycle INTEGER NOT NULL CHECK(permission_cycle >= 1),
            user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tax_year         TEXT    NOT NULL,
            notice_version   TEXT    NOT NULL,
            created_at       TEXT    NOT NULL,
            expires_at       TEXT    NOT NULL
        )""",
    ],
    # Version 12 — owner-bound, minimised annual-position projections.  These
    # rows deliberately contain only the reviewed structural projection and
    # references; originals such as payslips and provider payloads do not have
    # a column in this schema.
    12: [
        """CREATE TABLE IF NOT EXISTS owner_business_memberships (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            business_reference   TEXT NOT NULL,
            membership_reference TEXT NOT NULL UNIQUE,
            membership_version   INTEGER NOT NULL CHECK(membership_version >= 1),
            status               TEXT NOT NULL CHECK(status IN ('active', 'revoked')),
            created_at           TEXT NOT NULL,
            revoked_at           TEXT,
            UNIQUE(user_id, business_reference)
        )""",
        """CREATE TABLE IF NOT EXISTS annual_position_records (
            record_identity      TEXT PRIMARY KEY,
            user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            business_reference   TEXT NOT NULL,
            tax_year             TEXT NOT NULL,
            nation               TEXT NOT NULL,
            record_purpose       TEXT NOT NULL,
            record_version       INTEGER NOT NULL CHECK(record_version >= 1),
            predecessor_identity TEXT REFERENCES annual_position_records(record_identity),
            governance_fingerprint TEXT NOT NULL,
            envelope_json        TEXT NOT NULL,
            envelope_sha256      TEXT NOT NULL,
            state                TEXT NOT NULL CHECK(state IN ('current', 'superseded', 'deleted')),
            created_at           TEXT NOT NULL,
            deleted_at           TEXT,
            UNIQUE(user_id, business_reference, tax_year, nation, record_purpose, record_version)
        )""",
        """CREATE UNIQUE INDEX IF NOT EXISTS annual_position_one_current_head
            ON annual_position_records(user_id, business_reference, tax_year, nation, record_purpose)
            WHERE state = 'current'""",
        """CREATE TABLE IF NOT EXISTS annual_position_evidence_references (
            record_identity      TEXT NOT NULL REFERENCES annual_position_records(record_identity) ON DELETE CASCADE,
            position             INTEGER NOT NULL CHECK(position >= 0),
            evidence_reference   TEXT NOT NULL,
            PRIMARY KEY(record_identity, position),
            UNIQUE(record_identity, evidence_reference)
        )""",
        """CREATE TABLE IF NOT EXISTS annual_position_lifecycle_events (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            record_identity      TEXT REFERENCES annual_position_records(record_identity) ON DELETE SET NULL,
            user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_kind           TEXT NOT NULL CHECK(event_kind IN ('created', 'superseded', 'erasure_planned', 'erased')),
            audit_reference      TEXT NOT NULL,
            occurred_at          TEXT NOT NULL
        )""",
    ],
    # Version 13 — append-only, redacted durable-record read audit.  This is
    # separate from lifecycle events so v12's shipped event-kind constraint is
    # never rewritten destructively.
    13: [
        """CREATE TABLE IF NOT EXISTS annual_position_read_audit (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            record_identity      TEXT NOT NULL REFERENCES annual_position_records(record_identity) ON DELETE CASCADE,
            user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            business_reference   TEXT NOT NULL,
            audit_reference      TEXT NOT NULL,
            occurred_at          TEXT NOT NULL
        )""",
    ],
    # Version 14 — authority lifetime is a required runtime access control.
    # Existing rows receive NULL and therefore fail closed until independently
    # renewed; no expiry date is invented during migration.
    14: [
        "ALTER TABLE owner_business_memberships ADD COLUMN authority_expires_at TEXT",
    ],
    # Version 15 — structured, owner-bound manual PAYE evidence. This stores
    # no raw document or direct employer identifiers; replacement/deletion are
    # explicit state transitions and user deletion cascades through the FK.
    15: [
        """CREATE TABLE IF NOT EXISTS paye_manual_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tax_year TEXT NOT NULL,
            employment_slot INTEGER NOT NULL CHECK(employment_slot BETWEEN 1 AND 20),
            evidence_id TEXT NOT NULL UNIQUE,
            source_kind TEXT NOT NULL CHECK(source_kind = 'customer_confirmed_manual'),
            provenance TEXT NOT NULL,
            gross_to_date TEXT, tax_paid_to_date TEXT, tax_code TEXT,
            pay_frequency TEXT NOT NULL, pension_treatment TEXT NOT NULL,
            effective_through TEXT NOT NULL, observed_on TEXT NOT NULL,
            completeness TEXT NOT NULL CHECK(completeness IN ('partial', 'unknown')),
            replaced_at TEXT, deleted_at TEXT, created_at TEXT NOT NULL,
            UNIQUE(user_id, tax_year, evidence_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_paye_manual_entries_owner ON paye_manual_entries(user_id, tax_year, employment_slot, deleted_at, replaced_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_paye_manual_entries_active_slot ON paye_manual_entries(user_id, tax_year, employment_slot) WHERE replaced_at IS NULL AND deleted_at IS NULL",
    ],
}


def init_db() -> None:
    """
    Create tables if they do not already exist and apply pending schema migrations.

    Safe to call multiple times (idempotent):
    - CREATE TABLE IF NOT EXISTS skips existing tables.
    - Each migration statement is wrapped in try/except; ALTER TABLE ADD COLUMN
      raises OperationalError if the column already exists, which is treated as
      a no-op so that re-running init_db() on an up-to-date database is safe.
    - schema_version is stamped after all pending migrations complete.
    """
    with _connection() as conn:
        conn.executescript(_DDL)

    # Separate connection: executescript() does an implicit COMMIT so we open
    # a fresh transaction for schema-version reads and migration writes.
    with _connection() as conn:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        current_version = row["version"] if row else 0

        for version in range(current_version + 1, _SCHEMA_VERSION + 1):
            for sql in _MIGRATIONS.get(version, []):
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    # Only an additive ALTER re-applied to an already-upgraded
                    # database is safe to ignore.  In particular, a failed
                    # CREATE TABLE/INDEX must abort this transaction: stamping
                    # the schema version after a partial W9 migration would
                    # permanently hide missing owner/current-head controls.
                    if (
                        sql.lstrip().upper().startswith("ALTER TABLE")
                        and "duplicate column name" in str(exc).lower()
                    ):
                        continue
                    raise

        # Stamp with the current schema version so next init_db() is a no-op.
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (_SCHEMA_VERSION,),
            )
        elif current_version < _SCHEMA_VERSION:
            conn.execute(
                "UPDATE schema_version SET version = ?",
                (_SCHEMA_VERSION,),
            )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iso_now_plus_minutes(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    salt = os.environ.get("SESSION_SECRET", "")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


def _hash_rate_key(action: str, ip: str | None) -> str:
    """Return a 24-char hex key for rate-limit table lookups.

    Uses a distinct prefix so rate-limit hashes are not correlated with
    ip_hash values in feedback/early-access tables.
    """
    raw = f"rl:{action}:{ip or 'unknown'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


# ── Rate limiting (persistent, DB-backed, multi-worker safe) ──────────────────

def check_rate_limit(
    action: str,
    ip: str | None,
    max_attempts: int,
    window_seconds: int,
) -> bool:
    """Return True if the request is within limits, False if it should be blocked.

    Counts *failed* attempts (success=0) for this action/IP within the rolling
    window.  Successful attempts are recorded separately and do not count toward
    the limit.
    """
    key = _hash_rate_key(action, ip)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    ).isoformat(timespec="seconds")
    with _connection() as conn:
        count = conn.execute(
            """SELECT COUNT(*) FROM rate_limit_log
               WHERE key_hash = ? AND action = ? AND attempted_at > ? AND success = 0""",
            (key, action, cutoff),
        ).fetchone()[0]
    return count < max_attempts


def record_rate_attempt(
    action: str,
    ip: str | None,
    success: bool = False,
) -> None:
    """Record one attempt.  Also prunes entries older than 24 hours to keep
    the table tidy without requiring a separate maintenance job."""
    key = _hash_rate_key(action, ip)
    cutoff_prune = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).isoformat(timespec="seconds")
    with _connection() as conn:
        conn.execute(
            "DELETE FROM rate_limit_log WHERE attempted_at < ?",
            (cutoff_prune,),
        )
        conn.execute(
            """INSERT INTO rate_limit_log (key_hash, action, attempted_at, success)
               VALUES (?, ?, ?, ?)""",
            (key, action, _now(), 1 if success else 0),
        )


def _int_score(raw) -> int | None:
    try:
        v = int(raw)
        return v if 1 <= v <= 5 else None
    except (TypeError, ValueError):
        return None


# ── Writes ────────────────────────────────────────────────────────────────────

def save_feedback(data: dict, ip: str | None = None) -> int:
    """Insert a feedback submission. Returns the new row id."""
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback_submissions
                (submitted_at, intuitive, useful, trustworthy, area, comments,
                 would_use, ip_hash, email, browser, device, page_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                _int_score(data.get("intuitive")),
                _int_score(data.get("useful")),
                _int_score(data.get("trustworthy")),
                (data.get("area") or "").strip() or None,
                (data.get("comments") or "").strip() or None,
                (data.get("would_use") or "").strip() or None,
                _hash_ip(ip),
                (data.get("email") or "").strip().lower() or None,
                (data.get("browser") or "").strip() or None,
                (data.get("device") or "").strip() or None,
                (data.get("page_url") or "").strip() or None,
            ),
        )
        return cur.lastrowid


def save_early_access(data: dict, ip: str | None = None) -> dict:
    """
    Insert an early-access registration.
    Returns {"ok": True} or {"ok": False, "duplicate": True}.
    """
    email = (data.get("email") or "").strip().lower()
    with _connection() as conn:
        existing = conn.execute(
            "SELECT id FROM early_access_registrations WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
        if existing:
            return {"ok": True, "duplicate": True}
        conn.execute(
            """
            INSERT INTO early_access_registrations
                (submitted_at, name, email, occupation, working_style,
                 referral_source, comments, ip_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                (data.get("name") or "").strip(),
                email,
                (data.get("occupation") or "").strip() or None,
                (data.get("working_style") or "").strip() or None,
                (data.get("referral_source") or "").strip() or None,
                (data.get("comments") or "").strip() or None,
                _hash_ip(ip),
            ),
        )
        return {"ok": True, "duplicate": False}


# ── Reads (founder dashboard) ─────────────────────────────────────────────────

def get_feedback_stats() -> dict:
    with _connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)                    AS total,
                ROUND(AVG(intuitive), 1)    AS avg_intuitive,
                ROUND(AVG(useful), 1)       AS avg_useful,
                ROUND(AVG(trustworthy), 1)  AS avg_trustworthy
            FROM feedback_submissions
            """
        ).fetchone()
        would = conn.execute(
            """
            SELECT would_use, COUNT(*) AS n
            FROM feedback_submissions
            WHERE would_use IS NOT NULL AND would_use != ''
            GROUP BY would_use
            ORDER BY n DESC
            """
        ).fetchall()
        return {
            "total":           row["total"],
            "avg_intuitive":   row["avg_intuitive"],
            "avg_useful":      row["avg_useful"],
            "avg_trustworthy": row["avg_trustworthy"],
            "would_use":       [dict(r) for r in would],
        }


def get_recent_feedback(limit: int = 20) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT id, submitted_at, intuitive, useful, trustworthy,
                   area, comments, would_use
            FROM feedback_submissions
            ORDER BY submitted_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_early_access_stats() -> dict:
    with _connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM early_access_registrations"
        ).fetchone()
        styles = conn.execute(
            """
            SELECT working_style, COUNT(*) AS n
            FROM early_access_registrations
            WHERE working_style IS NOT NULL AND working_style != ''
            GROUP BY working_style
            ORDER BY n DESC
            """
        ).fetchall()
        return {
            "total":          row["total"],
            "working_styles": [dict(r) for r in styles],
        }


def get_recent_registrations(limit: int = 50) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT id, submitted_at, name, email, occupation, working_style, comments
            FROM early_access_registrations
            ORDER BY submitted_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_feedback() -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT id, submitted_at, intuitive, useful, trustworthy,
                   area, comments, would_use
            FROM feedback_submissions
            ORDER BY submitted_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_registrations() -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT id, submitted_at, name, email, occupation, working_style, comments
            FROM early_access_registrations
            ORDER BY submitted_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


# ── Bank connections ──────────────────────────────────────────────────────────

def save_connection(
    institution_id: str,
    institution_name: str,
    consent_token: str,
    consent_id: str | None = None,
    expires_at: str | None = None,
    session_key: str | None = None,
    user_id: int | None = None,
) -> int:
    """Insert a bank connection record. Returns the new row id."""
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO bank_connections
                (created_at, institution_id, institution_name, consent_token,
                 consent_id, status, expires_at, session_key, user_id)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (_now(), institution_id, institution_name, consent_token,
             consent_id, expires_at, session_key, user_id),
        )
        return cur.lastrowid


def get_connection_by_token(consent_token: str) -> dict | None:
    """Return the bank_connections row for a consent token, or None."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM bank_connections WHERE consent_token = ?",
            (consent_token,),
        ).fetchone()
        return dict(row) if row else None


def list_active_connections(
    session_key: str | None = None,
    user_id: int | None = None,
) -> list[dict]:
    """
    Return active connections, optionally filtered by session_key or user_id.

    When user_id is provided it takes precedence over session_key.
    """
    with _connection() as conn:
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT * FROM bank_connections
                WHERE status IN ('active', 'expiring') AND user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        elif session_key:
            rows = conn.execute(
                """
                SELECT * FROM bank_connections
                WHERE status IN ('active', 'expiring') AND session_key = ?
                ORDER BY created_at DESC
                """,
                (session_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM bank_connections
                WHERE status IN ('active', 'expiring')
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]


def update_connection_status(consent_token: str, status: str) -> None:
    """Update status for a connection. status: active|expiring|expired|revoked."""
    with _connection() as conn:
        conn.execute(
            "UPDATE bank_connections SET status = ? WHERE consent_token = ?",
            (status, consent_token),
        )


def delete_connection(consent_token: str) -> None:
    """Delete a connection and cascade to its accounts and transactions."""
    with _connection() as conn:
        conn.execute(
            "DELETE FROM bank_connections WHERE consent_token = ?",
            (consent_token,),
        )


# ── Connected accounts ────────────────────────────────────────────────────────

def save_account(
    connection_id: int,
    yapily_account_id: str,
    account_type: str | None = None,
    nickname: str | None = None,
    currency: str = "GBP",
    sort_code: str | None = None,
    account_number: str | None = None,
    balance: float | None = None,
    balance_at: str | None = None,
) -> int:
    """Insert a connected account. Returns the new row id."""
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO connected_accounts
                (connection_id, yapily_account_id, account_type, nickname,
                 currency, sort_code, account_number, balance, balance_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (connection_id, yapily_account_id, account_type, nickname,
             currency, sort_code, account_number, balance, balance_at),
        )
        return cur.lastrowid


def get_account(yapily_account_id: str) -> dict | None:
    """Return the connected_accounts row for a Yapily account ID, or None."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM connected_accounts WHERE yapily_account_id = ?",
            (yapily_account_id,),
        ).fetchone()
        return dict(row) if row else None


def list_accounts(connection_id: int) -> list[dict]:
    """Return all accounts for a connection."""
    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM connected_accounts WHERE connection_id = ? ORDER BY id",
            (connection_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_account_balance(
    yapily_account_id: str,
    balance: float,
    balance_at: str,
) -> None:
    """Refresh the cached balance for an account."""
    with _connection() as conn:
        conn.execute(
            """
            UPDATE connected_accounts
            SET balance = ?, balance_at = ?
            WHERE yapily_account_id = ?
            """,
            (balance, balance_at, yapily_account_id),
        )


# ── Transactions ──────────────────────────────────────────────────────────────

def save_transactions(account_id: int, rows: list[dict]) -> int:
    """
    Upsert classified transactions for an account.

    Each dict in ``rows`` must have:
        yapily_tx_id, tx_date, description, amount, currency,
        category, confidence, method, subcategory (or None),
        tax_relevant (bool), raw_json (str or None).

    Returns the number of rows written (inserts + updates).
    """
    written = 0
    with _connection() as conn:
        for row in rows:
            conn.execute(
                """
                INSERT INTO transactions
                    (account_id, yapily_tx_id, tx_date, description, amount, currency,
                     category, confidence, method, subcategory, tax_relevant,
                     raw_json, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, yapily_tx_id) DO UPDATE SET
                    category     = excluded.category,
                    confidence   = excluded.confidence,
                    method       = excluded.method,
                    subcategory  = excluded.subcategory,
                    tax_relevant = excluded.tax_relevant,
                    ingested_at  = excluded.ingested_at
                """,
                (
                    account_id,
                    row["yapily_tx_id"],
                    row["tx_date"],
                    row["description"],
                    row["amount"],
                    row.get("currency", "GBP"),
                    row["category"],
                    row["confidence"],
                    row["method"],
                    row.get("subcategory"),
                    1 if row.get("tax_relevant") else 0,
                    row.get("raw_json"),
                    _now(),
                ),
            )
            written += 1
    return written


def get_transactions(
    account_id: int,
    category: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """
    Return persisted transactions for an account, newest first.
    Optionally filter by category value.
    """
    with _connection() as conn:
        if category:
            rows = conn.execute(
                """
                SELECT * FROM transactions
                WHERE account_id = ? AND category = ?
                ORDER BY tx_date DESC, id DESC
                LIMIT ?
                """,
                (account_id, category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM transactions
                WHERE account_id = ?
                ORDER BY tx_date DESC, id DESC
                LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def get_transaction_summary(account_id: int) -> dict:
    """
    Return aggregate totals for an account's persisted transactions.

    Keys: total_income, total_tax_payments, total_expenses,
          unclassified_count, transaction_count.
    """
    with _connection() as conn:
        income_cats = (
            "freelance_income", "salary", "dividend",
            "interest", "rental_income", "tax_refund",
        )
        expense_cats = ("business_expense", "subscription")
        placeholders = lambda n: ",".join("?" * n)  # noqa: E731

        total_income = conn.execute(
            f"""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE account_id = ? AND category IN ({placeholders(len(income_cats))})
            """,
            (account_id, *income_cats),
        ).fetchone()[0]

        total_tax = conn.execute(
            """
            SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions
            WHERE account_id = ? AND category = 'tax_payment'
            """,
            (account_id,),
        ).fetchone()[0]

        total_expenses = conn.execute(
            f"""
            SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions
            WHERE account_id = ? AND category IN ({placeholders(len(expense_cats))})
            """,
            (account_id, *expense_cats),
        ).fetchone()[0]

        unclassified = conn.execute(
            """
            SELECT COUNT(*) FROM transactions
            WHERE account_id = ? AND category = 'unknown'
            """,
            (account_id,),
        ).fetchone()[0]

        total_count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = ?",
            (account_id,),
        ).fetchone()[0]

    return {
        "total_income": round(total_income, 2),
        "total_tax_payments": round(total_tax, 2),
        "total_expenses": round(total_expenses, 2),
        "unclassified_count": unclassified,
        "transaction_count": total_count,
    }


# ── Transaction overrides ─────────────────────────────────────────────────────

def save_override(
    transaction_id: int,
    original_category: str,
    new_category: str,
    note: str | None = None,
) -> int:
    """
    Record a manual category correction and update the transaction row.
    Returns the new override row id.
    """
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO transaction_overrides
                (transaction_id, overridden_at, original_category, new_category, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_id, _now(), original_category, new_category, note),
        )
        conn.execute(
            """
            UPDATE transactions
            SET category = ?, method = 'manual', confidence = 1.0
            WHERE id = ?
            """,
            (new_category, transaction_id),
        )
        return cur.lastrowid


def get_overrides(transaction_id: int) -> list[dict]:
    """Return all override records for a transaction, oldest first."""
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM transaction_overrides
            WHERE transaction_id = ?
            ORDER BY overridden_at
            """,
            (transaction_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── User profiles ─────────────────────────────────────────────────────────────

def save_profile(session_key: str, data: dict) -> None:
    """
    Insert or replace a user profile for a session.

    data keys (all optional): display_name, tax_year, income_estimate,
    pension_contribution, student_loan_plans (list → stored as JSON),
    notes.
    """
    import json
    student_plans = data.get("student_loan_plans")
    plans_json = json.dumps(student_plans) if isinstance(student_plans, list) else student_plans
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles
                (session_key, updated_at, display_name, tax_year,
                 income_estimate, pension_contribution, student_loan_plans, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_key) DO UPDATE SET
                updated_at           = excluded.updated_at,
                display_name         = excluded.display_name,
                tax_year             = excluded.tax_year,
                income_estimate      = excluded.income_estimate,
                pension_contribution = excluded.pension_contribution,
                student_loan_plans   = excluded.student_loan_plans,
                notes                = excluded.notes
            """,
            (
                session_key,
                _now(),
                data.get("display_name"),
                data.get("tax_year"),
                data.get("income_estimate"),
                data.get("pension_contribution"),
                plans_json,
                data.get("notes"),
            ),
        )


def get_profile(session_key: str) -> dict | None:
    """
    Return a user profile dict, or None if not found.
    student_loan_plans is decoded from JSON back to a list.
    """
    import json
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE session_key = ?",
            (session_key,),
        ).fetchone()
    if not row:
        return None
    profile = dict(row)
    raw_plans = profile.get("student_loan_plans")
    if raw_plans:
        try:
            profile["student_loan_plans"] = json.loads(raw_plans)
        except (ValueError, TypeError):
            pass
    return profile


# ── Workstream 5: User identity ───────────────────────────────────────────────

def get_or_create_user(
    clerk_user_id: str,
    email: str | None = None,
    display_name: str | None = None,
) -> int:
    """
    Return the internal DB user_id for a Clerk user ID, creating a new row
    if one does not yet exist.  Safe to call repeatedly (idempotent).

    Parameters
    ----------
    clerk_user_id : str
        The stable Clerk user identifier (e.g. "user_2abc…") or the demo
        sentinel DEMO_CLERK_ID for the internal preview user.
    email : str or None
        Primary email from the Clerk token claims.
    display_name : str or None
        Full name derived from first_name + last_name or email.

    Returns
    -------
    int
        The users.id primary key for this Clerk user.
    """
    with _connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE clerk_user_id = ?",
            (clerk_user_id,),
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            """
            INSERT INTO users (clerk_user_id, email, display_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clerk_user_id, email, display_name, _now()),
        )
        return cur.lastrowid


def get_user(user_id: int) -> dict | None:
    """Return the users row for an internal user_id, or None."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


# ── Structured manual PAYE evidence ───────────────────────────────────────────

def save_paye_manual_entry(user_id: int, data: dict) -> None:
    """Save one confirmed, minimised PAYE entry for its authenticated owner.

    ``data`` is admitted by the PAYE orchestration service. This narrow storage
    adapter deliberately accepts only structured cumulative figures and fixed
    provenance; it never receives a payslip, uploaded content, employer name,
    payroll reference, National Insurance number or future-pay assumption.
    """
    if type(user_id) is not int or user_id <= 0 or type(data) is not dict:
        raise ValueError("Invalid PAYE entry")
    from reserved.services.paye_customer_orchestration import validate_admitted_manual_entry
    validate_admitted_manual_entry(data)
    now = _now()
    with _connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise ValueError("Unknown PAYE entry owner")
        # A confirmed correction replaces only the active entry in the same
        # opaque employment slot. Historical rows remain unavailable to normal
        # reads, preserving an auditable replacement transition without keeping
        # any raw source document.
        conn.execute(
            "UPDATE paye_manual_entries SET replaced_at = ? WHERE user_id = ? "
            "AND tax_year = ? AND employment_slot = ? AND replaced_at IS NULL AND deleted_at IS NULL",
            (now, user_id, data["tax_year"], data["employment_slot"]),
        )
        conn.execute(
            """INSERT INTO paye_manual_entries
               (user_id, tax_year, employment_slot, evidence_id, source_kind, provenance,
                gross_to_date, tax_paid_to_date, tax_code, pay_frequency, pension_treatment,
                effective_through, observed_on, completeness, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, data["tax_year"], data["employment_slot"], data["evidence_id"],
             data["source_kind"], data["provenance"], data["gross_to_date"],
             data["tax_paid_to_date"], data["tax_code"], data["pay_frequency"],
             data["pension_treatment"], data["effective_through"], data["observed_on"],
             data["completeness"], now),
        )


def list_active_paye_manual_entries(user_id: int, tax_year: str) -> list[dict]:
    """Return current structured entries for one authenticated owner/year."""
    if type(user_id) is not int or user_id <= 0 or type(tax_year) is not str:
        raise ValueError("Invalid PAYE owner/year")
    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM paye_manual_entries WHERE user_id = ? AND tax_year = ? "
            "AND replaced_at IS NULL AND deleted_at IS NULL ORDER BY employment_slot, id",
            (user_id, tax_year),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_paye_manual_entry(user_id: int, tax_year: str, evidence_id: str) -> bool:
    """Remove one owner-bound entry from current use; retain its audit row."""
    if type(user_id) is not int or user_id <= 0 or type(tax_year) is not str or type(evidence_id) is not str:
        raise ValueError("Invalid PAYE deletion request")
    with _connection() as conn:
        changed = conn.execute(
            "UPDATE paye_manual_entries SET deleted_at = ? WHERE user_id = ? AND tax_year = ? "
            "AND evidence_id = ? AND replaced_at IS NULL AND deleted_at IS NULL",
            (_now(), user_id, tax_year, evidence_id),
        ).rowcount
    return changed == 1


def delete_all_paye_manual_entries_for_user(user_id: int) -> int:
    """Soft-remove current PAYE entries; retained rows are not account erasure.

    Whole-account physical erasure occurs only when an independently authorised
    account-deletion lifecycle deletes the owning ``users`` row and SQLite
    applies the foreign-key cascade.  This helper does not perform that
    lifecycle and deliberately makes no retention or backup-erasure claim.
    """
    if type(user_id) is not int or user_id <= 0:
        raise ValueError("Invalid PAYE deletion owner")
    with _connection() as conn:
        return conn.execute(
            "UPDATE paye_manual_entries SET deleted_at = ? WHERE user_id = ? AND deleted_at IS NULL",
            (_now(), user_id),
        ).rowcount


def migrate_session_to_user(session_key: str, user_id: int) -> dict:
    """
    Link existing session_key-keyed rows to a real user_id.

    Called automatically on the first Clerk sign-in when the browser
    previously used the app anonymously.  Only updates rows where
    user_id is currently NULL (so repeated calls are safe).

    Returns
    -------
    dict
        {"profiles": n, "connections": n} — count of rows updated per table.
    """
    with _connection() as conn:
        profiles = conn.execute(
            """
            UPDATE user_profiles
            SET user_id = ?
            WHERE session_key = ? AND user_id IS NULL
            """,
            (user_id, session_key),
        ).rowcount
        connections = conn.execute(
            """
            UPDATE bank_connections
            SET user_id = ?
            WHERE session_key = ? AND user_id IS NULL
            """,
            (user_id, session_key),
        ).rowcount
    return {"profiles": profiles, "connections": connections}


def save_profile_by_user(user_id: int, data: dict) -> None:
    """
    Insert or update a user profile keyed by user_id.

    Uses the synthetic session_key "user:<user_id>" so that this function
    is compatible with the session_key UNIQUE constraint on user_profiles.
    The user_id FK is also set for direct lookups via get_profile_by_user().

    data keys (all optional): display_name, tax_year, income_estimate,
    pension_contribution, student_loan_plans (list → JSON), notes.
    """
    import json
    session_key = f"user:{user_id}"
    student_plans = data.get("student_loan_plans")
    plans_json = json.dumps(student_plans) if isinstance(student_plans, list) else student_plans
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles
                (session_key, updated_at, display_name, tax_year,
                 income_estimate, pension_contribution, student_loan_plans, notes, user_id,
                 child_benefit_children, child_benefit_annual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_key) DO UPDATE SET
                updated_at              = excluded.updated_at,
                display_name            = excluded.display_name,
                tax_year                = excluded.tax_year,
                income_estimate         = excluded.income_estimate,
                pension_contribution    = excluded.pension_contribution,
                student_loan_plans      = excluded.student_loan_plans,
                notes                   = excluded.notes,
                user_id                 = excluded.user_id,
                child_benefit_children  = excluded.child_benefit_children,
                child_benefit_annual    = excluded.child_benefit_annual
            """,
            (
                session_key,
                _now(),
                data.get("display_name"),
                data.get("tax_year"),
                data.get("income_estimate"),
                data.get("pension_contribution"),
                plans_json,
                data.get("notes"),
                user_id,
                int(data.get("child_benefit_children") or 0),
                data.get("child_benefit_annual"),
            ),
        )


def get_profile_by_user(user_id: int) -> dict | None:
    """
    Return the user profile for a given internal user_id, or None.
    student_loan_plans is decoded from JSON back to a list.
    """
    import json
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    profile = dict(row)
    raw_plans = profile.get("student_loan_plans")
    if raw_plans:
        try:
            profile["student_loan_plans"] = json.loads(raw_plans)
        except (ValueError, TypeError):
            pass
    return profile


# ── HICBC partner estimates (October v1) ─────────────────────────────────────────
# Money/ANI values are canonical Decimal strings.  ``save_hicbc_estimate``
# preserves the evidence_id across updates (replacement) so the evidence stays a
# single stable identity for the user/tax-year; a fresh insert gets a new one.

def save_hicbc_estimate(user_id: int, data: dict) -> None:
    """Upsert the HICBC partner estimate for ``user_id`` and ``tax_year``.

    ``data`` keys (all optional except ``tax_year``):
        receives_child_benefit (None|0|1), child_benefit_claimant
        (None|'person'|'partner'|'none'), child_benefit_children (int),
        child_benefit_annual (Decimal str|None),
        child_benefit_weeks_entitled (int|None), has_relevant_partner (None|0|1),
        relationship_covers_full_year (None|0|1: whether the preceding partner
        status answer held for the full tax year), partner_status_period_semantics
        (None|'status_answer_full_year'; NULL identifies legacy ambiguous rows),
        representation (None|'point'|'range'),
        partner_ani_point/low/high (Decimal str|None),
        source_kind, observed_at, confirmed_at, completeness, recency_state.
    """
    import uuid

    tax_year = data.get("tax_year")
    if not tax_year:
        raise ValueError("tax_year is required")
    now = _now()
    with _connection() as conn:
        existing = conn.execute(
            "SELECT evidence_id FROM hicbc_estimates WHERE user_id = ? AND tax_year = ?",
            (user_id, tax_year),
        ).fetchone()
        evidence_id = existing["evidence_id"] if existing else uuid.uuid4().hex
        observed_at = data.get("observed_at") or now
        conn.execute(
            """
            INSERT INTO hicbc_estimates
                (user_id, tax_year, receives_child_benefit, child_benefit_claimant,
                 child_benefit_children, child_benefit_annual,
                 child_benefit_weeks_entitled, has_relevant_partner,
                 relationship_covers_full_year, partner_status_period_semantics, representation,
                 partner_ani_point, partner_ani_low, partner_ani_high,
                 evidence_id, source_kind, observed_at, confirmed_at,
                 completeness, recency_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, tax_year) DO UPDATE SET
                receives_child_benefit      = excluded.receives_child_benefit,
                child_benefit_claimant      = excluded.child_benefit_claimant,
                child_benefit_children      = excluded.child_benefit_children,
                child_benefit_annual        = excluded.child_benefit_annual,
                child_benefit_weeks_entitled = excluded.child_benefit_weeks_entitled,
                has_relevant_partner        = excluded.has_relevant_partner,
                relationship_covers_full_year = excluded.relationship_covers_full_year,
                partner_status_period_semantics = excluded.partner_status_period_semantics,
                representation              = excluded.representation,
                partner_ani_point           = excluded.partner_ani_point,
                partner_ani_low             = excluded.partner_ani_low,
                partner_ani_high            = excluded.partner_ani_high,
                source_kind                 = excluded.source_kind,
                observed_at                 = excluded.observed_at,
                confirmed_at                = excluded.confirmed_at,
                completeness                = excluded.completeness,
                recency_state               = excluded.recency_state,
                updated_at                  = excluded.updated_at
            """,
            (
                user_id,
                tax_year,
                data.get("receives_child_benefit"),
                data.get("child_benefit_claimant"),
                int(data.get("child_benefit_children") or 0),
                data.get("child_benefit_annual"),
                data.get("child_benefit_weeks_entitled"),
                data.get("has_relevant_partner"),
                data.get("relationship_covers_full_year"),
                data.get("partner_status_period_semantics") or (
                    "status_answer_full_year"
                    if "relationship_covers_full_year" in data else None
                ),
                data.get("representation"),
                data.get("partner_ani_point"),
                data.get("partner_ani_low"),
                data.get("partner_ani_high"),
                evidence_id,
                data.get("source_kind") or "user_supplied_partner_estimate",
                observed_at,
                data.get("confirmed_at"),
                data.get("completeness") or "complete_for_purpose",
                data.get("recency_state") or "current",
                now,
                now,
            ),
        )


def get_hicbc_estimate(user_id: int, tax_year: str) -> dict | None:
    """Return the HICBC partner estimate row for ``user_id``/``tax_year``."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM hicbc_estimates WHERE user_id = ? AND tax_year = ?",
            (user_id, tax_year),
        ).fetchone()
    return dict(row) if row else None


@contextmanager
def hicbc_manual_preview_read(user_id: int, tax_year: str):
    """Serialise a manual preview against owner/year evidence and link changes.

    Hold the short transaction through calculation: withdrawal/relink and
    estimate changes cannot commit between admission and result construction.
    No partner financial row is read and no data is written. Any active link,
    including ambiguous/multiple or unconsented links, blocks this manual path.
    """
    if type(user_id) is not int or user_id <= 0 or type(tax_year) is not str:
        raise ValueError("Invalid preview owner/year")
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        owner = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if owner is None:
            raise ValueError("Invalid preview owner/year")
        row = conn.execute(
            "SELECT * FROM hicbc_estimates WHERE user_id = ? AND tax_year = ?",
            (user_id, tax_year),
        ).fetchone()
        linked = conn.execute(
            "SELECT 1 FROM hicbc_links WHERE (user_low_id = ? OR user_high_id = ?) "
            "AND tax_year = ? AND status = ? LIMIT 1",
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchone()
        yield (dict(row) if row else None), linked is not None


def delete_hicbc_estimate(user_id: int, tax_year: str) -> bool:
    """Delete the HICBC partner estimate for ``user_id``/``tax_year``.

    Returns True if a row was deleted (enforces ownership).
    """
    with _connection() as conn:
        rowcount = conn.execute(
            "DELETE FROM hicbc_estimates WHERE user_id = ? AND tax_year = ?",
            (user_id, tax_year),
        ).rowcount
    return rowcount > 0


def delete_all_hicbc_estimates_for_user(user_id: int) -> int:
    """Delete every HICBC partner estimate owned by ``user_id``.

    This is the repository hook that a later account-deletion workflow must
    invoke; it does not itself delete the ``users`` row.  Returns the number of
    rows removed.
    """
    with _connection() as conn:
        rowcount = conn.execute(
            "DELETE FROM hicbc_estimates WHERE user_id = ?",
            (user_id,),
        ).rowcount
    return rowcount


# ── HICBC linked-account consent ────────────────────────────────────────────────

_LINK_STATUS_ACTIVE = "active"
_LINK_STATUS_REVOKED = "revoked"

_INVITATION_STATUS_PENDING = "pending"
_INVITATION_STATUS_ACCEPTED = "accepted"
_INVITATION_STATUS_REVOKED = "revoked"

# Invitations are short-lived and single-use.
_INVITATION_TTL_MINUTES = 60

# Display-to-submit permission bindings are short-lived and capped per user/link
# cycle so GET refreshes cannot grow durable state without bound.
_PERMISSION_FORM_TTL_MINUTES = 120
_MAX_PERMISSION_FORM_BINDINGS = 5

# Single authoritative linked-HICBC consent-notice version.  Mutual permission is
# established only when *both* participants have recorded this recognised version;
# an arbitrary or incompatible notice version must never satisfy consent.
HICBC_NOTICE_VERSION = "hicbc-notice-v1"

_PERMISSION_EVENT_CONSENT = "consent"
_PERMISSION_EVENT_WITHDRAW = "withdraw"
_PERMISSION_EVENT_UNLINK = "unlink"
_PERMISSION_EVENT_RELINK = "relink"


def _record_hicbc_permission_event(
    conn,
    *,
    link_id: int,
    permission_cycle: int,
    event_type: str,
    actor_user_id: int,
    occurred_at: str,
    notice_version: str,
) -> None:
    """Append one idempotent permission-lifecycle event inside a transaction.

    The uniqueness key is a state transition, not a request timestamp.  A retry
    can therefore never create a duplicate event, while a later re-link cycle
    retains its own complete history.  Events are evidence only: current access
    is always determined from ``hicbc_links`` and ``hicbc_link_consents``.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO hicbc_permission_events
            (link_id, permission_cycle, event_type, actor_user_id,
             occurred_at, notice_version)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            link_id,
            permission_cycle,
            event_type,
            actor_user_id,
            occurred_at,
            notice_version,
        ),
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_hicbc_link_invitation(
    user_id: int,
    tax_year: str,
    *,
    expires_in_minutes: int = _INVITATION_TTL_MINUTES,
) -> str:
    """Create a single-use HICBC link invitation and return its raw token.

    The raw token is returned exactly once (for out-of-band sharing) and is never
    stored; only its SHA-256 hash is persisted.  The token is high-entropy,
    short-lived and single-use.
    """
    token = secrets.token_urlsafe(32)
    now = _now()
    expires_at = _iso_now_plus_minutes(expires_in_minutes)
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO hicbc_link_invitations
                (token_hash, creator_id, tax_year, purpose, status, expires_at, created_at)
            VALUES (?, ?, ?, 'hicbc_responsibility', ?, ?, ?)
            """,
            (_token_hash(token), user_id, tax_year, _INVITATION_STATUS_PENDING, expires_at, now),
        )
    return token


def _has_other_active_link(conn, user_id: int, tax_year: str, low: int, high: int) -> bool:
    """True if ``user_id`` already has an active link with a *different* partner."""
    row = conn.execute(
        """
        SELECT id FROM hicbc_links
        WHERE (user_low_id = ? OR user_high_id = ?)
          AND tax_year = ?
          AND status = ?
          AND NOT (user_low_id = ? AND user_high_id = ?)
        """,
        (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE, low, high),
    ).fetchone()
    return row is not None


def accept_hicbc_link_invitation(user_id: int, token: str, tax_year: str) -> dict | None:
    """Accept a pending invitation and establish (or re-activate) a mutual link.

    Returns the active link row as a dict on success, or ``None`` when the token
    is invalid, expired, already used, a self-link, a duplicate active link, or
    either participant already has an active link with a different partner.

    The check-and-insert runs inside ``BEGIN IMMEDIATE`` so concurrent accepts
    cannot both observe an absent active link and insert two partners for one
    user.  Fails closed and never leaks which reason applied to a non-participant.
    """
    now = _now()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        invitation = conn.execute(
            "SELECT * FROM hicbc_link_invitations WHERE token_hash = ? AND tax_year = ?",
            (_token_hash(token), tax_year),
        ).fetchone()
        if invitation is None:
            return None
        invitation = dict(invitation)
        if invitation["status"] != _INVITATION_STATUS_PENDING:
            return None
        if invitation["expires_at"] <= now:
            return None
        creator_id = invitation["creator_id"]
        if creator_id == user_id:
            return None  # self-link rejected

        low, high = sorted((creator_id, user_id))
        if _has_other_active_link(conn, creator_id, tax_year, low, high):
            return None  # creator already linked to a different partner
        if _has_other_active_link(conn, user_id, tax_year, low, high):
            return None  # acceptor already linked to a different partner

        existing = conn.execute(
            "SELECT * FROM hicbc_links WHERE user_low_id = ? AND user_high_id = ? AND tax_year = ?",
            (low, high, tax_year),
        ).fetchone()
        if existing is not None and existing["status"] == _LINK_STATUS_ACTIVE:
            return None  # duplicate active link

        # Single-use token consumption.
        conn.execute(
            """
            UPDATE hicbc_link_invitations
            SET status = ?, accepted_at = ?, accepted_by = ?
            WHERE id = ?
            """,
            (_INVITATION_STATUS_ACCEPTED, now, user_id, invitation["id"]),
        )

        if existing is None:
            cur = conn.execute(
                """
                INSERT INTO hicbc_links
                    (user_low_id, user_high_id, tax_year, purpose, status, initiator_id,
                     relationship_started_at, created_at, accepted_at, permission_cycle)
                VALUES (?, ?, ?, 'hicbc_responsibility', ?, ?, NULL, ?, ?, 1)
                """,
                (low, high, tax_year, _LINK_STATUS_ACTIVE, creator_id, now, now),
            )
            link_id = cur.lastrowid
        else:
            link_id = existing["id"]
            next_cycle = int(existing["permission_cycle"] or 1) + 1
            # A revoked legacy row may still contain apparently current consent.
            # Invalidate every such row before reactivation; both participants
            # must affirm the current notice again for this new cycle.
            conn.execute(
                """
                UPDATE hicbc_link_consents
                SET withdrawn_at = COALESCE(withdrawn_at, ?)
                WHERE link_id = ?
                """,
                (now, link_id),
            )
            conn.execute(
                """
                UPDATE hicbc_links
                SET status = ?, initiator_id = ?, accepted_at = ?, revoked_at = NULL,
                    revoked_by = NULL, permission_cycle = ?
                WHERE id = ?
                """,
                (_LINK_STATUS_ACTIVE, creator_id, now, next_cycle, link_id),
            )
            _record_hicbc_permission_event(
                conn,
                link_id=link_id,
                permission_cycle=next_cycle,
                event_type=_PERMISSION_EVENT_RELINK,
                actor_user_id=user_id,
                occurred_at=now,
                notice_version=HICBC_NOTICE_VERSION,
            )
            conn.execute(
                "DELETE FROM hicbc_permission_form_bindings WHERE link_id = ?",
                (link_id,),
            )

        conn.execute(
            "UPDATE hicbc_link_invitations SET link_id = ? WHERE id = ?",
            (link_id, invitation["id"]),
        )
        return _get_hicbc_link_row(conn, link_id)


def _get_hicbc_link_row(conn, link_id: int) -> dict:
    row = conn.execute("SELECT * FROM hicbc_links WHERE id = ?", (link_id,)).fetchone()
    return dict(row) if row else None


def get_active_hicbc_link(user_id: int, tax_year: str) -> dict | None:
    """Return the active HICBC link involving ``user_id`` for ``tax_year``.

    Returns ``None`` when there is no active link **or** when more than one
    active link exists (ambiguous/malformed data).  Never selects an arbitrary
    partner.
    """
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?) AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
    if len(rows) == 1:
        return dict(rows[0])
    return None


def get_hicbc_link_partner_id(user_id: int, tax_year: str) -> int | None:
    """Return the other participant's user_id for a uniquely active link, or None."""
    link = get_active_hicbc_link(user_id, tax_year)
    if link is None:
        return None
    if link["user_low_id"] == user_id:
        return link["user_high_id"]
    return link["user_low_id"]


def revoke_hicbc_link(user_id: int, tax_year: str) -> bool:
    """Revoke the active HICBC link involving ``user_id``.

    Either participant may revoke.  Revocation takes effect immediately for
    future calculations; the link row is retained (status 'revoked') as minimal
    audit evidence and is never used again for cross-account access.  Returns
    True if exactly one active link was revoked; ambiguous (multiple) active
    links fail closed and are left untouched.
    """
    now = _now()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?) AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(rows) != 1:
            return False
        link = rows[0]
        active_actor_consent = conn.execute(
            """
            SELECT notice_version FROM hicbc_link_consents
            WHERE link_id = ? AND user_id = ? AND withdrawn_at IS NULL
            """,
            (link["id"], user_id),
        ).fetchone()
        # Unlinking invalidates all current permission rows atomically.  Only the
        # participant who acted is recorded as withdrawing; no withdrawal is
        # attributed to the other person.
        conn.execute(
            """
            UPDATE hicbc_link_consents
            SET withdrawn_at = COALESCE(withdrawn_at, ?)
            WHERE link_id = ?
            """,
            (now, link["id"]),
        )
        conn.execute(
            "DELETE FROM hicbc_permission_form_bindings WHERE link_id = ?",
            (link["id"],),
        )
        conn.execute(
            "UPDATE hicbc_links SET status = ?, revoked_at = ?, revoked_by = ? WHERE id = ?",
            (_LINK_STATUS_REVOKED, now, user_id, link["id"]),
        )
        cycle = int(link["permission_cycle"] or 1)
        if active_actor_consent is not None:
            _record_hicbc_permission_event(
                conn,
                link_id=link["id"],
                permission_cycle=cycle,
                event_type=_PERMISSION_EVENT_WITHDRAW,
                actor_user_id=user_id,
                occurred_at=now,
                # Preserve the immutable notice identity that the participant
                # actually accepted, even if a later notice is now current.
                notice_version=active_actor_consent["notice_version"],
            )
        _record_hicbc_permission_event(
            conn,
            link_id=link["id"],
            permission_cycle=cycle,
            event_type=_PERMISSION_EVENT_UNLINK,
            actor_user_id=user_id,
            occurred_at=now,
            notice_version=HICBC_NOTICE_VERSION,
        )
    return True


def _issue_hicbc_permission_binding_for_link(
    conn: sqlite3.Connection,
    link: sqlite3.Row,
    user_id: int,
    tax_year: str,
    now: str,
) -> str:
    """Issue a form binding for an already-validated link in ``conn``.

    The caller must hold the same transaction that established the link and
    consent state it is about to render.  Keeping the lookup, status and token
    insertion in one snapshot prevents a form for one link/cycle being paired
    with status from another during an unlink/relink race.
    """
    raw_token = secrets.token_urlsafe(32)
    expires_at = _iso_now_plus_minutes(_PERMISSION_FORM_TTL_MINUTES)
    cycle = int(link["permission_cycle"] or 1)
    conn.execute(
        """
        DELETE FROM hicbc_permission_form_bindings
        WHERE user_id = ? AND expires_at <= ?
        """,
        (user_id, now),
    )
    # Bound all outstanding forms for this participant/link/cycle, rather than
    # only the current notice version.  This keeps notice-version transitions
    # from accumulating obsolete form capabilities until expiry.
    retained = conn.execute(
        """
        SELECT token_hash FROM hicbc_permission_form_bindings
        WHERE link_id = ? AND permission_cycle = ? AND user_id = ?
          AND tax_year = ?
        ORDER BY created_at, token_hash
        """,
        (link["id"], cycle, user_id, tax_year),
    ).fetchall()
    excess = len(retained) - (_MAX_PERMISSION_FORM_BINDINGS - 1)
    for row in retained[:max(0, excess)]:
        conn.execute(
            "DELETE FROM hicbc_permission_form_bindings WHERE token_hash = ?",
            (row["token_hash"],),
        )
    conn.execute(
        """
        INSERT INTO hicbc_permission_form_bindings
            (token_hash, link_id, permission_cycle, user_id, tax_year,
             notice_version, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _token_hash(raw_token),
            link["id"],
            cycle,
            user_id,
            tax_year,
            HICBC_NOTICE_VERSION,
            now,
            expires_at,
        ),
    )
    return raw_token


def create_hicbc_link_permission_binding(user_id: int, tax_year: str) -> str | None:
    """Issue an opaque form token bound to the exact current permission context.

    The raw high-entropy token is returned once and only its SHA-256 hash is
    stored.  It binds the rendered form to link identity, permission cycle,
    authenticated participant, tax year and the server-owned notice version.
    Customer pages should use ``get_hicbc_link_permission_view`` so the status
    displayed and the binding issued share one atomic database snapshot.
    """
    now = _now()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        links = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?)
              AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(links) != 1:
            return None
        return _issue_hicbc_permission_binding_for_link(
            conn, links[0], user_id, tax_year, now
        )


def _record_hicbc_link_consent(
    user_id: int,
    tax_year: str,
    notice_version: str,
    *,
    permission_binding_token: str | None,
    require_permission_binding: bool,
) -> bool:
    """Transactional implementation for trusted and customer-form entrypoints."""
    if type(notice_version) is not str or notice_version != HICBC_NOTICE_VERSION:
        return False
    if require_permission_binding and (
        type(permission_binding_token) is not str or not permission_binding_token
    ):
        return False
    now = _now()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        links = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?)
              AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(links) != 1:
            return False
        link = links[0]
        if require_permission_binding:
            binding = conn.execute(
                """
                SELECT * FROM hicbc_permission_form_bindings
                WHERE token_hash = ?
                """,
                (_token_hash(permission_binding_token),),
            ).fetchone()
            if binding is None or not (
                binding["link_id"] == link["id"]
                and binding["permission_cycle"] == int(link["permission_cycle"] or 1)
                and binding["user_id"] == user_id
                and binding["tax_year"] == tax_year
                and binding["notice_version"] == HICBC_NOTICE_VERSION
                and binding["expires_at"] > now
            ):
                return False
        existing = conn.execute(
            """
            SELECT notice_version, withdrawn_at FROM hicbc_link_consents
            WHERE link_id = ? AND user_id = ?
            """,
            (link["id"], user_id),
        ).fetchone()
        if (
            existing is not None
            and existing["notice_version"] == HICBC_NOTICE_VERSION
            and existing["withdrawn_at"] is None
        ):
            return True
        conn.execute(
            """
            INSERT INTO hicbc_link_consents (link_id, user_id, notice_version, consented_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(link_id, user_id) DO UPDATE SET
                notice_version = excluded.notice_version,
                consented_at = excluded.consented_at,
                withdrawn_at = NULL
            """,
            (link["id"], user_id, notice_version, now),
        )
        _record_hicbc_permission_event(
            conn,
            link_id=link["id"],
            permission_cycle=int(link["permission_cycle"] or 1),
            event_type=_PERMISSION_EVENT_CONSENT,
            actor_user_id=user_id,
            occurred_at=now,
            notice_version=HICBC_NOTICE_VERSION,
        )
    return True


def record_hicbc_link_consent(user_id: int, tax_year: str, notice_version: str) -> bool:
    """Record trusted internal linked-HICBC consent against the current link.

    ``notice_version`` must be the recognised authoritative version; it is the
    auditable identifier of the concise explanation the participant was shown.
    Recording is per-participant: mutual permission is established only once
    *both* participants have recorded consent for the same active link.  Returns
    False when there is no unique active link or the notice version is not the
    recognised version.  This trusted internal entrypoint is retained for
    construction/tests; customer requests must use the binding-required
    ``record_hicbc_link_consent_from_binding`` entrypoint.
    """
    return _record_hicbc_link_consent(
        user_id,
        tax_year,
        notice_version,
        permission_binding_token=None,
        require_permission_binding=False,
    )


def record_hicbc_link_consent_from_binding(
    user_id: int,
    tax_year: str,
    notice_version: str,
    permission_binding_token: str,
) -> bool:
    """Record customer consent only after exact atomic form-binding validation."""
    return _record_hicbc_link_consent(
        user_id,
        tax_year,
        notice_version,
        permission_binding_token=permission_binding_token,
        require_permission_binding=True,
    )


def has_mutual_hicbc_link_consent(user_id: int, tax_year: str) -> bool:
    """True iff both participants recorded the recognised, non-withdrawn consent."""
    with _connection() as conn:
        links = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?)
              AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(links) != 1:
            return False
        link = links[0]
        rows = conn.execute(
            """
            SELECT user_id FROM hicbc_link_consents
            WHERE link_id = ? AND withdrawn_at IS NULL
              AND notice_version = ?
            """,
            (link["id"], HICBC_NOTICE_VERSION),
        ).fetchall()
    consented = {row["user_id"] for row in rows}
    return consented == {link["user_low_id"], link["user_high_id"]}


def get_hicbc_link_permission_status(user_id: int, tax_year: str) -> dict:
    """Return the minimum owner-scoped status needed by the linked-HICBC page.

    The result intentionally contains no partner identity, financial value,
    event history or timing.  It is not an authority source: calculations still
    call ``has_mutual_hicbc_link_consent`` against current rows.
    """
    with _connection() as conn:
        links = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?)
              AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(links) != 1:
            return {"linked": False, "own_permission": False, "mutual_permission": False}
        link = links[0]
        rows = conn.execute(
            """
            SELECT user_id FROM hicbc_link_consents
            WHERE link_id = ? AND withdrawn_at IS NULL
              AND notice_version = ?
            """,
            (link["id"], HICBC_NOTICE_VERSION),
        ).fetchall()
    consented = {row["user_id"] for row in rows}
    participants = {link["user_low_id"], link["user_high_id"]}
    return {
        "linked": True,
        "own_permission": user_id in consented,
        "mutual_permission": consented == participants,
    }


def get_hicbc_link_permission_view(user_id: int, tax_year: str) -> dict:
    """Return minimal page state and, when needed, its exact form binding.

    Link selection, current-consent inspection and binding issuance happen in
    one immediate transaction.  The returned object deliberately contains no
    link ID, permission-cycle value, partner identity or financial data; those
    facts remain server-side in the hashed binding record.
    """
    now = _now()
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        links = conn.execute(
            """
            SELECT * FROM hicbc_links
            WHERE (user_low_id = ? OR user_high_id = ?)
              AND tax_year = ? AND status = ?
            """,
            (user_id, user_id, tax_year, _LINK_STATUS_ACTIVE),
        ).fetchall()
        if len(links) != 1:
            return {
                "linked": False,
                "own_permission": False,
                "mutual_permission": False,
                "permission_binding": None,
            }
        link = links[0]
        rows = conn.execute(
            """
            SELECT user_id FROM hicbc_link_consents
            WHERE link_id = ? AND withdrawn_at IS NULL
              AND notice_version = ?
            """,
            (link["id"], HICBC_NOTICE_VERSION),
        ).fetchall()
        consented = {row["user_id"] for row in rows}
        participants = {link["user_low_id"], link["user_high_id"]}
        own_permission = user_id in consented
        permission_binding = None
        if not own_permission:
            permission_binding = _issue_hicbc_permission_binding_for_link(
                conn, link, user_id, tax_year, now
            )
        return {
            "linked": True,
            "own_permission": own_permission,
            "mutual_permission": consented == participants,
            "permission_binding": permission_binding,
        }


def delete_all_hicbc_links_for_user(user_id: int) -> int:
    """Delete every HICBC link and invitation involving ``user_id``.

    Account-deletion hook: removes links (both sides) and the user's invitations.
    Returns the number of link/invitation rows removed.
    """
    with _connection() as conn:
        links = conn.execute(
            "DELETE FROM hicbc_links WHERE user_low_id = ? OR user_high_id = ?",
            (user_id, user_id),
        ).rowcount
        invitations = conn.execute(
            "DELETE FROM hicbc_link_invitations WHERE creator_id = ? OR accepted_by = ?",
            (user_id, user_id),
        ).rowcount
    return links + invitations


def save_optimise_scenario(
    user_id: int,
    opportunity: str,
    inputs: dict,
    outputs: dict,
    label: str | None = None,
    tax_year: str | None = None,
) -> int:
    """Save a pension-contribution scenario comparison for a user.

    Parameters
    ----------
    user_id:     Internal user ID.
    opportunity: Opportunity identifier ("PA_TAPER" | "HICBC").
    inputs:      Dict of calculation inputs (projected_income, pension, extra, annual_cb).
    outputs:     Dict of results (before, after, it_reduction, hicbc_reduction, total_benefit).
    label:       Optional user-supplied name for this comparison.
    tax_year:    Applicable tax year the scenario was calculated under.  A new
                 save must carry a supported year (enforced by the caller);
                 ``None`` is reserved for legacy/pre-migration records only.

    Returns the new row ID.
    """
    import json
    with _connection() as conn:
        cur = conn.execute(
            """INSERT INTO optimise_scenarios
               (user_id, opportunity, label, tax_year, inputs_json, outputs_json, saved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, opportunity, label, tax_year, json.dumps(inputs), json.dumps(outputs), _now()),
        )
        return cur.lastrowid


def list_optimise_scenarios(user_id: int, limit: int = 10) -> list[dict]:
    """Return the most recent saved scenarios for a user, newest first."""
    import json
    with _connection() as conn:
        rows = conn.execute(
            """SELECT * FROM optimise_scenarios
               WHERE user_id = ?
               ORDER BY saved_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["inputs"]  = json.loads(d.get("inputs_json")  or "{}")
        except (ValueError, TypeError):
            d["inputs"] = {}
        try:
            d["outputs"] = json.loads(d.get("outputs_json") or "{}")
        except (ValueError, TypeError):
            d["outputs"] = {}
        result.append(d)
    return result


def delete_optimise_scenario(scenario_id: int, user_id: int) -> bool:
    """Delete a saved scenario, enforcing user ownership.  Returns True if deleted."""
    with _connection() as conn:
        rowcount = conn.execute(
            "DELETE FROM optimise_scenarios WHERE id = ? AND user_id = ?",
            (scenario_id, user_id),
        ).rowcount
    return rowcount > 0


def list_connections_for_user(user_id: int) -> list[dict]:
    """Return active and expiring bank connections for an authenticated user."""
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM bank_connections
            WHERE status IN ('active', 'expiring') AND user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Workstream 6: Invoices ─────────────────────────────────────────────────────

def save_invoice(
    reference: str,
    client_name: str,
    amount_due: float,
    issue_date: str,
    due_date: str,
    currency: str = "GBP",
    status: str = "unpaid",
    notes: str | None = None,
    user_id: int | None = None,
) -> int:
    """
    Insert a new invoice row. Returns the new invoice id.

    Raises sqlite3.IntegrityError if (user_id, reference) already exists.
    Call get_invoice_by_reference() first to check.
    """
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO invoices
                (user_id, reference, client_name, amount_due, currency,
                 issue_date, due_date, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                reference,
                client_name,
                amount_due,
                currency,
                issue_date,
                due_date,
                status,
                notes,
                _now(),
            ),
        )
        return cur.lastrowid


def get_invoice_by_reference(
    reference: str,
    user_id: int | None = None,
) -> dict | None:
    """
    Return an invoice dict by reference, scoped to user_id when provided.
    Returns None if not found.
    """
    with _connection() as conn:
        if user_id is not None:
            row = conn.execute(
                "SELECT * FROM invoices WHERE reference = ? AND user_id = ?",
                (reference, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM invoices WHERE reference = ? AND user_id IS NULL",
                (reference,),
            ).fetchone()
    return dict(row) if row else None


def get_invoice(invoice_id: int) -> dict | None:
    """Return an invoice dict by primary key, or None."""
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE id = ?",
            (invoice_id,),
        ).fetchone()
    return dict(row) if row else None


def list_invoices(user_id: int | None = None) -> list[dict]:
    """
    Return all invoices for a user, ordered by due_date descending.
    When user_id is None, returns invoices with a NULL user_id (demo/test rows).
    """
    with _connection() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT * FROM invoices WHERE user_id = ? ORDER BY due_date DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM invoices WHERE user_id IS NULL ORDER BY due_date DESC",
            ).fetchall()
    return [dict(r) for r in rows]


def update_invoice_status(invoice_id: int, status: str) -> None:
    """Update the status of an invoice row."""
    with _connection() as conn:
        conn.execute(
            "UPDATE invoices SET status = ? WHERE id = ?",
            (status, invoice_id),
        )


# ── Workstream 6: Invoice matches ──────────────────────────────────────────────

def save_match(
    invoice_id: int,
    status: str,
    confidence: int,
    method: str,
    explanation: str,
    matched_amount: float,
    transaction_id: int | None = None,
    review_state: str = "pending_review",
) -> int:
    """
    Persist one invoice-match link. Returns the new invoice_matches.id.

    For MULTIPLE_PAYMENTS, call once per contributing transaction.
    For UNMATCHED, call with transaction_id=None.
    """
    with _connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO invoice_matches
                (invoice_id, transaction_id, matched_at, status, confidence,
                 method, explanation, matched_amount, review_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                transaction_id,
                _now(),
                status,
                confidence,
                method,
                explanation,
                matched_amount,
                review_state,
            ),
        )
        return cur.lastrowid


def get_matches_for_invoice(invoice_id: int) -> list[dict]:
    """Return all match rows for an invoice, ordered by confidence descending."""
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM invoice_matches
            WHERE invoice_id = ?
            ORDER BY confidence DESC, matched_at DESC
            """,
            (invoice_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_invoices_with_best_match(user_id: int) -> list[dict]:
    """
    Return invoices for a user joined with their best match (highest confidence).
    Invoices with no match rows have match_* columns as None.
    Ownership is enforced: only invoices belonging to user_id are returned.
    """
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT
                i.id,            i.reference,     i.client_name,
                i.amount_due,    i.currency,
                i.status   AS invoice_status,
                i.due_date,      i.issue_date,    i.notes,
                im.id        AS match_id,
                im.status    AS match_status,
                im.confidence,   im.method,       im.explanation,
                im.matched_amount, im.review_state, im.transaction_id
            FROM invoices i
            LEFT JOIN invoice_matches im
                   ON im.invoice_id = i.id
                  AND im.confidence = (
                          SELECT MAX(im2.confidence)
                          FROM invoice_matches im2
                          WHERE im2.invoice_id = i.id
                      )
            WHERE i.user_id = ?
            ORDER BY i.due_date DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_invoice_counts_for_user(user_id: int) -> dict:
    """
    Return invoice status counts for a user in a single query.

    Keys: total, matched, outstanding, needs_review.
    """
    with _connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT i.id) AS total,
                COUNT(DISTINCT CASE
                    WHEN im.status = 'matched' THEN i.id END) AS matched,
                COUNT(DISTINCT CASE
                    WHEN im.status = 'unmatched' OR im.id IS NULL THEN i.id END) AS outstanding,
                COUNT(DISTINCT CASE
                    WHEN im.review_state = 'pending_review'
                     AND im.status != 'matched' THEN i.id END) AS needs_review
            FROM invoices i
            LEFT JOIN invoice_matches im
                   ON im.invoice_id = i.id
                  AND im.confidence = (
                          SELECT MAX(c.confidence)
                          FROM invoice_matches c
                          WHERE c.invoice_id = i.id
                      )
            WHERE i.user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else {"total": 0, "matched": 0, "outstanding": 0, "needs_review": 0}


def get_user_review_items(user_id: int) -> dict:
    """
    Return items requiring user attention.

    Ownership is enforced through JOINs to bank_connections.user_id and
    invoices.user_id — no client-supplied IDs are trusted.

    Returns:
        unclassified_transactions — unknown or low-confidence (< 0.6) transactions
        pending_invoice_matches   — unmatched, currency-missing, or pending-review matches
    """
    with _connection() as conn:
        unclassified = conn.execute(
            """
            SELECT t.id, t.tx_date, t.description, t.amount, t.currency,
                   t.category, t.confidence, t.subcategory
            FROM transactions t
            JOIN connected_accounts ca ON t.account_id = ca.id
            JOIN bank_connections   bc ON ca.connection_id = bc.id
            WHERE bc.user_id = ?
              AND (t.category = 'unknown' OR t.confidence < 0.6)
            ORDER BY t.tx_date DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()

        pending = conn.execute(
            """
            SELECT im.id AS match_id,
                   im.status AS match_status,
                   im.confidence, im.method, im.explanation,
                   im.matched_amount, im.review_state, im.transaction_id,
                   i.id AS invoice_id,
                   i.reference, i.client_name, i.amount_due, i.currency
            FROM invoice_matches im
            JOIN invoices i ON im.invoice_id = i.id
            WHERE i.user_id = ?
              AND (im.review_state = 'pending_review'
                   OR im.status   = 'unmatched'
                   OR im.method   = 'currency_missing')
            ORDER BY im.confidence DESC, i.due_date DESC
            """,
            (user_id,),
        ).fetchall()

    return {
        "unclassified_transactions": [dict(r) for r in unclassified],
        "pending_invoice_matches":   [dict(r) for r in pending],
    }


def update_match_review_state(match_id: int, review_state: str) -> None:
    """
    Update the review_state of a match row.
    Valid values: pending_review | confirmed | rejected.

    Architecture stub for WS7+ review workflow.
    """
    with _connection() as conn:
        conn.execute(
            "UPDATE invoice_matches SET review_state = ? WHERE id = ?",
            (review_state, match_id),
        )


def persist_match_result(result, invoice_id: int) -> list[int]:
    """
    Persist a MatchResult to the database.

    For UNMATCHED, writes one row with transaction_id=NULL.
    For MULTIPLE_PAYMENTS, writes one row per transaction_id in result.transaction_ids.
    For all other statuses, writes a single row.

    Returns list of new invoice_matches.id values written.

    Parameters
    ----------
    result : reserved.matching.engine.MatchResult
    invoice_id : int
        The invoices.id FK (must already exist in DB).
    """
    match_ids: list[int] = []

    if not result.transaction_ids:
        # UNMATCHED (or aggregate with no DB-persisted transactions)
        mid = save_match(
            invoice_id=invoice_id,
            status=result.status.value,
            confidence=result.confidence,
            method=result.method,
            explanation=result.explanation,
            matched_amount=float(result.matched_amount),
            transaction_id=None,
            review_state=result.review_state.value,
        )
        match_ids.append(mid)
    else:
        # One row per transaction_id (handles single, multiple, overpaid etc.)
        per_tx_amount = float(result.matched_amount) / len(result.transaction_ids)
        for tx_id in result.transaction_ids:
            mid = save_match(
                invoice_id=invoice_id,
                status=result.status.value,
                confidence=result.confidence,
                method=result.method,
                explanation=result.explanation,
                matched_amount=per_tx_amount,
                transaction_id=tx_id if isinstance(tx_id, int) else None,
                review_state=result.review_state.value,
            )
            match_ids.append(mid)

    return match_ids
