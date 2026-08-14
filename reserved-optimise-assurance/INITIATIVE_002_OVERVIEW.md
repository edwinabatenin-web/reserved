# Whip Smart West Initiative 002
## Tax Optimisation Assurance Programme

**Status:** IN PROGRESS  
**Date initiated:** 10 August 2026  
**Feature under test:** Reserved™ Tax Opportunities / Optimise page  
**Engine version assurance applies to:** optimise.py v1.0.0  
**Tax year in scope:** 2026/27 (England / Wales / Northern Ireland)

---

## Purpose

Initiative 002 provides independent mathematical assurance for the tax
optimisation engine introduced in `reserved/engines/optimise.py`.

The assurance programme:
1. Implements each supported mechanism from statutory first principles,
   with no shared code with the product engine.
2. Runs the product engine against an independent oracle on representative
   archetypes and boundary conditions.
3. Verifies interaction families (pension + PA taper, pension + HICBC,
   combined thresholds, multi-source income).
4. Validates key UX and positioning invariants (no negative savings,
   no double-counting of relief, salary sacrifice never assumed).
5. Confirms Initiative 001 regressions remain green.

---

## Mechanisms Assurred

| Mechanism | Statutory source | Status |
|---|---|---|
| Personal Allowance taper | ITEPA 2003 s.35; Finance (No.2) Act 2015 | In scope |
| High Income Child Benefit Charge | Finance Act 2012 s.681B; revised April 2024 | In scope |
| Pension Relief at Source (band extension + ANI reduction) | Finance Act 2004 s.192; HMRC PTM044100 | In scope |
| Scottish income tax | ITEPA 2003 Part 4A | **Out of scope** — engine excluded |
| Salary sacrifice | — | **Out of scope** — never assumed available |
| Gift Aid ANI interaction | — | **Out of scope** — planned for future version |
| Dividend / savings income ordering | — | **Out of scope** |

---

## CB Rates Used (2026/27)

Child Benefit rates for 2026/27 (England / Wales / NI) are approximate,
uprated ~2 % from 2025/26.  The reference uses:

- Eldest child: £26.60 / week (annual: £1,383.20)
- Each additional child: £17.60 / week (annual: £915.20)

**Action required before shipping:**  
Verify against the HMRC 2026/27 rates announcement (typically published
April 2026).  If the rates differ materially, update both the product
engine (`optimise.py`) and the reference (`reference/hicbc_reference.py`)
and re-run the gate tests.

---

## Gate Structure

| Gate | Description | File |
|---|---|---|
| Gate 1 | Each mechanism in isolation vs reference | `tests/gate1_isolation.py` |
| Gate 2 | Representative archetypes and exact boundaries | `tests/gate2_archetypes.py` |
| Gate 3 | Interaction families and sequence tests | `tests/gate3_interactions.py` |
| Gate 4 | Extremes, invariants, adversarial UX, regressions | `tests/gate4_extremes.py` |

All four gates must PASS before the Optimise feature is considered launch-ready.

---

## Running the Tests

```bash
# From workspace root:
PYTHONPATH=. .venv/bin/python -m pytest reserved-optimise-assurance/tests/ -v

# Or from inside the directory:
cd reserved-optimise-assurance
PYTHONPATH=..:. ../.venv/bin/python -m pytest tests/ -v
```

---

## Governance

Same four-gate authority as Initiative 001 (Reserved West Initiative 001,
August 2026).  All gates PASS = "launch-ready" certification for the
optimise feature.

Gate decisions are recorded in `GATE_DECISIONS.md`.  The final summary
is in `FINAL_READINESS_SUMMARY.md`.
