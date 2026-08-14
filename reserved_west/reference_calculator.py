"""
Reserved West — Independent HMRC-Grounded Reference Calculator
===============================================================

This module implements UK income tax, Class 4 NI, student loan, and CGT
calculations from HMRC primary sources.  It is deliberately independent
of the Reserved engine: no imports from reserved_engine, all thresholds
hard-coded from HMRC publications, and a different algorithmic approach
(total-tax differential rather than range-based).

Algorithmic independence
------------------------
The engine uses a range-based approach:
    liability = _income_tax_between(start_income, end_income, fixed_pa, fixed_ebrl)

This reference uses a total-then-differential approach:
    liability = total_it(end_income, pension) − total_it(start_income, pension)

The two approaches diverge in the EL-001 zone (ANI crossing £100,000)
because the engine fixes the Personal Allowance at its end-state value for
the entire range, while this reference computes the correct PA at each
income point independently.  See EL-001 in the engine's ASSUMPTIONS register.

HMRC sources
------------
Income tax bands (frozen Finance Act 2022, through 2028):
  https://www.gov.uk/income-tax-rates
  Income Tax Act 2007 ss.10-12; Finance (No.2) Act 2023 s.5 (ART at £125,140)

Personal Allowance taper:
  Income Tax Act 2007 s.35 (adjusted net income); HMRC SA150 guide

Class 4 NI:
  https://www.gov.uk/self-employed-national-insurance-rates
  Social Security Contributions and Benefits Act 1992 s.15

Pension Relief at Source:
  Finance Act 2004 s.192; HMRC Pensions Tax Manual PTM044100
  BRL extension: HMRC IT manual at EIM45820

Student loan repayments:
  Education (Student Loans) (Repayment) Regulations 2009 (SI 2009/470)
  SLC Annual Threshold Notices 2025/26 and 2026/27

Capital Gains Tax:
  Taxation of Chargeable Gains Act 1992
  Finance (No.2) Act 2023 s.8 (AEA £3,000 from 2024/25)
  Autumn Budget 2024: rates revised to 18 % basic / 24 % higher
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# ── Shared rounding ───────────────────────────────────────────────────────────

PENNY = Decimal("0.01")
ZERO  = Decimal("0")
INF   = Decimal("Infinity")


def _money(value) -> Decimal:
    """Round to nearest penny using ROUND_HALF_UP (matches HMRC SA rounding)."""
    return Decimal(str(value or 0)).quantize(PENNY, rounding=ROUND_HALF_UP)


# ── Hard-coded HMRC configuration (independent of engine tax_config.py) ──────
#
# Cross-checked against HMRC published rates post-Autumn Budget 2024.
# Income-tax bands are frozen under Finance Act 2022 through 2028.
# Student-loan thresholds are SLC Annual Threshold Notices for each year.

_IT_CFG: dict = {
    "2025/26": {
        "PA":             Decimal("12570"),   # Personal Allowance
        "PA_TAPER":       Decimal("100000"),  # ANI taper start
        "BRL":            Decimal("50270"),   # Basic Rate Limit (frozen)
        "ART":            Decimal("125140"),  # Additional Rate Threshold
        "BASIC":          Decimal("0.20"),
        "HIGHER":         Decimal("0.40"),
        "ADDITIONAL":     Decimal("0.45"),
        "NI_LPL":         Decimal("12570"),   # Class 4 Lower Profits Limit
        "NI_UPL":         Decimal("50270"),   # Class 4 Upper Profits Limit
        "NI_MAIN":        Decimal("0.06"),    # Class 4 main rate
        "NI_UPPER":       Decimal("0.02"),    # Class 4 upper rate
        "SL": {
            1:              {"threshold": Decimal("24990"), "rate": Decimal("0.09")},
            2:              {"threshold": Decimal("28470"), "rate": Decimal("0.09")},
            4:              {"threshold": Decimal("32745"), "rate": Decimal("0.09")},
            5:              {"threshold": Decimal("25000"), "rate": Decimal("0.09")},
            "postgraduate": {"threshold": Decimal("21000"), "rate": Decimal("0.06")},
        },
    },
    "2026/27": {
        "PA":             Decimal("12570"),
        "PA_TAPER":       Decimal("100000"),
        "BRL":            Decimal("50270"),
        "ART":            Decimal("125140"),
        "BASIC":          Decimal("0.20"),
        "HIGHER":         Decimal("0.40"),
        "ADDITIONAL":     Decimal("0.45"),
        "NI_LPL":         Decimal("12570"),
        "NI_UPL":         Decimal("50270"),
        "NI_MAIN":        Decimal("0.06"),
        "NI_UPPER":       Decimal("0.02"),
        "SL": {
            1:              {"threshold": Decimal("26900"), "rate": Decimal("0.09")},
            2:              {"threshold": Decimal("29385"), "rate": Decimal("0.09")},
            4:              {"threshold": Decimal("33795"), "rate": Decimal("0.09")},
            5:              {"threshold": Decimal("25000"), "rate": Decimal("0.09")},
            "postgraduate": {"threshold": Decimal("21000"), "rate": Decimal("0.06")},
        },
    },
}

_CGT_CFG: dict = {
    # Post-Autumn Budget 2024 rates (18 % basic / 24 % higher, effective 30 Oct 2024)
    # AEA fixed at £3,000 from 2024/25 (Finance (No.2) Act 2023 s.8)
    "2025/26": {
        "AEA":         Decimal("3000"),
        "BASIC_RATE":  Decimal("0.18"),
        "HIGHER_RATE": Decimal("0.24"),
    },
    "2026/27": {
        "AEA":         Decimal("3000"),
        "BASIC_RATE":  Decimal("0.18"),
        "HIGHER_RATE": Decimal("0.24"),
    },
}

SUPPORTED_TAX_YEARS = sorted(_IT_CFG)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _personal_allowance(ani: Decimal, cfg: dict) -> Decimal:
    """Personal Allowance after taper.

    ITA 2007 s.35: £1 reduction per £2 ANI above £100,000; floor at £0.
    PA reaches zero at ANI ≥ £125,140.
    """
    pa = cfg["PA"]
    if ani <= cfg["PA_TAPER"]:
        return pa
    reduction = (ani - cfg["PA_TAPER"]) / Decimal("2")
    return max(ZERO, pa - reduction)


def _total_income_tax(income: Decimal, pension: Decimal, cfg: dict) -> Decimal:
    """Total income tax on *income* with gross pension contribution *pension*.

    Implements England/Wales/NI rates.  Scottish rates are out of scope.

    Pension RaS (Finance Act 2004 s.192 / PTM044100):
      - Gross contributions reduce ANI for PA taper.
      - Gross contributions extend the basic-rate band by the same amount.
    """
    if income <= ZERO:
        return ZERO

    ani  = max(ZERO, income - pension)
    pa   = _personal_allowance(ani, cfg)
    # Extended BRL cannot exceed ART (avoids negative higher-rate band widths)
    basic_band = min((cfg["BRL"] - cfg["PA"]) + pension, cfg["ART"])
    art  = cfg["ART"]
    taxable_income = max(ZERO, income - pa)

    tax = ZERO
    tax += min(taxable_income, basic_band) * cfg["BASIC"]
    if taxable_income > basic_band:
        tax += (min(taxable_income, art) - basic_band) * cfg["HIGHER"]
    if taxable_income > art:
        tax += (taxable_income - art) * cfg["ADDITIONAL"]

    return _money(tax)


def _total_class4_ni(profit: Decimal, cfg: dict) -> Decimal:
    """Total Class 4 NI on self-employed profit.

    SSCBA 1992 s.15: main rate on profits LPL→UPL, upper rate above UPL.
    """
    if profit <= cfg["NI_LPL"]:
        return ZERO
    main  = (min(profit, cfg["NI_UPL"]) - cfg["NI_LPL"]) * cfg["NI_MAIN"]
    upper = max(ZERO, profit - cfg["NI_UPL"]) * cfg["NI_UPPER"]
    return _money(main + upper)


def _total_student_loan(income: Decimal, plan: Any, cfg: dict) -> Decimal:
    """Total student / postgraduate loan repayment on income."""
    sl = cfg["SL"].get(plan)
    if not sl:
        return ZERO
    if income <= sl["threshold"]:
        return ZERO
    return _money((income - sl["threshold"]) * sl["rate"])


# ── Public API ────────────────────────────────────────────────────────────────

def ref_estimate(
    invoice_amount: Any,
    profile: dict,
    tax_year: str = "2026/27",
) -> dict:
    """Estimate the marginal tax cost of a single invoice.

    Mirrors the engine's ``estimate_incremental_liability`` interface so
    results can be compared field-for-field.

    Parameters
    ----------
    invoice_amount:
        Gross invoice value.
    profile:
        Dict with ``day_job_salary``, ``ytd_freelance_profit``,
        ``personal_pension_contributions``, ``student_loan_plans`` (or
        legacy ``student_loan_plan``).
    tax_year:
        "2025/26" or "2026/27".

    Notes
    -----
    Unlike the engine, this function computes the correct Personal Allowance
    at *both* start and end income points.  The engine uses end-state PA
    for the full range (EL-001).  Divergence between this reference and the
    engine in the PA-taper zone is therefore expected and documented.
    """
    cfg = _IT_CFG[tax_year]

    invoice    = _money(invoice_amount)
    employment = _money(profile.get("day_job_salary", 0))
    ytd        = _money(profile.get("ytd_freelance_profit", 0))
    pension    = _money(profile.get("personal_pension_contributions", 0))

    plans: list = profile.get("student_loan_plans") or []
    if not plans:
        legacy = profile.get("student_loan_plan")
        if legacy is not None:
            plans = [legacy]

    start_income = employment + ytd
    end_income   = start_income + invoice

    # ── Income tax (total-then-differential) ─────────────────────────────────
    it_end   = _total_income_tax(end_income,   pension, cfg)
    it_start = _total_income_tax(start_income, pension, cfg)
    income_tax = _money(it_end - it_start)

    # ── Class 4 NI (freelance profit only) ───────────────────────────────────
    start_profit = ytd
    end_profit   = ytd + invoice
    ni_end   = _total_class4_ni(end_profit,   cfg)
    ni_start = _total_class4_ni(start_profit, cfg)
    national_insurance = _money(ni_end - ni_start)

    # ── Student loan ──────────────────────────────────────────────────────────
    total_sl      = ZERO
    sl_breakdown  = []
    for plan in plans:
        sl_e = _total_student_loan(end_income,   plan, cfg)
        sl_s = _total_student_loan(start_income, plan, cfg)
        marginal = _money(sl_e - sl_s)
        sl_breakdown.append({"plan": plan, "amount": marginal})
        total_sl += marginal
    student_loan = _money(total_sl)

    total = _money(income_tax + national_insurance + student_loan)

    result: dict = {
        "tax_year":           tax_year,
        "rules_version":      f"ref-{tax_year}-v1.0",
        "income_tax":         income_tax,
        "national_insurance": national_insurance,
        "student_loan":       student_loan,
        "total":              total,
    }
    if len(sl_breakdown) > 1:
        result["student_loan_breakdown"] = sl_breakdown
    return result


def ref_cgt(
    disposals: list,
    *,
    taxable_income_before_gains: Any,
    brought_forward_losses: Any = 0,
    tax_already_paid: Any = 0,
    tax_year: str = "2026/27",
) -> dict:
    """Estimate CGT liability for a set of disposals.

    Parameters
    ----------
    disposals:
        List of dicts with keys ``proceeds``, ``allowable_cost``,
        and optionally ``gain_or_loss`` (pre-computed).
    taxable_income_before_gains:
        Total taxable income after PA, before adding gains — used to
        determine how much of the basic-rate band remains.
    brought_forward_losses, tax_already_paid:
        As per the engine's interface.
    tax_year:
        "2025/26" or "2026/27".
    """
    cgt_cfg = _CGT_CFG[tax_year]
    it_cfg  = _IT_CFG[tax_year]

    # Aggregate gains and losses from each disposal
    gains  = ZERO
    losses = ZERO
    for d in disposals:
        gol = _money(d.get("gain_or_loss",
                           _money(d["proceeds"]) - _money(d["allowable_cost"])))
        if gol >= ZERO:
            gains  += gol
        else:
            losses += abs(gol)

    total_gains      = _money(gains)
    current_losses   = _money(losses)
    total_losses     = _money(current_losses + _money(brought_forward_losses))
    net_gains        = _money(max(ZERO, total_gains - total_losses))
    taxable_gains    = _money(max(ZERO, net_gains - cgt_cfg["AEA"]))

    # Basic/higher split
    taxable_income   = _money(taxable_income_before_gains)
    basic_remaining  = _money(max(ZERO, it_cfg["BRL"] - taxable_income))
    basic_slice      = _money(min(taxable_gains, basic_remaining))
    higher_slice     = _money(max(ZERO, taxable_gains - basic_slice))

    estimated_tax    = _money(
        basic_slice  * cgt_cfg["BASIC_RATE"]
        + higher_slice * cgt_cfg["HIGHER_RATE"]
    )
    outstanding      = _money(max(ZERO, estimated_tax - _money(tax_already_paid)))

    return {
        "tax_year":            tax_year,
        "rules_version":       f"ref-cgt-{tax_year}-v1.0",
        "total_gains":         total_gains,
        "current_year_losses": current_losses,
        "annual_exempt_amount": cgt_cfg["AEA"],
        "taxable_gains":       taxable_gains,
        "estimated_cgt":       estimated_tax,
        "tax_already_paid":    _money(tax_already_paid),
        "outstanding_reserve": outstanding,
    }


def in_el001_zone(invoice_amount: Any, profile: dict) -> bool:
    """Return True if the engine's EL-001 limitation will cause a divergence.

    EL-001 occurs whenever the Personal Allowance at start_income differs
    from the PA at end_income.  This happens in TWO distinct cases:

    Case A — Invoice crosses the PA taper start:
        ANI_start < £100,000 < ANI_end
        The engine uses end-state PA (reduced) for the full range, so it
        taxes part of the PA-protected start income at the basic rate.

    Case B — Both start and end are within the taper zone:
        £100,000 < ANI_start < ANI_end ≤ £125,140
        The PA shrinks continuously through the taper zone.  The engine
        fixes end-state PA for the full range; the reference applies the
        correct (higher) PA at start_income.  The underestimate is
        (PA_start − PA_end) × basic_rate_at_start.

    Case C — Invoice crosses the PA elimination threshold (£125,140):
        Subset of Case A or B where ANI_end > £125,140.

    The single correct test for all cases: does the PA differ between
    start_income and end_income?
    """
    pension      = _money(profile.get("personal_pension_contributions", 0))
    employment   = _money(profile.get("day_job_salary", 0))
    ytd          = _money(profile.get("ytd_freelance_profit", 0))
    start_income = employment + ytd
    end_income   = start_income + _money(invoice_amount)
    ani_start    = max(ZERO, start_income - pension)
    ani_end      = max(ZERO, end_income   - pension)

    # Thresholds are frozen and identical across both supported years
    cfg = _IT_CFG["2026/27"]
    pa_start = _personal_allowance(ani_start, cfg)
    pa_end   = _personal_allowance(ani_end,   cfg)
    return pa_start != pa_end
