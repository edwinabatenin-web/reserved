import copy
import pickle
from dataclasses import replace
from decimal import Decimal

import pytest

from reserved.providers.hmrc_paye_test_support_tax_contract import (
    HMRCPAYETestSupportTaxContractError, PensionsBenefits, Refunds,
    TaxEmployment, TaxSummaryCreated, TaxTestSupportRequest,
    parse_tax_summary_created, parse_tax_test_support_request,
)


def body(**changes):
    value = {"employments": [], "pensionsAnnuitiesAndOtherStateBenefits": {}, "refunds": {}}
    value.update(changes)
    return value


def parse(value=None, **kw):
    return parse_tax_summary_created(body() if value is None else value, status_code=201, **kw)


def test_scenarios_and_omission_default_are_exact():
    assert parse().scenario == "HAPPY_PATH_1"
    assert parse(scenario="HAPPY_PATH_1").scenario == "HAPPY_PATH_1"
    assert parse(scenario="HAPPY_PATH_2").scenario == "HAPPY_PATH_2"
    assert parse_tax_test_support_request({}).scenario == "HAPPY_PATH_1"
    assert parse_tax_test_support_request({"scenario": "HAPPY_PATH_2"}).scenario == "HAPPY_PATH_2"


def test_explicit_none_scenario_rejected_at_public_boundaries():
    with pytest.raises(HMRCPAYETestSupportTaxContractError): TaxTestSupportRequest(None)
    with pytest.raises(HMRCPAYETestSupportTaxContractError): parse_tax_test_support_request({"scenario": None})
    with pytest.raises(HMRCPAYETestSupportTaxContractError): parse(scenario=None)
    with pytest.raises(HMRCPAYETestSupportTaxContractError): TaxSummaryCreated((), PensionsBenefits(), Refunds(), scenario=None)


@pytest.mark.parametrize("bad", [True, 201.0, "201", Decimal(201), 200, None])
def test_status_is_exact_integer_201(bad):
    with pytest.raises(HMRCPAYETestSupportTaxContractError):
        parse_tax_summary_created(body(), status_code=bad)


@pytest.mark.parametrize("items", [[], [{"employerPayeReference": "", "taxTakenOffPay": 0}],
    [{"employerPayeReference": "A", "taxTakenOffPay": 1}, {"employerPayeReference": "B", "taxTakenOffPay": 2}]])
def test_zero_one_and_multiple_employments_preserve_array_order_without_semantics(items):
    assert len(parse(body(employments=items)).employments) == len(items)


@pytest.mark.parametrize("value", [{}, {"employments": [], "refunds": {}},
    {"employments": [], "pensionsAnnuitiesAndOtherStateBenefits": {}}])
def test_required_top_level_objects(value):
    with pytest.raises(HMRCPAYETestSupportTaxContractError): parse(value)


def test_required_employment_members():
    for item in ({"taxTakenOffPay": 1}, {"employerPayeReference": "A"}):
        with pytest.raises(HMRCPAYETestSupportTaxContractError): parse(body(employments=[item]))


def test_optional_omission_is_distinct_from_exact_zero_and_null():
    omitted = parse()
    assert omitted.pensions_benefits.present_fields == frozenset()
    assert omitted.pensions_benefits.absent_fields == {"otherPensionsAndRetirementAnnuities", "incapacityBenefit"}
    zero = parse(body(pensionsAnnuitiesAndOtherStateBenefits={"incapacityBenefit": 0},
                      refunds={"taxRefundedOrSetOff": Decimal("0.00")}))
    assert zero.pensions_benefits.incapacity_benefit == 0
    assert zero.refunds.tax_refunded_or_set_off == Decimal("0.00")
    for container, name in (("pensionsAnnuitiesAndOtherStateBenefits", "incapacityBenefit"),
                            ("refunds", "taxRefundedOrSetOff")):
        payload = body(); payload[container] = {name: None}
        with pytest.raises(HMRCPAYETestSupportTaxContractError): parse(payload)


def test_exact_decimal_preserved():
    result = parse(body(employments=[{"employerPayeReference": "A", "taxTakenOffPay": Decimal("12.3400")}]))
    assert result.employments[0].tax_taken_off_pay.as_tuple() == Decimal("12.3400").as_tuple()


@pytest.mark.parametrize("bad", [True, False, 1.2, "1", None, Decimal("NaN"), Decimal("Infinity"),
                                  Decimal("0.1234567890123"), 10**18 + 1])
def test_invalid_lossy_nonfinite_or_excessive_numbers_rejected(bad):
    with pytest.raises(HMRCPAYETestSupportTaxContractError):
        parse(body(employments=[{"employerPayeReference": "A", "taxTakenOffPay": bad}]))


class Hostile:
    def __getattribute__(self, name): raise AssertionError("traversed")
    def __repr__(self): raise AssertionError("represented")
    def __copy__(self): raise AssertionError("copied")
    def __deepcopy__(self, memo): raise AssertionError("deep-copied")


def test_open_schema_captures_names_only_at_every_layer_without_touching_values():
    result = parse({"employments": [{"employerPayeReference": "A", "taxTakenOffPay": 1, "employmentExtra": Hostile()}],
        "pensionsAnnuitiesAndOtherStateBenefits": {"pensionExtra": Hostile()},
        "refunds": {"refundExtra": Hostile()}, "topExtra": Hostile()})
    assert result.unknown_names == {"topExtra"}
    assert result.employments[0].unknown_names == {"employmentExtra"}
    assert result.pensions_benefits.unknown_names == {"pensionExtra"}
    assert result.refunds.unknown_names == {"refundExtra"}
    assert "Hostile" not in repr(result)


@pytest.mark.parametrize("factory", [
    lambda: TaxEmployment("A", 1, frozenset({"taxTakenOffPay"})),
    lambda: PensionsBenefits(unknown_names=frozenset({"incapacityBenefit"})),
    lambda: Refunds(unknown_names=frozenset({"taxRefundedOrSetOff"})),
    lambda: TaxSummaryCreated((), PensionsBenefits(), Refunds(), unknown_names=frozenset({"refunds"})),
])
def test_documented_name_injection_into_unknown_names_rejected_everywhere(factory):
    with pytest.raises(HMRCPAYETestSupportTaxContractError): factory()


@pytest.mark.parametrize("bad", ["bad\x00", "bad\u200b", "x" * 257])
def test_unsafe_or_overlong_unknown_names_rejected(bad):
    payload = body(); payload[bad] = Hostile()
    with pytest.raises(HMRCPAYETestSupportTaxContractError): parse(payload)


@pytest.mark.parametrize("bad", ["bad\n", "bad\u200e", "x" * 4097])
def test_unsafe_or_overlong_employer_reference_rejected_but_spaces_and_empty_allowed(bad):
    with pytest.raises(HMRCPAYETestSupportTaxContractError):
        parse(body(employments=[{"employerPayeReference": bad, "taxTakenOffPay": 1}]))
    assert parse(body(employments=[{"employerPayeReference": "", "taxTakenOffPay": 1}]))
    assert parse(body(employments=[{"employerPayeReference": "   ", "taxTakenOffPay": 1}]))


def test_constructor_replace_copy_deepcopy_pickle_coherence():
    value = parse(body(employments=[{"employerPayeReference": "A", "taxTakenOffPay": Decimal("1.00")}]))
    assert copy.copy(value) == value
    assert copy.deepcopy(value) == value
    assert pickle.loads(pickle.dumps(value)) == value
    assert replace(value, scenario="HAPPY_PATH_2").scenario == "HAPPY_PATH_2"
    with pytest.raises(HMRCPAYETestSupportTaxContractError): replace(value, status_code=True)
    with pytest.raises(HMRCPAYETestSupportTaxContractError): replace(value.employments[0], tax_taken_off_pay=1.0)


def test_module_has_no_network_credential_or_product_engine_import_path():
    import ast
    import inspect
    import reserved.providers.hmrc_paye_test_support_tax_contract as module
    source_names = set(module.__dict__)
    assert not ({"requests", "httpx", "urllib", "socket", "token", "credential"} & source_names)
    imports = []
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    assert imports == ["__future__", "unicodedata", "dataclasses", "decimal"]
