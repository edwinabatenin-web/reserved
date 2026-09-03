"""Network-inert HMRC PAYE Test Support 2.1 Child Benefit contract.

Opaque request tokens, bindings, digests and process-local issuance records
detect unsupported mutation/substitution. They are not provider authenticity,
durable provenance, authorisation, attestation or replay prevention. Python
module privacy is not a security boundary. A validated UTR is discarded.
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

OPERATION_ID = "createChildBenefitEntitlementTestData"
HTTP_METHOD = "POST"
SANDBOX_ORIGIN = "https://test-api.service.hmrc.gov.uk"
PATH_TEMPLATE = "/individual-paye-test-support/sa/{utr}/child-benefit-entitlement/annual-summary/{taxYear}"
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
_JSON_NAMES = frozenset({"childBenefitEntitlement"})
_UTR_RE, _YEAR_RE, _HEX_RE = re.compile(r"[0-9]{10}"), re.compile(r"[0-9]{4}-[0-9]{2}"), re.compile(r"[0-9a-f]{64}")
_OMITTED = object()

class HMRCPayeTestSupportChildBenefitContractError(ValueError): pass
def _fail(text): return HMRCPayeTestSupportChildBenefitContractError("HMRC PAYE Test Support Child Benefit contract: " + text)
def _year(v):
    if type(v) is not str or _YEAR_RE.fullmatch(v) is None: raise _fail("tax_year must match YYYY-YY using ASCII digits")
    return v
def _scenario(v):
    if type(v) is not str or v not in SCENARIOS: raise _fail("scenario must be an exact documented scenario string")
    return v
def _integer(v, name, bounded=False):
    if type(v) is not int: raise _fail(name + " must be an exact built-in integer")
    if bounded and abs(v) > 10**18: raise _fail(name + " exceeds the reserved numeric bound")
    return v
def _amount(v):
    if type(v) is int: return _integer(v, "childBenefitEntitlement", True)
    if type(v) is not Decimal or not v.is_finite(): raise _fail("childBenefitEntitlement must be an exact finite built-in int or Decimal")
    p = v.as_tuple()
    if len(p.digits) > 38 or max(0, -p.exponent) > 12 or abs(v) > Decimal("1000000000000000000"): raise _fail("childBenefitEntitlement exceeds the reserved numeric bound")
    return v
def _names(v, documented, context):
    if type(v) is not frozenset or len(v) > 32: raise _fail(context + " unknown_names is malformed")
    for name in v:
        if type(name) is not str or not name or len(name) > 256 or any(unicodedata.category(c).startswith("C") for c in name): raise _fail(context + " member name is unsafe")
        if name in documented: raise _fail(context + " unknown_names contains a documented member")
    return v
def _unknown(mapping, documented, context):
    if len(mapping) > 64: raise _fail(context + " exceeds the reserved member bound")
    names = []
    for name in mapping:
        if type(name) is not str or not name or len(name) > 256 or any(unicodedata.category(c).startswith("C") for c in name): raise _fail(context + " member names must be safe exact strings")
        if name not in documented: names.append(name)
    if len(names) > 32: raise _fail(context + " exceeds the reserved unknown-name bound")
    return frozenset(names)
def _binding(token, year, present, scenario):
    return (token, year, "present" if present else "omitted", scenario or "", OPERATION_ID, HTTP_METHOD, SANDBOX_ORIGIN, PATH_TEMPLATE, API_VERSION, ACCEPT, JSON_CONTENT_TYPE, OAUTH_GRANT_TYPE, "empty-scopes")
def _valid_binding(v):
    if type(v) is not tuple or len(v) != 13 or any(type(x) is not str for x in v): raise _fail("request binding has invalid shape")
    token, year, marker, scenario = v[:4]
    if _HEX_RE.fullmatch(token) is None: raise _fail("request correlation identity is malformed")
    _year(year)
    if marker == "present": present, scenario = True, _scenario(scenario)
    elif marker == "omitted" and scenario == "": present, scenario = False, None
    else: raise _fail("request scenario binding is malformed")
    if v != _binding(token, year, present, scenario): raise _fail("request binding is not canonical")
    return v

class ChildBenefitCreateRequestIntent:
    __slots__ = ("__binding",)
    def __init__(self, *, utr, tax_year, scenario=_OMITTED):
        if type(utr) is not str or _UTR_RE.fullmatch(utr) is None: raise _fail("utr must contain exactly ten ASCII digits")
        year = _year(tax_year)
        present, scenario = (False, None) if scenario is _OMITTED else (True, _scenario(scenario))
        object.__setattr__(self, "_ChildBenefitCreateRequestIntent__binding", _binding(secrets.token_hex(32), year, present, scenario))
    @property
    def tax_year(self): return _request_binding(self)[1]
    @property
    def scenario_present(self): return _request_binding(self)[2] == "present"
    @property
    def scenario(self):
        b = _request_binding(self); return b[3] if b[2] == "present" else None
    def __setattr__(self, n, v): raise AttributeError("ChildBenefitCreateRequestIntent is immutable")
    def __delattr__(self, n): raise AttributeError("ChildBenefitCreateRequestIntent is immutable")
    def __repr__(self): _request_binding(self); return "ChildBenefitCreateRequestIntent([REDACTED])"
    def __eq__(self, other):
        left = _request_binding(self)
        if type(other) is not ChildBenefitCreateRequestIntent: return NotImplemented
        return left == _request_binding(other)
    def __hash__(self): return hash(_request_binding(self))
    def __copy__(self): _request_binding(self); return self
    def __deepcopy__(self, memo): _request_binding(self); return self
    def __reduce__(self): return (_restore_request, (_request_binding(self),))
def _request_binding(v, _valid=_valid_binding):
    if type(v) is not ChildBenefitCreateRequestIntent: raise _fail("request must be an exact ChildBenefitCreateRequestIntent")
    try: binding = object.__getattribute__(v, "_ChildBenefitCreateRequestIntent__binding")
    except AttributeError: raise _fail("request binding is missing")
    return _valid(binding)
def _restore_request(binding, _valid=_valid_binding):
    value = object.__new__(ChildBenefitCreateRequestIntent)
    object.__setattr__(value, "_ChildBenefitCreateRequestIntent__binding", _valid(binding))
    return value

def _exact(v, typ, names):
    if type(v) is not typ: raise _fail("observation type is not exact")
    state = object.__getattribute__(v, "__dict__")
    if type(state) is not dict or len(state) != len(names): raise _fail("observation state is not exact")
    for key in state:
        if type(key) is not str or key not in names: raise _fail("observation state is not exact")
    return state
def _number(v):
    if type(v) is int: return ["int", v]
    p = v.as_tuple(); return ["Decimal", p.sign, list(p.digits), p.exponent]
def _digest(v): return hashlib.sha256(json.dumps(v, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()

def _build_nested_json_observation():
    amount_validator = _amount
    names_validator = _names
    exact = _exact
    number = _number
    sha256 = hashlib.sha256
    json_dumps = json.dumps
    def digest(v):
        return sha256(json_dumps(v, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    fail = _fail
    hex_re = _HEX_RE
    json_names = _JSON_NAMES
    compare_digest = secrets.compare_digest
    getattr_raw = object.__getattribute__
    new_obj = object.__new__
    setattr_raw = object.__setattr__
    json_state_names = frozenset({"child_benefit_entitlement", "unknown_names", "_json_integrity"})
    json_public_names = frozenset({"child_benefit_entitlement", "unknown_names"})
    json_issued = {}

    def json_state(v):
        s = exact(v, ChildBenefitExpectedJsonObservation, json_state_names)
        return (amount_validator(s["child_benefit_entitlement"]),
                names_validator(s["unknown_names"], json_names, "expectedJson"))

    def json_canonical(v):
        if v is None:
            return None
        amount, unknown = json_state(v)
        return [number(amount), sorted(unknown)]

    def json_identity(v):
        if v is None:
            return None
        amount, unknown = json_state(v)
        integrity = digest([number(amount), sorted(unknown)])
        s = getattr_raw(v, "__dict__")
        stored = s["_json_integrity"]
        if type(stored) is not str or hex_re.fullmatch(stored) is None or not compare_digest(stored, integrity):
            raise fail("expectedJson integrity is incoherent")
        issued = json_issued.get(id(v))
        if issued is None or issued[0]() is not v or not compare_digest(issued[1], integrity):
            raise fail("expectedJson provenance is unsupported")
        num = ("int", amount) if type(amount) is int else ("Decimal", amount.as_tuple())
        return (num, unknown)

    def json_register(value, integrity):
        identity = id(value)
        def discard(ref):
            current = json_issued.get(identity)
            if current is not None and current[0] is ref:
                json_issued.pop(identity, None)
        ref = weakref.ref(value, discard)
        json_issued[identity] = (ref, integrity)

    def new_json(amount, unknown):
        amount = amount_validator(amount)
        unknown = names_validator(unknown, json_names, "expectedJson")
        integrity = digest([number(amount), sorted(unknown)])
        v = new_obj(ChildBenefitExpectedJsonObservation)
        setattr_raw(v, "child_benefit_entitlement", amount)
        setattr_raw(v, "unknown_names", unknown)
        setattr_raw(v, "_json_integrity", integrity)
        json_register(v, integrity)
        json_identity(v)
        return v

    def restore_json(amount, unknown, issued_integrity):
        amount = amount_validator(amount)
        unknown = names_validator(unknown, json_names, "expectedJson")
        if type(issued_integrity) is not str or hex_re.fullmatch(issued_integrity) is None:
            raise fail("expectedJson issued identity is malformed")
        if not compare_digest(issued_integrity, digest([number(amount), sorted(unknown)])):
            raise fail("expectedJson issued identity does not match reconstructed values")
        return new_json(amount, unknown)
    restore_json.__qualname__ = "_restore_json"

    @dataclass(frozen=True, repr=False, init=False, eq=False)
    class ChildBenefitExpectedJsonObservation:
        child_benefit_entitlement: int | Decimal = field(init=False)
        unknown_names: frozenset[str] = field(init=False)
        _json_integrity: str = field(init=False, repr=False)

        def __init__(self, *a, **k):
            raise TypeError("ChildBenefitExpectedJsonObservation is observer-constructed only")

        def __getattribute__(self, name):
            if name in json_public_names:
                json_identity(self)
            return object.__getattribute__(self, name)

        def __repr__(self):
            json_identity(self)
            return "ChildBenefitExpectedJsonObservation([REDACTED])"

        def __eq__(self, other):
            left = json_identity(self)
            if type(other) is not ChildBenefitExpectedJsonObservation:
                return NotImplemented
            return left == json_identity(other)

        def __hash__(self):
            return hash(json_identity(self))

        def __copy__(self):
            json_identity(self)
            return self

        def __deepcopy__(self, memo):
            json_identity(self)
            return self

        def __reduce__(self):
            json_identity(self)
            s = object.__getattribute__(self, "__dict__")
            return (restore_json, (s["child_benefit_entitlement"], s["unknown_names"], s["_json_integrity"]))

    return (ChildBenefitExpectedJsonObservation, json_state, json_canonical,
            json_identity, new_json, restore_json)

ChildBenefitExpectedJsonObservation, _json_state, _json_canonical, _json_identity, _new_json, _restore_json = _build_nested_json_observation()

def _build_response_observation(json_state, json_canonical, json_identity):
    exact = _exact
    integer = _integer
    names = _names
    fail = _fail
    hex_re = _HEX_RE
    request_binding = _request_binding
    valid_binding = _valid_binding
    restore_request = _restore_request
    sha256 = hashlib.sha256
    json_dumps = json.dumps
    def digest(v):
        return sha256(json_dumps(v, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    compare_digest = secrets.compare_digest
    getattr_raw = object.__getattribute__
    new_obj = object.__new__
    setattr_raw = object.__setattr__
    weakref_ref = weakref.ref
    completeness = COMPLETENESS
    json_content_type = JSON_CONTENT_TYPE
    top_names = _TOP_NAMES
    state_names = frozenset({"request", "_request_binding", "_source_binding", "tax_year", "scenario", "scenario_present", "status_code", "content_type", "expected_status", "expected_json", "expected_json_present", "unknown_names", "completeness", "_observation_integrity"})
    state_public = frozenset({"request", "tax_year", "scenario", "scenario_present", "status_code", "content_type", "expected_status", "expected_json", "expected_json_present", "unknown_names", "completeness"})
    issued = {}

    @dataclass(frozen=True, repr=False, init=False, eq=False)
    class ChildBenefitCreateResponseObservation:
        request: ChildBenefitCreateRequestIntent = field(init=False, repr=False)
        _request_binding: tuple[str, ...] = field(init=False, repr=False)
        _source_binding: tuple[str, ...] = field(init=False, repr=False)
        tax_year: str = field(init=False)
        scenario: str | None = field(init=False)
        scenario_present: bool = field(init=False)
        status_code: int = field(init=False)
        content_type: str = field(init=False)
        expected_status: int = field(init=False)
        expected_json: ChildBenefitExpectedJsonObservation | None = field(init=False)
        expected_json_present: bool = field(init=False)
        unknown_names: frozenset[str] = field(init=False)
        completeness: str = field(init=False)
        _observation_integrity: str = field(init=False, repr=False)
        def __init__(self, *a, **k): raise TypeError("ChildBenefitCreateResponseObservation is observer-constructed only")
        def __getattribute__(self, name):
            if name in state_public: state(self)
            return object.__getattribute__(self, name)
        def __repr__(self): state(self); return "ChildBenefitCreateResponseObservation([REDACTED])"
        def __eq__(self, other):
            left = state(self)
            if type(other) is not ChildBenefitCreateResponseObservation: return NotImplemented
            return left == state(other)
        def __hash__(self): return hash(state(self))
        def __copy__(self): state(self); return self
        def __deepcopy__(self, memo): state(self); return self
        def __reduce__(self):
            state(self)
            s = getattr_raw(self, "__dict__")
            return (restore_observation, (s["_request_binding"], s["expected_status"],
                    s["expected_json"], s["expected_json_present"], s["unknown_names"],
                    s["_observation_integrity"]))

    def register(value, binding, integrity):
        identity = id(value)
        def discard(ref):
            current = issued.get(identity)
            if current is not None and current[0] is ref: issued.pop(identity, None)
        ref = weakref_ref(value, discard); issued[identity] = (ref, binding, integrity)

    def state(v):
        s = exact(v, ChildBenefitCreateResponseObservation, state_names)
        request, retained, source = request_binding(s["request"]), valid_binding(s["_request_binding"]), valid_binding(s["_source_binding"])
        if request != retained or retained != source: raise fail("observation request/source binding is incoherent")
        year, present = retained[1], retained[2] == "present"; scenario = retained[3] if present else None
        if type(s["tax_year"]) is not str or s["tax_year"] != year or type(s["scenario_present"]) is not bool or s["scenario_present"] is not present or type(s["scenario"]) not in (str, type(None)) or s["scenario"] != scenario: raise fail("observation request facts are incoherent")
        if type(s["status_code"]) is not int or s["status_code"] != 201: raise fail("retained HTTP status is incoherent")
        if type(s["content_type"]) is not str or s["content_type"] != json_content_type: raise fail("retained content type is incoherent")
        status = integer(s["expected_status"], "expectedStatus")
        if type(s["expected_json_present"]) is not bool: raise fail("expected_json_present must be an exact bool")
        expected = s["expected_json"]
        if s["expected_json_present"]: json_state(expected)
        elif expected is not None: raise fail("omitted expectedJson must retain None")
        unknown = names(s["unknown_names"], top_names, "top-level response")
        if type(s["completeness"]) is not str or s["completeness"] != completeness: raise fail("completeness must be UNVERIFIED")
        canonical = [list(retained), list(source), year, scenario, present, 201, json_content_type, status, s["expected_json_present"], json_canonical(expected), sorted(unknown), completeness]
        integrity = s["_observation_integrity"]
        if type(integrity) is not str or hex_re.fullmatch(integrity) is None or not compare_digest(integrity, digest(canonical)): raise fail("observation integrity is incoherent")
        entry = issued.get(id(v))
        if entry is None or entry[0]() is not v or entry[1] != retained or not compare_digest(entry[2], integrity): raise fail("observation provenance is unsupported")
        return (retained, source, year, scenario, present, 201, json_content_type, status,
                json_identity(expected), s["expected_json_present"], unknown,
                completeness, integrity)

    def new_observation(request, status, expected, present, unknown):
        b = request_binding(request); v = new_obj(ChildBenefitCreateResponseObservation)
        values = {"request": request, "_request_binding": b, "_source_binding": b, "tax_year": b[1], "scenario": b[3] if b[2] == "present" else None, "scenario_present": b[2] == "present", "status_code": 201, "content_type": json_content_type, "expected_status": status, "expected_json": expected, "expected_json_present": present, "unknown_names": unknown, "completeness": completeness}
        for name, item in values.items(): setattr_raw(v, name, item)
        canonical = [list(b), list(b), values["tax_year"], values["scenario"], values["scenario_present"], 201, json_content_type, status, present, json_canonical(expected), sorted(unknown), completeness]
        integrity = digest(canonical); setattr_raw(v, "_observation_integrity", integrity); register(v, b, integrity); state(v); return v

    def restore_observation(binding, status, expected, present, unknown, issued_integrity):
        b = valid_binding(binding)
        status = integer(status, "expectedStatus")
        if type(present) is not bool: raise fail("expected_json_present must be an exact bool")
        if present: json_state(expected)
        elif expected is not None: raise fail("omitted expectedJson must retain None")
        unknown = names(unknown, top_names, "top-level response")
        canonical = [list(b), list(b), b[1], b[3] if b[2] == "present" else None,
                     b[2] == "present", 201, json_content_type, status, present,
                     json_canonical(expected), sorted(unknown), completeness]
        if type(issued_integrity) is not str or hex_re.fullmatch(issued_integrity) is None:
            raise fail("observation issued identity is malformed")
        if not compare_digest(issued_integrity, digest(canonical)):
            raise fail("observation issued identity does not match reconstructed values")
        return new_observation(restore_request(b), status, expected, present, unknown)
    restore_observation.__qualname__ = "_restore_observation"

    def validate_observation(observation):
        """Revalidate exact state, payload integrity and producing-request binding."""
        state(observation); return observation
    validate_observation.__qualname__ = "validate_child_benefit_create_response_observation"

    return (ChildBenefitCreateResponseObservation, state, new_observation, restore_observation, validate_observation)

ChildBenefitCreateResponseObservation, _state, _new_observation, _restore_observation, validate_child_benefit_create_response_observation = _build_response_observation(_json_state, _json_canonical, _json_identity)

def build_child_benefit_create_request(*, utr, tax_year, scenario=_OMITTED): return ChildBenefitCreateRequestIntent(utr=utr, tax_year=tax_year, scenario=scenario)
def observe_child_benefit_create_response(request, *, status_code, content_type, payload):
    _request_binding(request)
    _integer(status_code, "status_code")
    if status_code != 201: raise _fail("undocumented HTTP status is not accepted")
    if type(content_type) is not str or content_type != JSON_CONTENT_TYPE: raise _fail("HTTP 201 requires exact application/json")
    if type(payload) is not dict: raise _fail("response payload must be an exact built-in object")
    unknown = _unknown(payload, _TOP_NAMES, "top-level response")
    if "expectedStatus" not in payload: raise _fail("response is missing expectedStatus")
    status = _integer(payload["expectedStatus"], "expectedStatus"); present = "expectedJson" in payload
    if present:
        raw = payload["expectedJson"]
        if type(raw) is not dict: raise _fail("expectedJson must be an exact built-in object")
        inner_unknown = _unknown(raw, _JSON_NAMES, "expectedJson")
        if "childBenefitEntitlement" not in raw: raise _fail("expectedJson is missing childBenefitEntitlement")
        expected = _new_json(_amount(raw["childBenefitEntitlement"]), inner_unknown)
    else: expected = None
    return _new_observation(request, status, expected, present, unknown)
