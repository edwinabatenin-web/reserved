# HICBC whole-number rounding defect

## Finding

The earlier calculations incompletely applied ITEPA 2003 section 681C(3). In addition to flooring the appropriate percentage and calculated charge, the relevant total Child Benefit amount must be floored before the percentage is applied. Omitting that first stage can overstate the charge by £1, including at 99% on a £1,406.60 award.

## Root cause

This is incomplete earlier test coverage and an incorrect staged-rounding interpretation, compounded by a misleading simplified formula in the code comments. The first repair added £200-step and final-charge boundaries but used award values/percentages where flooring the benefit first often happened to produce the same answer. It therefore missed the non-coincidental 99% case. No separate calculation path or unpromoted Reserved West correction was used to derive the corrected literals.

## Correction and prevention

The independent expected-result correction floors the relevant benefit total, floors and caps the percentage, applies that percentage to the floored benefit, and floors the resulting charge. RW3-HICBC-004 and RW3-HICBC-012 change from £1,392 to £1,391; 1%, 50%, 75% and 100% admitted cases are numerically unchanged after staged re-derivation. Regression expectations now expose the 99% case. Production must be corrected separately and must not be used to backfill validation literals.

## Final closure — 13 August 2026

Independent post-remediation replay confirms all three active calculation paths
now implement the staged rule: `internal_hicbc_scenario`,
`integrated_annual_position` and `optimise.calculate_position`. Each returned
£1,391 for the corrected 99% fixtures and for the non-coincidental ANI £79,800,
benefit £1,406.99 counterexample. Low-benefit 1%, midpoint and 100% cap cases
also agreed with their independently fixed literals.

The full relevant regression set passed (119 tests), and the corrected admitted
pack SHA-256 matched its integrity manifest. The deterministic rounding defect
and its material hold are closed for bounded 2026/27 arithmetic. This closure
does not approve ANI/pension derivation, partner or payment-period inference,
advice, persistence, API or customer use; those remain separately gated.

## Primary sources

- ITEPA 2003 section 681C as inserted by Finance Act 2012 Schedule 1: formula and whole-number rounding.
- Finance (No. 2) Act 2024 section 5: changes `L` to £60,000 and `X` to £200 for 2024/25 onwards.
- HMRC PAYE Manual PAYE14015: 1% for each £200 from 2024/25 onwards.
