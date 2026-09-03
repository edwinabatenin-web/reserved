"""Focused tests for the network-inert Child Benefit fixture contract."""

import ast
import copy
import hashlib
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
    SANDBOX_ORIGIN,
    ChildBenefitCreateRequestIntent,
    ChildBenefitCreateResponseObservation,
    ChildBenefitExpectedJsonObservation,
    HMRCPayeTestSupportChildBenefitContractError,
    build_child_benefit_create_request,
    observe_child_benefit_create_response,
    validate_child_benefit_create_response_observation,
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
    def __hash__(self):
        raise AssertionError("hostile value hashed")

    def __eq__(self, other):
        raise AssertionError("hostile value compared")

    def __bool__(self):
        raise AssertionError("hostile value truth-tested")

    def __sub__(self, other):
        raise AssertionError("hostile value subtracted")

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

    def __reduce__(self):
        raise AssertionError("hostile value reduced")

    def __reduce_ex__(self, protocol):
        raise AssertionError("hostile value reduced")


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


class ArmedKey:
    """A dict key that is hashable exactly once, then rejects re-hashing."""

    def __init__(self):
        self.calls = 0

    def __hash__(self):
        self.calls += 1
        if self.calls > 1:
            raise AssertionError("armed state key re-hashed before rejection")
        return 0

    def __eq__(self, other):
        return self is other


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
    assert SANDBOX_ORIGIN == "https://test-api.service.hmrc.gov.uk"


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
    assert not hasattr(a, "__dict__")
    assert a != b and hash(a) != hash(b)
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


def test_malformed_request_fails_before_status_content_or_body_access():
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        observe_child_benefit_create_response(
            object(), status_code=Hostile(), content_type=Hostile(), payload=Hostile()
        )


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
    with pytest.raises(TypeError):
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
    assert all(item is not outer for item in vars(result).values())
    assert all(item is not inner for item in vars(result.expected_json).values())
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
    with pytest.raises(TypeError):
        ChildBenefitCreateResponseObservation(
            request=request(),
            expected_status=200, expected_json=None, expected_json_present=False,
            unknown_names=frozenset({name}),
        )


def test_direct_expected_json_rejects_documented_name_in_unknown_names():
    with pytest.raises(TypeError):
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


def test_observer_only_observations_copy_deepcopy_pickle_are_coherent():
    req = request()
    result = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "x": object()}, "y": object()}, req=req)
    assert result.request is req
    for clone in (copy.copy(result), copy.deepcopy(result), pickle.loads(pickle.dumps(result))):
        assert clone == result
        assert validate_child_benefit_create_response_observation(clone) is clone
        assert UTR not in repr(clone)
        assert UTR.encode() not in pickle.dumps(clone)
    with pytest.raises(TypeError): replace(result)
    with pytest.raises(FrozenInstanceError):
        result.expected_status = 500


def test_distinct_requests_cannot_be_coherently_relabelled_even_for_same_payload():
    left_request = request(utr="1111111111")
    right_request = request(utr="2222222222")
    left = observe({"expectedStatus": 200}, req=left_request)
    right = observe({"expectedStatus": 200}, req=right_request)
    assert left != right and hash(left) != hash(right)
    for operation in (
        lambda: validate_child_benefit_create_response_observation(left),
        lambda: left == right, lambda: hash(left), lambda: repr(left),
        lambda: copy.copy(left), lambda: copy.deepcopy(left),
        lambda: pickle.loads(pickle.dumps(left)),
    ):
        assert operation() is not None
    for name in ("request", "_request_binding", "_source_binding"):
        forged = observe({"expectedStatus": 200}, req=left_request)
        object.__setattr__(forged, name, object.__getattribute__(right, name))
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            validate_child_benefit_create_response_observation(forged)


@pytest.mark.parametrize("field,value", [
    ("tax_year", "2024-25"), ("scenario", "HAPPY_PATH_2"),
    ("scenario_present", False), ("status_code", 200),
    ("content_type", "text/plain"), ("expected_status", 500),
    ("expected_json_present", False), ("unknown_names", frozenset({"changed"})),
    ("completeness", "VERIFIED"), ("_observation_integrity", "0" * 64),
])
def test_every_retained_top_level_semantic_is_integrity_bound(field, value):
    result = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "inner": object()},
        "outer": object()})
    object.__setattr__(result, field, value)
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(result)


@pytest.mark.parametrize("field,value", [
    ("child_benefit_entitlement", 1230),
    ("child_benefit_entitlement", Decimal("12.3")),
    ("unknown_names", frozenset({"other"})),
])
def test_every_expected_json_semantic_including_type_and_scale_is_bound(field, value):
    result = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "inner": object()}})
    object.__setattr__(result.expected_json, field, value)
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(result)


def test_direct_replace_subclass_and_malformed_low_level_state_fail_closed():
    class ResponseSubclass(ChildBenefitCreateResponseObservation):
        pass
    with pytest.raises(TypeError): ChildBenefitCreateResponseObservation()
    with pytest.raises(TypeError): ChildBenefitExpectedJsonObservation()
    with pytest.raises(TypeError): replace(observe({"expectedStatus": 200}))
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(object.__new__(ResponseSubclass))
    for mutation in ("missing", "extra", "hostile"):
        result = observe({"expectedStatus": 200})
        state = object.__getattribute__(result, "__dict__")
        if mutation == "missing": state.pop("tax_year")
        elif mutation == "extra": state["extra"] = None
        else: state["expected_status"] = Hostile()
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            validate_child_benefit_create_response_observation(result)


def test_instance_shadow_hooks_are_never_dispatched_before_exact_state_validation():
    result = observe({"expectedStatus": 200})
    state = object.__getattribute__(result, "__dict__")
    state["validate_child_benefit_create_response_observation"] = Hostile()
    state["__dataclass_fields__"] = Hostile()
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(result)


def test_armed_state_key_is_rejected_before_rehashing():
    result = observe({"expectedStatus": 200})
    state = object.__getattribute__(result, "__dict__")
    armed = ArmedKey()
    state[armed] = None
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(result)
    assert armed.calls == 1


def test_armed_state_key_is_rejected_without_hashing_when_length_matches():
    result = observe({"expectedStatus": 200})
    state = object.__getattribute__(result, "__dict__")
    armed = ArmedKey()
    state.pop("tax_year")
    state[armed] = None
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(result)
    assert armed.calls == 1


def test_response_direct_reads_fail_closed_after_low_level_mutation():
    result = observe({"expectedStatus": 200})
    object.__setattr__(result, "expected_status", Hostile())
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        result.expected_status
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        result.tax_year


def test_nested_direct_reads_fail_closed_after_low_level_mutation():
    result = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}})
    nested = result.expected_json
    object.__setattr__(nested, "child_benefit_entitlement", Hostile())
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.child_benefit_entitlement
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.unknown_names


def test_nested_equality_is_fail_closed_in_both_operand_directions():
    left = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    right = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    assert left == right and right == left
    assert hash(left) == hash(right)
    different_scale = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.3")}}).expected_json
    assert left != different_scale
    object.__setattr__(left, "child_benefit_entitlement", Hostile())
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        left == right
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        right == left


def test_nested_lifecycle_is_coherent_and_fail_closed_after_mutation():
    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    assert copy.copy(nested) is nested
    assert copy.deepcopy(nested) is nested
    assert pickle.loads(pickle.dumps(nested)) == nested
    object.__setattr__(nested, "child_benefit_entitlement", Hostile())
    for operation in (
        lambda: hash(nested),
        lambda: repr(nested),
        lambda: copy.copy(nested),
        lambda: copy.deepcopy(nested),
        lambda: pickle.loads(pickle.dumps(nested)),
    ):
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            operation()


def _assert_nested_fails_closed_on_all_surfaces(nested, other):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.child_benefit_entitlement
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.unknown_names
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested == other
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        other == nested
    for operation in (
        lambda: hash(nested),
        lambda: repr(nested),
        lambda: copy.copy(nested),
        lambda: copy.deepcopy(nested),
        lambda: pickle.dumps(nested),
    ):
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            operation()


def test_nested_valid_to_valid_entitlement_mutation_is_rejected():
    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    assert pickle.loads(pickle.dumps(nested)) == nested
    object.__setattr__(nested, "child_benefit_entitlement", Decimal("99.99"))
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_valid_to_valid_unknown_presence_mutation_is_rejected():
    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    object.__setattr__(nested, "unknown_names", frozenset({"newName"}))
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_valid_to_valid_unknown_name_mutation_is_rejected():
    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "oldName": "ignored"}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "oldName": "ignored"}}).expected_json
    assert nested.unknown_names == frozenset({"oldName"})
    object.__setattr__(nested, "unknown_names", frozenset({"newName"}))
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_whole_state_transplantation_is_rejected():
    target = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    donor = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("99.99"), "newName": "ignored"}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    for name, value in object.__getattribute__(donor, "__dict__").items():
        object.__setattr__(target, name, value)
    _assert_nested_fails_closed_on_all_surfaces(target, other)


def test_nested_json_identity_rebinding_is_defeated_across_every_surface():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    object.__setattr__(nested, "child_benefit_entitlement", Decimal("99.99"))

    genuine = module._json_identity
    module._json_identity = lambda v: (("int", 0), frozenset())
    try:
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            nested.child_benefit_entitlement
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            nested.unknown_names
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            repr(nested)
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            nested == other
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            other == nested
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            hash(nested)
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            copy.copy(nested)
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            copy.deepcopy(nested)
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            pickle.dumps(nested)
    finally:
        module._json_identity = genuine

    # Restoring the genuine helper must not expose a laundered 99.99 issuance.
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.child_benefit_entitlement
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        pickle.dumps(nested)


def test_nested_pickle_cannot_launder_mutated_semantics_into_new_issuance():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    object.__setattr__(nested, "child_benefit_entitlement", Decimal("99.99"))

    genuine = module._json_identity
    module._json_identity = lambda v: (("int", 0), frozenset())
    try:
        # __reduce__ re-validates through the closure-bound identity and rejects
        # the mutated semantics before any reconstruction callable is reached.
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            pickle.dumps(nested)
    finally:
        module._json_identity = genuine

    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        nested.child_benefit_entitlement


def test_reconstruction_validates_exact_issued_identity():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    issued_integrity = object.__getattribute__(nested, "_json_integrity")

    restored = module._restore_json(Decimal("12.30"), frozenset(), issued_integrity)
    assert restored.child_benefit_entitlement == Decimal("12.30")
    assert restored.unknown_names == frozenset()

    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        module._restore_json(Decimal("99.99"), frozenset(), issued_integrity)


@pytest.mark.parametrize("helper", [
    "_json_identity", "_json_state", "_exact", "_number", "_digest",
    "_amount", "_names", "_new_json", "_restore_json",
])
def test_nested_validation_and_reconstruction_are_immune_to_helper_rebinding(helper):
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    object.__setattr__(nested, "child_benefit_entitlement", Decimal("99.99"))

    genuine = getattr(module, helper)
    setattr(module, helper, lambda *a, **k: None)
    try:
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            nested.child_benefit_entitlement
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            pickle.dumps(nested)
    finally:
        setattr(module, helper, genuine)


def _nested_pair_mutated():
    nested = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}}).expected_json
    object.__setattr__(nested, "child_benefit_entitlement", Decimal("99.99"))
    return nested, other


def _fake_hashlib_returning_digest(digest_value):
    class _FakeSHA256:
        def __init__(self, data):
            self._data = data
        def hexdigest(self):
            return digest_value
    class _FakeHashlib:
        sha256 = _FakeSHA256
    return _FakeHashlib


def _fake_json_raising():
    class _FakeJson:
        @staticmethod
        def dumps(*a, **k):
            raise AssertionError("fake json.dumps invoked")
    return _FakeJson


def test_nested_digest_is_immune_to_rebound_hashlib_module():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested, other = _nested_pair_mutated()
    stored = object.__getattribute__(nested, "_json_integrity")
    genuine = module.hashlib
    module.hashlib = _fake_hashlib_returning_digest(stored)
    try:
        _assert_nested_fails_closed_on_all_surfaces(nested, other)
    finally:
        module.hashlib = genuine
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_digest_is_immune_to_rebound_json_module():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested, other = _nested_pair_mutated()
    genuine = module.json
    module.json = _fake_json_raising()
    try:
        _assert_nested_fails_closed_on_all_surfaces(nested, other)
    finally:
        module.json = genuine
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_digest_is_immune_to_rebound_hashlib_sha256_attribute():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested, other = _nested_pair_mutated()
    stored = object.__getattribute__(nested, "_json_integrity")
    genuine = module.hashlib.sha256
    module.hashlib.sha256 = _fake_hashlib_returning_digest(stored).sha256
    try:
        _assert_nested_fails_closed_on_all_surfaces(nested, other)
    finally:
        module.hashlib.sha256 = genuine
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_digest_is_immune_to_rebound_json_dumps_attribute():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested, other = _nested_pair_mutated()
    genuine = module.json.dumps
    def fake_dumps(*a, **k):
        raise AssertionError("fake json.dumps invoked")
    module.json.dumps = fake_dumps
    try:
        _assert_nested_fails_closed_on_all_surfaces(nested, other)
    finally:
        module.json.dumps = genuine
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def test_nested_stateful_digest_laundering_is_defeated():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    nested, other = _nested_pair_mutated()
    old_digest = object.__getattribute__(nested, "_json_integrity")
    genuine_sha256 = module.hashlib.sha256
    genuine_dumps = module.json.dumps
    canonical_99 = [module._number(Decimal("99.99")), []]
    new_digest = genuine_sha256(genuine_dumps(
        canonical_99, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()

    calls = {"n": 0}
    class _FakeSHA256:
        def __init__(self, data):
            self._data = data
        def hexdigest(self):
            i = calls["n"]
            calls["n"] += 1
            # "old" digest for validation, "new" digest for reconstruction.
            return old_digest if i < 2 else new_digest
    class _FakeHashlib:
        sha256 = _FakeSHA256

    genuine = module.hashlib
    module.hashlib = _FakeHashlib
    try:
        # A laundered 99.99 must never be read, reduced or reconstructed.
        _assert_nested_fails_closed_on_all_surfaces(nested, other)
    finally:
        module.hashlib = genuine

    # The genuine module still rejects; no laundered 99.99 issuance exists.
    _assert_nested_fails_closed_on_all_surfaces(nested, other)


def _outer_pair_mutated():
    obs = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}})
    other = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30")}})
    object.__setattr__(obs, "expected_status", 299)
    return obs, other


def _assert_outer_fails_closed_on_all_surfaces(obs, other):
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(obs)
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        obs.expected_status
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        obs.tax_year
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        obs == other
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        other == obs
    for operation in (
        lambda: hash(obs),
        lambda: repr(obs),
        lambda: copy.copy(obs),
        lambda: copy.deepcopy(obs),
        lambda: pickle.dumps(obs),
    ):
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            operation()


@pytest.mark.parametrize("helper", [
    "_digest", "_state", "_exact", "_integer", "_names",
    "_new_observation", "_restore_observation", "_request_binding",
    "_valid_binding", "_restore_request", "_json_state",
    "_json_canonical", "_json_identity",
])
def test_outer_response_immune_to_digest_and_state_helper_rebinding(helper):
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    genuine = getattr(module, helper)
    setattr(module, helper, lambda *a, **k: None)
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        setattr(module, helper, genuine)
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_digest_is_immune_to_rebound_hashlib_module():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    stored = object.__getattribute__(obs, "_observation_integrity")
    genuine = module.hashlib
    module.hashlib = _fake_hashlib_returning_digest(stored)
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module.hashlib = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_digest_is_immune_to_rebound_json_module():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    genuine = module.json
    module.json = _fake_json_raising()
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module.json = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_digest_is_immune_to_rebound_hashlib_sha256_attribute():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    stored = object.__getattribute__(obs, "_observation_integrity")
    genuine = module.hashlib.sha256
    module.hashlib.sha256 = _fake_hashlib_returning_digest(stored).sha256
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module.hashlib.sha256 = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_digest_is_immune_to_rebound_json_dumps_attribute():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    genuine = module.json.dumps
    def fake_dumps(*a, **k):
        raise AssertionError("fake json.dumps invoked")
    module.json.dumps = fake_dumps
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module.json.dumps = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_stateful_digest_laundering_is_defeated():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, other = _outer_pair_mutated()
    old_digest = object.__getattribute__(obs, "_observation_integrity")
    genuine_sha256 = module.hashlib.sha256
    genuine_dumps = module.json.dumps
    raw = object.__getattribute__(obs, "__dict__")
    b = module._request_binding(raw["request"])
    base = [list(b), list(b), b[1], b[3], True, 201, module.JSON_CONTENT_TYPE]
    tail = [True, module._json_canonical(raw["expected_json"]),
            sorted(raw["unknown_names"]), module.COMPLETENESS]
    new_digest = genuine_sha256(genuine_dumps(
        base + [299] + tail, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()

    calls = {"n": 0}
    class _FakeSHA256:
        def __init__(self, data):
            self._data = data
        def hexdigest(self):
            i = calls["n"]
            calls["n"] += 1
            # "old" digest for validation, "new" digest for reconstruction.
            return old_digest if i < 2 else new_digest
    class _FakeHashlib:
        sha256 = _FakeSHA256

    genuine = module.hashlib
    module.hashlib = _FakeHashlib
    try:
        # A laundered 299 status must never be read, reduced or reconstructed.
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module.hashlib = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_outer_validate_uses_captured_digest_despite_hashlib_rebinding():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs, _ = _outer_pair_mutated()
    genuine = module.hashlib
    module.hashlib = _fake_hashlib_returning_digest(
        object.__getattribute__(obs, "_observation_integrity"))
    try:
        with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
            validate_child_benefit_create_response_observation(obs)
    finally:
        module.hashlib = genuine
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        validate_child_benefit_create_response_observation(obs)


def test_outer_reconstruction_carries_and_verifies_issued_identity():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    obs = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("12.30"), "inner": object()},
        "outer": object()})
    restore, args = obs.__reduce__()
    assert len(args) == 6
    assert args[5] == object.__getattribute__(obs, "_observation_integrity")

    restored = restore(*args)
    assert validate_child_benefit_create_response_observation(restored) is restored
    assert pickle.loads(pickle.dumps(restored)) == restored

    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        restore(args[0], 299, *args[2:])

    altered_expected = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("99.99")}}).expected_json
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        restore(args[0], args[1], altered_expected, *args[3:])

    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        restore(args[0], args[1], args[2], not args[3], *args[4:])

    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        restore(args[0], args[1], args[2], args[3], frozenset({"other"}), args[5])

    other_binding = module._request_binding(
        request(utr="9999999999", tax_year="2024-25", scenario="HAPPY_PATH_2"))
    with pytest.raises(HMRCPayeTestSupportChildBenefitContractError):
        restore(other_binding, args[1], *args[2:])


def test_request_raw_binding_mutation_is_rejected_despite_valid_binding_rebinding():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    req_a = request()
    req_b = request(utr="9999999999", tax_year="2024-25", scenario="HAPPY_PATH_2")
    obs = observe({"expectedStatus": 200}, req=req_a)
    other = observe({"expectedStatus": 200})
    original_binding = module._request_binding(req_a)
    object.__setattr__(
        req_a, "_ChildBenefitCreateRequestIntent__binding",
        module._request_binding(req_b))

    genuine = module._valid_binding
    module._valid_binding = lambda v: original_binding
    try:
        _assert_outer_fails_closed_on_all_surfaces(obs, other)
    finally:
        module._valid_binding = genuine
    _assert_outer_fails_closed_on_all_surfaces(obs, other)


def test_pickle_preserves_decimal_sign_and_scale_and_contains_no_utr_derivative():
    utr = "3141592653"
    result = observe({"expectedStatus": 200, "expectedJson": {
        "childBenefitEntitlement": Decimal("-0.00")}}, req=request(utr=utr))
    encoded = pickle.dumps(result)
    restored = pickle.loads(encoded)
    assert restored == result
    assert restored.expected_json.child_benefit_entitlement.as_tuple() == Decimal("-0.00").as_tuple()
    assert utr.encode() not in encoded
    assert hashlib.sha256(utr.encode()).hexdigest().encode() not in encoded


def test_request_replace_reenters_utr_validation_boundary():
    req = request()
    with pytest.raises(TypeError):
        replace(req)


def test_module_has_no_network_credentials_persistence_activation_or_product_imports():
    import reserved.providers.hmrc_paye_test_support_child_benefit_contract as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports <= {"__future__", "re", "unicodedata", "dataclasses", "decimal",
                       "hashlib", "json", "secrets", "weakref"}
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import requests", "import httpx", "import urllib", "import socket",
        "ProviderRequest", "reserved.engines", "HicbcEngine",
    ):
        assert forbidden.lower() not in source.lower()
