"""Network-inert typed contract for HMRC PAYE Test Support 2.1 Child Benefit.

This module models only the documented request and HTTP 201 result of
``createChildBenefitEntitlementTestData``.  It has no transport, credential,
persistence, activation, read-side or HICBC-calculation capability.  A supplied
UTR is validated and immediately discarded.

Provider facts are recorded in
``docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md``.  Bounds in this module
are local defensive limits, not HMRC amount, precision or sign rules.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import InitVar, dataclass, field
from decimal import Decimal


OPERATION_ID = "createChildBenefitEntitlementTestData"
HTTP_METHOD = "POST"
PATH_TEMPLATE = (
    "/individual-paye-test-support/sa/{utr}/child-benefit-entitlement/"
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
_EXPECTED_JSON_NAMES = frozenset({"childBenefitEntitlement"})
_MAX_OBJECT_MEMBERS = 64
_MAX_UNKNOWN_NAMES = 32
_MAX_NAME_LENGTH = 256
_MAX_DECIMAL_DIGITS = 38
_MAX_DECIMAL_PLACES = 12
_MAX_NUMBER_MAGNITUDE = Decimal("1000000000000000000")
_MAX_INT_MAGNITUDE = 10**18
_UTR_RE = re.compile(r"[0-9]{10}")
_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
_SCENARIO_OMITTED = object()


class HMRCPayeTestSupportChildBenefitContractError(ValueError):
    """Controlled validation error that does not echo source values."""


def _fail(rule: str) -> HMRCPayeTestSupportChildBenefitContractError:
    return HMRCPayeTestSupportChildBenefitContractError(
        f"HMRC PAYE Test Support Child Benefit contract: {rule}"
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
    safe_names = [_safe_name(name, context) for name in obj]
    result = [name for name in safe_names if name not in documented]
    if len(result) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the reserved unknown-name bound")
    return frozenset(result)


def _validate_unknown_names(
    value: object, documented: frozenset[str], context: str
) -> None:
    if type(value) is not frozenset:
        raise _fail(f"{context} unknown_names must be an exact frozenset")
    if len(value) > _MAX_UNKNOWN_NAMES:
        raise _fail(f"{context} exceeds the reserved unknown-name bound")
    for name in value:
        _safe_name(name, context)
    if value & documented:
        raise _fail(f"{context} unknown_names contains a documented member name")


def _exact_int(value: object, field_name: str, *, bounded: bool = False) -> int:
    if type(value) is not int:
        raise _fail(f"{field_name} must be an exact built-in integer")
    if bounded and abs(value) > _MAX_INT_MAGNITUDE:
        raise _fail(f"{field_name} exceeds the reserved numeric bound")
    return value


def _entitlement(value: object) -> int | Decimal:
    if type(value) is int:
        return _exact_int(value, "childBenefitEntitlement", bounded=True)
    if type(value) is not Decimal:
        raise _fail("childBenefitEntitlement must be an exact built-in int or Decimal")
    if not value.is_finite():
        raise _fail("childBenefitEntitlement must be finite")
    parts = value.as_tuple()
    places = max(0, -parts.exponent)
    if (
        len(parts.digits) > _MAX_DECIMAL_DIGITS
        or places > _MAX_DECIMAL_PLACES
        or abs(value) > _MAX_NUMBER_MAGNITUDE
    ):
        raise _fail("childBenefitEntitlement exceeds the reserved numeric bound")
    return value


def _scenario(value: object) -> str:
    if type(value) is not str or value not in SCENARIOS:
        raise _fail("scenario must be an exact documented scenario string")
    return value


def _tax_year(value: object) -> str:
    if type(value) is not str or _TAX_YEAR_RE.fullmatch(value) is None:
        raise _fail("tax_year must match YYYY-YY using ASCII digits")
    return value


def _validate_utr(value: object) -> None:
    if type(value) is not str or _UTR_RE.fullmatch(value) is None:
        raise _fail("utr must contain exactly ten ASCII digits")


@dataclass(frozen=True, repr=False)
class ChildBenefitCreateRequestIntent:
    """Validated, immutable, non-sendable request intent with no retained UTR."""

    utr: InitVar[str]
    tax_year: str
    scenario: str | None = _SCENARIO_OMITTED
    scenario_present: bool = field(init=False, default=False)

    def __post_init__(self, utr: str) -> None:
        _validate_utr(utr)
        object.__setattr__(self, "tax_year", _tax_year(self.tax_year))
        if self.scenario is _SCENARIO_OMITTED:
            object.__setattr__(self, "scenario", None)
        else:
            object.__setattr__(self, "scenario", _scenario(self.scenario))
            object.__setattr__(self, "scenario_present", True)

    def __repr__(self) -> str:
        return (
            "ChildBenefitCreateRequestIntent("
            f"tax_year={self.tax_year!r}, scenario={self.scenario!r}, "
            f"scenario_present={self.scenario_present!r})"
        )


def build_child_benefit_create_request(
    *, utr: str, tax_year: str, scenario: object = _SCENARIO_OMITTED
) -> ChildBenefitCreateRequestIntent:
    if scenario is _SCENARIO_OMITTED:
        return ChildBenefitCreateRequestIntent(utr=utr, tax_year=tax_year)
    return ChildBenefitCreateRequestIntent(
        utr=utr, tax_year=tax_year, scenario=_scenario(scenario)
    )


@dataclass(frozen=True, repr=False)
class ChildBenefitExpectedJsonObservation:
    child_benefit_entitlement: int | Decimal
    unknown_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _entitlement(self.child_benefit_entitlement)
        _validate_unknown_names(
            self.unknown_names, _EXPECTED_JSON_NAMES, "expectedJson"
        )

    def __repr__(self) -> str:
        return "ChildBenefitExpectedJsonObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class ChildBenefitCreateResponseObservation:
    request: InitVar[ChildBenefitCreateRequestIntent]
    expected_status: int
    expected_json: ChildBenefitExpectedJsonObservation | None
    expected_json_present: bool
    unknown_names: frozenset[str] = frozenset()
    completeness: str = COMPLETENESS
    tax_year: str = field(init=False)
    scenario: str | None = field(init=False)
    scenario_present: bool = field(init=False)

    def __post_init__(self, request: ChildBenefitCreateRequestIntent) -> None:
        if type(request) is not ChildBenefitCreateRequestIntent:
            raise _fail("request must be an exact ChildBenefitCreateRequestIntent")
        object.__setattr__(self, "tax_year", request.tax_year)
        object.__setattr__(self, "scenario", request.scenario)
        object.__setattr__(self, "scenario_present", request.scenario_present)
        _exact_int(self.expected_status, "expectedStatus")
        if type(self.expected_json_present) is not bool:
            raise _fail("expected_json_present must be an exact built-in bool")
        if self.expected_json_present:
            if type(self.expected_json) is not ChildBenefitExpectedJsonObservation:
                raise _fail("present expectedJson requires an exact observation")
        elif self.expected_json is not None:
            raise _fail("omitted expectedJson must retain value None")
        _validate_unknown_names(self.unknown_names, _TOP_NAMES, "top-level response")
        if type(self.completeness) is not str or self.completeness != COMPLETENESS:
            raise _fail("completeness must be UNVERIFIED")

    def __repr__(self) -> str:
        return "ChildBenefitCreateResponseObservation([REDACTED])"


def _parse_expected_json(value: object) -> ChildBenefitExpectedJsonObservation:
    if type(value) is not dict:
        raise _fail("expectedJson must be an exact built-in object")
    unknown = _unknown_names(value, _EXPECTED_JSON_NAMES, "expectedJson")
    if "childBenefitEntitlement" not in value:
        raise _fail("expectedJson is missing childBenefitEntitlement")
    return ChildBenefitExpectedJsonObservation(
        child_benefit_entitlement=_entitlement(value["childBenefitEntitlement"]),
        unknown_names=unknown,
    )


def observe_child_benefit_create_response(
    request: ChildBenefitCreateRequestIntent,
    *,
    status_code: int,
    content_type: str,
    payload: object,
) -> ChildBenefitCreateResponseObservation:
    """Validate an already-retrieved HTTP 201 result; perform no I/O.

    Status is checked before content type or payload, ensuring a non-201 body is
    never inspected.  The resulting observation is bound to the validated,
    redacted request intent's tax-year and scenario facts.
    """
    if type(request) is not ChildBenefitCreateRequestIntent:
        raise _fail("request must be an exact ChildBenefitCreateRequestIntent")
    _exact_int(status_code, "status_code")
    if status_code != SUCCESS_STATUS:
        raise _fail("undocumented HTTP status is not accepted")
    if type(content_type) is not str or content_type != JSON_CONTENT_TYPE:
        raise _fail("HTTP 201 requires exact application/json")
    if type(payload) is not dict:
        raise _fail("response payload must be an exact built-in object")

    unknown = _unknown_names(payload, _TOP_NAMES, "top-level response")
    if "expectedStatus" not in payload:
        raise _fail("response is missing expectedStatus")
    expected_status = _exact_int(payload["expectedStatus"], "expectedStatus")
    expected_json_present = "expectedJson" in payload
    if expected_json_present:
        if payload["expectedJson"] is None:
            raise _fail("expectedJson must not be explicit null")
        expected_json = _parse_expected_json(payload["expectedJson"])
    else:
        expected_json = None

    return ChildBenefitCreateResponseObservation(
        request=request,
        expected_status=expected_status,
        expected_json=expected_json,
        expected_json_present=expected_json_present,
        unknown_names=unknown,
    )
