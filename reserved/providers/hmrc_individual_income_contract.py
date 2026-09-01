"""Network-inert HMRC Individual Income 1.2 literal request/response contract.

This module captures the reviewed, documented endpoint facts for::

    GET /individual-income/sa/{utr}/annual-summary/{taxYear}

with ``Accept: application/vnd.hmrc.1.2+json`` and OAuth scope
``read:individual-income``. It is an offline, sandbox-origin request *intent*
and response *observation* only. It owns no HTTP client, transport, credential,
token, authorization header, persistence, routing, provider-to-canonical
mapping, production origin or activation path.

Authority observed 2026-09-01. See
``docs/HMRC_INDIVIDUAL_INCOME_1_2_ENDPOINT_EVIDENCE.md`` for the endpoint facts
and ``docs/HMRC_INDIVIDUAL_INCOME_1_2_CONTRACT_EVIDENCE.md`` for the
implementation decisions recorded for this contract. The raw UTR is validated
and discarded; the raw response payload and error ``message`` are never
retained.

State Pension lump-sum reference ``267/LS500`` is a literal provider fact only:
this module attaches no special downstream tax or identity behaviour to it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal
from types import MappingProxyType

# ── Exact documented constants (provider facts, not Reserved inference) ─────

HMRC_INDIVIDUAL_INCOME_API = "individual-income"
HMRC_INDIVIDUAL_INCOME_API_VERSION = "1.2"
HMRC_INDIVIDUAL_INCOME_HTTP_METHOD = "GET"
HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE = (
    "/individual-income/sa/{utr}/annual-summary/{taxYear}"
)
HMRC_INDIVIDUAL_INCOME_ACCEPT = "application/vnd.hmrc.1.2+json"
HMRC_INDIVIDUAL_INCOME_SCOPE = "read:individual-income"
HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE = "application/json"

# The exact documented status/code pairings. The outer mapping is read-only and
# every nested code set is a frozenset: mutation attempts at either level leave
# the validation mapping unchanged.
HMRC_INDIVIDUAL_INCOME_400_CODES = frozenset({"SA_UTR_INVALID", "TAX_YEAR_INVALID"})
HMRC_INDIVIDUAL_INCOME_401_CODES = frozenset({"UNAUTHORIZED"})
HMRC_INDIVIDUAL_INCOME_404_CODES = frozenset({"NOT_FOUND"})
HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES = MappingProxyType({
    400: HMRC_INDIVIDUAL_INCOME_400_CODES,
    401: HMRC_INDIVIDUAL_INCOME_401_CODES,
    404: HMRC_INDIVIDUAL_INCOME_404_CODES,
})

HMRC_INDIVIDUAL_INCOME_COMPLETENESS = "UNVERIFIED"

# ── Exact documented field-name universes ────────────────────────────────────

_TOP_LEVEL_NAMES = frozenset({
    "employments",
    "pensionsAnnuitiesAndOtherStateBenefits",
})
_EMPLOYMENT_NAMES = frozenset({"employerPayeReference", "payFromEmployment"})
_BENEFITS_NAMES = frozenset({
    "otherPensionsAndRetirementAnnuities",
    "incapacityBenefit",
    "jobseekersAllowance",
    "seissNetPaid",
})
_ERROR_NAMES = frozenset({"code", "message"})

# ── Reserved defensive bounds (NOT endpoint sign/precision/magnitude facts) ──
# These are finite safety limits only. They are not evidence of an endpoint
# minimum/maximum, sign rule, scale, rounding rule or collection size.

_RESERVED_MAX_OBJECT_MEMBERS = 64        # max members in any JSON object
_RESERVED_MAX_UNKNOWN_KEYS = 32          # max additive unknown keys per object
_RESERVED_MAX_KEY_LENGTH = 256           # max characters per object key
_RESERVED_MAX_STRING_LENGTH = 4096       # max characters per retained string value
_RESERVED_MAX_EMPLOYMENTS = 10_000       # max employment items in one response
_RESERVED_NUMBER_MAX_DIGITS = 38         # max significant digits of a number
_RESERVED_NUMBER_MAX_PLACES = 12         # max fractional places of a Decimal
_RESERVED_NUMBER_MAX_MAGNITUDE = Decimal("1000000000000000000")  # 10**18
_RESERVED_NUMBER_MAX_INT = 10 ** 18

# ASCII-only regexes. ``[0-9]`` deliberately excludes Unicode ``Nd`` digits, so
# ``str.isdigit()``/``isdecimal()``/``isnumeric()`` semantics are never used.
_UTR_RE = re.compile(r"[0-9]{10}")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")

# Literal redaction marker used in the UTR-free request path.
UTR_REDACTION_MARKER = "[UTR-REDACTED]"


class HMRCIndividualIncomeContractError(ValueError):
    """Fail-closed validation error whose message never includes source data."""


def _fail(rule: str) -> HMRCIndividualIncomeContractError:
    return HMRCIndividualIncomeContractError(
        f"HMRC individual income contract: {rule}"
    )


# ── Defensive validators ─────────────────────────────────────────────────────


def _require_safe_name(name: object, context: str) -> str:
    """Require an exact built-in string key with a bounded, safe name.

    Keys are object member *names*. Empty names, non-string keys and oversized
    names are rejected before any value is dereferenced or inspected. Every
    character must be outside Unicode general category ``C`` (``Cc`` control,
    ``Cf`` format/bidi/zero-width, ``Cs`` surrogate, ``Co`` private-use and
    ``Cn`` unassigned/noncharacter). Ordinary international letters, combining
    marks, CJK, emoji, spaces and separator whitespace remain accepted where
    otherwise within bounds.
    """
    if type(name) is not str:
        raise _fail(f"{context} keys must be exact built-in strings")
    if not name:
        raise _fail(f"{context} keys must be non-empty")
    if len(name) > _RESERVED_MAX_KEY_LENGTH:
        raise _fail(f"{context} contains an oversized key name")
    for char in name:
        if unicodedata.category(char).startswith("C"):
            raise _fail(f"{context} contains an unsafe character in a key name")
    return name


def _require_string_value(value: object, field: str) -> str:
    """Require an exact built-in string; empty/whitespace-only is schema-valid.

    The documented schema declares no ``minLength``. A finite Reserved length
    bound is applied, but empty and whitespace-only values are accepted as
    schema-valid and semantically unverified.
    """
    if type(value) is not str:
        raise _fail(f"{field} must be an exact built-in string")
    if len(value) > _RESERVED_MAX_STRING_LENGTH:
        raise _fail(f"{field} exceeds the reserved string bound")
    return value


def _require_object(value: object, field: str) -> dict:
    if type(value) is not dict:
        raise _fail(f"{field} must be an exact built-in object")
    return value


def _require_list(value: object, field: str) -> list:
    if type(value) is not list:
        raise _fail(f"{field} must be an exact built-in array")
    return value


def _require_int_number(value: int, field: str) -> int:
    """Apply only the Reserved magnitude bound; ints are always finite."""
    if value > _RESERVED_NUMBER_MAX_INT or value < -_RESERVED_NUMBER_MAX_INT:
        raise _fail(f"{field} exceeds the reserved integer magnitude bound")
    return value


def _require_decimal_number(value: Decimal, field: str) -> Decimal:
    """Apply the Reserved coefficient/exponent/magnitude bounds.

    The value is retained exactly: no quantising, rounding, sign change
    (including negative zero) or exponent change is performed.
    """
    parts = value.as_tuple()
    places = max(0, -parts.exponent)
    integer_digits = max(1, len(parts.digits) + parts.exponent)
    if (
        abs(value) > _RESERVED_NUMBER_MAX_MAGNITUDE
        or len(parts.digits) > _RESERVED_NUMBER_MAX_DIGITS
        or places > _RESERVED_NUMBER_MAX_PLACES
        or integer_digits > _RESERVED_NUMBER_MAX_DIGITS
    ):
        raise _fail(f"{field} exceeds the reserved decimal bound")
    return value


def _parse_number(value: object, field: str) -> int | Decimal:
    """Decode a JSON number: exact built-in ``int`` or exact ``Decimal`` only.

    ``bool`` (a subclass of ``int``), ``float``, ``str``, every numeric
    subclass, NaN and infinities are rejected. The exact value is retained as
    ``int`` or ``Decimal`` without normalisation. Upstream JSON float parsing
    must be done with ``parse_float=Decimal`` by the later transport; this
    offline package never parses floats.
    """
    if type(value) is int:
        return _require_int_number(value, field)
    if type(value) is Decimal:
        if not value.is_finite():
            raise _fail(f"{field} must be a finite number")
        return _require_decimal_number(value, field)
    raise _fail(f"{field} must be an exact built-in int or Decimal")


def _classify_object_members(
    obj: dict, known_names: frozenset[str], context: str
) -> frozenset[str]:
    """Validate keys and return the bounded safe unknown *names* only.

    Unknown values are never traversed, copied, stringified, compared, hashed,
    logged or otherwise inspected.
    """
    if len(obj) > _RESERVED_MAX_OBJECT_MEMBERS:
        raise _fail(f"{context} exceeds the reserved object-member bound")
    unknown: list[str] = []
    for key in obj:
        safe_key = _require_safe_name(key, context)
        if safe_key not in known_names:
            unknown.append(safe_key)
    if len(unknown) > _RESERVED_MAX_UNKNOWN_KEYS:
        raise _fail(f"{context} exceeds the reserved unknown-key bound")
    return frozenset(unknown)


def _require_unknown_names(value: object, context: str) -> frozenset[str]:
    """Require the retained unknown-name set to be an exact bounded frozenset.

    The observation constructors retain only additive unknown *names*; they must
    already be exact built-in strings classified as safe and within the unknown
    key bound. Mutable sets, set subclasses and unsafe names are rejected.
    """
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown names must be an exact frozenset")
    if len(value) > _RESERVED_MAX_UNKNOWN_KEYS:
        raise _fail(f"{context} exceeds the reserved unknown-key bound")
    for name in value:
        _require_safe_name(name, context)
    return value


# ── Request intent ───────────────────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class IndividualIncomeRequestIntent:
    """Frozen, UTR-free intent for the documented annual-summary read.

    The only construction boundary accepts ``utr`` and ``tax_year``; the raw UTR
    is validated as exactly ten ASCII digits and immediately discarded. Every
    other field is derived internally and cannot be supplied or replaced through
    the constructor or ``dataclasses.replace``. The intent is not, does not
    inherit from, and does not convert by default into a generic sendable
    request. The raw UTR is never present in any field, so it cannot leak through
    ordinary, private, name-mangled, serialized, copied, equality/hash,
    representation or conversion state.
    """

    utr: InitVar[str]
    tax_year: str
    method: str = field(init=False, default=HMRC_INDIVIDUAL_INCOME_HTTP_METHOD)
    sandbox_origin: str = field(init=False, default=HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN)
    path_template: str = field(init=False, default=HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE)
    accept: str = field(init=False, default=HMRC_INDIVIDUAL_INCOME_ACCEPT)
    scope: str = field(init=False, default=HMRC_INDIVIDUAL_INCOME_SCOPE)
    redacted_path: str = field(init=False, default="")

    def __post_init__(self, utr: str) -> None:
        _require_ascii_utr(utr)
        tax_year = _require_tax_year(self.tax_year)
        object.__setattr__(self, "tax_year", tax_year)
        object.__setattr__(self, "method", HMRC_INDIVIDUAL_INCOME_HTTP_METHOD)
        object.__setattr__(self, "sandbox_origin", HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN)
        object.__setattr__(self, "path_template", HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE)
        object.__setattr__(self, "accept", HMRC_INDIVIDUAL_INCOME_ACCEPT)
        object.__setattr__(self, "scope", HMRC_INDIVIDUAL_INCOME_SCOPE)
        object.__setattr__(
            self,
            "redacted_path",
            HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE.replace("{utr}", UTR_REDACTION_MARKER)
            .replace("{taxYear}", tax_year),
        )

    def __repr__(self) -> str:
        return (
            "IndividualIncomeRequestIntent(method='GET', sandbox_origin="
            f"{self.sandbox_origin!r}, path_template={self.path_template!r}, "
            f"accept={self.accept!r}, scope={self.scope!r}, "
            f"tax_year={self.tax_year!r}, redacted_path={self.redacted_path!r})"
        )


def _require_ascii_utr(utr: object) -> None:
    """Validate exactly ten ASCII digits, then the caller discards ``utr``."""
    if type(utr) is not str:
        raise _fail("utr must be a string of exactly ten ASCII digits")
    if _UTR_RE.fullmatch(utr) is None:
        raise _fail("utr must be exactly ten ASCII digits ([0-9]{10})")


def _require_tax_year(tax_year: object) -> str:
    if type(tax_year) is not str:
        raise _fail("tax_year must be a string matching ^[0-9]{4}-[0-9]{2}$")
    if _TAX_YEAR_RE.fullmatch(tax_year) is None:
        raise _fail("tax_year must match ^[0-9]{4}-[0-9]{2}$")
    return tax_year


def build_individual_income_request(*, utr: str, tax_year: str) -> IndividualIncomeRequestIntent:
    """Build a frozen, UTR-free request intent.

    This is a thin, keyword-only convenience over the single validated
    construction boundary: the raw UTR is validated as exactly ten ASCII digits
    and discarded, and every derived field is computed internally.
    """
    return IndividualIncomeRequestIntent(utr=utr, tax_year=tax_year)


# ── Observations ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class EmploymentItemObservation:
    """Validated facts from one ``employments`` array item."""

    employer_paye_reference: str
    pay_from_employment: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _require_string_value(self.employer_paye_reference, "employerPayeReference")
        _parse_number(self.pay_from_employment, "payFromEmployment")
        _require_unknown_names(self.unknown_names, "employment item")

    def __repr__(self) -> str:
        return "EmploymentItemObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class PensionsBenefitsObservation:
    """Validated facts from ``pensionsAnnuitiesAndOtherStateBenefits``.

    Omission of a documented member is ``None`` and is never coerced to zero;
    explicit null is rejected before this object is built.
    """

    other_pensions_and_retirement_annuities: int | Decimal | None = None
    incapacity_benefit: int | Decimal | None = None
    jobseekers_allowance: int | Decimal | None = None
    seiss_net_paid: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    absent_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        present = self.present_fields
        absent = self.absent_fields
        if type(present) is not frozenset:
            raise _fail("benefits present_fields must be an exact frozenset")
        if type(absent) is not frozenset:
            raise _fail("benefits absent_fields must be an exact frozenset")
        if present & absent:
            raise _fail("benefits present and absent fields must be disjoint")
        if present | absent != _BENEFITS_NAMES:
            raise _fail("benefits present and absent fields must be exhaustive")
        for name, value in (
            ("otherPensionsAndRetirementAnnuities", self.other_pensions_and_retirement_annuities),
            ("incapacityBenefit", self.incapacity_benefit),
            ("jobseekersAllowance", self.jobseekers_allowance),
            ("seissNetPaid", self.seiss_net_paid),
        ):
            if name in present:
                if value is None:
                    raise _fail(f"{name} must not be None when present")
                _parse_number(value, name)
            elif value is not None:
                raise _fail(f"{name} must be None when absent")
        _require_unknown_names(self.unknown_names, "benefits object")

    def __repr__(self) -> str:
        return "PensionsBenefitsObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class IndividualIncomeAnnualSummaryObservation:
    """Validated facts from a documented HTTP 200 annual-summary response."""

    employments: tuple[EmploymentItemObservation, ...]
    pensions_benefits: PensionsBenefitsObservation
    unknown_names: frozenset[str] = frozenset()
    completeness: str = HMRC_INDIVIDUAL_INCOME_COMPLETENESS

    def __post_init__(self) -> None:
        if type(self.employments) is not tuple:
            raise _fail("employments must be an exact built-in tuple")
        if len(self.employments) > _RESERVED_MAX_EMPLOYMENTS:
            raise _fail("employments exceeds the reserved item bound")
        for item in self.employments:
            if type(item) is not EmploymentItemObservation:
                raise _fail("employments must contain exact employment observations")
        if type(self.pensions_benefits) is not PensionsBenefitsObservation:
            raise _fail("pensions_benefits must be an exact PensionsBenefitsObservation")
        if type(self.completeness) is not str or self.completeness != HMRC_INDIVIDUAL_INCOME_COMPLETENESS:
            raise _fail("completeness must be the exact documented UNVERIFIED value")
        _require_unknown_names(self.unknown_names, "annual-summary observation")

    def __repr__(self) -> str:
        return "IndividualIncomeAnnualSummaryObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class IndividualIncomeErrorObservation:
    """Validated facts from a documented HTTP 400/401/404 error response.

    The error ``message`` is validated as a string and then discarded; only the
    documented ``code`` and ``status_code`` are retained.
    """

    status_code: int
    code: str
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self.status_code) is not int:
            raise _fail("status_code must be an exact built-in integer")
        if self.status_code not in HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES:
            raise _fail("status_code is not a documented error status")
        if type(self.code) is not str:
            raise _fail("code must be an exact built-in string")
        if self.code not in HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[self.status_code]:
            raise _fail("error code does not match the documented status")
        _require_unknown_names(self.unknown_names, "error body")

    def __repr__(self) -> str:
        return (
            f"IndividualIncomeErrorObservation(status_code={self.status_code}, "
            f"code={self.code!r})"
        )


# ── Response observation ─────────────────────────────────────────────────────


def _parse_employment_item(item: object) -> EmploymentItemObservation:
    obj = _require_object(item, "employment item")
    unknown_names = _classify_object_members(obj, _EMPLOYMENT_NAMES, "employment item")

    if "employerPayeReference" not in obj:
        raise _fail("employment item is missing employerPayeReference")
    if "payFromEmployment" not in obj:
        raise _fail("employment item is missing payFromEmployment")

    employer_paye_reference = _require_string_value(
        obj["employerPayeReference"], "employerPayeReference"
    )
    pay_from_employment = _parse_number(obj["payFromEmployment"], "payFromEmployment")

    return EmploymentItemObservation(
        employer_paye_reference=employer_paye_reference,
        pay_from_employment=pay_from_employment,
        unknown_names=unknown_names,
    )


def _parse_benefits(value: object) -> PensionsBenefitsObservation:
    obj = _require_object(value, "pensionsAnnuitiesAndOtherStateBenefits")
    unknown_names = _classify_object_members(obj, _BENEFITS_NAMES, "benefits object")

    present: list[str] = []
    absent: list[str] = []
    parsed: dict[str, int | Decimal] = {}
    for name in sorted(_BENEFITS_NAMES):
        if name not in obj:
            absent.append(name)
            continue
        present.append(name)
        raw = obj[name]
        if raw is None:
            raise _fail(f"{name} must not be explicit null")
        parsed[name] = _parse_number(raw, name)

    return PensionsBenefitsObservation(
        other_pensions_and_retirement_annuities=parsed.get(
            "otherPensionsAndRetirementAnnuities"
        ),
        incapacity_benefit=parsed.get("incapacityBenefit"),
        jobseekers_allowance=parsed.get("jobseekersAllowance"),
        seiss_net_paid=parsed.get("seissNetPaid"),
        present_fields=frozenset(present),
        absent_fields=frozenset(absent),
        unknown_names=unknown_names,
    )


def _parse_annual_summary(payload: dict) -> IndividualIncomeAnnualSummaryObservation:
    obj = _require_object(payload, "annual-summary response")
    unknown_names = _classify_object_members(obj, _TOP_LEVEL_NAMES, "top-level object")

    if "employments" not in obj:
        raise _fail("annual-summary response is missing employments")
    if "pensionsAnnuitiesAndOtherStateBenefits" not in obj:
        raise _fail(
            "annual-summary response is missing pensionsAnnuitiesAndOtherStateBenefits"
        )

    employments_raw = _require_list(obj["employments"], "employments")
    if len(employments_raw) > _RESERVED_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the reserved item bound")

    employments = tuple(_parse_employment_item(item) for item in employments_raw)
    benefits = _parse_benefits(obj["pensionsAnnuitiesAndOtherStateBenefits"])

    return IndividualIncomeAnnualSummaryObservation(
        employments=employments,
        pensions_benefits=benefits,
        unknown_names=unknown_names,
        completeness=HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    )


def _parse_error(status_code: int, payload: dict) -> IndividualIncomeErrorObservation:
    obj = _require_object(payload, "error body")
    unknown_names = _classify_object_members(obj, _ERROR_NAMES, "error body")

    if "code" not in obj:
        raise _fail("error body is missing code")
    if "message" not in obj:
        raise _fail("error body is missing message")

    code = _require_string_value(obj["code"], "code")
    # Validate the message as a string (Reserved length bound only) and then
    # discard it: the raw message is never retained or echoed.
    _require_string_value(obj["message"], "message")

    allowed = HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[status_code]
    if code not in allowed:
        raise _fail("error code does not match the documented status")

    return IndividualIncomeErrorObservation(
        status_code=status_code,
        code=code,
        unknown_names=unknown_names,
    )


def _require_request_intent(request: object) -> None:
    if type(request) is not IndividualIncomeRequestIntent:
        raise _fail("request must be an exact IndividualIncomeRequestIntent")


def observe_individual_income_response(
    request: IndividualIncomeRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: object,
) -> IndividualIncomeAnnualSummaryObservation | IndividualIncomeErrorObservation:
    """Observe an already-retrieved response without any transport.

    Only the documented HTTP 200 success shape and the documented HTTP 400/401/
    404 error shapes are accepted. HTTP 404 is retained as unavailable
    evidence, never as an authoritative empty or zero-income record.
    """
    _require_request_intent(request)
    if type(status_code) is not int or isinstance(status_code, bool):
        raise _fail("status_code must be an exact built-in integer")
    if type(content_type) is not str:
        raise _fail("content_type must be an exact built-in string")

    if status_code == 200:
        if content_type != HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE:
            raise _fail("HTTP 200 requires exact application/json")
        return _parse_annual_summary(_require_object(payload, "response payload"))

    if status_code in (400, 401, 404):
        if content_type != HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE:
            raise _fail("documented error statuses require exact application/json")
        return _parse_error(status_code, _require_object(payload, "error payload"))

    raise _fail("undocumented HTTP status is not accepted")
