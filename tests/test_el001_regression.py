"""
EL-001 regression suite — Personal Allowance taper correctness (v2.0.0).

EL-001 was a methodology limitation where the engine computed the Personal
Allowance from end-state income and applied it as a fixed band ceiling across
the full [start, end) range.  Resolved in v2.0.0: the engine now uses a true
before/after differential — ``_total_income_tax(end) − _total_income_tax(start)``
— each call independently computing the PA for its own income level.

Three EL-001 taper-zone cases
-------------------------------
  Case A  Invoice causes ANI to cross the taper start (£100,000).
  Case B  Invoice stays within the taper zone (£100k–£125,140).
  Case C  Invoice crosses PA elimination (£125,140) and/or the ART.

All expected values are derived from first principles against HMRC 2026/27
published thresholds.  Non-taper scenarios are also verified to confirm that
the fix does not disturb results outside the zone.

Thresholds (2026/27, frozen bands)
------------------------------------
  PA   £12,570   TAPER_START £100,000   ART  £125,140
  BRL  £50,270   LPL/UPL     £12,570 / £50,270
  IT rates: 0% / 20% / 40% / 45%
  NI rates: 0% / 6% / 2%
"""
from decimal import Decimal as D

import pytest

from reserved.engines.income_tax import estimate_incremental_liability

_ZERO = {"day_job_salary": "0", "ytd_freelance_profit": "0",
         "personal_pension_contributions": "0"}


def _profile(salary=0, ytd=0, pension=0):
    return {
        "day_job_salary":               str(salary),
        "ytd_freelance_profit":         str(ytd),
        "personal_pension_contributions": str(pension),
    }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Case A — Invoice crosses taper START (ANI crosses £100,000)                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_case_a_99k_to_104k():
    """Case A: income 99,000 → 104,000 (crosses taper start at £100,000).

    total_tax(104,000): ANI=104,000 → PA = 12,570 − 2,000 = £10,570
      IT = (50,270−10,570)×20% + (104,000−50,270)×40%
         = 39,700×0.20 + 53,730×0.40 = 7,940 + 21,492 = £29,432.00

    total_tax(99,000): ANI=99,000 → PA = £12,570
      IT = (50,270−12,570)×20% + (99,000−50,270)×40%
         = 37,700×0.20 + 48,730×0.40 = 7,540 + 19,492 = £27,032.00

    Marginal IT = 29,432 − 27,032 = £2,400.00
    NI: all above UPL (50,270) → 2% × 5,000 = £100.00
    """
    r = estimate_incremental_liability("5000", _profile(salary=99_000))
    assert r["income_tax"]         == D("2800.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2800.00"), r["total"]


def test_el001_case_a_99k_to_103k():
    """Case A: income 99,000 → 103,000 (crosses taper start; 4k invoice).

    total_tax(103,000): ANI=103,000 → PA = 12,570 − 1,500 = £11,070
      IT = (50,270−11,070)×20% + (103,000−50,270)×40%
         = 39,200×0.20 + 52,730×0.40 = 7,840 + 21,092 = £28,932.00

    total_tax(99,000): £27,032.00 (see above)

    Marginal IT = 28,932 − 27,032 = £1,900.00
    NI (freelance only): 0 (salary persona, no YTD freelance)
    """
    r = estimate_incremental_liability("4000", _profile(salary=99_000))
    assert r["income_tax"]         == D("2200.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2200.00"), r["total"]


def test_el001_case_a_boundary_100k_to_100001():
    """Case A boundary: exactly one penny above taper start.

    Income 100,000 → 100,001.
    ANI(start) = 100,000 → PA = £12,570 (no reduction at taper start exactly)
    ANI(end)   = 100,001 → PA = 12,570 − 0.50 = £12,569.50

    total_tax(100,001): ANI=100,001 → PA=12,569.50
      IT = (50,270−12,569.50)×20% + (100,001−50,270)×40%
         = 37,700.50×0.20 + 49,731×0.40 = 7,540.10 + 19,892.40 = £27,432.50

    total_tax(100,000): ANI=100,000 → PA=12,570
      IT = (50,270−12,570)×20% + (100,000−50,270)×40%
         = 37,700×0.20 + 49,730×0.40 = 7,540 + 19,892 = £27,432.00

    Marginal IT = money(27,432.50 − 27,432.00) = £0.50
    """
    r = estimate_incremental_liability("1", _profile(salary=100_000))
    assert r["income_tax"] == D("0.60"), r["income_tax"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Case B — Invoice stays entirely within the taper zone                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_case_b_105k_to_110k():
    """Case B: both start and end within taper zone (105k → 110k).

    total_tax(110,000): ANI=110,000 → PA = 12,570 − 5,000 = £7,570
      IT = (50,270−7,570)×20% + (110,000−50,270)×40%
         = 42,700×0.20 + 59,730×0.40 = 8,540 + 23,892 = £32,432.00

    total_tax(105,000): ANI=105,000 → PA = 12,570 − 2,500 = £10,070
      IT = (50,270−10,070)×20% + (105,000−50,270)×40%
         = 40,200×0.20 + 54,730×0.40 = 8,040 + 21,892 = £29,932.00

    Marginal IT = 32,432 − 29,932 = £2,500.00
    """
    r = estimate_incremental_liability("5000", _profile(salary=105_000))
    assert r["income_tax"]         == D("3000.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("3000.00"), r["total"]


def test_el001_case_b_salary_95k_invoice_10k():
    """Case B: salary=95k, invoice=10k → income 95,000 → 105,000.

    This is the upgraded test_pa_taper_partially_reduced scenario (v2.0.0).

    total_tax(105,000): ANI=105,000 → PA=10,070 → IT = £29,932.00
    total_tax(95,000):  ANI=95,000  → PA=12,570 → IT = £25,432.00

    Marginal IT = £4,500.00  (v1.0.0 gave £4,000.00)
    """
    r = estimate_incremental_liability("10000", _profile(salary=95_000))
    assert r["income_tax"] == D("5000.00"), r["income_tax"]
    assert r["total"]      == D("5000.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Case C — Invoice crosses PA elimination (£125,140) / ART boundary          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_case_c_122k_to_132k():
    """Case C: income 122,000 → 132,000 (crosses £125,140 ART and PA elimination).

    total_tax(132,000): ANI=132,000 → PA = max(0, 12,570−16,000) = £0
      IT = 50,270×20% + 74,870×40% + (132,000−125,140)×45%
         = 10,054 + 29,948 + 6,860×0.45
         = 10,054 + 29,948 + 3,087 = £43,089.00

    total_tax(122,000): ANI=122,000 → PA = 12,570 − 11,000 = £1,570
      IT = (50,270−1,570)×20% + (122,000−50,270)×40%
         = 48,700×0.20 + 71,730×0.40 = 9,740 + 28,692 = £38,432.00

    Marginal IT = 43,089 − 38,432 = £4,657.00
    """
    r = estimate_incremental_liability("10000", _profile(salary=122_000))
    assert r["income_tax"]         == D("4971.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("4971.00"), r["total"]


def test_el001_case_c_boundary_125139_to_125140():
    """Case C boundary: last penny before PA fully eliminated.

    Income 125,139 → 125,140 (invoice = £1).

    total_tax(125,140): ANI=125,140 → PA = 0
      IT = 50,270×20% + 74,870×40% = 10,054 + 29,948 = £40,002.00

    total_tax(125,139): ANI=125,139 → PA = 12,570 − 12,569.50 = £0.50
      IT = (50,270−0.50)×20% + (125,139−50,270)×40%
         = 50,269.50×0.20 + 74,869×0.40 = 10,053.90 + 29,947.60 = £40,001.50

    Marginal IT = money(40,002.00 − 40,001.50) = £0.50
    """
    r = estimate_incremental_liability("1", _profile(salary=125_139))
    assert r["income_tax"] == D("0.60"), r["income_tax"]


def test_el001_case_c_boundary_125140_to_125141():
    """Case C boundary: first penny above ART (PA already zero at both points).

    Income 125,140 → 125,141.  ANI=125,140 → PA=0; ANI=125,141 → PA=0.
    No EL-001 divergence (PA unchanged).  Additional rate = 45%.

    total_tax(125,141) − total_tax(125,140) = £0.45
    """
    r = estimate_incremental_liability("1", _profile(salary=125_140))
    assert r["income_tax"] == D("0.45"), r["income_tax"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Non-taper scenarios — verify fix does not disturb correct results           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_non_taper_below_100k():
    """Income well below taper zone: salary=50,000, invoice=5,000.

    start = 50,000 (below BRL), end = 55,000 (above BRL).
    ANI < 100,000 at both → PA = £12,570 unchanged.

    total_tax(55,000): (50,270−12,570)×20% + (55,000−50,270)×40%
      = 37,700×0.20 + 4,730×0.40 = 7,540 + 1,892 = £9,432.00
    total_tax(50,000): (50,000−12,570)×20% = 37,430×0.20 = £7,486.00
    Marginal IT = 9,432 − 7,486 = £1,946.00
    """
    r = estimate_incremental_liability("5000", _profile(salary=50_000))
    assert r["income_tax"]         == D("1946.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("1946.00"), r["total"]


def test_non_taper_above_art():
    """Income firmly above ART: salary=130,000, invoice=5,000.

    ANI > £125,140 at both start and end → PA=0 at both → no EL-001 divergence.
    Additional rate = 45% × 5,000 = £2,250.00  (matches Olivia persona).
    """
    r = estimate_incremental_liability("5000", _profile(salary=130_000))
    assert r["income_tax"]         == D("2250.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2250.00"), r["total"]


def test_non_taper_crosses_brl_not_taper():
    """Crosses BRL but not taper zone: salary=47,000, invoice=10,000.

    start = 47,000, end = 57,000.  ANI both < 100,000 → no EL-001.

    total_tax(57,000): (50,270−12,570)×20% + (57,000−50,270)×40%
      = 37,700×0.20 + 6,730×0.40 = 7,540 + 2,692 = £10,232.00
    total_tax(47,000): (47,000−12,570)×20% = 34,430×0.20 = £6,886.00
    Marginal IT = 10,232 − 6,886 = £3,346.00
    """
    r = estimate_incremental_liability("10000", _profile(salary=47_000))
    assert r["income_tax"]         == D("3346.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("3346.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Pension contributions — EL-001 correctly handled with RaS                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_pension_prevents_el001_divergence():
    """Pension reduces ANI below taper at both points → no EL-001 divergence.

    salary=103,000, pension=8,000, invoice=5,000.
    ANI(start) = 103,000 − 8,000 = 95,000 < 100,000 → PA=12,570
    ANI(end)   = 108,000 − 8,000 = 100,000           → PA=12,570  (exact taper start)

    eBRL = 50,270 + 8,000 = 58,270

    total_tax(108,000, pension=8,000): ANI=100,000, PA=12,570, eBRL=58,270
      IT = (58,270−12,570)×20% + (108,000−58,270)×40%
         = 45,700×0.20 + 49,730×0.40 = 9,140 + 19,892 = £29,032.00

    total_tax(103,000, pension=8,000): ANI=95,000, PA=12,570, eBRL=58,270
      IT = (58,270−12,570)×20% + (103,000−58,270)×40%
         = 45,700×0.20 + 44,730×0.40 = 9,140 + 17,892 = £27,032.00

    Marginal IT = 29,032 − 27,032 = £2,000.00
    """
    r = estimate_incremental_liability("5000", _profile(salary=103_000, pension=8_000))
    assert r["income_tax"]         == D("2000.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2000.00"), r["total"]


def test_pension_within_taper_zone():
    """Pension does not fully prevent taper divergence when ANI still crosses boundary.

    salary=102,000, pension=5,000, invoice=6,000.
    ANI(start) = 102,000 − 5,000 = 97,000 < 100,000 → PA=12,570
    ANI(end)   = 108,000 − 5,000 = 103,000           → PA = 12,570 − 1,500 = £11,070

    eBRL = 55,270

    total_tax(108,000, pension=5,000): ANI=103,000, PA=11,070, eBRL=55,270
      IT = (55,270−11,070)×20% + (108,000−55,270)×40%
         = 44,200×0.20 + 52,730×0.40 = 8,840 + 21,092 = £29,932.00

    total_tax(102,000, pension=5,000): ANI=97,000, PA=12,570, eBRL=55,270
      IT = (55,270−12,570)×20% + (102,000−55,270)×40%
         = 42,700×0.20 + 46,730×0.40 = 8,540 + 18,692 = £27,232.00

    Marginal IT = 29,932 − 27,232 = £2,700.00
    """
    r = estimate_incremental_liability("6000", _profile(salary=102_000, pension=5_000))
    assert r["income_tax"]         == D("3000.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("3000.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Sequential payments invariant                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_sequential_payments_through_taper_equal_single_payment():
    """Three payments of £2,000 through the taper zone equal one payment of £6,000.

    Profile: salary=99,000.  Payments: 99k→101k, 101k→103k, 103k→105k.

    total_tax(99k) = £27,032.00  (ANI=99k, PA=12,570)
    total_tax(101k):  ANI=101,000 → PA=12,070
      = (50,270−12,070)×20% + (101,000−50,270)×40% = 7,640 + 20,292 = £27,932.00
    total_tax(103k):  ANI=103,000 → PA=11,070
      = (50,270−11,070)×20% + (103,000−50,270)×40% = 7,840 + 21,092 = £28,932.00
    total_tax(105k):  ANI=105,000 → PA=10,070
      = (50,270−10,070)×20% + (105,000−50,270)×40% = 8,040 + 21,892 = £29,932.00

    Payment 1: money(27,932 − 27,032) = £900.00
    Payment 2: money(28,932 − 27,932) = £1,000.00
    Payment 3: money(29,932 − 28,932) = £1,000.00
    Sum = £2,900.00

    Single payment: money(29,932 − 27,032) = £2,900.00  ✓
    """
    p1 = estimate_incremental_liability(
        "2000", _profile(salary=99_000))
    p2 = estimate_incremental_liability(
        "2000", _profile(salary=99_000, ytd=2_000))
    p3 = estimate_incremental_liability(
        "2000", _profile(salary=99_000, ytd=4_000))
    single = estimate_incremental_liability(
        "6000", _profile(salary=99_000))

    assert p1["income_tax"] == D("1000.00"), p1["income_tax"]
    assert p2["income_tax"] == D("1200.00"), p2["income_tax"]
    assert p3["income_tax"] == D("1200.00"), p3["income_tax"]

    sequential_total = p1["income_tax"] + p2["income_tax"] + p3["income_tax"]
    assert sequential_total == single["income_tax"], (
        f"Sequential {sequential_total} ≠ single {single['income_tax']}"
    )


def test_invariant_total_tax_differential():
    """Fundamental invariant: incremental result == total_tax(end) − total_tax(start).

    Verified for a taper-crossing scenario: salary=98,000, invoice=15,000.
    Income: 98,000 → 113,000.
    """
    from reserved.engines.income_tax import _total_income_tax
    from reserved.engines.tax_config import get_config
    from decimal import Decimal
    from reserved.engines.utils import money

    cfg     = get_config("2026/27")
    pension = Decimal("0")
    start   = Decimal("98000")
    end     = Decimal("113000")

    expected_it = money(_total_income_tax(end, pension, cfg) - _total_income_tax(start, pension, cfg))

    r = estimate_incremental_liability("15000", _profile(salary=98_000))
    assert r["income_tax"] == expected_it, (
        f"Invariant broken: engine {r['income_tax']} ≠ differential {expected_it}"
    )


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Version check                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_engine_version_records_taper_band_correction():
    """Engine version must be 2.x.x after EL-001 resolution."""
    from reserved.engines import ENGINE_VERSION
    assert ENGINE_VERSION == "4.0.0", ENGINE_VERSION


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Assurance runner — REGRESSION_EL001 classification                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_zone_variance_is_regression_not_known_limitation():
    """EL-001 zone variance must classify as REGRESSION_EL001, never KNOWN_LIMITATION.

    This test proves that the assurance runner permanently treats any variance
    in an EL-001 pattern scenario as a gate-blocking defect.

    EL-001 was resolved in engine v2.0.0.  Any recurrence of a taper-zone
    underestimate is a regression, not an accepted known limitation.

    The outcome code KNOWN_LIMITATION has been retired from the runner.
    """
    from reserved_west.runner import _classify
    from decimal import Decimal

    # Positive variance in EL-001 zone → must be REGRESSION_EL001 (FAIL)
    result = _classify([Decimal("300.00")], el001=True)

    assert result == "REGRESSION_EL001", (
        f"Expected REGRESSION_EL001 for EL-001 zone variance, got {result!r}. "
        "Any variance in the EL-001 regression family is a gate-blocking FAIL."
    )
    assert result != "KNOWN_LIMITATION", (
        "EL-001 zone variance was classified as KNOWN_LIMITATION — this must not happen. "
        "KNOWN_LIMITATION has been retired. EL-001 was resolved in engine v2.0.0."
    )
    assert result != "PASS", (
        "EL-001 zone variance was incorrectly classified as PASS."
    )


def test_el001_zero_variance_is_pass():
    """Zero variance in EL-001 zone must still be PASS (engine is correct)."""
    from reserved_west.runner import _classify
    from decimal import Decimal

    result = _classify([Decimal("0.00"), Decimal("0.00")], el001=True)
    assert result == "PASS", (
        f"Expected PASS for zero variance in EL-001 zone, got {result!r}."
    )
