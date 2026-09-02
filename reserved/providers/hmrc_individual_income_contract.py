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


def _compute_redacted_path(tax_year: str) -> str:
    """Compute the UTR-free redacted path for a validated tax year."""
    return (
        HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE.replace("{utr}", UTR_REDACTION_MARKER)
        .replace("{taxYear}", tax_year)
    )


@dataclass(frozen=True, repr=False, eq=False)
class IndividualIncomeRequestIntent:
    """Frozen, UTR-free intent for the documented annual-summary read.

    The only construction boundary accepts ``utr`` and ``tax_year``; the raw UTR
    is validated as exactly ten ASCII digits and immediately discarded. Every
    other field is derived internally and cannot be supplied or replaced through
    the constructor or ``dataclasses.replace``. The intent is not, does not
    inherit from, and does not convert by default into a generic sendable
    request. The raw UTR is never present in any field, so it cannot leak through
    ordinary, private, name-mangled, copied, equality/hash, representation or
    conversion state. Pickle reconstruction carries only the validated,
    canonical UTR-free retained state.
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
        object.__setattr__(self, "redacted_path", _compute_redacted_path(tax_year))

    def __repr__(self) -> str:
        # Never render retained values.  This remains non-value-bearing even if
        # hostile code has bypassed the frozen boundary with object.__setattr__.
        return "IndividualIncomeRequestIntent([REDACTED])"

    def __eq__(self, other: object) -> bool:
        _require_request_intent(self)
        if type(other) is not IndividualIncomeRequestIntent:
            return NotImplemented
        _require_request_intent(other)
        return _request_binding_for(self) == _request_binding_for(other)

    def __hash__(self) -> int:
        _require_request_intent(self)
        return hash(_request_binding_for(self))

    def __copy__(self) -> "IndividualIncomeRequestIntent":
        # Deeply immutable: sharing the instance is a fully coherent copy, but
        # only after validating every retained field.  Forged or missing state
        # must not be preserved merely because the object is frozen.
        _require_request_intent(self)
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualIncomeRequestIntent":
        _require_request_intent(self)
        return self

    def __reduce__(self):
        # Validate before emitting a reconstruction recipe.  The recipe
        # contains only the canonical UTR-free state; no raw UTR exists to
        # serialize or log.
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


def build_individual_income_request(*, utr: str, tax_year: str) -> IndividualIncomeRequestIntent:
    """Build a frozen, UTR-free request intent.

    This is a thin, keyword-only convenience over the single validated
    construction boundary: the raw UTR is validated as exactly ten ASCII digits
    and discarded, and every derived field is computed internally.
    """
    return IndividualIncomeRequestIntent(utr=utr, tax_year=tax_year)


_REQUEST_INTENT_STATE_ORDER = (
    "tax_year",
    "method",
    "sandbox_origin",
    "path_template",
    "accept",
    "scope",
    "redacted_path",
)
_REQUEST_INTENT_STATE_NAMES = frozenset(_REQUEST_INTENT_STATE_ORDER)


# ── Observations ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, repr=False)
class _ObservationRequestContext:
    """Private source context carried through safe replacement/serialization.

    This extra immutable source record is deliberately separate from the three
    convenient retained fields on a response observation. Validation detects
    incomplete or incoherent low-level mutation, including coordinated changes
    to ``request``, ``_request_binding`` and ``tax_year`` while this source
    context remains unchanged.

    This value-object boundary does not claim to resist arbitrary trusted-code
    memory rewriting. Code able to use ``object.__setattr__`` can replace every
    mutually coherent private and public field from another valid peer. Such
    code execution must be prevented by process and code-trust controls rather
    than represented as an invariant this Python object can enforce.
    """

    request: IndividualIncomeRequestIntent
    binding: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_observation_request_context(self)


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

    def __copy__(self) -> "EmploymentItemObservation":
        _require_employment_observation(self)
        return self

    def __deepcopy__(self, memo: dict) -> "EmploymentItemObservation":
        _require_employment_observation(self)
        return self

    def __reduce__(self):
        _require_employment_observation(self)
        return (EmploymentItemObservation, (
            self.employer_paye_reference,
            self.pay_from_employment,
            self.unknown_names,
        ))


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

    def __copy__(self) -> "PensionsBenefitsObservation":
        _require_benefits_observation(self)
        return self

    def __deepcopy__(self, memo: dict) -> "PensionsBenefitsObservation":
        _require_benefits_observation(self)
        return self

    def __reduce__(self):
        _require_benefits_observation(self)
        return (PensionsBenefitsObservation, (
            self.other_pensions_and_retirement_annuities,
            self.incapacity_benefit,
            self.jobseekers_allowance,
            self.seiss_net_paid,
            self.present_fields,
            self.absent_fields,
            self.unknown_names,
        ))


@dataclass(frozen=True, repr=False, init=False, eq=False)
class IndividualIncomeAnnualSummaryObservation:
    """Validated facts from a documented HTTP 200 annual-summary response.

    The observer's private factory retains the exact validated, UTR-free
    request context and an immutable snapshot of its canonical state.
    Every field is non-init.  Public construction and ``dataclasses.replace``
    are intentionally unavailable because standard dataclass replacement
    cannot carry hidden source provenance while preventing callers from
    substituting it.  ``tax_year`` is always derived by the private factory.
    """

    employments: tuple[EmploymentItemObservation, ...] = field(init=False)
    pensions_benefits: PensionsBenefitsObservation = field(init=False)
    unknown_names: frozenset[str] = field(init=False)
    completeness: str = field(init=False)
    _source_context: "_ObservationRequestContext" = field(init=False, repr=False)
    request: IndividualIncomeRequestIntent = field(init=False, repr=False)
    _request_binding: tuple[str, ...] = field(init=False, repr=False)
    tax_year: str = field(init=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "IndividualIncomeAnnualSummaryObservation is observer-constructed only"
        )

    def __repr__(self) -> str:
        return "IndividualIncomeAnnualSummaryObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        _require_annual_summary_observation(self)
        if type(other) is not IndividualIncomeAnnualSummaryObservation:
            return NotImplemented
        _require_annual_summary_observation(other)
        return (
            self.request,
            self.employments,
            self.pensions_benefits,
            self.unknown_names,
            self.completeness,
            self._request_binding,
            self.tax_year,
        ) == (
            other.request,
            other.employments,
            other.pensions_benefits,
            other.unknown_names,
            other.completeness,
            other._request_binding,
            other.tax_year,
        )

    def __hash__(self) -> int:
        _require_annual_summary_observation(self)
        return hash((
            self.request,
            self.employments,
            self.pensions_benefits,
            self.unknown_names,
            self.completeness,
            self._request_binding,
            self.tax_year,
        ))

    def __copy__(self) -> "IndividualIncomeAnnualSummaryObservation":
        _require_annual_summary_observation(self)
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualIncomeAnnualSummaryObservation":
        _require_annual_summary_observation(self)
        return self

    def __reduce__(self):
        _require_annual_summary_observation(self)
        return (
            _restore_annual_summary_observation,
            (
                self._source_context.binding,
                self.employments,
                self.pensions_benefits,
                self.unknown_names,
                self.completeness,
            ),
        )


@dataclass(frozen=True, repr=False, init=False, eq=False)
class IndividualIncomeErrorObservation:
    """Validated facts from a documented HTTP 400/401/404 error response.

    The error ``message`` is validated as a string and then discarded; only the
    documented ``code`` and ``status_code`` are retained. The observer's
    private factory also retains validated UTR-free request context. Every
    field is non-init, so public construction and dataclass replacement are
    unavailable. Valid UTR-free pickle remains supported.
    """

    status_code: int = field(init=False)
    code: str = field(init=False)
    unknown_names: frozenset[str] = field(init=False)
    _source_context: "_ObservationRequestContext" = field(init=False, repr=False)
    request: IndividualIncomeRequestIntent = field(init=False, repr=False)
    _request_binding: tuple[str, ...] = field(init=False, repr=False)
    tax_year: str = field(init=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("IndividualIncomeErrorObservation is observer-constructed only")

    def __repr__(self) -> str:
        return "IndividualIncomeErrorObservation([REDACTED])"

    def __eq__(self, other: object) -> bool:
        _require_error_observation(self)
        if type(other) is not IndividualIncomeErrorObservation:
            return NotImplemented
        _require_error_observation(other)
        return (
            self.request,
            self.status_code,
            self.code,
            self.unknown_names,
            self._request_binding,
            self.tax_year,
        ) == (
            other.request,
            other.status_code,
            other.code,
            other.unknown_names,
            other._request_binding,
            other.tax_year,
        )

    def __hash__(self) -> int:
        _require_error_observation(self)
        return hash((
            self.request,
            self.status_code,
            self.code,
            self.unknown_names,
            self._request_binding,
            self.tax_year,
        ))

    def __copy__(self) -> "IndividualIncomeErrorObservation":
        _require_error_observation(self)
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualIncomeErrorObservation":
        _require_error_observation(self)
        return self

    def __reduce__(self):
        _require_error_observation(self)
        return (
            _restore_error_observation,
            (
                self._source_context.binding,
                self.status_code,
                self.code,
                self.unknown_names,
            ),
        )


_EMPLOYMENT_OBSERVATION_STATE_NAMES = frozenset({
    "employer_paye_reference",
    "pay_from_employment",
    "unknown_names",
})
_BENEFITS_OBSERVATION_STATE_NAMES = frozenset({
    "other_pensions_and_retirement_annuities",
    "incapacity_benefit",
    "jobseekers_allowance",
    "seiss_net_paid",
    "present_fields",
    "absent_fields",
    "unknown_names",
})
_ANNUAL_OBSERVATION_STATE_NAMES = frozenset({
    "request",
    "employments",
    "pensions_benefits",
    "unknown_names",
    "completeness",
    "_source_context",
    "_request_binding",
    "tax_year",
})
_ERROR_OBSERVATION_STATE_NAMES = frozenset({
    "request",
    "status_code",
    "code",
    "unknown_names",
    "_source_context",
    "_request_binding",
    "tax_year",
})


def _require_exact_instance_state(
    value: object,
    expected_type: type,
    expected_names: frozenset[str],
    context: str,
) -> dict:
    """Return an exact instance dictionary only when its shape is complete."""
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


def _request_binding_for(request: IndividualIncomeRequestIntent) -> tuple[str, ...]:
    """Snapshot the complete validated UTR-free canonical request state."""
    validated = _require_request_intent(request)
    state = object.__getattribute__(validated, "__dict__")
    return tuple(state[name] for name in _REQUEST_INTENT_STATE_ORDER)


def _require_request_binding(binding: object) -> tuple[str, ...]:
    """Validate a retained binding without normalising or rebuilding it."""
    if type(binding) is not tuple:
        raise _fail("observation request binding must be an exact built-in tuple")
    if len(binding) != len(_REQUEST_INTENT_STATE_ORDER):
        raise _fail("observation request binding is not the exact expected shape")
    for value in binding:
        if type(value) is not str:
            raise _fail("observation request binding values must be exact strings")
    tax_year = _require_tax_year(binding[0])
    expected = (
        tax_year,
        HMRC_INDIVIDUAL_INCOME_HTTP_METHOD,
        HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN,
        HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE,
        HMRC_INDIVIDUAL_INCOME_ACCEPT,
        HMRC_INDIVIDUAL_INCOME_SCOPE,
        _compute_redacted_path(tax_year),
    )
    if binding != expected:
        raise _fail("observation request binding is not canonical")
    return binding


def _require_observation_request_context(
    context: object,
) -> _ObservationRequestContext:
    state = _require_exact_instance_state(
        context,
        _ObservationRequestContext,
        frozenset({"request", "binding"}),
        "observation source context",
    )
    request_binding = _request_binding_for(state["request"])
    retained_binding = _require_request_binding(state["binding"])
    if request_binding != retained_binding:
        raise _fail("observation source context is not coherent")
    return context


def _restore_request_intent(
    binding: tuple[str, ...],
) -> IndividualIncomeRequestIntent:
    """Restore only validated UTR-free retained request state."""
    canonical = _require_request_binding(binding)
    request = object.__new__(IndividualIncomeRequestIntent)
    for name, value in zip(_REQUEST_INTENT_STATE_ORDER, canonical):
        object.__setattr__(request, name, value)
    return _require_request_intent(request)


def _context_from_binding(binding: tuple[str, ...]) -> _ObservationRequestContext:
    canonical = _require_request_binding(binding)
    return _ObservationRequestContext(
        request=_restore_request_intent(canonical),
        binding=canonical,
    )


def _require_employment_observation(value: object) -> EmploymentItemObservation:
    state = _require_exact_instance_state(
        value,
        EmploymentItemObservation,
        _EMPLOYMENT_OBSERVATION_STATE_NAMES,
        "employment item",
    )
    _require_string_value(state["employer_paye_reference"], "employerPayeReference")
    _parse_number(state["pay_from_employment"], "payFromEmployment")
    _require_unknown_names(state["unknown_names"], "employment item")
    return value


def _require_benefits_observation(value: object) -> PensionsBenefitsObservation:
    state = _require_exact_instance_state(
        value,
        PensionsBenefitsObservation,
        _BENEFITS_OBSERVATION_STATE_NAMES,
        "benefits object",
    )
    present = state["present_fields"]
    absent = state["absent_fields"]
    if type(present) is not frozenset:
        raise _fail("benefits present_fields must be an exact frozenset")
    if type(absent) is not frozenset:
        raise _fail("benefits absent_fields must be an exact frozenset")
    if present & absent:
        raise _fail("benefits present and absent fields must be disjoint")
    if present | absent != _BENEFITS_NAMES:
        raise _fail("benefits present and absent fields must be exhaustive")
    for name, field_name in (
        ("otherPensionsAndRetirementAnnuities", "other_pensions_and_retirement_annuities"),
        ("incapacityBenefit", "incapacity_benefit"),
        ("jobseekersAllowance", "jobseekers_allowance"),
        ("seissNetPaid", "seiss_net_paid"),
    ):
        field_value = state[field_name]
        if name in present:
            if field_value is None:
                raise _fail(f"{name} must not be None when present")
            _parse_number(field_value, name)
        elif field_value is not None:
            raise _fail(f"{name} must be None when absent")
    _require_unknown_names(state["unknown_names"], "benefits object")
    return value


def _validate_annual_summary_values(
    observation: IndividualIncomeAnnualSummaryObservation,
) -> None:
    if type(observation.employments) is not tuple:
        raise _fail("employments must be an exact built-in tuple")
    if len(observation.employments) > _RESERVED_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the reserved item bound")
    for item in observation.employments:
        _require_employment_observation(item)
    _require_benefits_observation(observation.pensions_benefits)
    if (
        type(observation.completeness) is not str
        or observation.completeness != HMRC_INDIVIDUAL_INCOME_COMPLETENESS
    ):
        raise _fail("completeness must be the exact documented UNVERIFIED value")
    _require_unknown_names(observation.unknown_names, "annual-summary observation")


def _validate_error_values(observation: IndividualIncomeErrorObservation) -> None:
    if type(observation.status_code) is not int:
        raise _fail("status_code must be an exact built-in integer")
    if observation.status_code not in HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES:
        raise _fail("status_code is not a documented error status")
    if type(observation.code) is not str:
        raise _fail("code must be an exact built-in string")
    if observation.code not in HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES[observation.status_code]:
        raise _fail("error code does not match the documented status")
    _require_unknown_names(observation.unknown_names, "error body")


def _require_annual_summary_observation(
    value: object,
) -> IndividualIncomeAnnualSummaryObservation:
    state = _require_exact_instance_state(
        value,
        IndividualIncomeAnnualSummaryObservation,
        _ANNUAL_OBSERVATION_STATE_NAMES,
        "annual-summary observation",
    )
    source_context = _require_observation_request_context(state["_source_context"])
    request_binding = _request_binding_for(state["request"])
    retained_binding = _require_request_binding(state["_request_binding"])
    if (
        state["request"] is not source_context.request
        or request_binding != retained_binding
        or retained_binding != source_context.binding
    ):
        raise _fail("request does not match the retained observation context")
    if type(state["tax_year"]) is not str or state["tax_year"] != retained_binding[0]:
        raise _fail("observation tax year is not derived from its request context")
    _validate_annual_summary_values(value)
    return value


def _require_error_observation(value: object) -> IndividualIncomeErrorObservation:
    state = _require_exact_instance_state(
        value,
        IndividualIncomeErrorObservation,
        _ERROR_OBSERVATION_STATE_NAMES,
        "error observation",
    )
    source_context = _require_observation_request_context(state["_source_context"])
    request_binding = _request_binding_for(state["request"])
    retained_binding = _require_request_binding(state["_request_binding"])
    if (
        state["request"] is not source_context.request
        or request_binding != retained_binding
        or retained_binding != source_context.binding
    ):
        raise _fail("request does not match the retained observation context")
    if type(state["tax_year"]) is not str or state["tax_year"] != retained_binding[0]:
        raise _fail("observation tax year is not derived from its request context")
    _validate_error_values(value)
    return value


def _new_annual_summary_observation(
    request: IndividualIncomeRequestIntent,
    employments: tuple[EmploymentItemObservation, ...],
    pensions_benefits: PensionsBenefitsObservation,
    unknown_names: frozenset[str],
    completeness: str,
) -> IndividualIncomeAnnualSummaryObservation:
    """Construct a success observation only for the validated parser boundary."""
    validated_request = _require_request_intent(request)
    binding = _request_binding_for(validated_request)
    context = _ObservationRequestContext(validated_request, binding)
    observation = object.__new__(IndividualIncomeAnnualSummaryObservation)
    object.__setattr__(observation, "employments", employments)
    object.__setattr__(observation, "pensions_benefits", pensions_benefits)
    object.__setattr__(observation, "unknown_names", unknown_names)
    object.__setattr__(observation, "completeness", completeness)
    object.__setattr__(observation, "_source_context", context)
    object.__setattr__(observation, "request", context.request)
    object.__setattr__(observation, "_request_binding", context.binding)
    object.__setattr__(observation, "tax_year", context.binding[0])
    return _require_annual_summary_observation(observation)


def _new_error_observation(
    request: IndividualIncomeRequestIntent,
    status_code: int,
    code: str,
    unknown_names: frozenset[str],
) -> IndividualIncomeErrorObservation:
    """Construct an error observation only for the validated parser boundary."""
    validated_request = _require_request_intent(request)
    binding = _request_binding_for(validated_request)
    context = _ObservationRequestContext(validated_request, binding)
    observation = object.__new__(IndividualIncomeErrorObservation)
    object.__setattr__(observation, "status_code", status_code)
    object.__setattr__(observation, "code", code)
    object.__setattr__(observation, "unknown_names", unknown_names)
    object.__setattr__(observation, "_source_context", context)
    object.__setattr__(observation, "request", context.request)
    object.__setattr__(observation, "_request_binding", context.binding)
    object.__setattr__(observation, "tax_year", context.binding[0])
    return _require_error_observation(observation)


def _restore_annual_summary_observation(
    binding: tuple[str, ...],
    employments: tuple[EmploymentItemObservation, ...],
    pensions_benefits: PensionsBenefitsObservation,
    unknown_names: frozenset[str],
    completeness: str,
) -> IndividualIncomeAnnualSummaryObservation:
    """Restore a validated observation without any raw request identifier."""
    context = _context_from_binding(binding)
    return _new_annual_summary_observation(
        context.request,
        employments,
        pensions_benefits,
        unknown_names,
        completeness,
    )


def _restore_error_observation(
    binding: tuple[str, ...],
    status_code: int,
    code: str,
    unknown_names: frozenset[str],
) -> IndividualIncomeErrorObservation:
    """Restore a validated error observation without raw message or UTR."""
    context = _context_from_binding(binding)
    return _new_error_observation(context.request, status_code, code, unknown_names)


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


def _parse_annual_summary(
    request: IndividualIncomeRequestIntent,
    payload: dict,
) -> IndividualIncomeAnnualSummaryObservation:
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

    return _new_annual_summary_observation(
        request,
        employments,
        benefits,
        unknown_names,
        HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    )


def _parse_error(
    request: IndividualIncomeRequestIntent,
    status_code: int,
    payload: dict,
) -> IndividualIncomeErrorObservation:
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

    return _new_error_observation(request, status_code, code, unknown_names)


def _require_request_intent(request: object) -> IndividualIncomeRequestIntent:
    """Revalidate the full exact request intent rather than its history.

    Reads only the request's own built-in ``__dict__`` slot and checks its exact
    shape, keys and derived values against the documented constants. No hostile
    comparison, hashing, representation, string, truthiness, mapping or
    iteration hook is invoked: keys are type-checked before hashing, values are
    type-checked before use, and any mismatch fails closed without echoing
    hostile data.
    """
    if type(request) is not IndividualIncomeRequestIntent:
        raise _fail("request must be an exact IndividualIncomeRequestIntent")
    state = object.__getattribute__(request, "__dict__")
    if type(state) is not dict:
        raise _fail("request internal state must be an exact built-in dict")
    if len(state) != len(_REQUEST_INTENT_STATE_NAMES):
        raise _fail("request internal state is not the exact expected shape")

    keys: set[str] = set()
    for key in state:
        if type(key) is not str:
            raise _fail("request internal state contains a non-string key")
        keys.add(key)
    if keys != _REQUEST_INTENT_STATE_NAMES:
        raise _fail("request internal state keys are not exact")

    tax_year = state["tax_year"]
    if type(tax_year) is not str:
        raise _fail("request tax_year must be an exact built-in string")
    _require_tax_year(tax_year)

    for name, expected in (
        ("method", HMRC_INDIVIDUAL_INCOME_HTTP_METHOD),
        ("sandbox_origin", HMRC_INDIVIDUAL_INCOME_SANDBOX_ORIGIN),
        ("path_template", HMRC_INDIVIDUAL_INCOME_PATH_TEMPLATE),
        ("accept", HMRC_INDIVIDUAL_INCOME_ACCEPT),
        ("scope", HMRC_INDIVIDUAL_INCOME_SCOPE),
    ):
        if type(state[name]) is not str or state[name] != expected:
            raise _fail(f"request {name} is not the exact documented value")

    redacted_path = state["redacted_path"]
    if type(redacted_path) is not str or redacted_path != _compute_redacted_path(tax_year):
        raise _fail("request redacted_path is not coherent with the tax year")

    return request


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
    validated_request = _require_request_intent(request)
    if type(status_code) is not int or isinstance(status_code, bool):
        raise _fail("status_code must be an exact built-in integer")
    if type(content_type) is not str:
        raise _fail("content_type must be an exact built-in string")

    if status_code == 200:
        if content_type != HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE:
            raise _fail("HTTP 200 requires exact application/json")
        return _parse_annual_summary(
            validated_request,
            _require_object(payload, "response payload"),
        )

    if status_code in (400, 401, 404):
        if content_type != HMRC_INDIVIDUAL_INCOME_JSON_CONTENT_TYPE:
            raise _fail("documented error statuses require exact application/json")
        return _parse_error(
            validated_request,
            status_code,
            _require_object(payload, "error payload"),
        )

    raise _fail("undocumented HTTP status is not accepted")
