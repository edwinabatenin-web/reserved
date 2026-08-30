"""Tests for the bounded HICBC partner-responsibility engine (October v1 target).

Expected monetary values are derived directly from the current official rules and
recorded here with year, source and workings; they do not call production HICBC
helpers as an oracle.

Authority
---------
- ITEPA 2003 s.681C (whole-pound staged rounding): floor the relevant Child
  Benefit total, apply the whole complete-£200 percentage (capped at 100%), then
  floor the charge.
- Finance (No. 2) Act 2024 s.5: threshold £60,000, cap £80,000, £200 per
  percentage point (2024/25 onwards).
- HMRC PAYE14015.

Child Benefit rates (HMRC rates publications):
- 2026/27: eldest £27.05/week, additional £17.90/week, 52 weeks.
- 2025/26: eldest £26.05/week, additional £17.25/week, 52 weeks.
"""

from decimal import Decimal

import pytest

from reserved.engines.hicbc_partner import (
    ANI_COMPONENT_WHOLE,
    CLAIMANT_PARTNER,
    CLAIMANT_PERSON,
    RESPONSIBILITY_AMBIGUOUS,
    RESPONSIBILITY_INSUFFICIENT_FACTS,
    RESPONSIBILITY_NO_CHARGE,
    RESPONSIBILITY_PARTNER_LIABLE,
    RESPONSIBILITY_PERSON_LIABLE,
    HOUSEHOLD_CHANGED,
    HOUSEHOLD_MOVED_TO_PARTNER,
    HOUSEHOLD_MOVED_TO_PERSON,
    HOUSEHOLD_NOT_APPLICABLE,
    HOUSEHOLD_UNCHANGED,
    PartnerEvidence,
    SyntheticLinkedPartnerEvidenceProvider,
    annual_child_benefit_amount,
    customer_view,
    determine_hicbc_responsibility,
    household_change_status,
)


def _evidence(rep, point=None, low=None, high=None, *, completeness="complete_for_purpose",
              recency="current", consent="not_required", tax_year="2026/27",
              ani_components=(ANI_COMPONENT_WHOLE,)):
    return PartnerEvidence(
        evidence_id="ev1",
        source_kind="user_supplied_partner_estimate",
        source_reference="ref1",
        subject_reference="partner",
        tax_year=tax_year,
        representation=rep,
        point=point,
        low=low,
        high=high,
        effective_period=tax_year,
        observed_at="2026-08-17T10:00:00Z",
        confirmed_at=None,
        completeness=completeness,
        recency_state=recency,
        consent_state=consent,
        ani_components=ani_components,
    )


def _resolve(user_ani, cb, partner, evidence=None, tax_year="2026/27", previous=None,
             claimant=CLAIMANT_PERSON):
    return determine_hicbc_responsibility(
        user_ani=user_ani,
        child_benefit_amount=cb,
        has_relevant_partner=partner,
        claimant=claimant,
        partner_evidence=evidence,
        tax_year=tax_year,
        previous_responsibility_status=previous,
    )


CB_1 = Decimal("1406.60")  # 2026/27 one child: 27.05 * 52


# ── Staged-rounding arithmetic (independent authority) ───────────────────────

@pytest.mark.parametrize(
    "ani,expected",
    [
        ("60001", "0"),      # 1p above — no complete £200 step
        ("60199", "0"),      # still no complete step
        ("60200", "14.00"),  # 1 complete step → 1% of floor(1406.60)=1406 → 14.06 → 14
        ("70000", "703.00"),  # 50% → 703
        ("79800", "1391.00"),  # 99% → 1391.94 → 1391 (the non-coincidental case)
        ("80000", "1406.00"),  # 100% cap
        ("80200", "1406.00"),  # above cap — still 100%
    ],
)
def test_person_liable_staged_rounding(ani, expected):
    result = _resolve(ani, CB_1, False)
    assert result.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert result.projected_user_hicbc == Decimal(expected)
    assert result.calculation_status == "calculated"


def test_at_threshold_no_charge_strict_inequality():
    # At exactly £60,000 the charge formula returns nil — strict "above" applies.
    result = _resolve("60000", CB_1, False)
    assert result.responsibility_status == RESPONSIBILITY_NO_CHARGE
    assert result.projected_user_hicbc == Decimal("0")


def test_two_children_2026_27_midpoint():
    # (27.05 + 17.90) * 52 = 2337.40 → floor 2337 → 50% = 1168.50 → 1168
    result = _resolve("70000", "2337.40", False)
    assert result.projected_user_hicbc == Decimal("1168.00")


def test_one_child_2025_26_midpoint():
    # 2025/26 eldest 26.05 * 52 = 1354.60 → floor 1354 → 50% = 677
    result = _resolve("70000", "1354.60", False, tax_year="2025/26")
    assert result.projected_user_hicbc == Decimal("677.00")


# ── Responsibility status cases ───────────────────────────────────────────────

def test_neither_above_threshold_no_charge():
    r = _resolve("59000", CB_1, True, _evidence("point", point=Decimal("55000")))
    assert r.responsibility_status == RESPONSIBILITY_NO_CHARGE
    assert r.projected_user_hicbc == Decimal("0")


def test_user_above_partner_below_person_liable():
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("55000")))
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.projected_user_hicbc == Decimal("703.00")


def test_partner_above_user_below_user_not_liable():
    r = _resolve("55000", CB_1, True, _evidence("point", point=Decimal("70000")))
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")


def test_both_above_user_higher_person_liable():
    r = _resolve("79000", CB_1, True, _evidence("point", point=Decimal("70000")))
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.projected_user_hicbc == Decimal("1335.00")  # 95% of 1406 → 1335.70 → 1335


def test_both_above_partner_higher_partner_liable():
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("79000")))
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")
    assert r.hicbc_percentage is None  # partner's charge detail not computed/exposed


def test_equal_ani_user_claimant_is_person_liable():
    # ITEPA 2003 s.681B(2): condition A — the claimant's partner does not have an
    # ANI exceeding the claimant's, so equal ANIs leave the claimant liable.
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("70000")),
                 claimant=CLAIMANT_PERSON)
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.projected_user_hicbc == Decimal("703.00")
    assert r.calculation_status == "calculated"


def test_equal_ani_partner_claimant_is_partner_liable():
    # ITEPA 2003 s.681B(3): condition B requires the non-claimant's ANI to exceed
    # the claimant's, so equal ANIs leave the claimant (partner) liable.
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("70000")),
                 claimant=CLAIMANT_PARTNER)
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")
    assert r.calculation_status == "calculated"


def test_equal_ani_unknown_claimant_is_insufficient_facts():
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("70000")),
                 claimant=None)
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert r.projected_user_hicbc is None


def test_single_claimant_model_is_an_explicit_limitation():
    # The bounded v1 model supports exactly one Child Benefit claimant (person or
    # partner).  Dual-claimant households (each partner claiming for different
    # children) are not supported and are declared as an explicit limitation, so
    # they can never be silently reduced to a single invented claimant.
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("50000")),
                 claimant=CLAIMANT_PERSON)
    assert "single_child_benefit_claimant_model_dual_claims_not_supported" in r.limitations


def test_condition_b_partner_claimant_user_higher_is_person_liable():
    # ITEPA 2003 s.681B(3): where the partner is the claimant and the user's ANI
    # exceeds the partner's, the user is liable (condition B).
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("50000")),
                 claimant=CLAIMANT_PARTNER)
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.projected_user_hicbc == Decimal("703.00")


def test_condition_a_user_claimant_partner_higher_is_partner_liable():
    # ITEPA 2003 s.681B(2): where the user is the claimant and the partner's ANI
    # exceeds the user's, the user is not liable (condition A not met).
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("90000")),
                 claimant=CLAIMANT_PERSON)
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")


def test_range_entirely_below_user_person_liable():
    r = _resolve("70000", CB_1, True, _evidence("range", low=Decimal("40000"), high=Decimal("55000")))
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.projected_user_hicbc == Decimal("703.00")


def test_range_entirely_above_user_partner_liable():
    r = _resolve("70000", CB_1, True, _evidence("range", low=Decimal("75000"), high=Decimal("90000")))
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")


def test_range_overlapping_user_ambiguous_bounded():
    r = _resolve("70000", CB_1, True, _evidence("range", low=Decimal("65000"), high=Decimal("75000")))
    assert r.responsibility_status == RESPONSIBILITY_AMBIGUOUS
    assert r.projected_user_hicbc is None
    assert r.possible_charge_low == Decimal("0")
    assert r.possible_charge_high == Decimal("703.00")


def test_no_partner_person_liable():
    r = _resolve("70000", CB_1, False)
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE


def test_unknown_partner_insufficient():
    r = _resolve("70000", CB_1, None)
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert r.projected_user_hicbc is None


def test_declared_partner_missing_estimate_insufficient():
    r = _resolve("70000", CB_1, True, None)
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert r.projected_user_hicbc is None


def test_unknown_child_benefit_insufficient_not_zero():
    r = _resolve("70000", None, False)
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert r.projected_user_hicbc is None


def test_no_child_benefit_no_charge():
    r = _resolve("70000", Decimal("0"), False)
    assert r.responsibility_status == RESPONSIBILITY_NO_CHARGE
    assert r.projected_user_hicbc == Decimal("0")


# ── Evidence quality: stale / partial / revoked / unknown ────────────────────

def test_stale_partner_evidence_is_calculated_with_material_uncertainty():
    r = _resolve("70000", CB_1, True,
                 _evidence("point", point=Decimal("55000"), recency="stale"))
    assert r.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert r.calculation_status == "calculated_with_material_uncertainty"
    # Material uncertainty must not manufacture a point estimate or identical
    # bounds; the possible charge is bounded [0, full charge].
    assert r.projected_user_hicbc is None
    assert r.possible_charge_low == Decimal("0")
    assert r.possible_charge_high == Decimal("703.00")


def test_partial_partner_evidence_is_calculated_with_material_uncertainty():
    r = _resolve("70000", CB_1, True,
                 _evidence("point", point=Decimal("79000"), completeness="partial"))
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.calculation_status == "calculated_with_material_uncertainty"


def test_unknown_completeness_partner_evidence_insufficient():
    r = _resolve("70000", CB_1, True,
                 _evidence("point", point=Decimal("55000"), completeness="unknown"))
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS


def test_revoked_consent_partner_evidence_insufficient():
    r = _resolve("70000", CB_1, True,
                 _evidence("point", point=Decimal("55000"), consent="revoked"))
    assert r.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS


# ── Input validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["-1", "NaN", "Infinity", "inf"])
def test_invalid_user_ani_raises(bad):
    with pytest.raises(ValueError):
        _resolve(bad, CB_1, False)


def test_boolean_user_ani_raises():
    with pytest.raises(ValueError):
        _resolve(True, CB_1, False)


def test_range_low_above_high_raises():
    with pytest.raises(ValueError):
        _evidence("range", low=Decimal("80000"), high=Decimal("50000"))


def test_evidence_tax_year_mismatch_raises():
    with pytest.raises(ValueError):
        _resolve("70000", CB_1, True, _evidence("point", point=Decimal("55000"), tax_year="2025/26"))


# ── Household change status ───────────────────────────────────────────────────

def test_household_change_not_applicable_when_no_previous():
    assert household_change_status(None, RESPONSIBILITY_PERSON_LIABLE) == HOUSEHOLD_NOT_APPLICABLE


def test_household_change_unchanged():
    assert household_change_status(RESPONSIBILITY_PERSON_LIABLE, RESPONSIBILITY_PERSON_LIABLE) == HOUSEHOLD_UNCHANGED


def test_household_change_moved_to_partner():
    assert household_change_status(RESPONSIBILITY_PERSON_LIABLE, RESPONSIBILITY_PARTNER_LIABLE) == HOUSEHOLD_MOVED_TO_PARTNER


def test_household_change_moved_to_person():
    assert household_change_status(RESPONSIBILITY_PARTNER_LIABLE, RESPONSIBILITY_PERSON_LIABLE) == HOUSEHOLD_MOVED_TO_PERSON


def test_household_change_generic_changed():
    assert household_change_status(RESPONSIBILITY_NO_CHARGE, RESPONSIBILITY_PERSON_LIABLE) == HOUSEHOLD_CHANGED


def test_responsibility_moves_between_partners_on_ani_change():
    below = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("55000")))
    above = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("79000")))
    assert below.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert above.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert household_change_status(below.responsibility_status, above.responsibility_status) == HOUSEHOLD_MOVED_TO_PARTNER


# ── Child Benefit derivation helper ───────────────────────────────────────────

def test_annual_child_benefit_one_child_2026_27():
    assert annual_child_benefit_amount(children=1, weeks_entitled=52) == Decimal("1406.60")


def test_annual_child_benefit_two_children_2026_27():
    assert annual_child_benefit_amount(children=2, weeks_entitled=52) == Decimal("2337.40")


def test_annual_child_benefit_missing_weeks_unknown():
    # Omitted entitlement weeks remain unknown and never default to a full year.
    assert annual_child_benefit_amount(children=1) is None


def test_annual_child_benefit_override_wins():
    assert annual_child_benefit_amount(children=1, annual_override="1500.00") == Decimal("1500.00")


def test_annual_child_benefit_zero_children_unknown():
    assert annual_child_benefit_amount(children=0) is None


def test_annual_child_benefit_weeks_entitled_partial_period():
    # 2026/27 one child for 26 weeks: 27.05 * 26 = 703.30
    assert annual_child_benefit_amount(children=1, weeks_entitled=26) == Decimal("703.30")


def test_annual_child_benefit_invalid_weeks_raises():
    with pytest.raises(ValueError):
        annual_child_benefit_amount(children=1, weeks_entitled=54)


# ── Future linked-source hook ─────────────────────────────────────────────────

def test_synthetic_linked_provider_feeds_same_responsibility_logic():
    linked = SyntheticLinkedPartnerEvidenceProvider(
        _evidence("point", point=Decimal("79000"))
    )
    evidence = linked.fetch_partner_evidence(user_id="user-1", tax_year="2026/27")
    r = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1, has_relevant_partner=True,
        claimant=CLAIMANT_PERSON, partner_evidence=evidence,
    )
    assert r.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    assert r.projected_user_hicbc == Decimal("0")


def test_synthetic_linked_provider_returns_none_for_wrong_year():
    linked = SyntheticLinkedPartnerEvidenceProvider(
        _evidence("point", point=Decimal("79000"), tax_year="2026/27")
    )
    assert linked.fetch_partner_evidence(user_id="user-1", tax_year="2025/26") is None


# ── Customer view privacy ─────────────────────────────────────────────────────

def test_customer_view_never_exposes_partner_raw_values():
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("79000")))
    view = customer_view(r)
    assert "79000" not in str(view)
    assert "partner_evidence" not in view
    assert "original_value" not in view
    assert view["responsibility_status"] == RESPONSIBILITY_PARTNER_LIABLE
    # Partner-liable output must describe only the user's own consequence and
    # must not imply the partner earns more, is liable or carries the charge.
    assert "not included" in view["headline"].lower()
    assert "your partner" not in view["headline"].lower()
    assert "earns more" not in view["headline"].lower()
    assert "liable" not in view["headline"].lower()


def test_customer_view_uses_supplied_partner_message():
    r = _resolve("70000", CB_1, True, _evidence("point", point=Decimal("55000")))
    view = customer_view(r)
    assert "partner information you supplied" in view["messages"][0]
