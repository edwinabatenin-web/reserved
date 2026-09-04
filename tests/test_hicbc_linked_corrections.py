"""Direct regressions for the HICBC linked-evidence correction pass.

Each test targets a specific invariant from the bounded correction pass and
would fail against the pre-correction implementation.  Fixtures use a temporary
SQLite database; nothing outside ``/tmp`` is written.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import reserved.database as db
from reserved.web.hicbc import (
    _customer_ani_from_row,
    _full_profile_from_row,
    _linked_partner_evidence,
    _merge_partner_evidence,
    _normalise_has_relevant_partner,
    _user_ani_from_profile,
    build_responsibility,
)
from reserved.web.routes import (
    _db_data_to_profile,
    _missing_assurance_scope,
    _profile_to_db_data,
)
from reserved.engines.hicbc_partner import (
    ANI_COMPONENT_WHOLE,
    CLAIMANT_PERSON,
    RESPONSIBILITY_INSUFFICIENT_FACTS,
    RESPONSIBILITY_PARTNER_LIABLE,
    RESPONSIBILITY_PERSON_LIABLE,
    SOURCE_LINKED_PARTNER,
    PartnerEvidence,
    determine_hicbc_responsibility,
)
from reserved.evidence_uncertainty import EffectKind
from reserved.engines.hicbc_integration import (
    PAYMENT,
    PERSONALISED_ESTIMATE,
    RESERVE_GUIDANCE,
    integrate_hicbc,
)

ROOT = Path(__file__).resolve().parents[1]
TAX_YEAR = "2026/27"
CB_1 = Decimal("1406.60")  # 2026/27 one child: 27.05 * 52


# ── Fixtures / helpers ────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    test_file = tmp_path / "corrections.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


def _user(clerk_id: str, income: float, *, tax_year: str | None = TAX_YEAR) -> int:
    uid = db.get_or_create_user(clerk_id, email=f"{clerk_id}@x", display_name=clerk_id)
    data = {"income_estimate": income, "pension_contribution": 0.0, "display_name": clerk_id}
    if tax_year is not None:
        data["tax_year"] = tax_year
    db.save_profile_by_user(uid, data)
    return uid


def _link(a: int, b: int) -> None:
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    assert db.accept_hicbc_link_invitation(b, token, TAX_YEAR) is not None


def _consent(a: int, b: int) -> None:
    assert db.record_hicbc_link_consent(a, TAX_YEAR, "hicbc-notice-v1") is True
    assert db.record_hicbc_link_consent(b, TAX_YEAR, "hicbc-notice-v1") is True


def _set_profile_updated_at(uid: int, ts: str) -> None:
    with db._connection() as conn:
        conn.execute("UPDATE user_profiles SET updated_at = ? WHERE user_id = ?", (ts, uid))


def _set_profile_tax_year(uid: int, tax_year: str) -> None:
    with db._connection() as conn:
        conn.execute("UPDATE user_profiles SET tax_year = ? WHERE user_id = ?", (tax_year, uid))


def _evidence(point=None, low=None, high=None, *, completeness="complete_for_purpose",
              recency="current", consent="consented", observed="2026-08-01T00:00:00+00:00",
              effective=TAX_YEAR, tax_year=TAX_YEAR, ani_components=(), conflict=False,
              source_kind="user_supplied_partner_estimate"):
    return PartnerEvidence(
        evidence_id="ev",
        source_kind=source_kind,
        source_reference="ref",
        subject_reference="partner",
        tax_year=tax_year,
        representation=("point" if point is not None else "range"),
        point=Decimal(point) if point is not None else None,
        low=Decimal(low) if low is not None else None,
        high=Decimal(high) if high is not None else None,
        effective_period=effective,
        observed_at=observed,
        confirmed_at=None,
        completeness=completeness,
        recency_state=recency,
        consent_state=consent,
        ani_components=ani_components,
        conflict=conflict,
    )


# ── Correction 1 — assured linked ANI contract ────────────────────────────────

def test_raw_profile_is_not_complete_ani(tmp_db):
    # Production settings shape: employment salary lives in `notes`, YTD
    # freelance profit lives in the `income_estimate` column.
    partner = _user("p", 0)
    db.save_profile_by_user(partner, _profile_to_db_data({
        "day_job_salary": "60000",
        "ytd_freelance_profit": "30000",
        "personal_pension_contributions": "5000",
        "entity_type": "sole_trader",
        "trading_name": "",
        "accounting_method": "cash_basis",
        "vat_registered": False,
        "first_name": "Partner",
        "child_benefit_children": 0,
        "child_benefit_annual": None,
    }))
    raw = db.get_profile_by_user(partner)
    # The raw row omits day_job_salary and does not project ytd freelance profit.
    assert _user_ani_from_profile(raw) == Decimal("25000")  # 30000 - 5000, salary ignored


def test_deserialisation_alone_does_not_establish_completeness(tmp_db):
    partner = _user("p", 0)
    db.save_profile_by_user(partner, _profile_to_db_data({
        "day_job_salary": "60000",
        "ytd_freelance_profit": "30000",
        "personal_pension_contributions": "5000",
        "entity_type": "sole_trader",
        "trading_name": "",
        "accounting_method": "cash_basis",
        "vat_registered": False,
        "first_name": "Partner",
        "child_benefit_children": 0,
        "child_benefit_annual": None,
    }))
    full = _db_data_to_profile(db.get_profile_by_user(partner))
    assert full.get("day_job_salary") == "60000"
    # The settings-form mapping does not carry tax_year; restore the year scope.
    _set_profile_tax_year(partner, TAX_YEAR)
    # Even with the full profile restored, the linked path remains partial: it is
    # a projection, not an assured full-ANI contract.
    a = _user("a", 70000)
    _link(a, partner)
    _consent(a, partner)
    ev = _linked_partner_evidence(a, TAX_YEAR)
    assert ev is not None
    assert ev.completeness == "partial"
    assert ev.ani_components == ()


def test_profile_projection_is_partial_and_non_determinate(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    # Child Benefit facts are required independently of the link.
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR, "receives_child_benefit": 1, "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
    })
    ev = _linked_partner_evidence(a, TAX_YEAR)
    assert ev is not None and ev.completeness == "partial"
    result = build_responsibility(a, TAX_YEAR)["result"]
    # A partial linked ANI must never be determinate.
    assert result.calculation_status == "calculated_with_material_uncertainty"


def test_partial_linked_ani_cannot_pass_personalised_or_reserve(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    result = build_responsibility(a, TAX_YEAR)["result"]
    for purpose in (PERSONALISED_ESTIMATE, RESERVE_GUIDANCE):
        contribution = integrate_hicbc(result, purpose)
        assert not contribution.included
        assert not contribution.actionable
        assert contribution.charge is None


def test_synthetic_adequate_ani_contract_is_determinate():
    # A future adequate producer supplies a complete component set + provenance.
    ev = _evidence(
        point="50000",
        completeness="complete_for_purpose",
        recency="current",
        consent="consented",
        ani_components=(
            "employment", "sole_trade", "savings", "dividends",
            "property", "foreign", "gift_aid", "pension_adjustments",
        ),
    )
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated"
    assert result.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    # Independently derived charge (50% of floor(1406.60)=1406 → 703), not an
    # oracle read of production output.
    assert result.projected_user_hicbc == Decimal("703.00")
    assert integrate_hicbc(result, PERSONALISED_ESTIMATE).adequacy == "adequate"


def test_no_new_ani_formula_is_duplicated():
    src = (ROOT / "reserved" / "web" / "hicbc.py").read_text(encoding="utf-8")
    assert "_user_ani_from_profile(partner_profile)" in src
    low = src.lower()
    assert "gift_aid" not in low
    assert "savings_interest" not in low
    assert "dividends" not in low


# ── Correction 2 — truthful evidence timestamps ───────────────────────────────

def test_repeated_reads_retain_source_observation_time(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    _set_profile_updated_at(b, "2026-08-01T09:00:00+00:00")
    ev1 = _linked_partner_evidence(a, TAX_YEAR)
    ev2 = _linked_partner_evidence(a, TAX_YEAR)
    assert ev1.observed_at == "2026-08-01T09:00:00+00:00"
    assert ev2.observed_at == ev1.observed_at  # retrieval does not refresh age
    assert ev1.recency_state == "unconfirmed"  # never hard-coded "current"


def test_unknown_observation_time_remains_uncertain(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    # No usable profile observation time: the observation time stays unknown.
    _set_profile_updated_at(b, "")
    ev = _linked_partner_evidence(a, TAX_YEAR)
    assert ev is not None
    assert ev.observed_at == "unknown"
    assert ev.recency_state == "unconfirmed"


def test_merged_evidence_does_not_fabricate_observation_time(tmp_db):
    manual = _evidence(point="50000", observed="2026-08-10T00:00:00+00:00")
    linked = _evidence(point="90000", observed="2026-08-01T00:00:00+00:00", completeness="partial")
    merged, conflict = _merge_partner_evidence(manual, linked)
    assert merged.observed_at == "2026-08-01T00:00:00+00:00"  # older source, not now()


# ── Correction 3 — tax-year alignment ─────────────────────────────────────────

def test_mismatched_partner_tax_year_fails_closed(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000, tax_year="2025/26")
    _link(a, b)
    _consent(a, b)
    assert _linked_partner_evidence(a, TAX_YEAR) is None
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.calculation_status == "insufficient_facts"


def test_wrong_direction_tax_year_mismatch_fails_closed(tmp_db):
    a = _user("a", 70000, tax_year="2026/27")
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    # Requested year is 2025/26 while partner profile is 2026/27.
    assert _linked_partner_evidence(a, "2025/26") is None


# ── Correction 4 — relationship-period adequacy ───────────────────────────────

def test_null_relationship_start_is_non_determinate(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    ev = _linked_partner_evidence(a, TAX_YEAR)
    assert ev is not None
    assert ev.effective_period == "unknown"  # not the full tax year
    assert ev.completeness == "partial"


def test_link_acceptance_date_is_not_relationship_start(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    _set_profile_updated_at(b, "2026-08-01T09:00:00+00:00")
    link = db.get_active_hicbc_link(a, TAX_YEAR)
    assert link["relationship_started_at"] is None
    ev = _linked_partner_evidence(a, TAX_YEAR)
    # observed_at is the profile update time, never the link acceptance time.
    assert ev.observed_at == "2026-08-01T09:00:00+00:00"
    assert ev.observed_at != link["accepted_at"]


def test_relationship_adequacy_alone_does_not_make_partial_ani_adequate(tmp_db):
    # A full-period effective_period with partial ANI is still non-determinate.
    ev = _evidence(point="90000", completeness="partial", effective=TAX_YEAR)
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"


# ── Correction 5 — deterministic relationship selection ───────────────────────

def test_one_user_cannot_acquire_two_active_links(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    c = _user("c", 50000)
    _link(a, b)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    assert db.accept_hicbc_link_invitation(c, token, TAX_YEAR) is None  # a already linked
    # And the acceptor side: b→c while b already linked to a.
    token2 = db.create_hicbc_link_invitation(c, TAX_YEAR)
    assert db.accept_hicbc_link_invitation(b, token2, TAX_YEAR) is None


def test_preexisting_duplicate_active_links_fail_closed(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    c = _user("c", 50000)
    now = db._now()
    # Simulate malformed data: two active links for one user (bypassing service).
    with db._connection() as conn:
        conn.execute(
            "INSERT INTO hicbc_links (user_low_id, user_high_id, tax_year, purpose, status, initiator_id, created_at, accepted_at) "
            "VALUES (?, ?, ?, 'hicbc_responsibility', 'active', ?, ?, ?)",
            (min(a, b), max(a, b), TAX_YEAR, a, now, now),
        )
        conn.execute(
            "INSERT INTO hicbc_links (user_low_id, user_high_id, tax_year, purpose, status, initiator_id, created_at, accepted_at) "
            "VALUES (?, ?, ?, 'hicbc_responsibility', 'active', ?, ?, ?)",
            (min(a, c), max(a, c), TAX_YEAR, a, now, now),
        )
    assert db.get_active_hicbc_link(a, TAX_YEAR) is None  # ambiguous → fail closed
    assert db.get_hicbc_link_partner_id(a, TAX_YEAR) is None


def test_revoke_then_different_link_is_deterministic(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    c = _user("c", 50000)
    _link(a, b)
    assert db.revoke_hicbc_link(a, TAX_YEAR) is True
    assert db.get_active_hicbc_link(a, TAX_YEAR) is None
    _link(a, c)
    assert db.get_hicbc_link_partner_id(a, TAX_YEAR) == c


# ── Correction 6 — manual-versus-linked conflict logic ────────────────────────

@pytest.mark.parametrize(
    "mlow,mhigh,llow,lhigh,expect_conflict",
    [
        ("40000", "50000", "45000", "55000", False),  # partial overlap
        ("40000", "50000", "60000", "70000", True),   # disjoint above
        ("40000", "50000", "30000", "35000", True),   # disjoint below
        ("40000", "50000", "30000", "45000", False),  # overlap low side
        ("40000", "50000", "50000", "60000", False),  # touching upper bound
        ("40000", "50000", "30000", "40000", False),  # touching lower bound
        ("40000", "50000", "40000", "50000", False),  # identical ranges
        ("40000", "50000", "30000", "60000", False),  # containment (linked wider)
        ("40000", "50000", "42000", "48000", False),  # containment (manual wider)
    ],
)
def test_conflict_classification(mlow, mhigh, llow, lhigh, expect_conflict):
    manual = _evidence(low=mlow, high=mhigh)
    linked = _evidence(low=llow, high=lhigh)
    merged, conflict = _merge_partner_evidence(manual, linked)
    assert conflict is expect_conflict
    assert merged.conflict is expect_conflict
    assert merged.low == min(Decimal(mlow), Decimal(llow))
    assert merged.high == max(Decimal(mhigh), Decimal(lhigh))


def test_disjoint_sources_surface_conflicting_uncertainty(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 1,
        "representation": "range",
        "partner_ani_low": "40000",
        "partner_ani_high": "50000",
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert any(u.reason.value == "conflicting" for u in result.uncertainties)


def test_identical_sources_preserve_provenance_and_stay_uncertain(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 50000)
    _link(a, b)
    _consent(a, b)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 1,
        "representation": "point",
        "partner_ani_point": "50000",
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    kinds = {e.source_kind for e in result.evidence}
    assert "user_supplied_partner_estimate" in kinds
    assert "linked_partner_source" in kinds
    # Merged evidence is conservatively partial even when sources agree.
    assert result.calculation_status == "calculated_with_material_uncertainty"


# ── Correction 7 — current v1 semantics ───────────────────────────────────────

def test_result_limitations_no_longer_declare_post_v1():
    ev = _evidence(point="50000")
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    joined = " ".join(result.limitations).lower()
    assert "post_v1" not in joined
    assert "october_v1" in joined
    assert result.permitted_uses == ("hicbc_responsibility_estimate",)
    assert "payment_initiation" in result.prohibited_uses
    assert "v1_customer_tax_total" not in result.prohibited_uses
    assert "reserve_or_set_aside_guidance" not in result.prohibited_uses


def test_source_no_longer_declares_post_v1_exclusion():
    src = (ROOT / "reserved" / "engines" / "hicbc_partner.py").read_text(encoding="utf-8")
    assert "post_v1_hicbc_responsibility_estimate" not in src
    assert "hicbc_is_post_v1_and_excluded" not in src


def test_metadata_scope_uses_conditional_v1_wording():
    # Source-level: the metadata generator (and the API fallback) must describe
    # HICBC as a conditional October v1 target, never as a post-v1 exclusion.
    gen = (ROOT / "scripts" / "generate_assurance_metadata.py").read_text(encoding="utf-8")
    assert "High Income Child Benefit Charge (HICBC) — October v1 target (not yet activated)" in gen
    assert "High Income Child Benefit Charge (HICBC) — post-v1" not in gen
    routes = (ROOT / "reserved" / "web" / "routes.py").read_text(encoding="utf-8")
    assert "High Income Child Benefit Charge (HICBC) — October v1 target (not yet activated)" in routes


def test_missing_metadata_fallback_has_exact_founder_scope():
    assert _missing_assurance_scope() == {
        "in_scope": [
            "Income tax — England, Wales and Northern Ireland",
            "PAYE and multiple employments",
            "Sole-trade income",
            "Dividends and savings interest",
            "UK and foreign property income",
            "Student and postgraduate loan liability",
            "Relief-at-Source pension treatment",
            "High Income Child Benefit Charge (HICBC) — October v1 target (not yet activated)",
            "Blind Person's Allowance",
            "Bounded Making Tax Digital indication",
        ],
        "out_of_scope": [
            "Scottish Income Tax — post-v1",
            "Capital Gains Tax — post-v1",
            "Full MTD filing — post-v1",
        ],
    }


def test_customer_templates_do_not_declare_post_v1():
    # The 17 August founder decision brought HICBC into the October v1 scope; the
    # customer-facing pages must not still describe it as a post-v1 preview.
    for name in ("hicbc.html", "hicbc_link.html"):
        template = (ROOT / "reserved" / "templates" / "v2" / name).read_text(encoding="utf-8")
        assert "post-v1" not in template.lower()


# ── Mutual permission + limited inference gate ────────────────────────────────

def test_invitation_acceptance_alone_is_not_adequate_consent(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)  # no versioned mutual consent recorded
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR) is False
    assert _linked_partner_evidence(a, TAX_YEAR) is None


def test_missing_acknowledgement_from_either_participant_is_non_actionable(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    assert db.record_hicbc_link_consent(a, TAX_YEAR, "hicbc-notice-v1") is True
    # Only one participant consented.
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR) is False
    assert _linked_partner_evidence(a, TAX_YEAR) is None


def test_empty_notice_version_is_rejected(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    assert db.record_hicbc_link_consent(a, TAX_YEAR, "") is False
    assert db.record_hicbc_link_consent(a, TAX_YEAR, None) is False


def test_withdrawal_prevents_future_linked_evidence_use(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    assert _linked_partner_evidence(a, TAX_YEAR) is not None
    assert db.revoke_hicbc_link(b, TAX_YEAR) is True
    assert db.get_active_hicbc_link(a, TAX_YEAR) is None
    assert _linked_partner_evidence(a, TAX_YEAR) is None
    # Retained (revoked) link row must not preserve calculation access.
    with db._connection() as conn:
        row = conn.execute(
            "SELECT status FROM hicbc_links WHERE user_low_id=? OR user_high_id=?",
            (a, a),
        ).fetchone()
    assert row is not None and row["status"] == "revoked"


# ── Integration containment ───────────────────────────────────────────────────

def test_partial_linked_evidence_never_actionable():
    a_ani = Decimal("70000")
    # Even a clearly higher partner must not be actionable while ANI is partial.
    ev = _evidence(point="90000", completeness="partial", consent="consented")
    result = determine_hicbc_responsibility(
        user_ani=a_ani, child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.responsibility_status == RESPONSIBILITY_PARTNER_LIABLE
    for purpose in (PERSONALISED_ESTIMATE, RESERVE_GUIDANCE, PAYMENT):
        contribution = integrate_hicbc(result, purpose)
        assert not contribution.included
        assert not contribution.actionable


def test_payment_and_sweeping_remain_prohibited():
    ev = _evidence(point="50000")
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    payment = integrate_hicbc(result, PAYMENT)
    assert payment.included is False
    assert payment.actionable is False


def test_informational_result_is_not_falsely_determinate(tmp_db):
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    _consent(a, b)
    built = build_responsibility(a, TAX_YEAR)
    assert built["result"].calculation_status != "calculated"
    assert built["view"]["calculation_status"] != "calculated"


def test_integration_gate_has_no_production_caller():
    import subprocess
    r = subprocess.run(
        ["grep", "-rn", "--include=*.py", "integrate_hicbc",
         str(ROOT / "reserved")],
        capture_output=True, text=True,
    )
    callers = [
        line for line in r.stdout.splitlines()
        if "def integrate_hicbc" not in line and "integrate_hicbc(" in line
    ]
    assert callers == []  # disconnected gate: no production caller in this pass


# ── Final bounded corrections: adversarial regressions ───────────────────────

def test_absent_tax_year_fails_closed_not_relabelled(tmp_db):
    # R3: a linked partner with no supported source tax year must not be emitted
    # as evidence for the requested calculation year.
    a = _user("a", 70000)
    b = _user("b", 90000, tax_year=None)
    _link(a, b)
    _consent(a, b)
    assert _linked_partner_evidence(a, TAX_YEAR) is None
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.calculation_status == "insufficient_facts"


def test_merge_preserves_unknown_observation_time_and_period(tmp_db):
    # R4: merging must not turn an unknown observation time / relationship period
    # into a precise ISO date or the full tax year.
    manual = _evidence(point="50000", observed="2026-08-10T00:00:00+00:00",
                       effective=TAX_YEAR)
    linked = _evidence(point="90000", observed="unknown", effective="unknown",
                       completeness="partial")
    merged, _conflict = _merge_partner_evidence(manual, linked)
    assert merged.observed_at == "unknown"
    assert merged.effective_period == "unknown"


def test_incompatible_notice_versions_are_not_mutual(tmp_db):
    # R5: both participants must record the single authoritative notice version.
    a = _user("a", 70000)
    b = _user("b", 90000)
    _link(a, b)
    assert db.record_hicbc_link_consent(a, TAX_YEAR, "hicbc-notice-v1") is True
    assert db.record_hicbc_link_consent(b, TAX_YEAR, "hicbc-notice-v2") is False
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)


def test_caller_labels_cannot_bypass_missing_facts():
    # R1: completeness/recency labels alone must not produce a determinate result
    # when the underlying facts (relationship period, ANI coverage) are missing.
    ev = _evidence(point="50000", completeness="complete_for_purpose",
                   recency="current", effective="unknown", ani_components=())
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.projected_user_hicbc is None


def test_unknown_observation_time_does_not_crash_or_determine():
    # R1/R4: an unknown observation time must fail closed as materially uncertain
    # rather than crashing or producing a determinate point estimate.
    ev = _evidence(point="50000", observed="unknown", ani_components=())
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.projected_user_hicbc is None
    assert result.possible_charge_low == Decimal("0")
    assert result.possible_charge_high == Decimal("703.00")


def test_adequate_manual_assertion_stays_determinate():
    # Guard: the adequacy contract must not regress the legitimate manual route.
    ev = _evidence(point="50000", ani_components=(ANI_COMPONENT_WHOLE,))
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated"
    assert result.projected_user_hicbc == Decimal("703.00")


# ── H1 — persisted tri-state must be normalised before the engine boundary ────

def test_persisted_no_partner_integer_zero_is_normalised(tmp_db):
    # The persisted tri-state is INTEGER (0=no); the web boundary must normalise
    # 0 → False so the no-partner path is recognised.  Full-year relationship
    # coverage must also be explicit so "no partner" means "no partner for the
    # whole charge period" and the charge is available.
    a = _user("a", 70000)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 0,
        "relationship_covers_full_year": 1,
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_PERSON_LIABLE
    assert result.calculation_status == "calculated"
    assert result.projected_user_hicbc == Decimal("703.00")


def test_no_partner_does_not_manufacture_claimant_identity(tmp_db):
    # ``has_relevant_partner=0`` (no partner) must NOT manufacture a person
    # claimant on its own.  Personal claimant status requires an explicit
    # entitlement/claimant fact (receives_child_benefit=1 or child_benefit_claimant).
    # Without one, the Child Benefit amount is unknown and the result fails closed.
    a = _user("a", 70000)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "has_relevant_partner": 0,
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.responsibility_status == RESPONSIBILITY_INSUFFICIENT_FACTS
    assert result.claimant is None
    assert result.child_benefit_amount is None


def test_persisted_tri_state_normalisation_round_trip():
    assert _normalise_has_relevant_partner(0) is False
    assert _normalise_has_relevant_partner(1) is True
    assert _normalise_has_relevant_partner(None) is None
    assert _normalise_has_relevant_partner("0") is False
    assert _normalise_has_relevant_partner("no") is False
    assert _normalise_has_relevant_partner("yes") is True
    assert _normalise_has_relevant_partner("garbage") is None


# ── H2 — customer ANI from the full, tax-year-scoped profile ──────────────────

def test_customer_ani_uses_deserialised_profile(tmp_db):
    # Salary is persisted in the notes JSON column; the customer's own ANI must
    # restore it (60000 + 30000 freelance − 5000 pension = 85000), not derive
    # 25000 from the raw row.
    a = _user("a", 0)
    data = _profile_to_db_data({
        "day_job_salary": "60000",
        "ytd_freelance_profit": "30000",
        "personal_pension_contributions": "5000",
        "entity_type": "sole_trader",
        "trading_name": "",
        "accounting_method": "cash_basis",
        "vat_registered": False,
        "first_name": "A",
        "child_benefit_children": 0,
        "child_benefit_annual": None,
    })
    data["tax_year"] = TAX_YEAR
    db.save_profile_by_user(a, data)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 0,
        "relationship_covers_full_year": 1,
    })
    built = build_responsibility(a, TAX_YEAR)
    assert built["user_ani"] == Decimal("85000.00")
    assert built["result"].calculation_status == "calculated"
    # 85000 → 100 complete £200 steps (capped at 100%) → 100% of floor(1406.60)=1406.
    assert built["result"].projected_user_hicbc == Decimal("1406.00")


def test_customer_ani_tax_year_mismatch_fails_closed(tmp_db):
    a = _user("a", 70000, tax_year="2025/26")
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 0,
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.calculation_status == "insufficient_facts"
    assert result.user_ani is None


def test_customer_ani_tax_year_absence_fails_closed(tmp_db):
    a = _user("a", 70000, tax_year=None)
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 0,
    })
    result = build_responsibility(a, TAX_YEAR)["result"]
    assert result.calculation_status == "insufficient_facts"
    assert result.user_ani is None


# ── H3 — malformed labels cannot manufacture determinate evidence ─────────────

def test_unknown_consent_state_rejected_at_construction():
    with pytest.raises(ValueError):
        _evidence(point="50000", consent="not_consented")


def test_unknown_ani_component_markers_rejected_at_construction():
    with pytest.raises(ValueError):
        _evidence(point="50000", ani_components=("banana",))
    with pytest.raises(ValueError):
        _evidence(point="50000", ani_components=("salary_only",))


def test_limited_effective_period_is_non_determinate():
    ev = _evidence(point="50000", effective="one_day_only")
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.projected_user_hicbc is None


def test_linked_source_requires_consent_for_determinacy():
    ev = _evidence(point="50000", source_kind=SOURCE_LINKED_PARTNER,
                   consent="not_required", ani_components=(ANI_COMPONENT_WHOLE,))
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.projected_user_hicbc is None


# ── H4 — merge must not broaden temporal coverage ─────────────────────────────

def test_merge_does_not_expand_limited_period_to_full_year():
    manual = _evidence(point="50000", effective="2026/27")
    linked = _evidence(point="90000", effective="2026-04-06..2026-06-30",
                       completeness="partial")
    merged, _conflict = _merge_partner_evidence(manual, linked)
    assert merged.effective_period == "unknown"


# ── H5 — structured uncertainty effect must match displayed bounds ────────────

def test_material_uncertainty_effect_matches_bounds():
    ev = _evidence(point="50000", completeness="partial")
    result = determine_hicbc_responsibility(
        user_ani="70000", child_benefit_amount=CB_1,
        has_relevant_partner=True, claimant=CLAIMANT_PERSON, partner_evidence=ev, tax_year=TAX_YEAR,
    )
    assert result.calculation_status == "calculated_with_material_uncertainty"
    assert result.possible_charge_low == Decimal("0")
    assert result.possible_charge_high == Decimal("703.00")
    assert any(
        u.effect.kind == EffectKind.RANGE
        and u.effect.low == Decimal("0")
        and u.effect.high == Decimal("703.00")
        for u in result.uncertainties
    )
