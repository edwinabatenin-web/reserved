# Reserved Engine — Changelog

All notable changes to the tax engine are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

The engine version is exposed at runtime as `reserved.engines.ENGINE_VERSION`.

---

## [4.0.0] — 2026-08-14

### Relief-at-Source pension contributions extend BOTH limits

**Breaking correction:** a gross Relief-at-Source pension contribution now
extends **both** the basic-rate limit and the higher-rate limit (the point at
which the additional 45 % rate begins) by the gross contribution amount.

    extended basic-rate limit  = £37,700 + pension
    extended higher-rate limit = £125,140 + pension

The higher-rate band width (£87,440) is unchanged; the additional-rate
threshold shifts up by the contribution amount.  There is **no cap** at
£125,140.

This **supersedes** the v2.0.1 "eBRL cap at ART" treatment (recorded below),
which left the higher-rate limit fixed at £125,140 and overcharged the
additional-rate slice.  The v2.0.1 entry is retained unchanged as a
historical record; it was based on PTM044100, which does not address the
higher-rate limit, whereas PTM056120 ("Basic and higher rate limits") states
explicitly: *"Both the basic rate limit and the higher rate limit will be
increased by the gross amount of any contribution paid using RAS."*

**Authority:** HMRC Pensions Tax Manual PTM056120; Finance Act 2004 s.192.

**Representative corrections:**

| Income | Pension | v3.0.0 (wrong) | v4.0.0 (correct) |
|---|---|---|---|
| £125,141 | £1 | £42,516.25 | £42,516.20 (RW3-PEN-005) |
| £200,000 | £80,000 | £59,046.50 | £55,432.00 |

**Impact:** results change only when a gross pension contribution is present
and taxable income reaches the additional-rate threshold.  Zero-pension and
below-ART results are unchanged.

**Regression tests:** `tests/test_el003_regression.py` (decisive boundaries),
`tests/test_engine_adapters.py::test_rw3_pen_005_is_executable_and_passing`,
and the Optimise/artefact band-extension tests.

**Rules versions:** `uk-2026-27-v4`, `uk-2025-26-v2`.

**Status:** derived from authoritative material and implemented with explicit
workings; awaiting subsequent independent re-review.

### Assurance terminology and metadata (2026-08-14)

No engine behaviour change; engine version remains `4.0.0`.  This records the
assurance-facing terminology decisions so the UI and metadata cannot be read
as an absolute claim of correctness.

* The assurance metadata field `verified_date` is renamed to `generated_on`,
  and the top-level `status` is either `release_gate_passed` or
  `release_gate_failed`.  "Verified" is deliberately avoided.
* The annual period is labelled **period of assessment** (value `2026/27`)
  rather than the ambiguous "tax year".  The engine's `tax_year` code
  identifier is unchanged.
* The golden-persona wording "Extended basic-rate limit = £50,270 + £5,000"
  is corrected to **Extended higher-rate threshold = £50,270 + £5,000**
  (£50,270 is the higher-rate threshold, not the £37,700 basic-rate limit).
* The assurance metadata now records the mandatory RW3 fixture-gate result,
  its classification counts, and the artefact source identity.

---

## [3.0.0] — 2026-08-13

### PA taper taxable-band coordinate defect resolved

**Breaking correction:** full-position calculations now deduct the applicable
Personal Allowance and apply the fixed £37,700 basic-rate band to taxable
income. Earlier versions incorrectly used £50,270 as a gross-income ceiling
after the allowance had tapered, widening the 20% band and understating tax.

This is distinct from EL-001: v2.0.0 correctly introduced before/after full
positions, but each position and the Reserved West reference shared this band
defect. See `docs/PA_TAPER_ROOT_CAUSE.md` and
`tests/test_pa_taper_band_regression.py`.

Representative correction: total Income Tax at £110,000 with no pension is
£33,432, not £32,432. A £10,000 gross Relief-at-Source pension reduces that
liability by £4,000, not £3,000.

---

## [2.0.1] — 2026-08-06

### EL-003 resolved — eBRL cap at Additional Rate Threshold

**Bug fix:** When a pension contribution exceeded £74,870 (= ART − BRL =
£125,140 − £50,270), the uncapped extended basic-rate limit exceeded the
Additional Rate Threshold.  This caused `_income_tax_between` to absorb the
ART and additional-rate (45 %) band into the 20 % slice, silently suppressing
the 45 % rate on any income above £125,140.

**Trigger condition:** `pension > £74,870`.  Below this threshold results
were numerically unchanged.

**Root cause:**

```python
# v2.0.0 (incorrect when pension > ART − BRL)
extended_basic_rate_limit = cfg["BASIC_RATE_LIMIT"] + pension
```

**Fix:**

```python
# v2.0.1 (correct — matches reference_calculator.py and HMRC PTM044100)
extended_basic_rate_limit = min(
    cfg["BASIC_RATE_LIMIT"] + pension,
    cfg["ADDITIONAL_RATE_THRESHOLD"],
)
```

**Impact:**

| Pension | v2.0.0 | v2.0.1 | Change |
|---|---|---|---|
| ≤ £74,870 | ✓ | ✓ | **No change** |
| > £74,870 (income crosses ART) | Missing 45 % tax | Correct | +amount |

**Discovery:** Reserved West Initiative 001, Stage 3 (scenario RW-S3-011).

**Regression tests:** `tests/test_el003_regression.py`

**HMRC reference:** HMRC Pensions Tax Manual PTM044100 — pension band
extension operates within the basic-rate band and does not extend beyond ART.

---

## [2.0.0] — 2026-08-06

### EL-001 resolved — correct Personal Allowance taper handling

**Breaking change:** The income-tax component now produces different numeric
results for scenarios where a single invoice causes income to move through
the Personal Allowance taper zone (ANI £100,000 – £125,140).  Callers who
pin EL-001-affected results must update their expected values.

#### Root cause

`estimate_incremental_liability` v1.x computed ANI from `end_income` only
and applied the resulting Personal Allowance as a fixed band ceiling across
the full `[start_income, end_income)` range.  This underestimated the
marginal liability whenever the PA differed between start and end income:

```
# v1.x (incorrect for taper-zone invoices)
ani       = max(0, end_income − pension)          # end-state only
allowance = _personal_allowance(ani)              # fixed for full range
income_tax = _income_tax_between(start, end, allowance, eBRL)
```

#### Fix

A new internal function `_total_income_tax(income, pension, cfg)` computes
the complete income-tax liability from £0 to `income`, independently
deriving ANI, PA, and the extended BRL for that specific income level.  The
incremental liability is then the true before/after differential:

```
# v2.0.0 (correct)
income_tax = money(
    _total_income_tax(end_income,   pension, cfg)
    − _total_income_tax(start_income, pension, cfg)
)
```

`_total_income_tax` reuses `_income_tax_between` — no band or PA logic is
duplicated.  NI and student-loan calculations are unchanged.

#### Impact

| Scenario | v1.0.0 | v2.0.0 | Change |
|---|---|---|---|
| Income firmly below taper zone (ANI < £100,000) | ✓ | ✓ | **No change** |
| Income firmly above taper zone (ANI ≥ £125,140) | ✓ | ✓ | **No change** |
| Invoice enters taper zone (e.g. 99k→104k ANI) | Underestimate | Correct | +£400 |
| Invoice fully within taper zone (e.g. 105k→110k ANI) | Underestimate | Correct | +£500 |
| Invoice crosses PA elimination (e.g. 122k→132k ANI) | Underestimate | Correct | +£314–£500 |

#### Taper-zone error formula (v1.x)

```
error = (PA_start − PA_end) × marginal_rate_on_newly_exposed_income
```

where `PA_start` and `PA_end` are the allowances at start and end income
respectively.  The error was zero outside the taper zone.

#### Regression tests

Permanent regression tests for EL-001 are in
`tests/test_el001_regression.py` covering all three taper-zone cases plus
boundary conditions, sequential payments, and the invariant
`incremental = total_tax(end) − total_tax(start)`.

#### EL-001 status

**Resolved.**  See `docs/ASSUMPTIONS_AND_LIMITATIONS_REGISTER.md`.

---

## [1.0.0] — 2026-08-06

### Baseline — Initiative 001 (Reserved West preparation)

First formally versioned release. The engine was extracted from the Reserved
web application as a self-contained, Flask-independent computation package.
No calculation logic was changed; this release establishes the stable public
API surface and version record.

#### Public API established

| Symbol | Module | Description |
|---|---|---|
| `estimate_incremental_liability` | `income_tax` | Marginal Income Tax, Class 4 NI, Student Loan for a single invoice |
| `CapitalDisposal` | `capital_gains` | Frozen dataclass representing a single chargeable disposal |
| `estimate_cgt` | `capital_gains` | CGT liability across a set of disposals |
| `build_allocation` | `allocation` | Gross-to-safe-to-spend bucket split |
| `get_income_tax_config` | `tax_config` | Versioned IT/NI/SL configuration lookup |
| `get_cgt_config` | `capital_gains_config` | Versioned CGT configuration lookup |
| `SUPPORTED_TAX_YEARS` | `tax_config` | Ordered list of supported IT/NI/SL years |
| `SUPPORTED_CGT_TAX_YEARS` | `capital_gains_config` | Ordered list of supported CGT years |
| `money` | `utils` | ROUND_HALF_UP penny quantizer |
| `PENNY` | `utils` | `Decimal("0.01")` constant |

#### Supported tax years

| Year | IT/NI/SL | CGT |
|---|---|---|
| 2025/26 | ✓ `uk-2025-26-v1` | ✓ `uk-cgt-2025-26-v1` |
| 2026/27 | ✓ `uk-2026-27-v1` | ✓ `uk-cgt-2026-27-preview-v1` |

#### CGT configuration corrected (EL-002)

`estimate_cgt()` previously read `BASIC_RATE_LIMIT` from the module-level
constant in `tax_config` rather than from the versioned year config. This
produced the correct value for the default year (2026/27) but would have
returned the wrong band boundary for a hypothetical future year where the
basic-rate limit differs. Fixed: `estimate_cgt()` now accepts an explicit
`tax_year` parameter (default `"2026/27"`) and resolves both CGT rates and
the basic-rate limit from the versioned registries.

**No numeric change** for either currently supported tax year — the
basic-rate limit (£50,270) is frozen and identical in both 2025/26 and
2026/27.

#### Known methodology limitations (carried forward from pre-1.0 engine)

| ID | Description | Status |
|---|---|---|
| EL-001 | PA taper computed from end-state ANI across full invoice range | **Resolved in 2.0.0** |
| EL-002 | CGT BASIC_RATE_LIMIT sourced from module-level constant | **Resolved in 1.0.0** |
