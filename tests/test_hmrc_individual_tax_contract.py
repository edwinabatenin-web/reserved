"""Synthetic, network-free HMRC Individual Tax 1.1 literal contract tests."""

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

from reserved.providers.hmrc_individual_tax_contract import (
    HMRC_INDIVIDUAL_TAX_400_CODES,
    HMRC_INDIVIDUAL_TAX_401_CODES,
    HMRC_INDIVIDUAL_TAX_404_CODES,
    HMRC_INDIVIDUAL_TAX_ACCEPT,
    HMRC_INDIVIDUAL_TAX_API_VERSION,
    HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES,
    HMRC_INDIVIDUAL_TAX_HTTP_METHOD,
    HMRC_INDIVIDUAL_TAX_JSON_CONTENT_TYPE,
    HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE,
    HMRC_INDIVIDUAL_TAX_SCOPE,
    EmploymentItemObservation,
    HMRCIndividualTaxContractError,
    IndividualTaxAnnualSummaryObservation,
    IndividualTaxErrorObservation,
    IndividualTaxRequestIntent,
    PensionsBenefitsObservation,
    RefundsObservation,
    _rebuild_annual_summary,
    _rebuild_employment_item,
    _rebuild_error,
    _rebuild_individual_tax_request_intent,
    _rebuild_pensions_benefits,
    _rebuild_refunds,
    build_individual_tax_request,
    observe_individual_tax_response,
)
from reserved.providers.http_boundary import ProviderRequest

UTR = "0123456789"
TAX_YEAR = "2023-24"


def _request(utr=UTR, tax_year=TAX_YEAR):
    return build_individual_tax_request(utr=utr, tax_year=tax_year)


def _success_payload(**overrides):
    payload = {
        "employments": [],
        "pensionsAnnuitiesAndOtherStateBenefits": {},
        "refunds": {},
    }
    payload.update(overrides)
    return payload


_MISSING = object()


def _observe(payload=_MISSING, *, status_code=200, content_type="application/json", request=None):
    if payload is _MISSING:
        payload = _success_payload()
    return observe_individual_tax_response(
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


class _IntSubclass(int):
    pass


class _DecimalSubclass(Decimal):
    pass


class _StrSubclass(str):
    pass


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
    pass


# --- Exact constants and request construction ---------------------------------


def test_documented_constants_are_exact():
    assert HMRC_INDIVIDUAL_TAX_API_VERSION == "1.1"
    assert HMRC_INDIVIDUAL_TAX_HTTP_METHOD == "GET"
    assert HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE == (
        "/individual-tax/sa/{utr}/annual-summary/{taxYear}"
    )
    assert HMRC_INDIVIDUAL_TAX_ACCEPT == "application/vnd.hmrc.1.1+json"
    assert HMRC_INDIVIDUAL_TAX_SCOPE == "read:individual-tax"
    assert HMRC_INDIVIDUAL_TAX_JSON_CONTENT_TYPE == "application/json"
    assert HMRC_INDIVIDUAL_TAX_COMPLETENESS == "UNVERIFIED"


def test_documented_status_code_sets_are_exact():
    assert HMRC_INDIVIDUAL_TAX_400_CODES == {"SA_UTR_INVALID", "TAX_YEAR_INVALID"}
    assert HMRC_INDIVIDUAL_TAX_401_CODES == {"UNAUTHORIZED"}
    assert HMRC_INDIVIDUAL_TAX_404_CODES == {"NOT_FOUND"}
    assert set(HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES) == {400, 401, 404}


def test_request_intent_construction_and_exact_redaction():
    request = _request()
    assert type(request) is IndividualTaxRequestIntent
    assert request.tax_year == "2023-24"
    assert repr(request) == "IndividualTaxRequestIntent([REDACTED])"


def test_request_intent_exposes_no_sendable_or_credential_surface():
    request = _request()
    for absent in (
        "utr", "url", "headers", "body", "authorization", "token", "credential",
        "transport", "client", "method", "path", "path_template", "accept",
        "scope", "sandbox_origin", "redacted_path",
    ):
        assert not hasattr(request, absent)
    assert not issubclass(IndividualTaxRequestIntent, ProviderRequest)
    assert not isinstance(request, ProviderRequest)


def test_raw_utr_is_discarded_from_every_retained_state():
    request = _request(utr="9876543210")
    assert not hasattr(request, "utr")
    assert not hasattr(request, "_utr")
    assert not hasattr(request, "__utr")
    assert not hasattr(request, "_IndividualTaxRequestIntent__utr")
    assert "9876543210" not in repr(request)
    assert "9876543210" not in str(request)
    with pytest.raises(AttributeError):
        request.__dict__
    with pytest.raises(TypeError):
        vars(request)

    pickled = pickle.dumps(request)
    assert "9876543210".encode("ascii") not in pickled
    assert "9876543210" not in repr(pickle.loads(pickled))
    assert pickle.loads(pickled).tax_year == TAX_YEAR


def test_request_intent_is_frozen_against_field_injection():
    request = _request()
    with pytest.raises(AttributeError):
        request.tax_year = "2024-25"
    with pytest.raises(AttributeError):
        request.utr = "9999999999"
    with pytest.raises(AttributeError):
        del request.tax_year


def test_request_intent_replace_cannot_forge_retained_state():
    # The intent is not a dataclass, so dataclasses.replace cannot re-enter it.
    with pytest.raises(TypeError):
        replace(_request())
    with pytest.raises(TypeError):
        replace(_request(), tax_year="2024-25")


def test_request_intent_constructor_rejects_derived_field_injection():
    for kwargs in (
        {"method": "POST"},
        {"accept": "text/plain"},
        {"scope": "read:other"},
        {"path_template": "/other/{utr}/{taxYear}"},
        {"sandbox_origin": "https://evil.example"},
        {"url": "https://evil.example"},
        {"headers": {"Authorization": "Bearer x"}},
        {"body": b"x"},
    ):
        with pytest.raises(TypeError):
            IndividualTaxRequestIntent(utr=UTR, tax_year=TAX_YEAR, **kwargs)


def test_request_intent_copy_and_deepcopy_return_the_immutable_instance():
    request = _request()
    assert copy.copy(request) is request
    assert copy.deepcopy(request) is request


def test_request_intent_pickle_revalidates_through_rebuild_boundary():
    request = _request()
    restored = pickle.loads(pickle.dumps(request))
    assert type(restored) is IndividualTaxRequestIntent
    assert restored.tax_year == TAX_YEAR
    reduce_fn, args = request.__reduce__()
    assert reduce_fn is _rebuild_individual_tax_request_intent
    assert args == (TAX_YEAR,)


def test_request_intent_rebuild_rejects_invalid_tax_year():
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_individual_tax_request_intent("NOT-A-YEAR")
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_individual_tax_request_intent(1234)


def test_observe_requires_exact_request_intent_instance():
    for bad_request in (None, {}, "request", object()):
        with pytest.raises(HMRCIndividualTaxContractError):
            observe_individual_tax_response(
                bad_request,
                status_code=200,
                content_type="application/json",
                payload=_success_payload(),
            )


def test_observe_rejects_request_intent_subclass():
    class _SubclassIntent(IndividualTaxRequestIntent):
        pass

    subclass = _SubclassIntent(utr=UTR, tax_year=TAX_YEAR)
    with pytest.raises(HMRCIndividualTaxContractError):
        observe_individual_tax_response(
            subclass,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )


# --- UTR and tax-year validation ----------------------------------------------


@pytest.mark.parametrize("utr", [
    "123456789",          # nine digits
    "12345678901",        # eleven digits
    "123456789a",         # non-digit
    "12345-6789",         # separator
    "+1234567890",        # sign
    "\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff10",  # full-width
    "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",  # Arabic-Indic
    "",                    # empty
    " 123456789",          # leading whitespace
    "1234567890\n",
])
def test_malformed_utr_is_rejected(utr):
    with pytest.raises(HMRCIndividualTaxContractError):
        build_individual_tax_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("utr", [
    1234567890, None, True, b"0123456789", ["0123456789"], _StrSubclass("0123456789"),
])
def test_non_string_or_subclass_utr_is_rejected(utr):
    with pytest.raises(HMRCIndividualTaxContractError):
        build_individual_tax_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("tax_year", [
    "2023/24", "2023-2", "202-24", "202324", "2023_24", "ABCD-24", "2023-\u0662\u0664",
    "", None, 2023, " 2023-24",
])
def test_malformed_tax_year_is_rejected(tax_year):
    with pytest.raises(HMRCIndividualTaxContractError):
        build_individual_tax_request(utr=UTR, tax_year=tax_year)


def test_validation_failures_are_constant_and_non_echoing():
    for bad_utr in ("999999999X", "12345678901"):
        with pytest.raises(HMRCIndividualTaxContractError) as exc:
            build_individual_tax_request(utr=bad_utr, tax_year=TAX_YEAR)
        assert bad_utr not in str(exc.value)

    with pytest.raises(HMRCIndividualTaxContractError) as exc:
        build_individual_tax_request(utr=UTR, tax_year="NOT-A-YEAR")
    assert "NOT-A-YEAR" not in str(exc.value)


# --- Static isolation ---------------------------------------------------------


def test_module_imports_no_network_transport_or_subprocess():
    path = Path("reserved/providers/hmrc_individual_tax_contract.py")
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
    source = Path("reserved/providers/hmrc_individual_tax_contract.py").read_text(encoding="utf-8")
    for forbidden in (
        "https://api.service.hmrc.gov.uk",
        "PayeEvidence",
        "urlopen",
        "http.client",
        "requests",
        "httpx",
    ):
        assert forbidden not in source


def test_module_has_no_transport_credential_or_activation_surface():
    import reserved.providers.hmrc_individual_tax_contract as contract

    for name in (
        "requests", "httpx", "urlopen", "HttpTransport", "GuardedTransport",
        "ProviderRequest", "authorization", "token", "client", "activate",
        "enabled", "production",
    ):
        assert not hasattr(contract, name), name


# --- Required top-level containers and shapes ---------------------------------


def test_empty_containers_are_shape_valid_but_unverified():
    obs = _observe()
    assert isinstance(obs, IndividualTaxAnnualSummaryObservation)
    assert obs.employments == ()
    assert obs.completeness == "UNVERIFIED"
    assert obs.pensions_benefits.present_fields == frozenset()
    assert obs.pensions_benefits.absent_fields == {
        "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
    }
    assert obs.refunds.present_fields == frozenset()
    assert obs.refunds.absent_fields == {"taxRefundedOrSetOff"}


@pytest.mark.parametrize("payload", [
    {},
    {"employments": []},
    {"pensionsAnnuitiesAndOtherStateBenefits": {}},
    {"refunds": {}},
    {"employments": [], "pensionsAnnuitiesAndOtherStateBenefits": {}},
    {"employments": [], "refunds": {}},
    {"pensionsAnnuitiesAndOtherStateBenefits": {}, "refunds": {}},
])
def test_missing_required_container_is_rejected(payload):
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=payload)


def test_payload_must_be_exact_builtin_dict():
    for payload in ([], "{}", 1, None, OrderedDict(), MappingProxyType({})):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=payload)


def test_employments_must_be_exact_builtin_list():
    for value in ((), "[]", OrderedDict(), None, {}, _ListSubclass([])):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(employments=value))


def test_employment_items_must_be_exact_builtin_dicts():
    payload = _success_payload(employments=[OrderedDict(), ["x"], None, 1])
    for item in payload["employments"]:
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(employments=[item]))


def test_benefits_container_must_be_exact_builtin_dict():
    for value in ([], "{}", None, _DictSubclass({})):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(pensionsAnnuitiesAndOtherStateBenefits=value))


def test_refunds_container_must_be_exact_builtin_dict():
    for value in ([], "{}", None, _DictSubclass({})):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(refunds=value))


def test_employments_are_retained_without_identity_or_join_authority():
    payload = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": Decimal("890.35")},
        {"employerPayeReference": "123/AB456", "taxTakenOffPay": 250},
    ])
    obs = _observe(payload=payload)
    assert len(obs.employments) == 2
    assert obs.employments[0].employer_paye_reference == "267/LS500"
    assert obs.employments[0].tax_taken_off_pay == Decimal("890.35")
    assert obs.employments[1].employer_paye_reference == "123/AB456"
    assert obs.employments[1].tax_taken_off_pay == 250


def test_employment_required_members_are_enforced():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[{"taxTakenOffPay": 1}]))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[{"employerPayeReference": "267/LS500"}]))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[{
            "employerPayeReference": "267/LS500", "taxTakenOffPay": None,
        }]))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[{
            "employerPayeReference": None, "taxTakenOffPay": 1,
        }]))


def test_state_pension_lump_sum_reference_is_literal_only():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": Decimal("100.00")},
    ]))
    assert obs.employments[0].employer_paye_reference == "267/LS500"
    assert "267/LS500" not in repr(obs.employments[0])
    # No inferred join/identity/downstream special surface exists.
    for name in vars(obs.employments[0]):
        assert "join" not in name.lower()
        assert "identity" not in name.lower()
        assert "pension" not in name.lower()


# --- Exact numeric boundary ---------------------------------------------------


def test_int_and_decimal_are_retained_exactly():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": 0},
    ], pensionsAnnuitiesAndOtherStateBenefits={
        "otherPensionsAndRetirementAnnuities": Decimal("36.50"),
        "incapacityBenefit": -5,
    }, refunds={"taxRefundedOrSetOff": Decimal("-0.000")}))
    assert obs.employments[0].tax_taken_off_pay == 0
    assert type(obs.employments[0].tax_taken_off_pay) is int
    assert obs.pensions_benefits.other_pensions_and_retirement_annuities == Decimal("36.50")
    assert obs.pensions_benefits.incapacity_benefit == -5
    assert type(obs.pensions_benefits.incapacity_benefit) is int
    refund = obs.refunds.tax_refunded_or_set_off
    assert refund == Decimal("-0.000")
    assert refund.as_tuple().sign == 1
    assert refund.as_tuple().exponent == -3


def test_negative_zero_is_preserved_not_normalised():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": Decimal("-0.000")},
    ]))
    value = obs.employments[0].tax_taken_off_pay
    assert value == 0
    assert value.as_tuple().sign == 1
    assert value.as_tuple().exponent == -3


@pytest.mark.parametrize("bad", [
    True, False, 1.5, "1", Fraction(1, 2), None, [], {},
    _IntSubclass(5), _DecimalSubclass("5"), IntEnum("X", {"A": 1}).A,
])
def test_number_boundary_rejects_non_int_decimal(bad):
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[
            {"employerPayeReference": "267/LS500", "taxTakenOffPay": bad},
        ]))


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_number_boundary_rejects_non_finite_decimal(bad):
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[
            {"employerPayeReference": "267/LS500", "taxTakenOffPay": bad},
        ]))


def test_number_boundary_applies_reserved_magnitude_bounds():
    for bad in (10 ** 18 + 1, -(10 ** 18 + 1)):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(employments=[
                {"employerPayeReference": "267/LS500", "taxTakenOffPay": bad},
            ]))
    for bad in (
        Decimal("1000000000000000001"),
        Decimal("0.0000000000001"),  # 13 fractional places
    ):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(employments=[
                {"employerPayeReference": "267/LS500", "taxTakenOffPay": bad},
            ]))


# --- Optional presence and explicit null --------------------------------------


def test_benefits_optional_presence_is_tracked_distinct_from_zero():
    absent = _observe(payload=_success_payload(
        pensionsAnnuitiesAndOtherStateBenefits={},
    ))
    assert absent.pensions_benefits.other_pensions_and_retirement_annuities is None
    assert absent.pensions_benefits.incapacity_benefit is None
    assert "otherPensionsAndRetirementAnnuities" in absent.pensions_benefits.absent_fields
    assert "incapacityBenefit" in absent.pensions_benefits.absent_fields

    zero = _observe(payload=_success_payload(
        pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": 0},
    ))
    assert zero.pensions_benefits.incapacity_benefit == 0
    assert zero.pensions_benefits.incapacity_benefit is not None
    assert "incapacityBenefit" in zero.pensions_benefits.present_fields
    assert "incapacityBenefit" not in zero.pensions_benefits.absent_fields


def test_refunds_optional_presence_is_tracked_distinct_from_zero():
    absent = _observe(payload=_success_payload(refunds={}))
    assert absent.refunds.tax_refunded_or_set_off is None
    assert "taxRefundedOrSetOff" in absent.refunds.absent_fields

    zero = _observe(payload=_success_payload(refunds={"taxRefundedOrSetOff": 0}))
    assert zero.refunds.tax_refunded_or_set_off == 0
    assert zero.refunds.tax_refunded_or_set_off is not None
    assert "taxRefundedOrSetOff" in zero.refunds.present_fields


def test_explicit_null_fails_closed_in_optional_containers():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(
            pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": None},
        ))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(
            pensionsAnnuitiesAndOtherStateBenefits={
                "otherPensionsAndRetirementAnnuities": None,
            },
        ))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(refunds={"taxRefundedOrSetOff": None}))


# --- Documented string semantics ----------------------------------------------


@pytest.mark.parametrize("value", ["", "   ", "\u00a0"])
def test_employer_paye_reference_empty_and_separator_whitespace_is_schema_valid(value):
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": value, "taxTakenOffPay": 1},
    ]))
    assert obs.employments[0].employer_paye_reference == value


def test_employer_paye_reference_rejects_unsafe_category_c():
    for bad in ["\u202eM\u00fcller", "a\u200bb", "x\x00y", "\t\n"]:
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(payload=_success_payload(employments=[
                {"employerPayeReference": bad, "taxTakenOffPay": 1},
            ]))


def test_employer_paye_reference_preserves_ordinary_unicode_content():
    value = "na\u00efve caf\u00e9 \u2014 100%"
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": value, "taxTakenOffPay": 1},
    ]))
    assert obs.employments[0].employer_paye_reference == value


def test_employer_paye_reference_rejects_oversized():
    bad = "1" * 4097
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[
            {"employerPayeReference": bad, "taxTakenOffPay": 1},
        ]))


@pytest.mark.parametrize("message", ["", "   ", "\t\n"])
def test_error_accepts_empty_and_whitespace_message_as_schema_valid(message):
    result = _observe(
        status_code=404,
        payload={"code": "NOT_FOUND", "message": message},
    )
    assert result.code == "NOT_FOUND"
    assert not hasattr(result, "message")


def test_error_message_is_validated_but_discarded_and_non_echoing():
    obs = _observe(
        payload={"code": "NOT_FOUND", "message": "SECRET-12345"},
        status_code=404,
    )
    assert not hasattr(obs, "message")
    assert "SECRET-12345" not in repr(obs)

    with pytest.raises(HMRCIndividualTaxContractError) as exc:
        _observe(payload={"code": "WRONG", "message": "SECRET-99999"}, status_code=404)
    assert "SECRET-99999" not in str(exc.value)


def test_error_message_rejects_oversized():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(
            status_code=404,
            payload={"code": "NOT_FOUND", "message": "x" * 4097},
        )


# --- Documented error boundary ------------------------------------------------


@pytest.mark.parametrize("status_code, code", [
    (400, "SA_UTR_INVALID"),
    (400, "TAX_YEAR_INVALID"),
    (401, "UNAUTHORIZED"),
    (404, "NOT_FOUND"),
])
def test_documented_error_pairings_are_accepted(status_code, code):
    obs = _observe(payload={"code": code, "message": "detail"}, status_code=status_code)
    assert isinstance(obs, IndividualTaxErrorObservation)
    assert obs.status_code == status_code
    assert obs.code == code


@pytest.mark.parametrize("status_code, code", [
    (400, "NOT_FOUND"),
    (400, "UNAUTHORIZED"),
    (401, "SA_UTR_INVALID"),
    (401, "NOT_FOUND"),
    (404, "UNAUTHORIZED"),
    (404, "SA_UTR_INVALID"),
    (404, "UNKNOWN_CODE"),
])
def test_mismatched_or_unknown_status_code_pairings_are_rejected(status_code, code):
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload={"code": code, "message": "detail"}, status_code=status_code)


def test_http_404_not_found_is_endpoint_no_data_not_zero():
    obs = _observe(payload={"code": "NOT_FOUND", "message": "unavailable"}, status_code=404)
    assert isinstance(obs, IndividualTaxErrorObservation)
    assert obs.code == "NOT_FOUND"
    assert not isinstance(obs, IndividualTaxAnnualSummaryObservation)
    assert not hasattr(obs, "employments")


def test_unknown_404_remains_unclassified_and_fails_closed():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload={"code": "MATCHING_RESOURCE_NOT_FOUND", "message": "x"}, status_code=404)


@pytest.mark.parametrize("status_code", [200, 400, 401, 404])
def test_error_and_success_require_exact_json_content_type(status_code):
    for content_type in (
        "application/json; charset=utf-8",
        "text/json",
        "application/vnd.hmrc.1.1+json",
    ):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(status_code=status_code, content_type=content_type)


def test_undocumented_status_is_rejected():
    for status_code in (201, 204, 300, 500, 503):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(status_code=status_code)


def test_status_code_must_be_exact_integer():
    for status_code in (True, False, "200", 200.0, _IntSubclass(200)):
        with pytest.raises(HMRCIndividualTaxContractError):
            _observe(status_code=status_code)


@pytest.mark.parametrize("payload", [
    {"code": "NOT_FOUND"},
    {"message": "detail"},
    {"code": "NOT_FOUND", "message": None},
    {"code": None, "message": "detail"},
    {"code": "NOT_FOUND", "message": 42},
    {"code": 404, "message": "detail"},
    "NOT_FOUND",
    [],
])
def test_malformed_error_bodies_are_rejected(payload):
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=payload, status_code=404)


# --- Open-schema and hostile-input boundary -----------------------------------


def test_hostile_unknown_values_are_never_inspected_at_any_level():
    hostile = _HostileValue()

    obs = _observe(payload={
        "employments": [{
            "employerPayeReference": "267/LS500",
            "taxTakenOffPay": 1,
            "future_employment": hostile,
        }],
        "pensionsAnnuitiesAndOtherStateBenefits": {"future_benefit": hostile},
        "refunds": {"future_refund": hostile},
        "future_top": hostile,
    })

    assert "future_employment" in obs.employments[0].unknown_names
    assert "future_benefit" in obs.pensions_benefits.unknown_names
    assert "future_refund" in obs.refunds.unknown_names
    assert "future_top" in obs.unknown_names

    error_obs = _observe(
        status_code=404,
        payload={"code": "NOT_FOUND", "message": "x", "future_error": hostile},
    )
    assert "future_error" in error_obs.unknown_names


def test_hostile_value_in_documented_field_is_rejected_without_inspection():
    hostile = _HostileValue()
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[
            {"employerPayeReference": hostile, "taxTakenOffPay": 1},
        ]))


@pytest.mark.parametrize("name", [
    "\x00name", "name\x1f", "\x7f", "\x9f", "a\tb",
    "\ud800", "\udfff", "a\udc00b",   # lone surrogates
    "\ufffe", "\ufdd0",               # noncharacters
    "\u202e", "\u200b", "a\u202eb",   # format controls
    "\ue000", "a\uf8ffb",             # private use
    "\u0378", "a\u0378b",             # unassigned
])
def test_member_names_reject_unsafe_category_c(name):
    top_level = _success_payload()
    top_level[name] = "x"
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=top_level)

    emp = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": 1},
    ])
    emp["employments"][0][name] = "x"
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=emp)


def test_member_names_accept_ordinary_unicode_keys():
    name = "employ\u00e9\u2603_\u65e5"
    payload = _success_payload()
    payload[name] = "x"
    obs = _observe(payload=payload)
    assert name in obs.unknown_names


def test_member_names_reject_non_string_keys_at_every_level():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload={**_success_payload(), 1: "x"})
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(
            pensionsAnnuitiesAndOtherStateBenefits={1: "x"},
        ))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(refunds={1: "x"}))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(status_code=404, payload={"code": "NOT_FOUND", "message": "x", 1: "x"})


def test_member_names_reject_empty_and_oversized():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload={**_success_payload(), "": "x"})
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload={**_success_payload(), "x" * 257: "x"})


def test_object_member_count_and_unknown_key_bounds_are_enforced():
    payload = _success_payload()
    for index in range(65):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=payload)

    payload = _success_payload()
    for index in range(33):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=payload)


def test_employments_exceeding_defensive_bound_are_rejected():
    emp = {"employerPayeReference": "267/LS500", "taxTakenOffPay": 1}
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[emp] * 10001))


def test_container_subclasses_are_rejected_everywhere():
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_DictSubclass(_success_payload()))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=_ListSubclass([])))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(
            pensionsAnnuitiesAndOtherStateBenefits=_DictSubclass({}),
        ))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(refunds=_DictSubclass({})))
    with pytest.raises(HMRCIndividualTaxContractError):
        _observe(payload=_success_payload(employments=[
            _DictSubclass({"employerPayeReference": "267/LS500", "taxTakenOffPay": 1}),
        ]))


# --- Observation immutability, coherence and forgery resistance ---------------


def _employment_item_obs(paye="267/LS500", pay=Decimal("1.00")):
    return EmploymentItemObservation(employer_paye_reference=paye, tax_taken_off_pay=pay)


def _benefits_obs():
    return PensionsBenefitsObservation(
        incapacity_benefit=0,
        present_fields=frozenset({"incapacityBenefit"}),
        absent_fields=frozenset({"otherPensionsAndRetirementAnnuities"}),
    )


def _refunds_obs():
    return RefundsObservation(
        tax_refunded_or_set_off=Decimal("1.00"),
        present_fields=frozenset({"taxRefundedOrSetOff"}),
        absent_fields=frozenset(),
    )


def _annual_obs():
    return IndividualTaxAnnualSummaryObservation(
        employments=(_employment_item_obs(),),
        pensions_benefits=_benefits_obs(),
        refunds=_refunds_obs(),
    )


def _error_obs(status_code=404, code="NOT_FOUND"):
    return IndividualTaxErrorObservation(status_code=status_code, code=code)


def test_observations_are_frozen_and_redacted():
    obs = _annual_obs()
    assert repr(obs) == "IndividualTaxAnnualSummaryObservation([REDACTED])"
    assert repr(obs.employments[0]) == "EmploymentItemObservation([REDACTED])"
    assert repr(obs.pensions_benefits) == "PensionsBenefitsObservation([REDACTED])"
    assert repr(obs.refunds) == "RefundsObservation([REDACTED])"

    with pytest.raises(AttributeError):
        obs.employments = ()
    with pytest.raises(AttributeError):
        obs.employments[0].tax_taken_off_pay = 99
    with pytest.raises(AttributeError):
        obs.pensions_benefits.incapacity_benefit = 1
    with pytest.raises(AttributeError):
        obs.refunds.tax_refunded_or_set_off = 1
    assert isinstance(obs.employments, tuple)
    assert isinstance(obs.unknown_names, frozenset)


def test_observations_do_not_retain_raw_mappings_or_unknown_values():
    obs = _annual_obs()
    assert set(vars(obs)) == {
        "employments", "pensions_benefits", "refunds", "unknown_names", "completeness",
    }
    assert set(vars(obs.employments[0])) == {
        "employer_paye_reference", "tax_taken_off_pay", "unknown_names",
    }
    assert set(vars(obs.pensions_benefits)) == {
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "present_fields", "absent_fields", "unknown_names",
    }
    assert set(vars(obs.refunds)) == {
        "tax_refunded_or_set_off", "present_fields", "absent_fields", "unknown_names",
    }
    assert set(vars(_error_obs())) == {"status_code", "code", "unknown_names"}
    for container in (obs, obs.pensions_benefits, obs.refunds, obs.employments[0], _error_obs()):
        for value in vars(container).values():
            assert not isinstance(value, (dict, list, set))


def test_employment_item_direct_constructor_rejects_invalid_state():
    for bad_names in (["x"], {"x"}, ("x",), frozenset({"\x85"})):
        with pytest.raises(HMRCIndividualTaxContractError):
            EmploymentItemObservation(
                employer_paye_reference="267/LS500", tax_taken_off_pay=1,
                unknown_names=bad_names,
            )
    for bad_pay in (1.5, "1", True, None):
        with pytest.raises(HMRCIndividualTaxContractError):
            EmploymentItemObservation(
                employer_paye_reference="267/LS500", tax_taken_off_pay=bad_pay,
            )
    for bad_ref in (1, None, True, ["x"], "\u202e"):
        with pytest.raises(HMRCIndividualTaxContractError):
            EmploymentItemObservation(employer_paye_reference=bad_ref, tax_taken_off_pay=1)


def test_benefits_direct_constructor_enforces_coherence():
    base_absent = frozenset({"otherPensionsAndRetirementAnnuities"})
    present = frozenset({"incapacityBenefit"})

    with pytest.raises(HMRCIndividualTaxContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=0, present_fields=["incapacityBenefit"], absent_fields=base_absent,
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=None, present_fields=present, absent_fields=base_absent,
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        PensionsBenefitsObservation(
            other_pensions_and_retirement_annuities=1,
            present_fields=present, absent_fields=base_absent,
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=0, present_fields=present, absent_fields=base_absent,
            unknown_names=["x"],
        )


def test_refunds_direct_constructor_enforces_coherence():
    with pytest.raises(HMRCIndividualTaxContractError):
        RefundsObservation(tax_refunded_or_set_off=None, present_fields=frozenset({"taxRefundedOrSetOff"}))
    with pytest.raises(HMRCIndividualTaxContractError):
        RefundsObservation(tax_refunded_or_set_off=1, present_fields=frozenset())
    with pytest.raises(HMRCIndividualTaxContractError):
        RefundsObservation(tax_refunded_or_set_off=None, unknown_names=["x"])


def test_annual_summary_direct_constructor_enforces_coherence():
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxAnnualSummaryObservation(
            employments=[_employment_item_obs()],
            pensions_benefits=_benefits_obs(),
            refunds=_refunds_obs(),
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxAnnualSummaryObservation(
            employments=(object(),), pensions_benefits=_benefits_obs(), refunds=_refunds_obs(),
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxAnnualSummaryObservation(
            employments=(), pensions_benefits=object(), refunds=_refunds_obs(),
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxAnnualSummaryObservation(
            employments=(), pensions_benefits=_benefits_obs(), refunds=object(),
        )
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxAnnualSummaryObservation(
            employments=(), pensions_benefits=_benefits_obs(), refunds=_refunds_obs(),
            completeness="VERIFIED",
        )


def test_error_direct_constructor_enforces_pairing_and_types():
    for bad_status in (True, 200, "404", 404.0):
        with pytest.raises(HMRCIndividualTaxContractError):
            IndividualTaxErrorObservation(status_code=bad_status, code="NOT_FOUND")
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxErrorObservation(status_code=404, code=404)
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxErrorObservation(status_code=400, code="NOT_FOUND")
    with pytest.raises(HMRCIndividualTaxContractError):
        IndividualTaxErrorObservation(status_code=404, code="NOT_FOUND", unknown_names=["x"])


def test_dataclasses_replace_cannot_create_incoherent_observation():
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_employment_item_obs(), unknown_names=["x"])
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_employment_item_obs(), tax_taken_off_pay=1.5)
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_benefits_obs(), present_fields=frozenset())
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_refunds_obs(), tax_refunded_or_set_off=None)
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_annual_obs(), completeness="VERIFIED")
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_annual_obs(), employments=[_employment_item_obs()])
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_error_obs(), code="SA_UTR_INVALID")
    with pytest.raises(HMRCIndividualTaxContractError):
        replace(_error_obs(), status_code=200)


def test_observation_copy_deepcopy_return_immutable_instance():
    obs = _annual_obs()
    assert copy.copy(obs) is obs
    assert copy.deepcopy(obs) is obs
    assert copy.copy(obs.employments[0]) is obs.employments[0]
    assert copy.deepcopy(obs.pensions_benefits) is obs.pensions_benefits


def test_observation_pickle_preserves_coherence_and_exact_type():
    obs = _annual_obs()
    for candidate in (copy.copy(obs), copy.deepcopy(obs), pickle.loads(pickle.dumps(obs))):
        assert type(candidate) is IndividualTaxAnnualSummaryObservation
        assert type(candidate.employments) is tuple
        assert type(candidate.unknown_names) is frozenset
        assert type(candidate.pensions_benefits) is PensionsBenefitsObservation
        assert type(candidate.refunds) is RefundsObservation
        assert candidate == obs
        assert hash(candidate) == hash(obs)
        with pytest.raises(AttributeError):
            candidate.employments = ()


def test_pickle_uses_validated_rebuild_boundaries():
    assert _annual_obs().__reduce__()[0] is _rebuild_annual_summary
    assert _employment_item_obs().__reduce__()[0] is _rebuild_employment_item
    assert _benefits_obs().__reduce__()[0] is _rebuild_pensions_benefits
    assert _refunds_obs().__reduce__()[0] is _rebuild_refunds
    assert _error_obs().__reduce__()[0] is _rebuild_error


def test_observation_rebuild_boundaries_reject_invalid_state():
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_employment_item("267/LS500", 1.5, frozenset())
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_pensions_benefits(None, None, frozenset({"incapacityBenefit"}), frozenset({"otherPensionsAndRetirementAnnuities"}), frozenset())
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_refunds(None, frozenset({"taxRefundedOrSetOff"}), frozenset(), frozenset())
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_annual_summary((), object(), object(), frozenset(), "UNVERIFIED")
    with pytest.raises(HMRCIndividualTaxContractError):
        _rebuild_error(200, "NOT_FOUND", frozenset())


# --- No conversion into tax-engine / cash / customer evidence -----------------


def test_observations_contain_no_tax_cash_or_customer_fields():
    obs = _annual_obs()
    forbidden = {
        "paid", "tax_paid", "tax_liability", "gross_pay", "net_pay", "canonical",
        "cash", "customer", "launch_ready", "evidence_id", "amount", "money",
        "total", "net", "aggregate",
    }
    for container in (obs, obs.pensions_benefits, obs.refunds, obs.employments[0]):
        assert forbidden.isdisjoint(container.__dataclass_fields__)


def test_no_cross_endpoint_join_or_double_count_surface():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "taxTakenOffPay": Decimal("100.00")},
    ], refunds={"taxRefundedOrSetOff": Decimal("20.00")}))
    assert obs.completeness == "UNVERIFIED"
    # Deducted amounts and refunds stay separate; no netting/aggregation surface.
    assert obs.employments[0].tax_taken_off_pay == Decimal("100.00")
    assert obs.refunds.tax_refunded_or_set_off == Decimal("20.00")
    for container in (obs, obs.pensions_benefits, obs.refunds, obs.employments[0]):
        for name in vars(container):
            lowered = name.lower()
            assert "join" not in lowered
            assert "canonical" not in lowered
            assert "mapping" not in lowered
            assert "dedupe" not in lowered
            assert "double" not in lowered
            assert "net" not in lowered
            assert "total" not in lowered


def test_observations_are_not_paye_evidence():
    import reserved.providers.hmrc_individual_tax_contract as contract

    obs = _annual_obs()
    for name in ("PayeEvidence", "AccountingEntry", "CanonicalAccountingTaxInput"):
        assert not hasattr(contract, name)
    assert not isinstance(obs, tuple)


def test_status_code_mapping_is_deeply_immutable():
    assert isinstance(HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES, MappingProxyType)
    with pytest.raises(TypeError):
        HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES[400] = frozenset({"X"})
    with pytest.raises(AttributeError):
        HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES[400].add("X")
    assert HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES[400] == {
        "SA_UTR_INVALID", "TAX_YEAR_INVALID",
    }
