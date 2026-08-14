# Tranche H source-authority note

**Research date:** 13 August 2026  
**Scope:** three blockers identified in
`TRANCHE_H_INDEPENDENT_ASSURANCE_REVIEW.md`  
**Sources:** official legislation, HMRC manuals and GOV.UK guidance only  
**Change boundary:** no fixture, manifest, corpus, engine or gate record changed

## Conclusion

Current primary material resolves the three rule-source blockers narrowly:

1. legislation establishes the ordering of non-savings, savings and dividend
   income, and HMRC material confirms that the Personal Savings Allowance and
   Dividend Allowance are nil rates, not deductions from income;
2. student-loan Self Assessment rules start from section 23 step-1 total income,
   include all unearned income once it exceeds £2,000, and deduct qualifying
   pension-relief amounts not already excluded from step-1 income;
3. HICBC legislation rounds down the benefit amount, calculated percentage and
   resulting charge to whole numbers, while current HMRC guidance confirms the
   post-6-April-2024 £60,000/£80,000 and £200-per-percentage-point parameters.

This note supports re-review of the relevant Tranche H propositions. It does not
approve the candidate, prove all inputs factually complete, validate Foreign
Tax Credit Relief or settle HMX-003's evidence/presentation policy.

## 1. Mixed-income ordering and nil-rate bands

### Authoritative propositions

**Income Tax Act 2007, section 16** provides the ordering rule used to determine
rates. Savings and dividend income are treated as the highest parts of total
income; between them, dividend income is the higher part. The resulting stack
is therefore:

1. non-savings/non-dividend income;
2. savings income;
3. dividend income.

Section 16 also applies when determining the rates that would otherwise apply
to savings/dividend income. This is why each category consumes rate-band
capacity in that order; it is not permissible to tax each category against a
fresh basic-rate band.

HMRC's Savings and Investment Manual says:

- the savings starting rate is 0%;
- savings covered by the Personal Savings Allowance are charged at 0%;
- the dividend “allowance” is properly the dividend nil rate;
- dividend ordinary/upper/additional rates depend on the rate at which the
  dividend would otherwise be charged.

These are nil-rate slices of taxable income. They do not remove the income from
the section 16 ordering or restore rate-band capacity. The current GOV.UK rates
publication supplies the 2026/27 monetary amounts and dividend rates; it should
be used with section 16 rather than as the ordering authority.

### Application to HMX-001

On the candidate's stated assumptions:

- extended basic-rate limit: £42,700;
- taxable non-savings income: £42,430;
- basic-rate capacity remaining before savings: £270;
- savings income of £2,000 sits next; the £500 higher-rate-taxpayer PSA is a
  nil-rate slice that still occupies the first £500 of savings/band position;
- after that £500 slice, the remaining £1,500 savings lies above the extended
  basic-rate limit and is charged at 40% (£600);
- dividends sit above savings; the £500 Dividend Allowance is a dividend
  nil-rate slice and the remaining £2,500 lies in the higher-rate band, giving
  £2,500 × 35.75% = £893.75.

Thus the candidate's displayed HMX-001 savings/dividend allocation is supported
by the ordering and nil-rate propositions. This conclusion assumes the stated
income classifications, territorial scope, pension extension and absence of
other reliefs; it does not validate FTCR.

### Application to HMX-002

Taxable non-savings income already exceeds the extended basic-rate limit, so
the subsequent savings and dividend slices are in the higher-rate band. The
£500 PSA and £500 dividend nil rate occupy their respective ordered slices; the
remaining £500 savings at 40% and £1,500 dividends at 35.75% produce £200 and
£536.25 respectively.

### Primary links

- [Income Tax Act 2007, especially sections 13 and 16](https://www.legislation.gov.uk/ukpga/2007/3/contents)
- [HMRC SAIM1080 — savings/dividend rates and nil rates](https://www.gov.uk/hmrc-internal-manuals/savings-and-investment-manual/saim1080)
- [HMRC SAIM1090 — determining the applicable parts of income](https://www.gov.uk/hmrc-internal-manuals/savings-and-investment-manual/saim1090)
- [2026/27 Income Tax rates and allowances](https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past)

## 2. Annual Self Assessment student-loan income basis

### Starting point and deductions

Regulation 29 of the Education (Student Loans) (Repayment) Regulations 2009
calculates the repayment from the borrower's total income identified at step 1
of section 23 Income Tax Act 2007, adjusted by the regulation's exclusions and
deductions. HMRC's CSLM8520 summarises the same rule.

The regulation expressly deducts amounts receiving relief under Part 4,
Chapter 4 Finance Act 2004 (pension schemes etc.) that were not already included
in the section 23 step-1 calculation. This supports deduction of the **gross
amount receiving relief**, not merely the member's net cash contribution,
provided the candidate's `gross_ras_pension` is in fact an eligible contribution
receiving that relief. The source does not support deducting an ineligible,
excess or unrelieved contribution.

The statutory postgraduate-loan provisions use materially corresponding
step-1-income, exclusion and pension-relief language. A Plan 2 plus postgraduate
case still requires each liability to be calculated at its applicable rate and
threshold; it is not one blended threshold calculation.

### Unearned income

Regulation 29 and HMRC CSLM16035 establish:

- disregard unearned income where its total is £2,000 or less;
- where it exceeds £2,000, include the **whole amount**, not only the excess;
- the borrower must be within Self Assessment for this rule to apply.

Current GOV.UK guidance expressly lists PAYE employment, self-employed profits,
property income and unearned income over £2,000 as components of total Self
Assessment income. HMRC CSLM8520 defines unearned income for this purpose by
reference to income other than specified employment/trading sources.

For HMX-002, the candidate's property, savings and dividend amounts together
comfortably exceed £2,000. Therefore the all-or-nothing unearned-income rule
does not permit a £2,000 deduction: the full relevant unearned amount enters the
annual basis. Employment income and sole-trade profit also enter under the
step-1 starting point/current GOV.UK list. On the stated facts, subtracting the
£10,000 gross qualifying RaS contribution from £113,000 produces the candidate's
£103,000 loan basis.

### Important limitations

- This conclusion assumes every income figure is the amount that enters section
  23 step 1 and that the property/foreign-property figures are taxable profits,
  not gross receipts or amounts subject to a separate loss/relief adjustment.
- The sources do not validate residence, remittance basis, treaty treatment,
  foreign loss relief or FTCR.
- The gross pension deduction is supported only to the extent relief is actually
  given under the cited pension legislation and the amount was not already
  excluded from total income. The fixture should retain that eligibility
  assumption explicitly.
- The £2,000 rule is a gate: at exactly £2,000 unearned income is disregarded;
  once above £2,000 the whole amount is included. HMX-002 is not near that
  boundary, but boundary fixtures remain necessary elsewhere.
- PAYE loan deductions are separately evidenced credits against the annual
  liability. They do not alter the statutory annual income basis.

### Primary links

- [Education (Student Loans) (Repayment) Regulations 2009, regulation 29](https://www.legislation.gov.uk/uksi/2009/470/contents)
- [HMRC CSLM8520 — legislation and regulation 29 summary](https://www.gov.uk/hmrc-internal-manuals/collection-of-student-loans-manual/cslm8520)
- [HMRC CSLM16035 — unearned-income rule](https://www.gov.uk/hmrc-internal-manuals/collection-of-student-loans-manual/cslm16035)
- [Current GOV.UK Self Assessment student/postgraduate-loan guidance](https://www.gov.uk/guidance/tell-hmrc-about-a-student-loan-in-your-tax-return)
- [Education (Postgraduate Master's Degree Loans) Regulations 2016](https://www.legislation.gov.uk/uksi/2016/606/contents)

## 3. HICBC whole-pound rounding

### Authoritative propositions

Income Tax (Earnings and Pensions) Act 2003 sections 681B–681C, inserted by
Finance Act 2012 Schedule 1 and subsequently amended for the current thresholds,
define the charge. Section 681C(3) says that where:

- the relevant total Child Benefit amount;
- the calculated charge; or
- the calculated percentage

is not a whole number, it is rounded down to the nearest whole number. The
Finance Act 2012 explanatory notes confirm that the rounding applies at every
stage of the formula.

HMRC PAYE14015, updated in August 2026, confirms that for 2024/25 onwards the
charge is 1% of the full award for each £200 between £60,000 and £80,000, and
the full award above £80,000. Its example turns £453-and-pence into £453,
consistent with statutory downward whole-pound rounding.

### Application to HMX-002

The candidate states ANI £103,000 and that the taxpayer is the higher-ANI
partner. That is above £80,000, so the percentage is capped at 100%. The stated
annual Child Benefit of £1,406.60 is rounded down to £1,406 for the formula; the
100% charge is therefore £1,406. The candidate's `hicbc_percentage: "100"` and
`hicbc: "1406.00"` are supported on these assumptions.

This does not establish that £1,406.60 is the taxpayer's actual award. It assumes
the cited weekly rate, 52 qualifying weeks, receipt rather than an effective
non-payment election, and no partnership/claim-period changes.

### Primary links

- [Finance Act 2012 Schedule 1 / sections 681B–681C as enacted](https://www.legislation.gov.uk/ukpga/2012/14/schedule/1)
- [Finance Act 2012 explanatory notes on formula rounding](https://www.legislation.gov.uk/ukpga/2012/14/notes/division/1/1/2/1)
- [HMRC PAYE14015 — current thresholds and worked example](https://www.gov.uk/hmrc-internal-manuals/paye-manual/paye14015)
- [HMRC Child Benefit Technical Manual overview](https://www.gov.uk/hmrc-internal-manuals/child-benefit-technical-manual/cbtm01020)
- [Current Child Benefit rates](https://www.gov.uk/child-benefit/what-youll-get)

## Effect on the review blockers

| Review blocker | Research outcome | Remaining limitation |
|---|---|---|
| Mixed-income ordering and nil-rate band occupation | **Resolved for HMX-001/002 stated facts** | Exact income classifications and all other reliefs remain assumed; no FTCR validation |
| HMX-002 annual loan basis, gross RaS pension and unearned/property income | **Resolved conditionally** | Pension must actually receive qualifying relief; input property/foreign amounts must be valid step-1 taxable income; foreign/residence reliefs remain excluded |
| HICBC whole-pound rounding | **Resolved for stated full-award/full-charge case** | Actual award weeks, elections and partner/claim-period facts remain evidence inputs |

The source position now supports a deliberate re-review of HMX-001 and HMX-002.
It does not resolve HMX-003's absence of provenance-rich deduction evidence or
its customer-presentation policy block, and it does not itself authorise fixture
admission or a corpus/manifest change.

