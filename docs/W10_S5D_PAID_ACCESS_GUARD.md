# W10-S5D paid-access guard kernel

## Status and scope

This package supplies a pure, provider-neutral, route-less paid-access decision
kernel for the exact W10-S2F/S5A paid boundary. It covers 26 paid endpoints in
the accepted S5A class
`authenticated_product_candidate_pending_founder_decision` and produces a
deterministic allow/deny candidate for one endpoint, authenticated owner,
runtime-entitlement value and exact UTC evaluation instant.

This is implementation evidence only. It does not wire any route, authenticate
a customer, read a session, issue or mutate entitlement, contact Stripe or any
other provider, read or write a database, persist a decision, activate billing,
or create production/launch authority. It does not complete W10-S3 or W10-S5.

Source identity:

The source checkpoints below remain historical S5D provenance. The later
HICBC annual-source candidate at base `5d91ae0c83bf696cb650d90daa8d25417e466157`
adds only the new endpoint's classification and matching inventory tests; it
does not claim to wire this kernel into that endpoint. Original source-history
assertions are preserved, and the exact candidate path allowance applies only
to the named dirty implementation branch/base, not clean descendants.

- base commit: `6f3cb30d1bedcebe930084d56c64ab83ff719d5a`;
- base tree: `ef36688a8bd07a58b98aa54412cd14b1d7c7d86c`;
- owned paths: this document, `reserved/billing/paid_access_guard.py`, and
  `tests/test_w10_paid_access_guard.py`.

The correction is bound to `FD-W10-004` as accepted in source checkpoint
`ab4f8d4d34aa4b80022018b2b15315d5ff72ebb5` and integrated at
`22512f29ed17dbc9a13a8741891345eb54513d05`. Those identities are evidence
references only: this frozen candidate remains based on `6f3cb30...` and has not
been rebased or broadened.

## Boundary

The exact paid set is:

1. `v2.index`
2. `v2.connections`
3. `v2.dashboard_view`
4. `v2.invoices`
5. `v2.invoices_seed`
6. `v2.optimise_view`
7. `v2.optimise_calculate`
8. `v2.optimise_save_scenario`
9. `v2.optimise_delete_scenario`
10. `v2.review_queue`
11. `v2.settings_page`
12. `v2.transactions`
13. `v2.transactions_seed`
14. `v2.yapily_callback`
15. `v2.yapily_connect`
16. `v2.yapily_disconnect`
17. `v2.yapily_refresh`
18. `hicbc.index`
19. `hicbc.delete_estimate`
20. `hicbc.save_estimate`
21. `hicbc.link_page`
22. `hicbc.link_accept`
23. `hicbc.link_invite`
24. `hicbc.link_revoke`
25. `hicbc.result_json`
26. `hicbc.annual_preview` — independently gated non-production manual source;
    classification only, not runtime entitlement enforcement.

The public/auth/legal/support class, billing purchase/return/recovery class and
the separately reconciled internal/admin/closed class are deliberately absent.
The guard returns a denial for them; that denial is not a claim that these
surfaces should themselves be wired through this paid guard.

## Explicit runtime-authority seam

No authoritative runtime entitlement adapter exists in the current source
line. W10-S3A produces only detached structural candidates with
`runtime_access_authority=False`. Detached S3A candidates cannot grant access.

`bind_paid_access_guard` therefore requires two distinct exact functions from a
future trusted composition root:

- a validator that admits the supplied live runtime-entitlement object and
  returns its exact canonical projection; and
- a projector that independently returns the same exact canonical projection.

The guard captures this pair into an opaque, binder-issued, non-copyable and
non-serialisable handle. For every evaluation it requires validator/projector
agreement and checks that neither captured dependency changed. A malicious or
defective validator alone cannot override a contradictory projection, and a
malicious or defective projector alone cannot override validation. If either
fails or their outputs differ, access is denied.

The callable pair is an explicit dependency boundary, not an implementation of
the future adapter and not a claim that whoever calls the binder is an
authoritative composition root. Route integration must bind only an independently
reviewed live adapter and must re-establish that adapter's own issuer integrity,
provider reconciliation and owner authentication guarantees.

## Exact provisional runtime-decision protocol

The provisional runtime-decision protocol is
`reserved-runtime-entitlement-decision/1.0`. Both functions must return the same
exact ordered tuple of exact key/value pairs:

1. `protocol_version`
2. `decision_identity`
3. `admission_status`
4. `authenticated`
5. `runtime_access_authority`
6. `owner_id`
7. `decision_sequence`
8. `predecessor_identity`
9. `state`
10. `ordinary_access`
11. `valid_from_inclusive`
12. `valid_until_exclusive`
13. `transition_effective_at_utc`
14. `recovery_deadline_exclusive_at_utc`
15. `predecessor_entitled_access`
16. `predecessor_owner_id`
17. `derivation_kind`
18. `withdrawal_attribution`

There may be no missing, extra, duplicate or reordered fields. The identity is
the SHA-256 of the exact canonical non-identity fields using the documented
compact JSON ordering and `runtime-entitlement:sha256-<lowercase hex>` form.
The guard recomputes it. This unkeyed identity detects inconsistency; it is not
authenticity. Authenticity and admission must come from the bound validator.

Every non-initial decision must bind the prior derived-entitlement identity and
advance its exact positive sequence by one. This makes the prior/current
boundary explicit and causes mismatched predecessor or out-of-order transitions
to fail closed. A first decision must have sequence one and no predecessor.
The two predecessor-summary fields are identity-bound, authority-admitted facts
about only the immediate predecessor; when the predecessor carried ordinary
entitled access they must name that fact and the same owner exactly.

Every evaluated current decision requires:

- an exact paid endpoint;
- a syntactically valid authenticated owner reference;
- exact protocol version;
- exact `authoritative_runtime_entitlement_admitted` status;
- exact `authenticated=True`;
- exact `runtime_access_authority=True`;
- exact owner equality;
- an exact timezone-aware UTC `evaluated_at_utc` value;
- nondecreasing transition order
  (`prior.transition_effective_at_utc <= current.transition_effective_at_utc
  <= evaluated_at_utc`, or `current.transition_effective_at_utc <=
  evaluated_at_utc` for an initial decision);
- the UTC evaluation date within the half-open validity interval; and
- an exact recognised derivation kind and internally consistent withdrawal
  attribution.

Everything else denies. Missing, malformed, stale, not-yet-valid,
unauthenticated, cross-owner, suspended, no-entitlement and unknown states all
fail closed. Naive, non-UTC, string, Boolean and otherwise wrong-typed
evaluation values are rejected. Equal prior/current transition instants are
permitted because exact identity and sequence distinguish atomic transitions;
decreasing or future transitions are denied.

Day-granularity validity is evaluated consistently as
`valid_from_inclusive <= evaluated_at_utc.date() < valid_until_exclusive`.
Exact transition ordering is evaluated first, so a same-day transition is not
visible one microsecond before its UTC effective instant and is visible at that
instant if every other authority condition passes.

The first admitted `verified_renewal_failure` transition from `paid` to
`payment_recovery` must begin at the prior paid interval's exact exclusive end,
using a midnight UTC transition time, and must carry an exclusive recovery
deadline exactly seven calendar days later. Its derived access interval must end
at that exact UTC deadline. Short, long, shifted, non-midnight and repeated
failure extensions are rejected. These timestamps are authority-normalised
derived facts supplied by the future adapter; the kernel neither reads a clock
nor treats provider time as authority. The recovery interval starts at midnight
UTC, admits evaluation exactly at that start, remains available through the day
before its exclusive deadline, and is stale at the deadline itself.

## FD-W10-004 prior/current withdrawal boundary

The guard implements only the access consequence settled by `FD-W10-004`.

An authoritatively admitted verified full withdrawal suspends ordinary paid
access at the next evaluation only when it is attributable to the payment that
funds the current subscription period. The current derived decision must itself
be `suspended` with `ordinary_access=False`; a claimed full current-period
withdrawal that leaves access enabled is contradictory and denied.
`verified_full_withdrawal` with `not_applicable` attribution is also
contradictory and denied; only `other_period` or `unknown` may enter the
preserve-only branch when current-period attribution is absent.

Open, partial, ambiguous, contradictory or unresolved withdrawal evidence may
preserve only already-valid, non-expired, authenticated, owner-bound derived
access. Preservation requires the current interval to be a subset of the prior
interval and the current state to equal the prior state. It can never create,
restore, extend or prolong access. A full withdrawal attributed to another
period, or whose current-period attribution remains unknown, follows this same
preserve-only rule and cannot suspend solely on that evidence.

In short, unresolved withdrawal evidence must never create, restore, extend or prolong access.

Forged values are rejected by the bound admission functions. A pair whose
predecessor identity or sequence is duplicated, mismatched or out of order fails
the adjacency boundary. Expired prior access cannot be preserved.

After suspension, restoration is accepted only from a separately admitted:

- `verified_reinstatement`;
- `verified_reversal_success`; or
- `verified_replacement_payment`.

These represent admitted reinstatement, verified reversal success or verified replacement payment.

A provider status string, ordinary existing-access projection or routine renewal
label cannot restore suspended access. Verified initial payment, renewal payment
and the already-settled bounded payment-recovery transition remain explicit
non-withdrawal entitlement-establishing facts under their own admitted derived
decisions; they are not direct provider statuses.

This stateless kernel proves only the locally supplied pair's exact adjacency
and the suspension record's authority-bound immediate-predecessor summary. It
does not prove that the pair represents the globally latest durable state and
does not inspect the complete entitlement chain. Global replay, revocation,
staleness, competing-successor and durable ordering guarantees remain duties of
the future authoritative repository/adapter. Repeating evaluation of the same
internally consistent pair is normal and deterministic; it is not itself a
provider-event replay or a new entitlement transition.

## Output and consumer rule

`evaluate_paid_access` returns an opaque evaluator-issued, non-copyable and
non-serialisable decision handle. `validate_paid_access_decision` accepts only
a live handle issued by this evaluator and returns a fresh exact immutable tuple.
That projection names the endpoint, owner, runtime decision identity, state,
allow flag, reason and exact `evaluated_at_utc` instant, and always records:

- `provider_contacted=False`;
- `persisted=False`; and
- `route_wiring_active=False`.

The public evaluation call is explicit about its clock input:

```python
from datetime import datetime, timezone

decision = evaluate_paid_access(
    guard,
    endpoint="v2.index",
    authenticated_owner_id="users:17",
    prior_runtime_entitlement=prior_live_decision,
    current_runtime_entitlement=current_live_decision,
    evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
)
projection = validate_paid_access_decision(decision)
```

The caller supplies the evaluation instant; the kernel does not read wall-clock
time and does not accept a provider timestamp as evaluation authority.

Consumers must use `validate_paid_access_decision` and must obtain a fresh
decision for the current request. A fabricated handle and a customer-supplied,
deserialised or cached tuple are not accepted as access authority. The future
route package must also test direct URLs, every method/content type, API bypass,
cache invalidation, owner changes, revocation, concurrency and HICBC feature-gate
behaviour.

## Verification and limitations

The focused suite verifies the exact S5A membership, initial paid and bounded
payment-recovery access, missing/malformed/stale/cross-owner/suspended/unknown
denial, exact UTC transition/evaluation ordering, same-instant transition
adjacency, half-open validity-day boundaries, exact seven-calendar-day UTC
recovery, full-versus-partial withdrawal
attribution, preserve-only/no-create/no-extend behaviour, expiry, pair-local
adjacency rejection, origin-bound restoration, repeat evaluation, detached S3A
rejection, identity validation,
validator/projector disagreement, dependency mutation, output invariants,
handle forgery/copy/serialization resistance and absence of I/O/provider/route
imports.

Important remaining work and assurance:

- build and independently assure the authenticated, durable runtime-entitlement
  adapter and its validator/projector;
- reconcile the accepted `FD-W10-004` evidence into later W10 maps and live
  entitlement implementation without broadening this kernel;
- wire the accepted guard server-side to the exact routes in a separate package;
- prove current-owner authentication, cache/revocation/concurrency and direct
  URL/API coverage in the real request path;
- complete target, provider, security, privacy, operations, W8/W9/W10, release
  and go-live assurance.

No commit, integration, merge, push, release, deployment or activation is part
of this implementation candidate.
