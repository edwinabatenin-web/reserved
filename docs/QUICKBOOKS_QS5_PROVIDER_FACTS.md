# QuickBooks Q-S5 provider facts

Status: pre-Q-S5, network-inert evidence inspected 2026-09-01. The fixtures are
synthetic examples grounded in documented field semantics; they are not
captured Intuit payloads and contain no customer or credential data.

## Dated source register

| Subject | Official Intuit Developer documentation inspected 2026-09-01 |
|---|---|
| Minor versions | https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/minor-versions |
| Invoice | https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/invoice |
| Payment | https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/payment |
| Data queries | https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/data-queries |
| Change data capture | https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/change-data-capture |

## Fact versus inference

| Area | Retained provider fact | Conservative implementation inference |
|---|---|---|
| Minor version | Optional; versions 1–74 were discontinued from 2025-08-01, requests below 75 are treated as 75, omission defaults to 75, and non-SDK requests document `minorversion=75`; versions should not be mixed. | Pin the exact integer 75 throughout one app. |
| Invoice money and tax | `CurrencyRef` is conditional on multicurrency. `GlobalTaxCalculation` is required for non-US companies and permits `TaxExcluded`, `TaxInclusive`, or `NotApplicable`. `TxnTaxDetail` is optional and ignored/not stored if sales tax is disabled. `TotalAmt` is read-only and includes charges, allowances, and taxes. | Do not infer absent currency or tax fields; unsupported combinations fail closed. |
| Settlement | `Balance` is read-only, initially `TotalAmt`, reflects payments, and zero normally indicates fully paid; Intuit warns linked processing can leave it unchanged. Invoice `LinkedTxn` can expose read-only Payment links retrievable by `TxnId`. | Treat Balance as corroboration, never sole settlement truth; require Payment evidence and reconciled allocations. Unknown links fail closed. |
| Payment | A Payment may apply to multiple invoices/credit memos or remain customer credit. `Id`, `TotalAmt`, and `CustomerRef` are required; `SyncToken` is the revision token. `UnappliedAmt` is read-only. `Line` is optional and ordered; line updates are all-or-none. `TxnDate` defaults to provider server date only at creation. Current official response examples show each Payment `Line` with one `Amount` and one `LinkedTxn`; one has `TotalAmt` 65, line `Amount` 55, and `UnappliedAmt` 10, and another uses separate lines for separate linked transactions. Documented linked types include Invoice, CreditMemo, Expense, Check, CreditCardCredit, and JournalEntry. | Preserve unapplied amount and line order. Reserved supports allocation arithmetic only for a non-negative line with exactly one Invoice link: its `Amount` is the candidate applied amount, and supported amounts plus `UnappliedAmt` must equal `TotalAmt`. Multiple links on one line, a missing, negative, or non-numeric `Amount`, a non-Invoice link, or non-reconciliation fails closed. Do not generalise beyond the documented example shape. Never invent an absent retained date, currency, allocation, or link meaning. |
| Query | The endpoint is `GET /v3/company/<realmId>/query?query=<select_statement>`. One case-sensitive entity per query; valued attributes are returned. Projections, OR, GROUP BY, and JOIN are unsupported. `STARTPOSITION` is one-based; `MAXRESULTS` defaults to 100 and is capped at 1000. `COUNT(*)` gives expected cardinality and `MetaData.LastUpdatedTime` is filterable. | Establish deterministic ordering and completeness explicitly; separate calls do not prove snapshot stability. Fail closed if completeness cannot be proved. |
| CDC | The request is `GET /v3/company/<realmId>/cdc?entities=<entityList>&changedSince=<dateTime>`. CDC returns full changed payloads for a maximum 30-day look-back and at most 1000 objects. Only changed groups appear. Deleted entries use `status=Deleted` with identity/metadata; no changes may be an empty `QueryResponse`. | Treat tombstones separately from live entities. Bound the response by actual object count only; the retained facts do not establish query pagination metadata for CDC. Fail closed on an over-limit or incomplete CDC window. |

## Retained mechanical contract

The following JSON is the normative retained contract for the accompanying
tests and synthetic fixtures. Changing a decision requires deliberate review.

```json provider-facts-contract
{
  "inspection_date": "2026-09-01",
  "minorversion": 75,
  "sources": {
    "minor_versions": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/minor-versions",
    "invoice": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/invoice",
    "payment": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/payment",
    "query": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/data-queries",
    "cdc": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/change-data-capture"
  },
  "decisions": {
    "settlement_evidence": "balance_corroborated_by_payment_allocations",
    "allocation_evidence": "payment_required",
    "unapplied_amount": "preserve",
    "absent_date_currency_tax": "remain_absent",
    "incomplete_pagination_or_cdc": "fail_closed",
    "unknown_link_type": "fail_closed",
    "query_snapshot_stability": "not_assumed"
  },
  "bounds": {"query_max_results": 1000, "cdc_max_objects": 1000, "cdc_lookback_days": 30},
  "documented_payment_link_types": ["Invoice", "CreditMemo", "Expense", "Check", "CreditCardCredit", "JournalEntry"],
  "qs5_supported_allocation_link_types": ["Invoice"],
  "global_tax_calculations": ["TaxExcluded", "TaxInclusive", "NotApplicable"]
}
```

## Scope and unresolved activation evidence

A coherent network-inert Q-S5 may start only if this corrected fixture and
validator contract proves the supported single-Invoice-link allocation and
strict, entity-specific query and CDC boundaries. Its permitted scope over
already authorised retained observations is exact minor-version configuration,
that narrow allocation reconciliation, unapplied credit preservation,
currency/tax presence handling, deterministic query accounting, and CDC
live/tombstone handling with provenance and fail-closed completeness checks.

QBO-01 UK VAT optionality remains open for activation. The provider documents
support non-US `GlobalTaxCalculation`, but do not alone prove every UK VAT
field or business rule. Unsupported tax, currency, allocation, unknown-link,
query-snapshot, pagination, and CDC-completeness cases remain fail closed.
Nothing here grants production or sandbox authority, HTTP access, credential
access, enablement, deployment, or a launch decision. Q-S2, Q-S3, the actual
Q-S5 implementation/review, and all Q-S6 activation gates remain open.
