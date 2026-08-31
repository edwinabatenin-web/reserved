from copy import deepcopy
from datetime import date
from decimal import Decimal
import json

import pytest

from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis, DeductionRepresentation, LoanBasisEvidence, LoanComponent,
    LoanDeductionEvidence, reconcile_annual_student_loans,
)
from reserved.engines.annual_position_composition import compose_internal_annual_position
from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.engines.internal_snapshot import decode_internal_snapshot, encode_internal_snapshot


def results():
    annual = calculate_annual_position({
        "employment_income": "30000",
        "blind_persons_allowance_entitled": False,
        "blind_persons_allowance_transferred_in": "0",
        "blind_persons_allowance_transferred_out": "0",
    })
    loan = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("E-BASIS",), True, True, (
            LoanBasisEvidence("E-BASIS", "synthetic", "synthetic://basis", "person-a", date(2027, 4, 5), "2026/27", True),
        )), [2],
        [LoanDeductionEvidence(
            "E-SL", LoanComponent.PLAN_2, "3000", "2026/27",
            date(2027, 4, 5), date(2027, 4, 5), "job-a",
            DeductionRepresentation.EMPLOYMENT_CUMULATIVE, True,
            "synthetic_document", "synthetic://sl",
        )],
        as_of=date(2027, 4, 5), declared_employment_ids=("job-a",),
    )
    composition = compose_internal_annual_position(
        annual, loan,
        annual_tax_reference="annual-position:snapshot-1",
        student_loan_reference="loan-reconciliation:snapshot-1",
    )
    return annual, loan, composition


def all_keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(all_keys(item) for item in value), set())
    return set()


@pytest.mark.parametrize("index", [0, 1, 2])
def test_every_approved_root_round_trips_losslessly_through_json(index):
    original = results()[index]
    primitive = encode_internal_snapshot(original)
    assert decode_internal_snapshot(json.loads(json.dumps(primitive))) == original
    assert primitive["purpose"] == "internal_ephemeral_handoff_not_persistence_approval"
    assert not {"combined_total", "combined_balance", "amount_due", "customer_balance"} & all_keys(primitive)


def test_decimal_date_enum_and_provenance_remain_tagged_and_exact():
    primitive = encode_internal_snapshot(results()[1])
    text = json.dumps(primitive)
    assert '"$decimal": "6625.00"' in text
    assert '"$date": "2027-04-05"' in text
    assert '"$enum": "LoanComponent"' in text
    decoded = decode_internal_snapshot(primitive)
    assert decoded.components[0].annual_liability == Decimal("6625.00")
    assert decoded.components[0].evidence_decisions[0].source_reference == "synthetic://sl"


@pytest.mark.parametrize("mutation", ["unknown_root", "missing_root", "version", "purpose", "type_mismatch"])
def test_hostile_root_contract_changes_fail_closed(mutation):
    snapshot = encode_internal_snapshot(results()[0])
    if mutation == "unknown_root": snapshot["injected"] = True
    elif mutation == "missing_root": del snapshot["purpose"]
    elif mutation == "version": snapshot["snapshot_version"] = "reserved-internal-snapshot/999"
    elif mutation == "purpose": snapshot["purpose"] = "production_persistence"
    else: snapshot["root_type"] = "AnnualLoanReconciliation"
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


def test_unknown_missing_nested_fields_and_combined_money_fail_closed():
    base = encode_internal_snapshot(results()[2])
    for mutate in ("unknown", "missing", "combined"):
        snapshot = deepcopy(base)
        fields = snapshot["payload"]["fields"]
        if mutate == "unknown": fields["invented"] = 1
        elif mutate == "missing": del fields["limitations"]
        else: fields["combined_balance"] = {"$decimal": "1.00"}
        with pytest.raises(ValueError):
            decode_internal_snapshot(snapshot)


@pytest.mark.parametrize(
    "tag,value",
    [("$decimal", "NaN"), ("$decimal", "not-money"), ("$date", "2027-02-30")],
)
def test_malformed_typed_primitives_fail_closed(tag, value):
    snapshot = encode_internal_snapshot(results()[0])
    snapshot["payload"]["fields"]["adjusted_net_income"] = {tag: value}
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


def test_unknown_enum_and_extra_tag_fields_fail_closed():
    snapshot = encode_internal_snapshot(results()[1])
    component = snapshot["payload"]["fields"]["components"]["$tuple"][0]
    component["fields"]["component"] = {"$enum": "UnknownEnum", "value": "plan_2"}
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("annual", "contract_version", "hostile/999"),
        ("annual", "calculation_status", "customer_ready"),
        ("loan", "contract_version", "hostile/999"),
        ("loan", "calculation_status", "customer_ready"),
        ("loan", "prohibited_uses", {"$tuple": []}),
        ("composition", "contract_version", "hostile/999"),
        ("composition", "composition_status", "customer_ready"),
        ("composition", "prohibited_uses", {"$tuple": []}),
    ],
)
def test_exact_shape_semantic_weakening_is_rejected(target, field, value):
    index = {"annual": 0, "loan": 1, "composition": 2}[target]
    snapshot = encode_internal_snapshot(results()[index])
    snapshot["payload"]["fields"][field] = value
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


def test_nested_prohibition_and_completeness_weakening_is_rejected():
    snapshot = encode_internal_snapshot(results()[2])
    snapshot["payload"]["fields"]["student_loans"]["fields"]["prohibited_uses"] = {"$tuple": []}
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)

    snapshot = encode_internal_snapshot(results()[2])
    snapshot["payload"]["fields"]["component_set_complete"] = False
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


def test_calculated_annual_position_cannot_withhold_its_total_in_snapshot():
    snapshot = encode_internal_snapshot(results()[0])
    snapshot["payload"]["fields"]["total_liability"] = None
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


def test_composition_mandatory_limitations_and_typed_nested_references_cannot_be_weakened():
    for field, value in (
        ("limitations", {"$tuple": []}),
    ):
        snapshot = encode_internal_snapshot(results()[2])
        snapshot["payload"]["fields"][field] = value
        with pytest.raises(ValueError):
            decode_internal_snapshot(snapshot)


@pytest.mark.parametrize("wrapper,bad_ref", [
    ("annual_tax", "annual-position:../../ customer"),
    ("student_loans", "loan-reconciliation:bad/id"),
])
def test_namespaced_references_must_still_match_producer_identifier_grammar(wrapper, bad_ref):
    snapshot = encode_internal_snapshot(results()[2])
    snapshot["payload"]["fields"][wrapper]["fields"]["reference"] = bad_ref
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


@pytest.mark.parametrize("index", [0, 1])
def test_root_producer_rulesets_are_pinned(index):
    snapshot = encode_internal_snapshot(results()[index])
    snapshot["payload"]["fields"]["ruleset_version"] = "hostile-rules/999"
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


@pytest.mark.parametrize("wrapper", ["annual_tax", "student_loans"])
def test_composed_producer_rulesets_must_be_supported_and_compatible(wrapper):
    snapshot = encode_internal_snapshot(results()[2])
    snapshot["payload"]["fields"][wrapper]["fields"]["ruleset_version"] = "uk-2099-00-v1"
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)
    for wrapper, bad_ref in (
        ("annual_tax", "display:tax"),
        ("student_loans", "display:loan"),
    ):
        snapshot = encode_internal_snapshot(results()[2])
        snapshot["payload"]["fields"][wrapper]["fields"]["reference"] = bad_ref
        with pytest.raises(ValueError):
            decode_internal_snapshot(snapshot)


def test_calculated_loan_root_cannot_contain_incomplete_component():
    snapshot = encode_internal_snapshot(results()[1])
    component = snapshot["payload"]["fields"]["components"]["$tuple"][0]
    component["fields"]["calculation_status"] = "insufficient_facts"
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_all_snapshot_roots_are_pinned_to_the_supported_tax_year(index):
    snapshot = encode_internal_snapshot(results()[index])
    snapshot["payload"]["fields"]["tax_year"] = "2025/26"
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)

    snapshot = encode_internal_snapshot(results()[0])
    snapshot["payload"]["fields"]["income_tax_before_limitations"]["extra"] = True
    with pytest.raises(ValueError):
        decode_internal_snapshot(snapshot)
