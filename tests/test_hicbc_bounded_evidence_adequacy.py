"""Adversarial regressions for the HICBC bounded evidence-adequacy correction.

These tests pin the four independently reviewed findings (H1–H4) plus the key
regression boundaries.  Expected monetary values are derived directly from the
statutory rules (ITEPA 2003 s.681B–681C, £60,000/£80,000 and £200 per whole
percentage point), not by calling the production implementation as an oracle.

H1 — claimant identity is not absence of a higher-ANI partner.
H2 — missing entitlement weeks must not silently become a 52-week amount.
H3 — partial/unknown relationship-period facts must not be discarded.
H4 — customer wording must describe only the receiving user's consequence.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import reserved.database as db
from reserved.engines.hicbc_partner import (
    ANI_COMPONENT_WHOLE,
    CLAIMANT_PARTNER,
    CLAIMANT_PERSON,
    RESPONSIBILITY_INSUFFICIENT_FACTS,
    RESPONSIBILITY_PARTNER_LIABLE,
    RESPONSIBILITY_PERSON_LIABLE,
    SOURCE_LINKED_PARTNER,
    PartnerEvidence,
    annual_child_benefit_amount,
    customer_view,
    determine_hicbc_responsibility,
)
from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.web.hicbc import build_responsibility

ROOT = Path(__file__).resolve().parents[1]
TAX_YEAR = "2026/27"
CB_1 = Decimal("1406.60")  # 2026/27 one child: 27.05 * 52


# ── H1 — responsibility is established by adequate facts, never claimant alone ─

def test_claimant_person_without_partner_facts_is_not_actionable():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "person",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert result.total_liability is None
    assert result.calculation_status == "insufficient_facts"
    assert "hicbc" in result.unsupported_families


def test_negative_higher_ani_signal_is_not_ignored():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "person",
        "taxpayer_is_higher_ani_partner": False,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_explicit_no_partner_for_period_gives_valid_personal_calculation():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "has_relevant_partner": False,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal("703.00")
    assert result.hicbc_liable_person == "person"
    assert result.calculation_status == "calculated"


def test_partner_claimant_without_partner_is_insufficient():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "partner",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert result.calculation_status == "insufficient_facts"


def test_relevant_partner_declared_but_partner_ani_missing():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "has_relevant_partner": True,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_relevant_partner_with_user_higher():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "55000",
        "annual_child_benefit_received_by_person": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal("703.00")
    assert result.hicbc_liable_person == "person"


def test_relevant_partner_with_partner_higher():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "75000",
        "annual_child_benefit_received_by_person": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal("0.00")
    assert result.hicbc_liable_person == "partner"
    assert result.hicbc_household_charge == Decimal("1054.00")


def test_equal_ani_user_claimant_is_person_liable():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "person",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal("703.00")
    assert result.hicbc_liable_person == "person"


def test_equal_ani_partner_claimant_is_partner_liable():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "partner",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal("0.00")
    assert result.hicbc_liable_person == "partner"


def test_equal_ani_unknown_claimant_is_insufficient():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_malformed_claimant_fails_closed():
    with pytest.raises(ValueError, match="child_benefit_claimant"):
        calculate_annual_position({
            "adjusted_net_income": "70000",
            "annual_child_benefit": "1406.60",
            "child_benefit_claimant": "bogus",
            "payments_received_for_full_charge_period": True,
        })


def test_conflicting_claimant_and_partner_facts_are_insufficient():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "child_benefit_claimant": "partner",
        "has_relevant_partner": False,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_conflicting_partner_ani_and_no_partner_is_insufficient():
    result = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "55000",
        "annual_child_benefit_received_by_person": "1406.60",
        "has_relevant_partner": False,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_responsibility_moves_between_users_when_ani_changes():
    below = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "55000",
        "annual_child_benefit_received_by_person": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    above = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "79000",
        "annual_child_benefit_received_by_person": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    assert below.hicbc_liable_person == "person"
    assert above.hicbc_liable_person == "partner"


def test_main_engine_and_integrated_path_agree_for_equivalent_facts():
    main = determine_hicbc_responsibility(
        user_ani="70000",
        child_benefit_amount=CB_1,
        has_relevant_partner=True,
        claimant=CLAIMANT_PERSON,
        partner_evidence=PartnerEvidence(
            evidence_id="e1",
            source_kind="user_supplied_partner_estimate",
            source_reference="r",
            subject_reference="partner",
            tax_year=TAX_YEAR,
            representation="point",
            point=Decimal("55000"),
            low=None,
            high=None,
            effective_period=TAX_YEAR,
            observed_at="2026-08-17T10:00:00Z",
            confirmed_at=None,
            completeness="complete_for_purpose",
            recency_state="current",
            consent_state="not_required",
            ani_components=(ANI_COMPONENT_WHOLE,),
        ),
        tax_year=TAX_YEAR,
    )
    integrated = calculate_annual_position({
        "person_adjusted_net_income": "70000",
        "partner_adjusted_net_income": "55000",
        "annual_child_benefit_received_by_person": "1406.60",
        "payments_received_for_full_charge_period": True,
    })
    assert main.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert main.projected_user_hicbc == Decimal("703.00")
    assert integrated.hicbc == main.projected_user_hicbc
    assert integrated.hicbc_liable_person == "person"


# ── H2 — entitlement weeks and annual-amount period adequacy ──────────────────

def test_child_count_with_missing_weeks_is_incomplete():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "eldest_or_only_children": 1,
        "additional_children": 0,
        "taxpayer_is_higher_ani_partner": True,
    })
    assert result.child_benefit_amount is None
    assert result.hicbc is None
    assert result.unsupported_families == ("hicbc",)
    assert "hicbc_facts_incomplete" in result.limitations


@pytest.mark.parametrize("weeks,benefit", [(0, "0.00"), (1, "27.05"), (26, "703.30"), (52, "1406.60"), (53, "1433.65")])
def test_child_count_explicit_weeks(weeks, benefit):
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "eldest_or_only_children": 1,
        "additional_children": 0,
        "weeks_entitled": weeks,
        "taxpayer_is_higher_ani_partner": True,
    })
    assert result.child_benefit_amount == Decimal(benefit)


@pytest.mark.parametrize("weeks", [-1, 54, "abc", 26.5, True])
def test_malformed_or_out_of_range_weeks_fail_closed(weeks):
    with pytest.raises(ValueError):
        calculate_annual_position({
            "adjusted_net_income": "70000",
            "eldest_or_only_children": 1,
            "additional_children": 0,
            "weeks_entitled": weeks,
            "taxpayer_is_higher_ani_partner": True,
        })


def test_explicit_annual_amount_with_full_period_is_determinate():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "taxpayer_is_higher_ani_partner": True,
        "payments_received_for_full_charge_period": True,
    })
    assert result.child_benefit_amount == Decimal("1406.60")
    assert result.hicbc == Decimal("703.00")


def test_explicit_annual_amount_without_period_confirmation_is_incomplete():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "taxpayer_is_higher_ani_partner": True,
    })
    assert result.child_benefit_amount is None
    assert result.hicbc is None
    assert "hicbc_facts_incomplete" in result.limitations


def test_explicit_annual_amount_with_false_period_confirmation_is_incomplete():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "taxpayer_is_higher_ani_partner": True,
        "payments_received_for_full_charge_period": False,
    })
    assert result.hicbc is None
    assert "hicbc_facts_incomplete" in result.limitations


def test_missing_weeks_is_distinct_from_explicit_52():
    missing = calculate_annual_position({
        "adjusted_net_income": "70000",
        "eldest_or_only_children": 1,
        "additional_children": 0,
        "taxpayer_is_higher_ani_partner": True,
    })
    explicit = calculate_annual_position({
        "adjusted_net_income": "70000",
        "eldest_or_only_children": 1,
        "additional_children": 0,
        "weeks_entitled": 52,
        "taxpayer_is_higher_ani_partner": True,
    })
    assert missing.child_benefit_amount is None
    assert explicit.child_benefit_amount == Decimal("1406.60")
    assert explicit.hicbc == Decimal("703.00")


def test_annual_child_benefit_amount_weeks_boundaries():
    assert annual_child_benefit_amount(children=1, weeks_entitled=0) == Decimal("0.00")
    assert annual_child_benefit_amount(children=1, weeks_entitled=1) == Decimal("27.05")
    assert annual_child_benefit_amount(children=1, weeks_entitled=53) == Decimal("1433.65")
    assert annual_child_benefit_amount(children=1) is None  # missing stays unknown


# ── H3 — relationship-period facts must not be discarded ──────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    test_file = tmp_path / "adequacy.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


def _user(clerk_id: str, income: float) -> int:
    uid = db.get_or_create_user(clerk_id, email=f"{clerk_id}@x", display_name=clerk_id)
    db.save_profile_by_user(uid, {
        "income_estimate": income,
        "pension_contribution": 0.0,
        "display_name": clerk_id,
        "tax_year": TAX_YEAR,
    })
    return uid


def _save(row: dict) -> int:
    uid = _user("u", 70000)
    defaults = {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_claimant": "person",
        "child_benefit_children": 1,
        "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": None,
        "relationship_covers_full_year": None,
        "representation": None,
        "partner_ani_point": None,
        "partner_ani_low": None,
        "partner_ani_high": None,
        "source_kind": "user_supplied_partner_estimate",
        "completeness": "complete_for_purpose",
        "recency_state": "current",
    }
    defaults.update(row)
    db.save_hicbc_estimate(uid, defaults)
    return uid


def test_no_partner_for_entire_year_is_determinate(tmp_db):
    uid = _save({"has_relevant_partner": 0, "relationship_covers_full_year": 1})
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert result.projected_user_hicbc == Decimal("703.00")


def test_no_partner_with_unknown_relationship_period_is_insufficient(tmp_db):
    uid = _save({"has_relevant_partner": 0, "relationship_covers_full_year": None})
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert result.projected_user_hicbc is None


def test_no_partner_with_partial_relationship_is_insufficient(tmp_db):
    uid = _save({"has_relevant_partner": 0, "relationship_covers_full_year": 0})
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert result.projected_user_hicbc is None


def test_legacy_null_period_facts_remain_unknown(tmp_db):
    uid = _save({"has_relevant_partner": 0, "relationship_covers_full_year": None})
    row = db.get_hicbc_estimate(uid, TAX_YEAR)
    assert row["relationship_covers_full_year"] is None
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.calculation_status == "insufficient_facts"


def test_legacy_ambiguous_full_year_value_is_not_reinterpreted(tmp_db):
    uid = _save({
        "has_relevant_partner": 0,
        "relationship_covers_full_year": 1,
    })
    # Simulate the v10 migration boundary: the old value remains present but
    # the newly added semantics marker has no default and is therefore NULL.
    with db._connection() as conn:
        conn.execute(
            "UPDATE hicbc_estimates SET partner_status_period_semantics = NULL WHERE user_id = ?",
            (uid,),
        )
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert result.projected_user_hicbc is None


def test_malformed_persisted_period_value_fails_closed(tmp_db):
    uid = _save({
        "has_relevant_partner": 0,
        "relationship_covers_full_year": "not-a-period",
        "partner_status_period_semantics": "status_answer_full_year",
    })
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert result.projected_user_hicbc is None


def test_partner_for_whole_year_with_evidence_is_determinate(tmp_db):
    uid = _save({
        "has_relevant_partner": 1,
        "relationship_covers_full_year": 1,
        "representation": "point",
        "partner_ani_point": "55000",
    })
    result = build_responsibility(uid, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_PERSON_LIABLE


def test_partner_for_part_of_year_is_not_full_year_absence(tmp_db):
    uid = _save({
        "has_relevant_partner": 1,
        "relationship_covers_full_year": 0,
        "representation": "point",
        "partner_ani_point": "55000",
    })
    result = build_responsibility(uid, TAX_YEAR)["result"]
    # A partial-year relationship is material uncertainty, never a full-year point.
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.projected_user_hicbc is None


# ── H4 — privacy-minimised partner-liable presentation ────────────────────────

def _linked_evidence_result():
    return determine_hicbc_responsibility(
        user_ani="70000",
        child_benefit_amount=CB_1,
        has_relevant_partner=True,
        claimant=CLAIMANT_PERSON,
        partner_evidence=PartnerEvidence(
            evidence_id="linked",
            source_kind=SOURCE_LINKED_PARTNER,
            source_reference="link:1",
            subject_reference="linked_partner:abc",
            tax_year=TAX_YEAR,
            representation="point",
            point=Decimal("90000"),
            low=None,
            high=None,
            effective_period=TAX_YEAR,
            observed_at="2026-08-17T10:00:00Z",
            confirmed_at=None,
            completeness="complete_for_purpose",
            recency_state="current",
            consent_state="consented",
            ani_components=(ANI_COMPONENT_WHOLE,),
        ),
        tax_year=TAX_YEAR,
    )


def test_partner_liable_headline_describes_only_users_consequence():
    view = customer_view(_linked_evidence_result())
    headline = view["headline"].lower()
    assert "not included" in headline
    assert "your partner" not in headline
    assert "partner" not in headline
    assert "earns more" not in headline
    assert "liable" not in headline
    assert "applies to" not in headline


def test_linked_provenance_is_not_labelled_user_supplied():
    view = customer_view(_linked_evidence_result())
    assert not any("you supplied" in m for m in view["messages"])
    assert any("linked account" in m for m in view["messages"])


def test_manual_provenance_is_labelled_user_supplied():
    result = determine_hicbc_responsibility(
        user_ani="70000",
        child_benefit_amount=CB_1,
        has_relevant_partner=True,
        claimant=CLAIMANT_PERSON,
        partner_evidence=PartnerEvidence(
            evidence_id="manual",
            source_kind="user_supplied_partner_estimate",
            source_reference="r",
            subject_reference="partner",
            tax_year=TAX_YEAR,
            representation="point",
            point=Decimal("55000"),
            low=None,
            high=None,
            effective_period=TAX_YEAR,
            observed_at="2026-08-17T10:00:00Z",
            confirmed_at=None,
            completeness="complete_for_purpose",
            recency_state="current",
            consent_state="not_required",
            ani_components=(ANI_COMPONENT_WHOLE,),
        ),
        tax_year=TAX_YEAR,
    )
    view = customer_view(result)
    assert any("you supplied" in m for m in view["messages"])


def test_customer_view_never_exposes_partner_financials():
    view = customer_view(_linked_evidence_result())
    serialised = str(view)
    for forbidden in ("90000", "income band", "earns more", "relative salary", "partner_evidence", "original_value"):
        assert forbidden not in serialised
