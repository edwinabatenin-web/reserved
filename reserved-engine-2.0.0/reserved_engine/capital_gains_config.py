"""
Capital Gains Tax configuration — multi-year registry.

Module-level constants (TAX_YEAR, RULES_VERSION, etc.) are the current-year
(2026/27) values kept for backward compatibility with existing callers.
New code should use ``get_cgt_config(tax_year)`` to obtain a versioned
configuration dict, mirroring the pattern used by ``tax_config.get_config()``.

Sources
-------
2026/27
  - HMRC Capital Gains Tax rates 2026/27 (confirmed post-Autumn Budget 2024)
  - Annual Exempt Amount: Finance (No.2) Act 2023 — £3,000 from 2024/25 onwards

2025/26
  - HMRC Capital Gains Tax rates 2025/26 (confirmed post-Autumn Budget 2024)
  - Annual Exempt Amount: £3,000 (same as 2026/27; fixed from 2024/25 onwards)

Note on rate history
--------------------
CGT rates on shares and most chargeable assets were revised by the Autumn 2024
budget, effective 30 October 2024 and confirmed for subsequent full tax years:

  Basic rate:  10 % → 18 %
  Higher rate: 20 % → 24 %

Both 2025/26 and 2026/27 therefore carry the same post-budget rates.
Residential property rates remain unchanged at 18 % / 24 % (now unified with
shares) — see warnings in capital_gains.estimate_cgt().

Out of scope (noted as limitations, not config)
-----------------------------------------------
  - Business Asset Disposal Relief (BADR) / Investors' Relief
  - Share-pooling, same-day and 30-day matching rules
  - Carried-interest rules
  - Residential property 60-day reporting obligations
"""
from decimal import Decimal

# ── Supported asset types (shared across all years) ───────────────────────────

_SUPPORTED_ASSET_TYPES: dict[str, str] = {
    "shares":   "Shares and funds",
    "crypto":   "Cryptoassets",
    "property": "Residential property",
    "other":    "Other chargeable assets",
}


# ── Multi-year registry ───────────────────────────────────────────────────────

CONFIGS: dict = {
    # ── 2025/26 ────────────────────────────────────────────────────────────────
    # Rates: post-Autumn Budget 2024 (18 % basic / 24 % higher).
    # AEA:   £3,000 (Finance (No.2) Act 2023).
    "2025/26": {
        "tax_year":              "2025/26",
        "rules_version":         "uk-cgt-2025-26-v1",
        "ANNUAL_EXEMPT_AMOUNT":  Decimal("3000"),
        "BASIC_RATE":            Decimal("0.18"),
        "HIGHER_RATE":           Decimal("0.24"),
        "SUPPORTED_ASSET_TYPES": _SUPPORTED_ASSET_TYPES,
    },
    # ── 2026/27 ────────────────────────────────────────────────────────────────
    # Rates: same as 2025/26 (no change announced).
    # AEA:   £3,000 (same as 2025/26).
    "2026/27": {
        "tax_year":              "2026/27",
        "rules_version":         "uk-cgt-2026-27-preview-v1",
        "ANNUAL_EXEMPT_AMOUNT":  Decimal("3000"),
        "BASIC_RATE":            Decimal("0.18"),
        "HIGHER_RATE":           Decimal("0.24"),
        "SUPPORTED_ASSET_TYPES": _SUPPORTED_ASSET_TYPES,
    },
}

SUPPORTED_CGT_TAX_YEARS: list[str] = sorted(CONFIGS)


def get_cgt_config(tax_year: str = "2026/27") -> dict:
    """Return the CGT configuration dict for the requested tax year.

    Parameters
    ----------
    tax_year:
        HMRC-style tax year string, e.g. ``"2026/27"``.

    Returns
    -------
    dict
        Configuration dict with keys ``tax_year``, ``rules_version``,
        ``ANNUAL_EXEMPT_AMOUNT``, ``BASIC_RATE``, ``HIGHER_RATE``, and
        ``SUPPORTED_ASSET_TYPES``.

    Raises
    ------
    ValueError
        If ``tax_year`` is not in ``SUPPORTED_CGT_TAX_YEARS``.
    """
    if tax_year not in CONFIGS:
        raise ValueError(
            f"CGT tax year {tax_year!r} is not supported. "
            f"Supported years: {SUPPORTED_CGT_TAX_YEARS}"
        )
    return CONFIGS[tax_year]


# ── Current-year (2026/27) module-level constants ─────────────────────────────
# Retained for backward compatibility.  New code should use get_cgt_config().

TAX_YEAR              = "2026/27"
RULES_VERSION         = "uk-cgt-2026-27-preview-v1"
ANNUAL_EXEMPT_AMOUNT  = Decimal("3000")
BASIC_RATE            = Decimal("0.18")
HIGHER_RATE           = Decimal("0.24")
SUPPORTED_ASSET_TYPES = _SUPPORTED_ASSET_TYPES
