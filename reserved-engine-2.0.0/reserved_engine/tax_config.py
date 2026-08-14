"""
UK tax configuration — multi-year registry.

Module-level constants (PERSONAL_ALLOWANCE, BASIC_RATE_LIMIT, etc.) are the
current-year (2026/27) values kept for backward compatibility with existing
callers.  The canonical source of truth for each tax year is the ``CONFIGS``
dict below; use ``get_config(tax_year)`` to obtain a versioned config dict.

Sources
-------
2026/27
  - HMRC Rates and thresholds for employers 2026/27 (published April 2026)
  - Student Loans Company threshold notices 2026/27

2025/26
  - HMRC Rates and thresholds for employers 2025/26 (published April 2025)
  - Student Loans Company threshold notices 2025/26

Notes on frozen bands
---------------------
Income tax bands (PA £12,570; BRL £50,270; ART £125,140) and Class 4 NI bands
(LPL £12,570; UPL £50,270) were frozen by the Finance Act 2022 through 2028.
They are identical across both supported tax years.  The only year-on-year
differences are the student-loan repayment thresholds, which are uprated
annually by RPI/CPI as published by the Student Loans Company.
"""
from decimal import Decimal

# ── Current-year (2026/27) module-level constants ─────────────────────────────
# Kept for backward compatibility.  New code should use get_config().

TAX_YEAR      = "2026/27"
RULES_VERSION = "uk-2026-27-v3"

PERSONAL_ALLOWANCE            = Decimal("12570")
PERSONAL_ALLOWANCE_TAPER_START = Decimal("100000")
BASIC_RATE_LIMIT              = Decimal("50270")
BASIC_RATE_BAND               = Decimal("37700")
ADDITIONAL_RATE_THRESHOLD     = Decimal("125140")

INCOME_TAX_RATES = {
    "basic":      Decimal("0.20"),
    "higher":     Decimal("0.40"),
    "additional": Decimal("0.45"),
}

CLASS_4_NI = {
    "lower_profits_limit": Decimal("12570"),
    "upper_profits_limit": Decimal("50270"),
    "main_rate":           Decimal("0.06"),
    "upper_rate":          Decimal("0.02"),
}

STUDENT_LOANS = {
    1:              {"threshold": Decimal("26900"), "rate": Decimal("0.09")},
    2:              {"threshold": Decimal("29385"), "rate": Decimal("0.09")},
    4:              {"threshold": Decimal("33795"), "rate": Decimal("0.09")},
    5:              {"threshold": Decimal("25000"), "rate": Decimal("0.09")},
    "postgraduate": {"threshold": Decimal("21000"), "rate": Decimal("0.06")},
}


# ── Shared frozen-band block ───────────────────────────────────────────────────
# Income tax and NI bands are identical for 2025/26 and 2026/27.

_FROZEN_IT_BANDS = {
    "PERSONAL_ALLOWANCE":             Decimal("12570"),
    "PERSONAL_ALLOWANCE_TAPER_START": Decimal("100000"),
    "BASIC_RATE_LIMIT":               Decimal("50270"),
    "BASIC_RATE_BAND":                Decimal("37700"),
    "ADDITIONAL_RATE_THRESHOLD":      Decimal("125140"),
    "INCOME_TAX_RATES": {
        "basic":      Decimal("0.20"),
        "higher":     Decimal("0.40"),
        "additional": Decimal("0.45"),
    },
    "CLASS_4_NI": {
        "lower_profits_limit": Decimal("12570"),
        "upper_profits_limit": Decimal("50270"),
        "main_rate":           Decimal("0.06"),
        "upper_rate":          Decimal("0.02"),
    },
}


# ── Multi-year registry ────────────────────────────────────────────────────────

CONFIGS: dict = {
    # ── 2025/26 ────────────────────────────────────────────────────────────────
    # Income tax / NI bands: frozen (identical to 2026/27).
    # Student-loan thresholds: SLC Annual Threshold Notice 2025/26.
    #   Plan 1 (£24,990): uprated by RPI from 2024/25 £24,990 (frozen year).
    #   Plan 2 (£28,470): uprated by RPI from 2024/25 £27,295.
    #   Plan 4 (£32,745): uprated by RPI from 2024/25 £31,395.
    #   Plan 5 (£25,000): statutory fixed threshold until Apr 2027.
    #   PGL    (£21,000): statutory fixed threshold.
    "2025/26": {
        **_FROZEN_IT_BANDS,
        "tax_year":      "2025/26",
        "rules_version": "uk-2025-26-v1",
        "STUDENT_LOANS": {
            1:              {"threshold": Decimal("24990"), "rate": Decimal("0.09")},
            2:              {"threshold": Decimal("28470"), "rate": Decimal("0.09")},
            4:              {"threshold": Decimal("32745"), "rate": Decimal("0.09")},
            5:              {"threshold": Decimal("25000"), "rate": Decimal("0.09")},
            "postgraduate": {"threshold": Decimal("21000"), "rate": Decimal("0.06")},
        },
    },
    # ── 2026/27 ────────────────────────────────────────────────────────────────
    # Income tax / NI bands: frozen (identical to 2025/26).
    # Student-loan thresholds: SLC Annual Threshold Notice 2026/27.
    #   Plan 1 (£26,900): uprated by RPI.
    #   Plan 2 (£29,385): uprated by RPI.
    #   Plan 4 (£33,795): uprated by RPI.
    #   Plan 5 (£25,000): statutory fixed threshold.
    #   PGL    (£21,000): statutory fixed threshold.
    "2026/27": {
        **_FROZEN_IT_BANDS,
        "tax_year":      "2026/27",
        "rules_version": "uk-2026-27-v1",
        "STUDENT_LOANS": {
            1:              {"threshold": Decimal("26900"), "rate": Decimal("0.09")},
            2:              {"threshold": Decimal("29385"), "rate": Decimal("0.09")},
            4:              {"threshold": Decimal("33795"), "rate": Decimal("0.09")},
            5:              {"threshold": Decimal("25000"), "rate": Decimal("0.09")},
            "postgraduate": {"threshold": Decimal("21000"), "rate": Decimal("0.06")},
        },
    },
}

SUPPORTED_TAX_YEARS = sorted(CONFIGS)


def get_config(tax_year: str = "2026/27") -> dict:
    """Return the full configuration dict for the requested tax year.

    Parameters
    ----------
    tax_year:
        HMRC-style tax year string, e.g. ``"2026/27"``.

    Returns
    -------
    dict
        Configuration dict with keys ``tax_year``, ``rules_version``,
        ``PERSONAL_ALLOWANCE``, ``BASIC_RATE_LIMIT``, ``ADDITIONAL_RATE_THRESHOLD``,
        ``INCOME_TAX_RATES``, ``CLASS_4_NI``, ``STUDENT_LOANS``, etc.

    Raises
    ------
    ValueError
        If ``tax_year`` is not in ``SUPPORTED_TAX_YEARS``.
    """
    if tax_year not in CONFIGS:
        raise ValueError(
            f"Tax year {tax_year!r} is not supported. "
            f"Supported years: {SUPPORTED_TAX_YEARS}"
        )
    return CONFIGS[tax_year]
