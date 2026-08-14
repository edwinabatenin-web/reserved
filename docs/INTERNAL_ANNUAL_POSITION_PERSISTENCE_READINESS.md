# Internal annual-position persistence — design-readiness review

Review date: 13 August 2026  
Scope: design review only; no persistence, route, API or customer connection  
Decision: **NOT READY FOR PERSISTENCE**

## Bounded conclusion

The annual-position, annual-loan, composition and strict snapshot artifacts are
useful internal contracts, but none is an approved durable record. The snapshot
explicitly declares `internal_ephemeral_handoff_not_persistence_approval`, and
the composition assurance permits only ephemeral internal linking. The current
database has no table or repository contract that can preserve these objects'
identity, evidence, uncertainty and prohibitions losslessly.

The existing `tax_calculations` table must not be repurposed for them. It is a
legacy future-workstream stub with nullable identity, `REAL` money columns, a
free-form JSON input field and no contract/snapshot version, evidence policy,
provenance, uncertainty, limitations, prohibitions, integrity marker, retention
state or immutable audit history. Its additive migration model is useful
infrastructure, but is not a reviewed persistence design.

## Existing architecture relevant to the decision

- SQLite is accessed through a module-level repository. Foreign keys and WAL
  are enabled per connection, and a numeric schema-version table drives
  additive migrations.
- `users.clerk_user_id` provides a stable identity and several current tables
  carry `user_id` foreign keys. Historical compatibility leaves some ownership
  columns nullable and preserves session-key paths; that pattern is unsuitable
  for a new tax-result store.
- Some current user-owned records cascade on user deletion, while no single
  complete account-erasure workflow or tax-record retention policy is evident.
- Transaction overrides show an append-style audit-history pattern, but there
  is no equivalent calculation/snapshot event record.
- Database-level encryption, external key custody, authenticated field
  encryption and backup/restore key procedures are not evidenced here.
- The strict snapshot codec rejects unknown shape, unsupported versions,
  weakened prohibitions, combined-money fields and several semantic
  contradictions. This is valuable validation at a future boundary, but it is
  neither a storage schema nor an integrity/authenticity mechanism.

## Mandatory gates before any durable write

| Gate | Required evidence before approval | Current status |
|---|---|---|
| Tenant and identity isolation | Every record has a non-null `user_id` FK; repository reads, writes, updates and deletes require the authenticated owner; cross-user IDs and orphan/session-only writes fail closed; privileged support access is separately authorised and audited. | **Open.** Existing patterns are mixed and no annual-position repository exists. |
| Data minimisation | Approve a field-level inventory and purpose for each persisted fact; do not persist duplicate source payloads, display-only text, access tokens or unnecessary raw provider data; separate calculation record from source evidence references. | **Open.** No approved durable schema or DPIA/retention mapping exists. |
| Provenance and uncertainty survival | Losslessly retain evidence IDs, source references, observed/effective dates, selection decisions, competing evidence, status, ranges/effects, supported and unsupported families, ruleset/policy/limitation versions and calculated-at time. Round-trip tests must cover every non-calculated state. | **Open.** Internal objects carry much of this, but composition is not the adopted WP7U envelope and no lossless persistence mapping is approved. |
| Encryption and key custody | Select deployment-appropriate encryption at rest and, where required, authenticated field/envelope encryption; keep keys outside the database; document KMS/secret custody, rotation, wrong-key/tamper behavior, backup/restore and break-glass access. | **Open.** SQLite configuration alone supplies no evidenced application-managed encryption or key custody. |
| Retention and deletion | Approve purpose-specific retention periods, refresh/supersession behavior, user deletion, legal-hold exceptions, backup expiry and evidence-reference cleanup; prove deletion across all dependent records without erasing required audit events prematurely. | **Open.** Cascades exist selectively, but no annual-tax retention/deletion policy or verified whole-account erasure path is evidenced. |
| Schema and version migration | Define a durable record version distinct from the ephemeral snapshot version; pin producer contract, tax ruleset and evidence-policy versions; provide forward/backward compatibility rules, transactional migrations, rollback/recovery and fixtures for every supported stored version. Unknown versions must remain unreadable rather than silently coerced. | **Open.** Current migrations are additive and suppress duplicate-column errors; there is no annual-position version migration plan. |
| Integrity and concurrency | Use exact decimal representation, immutable record IDs, canonical bytes and an authenticated integrity mechanism; bind owner, purpose and version into integrity protection; define atomic creation/supersession and concurrency/idempotency rules. Reject truncation, field removal, replay under another owner and prohibition weakening. | **Open.** Strict decoding detects shape errors but not database substitution, replay or authorised-record history changes. Existing `REAL` fields are unsuitable for exact tax money. |
| Auditability | Append calculation creation, evidence selection, supersession, failed decode/integrity checks, access, export and deletion events with actor, time, reason and correlation IDs; redact sensitive values and prohibit secrets in logs. Audit access and retention must be defined. | **Open.** Transaction override history is not an annual-position audit design. |
| Prohibition preservation | Mandatory prohibitions and limitations are stored as governed data and revalidated on every read, migration and composition. Storage must never imply customer readiness, a combined balance, amount due, filing, payment, refund or reserve guidance. A more restrictive historical record may not be weakened by migration. | **Open.** The ephemeral decoder enforces current in-memory invariants only. |

## Required record boundary

A future design should keep three concepts distinct:

1. an immutable calculation record containing exact monetary components and the
   producer/ruleset versions;
2. immutable or append-only provenance/uncertainty records and their selection
   decisions, referenced by stable IDs; and
3. an immutable composition/link record containing typed references and
   prohibitions, with **no combined customer balance or amount due**.

Each record must be owner-bound. Supersession should create a new version and an
auditable link rather than overwrite the evidential history. Stored records
must be decoded and semantically validated before they enter trusted internal
types; database JSON must never be treated as trusted merely because it was
written by Reserved.

## Smallest safe next step

Create a documentation-and-test-only persistence contract proposal for one
synthetic `AnnualPositionResult` record. It should define:

- a field-level minimisation/data-classification table;
- non-null owner and immutable record/reference identifiers;
- canonical exact-decimal encoding and record/producer/policy versions;
- the lossless WP7U-envelope mapping, including provenance, uncertainty,
  limitations and prohibitions;
- retention, deletion, supersession and audit-event semantics;
- an approved encryption/key-custody option; and
- hostile contract tests for cross-user access, tamper/replay, unknown version,
  migration, deletion and prohibition weakening.

That proposal should receive privacy/security and independent contract review
before a migration or repository implementation is written. Until it passes,
keep all annual-position snapshots ephemeral and do not write them to
`tax_calculations`, JSON files, caches, queues or databases.

## Stopping criterion

This review stops at the first safe boundary: the exact persistence gates and a
minimal next artifact are identified. Choosing a production database,
encryption service, retention duration or legal basis requires deployment,
security, privacy and founder/legal decisions not established by the inspected
code, so none is invented here.
