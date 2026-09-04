# W10-S6F detached cancellation/end-of-paid-period copy candidate

## Bounded outcome

This slice validates exact, untrusted structural facts describing a cancellation
already verified elsewhere and produces fixed, recursively detached customer
copy. The copy says that future automatic renewal is stopped, that the current
already-paid period ends at an exact UTC-second boundary, and that use before
that boundary remains subject to Reserved's entitlement checks. It explicitly
does **not** promise or grant access at or after the exclusive boundary.

The result is a detached zero-authority (zero authority) copy candidate. It is not upstream
admission, not live customer presentation, and not evidence that the owner,
subscription, provider event, cancellation or paid-through period is authentic.

## Exact authority and source baseline

**Candidate base:** `109b5ec6e3ace82d8e41c98ece1baf7553eff039`

**Candidate base tree:** `9d0588c3d6761c21724b27fcc6ff412e6447f285`

| Source | Accepted source / integration identity | SHA-256 at the base | Bounded use |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | FD-W10-003 cancellation, paid-period and mandatory-rights policy only |
| `reserved/billing/entitlement_core.py` | source `b990d514a929c37b3f999137a0e383d05c37f0df`; integrated `48a97042fc0e17997bf2d23a4687e79c20b74b9e` | `201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415` | Separate detached lifecycle policy; sole owner of ordinary-access decisions |
| `reserved/billing/portal_intent_contract.py` | source `b197c987b96dd9fca6296c41bb002baf74099e55`; integrated `67b52a66805e9d5c1317330b9f7b1f2a19d4172c` | `f3f021bc05233cd5c4714c68e6eb57127f7722cc6685ea56e8c7a6e6de008d33` | Separate disabled Portal-intent boundary; never cancellation, refund or entitlement proof |

These hashes bind the reviewed design context. They do not authenticate the
caller-supplied facts or make either upstream structural contract a live source
of authority. This module deliberately does not import those sources.

## Exact detached input boundary

The builder accepts only an exact ordered built-in dictionary containing:

- the exact structural-facts schema version;
- owner, billing-account and subscription references;
- the sole state `cancellation_confirmed_end_of_paid_period`;
- exact `true` for the recorded fact that future renewal is stopped;
- paid-period start, cancellation-verification, paid-through-exclusive,
  cancellation-effective and evaluation timestamps.

All timestamps must be canonical UTC-second strings. Booleans, integers,
floats, naive/local timestamps, offsets, fractional seconds and subclasses are
not accepted as timestamps. Owner and subscription references must match exact
expected values supplied independently by the future consumer. References are
never copied into customer text.

The local consistency checks require:

- a non-empty paid period;
- cancellation verification during that paid period;
- the cancellation-effective boundary to equal the recorded
  paid-through-exclusive boundary exactly; and
- evaluation no earlier than verification and strictly before the exclusive
  paid-through boundary.

The supplied boundary is formatted exactly, including seconds. It is not
derived from a provider label, extended, rounded or converted into an access
decision. Unknown, reordered or additional fields fail closed.

## Boundary and entitlement semantics

`reserved/billing/entitlement_core.py` owns ordinary-access policy. This copy
candidate cannot independently decide access. Its text therefore says access
before the already-paid-period boundary remains **subject to Reserved's
entitlement checks**. At the exact exclusive end boundary, it states only that
the message does not promise or grant access and that entitlement policy makes
the decision.

This preserves the Founder policy that cancellation stops future renewal while
ordinary paid access continues through the already-paid period, without
silently converting a presentation object into an entitlement credential. The
fixed text also says that mandatory consumer and statutory rights are
unaffected. Those rights override the product policy where applicable; this
module does not interpret, waive or adjudicate them.

## Recursively detached zero-authority result

The output contains only exact recursively nested `tuple`, `str` and `bool`
values. It retains no caller object, identity token, registry, closure-based
admission entry or mutable per-result state. An independently reconstructed
equal value validates equally; that is intentional evidence that the value is
structure, not a capability.

Every authority flag is exact `false`:

- upstream admission;
- customer rendering;
- delivery;
- notification;
- entitlement;
- access decision;
- provider;
- cancellation;
- refund;
- persistence; and
- activation.

Provider labels have zero direct authority. A provider label such as active,
cancelled or cancel-at-period-end cannot satisfy this contract, choose an
owner, prove a paid-through boundary, grant access or authorise presentation.

## Fail-closed and hostile-input coverage

Focused tests cover exact field order and types, mapping/string/tuple
subclasses, bool-as-integer-shaped timestamp attempts, unknown fields, cross-
owner and cross-subscription use, malformed references, non-canonical and naive
timestamps, impossible orderings, mismatched effective and paid-through
boundaries, pre-verification and stale evaluation, unsupported state, altered
copy, altered classification/kind, non-false authority, retained-input
mutation, reconstructed values, secret/provider-ID leakage, upstream-export
substitution and absence of I/O, network, clock, importer or mutable-registry
effects.

These tests establish local structural behaviour only. They do not prove a
future authenticated adapter, provider event authenticity, persistence,
delivery or runtime isolation.

## Remaining activation and assurance gates

Live customer use still requires, at minimum:

- an authenticated owner-bound source of canonical subscription state;
- verified, deduplicated and durably reconciled provider events;
- exact linkage between owner, internal billing account and subscription;
- a reviewed target adapter that projects the canonical paid-through boundary;
- entitlement-core integration and enforcement at every paid surface;
- durable cancellation and event-ordering persistence;
- Stripe/provider account, product, price, tax, invoice and Portal
  configuration evidence;
- credential custody, webhook authenticity, replay and outage controls;
- reviewed rendering, accessibility, localisation and customer-support paths;
- legal/consumer-rights, cancellation, refund, VAT/tax and privacy confirmation;
- sandbox negative-path and target-runtime evidence; and
- separate provider activation, production, release and go-live authority.

This slice schedules or cancels nothing at Stripe, sends no provider request,
persists nothing, renders or delivers nothing, sends no notification, grants no
access, infers no refund and closes no W10 or W9 launch gate.

## Candidate ownership

Only these new paths are authorised:

- `reserved/billing/cancellation_presentation.py`
- `tests/test_w10_cancellation_presentation.py`
- `docs/W10_S6F_CANCELLATION_PRESENTATION_EVIDENCE.md`

The candidate stops uncommitted for fresh independent review.
