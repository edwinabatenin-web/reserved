# Provider-boundary adoption path

**Prepared:** 13 August 2026  
**Scope:** integration infrastructure only; no provider capability claim

## Current position

- `readiness.py` prevents configured connectors from operating unless a
  non-live environment and safe callback URI are explicit.
- `oauth_security.py` supplies hashed, provider-bound, expiring, single-use
  anti-forgery state.
- `oauth_contracts.py` validates callback ordering and confines raw token sets
  to a server-side token-store boundary.
- `http_boundary.py` validates exact non-live HTTPS origins before delegating
  requests to an injected transport and creates redacted evidence summaries.
- `accounting/sync_contracts.py` collects provider-translated `SyncPage`
  objects with explicit termination, loop/duplicate detection, monotonic source
  watermarks and a configured maximum page count.
- `import_evidence.py` records a payload-free, non-live import manifest. A
  `complete` verdict requires a terminal page, unique records and a provider
  total that matches; terminal pagination without an independently supplied
  source count remains explicitly `unverified`. A separate, predeclared
  `ImportPurpose` can classify that evidence as `sufficient_for_purpose` where
  the use genuinely needs terminal/unique records but not a provider total.
- `schema_evidence.py` records field names and coarse value kinds against a
  versioned adapter mapping without retaining source values. Missing or
  type-changed required fields quarantine a record. Unknown additive fields are
  retained for review but do not automatically block normalisation.
- FreeAgent, Xero and QuickBooks adapters remain deliberate placeholders.
- Yapily has fixture behaviour but no network implementation; its contracted
  authorisation journey still needs selection.
- No HMRC HTTP/OAuth adapter exists in this repository.
- All five provider specifications therefore have `implementation_enabled`
  set to false. Complete environment configuration reports
  `configured_not_implemented`, not `ready_for_sandbox_test`, and cannot enable
  network access. The flag may be changed only with the adapter, contract tests
  and sandbox execution evidence in the same deliberately reviewed change.

## Deliberate non-implementation: encrypted token store

No encrypted store has been added. Correct encryption at rest needs an approved
authenticated-encryption implementation, key generation and custody, key
versioning/rotation, backup/restore behaviour, access control, audit events and
a deployment-specific persistence decision. Home-grown encryption or a key
stored beside ciphertext would create a false security claim.

Before implementation, select one of these deployment-appropriate patterns:

1. managed secret/envelope encryption with a KMS-held key; or
2. database ciphertext produced by an approved AEAD library, with the master
   key held outside the database in the deployment secret/KMS facility.

Only opaque `CredentialReference` values may appear in user, sync, log and
analytics records. Plaintext tokens should exist only for the shortest possible
time inside exchange/refresh and authenticated HTTP request construction.

## Sequenced adoption

1. Select the deployment token-store and key-custody design; threat-model token
   theft, database disclosure, application compromise, rollback and key loss.
2. Implement `TokenStore.put`, atomic `replace` and `delete`; add synthetic
   encryption, wrong-key, tamper, rotation and backup/restore tests.
3. Implement one provider adapter from its selected current official contract.
   Keep provider endpoints and response parsing inside that adapter.
4. Construct an exact sandbox `EndpointPolicy`; wrap the adapter's injected
   HTTP client with `GuardedTransport`.
5. Issue OAuth state before redirect. At callback, call `validate_callback`
   before any exchange; call `exchange_and_store` and retain only its opaque
   reference.
6. Resolve tokens inside the adapter for API calls. Do not change public
   provider-neutral methods back to raw-token parameters.
7. For refresh, return a validated `OAuthTokenSet` from the adapter and call
   `refresh_and_rotate`. The store must atomically replace the complete pair;
   never delete the current reference before refresh succeeds.
8. Map provider errors to stable internal codes without storing raw callback
   descriptions or response bodies. Record only redacted sandbox evidence.
9. Translate only the provider's documented pagination mechanism into
   `SyncPage`, then use `collect_pages`; do not infer provider cursors or silently
   overwrite duplicate external identities.
10. Produce an `ImportManifest` for every sandbox resource/window. Where a
    provider contract supplies no total-count mechanism, retain the manifest's
    `unverified` completeness. Assess it against a predeclared purpose: it may
    be sufficient for a bounded display/import use, but remains unverified for
    count reconciliation. Contradictory counts or unterminated pagination are
    inadequate regardless of purpose.
11. Apply a versioned `SourceSchema` before normalisation. Quarantine required
    field loss/type drift. Review unknown additive fields proportionately; do
    not require a provider payload to remain byte-for-byte frozen.
12. Add contract tests with a synthetic transport, then execute the provider's
   sandbox pack. Only after that should a connector move from placeholder to
   sandbox-verified.
13. Set `implementation_enabled=True` only when the adapter is safe to execute
    in the explicit sandbox. Credential presence alone must never set the flag.

## Route adoption warning

Current `/v2/yapily/*` routes use bespoke session keys rather than
`OAuthStateStore`/`oauth_contracts`. They should be migrated only after the
Yapily flow is selected, because its Hosted Pages redirect contract must not be
mislabelled as generic OAuth or as a webhook. Accounting and HMRC routes do not
yet exist and should be built around these boundaries from the outset.

## Gate

Do not call a connector ready merely because credentials are present or a
redirect succeeds. The gate requires secure token custody, state/replay tests,
exact sandbox origin confinement, refresh rotation, ownership isolation,
pagination completeness, revocation/reconnect behaviour and redacted evidence.
