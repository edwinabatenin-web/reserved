# W9-S4A — provider outage and safe-degradation contract

## Scope and status

This package closes only the local contract portion of W9 `OUTAGE-01`: the
provider-neutral, network-inert classification of one evidence route during an
outage or safe-degradation event. It does not claim target monitoring, provider
sandbox evidence, customer UX acceptance, production readiness, or W9
completion.

- Authoritative context: `FOUNDER_DECISIONS.md` (external integration
  resilience, freshness/completeness, customer reassurance, October launch
  scope), `docs/W9_COMPLETION_MAP.md`,
  `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md`.
- Writable paths (only): this document,
  `reserved/providers/operational_resilience.py`,
  `tests/test_provider_operational_resilience.py`.

## Compatibility-consumer enumeration (inspected before coding)

Inspected as consumers, not edited:

- `reserved/providers/readiness.py` and `tests/test_provider_readiness.py` —
  fail-closed configuration checks; reused the frozen-dataclass + `str, Enum`
  style and the fail-closed `ValueError` convention.
- `reserved/providers/http_boundary.py` and `tests/test_provider_http_boundary.py` —
  provider-neutral, network-inert HTTP boundary; reused the "validates inputs,
  never performs network" boundary and `ValueError` error style.
- `reserved/providers/import_evidence.py` and `tests/test_import_evidence.py` —
  provenance/completeness value objects; reused the bounded non-secret
  reference format (`^[A-Za-z0-9._:-]{1,160}$`) and timezone-aware timestamp
  validation.
- `reserved/providers/schema_evidence.py` and `tests/test_schema_evidence.py` —
  schema-drift quarantine; reused immutable value objects and derived `may_*`
  properties.
- `reserved/providers/accounting/contracts.py` and
  `reserved/providers/accounting/sync_contracts.py` — canonical accounting
  identity/provenance and sync contracts; confirmed provider identity and
  provenance are already modelled there and are not duplicated here.
- `reserved/providers/accounting/freeagent_resilience.py` and
  `tests/test_freeagent_resilience.py` — existing state-transition contract;
  reused the `transition`-style fail-closed classification and the explicit
  "no network/credential/storage side effect" docstring discipline.
- `reserved/providers/identity/readiness.py` and `tests/test_identity_readiness.py` —
  identity readiness; confirmed fail-closed readiness is a separate concern.
- `reserved/providers/accounting/quickbooks_observation_contract.py` — bounded,
  redacted evidence representation; reused redacted-`repr` discipline.

Naming/type conventions reused: `str, Enum` for controlled vocabularies;
`@dataclass(frozen=True)` value objects with `__post_init__` validation; a
module-level `*Error(ValueError)`; derived boolean/property accessors;
`evidence_summary()` returning a safe one-way dict.

Why no existing product/shared file requires a mechanical update: the new module
is additive and imports nothing from the inspected contracts. No existing
readiness, HTTP-boundary, evidence, adapter, route, template, configuration or
test file references `operational_resilience`. No provider enumeration, registry,
release gate or activation path needs to be modified to consume it, and none is
edited.

## Implemented state and transition semantics

`reserved/providers/operational_resilience.py` defines:

- `OperationalState` — `available`, `temporarily_unavailable`,
  `authorisation_required`, `schema_incompatible`, `evidence_inadequate`,
  `stale`, `recovery_pending`.
- `OutageEvent` — bounded provider-neutral outage causes mapped to degraded
  states (`timeout`, `temporarily_unavailable`, `authorisation_expired`,
  `authorisation_revoked`, `schema_incompatible`, `required_fields_missing`,
  `required_fields_invalid`, `evidence_stale`).
- `EvidenceRouteIdentity(provider, route, owner_scope=None)` — bounded non-secret
  identity; hostile/malformed values are rejected without echo.
- `EvidenceRouteStatus` — immutable result carrying identity, state,
  `observed_at`/`retrieved_at`/`last_verified_at` (aware, UTC-normalised) and
  `last_transition_at`/`last_accepted_observed_at`/
  `required_fields_validated`. Derived facts:
  `may_use_as_current`, `may_show_stale_context`, `customer_action`,
  `customer_message_key`. Its validated deep state is integrity-bound so direct
  frozen-object mutation cannot manufacture a current result or safe summary.
- `RecoveryObservation` — a fresh observation (identity + observed/retrieved
  timestamps) offered for recovery.

Transitions:

- `classify_outage(identity, event, occurred_at, prior=None)` — degrades one
  route. It retains the latest outage/transition watermark. A late/repeated
  event (`occurred_at <= max(prior.last_verified_at,
  prior.last_transition_at, prior.retrieved_at)`) fails closed and cannot
  overwrite a newer verified, degraded or authentic pending-recovery state.
  `evidence_stale` requires a prior verified observation and retains its
  timestamps as stale context.
- `begin_recovery(current, observation, now=None)` — receives a fresh
  observation for exactly the same route, rejects future or non-newer
  observations, and returns `recovery_pending`. The pending value is bound to
  the validated source status and observation; a manually forged or subsequently
  mutated pending value cannot be completed or summarised. It never returns
  `available`. Recovery may begin only from a validated degraded state, and a
  newly retrieved observation whose source fact is older than or equal to the
  last accepted source fact is rejected.
- `complete_recovery(pending, required_fields_validated, schema_compatible,
  verified_at, now=None)` — verifies a pending recovery. Only a compatible
  schema and validated required fields restore `available`; otherwise the route
  degrades to `schema_incompatible` or `evidence_inadequate`. Both successful
  and failed decisions advance the route transition watermark.

`available` requires a validated observation with complete, ordered provenance
timestamps. No function takes a bare state label and produces `available`.

## Fail-close and anti-stale invariants (proven by tests)

1. Timeout, revocation, schema incompatibility, missing/invalid required fields
   and stale evidence are never `may_use_as_current`.
2. A provider failure is local to its route; different routes/owners stay
   independent, and cross-provider/cross-owner recovery substitution fails
   closed.
3. Last-known evidence is never silently promoted to current; `stale` is
   contextual only and cannot be completed into `available`.
4. Recovery to `available` requires a fresh observation with non-future,
   non-regressive observed/retrieved times plus validated required fields and a
   compatible schema; a fresh retrieval cannot rehabilitate an older or equal
   source observation, and a status flag alone cannot recover.
5. Repeated/late outage events cannot overwrite a newer verified or degraded
   state; the latest outage/transition watermark is retained independently of
   the prior verification watermark.
6. Cross-provider and cross-owner substitution fails closed.
7. Unknown enum/state, naive or wrong-type timestamps, missing/extra fields,
   subclasses and hostile strings fail closed; raw hostile values are not
   echoed through exceptions or `repr`.
8. Construction, `dataclasses.replace`, `copy`/`deepcopy`, equality/hashing and
   `evidence_summary` cannot bypass invariants. Direct `object.__setattr__`
   mutation of a route, observation or status is detected by deep revalidation
   and integrity bindings before recovery completion or summarisation. Pickling
   is explicitly rejected (`__reduce__` raises) because no consumer requires a
   wire format.
9. Recovery authority is part of equality/hash identity: an authentic pending
   transition and an otherwise field-identical unbound value are not equal and
   do not hash as the same capability.
10. The module performs no network call, credential access, token handling,
   persistence, customer-record read or activation path; the test asserts the
   source imports none of the relevant I/O surfaces.

## Verification run

- New focused module:
  `python3 -m pytest tests/test_provider_operational_resilience.py -p no:cacheprovider -q` —
  45 tests pass.
- Affected provider/readiness/HTTP/evidence matrix (unchanged, re-run only):
  `tests/test_provider_readiness.py`, `tests/test_provider_http_boundary.py`,
  `tests/test_schema_evidence.py`, `tests/test_import_evidence.py`,
  `tests/test_evidence_uncertainty.py`, `tests/test_quickbooks_sync_evidence.py`,
  `tests/test_quickbooks_qs5_provider_facts.py`, `tests/test_identity_readiness.py`,
  `tests/test_freeagent_resilience.py` — 322 tests pass including the focused
  module.

## Residual W9-S4 target/external evidence still required

This local contract does not close `OUTAGE-01` or W9-S4. Still required:

- Injected outage/timeout/revocation/schema-drift exercises in the intended
  provider sandbox, with redacted evidence.
- Customer-visible degradation, refresh/reconnect/manual-evidence UX
  acceptance.
- Target monitoring, alert routing, service-level ownership, retry/backoff
  scheduling and production runbooks.
- Recoverable backups/restore, rollback, incident/security response and
  customer-support escalation ownership.
- Named tax-rule, provider/API and security owners and their acceptance.

No network, credential, provider activation, staging, commit, push or
deployment was performed for this package.
