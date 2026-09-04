# W10 subscription and billing completion map

## Status and authority

**Evidence cut-off:** 4 September 2026

**Original planning commit:** `b15d3fcfa423192e1a8a2e8d0a49851b366518f4`

**Current integration reconciliation point:**
`051ae665a0cc94f6e9cdbbc728c621825c7769fe` (tree
`df4efac6e7e5265a54d5de8412b6aad9fb211155`)

**Current status:** **S1 independently reviewed and integrated; S2A's
provider/runtime-neutral authority, S2B's four fail-closed engineering defaults,
S2C's specialist-evidence/decision classification,
S3A's provider-neutral entitlement transition policy, S3B's detached event-inbox
contract, S4A's disabled-first Stripe edge contract, S5A's exact paid-surface
inventory and S5B's exact eleven-route reconciliation evidence are independently
reviewed and integrated; S2 partially implemented, with S3, S4 and S6 also
partial; S5A/S5B prerequisite evidence is integrated while S5 implementation
remains not started; 0/8 slices complete on the strict accepted-evidence
denominator; not launch-ready.**

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

### Fail-closed defaults and genuinely unresolved subordinate policy

Six Founder-settled policy keys are explicit. Integrated S2B at
`1033c9fbef008dcd33125a0b14e7fb18b8846d19` closes four further keys only as
ordinary engineering defaults under the accepted fail-closed boundaries:
promotions/discounts remain a reserved capability but inactive; partner offers
are disabled and unsupported; ordinary mid-cycle plan changes, proration and
immediate cancellation are disabled while paid-period-end cancellation and the
mandatory statutory/consumer-rights override are preserved; and no manual
entitlement override exists, with corrections limited to append-only observation
and reconciliation with zero direct entitlement effect. These details are not
represented as separately Founder-settled policy.

For historical continuity, the preceding S2A checkpoint described
six settled policy keys and nine policy keys unresolved. The accepted S2B defaults reduce
that current unresolved remainder to five; they do not retroactively expand
Founder authority.

Exactly five policy keys remain unresolved: refunds; tax invoicing/additional VAT
presentation; the exact paid-access surface; billing-account recovery; and
post-settlement dispute, chargeback or reversal consequences. None may be
silently inferred from a provider default. They require the appropriate product,
finance/tax, legal, security and operational evidence or decision. Escalate new
scope, consequential external commitments, material exceptions and high-risk
business judgement for Founder authority; ordinary implementation detail and
review are not Founder gates.

Integrated S2C at `a07348976321df65bbd95c9170c906bcddd5baa5`
independently classifies that remainder but does not answer or close it. Exactly
three consequential customer-treatment choices require Founder answers: **Q1**,
the discretionary-refund promise and confirmed-full-refund access consequence;
**Q2**, the exact paid-access class boundary against accepted S5A; and **Q3**,
the verified post-settlement loss/restoration access consequence. Tax
invoicing/additional VAT presentation requires accepted finance/tax/legal
evidence. The owner-bound no-transfer billing-account-recovery baseline requires
accepted security/privacy/operations and target evidence. Those latter two are
specialist gates under existing authority, not new Founder questions. Until Q1,
Q2 and Q3 are answered and all applicable evidence is accepted, all five keys
remain unresolved and S2 remains incomplete.

## Baseline finding and owned outcome

W10 owns a customer-to-billing-account-to-entitlement path that can quote one
of the three authorised plans, apply an explicitly configured offer, collect
and reconcile subscription payment through a selected provider, and enforce
and administer access according to approved lifecycle policy. It must be
owner-scoped, auditable, replay/idempotency safe, fail closed under ambiguity,
and independently demonstrated in the target environment.

The repository currently has a stable authenticated `users.id` boundary and
owner-isolation tests, but authentication alone grants every protected V2 route.
The integrated S1 catalogue/authority, S2B defaults, S3A lifecycle transition
policy and S3B event-inbox contract now have focused billing tests, but S3B is a
detached structural contract only: there is still no durable subscription/billing
schema or implemented event inbox, provider authenticity or persistence,
provider-verified entitlement decision, server-side paid-access gate,
provider-backed checkout/customer-portal route, billing webhook or provider SDK.
Authentication itself still lacks target-provider launch evidence.
Integrated S5A at `9c076019...` inventories the exact current route surface and
its observed access controls. Integrated S5B at `051ae665...` reconciles the
eleven internal/admin/legacy/unknown entries to bounded fail-closed treatments:
preserve five Founder-only routes and the Capital Gains hard-404, retire or
redirect three legacy public paths, and make two internal assurance/provider
pages production-404. These are accepted evidence and recommended engineering
treatments, not runtime changes; neither S5A nor S5B decides or enforces the paid
boundary.

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
| **W10-S2 — provider and policy closure** | Record the selected billing provider and every launch lifecycle/access/promotion/invoice and post-settlement dispute/chargeback/reversal policy needed by later slices, with decision owner and rationale. | **S2A, S2B and S2C are independently reviewed, checkpointed and integrated at `5464bfac7bec6b3456d1895b2355a7e8ce86859b`, `1033c9fbef008dcd33125a0b14e7fb18b8846d19` and `a07348976321df65bbd95c9170c906bcddd5baa5`.** S2A encodes six Founder-settled keys and the provisional Stripe capability boundary. S2B closes only four ordinary fail-closed engineering defaults. S2C classifies the exact five-key remainder and supplies evidence-backed recommendations/questions, but answers none: Q1 refunds, Q2 paid-access surface and Q3 post-settlement consequences remain Founder gates; VAT/invoice and no-transfer billing-account recovery remain specialist-evidence gates. S2 remains incomplete; S2C implements no policy and provides no legal/tax/provider/target acceptance. | Obtain authoritative answers to Q1/Q2/Q3 and accepted legal/finance evidence for refunds/post-settlement treatment, finance/tax/legal evidence for VAT/invoices, and security/privacy/operations/target evidence for owner-bound recovery. Provider terms/DPA/fees also remain open. Complete only when every key is versioned and accepted and no runtime behaviour relies on an undocumented provider default. |
| **W10-S3 — durable billing and entitlement core** | Implement the owner-bound catalogue/version reference, billing account, subscription and settlement observations, event inbox, audit/reconciliation record and policy-derived entitlement boundary, including post-settlement dispute/chargeback/reversal observations without assuming their access consequence. | **S3A and S3B are independently reviewed, checkpointed and integrated at `94bd87f019dc226ec8c73f32515229189500cf06` and `5bc29bcb30c95ea7a5a9430104653b366d709eb6`.** S3A defines the provider-neutral lifecycle transition policy. S3B defines detached immutable shapes and fail-closed admission/reconciliation invariants for future owner-bound billing account, subscription, event, receipt and disposition records. S3 remains incomplete: S3B is contract-only and supplies no database schema, migration, implemented durable inbox, provider authenticity, persistence or entitlement decision. | S1 and the relevant S2 policies; accepted S3A/S3B semantics; W9 datastore, retention, encryption/key-custody and erasure decisions. Still required: durable billing-account/subscription/event-inbox/audit/reconciliation records; migrations; exclusive shared-file ownership and concurrency controls; authenticated event source; dispute/chargeback/reversal and correction/deletion/retention tests; independent schema/security/privacy review. |
| **W10-S4 — provider adapter and collection lifecycle** | Implement disabled-first provider customer/checkout/management, verified webhooks, reconciliation and offer primitives against the provider-neutral core. | **S4A independently reviewed, checkpointed and integrated at `2ad4a63dd1f10ba38859050b47245c28390667d8`: the current official Stripe Checkout, Customer Portal, webhook integrity, duplicate/order and subscription-status semantics are encoded as a disabled, network-inert, non-entitling edge contract. S4 remains incomplete.** No SDK, credential, webhook endpoint, persistence, session creation, charge or provider activation is present. | Preserve S4A's exact disabled-first boundary. Completion still requires applicable S2 policies, S3B-compatible durable identities/event inbox, approved credential custody, accepted provider terms/security boundary and sandbox access. Synthetic and sandbox tests must cover successful, declined, delayed, duplicate, replayed, out-of-order, forged, refunded, post-settlement disputed/charged-back/reversed and recovered cases. No configuration or credential alone may enable it. |
| **W10-S5 — server-side access and administration** | Apply the approved entitlement decision, including explicitly approved post-settlement dispute/chargeback/reversal consequences, to every in-scope paid surface and supply least-privilege, audited support/admin correction tools. | **S5A and S5B are independently reviewed, checkpointed and integrated at `9c0760192bb2420b90e57ec7313f69bbe52cbf74` and `051ae665a0cc94f6e9cdbbc728c621825c7769fe`.** S5A source-binds the exact 44 always-registered and 8 HICBC-conditional routes and their provisional classes. S5B source-binds exact treatment of all 11 internal/admin/legacy/unknown entries and creates no new Founder question. Both are prerequisite evidence only: no route, paid boundary, entitlement guard or runtime behavior changed, and S5 implementation remains not started. | The separate route-cleanup package may proceed before and independently of Q2 because preserving Founder-only/Capital-Gains closures, retiring or redirecting legacy paths and production-404ing internal pages does not decide paid scope. Actual paid-boundary enforcement must await the exact Q2 Founder answer against accepted S5A plus the applicable S2 policies and S3 entitlement API. Test cross-user, stale/unknown, revocation, cache, concurrency, direct-URL/API bypass and admin separation; authentication/client hiding never substitutes for server enforcement. |
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

1. Preserve the independently reviewed integrated S1, S2A, S2B, S2C, S3A,
   S3B, S4A, S5A and S5B evidence. S2A encodes the six Founder-settled
   provider/lifecycle inputs;
   S2B closes only four fail-closed engineering defaults and leaves exactly five
   keys unresolved. S2C classifies Q1/Q2/Q3 as consequential Founder choices and
   VAT/invoice plus no-transfer recovery as specialist gates, but supplies no
   answer or external acceptance, so it does not close S2. S3A encodes the bounded
   transition policy without claiming provider verification, persistence or enforcement.
   S3B encodes detached structural record and reconciliation invariants, not a
   durable inbox, authenticated source, persistence layer or entitlement
   decision. S4A encodes only the disabled provider edge and cannot verify a
   callback or emit entitlement. S5A is inventory evidence only; S5B reconciles
   its 11 internal/admin/legacy/unknown entries without modifying them. Neither
   approves or enforces a paid boundary. Provider diligence, specialist evidence
   and the three Founder answers may run in parallel, but S2 closes only through
   explicit accepted evidence.
2. Durable S3 implementation follows the relevant S1/S2 contracts and must
   preserve S3A/S3B. S4 and S5 can then run in parallel: S4 owns authenticated
   provider translation, while S5 consumes only synthetic or canonical billing
   observations and entitlement decisions. Neither may treat S3B structural
   issuance as provider authenticity or durable admission.
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
dependencies are acceptance of Stripe terms and onboarding under the provisional
baseline (or an expressly authorised replacement), current provider documentation,
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
Provider terms/final acceptance and onboarding, credentials or sandbox queues are the largest
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

W10-S1, S2A, S2B, S2C, S3A, S3B, S4A, S5A and S5B are independently reviewed
and integrated.
S2A records the six Founder-settled provider and paid-lifecycle decisions. S2B
closes only the four accepted fail-closed engineering defaults and preserves the
exact five unresolved keys. S2C classifies the remaining evidence and decision
owners without answering or closing a policy: Q1 refunds, Q2 paid surface and Q3
post-settlement consequences remain unanswered Founder questions; VAT/invoice
treatment and owner-bound no-transfer billing-account recovery remain specialist
evidence gates rather than new Founder questions. S3A remains the
provider-neutral transition policy;
S3B is only the detached record/admission/reconciliation contract and provides
no durable inbox, provider authenticity, persistence or entitlement decision.
S4A remains a disabled provider-edge contract with no runtime adapter, signature
verification or activation. S5A supplies the exact source-bound route inventory
and minimal paid-surface decision question, but no boundary approval or
server-side entitlement enforcement. S5B supplies the exact source-bound
reconciliation of its 11 internal/admin/legacy/unknown routes and no new Founder
question, but changes no route and does not start S5.

The next S2 work is accepted specialist evidence for the enumerated refund,
VAT/invoice, recovery and post-settlement gates plus authoritative answers to
Q1, Q2 and Q3, followed by one versioned closure record for all 15 keys. The
smallest S5 work that can proceed before Q2 is a separate fail-closed route cleanup
implementing S5B's accepted treatments: preserve Founder-only and Capital Gains
closures, retire or redirect the three legacy public paths and production-404 the
two internal pages, with refreshed S5A/S5B evidence. It must not decide customer
paid scope. After Q2 and the applicable S2/S3 dependencies, the smallest
server-side paid-boundary design may consume a synthetic canonical entitlement
decision; it still implements no provider path. A
durable S3 implementation may proceed only when its datastore, migration
ownership, retention/erasure, key-custody, minimisation, authenticated-source and
independent-review dependencies are accepted; it must implement rather than
merely relabel S3B. Further provider-edge S4 implementation must preserve S4A,
proceed only against current authoritative technical evidence and remain
disabled-first.

No provider adapter, credential, persistence migration, access grant or checkout
package follows merely from the S1 contract. Provider-specific implementation
waits for a selected provisional provider boundary and applicable external
evidence. Preserve the accepted non-durable S3A/S3B contracts. Further durable
entitlement/event-inbox implementation requires the approved W9
custody/data-lifecycle boundary as well as the explicit lifecycle decisions.

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
implemented with independently reviewed/integrated S2A, S2B and evidence-only
S2C, six Founder-settled keys, four fail-closed engineering defaults and exactly
five policy keys unresolved, with Q1/Q2/Q3 unanswered and VAT/invoice plus
no-transfer recovery still awaiting specialist acceptance; S3 partially
implemented with independently
reviewed/integrated S3A and detached contract-only S3B but no durable inbox,
provider-authenticated source, persistence or enforcement boundary; S4 partially
implemented with independently reviewed/integrated S4A but no runtime adapter,
signature verification, persistence or activation; S5 implementation not
started, with independently reviewed/integrated S5A inventory and S5B 11-route
reconciliation as prerequisite evidence only, but no route change, approved paid
boundary or enforcement; S6 partially
implemented/integrated; strict completion remains 0/8 pending S2 policy closure
and every slice's remaining completion evidence.** Provider, target,
specialist-review, residual-risk, Founder activation/release and launch authority
gates remain open.
