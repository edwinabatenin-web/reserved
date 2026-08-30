"""Tests for the purpose-aware HICBC annual-position integration boundary.

Verifies that an ambiguous, uncertain or insufficient HICBC result can never be
promoted into an actionable total/reserve/payment figure, that payment is never
actionable, and that the informational tier shows only qualified values.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from reserved.engines.hicbc_partner import (
    ANI_COMPONENT_WHOLE,
    CLAIMANT_PERSON,
    PartnerEvidence,
    determine_hicbc_responsibility,
)
from reserved.engines.hicbc_integration import (
    INFORMATIONAL,
    PAYMENT,
    PERSONALISED_ESTIMATE,
    RESERVE_GUIDANCE,
    integrate_hicbc,
)

TAX_YEAR = "2026/27"
TS = "2026-08-17T10:00:00+00:00"
CHILD_BENEFIT = Decimal("1406.60")


def _evidence(point=None, low=None, high=None, *, completeness="complete_for_purpose",
              recency="current", ani_components=(ANI_COMPONENT_WHOLE,)) -> PartnerEvidence:
    common = dict(
        evidence_id="e1",
        source_kind="manual",
        source_reference="ref",
        subject_reference="partner",
        tax_year=TAX_YEAR,
        effective_period=TAX_YEAR,
        observed_at=TS,
        confirmed_at=None,
        completeness=completeness,
        recency_state=recency,
        consent_state="not_required",
        ani_components=ani_components,
    )
    if point is not None:
        return PartnerEvidence(representation="point", point=Decimal(point), low=None, high=None, **common)
    return PartnerEvidence(representation="range", point=None, low=Decimal(low), high=Decimal(high), **common)


def _result(user_ani, partner_evidence=None, has_partner=True, claimant=CLAIMANT_PERSON):
    return determine_hicbc_responsibility(
        user_ani=user_ani,
        child_benefit_amount=CHILD_BENEFIT,
        has_relevant_partner=has_partner,
        claimant=claimant,
        partner_evidence=partner_evidence,
        tax_year=TAX_YEAR,
    )


def test_determinate_result_enters_total_and_reserve_but_not_payment():
    result = _result(70000, _evidence(point="50000"))
    info = integrate_hicbc(result, INFORMATIONAL)
    total = integrate_hicbc(result, PERSONALISED_ESTIMATE)
    reserve = integrate_hicbc(result, RESERVE_GUIDANCE)
    payment = integrate_hicbc(result, PAYMENT)

    assert info.included and info.charge == Decimal("703.00")
    assert total.included and total.charge == Decimal("703.00") and not total.actionable
    assert reserve.included and reserve.charge == Decimal("703.00") and reserve.actionable
    assert not payment.included and not payment.actionable


def test_ambiguous_result_excluded_from_all_actionable_purposes():
    # An overlapping partner ANI range remains genuinely ambiguous.
    result = _result(70000, _evidence(low="65000", high="75000"))
    assert result.responsibility_status == "ambiguous"

    info = integrate_hicbc(result, INFORMATIONAL)
    assert info.included and info.adequacy == "bounded" and info.charge is None

    for purpose in (PERSONALISED_ESTIMATE, RESERVE_GUIDANCE, PAYMENT):
        contribution = integrate_hicbc(result, purpose)
        assert not contribution.included
        assert not contribution.actionable
        assert contribution.charge is None


def test_insufficient_facts_excluded_everywhere():
    result = _result(70000, has_partner=None)
    assert result.calculation_status == "insufficient_facts"

    info = integrate_hicbc(result, INFORMATIONAL)
    assert not info.included

    for purpose in (PERSONALISED_ESTIMATE, RESERVE_GUIDANCE, PAYMENT):
        contribution = integrate_hicbc(result, purpose)
        assert not contribution.included and contribution.charge is None


def test_payment_never_actionable_even_when_determinate():
    result = _result(70000, _evidence(point="50000"))
    payment = integrate_hicbc(result, PAYMENT)
    assert payment.included is False
    assert payment.actionable is False
    assert "not independently approved" in payment.reason


def test_unknown_purpose_rejected():
    result = _result(70000, _evidence(point="50000"))
    with pytest.raises(ValueError):
        integrate_hicbc(result, "customer_presentation")


def test_no_charge_result_enters_total_as_zero():
    result = _result(40000)  # below threshold => no charge
    total = integrate_hicbc(result, PERSONALISED_ESTIMATE)
    assert total.included and total.charge == Decimal("0")


def test_material_uncertainty_informational_is_bounded_not_exact():
    # R2: a materially uncertain (NOT_DETERMINABLE) result must not surface an
    # exact charge or identical low/high bounds in the informational tier.
    result = _result(70000, _evidence(point="50000", completeness="partial", recency="unconfirmed"))
    assert result.calculation_status == "calculated_with_material_uncertainty"
    info = integrate_hicbc(result, INFORMATIONAL)
    assert info.included
    assert info.charge is None
    assert info.charge_low == Decimal("0")
    assert info.charge_high == Decimal("703.00")
    assert info.charge_low != info.charge_high


def test_material_uncertainty_partner_higher_is_not_zero_zero():
    # R2: a materially uncertain partner-higher indication must not become an
    # exact £0–£0 informational result.
    result = _result(70000, _evidence(point="90000", completeness="partial", recency="unconfirmed"))
    info = integrate_hicbc(result, INFORMATIONAL)
    assert info.charge is None
    assert info.charge_low == Decimal("0")
    assert info.charge_high == Decimal("703.00")
    assert not (info.charge == info.charge_low == info.charge_high == Decimal("0"))
