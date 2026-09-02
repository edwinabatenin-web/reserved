"""Focused tests for the network-inert Child Benefit fixture contract."""

import ast
import copy
import pickle
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.providers.hmrc_paye_test_support_child_benefit_contract import (
    ACCEPT,
    API_VERSION,
    COMPLETENESS,
    HTTP_METHOD,
    JSON_CONTENT_TYPE,
    OAUTH_SCOPES,
    OPERATION_ID,
    PATH_TEMPLATE,
    SANDBOX_ONLY,
    SCENARIOS,
    SUCCESS_STATUS,
    ChildBenefitCreateRequestIntent,
    ChildBenefitCreateResponseObservation,
    ChildBenefitExpectedJsonObservation,
    HMRCPayeTestSupportChildBenefitContractError,
    build_child_benefit_create_request,
    observe_child_benefit_create_response,
)

UTR = "0123456789"
TAX_YEAR = "2025-26"


def request(*, utr=UTR, tax_year=TAX_YEAR, scenario="HAPPY_PATH_1"):
    return build_child_benefit_create_request(
        utr=utr, tax_year=tax_year, scenario=scenario
    )


def observe(payload, *, status=201, req=None, content_type="application/json"):
    return observe_child_benefit_create_response(
        req or request(), status_code=status, content_type=content_type, payload=payload
    )


class Hostile:
    def __getattribute__(self, name):
        if name == "__class__":
            return object.__getattribute__(self, name)
        raise AssertionError("hostile value inspected")

    def __repr__(self):
        raise AssertionError("hostile value represented")

    def __str__(self):
        raise AssertionError("hostile value stringified")

    def __iter__(self):
        raise AssertionError("hostile value traversed")

    def __copy__(self):
        raise AssertionError("hostile value copied")

    def __deepcopy__(self, memo):
        raise AssertionError("hostile value deep-copied")


class IntSubclass(int):
    pass


class DecimalSubclass(Decimal):
    pass


class DocumentedNameSubclass(str):
    pass


class HostileNameSubclass(str):
    __hash__ = str.__hash__

    def __eq__(self, other):
        raise AssertionError("hostile name compared during classification")


def test_documented_constants_and_isolation_metadata():
    assert OPERATION_ID == "createChildBenefitEntitlementTestData"
    assert HTTP_METHOD == "POST"
    assert PATH_TEMPLATE.endswith("child-benefit-entitlement/annual-summary/{taxYear}")
    assert API_VERSION == "2.1"
    assert ACCEPT == "application/vnd.hmrc.2.1+json"
    assert JSON_CONTENT_TYPE == "application/json"
    assert SUCCESS_STATUS == 201
    assert SANDBOX_ONLY is True
    assert OAUTH_SCOPES == frozenset()
    assert COMPLETENESS == "UNVERIFIED"


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_all_three_scenarios_are_preserved_without_response_inference(scenario):
    result = observe({"expectedStatus": 299}, req=request(scenario=scenario))
    assert result.scenario == scenario
    assert result.scenario_present is True
    assert result.expected_status == 299
    assert result.expected_json_present is False


def test_scenario_omission_selects_default_semantics_but_preserves_absence():
    req = build_child_benefit_create_request(utr=UTR, tax_year=TAX_YEAR)
    assert req.scenario is None
    assert req.scenario_present is False
    result = observe({"expectedStatus": 200}, req=req)
    assert (result.scenario, result.scenario_present) == (None, False)


@pytest.mark.parametrize("constructor", [
    lambda: build_child_benefit_create_request(
        utr=UTR, tax_year=TAX_YEAR, scenario=None
    ),
    lambda: ChildBenefitCreateRequestIntent(
        utr=UTR, tax_year=TAX_YEAR, scenario=None
    ),
])
def test_explicit_null_scenario_rejected_at_public_request_boundaries(constructor):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        constructor()


@pytest.mark.parametrize("bad", [None, 1234567890, True, "123", "１２３４５６７８９０", "123456789A"])
def test_exact_utr_validation(bad):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        build_child_benefit_create_request(utr=bad, tax_year=TAX_YEAR)


@pytest.mark.parametrize("bad", [None, 202526, True, "25-26", "2025/26", "２０２５-２６", "2025-2"])
def test_exact_tax_year_validation(bad):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        build_child_benefit_create_request(utr=UTR, tax_year=bad)


def test_utr_is_immediately_discarded_from_copy_pickle_and_identity():
    a = request(utr="1111111111")
    b = request(utr="2222222222")
    assert vars(a) == {"tax_year": TAX_YEAR, "scenario": "HAPPY_PATH_1", "scenario_present": True}
    assert a == b and hash(a) == hash(b)
    for item in (a, copy.copy(a), copy.deepcopy(a), pickle.loads(pickle.dumps(a))):
        assert "1111111111" not in repr(item)
        assert b"1111111111" not in pickle.dumps(item)


@pytest.mark.parametrize("bad", [True, False, 201.0, "201", Decimal("201"), IntSubclass(201)])
def test_create_status_requires_exact_builtin_201_type(bad):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({"expectedStatus": 200}, status=bad)


def test_non_201_does_not_inspect_content_type_or_body():
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe(Hostile(), status=500, content_type=Hostile())


def test_response_requires_validated_request_and_binds_exact_request_facts():
    req = request(tax_year="2024-25", scenario="HAPPY_PATH_2")
    result = observe({"expectedStatus": 404}, req=req)
    assert (result.tax_year, result.scenario, result.scenario_present) == (
        "2024-25", "HAPPY_PATH_2", True
    )
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe_child_benefit_create_response(
            object(), status_code=201, content_type="application/json", payload={}
        )
    with pytest.raises(TypeError):
        ChildBenefitCreateResponseObservation(
            expected_status=404, expected_json=None, expected_json_present=False
        )
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        ChildBenefitCreateResponseObservation(
            request=object(), expected_status=404,
            expected_json=None, expected_json_present=False,
        )


def test_expected_json_omission_presence_and_null_are_distinct():
    omitted = observe({"expectedStatus": 404})
    assert omitted.expected_json is None and omitted.expected_json_present is False
    present = observe({"expectedStatus": 200, "expectedJson": {"childBenefitEntitlement": 0}})
    assert present.expected_json_present is True
    assert present.expected_json.child_benefit_entitlement == 0
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({"expectedStatus": 200, "expectedJson": None})


def test_required_members_fail_closed():
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({})
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({"expectedStatus": 200, "expectedJson": {}})


@pytest.mark.parametrize("value", [0, Decimal("0"), Decimal("450.9900"), -1, Decimal("-0.01")])
def test_exact_entitlement_is_preserved_without_sign_or_rounding_rules(value):
    result = observe({"expectedStatus": 200, "expectedJson": {"childBenefitEntitlement": value}})
    retained = result.expected_json.child_benefit_entitlement
    assert type(retained) is type(value)
    assert retained.as_tuple() == value.as_tuple() if type(value) is Decimal else retained == value


@pytest.mark.parametrize("value", [True, 1.0, "1", Decimal("NaN"), Decimal("Infinity"), IntSubclass(1), DecimalSubclass("1"), 10**19, Decimal("1.0000000000001"), Decimal("1E+30")])
def test_entitlement_rejects_bool_float_nonfinite_subclass_and_excessive_forms(value):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({"expectedStatus": 200, "expectedJson": {"childBenefitEntitlement": value}})


@pytest.mark.parametrize("value", [True, 200.0, "200", Decimal("200"), IntSubclass(200)])
def test_expected_status_requires_exact_builtin_integer(value):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe({"expectedStatus": value})


def test_open_schema_captures_names_without_touching_or_retaining_values():
    outer, inner = Hostile(), Hostile()
    result = observe({
        "expectedStatus": 200,
        "outerExtension": outer,
        "expectedJson": {"childBenefitEntitlement": 0, "innerExtension": inner},
    })
    assert result.unknown_names == frozenset({"outerExtension"})
    assert result.expected_json.unknown_names == frozenset({"innerExtension"})
    assert outer not in vars(result).values()
    assert inner not in vars(result.expected_json).values()
    repr(result)
    copy.deepcopy(result)
    pickle.loads(pickle.dumps(result))


@pytest.mark.parametrize("layer", ["top", "inner"])
def test_documented_name_subclasses_are_rejected_before_classification(layer):
    if layer == "top":
        payload = {DocumentedNameSubclass("expectedStatus"): 200}
    else:
        payload = {
            "expectedStatus": 200,
            "expectedJson": {DocumentedNameSubclass("childBenefitEntitlement"): 0},
        }
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe(payload)


def test_hostile_name_hooks_are_not_invoked_to_classify_a_member_name():
    name = HostileNameSubclass("expectedStatus")
    payload = {name: 200}
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe(payload)


@pytest.mark.parametrize("name", ["expectedStatus", "expectedJson"])
def test_direct_top_observation_rejects_documented_name_in_unknown_names(name):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        ChildBenefitCreateResponseObservation(
            request=request(),
            expected_status=200, expected_json=None, expected_json_present=False,
            unknown_names=frozenset({name}),
        )


def test_direct_expected_json_rejects_documented_name_in_unknown_names():
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        ChildBenefitExpectedJsonObservation(0, frozenset({"childBenefitEntitlement"}))


@pytest.mark.parametrize("name", ["bad\nname", "bad\u200dname", "bad\ue000name", "x" * 257])
@pytest.mark.parametrize("layer", ["top", "inner"])
def test_unsafe_or_overlong_unknown_names_rejected(layer, name):
    payload = {"expectedStatus": 200}
    if layer == "top":
        payload[name] = Hostile()
    else:
        payload["expectedJson"] = {"childBenefitEntitlement": 1, name: Hostile()}
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe(payload)


def test_direct_observations_replace_copy_deepcopy_pickle_are_coherent():
    inner = ChildBenefitExpectedJsonObservation(Decimal("12.30"), frozenset({"x"}))
    req = request()
    result = ChildBenefitCreateResponseObservation(
        request=req,
        expected_status=200, expected_json=inner, expected_json_present=True,
        unknown_names=frozenset({"y"}),
    )
    assert "request" not in vars(result)
    assert replace(inner, child_benefit_entitlement=0).child_benefit_entitlement == 0
    for clone in (copy.copy(result), copy.deepcopy(result), pickle.loads(pickle.dumps(result))):
        assert clone == result
        assert "request" not in vars(clone)
        assert UTR not in repr(clone)
        assert UTR.encode() not in pickle.dumps(clone)
    with pytest.raises(TypeError):
        replace(result)
    changed_request = request(utr="9999999999", tax_year="2024-25", scenario="HAPPY_PATH_2")
    changed = replace(result, request=changed_request, expected_status=404)
    assert (changed.tax_year, changed.scenario, changed.scenario_present) == (
        "2024-25", "HAPPY_PATH_2", True
    )
    with pytest.raises(TypeError):
        replace(result, request=req, tax_year="2024-25")
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        replace(result, request=object())
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        replace(result, request=req, expected_json_present=False)
    with pytest.raises(FrozenInstanceError):
        result.expected_status = 500


def test_request_replace_reenters_utr_validation_boundary():
    req = request()
    with pytest.raises(TypeError):
        replace(req)
    changed = replace(req, utr="9999999999", tax_year="2024-25")
    assert changed.tax_year == "2024-25"
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        replace(req, utr="bad", scenario=None)


def test_module_has_no_network_credentials_persistence_activation_or_product_imports():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports <= {"__future__", "re", "unicodedata", "dataclasses", "decimal"}
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import requests", "import httpx", "import urllib", "import socket",
        "ProviderRequest", "reserved.engines", "HicbcEngine",
    ):
        assert forbidden.lower() not in source.lower()
