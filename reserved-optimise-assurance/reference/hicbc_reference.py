"""
Initiative 002 — Independent HICBC reference implementation.

High Income Child Benefit Charge.  No code shared with reserved.engines.

Source: Finance Act 2012 ss.681A-681H; HMRC CH2300C.
Threshold revised April 2024 (Finance Act 2024): £60,000 → £80,000 taper.
Previous threshold (2012–2023/24): £50,000 → £60,000 — NOT implemented here.

2026/27 Child Benefit weekly rates (England / Wales / NI):
  Eldest child:      £26.60 / week = £1,383.20 / year
  Additional child:  £17.60 / week = £  915.20 / year
"""
from decimal import Decimal
from .common import p, hicbc_ref, HICBC_LOWER, HICBC_UPPER

# 2026/27 Child Benefit weekly rates
CB_WEEKLY_ELDEST     = Decimal("26.60")
CB_WEEKLY_ADDITIONAL = Decimal("17.60")
CB_WEEKS             = Decimal("52")

CB_ANNUAL_ELDEST     = p(CB_WEEKLY_ELDEST     * CB_WEEKS)   # £1,383.20
CB_ANNUAL_ADDITIONAL = p(CB_WEEKLY_ADDITIONAL * CB_WEEKS)   # £ 915.20


def annual_cb_for_children(n: int) -> Decimal:
    """Standard 2026/27 annual Child Benefit for n children (n ≥ 0)."""
    if n <= 0:
        return Decimal("0")
    eldest     = CB_ANNUAL_ELDEST
    additional = CB_ANNUAL_ADDITIONAL * Decimal(str(max(0, n - 1)))
    return p(eldest + additional)


def hicbc_charge(ani: Decimal, annual_cb: Decimal) -> Decimal:
    """HICBC charge for given ANI and annual CB received.

    Delegates to the shared reference formula in common.py.
    """
    return hicbc_ref(ani, annual_cb)


def hicbc_threshold() -> tuple[Decimal, Decimal]:
    """Return (HICBC_LOWER, HICBC_UPPER) for assertion use."""
    return HICBC_LOWER, HICBC_UPPER


def pension_to_eliminate_hicbc(ani: Decimal) -> Decimal:
    """Gross pension needed to bring ANI below the £60,000 HICBC threshold.

    As with the PA taper: we need ANI − pension = 60,000.
    ∴ additional = ANI − 60,000.
    """
    if ani <= HICBC_LOWER:
        return Decimal("0")
    return p(ani - HICBC_LOWER)


def charge_percentage(ani: Decimal) -> Decimal:
    """Percentage of CB recovered by HMRC at a given ANI (0–100)."""
    if ani <= HICBC_LOWER:
        return Decimal("0")
    return min(Decimal("100"), (ani - HICBC_LOWER) / Decimal("200"))
