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
from hashlib import sha256
from dataclasses import dataclass, field
from decimal import Decimal

API_NAME = "Individual PAYE Test Support"
API_VERSION = "2.1"
API_BETA = True
SANDBOX_ONLY = True
SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
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
_REQUEST_IDENTITY_TAG = "HMRC_PAYE_TEST_SUPPORT_BENEFITS_REQUEST_V1"
_REQUEST_STATE = frozenset({"_request_identity"})
_EMPLOYMENT_STATE = frozenset({"employer_paye_reference", "company_cars_and_vans_benefit",
                               "fuel_for_company_cars_and_vans_benefit",
                               "private_medical_dental_insurance",
                               "vouchers_credit_cards_excess_mileage_allowance",
                               "goods_etc_provided_by_employer",
                               "accommodation_provided_by_employer", "other_benefits",
                               "expenses_payments_received", "present_fields", "unknown_names"})
_OBSERVATION_STATE = frozenset({"_request_identity", "_request_binding", "_integrity_digest", "employments",
                                "status_code", "content_type", "unknown_names",
                                "completeness"})


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


def _scenario_parts(tax_year: object, scenario: object,
                    scenario_present: object) -> tuple[str, str | None, bool]:
    if type(tax_year) is not str or _TAX_YEAR.fullmatch(tax_year) is None:
        raise _fail("tax_year must match YYYY-YY using ASCII digits")
    if type(scenario_present) is not bool:
        raise _fail("scenario_present must be an exact bool")
    if scenario_present:
        if type(scenario) is not str or scenario not in SCENARIOS:
            raise _fail("scenario must be HAPPY_PATH_1 or HAPPY_PATH_2")
    elif scenario is not None:
        raise _fail("an omitted scenario must have value None")
    return tax_year, scenario, scenario_present


def _canonical_request_identity(tax_year: object, scenario: object,
                                scenario_present: object) -> tuple[object, ...]:
    year, value, present = _scenario_parts(tax_year, scenario, scenario_present)
    return (_REQUEST_IDENTITY_TAG, HTTP_METHOD, SANDBOX_ORIGIN, PATH_TEMPLATE,
            REQUEST_ACCEPT, REQUEST_CONTENT_TYPE, RESPONSE_CONTENT_TYPE, API_VERSION,
            year, present, value)


def _validate_request_identity(value: object) -> tuple[object, ...]:
    if type(value) is not tuple or len(value) != 11:
        raise _fail("request identity has invalid exact built-in state")
    # Check every built-in type before tuple equality can dispatch a hostile hook.
    if any(type(item) is not str for item in value[:9]) or type(value[9]) is not bool:
        raise _fail("request identity has malformed built-in values")
    if value[10] is not None and type(value[10]) is not str:
        raise _fail("request identity has malformed scenario state")
    expected = _canonical_request_identity(value[8], value[10], value[9])
    if value != expected:
        raise _fail("request identity fixed descriptors do not match")
    return value


def _validate_exact_state(value: object, exact_type: type,
                          names: frozenset[str], label: str) -> dict[str, object]:
    if type(value) is not exact_type:
        raise _fail(f"{label} must have its exact built-in contract type")
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or len(state) != len(names):
        raise _fail(f"{label} has missing or extra state")
    # Dict iteration itself does not hash or compare its already-stored keys.
    # Prove every key safe before set conversion/equality can dispatch a key hook.
    for name in state:
        if type(name) is not str:
            raise _fail(f"{label} state keys must be exact built-in strings")
    if frozenset(state) != names:
        raise _fail(f"{label} has missing or extra state")
    return state


def _canonical_bytes(value: object) -> bytes:
    """Encode already type-validated retained values without Python repr hooks."""
    if value is None:
        return b"n"
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        return b"i" + str(value).encode("ascii") + b";"
    if type(value) is str:
        encoded = value.encode("utf-8")
        return b"s" + str(len(encoded)).encode("ascii") + b":" + encoded
    if type(value) is Decimal:
        sign, digits, exponent = value.as_tuple()
        digit_bytes = bytes(digits)
        return (b"d" + bytes((sign,)) + str(exponent).encode("ascii") + b":"
                + str(len(digit_bytes)).encode("ascii") + b":" + digit_bytes)
    if type(value) is tuple:
        return b"t" + str(len(value)).encode("ascii") + b":" + b"".join(
            _canonical_bytes(item) for item in value)
    if type(value) is frozenset:
        encoded_items = sorted(_canonical_bytes(item) for item in value)
        return b"f" + str(len(value)).encode("ascii") + b":" + b"".join(encoded_items)
    raise _fail("integrity input has an unsupported exact type")


@dataclass(frozen=True, repr=False, init=False, eq=False)
class BenefitsSummaryRequestIntent:
    """UTR-free, non-sendable request intent; omission differs from null."""

    _request_identity: tuple[object, ...] = field(init=False)

    def __init__(self, identity: object) -> None:
        checked = _validate_request_identity(identity)
        object.__setattr__(self, "_request_identity", checked)

    def _identity(self) -> tuple[object, ...]:
        state = _validate_exact_state(self, BenefitsSummaryRequestIntent,
                                      _REQUEST_STATE, "request intent")
        identity = _validate_request_identity(state["_request_identity"])
        return identity

    @property
    def request_identity(self) -> tuple[object, ...]:
        return BenefitsSummaryRequestIntent._identity(self)

    @property
    def tax_year(self) -> str:
        return BenefitsSummaryRequestIntent._identity(self)[8]  # type: ignore[return-value]

    @property
    def scenario_present(self) -> bool:
        return BenefitsSummaryRequestIntent._identity(self)[9]  # type: ignore[return-value]

    @property
    def scenario(self) -> str | None:
        return BenefitsSummaryRequestIntent._identity(self)[10]  # type: ignore[return-value]

    def __repr__(self) -> str:
        BenefitsSummaryRequestIntent._identity(self)
        return "BenefitsSummaryRequestIntent([REDACTED])"

    def __eq__(self, other: object) -> bool:
        left = BenefitsSummaryRequestIntent._identity(self)
        if type(other) is not BenefitsSummaryRequestIntent:
            return False
        return left == BenefitsSummaryRequestIntent._identity(other)

    def __hash__(self) -> int:
        return hash(BenefitsSummaryRequestIntent._identity(self))

    def __copy__(self) -> BenefitsSummaryRequestIntent:
        BenefitsSummaryRequestIntent._identity(self)
        return self

    def __deepcopy__(self, memo: dict) -> BenefitsSummaryRequestIntent:
        BenefitsSummaryRequestIntent._identity(self)
        return self

    def __reduce__(self) -> object:
        return (_rebuild_intent, (BenefitsSummaryRequestIntent._identity(self),))


def build_benefits_summary_request(*, utr: str, tax_year: str,
                                   scenario: object = _OMITTED) -> BenefitsSummaryRequestIntent:
    # The UTR is validated and deliberately never passed to retained construction.
    if type(utr) is not str or _UTR.fullmatch(utr) is None:
        raise _fail("utr must be exactly ten ASCII digits")
    if scenario is _OMITTED:
        identity = _canonical_request_identity(tax_year, None, False)
    else:
        identity = _canonical_request_identity(tax_year, scenario, True)
    return BenefitsSummaryRequestIntent(identity)


@dataclass(frozen=True, repr=False, eq=False)
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

    def __getattribute__(self, name: str) -> object:
        if name in _EMPLOYMENT_STATE:
            BenefitsEmployment._validated_values(self)
            state = object.__getattribute__(self, "__dict__")
            return state[name]
        return object.__getattribute__(self, name)

    def __post_init__(self) -> None:
        BenefitsEmployment._validated_values(self)

    def _validated_values(self) -> tuple[object, ...]:
        state = _validate_exact_state(self, BenefitsEmployment, _EMPLOYMENT_STATE,
                                      "benefits employment")
        _safe_string(state["employer_paye_reference"], "employerPayeReference",
                     RESERVED_MAX_EMPLOYER_REFERENCE_LENGTH, empty=True)
        present_fields = state["present_fields"]
        if type(present_fields) is not frozenset or len(present_fields) > len(_NUMERIC_NAMES):
            raise _fail("present_fields must be an exact documented-name frozenset")
        # Iteration is safe for already-stored frozenset members. Validate exact
        # string type before subset or membership operations can invoke hooks.
        for name in present_fields:
            if type(name) is not str:
                raise _fail("present_fields must be an exact documented-name frozenset")
        if not present_fields <= frozenset(_NUMERIC_NAMES):
            raise _fail("present_fields must be an exact documented-name frozenset")
        values = tuple(state[name] for name in (
            "company_cars_and_vans_benefit", "fuel_for_company_cars_and_vans_benefit",
            "private_medical_dental_insurance", "vouchers_credit_cards_excess_mileage_allowance",
            "goods_etc_provided_by_employer", "accommodation_provided_by_employer",
            "other_benefits", "expenses_payments_received"))
        for name, value in zip(_NUMERIC_NAMES, values):
            if name in present_fields:
                if value is None:
                    raise _fail(f"{name} must not be null when present")
                _number(value, name)
            elif value is not None:
                raise _fail(f"{name} must be None when omitted")
        _unknown_names(state["unknown_names"], _EMPLOYMENT_NAMES, "employment")
        return (state["employer_paye_reference"], *values, state["present_fields"],
                state["unknown_names"])

    def _values(self) -> tuple[int | Decimal | None, ...]:
        validated = BenefitsEmployment._validated_values(self)
        return validated[1:9]  # type: ignore[return-value]

    @property
    def absent_fields(self) -> frozenset[str]:
        validated = BenefitsEmployment._validated_values(self)
        return frozenset(_NUMERIC_NAMES) - validated[9]  # type: ignore[operator]

    def __repr__(self) -> str:
        BenefitsEmployment._validated_values(self)
        return "BenefitsEmployment([REDACTED])"

    def __eq__(self, other: object) -> bool:
        left = BenefitsEmployment._validated_values(self)
        if type(other) is not BenefitsEmployment:
            return False
        return left == BenefitsEmployment._validated_values(other)

    def __hash__(self) -> int:
        return hash(BenefitsEmployment._validated_values(self))

    def __copy__(self) -> BenefitsEmployment:
        BenefitsEmployment._validated_values(self)
        return self

    def __deepcopy__(self, memo: dict) -> BenefitsEmployment:
        BenefitsEmployment._validated_values(self)
        return self

    def __reduce__(self) -> object:
        validated = BenefitsEmployment._validated_values(self)
        return (_rebuild_employment, (validated[0], validated[1:9],
                                     validated[9], validated[10]))


@dataclass(frozen=True, repr=False, init=False, eq=False)
class BenefitsSummaryCreated:
    """Immutable fixture observation bound to a validated request intent."""

    _request_identity: tuple[object, ...] = field(init=False)
    _request_binding: tuple[object, ...] = field(init=False)
    _integrity_digest: str = field(init=False)
    employments: tuple[BenefitsEmployment, ...] = field(init=False)
    status_code: int = field(init=False)
    content_type: str = field(init=False)
    unknown_names: frozenset[str] = field(init=False)
    completeness: str = field(init=False)

    def __getattribute__(self, name: str) -> object:
        if name in _OBSERVATION_STATE and not name.startswith("_"):
            BenefitsSummaryCreated._validated_state(self)
            state = object.__getattribute__(self, "__dict__")
            return state[name]
        return object.__getattribute__(self, name)

    def __init__(self, request: object, employments: object, *, status_code: object = SUCCESS_STATUS,
                 content_type: object = RESPONSE_CONTENT_TYPE,
                 unknown_names: object = frozenset(), completeness: object = COMPLETENESS,
                 _integrity_digest: object = None) -> None:
        if type(request) is not BenefitsSummaryRequestIntent:
            raise _fail("request must be an exact validated BenefitsSummaryRequestIntent")
        identity = BenefitsSummaryRequestIntent._identity(request)
        binding = (_REQUEST_IDENTITY_TAG, identity)
        object.__setattr__(self, "_request_identity", identity)
        object.__setattr__(self, "_request_binding", binding)
        object.__setattr__(self, "employments", employments)
        object.__setattr__(self, "status_code", status_code)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "unknown_names", unknown_names)
        object.__setattr__(self, "completeness", completeness)
        object.__setattr__(self, "_integrity_digest", _integrity_digest)
        BenefitsSummaryCreated._validated_state(self)

    def _validated_state(self) -> tuple[tuple[object, ...], tuple[object, ...]]:
        state = _validate_exact_state(self, BenefitsSummaryCreated,
                                      _OBSERVATION_STATE, "benefits observation")
        identity = _validate_request_identity(state["_request_identity"])
        binding = state["_request_binding"]
        if type(binding) is not tuple or len(binding) != 2 or type(binding[0]) is not str:
            raise _fail("request binding has invalid exact built-in state")
        if type(binding[1]) is not tuple:
            raise _fail("request binding has malformed identity state")
        bound_identity = _validate_request_identity(binding[1])
        if binding[0] != _REQUEST_IDENTITY_TAG or identity != bound_identity:
            raise _fail("observation request binding does not match its canonical identity")
        if type(state["status_code"]) is not int or state["status_code"] != SUCCESS_STATUS:
            raise _fail("status_code must be the exact built-in integer 201")
        if type(state["content_type"]) is not str or state["content_type"] != RESPONSE_CONTENT_TYPE:
            raise _fail("content_type must be exact application/json")
        employments = state["employments"]
        if type(employments) is not tuple or not (1 <= len(employments) <= RESERVED_MAX_EMPLOYMENTS):
            raise _fail("employments must be a bounded non-empty exact tuple")
        if any(type(item) is not BenefitsEmployment for item in employments):
            raise _fail("employments must contain exact BenefitsEmployment values")
        for item in employments:
            BenefitsEmployment._validated_values(item)
        _unknown_names(state["unknown_names"], _TOP_NAMES, "top level")
        if type(state["completeness"]) is not str or state["completeness"] != COMPLETENESS:
            raise _fail("completeness must be exactly UNVERIFIED")
        digest = state["_integrity_digest"]
        if type(digest) is not str or len(digest) != 64:
            raise _fail("observation integrity digest has invalid exact state")
        employment_values = tuple(BenefitsEmployment._validated_values(item)
                                  for item in employments)
        integrity_material = (
            "HMRC_PAYE_TEST_SUPPORT_BENEFITS_OBSERVATION_INTEGRITY_V1",
            identity, binding, employment_values, state["status_code"],
            state["content_type"], state["unknown_names"], state["completeness"])
        expected_digest = sha256(_canonical_bytes(integrity_material)).hexdigest()
        if digest != expected_digest:
            raise _fail("observation request-and-payload integrity does not match")
        return identity, binding

    @property
    def request_identity(self) -> tuple[object, ...]:
        return BenefitsSummaryCreated._validated_state(self)[0]

    @property
    def request_binding(self) -> tuple[object, ...]:
        return BenefitsSummaryCreated._validated_state(self)[1]

    @property
    def tax_year(self) -> str:
        return BenefitsSummaryCreated._validated_state(self)[0][8]  # type: ignore[return-value]

    @property
    def scenario_present(self) -> bool:
        return BenefitsSummaryCreated._validated_state(self)[0][9]  # type: ignore[return-value]

    @property
    def scenario(self) -> str | None:
        return BenefitsSummaryCreated._validated_state(self)[0][10]  # type: ignore[return-value]

    def __repr__(self) -> str:
        BenefitsSummaryCreated._validated_state(self)
        return "BenefitsSummaryCreated([REDACTED])"

    def __eq__(self, other: object) -> bool:
        BenefitsSummaryCreated._validated_state(self)
        if type(other) is not BenefitsSummaryCreated:
            return False
        BenefitsSummaryCreated._validated_state(other)
        left = object.__getattribute__(self, "__dict__")
        right = object.__getattribute__(other, "__dict__")
        names = ("_request_binding", "employments", "status_code", "content_type",
                 "unknown_names", "completeness")
        return tuple(left[name] for name in names) == tuple(right[name] for name in names)

    def __hash__(self) -> int:
        BenefitsSummaryCreated._validated_state(self)
        state = object.__getattribute__(self, "__dict__")
        return hash((state["_request_binding"], state["employments"], state["status_code"],
                     state["content_type"], state["unknown_names"], state["completeness"]))

    def __copy__(self) -> BenefitsSummaryCreated:
        BenefitsSummaryCreated._validated_state(self)
        return self

    def __deepcopy__(self, memo: dict) -> BenefitsSummaryCreated:
        BenefitsSummaryCreated._validated_state(self)
        return self

    def __reduce__(self) -> object:
        identity, binding = BenefitsSummaryCreated._validated_state(self)
        state = object.__getattribute__(self, "__dict__")
        return (_rebuild_summary, (identity, binding, state["employments"],
                                  state["status_code"], state["content_type"],
                                  state["unknown_names"], state["completeness"],
                                  state["_integrity_digest"]))


def _rebuild_intent(identity: object) -> BenefitsSummaryRequestIntent:
    return BenefitsSummaryRequestIntent(identity)


def _rebuild_employment(reference: str, values: tuple[int | Decimal | None, ...],
                        present_fields: frozenset[str],
                        unknown_names: frozenset[str]) -> BenefitsEmployment:
    if type(values) is not tuple or len(values) != len(_NUMERIC_NAMES):
        raise _fail("serialized employment numeric shape is invalid")
    return BenefitsEmployment(reference, *values, present_fields=present_fields,
                              unknown_names=unknown_names)


def _rebuild_summary(identity: object, binding: object,
                     employments: tuple[BenefitsEmployment, ...], status_code: int,
                     content_type: str, unknown_names: frozenset[str],
                     completeness: str, integrity_digest: object) -> BenefitsSummaryCreated:
    checked_identity = _validate_request_identity(identity)
    if type(binding) is not tuple or len(binding) != 2 or type(binding[0]) is not str:
        raise _fail("serialized request binding is invalid")
    if type(binding[1]) is not tuple:
        raise _fail("serialized request binding identity is invalid")
    checked_bound = _validate_request_identity(binding[1])
    if binding[0] != _REQUEST_IDENTITY_TAG or checked_identity != checked_bound:
        raise _fail("serialized request identity and binding differ")
    request = _rebuild_intent(checked_identity)
    return BenefitsSummaryCreated(request, employments, status_code=status_code,
                                  content_type=content_type, unknown_names=unknown_names,
                                  completeness=completeness,
                                  _integrity_digest=integrity_digest)


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
    identity = BenefitsSummaryRequestIntent._identity(request)
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
    binding = (_REQUEST_IDENTITY_TAG, identity)
    employment_values = tuple(BenefitsEmployment._validated_values(item)
                              for item in employments)
    integrity_material = (
        "HMRC_PAYE_TEST_SUPPORT_BENEFITS_OBSERVATION_INTEGRITY_V1",
        identity, binding, employment_values, SUCCESS_STATUS,
        RESPONSE_CONTENT_TYPE, unknown, COMPLETENESS)
    digest = sha256(_canonical_bytes(integrity_material)).hexdigest()
    return BenefitsSummaryCreated(request, employments, unknown_names=unknown,
                                  _integrity_digest=digest)


__all__ = ["HMRCPAYETestSupportBenefitsContractError", "BenefitsSummaryRequestIntent",
           "BenefitsEmployment", "BenefitsSummaryCreated", "build_benefits_summary_request",
           "observe_benefits_summary_response"]
