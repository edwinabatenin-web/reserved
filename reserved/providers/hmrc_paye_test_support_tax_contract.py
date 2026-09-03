"""Network-inert HMRC PAYE Test Support 2.1 tax fixture binding.

The seals below establish process-local coherence and mutation/substitution
detection only. They do not establish provider authenticity, durable
provenance, authorization, attestation, secrecy, or replay prevention.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
import weakref
from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256

OPERATION_ID = "createTaxSummaryTestData"
API_NAME, API_VERSION, API_BETA, SANDBOX_ONLY = "Individual PAYE Test Support", "2.1", True, True
HTTP_METHOD = "POST"
PATH_TEMPLATE = "/individual-paye-test-support/sa/{utr}/tax/annual-summary/{taxYear}"
REQUEST_ACCEPT, REQUEST_CONTENT_TYPE = "application/vnd.hmrc.2.1+json", "application/json"
RESPONSE_CONTENT_TYPE, SUCCESS_STATUS = "application/json", 201
OAUTH_GRANT_TYPE, OAUTH_SCOPES = "client_credentials", frozenset()
COMPLETENESS = "UNVERIFIED"
SCENARIOS, DEFAULT_SCENARIO = frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2"}), "HAPPY_PATH_1"
_TOP = frozenset({"employments", "pensionsAnnuitiesAndOtherStateBenefits", "refunds"})
_EMP = frozenset({"employerPayeReference", "taxTakenOffPay"})
_PEN = frozenset({"otherPensionsAndRetirementAnnuities", "incapacityBenefit"})
_REF = frozenset({"taxRefundedOrSetOff"})
_OMITTED = object()
_UTR, _YEAR, _TOKEN = re.compile(r"[0-9]{10}", re.ASCII), re.compile(r"[0-9]{4}-[0-9]{2}", re.ASCII), re.compile(r"[0-9a-f]{64}")
_FIXED = (OPERATION_ID, HTTP_METHOD, PATH_TEMPLATE, API_NAME, API_VERSION, REQUEST_ACCEPT,
          REQUEST_CONTENT_TYPE, RESPONSE_CONTENT_TYPE, OAUTH_GRANT_TYPE, OAUTH_SCOPES,
          SANDBOX_ONLY, API_BETA)
_REQ_STATE = frozenset({"_identity"})
_EMP_STATE = frozenset({"_token", "employer_paye_reference", "tax_taken_off_pay", "unknown_names"})
_PEN_STATE = frozenset({"_token", "other_pensions_and_retirement_annuities", "incapacity_benefit", "present_fields", "unknown_names"})
_REF_STATE = frozenset({"_token", "tax_refunded_or_set_off", "present_fields", "unknown_names"})
_SUM_STATE = frozenset({"_bound", "_request_identity", "_source_identity", "_integrity", "employments", "pensions_benefits", "refunds", "status_code", "content_type", "scenario", "scenario_present", "unknown_names", "completeness"})
_ISSUED: dict[int, tuple[weakref.ReferenceType[object], tuple[object, ...]]] = {}

class HMRCPAYETestSupportTaxContractError(ValueError): pass
def _fail(s): return HMRCPAYETestSupportTaxContractError("HMRC PAYE test-support tax contract: " + s)

def _state(v, typ, names, label):
    if type(v) is not typ: raise _fail(label + " has invalid exact type")
    d = object.__getattribute__(v, "__dict__")
    if type(d) is not dict or len(d) != len(names): raise _fail(label + " has missing or extra state")
    for k in d:
        if type(k) is not str: raise _fail(label + " has a non-string state key")
    if frozenset(d) != names: raise _fail(label + " has missing or extra state")
    return d

def _text(v, label, empty=True, limit=4096):
    if type(v) is not str or (not empty and not v) or len(v) > limit: raise _fail(label + " is invalid")
    if any(unicodedata.category(c).startswith("C") for c in v): raise _fail(label + " is unsafe")
    return v

def _num(v, label):
    if type(v) is int:
        if abs(v) > 10**18: raise _fail(label + " exceeds a Reserved bound")
        return v
    if type(v) is Decimal:
        if not v.is_finite(): raise _fail(label + " must be finite")
        _, ds, ex = v.as_tuple()
        if abs(v) > Decimal("1e18") or len(ds) > 38 or max(0, -ex) > 12 or max(1, len(ds)+ex) > 38: raise _fail(label + " exceeds a Reserved bound")
        return v
    raise _fail(label + " must be an exact int or Decimal")

def _names(v, known, label):
    if type(v) is not frozenset or len(v) > 32: raise _fail(label + " names are invalid")
    for n in v:
        _text(n, label + " member name", False, 256)
        if n in known: raise _fail(label + " names contain a documented member")
    return v

def _present(v, known, label):
    if type(v) is not frozenset or len(v) > len(known): raise _fail(label + " presence is invalid")
    for n in v:
        if type(n) is not str: raise _fail(label + " presence is invalid")
    if not v <= known: raise _fail(label + " presence is invalid")
    return v

def _object(v, known, label):
    if type(v) is not dict or len(v) > 64: raise _fail(label + " must be an exact bounded object")
    u=[]
    for n in v:
        _text(n, label + " member name", False, 256)
        if n not in known: u.append(n)
    if len(u)>32: raise _fail(label + " has too many unknown members")
    return v, frozenset(u)

def _scenario(year, value, present):
    if type(year) is not str or _YEAR.fullmatch(year) is None: raise _fail("tax_year must match YYYY-YY using ASCII digits")
    if type(present) is not bool: raise _fail("scenario presence is invalid")
    if present:
        if type(value) is not str or value not in SCENARIOS: raise _fail("scenario is not documented")
    elif value is not None: raise _fail("omitted scenario must be None")
    return year, value, present

def _identity(token, year, value, present):
    _scenario(year,value,present)
    if type(token) is not str or _TOKEN.fullmatch(token) is None: raise _fail("request correlation is invalid")
    return (token,year,present,value)+_FIXED

def _valid_identity(v):
    if type(v) is not tuple or len(v)!=16: raise _fail("request identity shape is invalid")
    if (type(v[0]) is not str or type(v[1]) is not str or type(v[2]) is not bool or
        (v[3] is not None and type(v[3]) is not str) or any(type(x) is not str for x in v[4:13]) or
        type(v[13]) is not frozenset or len(v[13]) != 0 or type(v[14]) is not bool or type(v[15]) is not bool): raise _fail("request identity values are invalid")
    if v != _identity(v[0],v[1],v[3],v[2]): raise _fail("request identity is incoherent")
    return v

def _effective_scenario(request_identity,scenario,present,label="retained scenario"):
    req=_valid_identity(request_identity)
    if type(present) is not bool or type(scenario) is not str or scenario not in SCENARIOS:raise _fail(label+" is invalid")
    expected=req[3] if req[2] else DEFAULT_SCENARIO
    if present != req[2] or scenario != expected:raise _fail(label+" contradicts request identity")
    return req,expected,present

@dataclass(frozen=True,repr=False,init=False,eq=False)
class TaxTestSupportRequest:
    _identity: tuple[object,...]=field(init=False)
    def __init__(self,*,utr,tax_year,scenario=_OMITTED):
        if type(utr) is not str or _UTR.fullmatch(utr) is None: raise _fail("utr must be exactly ten ASCII digits")
        val,present=(None,False) if scenario is _OMITTED else (scenario,True)
        object.__setattr__(self,"_identity",_identity(secrets.token_hex(32),tax_year,val,present)); self._values()
    def _values(self): return _valid_identity(_state(self,TaxTestSupportRequest,_REQ_STATE,"request intent")["_identity"])
    @property
    def tax_year(self): return TaxTestSupportRequest._values(self)[1]
    @property
    def scenario_present(self): return TaxTestSupportRequest._values(self)[2]
    @property
    def scenario(self): return TaxTestSupportRequest._values(self)[3]
    @property
    def request_identity(self): return TaxTestSupportRequest._values(self)
    def __repr__(self): TaxTestSupportRequest._values(self); return "TaxTestSupportRequest([REDACTED])"
    def __eq__(self,o):
        a=TaxTestSupportRequest._values(self)
        if type(o) is not TaxTestSupportRequest:return NotImplemented
        return a==TaxTestSupportRequest._values(o)
    def __hash__(self): return hash(TaxTestSupportRequest._values(self))
    def __copy__(self): TaxTestSupportRequest._values(self); return self
    def __deepcopy__(self,memo): TaxTestSupportRequest._values(self); return self
    def __reduce__(self): return (_restore_request,(TaxTestSupportRequest._values(self),))

def build_tax_test_support_request(*,utr,tax_year,scenario=_OMITTED): return TaxTestSupportRequest(utr=utr,tax_year=tax_year,scenario=scenario)
def _restore_request(identity):
    v=object.__new__(TaxTestSupportRequest); object.__setattr__(v,"_identity",_valid_identity(identity)); TaxTestSupportRequest._values(v); return v
def _tok(v):
    if type(v) is not str or _TOKEN.fullmatch(v) is None: raise _fail("nested identity is invalid")
    return v

@dataclass(frozen=True,repr=False,eq=False)
class TaxEmployment:
    employer_paye_reference:str; tax_taken_off_pay:int|Decimal; unknown_names:frozenset[str]=frozenset(); _token:str=field(default_factory=lambda:secrets.token_hex(32),init=False,repr=False)
    def __getattribute__(self,n):
        if n in _EMP_STATE and not n.startswith("_"): TaxEmployment._values(self)
        return object.__getattribute__(self,n)
    def __post_init__(self): TaxEmployment._values(self)
    def _values(self):
        s=_state(self,TaxEmployment,_EMP_STATE,"employment"); return (_tok(s["_token"]),_text(s["employer_paye_reference"],"employerPayeReference"),_num(s["tax_taken_off_pay"],"taxTakenOffPay"),_names(s["unknown_names"],_EMP,"employment"))
    def __repr__(self): TaxEmployment._values(self); return "TaxEmployment([REDACTED])"
    def __eq__(self,o):
        a=TaxEmployment._values(self)
        if type(o) is not TaxEmployment:return NotImplemented
        return a==TaxEmployment._values(o)
    def __hash__(self): return hash(TaxEmployment._values(self))
    def __copy__(self): TaxEmployment._values(self); return self
    def __deepcopy__(self,m): TaxEmployment._values(self); return self
    def __reduce__(self): return (_restore_emp,TaxEmployment._values(self))

@dataclass(frozen=True,repr=False,eq=False)
class PensionsBenefits:
    other_pensions_and_retirement_annuities:int|Decimal|None=None; incapacity_benefit:int|Decimal|None=None; present_fields:frozenset[str]=frozenset(); unknown_names:frozenset[str]=frozenset(); _token:str=field(default_factory=lambda:secrets.token_hex(32),init=False,repr=False)
    def __getattribute__(self,n):
        if n in _PEN_STATE and not n.startswith("_"): PensionsBenefits._values(self)
        return object.__getattribute__(self,n)
    def __post_init__(self): PensionsBenefits._values(self)
    def _values(self):
        s=_state(self,PensionsBenefits,_PEN_STATE,"pensions"); p=_present(s["present_fields"],_PEN,"pensions"); vals=(s["other_pensions_and_retirement_annuities"],s["incapacity_benefit"])
        for n,v in zip(("otherPensionsAndRetirementAnnuities","incapacityBenefit"),vals):
            if n in p:
                if v is None: raise _fail(n+" cannot be null")
                _num(v,n)
            elif v is not None: raise _fail(n+" must be None when absent")
        return (_tok(s["_token"]),*vals,p,_names(s["unknown_names"],_PEN,"pensions"))
    @property
    def absent_fields(self): return _PEN-PensionsBenefits._values(self)[3]
    def __repr__(self): PensionsBenefits._values(self); return "PensionsBenefits([REDACTED])"
    def __eq__(self,o):
        a=PensionsBenefits._values(self)
        if type(o) is not PensionsBenefits:return NotImplemented
        return a==PensionsBenefits._values(o)
    def __hash__(self): return hash(PensionsBenefits._values(self))
    def __copy__(self): PensionsBenefits._values(self); return self
    def __deepcopy__(self,m): PensionsBenefits._values(self); return self
    def __reduce__(self): return (_restore_pen,PensionsBenefits._values(self))

@dataclass(frozen=True,repr=False,eq=False)
class Refunds:
    tax_refunded_or_set_off:int|Decimal|None=None; present_fields:frozenset[str]=frozenset(); unknown_names:frozenset[str]=frozenset(); _token:str=field(default_factory=lambda:secrets.token_hex(32),init=False,repr=False)
    def __getattribute__(self,n):
        if n in _REF_STATE and not n.startswith("_"): Refunds._values(self)
        return object.__getattribute__(self,n)
    def __post_init__(self): Refunds._values(self)
    def _values(self):
        s=_state(self,Refunds,_REF_STATE,"refunds"); p=_present(s["present_fields"],_REF,"refunds"); v=s["tax_refunded_or_set_off"]
        if "taxRefundedOrSetOff" in p:
            if v is None: raise _fail("taxRefundedOrSetOff cannot be null")
            _num(v,"taxRefundedOrSetOff")
        elif v is not None: raise _fail("taxRefundedOrSetOff must be None when absent")
        return (_tok(s["_token"]),v,p,_names(s["unknown_names"],_REF,"refunds"))
    @property
    def absent_fields(self): return _REF-Refunds._values(self)[2]
    def __repr__(self): Refunds._values(self); return "Refunds([REDACTED])"
    def __eq__(self,o):
        a=Refunds._values(self)
        if type(o) is not Refunds:return NotImplemented
        return a==Refunds._values(o)
    def __hash__(self): return hash(Refunds._values(self))
    def __copy__(self): Refunds._values(self); return self
    def __deepcopy__(self,m): Refunds._values(self); return self
    def __reduce__(self): return (_restore_ref,Refunds._values(self))

def _restore_emp(t,r,n,u):
    v=object.__new__(TaxEmployment)
    for k,x in (("_token",t),("employer_paye_reference",r),("tax_taken_off_pay",n),("unknown_names",u)):object.__setattr__(v,k,x)
    TaxEmployment._values(v);return v
def _restore_pen(t,a,b,p,u):
    v=object.__new__(PensionsBenefits)
    for k,x in (("_token",t),("other_pensions_and_retirement_annuities",a),("incapacity_benefit",b),("present_fields",p),("unknown_names",u)):object.__setattr__(v,k,x)
    PensionsBenefits._values(v);return v
def _restore_ref(t,a,p,u):
    v=object.__new__(Refunds)
    for k,x in (("_token",t),("tax_refunded_or_set_off",a),("present_fields",p),("unknown_names",u)):object.__setattr__(v,k,x)
    Refunds._values(v);return v

def _canon(v):
    if v is None:return b"n"
    if type(v) is bool:return b"b1" if v else b"b0"
    if type(v) is int:return b"i"+str(v).encode()+b";"
    if type(v) is str:
        b=v.encode();return b"s"+str(len(b)).encode()+b":"+b
    if type(v) is Decimal:
        s,d,e=v.as_tuple();return b"d"+bytes((s,))+str(e).encode()+b":"+bytes(d)
    if type(v) is tuple:return b"t"+str(len(v)).encode()+b":"+b"".join(_canon(x) for x in v)
    if type(v) is frozenset:return b"f"+b"".join(sorted(_canon(x) for x in v))
    raise _fail("integrity input type is invalid")

def _register(v,record):
    i=id(v)
    def gone(r):
        if i in _ISSUED and _ISSUED[i][0] is r:_ISSUED.pop(i,None)
    r=weakref.ref(v,gone);_ISSUED[i]=(r,record)

@dataclass(frozen=True,repr=False,init=False,eq=False)
class TaxSummaryCreated:
    _bound:bool=field(init=False);_request_identity:object=field(init=False);_source_identity:object=field(init=False);_integrity:str=field(init=False)
    employments:tuple[TaxEmployment,...]=field(init=False);pensions_benefits:PensionsBenefits=field(init=False);refunds:Refunds=field(init=False);status_code:int=field(init=False);content_type:str=field(init=False);scenario:str=field(init=False);scenario_present:bool=field(init=False);unknown_names:frozenset[str]=field(init=False);completeness:str=field(init=False)
    def __init__(self,*a,**k):raise TypeError("TaxSummaryCreated is boundary-constructed only")
    def __getattribute__(self,n):
        if n in _SUM_STATE and not n.startswith("_"):TaxSummaryCreated._values(self)
        return object.__getattribute__(self,n)
    def _values(self):return _sum_values(self)
    @property
    def request_bound(self):return TaxSummaryCreated._values(self)[0]
    @property
    def request_identity(self):return TaxSummaryCreated._values(self)[1]
    @property
    def source_identity(self):return TaxSummaryCreated._values(self)[2]
    def __repr__(self):return "TaxSummaryCreated([REDACTED], request_bound=%r)"%TaxSummaryCreated._values(self)[0]
    def __eq__(self,o):
        a=TaxSummaryCreated._values(self)
        if type(o) is not TaxSummaryCreated:return NotImplemented
        return a==TaxSummaryCreated._values(o)
    def __hash__(self):return hash(TaxSummaryCreated._values(self))
    def __copy__(self):TaxSummaryCreated._values(self);return self
    def __deepcopy__(self,m):TaxSummaryCreated._values(self);return self
    def __reduce__(self):
        v=TaxSummaryCreated._values(self);return (_restore_sum,(v[0],v[1],v[2],v[3],v[4],v[5],v[8],v[9],v[10]))

def _sum_values(v):
    s=_state(v,TaxSummaryCreated,_SUM_STATE,"summary")
    if type(s["_bound"]) is not bool:raise _fail("binding marker is invalid")
    bound,req,src=s["_bound"],s["_request_identity"],s["_source_identity"]
    if bound:
        req=_valid_identity(req)
        if type(src) is not tuple or len(src)!=2 or type(src[0]) is not str or _TOKEN.fullmatch(src[0]) is None or type(src[1]) is not tuple:raise _fail("source identity is invalid")
        source_request=_valid_identity(src[1])
        if source_request!=req:raise _fail("source identity is incoherent")
        req,scenario,present=_effective_scenario(req,s["scenario"],s["scenario_present"])
    elif req is not None or src is not None:raise _fail("unbound result carries source state")
    es=s["employments"]
    if type(es) is not tuple or len(es)>10000:raise _fail("employments are invalid")
    ev=[]
    for e in es:
        if type(e) is not TaxEmployment:raise _fail("employment member type is invalid")
        ev.append(TaxEmployment._values(e))
    pv=PensionsBenefits._values(s["pensions_benefits"]);rv=Refunds._values(s["refunds"])
    if type(s["status_code"]) is not int or s["status_code"]!=201:raise _fail("status is invalid")
    if type(s["content_type"]) is not str or s["content_type"]!=RESPONSE_CONTENT_TYPE:raise _fail("content type is invalid")
    if not bound:
        scenario=s["scenario"];present=s["scenario_present"]
        if type(scenario) is not str or scenario not in SCENARIOS or type(present) is not bool:raise _fail("retained scenario is invalid")
    unknown=_names(s["unknown_names"],_TOP,"top level")
    if type(s["completeness"]) is not str or s["completeness"]!=COMPLETENESS:raise _fail("completeness is invalid")
    material=(bound,req,src,tuple(ev),pv,rv,201,RESPONSE_CONTENT_TYPE,scenario,present,unknown,COMPLETENESS)
    digest=s["_integrity"]
    if type(digest) is not str or _TOKEN.fullmatch(digest) is None or not secrets.compare_digest(digest,sha256(_canon(material)).hexdigest()):raise _fail("summary integrity is invalid")
    if bound:
        issued=_ISSUED.get(id(v))
        if issued is None or issued[0]() is not v or issued[1]!=(req,src,digest):raise _fail("summary process-local issuance is unsupported")
    return (bound,req,src,es,s["pensions_benefits"],s["refunds"],201,RESPONSE_CONTENT_TYPE,scenario,present,unknown,COMPLETENESS,digest)

def _new(bound,req,src,es,p,r,scenario,present,unknown):
    if type(bound) is not bool:raise _fail("binding marker is invalid")
    if bound:
        req,scenario,present=_effective_scenario(req,scenario,present,"constructed scenario")
        if type(src) is not tuple or len(src)!=2 or type(src[0]) is not str or _TOKEN.fullmatch(src[0]) is None or type(src[1]) is not tuple:raise _fail("source identity is invalid")
        if _valid_identity(src[1])!=req:raise _fail("source identity is incoherent")
    elif req is not None or src is not None:raise _fail("unbound result carries source state")
    material=(bound,req,src,tuple(TaxEmployment._values(x) for x in es),PensionsBenefits._values(p),Refunds._values(r),201,RESPONSE_CONTENT_TYPE,scenario,present,unknown,COMPLETENESS);digest=sha256(_canon(material)).hexdigest();v=object.__new__(TaxSummaryCreated)
    for k,x in (("_bound",bound),("_request_identity",req),("_source_identity",src),("_integrity",digest),("employments",es),("pensions_benefits",p),("refunds",r),("status_code",201),("content_type",RESPONSE_CONTENT_TYPE),("scenario",scenario),("scenario_present",present),("unknown_names",unknown),("completeness",COMPLETENESS)):object.__setattr__(v,k,x)
    if bound:_register(v,(req,src,digest))
    TaxSummaryCreated._values(v);return v

def _restore_sum(bound,req,src,es,p,r,scenario,present,unknown):
    if bound:
        req,scenario,present=_effective_scenario(req,scenario,present,"serialized scenario")
        if type(src) is not tuple or len(src)!=2 or type(src[0]) is not str or _TOKEN.fullmatch(src[0]) is None or type(src[1]) is not tuple:raise _fail("serialized source identity is invalid")
        if _valid_identity(src[1])!=req:raise _fail("serialized source identity is invalid")
        return _new(True,req,src,es,p,r,scenario,present,unknown)
    return _new(False,None,None,es,p,r,scenario,present,unknown)

def _parse(payload):
    o,u=_object(payload,_TOP,"top level")
    if not _TOP<=o.keys():raise _fail("top level is missing a documented member")
    raw=o["employments"]
    if type(raw) is not list or len(raw)>10000:raise _fail("employments must be an exact bounded array")
    es=[]
    for x in raw:
        d,du=_object(x,_EMP,"employment")
        if not _EMP<=d.keys():raise _fail("employment is missing a documented member")
        es.append(TaxEmployment(_text(d["employerPayeReference"],"employerPayeReference"),_num(d["taxTakenOffPay"],"taxTakenOffPay"),du))
    p,pu=_object(o["pensionsAnnuitiesAndOtherStateBenefits"],_PEN,"pensions");pp=frozenset(p.keys()&_PEN);pv={n:_num(p[n],n) for n in pp};pen=PensionsBenefits(pv.get("otherPensionsAndRetirementAnnuities"),pv.get("incapacityBenefit"),pp,pu)
    r,ru=_object(o["refunds"],_REF,"refunds");rp=frozenset(r.keys()&_REF);ref=Refunds(_num(r["taxRefundedOrSetOff"],"taxRefundedOrSetOff") if rp else None,rp,ru)
    return tuple(es),pen,ref,u

def observe_create_tax_summary_response(request,*,status_code,content_type,payload):
    if type(request) is not TaxTestSupportRequest:raise _fail("request has invalid exact type")
    req=TaxTestSupportRequest._values(request)
    if type(status_code) is not int or status_code!=201:raise _fail("undocumented status is not accepted")
    if type(content_type) is not str or content_type!=RESPONSE_CONTENT_TYPE:raise _fail("HTTP 201 requires application/json")
    es,p,r,u=_parse(payload);return _new(True,req,(secrets.token_hex(32),req),es,p,r,req[3] if req[2] else DEFAULT_SCENARIO,req[2],u)

def validate_tax_summary_created(v):TaxSummaryCreated._values(v);return v

@dataclass(frozen=True)
class TaxTestSupportRequestBody:
    """Legacy scenario-only request-body value; not a create intent."""
    scenario:str=DEFAULT_SCENARIO
    def __post_init__(self):_scenario("2000-00",self.scenario,True)

def parse_tax_test_support_request(payload):
    o,u=_object(payload,frozenset({"scenario"}),"request body")
    if u:raise _fail("request body contains an undocumented member")
    return TaxTestSupportRequestBody(DEFAULT_SCENARIO if "scenario" not in o else _scenario("2000-00",o["scenario"],True)[1])

def parse_tax_summary_created(payload,*,status_code,scenario=_OMITTED):
    """Compatibility parse returning an explicitly unbound/unassured value."""
    if type(status_code) is not int or status_code!=201:raise _fail("status is invalid")
    val,present=(DEFAULT_SCENARIO,False) if scenario is _OMITTED else (_scenario("2000-00",scenario,True)[1],True)
    es,p,r,u=_parse(payload);return _new(False,None,None,es,p,r,val,present,u)

__all__=["HMRCPAYETestSupportTaxContractError","TaxTestSupportRequest","TaxTestSupportRequestBody","TaxEmployment","PensionsBenefits","Refunds","TaxSummaryCreated","build_tax_test_support_request","observe_create_tax_summary_response","validate_tax_summary_created","parse_tax_test_support_request","parse_tax_summary_created"]
