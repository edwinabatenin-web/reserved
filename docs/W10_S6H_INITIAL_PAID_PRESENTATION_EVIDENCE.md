# W10-S6H detached initial-paid presentation candidate

## Bounded outcome

This slice supplies one deterministic, recursively detached copy candidate for
the narrow post-reconciliation case in which caller-supplied structural facts
say both that a successful initial payment observation was reconciled and that
the canonical entitlement transition was observed in its paid state, the
current canonical posture still renews automatically and an exact next-renewal
boundary was independently supplied.

The fixed copy says that the subscription payment is verified, the paid
subscription has started, the selected plan is set to renew automatically at
the exact supplied paid-through-exclusive boundary, and a future payment is not
guaranteed to succeed. It also says that access remains subject to Reserved's
entitlement checks. It does not grant access, create a charge, authenticate or
admit the facts, promise renewal success, adjudicate cancellation or refund,
contact a provider, render/deliver copy, persist state or activate billing.

There is deliberately no path from a Checkout result, browser return or copied
provider status label to this candidate. The only accepted state is the exact
Reserved structural state `initial_payment_verified_paid`, accompanied by
exact-true reconciled-payment, paid-state and current automatic-renewal
structural confirmations. A canonical paid state with
`renews_automatically=false` is not eligible for automatic-renewal copy: that
includes the paid-through remainder after cancellation. Those inputs remain explicitly labelled
`unauthenticated_structural_facts_only`; they are not evidence admission.

## Exact source baseline

**Candidate base commit:** `2690c9335ca8073b1723846cccf33c15f9ff727f`

**Candidate base tree:** `c5ee5ef6cde1272288c6e60325747c6d9752b99c`

| Source | Last integrated checkpoint at the base | SHA-256 at the base | Bounded use |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | Exact `FD-W10-003` initial-access, renewal, recovery and cancellation boundary; no runtime authority |
| `reserved/billing/entitlement_core.py` | `48a97042fc0e17997bf2d23a4687e79c20b74b9e` | `201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415` | Hardened detached entitlement transition context; not imported and not admission or access authority here |
| `reserved/billing/checkout_intent_contract.py` | `23f4d3dc742474d3a672388a1ebe99962505b234` | `ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0` | Disabled-first Checkout boundary and its rule that Checkout/browser return cannot start access; not imported or runtime authority here |
| `reserved/billing/initial_payment_presentation.py` | `2690c9335ca8073b1723846cccf33c15f9ff727f` | `009970f3217bee7dddc59471f02ce801d8992e7d92b951f41a7ee97cc2bd5451` | S6G pending/failed copy boundary, whose states explicitly do not start paid access |

These source bindings document the exact design context used to construct the
candidate. They do not authenticate the caller, admit observations, establish
an entitlement transition or turn a structurally valid result into customer
delivery authority.

## Detached structural boundary

The builder accepts one exact ordered built-in dictionary and three
independently supplied expected references. The facts contain:

- an exact structural-facts version;
- owner, subscription and plan references;
- exact state `initial_payment_verified_paid`;
- exact-true `successful_payment_observation_reconciled`,
  `canonical_entitlement_state_observed` and `renews_automatically` structural
  booleans;
- exact canonical UTC seconds for payment verification, entitlement effect,
  paid-through-exclusive boundary, independently supplied next-renewal
  boundary and evaluation.

The references must be bounded exact strings, must not be secret-shaped or
provider-object-ID-shaped and must match the independently supplied expected
references. This is cross-context structural consistency only. It does not
authenticate an owner, subscription, plan, payment observation or entitlement.

The accepted timestamp order is:

`payment_verified_at_utc <= entitlement_effective_at_utc <= evaluated_at_utc < paid_through_exclusive_utc`

Evaluation must be less than 300 seconds after verification. Exactly 300
seconds is stale. The supplied paid-through-exclusive boundary must be strictly
future at evaluation. The module does not add a month, year or plan interval to
derive or extend that boundary; it copies and formats the exact supplied UTC
second after validation. For this narrow automatic-renewal candidate,
`next_renewal_at_utc` must independently be supplied and must exactly equal the
paid-through-exclusive boundary. A mismatch fails closed rather than choosing
or deriving one. The five-minute limit is only structural freshness
for this copy candidate, not a payment/provider timeout or an entitlement
period.

The output contains recursively exact built-in tuples, strings and booleans.
It may be independently reconstructed and validated without a registry,
identity capability or producer-held state. Structural references are separate
from copy and never interpolated into customer text. Supplied, expected and
reconstructed references are rejected when secret-shaped or shaped like known
provider object identifiers.

## Exact authority boundary

Every returned authority flag is exact `false`:

- upstream admission;
- authentication;
- customer rendering;
- delivery;
- notification;
- entitlement;
- access;
- provider;
- charge;
- refund;
- persistence; and
- activation.

The three exact-true structural confirmations are facts to be checked, not
authority flags. A future authenticated and independently admitted adapter
would still need to establish the canonical facts before using this detached
copy candidate, and a separate entitlement/access control remains authoritative
for runtime access.

## Copy and policy exclusions

The copy contains no amount or plan duration because this package does not
rederive catalogue authority. It does not invent VAT, invoice, tax, refund,
cancellation, retry, grace-period or provider mechanics. “Set to renew
automatically” describes the structurally observed selected-plan posture; the
adjacent fixed caveat expressly says that a future payment is not guaranteed to
succeed. Automatic renewal posture and the next-renewal boundary are
caller-supplied unauthenticated structural facts, not inferences from a paid
state, Checkout/browser return or provider label. The independently supplied
next-renewal UTC second is presented only after it exactly matches the supplied
paid-through-exclusive UTC second; no calendar arithmetic derives either.

## Fail-closed coverage

Focused hostile tests cover:

- exact dictionary, output, nested-pair, key and scalar types/order;
- recursively detached output and post-build input mutation;
- independent reconstruction without a registry or identity capability;
- cross-owner, cross-subscription and cross-plan mismatches;
- exact-true requirements for the reconciled-payment, canonical-paid-state and
  current automatic-renewal structural confirmations, rejecting bool/int
  confusion;
- explicit rejection of a paid-through canonical-paid subscription whose
  current posture has `renews_automatically=false`;
- Checkout, browser-return, provider, success, active, pending, failure,
  recovery and other injected state labels;
- extra provider status and reordered/extra facts;
- exact verified/effective/evaluated ordering;
- the start-inclusive, 300-second-exclusive freshness boundary;
- strictly future, exact paid-through-exclusive boundaries without arithmetic,
  plus exact equality with the independently supplied next-renewal boundary;
- malformed, non-canonical and non-exact timestamps;
- secret-shaped and provider-object-ID-shaped supplied, expected and
  reconstructed references;
- tampered classification, kind, fact status, timestamps, renewal posture,
  renewal-boundary equality, copy, confirmations and authority;
- no invented VAT, invoice, refund, provider or cancellation language; and
- absence of I/O, network, clock, runtime adapter, mutable registry or identity
  capability.

## Explicit open gates

This package does not provide or prove provider authenticity, webhook/event
admission, owner authentication, the successful payment observation, the
canonical entitlement transition, durable storage, a live access decision,
customer rendering/delivery/notification, Checkout or Customer Portal access,
charge/refund/cancellation handling, provider sandbox evidence, production
credentials, activation, integrated journey assurance, release or go-live.

It does not itself close W10 Q1, Q2 or Q3, complete W10-S6, close W7A/W8/W9 or
satisfy provider, finance/tax, legal, privacy, security, accessibility,
target-runtime, activation or launch evidence.

## Candidate ownership

Only these new paths are authorised:

- `reserved/billing/initial_paid_presentation.py`
- `tests/test_w10_initial_paid_presentation.py`
- `docs/W10_S6H_INITIAL_PAID_PRESENTATION_EVIDENCE.md`

The candidate stops uncommitted for fresh independent review.
