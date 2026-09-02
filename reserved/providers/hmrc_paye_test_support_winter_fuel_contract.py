"""Disabled, offline HMRC PAYE Test Support 2.1 Winter Fuel contract.

This module models only the retained literal request intent and response
observation for ``createWinterFuelPaymentAmountTestData``.  It has no HTTP,
credential, persistence, dispatch, product, accounting or activation surface.
The supplied NINO is validated and immediately discarded.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal


OPERATION_ID = "createWinterFuelPaymentAmountTestData"
HTTP_METHOD = "POST"
PATH_TEMPLATE = (
    "/individual-paye-test-support/{nino}/winter-fuel-payment-amount/"
    "annual-summary/{taxYear}"
)
API_VERSION = "2.1"
ACCEPT = "application/vnd.hmrc.2.1+json"
JSON_CONTENT_TYPE = "application/json"
SUCCESS_STATUS = 201
OAUTH_GRANT_TYPE = "client_credentials"
OAUTH_SCOPES = frozenset()
SANDBOX_ONLY = True
SCENARIOS = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2", "UNHAPPY_PATH_500"})
COMPLETENESS = "UNVERIFIED"

_TOP_NAMES = frozenset({"expectedStatus", "expectedJson"})
_EXPECTED_JSON_NAMES = frozenset({"winterFuelPaymentAmount"})
_MAX_OBJECT_MEMBERS = 64
_MAX_UNKNOWN_NAMES = 32
_MAX_NAME_LENGTH = 256
_MAX_DECIMAL_DIGITS = 38
_MAX_DECIMAL_PLACES = 12
_MAX_NUMBER_MAGNITUDE = Decimal("1000000000000000000")
_MAX_INT_MAGNITUDE = 10**18
_NINO_RE = re.compile(r"[A-Z]{2}[0-9]{6}[A-Z]")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
_SCENARIO_OMITTED = object()


class HMRCPayeTestSupportWinterFuelContractError(ValueError):
    """Controlled validation error that never echoes supplied data."""


def _fail(rule: str) -> HMRCPayeTestSupportWinterFuelContractError:
    return HMRCPayeTestSupportWinterFuelContractError(
        f"HMRC PAYE Test Support Winter Fuel contract: {rule}"
    )


def _safe_name(value: object, context: str) -> str:
    if type(value) is not str:
        raise _fail(f"{context} member names must be exact built-in strings")
    if not value or len(value) > _MAX_NAME_LENGTH:
        raise _fail(f"{context} member name is empty or exceeds the reserved bound")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise _fail(f"{context} member name contains an unsafe category-C character")
    return value


def _unknown_names(obj: dict, documented: frozenset[str], context: str) -> frozenset[str]:
    if len(obj) > _MAX_OBJECT_MEMBERS:
        raise _fail(f"{context} exceeds the reserved member bound")
    # Validate every name before known/unknown classification. Values are never read.
    names = [_safe_name(name, context) for name in obj]
    result = [name for name in names if name not in documented]
    if len(result) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the reserved unknown-name bound")
    return frozenset(result)


def _validate_unknown_names(
    value: object, documented: frozenset[str], context: str
) -> frozenset[str]:
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown_names must be an exact frozenset")
    if len(value) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the reserved unknown-name bound")
    for name in value:
        _safe_name(name, context)
    if value & documented:
        raise _fail(f"{context} unknown_names contains a documented member name")
    return value


def _number(value: object, field_name: str) -> int | Decimal:
    if type(value) is int:
        if value > _MAX_INT_MAGNITUDE or value < -_MAX_INT_MAGNITUDE:
            raise _fail(f"{field_name} exceeds the reserved numeric bound")
        return value
    if type(value) is not Decimal:
        raise _fail(f"{field_name} must be an exact built-in int or Decimal")
    if not value.is_finite():
        raise _fail(f"{field_name} must be finite")
    parts = value.as_tuple()
    places = max(0, -parts.exponent)
    # Reserved defensive bound: limit positive-exponent/integer numeric shape.
    integer_digits = max(1, len(parts.digits) + parts.exponent)
    if (
        len(parts.digits) > _MAX_DECIMAL_DIGITS
        or places > _MAX_DECIMAL_PLACES
        or integer_digits > _MAX_DECIMAL_DIGITS
        or abs(value) > _MAX_NUMBER_MAGNITUDE
    ):
        raise _fail(f"{field_name} exceeds the reserved numeric bound")
    return value


def _exact_status(value: object) -> int:
    if type(value) is not int:
        raise _fail("status_code must be an exact built-in integer")
    return value


def _scenario(value: object) -> str:
    if type(value) is not str or value not in SCENARIOS:
        raise _fail("scenario must be an exact documented scenario string")
    return value


def _tax_year(value: object) -> str:
    if type(value) is not str or _TAX_YEAR_RE.fullmatch(value) is None:
        raise _fail("tax_year must match YYYY-YY using ASCII digits")
    return value


def _validate_nino(value: object) -> None:
    if type(value) is not str or _NINO_RE.fullmatch(value) is None:
        raise _fail("nino must match the documented uppercase ASCII pattern")


@dataclass(frozen=True, repr=False, kw_only=True)
class WinterFuelCreateRequestIntent:
    """Validated immutable, non-sendable request intent with no retained NINO."""

    nino: InitVar[str]
    tax_year: str
    scenario: str | None = _SCENARIO_OMITTED
    scenario_present: bool = field(init=False, default=False)

    def __post_init__(self, nino: str) -> None:
        _validate_nino(nino)
        object.__setattr__(self, "tax_year", _tax_year(self.tax_year))
        if self.scenario is _SCENARIO_OMITTED:
            object.__setattr__(self, "scenario", None)
        else:
            object.__setattr__(self, "scenario", _scenario(self.scenario))
            object.__setattr__(self, "scenario_present", True)

    def __repr__(self) -> str:
        return (
            "WinterFuelCreateRequestIntent("
            f"tax_year={self.tax_year!r}, scenario={self.scenario!r}, "
            f"scenario_present={self.scenario_present!r})"
        )


def build_winter_fuel_create_request(
    *, nino: str, tax_year: str, scenario: object = _SCENARIO_OMITTED
) -> WinterFuelCreateRequestIntent:
    if scenario is _SCENARIO_OMITTED:
        return WinterFuelCreateRequestIntent(nino=nino, tax_year=tax_year)
    return WinterFuelCreateRequestIntent(
        nino=nino, tax_year=tax_year, scenario=_scenario(scenario)
    )


@dataclass(frozen=True, repr=False, kw_only=True)
class WinterFuelExpectedJsonObservation:
    winter_fuel_payment_amount: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _number(self.winter_fuel_payment_amount, "winterFuelPaymentAmount")
        _validate_unknown_names(
            self.unknown_names, _EXPECTED_JSON_NAMES, "expectedJson"
        )

    def __repr__(self) -> str:
        return "WinterFuelExpectedJsonObservation([REDACTED])"


def _bind_request(request: object) -> WinterFuelCreateRequestIntent:
    if type(request) is not WinterFuelCreateRequestIntent:
        raise _fail("request must be an exact WinterFuelCreateRequestIntent")
    return request


@dataclass(frozen=True, repr=False, kw_only=True)
class WinterFuelCreateResponseObservation:
    request: InitVar[WinterFuelCreateRequestIntent]
    expected_status: int | Decimal
    expected_json: WinterFuelExpectedJsonObservation | None
    expected_json_present: bool
    unknown_names: frozenset[str] = frozenset()
    completeness: str = COMPLETENESS
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)

    def __post_init__(self, request: WinterFuelCreateRequestIntent) -> None:
        request = _bind_request(request)
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "scenario", request.scenario)
        object.__setattr__(self, "scenario_present", request.scenario_present)
        _number(self.expected_status, "expectedStatus")
        if type(self.expected_json_present) is not bool:
            raise _fail("expected_json_present must be an exact built-in bool")
        if self.expected_json_present:
            if type(self.expected_json) is not WinterFuelExpectedJsonObservation:
                raise _fail("present expectedJson requires an exact observation")
        elif self.expected_json is not None:
            raise _fail("omitted expectedJson must retain value None")
        _validate_unknown_names(self.unknown_names, _TOP_NAMES, "top-level response")
        if type(self.completeness) is not str or self.completeness != COMPLETENESS:
            raise _fail("completeness must be UNVERIFIED")

    def __repr__(self) -> str:
        return "WinterFuelCreateResponseObservation([REDACTED])"


@dataclass(frozen=True, repr=False, kw_only=True)
class WinterFuelNon201Observation:
    """Bounded non-success fact; content type and body are deliberately ignored."""

    request: InitVar[WinterFuelCreateRequestIntent]
    status_code: int
    completeness: str = COMPLETENESS
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)

    def __post_init__(self, request: WinterFuelCreateRequestIntent) -> None:
        request = _bind_request(request)
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "scenario", request.scenario)
        object.__setattr__(self, "scenario_present", request.scenario_present)
        _exact_status(self.status_code)
        if self.status_code == SUCCESS_STATUS:
            raise _fail("non-201 observation cannot record HTTP 201")
        if type(self.completeness) is not str or self.completeness != COMPLETENESS:
            raise _fail("completeness must be UNVERIFIED")

    def __repr__(self) -> str:
        return "WinterFuelNon201Observation([REDACTED])"


def _parse_expected_json(value: object) -> WinterFuelExpectedJsonObservation:
    if type(value) is not dict:
        raise _fail("expectedJson must be an exact built-in object")
    unknown = _unknown_names(value, _EXPECTED_JSON_NAMES, "expectedJson")
    if "winterFuelPaymentAmount" not in value:
        raise _fail("expectedJson is missing winterFuelPaymentAmount")
    return WinterFuelExpectedJsonObservation(
        winter_fuel_payment_amount=_number(
            value["winterFuelPaymentAmount"], "winterFuelPaymentAmount"
        ),
        unknown_names=unknown,
    )


def observe_winter_fuel_create_response(
    request: WinterFuelCreateRequestIntent,
    *,
    status_code: int,
    content_type: object,
    payload: object,
) -> WinterFuelCreateResponseObservation | WinterFuelNon201Observation:
    """Observe an already-retrieved response without performing any I/O."""
    request = _bind_request(request)
    status_code = _exact_status(status_code)
    if status_code != SUCCESS_STATUS:
        # Do not inspect, compare, iterate, stringify, copy or retain either input.
        return WinterFuelNon201Observation(request=request, status_code=status_code)
    if type(content_type) is not str or content_type != JSON_CONTENT_TYPE:
        raise _fail("HTTP 201 requires exact application/json")
    if type(payload) is not dict:
        raise _fail("response payload must be an exact built-in object")
    unknown = _unknown_names(payload, _TOP_NAMES, "top-level response")
    if "expectedStatus" not in payload:
        raise _fail("response is missing expectedStatus")
    expected_status = _number(payload["expectedStatus"], "expectedStatus")
    expected_json_present = "expectedJson" in payload
    if expected_json_present:
        if payload["expectedJson"] is None:
            raise _fail("expectedJson must not be explicit null")
        expected_json = _parse_expected_json(payload["expectedJson"])
    else:
        expected_json = None
    return WinterFuelCreateResponseObservation(
        request=request,
        expected_status=expected_status,
        expected_json=expected_json,
        expected_json_present=expected_json_present,
        unknown_names=unknown,
    )
