# W9 privacy, security and operations completion map

## Purpose and evidence cut-off

This map gives the October-launch privacy, security and operations workstream a
finite denominator. It is a planning and assurance control, not evidence that a
control is deployed or launch-ready.

- Evidence cut-off: 4 September 2026.
- Current integration reconciliation point:
  `110a90043dfc770c70059482be9d7b7e237749a6` (tree
  `0d5b2e3e89334a58eab13f7ccdf5fb464ccf0079`).
- Inspection worktree branch: `codex-cli/w9-completion-map-110a` (an isolated
  branch based on, but not itself, the integration lineage).
- Immutable starting commit: `110a90043dfc770c70059482be9d7b7e237749a6`.
- Starting tree: `0d5b2e3e89334a58eab13f7ccdf5fb464ccf0079`.
- Starting worktree: clean.
- Evidence used: repository implementation and tests, [Founder Decisions](../FOUNDER_DECISIONS.md),
  [authentication readiness](AUTHENTICATION_READINESS.md),
  [provider boundary adoption](PROVIDER_BOUNDARY_ADOPTION.md),
  [provider pre-audit readiness](PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md),
  [annual-position persistence readiness](INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md),
  [annual-position isolation audit](INTERNAL_ANNUAL_PERSISTENCE_ISOLATION_AUDIT.md),
  [W9-S3A minimised projection contract](W9_S3A_ANNUAL_POSITION_PERSISTENCE_CONTRACT.md),
  [W9-S3B detached repository/schema contract](W9_S3B_ANNUAL_POSITION_REPOSITORY_CONTRACT.md),
  [PAYE fallback completion map](HMRC_PAYE_FALLBACK_COMPLETION_MAP.md), and
  `reserved/assurance_metadata.json` at the starting commit.

Here, **W9** means the privacy, security and operations workstream. It does not
refer to the historical annual-loan package labelled WP9 elsewhere.

## State vocabulary

- **Implemented**: code exists in an isolated or integrated repository lineage.
- **Integrated**: the code is present at the evidence cut-off and has local test
  coverage. This does not prove target-runtime operation.
- **Externally evidenced**: the required result has been observed in the
  intended provider, identity, hosting or operational environment.
- **Launch-ready**: implementation, independent review, integration, target
  evidence, privacy/security acceptance and all applicable Founder gates have
  passed.

No item should move directly from implemented to launch-ready merely because a
local test suite passes.

## Current baseline

| Boundary | Implemented/integrated evidence | What remains before launch |
| --- | --- | --- |
| Authentication and sessions | Clerk-broker token checks validate issuer, authorised party, subject and session identity; successful login establishes Reserved's signed, HTTP-only session; logout clears the complete session. Sensitive routes receive no-store headers. Local negative-claim and readiness tests exist. | Target Clerk/Google/Apple configuration, browser journeys, revocation/account-deletion handling and target-runtime negative tests remain external acceptance evidence. The current CSP still permits inline script and style execution and must be consciously accepted or tightened before launch. |
| Provider OAuth and HTTP boundaries | Provider-bound, expiring, single-use state; callback ordering; opaque credential references; injected, non-production HTTP origins; payload-redacted evidence; and fail-closed provider readiness are integrated. Configuration alone cannot make an unimplemented adapter ready. | There is no approved encrypted token store or evidenced external key custody, rotation, break-glass, runtime redaction, deployment isolation, revocation/reconnect or backup/restore behavior. Provider sandbox and production activation evidence remain gated. |
| Evidence and annual-position persistence | W9-S3A is accepted and integrated at `c489c25bab669c64e1c11d28caf29fcde9678fdd`: it defines a minimised, owner-bound, admission-sealed annual-position projection contract. W9-S3B is accepted and integrated at `110a90043dfc770c70059482be9d7b7e237749a6`: it defines a detached exact-primitive structural candidate, logical record/evidence-row shape and pure repository-operation contract. S3B deliberately does not import, trust or preserve S3A runtime admission and every result denies persistence authority. Neither package performs database, migration, retention, deletion, credential, environment or activation I/O. | There is still no authenticated S3A-to-S3B adapter, selected/verified datastore, physical schema or migration, durable read/write implementation, authenticated storage integrity, access-audit implementation, approved retention/legal-hold/backup-expiry behavior, whole-account erasure executor, encryption/key-custody implementation or target evidence. The existing `tax_calculations` stub remains unacceptable. |
| Retention, deletion and account erasure | Founder Decisions establish minimisation and deletion principles. HICBC has bounded deletion hooks. PAYE fallback records a `secure_deletion_required` disposition without claiming deletion occurred. | Field inventory, lawful purpose, retention periods, supersession, legal-hold exceptions, backup expiry, verified whole-account erasure and deletion evidence are unresolved. No actual payslip upload/extraction/raw-document deletion lifecycle exists. |
| Activation controls | Provider and identity readiness checks fail closed; provider adapters are network-inert unless explicitly enabled and evidenced. The canonical October release gate already preserves a 16-blocker inventory. | Existing readiness and release inventories must be reconciled to exact package, target and acceptance evidence rather than duplicated by another diagnostic. Production/provider enablement remains a Founder gate. |
| Monitoring and outage behavior | A local application/database health boundary and a tax-rule drift monitor exist. Integrated W9-S4A–E work adds a fail-closed provider outage/recovery contract, local/synthetic single- and multi-provider presentation and coordination, and a synthetic outage exercise (`58fb282...`, `2cb3d43...`, `43e4671...`, `8f26ee7...`, `1a277b6...`). | There is no evidenced target-runtime monitoring or alert routing, named service ownership, sandbox/real-provider outage exercise, backup/restore rehearsal or accepted production runbook. Local synthetic evidence and tax-rule monitoring do not prove target operations. |
| Restore, rollback and incident response | Database operations use bounded transactional rollback in places, and repository changes are checkpointed/revertible. | Recoverable backups, restoration tests, application/data rollback, key recovery, incident triage, security response, customer-support escalation and named operational ownership are not evidenced. Database transaction rollback is not disaster recovery. |
| Target-runtime and privacy/security acceptance | Local and synthetic test evidence exists. Readiness documents preserve missing evidence as blockers. | The target runtime, provider and identity journeys, security/privacy review, manual failure/accessibility checks and complete release gate have not passed. No production activation follows from this map. |

## Finite delivery slices

| Slice | Owned outcome | Current state | Dependencies and concurrency | Completion evidence |
| --- | --- | --- | --- | --- |
| **W9-S1 — control inventory, launch data-flow and threat boundary** | Preserve existing authentication/session, provider fail-close and canonical release controls; document the complete October data flow, trust boundaries, threats and exact unresolved security/privacy decisions without creating another readiness authority. | **Implemented and integrated; completion evidence still partial.** The launch data-flow/threat model and decision dossier were added at `8eec5d8...`, and their introducing-commit guard was corrected at `1b9a877...`. No durable package record located by this reconciliation proves the fresh independent-review disposition, so the slice is not counted complete. | Preserve the integrated evidence. Reconcile or repeat only the missing independent review; do not reimplement S1A. Target journeys remain for S5. | Independent review of exact evidence; all October flows and trust boundaries covered; threats and mitigations tied to existing controls/blockers; every unresolved choice has an owner and acceptance evidence; no environment, credential, network, persistence or activation side effects. |
| **W9-S2 — provider secret and token custody** | Implement the approved encrypted credential/token store and its provider/owner isolation, rotation, tamper, revocation, audit and key-recovery boundaries. | **Missing engineering; decision-bound.** OAuth contracts deliberately stop at an abstract store boundary. | Requires an approved target datastore/KMS or equivalent, key custody and rotation owner, access policy and backup/recovery semantics. Provider adapters can continue against opaque references while this is decided. | Architecture/security decision; bounded implementation and independent review; wrong-key, tamper, rotation, ownership and restore tests; target custody evidence. |
| **W9-S3 — durable data lifecycle** | Implement only the approved, minimised persistence for annual-position/evidence references and PAYE fallback, including retention, supersession, account erasure, backup expiry and provable raw-payslip deletion. | **Partial contract engineering is accepted and integrated; durable implementation and external evidence remain decision-bound.** S3A (`c489c25bab669c64e1c11d28caf29fcde9678fdd`) supplies the minimised admission/projection contract. S3B (`110a90043dfc770c70059482be9d7b7e237749a6`) supplies a detached, non-admitted logical row/evidence/repository-operation contract. Both are in-memory and disabled-first; neither is a datastore, migration or persistence implementation. | Preserve S3A/S3B rather than redispatching them. A separately reviewed adapter must authenticate genuine S3A output before forming an S3B structural candidate. Durable work additionally requires the approved field inventory/purpose and lawful-basis review, retention and backup-deletion schedule, erasure/legal-hold exceptions, target/datastore facts, encryption/key custody and audit-event rules. | Existing contract tests are design evidence only. Slice completion still requires approved schema/lifecycle decisions; reviewed adapter and physical implementation; migrations; ownership/integrity/concurrency and minimisation tests; target durable read/write evidence; deletion/erasure/backup-expiry evidence; and raw-payslip deletion demonstrated without logging or retaining document content. |
| **W9-S4 — operational resilience and ownership** | Establish target monitoring, safe outage behavior, recoverable backup/restore, rollback, incident/security response and customer-support escalation with named owners. | **Partial local/synthetic implementation and review evidence.** S4A–E are integrated at `58fb282...`, `2cb3d43...`, `43e4671...`, `8f26ee7...` and `1a277b6...`, covering the fail-closed outage/recovery contract, local presentation and coordination, and a synthetic exercise. This does not close S4. | Target-runtime monitoring and ownership must be named before a further runbook/monitoring package is selected. Provider-specific exercises depend on sandbox access. Backup/restore, target alert routing, real-provider behavior and external/human acceptance remain missing. | Monitors and alerts exercised; provider outage and degraded-customer paths tested in the applicable target/sandbox; backup restored; rollback rehearsed; incident/support paths and tax/API/security owners accepted. |
| **W9-S5 — target privacy/security and release acceptance** | Assemble the preceding controls in the intended runtime and complete provider/identity, privacy, security, manual failure and release assurance. | **External evidence missing.** | Depends on applicable S1-S4 gates and on launch-candidate provider and product integrations. It may collect evidence incrementally but is the final serial gate. | Target-runtime suite and browser journeys; provider sandbox evidence; privacy/security acceptance; residual-risk register; independent integrated review; Founder authorisation for activation/release. |

The accepted W9-S3 layers must be read narrowly:

| Layer | What is integrated | What it does not establish |
| --- | --- | --- |
| W9-S3A — `c489c25bab669c64e1c11d28caf29fcde9678fdd` | A minimised structured annual-position projection, local producer admission boundary, provenance/uncertainty representation, exact identity and supersession-chain contract. | No datastore, relational row, migration, retention period, legal hold, backup expiry, encryption/key custody, target write or production activation. |
| W9-S3B — `110a90043dfc770c70059482be9d7b7e237749a6` | A datastore-neutral detached primitive candidate, logical annual-position/evidence rows, governance-input gates and pure create/read/CAS/deletion-plan decisions. It is explicitly non-admitted and grants no persistence authority. | No authentication of live S3A output, adapter, database/SQL, durable read/write, atomic target CAS, migration, deletion execution, retention clock, custody, backup behavior, target runtime or activation. |

The workstream denominator remains five slices. At the cut-off, **0/5 slices
are complete (0%)**. S1 is partial, S3 now has two accepted contract layers,
and several other reusable controls are integrated, but no slice yet has all of
its required assurance. This conservative measure prevents local contracts and
tests from being mistaken for launch readiness.

## Sequence and parallelism

1. Preserve W9-S1A's integrated launch data-flow/threat and decision-dossier
   evidence. Reconcile or repeat only its missing independent-review evidence;
   do not dispatch another implementation of the same package.
2. Resolve S2 custody and the remaining S3 lifecycle/legal/privacy/target facts
   in parallel with ordinary provider/domain work. Keep credentials opaque and
   all S3 results non-durable until those gates are accepted.
3. Preserve the integrated S3A projection contract and S3B detached repository
   contract. Do not redispatch them or call them persistence. Select a further
   S3 adapter/physical-store package only after its exact authority and external
   dependencies are recorded; it must not silently choose a vendor, retention
   period, lawful basis, key owner, legal-hold rule or target runtime.
4. Preserve the integrated S4A–E local/synthetic evidence. Further S4 runbook
   or monitoring work begins only after target runtime and responsible owners
   are named; provider and restore exercises follow environment access.
5. Accumulate target evidence as it becomes available, but close S5 only once
   the complete launch candidate exists. Activation and release remain Founder
   gates.

## Terminal W9 completion gate

W9 is complete only when all of the following are true:

1. Local and target authentication/session behavior, logout, expiry,
   unauthorised access, account deletion and applicable Google/Apple journeys
   pass independent review.
2. Provider credentials and refresh tokens use an approved, owner-isolated
   custody boundary with evidenced encryption, key separation, rotation,
   revocation, audit and recovery behavior.
3. Every durably stored annual-position or source-evidence field has an approved
   purpose, owner boundary, provenance/integrity representation, retention and
   deletion rule; unapproved raw payloads and credentials are not stored.
4. Account erasure, supersession, legal exceptions, dependent evidence cleanup
   and backup expiry are implemented and verified end to end.
5. Any payslip-original flow proves secure deletion after extraction/checking,
   including failure and backup behavior, without confusing a required-deletion
   marker with proof of deletion.
6. Each identity/provider capability has a fail-closed evidence record; no
   credentials, configuration or diagnostic matrix can activate it by itself.
7. Monitoring and alerting cover application, database, provider, tax-rule and
   relevant security failures; outage and degraded-customer behavior are tested.
8. Recoverable backups, restoration and application/data rollback are tested
   against the intended runtime and custody design.
9. Incident response, security escalation, customer-support escalation and
   ownership of tax-rule, provider/API and security changes are documented and
   exercised.
10. The launch candidate passes target-runtime, provider/identity sandbox,
    privacy, security and integrated failure-path assurance with traceable,
    redacted evidence.
11. All unresolved risks are explicit and accepted by the appropriate authority;
    production/provider activation, merge/release and go-live receive their
    separate Founder authorisation.

## Current next action

W9-S1A, W9-S3A and W9-S3B are already implemented and integrated. The next
assurance action remains obtaining or repeating a fresh independent review of
the exact W9-S1A evidence. In parallel, named legal/privacy/security/operations
owners must supply and accept the remaining S2/S3 evidence recorded in
`W9_SECURITY_DECISION_DOSSIER.md`, including exact retention/erasure/legal-hold
and backup-expiry rules, custody and target/datastore facts.

`FD-W9-001` authorises the bounded minimised persistence design represented by
S3A/S3B, but expressly leaves those legal/privacy/security/target matters open.
`FD-OA-001` permits routine bounded engineering and reconciliation; it does not
answer them or enlarge persistence, production, deployment or activation
authority. Any consequential target/production choice and final activation or
release remains behind its applicable Founder gate.

No W9-S2 credential-custody implementation, S3A-to-S3B authentication adapter,
W9-S3 datastore/migration or durable write is authorised merely by this
reconciliation. S3A and S3B reduce design uncertainty but do not satisfy the
approved target/custody/lifecycle, human-review or external-evidence gates. The
integrated W9-S4A–E local/synthetic evidence is preserved, but no new S4 package
is selected until target runtime and ownership are named. This map grants no
new implementation, environment, credential, persistence, migration or
activation authority.

## Out of scope

This map does not authorise production access, provider activation, credentials,
real customer or bank data, payments, filing, deployment, merge/release/go-live,
new provider scope, Scotland, VAT, Ireland/Europe, or optional post-launch
sophistication. It does not amend Founder Decisions or the Control Plane.
