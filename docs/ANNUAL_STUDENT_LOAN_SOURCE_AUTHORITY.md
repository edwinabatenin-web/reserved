# Annual Self Assessment student-loan source authority

Reviewed: 13 August 2026  
Purpose: close source-applicability gaps without changing or approving fixtures

## Official evidence now established

HMRC's current Tax Logic service guide publishes Self Assessment student-loan
calculation pseudocode:

- total Self Assessment income above the applicable plan threshold is the
  calculation basis;
- non-PAYE earned income includes taxable self-employment and specified
  property profits;
- specified non-PAYE unearned income is ignored when it does not exceed £2,000,
  but the whole amount is included when it exceeds £2,000;
- pension contributions are deducted in arriving at the loan-calculation total
  income;
- the calculated repayment is rounded down to the nearest whole pound before
  PAYE deductions are reconciled.

Source: [HMRC Tax Logic service guide — Tax calculation](https://developer.service.hmrc.gov.uk/guides/tax-logic-service-guide/documentation/tax-calculation.html).

HMRC's 2026/27 student-loan deduction tables separately establish the current
plan thresholds/rates and payroll-period rounding. They support threshold/rate
configuration but payroll examples must not be used as evidence that an annual
Self Assessment fixture models a payroll-period deduction.

Source: [2026 to 2027 Student and Postgraduate Loan deduction tables](https://www.gov.uk/government/publications/sl3-student-loan-deduction-tables/2026-to-2027-student-and-postgraduate-loan-deduction-tables).

HMRC's current Self Assessment guidance confirms that the return calculates an
undergraduate student-loan component at 9% of total Self Assessment income over
the borrower's plan threshold and a postgraduate component separately at 6%.

Source: [Tell HMRC about a student or postgraduate loan in your tax return](https://www.gov.uk/guidance/tell-hmrc-about-a-student-loan-in-your-tax-return).

## Remaining limitation

Current official public guidance reviewed here does not expressly state which
undergraduate plan threshold the annual Self Assessment calculation uses when
a borrower simultaneously has more than one undergraduate plan type. Current
HMRC employer guidance says payroll deducts only one undergraduate plan and,
where more than one plan is indicated, starts with the lowest threshold; a
postgraduate loan may be deducted in addition. That is direct payroll authority,
not sufficient proof that annual Self Assessment applies the identical
selection rule.

Sources:

- [Tell HMRC about a new employee — student loans](https://www.gov.uk/new-employee/student-loans)
- [HMRC Agent Update 140](https://www.gov.uk/government/publications/agent-update-issue-140/issue-140-of-agent-update)

## Assurance consequence

The annual income-basis and whole-pound-rounding provenance gap is substantially
resolved. Individual-plan and undergraduate-plus-postgraduate annual fixtures
can use the Tax Logic guide with the applicable 2026/27 threshold source,
subject to an independent reviewer confirming each fixture's facts and source
scope.

Simultaneous multiple-undergraduate annual Self Assessment fixtures remain
review-pending. They must not be promoted by inference from payroll guidance.
An explicit HMRC annual-calculation authority, sandbox Tax Logic evidence for
that state, or a deliberate exclusion/limitation is still required.

## Final multiple-undergraduate-plan search — 13 August 2026

### Search boundary

A final bounded search reviewed current official primary material across:

- HMRC's Tax Logic service guide, including its student-loan pseudocode and
  references to tax-year configuration;
- current HMRC/GOV.UK Self Assessment guidance, the SA100 form material, the
  Self Assessment Manual and Collection of Student Loans Manual;
- current MTD/Agent Update material describing student-loan plan data;
- current GOV.UK borrower guidance for multiple plan types;
- 2026/27 official thresholds and employer material; and
- legislation and official legislation search results for income-contingent
  student-loan repayment calculations.

Search terms deliberately combined “Self Assessment”, “annual”, “multiple”,
“more than one”, “undergraduate”, “plan type”, “lowest threshold”, “Tax Logic”
and the individual plan numbers. Payroll-only propositions were recorded but
not treated as annual Self Assessment authority.

### Exact findings

The Tax Logic guide models `planType`, `incomeThreshold` and `loanRate` in the
singular and says to use the correct threshold/rate for the plan type. Its
published pseudocode does not state how to select a plan where the borrower has
simultaneous undergraduate plan types, nor how multiple undergraduate balances
are represented in the configuration or calculation input.

Current Self Assessment guidance likewise asks for “the student loan plan type”
and says the undergraduate charge is 9% of total Self Assessment income above
the threshold for that plan type. HMRC CSLM13163 describes selecting Plan 1,
2, 4 or 5, with a postgraduate loan additionally possible. Agent Update 145
says MTD software holds a client's student-loan plan type (1, 2, 4 or 5), a
postgraduate loan, or both. None of these sources expressly resolves a state in
which two undergraduate plan types simultaneously apply to the annual Self
Assessment calculation.

Sources:

- [HMRC Tax Logic service guide — Tax calculation](https://developer.service.hmrc.gov.uk/guides/tax-logic-service-guide/documentation/tax-calculation.html)
- [Tell HMRC about a student or postgraduate loan in your tax return](https://www.gov.uk/guidance/tell-hmrc-about-a-student-loan-in-your-tax-return)
- [HMRC CSLM13163 — completing student-loan questions on an SA return](https://www.gov.uk/hmrc-internal-manuals/collection-of-student-loans-manual/cslm13163)
- [HMRC SAM121610 — student-loan cases](https://www.gov.uk/hmrc-internal-manuals/self-assessment-manual/sam121610)
- [HMRC Agent Update 145 — student loans within MTD](https://www.gov.uk/government/publications/agent-update-issue-145/issue-145-of-agent-update)

Current GOV.UK borrower guidance does establish a general substantive rule for
multiple undergraduate plans: repay 9% above the lowest threshold, as a single
repayment, with allocation between loans governed by a cap. The same page later
states that Self Assessment uses whole-year income. However, it illustrates the
multiple-plan rule with pay-period calculations and does not expressly say that
the lowest-threshold/cap mechanism is the annual Self Assessment calculation
implemented by HMRC Tax Logic. The 2026/27 terms-and-conditions guide similarly
discusses multiple-plan repayments using monthly examples before separately
describing collection through Self Assessment. These sources materially support
the general borrower liability rule but do not close the validation-critical
annual implementation and representation gap.

Sources:

- [Repaying your student loan — how much you repay](https://www.gov.uk/repaying-your-student-loan/what-you-pay)
- [Student loans: a guide to terms and conditions 2026 to 2027](https://www.gov.uk/government/publications/student-loans-a-guide-to-terms-and-conditions/student-loans-a-guide-to-terms-and-conditions-2026-to-2027)

Employer Bulletins, Agent Updates and the starter checklist explicitly direct
payroll to use the plan with the lowest threshold when more than one plan is
indicated. They are unambiguous payroll authority only and cannot establish the
annual Self Assessment calculation.

Sources:

- [HMRC Agent Update 140](https://www.gov.uk/government/publications/agent-update-issue-140/issue-140-of-agent-update)
- [February 2026 Employer Bulletin](https://www.gov.uk/government/publications/employer-bulletin-february-2026/february-2026-issue-of-the-employer-bulletin)

No reviewed legislation, public HMRC API schema, Tax Logic configuration page,
manual, form or current Self Assessment guidance exposed an explicit annual
multiple-undergraduate selection/allocation rule. This is a “not found in the
reviewed public official sources” result, not proof that HMRC has no internal
rule or that the general lowest-threshold rule is inapplicable.

### Stopping conclusion

The limitation remains. It would be unsafe to promote an annual
multiple-undergraduate fixture merely by applying payroll guidance or by
joining adjacent paragraphs from general borrower guidance. No further public-
source searching is proportionate unless HMRC publishes a specific Tax Logic
configuration/schema proposition or annual worked example.

The next admissible evidence is one of:

1. an explicit HMRC annual Self Assessment rule or Tax Logic configuration/
   schema for simultaneous undergraduate plan types;
2. controlled HMRC sandbox calculation evidence for representative combinations
   (including Plan 5 when applicable), independently reviewed and narrowly
   labelled as observed sandbox behavior; or
3. a deliberate product exclusion that refuses to calculate these cases and
   directs them to HMRC/accountant confirmation.

Until then, individual undergraduate and undergraduate-plus-postgraduate cases
remain supported as described above; simultaneous multiple-undergraduate cases
remain outside the admitted annual assurance scope.
