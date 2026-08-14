# Independent v1 tax validation fixtures

**Status:** synthetic manual validation, 12 August 2026  
**Jurisdiction/year:** England, Wales and Northern Ireland; 2026/27  
**Executable cases:** `tests/test_independent_v1_validation.py`

## Independence method

Expected results were worked manually from published HMRC/SLC thresholds and
band widths, then entered as literal amounts. The test oracle does not import
Reserved rule configuration and does not reproduce the production algorithm.
Inputs describe fictional people and contain no customer or sandbox data.

This is useful engineering validation, but is not a substitute for review by a
qualified tax specialist or HMRC-recognised filing calculation specifications.

## Fixture register

| ID | Synthetic position | Literal expected result | Current result |
|---|---|---:|---|
| IT-01 | £30,000 non-savings income | Income tax £3,486.00 | Pass |
| IT-02 | £60,000 non-savings income | Income tax £11,432.00 | Pass |
| PA-01 | £110,000, no pension | PA £7,570; income tax £33,432.00 | **Known failure** |
| PA-02 | £100,000 plus £10,000 income | Incremental income tax £6,000.00 | **Known failure** |
| PA-03 | £125,140, no pension | PA £0; income tax £42,516.00 | **Known failure** |
| NI-01 | Sole-trade profit £12,000 plus £1,000 | Incremental Class 4 £25.80 | Pass |
| NI-02 | Sole-trade profit £50,000 plus £1,000 | Incremental Class 4 £30.80 | Pass |
| SL-01 | Plan 2 at/above £29,385 | £0 then £90 on next £1,000 | Pass |
| SL-02 | Plans 2 and 5, £25,000 plus £5,000 | One 9% charge: £450.00 | Pass |
| SL-03 | Plan 2 plus PGL, £30,000 plus £5,000 | 9% + 6%: £750.00 | Pass |
| CB-01 | ANI £60k/£70k/£80k, one child | £0/£703.00/£1,406.00 HICBC | Pass after statutory-rounding correction |
| CB-02 | £70k income, £10k gross RaS pension | ANI £60k; HICBC £0; IT £13,432 | Pass |
| PA-04 | £110k, compare no pension with £10k RaS | Income-tax reduction £4,000 | **Known failure** |
| PY-01 | Two current HMRC employment observations | Sum £2,500; remaining £7,500 | Pass |
| PY-02 | Aggregate and employment-level observations | Use £2,500 aggregate once | Pass |

## Material finding: reduced Personal Allowance changes the gross coordinate

The statutory basic-rate band is **£37,700 of taxable income**. The current
engine uses £50,270 as a fixed gross-income boundary. That happens to give the
right answer with the standard £12,570 Personal Allowance, but becomes wrong
when the allowance tapers.

At £110,000:

1. Personal Allowance is £12,570 − (£10,000 ÷ 2) = £7,570.
2. Taxable income is £102,430.
3. £37,700 at 20% is £7,540.
4. £64,730 at 40% is £25,892.
5. Total is £33,432.

The production result observed during this validation was £32,432. The defect
also understates the £100,000–£110,000 marginal income tax by £1,000 and the
total at £125,140 by £2,514. It affects PA-taper and pension-scenario outputs and
must be corrected before West validation can pass.

The four affected executable cases are marked `expectedFailure`, so they
document the present defect without making every test run fail. Once the engine
is corrected they become unexpected successes and force the marker to be
removed.

## Primary sources

- [HMRC income-tax rates and allowances](https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past)
- [HMRC National Insurance rates](https://www.gov.uk/national-insurance/how-much-you-pay)
- [HMRC Employer Bulletin: 2026/27 student-loan thresholds](https://www.gov.uk/government/publications/employer-bulletin-december-2025/december-2025-issue-of-the-employer-bulletin)
- [Student Loans Company: multiple plan types](https://www.gov.uk/government/publications/student-loans-a-guide-to-terms-and-conditions/student-loans-a-guide-to-terms-and-conditions-2026-to-2027)
- [HMRC High Income Child Benefit Charge](https://www.gov.uk/child-benefit-tax-charge)
- [HMRC 2026/27 Child Benefit rates](https://www.gov.uk/government/publications/budget-2025-overview-of-tax-legislation-and-rates-ootlar/annex-a-rates-and-allowances)
