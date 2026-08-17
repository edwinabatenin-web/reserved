"""
Initiative 002 — Independent pension RaS + band-extension reference.

Models Relief-at-Source pension contributions for the 2026/27 tax year.
No code shared with reserved.engines.

Source: Finance Act 2004 s.192; HMRC PTM056120.
"""
from decimal import Decimal
from .common import p, income_tax_total_ref, PA, BRL, ART

# Standard Annual Allowance 2026/27
ANNUAL_ALLOWANCE = Decimal("60000")

# MPAA and tapered AA thresholds (for constraint warnings only — not modelled)
MPAA = Decimal("10000")
TAPERED_AA_THRESHOLD_ADJUSTED_INCOME = Decimal("260000")


def net_to_gross(net_paid: Decimal) -> Decimal:
    """Convert net pension payment to gross (÷ 0.80).

    Under Relief at Source, the provider claims 20 % basic-rate relief
    from HMRC and adds it to the pot.  The user's gross contribution is
    the total pension pot increase (net + relief).
    """
    return p(net_paid / Decimal("0.80"))


def gross_to_net(gross: Decimal) -> Decimal:
    """Convert gross pension amount to net paid by user (× 0.80)."""
    return p(gross * Decimal("0.80"))


def basic_rate_relief(gross: Decimal) -> Decimal:
    """HMRC basic-rate relief added to the pension (20 % of gross).

    This is NOT a tax saving to the user — it is the amount HMRC adds
    to the pension fund and is already reflected in the gross amount.
    It is surfaced separately to prevent double-counting.
    """
    return p(gross * Decimal("0.20"))


def extended_brl(pension: Decimal) -> Decimal:
    """Extended basic-rate *band* after RaS pension contributions.

    The statutory basic-rate band is £37,700 of taxable income (= BRL − PA).
    A gross Relief-at-Source contribution extends that band by the gross
    amount with no cap (PTM056120).  The higher-rate limit extends by the
    same amount; see ``income_tax_total_ref`` in ``common.py``.

    Source: HMRC PTM056120; Finance Act 2004 s.192.
    """
    return (BRL - PA) + pension


def extended_hrl(pension: Decimal) -> Decimal:
    """Extended higher-rate *limit* (additional-rate threshold) after RAS.

    The statutory higher-rate limit is £125,140.  A gross Relief-at-Source
    contribution extends it by the gross amount, mirroring the basic-rate
    limit extension (PTM056120).
    """
    return ART + pension


def it_saving_from_pension(
    projected_income: Decimal,
    current_pension: Decimal,
    additional_pension: Decimal,
) -> Decimal:
    """Income-tax saving from adding `additional_pension` gross.

    Computes full-year IT before and after and returns the difference.
    """
    before = income_tax_total_ref(projected_income, current_pension)
    after  = income_tax_total_ref(projected_income, current_pension + additional_pension)
    return p(max(Decimal("0"), before - after))
