"""Focused, pure integration tests for the authenticated PAYE annual bridge."""
from datetime import date
from decimal import Decimal

import pytest
from flask import Flask

import reserved.auth as auth
import reserved.database as db
from reserved.annual_position_persistence_contract import admit_annual_position_projection
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.owner_business_membership_contract import (
    InMemoryOwnerBusinessMembershipFake, MembershipStatus,
    OwnerBusinessMembershipRecord, evaluate_authenticated_owner_business_membership,
)
from reserved.paye_annual_bridge import (
    OwnerBoundPayeEvidenceBatch,
    compose_authenticated_manual_paye,
    read_owner_bound_manual_paye_evidence,
)
from reserved.services.w8_annual_cash_customer_handoff import compose_w8_annual_cash_customer_handoff
from tests.test_annual_to_cash_integration import compose
from tests.test_w8_annual_cash_customer_handoff import references


def entry(slot, tax, *, tax_year="2026/27", user_id=41):
    return {
        "user_id": user_id, "tax_year": tax_year, "employment_slot": slot,
        "evidence_id": f"paye-manual-{slot:032x}",
        "source_kind": "customer_confirmed_manual", "provenance": "customer_confirmed_manual_cumulative_entry",
        "gross_to_date": "10000.00", "tax_paid_to_date": tax, "tax_code": "1257L",
        "pay_frequency": "monthly", "pension_treatment": "none",
        "effective_through": "2027-03-31", "observed_on": "2027-04-05", "completeness": "partial",
    }


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "bridge.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    with db._connection() as connection:
        for user_id in (41, 42):
            connection.execute(
                "INSERT INTO users (id,clerk_user_id,created_at) VALUES (?,?,?)",
                (user_id, f"user_{user_id}", "2026-09-27T00:00:00+00:00"),
            )
    application = Flask(__name__)
    application.config["SECRET_KEY"] = "synthetic"
    return application


def admitted_annual():
    annual = compose()
    handoff = compose_w8_annual_cash_customer_handoff(annual, evidence_references=references(annual))
    assert handoff is not None
    return annual, admit_annual_position_projection(
        annual, handoff, authenticated_user_id="41", authenticated_business_id="business-41-a",
    )


def allowed_membership(app):
    membership = InMemoryOwnerBusinessMembershipFake((OwnerBusinessMembershipRecord(
        membership_reference="membership-41-a", owner_users_id=41,
        business_reference="business-41-a", membership_version=1,
        status=MembershipStatus.ACTIVE,
    ),), snapshot_version=1)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        decision = evaluate_authenticated_owner_business_membership(
            membership_fake=membership, requested_business_reference="business-41-a",
        )
    return membership, decision


def compose_bridge(app, *, entries=None, batch_owner=41, projection=None, decision=None, membership=None):
    annual, accepted_projection = admitted_annual()
    membership, accepted_decision = allowed_membership(app)
    for row in entries if entries is not None else [entry(1, "1200.00"), entry(2, "800.00")]:
        stored = dict(row)
        owner = stored.pop("user_id")
        db.save_paye_manual_entry(owner, stored)
    batch = read_owner_bound_manual_paye_evidence(
        authenticated_owner_user_id=batch_owner, tax_year="2026/27"
    )
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        return compose_authenticated_manual_paye(
            evidence_batch=batch,
            annual_position=annual, annual_projection=projection or accepted_projection,
            membership_decision=decision or accepted_decision, current_membership_snapshot=membership,
            reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        )


def test_multi_employment_manual_evidence_composes_only_after_exact_binding(app):
    result = compose_bridge(app)
    assert result.reconciliation.tax_paid_to_date == Decimal("2000.00")
    assert result.reconciliation.tax_paid_known is True
    assert result.future_pay_forecast is None


@pytest.mark.parametrize("entries", [
    [entry(1, "1200.00"), {**entry(1, "800.00"), "evidence_id": "manual-other"}],
    [entry(1, "1200.00"), {**entry(2, "800.00"), "evidence_id": "paye-manual-00000000000000000000000000000001"}],
])
def test_duplicate_employment_slot_or_evidence_identity_fails_closed(app, monkeypatch, entries):
    monkeypatch.setattr(db, "list_active_paye_manual_entries", lambda *_: entries)
    with pytest.raises(ValueError, match="duplicate"):
        read_owner_bound_manual_paye_evidence(
            authenticated_owner_user_id=41, tax_year="2026/27"
        )


def test_foreign_owner_manual_evidence_fails_closed(app):
    with pytest.raises(ValueError, match="bound"):
        compose_bridge(app, entries=[entry(1, "1200.00", user_id=42)], batch_owner=42)


def test_caller_cannot_construct_or_substitute_an_evidence_batch(app):
    with pytest.raises(TypeError, match="repository-issued"):
        OwnerBoundPayeEvidenceBatch()
    forged = object.__new__(OwnerBoundPayeEvidenceBatch)
    annual, projection = admitted_annual()
    membership, decision = allowed_membership(app)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="not bound"):
            compose_authenticated_manual_paye(
                evidence_batch=forged, annual_position=annual, annual_projection=projection,
                membership_decision=decision, current_membership_snapshot=membership,
                reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
            )


def test_absent_or_cross_owner_membership_and_unadmitted_annual_input_fail_closed(app):
    annual, projection = admitted_annual()
    membership, decision = allowed_membership(app)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="membership"):
            compose_authenticated_manual_paye(
                evidence_batch=read_owner_bound_manual_paye_evidence(authenticated_owner_user_id=41, tax_year="2026/27"), annual_position=annual, annual_projection=projection,
                membership_decision=decision, current_membership_snapshot=InMemoryOwnerBusinessMembershipFake((), snapshot_version=1),
                reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
            )
    with pytest.raises(ValueError, match="not bound"):
        compose_authenticated_manual_paye(
            evidence_batch=read_owner_bound_manual_paye_evidence(authenticated_owner_user_id=41, tax_year="2025/26"), annual_position=annual, annual_projection=projection,
            membership_decision=decision, current_membership_snapshot=membership,
            reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        )
