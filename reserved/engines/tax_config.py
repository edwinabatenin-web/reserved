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

Blind Person's Allowance
  - GOV.UK, Blind Person's Allowance — What you'll get (2026/27 £3,250; 2025/26 £3,130)
  - The Income Tax (Indexation of Blind Person's Allowance and Married Couple's
    Allowance) Order 2026 (SI 2026/38) sets the statutory 2026/27 amount to £3,250.

Notes on frozen bands
---------------------
Income tax bands (PA £12,570; BRL £50,270; ART £125,140) and Class 4 NI bands
(LPL £12,570; UPL £50,270) were frozen by the Finance Act 2022 through 2028.
They are identical across both supported tax years.  The year-on-year
differences are the student-loan repayment thresholds (uprated annually by
RPI/CPI as published by the Student Loans Company) and the Blind Person's
Allowance (uprated by statutory indexation order).
"""
from decimal import Decimal

# ── Current-year (2026/27) module-level constants ─────────────────────────────
# Kept for backward compatibility.  New code should use get_config().

TAX_YEAR      = "2026/27"
RULES_VERSION = "uk-2026-27-v4"

PERSONAL_ALLOWANCE            = Decimal("12570")
PERSONAL_ALLOWANCE_TAPER_START = Decimal("100000")
BLIND_PERSONS_ALLOWANCE       = Decimal("3250")
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

DIVIDEND_ALLOWANCE = Decimal("500")
DIVIDEND_TAX_RATES = {
    "basic": Decimal("0.1075"),
    "higher": Decimal("0.3575"),
    "additional": Decimal("0.3935"),
}
SAVINGS = {
    "starting_rate_limit": Decimal("5000"),
    "personal_savings_allowance_basic": Decimal("1000"),
    "personal_savings_allowance_higher": Decimal("500"),
    "personal_savings_allowance_additional": Decimal("0"),
}
HICBC = {
    "lower_threshold": Decimal("60000"),
    "upper_threshold": Decimal("80000"),
    "income_per_percentage_point": Decimal("200"),
}
CHILD_BENEFIT = {
    "eldest_weekly": Decimal("27.05"),
    "additional_weekly": Decimal("17.90"),
    "weeks_per_year": Decimal("52"),
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
    "SAVINGS": SAVINGS,
    "HICBC": HICBC,
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
        "rules_version": "uk-2025-26-v2",
        "BLIND_PERSONS_ALLOWANCE": Decimal("3130"),
        "DIVIDEND_ALLOWANCE": Decimal("500"),
        "DIVIDEND_TAX_RATES": {
            "basic": Decimal("0.0875"),
            "higher": Decimal("0.3375"),
            "additional": Decimal("0.3935"),
        },
        "CHILD_BENEFIT": {
            "eldest_weekly": Decimal("26.05"),
            "additional_weekly": Decimal("17.25"),
            "weeks_per_year": Decimal("52"),
        },
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
        "rules_version": "uk-2026-27-v4",
        "BLIND_PERSONS_ALLOWANCE": BLIND_PERSONS_ALLOWANCE,
        "DIVIDEND_ALLOWANCE": DIVIDEND_ALLOWANCE,
        "DIVIDEND_TAX_RATES": DIVIDEND_TAX_RATES,
        "CHILD_BENEFIT": CHILD_BENEFIT,
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
