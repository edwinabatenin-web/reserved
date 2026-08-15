"""Authoritative tax-year resolution for customer-facing surfaces.

A customer-facing surface must never hard-code a tax year.  It resolves the
applicable year in priority order:

1. the tax year attached to the calculation/result contract it is displaying
   (for example the ``tax_year`` field carried by a returned result object or
   serialized response);
2. the authoritative configured workflow context (the engine's current tax
   year, ``tax_config.TAX_YEAR``) — used for surfaces such as settings or
   onboarding that are not displaying a particular calculation result.

A year is never inferred from today's date.  If no supported year can be
determined the resolver returns ``None`` (an unavailable state) so a surface
can fail closed rather than inventing or silently defaulting to a year.

Literal years may remain only in the tax configuration (``tax_config``), in
tests, and in clearly historical material; they must not reappear in generic
customer-facing templates or routes.
"""
from __future__ import annotations

from typing import Any

from reserved.engines import tax_config


def configured_tax_year() -> str:
    """Return the authoritative configured workflow tax year."""
    return tax_config.TAX_YEAR


def is_supported_tax_year(year: Any) -> bool:
    """Return ``True`` iff ``year`` is a supported engine tax-year string."""
    return isinstance(year, str) and year in tax_config.SUPPORTED_TAX_YEARS


def resolve_tax_year(
    *,
    result_tax_year: Any = None,
    context_tax_year: Any = None,
) -> str | None:
    """Resolve the applicable tax year, preferring the result contract.

    Returns ``None`` when no supported year can be determined.  The caller is
    responsible for surfacing that as an unavailable state rather than
    substituting a literal year.
    """
    if is_supported_tax_year(result_tax_year):
        return result_tax_year
    if is_supported_tax_year(context_tax_year):
        return context_tax_year
    return None
