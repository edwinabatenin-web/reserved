"""Hand-written adapters for the independently approved MTD literals.

MTD remains a readiness result, deliberately separate from annual liability.
The adapter below translates its tax-year/status vocabulary for assertions; it
is test-only and does not create a second production contract.
"""

from decimal import Decimal

import pytest

from reserved.engines.mtd_readiness import IncomeKind, IncomeSource, MtdStatus, assess_mtd_readiness


START_DATES = {"2026-27": "2026-04-06", "2027-28": "2027-04-06", "2028-29": "2028-04-06"}


def _audit_case(year, trade, prop, *, registered=None, exempt=None, excluded=()):
    sources = [
        IncomeSource("trade", IncomeKind.SOLE_TRADE, trade),
        IncomeSource("property", IncomeKind.UK_PROPERTY, prop),
        *excluded,
    ]
    result = assess_mtd_readiness(
        sources,
        assessment_tax_year=year.replace("/", "-"),
        registered_for_self_assessment=registered,
        exemption_applies=exempt,
    )
    if result.status is MtdStatus.MTD_APPLIES:
        threshold_result = "over"
        mandatory_from = START_DATES[result.mandatory_from_tax_year]
    elif result.status is MtdStatus.MTD_DATA_INCOMPLETE:
        threshold_result = "eligibility_incomplete"
        mandatory_from = None
    elif result.exemption_applies:
        threshold_result = "exempt"
        mandatory_from = None
    else:
        threshold_result = "not_over"
        mandatory_from = None
    return result, threshold_result, mandatory_from


@pytest.mark.engine
@pytest.mark.parametrize(
    "case_id,year,trade,prop,registered,exempt,qualifying,status,start",
    [
        ("RW3-MTD-001", "2024/25", "30000", "20000", None, None, "50000.00", "not_over", None),
        ("RW3-MTD-002", "2024/25", "30000", "20001", True, False, "50001.00", "over", "2026-04-06"),
        ("RW3-MTD-003", "2025/26", "10000", "20000", None, None, "30000.00", "not_over", None),
        ("RW3-MTD-004", "2025/26", "10000", "20001", True, False, "30001.00", "over", "2027-04-06"),
        ("RW3-MTD-005", "2026/27", "20000", "0", None, None, "20000.00", "not_over", None),
        ("RW3-MTD-006", "2026/27", "20001", "0", True, False, "20001.00", "over", "2028-04-06"),
        ("RW3-MTD-007", "2024/25", "50001", "0", None, None, "50001.00", "eligibility_incomplete", None),
        ("RW3-MTD-008", "2024/25", "50001", "0", True, True, "50001.00", "exempt", None),
    ],
)
def test_approved_mtd_threshold_literals(case_id, year, trade, prop, registered, exempt, qualifying, status, start):
    result, threshold_result, mandatory_from = _audit_case(
        year, trade, prop, registered=registered, exempt=exempt
    )
    assert result.qualifying_income == Decimal(qualifying), case_id
    assert threshold_result == status, case_id
    assert mandatory_from == start, case_id


def test_mtd_excludes_nonqualifying_income_and_uses_gross_not_profit():
    excluded = (
        IncomeSource("employment", IncomeKind.PAYE_EMPLOYMENT, "50000"),
        IncomeSource("dividends", IncomeKind.DIVIDENDS, "10000"),
        IncomeSource("savings", IncomeKind.SAVINGS_INTEREST, "5000"),
    )
    result, status, _ = _audit_case("2024/25", "20000", "10000", excluded=excluded)
    assert result.qualifying_income == Decimal("30000.00")
    assert status == "not_over"
    assert result.excluded_source_ids == ("employment", "dividends", "savings")

    gross, status, start = _audit_case("2024/25", "40000", "10001", registered=True, exempt=False)
    assert gross.qualifying_income == Decimal("50001.00")
    assert Decimal("40000") - Decimal("25000") + Decimal("10001") - Decimal("9000") == Decimal("16001")
    assert (status, start) == ("over", "2026-04-06")


def test_mtd_operational_and_partnership_boundaries_remain_explicitly_separate():
    statutory, status, start = _audit_case("2024/25", "50001", "0", registered=True, exempt=False)
    assert (status, start) == ("over", "2026-04-06")
    # RW3-MTD-011's recent-return sign-up fact is operational readiness, not a
    # reason to alter the statutory threshold result.
    assert statutory.status is MtdStatus.MTD_APPLIES

    partnership = IncomeSource("partnership", IncomeKind.OTHER_TAXABLE_INCOME, "60000")
    result, status, start = _audit_case("2024/25", "0", "0", excluded=(partnership,))
    assert result.qualifying_income == Decimal("0.00")
    assert (status, start) == ("not_over", None)
    assert result.excluded_source_ids == ("partnership",)
