# W10-S2E tax/invoice prerequisite evidence contract

## Result and boundary

W10-S2E is a pure, immutable, I/O-free prerequisite contract. It preserves the
Founder-settled gross catalogue and records what a future tax, invoice, receipt
and credit-note implementation is **not** yet authorised to do. It is not legal
or tax assurance, does not close the W10-S2 tax/invoice policy key, and does not implement W10-S6.

The contract calculates no VAT, makes no customer, supply, registration or
place-of-supply determination, issues or stores no document, performs no SDK or
network call, accepts no credential or provider configuration, and changes no
entitlement, route or customer journey.

## Exact integration and repository evidence

The candidate is based on clean integration commit
`54a82476939dce8f75af62d73aeb477e11a1260c`, tree
`26b1aa6a1302195770534dc41caf099bcdd7cb06`.

| Evidence | Path | SHA-256 | Bounded use |
|---|---|---|---|
| Founder authority | `FOUNDER_DECISIONS.md` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | `FD-W10-001/2026-09-02/v1`; gross catalogue and qualified VAT statement only |
| Catalogue contract | `reserved/billing/contracts.py` | `9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b` | W10-S1A plan keys, exact price authority, and non-calculation boundary |
| Authority boundary | `docs/W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md` | `e5911c70199727beba888175f5f31a208a4418eb16cae7978e8b52fa57d688ce` | contract-only, no VAT inference |
| Specialist-gate dossier | `docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md` | `db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd` | candidate evidence, not legal/tax acceptance |

These are build-time evidence bindings. The module performs no runtime file
read. A changed source requires explicit reconciliation and independent review.

## Exact safe catalogue semantics

The only customer-price statement retained is:

> inclusive of VAT where applicable

The exact catalogue is:

| Plan key | Exact gross GBP minor units | Cadence | Simplified-invoice amount limb | Simplified-invoice authority |
|---|---:|---|---|---|
| `monthly` | `2900` | 1 month | true | false |
| `six_month` | `15600` | 6 months | true | false |
| `yearly` | `28800` | 1 year | false | false |

“Amount limb only” means that £29 and £156 are no more than the current £250
simplified-invoice threshold described by HMRC. It does not establish supplier
VAT registration, customer agreement or status, geography, taxability, rate,
required fields, or permission to issue anything. £288 does not satisfy that
amount limb. All three remain unauthorised for simplified-invoice issuance.

The contract has no VAT rate, net amount, or VAT amount and provides no way to
derive one. It rejects a gross amount that differs from the settled catalogue,
including an amount with tax added on top or a discounted amount.

## Neutral document candidates

The three concepts are deliberately distinct:

- `payment_receipt_candidate` is a neutral acknowledgement candidate for a
  verified payment; it is not a live receipt or VAT invoice.
- `invoice_candidate` is a neutral gross-only shape candidate; it is not a VAT
  invoice.
- `credit_note_candidate` is available only as an append-only correction linked
  to an exact original candidate; it is not a VAT credit note and does not
  decide a refund or tax disposition.

Candidate constructors accept only an owner reference, exact settled plan/gross
amount/currency, exact built-in `datetime` with `timezone.utc`, and a sanitised
opaque evidence reference. They do not accept VAT rates or amounts, supplier or
customer VAT IDs, customer status or location, place of supply, a provider
zero-tax result, tax-document labels, or an entitlement effect.
Their positional and named call shapes are validated inside metadata-independent
dispatch, so mutating callable defaults cannot supply authority or mandatory
facts.

Corrections require a unique correction ID, an exact link to the original
document ID, and a strictly later UTC `recorded_at` than the complete existing
chain. The prior candidate value remains unchanged. Each candidate and correction has
zero direct entitlement effect, zero provider-observation tax-document effect,
and false live-render/delivery and VAT-document status.

## Authorities fixed false

The following remain false:

- VAT calculation, net derivation and VAT-amount derivation;
- VAT-invoice and simplified-invoice issuance;
- Stripe Tax activation;
- refund/credit-note tax disposition;
- live receipt rendering or delivery;
- provider-observation tax-document or entitlement effect; and
- candidate-document entitlement effect.

Stripe producing zero tax, an invoice object, a PDF, or a rendered tax ID does
not change any flag. Provider observations are evidence requiring specialist
and application reconciliation, never tax, document, or entitlement authority.

## Future specialist inputs and production gates

No externally supplied tax fact is accepted here. A later, separately reviewed
authority must provide effective-dated facts for the contracting supplier and
address; establishment and VAT registration status/number; supply taxability,
rate and digital-service classification; customer business/private status;
customer location/place of supply and supported geography; tax-point/accounting
scheme; invoice/receipt/credit-note fields, numbering, timing and request policy;
Stripe registration/tax-code/price-behaviour/location configuration; and the
field-level retention, erasure, legal-hold and backup-expiry policy.

Production remains gated on accepted finance/accounting VAT evidence; tax/legal
supply, customer and geography classification; approved document schema and
copy; privacy/security minimisation and retention design; accepted W9 retention,
erasure, legal-hold, backup and custody evidence; reviewed Stripe sandbox
configuration and sample artifacts; target reconciliation/audit/access/recovery
and operations evidence; and separate Founder production activation/release
authority.

Q1 (refunds), Q2 (paid-access surface), and Q3 (post-settlement
dispute/chargeback/reversal consequences) remain exactly unresolved. This
contract answers none of them. No new Founder question is asserted: specialist
evidence should return to the Founder only if it creates a material price or
launch-scope choice.

## Official source register

These sources support bounded rules or provider capabilities for specialist
review. Their inclusion is not legal or tax assurance and does not determine
Reserved's actual facts.

| Source | URL | Bounded finding |
|---|---|---|
| CMA consumer price transparency | <https://www.gov.uk/government/publications/price-transparency-cma209/providing-clear-and-accurate-information-about-prices-summary> | Consumer total prices include reasonably calculable mandatory taxes/charges; periodic/minimum-term presentation differs. |
| GOV.UK VAT registration | <https://www.gov.uk/register-for-vat> | Registration depends on actual turnover/forecast, establishment and voluntary status. |
| HMRC VAT Notice 700 | <https://www.gov.uk/guidance/vat-guide-notice-700> | VAT-invoice duty/content/timing, simplified-invoice conditions, and credit-note rules are conditional. |
| HMRC VAT record keeping | <https://www.gov.uk/charge-reclaim-record-vat/keeping-vat-records> | Only VAT-registered businesses issue VAT invoices; record retention depends on the applicable scheme. |
| HMRC continuous supply/tax point | <https://www.gov.uk/guidance/vat-instalments-deposits-credit-sales> | If continuous-service classification applies, invoice/payment timing controls tax point. |
| HMRC digital services | <https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers> | Treatment depends on service, customer status and location, with cross-border evidence requirements. |
| HMRC electronic invoicing | <https://www.gov.uk/guidance/electronic-invoicing-notice-70063> | Authenticity, integrity, legibility, agreement, audit and storage controls are conditional requirements. |
| Stripe Tax setup | <https://docs.stripe.com/tax/set-up> | Stripe capability depends on merchant-supplied registrations, tax code, price behaviour and location facts. |
| Stripe hosted invoice page | <https://docs.stripe.com/invoicing/hosted-invoice-page> | Stripe can host invoice and receipt PDFs; this is capability, not tax authority. |
| Stripe tax IDs | <https://docs.stripe.com/tax/invoicing/tax-ids> | Stripe can render configured tax IDs; configuration is not legal/tax acceptance. |

## Integrity and scope assurance

The contract and document candidates are detached exact built-in immutable
structures. Validation establishes only local structural and semantic
consistency; it is explicitly not provenance, authentication, issuance, legal
authority, tax authority, provider authority, delivery authority, or entitlement
authority. A caller can independently reconstruct an equivalent value, so no
producer-issued or unforgeable admission claim is made. There are no mutable
issuance registries. Modified catalogue facts, true authority/status fields,
stateful/custom timezone input, unsafe identifier content,
unlinked/backdated/non-increasing corrections, and enabling-field injection fail
closed.

There is no provider SDK, network, credential, configuration, database, file or
runtime I/O; no webhook parsing; no route, template, checkout, refund, discount,
document delivery, persistence, entitlement, access enforcement, or activation.
This is neither tax implementation nor W10-S2/W10-S6 completion.
