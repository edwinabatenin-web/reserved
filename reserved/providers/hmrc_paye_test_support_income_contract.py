"""Network-inert HMRC Individual PAYE Test Support 2.1 income create contract.

This module captures the reviewed, documented endpoint facts for exactly one
sandbox create operation::

    POST /individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}

``operationId`` ``createAnnualIncomeSummaryTestData``. It is an offline,
Sandbox-only write-side *request intent* and *response observation* only. It
owns no HTTP client, transport, credential, token, authorization header,
persistence, routing, provider-to-canonical mapping, production origin or
activation path. It is not, does not inherit from, and does not convert by
default into a generic sendable request.

Authority observed 2026-09-02. See
``docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`` for the endpoint facts
and ``docs/HMRC_PAYE_TEST_SUPPORT_2_1_INCOME_CONTRACT_EVIDENCE.md`` for the
implementation decisions recorded for this contract.

The request boundary accepts an SA UTR (ten ASCII digits), a tax year
(``^[0-9]{4}-[0-9]{2}$``) and an optional ``scenario``. The raw UTR is
validated and immediately discarded; only the tax year and scenario
presence/value are retained. The raw response payload is never retained and no
rendered URL/path, credential, authorization header, token or sendable
header/body is exposed anywhere.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal

# ── Exact documented constants (provider facts, not Reserved inference) ─────

HMRC_PAYE_TEST_SUPPORT_OPERATION_ID = "createAnnualIncomeSummaryTestData"
HMRC_PAYE_TEST_SUPPORT_API = "individual-paye-test-support"
HMRC_PAYE_TEST_SUPPORT_API_VERSION = "2.1"
HMRC_PAYE_TEST_SUPPORT_HTTP_METHOD = "POST"
HMRC_PAYE_TEST_SUPPORT_SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
HMRC_PAYE_TEST_SUPPORT_PATH_TEMPLATE = (
    "/individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}"
)
HMRC_PAYE_TEST_SUPPORT_ACCEPT = "application/vnd.hmrc.2.1+json"
HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE = "application/json"
HMRC_PAYE_TEST_SUPPORT_SUCCESS_STATUS = 201

# Application-restricted OAuth 2.0 Client Credentials. The specification's
# scope map/list are empty, so no named OAuth scope exists and none is invented.
HMRC_PAYE_TEST_SUPPORT_OAUTH_GRANT_TYPE = "client_credentials"
HMRC_PAYE_TEST_SUPPORT_OAUTH_SCOPES = frozenset()

HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_1 = "HAPPY_PATH_1"
HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_2 = "HAPPY_PATH_2"
HMRC_PAYE_TEST_SUPPORT_SCENARIOS = frozenset({
    HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_1,
    HMRC_PAYE_TEST_SUPPORT_SCENARIO_HAPPY_PATH_2,
})

HMRC_PAYE_TEST_SUPPORT_COMPLETENESS = "UNVERIFIED"

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

# Private sentinel used only at the build boundary to distinguish "scenario
# omitted" from an explicit ``None`` (JSON null), which fails closed.
_SCENARIO_OMITTED = object()


class HMRCPayeTestSupportIncomeContractError(ValueError):
    """Fail-closed validation error whose message never includes source data."""


def _fail(rule: str) -> HMRCPayeTestSupportIncomeContractError:
    return HMRCPayeTestSupportIncomeContractError(
        f"HMRC PAYE Test Support income contract: {rule}"
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
    """Require an exact built-in bounded string; empty/space-only is schema-valid.

    The documented schema declares no ``minLength``. A finite Reserved length
    bound is applied, but empty and ordinary-space-only values are accepted as
    schema-valid and semantically unverified. Every character must be outside
    Unicode general category ``C`` (``Cc`` control, ``Cf`` format/bidi/zero-width,
    ``Cs`` surrogate, ``Co`` private-use and ``Cn`` unassigned/noncharacter);
    unsafe category-C characters are rejected without trimming or normalising the
    otherwise valid string.
    """
    if type(value) is not str:
        raise _fail(f"{field} must be an exact built-in string")
    if len(value) > _RESERVED_MAX_STRING_LENGTH:
        raise _fail(f"{field} exceeds the reserved string bound")
    for char in value:
        if unicodedata.category(char).startswith("C"):
            raise _fail(f"{field} contains an unsafe category-C character")
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
    must be done with ``parse_float=Decimal`` by a later transport; this offline
    package never parses floats.
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


def _require_unknown_names(
    value: object, context: str, known_names: frozenset[str]
) -> frozenset[str]:
    """Require the retained unknown-name set to be exact, bounded and disjoint.

    The observation constructors retain only additive unknown *names*; they must
    already be exact built-in strings classified as safe, within the unknown key
    bound and disjoint from the documented member names for that object. Mutable
    sets, set subclasses, unsafe names, documented-name collisions and
    non-string members are rejected.
    """
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown names must be an exact frozenset")
    if len(value) > _RESERVED_MAX_UNKNOWN_KEYS:
        raise _fail(f"{context} exceeds the reserved unknown-key bound")
    for name in value:
        _require_safe_name(name, context)
    if value & known_names:
        raise _fail(f"{context} unknown names must be disjoint from documented names")
    return value


def _require_scenario(scenario: object) -> str:
    """Require an exact built-in string that is a documented scenario literal.

    Subclasses, custom objects, whitespace, Unicode lookalikes, ``None`` and any
    string outside the two documented literals fail closed.
    """
    if type(scenario) is not str:
        raise _fail("scenario must be an exact built-in string")
    if scenario not in HMRC_PAYE_TEST_SUPPORT_SCENARIOS:
        raise _fail("scenario is not a documented scenario identifier")
    return scenario


# ── Request intent ───────────────────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class CreateAnnualIncomeSummaryRequestIntent:
    """Frozen, UTR-free intent for the documented annual-summary create.

    The construction boundary accepts ``utr``, ``tax_year`` and an optional
    ``scenario``. The raw UTR is validated as exactly ten ASCII digits and
    immediately discarded. Only the validated tax year and the scenario
    presence/value are retained. Omitting ``scenario`` (via the private sentinel
    default) records absence; an explicit ``None`` (JSON null) fails closed. The
    intent is not, does not inherit from, and does not convert by default into a
    generic sendable request, and it exposes no rendered URL/path, credential,
    authorization header, token, header map, body or transport. The raw UTR is
    never present in any field, so it cannot leak through ordinary, private,
    name-mangled, serialized, copied, equality/hash, representation or conversion
    state.
    """

    utr: InitVar[str]
    tax_year: str
    scenario: str | None = _SCENARIO_OMITTED
    scenario_present: bool = field(init=False, default=False)

    def __post_init__(self, utr: str) -> None:
        _require_ascii_utr(utr)
        tax_year = _require_tax_year(self.tax_year)
        object.__setattr__(self, "tax_year", tax_year)
        if self.scenario is _SCENARIO_OMITTED:
            object.__setattr__(self, "scenario", None)
            object.__setattr__(self, "scenario_present", False)
        else:
            scenario = _require_scenario(self.scenario)
            object.__setattr__(self, "scenario", scenario)
            object.__setattr__(self, "scenario_present", True)

    def __repr__(self) -> str:
        return (
            "CreateAnnualIncomeSummaryRequestIntent("
            f"tax_year={self.tax_year!r}, scenario={self.scenario!r}, "
            f"scenario_present={self.scenario_present!r})"
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


def build_create_annual_income_summary_request(
    *,
    utr: str,
    tax_year: str,
    scenario: object = _SCENARIO_OMITTED,
) -> CreateAnnualIncomeSummaryRequestIntent:
    """Build a frozen, UTR-free request intent.

    This is a thin, keyword-only convenience over the single validated
    construction boundary: the raw UTR is validated as exactly ten ASCII digits
    and discarded, and the optional ``scenario`` is retained. Omitting
    ``scenario`` (the default) records an absent scenario; passing an explicit
    ``None`` (JSON null) or any malformed value fails closed.
    """
    if scenario is _SCENARIO_OMITTED:
        return CreateAnnualIncomeSummaryRequestIntent(utr=utr, tax_year=tax_year)
    return CreateAnnualIncomeSummaryRequestIntent(
        utr=utr, tax_year=tax_year, scenario=_require_scenario(scenario)
    )


# ── Observations ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class AnnualIncomeEmploymentObservation:
    """Validated facts from one ``employments`` array item."""

    employer_paye_reference: str
    pay_from_employment: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _require_string_value(self.employer_paye_reference, "employerPayeReference")
        _parse_number(self.pay_from_employment, "payFromEmployment")
        _require_unknown_names(self.unknown_names, "employment item", _EMPLOYMENT_NAMES)

    def __repr__(self) -> str:
        return "AnnualIncomeEmploymentObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class AnnualIncomePensionsBenefitsObservation:
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
        _require_unknown_names(self.unknown_names, "benefits object", _BENEFITS_NAMES)

    def __repr__(self) -> str:
        return "AnnualIncomePensionsBenefitsObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class AnnualIncomeSummaryTestDataObservation:
    """Validated facts from a documented HTTP 201 create response."""

    employments: tuple[AnnualIncomeEmploymentObservation, ...]
    pensions_benefits: AnnualIncomePensionsBenefitsObservation
    unknown_names: frozenset[str] = frozenset()
    completeness: str = HMRC_PAYE_TEST_SUPPORT_COMPLETENESS

    def __post_init__(self) -> None:
        if type(self.employments) is not tuple:
            raise _fail("employments must be an exact built-in tuple")
        if len(self.employments) > _RESERVED_MAX_EMPLOYMENTS:
            raise _fail("employments exceeds the reserved item bound")
        for item in self.employments:
            if type(item) is not AnnualIncomeEmploymentObservation:
                raise _fail("employments must contain exact employment observations")
        if type(self.pensions_benefits) is not AnnualIncomePensionsBenefitsObservation:
            raise _fail(
                "pensions_benefits must be an exact AnnualIncomePensionsBenefitsObservation"
            )
        if type(self.completeness) is not str or self.completeness != HMRC_PAYE_TEST_SUPPORT_COMPLETENESS:
            raise _fail("completeness must be the exact documented UNVERIFIED value")
        _require_unknown_names(
            self.unknown_names, "annual-summary observation", _TOP_LEVEL_NAMES
        )

    def __repr__(self) -> str:
        return "AnnualIncomeSummaryTestDataObservation([REDACTED])"


# ── Response observation ─────────────────────────────────────────────────────


def _parse_employment_item(item: object) -> AnnualIncomeEmploymentObservation:
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

    return AnnualIncomeEmploymentObservation(
        employer_paye_reference=employer_paye_reference,
        pay_from_employment=pay_from_employment,
        unknown_names=unknown_names,
    )


def _parse_benefits(value: object) -> AnnualIncomePensionsBenefitsObservation:
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

    return AnnualIncomePensionsBenefitsObservation(
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


def _parse_annual_summary(payload: dict) -> AnnualIncomeSummaryTestDataObservation:
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

    return AnnualIncomeSummaryTestDataObservation(
        employments=employments,
        pensions_benefits=benefits,
        unknown_names=unknown_names,
        completeness=HMRC_PAYE_TEST_SUPPORT_COMPLETENESS,
    )


def _require_request_intent(request: object) -> None:
    if type(request) is not CreateAnnualIncomeSummaryRequestIntent:
        raise _fail("request must be an exact CreateAnnualIncomeSummaryRequestIntent")


def observe_create_annual_income_summary_response(
    request: CreateAnnualIncomeSummaryRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: object,
) -> AnnualIncomeSummaryTestDataObservation:
    """Observe an already-retrieved response without any transport.

    Only the documented HTTP 201 success shape is accepted. Every non-201 status
    fails closed as unclassified: its arbitrary body is never parsed, echoed,
    retained, classified or turned into a no-data/zero/success record.
    """
    _require_request_intent(request)
    if type(status_code) is not int or isinstance(status_code, bool):
        raise _fail("status_code must be an exact built-in integer")

    if status_code == HMRC_PAYE_TEST_SUPPORT_SUCCESS_STATUS:
        if type(content_type) is not str:
            raise _fail("content_type must be an exact built-in string")
        if content_type != HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE:
            raise _fail("HTTP 201 requires exact application/json")
        return _parse_annual_summary(_require_object(payload, "response payload"))

    raise _fail("undocumented HTTP status is not accepted")
