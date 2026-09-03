"""Synthetic, network-free HMRC PAYE Test Support 2.1 income create contract tests."""

import ast
import copy
import pickle
from collections import OrderedDict
from dataclasses import replace
from decimal import Decimal
from enum import IntEnum
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType

import pytest

import reserved.providers.hmrc_paye_test_support_income_contract as income_contract
from reserved.providers.hmrc_paye_test_support_income_contract import (
    HMRC_PAYE_TEST_SUPPORT_ACCEPT,
    HMRC_PAYE_TEST_SUPPORT_API,
    HMRC_PAYE_TEST_SUPPORT_API_VERSION,
    HMRC_PAYE_TEST_SUPPORT_COMPLETENESS,
    HMRC_PAYE_TEST_SUPPORT_HTTP_METHOD,
    HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE,
    HMRC_PAYE_TEST_SUPPORT_OAUTH_GRANT_TYPE,
    HMRC_PAYE_TEST_SUPPORT_OAUTH_SCOPES,
    HMRC_PAYE_TEST_SUPPORT_OPERATION_ID,
    HMRC_PAYE_TEST_SUPPORT_PATH_TEMPLATE,
    HMRC_PAYE_TEST_SUPPORT_SANDBOX_ORIGIN,
    HMRC_PAYE_TEST_SUPPORT_SCENARIOS,
    HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_1,
    HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_2,
    HMRC_PAYE_TEST_SUPPORT_SUCCESS_STATUS,
    AnnualIncomeEmploymentObservation,
    AnnualIncomePensionsBenefitsObservation,
    AnnualIncomeSummaryTestDataObservation,
    CreateAnnualIncomeSummaryRequestIntent,
    HMRCPayeTestSupportIncomeContractError,
    build_create_annual_income_summary_request,
    observe_create_annual_income_summary_response,
    validate_annual_income_summary_observation,
)
from reserved.providers.http_boundary import ProviderRequest


UTR = "0123456789"
TAX_YEAR = "2023-24"


def _request(utr=UTR, tax_year=TAX_YEAR, scenario="HAPPY_PATH_1"):
    return build_create_annual_income_summary_request(
        utr=utr, tax_year=tax_year, scenario=scenario
    )


def _success_payload(**overrides):
    payload = {"employments": [], "pensionsAnnuitiesAndOtherStateBenefits": {}}
    payload.update(overrides)
    return payload


_MISSING = object()


def _observe(payload=_MISSING, *, status_code=201, content_type="application/json", request=None):
    if payload is _MISSING:
        payload = _success_payload()
    return observe_create_annual_income_summary_response(
        request or _request(),
        status_code=status_code,
        content_type=content_type,
        payload=payload,
    )


class _HostileValue:
    """Any inspection (repr/str/hash/eq/iter) raises; must never be touched."""

    def __repr__(self):
        raise RuntimeError("repr touched")

    def __str__(self):
        raise RuntimeError("str touched")

    def __hash__(self):
        raise RuntimeError("hash touched")

    def __eq__(self, other):
        raise RuntimeError("eq touched")

    def __iter__(self):
        raise RuntimeError("iter touched")

    def __bool__(self):
        raise RuntimeError("bool touched")

    def __sub__(self, other):
        raise RuntimeError("subtraction touched")

    def __rsub__(self, other):
        raise RuntimeError("reverse subtraction touched")


class _IntSubclass(int):
    pass


class _DecimalSubclass(Decimal):
    pass


class _StrSubclass(str):
    pass


# ── Exact constants and request construction ─────────────────────────────────


def test_documented_constants_are_exact():
    assert HMRC_PAYE_TEST_SUPPORT_OPERATION_ID == "createAnnualIncomeSummaryTestData"
    assert HMRC_PAYE_TEST_SUPPORT_API == "individual-paye-test-support"
    assert HMRC_PAYE_TEST_SUPPORT_API_VERSION == "2.1"
    assert HMRC_PAYE_TEST_SUPPORT_HTTP_METHOD == "POST"
    assert HMRC_PAYE_TEST_SUPPORT_SANDBOX_ORIGIN == "https://test-api.service.hmrc.gov.uk"
    assert HMRC_PAYE_TEST_SUPPORT_PATH_TEMPLATE == (
        "/individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}"
    )
    assert HMRC_PAYE_TEST_SUPPORT_ACCEPT == "application/vnd.hmrc.2.1+json"
    assert HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE == "application/json"
    assert HMRC_PAYE_TEST_SUPPORT_SUCCESS_STATUS == 201
    assert HMRC_PAYE_TEST_SUPPORT_COMPLETENESS == "UNVERIFIED"


def test_oauth_metadata_is_application_restricted_with_empty_scope_map():
    assert HMRC_PAYE_TEST_SUPPORT_OAUTH_GRANT_TYPE == "client_credentials"
    # The specification's scope map/list are empty: no named scope is invented.
    assert HMRC_PAYE_TEST_SUPPORT_OAUTH_SCOPES == frozenset()
    assert type(HMRC_PAYE_TEST_SUPPORT_OAUTH_SCOPES) is frozenset


def test_scenario_universe_is_exactly_two_literals():
    assert HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_1 == "HAPPY_PATH_1"
    assert HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_2 == "HAPPY_PATH_2"
    assert HMRC_PAYE_TEST_SUPPORT_SCENARIOS == {"HAPPY_PATH_1", "HAPPY_PATH_2"}
    assert type(HMRC_PAYE_TEST_SUPPORT_SCENARIOS) is frozenset


def test_request_intent_retains_canonical_utr_free_identity_and_context():
    request = _request()
    assert isinstance(request, CreateAnnualIncomeSummaryRequestIntent)
    assert not hasattr(request, "__dict__")
    assert request.tax_year == "2023-24"
    assert request.scenario == "HAPPY_PATH_1"
    assert request.scenario_present is True


def test_request_intent_exposes_no_url_path_credential_or_sendable_state():
    request = _request()
    for absent in (
        "url", "headers", "body", "authorization", "token", "credential",
        "transport", "client", "method", "sandbox_origin", "path_template",
        "accept", "scope", "redacted_path", "operation_id",
    ):
        assert not hasattr(request, absent)
    assert not issubclass(CreateAnnualIncomeSummaryRequestIntent, ProviderRequest)


def test_raw_utr_is_discarded_from_every_retained_state():
    request = _request()
    snapshots = [
        repr(request),
        str(request),
        repr(copy.copy(request)),
        repr(copy.deepcopy(request)),
    ]
    for snapshot in snapshots:
        assert UTR not in snapshot

    pickled = pickle.dumps(request)
    assert UTR.encode("ascii") not in pickled
    assert UTR not in repr(pickle.loads(pickled))

    assert pickle.loads(pickled) == request
    assert hash(pickle.loads(pickled)) == hash(request)


def test_each_request_has_fresh_identity_independent_of_utr():
    a = _request(utr="1111111111")
    b = _request(utr="2222222222")
    assert a != b
    assert repr(a) == repr(b)
    for snapshot in (pickle.dumps(a), pickle.dumps(b)):
        assert b"1111111111" not in snapshot
        assert b"2222222222" not in snapshot


def test_request_intent_constructor_cannot_supply_derived_fields():
    with pytest.raises(TypeError):
        CreateAnnualIncomeSummaryRequestIntent(
            utr=UTR, tax_year=TAX_YEAR, scenario="HAPPY_PATH_1", scenario_present=True
        )


def test_request_intent_constructor_validates_utr_and_tax_year_directly():
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        CreateAnnualIncomeSummaryRequestIntent(utr="123456789", tax_year=TAX_YEAR)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        CreateAnnualIncomeSummaryRequestIntent(utr=UTR, tax_year="NOT-A-YEAR")
    valid = CreateAnnualIncomeSummaryRequestIntent(utr=UTR, tax_year=TAX_YEAR)
    assert valid.tax_year == TAX_YEAR
    assert valid.scenario is None
    assert valid.scenario_present is False


def test_request_intent_dataclasses_replace_is_not_a_construction_boundary():
    request = _request()
    with pytest.raises(TypeError):
        replace(request)
    with pytest.raises(TypeError):
        replace(request, scenario_present=True)
    with pytest.raises(TypeError):
        replace(request, utr="1111111111", scenario="HAPPY_PATH_3")


def test_request_intent_replace_rejects_explicit_null_scenario():
    request = _request()
    with pytest.raises(TypeError):
        replace(request, utr="1111111111", scenario=None)

    omitted = build_create_annual_income_summary_request(utr=UTR, tax_year=TAX_YEAR)
    with pytest.raises(TypeError):
        replace(omitted, utr="1111111111")


def test_request_intent_is_frozen_against_arbitrary_field_injection():
    request = _request()
    for attr in ("tax_year", "scenario", "scenario_present"):
        with pytest.raises(AttributeError):
            setattr(request, attr, "forged")
    with pytest.raises(AttributeError):
        del request.scenario_present


def test_exact_observer_accepts_roundtripped_request_intent():
    request = _request()
    candidates = (
        request,
        copy.copy(request),
        copy.deepcopy(request),
        pickle.loads(pickle.dumps(request)),
    )
    for candidate in candidates:
        obs = observe_create_annual_income_summary_response(
            candidate,
            status_code=201,
            content_type="application/json",
            payload=_success_payload(),
        )
        assert isinstance(obs, AnnualIncomeSummaryTestDataObservation)


# ── Scenario omission vs presence ────────────────────────────────────────────


def test_scenario_omission_is_distinct_from_presence():
    omitted = build_create_annual_income_summary_request(utr=UTR, tax_year=TAX_YEAR)
    present = build_create_annual_income_summary_request(
        utr=UTR, tax_year=TAX_YEAR, scenario="HAPPY_PATH_1"
    )
    assert omitted.scenario is None
    assert omitted.scenario_present is False
    assert present.scenario == "HAPPY_PATH_1"
    assert present.scenario_present is True
    assert omitted != present


def test_both_documented_scenarios_are_accepted():
    for scenario in ("HAPPY_PATH_1", "HAPPY_PATH_2"):
        request = build_create_annual_income_summary_request(
            utr=UTR, tax_year=TAX_YEAR, scenario=scenario
        )
        assert request.scenario == scenario
        assert request.scenario_present is True


@pytest.mark.parametrize("scenario", [
    None,                         # explicit JSON null
    "HAPPY_PATH_3",               # undocumented identifier
    "",                           # empty
    " HAPPY_PATH_1",              # leading whitespace
    "HAPPY_PATH_1 ",              # trailing whitespace
    "happy_path_1",               # wrong case
    "НAPPY_PATH_1",               # Cyrillic lookalike
    "ＨAPPY_PATH_1",              # full-width lookalike
    b"HAPPY_PATH_1",              # bytes
    True,                         # bool
    123,                          # int
    ["HAPPY_PATH_1"],             # list
    _StrSubclass("HAPPY_PATH_1"), # subclass
])
def test_malformed_scenario_is_rejected(scenario):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        build_create_annual_income_summary_request(
            utr=UTR, tax_year=TAX_YEAR, scenario=scenario
        )


def test_scenario_direct_constructor_rejects_malformed_value():
    # ``scenario=None`` is now an explicit JSON null at the direct construction
    # boundary too; omission is available only via the private sentinel default.
    for bad in (
        None, "HAPPY_PATH_3", "", " HAPPY_PATH_1", _StrSubclass("HAPPY_PATH_1"),
    ):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            CreateAnnualIncomeSummaryRequestIntent(utr=UTR, tax_year=TAX_YEAR, scenario=bad)


# ── UTR and tax-year validation ──────────────────────────────────────────────


@pytest.mark.parametrize("utr", [
    "123456789",          # nine digits
    "12345678901",        # eleven digits
    "123456789a",         # non-digit
    "12345-6789",         # separator
    "１２３４５６７８９０",   # full-width Unicode digits
    "٠١٢٣٤٥٦٧٨٩",         # Arabic-Indic Unicode digits
    "",                    # empty
    " 123456789",          # whitespace
    "1234567890\n",
])
def test_malformed_utr_is_rejected(utr):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        build_create_annual_income_summary_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("utr", [1234567890, None, True, b"0123456789", ["0123456789"]])
def test_non_string_utr_is_rejected(utr):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        build_create_annual_income_summary_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("tax_year", [
    "2023/24", "2023-2", "202-24", "202324", "2023_24", "ABCD-24", "2023-٢٤", "", None, 2023,
])
def test_malformed_tax_year_is_rejected(tax_year):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        build_create_annual_income_summary_request(utr=UTR, tax_year=tax_year)


def test_validation_failures_are_constant_and_non_echoing():
    for bad_utr in ("999999999X", "12345678901"):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError) as exc:
            build_create_annual_income_summary_request(utr=bad_utr, tax_year=TAX_YEAR)
        assert bad_utr not in str(exc.value)

    with pytest.raises(HMRCPayeTestSupportIncomeContractError) as exc:
        build_create_annual_income_summary_request(utr=UTR, tax_year="NOT-A-YEAR")
    assert "NOT-A-YEAR" not in str(exc.value)

    with pytest.raises(HMRCPayeTestSupportIncomeContractError) as exc:
        build_create_annual_income_summary_request(utr=UTR, tax_year=TAX_YEAR, scenario="HAPPY_PATH_3")
    assert "HAPPY_PATH_3" not in str(exc.value)


# ── Network-inert / no transport / no downstream evidence surface ───────────


def test_module_imports_no_network_transport_or_subprocess():
    path = Path("reserved/providers/hmrc_paye_test_support_income_contract.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots.isdisjoint({
        "requests", "httpx", "urllib3", "socket", "http", "subprocess",
        "aiohttp", "flask", "gunicorn",
    })
    assert "http_boundary" not in imported_roots


def test_module_source_has_no_production_origin_or_downstream_evidence_surface():
    source = Path("reserved/providers/hmrc_paye_test_support_income_contract.py").read_text(encoding="utf-8")
    for forbidden in (
        "https://api.service.hmrc.gov.uk",
        "PayeEvidence",
        "urlopen",
        "http.client",
    ):
        assert forbidden not in source


# ── Required top-level containers and shapes ─────────────────────────────────


def test_empty_containers_are_shape_valid_but_unverified():
    obs = _observe()
    assert isinstance(obs, AnnualIncomeSummaryTestDataObservation)
    assert obs.employments == ()
    assert obs.pensions_benefits.absent_fields == {
        "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
        "jobseekersAllowance", "seissNetPaid",
    }
    assert obs.pensions_benefits.present_fields == frozenset()
    assert obs.completeness == "UNVERIFIED"


@pytest.mark.parametrize("payload", [
    {},
    {"employments": []},
    {"pensionsAnnuitiesAndOtherStateBenefits": {}},
])
def test_missing_required_container_is_rejected(payload):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_payload_must_be_exact_builtin_dict():
    for payload in ([], "{}", 1, None, OrderedDict(), MappingProxyType({})):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=payload)


def test_employments_must_be_exact_builtin_list():
    for value in ((), "[]", OrderedDict(), None):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=_success_payload(employments=value))


def test_employment_items_must_be_exact_builtin_dicts():
    for item in (OrderedDict(), ["x"], None, 1):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload={"employments": [item], "pensionsAnnuitiesAndOtherStateBenefits": {}})


def test_benefits_container_must_be_exact_builtin_dict():
    for value in ([], "{}", None):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=_success_payload(pensionsAnnuitiesAndOtherStateBenefits=value))


def test_multiple_employments_are_retained_without_identity_or_join_authority():
    payload = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": Decimal("100.00")},
        {"employerPayeReference": "123/AB45678", "payFromEmployment": 250},
    ])
    obs = _observe(payload=payload)
    assert len(obs.employments) == 2
    assert obs.employments[0].employer_paye_reference == "267/LS500"
    assert obs.employments[0].pay_from_employment == Decimal("100.00")
    assert obs.employments[1].employer_paye_reference == "123/AB45678"
    assert obs.employments[1].pay_from_employment == 250


def test_employment_required_members_are_enforced():
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=_success_payload(employments=[{"payFromEmployment": 1}]))
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=_success_payload(employments=[{"employerPayeReference": "267/LS500"}]))


# ── Benefits presence / absence / null ───────────────────────────────────────


def test_benefit_optional_presence_and_absence_never_coerced_to_zero():
    payload = _success_payload(pensionsAnnuitiesAndOtherStateBenefits={
        "incapacityBenefit": Decimal("12.34"),
        "jobseekersAllowance": 0,
    })
    obs = _observe(payload=payload)
    benefits = obs.pensions_benefits
    assert benefits.incapacity_benefit == Decimal("12.34")
    assert benefits.jobseekers_allowance == 0
    assert benefits.other_pensions_and_retirement_annuities is None
    assert benefits.seiss_net_paid is None
    assert benefits.present_fields == {"incapacityBenefit", "jobseekersAllowance"}
    assert benefits.absent_fields == {
        "otherPensionsAndRetirementAnnuities", "seissNetPaid",
    }


@pytest.mark.parametrize("name", [
    "otherPensionsAndRetirementAnnuities",
    "incapacityBenefit",
    "jobseekersAllowance",
    "seissNetPaid",
])
def test_explicit_null_benefit_is_rejected(name):
    payload = _success_payload(pensionsAnnuitiesAndOtherStateBenefits={name: None})
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


# ── Number boundary ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("value, expected", [
    (0, 0),
    (250, 250),
    (-50, -50),
    (Decimal("123.45"), Decimal("123.45")),
    (Decimal("-123.45"), Decimal("-123.45")),
])
def test_exact_int_and_decimal_are_retained(value, expected):
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": value,
    }])
    obs = _observe(payload=payload)
    assert obs.employments[0].pay_from_employment == expected


def test_negative_zero_is_retained_without_sign_or_exponent_change():
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": Decimal("-0.000"),
    }])
    obs = _observe(payload=payload)
    retained = obs.employments[0].pay_from_employment
    assert str(retained) == "-0.000"
    assert retained.as_tuple().sign == 1
    assert retained.as_tuple().exponent == -3


@pytest.mark.parametrize("value", [
    True, False,            # bool-as-number
    1.5, -0.0,              # float
    "100",                  # string
    None,                   # null
])
def test_non_int_non_decimal_number_is_rejected(value):
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": value,
    }])
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_numeric_subclasses_are_rejected():
    class _IntEnum(IntEnum):
        X = 5

    for value in (_IntSubclass(5), _DecimalSubclass("1.5"), Fraction(1, 2), _IntEnum.X):
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=payload)


@pytest.mark.parametrize("value", [
    Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"),
])
def test_non_finite_decimal_is_rejected(value):
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": value,
    }])
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_reserved_number_magnitude_boundary():
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": 10 ** 18,
    }])
    _observe(payload=payload)  # boundary accepted

    for value in (10 ** 18 + 1, -(10 ** 18 + 1)):
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=payload)


def test_reserved_decimal_magnitude_and_scale_boundaries():
    for value in (Decimal("1e18"), Decimal("-1e18"), Decimal("0.123456789012")):
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        _observe(payload=payload)

    for value in (Decimal("1000000000000000001"), Decimal("0.1234567890123")):
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(payload=payload)


# ── String values: empty/whitespace accepted, schema-valid but unverified ───


@pytest.mark.parametrize("paye", ["", " ", "   "])
def test_empty_and_whitespace_employer_paye_reference_is_schema_valid(paye):
    payload = _success_payload(employments=[{
        "employerPayeReference": paye, "payFromEmployment": 1,
    }])
    obs = _observe(payload=payload)
    assert obs.employments[0].employer_paye_reference == paye


@pytest.mark.parametrize("paye", [1, None, True, ["x"]])
def test_non_string_employer_paye_reference_is_rejected(paye):
    payload = _success_payload(employments=[{
        "employerPayeReference": paye, "payFromEmployment": 1,
    }])
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


@pytest.mark.parametrize("paye", [
    "\u200b",          # zero-width space (Cf)
    "a\u200bb",        # embedded zero-width space
    "\t",              # tab (Cc)
    "\x85",            # next-line control (Cc)
    "\ud800",          # lone high surrogate (Cs)
])
def test_category_c_employer_paye_reference_is_rejected_through_parsing(paye):
    payload = _success_payload(employments=[{
        "employerPayeReference": paye, "payFromEmployment": 1,
    }])
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


@pytest.mark.parametrize("paye", [
    "\u200b", "a\u200bb", "\t", "\x85", "\ud800",
])
def test_category_c_employer_paye_reference_is_rejected_direct(paye):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomeEmploymentObservation(
            employer_paye_reference=paye, pay_from_employment=1,
        )


@pytest.mark.parametrize("paye", [
    "\u200b", "a\u200bb", "\t", "\x85", "\ud800",
])
def test_category_c_employer_paye_reference_is_rejected_through_replace(paye):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_employment_item_obs(), employer_paye_reference=paye)


# ── Unknown names: accepted without touching hostile values ─────────────────


def test_bounded_safe_unknown_names_accepted_without_touching_values():
    payload = _success_payload()
    payload["futureField"] = _HostileValue()
    payload["employments"].append({
        "employerPayeReference": "267/LS500",
        "payFromEmployment": 1,
        "extensionField": _HostileValue(),
    })
    payload["pensionsAnnuitiesAndOtherStateBenefits"]["extraBenefit"] = _HostileValue()

    obs = _observe(payload=payload)
    assert obs.unknown_names == {"futureField"}
    assert obs.employments[0].unknown_names == {"extensionField"}
    assert obs.pensions_benefits.unknown_names == {"extraBenefit"}


# ── Unsafe / malformed / excessive keys rejected ────────────────────────────


def test_non_string_and_mixed_keys_are_rejected():
    payload = _success_payload()
    payload[1] = "x"
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def _key_level_observe_kwargs(key, level):
    if level == "top":
        payload = _success_payload()
        payload[key] = _HostileValue()
        return {"payload": payload}
    if level == "employment":
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500",
            "payFromEmployment": 1,
            key: _HostileValue(),
        }])
        return {"payload": payload}
    if level == "benefits":
        payload = _success_payload(pensionsAnnuitiesAndOtherStateBenefits={
            key: _HostileValue(),
        })
        return {"payload": payload}
    raise AssertionError(f"unknown level {level!r}")


def _level_unknown_names(obs, level):
    if level == "top":
        return obs.unknown_names
    if level == "employment":
        return obs.employments[0].unknown_names
    if level == "benefits":
        return obs.pensions_benefits.unknown_names
    raise AssertionError(f"unknown level {level!r}")


@pytest.mark.parametrize("key", [
    "\x85", "\x9f", "\u200e", "\u200b", "\ud800", "\udfff",
    "\ue000", "\uf8ff", "\ufdd0", "\uffff", "\u0378",
])
@pytest.mark.parametrize("level", ["top", "employment", "benefits"])
def test_unsafe_unicode_key_names_are_rejected_at_every_level(key, level):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(**_key_level_observe_kwargs(key, level))


@pytest.mark.parametrize("key", [
    "café", "na\u00efve", "e\u0301tude", "\u4e2d\u6587", "\U0001f600",
    "field name", "a\u00a0b", "\u2028separator",
])
@pytest.mark.parametrize("level", ["top", "employment", "benefits"])
def test_safe_international_key_names_are_retained_at_every_level(key, level):
    obs = _observe(**_key_level_observe_kwargs(key, level))
    assert key in _level_unknown_names(obs, level)


def test_oversized_key_is_rejected():
    payload = _success_payload()
    payload["x" * 257] = _HostileValue()
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_empty_key_is_rejected():
    payload = _success_payload()
    payload[""] = _HostileValue()
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_excessive_unknown_keys_are_rejected():
    payload = _success_payload()
    for index in range(33):
        payload[f"future_{index}"] = _HostileValue()
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_excessive_object_members_are_rejected():
    payload = _success_payload()
    for index in range(65):
        payload[f"field_{index}"] = _HostileValue()
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


def test_excessive_employments_are_rejected():
    payload = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": 1}
    ] * 10_001)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(payload=payload)


# ── Non-201 fails closed as unclassified ─────────────────────────────────────


@pytest.mark.parametrize("status_code", [200, 202, 204, 301, 400, 401, 403, 404, 429, 500, 503])
def test_every_non_201_status_fails_closed(status_code):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(status_code=status_code)


def test_non_201_body_is_never_parsed_echoed_or_retained():
    secret = "NON-201-SECRET-BODY"
    with pytest.raises(HMRCPayeTestSupportIncomeContractError) as exc:
        _observe(status_code=500, payload={"error": secret})
    assert secret not in str(exc.value)

    with pytest.raises(HMRCPayeTestSupportIncomeContractError) as exc:
        _observe(status_code=500, payload=_HostileValue())
    assert "undocumented HTTP status" in str(exc.value)


def test_non_201_is_not_turned_into_success_or_no_data():
    # A non-201 must never yield an observation, empty or otherwise.
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(status_code=404, payload={})


def test_status_code_must_be_exact_integer():
    for status_code in (True, False, "201", 201.0):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(status_code=status_code)


def test_success_requires_exact_json_content_type():
    for content_type in (
        "application/json; charset=utf-8",
        "text/json",
        "application/vnd.hmrc.2.1+json",
        "application/xml",
    ):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            _observe(content_type=content_type)


# ── Immutability ─────────────────────────────────────────────────────────────


def test_observations_are_frozen_and_immutable():
    obs = _observe(payload=_success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": Decimal("1.00"),
    }], pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": 0}))

    with pytest.raises(AttributeError):
        obs.employments = ()
    with pytest.raises(AttributeError):
        obs.employments[0].pay_from_employment = 99
    with pytest.raises(AttributeError):
        obs.pensions_benefits.incapacity_benefit = 1
    assert isinstance(obs.employments, tuple)
    assert isinstance(obs.unknown_names, frozenset)
    assert isinstance(obs.pensions_benefits.present_fields, frozenset)


def _employment_item_obs(paye="267/LS500", pay=Decimal("1.00")):
    return AnnualIncomeEmploymentObservation(
        employer_paye_reference=paye, pay_from_employment=pay
    )


def _benefits_obs():
    return AnnualIncomePensionsBenefitsObservation(
        incapacity_benefit=0,
        present_fields=frozenset({"incapacityBenefit"}),
        absent_fields=frozenset({
            "otherPensionsAndRetirementAnnuities", "jobseekersAllowance", "seissNetPaid",
        }),
    )


def _annual_obs():
    return _observe(payload=_success_payload(
        employments=[{"employerPayeReference": "267/LS500",
                      "payFromEmployment": Decimal("1.00")}],
        pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": 0},
    ))


def test_employment_item_direct_constructor_rejects_mutable_or_invalid_state():
    for bad_names in (["x"], {"x"}, ("x",), frozenset({"\x85"})):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            AnnualIncomeEmploymentObservation(
                employer_paye_reference="267/LS500", pay_from_employment=1,
                unknown_names=bad_names,
            )
    for bad_pay in (1.5, "1", True, None):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            AnnualIncomeEmploymentObservation(
                employer_paye_reference="267/LS500", pay_from_employment=bad_pay,
            )
    for bad_ref in (1, None, True, ["x"]):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            AnnualIncomeEmploymentObservation(
                employer_paye_reference=bad_ref, pay_from_employment=1
            )


def test_benefits_direct_constructor_enforces_coherence():
    base_absent = frozenset({
        "otherPensionsAndRetirementAnnuities", "jobseekersAllowance", "seissNetPaid",
    })
    present = frozenset({"incapacityBenefit"})

    for bad in (["incapacityBenefit"], {"incapacityBenefit"}):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            AnnualIncomePensionsBenefitsObservation(
                incapacity_benefit=0, present_fields=bad, absent_fields=base_absent,
            )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomePensionsBenefitsObservation(
            incapacity_benefit=0,
            present_fields=present,
            absent_fields=frozenset({"incapacityBenefit", "jobseekersAllowance", "seissNetPaid"}),
        )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomePensionsBenefitsObservation(
            incapacity_benefit=None, present_fields=present, absent_fields=base_absent,
        )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomePensionsBenefitsObservation(
            other_pensions_and_retirement_annuities=1,
            present_fields=present,
            absent_fields=base_absent,
        )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomePensionsBenefitsObservation(
            incapacity_benefit=0, present_fields=present, absent_fields=base_absent,
            unknown_names=["x"],
        )


def test_annual_summary_direct_constructor_enforces_coherence():
    with pytest.raises(TypeError):
        AnnualIncomeSummaryTestDataObservation()
    with pytest.raises(TypeError):
        AnnualIncomeSummaryTestDataObservation(
            employments=(), pensions_benefits=_benefits_obs())


def test_dataclasses_replace_cannot_create_incoherent_observation():
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_employment_item_obs(), unknown_names=["x"])
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_employment_item_obs(), pay_from_employment=1.5)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_benefits_obs(), present_fields=frozenset())
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_benefits_obs(), unknown_names=["x"])
    with pytest.raises((TypeError, HMRCPayeTestSupportIncomeContractError)):
        replace(_annual_obs(), completeness="VERIFIED")
    with pytest.raises((TypeError, HMRCPayeTestSupportIncomeContractError)):
        replace(_annual_obs(), employments=[_employment_item_obs()])


def test_unknown_names_must_be_disjoint_from_documented_names():
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomeEmploymentObservation(
            employer_paye_reference="267/LS500", pay_from_employment=1,
            unknown_names=frozenset({"employerPayeReference"}),
        )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomePensionsBenefitsObservation(
            incapacity_benefit=0,
            present_fields=frozenset({"incapacityBenefit"}),
            absent_fields=frozenset({
                "otherPensionsAndRetirementAnnuities",
                "jobseekersAllowance",
                "seissNetPaid",
            }),
            unknown_names=frozenset({"incapacityBenefit"}),
        )
    obs = _annual_obs()
    object.__setattr__(obs, "unknown_names", frozenset({"employments"}))
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        validate_annual_income_summary_observation(obs)


def test_unknown_names_disjointness_enforced_through_replace():
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(
            _employment_item_obs(),
            unknown_names=frozenset({"employerPayeReference"}),
        )
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_benefits_obs(), unknown_names=frozenset({"incapacityBenefit"}))
    with pytest.raises((TypeError, HMRCPayeTestSupportIncomeContractError)):
        replace(_annual_obs(), unknown_names=frozenset({"employments"}))


@pytest.mark.parametrize("bad_names", [
    frozenset({_StrSubclass("future")}),
    frozenset({"\u200b"}),
    frozenset({"x" * 257}),
    frozenset({f"future_{i}" for i in range(33)}),
    frozenset({1}),
])
def test_employment_unknown_names_other_invalid_forms_rejected_at_construction(bad_names):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        AnnualIncomeEmploymentObservation(
            employer_paye_reference="267/LS500", pay_from_employment=1,
            unknown_names=bad_names,
        )


@pytest.mark.parametrize("bad_names", [
    frozenset({_StrSubclass("future")}),
    frozenset({"\u200b"}),
    frozenset({"x" * 257}),
    frozenset({f"future_{i}" for i in range(33)}),
    frozenset({1}),
])
def test_employment_unknown_names_other_invalid_forms_rejected_at_replace(bad_names):
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        replace(_employment_item_obs(), unknown_names=bad_names)


def test_observation_copy_deepcopy_and_pickle_preserve_coherence():
    obs = _annual_obs()
    for candidate in (copy.copy(obs), copy.deepcopy(obs), pickle.loads(pickle.dumps(obs))):
        assert candidate == obs
        assert hash(candidate) == hash(obs)
        assert type(candidate) is AnnualIncomeSummaryTestDataObservation
        assert type(candidate.employments) is tuple
        assert type(candidate.unknown_names) is frozenset
        assert type(candidate.pensions_benefits) is AnnualIncomePensionsBenefitsObservation
        with pytest.raises(AttributeError):
            candidate.employments = ()


def test_observations_do_not_retain_raw_mappings_or_unknown_values():
    obs = _annual_obs()
    assert set(vars(obs)) == {
        "request", "_request_binding", "_source_binding", "tax_year", "scenario",
        "scenario_present", "status_code", "employments", "pensions_benefits",
        "unknown_names", "completeness", "_observation_integrity",
    }
    assert set(vars(obs.pensions_benefits)) == {
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "jobseekers_allowance", "seiss_net_paid", "present_fields",
        "absent_fields", "unknown_names",
    }
    assert set(vars(obs.employments[0])) == {
        "employer_paye_reference", "pay_from_employment", "unknown_names",
    }
    for container in (obs.pensions_benefits, obs.employments[0]):
        for value in vars(container).values():
            assert not isinstance(value, (dict, list, set))


# ── Request intent must be an exact instance ────────────────────────────────


def test_observe_requires_exact_request_intent_instance():
    for bad_request in (None, {}, "request", object()):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            observe_create_annual_income_summary_response(
                bad_request,
                status_code=201,
                content_type="application/json",
                payload=_success_payload(),
            )


def test_observe_rejects_request_intent_subclass():
    class _SubclassIntent(CreateAnnualIncomeSummaryRequestIntent):
        pass

    subclass = _SubclassIntent(utr=UTR, tax_year=TAX_YEAR)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        observe_create_annual_income_summary_response(
            subclass,
            status_code=201,
            content_type="application/json",
            payload=_success_payload(),
        )


# ── Exact request/response provenance and adversarial validation ─────────────


def test_omitted_and_both_scenarios_survive_request_to_observation_distinctly():
    requests = (
        build_create_annual_income_summary_request(utr=UTR, tax_year=TAX_YEAR),
        _request(scenario="HAPPY_PATH_1"),
        _request(scenario="HAPPY_PATH_2"),
    )
    observed = [_observe(request=request) for request in requests]
    assert [(item.scenario_present, item.scenario) for item in observed] == [
        (False, None), (True, "HAPPY_PATH_1"), (True, "HAPPY_PATH_2")]
    assert len(set(observed)) == 3
    assert all(validate_annual_income_summary_observation(item) is item for item in observed)


def test_cross_request_wholesale_relabelling_fails_even_with_coordinated_swaps():
    a = _observe(request=_request(tax_year="2023-24", scenario="HAPPY_PATH_1"))
    b = _observe(request=_request(tax_year="2024-25", scenario="HAPPY_PATH_2"))
    for name in (
        "request", "_request_binding", "_source_binding", "tax_year", "scenario",
        "scenario_present", "_observation_integrity",
    ):
        object.__setattr__(a, name, object.__getattribute__(b, name))
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        validate_annual_income_summary_observation(a)


@pytest.mark.parametrize("index", range(4, 14))
def test_fixed_request_descriptor_substitution_fails(index):
    request = _request()
    name = "_CreateAnnualIncomeSummaryRequestIntent__binding"
    binding = object.__getattribute__(request, name)
    altered = binding[:index] + ("forged",) + binding[index + 1:]
    object.__setattr__(request, name, altered)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        _observe(request=request)


def test_every_nested_semantic_category_is_integrity_bound():
    payload = _success_payload(
        employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": Decimal("1.20"),
            "futureEmployment": _HostileValue(),
        }],
        pensionsAnnuitiesAndOtherStateBenefits={
            "incapacityBenefit": 2, "futureBenefit": _HostileValue(),
        },
        futureTop=_HostileValue(),
    )
    mutations = (
        ("employment", "employer_paye_reference", "changed"),
        ("employment", "pay_from_employment", Decimal("1.21")),
        ("employment", "unknown_names", frozenset({"otherEmployment"})),
        ("benefits", "incapacity_benefit", 3),
        ("benefits", "present_fields", frozenset()),
        ("benefits", "absent_fields", frozenset()),
        ("benefits", "unknown_names", frozenset({"otherBenefit"})),
        ("outer", "employments", ()),
        ("outer", "unknown_names", frozenset({"otherTop"})),
        ("outer", "completeness", "VERIFIED"),
    )
    for level, name, replacement in mutations:
        obs = _observe(payload=payload)
        target = (obs.employments[0] if level == "employment" else
                  obs.pensions_benefits if level == "benefits" else obs)
        object.__setattr__(target, name, replacement)
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            validate_annual_income_summary_observation(obs)


def test_low_level_clone_extra_missing_subclass_and_shadow_state_fail_closed():
    authentic = _annual_obs()
    for mutate in ("missing", "extra", "shadow"):
        forged = object.__new__(AnnualIncomeSummaryTestDataObservation)
        for name, value in vars(authentic).items():
            object.__setattr__(forged, name, value)
        if mutate == "missing":
            object.__delattr__(forged, "status_code")
        elif mutate == "extra":
            object.__setattr__(forged, "validate_annual_income_summary_observation", _HostileValue())
        else:
            object.__setattr__(forged, "__dataclass_fields__", _HostileValue())
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            validate_annual_income_summary_observation(forged)

    class Subclass(AnnualIncomeSummaryTestDataObservation):
        pass
    forged_subclass = object.__new__(Subclass)
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        validate_annual_income_summary_observation(forged_subclass)


def test_hostile_instance_hooks_are_not_invoked_before_exact_state_rejection():
    obs = _annual_obs()
    for name in ("request", "status_code", "employments", "pensions_benefits",
                 "unknown_names", "completeness", "_observation_integrity"):
        candidate = _annual_obs()
        object.__setattr__(candidate, name, _HostileValue())
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            validate_annual_income_summary_observation(candidate)
    assert validate_annual_income_summary_observation(obs) is obs


@pytest.mark.parametrize("operation", [
    lambda value: repr(value),
    lambda value: hash(value),
    lambda value: value == _annual_obs(),
    lambda value: copy.copy(value),
    lambda value: copy.deepcopy(value),
    lambda value: pickle.dumps(value),
])
def test_observation_protocols_validate_before_hostile_hook_dispatch(operation):
    candidate = _annual_obs()
    object.__setattr__(candidate, "scenario", _HostileValue())
    with pytest.raises(HMRCPayeTestSupportIncomeContractError):
        operation(candidate)


def _clone_nested(value, cls):
    clone = object.__new__(cls)
    for name, item in vars(value).items():
        object.__setattr__(clone, name, item)
    return clone


def _nested_protocol_operations(candidate, valid):
    return (
        lambda: hash(candidate), lambda: repr(candidate),
        lambda: candidate == valid, lambda: valid == candidate,
        lambda: copy.copy(candidate), lambda: copy.deepcopy(candidate),
        lambda: pickle.dumps(candidate),
    )


@pytest.mark.parametrize("kind", ["employment", "benefits"])
@pytest.mark.parametrize("mutation", ["hostile", "missing", "extra"])
def test_nested_protocols_reject_low_level_malformed_exact_state(kind, mutation):
    valid = _employment_item_obs() if kind == "employment" else _benefits_obs()
    cls = type(valid)
    for operation_index in range(7):
        candidate = _clone_nested(valid, cls)
        first_name = next(iter(vars(candidate)))
        if mutation == "hostile":
            object.__setattr__(candidate, first_name, _HostileValue())
        elif mutation == "missing":
            object.__delattr__(candidate, first_name)
        else:
            object.__setattr__(candidate, "unexpected_state", _HostileValue())
        operation = _nested_protocol_operations(candidate, valid)[operation_index]
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            operation()


@pytest.mark.parametrize("kind", ["employment", "benefits"])
def test_nested_protocols_reject_subclass_state_in_both_equality_directions(kind):
    valid = _employment_item_obs() if kind == "employment" else _benefits_obs()
    base = type(valid)
    subclass = type("NestedSubclass", (base,), {})
    candidate = _clone_nested(valid, subclass)
    for operation in _nested_protocol_operations(candidate, valid):
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            operation()


def test_valid_nested_protocols_preserve_ordinary_value_semantics():
    for value in (_employment_item_obs(), _benefits_obs()):
        assert value == copy.copy(value) == copy.deepcopy(value)
        assert hash(value) == hash(copy.copy(value))
        restored = pickle.loads(pickle.dumps(value))
        assert type(restored) is type(value)
        assert restored == value


class _CountedHostile:
    calls = 0

    @classmethod
    def _touched(cls):
        cls.calls += 1
        raise RuntimeError("attacker hook touched")

    __repr__ = lambda self: self._touched()
    __str__ = lambda self: self._touched()
    __hash__ = lambda self: self._touched()
    __bool__ = lambda self: self._touched()
    __iter__ = lambda self: self._touched()
    __eq__ = lambda self, other: self._touched()


class _CountedHostileName(str):
    calls = 0

    def __hash__(self):
        type(self).calls += 1
        return super().__hash__()

    def __eq__(self, other):
        type(self).calls += 1
        return super().__eq__(other)


def test_restore_rejects_hostile_fields_before_any_attacker_hook():
    obs = _annual_obs()
    binding = object.__getattribute__(obs.request, "_CreateAnnualIncomeSummaryRequestIntent__binding")
    valid_args = (binding, obs.employments, obs.pensions_benefits,
                  obs.unknown_names, obs.completeness)
    hostile_name = _CountedHostileName("futureTop")
    hostile_names = frozenset({hostile_name})
    _CountedHostileName.calls = 0
    cases = (
        valid_args[:-1] + (_CountedHostile(),),
        (binding, _CountedHostile(), *valid_args[2:]),
        (binding, (_CountedHostile(),), *valid_args[2:]),
        (binding, valid_args[1], _CountedHostile(), *valid_args[3:]),
        (binding, valid_args[1], valid_args[2], _CountedHostile(), valid_args[4]),
        (binding, valid_args[1], valid_args[2], hostile_names, valid_args[4]),
    )
    for args in cases:
        _CountedHostile.calls = 0
        _CountedHostileName.calls = 0
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            income_contract._restore_observation(*args)
        assert _CountedHostile.calls == 0
        assert _CountedHostileName.calls == 0


def test_request_properties_and_protocols_fail_closed_after_low_level_mutation():
    request = _request()
    object.__setattr__(
        request, "_CreateAnnualIncomeSummaryRequestIntent__binding", _HostileValue()
    )
    operations = (
        lambda: request.tax_year, lambda: request.scenario,
        lambda: request.scenario_present, lambda: repr(request),
        lambda: hash(request), lambda: copy.copy(request),
        lambda: copy.deepcopy(request), lambda: pickle.dumps(request),
    )
    for operation in operations:
        with pytest.raises(HMRCPayeTestSupportIncomeContractError):
            operation()


def test_observation_pickle_is_validated_utr_free_reconstruction():
    obs = _annual_obs()
    encoded = pickle.dumps(obs)
    assert UTR.encode("ascii") not in encoded
    restored = pickle.loads(encoded)
    assert validate_annual_income_summary_observation(restored) is restored
    assert restored == obs


# ── No cross-endpoint join / double-count / activation claims ───────────────


def test_no_cross_endpoint_join_or_double_count_surface():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": Decimal("100.00")},
    ]))
    assert obs.completeness == "UNVERIFIED"
    assert obs.tax_year == TAX_YEAR
    assert obs.scenario == "HAPPY_PATH_1"
    assert obs.scenario_present is True
    for container in (obs.pensions_benefits, obs.employments[0]):
        for name in vars(container):
            lowered = name.lower()
            assert "join" not in lowered
            assert "canonical" not in lowered
            assert "mapping" not in lowered
            assert "dedupe" not in lowered
            assert "double" not in lowered
            assert "tax" not in lowered
            assert "cash" not in lowered
            assert "total" not in lowered
