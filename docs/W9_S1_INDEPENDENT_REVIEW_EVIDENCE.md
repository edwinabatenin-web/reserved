# W9-S1 independent-review evidence candidate

## Disposition

**Candidate finding: the stated W9-S1 completion gate is not met at the review
cut-off.**

The repository contains a substantial, fail-closed W9-S1A data-flow, trust-
boundary, threat and decision inventory. Its structural evidence test passes,
and the implementation-facing controls sampled by this review pass their local
tests. That is useful design and regression evidence. It is not enough to close
W9-S1 because:

1. this file is a candidate record for a separate reviewer, not an accepted
   independent-review disposition;
2. the integrated W9-S1A evidence is reconciled to an older repository point
   and contains material current-state drift described below;
3. 13 of 14 decision entries still assign their accountable human role as “to
   be named”; and
4. the dossier describes the evidence required for each open decision, but the
   required human, target-runtime and provider evidence is not present.

No finding here activates a provider, accepts a residual risk, approves a
datastore or retention rule, or authorises persistence, migration, deployment,
release or go-live.

## Exact review basis and limits

| Item | Exact basis |
| --- | --- |
| Repository HEAD | `6edf3cd6b96090f25036688e83da1d3b5295b098` |
| Repository tree | `0d77f1853cc22a8c1e923552425478b7b9155cb2` |
| Review date | 4 September 2026 |
| W9-S1A evidence under review | `docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md`, `docs/W9_SECURITY_DECISION_DOSSIER.md`, `tests/test_w9_security_evidence.py`, last changed together at `043a86883daba5a66908ca2f3b92bf8fa3e8e66a` |
| W9 planning state | `docs/W9_COMPLETION_MAP.md`, last changed at `cab84cca1c4b8d83abff1540791a2c98c5eee1be`; `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md`, last changed at `dd98c4421707f54eb0b564a85ee77d3ed286d79d` |
| Canonical launch blocker | `reserved_west/release_gate.py`, last changed at `58936c2f70d7202b86cdcda6eb953816b38b7808` |
| Method | Read-only inspection of tracked repository evidence and code, deterministic local tests, and worktree/diff checks |
| Excluded | Credentials, environment inspection, network/provider access, production data, deployment, legal advice, privacy/security acceptance and operational exercises |

The original S1A package was introduced at
`8eec5d81ae915b04d592a4432a065237dda6a9c9`; its introducing-commit scope guard
was corrected at `1b9a877cef488f0ea607eb6de37b1d047a76c880`.
Passing that guard proves the package-history path boundary and required marker
shape. It does not prove that all prose remains accurate at a later HEAD or
that a human has accepted the unresolved risks.

## Inventory reconstruction

The exact integrated S1A documents contain the following unique structured
sections:

| Inventory | Present | Review finding |
| --- | ---: | --- |
| Mandatory October flows | 15/15 (`FLOW-01` through `FLOW-15`) | Structurally complete. Browser/auth, accounting OAuth and retrieval, HMRC/PAYE, manual payslip, annual/cash, banking, billing, operations, erasure, runtime/release, linked HICBC, MTD and geography are represented. Some current-state descriptions are stale. |
| Trust boundaries | 14/14 (`TB-01` through `TB-14`) | Structurally complete. Local controls and external boundaries are distinguished, subject to the drift findings below. |
| Threat classes | 21/21 (`TH-01` through `TH-21`) | Structurally complete. Each has a mitigation or an explicit missing control; several mitigations remain contract-only or local/synthetic. |
| Unresolved decisions | 14/14 (`DEC-01` through `DEC-14`) | Every entry has the required fields, safe default and evidence request. The owner and acceptance part of the completion gate fails: 13 entries explicitly say the responsible role is “to be named,” and required evidence is generally prospective rather than attached and accepted. |
| Canonical October release blockers | 16/16 in `OCTOBER_LAUNCH_COMPONENTS` | All remain non-passing (`not_executable`, `externally_blocked`, `not_implemented`, `evidence_missing`, or `privacy_retention_review_required`). |

`tests/test_w9_security_evidence.py` enforces IDs, required fields, selected
semantic markers, canonical blocker references, non-activation wording and the
historical three-path package boundary. Its 17 tests passed in this worktree.
This is a valuable completeness guard, but it is not a semantic proof of every
claim and it deliberately binds the evidence documents to reconciliation point
`10fb93e2e6ab567a72d2370c1603768a7ac04bb5`, not to this review's exact HEAD.

## Implementation-facing control review

“Locally verified” below means only that the code and cited local tests were
present at the exact review HEAD and passed in the bounded affected suite. It
does not mean externally evidenced or launch-ready.

| Boundary | Implemented / locally verified evidence | Missing human, target or provider evidence |
| --- | --- | --- |
| Authentication and session | `reserved/auth.py` and `reserved/__init__.py` validate the broker token issuer, authorised party, subject, session and optional audience before establishing Reserved's session; successful login clears prior session state; sensitive responses receive no-store headers. Local negative and readiness tests include `tests/test_auth.py`, `tests/test_auth_claims.py` and `tests/test_identity_readiness.py`. Auth code was integrated at `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb`; application headers at `58936c2f70d7202b86cdcda6eb953816b38b7808`. | Target Clerk/Google/Apple sign-in, denial, expiry, replay, logout, revocation and account-deletion journeys are absent. The CSP still permits `unsafe-inline` script/style execution and has neither accepted risk nor target browser hardening evidence. |
| Provider OAuth, tokens and secrets | `reserved/providers/oauth_security.py` uses hashed provider-bound expiring single-use state. `reserved/providers/oauth_contracts.py` consumes state before exposing a single-use code, redacts token/code representations and returns an opaque `CredentialReference`. `reserved/providers/readiness.py` checks only presence and safe non-production shape and keeps every canonical provider's `implementation_enabled=False`; configuration alone therefore cannot enable calls. Tests include `tests/test_oauth_contracts.py` and `tests/test_provider_readiness.py`. Core OAuth controls were integrated at `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb`; readiness was last changed at `ac871c4a8ce2cc1cf8170d30708ea8e70f7ad7d6`. | `TokenStore` remains a protocol, not an encrypted store. There is no approved datastore/KMS equivalent, key custodian, IAM boundary, rotation, revocation, break-glass, tamper/wrong-key, audit, backup or recovery evidence. No real credentials were inspected. |
| Provider ingress/egress and schemas | `reserved/providers/http_boundary.py` accepts only injected sandbox/test/demo HTTPS origins and validates the exact origin before an injected transport is called; its summary omits bodies and redacts sensitive headers. `reserved/providers/schema_evidence.py` records coarse schema evidence and quarantines incompatible drift. Local tests include `tests/test_provider_http_boundary.py` and `tests/test_schema_evidence.py`; these boundaries were integrated at `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb` and `3831e041595adc1c216b7154ec2c8ed8725ba92a`. | No cited local test is evidence of an intended provider's sandbox/production destination, signature/authenticity, scopes, pagination completeness, webhook behavior, DPA/terms, rate limits or recovery. The canonical release gate still records HMRC and Yapily as externally blocked and FreeAgent/Xero/QuickBooks as not implemented for launch. Later provider-specific contracts do not by themselves alter those launch states. |
| Temporary payslip rule | `reserved/engines/paye_extraction_confirmation.py` accepts bounded typed fields and emits an immutable redacted confirmation whose only disposition is `secure_deletion_required`. It explicitly performs no I/O and never says deletion occurred. Source last changed at `af5df09004b3202d77fca0ffa7e74d51268882d6`; focused tests at `tests/test_paye_extraction_confirmation.py` were last changed at `c23d343032a3bfd94e8ba1bda45cc5361b3fff40`. This correctly implements the safe meaning of the temporary-payslip rule. | There is no upload/extraction storage path, deletion executor, deletion proof, failure/retry handling, replacement behavior, content-log proof or backup-expiry evidence. `secure_deletion_required` is a duty marker, not proof of secure deletion. |
| Owner isolation and cross-account data | `reserved/database.py` contains owner-linked foreign keys and feature-specific owner checks/cascades. Its linked-HICBC surface stores the relationship, hashed single-use invitations and per-participant versioned consent rather than partner financial values, and supplies unlink/account-deletion hooks. Local isolation/privacy tests include `tests/test_hicbc_linked_account.py` and `tests/test_hicbc_partner_privacy.py`; this surface was last changed at `7df7ac871e046e1ab6c2f870bc26269a1403ecbf`. | These feature-specific controls are not a whole-account erasure implementation or a proof that every database function is owner-safe. Linked-HICBC still needs lawful-basis, transparency, minimisation, anti-probing, retention/deletion and target cross-account acceptance by named reviewers. |
| Annual-position minimisation and repository boundary | W9-S3A, integrated at `c489c25bab669c64e1c11d28caf29fcde9678fdd`, defines a minimised owner/business/year/nation/purpose-bound admitted projection, exact-money identity and supersession contract. W9-S3B, integrated at `110a90043dfc770c70059482be9d7b7e237749a6`, defines a detached exact-primitive structural candidate, logical records/evidence rows, fail-closed reads, in-memory create/CAS/deletion decisions and opaque governance-input shape. `tests/test_annual_position_persistence_contract.py` and `tests/test_annual_position_repository_contract.py` passed. S3B always denies upstream admission and persistence authority. | There is no reviewed S3A-to-S3B adapter, physical schema, migration, durable repository, database I/O, authenticated integrity, atomic target CAS, access audit, approved retention/legal hold/erasure/backup expiry, custody, target runtime or production write. A source hash or unkeyed content identity is not storage authenticity. |
| Logs, monitoring and support | Provider request summaries redact sensitive header values and omit body content. `reserved/database.py` stores a short SHA-256 IP-derived value rather than a raw IP. Local health and tax-rule drift checks exist. | There is no complete target log-field inventory, redaction test over emitted runtime logs, retention/deletion schedule, operator/support RBAC, alert route, named responder or target monitoring evidence. Hashing an IP does not settle lawful purpose, retention or re-identification risk. |
| Outage and recovery | W9-S4A–E provide a fail-closed provider outage/recovery contract, single-provider presentation, multi-provider coordination/presentation and a synthetic exercise at `58fb28267afb5a7b766d8f1e7bbcdbda8d517e81`, `2cb3d43fbc59d75226c7b5d1a4f5f77addd24319`, `43e4671a3ac59edd3620a950157b2f483e8e209a`, `8f26ee74138432f00398eaa4297f8a7ef5817734` and `1a277b60f3bc9da02d52fd1a869f91a35ce303fe`. The corresponding five local test modules passed. Transaction rollback is used in parts of `reserved/database.py`. | No provider sandbox/real-provider outage, webhook backlog, target alerting, named ownership, accepted runbook, tabletop, encrypted backup, restoration, data/application rollback, key recovery or RPO/RTO exercise is evidenced. Database transaction rollback and Git revertibility are not disaster recovery. |
| Billing boundary relevant to W9 | Current HEAD adds provider/lifecycle authority, fail-closed defaults, a non-durable entitlement transition contract, a detached event-inbox contract and a disabled-first Stripe edge contract at `5464bfac7bec6b3456d1895b2355a7e8ce86859b`, `1033c9fbef008dcd33125a0b14e7fb18b8846d19`, `94bd87f019dc226ec8c73f32515229189500cf06`, `5bc29bcb30c95ea7a5a9430104653b366d709eb6` and `2ad4a63dd1f10ba38859050b47245c28390667d8`. Their affected local tests passed. They remain network-inert, persistence-free or detached contracts and grant no charge/entitlement/activation authority. | There is no authenticated webhook ingress, signature verification, durable event inbox, billing datastore, provider SDK/call, credentials, checkout/portal session creation, charge, route entitlement enforcement, target evidence or production activation. W10 remains 0/8 strictly complete in `docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md` at exact HEAD. |
| Target runtime and release | `reserved_west/release_gate.py` keeps a canonical 16-item October blocker inventory and never converts a narrow deterministic-engine pass into launch readiness. `tests/test_release_gate.py` passed. | No immutable launch target/configuration, deployment isolation, complete target suite, browser/provider journeys, external security/privacy review, named operational ownership or Founder activation/release authorisation is recorded. |

## Data flow and trust-boundary findings

### What the evidence gets right

- The 15 flows trace customer/browser input through identity, provider and
  evidence acquisition, calculation, presentation, limited existing storage,
  deletion/backup intentions and release/activation. Destinations, present
  storage behavior, unresolved lifecycle state and safe failure state are
  separate fields.
- The 14 trust boundaries include not only network edges but also application
  to persistence, runtime to operators, primary data to backups, local evidence
  to target acceptance, linked-customer access, MTD-indication semantics and
  October geography admission.
- The 21 threat classes cover spoofing, OAuth replay/order, SSRF, schema drift,
  stale certainty, credential exposure, owner leakage, webhook replay,
  evidence tampering, logging, deletion/backup failure, outage, privilege and
  runtime compromise, cash misdirection, unsafe activation, linked-person
  inference, MTD overstatement and geography leakage.
- Safe defaults are generally conservative: absent adapters and target facts
  remain disabled; raw payslips are not accepted as durably stored; local or
  synthetic evidence is not labelled target evidence; and release/activation
  is a separate Founder gate.

### Current-state drift and evidence defects

1. **The S1A cut-off is not the reviewed HEAD.** Both evidence documents still
   identify `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` as their current integration
   reconciliation point. The structural test requires that older value. Many
   accepted packages now present at `6edf3cd...` are therefore outside its
   semantic reconciliation.
2. **Annual-position language predates W9-S3A/S3B.** `FLOW-06`, `FLOW-07`,
   `TB-03` and `TH-06` still describe only ephemeral/non-persistent handling,
   presentation-only results or a gated field inventory. The safe operational
   conclusion remains true—there is no durable write or approved target
   lifecycle—but the model omits the two integrated contract layers and their
   precise non-authority boundary. The current W9 completion map contains the
   narrower, accurate statement.
3. **Billing language predates later W10 layers.** `FLOW-09`, `TB-08` and
   `DEC-11` principally describe W10-S1A. Current HEAD includes S2A/S2B,
   contract-only S3A/S3B and disabled-first S4A, plus later presentation work.
   None enables billing, but omitting them makes the control inventory
   incomplete at the exact HEAD.
4. **The gap register and model disagree on outage status.** `OUTAGE-01` in
   `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md` says customer-visible
   degradation/recovery and multi-provider behavior are not integrated, while
   `TH-14` and the current completion map correctly record integrated local/
   synthetic W9-S4A–E evidence. Target/provider exercise evidence remains
   missing either way.

These defects do not justify broad implementation changes in this bounded
package. They do mean a separate reviewer should not accept the existing S1A
documents as an exact current-state model without a narrowly authorised
reconciliation.

## Retention, erasure, recovery and authority gaps

The decision dossier is candid about the missing controls. Description is not
acceptance:

- `DEC-01`/`DEC-02`: datastore, encryption/KMS-equivalent and key custody;
- `DEC-03`/`DEC-04`: minimised durable fields, purpose/lawful basis,
  retention, supersession, legal exceptions, account erasure and backup
  expiry;
- `DEC-05`: payslip acquisition and provable raw-document deletion;
- `DEC-06`: CSP acceptance or tightening;
- `DEC-07`–`DEC-10`: target isolation, monitoring/alerts, backup/restore and
  incident/support ownership;
- `DEC-11`: provider custody/webhook and remaining billing policies;
- `DEC-12`: linked-HICBC lawful-basis, minimisation, anti-probing and lifecycle
  acceptance; and
- `DEC-13`/`DEC-14`: MTD source/routing/recheck/target acceptance and validated
  geography-source acquisition.

All 14 entries contain an “Accountable decision owner/authority” field, but 13
explicitly defer the responsible person as “to be named under W9-S4.” `DEC-11`
names the Founder for already settled provisional provider/lifecycle authority
and a generic security owner for the remaining custody/webhook boundary. No
entry contains a reviewer identity, dated acceptance, target artifact or risk
sign-off satisfying its “Exact evidence required to decide” field.

## Evaluation against the stated W9-S1 gate

| Completion criterion from `docs/W9_COMPLETION_MAP.md` | Result | Reason |
| --- | --- | --- |
| Independent review of exact evidence | **Not met** | This is an independent reconstruction candidate, deliberately awaiting a separate reviewer. The underlying evidence is not reconciled to exact HEAD and has the defects above. |
| All October flows and trust boundaries covered | **Partially met** | The finite 15-flow/14-boundary denominator is structurally present, but exact-current coverage omits integrated S3 and W10 layers. |
| Threats and mitigations tied to existing controls/blockers | **Met locally, qualified** | All 21 threat sections name mitigations or explicit absences and link to blockers. Some are contract-only/local/synthetic and cannot be treated as deployed controls. |
| Every unresolved choice has an owner and acceptance evidence | **Not met** | Role fields exist, but 13/14 owners remain “to be named”; required evidence and accepted dispositions are absent. |
| No environment, credential, network, persistence or activation side effects | **Met for this candidate and the S1A documentation package** | Review and tests were repository-local and read-only apart from this one new evidence file. No runtime/configuration/source/readiness file was changed. |

Because required criteria are conjunctive, the overall W9-S1 result is **not
complete**. It must remain outside the W9 completed-slice numerator; the current
0/5 W9 denominator is not advanced by this candidate.

## Minimal next review action

1. A separate reviewer should verify or challenge each finding in this
   candidate and record a dated disposition; this candidate must not approve
   itself.
2. If authorised, reconcile only the existing S1A evidence documents and their
   evidence-contract test to the exact integrated tree: add the narrow S3A/S3B
   and current W10 contract states, and reconcile the outage gap without
   converting contracts into runtime assurance.
3. Name the accountable security, privacy/legal and operations owners and link
   actual accepted evidence, or keep the corresponding decision explicitly
   open. A role placeholder or list of desired artifacts is not acceptance.
4. Preserve all target/provider/legal/privacy/Founder gates. Missing external
   evidence should be collected only in its separately authorised environment;
   no such access is implied here.

## Verification record

Executed from the clean isolated worktree based on the exact HEAD above:

- `python3 -m pytest -o addopts='' -q tests/test_w9_security_evidence.py` —
  **17 passed**.
- A bounded affected suite covering authentication, identity readiness, OAuth,
  provider HTTP/readiness/schema, payslip confirmation, HICBC isolation/privacy,
  W9-S3A/S3B, W9-S4 outage behavior, canonical release gate and the current W10
  authority/lifecycle/inbox/Stripe contracts — **869 passed**.
- `python3 -m pytest -o addopts='' -q` — **6512 passed, 7 subtests passed**.

These results establish deterministic local behavior only. They are not legal,
privacy, security, provider, target-runtime, operational or launch acceptance.
