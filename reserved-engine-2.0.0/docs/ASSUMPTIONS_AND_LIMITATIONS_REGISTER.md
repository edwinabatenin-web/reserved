# Assumptions and Limitations Register — Reserved 2025/26 – 2026/27

> **Status:** Preview (private beta, October 2026)
> **Supported tax years:** 2025/26, 2026/27
> **Rules versions:** `uk-2025-26-v1`, `uk-2026-27-v1`
> **Last verified:** 2026-08-04

---

## Purpose

This document records the verification methodology, scope, known limitations,
and defect register for the Reserved tax estimation engine.  It is intended for:

- Internal engineering and product review
- Third-party technical due diligence
- HMRC compliance self-assessment at launch

Reserved does **not** file tax returns or provide regulated financial advice.
The engine produces **illustrative estimates** to help sole traders understand
the approximate tax cost of each invoice before they decide how much to spend.

---

## 1. Supported tax years and thresholds

### 1.1 Income Tax (frozen 2025/26 and 2026/27)

Income-tax bands are frozen under the Finance Act 2022 through 2027/28 and
are identical in both supported tax years.

| Band | Rate | Threshold |
|---|---|---|
| Personal Allowance | 0 % | Up to £12,570 |
| Basic rate | 20 % | £12,571 – £50,270 |
| Higher rate | 40 % | £50,271 – £125,140 |
| Additional rate | 45 % | Above £125,140 |

**Personal Allowance taper:** Reduced by £1 for every £2 of Adjusted Net
Income above £100,000; reaches zero at ANI ≥ £125,140.

### 1.2 Class 4 National Insurance (sole traders) — frozen 2025/26 and 2026/27

| Band | Rate |
|---|---|
| Below £12,570 (Lower Profits Limit) | 0 % |
| £12,570 – £50,270 (main band) | 6 % |
| Above £50,270 | 2 % |

### 1.3 Student and Postgraduate Loan repayment thresholds

Thresholds are uprated annually by the Student Loans Company (RPI/CPI for
Plans 1–4; fixed by statute for Plans 5 and PGL).

| Plan | Threshold 2025/26 | Threshold 2026/27 | Rate |
|---|---|---|---|
| Plan 1 | £24,990 | £26,900 | 9 % |
| Plan 2 | £28,470 | £29,385 | 9 % |
| Plan 4 (Scotland) | £32,745 | £33,795 | 9 % |
| Plan 5 | £25,000 | £25,000 | 9 % |
| Postgraduate Loan | £21,000 | £21,000 | 6 % |

**Year-on-year notes:** Plans 5 and PGL thresholds are fixed by statute until
April 2027.  Plans 1, 2, and 4 were uprated between 2025/26 and 2026/27.
Tests verify that income between the two thresholds triggers repayment only in
the earlier year (e.g. £26,000 earns no Plan 1 SL in 2026/27 but £90.90 in
2025/26).

### 1.4 Capital Gains Tax (2026/27)

| Band | Rate |
|---|---|
| Basic-rate taxpayers | 18 % |
| Higher/additional-rate taxpayers | 24 % |
| Annual Exempt Amount | £3,000 |

---

## 2. Calculation methodology

### 2.1 Incremental (before/after) approach

The income-tax engine uses a marginal *before/after differential*:

```
marginal_liability = tax(ytd_income + invoice) − tax(ytd_income)
```

where `ytd_income = employment_income + prior_freelance_profit`.

This correctly captures the marginal rate for the invoice without needing to
model PAYE coding notices or tax-code adjustments.

### 2.2 Pension Relief at Source (RaS)

Gross pension contributions affect the calculation in two ways:

1. **Adjusted Net Income** — pension reduces ANI for the Personal Allowance
   taper test (`ANI = total_income − gross_pension`).
2. **Basic-rate band extension** — the basic-rate ceiling is raised by the
   gross pension contribution (`extended_BRL = £50,270 + gross_pension`),
   meaning more income falls in the 20 % band rather than 40 %.

The engine expects the **gross** pension figure.  For Relief at Source schemes
the gross = net paid ÷ 0.80 (the provider reclaims the 20 % basic-rate relief).

### 2.3 Class 4 NI

Computed on sole-trader profit only (not on employment income).  Employs the
same before/after approach as income tax.

### 2.4 Student / Postgraduate Loans

Multiple plans run concurrently.  Each plan is computed independently and the
amounts are summed.  The `student_loan_plans` profile key accepts a list;
the legacy singular `student_loan_plan` key is also accepted for backward
compatibility.

### 2.5 Capital Gains Tax

Uses the statutory AEA offset, then applies the basic/higher split based on
remaining basic-rate band after income.  Current-year and brought-forward
losses are offset against gains before AEA.

---

## 3. Defect register

### EL-001 — PA-taper methodology limitation (known, documented, not a bug)

| Field | Value |
|---|---|
| **ID** | EL-001 |
| **Severity** | Low (affects < 3 % of UK taxpayers; preview product) |
| **Status** | Documented; deferred to v2 |
| **Pinned by test** | `test_pa_taper_methodology_limitation_el001` in `tests/test_income_tax_boundaries.py` |

**Description**

The engine computes the Personal Allowance from the *end-state* income
(`end_income = ytd + invoice`) and applies it as a fixed band ceiling across
the full [start, end) income range.

This is equivalent to:

```
engine_marginal = tax_at_end_PA(start → end)
```

rather than the strictly correct:

```
true_marginal = total_tax(end, PA_end) − total_tax(start, PA_start)
```

The two expressions diverge when the invoice itself pushes income *through*
the PA taper zone (ANI crosses £100,000 mid-invoice).  In that case the
engine underestimates the marginal liability by:

```
error ≈ (PA_start − PA_end) × applicable_rate
```

**Example (documented in test):**

- YTD = £99,000 · Invoice = £4,000 → income 99k → 103k
- ANI at end: 103,000 → PA = 11,070 (reduced from 12,570)
- Engine: 40 % × 4,000 = **£1,600**
- True marginal: 28,932 − 27,032 = **£1,900** (difference = £300)

**Impact:** Only users whose total income straddles the £100k–£125.14k taper
zone within a single invoice.  For users whose income is firmly above or below
the zone the result is correct.

**Mitigation in engine v2:** Replace with a true `total_tax(end) − total_tax(start)` differential, computing each call with its own PA.

---

## 4. Known scope exclusions

| Exclusion | Impact |
|---|---|
| Scottish income tax | Scottish taxpayers face different rates; engine uses England/Wales/NI rates |
| Dividend and savings income | Different priority order in the tax computation |
| PAYE coding interactions | Estimates may differ from actual Self Assessment liability |
| Salary sacrifice pension | Engine only handles personal (RaS) contributions |
| VAT-registered traders | VAT liability is not deducted from safe-to-spend |
| Share pooling / same-day matching | CGT results may be incorrect for frequent traders |
| Residential property CGT | Property-specific rates (18 %/28 %) not applied |
| BADR / Investors' Relief | Business asset disposals not discounted |
| Carried interest | Not modelled |
| PA-taper within a single invoice | See EL-001 above |

---

## 5. Test suite summary

The automated test suite covers the following scenarios.  All tests are in
`tests/` and are run with `pytest`.

### 5.1 Income Tax — personas (`tests/test_income_tax.py`)

| Test group | Scenarios covered |
|---|---|
| Gabriel persona | Employment + YTD profit + RaS pension + Plan 2; all four components |
| Hannah persona | First invoice, within PA, exactly at PA, 1p above PA |
| Emily persona | Crossing basic/higher boundary mid-invoice; no NI on employment income |
| Felipe persona | Pension RaS extending basic-rate band; quantified saving vs no pension |
| Olivia persona | PA fully tapered to zero (income > £125,140) |
| Priya persona | Pension ANI reduction restores full PA |
| PA taper boundary | ANI just above £100,000 |
| Student loan plans | All five plans independently (Plans 1, 2, 4, 5, PGL) |
| Student loan boundary | Below threshold, partially above threshold |
| Dual loans | Plan 1 + Postgraduate concurrently with breakdown |
| Legacy key | Backward-compatible `student_loan_plan` singular key |
| Class 4 NI | Below LPL, crossing LPL, crossing UPL |
| Input validation | Zero invoice, negative invoice, non-numeric, negative profile fields |
| Missing profile fields | Default to zero without raising |
| Decimal precision | All outputs are Decimal; all are 2 decimal places |

### 5.2 Income Tax — boundaries (`tests/test_income_tax_boundaries.py`)

| Test group | Scenarios covered |
|---|---|
| IT band boundaries | Within PA; exactly fills PA; 1p above PA (IT + NI); entirely in basic band; fills basic band; 1st penny in higher band; entirely in higher band; crosses BRL; crosses ART; 1st penny in additional band |
| NI band boundaries | Exactly at LPL (zero); 1st £100 above LPL; fills main band; 1st penny in upper band; all in upper band; crosses LPL and UPL together |
| PA taper boundaries | ANI exactly at taper start (full PA); 1p above taper start (fractional PA); ANI = ART (PA = 0); midpoint partial reduction |
| EL-001 regression | Pins engine behaviour for invoice crossing taper zone |
| SL exact boundaries | All five plans: income exactly at threshold (£0); income £1 above threshold |
| Rounding | ROUND_HALF_UP for IT (40%×4.6125 → £1.85); ROUND_HALF_UP for NI (6%×16.75 → £1.01); total == sum of components; fractional invoice |
| Composite regression | Plan 5 crossing BRL + NI crossing UPL; high earner at additional rate; pension saving at BRL boundary; zero-start first invoice |

### 5.3 Multi-year (`tests/test_multi_year.py`)

| Test group | Scenarios covered |
|---|---|
| Year selection | Default = 2026/27; explicit 2026/27; explicit 2025/26 metadata; invalid year raises ValueError |
| Config API | `get_config()` raises for unknown year; both years in `SUPPORTED_TAX_YEARS` |
| Frozen bands | IT and NI identical in both years (basic rate; higher rate) |
| SL threshold changes | Plan 1, 2, 4: higher repayment in 2025/26; Plans 5 and PGL: identical |
| Between-threshold band | Income £26k triggers Plan 1 SL in 2025/26 but not 2026/27 |
| End-to-end totals | Total difference = SL delta only; Gabriel same both years (start above both thresholds) |

### 5.4 Allocation (`tests/test_allocation.py`)

| Test group | Scenarios covered |
|---|---|
| Basic split | No fee; with fee |
| Zero liability | All gross to safe_to_spend |
| Reconciliation invariant | Normal inputs; fractional fee; gross == liability; liability > gross |
| Edge cases | Fee on zero liability; gross = liability + fee; small invoice (£0.03); liability > gross |
| Penny / large amounts | Smallest input; £100,000 |
| Types | All monetary values are Decimal; reconciles is bool; all keys present |

### 5.5 Capital Gains Tax (`tests/test_capital_gains.py`)

| Test group | Scenarios covered |
|---|---|
| Within AEA | Gain below £3,000 — zero tax; gain exactly equal to AEA |
| Basic rate | All gain taxed at 18 % |
| Split rate | Gain spanning both basic and higher rate bands |
| All higher rate | Income fills basic band entirely |
| Loss offset | Current-year losses reducing gain |
| Brought-forward losses | Prior-year losses; BF losses exceed current gain |
| Tax already paid | Reduces outstanding reserve; never goes negative |
| Net loss | No tax payable |
| Multiple disposals | Gains summed; three small gains equal AEA |
| Disposal costs | Acquisition + disposal costs correctly reduce gain |
| Zero gain | Proceeds = cost → zero gain |
| `Disposal.gain_or_loss` | Positive gain; negative loss |
| BASIC_RATE_LIMIT source | Verifies threshold from tax_config, not hardcoded |
| Result structure | All required keys present; warnings list present |
| Types | Monetary outputs are Decimal |

---

## 6. Golden persona — Gabriel (2026/27)

The Gabriel persona is the primary reference case used to validate the engine
end-to-end with a realistic taxpayer profile.

| Field | Value |
|---|---|
| Employment income (PAYE) | £40,000 |
| YTD freelance profit | £15,000 |
| Pension (gross, RaS) | £5,000 |
| Student loan | Plan 2 |
| Invoice | £10,000 |

**Expected outputs (2026/27):**

| Component | Manual calculation | Expected |
|---|---|---|
| Income tax | 20%×270 + 40%×9,730 = 54 + 3,892 | **£3,946.00** |
| Class 4 NI | 6%×10,000 | **£600.00** |
| Student loan | 9%×10,000 (Plan 2) | **£900.00** |
| **Total** | | **£5,446.00** |

_Workings:_
- start_income = £55,000; end_income = £65,000
- ANI = £65,000 − £5,000 = £60,000 → full PA (£12,570)
- Extended basic-rate limit = £50,270 + £5,000 = £55,270
- NI on freelance profit only: £15,000 → £25,000, all within main band

**Note:** Gabriel gives identical results in 2025/26 and 2026/27 because his
start income (£55,000) already exceeds both years' Plan 2 thresholds.

---

## 7. Rounding policy

All monetary computations use Python's `Decimal` type with `ROUND_HALF_UP` to
the nearest penny.  This policy is documented in `reserved/engines/utils.py`
and applied consistently across all three engines.  The allocation engine is
designed so that the three output buckets always sum to the gross amount when
sufficient gross is available.

---

## 8. Change log

| Date | Version | Change |
|---|---|---|
| 2026-08-03 | `uk-2026-27-v1` | Initial verified release: income tax, Class 4 NI, student loans (all plans), CGT, allocation |
| 2026-08-04 | `uk-2025-26-v1` | Added 2025/26 config; multi-year engine (tax_year parameter); boundary test suite; EL-001 documented |

---

## 9. Sign-off checklist

- [x] 2026/27 thresholds cross-referenced against HMRC publication
- [x] 2025/26 thresholds added: SLC Annual Threshold Notice 2025/26
- [x] Frozen bands verified identical across 2025/26 and 2026/27
- [x] Student loan thresholds verified to differ between years (Plans 1, 2, 4)
- [x] Plan 5 and PGL thresholds verified as fixed by statute (both years = same)
- [x] Pension Relief at Source band extension implemented and tested
- [x] Class 4 NI before/after differential implemented correctly
- [x] Dual student loan plans tested
- [x] All five student loan plans tested against independent golden values (both years)
- [x] Input validation: negative values and zero invoice rejected
- [x] Missing profile fields default to zero (no silent KeyError)
- [x] `BASIC_RATE_LIMIT` sourced from `tax_config` in CGT engine (no hardcoding)
- [x] Allocation reconciliation invariant asserted at runtime
- [x] All monetary outputs are `Decimal` quantized to 2 d.p.
- [x] ROUND_HALF_UP verified (not ROUND_HALF_EVEN) with sub-penny test cases
- [x] EL-001 (PA-taper methodology limitation) documented and pinned by regression test
- [x] Automated test suite passes with zero failures

**Open items (future versions):**
- [ ] EL-001: Replace end-state PA approximation with true `total_tax(end) − total_tax(start)` differential
- [ ] Scottish income tax bands
- [ ] Dividend and savings income priority ordering
- [ ] VAT-registered trader safe-to-spend reduction
- [ ] BADR / Investors' Relief CGT discount
- [ ] Residential property CGT rates (18 % / 28 %)
- [ ] Share pooling and same-day / 30-day matching
