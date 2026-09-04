# W9 privacy, security and operations completion map

## Purpose and evidence cut-off

This map gives the October-launch privacy, security and operations workstream a
finite denominator. It is a planning and assurance control, not evidence that a
control is deployed or launch-ready.

- Evidence cut-off: 4 September 2026.
- Current integration reconciliation point:
  `b8ce971f4dc6b8a1ced10e9b490be68d481752de` (tree
  `7fcc5be531c5a4331e6a7ff65ce18a33e1772766`).
- Inspection worktree branch: `codex/w9-w10-map-post-s3d` (an isolated
  branch based on, but not itself, the integration lineage).
- Immutable starting commit: `b8ce971f4dc6b8a1ced10e9b490be68d481752de`.
- Starting tree: `7fcc5be531c5a4331e6a7ff65ce18a33e1772766`.
- Starting worktree: clean.
- Evidence used: repository implementation and tests, [Founder Decisions](../FOUNDER_DECISIONS.md),
  [W9-S1 independent-review findings](W9_S1_INDEPENDENT_REVIEW_EVIDENCE.md),
  [W9-S1 launch data-flow and threat model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md),
  [W9-S1 security decision dossier](W9_SECURITY_DECISION_DOSSIER.md),
  [W9 security/operations gap register](W9_SECURITY_OPERATIONS_GAP_REGISTER.md),
  [authentication readiness](AUTHENTICATION_READINESS.md),
  [provider boundary adoption](PROVIDER_BOUNDARY_ADOPTION.md),
  [provider pre-audit readiness](PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md),
  [annual-position persistence readiness](INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md),
  [annual-position isolation audit](INTERNAL_ANNUAL_PERSISTENCE_ISOLATION_AUDIT.md),
  [W9-S3A minimised projection contract](W9_S3A_ANNUAL_POSITION_PERSISTENCE_CONTRACT.md),
  [W9-S3B detached repository/schema contract](W9_S3B_ANNUAL_POSITION_REPOSITORY_CONTRACT.md),
  [W9-S3C validating non-durable detachment adapter](W9_S3C_PROJECTION_REPOSITORY_ADAPTER.md),
  [W9-S3D authenticated runtime-owner adapter](W9_S3D_AUTHENTICATED_OWNER_ADAPTER.md),
  [PAYE fallback completion map](HMRC_PAYE_FALLBACK_COMPLETION_MAP.md),
  [W10 completion map](W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md),
  [W10-S2C policy evidence candidate](W10_S2C_POLICY_EVIDENCE_DOSSIER.md), and
  `reserved/assurance_metadata.json` at the starting commit.
- The W9-S1 independent-review record integrated at
  `81ae02044cccd921d98a0d1fc2360e1c4a983ab1` and its findings-driven W9-S1B
  reconciliation are independently accepted and integrated in this lineage at
  `587828337e01f269320048847b3250a690ce6133`. That acceptance establishes the
  accuracy and current-state provenance of the findings/reconciliation only; it
  is not assurance acceptance of the 13 unnamed decision owners, unresolved
  risks, missing target/provider evidence, or W9-S1 completion.
- The later W10 completion-map reconciliation at
  `5612f7a33f27f09d1fa988f15dfdffbe77a72705` and W10-S2C historical
  accepted/integrated evidence at `a07348976321df65bbd95c9170c906bcddd5baa5`
  remain evidence-only and leave W10 incomplete. They do not
  activate billing, accept the unresolved policies, or alter W9's S1–S5 state;
  the S1B provider-neutral W10 non-authority boundary therefore remains current.
- `FD-W9-001` is durably settled in ancestor
  `10fb93e2e6ab567a72d2370c1603768a7ac04bb5`; it selects a minimised structured
  annual position but does not select a datastore, retention/custody policy or
  target-runtime implementation.

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
| W9-S1 control inventory and threat evidence | The independent-review findings record is accepted/integrated at `81ae02044cccd921d98a0d1fc2360e1c4a983ab1`, and W9-S1B is accepted/integrated at `587828337e01f269320048847b3250a690ce6133`. S1B reconciles the launch model, decision dossier, gap register and evidence test to the accepted lineage; it preserves exactly 15 flows, 14 trust boundaries, 21 threats and 14 decisions, and brings the W9-S3A/S3B, W9-S4A–E and provider-neutral W10 local contract/inventory descriptions current. The gap register's candidate-era `ACT-01` and “Immediate package boundary” statements selecting S1B and fresh review are historical and satisfied by `5878283...` plus its independent acceptance; they are not a current redispatch instruction. | W9-S1 remains incomplete. Thirteen of the 14 decision entries still identify their accountable human role as “to be named”, and the required dated human, provider, target, legal, privacy, security and operations evidence has not been accepted. Every substantive gap row remains open unless separately evidenced; marking the S1B self-reference satisfied accepts no unresolved risk. |
| Authentication and sessions | Clerk-broker token checks validate issuer, authorised party, subject and session identity; successful login establishes Reserved's signed, HTTP-only session; logout clears the complete session. Sensitive routes receive no-store headers. Local negative-claim and readiness tests exist. | Target Clerk/Google/Apple configuration, browser journeys, revocation/account-deletion handling and target-runtime negative tests remain external acceptance evidence. The current CSP still permits inline script and style execution and must be consciously accepted or tightened before launch. |
| Provider OAuth and HTTP boundaries | Provider-bound, expiring, single-use state; callback ordering; opaque credential references; injected, non-production HTTP origins; payload-redacted evidence; and fail-closed provider readiness are integrated. Configuration alone cannot make an unimplemented adapter ready. | There is no approved encrypted token store or evidenced external key custody, rotation, break-glass, runtime redaction, deployment isolation, revocation/reconnect or backup/restore behavior. Provider sandbox and production activation evidence remain gated. |
| Evidence and annual-position persistence | W9-S3A is accepted and integrated at `c489c25bab669c64e1c11d28caf29fcde9678fdd`: it defines a minimised, owner-bound, admission-sealed annual-position projection contract. W9-S3B is accepted and integrated at `110a90043dfc770c70059482be9d7b7e237749a6`: it defines a detached exact-primitive structural candidate, logical record/evidence-row shape and pure repository-operation contract. W9-S3C is accepted at `c9bdaa6538d68c0c64b2dcde97f224a69c089d30` and integrated at `5f5a948891e1e812a5c74ff6c7266d153bb492fa`: it validates the exact live admitted S3A projection and binds caller-supplied expected owner/business references before constructing an S3B-compatible candidate, while remaining explicitly non-durable and non-authoritative. W9-S3D is accepted at source checkpoints `98e4887e038f9ada1f090b0723837f3cb49eb8af` and `2ccafb00047583979e55e0ebb4fb193f17abe659`, and integrated at `5f7b76408a5d72b71be71d0e5d6c7a6edde260b7` and `b8ce971f4dc6b8a1ced10e9b490be68d481752de`: its exact three-path boundary binds the current signed-session `users.id` to S3C's canonical owner reference, while the business reference remains separately supplied and unauthenticated as membership. None of S3A-D performs database, migration, retention, deletion, credential, environment or activation I/O. | Owner-to-business membership authorisation, selected/verified datastore, physical schema and migration, durable read/write implementation, authenticated storage integrity, access-audit implementation, approved retention/legal-hold/backup-expiry behavior, whole-account erasure executor, encryption/key-custody implementation and target evidence remain missing. The existing `tax_calculations` stub remains unacceptable. |
| Retention, deletion and account erasure | Founder Decisions establish minimisation and deletion principles. HICBC has bounded deletion hooks. PAYE fallback records a `secure_deletion_required` disposition without claiming deletion occurred. | Field inventory, lawful purpose, retention periods, supersession, legal-hold exceptions, backup expiry, verified whole-account erasure and deletion evidence are unresolved. No actual payslip upload/extraction/raw-document deletion lifecycle exists. |
| Activation controls | Provider and identity readiness checks fail closed; provider adapters are network-inert unless explicitly enabled and evidenced. The canonical October release gate already preserves a 16-blocker inventory. | Existing readiness and release inventories must be reconciled to exact package, target and acceptance evidence rather than duplicated by another diagnostic. Production/provider enablement remains a Founder gate. |
| Monitoring and outage behavior | A local application/database health boundary and a tax-rule drift monitor exist. Integrated W9-S4A–E work adds a fail-closed provider outage/recovery contract, local/synthetic single- and multi-provider presentation and coordination, and a synthetic outage exercise (`58fb282...`, `2cb3d43...`, `43e4671...`, `8f26ee7...`, `1a277b6...`). | There is no evidenced target-runtime monitoring or alert routing, named service ownership, sandbox/real-provider outage exercise, backup/restore rehearsal or accepted production runbook. Local synthetic evidence and tax-rule monitoring do not prove target operations. |
| Restore, rollback and incident response | Database operations use bounded transactional rollback in places, and repository changes are checkpointed/revertible. | Recoverable backups, restoration tests, application/data rollback, key recovery, incident triage, security response, customer-support escalation and named operational ownership are not evidenced. Database transaction rollback is not disaster recovery. |
| Target-runtime and privacy/security acceptance | Local and synthetic test evidence exists. Readiness documents preserve missing evidence as blockers. | The target runtime, provider and identity journeys, security/privacy review, manual failure/accessibility checks and complete release gate have not passed. No production activation follows from this map. |

## Finite delivery slices

| Slice | Owned outcome | Current state | Dependencies and concurrency | Completion evidence |
| --- | --- | --- | --- | --- |
| **W9-S1 — control inventory, launch data-flow and threat boundary** | Preserve existing authentication/session, provider fail-close and canonical release controls; document the complete October data flow, trust boundaries, threats and exact unresolved security/privacy decisions without creating another readiness authority. | **Implemented and integrated; completion evidence remains partial.** The S1 independent-review findings record (`81ae02044cccd921d98a0d1fc2360e1c4a983ab1`) and findings-driven S1B current-state reconciliation (`587828337e01f269320048847b3250a690ce6133`) are accepted/integrated as exact local evidence. The model, decision dossier, gap register and test now cover the accepted lineage and preserve all 15 flows, 14 boundaries, 21 threats and 14 decisions. This does not complete S1: 13 decision owners remain “to be named”, and required human/provider/target/legal/privacy/security/operations evidence is not accepted. | Preserve S1A/S1B; do not repeat or redispatch their evidence-only work. Name the accountable roles without inferring them, obtain their dated evidence/acceptance, and complete the applicable target/provider journeys under S5. | The accepted structural review/reconciliation is necessary but insufficient. Slice completion still requires every unresolved choice to have a named accountable owner and accepted evidence, plus independent review of the exact resulting launch candidate; no environment, credential, network, persistence or activation side effects. |
| **W9-S2 — provider secret and token custody** | Implement the approved encrypted credential/token store and its provider/owner isolation, rotation, tamper, revocation, audit and key-recovery boundaries. | **Missing engineering; decision-bound.** OAuth contracts deliberately stop at an abstract store boundary. | Requires an approved target datastore/KMS or equivalent, key custody and rotation owner, access policy and backup/recovery semantics. Provider adapters can continue against opaque references while this is decided. | Architecture/security decision; bounded implementation and independent review; wrong-key, tamper, rotation, ownership and restore tests; target custody evidence. |
| **W9-S3 — durable data lifecycle** | Implement only the approved, minimised persistence for annual-position/evidence references and PAYE fallback, including retention, supersession, account erasure, backup expiry and provable raw-payslip deletion. | **Partial contract engineering is accepted and integrated; durable implementation and external evidence remain decision-bound.** S3A (`c489c25bab669c64e1c11d28caf29fcde9678fdd`) supplies the minimised admission/projection contract. S3B (`110a90043dfc770c70059482be9d7b7e237749a6`) supplies a detached, non-admitted logical row/evidence/repository-operation contract. S3C (`c9bdaa6538d68c0c64b2dcde97f224a69c089d30`, integrated at `5f5a948891e1e812a5c74ff6c7266d153bb492fa`) validates the exact live admitted S3A projection, binds the supplied expected owner/business references and forms a detached S3B candidate without granting persistence authority. S3D source checkpoints `98e4887e038f9ada1f090b0723837f3cb49eb8af` and `2ccafb00047583979e55e0ebb4fb193f17abe659` are integrated at `5f7b76408a5d72b71be71d0e5d6c7a6edde260b7` and `b8ce971f4dc6b8a1ced10e9b490be68d481752de`; its exact three-path boundary authenticates the current session owner only, not owner-to-business membership. All four remain non-durable local contract/adapter layers; none is a datastore, migration or persistence implementation. | Preserve S3A/S3B/S3C/S3D rather than redispatching them. Owner-to-business membership remains required. Durable work also requires the approved field inventory/purpose and lawful-basis review, retention and backup-deletion schedule, erasure/legal-hold exceptions, target/datastore facts, encryption/key custody and audit-event rules. | Existing contract/adapter tests are design evidence only. Slice completion still requires approved schema/lifecycle decisions; authenticated owner-to-business membership and reviewed physical implementation; migrations; ownership/integrity/concurrency and minimisation tests; target durable read/write evidence; deletion/erasure/backup-expiry evidence; and raw-payslip deletion demonstrated without logging or retaining document content. |
| **W9-S4 — operational resilience and ownership** | Establish target monitoring, safe outage behavior, recoverable backup/restore, rollback, incident/security response and customer-support escalation with named owners. | **Partial local/synthetic implementation and review evidence.** S4A–E are integrated at `58fb282...`, `2cb3d43...`, `43e4671...`, `8f26ee7...` and `1a277b6...`, covering the fail-closed outage/recovery contract, local presentation and coordination, and a synthetic exercise. This does not close S4. | Target-runtime monitoring and ownership must be named before a further runbook/monitoring package is selected. Provider-specific exercises depend on sandbox access. Backup/restore, target alert routing, real-provider behavior and external/human acceptance remain missing. | Monitors and alerts exercised; provider outage and degraded-customer paths tested in the applicable target/sandbox; backup restored; rollback rehearsed; incident/support paths and tax/API/security owners accepted. |
| **W9-S5 — target privacy/security and release acceptance** | Assemble the preceding controls in the intended runtime and complete provider/identity, privacy, security, manual failure and release assurance. | **External evidence missing.** | Depends on applicable S1-S4 gates and on launch-candidate provider and product integrations. It may collect evidence incrementally but is the final serial gate. | Target-runtime suite and browser journeys; provider sandbox evidence; privacy/security acceptance; residual-risk register; independent integrated review; Founder authorisation for activation/release. |

The accepted W9-S3 layers must be read narrowly:

| Layer | What is integrated | What it does not establish |
| --- | --- | --- |
| W9-S3A — `c489c25bab669c64e1c11d28caf29fcde9678fdd` | A minimised structured annual-position projection, local producer admission boundary, provenance/uncertainty representation, exact identity and supersession-chain contract. | No datastore, relational row, migration, retention period, legal hold, backup expiry, encryption/key custody, target write or production activation. |
| W9-S3B — `110a90043dfc770c70059482be9d7b7e237749a6` | A datastore-neutral detached primitive candidate, logical annual-position/evidence rows, governance-input gates and pure create/read/CAS/deletion-plan decisions. It is explicitly non-admitted and grants no persistence authority. | No authentication of live S3A output, adapter, database/SQL, durable read/write, atomic target CAS, migration, deletion execution, retention clock, custody, backup behavior, target runtime or activation. |
| W9-S3C — `c9bdaa6538d68c0c64b2dcde97f224a69c089d30` / integration `5f5a948891e1e812a5c74ff6c7266d153bb492fa` | A validating non-durable detachment adapter from the exact live admitted S3A projection to the detached S3B candidate shape. It binds caller-supplied expected owner/business references, preserves predecessor linkage and grants zero persistence authority; it does not authenticate the runtime caller or issuer. | S3C itself supplies no runtime-owner authentication, owner-to-business membership, database/SQL, datastore selection, durable write/read, target CAS, migration, retention/deletion execution, custody, backup behavior, target runtime or activation. |
| W9-S3D — source `98e4887e038f9ada1f090b0723837f3cb49eb8af` + `2ccafb00047583979e55e0ebb4fb193f17abe659`; integrations `5f7b76408a5d72b71be71d0e5d6c7a6edde260b7` + `b8ce971f4dc6b8a1ced10e9b490be68d481752de` | An exact three-path, pure/non-durable adapter that snapshots the authenticated signed-session `users.id`, canonicalises it through the accepted owner mapper and supplies it to S3C. Source ancestry is preserved after checkpoint. | No owner-to-business membership authentication, database/SQL, datastore selection, durable write/read, target CAS, migration, retention/deletion execution, custody, backup behavior, target runtime or activation. |

The workstream denominator remains five slices. At the cut-off, **0/5 slices
are complete (0%)**. S1 is partial and S3 now has four accepted non-durable
contract/adapter layers, but no slice yet has all of
its required assurance. This conservative measure prevents local contracts and
tests from being mistaken for launch readiness.

## Sequence and parallelism

1. Preserve the accepted/integrated W9-S1 independent-review findings and S1B
   reconciliation. Do not redispatch S1A/S1B or treat accepted evidence of
   incompleteness as risk acceptance. Name the 13 accountable decision roles
   and obtain their dated evidence/acceptance before reassessing S1.
2. Resolve S2 custody and the remaining S3 lifecycle/legal/privacy/target facts
   in parallel with ordinary provider/domain work. Keep credentials opaque and
   all S3 results non-durable until those gates are accepted.
3. Preserve the integrated S3A projection contract, S3B detached repository
   contract, S3C validating non-durable detachment adapter and S3D authenticated
   session-owner adapter. Do not redispatch them or
   call them persistence. Select a physical-store package only after its exact authority and external
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

W9-S1A/S1B and W9-S3A/S3B/S3C/S3D are already implemented and integrated. The next
W9 assurance action is not another evidence-only reconciliation: the 13
currently unnamed accountable decision roles must be named without inference,
and the required dated human/provider/target/legal/privacy/security/operations
evidence and acceptance must be obtained. This includes the remaining S2/S3
evidence recorded in `W9_SECURITY_DECISION_DOSSIER.md`: exact
retention/erasure/legal-hold and backup-expiry rules, custody and
target/datastore facts. S1 must then be assessed against the exact resulting
launch candidate; the accepted S1 findings and S1B reconciliation do not
pre-approve that assessment.

For avoidance of doubt, the integrated gap register's `ACT-01` and “Immediate
package boundary” text predates S1B acceptance. Those two self-referential
selection statements are satisfied by `587828337e01f269320048847b3250a690ce6133`
and its independent review. All substantive retention, custody, target,
provider, ownership, operations and acceptance gaps recorded around them remain
open.

`FD-W9-001` authorises the bounded minimised persistence design represented by
S3A/S3B/S3C/S3D, but expressly leaves owner-to-business membership and those
legal/privacy/security/target matters open.
`FD-OA-001` permits routine bounded engineering and reconciliation; it does not
answer them or enlarge persistence, production, deployment or activation
authority. Any consequential target/production choice and final activation or
release remains behind its applicable Founder gate.

No W9-S2 credential-custody implementation, W9-S3 datastore/migration or durable
write is authorised merely by this reconciliation. S3A, S3B, S3C and S3D reduce design
uncertainty but do not satisfy the
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
