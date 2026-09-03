import ast, copy, hashlib, pickle
from decimal import Decimal
from pathlib import Path
import pytest
import reserved.providers.hmrc_paye_test_support_tax_contract as mod
from reserved.providers.hmrc_paye_test_support_tax_contract import (
 HMRCPAYETestSupportTaxContractError as Error, TaxSummaryCreated,
 build_tax_test_support_request, observe_create_tax_summary_response,
 parse_tax_summary_created, parse_tax_test_support_request,
 TaxTestSupportRequestBody, validate_tax_summary_created)

UTR,YEAR="0123456789","2023-24"
def payload(**changes):
 v={"employments":[],"pensionsAnnuitiesAndOtherStateBenefits":{},"refunds":{}};v.update(changes);return v
def request(**kw):return build_tax_test_support_request(utr=kw.pop("utr",UTR),tax_year=kw.pop("tax_year",YEAR),**kw)
def observe(body=None,req=None,**kw):return observe_create_tax_summary_response(req or request(),status_code=kw.pop("status_code",201),content_type=kw.pop("content_type","application/json"),payload=payload() if body is None else body)
class Bomb:
 calls=[]
 def _x(self,*a,**k):self.calls.append(1);raise AssertionError("hook executed")
 __repr__=__str__=__hash__=__eq__=__iter__=__getattribute__=__copy__=__deepcopy__=__reduce__=_x
class S(str):pass
class I(int):pass
class D(Decimal):pass

def test_exact_descriptors_are_bound():
 r=request(scenario="HAPPY_PATH_2")
 assert r.request_identity[4:]==(mod.OPERATION_ID,mod.HTTP_METHOD,mod.PATH_TEMPLATE,mod.API_NAME,mod.API_VERSION,mod.REQUEST_ACCEPT,mod.REQUEST_CONTENT_TYPE,mod.RESPONSE_CONTENT_TYPE,mod.OAUTH_GRANT_TYPE,mod.OAUTH_SCOPES,True,True)
 assert mod.OPERATION_ID=="createTaxSummaryTestData" and mod.OAUTH_SCOPES==frozenset()

@pytest.mark.parametrize("utr",["123456789","12345678901","１２３４５６７８９０",None,1234567890,S(UTR)])
def test_bad_utr_is_rejected_without_echo(utr):
 with pytest.raises(Error) as e:build_tax_test_support_request(utr=utr,tax_year=YEAR)
 assert str(utr) not in str(e.value)
@pytest.mark.parametrize("year",["2023/24","2023-2","٢٠٢٣-٢٤",None,2023,S(YEAR)])
def test_bad_tax_year(year):
 with pytest.raises(Error):build_tax_test_support_request(utr=UTR,tax_year=year)

def test_scenario_omission_default_and_null():
 omitted=request();one=request(scenario="HAPPY_PATH_1");two=request(scenario="HAPPY_PATH_2")
 assert (omitted.scenario,omitted.scenario_present)==(None,False)
 assert (one.scenario,one.scenario_present)==("HAPPY_PATH_1",True)
 assert observe(req=omitted).scenario=="HAPPY_PATH_1" and observe(req=two).scenario=="HAPPY_PATH_2"
 for bad in (None,"HAPPY_PATH_3","",True,S("HAPPY_PATH_1")):
  with pytest.raises(Error):request(scenario=bad)

def test_public_legacy_request_body_type_is_explicit():
 assert parse_tax_test_support_request({})==TaxTestSupportRequestBody("HAPPY_PATH_1")
 assert parse_tax_test_support_request({"scenario":"HAPPY_PATH_2"})==TaxTestSupportRequestBody("HAPPY_PATH_2")
 with pytest.raises(Error):TaxTestSupportRequestBody("HAPPY_PATH_3")

def test_utr_absent_from_all_surfaces_and_derivatives():
 r=request();o=observe(req=r);old=hashlib.sha256(UTR.encode()).hexdigest()
 surfaces=(vars(r),r.request_identity,repr(r),hash(r),vars(o),o.request_identity,o.source_identity,repr(o),copy.copy(r),copy.deepcopy(r))
 assert all(UTR not in repr(x) and old not in repr(x) for x in surfaces)
 assert UTR.encode() not in pickle.dumps(r) and UTR.encode() not in pickle.dumps(o)
 assert request(utr="1111111111")!=request(utr="1111111111")

def test_intent_frozen_non_sendable_and_transport_free():
 r=request()
 with pytest.raises(AttributeError):r.tax_year="2024-25"
 for n in ("url","headers","body","payload","token","credential","client","transport","route","send","persist","method"):assert not hasattr(r,n)

def test_observer_binds_request_source_and_copy_reconstruction():
 r=request(scenario="HAPPY_PATH_2");o=observe(req=r)
 assert o.request_bound and o.request_identity==r.request_identity and o.source_identity[1]==r.request_identity and o.completeness=="UNVERIFIED"
 assert copy.copy(o) is o and copy.deepcopy(o) is o
 clone=pickle.loads(pickle.dumps(o));assert clone.request_bound and clone==o

@pytest.mark.parametrize("scenario",["HAPPY_PATH_1","HAPPY_PATH_2"])
def test_explicit_scenario_reconstruction_retains_exact_request_semantics(scenario):
 r=request(scenario=scenario);o=observe(req=r);clone=pickle.loads(pickle.dumps(o))
 assert (clone.scenario,clone.scenario_present)==(scenario,True)

def test_omitted_scenario_reconstruction_retains_default_with_absence():
 r=request();o=observe(req=r);clone=pickle.loads(pickle.dumps(o))
 assert (clone.scenario,clone.scenario_present)==("HAPPY_PATH_1",False)

@pytest.mark.parametrize("request_scenario,forged_scenario,forged_present",[
 (mod._OMITTED,"HAPPY_PATH_1",True),
 ("HAPPY_PATH_1","HAPPY_PATH_1",False),
 ("HAPPY_PATH_1","HAPPY_PATH_2",True),
 ("HAPPY_PATH_2","HAPPY_PATH_1",True),
])
def test_contradictory_reconstruction_fails_closed(request_scenario,forged_scenario,forged_present):
 r=request() if request_scenario is mod._OMITTED else request(scenario=request_scenario);o=observe(req=r)
 v=TaxSummaryCreated._values(o);issued=set(mod._ISSUED)
 for construct in (mod._restore_sum,mod._new):
  with pytest.raises(Error):construct(v[0],v[1],v[2],v[3],v[4],v[5],forged_scenario,forged_present,v[10])
  assert set(mod._ISSUED)==issued

@pytest.mark.parametrize("field",["scenario","presence"])
def test_hostile_reconstruction_scenario_inputs_fail_without_hooks(field):
 o=observe();v=TaxSummaryCreated._values(o);hostile=Bomb();Bomb.calls=[];issued=set(mod._ISSUED)
 scenario,present=(hostile,v[9]) if field=="scenario" else (v[8],hostile)
 for construct in (mod._restore_sum,mod._new):
  with pytest.raises(Error):construct(v[0],v[1],v[2],v[3],v[4],v[5],scenario,present,v[10])
  assert Bomb.calls==[] and set(mod._ISSUED)==issued

def test_old_parser_is_explicitly_unbound():
 old=parse_tax_summary_created(payload(),status_code=201)
 assert type(old) is TaxSummaryCreated and not old.request_bound
 assert old.request_identity is None and old.source_identity is None and "request_bound=False" in repr(old)

def test_non201_precedes_content_and_body_access():
 Bomb.calls=[]
 with pytest.raises(Error):observe_create_tax_summary_response(request(),status_code=400,content_type=Bomb(),payload=Bomb())
 assert Bomb.calls==[]

def test_every_nested_numeric_presence_unknown_semantic_is_bound():
 o=observe({"employments":[{"employerPayeReference":"A","taxTakenOffPay":Decimal("-0.00"),"futureE":Bomb()}],"pensionsAnnuitiesAndOtherStateBenefits":{"incapacityBenefit":0,"futureP":Bomb()},"refunds":{"taxRefundedOrSetOff":Decimal("1.2300"),"futureR":Bomb()},"futureTop":Bomb()})
 assert o.employments[0].tax_taken_off_pay.as_tuple()==Decimal("-0.00").as_tuple()
 assert o.pensions_benefits.present_fields=={"incapacityBenefit"} and o.pensions_benefits.absent_fields=={"otherPensionsAndRetirementAnnuities"}
 assert o.refunds.tax_refunded_or_set_off.as_tuple()==Decimal("1.2300").as_tuple()
 assert (o.unknown_names,o.employments[0].unknown_names,o.pensions_benefits.unknown_names,o.refunds.unknown_names)==({"futureTop"},{"futureE"},{"futureP"},{"futureR"})

@pytest.mark.parametrize("bad",[True,1.2,"1",None,I(1),D("1"),Decimal("NaN"),Decimal("Infinity"),Decimal("1.0000000000000"),10**18+1])
def test_numeric_exactness(bad):
 with pytest.raises(Error):observe(payload(employments=[{"employerPayeReference":"A","taxTakenOffPay":bad}]))

def test_required_null_and_container_failures():
 bads=({},[],{"employments":[],"refunds":{}},payload(employments={}),payload(refunds={"taxRefundedOrSetOff":None}),payload(pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit":None}))
 for bad in bads:
  with pytest.raises(Error):observe(bad)

def test_unknown_values_never_touched_or_retained():
 Bomb.calls=[];o=observe({"employments":[],"pensionsAnnuitiesAndOtherStateBenefits":{},"refunds":{},"future":Bomb()})
 assert Bomb.calls==[] and "Bomb" not in repr(vars(o)) and o.unknown_names=={"future"}

def clone(v):
 n=object.__new__(type(v));n.__dict__.update(object.__getattribute__(v,"__dict__"));return n

@pytest.mark.parametrize("field,value",[("status_code",200),("content_type","text/plain"),("scenario","HAPPY_PATH_2"),("scenario_present",True),("unknown_names",frozenset({"x"})),("completeness","VERIFIED")])
def test_top_semantic_mutations_detected(field,value):
 o=observe();object.__setattr__(o,field,value)
 with pytest.raises(Error):hash(o)

def test_nested_mutation_and_valid_substitution_detected():
 a=observe(payload(employments=[{"employerPayeReference":"A","taxTakenOffPay":1}]))
 b=observe(payload(employments=[{"employerPayeReference":"A","taxTakenOffPay":1}]))
 object.__setattr__(a,"employments",b.employments)
 with pytest.raises(Error):validate_tax_summary_created(a)
 c=observe(payload(employments=[{"employerPayeReference":"A","taxTakenOffPay":1}]))
 object.__setattr__(c.employments[0],"tax_taken_off_pay",2)
 with pytest.raises(Error):repr(c)

def test_identical_payload_cross_request_and_coordinated_relabel_fail():
 a,b=observe(req=request()),observe(req=request());forged=clone(a)
 for n in ("_request_identity","_source_identity","_integrity"):object.__setattr__(forged,n,object.__getattribute__(b,n))
 for op in (repr,hash,copy.copy,copy.deepcopy,pickle.dumps,validate_tax_summary_created):
  with pytest.raises(Error):op(forged)

@pytest.mark.parametrize("change",["missing","extra","subclass","hostile"])
def test_low_level_bad_state_prevalidates_without_hooks(change):
 bad=clone(observe())
 if change=="missing":del bad.__dict__["status_code"]
 elif change=="extra":bad.__dict__["extra"]=Bomb()
 elif change=="subclass":bad.__dict__["status_code"]=I(201)
 else:bad.__dict__["employments"]=Bomb()
 Bomb.calls=[]
 for op in (repr,hash,copy.copy,copy.deepcopy,pickle.dumps):
  with pytest.raises(Error):op(bad)
  assert Bomb.calls==[]

def test_hostile_member_all_protocol_surfaces_prevalidate():
 good=observe();bad=clone(good);bad.__dict__["pensions_benefits"]=Bomb();Bomb.calls=[]
 for op in (lambda:bad==good,lambda:good==bad,lambda:getattr(bad,"pensions_benefits"),lambda:hash(bad),lambda:repr(bad),lambda:copy.copy(bad),lambda:copy.deepcopy(bad),lambda:pickle.dumps(bad)):
  with pytest.raises(Error):op()
  assert Bomb.calls==[]

def test_hostile_nested_source_identity_prevalidates_before_equality_hook():
 bad=clone(observe());source=object.__getattribute__(bad,"_source_identity")
 object.__setattr__(bad,"_source_identity",(source[0],(Bomb(),)));Bomb.calls=[]
 for op in (repr,hash,copy.copy,copy.deepcopy,pickle.dumps):
  with pytest.raises(Error):op(bad)
  assert Bomb.calls==[]

def test_no_network_credentials_routing_persistence_or_activation():
 tree=ast.parse(Path(mod.__file__).read_text());roots={(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}|{a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
 assert roots.isdisjoint({"requests","httpx","urllib","socket","http","subprocess","aiohttp"})
 source=Path(mod.__file__).read_text()
 for x in ("https://api.service.hmrc.gov.uk","Authorization","ProviderRequest","urlopen"):assert x not in source
