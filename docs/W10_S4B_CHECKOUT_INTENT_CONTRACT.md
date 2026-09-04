# W10-S4B owner-bound Stripe Checkout intent/request-candidate contract

## Result and boundary

This package implements the smallest disabled-first Checkout-edge contract
unlocked by `FD-W10-002` and `FD-W10-003`. It is a pure, provider-separated
structural candidate boundary. It does not authenticate a user, persist or
consume an intent, access credentials, call Stripe, create a Checkout Session,
initiate a charge, accept a browser return, grant entitlement or activate a
sandbox or production environment.

**Candidate base:** `1d91526d11b5291d5388c78940682ca02edeb61e`
(tree `e2fc725961f816d80eed9e5373d738e5e21a024c`).

**Contract version:** `reserved-w10-checkout-intent-contract/1.0`.

The result is deliberately labelled
`structural_candidate_not_authenticated_persisted_provider_or_entitlement_admitted`.
Structural validation is not issuer admission or action authority. A future
adapter must authenticate the current Reserved owner again, atomically consume
a durable single-use intent, resolve the fixed destination to a reviewed HTTPS
URL and independently construct the provider request.

## Accepted sources and authority

| Source | Accepted commit | SHA-256 | Bounded use |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | through candidate base | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | `FD-W10-001` fixes the initial gross catalogue; `FD-W10-002` permits disabled-first Stripe Checkout design; `FD-W10-003` fixes the entitlement lifecycle. |
| `reserved/billing/contracts.py` | `9e8f94a9906f0c9d5c85b47223d20c34be499e1c` | `9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b` | Exact three-plan catalogue and authority version. |
| `reserved/billing/entitlement_core.py` | `94bd87f019dc226ec8c73f32515229189500cf06` | `b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b` | Provider-neutral lifecycle; payment confirmation is separate from Checkout. |
| `reserved/billing/event_inbox_contract.py` | `5bc29bcb30c95ea7a5a9430104653b366d709eb6` | `4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed` | Future owner-bound, idempotent event admission remains detached and non-durable. |
| `reserved/billing/stripe_disabled_first_contract.py` | `2ad4a63dd1f10ba38859050b47245c28390667d8` | `87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638` | Stripe Checkout subscription mode is provisional; completion is not payment or entitlement authority. |
| `docs/W10_S6C_AUTHENTICATED_PLAN_QUOTE_EVIDENCE.md` | `3e05fb7f3149ee7030be768909eb6fe4f50e0b75` | `c424c0ca999ef18568dfc1b86f79d9f0e27af1d05e7f9167ef9de43b344b3bb1` | Existing authenticated catalogue preview remains non-purchasing. |
| `docs/W10_S6D_PLAN_SELECTION_PREVIEW_EVIDENCE.md` | `46e2141c421fa80e39b60cd5b6bb955f44dfd863` | `d7306da9e1e163420e345567800c6789d8422619ceaf9b91d925458d0a136790` | Existing selected-plan preview supplies no checkout authority or action. |

S4A already preserves the necessary provider facts from official Stripe
documentation: Checkout supports subscription mode, and Checkout completion is
only a provider observation. S4B introduces no additional Stripe semantic and
therefore performs no fresh provider inference. Provider facts never override
Reserved authority.

## Exact detached input

`create_checkout_request_candidate` requires exactly one positional value: the
positive exact `users.id` asserted by the future authenticated Reserved-owner
adapter. The complete exact named fact set contains:

- an exact authentication-context dictionary repeating that owner, a redacted
  `evidence:` reference, its UTC interval and the explicit marker that the
  context is structural input rather than authentication proof;
- the same `owner_user_id` and exact catalogue authority version
  `FD-W10-001/2026-09-02/v1`;
- one exact plan key: `monthly`, `six_month` or `yearly`;
- namespaced opaque intent and idempotency identifiers;
- exact built-in UTC request, evaluation and expiry timestamps;
- the sole logical return destination
  `reserved_billing_return_reconciliation`;
- an exact owner/intent/idempotency/time-bound replay snapshot in `unused`
  state; and
- one redacted `evidence:` reference.

The function accepts no price, amount, currency, cadence, quantity, provider
product/price/customer/session identifier, URL, email, provider status,
entitlement, discount, VAT rate or credential input. Extra, partial, positional,
subtyped, ambiguous, cross-owner, stale, replayed or conflicting inputs fail.
Secret- and credential-shaped identifiers fail before projection.

Callable defaults supply no fact or authority. The public functions use exact
`*args`/`**kwargs` dispatch and validate argument counts and the complete named
set inside captured code. The implementation has no handle registry, live-object
registry or mutable closure collection. A coherent registry-injection attack
therefore has no admission mechanism to rewrite. Public constant/global and
callable-default rebinding is inert for saved functions.

## Server-side catalogue derivation

For the one accepted authority version, the contract independently rederives:

| Plan | Gross minor units | Currency | Recurrence |
|---|---:|---|---|
| `monthly` | `2900` | `GBP` | every 1 month |
| `six_month` | `15600` | `GBP` | every 6 months |
| `yearly` | `28800` | `GBP` | every 1 year |

The quantity is fixed to one and mode is fixed to `subscription`. Browser or
caller-supplied commercial facts cannot alter the projection. The wording
remains “inclusive of VAT where applicable”; this package performs no VAT or
invoice calculation and does not close the specialist VAT/invoice gate.

## Intent, replay and return semantics

The candidate is valid only when authentication precedes the request, the
request does not follow evaluation, the replay check occurs at that exact
evaluation instant, and expiry is later than evaluation but no more than five
minutes later or beyond authentication validity. Five minutes is a conservative
local structural lifetime, not a claim about Stripe Session lifetime.

The raw idempotency key is not projected. Its SHA-256 digest, exact owner,
intent, plan and all other candidate facts contribute to a deterministic
content identity. Repeated pure evaluation of identical unused facts produces
the same identity; it does not prove the intent was persisted or consumed.
Used, replayed, ambiguous, stale, cross-owner and conflicting snapshots deny.
A future durable repository must enforce unique owner-bound intent identity and
atomically compare-and-set unused to consumed before any provider call.

The candidate contains only a logical return-destination ID, never a URL. A
future adapter must map it to a fixed reviewed HTTPS destination. Any browser
return, success query, Checkout Session identifier or provider status has zero
payment and zero entitlement authority. Access begins only after Reserved's
separate verified, owner-bound, idempotent and order-safe provider-event path.

## Lifecycle and zero authority

The integrated `FD-W10-003` lifecycle remains explicit. `payment_recovery` is a
Reserved canonical state with one seven calendar days period established from
verified reconciled renewal-failure observations. No Stripe status is copied
into it, and Checkout cannot create or extend it.

Every candidate fixes these authorities to false:

- authentication and durable intent persistence/consumption;
- Stripe SDK, network and credentials;
- Checkout Session creation and charging;
- browser-return payment authority;
- provider-status entitlement authority;
- entitlement grant or mutation; and
- sandbox and production activation.

A structurally recreated exact tuple can at most remain the same zero-authority
structural candidate. Direct classes, dictionaries, lists, tuple subclasses,
incomplete shapes, tampered content and recomputation-free forged identities
fail structural validation. No structural result is acceptable as runtime
authentication, durable single-use evidence or provider-request authority.

## Residual external and later-slice gates

Before a real Checkout path can exist, Reserved still needs:

1. a real authenticated-owner adapter;
2. a durable owner-bound intent repository and atomic single-use consume;
3. accepted Stripe account/product/price configuration and reconciliation;
4. approved credential custody, rotation and target secret injection;
5. a reviewed fixed HTTPS return mapping plus CSRF/session-integrity handling;
6. sandbox failure, replay, ordering and reconciliation evidence;
7. verified webhook ingress, event inbox and entitlement reconciliation;
8. target security, privacy, finance/tax, operations and accessibility evidence;
9. outstanding Q1 refunds, Q2 paid-surface and Q3 post-settlement consequences;
   and
10. separate Founder provider, production, release and go-live authority.

This package does not implement any route, database, migration, provider SDK,
network access, credential, Checkout or Portal Session, webhook, charge,
entitlement, sandbox or production activation. It does not complete W10-S4 or
make W10 or Reserved launch-ready.

No Stripe SDK or provider dependency is imported by the contract.
