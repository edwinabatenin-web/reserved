# QuickBooks Q-S5 — UK VAT contract evidence boundary

Status: uncommitted, network-inert evidence reconciliation candidate. This
package resolves only the provider-contract evidence boundary for the
already-existing narrow Q-S5A representation. It is not a continuation of any
other lane, not an implementation, and not authority to expand VAT. QuickBooks
remains disabled.

## 1. Scope and immutable retrieval identity

- Workstream/package: `reserved-quickbooks-qs5-uk-vat-evidence`.
- Branch: `ohds/quickbooks-qs5-uk-vat-evidence`.
- Immutable base HEAD: `4d48fe27917ef7ae3f48df8fd75a5685ec5e95d5`.
- Retrieval date: `2026-09-01`.
- Permitted paths only:
  - create `docs/QUICKBOOKS_QS5_UK_VAT_CONTRACT_EVIDENCE.md` (this file);
  - minimally update `docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md` only if a newly
    verified stable mechanical fact warrants binding;
  - minimally update `tests/test_quickbooks_qs5_provider_facts.py` only for any
    newly bound mechanical fact;
  - minimally update `docs/QUICKBOOKS_COMPLETION_MAP.md` to state the QBO-01
    boundary.

Scope is confined to establishing, or explicitly leaving unresolved, the
official provider-evidence status of the VAT/transaction-tax fields already
touched by Q-S5A. It does not broaden Q-S5A, define a VAT product, implement VAT
logic, or turn provider tax fields into tax/accounting conclusions. Accounting
write-back, bookkeeping correction, invoice creation, tax-return submission,
full MTD filing, VAT expansion and Corporation Tax are out of scope for October
and are not exercised here.

## 2. Dated official source register

All URLs are current official Intuit/QuickBooks Developer documentation. Each
was requested read-only on 2026-09-01 with `HTTP 200`.

| # | Subject | Exact official URL | Retrieved | Purpose |
|---|---|---|---|---|
| S1 | Invoice schema/reference | `https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/invoice` | 2026-09-01, HTTP 200 | Field presence, role, and required/optional/read-only/conditional status for the Invoice object and its transaction-tax members |
| S2 | Non-US automated sales tax workflow (already cited by Q-S5A) | `https://developer.intuit.com/app/developer/qbo/docs/workflows/calculate-sales-tax/automated-sales-tax-for-non-us-locales` | 2026-09-01, HTTP 200 | Non-US `GlobalTaxCalculation`, `TaxCodeRef`, `TxnTaxDetail.TotalTax`, TaxLine `Amount`/`NetAmountTaxable`, `DetailType`/`PercentBased`/`TaxRateRef`/`TaxPercent`, override descriptions, subtotal behaviour, and the GBP/VAT worked example |
| S3 | Minor versions | `https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/minor-versions` | 2026-09-01, HTTP 200 | Re-verify whether minor 75 remains accepted/default on the retrieval date |

Supporting already-retained sources (not re-inspected here and not central to
the VAT boundary) remain exactly as recorded in
`docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md`: Payment, data queries, and change-data
capture.

### Retrieval record (rendered read-only inspection, not a durable byte export)

The three pages above were independently inspected read-only on 2026-09-01 as
rendered current official pages; the inspection result is not an `HTTP 200`
application shell treated as substantive. The rendered field/reference wording
was read from the current pages on the retrieval date and is the current-source
evidence for the corrections below.

No page checksum or durable byte export of the rendered HTML/JSON was retained,
and none is claimed here. The rendered current source is therefore kept distinct
from the earlier retained summaries in
`docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md` and
`docs/QUICKBOOKS_QS5_ADAPTER_EVIDENCE.md`, each carrying its own 2026-09-01
inspection record and not re-derived here.

Consequences, applied strictly throughout this document:

- Only wording independently read from the rendered current pages is treated as
  current-source evidence; nothing is invented from memory.
- Where the current source does not establish a field's documented
  presence/optionality, that field is labelled unresolved rather than filled in.
- The rendered current source is distinguished from the earlier retained
  summaries; where a fact comes from the current source rather than those
  summaries, that provenance is stated.

## 3. Field / optionality matrix

Source levels: **schema** = current Invoice reference; **workflow** = current
non-US automated-sales-tax workflow; **example** = worked example shape only.
Q-S5A's stricter cardinality, exact reconciliation, accepted currency/mode, and
business interpretation are recorded separately in section 4.4 as **Reserved
inference**, not as field-presence facts.

UK/non-US applicability: **generic non-US** (non-US company, not UK-specific);
**generic** (not locale-qualified); **example** (GBP/VAT example shape only).

Minor-version status (all rows): the current minor-versions page records that
minor version 75 remains accepted/default, that requests below 75 are treated
as 75, and that omission defaults to 75. No current source documents a
field-by-field v75 change history, so no row asserts one.

| Field | Retained role | Required / optional / etc. | Source level | UK/non-US applicability |
|---|---|---|---|---|
| `GlobalTaxCalculation` | Transaction-tax computation mode for the invoice | Required for non-US companies; allowed values `TaxExcluded`, `TaxInclusive`, `NotApplicable` | schema | generic non-US |
| `CurrencyRef` | Invoice currency reference | Conditional on multicurrency | schema | generic |
| `TotalAmt` | Invoice total | Read-only; includes charges, allowances, and taxes | schema | generic |
| `HomeTotalAmt` | Home-currency total | Read-only/system-defined; includes charges, allowances, and taxes; valid when `CurrencyRef` is present; applicable with multicurrency | schema | generic |
| `TxnTaxDetail` | Transaction-level tax detail container | Optional; ignored / not stored if sales tax is disabled | schema | generic non-US |
| `TxnTaxDetail.TotalTax` | Transaction tax total | Documented in the non-US workflow and described for overrides; Q-S5A requires it | workflow | generic non-US |
| `TxnTaxDetail.TaxLine` (transaction-level) | Per-rate tax lines | Documented in the non-US workflow; Q-S5A requires exactly one | workflow | generic non-US |
| `TaxLine.Amount` | Tax amount for the line | Documented in the non-US workflow and described for overrides; Q-S5A requires it | workflow | generic non-US |
| `TaxLine.DetailType` = `TaxLineDetail` | Tax line discriminator | Shown in the current non-US worked example; Q-S5A requires the literal value `TaxLineDetail` | example | example |
| `TaxLineDetail.PercentBased` | Percentage-vs-amount tax discriminator | Shown in the current non-US worked example; Q-S5A requires `true` | example | example |
| `TaxLineDetail.NetAmountTaxable` | Net amount subject to the line's tax | Documented in the non-US workflow; Q-S5A requires exact equality with the net line | workflow | generic non-US |
| `TaxLineDetail.TaxRateRef` / `.value` | Tax-rate reference | Shown in the current non-US worked example and described for overrides; Q-S5A retains it only as provenance, never interpreted as an accounting/item category | example | example |
| `TaxLineDetail.TaxPercent` | Tax percentage in provider units | Shown in the current non-US worked example and described for overrides; optional in Q-S5A; converted to fractional rate only on exact reconciliation | example | example |
| `SalesItemLineDetail.TaxCodeRef` / `.value` | Line-level provider VAT/tax code | Documented in the non-US workflow; Q-S5A requires it and retains it as the canonical `vat_code` string | workflow | generic non-US |
| `SubTotalLineDetail` (terminal subtotal) | Subtotal behaviour | Documented in the non-US workflow; Q-S5A accepts at most one terminal subtotal and requires it to equal the net economic line without double counting | workflow | generic non-US |

## 4. Fact / example / Reserved defensive policy / inference / unresolved register

### 4.1 Schema/reference facts (current, generic unless noted)

- `GlobalTaxCalculation` is required for non-US companies and permits exactly
  `TaxExcluded`, `TaxInclusive`, or `NotApplicable`.
- `CurrencyRef` is conditional on multicurrency.
- `TotalAmt` is read-only and includes charges, allowances, and taxes.
- `HomeTotalAmt` is read-only/system-defined, includes charges, allowances, and
  taxes, is valid when `CurrencyRef` is present, and is applicable with
  multicurrency.
- `TxnTaxDetail` is optional and ignored / not stored if sales tax is disabled.

These establish the *container*, *mode*, and *money-total* semantics, not UK VAT
meaning.

### 4.2 Workflow facts (current, generic non-US)

The non-US automated-sales-tax workflow (S2) documents line `TaxCodeRef`,
`TxnTaxDetail.TotalTax`, transaction-level `TaxLine` `Amount` and
`NetAmountTaxable`, `GlobalTaxCalculation == TaxExcluded`, and subtotal
behaviour. The same current workflow/example explicitly shows
`DetailType == "TaxLineDetail"`, `PercentBased`, `TaxRateRef`, and `TaxPercent`
on the tax line, and describes `TotalTax`, `TaxRateRef`, line `Amount`, and
`TaxPercent` for overrides. These are the narrow non-US tax representation, not
a UK VAT rule set.

### 4.3 Worked example and override narrative (current, example shape only)

The workflow supplies a main GBP/VAT example that contains three sales lines
and two tax lines, not Q-S5A's narrow single-line shape. The workflow's
override narrative/request describes £8.90 tax on £89 at 10%, while the shown
response retains £8.90 and £89 but reports `TaxPercent: 20` — a
percentage/arithmetic contradiction. These example shapes are evidence only for
themselves; they are **not generalised** into universal UK semantics, do not
prove universal emission of Q-S5A's exact shape, and do not prove that every UK
company supplies tax detail. Q-S5A's exact arithmetic correctly rejects the
contradictory override response.

### 4.4 Reserved defensive policy / conservative inference (Q-S5A decisions)

Reserved inference applies only to Q-S5A's stricter cardinality, exact
reconciliation, accepted currency/mode, and business interpretation — not to
the field-presence facts classified above. These are Q-S5A implementation
decisions, not claims about every valid QuickBooks record:

- Only `GlobalTaxCalculation == TaxExcluded` is accepted.
- GBP is the only accepted currency (the only code in the reviewed example).
- Missing and null are never defaults; currency, dates, totals, IDs, revisions,
  tax references and tax detail must be explicit.
- Exactly one `SalesItemLineDetail` economic line, one terminal `SubTotalLineDetail`
  (non-economic, equal to net), one `TaxLine`, one percentage tax line.
- `TaxCodeRef.value` is retained as the provider VAT code.
- `TaxRateRef.value` is retained only in provenance/source evidence and is not
  treated as an accounting/item category.
- `TaxPercent` is converted from provider percentage units to a fractional rate
  only when it reconciles exactly with taxable net and tax amount; never rounded
  or inferred when absent.
- Money is exact integer/`Decimal`, finite, nonnegative, at most two decimals.
- Arithmetic must reconcile exactly: `NetAmountTaxable == net`,
  `TaxLine.Amount == TotalTax`, `net + TotalTax == TotalAmt`.

### 4.5 Unresolved (not established by any cited source)

- UK-specific optionality: zero-rated, exempt, outside-scope, reverse-charge,
  inclusive-tax, multi-rate, rounding, currency/FX, and any jurisdiction-specific
  VAT meaning. None is proven by the cited sources.
- An absent field's zero / not-applicable / completeness meaning: no source
  proves one. Q-S5A treats absence as fail-closed, never as zero or complete.
- Stable canonical business meaning of provider tax-code / tax-rate identifiers:
  `TaxCodeRef` and `TaxRateRef` are retained as opaque provider strings; no
  source establishes a stable mapping suitable for canonical tax interpretation.
- Field-by-field v75 change history: unresolved. The current minor-versions page
  records that minor version 75 remains accepted/default, requests below 75 are
  treated as 75, and omission defaults to 75, but it does not document a
  field-by-field v75 change history (including for `HomeTotalAmt`).

## 5. Consistency review against existing Q-S5 evidence

Reviewed against `docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md`,
`docs/QUICKBOOKS_QS5_ADAPTER_EVIDENCE.md`, `docs/QUICKBOOKS_QS5_SYNC_EVIDENCE.md`,
`docs/QUICKBOOKS_QS4_OBSERVATION_EVIDENCE.md`, `docs/QUICKBOOKS_COMPLETION_MAP.md`,
and `docs/DESIGN_QUESTIONS.md`.

- **Provider-facts**: consistent. It already records `GlobalTaxCalculation`
  (required non-US; `TaxExcluded`/`TaxInclusive`/`NotApplicable`), `CurrencyRef`
  (conditional), `TotalAmt` (read-only), `TxnTaxDetail` (optional/ignored), and
  that the provider documents "do not alone prove every UK VAT field or business
  rule". This document does not alter that retained contract.
- **Q-S5A adapter evidence**: consistent. It already states the cited page
  supports the exact non-US tax representation while not proving every UK VAT
  configuration, and that QBO-01 remains open. This document refines the
  field-level source labelling (schema vs workflow vs example) and records that
  the current workflow/example explicitly shows
  `TaxLineDetail`/`PercentBased`/`TaxRateRef`/`TaxPercent`, reserving Reserved
  inference for Q-S5A's stricter cardinality, exact reconciliation, accepted
  currency/mode, and business interpretation.
- **Q-S5B sync evidence and Q-S4 observation evidence**: no conflict; they
  concern sync mechanics and observation capture, not VAT optionality.
- **Completion map**: consistent; it keeps Q-S5A locally checkpointed and does
  not claim implementation/launch/activation. This document's disposition is a
  planning-map boundary, not a completion claim.
- **DESIGN_QUESTIONS QBO-01**: remains `open` with `Answer: pending`. This
  document does not close QBO-01 for broader UK VAT; confirmation of broader UK
  VAT semantics, universal UK emission of Q-S5A's exact shape, and exact v75
  field history remains outstanding. The narrow Q-S5A boundary is sufficient
  for its exact shape only.

The current-source contradiction now recorded here is Intuit's own worked
override example: the override narrative/request describes £8.90 tax on £89 at
10%, while the shown response retains £8.90 and £89 but reports `TaxPercent:
20`. The main GBP example also contains three sales lines and two tax lines,
not Q-S5A's narrow single-line shape. These are consistent with the existing
evidence, which already scopes Q-S5A to a single reviewed non-US example shape
and rejects shapes it cannot reconcile exactly; the source therefore does not
prove universal emission of Q-S5A's exact shape.

## 6. Exact Q-S5A supported shape and fail-closed cases

The supported shape (implemented in
`reserved/providers/accounting/quickbooks_invoice_payment_adapter.py`, tested in
`tests/test_quickbooks_invoice_payment_adapter.py`) is:

- Invoice: exact Q-S4 `InvoiceObservation`; `GlobalTaxCalculation == TaxExcluded`;
  explicit `TxnDate`; `CurrencyRef.value == "GBP"`; explicit read-only `TotalAmt`;
  exactly one `SalesItemLineDetail` economic line (net `Amount`, explicit
  `TaxCodeRef.value`) and at most one terminal `SubTotalLineDetail` equal to net;
  `TxnTaxDetail` with `TotalTax`, exactly one `TaxLine`
  (`DetailType == "TaxLineDetail"`, `PercentBased == true`, `NetAmountTaxable`,
  `TaxRateRef.value`, optional `TaxPercent`) with exact
  `NetAmountTaxable == net`, `TaxLine.Amount == TotalTax`, `net + TotalTax == TotalAmt`.
- Payment: exact Q-S4 `PaymentObservation` linked to that invoice; explicit
  `TxnDate`; `CurrencyRef.value == "GBP"`; exactly one Payment `Line` with one
  `Amount` and exactly one `LinkedTxn` of `TxnType == "Invoice"` matching the
  invoice ID; exact `Amount + UnappliedAmt == TotalAmt`; one PAYMENT allocation.

Everything else fails closed, including (not exhaustive): `TaxInclusive` or
`NotApplicable`; absent/unknown currency, date, totals, or tax detail; zero or
multiple economic lines; discounts, shipping, groups, description-only or other
roles; non-terminal or mismatched subtotals; multiple tax lines; non-percentage
tax; any net/tax/total mismatch; negative/non-finite/float/over-precision money;
missing/duplicate/unstable identifiers; multi-rate, inclusive, zero-rated,
exempt, outside-scope, reverse-charge, FX, credit-memo, refund, or
multi-document payment cases; unknown invoice IDs; duplicate invoice/payment
IDs; and any currency/customer/user/realm/connected-organisation or allocation
mismatch.

## 7. QBO-01 disposition

```
Current official evidence supports the tax-field presence used by the existing conservative Q-S5A representation, but does not prove universal UK emission, exact v75 field history, or broader UK VAT semantics. Intuit's worked override example contains a percentage/arithmetic contradiction that Q-S5A correctly rejects. QBO-01 and all activation gates remain open.
```

The rendered current official Invoice and non-US automated-sales-tax sources
support the tax-field presence that the existing conservative Q-S5A
representation already uses, but do not prove universal UK emission of its exact
shape, exact v75 field history, or broader UK VAT semantics (inclusive,
zero-rated, exempt, outside-scope, reverse-charge, multi-rate, rounding, FX, or
jurisdiction-specific meaning). The worked override example's
percentage/arithmetic contradiction is rejected by Q-S5A's exact arithmetic.
Resolving this narrow evidence question does not implement, integrate, launch,
or activate QuickBooks or VAT expansion.

## 8. Residual gates

Unchanged and still open:

- QBO-01 broader UK VAT semantics: external confirmation of broader UK VAT
  optionality (inclusive, zero-rated, exempt, outside-scope, reverse-charge,
  multi-rate, rounding, FX, jurisdiction-specific), universal UK emission of
  Q-S5A's exact shape, and exact v75 field history (DESIGN_QUESTIONS QBO-01).
- QBO-02 (UK CIS/subcontractor deductions) and QBO-03 (class/location/project/
  custom-field editions): untouched.
- Q-S2 HTTP/secret-custody, Q-S3 authenticated callback/route integration,
  broader Q-S5 pagination/incremental-sync and operational ingestion, and all
  Q-S6 sandbox, monitoring/recovery, privacy/security, independent-assurance,
  enablement, and launch gates.

Exact next package — required only if broader UK VAT is pursued, and only as an
evidence-acquisition package, not an implementation package: obtain a written
Intuit confirmation (or current official wording) that establishes broader UK
VAT optionality, universal UK emission of Q-S5A's exact shape, and exact
field-by-field v75 history for the pinned version, before any adapter is
broadened. Nothing here authorises that next package or any VAT expansion.
