"""Synthetic-only tests for PAYE reconciliation and fallback evidence."""

from datetime import date, timedelta
from decimal import Decimal

from reserved.engines.paye_reconciliation import (
    Completeness,
    Confidence,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
    reconcile_paye,
)


TODAY = date(2026, 8, 12)


def ev(kind, paid, *, employment=None, days_old=0, evidence_id=None,
       representation=None, completeness=Completeness.COMPLETE_FOR_REPRESENTATION,
       covered_employments=()):
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
        covered_employment_ids=covered_employments,
    )


def test_one_paye_employment_uses_hmrc_tax_paid():
    result = reconcile_paye("6000", [ev(EvidenceKind.HMRC, "2100", employment="job-a")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2100.00")
    assert result.estimated_remaining_liability == Decimal("3900.00")
    assert result.confidence is Confidence.HIGH


def test_multiple_employments_are_summed_without_collapsing_sources():
    result = reconcile_paye("10000", [
        ev(EvidenceKind.HMRC, "1800", employment="job-a"),
        ev(EvidenceKind.HMRC, "700", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2500.00")
    assert result.estimated_remaining_liability == Decimal("7500.00")


def test_conflict_is_retained_and_reduces_confidence():
    result = reconcile_paye("6000", [
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
    result = reconcile_paye("6000", [
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
    result = reconcile_paye("6000", [ev(EvidenceKind.DOCUMENT, "2000")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.selected_kind is EvidenceKind.DOCUMENT
    assert result.confidence is Confidence.HIGH


def test_structured_manual_entry_is_medium_confidence():
    result = reconcile_paye("6000", [ev(EvidenceKind.MANUAL, "1900")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.MEDIUM


def test_bank_inference_is_last_resort_and_low_confidence():
    result = reconcile_paye("6000", [ev(EvidenceKind.BANK_INFERENCE, "1800")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.LOW
    assert any("last-resort" in warning for warning in result.warnings)


def test_stale_hmrc_data_reduces_confidence():
    result = reconcile_paye("6000", [ev(EvidenceKind.HMRC, "1800", days_old=46)],
                            tax_year="2026-27", as_of=TODAY)
    assert result.confidence is Confidence.MEDIUM
    assert any("out of date" in warning for warning in result.warnings)


def test_no_evidence_is_explicitly_incomplete():
    result = reconcile_paye("6000", [], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date is None
    assert result.estimated_remaining_liability is None
    assert result.tax_paid_known is False
    assert result.conservative_assumed_tax_paid == Decimal("0.00")
    assert result.confidence is Confidence.INCOMPLETE


def test_aggregate_and_employment_evidence_are_not_double_counted():
    result = reconcile_paye("6000", [
        ev(EvidenceKind.DOCUMENT, "2000", evidence_id="aggregate",
           representation=EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE,
           covered_employments=("job-a", "job-b")),
        ev(EvidenceKind.HMRC, "1200", employment="job-a"),
        ev(EvidenceKind.HMRC, "800", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.tax_paid_to_date == Decimal("2000.00")
    assert any("double counting" in warning for warning in result.warnings)


def test_tax_paid_above_estimate_yields_zero_remaining_not_negative():
    result = reconcile_paye("1000", [ev(EvidenceKind.HMRC, "1200")],
                            tax_year="2026-27", as_of=TODAY)
    assert result.estimated_remaining_liability == Decimal("0.00")
    assert result.apparent_overpayment == Decimal("200.00")


def test_unlinked_equal_aggregate_and_entity_totals_fail_closed():
    result = reconcile_paye("6000", [
        ev(EvidenceKind.DOCUMENT, "2000"),
        ev(EvidenceKind.HMRC, "1200", employment="job-a"),
        ev(EvidenceKind.HMRC, "800", employment="job-b"),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.calculation_status == "insufficient_facts"
    assert result.tax_paid_known is False


def test_stale_period_reports_partial_unbounded_effect():
    result = reconcile_paye("6000", [
        ev(EvidenceKind.HMRC, "2000", employment="job-a", days_old=72),
    ], tax_year="2026-27", as_of=TODAY)
    assert result.estimated_remaining_liability == Decimal("4000.00")
    assert result.range_completeness == "partial"
    assert result.indeterminable_effect is True
