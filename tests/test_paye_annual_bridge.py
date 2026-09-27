"""Focused, pure integration tests for the authenticated PAYE annual bridge."""
from datetime import date
from decimal import Decimal

import pytest
from flask import Flask

import reserved.auth as auth
from reserved.annual_position_persistence_contract import admit_annual_position_projection
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.owner_business_membership_contract import (
    InMemoryOwnerBusinessMembershipFake, MembershipStatus,
    OwnerBusinessMembershipRecord, evaluate_authenticated_owner_business_membership,
)
from reserved.paye_annual_bridge import compose_authenticated_manual_paye
from reserved.services.w8_annual_cash_customer_handoff import compose_w8_annual_cash_customer_handoff
from tests.test_annual_to_cash_integration import compose
from tests.test_w8_annual_cash_customer_handoff import references


def entry(slot, tax, *, tax_year="2026/27"):
    return {
        "tax_year": tax_year, "employment_slot": slot, "evidence_id": f"manual-{slot}",
        "source_kind": "customer_confirmed_manual", "provenance": "customer_confirmed_manual_cumulative_entry",
        "gross_to_date": "10000.00", "tax_paid_to_date": tax, "tax_code": "1257L",
        "pay_frequency": "monthly", "pension_treatment": "none",
        "effective_through": "2027-03-31", "observed_on": "2027-04-05", "completeness": "partial",
    }


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


def compose_bridge(app, *, entries=None, projection=None, decision=None, membership=None):
    annual, accepted_projection = admitted_annual()
    membership, accepted_decision = allowed_membership(app)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        return compose_authenticated_manual_paye(
            entries=entries if entries is not None else [entry(1, "1200.00"), entry(2, "800.00")],
            annual_position=annual, annual_projection=projection or accepted_projection,
            membership_decision=decision or accepted_decision, current_membership_snapshot=membership,
            reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        )


def test_multi_employment_manual_evidence_composes_only_after_exact_binding():
    app = Flask(__name__); app.config["SECRET_KEY"] = "synthetic"
    result = compose_bridge(app)
    assert result.reconciliation.tax_paid_to_date == Decimal("2000.00")
    assert result.reconciliation.tax_paid_known is True
    assert result.future_pay_forecast is None


@pytest.mark.parametrize("entries", [
    [entry(1, "1200.00"), {**entry(1, "800.00"), "evidence_id": "manual-other"}],
    [entry(1, "1200.00"), {**entry(2, "800.00"), "evidence_id": "manual-1"}],
])
def test_duplicate_employment_slot_or_evidence_identity_fails_closed(entries):
    app = Flask(__name__); app.config["SECRET_KEY"] = "synthetic"
    with pytest.raises(ValueError, match="duplicated"):
        compose_bridge(app, entries=entries)


def test_absent_or_cross_owner_membership_and_unadmitted_annual_input_fail_closed():
    app = Flask(__name__); app.config["SECRET_KEY"] = "synthetic"
    annual, projection = admitted_annual()
    membership, decision = allowed_membership(app)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="membership"):
            compose_authenticated_manual_paye(
                entries=[entry(1, "1200.00")], annual_position=annual, annual_projection=projection,
                membership_decision=decision, current_membership_snapshot=InMemoryOwnerBusinessMembershipFake((), snapshot_version=1),
                reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
            )
        with pytest.raises(ValueError, match="tax year"):
            compose_authenticated_manual_paye(
                entries=[entry(1, "1200.00", tax_year="2025/26")], annual_position=annual, annual_projection=projection,
                membership_decision=decision, current_membership_snapshot=membership,
                reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
            )
