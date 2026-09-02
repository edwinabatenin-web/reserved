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
- Companion document: [W9 launch data-flow and threat model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md)
- Authoritative inputs: [W9 completion map](W9_COMPLETION_MAP.md),
  [W9 gap register](W9_SECURITY_OPERATIONS_GAP_REGISTER.md),
  [Founder Decisions](../FOUNDER_DECISIONS.md).

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
| Why it blocks implementation or activation | Durable annual-position/evidence persistence cannot be built without an approved field inventory, purpose, provenance/uncertainty representation and owner schema |
| Current safe default | Annual-position and evidence remain ephemeral; the `tax_calculations` stub is not used |
| Options | Minimised owner-bound schema with provenance/integrity markers and immutable audit; or continue ephemeral-only for the October boundary |
| Trade-offs/risks | Persisting too much enlarges the privacy surface; persisting too little breaks cross-session continuity |
| Existing constraints/evidence | `INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md`; gaps `PERSIST-01`, `PERSIST-02` |
| Exact evidence required to decide | Approved field-by-field purpose, provenance/uncertainty representation, owner schema, datastore/encryption and migration rules |
| Downstream packages affected | W9-S3 persistence; W9-S5 privacy/security acceptance |
| Gating | Implementation-gating and production-gating |

### DEC-04 — Retention, supersession, legal exceptions, account erasure and backup expiry

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-04 |
| Accountable decision owner/authority | Privacy/legal owner (to be named under W9-S4); Founder authorisation for legal-hold exceptions |
| Why it blocks implementation or activation | Field inventory, lawful purpose, retention periods, supersession, legal-hold exceptions, backup expiry and whole-account erasure are all unresolved |
| Current safe default | No durable annual-position or raw-document payload is stored; feature-level owner deletion and HICBC hooks only |
| Options | Field-by-field retention register with legal exceptions and backup-expiry schedule; or retain ephemeral-only and defer durable storage |
| Trade-offs/risks | A legal-hold exception without ownership could block erasure indefinitely; under-specified retention risks over-collection |
| Existing constraints/evidence | Founder Decisions establish minimisation and deletion principles; gaps `DATA-01`, `DATA-02`, `DATA-03`, `AUTH-03` |
| Exact evidence required to decide | Privacy/security owner approval of field-by-field purpose, retention, deletion, exception and backup-expiry register |
| Downstream packages affected | W9-S3 lifecycle; W9-S4 backup/restore; W9-S5 acceptance |
| Gating | Production-gating |

### DEC-05 — PAYE raw-document acquisition, extraction, storage, deletion proof, failure/retry and backup behaviour

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-05 |
| Accountable decision owner/authority | Privacy/security owner (to be named under W9-S4) |
| Why it blocks implementation or activation | The `secure_deletion_required` marker is not proof of deletion; upload/extraction/storage/failure/retry and backup behaviour do not exist |
| Current safe default | No raw payslip is uploaded or stored; only typed, bounded fields and a deletion disposition are recorded |
| Options | Isolated raw-document flow with delete-after-check executor; or continue manual fallback without raw-document persistence |
| Trade-offs/risks | Storing a raw payslip enlarges exposure; deleting before verification risks losing evidence |
| Existing constraints/evidence | `reserved/engines/paye_extraction_confirmation.py`; gap `PAYSLIP-01`; `HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` |
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

### DEC-11 — Security-relevant W10 dependencies: billing provider custody/webhook model, entitlement evidence boundary and unresolved lifecycle policies

| Attribute | Record |
| --- | --- |
| Decision ID | W9-DEC-11 |
| Accountable decision owner/authority | Founder (billing provider and pricing scope); security owner for custody/webhook model |
| Why it blocks implementation or activation | `FD-W10-001` brings paid subscription into scope but explicitly leaves provider choice, custody/webhook model, entitlement evidence and subordinate lifecycle policies unresolved |
| Current safe default | No billing provider is selected; Stripe is an explicitly non-selected placeholder; no entitlement or checkout is wired |
| Options | Select a billing provider and define tokenisation/webhook/entitlement evidence boundary; or defer W10 plumbing until a provider decision exists |
| Trade-offs/risks | A provider with weak webhook/idempotency could mis-grant entitlement; unresolved refund/VAT/discount policy risks mis-pricing |
| Existing constraints/evidence | `FD-W10-001`; `STRIPE_CONNECT_SPEC.md`; `reserved/providers/payments/stripe_connect.py` |
| Exact evidence required to decide | A reviewed provider-neutral W10 contract plus an exact billing-provider custody/webhook and entitlement-evidence decision |
| Downstream packages affected | W10 subscription plumbing; W9-S2/S3 custody and lifecycle integration |
| Gating | Implementation-gating and production-gating |

## Non-activation and non-duplication statement

This package does not activate a provider, permit credentials, prove target
operation, close W9, declare launch readiness, or authorise
merge/release/go-live. It does not amend Founder Decisions, the W9 completion
map, the gap register, or the canonical release gate. Implemented, integrated,
externally evidenced and launch-ready remain distinct states and are not
conflated here.
