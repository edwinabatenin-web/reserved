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

from reserved_engine.income_tax import estimate_incremental_liability

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
    """
    r = estimate_incremental_liability("5000", _profile(salary=99_000))
    assert r["income_tax"]         == D("2400.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2400.00"), r["total"]


def test_el001_case_a_99k_to_103k():
    """Case A: income 99,000 → 103,000 (crosses taper start; 4k invoice).

    Marginal IT = 28,932 − 27,032 = £1,900.00  (v1.0.0 gave £1,600.00)
    """
    r = estimate_incremental_liability("4000", _profile(salary=99_000))
    assert r["income_tax"]         == D("1900.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("1900.00"), r["total"]


def test_el001_case_a_boundary_100k_to_100001():
    """Case A boundary: exactly one penny above taper start.

    Marginal IT = money(27,432.50 − 27,432.00) = £0.50
    """
    r = estimate_incremental_liability("1", _profile(salary=100_000))
    assert r["income_tax"] == D("0.50"), r["income_tax"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Case B — Invoice stays entirely within the taper zone                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_case_b_105k_to_110k():
    """Case B: both start and end within taper zone (105k → 110k).

    Marginal IT = 32,432 − 29,932 = £2,500.00
    """
    r = estimate_incremental_liability("5000", _profile(salary=105_000))
    assert r["income_tax"]         == D("2500.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("2500.00"), r["total"]


def test_el001_case_b_salary_95k_invoice_10k():
    """Case B: salary=95k, invoice=10k → income 95,000 → 105,000.

    Marginal IT = £4,500.00  (v1.0.0 gave £4,000.00)
    """
    r = estimate_incremental_liability("10000", _profile(salary=95_000))
    assert r["income_tax"] == D("4500.00"), r["income_tax"]
    assert r["total"]      == D("4500.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Case C — Invoice crosses PA elimination (£125,140) / ART boundary          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_el001_case_c_122k_to_132k():
    """Case C: income 122,000 → 132,000 (crosses £125,140 ART and PA elimination).

    Marginal IT = 43,089 − 38,432 = £4,657.00
    """
    r = estimate_incremental_liability("10000", _profile(salary=122_000))
    assert r["income_tax"]         == D("4657.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00"),    r["national_insurance"]
    assert r["total"]              == D("4657.00"), r["total"]


def test_el001_case_c_boundary_125139_to_125140():
    """Case C boundary: last penny before PA fully eliminated.

    Marginal IT = money(40,002.00 − 40,001.50) = £0.50
    """
    r = estimate_incremental_liability("1", _profile(salary=125_139))
    assert r["income_tax"] == D("0.50"), r["income_tax"]


def test_el001_case_c_boundary_125140_to_125141():
    """Case C boundary: first penny above ART (PA=0 at both → no divergence).

    45% × £1 = £0.45
    """
    r = estimate_incremental_liability("1", _profile(salary=125_140))
    assert r["income_tax"] == D("0.45"), r["income_tax"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Non-taper scenarios — verify fix does not disturb correct results           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_non_taper_below_100k():
    r = estimate_incremental_liability("5000", _profile(salary=50_000))
    assert r["income_tax"] == D("1946.00"), r["income_tax"]
    assert r["total"]      == D("1946.00"), r["total"]


def test_non_taper_above_art():
    r = estimate_incremental_liability("5000", _profile(salary=130_000))
    assert r["income_tax"] == D("2250.00"), r["income_tax"]
    assert r["total"]      == D("2250.00"), r["total"]


def test_non_taper_crosses_brl_not_taper():
    r = estimate_incremental_liability("10000", _profile(salary=47_000))
    assert r["income_tax"] == D("3346.00"), r["income_tax"]
    assert r["total"]      == D("3346.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Pension contributions                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_pension_prevents_el001_divergence():
    """Pension reduces ANI below taper at both points → no EL-001 divergence."""
    r = estimate_incremental_liability("5000", _profile(salary=103_000, pension=8_000))
    assert r["income_tax"] == D("2000.00"), r["income_tax"]
    assert r["total"]      == D("2000.00"), r["total"]


def test_pension_within_taper_zone():
    """Pension does not fully prevent taper divergence when ANI still crosses."""
    r = estimate_incremental_liability("6000", _profile(salary=102_000, pension=5_000))
    assert r["income_tax"] == D("2700.00"), r["income_tax"]
    assert r["total"]      == D("2700.00"), r["total"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Sequential payments invariant                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_sequential_payments_through_taper_equal_single_payment():
    """Three payments of £2,000 through taper zone sum to one payment of £6,000."""
    p1 = estimate_incremental_liability("2000", _profile(salary=99_000))
    p2 = estimate_incremental_liability("2000", _profile(salary=99_000, ytd=2_000))
    p3 = estimate_incremental_liability("2000", _profile(salary=99_000, ytd=4_000))
    single = estimate_incremental_liability("6000", _profile(salary=99_000))

    assert p1["income_tax"] == D("900.00"),  p1["income_tax"]
    assert p2["income_tax"] == D("1000.00"), p2["income_tax"]
    assert p3["income_tax"] == D("1000.00"), p3["income_tax"]

    seq = p1["income_tax"] + p2["income_tax"] + p3["income_tax"]
    assert seq == single["income_tax"], f"Sequential {seq} ≠ single {single['income_tax']}"


def test_invariant_total_tax_differential():
    """Fundamental invariant: incremental result == total_tax(end) − total_tax(start)."""
    from reserved_engine.income_tax import _total_income_tax
    from reserved_engine.tax_config import get_config
    from decimal import Decimal
    from reserved_engine.utils import money

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
    from reserved_engine import ENGINE_VERSION
    assert ENGINE_VERSION == "3.0.0", ENGINE_VERSION
