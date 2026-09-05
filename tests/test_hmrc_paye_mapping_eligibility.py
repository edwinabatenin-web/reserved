"""Acceptance matrix for the detached HMRC PAYE eligibility mapper."""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.providers import hmrc_paye_test_support_benefits_contract as ts_benefits
from reserved.providers import hmrc_paye_test_support_child_benefit_contract as ts_child
from reserved.providers import hmrc_paye_test_support_employment_contract as ts_employment
from reserved.providers import hmrc_paye_test_support_income_contract as ts_income
from reserved.providers import hmrc_paye_test_support_tax_contract as ts_tax
from reserved.providers import hmrc_paye_test_support_winter_fuel_contract as ts_winter

from reserved.providers.hmrc_individual_employment_contract import (
    COMPLETENESS_UNVERIFIED,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
    build_individual_employment_request,
)
from reserved.providers.hmrc_individual_employment_source_evidence import (
    EmploymentSourceEvidenceRecord,
    HMRCIndividualEmploymentEvidence,
)
from reserved.providers.hmrc_individual_income_contract import (
    HMRC_INDIVIDUAL_INCOME_API,
    HMRC_INDIVIDUAL_INCOME_API_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    build_individual_income_request,
)
from reserved.providers.hmrc_individual_income_source_evidence import (
    HMRCIndividualIncomeSourceEvidence,
    IndividualIncomeEmploymentSourceEvidence,
    IndividualIncomePensionsBenefitsSourceEvidence,
)
from reserved.providers.hmrc_individual_tax_contract import (
    HMRC_INDIVIDUAL_TAX_API_VERSION,
    HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    build_individual_tax_request,
)
from reserved.providers.hmrc_individual_tax_source_evidence import (
    HMRC_INDIVIDUAL_TAX_API_NAME,
    HMRCIndividualTaxSourceEvidence,
    IndividualTaxEmploymentEvidence,
    IndividualTaxPensionsBenefitsEvidence,
    IndividualTaxRefundEvidence,
)
from reserved.providers.hmrc_paye_mapping_eligibility import (
    HMRCPayeMappingEligibilityError,
    project_hmrc_paye_mapping_eligibility,
)
from reserved.providers.readiness import PROVIDERS, ReadinessState, assess_provider


NOW = datetime(2026, 9, 5, 9, 30, tzinfo=timezone.utc)
INCOME_BENEFITS = frozenset(
    {
        "otherPensionsAndRetirementAnnuities",
        "incapacityBenefit",
        "jobseekersAllowance",
        "seissNetPaid",
    }
)
TAX_BENEFITS = frozenset(
    {"otherPensionsAndRetirementAnnuities", "incapacityBenefit"}
)
TAX_REFUNDS = frozenset({"taxRefundedOrSetOff"})


class _IntSubclass(int):
    pass


class _DecimalSubclass(Decimal):
    pass


def _bundles(
    *,
    year="2025-26",
    employment_reference="123/AA1",
    income_reference="123/AA1",
    tax_reference="123/AA1",
    pay=Decimal("100.00"),
    deducted=Decimal("20.00"),
    off_payroll=None,
    digests=(None, None, None),
    timestamps=(NOW, NOW, NOW),
    construction_order=("employment", "income", "tax"),
):
    absent = frozenset({"offPayrollWorkFlag"}) if off_payroll is None else frozenset()
    factories = {
        "employment": lambda: HMRCIndividualEmploymentEvidence(
            HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
            HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
            year,
            (EmploymentSourceEvidenceRecord(
                employment_reference, "Example Ltd", off_payroll, absent, frozenset()
            ),),
            "employment-run",
            timestamps[0],
            COMPLETENESS_UNVERIFIED,
            unknown_fields=frozenset(),
            **({"source_artifact_sha256": digests[0]} if digests[0] is not None else {}),
        ),
        "income": lambda: HMRCIndividualIncomeSourceEvidence(
            HMRC_INDIVIDUAL_INCOME_API,
            HMRC_INDIVIDUAL_INCOME_API_VERSION,
            year,
            (IndividualIncomeEmploymentSourceEvidence(income_reference, pay),),
            IndividualIncomePensionsBenefitsSourceEvidence(
                present_fields=frozenset(), absent_fields=INCOME_BENEFITS
            ),
            "income-run",
            timestamps[1],
            HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
            unknown_names=frozenset(),
            **({"source_artifact_sha256": digests[1]} if digests[1] is not None else {}),
        ),
        "tax": lambda: HMRCIndividualTaxSourceEvidence(
            HMRC_INDIVIDUAL_TAX_API_NAME,
            HMRC_INDIVIDUAL_TAX_API_VERSION,
            year,
            (IndividualTaxEmploymentEvidence(tax_reference, deducted, frozenset()),),
            IndividualTaxPensionsBenefitsEvidence(
                None, None, frozenset(), TAX_BENEFITS, frozenset()
            ),
            IndividualTaxRefundEvidence(None, frozenset(), TAX_REFUNDS, frozenset()),
            frozenset(),
            "tax-run",
            timestamps[2],
            HMRC_INDIVIDUAL_TAX_COMPLETENESS,
            digests[2],
        ),
    }
    if tuple(construction_order) not in (
        ("employment", "income", "tax"),
        ("tax", "income", "employment"),
    ):
        raise AssertionError("unsupported test construction order")
    constructed = {}
    for name in construction_order:
        constructed[name] = factories[name]()
    return constructed["employment"], constructed["income"], constructed["tax"]


def _project(**kwargs):
    return project_hmrc_paye_mapping_eligibility(*_bundles(**kwargs))


def _mapping(value):
    return dict(value)


def _refusal(category, bundles):
    with pytest.raises(HMRCPayeMappingEligibilityError) as caught:
        project_hmrc_paye_mapping_eligibility(*bundles)
    assert type(caught.value) is HMRCPayeMappingEligibilityError
    assert type(caught.value).__bases__ == (ValueError,)
    assert str(caught.value) == category


def test_01_exact_source_contracts_are_required_and_revalidated():
    employment, income, tax = _bundles()
    _refusal("invalid_source_bundle", (object(), income, tax))
    object.__setattr__(employment.records[0], "employer_name", object())
    _refusal("invalid_source_bundle", (employment, income, tax))


def test_02_exact_positional_signature_binding_and_categorical_errors():
    signature = inspect.signature(project_hmrc_paye_mapping_eligibility)
    assert str(signature) == "(employment, income, tax, /)"
    sentinel = "DO_NOT_ECHO_VALUE"
    for call in (
        lambda: project_hmrc_paye_mapping_eligibility(),
        lambda: project_hmrc_paye_mapping_eligibility(sentinel),
        lambda: project_hmrc_paye_mapping_eligibility(*_bundles(), sentinel),
        lambda: project_hmrc_paye_mapping_eligibility(
            employment=sentinel, income=sentinel, tax=sentinel
        ),
    ):
        with pytest.raises(TypeError) as caught:
            call()
        assert sentinel not in str(caught.value)


def test_03_exact_ordered_immutable_projection():
    result = _project()
    assert type(result) is tuple
    assert tuple(name for name, _ in result) == (
        "schema_version", "result_kind", "tax_year", "employment_source",
        "income_source", "tax_source", "mapping_completeness", "currentness",
        "authority_flags",
    )
    expected_nested = {
        "employment_source": (
            "source_api_name", "source_api_version", "evidence_reference",
            "observed_at", "source_artifact_sha256_present",
            "source_artifact_sha256", "source_completeness",
            "employer_paye_reference", "employer_name",
            "off_payroll_work_flag_present", "off_payroll_work_flag",
        ),
        "income_source": (
            "source_api_name", "source_api_version", "evidence_reference",
            "observed_at", "source_artifact_sha256_present",
            "source_artifact_sha256", "source_completeness",
            "employer_paye_reference", "pay_from_employment",
            "pay_from_employment_representation",
            "pay_from_employment_two_decimal_candidate",
        ),
        "tax_source": (
            "source_api_name", "source_api_version", "evidence_reference",
            "collected_at", "source_artifact_sha256_present",
            "source_artifact_sha256", "source_completeness",
            "employer_paye_reference", "tax_taken_off_pay",
            "tax_taken_off_pay_representation",
            "tax_taken_off_pay_two_decimal_candidate",
        ),
    }
    projected = _mapping(result)
    for branch, names in expected_nested.items():
        assert tuple(name for name, _ in projected[branch]) == names
    assert "PayeEvidence" not in repr(result)


def test_04_zero_duplicate_distinct_two_and_distinct_many_cardinality_refuse():
    for index, attribute in enumerate(("records", "employments", "employments")):
        for mode in ("zero", "duplicate", "distinct_two", "distinct_many"):
            bundles = list(_bundles())
            value = getattr(bundles[index], attribute)
            if index == 0:
                distinct = tuple(
                    EmploymentSourceEvidenceRecord(
                        f"{number}/DISTINCT", f"Employer {number}", None,
                        frozenset({"offPayrollWorkFlag"}), frozenset(),
                    )
                    for number in range(2, 6)
                )
            elif index == 1:
                distinct = tuple(
                    IndividualIncomeEmploymentSourceEvidence(
                        f"{number}/DISTINCT", number, frozenset()
                    )
                    for number in range(2, 6)
                )
            else:
                distinct = tuple(
                    IndividualTaxEmploymentEvidence(
                        f"{number}/DISTINCT", number, frozenset()
                    )
                    for number in range(2, 6)
                )
            members = {
                "zero": (),
                "duplicate": value + value,
                "distinct_two": value + distinct[:1],
                "distinct_many": value + distinct,
            }[mode]
            object.__setattr__(bundles[index], attribute, members)
            _refusal("unsupported_source_cardinality", tuple(bundles))


def test_05_equal_and_unequal_references_remain_separate_and_non_authoritative():
    for references in (("A", "A", "A"), ("A", "B", "C")):
        result = _mapping(_project(
            employment_reference=references[0], income_reference=references[1],
            tax_reference=references[2],
        ))
        assert tuple(_mapping(result[name])["employer_paye_reference"] for name in
                     ("employment_source", "income_source", "tax_source")) == references
        flags = _mapping(result["authority_flags"])
        assert not flags["same_subject_authority"]
        assert not flags["employment_identity_authority"]


def test_06_state_pension_marker_refuses_in_every_position():
    for field in ("employment_reference", "income_reference", "tax_reference"):
        _refusal("unsupported_state_pension_lump_sum", _bundles(**{field: "267/LS500"}))


def test_07_tax_year_is_exact_equal_ascii_and_consecutive():
    assert _mapping(_project(year="2099-00"))["tax_year"] == "2099-00"
    for year in ("2025/26", "２０２５-２６", "2025-27"):
        bundles = list(_bundles())
        for bundle in bundles:
            object.__setattr__(bundle, "tax_year", year)
        _refusal("invalid_tax_year", tuple(bundles))
    bundles = list(_bundles())
    object.__setattr__(bundles[2], "tax_year", "2024-25")
    _refusal("invalid_tax_year", tuple(bundles))


def test_08_unknown_names_at_every_retained_level_refuse():
    paths = (
        (0, (), "unknown_fields"),
        (0, ("records", 0), "unknown_fields"),
        (1, (), "unknown_names"),
        (1, ("employments", 0), "unknown_names"),
        (1, ("pensions_benefits",), "unknown_names"),
        (2, (), "top_level_unknown_names"),
        (2, ("employments", 0), "unknown_names"),
        (2, ("pensions_benefits",), "unknown_names"),
        (2, ("refunds",), "unknown_names"),
    )
    for index, path, name in paths:
        bundles = list(_bundles())
        target = bundles[index]
        for step in path:
            target = target[step] if type(step) is int else getattr(target, step)
        object.__setattr__(target, name, frozenset({"future"}))
        _refusal("unsupported_schema_extension", tuple(bundles))


def test_09_excluded_presence_including_zero_refuses_and_off_payroll_presence_survives():
    for off_payroll, expected in ((None, (False, None)), (False, (True, False)), (True, (True, True))):
        branch = _mapping(_mapping(_project(off_payroll=off_payroll))["employment_source"])
        assert (branch["off_payroll_work_flag_present"], branch["off_payroll_work_flag"]) == expected
    employment, income, tax = _bundles()
    object.__setattr__(income.pensions_benefits, "other_pensions_and_retirement_annuities", 0)
    object.__setattr__(income.pensions_benefits, "present_fields", frozenset({"otherPensionsAndRetirementAnnuities"}))
    object.__setattr__(income.pensions_benefits, "absent_fields", INCOME_BENEFITS - {"otherPensionsAndRetirementAnnuities"})
    _refusal("unsupported_pension_benefit_or_refund_set_off", (employment, income, tax))
    for target_name, source_name, attr_name, all_names in (
        ("income", "incapacityBenefit", "incapacity_benefit", INCOME_BENEFITS),
        ("income", "jobseekersAllowance", "jobseekers_allowance", INCOME_BENEFITS),
        ("income", "seissNetPaid", "seiss_net_paid", INCOME_BENEFITS),
        ("tax_benefits", "otherPensionsAndRetirementAnnuities", "other_pensions_and_retirement_annuities", TAX_BENEFITS),
        ("tax_benefits", "incapacityBenefit", "incapacity_benefit", TAX_BENEFITS),
        ("tax_refund", "taxRefundedOrSetOff", "tax_refunded_or_set_off", TAX_REFUNDS),
    ):
        employment, income, tax = _bundles()
        target = income.pensions_benefits if target_name == "income" else (
            tax.pensions_benefits if target_name == "tax_benefits" else tax.refunds
        )
        object.__setattr__(target, attr_name, 0)
        object.__setattr__(target, "present_fields", frozenset({source_name}))
        object.__setattr__(target, "absent_fields", all_names - {source_name})
        _refusal("unsupported_pension_benefit_or_refund_set_off", (employment, income, tax))


@pytest.mark.parametrize("value", [0, 1, Decimal("1.00"), Decimal("1.0"), Decimal("1"), Decimal("1E+2")])
def test_10_compatible_money_maps_exactly_to_two_places(value):
    result = _mapping(_project(pay=value, deducted=value))
    assert _mapping(result["income_source"])["pay_from_employment_two_decimal_candidate"] == Decimal(value).quantize(Decimal("0.01"))
    assert _mapping(result["tax_source"])["tax_taken_off_pay_two_decimal_candidate"] == Decimal(value).quantize(Decimal("0.01"))


@pytest.mark.parametrize("value", [
    -1, Decimal("-0.00"), Decimal("1.000"), Decimal("1.001"), Decimal("NaN"),
    Decimal("Infinity"), True, 1.0, _IntSubclass(1), _DecimalSubclass("1.00"),
    1000000000000000001, Decimal("1000000000000000000.01"),
])
def test_11_incompatible_money_refuses_without_coercion(value):
    bundles = list(_bundles())
    object.__setattr__(bundles[1].employments[0], "pay_from_employment", value)
    _refusal("unsupported_money", tuple(bundles))


def test_12_source_number_representations_distinguish_equal_values():
    representations = []
    for value in (1, Decimal("1.0"), Decimal("1.00")):
        branch = _mapping(_mapping(_project(pay=value))["income_source"])
        representations.append(branch["pay_from_employment_representation"])
        assert branch["pay_from_employment_two_decimal_candidate"] == Decimal("1.00")
    assert representations == [("int", 1), ("decimal", 0, (1, 0), -1), ("decimal", 0, (1, 0, 0), -2)]


def test_13_required_zero_is_preserved_not_treated_as_absence():
    result = _mapping(_project(pay=0, deducted=0))
    assert _mapping(result["income_source"])["pay_from_employment"] == 0
    assert _mapping(result["tax_source"])["tax_taken_off_pay"] == 0
    bundles = list(_bundles())
    object.__setattr__(bundles[1], "employments", ())
    _refusal("unsupported_source_cardinality", tuple(bundles))


def test_14_timestamps_and_digest_presence_are_preserved_without_derived_dates():
    timestamps = (
        NOW - timedelta(days=2),
        NOW - timedelta(days=1),
        NOW,
    )
    result = _mapping(_project(
        digests=("a" * 64, None, "c" * 64), timestamps=timestamps
    ))
    employment = _mapping(result["employment_source"])
    income = _mapping(result["income_source"])
    tax = _mapping(result["tax_source"])
    assert employment["observed_at"] == timestamps[0]
    assert income["observed_at"] == timestamps[1]
    assert tax["collected_at"] == timestamps[2]
    assert len({employment["observed_at"], income["observed_at"], tax["collected_at"]}) == 3
    assert (
        employment["source_artifact_sha256_present"],
        employment["source_artifact_sha256"],
    ) == (True, "a" * 64)
    assert (
        income["source_artifact_sha256_present"],
        income["source_artifact_sha256"],
    ) == (False, None)
    assert (
        tax["source_artifact_sha256_present"],
        tax["source_artifact_sha256"],
    ) == (True, "c" * 64)
    assert "effective_through" not in result and "observed_on" not in result


def test_employment_retained_digest_omission_presence_and_explicit_none_are_distinct():
    omitted = _mapping(_mapping(_project())["employment_source"])
    assert (
        omitted["source_artifact_sha256_present"],
        omitted["source_artifact_sha256"],
    ) == (False, None)

    present = _mapping(_mapping(_project(digests=("a" * 64, None, None)))["employment_source"])
    assert (
        present["source_artifact_sha256_present"],
        present["source_artifact_sha256"],
    ) == (True, "a" * 64)

    employment, income, tax = _bundles()
    object.__setattr__(employment, "_source_artifact_sha256_state", None)
    _refusal("invalid_source_bundle", (employment, income, tax))


def test_15_completeness_and_currentness_are_unknown_and_no_policy_is_accepted():
    result = _mapping(_project())
    assert result["mapping_completeness"] == result["currentness"] == "UNKNOWN"
    assert tuple(inspect.signature(project_hmrc_paye_mapping_eligibility).parameters) == ("employment", "income", "tax")


def test_16_every_authority_flag_is_false_and_copies_gain_no_authority():
    result = _project()
    flags = _mapping(_mapping(result)["authority_flags"])
    assert len(flags) == 11 and not any(flags.values())
    recreated = tuple(result)
    assert recreated == result
    altered = result[:-1] + (("authority_flags", (("production_authority", True),)),)
    assert altered != result


def test_17_no_request_identity_is_used_or_projected():
    result = _mapping(_project())
    projected_names = set(result)
    for branch in ("employment_source", "income_source", "tax_source"):
        projected_names.update(_mapping(result[branch]))
    assert projected_names.isdisjoint(
        {"request_identity", "request_receipt", "same_subject", "acquisition_run"}
    )
    employment_one = build_individual_employment_request(
        utr="1234567890", tax_year="2025-26"
    )
    employment_two = build_individual_employment_request(
        utr="0987654321", tax_year="2025-26"
    )
    assert employment_one != employment_two
    assert build_individual_income_request(
        utr="1234567890", tax_year="2025-26"
    ) == build_individual_income_request(utr="0987654321", tax_year="2025-26")
    assert build_individual_tax_request(
        utr="1234567890", tax_year="2025-26"
    ) == build_individual_tax_request(utr="0987654321", tax_year="2025-26")


def test_18_evidence_references_are_metadata_and_run_authority_stays_false():
    result = _mapping(_project())
    assert _mapping(result["employment_source"])["evidence_reference"] == "employment-run"
    assert not _mapping(result["authority_flags"])["acquisition_run_authority"]


def _actual_test_support_observations_and_tax_body_results():
    employment_request = ts_employment.build_employment_test_support_request(
        utr="0123456789", tax_year="2025-26"
    )
    employment = ts_employment.observe_employment_test_support_response(
        employment_request,
        status_code=201,
        content_type="application/json",
        payload={
            "employments": [{
                "employerName": "Fixture Employer",
                "employerPayeReference": "123/FIXTURE",
            }]
        },
    )
    income_request = ts_income.build_create_annual_income_summary_request(
        utr="0123456789", tax_year="2025-26"
    )
    income = ts_income.observe_create_annual_income_summary_response(
        income_request,
        status_code=201,
        content_type="application/json",
        payload={
            "employments": [],
            "pensionsAnnuitiesAndOtherStateBenefits": {},
        },
    )
    tax_request = ts_tax.build_tax_test_support_request(
        utr="0123456789", tax_year="2025-26"
    )
    tax_payload = {
        "employments": [],
        "pensionsAnnuitiesAndOtherStateBenefits": {},
        "refunds": {},
    }
    tax = ts_tax.observe_create_tax_summary_response(
        tax_request,
        status_code=201,
        content_type="application/json",
        payload=tax_payload,
    )
    benefits_request = ts_benefits.build_benefits_summary_request(
        utr="0123456789", tax_year="2025-26"
    )
    benefits = ts_benefits.observe_benefits_summary_response(
        benefits_request,
        status_code=201,
        content_type="application/json",
        payload={"employments": [{"employerPayeReference": "123/FIXTURE"}]},
    )
    child_request = ts_child.build_child_benefit_create_request(
        utr="0123456789", tax_year="2025-26"
    )
    child = ts_child.observe_child_benefit_create_response(
        child_request,
        status_code=201,
        content_type="application/json",
        payload={"expectedStatus": 200},
    )
    winter_request = ts_winter.build_winter_fuel_create_request(
        nino="SA123456Z", tax_year="2025-26"
    )
    winter = ts_winter.observe_winter_fuel_create_response(
        winter_request,
        status_code=201,
        content_type="application/json",
        payload={"expectedStatus": 200},
    )
    tax_request_body = ts_tax.parse_tax_test_support_request({})
    tax_unbound_summary = ts_tax.parse_tax_summary_created(
        tax_payload, status_code=201
    )
    return (
        employment,
        income,
        tax,
        benefits,
        child,
        winter,
        tax_request_body,
        tax_unbound_summary,
    )


def test_19_all_actual_test_support_observations_and_tax_body_results_refuse():
    employment, income, tax = _bundles()
    actual_values = _actual_test_support_observations_and_tax_body_results()
    assert tuple(type(value) for value in actual_values[:6]) == (
        ts_employment.EmploymentTestSupportResponseObservation,
        ts_income.AnnualIncomeSummaryTestDataObservation,
        ts_tax.TaxSummaryCreated,
        ts_benefits.BenefitsSummaryCreated,
        ts_child.ChildBenefitCreateResponseObservation,
        ts_winter.WinterFuelCreateResponseObservation,
    )
    assert type(actual_values[6]) is ts_tax.TaxTestSupportRequestBody
    assert type(actual_values[7]) is ts_tax.TaxSummaryCreated
    assert actual_values[7].request_bound is False
    for actual in actual_values:
        for position in range(3):
            values = [employment, income, tax]
            values[position] = actual
            _refusal("invalid_source_bundle", tuple(values))


def test_20_construction_order_cannot_create_join_aggregate_or_precedence():
    forward = _project(
        employment_reference="C", income_reference="A", tax_reference="B",
        construction_order=("employment", "income", "tax"),
    )
    reverse = _project(
        employment_reference="C", income_reference="A", tax_reference="B",
        construction_order=("tax", "income", "employment"),
    )
    assert forward == reverse
    names = repr(forward)
    assert all(term not in names for term in ("aggregate", "total", "precedence", "joined_employment"))


def test_21_output_and_refusals_do_not_echo_sensitive_source_values():
    sensitive = "SENSITIVE-UTR-NINO-TOKEN-PROVIDER-MESSAGE"
    employment, income, tax = _bundles()
    object.__setattr__(income.employments[0], "pay_from_employment", sensitive)
    with pytest.raises(HMRCPayeMappingEligibilityError) as caught:
        project_hmrc_paye_mapping_eligibility(employment, income, tax)
    assert sensitive not in str(caught.value) and sensitive not in repr(caught.value)
    assert sensitive not in repr(_project())


def test_22_module_is_dependency_inert_and_hmrc_readiness_stays_disabled():
    path = Path(__file__).parents[1] / "reserved/providers/hmrc_paye_mapping_eligibility.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    forbidden = (
        "paye_reconciliation", "forecast", "presentation", "session", "auth",
        "membership", "transport", "http", "credential", "environment",
        "database", "filesystem", "route",
    )
    assert not any(token in module for token in forbidden for module in imported)
    source = path.read_text(encoding="utf-8")
    assert "PayeEvidence" not in source
    hmrc = next(item for item in PROVIDERS if item.name == "hmrc")
    assert hmrc.implementation_enabled is False
    configured = {name: "synthetic" for name in hmrc.credential_variables}
    configured[hmrc.environment_variable] = "sandbox"
    configured[hmrc.callback_variable] = "https://sandbox.example/hmrc/callback"
    result = assess_provider(hmrc, configured)
    assert result.state is ReadinessState.CONFIGURED_NOT_IMPLEMENTED
    assert result.may_make_sandbox_calls is False
    configured[hmrc.environment_variable] = "production"
    assert assess_provider(hmrc, configured).state is ReadinessState.BLOCKED_UNSAFE_ENVIRONMENT


def test_error_precedence_is_exact():
    employment, income, tax = _bundles(employment_reference="267/LS500")
    object.__setattr__(income, "unknown_names", frozenset({"future"}))
    object.__setattr__(tax.employments[0], "tax_taken_off_pay", Decimal("-1"))
    _refusal("unsupported_schema_extension", (employment, income, tax))


def test_wrong_contract_constants_have_their_own_category():
    employment, income, tax = _bundles()
    object.__setattr__(income, "source_api_version", "9.9")
    _refusal("unsupported_source_contract", (employment, income, tax))
