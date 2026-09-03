"""Disabled, offline and NINO-free Winter Fuel Test Support contract."""
from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
import weakref
from dataclasses import dataclass, field
from decimal import Decimal

OPERATION_ID = "createWinterFuelPaymentAmountTestData"
HTTP_METHOD = "POST"
PATH_TEMPLATE = "/individual-paye-test-support/{nino}/winter-fuel-payment-amount/annual-summary/{taxYear}"
API_VERSION = "2.1"
ACCEPT = "application/vnd.hmrc.2.1+json"
JSON_CONTENT_TYPE = "application/json"
SUCCESS_STATUS = 201
OAUTH_GRANT_TYPE = "client_credentials"
OAUTH_SCOPES = frozenset()
SANDBOX_ONLY = True
SCENARIOS = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2", "UNHAPPY_PATH_500"})
COMPLETENESS = "UNVERIFIED"

_TOP = frozenset({"expectedStatus", "expectedJson"})
_INNER = frozenset({"winterFuelPaymentAmount"})
_MAX_MEMBERS, _MAX_UNKNOWN, _MAX_NAME = 64, 32, 256
_MAX_DIGITS, _MAX_PLACES, _MAX_INT = 38, 12, 10**18
_MAX_DECIMAL = Decimal("1000000000000000000")
_NINO = re.compile(r"[A-Z]{2}[0-9]{6}[A-Z]")
_YEAR = re.compile(r"[0-9]{4}-[0-9]{2}")
_HEX = re.compile(r"[0-9a-f]{64}")
_OMITTED = object()
_BINDING_LEN = 13
_REQUEST_FIELDS = frozenset({"_request_binding"})
_INNER_FIELDS = frozenset({"winter_fuel_payment_amount", "unknown_names"})
_SUCCESS_FIELDS = frozenset({"request", "_request_binding", "_source_binding",
    "tax_year", "scenario", "scenario_present", "expected_status", "expected_json",
    "expected_json_present", "unknown_names", "completeness", "_observation_integrity"})
_NON201_FIELDS = frozenset({"request", "_request_binding", "_source_binding",
    "tax_year", "scenario", "scenario_present", "status_code", "completeness",
    "_observation_integrity"})
_REQUEST_ISSUANCE: dict[int, tuple[weakref.ReferenceType[object], tuple[str, ...]]] = {}
_OBS_ISSUANCE: dict[int, tuple[weakref.ReferenceType[object], tuple[str, ...], str]] = {}

class HMRCPayeTestSupportWinterFuelContractError(ValueError):
    """Constant, non-echoing contract failure."""

def _fail(rule: str):
    return HMRCPayeTestSupportWinterFuelContractError(
        f"HMRC PAYE Test Support Winter Fuel contract: {rule}")

def _state(value: object, kind: type, fields: frozenset[str], label: str) -> dict:
    if type(value) is not kind:
        raise _fail(f"{label} must have its exact contract type")
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or len(state) != len(fields):
        raise _fail(f"{label} has missing or extra state")
    for name in state:  # existing-key iteration invokes no key hook
        if type(name) is not str:
            raise _fail(f"{label} state names must be exact built-in strings")
    if frozenset(state) != fields:
        raise _fail(f"{label} has missing or extra state")
    return state

def _name(value: object, context: str) -> str:
    if type(value) is not str:
        raise _fail(f"{context} member names must be exact built-in strings")
    if not value or len(value) > _MAX_NAME:
        raise _fail(f"{context} member name is outside the reserved bound")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise _fail(f"{context} member name contains an unsafe character")
    return value

def _unknown_from(obj: dict, known: frozenset[str], context: str) -> frozenset[str]:
    if len(obj) > _MAX_MEMBERS:
        raise _fail(f"{context} exceeds the reserved member bound")
    names = [_name(key, context) for key in obj]
    result = frozenset(key for key in names if key not in known)
    if len(result) > _MAX_UNKNOWN:
        raise _fail(f"{context} exceeds the reserved unknown-name bound")
    return result

def _unknown(value: object, known: frozenset[str], context: str) -> frozenset[str]:
    if type(value) is not frozenset or len(value) > _MAX_UNKNOWN:
        raise _fail(f"{context} unknown_names must be an exact bounded frozenset")
    for key in value:
        _name(key, context)
    if value & known:
        raise _fail(f"{context} unknown_names contains a documented name")
    return value

def _number(value: object, field_name: str) -> int | Decimal:
    if type(value) is int:
        if abs(value) > _MAX_INT:
            raise _fail(f"{field_name} exceeds the reserved numeric bound")
        return value
    if type(value) is not Decimal or not value.is_finite():
        raise _fail(f"{field_name} must be an exact finite int or Decimal")
    parts = value.as_tuple()
    if (len(parts.digits) > _MAX_DIGITS or max(0, -parts.exponent) > _MAX_PLACES
            or max(1, len(parts.digits) + parts.exponent) > _MAX_DIGITS
            or abs(value) > _MAX_DECIMAL):
        raise _fail(f"{field_name} exceeds the reserved numeric bound")
    return value

def _status(value: object) -> int:
    if type(value) is not int:
        raise _fail("status_code must be an exact built-in integer")
    return value

def _scenario(value: object) -> str:
    if type(value) is not str or value not in SCENARIOS:
        raise _fail("scenario must be an exact documented scenario string")
    return value

def _year(value: object) -> str:
    if type(value) is not str or _YEAR.fullmatch(value) is None:
        raise _fail("tax_year must match YYYY-YY using ASCII digits")
    return value

def _binding(correlation: str, year: str, present: bool, scenario: str | None) -> tuple[str, ...]:
    return (correlation, OPERATION_ID, HTTP_METHOD, PATH_TEMPLATE, API_VERSION, ACCEPT,
        JSON_CONTENT_TYPE, OAUTH_GRANT_TYPE, "scopes:<empty>", "sandbox-only", year,
        "present" if present else "omitted", scenario if present else "<omitted>")

def _check_binding(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) != _BINDING_LEN:
        raise _fail("request binding has invalid shape")
    if any(type(item) is not str for item in value):
        raise _fail("request binding values must be exact built-in strings")
    correlation, *_, year, presence, scenario = value
    if _HEX.fullmatch(correlation) is None:
        raise _fail("request identity is malformed")
    _year(year)
    if presence == "omitted" and scenario == "<omitted>":
        present, selected = False, None
    elif presence == "present":
        present, selected = True, _scenario(scenario)
    else:
        raise _fail("request scenario state is malformed")
    if value != _binding(correlation, year, present, selected):
        raise _fail("request binding is not canonical")
    return value

def _register(registry: dict, value: object, record: tuple) -> None:
    identity = id(value)
    def discard(ref):
        current = registry.get(identity)
        if current is not None and current[0] is ref:
            registry.pop(identity, None)
    registry[identity] = (weakref.ref(value, discard), *record)

@dataclass(frozen=True, repr=False, init=False, eq=False)
class WinterFuelCreateRequestIntent:
    _request_binding: tuple[str, ...] = field(init=False)
    def __init__(self, *, nino: str, tax_year: str, scenario: object = _OMITTED):
        if type(nino) is not str or _NINO.fullmatch(nino) is None:
            raise _fail("nino must match the documented uppercase ASCII pattern")
        year = _year(tax_year)
        present, selected = (False, None) if scenario is _OMITTED else (True, _scenario(scenario))
        binding = _binding(secrets.token_hex(32), year, present, selected)
        object.__setattr__(self, "_request_binding", binding)
        _register(_REQUEST_ISSUANCE, self, (binding,))
    def _validated(self):
        binding = _check_binding(_state(self, WinterFuelCreateRequestIntent,
                                        _REQUEST_FIELDS, "request")["_request_binding"])
        issued = _REQUEST_ISSUANCE.get(id(self))
        if issued is None or issued[0]() is not self or issued[1] != binding:
            raise _fail("request provenance is unsupported")
        return binding
    @property
    def tax_year(self): return WinterFuelCreateRequestIntent._validated(self)[10]
    @property
    def scenario_present(self): return WinterFuelCreateRequestIntent._validated(self)[11] == "present"
    @property
    def scenario(self):
        value = WinterFuelCreateRequestIntent._validated(self)[12]
        return None if value == "<omitted>" else value
    def __repr__(self):
        WinterFuelCreateRequestIntent._validated(self); return "WinterFuelCreateRequestIntent([REDACTED])"
    def __eq__(self, other):
        left = WinterFuelCreateRequestIntent._validated(self)
        return type(other) is WinterFuelCreateRequestIntent and left == WinterFuelCreateRequestIntent._validated(other)
    def __hash__(self): return hash(WinterFuelCreateRequestIntent._validated(self))
    def __copy__(self): WinterFuelCreateRequestIntent._validated(self); return self
    def __deepcopy__(self, memo): WinterFuelCreateRequestIntent._validated(self); return self
    def __reduce__(self): return (_restore_request, (WinterFuelCreateRequestIntent._validated(self),))

def _restore_request(binding: object):
    checked = _check_binding(binding)
    value = object.__new__(WinterFuelCreateRequestIntent)
    object.__setattr__(value, "_request_binding", checked)
    _register(_REQUEST_ISSUANCE, value, (checked,))
    return value

def build_winter_fuel_create_request(*, nino: str, tax_year: str, scenario: object = _OMITTED):
    return WinterFuelCreateRequestIntent(nino=nino, tax_year=tax_year, scenario=scenario)

@dataclass(frozen=True, repr=False, eq=False)
class WinterFuelExpectedJsonObservation:
    winter_fuel_payment_amount: int | Decimal
    unknown_names: frozenset[str] = frozenset()
    def __getattribute__(self, name):
        if name in _INNER_FIELDS:
            values = WinterFuelExpectedJsonObservation._validated(self)
            return values[0 if name == "winter_fuel_payment_amount" else 1]
        return object.__getattribute__(self, name)
    def __post_init__(self): WinterFuelExpectedJsonObservation._validated(self)
    def _validated(self):
        state = _state(self, WinterFuelExpectedJsonObservation, _INNER_FIELDS, "expectedJson")
        return (_number(state["winter_fuel_payment_amount"], "winterFuelPaymentAmount"),
                _unknown(state["unknown_names"], _INNER, "expectedJson"))
    def __repr__(self): WinterFuelExpectedJsonObservation._validated(self); return "WinterFuelExpectedJsonObservation([REDACTED])"
    def __eq__(self, other):
        left = WinterFuelExpectedJsonObservation._validated(self)
        if type(other) is not WinterFuelExpectedJsonObservation:
            return False
        right = WinterFuelExpectedJsonObservation._validated(other)
        return _bytes(left) == _bytes(right)
    def __hash__(self): return hash(_bytes(WinterFuelExpectedJsonObservation._validated(self)))
    def __copy__(self): WinterFuelExpectedJsonObservation._validated(self); return self
    def __deepcopy__(self, memo): WinterFuelExpectedJsonObservation._validated(self); return self
    def __reduce__(self): return (_restore_inner, WinterFuelExpectedJsonObservation._validated(self))

def _restore_inner(amount: object, names: object):
    if type(amount) not in (int, Decimal) or type(names) is not frozenset:
        raise _fail("serialized expectedJson state is invalid")
    return WinterFuelExpectedJsonObservation(amount, names)

def _bytes(value: object) -> bytes:
    if value is None: return b"n"
    if type(value) is bool: return b"b1" if value else b"b0"
    if type(value) is int: return b"i" + str(value).encode() + b";"
    if type(value) is str:
        raw = value.encode(); return b"s" + str(len(raw)).encode() + b":" + raw
    if type(value) is Decimal:
        sign, digits, exponent = value.as_tuple()
        return b"d" + bytes((sign,)) + str(exponent).encode() + b":" + bytes(digits)
    if type(value) is tuple:
        return b"t" + str(len(value)).encode() + b":" + b"".join(_bytes(x) for x in value)
    if type(value) is frozenset:
        return b"f" + b"".join(sorted(_bytes(x) for x in value))
    raise _fail("integrity input has an unsupported exact type")

def _digest(kind: str, binding: tuple[str, ...], values: tuple[object, ...]) -> str:
    return hashlib.sha256(_bytes(("WINTER_FUEL_INTEGRITY_V1", kind, binding, values))).hexdigest()

def _context(binding):
    return binding[10], None if binding[12] == "<omitted>" else binding[12], binding[11] == "present"

def _bound(state: dict):
    if type(state["request"]) is not WinterFuelCreateRequestIntent:
        raise _fail("observation request must have its exact contract type")
    actual = WinterFuelCreateRequestIntent._validated(state["request"])
    retained, source = _check_binding(state["_request_binding"]), _check_binding(state["_source_binding"])
    if actual != retained or retained != source:
        raise _fail("observation request/source binding is incoherent")
    year, scenario, present = _context(retained)
    if (type(state["tax_year"]) is not str or state["tax_year"] != year
            or type(state["scenario_present"]) is not bool or state["scenario_present"] is not present
            or (scenario is None and state["scenario"] is not None)
            or (scenario is not None and (type(state["scenario"]) is not str or state["scenario"] != scenario))):
        raise _fail("observation request context is incoherent")
    return retained

def _success_values(state):
    status = _number(state["expected_status"], "expectedStatus")
    if type(state["expected_json_present"]) is not bool:
        raise _fail("expected_json_present must be an exact built-in bool")
    nested = state["expected_json"]
    if state["expected_json_present"]:
        if type(nested) is not WinterFuelExpectedJsonObservation:
            raise _fail("present expectedJson requires an exact observation")
        material = WinterFuelExpectedJsonObservation._validated(nested)
    elif nested is not None:
        raise _fail("omitted expectedJson must retain value None")
    else: material = None
    unknown = _unknown(state["unknown_names"], _TOP, "top-level response")
    if type(state["completeness"]) is not str or state["completeness"] != COMPLETENESS:
        raise _fail("completeness must be UNVERIFIED")
    return status, material, state["expected_json_present"], unknown, state["completeness"]

def _issued(value, binding, digest):
    if type(digest) is not str or _HEX.fullmatch(digest) is None:
        raise _fail("observation integrity is malformed")
    issued = _OBS_ISSUANCE.get(id(value))
    if (issued is None or issued[0]() is not value or issued[1] != binding
            or not secrets.compare_digest(issued[2], digest)):
        raise _fail("observation provenance is unsupported")

def _validated_observation(value):
    kind = type(value)
    if kind is WinterFuelCreateResponseObservation:
        return WinterFuelCreateResponseObservation._validated(value)
    if kind is WinterFuelNon201Observation:
        return WinterFuelNon201Observation._validated(value)
    raise _fail("observation must have its exact contract type")

class _ObservationProtocol:
    _fields: frozenset[str]
    _kind: str
    def __getattribute__(self, name):
        kind = type(self)
        if kind is WinterFuelCreateResponseObservation:
            fields = _SUCCESS_FIELDS
        elif kind is WinterFuelNon201Observation:
            fields = _NON201_FIELDS
        else:
            raise _fail("observation must have its exact contract type")
        if name in fields and not name.startswith("_"):
            return _validated_observation(self)[0][name]
        return object.__getattribute__(self, name)
    def __repr__(self):
        kind = type(self)
        _validated_observation(self)
        return f"{kind.__name__}([REDACTED])"
    def __eq__(self, other):
        state, _ = _validated_observation(self)
        if type(other) is not type(self):
            if isinstance(other, _ObservationProtocol):
                _validated_observation(other)
            return False
        other_state, _ = _validated_observation(other)
        return state["_observation_integrity"] == other_state["_observation_integrity"]
    def __hash__(self): return hash(_validated_observation(self)[0]["_observation_integrity"])
    def __copy__(self): _validated_observation(self); return self
    def __deepcopy__(self, memo): _validated_observation(self); return self

@dataclass(frozen=True, repr=False, init=False, eq=False)
class WinterFuelCreateResponseObservation(_ObservationProtocol):
    _fields = _SUCCESS_FIELDS
    request: object = field(init=False); _request_binding: object = field(init=False); _source_binding: object = field(init=False)
    tax_year: object = field(init=False); scenario: object = field(init=False); scenario_present: object = field(init=False)
    expected_status: object = field(init=False); expected_json: object = field(init=False); expected_json_present: object = field(init=False)
    unknown_names: object = field(init=False); completeness: object = field(init=False); _observation_integrity: object = field(init=False)
    def __init__(self, *, request, expected_status, expected_json, expected_json_present,
                 unknown_names=frozenset(), completeness=COMPLETENESS):
        _new(self, request, (expected_status, expected_json, expected_json_present, unknown_names, completeness))
    def _validated(self):
        state = _state(self, WinterFuelCreateResponseObservation, _SUCCESS_FIELDS, "success observation")
        binding = _bound(state); values = _success_values(state); digest = state["_observation_integrity"]
        expected = _digest("success", binding, values)
        if type(digest) is not str or not secrets.compare_digest(digest, expected):
            raise _fail("success observation integrity is incoherent")
        _issued(self, binding, digest); return state, binding
    def __reduce__(self):
        state, binding = WinterFuelCreateResponseObservation._validated(self)
        return (_restore_success, (binding, state["expected_status"], state["expected_json"],
            state["expected_json_present"], state["unknown_names"], state["completeness"]))

@dataclass(frozen=True, repr=False, init=False, eq=False)
class WinterFuelNon201Observation(_ObservationProtocol):
    _fields = _NON201_FIELDS
    request: object = field(init=False); _request_binding: object = field(init=False); _source_binding: object = field(init=False)
    tax_year: object = field(init=False); scenario: object = field(init=False); scenario_present: object = field(init=False)
    status_code: object = field(init=False); completeness: object = field(init=False); _observation_integrity: object = field(init=False)
    def __init__(self, *, request, status_code, completeness=COMPLETENESS):
        _new(self, request, (status_code, completeness))
    def _validated(self):
        state = _state(self, WinterFuelNon201Observation, _NON201_FIELDS, "non-201 observation")
        binding = _bound(state); status = _status(state["status_code"])
        if status == 201: raise _fail("non-201 observation cannot record HTTP 201")
        if type(state["completeness"]) is not str or state["completeness"] != COMPLETENESS:
            raise _fail("completeness must be UNVERIFIED")
        values = (status, state["completeness"]); digest = state["_observation_integrity"]
        expected = _digest("non-201", binding, values)
        if type(digest) is not str or not secrets.compare_digest(digest, expected):
            raise _fail("non-201 observation integrity is incoherent")
        _issued(self, binding, digest); return state, binding
    def __reduce__(self):
        state, binding = WinterFuelNon201Observation._validated(self)
        return (_restore_non201, (binding, state["status_code"], state["completeness"]))

def _new(target, request, values):
    target_kind = type(target)
    if target_kind is not WinterFuelCreateResponseObservation and target_kind is not WinterFuelNon201Observation:
        raise _fail("observation must have its exact contract type")
    if type(request) is not WinterFuelCreateRequestIntent:
        raise _fail("request must be an exact WinterFuelCreateRequestIntent")
    binding = WinterFuelCreateRequestIntent._validated(request); year, scenario, present = _context(binding)
    common = {"request": request, "_request_binding": binding, "_source_binding": binding,
              "tax_year": year, "scenario": scenario, "scenario_present": present}
    if target_kind is WinterFuelCreateResponseObservation:
        status, nested, nested_present, unknown, completeness = values
        common.update(expected_status=status, expected_json=nested, expected_json_present=nested_present,
                      unknown_names=unknown, completeness=completeness)
        for name, value in common.items(): object.__setattr__(target, name, value)
        material = _success_values(object.__getattribute__(target, "__dict__")); kind = "success"
    elif target_kind is WinterFuelNon201Observation:
        status, completeness = values; status = _status(status)
        if status == 201: raise _fail("non-201 observation cannot record HTTP 201")
        if type(completeness) is not str or completeness != COMPLETENESS: raise _fail("completeness must be UNVERIFIED")
        common.update(status_code=status, completeness=completeness)
        for name, value in common.items(): object.__setattr__(target, name, value)
        material = (status, completeness); kind = "non-201"
    digest = _digest(kind, binding, material); object.__setattr__(target, "_observation_integrity", digest)
    _register(_OBS_ISSUANCE, target, (binding, digest)); _validated_observation(target)

def _restore_success(binding, status, nested, present, unknown, completeness):
    if (type(binding) is not tuple or len(binding) != _BINDING_LEN
            or any(type(x) is not str for x in binding) or type(status) not in (int, Decimal)
            or type(present) is not bool or (nested is not None and type(nested) is not WinterFuelExpectedJsonObservation)
            or type(unknown) is not frozenset or type(completeness) is not str):
        raise _fail("serialized success state is invalid")
    return WinterFuelCreateResponseObservation(request=_restore_request(_check_binding(binding)),
        expected_status=status, expected_json=nested, expected_json_present=present,
        unknown_names=unknown, completeness=completeness)

def _restore_non201(binding, status, completeness):
    if (type(binding) is not tuple or len(binding) != _BINDING_LEN
            or any(type(x) is not str for x in binding) or type(status) is not int
            or type(completeness) is not str): raise _fail("serialized non-201 state is invalid")
    return WinterFuelNon201Observation(request=_restore_request(_check_binding(binding)),
                                       status_code=status, completeness=completeness)

def _parse_inner(value):
    if type(value) is not dict: raise _fail("expectedJson must be an exact built-in object")
    unknown = _unknown_from(value, _INNER, "expectedJson")
    if "winterFuelPaymentAmount" not in value: raise _fail("expectedJson is missing winterFuelPaymentAmount")
    return WinterFuelExpectedJsonObservation(_number(value["winterFuelPaymentAmount"], "winterFuelPaymentAmount"), unknown)

def observe_winter_fuel_create_response(request, *, status_code, content_type, payload):
    if type(request) is not WinterFuelCreateRequestIntent: raise _fail("request must be an exact WinterFuelCreateRequestIntent")
    WinterFuelCreateRequestIntent._validated(request); status_code = _status(status_code)
    if status_code != 201: return WinterFuelNon201Observation(request=request, status_code=status_code)
    if type(content_type) is not str or content_type != JSON_CONTENT_TYPE: raise _fail("HTTP 201 requires exact application/json")
    if type(payload) is not dict: raise _fail("response payload must be an exact built-in object")
    unknown = _unknown_from(payload, _TOP, "top-level response")
    if "expectedStatus" not in payload: raise _fail("response is missing expectedStatus")
    status = _number(payload["expectedStatus"], "expectedStatus"); present = "expectedJson" in payload
    if present and payload["expectedJson"] is None: raise _fail("expectedJson must not be explicit null")
    nested = _parse_inner(payload["expectedJson"]) if present else None
    return WinterFuelCreateResponseObservation(request=request, expected_status=status,
        expected_json=nested, expected_json_present=present, unknown_names=unknown)

__all__ = ["HMRCPayeTestSupportWinterFuelContractError", "WinterFuelCreateRequestIntent",
    "WinterFuelExpectedJsonObservation", "WinterFuelCreateResponseObservation",
    "WinterFuelNon201Observation", "build_winter_fuel_create_request",
    "observe_winter_fuel_create_response"]
