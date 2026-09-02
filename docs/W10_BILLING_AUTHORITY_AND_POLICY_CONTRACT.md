# W10-S1A billing authority and policy-completeness contract

**Authority:** `FOUNDER_DECISIONS.md`, `FD-W10-001` (2 September 2026)

**Completion boundary:** `docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md`

**Scope:** provider-neutral, network-inert and persistence-free contract only

## Purpose

`reserved/billing/contracts.py` provides two deliberately separate boundaries:

1. an immutable, version-bound reconstruction of the commercial facts settled
   by `FD-W10-001`; and
2. an immutable register that reports whether every still-required subordinate
   policy input has an explicit, traceable decision.

The contract does not decide whether any policy is good enough or held by the
right authority. It makes absence, duplication, malformed provenance and
placeholder outcomes fail closed so later implementation cannot silently use a
provider default.

## Settled authority encoded

The singleton `INITIAL_BILLING_AUTHORITY` binds all of the following facts to
authority version `FD-W10-001/2026-09-02/v1`:

| Internal key | Exact amount | Currency |
|---|---:|---|
| `monthly` | `Decimal("29")` | GBP |
| `six_month` | `Decimal("156")` | GBP |
| `yearly` | `Decimal("288")` | GBP |

It also records:

- paid subscription is the October launch model;
- customer prices are inclusive of VAT **where applicable**, without a VAT
  rate, VAT amount or applicability determination;
- prices are initial and may change only under a later Founder Decision; and
- special discounts and offers are a required capability, but that requirement
  supplies neither a calculation rule nor access authority.

Provider product/price identifiers are not authority fields. A later Founder
decision must create a new versioned authority snapshot rather than mutate this
one.

## Required unresolved policy inventory

`REQUIRED_BILLING_POLICY_KEYS` is a stable fifteen-key denominator. Each key
needs one explicit `BillingPolicyDecision` before the register can report that
the policy inputs are complete.

| Contract key | Decision still required |
|---|---|
| `billing_provider` | Billing provider selection and boundary |
| `renewal_behaviour` | Renewal behaviour |
| `cancellation_timing` | Cancellation timing |
| `failed_payment_and_grace` | Failed-payment and grace handling |
| `entitlement_start_and_end` | Entitlement start and end |
| `refunds` | Refund policy |
| `tax_invoicing_and_additional_presentation` | Tax invoicing and presentation beyond the settled VAT-inclusive wording |
| `promotion_and_discount_mechanics` | Promotion and discount mechanics |
| `partner_offer_handling` | Partner-offer handling |
| `paid_access_surface` | Which launch surfaces require paid access |
| `trial_and_free_access_if_applicable` | Explicit support or non-support for trial/free access |
| `plan_changes_and_proration` | Plan-change and proration behaviour |
| `billing_account_recovery` | Billing-account recovery |
| `manual_overrides` | Manual override authority, limits and audit expectations |
| `post_settlement_dispute_chargeback_reversal_consequences` | Post-settlement dispute, chargeback and reversal handling, including entitlement consequences |

The conditional wording for trial/free access does not remove its key: an
explicit, traceable “not supported/not applicable” decision closes it without
inventing a free tier.

## Validation and status semantics

Authority values accept only exact enum members, exact tuples and exact finite
`Decimal` amounts. Construction and `dataclasses.replace` reject changed or
cross-assigned prices, missing/duplicate/reordered plan keys, non-GBP currency,
wrong authority versions, provider identifiers, VAT rates/applicability,
discount algorithms and access-grant fields.

A policy decision requires:

- one known `BillingPolicyKey`;
- a non-empty, trimmed, printable outcome that is not a placeholder or
  “provider default”; and
- a `DecisionProvenance` value with a stable decision identifier, decision
  owner, timezone-aware UTC timestamp and local record-plus-section reference.

Placeholder detection uses only conservative comparison normalization: Unicode
case-folding, collapsed surrounding/internal whitespace and removal of terminal
`.`, `,`, `!`, `?`, `;` or `:` punctuation. It then compares against a bounded
explicit vocabulary including `TBD`/`TBC`, `pending`,
`pending decision`, `decision pending`, `not decided`, `not yet decided`,
`unknown`, `to be decided`/`confirmed`/`determined`, `default`, and
`provider default`/`use provider default` (including the explicit hyphenated
and possessive forms). It does not score semantic adequacy, search for common
words inside legitimate prose or rewrite the retained outcome.

TBD/TBC recognition is additionally confined to a full-string, three-letter
token with at most one optional dot and arbitrary harmless whitespace between
the letters. This covers forms such as `T. B. D.`, `T . B . D .` and
`T .B .D` without treating those letters inside a longer sentence as a
placeholder.

Local provenance references must contain a record path and section anchor. The
path is lexical and may not contain `.` or `..` segments, so values such as
`../secret.md#x` and `docs/../secret.md#x` fail closed rather than being
accepted as local evidence identities.

The register rejects unknown values and duplicate keys. Missing keys are
returned in the declared denominator order. Its only statuses are:

- `policy_incomplete` — at least one required key is absent; and
- `policy_inputs_complete` — every key has one syntactically valid, traceable
  decision.

`policy_inputs_complete` is not a provider selection made by this module, an
approval of the decision substance, an entitlement, an access grant, billing
activation, integration evidence or launch readiness.

Every frozen slotted leaf has an exact complete-state validator. Authority,
policy-decision and register validators recursively revalidate every nested
leaf, not merely its class. Public construction, `dataclasses.replace`, copy,
deepcopy, direct reduction and pickle serialization/reconstruction all enter
those validators before returning or emitting reconstruction data. Missing
slot state, subclasses and forged nested prices, provenance, decisions or
registers therefore fail closed rather than being legitimised by rebuilding.

## What W10-S1A proves

- The exact initial GBP price facts and qualified VAT statement can be consumed
  without provider coupling or binary floating-point money.
- Later price authority can be versioned without treating current values as
  permanent.
- Every unresolved policy named by the W10 map has a finite, inspectable key.
- Missing policy remains visibly incomplete; no lifecycle default is supplied.
- The special-offer requirement cannot itself calculate a discount or grant
  access.
- The boundary can be tested without a network, datastore, credential, provider
  account or production configuration.

## What remains gated

W10-S1A does not select or call a billing provider; choose policy outcomes;
calculate VAT, discounts, refunds or proration; decide dispute/chargeback/
reversal consequences; create customers, checkout sessions, subscriptions,
invoices or webhooks; store billing state; derive entitlement; gate a route;
grant or revoke access; administer an account; reconcile money; activate a
configuration; or establish launch evidence.

Those outcomes remain in W10-S2 through W10-S8. Provider selection, policy
authority, persistence/retention/custody, authentication launch evidence,
customer journeys, security/operations, sandbox evidence, independent review
and Founder production/release/go-live authority retain their separate gates.
