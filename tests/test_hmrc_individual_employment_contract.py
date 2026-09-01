"""Synthetic, network-free tests for the HMRC Individual Employment 1.2
literal contract.

These tests exercise only the deterministic request/response contract and its
fail-closed validation. Nothing here calls HMRC, performs HTTP, reads
credentials, persists data or constructs tax-engine/cash/customer evidence.
"""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from types import MappingProxyType

import pytest

from reserved.providers.hmrc_individual_employment_contract import (
    COMPLETENESS_UNVERIFIED,
    HMRC_INDIVIDUAL_EMPLOYMENT_ACCEPT,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
    HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES,
    HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_STATUSES,
    HMRC_INDIVIDUAL_EMPLOYMENT_OAUTH_SCOPE,
    HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS,
    HMRC_INDIVIDUAL_EMPLOYMENT_PATH_TEMPLATE,
    HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS,
    HMRC_INDIVIDUAL_EMPLOYMENT_RESPONSE_CONTENT_TYPE,
    HMRC_INDIVIDUAL_EMPLOYMENT_SANDBOX_ORIGIN,
    HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYMENTS,
    RESERVED_DEFENSIVE_MAX_ERROR_CODE_LENGTH,
    RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH,
    RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS,
    RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS,
    EmploymentErrorObservation,
    EmploymentHistoryObservation,
    EmploymentRecordObservation,
    HMRCIndividualEmploymentContractError,
    IndividualEmploymentRequestIntent,
    build_individual_employment_request,
    observe_individual_employment_response,
)
from reserved.providers.http_boundary import ProviderRequest

REPO = Path(__file__).resolve().parents[1]


def _request(*, utr="1234567890", tax_year="2026-27"):
    return build_individual_employment_request(utr=utr, tax_year=tax_year)


def _employment(**overrides):
    record = {
        "employerPayeReference": "123/AB12345",
        "employerName": "Example Ltd",
    }
    record.update(overrides)
    return record


def _success_payload(*employments, **top_level):
    payload = {"employments": list(employments)}
    payload.update(top_level)
    return payload


_UNSET = object()


def _observe(*, status_code=200, content_type="application/json", payload=_UNSET, utr="1234567890", tax_year="2026-27"):
    if payload is _UNSET:
        payload = _success_payload(_employment())
    return observe_individual_employment_response(
        _request(utr=utr, tax_year=tax_year),
        status_code=status_code,
        content_type=content_type,
        payload=payload,
    )


# ── Exact documented constants ───────────────────────────────────────────────


def test_documented_constants_are_exact():
    assert HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME == "Individual Employment"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION == "1.2"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_SANDBOX_ORIGIN == "https://test-api.service.hmrc.gov.uk"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_PATH_TEMPLATE == (
        "/individual-employment/sa/{utr}/annual-summary/{taxYear}"
    )
    assert HMRC_INDIVIDUAL_EMPLOYMENT_ACCEPT == "application/vnd.hmrc.1.2+json"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_OAUTH_SCOPE == "read:individual-employment"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_RESPONSE_CONTENT_TYPE == "application/json"
    assert HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS == 200
    assert HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_STATUSES == {400, 401, 404}
    assert HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES == {
        400: {"SA_UTR_INVALID", "TAX_YEAR_INVALID"},
        401: {"UNAUTHORIZED"},
        404: {"NOT_FOUND"},
    }
    assert HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS == {
        "employerPayeReference", "employerName",
    }
    assert HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS == {
        "offPayrollWorkFlag",
    }
    assert COMPLETENESS_UNVERIFIED == "UNVERIFIED"


def test_sandbox_origin_is_not_the_production_origin():
    assert HMRC_INDIVIDUAL_EMPLOYMENT_SANDBOX_ORIGIN != "https://api.service.hmrc.gov.uk"
    assert "test-api" in HMRC_INDIVIDUAL_EMPLOYMENT_SANDBOX_ORIGIN


def test_error_code_mapping_is_immutable_and_cannot_authorize_injection():
    # Outer mapping is an immutable mappingproxy; nested sets are frozensets.
    assert isinstance(HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES, MappingProxyType)
    for codes in HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES.values():
        assert isinstance(codes, frozenset)

    with pytest.raises(TypeError):
        HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES[400] = {"INJECTED"}  # type: ignore[index]
    with pytest.raises(TypeError):
        HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES[500] = {"INJECTED"}  # type: ignore[index]
    with pytest.raises(TypeError):
        del HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES[404]  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES[404].add("INJECTED")  # type: ignore[attr-defined]

    # Exact documented status/code pairing remains intact.
    assert HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES == {
        400: {"SA_UTR_INVALID", "TAX_YEAR_INVALID"},
        401: {"UNAUTHORIZED"},
        404: {"NOT_FOUND"},
    }


# ── Exact request construction and redaction ─────────────────────────────────


def test_request_builds_exact_validated_intent():
    request = _request()
    assert type(request) is IndividualEmploymentRequestIntent
    assert request.tax_year == "2026-27"


def test_request_representation_is_redacted_and_never_exposes_utr():
    request = _request(utr="1234567890")
    assert repr(request) == "IndividualEmploymentRequestIntent([REDACTED])"
    assert "1234567890" not in repr(request)
    assert "1234567890" not in str(request)
    # No UTR-bearing path, raw UTR or sendable attributes are exposed.
    assert not hasattr(request, "utr")
    assert not hasattr(request, "_utr")
    assert not hasattr(request, "path")
    assert not hasattr(request, "url")
    assert not hasattr(request, "method")
    assert not hasattr(request, "headers")
    assert not hasattr(request, "body")
    assert not hasattr(request, "authorization")


def test_request_intent_does_not_retain_raw_utr():
    request = _request(utr="1234567890")

    # Conventional and name-mangled private attributes never expose the UTR.
    assert not hasattr(request, "utr")
    assert not hasattr(request, "_utr")
    assert not hasattr(request, "__utr")
    assert not hasattr(request, "_IndividualEmploymentRequestIntent__utr")

    # Serialization/conversion helpers and the instance namespace expose no UTR.
    with pytest.raises(AttributeError):
        request.__dict__
    with pytest.raises(TypeError):
        vars(request)
    with pytest.raises(TypeError):
        asdict(request)
    assert "1234567890" not in repr(request)
    assert "1234567890" not in str(request)

    # The only retained state is the non-sensitive, validated tax year.
    assert request.tax_year == "2026-27"
    assert hasattr(request, "_IndividualEmploymentRequestIntent__tax_year")


def test_request_intent_is_immutable():
    request = _request()
    with pytest.raises(AttributeError):
        request.tax_year = "2027-28"
    with pytest.raises(AttributeError):
        request.utr = "9999999999"
    with pytest.raises(AttributeError):
        del request.tax_year


# ── Malformed UTR / tax year and constant non-echoing failures ───────────────


@pytest.mark.parametrize("bad", [
    None, 1234567890, True, "123456789", "12345678901", "abcdefghij",
    "123456789A", "", " 1234567890",
])
def test_request_rejects_malformed_utr_without_echo(bad):
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        build_individual_employment_request(utr=bad, tax_year="2026-27")
    if isinstance(bad, str) and bad:
        assert bad not in str(exc.value)


@pytest.mark.parametrize("bad", [
    None, 202627, True, "2026", "26-27", "2026-2", "2026/27", "2026-27 ",
    "abc-ef", "", "2026-275",
])
def test_request_rejects_malformed_tax_year_without_echo(bad):
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        build_individual_employment_request(utr="1234567890", tax_year=bad)
    if isinstance(bad, str) and bad:
        assert bad not in str(exc.value)


def test_utr_wrong_type_message_is_constant():
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        build_individual_employment_request(utr=1234567890, tax_year="2026-27")
    assert str(exc.value) == "HMRC Individual Employment contract: utr must be a string"


def test_tax_year_wrong_format_message_is_constant():
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        build_individual_employment_request(utr="1234567890", tax_year="26/27")
    assert str(exc.value) == (
        "HMRC Individual Employment contract: tax_year must match YYYY-YY"
    )


# ── No sendable ProviderRequest / transport / credential / production surface ─


def test_request_intent_is_not_and_cannot_become_a_provider_request():
    request = _request()
    assert not isinstance(request, ProviderRequest)
    assert IndividualEmploymentRequestIntent is not ProviderRequest
    assert not issubclass(IndividualEmploymentRequestIntent, ProviderRequest)
    for attribute in ("method", "url", "headers", "body", "redacted_summary", "correlation_id"):
        assert not hasattr(request, attribute)


def test_module_contains_no_transport_or_credential_surface():
    import reserved.providers.hmrc_individual_employment_contract as contract

    for name in ("requests", "httpx", "urlopen", "HttpTransport", "GuardedTransport",
                 "ProviderRequest", "authorization", "token", "client"):
        assert not hasattr(contract, name), name


def test_module_imports_no_production_evidence_or_web_surface():
    import reserved.providers.hmrc_individual_employment_contract as contract

    tree = ast.parse(Path(contract.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = ("reserved.engines", "reserved.providers.accounting", "reserved.web")
    for name in imported:
        assert not name.startswith(forbidden), name


# ── Immutable observations and non-sensitive representations ─────────────────


def test_observations_are_frozen_and_redacted():
    history = _observe()
    assert repr(history) == "EmploymentHistoryObservation([REDACTED])"
    assert repr(history.employments[0]) == "EmploymentRecordObservation([REDACTED])"

    with pytest.raises(FrozenInstanceError):
        history.completeness = "COMPLETE"
    with pytest.raises(FrozenInstanceError):
        history.employments = ()
    with pytest.raises(FrozenInstanceError):
        history.employments[0].employer_name = "changed"

    assert isinstance(history.employments, tuple)
    assert isinstance(history.employments[0].absent_fields, frozenset)
    assert isinstance(history.employments[0].unknown_fields, frozenset)


def test_raw_response_payload_is_not_retained():
    history = _observe()
    assert not hasattr(history, "payload")
    assert not hasattr(history.employments[0], "payload")
    assert "employerPayeReference" not in repr(history.employments[0])
    assert "Example Ltd" not in repr(history.employments[0])


# ── Exact media-type / status / schema handling ──────────────────────────────


def test_success_accepts_exact_documented_media_type_and_status():
    history = _observe()
    assert isinstance(history, EmploymentHistoryObservation)
    assert history.status_code == 200
    assert history.tax_year == "2026-27"
    assert history.completeness == "UNVERIFIED"


@pytest.mark.parametrize("content_type", [
    "application/vnd.hmrc.1.2+json",
    "text/html",
    "application/json; charset=utf-8",
    "Application/JSON",
    None,
    123,
])
def test_rejects_wrong_media_type(content_type):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(content_type=content_type)


@pytest.mark.parametrize("status", [201, 204, 500, 503, 0, -1, True, "200"])
def test_rejects_undocumented_or_non_int_status(status):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=status)


@pytest.mark.parametrize("payload", [None, [], "not-a-dict", 123])
def test_success_rejects_non_object_top_level(payload):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=payload)


def test_success_rejects_missing_employments():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload={})


@pytest.mark.parametrize("employments", [None, {}, "x", 123, (1, 2)])
def test_success_rejects_non_list_employments(employments):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload={"employments": employments})


def test_success_rejects_empty_employments():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload={"employments": []})


def test_success_rejects_non_object_employment_entry():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload={"employments": ["not-an-object"]})


# ── Missing / null / wrong-type / bool-as-int / subclass inputs ──────────────


@pytest.mark.parametrize("field", ["employerPayeReference", "employerName"])
def test_employment_rejects_missing_required(field):
    emp = _employment()
    del emp[field]
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(emp))


@pytest.mark.parametrize("field", ["employerPayeReference", "employerName"])
def test_employment_rejects_null_required(field):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: None})))


@pytest.mark.parametrize("field,bad", [
    ("employerPayeReference", 123),
    ("employerPayeReference", True),
    ("employerName", 123),
    ("employerName", True),
])
def test_employment_rejects_wrong_type_required(field, bad):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field,attribute", [
    ("employerPayeReference", "employer_paye_reference"),
    ("employerName", "employer_name"),
])
@pytest.mark.parametrize("blank", ["", "   ", "\u00a0\u2009"])
def test_employment_accepts_empty_and_whitespace_strings_as_schema_valid(field, attribute, blank):
    # The captured OpenAPI schema declares these as ``type: string`` with no
    # evidenced ``minLength``, so empty/separator-whitespace-only values are
    # schema-valid. Control whitespace (Unicode ``Cc``, e.g. tab/newline) is
    # instead rejected by the retained-string Unicode-safety predicate. These
    # values remain semantically unverified and are not promoted into evidence.
    history = _observe(payload=_success_payload(_employment(**{field: blank})))
    assert getattr(history.employments[0], attribute) == blank
    assert getattr(history.employments[0], attribute).strip() == ""


# ── Retained employer-string Unicode safety ──────────────────────────────────


@pytest.mark.parametrize("field", ["employerPayeReference", "employerName"])
@pytest.mark.parametrize("bad", ["\t", "\n", "\r", "\x00", "a\tb", "a\nb", "a\x1fc"])
def test_employment_rejects_control_whitespace_and_raw_controls(field, bad):
    # Tab/newline are Unicode ``Cc`` controls even though they are whitespace;
    # the retained-string predicate must reject them rather than silently retain
    # raw controls.
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field", ["employerPayeReference", "employerName"])
@pytest.mark.parametrize("bad", [
    "\u202e",           # U+202E RIGHT-TO-LEFT OVERRIDE (Cf format control)
    "\u200b",           # U+200B ZERO WIDTH SPACE (Cf format control)
    "safe\u202esuffix",
    "\ue000",           # U+E000 private-use (Co)
    "a\uf8ffb",         # U+F8FF private-use (Co)
    "\u0378",           # U+0378 unassigned (Cn) on the runtime Unicode database
    "\ud800",           # lone high surrogate (Cs)
    "a\udfff",          # lone low surrogate (Cs)
    "\ufffe",           # noncharacter (Cn)
])
def test_employment_rejects_unicode_unsafe_values(field, bad):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(**{field: bad})))


@pytest.mark.parametrize("field,attribute", [
    ("employerPayeReference", "employer_paye_reference"),
    ("employerName", "employer_name"),
])
@pytest.mark.parametrize("value", [
    "René Müller",
    "株式会社",
    "e\u0301tude",      # combining acute accent (Mn)
    "M\u0301\u00fcller",
    "🏢 Example Ltd",   # emoji (So) plus letters
    "¡Hola! 日本語 123",
    "naïve café — 100%",
])
def test_employment_accepts_ordinary_unicode(field, attribute, value):
    history = _observe(payload=_success_payload(_employment(**{field: value})))
    assert getattr(history.employments[0], attribute) == value


def test_unicode_rejection_does_not_echo_value():
    bad = "\u202eMüller"
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        _observe(payload=_success_payload(_employment(employerName=bad)))
    assert "\u202e" not in str(exc.value)
    assert bad not in str(exc.value)


@pytest.mark.parametrize("bad", [1, 0, "true", "false", [], {}, None])
def test_off_payroll_work_flag_rejects_null_wrong_types_and_bool_as_int(bad):
    # The captured schema does not declare ``offPayrollWorkFlag`` nullable, so
    # explicit null and every non-bool present value fail closed.
    with pytest.raises(HMRCIndividualEmploymentContractError):
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


def test_off_payroll_work_flag_rejects_int_subclass():
    # ``bool`` is a final type in Python and cannot be subclassed, so an exact
    # ``int`` subclass carrying a boolean-like value is the closest adversarial
    # subclass proxy. It must be rejected because only exact built-in bools are
    # accepted present values.
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(offPayrollWorkFlag=_IntSubclass(True))))


class _StrSubclass(str):
    pass


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
    pass


class _IntSubclass(int):
    pass


def test_employment_rejects_string_subclass():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(_employment(employerName=_StrSubclass("Example Ltd"))))


def test_payload_rejects_dict_subclass():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_DictSubclass(employments=[_employment()]))


def test_employments_rejects_list_subclass():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload={"employments": _ListSubclass([_employment()])})


def test_status_rejects_int_subclass():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=_IntSubclass(200))


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

    history = _observe(payload=payload)

    assert "some_future_field" in history.employments[0].unknown_fields
    assert "future_top" in history.unknown_fields
    assert "future_unknown" in history.unknown_fields
    assert "cyclic_unknown" in history.unknown_fields


# ── Open-schema member-name bounding and type checks ─────────────────────────


def test_member_names_reject_non_string_keys_at_every_level():
    top_level = _success_payload(_employment())
    top_level[1] = "x"
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=top_level)

    emp = _employment()
    emp[1] = "x"
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(emp))

    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=404, payload={"code": "NOT_FOUND", "message": "x", 1: "x"})


def test_member_names_reject_mixed_string_and_non_string_keys():
    top_level = _success_payload(_employment())
    top_level["safe"] = "x"
    top_level[2] = "y"
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=top_level)


def _assert_bad_member_name_rejected_at_every_level(name):
    top_level = _success_payload(_employment())
    top_level[name] = "x"
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=top_level)

    emp = _employment()
    emp[name] = "x"
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(emp))

    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=404, payload={"code": "NOT_FOUND", "message": "x", name: "x"})


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
    # Open-schema member names may be arbitrary ordinary Unicode; only category
    # ``C`` is rejected. These unknown keys must be classified without touching
    # their values.
    name = "employé🏢_日"
    payload = _success_payload(_employment())
    payload[name] = "x"
    history = _observe(payload=payload)
    assert name in history.unknown_fields


def test_member_names_reject_overlong_names():
    name = "x" * (RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH + 1)
    _assert_bad_member_name_rejected_at_every_level(name)


def test_member_names_reject_oversized_object_member_count():
    payload = _success_payload(_employment())
    for index in range(RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS + 1):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        _observe(payload=payload)
    assert "object member count" in str(exc.value)


def test_member_names_reject_excessive_unknown_keys():
    payload = _success_payload(_employment())
    for index in range(RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS + 1):
        payload[f"future_{index}"] = index
    with pytest.raises(HMRCIndividualEmploymentContractError) as exc:
        _observe(payload=payload)
    assert "unknown member count" in str(exc.value)


def test_hostile_unknown_values_are_never_inspected_at_any_level():
    hostile = _Hostile()
    payload = _success_payload(_employment(future=hostile), future_top=hostile)
    payload["future_unknown"] = hostile
    result = _observe(payload=payload)
    assert "future" in result.employments[0].unknown_fields
    assert "future_top" in result.unknown_fields
    assert "future_unknown" in result.unknown_fields

    error_result = _observe(
        status_code=404,
        payload={"code": "NOT_FOUND", "message": "x", "future_error": hostile},
    )
    assert "future_error" in error_result.unknown_fields


# ── Documented error statuses and malformed error bodies ─────────────────────


@pytest.mark.parametrize("status,code", [
    (400, "SA_UTR_INVALID"),
    (400, "TAX_YEAR_INVALID"),
    (401, "UNAUTHORIZED"),
    (404, "NOT_FOUND"),
])
def test_documented_error_statuses_are_classified(status, code):
    result = _observe(status_code=status, payload={"code": code, "message": "provider message"})
    assert isinstance(result, EmploymentErrorObservation)
    assert result.status_code == status
    assert result.error_code == code
    assert result.tax_year == "2026-27"


def test_error_message_is_validated_but_not_retained_or_echoed():
    result = _observe(
        status_code=400,
        payload={"code": "SA_UTR_INVALID", "message": "invalid UTR 1234567890"},
    )
    assert not hasattr(result, "message")
    assert "1234567890" not in repr(result)
    assert "1234567890" not in str(result.error_code)
    assert repr(result) == "EmploymentErrorObservation([REDACTED])"


@pytest.mark.parametrize("payload", [
    None,
    [],
    "not-a-dict",
    {},
    {"code": "NOT_FOUND"},
    {"message": "x"},
    {"code": 123, "message": "x"},
    {"code": "NOT_FOUND", "message": 123},
])
def test_error_rejects_malformed_body(payload):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=404, payload=payload)


@pytest.mark.parametrize("message", ["", "   ", "\t\n"])
def test_error_accepts_empty_and_whitespace_message_as_schema_valid(message):
    # ``message`` is OpenAPI ``type: string`` with no evidenced ``minLength``,
    # so empty/whitespace-only values are schema-valid. They are validated for
    # structure but never retained or echoed.
    result = _observe(status_code=404, payload={"code": "NOT_FOUND", "message": message})
    assert result.error_code == "NOT_FOUND"
    assert not hasattr(result, "message")


@pytest.mark.parametrize("status,code", [
    (400, "UNAUTHORIZED"),
    (400, "NOT_FOUND"),
    (401, "NOT_FOUND"),
    (401, "SA_UTR_INVALID"),
    (404, "SA_UTR_INVALID"),
    (404, "SOME_NEW_CODE"),
])
def test_error_rejects_undocumented_or_mismatched_code(status, code):
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(status_code=status, payload={"code": code, "message": "x"})


def test_error_accepts_additive_unknown_members():
    result = _observe(
        status_code=404,
        payload={"code": "NOT_FOUND", "message": "x", "future": {"deep": True}},
    )
    assert "future" in result.unknown_fields


# ── Reserved defensive bounds ────────────────────────────────────────────────


def test_defensive_bounds_are_present_and_labelled():
    assert RESERVED_DEFENSIVE_MAX_EMPLOYMENTS == 1000
    assert RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH == 512
    assert RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH == 64
    assert RESERVED_DEFENSIVE_MAX_ERROR_CODE_LENGTH == 64
    assert RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH == 1024
    assert RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH == 256
    assert RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS == 1000
    assert RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS == 64


def test_employments_exceeding_defensive_bound_are_rejected():
    emp = _employment()
    payload = {"employments": [emp] * (RESERVED_DEFENSIVE_MAX_EMPLOYMENTS + 1)}
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=payload)


def test_employer_name_exceeding_defensive_bound_is_rejected():
    emp = _employment(employerName="x" * (RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH + 1))
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(emp))


def test_employer_paye_reference_exceeding_defensive_bound_is_rejected():
    emp = _employment(
        employerPayeReference="1" * (RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH + 1)
    )
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(payload=_success_payload(emp))


def test_error_message_exceeding_defensive_bound_is_rejected():
    with pytest.raises(HMRCIndividualEmploymentContractError):
        _observe(
            status_code=404,
            payload={
                "code": "NOT_FOUND",
                "message": "x" * (RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH + 1),
            },
        )


# ── No conversion into tax-engine / cash / customer evidence ─────────────────


def test_observations_contain_no_tax_cash_or_customer_fields():
    history = _observe()
    forbidden = {
        "paid", "tax_paid", "tax_liability", "gross_pay", "net_pay", "canonical",
        "cash", "customer", "launch_ready", "evidence_id", "amount", "money",
    }
    assert forbidden.isdisjoint(history.__dataclass_fields__)
    assert forbidden.isdisjoint(history.employments[0].__dataclass_fields__)


def test_observations_are_not_paye_evidence():
    import reserved.providers.hmrc_individual_employment_contract as contract

    history = _observe()
    # The module never imports PayeEvidence; observations therefore cannot be it.
    for name in ("PayeEvidence", "AccountingEntry", "CanonicalAccountingTaxInput"):
        assert not hasattr(contract, name)
    assert not isinstance(history, tuple)


# ── Existing adapter decision and fail-closed readiness gates ────────────────


def test_hmrc_provider_spec_remains_disabled():
    from reserved.providers.readiness import PROVIDERS

    hmrc = next(spec for spec in PROVIDERS if spec.name == "hmrc")
    assert hmrc.implementation_enabled is False


def test_adapter_decision_document_preserves_disabled_decision_and_gates():
    text = (REPO / "docs" / "HMRC_ADAPTER_IMPLEMENTATION_DECISION.md").read_text(encoding="utf-8")
    assert "do not implement or enable an HMRC HTTP adapter" in text
    assert "implementation_enabled=False" in text
    assert "Individual Employment 1.2" in text
