# Xero X-S2 invoice evidence and mapping contract

Evidence observation date: **1 September 2026**. This package uses only the
official facts supplied to the worktree and reviewed provider-neutral Reserved
contracts. No page was browsed during implementation and no Xero account,
credential, token, environment variable, sandbox, customer record or network
request was used.

## Supplied official facts

- [Accounting API — Invoices](https://developer.xero.com/documentation/api/accounting/invoices):
  `GET /api.xro/2.0/Invoices` retrieves sales invoices and purchase bills.
  Collection responses normally contain contact summaries without line detail;
  individual invoice, `Statuses` and paged queries return line detail.
  `summaryOnly=true` excludes `Payments`, `HasAttachments`, `LineItems` and
  `CISDeduction`. Amounts are in invoice currency. Reviewed invoice fields
  include `Type`, `Contact`, `Date`, `DueDate`, `Status`, `LineAmountTypes`,
  `LineItems`, `SubTotal`, `TotalTax` and the other fields on that page. Reviewed
  line fields include `Description`, `Quantity`, `UnitAmount`, `ItemCode`,
  `AccountCode`/`AccountId`, `Item`, `LineItemID`, `TaxType`, `TaxAmount`,
  `LineAmount`, `DiscountRate` and `Tracking`.
- [Accounting API — Types](https://developer.xero.com/documentation/api/accounting/types/):
  invoice types are exactly `ACCPAY` (supplier bill) and `ACCREC` (sales
  invoice); statuses are `DRAFT`, `SUBMITTED`, `DELETED`, `AUTHORISED`, `PAID`
  and `VOIDED`; line amount types are `Exclusive`, `Inclusive` and `NoTax`.
- [Rounding in Xero](https://developer.xero.com/documentation/guides/how-to-guides/rounding-in-xero/):
  `UnitAmount` defaults to two decimal places and may opt into four with
  `unitdp=4`; summary values such as `Total` and `LineAmount` remain two decimal
  places.

These facts are source assertions, not tax decisions. In particular, a Xero
status does not establish settlement, a `TaxType` does not establish canonical
tax treatment, and no invoice field establishes taxable profit or liability.

## Enforced detailed-response boundary

`parse_detailed_invoice_response` accepts an object containing only an
`Invoices` array with exactly one item. The invoice must contain `InvoiceID`,
`Type`, `Contact`, `Date`, `Status`, `LineAmountTypes`, `LineItems`, `SubTotal`,
`TotalTax`, `Total` and `CurrencyCode`. `LineItems` must be present and non-empty,
and each line requires `LineItemID`, `LineAmount` and `TaxAmount`. Consequently,
an empty/list collection response, ordinary collection summary, or
`summaryOnly=true` result cannot silently become complete evidence.

The parser preserves optional absent and explicit-null fields separately from
zero. Unknown additive invoice and line field names are recorded but receive
no semantics. Missing, explicit-null and empty-array `Tracking` all produce the
same empty immutable value while absent/null metadata preserves their source
distinction. Raw payloads are not retained. A provider-local, recursively
type-tagged canonical digest binds the transient source representation to
immutable Xero/connection/tenant/import provenance. It preserves distinctions
between strings, integers, booleans, exact `Decimal` representations, nulls,
arrays and objects while sorting object keys. The existing shared observation
types are constructed directly; the shared contract and normaliser are
unchanged. Top-level `source_fields` remain exactly the observed Xero invoice
field names. Errors identify only a field or violated rule and do not echo
source values.

Exact JSON numbers must reach this boundary as JSON integers or `Decimal`
values (for example by a future transport using `parse_float=Decimal`). Python
`float`, numeric strings, booleans, non-finite decimals and magnitudes above
`10^18` are rejected. `UnitAmount` permits at most four decimal places;
`LineAmount`, `TaxAmount`, `SubTotal`, `TotalTax` and `Total` permit at most two.
Every accepted object boundary, including nested `Item` and `Tracking` objects,
requires string keys before presence metadata, freezing, ordering or digesting.

Opaque `Item` and `Tracking` evidence is immutable and bounded independently of
invoice line limits: maximum nesting depth 16, total 10,000 nodes, 1,000 entries
per individual array/object, and 4,096 characters per string or object key.
Opaque decimals must be finite and have absolute magnitude no greater than
`10^18`; opaque integers use the same magnitude bound. Unsupported Python
objects fail closed. The canonical source digest also bounds depth, total nodes,
individual containers, 4,096 Unicode characters / 16,384 UTF-8 bytes per
string or key, integer magnitude and cumulative encoded bytes. Invalid Unicode
is rejected before hashing, so hostile additive source content produces a controlled
non-echoing contract error rather than unbounded work or a runtime escape.

## Mapping into the existing neutral v3 contract

- `ACCREC` maps to candidate `INVOICE` / `RECEIVABLE`; `ACCPAY` maps to
  candidate `BILL` / `PAYABLE`.
- Xero `Status`, `Type`, `LineAmountTypes` and contact identity remain explicit
  provider assertions. No canonical lifecycle, settlement, recognition,
  allowability, VAT category, payment or tax decision is emitted.
- `InvoiceID`, connection identity and tenant identity remain distinct. The
  tenant is the neutral business identity and the X-S1 connection id is the
  connected-organisation identity.
- Invoice totals map to gross/net/tax candidate amounts in invoice currency.
  Each line maps into neutral line gross plus a net/tax/gross breakdown while
  retaining the raw tax type only as `vat_code`; it is not interpreted.
- `AccountID`/`AccountId` is preferred as the provider account identity; when
  absent, observed `AccountCode` is retained there. Supplying both spellings is
  rejected as ambiguous. `ItemCode` is retained as a provider
  category identifier only, without category or tax semantics. Tracking is
  retained on the validated source record and is not guessed into neutral
  allocation identifiers.

## Reserved implementation inferences (not Xero facts)

The existing neutral contract needs stronger conditions than the supplied
field catalogue alone states. X-S2 therefore makes the following conservative,
fail-closed inferences:

- one-item `Invoices` envelope and non-empty detailed lines are required for
  this mapper, even though other documented retrieval shapes can also supply
  detail;
- identifiers are non-empty, control-character-free strings of at most 512
  characters; descriptions are at most 4096 characters; at most 10,000 lines
  are accepted;
- dates must be valid `YYYY-MM-DD` calendar dates and currency must be three
  uppercase ASCII letters;
- `SubTotal + TotalTax == Total`, line tax sums equal `TotalTax`, line identifiers
  are unique, and line values reconcile exactly: exclusive/no-tax line amounts
  to `SubTotal`, inclusive line amounts to `Total`; `NoTax` rejects non-zero tax;
- the names `Exclusive`, `Inclusive` and `NoTax` are used conservatively to
  construct the neutral line gross/net/tax representation. This is a mapping
  inference required by the neutral contract, not a canonical tax treatment;
- source invoice identity is used as the candidate economic-event identity
  within the same connection and tenant. No cross-tenant equivalence is implied;
- negative values are retained as provider evidence rather than reclassified
  as credit notes or refunds.

If later official evidence contradicts any inference, this candidate must be
reviewed and revised before transport or activation work proceeds.

## Explicitly outside X-S2

HTTP, query construction, pagination completeness, credentials, token custody,
environment access, retries, rate limits, routes, UI, persistence, payments,
tax decisions, provider activation, sandbox/live calls, merge, release and
deployment remain outside this module. X-S2 does not make Xero launch-ready.
