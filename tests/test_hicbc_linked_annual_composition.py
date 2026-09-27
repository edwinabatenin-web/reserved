"""Hostile synthetic contract tests for disabled linked annual HICBC composition."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Event

import pytest
from flask import Flask

import reserved.auth as auth
import reserved.database as db
import reserved.services.hicbc_linked_annual_composition as linked
from reserved.annual_position_durable_repository import DurableGovernance
from reserved.annual_position_repository_contract import (
    make_structural_candidate,
    prepare_annual_position_record,
)
from reserved.engines.annual_to_cash_integration import annual_to_cash_position_identity
from reserved.services.hicbc_linked_annual_composition import (
    LinkedAnnualLiveSource,
    compose_linked_durable_authenticated_hicbc_preview,
)
from reserved.services.w8_annual_cash_customer_handoff import (
    annual_to_cash_evidence_references,
    compose_w8_annual_cash_customer_handoff,
)
from reserved.services.w8_customer_result import (
    compose_w8_customer_result,
    w8_customer_result_identity,
)
from tests.test_annual_position_durable_repository import _membership, _repository
from tests.test_annual_to_cash_integration import AS_OF
from tests.test_hicbc_durable_annual_bridge import _live_annual


YEAR = "2026/27"
NATION = "England"
OWNER_BUSINESS = "business-owner"
PARTNER_BUSINESS = "business-partner"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "linked-annual.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setattr(linked, "_server_date", lambda: AS_OF)
    db.init_db()
    with db._connection() as conn:
        for user_id in (41, 42, 43):
            conn.execute(
                "INSERT INTO users (id,clerk_user_id,created_at) VALUES (?,?,?)",
                (user_id, f"user_{user_id}", "2026-09-27T00:00:00+00:00"),
            )
    memberships = (
        _membership(41, business=OWNER_BUSINESS),
        _membership(42, business=PARTNER_BUSINESS),
    )
    repository = _repository(memberships=memberships)
    tax, annual = _live_annual()
    source = LinkedAnnualLiveSource(annual, tax)
    governance = DurableGovernance(
        "retention:approved-policy-v1", "erasure:approved-disposition-v1",
        "crypto:approved-key-v1", "target:local-integration-v1",
    ).contract_handle()

    for user_id, business, membership in (
        (41, OWNER_BUSINESS, memberships[0]),
        (42, PARTNER_BUSINESS, memberships[1]),
    ):
        repository.register_owner_business_membership(
            user_id=user_id,
            business_reference=business,
            membership_authority=membership,
            audit_reference="audit:linked-hicbc-membership",
        )
        source_refs = annual_to_cash_evidence_references(annual)
        evidence_refs = ("annual:no-loan", "cash:deductions-credits", "charge:balancing")
        handoff = compose_w8_annual_cash_customer_handoff(
            annual, evidence_references=source_refs,
        )
        customer = compose_w8_customer_result(
            handoff.presentation_input,
            nation=NATION,
            tax_year=YEAR,
            user_id=str(user_id),
            business_id=business,
            evidence_references=evidence_refs,
        )
        presentation = customer.presentation_input
        candidate = make_structural_candidate(
            record_version=1,
            user_id=str(user_id),
            business_id=business,
            tax_year=YEAR,
            nation=NATION,
            annual_cash_identity=annual_to_cash_position_identity(annual),
            customer_result_identity=w8_customer_result_identity(customer),
            evidence_classification=presentation.evidence.value,
            annual_liability=f"{presentation.annual_liability:.2f}",
            obligations=tuple(
                (item.kind.value, f"{item.amount:.2f}", item.due_date.isoformat())
                for item in presentation.obligations
            ),
            adjustments=tuple(
                (item.kind.value, f"{item.amount:.2f}") for item in presentation.adjustments
            ),
            funding=presentation.funding.value,
            funding_amount=(
                None if presentation.funding_amount is None
                else f"{presentation.funding_amount:.2f}"
            ),
            evidence_references=evidence_refs,
            ruleset_version=annual.ruleset_version,
            as_of=annual.as_of.isoformat(),
            stale_after_days=45,
        )
        repository.create_or_read(
            authenticated_user_id=user_id,
            business_reference=business,
            record=prepare_annual_position_record(candidate, governance),
            audit_reference="audit:linked-hicbc-create",
        )

    db.save_hicbc_estimate(41, {
        "tax_year": YEAR,
        "child_benefit_claimant": "person",
        "child_benefit_annual": "1406.60",
        "has_relevant_partner": 1,
        "relationship_covers_full_year": 1,
        "partner_status_period_semantics": "status_answer_full_year",
        "representation": None,
        "completeness": "complete_for_purpose",
        "recency_state": "current",
        "confirmed_at": "2027-04-05",
        "observed_at": "2027-04-05",
    })
    token = db.create_hicbc_link_invitation(41, YEAR)
    assert db.accept_hicbc_link_invitation(42, token, YEAR)
    assert db.record_hicbc_link_consent(41, YEAR, db.HICBC_NOTICE_VERSION)
    assert db.record_hicbc_link_consent(42, YEAR, db.HICBC_NOTICE_VERSION)
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "synthetic"
    return app, repository, source


def _compose(setup, provider=None):
    app, repository, source = setup
    provider = provider or (lambda partner_id, tax_year, nation: source)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        return compose_linked_durable_authenticated_hicbc_preview(
            repository=repository,
            owner_source=source,
            partner_source_provider=provider,
            owner_business_reference=OWNER_BUSINESS,
            tax_year=YEAR,
            nation=NATION,
        )


def test_exact_linked_sources_return_only_receiving_users_own_result(setup):
    seen = []

    def provider(partner_id, tax_year, nation):
        seen.append((partner_id, tax_year, nation))
        return setup[2]

    result = _compose(setup, provider)
    assert seen == [(42, YEAR, NATION)]
    assert result.projected_user_hicbc == Decimal("703.00")
    assert result.public_value() == {
        "tax_year": YEAR,
        "calculation_status": "calculated",
        "responsibility_status": "person_liable",
        "projected_user_hicbc": "703.00",
        "possible_charge_low": "703.00",
        "possible_charge_high": "703.00",
    }
    serialized = repr(result.public_value()).casefold()
    assert all(word not in serialized for word in (
        "partner", "income", "ani", "source", "business", "user_42",
    ))


def test_other_participant_liability_is_projected_only_as_no_own_charge(setup):
    with db._connection() as conn:
        conn.execute(
            "UPDATE hicbc_estimates SET child_benefit_claimant='partner' "
            "WHERE user_id=41 AND tax_year=?",
            (YEAR,),
        )
    result = _compose(setup)
    assert result.projected_user_hicbc == Decimal("0.00")
    assert result.responsibility_status == "no_charge"
    assert "partner" not in repr(result.public_value()).casefold()


@pytest.mark.parametrize("mutation", ["withdraw", "wrong_notice", "extra_link"])
def test_missing_or_ambiguous_current_permission_fails_before_partner_read(setup, mutation):
    if mutation == "withdraw":
        assert db.revoke_hicbc_link(42, YEAR)
    elif mutation == "wrong_notice":
        with db._connection() as conn:
            conn.execute(
                "UPDATE hicbc_link_consents SET notice_version='obsolete' WHERE user_id=42"
            )
    else:
        with db._connection() as conn:
            conn.execute(
                "INSERT INTO hicbc_links "
                "(user_low_id,user_high_id,tax_year,purpose,status,initiator_id,"
                "permission_cycle,created_at,accepted_at) "
                "VALUES (41,43,?,'hicbc_responsibility','active',41,1,?,?)",
                (YEAR, "2026-09-27T00:00:00+00:00", "2026-09-27T00:00:00+00:00"),
            )
    calls = []
    result = _compose(setup, lambda *args: calls.append(args))
    assert result.projected_user_hicbc is None
    assert calls == []


def test_partner_is_derived_and_cannot_be_request_selected(setup):
    app, repository, source = setup
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(TypeError, match="unexpected keyword"):
            compose_linked_durable_authenticated_hicbc_preview(
                repository=repository,
                owner_source=source,
                partner_source_provider=lambda *_: source,
                owner_business_reference=OWNER_BUSINESS,
                tax_year=YEAR,
                nation=NATION,
                partner_id=43,
            )


def test_withdrawal_during_source_resolution_fails_final_atomic_recheck(setup):
    def provider(*_):
        assert db.revoke_hicbc_link(42, YEAR)
        return setup[2]

    result = _compose(setup, provider)
    assert result.public_value()["calculation_status"] == "insufficient_facts"
    assert result.projected_user_hicbc is None


def test_stale_or_conflicting_evidence_suppresses_result(setup, monkeypatch):
    monkeypatch.setattr(linked, "_server_date", lambda: AS_OF + timedelta(days=46))
    assert _compose(setup).projected_user_hicbc is None

    monkeypatch.setattr(linked, "_server_date", lambda: AS_OF)
    db.save_hicbc_estimate(41, {
        "tax_year": YEAR,
        "child_benefit_claimant": "person",
        "child_benefit_annual": "1406.60",
        "has_relevant_partner": 1,
        "relationship_covers_full_year": 1,
        "partner_status_period_semantics": "status_answer_full_year",
        "representation": "point",
        "partner_ani_point": "1000",
        "completeness": "complete_for_purpose",
        "recency_state": "current",
        "confirmed_at": "2027-04-05",
        "observed_at": "2027-04-05",
    })
    assert _compose(setup).projected_user_hicbc is None


def test_revocation_waits_for_final_permission_and_source_snapshot(setup, monkeypatch):
    entered = Event()
    release = Event()
    original = linked._responsibility_from_sources

    def pause(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(linked, "_responsibility_from_sources", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        composition = pool.submit(_compose, setup)
        assert entered.wait(timeout=5)
        revocation = pool.submit(db.revoke_hicbc_link, 42, YEAR)
        assert not revocation.done()
        release.set()
        result = composition.result(timeout=5)
        assert result.projected_user_hicbc == Decimal("703.00")
        assert revocation.result(timeout=5) is True
    assert _compose(setup).projected_user_hicbc is None


def test_service_has_no_route_activation_or_partner_financial_persistence(setup):
    with db._connection() as conn:
        before = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("annual_position_records", "hicbc_links", "hicbc_link_consents")
        }
    result = _compose(setup)
    assert result.projected_user_hicbc == Decimal("703.00")
    with db._connection() as conn:
        after = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in before
        }
        columns = [row[1] for row in conn.execute("PRAGMA table_info(hicbc_links)")]
    assert before == after
    assert all("ani" not in column and "income" not in column for column in columns)
