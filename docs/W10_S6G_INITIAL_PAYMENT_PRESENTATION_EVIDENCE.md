# W10-S6G detached initial-payment presentation candidates

## Bounded outcome

This slice supplies two deterministic, recursively detached copy candidates for
the period before Reserved has verified a successful initial subscription
payment:

- `initial_payment_pending` / `unverified`; and
- `initial_payment_failed` / `failed_verification`.

The pending copy says that the initial subscription payment is still being
verified and that paid access has not started. The failed copy says that the
initial subscription payment could not be verified and that paid access has not
started. The only next step in either state is generic support/help wording.
The failed state deliberately gives no retry direction because retry mechanics
are not settled by `FD-W10-003` and this package has no Checkout, provider,
charge or retry authority.

There is deliberately no paid, active, successful or confirmed state in this
contract. Under `FD-W10-003`, paid access may begin only after the separate
canonical entitlement core receives a verified, reconciled successful initial-
payment observation. A browser return, provider label or this copy candidate
cannot grant access.

## Exact source baseline

**Candidate base commit:** `fd7f30dcdc3557ef70c9bdfc4b89e046e16c2bd0`

**Candidate base tree:** `b2edd687819b5b0f95c44f1a68d746a85f7bd9c1`

| Source | Last integrated checkpoint at the base | SHA-256 at the base | Bounded use |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | Exact `FD-W10-003` rule that initial paid access begins only after Reserved verifies a successful reconciled initial-payment observation |
| `reserved/billing/entitlement_core.py` | `48a97042fc0e17997bf2d23a4687e79c20b74b9e` | `201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415` | Hardened detached entitlement transition context; not imported and not admission authority here |
| `reserved/billing/checkout_intent_contract.py` | `23f4d3dc742474d3a672388a1ebe99962505b234` | `ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0` | Disabled-first Checkout intent context and its explicit rule that Checkout/browser return does not start access; not imported or treated as runtime authority here |

These exact source bindings document the reviewed design context. They do not
authenticate caller-supplied facts or turn a structurally valid result into an
admitted customer message.

## Detached structural boundary

The builder accepts only one exact ordered built-in dictionary and three
independently supplied expected references. The facts contain:

- an exact structural-facts version;
- owner, subscription and plan references;
- exactly one of the two states above;
- an exact canonical observed UTC second; and
- an exact canonical evaluated UTC second.

All three supplied references must be bounded exact strings, must not be
secret-shaped or provider-object-ID-shaped, and must exactly match their
independently supplied expected values. This is cross-context structural
consistency only. It does not authenticate an owner, subscription, plan or
observation.

The evaluation must be no earlier than the observation and less than 300
seconds later. Five minutes is a conservative, fixed freshness window for a
copy candidate at this initial-payment boundary. It is not a provider timeout,
retry interval, entitlement period or evidence-retention policy. The module has
no clock: both timestamps are supplied and neither is inferred. At exactly 300
seconds the facts are stale and fail closed.

The output contains only recursively exact `tuple`, `str` and `bool` values.
Internal structural references are held in a separate fixed field and never
interpolated into the fixed copy. Known secret-shaped values and provider
object identifiers are rejected for both the supplied and independently
expected references, rather than being retained in the presentation object.
Ordinary bounded internal owner, subscription and plan references remain
structural only. The result can be independently reconstructed and validated
without identity, a mutable registry or producer-held state; that is
intentional evidence of zero authority.

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

Neither building nor validating a candidate admits its facts, authenticates the
references, authorises rendering/delivery, contacts a provider, creates or
retries a charge, grants or denies runtime access, creates Checkout, promises a
refund, persists state or activates billing.

## Fail-closed behaviour

Focused hostile tests cover:

- exact field and output order/types;
- dictionary and string subclasses;
- bool/int/float timestamp tricks;
- altered schema, classification, state, verification status, timestamps, copy,
  kind/verification relationships and authority flags;
- cross-owner, cross-subscription and cross-plan facts;
- extra or injected provider status;
- every common paid/success/active/confirmed label;
- non-canonical, invalid, future, out-of-order and stale timestamps;
- detachment after caller mutation and reconstruction without identity;
- fail-closed rejection of provider-object-ID-shaped and secret-shaped supplied
  or independently expected references, plus non-interpolation of ordinary
  internal customer references; and
- absence of upstream runtime imports, I/O, a clock or global admission registry.

The exact 300-second limit and contract values are closed over so mutation of
exported descriptive constants cannot expand the accepted boundary.

## Explicit exclusions and open gates

This package provides no authenticated adapter, admitted provider event,
customer route, HTML/native renderer, email/SMS/push delivery, notification,
runtime access decision, durable store, webhook verification, Stripe call,
Checkout creation, charge/retry/refund action, support override, activation,
production readiness or launch assurance.

It does not prove that a payment is pending or failed. It does not close W10 Q1,
Q2 or Q3, complete W10-S6, close any W7A/W8/W9 gate, or satisfy provider,
legal, finance/tax, security, accessibility, target-runtime, activation, release
or go-live evidence.

## Candidate ownership

Only these new paths are authorised:

- `reserved/billing/initial_payment_presentation.py`
- `tests/test_w10_initial_payment_presentation.py`
- `docs/W10_S6G_INITIAL_PAYMENT_PRESENTATION_EVIDENCE.md`

The candidate stops uncommitted for fresh independent review.
