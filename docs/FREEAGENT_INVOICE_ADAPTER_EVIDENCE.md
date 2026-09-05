# FreeAgent offline invoice mapping — bounded candidate

Uncommitted implementation pending different independent review, on base
`9d36b218bbd15728c120cbe7055bb0b5c7890b10`. Founder SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
The explicit owning sequence decision separates this offline FA-S3 component
from FA-S2; it does not waive custody/authenticated company binding for live
integration, complete FA-S3 or enable FreeAgent.

## Source and inference

FA-S1's accepted evidence/validator remain unchanged. The official
[FreeAgent invoice documentation](https://dev.freeagent.com/docs/invoices)
was read publicly on 5 September 2026 to check the item fields absent from the
retained FA-S1 item schema. No provider API or account was accessed.

The source identifies header net, sales-tax and gross amounts, separately
reported paid/due amounts, the invoice-item URL, quantity, unit price,
description, item type and position. Products and Services are documented
types; position starts at one. The documented non-sales-tax flag is explicit.
Decimal JSON examples use strings. The page does not supply a general
rounding/discount/CIS/second-tax mapping algorithm. Its list example with zero
net/tax but gross 200 is contradictory; the adapter rejects it.

The implemented subset is deliberately narrower than the provider API. It
requires supplied UK sole-trader company context, GBP company/invoice currency,
country exactly `United Kingdom`, all three company CIS flags explicitly false,
and exactly one source-identified Products/Services item. This does not verify
residence, legal status, membership or VAT registration. It is a conservative
engineering support boundary, not an assertion that other records are invalid.

Required invoice facts are explicit `involves_sales_tax=false`,
`is_interim_uk_vat=false`, `ec_status=UK/Non-EC`, zero discount and zero header
sales tax, with header net equal to gross. Item quantity times unit price must
equal that gross exactly. No rounding, balancing line, tax rate or missing
default is introduced. The same observed zero tax and equal net/gross are
represented in the canonical tax breakdown; tax and raw-value semantics stay
UNKNOWN rather than asserting VAT legality or inclusive/exclusive treatment.

## Actual callable boundary

`observe_invoice(company_payload, invoice_payload, **context)` captures an
unresolved `SourceObservation`. Inputs are exact JSON dictionaries with the
FA-S1 company envelope and exactly one member in the invoice-list envelope.
The full graph is checked and copied before schema parsing or arithmetic.
`adapt_invoice(..., observation=observed, **context)` replays that exact source
and context before constructing an internal `SemanticAdapterResult` and calling
the unchanged `normalise_document`.

Context fields are `user_id`, `connected_organisation_id`, `business_id`,
`company_id`, `import_run_id`, `retrieved_at`. The first four string identifiers
(excluding company ID) are bounded ASCII references. Company ID retains its
exact positive integer or decimal-string type and must match the company
response. Retrieval must be an exact UTC datetime. None is authenticated by
this module. Changed company/user/connection/business/import/retrieval context
cannot reuse an old observation. This detects inconsistent reuse, not actual
provider freshness, authorised membership or deliberate coordinated forgery
of both source and supplied context.

The source digest covers the complete company-and-invoice snapshot; the source
field paths name the actually observed fields, including nested item paths.
Observation identity also binds every context value and retrieval time. The
economic-event identity binds user, connection, business, company and invoice,
but not import/retrieval, so a refresh does not invent a new economic event.
No provider revision is inferred from timestamps. No raw payload or credential
reference is retained in the result; source digest is not an authenticated seal.
Same-source/context re-observation is deterministic, not durable deduplication.

Item identity correction: source URLs in the evidenced `invoices`, `contacts`,
`projects`, `properties`, `bank_accounts`, `recurring_invoices`, `company`,
`categories` and `stock_items` namespaces are rejected before normalisation, including
invoice PDF paths and references to other records rather than only the current
invoice/contact. The existing HTTPS/host/path-shape restrictions also apply.
The positive synthetic item uses `/v2/invoice_items/301` (and a second identifier
for Products); its supplied URL is preserved, never generated from position.
This is evidence-limited URI support, not a claim that the documentation defines
a universal invoice-item URI grammar. Other syntactically admissible paths are
not thereby verified as real item resources. Neither URI shape nor its presence
in the payload proves provider authenticity or company membership; evidence
remains unresolved and live source validation remains gated.
This bounded set follows accepted FA-S1 company/invoice resource validators and
the invoice-item category/stock references. Root's correction authority records
public checks of the official [categories](https://dev.freeagent.com/docs/categories)
and [stock items](https://dev.freeagent.com/docs/stock_items) pages: those catalog
identities are distinct from economic invoice-item identity. A parameterized
matrix covers every listed namespace's root, record and deeper subpaths;
singleton roots fail the existing generic path-shape check. No other namespace
is excluded by speculation or claimed verified merely because it is admissible.

Bounds: 64 KiB encoded snapshot, 1,024 graph nodes, depth eight, 100 entries per
container and 2,048 characters per string; cycles, aliases, custom objects,
unsafe control characters and non-JSON scalar types are rejected. Decimal
strings allow ten integer digits, two fractional digits for money and six for
quantity/position, with no signs, exponent or leading-zero ambiguity. A private
64-digit decimal context prevents caller precision from changing arithmetic.
Errors contain fixed reasons, not source values.

## Public canonical result and correction-state seam

The public result contains only the replayed observation and final canonical
document. The semantic result is an internal intermediate, not an exported
round-trip contract. The unchanged shared normaliser defaults
`correction_lifecycle` to NONE: no correction recorded, not independently
verified absence. After normalisation this adapter changes **only** that field
to the existing UNKNOWN value, because it has no correction evidence. Tests
capture the actual normaliser result and prove every other field and provenance
are unchanged. A caller bypassing this public boundary and constructing its own
semantic result is not promised UNKNOWN by the unchanged shared normaliser.
Private names are not a security sandbox against arbitrary in-process code.

UNKNOWN correction state is not itself a recognition-denial control. There are
no cash/accrual recognition candidates, payments, allocation edges,
allowability/recognition decisions or canonical tax input. Raw status is
preserved while canonical lifecycle and settlement remain UNKNOWN. Paid/due
values remain provider-balance assertions, including missing/null versus zero
through the source identity. `paid_on` and `due_on` do not create cash evidence.

## Unsupported cases and remaining gates

Multiple/missing items, time-based or adjustment item types, absent item URL,
foreign currency, sales-tax invoices, draft/refund/write-off/overpayment forms,
nonzero Zero Value status, tax/discount/line-total mismatches, missing required
facts, unknown additive fields and unsupported financial fields are rejected.
Invoice exchange-rate, second-tax, CIS, property and item tax/category fields
are outside this initial mapping even if supplied as zero: they do not silently
disappear. Optional descriptive/date/balance fields are schema-validated and
retained in the source identity; dates are not guessed from payment terms.

This component can produce a real exact canonical invoice, but it is not
general accounting ingestion, a complete business-income inventory or tax
recognition. No HTTP client, retry loop, provider session, credential access,
storage, route, configuration change or provider enablement is added.
FA-S2, transport, wider mappings, source completeness/freshness, custody,
privacy/security, sandbox/customer/target evidence and activation remain open.

## Synthetic verification

`tests/test_freeagent_invoice_adapter.py` traverses actual FA-S1 validation and
canonical normalisation. It proves the literal 2.5 × 50 = 125 positive case,
zero/missing/null distinctions, non-rounding, source/context replay rejection,
owned snapshots, typed company identity, genuine item identity, unsupported
forms, graph/type/size bounds, raw-status/balance non-authority and unchanged
disabled provider. This is local synthetic evidence, not independent acceptance.
Final focused run: **159 passed**. Affected matrix: **1,690 passed**, no failures:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest \
  tests/test_freeagent_invoice_adapter.py tests/test_freeagent_invoice_contract.py \
  tests/test_freeagent_resilience.py tests/test_freeagent_oauth_contract.py \
  tests/test_accounting*.py tests/test_provider*.py tests/test_xero*.py \
  tests/test_quickbooks*.py -o addopts='' -q -p no:cacheprovider
```

The focused run used the same interpreter/options with only the new test file.
No full-repository run or live-provider validation is claimed. Frozen hashes
accompany the handoff for independent review.
