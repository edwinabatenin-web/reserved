"""Synthetic MTD readiness tests."""

from decimal import Decimal

from reserved.engines.mtd_readiness import (
    IncomeKind,
    IncomeSource,
    MtdStatus,
    assess_mtd_readiness,
)


def source(source_id, kind, gross, *, business_id=None, complete=True):
    return IncomeSource(source_id, kind, gross, business_id, complete)


def test_paye_dividends_savings_and_gains_are_not_qualifying_income():
    result = assess_mtd_readiness([
        source("job", IncomeKind.PAYE_EMPLOYMENT, "80000"),
        source("dividends", IncomeKind.DIVIDENDS, "10000"),
        source("interest", IncomeKind.SAVINGS_INTEREST, "5000"),
        source("gain", IncomeKind.CAPITAL_GAINS, "50000"),
    ], assessment_tax_year="2025-26", registered_for_self_assessment=True,
       exemption_applies=False)
    assert result.qualifying_income == Decimal("0.00")
    assert result.status is MtdStatus.NOT_CURRENTLY_IN_SCOPE
    assert result.excluded_source_ids == ("job", "dividends", "interest", "gain")


def test_multiple_businesses_and_property_sources_remain_separate():
    result = assess_mtd_readiness([
        source("trade-a", IncomeKind.SOLE_TRADE, "12000", business_id="business-a"),
        source("trade-b", IncomeKind.SOLE_TRADE, "9000", business_id="business-b"),
        source("uk-property", IncomeKind.UK_PROPERTY, "10000", business_id="property-uk"),
    ], assessment_tax_year="2025-26", registered_for_self_assessment=True,
       exemption_applies=False)
    assert result.qualifying_income == Decimal("31000.00")
    assert result.status is MtdStatus.MTD_APPLIES
    assert result.qualifying_business_ids == ("business-a", "business-b", "property-uk")


def test_threshold_is_strictly_more_than_not_equal():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "30000"),
    ], assessment_tax_year="2025-26")
    assert result.status is MtdStatus.APPROACHING_MTD_THRESHOLD
    assert result.distance_from_threshold == Decimal("0.00")


def test_approaching_threshold_is_progressive():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "25000"),
    ], assessment_tax_year="2025-26")
    assert result.status is MtdStatus.APPROACHING_MTD_THRESHOLD
    assert result.distance_from_threshold == Decimal("5000.00")


def test_incomplete_source_wins_over_threshold_classification():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "51000", complete=False),
    ], assessment_tax_year="2024-25")
    assert result.status is MtdStatus.MTD_DATA_INCOMPLETE
    assert result.data_complete is False


def test_future_threshold_is_centralised_by_assessment_year():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "21000"),
    ], assessment_tax_year="2026-27", registered_for_self_assessment=True,
       exemption_applies=False)
    assert result.threshold == Decimal("20000")
    assert result.mandatory_from_tax_year == "2028-29"
    assert result.status is MtdStatus.MTD_APPLIES


def test_over_threshold_with_unknown_eligibility_fails_closed():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "51000"),
    ], assessment_tax_year="2024-25")
    assert result.status is MtdStatus.MTD_DATA_INCOMPLETE
    assert result.eligibility_complete is False


def test_confirmed_exemption_prevents_applies_classification():
    result = assess_mtd_readiness([
        source("trade", IncomeKind.SOLE_TRADE, "51000"),
    ], assessment_tax_year="2024-25", registered_for_self_assessment=True,
       exemption_applies=True)
    assert result.status is MtdStatus.NOT_CURRENTLY_IN_SCOPE
    assert result.exemption_applies is True


def test_unknown_tax_year_fails_closed():
    try:
        assess_mtd_readiness([], assessment_tax_year="2027-28")
    except ValueError as exc:
        assert "No MTD threshold rule" in str(exc)
    else:
        raise AssertionError("Unknown tax year must fail closed")
