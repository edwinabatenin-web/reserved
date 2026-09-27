"""Focused trusted-source HICBC annual composition tests (no HTTP activation)."""

from datetime import date, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Event

import pytest
from flask import Flask

import reserved.auth as auth
import reserved.database as db
from reserved.annual_position_durable_repository import DurableAnnualPositionRepository, DurableGovernance
from reserved.annual_position_repository_contract import (
    make_structural_candidate,
    prepare_annual_position_record,
)
from reserved.engines.annual_to_cash_integration import annual_to_cash_position_identity
from reserved.engines.cash_ready_annual_position import (
    NoStudentLoanEvidence,
    annual_position_identity,
    compose_cash_ready_annual_position,
    student_loan_position_identity,
)
from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.hicbc_durable_annual_bridge import (
    _atomic_hicbc_row,
    compose_durable_authenticated_hicbc_preview,
)
from tests.test_annual_position_durable_repository import (
    _AuthorityAdapter, _governance, _membership, _policy, _repository,
)
from tests.test_annual_to_cash_integration import AS_OF, compose


YEAR = "2026/27"
NATION = "England"
BUSINESS = "business-1"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "hicbc-durable.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    with db._connection() as conn:
        for user_id in (41, 42):
            conn.execute(
                "INSERT INTO users (id,clerk_user_id,created_at) VALUES (?,?,?)",
                (user_id, f"user_{user_id}", "2026-09-27T00:00:00+00:00"),
            )
    application = Flask(__name__)
    application.config["SECRET_KEY"] = "synthetic"
    return application


def _live_annual():
    tax = calculate_annual_position({
        "employment_income": "70000",
        "country": NATION,
        "blind_persons_allowance_entitled": False,
        "blind_persons_allowance_transferred_in": "0",
        "blind_persons_allowance_transferred_out": "0",
    })
    loans = NoStudentLoanEvidence(
        "annual-no-loan", YEAR, "uk-2026-27-v4", AS_OF,
        "person-a", "synthetic", "synthetic:no-loan", True,
    )
    ready = compose_cash_ready_annual_position(
        tax, loans, annual_tax_reference=annual_position_identity(tax),
        student_loan_reference=student_loan_position_identity(loans), as_of=AS_OF,
    )
    return tax, compose(annual=ready)


def _durable(owner, *, permit_revocation=False):
    tax, annual = _live_annual()
    membership = _membership(owner, business=BUSINESS)
    authorities = (membership,)
    if permit_revocation:
        authorities += (_membership(owner, business=BUSINESS, state="revoked"),)
    repository = _repository(memberships=authorities)
    repository.register_owner_business_membership(
        user_id=owner, business_reference=BUSINESS, membership_authority=membership,
        audit_reference="audit:hicbc-membership",
    )
    governance = DurableGovernance(
        "retention:approved-policy-v1", "erasure:approved-disposition-v1",
        "crypto:approved-key-v1", "target:local-integration-v1",
    ).contract_handle()
    candidate = make_structural_candidate(
        record_version=1, user_id=str(owner), business_id=BUSINESS, tax_year=YEAR,
        nation=NATION, annual_cash_identity=annual_to_cash_position_identity(annual),
        customer_result_identity="w8-customer-result:sha256-" + "b" * 64,
        evidence_classification="qualified_local_estimate",
        annual_liability=str(annual.final_self_assessment_liability),
        obligations=(("balancing_payment", "15432.00", "2028-01-31"),
                     ("first_payment_on_account", "600.00", "2028-01-31"),
                     ("second_payment_on_account", "600.00", "2028-07-31")),
        adjustments=(("deductions_and_credits", "0.00"), ("prior_payments_on_account", "0.00"),
                     ("payments_made", "0.00"), ("credit_or_refund", "0.00")),
        funding="exact", funding_amount=None,
        evidence_references=("annual:no-loan", "cash:deductions-credits", "charge:balancing"),
        ruleset_version="uk-2026-27-v4", as_of="2027-04-05", stale_after_days=45,
    )
    record = prepare_annual_position_record(candidate, governance)
    repository.create_or_read(
        authenticated_user_id=owner, business_reference=BUSINESS, record=record,
        audit_reference="audit:hicbc-create",
    )
    return tax, annual, repository


def _seed(owner, **changes):
    facts = {
        "tax_year": YEAR, "child_benefit_claimant": "person",
        "child_benefit_annual": "1406.60", "has_relevant_partner": 1,
        "relationship_covers_full_year": 1,
        "partner_status_period_semantics": "status_answer_full_year",
        "representation": "point", "partner_ani_point": "50000",
        "completeness": "complete_for_purpose", "recency_state": "current",
        "confirmed_at": "2026-09-04", "observed_at": "2026-09-04",
    }
    facts.update(changes)
    db.save_hicbc_estimate(owner, facts)


def _compose(app, repository, annual, tax):
    return compose_durable_authenticated_hicbc_preview(
        repository=repository, annual_position=annual, annual_tax_position=tax,
        business_reference=BUSINESS, tax_year=YEAR, nation=NATION,
        clock=lambda: annual.as_of,
        audit_reference="audit:hicbc-read",
    )


def test_live_durable_annual_source_allows_only_minimal_determinate_hicbc(app):
    tax, annual, repository = _durable(41)
    _seed(41)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        result = _compose(app, repository, annual, tax)
    assert result.projected_user_hicbc == Decimal("703.00")
    assert result.public_value() == {
        "tax_year": YEAR, "calculation_status": "calculated",
        "responsibility_status": "person_liable", "projected_user_hicbc": "703.00",
        "possible_charge_low": "703.00", "possible_charge_high": "703.00",
    }
    assert not {"payment", "refund", "reserve", "source", "action"} & set(result.public_value())


def test_cross_owner_year_and_live_identity_substitution_fail_closed(app):
    tax, annual, repository = _durable(41)
    _seed(41)
    with app.test_request_context("/"):
        auth.set_user_session(42, "user_42")
        with pytest.raises(ValueError, match="durable annual position"):
            _compose(app, repository, annual, tax)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="scope"):
            compose_durable_authenticated_hicbc_preview(
                repository=repository, annual_position=annual, annual_tax_position=tax,
                business_reference=BUSINESS, tax_year="2025/26", nation=NATION,
                clock=lambda: annual.as_of,
                audit_reference="audit:hicbc-read",
            )
        other_tax = calculate_annual_position({"employment_income": "70001", "country": NATION})
        with pytest.raises(ValueError, match="identity"):
            _compose(app, repository, annual, other_tax)
        expired = compose_durable_authenticated_hicbc_preview(
            repository=repository, annual_position=annual, annual_tax_position=tax,
            business_reference=BUSINESS, tax_year=YEAR, nation=NATION,
            clock=lambda: annual.as_of + timedelta(days=46), audit_reference="audit:hicbc-read",
        )
    assert expired.projected_user_hicbc is None
    assert expired.possible_charge_low is None and expired.possible_charge_high is None
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="server clock"):
            compose_durable_authenticated_hicbc_preview(
                repository=repository, annual_position=annual, annual_tax_position=tax,
                business_reference=BUSINESS, tax_year=YEAR, nation=NATION,
                clock=lambda: "not-a-date", audit_reference="audit:hicbc-read",
            )


def test_missing_or_unavailable_external_verifier_cannot_read_persisted_hicbc(app):
    tax, annual, repository = _durable(41)
    _seed(41)
    no_adapter = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
        external_authority_adapter=None,
    )
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="current durable annual position"):
            _compose(app, no_adapter, annual, tax)

    class FalseAuthority(_AuthorityAdapter):
        def verify_evidence_reference_policy(self, policy):
            return False

    class UnavailableAuthority(_AuthorityAdapter):
        def verify_evidence_reference_policy(self, policy):
            raise RuntimeError("synthetic verifier outage")

    for adapter in (FalseAuthority(), UnavailableAuthority()):
        with pytest.raises(Exception):
            DurableAnnualPositionRepository(
                _governance(), evidence_reference_policy=_policy(),
                membership_issuer_reference="membership:approved-v1",
                lifecycle_issuer_reference="lifecycle:approved-v1",
                external_authority_adapter=adapter,
            )


def test_membership_revocation_prevents_every_subsequent_durable_hicbc_read(app):
    tax, annual, repository = _durable(41, permit_revocation=True)
    _seed(41)
    revoked = _membership(41, business=BUSINESS, state="revoked")
    repository.revoke_owner_business_membership(
        user_id=41, business_reference=BUSINESS, membership_authority=revoked,
        audit_reference="audit:hicbc-revoke-membership",
    )
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        with pytest.raises(ValueError, match="current durable annual position"):
            _compose(app, repository, annual, tax)


def test_uncertainty_and_active_link_suppress_amount_then_revocation_releases_new_read(app):
    tax, annual, repository = _durable(41)
    _seed(41, representation="range", partner_ani_point=None,
          partner_ani_low="65000", partner_ani_high="75000")
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        uncertain = _compose(app, repository, annual, tax)
    assert uncertain.projected_user_hicbc is None
    assert uncertain.public_value() == {
        "tax_year": YEAR, "calculation_status": "insufficient_facts",
        "responsibility_status": None, "projected_user_hicbc": None,
        "possible_charge_low": None, "possible_charge_high": None,
    }

    other = 42
    token = db.create_hicbc_link_invitation(41, YEAR)
    assert db.accept_hicbc_link_invitation(other, token, YEAR) is not None
    assert db.record_hicbc_link_consent(41, YEAR, db.HICBC_NOTICE_VERSION)
    assert db.record_hicbc_link_consent(other, YEAR, db.HICBC_NOTICE_VERSION)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        blocked = _compose(app, repository, annual, tax)
    assert blocked.projected_user_hicbc is None
    assert all(blocked.public_value()[key] is None for key in (
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    ))
    assert db.revoke_hicbc_link(other, YEAR)
    _seed(41, representation="point", partner_ani_point="50000")
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        released = _compose(app, repository, annual, tax)
    assert released.projected_user_hicbc == Decimal("703.00")


def test_stale_manual_evidence_and_duplicate_linked_profiles_cannot_create_output(app):
    tax, annual, repository = _durable(41)
    _seed(41, recency_state="stale")
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        stale = _compose(app, repository, annual, tax)
    assert stale.projected_user_hicbc is None
    assert all(stale.public_value()[key] is None for key in (
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    ))

    # The trusted annual bridge never reads a linked partner profile.  Even a
    # deliberately ambiguous duplicate profile cannot become a source; the
    # active link itself suppresses this calculation until revocation.
    db.save_profile_by_user(42, {"tax_year": YEAR, "income_estimate": 90000})
    with db._connection() as conn:
        conn.execute(
            "INSERT INTO user_profiles (session_key,updated_at,user_id,notes) VALUES (?,?,?,?)",
            ("duplicate-profile-42", "2026-09-27T00:00:00+00:00", 42, "{}"),
        )
    token = db.create_hicbc_link_invitation(41, YEAR)
    assert db.accept_hicbc_link_invitation(42, token, YEAR) is not None
    assert db.record_hicbc_link_consent(41, YEAR, db.HICBC_NOTICE_VERSION)
    assert db.record_hicbc_link_consent(42, YEAR, db.HICBC_NOTICE_VERSION)
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        blocked = _compose(app, repository, annual, tax)
    assert blocked.projected_user_hicbc is None
    assert all(blocked.public_value()[key] is None for key in (
        "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
    ))


def test_incomplete_hicbc_facts_return_the_same_uniform_unavailable_shape(app):
    tax, annual, repository = _durable(41)
    _seed(41, completeness="partial")
    with app.test_request_context("/"):
        auth.set_user_session(41, "user_41")
        result = _compose(app, repository, annual, tax)
    assert result.public_value() == {
        "tax_year": YEAR, "calculation_status": "insufficient_facts",
        "responsibility_status": None, "projected_user_hicbc": None,
        "possible_charge_low": None, "possible_charge_high": None,
    }


def test_atomic_snapshot_linearises_link_revocation(app):
    """A revoke begun after the snapshot cannot create a post-revoke result."""
    _, _, repository = _durable(41)
    _seed(41)
    token = db.create_hicbc_link_invitation(41, YEAR)
    assert db.accept_hicbc_link_invitation(42, token, YEAR) is not None
    assert db.record_hicbc_link_consent(41, YEAR, db.HICBC_NOTICE_VERSION)
    assert db.record_hicbc_link_consent(42, YEAR, db.HICBC_NOTICE_VERSION)
    with db._connection() as conn:
        record_identity = conn.execute(
            "SELECT record_identity FROM annual_position_records WHERE user_id=?", (41,)
        ).fetchone()[0]

    captured, release, revoke_started = Event(), Event(), Event()

    def hold_snapshot():
        captured.set()
        assert release.wait(2)

    def revoke_after_signal():
        revoke_started.set()
        return db.revoke_hicbc_link(42, YEAR)

    with ThreadPoolExecutor(max_workers=2) as pool:
        snapshot = pool.submit(
            _atomic_hicbc_row,
            repository=repository,
            owner=41,
            business_reference=BUSINESS,
            tax_year=YEAR,
            durable_record_identity=record_identity,
            _after_read=hold_snapshot,
        )
        assert captured.wait(2)
        revocation = pool.submit(revoke_after_signal)
        assert revoke_started.wait(2)
        with pytest.raises(FutureTimeoutError):
            revocation.result(timeout=.1)
        release.set()
        assert snapshot.result(timeout=2)[1] is True
        assert revocation.result(timeout=2) is True
    assert _atomic_hicbc_row(
        repository=repository,
        owner=41, business_reference=BUSINESS, tax_year=YEAR,
        durable_record_identity=record_identity,
    )[1] is False
