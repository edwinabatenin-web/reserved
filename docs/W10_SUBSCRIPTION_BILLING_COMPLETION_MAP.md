# W10 subscription and billing completion map

## Status and authority

**Evidence cut-off:** 4 September 2026

**Original planning commit:** `b15d3fcfa423192e1a8a2e8d0a49851b366518f4`

**Current integration reconciliation point:**
`9e8f94a9906f0c9d5c85b47223d20c34be499e1c` (tree
`0351fc341ebe4220c173da064c4aaf8db143b394`)

**Current status:** **S1 independently reviewed and integrated; S2 partially
implemented as a provider/runtime-neutral authority candidate; S6 partially implemented
and integrated; 0/8 slices complete on the strict accepted-evidence denominator;
not launch-ready.**

This map gives the October-launch subscription and billing workstream a finite
endpoint. It is a planning and assurance control, not a provider decision,
billing policy, implementation approval, production-access request or launch
approval. `FOUNDER_DECISIONS.md` is authoritative where older material differs.

### Settled Founder authority (`FD-W10-001`)

- Reserved is a paid subscription product at the October launch.
- Initial customer-facing prices are **£29 monthly**, **£156 for six months**
  and **£288 yearly**, inclusive of VAT where applicable.
- These are initial, changeable prices rather than permanent price promises; a
  later change requires a later Founder Decision.
- The minimum ability to sell, grant and administer access is in October scope.
- Special discounts and offers must be supportable.
- Unrelated commerce, marketplace and reseller scope is not authorised.

### Settled provisional provider and lifecycle authority (`FD-W10-002` / `FD-W10-003`)

- Stripe Billing, Stripe Checkout and Stripe Customer Portal form the
  provisional disabled-first subscription baseline; Stripe Connect is excluded.
- Paid access starts only after verified successful initial payment and renews
  automatically for the selected paid plan.
- Cancellation stops future renewal while ordinary access continues through the
  already-paid period.
- The first verified failed-renewal observation enters the explicit canonical
  `payment_recovery` state for exactly seven calendar days. Ordinary access may
  continue during that bounded state; duplicate/repeated failures cannot extend
  it; verified recovery returns to ordinary paid state; unresolved expiry
  suspends ordinary access.
- No October free trial or free tier is authorised.
- Provider events and labels are observations, never direct entitlement flags.
- This authority remains provisional and does not accept provider terms, approve
  credentials, activate billing, settle VAT/invoice treatment or authorise a
  charge.

### Genuinely unresolved subordinate policy

Six settled policy keys are now explicit. Nine policy keys remain unresolved:
refunds; tax invoicing/additional VAT presentation; promotion/discount mechanics;
partner-offer handling; the exact paid-access surface; plan changes/proration;
billing-account recovery; manual overrides; and post-settlement dispute,
chargeback or reversal consequences. None may be silently inferred from a
provider default. These are implementation policies or decisions for the
appropriate product, finance/tax, legal, security and operational owners.
Escalate new scope, consequential external commitments, material exceptions and
high-risk business judgement for Founder authority; ordinary implementation
detail and review are not Founder gates.

## Baseline finding and owned outcome

W10 owns a customer-to-billing-account-to-entitlement path that can quote one
of the three authorised plans, apply an explicitly configured offer, collect
and reconcile subscription payment through a selected provider, and enforce
and administer access according to approved lifecycle policy. It must be
owner-scoped, auditable, replay/idempotency safe, fail closed under ambiguity,
and independently demonstrated in the target environment.

The repository currently has a stable authenticated `users.id` boundary and
owner-isolation tests, but authentication alone grants every protected V2 route.
There is no subscription/billing schema, entitlement decision, access gate,
catalogue, checkout/customer-portal route, billing webhook, provider SDK or
billing-specific test suite. Authentication itself still lacks target-provider
launch evidence.

`docs/STRIPE_CONNECT_SPEC.md`, `reserved/providers/payments/base.py` and
`reserved/providers/payments/stripe_connect.py` concern the separate movement
of a customer's set-aside money. Stripe Connect is historical and unselected;
the disabled stub neither selects Stripe for subscriptions nor supplies billing
capability. Transaction-classifier uses of the word `subscription` describe a
customer's business expenses and are also unrelated. W10 may reuse general
security lessons such as signed webhooks, idempotency and reconciliation, but
must not reuse either domain contract as if it were subscription billing.

## Finite slices and evidence

| Slice | Smallest coherent outcome | Current state | Dependencies and completion evidence |
|---|---|---|---|
| **W10-S1 — authority and provider-neutral contract** | Encode the versioned initial plan catalogue and a fail-closed inventory of required policy inputs, while representing discounts/offers only as a required capability. | **Independently reviewed, checkpointed and integrated at `9e8f94a...`.** Exact authority, billing boundary, adversarial integrity and affected/full regression evidence passed. The slice remains short of launch-evidence-complete because later provider/target evidence is outside S1. | Preserve the exact integrated S1 authority and its 15-key denominator. S2 must consume its closure-bound validation/projector protocol, never mutable raw attributes or provider defaults. |
| **W10-S2 — provider and policy closure** | Record the selected billing provider and every launch lifecycle/access/promotion/invoice and post-settlement dispute/chargeback/reversal policy needed by later slices, with decision owner and rationale. | **S2 partially implemented as W10-S2A authority evidence: six settled policy keys and the provisional Stripe capability boundary are encoded; nine policy keys remain unresolved. S2 remains incomplete.** The candidate is provider/runtime-neutral and does not activate billing. | Independent acceptance/integration of S2A; provider terms/DPA/fees and appropriate product, finance/tax, legal, security and operational review for the nine remaining keys. Complete only when no runtime behaviour relies on an undocumented provider default. |
| **W10-S3 — durable billing and entitlement core** | Implement the owner-bound catalogue/version reference, billing account, subscription and settlement observations, event inbox, audit/reconciliation record and policy-derived entitlement boundary, including post-settlement dispute/chargeback/reversal observations without assuming their access consequence. | **Not started.** | S1 and the relevant S2 policies; W9 datastore, retention, encryption/key-custody and erasure decisions. Migrations, ownership/concurrency, ordered-event, duplicate/replay, dispute/chargeback/reversal, correction and deletion/retention tests; independent schema/security review. |
| **W10-S4 — provider adapter and collection lifecycle** | Implement disabled-first provider customer/checkout/management, verified webhooks, reconciliation and offer primitives against the provider-neutral core. | **Not started.** | S2 provider selection/contract; S3 identities; approved credential custody; current official provider contract and sandbox access. Synthetic contract tests plus successful, declined, delayed, duplicate, replayed, out-of-order, forged, refunded, post-settlement disputed/charged-back/reversed and recovered sandbox evidence. No configuration or credential alone may enable it. |
| **W10-S5 — server-side access and administration** | Apply the approved entitlement decision, including explicitly approved post-settlement dispute/chargeback/reversal consequences, to every in-scope paid surface and supply least-privilege, audited support/admin correction tools. | **Not started.** | S2 access/lifecycle/override policy and S3 entitlement API; can use synthetic events while S4 proceeds. Route inventory, cross-user, stale/unknown status, dispute/chargeback/reversal, revocation, cache, concurrent update, bypass and audited-override tests; authentication and client-side hiding must never substitute for server enforcement. |
| **W10-S6 — customer billing journeys** | Deliver truthful plan/offer presentation and the approved checkout, success/pending/failure, renewal/cancellation, invoice/receipt/refund, post-settlement dispute/chargeback/reversal and account-management journeys. | **Partial local implementation.** Integrated S6A–D work provides plan presentation, a safe renderer, an authenticated plans preview and an authenticated plan-selection preview (`45ade8e...`, `23d04a6...`, `3e05fb7...`, `46e2141...`). It does not provide provider-backed checkout or lifecycle journeys and is not counted complete. | Preserve those components. Completion still requires S1 catalogue; relevant S2 policy; stable S3-S5 contracts; provider-backed checkout/account-management states; exact price/VAT copy review; accessibility/browser evidence; no surprise renewal or invented refund/grace/dispute outcome; and clear recovery/support paths. |
| **W10-S7 — billing security, privacy and operations** | Close W10-specific abuse, privacy, reconciliation, monitoring, support, recovery and incident controls without duplicating W9's general control plane. | **Not started.** | Threat model plus S2-S6; W9 custody, retention, monitoring, incident and target-runtime controls. Exercised webhook/credential rotation, alerting, ledger-provider and dispute/chargeback/reversal reconciliation, outage/backlog recovery, account erasure/retention and support runbooks with redacted evidence. |
| **W10-S8 — integrated target assurance and activation** | Prove the complete paid-access journey in the launch candidate and assemble the W10 release evidence. | **Not started.** | S1-S7, launch identity and target runtime, provider sandbox/production-capable configuration and independent reviewer. End-to-end positive and failure-path evidence, final privacy/security/finance-tax review, residual-risk disposition and separate Founder authorisation for production activation/release/go-live. |

## Assurance states and stable denominator

Each slice is tracked separately as **planned**, **implemented**, **locally
verified**, **independently reviewed**, **integrated**, **launch-evidence-complete**
and **launch-ready**. “Integrated” means present in the exact launch-candidate
lineage with applicable regressions passing; it does not prove provider or
target-runtime behaviour. “Launch-evidence-complete” requires the slice's
applicable target, security/privacy, operational and commercial evidence.
“Launch-ready” additionally requires all dependent slices and the final
activation/release authority.

The stable delivery denominator is the eight slices above. A slice contributes
one only when all of its stated completion evidence is accepted; partial work
does not round up. At this cut-off **0/8 (0%)** are complete. Existing auth and
payment-boundary foundations are dependencies, not partial W10 slices. Terminal
checks are a separate **0/13** and must not be combined with the delivery
percentage. Change either denominator only if authoritative scope changes or
new evidence proves that a launch-critical outcome is absent; record the reason
rather than growing the map for ordinary fixes.

## Dependencies, parallelism and collision boundaries

1. Preserve the independently reviewed integrated S1 contract. S2A encodes the
   six settled provider/lifecycle inputs without closing S2. Provider diligence
   and the nine remaining policies may run in parallel, but S2 closes only
   through explicit accepted evidence.
2. S3 follows the relevant S1/S2 contracts. S4 and S5 can then run in parallel:
   S4 owns provider translation, while S5 consumes only synthetic or canonical
   billing observations and entitlement decisions.
3. Preserve S6A–D's integrated presentation and authenticated preview work.
   Binding customer actions and the remaining provider-backed lifecycle journeys
   wait for stable S2-S5 contracts. S7 develops alongside S3-S6 and is exercised
   against their integrated result. S8 is the final serial gate.
4. One owner at a time controls `reserved/database.py` migrations and shared
   user/account deletion. Billing code should start in a new `reserved/billing/`
   boundary; provider-specific code must translate at its edge and must not
   write access flags directly.
5. Changes to `reserved/auth.py`, `reserved/web/v2.py`, shared templates/nav,
   `reserved/__init__.py`, CSP/configuration, W9 controls or release metadata
   require an enumerated integration package and the relevant workstream owner.
   No parallel package may edit the same route, migration, entitlement contract
   or price-authority record. Provider product/price IDs and secrets remain
   deployment configuration/custody concerns, never Founder authority.

Upstream contracts are the Founder authority snapshot, authenticated stable user
identity and the W9 custody/data-lifecycle/operations boundaries. External
dependencies are provider selection and terms, current provider documentation,
sandbox access, approved credentials/key custody, target hosting, finance/tax
review of billing VAT/invoices and independent target review. W10 is independent
of Yapily PIS/VRP and the tax calculation engine except for shared identity,
security, UI and release surfaces.

## Effort and critical path

These are planning ranges, not delivery promises. They assume two engineers can
work in parallel, prompt policy decisions, one reviewer, an established billing
provider with usable sandbox tooling, and reuse of the existing auth/W9
foundations. “Critical-path” is the likely serial contribution in working days;
external contracting/onboarding queues can extend elapsed time beyond it.

| Slice | Active effort | Likely elapsed | Critical-path contribution |
|---|---:|---:|---:|
| S1 | 2–3 person-days | 2–4 working days | 2–3 days |
| S2 | 2–5 person-days plus decision time | 3–10 working days | 3–10 days |
| S3 | 5–8 person-days | 1–2 weeks | 5–8 days |
| S4 | 6–10 person-days | 2–4 weeks | 6–10 days |
| S5 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S6 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S7 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S8 | 5–8 person-days | 1–3 weeks | 7–12 days |

Total active effort is roughly **32–55 person-days**. A conservative elapsed
range is **7–14 weeks** with the assumed parallelism; the serial critical path
is roughly **29–58 working days** before any longer external queue is known.
Provider selection, contracting, credentials or sandbox queues are the largest
schedule risks and may extend elapsed time beyond fourteen weeks; they are not
disguised inside the engineering estimate.

## Finite terminal W10 gate

W10 is complete only when all thirteen checks pass:

1. The three current plans and customer-facing prices match the applicable
   Founder authority version, use GBP exact-money representation, and show VAT
   inclusion where applicable without inventing a VAT rate or applicability.
2. Every required renewal, cancellation, failed-payment/grace, entitlement,
   refund, post-settlement dispute/chargeback/reversal, invoice, offer/discount,
   partner-offer, access and override behaviour is explicit and approved by its
   appropriate owner.
3. A billing provider is explicitly selected and its commercial, legal,
   technical, security and data-processing boundary is accepted; historical
   Stripe Connect or Yapily payment material is not treated as that selection.
4. Billing accounts, events, subscriptions, settlement reversals/disputes and
   entitlements are owner-bound, versioned, auditable, idempotent, order-safe
   and reconcilable; provider state is never copied directly into an unaudited
   access flag.
5. Signed provider callbacks, checkout/management returns and reconciliation,
   including post-settlement dispute/chargeback/reversal events, resist forgery,
   replay, duplication, delay, reordering, cross-user access and uncertain
   status, and fail closed without losing recoverability.
6. Every paid launch surface is enforced server-side under the approved access
   policy, including the approved consequences of a post-settlement dispute,
   chargeback or reversal and access through direct URLs and APIs; support/admin
   access and corrections are least-privilege and auditable.
7. Purchase, offer, pending, success, renewal, cancellation, failure, recovery,
   invoice/receipt, refund and post-settlement dispute/chargeback/reversal
   journeys behave and communicate exactly according to approved policy across
   supported browsers and accessibility checks.
8. Special discounts/offers are demonstrated without allowing unapproved price,
   duration, stacking, eligibility or entitlement consequences; partner offers
   remain disabled until their handling is explicit.
9. Billing VAT determination, customer presentation, invoice/receipt content,
   finance reconciliation and refund/dispute/chargeback/reversal accounting pass
   the applicable finance/tax review; VAT-inclusive price authority alone is not
   treated as tax advice.
10. Billing personal data, provider identifiers and credentials follow approved
    minimisation, retention, erasure, encryption/custody, log-redaction and
    account-recovery controls.
11. Monitoring, alerting, webhook backlog recovery, provider-ledger and
    post-settlement dispute/chargeback/reversal reconciliation, outage
    degradation, credential rotation and incident/support runbooks are exercised
    in the intended environment.
12. The exact launch candidate passes local regression, provider sandbox,
    end-to-end identity-to-access, negative/failure, privacy, security and
    operational assurance with traceable redacted evidence and independent
    review.
13. Residual risks are explicitly accepted and the separate Founder gates for
    production access, payment authority, activation, merge/release and go-live
    are recorded. No credential, provider dashboard setting or green local test
    can grant launch status by itself.

## Current next action

W10-S1A is independently reviewed and integrated. The current S2A candidate
records the six settled provider and paid-lifecycle decisions while preserving
the nine unresolved keys. The next action is independent S2A review/integration,
followed by provider-neutral S3 design against the explicit lifecycle subset and
bounded work to close the remaining S2 evidence without inventing defaults.

No provider adapter, credential, persistence migration, access grant or checkout
package follows merely from the S1 contract. Provider-specific implementation
waits for a selected provisional provider boundary and applicable external
evidence. Provider-neutral entitlement design may begin only against explicit
lifecycle decisions and the approved W9 custody/data-lifecycle boundary.

## Explicitly out of scope

This map does not authorise set-aside PIS/VRP or other customer money movement,
marketplace/reseller/affiliate commerce, merchant acquiring for third parties,
multi-currency or non-UK expansion, tax-return/VAT-return functionality, a free
tier or trial, account sharing/team seats, bespoke enterprise billing, dunning
optimisation, or post-launch pricing experiments. It does not select a provider,
amend Founder Decisions, modify the Control Plane, access production or sandbox
accounts, handle credentials, charge money, merge, deploy or go live. A required
launch policy may describe a deliberately unsupported case; unsupported
sophistication does not create another slice unless authoritative scope changes.

**Map disposition:** **S1 independently reviewed and integrated; S2 partially
implemented with six settled policy keys and nine policy keys unresolved; S6
partially implemented/integrated; strict completion remains 0/8 pending S2
policy closure and each slice's remaining completion evidence.** Target evidence
and launch authority remain open.
