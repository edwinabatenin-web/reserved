# W9 security and operations gap register

## Scope and labels

This register is the execution companion to the
[W9 completion map](W9_COMPLETION_MAP.md). Its evidence cut-off is 4 September
2026 at exact integration commit
`81ae02044cccd921d98a0d1fc2360e1c4a983ab1`, tree
`ac5922e7aae0016a54f78a8645a244ac83eae0d2`. The
[W9-S1 independent-review evidence](W9_S1_INDEPENDENT_REVIEW_EVIDENCE.md) is
findings input only, not assurance authority or human acceptance. Exact source
SHA-256 bindings for the reconciled integrated evidence are in the
[W9 data-flow and threat model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md#exact-current-state-source-binding).

Every open item has exactly one disposition:

- **IMPLEMENTABLE NOW** — settled local semantics permit a bounded package.
- **DECISION REQUIRED** — implementation would otherwise invent security,
  privacy, legal, operational or Founder-owned semantics.
- **EXTERNAL EVIDENCE** — the code may exist, but closure requires the intended
  provider, identity, hosting or operational environment.
- **LATER/OUT OF SCOPE** — not required for the settled October launch boundary.

An item labelled external evidence is not a request to access credentials or a
live service under this package.

## Open gaps

| ID | Boundary and current evidence | Disposition | Sequence | Exact closure evidence |
| --- | --- | --- | --- | --- |
| AUTH-01 | Local Clerk token/session checks, logout clearing and sensitive-route no-store headers exist, but Google/Apple and target broker journeys are not verified. | **EXTERNAL EVIDENCE** | S5; collect after target configuration without delaying S1. | Target sign-in, denial, expiry, logout, replay, account-deletion/revocation and applicable Google/Apple journeys, independently reviewed with redacted evidence. |
| AUTH-02 | The content-security policy intentionally allows inline scripts/styles; no launch acceptance or nonce/hash migration is evidenced. | **DECISION REQUIRED** | Decide before S5; implement a bounded tightening package if the accepted target policy requires it. | Security owner records accepted CSP/risk or approves exact tightening; browser regression and injection-focused evidence pass. |
| AUTH-03 | Feature-level owner deletion exists in places, but there is no complete authenticated account-erasure flow. | **DECISION REQUIRED** | Define with DATA-02 in S3; test in S5. | Approved reauthentication, scope, exceptions and notification semantics, followed by cross-store erasure and negative-ownership tests. |
| CUST-01 | OAuth contracts expose only opaque references. The encrypted token store and deployment key custodian are deliberately absent. | **DECISION REQUIRED** | First S2 gate; may run in parallel with S1. | Approved datastore/KMS or equivalent, key owner, access boundary, rotation, break-glass, audit and recovery design. |
| CUST-02 | There is no concrete token-store implementation, provider/owner isolation, atomic refresh persistence, revocation or wrong-key behavior. | **DECISION REQUIRED** | CUST-01 must first settle the design; implementation then precedes provider target acceptance. | Independent code review and tests for encryption, owner/provider binding, concurrency, tamper, wrong-key, rotation, revocation, redaction and recovery. |
| PERSIST-01 | W9-S3A integrates a minimised owner/business/year/nation/purpose-bound admitted projection with exact money identity and supersession semantics. It is not an approved field-by-field lifecycle, lawful basis, physical schema, datastore, encryption or migration design; the existing calculation stub remains unsuitable. | **DECISION REQUIRED** | S3 policy/design gate remains open despite the integrated contract evidence. | Approved field-by-field purpose, lawful basis, provenance/uncertainty representation, owner schema, retention/deletion/backup rules, datastore/encryption and migration rules. |
| PERSIST-02 | W9-S3B integrates a detached structural candidate for logical annual-position/evidence records plus in-memory create/CAS/deletion decisions and fail-closed reads. It explicitly lacks upstream-admission and persistence authority: there is no physical schema/migration, durable repository/database I/O, authenticated integrity, atomic target CAS, access audit or deletion executor. | **DECISION REQUIRED** | PERSIST-01 and DATA-01 must settle lifecycle and target design before a durable implementation; then implementation precedes S5. | Bounded physical repository/migrations with ownership, authenticated integrity, atomic target concurrency, supersession, access audit, minimisation, lifecycle enforcement and fail-closed decode tests. |
| DATA-01 | No approved cross-feature retention schedule, lawful-purpose mapping, legal-hold rule or backup-expiry schedule exists. | **DECISION REQUIRED** | S3 gate before durable storage expands. | Privacy/security owner approves field-by-field purpose, retention, deletion, exception and backup-expiry register. |
| DATA-02 | Selective cascades and HICBC hooks do not constitute whole-account erasure across identity, provider, evidence and annual-position records. | **DECISION REQUIRED** | AUTH-03, PERSIST-01 and DATA-01 must first settle the design; implementation is then tested before S5. | Idempotent, owner-safe cross-store deletion with interruption/retry, exception, evidence-reference and audit tests. |
| DATA-03 | Backup deletion and expiry behavior is not selected or testable without the target storage/backup design. | **DECISION REQUIRED** | Decide in S3/S4 before backup implementation. | Approved backup retention, encryption/key retirement, deletion propagation, restore exclusion and legal-exception rules. |
| PAYSLIP-01 | S1 structured capture and S2A confirmation are integrated. The marker `secure_deletion_required` is not proof that a raw payslip was deleted; upload/extraction/storage do not exist. | **DECISION REQUIRED** | Resolve storage, expiry, confirmation and backup semantics in S3; then implement one isolated flow. | Approved raw-document lifecycle plus deletion executor/evidence; tests prove delete-after-check, failure/retry, replacement, no content logging and applicable backup expiry. |
| ACT-01 | The W9-S1A launch data-flow/threat model and decision dossier are integrated, but their prior lineage is stale against current W9-S3A/S3B, W9-S4A–E and W10 evidence. The independent-review candidate records useful findings but is not assurance authority; exact-current reconciliation and fresh independent acceptance remain missing. | **IMPLEMENTABLE NOW** | **Immediate W9-S1B evidence-only reconciliation; then independent review of the exact candidate.** | Exact-current commit/tree/source-bound model, dossier, register and tests preserve all flows/boundaries/threats/decisions and honest non-authority boundaries; separate reviewer accepts the exact candidate and unresolved owners/gates remain explicit. No environment, secret, network, persistence, configuration or activation side effects. |
| ACT-02 | Provider and identity target journeys and activation evidence are incomplete. | **EXTERNAL EVIDENCE** | S5 after applicable S1-S4 controls. | Provider/identity target evidence is complete and independently accepted; this evidence does not itself activate a capability. |
| ACT-03 | Production provider/identity activation remains an explicit Founder gate even after target evidence passes. | **DECISION REQUIRED** | After ACT-02 and the applicable W9 terminal gates; never inferred from configuration or test success. | Exact activation scope, candidate identity, evidence and residual risks are presented and explicit Founder authority is recorded. |
| MON-01 | Application/database health and tax-rule drift checks exist, but there is no target monitor, alert route or service-level owner. | **DECISION REQUIRED** | Name the target runtime, alert channels and owners in S4; local event/runbook contracts may then be implemented. | Target health/security/provider/tax-rule alerts reach named owners; false-positive, missed-heartbeat and sensitive-data tests pass. |
| OUTAGE-01 | W9-S4A–E are integrated: fail-closed outage/recovery contracts, local/synthetic single- and multi-provider presentation/coordination, and a synthetic exercise. This is not intended-target or provider evidence. Target monitoring/alert routing, named ownership, an accepted production runbook, tabletop evidence, and sandbox/real-provider degraded-customer/recovery evidence remain missing. | **DECISION REQUIRED** | Name the operational owner and accept the runbook/target design first; intended-target and provider exercises then remain **EXTERNAL EVIDENCE**. | Named owner and accepted runbook; target alert routing; tabletop/drill artifacts; sandbox/real-provider outage, timeout, revocation and schema-drift evidence proving safe degradation, no stale certainty and recovery/reconnect behavior. |
| REC-01 | Transaction rollback and Git revertibility exist, but recoverable application/data backups and restoration do not. | **DECISION REQUIRED** | Select target backup/key/RPO-RTO ownership in S4 before implementation. | Approved recovery objectives and ownership; encrypted backup, restore, integrity, key recovery, rollback and data-loss-window exercises pass. |
| INC-01 | No complete incident/security response and customer-support escalation ownership is evidenced. | **DECISION REQUIRED** | Name owners and severity/escalation rules early in S4; exercise before S5. | Accepted incident and support runbooks with tax-rule, provider/API, privacy and security owners; tabletop/drill evidence and follow-up actions. |
| RUNTIME-01 | Local tests are extensive, but the complete suite and required journeys have not been repeated in the intended launch runtime. | **EXTERNAL EVIDENCE** | S5; incremental evidence may be collected earlier. | Immutable target identity and configuration, complete required suite, failure paths, browser journeys and redacted artifact register. |
| PRIV-01 | Privacy/security blockers are recorded, including HICBC and PAYE fallback, but no complete launch-candidate acceptance exists. | **IMPLEMENTABLE NOW** | Internal review can begin with S2/S3 decisions; final acceptance is S5. | Field/data-flow inventory, threat/privacy review, mitigations, residual risks and independent sign-off cover the exact launch candidate. Seek external advice only if that review identifies a material unresolved question. |
| PRIV-02 | Manual access-control, failure, browser privacy/cache and relevant accessibility checks are incomplete in the target environment. | **EXTERNAL EVIDENCE** | Final S5 affected-journey pass. | Named tester, target/build identity, negative cases, artifacts and independently reviewed outcomes. |
| RELEASE-01 | A green local or target suite does not authorise merge/release or go-live; these remain separate Founder gates. | **DECISION REQUIRED** | Last S5 gate; never inferred from another row. | Complete launch checklist, integrated evidence and residual-risk reconciliation are presented, followed by explicit Founder authorisation. |
| LATER-01 | Optional providers, regions and tax products outside the settled October scope would enlarge the security/privacy surface. | **LATER/OUT OF SCOPE** | After launch only under new authority. | New scoped decision and workstream; no work is authorised by W9. |

## Current integrated controls that must not be reimplemented

- Clerk-broker claim and session validation, complete logout clearing and
  sensitive-route cache prevention.
- Provider-bound, expiring, single-use OAuth state and callback-ordering
  contracts.
- Opaque credential references and an abstract atomic refresh-store boundary.
- Injected, HTTPS, non-production provider HTTP boundaries and redacted import
  evidence.
- Fail-closed provider and identity readiness; configuration alone does not
  prove implementation or launch readiness.
- W9-S3A's minimised admitted projection and W9-S3B's detached structural and
  in-memory repository decisions. They remain non-authority evidence: no
  physical schema, database I/O or durable annual-position storage exists.
- Integrated W9-S4A–E local/synthetic outage behavior and exercise evidence;
  target/provider operation, ownership, runbook and tabletop acceptance remain
  open.
- PAYE confirmation's honest `secure_deletion_required` marker, which must not
  be relabelled as deletion evidence.

These controls should be reused and independently rechecked through their
affected tests. Rewriting them is not part of the next package.

## Immediate package boundary

Only **ACT-01 / W9-S1B exact-current-state evidence reconciliation** is selected
for immediate implementation here. It may update only this register, the W9-S1A
launch data-flow/threat model, the decision dossier and their evidence-contract
test. It cannot complete W9-S1; the exact reconciled candidate still requires a
fresh independent review, and the unnamed decision/operational owners remain
unnamed.

All decision-bound rows remain fail-closed. “Implementable now” means the
engineering semantics are sufficiently bounded; where its sequence names a
dependency, it does not authorise work before that dependency is satisfied.

This register does not itself modify readiness, provider state, credentials,
retention, deployment or Founder authority. It does not prove target/provider
operation, human acceptance, durable annual-position storage, billing
activation, W9-S1 completion or launch readiness.
