"""Pure HMRC PAYE source-bundle structural-eligibility projection.

This module deliberately stops before identity, joining, canonical evidence,
currentness, reconciliation, persistence, transport, or provider activation.
"""

from __future__ import annotations

import re as _re
from decimal import Decimal as _Decimal

from reserved.providers import hmrc_individual_employment_source_evidence as _employment
from reserved.providers import hmrc_individual_income_source_evidence as _income
from reserved.providers.hmrc_individual_employment_contract import (
    COMPLETENESS_UNVERIFIED as _EMPLOYMENT_COMPLETENESS,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME as _EMPLOYMENT_API,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION as _EMPLOYMENT_VERSION,
)
from reserved.providers.hmrc_individual_employment_source_evidence import (
    EmploymentSourceEvidenceRecord as _EmploymentSourceEvidenceRecord,
    HMRCIndividualEmploymentEvidence as _HMRCIndividualEmploymentEvidence,
)
from reserved.providers.hmrc_individual_income_contract import (
    HMRC_INDIVIDUAL_INCOME_API as _INCOME_API,
    HMRC_INDIVIDUAL_INCOME_API_VERSION as _INCOME_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS as _INCOME_COMPLETENESS,
)
from reserved.providers.hmrc_individual_income_source_evidence import (
    HMRCIndividualIncomeSourceEvidence as _HMRCIndividualIncomeSourceEvidence,
    IndividualIncomeEmploymentSourceEvidence as _IndividualIncomeEmploymentSourceEvidence,
)
from reserved.providers.hmrc_individual_tax_contract import (
    HMRC_INDIVIDUAL_TAX_API_VERSION as _TAX_VERSION,
    HMRC_INDIVIDUAL_TAX_COMPLETENESS as _TAX_COMPLETENESS,
)
from reserved.providers.hmrc_individual_tax_source_evidence import (
    HMRC_INDIVIDUAL_TAX_API_NAME as _TAX_API,
    HMRCIndividualTaxSourceEvidence as _HMRCIndividualTaxSourceEvidence,
    IndividualTaxEmploymentEvidence as _IndividualTaxEmploymentEvidence,
)


class HMRCPayeMappingEligibilityError(ValueError):
    """Fixed, categorical and non-echoing mapping-eligibility refusal."""


_TAX_YEAR = _re.compile(r"[0-9]{4}-[0-9]{2}")
_MONEY_LIMIT = _Decimal("1000000000000000000.00")
_EMPLOYMENT_UNSET = _employment._UNSET
_INCOME_UNSET = _income._UNSET
_EMPLOYMENT_STATE = frozenset(
    {
        "source_api_name",
        "source_api_version",
        "tax_year",
        "records",
        "evidence_reference",
        "observed_at",
        "completeness",
        "unknown_fields",
        "_source_artifact_sha256_state",
    }
)
_EMPLOYMENT_RECORD_STATE = frozenset(
    {
        "employer_paye_reference",
        "employer_name",
        "off_payroll_work_flag",
        "absent_fields",
        "unknown_fields",
    }
)
_INCOME_STATE = frozenset(
    {
        "source_api_name",
        "source_api_version",
        "tax_year",
        "employments",
        "pensions_benefits",
        "evidence_reference",
        "observed_at",
        "completeness",
        "unknown_names",
        "_source_artifact_sha256_state",
    }
)
_INCOME_EMPLOYMENT_STATE = frozenset(
    {"employer_paye_reference", "pay_from_employment", "unknown_names"}
)
_AUTHORITY_FLAGS = (
    ("same_subject_authority", False),
    ("acquisition_run_authority", False),
    ("employment_identity_authority", False),
    ("owner_scope_authority", False),
    ("transport_authority", False),
    ("persistence_authority", False),
    ("customer_evidence_authority", False),
    ("canonical_evidence_authority", False),
    ("production_authority", False),
    ("activation_authority", False),
    ("paye_evidence_emitted", False),
)


def _refuse(category: str) -> None:
    raise HMRCPayeMappingEligibilityError(category) from None


def _exact_dict_state(value: object, names: frozenset[str]) -> dict:
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or frozenset(state.keys()) != names:
        _refuse("invalid_source_bundle")
    return state


def _validate_bundles(employment: object, income: object, tax: object) -> None:
    """Revalidate while normalising only facts owned by later categories."""
    if type(employment) is not _HMRCIndividualEmploymentEvidence:
        _refuse("invalid_source_bundle")
    if type(income) is not _HMRCIndividualIncomeSourceEvidence:
        _refuse("invalid_source_bundle")
    if type(tax) is not _HMRCIndividualTaxSourceEvidence:
        _refuse("invalid_source_bundle")
    try:
        employment_state = _exact_dict_state(employment, _EMPLOYMENT_STATE)
        income_state = _exact_dict_state(income, _INCOME_STATE)
        records = employment_state["records"]
        if type(records) is not tuple:
            _refuse("invalid_source_bundle")
        checked_records = []
        for record in records:
            if type(record) is not _EmploymentSourceEvidenceRecord:
                _refuse("invalid_source_bundle")
            _exact_dict_state(record, _EMPLOYMENT_RECORD_STATE)
            checked_records.append(
                _EmploymentSourceEvidenceRecord(
                    record.employer_paye_reference,
                    record.employer_name,
                    record.off_payroll_work_flag,
                    record.absent_fields,
                    record.unknown_fields,
                )
            )
        if not checked_records:
            checked_records.append(
                _EmploymentSourceEvidenceRecord(
                    "", "", None, frozenset({"offPayrollWorkFlag"}), frozenset()
                )
            )

        if type(income.employments) is not tuple:
            _refuse("invalid_source_bundle")
        checked_income_employments_list = []
        for item in income.employments:
            if type(item) is not _IndividualIncomeEmploymentSourceEvidence:
                _refuse("invalid_source_bundle")
            _exact_dict_state(item, _INCOME_EMPLOYMENT_STATE)
            checked_income_employments_list.append(
                _IndividualIncomeEmploymentSourceEvidence(
                    item.employer_paye_reference, 0, item.unknown_names
                )
            )
        checked_income_employments = tuple(checked_income_employments_list)

        if type(tax.employments) is not tuple:
            _refuse("invalid_source_bundle")
        checked_tax_employments = tuple(
            _IndividualTaxEmploymentEvidence(
                item.employer_paye_reference, 0, item.unknown_names
            )
            if type(item) is _IndividualTaxEmploymentEvidence
            else _refuse("invalid_source_bundle")
            for item in tax.employments
        )

        employment_kwargs = {}
        retained_employment_digest = employment_state[
            "_source_artifact_sha256_state"
        ]
        if retained_employment_digest is not _EMPLOYMENT_UNSET:
            employment_kwargs["source_artifact_sha256"] = retained_employment_digest
        _HMRCIndividualEmploymentEvidence(
            _EMPLOYMENT_API,
            _EMPLOYMENT_VERSION,
            "2025-26",
            tuple(checked_records),
            employment.evidence_reference,
            employment.observed_at,
            _EMPLOYMENT_COMPLETENESS,
            unknown_fields=employment.unknown_fields,
            **employment_kwargs,
        )

        income_kwargs = {}
        retained_income_digest = income_state["_source_artifact_sha256_state"]
        if retained_income_digest is not _INCOME_UNSET:
            income_kwargs["source_artifact_sha256"] = retained_income_digest
        _HMRCIndividualIncomeSourceEvidence(
            _INCOME_API,
            _INCOME_VERSION,
            "2025-26",
            checked_income_employments,
            income.pensions_benefits,
            income.evidence_reference,
            income.observed_at,
            _INCOME_COMPLETENESS,
            unknown_names=income.unknown_names,
            **income_kwargs,
        )

        _HMRCIndividualTaxSourceEvidence(
            _TAX_API,
            _TAX_VERSION,
            "2025-26",
            checked_tax_employments,
            tax.pensions_benefits,
            tax.refunds,
            tax.top_level_unknown_names,
            tax.evidence_reference,
            tax.collected_at,
            _TAX_COMPLETENESS,
            tax.source_artifact_sha256,
        )
    except HMRCPayeMappingEligibilityError:
        raise
    except Exception:
        _refuse("invalid_source_bundle")


def _validate_contracts(employment: object, income: object, tax: object) -> None:
    expected = (
        (employment.source_api_name, _EMPLOYMENT_API),
        (employment.source_api_version, _EMPLOYMENT_VERSION),
        (employment.completeness, _EMPLOYMENT_COMPLETENESS),
        (income.source_api_name, _INCOME_API),
        (income.source_api_version, _INCOME_VERSION),
        (income.completeness, _INCOME_COMPLETENESS),
        (tax.source_api_name, _TAX_API),
        (tax.source_api_version, _TAX_VERSION),
        (tax.completeness, _TAX_COMPLETENESS),
    )
    if any(type(actual) is not str or actual != wanted for actual, wanted in expected):
        _refuse("unsupported_source_contract")


def _validate_tax_years(employment: object, income: object, tax: object) -> str:
    years = (employment.tax_year, income.tax_year, tax.tax_year)
    for year in years:
        if type(year) is not str or _TAX_YEAR.fullmatch(year) is None:
            _refuse("invalid_tax_year")
        if int(year[5:]) != (int(year[:4]) + 1) % 100:
            _refuse("invalid_tax_year")
    if years[0] != years[1] or years[0] != years[2]:
        _refuse("invalid_tax_year")
    return years[0]


def _money(value: object) -> tuple[tuple, _Decimal]:
    if type(value) is int:
        if value < 0 or value > _MONEY_LIMIT:
            _refuse("unsupported_money")
        representation = ("int", value)
        digits = _Decimal(value).as_tuple().digits
        candidate = _Decimal((0, digits + (0, 0), -2))
    elif type(value) is _Decimal:
        parts = value.as_tuple()
        if (
            not value.is_finite()
            or parts.sign != 0
            or parts.exponent < -2
            or value > _MONEY_LIMIT
        ):
            _refuse("unsupported_money")
        representation = ("decimal", parts.sign, parts.digits, parts.exponent)
        candidate = _Decimal(
            (0, parts.digits + (0,) * (parts.exponent + 2), -2)
        )
        if candidate != value:
            _refuse("unsupported_money")
    else:
        _refuse("unsupported_money")
    return representation, candidate


def project_hmrc_paye_mapping_eligibility(employment, income, tax, /):
    """Return the exact detached eligibility tuple or a categorical refusal."""
    _validate_bundles(employment, income, tax)
    _validate_contracts(employment, income, tax)

    if len(employment.records) != 1 or len(income.employments) != 1 or len(tax.employments) != 1:
        _refuse("unsupported_source_cardinality")

    tax_year = _validate_tax_years(employment, income, tax)
    employment_record = employment.records[0]
    income_record = income.employments[0]
    tax_record = tax.employments[0]

    if (
        employment.unknown_fields
        or employment_record.unknown_fields
        or income.unknown_names
        or income_record.unknown_names
        or income.pensions_benefits.unknown_names
        or tax.top_level_unknown_names
        or tax_record.unknown_names
        or tax.pensions_benefits.unknown_names
        or tax.refunds.unknown_names
    ):
        _refuse("unsupported_schema_extension")

    if (
        income.pensions_benefits.present_fields
        or tax.pensions_benefits.present_fields
        or tax.refunds.present_fields
    ):
        _refuse("unsupported_pension_benefit_or_refund_set_off")

    references = (
        employment_record.employer_paye_reference,
        income_record.employer_paye_reference,
        tax_record.employer_paye_reference,
    )
    if "267/LS500" in references:
        _refuse("unsupported_state_pension_lump_sum")

    income_representation, income_candidate = _money(income_record.pay_from_employment)
    tax_representation, tax_candidate = _money(tax_record.tax_taken_off_pay)

    employment_digest = employment.source_artifact_sha256
    income_digest = income.source_artifact_sha256
    tax_digest = tax.source_artifact_sha256
    off_payroll_present = "offPayrollWorkFlag" not in employment_record.absent_fields

    employment_source = (
        ("source_api_name", employment.source_api_name),
        ("source_api_version", employment.source_api_version),
        ("evidence_reference", employment.evidence_reference),
        ("observed_at", employment.observed_at),
        ("source_artifact_sha256_present", employment_digest is not None),
        ("source_artifact_sha256", employment_digest),
        ("source_completeness", employment.completeness),
        ("employer_paye_reference", employment_record.employer_paye_reference),
        ("employer_name", employment_record.employer_name),
        ("off_payroll_work_flag_present", off_payroll_present),
        ("off_payroll_work_flag", employment_record.off_payroll_work_flag),
    )
    income_source = (
        ("source_api_name", income.source_api_name),
        ("source_api_version", income.source_api_version),
        ("evidence_reference", income.evidence_reference),
        ("observed_at", income.observed_at),
        ("source_artifact_sha256_present", income_digest is not None),
        ("source_artifact_sha256", income_digest),
        ("source_completeness", income.completeness),
        ("employer_paye_reference", income_record.employer_paye_reference),
        ("pay_from_employment", income_record.pay_from_employment),
        ("pay_from_employment_representation", income_representation),
        ("pay_from_employment_two_decimal_candidate", income_candidate),
    )
    tax_source = (
        ("source_api_name", tax.source_api_name),
        ("source_api_version", tax.source_api_version),
        ("evidence_reference", tax.evidence_reference),
        ("collected_at", tax.collected_at),
        ("source_artifact_sha256_present", tax_digest is not None),
        ("source_artifact_sha256", tax_digest),
        ("source_completeness", tax.completeness),
        ("employer_paye_reference", tax_record.employer_paye_reference),
        ("tax_taken_off_pay", tax_record.tax_taken_off_pay),
        ("tax_taken_off_pay_representation", tax_representation),
        ("tax_taken_off_pay_two_decimal_candidate", tax_candidate),
    )
    return (
        ("schema_version", "hmrc_paye_mapping_eligibility.v1"),
        ("result_kind", "structurally_eligible_non_authoritative"),
        ("tax_year", tax_year),
        ("employment_source", employment_source),
        ("income_source", income_source),
        ("tax_source", tax_source),
        ("mapping_completeness", "UNKNOWN"),
        ("currentness", "UNKNOWN"),
        ("authority_flags", _AUTHORITY_FLAGS),
    )


__all__ = (
    "HMRCPayeMappingEligibilityError",
    "project_hmrc_paye_mapping_eligibility",
)
