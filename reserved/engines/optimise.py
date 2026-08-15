"""
Tax optimisation engine — Reserved™.

Identifies material Adjusted Net Income (ANI) threshold interactions and
models counterfactual pension-contribution scenarios.

This is a *factual planning tool* — outputs are illustrative estimates
produced by the tax engine.  Use the wording "If your circumstances changed
in this way, Reserved estimates…" rather than "you should".

Supported opportunities (2026/27, England / Wales / Northern Ireland):
──────────────────────────────────────────────────────────────────────
  PA_TAPER  Personal Allowance taper, ANI £100,000 – £125,140.
            Effective marginal rate up to 60 % in this band.
            Source: ITEPA 2003 s.35; Finance (No.2) Act 2015.

  HICBC     High Income Child Benefit Charge, ANI £60,000 – £80,000
            (revised threshold from April 2024: Finance Act 2024).
            Source: Finance Act 2012 ss.681A-681H; HMRC CH2300C.

Explicit out of scope in this version:
──────────────────────────────────────
  •  Scottish income tax (different bands — excluded per engine contract)
  •  Salary sacrifice — never assumed available; must be confirmed with employer
  •  Gift Aid (similar ANI interaction — planned for a future version)
  •  Dividend income / savings income (order of priority differs)
  •  Pension Annual Allowance / tapered AA / MPAA (noted as hard constraints)
  •  Carry-forward of unused annual allowances (not modelled)
  •  Marriage Allowance, Blind Person's Allowance, other reliefs

HMRC references
───────────────
  HMRC EIM05100   — Personal Allowance reduction
  HMRC CH2300C    — High Income Child Benefit Charge
  Finance Act 2012 s.681B — HICBC charge formula
  Finance (No.2) Act 2015 — PA taper threshold
  HMRC PTM056120  — Pension Relief at Source (basic and higher rate limits)

Change history
──────────────
v1.0.0  Initial release.  PA_TAPER and HICBC opportunities; RaS pension
        scenario modelling.  No salary sacrifice; no Gift Aid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from decimal import Decimal, ROUND_FLOOR
from typing import Literal

from .income_tax import _personal_allowance, _total_income_tax
from .tax_config import TAX_YEAR, get_config
from .utils import money

_CURRENT_CFG = get_config(TAX_YEAR)
_CB_WEEKLY_ELDEST = _CURRENT_CFG["CHILD_BENEFIT"]["eldest_weekly"]
_CB_WEEKLY_ADDITIONAL = _CURRENT_CFG["CHILD_BENEFIT"]["additional_weekly"]
_CB_WEEKS_PER_YEAR = _CURRENT_CFG["CHILD_BENEFIT"]["weeks_per_year"]

_HICBC_LOWER = _CURRENT_CFG["HICBC"]["lower_threshold"]
_HICBC_UPPER = _CURRENT_CFG["HICBC"]["upper_threshold"]

# PA taper (frozen by Finance Act 2022 through at least 2027/28)
_PA_TAPER_START = Decimal("100000")
_PA_TAPER_END   = Decimal("125140")

# Standard Pension Annual Allowance 2026/27
_PENSION_ANNUAL_ALLOWANCE = Decimal("60000")

# Proximity window for "incomplete" HICBC warning (either side of £60k)
_HICBC_PROXIMITY = Decimal("20000")


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Position:
    """A projected full-year tax position."""
    projected_income:      Decimal
    pension:               Decimal
    adjusted_net_income:   Decimal
    personal_allowance:    Decimal
    estimated_income_tax:  Decimal
    hicbc:                 Decimal = Decimal("0")
    annual_cb:             Decimal = Decimal("0")
    tax_year:              str = TAX_YEAR

    def total_charges(self) -> Decimal:
        """Income tax + HICBC (total direct liability, excludes pension contributions)."""
        return money(self.estimated_income_tax + self.hicbc)


@dataclass
class ScenarioResult:
    """Before-versus-scenario comparison for a modelled pension contribution."""
    opportunity_id:    str
    additional_pension: Decimal   # gross RaS contribution being modelled
    total_pension:      Decimal   # current + additional

    before: Position
    after:  Position

    # Direct financial effects — money not paid to HMRC / charges
    it_reduction:     Decimal   # income-tax saving
    hicbc_reduction:  Decimal   # HICBC saving
    total_benefit:    Decimal   # it_reduction + hicbc_reduction (≥ 0)

    # Clarification: basic-rate relief HMRC adds to the pension pot.
    # This is NOT a tax saving — it is 20 % of the gross pension added by HMRC
    # to the pension fund (not the user's bank).  Shown separately so figures
    # are never double-counted with the income-tax saving above.
    basic_rate_relief_to_pension: Decimal

    caveats: list[str] = field(default_factory=list)


@dataclass
class Opportunity:
    """A detected tax-planning opportunity."""
    id:     str   # "PA_TAPER" | "HICBC"
    title:  str
    trigger: str  # Factual explanation of why this surfaced
    status: Literal["available", "incomplete", "unavailable"]

    current_position: Position | None = None

    # Pension amount hints for scenario suggestions
    pension_to_clear_fully:  Decimal | None = None
    pension_to_clear_capped: Decimal | None = None   # min(above, £60k AA)

    missing_data:    list[str] = field(default_factory=list)
    constraints:     list[str] = field(default_factory=list)
    what_to_confirm: list[str] = field(default_factory=list)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _annual_cb_from_profile(profile: dict) -> Decimal:
    """Resolve annual Child Benefit amount from the profile dict.

    Priority:
      1. ``child_benefit_annual`` — explicit annual total entered by user.
      2. ``child_benefit_children`` × standard 2026/27 weekly rates × 52.
      3. Zero (no CB data → HICBC opportunity hidden or incomplete).
    """
    override = profile.get("child_benefit_annual")
    if override is not None:
        try:
            val = money(override)
            if val > Decimal("0"):
                return val
        except Exception:
            pass

    n = int(profile.get("child_benefit_children") or 0)
    if n <= 0:
        return Decimal("0")
    eldest     = _CB_WEEKLY_ELDEST     * _CB_WEEKS_PER_YEAR
    additional = _CB_WEEKLY_ADDITIONAL * _CB_WEEKS_PER_YEAR * Decimal(str(max(0, n - 1)))
    return money(eldest + additional)


def _resolve_pension(profile: dict) -> Decimal:
    """Extract gross RaS pension from profile, tolerating field-name variants."""
    for key in ("personal_pension_contributions", "pension_contribution", "pension"):
        val = profile.get(key)
        if val is not None:
            try:
                d = money(val)
                if d >= Decimal("0"):
                    return d
            except Exception:
                pass
    return Decimal("0")


def _resolve_annual_income(profile: dict, today: _date | None = None) -> Decimal:
    """Best-effort full-year income projection from profile fields.

    Employment income (``day_job_salary``) is already annual.
    Freelance income is resolved in this order:
      1. ``income_estimate`` — explicit annual target set in profile.
      2. ``ytd_freelance_profit`` projected to 12 months via elapsed months.
    """
    if today is None:
        today = _date.today()

    salary = Decimal("0")
    raw_salary = profile.get("day_job_salary")
    if raw_salary is not None:
        try:
            salary = money(raw_salary)
        except Exception:
            pass

    # Prefer an explicit annual estimate
    annual_fl = profile.get("income_estimate")
    if annual_fl is not None:
        try:
            v = money(annual_fl)
            if v > Decimal("0"):
                return money(salary + v)
        except Exception:
            pass

    # Project from YTD figure
    ytd = Decimal("0")
    raw_ytd = profile.get("ytd_freelance_profit")
    if raw_ytd is not None:
        try:
            ytd = money(raw_ytd)
        except Exception:
            pass

    if ytd > Decimal("0"):
        yr    = today.year if today >= _date(today.year, 4, 6) else today.year - 1
        start = _date(yr, 4, 6)
        months = max(Decimal("1"), Decimal(str(round((today - start).days / 30.44, 4))))
        projected_fl = money(ytd * Decimal("12") / months)
        return money(salary + projected_fl)

    return salary


def _hicbc(ani: Decimal, annual_cb: Decimal) -> Decimal:
    """High Income Child Benefit Charge.

    Formula (Finance Act 2012 s.681B, revised April 2024):
        charge_pct = floor(min(100, max(0, (ANI − 60,000) / 200)))
        relevant_benefit = floor(annual_cb) to whole pounds
        HICBC = floor(relevant_benefit × charge_pct / 100) to whole pounds

    Returns £0 if ANI ≤ £60,000 or if no Child Benefit is received.
    """
    if ani <= _HICBC_LOWER or annual_cb <= Decimal("0"):
        return Decimal("0")
    # ITEPA 2003 s681C(3) requires a non-whole appropriate percentage and a
    # non-whole charge to be rounded down.  Fractional £200 steps must not be
    # treated as fractional percentage points.
    charge_pct = min(
        Decimal("100"),
        ((ani - _HICBC_LOWER) / Decimal("200")).to_integral_value(
            rounding=ROUND_FLOOR
        ),
    )
    relevant_benefit = annual_cb.to_integral_value(rounding=ROUND_FLOOR)
    charge = (relevant_benefit * charge_pct / Decimal("100")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return money(charge)


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_position(
    projected_income: Decimal,
    pension: Decimal,
    annual_cb: Decimal = Decimal("0"),
    tax_year: str = TAX_YEAR,
) -> Position:
    """Calculate the full projected annual tax position.

    Pure function — no side effects.  Used for both current and scenario
    positions so before/after comparisons are internally consistent.

    Parameters
    ----------
    projected_income:
        Full-year combined income (employment + projected freelance).
    pension:
        Gross Relief-at-Source pension contributions for the tax year.
    annual_cb:
        Annual Child Benefit amount received.  Pass ``Decimal("0")``
        if Child Benefit is not received.
    tax_year:
        Must be in ``SUPPORTED_TAX_YEARS``.
    """
    cfg = get_config(tax_year)
    ani = max(Decimal("0"), projected_income - pension)
    pa  = _personal_allowance(ani, cfg)
    it  = _total_income_tax(projected_income, pension, cfg)
    hb  = _hicbc(ani, annual_cb)
    return Position(
        projected_income     = projected_income,
        pension              = pension,
        adjusted_net_income  = ani,
        personal_allowance   = pa,
        estimated_income_tax = it,
        hicbc                = hb,
        annual_cb            = annual_cb,
        tax_year             = tax_year,
    )


def model_pension_scenario(
    projected_income: Decimal,
    current_pension: Decimal,
    additional_pension: Decimal,
    opportunity_id: str,
    annual_cb: Decimal = Decimal("0"),
    tax_year: str = TAX_YEAR,
) -> ScenarioResult:
    """Model the effect of an additional gross pension contribution.

    The ``additional_pension`` is a gross Relief-at-Source amount:
    net paid ÷ 0.80 = gross.  Example: pay £8,000 net → £10,000 gross.

    The ``total_benefit`` in the result is the estimated reduction in income
    tax **and** HICBC only.  This is money that does not go to HMRC / charges.

    The ``basic_rate_relief_to_pension`` is shown separately: it is the 20 %
    that HMRC adds to the pension fund (not the user's bank account).  It must
    never be added to ``total_benefit`` — doing so would double-count it.

    Raises
    ------
    ValueError
        If ``additional_pension`` is negative.
    """
    if additional_pension < Decimal("0"):
        raise ValueError("additional_pension must not be negative.")

    before = calculate_position(projected_income, current_pension,                       annual_cb, tax_year)
    after  = calculate_position(projected_income, current_pension + additional_pension,  annual_cb, tax_year)

    it_reduction    = money(max(Decimal("0"), before.estimated_income_tax - after.estimated_income_tax))
    hicbc_reduction = money(max(Decimal("0"), before.hicbc               - after.hicbc))
    total_benefit   = money(it_reduction + hicbc_reduction)

    # HMRC basic-rate top-up added to the pension pot (20 % of gross).
    # Surfaced for transparency — NOT a tax saving and NOT included in total_benefit.
    basic_rate_relief = money(additional_pension * Decimal("0.20"))

    caveats = [
        f"Pension Annual Allowance: the standard limit for {tax_year} is "
        f"£{_PENSION_ANNUAL_ALLOWANCE:,.0f} gross across all contributions "
        f"(employer + personal). Verify your remaining allowance before contributing.",
        "Tapered Annual Allowance applies where your adjusted income exceeds £260,000, "
        "potentially reducing the allowance to as little as £10,000.",
        "Money Purchase Annual Allowance (MPAA, £10,000) applies if you have "
        "flexibly accessed a defined-contribution pension.",
        "Carry-forward of unused allowances from the three prior tax years is not "
        "modelled here. It can increase your effective ceiling.",
        "Salary sacrifice (employer pension) is a separate mechanism — not modelled "
        "and must not be assumed available without employer confirmation.",
        "These figures are illustrative projections only — not financial advice. "
        "Reserved estimates the above if your circumstances changed in this way.",
    ]

    return ScenarioResult(
        opportunity_id               = opportunity_id,
        additional_pension           = additional_pension,
        total_pension                = money(current_pension + additional_pension),
        before                       = before,
        after                        = after,
        it_reduction                 = it_reduction,
        hicbc_reduction              = hicbc_reduction,
        total_benefit                = total_benefit,
        basic_rate_relief_to_pension = basic_rate_relief,
        caveats                      = caveats,
    )


def assess_opportunities(
    profile: dict,
    projected_income_override: Decimal | None = None,
    tax_year: str = TAX_YEAR,
    today: _date | None = None,
) -> tuple[Position, list[Opportunity]]:
    """Assess the current projected position and detect applicable opportunities.

    Parameters
    ----------
    profile:
        The user's profile dict (from session or DB).
    projected_income_override:
        If supplied, use this as the annual income rather than projecting
        from the profile.  Used by the UI when the user adjusts the income
        projection manually.
    tax_year:
        Tax year string (default: ``"2026/27"``).
    today:
        Override today's date (used by tests).

    Returns
    -------
    (current_position, opportunities)
        ``current_position`` — the calculated current Position.
        ``opportunities``    — list of Opportunity, ordered by materiality.
    """
    pension   = _resolve_pension(profile)
    annual_cb = _annual_cb_from_profile(profile)

    if projected_income_override is not None:
        projected_income = projected_income_override
    else:
        projected_income = _resolve_annual_income(profile, today)

    current = calculate_position(projected_income, pension, annual_cb, tax_year)
    ani     = current.adjusted_net_income
    opportunities: list[Opportunity] = []

    # ── PA_TAPER ──────────────────────────────────────────────────────────────
    # At ANI = £100,000 exactly, PA is still full (£12,570) — taper has not
    # started.  Use strict > so the opportunity only appears when the PA is
    # actually being reduced.
    if ani > _PA_TAPER_START:
        pension_to_clear = max(Decimal("0"), projected_income - _PA_TAPER_START - pension)
        pension_capped   = min(pension_to_clear, _PENSION_ANNUAL_ALLOWANCE)

        opportunities.append(Opportunity(
            id    = "PA_TAPER",
            title = "Personal Allowance taper",
            trigger = (
                f"Your projected Adjusted Net Income is £{ani:,.0f}, above the "
                f"£{_PA_TAPER_START:,.0f} threshold where the Personal Allowance "
                f"starts to reduce. Every £2 of ANI above this point costs £1 of "
                f"Personal Allowance, creating an effective marginal rate of up to "
                f"60 % in this band. Your current Personal Allowance is estimated "
                f"at £{current.personal_allowance:,.0f}."
            ),
            status                  = "available",
            current_position        = current,
            pension_to_clear_fully  = pension_to_clear,
            pension_to_clear_capped = pension_capped,
            constraints = [
                f"Standard Pension Annual Allowance: £{_PENSION_ANNUAL_ALLOWANCE:,.0f} gross ({tax_year}).",
                "Tapered Annual Allowance may apply if adjusted income exceeds £260,000.",
                "MPAA (£10,000) applies if you have flexibly accessed a pension.",
                "Carry-forward of unused prior-year allowances is not modelled.",
            ],
            what_to_confirm = [
                f"Your remaining Annual Allowance for {tax_year} (from your pension provider).",
                "Whether carry-forward allowance is available from prior tax years.",
                "Whether salary sacrifice is available from your employer.",
                "The contribution basis: Relief at Source or net-pay arrangement.",
            ],
        ))

    # ── HICBC (available) ─────────────────────────────────────────────────────
    # At ANI = £60,000 exactly the charge formula returns £0 — use strict >
    # so the opportunity only appears when a real charge is actually present.
    if annual_cb > Decimal("0") and ani > _HICBC_LOWER:
        pension_to_clear = max(Decimal("0"), projected_income - _HICBC_LOWER - pension)
        pension_capped   = min(pension_to_clear, _PENSION_ANNUAL_ALLOWANCE)

        opportunities.append(Opportunity(
            id    = "HICBC",
            title = "High Income Child Benefit Charge",
            trigger = (
                f"Your projected ANI is £{ani:,.0f}, above the "
                f"£{_HICBC_LOWER:,.0f} HICBC threshold. Based on the Child Benefit "
                f"information in your profile, Reserved estimates a full-year charge "
                f"of £{current.hicbc:,.2f}. A pension contribution that reduces ANI "
                f"to below £{_HICBC_LOWER:,.0f} would eliminate the charge entirely."
            ),
            status                  = "available",
            current_position        = current,
            pension_to_clear_fully  = pension_to_clear,
            pension_to_clear_capped = pension_capped,
            constraints = [
                "HICBC applies to the person in the household with the higher ANI, "
                "regardless of which partner claims the Child Benefit.",
                f"Standard Pension Annual Allowance: £{_PENSION_ANNUAL_ALLOWANCE:,.0f} gross ({tax_year}).",
                "The charge applies proportionally — partial years above the threshold "
                "result in a proportional charge.",
            ],
            what_to_confirm = [
                "Confirm you (not your partner) have the higher ANI for the full tax year.",
                "Verify your actual annual Child Benefit award against your HMRC letter — "
                "rates change each April.",
                "Check your remaining Annual Allowance before contributing.",
            ],
        ))

    # ── HICBC (incomplete — near threshold but no CB data) ───────────────────
    elif annual_cb == Decimal("0") and abs(ani - _HICBC_LOWER) <= _HICBC_PROXIMITY:
        opportunities.append(Opportunity(
            id    = "HICBC",
            title = "High Income Child Benefit Charge",
            trigger = (
                f"Your projected ANI (£{ani:,.0f}) is near the "
                f"£{_HICBC_LOWER:,.0f} HICBC threshold. If you or your partner "
                f"receives Child Benefit and your ANI exceeds £60,000, a charge "
                f"will apply."
            ),
            status           = "incomplete",
            current_position = current,
            missing_data = [
                "Add your Child Benefit information in Settings → Income & tax "
                "(number of children, or the annual award total) to see whether "
                "this opportunity is relevant and to model a scenario."
            ],
            constraints = [
                "HICBC applies to the person in the household with the higher ANI.",
            ],
        ))

    return current, opportunities
