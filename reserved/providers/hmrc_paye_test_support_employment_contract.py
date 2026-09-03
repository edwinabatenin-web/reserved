"""Network-inert literal contract for the HMRC Individual PAYE Test Support 2.1
``createEmploymentHistoryTestData`` create (POST) operation.

This module is a deterministic request/response contract and validator for the
single documented sandbox fixture-creation operation::

    POST /individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}

It is deliberately **not** a transport adapter and owns no HTTP client,
credentials, token storage, authorisation header, persistence, routing,
configurable production origin or provider-enablement path. The request intent
it builds is not, is not derived from, and cannot be converted into the
sendable ``ProviderRequest`` from ``reserved.providers.http_boundary``. The UTR
is validated and then discarded: no raw UTR, UTR-bearing path or recoverable
equivalent is retained on the request intent.

The operation documents exactly one response, HTTP 201. Every non-201 result
fails closed as an unclassified outcome; no body is parsed, echoed, retained or
classified, and no HMRC error code is fabricated.

This module creates no tax-engine evidence (``PayeEvidence``), no canonical
accounting evidence, no annual tax inputs, no cash-obligation inputs, no
customer-presentation data and no employment identity linkage. The response is
fixture evidence only and is not proof that a subsequent read is complete or
current.

Authority observed 2026-09-02
(see docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md):

- ``POST /individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}``;
- operationId ``createEmploymentHistoryTestData``;
- version 2.1 beta, Sandbox-only;
- ``utr``: a 10-digit Self Assessment UTR path parameter;
- ``taxYear``: a path parameter matching ``^[0-9]{4}-[0-9]{2}$``;
- request Accept: ``application/vnd.hmrc.2.1+json``;
- request Content-Type: ``application/json``;
- application-restricted OAuth 2.0 Client Credentials Grant with an empty
  scope map (no named OAuth scope is documented);
- required request body whose object schema does not mark ``scenario`` required;
- ``scenario``, when present, is exactly ``HAPPY_PATH_1`` or ``HAPPY_PATH_2``;
- success HTTP 201 with ``application/json``;
- no endpoint-specific error responses or error codes are documented.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata
import weakref
from dataclasses import dataclass, field
from typing import Any, Mapping

# ── Exact documented contract constants ─────────────────────────────────────

HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_NAME = "Individual PAYE Test Support"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION = "2.1"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_BETA = True
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ONLY = True
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPERATION_ID = "createEmploymentHistoryTestData"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD = "POST"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_PATH_TEMPLATE = (
    "/individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}"
)
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_ACCEPT = "application/vnd.hmrc.2.1+json"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_CONTENT_TYPE = "application/json"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE = "application/json"
# Documentation metadata only: the operation binds ``application-restricted``
# OAuth 2.0 Client Credentials Grant with an empty scope map. This string is a
# recorded fact, never a credential, token or authorisation header.
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_AUTHENTICATION = (
    "application-restricted OAuth 2.0 Client Credentials Grant"
)
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES = frozenset()
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2"})
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS = 201

HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS = frozenset({
    "employerName",
    "employerPayeReference",
})
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS = frozenset({
    "offPayrollWorkFlag",
})

COMPLETENESS_UNVERIFIED = "UNVERIFIED"

# ── Reserved defensive policy bounds (NOT HMRC wire facts) ──────────────────
#
# HMRC's documented Test Support 2.1 employment schemas state no maximum for the
# ``employments`` array, the employer name/Paye-reference strings, the number of
# object members, or the length/number of unknown member names. The bounds below
# are local safety limits only. They are not provider facts and must not be
# presented as such; they exist to reject unbounded hostile input before any
# documented field is dereferenced or any member name is classified.
RESERVED_DEFENSIVE_MAX_EMPLOYMENTS = 1000
RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH = 512
RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH = 64
RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS = 1000
RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH = 256
RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS = 64

_UTR_RE = re.compile(r"[0-9]{10}")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
_OPAQUE_TOKEN_RE = re.compile(r"[0-9a-f]{64}")
_OBSERVATION_INTEGRITY_RE = re.compile(r"[0-9a-f]{64}")

# Process-local observer/reconstructor issuance records.  These are deliberately
# not a cryptographic authenticity mechanism: Python code with arbitrary module
# internals access is trusted.  They do, however, give the public validators an
# identity boundary that deterministic object state alone cannot provide.  A
# low-level clone is unsupported, while copy/deepcopy return the registered
# object and pickle reconstruction registers the newly validated object.
_OBSERVATION_ISSUANCE: dict[
    int, tuple[weakref.ReferenceType[object], str, tuple, str]
] = {}

_EMPLOYMENT_DOCUMENTED_FIELDS = (
    HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS
    | HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS
)
_TOP_LEVEL_DOCUMENTED_FIELDS = frozenset({"employments"})

# Module-private sentinel used to distinguish "scenario omitted" from an
# explicit (and therefore rejectable) ``scenario=None`` at the public boundary.
_SCENARIO_OMITTED = object()


class HMRCPayeTestSupportEmploymentContractError(ValueError):
    """Controlled validation failure whose message never includes source values."""


def _fail(rule: str) -> HMRCPayeTestSupportEmploymentContractError:
    """Return a constant, redacted, fail-closed contract error."""
    return HMRCPayeTestSupportEmploymentContractError(
        f"HMRC PAYE Test Support Employment contract: {rule}"
    )


# ── Frozen, redacted, non-sendable request intent ────────────────────────────


class EmploymentTestSupportRequestIntent:
    """Frozen, canonical UTR-free intent for the documented POST operation.

    Deliberately not a ``ProviderRequest``. It exposes no method, URL, headers,
    body, path or raw UTR; only the validated non-sensitive tax year and the
    explicit scenario-presence/value facts are readable. The supplied UTR is
    validated for fail-closed construction but is then discarded: no raw UTR,
    UTR-bearing path or recoverable equivalent is retained on the object.

    The fixed request descriptors (method, sandbox origin, path template,
    request/response media types and API version) are retained as private slots
    derived from documented constants so the object carries an exact canonical
    UTR-free request identity without exposing a sendable surface. Each
    constructed intent additionally receives a fresh high-entropy opaque
    correlation token (never a function of the UTR) so two separately built
    intents with identical semantics remain distinguishable per request.

    ``scenario`` is ``None`` exactly when ``scenario_present`` is ``False``
    (scenario omitted). A present scenario is always one of the two documented
    literal strings ``HAPPY_PATH_1`` / ``HAPPY_PATH_2``.
    """

    __slots__ = (
        "__correlation_id",
        "__tax_year",
        "__scenario",
        "__scenario_present",
        "__method",
        "__sandbox_origin",
        "__path_template",
        "__accept",
        "__content_type",
        "__response_content_type",
        "__api_version",
    )

    def __init__(
        self,
        *,
        utr: str,
        tax_year: str,
        scenario: str = _SCENARIO_OMITTED,  # type: ignore[assignment]
    ) -> None:
        # Fail closed on a malformed UTR, then discard it. The intent keeps only
        # the opaque correlation token, the validated tax year, the scenario
        # facts and the constant-derived request descriptors.
        _validate_utr(utr)
        validated_tax_year = _validate_tax_year(tax_year)
        scenario_present, scenario_value = _validate_scenario(scenario)
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__correlation_id",
            secrets.token_hex(32),
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__tax_year",
            validated_tax_year,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__scenario",
            scenario_value,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__scenario_present",
            scenario_present,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__method",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__sandbox_origin",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ORIGIN,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__path_template",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_PATH_TEMPLATE,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__accept",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_ACCEPT,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__content_type",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_CONTENT_TYPE,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__response_content_type",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE,
        )
        object.__setattr__(
            self,
            "_EmploymentTestSupportRequestIntent__api_version",
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION,
        )

    @property
    def tax_year(self) -> str:
        return _request_binding_for(self)[1]

    @property
    def scenario(self) -> str | None:
        return _request_binding_for(self)[2]

    @property
    def scenario_present(self) -> bool:
        return _request_binding_for(self)[3]

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("EmploymentTestSupportRequestIntent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("EmploymentTestSupportRequestIntent is immutable")

    def __repr__(self) -> str:
        _require_request_intent(self)
        return "EmploymentTestSupportRequestIntent([REDACTED])"

    def __eq__(self, other: object) -> bool:
        binding = _request_binding_for(self)
        if type(other) is not EmploymentTestSupportRequestIntent:
            return NotImplemented
        return binding == _request_binding_for(other)

    def __hash__(self) -> int:
        return hash(_request_binding_for(self))

    def __copy__(self) -> "EmploymentTestSupportRequestIntent":
        # Deeply immutable: sharing the instance is a coherent copy, but only
        # after revalidating every retained field so forged state is rejected.
        _require_request_intent(self)
        return self

    def __deepcopy__(self, memo: dict) -> "EmploymentTestSupportRequestIntent":
        _require_request_intent(self)
        return self

    def __reduce__(self) -> object:
        # Reconstruct only through the validated, UTR-free canonical binding so
        # a forged pickle cannot inject an unvalidated descriptor or a raw UTR.
        return (_restore_request_intent, (_request_binding_for(self),))


# ── Canonical request identity helpers ───────────────────────────────────────

_REQUEST_INTENT_FIXED_FIELDS = (
    ("method", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD),
    ("sandbox_origin", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ORIGIN),
    ("path_template", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_PATH_TEMPLATE),
    ("accept", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_ACCEPT),
    ("content_type", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_CONTENT_TYPE),
    ("response_content_type", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE),
    ("api_version", HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION),
)
_REQUEST_INTENT_STATE_ORDER = (
    "correlation_id",
    "tax_year",
    "scenario",
    "scenario_present",
) + tuple(name for name, _expected in _REQUEST_INTENT_FIXED_FIELDS)
_REQUEST_INTENT_STATE_NAMES = frozenset(_REQUEST_INTENT_STATE_ORDER)


def _request_intent_field(request: EmploymentTestSupportRequestIntent, name: str) -> object:
    return object.__getattribute__(
        request, f"_EmploymentTestSupportRequestIntent__{name}"
    )


def _read_request_field(request: EmploymentTestSupportRequestIntent, name: str) -> object:
    try:
        return _request_intent_field(request, name)
    except AttributeError:
        raise _fail(f"request {name} must be present")


def _validate_bound_scenario(value: object) -> str | None:
    """Validate a retained scenario value: ``None`` or a documented literal."""
    if value is None:
        return None
    _present, scenario = _validate_scenario(value)
    return scenario


def _canonical_request_binding(
    correlation_id: str, tax_year: str, scenario: str | None
) -> tuple:
    return (
        correlation_id,
        tax_year,
        scenario,
        scenario is not None,
    ) + tuple(expected for _name, expected in _REQUEST_INTENT_FIXED_FIELDS)


def _require_request_intent(request: object) -> EmploymentTestSupportRequestIntent:
    """Revalidate the full exact request intent rather than trusting history.

    Reads only the request's own built-in slots and checks their exact values
    against the documented constants and the validated tax-year/scenario facts.
    No hostile comparison, hashing, representation, string, truthiness, mapping
    or iteration hook is invoked: values are type-checked before use and any
    mismatch fails closed without echoing hostile data.
    """
    if type(request) is not EmploymentTestSupportRequestIntent:
        raise _fail("request must be an exact EmploymentTestSupportRequestIntent")

    correlation_id = _read_request_field(request, "correlation_id")
    if (
        type(correlation_id) is not str
        or _OPAQUE_TOKEN_RE.fullmatch(correlation_id) is None
    ):
        raise _fail("request correlation identity is malformed")

    tax_year = _read_request_field(request, "tax_year")
    scenario = _read_request_field(request, "scenario")
    scenario_present = _read_request_field(request, "scenario_present")
    _validate_tax_year(tax_year)
    _validate_bound_scenario(scenario)
    if type(scenario_present) is not bool:
        raise _fail("request scenario_present must be an exact built-in boolean")
    if scenario_present != (scenario is not None):
        raise _fail("request scenario presence is incoherent")

    for name, expected in _REQUEST_INTENT_FIXED_FIELDS:
        value = _read_request_field(request, name)
        if type(value) is not str or value != expected:
            raise _fail(f"request {name} is not the exact documented value")
    return request


def _request_binding_for(request: EmploymentTestSupportRequestIntent) -> tuple:
    """Snapshot the complete validated UTR-free canonical request state."""
    validated = _require_request_intent(request)
    return tuple(
        _request_intent_field(validated, name) for name in _REQUEST_INTENT_STATE_ORDER
    )


def _require_request_binding(binding: object) -> tuple:
    """Validate a retained binding without normalising or rebuilding it."""
    if type(binding) is not tuple:
        raise _fail("observation request binding must be an exact built-in tuple")
    if len(binding) != len(_REQUEST_INTENT_STATE_ORDER):
        raise _fail("observation request binding is not the exact expected shape")

    correlation_id = binding[0]
    if (
        type(correlation_id) is not str
        or _OPAQUE_TOKEN_RE.fullmatch(correlation_id) is None
    ):
        raise _fail("observation request binding correlation identity is malformed")

    tax_year = _validate_tax_year(binding[1])
    scenario = _validate_bound_scenario(binding[2])
    scenario_present = binding[3]
    if type(scenario_present) is not bool:
        raise _fail(
            "observation request binding scenario_present must be an exact built-in boolean"
        )
    if scenario_present != (scenario is not None):
        raise _fail("observation request binding scenario presence is incoherent")

    for index, (_name, expected) in enumerate(_REQUEST_INTENT_FIXED_FIELDS, start=4):
        value = binding[index]
        if type(value) is not str or value != expected:
            raise _fail("observation request binding has a non-canonical fixed descriptor")

    expected = _canonical_request_binding(correlation_id, tax_year, scenario)
    if binding != expected:
        raise _fail("observation request binding is not canonical")
    return binding


def _restore_request_intent(binding: tuple) -> EmploymentTestSupportRequestIntent:
    """Restore only validated UTR-free retained request state."""
    canonical = _require_request_binding(binding)
    request = object.__new__(EmploymentTestSupportRequestIntent)
    for name, value in zip(_REQUEST_INTENT_STATE_ORDER, canonical):
        object.__setattr__(
            request, f"_EmploymentTestSupportRequestIntent__{name}", value
        )
    return _require_request_intent(request)


# ── Exact instance-state validator ───────────────────────────────────────────


def _require_exact_instance_state(
    value: object,
    expected_type: type,
    expected_names: frozenset[str],
    context: str,
) -> dict:
    """Return an exact instance dictionary only when its shape is complete.

    ``object.__setattr__`` can inject undeclared instance attributes into a
    frozen, non-slotted dataclass. Before any equality, hashing, copy, deepcopy
    or reduction the instance ``__dict__`` is therefore compared against the
    exact declared key set, so missing/extra state fails closed instead of being
    preserved or silently ignored.
    """
    if type(value) is not expected_type:
        raise _fail(f"{context} must be the exact expected observation type")
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict:
        raise _fail(f"{context} internal state must be an exact built-in dict")
    if len(state) != len(expected_names):
        raise _fail(f"{context} internal state is not the exact expected shape")
    keys: set[str] = set()
    for key in state:
        if type(key) is not str:
            raise _fail(f"{context} internal state contains a non-string key")
        keys.add(key)
    if keys != expected_names:
        raise _fail(f"{context} internal state keys are not exact")
    return state


# ── Frozen, redacted observations ────────────────────────────────────────────

_RECORD_OBSERVATION_STATE_NAMES = frozenset({
    "employer_name",
    "employer_paye_reference",
    "off_payroll_work_flag",
    "absent_fields",
    "unknown_fields",
})


def _validate_record_fields(
    employer_name: str,
    employer_paye_reference: str,
    off_payroll_work_flag: bool | None,
    absent_fields: frozenset[str],
    unknown_fields: frozenset[str],
) -> None:
    _require_employer_string(
        employer_name,
        "employer_name",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    )
    _require_employer_string(
        employer_paye_reference,
        "employer_paye_reference",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    )
    if off_payroll_work_flag is not None:
        _require_exact_bool(off_payroll_work_flag, "off_payroll_work_flag")
    _require_safe_member_name_set(
        absent_fields, "absent_fields", RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS
    )
    _require_unknown_field_set(
        unknown_fields, _EMPLOYMENT_DOCUMENTED_FIELDS, "unknown_fields"
    )
    expected_absent = (
        HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS
        if off_payroll_work_flag is None
        else frozenset()
    )
    if absent_fields != expected_absent:
        raise _fail("absent_fields is incoherent with off_payroll_work_flag")


@dataclass(frozen=True, repr=False, eq=False)
class EmploymentTestSupportRecordObservation:
    """Validated facts from one element of the ``employments`` array.

    ``off_payroll_work_flag`` is ``None`` when, and only when, the optional
    field is absent; ``absent_fields`` records that omission. No field in the
    captured OpenAPI schema is declared nullable, so explicit ``null`` is
    rejected rather than retained. ``off_payroll_work_flag`` present values are
    therefore always exact built-in ``True``/``False``. Unknown member names are
    recorded for review without their values ever being inspected or retained.
    """

    employer_name: str
    employer_paye_reference: str
    off_payroll_work_flag: bool | None = None
    absent_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_record_fields(
            self.employer_name,
            self.employer_paye_reference,
            self.off_payroll_work_flag,
            self.absent_fields,
            self.unknown_fields,
        )

    def __repr__(self) -> str:
        _require_record_observation(self)
        return "EmploymentTestSupportRecordObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        _require_record_observation(self)
        if type(other) is not EmploymentTestSupportRecordObservation:
            return NotImplemented
        _require_record_observation(other)
        return (
            self.employer_name,
            self.employer_paye_reference,
            self.off_payroll_work_flag,
            self.absent_fields,
            self.unknown_fields,
        ) == (
            other.employer_name,
            other.employer_paye_reference,
            other.off_payroll_work_flag,
            other.absent_fields,
            other.unknown_fields,
        )

    def __hash__(self) -> int:
        _require_record_observation(self)
        return hash((
            self.employer_name,
            self.employer_paye_reference,
            self.off_payroll_work_flag,
            self.absent_fields,
            self.unknown_fields,
        ))

    def __copy__(self) -> "EmploymentTestSupportRecordObservation":
        _require_record_observation(self)
        return self

    def __deepcopy__(self, memo: dict) -> "EmploymentTestSupportRecordObservation":
        _require_record_observation(self)
        return self

    def __reduce__(self) -> object:
        _require_record_observation(self)
        return (EmploymentTestSupportRecordObservation, (
            self.employer_name,
            self.employer_paye_reference,
            self.off_payroll_work_flag,
            self.absent_fields,
            self.unknown_fields,
        ))


def _require_record_observation(value: object) -> EmploymentTestSupportRecordObservation:
    state = _require_exact_instance_state(
        value,
        EmploymentTestSupportRecordObservation,
        _RECORD_OBSERVATION_STATE_NAMES,
        "employment record observation",
    )
    _validate_record_fields(
        state["employer_name"],
        state["employer_paye_reference"],
        state["off_payroll_work_flag"],
        state["absent_fields"],
        state["unknown_fields"],
    )
    return value


def _record_integrity_value(record: EmploymentTestSupportRecordObservation) -> list[object]:
    state = object.__getattribute__(record, "__dict__")
    return [
        state["employer_name"],
        state["employer_paye_reference"],
        state["off_payroll_work_flag"],
        sorted(state["absent_fields"]),
        sorted(state["unknown_fields"]),
    ]


_RESPONSE_OBSERVATION_STATE_NAMES = frozenset({
    "status_code",
    "employments",
    "completeness",
    "absent_fields",
    "unknown_fields",
    "request",
    "_request_binding",
    "_source_binding",
    "tax_year",
    "scenario",
    "scenario_present",
    "_observation_integrity",
})


def _validate_response_facts(value: "EmploymentTestSupportResponseObservation") -> None:
    _require_exact_int(value.status_code, "status_code")
    if value.status_code != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS:
        raise _fail("only HTTP 201 is documented")
    _require_exact_type(value.employments, tuple, "employments")
    if len(value.employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the Reserved defensive bound")
    for record in value.employments:
        _require_record_observation(record)
    _require_exact_type(value.completeness, str, "completeness")
    if value.completeness != COMPLETENESS_UNVERIFIED:
        raise _fail("completeness must be UNVERIFIED")
    _require_safe_member_name_set(
        value.absent_fields, "absent_fields", RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS
    )
    _require_unknown_field_set(
        value.unknown_fields, _TOP_LEVEL_DOCUMENTED_FIELDS, "unknown_fields"
    )
    if value.absent_fields != frozenset():
        raise _fail("absent_fields must be empty because employments is required")


@dataclass(frozen=True, repr=False, init=False, eq=False)
class EmploymentTestSupportResponseObservation:
    """Validated 201 observation for a documented create response.

    Completeness is always ``UNVERIFIED``: this is fixture evidence, not proof
    that a subsequent read is complete or current. Array order has no documented
    semantic meaning, so the retained tuple records input order only. The raw
    response payload is not retained.

    The observer's private factory retains the exact validated, UTR-free request
    context, two retained references (``_request_binding`` and ``_source_binding``)
    to the same immutable canonical binding tuple, and a canonical SHA-256
    observation-integrity digest covering the complete request binding and every
    retained semantic value.
    ``tax_year``, ``scenario`` and ``scenario_present`` are derived from that
    trusted context, never duplicated from caller input. Public construction and
    ``dataclasses.replace`` are intentionally unavailable.
    """

    status_code: int = field(init=False)
    employments: tuple[EmploymentTestSupportRecordObservation, ...] = field(init=False)
    completeness: str = field(init=False)
    absent_fields: frozenset[str] = field(init=False)
    unknown_fields: frozenset[str] = field(init=False)
    request: EmploymentTestSupportRequestIntent = field(init=False, repr=False)
    _request_binding: tuple = field(init=False, repr=False)
    _source_binding: tuple = field(init=False, repr=False)
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)
    _observation_integrity: str = field(init=False, repr=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "EmploymentTestSupportResponseObservation is observer-constructed only"
        )

    def __repr__(self) -> str:
        _response_state(self)
        return "EmploymentTestSupportResponseObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        left = _response_state(self)
        if type(other) is not EmploymentTestSupportResponseObservation:
            return NotImplemented
        return left == _response_state(other)

    def __hash__(self) -> int:
        return hash(_response_state(self))

    def __copy__(self) -> "EmploymentTestSupportResponseObservation":
        _response_state(self)
        return self

    def __deepcopy__(self, memo: dict) -> "EmploymentTestSupportResponseObservation":
        _response_state(self)
        return self

    def __reduce__(self) -> object:
        state = _response_state(self)
        return (_restore_response_observation, (
            state[0],
            state[1],
            state[2],
            state[3],
            state[4],
            state[5],
        ))


def _observation_digest(canonical: object) -> str:
    encoded = json.dumps(
        canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_observation_integrity(value: object, expected: str) -> str:
    if type(value) is not str or _OBSERVATION_INTEGRITY_RE.fullmatch(value) is None:
        raise _fail("observation integrity is malformed")
    if not secrets.compare_digest(value, expected):
        raise _fail("observation integrity is incoherent")
    return value


def _register_observation(
    value: object, kind: str, binding: tuple, integrity: str
) -> None:
    identity = id(value)

    def discard(reference: weakref.ReferenceType[object]) -> None:
        current = _OBSERVATION_ISSUANCE.get(identity)
        if current is not None and current[0] is reference:
            _OBSERVATION_ISSUANCE.pop(identity, None)

    reference = weakref.ref(value, discard)
    _OBSERVATION_ISSUANCE[identity] = (reference, kind, binding, integrity)


def _validate_observation_issuance(
    value: object, kind: str, binding: tuple, integrity: str
) -> None:
    issued = _OBSERVATION_ISSUANCE.get(id(value))
    if (
        issued is None
        or issued[0]() is not value
        or issued[1] != kind
        or issued[2] != binding
        or not secrets.compare_digest(issued[3], integrity)
    ):
        raise _fail("observation provenance is unsupported")


def _bound_observation_state(state: dict) -> tuple:
    request_binding = _request_binding_for(state["request"])
    retained = _require_request_binding(state["_request_binding"])
    source = _require_request_binding(state["_source_binding"])
    if request_binding != retained or retained != source:
        raise _fail("observation request binding is not coherent")
    if type(state["tax_year"]) is not str or state["tax_year"] != retained[1]:
        raise _fail("observation tax year is not derived from its request context")
    if _validate_bound_scenario(state["scenario"]) != retained[2]:
        raise _fail("observation scenario is not derived from its request context")
    if (
        type(state["scenario_present"]) is not bool
        or state["scenario_present"] != retained[3]
    ):
        raise _fail(
            "observation scenario presence is not derived from its request context"
        )
    return retained


def _response_integrity_canonical(
    binding: tuple,
    tax_year: str,
    status_code: int,
    employments: tuple[EmploymentTestSupportRecordObservation, ...],
    completeness: str,
    absent_fields: frozenset[str],
    unknown_fields: frozenset[str],
) -> list[object]:
    return [
        "success",
        list(binding),
        tax_year,
        status_code,
        [_record_integrity_value(record) for record in employments],
        completeness,
        sorted(absent_fields),
        sorted(unknown_fields),
    ]


def _response_state(value: object) -> tuple:
    state = _require_exact_instance_state(
        value,
        EmploymentTestSupportResponseObservation,
        _RESPONSE_OBSERVATION_STATE_NAMES,
        "response observation",
    )
    binding = _bound_observation_state(state)
    _validate_response_facts(value)
    canonical = _response_integrity_canonical(
        binding,
        state["tax_year"],
        state["status_code"],
        state["employments"],
        state["completeness"],
        state["absent_fields"],
        state["unknown_fields"],
    )
    integrity = _validate_observation_integrity(
        state["_observation_integrity"], _observation_digest(canonical)
    )
    _validate_observation_issuance(value, "success", binding, integrity)
    return (
        binding,
        state["status_code"],
        state["employments"],
        state["completeness"],
        state["absent_fields"],
        state["unknown_fields"],
        state["_request_binding"],
        state["_source_binding"],
        state["tax_year"],
        state["scenario"],
        state["scenario_present"],
        integrity,
    )


def _preflight_response_arguments(
    status_code: object,
    employments: object,
    completeness: object,
    absent_fields: object,
    unknown_fields: object,
) -> None:
    """Structurally validate every response argument before any downstream use.

    Reconstruction (pickle ``__reduce__``) re-enters here with caller-supplied
    values, so each argument is exact-type-checked before any iteration, sorting,
    hashing, equality, JSON serialisation or record extraction. Every failure
    raises only the controlled contract error and never invokes an
    attacker-supplied comparison, hashing, representation, truthiness, mapping
    or iteration hook.
    """
    status = _require_exact_int(status_code, "status_code")
    if status != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS:
        raise _fail("only HTTP 201 is documented")
    _require_exact_type(employments, tuple, "employments")
    if len(employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the Reserved defensive bound")
    for record in employments:
        _require_record_observation(record)
    _require_exact_type(completeness, str, "completeness")
    if completeness != COMPLETENESS_UNVERIFIED:
        raise _fail("completeness must be UNVERIFIED")
    _require_safe_member_name_set(
        absent_fields, "absent_fields", RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS
    )
    _require_unknown_field_set(
        unknown_fields, _TOP_LEVEL_DOCUMENTED_FIELDS, "unknown_fields"
    )
    if absent_fields != frozenset():
        raise _fail("absent_fields must be empty because employments is required")


def _build_response_observation(
    request: EmploymentTestSupportRequestIntent,
    status_code: int,
    employments: tuple[EmploymentTestSupportRecordObservation, ...],
    completeness: str,
    absent_fields: frozenset[str],
    unknown_fields: frozenset[str],
) -> EmploymentTestSupportResponseObservation:
    """Construct a response observation only for the validated parser boundary."""
    validated_request = _require_request_intent(request)
    binding = _request_binding_for(validated_request)
    _preflight_response_arguments(
        status_code, employments, completeness, absent_fields, unknown_fields
    )
    observation = object.__new__(EmploymentTestSupportResponseObservation)
    object.__setattr__(observation, "status_code", status_code)
    object.__setattr__(observation, "employments", employments)
    object.__setattr__(observation, "completeness", completeness)
    object.__setattr__(observation, "absent_fields", absent_fields)
    object.__setattr__(observation, "unknown_fields", unknown_fields)
    object.__setattr__(observation, "request", validated_request)
    object.__setattr__(observation, "_request_binding", binding)
    object.__setattr__(observation, "_source_binding", binding)
    object.__setattr__(observation, "tax_year", binding[1])
    object.__setattr__(observation, "scenario", binding[2])
    object.__setattr__(observation, "scenario_present", binding[3])
    canonical = _response_integrity_canonical(
        binding,
        binding[1],
        status_code,
        employments,
        completeness,
        absent_fields,
        unknown_fields,
    )
    object.__setattr__(
        observation, "_observation_integrity", _observation_digest(canonical)
    )
    _register_observation(
        observation,
        "success",
        binding,
        object.__getattribute__(observation, "_observation_integrity"),
    )
    _response_state(observation)
    return observation


def _restore_response_observation(
    binding: tuple,
    status_code: int,
    employments: tuple[EmploymentTestSupportRecordObservation, ...],
    completeness: str,
    absent_fields: frozenset[str],
    unknown_fields: frozenset[str],
) -> EmploymentTestSupportResponseObservation:
    """Restore a validated observation without any raw request identifier."""
    return _build_response_observation(
        _restore_request_intent(binding),
        status_code,
        employments,
        completeness,
        absent_fields,
        unknown_fields,
    )


def validate_employment_test_support_response_observation(
    observation: object,
) -> EmploymentTestSupportResponseObservation:
    """Revalidate exact state and its complete producing-request binding."""
    _response_state(observation)
    return observation


# ── Exact built-in type and format validators ───────────────────────────────


def _validate_utr(value: Any) -> str:
    if type(value) is not str:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: utr must be a string"
        )
    if _UTR_RE.fullmatch(value) is None:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: utr must be a 10-digit string"
        )
    return value


def _validate_tax_year(value: Any) -> str:
    if type(value) is not str:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: tax_year must be a string"
        )
    if _TAX_YEAR_RE.fullmatch(value) is None:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: tax_year must match YYYY-YY"
        )
    return value


def _validate_scenario(value: Any) -> tuple[bool, str | None]:
    if value is _SCENARIO_OMITTED:
        return False, None
    if type(value) is not str:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: scenario must be a string"
        )
    if value not in HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SCENARIOS:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: undocumented scenario"
        )
    return True, value


def _require_exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} must be an integer"
        )
    return value


def _require_exact_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} must be a boolean"
        )
    return value


def _require_exact_type(value: Any, expected: type, field: str) -> Any:
    if type(value) is not expected:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} has an invalid type"
        )
    return value


def _require_documented_string(value: Any, field: str, max_length: int) -> str:
    """Validate an exact built-in string within the Reserved defensive bound.

    ``max_length`` is a Reserved defensive policy bound, not an HMRC wire fact.
    The captured OpenAPI schemas declare these fields as ``type: string``
    without an evidenced ``minLength``, so empty and whitespace-only strings are
    accepted as schema-valid. They remain semantically unverified; this module
    does not promote them into downstream evidence.
    """
    if type(value) is not str:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} must be a string"
        )
    if len(value) > max_length:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} exceeds the "
            "Reserved defensive bound"
        )
    return value


def _has_unsafe_unicode_character(text: str) -> bool:
    """Return ``True`` if any character is in Unicode general category ``C``.

    Category ``C`` is the conservative unsafe set: control (``Cc``), format
    (``Cf``), surrogate (``Cs``), private-use (``Co``) and unassigned (``Cn``).
    This rejects control/surrogate/noncharacter code points *and* format
    controls (U+202E, U+200B), private-use code points and unassigned code
    points. Ordinary letters, combining marks, numbers, punctuation, symbols
    and separators (including spaces) are preserved. The caller guarantees
    ``text`` is an exact built-in ``str``, so iteration cannot dispatch to a
    subclass override.
    """
    for character in text:
        if unicodedata.category(character).startswith("C"):
            return True
    return False


def _require_employer_string(value: Any, field: str, max_length: int) -> str:
    """Validate a retained employer string, including Unicode safety.

    Retained employer strings use the same Unicode category ``C`` predicate as
    member names: control, format, surrogate, private-use and unassigned
    characters are rejected. Empty and separator whitespace-only strings remain
    schema-valid (the captured schema has no evidenced ``minLength``) and are
    not rejected here.
    """
    result = _require_documented_string(value, field, max_length)
    if _has_unsafe_unicode_character(result):
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} contains unsafe "
            "Unicode characters"
        )
    return result


def _require_safe_member_name_set(
    value: Any, field: str, max_count: int
) -> frozenset[str]:
    """Validate a retained member-name set under the shared safe-name policy.

    A retained field-name set (``absent_fields`` / ``unknown_fields``) must be an
    exact built-in ``frozenset`` whose size obeys the supplied Reserved bound and
    whose elements are exact built-in ``str`` values within the Reserved
    member-name length bound and free of Unicode general-category ``C``
    characters. This is the single policy used by both observation classes so
    direct construction, ``replace``, copy/deepcopy and pickle cannot diverge.
    """
    if type(value) is not frozenset:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} has an invalid type"
        )
    if len(value) > max_count:
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} exceeds the "
            "Reserved defensive bound"
        )
    for name in value:
        if type(name) is not str:
            raise HMRCPayeTestSupportEmploymentContractError(
                f"HMRC PAYE Test Support Employment contract: {field} must contain "
                "only strings"
            )
        if len(name) > RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH:
            raise HMRCPayeTestSupportEmploymentContractError(
                f"HMRC PAYE Test Support Employment contract: {field} member name "
                "exceeds the Reserved defensive bound"
            )
        if _has_unsafe_unicode_character(name):
            raise HMRCPayeTestSupportEmploymentContractError(
                f"HMRC PAYE Test Support Employment contract: {field} member name "
                "contains control or unsafe characters"
            )
    return value


def _require_unknown_field_set(
    value: Any, documented: frozenset[str], field: str
) -> frozenset[str]:
    """Validate an unknown-field-name set disjoint from the documented names."""
    result = _require_safe_member_name_set(
        value, field, RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS
    )
    if not result.isdisjoint(documented):
        raise HMRCPayeTestSupportEmploymentContractError(
            f"HMRC PAYE Test Support Employment contract: {field} contains a "
            "documented field name"
        )
    return result


def _validate_member_names(mapping: Mapping[str, Any], documented: frozenset[str]) -> None:
    """Bound and type-check open-schema member names before classification.

    Runs before known/unknown classification or any operation that assumes safe
    strings. Only member *names* are inspected; member *values* are never
    dereferenced, copied, stringified, compared, hashed, logged or retained.
    """
    if len(mapping) > RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: object member count exceeds "
            "the Reserved defensive bound"
        )

    unknown_count = 0
    for name in mapping:
        if type(name) is not str:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: object member names must "
                "be strings"
            )
        if len(name) > RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: object member name "
                "exceeds the Reserved defensive bound"
            )
        if _has_unsafe_unicode_character(name):
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: object member name "
                "contains control or unsafe characters"
            )
        if name not in documented:
            unknown_count += 1

    if unknown_count > RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: unknown member count exceeds "
            "the Reserved defensive bound"
        )


def _classify(
    mapping: Mapping[str, Any], documented: frozenset[str]
) -> tuple[frozenset[str], frozenset[str]]:
    """Classify absent and unknown member names after name validation.

    Only member *names* are inspected. No documented field is nullable, so
    explicit ``null`` is rejected by the value validators before this runs;
    there is no null-name category to record. Unknown member values are never
    dereferenced, copied, stringified, compared, hashed, logged or retained.
    """
    absent = frozenset(field for field in documented if field not in mapping)
    unknown = frozenset(field for field in mapping if field not in documented)
    return absent, unknown


# ── Public builders and validators ──────────────────────────────────────────


def build_employment_test_support_request(
    *,
    utr: str,
    tax_year: str,
    scenario: str = _SCENARIO_OMITTED,  # type: ignore[assignment]
) -> EmploymentTestSupportRequestIntent:
    """Build a frozen, redacted, non-sendable request intent.

    Validates a 10-digit SA UTR and the documented tax-year form, and validates
    an explicitly supplied scenario against the two documented literals. The
    ``scenario`` argument defaults to omission; omission is distinct from an
    explicit (rejected) ``None`` or any other value. Error text is constant and
    never echoes the supplied values. The returned intent exposes no UTR,
    UTR-bearing path, method, URL, headers, body or authorisation data.
    """
    return EmploymentTestSupportRequestIntent(
        utr=utr,
        tax_year=tax_year,
        scenario=scenario,
    )


def _observe_employment_test_support_201(
    request: EmploymentTestSupportRequestIntent,
    status_code: int,
    payload: Any,
) -> EmploymentTestSupportResponseObservation:
    if type(payload) is not dict:
        raise _fail("success payload must be a JSON object")
    _validate_member_names(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    if "employments" not in payload:
        raise _fail("success payload is missing employments")
    employments = payload["employments"]
    if type(employments) is not list:
        raise _fail("employments must be a JSON array")
    # The prose describes "one or more" employments, but the captured schema
    # supplies no ``minItems``. An empty array is therefore shape-valid but
    # semantically unverified; it is accepted and recorded with UNVERIFIED
    # completeness rather than promoted into a non-empty guarantee.
    if len(employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the Reserved defensive bound")

    records = tuple(_parse_employment_test_support_record(entry) for entry in employments)
    _, unknown = _classify(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    return _build_response_observation(
        request,
        status_code,
        records,
        COMPLETENESS_UNVERIFIED,
        frozenset(),
        unknown,
    )


def _parse_employment_test_support_record(
    entry: Any,
) -> EmploymentTestSupportRecordObservation:
    if type(entry) is not dict:
        raise _fail("employment must be a JSON object")
    _validate_member_names(entry, _EMPLOYMENT_DOCUMENTED_FIELDS)

    if "employerName" not in entry:
        raise _fail("employment is missing employerName")
    if "employerPayeReference" not in entry:
        raise _fail("employment is missing employerPayeReference")

    employer_name = _require_employer_string(
        entry["employerName"],
        "employerName",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    )
    employer_paye_reference = _require_employer_string(
        entry["employerPayeReference"],
        "employerPayeReference",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    )

    off_payroll_work_flag: bool | None = None
    if "offPayrollWorkFlag" in entry:
        # No field in the captured schema is nullable: an exact built-in bool is
        # the only accepted present value, so explicit null fails closed here.
        off_payroll_work_flag = _require_exact_bool(
            entry["offPayrollWorkFlag"], "offPayrollWorkFlag"
        )

    absent, unknown = _classify(entry, _EMPLOYMENT_DOCUMENTED_FIELDS)
    return EmploymentTestSupportRecordObservation(
        employer_name=employer_name,
        employer_paye_reference=employer_paye_reference,
        off_payroll_work_flag=off_payroll_work_flag,
        absent_fields=absent,
        unknown_fields=unknown,
    )


def observe_employment_test_support_response(
    request: EmploymentTestSupportRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: Any,
) -> EmploymentTestSupportResponseObservation:
    """Validate a response for the documented POST operation and fail closed.

    Only the exact documented HTTP 201 success is accepted. Every non-201 result
    fails closed as an unclassified outcome: the body is never parsed, echoed,
    retained or classified, and no HMRC error code is fabricated. For 201, the
    exact response media type and the documented response schema are validated,
    and the observation is bound to the producing UTR-free request identity.
    """
    validated_request = _require_request_intent(request)

    status = _require_exact_int(status_code, "status_code")
    # Fail closed before touching the body: no non-201 body is inspected or
    # classified, and no success/no-data/zero/fixture-complete conversion occurs.
    if status != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS:
        raise _fail("undocumented HTTP status")

    if (
        type(content_type) is not str
        or content_type != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE
    ):
        raise _fail("response Content-Type must be application/json")

    return _observe_employment_test_support_201(validated_request, status, payload)
