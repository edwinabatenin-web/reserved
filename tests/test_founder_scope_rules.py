from decimal import Decimal

import pytest

from reserved.engines.income_tax import (
    UnsupportedStudentLoanPlanCombination,
    estimate_incremental_liability,
)
from reserved.engines.tax_config import get_config


def test_2026_27_dividend_rates_are_current():
    cfg = get_config("2026/27")
    assert cfg["DIVIDEND_ALLOWANCE"] == Decimal("500")
    assert cfg["DIVIDEND_TAX_RATES"] == {
        "basic": Decimal("0.1075"),
        "higher": Decimal("0.3575"),
        "additional": Decimal("0.3935"),
    }


def test_2026_27_child_benefit_rates_are_current():
    cfg = get_config("2026/27")
    assert cfg["CHILD_BENEFIT"]["eldest_weekly"] == Decimal("27.05")
    assert cfg["CHILD_BENEFIT"]["additional_weekly"] == Decimal("17.90")


def test_multiple_undergraduate_plans_fail_closed_without_monetary_result():
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": [1, 2],
    }
    with pytest.raises(UnsupportedStudentLoanPlanCombination) as caught:
        estimate_incremental_liability("5000", profile)
    assert caught.value.calculation_status == "unsupported_rule"
    assert caught.value.uncertainty_effect == "not_determinable"
    assert "Verify the applicable annual Self Assessment plan treatment" in caught.value.verification_requirement
    assert "no_student_loan_or_total_monetary_result_available" in caught.value.limitations


def test_multiple_undergraduate_plus_postgraduate_also_fails_closed():
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": [1, 2, "postgraduate"],
    }
    with pytest.raises(UnsupportedStudentLoanPlanCombination):
        estimate_incremental_liability("5000", profile)


@pytest.mark.parametrize("plans", [["mystery"], [2, "mystery"]])
def test_unknown_plan_fails_closed_without_partial_monetary_result(plans):
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": plans,
    }
    with pytest.raises(UnsupportedStudentLoanPlanCombination) as caught:
        estimate_incremental_liability("5000", profile)
    assert caught.value.uncertainty_effect == "not_determinable"
    assert "qualified tax adviser" in caught.value.verification_requirement


def test_single_undergraduate_and_postgraduate_remain_supported():
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": [2, "postgraduate"],
    }
    result = estimate_incremental_liability("5000", profile)
    assert result["student_loan"] == Decimal("750.00")
    assert result["student_loan_breakdown"] == [
        {"plan": 2, "amount": Decimal("450.00")},
        {"plan": "postgraduate", "amount": Decimal("300.00")},
    ]
