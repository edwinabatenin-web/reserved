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


class UnsupportedTaxYear(ValueError):
    """A supplied tax year is malformed, unsupported or contradictory."""


def resolve_tax_year(
    *,
    result_tax_year: Any = None,
    context_tax_year: Any = None,
) -> str | None:
    """Resolve the applicable tax year, failing closed on invalid explicit input.

    * ``result_tax_year is None`` — genuinely absent: the approved context year
      may be used (returned when supported, otherwise ``None``).
    * present and supported — used, subject to consistency with a supported
      context year.  A valid but *different* context year is contradictory and
      fails closed.
    * present but malformed or unsupported — fails closed (``UnsupportedTaxYear``).
      An explicit invalid year is never treated as merely absent.

    ``None`` is reserved exclusively for the genuinely-unavailable state; any
    other outcome the caller must surface as unavailable rather than silently
    substituting a literal year.
    """
    if result_tax_year is None:
        return context_tax_year if is_supported_tax_year(context_tax_year) else None

    if not is_supported_tax_year(result_tax_year):
        raise UnsupportedTaxYear(
            f"unsupported or malformed result tax year: {result_tax_year!r}"
        )

    if is_supported_tax_year(context_tax_year) and context_tax_year != result_tax_year:
        raise UnsupportedTaxYear(
            f"result tax year {result_tax_year!r} conflicts with "
            f"context tax year {context_tax_year!r}"
        )

    return result_tax_year
