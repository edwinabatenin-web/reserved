# 2026/27 tax-rule audit

Audit date: 12 August 2026. Territory: England, Wales and Northern Ireland. “Configured” does not mean the rule is fully integrated into an annual liability calculation.

| Rule | 2026/27 official value | Previous configured value | Result / action | Calculation status |
|---|---:|---:|---|---|
| Personal allowance | £12,570; taper £1 per £2 over £100,000 | same | confirmed | incremental engine present; interaction validation required |
| Non-savings income | 20% / 40% / 45%; higher-rate threshold £50,270; additional threshold £125,140 | same | confirmed | incremental engine present; annual multi-income engine incomplete |
| Class 4 NI | 6% from £12,570 to £50,270; 2% above | same | confirmed | present |
| Dividend allowance | £500 | absent from central rules | added | annual calculation missing |
| Dividend rates | 10.75% / 35.75% / 39.35% | absent from central rules | added | annual calculation missing |
| Savings starting rate | up to £5,000 | absent from central rules | added | annual calculation missing |
| Personal Savings Allowance | £1,000 / £500 / £0 | absent from central rules | added | annual calculation missing |
| UK property income | ordinary 20% / 40% / 45% rates in 2026/27 | not modelled as a full position | no false implementation | missing |
| Foreign property income | depends on UK-resident taxpayer facts and reliefs | not modelled | no false implementation | missing; requirements and relief boundaries needed |
| HICBC | starts over £60,000 adjusted net income; 1% of benefit per £200; full at £80,000 | thresholds present only in opportunity engine | centralised | liability integration missing |
| Child Benefit used by HICBC | £27.05 eldest/only child and £17.90 each additional child weekly | £26.60 / £17.60 | corrected | scenario present; annual liability missing |
| Student loans | Plan 1 £26,900; Plan 2 £29,385; Plan 4 £33,795; Plan 5 £25,000 at 9%; postgraduate £21,000 at 6% | thresholds correct | confirmed | present |
| Multiple student-loan plans | one 9% undergraduate calculation using lowest applicable threshold; postgraduate 6% additionally | charged each undergraduate plan separately | corrected | synthetic regression tests added |
| MTD qualifying-income thresholds | over £50k (2026), over £30k (2027), over £20k (2028), based on relevant prior return | same | confirmed | readiness engine present; filing out of v1 |

## Primary sources

- [Income Tax rates and Personal Allowances](https://www.gov.uk/income-tax-rates)
- [Self-employed National Insurance rates](https://www.gov.uk/national-insurance/how-much-you-pay)
- [Dividend tax](https://www.gov.uk/tax-on-dividends)
- [2026 dividend, property and savings rate technical note](https://www.gov.uk/government/publications/changes-to-tax-rates-for-property-savings-and-dividend-income/change-to-tax-rates-for-property-savings-and-dividend-income-technical-note)
- [Tax on savings interest](https://www.gov.uk/apply-tax-free-interest-on-savings)
- [HICBC threshold measure](https://www.gov.uk/government/publications/income-tax-increasing-the-high-income-child-benefit-charge-threshold)
- [Child Benefit rates](https://www.gov.uk/government/publications/rates-and-allowances-tax-credits-child-benefit-and-guardians-allowance/tax-credits-child-benefit-and-guardians-allowance)
- [Repaying student loans with more than one plan](https://www.gov.uk/repaying-your-student-loan/what-you-pay)
- [Making Tax Digital for Income Tax](https://www.gov.uk/guidance/check-if-youre-eligible-for-making-tax-digital-for-income-tax)

## Material conclusion

The central configuration is more complete and two defects have been corrected, but the v1 engine is not feature-complete: dividends, savings, UK/foreign property and HICBC still need an integrated annual calculation, and PAYE/student-loan deductions need full-position reconciliation. Reserved West validation has not yet been achieved.

