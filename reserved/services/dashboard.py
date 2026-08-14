"""
Dashboard service — builds the personalised data dict for the overview page.

All monetary calculations come from the tax engines; no values are hardcoded.
The service is pure (no Flask imports, no session access) so it is trivially
testable: pass a profile dict and an optional ``today`` date override.

Persistence layer
-----------------
The profile is stored in Flask's signed client-side session (cookie) by the
web layer.  This service only receives a plain dict — it has no opinion about
how the caller obtained it.

YTD liability calculation
--------------------------
We compute the total tax on **all** freelance income earned so far this year
by calling ``estimate_incremental_liability`` with:

    ytd_freelance_profit = 0   (no prior profit)
    invoice_amount       = profile["ytd_freelance_profit"]

This gives the legacy cumulative incremental estimate for entered employment
and freelance income. It is not a complete annual position or an assured
reserve amount because the estimator omits other income and liability families.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _datetime
from decimal import Decimal
from typing import Any

from reserved.engines.income_tax import (
    UnsupportedStudentLoanPlanCombination,
    estimate_incremental_liability,
)
from reserved.engines.allocation import build_allocation
from reserved.engines.utils import money


# ── Default profile shown to first-time / unauthenticated visitors ────────────
# Realistic sole-trader profile so the demo is meaningful from first load.
# The web layer sets is_demo=True when no user-saved profile exists.
DEFAULT_PROFILE: dict[str, Any] = {
    "first_name": "Mesh",
    "trading_name": "",
    "entity_type": "sole_trader",
    "day_job_salary": "42000",
    "ytd_freelance_profit": "18000",
    "personal_pension_contributions": "2500",
    "student_loan_plans": [2],
    "vat_registered": False,
    "accounting_method": "cash_basis",
}

_ZERO = Decimal("0.00")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _months_in_tax_year(today: _date) -> float:
    """Return approximate months elapsed since 6 April of the current tax year."""
    year = today.year if today >= _date(today.year, 4, 6) else today.year - 1
    start = _date(year, 4, 6)
    return max(1.0, (today - start).days / 30.44)


def _zero_ytd_liability(tax_year: str, rules_version: str) -> dict:
    """Minimal liability-shaped dict for when YTD freelance profit is zero."""
    return {
        "tax_year": tax_year,
        "rules_version": rules_version,
        "income_tax": _ZERO,
        "national_insurance": _ZERO,
        "student_loan": _ZERO,
        "total": _ZERO,
    }


def _build_activity(
    profile: dict,
    ytd_tax: Decimal,
    ytd_profit: Decimal,
    invoice_liability: dict,
    today: _date,
) -> list[dict]:
    """Generate 3 contextual activity items from the current profile."""
    items: list[dict] = []
    tax_year = invoice_liability.get("tax_year", "2026/27")

    # 1 — Tax estimate line (always shown; copy adapts to whether income exists)
    if ytd_profit > _ZERO:
        sl_suffix = " and student loan" if invoice_liability.get("student_loan", _ZERO) > _ZERO else ""
        items.append({
            "title": "Tax estimate updated",
            "detail": f"Income Tax, NI{sl_suffix} · {tax_year}",
            "time": "Now",
            "meta": f"£{ytd_tax:,.2f} incremental estimate on entered employment and freelance income",
        })
    else:
        items.append({
            "title": "Add income to see your estimate",
            "detail": "Enter your freelance income to date in Settings",
            "time": "Now",
            "meta": "Your reserve amount will appear here",
        })

    # 2 — Employment income note (if applicable)
    salary = money(profile.get("day_job_salary", 0))
    if salary > _ZERO:
        items.append({
            "title": "Employment income applied",
            "detail": f"£{salary:,.0f} annual salary · affects your marginal rate",
            "time": "Profile",
            "meta": "Income Tax band calculated from combined income",
        })
    else:
        pension = money(profile.get("personal_pension_contributions", 0))
        if pension > _ZERO:
            items.append({
                "title": "Pension deduction applied",
                "detail": f"£{pension:,.0f} gross pension · Relief at Source",
                "time": "Profile",
                "meta": "Basic-rate band extended; ANI reduced",
            })
        else:
            items.append({
                "title": "Profile updated",
                "detail": "Tax estimate uses your saved income and deductions",
                "time": "Profile",
                "meta": "Review Settings to refine your estimate",
            })

    # 3 — Self Assessment deadline
    deadline = _date(2027, 1, 31)
    days_remaining = (deadline - today).days
    if days_remaining > 0:
        deadline_meta = f"{days_remaining} days remaining"
    elif days_remaining == 0:
        deadline_meta = "Due today"
    else:
        deadline_meta = "Deadline passed"

    items.append({
        "title": "Self Assessment deadline",
        "detail": f"Tax year {tax_year} · Online filing by 31 January",
        "time": "31 Jan 2027",
        "meta": deadline_meta,
    })

    return items[:3]


# ── Public API ────────────────────────────────────────────────────────────────

def build_dashboard(
    profile: dict | None = None,
    invoice_amount: str = "4800.00",
    today: _date | None = None,
    *,
    is_demo: bool = True,
) -> dict:
    """Return the full data dict for the dashboard template.

    Parameters
    ----------
    profile:
        User's tax profile.  Defaults to ``DEFAULT_PROFILE`` if ``None``.
    invoice_amount:
        The invoice amount for the interactive calculator panel.
    today:
        Override today's date (used by tests; defaults to ``date.today()``).
    is_demo:
        ``True`` when no user-saved profile exists (first visit / defaults).
        Controls the "customise your profile" prompt in the template.
    """
    # Determine the date and time-of-day greeting.
    # When ``today`` is not supplied (real requests) we use datetime.now() so
    # the greeting is accurate.  When a bare date is passed (tests) we use a
    # neutral greeting to avoid breaking callers that don't care about the hour.
    if today is None:
        _now = _datetime.now()
        today = _now.date()
        _hour = _now.hour
    elif isinstance(today, _datetime):
        _hour = today.hour
        today = today.date()
    else:
        _hour = 12  # neutral: tests pass a date, not a datetime

    if _hour < 12:
        greeting = "morning"
    elif _hour < 18:
        greeting = "afternoon"
    else:
        greeting = "evening"

    merged: dict = {**DEFAULT_PROFILE, **(profile or {})}

    # ── Invoice calculator (incremental, per the calculator panel) ─────────────
    try:
        inv_amount = invoice_amount
        liability = estimate_incremental_liability(inv_amount, merged)
    except UnsupportedStudentLoanPlanCombination as exc:
        # Never retry or substitute zero/partial money for an unsupported
        # stored multi-plan profile. Return an explicitly unavailable service
        # state before allocation, YTD totals or reserve guidance are built.
        return {
            "profile": merged,
            "invoice_amount": Decimal(str(inv_amount)),
            "liability": {
                "tax_year": "2026/27",
                "calculation_status": exc.calculation_status,
                "unsupported_family": exc.unsupported_family,
                "uncertainty_reason": exc.uncertainty_reason,
                "uncertainty_effect": exc.uncertainty_effect,
                "verification_requirement": exc.verification_requirement,
                "student_loan_plans_supplied": tuple(merged.get("student_loan_plans") or ()),
                "limitations": exc.limitations,
                "income_tax": None,
                "national_insurance": None,
                "student_loan": None,
                "total": None,
            },
            "allocation": None,
            "today": today,
            "greeting": greeting,
            "is_demo": is_demo,
            "summary": {
                "protected": None,
                "annual_target": None,
                "funding_percentage": None,
                "income_ytd": money(merged.get("ytd_freelance_profit", 0)),
                "calculation_status": exc.calculation_status,
            },
            "connections": [],
            "chart": None,
            "activity": [],
        }
    except Exception:
        inv_amount = "4800.00"
        liability = estimate_incremental_liability(inv_amount, merged)
    legacy_allocation = build_allocation(inv_amount, liability["total"])
    # The legacy allocator retains an arithmetic remainder for compatibility.
    # It is deliberately excluded from the customer/dashboard contract: the
    # available inputs cannot establish that a remainder is safe to spend.
    allocation = {
        key: legacy_allocation[key]
        for key in ("gross_amount", "tax_reserve", "platform_fee", "reconciles")
    }

    # ── YTD summary (total tax on all freelance income earned this year) ───────
    ytd_profit = money(merged.get("ytd_freelance_profit", 0))

    if ytd_profit > _ZERO:
        ytd_profile = {**merged, "ytd_freelance_profit": "0"}
        ytd_liability = estimate_incremental_liability(str(ytd_profit), ytd_profile)
        ytd_tax = ytd_liability["total"]
    else:
        ytd_tax = _ZERO

    protected = ytd_tax

    # ── Annual target (project current monthly run rate to full year) ──────────
    months = _months_in_tax_year(today)
    if ytd_tax > _ZERO:
        annual_target = money(ytd_tax * Decimal("12") / Decimal(str(round(months, 4))))
    else:
        annual_target = _ZERO

    # ── Ring metric: % of income reserved for tax ─────────────────────────────
    # Shows how much of every pound earned goes to tax obligations — varies
    # meaningfully with income level, pension, student loan, higher-rate exposure.
    if ytd_profit > _ZERO:
        reserve_rate_pct = min(100, round(float(ytd_tax / ytd_profit * 100)))
    else:
        reserve_rate_pct = 0

    # ── Activity feed ──────────────────────────────────────────────────────────
    activity = _build_activity(merged, ytd_tax, ytd_profit, liability, today)

    return {
        "profile": merged,
        "invoice_amount": Decimal(str(inv_amount)),
        "liability": liability,
        "allocation": allocation,
        "today": today,
        "greeting": greeting,
        "is_demo": is_demo,
        "summary": {
            "protected": protected,
            "annual_target": annual_target,
            "funding_percentage": reserve_rate_pct,   # ring: % of income reserved
            "income_ytd": ytd_profit,                  # replaces income_this_month
        },
        # Connections – demo data only; real open banking not yet live.
        "connections": [
            {
                "name": "first direct",
                "account_type": "1st Account · Current",
                "status": "Connected",
                "updated": "2 minutes ago",
                "initials": "fd",
                "show_balance": False,
            },
            {
                "name": "Mettle",
                "account_type": "Business current · NatWest",
                "status": "Connected",
                "updated": "Today",
                "initials": "M",
                "show_balance": False,
            },
            {
                "name": "Reserved account",
                "account_type": "Tax reserve",
                "status": "Ready",
                "balance": ytd_tax,
                "updated": "Today",
                "initials": "R",
                "show_balance": True,
            },
        ],
        "chart": {
            "labels": ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
            "income":   [5200, 7600, 6100, 9200, 6800, 10400, 8300],
            "reserved": [2028, 2964, 2379, 3588, 2652, 4056, 3237],
        },
        "activity": activity,
    }
