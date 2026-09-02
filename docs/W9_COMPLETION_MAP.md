# W9 privacy, security and operations completion map

## Purpose and evidence cut-off

This map gives the October-launch privacy, security and operations workstream a
finite denominator. It is a planning and assurance control, not evidence that a
control is deployed or launch-ready.

- Evidence cut-off: 2 September 2026.
- Inspection worktree branch: `codex-cli/w9-completion-map` (an isolated
  branch based on, but not itself, the integration lineage).
- Immutable starting commit: `b2c216294b83c1fbaaa09259f671ae5bf7708e06`.
- Starting tree: `2ba2ce52b389f76c5d6d2ae7ab032763f2e6e1b5`.
- Starting worktree: clean.
- Evidence used: repository implementation and tests, [Founder Decisions](../FOUNDER_DECISIONS.md),
  [authentication readiness](AUTHENTICATION_READINESS.md),
  [provider boundary adoption](PROVIDER_BOUNDARY_ADOPTION.md),
  [provider pre-audit readiness](PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md),
  [annual-position persistence readiness](INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md),
  [annual-position isolation audit](INTERNAL_ANNUAL_PERSISTENCE_ISOLATION_AUDIT.md),
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
| Evidence and annual-position persistence | Annual calculations, provenance and uncertainty remain intentionally ephemeral. The repository audit found no incidental durable annual-position write. Some bounded feature data has owner/deletion controls. | There is no approved owner-bound annual-position schema, evidence-reference lifecycle, integrity/concurrency design, access audit, retention schedule, whole-account erasure workflow, encryption/key plan or migration path. The existing `tax_calculations` stub is not an acceptable substitute. |
| Retention, deletion and account erasure | Founder Decisions establish minimisation and deletion principles. HICBC has bounded deletion hooks. PAYE fallback records a `secure_deletion_required` disposition without claiming deletion occurred. | Field inventory, lawful purpose, retention periods, supersession, legal-hold exceptions, backup expiry, verified whole-account erasure and deletion evidence are unresolved. No actual payslip upload/extraction/raw-document deletion lifecycle exists. |
| Activation controls | Provider and identity readiness checks fail closed; provider adapters are network-inert unless explicitly enabled and evidenced. The canonical October release gate already preserves a 16-blocker inventory. | Existing readiness and release inventories must be reconciled to exact package, target and acceptance evidence rather than duplicated by another diagnostic. Production/provider enablement remains a Founder gate. |
| Monitoring and outage behavior | A local application/database health boundary and a tax-rule drift monitor exist. Provider contracts contain bounded fail-close behavior. | There is no evidenced target monitoring, alert routing, service-level ownership, provider-outage exercise, customer degradation test or production runbook. Tax-rule monitoring is not general operational monitoring. |
| Restore, rollback and incident response | Database operations use bounded transactional rollback in places, and repository changes are checkpointed/revertible. | Recoverable backups, restoration tests, application/data rollback, key recovery, incident triage, security response, customer-support escalation and named operational ownership are not evidenced. Database transaction rollback is not disaster recovery. |
| Target-runtime and privacy/security acceptance | Local and synthetic test evidence exists. Readiness documents preserve missing evidence as blockers. | The target runtime, provider and identity journeys, security/privacy review, manual failure/accessibility checks and complete release gate have not passed. No production activation follows from this map. |

## Finite delivery slices

| Slice | Owned outcome | Current state | Dependencies and concurrency | Completion evidence |
| --- | --- | --- | --- | --- |
| **W9-S1 — control inventory, launch data-flow and threat boundary** | Preserve existing authentication/session, provider fail-close and canonical release controls; document the complete October data flow, trust boundaries, threats and exact unresolved security/privacy decisions without creating another readiness authority. | **Partial.** The underlying controls and blocker inventory are integrated; a single launch-scoped data-flow/threat model and decision dossier are missing. | Can proceed now and in parallel with provider implementation. It must not edit adapters, configuration, credentials, retention or activation flags, and it must not select unresolved options. Target journeys remain for S5. | Independent review of exact evidence; all October flows and trust boundaries covered; threats and mitigations tied to existing controls/blockers; every unresolved choice has an owner and acceptance evidence; no environment, credential, network, persistence or activation side effects. |
| **W9-S2 — provider secret and token custody** | Implement the approved encrypted credential/token store and its provider/owner isolation, rotation, tamper, revocation, audit and key-recovery boundaries. | **Missing engineering; decision-bound.** OAuth contracts deliberately stop at an abstract store boundary. | Requires an approved target datastore/KMS or equivalent, key custody and rotation owner, access policy and backup/recovery semantics. Provider adapters can continue against opaque references while this is decided. | Architecture/security decision; bounded implementation and independent review; wrong-key, tamper, rotation, ownership and restore tests; target custody evidence. |
| **W9-S3 — durable data lifecycle** | Implement only the approved, minimised persistence for annual-position/evidence references and PAYE fallback, including retention, supersession, account erasure, backup expiry and provable raw-payslip deletion. | **Missing engineering; decision-bound.** Annual-position isolation is presently the correct safe state. | Requires approved field inventory, purpose/lawful-basis review, retention and backup-deletion schedule, erasure exceptions, datastore/encryption choice and audit-event rules. Domain work may continue ephemerally. | Approved schema/lifecycle decisions; migrations; ownership/integrity/concurrency and minimisation tests; deletion/erasure/backup-expiry evidence; raw payslip deletion demonstrated without logging or retaining document content. |
| **W9-S4 — operational resilience and ownership** | Establish target monitoring, safe outage behavior, recoverable backup/restore, rollback, incident/security response and customer-support escalation with named owners. | **Partial foundations only.** Health and tax-rule checks do not close the slice. | Local runbook/event contracts can proceed once target runtime and ownership are named. Provider-specific outage exercises depend on sandbox access. Can overlap S2/S3 implementation. | Monitors and alerts exercised; provider outage and degraded-customer paths tested; backup restored; rollback rehearsed; incident/support paths and tax/API/security owners accepted. |
| **W9-S5 — target privacy/security and release acceptance** | Assemble the preceding controls in the intended runtime and complete provider/identity, privacy, security, manual failure and release assurance. | **External evidence missing.** | Depends on applicable S1-S4 gates and on launch-candidate provider and product integrations. It may collect evidence incrementally but is the final serial gate. | Target-runtime suite and browser journeys; provider sandbox evidence; privacy/security acceptance; residual-risk register; independent integrated review; Founder authorisation for activation/release. |

The workstream denominator is five slices. At the cut-off, **0/5 slices are
complete (0%)**. S1 is partial and several reusable controls are integrated,
but no slice yet has all of its required assurance. This conservative measure
prevents local building blocks from being mistaken for launch readiness.

## Sequence and parallelism

1. Execute W9-S1's launch data-flow/threat and decision-dossier package
   immediately; it has no external or policy dependency, duplicates no release
   authority and changes no activation state.
2. Resolve S2 custody and S3 lifecycle decisions in parallel with ordinary
   provider/domain work. Keep credentials opaque and annual results ephemeral
   until those decisions are approved.
3. Build S2 and S3 as separate packages after their exact decisions are
   recorded. Do not let either silently choose a vendor, retention period,
   lawful basis, key owner or legal-hold rule.
4. Develop S4's local runbooks and fail-close contracts alongside S2/S3, then
   exercise them in the selected target environment.
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

## Exactly one next implementation package

### W9-S1A — launch data-flow, threat model and security-decision dossier

**Objective.** Produce the launch-scoped technical evidence required to make
the S2-S4 decisions safely: one complete data-flow/trust-boundary threat model
and one exact decision dossier. Reconcile these to the existing provider and
identity readiness checks and canonical October blocker inventory; do not add a
second readiness engine or choose an unresolved option.

**Proposed exact new paths**

- `docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md`
- `docs/W9_SECURITY_DECISION_DOSSIER.md`
- `tests/test_w9_security_evidence.py`

**Protected paths**

- `FOUNDER_DECISIONS.md`
- `reserved/assurance_metadata.json`
- `reserved_west/release_gate.py`
- `reserved/auth.py`
- `reserved/database.py`
- `reserved/providers/readiness.py`
- `reserved/providers/identity/readiness.py`
- `reserved/providers/oauth_security.py`
- `reserved/providers/oauth_contracts.py`
- `reserved/providers/http_boundary.py`
- every provider adapter, route, configuration file and template
- all existing tests and documents, including this map and
  `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md`

**Required evidence.** Cover every settled October flow from collection through
provider transport, normalisation, annual tax, cash/reserve, presentation,
payment initiation, persistence, logs/monitoring, deletion, backups and support.
For each, state data class, owner, trust boundary, allowed destination, storage,
retention/deletion state, existing control, threat, failure mode and closure
evidence. The decision dossier must isolate the exact choices still required
for credential/key custody, durable evidence, PAYE documents, account erasure,
backup expiry/recovery, CSP, target runtime, monitoring/ownership and incident
response, with options and consequences but no invented decision.

**Focused acceptance.** A small evidence-contract test must fail if an October
flow, mandatory trust boundary, threat class, unresolved decision owner,
canonical blocker reference or explicit non-activation statement disappears.
It must also prove that the package does not alter existing readiness, release,
configuration or production files. Run the existing provider/identity
readiness and release-gate tests as the affected matrix.

This is the only next package selected by this map. It is **IMPLEMENTABLE
NOW**, independently testable, directly unblocks S2-S4 decisions, and does not
invent custody, retention, legal, provider or production semantics.

## Out of scope

This map does not authorise production access, provider activation, credentials,
real customer or bank data, payments, filing, deployment, merge/release/go-live,
new provider scope, Scotland, VAT, Ireland/Europe, or optional post-launch
sophistication. It does not amend Founder Decisions or the Control Plane.
