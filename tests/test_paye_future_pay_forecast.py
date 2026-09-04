"""Adversarial tests for the bounded PAYE future-pay forecast composer."""

from __future__ import annotations

import copy
from datetime import date, timedelta
from decimal import Decimal
import pickle

import pytest

from reserved.engines.paye_reconciliation import (
    Completeness,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
    make_paye_reconciliation_policy,
    reconcile_paye,
)
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact,
    FuturePayForecastPolicy,
    FuturePayFrequency,
    FuturePaySource,
    PayeFuturePayForecast,
    PeriodCompleteness,
    compose_paye_future_pay_forecast,
    make_future_pay_forecast_policy,
    project_paye_future_pay_forecast,
)


AS_OF = date(2026, 10, 1)
OWNER = "owner-1"
BUSINESS = "business-1"
TAX_YEAR = "2026-27"
RECONCILIATION_POLICY = make_paye_reconciliation_policy(45, Decimal("1.00"))
FORECAST_POLICY = make_future_pay_forecast_policy(30, Decimal("100.00"))


def evidence(**changes):
    values = {
        "kind": EvidenceKind.DOCUMENT,
        "tax_year": TAX_YEAR,
        "tax_paid_to_date": "2500.00",
        "gross_pay_to_date": "20000.00",
        "employment_id": "employment-1",
        "observed_on": AS_OF,
        "source_reference": "customer_confirmed:payslip",
        "evidence_id": "payslip-1",
        "representation": EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
        "completeness": Completeness.COMPLETE_FOR_REPRESENTATION,
        "effective_through": AS_OF,
    }
    values.update(changes)
    return PayeEvidence(**values)


def reconciliation(*items, tax_year=TAX_YEAR, as_of=AS_OF):
    return reconcile_paye(
        "9000.00",
        tuple(items or (evidence(),)),
        tax_year=tax_year,
        as_of=as_of,
        policy=RECONCILIATION_POLICY,
    )


def fact(**changes):
    values = {
        "source": FuturePaySource.CUSTOMER_CONFIRMED,
        "fact_id": "future-pay-1",
        "source_evidence_id": "confirmation-1",
        "source_evidence_digest": "a" * 64,
        "owner_id": OWNER,
        "business_id": BUSINESS,
        "tax_year": TAX_YEAR,
        "employment_id": "employment-1",
        "gross_pay": "5000.00",
        "expected_tax_deduction": "750.00",
        "pay_date": date(2026, 10, 31),
        "period_start": date(2026, 10, 2),
        "period_end": date(2026, 10, 31),
        "confirmed_on": AS_OF,
        "frequency": FuturePayFrequency.MONTHLY,
        "period_completeness": PeriodCompleteness.COMPLETE,
    }
    values.update(changes)
    return ConfirmedFuturePayFact(**values)


def compose(*facts, result=None, policy=FORECAST_POLICY, **binding):
    values = {
        "owner_id": OWNER,
        "business_id": BUSINESS,
        "tax_year": TAX_YEAR,
        "as_of": AS_OF,
        "policy": policy,
    }
    values.update(binding)
    return compose_paye_future_pay_forecast(
        result or reconciliation(), tuple(facts or (fact(),)), **values
    )


def projection(value):
    return dict(project_paye_future_pay_forecast(value))


def test_composes_only_explicit_confirmed_amounts_and_detached_provenance():
    first = fact()
    second = fact(
        source=FuturePaySource.CONFIRMED_SOURCE_DOCUMENT,
        fact_id="future-pay-2",
        source_evidence_id="confirmation-2",
        source_evidence_digest="b" * 64,
        gross_pay=Decimal("3000.10"),
        expected_tax_deduction=Decimal("0.00"),
        pay_date=date(2026, 11, 30),
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
    )
    output = compose(second, first)
    state = projection(output)

    assert type(output) is PayeFuturePayForecast
    assert state["owner_id"] == OWNER
    assert state["business_id"] == BUSINESS
    assert state["tax_year"] == TAX_YEAR
    assert state["reconciled_tax_paid_to_date"] == Decimal("2500.00")
    assert state["reconciliation_effective_through"] == AS_OF
    assert state["reconciliation_provenance"] == ((
        "document", "customer_confirmed:payslip", "payslip-1", AS_OF, AS_OF,
    ),)
    assert len(state["reconciliation_digest"]) == 64
    assert state["expected_future_gross_pay"] == Decimal("8000.10")
    assert state["expected_future_tax_deduction"] == Decimal("750.00")
    assert state["projected_tax_deducted_total"] == Decimal("3250.00")
    assert state["expected_pay_dates"] == (date(2026, 10, 31), date(2026, 11, 30))
    assert state["material_threshold_reached"] is True
    assert state["forecast_status"] == "confirmed_inputs_composed_not_observed"
    assert state["coverage_scope"] == "submitted_confirmed_periods_only"
    assert state["owner_business_authentication_status"] == (
        "not_established_requires_authenticated_orchestration"
    )
    assert state["customer_authority_status"] == "not_customer_authoritative"
    assert state["orchestration_requirement"] == (
        "authenticated_owner_business_reconciliation_binding_required"
    )
    assert state["source_provenance"][0][:4] == (
        "future-pay-1", "confirmation-1", "a" * 64, "customer_confirmed"
    )
    assert all(type(item) is not ConfirmedFuturePayFact for item in state["source_provenance"])
    assert "forecast_does_not_establish_final_tax_liability" in state["uncertainties"]


def test_input_order_does_not_change_projection_or_digest():
    later = fact(
        fact_id="future-pay-2",
        source_evidence_id="confirmation-2",
        source_evidence_digest="b" * 64,
        pay_date=date(2026, 11, 30),
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
    )
    assert project_paye_future_pay_forecast(compose(fact(), later)) == (
        project_paye_future_pay_forecast(compose(later, fact()))
    )


@pytest.mark.parametrize("field", ["owner_id", "business_id", "tax_year"])
def test_cross_owner_business_and_tax_year_facts_fail_closed(field):
    changed = {field: "2025-26" if field == "tax_year" else "other"}
    if field == "tax_year":
        changed.update({
            "pay_date": date(2025, 10, 31),
            "period_start": date(2025, 10, 2),
            "period_end": date(2025, 10, 31),
            "confirmed_on": date(2025, 10, 1),
        })
    with pytest.raises(ValueError, match="owner, business or tax year"):
        compose(fact(**changed))


def test_reconciliation_tax_year_mismatch_fails_closed():
    other_as_of = date(2025, 10, 1)
    other = evidence(
        tax_year="2025-26",
        observed_on=other_as_of,
        effective_through=other_as_of,
    )
    with pytest.raises(ValueError, match="tax year does not match"):
        compose(fact(), result=reconciliation(other, tax_year="2025-26", as_of=other_as_of))


def test_selected_reconciliation_observation_after_forecast_date_fails_separately():
    later = evidence(observed_on=AS_OF + timedelta(days=1), effective_through=AS_OF)
    later_reconciliation = reconciliation(later, as_of=AS_OF + timedelta(days=1))
    with pytest.raises(ValueError, match="observation is after forecast date"):
        compose(fact(), result=later_reconciliation)


def test_selected_reconciliation_effective_period_after_forecast_date_fails_separately():
    later_date = AS_OF + timedelta(days=1)
    later = evidence(observed_on=later_date, effective_through=later_date)
    later_reconciliation = reconciliation(later, as_of=later_date)
    with pytest.raises(ValueError, match="effective period is after forecast date"):
        compose(fact(), result=later_reconciliation)


def test_selected_reconciliation_dates_equal_to_forecast_date_are_accepted():
    state = projection(compose(fact(), result=reconciliation(evidence())))
    assert state["reconciliation_effective_through"] == AS_OF


@pytest.mark.parametrize(
    "facts, message",
    [
        ((fact(), fact()), "fact identifiers"),
        ((fact(), fact(fact_id="future-pay-2")), "source evidence identifiers"),
        ((fact(), fact(fact_id="future-pay-2", source_evidence_id="confirmation-2")),
         "source evidence digests"),
        ((fact(), fact(
            fact_id="future-pay-2", source_evidence_id="confirmation-2",
            source_evidence_digest="b" * 64,
        )), "duplicate represented payments"),
    ],
)
def test_duplicate_id_source_digest_and_semantic_payment_fail(facts, message):
    with pytest.raises(ValueError, match=message):
        compose(*facts)


def test_overlapping_periods_for_same_employment_fail_instead_of_double_counting():
    overlapping = fact(
        fact_id="future-pay-2",
        source_evidence_id="confirmation-2",
        source_evidence_digest="b" * 64,
        pay_date=date(2026, 11, 15),
        period_start=date(2026, 10, 15),
        period_end=date(2026, 11, 15),
    )
    with pytest.raises(ValueError, match="overlapping represented periods"):
        compose(fact(), overlapping)


def test_same_dates_for_distinct_employments_remain_independently_composable():
    other_job = fact(
        fact_id="future-pay-2",
        source_evidence_id="confirmation-2",
        source_evidence_digest="b" * 64,
        employment_id="employment-2",
    )
    state = projection(compose(fact(), other_job))
    assert state["fact_count"] == 2
    assert state["expected_future_tax_deduction"] == Decimal("1500.00")


def test_partial_period_fails_closed():
    with pytest.raises(ValueError, match="partial period"):
        compose(fact(period_completeness=PeriodCompleteness.PARTIAL))


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("gross_pay", "0", "gross pay"),
        ("gross_pay", "-1", "gross pay"),
        ("expected_tax_deduction", "-0.01", "expected tax deduction"),
        ("gross_pay", "1.001", "gross pay"),
        ("expected_tax_deduction", 1.0, "expected tax deduction"),
        ("gross_pay", True, "gross pay"),
    ],
)
def test_zero_negative_inexact_and_wrong_runtime_amounts_fail(field, value, message):
    with pytest.raises((TypeError, ValueError), match=message):
        fact(**{field: value})


def test_exact_zero_expected_tax_is_preserved_not_missing():
    state = projection(compose(fact(expected_tax_deduction=0)))
    assert state["expected_future_tax_deduction"] == Decimal("0.00")
    assert state["projected_tax_deducted_total"] == Decimal("2500.00")


def test_expected_tax_may_equal_but_never_exceed_explicit_gross_pay():
    at_boundary = projection(compose(fact(
        gross_pay=Decimal("5000.00"),
        expected_tax_deduction=Decimal("5000.00"),
    )))
    assert at_boundary["expected_future_tax_deduction"] == Decimal("5000.00")

    with pytest.raises(ValueError, match="exceeds gross pay"):
        compose(fact(
            gross_pay=Decimal("5000.00"),
            expected_tax_deduction=Decimal("5000.01"),
        ))


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"pay_date": AS_OF, "period_start": AS_OF, "period_end": AS_OF},
         "after the forecast date"),
        ({"confirmed_on": AS_OF + timedelta(days=1)}, "not confirmed"),
        ({"confirmed_on": AS_OF - timedelta(days=31)}, "stale"),
        ({"period_start": AS_OF}, "overlaps"),
        ({"period_start": date(2026, 12, 1), "period_end": date(2026, 11, 30)},
         "period must fall"),
        ({"pay_date": date(2026, 10, 15), "period_end": date(2026, 10, 31)},
         "date must follow"),
    ],
)
def test_time_ordering_overlap_and_staleness_fail_closed(changes, message):
    with pytest.raises(ValueError, match=message):
        compose(fact(**changes))


def test_confirmation_age_threshold_boundaries_are_exact():
    policy = make_future_pay_forecast_policy(30, Decimal("100.00"))
    compose(fact(confirmed_on=AS_OF - timedelta(days=30)), policy=policy)
    with pytest.raises(ValueError, match="stale"):
        compose(fact(confirmed_on=AS_OF - timedelta(days=31)), policy=policy)


def test_materiality_threshold_boundaries_are_exact_and_do_not_filter_facts():
    policy = make_future_pay_forecast_policy(30, Decimal("750.00"))
    at_boundary = projection(compose(fact(expected_tax_deduction="750"), policy=policy))
    below = projection(compose(fact(expected_tax_deduction="749.99"), policy=policy))
    assert at_boundary["material_threshold_reached"] is True
    assert below["material_threshold_reached"] is False
    assert below["expected_future_tax_deduction"] == Decimal("749.99")


@pytest.mark.parametrize(
    "args",
    [
        (True, Decimal("1.00")),
        (1.0, Decimal("1.00")),
        (-1, Decimal("1.00")),
        (1, Decimal("1")),
        (1, Decimal("-0.01")),
    ],
)
def test_policy_thresholds_require_exact_bounded_runtime_types(args):
    with pytest.raises((TypeError, ValueError)):
        make_future_pay_forecast_policy(*args)


def test_unsupported_frequency_and_subtypes_fail_closed():
    with pytest.raises(TypeError, match="frequency"):
        fact(frequency="monthly")

    class DateSubclass(date):
        pass

    with pytest.raises(TypeError, match="pay_date"):
        fact(pay_date=DateSubclass(2026, 10, 31))


def test_missing_or_ambiguous_reconciliation_fails_closed():
    empty = reconcile_paye(
        "9000.00", (), tax_year=TAX_YEAR, as_of=AS_OF, policy=RECONCILIATION_POLICY
    )
    with pytest.raises(ValueError, match="incomplete, stale or ambiguous"):
        compose(fact(), result=empty)

    conflict = reconciliation(
        evidence(kind=EvidenceKind.HMRC, evidence_id="hmrc", tax_paid_to_date="2500"),
        evidence(kind=EvidenceKind.DOCUMENT, evidence_id="document", tax_paid_to_date="2600"),
    )
    with pytest.raises(ValueError, match="incomplete, stale or ambiguous"):
        compose(fact(), result=conflict)


def test_stale_reconciliation_fails_closed_even_when_it_has_a_point_amount():
    stale_date = AS_OF - timedelta(days=46)
    stale = reconciliation(evidence(observed_on=stale_date, effective_through=stale_date))
    with pytest.raises(ValueError, match="incomplete, stale or ambiguous"):
        compose(fact(period_start=stale_date + timedelta(days=1)), result=stale)


def test_mutated_fact_and_forged_reconciliation_are_rejected():
    item = fact()
    object.__setattr__(item, "owner_id", "attacker")
    with pytest.raises(ValueError, match="integrity"):
        compose(item)
    with pytest.raises(ValueError, match="cannot be re-issued"):
        item.__post_init__()

    forged_fact = object.__new__(ConfirmedFuturePayFact)
    with pytest.raises((AttributeError, TypeError, ValueError)):
        compose(forged_fact)

    forged = object.__new__(type(reconciliation()))
    with pytest.raises(ValueError, match="reconciliation validation"):
        compose(fact(), result=forged)


def test_future_source_identity_cannot_collide_with_selected_reconciliation_evidence():
    with pytest.raises(ValueError, match="collides with reconciled evidence"):
        compose(fact(source_evidence_id="payslip-1"))


def test_result_policy_and_fact_are_immutable_copy_safe_and_not_pickleable():
    item = fact()
    output = compose(item)
    assert copy.copy(item) is item
    assert copy.deepcopy(item) is item
    assert copy.copy(FORECAST_POLICY) is FORECAST_POLICY
    assert copy.deepcopy(output) is output
    with pytest.raises(Exception):
        item.owner_id = "other"
    with pytest.raises(Exception):
        FORECAST_POLICY.max_confirmation_age_days = 999
    with pytest.raises(Exception):
        output.anything = "other"
    for value in (item, FORECAST_POLICY, output):
        with pytest.raises(TypeError):
            pickle.dumps(value)


def test_direct_policy_and_result_construction_and_object_new_forgery_fail():
    with pytest.raises(TypeError):
        FuturePayForecastPolicy()
    with pytest.raises(TypeError):
        PayeFuturePayForecast()
    forged = object.__new__(PayeFuturePayForecast)
    with pytest.raises(ValueError, match="not producer-issued"):
        project_paye_future_pay_forecast(forged)


def test_runtime_limitations_are_fixed_detached_and_cannot_be_forged_by_mutation():
    output = compose(fact())
    before = project_paye_future_pay_forecast(output)
    state = dict(before)
    assert state["coverage_scope"] == "submitted_confirmed_periods_only"
    assert state["owner_business_authentication_status"].startswith("not_established")
    assert state["customer_authority_status"] == "not_customer_authoritative"
    assert state["orchestration_requirement"].startswith("authenticated_owner_business")
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(output, "coverage_scope", "all_future_pay")
    assert project_paye_future_pay_forecast(output) == before


def test_rebound_module_projector_does_not_change_captured_reconciliation(monkeypatch):
    import reserved.services.paye_future_pay_forecast as module

    monkeypatch.setattr(module, "project_paye_reconciliation", lambda value: ())
    state = projection(compose(fact()))
    assert state["reconciled_tax_paid_to_date"] == Decimal("2500.00")


def test_no_facts_or_non_tuple_facts_fail_closed():
    with pytest.raises(ValueError, match="count"):
        compose_paye_future_pay_forecast(
            reconciliation(), (), owner_id=OWNER, business_id=BUSINESS,
            tax_year=TAX_YEAR, as_of=AS_OF, policy=FORECAST_POLICY,
        )
    with pytest.raises(TypeError, match="exact tuple"):
        compose_paye_future_pay_forecast(
            reconciliation(), [fact()], owner_id=OWNER, business_id=BUSINESS,
            tax_year=TAX_YEAR, as_of=AS_OF, policy=FORECAST_POLICY,
        )


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64, "", None])
def test_source_evidence_digest_must_be_exact_lowercase_sha256(digest):
    with pytest.raises((TypeError, ValueError), match="digest"):
        fact(source_evidence_digest=digest)
