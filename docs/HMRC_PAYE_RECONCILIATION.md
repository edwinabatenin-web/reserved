# HMRC/PAYE reconciliation

Verified against current official HMRC documentation on 12 August 2026. This
document describes a read/reconcile capability, not MTD submission and not a
connection to a live taxpayer account.

## Capability matrix

| Data needed | HMRC API/source | Available? | Granularity | Timing | Authorisation | Limitations |
|---|---|---:|---|---|---|---|
| Employment records, employer name and PAYE reference | Individual Employment 1.2 | Yes; beta, sandbox and production | Employment and tax year | As reported to HMRC through PAYE | User-restricted OAuth 2.0; user consent and API subscription required | Intended primarily to pre-populate Self Assessment; not proof that all current employment data is complete |
| PAYE employment income | Individual Income 1.2 | Yes; beta, sandbox and production | Employment income for a tax year; also covers specified pensions/benefits | As reported to HMRC by employers | User-restricted OAuth 2.0; user consent and API subscription required | Does not provide Reserved's complete live income position; other sources and recent changes may be missing or delayed |
| Tax deducted from employment income | Individual Tax 1.1 | Yes; beta, sandbox and production | Employment and tax year; also specified pension/benefit tax and refunds/set-offs | HMRC-held tax-year record | User-restricted OAuth 2.0; user consent and API subscription required | Refunds/set-offs need separate interpretation; not the same as Reserved's remaining liability |
| Employer-reported benefits | Individual Benefits 2.0 (latest subscribable beta; 2.1 is alpha) | Yes, if subscribed | Benefit and tax year | After employer reporting | User-restricted OAuth 2.0 | Add only if benefits are confirmed in v1 scope; data may arrive after the period being estimated |
| Synthetic PAYE fixtures | Individual PAYE Test Support 2.0 | Yes; sandbox only | Configurable test records for Benefits, Employment, Income and Tax | Test-controlled | Sandbox application subscription/credentials | Never production; 2.1 is currently alpha and not subscribable |
| Self Assessment calculation | Individual Calculations (MTD) 8.0 | Yes, in its MTD journey | Calculation for an MTD Self Assessment customer | Trigger/retrieve/finalisation flow | MTD OAuth scopes and journey requirements | Not a general real-time calculation endpoint and not a replacement for Reserved's continuous local estimator |
| Tax code changes, cumulative/non-cumulative operation and payroll-period detail | PAYE APIs reviewed above | Not established as a complete read capability for Reserved's intended journey | TBC | TBC | TBC | Do not claim availability until the exact documented response fields and permitted use are verified |
| Future tax-rule changes | HMRC Developer Hub changelogs/roadmaps and GOV.UK legislation/rates | Yes as published information, not as a personalised rule feed | API/release/tax-year level | Publication schedule | No taxpayer consent for public documents | Requires an owned monitoring and review process; never update production tax rules automatically without review and tests |

Official sources:

- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2
- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income/1.2
- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-tax/1.1
- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-benefits/1.1
- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/1.0
- https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-calculations-api/8.0
- https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/user-restricted-endpoints
- https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide

## Architectural decision

Reserved should retain its local, tax-year-versioned estimator and use HMRC as
a provenance-bearing evidence source for information HMRC currently holds. HMRC is
not a complete or necessarily current “golden source” for the user's whole tax
position. User, payslip, accounting and bank evidence must remain visible and
must not be silently overwritten.

The reconciliation answers:

> What tax does the available evidence show as already deducted or paid, and
> how does that change the estimated additional amount to set aside?

The core relationship is:

```text
Reserved estimated total liability
− reconciled tax already deducted or paid
= estimated additional amount to set aside (minimum £0)
```

An overpayment/conflict is reported separately; it must not produce a negative
set-aside amount or an unqualified statement that money is available to spend.

## Evidence and confidence rules

1. No source, including HMRC, has unconditional precedence. Selection considers
   tax year, employment identity, what the evidence represents, observation or
   effective date, recency and completeness together. Source type is at most a
   tie-breaker between otherwise equivalent observations.
2. All considered evidence retains its provenance, date and selection/exclusion
   status; a selected value does not overwrite a conflicting value.
3. Current HMRC observations and current source documents can both be strong
   direct evidence. Structured manual entry is less independently evidenced;
   bank-payment inference is indirect and a last resort.
4. Evidence is selected per employment where identities and representation are
   sufficiently clear.
5. An aggregate observation is never added to employment-level observations,
   avoiding double counting.
6. Material conflicts and stale/missing dates reduce confidence and remain
   visible for user review. Where competing known amounts permit it, Reserved
   records the resulting range or numerical effect on the estimate; otherwise
   it states that the effect is not reasonably determinable.
7. A connection failure never deletes existing user evidence.
8. Confidence describes evidence quality only. It is not a probability and not
   a guarantee that the tax estimate is correct or complete.
9. Missing evidence is not treated as evidence of zero, and a possible
   overpayment is not presented as an available or confirmed refund.

The dependency-free implementation is in
`reserved/engines/paye_reconciliation.py` with synthetic tests covering one and
multiple employments, conflicts, stale data, fallback levels, missing evidence
and overpayment.

## Non-HMRC fallback

The product journey should offer these acquisition routes. Their display order
does not establish evidence precedence:

1. **HMRC connection** — permissioned retrieval of HMRC-held PAYE evidence.
2. **Payslip/P45/P60 entry** — gross pay to date, tax paid to date, tax code,
   pay date/frequency and employment identity; source document date retained.
3. **Structured manual entry** — the same minimum year-to-date fields, with
   salary sacrifice/pension, bonuses and benefits requested where relevant.
4. **Bank inference** — clearly labelled as incomplete; do not reverse-engineer
   gross pay and tax from a net deposit as if it were direct evidence.

## Sandbox boundary

Sandbox application metadata supplied by the founder:

- Application: Reserved
- Application ID: `f6aa7710-1b34-48b9-8a46-7de8562eccae`
- Environment: Sandbox
- Created: 12 August 2026

The application ID is non-secret metadata. Client secrets, access tokens,
refresh tokens, test-user passwords and NINOs must remain in an approved secret
store and must never be committed or copied into reports.

Individual Employment 1.2, Individual Income 1.2 and Individual Tax 1.1 are
subscribed. Add Individual PAYE Test Support 2.0 before stateful fixture tests.
