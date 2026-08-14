"""
Common arithmetic for the Initiative 002 independent reference.

No imports from the product engine (reserved.*) are permitted here.
All calculations use plain Python floats / Decimal independently.

HMRC sources used to derive constants
--------------------------------------
Income tax bands (frozen Finance Act 2022 through 2027/28):
  Personal Allowance:   £12,570
  Basic-rate limit:     £50,270
  Additional-rate:      £125,140
  Rates: 20 % / 40 % / 45 %

Class 4 NI (frozen same period):
  LPL: £12,570  UPL: £50,270  Rates: 6 % / 2 %

PA taper (Finance (No.2) Act 2015):
  Start: £100,000  End: £125,140  Rate: £1 per £2

HICBC (Finance Act 2012 s.681B, revised April 2024):
  Threshold: £60,000  Taper: 1 % per £200  Full charge: £80,000
"""
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

# ── Constants ─────────────────────────────────────────────────────────────────
PA              = Decimal("12570")
TAPER_START     = Decimal("100000")
TAPER_END       = Decimal("125140")
BRL             = Decimal("50270")
ART             = Decimal("125140")

HICBC_LOWER     = Decimal("60000")
HICBC_UPPER     = Decimal("80000")

PENNY = Decimal("0.01")


def p(amount) -> Decimal:
    """Round to nearest penny (ROUND_HALF_UP), accepting any numeric input."""
    return Decimal(str(amount)).quantize(PENNY, rounding=ROUND_HALF_UP)


def personal_allowance_ref(ani: Decimal) -> Decimal:
    """Personal Allowance after taper.

    Source: ITEPA 2003 s.35; Finance (No.2) Act 2015.
    """
    if ani <= TAPER_START:
        return PA
    reduction = (ani - TAPER_START) / Decimal("2")
    return max(Decimal("0"), p(PA - reduction))


def income_tax_total_ref(income: Decimal, pension: Decimal) -> Decimal:
    """Full-year income-tax liability from £0.

    ANI = income − pension (clamped to 0).
    PA reduced by £1 per £2 ANI above £100,000.
    BRL extended by pension, capped at ART.

    Rates: 0 % / 20 % / 40 % / 45 %.
    Source: ITEPA 2003 Part 2; Income Tax Act 2007 s.35.
    """
    if income <= Decimal("0"):
        return Decimal("0")

    ani = max(Decimal("0"), income - pension)
    pa  = personal_allowance_ref(ani)
    basic_band = min((BRL - PA) + pension, ART)
    taxable_income = max(Decimal("0"), income - pa)

    bands = [
        (basic_band,      Decimal("0.20")),
        (ART,             Decimal("0.40")),
        (Decimal("Inf"), Decimal("0.45")),
    ]

    tax    = Decimal("0")
    cursor = Decimal("0")
    end    = taxable_income

    for ceiling, rate in bands:
        if cursor >= end:
            break
        if cursor < ceiling:
            slice_end = min(end, ceiling)
            tax += max(Decimal("0"), slice_end - cursor) * rate
            cursor = slice_end

    return p(tax)


def hicbc_ref(ani: Decimal, annual_cb: Decimal) -> Decimal:
    """High Income Child Benefit Charge with statutory staged flooring.

    Source: Finance Act 2012 s.681B (revised April 2024); ITEPA 2003 s.681C(3).

    Staged whole-pound flooring (matching HMRC CH2300C and the independently
    reviewed RW3-HICBC fixtures):
      1. appropriate percentage = floor((ANI − 60,000) / 200), capped at 100;
      2. relevant total benefit  = floor(annual_cb);
      3. charge = floor(relevant_benefit × percentage / 100).
    """
    if ani <= HICBC_LOWER or annual_cb <= Decimal("0"):
        return Decimal("0")
    charge_pct = min(Decimal("100"), (ani - HICBC_LOWER) // Decimal("200"))
    relevant_benefit = annual_cb.to_integral_value(rounding=ROUND_FLOOR)
    charge = (relevant_benefit * charge_pct / Decimal("100")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return charge
