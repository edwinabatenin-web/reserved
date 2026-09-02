"""Network-inert HMRC Individual Tax 1.1 literal request/response contract.

This module captures the reviewed, documented endpoint facts for::

    GET /individual-tax/sa/{utr}/annual-summary/{taxYear}

with ``Accept: application/vnd.hmrc.1.1+json`` and OAuth scope
``read:individual-tax``. It is an offline request *intent* and response
*observation* only. It owns no HTTP client, transport, credential, token,
authorization header, persistence, routing, provider-to-canonical mapping,
production origin or activation path.

Authority observed 2026-09-01. See
``docs/HMRC_INDIVIDUAL_TAX_1_1_ENDPOINT_EVIDENCE.md`` for the endpoint facts and
``docs/HMRC_INDIVIDUAL_TAX_1_1_CONTRACT_EVIDENCE.md`` for the implementation
decisions recorded for this contract. The raw UTR is validated and discarded;
the raw response payload and error ``message`` are never retained. Every
success/error observation is bound to the exact validated, UTR-free request
intent so its request-derived tax year cannot be supplied, forged or replaced
independently.

State Pension lump-sum reference ``267/LS500`` is a literal provider fact only:
this module attaches no special downstream tax or identity behaviour to it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal
from types import MappingProxyType

# --- Exact documented constants (provider facts, not Reserved inference) -----

HMRC_INDIVIDUAL_TAX_API_VERSION = "1.1"
HMRC_INDIVIDUAL_TAX_HTTP_METHOD = "GET"
HMRC_INDIVIDUAL_TAX_SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE = (
    "/individual-tax/sa/{utr}/annual-summary/{taxYear}"
)
HMRC_INDIVIDUAL_TAX_ACCEPT = "application/vnd.hmrc.1.1+json"
HMRC_INDIVIDUAL_TAX_SCOPE = "read:individual-tax"
HMRC_INDIVIDUAL_TAX_JSON_CONTENT_TYPE = "application/json"

# Marker substituted for the raw UTR in every retained/redacted path form so no
# recoverable UTR survives construction, copy, pickle, repr, equality or hash.
UTR_REDACTION_MARKER = "[UTR-REDACTED]"

# The exact documented status/code pairings. The outer mapping is read-only and
# every nested code set is a frozenset: mutation attempts at either level leave
# the validation mapping unchanged.
HMRC_INDIVIDUAL_TAX_400_CODES = frozenset({"SA_UTR_INVALID", "TAX_YEAR_INVALID"})
HMRC_INDIVIDUAL_TAX_401_CODES = frozenset({"UNAUTHORIZED"})
HMRC_INDIVIDUAL_TAX_404_CODES = frozenset({"NOT_FOUND"})
HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES = MappingProxyType({
    400: HMRC_INDIVIDUAL_TAX_400_CODES,
    401: HMRC_INDIVIDUAL_TAX_401_CODES,
    404: HMRC_INDIVIDUAL_TAX_404_CODES,
})

HMRC_INDIVIDUAL_TAX_COMPLETENESS = "UNVERIFIED"

# --- Exact documented field-name universes -----------------------------------

_TOP_LEVEL_NAMES = frozenset({
    "employments",
    "pensionsAnnuitiesAndOtherStateBenefits",
    "refunds",
})
_EMPLOYMENT_NAMES = frozenset({"employerPayeReference", "taxTakenOffPay"})
_BENEFITS_NAMES = frozenset({
    "otherPensionsAndRetirementAnnuities",
    "incapacityBenefit",
})
_REFUNDS_NAMES = frozenset({"taxRefundedOrSetOff"})
_ERROR_NAMES = frozenset({"code", "message"})

# --- Reserved defensive bounds (NOT endpoint sign/precision/magnitude facts) -
# Finite safety limits only. They are not evidence of an endpoint minimum,
# maximum, sign rule, scale, rounding rule or collection size.

_RESERVED_MAX_OBJECT_MEMBERS = 64
_RESERVED_MAX_UNKNOWN_KEYS = 32
_RESERVED_MAX_KEY_LENGTH = 256
_RESERVED_MAX_STRING_LENGTH = 4096
_RESERVED_MAX_EMPLOYMENTS = 10_000
_RESERVED_NUMBER_MAX_DIGITS = 38
_RESERVED_NUMBER_MAX_PLACES = 12
_RESERVED_NUMBER_MAX_MAGNITUDE = Decimal("1000000000000000000")  # 10**18
_RESERVED_NUMBER_MAX_INT = 10 ** 18

# ASCII-only regexes. ``[0-9]`` deliberately excludes Unicode ``Nd`` digits, so
# ``str.isdigit()``/``isdecimal()``/``isnumeric()`` semantics are never used.
_UTR_RE = re.compile(r"[0-9]{10}")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")


class HMRCIndividualTaxContractError(ValueError):
    """Fail-closed validation error whose message never includes source data."""


def _fail(rule: str) -> HMRCIndividualTaxContractError:
    return HMRCIndividualTaxContractError(
        f"HMRC individual tax contract: {rule}"
    )


# --- Defensive validators ----------------------------------------------------


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


def _has_unsafe_unicode_character(text: str) -> bool:
    """Return ``True`` if any character is in Unicode general category ``C``.

    Category ``C`` is the conservative unsafe set: control (``Cc``), format
    (``Cf``), surrogate (``Cs``), private-use (``Co``) and unassigned (``Cn``).
    The caller guarantees ``text`` is an exact built-in ``str``.
    """
    for char in text:
        if unicodedata.category(char).startswith("C"):
            return True
    return False


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


def _require_employer_paye_reference(value: object) -> str:
    """Validate a retained ``employerPayeReference`` string.

    The Reserved length bound and Unicode category ``C`` rejection are applied,
    but other exact string content is preserved without trimming or normalising.
    Empty and separator-whitespace-only values are schema-valid (no evidenced
    ``minLength``) and are not promoted into downstream evidence.
    """
    result = _require_string_value(value, "employerPayeReference")
    if _has_unsafe_unicode_character(result):
        raise _fail("employerPayeReference contains unsafe Unicode characters")
    return result


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


# --- Request intent ----------------------------------------------------------


@dataclass(frozen=True, repr=False, slots=True, kw_only=True)
class IndividualTaxRequestIntent:
    """Frozen, UTR-free intent for the documented annual-summary read.

    ``utr`` is a construction-only value: it is validated as exactly ten ASCII
    digits and immediately discarded. ``tax_year`` is the only request-derived
    identity retained. Method, sandbox origin, path template, Accept value,
    scope and the UTR-redacted path are derived internally from documented
    constants and can never be supplied, forged or replaced through the public
    constructor, ``dataclasses.replace``, copy, deepcopy or pickle. The class is
    slotted and frozen: it carries no instance ``__dict__``, exposes no sendable
    URL/header/body or credential state, and cannot be reassembled with an
    arbitrary retained field.
    """

    utr: InitVar[str]
    tax_year: str
    method: str = field(init=False, default=HMRC_INDIVIDUAL_TAX_HTTP_METHOD)
    sandbox_origin: str = field(init=False, default=HMRC_INDIVIDUAL_TAX_SANDBOX_ORIGIN)
    path_template: str = field(init=False, default=HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE)
    accept: str = field(init=False, default=HMRC_INDIVIDUAL_TAX_ACCEPT)
    scope: str = field(init=False, default=HMRC_INDIVIDUAL_TAX_SCOPE)
    redacted_path: str = field(init=False, default="")
    _tax_year_binding: str = field(init=False, repr=False, compare=False, default="")

    def __post_init__(self, utr: str) -> None:
        # Fail closed on a malformed UTR, then discard it. The intent keeps only
        # the validated tax year plus the constant-derived request descriptors,
        # and a UTR-redacted path derived from the tax year alone.
        _require_ascii_utr(utr)
        tax_year = _require_tax_year(self.tax_year)
        object.__setattr__(self, "tax_year", tax_year)
        object.__setattr__(self, "method", HMRC_INDIVIDUAL_TAX_HTTP_METHOD)
        object.__setattr__(self, "sandbox_origin", HMRC_INDIVIDUAL_TAX_SANDBOX_ORIGIN)
        object.__setattr__(self, "path_template", HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE)
        object.__setattr__(self, "accept", HMRC_INDIVIDUAL_TAX_ACCEPT)
        object.__setattr__(self, "scope", HMRC_INDIVIDUAL_TAX_SCOPE)
        object.__setattr__(self, "redacted_path", _redacted_path_for(tax_year))
        object.__setattr__(self, "_tax_year_binding", tax_year)

    def __repr__(self) -> str:
        return (
            "IndividualTaxRequestIntent(method='GET', sandbox_origin="
            f"{self.sandbox_origin!r}, path_template={self.path_template!r}, "
            f"accept={self.accept!r}, scope={self.scope!r}, "
            f"tax_year={self.tax_year!r}, redacted_path={self.redacted_path!r})"
        )

    def __copy__(self) -> "IndividualTaxRequestIntent":
        # Deeply immutable: sharing the instance is a fully coherent copy, but
        # only after re-validating the complete retained state so a forged,
        # missing or stale field cannot be preserved.
        _require_exact_request_intent(self)
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualTaxRequestIntent":
        _require_exact_request_intent(self)
        return self

    def __reduce__(self):
        # Reconstruct through the validated tax-year-only rebuild boundary so a
        # forged pickle cannot inject an unvalidated retained field. Validate
        # the complete retained state first: a forged/missing/stale descriptor
        # must raise rather than be silently normalised into a valid request.
        _require_exact_request_intent(self)
        return (_rebuild_individual_tax_request_intent, (self.tax_year,))


def _immutable_request_setattr(self: object, name: str, value: object) -> None:
    raise AttributeError("IndividualTaxRequestIntent is immutable")


def _immutable_request_delattr(self: object, name: str) -> None:
    raise AttributeError("IndividualTaxRequestIntent is immutable")


# The frozen+slotted dataclass generates a ``__setattr__`` whose non-field
# branch raises ``TypeError`` on some CPython versions. Replace both accessors
# with constant, fail-closed ``AttributeError`` versions so every mutation
# attempt (field, non-field or deletion) fails closed identically.
IndividualTaxRequestIntent.__setattr__ = _immutable_request_setattr  # type: ignore[method-assign]
IndividualTaxRequestIntent.__delattr__ = _immutable_request_delattr  # type: ignore[method-assign]


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


def _redacted_path_for(tax_year: str) -> str:
    """Derive the UTR-redacted path from the validated tax year alone."""
    return (
        HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE.replace("{utr}", UTR_REDACTION_MARKER)
        .replace("{taxYear}", tax_year)
    )


def build_individual_tax_request(
    *, utr: str, tax_year: str
) -> IndividualTaxRequestIntent:
    """Build a frozen, UTR-free request intent.

    This is a thin, keyword-only convenience over the single validated
    construction boundary: the raw UTR is validated as exactly ten ASCII digits
    and discarded. Only the validated tax year and the constant-derived request
    descriptors (with a UTR-redacted path) are retained.
    """
    return IndividualTaxRequestIntent(utr=utr, tax_year=tax_year)


def _observation_field(observation: object, name: str) -> object:
    """Return a retained observation field or fail closed if it is missing."""
    try:
        return object.__getattribute__(observation, name)
    except AttributeError:
        raise _fail(f"observation {name} must be present")


def _require_observation_request_binding(
    observation: object,
) -> IndividualTaxRequestIntent:
    """Require and revalidate the retained, UTR-free provenance binding."""
    return _require_exact_request_intent(
        _observation_field(observation, "_request_binding")
    )


def _require_observation_tax_year(
    observation: object,
    request: IndividualTaxRequestIntent,
) -> str:
    """Require the retained ``tax_year`` to be coherent with the request."""
    tax_year = _observation_field(observation, "tax_year")
    if type(tax_year) is not str or tax_year != request.tax_year:
        raise _fail(
            "observation tax year is not coherent with the producing request"
        )
    return tax_year


def _require_exact_instance_state(
    observation: object, expected: frozenset[str]
) -> None:
    """Require the observation to carry exactly its declared instance fields.

    ``object.__setattr__`` can inject undeclared instance attributes into a
    frozen, non-slotted dataclass. Before any copy, deepcopy or reduction the
    instance ``__dict__`` is therefore compared against the exact declared key
    set, so injected extra state fails closed instead of being preserved or
    silently ignored.
    """
    try:
        actual = set(observation.__dict__)
    except AttributeError:
        raise _fail("observation instance state must be inspectable")
    if actual != expected:
        raise _fail("observation carries undeclared instance state")


# --- Observations ------------------------------------------------------------


_EMPLOYMENT_ITEM_STATE_KEYS = frozenset({
    "employer_paye_reference",
    "tax_taken_off_pay",
    "unknown_names",
})


@dataclass(frozen=True, repr=False)
class EmploymentItemObservation:
    """Validated facts from one ``employments`` array item."""

    employer_paye_reference: str
    tax_taken_off_pay: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        self._validate_state()

    def _validate_state(self) -> None:
        if type(self) is not EmploymentItemObservation:
            raise _fail("employment item must be an exact observation")
        _require_exact_instance_state(self, _EMPLOYMENT_ITEM_STATE_KEYS)
        _require_employer_paye_reference(self.employer_paye_reference)
        _parse_number(self.tax_taken_off_pay, "taxTakenOffPay")
        _require_unknown_names(self.unknown_names, "employment item")

    def __repr__(self) -> str:
        return "EmploymentItemObservation([REDACTED])"

    def __copy__(self) -> "EmploymentItemObservation":
        self._validate_state()
        return self

    def __deepcopy__(self, memo: dict) -> "EmploymentItemObservation":
        self._validate_state()
        return self

    def __reduce__(self):
        self._validate_state()
        return (_rebuild_employment_item, (
            self.employer_paye_reference,
            self.tax_taken_off_pay,
            self.unknown_names,
        ))


_PENSIONS_BENEFITS_STATE_KEYS = frozenset({
    "other_pensions_and_retirement_annuities",
    "incapacity_benefit",
    "present_fields",
    "absent_fields",
    "unknown_names",
})


@dataclass(frozen=True, repr=False)
class PensionsBenefitsObservation:
    """Validated facts from ``pensionsAnnuitiesAndOtherStateBenefits``.

    Omission of a documented member is ``None`` and is never coerced to zero;
    explicit null is rejected before this object is built.
    """

    other_pensions_and_retirement_annuities: int | Decimal | None = None
    incapacity_benefit: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    absent_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        self._validate_state()

    def _validate_state(self) -> None:
        if type(self) is not PensionsBenefitsObservation:
            raise _fail("benefits value must be an exact observation")
        _require_exact_instance_state(self, _PENSIONS_BENEFITS_STATE_KEYS)
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
        self._validate_state()
        return self

    def __deepcopy__(self, memo: dict) -> "PensionsBenefitsObservation":
        self._validate_state()
        return self

    def __reduce__(self):
        self._validate_state()
        return (_rebuild_pensions_benefits, (
            self.other_pensions_and_retirement_annuities,
            self.incapacity_benefit,
            self.present_fields,
            self.absent_fields,
            self.unknown_names,
        ))


_REFUNDS_STATE_KEYS = frozenset({
    "tax_refunded_or_set_off",
    "present_fields",
    "absent_fields",
    "unknown_names",
})


@dataclass(frozen=True, repr=False)
class RefundsObservation:
    """Validated facts from the ``refunds`` object.

    Omission of ``taxRefundedOrSetOff`` is ``None`` and is never coerced to
    zero; explicit null is rejected before this object is built. The value is
    retained only as a separate refund/set-off literal, never as a credit,
    entitlement, cash amount or reduction of deducted tax.
    """

    tax_refunded_or_set_off: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    absent_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        self._validate_state()

    def _validate_state(self) -> None:
        if type(self) is not RefundsObservation:
            raise _fail("refunds value must be an exact observation")
        _require_exact_instance_state(self, _REFUNDS_STATE_KEYS)
        present = self.present_fields
        absent = self.absent_fields
        if type(present) is not frozenset:
            raise _fail("refunds present_fields must be an exact frozenset")
        if type(absent) is not frozenset:
            raise _fail("refunds absent_fields must be an exact frozenset")
        if present & absent:
            raise _fail("refunds present and absent fields must be disjoint")
        if present | absent != _REFUNDS_NAMES:
            raise _fail("refunds present and absent fields must be exhaustive")
        if "taxRefundedOrSetOff" in present:
            if self.tax_refunded_or_set_off is None:
                raise _fail("taxRefundedOrSetOff must not be None when present")
            _parse_number(self.tax_refunded_or_set_off, "taxRefundedOrSetOff")
        elif self.tax_refunded_or_set_off is not None:
            raise _fail("taxRefundedOrSetOff must be None when absent")
        _require_unknown_names(self.unknown_names, "refunds object")

    def __repr__(self) -> str:
        return "RefundsObservation([REDACTED])"

    def __copy__(self) -> "RefundsObservation":
        self._validate_state()
        return self

    def __deepcopy__(self, memo: dict) -> "RefundsObservation":
        self._validate_state()
        return self

    def __reduce__(self):
        self._validate_state()
        return (_rebuild_refunds, (
            self.tax_refunded_or_set_off,
            self.present_fields,
            self.absent_fields,
            self.unknown_names,
        ))


_ANNUAL_SUMMARY_STATE_KEYS = frozenset({
    "employments",
    "pensions_benefits",
    "refunds",
    "request",
    "tax_year",
    "unknown_names",
    "completeness",
    "_request_binding",
})


@dataclass(frozen=True, repr=False, init=False)
class IndividualTaxAnnualSummaryObservation:
    """Validated facts from a documented HTTP 200 annual-summary response.

    Completeness is always ``UNVERIFIED``; an empty ``employments`` list is
    shape-valid but never evidence of zero tax deducted. The exact validated,
    UTR-free request intent is retained, the public ``tax_year`` and the private
    ``_request_binding`` are derived from that request (never supplied), and the
    request identity is non-replaceable, so no ``dataclasses.replace``,
    constructor, copy, deepcopy or pickle path can substitute request identity
    while retaining response facts.
    """

    employments: tuple[EmploymentItemObservation, ...]
    pensions_benefits: PensionsBenefitsObservation
    refunds: RefundsObservation
    request: IndividualTaxRequestIntent = field(init=False)
    tax_year: str = field(init=False, compare=False)
    unknown_names: frozenset[str] = frozenset()
    completeness: str = HMRC_INDIVIDUAL_TAX_COMPLETENESS
    _request_binding: IndividualTaxRequestIntent = field(
        init=False, repr=False, compare=False
    )

    def __init__(
        self,
        *,
        employments: tuple[EmploymentItemObservation, ...],
        pensions_benefits: PensionsBenefitsObservation,
        refunds: RefundsObservation,
        request: IndividualTaxRequestIntent,
        unknown_names: frozenset[str] = frozenset(),
        completeness: str = HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    ) -> None:
        request = _require_exact_request_intent(request)
        object.__setattr__(self, "employments", employments)
        object.__setattr__(self, "pensions_benefits", pensions_benefits)
        object.__setattr__(self, "refunds", refunds)
        object.__setattr__(self, "request", request)
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "unknown_names", unknown_names)
        object.__setattr__(self, "completeness", completeness)
        object.__setattr__(
            self,
            "_request_binding",
            _rebuild_individual_tax_request_intent(request.tax_year),
        )
        self._validate_state()

    def _validate_facts(self) -> None:
        if type(self.employments) is not tuple:
            raise _fail("employments must be an exact built-in tuple")
        if len(self.employments) > _RESERVED_MAX_EMPLOYMENTS:
            raise _fail("employments exceeds the reserved item bound")
        for item in self.employments:
            if type(item) is not EmploymentItemObservation:
                raise _fail("employments must contain exact employment observations")
            item._validate_state()
        if type(self.pensions_benefits) is not PensionsBenefitsObservation:
            raise _fail("pensions_benefits must be an exact PensionsBenefitsObservation")
        self.pensions_benefits._validate_state()
        if type(self.refunds) is not RefundsObservation:
            raise _fail("refunds must be an exact RefundsObservation")
        self.refunds._validate_state()
        if type(self.completeness) is not str or self.completeness != HMRC_INDIVIDUAL_TAX_COMPLETENESS:
            raise _fail("completeness must be the exact documented UNVERIFIED value")
        _require_unknown_names(self.unknown_names, "annual-summary observation")

    def _validate_state(self) -> None:
        request = _require_exact_request_intent(_observation_field(self, "request"))
        binding = _require_observation_request_binding(self)
        if request != binding:
            raise _fail(
                "observation request is not coherent with its producing binding"
            )
        _require_observation_tax_year(self, request)
        _require_exact_instance_state(self, _ANNUAL_SUMMARY_STATE_KEYS)
        self._validate_facts()

    def __repr__(self) -> str:
        return "IndividualTaxAnnualSummaryObservation([REDACTED])"

    def __copy__(self) -> "IndividualTaxAnnualSummaryObservation":
        self._validate_state()
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualTaxAnnualSummaryObservation":
        self._validate_state()
        return self

    def __reduce__(self):
        self._validate_state()
        return (_rebuild_annual_summary, (
            self.employments,
            self.pensions_benefits,
            self.refunds,
            self.request,
            self.unknown_names,
            self.completeness,
            self._request_binding,
        ))


_ERROR_STATE_KEYS = frozenset({
    "status_code",
    "code",
    "request",
    "tax_year",
    "unknown_names",
    "_request_binding",
})


@dataclass(frozen=True, repr=False, init=False)
class IndividualTaxErrorObservation:
    """Validated facts from a documented HTTP 400/401/404 error response.

    The error ``message`` is validated as a string and then discarded; only the
    documented ``code`` and ``status_code`` are retained. The exact validated,
    UTR-free request intent is retained, the public ``tax_year`` and the private
    ``_request_binding`` are derived from that request (never supplied), and the
    request identity is non-replaceable, so no ``dataclasses.replace``,
    constructor, copy, deepcopy or pickle path can substitute request identity
    while retaining response facts.
    """

    status_code: int
    code: str
    request: IndividualTaxRequestIntent = field(init=False)
    tax_year: str = field(init=False, compare=False)
    unknown_names: frozenset[str] = frozenset()
    _request_binding: IndividualTaxRequestIntent = field(
        init=False, repr=False, compare=False
    )

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        request: IndividualTaxRequestIntent,
        unknown_names: frozenset[str] = frozenset(),
    ) -> None:
        request = _require_exact_request_intent(request)
        object.__setattr__(self, "status_code", status_code)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "request", request)
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "unknown_names", unknown_names)
        object.__setattr__(
            self,
            "_request_binding",
            _rebuild_individual_tax_request_intent(request.tax_year),
        )
        self._validate_state()

    def _validate_facts(self) -> None:
        if type(self.status_code) is not int:
            raise _fail("status_code must be an exact built-in integer")
        if self.status_code not in HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES:
            raise _fail("status_code is not a documented error status")
        if type(self.code) is not str:
            raise _fail("code must be an exact built-in string")
        if self.code not in HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES[self.status_code]:
            raise _fail("error code does not match the documented status")
        _require_unknown_names(self.unknown_names, "error body")

    def _validate_state(self) -> None:
        request = _require_exact_request_intent(_observation_field(self, "request"))
        binding = _require_observation_request_binding(self)
        if request != binding:
            raise _fail(
                "observation request is not coherent with its producing binding"
            )
        _require_observation_tax_year(self, request)
        _require_exact_instance_state(self, _ERROR_STATE_KEYS)
        self._validate_facts()

    def __repr__(self) -> str:
        return (
            f"IndividualTaxErrorObservation(status_code={self.status_code}, "
            f"code={self.code!r})"
        )

    def __copy__(self) -> "IndividualTaxErrorObservation":
        self._validate_state()
        return self

    def __deepcopy__(self, memo: dict) -> "IndividualTaxErrorObservation":
        self._validate_state()
        return self

    def __reduce__(self):
        self._validate_state()
        return (_rebuild_error, (
            self.status_code,
            self.code,
            self.request,
            self.unknown_names,
            self._request_binding,
        ))


# --- Response observation ----------------------------------------------------


def _parse_employment_item(item: object) -> EmploymentItemObservation:
    obj = _require_object(item, "employment item")
    unknown_names = _classify_object_members(obj, _EMPLOYMENT_NAMES, "employment item")

    if "employerPayeReference" not in obj:
        raise _fail("employment item is missing employerPayeReference")
    if "taxTakenOffPay" not in obj:
        raise _fail("employment item is missing taxTakenOffPay")

    employer_paye_reference = _require_employer_paye_reference(
        obj["employerPayeReference"]
    )
    tax_taken_off_pay = _parse_number(obj["taxTakenOffPay"], "taxTakenOffPay")

    return EmploymentItemObservation(
        employer_paye_reference=employer_paye_reference,
        tax_taken_off_pay=tax_taken_off_pay,
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
        present_fields=frozenset(present),
        absent_fields=frozenset(absent),
        unknown_names=unknown_names,
    )


def _parse_refunds(value: object) -> RefundsObservation:
    obj = _require_object(value, "refunds")
    unknown_names = _classify_object_members(obj, _REFUNDS_NAMES, "refunds object")

    present: list[str] = []
    absent: list[str] = []
    parsed: int | Decimal | None = None
    for name in sorted(_REFUNDS_NAMES):
        if name not in obj:
            absent.append(name)
            continue
        present.append(name)
        raw = obj[name]
        if raw is None:
            raise _fail(f"{name} must not be explicit null")
        parsed = _parse_number(raw, name)

    return RefundsObservation(
        tax_refunded_or_set_off=parsed,
        present_fields=frozenset(present),
        absent_fields=frozenset(absent),
        unknown_names=unknown_names,
    )


def _parse_annual_summary(
    request: IndividualTaxRequestIntent, payload: dict
) -> IndividualTaxAnnualSummaryObservation:
    obj = _require_object(payload, "annual-summary response")
    unknown_names = _classify_object_members(obj, _TOP_LEVEL_NAMES, "top-level object")

    if "employments" not in obj:
        raise _fail("annual-summary response is missing employments")
    if "pensionsAnnuitiesAndOtherStateBenefits" not in obj:
        raise _fail(
            "annual-summary response is missing pensionsAnnuitiesAndOtherStateBenefits"
        )
    if "refunds" not in obj:
        raise _fail("annual-summary response is missing refunds")

    employments_raw = _require_list(obj["employments"], "employments")
    if len(employments_raw) > _RESERVED_MAX_EMPLOYMENTS:
        raise _fail("employments exceeds the reserved item bound")

    employments = tuple(_parse_employment_item(item) for item in employments_raw)
    benefits = _parse_benefits(obj["pensionsAnnuitiesAndOtherStateBenefits"])
    refunds = _parse_refunds(obj["refunds"])

    return IndividualTaxAnnualSummaryObservation(
        employments=employments,
        pensions_benefits=benefits,
        refunds=refunds,
        request=request,
        unknown_names=unknown_names,
        completeness=HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    )


def _parse_error(
    request: IndividualTaxRequestIntent, status_code: int, payload: dict
) -> IndividualTaxErrorObservation:
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

    allowed = HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES[status_code]
    if code not in allowed:
        raise _fail("error code does not match the documented status")

    return IndividualTaxErrorObservation(
        status_code=status_code,
        code=code,
        request=request,
        unknown_names=unknown_names,
    )


def _require_exact_request_intent(request: object) -> IndividualTaxRequestIntent:
    """Require the exact intent and revalidate its full retained state.

    Construction history is deliberately not trusted: every retained field is
    re-read and checked against the documented constant or the validated tax
    year so a forged, missing or additionally-shaped intent fails closed here,
    before any hostile response input is touched.
    """
    if type(request) is not IndividualTaxRequestIntent:
        raise _fail("request must be an exact IndividualTaxRequestIntent")

    tax_year = _require_request_field_string(request, "tax_year")
    method = _require_request_field_string(request, "method")
    sandbox_origin = _require_request_field_string(request, "sandbox_origin")
    path_template = _require_request_field_string(request, "path_template")
    accept = _require_request_field_string(request, "accept")
    scope = _require_request_field_string(request, "scope")
    redacted_path = _require_request_field_string(request, "redacted_path")
    tax_year_binding = _require_request_field_string(request, "_tax_year_binding")

    _require_tax_year(tax_year)
    if method != HMRC_INDIVIDUAL_TAX_HTTP_METHOD:
        raise _fail("request method is not the documented value")
    if sandbox_origin != HMRC_INDIVIDUAL_TAX_SANDBOX_ORIGIN:
        raise _fail("request sandbox origin is not the documented value")
    if path_template != HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE:
        raise _fail("request path template is not the documented value")
    if accept != HMRC_INDIVIDUAL_TAX_ACCEPT:
        raise _fail("request Accept value is not the documented value")
    if scope != HMRC_INDIVIDUAL_TAX_SCOPE:
        raise _fail("request scope is not the documented value")
    if redacted_path != _redacted_path_for(tax_year):
        raise _fail("request redacted path is not coherent with the tax year")
    if tax_year_binding != tax_year:
        raise _fail("request tax year is not coherent with its original binding")
    return request


def _require_request_field_string(request: IndividualTaxRequestIntent, name: str) -> str:
    try:
        value = object.__getattribute__(request, name)
    except AttributeError:
        raise _fail(f"request {name} must be present")
    if type(value) is not str:
        raise _fail(f"request {name} must be an exact built-in string")
    return value


def observe_individual_tax_response(
    request: IndividualTaxRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: object,
) -> IndividualTaxAnnualSummaryObservation | IndividualTaxErrorObservation:
    """Observe an already-retrieved response without any transport.

    Only the documented HTTP 200 success shape and the documented HTTP 400/401/
    404 error shapes are accepted. HTTP 404 is retained as unavailable
    evidence, never as an authoritative empty or zero-tax record.
    """
    request = _require_exact_request_intent(request)
    if type(status_code) is not int or isinstance(status_code, bool):
        raise _fail("status_code must be an exact built-in integer")
    if type(content_type) is not str:
        raise _fail("content_type must be an exact built-in string")

    if status_code == 200:
        if content_type != HMRC_INDIVIDUAL_TAX_JSON_CONTENT_TYPE:
            raise _fail("HTTP 200 requires exact application/json")
        return _parse_annual_summary(
            request, _require_object(payload, "response payload")
        )

    if status_code in (400, 401, 404):
        if content_type != HMRC_INDIVIDUAL_TAX_JSON_CONTENT_TYPE:
            raise _fail("documented error statuses require exact application/json")
        return _parse_error(
            request, status_code, _require_object(payload, "error payload")
        )

    raise _fail("undocumented HTTP status is not accepted")


# --- Pickle/copy rebuild boundaries (validated construction entry points) ----


def _rebuild_individual_tax_request_intent(tax_year: str) -> IndividualTaxRequestIntent:
    """Reconstruct the intent from its only variable retained field.

    The constant-derived descriptors are recomputed from documented constants
    and the validated tax year, so a forged pickle cannot inject an unvalidated
    retained field or an incoherent redacted path.
    """
    intent = object.__new__(IndividualTaxRequestIntent)
    validated = _require_tax_year(tax_year)
    object.__setattr__(intent, "tax_year", validated)
    object.__setattr__(intent, "method", HMRC_INDIVIDUAL_TAX_HTTP_METHOD)
    object.__setattr__(intent, "sandbox_origin", HMRC_INDIVIDUAL_TAX_SANDBOX_ORIGIN)
    object.__setattr__(intent, "path_template", HMRC_INDIVIDUAL_TAX_PATH_TEMPLATE)
    object.__setattr__(intent, "accept", HMRC_INDIVIDUAL_TAX_ACCEPT)
    object.__setattr__(intent, "scope", HMRC_INDIVIDUAL_TAX_SCOPE)
    object.__setattr__(intent, "redacted_path", _redacted_path_for(validated))
    object.__setattr__(intent, "_tax_year_binding", validated)
    return intent


def _rebuild_employment_item(
    employer_paye_reference: str,
    tax_taken_off_pay: int | Decimal,
    unknown_names: frozenset[str],
) -> EmploymentItemObservation:
    return EmploymentItemObservation(
        employer_paye_reference=employer_paye_reference,
        tax_taken_off_pay=tax_taken_off_pay,
        unknown_names=unknown_names,
    )


def _rebuild_pensions_benefits(
    other_pensions_and_retirement_annuities: int | Decimal | None,
    incapacity_benefit: int | Decimal | None,
    present_fields: frozenset[str],
    absent_fields: frozenset[str],
    unknown_names: frozenset[str],
) -> PensionsBenefitsObservation:
    return PensionsBenefitsObservation(
        other_pensions_and_retirement_annuities=other_pensions_and_retirement_annuities,
        incapacity_benefit=incapacity_benefit,
        present_fields=present_fields,
        absent_fields=absent_fields,
        unknown_names=unknown_names,
    )


def _rebuild_refunds(
    tax_refunded_or_set_off: int | Decimal | None,
    present_fields: frozenset[str],
    absent_fields: frozenset[str],
    unknown_names: frozenset[str],
) -> RefundsObservation:
    return RefundsObservation(
        tax_refunded_or_set_off=tax_refunded_or_set_off,
        present_fields=present_fields,
        absent_fields=absent_fields,
        unknown_names=unknown_names,
    )


def _rebuild_annual_summary(
    employments: tuple[EmploymentItemObservation, ...],
    pensions_benefits: PensionsBenefitsObservation,
    refunds: RefundsObservation,
    request: IndividualTaxRequestIntent,
    unknown_names: frozenset[str],
    completeness: str,
    binding: IndividualTaxRequestIntent,
) -> IndividualTaxAnnualSummaryObservation:
    request = _require_exact_request_intent(request)
    _require_exact_request_intent(binding)
    if request != binding:
        raise _fail(
            "observation request is not coherent with its producing binding"
        )
    return IndividualTaxAnnualSummaryObservation(
        employments=employments,
        pensions_benefits=pensions_benefits,
        refunds=refunds,
        request=request,
        unknown_names=unknown_names,
        completeness=completeness,
    )


def _rebuild_error(
    status_code: int,
    code: str,
    request: IndividualTaxRequestIntent,
    unknown_names: frozenset[str],
    binding: IndividualTaxRequestIntent,
) -> IndividualTaxErrorObservation:
    request = _require_exact_request_intent(request)
    _require_exact_request_intent(binding)
    if request != binding:
        raise _fail(
            "observation request is not coherent with its producing binding"
        )
    return IndividualTaxErrorObservation(
        status_code=status_code,
        code=code,
        request=request,
        unknown_names=unknown_names,
    )
