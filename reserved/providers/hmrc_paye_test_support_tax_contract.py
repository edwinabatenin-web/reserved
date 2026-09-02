"""Network-inert contract for the PAYE Test Support 2.1 tax HTTP 201 body.

This module is only a typed parser/value boundary for synthetic sandbox
evidence.  It has no HTTP, OAuth, credential, persistence, activation or
read-side path.  Unknown extension values are deliberately ignored: only their
bounded, safe member names are retained.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

HTTP_METHOD = "POST"
PATH_TEMPLATE = "/individual-paye-test-support/sa/{utr}/tax/annual-summary/{taxYear}"
API_VERSION = "2.1"
SCENARIOS = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2"})
DEFAULT_SCENARIO = "HAPPY_PATH_1"
SUCCESS_STATUS = 201

_TOP_NAMES = frozenset({"employments", "pensionsAnnuitiesAndOtherStateBenefits", "refunds"})
_EMPLOYMENT_NAMES = frozenset({"employerPayeReference", "taxTakenOffPay"})
_PENSIONS_NAMES = frozenset({"otherPensionsAndRetirementAnnuities", "incapacityBenefit"})
_REFUND_NAMES = frozenset({"taxRefundedOrSetOff"})
_MAX_MEMBERS = 64
_MAX_UNKNOWN_NAMES = 32
_MAX_NAME_LENGTH = 256
_MAX_STRING_LENGTH = 4096
_MAX_EMPLOYMENTS = 10_000
_MAX_DIGITS = 38
_MAX_PLACES = 12
_MAX_MAGNITUDE = Decimal("1000000000000000000")
_OMITTED = object()


class HMRCPAYETestSupportTaxContractError(ValueError):
    """Fail-closed error which never incorporates supplied evidence values."""


def _fail(message: str) -> HMRCPAYETestSupportTaxContractError:
    return HMRCPAYETestSupportTaxContractError(f"HMRC PAYE test-support tax contract: {message}")


def _safe_text(value: object, field: str, *, empty: bool) -> str:
    if type(value) is not str:
        raise _fail(f"{field} must be an exact built-in string")
    if not empty and not value:
        raise _fail(f"{field} must not be empty")
    limit = _MAX_STRING_LENGTH if field == "employerPayeReference" else _MAX_NAME_LENGTH
    if len(value) > limit:
        raise _fail(f"{field} exceeds its reserved length bound")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise _fail(f"{field} contains an unsafe control/format character")
    return value


def _number(value: object, field: str) -> int | Decimal:
    if type(value) is int:
        if abs(value) > 10**18:
            raise _fail(f"{field} exceeds the reserved magnitude bound")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise _fail(f"{field} must be finite")
        parts = value.as_tuple()
        places = max(0, -parts.exponent)
        integer_digits = max(1, len(parts.digits) + parts.exponent)
        if (abs(value) > _MAX_MAGNITUDE or len(parts.digits) > _MAX_DIGITS
                or places > _MAX_PLACES or integer_digits > _MAX_DIGITS):
            raise _fail(f"{field} exceeds the reserved decimal bound")
        return value
    raise _fail(f"{field} must be an exact built-in int or Decimal")


def _unknown_names(value: object, known: frozenset[str], context: str) -> frozenset[str]:
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown_names must be an exact frozenset")
    if len(value) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the unknown-name bound")
    for name in value:
        _safe_text(name, f"{context} member name", empty=False)
        if name in known:
            raise _fail(f"{context} unknown_names contains a documented name")
    return value


def _classify(obj: object, known: frozenset[str], context: str) -> tuple[dict, frozenset[str]]:
    if type(obj) is not dict:
        raise _fail(f"{context} must be an exact built-in object")
    if len(obj) > _MAX_MEMBERS:
        raise _fail(f"{context} exceeds the object-member bound")
    unknown = []
    for name in obj:  # values of unknown members are never fetched or inspected
        _safe_text(name, f"{context} member name", empty=False)
        if name not in known:
            unknown.append(name)
    if len(unknown) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the unknown-name bound")
    return obj, frozenset(unknown)


def _scenario(value: object) -> str:
    if type(value) is not str or value not in SCENARIOS:
        raise _fail("scenario must be HAPPY_PATH_1 or HAPPY_PATH_2")
    return value


def _presence(present: object, known: frozenset[str], context: str) -> frozenset[str]:
    if type(present) is not frozenset or not present <= known:
        raise _fail(f"{context} present_fields must be an exact documented-name frozenset")
    return present


@dataclass(frozen=True, repr=False)
class TaxTestSupportRequest:
    scenario: str = DEFAULT_SCENARIO

    def __post_init__(self) -> None:
        _scenario(self.scenario)

    def __repr__(self) -> str:
        return f"TaxTestSupportRequest(scenario={self.scenario!r})"


@dataclass(frozen=True, repr=False)
class TaxEmployment:
    employer_paye_reference: str
    tax_taken_off_pay: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _safe_text(self.employer_paye_reference, "employerPayeReference", empty=True)
        _number(self.tax_taken_off_pay, "taxTakenOffPay")
        _unknown_names(self.unknown_names, _EMPLOYMENT_NAMES, "employment")

    def __repr__(self) -> str:
        return "TaxEmployment([REDACTED])"


@dataclass(frozen=True, repr=False)
class PensionsBenefits:
    other_pensions_and_retirement_annuities: int | Decimal | None = None
    incapacity_benefit: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        present = _presence(self.present_fields, _PENSIONS_NAMES, "pensions/benefits")
        for name, value in (("otherPensionsAndRetirementAnnuities", self.other_pensions_and_retirement_annuities),
                            ("incapacityBenefit", self.incapacity_benefit)):
            if name in present:
                if value is None:
                    raise _fail(f"{name} must not be None when present")
                _number(value, name)
            elif value is not None:
                raise _fail(f"{name} must be None when absent")
        _unknown_names(self.unknown_names, _PENSIONS_NAMES, "pensions/benefits")

    @property
    def absent_fields(self) -> frozenset[str]:
        return _PENSIONS_NAMES - self.present_fields

    def __repr__(self) -> str:
        return "PensionsBenefits([REDACTED])"


@dataclass(frozen=True, repr=False)
class Refunds:
    tax_refunded_or_set_off: int | Decimal | None = None
    present_fields: frozenset[str] = frozenset()
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        present = _presence(self.present_fields, _REFUND_NAMES, "refunds")
        if "taxRefundedOrSetOff" in present:
            if self.tax_refunded_or_set_off is None:
                raise _fail("taxRefundedOrSetOff must not be None when present")
            _number(self.tax_refunded_or_set_off, "taxRefundedOrSetOff")
        elif self.tax_refunded_or_set_off is not None:
            raise _fail("taxRefundedOrSetOff must be None when absent")
        _unknown_names(self.unknown_names, _REFUND_NAMES, "refunds")

    @property
    def absent_fields(self) -> frozenset[str]:
        return _REFUND_NAMES - self.present_fields

    def __repr__(self) -> str:
        return "Refunds([REDACTED])"


@dataclass(frozen=True, repr=False)
class TaxSummaryCreated:
    employments: tuple[TaxEmployment, ...]
    pensions_benefits: PensionsBenefits
    refunds: Refunds
    status_code: int = SUCCESS_STATUS
    scenario: str = DEFAULT_SCENARIO
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self.status_code) is not int or self.status_code != SUCCESS_STATUS:
            raise _fail("status_code must be the exact built-in integer 201")
        _scenario(self.scenario)
        if type(self.employments) is not tuple or len(self.employments) > _MAX_EMPLOYMENTS:
            raise _fail("employments must be a bounded exact built-in tuple")
        if any(type(item) is not TaxEmployment for item in self.employments):
            raise _fail("employments must contain exact TaxEmployment values")
        if type(self.pensions_benefits) is not PensionsBenefits:
            raise _fail("pensions_benefits must be an exact PensionsBenefits value")
        if type(self.refunds) is not Refunds:
            raise _fail("refunds must be an exact Refunds value")
        _unknown_names(self.unknown_names, _TOP_NAMES, "top level")

    def __repr__(self) -> str:
        return f"TaxSummaryCreated(status_code=201, scenario={self.scenario!r}, [REDACTED])"


def parse_tax_test_support_request(payload: object) -> TaxTestSupportRequest:
    obj, unknown = _classify(payload, frozenset({"scenario"}), "request")
    if unknown:
        raise _fail("request contains an undocumented member")
    scenario = DEFAULT_SCENARIO if "scenario" not in obj else _scenario(obj["scenario"])
    return TaxTestSupportRequest(scenario=scenario)


def _parse_pensions(value: object) -> PensionsBenefits:
    obj, unknown = _classify(value, _PENSIONS_NAMES, "pensions/benefits")
    present = frozenset(obj.keys() & _PENSIONS_NAMES)
    values = {name: _number(obj[name], name) for name in present}
    return PensionsBenefits(values.get("otherPensionsAndRetirementAnnuities"),
                            values.get("incapacityBenefit"), present, unknown)


def _parse_refunds(value: object) -> Refunds:
    obj, unknown = _classify(value, _REFUND_NAMES, "refunds")
    present = frozenset(obj.keys() & _REFUND_NAMES)
    value = _number(obj["taxRefundedOrSetOff"], "taxRefundedOrSetOff") if present else None
    return Refunds(value, present, unknown)


def parse_tax_summary_created(payload: object, *, status_code: int,
                              scenario: object = _OMITTED) -> TaxSummaryCreated:
    """Parse a documented 201 body; omission alone selects the default scenario."""
    if type(status_code) is not int or status_code != SUCCESS_STATUS:
        raise _fail("status_code must be the exact built-in integer 201")
    selected = DEFAULT_SCENARIO if scenario is _OMITTED else _scenario(scenario)
    obj, unknown = _classify(payload, _TOP_NAMES, "top level")
    missing = _TOP_NAMES - obj.keys()
    if missing:
        raise _fail("top level is missing a required documented member")
    employments_raw = obj["employments"]
    if type(employments_raw) is not list or len(employments_raw) > _MAX_EMPLOYMENTS:
        raise _fail("employments must be a bounded exact built-in array")
    employments = []
    for raw in employments_raw:
        item, item_unknown = _classify(raw, _EMPLOYMENT_NAMES, "employment")
        if not _EMPLOYMENT_NAMES <= item.keys():
            raise _fail("employment is missing a required documented member")
        employments.append(TaxEmployment(
            _safe_text(item["employerPayeReference"], "employerPayeReference", empty=True),
            _number(item["taxTakenOffPay"], "taxTakenOffPay"), item_unknown))
    return TaxSummaryCreated(tuple(employments),
                             _parse_pensions(obj["pensionsAnnuitiesAndOtherStateBenefits"]),
                             _parse_refunds(obj["refunds"]), status_code, selected, unknown)


__all__ = ["HMRCPAYETestSupportTaxContractError", "TaxTestSupportRequest",
           "TaxEmployment", "PensionsBenefits", "Refunds", "TaxSummaryCreated",
           "parse_tax_test_support_request", "parse_tax_summary_created"]
