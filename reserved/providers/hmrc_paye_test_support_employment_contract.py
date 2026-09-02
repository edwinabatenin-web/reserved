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

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping

# ── Exact documented contract constants ─────────────────────────────────────

HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_NAME = "Individual PAYE Test Support"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_VERSION = "2.1"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_API_BETA = True
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SANDBOX_ONLY = True
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPERATION_ID = "createEmploymentHistoryTestData"
HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_METHOD = "POST"
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


# ── Frozen, redacted, non-sendable request intent ────────────────────────────


class EmploymentTestSupportRequestIntent:
    """Frozen request intent for the documented POST operation.

    Deliberately not a ``ProviderRequest``. It exposes no method, URL, headers,
    body, path or raw UTR; only the validated non-sensitive tax year and the
    explicit scenario-presence/value facts are readable. The supplied UTR is
    validated for fail-closed construction but is then discarded: no raw UTR,
    UTR-bearing path or recoverable equivalent is retained on the object.

    ``scenario`` is ``None`` exactly when ``scenario_present`` is ``False``
    (scenario omitted). A present scenario is always one of the two documented
    literal strings ``HAPPY_PATH_1`` / ``HAPPY_PATH_2``.
    """

    __slots__ = ("__tax_year", "__scenario", "__scenario_present")

    def __init__(
        self,
        *,
        utr: str,
        tax_year: str,
        scenario: str = _SCENARIO_OMITTED,  # type: ignore[assignment]
    ) -> None:
        # Fail closed on a malformed UTR, then discard it. The intent keeps only
        # the validated non-sensitive tax year and the explicit scenario facts.
        _validate_utr(utr)
        validated_tax_year = _validate_tax_year(tax_year)
        scenario_present, scenario_value = _validate_scenario(scenario)
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

    @property
    def tax_year(self) -> str:
        return object.__getattribute__(
            self, "_EmploymentTestSupportRequestIntent__tax_year"
        )

    @property
    def scenario(self) -> str | None:
        return object.__getattribute__(
            self, "_EmploymentTestSupportRequestIntent__scenario"
        )

    @property
    def scenario_present(self) -> bool:
        return object.__getattribute__(
            self, "_EmploymentTestSupportRequestIntent__scenario_present"
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("EmploymentTestSupportRequestIntent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("EmploymentTestSupportRequestIntent is immutable")

    def __repr__(self) -> str:
        return "EmploymentTestSupportRequestIntent([REDACTED])"

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("EmploymentTestSupportRequestIntent cannot be copied or pickled")

    def __reduce__(self) -> object:
        raise TypeError("EmploymentTestSupportRequestIntent cannot be copied or pickled")


# ── Frozen, redacted observations ────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
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
        _require_employer_string(
            self.employer_name,
            "employer_name",
            RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
        )
        _require_employer_string(
            self.employer_paye_reference,
            "employer_paye_reference",
            RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
        )
        if self.off_payroll_work_flag is not None:
            _require_exact_bool(self.off_payroll_work_flag, "off_payroll_work_flag")

        _require_safe_member_name_set(
            self.absent_fields, "absent_fields", RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS
        )
        _require_unknown_field_set(
            self.unknown_fields, _EMPLOYMENT_DOCUMENTED_FIELDS, "unknown_fields"
        )

        expected_absent = (
            HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS
            if self.off_payroll_work_flag is None
            else frozenset()
        )
        if self.absent_fields != expected_absent:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: absent_fields is "
                "incoherent with off_payroll_work_flag"
            )

    def __repr__(self) -> str:
        return "EmploymentTestSupportRecordObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class EmploymentTestSupportResponseObservation:
    """Validated 201 observation for a documented create response.

    Completeness is always ``UNVERIFIED``: this is fixture evidence, not proof
    that a subsequent read is complete or current. Array order has no documented
    semantic meaning, so the retained tuple records input order only. The raw
    response payload is not retained.
    """

    tax_year: str
    status_code: int
    employments: tuple[EmploymentTestSupportRecordObservation, ...]
    completeness: str = COMPLETENESS_UNVERIFIED
    absent_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_tax_year(self.tax_year)
        _require_exact_int(self.status_code, "status_code")
        if self.status_code != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: only HTTP 201 is documented"
            )
        _require_exact_type(self.employments, tuple, "employments")
        if len(self.employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: employments exceeds the "
                "Reserved defensive bound"
            )
        for record in self.employments:
            if type(record) is not EmploymentTestSupportRecordObservation:
                raise HMRCPayeTestSupportEmploymentContractError(
                    "HMRC PAYE Test Support Employment contract: employment "
                    "record has an invalid type"
                )
        _require_exact_type(self.completeness, str, "completeness")
        if self.completeness != COMPLETENESS_UNVERIFIED:
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: completeness must be "
                "UNVERIFIED"
            )
        _require_safe_member_name_set(
            self.absent_fields, "absent_fields", RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS
        )
        _require_unknown_field_set(
            self.unknown_fields, _TOP_LEVEL_DOCUMENTED_FIELDS, "unknown_fields"
        )
        if self.absent_fields != frozenset():
            raise HMRCPayeTestSupportEmploymentContractError(
                "HMRC PAYE Test Support Employment contract: absent_fields must be "
                "empty because employments is required"
            )

    def __repr__(self) -> str:
        return "EmploymentTestSupportResponseObservation([REDACTED])"


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
    tax_year: str, status_code: int, payload: Any
) -> EmploymentTestSupportResponseObservation:
    if type(payload) is not dict:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: success payload must be a "
            "JSON object"
        )
    _validate_member_names(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    if "employments" not in payload:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: success payload is missing "
            "employments"
        )
    employments = payload["employments"]
    if type(employments) is not list:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: employments must be a "
            "JSON array"
        )
    # The prose describes "one or more" employments, but the captured schema
    # supplies no ``minItems``. An empty array is therefore shape-valid but
    # semantically unverified; it is accepted and recorded with UNVERIFIED
    # completeness rather than promoted into a non-empty guarantee.
    if len(employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: employments exceeds the "
            "Reserved defensive bound"
        )

    records = tuple(_parse_employment_test_support_record(entry) for entry in employments)
    _, unknown = _classify(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    return EmploymentTestSupportResponseObservation(
        tax_year=tax_year,
        status_code=status_code,
        employments=records,
        completeness=COMPLETENESS_UNVERIFIED,
        unknown_fields=unknown,
    )


def _parse_employment_test_support_record(
    entry: Any,
) -> EmploymentTestSupportRecordObservation:
    if type(entry) is not dict:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: employment must be a "
            "JSON object"
        )
    _validate_member_names(entry, _EMPLOYMENT_DOCUMENTED_FIELDS)

    if "employerName" not in entry:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: employment is missing "
            "employerName"
        )
    if "employerPayeReference" not in entry:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: employment is missing "
            "employerPayeReference"
        )

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
    exact response media type and the documented response schema are validated.
    """
    if type(request) is not EmploymentTestSupportRequestIntent:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: request must be an "
            "EmploymentTestSupportRequestIntent"
        )

    status = _require_exact_int(status_code, "status_code")
    # Fail closed before touching the body: no non-201 body is inspected or
    # classified, and no success/no-data/zero/fixture-complete conversion occurs.
    if status != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_SUCCESS_STATUS:
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: undocumented HTTP status"
        )

    if (
        type(content_type) is not str
        or content_type != HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_RESPONSE_CONTENT_TYPE
    ):
        raise HMRCPayeTestSupportEmploymentContractError(
            "HMRC PAYE Test Support Employment contract: response Content-Type must be "
            "application/json"
        )

    return _observe_employment_test_support_201(request.tax_year, status, payload)
