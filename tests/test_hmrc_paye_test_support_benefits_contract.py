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
    assert vars(omitted) == {"tax_year": YEAR, "scenario": None, "scenario_present": False}
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


def test_response_is_request_bound_and_replace_requires_fresh_request():
    request = intent(scenario="HAPPY_PATH_2")
    result = observe(request=request)
    assert (result.tax_year, result.scenario, result.scenario_present) == (YEAR, "HAPPY_PATH_2", True)
    assert "request" not in vars(result)
    with pytest.raises((TypeError, ERR)):
        BenefitsSummaryCreated(employments=result.employments)
    with pytest.raises((TypeError, ERR)):
        replace(result, employments=result.employments)
    fresh = build_benefits_summary_request(utr="0000000000", tax_year="2024-25", scenario="HAPPY_PATH_1")
    changed = replace(result, request=fresh, employments=result.employments)
    assert (changed.tax_year, changed.scenario) == ("2024-25", "HAPPY_PATH_1")
    with pytest.raises(TypeError):
        replace(result, request=fresh, tax_year="2020-21")


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
