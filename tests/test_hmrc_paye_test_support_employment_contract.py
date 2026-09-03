"""Synthetic, network-free tests for the HMRC Individual PAYE Test Support 2.1
employment fixture literal contract.

These tests exercise only the deterministic request/response contract, its
UTR-free request-binding boundary and its fail-closed validation. Nothing here
calls HMRC, performs HTTP, reads credentials, persists data or constructs
tax-engine/cash/customer evidence.
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
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ORIGIN,
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
    validate_employment_test_support_response_observation,
    _restore_response_observation,
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
    scenario=_UNSET,
):
    if payload is _UNSET:
        payload = _success_payload(_employment())
    return observe_employment_test_support_response(
        _request(utr=utr, tax_year=tax_year, scenario=scenario),
        status_code=status_code,
        content_type=content_type,
        payload=payload,
    )


class _StrSubclass(str):
    pass


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
    pass


class _IntSubclass(int):
    pass


class _Hostile:
    def __repr__(self):
        raise RuntimeError("repr touched")

    def __str__(self):
        raise RuntimeError("str touched")

    def __eq__(self, other):
        raise RuntimeError("eq touched")

    def __hash__(self):
        raise RuntimeError("hash touched")

    def __bool__(self):
        raise RuntimeError("bool touched")

    def __iter__(self):
        raise RuntimeError("iter touched")


class _HostileStr(str):
    def __eq__(self, other):
        raise RuntimeError("eq touched")

    def __hash__(self):
        raise RuntimeError("hash touched")

    def __repr__(self):
        raise RuntimeError("repr touched")

    def __str__(self):
        raise RuntimeError("str touched")


class _HashableHostile:
    """Hashable object whose comparison/representation/iteration hooks raise."""

    def __hash__(self):
        return 0

    def __eq__(self, other):
        raise RuntimeError("eq touched")

    def __repr__(self):
        raise RuntimeError("repr touched")

    def __str__(self):
        raise RuntimeError("str touched")

    def __bool__(self):
        raise RuntimeError("bool touched")

    def __iter__(self):
        raise RuntimeError("iter touched")


class _HostileIterable(list):
    def __iter__(self):
        raise RuntimeError("iter touched")


# ── Exact documented constants ───────────────────────────────────────────────


def test_documented_constants_are_exact():
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_NAME == "Individual PAYE Test Support"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION == "2.1"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_BETA is True
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ONLY is True
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPERATION_ID == "createEmploymentHistoryTestData"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD == "POST"
    assert HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ORIGIN == (
        "https://test-api.service.hmrc.gov.uk"
    )
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


# ── Request identity: equality, hash, copy/deepcopy/pickle and tampering ─────


def test_request_intent_copy_deepcopy_and_pickle_are_coherent():
    request = _request(utr="1234567890", scenario="HAPPY_PATH_1")
    for clone in (
        copy.copy(request),
        copy.deepcopy(request),
        pickle.loads(pickle.dumps(request)),
    ):
        assert type(clone) is EmploymentTestSupportRequestIntent
        assert clone == request
        assert hash(clone) == hash(request)
        assert clone.tax_year == request.tax_year
        assert clone.scenario == request.scenario
        assert clone.scenario_present is request.scenario_present


def test_request_intent_identity_is_correlation_bound_and_scenario_sensitive():
    a = _request(utr="1111111111", scenario="HAPPY_PATH_1")
    b = _request(utr="1111111111", scenario="HAPPY_PATH_1")
    c = _request(utr="2222222222", scenario="HAPPY_PATH_1")
    # Separately constructed intents are distinct even with identical semantics,
    # and the distinction is UTR-free: it comes from the opaque correlation id.
    assert len({a, b, c}) == 3

    assert a != _request(utr="1111111111", scenario="HAPPY_PATH_2")
    assert a != _request(utr="1111111111", scenario="HAPPY_PATH_2", tax_year="2025-26")
    assert a != _request(utr="1111111111")
    assert a != "not-a-request"

    # copy/deepcopy/pickle preserve the same correlation-bound identity.
    for clone in (copy.copy(a), copy.deepcopy(a), pickle.loads(pickle.dumps(a))):
        assert clone == a
        assert hash(clone) == hash(a)


def _tamper_request(request, **fields):
    for name, value in fields.items():
        object.__setattr__(
            request, f"_EmploymentTestSupportRequestIntent__{name}", value
        )
    return request


@pytest.mark.parametrize("field,value", [
    ("tax_year", 202627),
    ("tax_year", "26-27"),
    ("scenario", "HAPPY_PATH_3"),
    ("scenario", 123),
    ("scenario_present", None),
    ("scenario_present", "yes"),
    ("method", "GET"),
    ("method", None),
    ("sandbox_origin", "https://evil.example"),
    ("path_template", "/other/{utr}/{taxYear}"),
    ("accept", "text/plain"),
    ("content_type", "text/plain"),
    ("response_content_type", "text/plain"),
    ("api_version", "3.0"),
    ("correlation_id", None),
    ("correlation_id", "short"),
    ("correlation_id", "Z" * 64),
    ("correlation_id", "x" * 63),
])
def test_request_intent_low_level_invalid_mutation_fails_closed(field, value):
    request = _tamper_request(_request(scenario="HAPPY_PATH_1"), **{field: value})
    for operation in (
        lambda r: r == _request(scenario="HAPPY_PATH_1"),
        hash,
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
        lambda r: r.__reduce__(),
    ):
        with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
            operation(request)


def test_request_intent_subclass_is_rejected():
    class _IntentSubclass(EmploymentTestSupportRequestIntent):
        pass

    forged = object.__new__(_IntentSubclass)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _request(scenario="HAPPY_PATH_1") == forged


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

    allowed = {
        "re", "unicodedata", "dataclasses", "typing", "__future__",
        "hashlib", "json", "secrets", "weakref",
    }
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


def test_response_observation_replace_is_unavailable():
    response = _observe()
    for changes in (
        {},
        {"completeness": "UNVERIFIED"},
        {"status_code": 201},
        {"tax_year": "2026-27"},
        {"employments": ()},
    ):
        with pytest.raises(TypeError):
            replace(response, **changes)


def test_observations_reject_invalid_direct_construction():
    # The record observation is a validated, directly-constructible value object.
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        EmploymentTestSupportRecordObservation(
            employer_name=123, employer_paye_reference="x"
        )
    # The response observation is observer-constructed only.
    with pytest.raises(TypeError):
        EmploymentTestSupportResponseObservation(
            tax_year="2026-27", status_code=201, employments=()
        )
    with pytest.raises(TypeError):
        EmploymentTestSupportResponseObservation()


# ── Low-level observation tampering helpers ──────────────────────────────────


def _mutate(observation, **fields):
    for name, value in fields.items():
        object.__setattr__(observation, name, value)
    return observation


def _assert_revalidation_rejects(observation):
    for operation in (
        lambda o: o == o,
        hash,
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
        lambda o: o.__reduce__(),
    ):
        with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
            operation(observation)


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


# ── Record observation: direct construction / replace exact-coherence ───────


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


# ── Response observation: low-level mutation must fail closed ────────────────


@pytest.mark.parametrize("field,value", [
    ("tax_year", "2025-26"),
    ("scenario", "HAPPY_PATH_2"),
    ("scenario_present", False),
])
def test_response_rejects_derived_context_substitution(field, value):
    response = _observe(scenario="HAPPY_PATH_1")
    _assert_revalidation_rejects(_mutate(response, **{field: value}))


@pytest.mark.parametrize("field,value", [
    ("status_code", 200),
    ("status_code", True),
    ("status_code", "201"),
    ("completeness", "COMPLETE"),
    ("completeness", None),
    ("employments", ("not-a-record",)),
    ("employments", []),
    ("absent_fields", frozenset({"employments"})),
    ("unknown_fields", frozenset({"employments"})),
    ("unknown_fields", frozenset([123])),
])
def test_response_rejects_fact_substitution(field, value):
    response = _observe()
    _assert_revalidation_rejects(_mutate(response, **{field: value}))


def test_response_rejects_too_many_records_via_mutation():
    record = _coherent_record()
    response = _observe()
    _assert_revalidation_rejects(
        _mutate(
            response,
            employments=tuple(
                record for _ in range(RESERVED_DEFENSIVE_MAX_EMPLOYMENTS + 1)
            ),
        )
    )


def test_response_rejects_record_subclass_via_mutation():
    class _RecordSubclass(EmploymentTestSupportRecordObservation):
        pass

    record = _RecordSubclass(
        employer_name="Example Ltd",
        employer_paye_reference="123/AB456",
        absent_fields=frozenset({"offPayrollWorkFlag"}),
    )
    response = _observe()
    _assert_revalidation_rejects(_mutate(response, employments=(record,)))


def test_response_rejects_coordinated_request_and_binding_substitution():
    h1 = _observe(scenario="HAPPY_PATH_1")
    h2 = _observe(scenario="HAPPY_PATH_2")
    # Swap only the request (binding and derived fields remain HAPPY_PATH_1).
    _assert_revalidation_rejects(_mutate(h1, request=h2.request))
    # Swap only the binding (request and derived fields remain HAPPY_PATH_1).
    _assert_revalidation_rejects(_mutate(h1, _request_binding=h2._request_binding))
    # Swap request + binding coherently but leave the derived fields stale.
    _assert_revalidation_rejects(
        _mutate(h1, request=h2.request, _request_binding=h2._request_binding)
    )


@pytest.mark.parametrize("field", ["tax_year", "scenario"])
def test_response_rejection_does_not_invoke_hostile_string_hooks(field):
    response = _observe()
    _mutate(response, **{field: _HostileStr("2026-27")})
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        response == response
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        hash(response)


def test_response_rejection_does_not_invoke_hostile_fact_hooks():
    response = _observe()
    _mutate(response, status_code=_Hostile())
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        response == response
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        copy.copy(response)


# ── Exact request → response binding across scenarios ────────────────────────


def test_each_scenario_survives_exact_request_response_binding():
    cases = {
        "omitted": (_request(), None, False),
        "HAPPY_PATH_1": (_request(scenario="HAPPY_PATH_1"), "HAPPY_PATH_1", True),
        "HAPPY_PATH_2": (_request(scenario="HAPPY_PATH_2"), "HAPPY_PATH_2", True),
    }
    for request, scenario, present in cases.values():
        response = observe_employment_test_support_response(
            request,
            status_code=201,
            content_type="application/json",
            payload=_success_payload(_employment()),
        )
        assert response.tax_year == "2026-27"
        assert response.scenario == scenario
        assert response.scenario_present is present
        assert response.request == request

        clone = pickle.loads(pickle.dumps(response))
        assert clone == response
        assert clone.tax_year == "2026-27"
        assert clone.scenario == scenario
        assert clone.scenario_present is present


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
    assert clone.scenario is None
    assert clone.scenario_present is False
    assert clone.absent_fields == frozenset()
    assert clone.unknown_fields == frozenset()
    assert isinstance(clone.employments, tuple)
    assert clone.employments[0].off_payroll_work_flag is None
    assert clone.employments[0].absent_fields == frozenset({"offPayrollWorkFlag"})
    assert clone.employments[0].unknown_fields == frozenset()


def test_no_utr_leaks_through_state_representation_errors_or_serialization():
    request = _request(utr="1234567890", scenario="HAPPY_PATH_1")
    response = observe_employment_test_support_response(
        request,
        status_code=201,
        content_type="application/json",
        payload=_success_payload(_employment()),
    )
    for obj in (request, response, response.employments[0]):
        assert "1234567890" not in repr(obj)
        assert "1234567890" not in str(obj)
        assert b"1234567890" not in pickle.dumps(obj)

    with pytest.raises(HMRCPayeTestSupportEmploymentContractError) as exc:
        build_employment_test_support_request(utr="1234567890", tax_year="not-a-year")
    assert "1234567890" not in str(exc.value)


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


# ── Opaque per-request correlation identity and observer-bound integrity ─────


def test_request_identity_is_unique_per_construction_and_instance_stable():
    first = _request(utr="1234567890", tax_year="2026-27", scenario="HAPPY_PATH_1")
    same = _request(utr="1234567890", tax_year="2026-27", scenario="HAPPY_PATH_1")
    other_utr = _request(utr="0987654321", tax_year="2026-27", scenario="HAPPY_PATH_1")
    other_year = _request(utr="1234567890", tax_year="2027-28", scenario="HAPPY_PATH_1")
    other_scenario = _request(utr="1234567890", tax_year="2026-27", scenario="HAPPY_PATH_2")
    assert len({first, same, other_utr, other_year, other_scenario}) == 5
    for clone in (copy.copy(first), copy.deepcopy(first), pickle.loads(pickle.dumps(first))):
        assert clone == first
        assert hash(clone) == hash(first)
    assert b"1234567890" not in pickle.dumps(first)


def test_request_only_substitution_is_rejected():
    original = _observe(utr="1234567890", scenario="HAPPY_PATH_1")
    same_semantics = _request(utr="0987654321", scenario="HAPPY_PATH_1")
    mutated = _mutate(original, request=same_semantics)
    _assert_revalidation_rejects(mutated)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        validate_employment_test_support_response_observation(mutated)


def test_identical_semantics_wholesale_provenance_swap_fails_all_paths():
    for clone_kind in ("low-level", "copy", "deepcopy", "pickle"):
        original = _observe(utr="1234567890", scenario="HAPPY_PATH_1")
        other = _observe(utr="0987654321", scenario="HAPPY_PATH_1")
        if clone_kind == "low-level":
            forged = object.__new__(EmploymentTestSupportResponseObservation)
            for name, value in vars(original).items():
                object.__setattr__(forged, name, value)
        elif clone_kind == "copy":
            forged = copy.copy(original)
        elif clone_kind == "deepcopy":
            forged = copy.deepcopy(original)
        else:
            forged = pickle.loads(pickle.dumps(original))

        for name in (
            "request", "_request_binding", "_source_binding", "tax_year",
            "scenario", "scenario_present", "_observation_integrity",
        ):
            object.__setattr__(forged, name, getattr(other, name))

        for operation in (
            validate_employment_test_support_response_observation,
            copy.copy,
            copy.deepcopy,
            pickle.dumps,
            hash,
        ):
            with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
                operation(forged)


def test_each_success_payload_component_is_integrity_bound():
    response = _observe()
    # Replace employments with another *valid* tuple of differing values.
    swapped_employments = _mutate(
        response,
        employments=(EmploymentTestSupportRecordObservation(
            **_record_kwargs(
                employer_name="Other Ltd",
                employer_paye_reference="999/ZZ999",
            )
        ),),
    )
    _assert_revalidation_rejects(swapped_employments)
    # Replace unknown_fields with another *valid* unknown-name set.
    swapped_unknown = _mutate(response, unknown_fields=frozenset({"x-extra"}))
    _assert_revalidation_rejects(swapped_unknown)


def test_each_retained_employment_value_is_integrity_bound():
    response = _observe()
    _mutate(response.employments[0], employer_name="Renamed Ltd")
    _assert_revalidation_rejects(response)


def test_coherent_scenario_relabel_is_rejected():
    original = _observe(utr="1234567890", scenario="HAPPY_PATH_1")
    _assert_revalidation_rejects(_mutate(original, scenario="HAPPY_PATH_2"))


def test_complete_payload_state_mutation_is_rejected():
    response = _observe()
    mutated = _mutate(
        response,
        employments=(EmploymentTestSupportRecordObservation(
            **_record_kwargs(
                employer_name="Other Ltd",
                employer_paye_reference="999/ZZ999",
            )
        ),),
        unknown_fields=frozenset({"x-extra"}),
    )
    _assert_revalidation_rejects(mutated)


def test_unrelated_observation_integrity_value_is_rejected():
    a = _observe(utr="1234567890", scenario="HAPPY_PATH_1")
    b = _observe(utr="0987654321", scenario="HAPPY_PATH_1")
    _assert_revalidation_rejects(
        _mutate(a, _observation_integrity=b._observation_integrity)
    )


def test_low_level_clone_is_unregistered_and_unsupported():
    response = _observe()
    forged = object.__new__(EmploymentTestSupportResponseObservation)
    for name, value in vars(response).items():
        object.__setattr__(forged, name, value)
    _assert_revalidation_rejects(forged)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        validate_employment_test_support_response_observation(forged)


def test_response_missing_state_is_rejected():
    response = _observe()
    state = object.__getattribute__(response, "__dict__")
    del state["_observation_integrity"]
    _assert_revalidation_rejects(response)


def test_response_extra_state_shadowing_helper_is_rejected():
    response = _observe()
    object.__setattr__(response, "_response_state", _Hostile())
    _assert_revalidation_rejects(response)


def test_record_extra_state_shadowing_helper_is_rejected():
    record = _coherent_record()
    object.__setattr__(record, "_require_record_observation", _Hostile())
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        record == record


def test_response_subclass_is_rejected():
    class _ResponseSubclass(EmploymentTestSupportResponseObservation):
        pass

    forged = object.__new__(_ResponseSubclass)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _observe() == forged
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        validate_employment_test_support_response_observation(forged)


def test_record_subclass_is_rejected():
    class _RecordSubclass(EmploymentTestSupportRecordObservation):
        pass

    forged = object.__new__(_RecordSubclass)
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _coherent_record() == forged


def test_hostile_request_binding_hooks_are_not_invoked():
    response = _observe()
    _mutate(response, _request_binding=_Hostile(), _source_binding=_Hostile())
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        validate_employment_test_support_response_observation(response)


def test_hostile_integrity_and_fact_hooks_are_not_invoked():
    response = _observe()
    _mutate(response, _observation_integrity=_Hostile(), status_code=_Hostile())
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        validate_employment_test_support_response_observation(response)


# ── Reconstruction argument preflight ────────────────────────────────────────

_RESTORE_BINDING = 0
_RESTORE_STATUS = 1
_RESTORE_EMPLOYMENTS = 2
_RESTORE_COMPLETENESS = 3
_RESTORE_ABSENT = 4
_RESTORE_UNKNOWN = 5


def _forged_record_missing_field():
    record = object.__new__(EmploymentTestSupportRecordObservation)
    for name, value in (
        ("employer_name", "Example Ltd"),
        ("employer_paye_reference", "123/AB456"),
        ("off_payroll_work_flag", None),
        ("absent_fields", frozenset({"offPayrollWorkFlag"})),
    ):
        object.__setattr__(record, name, value)
    return record


def _restore_args():
    response = _observe()
    _, args = response.__reduce__()
    return args


def _restore_with(index, value):
    args = list(_restore_args())
    args[index] = value
    return _restore_response_observation(*args)


@pytest.mark.parametrize("index,factory", [
    pytest.param(_RESTORE_BINDING, lambda: _Hostile(), id="binding-generic-hostile"),
    pytest.param(_RESTORE_BINDING, lambda: [], id="binding-list"),
    pytest.param(_RESTORE_BINDING, lambda: ("correlation-token",), id="binding-short-tuple"),
    pytest.param(_RESTORE_STATUS, lambda: _Hostile(), id="status-generic-hostile"),
    pytest.param(_RESTORE_STATUS, lambda: True, id="status-bool"),
    pytest.param(_RESTORE_STATUS, lambda: _IntSubclass(201), id="status-int-subclass"),
    pytest.param(_RESTORE_STATUS, lambda: "201", id="status-string"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: _Hostile(), id="employments-generic-hostile"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: [], id="employments-list"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: _ListSubclass(), id="employments-list-subclass"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: _HostileIterable(), id="employments-hostile-iterable"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: (object(),), id="employments-member-object"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: (_Hostile(),), id="employments-member-hostile"),
    pytest.param(_RESTORE_EMPLOYMENTS, lambda: (_forged_record_missing_field(),), id="employments-member-missing-field"),
    pytest.param(_RESTORE_COMPLETENESS, lambda: _Hostile(), id="completeness-generic-hostile"),
    pytest.param(_RESTORE_COMPLETENESS, lambda: _HostileStr("UNVERIFIED"), id="completeness-str-subclass"),
    pytest.param(_RESTORE_COMPLETENESS, lambda: "COMPLETE", id="completeness-wrong-value"),
    pytest.param(_RESTORE_COMPLETENESS, lambda: 123, id="completeness-int"),
    pytest.param(_RESTORE_ABSENT, lambda: _Hostile(), id="absent-generic-hostile"),
    pytest.param(_RESTORE_ABSENT, lambda: [], id="absent-list"),
    pytest.param(_RESTORE_ABSENT, lambda: set(), id="absent-set"),
    pytest.param(_RESTORE_ABSENT, lambda: frozenset({_HashableHostile()}), id="absent-hostile-member"),
    pytest.param(_RESTORE_ABSENT, lambda: frozenset({123}), id="absent-int-member"),
    pytest.param(_RESTORE_ABSENT, lambda: frozenset({"employments"}), id="absent-nonempty"),
    pytest.param(_RESTORE_UNKNOWN, lambda: _Hostile(), id="unknown-generic-hostile"),
    pytest.param(_RESTORE_UNKNOWN, lambda: [], id="unknown-list"),
    pytest.param(_RESTORE_UNKNOWN, lambda: set(), id="unknown-set"),
    pytest.param(_RESTORE_UNKNOWN, lambda: frozenset({_HashableHostile()}), id="unknown-hostile-member"),
    pytest.param(_RESTORE_UNKNOWN, lambda: frozenset({123}), id="unknown-int-member"),
    pytest.param(_RESTORE_UNKNOWN, lambda: frozenset({"employments"}), id="unknown-documented-member"),
])
def test_restore_preflights_every_reconstruction_argument(index, factory):
    with pytest.raises(HMRCPayeTestSupportEmploymentContractError):
        _restore_with(index, factory())
