import copy
import pickle
from dataclasses import replace
from decimal import Decimal

import pytest

import reserved.providers.hmrc_paye_test_support_benefits_contract as contract
from reserved.providers.hmrc_paye_test_support_benefits_contract import (
    BenefitsEmployment,
    BenefitsSummaryCreated,
    BenefitsSummaryRequestIntent,
    HMRCPAYETestSupportBenefitsContractError,
    build_benefits_summary_request,
    observe_benefits_summary_response,
)

UTR = "2234567890"
YEAR = "2025-26"
ERR = HMRCPAYETestSupportBenefitsContractError


def intent(**kwargs):
    return build_benefits_summary_request(utr=UTR, tax_year=YEAR, **kwargs)


def payload(**extra):
    item = {"employerPayeReference": "123/AB456"}
    item.update(extra)
    return {"employments": [item]}


def observe(body=None, request=None, **kwargs):
    return observe_benefits_summary_response(
        request or intent(), status_code=kwargs.get("status_code", 201),
        content_type=kwargs.get("content_type", "application/json"),
        payload=payload() if body is None else body,
    )


def test_exact_identity_constants_and_sandbox_limitation():
    assert contract.HTTP_METHOD == "POST"
    assert contract.PATH_TEMPLATE == "/individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}"
    assert contract.OPERATION_ID == "createBenefitsSummaryTestData"
    assert contract.API_VERSION == "2.1"
    assert contract.SANDBOX_ONLY is True
    assert contract.COMPLETENESS == "UNVERIFIED"
    source = open(contract.__file__, encoding="utf-8").read()
    for forbidden in ("requests", "urllib", "httpx", "ProviderRequest", "PayeEvidence", "hicbc"):
        assert f"import {forbidden}" not in source


@pytest.mark.parametrize("bad", [None, 123, "", "123456789", "12345678901", "１２３４５６７８９０", "12345A7890"])
def test_utr_exact_ten_ascii_digits(bad):
    with pytest.raises(ERR):
        build_benefits_summary_request(utr=bad, tax_year=YEAR)


@pytest.mark.parametrize("bad", [None, 202526, "25-26", "2025/26", "２０２５-２６", "2025-2"])
def test_tax_year_shape(bad):
    with pytest.raises(ERR):
        build_benefits_summary_request(utr=UTR, tax_year=bad)


def test_request_discards_utr_and_tracks_scenario_omission_and_values():
    omitted = intent()
    assert set(vars(omitted)) == {"_request_identity"}
    assert (omitted.tax_year, omitted.scenario, omitted.scenario_present) == (YEAR, None, False)
    assert omitted.request_identity == (
        "HMRC_PAYE_TEST_SUPPORT_BENEFITS_REQUEST_V1", "POST",
        "https://test-api.service.hmrc.gov.uk",
        "/individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}",
        "application/vnd.hmrc.2.1+json", "application/json", "application/json",
        "2.1", YEAR, False, None,
    )
    assert UTR not in repr(omitted) and UTR not in pickle.dumps(omitted).decode("latin1")
    for value in ("HAPPY_PATH_1", "HAPPY_PATH_2"):
        request = intent(scenario=value)
        assert (request.scenario, request.scenario_present) == (value, True)
    with pytest.raises(ERR):
        intent(scenario=None)


class Hostile:
    def __getattribute__(self, name):
        raise AssertionError("hostile value was touched")
    def __repr__(self):
        raise AssertionError("hostile value was represented")
    def __deepcopy__(self, memo):
        raise AssertionError("hostile value was copied")


def test_non_201_rejects_before_content_type_or_body_traversal():
    with pytest.raises(ERR):
        observe_benefits_summary_response(intent(), status_code=404,
                                          content_type=Hostile(), payload=Hostile())
    for bad in (True, 201.0, "201", Decimal(201)):
        with pytest.raises(ERR):
            observe_benefits_summary_response(intent(), status_code=bad,
                                              content_type=Hostile(), payload=Hostile())


def test_exact_201_and_content_type():
    assert observe().status_code == 201
    for status in (True, 201.0, "201"):
        with pytest.raises(ERR):
            observe(status_code=status)
    for media in (None, "Application/JSON", "application/json; charset=utf-8"):
        with pytest.raises(ERR):
            observe(content_type=media)
    with pytest.raises(ERR):
        observe_benefits_summary_response(intent(), status_code=201,
                                          content_type="text/plain", payload=Hostile())


def test_response_is_request_bound_and_replace_cannot_rebind():
    request = intent(scenario="HAPPY_PATH_2")
    result = observe(request=request)
    assert (result.tax_year, result.scenario, result.scenario_present) == (YEAR, "HAPPY_PATH_2", True)
    assert "request" not in vars(result) and result.request_identity == request.request_identity
    assert result.request_binding == (
        "HMRC_PAYE_TEST_SUPPORT_BENEFITS_REQUEST_V1", request.request_identity)
    with pytest.raises((TypeError, ERR)):
        BenefitsSummaryCreated(employments=result.employments)
    with pytest.raises((TypeError, ERR)):
        replace(result, employments=result.employments)
    fresh = build_benefits_summary_request(utr="0000000000", tax_year="2024-25", scenario="HAPPY_PATH_1")
    with pytest.raises((TypeError, ERR)):
        replace(result, request=fresh, employments=result.employments)
    with pytest.raises((TypeError, ERR)):
        replace(result)


@pytest.mark.parametrize("scenario", [contract._OMITTED, "HAPPY_PATH_1", "HAPPY_PATH_2"])
def test_exact_request_to_observation_binding_survives_copy_and_pickle(scenario):
    request = intent() if scenario is contract._OMITTED else intent(scenario=scenario)
    result = observe(request=request)
    expected = (None, False) if scenario is contract._OMITTED else (scenario, True)
    assert (result.scenario, result.scenario_present) == expected
    assert result.request_identity == request.request_identity
    for request_clone in (copy.copy(request), copy.deepcopy(request),
                          pickle.loads(pickle.dumps(request))):
        assert request_clone == request and hash(request_clone) == hash(request)
        assert request_clone.request_identity == request.request_identity
    for result_clone in (copy.copy(result), copy.deepcopy(result),
                         pickle.loads(pickle.dumps(result))):
        assert result_clone == result and hash(result_clone) == hash(result)
        assert result_clone.request_binding == result.request_binding


def test_year_scenario_descriptor_and_coordinated_substitution_fail_closed():
    result = observe(request=intent(scenario="HAPPY_PATH_1"))
    original_identity = result.request_identity
    variants = [
        original_identity[:8] + ("2024-25",) + original_identity[9:],
        original_identity[:9] + (True, "HAPPY_PATH_2"),
        original_identity[:1] + ("GET",) + original_identity[2:],
        original_identity[:9] + (False, None),
    ]
    for changed_identity in variants:
        altered = object.__new__(BenefitsSummaryCreated)
        altered.__dict__.update(vars(result))
        object.__setattr__(altered, "_request_identity", changed_identity)
        with pytest.raises(ERR):
            hash(altered)
    other = observe(request=intent(scenario="HAPPY_PATH_2"),
                    body=payload(otherBenefits=99))
    altered = object.__new__(BenefitsSummaryCreated)
    altered.__dict__.update(vars(result))
    for name in ("_request_identity", "_request_binding", "_integrity_digest"):
        altered.__dict__[name] = vars(other)[name]
    with pytest.raises(ERR):
        pickle.dumps(altered)


def test_reconstruction_and_direct_construction_cannot_relabel_payload_with_transplanted_digest():
    first = observe(request=intent(scenario="HAPPY_PATH_1"),
                    body=payload(otherBenefits=1))
    second = observe(request=intent(scenario="HAPPY_PATH_2"),
                     body=payload(otherBenefits=2))
    with pytest.raises(ERR):
        contract._rebuild_summary(
            second.request_identity, second.request_binding, first.employments,
            second.status_code, second.content_type, second.unknown_names,
            second.completeness, vars(second)["_integrity_digest"])
    rebuilt_request = contract._rebuild_intent(second.request_identity)
    with pytest.raises(ERR):
        BenefitsSummaryCreated(
            rebuilt_request, first.employments,
            _integrity_digest=vars(second)["_integrity_digest"])
    assert not hasattr(contract, "_CONSTRUCTION_KEY")
    assert not hasattr(contract, "_observation_integrity")


def test_private_construction_subclasses_missing_extra_and_mutated_state_rejected():
    with pytest.raises(ERR):
        BenefitsSummaryRequestIntent(("x",))
    with pytest.raises(ERR):
        BenefitsSummaryCreated(intent(), (BenefitsEmployment("x"),))
    class RequestSubclass(BenefitsSummaryRequestIntent):
        pass
    class ObservationSubclass(BenefitsSummaryCreated):
        pass
    request_subclass = object.__new__(RequestSubclass)
    request_subclass.__dict__.update(vars(intent()))
    with pytest.raises(ERR):
        repr(request_subclass)
    observation_subclass = object.__new__(ObservationSubclass)
    observation_subclass.__dict__.update(vars(observe()))
    with pytest.raises(ERR):
        repr(observation_subclass)
    for state_change in ("missing", "extra"):
        malformed = object.__new__(BenefitsSummaryRequestIntent)
        malformed.__dict__.update(vars(intent()))
        if state_change == "missing":
            del malformed.__dict__["_request_identity"]
        else:
            malformed.__dict__["extra"] = 1
        with pytest.raises(ERR):
            copy.copy(malformed)
    for state_change in ("missing", "extra"):
        malformed = object.__new__(BenefitsSummaryCreated)
        malformed.__dict__.update(vars(observe()))
        if state_change == "missing":
            del malformed.__dict__["_request_binding"]
        else:
            malformed.__dict__["extra"] = 1
        with pytest.raises(ERR):
            hash(malformed)


class HookBomb:
    def __eq__(self, other):
        raise AssertionError("equality hook invoked")
    def __hash__(self):
        raise AssertionError("hash hook invoked")
    def __repr__(self):
        raise AssertionError("repr hook invoked")
    def __str__(self):
        raise AssertionError("string hook invoked")
    def __bool__(self):
        raise AssertionError("bool hook invoked")
    def __iter__(self):
        raise AssertionError("iteration hook invoked")


class ArmedCollision:
    def __init__(self, collision):
        self.collision = collision
        self.armed = False
        self.calls = []

    def __hash__(self):
        if self.armed:
            self.calls.append("hash")
            raise AssertionError("armed hash hook invoked")
        return hash(self.collision)

    def __eq__(self, other):
        if self.armed:
            self.calls.append("eq")
            raise AssertionError("armed equality hook invoked")
        return False


def _state_with_armed_key(value):
    original = vars(value)
    replaced = next(iter(original))
    bomb = ArmedCollision(replaced)
    state = {bomb: original[replaced]}
    state.update((name, item) for name, item in original.items() if name != replaced)
    bomb.calls.clear()
    bomb.armed = True
    malformed = object.__new__(type(value))
    object.__setattr__(malformed, "__dict__", state)
    return malformed, bomb


def test_malformed_identity_rejected_before_custom_hooks():
    malformed = object.__new__(BenefitsSummaryRequestIntent)
    good = intent()
    malformed.__dict__.update(vars(good))
    identity = list(good.request_identity)
    identity[1] = HookBomb()
    malformed.__dict__["_request_identity"] = tuple(identity)
    with pytest.raises(ERR):
        repr(malformed)


def test_employment_exact_layout_precedes_shadowed_dataclass_fields_hook():
    malformed = object.__new__(BenefitsEmployment)
    malformed.__dict__.update(vars(BenefitsEmployment("x")))
    bomb = HookBomb()
    malformed.__dict__["__dataclass_fields__"] = bomb
    with pytest.raises(ERR):
        BenefitsEmployment._validated_values(malformed)


class InvocationBomb:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(("call", args, kwargs))
        raise AssertionError("injected callable was invoked")

    def __rsub__(self, other):
        self.calls.append(("rsub", other))
        raise AssertionError("injected subtraction hook was invoked")


def _shadowed_clone(value, name, bomb):
    malformed = object.__new__(type(value))
    malformed.__dict__.update(vars(value))
    object.__setattr__(malformed, name, bomb)
    return malformed


def _hostile_public_operations(good, malformed, properties):
    return (
        lambda: repr(malformed),
        lambda: malformed == good,
        lambda: good == malformed,
        lambda: hash(malformed),
        lambda: copy.copy(malformed),
        lambda: copy.deepcopy(malformed),
        lambda: pickle.dumps(malformed),
        *(lambda name=name: getattr(malformed, name) for name in properties),
    )


@pytest.mark.parametrize("surface", ["request", "employment", "observation"])
def test_armed_custom_state_key_rejected_without_hash_or_equality_hooks(surface):
    request = intent(scenario="HAPPY_PATH_1")
    values = {
        "request": (request, ("request_identity", "tax_year", "scenario_present", "scenario")),
        "employment": (BenefitsEmployment("123/AB456"),
                       ("employer_paye_reference", "present_fields", "absent_fields")),
        "observation": (observe(request=request),
                        ("request_identity", "request_binding", "tax_year", "scenario_present",
                         "scenario", "employments", "status_code", "content_type",
                         "unknown_names", "completeness")),
    }
    good, properties = values[surface]
    malformed, bomb = _state_with_armed_key(good)
    for operation in _hostile_public_operations(good, malformed, properties):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


@pytest.mark.parametrize("field_name", ["present_fields", "unknown_names"])
def test_armed_frozenset_member_rejected_without_hash_or_equality_hooks(field_name):
    request = intent(scenario="HAPPY_PATH_2")
    if field_name == "present_fields":
        good = BenefitsEmployment("123/AB456")
        collision = "otherBenefits"
        properties = ("employer_paye_reference", "present_fields", "absent_fields")
    else:
        good = observe(request=request)
        collision = "employments"
        properties = ("request_identity", "request_binding", "tax_year", "scenario_present",
                      "scenario", "employments", "status_code", "content_type",
                      "unknown_names", "completeness")
    bomb = ArmedCollision(collision)
    hostile_members = frozenset((bomb,))
    bomb.calls.clear()
    bomb.armed = True
    malformed = object.__new__(type(good))
    malformed.__dict__.update(vars(good))
    object.__setattr__(malformed, field_name, hostile_members)
    for operation in _hostile_public_operations(good, malformed, properties):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


@pytest.mark.parametrize("surface", ["request_identity", "observation_employments"])
def test_armed_tuple_member_rejected_without_hash_or_equality_hooks(surface):
    request = intent(scenario="HAPPY_PATH_1")
    if surface == "request_identity":
        good = request
        identity = list(request.request_identity)
        bomb = ArmedCollision(identity[1])
        identity[1] = bomb
        field_name, hostile_value = "_request_identity", tuple(identity)
        properties = ("request_identity", "tax_year", "scenario_present", "scenario")
    else:
        good = observe(request=request)
        bomb = ArmedCollision(good.employments[0])
        field_name, hostile_value = "employments", (bomb,)
        properties = ("request_identity", "request_binding", "tax_year", "scenario_present",
                      "scenario", "employments", "status_code", "content_type",
                      "unknown_names", "completeness")
    bomb.calls.clear()
    bomb.armed = True
    malformed = object.__new__(type(good))
    malformed.__dict__.update(vars(good))
    object.__setattr__(malformed, field_name, hostile_value)
    for operation in _hostile_public_operations(good, malformed, properties):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


@pytest.mark.parametrize("helper_name", ["_identity"])
def test_request_helper_shadowing_rejects_before_any_injected_hook(helper_name):
    good = intent(scenario="HAPPY_PATH_1")
    bomb = InvocationBomb()
    malformed = _shadowed_clone(good, helper_name, bomb)
    for operation in _hostile_public_operations(
            good, malformed,
            ("request_identity", "tax_year", "scenario_present", "scenario")):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


@pytest.mark.parametrize("helper_name", ["_validated_values", "_values"])
def test_employment_helper_shadowing_rejects_before_any_injected_hook(helper_name):
    good = BenefitsEmployment("123/AB456", other_benefits=1,
                              present_fields=frozenset({"otherBenefits"}))
    bomb = InvocationBomb()
    malformed = _shadowed_clone(good, helper_name, bomb)
    for operation in _hostile_public_operations(
            good, malformed,
            ("employer_paye_reference", "present_fields", "absent_fields")):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


def test_employment_absent_fields_rejects_before_injected_rsub_hook():
    good = BenefitsEmployment("123/AB456")
    bomb = InvocationBomb()
    malformed = object.__new__(BenefitsEmployment)
    malformed.__dict__.update(vars(good))
    object.__setattr__(malformed, "present_fields", bomb)
    for property_name in ("present_fields", "absent_fields"):
        with pytest.raises(ERR):
            getattr(malformed, property_name)
        assert bomb.calls == []


@pytest.mark.parametrize("helper_name", ["_validated_state"])
def test_observation_helper_shadowing_rejects_before_any_injected_hook(helper_name):
    good = observe(request=intent(scenario="HAPPY_PATH_2"))
    bomb = InvocationBomb()
    malformed = _shadowed_clone(good, helper_name, bomb)
    for operation in _hostile_public_operations(
            good, malformed,
            ("request_identity", "request_binding", "tax_year", "scenario_present",
             "scenario", "employments", "status_code", "content_type",
             "unknown_names", "completeness")):
        with pytest.raises(ERR):
            operation()
        assert bomb.calls == []


@pytest.mark.parametrize("state_change", ["missing", "extra", "malformed"])
def test_malformed_exact_request_fails_before_status_content_or_payload_access(state_change):
    malformed = object.__new__(BenefitsSummaryRequestIntent)
    malformed.__dict__.update(vars(intent()))
    if state_change == "missing":
        del malformed.__dict__["_request_identity"]
    elif state_change == "extra":
        malformed.__dict__["extra"] = HookBomb()
    else:
        malformed.__dict__["_request_identity"] = (HookBomb(),)
    messages = []
    for status in (201, 404):
        with pytest.raises(ERR) as captured:
            observe_benefits_summary_response(
                malformed, status_code=status, content_type=Hostile(), payload=Hostile())
        messages.append(str(captured.value))
    assert messages[0] == messages[1]


def test_raw_utr_absent_from_all_retained_and_reconstructed_surfaces():
    request = intent(scenario="HAPPY_PATH_2")
    result = observe(request=request)
    surfaces = (vars(request), request.request_identity, repr(request), vars(result),
                result.request_identity, result.request_binding, repr(result))
    assert all(UTR not in repr(surface) for surface in surfaces)
    assert UTR.encode() not in pickle.dumps(request)
    assert UTR.encode() not in pickle.dumps(result)
    other_utr_result = observe_benefits_summary_response(
        build_benefits_summary_request(utr="9876543210", tax_year=YEAR,
                                       scenario="HAPPY_PATH_2"),
        status_code=201, content_type="application/json", payload=payload())
    assert vars(other_utr_result)["_integrity_digest"] == vars(result)["_integrity_digest"]
    with pytest.raises(ERR) as captured:
        build_benefits_summary_request(utr=UTR[:-1], tax_year=YEAR)
    assert UTR not in str(captured.value)


def test_all_retained_payload_fields_and_cross_object_digests_are_integrity_bound():
    original = observe(payload(**{name: index for index, name in enumerate(NUMBERS, 1)}))
    other = observe(payload(otherBenefits=Decimal("45.60")))
    employment_replacements = {
        "employer_paye_reference": "changed",
        **{attribute: 100 + index for index, attribute in enumerate(NUMBERS.values())},
        "present_fields": frozenset(),
        "unknown_names": frozenset({"future"}),
    }
    for name, value in employment_replacements.items():
        employment = object.__new__(BenefitsEmployment)
        employment.__dict__.update(vars(original.employments[0]))
        employment.__dict__[name] = value
        altered = object.__new__(BenefitsSummaryCreated)
        altered.__dict__.update(vars(original))
        altered.__dict__["employments"] = (employment,)
        with pytest.raises(ERR):
            hash(altered)
    for name, value in {
        "employments": other.employments,
        "unknown_names": frozenset({"futureTop"}),
        "content_type": "text/plain",
        "status_code": 200,
        "completeness": "VERIFIED",
    }.items():
        altered = object.__new__(BenefitsSummaryCreated)
        altered.__dict__.update(vars(original))
        altered.__dict__[name] = value
        with pytest.raises(ERR):
            hash(altered)
    transplanted = object.__new__(BenefitsSummaryCreated)
    transplanted.__dict__.update(vars(original))
    transplanted.__dict__["_integrity_digest"] = vars(other)["_integrity_digest"]
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(ERR):
            operation(transplanted)


def test_one_or_more_employments_and_order_is_only_source_shape():
    with pytest.raises(ERR):
        observe({"employments": []})
    one = observe()
    many = observe({"employments": [{"employerPayeReference": "B"}, {"employerPayeReference": "A"}]})
    assert len(one.employments) == 1
    assert [x.employer_paye_reference for x in many.employments] == ["B", "A"]
    assert not hasattr(many.employments[0], "id")


@pytest.mark.parametrize("body", [{}, {"employments": [{}]}, {"employments": None}, []])
def test_required_members_and_container_shapes(body):
    with pytest.raises(ERR):
        observe(body)


NUMBERS = {
    "companyCarsAndVansBenefit": "company_cars_and_vans_benefit",
    "fuelForCompanyCarsAndVansBenefit": "fuel_for_company_cars_and_vans_benefit",
    "privateMedicalDentalInsurance": "private_medical_dental_insurance",
    "vouchersCreditCardsExcessMileageAllowance": "vouchers_credit_cards_excess_mileage_allowance",
    "goodsEtcProvidedByEmployer": "goods_etc_provided_by_employer",
    "accommodationProvidedByEmployer": "accommodation_provided_by_employer",
    "otherBenefits": "other_benefits",
    "expensesPaymentsReceived": "expenses_payments_received",
}


@pytest.mark.parametrize("wire,attribute", NUMBERS.items())
def test_each_optional_number_distinguishes_omission_zero_and_rejects_null(wire, attribute):
    absent = observe().employments[0]
    assert getattr(absent, attribute) is None and wire in absent.absent_fields
    zero = observe(payload(**{wire: 0})).employments[0]
    assert getattr(zero, attribute) == 0 and wire in zero.present_fields
    with pytest.raises(ERR):
        observe(payload(**{wire: None}))


def test_exact_int_decimal_preservation_including_negative_zero():
    result = observe(payload(companyCarsAndVansBenefit=-2,
                             otherBenefits=Decimal("-0.00"))).employments[0]
    assert type(result.company_cars_and_vans_benefit) is int
    assert result.other_benefits is not None
    assert result.other_benefits.as_tuple().sign == 1
    assert result.other_benefits.as_tuple().exponent == -2


class IntSubclass(int):
    pass
class DecimalSubclass(Decimal):
    pass
class StrSubclass(str):
    pass


@pytest.mark.parametrize("bad", [True, 1.0, "1", IntSubclass(1), DecimalSubclass("1"),
                                  Decimal("NaN"), Decimal("Infinity"), 10**19,
                                  Decimal("1.0000000000000")])
def test_numeric_coercion_nonfinite_subclasses_and_excess_rejected(bad):
    with pytest.raises(ERR):
        observe(payload(otherBenefits=bad))


def test_unknown_names_only_and_hostile_values_absent_from_state_copy_pickle_repr():
    hostile = Hostile()
    result = observe({"futureTop": hostile, "employments": [
        {"employerPayeReference": "", "futureEmployment": hostile}
    ]})
    assert result.unknown_names == {"futureTop"}
    assert result.employments[0].unknown_names == {"futureEmployment"}
    assert "Hostile" not in repr(result)
    assert copy.copy(result) is result and copy.deepcopy(result) is result
    clone = pickle.loads(pickle.dumps(result))
    assert clone == result
    assert "futureTop" in clone.unknown_names


@pytest.mark.parametrize("level,name", [("top", "employments"),
                                         ("employment", "employerPayeReference"),
                                         ("employment", "otherBenefits")])
def test_documented_name_cannot_be_injected_as_unknown(level, name):
    if level == "top":
        with pytest.raises(ERR):
            BenefitsSummaryCreated(intent(), (BenefitsEmployment("x"),), unknown_names=frozenset({name}))
    else:
        with pytest.raises(ERR):
            BenefitsEmployment("x", unknown_names=frozenset({name}))


@pytest.mark.parametrize("bad", [StrSubclass("future"), "", "bad\x00name", "x" * 257])
def test_every_member_name_is_exact_safe_nonempty_and_bounded(bad):
    with pytest.raises(ERR):
        observe({bad: Hostile(), "employments": [{"employerPayeReference": "x"}]})
    with pytest.raises(ERR):
        observe({"employments": [{bad: Hostile(), "employerPayeReference": "x"}]})


@pytest.mark.parametrize("bad", [StrSubclass("x"), None, "bad\u200bref", "x" * 4097])
def test_employer_reference_exact_safe_and_bounded_but_empty_and_spaces_allowed(bad):
    with pytest.raises(ERR):
        observe(payload(employerPayeReference=bad))
    assert observe(payload(employerPayeReference="")).employments[0].employer_paye_reference == ""
    assert observe(payload(employerPayeReference="   ")).employments[0].employer_paye_reference == "   "


def test_immutable_replace_copy_deepcopy_pickle_constructor_coherence():
    result = observe(payload(otherBenefits=Decimal("12.30")))
    employment = result.employments[0]
    with pytest.raises((AttributeError, TypeError)):
        result.completeness = "VERIFIED"
    for candidate in (copy.copy(result), copy.deepcopy(result), pickle.loads(pickle.dumps(result))):
        assert candidate == result and candidate.completeness == "UNVERIFIED"
    with pytest.raises(ERR):
        replace(employment, other_benefits=None)
    with pytest.raises(ERR):
        BenefitsSummaryCreated(intent(), result.employments, completeness="VERIFIED")


def test_no_transport_credentials_persistence_activation_or_product_state():
    result = observe()
    retained = set(vars(result)) | set(vars(result.employments[0]))
    forbidden = {"utr", "url", "path", "headers", "body", "payload", "token", "credential",
                 "transport", "request", "tax", "hicbc", "total", "identity", "chronology"}
    assert retained.isdisjoint(forbidden)
    assert result.completeness == "UNVERIFIED"
