# Initiative 002 — Final Readiness Summary

**Feature:** Tax Opportunities / Optimise  
**Engine:** `reserved/engines/optimise.py` v1.0.0  
**Tax year:** 2026/27 (England / Wales / Northern Ireland)  
**Date:** 10 August 2026  
**Status: ✓ CERTIFIED — all four gates PASS**

---

## Executive Summary

The Reserved™ Tax Optimise engine and its associated routes, template, and
test infrastructure were built and independently verified in a single session
on 10 August 2026.

All 136 gate tests pass across all four initiative gates.  The product test
suite (42 optimise-specific tests, 589 total) also passes in full.

The feature is ready for the October 2026 beta, subject to the pre-launch
actions below.

---

## Gate Results

| Gate | Description | Result | Tests |
|---|---|---|---|
| Gate 1 | Isolation — each mechanism vs independent reference | **PASS** | 37/37 |
| Gate 2 | Archetypes — representative users and exact boundaries | **PASS** | 24/24 |
| Gate 3 | Interactions — combined thresholds and state sequences | **PASS** | 24/24 |
| Gate 4 | Extremes — invariants, adversarial UX, RWI-001 regressions | **PASS** | 51/51 |

**Total: 136/136 passed**

---

## Mechanisms Certified

| Mechanism | Source | Result |
|---|---|---|
| Personal Allowance taper (PA_TAPER) | ITEPA 2003 s.35; Finance (No.2) Act 2015 | ✓ CERTIFIED |
| High Income Child Benefit Charge (HICBC) | Finance Act 2012 s.681B (revised April 2024) | ✓ CERTIFIED |
| Relief-at-Source pension: ANI reduction + BRL extension | Finance Act 2004 s.192; HMRC PTM044100 | ✓ CERTIFIED |

---

## Key Invariants Verified

- `total_benefit = it_reduction + hicbc_reduction` (exact, always)
- `basic_rate_relief_to_pension` never included in `total_benefit`
- `it_reduction ≥ 0` and `hicbc_reduction ≥ 0` for all valid inputs
- `HICBC charge ≤ annual_cb` always
- `after.income_tax ≤ before.income_tax` always
- `ANI ≥ 0` always (clamped at zero when pension > income)
- Negative `additional_pension` rejected with `ValueError`
- Salary sacrifice never assumed available in any output
- All scenarios include caveats and "what to confirm" lists

---

## Pre-Launch Actions Required

1. **Verify 2026/27 CB rates** against HMRC official announcement:
   - Engine uses: eldest £26.60/week, additional £17.60/week
   - If different, update `optimise.py` and `reference/hicbc_reference.py`; re-run gates.

2. **Confirm HICBC threshold** for 2026/27:
   - Engine uses: £60,000 lower, £80,000 upper (post-April 2024 thresholds)
   - Verify no further change was announced for 2026/27.

---

## Accepted Scope Limitations

| Item | Status |
|---|---|
| Scottish income tax | Out of scope — engine excludes Scotland |
| Salary sacrifice | Out of scope — never assumed; confirmed in invariants |
| Gift Aid ANI interaction | Deferred — planned for future version |
| Tapered Annual Allowance | Constraint warning only; not modelled |
| Carry-forward of unused AA | Constraint warning only; not modelled |
| Marriage Allowance | Out of scope |
| Dividend/savings income ordering | Out of scope |
