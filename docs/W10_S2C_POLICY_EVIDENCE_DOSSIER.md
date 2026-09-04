# W10-S2C policy evidence and decision dossier

## Status, purpose and boundary

**Evidence retrieval/cut-off:** 4 September 2026

**Repository reconciliation point:** `5612f7a33f27f09d1fa988f15dfdffbe77a72705`

**Repository tree:** `4786614d7ea428e3aea1d61a72dc74d9aad6bd92`

**Disposition:** candidate specialist-evidence and decision record; independent
review and explicit acceptance remain required.

This dossier reconciles the five W10-S2 policy keys that remain unresolved after
the integrated S2A and S2B contracts. It distinguishes ordinary engineering
defaults, provider facts, specialist evidence and genuinely consequential
Founder choices. It does not answer a Founder question, amend Founder authority,
complete S2, implement policy or authorise launch.

No route, entitlement, account, persistence, provider setting or customer data
was changed or exercised. There is no SDK or network integration, credential,
provider session, charge, refund, invoice, dispute action, migration, deployment
or production evidence in this package. Official sources were read as public
evidence only. Their content is not legal or tax advice.

## Executive disposition

| Remaining S2 key | Ordinary engineering default now supportable | Missing accepted evidence | Consequential Founder choice | Current disposition |
|---|---|---|---|---|
| `refunds` | No silent/automatic refund; owner-bound, idempotent request and verified outcome; pending/failed is not succeeded; no provider event directly changes access. | UK consumer-law review of Reserved's supply/customer classification, cancellation information/consent, statutory remedies and terms; finance treatment. | Discretionary refund promise beyond mandatory rights, and the paid-access consequence of a confirmed full discretionary refund. | **Founder Q1 plus legal/finance acceptance; fail closed meanwhile.** |
| `tax_invoicing_and_additional_presentation` | Preserve the authorised VAT-inclusive totals; never add tax beyond those displayed totals, invent a rate/applicability, or call a document a VAT invoice without accepted evidence. | Entity and VAT-registration facts; supply/customer/place-of-supply classification; tax rate/treatment; invoice/credit-note fields, timing and retention; tax review of Stripe configuration. | None on present evidence: Founder already settled customer-facing prices inclusive of VAT where applicable. Escalate only if specialist evidence creates a material price/scope choice. | **No Founder question now; finance/tax evidence required.** |
| `paid_access_surface` | Inventory and server-side enforcement design may proceed; unknown/internal surfaces stay excluded until reconciled; public/auth/legal/support and purchase/recovery paths retain their own controls. | S5A is accepted local evidence. Still missing: the 11-route reconciliation, Founder Q2 and future security/target review of enforcement and bypass coverage. | Which authenticated product surfaces are inside the paid boundary and any exceptions. | **Founder Q2 against accepted S5A; no enforcement before authority.** |
| `billing_account_recovery` | Current authenticated Reserved owner is the sole root; provider email/customer ID is never login authority; no cross-account transfer/merge/manual entitlement grant; ambiguity fails closed. | Target identity-recovery, support, security/privacy and operational evidence; owner-to-provider mapping assurance. | None for the safe October baseline. A later transfer, household/team sharing or identity-merger capability would be a new choice. | **No Founder question now; security/operations evidence required.** |
| `post_settlement_dispute_chargeback_reversal_consequences` | Authenticate, bind, deduplicate, order and reconcile observations; ambiguous/open/partial states do not grant or extend access and never become direct access flags. | Provider sandbox event matrix; legal/finance/support/fraud treatment; target reconciliation and appeal/recovery runbook. | When a verified loss/reinstatement of funds suspends/restores ordinary paid access. | **Founder Q3 plus specialist acceptance; fail closed meanwhile.** |

These classifications apply `FD-OA-001`: implementation detail is not converted
into a Founder gate, while material customer treatment and economic-risk choices
are not silently made as engineering defaults.

## Exact repository evidence

| ID | Integrated identity | Artifact | SHA-256 | Evidentiary use |
|---|---|---|---|---|
| R-01 | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `FOUNDER_DECISIONS.md` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | `FD-W10-001`–`003` and `FD-OA-001`; settled prices/provider/lifecycle and unresolved boundary. |
| R-02 | `5612f7a33f27f09d1fa988f15dfdffbe77a72705` | `docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md` | `7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d` | Exact five-key remainder, accepted S5A prerequisite status, strict 0/8 status and completion gates. |
| R-03 | `c09dac2eac097347357b3d4fc252977a0b8115a3` | `docs/W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md` | `e5911c70199727beba888175f5f31a208a4418eb16cae7978e8b52fa57d688ce` | Fifteen-key policy denominator and non-inference rule. |
| R-04 | `5464bfac7bec6b3456d1895b2355a7e8ce86859b` | `docs/W10_S2A_PROVIDER_LIFECYCLE_AUTHORITY_EVIDENCE.md` | `48cefde6e995f160f6d0d0199cc287c4d7359f4c891e88ca251a65a661b75544` | Six Founder-settled S2 keys and provisional Stripe boundary. |
| R-05 | current descendant reconciliation (historical source checkpoint `1033c9fbef008dcd33125a0b14e7fb18b8846d19`) | `docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md` | `617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703` | Four ordinary defaults and exact five-key unresolved remainder; still live-drift checked. |
| R-06 | `94bd87f019dc226ec8c73f32515229189500cf06` | `docs/W10_S3A_ENTITLEMENT_TRANSITION_EVIDENCE.md` | `07fced7c7ca2f2ecb48541bb2e25db177651ecfb13dd75bda21b08a084e3bda8` | Entitlement transition boundary; refunds/disputes remain excluded. |
| R-07 | `5bc29bcb30c95ea7a5a9430104653b366d709eb6` | `docs/W10_S3B_EVENT_INBOX_CONTRACT.md` | `4e28d354dcff1bb5e44f7c01fa17a7712c209df3010fbb722bb8fbf28ac88182` | Detached inbox shapes; unknown/refund/dispute/reversal inputs reconcile with zero direct entitlement effect. |
| R-08 | `2ad4a63dd1f10ba38859050b47245c28390667d8` | `docs/W10_S4A_STRIPE_DISABLED_FIRST_CONTRACT_EVIDENCE.md` | `da9881c5625cf1f338b8f2626d0b6c4806594508784f84c64a0160c94706111a` | Network-inert Stripe edge, webhook/provider-observation limits and unresolved consequences. |
| R-09 | `9c0760192bb2420b90e57ec7313f69bbe52cbf74` (tree `9b6c8891d0ab91e703f55a6a92b9d47b1f62aeac`) | `docs/W10_S5A_PAID_SURFACE_INVENTORY.md` | `abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8` | Independently accepted exact route inventory and provisional classes; evidence only, with S5 implementation not started. |
| R-10 | `9c0760192bb2420b90e57ec7313f69bbe52cbf74` (tree `9b6c8891d0ab91e703f55a6a92b9d47b1f62aeac`) | `tests/test_w10_paid_surface_inventory.py` | `0d1bec99ea12496a747906b69619df0d60cd339b870042573b7dc60158c060f6` | Source-bound route, class, guard, CSRF and HICBC-registration freshness checks; not a paid-boundary decision. |

The accepted S5A evidence is the route-level dependency for Q2. This dossier
binds its exact accepted commit, tree and artifact hashes without copying its
route inventory. S5A remains evidence-only: it does not answer Q2, start S5
implementation or authorise enforcement.

## Official source register

All web sources below were retrieved on **4 September 2026**. Provider pages
establish Stripe behavior/capability only. Statute and government guidance
identify matters for qualified UK legal/tax review; this dossier does not decide
Reserved's customer, contract, supply, VAT or jurisdiction classification.

### Stripe primary sources

| ID | Official URL | Bounded fact used |
|---|---|---|
| P-01 | <https://docs.stripe.com/refunds> | Stripe supports full and partial refunds after success, with aggregate refunds bounded by the original charge; refund state can be pending, require action, succeed or fail, and available balance/payment method affects processing. |
| P-02 | <https://docs.stripe.com/customer-management> | Customer Portal can manage billing information, payment methods, invoices and subscriptions; portal behavior is configurable and sessions are temporary. |
| P-03 | <https://docs.stripe.com/customer-management/configure-portal> | Portal capabilities are configuration choices; a provider configuration must not silently settle Reserved policy. |
| P-04 | <https://docs.stripe.com/customer-management/integrate-customer-portal?locale=en-GB> | Reserved must create and bind a portal session from its application; Stripe warns not to use the billing email as the login credential. |
| P-05 | <https://docs.stripe.com/tax/invoicing/tax-ids?locale=en-GB> | Stripe can render account/customer tax IDs, but the customer information and applicable validation remain merchant responsibilities. |
| P-06 | <https://docs.stripe.com/invoicing/dashboard/credit-notes> | A credit note can reduce an open or paid invoice and may be associated with refund, customer credit or an out-of-band adjustment; capability does not choose policy. |
| P-07 | <https://docs.stripe.com/disputes/how-disputes-work?locale=en-GB> | A dispute/chargeback can reverse funds and fees while the issuing bank controls the decision and the case moves through provider states. |
| P-08 | <https://docs.stripe.com/api/events/types> | Stripe exposes dispute created/updated/closed and funds reinstated/withdrawn events, plus refund lifecycle events; event labels are observations, not entitlement decisions. |
| P-09 | <https://docs.stripe.com/api/subscriptions/cancel> | Stripe cancellation timing and invoicing behavior are configurable provider operations, not refund or access authority. |
| P-10 | <https://docs.stripe.com/billing/invoices/subscription?lang=curl> | Stripe creates and advances subscription invoices; an invoice object does not establish UK tax correctness. |

### UK statute and official guidance

| ID | Official URL | Bounded fact used |
|---|---|---|
| L-01 | <https://www.legislation.gov.uk/uksi/2013/3134/regulation/29> | The Consumer Contracts Regulations 2013 establish cancellation rights for applicable distance/off-premises contracts. |
| L-02 | <https://www.legislation.gov.uk/uksi/2013/3134/regulation/30> | The applicable cancellation period is calculated under the statutory contract/supply classification; it is ordinarily 14 days. |
| L-03 | <https://www.legislation.gov.uk/uksi/2013/3134/regulation/34> | Applicable cancellation can require reimbursement, subject to statutory conditions and deductions. |
| L-04 | <https://www.legislation.gov.uk/uksi/2013/3134/regulation/36> | Early performance of a service during the cancellation period has request/information and proportionate-payment consequences. |
| L-05 | <https://www.legislation.gov.uk/uksi/2013/3134/regulation/37> | Digital-content cancellation treatment has separate prior-consent and acknowledgment conditions. |
| L-06 | <https://www.legislation.gov.uk/ukpga/2015/15/section/44> | The Consumer Rights Act 2015 provides a price-reduction remedy for qualifying digital-content breaches. |
| L-07 | <https://www.legislation.gov.uk/ukpga/2015/15/section/56> | The Consumer Rights Act 2015 provides a price-reduction remedy for qualifying service breaches. |
| L-08 | <https://www.gov.uk/online-and-distance-selling-for-businesses> | Distance sellers must provide clear pre-contract price, term, cancellation and early-use information in a durable form. |
| T-01 | <https://www.gov.uk/invoicing-and-taking-payment-from-customers/invoices-what-they-must-include> | General invoices have required identity, description, date and amount fields; VAT invoices have additional conditions. |
| T-02 | <https://www.gov.uk/guidance/record-keeping-for-vat-notice-70021> | Only VAT-registered businesses issue VAT invoices; taxable B2B supplies and invoice fields/timing/copy retention have specific requirements. |
| T-03 | <https://www.gov.uk/guidance/electronic-invoicing-notice-70063> | Electronic invoices remain subject to content, authenticity, integrity, legibility and customer-agreement requirements. |
| T-04 | <https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers> | Digital-service VAT depends on whether the supply is an e-service, customer status and location/place of supply; the guidance warns classification can require advice. |
| T-05 | <https://www.gov.uk/government/publications/price-transparency-cma209/providing-clear-and-accurate-information-about-prices-summary> | Consumer total-price presentation must include unavoidable fees and taxes and avoid drip pricing. |
| F-01 | <https://competitionandmarkets.blog.gov.uk/2026/04/17/direct-consumer-enforcement-one-year-on/> | As of retrieval, the CMA said the new DMCCA subscription-contract rules were expected in Spring 2027. |
| F-02 | <https://www.gov.uk/government/consultations/consultation-on-the-implementation-of-the-new-subscription-contracts-regime> | Secondary legislation/guidance was forthcoming for clearer pre-contract information, reminders, cancellation and refund mechanics. |
| F-03 | <https://www.gov.uk/guidance/writing-a-fair-contract-for-customers> | Current unfair-terms requirements remain relevant to subscription exit and customer remedies. |

The future-regime timing is time-sensitive and not activation evidence. A UK
consumer-law specialist must recheck commencement, regulations and guidance
against the actual launch date and customer footprint.

## Key 1 — `refunds`

### Established facts and classification

- **Founder authority:** `FD-W10-003` preserves mandatory statutory/consumer
  rights but explicitly leaves refunds unresolved. End-of-paid-period ordinary
  cancellation is not itself a refund answer (R-01, R-04).
- **Provider fact:** Stripe can execute bounded full/partial refunds, but refund
  availability and status do not state when Reserved owes or offers one (P-01).
  A credit note is a separate accounting primitive, not a customer-treatment
  decision (P-06).
- **External legal/finance evidence:** a reviewer must establish customer and
  supply classification, applicable cancellation/remedy rules, compliant
  pre-contract wording/express requests/acknowledgments, reimbursement timing,
  price-reduction handling, terms, tax/credit-note treatment and geographic
  scope (L-01–L-08, T-01–T-04, F-01–F-03).
- **Founder decision:** any discretionary promise beyond the verified mandatory
  minimum, and whether a confirmed full discretionary refund ends ordinary paid
  access, materially affect customer treatment and economics.

### Safest current engineering default

Until Q1 and specialist evidence are accepted, no ordinary automated or support
refund is enabled. A future flow must authenticate the current Reserved owner,
bind payment/subscription/period and exact money, enforce aggregate-refund limits,
use an idempotency key, separate requested/pending/requires-action/succeeded/
failed, record a redacted append-only audit trail, reconcile provider outcome,
and prevent any provider refund observation from directly granting, extending,
suspending or revoking access. Mandatory rights are never blocked by the absence
of a discretionary product policy; such requests require the legally approved
manual escalation path until implemented.

### Recommended Founder default and consequences

Recommend a simple consumer-favorable discretionary baseline, **subject to
legal/finance confirmation and always subordinate to mandatory rights**: accept
a request within 14 calendar days of an initial purchase or renewal for a full
refund; outside that window make no discretionary promise except duplicate/
erroneous charge, Reserved service failure or mandatory remedy. A confirmed
full refund of the payment funding the current period ends ordinary paid access;
a partial statutory price reduction does not automatically revoke it.

This is easier to explain and more compatible with the forthcoming subscription
direction, but increases refund exposure and needs controls against double
refund/dispute recovery. A narrower early-use deduction or different renewal
treatment could reduce cost but requires more complex compliant disclosure and
case handling. The recommendation is not adopted by this document.

### Closure evidence

Accepted Q1 answer; signed UK legal classification/terms/cancellation review;
finance/tax refund and credit-note treatment; exact customer copy; approved
operational authority/escalation; and later sandbox/target evidence for all
refund states. Until all applicable evidence exists, this key remains open.

## Key 2 — `tax_invoicing_and_additional_presentation`

### Established facts and classification

- **Founder authority:** `FD-W10-001` settles the three customer-facing totals
  as inclusive of VAT where applicable; `FD-W10-002` explicitly does not settle
  VAT/invoice treatment (R-01).
- **Engineering default:** show those exact total prices consistently and never
  add an unannounced VAT amount, infer a rate/applicability, enable a Stripe tax
  default, or call a receipt/invoice a VAT invoice without accepted facts.
- **Provider fact:** Stripe can create invoices, display tax IDs and support
  credit notes, but its fields/configuration do not prove entity registration,
  customer accuracy, place of supply, tax rate or legal invoice compliance
  (P-05, P-06, P-10).
- **External tax/legal evidence:** confirm Reserved's contracting entity and VAT
  registration, customer B2B/B2C status, supply classification, customer
  location/place of supply, registration obligations, applicable VAT treatment,
  invoice/credit-note fields and timing, electronic-invoice controls, retention
  and accounting (T-01–T-05).
- **Founder decision:** none is currently required. If specialist conclusions
  conflict with the settled inclusive totals or introduce materially different
  markets/prices, return the exact commercial choice to the Founder then.

### Safest current engineering default and closure evidence

Keep the total-price wording already authorised. Fail closed on checkout or
document issuance whenever the accepted tax profile cannot supply an exact
applicability/rate/treatment and compliant immutable invoice/credit-note facts.
Do not treat provider tax-ID validation or an invoice PDF as tax acceptance.

Closure needs signed finance/tax advice tied to the entity, product, customer
types and launch geography; approved invoice/receipt/credit-note schema and
copy; verified provider configuration; record-retention treatment; and target
examples. No Founder question is posed on current evidence.

## Key 3 — `paid_access_surface`

### Established facts and classification

The integration map records that authentication currently protects many routes
but is not a paid-entitlement gate (R-02). Accepted S5A supplies the exact route
inventory and provisional four-way classification; it supplies no Founder
decision or enforcement. This dossier binds its accepted identity recorded
above and does not reproduce its routes.

- **Engineering default:** enforce an accepted entitlement server-side on every
  approved paid product surface, including direct URL/API access; never rely on
  client hiding. Preserve existing auth/rate/CSRF controls independently. Keep
  internal/ambiguous surfaces out of customer access until reconciled.
- **Satisfied local evidence:** independent acceptance of the exact S5A
  inventory and its source-bound current route classification.
- **Remaining evidence:** reconciliation of the 11 internal/admin/legacy routes,
  followed by independent security/target review of future enforcement,
  route ownership and negative/bypass coverage.
- **Founder decision:** the product boundary—what the subscription buys and any
  route exceptions—is consequential customer/product scope.

### Recommended Founder default and closure evidence

Recommend S5A's proposed class boundary: every
`authenticated_product_candidate_pending_founder_decision` surface is paid
(including HICBC only if separately enabled); `public_infrastructure_auth_legal_support`
and `billing_purchase_return_recovery_candidate` remain outside the paid gate
while retaining existing controls; and
`internal_admin_unknown_requiring_reconciliation` remains excluded from
customer access pending route-by-route reconciliation.

Closure requires Q2 against the accepted, hash-bound S5A inventory, plus
reviewed server-side enforcement/bypass tests later. Inventory evidence alone
does not close this key.

## Key 4 — `billing_account_recovery`

### Established facts and classification

- **Founder/provider authority:** Stripe Customer Portal is provisional, but a
  portal session and billing email/provider customer ID do not authenticate a
  Reserved owner (R-01, R-08, P-02–P-04).
- **Engineering/security default:** only the currently authenticated Reserved
  owner may request a short-lived server-created portal session for the uniquely
  owner-bound billing account. Never accept a browser-provided provider customer
  ID as authority, use billing email as login identity, search/attach by email,
  merge/transfer accounts, or grant entitlement manually. Missing, duplicate,
  stale or cross-owner mappings fail closed and enter audited reconciliation.
  Loss of Reserved login uses the separately assured identity-recovery/support
  path; billing recovery cannot bypass it.
- **External security/privacy/operations evidence:** target identity-recovery
  assurance; support authentication and least privilege; owner-provider mapping
  lifecycle; email/change/collision and account-deletion behavior; session/return
  integrity; audit/redaction; incident and provider-outage recovery.
- **Founder decision:** none for this no-transfer October baseline. Cross-account
  transfer/merge, delegated/household/team billing or manual grants would be new
  consequential scope and must be separately proposed.

### Safest current engineering default and closure evidence

Keep all portal/recovery operations disabled until the owner mapping and target
controls are independently verified. A customer can retain access to ordinary
authentication, billing/recovery and required support/export surfaces only as
permitted by a future approved paid-surface boundary, but recovery never creates
entitlement.

Closure needs accepted security/privacy/operations evidence and target negative
tests for enumeration, session swapping, email collision/change, replay,
cross-owner access, deletion and support misuse. No Founder question is posed.

## Key 5 — `post_settlement_dispute_chargeback_reversal_consequences`

### Established facts and classification

- **Repository authority:** S3B and S4A admit only detached/reconciliation
  observations; post-settlement events have zero direct entitlement effect and
  the access consequence remains unresolved (R-07, R-08).
- **Provider fact:** Stripe may debit disputed funds/fees, exposes a multi-state
  bank-controlled dispute lifecycle, and may later withdraw or reinstate funds
  (P-07, P-08). These observations do not state Reserved's access outcome.
- **Engineering default:** later ingestion must verify source, owner, billing
  account, subscription, payment, paid period, amount/currency and event version;
  deduplicate and order safely; distinguish open/closed, full/partial,
  withdrawn/reinstated and won/lost; never grant or extend access from an
  ambiguous event. Unknown/contradictory cases reconcile without direct effect.
- **External legal/finance/security/operations evidence:** permitted consumer
  treatment/notice/appeal, fraud and support process, accounting, evidence
  submission, exact event/state matrix, provider deadlines, target reconciliation
  and replacement-payment behavior.
- **Founder decision:** suspension/restoration treatment after verified loss or
  reinstatement of the funds that support a current paid period is a material
  customer/economic-risk choice.

### Recommended Founder default and consequences

Recommend suspending ordinary paid-product access only after a verified **full
funds-withdrawn chargeback/dispute/reversal** tied to the payment funding the
current period. An open event without verified withdrawal, a partial event or an
ambiguous binding enters reconciliation: it cannot grant/extend access and does
not automatically suspend already-derived access. Verified funds reinstatement,
a win or a verified replacement payment restores only the access calculated by
the normal policy. Authentication, billing/recovery, support and legally
required export remain reachable.

This limits uncompensated access while reducing wrongful lockout from ambiguous
or partial observations. It still needs prompt customer notice, support/appeal,
fraud controls and exact finance/provider handling; delayed suspension increases
revenue exposure, while suspension on any dispute event increases wrongful
lockout and consumer-treatment risk. The recommendation is not adopted here.

### Closure evidence

Accepted Q3 answer; approved legal/finance/security/support treatment and copy;
accepted provider event matrix; sandbox sequences for open/withdrawn/partial/
won/lost/reinstated/replacement states; and target reconciliation/recovery tests.
Until then, this key remains open.

## Exact minimal Founder questions

These questions are deliberately limited to the three consequential choices.
They must be answered in an authoritative Founder record, not in this candidate.

### Q1 — discretionary refunds and confirmed-full-refund access

> Subject always to mandatory rights and accepted legal/finance wording, approve
> the October default of a full refund on request within 14 calendar days of an
> initial purchase or renewal; no discretionary promise outside that window
> except duplicate/erroneous charge, Reserved service failure or mandatory
> remedy; a confirmed full refund of the payment funding the current period ends
> ordinary paid access, while a partial price reduction does not automatically
> end it? If not, specify the request window, initial-versus-renewal treatment,
> exceptions and full/partial-refund access consequence.

### Q2 — exact paid-access class boundary

> For the October launch, approve server-side paid-entitlement enforcement on
> every route in `authenticated_product_candidate_pending_founder_decision`,
> while routes in `public_infrastructure_auth_legal_support` and
> `billing_purchase_return_recovery_candidate` remain outside that gate but keep
> their existing controls, and `internal_admin_unknown_requiring_reconciliation`
> remains excluded from customer access pending route-by-route reconciliation?
> If not, identify the exact route exceptions and intended treatment.

Q2 is attached to the independently accepted exact S5A commit, tree and
artifact hashes in R-09 and R-10. That evidence fixes the question's route-class
meaning but does not answer it or authorise enforcement.

### Q3 — verified post-settlement loss and restoration

> For the October launch, approve suspension of ordinary paid-product access
> only when a verified full funds-withdrawn chargeback, dispute or reversal is
> bound to the payment funding the current paid period; open-without-withdrawal,
> partial or ambiguous cases reconcile and neither grant nor extend access nor
> automatically suspend existing policy-derived access; verified reinstatement,
> win or replacement payment restores only policy-derived access; and
> authentication, billing/recovery, support and legally required export remain
> reachable? If not, specify the exact event, amount and state consequences.

There is intentionally no Founder question for tax-invoice implementation or
the no-transfer owner-bound recovery baseline. Those are specialist-assurance
gates under existing authority, not unanswered product preferences.

## Claims-to-source matrix

| Claim | Classification | Supporting source(s) | What the source does not establish |
|---|---|---|---|
| C-01: Exactly these five S2 keys remain unresolved. | Repository fact | R-02, R-04, R-05 | Any outcome for a key. |
| C-02: Ordinary cancellation and the seven-day failed-renewal path are settled; refunds and post-settlement consequences are not. | Founder authority | R-01, R-04, R-06 | Mandatory-right classification or discretionary policy. |
| C-03: Stripe supports full/partial refunds and asynchronous/failing refund states. | Provider fact | P-01, P-08 | When Reserved must/should refund or access consequences. |
| C-04: UK cancellation and breach remedies may apply and depend on supply/contract facts and compliant disclosures/consents. | Statutory issue requiring legal application | L-01–L-08, F-03 | Whether Reserved is a service, digital content or another class; an approved policy. |
| C-05: The three prices remain consumer-facing VAT-inclusive totals. | Founder authority plus official price-transparency support | R-01, T-05 | VAT registration, rate, place of supply or invoice compliance. |
| C-06: VAT invoice duties depend on registration, customer/supply facts and required content/records. | Tax evidence requiring specialist application | T-01–T-04 | Reserved's actual tax treatment. |
| C-07: Stripe invoice, tax-ID and credit-note features are implementation capabilities only. | Provider fact | P-05, P-06, P-10, R-08 | Legal/tax correctness or approved customer copy. |
| C-08: The paid surface requires an accepted exact inventory and Founder-settled product boundary. | Repository/product decision | R-02, R-09, R-10 | A Founder answer, enforcement or launch evidence. |
| C-09: Portal access must derive from Reserved identity; billing email is not login authority. | Provider/security fact and engineering default | P-02–P-04, R-08 | Target identity-recovery/security assurance. |
| C-10: No account transfer/merge/manual grant is the safe launch baseline. | Ordinary fail-closed engineering default | R-05, P-04 | Future household/team/delegated-account product policy. |
| C-11: Disputes can withdraw/reinstate funds through provider states. | Provider fact | P-07, P-08 | Reserved access, legal, notice or appeal consequences. |
| C-12: Provider observations have zero direct entitlement authority. | Integrated repository contract | R-01, R-06–R-08 | A final reconciled consequence. |
| C-13: New UK subscription rules require a launch-date recheck. | Time-sensitive official future-law evidence | F-01, F-02 | Commencement/applicability at activation or final compliant design. |
| C-14: Q1–Q3, not VAT/recovery implementation detail, are the present consequential Founder choices. | Reconciliation under `FD-OA-001` | R-01–R-08, C-01–C-13 | An answer, acceptance or implementation. |

## Result and next evidence package

W10-S2 remains **incomplete** and the strict W10 denominator remains **0/8**.
This candidate does not close or round up any key. Founder action is genuinely
required for Q1, Q2 and Q3; it is not presently required for the VAT/invoice or
owner-bound no-transfer recovery defaults.

The smallest non-policy work that can proceed immediately is specialist
evidence for the enumerated legal/tax and security/operations gates, alongside
route-by-route reconciliation of S5A's internal/admin/legacy class without
changing runtime behavior. Record Q1–Q3 in Founder authority only when answered,
then produce one accepted S2 closure artifact that binds the accepted S5A
identity, specialist sign-offs, exact policy versions and all fifteen S2 keys.
Provider configuration, runtime implementation and activation remain separate
later packages.

## Post-entitlement-core evidence reconciliation

R-06 remains the exact historical evidence reviewed by S2C. Hardened S3A
evidence is accepted at source checkpoint `b990d514a929c37b3f999137a0e383d05c37f0df`,
integrated as `48a97042fc0e17997bf2d23a4687e79c20b74b9e`, with current SHA-256
`fafd93c1a8fa65428bd3af19c1f35e9b47b10f38f68312721e6f2a5e14943f0d`.
It documents detached zero-authority structural lifecycle candidates and fixed
history/date behaviour. It answers none of Q1/Q2/Q3, changes no denominator,
and closes no provider, target, persistence or activation evidence.
