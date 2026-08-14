"""Lossless WP9 component emission into the adopted WP7U envelope vocabulary.

One envelope is emitted per loan component; monetary components are never
combined. This adapter does not recalculate, persist or expose results.
"""

from datetime import datetime
from decimal import Decimal

from reserved.evidence_uncertainty import (
    CalculationStatus, EffectKind, EvidenceCompleteness, EvidenceRepresentation,
    EvidenceSelection, EstimateEffect, EstimateEnvelope, EstimateEvidenceItem,
    EstimatePurpose, EstimateUncertainty, PurposeFitness, UncertaintyReason,
)
from .annual_loan_reconciliation import AnnualLoanReconciliation, LoanEvidenceDecision


POLICY_VERSION = "evidence-policy/2026-08-13"
PROHIBITED = ("customer_combined_balance", "reserve_guidance", "filing", "payment", "refund")


def _selection(decision: LoanEvidenceDecision) -> EvidenceSelection:
    if decision.decision == "selected":
        return EvidenceSelection.SELECTED
    if decision.decision == "superseded":
        return EvidenceSelection.SUPERSEDED
    if decision.decision == "conflict":
        return EvidenceSelection.UNRESOLVED_CONFLICT
    if decision.reason == "outside_tax_year_as_of_or_coherent_timeline":
        return EvidenceSelection.OUTSIDE_PERIOD
    return EvidenceSelection.INCOMPATIBLE_REPRESENTATION


def _evidence(decision: LoanEvidenceDecision, tax_year: str, as_of, stale_after_days: int) -> EstimateEvidenceItem:
    stale = as_of is not None and (as_of - decision.effective_through).days > stale_after_days
    return EstimateEvidenceItem(
        decision.evidence_id, decision.source_kind, decision.source_reference,
        decision.employment_id, tax_year,
        f"cumulative through {decision.effective_through.isoformat()}",
        f"{decision.observed_on.isoformat()}T00:00:00+00:00",
        EvidenceRepresentation.YEAR_TO_DATE,
        EvidenceCompleteness.COMPLETE_FOR_PURPOSE if decision.complete_for_representation else EvidenceCompleteness.PARTIAL,
        "stale" if stale else "current_as_of_declared_date", _selection(decision),
        decision.reason, str(decision.original_amount), "GBP",
    )


def _basis_evidence(result: AnnualLoanReconciliation) -> tuple[EstimateEvidenceItem, ...]:
    return tuple(EstimateEvidenceItem(
        item.evidence_id, item.source_kind, item.source_reference, item.subject_reference,
        result.tax_year, item.effective_period, f"{item.observed_on.isoformat()}T00:00:00+00:00",
        EvidenceRepresentation.ANNUAL_FINAL,
        EvidenceCompleteness.COMPLETE_FOR_PURPOSE if item.complete_for_basis else EvidenceCompleteness.PARTIAL,
        "current_as_of_declared_date", EvidenceSelection.SELECTED,
        "selected_as_declared_annual_loan_income_basis_evidence", None, None,
    ) for item in result.basis_evidence)


def _unsupported_plan_evidence(result: AnnualLoanReconciliation) -> tuple[EstimateEvidenceItem, ...]:
    """Preserve declared plan inputs without treating them as calculation evidence."""
    if result.as_of is None:
        raise ValueError("Unsupported plan input provenance requires the producer as_of date")
    return tuple(EstimateEvidenceItem(
        f"student-loan-plan-input:{index}", "declared_input", "internal://student-loan-plans",
        "annual-self-assessment-plan-input", result.tax_year, result.tax_year,
        f"{result.as_of.isoformat()}T00:00:00+00:00",
        EvidenceRepresentation.MANUAL_ASSERTION, EvidenceCompleteness.COMPLETE_FOR_PURPOSE,
        "current_as_of_declared_date", EvidenceSelection.INCOMPATIBLE_REPRESENTATION,
        "retained_as_unsupported_declared_plan_input", plan, None,
    ) for index, plan in enumerate(result.unsupported_plans))


def _unsupported_families(result: AnnualLoanReconciliation) -> tuple[str, ...]:
    for family in (
        "mixed_known_and_unknown_student_loan_plans",
        "unknown_student_loan_plan",
        "simultaneous_multiple_undergraduate_plans",
        "unsupported_undergraduate_plan",
    ):
        if family in result.limitations:
            return (family,)
    return ("unsupported_student_loan_plan_treatment",)


def _uncertainties(item) -> tuple[EstimateUncertainty, ...]:
    issues = []
    refs = item.retained_evidence_ids
    if item.calculation_status == "insufficient_facts":
        issues.append(EstimateUncertainty(
            f"{item.component.value}-missing", UncertaintyReason.MISSING,
            "payroll_loan_deductions", refs,
            "Complete direct deduction evidence is missing for the declared employment scope.",
            EstimateEffect(EffectKind.NOT_DETERMINABLE), affected_components=(item.component.value,),
        ))
    if item.conflict_difference is not None:
        issues.append(EstimateUncertainty(
            f"{item.component.value}-conflict", UncertaintyReason.CONFLICTING,
            "payroll_loan_deductions", refs,
            "Same-period cumulative deduction evidence conflicts.",
            EstimateEffect(EffectKind.RANGE, low=item.remaining_amount_low, high=item.remaining_amount_high),
            affected_components=(item.component.value,),
        ))
    if item.stale_reconciliation_effect is not None:
        issues.append(EstimateUncertainty(
            f"{item.component.value}-stale", UncertaintyReason.STALE,
            "payroll_loan_deductions", item.selected_evidence_ids,
            "Selected cumulative evidence may omit later-period deductions.",
            EstimateEffect(EffectKind.POINT_EFFECT, amount=item.stale_reconciliation_effect),
            affected_components=(item.component.value,),
        ))
    if item.apparent_excess_deductions is not None:
        issues.append(EstimateUncertainty(
            f"{item.component.value}-excess", UncertaintyReason.ASSUMPTION,
            "apparent_excess_deductions", item.selected_evidence_ids,
            "The apparent excess is not a confirmed or available refund.",
            EstimateEffect(EffectKind.POINT_EFFECT, amount=item.apparent_excess_deductions),
            affected_components=(item.component.value,),
        ))
    return tuple(issues)


def _status(value: str) -> CalculationStatus:
    return {
        "calculated": CalculationStatus.CALCULATED,
        "calculated_with_material_uncertainty": CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY,
        "insufficient_facts": CalculationStatus.INSUFFICIENT_FACTS,
        "conflict_requires_review": CalculationStatus.CONFLICT_REQUIRES_REVIEW,
    }[value]


def emit_annual_loan_wp7u_envelopes(
    result: AnnualLoanReconciliation,
    *,
    emission_id: str,
    calculated_at: str,
) -> tuple[EstimateEnvelope, ...]:
    """Emit component envelopes without inventing a combined loan balance."""
    try:
        datetime.fromisoformat(calculated_at.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("calculated_at must be ISO-8601") from None
    if not emission_id:
        raise ValueError("emission_id is required")
    if result.calculation_status == "unsupported_plan_combination":
        plan_evidence = _unsupported_plan_evidence(result)
        evidence = _basis_evidence(result) + plan_evidence
        evidence_refs = result.basis_evidence_ids + tuple(item.evidence_id for item in plan_evidence)
        return (EstimateEnvelope(
            "reserved-estimate-envelope/1.0", f"{emission_id}:unsupported-plans", calculated_at,
            result.tax_year, result.ruleset_version, EstimatePurpose.UNSUPPORTED_FOR_DECISION,
            PurposeFitness.INADEQUATE, CalculationStatus.UNSUPPORTED_RULE,
            None, None, None, None, (), _unsupported_families(result),
            evidence, (EstimateUncertainty(
                "unsupported-plan-combination", UncertaintyReason.ASSUMPTION,
                "student_loan_plans", evidence_refs,
                "Annual plan-selection treatment is outside approved scope and requires verification with HMRC or a qualified tax adviser before any monetary use.",
                EstimateEffect(EffectKind.NOT_DETERMINABLE), affected_components=("student_loans",),
                customer_action="Verify the applicable annual Self Assessment plan treatment with HMRC or a qualified tax adviser.",
            ),), POLICY_VERSION, result.limitations + (
                "verification_required_before_student_loan_or_total_amount",
            ), PROHIBITED,
        ),)
    if not result.components:
        reason = "no_supported_plan_supplied" if "no_supported_plan_supplied" in result.limitations else "annual_loan_income_basis_not_fully_evidenced"
        return (EstimateEnvelope(
            "reserved-estimate-envelope/1.0", f"{emission_id}:root-failure", calculated_at,
            result.tax_year, result.ruleset_version, EstimatePurpose.RECONCILIATION,
            PurposeFitness.INADEQUATE, CalculationStatus.INSUFFICIENT_FACTS,
            None, None, None, None, (), (), _basis_evidence(result),
            (EstimateUncertainty(
                "annual-loan-root-failure", UncertaintyReason.MISSING,
                "student_loan_plan" if reason == "no_supported_plan_supplied" else "annual_loan_income_basis",
                result.basis_evidence_ids, reason.replace("_", " "),
                EstimateEffect(EffectKind.NOT_DETERMINABLE), affected_components=("student_loans",),
            ),), POLICY_VERSION, result.limitations, PROHIBITED,
        ),)
    envelopes = []
    for item in result.components:
        issues = _uncertainties(item)
        status = _status(item.calculation_status)
        if status is CalculationStatus.CALCULATED:
            fitness = PurposeFitness.ADEQUATE
        elif status is CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY:
            fitness = PurposeFitness.ADEQUATE_WITH_MATERIAL_UNCERTAINTY
        else:
            fitness = PurposeFitness.INADEQUATE
        envelopes.append(EstimateEnvelope(
            "reserved-estimate-envelope/1.0", f"{emission_id}:{item.component.value}", calculated_at,
            result.tax_year, result.ruleset_version, EstimatePurpose.RECONCILIATION, fitness, status,
            item.remaining_self_assessment_amount if status in {
                CalculationStatus.CALCULATED, CalculationStatus.CALCULATED_WITH_MATERIAL_UNCERTAINTY
            } else None,
            item.remaining_amount_low, item.remaining_amount_high,
            (
                "candidate residuals from " + ", ".join(
                    f"{decision.evidence_id}={decision.original_amount}"
                    for decision in item.evidence_decisions if decision.decision == "conflict"
                )
            ) if item.remaining_amount_low is not None else None,
            (item.component.value,), (),
            _basis_evidence(result) + tuple(
                _evidence(decision, result.tax_year, result.as_of, result.stale_after_days)
                for decision in item.evidence_decisions
            ),
            issues, POLICY_VERSION,
            result.limitations + item.uncertainties + item.selection_reasons + (
                (f"range_completeness:{item.range_completeness}",) if item.range_completeness else ()
            ),
            PROHIBITED,
        ))
    return tuple(envelopes)
