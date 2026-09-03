"""Transport-neutral source evidence for HMRC Individual Income 1.2.

Consumes only an exact fully revalidated annual-summary success observation and
preserves its literal source shape. This is evidence, not a canonical tax,
accounting, cash, customer, identity, transport or activation boundary.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from reserved.providers.hmrc_individual_income_contract import (
    HMRC_INDIVIDUAL_INCOME_API,
    HMRC_INDIVIDUAL_INCOME_API_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    EmploymentItemObservation,
    HMRCIndividualIncomeContractError,
    IndividualIncomeAnnualSummaryObservation,
    PensionsBenefitsObservation,
    validate_individual_income_annual_summary_observation,
)


RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH = 256
_MAX_EMPLOYMENTS = 10_000
_MAX_UNKNOWN_NAMES = 32
_MAX_NAME_LENGTH = 256
_MAX_STRING_LENGTH = 4096
_MAX_DIGITS = 38
_MAX_PLACES = 12
_MAX_INT = 10 ** 18
_MAX_MAGNITUDE = Decimal("1000000000000000000")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_UNSET = object()

_TOP_DOCUMENTED = frozenset(
    {"employments", "pensionsAnnuitiesAndOtherStateBenefits"}
)
_EMPLOYMENT_DOCUMENTED = frozenset(
    {"employerPayeReference", "payFromEmployment"}
)
_BENEFITS_DOCUMENTED = frozenset(
    {
        "otherPensionsAndRetirementAnnuities",
        "incapacityBenefit",
        "jobseekersAllowance",
        "seissNetPaid",
    }
)
_BENEFIT_FIELDS = (
    ("otherPensionsAndRetirementAnnuities", "other_pensions_and_retirement_annuities"),
    ("incapacityBenefit", "incapacity_benefit"),
    ("jobseekersAllowance", "jobseekers_allowance"),
    ("seissNetPaid", "seiss_net_paid"),
)


class HMRCIndividualIncomeSourceEvidenceError(ValueError):
    """Constant, non-echoing source-evidence validation failure."""


def _fail(rule: str) -> HMRCIndividualIncomeSourceEvidenceError:
    return HMRCIndividualIncomeSourceEvidenceError(
        f"HMRC Individual Income source evidence: {rule}"
    )


def _safe_text(value: object, field_name: str, max_length: int, *, nonempty: bool = False) -> str:
    if type(value) is not str:
        raise _fail(f"{field_name} must be an exact built-in string")
    if (nonempty and not value) or len(value) > max_length:
        raise _fail(f"{field_name} is outside the Reserved defensive bound")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise _fail(f"{field_name} contains unsafe Unicode characters")
    return value


def _source_string(value: object, field_name: str, max_length: int) -> str:
    """Preserve an exact source-valid documented string without normalization."""
    if type(value) is not str:
        raise _fail(f"{field_name} must be an exact built-in string")
    if len(value) > max_length:
        raise _fail(f"{field_name} exceeds the Reserved defensive bound")
    return value


def _unknown_names(
    value: object,
    field_name: str,
    documented: frozenset[str],
) -> frozenset[str]:
    if type(value) is not frozenset:
        raise _fail(f"{field_name} must be an exact frozenset")
    if len(value) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{field_name} exceeds the Reserved defensive bound")
    for name in value:
        _safe_text(name, field_name, _MAX_NAME_LENGTH, nonempty=True)
        if name in documented:
            raise _fail(f"{field_name} collides with a documented member")
    return value


def _number(value: object, field_name: str) -> int | Decimal:
    if type(value) is int:
        if value < -_MAX_INT or value > _MAX_INT:
            raise _fail(f"{field_name} exceeds the Reserved numeric bound")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise _fail(f"{field_name} must be finite")
        parts = value.as_tuple()
        places = max(0, -parts.exponent)
        integer_digits = max(1, len(parts.digits) + parts.exponent)
        if (
            abs(value) > _MAX_MAGNITUDE
            or len(parts.digits) > _MAX_DIGITS
            or places > _MAX_PLACES
            or integer_digits > _MAX_DIGITS
        ):
            raise _fail(f"{field_name} exceeds the Reserved numeric bound")
        return value
    raise _fail(f"{field_name} must be an exact built-in int or Decimal")


def _observed_at(value: object) -> datetime:
    if type(value) is not datetime or type(value.tzinfo) is not timezone:
        raise _fail("observed_at must be an aware built-in fixed-offset datetime")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _fail("source artifact digest must be lowercase SHA-256 hex")
    return value


def _exact_state(value: object, expected_type: type, names: frozenset[str], field_name: str) -> dict:
    if type(value) is not expected_type:
        raise _fail(f"{field_name} must have the exact expected type")
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or len(state) != len(names):
        raise _fail(f"{field_name} has unexpected instance state")
    actual: set[str] = set()
    for key in state:
        if type(key) is not str:
            raise _fail(f"{field_name} has unexpected instance state")
        actual.add(key)
    if actual != names:
        raise _fail(f"{field_name} has unexpected instance state")
    return state


@dataclass(frozen=True, repr=False)
class IndividualIncomeEmploymentSourceEvidence:
    employer_paye_reference: str
    pay_from_employment: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_employment(self)

    def __repr__(self) -> str:
        return "IndividualIncomeEmploymentSourceEvidence([REDACTED])"

    def __copy__(self):
        _validate_employment(self)
        return self

    def __deepcopy__(self, memo: dict):
        _validate_employment(self)
        return self

    def __reduce_ex__(self, protocol: int):
        _validate_employment(self)
        return (type(self), (
            self.employer_paye_reference,
            self.pay_from_employment,
            self.unknown_names,
        ))


_EMPLOYMENT_STATE = frozenset(
    {"employer_paye_reference", "pay_from_employment", "unknown_names"}
)


def _validate_employment(value: object) -> IndividualIncomeEmploymentSourceEvidence:
    state = _exact_state(
        value,
        IndividualIncomeEmploymentSourceEvidence,
        _EMPLOYMENT_STATE,
        "employment evidence",
    )
    _source_string(
        state["employer_paye_reference"],
        "employerPayeReference",
        _MAX_STRING_LENGTH,
    )
    _number(state["pay_from_employment"], "payFromEmployment")
    _unknown_names(state["unknown_names"], "employment unknown names", _EMPLOYMENT_DOCUMENTED)
    return value


@dataclass(frozen=True, repr=False)
class IndividualIncomePensionsBenefitsSourceEvidence:
    other_pensions_and_retirement_annuities: int | Decimal | None = None
    incapacity_benefit: int | Decimal | None = None
    jobseekers_allowance: int | Decimal | None = None
    seiss_net_paid: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    absent_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_benefits(self)

    def __repr__(self) -> str:
        return "IndividualIncomePensionsBenefitsSourceEvidence([REDACTED])"

    def __copy__(self):
        _validate_benefits(self)
        return self

    def __deepcopy__(self, memo: dict):
        _validate_benefits(self)
        return self

    def __reduce_ex__(self, protocol: int):
        _validate_benefits(self)
        return (type(self), tuple(object.__getattribute__(self, name) for _, name in _BENEFIT_FIELDS) + (
            self.present_fields,
            self.absent_fields,
            self.unknown_names,
        ))


_BENEFITS_STATE = frozenset(
    {name for _, name in _BENEFIT_FIELDS}
    | {"present_fields", "absent_fields", "unknown_names"}
)


def _validate_benefits(value: object) -> IndividualIncomePensionsBenefitsSourceEvidence:
    state = _exact_state(
        value,
        IndividualIncomePensionsBenefitsSourceEvidence,
        _BENEFITS_STATE,
        "pensions and benefits evidence",
    )
    present = state["present_fields"]
    absent = state["absent_fields"]
    if type(present) is not frozenset or type(absent) is not frozenset:
        raise _fail("benefit presence sets must be exact frozensets")
    if present & absent or present | absent != _BENEFITS_DOCUMENTED:
        raise _fail("benefit presence and absence must be coherent and exhaustive")
    for source_name, field_name in _BENEFIT_FIELDS:
        retained = state[field_name]
        if source_name in present:
            if retained is None:
                raise _fail("present benefit must retain an exact number")
            _number(retained, source_name)
        elif retained is not None:
            raise _fail("absent benefit must remain absent, not zero")
    _unknown_names(state["unknown_names"], "benefits unknown names", _BENEFITS_DOCUMENTED)
    return value


@dataclass(frozen=True, repr=False, init=False)
class HMRCIndividualIncomeSourceEvidence:
    source_api_name: str
    source_api_version: str
    tax_year: str
    employments: tuple[IndividualIncomeEmploymentSourceEvidence, ...]
    pensions_benefits: IndividualIncomePensionsBenefitsSourceEvidence
    evidence_reference: str
    observed_at: datetime
    completeness: str = HMRC_INDIVIDUAL_INCOME_COMPLETENESS
    unknown_names: frozenset[str] = frozenset()
    _source_artifact_sha256_state: Any = field(default=_UNSET, repr=False)

    def __init__(
        self,
        source_api_name: str,
        source_api_version: str,
        tax_year: str,
        employments: tuple[IndividualIncomeEmploymentSourceEvidence, ...],
        pensions_benefits: IndividualIncomePensionsBenefitsSourceEvidence,
        evidence_reference: str,
        observed_at: datetime,
        completeness: str = HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
        source_artifact_sha256: object = _UNSET,
        unknown_names: frozenset[str] = frozenset(),
        *,
        _source_artifact_sha256_state: object = _UNSET,
    ) -> None:
        for name, value in (
            ("source_api_name", source_api_name),
            ("source_api_version", source_api_version),
            ("tax_year", tax_year),
            ("employments", employments),
            ("pensions_benefits", pensions_benefits),
            ("evidence_reference", evidence_reference),
            ("observed_at", observed_at),
            ("completeness", completeness),
            ("unknown_names", unknown_names),
        ):
            object.__setattr__(self, name, value)
        digest_state = (
            _source_artifact_sha256_state
            if source_artifact_sha256 is _UNSET
            else source_artifact_sha256
        )
        object.__setattr__(self, "_source_artifact_sha256_state", digest_state)
        _validate_evidence(self)

    def __repr__(self) -> str:
        return "HMRCIndividualIncomeSourceEvidence([REDACTED])"

    def __copy__(self):
        _validate_evidence(self)
        return self

    def __deepcopy__(self, memo: dict):
        _validate_evidence(self)
        return self

    def __reduce_ex__(self, protocol: int):
        _validate_evidence(self)
        return (
            _restore_evidence,
            (
                self.source_api_name,
                self.source_api_version,
                self.tax_year,
                self.employments,
                self.pensions_benefits,
                self.evidence_reference,
                self.observed_at,
                self.completeness,
                self.unknown_names,
                self._source_artifact_sha256_state is not _UNSET,
                self.source_artifact_sha256,
            ),
        )


_EVIDENCE_STATE = frozenset(
    {
        "source_api_name", "source_api_version", "tax_year", "employments",
        "pensions_benefits", "evidence_reference", "observed_at", "completeness",
        "unknown_names", "_source_artifact_sha256_state",
    }
)


def _validate_evidence(value: object) -> HMRCIndividualIncomeSourceEvidence:
    state = _exact_state(
        value,
        HMRCIndividualIncomeSourceEvidence,
        _EVIDENCE_STATE,
        "source evidence bundle",
    )
    if type(state["source_api_name"]) is not str or state["source_api_name"] != HMRC_INDIVIDUAL_INCOME_API:
        raise _fail("source API name is not exact")
    if type(state["source_api_version"]) is not str or state["source_api_version"] != HMRC_INDIVIDUAL_INCOME_API_VERSION:
        raise _fail("source API version is not exact")
    tax_year = state["tax_year"]
    if type(tax_year) is not str or _TAX_YEAR_RE.fullmatch(tax_year) is None:
        raise _fail("tax year must match YYYY-YY exactly")
    employments = state["employments"]
    if type(employments) is not tuple or len(employments) > _MAX_EMPLOYMENTS:
        raise _fail("employments must be an exact bounded tuple")
    for employment in employments:
        _validate_employment(employment)
    _validate_benefits(state["pensions_benefits"])
    _safe_text(
        state["evidence_reference"],
        "evidence reference",
        RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH,
        nonempty=True,
    )
    _observed_at(state["observed_at"])
    if type(state["completeness"]) is not str or state["completeness"] != HMRC_INDIVIDUAL_INCOME_COMPLETENESS:
        raise _fail("completeness must be exactly UNVERIFIED")
    _unknown_names(state["unknown_names"], "top-level unknown names", _TOP_DOCUMENTED)
    digest_state = state["_source_artifact_sha256_state"]
    if digest_state is not _UNSET:
        _digest(digest_state)
    return value


def _source_artifact_sha256(value: HMRCIndividualIncomeSourceEvidence) -> str | None:
    _validate_evidence(value)
    retained = object.__getattribute__(value, "_source_artifact_sha256_state")
    return None if retained is _UNSET else retained


HMRCIndividualIncomeSourceEvidence.source_artifact_sha256 = property(  # type: ignore[assignment]
    _source_artifact_sha256
)


def _restore_evidence(
    source_api_name: str,
    source_api_version: str,
    tax_year: str,
    employments: tuple[IndividualIncomeEmploymentSourceEvidence, ...],
    pensions_benefits: IndividualIncomePensionsBenefitsSourceEvidence,
    evidence_reference: str,
    observed_at: datetime,
    completeness: str,
    unknown_names: frozenset[str],
    digest_present: bool,
    digest: object,
) -> HMRCIndividualIncomeSourceEvidence:
    if type(digest_present) is not bool:
        raise _fail("serialized digest presence must be an exact boolean")
    kwargs: dict[str, object] = {}
    if digest_present:
        kwargs["source_artifact_sha256"] = digest
    return HMRCIndividualIncomeSourceEvidence(
        source_api_name,
        source_api_version,
        tax_year,
        employments,
        pensions_benefits,
        evidence_reference,
        observed_at,
        completeness,
        unknown_names=unknown_names,
        **kwargs,
    )


def _bind_builder(
    source_validator: object,
    employment_type: type,
    benefits_type: type,
    evidence_type: type,
    reference_validator: object,
    time_validator: object,
    digest_validator: object,
):
    def build_hmrc_individual_income_source_evidence(
        observation: object,
        *args: object,
        **kwargs: object,
    ) -> HMRCIndividualIncomeSourceEvidence:
        if args or set(kwargs) - {
            "evidence_reference", "observed_at", "source_artifact_sha256"
        } or "evidence_reference" not in kwargs or "observed_at" not in kwargs:
            raise _fail("builder arguments are not the exact supported shape")
        try:
            validated = source_validator(observation)  # type: ignore[operator]
        except HMRCIndividualIncomeContractError as exc:
            raise _fail("source observation is invalid") from exc
        reference = reference_validator(kwargs["evidence_reference"])  # type: ignore[operator]
        observed = time_validator(kwargs["observed_at"])  # type: ignore[operator]
        evidence_kwargs: dict[str, object] = {}
        if "source_artifact_sha256" in kwargs:
            evidence_kwargs["source_artifact_sha256"] = digest_validator(  # type: ignore[operator]
                kwargs["source_artifact_sha256"]
            )
        employments = tuple(
            employment_type(
                item.employer_paye_reference,
                item.pay_from_employment,
                item.unknown_names,
            )
            for item in validated.employments
        )
        benefits = validated.pensions_benefits
        benefits_evidence = benefits_type(
            benefits.other_pensions_and_retirement_annuities,
            benefits.incapacity_benefit,
            benefits.jobseekers_allowance,
            benefits.seiss_net_paid,
            benefits.present_fields,
            benefits.absent_fields,
            benefits.unknown_names,
        )
        return evidence_type(
            HMRC_INDIVIDUAL_INCOME_API,
            HMRC_INDIVIDUAL_INCOME_API_VERSION,
            validated.tax_year,
            employments,
            benefits_evidence,
            reference,
            observed,
            HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
            unknown_names=validated.unknown_names,
            **evidence_kwargs,
        )

    return build_hmrc_individual_income_source_evidence


def _bind_reference_validator(validator: object, maximum: int):
    def validate(value: object) -> str:
        return validator(  # type: ignore[operator,return-value]
            value,
            "evidence reference",
            maximum,
            nonempty=True,
        )

    return validate


_evidence_reference = _bind_reference_validator(
    _safe_text,
    RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH,
)


build_hmrc_individual_income_source_evidence = _bind_builder(
    validate_individual_income_annual_summary_observation,
    IndividualIncomeEmploymentSourceEvidence,
    IndividualIncomePensionsBenefitsSourceEvidence,
    HMRCIndividualIncomeSourceEvidence,
    _evidence_reference,
    _observed_at,
    _digest,
)


def _bind_hardened_source_boundary(
    employment_type: type,
    benefits_type: type,
    evidence_type: type,
    source_validator: object,
    source_error_type: type,
    evidence_error_type: type,
    decimal_type: type,
    datetime_type: type,
    timezone_type: type,
    int_type: type,
    str_type: type,
    tuple_type: type,
    frozenset_type: type,
    dict_type: type,
    bool_type: type,
    tax_year_match: object,
    digest_match: object,
    unicode_category: object,
    expected_api: str,
    expected_version: str,
    expected_completeness: str,
    unset: object,
    employment_state: frozenset[str],
    benefits_state: frozenset[str],
    evidence_state: frozenset[str],
    top_documented: frozenset[str],
    employment_documented: frozenset[str],
    benefits_documented: frozenset[str],
    benefit_fields: tuple[tuple[str, str], ...],
    max_reference: int,
    max_employments: int,
    max_unknown: int,
    max_name: int,
    max_string: int,
    max_digits: int,
    max_places: int,
    max_integer: int,
    max_magnitude: Decimal,
):
    """Freeze the complete public construction/validation dependency graph.

    This closes ordinary module-global/helper substitution.  It intentionally
    does not claim resistance to arbitrary replacement of trusted class code.
    """
    exact_type, length, maximum, absolute, any_value = type, len, max, abs, any
    set_type = set
    enumerate_values = enumerate
    get = object.__getattribute__
    put = object.__setattr__
    empty_names = frozenset_type()

    def fail(rule: str):
        return evidence_error_type(f"HMRC Individual Income source evidence: {rule}")

    def exact_state(value: object, expected: type, names: frozenset[str], field_name: str):
        if exact_type(value) is not expected:
            raise fail(f"{field_name} must have the exact expected type")
        state = get(value, "__dict__")
        if exact_type(state) is not dict_type or length(state) != length(names):
            raise fail(f"{field_name} has unexpected instance state")
        actual = set_type()
        for key in state:
            if exact_type(key) is not str_type:
                raise fail(f"{field_name} has unexpected instance state")
            actual.add(key)
        if actual != names:
            raise fail(f"{field_name} has unexpected instance state")
        return state

    def safe_text(value: object, field_name: str, maximum: int, nonempty: bool = False):
        if exact_type(value) is not str_type or (nonempty and not value) or length(value) > maximum:
            raise fail(f"{field_name} is outside the Reserved defensive bound")
        for char in value:
            if unicode_category(char).startswith("C"):  # type: ignore[operator]
                raise fail(f"{field_name} contains unsafe Unicode characters")
        return value

    def source_string(value: object, field_name: str):
        if exact_type(value) is not str_type or length(value) > max_string:
            raise fail(f"{field_name} must be an exact bounded string")
        return value

    def unknown_names(value: object, field_name: str, documented: frozenset[str]):
        if exact_type(value) is not frozenset_type or length(value) > max_unknown:
            raise fail(f"{field_name} must be an exact bounded frozenset")
        for name in value:
            safe_text(name, field_name, max_name, True)
            if name in documented:
                raise fail(f"{field_name} collides with a documented member")
        return value

    def number(value: object, field_name: str):
        if exact_type(value) is int_type:
            if value < -max_integer or value > max_integer:
                raise fail(f"{field_name} exceeds the Reserved numeric bound")
            return value
        if exact_type(value) is decimal_type:
            if not value.is_finite():
                raise fail(f"{field_name} must be finite")
            parts = value.as_tuple()
            places = maximum(0, -parts.exponent)
            integer_digits = maximum(1, length(parts.digits) + parts.exponent)
            if (absolute(value) > max_magnitude or length(parts.digits) > max_digits
                    or places > max_places or integer_digits > max_digits):
                raise fail(f"{field_name} exceeds the Reserved numeric bound")
            return value
        raise fail(f"{field_name} must be an exact built-in int or Decimal")

    def validate_employment(value: object):
        state = exact_state(value, employment_type, employment_state, "employment evidence")
        source_string(state["employer_paye_reference"], "employerPayeReference")
        number(state["pay_from_employment"], "payFromEmployment")
        unknown_names(state["unknown_names"], "employment unknown names", employment_documented)
        return value

    def validate_benefits(value: object):
        state = exact_state(value, benefits_type, benefits_state, "pensions and benefits evidence")
        present, absent = state["present_fields"], state["absent_fields"]
        if exact_type(present) is not frozenset_type or exact_type(absent) is not frozenset_type:
            raise fail("benefit presence sets must be exact frozensets")
        for names in (present, absent):
            if any_value(
                exact_type(name) is not str_type or name not in benefits_documented
                for name in names
            ):
                raise fail("benefit presence sets contain an invalid member")
        if present & absent or present | absent != benefits_documented:
            raise fail("benefit presence and absence must be coherent and exhaustive")
        for source_name, field_name in benefit_fields:
            retained = state[field_name]
            if source_name in present:
                if retained is None:
                    raise fail("present benefit must retain an exact number")
                number(retained, source_name)
            elif retained is not None:
                raise fail("absent benefit must remain absent, not zero")
        unknown_names(state["unknown_names"], "benefits unknown names", benefits_documented)
        return value

    def validate_time(value: object):
        if exact_type(value) is not datetime_type or exact_type(value.tzinfo) is not timezone_type:
            raise fail("observed_at must be an aware built-in fixed-offset datetime")
        return value

    def validate_digest(value: object):
        if exact_type(value) is not str_type or digest_match(value) is None:  # type: ignore[operator]
            raise fail("source artifact digest must be lowercase SHA-256 hex")
        return value

    def validate_evidence(value: object):
        state = exact_state(value, evidence_type, evidence_state, "source evidence bundle")
        if exact_type(state["source_api_name"]) is not str_type or state["source_api_name"] != expected_api:
            raise fail("source API name is not exact")
        if exact_type(state["source_api_version"]) is not str_type or state["source_api_version"] != expected_version:
            raise fail("source API version is not exact")
        if exact_type(state["tax_year"]) is not str_type or tax_year_match(state["tax_year"]) is None:  # type: ignore[operator]
            raise fail("tax year must match YYYY-YY exactly")
        employments = state["employments"]
        if exact_type(employments) is not tuple_type or length(employments) > max_employments:
            raise fail("employments must be an exact bounded tuple")
        for item in employments:
            validate_employment(item)
        validate_benefits(state["pensions_benefits"])
        safe_text(state["evidence_reference"], "evidence reference", max_reference, True)
        validate_time(state["observed_at"])
        if exact_type(state["completeness"]) is not str_type or state["completeness"] != expected_completeness:
            raise fail("completeness must be exactly UNVERIFIED")
        unknown_names(state["unknown_names"], "top-level unknown names", top_documented)
        if state["_source_artifact_sha256_state"] is not unset:
            validate_digest(state["_source_artifact_sha256_state"])
        return value

    def parse(fields: tuple[str, ...], required: int, args: tuple, kwargs: dict, defaults: tuple):
        if length(args) > length(fields) or any_value(exact_type(key) is not str_type for key in kwargs):
            raise fail("constructor arguments are not the exact supported shape")
        values: dict[str, object] = {}
        for index, value in enumerate_values(args):
            values[fields[index]] = value
        for key, value in kwargs.items():
            if key not in fields or key in values:
                raise fail("constructor arguments are not the exact supported shape")
            values[key] = value
        for index, name in enumerate_values(fields):
            if name not in values:
                if index < required:
                    raise fail("constructor arguments are not the exact supported shape")
                values[name] = defaults[index - required]
        return values

    employment_fields = ("employer_paye_reference", "pay_from_employment", "unknown_names")
    def employment_init(self, *args, **kwargs):
        values = parse(employment_fields, 2, args, kwargs, (empty_names,))
        for name in employment_fields:
            put(self, name, values[name])
        validate_employment(self)

    benefits_fields = tuple_type(name for _, name in benefit_fields) + ("present_fields", "absent_fields", "unknown_names")
    benefits_defaults = (None, None, None, None, empty_names, empty_names, empty_names)
    def benefits_init(self, *args, **kwargs):
        values = parse(benefits_fields, 0, args, kwargs, benefits_defaults)
        for name in benefits_fields:
            put(self, name, values[name])
        validate_benefits(self)

    evidence_fields = (
        "source_api_name", "source_api_version", "tax_year", "employments",
        "pensions_benefits", "evidence_reference", "observed_at", "completeness",
        "source_artifact_sha256", "unknown_names", "_source_artifact_sha256_state",
    )
    evidence_defaults = (expected_completeness, unset, empty_names, unset)
    def evidence_init(self, *args, **kwargs):
        values = parse(evidence_fields, 7, args, kwargs, evidence_defaults)
        supplied = values["source_artifact_sha256"]
        retained = values["_source_artifact_sha256_state"] if supplied is unset else supplied
        for name in evidence_fields[:8]:
            put(self, name, values[name])
        put(self, "unknown_names", values["unknown_names"])
        put(self, "_source_artifact_sha256_state", retained)
        validate_evidence(self)

    def employment_copy(self):
        validate_employment(self); return self
    def employment_deepcopy(self, memo):
        validate_employment(self); return self
    def employment_reduce(self, protocol):
        validate_employment(self)
        return (employment_type, tuple_type(get(self, name) for name in employment_fields))
    def benefits_copy(self):
        validate_benefits(self); return self
    def benefits_deepcopy(self, memo):
        validate_benefits(self); return self
    def benefits_reduce(self, protocol):
        validate_benefits(self)
        return (benefits_type, tuple_type(get(self, name) for name in benefits_fields))

    def restore(*args):
        if length(args) != 11 or exact_type(args[9]) is not bool_type:
            raise fail("serialized evidence state is invalid")
        kwargs = {"unknown_names": args[8]}
        if args[9]:
            kwargs["source_artifact_sha256"] = args[10]
        return evidence_type(*args[:8], **kwargs)

    def evidence_copy(self):
        validate_evidence(self); return self
    def evidence_deepcopy(self, memo):
        validate_evidence(self); return self
    def evidence_reduce(self, protocol):
        validate_evidence(self)
        retained = get(self, "_source_artifact_sha256_state")
        return (restore, (
            get(self, "source_api_name"), get(self, "source_api_version"),
            get(self, "tax_year"), get(self, "employments"),
            get(self, "pensions_benefits"), get(self, "evidence_reference"),
            get(self, "observed_at"), get(self, "completeness"),
            get(self, "unknown_names"), retained is not unset,
            None if retained is unset else retained,
        ))
    def digest_property(self):
        validate_evidence(self)
        retained = get(self, "_source_artifact_sha256_state")
        return None if retained is unset else retained

    def builder(observation: object, *args: object, **kwargs: object):
        if args or set_type(kwargs) - {"evidence_reference", "observed_at", "source_artifact_sha256"} \
                or "evidence_reference" not in kwargs or "observed_at" not in kwargs:
            raise fail("builder arguments are not the exact supported shape")
        try:
            validated = source_validator(observation)  # type: ignore[operator]
        except source_error_type as exc:
            raise fail("source observation is invalid") from exc
        reference = safe_text(kwargs["evidence_reference"], "evidence reference", max_reference, True)
        observed = validate_time(kwargs["observed_at"])
        digest_kwargs = {}
        if "source_artifact_sha256" in kwargs:
            digest_kwargs["source_artifact_sha256"] = validate_digest(kwargs["source_artifact_sha256"])
        employments = tuple_type(employment_type(
            get(item, "employer_paye_reference"), get(item, "pay_from_employment"),
            get(item, "unknown_names"),
        ) for item in get(validated, "employments"))
        source_benefits = get(validated, "pensions_benefits")
        benefits = benefits_type(*(get(source_benefits, name) for name in benefits_fields))
        return evidence_type(
            expected_api, expected_version, get(validated, "tax_year"), employments,
            benefits, reference, observed, expected_completeness,
            unknown_names=get(validated, "unknown_names"), **digest_kwargs,
        )

    employment_type.__init__ = employment_init
    employment_type.__post_init__ = lambda self: validate_employment(self)
    employment_type.__copy__ = employment_copy
    employment_type.__deepcopy__ = employment_deepcopy
    employment_type.__reduce_ex__ = employment_reduce
    benefits_type.__init__ = benefits_init
    benefits_type.__post_init__ = lambda self: validate_benefits(self)
    benefits_type.__copy__ = benefits_copy
    benefits_type.__deepcopy__ = benefits_deepcopy
    benefits_type.__reduce_ex__ = benefits_reduce
    evidence_type.__init__ = evidence_init
    evidence_type.__copy__ = evidence_copy
    evidence_type.__deepcopy__ = evidence_deepcopy
    evidence_type.__reduce_ex__ = evidence_reduce
    evidence_type.source_artifact_sha256 = property(digest_property)
    restore.__name__ = "_hardened_restore_evidence"
    restore.__qualname__ = "_hardened_restore_evidence"
    return builder, validate_employment, validate_benefits, validate_evidence, restore


(
    build_hmrc_individual_income_source_evidence,
    _validate_employment,
    _validate_benefits,
    _validate_evidence,
    _hardened_restore_evidence,
) = _bind_hardened_source_boundary(
    IndividualIncomeEmploymentSourceEvidence,
    IndividualIncomePensionsBenefitsSourceEvidence,
    HMRCIndividualIncomeSourceEvidence,
    validate_individual_income_annual_summary_observation,
    HMRCIndividualIncomeContractError,
    HMRCIndividualIncomeSourceEvidenceError,
    Decimal, datetime, timezone, int, str, tuple, frozenset, dict, bool,
    _TAX_YEAR_RE.fullmatch, _SHA256_RE.fullmatch, unicodedata.category,
    HMRC_INDIVIDUAL_INCOME_API, HMRC_INDIVIDUAL_INCOME_API_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS, _UNSET,
    _EMPLOYMENT_STATE, _BENEFITS_STATE, _EVIDENCE_STATE,
    _TOP_DOCUMENTED, _EMPLOYMENT_DOCUMENTED, _BENEFITS_DOCUMENTED,
    _BENEFIT_FIELDS, RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH,
    _MAX_EMPLOYMENTS, _MAX_UNKNOWN_NAMES, _MAX_NAME_LENGTH, _MAX_STRING_LENGTH,
    _MAX_DIGITS, _MAX_PLACES, _MAX_INT, _MAX_MAGNITUDE,
)


__all__ = (
    "RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH",
    "HMRCIndividualIncomeSourceEvidenceError",
    "IndividualIncomeEmploymentSourceEvidence",
    "IndividualIncomePensionsBenefitsSourceEvidence",
    "HMRCIndividualIncomeSourceEvidence",
    "build_hmrc_individual_income_source_evidence",
)
