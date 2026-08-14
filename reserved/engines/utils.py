"""
Shared arithmetic utilities for Reserved tax engines.

Rounding policy: ROUND_HALF_UP to the nearest penny, matching HMRC PAYE
rounding conventions (SA100 guidance rounds liabilities up to the nearest
penny in the taxpayer's favour on each computation step).
"""
from decimal import Decimal, ROUND_HALF_UP

PENNY = Decimal("0.01")


def money(value) -> Decimal:
    """Round *value* to the nearest penny using ROUND_HALF_UP.

    Accepts any numeric type or string; ``None`` / falsy values are treated
    as zero so callers can safely pass ``profile.get("key")`` directly.
    """
    return Decimal(str(value or 0)).quantize(PENNY, rounding=ROUND_HALF_UP)
