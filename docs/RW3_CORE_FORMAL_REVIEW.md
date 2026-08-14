# RW3 core fixture pack — formal independent review

## Split review and partial promotion — 13 August 2026

Reviewer: Codex independent second-person split review stream  
Decision: **43 fixtures approved; 3 unchanged fixtures isolated and remain pending**

HMRC's current Tax Logic service guide closes the annual Self Assessment
income-basis and whole-pound-flooring provenance gap identified in the earlier
reviews below. Together with the pack's 2026/27 threshold/rate sources and
general annual-return guidance, it supports the individual undergraduate-plan,
postgraduate-only and undergraduate-plus-postgraduate fixtures.

It does not expressly establish the annual Self Assessment rule when a borrower
simultaneously holds more than one undergraduate plan. The only remaining
unsupported fixtures are therefore:

| Fixture | Pending proposition |
|---|---|
| RW3-SL-001 | Plans 1 and 2: use Plan 1's lower threshold once, with no second undergraduate charge. |
| RW3-SL-002 | Plans 1 and 2 plus PGL: use the lower undergraduate threshold once, then add the separate PGL component. The separate PGL arithmetic is supportable, but the combined literal depends on the unresolved undergraduate selection. |
| RW3-SL-009 | Plans 1 and 5: use Plan 5's lower threshold once, with no separate Plan 1 charge. |

Those three fixture objects were copied without changing their IDs, inputs,
expected values, derivations or pending statuses into
`docs/fixtures/RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json`. The new pack
retains every original source and adds the Tax Logic authority with an express
statement that it does not establish simultaneous-plan selection. It remains
`independent_fixture_review_pending` and stays inside the corpus and integrity
manifest, so the evidence is deferred rather than deleted or counted as an
accuracy pass.

`docs/fixtures/RW3_CORE_FIXTURES.json` now contains the other 43 fixture objects.
They have been independently re-reviewed against the fixture-by-fixture
arithmetic findings below and the updated annual-loan authority. All are
supportable and are promoted to `independent_validation`. No input, derivation
or expected value was changed in the split. The core pack sources add the Tax
Logic guide as applicable annual-SA methodology authority.

This split does not validate simultaneous multiple-undergraduate annual-SA
treatment, does not infer annual rules from payroll guidance and does not open
the overall corpus gate while the three-fixture pack remains pending.

## Subsequent source-authority update — 13 August 2026

HMRC's current Tax Logic service guide now supplies direct public methodology
for annual Self Assessment loan income, pension deductions, the £2,000
unearned-income rule and whole-pound flooring. This materially narrows the
source-applicability rejection recorded below. It does not expressly establish
the annual Self Assessment treatment of simultaneous multiple undergraduate
plans, so the pack remains review-pending and must be re-reviewed rather than
partially or automatically promoted. See
`docs/ANNUAL_STUDENT_LOAN_SOURCE_AUTHORITY.md`.

Review date: 13 August 2026  
Reviewer: Codex independent second-person review stream  
Artifact: `docs/fixtures/RW3_CORE_FIXTURES.json`  
Decision: **REJECTED FOR PROMOTION AFTER RE-REVIEW — remains `independent_fixture_review_pending`**

Re-review update, 13 August 2026: RW3-PEN-005 has been corrected to £42,516.20 and is now supportable. The added loan sources improve the distinction between annual Self Assessment and payroll deductions, but do not fully close the provenance gate. The SA110 page currently provides the 2026 return and notes for tax year 2025/26, not a 2026/27 annual calculation. The general GOV.UK return guidance establishes annual total-income calculation, separate undergraduate/PGL components and deduction reconciliation, but it does not expressly establish the lowest-threshold-once rule for a person simultaneously holding multiple undergraduate plan types in annual Self Assessment. Promotion therefore remains blocked.

## Review boundary

All 46 fixtures were reviewed for source applicability, arithmetic, rounding, semantics and stated limitations under `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`. The review used official GOV.UK/HMRC rules and manual arithmetic only. It did not execute or inspect production calculation helpers, the historical West calculator, Optimise helpers or shared expected-result generators.

The original pension defect is remediated. The pack is still not promoted because the 2026/27 annual Self Assessment student-loan rounding and multiple-undergraduate-plan semantics are not both supported by tax-year-applicable cited authority. The manifest and pack metadata remain unchanged.

## Official rule basis applied

- 2026/27 Personal Allowance £12,570; withdrawal of £1 per £2 of adjusted net income above £100,000.
- England, Wales and Northern Ireland taxable basic-rate band £37,700; non-savings rates 20%, 40% and 45%.
- Gross relief-at-source pension contributions reduce ANI and extend the basic-rate limit; the higher-rate limit correspondingly moves by the gross contribution when determining the additional-rate slice.
- 2026/27 Class 4: 6% above £12,570 through £50,270 and 2% above £50,270.
- Annual loan thresholds: Plan 1 £26,900, Plan 2 £29,385, Plan 4 £33,795, Plan 5 £25,000 and PGL £21,000; undergraduate rate 9% and PGL rate 6%.
- For an annual Self Assessment fixture, annual repayment rounding and the treatment of deductions already made must be supported by annual Self Assessment guidance. Payroll SL3 deduction tables establish payroll-period treatment, not by themselves annual-SA semantics.

## Fixture decisions

| Fixture | Decision | Independent review finding |
|---|---|---|
| RW3-IT-001 | Supportable | PA £12,570; taxable £87,429; £7,540 + £19,891.60 = £27,431.60. |
| RW3-IT-002 | Supportable | At ANI £100,000 the full PA remains; tax £27,432.00. |
| RW3-IT-003 | Supportable | £1 excess withdraws £0.50 PA; taxable £87,431.50; tax £27,432.60. Half-pound allowance semantics are explicit. |
| RW3-IT-004 | Supportable | £10,000 excess withdraws £5,000 PA; tax £33,432.00. |
| RW3-IT-005 | Supportable | PA is nil at £125,140; £37,700 at 20% and £87,440 at 40% gives £42,516.00. |
| RW3-PEN-001 | Supportable | Gross RaS £10,000 restores ANI to £100,000 and extends basic band to £47,700; tax £29,432.00. |
| RW3-NI-001 | Supportable | £37,700 at 6% plus £9,730 at 2% gives £2,456.60. |
| RW3-SL-001 | Arithmetic supportable; provenance blocker | £40,000 less Plan 1 threshold £26,900 at 9% gives £1,179 once. Lowest-undergraduate-plan treatment is supported, but annual-SA basis/rounding provenance must be added rather than relying on payroll material. |
| RW3-SL-002 | Arithmetic supportable; provenance blocker | £1,179 undergraduate plus £1,140 PGL = £2,319. Annual-SA component treatment and rounding require applicable cited authority. |
| RW3-IT-006 | Supportable | With no pension extension, the pound above £125,140 is taxed at 45%; £42,516.45. |
| RW3-IT-007 | Supportable | £7,540 + £34,976 + £2,187 = £44,703.00. |
| RW3-PEN-002 | Supportable | ANI £100,000, PA £12,570, extended basic band £62,840 and remaining £49,730 at 40%; tax £32,460.00. |
| RW3-NI-002 | Supportable | Exact lower profits limit produces nil Class 4. |
| RW3-NI-003 | Supportable | £1 above lower limit at 6% gives £0.06. |
| RW3-NI-004 | Supportable | £37,700 at 6% gives £2,262.00. |
| RW3-NI-005 | Supportable | One pound above upper limit adds £0.02; total £2,262.02. |
| RW3-SL-003 | Arithmetic supportable; provenance blocker | Exact Plan 2 annual threshold produces nil; add annual-SA authority. |
| RW3-SL-004 | Arithmetic supportable; provenance blocker | £0.09 annual amount floors to £0 only under the asserted annual-SA rounding basis; SL3 payroll tables are not sufficient provenance for that assertion. |
| RW3-SL-005 | Arithmetic supportable; provenance blocker | £0.06 annual PGL amount floors to £0 under annual-SA rounding; applicable annual-SA authority is missing from pack sources. |
| RW3-IT-008 | Supportable | £37,699 taxable at 20% gives £7,539.80. |
| RW3-IT-009 | Supportable | Exact £37,700 taxable basic band gives £7,540.00. |
| RW3-IT-010 | Supportable | Next pound is at 40%; tax £7,540.40. |
| RW3-IT-011 | Supportable | PA £0.50, taxable £125,138.50; tax £42,515.40. |
| RW3-PEN-003 | Supportable | ANI £100,001, PA £12,569.50, extended band £47,700; tax £29,432.60. |
| RW3-PEN-004 | Supportable | ANI £100,000, PA £12,570, extended band £47,701; tax £29,432.20. |
| RW3-PEN-005 | Supportable after remediation | A £1 gross RaS contribution extends the basic-rate limit to £37,701 and the higher-rate limit to £125,141. £7,540.20 + £34,976.00 = **£42,516.20**; no income remains at 45%. Corrected literal and derivation agree. |
| RW3-NI-006 | Supportable | Below lower profits limit; nil. |
| RW3-NI-007 | Supportable | £37,699 at 6% gives £2,261.94. |
| RW3-SL-006 | Arithmetic supportable; provenance blocker | £12 × 9% = £1.08, asserted annual floor £1; add annual-SA rounding authority. |
| RW3-SL-007 | Arithmetic supportable; provenance blocker | £17 × 6% = £1.02, asserted annual floor £1; add annual-SA rounding authority. |
| RW3-SL-008 | Arithmetic supportable; provenance blocker | Plan 5: £12 × 9% = £1.08, asserted annual floor £1; add annual-SA rounding authority. |
| RW3-SL-009 | Arithmetic supportable; provenance blocker | Lowest undergraduate threshold is Plan 5: £15,000 × 9% = £1,350 once. Annual-SA/multiple-plan applicability must be cited explicitly. |
| RW3-SL-010 | Arithmetic supportable; provenance blocker | £1 below Plan 1 threshold; nil. |
| RW3-SL-011 | Arithmetic supportable; provenance blocker | Exact Plan 1 threshold; nil. |
| RW3-SL-012 | Arithmetic supportable; provenance blocker | £0.09 floors to nil under annual-SA rounding; applicable authority absent. |
| RW3-SL-013 | Arithmetic supportable; provenance blocker | £1.08 floors to £1 under annual-SA rounding; applicable authority absent. |
| RW3-SL-014 | Arithmetic supportable; provenance blocker | £1 below Plan 2 threshold; nil. |
| RW3-SL-015 | Arithmetic supportable; provenance blocker | £1 below Plan 4 threshold; nil. |
| RW3-SL-016 | Arithmetic supportable; provenance blocker | Exact Plan 4 threshold; nil. |
| RW3-SL-017 | Arithmetic supportable; provenance blocker | £0.09 floors to nil under annual-SA rounding; applicable authority absent. |
| RW3-SL-018 | Arithmetic supportable; provenance blocker | £1.08 floors to £1 under annual-SA rounding; applicable authority absent. |
| RW3-SL-019 | Arithmetic supportable; provenance blocker | £1 below Plan 5 threshold; nil. |
| RW3-SL-020 | Arithmetic supportable; provenance blocker | Exact Plan 5 threshold; nil. |
| RW3-SL-021 | Arithmetic supportable; provenance blocker | £0.09 floors to nil under annual-SA rounding; applicable authority absent. |
| RW3-SL-022 | Arithmetic supportable; provenance blocker | £1 below PGL threshold; nil. |
| RW3-SL-023 | Arithmetic supportable; provenance blocker | Exact PGL threshold; nil. |

## Required remediation before re-review

1. Add tax-year-applicable official authority for **2026/27 annual Self Assessment** whole-pound rounding of undergraduate and postgraduate components. The SA110 page reviewed on 13 August 2026 exposes the 2026 return/notes for tax year 2025/26; it is evidence of established SA treatment but is not itself a 2026/27 calculation note.
2. Add official authority expressly covering simultaneous multiple undergraduate plan types in **annual Self Assessment**, including use of the lowest applicable threshold once. Agent Update 140 expressly addresses payroll agents; the general return guidance describes “your repayment plan type” and undergraduate plus PGL, but does not state the multiple-undergraduate rule.
3. Alternatively, remove or separately defer RW3-SL-001, RW3-SL-002 and RW3-SL-009 from this pack and bound the remaining annual fixtures only if the adopted standard accepts prior-year procedural rounding as sufficiently applicable to 2026/27. Such a scope change requires deliberate re-review and cannot be inferred here.
4. Obtain a fresh second-person review after the provenance gap is closed.

## Pack verdict

**REJECTED FOR PROMOTION AFTER RE-REVIEW.** All 46 literals are now arithmetically supportable, including corrected RW3-PEN-005. The remaining failure is source applicability: annual loan rounding is evidenced only by a prior-tax-year SA110 note, and lowest-threshold treatment for multiple undergraduate plans is evidenced in payroll guidance rather than expressly in annual-SA guidance. Because the Independence Standard requires applicable tax-year and semantic provenance, the pack remains `independent_fixture_review_pending`. No fixture status, pack review metadata or integrity-manifest entry was changed.
