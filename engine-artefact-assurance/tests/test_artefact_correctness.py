"""
Current engine-artefact correctness tests.

These tests validate the *generated release artefact* (built from
``reserved/engines`` by ``scripts/build_engine_artefact.py``) against
independently derived expected values.  They are the "current engine artefact
suite" of the release gate and are deliberately separate from the root
production suite and from the historical ``reserved-engine-2.0.0`` bundle.

All expected values are derived from first principles against the 2026/27
rules; the derivations are preserved inline so a reviewer can re-derive each
figure without trusting the implementation under test.

2026/27 coordinates
-------------------
  Personal Allowance      £12,570 (reduced £1 per £2 of ANI above £100,000)
  Basic-rate band         £37,700  (taxable income)
  Additional-rate         £125,140 (ART)
  Rates                   20 % / 40 % / 45 %
  Class 4 NI              LPL £12,570 @ 6 %; UPL £50,270 @ 2 %
  Student Loan            annual Self Assessment, whole-pound floor per component
"""
from decimal import Decimal as D

import pytest

from reserved_engine.income_tax import (
    estimate_incremental_liability,
    UnsupportedStudentLoanPlanCombination,
)


def _profile(**overrides):
    base = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    }
    base.update(overrides)
    return base


# ── Provenance ────────────────────────────────────────────────────────────────

def test_artefact_records_provenance(engine):
    module, provenance = engine
    assert provenance["engine_version"] == module.ENGINE_VERSION
    assert provenance["engine_version"] == "4.0.0"
    assert provenance["rules_version"] == "uk-2026-27-v4"
    assert provenance["source_commit"]
    assert len(provenance["content_hash"]) == 64


# ── Personal Allowance taper and band coordinates ─────────────────────────────

def test_pa_full_below_taper():
    from reserved_engine.income_tax import _personal_allowance
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    assert _personal_allowance(D("99999"), cfg) == D("12570")
    assert _personal_allowance(D("100000"), cfg) == D("12570")


def test_pa_reduced_immediately_above_taper():
    # £100,001 → £0.50 reduction → £12,569.50 (half-pound values preserved).
    from reserved_engine.income_tax import _personal_allowance
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    assert _personal_allowance(D("100001"), cfg) == D("12569.5")


def test_pa_fully_withdrawn_at_art():
    # 12,570 × 2 = 25,140 above £100,000 → zero PA at £125,140.
    from reserved_engine.income_tax import _personal_allowance
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    assert _personal_allowance(D("125140"), cfg) == D("0")


def test_income_tax_at_full_pa_withdrawal():
    # ANI £125,140 → PA £0 → taxable £125,140.
    #   37,700 @ 20 % =  7,540.00
    #   87,440 @ 40 % = 34,976.00
    #   Total         = 42,516.00
    from reserved_engine.income_tax import _total_income_tax
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    assert _total_income_tax(D("125140"), D("0"), cfg) == D("42516.00")


def test_incremental_it_99k_to_104k():
    # 99,000  → PA 12,570, taxable 86,430 → 7,540 + 19,492 = 27,032.00
    # 104,000 → PA 10,570, taxable 93,430 → 7,540 + 22,292 = 29,832.00
    # Incremental = 2,800.00
    r = estimate_incremental_liability(
        "5000",
        _profile(day_job_salary="99000"),
        "2026/27",
    )
    assert r["income_tax"] == D("2800.00")


def test_marginal_it_100k_to_100001_is_60p():
    # £100,000 → IT 27,432.00; £100,001 → IT 27,432.60 (PA falls £0.50,
    # re-taxing £0.50 at 40 % and the £1 at 40 %).  Marginal = £0.60.
    r = estimate_incremental_liability(
        "1",
        _profile(day_job_salary="100000"),
        "2026/27",
    )
    assert r["income_tax"] == D("0.60")


# ── Pension interactions ──────────────────────────────────────────────────────

def test_pension_saving_in_taper_zone():
    # £110,000 income, £10,000 gross RaS pension (ANI £110k → £100k):
    #   before: PA 7,570 → taxable 102,430 → 7,540 + 25,892 = 33,432.00
    #   after:  PA 12,570 → taxable 97,430; band 47,700 → 9,540 + 19,892 = 29,432.00
    #   saving = 4,000.00
    from reserved_engine.income_tax import _total_income_tax
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    before = _total_income_tax(D("110000"), D("0"), cfg)
    after = _total_income_tax(D("110000"), D("10000"), cfg)
    assert before - after == D("4000.00")


def test_large_pension_extends_both_limits():
    # £200,000 income, £80,000 pension → ANI 120,000 → PA 2,570 → taxable 197,430.
    # PTM056120: a gross RAS contribution extends both the basic-rate limit and
    # the higher-rate limit by the gross amount (no cap).
    #   Extended basic-rate limit  = 37,700 + 80,000 = 117,700
    #   Extended higher-rate limit = 125,140 + 80,000 = 205,140
    #   117,700 @ 20 % = 23,540.00
    #    79,730 @ 40 % = 31,892.00
    #         0 @ 45 % =      0.00
    #   Total          = 55,432.00
    from reserved_engine.income_tax import _total_income_tax
    from reserved_engine.tax_config import get_config
    cfg = get_config("2026/27")
    assert _total_income_tax(D("200000"), D("80000"), cfg) == D("55432.00")


# ── Student Loan annual semantics ─────────────────────────────────────────────

def test_student_loan_whole_pound_floor():
    # Plan 2 threshold £29,385.  £29,386 → £1 above → 9 % = £0.09 → floor £0.
    r = estimate_incremental_liability("29386", _profile(student_loan_plans=[2]), "2026/27")
    assert r["student_loan"] == D("0.00")
    assert r["student_loan_basis"] == "annual_self_assessment_liability"


def test_student_loan_first_whole_pound():
    # £29,397 → £12 above threshold → 9 % = £1.08 → floor £1.00.
    r = estimate_incremental_liability("29397", _profile(student_loan_plans=[2]), "2026/27")
    assert r["student_loan"] == D("1.00")


def test_student_loan_simultaneous_plans_fail_closed():
    # Simultaneous undergraduate plans are outside the supported annual
    # Self Assessment scope and must fail closed, never leak a partial figure.
    with pytest.raises(UnsupportedStudentLoanPlanCombination):
        estimate_incremental_liability("40000", _profile(student_loan_plans=[1, 2]), "2026/27")


def test_student_loan_unknown_plan_fail_closed():
    # Unknown plan identifiers must not be silently ignored.
    with pytest.raises(UnsupportedStudentLoanPlanCombination):
        estimate_incremental_liability("40000", _profile(student_loan_plans=["mystery"]), "2026/27")
