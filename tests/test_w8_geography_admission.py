"""W8-S3 geography-admission boundary tests.

These tests pin the enforced fail-closed geography boundary at the annual
position entry point. They are adversarial: supported values calculate
normally, the five W8-S2 silent-ignore cases now fail closed, and hostile,
malformed or contradictory geography facts fail without leaking rejected
values.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from reserved.engines.income_tax import estimate_incremental_liability
from reserved.engines.integrated_annual_position import (
    calculate_annual_position,
)

# A complete, explicitly closed Blind Person's Allowance fact group so the
# annual position is a clean, calculated baseline rather than fact-incomplete.
BPA = {
    "blind_persons_allowance_entitled": False,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}

BASE_FACTS = {"employment_income": "30000", **BPA}

GEOGRAPHY_ALIASES = ("jurisdiction", "country", "country_code", "territory", "tax_regime")

SUPPORTED_NATIONS = ("England", "Wales", "Northern Ireland")
SUPPORTED_CODES = ("GB-ENG", "GB-WLS", "GB-NIR")


class _GeographyString(str):
    """A str subclass used to prove values are validated as their string content."""


# ── 1. Supported nation names/codes calculate normally ──────────────────────

@pytest.mark.parametrize("value", SUPPORTED_NATIONS + SUPPORTED_CODES)
def test_supported_geography_calculates_normally(value):
    result = calculate_annual_position({**BASE_FACTS, "country": value})
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")


@pytest.mark.parametrize("field", GEOGRAPHY_ALIASES)
def test_each_geography_alias_accepts_a_supported_nation(field):
    result = calculate_annual_position({**BASE_FACTS, field: "England"})
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")


# ── 2. The five W8-S2 silent-ignore cases now fail closed ───────────────────

@pytest.mark.parametrize(
    "field, value",
    [
        ("jurisdiction", "Scotland"),
        ("country", "Scotland"),
        ("country_code", "GB-SCT"),
        ("territory", "Scotland"),
        ("tax_regime", "Scottish"),
    ],
)
def test_w8_s2_silent_ignore_cases_now_fail_closed(field, value):
    with pytest.raises(ValueError):
        calculate_annual_position({**BASE_FACTS, field: value})


# ── 3. Unsupported and unknown jurisdictions fail closed ────────────────────

@pytest.mark.parametrize(
    "value",
    [
        "Scotland",
        "Scottish",
        "scottish",
        "SCOTLAND",
        "GB-SCT",
        "gb-sct",
        "Ireland",
        "Republic of Ireland",
        "Republic Of Ireland",
        "IE",
        "France",
        "Germany",
        "United States",
        "US",
        "Channel Islands",
        "Isle of Man",
    ],
)
def test_unsupported_or_unknown_jurisdiction_fails_closed(value):
    with pytest.raises(ValueError):
        calculate_annual_position({**BASE_FACTS, "country": value})


# ── 4. Umbrella / ambiguous labels are never positive evidence ──────────────

@pytest.mark.parametrize(
    "value",
    ["UK", "GB", "United Kingdom", "uk", "gb", "United Kingdom (UK)"],
)
def test_umbrella_labels_are_not_positive_supported_evidence(value):
    with pytest.raises(ValueError):
        calculate_annual_position({**BASE_FACTS, "country": value})


# ── 5. Multiple geography facts must resolve to the same nation ─────────────

def test_mixed_supported_aliases_that_agree_pass():
    result = calculate_annual_position(
        {
            **BASE_FACTS,
            "country": "England",
            "country_code": "GB-ENG",
            "jurisdiction": "england",
        }
    )
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")


@pytest.mark.parametrize(
    "facts",
    [
        {"country": "England", "country_code": "GB-WLS"},
        {"country": "Wales", "territory": "England"},
        {"jurisdiction": "Northern Ireland", "country": "England"},
    ],
)
def test_cross_nation_contradiction_fails_closed(facts):
    with pytest.raises(ValueError):
        calculate_annual_position({**BASE_FACTS, **facts})


def test_supported_unsupported_contradiction_fails_closed():
    with pytest.raises(ValueError):
        calculate_annual_position(
            {**BASE_FACTS, "country": "England", "territory": "Scotland"}
        )


# ── 6. Hostile / malformed values fail without leaking the rejected value ───

@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        1,
        0,
        123,
        -1,
        3.5,
        ["England"],
        {"country": "England"},
        ("England",),
        "",
        "   ",
        "\t\n ",
    ],
)
def test_hostile_geography_fails_without_value_leakage(value):
    with pytest.raises(ValueError) as exc:
        calculate_annual_position({**BASE_FACTS, "country": value})
    assert repr(value) not in str(exc.value)
    assert "Unsupported geography" in str(exc.value)


def test_string_subclass_is_validated_as_its_string_content():
    assert (
        calculate_annual_position({**BASE_FACTS, "country": _GeographyString("England")}).calculation_status
        == "calculated"
    )
    with pytest.raises(ValueError) as exc:
        calculate_annual_position({**BASE_FACTS, "country": _GeographyString("Scotland")})
    assert "Scotland" not in str(exc.value)


# ── 7. Validation happens before arithmetic / result construction ───────────

def test_geography_validates_before_later_fact_validation():
    # ``employment_income`` as a boolean would fail later in arithmetic; the
    # geography boundary must fail first, proving it runs at the entry point.
    with pytest.raises(ValueError, match="Unsupported geography"):
        calculate_annual_position({"employment_income": True, "country": "Scotland"})


# ── 8. Missing geography preserves internal compatibility and claims nothing ─

def test_missing_geography_preserves_internal_compatibility_and_claims_nothing():
    result = calculate_annual_position(BASE_FACTS)
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")
    # Absence is not represented as a supported-jurisdiction claim.
    assert "country" not in result.__dataclass_fields__
    assert not any(
        "geography" in lim or "jurisdiction" in lim for lim in result.limitations
    )


def test_none_geography_fact_is_treated_as_absent():
    result = calculate_annual_position({**BASE_FACTS, "country": None})
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")


# ── 9. Plan 4 remains a student-loan plan, not geography evidence ───────────

def test_plan_4_remains_accepted_by_student_loan_boundary():
    result = estimate_incremental_liability("1000", {"student_loan_plans": [4]})
    assert any(item["plan"] == 4 for item in result["student_loan_breakdown"])


def test_student_loan_plan_facts_are_not_misread_as_geography():
    result = calculate_annual_position(
        {**BASE_FACTS, "student_loan_plans": [4], "plan": "4"}
    )
    assert result.calculation_status == "calculated"
    assert result.total_liability == Decimal("3486.00")
