"""Tax-year-versioned MTD for Income Tax readiness assessment.

The rules here classify readiness only. They do not submit updates or a tax
return. Qualifying income is kept separate from PAYE, dividends, savings and
capital gains, and individual businesses remain identifiable in the result.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable

from .utils import money


class IncomeKind(str, Enum):
    PAYE_EMPLOYMENT = "paye_employment"
    SOLE_TRADE = "sole_trade"
    UK_PROPERTY = "uk_property"
    FOREIGN_PROPERTY = "foreign_property"
    DIVIDENDS = "dividends"
    SAVINGS_INTEREST = "savings_interest"
    OTHER_TAXABLE_INCOME = "other_taxable_income"
    CAPITAL_GAINS = "capital_gains"


class MtdStatus(str, Enum):
    NOT_CURRENTLY_IN_SCOPE = "not_currently_in_scope"
    APPROACHING_MTD_THRESHOLD = "approaching_mtd_threshold"
    EXPECTED_NEXT_TAX_YEAR = "expected_to_be_in_scope_next_tax_year"
    MTD_APPLIES = "mtd_applies"
    MTD_DATA_INCOMPLETE = "mtd_data_incomplete"


@dataclass(frozen=True)
class IncomeSource:
    source_id: str
    kind: IncomeKind
    gross_income: Decimal | str | int | float | None
    business_id: str | None = None
    complete: bool = True


@dataclass(frozen=True)
class MtdThresholdRule:
    assessment_tax_year: str
    mandatory_from_tax_year: str
    threshold: Decimal


@dataclass(frozen=True)
class MtdReadiness:
    status: MtdStatus
    assessment_tax_year: str
    mandatory_from_tax_year: str
    qualifying_income: Decimal
    threshold: Decimal
    distance_from_threshold: Decimal
    qualifying_source_ids: tuple[str, ...]
    qualifying_business_ids: tuple[str, ...]
    excluded_source_ids: tuple[str, ...]
    data_complete: bool
    eligibility_complete: bool
    exemption_applies: bool | None


# GOV.UK rules verified 12 August 2026. Centralised here so tax-year changes do
# not require UI or orchestration rewrites. Threshold test is strictly "more
# than", not greater-than-or-equal.
MTD_THRESHOLD_RULES = {
    "2024-25": MtdThresholdRule("2024-25", "2026-27", Decimal("50000")),
    "2025-26": MtdThresholdRule("2025-26", "2027-28", Decimal("30000")),
    "2026-27": MtdThresholdRule("2026-27", "2028-29", Decimal("20000")),
}

_QUALIFYING = {
    IncomeKind.SOLE_TRADE,
    IncomeKind.UK_PROPERTY,
    IncomeKind.FOREIGN_PROPERTY,
}


def _amount(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = money(value)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return amount if amount >= 0 else None


def assess_mtd_readiness(
    sources: Iterable[IncomeSource],
    *,
    assessment_tax_year: str,
    approaching_ratio=Decimal("0.80"),
    registered_for_self_assessment: bool | None = None,
    exemption_applies: bool | None = None,
) -> MtdReadiness:
    rule = MTD_THRESHOLD_RULES.get(assessment_tax_year)
    if rule is None:
        raise ValueError(f"No MTD threshold rule configured for {assessment_tax_year}")

    all_sources = tuple(sources)
    qualifying_sources = tuple(source for source in all_sources if source.kind in _QUALIFYING)
    excluded_sources = tuple(source for source in all_sources if source.kind not in _QUALIFYING)
    complete = all(source.complete and _amount(source.gross_income) is not None
                   for source in qualifying_sources)
    qualifying_income = money(sum(
        (_amount(source.gross_income) or Decimal("0") for source in qualifying_sources),
        Decimal("0"),
    ))
    distance = money(rule.threshold - qualifying_income)

    above_threshold = qualifying_income > rule.threshold
    eligibility_complete = (
        not above_threshold
        or (
            registered_for_self_assessment is not None
            and exemption_applies is not None
        )
    )

    if not complete or not eligibility_complete:
        status = MtdStatus.MTD_DATA_INCOMPLETE
    elif above_threshold and exemption_applies:
        status = MtdStatus.NOT_CURRENTLY_IN_SCOPE
    elif above_threshold and registered_for_self_assessment:
        status = MtdStatus.MTD_APPLIES
    elif above_threshold:
        status = MtdStatus.NOT_CURRENTLY_IN_SCOPE
    elif qualifying_income >= money(rule.threshold * Decimal(str(approaching_ratio))):
        status = MtdStatus.APPROACHING_MTD_THRESHOLD
    else:
        status = MtdStatus.NOT_CURRENTLY_IN_SCOPE

    business_ids = tuple(dict.fromkeys(
        source.business_id or source.source_id for source in qualifying_sources
    ))
    return MtdReadiness(
        status=status,
        assessment_tax_year=assessment_tax_year,
        mandatory_from_tax_year=rule.mandatory_from_tax_year,
        qualifying_income=qualifying_income,
        threshold=rule.threshold,
        distance_from_threshold=distance,
        qualifying_source_ids=tuple(source.source_id for source in qualifying_sources),
        qualifying_business_ids=business_ids,
        excluded_source_ids=tuple(source.source_id for source in excluded_sources),
        data_complete=complete,
        eligibility_complete=eligibility_complete,
        exemption_applies=exemption_applies,
    )
