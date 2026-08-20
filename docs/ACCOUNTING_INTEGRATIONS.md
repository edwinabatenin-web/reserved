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
