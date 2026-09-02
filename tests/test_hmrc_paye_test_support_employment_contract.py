"""Synthetic, network-free tests for the HMRC Individual PAYE Test Support 2.1
employment fixture literal contract.

These tests exercise only the deterministic request/response contract and its
fail-closed validation. Nothing here calls HMRC, performs HTTP, reads
credentials, persists data or constructs tax-engine/cash/customer evidence.
"""

from __future__ import annotations

import ast
import copy
import pickle
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest

from reserved.providers.hmrc_paye_test_support_employment_contract import (
    COMPLETENESS_UNVERIFIED,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_ACCEPT,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_BETA,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_NAME,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_AUTHENTICATION,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_CONTENT_TYPE,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPERATION_ID,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_PATH_TEMPLATE,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ONLY,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS,
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYMENTS,
    RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS,
    RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS,
    EmploymentTestSupportRecordObservation,
    EmploymentTestSupportRequestIntent,
    EmploymentTestSupportResponseObservation,
    HMRCPayeTestSupportEmploymentContractError,
    build_employment_test_support_request,
    observe_employment_test_support_response,
)
from reserved.providers.http_boundary import ProviderRequest

REPO = Path(__file__).resolve().parents[1]

_UNSET = object()


def _request(*, utr="1234567890", tax_year="2026-27", scenario=_UNSET):
    if scenario is _UNSET:
        return build_employment_test_support_request(utr=utr, tax_year=tax_year)
    return build_employment_test_support_request(
        utr=utr, tax_year=tax_year, scenario=scenario
    )


def _employment(**overrides):
    record = {
        "employerName": "Example Ltd",
        "employerPayeReference": "123/AB456",
    }
    record.update(overrides)
    return record


def _success_payload(*employments, **top_level):
    payload = {"employments": list(employments)}
    payload.update(top_level)
    return payload


def _observe(
    *,
    status_code=201,
    content_type="application/json",
    payload=_UNSET,
    utr="1234567890",
    tax_year="2026-27",
):
    if payload is _UNSET:
        payload = _success_payload(_employment())
    return observe_employment_test_support_response(
        _request(utr=utr, tax_year=tax_year),
        status_code=status_code,
        content_type=content_type,
        payload=payload,
    )


# ── Exact documented constants ───────────────────────────────────────────────


def test_documented_constants_are_exact():
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_NAME == "Individual PAYE Test Support"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION == "2.1"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_BETA is True
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ONLY is True
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPERATION_ID == "createEmploymentHistoryTestData"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD == "POST"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_PATH_TEMPLATE == (
        "/individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}"
    )
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_ACCEPT == "application/vnd.hmrc.2.1+json"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_CONTENT_TYPE == "application/json"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE == "application/json"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS == 201
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS == {"HAPPY_PATH_1", "HAPPY_PATH_2"}
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS == {
        "employerName", "employerPayeReference",
    }
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS == {
        "offPayrollWorkFlag",
    }
    assert COMPLETENESS_UNVERIFIED == "UNVERIFIED"


def test_authentication_and_scope_are_documentation_facts_only():
    assert isinstance(HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_AUTHENTICATION, str)
    assert "application-restricted" in HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_AUTHENTICATION
    assert isinstance(HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES, frozenset)
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES == frozenset()
    assert isinstance(HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS, frozenset)


def test_scope_and_scenario_sets_are_immutable():
    with pytest.raises(AttributeError):
        HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES.add("read:something")  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS.add("HAPPY_PATH_3")  # type: ignore[attr-defined]


# ── Exact request construction, scenario presence and redaction ──────────────


def test_request_builds_exact_validated_intent():
    request = _request()
    assert type(request) is EmploymentTestSupportRequestIntent
    assert request.tax_year == "2026-27"


def test_scenario_omission_is_distinct_from_presence():
    omitted = _request()
    assert omitted.scenario is None
    assert omitted.scenario_present is False

    present = _request(scenario="HAPPY_PATH_1")
    assert present.scenario == "HAPPY_PATH_1"
    assert present.scenario_present is True

    assert omitted.scenario != present.scenario
    assert omitted.scenario_present != present.scenario_present


def test_both_documented_scenarios_are_accepted():
    assert _request(scenario="HAPPY_PATH_1").scenario == "HAPPY_PATH_1"
    assert _request(scenario="HAPPY_PATH_2").scenario == "HAPPY_PATH_2"


def test_request_representation_is_redacted_and_never_exposes_utr():
    request = _request(utr="1234567890", scenario="HAPPY_PATH_1")
    assert repr(request) == "EmploymentTestSupportRequestIntent([REDACTED])"
    assert "1234567890" not in repr(request)
    assert "1234567890" not in str(request)
    assert "HAPPY_PATH_1" not in repr(request)
    # No UTR-bearing path, raw UTR or sendable attributes are exposed.
    for attribute in (
        "utr", "_utr", "path", "url", "method", "headers", "body",
        "authorization", "token", "content_type", "accept",
    ):
        assert not hasattr(request, attribute), attribute


def test_request_intent_does_not_retain_raw_utr():
    request = _request(utr="1234567890")

    assert not hasattr(request, "utr")
    assert not hasattr(request, "_utr")
    assert not hasattr(request, "__utr")
    assert not hasattr(request, "_EmploymentTestSupportRequestIntent__utr")

    with pytest.raises(AttributeError):
        request.__dict__
    with pytest.raises(TypeError):
        vars(request)
    with pytest.raises(TypeError):
        asdict(request)
    assert "1234567890" not in repr(request)
    assert "1234567890" not in str(request)

    assert request.tax_year == "2026-27"
    assert hasattr(request, "_EmploymentTestSupportRequestIntent__tax_year")


def test_request_intent_is_immutable():
    request = _request()
    with pytest.raises(AttributeError):
        request.tax_year = "2027-28"
    with pytest.raises(AttributeError):
        request.utr = "9999999999"
    with pytest.raises(AttributeError):
        request.scenario = "HAPPY_PATH_1"
    with pytest.raises(AttributeError):
        del request.tax_year


def test_request_intent_has_no_mutable_namespace_or_replace_surface():
    request = _request()
    assert not hasattr(request, "__dict__")
    assert not hasattr(request, "replace")
    with pytest.raises(TypeError):
        asdict(request)


def test_request_intent_resists_copy_deepcopy_and_pickle():
    request = _request(utr="1234567890", scenario="HAPPY_PATH_1")
    with pytest.raises(TypeError):
        copy.copy(request)
    with pytest.raises(TypeError):
        copy.deepcopy(request)
    with pytest.raises(TypeError):
        pickle.dumps(request)


# ── Malformed UTR / tax year / scenario and constant non-echoing failures ────


@pytest.mark.parametrize("bad", [
    None, 1234567890, True, "123456789", "12345678901", "abcdefghij",
    "123456789A", "", " 1234567890", "123-456-789", "１２３４５６７８９０",
    "+1234567890",
])
def test_request_rejects_malformed_utr_without_echo(bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(utr=bad, tax_year="2026-27")
    if isinstance(bad, str) and bad:
        assert bad not in str(exc.value)


@pytest.mark.parametrize("bad", [
    None, 202627, True, "2026", "26-27", "2026-2", "2026/27", "2026-27 ",
    "abc-ef", "", "2026-275", "2026－27", "２０２６-２７",
])
def test_request_rejects_malformed_tax_year_without_echo(bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(utr="1234567890", tax_year=bad)
    if isinstance(bad, str) and bad:
        assert bad not in str(exc.value)


@pytest.mark.parametrize("bad", [
    None, 123, True, "HAPPY_PATH_3", "happy_path_1", " HAPPY_PATH_1",
    "HAPPY_PATH_1 ", "",
])
def test_request_rejects_malformed_scenario_without_echo(bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(
            utr="1234567890", tax_year="2026-27", scenario=bad
        )
    if isinstance(bad, str) and bad:
        assert bad not in str(exc.value)


def test_request_rejects_scenario_string_subclass():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        build_employment_test_support_request(
            utr="1234567890", tax_year="2026-27", scenario=_StrSubclass("HAPPY_PATH_1")
        )


def test_explicit_null_scenario_is_rejected_not_treated_as_omission():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _request(scenario=None)


def test_utr_wrong_type_message_is_constant():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(utr=1234567890, tax_year="2026-27")
    assert str(exc.value) == (
        "HMRC PAYE Test Support Employment contract: utr must be a string"
    )


def test_tax_year_wrong_format_message_is_constant():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(utr="1234567890", tax_year="26/27")
    assert str(exc.value) == (
        "HMRC PAYE Test Support Employment contract: tax_year must match YYYY-YY"
    )


# ── No sendable ProviderRequest / transport / credential / production surface ─


def test_request_intent_is_not_and_cannot_become_a_provider_request():
    request = _request()
    assert not isinstance(request, ProviderRequest)
    assert EmploymentTestSupportRequestIntent is not ProviderRequest
    assert not issubclass(EmploymentTestSupportRequestIntent, ProviderRequest)
    for attribute in ("method", "url", "headers", "body", "redacted_summary", "correlation_id"):
        assert not hasattr(request, attribute)


def test_module_contains_no_transport_or_credential_surface():
    import reserved.providers.hmrc_paye_test_support_employment_contract as contract

    for name in (
        "requests", "httpx", "urlopen", "HttpTransport", "GuardedTransport",
        "ProviderRequest", "authorization", "token", "client", "getenv", "environ",
    ):
        assert not hasattr(contract, name), name


def test_module_imports_only_stdlib_validation_helpers():
    import reserved.providers.hmrc_paye_test_support_employment_contract as contract

    tree = ast.parse(Path(contract.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    allowed = {"re", "unicodedata", "dataclasses", "typing", "__future__"}
    assert imported <= allowed, imported


def test_module_has_no_http_network_process_or_credential_imports():
    import reserved.providers.hmrc_paye_test_support_employment_contract as contract

    tree = ast.parse(Path(contract.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {
        "requests", "httpx", "urllib", "socket", "http", "aiohttp", "subprocess",
        "os", "sys", "flask", "reserved.providers.http_boundary",
        "reserved.auth", "reserved.config", "reserved.database", "reserved.api",
        "reserved.web", "reserved.providers.oauth_contracts",
        "reserved.providers.oauth_security", "reserved.providers.readiness",
        "reserved.engines", "reserved.providers.accounting",
    }
    for name in imported:
        for root in forbidden:
            assert not (name == root or name.startswith(root + ".")), name


# ── Immutable observations and non-sensitive representations ─────────────────


def test_observations_are_frozen_and_redacted():
    response = _observe()
    assert repr(response) == "EmploymentTestSupportResponseObservation([REDACTED])"
    assert repr(response.employments[0]) == (
        "EmploymentTestSupportRecordObservation([REDACTED])"
    )

    with pytest.raises(FrozenInstanceError):
        response.completeness = "COMPLETE"
    with pytest.raises(FrozenInstanceError):
        response.employments = ()
    with pytest.raises(FrozenInstanceError):
        response.employments[0].employer_name = "changed"

    assert isinstance(response.employments, tuple)
    assert isinstance(response.employments[0].absent_fields, frozenset)
    assert isinstance(response.employments[0].unknown_fields, frozenset)


def test_raw_response_payload_is_not_retained():
    response = _observe()
    assert not hasattr(response, "payload")
    assert not hasattr(response.employments[0], "payload")
    assert "employerName" not in repr(response.employments[0])
    assert "employerPayeReference" not in repr(response.employments[0])
    assert "Example Ltd" not in repr(response.employments[0])


def test_observations_are_safe_across_copy_deepcopy_and_pickle():
    response = _observe()
    for clone in (
        copy.copy(response),
        copy.deepcopy(response),
        pickle.loads(pickle.dumps(response)),
    ):
        assert type(clone) is EmploymentTestSupportResponseObservation
        assert clone == response
        assert clone.completeness == "UNVERIFIED"
        assert repr(clone) == "EmploymentTestSupportResponseObservation([REDACTED])"
        with pytest.raises(FrozenInstanceError):
            clone.completeness = "COMPLETE"


def test_observation_replace_valid_is_frozen_and_replace_invalid_fails_closed():
    response = _observe()
    replaced = replace(response, completeness="UNVERIFIED")
    assert replaced == response
    assert isinstance(replaced, EmploymentTestSupportResponseObservation)

    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(response, employments=["not-a-tuple"])
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(response, status_code=200)


def test_observations_reject_invalid_direct_construction():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            employer_name=123, employer_paye_reference="x"
        )
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27", status_code=200, employments=()
        )


# ── Constructor / replace exact-coherence (negative) ─────────────────────────


def _coherent_record():
    return _observe().employments[0]


def _coherent_response():
    return _observe()


def _record_kwargs(**overrides):
    kwargs = {
        "employer_name": "Example Ltd",
        "employer_paye_reference": "123/AB456",
        "absent_fields": frozenset({"offPayrollWorkFlag"}),
        "unknown_fields": frozenset(),
    }
    kwargs.update(overrides)
    return kwargs


@pytest.mark.parametrize("field", ["employer_name", "employer_paye_reference"])
@pytest.mark.parametrize("bad", [
    "\u202eMüller", "a\x00b", "\ud800", "\ue000", "\u0378",
])
def test_record_rejects_unsafe_employer_string_on_direct_construction(field, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(**{**_record_kwargs(), field: bad})


@pytest.mark.parametrize("field,max_length", [
    ("employer_name", RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH),
    ("employer_paye_reference", RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH),
])
def test_record_rejects_overlong_employer_string_on_direct_construction(field, max_length):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **{**_record_kwargs(), field: "x" * (max_length + 1)}
        )


@pytest.mark.parametrize("field", ["employer_name", "employer_paye_reference"])
@pytest.mark.parametrize("bad", ["\u202eMüller", "a\x00b", "\ud800"])
def test_record_rejects_unsafe_employer_string_through_replace(field, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_record(), **{field: bad})


@pytest.mark.parametrize("field,max_length", [
    ("employer_name", RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH),
    ("employer_paye_reference", RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH),
])
def test_record_rejects_overlong_employer_string_through_replace(field, max_length):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_record(), **{field: "x" * (max_length + 1)})


@pytest.mark.parametrize("flag,absent", [
    (None, frozenset()),
    (True, frozenset({"offPayrollWorkFlag"})),
    (False, frozenset({"offPayrollWorkFlag"})),
    (None, frozenset({"employerName"})),
    (True, frozenset({"employerName"})),
])
def test_record_rejects_optional_flag_absence_contradiction(flag, absent):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            employer_name="Example Ltd",
            employer_paye_reference="123/AB456",
            off_payroll_work_flag=flag,
            absent_fields=absent,
        )


@pytest.mark.parametrize("flag,absent", [
    (None, frozenset({"offPayrollWorkFlag"})),
    (True, frozenset()),
    (False, frozenset()),
])
def test_record_accepts_coherent_optional_flag_absence(flag, absent):
    record = EmploymentTestSupportRecordObservation(
        employer_name="Example Ltd",
        employer_paye_reference="123/AB456",
        off_payroll_work_flag=flag,
        absent_fields=absent,
    )
    assert record.off_payroll_work_flag is flag
    assert record.absent_fields == absent


def test_record_replace_rejects_incoherent_absent_fields():
    record = _coherent_record()
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(record, absent_fields=frozenset())


@pytest.mark.parametrize("flag", [True, False])
def test_record_replace_rejects_present_flag_with_absent_marker(flag):
    record = _coherent_record()
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(record, off_payroll_work_flag=flag)


@pytest.mark.parametrize("tax_year", [
    "26-27", "2026-2", "2026-27 ", "abc-ef", "", 202627, None,
])
def test_response_rejects_malformed_tax_year_on_direct_construction(tax_year):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year=tax_year, status_code=201, employments=()
        )


@pytest.mark.parametrize("status", [200, 202, 400, True, "201", 201.0])
def test_response_rejects_wrong_status_on_direct_construction(status):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27", status_code=status, employments=()
        )


@pytest.mark.parametrize("completeness", [
    "COMPLETE", "VERIFIED", "UNVERIFIED ", "", None, 123,
])
def test_response_rejects_non_unverified_completeness_on_direct_construction(completeness):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=(),
            completeness=completeness,
        )


def test_response_replace_rejects_malformed_tax_year():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_response(), tax_year="2026/27")


def test_response_replace_rejects_non_unverified_completeness():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_response(), completeness="COMPLETE")


def test_response_rejects_too_many_records_on_direct_construction():
    record = _coherent_record()
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=tuple(
                record for _ in range(RESERVED_DEFENSIVE_MAX_EMPLOYMENTS + 1)
            ),
        )


def test_response_replace_rejects_too_many_records():
    record = _coherent_record()
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(
            _coherent_response(),
            employments=tuple(
                record for _ in range(RESERVED_DEFENSIVE_MAX_EMPLOYMENTS + 1)
            ),
        )


def test_response_rejects_record_subclass_in_employments():
    class _RecordSubclass(EmploymentTestSupportRecordObservation):
        pass

    record = _RecordSubclass(
        employer_name="Example Ltd",
        employer_paye_reference="123/AB456",
        absent_fields=frozenset({"offPayrollWorkFlag"}),
    )
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27", status_code=201, employments=(record,)
        )


def test_response_replace_rejects_record_subclass_in_employments():
    class _RecordSubclass(EmploymentTestSupportRecordObservation):
        pass

    record = _RecordSubclass(
        employer_name="Example Ltd",
        employer_paye_reference="123/AB456",
        absent_fields=frozenset({"offPayrollWorkFlag"}),
    )
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_response(), employments=(record,))


def test_response_rejects_non_record_in_employments():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27", status_code=201, employments=("not-a-record",)
        )


@pytest.mark.parametrize("field_name", ["absent_fields", "unknown_fields"])
@pytest.mark.parametrize("bad", [set(), ["x"], "x", None, 123, {"offPayrollWorkFlag"}])
def test_record_rejects_wrong_type_field_name_set(field_name, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(**{**_record_kwargs(), field_name: bad})


@pytest.mark.parametrize("field_name", ["absent_fields", "unknown_fields"])
@pytest.mark.parametrize("bad_element", [123, True, None, b"bytes", 1.5])
def test_record_rejects_non_string_member_in_field_name_set(field_name, bad_element):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **{**_record_kwargs(), field_name: frozenset([bad_element])}
        )


@pytest.mark.parametrize("field_name", ["absent_fields", "unknown_fields"])
@pytest.mark.parametrize("bad_name", ["\u202e", "a\x00b", "\ud800", "\ue000", "\u0378"])
def test_record_rejects_unsafe_member_name_in_field_name_set(field_name, bad_name):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **{**_record_kwargs(), field_name: frozenset([bad_name])}
        )


@pytest.mark.parametrize("field_name", ["absent_fields", "unknown_fields"])
def test_record_rejects_overlong_member_name_in_field_name_set(field_name):
    bad_name = "x" * (RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH + 1)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **{**_record_kwargs(), field_name: frozenset([bad_name])}
        )


def test_record_rejects_too_many_unknown_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **_record_kwargs(
                unknown_fields=frozenset(
                    f"future_{i}" for i in range(RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS + 1)
                )
            )
        )


def test_record_rejects_too_many_absent_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **_record_kwargs(
                absent_fields=frozenset(
                    f"a{i}" for i in range(RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS + 1)
                )
            )
        )


@pytest.mark.parametrize("documented", [
    "employerName", "employerPayeReference", "offPayrollWorkFlag",
])
def test_record_rejects_documented_name_in_unknown_fields(documented):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **_record_kwargs(unknown_fields=frozenset({documented}))
        )


def test_record_replace_rejects_documented_name_in_unknown_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        replace(_coherent_record(), unknown_fields=frozenset({"employerName"}))


@pytest.mark.parametrize("required", ["employerName", "employerPayeReference"])
def test_record_rejects_required_name_in_absent_fields(required):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            **_record_kwargs(absent_fields=frozenset({required}))
        )


def test_response_rejects_employments_in_unknown_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=(),
            unknown_fields=frozenset({"employments"}),
        )


def test_response_rejects_employments_marked_absent():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=(),
            absent_fields=frozenset({"employments"}),
        )


def test_response_rejects_any_non_empty_absent_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=(),
            absent_fields=frozenset({"future"}),
        )


def test_response_rejects_non_string_member_in_unknown_fields():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27",
            status_code=201,
            employments=(),
            unknown_fields=frozenset([123]),
        )


def test_coherent_observations_round_trip_copy_deepcopy_and_pickle():
    record = _coherent_record()
    response = _coherent_response()
    for obj in (record, response):
        for clone in (copy.copy(obj), copy.deepcopy(obj), pickle.loads(pickle.dumps(obj))):
            assert type(clone) is type(obj)
            assert clone == obj

    clone = pickle.loads(pickle.dumps(response))
    assert clone.status_code == 201
    assert clone.completeness == "UNVERIFIED"
    assert clone.tax_year == "2026-27"
    assert clone.absent_fields == frozenset()
    assert clone.unknown_fields == frozenset()
    assert isinstance(clone.employments, tuple)
    assert clone.employments[0].off_payroll_work_flag is None
    assert clone.employments[0].absent_fields == frozenset({"offPayrollWorkFlag"})
    assert clone.employments[0].unknown_fields == frozenset()


# ── Exact media-type / status / schema handling ──────────────────────────────


def test_success_accepts_exact_documented_media_type_and_status():
    response = _observe()
    assert isinstance(response, EmploymentTestSupportResponseObservation)
    assert response.status_code == 201
    assert response.tax_year == "2026-27"
    assert response.completeness == "UNVERIFIED"


@pytest.mark.parametrize("content_type", [
    "application/vnd.hmrc.2.1+json",
    "text/html",
    "application/json; charset=utf-8",
    "Application/JSON",
    None,
    123,
])
def test_rejects_wrong_media_type(content_type):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(content_type=content_type)


@pytest.mark.parametrize("payload", [None, [], "not-a-dict", 123, True])
def test_success_rejects_non_object_top_level(payload):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=payload)


def test_success_rejects_missing_employments():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload={})


@pytest.mark.parametrize("employments", [None, {}, "x", 123, (1, 2), True])
def test_success_rejects_non_list_employments(employments):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload={"employments": employments})


def test_empty_employments_is_shape_valid_but_semantically_unverified():
    # Prose says "one or more", but the captured schema supplies no minItems, so
    # an empty array is accepted as shape-valid with UNVERIFIED completeness.
    response = _observe(payload={"employments": []})
    assert response.employments == ()
    assert response.completeness == "UNVERIFIED"


def test_success_rejects_non_object_employment_entry():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload={"employments": ["not-an-object"]})


# ── Missing / null / wrong-type / bool-as-int / subclass inputs ──────────────


@pytest.mark.parametrize("field", ["employerName", "employerPayeReference"])
def test_employment_rejects_missing_required(field):
    emp = _employment()
    del emp[field]
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(emp))


@pytest.mark.parametrize("field", ["employerName", "employerPayeReference"])
def test_employment_rejects_null_required(field):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: None})))


@pytest.mark.parametrize("field,bad", [
    ("employerName", 123),
    ("employerName", True),
    ("employerPayeReference", 123),
    ("employerPayeReference", True),
])
def test_employment_rejects_wrong_type_required(field, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field,attribute", [
    ("employerName", "employer_name"),
    ("employerPayeReference", "employer_paye_reference"),
])
@pytest.mark.parametrize("blank", ["", "   ", "\u00a0\u2009"])
def test_employment_accepts_empty_and_whitespace_strings_as_schema_valid(field, attribute, blank):
    # ``type: string`` with no evidenced ``minLength``: empty and separator
    # whitespace-only values are schema-valid but semantically unverified.
    response = _observe(payload=_success_payload(_employment(**{field: blank})))
    assert getattr(response.employments[0], attribute) == blank
    assert getattr(response.employments[0], attribute).strip() == ""


@pytest.mark.parametrize("field", ["employerName", "employerPayeReference"])
@pytest.mark.parametrize("bad", ["\t", "\n", "\r", "\x00", "a\tb", "a\nb", "a\x1fc"])
def test_employment_rejects_control_whitespace_and_raw_controls(field, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field", ["employerName", "employerPayeReference"])
@pytest.mark.parametrize("bad", [
    "\u202e", "\u200b", "safe\u202esuffix", "\ue000", "a\uf8ffb",
    "\u0378", "\ud800", "a\udfff", "\ufffe",
])
def test_employment_rejects_unicode_unsafe_values(field, bad):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field,attribute", [
    ("employerName", "employer_name"),
    ("employerPayeReference", "employer_paye_reference"),
])
@pytest.mark.parametrize("value", [
    "René Müller", "株式会社", "e\u0301tude", "M\u0301\u00fcller",
    "🏢 Example Ltd", "¡Hola! 日本語 123", "naïve café — 100%",
])
def test_employment_accepts_ordinary_unicode(field, attribute, value):
    response = _observe(payload=_success_payload(_employment(**{field: value})))
    assert getattr(response.employments[0], attribute) == value


def test_unicode_rejection_does_not_echo_value():
    bad = "\u202eMüller"
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        _observe(payload=_success_payload(_employment(employerName=bad)))
    assert "\u202e" not in str(exc.value)
    assert bad not in str(exc.value)


@pytest.mark.parametrize("bad", [1, 0, "true", "false", [], {}, None])
def test_off_payroll_work_flag_rejects_null_wrong_types_and_bool_as_int(bad):
    # The captured schema does not declare ``offPayrollWorkFlag`` nullable, so
    # explicit null and every non-bool present value fail closed.
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(offPayrollWorkFlag=bad)))


def test_off_payroll_work_flag_absent_true_and_false_are_distinct():
    absent = _observe(payload=_success_payload(_employment()))
    assert "offPayrollWorkFlag" in absent.employments[0].absent_fields
    assert absent.employments[0].off_payroll_work_flag is None

    flagged = _observe(payload=_success_payload(_employment(offPayrollWorkFlag=True)))
    assert flagged.employments[0].off_payroll_work_flag is True
    assert "offPayrollWorkFlag" not in flagged.employments[0].absent_fields

    unflagged = _observe(payload=_success_payload(_employment(offPayrollWorkFlag=False)))
    assert unflagged.employments[0].off_payroll_work_flag is False
    assert "offPayrollWorkFlag" not in unflagged.employments[0].absent_fields


class _StrSubclass(str):
    pass


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
    pass


class _IntSubclass(int):
    pass


def test_employment_rejects_string_subclass():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(_employment(employerName=_StrSubclass("Example Ltd"))))


def test_payload_rejects_dict_subclass():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_DictSubclass(employments=[_employment()]))


def test_employments_rejects_list_subclass():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload={"employments": _ListSubclass([_employment()])})


def test_status_rejects_int_subclass_and_bool():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(status_code=_IntSubclass(201))
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(status_code=True)


def test_request_rejects_utr_and_tax_year_subclasses():
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        build_employment_test_support_request(
            utr=_StrSubclass("1234567890"), tax_year="2026-27"
        )
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        build_employment_test_support_request(
            utr="1234567890", tax_year=_StrSubclass("2026-27")
        )


# ── Additive unknown names accepted without touching hostile values ──────────


class _Hostile:
    def __repr__(self):
        raise RuntimeError("repr touched")

    def __str__(self):
        raise RuntimeError("str touched")

    def __eq__(self, other):
        raise RuntimeError("eq touched")

    def __hash__(self):
        raise RuntimeError("hash touched")

    def __iter__(self):
        raise RuntimeError("iter touched")


def test_additive_unknown_members_are_accepted_without_inspecting_values():
    hostile = _Hostile()
    cyclic = {}
    cyclic["self"] = cyclic

    payload = _success_payload(
        _employment(some_future_field=hostile),
        future_top={"deep": [hostile]},
    )
    payload["future_unknown"] = hostile
    payload["cyclic_unknown"] = cyclic

    response = _observe(payload=payload)

    assert "some_future_field" in response.employments[0].unknown_fields
    assert "future_top" in response.unknown_fields
    assert "future_unknown" in response.unknown_fields
    assert "cyclic_unknown" in response.unknown_fields


def test_hostile_unknown_values_are_never_inspected_at_any_level():
    hostile = _Hostile()
    payload = _success_payload(_employment(future=hostile), future_top=hostile)
    payload["future_unknown"] = hostile
    result = _observe(payload=payload)
    assert "future" in result.employments[0].unknown_fields
    assert "future_top" in result.unknown_fields
    assert "future_unknown" in result.unknown_fields


# ── Open-schema member-name bounding and type checks ─────────────────────────


def test_member_names_reject_non_string_keys_at_every_level():
    top_level = _success_payload(_employment())
    top_level[1] = "x"
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=top_level)

    emp = _employment()
    emp[1] = "x"
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(emp))


def _assert_bad_member_name_rejected_at_every_level(name):
    top_level = _success_payload(_employment())
    top_level[name] = "x"
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=top_level)

    emp = _employment()
    emp[name] = "x"
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(emp))


@pytest.mark.parametrize("name", ["\x00name", "name\x1f", "\x7f", "\x9f", "a\tb"])
def test_member_names_reject_control_characters(name):
    _assert_bad_member_name_rejected_at_every_level(name)


@pytest.mark.parametrize("name", ["\ud800", "\udfff", "a\udc00b"])
def test_member_names_reject_lone_surrogates(name):
    _assert_bad_member_name_rejected_at_every_level(name)


@pytest.mark.parametrize("name", ["\ufffe", "\ufdd0"])
def test_member_names_reject_non_characters(name):
    _assert_bad_member_name_rejected_at_every_level(name)


@pytest.mark.parametrize("name", ["\u202e", "\u200b", "a\u202eb"])
def test_member_names_reject_format_controls(name):
    _assert_bad_member_name_rejected_at_every_level(name)


@pytest.mark.parametrize("name", ["\ue000", "a\uf8ffb"])
def test_member_names_reject_private_use(name):
    _assert_bad_member_name_rejected_at_every_level(name)


@pytest.mark.parametrize("name", ["\u0378", "a\u0378b"])
def test_member_names_reject_unassigned(name):
    _assert_bad_member_name_rejected_at_every_level(name)


def test_member_names_accept_ordinary_unicode_keys():
    name = "employé🏢_日"
    payload = _success_payload(_employment())
    payload[name] = "x"
    response = _observe(payload=payload)
    assert name in response.unknown_fields


def test_member_names_reject_overlong_names():
    name = "x" * (RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH + 1)
    _assert_bad_member_name_rejected_at_every_level(name)


def test_member_names_reject_oversized_object_member_count():
    payload = _success_payload(_employment())
    for index in range(RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS + 1):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        _observe(payload=payload)
    assert "object member count" in str(exc.value)


def test_member_names_reject_excessive_unknown_keys():
    payload = _success_payload(_employment())
    for index in range(RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS + 1):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        _observe(payload=payload)
    assert "unknown member count" in str(exc.value)


# ── Non-201 fail-closed boundary ─────────────────────────────────────────────


@pytest.mark.parametrize("status", [
    200, 202, 400, 401, 404, 500, 503, 0, -1,
])
def test_every_non_201_int_status_fails_closed(status):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        _observe(status_code=status)
    assert "undocumented HTTP status" in str(exc.value)


@pytest.mark.parametrize("status", [True, "201", 201.0])
def test_non_int_status_fails_closed(status):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(status_code=status)


def test_non_201_fails_closed_before_inspecting_body():
    hostile = _Hostile()
    # The body must never be parsed/echoed/retained/classified for a non-201.
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        _observe(
            status_code=500,
            content_type="application/json",
            payload={"code": "INTERNAL_SERVER_ERROR", "message": "x", "evil": hostile},
        )
    assert "undocumented HTTP status" in str(exc.value)


def test_non_201_does_not_classify_or_fabricate_error_codes():
    # A well-formed-looking provider error body is still unclassified: the
    # operation documents no endpoint-specific error responses or codes.
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(status_code=400, payload={"code": "SA_UTR_INVALID", "message": "x"})
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(status_code=404, payload={"code": "NOT_FOUND", "message": "x"})


# ── Reserved defensive bounds ────────────────────────────────────────────────


def test_defensive_bounds_are_present_and_labelled():
    assert RESERVED_DEFENSIVE_MAX_EMPLOYMENTS == 1000
    assert RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH == 512
    assert RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH == 64
    assert RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH == 256
    assert RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS == 1000
    assert RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS == 64


def test_employments_exceeding_defensive_bound_are_rejected():
    emp = _employment()
    payload = {"employments": [emp] * (RESERVED_DEFENSIVE_MAX_EMPLOYMENTS + 1)}
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=payload)


def test_employer_name_exceeding_defensive_bound_is_rejected():
    emp = _employment(employerName="x" * (RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH + 1))
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(emp))


def test_employer_paye_reference_exceeding_defensive_bound_is_rejected():
    emp = _employment(
        employerPayeReference="1" * (RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH + 1)
    )
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe(payload=_success_payload(emp))


# ── No conversion into tax-engine / cash / customer evidence ─────────────────


def test_observations_contain_no_tax_cash_or_customer_fields():
    response = _observe()
    forbidden = {
        "paid", "tax_paid", "tax_liability", "gross_pay", "net_pay", "canonical",
        "cash", "customer", "launch_ready", "evidence_id", "amount", "money",
    }
    assert forbidden.isdisjoint(response.__dataclass_fields__)
    assert forbidden.isdisjoint(response.employments[0].__dataclass_fields__)


def test_observations_are_not_paye_evidence():
    import reserved.providers.hmrc_paye_test_support_employment_contract as contract

    response = _observe()
    for name in ("PayeEvidence", "AccountingEntry", "CanonicalAccountingTaxInput"):
        assert not hasattr(contract, name)
    assert not isinstance(response, tuple)


# ── Existing adapter decision and fail-closed readiness gates ────────────────


def test_hmrc_provider_spec_remains_disabled():
    from reserved.providers.readiness import PROVIDERS

    hmrc = next(spec for spec in PROVIDERS if spec.name == "hmrc")
    assert hmrc.implementation_enabled is False


def test_adapter_decision_document_preserves_disabled_decision_and_gates():
    text = (REPO / "docs" / "HMRC_ADAPTER_IMPLEMENTATION_DECISION.md").read_text(encoding="utf-8")
    assert "do not implement or enable an HMRC HTTP adapter" in text
    assert "implementation_enabled=False" in text
    assert "Individual PAYE Test Support" in text
