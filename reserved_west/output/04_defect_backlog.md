# Prioritised Defect Backlog
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06
**Engine version:** 2.0.1

## Severity key
- **Critical** — systemic; stops Gate progression
- **High** — significant unexplained variance
- **Medium** — isolated; within acceptable tolerance
- **Low** — edge case or tolerance zone

## Active defects

_No active defects found._

---

### EL-003 — eBRL cap at Additional Rate Threshold suppressed 45 % additional rate
**Severity at time of discovery:** High
**Status:** ✅ Resolved in engine v2.0.1
**Discovery:** Reserved West Initiative 001, Stage 3 (scenario RW-S3-011)
**Resolution date:** 2026-08-06

**Description**
When a pension contribution exceeded £74,870 (= ART − BRL = £125,140 − £50,270),
the extended basic-rate limit computed inside `_total_income_tax` was not capped
at the Additional Rate Threshold.  The uncapped eBRL exceeded £125,140, which
caused `_income_tax_between` to process the ART and additional-rate band as part
of the basic-rate (20 %) slice.  The 45 % rate was silently suppressed on all
income above £125,140.

**Trigger condition:** `pension > £74,870`.  For pension ≤ £74,870 the cap is
never reached and results were numerically identical to the fixed engine.

**Variance observed:** RW-S3-011: engine £1,000 vs reference £2,215 = −£1,215

**Resolution:** Engine v2.0.1 caps eBRL at ART in `_total_income_tax`:
```python
extended_basic_rate_limit = min(
    cfg["BASIC_RATE_LIMIT"] + pension,
    cfg["ADDITIONAL_RATE_THRESHOLD"],
)
```
Consistent with HMRC Pensions Tax Manual PTM044100 and `reference_calculator.py`.

**Regression tests:** `tests/test_el003_regression.py` (24 tests)

---

## Defect history — resolved

### EL-001 — Moving Personal Allowance / Incremental Income Tax defect
**Severity at time of discovery:** Medium
**Status:** ✅ Resolved in engine v2.0.0
**Discovery:** Reserved West Initiative 001, Stage 1 (engine v1.0.0)
**Resolution date:** 2026-08-06

**Description**
The incremental Income Tax calculation applied the Personal Allowance
determined at the ending tax position across the entire income interval.
This was invalid where the taxpayer's Personal Allowance changed between
the starting and ending tax positions.

The defect affected events that:
- entered the Personal Allowance taper (ANI crossing £100,000 from below);
- remained wholly within the taper (£100,000 < ANI_start < ANI_end ≤ £125,140);
- crossed the point where the Personal Allowance became zero (ANI crossing £125,140).

**Resolution:** Engine v2.0.0 computes:
  complete Income Tax at the ending tax position
  minus
  complete Income Tax at the starting tax position

Each complete tax position independently determines adjusted net income,
Personal Allowance, taxable income and tax-band allocation.

**Variances observed in Stage 1 (engine v1.0.0 vs reference):**
  - RW-S1-012 (invoice enters taper zone): −£400
  - RW-S1-013 (invoice fully within taper zone): −£500
  - RW-S1-014 (invoice crosses PA elimination): −£314

---

### EL-002 — CGT BASIC_RATE_LIMIT sourced from module-level constant
**Severity at time of discovery:** Low
**Status:** ✅ Resolved in engine v1.0.0
**Discovery:** Reserved West Initiative 001, pre-Stage 1 code review
**Resolution date:** 2026-08-06

**Description**
The Capital Gains Tax module (`capital_gains.py`) sourced `BASIC_RATE_LIMIT` from a
module-level constant instead of reading it from the versioned `tax_config` dictionary.
This meant that any future change to the rate configuration would not propagate to the
CGT basic/higher rate band split calculation.

**Resolution:** `capital_gains.py` updated to read `BASIC_RATE_LIMIT` from the
versioned `tax_config` at call time, not from a module-level import.

**Regression test:** `tests/test_capital_gains.py::test_cgt_uses_versioned_brl`

---

## EL-001 permanent regression family

EL-001 is the first example of the broader risk class:
  > An incremental calculation must not assume that allowances, reliefs,
  > thresholds or tax treatment remain constant between the starting and
  > ending tax positions.

Future variants could arise if:
- the Personal Allowance taper threshold or withdrawal rate changes;
- another allowance or relief is withdrawn as income increases;
- new tax bands or regional rules interact with a moving allowance;
- pension contributions, Gift Aid or another adjustment changes adjusted net income;
- tax-year configuration is applied inconsistently;
- rounding differs across sequential events;
- a future refactor reintroduces interval-based assumptions;
- the before-state is incomplete, stale or calculated using different rules.

**Runner classification:** `REGRESSION_EL001` is a gate-blocking FAIL.
It must never be classified as KNOWN_LIMITATION.
Permanent regression tests are in `tests/test_el001_regression.py`.
