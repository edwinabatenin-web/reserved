# Accounting-Assisted Income Matching

Accounting integrations provide context that Open Banking cannot reliably infer.

The current provider classes are implementation placeholders. The canonical
contracts in `reserved/providers/accounting/contracts.py` now preserve business
identity, provider identity, pagination cursor, source update time and sync
status across FreeAgent, Xero and QuickBooks. Raw access/refresh tokens are not
part of canonical records.

Reserved's canonical flow is:

1. Import an invoice from FreeAgent, Xero or QuickBooks.
2. Observe the raw provider record as an immutable `SourceObservation`, translate
   it through a `SemanticAdapterResult`, and only then construct canonical
   accounting evidence. Raw provider records never enter tax calculations and a
   provider adapter never emits a final recognition or allowability decision.
3. Observe a bank credit through Open Banking.
4. score possible invoice matches using amount, date, payer, reference and provider payment records.
5. Auto-match only when confidence is high and the result is unambiguous.
6. Ask the user to confirm ambiguous matches.
7. Produce an explicit, evidence-linked `RecognitionDecision` (cash or accrual)
   from the relevant accounting basis; recognition is never inferred from an
   invoice issue date alone.

For cash-basis sole traders, payment timing will normally drive the income
estimate. Invoice and service dates remain valuable for matching, forecasting
and overdue-payment insight.

## Enforced provider-neutral boundary

The canonical contracts now make the boundary executable and fail-closed:

- `SourceObservation` records the observed provider field paths and the digest
  of the observed representation, never canonical keys or a transformed payload.
- `SemanticAdapterResult` carries translated candidate facts and flags missing,
  unsupported and conflicting facts; it cannot produce a final decision.
- `RecognitionDecision` is explicit and evidence-linked; a missing candidate
  remains missing (never zero) and an unknown accounting method cannot select
  cash or accrual.
- `CanonicalAccountingTaxInput` is the only synthetic object that may cross the
  accounting/tax boundary, and only from a valid event + recognition decision.
- Allocation edges are validated for sign, references, business/event/currency
  compatibility, duplicate identity and reversal correctness.

The FreeAgent, Xero and QuickBooks adapters remain disabled placeholders; the
tests exercise the boundary with synthetic inputs only.

### Corrected contract enforcement

The boundary now additionally enforces the following fail-closed invariants,
each covered by an adversarial regression test:

- The raw payload is bound to its observation by digest: a raw record that does
  not hash to the observation's source digest is rejected, and a canonical
  document whose `business_id` or `document_id` differs from the observation's
  identity/record identity is rejected.
- Unsupported facts, conflicting facts, and observations marked conflicting or
  excluded fail closed; the observation's evidence state is preserved on the
  canonical document and malformed source lines are never silently discarded.
  A superseded observation may be documented but cannot resolve into a
  recognition decision.
- The accounting method is coerced to one canonical enum value; unknown or
  mistyped values fail closed and cannot silently select a different recognition
  basis.
- A recognition decision must be internally consistent with the canonical
  document and its candidate (amount, date, supporting observation IDs), and the
  tax year is checked against the recognised date under the 6-April boundary.
- Classification is derived from the document type, never from the amount sign;
  an expense document requires a decided allowability decision.
- Missing or invalid FX facts fail closed; a rate, source amount or rate date is
  never substituted with zero. Allocation edges must not exceed the referenced
  settlement's capacity and must use a compatible settlement type. Effective
  periods for one business must not overlap or be ambiguously open-ended.

This is a synthetic, provider-neutral boundary only. It is not connected to
routes, persistence, the production tax engine, reserve calculations, filing or
payments, and the provider adapters remain disabled placeholders.

## v3 canonical-contract convergence (provider-neutral)

The shared contract is pinned at `CANONICAL_CONTRACT_VERSION = "v3"`
(`reserved/providers/accounting/contracts.py`). v3 is the frozen, provider-neutral
foundation for later FreeAgent correction and Xero/QuickBooks implementation
workstreams. It is not a redesign, not provider implementation, and not a
production integration.

v3 incorporates the lessons of the completed FreeAgent, Xero and QuickBooks
evidence reviews without implementing any provider. The sections below are
marked where they remain historical/unresolved rather than rewriting history.

### Accepted convergence decisions (C1-C12)

- **C1 lifecycle**: raw provider status is preserved verbatim as source evidence;
  a conservative, reason-bearing `CanonicalDocumentState` translation exists but
  unknown/mixed statuses map to `UNKNOWN`. Settlement still derives only from
  allocation evidence; `Paid`, zero balance or zero amount-due never establish
  settlement. Correction/void/deletion (`CorrectionLifecycle`) stays distinct
  from settlement and from tax recognition.
- **C2 line values**: canonical line money is line gross; `TaxBreakdown` retains
  net/tax/gross; `LineValueSemantics` records whether a raw line was net, gross,
  inclusive, exclusive or unknown; `LineRole` keeps discounts, shipping, tax and
  adjustments explicit. Document net/tax/gross reconcile exactly (no tolerance,
  no fabricated balancing line) and otherwise fail closed.
- **C3 economic direction**: provider-neutral `EconomicDirection`
  (`RECEIVABLE`/`PAYABLE`/`UNKNOWN`). Unknown direction blocks income/expense
  interpretation. No provider-specific types are added to the shared model.
- **C4 prepayments/overpayments**: represented on payment/economic-event evidence
  via direction + `unapplied_amount`; no universal Xero resource types are added.
  Multiple retrieval paths must converge on one stable identity (duplicate
  identities are rejected).
- **C5 balance assertions**: optional immutable `ProviderBalanceAssertions`
  (`amount_due`, `amount_paid`, `amount_credited`, `balance`, `fully_settled_date`)
  are reconciliation-only; missing stays missing and nothing is derived merely to
  populate the shape.
- **C6 date semantics**: issue, posting, supply, due, provider creation/update and
  payment/allocation dates are distinct; Xero `Date` / QuickBooks `TxnDate` are
  never substituted into `created_at`. A document with incomplete dates cannot
  cross recognition/tax gates without an adequate selected recognition date.
- **C7 revision/staleness**: optional provider-native `revision_id` (e.g.
  QuickBooks `SyncToken`) is never synthesised from a timestamp.
  `classify_observation_relation` distinguishes identical, conflicting and
  revision-changed observations; same-version materially-different content fails
  closed as conflict, and timestamps do not alone order observations.
- **C8 incomplete FX**: `FxProvenance` stays strictly complete/consistent;
  `FxObservation` separately preserves only the FX facts actually observed.
  A foreign-currency record without a validated conversion is never treated as
  native currency and is barred from tax use.
- **C9 identity**: `connected_organisation_id` (authorised connection/grant
  context) and `business_id` (provider business/tenant/realm) are defined
  centrally; cross-connection, cross-business, cross-tenant and cross-resource
  substitution is rejected.
- **C10 provider configuration is not tax policy**: VAT basis is not the Income
  Tax accounting method; provider category/account/tax-code is not allowability;
  ownership/share requires separate evidence.
- **C11 resource-level completeness**: `ResourceCompleteness` carries pagination,
  terminal-page, source-totals, watermark/revision, tombstone, webhook, polling
  and freshness dimensions per resource. Lack of totals/CDC/webhooks is never
  described as complete.
- **C12 schema vs prerequisites**: `SourceSchema.request_prerequisites` is kept
  distinct from response `required_fields`; a nested-items query requirement is
  not encoded as unconditional response requiredness.

### Source evidence vs Reserved decisions

Provider facts remain reconciliation evidence only. Income Tax accounting method,
tax recognition, deductibility/allowability, ownership/customer share, settlement,
reserve calculations, filing and payments are Reserved decisions made through the
existing recognition/allowability gates, never by provider status, balance or
category. Provider adapters stay disabled unless separately approved.

### Version and compatibility boundary

v3 is internal and provider-disabled. Before changing a public or persisted
internal shape, every caller, serializer, fixture, snapshot and test must be
accounted for; unsupported older/newer shapes are rejected rather than
interpreted opportunistically. No production persistence is introduced merely to
test migration.

### Remaining provider-specific uncertainties (deferred, not blockers)

- FreeAgent line `price` is net and the candidate adapter treated it as line
  gross; genuine taxable invoices/credit notes were therefore quarantined
  (historical finding — correction is a separate package, not this one).
- Xero `PAID` is not universal settlement truth; `AmountDue`/`AmountPaid`/
  `AmountCredited` are assertions, not authoritative allocation evidence;
  prepayments/overpayments/refunds and credit direction must be mapped by the
  Xero adapter.
- QuickBooks `SyncToken` is an optional revision identity; there is no lifecycle
  status directly comparable to the shared state; `TxnDate` is a posting date;
  `CreditMemo`/`VendorCredit` need economic direction; `minorversion` may affect
  schema interpretation.
- Exact resource field mappings, webhook coverage and completeness remain
  provider-adapter responsibilities and are not inferred from this shared model.

### Readiness

The v3 shared contract is coherent and tested, and is ready for a separate
read-only review. It is **not** production-ready or launch-ready: providers
remain disabled and the contract is not connected to customer routes,
persistence, tax calculations, reserves, filing or payments.

## Canonical data requirements

Accounting method and MTD update-period basis are separate concepts and must be
stored independently for each applicable business or property income source.

| Attribute | Allowed values | Meaning and use |
|---|---|---|
| `accounting_method` | `cash`; `traditional_accrual` | Determines when income and expenses are recognised for tax. Cash and traditional-accrual users can therefore require different recognition treatment for the same invoice, payment, expense or prepayment. |
| `mtd_update_period_basis` | `standard-tax-year`; `calendar` | Determines the convention used for MTD quarterly reporting periods. It does not determine the accounting recognition method. Filing deadlines remain the same for standard-tax-year and calendar update periods. |

Neither attribute may be inferred from the other. Provider data must be mapped
to these canonical values only where its meaning and applicable income source
are established; otherwise the value remains unknown and requires confirmation
or an appropriate qualified fallback.

## Verified provider constraints (12 August 2026)

| Provider | OAuth / test environment | Pagination / limits | Implementation boundary |
|---|---|---|---|
| FreeAgent | OAuth 2.0; sandbox host `api.sandbox.freeagent.com`; access and refresh tokens per authorised account | Default 25, maximum 100 per page using `page`/`per_page`; Link and `X-Total-Count` headers; 120 user requests/minute, 3,600/hour, 15 refreshes/minute | Company, invoices and related records can be adapted after sandbox app credentials/callback are configured |
| Xero | OAuth 2.0 and demo company | Invoices and bank transactions support pagination; 5 concurrent calls, 60/minute per tenant, daily tier limits and `Retry-After` on 429 | Tenant selection and token refresh are required; connector must queue/back off rather than promise immediate full history |
| QuickBooks Online | OAuth 2.0 and sandbox company | Query responses capped at 1,000 entities; sandbox/production REST limits include 500/minute per realm and 10/second per realm/app; webhooks available | Preserve Realm/business ID, paginate explicitly, verify webhooks, back off on 429 |

Official sources:

- https://dev.freeagent.com/docs/oauth
- https://dev.freeagent.com/docs/introduction
- https://developer.xero.com/documentation/getting-started-guide/
- https://developer.xero.com/documentation/guides/oauth2/limits
- https://developer.intuit.com/app/developer/qbo/docs/learn/limits-and-throttles
- https://developer.intuit.com/app/developer/qbo/docs/develop/webhooks

Exact resource field mappings, webhook event coverage and app-review requirements
must be verified against each official resource reference during adapter
implementation; capabilities are not inferred merely from the normalised model.
