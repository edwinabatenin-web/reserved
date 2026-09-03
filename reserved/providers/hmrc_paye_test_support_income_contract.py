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
validated and immediately discarded; a fresh opaque correlation identity, the
tax year, scenario presence/value and fixed operation descriptors are retained
in a canonical UTR-free binding. The raw response payload is never retained and no
rendered URL/path, credential, authorization header, token or sendable
header/body is exposed anywhere.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata
import weakref
from dataclasses import dataclass, field
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
_REQUEST_BINDING_LENGTH = 14
_OPAQUE_TOKEN_RE = re.compile(r"[0-9a-f]{64}")
_INTEGRITY_RE = re.compile(r"[0-9a-f]{64}")

# Process-local coherence records. This registry is deliberately not provider
# authenticity, durable provenance, authorisation, attestation or replay
# prevention. Code with arbitrary module-internal access is trusted; Python
# module privacy is not a security boundary.
_OBSERVATION_ISSUANCE: dict[
    int, tuple[weakref.ReferenceType[object], tuple[str, ...], str]
] = {}


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


class CreateAnnualIncomeSummaryRequestIntent:
    """Frozen, UTR-free intent for the documented annual-summary create.

    The construction boundary accepts ``utr``, ``tax_year`` and an optional
    ``scenario``. The raw UTR is validated as exactly ten ASCII digits and
    immediately discarded. A fresh opaque correlation identity, the validated
    tax year, scenario presence/value and fixed operation facts are retained in
    one canonical binding. Omitting ``scenario`` (via the private sentinel
    default) records absence; an explicit ``None`` (JSON null) fails closed. The
    intent is not, does not inherit from, and does not convert by default into a
    generic sendable request, and it exposes no rendered URL/path, credential,
    authorization header, token, header map, body or transport. The raw UTR is
    never present in that binding, so it cannot leak through ordinary, private,
    name-mangled, serialized, copied, equality/hash, representation or conversion
    state.
    """

    __slots__ = ("__binding",)

    def __init__(self, *, utr: str, tax_year: str,
                 scenario: object = _SCENARIO_OMITTED) -> None:
        _require_ascii_utr(utr)
        validated_year = _require_tax_year(tax_year)
        if scenario is _SCENARIO_OMITTED:
            present, validated_scenario = False, None
        else:
            present, validated_scenario = True, _require_scenario(scenario)
        object.__setattr__(
            self, "_CreateAnnualIncomeSummaryRequestIntent__binding",
            _canonical_request_binding(
                secrets.token_hex(32), validated_year, present, validated_scenario
            ),
        )

    @property
    def tax_year(self) -> str:
        return _request_binding_for(self)[1]

    @property
    def scenario_present(self) -> bool:
        return _request_binding_for(self)[2] == "present"

    @property
    def scenario(self) -> str | None:
        value = _request_binding_for(self)[3]
        return None if value == "<omitted>" else value

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("CreateAnnualIncomeSummaryRequestIntent is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("CreateAnnualIncomeSummaryRequestIntent is immutable")

    def __repr__(self) -> str:
        _request_binding_for(self)
        return "CreateAnnualIncomeSummaryRequestIntent([REDACTED])"

    def __eq__(self, other: object) -> bool:
        binding = _request_binding_for(self)
        if type(other) is not CreateAnnualIncomeSummaryRequestIntent:
            return NotImplemented
        return binding == _request_binding_for(other)

    def __hash__(self) -> int:
        return hash(_request_binding_for(self))

    def __copy__(self):
        _request_binding_for(self)
        return self

    def __deepcopy__(self, memo: dict):
        _request_binding_for(self)
        return self

    def __reduce__(self):
        return (_restore_request_intent, (_request_binding_for(self),))


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


def _binding_from_values(
    token: str, tax_year: str, scenario_present: bool, scenario: str | None
) -> tuple[str, ...]:
    return (
        token,
        tax_year,
        "present" if scenario_present else "omitted",
        scenario if scenario_present else "<omitted>",
        HMRC_PAYE_TEST_SUPPORT_OPERATION_ID,
        HMRC_PAYE_TEST_SUPPORT_HTTP_METHOD,
        HMRC_PAYE_TEST_SUPPORT_SANDBOX_ORIGIN,
        HMRC_PAYE_TEST_SUPPORT_PATH_TEMPLATE,
        HMRC_PAYE_TEST_SUPPORT_API,
        HMRC_PAYE_TEST_SUPPORT_API_VERSION,
        HMRC_PAYE_TEST_SUPPORT_ACCEPT,
        HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE,
        HMRC_PAYE_TEST_SUPPORT_OAUTH_GRANT_TYPE,
        "scopes:<empty>",
    )


def _canonical_request_binding(
    token: str, tax_year: str, scenario_present: bool, scenario: str | None
) -> tuple[str, ...]:
    return _binding_from_values(token, tax_year, scenario_present, scenario)


def _validate_request_binding(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) != _REQUEST_BINDING_LENGTH:
        raise _fail("request binding has invalid shape")
    if any(type(item) is not str for item in value):
        raise _fail("request binding values must be exact built-in strings")
    token, tax_year, presence, scenario = value[:4]
    if _OPAQUE_TOKEN_RE.fullmatch(token) is None:
        raise _fail("request correlation identity is malformed")
    _require_tax_year(tax_year)
    if presence == "omitted" and scenario == "<omitted>":
        present, scenario_value = False, None
    elif presence == "present":
        present, scenario_value = True, _require_scenario(scenario)
    else:
        raise _fail("request scenario state is malformed")
    if value != _binding_from_values(token, tax_year, present, scenario_value):
        raise _fail("request binding is not canonical")
    return value


def _request_binding_for(request: object) -> tuple[str, ...]:
    if type(request) is not CreateAnnualIncomeSummaryRequestIntent:
        raise _fail("request must be an exact CreateAnnualIncomeSummaryRequestIntent")
    try:
        binding = object.__getattribute__(
            request, "_CreateAnnualIncomeSummaryRequestIntent__binding"
        )
    except AttributeError:
        raise _fail("request binding is missing") from None
    return _validate_request_binding(binding)


def _restore_request_intent(
    binding: tuple[str, ...]
) -> CreateAnnualIncomeSummaryRequestIntent:
    canonical = _validate_request_binding(binding)
    request = object.__new__(CreateAnnualIncomeSummaryRequestIntent)
    object.__setattr__(
        request, "_CreateAnnualIncomeSummaryRequestIntent__binding", canonical
    )
    return request


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


@dataclass(frozen=True, repr=False, eq=False)
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
        _employment_protocol_state(self)
        return "AnnualIncomeEmploymentObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        state = _employment_protocol_state(self)
        if type(other) is not AnnualIncomeEmploymentObservation:
            return False
        other_state = _employment_protocol_state(other)
        return state == other_state

    def __hash__(self) -> int:
        return hash(_employment_protocol_state(self))

    def __copy__(self):
        _employment_protocol_state(self)
        return self

    def __deepcopy__(self, memo: dict):
        _employment_protocol_state(self)
        return self

    def __reduce__(self):
        return (_restore_employment, _employment_protocol_state(self))


@dataclass(frozen=True, repr=False, eq=False)
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
        for name in present:
            if type(name) is not str or name not in _BENEFITS_NAMES:
                raise _fail("benefits present_fields contains an invalid name")
        for name in absent:
            if type(name) is not str or name not in _BENEFITS_NAMES:
                raise _fail("benefits absent_fields contains an invalid name")
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
        _benefits_protocol_state(self)
        return "AnnualIncomePensionsBenefitsObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        state = _benefits_protocol_state(self)
        if type(other) is not AnnualIncomePensionsBenefitsObservation:
            return False
        other_state = _benefits_protocol_state(other)
        return state == other_state

    def __hash__(self) -> int:
        return hash(_benefits_protocol_state(self))

    def __copy__(self):
        _benefits_protocol_state(self)
        return self

    def __deepcopy__(self, memo: dict):
        _benefits_protocol_state(self)
        return self

    def __reduce__(self):
        return (_restore_benefits, _benefits_protocol_state(self))


@dataclass(frozen=True, repr=False, init=False, eq=False)
class AnnualIncomeSummaryTestDataObservation:
    """Validated facts from a documented HTTP 201 create response."""

    request: CreateAnnualIncomeSummaryRequestIntent = field(init=False, repr=False)
    _request_binding: tuple[str, ...] = field(init=False, repr=False)
    _source_binding: tuple[str, ...] = field(init=False, repr=False)
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)
    status_code: int = field(init=False)
    employments: tuple[AnnualIncomeEmploymentObservation, ...] = field(init=False)
    pensions_benefits: AnnualIncomePensionsBenefitsObservation = field(init=False)
    unknown_names: frozenset[str] = field(init=False)
    completeness: str = field(init=False)
    _observation_integrity: str = field(init=False, repr=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "AnnualIncomeSummaryTestDataObservation is observer-constructed only"
        )

    def __repr__(self) -> str:
        _observation_state(self)
        return "AnnualIncomeSummaryTestDataObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        state = _observation_state(self)
        if type(other) is not AnnualIncomeSummaryTestDataObservation:
            return NotImplemented
        return state == _observation_state(other)

    def __hash__(self) -> int:
        return hash(_observation_state(self))

    def __copy__(self):
        _observation_state(self)
        return self

    def __deepcopy__(self, memo: dict):
        _observation_state(self)
        return self

    def __reduce__(self):
        state = _observation_state(self)
        return (_restore_observation, (state[0],) + state[7:-1])


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

    # Internal parse carrier only; it is completed, issued and validated by
    # ``_new_observation`` before it can cross the public observer boundary.
    parsed = object.__new__(AnnualIncomeSummaryTestDataObservation)
    object.__setattr__(parsed, "employments", employments)
    object.__setattr__(parsed, "pensions_benefits", benefits)
    object.__setattr__(parsed, "unknown_names", unknown_names)
    return parsed


_EMPLOYMENT_STATE = frozenset({
    "employer_paye_reference", "pay_from_employment", "unknown_names",
})
_BENEFITS_STATE = frozenset({
    "other_pensions_and_retirement_annuities", "incapacity_benefit",
    "jobseekers_allowance", "seiss_net_paid", "present_fields",
    "absent_fields", "unknown_names",
})
_OBSERVATION_STATE = frozenset({
    "request", "_request_binding", "_source_binding", "tax_year", "scenario",
    "scenario_present", "status_code", "employments", "pensions_benefits",
    "unknown_names", "completeness", "_observation_integrity",
})


def _exact_state(value: object, expected_type: type, names: frozenset[str]) -> dict:
    if type(value) is not expected_type:
        raise _fail("observation type is not exact")
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or len(state) != len(names):
        raise _fail("observation state is not exact")
    for name in state:
        if type(name) is not str:
            raise _fail("observation state names must be exact built-in strings")
    if frozenset(state) != names:
        raise _fail("observation state is not exact")
    return state


def _validate_employment(value: object) -> AnnualIncomeEmploymentObservation:
    state = _exact_state(value, AnnualIncomeEmploymentObservation, _EMPLOYMENT_STATE)
    _require_string_value(state["employer_paye_reference"], "employerPayeReference")
    _parse_number(state["pay_from_employment"], "payFromEmployment")
    _require_unknown_names(state["unknown_names"], "employment item", _EMPLOYMENT_NAMES)
    return value


def _validate_benefits(value: object) -> AnnualIncomePensionsBenefitsObservation:
    state = _exact_state(value, AnnualIncomePensionsBenefitsObservation, _BENEFITS_STATE)
    present = state["present_fields"]
    absent = state["absent_fields"]
    if type(present) is not frozenset or type(absent) is not frozenset:
        raise _fail("benefits retained field sets must be exact frozensets")
    for name in present:
        if type(name) is not str or name not in _BENEFITS_NAMES:
            raise _fail("benefits retained present name is invalid")
    for name in absent:
        if type(name) is not str or name not in _BENEFITS_NAMES:
            raise _fail("benefits retained absent name is invalid")
    if present & absent or present | absent != _BENEFITS_NAMES:
        raise _fail("benefits retained field presence is incoherent")
    for name, attribute in (
        ("otherPensionsAndRetirementAnnuities", "other_pensions_and_retirement_annuities"),
        ("incapacityBenefit", "incapacity_benefit"),
        ("jobseekersAllowance", "jobseekers_allowance"),
        ("seissNetPaid", "seiss_net_paid"),
    ):
        item = state[attribute]
        if name in present:
            if item is None:
                raise _fail("present benefit value is missing")
            _parse_number(item, name)
        elif item is not None:
            raise _fail("absent benefit value is retained")
    _require_unknown_names(state["unknown_names"], "benefits object", _BENEFITS_NAMES)
    return value


def _employment_protocol_state(value: object) -> tuple[object, ...]:
    state = object.__getattribute__(_validate_employment(value), "__dict__")
    return (
        state["employer_paye_reference"], state["pay_from_employment"],
        state["unknown_names"],
    )


def _benefits_protocol_state(value: object) -> tuple[object, ...]:
    state = object.__getattribute__(_validate_benefits(value), "__dict__")
    return (
        state["other_pensions_and_retirement_annuities"],
        state["incapacity_benefit"], state["jobseekers_allowance"],
        state["seiss_net_paid"], state["present_fields"],
        state["absent_fields"], state["unknown_names"],
    )


def _restore_employment(employer_paye_reference, pay_from_employment, unknown_names):
    shell = object.__new__(AnnualIncomeEmploymentObservation)
    object.__setattr__(shell, "employer_paye_reference", employer_paye_reference)
    object.__setattr__(shell, "pay_from_employment", pay_from_employment)
    object.__setattr__(shell, "unknown_names", unknown_names)
    _validate_employment(shell)
    return AnnualIncomeEmploymentObservation(
        employer_paye_reference, pay_from_employment, unknown_names
    )


def _restore_benefits(
    other_pensions_and_retirement_annuities, incapacity_benefit,
    jobseekers_allowance, seiss_net_paid, present_fields, absent_fields,
    unknown_names,
):
    shell = object.__new__(AnnualIncomePensionsBenefitsObservation)
    for name, item in (
        ("other_pensions_and_retirement_annuities", other_pensions_and_retirement_annuities),
        ("incapacity_benefit", incapacity_benefit),
        ("jobseekers_allowance", jobseekers_allowance),
        ("seiss_net_paid", seiss_net_paid),
        ("present_fields", present_fields), ("absent_fields", absent_fields),
        ("unknown_names", unknown_names),
    ):
        object.__setattr__(shell, name, item)
    _validate_benefits(shell)
    return AnnualIncomePensionsBenefitsObservation(
        other_pensions_and_retirement_annuities, incapacity_benefit,
        jobseekers_allowance, seiss_net_paid, present_fields, absent_fields,
        unknown_names,
    )


def _number_integrity_value(value: int | Decimal) -> list[object]:
    if type(value) is int:
        return ["int", str(value)]
    _require_decimal_number(value, "retained number")
    parts = value.as_tuple()
    return ["decimal", parts.sign, list(parts.digits), parts.exponent]


def _employment_integrity_value(value: AnnualIncomeEmploymentObservation) -> list[object]:
    state = object.__getattribute__(_validate_employment(value), "__dict__")
    return [state["employer_paye_reference"],
            _number_integrity_value(state["pay_from_employment"]),
            sorted(state["unknown_names"])]


def _benefits_integrity_value(value: AnnualIncomePensionsBenefitsObservation) -> list[object]:
    state = object.__getattribute__(_validate_benefits(value), "__dict__")
    values = []
    for attribute in (
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "jobseekers_allowance", "seiss_net_paid",
    ):
        item = state[attribute]
        values.append(None if item is None else _number_integrity_value(item))
    return values + [sorted(state["present_fields"]), sorted(state["absent_fields"]),
                     sorted(state["unknown_names"])]


def _observation_digest(canonical: object) -> str:
    encoded = json.dumps(
        canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_observation(state: dict, binding: tuple[str, ...]) -> list[object]:
    return [
        "success", list(binding), state["tax_year"], state["scenario_present"],
        state["scenario"], state["status_code"],
        [_employment_integrity_value(item) for item in state["employments"]],
        _benefits_integrity_value(state["pensions_benefits"]),
        sorted(state["unknown_names"]), state["completeness"],
    ]


def _register_observation(value: object, binding: tuple[str, ...], integrity: str) -> None:
    identity = id(value)
    def discard(reference: weakref.ReferenceType[object]) -> None:
        current = _OBSERVATION_ISSUANCE.get(identity)
        if current is not None and current[0] is reference:
            _OBSERVATION_ISSUANCE.pop(identity, None)
    reference = weakref.ref(value, discard)
    _OBSERVATION_ISSUANCE[identity] = (reference, binding, integrity)


def _observation_state(value: object) -> tuple[object, ...]:
    state = _exact_state(value, AnnualIncomeSummaryTestDataObservation, _OBSERVATION_STATE)
    request_binding = _request_binding_for(state["request"])
    retained = _validate_request_binding(state["_request_binding"])
    source = _validate_request_binding(state["_source_binding"])
    if request_binding != retained or retained != source:
        raise _fail("observation request/source binding is incoherent")
    expected_present = retained[2] == "present"
    expected_scenario = None if retained[3] == "<omitted>" else retained[3]
    scenario = state["scenario"]
    scenario_invalid = (
        scenario is not None if expected_scenario is None
        else type(scenario) is not str or scenario != expected_scenario
    )
    if (type(state["tax_year"]) is not str or state["tax_year"] != retained[1]
            or type(state["scenario_present"]) is not bool
            or state["scenario_present"] is not expected_present
            or scenario_invalid):
        raise _fail("observation request context is incoherent")
    if type(state["status_code"]) is not int or state["status_code"] != 201:
        raise _fail("observation status is invalid")
    employments = state["employments"]
    if type(employments) is not tuple or len(employments) > _RESERVED_MAX_EMPLOYMENTS:
        raise _fail("retained employments are invalid")
    for item in employments:
        _validate_employment(item)
    _validate_benefits(state["pensions_benefits"])
    _require_unknown_names(state["unknown_names"], "annual-summary observation", _TOP_LEVEL_NAMES)
    if type(state["completeness"]) is not str or state["completeness"] != HMRC_PAYE_TEST_SUPPORT_COMPLETENESS:
        raise _fail("completeness is invalid")
    expected = _observation_digest(_canonical_observation(state, retained))
    integrity = state["_observation_integrity"]
    if (type(integrity) is not str or _INTEGRITY_RE.fullmatch(integrity) is None
            or not secrets.compare_digest(integrity, expected)):
        raise _fail("observation integrity is incoherent")
    issued = _OBSERVATION_ISSUANCE.get(id(value))
    if (issued is None or issued[0]() is not value or issued[1] != retained
            or not secrets.compare_digest(issued[2], integrity)):
        raise _fail("observation provenance is unsupported")
    return (
        retained, state["_request_binding"], state["_source_binding"],
        state["tax_year"], state["scenario"], state["scenario_present"],
        state["status_code"], employments, state["pensions_benefits"],
        state["unknown_names"], state["completeness"], integrity,
    )


def _new_observation(
    request: CreateAnnualIncomeSummaryRequestIntent, status_code: int,
    parsed: AnnualIncomeSummaryTestDataObservation,
) -> AnnualIncomeSummaryTestDataObservation:
    binding = _request_binding_for(request)
    parsed_state = object.__getattribute__(parsed, "__dict__")
    value = object.__new__(AnnualIncomeSummaryTestDataObservation)
    fields = (
        ("request", request), ("_request_binding", binding), ("_source_binding", binding),
        ("tax_year", binding[1]), ("scenario", None if binding[3] == "<omitted>" else binding[3]),
        ("scenario_present", binding[2] == "present"), ("status_code", status_code),
        ("employments", parsed_state["employments"]),
        ("pensions_benefits", parsed_state["pensions_benefits"]),
        ("unknown_names", parsed_state["unknown_names"]),
        ("completeness", HMRC_PAYE_TEST_SUPPORT_COMPLETENESS),
    )
    for name, item in fields:
        object.__setattr__(value, name, item)
    state = object.__getattribute__(value, "__dict__")
    integrity = _observation_digest(_canonical_observation(state, binding))
    object.__setattr__(value, "_observation_integrity", integrity)
    _register_observation(value, binding, integrity)
    _observation_state(value)
    return value


def _restore_observation(binding, employments, benefits, unknown, completeness):
    # Structural preflight covers every reconstruction argument before any
    # canonical equality, set algebra, sorting, digesting or construction.
    if (type(binding) is not tuple or len(binding) != _REQUEST_BINDING_LENGTH
            or any(type(item) is not str for item in binding)):
        raise _fail("serialized observation request binding is invalid")
    if type(completeness) is not str:
        raise _fail("serialized observation is invalid")
    if type(employments) is not tuple or len(employments) > _RESERVED_MAX_EMPLOYMENTS:
        raise _fail("serialized observation employments are invalid")
    for item in employments:
        item_state = _exact_state(
            item, AnnualIncomeEmploymentObservation, _EMPLOYMENT_STATE
        )
        if (type(item_state["employer_paye_reference"]) is not str
                or type(item_state["pay_from_employment"]) not in (int, Decimal)):
            raise _fail("serialized employment state is invalid")
        names = item_state["unknown_names"]
        if (type(names) is not frozenset
                or any(type(name) is not str for name in names)):
            raise _fail("serialized employment unknown names are invalid")
    benefit_state = _exact_state(
        benefits, AnnualIncomePensionsBenefitsObservation, _BENEFITS_STATE
    )
    for attribute in (
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "jobseekers_allowance", "seiss_net_paid",
    ):
        item = benefit_state[attribute]
        if item is not None and type(item) not in (int, Decimal):
            raise _fail("serialized benefit value is invalid")
    for attribute in ("present_fields", "absent_fields", "unknown_names"):
        names = benefit_state[attribute]
        if (type(names) is not frozenset
                or any(type(name) is not str for name in names)):
            raise _fail("serialized benefit name state is invalid")
    if (type(unknown) is not frozenset
            or any(type(name) is not str for name in unknown)):
        raise _fail("serialized observation unknown names are invalid")

    canonical_binding = _validate_request_binding(binding)
    for item in employments:
        _validate_employment(item)
    _validate_benefits(benefits)
    _require_unknown_names(unknown, "annual-summary observation", _TOP_LEVEL_NAMES)
    if completeness != HMRC_PAYE_TEST_SUPPORT_COMPLETENESS:
        raise _fail("serialized observation is invalid")
    shell = object.__new__(AnnualIncomeSummaryTestDataObservation)
    object.__setattr__(shell, "employments", employments)
    object.__setattr__(shell, "pensions_benefits", benefits)
    object.__setattr__(shell, "unknown_names", unknown)
    return _new_observation(_restore_request_intent(canonical_binding), 201, shell)


def validate_annual_income_summary_observation(
    observation: object,
) -> AnnualIncomeSummaryTestDataObservation:
    """Validate exact state, issuance and complete producing-request binding."""
    _observation_state(observation)
    return observation


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
    _request_binding_for(request)
    if type(status_code) is not int or isinstance(status_code, bool):
        raise _fail("status_code must be an exact built-in integer")

    if status_code == HMRC_PAYE_TEST_SUPPORT_SUCCESS_STATUS:
        if type(content_type) is not str:
            raise _fail("content_type must be an exact built-in string")
        if content_type != HMRC_PAYE_TEST_SUPPORT_JSON_CONTENT_TYPE:
            raise _fail("HTTP 201 requires exact application/json")
        parsed = _parse_annual_summary(_require_object(payload, "response payload"))
        return _new_observation(request, status_code, parsed)

    raise _fail("undocumented HTTP status is not accepted")
