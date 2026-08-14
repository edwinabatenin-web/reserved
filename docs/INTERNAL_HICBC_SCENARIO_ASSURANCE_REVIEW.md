# HICBC calculation paths — final bounded independent assurance review

Review date: 13 August 2026  
Scope: `internal_hicbc_scenario`, `integrated_annual_position` and `optimise.calculate_position`  
Decision: **PASS for their declared bounded internal calculation purposes**

## Review basis

The three active paths were checked against the corrected admitted independent
HICBC fixtures and the retained official-source derivation in
`TRANCHE_H_SOURCE_AUTHORITY_NOTE.md`. No path's output was used to derive the
expected results. Under ITEPA 2003 section 681C(3), the relevant total Child
Benefit amount is rounded down, the complete-£200 percentage is rounded down
and capped, and the calculated charge is then rounded down.

## Counterexample replay

All three paths returned the same independently derived result for every direct
case below:

| ANI | Benefit | Percentage | Charge |
|---:|---:|---:|---:|
| £60,200 | £99.99 | 1% | £0 |
| £60,200 | £100.00 | 1% | £1 |
| £70,000 | £1,406.60 | 50% | £703 |
| £79,800 | £1,406.60 | 99% | £1,391 |
| £79,999 | £1,406.60 | 99% | £1,391 |
| £79,800 | £1,406.99 | 99% | £1,391 |
| £80,000 | £1,406.99 | 100% | £1,406 |
| £80,200 | £1,406.60 | 100% | £1,406 |

The £79,800/£1,406.99 case closes the original non-coincidental defect: floor
the benefit to £1,406, apply 99% to obtain £1,391.94, then floor the charge to
£1,391. The corrected admitted fixtures `RW3-HICBC-004` and
`RW3-HICBC-012` likewise return £1,391 in every applicable path.

## Regression and integrity evidence

- **119 relevant tests passed**, covering the isolated scenario, integrated
  position, Optimise/independent validation, literal fixture runner, fixture
  integrity, and internal exposure boundary.
- The admitted pack digest is
  `e9c9d1da029f277d9a7316a1e9c3ed4d10c629c14442fed9a2acacfae136f7e2`,
  exactly matching `WP7_FIXTURE_INTEGRITY.json`.
- Existing boundary, midpoint, cap, additional-child, partial-period,
  responsibility-fact, pension-ANI and invalid-input coverage remains green.
- The isolated scenario continues to fail closed when higher-ANI responsibility
  or full charge-period facts are not affirmatively confirmed and retains its
  recommendation/customer/reserve/filing/payment prohibitions.

## Supported purpose and limitations

This PASS supports deterministic 2026/27 HICBC arithmetic within the facts each
path expressly accepts. For `internal_hicbc_scenario`, it supports only an
isolated factual before/after ANI comparison. For the integrated path it
supports the admitted HICBC component within that producer's separately assured
scope. For Optimise it closes this arithmetic defect only; it does not transform
the legacy scenario surface into regulated advice or a customer-ready annual
position.

The PASS does not infer ANI, pension relief or annual-allowance eligibility,
partner responsibility, actual award weeks, payment elections or charge-period
completeness. It does not approve persistence, API exposure, recommendation,
reserve guidance, filing or payment use. Those facts and uses retain their own
fail-closed and later-gate requirements.

## Adequacy, material hold and stopping rule

The deterministic HICBC staged-rounding material hold **can close**. The exact
counterexample now passes in all three paths, both corrected admitted fixtures
pass, integrity is coherent, and the relevant regression set is green. No known
material deterministic HICBC arithmetic discrepancy remains within this
declared scope.

Further review is unlikely to change this bounded decision. Reopen only for a
tax-year/rule change, altered rounding sequence, new HICBC input derivation,
changed partner/payment-period policy, changed calculation path, contradictory
literal, or expansion into persistence/API/customer/advice use.

## Verdict

**PASS for the declared bounded internal calculation purposes. The deterministic
HICBC material hold can close.**
