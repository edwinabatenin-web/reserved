# Integrated annual position — independent assurance review

Review date: 13 August 2026  
Artifact: `reserved/engines/integrated_annual_position.py`  
Decision: **PASS for isolated internal calculation use only**

## Boundary and method

This was a review-only assessment against the independently approved RW3 v1
preimplementation propositions and the WP7U status/limitation semantics. The
review inspected the production implementation, independently recomputed
representative cases from rule literals, and ran the focused synthetic suite.
It did not use production helpers as an arithmetic oracle and did not alter
code, tests, fixtures, manifests or shared sprint records.

## Independent arithmetic checks

- Savings ordering: £15,570 non-savings leaves £3,000 taxable (£600); the
  savings starting-rate band falls to £2,000, the £1,000 PSA is nil-rated, and
  £4,000 interest at 20% gives £800. Total Income Tax: £1,400.
- PA taper: £99,500 employment plus £1,000 interest gives ANI £100,500 and PA
  £12,320. Taxable employment £87,180 gives £27,332; £500 interest after the
  higher-rate PSA gives £200. Total: £27,532.
- Dividend crossing: £49,498 employment leaves £772 basic-band capacity. The
  £500 dividend allowance occupies band capacity; £272 at 10.75% and £728 at
  35.75% give £29.24 and £260.26. Dividend Tax: £289.50.
- Property: £5,000 and negative £2,000 UK letting results aggregate to £3,000;
  with £30,000 employment, £20,430 is taxable at 20%, giving £4,086. A £2,000
  property loss remains carried forward and does not reduce employment.
- Class 4: £20,000 sole-trade profit leaves £7,430 above the £12,570 lower
  profits limit; 6% gives £445.80. Property profit does not enter Class 4.
- HICBC: ANI £79,999 contains 99 complete £200 steps above £60,000. Under the
  corrected staged interpretation, the relevant benefit £1,406.60 is first
  floored to £1,406; 99% is £1,391.94 and the final whole-pound charge is
  £1,391. At £80,000 the capped charge remains £1,406. The prior £1,392 review
  statement resulted from incomplete coverage and omission of the first
  statutory rounding stage, not from new production-derived evidence.

No discrepancy was found in the approved savings, dividend, mixed-income,
PA/ANI, UK-property, bounded foreign-property, Class 4 or HICBC propositions.

## Status and limitation controls

- `calculated` is used only where all applicable supported families have
  sufficient facts and `total_liability` is available.
- Unknown residence and ambiguous HICBC responsibility produce
  `insufficient_facts`, name the affected family, and withhold the total.
- Non-resident foreign-property treatment, Foreign Tax Credit Relief and the
  residential finance-cost reduction produce `unsupported_rule`, name the
  unsupported family, retain only the expressly pre-limitation amount, and
  withhold the total.
- Contradictory representations, impossible property configurations,
  boolean-as-money values and inconsistent ANI facts raise errors rather than
  being coerced into zero or a partial calculation.
- Ruleset, included families, unsupported families and limitations remain
  explicit. PAYE reconciliation and student-loan calculation are always named
  as not performed.

## Explicit exclusions

This verdict does **not** approve or validate:

- customer connection, presentation, reserve guidance, filing or payment use;
- Foreign Tax Credit Relief, treaties, non-resident liability, split-year or
  remittance-basis treatment;
- residential finance-cost tax-reduction arithmetic;
- PAYE reconciliation or tax-paid deductions;
- student-loan or postgraduate-loan liability or reconciliation;
- property ownership inference, Scottish tax, or tax years other than 2026/27.

The output remains an internal component result, not a complete tax bill or
WP7U customer envelope. Pre-FTCR and pre-finance-cost figures must retain their
named limitations and must not be promoted as totals.

## Verification

Focused execution: **55 tests passed** in
`tests/test_integrated_annual_position.py`.

## Verdict

**PASS for isolated internal calculation use within the literal approved
scope.** The implementation is not fit for customer connection or any of the
excluded calculations above. Any widening of inputs, tax rules, aggregation or
presentation requires separate evidence and assurance.
