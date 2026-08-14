"""Synthetic contract tests for estimate uncertainty preservation."""

from decimal import Decimal

import pytest

from reserved.evidence_uncertainty import (
    EffectKind,
    CalculationStatus,
    EvidenceCompleteness,
    EvidenceRepresentation,
    EvidenceSelection,
    EstimateEnvelope,
    EstimateEvidenceItem,
    EstimatePurpose,
    EstimateEffect,
    EstimateEvidenceAssessment,
    EstimateUncertainty,
    PurposeFitness,
    UncertaintyReason,
    amount,
)


def test_known_conflict_preserves_provenance_and_determinable_range():
    issue = EstimateUncertainty(
        issue_id="PAYE-CONFLICT-1",
        reason=UncertaintyReason.CONFLICTING,
        affected_input="paye_tax_deducted",
        evidence_references=("E-HMRC-OLD", "E-PAYSLIP-CURRENT"),
        explanation="Cumulative observations differ by £100.",
        effect=EstimateEffect(EffectKind.RANGE, low=amount("3900"), high=amount("4000")),
    )
    assessment = EstimateEvidenceAssessment("2026-08-12", (issue,))
    assert assessment.has_known_uncertainty
    assert not assessment.has_indeterminable_effect
    assert issue.evidence_references == ("E-HMRC-OLD", "E-PAYSLIP-CURRENT")


def test_possible_omission_does_not_invent_a_numeric_range():
    issue = EstimateUncertainty(
        issue_id="INCOME-OMISSION-1",
        reason=UncertaintyReason.POSSIBLY_OMITTED,
        affected_input="foreign_property_income",
        evidence_references=(),
        explanation="No completeness evidence establishes whether this source exists.",
        effect=EstimateEffect(EffectKind.NOT_DETERMINABLE),
    )
    assessment = EstimateEvidenceAssessment("2026-08-12", (issue,))
    assert assessment.has_indeterminable_effect


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-1", "not-money"])
def test_effect_amount_rejects_false_precision_and_invalid_values(bad):
    with pytest.raises(ValueError):
        amount(bad)


def test_effect_shape_cannot_mix_range_and_point_or_reverse_bounds():
    with pytest.raises(ValueError):
        EstimateEffect(EffectKind.RANGE, low=Decimal("2"), high=Decimal("1"))
    with pytest.raises(ValueError):
        EstimateEffect(EffectKind.POINT_EFFECT, amount=Decimal("1"), low=Decimal("0"))


def test_assessment_can_be_fit_for_a_stated_purpose_without_claiming_certainty():
    issue = EstimateUncertainty(
        issue_id="PAYE-STALE-1",
        reason=UncertaintyReason.STALE,
        affected_input="paye_tax_deducted",
        evidence_references=("E-PAYE-1",),
        explanation="Evidence may not include the most recent payroll period.",
        effect=EstimateEffect(EffectKind.NOT_DETERMINABLE),
    )
    assessment = EstimateEvidenceAssessment(
        "2026-08-12", (issue,),
        purpose=EstimatePurpose.PERSONALISED_ESTIMATE,
        fitness=PurposeFitness.ADEQUATE_WITH_MATERIAL_UNCERTAINTY,
        rationale="Useful for an explicitly qualified projection; not adequate for filing.",
    )
    assert assessment.fitness is PurposeFitness.ADEQUATE_WITH_MATERIAL_UNCERTAINTY
    assert assessment.has_indeterminable_effect


def test_unqualified_adequate_status_cannot_hide_known_uncertainty():
    issue = EstimateUncertainty(
        "U1", UncertaintyReason.MISSING, "income", (), "Income is missing.",
        EstimateEffect(EffectKind.NOT_DETERMINABLE),
    )
    with pytest.raises(ValueError):
        EstimateEvidenceAssessment(
            "2026-08-12", (issue,), EstimatePurpose.PERSONALISED_ESTIMATE,
            PurposeFitness.ADEQUATE, "Incorrectly suppresses known uncertainty.",
        )


def test_versioned_envelope_preserves_evidence_scope_uncertainty_and_restriction():
    evidence = EstimateEvidenceItem(
        "E-1", "document", "opaque-ref", "employment-a", "2026-27",
        "year-to-date through 2026-08-11", "2026-08-11T12:00:00+00:00",
        EvidenceRepresentation.YEAR_TO_DATE, EvidenceCompleteness.COMPLETE_FOR_PURPOSE,
        "current", EvidenceSelection.SELECTED, "most recent complete representation",
        "2000.00", "GBP",
    )
    uncertainty = EstimateUncertainty(
        "U-1", UncertaintyReason.POSSIBLY_OMITTED, "other_income", (),
        "Other income cannot be ruled out.", EstimateEffect(EffectKind.NOT_DETERMINABLE),
        known=False, affected_components=("income_tax",), customer_action="Review income sources.",
    )
    envelope = EstimateEnvelope(
        "1.0", "EST-1", "2026-08-13T12:00:00+00:00", "2026-27", "engine-3.0.0",
        EstimatePurpose.RESERVE_GUIDANCE, PurposeFitness.ADEQUATE_WITH_MATERIAL_UNCERTAINTY,
        CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY, Decimal("4000"), None, None, None,
        ("income_tax",), ("foreign_tax_credit_relief",), (evidence,), (uncertainty,),
        "evidence-policy-2026-08-13", ("FTCR-out-of-scope",),
        ("not_for_filing", "not_a_confirmed_payment_amount"),
    )
    assert envelope.evidence[0].selection is EvidenceSelection.SELECTED
    assert envelope.unsupported_families == ("foreign_tax_credit_relief",)


def test_higher_consequence_restricted_output_cannot_omit_prohibited_uses():
    with pytest.raises(ValueError):
        EstimateEnvelope(
            "1.0", "EST-2", "2026-08-13T12:00:00+00:00", "2026-27", "rules",
            EstimatePurpose.RECONCILIATION, PurposeFitness.INADEQUATE,
            CalculationStatus.INSUFFICIENT_FACTS, None, None, None, None,
            (), (), (), (), "policy-pending", (), (),
        )
