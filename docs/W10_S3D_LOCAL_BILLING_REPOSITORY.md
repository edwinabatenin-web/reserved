# W10-S3D local transactional billing repository

## Status

**Evidence cut-off:** 4 September 2026

**Candidate status:** IMPLEMENTATION CANDIDATE READY FOR INDEPENDENT REVIEW.
This is an uncommitted, review-ready candidate only. It is **not** a claim of
W10 completion, production custody, provider authenticity, launch readiness or
independent acceptance.

**Writable candidate paths (the only paths touched):**

- `reserved/billing/local_billing_repository.py`
- `tests/test_w10_local_billing_repository.py`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`

All other files were read-only during this work, including Founder Decisions,
the completion map, application database/schema, routes, existing billing
contracts, security/assurance metadata and prior tests.

## Boundary

`reserved/billing/local_billing_repository.py` is a caller-supplied,
disposable, file-backed SQLite persistence and ordering primitive for the
settled October subscription lifecycle. It is **opt-in**: no module-level
database path, no import side effects, no application registration, no default
owner mapping, no HTTP endpoint and no entitlement grant.

It stores only minimised synthetic identifiers, canonical billing facts,
content identities, append-only ordering and bounded reconciliation
dispositions. It stores **no** raw provider payloads, personal data, secrets,
arbitrary log text or signed credentials. Temporary test data does not settle
production retention, erasure/legal hold, backups, custody, authenticated
storage integrity, provider admission or migration authority.

Owning Codex selected Python stdlib SQLite as the explicit disposable-local
engineering datastore for this package only. Schema ownership is this module;
no migration of the application database is authorised.

## What this is not

This module is **not** a provider-admission or authenticated-storage boundary.
A persisted row is a **structural projection, never an authenticated fact**.
No producer here stamps `authenticated=True` merely from a row or hash; that
remains the independent source-admission responsibility of W10-S3C/S5D and any
future authenticated ingress. The file is a same-process / co-operating-process
engineering datastore, not a defence against a hostile host administrator who
can rewrite or replace the SQLite file. Untrusted SQLite rows are not treated
as authenticated facts.

## Schema

`SCHEMA_VERSION = reserved-w10-local-billing-repository-schema/1.0`. The schema
is versioned and digest-verified; `create` builds it in one transaction (and
rolls back the whole file on any DDL failure) and `open` verifies — against the
live schema, not merely a stored digest — the version, digest, expected
table/column shape, each table's primary-key column order, each required
explicit `CREATE [UNIQUE] INDEX` (name, uniqueness, column order and
partial-index predicate), the absence of any trigger/view executable schema, and
`PRAGMA integrity_check`. Missing, corrupt, unsupported or partial schema
(including a dropped unique index, an altered partial-index predicate, an added
table, an altered primary key or an injected trigger) fails
closed with `LocalBillingRepositoryError` and never performs destructive
repair, history replacement or application-database migration.

Tables:

- `repository_meta` — version/digest/purpose/creation stamp.
- `billing_journal` — append-only minimised observations, keyed by
  `(owner_id, billing_account_id, subscription_id, sequence)` with a unique
  `(source_namespace, source_event_id)` identity index.
- `subscription_head` — one current head pointer per
  `(owner_id, billing_account_id, subscription_id)`.
- `reconciliation_disposition` — append-only bounded dispositions for reused
  source identities.

## Exact settled meanings reused

The module re-uses, without reinterpretation, the settled lifecycle meanings
already enforced in `reserved.billing.contracts` and
`reserved.billing.runtime_entitlement_admission`:

- exact catalogue identities `PLAN_KEYS = {monthly, six_month, yearly}`
  (FD-W10-001), cross-checked against `contracts.PlanKey`;
- the exact W10-S3C billing-fact state vocabulary `{paid, payment_recovery,
  suspended}`;
- exact observation kinds (canonical lifecycle kinds plus zero-effect
  reconciliation-only kinds), derivation kinds and withdrawal attributions;
- the one non-extendable seven-calendar-day `payment_recovery` period
  (FD-W10-003) and the verified full current-period withdrawal / restoration
  policy (FD-W10-004) are **not** reimplemented here — they remain enforced by
  S3C at the admission boundary. This module only persists their inputs.

## Ordering and concurrency

`append_observation` atomically commits the journal entry and the head
advancement together (single `BEGIN IMMEDIATE` transaction), or neither.

- An exact duplicate (same source identity and same content identity) is
  idempotent.
- A reused source identity with different content is quarantined in
  `reconciliation_disposition` and fails closed; it never rewrites accepted
  history or advances access.
- A stale, out-of-order or forked successor fails closed by comparing the
  caller-supplied `expected_predecessor_identity` and `expected_sequence`
  against the current head.
- Two real competing connections/processes advancing the same predecessor are
  serialised by `BEGIN IMMEDIATE`; at most one succeeds (verified by test).

The head advancement is a compare-and-swap on the expected predecessor: the
head only moves when the caller's predecessor matches the persisted current
head. Reopening from another process re-derives the same duplicate/order/fork
decisions without any in-memory authority.

## Validation

All identifiers, enums, dates and instants are validated before any write.
Identifiers are bounded, character-class-restricted and secret-marker-rejected.
Dates are exact `date`; instants must be timezone-aware UTC. `paid_through` is
required only for confirmed-payment observations. Confirmed payments require a
current paid period; non-payment observations must not carry `paid_through`.
Disposition `reason` is an **exact bounded vocabulary**
(`RECONCILIATION_DISPOSITION_REASONS`), never free text, a log fragment or
secret-shaped material, and persists exactly across close/reopen.
Paths are validated for unsafe forms: no URI query/fragment, no `:memory:`, no
symlink, create refuses pre-existing paths and open refuses missing/non-regular
files. `busy_timeout_seconds` is bounded between 0 and 60 seconds.

## Correction (post independent recovery/review)

Fresh correction v1, not a replay of failed runtime
`96d4f1b0-b51d-4d84-a39c-07955da76846` (preserved as `execution_unverified`).
Six independent blocking findings were fixed and each gained a reproducible
regression test plus negative controls. This v1 list did **not** establish that
all schema/history integrity was already fully verified: an independent
recovery/re-review (job `a8e171f4-781d-4950-b794-2846bc922f7b`) later found two
residual defects — partial required-index predicates still accepted, and deleted
history / a mismatched head state silently overwritten by append — corrected
separately as v2 below:

1. **Bounded disposition reason.** `_bounded_reason` previously accepted free
   text up to 240 characters; a secret-shaped reason survived close/reopen. It
   now accepts only the exact `RECONCILIATION_DISPOSITION_REASONS` vocabulary
   and rejects arbitrary/secret-shaped text.
2. **Structural schema verification.** `_verify_schema` previously trusted the
   stored digest and checked column names only, so dropping the
   `billing_journal_source_identity_unique` index still permitted `open`. It
   now validates live PK column order, explicit indexes (name/uniqueness/column
   order **and partial-index predicate**) and rejects any trigger/view
   executable schema; it fails closed on altered/missing/extra schema without
   repair. Adversarial triggers remain a deliberately controlled test fixture,
   not accepted production schema.
3. **Plan and temporal binding.** `append_observation` previously checked only
   sequence and predecessor identity, accepting monthly→yearly and temporal
   effective/transition regression. It now binds the accepted catalogue/plan
   identity and rejects effective-date and transition-instant regression,
   without inferring plan-change or proration policy. Equal-time exact
   duplicates and runtime lifecycle semantics are preserved.
4. **Backing-row chain consistency.** Corrupting a prior journal
   `evidence_reference` without updating its digest previously still allowed a
   head read and successor, detected only later by `journal()`. Head read and
   advancement now verify the backing row/content identity and full chain/head
   consistency — including a missing origin/interior/tail sequence, a mismatched
   head state/identity, a broken predecessor link and orphan journal/head rows —
   on both reads and inside the advancement transaction; corrupt/inconsistent
   state cannot become a predecessor and append never silently repairs it.
5. **Owner-scoped dispositions.** Dispositions with the same namespace/event
   under different owners previously joined one sequence chain, and reads had
   no owner/account/subscription scope. Writes, queries, unique identity and
   predecessor selection are now bound to exact ownership; no cross-owner chain
   or read disclosure. Global source-event reuse conflict detection is
   preserved without leaking another owner's data.
6. **Whole-transaction rollback.** Injecting a `RuntimeError` at
   `_upsert_head_row` after journal insertion previously left a connection
   `in_transaction` with one visible journal row and no head. All unsuccessful
   transaction exits now roll back (not just SQLite errors and the module's own
   exception), while the intentional committed-quarantine path is preserved.
   Disposition and create paths have the same all-or-nothing behaviour.

## Correction v2 (residual defects)

Fresh correction v2, not a replay or continuation of the unverified execution.
Two independently demonstrated residual defects remain after v1 and are now
fixed, with exact reproductions plus negative controls:

1. **Partial required-index predicate was ignored.** In a disposable created DB,
   dropping `billing_journal_source_identity_unique` and recreating the same
   named `UNIQUE` index on `(source_namespace, source_event_id)` with a partial
   `WHERE` predicate still permitted `open`. `_verify_schema` now also compares
   the partial-index flag/predicate, not only name/columns/unique flags, and
   rejects any altered predicate. Recreating the identical **non-partial** index
   still opens (negative control), while two distinct predicates fail closed.
2. **History/head consistency was not fully enforced on reads and append.**
   After appending sequences 1 and 2, deleting sequence 1 still permitted a
   `current_head` of 2, `journal()[2]` and a successor `append` 3 (missing
   origin). Independently, changing `subscription_head.state` from `paid` to
   `suspended` was rejected on `current_head` read but a valid successor append
   silently overwrote it. Reads and the advancement transaction now validate the
   complete chain/head — missing origin/interior/tail, mismatched head
   state/identity, broken predecessor link and orphan journal/head rows — and
   fail closed without any silent repair by append. Exact replay/idempotency,
   ownership isolation and bounded locking are preserved, and a failed mutation
   leaves the DB unchanged with the connection usable/safely closed, including
   reopen and concurrent successor competition.

This document previously overstated that all schema/history integrity was
already verified; that claim is corrected. Nothing here asserts resistance to a
hostile host administrator, who can rewrite or replace the SQLite file; rows and
hashes remain structural projections, not authenticated facts.

## Correction v3 (residual defects)

Fresh correction v3, not a replay or continuation of the unverified execution.
Three independently reproduced residual defects remain after v2 and are now
fixed, with exact reproductions plus meaningful variant/negative controls:

1. **Actual table constraints were still only partially checked.** Rebuilding the
   declared schema with only `source_event_id TEXT NOT NULL` changed to
   `source_event_id TEXT` still permitted `open`. `_verify_schema` now validates
   the live versioned column semantics (declared type, nullability and default)
   and each table's declared `CHECK`/`UNIQUE`/`FOREIGN KEY` constraints — not
   only column names, PK order, index shape or the stored digest. Altered schema
   fails closed without repair/migration; an identical legitimate schema still
   opens (negative control).
2. **Multi-query reads had no stable transaction snapshot.** On two real SQLite
   connections, committing a valid successor after the reader had fetched the
   journal sequence but before it fetched the head made `current_head()` raise
   `head is inconsistent with journal tail` on a valid database (the next read
   then succeeded). `current_head` and `journal` now execute their validation
   plus returned head/journal inside one bounded SQLite transaction
   (`BEGIN`/`ROLLBACK`, `DEFERRED`), returning a single internally consistent
   snapshot. `reconciliation_dispositions` performs a single ordered `SELECT`
   and therefore already returns one SQLite-statement-atomic snapshot; it does
   not open an explicit read transaction. No global lock, no infinite retry, no
   weakened corruption checks and no intermediate/stale row masquerading as a
   verified newer head; atomic append/CAS is preserved.
3. **Generated quarantine disposition IDs collided across distinct events.**
   Appending two distinct events for one owner, then conflicting content for each
   with the same supplied digest, quarantined the first but the second hit a
   generic transaction failure and lost its disposition. The generated
   `disposition_id` now binds deterministically to the complete bounded
   disposition identity (owner, account, subscription, source namespace and
   source event) instead of only owner/digest/per-event sequence. Both distinct
   conflicts are retained, neither advances or rewrites journal/head, same-event
   sequencing and reopen remain correct, and the generated IDs expose no raw
   payloads, digests or cross-owner material.

All previous exact fixes and their negative controls remain: bounded reasons;
actual PK/index/partial-predicate checks; plan/time monotonicity; complete
history/head consistency on read and append; scoped dispositions; complete
rollback; duplicate replay without head rewind; two-process successor race.

## Correction v4 (approved-schema semantics and evidence precision)

Fresh correction v4, not a replay or continuation. Two residual issues remain
after v3 and are now fixed, with exact reproductions and negative controls:

1. **Approved-schema comparison/conflict semantics were still only partially
   checked.** `_verify_schema` validated column/index names and structural
   properties but not the exact declaration. Rebuilding the declared schema with
   legitimate metadata while changing only comparison or conflict semantics —
   `owner_id TEXT NOT NULL COLLATE NOCASE`, `source_event_id` column or
   source-identity index `COLLATE NOCASE`, or journal primary key
   `ON CONFLICT REPLACE` — still permitted `open`, and the collation changes
   leaked exact-case isolation (a `USERS:17` head/journal returned the original
   `users:17` owner's rows) or falsely quarantined distinct-case events
   (`evt-1` versus `EVT-1`). `_verify_schema` now compares the exact normalised
   `sqlite_master` declaration of every owned table and index against the
   approved-schema identity derived from `_SCHEMA_DDL`, so any declaration
   change — table-column and index collations, primary/unique conflict policy,
   generated columns, `STRICT`/`WITHOUT ROWID` markers and every other
   CREATE-text difference — fails closed before use, without repair/migration
   and without a general SQL parser or a change to the approved schema. An
   ordinary legitimate create/open/reopen remains accepted (negative control),
   and a rejected `open` leaves the underlying file byte-for-byte unchanged.
2. **Evidence precision.** The v3 note overstated `reconciliation_dispositions`
   as executing inside a bounded read transaction; the method performs a single
   ordered `SELECT` and never calls `_with_read_snapshot`. The description above
   now states the actual single-query behavior instead of adding transaction
   machinery solely to match a narrative.

Nothing here asserts resistance to a hostile host administrator who can rewrite
or replace the SQLite file, nor to a hostile file modified after `open`; rows
and hashes remain structural projections, not authenticated facts.

## Tests (regression additions)

v1 added 13 focused regression tests (total 53 in this file) covering the six
findings and negative controls: bounded-reason rejection plus exact
close/reopen persistence; dropped-unique-index, extra-table and injected-trigger
open failures; plan-change and effective-date/transition regression rejection;
corrupt prior journal content detected on head read and advancement, and orphan
head-without-row read failure; owner-scoped disposition chains with no
cross-owner read disclosure; and `RuntimeError` rollback on head-upsert,
disposition-insert and create-DDL paths with reusable/clean connection
afterwards.

v2 added 10 further regression tests (total 63 in this file): three open-time
partial-index predicate rejections (two distinct predicates) plus an
identical-recreation negative control, and seven full chain/head-consistency
tests — missing origin, missing interior, missing tail, head-state tamper,
head-identity tamper, orphan journal-without-head, and an intact-chain negative
control — asserting fail-closed reads and append, unchanged DB on failed
mutation, and a usable/reopenable connection afterwards.

v3 added 10 further regression tests (total 73 in this file): a dropped
`NOT NULL` column-constraint reproduction, five altered column/constraint
variants (declared type, added default, added `CHECK`, added table-level
`UNIQUE`, added `FOREIGN KEY`) plus an identical-schema negative control; a
deterministic two-connection interleaving proving a concurrent writer cannot
tear a read snapshot, plus a transaction-rollback/connection-usability control
for both successful and corruption-failing reads; and a distinct-events-same-
digest test proving two quarantine dispositions are both retained with distinct
IDs while journal/head stay at sequence 2, same-event sequencing survives reopen,
and generated IDs expose no raw payloads/digests/cross-owner material.

v4 added 7 further regression tests (total 80 in this file): four exact
approved-schema reproductions (owner column `COLLATE NOCASE`, source-event
column `COLLATE NOCASE`, source-identity index `COLLATE NOCASE`, journal
primary-key `ON CONFLICT REPLACE`) all rejected at `open`; an ordinary-schema
cross-owner denial control (`USERS:17` returns none of `users:17`'s rows); a
distinct-case event control (`evt-1` and `EVT-1` remain two separate
non-quarantined sequences); and an unchanged-data-on-rejected-open control (the
underlying file is byte-for-byte identical and its rows/tables are preserved).


## Test coverage

`tests/test_w10_local_billing_repository.py` covers, on disposable synthetic
databases in `pytest` temporary directories only:

1. close/reopen durability and an independent-process read/write of the same
   file;
2. owner/account/subscription isolation and invalid identifier/type/enum
   rejection;
3. exact duplicates, reused-identity/content conflicts and stale/out-of-order/
   forked successors;
4. two real competing processes where at most one advances a predecessor;
5. atomic rollback on mid-transaction failure (forced via a test-only trigger)
   with no partial journal/head state;
6. missing/corrupt/unsupported/partial schema and bounded lock errors;
7. synthetic composition (test-only trusted ingress) for initial payment, one
   non-extendable seven-day recovery period, expiry, verified full
   current-period withdrawal, only already-authorised restoration, and
   ambiguous withdrawal that preserves valid access without creating or
   extending entitlement;
8. rehydrated structural rows alone fail runtime admission, and no raw
   payload/secret columns exist;
9. no import/default-path mutation, no production routing, no credentials, and
   a stdlib-only import surface.

The synthetic issuer lives only in the test file (`_test_only_authority`) and
does not ship in the product module.

## Verification (commands and results)

Interpreter: Python 3.14 at
`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`. Synthetic
`pytest` temp databases only; no application/user database, network, provider or
credential use.

Focused suite:

```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_w10_local_billing_repository.py
# 80 passed in 4.59s
```

Full affected matrix (repository / core / event-inbox / S3C / S5D — the five
modules named by the authority):

```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_w10_local_billing_repository.py tests/test_w10_entitlement_core.py tests/test_w10_event_inbox_contract.py tests/test_w10_runtime_entitlement_admission.py tests/test_w10_paid_access_guard.py
# 372 passed, 1 failed in 6.08s
```

This matches the independent baseline shape (v3: 73 focused within 365 affected
pass) shifted by exactly the 7 added focused tests (80 within 372 affected
pass).

The single affected-suite failure is the pre-existing historical S5D
dirty-candidate scope sentinel
`test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base`.
It is an **expected, separate scope-sentinel failure**, not a regression: the
sentinel's allowlist predates and rejects these three authorised new paths. Its
allowlist was deliberately **not** edited, per instruction.

Whole W10 billing cluster (broader context):

```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_w10*.py
# 6 failed, 1285 passed in 30.65s
```

All six failures are the same class of pre-existing global dirty-candidate
scope sentinel (one per owning file: `completion_map`, `initial_paid_presentation`,
`initial_payment_presentation`, `internal_route_hardening`, `paid_access_guard`,
`q1_q2_policy_closure`). None is a behavioural failure of this package; each
merely rejects the three new untracked paths against a stale allowlist.


## Limitations

- No real provider-admission path: source events are caller-supplied and this
  module cannot establish that a source event is authentic.
- No authenticated storage: rows and hashes are structural projections, not
  authenticated facts; there is no attestation, signing or tamper-evident
  storage here.
- No automatic replay, destructive migration, history replacement or manual
  entitlement override.
- SQLite is a co-operating-process datastore; it does not defend against a
  hostile host administrator.

## Exact candidate paths

- `reserved/billing/local_billing_repository.py`
- `tests/test_w10_local_billing_repository.py`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`

## Frozen identities (pre-v2 baseline, SHA-256)

Verified before editing, matching durable candidate tree
`adb599381c55fb9308db0866c37e5c029baf74a5` at base
`064eac2d339038b942897c6e58e24cf496c1d7ae`:

- `reserved/billing/local_billing_repository.py`
  `18a1fa477aa86531dbe337670ba6094d57d7771f04e4990d69cd2ac560b62246`
- `tests/test_w10_local_billing_repository.py`
  `f5aa806506d8681a56320241986958c8545a27cedfcf8b941bfdac39eb379398`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`
  `86c6c7b7ebb63920f3356277988b5973cce4181ff9d64d3ede57f4e1251be5ce`

## Final frozen hashes (SHA-256, after v2 correction)

- `reserved/billing/local_billing_repository.py`
  `c9cb207cbf39ea5067bdfa162cea9b02b0ad40c5d3c1c36897117d2c3b5218aa`
- `tests/test_w10_local_billing_repository.py`
  `1236e637f1be9dbab1b02c0f06b937afd955c35fba59852afef6d6e72cd645de`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`
  `29fab78c8c24a3d0d347b7ceaa5063a8df3870dd0cb299f08e03407f510b8095`

## Final frozen hashes (SHA-256, after v3 correction)

- `reserved/billing/local_billing_repository.py`
  `5aeb5009d09ad81c442860eb166b871cbd6041bfd2d1d2fd21093c7b9e819dd6`
- `tests/test_w10_local_billing_repository.py`
  `ae03de70d9dd7af023238bace7a942b3c4bab1f93d8910cffdd91a2f45be95fd`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`
  (this document's own hash is reported separately after final edit, since
  inlining it would self-modify the file)

## Final frozen hashes (SHA-256, after v4 correction)

- `reserved/billing/local_billing_repository.py`
  `469825766f1ae5058128dfa270bc9ab06327f786bd1e8ba05b923d3d6accef5e`
- `tests/test_w10_local_billing_repository.py`
  `8d0179223b34333697cece3f7b28e86fd0c9cd6ff1458be2d698d6e19f912c62`
- `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md`
  (this document's own hash is reported separately after final edit, since
  inlining it would self-modify the file)


## Final output

IMPLEMENTATION CANDIDATE READY FOR A DIFFERENT INDEPENDENT REVIEWER (uncommitted,
review-ready; not self-assurance, not a completion claim).
