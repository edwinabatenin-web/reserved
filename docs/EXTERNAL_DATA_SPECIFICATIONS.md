# Reserved — External Data Specifications

**Purpose:** authoritative agent-facing technical and semantic contract for
external data providers. Read with `FOUNDER_DECISIONS.md`, unresolved entries in
`docs/DESIGN_QUESTIONS.md`, and implementation work in
`EXTERNAL_DEPENDENCIES.md`.

## 1. Common principles

### Canonical data boundary and provenance

No provider payload may affect a calculation directly. A provider adapter must
normalise it into a Reserved datum with: provider/API/version; redacted source
reference; subject and business/employment identity; tax year and represented
period; source effective/observation time where available; retrieval time;
field-level presence and completeness; transformation and schema version; raw
artefact hash where retention is approved; and evidence-quality/conflict state.
Absent, zero, known-empty, partial, stale and quarantined are distinct states.

### Freshness, completeness and source priority

Freshness is assessed from the time the source value represents, not merely the
time it was retrieved. Completeness is purpose- and population-specific. No
provider, including HMRC, automatically outranks another source: priority is
resolved per datum using identity, represented period, recency, completeness,
semantics and intended use. Material divergence is preserved and surfaced.

### Conflict, fallback and resilience

Adapters are isolated evidence sources. Required-field/schema incompatibility
fails closed and quarantines the affected record. Provider failure is localised;
it does not delete earlier provenance or disable unrelated journeys. A safe
fallback may use last-known-good data only with timestamps and an explicit stale
state, or use current payslip/manual/accounting/bank evidence where the datum's
contract permits it. Controls are tracked in `EXTERNAL_DEPENDENCIES.md`.

### Accounting method and MTD update-period basis

The canonical Data Requirements Matrix includes two independent attributes:

- `accounting_method = cash | traditional_accrual | unknown` controls when income and
  expenses are recognised.
- `mtd_update_period_basis = standard_tax_year | calendar | unknown` controls the
  convention used to group MTD updates into reporting periods. It does **not**
  alter the statutory filing deadlines.

Neither value may be inferred from the other. Provider-native labels must be
mapped explicitly and unsupported/unknown values must fail closed for affected
calculations or reporting.

### Canonical accounting pipeline — governing contract

All accounting integrations must implement this boundary:

> **Provider record → immutable source observation → semantic adapter result →
> canonical accounting event/evidence → recognition & allowability decision →
> tax engine**

The stage contracts (`SourceObservation`, `SemanticAdapterResult`,
`RecognitionDecision` and `CanonicalAccountingTaxInput`) are concrete, frozen
dataclasses and the normalisation is fail-closed: a canonical object cannot be
constructed without a valid observation and adapter result, and recognition is
never inferred from an invoice issue date.

Raw provider records and fields never enter the tax engine directly. Provider
observations are evidence and may be **selected, corroborating, superseded,
excluded, conflicting or unresolved**, with reasons and references to competing
evidence. The semantic adapter preserves provider meaning; it does not decide
final tax recognition or allowability. The tax engine accepts only canonical
accounting facts/events and rules-layer decisions.

The shared provider-neutral contract must preserve:

- separate user, provider, connected-organisation, business/source and
  import-run identities;
- business type and per-business, effective-dated `accounting_method`, with
  MTD update-period basis held independently;
- VAT registration state/history/effective dates, scheme and basis where known,
  plus explicit net/VAT/gross and inclusive/exclusive/not-applicable semantics;
- distinct document types, line facts, payment/receipt records and allocation
  edges for payments, credits, refunds, write-offs and reversals;
- candidate cash-recognition and accrual-recognition dates/amounts separately;
  the adapter never selects the final recognition basis;
- original and base currency amounts with FX rate, rate date, source and
  conversion/rounding provenance;
- ownership/share evidence for property and business allocations, effective
  dates, evidence source and confirmed/estimated/unknown status;
- an allowability decision model separating provider assertion, Reserved rule,
  customer confirmation and adviser adjustment, including mixed/apportioned,
  adjustment-required, insufficient-facts, unsupported and unresolved outcomes;
- correction lifecycle for void, deletion, reversal, refund, credit allocation,
  write-off and reclassification without creating a second economic event;
- provider, API/version, resource, record ID, exact source fields/definitions,
  created/updated/effective/retrieved timestamps, adapter version,
  transformation/rounding and source-record digest;
- separate record-freshness, retrieval, bookkeeping and reconciliation
  completeness states;
- `economic_event_id`/match groups for cross-source deduplication and
  corroboration; and
- explicit missing, stale, conflicting, incomplete and unsupported uncertainty,
  including determinable numerical bounds where possible. Missing is never
  silently converted to zero.

Outstanding or settled status is derived from the allocation graph, not
`gross - amount_paid`. A provider's `amount_paid` value may be retained as an
assertion but cannot replace payments, credit allocations, refunds, write-offs,
reversals or overpayments.

The synthetic boundary additionally enforces, after the corrective remediation
pass: the adapted payload is bound to its observation by source-record digest;
the canonical document must match the observation's business and record
identity; unsupported/conflicting facts and conflicting/excluded observations
fail closed and the observation's evidence state is preserved, while a
superseded observation may be documented but cannot resolve into a recognition
decision; the accounting method is one canonical enum value; recognition
decisions are validated against
the canonical candidate and the tax year against the recognised date;
classification derives from the document type (never the amount sign) and
expenses require a decided allowability decision; missing or invalid FX facts
fail closed rather than becoming zero; allocation edges respect settlement
capacity and type; and effective periods must not overlap or be ambiguously
open-ended.

Unresolved policy choices and provider facts are cross-referenced, not answered
here: see `FOUNDER_DECISIONS.md` and the accounting-software entries in
`docs/DESIGN_QUESTIONS.md`.

## 2. HMRC data specification

### 2.1 Corrected HMRC Data Requirements Matrix

| Reserved datum | HMRC mapping and exact meaning | Period / freshness | Population / conditions | October use and source priority | Classification |
|---|---|---|---|---|---|
| Employment identity | Individual Employment 1.2: employment history, employer PAYE reference/name and relevant off-payroll flag | Tax-year PAYE record; completeness latency not established | User-authorised PAYE population; not proven universal/current | Link employment-level evidence; insufficient alone | Sandbox verification required |
| Historic/reconciled employment income | Individual Income 1.2: employer-reported employment income for a tax year | Tax-year/prepopulation record; not a documented live payroll feed | User-authorised PAYE population | Prior-year corroboration/reconciliation | Sandbox verification required |
| Historic/reconciled employment tax deducted | Individual Tax 1.1: tax deducted from annual gross employment income | Annual/tax-year SA prepopulation semantics | User-authorised PAYE population | Historic evidence; not verified current YTD | Sandbox verification required |
| Current taxable employment pay YTD | Individuals Employments Income (MTD) 2.0, employment financial details, `taxablePayToDate` | Employer-submitted taxable pay to date; FPS timestamp/latency unresolved | Relevant MTD customer journey, not general PAYE population | Corroborate where eligible; newer complete payslip may outrank; fallback required | Sandbox verification required; see HMRC-01/02 |
| Current PAYE tax deducted YTD | Same resource, `totalTaxToDate` | Total tax deducted to date; underlying FPS time/latency unresolved | Relevant MTD population | Useful corroboration; never a universal hard dependency | Mapping supported; freshness clarification HMRC-01/02 |
| Current estimated annual employment pay | No verified public user-authorised mapping | Unknown | Unknown | Forecast locally; do not substitute `totalEstimatedIncome` | HMRC clarification HMRC-05 |
| Employer submission timestamp | No confirmed field alongside the YTD values | Retrieval time is not submission/effective time | Unknown | Required for reliable freshness classification | HMRC clarification HMRC-01 |
| HMRC in-year/final SA calculation | Individual Calculations (MTD) 8.0 trigger/list/retrieve; calculation timestamps and employment details include YTD pay/tax | Reflects data held at the calculation timestamp; in-year or final | MTD Self Assessment journey | Comparator/reconciliation only, never Reserved's primary engine | Sandbox verification required |
| Current HMRC-recorded MTD status | Self Assessment Individual Details (MTD) 2.0; capture exact endpoint/field from current OAS | Current recorded state where available | May return `CLIENT_NOT_MTD_ENROLLED`; not population-wide | Authoritative evidence of recorded status, not sole future-scope predictor | Sandbox verification; HMRC-06 |
| MTD obligations | Obligations (MTD) 3.0 | Current obligations/deadlines recorded by HMRC | MTD-enrolled/relevant income-source population | Authoritative for actual recorded obligations | Concept verified; operational sandbox proof required |
| Likely future MTD scope | Reserved rules applied to prior-return qualifying gross self-employment/property income and eligibility/exemption facts | Predictive assessment from applicable earlier return | Wider SA population where facts are available | Clearly labelled Reserved forecast, separate from HMRC status | Local model verified in principle; HMRC-06 |
| MTD SA payments/liabilities | Self Assessment Accounts (MTD) 4.0 | Payments/liabilities for years since joining MTD | MTD customers | Never use as universal SA account source | Limitation verified |
| General SA account position | View Self Assessment Account 1.0 controlled beta; `GET /individuals/self-assessment/breakdown/{utr}`, optional `fromDate` | On-demand breakdown of effective-dated charges, payments, credits, interest and balances | SA user/agent with UTR/OAuth; controlled production onboarding | Strong reconciliation candidate; access unresolved | HMRC clarification HMRC-04 |
| Tax-rule changes | Developer Hub changelogs/roadmaps, GOV.UK and legislation | Publication-based, not personalised | Public | Operational monitoring only; never automatic production-rule mutation | Verified |
| PAYE tax code/current payroll method | No complete mapping verified | Exact current public read semantics unresolved | Unknown | Useful but not an October dependency with payslip/manual route | Not required for launch |
| `accounting_method` | Reserved canonical attribute; HMRC/provider mapping must be evidenced per business/source | `cash` recognises on cash movement; `traditional_accrual` recognises on earned/incurred basis | Per business/accounting configuration | Required before business income/expense recognition | Explicit canonical requirement |
| `mtd_update_period_basis` | Reserved canonical attribute: `standard_tax_year` or `calendar` | Reporting-period grouping convention only | Per MTD business/configuration where applicable | Does not change statutory filing deadlines | Explicit canonical requirement |

### 2.2 API subscription checklist

**Launch/core — subscribe and test where the feature is in approved scope:**

- Individuals Employments Income (MTD) 2.0;
- Self Assessment Individual Details (MTD) 2.0;
- Business Details (MTD) 2.0;
- Obligations (MTD) 3.0;
- Self Assessment Accounts (MTD) 4.0;
- Individual Calculations (MTD) 8.0;
- Marriage Allowance 2.0;
- Self Employment Business (MTD) 5.0;
- Property Business (MTD) 6.0; and
- Business Income Source Summary (MTD) 3.0.

**Useful wider coverage — subscribe/test when product scope requires it:**
Individuals Dividends Income 2.0; Savings Income 2.0; Pensions Income 2.0;
State Benefits 2.0; Reliefs 3.0; Expenses 3.0; Foreign Income 2.0; Other
Income; and Individual Losses 7.0.

**Historic/reconciliation:** Individual Income 1.2, Individual Employment 1.2,
Individual Tax 1.1, Individual Benefits 2.0 and National Insurance. Use
Individual PAYE Test Support 2.0 beta (`paye-des-stub`) for the documented
stateful PAYE sandbox journey. Self Assessment Test Support (MTD) 1.0 is a
separate MTD cleanup facility, not a PAYE fixture source.

Production eligibility for relevant MTD read uses is unresolved: see HMRC-03.
Pin every implemented version in adapter provenance and monitor its changelog.

### 2.3 Population, temporal and source-priority rules

- MTD endpoints are never assumed to cover the general PAYE or SA population.
- Legacy Individual Income, Employment and Tax values are tax-year/prepopulation
  evidence unless the exact endpoint contract establishes a different meaning.
- `taxablePayToDate` and `totalTaxToDate` are current-year evidence only for the
  eligible journey; until HMRC-01/02 are answered, their effective freshness is
  unknown and a newer complete payslip may be preferred.
- HMRC calculation timestamps date HMRC's calculation, not necessarily every
  underlying fact. HMRC calculations corroborate Reserved's local engine.
- HMRC obligations and recorded account/status facts are authoritative for what
  HMRC records. They do not prove that Reserved has every current economic fact.
- Reserved's likely-future-MTD result remains a forecast until reconciled with a
  formal HMRC status; the two values are stored and displayed separately.

### 2.4 Canonical HMRC provenance contract

In addition to the common provenance fields, retain the HMRC API and semantic
version, OAuth subject/agent context (without tokens), tax year, employment or
business identifier, endpoint journey, calculation ID/timestamp where relevant,
field presence, HMRC correlation/reference metadata safe to retain, and the
population/configuration condition under which the datum was available. Do not
convert an absent MTD-only field into evidence that the underlying income is
absent.

### 2.5 Sandbox acceptance tests

1. Authorise a synthetic user with minimum scopes; prove denial, state replay,
   token expiry/refresh and disconnect fail safely without secrets in logs.
2. Retrieve/link multiple employments without merging identities or double
   counting aggregate and employment-level values.
3. Verify `taxablePayToDate` and `totalTaxToDate` field paths, decimals,
   adjustment/negative behaviour and absent/null/zero distinctions.
4. Exercise fresh, lagged, missing and conflicting HMRC-versus-payslip evidence;
   prove no unconditional HMRC precedence and no use of retrieval time as FPS
   time.
5. Verify an ineligible/not-enrolled MTD user yields a population/status result,
   not zero income or a broken general calculation.
6. Trigger/list/retrieve in-year and final calculations; preserve calculation
   timestamp and use only as comparator/reconciliation evidence.
7. Retrieve obligations and accounts across joined/non-joined years; prove MTD
   account data is not treated as a universal SA balance.
8. Exercise schema drift: additive fields are flagged; missing/incompatible
   required fields quarantine/fail closed and leave last-known-good evidence
   intact with timestamps.
9. Reconcile webhook/event-driven updates, where supported, against a periodic
   full read; detect missed, duplicate and reordered observations.
10. Run version-change regression tests before enabling a new API/schema version
    to influence any calculation.

## 3. Xero data specification

Placeholder pending a validated provider review. Use the common structure:
Reserved datum → provider field → exact definition → period/date semantics →
freshness → population/configuration → transformation → source priority →
fallback → API/version → acceptance test.

## 4. QuickBooks data specification

Placeholder pending a validated provider review; apply the common structure and
do not infer accounting basis from endpoint naming or report labels.

## 5. FreeAgent data specification

Placeholder pending a validated provider review. Existing implementation
constraints remain in `docs/FREEAGENT_ADAPTER_IMPLEMENTATION_DECISION.md`.

## 6. Yapily / banking data specification

Placeholder pending a validated provider review. Existing validated material
remains in `docs/YAPILY_INTEGRATION_SPEC.md`; migrate only reviewed mappings into
this canonical structure.

### Open retention and reproducibility questions

The Yapily/banking design must not assume that historical source data can be
retrieved again after consent expires, is revoked or the institution limits the
available history. Before finalising retained fields or lifecycle rules, resolve
the following entries in `docs/DESIGN_QUESTIONS.md`:

- YAPILY-01 — minimum evidence for historical calculation reproducibility;
- LEGAL-01 — lawful basis after Open Banking consent ends;
- LEGAL-02 — proportionate retention periods by evidence class;
- LEGAL-03 — effect of Open Banking consent revocation; and
- LEGAL-04 — minimising special-category exposure in transaction data.

Until those questions are resolved, the working design is to separate
short-lived operational source data from a minimised calculation-evidence
snapshot. Exact retained fields, retention periods, deletion/anonymisation
triggers and customer controls remain unapproved and must not be inferred from
this cross-reference.

### Open provider and institution-behaviour questions

Before finalising the Yapily adapter and its launch acceptance tests, resolve
`YAP-01` through `YAP-06` in `docs/DESIGN_QUESTIONS.md`. These cover Data Plus
commercial availability, transaction statuses, booking/value-date semantics,
historical-coverage metadata, transaction identity/mutation and joint-account
holder/ownership metadata. The retention, reproducibility and legal/privacy
questions above remain separate and are not duplicated in those entries.
