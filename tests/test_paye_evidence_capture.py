"""Independently derived synthetic tests for the structured PAYE boundary."""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal

import pytest

from reserved.engines.paye_evidence_capture import (
    CaptureSource,
    PayFrequency,
    PayeEvidenceCapture,
    PensionTreatment,
    SourceDocumentType,
    normalise_paye_evidence,
)
from reserved.engines.paye_reconciliation import (
    Completeness,
    Confidence,
    EvidenceKind,
    EvidenceRepresentation,
    make_paye_reconciliation_policy,
    reconcile_paye,
)


AS_OF = date(2026, 8, 20)
POLICY = make_paye_reconciliation_policy(45, Decimal("1.00"))


def reconcile(liability, evidence, **kwargs):
    return reconcile_paye(liability, tuple(evidence), policy=POLICY, **kwargs)


def capture(**changes):
    values = dict(
        source=CaptureSource.SOURCE_DOCUMENT,
        document_type=SourceDocumentType.PAYSLIP,
        evidence_id="evidence-101",
        tax_year="2026-27",
        employment_id="employment-A",
        gross_pay_to_date="12345.67",
        tax_paid_to_date="2345.60",
        tax_code="1257L",
        pay_frequency=PayFrequency.MONTHLY,
        pension_treatment=PensionTreatment.UNKNOWN,
        effective_through=date(2026, 8, 18),
        observed_on=AS_OF,
    )
    values.update(changes)
    return PayeEvidenceCapture(**values)


@pytest.mark.parametrize("document_type", list(SourceDocumentType))
def test_supported_documents_map_to_document(document_type):
    item = normalise_paye_evidence(capture(document_type=document_type))
    assert item.kind is EvidenceKind.DOCUMENT
    assert item.source_reference == f"customer_confirmed:{document_type.value}"


def test_manual_maps_to_manual_and_rejects_document_shape():
    item = normalise_paye_evidence(capture(source=CaptureSource.MANUAL, document_type=None))
    assert item.kind is EvidenceKind.MANUAL
    assert item.source_reference == "customer_confirmed:structured_manual"
    with pytest.raises(ValueError, match="only valid"):
        capture(source=CaptureSource.MANUAL)
    with pytest.raises(TypeError, match="document_type"):
        capture(document_type=None)


def test_missing_and_exact_zero_remain_distinct():
    missing = capture(gross_pay_to_date=None, tax_paid_to_date=None)
    zero = capture(gross_pay_to_date=0, tax_paid_to_date="0.00")
    assert normalise_paye_evidence(missing).tax_paid_to_date is None
    assert normalise_paye_evidence(zero).tax_paid_to_date == Decimal("0.00")
    assert missing != zero


@pytest.mark.parametrize("value, expected", [
    (0, Decimal("0.00")), (42, Decimal("42.00")),
    ("7", Decimal("7.00")), ("7.5", Decimal("7.50")),
    (Decimal("7.50"), Decimal("7.50")),
])
def test_exact_amounts_are_normalised(value, expected):
    assert capture(tax_paid_to_date=value).tax_paid_to_date == expected


@pytest.mark.parametrize("value", [
    True, False, 1.2, float("nan"), float("inf"), Decimal("NaN"),
    Decimal("Infinity"), Decimal("-0"), -1, "-1", " 1", "1 ", "+1", "1,000", "1e3",
    "", "01", "1.234", Decimal("1.001"),
])
def test_unsafe_or_ambiguous_amounts_fail_closed(value):
    with pytest.raises((TypeError, ValueError)):
        capture(tax_paid_to_date=value)


@pytest.mark.parametrize("field", ["evidence_id", "employment_id"])
@pytest.mark.parametrize("value", ["", " ", "has spaces", 123, True, None])
def test_identifiers_reject_blank_or_wrong_runtime_types(field, value):
    with pytest.raises((TypeError, ValueError)):
        capture(**{field: value})


@pytest.mark.parametrize("field,value", [
    ("source", "source_document"),
    ("document_type", "payslip"),
    ("pay_frequency", "monthly"),
    ("pension_treatment", "unknown"),
])
def test_enums_require_exact_runtime_types(field, value):
    with pytest.raises(TypeError):
        capture(**{field: value})


@pytest.mark.parametrize("tax_code", [
    " 1257L", "1257L ", "\t1257L", "1257L\t", "\n1257L", "1257L\n",
])
def test_tax_code_rejects_leading_or_trailing_whitespace(tax_code):
    with pytest.raises(ValueError, match="tax_code"):
        capture(tax_code=tax_code)


def test_tax_code_preserves_existing_internal_space_form():
    assert capture(tax_code="S 1257L").tax_code == "S 1257L"


def test_tax_year_and_date_boundaries_are_explicit():
    assert capture(effective_through=date(2026, 4, 6)).effective_through == date(2026, 4, 6)
    assert capture(effective_through=date(2027, 4, 5), observed_on=date(2027, 4, 5)).effective_through == date(2027, 4, 5)
    for bad in (date(2026, 4, 5), date(2027, 4, 6)):
        with pytest.raises(ValueError, match="within tax_year"):
            capture(effective_through=bad)
    with pytest.raises(ValueError, match="immediately follow"):
        capture(tax_year="2026-28")
    with pytest.raises(ValueError, match="cannot precede"):
        capture(observed_on=date(2026, 8, 17))
    with pytest.raises(TypeError):
        capture(observed_on="2026-08-20")


def test_normalisation_is_partial_employment_cumulative_and_preserves_provenance():
    item = normalise_paye_evidence(capture())
    assert item.completeness is Completeness.PARTIAL
    assert item.representation is EvidenceRepresentation.EMPLOYMENT_CUMULATIVE
    assert item.evidence_id == "evidence-101"
    assert item.employment_id == "employment-A"
    assert item.effective_through == date(2026, 8, 18)
    assert item.observed_on == AS_OF


def test_supersession_is_a_reference_and_does_not_mutate_prior_capture():
    prior = capture(evidence_id="evidence-100")
    replacement = capture(evidence_id="evidence-101", supersedes_evidence_id="evidence-100")
    assert replacement.supersedes_evidence_id == prior.evidence_id
    assert prior.supersedes_evidence_id is None
    with pytest.raises(ValueError, match="itself"):
        capture(supersedes_evidence_id="evidence-101")


@pytest.mark.parametrize("forbidden", [
    "raw_document", "document_bytes", "document_text", "filesystem_path",
    "credentials", "nino", "bank_data", "production_id",
])
def test_forbidden_content_is_not_accepted_or_exposed(forbidden):
    with pytest.raises(TypeError):
        capture(**{forbidden: "sensitive"})
    assert not hasattr(capture(), forbidden)


def test_capture_is_immutable_equal_and_has_a_value_safe_repr():
    first = capture(tax_code="SENSITIVE-CODE")
    second = capture(tax_code="SENSITIVE-CODE")
    assert first == second
    with pytest.raises((FrozenInstanceError, AttributeError)):
        first.tax_code = "changed"
    rendered = repr(first)
    assert "SENSITIVE-CODE" not in rendered
    assert "12345.67" not in rendered


def test_normaliser_requires_validated_exact_capture_type():
    with pytest.raises(TypeError):
        normalise_paye_evidence({"evidence_id": "not-validated"})


def test_reconciliation_conflict_compatibility_without_source_precedence():
    old = normalise_paye_evidence(capture(
        source=CaptureSource.MANUAL, document_type=None, evidence_id="manual-1",
        tax_paid_to_date="2200", observed_on=date(2026, 8, 19),
    ))
    current = normalise_paye_evidence(capture(evidence_id="document-1", tax_paid_to_date="2000"))
    result = reconcile("6000", [old, current], tax_year="2026-27", as_of=AS_OF)
    assert result.calculation_status == "conflict_requires_review"
    assert result.tax_paid_to_date is None
    assert {e.evidence_id for e in result.considered_evidence} == {"manual-1", "document-1"}


def test_reconciliation_stale_and_apparent_overpayment_compatibility():
    stale = normalise_paye_evidence(capture(
        effective_through=date(2026, 6, 1), observed_on=date(2026, 6, 1),
        tax_paid_to_date="1200",
    ))
    stale_result = reconcile("4000", [stale], tax_year="2026-27", as_of=AS_OF)
    assert stale_result.confidence is Confidence.MEDIUM
    assert stale_result.indeterminable_effect is True

    excess = normalise_paye_evidence(replace(capture(), tax_paid_to_date="1200"))
    excess_result = reconcile("1000", [excess], tax_year="2026-27", as_of=AS_OF)
    assert excess_result.estimated_remaining_liability == Decimal("0.00")
    assert excess_result.apparent_overpayment == Decimal("200.00")
