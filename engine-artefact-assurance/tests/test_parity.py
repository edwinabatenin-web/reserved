"""
Production ↔ artefact parity gate.

Detects semantic drift between the maintained production engine
(``reserved.engines``) and the generated release artefact (``reserved_engine``
built from it).  Packaging parity is *not* independent tax validation: it
guards against the artefact silently diverging from production (e.g. a stale
build or an in-place edit), which is what let the historical bundle drift on
Student Loan behaviour.

The gate compares material public behaviour and version/configuration
identity without coupling to private implementation layout.
"""
from decimal import Decimal as D

import pytest

from reserved import engines as prod
from reserved_engine import (
    estimate_incremental_liability as art_estimate,
    build_allocation as art_allocate,
    estimate_cgt as art_cgt,
    CapitalDisposal as ArtDisposal,
)

P_ESTIMATE = prod.estimate_incremental_liability
P_ALLOCATE = prod.build_allocation
P_CGT = prod.estimate_cgt
P_DISPOSAL = prod.CapitalDisposal


def _normalise(value):
    """Convert Decimals/dataclasses/dicts to plain comparable structures."""
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        return _normalise(asdict(value))
    return value


def _call(fn, *args, **kwargs):
    """Return a canonical triple describing either the result or the exception."""
    try:
        return ("ok", _normalise(fn(*args, **kwargs)))
    except Exception as exc:  # noqa: BLE001 — we are intentionally comparing behaviour
        return ("raise", type(exc).__name__, str(exc))


def _profile(**overrides):
    base = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    }
    base.update(overrides)
    return base


# ── Version / configuration identity ─────────────────────────────────────────

def test_engine_version_identity():
    assert prod.ENGINE_VERSION == "3.0.0"
    assert prod.ENGINE_VERSION == __import__("reserved_engine").ENGINE_VERSION


def test_rules_version_identity():
    from reserved.engines.tax_config import RULES_VERSION as prod_rules
    from reserved_engine.tax_config import RULES_VERSION as art_rules
    assert prod_rules == art_rules


def test_income_tax_config_identity():
    from reserved.engines.tax_config import get_config as prod_cfg
    from reserved_engine.tax_config import get_config as art_cfg
    for year in ("2025/26", "2026/27"):
        assert prod_cfg(year) == art_cfg(year)


def test_supported_years_identity():
    from reserved.engines.tax_config import SUPPORTED_TAX_YEARS as prod_years
    from reserved_engine.tax_config import SUPPORTED_TAX_YEARS as art_years
    assert prod_years == art_years


# ── Incremental liability parity (IT / NI / Student Loan) ────────────────────

@pytest.mark.parametrize("invoice,tax_year,plans", [
    ("5000", "2026/27", None),
    ("5000", "2025/26", None),
    ("100", "2026/27", None),
    ("150000", "2026/27", None),
    ("29386", "2026/27", [2]),       # SL whole-pound floor → £0.00
    ("29397", "2026/27", [2]),       # SL whole-pound floor → £1.00
    ("26912", "2026/27", [1]),       # Plan 1 floor → £1.00
    ("5000", "2026/27", ["postgraduate"]),
    ("40000", "2026/27", [2, "postgraduate"]),  # single undergrad + PGL supported
])
def test_incremental_liability_parity(invoice, tax_year, plans):
    profile = _profile(student_loan_plans=plans) if plans else _profile()
    assert _call(P_ESTIMATE, invoice, profile, tax_year) == \
           _call(art_estimate, invoice, profile, tax_year)


@pytest.mark.parametrize("plans", [
    [1, 2],                    # simultaneous undergraduate plans
    ["mystery"],               # unknown plan identifier
    [1, "postgraduate", 2],    # multiple undergraduate plans + PGL
])
def test_student_loan_unsupported_states_fail_closed_identically(plans):
    profile = _profile(student_loan_plans=plans)
    prod_out = _call(P_ESTIMATE, "40000", profile, "2026/27")
    art_out = _call(art_estimate, "40000", profile, "2026/27")
    assert prod_out[0] == "raise", f"production did not fail closed for {plans}"
    assert prod_out == art_out


# ── Allocation parity ─────────────────────────────────────────────────────────

def test_allocation_parity():
    liability = {"income_tax": D("2000.00"), "national_insurance": D("600.00"),
                 "student_loan": D("0.00"), "total": D("2600.00")}
    assert _call(P_ALLOCATE, "10000.00", liability) == \
           _call(art_allocate, "10000.00", liability)


# ── Capital Gains parity ──────────────────────────────────────────────────────

def test_cgt_parity():
    def _run(disposal_cls, cgt_fn):
        disposals = [disposal_cls(
            asset_type="shares", description="x", disposal_date="2026-01-01",
            proceeds=D("20000"), allowable_cost=D("5000"),
        )]
        return cgt_fn(disposals, taxable_income_before_gains=D("30000"),
                      tax_year="2026/27")

    assert _call(lambda *a: _run(P_DISPOSAL, P_CGT)) == \
           _call(lambda *a: _run(ArtDisposal, art_cgt))


# ── Optimise parity ───────────────────────────────────────────────────────────

def test_optimise_parity():
    from reserved.engines.optimise import calculate_position as prod_pos
    from reserved_engine.optimise import calculate_position as art_pos
    for income, pension in [(D("110000"), D("0")), (D("70000"), D("0")),
                            (D("200000"), D("80000"))]:
        assert _call(prod_pos, income, pension) == _call(art_pos, income, pension)
