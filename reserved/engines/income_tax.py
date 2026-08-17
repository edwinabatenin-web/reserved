"""
Incremental income-tax, Class 4 NI, and student-loan liability estimator.

Methodology
-----------
The engine uses a *before/after* differential approach:

    liability = total_income_tax(end_income) − total_income_tax(start_income)

where ``start_income = employment_income + ytd_freelance_profit`` and
``end_income = start_income + invoice``.

Each ``total_income_tax`` call independently determines:

  1. Adjusted Net Income (ANI = income − gross pension contributions)
  2. Personal Allowance applicable at *that* income level (after taper)
  3. Taxable income across the statutory bands
  4. Total income-tax liability

This correctly handles all Personal Allowance taper cases, including
invoices that enter, remain within, or exit the £100,000 – £125,140 taper
zone.

Pension Relief at Source (RaS)
-------------------------------
Gross pension contributions do two things:

  1. Reduce Adjusted Net Income (ANI) for the Personal Allowance taper test.
  2. **Extend the basic-rate band** by the same gross amount, meaning more
     income is taxed at 20 % rather than 40 %.

Both are implemented here.  The engine does *not* model employer contributions,
salary sacrifice, or relief-in-the-year-of-claim schemes.

Multi-year support
------------------
Pass ``tax_year="2025/26"`` to use confirmed 2025/26 thresholds.  The default
is ``"2026/27"``.  Income-tax and NI bands are frozen and identical in both
supported years; only student-loan repayment thresholds differ.

Change history (income-tax component)
--------------------------------------
v1.0.0  Initial release.  Used a single end-state ANI to fix the PA for the
        full [start, end) range — underestimated when invoice crossed the
        PA taper zone (EL-001).

v2.0.0  EL-001 resolved.  The income-tax component now calls
        ``_total_income_tax(end) − _total_income_tax(start)``, each with
        the correct PA for its own income level.  Results outside the taper
        zone (ANI < £100,000 or ANI ≥ £125,140 at both start and end) are
        numerically unchanged.

Out of scope
------------
  - Scottish income tax (different bands apply)
  - Dividend tax and savings income (separate orders of priority)
  - BADR / Investors' Relief on capital gains (handled in capital_gains.py)
  - PAYE coding adjustments (this is a self-assessment estimate only)
"""
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from . import tax_config
from .utils import money


class UnsupportedStudentLoanPlanCombination(ValueError):
    """Annual-SA plan selection is outside the approved calculation scope."""

    calculation_status = "unsupported_rule"
    unsupported_family = "simultaneous_multiple_undergraduate_plans"
    uncertainty_reason = "unsupported_rule_requires_verification"
    uncertainty_effect = "not_determinable"
    verification_requirement = (
        "Verify the applicable annual Self Assessment plan treatment with HMRC "
        "or a qualified tax adviser before using a student-loan or total amount."
    )
    limitations = (
        "annual_self_assessment_multiple_undergraduate_plan_selection_not_approved",
        "no_student_loan_or_total_monetary_result_available",
        "annual_plan_treatment_requires_external_verification",
    )


# ── Internal helpers (all accept a ``cfg`` dict from get_config()) ─────────────

def _personal_allowance(adjusted_net_income: Decimal, cfg: dict) -> Decimal:
    """Return the Personal Allowance after taper.

    The allowance is reduced by £1 for every £2 of ANI above £100,000,
    reaching zero at ANI ≥ £125,140.
    """
    allowance = cfg["PERSONAL_ALLOWANCE"]
    if adjusted_net_income <= cfg["PERSONAL_ALLOWANCE_TAPER_START"]:
        return allowance
    reduction = (
        adjusted_net_income - cfg["PERSONAL_ALLOWANCE_TAPER_START"]
    ) / Decimal("2")
    return max(Decimal("0"), allowance - reduction)


def _income_tax_between(
    start: Decimal,
    end: Decimal,
    basic_rate_band: Decimal,
    higher_rate_limit: Decimal,
    cfg: dict,
) -> Decimal:
    """Return tax on *taxable income* in the half-open interval [start, end).

    ``basic_rate_band`` is the (possibly extended) basic-rate limit and
    ``higher_rate_limit`` is the (possibly extended) higher-rate limit at which
    the additional rate begins.  Band widths are measured from zero taxable
    income; both limits are passed in explicitly so callers can apply the
    Relief-at-Source band extension (which shifts both boundaries) without the
    helper silently fixing the higher-rate limit at the statutory threshold.
    """
    if end <= start:
        return Decimal("0")

    bands = [
        (basic_rate_band,                         cfg["INCOME_TAX_RATES"]["basic"]),
        (higher_rate_limit,                       cfg["INCOME_TAX_RATES"]["higher"]),
        (Decimal("Infinity"),                    cfg["INCOME_TAX_RATES"]["additional"]),
    ]

    total = Decimal("0")
    cursor = start
    for ceiling, rate in bands:
        if cursor >= end:
            break
        if cursor < ceiling:
            slice_end = min(end, ceiling)
            total += max(Decimal("0"), slice_end - cursor) * rate
            cursor = slice_end
    return money(total)


def _total_income_tax(
    income: Decimal,
    pension: Decimal,
    cfg: dict,
) -> Decimal:
    """Return the total income-tax liability on *income* with gross pension *pension*.

    Computes the complete liability from £0 up to *income*, independently
    deriving the Personal Allowance and extended basic-rate limit that
    correspond to *this specific income level*.

    This is the authoritative full-liability calculation used by
    ``estimate_incremental_liability`` to produce a correct before/after
    differential across the PA taper zone.

    Pension RaS (Finance Act 2004 s.192; HMRC Pensions Tax Manual PTM056120):
      - Reduces ANI (``ANI = income − pension``) for the PA taper test.
      - Extends BOTH the basic-rate limit and the higher-rate limit (the point
        at which the additional rate begins) by the gross pension amount, so
        the higher-rate band width (£87,440) is unchanged.
    """
    if income <= Decimal("0"):
        return Decimal("0")

    ani                       = max(Decimal("0"), income - pension)
    allowance                 = _personal_allowance(ani, cfg)
    taxable_income = max(Decimal("0"), income - allowance)
    # A gross Relief-at-Source contribution shifts both the basic-rate limit and
    # the higher-rate limit up by the same amount (PTM056120).  No cap applies:
    # a contribution larger than the basic-rate band simply moves both boundaries
    # and preserves the £87,440 higher-rate band width.
    extended_basic_rate_band  = cfg["BASIC_RATE_BAND"] + pension
    extended_higher_rate_limit = cfg["ADDITIONAL_RATE_THRESHOLD"] + pension

    return _income_tax_between(
        Decimal("0"),
        taxable_income,
        extended_basic_rate_band,
        extended_higher_rate_limit,
        cfg,
    )


def _class_4_ni_between(
    start_profit: Decimal,
    end_profit: Decimal,
    cfg: dict,
) -> Decimal:
    """Return Class 4 NI on sole-trader profit in the interval [start_profit, end_profit)."""
    if end_profit <= start_profit:
        return Decimal("0")

    lower = cfg["CLASS_4_NI"]["lower_profits_limit"]
    upper = cfg["CLASS_4_NI"]["upper_profits_limit"]
    main_slice  = max(Decimal("0"), min(end_profit, upper) - max(start_profit, lower))
    upper_slice = max(Decimal("0"), end_profit - max(start_profit, upper))

    return money(
        main_slice  * cfg["CLASS_4_NI"]["main_rate"]
        + upper_slice * cfg["CLASS_4_NI"]["upper_rate"]
    )


def _student_loan_between(
    start: Decimal,
    end: Decimal,
    plan: Any,
    cfg: dict,
) -> Decimal:
    """Return incremental annual Self Assessment loan liability.

    This is not a payroll-period deduction. Annual liability is calculated at
    both ends and rounded down to whole pounds before taking the difference.
    """
    metadata = cfg["STUDENT_LOANS"].get(plan)
    if not metadata:
        return Decimal("0")
    threshold  = metadata["threshold"]
    def annual_total(income):
        chargeable = max(Decimal("0"), income - threshold)
        return (chargeable * metadata["rate"]).to_integral_value(
            rounding=ROUND_FLOOR
        )

    return money(max(Decimal("0"), annual_total(end) - annual_total(start)))


def _student_loan_total_between(start: Decimal, end: Decimal, plans: list, cfg: dict):
    """Return statutory combined repayment and a transparent breakdown.

    One undergraduate plan may be combined with a Postgraduate Loan. More than
    one distinct undergraduate plan fails closed because the annual Self
    Assessment selection rule has not been independently approved.

    Values represent annual Self Assessment liability, rounded down to whole
    pounds per loan component. They are not payroll-period deductions.
    """
    unsupported = tuple(dict.fromkeys(
        plan for plan in plans
        if plan != "postgraduate" and plan not in cfg["STUDENT_LOANS"]
    ))
    undergraduate = list(dict.fromkeys(
        plan for plan in plans
        if plan != "postgraduate" and plan in cfg["STUDENT_LOANS"]
    ))
    if unsupported or len(undergraduate) > 1:
        raise UnsupportedStudentLoanPlanCombination(
            "Cannot calculate student-loan liability when supplied loan plans are "
            "outside the approved annual Self Assessment scope."
        )
    selected_undergraduate = None
    if undergraduate:
        selected_undergraduate = undergraduate[0]
    selected = ([selected_undergraduate] if selected_undergraduate is not None else [])
    if "postgraduate" in plans:
        selected.append("postgraduate")
    breakdown = [
        {"plan": plan, "amount": _student_loan_between(start, end, plan, cfg)}
        for plan in selected
    ]
    return money(sum((item["amount"] for item in breakdown), Decimal("0"))), breakdown


# ── Public API ────────────────────────────────────────────────────────────────

def estimate_incremental_liability(
    invoice_amount: Any,
    profile: dict,
    tax_year: str = "2026/27",
) -> dict:
    """Estimate the marginal tax cost of a single invoice.

    Parameters
    ----------
    invoice_amount:
        The gross invoice value (will be coerced to Decimal).
    profile:
        Dict with the following keys:

        ``day_job_salary``
            Annual PAYE employment income already received this tax year.
        ``ytd_freelance_profit``
            Sole-trader / freelance profit *before* this invoice.
        ``personal_pension_contributions``
            Gross personal pension contributions this tax year (Relief at
            Source: gross = net paid ÷ 0.80 if your provider claims the
            basic-rate top-up).
        ``student_loan_plans``
            List of active plan identifiers, e.g. ``[2]`` or
            ``[1, "postgraduate"]``.  The legacy singular key
            ``student_loan_plan`` is also accepted.

    tax_year:
        HMRC tax year string, e.g. ``"2026/27"`` (default) or ``"2025/26"``.
        Use ``tax_config.SUPPORTED_TAX_YEARS`` to enumerate valid values.

    Returns
    -------
    dict
        ``income_tax``, ``national_insurance``, ``student_loan``, ``total``
        (all Decimal rounded to the nearest penny), plus metadata fields.

    Raises
    ------
    ValueError
        If ``invoice_amount`` is not greater than zero, any profile value
        is invalid or negative, or ``tax_year`` is not supported.
    """
    cfg = tax_config.get_config(tax_year)

    # ── Validate invoice ──────────────────────────────────────────────────────
    try:
        invoice = money(invoice_amount)
    except Exception as exc:
        raise ValueError(f"invoice_amount is not a valid number: {exc}") from exc
    if invoice <= Decimal("0"):
        raise ValueError("invoice_amount must be greater than zero.")

    # ── Validate and extract profile ──────────────────────────────────────────
    def _require_nonneg(key: str) -> Decimal:
        raw = profile.get(key, 0)
        try:
            val = money(raw)
        except Exception as exc:
            raise ValueError(
                f"Profile field '{key}' is not a valid number: {exc}"
            ) from exc
        if val < Decimal("0"):
            raise ValueError(
                f"Profile field '{key}' must not be negative (got {val})."
            )
        return val

    employment_income = _require_nonneg("day_job_salary")
    prior_profit      = _require_nonneg("ytd_freelance_profit")
    pension           = _require_nonneg("personal_pension_contributions")

    # Student loan plans — accept list (preferred) or legacy singular key.
    plans: list = profile.get("student_loan_plans") or []
    if not plans:
        legacy = profile.get("student_loan_plan")
        if legacy is not None:
            plans = [legacy]

    # ── Core calculation ──────────────────────────────────────────────────────
    start_income = employment_income + prior_profit
    end_income   = start_income + invoice

    # Income tax: total_tax(end) − total_tax(start).
    # Each call independently determines ANI, PA, and the extended BRL for
    # its own income level.  This correctly handles all PA taper cases,
    # including invoices that cross or remain within the £100k–£125.14k zone.
    income_tax = money(
        _total_income_tax(end_income,   pension, cfg)
        - _total_income_tax(start_income, pension, cfg)
    )

    national_insurance = _class_4_ni_between(
        prior_profit, prior_profit + invoice, cfg
    )

    total_student_loan, student_loan_breakdown = _student_loan_total_between(
        start_income, end_income, plans, cfg
    )

    total = money(income_tax + national_insurance + total_student_loan)

    # ── Build result ──────────────────────────────────────────────────────────
    result: dict = {
        "tax_year":           cfg["tax_year"],
        "rules_version":      cfg["rules_version"],
        "income_tax":         income_tax,
        "national_insurance": national_insurance,
        "student_loan":       total_student_loan,
        "student_loan_basis": "annual_self_assessment_liability",
        "total":              total,
        "assumptions": [
            "Illustrative sole-trader estimate only; not a tax return or professional advice.",
            "Scottish income tax and Capital Gains Tax are outside v1 scope.",
            "Dividend, savings, property and HICBC inputs require the full-position engine; this incremental invoice result does not yet include them.",
            "Pension contributions are treated as Relief at Source (gross figure expected).",
            "Student-loan figures are incremental annual Self Assessment liabilities, not payroll-period deductions; each component is rounded down to whole pounds.",
        ],
    }
    if student_loan_breakdown:
        result["student_loan_breakdown"] = student_loan_breakdown

    return result
