# W9-S4C — multi-provider outage coordination evidence

## Scope and status

This package closes only the local, pure, network-inert portion of W9
`OUTAGE-01`: combining several already-validated `EvidenceRouteStatus` values
for one exact owner into one deterministic, customer-safe multi-route outage
result. It does **not** implement target monitors, alerts, incident owners,
backups, provider sandbox exercises or production operations. **W9-S4 remains
partial.**

- Authoritative context: `FOUNDER_DECISIONS.md` (external integration
  resilience, freshness/completeness, customer reassurance, October launch
  scope), `docs/W9_COMPLETION_MAP.md`,
  `docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md` (`OUTAGE-01`),
  `docs/W9_PROVIDER_OUTAGE_DEGRADATION_CONTRACT.md` (the single-route
  W9-S4A/B contract this package composes).
- Writable paths (only): this document,
  `reserved/services/provider_outage_coordination.py`,
  `tests/test_provider_outage_coordination.py`.

## Compatibility-consumer enumeration (inspected before coding, not edited)

- `reserved/providers/operational_resilience.py` and
  `tests/test_provider_operational_resilience.py` — the reviewed upstream
  single-route state/action/message contract. This package reuses its bounded
  vocabulary (`OperationalState`, `CustomerAction`, `CustomerMessage`) and its
  exact-type/integrity discipline; it imports only public names and does not
  weaken the upstream contract.
- `reserved/services/provider_outage_presentation.py` and
  `tests/test_provider_outage_presentation.py` — the existing owner-bound HTML
  projection. Reused its "bind collaborators at construction time" pattern and
  its equality-probe-safe structural validation. Not edited; its suite must
  remain green.
- `reserved/templates/v2/_provider_outage_status.html` — read-only; no change
  is required because this slice produces a safe result object, not HTML.

No existing product/shared file requires a mechanical update: the new module is
additive, imports nothing beyond the upstream contract, and is not referenced by
any readiness, adapter, route, template, configuration or activation path.

## Implemented semantics

`reserved/services/provider_outage_coordination.py` defines one public
operation:

- `coordinate_provider_outage(*, routes, owner, as_of=None)` — accepts an exact
  immutable tuple of exact `EvidenceRouteStatus` values, one exact owner
  reference, and an optional timezone-aware coordination-time boundary
  `as_of` (defaulting to the current UTC instant, matching the upstream
  `now` convention). It returns either an immutable
  `ProviderOutageCoordination` result or the categorical value-free singleton
  `ProviderOutageCoordinationRefusal`.

The result is issued only by the bound coordinator. Issuance is a process-local
producer-held registry keyed to the exact live object and held outside the
consumer-writable dictionary, so field transfer or re-initialisation can never
acquire validity. The result carries an exact, order-independent per-route
status/provenance digest (including, for `recovery_pending`, the validated
source status and observation provenance). Directly constructed, reconstructed,
copied or subsequently modified values fail closed on every public surface.

The result exposes only `customer_projection()`, which returns exactly three
bounded-vocabulary fields:

- `aggregate_state` — the documented precedence-winning `OperationalState`
  value.
- `customer_message_key` — the corresponding `CustomerMessage` value.
- `customer_actions` — the exact distinct set of non-`NONE` `CustomerAction`
  values in canonical order (empty when no customer action applies).

### Deterministic aggregate precedence

`AVAILABLE` is last in precedence, so a single degraded, stale or
recovery-pending route is never masked by another available route:

1. `temporarily_unavailable`
2. `authorisation_required`
3. `schema_incompatible`
4. `evidence_inadequate`
5. `stale`
6. `recovery_pending`
7. `available`

The aggregate state is the first state present among the accepted routes. The
aggregate message is the upstream message key for that state. The aggregate
action set preserves every distinct applicable customer action rather than
selecting an arbitrary one.

This layer claims **exact route-status coordination only**: the private digest
records each `(provider, route, owner_scope)` together with its exact validated
state and provenance (including, for `recovery_pending`, the validated source
status and observation), so two coordinations are distinguishable even when
their customer-visible aggregate is identical. It does **not** claim
cross-provider
source-evidence non-reuse, because the upstream `EvidenceRouteStatus` carries no
source-evidence identity or content digest; whether two routes reused the same
underlying source evidence is not verifiable here and remains an upstream-owned
property.

### Integrity and refusal

The operation refuses (returns the same value-free singleton) when any of the
following is true:

- the owner reference is not an exact bounded identifier string;
- the routes argument is not an exact non-empty tuple;
- any route is a subtype, incomplete or mutated upstream object;
- any identity is a subtype or its binding does not exactly match its fields;
- any route's `owner_scope` does not exactly equal the requested owner;
- any route's state/binding is not exactly intact (including an authentic
  two-step recovery binding for `recovery_pending`);
- any `(provider, route)` identity is duplicated;
- the coordination `as_of` is not an exact timezone-aware datetime;
- any route's `observed_at`, `retrieved_at`, `last_verified_at`,
  `last_transition_at` or `last_accepted_observed_at` timestamp is later than
  the coordination `as_of` boundary.

`recovery_pending` is kept non-current: it can only become `available` after the
existing upstream two-step authority (`begin_recovery` then `complete_recovery`)
has validly produced an available status. The coordination operation itself
never performs recovery.

Security-critical collaborators — the upstream status/identity/state/message/
action/error types, the message/action/precedence mappings, the timezone source,
the weak-reference constructor and the structural validators — are captured at import time, so ordinary
module/helper rebinding cannot alter validation, equality/hash/copy or
projection. Message/action/precedence collaborators are additionally snapshotted
into immutable closure-bound views so later in-place mutation of the
module-global mappings cannot alter accepted semantics. The result carries a
process-local, coordinator-only, producer-held issuance registry keyed to the
exact live object and held outside the consumer-writable dictionary; values
constructed, reconstructed or re-initialised outside the coordinator fail closed
on every public surface. Necessary internal provenance (exact per-route status
plus recovery source/observation provenance) is retained only in a private
digest; it is never serialised into the customer projection or `repr`, which
expose only bounded vocabulary.

## Fail-close invariants (proven by tests)

1. One available route never masks a degraded, stale or recovery-pending route.
2. Mixed available + timeout/revocation/schema/inadequate-evidence/stale/
   recovery-pending each resolve to the documented non-available aggregate.
3. Multiple distinct degraded states use documented precedence and preserve the
   exact distinct action set.
4. A failed route is never hidden by other available routes.
5. `recovery_pending` stays non-current and becomes available only after
   `complete_recovery` has validly returned available.
6. Ordering and result identity are stable for the same route set in any input
   order.
7. Exact owner isolation, empty input, duplicate `(provider, route)` and
   cross-owner/cross-route/identical-payload source substitution are refused.
8. Swapping route outcomes yields distinguishable exact per-route
   status/provenance identities even when the customer-visible aggregate is
   unchanged.
9. Direct construction, reconstruction, copy/deepcopy/pickle and subsequent
   mutation of a result fail closed without attacker hooks.
10. Subtype, incomplete, equality/hash/repr, foreign-value equality and ordinary
    rebinding probes fail closed without attacker hooks.
11. In-place mutation of the module-global message/action mappings after binding
    cannot alter accepted semantics.
12. No identifier, provider/route payload, timestamp, secret, URL or unbounded
    text reaches the customer-safe result, `repr` or serialization boundary.
13. Route observation/retrieval/verification/transition timestamps later than the
    coordination `as_of` boundary are refused; a non-timezone-aware `as_of` is
    refused.
14. The module performs no request-time filesystem, network, provider, retry,
    reconnect, monitoring, scheduling, persistence, logging or other I/O.

## Verification run

- New focused suite:
  `python3 -m pytest tests/test_provider_outage_coordination.py -q` — 48 tests
  pass.
- Existing upstream single-route and presentation suites (unchanged, re-run):
  `tests/test_provider_operational_resilience.py`,
  `tests/test_provider_outage_presentation.py` — all pass.

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
- A future upstream source-evidence contract change: the upstream
  `EvidenceRouteStatus` carries no source-evidence identity/content digest, so
  this layer verifies exact route-status coordination but cannot (and does not)
  claim cross-provider source-evidence non-reuse. Adding that claim would require
  a separate upstream source-evidence digest, out of scope for W9-S4C.

No network, credential, provider activation, staging, commit, push or
deployment was performed for this package.
