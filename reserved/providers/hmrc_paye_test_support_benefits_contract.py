"""Network-inert contract for one HMRC PAYE Test Support 2.1 operation.

Only the synthetic, Sandbox-only ``createBenefitsSummaryTestData`` request
intent and documented HTTP 201 response are represented.  There is no HTTP,
OAuth, credential, persistence, activation, read-side, tax/HICBC calculation,
or product-engine integration surface here.  Unknown extension values are
never fetched or retained; only bounded safe member names are recorded.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal

API_NAME = "Individual PAYE Test Support"
API_VERSION = "2.1"
API_BETA = True
SANDBOX_ONLY = True
HTTP_METHOD = "POST"
PATH_TEMPLATE = "/individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}"
OPERATION_ID = "createBenefitsSummaryTestData"
REQUEST_ACCEPT = "application/vnd.hmrc.2.1+json"
REQUEST_CONTENT_TYPE = "application/json"
RESPONSE_CONTENT_TYPE = "application/json"
SUCCESS_STATUS = 201
COMPLETENESS = "UNVERIFIED"
SCENARIOS = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2"})

# Reserved safety limits, not HMRC/provider rules.
RESERVED_MAX_OBJECT_MEMBERS = 64
RESERVED_MAX_UNKNOWN_NAMES = 32
RESERVED_MAX_MEMBER_NAME_LENGTH = 256
RESERVED_MAX_EMPLOYER_REFERENCE_LENGTH = 4096
RESERVED_MAX_EMPLOYMENTS = 10_000
RESERVED_MAX_INTEGER_ABS = 10**18
RESERVED_MAX_DECIMAL_DIGITS = 38
RESERVED_MAX_DECIMAL_PLACES = 12
RESERVED_MAX_DECIMAL_ABS = Decimal("1000000000000000000")

_OMITTED = object()
_UTR = re.compile(r"[0-9]{10}", re.ASCII)
_TAX_YEAR = re.compile(r"[0-9]{4}-[0-9]{2}", re.ASCII)
_TOP_NAMES = frozenset({"employments"})
_NUMERIC_NAMES = (
    "companyCarsAndVansBenefit",
    "fuelForCompanyCarsAndVansBenefit",
    "privateMedicalDentalInsurance",
    "vouchersCreditCardsExcessMileageAllowance",
    "goodsEtcProvidedByEmployer",
    "accommodationProvidedByEmployer",
    "otherBenefits",
    "expensesPaymentsReceived",
)
_EMPLOYMENT_NAMES = frozenset(("employerPayeReference",) + _NUMERIC_NAMES)


class HMRCPAYETestSupportBenefitsContractError(ValueError):
    """A value failed the bounded literal contract."""


def _fail(message: str) -> HMRCPAYETestSupportBenefitsContractError:
    return HMRCPAYETestSupportBenefitsContractError(
        f"HMRC PAYE test-support benefits contract: {message}"
    )


def _safe_string(value: object, field_name: str, limit: int, *, empty: bool) -> str:
    if type(value) is not str:
        raise _fail(f"{field_name} must be an exact built-in string")
    if not empty and not value:
        raise _fail(f"{field_name} must not be empty")
    if len(value) > limit:
        raise _fail(f"{field_name} exceeds the Reserved safety limit")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise _fail(f"{field_name} contains an unsafe category-C character")
    return value


def _number(value: object, field_name: str) -> int | Decimal:
    if type(value) is int:
        if abs(value) > RESERVED_MAX_INTEGER_ABS:
            raise _fail(f"{field_name} exceeds the Reserved integer limit")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise _fail(f"{field_name} must be finite")
        sign, digits, exponent = value.as_tuple()
        places = max(0, -exponent)
        integer_digits = max(1, len(digits) + exponent)
        if (len(digits) > RESERVED_MAX_DECIMAL_DIGITS
                or places > RESERVED_MAX_DECIMAL_PLACES
                or integer_digits > RESERVED_MAX_DECIMAL_DIGITS
                or abs(value) > RESERVED_MAX_DECIMAL_ABS):
            raise _fail(f"{field_name} exceeds a Reserved decimal-shape limit")
        return value
    raise _fail(f"{field_name} must be an exact built-in int or Decimal")


def _unknown_names(value: object, known: frozenset[str], context: str) -> frozenset[str]:
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown_names must be an exact frozenset")
    if len(value) > RESERVED_MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the Reserved unknown-name limit")
    for name in value:
        _safe_string(name, f"{context} member name", RESERVED_MAX_MEMBER_NAME_LENGTH, empty=False)
        if name in known:
            raise _fail(f"{context} unknown_names contains a documented name")
    return value


def _classify(value: object, known: frozenset[str], context: str) -> tuple[dict, frozenset[str]]:
    if type(value) is not dict:
        raise _fail(f"{context} must be an exact built-in object")
    if len(value) > RESERVED_MAX_OBJECT_MEMBERS:
        raise _fail(f"{context} exceeds the Reserved object-member limit")
    unknown: list[str] = []
    # Validate every name before membership classification. Iteration does not
    # retrieve, compare, stringify, copy, traverse, or retain unknown values.
    for name in value:
        _safe_string(name, f"{context} member name", RESERVED_MAX_MEMBER_NAME_LENGTH, empty=False)
        if name not in known:
            unknown.append(name)
    if len(unknown) > RESERVED_MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the Reserved unknown-name limit")
    return value, frozenset(unknown)


@dataclass(frozen=True, repr=False)
class BenefitsSummaryRequestIntent:
    """UTR-free, non-sendable request intent; omission differs from null."""

    utr: InitVar[str]
    tax_year: str
    scenario: str | None = _OMITTED
    scenario_present: bool = field(init=False, default=False)

    def __post_init__(self, utr: str) -> None:
        if type(utr) is not str or _UTR.fullmatch(utr) is None:
            raise _fail("utr must be exactly ten ASCII digits")
        if type(self.tax_year) is not str or _TAX_YEAR.fullmatch(self.tax_year) is None:
            raise _fail("tax_year must match YYYY-YY using ASCII digits")
        if self.scenario is _OMITTED:
            object.__setattr__(self, "scenario", None)
            object.__setattr__(self, "scenario_present", False)
        else:
            if type(self.scenario) is not str or self.scenario not in SCENARIOS:
                raise _fail("scenario must be HAPPY_PATH_1 or HAPPY_PATH_2")
            object.__setattr__(self, "scenario_present", True)

    def __repr__(self) -> str:
        return "BenefitsSummaryRequestIntent([REDACTED])"

    def __reduce__(self) -> object:
        return (_fresh_intent, (self.tax_year, self.scenario, self.scenario_present))


def build_benefits_summary_request(*, utr: str, tax_year: str,
                                   scenario: object = _OMITTED) -> BenefitsSummaryRequestIntent:
    if scenario is _OMITTED:
        return BenefitsSummaryRequestIntent(utr=utr, tax_year=tax_year)
    return BenefitsSummaryRequestIntent(utr=utr, tax_year=tax_year, scenario=scenario)


@dataclass(frozen=True, repr=False)
class BenefitsEmployment:
    employer_paye_reference: str
    company_cars_and_vans_benefit: int | Decimal | None = None
    fuel_for_company_cars_and_vans_benefit: int | Decimal | None = None
    private_medical_dental_insurance: int | Decimal | None = None
    vouchers_credit_cards_excess_mileage_allowance: int | Decimal | None = None
    goods_etc_provided_by_employer: int | Decimal | None = None
    accommodation_provided_by_employer: int | Decimal | None = None
    other_benefits: int | Decimal | None = None
    expenses_payments_received: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _safe_string(self.employer_paye_reference, "employerPayeReference",
                     RESERVED_MAX_EMPLOYER_REFERENCE_LENGTH, empty=True)
        if type(self.present_fields) is not frozenset or not self.present_fields <= frozenset(_NUMERIC_NAMES):
            raise _fail("present_fields must be an exact documented-name frozenset")
        for name, value in zip(_NUMERIC_NAMES, self._values()):
            if name in self.present_fields:
                if value is None:
                    raise _fail(f"{name} must not be null when present")
                _number(value, name)
            elif value is not None:
                raise _fail(f"{name} must be None when omitted")
        _unknown_names(self.unknown_names, _EMPLOYMENT_NAMES, "employment")

    def _values(self) -> tuple[int | Decimal | None, ...]:
        return (self.company_cars_and_vans_benefit,
                self.fuel_for_company_cars_and_vans_benefit,
                self.private_medical_dental_insurance,
                self.vouchers_credit_cards_excess_mileage_allowance,
                self.goods_etc_provided_by_employer,
                self.accommodation_provided_by_employer,
                self.other_benefits, self.expenses_payments_received)

    @property
    def absent_fields(self) -> frozenset[str]:
        return frozenset(_NUMERIC_NAMES) - self.present_fields

    def __repr__(self) -> str:
        return "BenefitsEmployment([REDACTED])"

    def __copy__(self) -> BenefitsEmployment:
        return self

    def __deepcopy__(self, memo: dict) -> BenefitsEmployment:
        return self

    def __reduce__(self) -> object:
        return (_rebuild_employment, (self.employer_paye_reference, self._values(),
                                     self.present_fields, self.unknown_names))


@dataclass(frozen=True, repr=False)
class BenefitsSummaryCreated:
    """Immutable fixture observation bound to a validated request intent."""

    request: InitVar[BenefitsSummaryRequestIntent]
    employments: tuple[BenefitsEmployment, ...]
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)
    status_code: int = SUCCESS_STATUS
    content_type: str = RESPONSE_CONTENT_TYPE
    unknown_names: frozenset[str] = frozenset()
    completeness: str = COMPLETENESS

    def __post_init__(self, request: BenefitsSummaryRequestIntent) -> None:
        if type(request) is not BenefitsSummaryRequestIntent:
            raise _fail("request must be an exact validated BenefitsSummaryRequestIntent")
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "scenario", request.scenario)
        object.__setattr__(self, "scenario_present", request.scenario_present)
        if type(self.status_code) is not int or self.status_code != SUCCESS_STATUS:
            raise _fail("status_code must be the exact built-in integer 201")
        if type(self.content_type) is not str or self.content_type != RESPONSE_CONTENT_TYPE:
            raise _fail("content_type must be exact application/json")
        if type(self.employments) is not tuple or not (1 <= len(self.employments) <= RESERVED_MAX_EMPLOYMENTS):
            raise _fail("employments must be a bounded non-empty exact tuple")
        if any(type(item) is not BenefitsEmployment for item in self.employments):
            raise _fail("employments must contain exact BenefitsEmployment values")
        _unknown_names(self.unknown_names, _TOP_NAMES, "top level")
        if type(self.completeness) is not str or self.completeness != COMPLETENESS:
            raise _fail("completeness must be exactly UNVERIFIED")

    def __repr__(self) -> str:
        return "BenefitsSummaryCreated([REDACTED])"

    def __copy__(self) -> BenefitsSummaryCreated:
        return self

    def __deepcopy__(self, memo: dict) -> BenefitsSummaryCreated:
        return self

    def __reduce__(self) -> object:
        return (_rebuild_summary, (self.tax_year, self.scenario, self.scenario_present,
                                  self.employments, self.status_code, self.content_type,
                                  self.unknown_names, self.completeness))


def _fresh_intent(tax_year: str, scenario: str | None, present: bool) -> BenefitsSummaryRequestIntent:
    if type(present) is not bool:
        raise _fail("scenario_present must be an exact bool")
    if present:
        return BenefitsSummaryRequestIntent(utr="0000000000", tax_year=tax_year, scenario=scenario)
    if scenario is not None:
        raise _fail("an omitted scenario must have value None")
    return BenefitsSummaryRequestIntent(utr="0000000000", tax_year=tax_year)


def _rebuild_employment(reference: str, values: tuple[int | Decimal | None, ...],
                        present_fields: frozenset[str],
                        unknown_names: frozenset[str]) -> BenefitsEmployment:
    if type(values) is not tuple or len(values) != len(_NUMERIC_NAMES):
        raise _fail("serialized employment numeric shape is invalid")
    return BenefitsEmployment(reference, *values, present_fields=present_fields,
                              unknown_names=unknown_names)


def _rebuild_summary(tax_year: str, scenario: str | None, scenario_present: bool,
                     employments: tuple[BenefitsEmployment, ...], status_code: int,
                     content_type: str, unknown_names: frozenset[str],
                     completeness: str) -> BenefitsSummaryCreated:
    return BenefitsSummaryCreated(_fresh_intent(tax_year, scenario, scenario_present),
                                  employments, status_code=status_code,
                                  content_type=content_type, unknown_names=unknown_names,
                                  completeness=completeness)


def _parse_employment(raw: object) -> BenefitsEmployment:
    obj, unknown = _classify(raw, _EMPLOYMENT_NAMES, "employment")
    if "employerPayeReference" not in obj:
        raise _fail("employment is missing employerPayeReference")
    reference = _safe_string(obj["employerPayeReference"], "employerPayeReference",
                             RESERVED_MAX_EMPLOYER_REFERENCE_LENGTH, empty=True)
    present = frozenset(name for name in _NUMERIC_NAMES if name in obj)
    values = {name: _number(obj[name], name) for name in present}
    return BenefitsEmployment(reference, *(values.get(name) for name in _NUMERIC_NAMES),
                              present_fields=present, unknown_names=unknown)


def observe_benefits_summary_response(request: BenefitsSummaryRequestIntent, *,
                                      status_code: int, content_type: object,
                                      payload: object) -> BenefitsSummaryCreated:
    """Validate 201 evidence; non-201 rejects before touching content/body."""
    if type(request) is not BenefitsSummaryRequestIntent:
        raise _fail("request must be an exact validated BenefitsSummaryRequestIntent")
    if type(status_code) is not int or status_code != SUCCESS_STATUS:
        raise _fail("status_code must be the exact built-in integer 201")
    if type(content_type) is not str or content_type != RESPONSE_CONTENT_TYPE:
        raise _fail("content_type must be exact application/json")
    obj, unknown = _classify(payload, _TOP_NAMES, "top level")
    if "employments" not in obj:
        raise _fail("top level is missing employments")
    raw_employments = obj["employments"]
    if type(raw_employments) is not list or not (1 <= len(raw_employments) <= RESERVED_MAX_EMPLOYMENTS):
        raise _fail("employments must be a bounded non-empty exact array")
    employments = tuple(_parse_employment(raw) for raw in raw_employments)
    return BenefitsSummaryCreated(request, employments, unknown_names=unknown)


__all__ = ["HMRCPAYETestSupportBenefitsContractError", "BenefitsSummaryRequestIntent",
           "BenefitsEmployment", "BenefitsSummaryCreated", "build_benefits_summary_request",
           "observe_benefits_summary_response"]
