"""Synthetic-only tests for PAYE reconciliation and fallback evidence."""

import copy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import pickle

import pytest

import reserved.engines.paye_reconciliation as module

from reserved.engines.paye_reconciliation import (
    Completeness,
    Confidence,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
    PayeReconciliation,
    PayeReconciliationPolicy,
    make_paye_reconciliation_policy,
    project_paye_conflict,
    project_paye_evidence,
    project_paye_reconciliation,
    project_paye_reconciliation_policy,
    reconcile_paye,
)


TODAY = date(2026, 8, 12)
POLICY = make_paye_reconciliation_policy(45, Decimal("1.00"))


def reconcile(liability, evidence, **kwargs):
    return reconcile_paye(liability, tuple(evidence), policy=POLICY, **kwargs)


def ev(kind, paid, *, employment=None, days_old=0, evidence_id=None,
       representation=None, completeness=Completeness.COMPLETE_FOR_REPRESENTATION,
       covered_employments=("aggregate-scope",)):
    return PayeEvidence(
        kind=kind,
        tax_year="2026-27",
        tax_paid_to_date=paid,
        employment_id=employment,
        observed_on=TODAY - timedelta(days=days_old),
        effective_through=TODAY - timedelta(days=days_old),
        evidence_id=evidence_id or f"{kind.value}-{employment or 'aggregate'}-{days_old}",
        representation=representation or (
            EvidenceRepresentation.EMPLOYMENT_CUMULATIVE if employment
            else EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE
        ),
        completeness=completeness,
        covered_employment_ids=() if employment else covered_employments,
    )


def test_one_paye_employment_uses_hmrc_tax_paid():
    result = reconcile("6000", [ev(EvidenceKind.HMRC, "2100", employment="job-a")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2100.00")
    assert result.estimated_remaining_liability == Decimal("3900.00")
    assert result.confidence is Confidence.HIGH


def test_multiple_employments_are_summed_without_collapsing_sources():
    result = reconcile("10000", [
        ev(EvidenceKind.HMRC, "1800", employment="job-a"),
        ev(EvidenceKind.HMRC, "700", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2500.00")
    assert result.estimated_remaining_liability == Decimal("7500.00")


def test_conflict_is_retained_and_reduces_confidence():
    result = reconcile("6000", [
        ev(EvidenceKind.HMRC, "2100", employment="job-a"),
        ev(EvidenceKind.DOCUMENT, "2000", employment="job-a"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_known is False
    assert result.calculation_status == "conflict_requires_review"
    assert result.conflicts[0].difference == Decimal("100.00")
    assert result.confidence is Confidence.INCOMPLETE
    assert result.estimated_remaining_liability_low == Decimal("3900.00")
    assert result.estimated_remaining_liability_high == Decimal("4000.00")


def test_newer_document_does_not_win_unresolved_conflict_by_recency_alone():
    result = reconcile("6000", [
        ev(EvidenceKind.HMRC, "2100", employment="job-a", days_old=30),
        ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", days_old=1),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_known is False
    assert result.selected_kind is None
    assert result.selected_evidence == ()
    assert {item.kind for item in result.considered_evidence} == {
        EvidenceKind.HMRC, EvidenceKind.DOCUMENT
    }
    assert result.calculation_status == "conflict_requires_review"
    assert result.estimated_remaining_liability_low == Decimal("3900.00")
    assert result.estimated_remaining_liability_high == Decimal("4000.00")


def test_document_fallback_is_high_confidence_when_current():
    result = reconcile("6000", [ev(EvidenceKind.DOCUMENT, "2000")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.selected_kind is EvidenceKind.DOCUMENT
    assert result.confidence is Confidence.HIGH


def test_structured_manual_entry_is_medium_confidence():
    result = reconcile("6000", [ev(EvidenceKind.MANUAL, "1900")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.MEDIUM


def test_bank_inference_is_last_resort_and_low_confidence():
    result = reconcile("6000", [ev(EvidenceKind.BANK_INFERENCE, "1800")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.LOW
    assert any("last-resort" in warning for warning in result.warnings)


def test_stale_hmrc_data_reduces_confidence():
    result = reconcile("6000", [ev(EvidenceKind.HMRC, "1800", days_old=46)],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.MEDIUM
    assert any("out of date" in warning for warning in result.warnings)


def test_no_evidence_is_explicitly_incomplete():
    result = reconcile("6000", [], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date is None
    assert result.estimated_remaining_liability is None
    assert result.tax_paid_known is False
    assert result.conservative_assumed_tax_paid == Decimal("0.00")
    assert result.confidence is Confidence.INCOMPLETE


def test_aggregate_and_employment_evidence_are_not_double_counted():
    result = reconcile("6000", [
        ev(EvidenceKind.DOCUMENT, "2000", evidence_id="aggregate",
           representation=EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE,
           covered_employments=("job-a", "job-b")),
        ev(EvidenceKind.HMRC, "1200", employment="job-a"),
        ev(EvidenceKind.HMRC, "800", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2000.00")
    assert any("double counting" in warning for warning in result.warnings)


def test_tax_paid_above_estimate_yields_zero_remaining_not_negative():
    result = reconcile("1000", [ev(EvidenceKind.HMRC, "1200")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.estimated_remaining_liability == Decimal("0.00")
    assert result.apparent_overpayment == Decimal("200.00")


def test_unlinked_equal_aggregate_and_entity_totals_fail_closed():
    result = reconcile("6000", [
        ev(EvidenceKind.DOCUMENT, "2000"),
        ev(EvidenceKind.HMRC, "1200", employment="job-a"),
        ev(EvidenceKind.HMRC, "800", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.calculation_status == "insufficient_facts"
    assert result.tax_paid_known is False


def test_stale_period_reports_partial_unbounded_effect():
    result = reconcile("6000", [
        ev(EvidenceKind.HMRC, "2000", employment="job-a", days_old=72),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.estimated_remaining_liability == Decimal("4000.00")
    assert result.range_completeness == "partial"
    assert result.indeterminable_effect is True


def test_policy_is_explicit_exact_and_has_no_embedded_threshold_default():
    with pytest.raises(TypeError):
        reconcile_paye("1", (), tax_year="2026-27", as_of=TODAY)
    with pytest.raises(TypeError):
        reconcile_paye("1", (), tax_year="2026-27", as_of=TODAY, policy=object())
    with pytest.raises(TypeError):
        reconcile_paye(
            "1", (), "extra", tax_year="2026-27", as_of=TODAY, policy=POLICY
        )


def test_function_metadata_cannot_inject_implicit_policy_or_as_of_values():
    original_defaults = reconcile_paye.__defaults__
    original_kwdefaults = reconcile_paye.__kwdefaults__
    original_factory_defaults = make_paye_reconciliation_policy.__defaults__
    original_factory_kwdefaults = make_paye_reconciliation_policy.__kwdefaults__
    try:
        reconcile_paye.__defaults__ = ((),)
        reconcile_paye.__kwdefaults__ = {
            "tax_year": "2026-27",
            "as_of": TODAY,
            "policy": POLICY,
        }
        make_paye_reconciliation_policy.__defaults__ = (45, Decimal("1.00"))
        make_paye_reconciliation_policy.__kwdefaults__ = {
            "stale_after_days": 45,
            "conflict_tolerance": Decimal("1.00"),
        }
        with pytest.raises(TypeError, match="issued only"):
            PayeReconciliationPolicy()
        with pytest.raises(TypeError, match="exactly two positional"):
            make_paye_reconciliation_policy()
        with pytest.raises(TypeError, match="two positional inputs"):
            reconcile_paye("1", ())
        with pytest.raises(TypeError, match="two positional inputs"):
            reconcile_paye("1", (), tax_year="2026-27", policy=POLICY)
    finally:
        reconcile_paye.__defaults__ = original_defaults
        reconcile_paye.__kwdefaults__ = original_kwdefaults
        make_paye_reconciliation_policy.__defaults__ = original_factory_defaults
        make_paye_reconciliation_policy.__kwdefaults__ = original_factory_kwdefaults


def test_factory_issuance_survives_metaclass_constructor_and_default_rebinding():
    factory = make_paye_reconciliation_policy
    project_policy = project_paye_reconciliation_policy
    meta = type(PayeReconciliationPolicy)
    original_call = meta.__dict__["__call__"]
    original_new = PayeReconciliationPolicy.__dict__["__new__"]
    had_init = "__init__" in PayeReconciliationPolicy.__dict__
    original_init = PayeReconciliationPolicy.__dict__.get("__init__")

    def injected_init(
        self, stale_after_days=45, conflict_tolerance=Decimal("1.00")
    ):
        object.__setattr__(self, "stale_after_days", stale_after_days)
        object.__setattr__(self, "conflict_tolerance", conflict_tolerance)

    try:
        type.__setattr__(meta, "__call__", type.__call__)
        type.__setattr__(
            PayeReconciliationPolicy, "__new__", staticmethod(object.__new__)
        )
        type.__setattr__(PayeReconciliationPolicy, "__init__", injected_init)
        forged = PayeReconciliationPolicy()
        with pytest.raises(ValueError, match="integrity"):
            project_policy(forged)
        with pytest.raises(ValueError, match="integrity"):
            reconcile_paye(
                "1", (), tax_year="2026-27", as_of=TODAY, policy=forged
            )

        genuine = factory(45, Decimal("1.00"))
        assert dict(project_policy(genuine)) == {
            "stale_after_days": 45,
            "conflict_tolerance": Decimal("1.00"),
        }
        assert reconcile_paye(
            "1", (), tax_year="2026-27", as_of=TODAY, policy=genuine
        ).calculation_status == "insufficient_facts"
    finally:
        type.__setattr__(meta, "__call__", original_call)
        type.__setattr__(PayeReconciliationPolicy, "__new__", original_new)
        if had_init:
            type.__setattr__(PayeReconciliationPolicy, "__init__", original_init)
        else:
            type.__delattr__(PayeReconciliationPolicy, "__init__")


@pytest.mark.parametrize("days", [True, -1, 36_601])
def test_policy_rejects_invalid_recency_bounds(days):
    with pytest.raises((TypeError, ValueError)):
        make_paye_reconciliation_policy(days, Decimal("1.00"))


@pytest.mark.parametrize(
    "tolerance",
    ["1.00", 1, 1.0, Decimal("NaN"), Decimal("-0.00"), Decimal("1.0")],
)
def test_policy_rejects_nonexact_conflict_tolerance(tolerance):
    with pytest.raises((TypeError, ValueError)):
        make_paye_reconciliation_policy(45, tolerance)


def test_policy_values_control_recency_and_conflict_without_a_universal_value():
    stale_item = ev(EvidenceKind.HMRC, "1800", employment="job-a", days_old=46)
    stale = reconcile_paye(
        "6000", (stale_item,), tax_year="2026-27", as_of=TODAY,
        policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
    )
    current = reconcile_paye(
        "6000", (stale_item,), tax_year="2026-27", as_of=TODAY,
        policy=make_paye_reconciliation_policy(46, Decimal("1.00")),
    )
    assert stale.confidence is Confidence.MEDIUM
    assert current.confidence is Confidence.HIGH

    candidates = (
        ev(EvidenceKind.HMRC, "2001.01", employment="job-a", evidence_id="a-hmrc"),
        ev(EvidenceKind.DOCUMENT, "2000.00", employment="job-a", evidence_id="z-document"),
    )
    strict = reconcile_paye(
        "6000", candidates, tax_year="2026-27", as_of=TODAY,
        policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
    )
    wider = reconcile_paye(
        "6000", candidates, tax_year="2026-27", as_of=TODAY,
        policy=make_paye_reconciliation_policy(45, Decimal("1.01")),
    )
    assert strict.calculation_status == "conflict_requires_review"
    assert wider.selected_kind is EvidenceKind.DOCUMENT
    assert wider.selected_evidence_ids == ("z-document",)


def test_input_cardinality_has_exact_defensive_bounds_before_graph_traversal():
    with pytest.raises(ValueError, match="evidence tuple exceeds the defensive bound"):
        reconcile_paye(
            "6000",
            (object(),) * 10_001,
            tax_year="2026-27",
            as_of=TODAY,
            policy=POLICY,
        )

    covered = tuple(f"job-{index}" for index in range(1_001))
    with pytest.raises(ValueError, match="coverage exceeds the defensive bound"):
        ev(
            EvidenceKind.DOCUMENT,
            "2000",
            evidence_id="bounded-aggregate",
            covered_employments=covered,
        )


def test_same_kind_exact_selection_tie_is_independent_of_input_order():
    alpha = ev(
        EvidenceKind.DOCUMENT,
        "2000",
        evidence_id="alpha",
        covered_employments=("job-a",),
    )
    omega = ev(
        EvidenceKind.DOCUMENT,
        "2000",
        evidence_id="omega",
        covered_employments=("job-a",),
    )
    forward = reconcile(
        "6000", (alpha, omega), tax_year="2026-27", as_of=TODAY
    )
    reverse = reconcile(
        "6000", (omega, alpha), tax_year="2026-27", as_of=TODAY
    )
    assert forward.selected_evidence_ids == reverse.selected_evidence_ids == ("omega",)
    assert forward.tax_paid_to_date == reverse.tax_paid_to_date == Decimal("2000.00")


def test_source_kind_does_not_override_source_neutral_stable_identity():
    document = ev(
        EvidenceKind.DOCUMENT,
        "2000",
        evidence_id="zzzz-document",
        covered_employments=("job-a",),
    )
    hmrc = ev(
        EvidenceKind.HMRC,
        "2000",
        evidence_id="aaaa-hmrc",
        covered_employments=("job-a",),
    )
    result = reconcile(
        "6000", (document, hmrc), tax_year="2026-27", as_of=TODAY
    )
    assert result.selected_kind is EvidenceKind.DOCUMENT
    assert result.selected_evidence_ids == ("zzzz-document",)


def test_evidence_input_must_be_exact_tuple_without_consuming_one_shot_iterable():
    item = ev(EvidenceKind.HMRC, "1", employment="job-a")

    class OneShot:
        calls = 0

        def __iter__(self):
            self.calls += 1
            yield item

    one_shot = OneShot()
    for value in ([item], one_shot):
        with pytest.raises(TypeError, match="exact tuple"):
            reconcile_paye(
                "1", value, tax_year="2026-27", as_of=TODAY, policy=POLICY
            )
    assert one_shot.calls == 0


class _StringSubtype(str):
    pass


class _DecimalSubtype(Decimal):
    pass


class _DateSubtype(date):
    pass


def evidence(**changes):
    values = dict(
        kind=EvidenceKind.HMRC,
        tax_year="2026-27",
        tax_paid_to_date=Decimal("1.00"),
        employment_id="job-a",
        observed_on=TODAY,
        evidence_id="evidence-a",
        representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
        completeness=Completeness.COMPLETE_FOR_REPRESENTATION,
        effective_through=TODAY,
    )
    values.update(changes)
    return PayeEvidence(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "hmrc"),
        ("representation", "employment_cumulative"),
        ("completeness", "complete_for_representation"),
        ("tax_year", _StringSubtype("2026-27")),
        ("employment_id", _StringSubtype("job-a")),
        ("evidence_id", ""),
        ("observed_on", _DateSubtype(2026, 8, 12)),
    ],
)
def test_evidence_rejects_wrong_enum_identifier_tax_year_and_date_types(field, value):
    with pytest.raises((TypeError, ValueError)):
        evidence(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        True,
        1.0,
        _DecimalSubtype("1.00"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-0.00"),
        Decimal("-1.00"),
        Decimal("1000000000000000000.01"),
        "1e3",
        "01",
        "1.001",
    ],
)
def test_evidence_rejects_unsafe_or_ambiguous_amounts(value):
    with pytest.raises((TypeError, ValueError)):
        evidence(tax_paid_to_date=value)


@pytest.mark.parametrize("tax_year", ["٢٠٢٦-٢٧", "２０２６-２７", "2026-28", "2026/27"])
def test_evidence_rejects_non_ascii_or_nonconsecutive_tax_year(tax_year):
    with pytest.raises(ValueError):
        evidence(tax_year=tax_year)


def test_representation_and_coverage_must_be_coherent_and_unique():
    with pytest.raises(ValueError, match="aggregate representation coverage"):
        evidence(
            employment_id=None,
            representation=EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE,
            covered_employment_ids=(),
        )
    with pytest.raises(ValueError, match="employment representation identity"):
        evidence(covered_employment_ids=("job-a",))
    with pytest.raises(ValueError, match="duplicates"):
        evidence(
            employment_id=None,
            representation=EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE,
            covered_employment_ids=("job-a", "job-a"),
        )


def test_mixed_years_duplicate_ids_and_future_observations_are_rejected():
    other_year = evidence(
        tax_year="2025-26",
        observed_on=date(2026, 4, 5),
        effective_through=date(2026, 4, 5),
        evidence_id="other-year",
    )
    with pytest.raises(ValueError, match="mixed or mismatched"):
        reconcile_paye(
            "1", (evidence(), other_year), tax_year="2026-27", as_of=TODAY,
            policy=POLICY,
        )
    first = evidence(evidence_id="duplicate")
    second = evidence(evidence_id="duplicate", tax_paid_to_date="2")
    with pytest.raises(ValueError, match="duplicates"):
        reconcile_paye(
            "1", (first, second), tax_year="2026-27", as_of=TODAY, policy=POLICY
        )
    future = evidence(
        observed_on=date(2026, 8, 13), effective_through=date(2026, 8, 12)
    )
    with pytest.raises(ValueError, match="after reconciliation"):
        reconcile_paye(
            "1", (future,), tax_year="2026-27", as_of=TODAY, policy=POLICY
        )


def test_missing_and_exact_zero_remain_distinct_at_reconciliation_boundary():
    missing = evidence(tax_paid_to_date=None)
    exact_zero = evidence(tax_paid_to_date=0, evidence_id="zero")
    missing_result = reconcile_paye(
        "1", (missing,), tax_year="2026-27", as_of=TODAY, policy=POLICY
    )
    zero_result = reconcile_paye(
        "1", (exact_zero,), tax_year="2026-27", as_of=TODAY, policy=POLICY
    )
    assert missing_result.tax_paid_to_date is None
    assert missing_result.conservative_assumed_tax_paid == Decimal("0.00")
    assert zero_result.tax_paid_to_date == Decimal("0.00")
    assert zero_result.conservative_assumed_tax_paid is None


def test_aggregate_coverage_and_period_mismatch_fails_closed_before_arithmetic():
    aggregate = ev(
        EvidenceKind.DOCUMENT,
        "2000",
        evidence_id="aggregate",
        covered_employments=("job-a", "job-b"),
    )
    job_a = ev(EvidenceKind.HMRC, "1200", employment="job-a")
    job_b = PayeEvidence(
        EvidenceKind.HMRC,
        "2026-27",
        "800",
        employment_id="job-b",
        observed_on=TODAY,
        effective_through=TODAY - timedelta(days=1),
        evidence_id="job-b",
        representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
        completeness=Completeness.COMPLETE_FOR_REPRESENTATION,
    )
    result = reconcile(
        "6000", (aggregate, job_a, job_b), tax_year="2026-27", as_of=TODAY
    )
    assert result.calculation_status == "insufficient_facts"
    assert result.tax_paid_to_date is None


def test_newer_document_wins_and_exact_tie_uses_source_neutral_identity():
    older_hmrc = ev(
        EvidenceKind.HMRC, "2000", employment="job-a", days_old=2,
        evidence_id="hmrc",
    )
    newer_document = ev(
        EvidenceKind.DOCUMENT, "2000", employment="job-a", days_old=1,
        evidence_id="document",
    )
    result = reconcile(
        "6000", (older_hmrc, newer_document), tax_year="2026-27", as_of=TODAY
    )
    assert result.selected_kind is EvidenceKind.DOCUMENT
    assert result.selected_evidence_ids == ("document",)

    tied_hmrc = ev(
        EvidenceKind.HMRC, "2000", employment="job-a", evidence_id="hmrc-tied"
    )
    tied_document = ev(
        EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="doc-tied"
    )
    tied = reconcile(
        "6000", (tied_document, tied_hmrc), tax_year="2026-27", as_of=TODAY
    )
    assert tied.selected_kind is EvidenceKind.HMRC
    assert tied.selected_evidence_ids == ("hmrc-tied",)


def test_result_is_producer_issued_immutable_and_reconstruction_safe():
    result = reconcile(
        "6000", (ev(EvidenceKind.HMRC, "2000", employment="job-a"),),
        tax_year="2026-27", as_of=TODAY,
    )
    with pytest.raises(TypeError, match="constructed directly"):
        PayeReconciliation()
    forged = object.__new__(PayeReconciliation)
    with pytest.raises(ValueError, match="producer-issued"):
        _ = forged.tax_year
    with pytest.raises(AttributeError):
        result.tax_year = "2025-26"
    with pytest.raises(AttributeError):
        object.__setattr__(result, "tax_year", "2025-26")
    with pytest.raises(TypeError):
        replace(result)
    assert copy.copy(result) is result
    assert copy.deepcopy(result) is result
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(result)


def test_nested_conflict_mutation_invalidates_the_issued_result():
    result = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", evidence_id="hmrc"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="doc"),
        ),
        tax_year="2026-27", as_of=TODAY,
    )
    conflict = result.conflicts[0]
    object.__setattr__(conflict, "difference", Decimal("0.00"))
    with pytest.raises(ValueError, match="integrity"):
        _ = result.conflicts


def test_exact_fingerprints_reject_equality_equal_field_subtypes():
    item = ev(EvidenceKind.HMRC, "2000", employment="job-a", evidence_id="exact-id")
    result = reconcile("6000", (item,), tax_year="2026-27", as_of=TODAY)
    object.__setattr__(item, "evidence_id", _StringSubtype("exact-id"))
    with pytest.raises(ValueError, match="integrity"):
        copy.copy(item)
    with pytest.raises(ValueError, match="integrity"):
        copy.deepcopy(item)
    with pytest.raises(ValueError, match="integrity"):
        _ = result.considered_evidence

    conflict_result = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", evidence_id="a"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="b"),
        ),
        tax_year="2026-27",
        as_of=TODAY,
    )
    conflict = conflict_result.conflicts[0]
    object.__setattr__(conflict, "field", _StringSubtype("tax_paid_to_date"))
    with pytest.raises(ValueError, match="integrity"):
        copy.copy(conflict)
    with pytest.raises(ValueError, match="integrity"):
        project_paye_conflict(conflict)
    with pytest.raises(ValueError, match="integrity"):
        _ = conflict_result.conflicts


def test_policy_and_conflict_copy_pickle_and_mutation_boundaries():
    policy = make_paye_reconciliation_policy(45, Decimal("1.00"))
    assert copy.copy(policy) is policy
    assert copy.deepcopy(policy) is policy
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(policy)
    object.__setattr__(policy, "stale_after_days", 46)
    with pytest.raises(ValueError, match="integrity"):
        copy.copy(policy)

    result = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", evidence_id="a"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="b"),
        ),
        tax_year="2026-27",
        as_of=TODAY,
    )
    conflict = result.conflicts[0]
    assert copy.copy(conflict) is conflict
    assert copy.deepcopy(conflict) is conflict
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(conflict)


def test_multi_employment_public_state_and_conflicts_are_order_independent():
    evidence_values = (
        ev(EvidenceKind.HMRC, "1200", employment="job-b", evidence_id="z-job-b"),
        ev(EvidenceKind.DOCUMENT, "800", employment="job-a", evidence_id="a-job-a"),
    )
    forward = reconcile("6000", evidence_values, tax_year="2026-27", as_of=TODAY)
    reverse = reconcile("6000", tuple(reversed(evidence_values)), tax_year="2026-27", as_of=TODAY)
    assert project_paye_reconciliation(forward) == project_paye_reconciliation(reverse)

    conflicting = evidence_values + (
        ev(EvidenceKind.MANUAL, "1000", employment="job-a", evidence_id="m-job-a"),
        ev(EvidenceKind.DOCUMENT, "1400", employment="job-b", evidence_id="d-job-b"),
    )
    forward_conflict = reconcile(
        "6000", conflicting, tax_year="2026-27", as_of=TODAY
    )
    reverse_conflict = reconcile(
        "6000", tuple(reversed(conflicting)), tax_year="2026-27", as_of=TODAY
    )
    assert project_paye_reconciliation(
        forward_conflict
    ) == project_paye_reconciliation(reverse_conflict)


def test_stale_conflict_preserves_partial_later_period_uncertainty():
    result = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", days_old=72,
               evidence_id="a-stale"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", days_old=71,
               evidence_id="b-stale"),
        ),
        tax_year="2026-27",
        as_of=TODAY,
    )
    assert result.calculation_status == "conflict_requires_review"
    assert result.estimated_remaining_liability_low == Decimal("3900.00")
    assert result.estimated_remaining_liability_high == Decimal("4000.00")
    assert result.range_completeness == "partial"
    assert result.indeterminable_effect is True


def test_authoritative_projectors_ignore_combined_class_dispatch_attacks():
    project_evidence = project_paye_evidence
    project_conflict = project_paye_conflict
    project_policy = project_paye_reconciliation_policy
    project_result = project_paye_reconciliation
    captured_reconcile = reconcile_paye
    item = ev(EvidenceKind.HMRC, "2000", employment="job-a", evidence_id="genuine")
    result = reconcile("6000", (item,), tax_year="2026-27", as_of=TODAY)
    conflict_result = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", evidence_id="a"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="b"),
        ),
        tax_year="2026-27",
        as_of=TODAY,
    )
    conflict = conflict_result.conflicts[0]

    def assert_detached_immutable(value):
        if type(value) is tuple:
            for item_value in value:
                assert_detached_immutable(item_value)
            return
        assert type(value) in {type(None), str, int, bool, Decimal, date}

    for projected in (
        project_evidence(item), project_conflict(conflict), project_policy(POLICY),
        project_result(result), project_result(conflict_result),
    ):
        assert_detached_immutable(projected)
        assert copy.copy(projected) is projected
        assert copy.deepcopy(projected) == projected

    attacked = (
        (PayeReconciliation, "tax_year", "forged"),
        (PayeEvidence, "evidence_id", "forged"),
        (type(conflict), "field", "forged"),
        (PayeReconciliationPolicy, "stale_after_days", 0),
    )
    originals = tuple(
        (
            cls,
            field,
            cls.__dict__["__getattribute__"],
            cls.__dict__[field],
        )
        for cls, field, _ in attacked
    )
    try:
        for cls, field, forged in attacked:
            type.__setattr__(cls, "__getattribute__", object.__getattribute__)
            type.__setattr__(cls, field, property(lambda value, forged=forged: forged))

        # Convenience attribute dispatch is deliberately non-authoritative.
        assert result.tax_year == "forged"
        assert item.evidence_id == "forged"
        assert conflict.field == "forged"
        assert POLICY.stale_after_days == 0

        assert dict(project_evidence(item))["evidence_id"] == "genuine"
        assert dict(project_conflict(conflict))["field"] == "tax_paid_to_date"
        assert dict(project_policy(POLICY)) == {
            "stale_after_days": 45,
            "conflict_tolerance": Decimal("1.00"),
        }
        safe_result = dict(project_result(result))
        assert safe_result["tax_year"] == "2026-27"
        assert dict(safe_result["selected_evidence"][0])["evidence_id"] == "genuine"
        safe_conflict_result = dict(project_result(conflict_result))
        assert dict(safe_conflict_result["conflicts"][0])["field"] == "tax_paid_to_date"
        assert dict(safe_conflict_result["considered_evidence"][0])["evidence_id"] == "a"

        rerun = captured_reconcile(
            "6000", (item,), tax_year="2026-27", as_of=TODAY, policy=POLICY
        )
        assert dict(project_result(rerun))["tax_paid_to_date"] == Decimal("2000.00")
    finally:
        for cls, field, getattribute, descriptor in originals:
            type.__setattr__(cls, "__getattribute__", getattribute)
            type.__setattr__(cls, field, descriptor)


def test_projectors_fail_closed_after_low_level_registered_slot_mutation():
    item = ev(EvidenceKind.HMRC, "2000", employment="job-a", evidence_id="genuine")
    policy = make_paye_reconciliation_policy(45, Decimal("1.00"))
    result = reconcile("6000", (item,), tax_year="2026-27", as_of=TODAY)
    object.__setattr__(item, "evidence_id", "mutated")
    object.__setattr__(policy, "stale_after_days", 46)
    with pytest.raises(ValueError, match="integrity"):
        project_paye_evidence(item)
    with pytest.raises(ValueError, match="integrity"):
        project_paye_reconciliation_policy(policy)
    with pytest.raises(ValueError, match="integrity"):
        project_paye_reconciliation(result)


def test_evidence_integrity_is_revalidated_through_issued_result():
    item = ev(EvidenceKind.HMRC, "2000", employment="job-a")
    result = reconcile("6000", (item,), tax_year="2026-27", as_of=TODAY)
    object.__setattr__(item, "tax_paid_to_date", Decimal("3000.00"))
    with pytest.raises(ValueError, match="integrity"):
        reconcile("6000", (item,), tax_year="2026-27", as_of=TODAY)
    with pytest.raises(ValueError, match="integrity"):
        _ = result.tax_paid_to_date


def test_module_helper_class_and_primitive_rebinding_cannot_promote_state(monkeypatch):
    captured = reconcile_paye
    item = ev(EvidenceKind.HMRC, "2000", employment="job-a")
    expected = captured(
        "6000", (item,), tax_year="2026-27", as_of=TODAY, policy=POLICY
    ).tax_paid_to_date
    for name, replacement in {
        "PayeEvidence": object,
        "PayeReconciliation": object,
        "PayeReconciliationPolicy": object,
        "EvidenceKind": object,
        "EvidenceRepresentation": object,
        "Completeness": object,
        "Confidence": object,
        "Decimal": object,
        "date": object,
        "type": lambda value: object,
        "tuple": object,
        "len": lambda value: 0,
        "all": lambda values: False,
        "any": lambda values: True,
        "sum": lambda values, start=None: Decimal("999.00"),
        "min": lambda *args, **kwargs: None,
        "max": lambda *args, **kwargs: None,
        "abs": lambda value: Decimal("0.00"),
        "reconcile_paye": lambda *args, **kwargs: object(),
    }.items():
        monkeypatch.setattr(module, name, replacement, raising=False)
    assert captured(
        "6000", (item,), tax_year="2026-27", as_of=TODAY, policy=POLICY
    ).tax_paid_to_date == expected
    with pytest.raises(TypeError):
        setattr(PayeReconciliation, "tax_paid_to_date", property(lambda value: Decimal("0")))


def test_all_six_independently_reviewed_paye_propositions_remain_exact():
    two_jobs = reconcile(
        "10000",
        (
            ev(EvidenceKind.HMRC, "1800", employment="job-a", evidence_id="job-a"),
            ev(EvidenceKind.HMRC, "700", employment="job-b", evidence_id="job-b"),
        ),
        tax_year="2026-27", as_of=TODAY,
    )
    assert (two_jobs.tax_paid_to_date, two_jobs.estimated_remaining_liability) == (
        Decimal("2500.00"), Decimal("7500.00")
    )

    aggregate = reconcile(
        "6000",
        (
            ev(EvidenceKind.DOCUMENT, "2000", evidence_id="aggregate",
               covered_employments=("job-a", "job-b")),
            ev(EvidenceKind.HMRC, "1200", employment="job-a", evidence_id="job-a"),
            ev(EvidenceKind.HMRC, "800", employment="job-b", evidence_id="job-b"),
        ),
        tax_year="2026-27", as_of=TODAY,
    )
    assert aggregate.tax_paid_to_date == Decimal("2000.00")
    assert aggregate.selected_evidence_ids == ("aggregate",)

    conflict = reconcile(
        "6000",
        (
            ev(EvidenceKind.HMRC, "2100", employment="job-a", evidence_id="hmrc"),
            ev(EvidenceKind.DOCUMENT, "2000", employment="job-a", evidence_id="doc"),
        ),
        tax_year="2026-27", as_of=TODAY,
    )
    assert conflict.calculation_status == "conflict_requires_review"
    assert (conflict.estimated_remaining_liability_low,
            conflict.estimated_remaining_liability_high) == (
        Decimal("3900.00"), Decimal("4000.00")
    )

    missing = reconcile("6000", (), tax_year="2026-27", as_of=TODAY)
    assert missing.tax_paid_to_date is None
    assert missing.conservative_assumed_tax_paid == Decimal("0.00")

    excess = reconcile(
        "1000", (ev(EvidenceKind.HMRC, "1200", employment="job-a"),),
        tax_year="2026-27", as_of=TODAY,
    )
    assert excess.estimated_remaining_liability == Decimal("0.00")
    assert excess.apparent_overpayment == Decimal("200.00")
    assert any("not a confirmed or available refund" in item for item in excess.warnings)

    stale = reconcile(
        "6000",
        (ev(EvidenceKind.HMRC, "2000", employment="job-a", days_old=72),),
        tax_year="2026-27", as_of=TODAY,
    )
    assert stale.tax_paid_to_date == Decimal("2000.00")
    assert stale.estimated_remaining_liability == Decimal("4000.00")
    assert stale.calculation_status == "calculated_with_material_uncertainty"
    assert stale.range_completeness == "partial"
    assert stale.indeterminable_effect is True
