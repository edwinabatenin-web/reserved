# W9-S1A — October launch data-flow and trust-boundary threat model

Status: **evidence and planning control only — not launch readiness**

This document traces the settled October launch flows from collection through
processing, evidence, presentation and deletion, and records the trust
boundaries and threat classes that apply to them. It documents and tests
evidence. It does not implement controls, select vendors or policies, create
another readiness authority, or alter production/readiness state.

- Base commit: `dd98c4421707f54eb0b564a85ee77d3ed286d79d`
- Authoritative planning inputs: [W9 completion map](W9_COMPLETION_MAP.md),
  [W9 security and operations gap register](W9_SECURITY_OPERATIONS_GAP_REGISTER.md),
  [Founder Decisions](../FOUNDER_DECISIONS.md), and the canonical
  `reserved_west/release_gate.py` October blocker inventory.
- State vocabulary: **implemented**, **integrated**, **externally evidenced**,
  **launch-ready** are distinct and are never conflated below.

## Mandatory October flow coverage

Each flow record states: data class, subject/owner, source, trust boundary
crossed, processing purpose, allowed destination, present storage behaviour,
unresolved target storage/retention/deletion state, existing control,
threat/failure mode, current fail-closed state, exact closure evidence and
canonical blocker/reference.

### FLOW-01 — Browser/customer input, authentication, identity broker, Reserved session and logout

| Attribute | Record |
| --- | --- |
| Data class | Customer identity (Clerk `sub`/`sid`), email/name, Reserved session identity, browser inputs |
| Subject/owner | Authenticated customer (Reserved user) |
| Source | Customer browser; Clerk identity broker (`CLERK_PUBLISHABLE_KEY` frontend API) |
| Trust boundary crossed | Browser/customer device ↔ Reserved application; identity provider/broker ↔ Reserved |
| Processing purpose | Establish a tamper-proof authenticated session; verify broker token before issuing Reserved's own signed session |
| Allowed destination | Reserved application session state and `users` table keyed by `clerk_user_id` |
| Present storage behaviour | Flask session cookie (`rsvd_session`) is HttpOnly, SameSite=Lax, Secure, 8-hour lifetime; session identity written after a full `session.clear()`; a `users` row is created/retrieved keyed by Clerk id; sensitive routes get `Cache-Control: no-store` and `Pragma: no-cache` |
| Unresolved target storage/retention/deletion | No target Clerk/Google/Apple revocation or account-deletion cascade; no retention/erasure schedule for identity records |
| Existing control | `reserved/auth.py` verifies `iss`, `azp` allowlist, `sub`, `sid` and optional `aud`, fails closed without a permitted origin; `clear_user_session()` wipes the whole session; `reserved/__init__.py` applies no-store headers and a permissive CSP baseline |
| Threat/failure mode | Spoofing/broken authorisation; CSRF/OAuth replay; session fixation; token replay; privilege escalation |
| Current fail-closed state | Verification returns `None` on any invalid/expired/forged token; demo login is gated by the `is_production_environment()` dual-lock |
| Exact closure evidence | Target sign-in, denial, expiry, logout, replay, account-deletion/revocation and Google/Apple journeys, independently reviewed with redacted evidence |
| Canonical blocker/reference | `AUTH-01`, `AUTH-02`, `AUTH-03`; `AUTHENTICATION_READINESS.md`; `reserved_west/release_gate.py` `target_environment_testing` |

### FLOW-02 — Accounting-provider OAuth consent/callback and opaque credential reference

| Attribute | Record |
| --- | --- |
| Data class | Provider-bound OAuth `state`, one-use authorisation code, raw token set, opaque credential reference |
| Subject/owner | Customer and the accounting provider (FreeAgent/Xero/QuickBooks) |
| Source | Provider consent screen and OAuth callback |
| Trust boundary crossed | Application ↔ accounting providers; application ↔ unresolved secret/token custody boundary |
| Processing purpose | Exchange a validated code exactly once and retain only an opaque reference |
| Allowed destination | A server-side token store behind the `TokenStore` protocol; never application callers or logs |
| Present storage behaviour | No encrypted token store exists; only opaque `CredentialReference` values may appear in user/sync/log/analytics records; raw token sets exist only transiently during exchange/refresh |
| Unresolved target storage/retention/deletion | Approved encrypted datastore/KMS or equivalent, key custody, rotation, revocation, audit and recovery are all unresolved |
| Existing control | `reserved/providers/oauth_security.py` issues hashed, provider-bound, expiring, single-use `state`; `oauth_contracts.py` consumes state before exposing a code and returns a redacted `OAuthTokenSet`; `exchange_and_store` returns only a `CredentialReference` |
| Threat/failure mode | CSRF/OAuth replay; callback/order manipulation; credential/token exposure; destination substitution |
| Current fail-closed state | Invalid or expired `state` raises `OAuthContractError` and consumes the state; a code is single-use; raw token sets are redacted in `repr` |
| Exact closure evidence | Approved datastore/KMS or equivalent, key owner, access boundary, rotation, break-glass, audit and recovery design |
| Canonical blocker/reference | `CUST-01`, `CUST-02`; `PROVIDER_BOUNDARY_ADOPTION.md`; `PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md`; `reserved_west/release_gate.py` provider `not_implemented` rows |

### FLOW-03 — Accounting account and transaction retrieval, normalisation and provider evidence

| Attribute | Record |
| --- | --- |
| Data class | Account and transaction records, translated `SyncPage` objects, normalised fields, redacted import manifest |
| Subject/owner | Customer and their accounting provider |
| Source | Accounting provider API via an injected, non-production HTTP transport |
| Trust boundary crossed | Application ↔ accounting providers; application ↔ unresolved secret/token custody boundary |
| Processing purpose | Retrieve, paginate, schema-validate and normalise provider data into provider-neutral evidence |
| Allowed destination | Provider-neutral sync/normalisation contracts and a payload-free import manifest |
| Present storage behaviour | No durable provider payload is retained; import evidence is payload-free; schema evidence records field names and coarse value kinds without source values |
| Unresolved target storage/retention/deletion | No approved provider-evidence reference lifecycle, retention or deletion schedule |
| Existing control | `http_boundary.py` validates exact non-live HTTPS origins before delegating to an injected transport and emits redacted summaries; `sync_contracts.py` enforces termination, loop/duplicate detection and monotonic watermarks; `schema_evidence.py` quarantines required-field loss/type drift |
| Threat/failure mode | SSRF/destination substitution; injection/schema drift; stale data and false certainty; evidence tampering |
| Current fail-closed state | Provider adapters are placeholders and `implementation_enabled=False`; `readiness.py` never enables network access from configuration alone |
| Exact closure evidence | Reviewed provider adapter, sandbox execution evidence, exact origin confinement, pagination completeness and redacted import manifest |
| Canonical blocker/reference | `CUST-02`, `OUTAGE-01`; `ACCOUNTING_INTEGRATIONS.md`; `PROVIDER_BOUNDARY_ADOPTION.md`; `reserved_west/release_gate.py` `freeagent/xero/quickbooks_integration` |

### FLOW-04 — HMRC/PAYE data retrieval

| Attribute | Record |
| --- | --- |
| Data class | HMRC/PAYE employment, income and tax data (DES Test Support contracts) |
| Subject/owner | Customer and HMRC |
| Source | HMRC MTD/PAYE endpoints (no production-capable adapter yet) |
| Trust boundary crossed | Application ↔ HMRC |
| Processing purpose | Retrieve and normalise HMRC data for annual tax computation |
| Allowed destination | Provider-neutral HMRC contract models |
| Present storage behaviour | No HMRC HTTP/OAuth adapter exists; contract evidence documents endpoints/schemas without retaining customer data |
| Unresolved target storage/retention/deletion | No approved HMRC source-evidence reference lifecycle |
| Existing control | HMRC contract modules (`reserved/providers/hmrc_*_contract.py`) capture reviewed contracts network-inert; `readiness.py` keeps HMRC `implementation_enabled=False` |
| Threat/failure mode | SSRF; credential/token exposure; stale data and false certainty; evidence tampering |
| Current fail-closed state | `hmrc_integration` is `externally_blocked` in the release gate; no adapter executes |
| Exact closure evidence | Reviewable PAYE Test Support OpenAPI operation, selected endpoint/scopes/errors, adapter, synthetic test user and end-to-end sandbox evidence |
| Canonical blocker/reference | `HMRC_ADAPTER_IMPLEMENTATION_DECISION.md`; `reserved_west/release_gate.py` `hmrc_integration`; `W9_SECURITY_OPERATIONS_GAP_REGISTER.md` |

### FLOW-05 — Bounded manual/payslip fallback and `secure_deletion_required` versus proof of deletion

| Attribute | Record |
| --- | --- |
| Data class | Structured payslip extraction candidate and customer-confirmed `PayeEvidenceCapture`; raw payslip document |
| Subject/owner | Customer |
| Source | Customer-supplied payslip (manual fallback) |
| Trust boundary crossed | Browser/customer device ↔ Reserved application; application ↔ database/persistence |
| Processing purpose | Extract bounded fields, obtain per-field customer confirmation, and record a deletion disposition for the raw document |
| Allowed destination | In-memory S1-compatible `PayeEvidenceCapture`; no raw document content is stored |
| Present storage behaviour | The confirmation contract performs no filesystem, network, logging or persistence of raw documents; `disposition` is `secure_deletion_required`, which is not proof of deletion |
| Unresolved target storage/retention/deletion | Raw-document upload, extraction, storage, deletion proof, failure/retry and backup expiry do not exist |
| Existing control | `reserved/engines/paye_extraction_confirmation.py` accepts typed, bounded fields only and rejects raw bytes/paths/identifiers; `paye_evidence_capture.py` marks the document source `SOURCE_DOCUMENT`/`PAYSLIP` |
| Threat/failure mode | Injection; credential/token exposure; logging/exfiltration; retention/deletion failure |
| Current fail-closed state | The only successful output is an in-memory partial capture; `secure_deletion_required` cannot be relabelled as deletion evidence |
| Exact closure evidence | Approved raw-document lifecycle plus deletion executor/evidence; delete-after-check, failure/retry, replacement, no-content-logging and backup-expiry tests |
| Canonical blocker/reference | `PAYSLIP-01`; `HMRC_PAYE_FALLBACK_COMPLETION_MAP.md`; `reserved_west/release_gate.py` `paye_payslip_manual_evidence_journey` |

### FLOW-06 — Canonical accounting evidence into annual tax calculation, provenance/uncertainty and annual position

| Attribute | Record |
| --- | --- |
| Data class | Canonical accounting evidence, provenance and uncertainty metadata, annual-position result |
| Subject/owner | Customer |
| Source | Provider-neutral normalised evidence and tax engines |
| Trust boundary crossed | Application ↔ database/persistence (currently non-persistent) |
| Processing purpose | Compute the annual tax position with provenance and uncertainty attached |
| Allowed destination | Ephemeral internal contracts only |
| Present storage behaviour | Annual calculations, provenance and uncertainty remain intentionally ephemeral; no incidental durable annual-position write exists |
| Unresolved target storage/retention/deletion | No approved owner-bound annual-position schema, evidence-reference lifecycle, integrity/concurrency design, access audit, retention or erasure path |
| Existing control | `INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md` records the `tax_calculations` stub as unsuitable; strict snapshot codec rejects unknown shape and weakened prohibitions |
| Threat/failure mode | Stale data and false certainty; evidence tampering; cross-owner/tenant leakage; injection/schema drift |
| Current fail-closed state | Annual-position non-persistence is the correct safe state until the lifecycle design is approved |
| Exact closure evidence | Approved minimised field inventory, purpose, provenance/uncertainty representation, owner schema, datastore/encryption and migration rules |
| Canonical blocker/reference | `PERSIST-01`, `PERSIST-02`; `INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md`; `reserved_west/release_gate.py` `evidence_persistence_and_deletion` |

### FLOW-07 — Annual liability into dated cash obligation, reserve gap/surplus and customer presentation

| Attribute | Record |
| --- | --- |
| Data class | Annual liability, dated cash obligation, reserve gap/surplus, customer-facing presentation |
| Subject/owner | Customer |
| Source | Annual tax computation and cash/reconciliation engines |
| Trust boundary crossed | Browser/customer device ↔ Reserved application |
| Processing purpose | Convert annual liability into a dated cash obligation and present reserve gap/surplus |
| Allowed destination | Customer presentation only |
| Present storage behaviour | Results remain ephemeral; presentation is bounded and does not persist a durable position |
| Unresolved target storage/retention/deletion | No approved durable cash/obligation record or retention schedule |
| Existing control | `cash_obligation_reconciliation.py`, `cash_ready_annual_position.py` and `cash_funding_position.py` compute without a money-movement side effect |
| Threat/failure mode | Stale data and false certainty; payment/cash misdirection; cross-owner/tenant leakage |
| Current fail-closed state | No payment is initiated; `TrackOnlyProvider` rejects non-track-only instructions |
| Exact closure evidence | Independent review of cash/reserve presentation against the canonical obligation contract |
| Canonical blocker/reference | `W2_S6_ANNUAL_TO_CASH_CONTRACT_PREPARATION.md`; `reserved_west/release_gate.py` `paye_evidence_and_forecasting` |

### FLOW-08 — Yapily AIS and explicitly customer-authorised payment-initiation boundary

| Attribute | Record |
| --- | --- |
| Data class | Bank consent token/account/transaction data (AIS); set-aside instruction (no live transfer) |
| Subject/owner | Customer and their bank |
| Source | Yapily Hosted Pages consent flow and bank accounts |
| Trust boundary crossed | Application ↔ Yapily/banks; browser/customer device ↔ Reserved application |
| Processing purpose | Read-only account information access; explicitly customer-authorised set-aside tracking only |
| Allowed destination | Provider-neutral AIS contracts; `TrackOnlyProvider` for set-aside intent |
| Present storage behaviour | Yapily live methods raise `NotImplementedError`; fixture behaviour is synthetic; `bank_connections`/`transactions` tables store consent/account/transaction rows under owner FK |
| Unresolved target storage/retention/deletion | Encrypted consent custody, institution-specific implementation and consent lifecycle are unresolved |
| Existing control | `reserved/providers/banking/yapily.py` separates AIS from payment initiation; `reserved/providers/payments/base.py` keeps money movement separate from AIS and `TrackOnlyProvider` cannot move money |
| Threat/failure mode | Spoofing/broken authorisation; payment/cash misdirection; webhook/replay; credential/token exposure |
| Current fail-closed state | `yapily_ais` and `yapily_pis` are `externally_blocked`; no live or automatic transfer authority exists |
| Exact closure evidence | Confirmed AIS product and Hosted Pages/consent/webhook contracts, encrypted consent custody, sandbox evidence |
| Canonical blocker/reference | `YAPILY_COMPLETION_MAP.md`; `YAPILY_INTEGRATION_SPEC.md`; `reserved_west/release_gate.py` `yapily_ais`, `yapily_pis` |

### FLOW-09 — Provider-neutral W10 subscription flow (plan/offer, checkout, billing evidence, entitlement, cancellation/refund, reconciliation)

| Attribute | Record |
| --- | --- |
| Data class | Plan/offer selection, checkout token, billing/webhook evidence, entitlement state, reconciliation data |
| Subject/owner | Customer and the unresolved billing provider |
| Source | Customer plan selection and the billing provider checkout/webhook |
| Trust boundary crossed | Application ↔ unresolved billing provider; browser/customer device ↔ Reserved application |
| Processing purpose | Sell, grant and administer access under the paid-subscription model established by `FD-W10-001` |
| Allowed destination | Provider-neutral W10 contracts only (none yet implemented) |
| Present storage behaviour | No W10 billing/entitlement implementation exists; `FD-W10-001` sets initial pricing (£29 monthly, £156 six-month, £288 yearly) plus special-offer support only |
| Unresolved target storage/retention/deletion | Billing provider, custody/webhook model, entitlement evidence boundary, renewal/cancellation/failure/entitlement/refund/VAT/discount/partner policies are all unresolved |
| Existing control | `reserved/providers/payments/stripe_connect.py` is an explicit non-selected, disabled placeholder; `STRIPE_CONNECT_SPEC.md` records Stripe as not selected |
| Threat/failure mode | Callback/order manipulation; webhook/replay/idempotency errors; payment/cash misdirection; cross-owner/tenant leakage; unsafe activation |
| Current fail-closed state | No checkout/tokenisation or entitlement grant is wired; payment initiation is disabled |
| Exact closure evidence | A reviewed, provider-neutral W10 contract plus an exact billing-provider custody/webhook decision |
| Canonical blocker/reference | `FD-W10-001`; `STRIPE_CONNECT_SPEC.md`; decision dossier `W9-DEC-11` |

### FLOW-10 — Intended persistence, evidence references, logs, monitoring, support access and incident handling

| Attribute | Record |
| --- | --- |
| Data class | Durable records, evidence references, logs, monitoring/alert events, support-access events |
| Subject/owner | Customer and operational owners |
| Source | Application runtime, database and monitoring/support tooling |
| Trust boundary crossed | Runtime ↔ logs/monitoring/support operators; application ↔ database/persistence |
| Processing purpose | Observe, operate, support and investigate the running service |
| Allowed destination | Logs, monitoring channels, support tooling and incident records (target tooling unresolved) |
| Present storage behaviour | Local health boundary and tax-rule drift monitor exist; SQLite logs IP as a short SHA-256 hash, never raw IP |
| Unresolved target storage/retention/deletion | No evidenced target monitoring, alert routing, service-level ownership or log retention schedule |
| Existing control | `tax_rule_monitor.py` and a local health boundary; `database.py` hashes IP addresses |
| Threat/failure mode | Logging/exfiltration; privilege escalation; availability/provider outage; evidence tampering |
| Current fail-closed state | Tax-rule monitoring is not general operational monitoring; no alert is routed to a named owner |
| Exact closure evidence | Target health/security/provider/tax-rule alerts reach named owners; false-positive, missed-heartbeat and sensitive-data tests pass |
| Canonical blocker/reference | `MON-01`, `OUTAGE-01`, `INC-01`; `reserved_west/release_gate.py` `operational_readiness` |

### FLOW-11 — Account erasure, retention, raw-document deletion, backup expiry and restore boundaries

| Attribute | Record |
| --- | --- |
| Data class | Customer identity, provider/evidence records, raw documents, backups |
| Subject/owner | Customer and backup/custody owners |
| Source | Account-deletion request and backup/restore tooling |
| Trust boundary crossed | Primary data ↔ backups/restore; application ↔ database/persistence |
| Processing purpose | Erase account data, apply retention/supersession, expire backups, and restore when required |
| Allowed destination | Cross-store erasure and backup/restore tooling (unresolved) |
| Present storage behaviour | Feature-level owner deletion and HICBC deletion hooks exist; no whole-account erasure; backups/restore are not evidenced |
| Unresolved target storage/retention/deletion | Field inventory, lawful purpose, retention periods, supersession, legal-hold, backup expiry and deletion evidence are unresolved |
| Existing control | Founder Decisions establish minimisation and deletion principles; `database.py` uses FK cascades in places |
| Threat/failure mode | Retention/deletion failure; backup/restore leakage; cross-owner/tenant leakage |
| Current fail-closed state | No durable annual-position or raw-document payload is stored, so erasure surface is currently bounded |
| Exact closure evidence | Approved retention/erasure schedule, backup expiry, whole-account erasure and raw-document deletion evidence |
| Canonical blocker/reference | `DATA-01`, `DATA-02`, `DATA-03`, `AUTH-03`; `reserved_west/release_gate.py` `hicbc_manual_privacy_retention_legal` |

### FLOW-12 — Target-runtime, operational-owner and release/activation boundaries

| Attribute | Record |
| --- | --- |
| Data class | Target runtime identity/configuration, operational ownership, release/activation authority |
| Subject/owner | Founder and operational owners |
| Source | Target deployment and release gate |
| Trust boundary crossed | Local/synthetic evidence ↔ target/provider/production acceptance |
| Processing purpose | Repeat the suite in the intended runtime and gate merge/release/go-live |
| Allowed destination | Target runtime and Founder authorisation record |
| Present storage behaviour | Local and synthetic test evidence exists; readiness documents preserve missing evidence as blockers |
| Unresolved target storage/retention/deletion | Target runtime, deployment isolation, monitoring ownership and release acceptance are unresolved |
| Existing control | `reserved_west/release_gate.py` preserves the 16-blocker October inventory and rejects non-canonical inventories |
| Threat/failure mode | Unsafe activation; supply-chain/runtime compromise; privilege escalation; availability outage |
| Current fail-closed state | A green local suite does not authorise merge/release/go-live; production/provider activation is a Founder gate |
| Exact closure evidence | Immutable target identity, complete required suite, failure paths, browser journeys and Founder authorisation |
| Canonical blocker/reference | `ACT-01`, `ACT-02`, `ACT-03`, `RUNTIME-01`, `RELEASE-01`; `reserved_west/release_gate.py` |

## Mandatory trust boundaries

### TB-01 — Browser/customer device ↔ Reserved application

The customer browser submits inputs and receives presentation. Protected by the
signed `rsvd_session` cookie (HttpOnly/SameSite=Lax/Secure), no-store headers on
sensitive responses, and the permissive CSP baseline documented in
`reserved/__init__.py`. Google/Apple journeys and CSP tightening remain open
(`AUTH-01`, `AUTH-02`).

### TB-02 — Identity provider/broker ↔ Reserved

Reserved verifies the Clerk session token against Clerk's JWKS and validates
`iss`, `azp`, `sub`, `sid` and optional `aud` before issuing its own session
(`reserved/auth.py`). Fails closed without a permitted origin.

### TB-03 — Application ↔ database/persistence

SQLite accessed through a module-level repository with foreign keys and WAL.
Annual-position and source-evidence persistence is intentionally non-durable
until the lifecycle design is approved (`PERSIST-01`, `PERSIST-02`, `DATA-01`).

### TB-04 — Application ↔ unresolved secret/token custody boundary

OAuth contracts stop at an abstract `TokenStore` boundary; only opaque
`CredentialReference` values may appear elsewhere. No encrypted store or key
custody exists (`CUST-01`, `CUST-02`).

### TB-05 — Application ↔ accounting providers

Network-inert, injected HTTPS origins via `http_boundary.py`; providers are
placeholders with `implementation_enabled=False`. Exact origin confinement and
sandbox execution are external evidence.

### TB-06 — Application ↔ HMRC

No HTTP/OAuth adapter exists; contract evidence is network-inert. HMRC is
`externally_blocked` in the release gate.

### TB-07 — Application ↔ Yapily/banks

AIS read-only flow separated from payment initiation. Live methods raise
`NotImplementedError`; `TrackOnlyProvider` cannot move money. `yapily_ais` and
`yapily_pis` are `externally_blocked`.

### TB-08 — Application ↔ unresolved billing provider

Provider-neutral W10 boundary only; no provider is selected. Stripe is an
explicitly non-selected placeholder. All subordinate billing policy is
unresolved (`FD-W10-001`, decision dossier `W9-DEC-11`).

### TB-09 — Runtime ↔ logs/monitoring/support operators

Local health and tax-rule drift checks exist; target monitoring, alert routing
and named owners are unresolved (`MON-01`, `INC-01`).

### TB-10 — Primary data ↔ backups/restore

Transactional rollback and Git revertibility exist, but recoverable backups and
restoration are not evidenced (`REC-01`, `DATA-03`).

### TB-11 — Local/synthetic evidence ↔ target/provider/production acceptance

Local/synthetic evidence does not prove target operation. Production/provider
activation and merge/release/go-live remain separate Founder gates (`ACT-02`,
`ACT-03`, `RELEASE-01`, `RUNTIME-01`).

## Mandatory threat classes

### TH-01 — Spoofing and broken authorisation

Mitigation: `reserved/auth.py` broker-token verification and the `require_auth`
session check; ownership is enforced through `user_id` FK joins in
`database.py`. Missing: target Google/Apple and provider authorisation evidence
(`AUTH-01`).

### TH-02 — CSRF/OAuth replay

Mitigation: hashed, provider-bound, expiring, single-use `OAuthStateStore`;
`validate_callback` consumes state before exposing a code; codes are single-use.

### TH-03 — Callback/order manipulation

Mitigation: `oauth_contracts.py` enforces callback ordering and single-use
codes; `readiness.py` validates callback URIs and rejects hostile values
without echoing them.

### TH-04 — SSRF or destination substitution

Mitigation: `http_boundary.py` `EndpointPolicy` validates exact non-live HTTPS
origins; `GuardedTransport` rejects URLs outside the approved origin set.

### TH-05 — Injection/schema drift

Mitigation: `schema_evidence.py` quarantines required-field loss/type drift;
`sync_contracts.py` enforces termination and duplicate detection. Missing:
target provider schema execution (`OUTAGE-01`).

### TH-06 — Stale data and false certainty

Mitigation: annual-position non-persistence and `INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md`
reject the `tax_calculations` stub; provenance/uncertainty remain ephemeral.

### TH-07 — Credential/token exposure

Mitigation: `OAuthTokenSet`/`ValidatedAuthorizationCode` redacted `repr`;
`CredentialReference` only; `readiness.py` never returns/logs secret values.
Missing: encrypted store and key custody (`CUST-01`, `CUST-02`).

### TH-08 — Cross-owner/tenant leakage

Mitigation: `database.py` enforces ownership through FK joins and no
client-supplied ID trust; missing whole-account erasure (`DATA-02`, `AUTH-03`).

### TH-09 — Webhook/replay/idempotency errors

Mitigation: none deployed; W10 and Yapily webhook/idempotency contracts are
unresolved (`W9-DEC-11`, `YAPILY_COMPLETION_MAP.md`).

### TH-10 — Evidence tampering

Mitigation: redacted import/schema evidence and strict snapshot codec reject
weakened prohibitions; missing immutable audit history (`PERSIST-02`).

### TH-11 — Logging/exfiltration

Mitigation: `http_boundary.redacted_summary` strips sensitive headers/bodies;
IP hashing in `database.py`. Missing: runtime log redaction and retention.

### TH-12 — Retention/deletion failure

Mitigation: `secure_deletion_required` disposition without claiming deletion.
Missing: deletion executor and retention schedule (`PAYSLIP-01`, `DATA-01`).

### TH-13 — Backup/restore leakage

Mitigation: none deployed; backups/restore are unresolved (`REC-01`, `DATA-03`).

### TH-14 — Availability/provider outage

Mitigation: bounded fail-close in provider contracts. Missing: outage exercise
and degraded-customer tests (`OUTAGE-01`).

### TH-15 — Privilege escalation

Mitigation: `require_auth` decorator and `is_production_environment()` dual-lock
gate demo login; missing target operational RBAC and ownership (`INC-01`).

### TH-16 — Supply-chain/runtime compromise

Mitigation: ClerkJS pinned to `6.25.12`; missing target runtime isolation and
dependency-review evidence (`RUNTIME-01`).

### TH-17 — Payment/cash misdirection

Mitigation: `TrackOnlyProvider` rejects non-track-only instructions; Stripe is a
disabled placeholder; Yapily AIS is separated from PIS.

### TH-18 — Unsafe activation

Mitigation: fail-closed `readiness.py`/identity readiness and the canonical
release gate preserve blockers; configuration alone cannot activate a provider.

## Non-activation and non-duplication statement

This package does not activate a provider, permit credentials, prove target
operation, close W9, declare launch readiness, or authorise
merge/release/go-live. It does not amend Founder Decisions, the W9 completion
map, the gap register, or the canonical release gate. Implemented, integrated,
externally evidenced and launch-ready remain distinct states and are not
conflated here.
