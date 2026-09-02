"""Adversarial tests for the network-inert Winter Fuel fixture contract."""

import ast
import copy
import pickle
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import reserved.providers.hmrc_paye_test_support_winter_fuel_contract as contract
from reserved.providers.hmrc_paye_test_support_winter_fuel_contract import (
    HMRCPayeTestSupportWinterFuelContractError,
    WinterFuelCreateRequestIntent,
    WinterFuelCreateResponseObservation,
    WinterFuelExpectedJsonObservation,
    WinterFuelNon201Observation,
    build_winter_fuel_create_request,
    observe_winter_fuel_create_response,
)
from reserved.providers.http_boundary import ProviderRequest


NINO = "SA123456Z"
YEAR = "2025-26"


class Hostile:
    def __repr__(self): raise RuntimeError("repr touched")
    def __str__(self): raise RuntimeError("str touched")
    def __eq__(self, other): raise RuntimeError("comparison touched")
    def __hash__(self): raise RuntimeError("hash touched")
    def __bool__(self): raise RuntimeError("truth touched")
    def __iter__(self): raise RuntimeError("iteration touched")


class StrSub(str): pass
class IntSub(int): pass
class DecimalSub(Decimal): pass
class DictSub(dict): pass
class FrozenSub(frozenset): pass


def request(**changes):
    values = {"nino": NINO, "tax_year": YEAR, "scenario": "HAPPY_PATH_1"}
    values.update(changes)
    return build_winter_fuel_create_request(**values)


def observe(payload, **changes):
    values = {"status_code": 201, "content_type": "application/json", "payload": payload}
    values.update(changes)
    return observe_winter_fuel_create_response(request(), **values)


def test_literal_endpoint_facts_are_exact():
    assert contract.OPERATION_ID == "createWinterFuelPaymentAmountTestData"
    assert contract.HTTP_METHOD == "POST"
    assert contract.PATH_TEMPLATE == "/individual-paye-test-support/{nino}/winter-fuel-payment-amount/annual-summary/{taxYear}"
    assert contract.API_VERSION == "2.1"
    assert contract.SANDBOX_ONLY is True
    assert contract.ACCEPT == "application/vnd.hmrc.2.1+json"
    assert contract.JSON_CONTENT_TYPE == "application/json"
    assert contract.OAUTH_GRANT_TYPE == "client_credentials"
    assert contract.OAUTH_SCOPES == frozenset()
    assert contract.SCENARIOS == frozenset({"HAPPY_PATH_1", "HAPPY_PATH_2", "UNHAPPY_PATH_500"})
    assert contract.COMPLETENESS == "UNVERIFIED"


@pytest.mark.parametrize("nino", ["AA000000A", "ZZ999999Z", "SA123456E"])
def test_exact_documented_nino_pattern_accepts_any_final_ascii_uppercase(nino):
    assert request(nino=nino).tax_year == YEAR


@pytest.mark.parametrize("nino", ["SA123456", "SA123456AA", "sa123456A", "SA１２３４５６A", StrSub(NINO), None, Hostile()])
def test_nino_rejects_invalid_subclass_null_and_hostile_without_echo(nino):
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError) as exc:
        request(nino=nino)
    assert NINO not in str(exc.value)


@pytest.mark.parametrize("year", ["2025-2", "２０２５-２６", StrSub(YEAR), None, Hostile()])
def test_tax_year_is_exact_ascii_pattern(year):
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): request(tax_year=year)


def test_scenario_omission_presence_and_explicit_null_are_distinct():
    omitted = build_winter_fuel_create_request(nino=NINO, tax_year=YEAR)
    assert (omitted.scenario, omitted.scenario_present) == (None, False)
    for scenario in contract.SCENARIOS:
        present = request(scenario=scenario)
        assert (present.scenario, present.scenario_present) == (scenario, True)
    for make in (
        lambda: build_winter_fuel_create_request(nino=NINO, tax_year=YEAR, scenario=None),
        lambda: WinterFuelCreateRequestIntent(nino=NINO, tax_year=YEAR, scenario=None),
        lambda: replace(request(), nino="QQ000000A", scenario=None),
    ):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): make()
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): request(scenario=StrSub("HAPPY_PATH_1"))
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): request(scenario=Hostile())


def test_nino_is_discarded_from_all_state_and_errors():
    item = request()
    assert set(vars(item)) == {"tax_year", "scenario", "scenario_present"}
    candidates = [item, copy.copy(item), copy.deepcopy(item), pickle.loads(pickle.dumps(item))]
    for candidate in candidates:
        assert NINO not in repr(candidate)
        assert NINO not in str(vars(candidate))
        assert NINO.encode() not in pickle.dumps(candidate)
    assert request(nino="QQ000000A") == request(nino="ZZ999999Z")
    assert hash(request(nino="QQ000000A")) == hash(request(nino="ZZ999999Z"))
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError) as exc: request(nino=NINO.lower())
    assert NINO.lower() not in str(exc.value)


def test_request_is_frozen_non_sendable_and_replace_revalidates():
    item = request()
    assert not issubclass(WinterFuelCreateRequestIntent, ProviderRequest)
    for name in ("url", "headers", "body", "token", "credential", "client", "transport", "method"):
        assert not hasattr(item, name)
    with pytest.raises(AttributeError): item.tax_year = "x"
    assert replace(item, nino="QQ000000A") == item
    with pytest.raises(TypeError): replace(item)
    with pytest.raises(TypeError): WinterFuelCreateRequestIntent(NINO, YEAR)


def test_response_requires_exact_request_and_has_no_free_identity_inputs():
    payload = {"expectedStatus": 200}
    for bad in (object(), Hostile()):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            observe_winter_fuel_create_response(bad, status_code=201, content_type="application/json", payload=payload)
    class RequestSub(WinterFuelCreateRequestIntent): pass
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
        observe_winter_fuel_create_response(RequestSub(nino=NINO, tax_year=YEAR), status_code=201, content_type="application/json", payload=payload)
    with pytest.raises(TypeError):
        WinterFuelCreateResponseObservation(request=request(), expected_status=200, expected_json=None, expected_json_present=False, tax_year=YEAR)


def test_exact_201_and_media_type_policy():
    assert isinstance(observe({"expectedStatus": 200}), WinterFuelCreateResponseObservation)
    for media in ("Application/JSON", "application/json; charset=utf-8", StrSub("application/json"), None, Hostile()):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": 200}, content_type=media)
    for status in (True, 201.0, IntSub(201), Decimal(201), Hostile()):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": 200}, status_code=status)


def test_required_optional_shape_and_presence_are_preserved():
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({})
    omitted = observe({"expectedStatus": 200})
    assert omitted.expected_json is None and omitted.expected_json_present is False
    present = observe({"expectedStatus": Decimal("2E+2"), "expectedJson": {"winterFuelPaymentAmount": Decimal("250.15")}})
    assert present.expected_json_present is True
    assert present.expected_status.as_tuple() == Decimal("2E+2").as_tuple()
    assert present.expected_json.winter_fuel_payment_amount == Decimal("250.15")
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": 200, "expectedJson": None})
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": 200, "expectedJson": {}})


@pytest.mark.parametrize("value", [0, -7, Decimal("0"), Decimal("-0"), Decimal("-2.50"), Decimal("1E+18"), Decimal("1E-12")])
def test_exact_valid_numeric_identities_are_preserved(value):
    obs = observe({"expectedStatus": value, "expectedJson": {"winterFuelPaymentAmount": value}})
    assert type(obs.expected_status) is type(value)
    assert type(obs.expected_json.winter_fuel_payment_amount) is type(value)
    if type(value) is Decimal:
        assert obs.expected_status.as_tuple() == value.as_tuple()
        assert obs.expected_json.winter_fuel_payment_amount.as_tuple() == value.as_tuple()


@pytest.mark.parametrize("value", [None, True, 1.0, "1", IntSub(1), DecimalSub("1"), Decimal("NaN"), Decimal("Infinity"), 10**18 + 1, Decimal("1E+19"), Decimal("1E-13"), Hostile()])
def test_numbers_reject_null_bool_float_coercion_subclasses_nonfinite_and_out_of_bounds(value):
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": value})
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe({"expectedStatus": 200, "expectedJson": {"winterFuelPaymentAmount": value}})


@pytest.mark.parametrize("value", [Decimal("0E+999999999"), Decimal("-0E+999999999")])
@pytest.mark.parametrize("field", ["expectedStatus", "winterFuelPaymentAmount"])
def test_excessive_positive_exponent_zero_is_rejected_by_parser_constructor_and_replace(value, field):
    req = request()
    nested = WinterFuelExpectedJsonObservation(winter_fuel_payment_amount=0)
    obs = WinterFuelCreateResponseObservation(
        request=req,
        expected_status=200,
        expected_json=nested,
        expected_json_present=True,
    )
    if field == "expectedStatus":
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            observe({"expectedStatus": value})
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            WinterFuelCreateResponseObservation(
                request=req,
                expected_status=value,
                expected_json=None,
                expected_json_present=False,
            )
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            replace(obs, request=req, expected_status=value)
    else:
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            observe({"expectedStatus": 200, "expectedJson": {"winterFuelPaymentAmount": value}})
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            WinterFuelExpectedJsonObservation(winter_fuel_payment_amount=value)
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            replace(nested, winter_fuel_payment_amount=value)


def test_open_schema_retains_only_safe_bounded_unknown_names_without_values():
    hostile = Hostile()
    obs = observe({"extra": hostile, "expectedStatus": 200, "expectedJson": {"winterFuelPaymentAmount": 0, "nestedExtra": hostile}})
    assert obs.unknown_names == frozenset({"extra"})
    assert obs.expected_json.unknown_names == frozenset({"nestedExtra"})
    assert not any(value is hostile for value in vars(obs).values())
    assert not any(value is hostile for value in vars(obs.expected_json).values())
    for payload in (
        {StrSub("expectedStatus"): 200},
        {"expectedStatus": 200, StrSub("expectedJson"): {}},
        {"expectedStatus": 200, "expectedJson": {StrSub("winterFuelPaymentAmount"): 1}},
        {"expectedStatus": 200, "bad\u202e": hostile},
    ):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe(payload)
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): observe(DictSub(expectedStatus=200))


def test_unknown_name_constructor_invariants_are_exact_safe_and_disjoint():
    for names in ({"x"}, FrozenSub({"x"}), frozenset({"expectedStatus"}), frozenset({"bad\x00"})):
        with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
            WinterFuelCreateResponseObservation(request=request(), expected_status=200, expected_json=None, expected_json_present=False, unknown_names=names)
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError):
        WinterFuelExpectedJsonObservation(
            winter_fuel_payment_amount=1,
            unknown_names=frozenset({"winterFuelPaymentAmount"}),
        )


def test_non_201_records_only_status_and_never_touches_or_retains_body_or_media():
    hostile = Hostile()
    obs = observe_winter_fuel_create_response(request(), status_code=404, content_type=hostile, payload=hostile)
    assert type(obs) is WinterFuelNon201Observation
    assert set(vars(obs)) == {"status_code", "completeness", "tax_year", "scenario", "scenario_present"}
    assert obs.status_code == 404 and obs.completeness == "UNVERIFIED"
    assert not any(value is hostile for value in vars(obs).values())


def test_direct_replace_copy_deepcopy_pickle_coherence():
    req = request(scenario="HAPPY_PATH_2")
    nested = WinterFuelExpectedJsonObservation(
        winter_fuel_payment_amount=Decimal("2.5"),
        unknown_names=frozenset({"future"}),
    )
    obs = WinterFuelCreateResponseObservation(request=req, expected_status=Decimal("404"), expected_json=nested, expected_json_present=True, unknown_names=frozenset({"topFuture"}))
    for candidate in (obs, copy.copy(obs), copy.deepcopy(obs), pickle.loads(pickle.dumps(obs))):
        assert candidate == obs and candidate.completeness == "UNVERIFIED"
    assert replace(obs, request=req) == obs
    with pytest.raises(TypeError): replace(obs)
    with pytest.raises(HMRCPayeTestSupportWinterFuelContractError): replace(obs, request=req, expected_json=None)
    non201 = WinterFuelNon201Observation(request=req, status_code=500)
    for candidate in (copy.copy(non201), copy.deepcopy(non201), pickle.loads(pickle.dumps(non201)), replace(non201, request=req)):
        assert candidate == non201


def test_module_ast_has_no_forbidden_operational_surfaces():
    path = Path(contract.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert imports.isdisjoint({"requests", "httpx", "urllib", "socket", "subprocess", "sqlite3", "oauthlib"})
    names = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert (names | attributes).isdisjoint({
        "authorization", "token", "credential", "client", "transport",
        "send", "persist", "save", "activate", "dispatch",
        "canonical", "liability", "cash", "customer", "hicbc",
    })
