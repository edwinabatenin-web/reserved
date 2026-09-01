# QuickBooks Q-S5A narrow adapter evidence

Status: uncommitted, network-inert candidate for independent review. QuickBooks
remains disabled. This is not general invoice ingestion, transport, custody,
sandbox evidence, activation, deployment, or launch readiness.

## Scope

`reserved/providers/accounting/quickbooks_invoice_payment_adapter.py` accepts
only exact Q-S4 `InvoiceObservation` and `PaymentObservation` instances and
requires the caller to re-present their exact Q-S1 `RealmBinding`. It safely
requires the exact frozen-evidence root and recursively exact frozen containers
before traversal, independently recomputes the Q-S4 observation attestation,
reconstructs plain input from that evidence, replays the exact Q-S4
observer with the original retrieval and binding identity, and compares the
complete observation before interpretation. It has no HTTP client,
URL, SDK, environment/configuration read, credential access, persistence,
logging, route, callback, file-write, or provider-enablement capability.

The adapter deliberately covers one non-US, tax-exclusive sales invoice line,
an optional terminal corroborating subtotal, one percentage TaxLine, and one
Payment line linked once to that invoice. All other shapes fail closed.

## Official provider facts

The official Intuit non-US automated-sales-tax page supplied for this review
was inspected on 2026-09-01:

`https://developer.intuit.com/app/developer/qbo/docs/workflows/calculate-sales-tax/automated-sales-tax-for-non-us-locales`

For the bounded evidence used here, it documents line `TaxCodeRef`,
`TxnTaxDetail.TotalTax`, TaxLine `Amount` and `NetAmountTaxable`,
`GlobalTaxCalculation == TaxExcluded`, subtotal behaviour, and a GBP/VAT
example. The already-retained provider facts in
`docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md` separately document Invoice, Payment,
query, CDC, minor-version, `Balance`, `UnappliedAmt`, and linked-transaction
facts.

These provider facts do **not** prove every UK VAT business rule, that every UK
company supplies tax detail, Reserved recognition or category meaning,
complete query/CDC ingestion, or activation readiness.

## Narrow Reserved implementation inference

The following are conservative Q-S5A decisions, not claims about every valid
QuickBooks record:

- Currency, transaction dates, totals, IDs, revisions, tax references, and tax
  detail must be explicit; missing and null never become defaults. GBP is the
  only currency in the reviewed example and therefore the only accepted code.
- Money is an exact JSON integer or `Decimal`, finite, nonnegative, and limited
  to two decimal places. No float coercion or rounding occurs.
- The single SalesItem `Amount` is net because this slice accepts only exact
  `TaxExcluded`. Canonical line gross is net plus its one reconciled TaxLine.
- A terminal `SubTotalLineDetail` must exactly equal that net but is not a
  second economic line.
- `TaxCodeRef.value` is retained as the provider VAT code. `TaxRateRef.value`
  remains only in retained source/provenance evidence and is not treated as an
  accounting/item category. An explicit `TaxPercent` is converted from provider
  percentage units to the canonical fractional rate (`20` to `0.20`) only when
  it reconciles exactly with taxable net and TaxLine amount; no rate is rounded
  or inferred when absent.
- Realm ID is the canonical business identity. The opaque Q-S1 credential
  reference is the connected-organisation identity. The source customer
  reference is retained by the Q-S5A result solely to reconcile its Payment.
- The raw provider status is preserved when explicit. Canonical lifecycle stays
  unknown; no lifecycle, recognition, allowability, category, FX, or settlement
  status is invented.
- Invoice `Balance`, when present, is only `ProviderBalanceAssertions.balance`.
  Settlement remains unknown on the document and is derived only by the
  existing allocation validation/settlement boundary.
- A Payment is emitted with one allocation only if its one Invoice link and
  arithmetic reconcile exactly against the Q-S5A invoice result. Total payment
  money and unapplied credit remain distinct from the allocated amount.
- The invoice result retains its complete originating Q-S4 observation. Before
  payment emission the adapter replays and re-adapts it, requiring the entire
  source observation, semantic result, canonical document, and customer
identity to match; forged or mutated exact dataclass instances fail closed.
  Exact nested source-observation, semantic-result, source-observation wrapper,
  and canonical-document types are established before dereference or equality.

## Unsupported and fail-closed

The candidate emits no canonical object for `TaxInclusive`, `NotApplicable`,
absent/unknown currency or dates, absent/null totals or tax detail, zero or
multiple economic lines, discounts, shipping, groups, description-only or
other roles, non-terminal/mismatched subtotals, multiple TaxLines, non-percent
tax, or any net/tax/total mismatch. Negative, non-finite, boolean, float,
over-precision money and missing, duplicate, whitespace-bearing, delimiter-
bearing, or otherwise unstable IDs are rejected.

Payments fail closed for absent date/currency, zero or multiple lines, zero or
multiple links, non-Invoice links, unknown invoice IDs, duplicate invoice and
payment IDs, currency/customer/user/realm/connected-organisation mismatch, or
allocation arithmetic mismatch. Hand-built lookalikes, conflicting/excluded
evidence, digest/revision/identity mutation, and Q-S1 binding substitution are
also rejected. Retrieval-time or attestation mutation, plain-dict/list
substitution for frozen evidence, unexpected nested containers/scalars, hostile
container hooks, and forged linked-result nested objects fail with constant,
non-echoing adapter errors.
Retained evidence is validated as a complete bounded graph (including every
container and scalar) and iteratively reconstructed; depth, width, node and
payload limits, cycles, and aliases fail closed. Stored retrieval time must be
the exact normalized UTC form produced by Q-S4, so polymorphic timezone hooks
cannot run at the adapter boundary.

No inference is made for invoice discounts, shipping, compound or inclusive
tax, multiple rates or lines, zero-rated/exempt/outside-scope VAT meaning,
foreign exchange, credit memos, refunds, multi-document payments, payment
ordering, or incomplete query/CDC windows.

## Residual gates

QBO-01 UK VAT optionality remains open: the cited page supports this exact
non-US tax representation but does not prove every UK VAT configuration or
business rule. Q-S2 transport and secret custody, Q-S3 authenticated callback
and protected-route integration, broader Q-S5 pagination/incremental-sync and
operational ingestion, and every Q-S6 sandbox, monitoring/recovery,
privacy/security, independent-assurance, enablement, and launch gate remain
open. Nothing in Q-S5A grants credentials, sandbox/production access, network
authority, deployment authority, or permission to activate QuickBooks.

## Verification

`tests/test_quickbooks_invoice_payment_adapter.py` constructs every candidate
through the exact Q-S4 observers. It covers the accepted invoice and payment,
canonical v3 normalisation, subtotal non-double-counting, allocation-derived
settlement, Balance non-authority, the rejection classes above, immutable and
redacted evidence, no raw-evidence reference, no network/file-write behaviour,
and the unchanged disabled provider.
It also covers complete typed-projection replay, retrieval/binding/source
attestation, exact-container trust boundaries, hostile non-echoing failures,
linked-result replay/re-adaptation, non-category `TaxRateRef`, fractional
canonical rates, and exact `TaxPercent` arithmetic.
