"""
Initiative 002 — Independent Personal Allowance taper reference.

Implements the PA taper calculation from primary statutory sources.
No code shared with reserved.engines.income_tax.

Source: ITEPA 2003 s.35; Finance (No.2) Act 2015.
"""
from decimal import Decimal
from .common import p, PA, TAPER_START, TAPER_END, personal_allowance_ref


def effective_marginal_rate_in_taper(marginal_it_rate: Decimal = Decimal("0.40")) -> Decimal:
    """Effective marginal rate in the PA taper band.

    In the £100,000 – £125,140 band, every additional £1 of income:
      1. Is taxed at the marginal IT rate (default 40 %).
      2. Reduces PA by £0.50, creating £0.50 of previously-untaxed income
         now taxed at the marginal rate.
    Total: marginal_it_rate + marginal_it_rate × 0.50

    At 40 %: 0.40 + 0.40 × 0.50 = 0.60 (60 % effective rate).
    """
    return p(marginal_it_rate + marginal_it_rate * Decimal("0.50"))


def pa_taper_zone() -> tuple[Decimal, Decimal]:
    """Return (TAPER_START, TAPER_END) for test assertions."""
    return TAPER_START, TAPER_END


def pension_to_restore_full_pa(ani: Decimal) -> Decimal:
    """Minimum additional gross pension to restore the full Personal Allowance.

    This is the gross pension contribution required to bring ANI to exactly
    the taper start (£100,000), restoring the full £12,570 PA.

    income − (current_pension + additional) = 100,000
    → additional = income − current_pension − 100,000
                 = ANI − 100,000

    In the optimise engine this is calculated from projected income and
    current pension; here we accept ANI directly for clarity.
    """
    if ani <= TAPER_START:
        return Decimal("0")
    return p(ani - TAPER_START)


def pa_at_ani(ani: Decimal) -> Decimal:
    """Personal Allowance for a given ANI.  Wrapper around reference calc."""
    return personal_allowance_ref(ani)


def pa_reduction_at_ani(ani: Decimal) -> Decimal:
    """Reduction applied to the full £12,570 PA at a given ANI."""
    return p(PA - personal_allowance_ref(ani))
