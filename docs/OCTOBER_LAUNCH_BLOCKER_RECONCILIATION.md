# October launch blocker reconciliation

## Purpose and source boundary

This record reconciles the canonical October launch blocker inventory at clean
base commit `030da8a2928473b9b5af35a158ea6ad5c5ad8e49`, tree
`7e7430c7f3fe3dd80aeec6c06a8860f48728b520`. It corrects one omission:
`FD-W10-001` makes the minimum subscription and billing plumbing required to
sell, grant and administer paid access launch-critical, while the W10
completion map remains at **0/8 complete slices** and **0/13 terminal checks**.
The canonical inventory therefore needs one coherent `subscription_billing`
blocker.

Independent review also identified the distinct open W2 terminal check 12
(representative customer-language/UX evidence) and two calculation families
that were within the settled October scope but absent from the canonical family
list. This is an inventory and routing record, not evidence that any blocker is
closed. All 18 blockers remain non-passing. The record does not alter a
completion map, approve a policy or residual risk, enable a provider, select a
target environment, or grant merge, release, activation or go-live authority.

## Exact source bindings

The following SHA-256 values identify the authority and current maps used for
this reconciliation. They are evidence inputs; their presence does not upgrade
their assurance state.

| Source | SHA-256 |
|---|---|
| `FOUNDER_DECISIONS.md` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` |
| `docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` | `bd42b33d98f598a5ed56f1e40c21dfea99371399387de0e59d73522673bbba0d` |
| `docs/FREEAGENT_COMPLETION_MAP.md` | `3686ddfc965357b6942bdc5db1513c35081f5d2b6b8865246dbc6ff954fb0778` |
| `docs/XERO_COMPLETION_MAP.md` | `de759b0327fb31df633819d646292df852dcf19c5346c63d90cea1e6bbd0630c` |
| `docs/QUICKBOOKS_COMPLETION_MAP.md` | `41c337c61f948622d15bec5ae807e9b7f711f799baf2344cfe8ffdb1d56a2b84` |
| `docs/YAPILY_COMPLETION_MAP.md` | `0edd04228b3cdb5a70d7394464b9672d92e29df893e217798bda09062388ba68` |
| `docs/W1_COMPLETION_MAP_SUPPORTING.md` | `f26e5009a9c005ba8ac47530307648bb6ca672e523916ffb0a9cb8846510916b` |
| `docs/W2_COMPLETION_MAP.md` | `cf4209c27dd57ed4153ee8bd4a3f5edf040d23fcd1c92b9eff23f58e68b11ac6` |
| `docs/HICBC_PARTNER_SUPPORT.md` | `e386dd6b71c5b39a3df533eadf58b6bb025dd66de8ebdff6059d8746ff913706` |
| `docs/W8_COMPLETION_MAP.md` | `99f03a8e255ea096e7366e673607606e5528524403fbc80b3f883501d23a50a3` |
| `docs/W9_COMPLETION_MAP.md` | `19270167e25dd3cb2093cbdbb0b6b0990d6bfd92c1e20da4b3cc52c4c1aaea57` |
| `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md` | `4d57107306bf78e5bf32ee2f2de24bf49531abbc1cb2dddf20595ae907893647` |
| `docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md` | `50bc0e20729b9b0120d125510b6f81e84f2d37967f3cb76b51cfcba4633e7a72` |
| pre-correction `reserved_west/release_gate.py` | `3d67ad473c84e8b081d705114f70b9c6562e81781dda098f70cc1bcd15011730` |
| pre-correction `tests/test_release_gate.py` | `8885ebd4098b87d6c2ed2bd165c4121f083fd8f6108abc44f11560b62f13b214` |
| pre-correction `tests/test_assurance_metadata.py` | `0ea443805868996a74ad3a691f17b4da3eab2201931ff6df05d2cf99149de818` |

## Canonical blocker map

“Category” records the current canonical non-passing state. “Owner/evidence”
names the current completion-map or evidence owner, not an assertion that the
named workstream can close every external or human dependency itself.

| Canonical blocker | Current owner/evidence | Category | Evidence required to clear | Next action |
|---|---|---|---|---|
| `paye_evidence_and_forecasting` | HMRC/PAYE fallback map; durable current-position route at `c6f5e4a` | `evidence_missing` | Target-runtime and representative evidence for the paid owner-bound current-position path; external authority evidence if that source is later enabled | Preserve missing/conflicting and unknown-future-pay states; run target and representative checks when their environments are available |
| `paye_payslip_manual_evidence_journey` | HMRC/PAYE fallback map; durable manual route and current-position composition | `evidence_missing` | Target custody, retention/backup, privacy/security and representative UX evidence for structured manual PAYE | Keep raw upload/extraction outside the approved manual scope unless separately authorised; collect the remaining target/human evidence |
| `hmrc_integration` | HMRC/PAYE fallback map; W8 slice 4; W9 `ACT-02` | `externally_blocked` | Exact official source contract, credential custody, authenticated disabled-first transport, sandbox journeys, error/recovery and target assurance | Obtain the applicable HMRC access/custody/sandbox facts; do not infer production capability from local contracts |
| `freeagent_integration` | FreeAgent completion map, FA-S2–S6 | `not_implemented` | Owner/company-bound encrypted custody, disabled-first adapter, complete resilience, sandbox and target/customer assurance | Resume at FA-S2 only after the external custody design is approved; preserve accepted FA-S1/FA-S4 evidence |
| `xero_integration` | Xero completion map, X-S3–S5 | `not_implemented` | Authenticated transport/refresh and pagination, disabled customer journey, sandbox plus privacy/security/operations evidence | Start X-S3 only when credential, custody and sandbox entry gates are available |
| `quickbooks_integration` | QuickBooks completion map, Q-S2/Q-S3/Q-S5/Q-S6 | `not_implemented` | Secret-custody transport, callback/realm ownership, complete canonical ingestion/sync and sandbox/operational assurance | Sequence Q-S2 before Q-S3 and the remaining Q-S5 ingestion; retain disabled state through Q-S6 |
| `yapily_ais` | Yapily completion map, Y2–Y3 | `externally_blocked` | Resolved hosted-URL/schema facts, credential/consent custody, sandbox accounts/transactions journey, retention/revocation and legal/provider delta | Resolve the documented hosted-URL conflict and approved sandbox/custody entry gates before Y2 |
| `yapily_pis` | Yapily separate PIS gate | `externally_blocked` | Contractual/provider confirmation, regulatory/legal/security/custody controls, same-owner destination, consent/status and launch assurance | Keep PIS separate and disabled; obtain its exact provider/legal entry evidence before implementation or activation |
| `mtd_indication` | W8 completion map and bounded W1 scope | `not_executable` | Customer-facing indication over complete current evidence that preserves incomplete/unsupported MTD states and passes integrated/customer-language review | Exercise the exact indication through the assembled W8 customer boundary; full MTD filing remains outside scope |
| `poa_sa_cash_obligation_customer_language` | Founder Self Assessment Payments on Account decision; W2 terminal check 12 | `evidence_missing` | Representative customer-language/UX evidence that annual liability, HMRC bill, payment timing, set-aside gap and claim-to-reduce limitations are not misleading | Test the exact accepted W1/W2 customer boundary with representative users and preserve the result as reviewable evidence; do not reopen the complete six-slice W2 implementation denominator |
| `evidence_persistence_and_deletion` | W9 S3; `PERSIST-01/02`, `DATA-01/02/03`, `AUTH-03` | `not_implemented` | Approved minimised schema/datastore, owner-to-business membership, durable atomic I/O, authenticated integrity, retention, erasure, backup and migration evidence | Settle the explicit lifecycle/target/custody facts, then implement the physical repository and deletion path without relabelling the accepted non-durable S3 chain |
| `privacy_security_review` | W9 S1/S5; `PRIV-01/02` and decision dossier | `evidence_missing` | Exact-candidate data-flow/threat/privacy review, mitigations, hostile/target checks, named acceptance and residual-risk disposition | Complete internal exact-candidate review and collect the target/human evidence; escalate only material unresolved questions |
| `target_environment_testing` | W9 S5; `RUNTIME-01`, `AUTH-01`, `ACT-02` | `evidence_missing` | Immutable target identity/configuration, complete suite, negative/failure/browser and applicable provider/identity journeys with redacted review evidence | Run only after the intended runtime and approved access exist; keep local passes distinct from target evidence |
| `operational_readiness` | W9 S4/S5; `MON-01`, `OUTAGE-01`, `REC-01`, `INC-01` | `not_implemented` | Named owners, monitoring/alerts, accepted runbooks, backup/restore/rollback and incident/outage exercises in the intended environment | Name the responsible owners and target design, then implement/exercise the bounded operational controls |
| `subscription_billing` | `FD-W10-001`–`003`; W10 completion map S2–S8; W9/W10 threat evidence | `not_implemented` | All 8 W10 slices and 13 terminal checks: settled remaining policy, owner-bound durable billing/event evidence, verified Stripe edge and reconciliation, entitlement enforcement, customer journeys, security/target/provider/legal evidence and explicit release authority | Continue the finite W10 map from its exact open policy/provider/persistence boundaries; retain disabled-first behavior and do not count partial contracts as a complete slice |
| `hicbc_manual_privacy_retention_legal` | HICBC partner-support evidence; W9 `DATA-01/02/03`, `PRIV-01/02` | `privacy_retention_review_required` | Approved notice, lawful basis, minimised retention/deletion/backup schedule plus authenticated route and customer/privacy evidence | Complete the internal privacy/retention review; obtain external advice only if it identifies a material unresolved legal/privacy question |
| `hicbc_linked_consent_privacy_security` | HICBC partner-support evidence; Founder linked-consent decisions; W9 auth/privacy gates | `privacy_retention_review_required` | Mutual consent, revocation/unlinking and relationship-period behavior, owner/cross-account authorisation, anti-probing, privacy/security and customer evidence | Independently test the exact linked-account journey and keep it feature-gated until all evidence is accepted |
| `hicbc_annual_integration_assurance` | HICBC purpose-aware integration; W8 slices 2/5 | `not_executable` | Independent integrated evidence that adequate HICBC enters only the permitted annual/reserve boundary, uncertainty suppresses action, and payment remains separately gated | Run the exact annual-to-cash/customer composition assurance after its persistence/provider dependencies are available |

## Integrity and follow-on regeneration

The canonical blocker denominator after independent-review correction is
exactly **18** and includes both `subscription_billing` and
`poa_sa_cash_obligation_customer_language`. No row above is cleared or
reclassified as complete. The exact ordered supported-calculation-family list
is now:

1. `paye_multiple_employment`
2. `sole_trade`
3. `uk_property`
4. `foreign_property`
5. `dividends`
6. `savings`
7. `pension_treatment`
8. `student_loan_pgl`
9. `evidence_reconciliation`
10. `hicbc`
11. `blind_persons_allowance`

`reserved_west/release_gate.py` is an input to the assurance implementation
identity. This source change therefore makes any previously generated
canonical result, rendered release result and `reserved/assurance_metadata.json`
stale by design. This phase deliberately does **not** edit those generated
artifacts. After this exact candidate is independently accepted and integrated,
the follow-on release-evidence package must, on that accepted clean lineage:

1. run the canonical release gate to regenerate its structured and rendered
   results with the new implementation identity, 18-blocker inventory and exact
   11-family list;
2. independently inspect the exact result and preserved `not_ready` decision;
3. regenerate assurance metadata from that exact canonical result; and
4. run metadata-freshness, release-gate and applicable broad regression checks.

Until that follow-on succeeds, existing generated release evidence must not be
presented as current for this corrected release-gate source.
