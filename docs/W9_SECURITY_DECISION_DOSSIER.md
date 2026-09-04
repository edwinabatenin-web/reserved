# W9-S1A — Security, privacy and operations decision dossier

Status: **decision entries, not decisions**

This dossier records the exact implementation-blocking choices required by
W9 S2-S4. It catalogues each choice with its accountable authority, why it
blocks implementation or activation, the current safe default, options,
trade-offs/risks, existing constraints, the exact evidence required to decide,
and the downstream packages affected. It does not choose an option, fabricate
legal/privacy advice, name an owner not already established, or turn a standard
engineering suggestion into Founder authority.

- Base commit: `dd98c4421707f54eb0b564a85ee77d3ed286d79d`
- Evidence cut-off: 4 September 2026 at exact integration commit
  `81ae02044cccd921d98a0d1fc2360e1c4a983ab1`, tree
  `ac5922e7aae0016a54f78a8645a244ac83eae0d2`.
- Narrow HICBC/W8–W9 refresh: source
  `7674b2f756f621ae9a8d1fe18063f634be90c367` integrated as
  `91cb4c2f14bce089db1f92f656c8cbc1d85639b7`; source
  `5ba53dccc8c608ff9c61a6913fa29704141c38a2` integrated as
  `d3c0f53f785a4fca75e54c466032244ee2bbb2b3`, tree
  `68cacad8f926a790b43af44e4a77bd61e7fe4594`. These exact immutable
  checkpoints update DEC-03 and DEC-12 only, not historical pins or external
  gates. This refresh changes only the two companion documents and their
  evidence test, not the gap register, product, configuration or Founder policy.
- Narrow live-current W10 route-evidence refresh binds the independently
  accepted S5C product checkpoint
  `3c63e64e478957ce04ee1154363c2eae94b82b30`, tree
  `ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7`. It records only reviewed
  legacy/internal route hardening; Founder Q2, paid-entitlement enforcement,
  W10-S5 completion and every W9 gate remain open. Strict W9 completion
  remains **0/5**, with all 13 previously unnamed accountable decision owners
  still unnamed.
- [W9-S1 independent-review evidence](W9_S1_INDEPENDENT_REVIEW_EVIDENCE.md)
  supplies findings for this reconciliation only. It is not assurance
  authority, human acceptance, or evidence that W9-S1 is complete.
- Exact source SHA-256 bindings for the reconciled W9-S3A/S3B, W9-S4A–E and
  W10 S2A/S2B/S3A/S3B/S4A/S5A/S5B/S5C-related evidence are recorded in the companion
  [data-flow and threat model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md#exact-current-state-source-binding).
- Companion document: [W9 launch data-flow and threat model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md)
- Authoritative inputs: [W9 completion map](W9_COMPLETION_MAP.md),
  [W9 gap register](W9_SECURITY_OPERATIONS_GAP_REGISTER.md),
  [W10 billing authority and policy contract](W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md),
  [Founder Decisions](../FOUNDER_DECISIONS.md).
- Reconciled Founder authority: `FD-W9-001` (durable minimised owner-bound
  structured annual position), `FD-W10-002` (provisional Stripe subscription
  baseline) and `FD-W10-003` (October paid-entitlement lifecycle). These settle
  policy; they do not close the remaining legal, retention, custody, target,
  provider or activation gates recorded below.

## Decision entries

### DEC-01 — Token/credential datastore and encryption/KMS equivalent

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-01 |
| Accountable decision owner/authority | Security owner (to be named under W9-S4); Founder authorisation required for the production custody boundary |
| Why it blocks implementation or activation | OAuth contracts deliberately stop at an abstract `TokenStore` boundary; no encrypted store or external key custody exists, so provider activation would store plaintext or invent home-grown encryption |
| Current safe default | No token store; only opaque `CredentialReference` values appear outside exchange/refresh; provider adapters remain placeholders |
| Options | Managed secret/envelope encryption with a KMS-held key; or database ciphertext via an approved AEAD library with the master key held outside the database |
| Trade-offs/risks | Home-grown encryption or a key stored beside ciphertext creates a false security claim; managed KMS adds an external dependency and cost |
| Existing constraints/evidence | `reserved/providers/oauth_contracts.py` defines the `TokenStore` protocol; `PROVIDER_BOUNDARY_ADOPTION.md` documents the deliberate non-implementation |
| Exact evidence required to decide | Approved datastore/KMS or equivalent, key owner, access boundary, rotation, break-glass, audit and recovery design |
| Downstream packages affected | W9-S2 token-store implementation; provider adapter integration |
| Gating | Implementation-gating and production-gating |

### DEC-02 — Key custodian, separation, rotation, break-glass, audit and recovery

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-02 |
| Accountable decision owner/authority | Security owner (to be named under W9-S4); operational owner for recovery |
| Why it blocks implementation or activation | Correct encryption requires key generation/custody, versioning/rotation, backup/restore behaviour, access control and audit events before any token is stored |
| Current safe default | No keys are generated or stored; provider secrets are not retained by the application |
| Options | Deployment secret/KMS facility with envelope encryption; or an AEAD master key in a deployment secret facility with periodic rotation |
| Trade-offs/risks | Key loss without recovery would lock out provider reconnects; over-broad break-glass access would undermine separation |
| Existing constraints/evidence | `PROVIDER_BOUNDARY_ADOPTION.md` sequenced-adoption steps 1-2; gap `CUST-02` |
| Exact evidence required to decide | Named key owner, separation model, rotation schedule, break-glass process, audit trail and recovery procedure |
| Downstream packages affected | W9-S2 custody implementation; W9-S4 key recovery |
| Gating | Implementation-gating and production-gating |

### DEC-03 — Minimised annual-position/evidence field inventory, purpose, provenance/integrity and owner schema

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-03 |
| Accountable decision owner/authority | Privacy/security owner (to be named under W9-S4); Founder authorisation for the durable schema |
| Why it blocks implementation or activation | `FD-W9-001` settles a durable minimised owner-bound structured annual tax/cash position with evidence references, provenance and uncertainty. W9-S3A provides an exact minimised admitted projection and W9-S3B provides a detached structural/in-memory repository contract, but the field-by-field lifecycle, lawful basis, physical datastore/schema, key custody, migration and activation remain gated; durable persistence still cannot be built or activated |
| Current safe default | No physical schema, database I/O or durable annual-position write. S3A/S3B remain contract evidence only; S3B denies upstream-admission and persistence authority, the `tax_calculations` stub is not used, and `FD-W9-001` is settled policy rather than an approved lifecycle |
| Options | Minimised owner-bound schema with provenance/integrity markers and immutable audit (now the settled policy direction); or continue ephemeral-only until the gated inventory is approved |
| Trade-offs/risks | Persisting too much enlarges the privacy surface; persisting too little breaks cross-session continuity |
| Existing constraints/evidence | `FD-W9-001`; integrated `reserved/annual_position_persistence_contract.py` (historical W9-S3A `c489c25bab669c64e1c11d28caf29fcde9678fdd`, accepted migration `d3c0f53f785a4fca75e54c466032244ee2bbb2b3`) and `reserved/annual_position_repository_contract.py` (W9-S3B, `110a90043dfc770c70059482be9d7b7e237749a6`). S3A checks the exact source type before property or descriptor access, validates the sealed owner-unbound handoff and exact source/evidence/as-of/year/geography coherence, then binds separately supplied authenticated user/business references. W8 is `owner_authoritative=False` with no user/business identity; owner-bound customer results are not accepted admission inputs. This local contract supplies no physical persistence, provider or production authority. See `W9_S3A_ANNUAL_POSITION_PERSISTENCE_CONTRACT.md`, `W8_S2C_ANNUAL_CASH_CUSTOMER_HANDOFF_EVIDENCE.md`, `INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md`; gaps `PERSIST-01`, `PERSIST-02` |
| Exact evidence required to decide | Approved field-by-field purpose, provenance/uncertainty representation, owner schema, datastore/encryption and migration rules |
| Downstream packages affected | W9-S3 persistence; W9-S5 privacy/security acceptance |
| Gating | Implementation-gating and production-gating |

### DEC-04 — Retention, supersession, legal exceptions, account erasure and backup expiry

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-04 |
| Accountable decision owner/authority | Privacy/legal owner (to be named under W9-S4); Founder authorisation for legal-hold exceptions |
| Why it blocks implementation or activation | W9-S3A/S3B now model a minimised admitted projection, supersession structure and in-memory deletion decisions, but lawful purpose, retention periods, legal-hold exceptions, backup expiry and whole-account erasure remain unresolved; `FD-W9-001` adds a durable minimised structured position to the intended erasure surface without settling those lifecycle rules |
| Current safe default | No durable annual-position or raw-document payload is stored. S3B's in-memory deletion decision is not a deletion executor or proof of erasure; feature-level owner deletion and HICBC hooks remain partial, and raw payslip originals remain transient (`FD-W9-001`) |
| Options | Field-by-field retention register with legal exceptions and backup-expiry schedule; or retain ephemeral-only and defer durable storage |
| Trade-offs/risks | A legal-hold exception without ownership could block erasure indefinitely; under-specified retention risks over-collection |
| Existing constraints/evidence | Founder Decisions establish minimisation and deletion principles; `FD-W9-001`; gaps `DATA-01`, `DATA-02`, `DATA-03`, `AUTH-03` |
| Exact evidence required to decide | Privacy/security owner approval of field-by-field purpose, retention, deletion, exception and backup-expiry register |
| Downstream packages affected | W9-S3 lifecycle; W9-S4 backup/restore; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-05 — PAYE raw-document acquisition, extraction, storage, deletion proof, failure/retry and backup behaviour

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-05 |
| Accountable decision owner/authority | Privacy/security owner (to be named under W9-S4) |
| Why it blocks implementation or activation | The `secure_deletion_required` marker is not proof of deletion; upload/extraction/storage/failure/retry and backup behaviour do not exist; `FD-W9-001` keeps raw payslip originals transient/deleted but does not define the deletion executor/evidence |
| Current safe default | No raw payslip is uploaded or stored; only typed, bounded fields and a deletion disposition are recorded |
| Options | Isolated raw-document flow with delete-after-check executor; or continue manual fallback without raw-document persistence |
| Trade-offs/risks | Storing a raw payslip enlarges exposure; deleting before verification risks losing evidence |
| Existing constraints/evidence | `FD-W9-001`; `reserved/engines/paye_extraction_confirmation.py`; gap `PAYSLIP-01`; `HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` |
| Exact evidence required to decide | Approved raw-document lifecycle plus deletion executor/evidence; delete-after-check, failure/retry, replacement, no-content-logging and backup-expiry tests |
| Downstream packages affected | W9-S3 raw-document flow; W9-S5 privacy acceptance |
| Gating | Implementation-gating and production-gating |

### DEC-06 — CSP acceptance versus tightening

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-06 |
| Accountable decision owner/authority | Security owner (to be named under W9-S4) |
| Why it blocks implementation or activation | The current CSP permits inline script/style execution; launch requires conscious acceptance or a nonce/hash migration |
| Current safe default | Permissive CSP baseline with `unsafe-inline` on scripts/styles |
| Options | Accept the current CSP with a recorded risk; or migrate to nonce/hash-based CSP and tighten |
| Trade-offs/risks | Tightening may break Clerk/Turnstile and inline handlers; accepting it leaves injection surface unmitigated |
| Existing constraints/evidence | `reserved/__init__.py` CSP baseline; gap `AUTH-02`; `AUTHENTICATION_READINESS.md` |
| Exact evidence required to decide | Security owner records accepted CSP/risk or approves exact tightening; browser regression and injection-focused evidence pass |
| Downstream packages affected | W9-S5 target privacy/security acceptance |
| Gating | Production-gating |

### DEC-07 — Target runtime/deployment isolation

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-07 |
| Accountable decision owner/authority | Operational owner (to be named under W9-S4); Founder authorisation for target selection |
| Why it blocks implementation or activation | The suite has not been repeated in the intended launch runtime; deployment isolation and immutable target identity are undefined |
| Current safe default | Local/synthetic evidence only; no target deployment is asserted |
| Options | Select an isolated target runtime with immutable build identity; or continue local-only until target is named |
| Trade-offs/risks | Deploying without isolation risks supply-chain/runtime compromise; delaying blocks target evidence |
| Existing constraints/evidence | `reserved_west/release_gate.py` `target_environment_testing`; gap `RUNTIME-01` |
| Exact evidence required to decide | Immutable target identity and configuration, complete required suite, failure paths, browser journeys and redacted artifact register |
| Downstream packages affected | W9-S4 monitoring/backups; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-08 — Monitoring/alert channels and named operational owners

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-08 |
| Accountable decision owner/authority | Operational owner (to be named under W9-S4) |
| Why it blocks implementation or activation | There is no evidenced target monitoring, alert routing or service-level owner; local health/tax-rule checks do not close the slice |
| Current safe default | Local application/database health boundary and tax-rule drift monitor only |
| Options | Named owners with alert routing for health/security/provider/tax-rule events; or defer until target runtime is selected |
| Trade-offs/risks | Alerts without owners are noise; over-alerting leaks sensitive data to logs |
| Existing constraints/evidence | `tax_rule_monitor.py`; gap `MON-01`; `reserved_west/release_gate.py` `operational_readiness` |
| Exact evidence required to decide | Target health/security/provider/tax-rule alerts reach named owners; false-positive, missed-heartbeat and sensitive-data tests pass |
| Downstream packages affected | W9-S4 monitoring; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-09 — Backup objectives, restore, rollback and key recovery

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-09 |
| Accountable decision owner/authority | Operational owner (to be named under W9-S4); security owner for key recovery |
| Why it blocks implementation or activation | Recoverable backups, restoration tests, rollback and key recovery are not evidenced; database transaction rollback is not disaster recovery |
| Current safe default | Transactional rollback and Git revertibility only |
| Options | Encrypted backups with RPO/RTO objectives and key recovery; or defer durable backup until target storage is selected |
| Trade-offs/risks | Unencrypted backups leak data; missing key recovery strands restored data |
| Existing constraints/evidence | gap `REC-01`, `DATA-03` |
| Exact evidence required to decide | Approved recovery objectives and ownership; encrypted backup, restore, integrity, key recovery, rollback and data-loss-window exercises pass |
| Downstream packages affected | W9-S4 resilience; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-10 — Incident/security/customer-support escalation and ownership

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-10 |
| Accountable decision owner/authority | Security and operational owners (to be named under W9-S4); Founder authorisation for external escalation |
| Why it blocks implementation or activation | No complete incident/security response and customer-support escalation ownership is evidenced |
| Current safe default | No incident/support runbooks or named owners |
| Options | Accepted incident/support runbooks with tax-rule, provider/API, privacy and security owners; or defer until owners are named |
| Trade-offs/risks | Unnamed owners leave incidents unhandled; premature ownership claims misassign accountability |
| Existing constraints/evidence | gap `INC-01`; `reserved_west/release_gate.py` `operational_readiness` |
| Exact evidence required to decide | Accepted incident and support runbooks with tax-rule, provider/API, privacy and security owners; tabletop/drill evidence and follow-up actions |
| Downstream packages affected | W9-S4 operational resilience; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-11 — Security-relevant W10 dependencies: provisional provider custody/webhook model, entitlement evidence boundary and unresolved refund/dispute/chargeback/reversal/VAT and paid-surface policies

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-11 |
| Accountable decision owner/authority | Founder (provisional provider and paid-entitlement lifecycle); security owner for custody/webhook model |
| Why it blocks implementation or activation | `FD-W10-002` selects Stripe Billing, Checkout and Customer Portal as the provisional disabled-first subscription baseline (not Stripe Connect), while terms/DPA/fees, credentials, sandbox/production, charging and activation remain gated. S2A binds the `FD-W10-003` lifecycle and S2B closes four ordinary defaults only: promotions/discount mechanics inactive, partner offers disabled, mid-cycle plan changes/proration disabled, and no manual entitlement override. Five exact keys remain unresolved: refunds; tax invoicing/additional VAT presentation; exact paid-access surface; billing-account recovery; and post-settlement dispute/chargeback/reversal consequences. S3A/S3B/S4A are non-durable or disabled evidence; S5A/S5B are inventory/reconciliation evidence; S5C hardens only the reviewed legacy/internal routes. None supplies provider authenticity, persistence, entitlement mutation or paid-surface enforcement |
| Current safe default | No checkout, entitlement grant, charge or provider credential is wired; Stripe identifiers/statuses are observations, not entitlement authority; `payment_recovery` is a canonical bounded state with a non-extendable seven-day deadline and continuing access, not normally paid and not provider-default behaviour. Accepted S5C closes or redirects reviewed legacy/internal product bypasses, production-404s the sandbox checklist and preserves Founder/Capital-Gains separation without deciding paid access |
| Options | Keep the provisional Stripe baseline disabled while specialist/Founder evidence settles the five exact open keys and engineering defines custody/authenticity/webhook/durable-inbox/entitlement boundaries; or replace the provisional provider before activation |
| Trade-offs/risks | Weak authenticity, idempotency or reconciliation could mis-grant entitlement; provider-specific configuration grows migration cost; silently choosing refund/VAT/post-settlement/access policy creates legal, price and access risk |
| Existing constraints/evidence | `FD-W10-001`, `FD-W10-002`, `FD-W10-003`; `W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md`; `STRIPE_CONNECT_SPEC.md`; `reserved/billing/contracts.py`; S2A `provider_lifecycle_authority.py`; S2B `fail_closed_launch_defaults.py`; S3A `entitlement_core.py`; S3B `event_inbox_contract.py`; S4A `stripe_disabled_first_contract.py`; S5A `W10_S5A_PAID_SURFACE_INVENTORY.md`; accepted S5B `W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md`; accepted product checkpoint S5C and its candidate `W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md`; `reserved/providers/payments/stripe_connect.py` remains outside subscription authority |
| Exact evidence required to decide | Accepted provider terms/DPA/fees and sandbox/target evidence; exact custody, signature/authenticity, webhook, durable-inbox/reconciliation and entitlement-evidence design; specialist/Founder resolution of the five open keys; final paid-surface acceptance and enforcement tests |
| Downstream packages affected | W10 subscription plumbing; W9-S2/S3 custody and lifecycle integration |
| Gating | Implementation-gating and production-gating |

### DEC-12 — Linked-customer HICBC mutual permission, minimisation, anti-probing, audit, withdrawal/unlinking and deletion

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-12 |
| Accountable decision owner/authority | Founder Decisions already require an auditable linked-HICBC notice/consent record; the privacy/legal owner (to be named under W9-S4) owns the remaining lawful-basis, minimisation, anti-probing, retention/deletion and target-acceptance design |
| Why it blocks implementation or activation | Linked HICBC requires mutual affirmative permission from two customers, cross-account use of the minimum partner evidence, auditable notice/version/who/when, withdrawal/unlinking and deletion. The accepted five-table lifecycle implements separate affirmative permission after four notices, atomic page/binding issuance and atomic consent validation, but privacy/retention/legal/target gates remain open; documented lawful basis, minimisation, anti-probing and deletion design plus independent review are still required |
| Current safe default | Linked-HICBC persistence is integrated but disabled by default behind `HICBC_ENABLED`. Invitation acceptance creates a link only, never permission. The exact link/cycle/user/year/notice/expiry form binding denies stale/tampered/cross-context/expired replay. Re-link advances `permission_cycle`, invalidates old consent/bindings and requires fresh permission from both users. Current link/consent rows control use (one active link, both non-withdrawn authoritative-notice rows); notice-version-aware append-only lifecycle events are evidence only, never consent authority. Unknown partner/Child Benefit facts fail closed and manual partner estimates remain bounded third-party data |
| Options | Production-activate the implemented owner-bound linked record once auditable consent and anti-probing controls are independently reviewed; or keep it disabled by default until the privacy design is approved |
| Trade-offs/risks | Persisting partner evidence enlarges disclosure/probing surface; refusing to persist limits cross-session continuity |
| Existing constraints/evidence | Founder Decisions establish minimisation and mutual-consent principles; accepted `91cb4c2f14bce089db1f92f656c8cbc1d85639b7` from source `7674b2f756f621ae9a8d1fe18063f634be90c367`; `reserved/database.py` (`hicbc_links`, `hicbc_link_invitations`, `hicbc_link_consents` with `withdrawn_at`, `hicbc_permission_form_bindings`, `hicbc_permission_events`, `delete_all_hicbc_links_for_user`); `reserved/web/hicbc.py` (`/v2/hicbc/link/*`); `HICBC_PARTNER_SUPPORT.md`; `HICBC_LINKED_MUTUAL_CONSENT_JOURNEY_EVIDENCE.md`. Event transition uniqueness includes notice version: repeated acceptance is idempotent, later notices remain separately auditable; withdrawal preserves the accepted notice identity. Events are append-only through the application API, not deletion-proof: account deletion cascades to permissions, bindings and events. Gaps `DATA-01`, `DATA-02`, `AUTH-03` remain |
| Exact evidence required to decide | Documented lawful basis, transparency, purpose limitation, minimisation, withdrawal/unlinking, deletion and anti-probing controls plus cross-account privacy tests |
| Downstream packages affected | W9-S5 privacy/legal-basis, minimisation/anti-probing, retention/deletion and target cross-account acceptance; focused hardening only if that assurance identifies a defect |
| Gating | Assurance and production-gating; linked-HICBC persistence is already integrated and remains disabled pending acceptance |

### DEC-13 — Customer MTD scope indication source/residence/cessation/timing/exclusion boundaries and formal-vs-indication distinction

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-13 |
| Accountable decision owner/authority | Privacy/security owner (to be named under W9-S4) |
| Why it blocks implementation or activation | The integrated MTD core (`reserved/engines/mtd_readiness.py`) and presentation (`reserved/services/mtd_scope_indication.py` plus `mtd_scope_indication_presentation.py`) are implemented and keep the indication distinct from HMRC's formal determination; activation still requires source-acquisition/orchestration, authenticated routing, recheck scheduling, target UX/accessibility, privacy and release acceptance |
| Current safe default | Integrated core and renderer run ephemerally; gross-before-expenses input; "Worth reviewing" wording; no "MTD ready" or definite-application claim; no filing/submission, authenticated route, source orchestration or recheck schedule is wired |
| Options | Wire source-acquisition/orchestration, authenticated routing and recheck scheduling to the integrated core/renderer; or keep the indication ephemeral and out of any filing path until target UX/accessibility/privacy/release acceptance |
| Trade-offs/risks | Overstating applicability risks false certainty; understating it under-serves customers near a threshold |
| Existing constraints/evidence | `MTD_SCOPE_INDICATION_EVIDENCE.md`; `MTD_SCOPE_INDICATION_PRESENTATION_EVIDENCE.md`; `reserved/engines/mtd_readiness.py`; `reserved/services/mtd_scope_indication.py`; `reserved/services/mtd_scope_indication_presentation.py`; `test_mtd_scope_indication.py`, `test_mtd_scope_indication_presentation.py`, `test_mtd_readiness.py` |
| Exact evidence required to decide | Source-acquisition/orchestration, authenticated routing, recheck scheduling, target UX/accessibility, privacy and release acceptance for the integrated MTD indication |
| Downstream packages affected | W9-S3 source acquisition/orchestration, authenticated routing and recheck scheduling; target UX/accessibility/privacy/release acceptance |
| Gating | Remaining-source-integration and production-gating; the MTD core and customer renderer are already integrated |

### DEC-14 — October geography admission and residence provenance

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-14 |
| Accountable decision owner/authority | Privacy/security owner (to be named under W9-S4) |
| Why it blocks implementation or activation | October annual/customer flows are constrained to England, Wales and Northern Ireland; the fail-closed E/W/NI admission guard and provenance handoff are integrated and independently reviewed, but no customer/provider path yet supplies a validated geography fact into the annual calculator, and target acceptance remains open |
| Current safe default | E/W/NI only; Scotland and Ireland are excluded from calculation, reserve and launch claims; foreign income/SEPA-ready models do not imply geography support |
| Options | Acquire and forward a validated customer geography fact (customer-source acquisition) and obtain target acceptance; or keep geography as a non-durable scope guard until the acquisition path is wired |
| Trade-offs/risks | Under-validated residence risks admitting Scottish Income Tax/Ireland leakage; over-collecting residence enlarges the privacy surface |
| Existing constraints/evidence | `W8_S3_GEOGRAPHY_ADMISSION_EVIDENCE.md`; `W8_S3B_GEOGRAPHY_PROVENANCE_HANDOFF_EVIDENCE.md`; `reserved/engines/integrated_annual_position.py` (`_enforce_geography_admission`); `test_w8_geography_admission.py` |
| Exact evidence required to decide | Customer-source acquisition of a validated E/W/NI geography fact and target acceptance; admission/provenance boundaries are already integrated and reviewed |
| Downstream packages affected | W9-S3 customer-source acquisition of validated geography; target acceptance |
| Gating | Remaining-source-integration and production-gating; geography admission and provenance are already integrated and independently reviewed |


## Non-activation and non-duplication statement

This package does not activate a provider, permit credentials, prove target
operation, close W9, declare launch readiness, or authorise
merge/release/go-live. It does not amend Founder Decisions, the W9 completion
map or the canonical release gate. It amends the gap register only for this
authorised evidence-only current-state reconciliation; it does not convert
local/synthetic evidence into external or launch assurance. Implemented,
integrated, externally evidenced and launch-ready remain distinct states and
are not conflated here.
