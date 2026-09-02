"""Synthetic, network-free HMRC Individual Income 1.2 literal contract tests."""

import ast
import copy
import pickle
from collections import OrderedDict
from dataclasses import fields, replace
from decimal import Decimal
from enum import IntEnum
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType

import pytest

from reserved.providers.hmrc_individual_income_contract import (
    HMRC_INDIVIDUAL_INCOME_400_CODES,
    HMRC_INDIVIDUAL_INCOME_401_CODES,
    HMRC_INDIVIDUAL_INCOME_404_CODES,
    HMRC_INDIVIDUAL_INCOME_ACCEPT,
    HMRC_INDIVIDUAL_INCOME_API,
    HMRC_INDIVIDUAL_INCOME_API_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES,
    HMRC_INDIVIDUAL_INCOME_HTTP_METHOD,
    HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE,
    HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE,
    HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN,
    HMRC_INDIVIDUAL_INCOME_SCOPE,
    UTR_REDACTION_MARKER,
    EmploymentItemObservation,
    HMRCIndividualIncomeContractError,
    IndividualIncomeAnnualSummaryObservation,
    IndividualIncomeErrorObservation,
    IndividualIncomeRequestIntent,
    PensionsBenefitsObservation,
    build_individual_income_request,
    observe_individual_income_response,
)
from reserved.providers.http_boundary import ProviderRequest


UTR = "0123456789"
TAX_YEAR = "2023-24"


def _request(utr=UTR, tax_year=TAX_YEAR):
    return build_individual_income_request(utr=utr, tax_year=tax_year)


def _success_payload(**overrides):
    payload = {"employments": [], "pensionsAnnuitiesAndOtherStateBenefits": {}}
    payload.update(overrides)
    return payload


_MISSING = object()


def _observe(payload=_MISSING, *, status_code=200, content_type="application/json", request=None):
    if payload is _MISSING:
        payload = _success_payload()
    return observe_individual_income_response(
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


# ── Exact constants and request construction ─────────────────────────────────


def test_documented_constants_are_exact():
    assert HMRC_INDIVIDUAL_INCOME_API == "individual-income"
    assert HMRC_INDIVIDUAL_INCOME_API_VERSION == "1.2"
    assert HMRC_INDIVIDUAL_INCOME_HTTP_METHOD == "GET"
    assert HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN == "https://test-api.service.hmrc.gov.uk"
    assert HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE == (
        "/individual-income/sa/{utr}/annual-summary/{taxYear}"
    )
    assert HMRC_INDIVIDUAL_INCOME_ACCEPT == "application/vnd.hmrc.1.2+json"
    assert HMRC_INDIVIDUAL_INCOME_SCOPE == "read:individual-income"
    assert HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE == "application/json"
    assert HMRC_INDIVIDUAL_INCOME_COMPLETENESS == "UNVERIFIED"


def test_documented_status_code_sets_are_exact():
    assert HMRC_INDIVIDUAL_INCOME_400_CODES == {"SA_UTR_INVALID", "TAX_YEAR_INVALID"}
    assert HMRC_INDIVIDUAL_INCOME_401_CODES == {"UNAUTHORIZED"}
    assert HMRC_INDIVIDUAL_INCOME_404_CODES == {"NOT_FOUND"}


def test_request_intent_construction_and_exact_redaction():
    request = _request()
    assert isinstance(request, IndividualIncomeRequestIntent)
    assert request.method == "GET"
    assert request.sandbox_origin == "https://test-api.service.hmrc.gov.uk"
    assert request.path_template == "/individual-income/sa/{utr}/annual-summary/{taxYear}"
    assert request.accept == "application/vnd.hmrc.1.2+json"
    assert request.scope == "read:individual-income"
    assert request.tax_year == "2023-24"
    assert request.redacted_path == (
        "/individual-income/sa/[UTR-REDACTED]/annual-summary/2023-24"
    )
    assert UTR_REDACTION_MARKER == "[UTR-REDACTED]"
    assert UTR_REDACTION_MARKER in request.redacted_path
    assert UTR not in request.redacted_path


def test_raw_utr_is_discarded_from_every_retained_state():
    request = _request()
    snapshots = [
        repr(request),
        str(request),
        str(vars(request)),
        str(request.__dict__),
        repr(copy.copy(request)),
        repr(copy.deepcopy(request)),
    ]
    for snapshot in snapshots:
        assert UTR not in snapshot

    serialized = pickle.dumps(request)
    assert UTR.encode("ascii") not in serialized
    assert pickle.loads(serialized) == request

    # Equality and hash depend only on the UTR-free fields.
    assert _request(utr="1111111111") == _request(utr="2222222222")
    assert hash(_request(utr="1111111111")) == hash(_request(utr="2222222222"))


def test_request_intent_does_not_carry_sendable_or_credential_state():
    request = _request()
    for absent in ("url", "headers", "body", "authorization", "token", "credential", "transport", "client"):
        assert not hasattr(request, absent)
    assert not issubclass(IndividualIncomeRequestIntent, ProviderRequest)


def test_request_intent_constructor_cannot_supply_derived_fields():
    # method, origin, path template, Accept, scope and redacted path are all
    # derived internally and are not accepted constructor arguments.
    for kwargs in (
        {"method": "POST"},
        {"sandbox_origin": "https://evil.example"},
        {"path_template": "/other/{utr}/{taxYear}"},
        {"accept": "text/plain"},
        {"scope": "read:other"},
        {"redacted_path": f"/individual-income/sa/{UTR}/annual-summary/{TAX_YEAR}"},
    ):
        with pytest.raises(TypeError):
            IndividualIncomeRequestIntent(utr=UTR, tax_year=TAX_YEAR, **kwargs)


def test_request_intent_constructor_validates_utr_and_tax_year_directly():
    # The exact public class is itself a validated construction boundary.
    with pytest.raises(HMRCIndividualIncomeContractError):
        IndividualIncomeRequestIntent(utr="123456789", tax_year=TAX_YEAR)
    with pytest.raises(HMRCIndividualIncomeContractError):
        IndividualIncomeRequestIntent(utr=UTR, tax_year="NOT-A-YEAR")
    valid = IndividualIncomeRequestIntent(utr=UTR, tax_year=TAX_YEAR)
    assert valid.tax_year == TAX_YEAR
    assert UTR not in valid.redacted_path


def test_request_intent_dataclasses_replace_cannot_forge_retained_state():
    request = _request()
    # replace() cannot re-enter the object without the validated UTR boundary.
    with pytest.raises(TypeError):
        replace(request)
    with pytest.raises(TypeError):
        replace(request, redacted_path=f"/individual-income/sa/{UTR}/annual-summary/{TAX_YEAR}")
    with pytest.raises(TypeError):
        replace(request, method="POST")
    with pytest.raises(TypeError):
        replace(request, scope="read:other")
    # The only accepted re-entry is through the validated UTR/tax-year boundary,
    # which discards the UTR and recomputes the redacted path internally.
    forged = replace(request, utr="1111111111")
    assert UTR not in forged.redacted_path
    assert "1111111111" not in forged.redacted_path
    assert forged.redacted_path == request.redacted_path


def test_request_intent_is_frozen_against_arbitrary_field_injection():
    request = _request()
    for attr in (
        "method", "sandbox_origin", "path_template", "accept", "scope",
        "tax_year", "redacted_path",
    ):
        with pytest.raises(AttributeError):
            setattr(request, attr, "forged")
    with pytest.raises(AttributeError):
        del request.redacted_path


def test_different_utrs_same_tax_year_leave_identical_retained_state():
    a = _request(utr="1111111111")
    b = _request(utr="2222222222")
    assert vars(a) == vars(b)
    assert a == b
    assert hash(a) == hash(b)
    assert repr(a) == repr(b)
    assert a.redacted_path == b.redacted_path
    for snapshot in (pickle.dumps(a), pickle.dumps(b)):
        assert b"1111111111" not in snapshot
        assert b"2222222222" not in snapshot


def test_exact_observer_accepts_validated_request_copies():
    request = _request()
    candidates = (
        request,
        copy.copy(request),
        copy.deepcopy(request),
    )
    for candidate in candidates:
        obs = observe_individual_income_response(
            candidate,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )
        assert isinstance(obs, IndividualIncomeAnnualSummaryObservation)


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
    with pytest.raises(HMRCIndividualIncomeContractError):
        build_individual_income_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("utr", [1234567890, None, True, b"0123456789", ["0123456789"]])
def test_non_string_utr_is_rejected(utr):
    with pytest.raises(HMRCIndividualIncomeContractError):
        build_individual_income_request(utr=utr, tax_year=TAX_YEAR)


@pytest.mark.parametrize("tax_year", [
    "2023/24", "2023-2", "202-24", "202324", "2023_24", "ABCD-24", "2023-٢٤", "", None, 2023,
])
def test_malformed_tax_year_is_rejected(tax_year):
    with pytest.raises(HMRCIndividualIncomeContractError):
        build_individual_income_request(utr=UTR, tax_year=tax_year)


def test_validation_failures_are_constant_and_non_echoing():
    for bad_utr in ("999999999X", "12345678901"):
        with pytest.raises(HMRCIndividualIncomeContractError) as exc:
            build_individual_income_request(utr=bad_utr, tax_year=TAX_YEAR)
        assert bad_utr not in str(exc.value)

    with pytest.raises(HMRCIndividualIncomeContractError) as exc:
        build_individual_income_request(utr=UTR, tax_year="NOT-A-YEAR")
    assert "NOT-A-YEAR" not in str(exc.value)


# ── Network-inert / no transport / no downstream evidence surface ───────────


def test_module_imports_no_network_transport_or_subprocess():
    path = Path("reserved/providers/hmrc_individual_income_contract.py")
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
    # It must not even import the generic sendable request/transport boundary.
    assert "http_boundary" not in imported_roots


def test_module_source_has_no_production_origin_or_downstream_evidence_surface():
    source = Path("reserved/providers/hmrc_individual_income_contract.py").read_text(encoding="utf-8")
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
    assert isinstance(obs, IndividualIncomeAnnualSummaryObservation)
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
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_payload_must_be_exact_builtin_dict():
    for payload in ([], "{}", 1, None, OrderedDict(), MappingProxyType({})):
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload=payload)


def test_employments_must_be_exact_builtin_list():
    for value in ((), "[]", OrderedDict(), None):
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload=_success_payload(employments=value))


def test_employment_items_must_be_exact_builtin_dicts():
    payload = _success_payload(employments=[OrderedDict(), ["x"], None, 1])
    for item in payload["employments"]:
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload={"employments": [item], "pensionsAnnuitiesAndOtherStateBenefits": {}})


def test_benefits_container_must_be_exact_builtin_dict():
    for value in ([], "{}", None):
        with pytest.raises(HMRCIndividualIncomeContractError):
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
    payload = _success_payload(employments=[{"payFromEmployment": 1}])
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)
    payload = _success_payload(employments=[{"employerPayeReference": "267/LS500"}])
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


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
    with pytest.raises(HMRCIndividualIncomeContractError):
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
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_numeric_subclasses_are_rejected():
    class _IntEnum(IntEnum):
        X = 5

    values = [
        _IntSubclass(5),
        _DecimalSubclass("1.5"),
        Fraction(1, 2),
        _IntEnum.X,
    ]
    for value in values:
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload=payload)


@pytest.mark.parametrize("value", [
    Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"),
])
def test_non_finite_decimal_is_rejected(value):
    payload = _success_payload(employments=[{
        "employerPayeReference": "267/LS500", "payFromEmployment": value,
    }])
    with pytest.raises(HMRCIndividualIncomeContractError):
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
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload=payload)


def test_reserved_decimal_magnitude_and_scale_boundaries():
    accepted = [Decimal("1e18"), Decimal("-1e18"), Decimal("0.123456789012")]
    for value in accepted:
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        _observe(payload=payload)

    rejected = [
        Decimal("1000000000000000001"),   # magnitude just over 10**18
        Decimal("0.1234567890123"),       # 13 fractional places
    ]
    for value in rejected:
        payload = _success_payload(employments=[{
            "employerPayeReference": "267/LS500", "payFromEmployment": value,
        }])
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(payload=payload)


# ── String values: empty/whitespace accepted, schema-valid but unverified ───


@pytest.mark.parametrize("paye", ["", "   ", "\t"])
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
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


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


def test_error_body_unknown_names_accepted_without_touching_values():
    obs = _observe(
        payload={"code": "NOT_FOUND", "message": "n/a", "extra": _HostileValue()},
        status_code=404,
    )
    assert isinstance(obs, IndividualIncomeErrorObservation)
    assert obs.unknown_names == {"extra"}


# ── Unsafe / malformed / excessive keys rejected ────────────────────────────


def test_non_string_and_mixed_keys_are_rejected():
    payload = _success_payload()
    payload[1] = "x"
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


@pytest.mark.parametrize("key", [
    "bad\x00key",
    "bad\nkey",
    "bad\x7fkey",
    "bad\ud800key",       # lone surrogate
    "bad\udfffkey",       # lone surrogate
])
def test_control_character_and_surrogate_keys_are_rejected(key):
    payload = _success_payload()
    payload[key] = _HostileValue()
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def _key_level_observe_kwargs(key, level):
    """Build the payload (and status) that places ``key`` at one object level."""
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
    if level == "error":
        return {
            "payload": {"code": "NOT_FOUND", "message": "n/a", key: _HostileValue()},
            "status_code": 404,
        }
    raise AssertionError(f"unknown level {level!r}")


def _level_unknown_names(obs, level):
    if level == "top":
        return obs.unknown_names
    if level == "employment":
        return obs.employments[0].unknown_names
    if level == "benefits":
        return obs.pensions_benefits.unknown_names
    if level == "error":
        return obs.unknown_names
    raise AssertionError(f"unknown level {level!r}")


@pytest.mark.parametrize("key", [
    "\x85",               # C1 control (Cc)
    "\x9f",               # C1 control (Cc)
    "\u200e",             # bidi format control (Cf)
    "\u200b",             # zero-width space (Cf)
    "\ud800",             # lone high surrogate (Cs)
    "\udfff",             # lone low surrogate (Cs)
    "\ue000",             # private use (Co)
    "\uf8ff",             # private use (Co)
    "\ufdd0",             # noncharacter (Cn)
    "\uffff",             # noncharacter (Cn)
    "\u0378",             # unassigned code point (Cn)
])
@pytest.mark.parametrize("level", ["top", "employment", "benefits", "error"])
def test_unsafe_unicode_key_names_are_rejected_at_every_level(key, level):
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(**_key_level_observe_kwargs(key, level))


@pytest.mark.parametrize("key", [
    "café",               # international letters (Ll)
    "na\u00efve",         # international letters (Ll)
    "e\u0301tude",        # combining mark (Mn)
    "\u4e2d\u6587",       # CJK ideographs (Lo)
    "\U0001f600",         # emoji (So)
    "field name",         # ASCII space (Zs)
    "a\u00a0b",           # no-break space separator (Zs)
    "\u2028separator",    # Unicode line separator (Zl)
])
@pytest.mark.parametrize("level", ["top", "employment", "benefits", "error"])
def test_safe_international_key_names_are_retained_at_every_level(key, level):
    obs = _observe(**_key_level_observe_kwargs(key, level))
    assert key in _level_unknown_names(obs, level)


def test_oversized_key_is_rejected():
    payload = _success_payload()
    payload["x" * 257] = _HostileValue()
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_empty_key_is_rejected():
    payload = _success_payload()
    payload[""] = _HostileValue()
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_excessive_unknown_keys_are_rejected():
    payload = _success_payload()
    for index in range(33):
        payload[f"future_{index}"] = _HostileValue()
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_excessive_object_members_are_rejected():
    payload = _success_payload()
    for index in range(65):
        payload[f"field_{index}"] = _HostileValue()
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


def test_excessive_employments_are_rejected():
    payload = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": 1}
    ] * 10_001)
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload)


# ── Error status/code/media combinations ────────────────────────────────────


@pytest.mark.parametrize("status_code, code", [
    (400, "SA_UTR_INVALID"),
    (400, "TAX_YEAR_INVALID"),
    (401, "UNAUTHORIZED"),
    (404, "NOT_FOUND"),
])
def test_documented_error_pairings_are_accepted(status_code, code):
    obs = _observe(payload={"code": code, "message": "detail"}, status_code=status_code)
    assert isinstance(obs, IndividualIncomeErrorObservation)
    assert obs.status_code == status_code
    assert obs.code == code


@pytest.mark.parametrize("status_code, code", [
    (400, "NOT_FOUND"),
    (400, "UNAUTHORIZED"),
    (401, "SA_UTR_INVALID"),
    (401, "NOT_FOUND"),
    (404, "UNAUTHORIZED"),
    (404, "SA_UTR_INVALID"),
    (400, "UNKNOWN_CODE"),
])
def test_mismatched_status_code_pairings_are_rejected(status_code, code):
    payload = {"code": code, "message": "detail"}
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload, status_code=status_code)


@pytest.mark.parametrize("status_code", [200, 400, 401, 404])
def test_error_and_success_require_exact_json_content_type(status_code):
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(status_code=status_code, content_type="application/json; charset=utf-8")
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(status_code=status_code, content_type="text/json")
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(status_code=status_code, content_type="application/vnd.hmrc.1.2+json")


def test_undocumented_status_is_rejected():
    for status_code in (201, 204, 300, 500, 503):
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(status_code=status_code)


def test_status_code_must_be_exact_integer():
    for status_code in (True, False, "200", 200.0):
        with pytest.raises(HMRCIndividualIncomeContractError):
            _observe(status_code=status_code)


@pytest.mark.parametrize("payload", [
    {"code": "NOT_FOUND"},                       # missing message
    {"message": "detail"},                       # missing code
    {"code": "NOT_FOUND", "message": None},      # null message
    {"code": None, "message": "detail"},         # null code
    {"code": "NOT_FOUND", "message": 42},        # non-string message
    {"code": 404, "message": "detail"},          # non-string code
    "NOT_FOUND",                                  # non-object body
    [],
])
def test_malformed_error_bodies_are_rejected(payload):
    with pytest.raises(HMRCIndividualIncomeContractError):
        _observe(payload=payload, status_code=404)


def test_error_message_is_unretained_and_non_echoing():
    obs = _observe(payload={"code": "NOT_FOUND", "message": "SECRET-12345"}, status_code=404)
    assert not hasattr(obs, "message")
    assert "SECRET-12345" not in repr(obs)

    payload = {"code": "WRONG", "message": "SECRET-99999"}
    with pytest.raises(HMRCIndividualIncomeContractError) as exc:
        _observe(payload=payload, status_code=404)
    assert "SECRET-99999" not in str(exc.value)


def test_http_404_is_unavailable_not_zero_or_empty_evidence():
    obs = _observe(payload={"code": "NOT_FOUND", "message": "unavailable"}, status_code=404)
    assert isinstance(obs, IndividualIncomeErrorObservation)
    assert obs.code == "NOT_FOUND"
    # A 404 error observation is not an annual-summary/empty-income record.
    assert not isinstance(obs, IndividualIncomeAnnualSummaryObservation)
    assert not hasattr(obs, "employments")


# ── Immutability ────────────────────────────────────────────────────────────


def test_status_code_mapping_and_nested_sets_are_deeply_immutable():
    assert isinstance(HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES, MappingProxyType)
    with pytest.raises(TypeError):
        HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[400] = frozenset({"X"})
    with pytest.raises(AttributeError):
        HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[400].add("X")

    # Mutation attempts leave validation unchanged.
    assert HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[400] == {
        "SA_UTR_INVALID", "TAX_YEAR_INVALID",
    }
    obs = _observe(payload={"code": "SA_UTR_INVALID", "message": "bad"}, status_code=400)
    assert obs.code == "SA_UTR_INVALID"


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
    return EmploymentItemObservation(employer_paye_reference=paye, pay_from_employment=pay)


def _benefits_obs():
    return PensionsBenefitsObservation(
        incapacity_benefit=0,
        present_fields=frozenset({"incapacityBenefit"}),
        absent_fields=frozenset({
            "otherPensionsAndRetirementAnnuities", "jobseekersAllowance", "seissNetPaid",
        }),
    )


def _annual_obs(request=None):
    return observe_individual_income_response(
        request or _request(),
        status_code=200,
        content_type="application/json",
        payload=_success_payload(
            employments=[{
                "employerPayeReference": "267/LS500",
                "payFromEmployment": Decimal("1.00"),
            }],
            pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": 0},
        ),
    )


def _error_obs(status_code=404, code="NOT_FOUND", request=None):
    return observe_individual_income_response(
        request or _request(),
        status_code=status_code,
        content_type="application/json",
        payload={"code": code, "message": "detail"},
    )


def test_employment_item_direct_constructor_rejects_mutable_or_invalid_state():
    for bad_names in (["x"], {"x"}, ("x",), frozenset({"\x85"})):
        with pytest.raises(HMRCIndividualIncomeContractError):
            EmploymentItemObservation(
                employer_paye_reference="267/LS500", pay_from_employment=1,
                unknown_names=bad_names,
            )
    for bad_pay in (1.5, "1", True, None):
        with pytest.raises(HMRCIndividualIncomeContractError):
            EmploymentItemObservation(
                employer_paye_reference="267/LS500", pay_from_employment=bad_pay,
            )
    for bad_ref in (1, None, True, ["x"]):
        with pytest.raises(HMRCIndividualIncomeContractError):
            EmploymentItemObservation(employer_paye_reference=bad_ref, pay_from_employment=1)


def test_benefits_direct_constructor_enforces_coherence():
    base_absent = frozenset({
        "otherPensionsAndRetirementAnnuities", "jobseekersAllowance", "seissNetPaid",
    })
    present = frozenset({"incapacityBenefit"})

    for bad in (["incapacityBenefit"], {"incapacityBenefit"}):
        with pytest.raises(HMRCIndividualIncomeContractError):
            PensionsBenefitsObservation(
                incapacity_benefit=0, present_fields=bad, absent_fields=base_absent,
            )
    with pytest.raises(HMRCIndividualIncomeContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=0,
            present_fields=present,
            absent_fields=frozenset({"incapacityBenefit", "jobseekersAllowance", "seissNetPaid"}),
        )
    with pytest.raises(HMRCIndividualIncomeContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=0,
            present_fields=present,
            absent_fields=frozenset({"otherPensionsAndRetirementAnnuities", "seissNetPaid"}),
        )
    # A present member must not be None; an absent member must be None.
    with pytest.raises(HMRCIndividualIncomeContractError):
        PensionsBenefitsObservation(incapacity_benefit=None, present_fields=present, absent_fields=base_absent)
    with pytest.raises(HMRCIndividualIncomeContractError):
        PensionsBenefitsObservation(
            other_pensions_and_retirement_annuities=1,
            present_fields=present,
            absent_fields=base_absent,
        )
    with pytest.raises(HMRCIndividualIncomeContractError):
        PensionsBenefitsObservation(
            incapacity_benefit=0, present_fields=present, absent_fields=base_absent,
            unknown_names=["x"],
        )


def test_annual_summary_public_constructor_is_unconditionally_unsupported():
    request = _request()
    for kwargs in (
        {
            "request": request,
            "employments": (_employment_item_obs(),),
            "pensions_benefits": _benefits_obs(),
        },
        {
            "request": request,
            "employments": (),
            "pensions_benefits": _benefits_obs(),
            "_request_binding": tuple(vars(request).values()),
            "tax_year": TAX_YEAR,
        },
    ):
        with pytest.raises(TypeError):
            IndividualIncomeAnnualSummaryObservation(**kwargs)

    with pytest.raises(TypeError):
        IndividualIncomeAnnualSummaryObservation(
            request=request,
            employments=[_employment_item_obs()], pensions_benefits=_benefits_obs(),
        )


def test_error_public_constructor_is_unconditionally_unsupported():
    request = _request()
    for status_code, code in (
        (400, "SA_UTR_INVALID"),
        (400, "TAX_YEAR_INVALID"),
        (401, "UNAUTHORIZED"),
        (404, "NOT_FOUND"),
    ):
        with pytest.raises(TypeError):
            IndividualIncomeErrorObservation(
                request=request,
                status_code=status_code,
                code=code,
                _request_binding=_error_obs(
                    status_code=status_code,
                    code=code,
                    request=request,
                )._request_binding,
                tax_year=TAX_YEAR,
            )


def test_dataclasses_replace_cannot_create_incoherent_observation():
    with pytest.raises(HMRCIndividualIncomeContractError):
        replace(_employment_item_obs(), unknown_names=["x"])
    with pytest.raises(HMRCIndividualIncomeContractError):
        replace(_employment_item_obs(), pay_from_employment=1.5)
    with pytest.raises(HMRCIndividualIncomeContractError):
        replace(_benefits_obs(), present_fields=frozenset())
    with pytest.raises(HMRCIndividualIncomeContractError):
        replace(_benefits_obs(), unknown_names=["x"])
    for observation in (_annual_obs(), _error_obs()):
        with pytest.raises((TypeError, ValueError)):
            replace(observation)
        for field_name, value in (
            ("request", _request()),
            ("tax_year", TAX_YEAR),
            ("_request_binding", observation._request_binding),
        ):
            with pytest.raises((TypeError, ValueError)):
                replace(observation, **{field_name: value})


def test_observation_copy_deepcopy_and_pickle_preserve_coherence():
    obs = _annual_obs()
    serialized = pickle.dumps(obs)
    assert UTR.encode("ascii") not in serialized
    for candidate in (copy.copy(obs), copy.deepcopy(obs), pickle.loads(serialized)):
        assert candidate == obs
        assert hash(candidate) == hash(obs)
        assert type(candidate) is IndividualIncomeAnnualSummaryObservation
        assert type(candidate.employments) is tuple
        assert type(candidate.unknown_names) is frozenset
        assert type(candidate.pensions_benefits) is PensionsBenefitsObservation
        assert candidate.tax_year == obs.tax_year == TAX_YEAR
        with pytest.raises(AttributeError):
            candidate.employments = ()


def test_observations_do_not_retain_raw_mappings_or_unknown_values():
    obs = _annual_obs()
    assert set(vars(obs)) == {
        "request", "employments", "pensions_benefits", "unknown_names",
        "completeness", "_source_context", "_request_binding", "tax_year",
    }
    assert set(vars(obs.pensions_benefits)) == {
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "jobseekers_allowance", "seiss_net_paid", "present_fields",
        "absent_fields", "unknown_names",
    }
    assert set(vars(obs.employments[0])) == {
        "employer_paye_reference", "pay_from_employment", "unknown_names",
    }
    assert set(vars(_error_obs())) == {
        "request", "status_code", "code", "unknown_names", "_source_context",
        "_request_binding", "tax_year",
    }
    for container in (obs, obs.pensions_benefits, obs.employments[0], _error_obs()):
        for value in vars(container).values():
            assert not isinstance(value, (dict, list, set))


# ── Request intent must be an exact instance ────────────────────────────────


def test_observe_requires_exact_request_intent_instance():
    for bad_request in (None, {}, "request", object()):
        with pytest.raises(HMRCIndividualIncomeContractError):
            observe_individual_income_response(
                bad_request,
                status_code=200,
                content_type="application/json",
                payload=_success_payload(),
            )


def test_observe_rejects_request_intent_subclass():
    class _SubclassIntent(IndividualIncomeRequestIntent):
        pass

    subclass = _SubclassIntent(utr=UTR, tax_year=TAX_YEAR)
    with pytest.raises(HMRCIndividualIncomeContractError):
        observe_individual_income_response(
            subclass,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )


# ── Request-derived annual identity binding ─────────────────────────────────


def test_success_and_error_observations_carry_exact_request_tax_year():
    for tax_year in ("2023-24", "2024-25"):
        request = _request(tax_year=tax_year)
        success = observe_individual_income_response(
            request,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )
        assert isinstance(success, IndividualIncomeAnnualSummaryObservation)
        assert success.tax_year == tax_year

        for status, code in (
            (400, "SA_UTR_INVALID"),
            (401, "UNAUTHORIZED"),
            (404, "NOT_FOUND"),
        ):
            error = observe_individual_income_response(
                request,
                status_code=status,
                content_type="application/json",
                payload={"code": code, "message": "m"},
            )
            assert isinstance(error, IndividualIncomeErrorObservation)
            assert error.tax_year == tax_year


def test_annual_identity_cannot_be_injected_or_replaced_independently():
    request = _request()
    with pytest.raises(TypeError):
        IndividualIncomeAnnualSummaryObservation(
            request=request,
            employments=(),
            pensions_benefits=_benefits_obs(),
            tax_year="2099-00",
        )
    with pytest.raises(TypeError):
        replace(_annual_obs(), request=request, tax_year="2099-00")
    with pytest.raises(TypeError):
        IndividualIncomeErrorObservation(
            request=request,
            status_code=404,
            code="NOT_FOUND",
            tax_year="2099-00",
        )
    with pytest.raises(TypeError):
        replace(_error_obs(), request=request, tax_year="2099-00")

    # A different validated request cannot relabel already-observed facts.
    other = _request(tax_year="2024-25")
    with pytest.raises((TypeError, ValueError)):
        replace(_annual_obs(), request=other)


def test_forged_request_state_fails_closed_without_hostile_hooks():
    # Missing internal state is rejected by shape before any value is read.
    empty = object.__new__(IndividualIncomeRequestIntent)
    with pytest.raises(HMRCIndividualIncomeContractError):
        observe_individual_income_response(
            empty,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )

    # Additional internal state is rejected without inspecting its value.
    extra = _request()
    object.__setattr__(extra, "extra", _HostileValue())
    with pytest.raises(HMRCIndividualIncomeContractError):
        observe_individual_income_response(
            extra,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )

    # A hostile value smuggled into every known slot is type-rejected before
    # any comparison, hash, repr, str or iteration hook is invoked.
    forged = object.__new__(IndividualIncomeRequestIntent)
    for name in (
        "tax_year", "method", "sandbox_origin", "path_template",
        "accept", "scope", "redacted_path",
    ):
        object.__setattr__(forged, name, _HostileValue())
    with pytest.raises(HMRCIndividualIncomeContractError):
        observe_individual_income_response(
            forged,
            status_code=200,
            content_type="application/json",
            payload=_success_payload(),
        )


def test_request_repr_never_renders_injected_utr_and_equality_hash_fail_closed():
    for field_name in ("tax_year", "redacted_path", "raw_utr"):
        damaged = _request()
        object.__setattr__(damaged, field_name, UTR)
        assert UTR not in repr(damaged)
        assert UTR not in str(damaged)
        with pytest.raises(HMRCIndividualIncomeContractError):
            damaged == _request()
        with pytest.raises(HMRCIndividualIncomeContractError):
            hash(damaged)
        with pytest.raises(HMRCIndividualIncomeContractError):
            pickle.dumps(damaged)

    hostile = _request()
    object.__setattr__(hostile, "tax_year", _HostileValue())
    assert repr(hostile) == "IndividualIncomeRequestIntent([REDACTED])"
    with pytest.raises(HMRCIndividualIncomeContractError):
        hostile == _request()
    with pytest.raises(HMRCIndividualIncomeContractError):
        hash(hostile)


@pytest.mark.parametrize("status_code,code", (
    (400, "SA_UTR_INVALID"),
    (400, "TAX_YEAR_INVALID"),
    (401, "UNAUTHORIZED"),
    (404, "NOT_FOUND"),
))
def test_error_repr_never_renders_injected_utr_and_equality_hash_fail_closed(status_code, code):
    for field_name in ("code", "tax_year", "raw_utr"):
        damaged = _error_obs(status_code=status_code, code=code)
        object.__setattr__(damaged, field_name, UTR)
        assert UTR not in repr(damaged)
        assert UTR not in str(damaged)
        with pytest.raises(HMRCIndividualIncomeContractError):
            damaged == _error_obs(status_code=status_code, code=code)
        with pytest.raises(HMRCIndividualIncomeContractError):
            hash(damaged)
        with pytest.raises(HMRCIndividualIncomeContractError):
            pickle.dumps(damaged)

    hostile = _error_obs(status_code=status_code, code=code)
    object.__setattr__(hostile, "code", _HostileValue())
    assert repr(hostile) == "IndividualIncomeErrorObservation([REDACTED])"
    with pytest.raises(HMRCIndividualIncomeContractError):
        hostile == _error_obs(status_code=status_code, code=code)
    with pytest.raises(HMRCIndividualIncomeContractError):
        hash(hostile)


def test_observations_retain_no_utr_and_match_only_by_tax_year():
    payload = _success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": Decimal("1.00")},
    ])
    a = observe_individual_income_response(
        _request(utr="1111111111"),
        status_code=200,
        content_type="application/json",
        payload=payload,
    )
    b = observe_individual_income_response(
        _request(utr="2222222222"),
        status_code=200,
        content_type="application/json",
        payload=payload,
    )
    assert vars(a) == vars(b)
    assert a == b
    assert hash(a) == hash(b)
    for snapshot in (repr(a), str(vars(a))):
        assert "1111111111" not in snapshot
        assert "2222222222" not in snapshot
    serialized = pickle.dumps(a)
    assert b"1111111111" not in serialized
    assert b"2222222222" not in serialized
    assert pickle.loads(serialized) == a


def test_error_observation_copy_deepcopy_and_pickle_preserve_coherence():
    obs = _error_obs()
    serialized = pickle.dumps(obs)
    assert UTR.encode("ascii") not in serialized
    for candidate in (copy.copy(obs), copy.deepcopy(obs), pickle.loads(serialized)):
        assert candidate == obs
        assert hash(candidate) == hash(obs)
        assert type(candidate) is IndividualIncomeErrorObservation
        assert candidate.tax_year == obs.tax_year == TAX_YEAR
        with pytest.raises(AttributeError):
            candidate.code = "NOT_FOUND"


_DOCUMENTED_ERROR_PAIRINGS = (
    (400, "SA_UTR_INVALID"),
    (400, "TAX_YEAR_INVALID"),
    (401, "UNAUTHORIZED"),
    (404, "NOT_FOUND"),
)


def _assert_clone_and_reduce_boundaries_reject(value):
    for operation in (
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
        lambda candidate: candidate.__reduce__(),
    ):
        with pytest.raises(HMRCIndividualIncomeContractError):
            operation(value)


def test_observation_tax_year_is_derived_non_init_state():
    for observation_type in (
        IndividualIncomeAnnualSummaryObservation,
        IndividualIncomeErrorObservation,
    ):
        observation_fields = fields(observation_type)
        assert all(item.init is False for item in observation_fields)
        tax_year_field = next(item for item in observation_fields if item.name == "tax_year")
        assert tax_year_field.init is False
        for name in ("request", "_request_binding", "tax_year"):
            assert next(item for item in observation_fields if item.name == name).init is False


def test_observation_replace_is_unconditionally_unsupported():
    request = _request(tax_year="2023-24")
    observations = [_annual_obs(request=request)]
    observations.extend(
        _error_obs(status_code=status_code, code=code, request=request)
        for status_code, code in _DOCUMENTED_ERROR_PAIRINGS
    )
    for observation in observations:
        for changes in (
            {},
            {"unknown_names": frozenset({"futureMember"})},
            {"_source_context": observation._source_context},
        ):
            with pytest.raises((TypeError, ValueError)):
                replace(observation, **changes)


def test_source_context_cannot_be_supplied_to_public_construction():
    annual = _annual_obs()
    with pytest.raises(TypeError):
        IndividualIncomeAnnualSummaryObservation(
            employments=annual.employments,
            pensions_benefits=annual.pensions_benefits,
            unknown_names=annual.unknown_names,
            completeness=annual.completeness,
            _source_context=annual._source_context,
        )

    for status_code, code in _DOCUMENTED_ERROR_PAIRINGS:
        error = _error_obs(status_code=status_code, code=code)
        with pytest.raises(TypeError):
            IndividualIncomeErrorObservation(
                status_code=error.status_code,
                code=error.code,
                unknown_names=error.unknown_names,
                _source_context=error._source_context,
            )


def test_public_replace_and_partial_low_level_relabel_fail_for_success_and_errors():
    original = _request(tax_year="2023-24")
    other = _request(tax_year="2024-25")
    observations = [_annual_obs(request=original)]
    observations.extend(
        _error_obs(status_code=status_code, code=code, request=original)
        for status_code, code in _DOCUMENTED_ERROR_PAIRINGS
    )

    for observation in observations:
        with pytest.raises((TypeError, ValueError)):
            replace(observation, request=other)
        with pytest.raises((TypeError, ValueError)):
            replace(observation, request=other, tax_year="2024-25")
        with pytest.raises((TypeError, ValueError)):
            replace(
                observation,
                request=other,
                _request_binding=_annual_obs(request=other)._request_binding,
                tax_year="2024-25",
            )
        other_observation = (
            _annual_obs(request=other)
            if type(observation) is IndividualIncomeAnnualSummaryObservation
            else _error_obs(
                status_code=observation.status_code,
                code=observation.code,
                request=other,
            )
        )
        with pytest.raises((TypeError, ValueError)):
            replace(observation, _source_context=other_observation._source_context)

        # These three coordinated changes are still incomplete relative to the
        # parser-established source context and therefore fail on every
        # validating protocol surface. Arbitrary code replacing *all* mutually
        # coherent state is outside this value object's enforceable boundary.
        object.__setattr__(observation, "request", other)
        object.__setattr__(
            observation,
            "_request_binding",
            _annual_obs(request=other)._request_binding,
        )
        object.__setattr__(observation, "tax_year", "2024-25")
        _assert_clone_and_reduce_boundaries_reject(observation)
        with pytest.raises(HMRCIndividualIncomeContractError):
            hash(observation)
        peer = (
            _annual_obs(request=other)
            if type(observation) is IndividualIncomeAnnualSummaryObservation
            else _error_obs(
                status_code=observation.status_code,
                code=observation.code,
                request=other,
            )
        )
        with pytest.raises(HMRCIndividualIncomeContractError):
            observation == peer


def test_partial_low_level_source_context_substitution_fails_protocol_surfaces():
    original = _request(tax_year="2023-24")
    other = _request(tax_year="2024-25")
    observations = [_annual_obs(request=original)]
    observations.extend(
        _error_obs(status_code=status_code, code=code, request=original)
        for status_code, code in _DOCUMENTED_ERROR_PAIRINGS
    )
    for observation in observations:
        other_observation = (
            _annual_obs(request=other)
            if type(observation) is IndividualIncomeAnnualSummaryObservation
            else _error_obs(
                status_code=observation.status_code,
                code=observation.code,
                request=other,
            )
        )
        object.__setattr__(observation, "_source_context", other_observation._source_context)
        _assert_clone_and_reduce_boundaries_reject(observation)
        with pytest.raises(HMRCIndividualIncomeContractError):
            hash(observation)
        with pytest.raises(HMRCIndividualIncomeContractError):
            observation == other_observation


def test_request_clone_pickle_and_reduce_reject_missing_or_forged_complete_state():
    request_fields = (
        "tax_year", "method", "sandbox_origin", "path_template",
        "accept", "scope", "redacted_path",
    )
    for field_name in request_fields:
        damaged = _request()
        object.__delattr__(damaged, field_name)
        _assert_clone_and_reduce_boundaries_reject(damaged)

    for field_name, forged_value in (
        ("tax_year", "NOT-A-YEAR"),
        ("tax_year", "2024-25"),
        ("method", "POST"),
        ("sandbox_origin", "https://evil.example"),
        ("path_template", "/different/{utr}/{taxYear}"),
        ("accept", "text/plain"),
        ("scope", "read:other"),
        ("redacted_path", "/individual-income/sa/[UTR-REDACTED]/annual-summary/2024-25"),
    ):
        damaged = _request()
        object.__setattr__(damaged, field_name, forged_value)
        _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _request()
    object.__setattr__(damaged, "additional_state", _HostileValue())
    _assert_clone_and_reduce_boundaries_reject(damaged)


def test_annual_clone_pickle_and_reduce_reject_missing_forged_or_nested_state():
    for field_name in (
        "request", "employments", "pensions_benefits", "unknown_names",
        "completeness", "_request_binding", "tax_year",
    ):
        damaged = _annual_obs()
        object.__delattr__(damaged, field_name)
        _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "request", _request(tax_year="2024-25"))
    object.__setattr__(damaged, "tax_year", "2024-25")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "tax_year", "2024-25")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "_request_binding", _annual_obs(
        request=_request(tax_year="2024-25")
    )._request_binding)
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "completeness", "VERIFIED")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "employments", [_employment_item_obs()])
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "unknown_names", ["futureTopLevel"])
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged, "additional_state", _HostileValue())
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged.request, "method", "POST")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__delattr__(damaged.employments[0], "pay_from_employment")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _annual_obs()
    object.__setattr__(damaged.pensions_benefits, "present_fields", frozenset())
    _assert_clone_and_reduce_boundaries_reject(damaged)


def test_nested_observation_clone_pickle_and_reduce_reject_incomplete_state():
    employment = _employment_item_obs()
    object.__delattr__(employment, "pay_from_employment")
    _assert_clone_and_reduce_boundaries_reject(employment)

    employment = _employment_item_obs()
    object.__setattr__(employment, "additional_state", _HostileValue())
    _assert_clone_and_reduce_boundaries_reject(employment)

    benefits = _benefits_obs()
    object.__setattr__(benefits, "present_fields", frozenset())
    _assert_clone_and_reduce_boundaries_reject(benefits)

    benefits = _benefits_obs()
    object.__delattr__(benefits, "absent_fields")
    _assert_clone_and_reduce_boundaries_reject(benefits)


@pytest.mark.parametrize("status_code,code", _DOCUMENTED_ERROR_PAIRINGS)
def test_error_clone_pickle_and_reduce_reject_missing_forged_or_nested_state(status_code, code):
    for field_name in (
        "request", "status_code", "code", "unknown_names", "_request_binding", "tax_year",
    ):
        damaged = _error_obs(status_code=status_code, code=code)
        object.__delattr__(damaged, field_name)
        _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "request", _request(tax_year="2024-25"))
    object.__setattr__(damaged, "tax_year", "2024-25")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "tax_year", "2024-25")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "_request_binding", _error_obs(
        status_code=status_code,
        code=code,
        request=_request(tax_year="2024-25"),
    )._request_binding)
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "status_code", 200)
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "code", "NOT_A_DOCUMENTED_CODE")
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "unknown_names", ["futureErrorMember"])
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged, "additional_state", _HostileValue())
    _assert_clone_and_reduce_boundaries_reject(damaged)

    damaged = _error_obs(status_code=status_code, code=code)
    object.__setattr__(damaged.request, "redacted_path", "/forged")
    _assert_clone_and_reduce_boundaries_reject(damaged)


def test_valid_protocol_surfaces_cover_success_and_all_errors_without_utr():
    observations = [_annual_obs()]
    observations.extend(
        _error_obs(status_code=status_code, code=code)
        for status_code, code in _DOCUMENTED_ERROR_PAIRINGS
    )
    for observation in observations:
        serialized = pickle.dumps(observation)
        assert UTR.encode("ascii") not in serialized
        reduced = observation.__reduce__()
        assert UTR not in repr(reduced)
        for candidate in (copy.copy(observation), copy.deepcopy(observation), pickle.loads(serialized)):
            assert candidate == observation
            assert candidate.request == observation.request
            assert candidate._request_binding == observation._request_binding
            assert candidate.tax_year == observation.tax_year


def test_reduction_rebuilders_revalidate_the_canonical_utr_free_source_state():
    request_restore, request_args = _request().__reduce__()
    damaged_binding = list(request_args[0])
    damaged_binding[1] = "POST"
    with pytest.raises(HMRCIndividualIncomeContractError):
        request_restore(tuple(damaged_binding))

    for observation in (_annual_obs(), _error_obs()):
        restore, args = observation.__reduce__()
        damaged_binding = list(args[0])
        damaged_binding[-1] = "/forged"
        with pytest.raises(HMRCIndividualIncomeContractError):
            restore(tuple(damaged_binding), *args[1:])


# ── No cross-endpoint join / double-count / activation claims ───────────────


def test_no_cross_endpoint_join_or_double_count_surface():
    obs = _observe(payload=_success_payload(employments=[
        {"employerPayeReference": "267/LS500", "payFromEmployment": Decimal("100.00")},
    ]))
    assert obs.completeness == "UNVERIFIED"
    # The annual-summary observation exposes only validated known scalars,
    # frozen containers, bounded safe unknown names and the request-derived
    # tax year.
    assert set(vars(obs)) == {
        "request", "employments", "pensions_benefits", "unknown_names",
        "completeness", "_source_context", "_request_binding", "tax_year",
    }
    # No join key, identity, double-count, mapping or canonical surface.
    for container in (obs, obs.pensions_benefits, obs.employments[0]):
        for name in vars(container):
            lowered = name.lower()
            assert "join" not in lowered
            assert "canonical" not in lowered
            assert "mapping" not in lowered
            assert "dedupe" not in lowered
            assert "double" not in lowered
