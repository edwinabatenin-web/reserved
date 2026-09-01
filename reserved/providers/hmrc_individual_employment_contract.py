"""Network-inert literal contract for the HMRC Individual Employment 1.2 read.

This module is a deterministic request/response contract and validator for the
single documented GET operation::

    GET /individual-employment/sa/{utr}/annual-summary/{taxYear}

It is deliberately **not** a transport adapter and owns no HTTP client,
credentials, token storage, authorisation header, persistence, routing,
configurable production origin or provider-enablement path. The request intent
it builds is not, is not derived from, and cannot be converted into the
sendable ``ProviderRequest`` from ``reserved.providers.http_boundary``. The UTR
is validated and then discarded: no raw UTR, UTR-bearing path or recoverable
equivalent is retained on the request intent.

This module creates no tax-engine evidence (``PayeEvidence``), no canonical
accounting evidence, no annual tax inputs, no cash-obligation inputs and no
customer-presentation data. The annual summary is an observation whose
completeness remains ``UNVERIFIED``; it is not proof of a complete current
position.

Authority observed 2026-09-01
(see docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md):

- ``GET /individual-employment/sa/{utr}/annual-summary/{taxYear}``;
- ``utr``: a 10-digit Self Assessment UTR path parameter;
- ``taxYear``: a path parameter matching ``^[0-9]{4}-[0-9]{2}$``;
- request Accept: ``application/vnd.hmrc.1.2+json``;
- user-restricted OAuth scope ``read:individual-employment``;
- success HTTP 200 with a required non-empty ``employments`` array, each entry
  requiring string ``employerPayeReference`` and string ``employerName`` with
  optional boolean ``offPayrollWorkFlag``;
- documented response bodies use ``application/json``;
- documented endpoint errors: 400 ``SA_UTR_INVALID`` / ``TAX_YEAR_INVALID``,
  401 ``UNAUTHORIZED`` and 404 ``NOT_FOUND``; every documented error body
  requires string ``code`` and string ``message``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

# ── Exact documented contract constants ─────────────────────────────────────

HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME = "Individual Employment"
HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION = "1.2"
HMRC_INDIVIDUAL_EMPLOYMENT_SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
HMRC_INDIVIDUAL_EMPLOYMENT_PATH_TEMPLATE = (
    "/individual-employment/sa/{utr}/annual-summary/{taxYear}"
)
HMRC_INDIVIDUAL_EMPLOYMENT_ACCEPT = "application/vnd.hmrc.1.2+json"
HMRC_INDIVIDUAL_EMPLOYMENT_OAUTH_SCOPE = "read:individual-employment"
HMRC_INDIVIDUAL_EMPLOYMENT_RESPONSE_CONTENT_TYPE = "application/json"

HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS = 200
HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_STATUSES = frozenset({400, 401, 404})
HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES = MappingProxyType({
    400: frozenset({"SA_UTR_INVALID", "TAX_YEAR_INVALID"}),
    401: frozenset({"UNAUTHORIZED"}),
    404: frozenset({"NOT_FOUND"}),
})

HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS = frozenset({
    "employerPayeReference",
    "employerName",
})
HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS = frozenset({
    "offPayrollWorkFlag",
})

COMPLETENESS_UNVERIFIED = "UNVERIFIED"

# ── Reserved defensive policy bounds (NOT HMRC wire facts) ──────────────────
#
# HMRC's documented Individual Employment 1.2 schemas state no maximum for the
# ``employments`` array, the employer identifier/name/message strings, the
# number of object members, or the length/number of unknown member names. The
# bounds below are local safety limits only. They are not provider facts and
# must not be presented as such; they exist to reject unbounded hostile input
# before any documented field is dereferenced or any member name is classified.
RESERVED_DEFENSIVE_MAX_EMPLOYMENTS = 1000
RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH = 512
RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH = 64
RESERVED_DEFENSIVE_MAX_ERROR_CODE_LENGTH = 64
RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH = 1024
RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS = 1000
RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH = 256
RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS = 64

_UTR_RE = re.compile(r"[0-9]{10}")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")

_EMPLOYMENT_DOCUMENTED_FIELDS = (
    HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS
    | HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS
)
_TOP_LEVEL_DOCUMENTED_FIELDS = frozenset({"employments"})
_ERROR_BODY_DOCUMENTED_FIELDS = frozenset({"code", "message"})
_DOCUMENTED_STATUSES = frozenset({HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS}) | (
    HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_STATUSES
)


class HMRCIndividualEmploymentContractError(ValueError):
    """Controlled validation failure whose message never includes source values."""


# ── Frozen, redacted, non-sendable request intent ───────────────────────────


class IndividualEmploymentRequestIntent:
    """Frozen request intent for the documented GET operation.

    Deliberately not a ``ProviderRequest``. It exposes no method, URL, headers,
    body, path or raw UTR; only the validated (non-sensitive) tax year is
    readable. The supplied UTR is validated for fail-closed construction but is
    then discarded: no raw UTR, UTR-bearing path or recoverable equivalent is
    retained on the object.
    """

    __slots__ = ("__tax_year",)

    def __init__(self, *, utr: str, tax_year: str) -> None:
        # Fail closed on a malformed UTR, then discard it. The intent keeps only
        # the validated, non-sensitive tax year and no UTR-bearing state.
        _validate_utr(utr)
        validated_tax_year = _validate_tax_year(tax_year)
        object.__setattr__(
            self, "_IndividualEmploymentRequestIntent__tax_year", validated_tax_year
        )

    @property
    def tax_year(self) -> str:
        return object.__getattribute__(
            self, "_IndividualEmploymentRequestIntent__tax_year"
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("IndividualEmploymentRequestIntent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("IndividualEmploymentRequestIntent is immutable")

    def __repr__(self) -> str:
        return "IndividualEmploymentRequestIntent([REDACTED])"


# ── Frozen, redacted observations ───────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class EmploymentRecordObservation:
    """Validated facts from one element of the ``employments`` array.

    ``off_payroll_work_flag`` is ``None`` when, and only when, the optional
    field is absent; ``absent_fields`` records that omission. No field in the
    captured OpenAPI schema is declared nullable, so explicit ``null`` is
    rejected rather than retained. ``off_payroll_work_flag`` present values are
    therefore always exact built-in ``True``/``False``. Unknown member names are
    recorded for review without their values ever being inspected or retained.
    """

    employer_paye_reference: str
    employer_name: str
    off_payroll_work_flag: bool | None = None
    absent_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()

    def __repr__(self) -> str:
        return "EmploymentRecordObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class EmploymentHistoryObservation:
    """Validated annual-summary observation for a documented 200 response.

    Completeness is always ``UNVERIFIED``: this is an annual-summary
    observation, not proof of a complete current position. The raw response
    payload is not retained.
    """

    tax_year: str
    status_code: int
    employments: tuple[EmploymentRecordObservation, ...]
    completeness: str = COMPLETENESS_UNVERIFIED
    absent_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()

    def __repr__(self) -> str:
        return "EmploymentHistoryObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class EmploymentErrorObservation:
    """Classified, non-echoing observation for a documented error status.

    The provider ``message`` is validated for structure but never retained or
    exposed because it may echo the submitted UTR or tax year. Only the
    documented, constant ``error_code`` is retained.
    """

    tax_year: str
    status_code: int
    error_code: str
    unknown_fields: frozenset[str] = frozenset()

    def __repr__(self) -> str:
        return "EmploymentErrorObservation([REDACTED])"


# ── Exact built-in type and format validators ───────────────────────────────


def _validate_utr(value: Any) -> str:
    if type(value) is not str:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: utr must be a string"
        )
    if _UTR_RE.fullmatch(value) is None:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: utr must be a 10-digit string"
        )
    return value


def _validate_tax_year(value: Any) -> str:
    if type(value) is not str:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: tax_year must be a string"
        )
    if _TAX_YEAR_RE.fullmatch(value) is None:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: tax_year must match YYYY-YY"
        )
    return value


def _require_exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise HMRCIndividualEmploymentContractError(
            f"HMRC Individual Employment contract: {field} must be an integer"
        )
    return value


def _require_exact_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise HMRCIndividualEmploymentContractError(
            f"HMRC Individual Employment contract: {field} must be a boolean"
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
        raise HMRCIndividualEmploymentContractError(
            f"HMRC Individual Employment contract: {field} must be a string"
        )
    if len(value) > max_length:
        raise HMRCIndividualEmploymentContractError(
            f"HMRC Individual Employment contract: {field} exceeds the "
            "Reserved defensive bound"
        )
    return value


def _has_unsafe_unicode_character(text: str) -> bool:
    """Return ``True`` if any character is in Unicode general category ``C``.

    Category ``C`` is the conservative unsafe set: control (``Cc``), format
    (``Cf``), surrogate (``Cs``), private-use (``Co``) and unassigned (``Cn``).
    This rejects the earlier control/surrogate/noncharacter set *and* format
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
    not rejected here. The provider error ``message`` is intentionally not
    routed through this check because it is validated but never retained.
    """
    result = _require_documented_string(value, field, max_length)
    if _has_unsafe_unicode_character(result):
        raise HMRCIndividualEmploymentContractError(
            f"HMRC Individual Employment contract: {field} contains unsafe "
            "Unicode characters"
        )
    return result


def _validate_member_names(mapping: Mapping[str, Any], documented: frozenset[str]) -> None:
    """Bound and type-check open-schema member names before classification.

    Runs before known/unknown classification or any operation that assumes safe
    strings. Only member *names* are inspected; member *values* are never
    dereferenced, copied, stringified, compared, hashed, logged or retained.
    """
    if len(mapping) > RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: object member count exceeds "
            "the Reserved defensive bound"
        )

    unknown_count = 0
    for name in mapping:
        if type(name) is not str:
            raise HMRCIndividualEmploymentContractError(
                "HMRC Individual Employment contract: object member names must "
                "be strings"
            )
        if len(name) > RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH:
            raise HMRCIndividualEmploymentContractError(
                "HMRC Individual Employment contract: object member name "
                "exceeds the Reserved defensive bound"
            )
        if _has_unsafe_unicode_character(name):
            raise HMRCIndividualEmploymentContractError(
                "HMRC Individual Employment contract: object member name "
                "contains control or unsafe characters"
            )
        if name not in documented:
            unknown_count += 1

    if unknown_count > RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: unknown member count exceeds "
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


def build_individual_employment_request(
    *, utr: str, tax_year: str
) -> IndividualEmploymentRequestIntent:
    """Build a frozen, redacted, non-sendable request intent.

    Validates a 10-digit SA UTR and the documented tax-year form. Error text is
    constant and never echoes the supplied values. The returned intent exposes
    no UTR, UTR-bearing path, headers or body.
    """
    return IndividualEmploymentRequestIntent(utr=utr, tax_year=tax_year)


def _observe_employment_history(
    tax_year: str, status_code: int, payload: Any
) -> EmploymentHistoryObservation:
    if type(payload) is not dict:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: success payload must be a JSON object"
        )
    _validate_member_names(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    if "employments" not in payload:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: success payload is missing employments"
        )
    employments = payload["employments"]
    if type(employments) is not list:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employments must be a JSON array"
        )
    if not employments:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employments must not be empty"
        )
    if len(employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employments exceeds the "
            "Reserved defensive bound"
        )

    records = tuple(_parse_employment_record(entry) for entry in employments)
    _, unknown = _classify(payload, _TOP_LEVEL_DOCUMENTED_FIELDS)
    return EmploymentHistoryObservation(
        tax_year=tax_year,
        status_code=status_code,
        employments=records,
        completeness=COMPLETENESS_UNVERIFIED,
        unknown_fields=unknown,
    )


def _parse_employment_record(entry: Any) -> EmploymentRecordObservation:
    if type(entry) is not dict:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employment must be a JSON object"
        )
    _validate_member_names(entry, _EMPLOYMENT_DOCUMENTED_FIELDS)

    if "employerPayeReference" not in entry:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employment is missing "
            "employerPayeReference"
        )
    if "employerName" not in entry:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: employment is missing employerName"
        )

    employer_paye_reference = _require_employer_string(
        entry["employerPayeReference"],
        "employerPayeReference",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    )
    employer_name = _require_employer_string(
        entry["employerName"],
        "employerName",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    )

    off_payroll_work_flag: bool | None = None
    if "offPayrollWorkFlag" in entry:
        # No field in the captured schema is nullable: an exact built-in bool is
        # the only accepted present value, so explicit null fails closed here.
        off_payroll_work_flag = _require_exact_bool(
            entry["offPayrollWorkFlag"], "offPayrollWorkFlag"
        )

    absent, unknown = _classify(entry, _EMPLOYMENT_DOCUMENTED_FIELDS)
    return EmploymentRecordObservation(
        employer_paye_reference=employer_paye_reference,
        employer_name=employer_name,
        off_payroll_work_flag=off_payroll_work_flag,
        absent_fields=absent,
        unknown_fields=unknown,
    )


def _observe_employment_error(
    tax_year: str, status_code: int, payload: Any
) -> EmploymentErrorObservation:
    if type(payload) is not dict:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: error payload must be a JSON object"
        )
    _validate_member_names(payload, _ERROR_BODY_DOCUMENTED_FIELDS)
    if "code" not in payload:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: error payload is missing code"
        )
    if "message" not in payload:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: error payload is missing message"
        )

    error_code = _require_documented_string(
        payload["code"], "code", RESERVED_DEFENSIVE_MAX_ERROR_CODE_LENGTH
    )
    # The provider message is validated for structure only. It is deliberately
    # not retained or echoed because it may contain the submitted UTR/tax year.
    _require_documented_string(
        payload["message"], "message", RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH
    )

    if error_code not in HMRC_INDIVIDUAL_EMPLOYMENT_ERROR_CODES[status_code]:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: undocumented error code "
            "for the HTTP status"
        )

    _, unknown = _classify(payload, _ERROR_BODY_DOCUMENTED_FIELDS)
    return EmploymentErrorObservation(
        tax_year=tax_year,
        status_code=status_code,
        error_code=error_code,
        unknown_fields=unknown,
    )


def observe_individual_employment_response(
    request: IndividualEmploymentRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: Any,
) -> EmploymentHistoryObservation | EmploymentErrorObservation:
    """Validate a response for the documented GET operation and fail closed.

    Accepts only the exact documented response media type, a structurally valid
    top-level payload and documented statuses. Success additionally requires a
    non-empty ``employments`` collection. Documented errors are classified into
    constant, non-echoing observations; undocumented or malformed combinations
    are rejected.
    """
    if type(request) is not IndividualEmploymentRequestIntent:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: request must be an "
            "IndividualEmploymentRequestIntent"
        )

    status = _require_exact_int(status_code, "status_code")
    if status not in _DOCUMENTED_STATUSES:
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: undocumented HTTP status"
        )

    if (
        type(content_type) is not str
        or content_type != HMRC_INDIVIDUAL_EMPLOYMENT_RESPONSE_CONTENT_TYPE
    ):
        raise HMRCIndividualEmploymentContractError(
            "HMRC Individual Employment contract: response Content-Type must be "
            "application/json"
        )

    tax_year = request.tax_year
    if status == HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS:
        return _observe_employment_history(tax_year, status, payload)
    return _observe_employment_error(tax_year, status, payload)
