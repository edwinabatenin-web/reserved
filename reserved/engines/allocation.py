"""
Legacy gross allocation splitter.

This result is retained as an internal compatibility contract while the
customer-facing "safe to spend" concept is removed. It must not be presented
as an amount that is available or safe for a customer to spend: the inputs do
not establish the customer's complete cash position.

Given a gross invoice amount and an estimated tax liability, this module
splits the payment into three buckets:

  tax_reserve     — the estimated tax to hold back
  platform_fee    — Reserved's service fee (zero in preview)
  safe_to_spend   — deprecated arithmetic remainder (internal only)

Rounding guarantee
------------------
safe_to_spend is computed by subtraction (gross − liability − fee), so when
gross ≥ liability + fee the three buckets always sum exactly to gross and
``reconciles`` is always True.  When the liability exceeds the gross (edge
case: invoice smaller than its own tax estimate), safe_to_spend is clamped
to zero and ``reconciles`` is False — the caller must surface this to the user.
"""
from decimal import Decimal

from .utils import money


def build_allocation(
    gross_amount,
    estimated_liability,
    fee_rate: str = "0.00",
) -> dict:
    """Return the allocation breakdown for a single invoice.

    Parameters
    ----------
    gross_amount:
        Total invoice value received.
    estimated_liability:
        Tax liability as estimated by the income-tax engine.
    fee_rate:
        Reserved platform fee as a decimal fraction of the liability
        (e.g. ``"0.01"`` for 1 %).  Zero in preview mode.

    Returns
    -------
    dict
        ``gross_amount``, ``tax_reserve``, ``platform_fee``,
        ``safe_to_spend`` (deprecated internal remainder; all Decimal), and
        ``reconciles`` (bool).
    """
    gross     = money(gross_amount)
    liability = money(estimated_liability)
    fee       = money(liability * Decimal(str(fee_rate)))

    # Compute safe_to_spend by subtraction so that rounding stays consistent.
    safe_to_spend = money(max(Decimal("0"), gross - liability - fee))
    reconciles    = money(liability + fee + safe_to_spend) == gross

    # Reconciliation must hold whenever gross ≥ liability + fee.
    assert reconciles or safe_to_spend == Decimal("0"), (
        "Allocation arithmetic error: buckets do not sum to gross. "
        f"gross={gross}, liability={liability}, fee={fee}, "
        f"safe_to_spend={safe_to_spend}"
    )

    return {
        "gross_amount":   gross,
        "tax_reserve":    liability,
        "platform_fee":   fee,
        "safe_to_spend":  safe_to_spend,
        "reconciles":     reconciles,
    }
