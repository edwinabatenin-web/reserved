# WP7 Tranche H candidate derivation

Status: **independent fixture, review pending**. This note and `docs/fixtures/TRANCHE_H_CANDIDATE.json` are deliberately outside the WP7 assurance corpus and integrity manifest. They must not support an accuracy claim until independently reviewed, policy decisions are resolved and the gate artifacts are deliberately updated.

## Scope

The candidate matrix supplies three complementary views:

1. a mixed-income ordering case below the HICBC threshold, including gross relief-at-source pension treatment, property income, foreign tax evidence, savings, dividends, PAYE evidence and Class 4;
2. a Personal Allowance taper case with the same income families, full HICBC and separate annual Plan 2/PGL liabilities and payroll deductions;
3. a reconciliation-only case that keeps statutory liabilities and payment/deduction evidence distinct and labels the combined presentation as policy-dependent.

All arithmetic was derived from the primary sources recorded in the candidate pack. No production engine, historical West calculator, Optimise helper or shared expected-result generator was used.

## HMX-001

Income totals £60,000. The £5,000 gross RaS contribution reduces ANI to £55,000 and extends the taxable basic-rate band to £42,700. The £12,570 PA leaves £42,430 taxable non-savings income, wholly inside that extended band: £8,486.

Because total taxable income proceeds beyond the extended basic band, the PSA is £500. Of £2,000 savings, £1,500 is taxed at 40%: £600. The £500 Dividend Allowance is nil-rated but occupies band capacity; the remaining £2,500 dividends are taxed at 35.75%: £893.75. Pre-credit Income Tax is therefore £9,979.75.

Only the £15,000 sole-trade profit enters Class 4: (£15,000 − £12,570) × 6% = £145.80. ANI is not over £60,000, so HICBC is nil. Foreign tax and PAYE tax are evidence fields, not reductions silently embedded in the tax calculation.

## HMX-002

Income totals £113,000. The £10,000 gross RaS contribution reduces ANI to £103,000. PA is £12,570 − (£3,000 ÷ 2) = £11,070; the basic-rate band extends to £47,700.

Non-savings income is £110,000, leaving £98,930 taxable: £47,700 × 20% plus £51,230 × 40% = £30,032. The £500 higher-rate PSA leaves £500 savings taxed at 40% (£200). The £500 Dividend Allowance leaves £1,500 dividends taxed at 35.75% (£536.25). Pre-credit Income Tax is £30,768.25.

Class 4 is (£20,000 − £12,570) × 6% = £445.80. ANI is above £80,000, so the charge reaches 100%; £1,406.60 is floored to a £1,406 HICBC.

For the expressly annual Self Assessment loan basis, income after the gross pension is £103,000. Plan 2 is (£103,000 − £29,385) × 9% = £6,625.35, floored to £6,625. PGL is (£103,000 − £21,000) × 6% = £4,920. After £3,000 undergraduate and £1,800 postgraduate payroll deductions, £3,625 and £3,120 remain respectively: £6,745 combined.

## HMX-003 and policy boundary

The subtraction is arithmetic: £30,768.25 − £15,000 = £15,768.25, and £11,545 − £4,800 = £6,745. Adding unchanged Class 4 (£445.80) and HICBC (£1,406) produces the arithmetic sum £24,365.05. This is explicitly blocked from customer presentation and is not an approved combined tax-position output.

The following are not statutory expected results and require Reserved product/accounting approval:

- whether PAYE evidence is fresh, authoritative and conflict-free;
- whether payroll deductions may be displayed against annual loan liabilities before final reconciliation;
- whether Income Tax, NI, HICBC and loan amounts should appear as one combined customer figure;
- confidence labels, warnings and precedence between evidence sources;
- due dates, payments on account, coding adjustments, refunds, interest and penalties.

## Deliberate limitations

- Foreign Tax Credit Relief is excluded pending its own bounded validation.
- Residence, split-year, remittance and treaty questions are not validated.
- Residential finance-cost reduction is not present.
- Student-loan calculations are annual Self Assessment liabilities; payroll-period calculations are not inferred.
- The cases assume the supplied property figures are already valid taxable profits and that the stated income is included in the annual student-loan basis.
- HICBC assumes the taxpayer is the higher-ANI partner where stated and that the recorded benefit was received for the full charge period.
