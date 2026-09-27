"""Focused hostile tests for the W9 physical annual-position repository."""

from __future__ import annotations

import sqlite3
import threading

import pytest

import reserved.database as db
import reserved.annual_position_durable_repository as durable_module
from reserved.annual_position_durable_repository import (
    AccountErasureClearance,
    ApprovedEvidenceReferencePolicy,
    DurableAnnualPositionError,
    DurableAnnualPositionRepository,
    DurableGovernance,
    ExternalAuthorityAdapter,
    MembershipAuthorityEvidence,
)
from reserved.annual_position_repository_contract import (
    make_structural_candidate,
    prepare_annual_position_record,
    project_annual_position_record,
    structural_candidate_identity,
)


@pytest.fixture
def prepared_db(tmp_path, monkeypatch):
    path = tmp_path / "annual-position.db"
    monkeypatch.setattr(db, "_DB_FILE", path)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return path


def _governance():
    return DurableGovernance(
        retention_policy_version="retention:approved-policy-v1",
        erasure_disposition="erasure:approved-disposition-v1",
        crypto_key_version="crypto:approved-key-v1",
        target_profile="target:local-integration-v1",
    )


def _policy():
    return ApprovedEvidenceReferencePolicy(
        issuer_reference="evidence-policy:approved-v1", policy_version="policy-v1",
        allowed_references=("annual:no-loan", "cash:deductions-credits", "charge:balancing"),
    )


class _AuthorityAdapter(ExternalAuthorityAdapter):
    authority_identity = "authority:external-test-v1"

    def __init__(self, *, memberships=(), clearances=(), policies=()):
        self.memberships = set(memberships)
        self.clearances = set(clearances)
        self.policies = set(policies)

    def verify_membership_authority(self, evidence):
        return evidence in self.memberships

    def verify_account_erasure_clearance(self, clearance):
        return clearance in self.clearances

    def verify_evidence_reference_policy(self, policy):
        return policy in self.policies


def _repository(*, memberships=(), clearances=(), policy=None):
    policy = _policy() if policy is None else policy
    return DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=policy,
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
        external_authority_adapter=_AuthorityAdapter(
            memberships=memberships, clearances=clearances, policies=(policy,),
        ),
    )


def _membership(user_id, *, business="business-1", state="active", version=1,
                expires_at="2030-01-01T00:00:00+00:00"):
    return MembershipAuthorityEvidence(
        issuer_reference="membership:approved-v1", owner_user_id=user_id,
        business_reference=business, membership_reference=f"membership-{user_id}-{version}",
        membership_version=version, state=state, issued_at="2026-09-01T00:00:00+00:00",
        expires_at=expires_at,
        revoked_at="2026-09-02T00:00:00+00:00" if state == "revoked" else None,
    )


def _clearance(user_id, kind, *, state="current", expires_at="2030-01-01T00:00:00+00:00"):
    return AccountErasureClearance(
        issuer_reference="lifecycle:approved-v1", clearance_kind=kind, purpose="account_erasure",
        owner_user_id=user_id, account_reference=str(user_id), state=state,
        issued_at="2026-09-01T00:00:00+00:00", expires_at=expires_at,
        revoked_at="2026-09-02T00:00:00+00:00" if state == "revoked" else None,
    )


def _record(*, user_id: int, version=1, predecessor=None, liability="3486.00",
            evidence_references=("annual:no-loan", "cash:deductions-credits", "charge:balancing")):
    governance = _governance().contract_handle()
    candidate = make_structural_candidate(
        record_version=version,
        user_id=str(user_id), business_id="business-1", tax_year="2026/27", nation="England",
        annual_cash_identity="annual-to-cash-position:sha256-" + "a" * 64,
        customer_result_identity="w8-customer-result:sha256-" + "b" * 64,
        evidence_classification="qualified_local_estimate", annual_liability=liability,
        obligations=(("balancing_payment", liability, "2028-01-31"),
                     ("first_payment_on_account", "600.00", "2028-01-31"),
                     ("second_payment_on_account", "600.00", "2028-07-31")),
        adjustments=(("deductions_and_credits", "0.00"), ("prior_payments_on_account", "0.00"),
                     ("payments_made", "0.00"), ("credit_or_refund", "0.00")),
        funding="exact", funding_amount=None,
        evidence_references=evidence_references,
        ruleset_version="uk-2026-27-v4", as_of="2027-04-05", stale_after_days=45,
        predecessor_identity=predecessor,
    )
    return prepare_annual_position_record(candidate, governance), structural_candidate_identity(candidate)


def _user(label="owner"):
    return db.get_or_create_user(label, email=f"{label}@example.test", display_name=label)


def test_create_read_and_atomic_supersession_are_owner_bound(prepared_db):
    owner, other = _user("owner"), _user("other")
    membership = _membership(owner)
    repository = _repository(memberships=(membership,))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    initial, identity = _record(user_id=owner)
    assert repository.create_or_read(authenticated_user_id=owner, business_reference="business-1",
                                     record=initial, audit_reference="audit:create") == identity
    assert repository.create_or_read(authenticated_user_id=owner, business_reference="business-1",
                                     record=initial, audit_reference="audit:replay") == identity
    with pytest.raises(DurableAnnualPositionError, match="membership"):
        repository.read_current(authenticated_user_id=other, business_reference="business-1",
                                tax_year="2026/27", nation="England",
                                record_purpose="annual_cash_position_durable_projection",
                                audit_reference="audit:cross-owner")
    successor, successor_identity = _record(user_id=owner, version=2, predecessor=identity, liability="3600.00")
    assert repository.supersede(authenticated_user_id=owner, business_reference="business-1", record=successor,
                                expected_current_identity=identity, audit_reference="audit:supersede") == successor_identity
    with pytest.raises(DurableAnnualPositionError, match="compare-and-swap"):
        repository.supersede(authenticated_user_id=owner, business_reference="business-1", record=successor,
                             expected_current_identity=identity, audit_reference="audit:stale-cas")
    read = repository.read_current(authenticated_user_id=owner, business_reference="business-1",
                                   tax_year="2026/27", nation="England",
                                   record_purpose="annual_cash_position_durable_projection", audit_reference="audit:read")
    assert project_annual_position_record(read) == project_annual_position_record(successor)


def test_unsettled_governance_and_erasures_fail_closed(prepared_db):
    with pytest.raises(DurableAnnualPositionError, match="unresolved"):
        DurableAnnualPositionRepository(
            DurableGovernance("retention:unresolved", "erasure:approved", "crypto:approved", "target:approved"),
            evidence_reference_policy=_policy(), membership_issuer_reference="membership:approved-v1",
            lifecycle_issuer_reference="lifecycle:approved-v1",
        )
    owner = _user()
    membership = _membership(owner)
    legal = _clearance(owner, "legal_hold_clear")
    backup = _clearance(owner, "backup_expiry_confirmed")
    repository = _repository(memberships=(membership,), clearances=(legal, backup))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, _ = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    assert len(repository.plan_account_erasure(authenticated_user_id=owner, audit_reference="audit:erasure-plan")) == 1
    with pytest.raises(DurableAnnualPositionError, match="clearance"):
        repository.execute_account_erasure(authenticated_user_id=owner, audit_reference="audit:erase",
                                           legal_hold_clearance="legal-hold:pending", backup_expiry_clearance=backup)
    assert repository.execute_account_erasure(authenticated_user_id=owner, audit_reference="audit:erase",
                                              legal_hold_clearance=legal, backup_expiry_clearance=backup) == 1
    with pytest.raises(DurableAnnualPositionError, match="unavailable"):
        repository.read_current(authenticated_user_id=owner, business_reference="business-1",
                                tax_year="2026/27", nation="England",
                                record_purpose="annual_cash_position_durable_projection", audit_reference="audit:read-deleted")
    with db._connection() as conn:
        assert conn.execute("SELECT count(*) FROM annual_position_evidence_references").fetchone()[0] == 0
        # No raw source column exists; only canonical envelope storage is present.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(annual_position_records)")}
    assert "raw_payslip" not in columns and "provider_payload" not in columns


def test_read_is_purpose_scoped_and_rejects_governance_tampering(prepared_db):
    owner = _user()
    membership = _membership(owner)
    repository = _repository(memberships=(membership,))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, identity = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    with db._connection() as conn:
        # A foreign purpose in the same owner/year/nation cannot be selected by
        # the annual-position read query, even if it is marked current.
        conn.execute(
            "INSERT INTO annual_position_records "
            "(record_identity,user_id,business_reference,tax_year,nation,record_purpose,record_version,"
            "governance_fingerprint,envelope_json,envelope_sha256,state,created_at) "
            "SELECT ?,user_id,business_reference,tax_year,nation,'other_projection',record_version,"
            "governance_fingerprint,envelope_json,envelope_sha256,'current',created_at "
            "FROM annual_position_records WHERE record_identity=?",
            ("annual-position-structural:sha256-" + "f" * 64, identity),
        )
    assert repository.read_current(
        authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
        record_purpose="annual_cash_position_durable_projection", audit_reference="audit:purpose-read",
    )
    with pytest.raises(DurableAnnualPositionError, match="purpose"):
        repository.read_current(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
            record_purpose="other_projection", audit_reference="audit:foreign-purpose",
        )
    with db._connection() as conn:
        conn.execute("UPDATE annual_position_records SET governance_fingerprint='annual-position-governance:sha256-" + "0" * 64 + "' WHERE record_identity=?", (identity,))
    with pytest.raises(DurableAnnualPositionError, match="governance profile"):
        repository.read_current(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
            record_purpose="annual_cash_position_durable_projection", audit_reference="audit:governance-tamper",
        )


def test_membership_authority_preemption_cross_owner_and_revocation(prepared_db):
    owner, other = _user("owner"), _user("other")
    evidence = _membership(owner)
    revoked = _membership(owner, state="revoked")
    other_evidence = _membership(other)
    successor_evidence = _membership(owner, version=2)
    repository = _repository(memberships=(evidence, revoked, other_evidence, successor_evidence))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=evidence,
        audit_reference="audit:membership-create",
    )
    with pytest.raises(DurableAnnualPositionError, match="already owned or unavailable"):
        repository.register_owner_business_membership(
            user_id=other, business_reference="business-1", membership_authority=other_evidence,
            audit_reference="audit:cross-owner-register",
        )
    with pytest.raises(DurableAnnualPositionError, match="already owned"):
        repository.register_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=successor_evidence,
            audit_reference="audit:preempt-version",
        )
    repository.revoke_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=revoked,
        audit_reference="audit:membership-revoke",
    )
    record, _ = _record(user_id=owner)
    with pytest.raises(DurableAnnualPositionError, match="active owner-to-business"):
        repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                                  audit_reference="audit:revoked-write")


def test_evidence_allowlist_and_read_access_audit_are_enforced(prepared_db):
    owner = _user()
    membership = _membership(owner)
    repository = _repository(memberships=(membership,))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, _ = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    repository.read_current(
        authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
        record_purpose="annual_cash_position_durable_projection", audit_reference="audit:read-access",
    )
    with db._connection() as conn:
        rows = conn.execute("SELECT user_id,business_reference,audit_reference FROM annual_position_read_audit").fetchall()
    assert [tuple(row) for row in rows] == [(owner, "business-1", "audit:read-access")]
    forged, _ = _record(user_id=owner, evidence_references=("unapproved:field",))
    with pytest.raises(DurableAnnualPositionError, match="unapproved evidence"):
        repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=forged,
                                  audit_reference="audit:hostile-evidence")


def test_forged_clearance_object_cannot_execute_erasure(prepared_db):
    owner = _user()
    backup = _clearance(owner, "backup_expiry_confirmed")
    repository = _repository(clearances=(backup,))
    forged = AccountErasureClearance(
        "lifecycle:approved-v1", "legal_hold_clear", "account_erasure", owner, str(owner),
        "2026-09-01T00:00:00+00:00", "2030-01-01T00:00:00+00:00", "current",
    )
    with pytest.raises(DurableAnnualPositionError, match="independent verification"):
        repository.execute_account_erasure(
            authenticated_user_id=owner, audit_reference="audit:forged-clearance",
            legal_hold_clearance=forged, backup_expiry_clearance=backup,
        )


def test_no_local_issuer_factories_are_exported_or_available():
    forbidden = {
        "issue_membership_authority_evidence", "issue_account_erasure_clearance",
        "issue_approved_evidence_reference_policy",
    }
    assert forbidden.isdisjoint(durable_module.__all__)
    assert all(not hasattr(durable_module, name) for name in forbidden)
    assert {"ExternalAuthorityAdapter", "MembershipAuthorityEvidence", "AccountErasureClearance"} <= set(durable_module.__all__)


def test_without_external_verifier_mutating_authority_operations_are_inert(prepared_db):
    owner = _user()
    membership = _membership(owner)
    legal, backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    repository = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1", lifecycle_issuer_reference="lifecycle:approved-v1",
    )
    with pytest.raises(DurableAnnualPositionError, match="operation is disabled"):
        repository.register_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=membership,
            audit_reference="audit:disabled-register",
        )
    with pytest.raises(DurableAnnualPositionError, match="operation is disabled"):
        repository.revoke_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=_membership(owner, state="revoked"),
            audit_reference="audit:disabled-revoke",
        )
    with pytest.raises(DurableAnnualPositionError, match="operation is disabled"):
        repository.execute_account_erasure(
            authenticated_user_id=owner, audit_reference="audit:disabled-erasure",
            legal_hold_clearance=legal, backup_expiry_clearance=backup,
        )


def test_expired_membership_blocks_read_and_write(prepared_db):
    owner = _user()
    membership = _membership(owner)
    legal, backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    repository = _repository(memberships=(membership,), clearances=(legal, backup))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, identity = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    with db._connection() as conn:
        conn.execute("UPDATE owner_business_memberships SET authority_expires_at='2026-09-01T00:00:00+00:00'")
    with pytest.raises(DurableAnnualPositionError, match="has expired"):
        repository.read_current(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
            record_purpose="annual_cash_position_durable_projection", audit_reference="audit:expired-read",
        )
    successor, _ = _record(user_id=owner, version=2, predecessor=identity)
    with pytest.raises(DurableAnnualPositionError, match="has expired"):
        repository.supersede(authenticated_user_id=owner, business_reference="business-1", record=successor,
                             expected_current_identity=identity, audit_reference="audit:expired-write")
    assert repository.plan_account_erasure(authenticated_user_id=owner, audit_reference="audit:expired-erasure-plan") == (identity,)
    assert repository.execute_account_erasure(
        authenticated_user_id=owner, audit_reference="audit:expired-erasure",
        legal_hold_clearance=legal, backup_expiry_clearance=backup,
    ) == 1


def test_externally_verified_membership_renewal_and_revocation_race_semantics(prepared_db):
    owner = _user()
    initial = _membership(owner, version=1)
    renewal = _membership(owner, version=2, expires_at="2031-01-01T00:00:00+00:00")
    revoke_v1 = _membership(owner, version=1, state="revoked")
    revoke_v2 = _membership(owner, version=2, state="revoked")
    legal, backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    repository = _repository(memberships=(initial, renewal, revoke_v1, revoke_v2), clearances=(legal, backup))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=initial,
        audit_reference="audit:membership-create",
    )
    record, identity = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create-before-revoke")
    repository.renew_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=renewal,
        audit_reference="audit:membership-renew",
    )
    with db._connection() as conn:
        assert tuple(conn.execute("SELECT membership_version,authority_expires_at,status FROM owner_business_memberships").fetchone()) == (2, "2031-01-01T00:00:00+00:00", "active")
    # Renewal won the transaction; an older revocation cannot revoke the newer authority.
    with pytest.raises(DurableAnnualPositionError, match="stale or unavailable"):
        repository.revoke_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=revoke_v1,
            audit_reference="audit:stale-revoke",
        )
    repository.revoke_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=revoke_v2,
        audit_reference="audit:current-revoke",
    )
    with pytest.raises(DurableAnnualPositionError, match="revoked or unavailable"):
        repository.renew_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=renewal,
            audit_reference="audit:renew-after-revoke",
        )
    with pytest.raises(DurableAnnualPositionError, match="active owner-to-business"):
        repository.read_current(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27", nation="England",
            record_purpose="annual_cash_position_durable_projection", audit_reference="audit:revoked-read",
        )
    assert repository.plan_account_erasure(authenticated_user_id=owner, audit_reference="audit:revoked-erasure-plan") == (identity,)
    assert repository.execute_account_erasure(
        authenticated_user_id=owner, audit_reference="audit:revoked-erasure",
        legal_hold_clearance=legal, backup_expiry_clearance=backup,
    ) == 1


def test_expired_membership_renewal_requires_separate_restoration_authority(prepared_db):
    owner = _user()
    initial = _membership(owner)
    renewal = _membership(owner, version=2)
    repository = _repository(memberships=(initial, renewal))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=initial,
        audit_reference="audit:membership-create",
    )
    with db._connection() as conn:
        conn.execute("UPDATE owner_business_memberships SET authority_expires_at='2026-09-01T00:00:00+00:00'")
    with pytest.raises(DurableAnnualPositionError, match="expired membership cannot be renewed"):
        repository.renew_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=renewal,
            audit_reference="audit:expired-renew",
        )


def test_cross_owner_erasure_is_scoped_to_historically_authenticated_owner(prepared_db):
    owner, other = _user("owner"), _user("other")
    membership = _membership(owner)
    owner_legal, owner_backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    other_legal, other_backup = _clearance(other, "legal_hold_clear"), _clearance(other, "backup_expiry_confirmed")
    repository = _repository(
        memberships=(membership,), clearances=(owner_legal, owner_backup, other_legal, other_backup),
    )
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, identity = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    assert repository.plan_account_erasure(authenticated_user_id=other, audit_reference="audit:other-plan") == ()
    assert repository.execute_account_erasure(
        authenticated_user_id=other, audit_reference="audit:other-erase",
        legal_hold_clearance=other_legal, backup_expiry_clearance=other_backup,
    ) == 0
    # Owner's historical record is untouched by the other owner's lifecycle request.
    assert repository.plan_account_erasure(authenticated_user_id=owner, audit_reference="audit:owner-plan") == (identity,)


def _insert_paye_row(user_id: int, *, evidence_id: str) -> None:
    """Insert minimised already-admitted PAYE storage for erasure-scope tests."""
    with db._connection() as conn:
        conn.execute(
            """INSERT INTO paye_manual_entries
               (user_id,tax_year,employment_slot,evidence_id,source_kind,provenance,
                gross_to_date,tax_paid_to_date,tax_code,pay_frequency,pension_treatment,
                effective_through,observed_on,completeness,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, "2026/27", 1, evidence_id, "customer_confirmed_manual",
             "manual-customer-confirmed", "100.00", "10.00", "1257L", "monthly",
             "net_pay", "2026-09-01", "2026-09-02", "partial", "2026-09-02T00:00:00+00:00"),
        )


def test_cleared_local_tax_data_erasure_physically_deletes_owned_paye_and_annual_rows(prepared_db):
    owner = _user()
    membership = _membership(owner)
    legal = _clearance(owner, "legal_hold_clear")
    backup = _clearance(owner, "backup_expiry_confirmed")
    repository = _repository(memberships=(membership,), clearances=(legal, backup))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, identity = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    successor, _ = _record(user_id=owner, version=2, predecessor=identity, liability="3600.00")
    repository.supersede(
        authenticated_user_id=owner, business_reference="business-1", record=successor,
        expected_current_identity=identity, audit_reference="audit:supersede",
    )
    _insert_paye_row(owner, evidence_id="paye-owner-1")

    result = repository.execute_local_tax_data_erasure(
        authenticated_user_id=owner, audit_reference="audit:local-physical-erasure",
        legal_hold_clearance=legal, backup_expiry_clearance=backup,
    )
    assert result.annual_position_records == 2
    assert result.paye_manual_entries == 1
    with db._connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?", (owner,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM annual_position_evidence_references WHERE record_identity=?", (identity,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM annual_position_lifecycle_events WHERE user_id=?", (owner,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM annual_position_read_audit WHERE user_id=?", (owner,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?", (owner,)).fetchone()[0] == 0
        # Authentication identity is intentionally outside this bounded local-tax erasure.
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id=?", (owner,)).fetchone()[0] == 1


def test_local_tax_data_erasure_cannot_cross_owner_boundary(prepared_db):
    owner, other = _user("owner"), _user("other")
    membership = _membership(owner)
    owner_legal, owner_backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    other_legal, other_backup = _clearance(other, "legal_hold_clear"), _clearance(other, "backup_expiry_confirmed")
    repository = _repository(
        memberships=(membership,), clearances=(owner_legal, owner_backup, other_legal, other_backup),
    )
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, _ = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    _insert_paye_row(owner, evidence_id="paye-owner-1")

    result = repository.execute_local_tax_data_erasure(
        authenticated_user_id=other, audit_reference="audit:other-local-erasure",
        legal_hold_clearance=other_legal, backup_expiry_clearance=other_backup,
    )
    assert (result.annual_position_records, result.paye_manual_entries) == (0, 0)
    with db._connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?", (owner,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?", (owner,)).fetchone()[0] == 1


@pytest.mark.parametrize(
    "clearance",
    (
        lambda owner: _clearance(owner, "legal_hold_clear", expires_at="2026-09-02T00:00:00+00:00"),
        lambda owner: _clearance(owner, "backup_expiry_confirmed", state="revoked"),
    ),
    ids=("expired", "revoked"),
)
def test_local_tax_data_erasure_rejects_expired_or_revoked_clearance(prepared_db, clearance):
    owner = _user()
    membership = _membership(owner)
    legal = _clearance(owner, "legal_hold_clear")
    backup = _clearance(owner, "backup_expiry_confirmed")
    rejected = clearance(owner)
    if rejected.clearance_kind == "legal_hold_clear":
        legal = rejected
    else:
        backup = rejected
    repository = _repository(memberships=(membership,), clearances=(legal, backup))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=membership,
        audit_reference="audit:membership-create",
    )
    record, _ = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1", record=record,
                              audit_reference="audit:create")
    _insert_paye_row(owner, evidence_id="paye-owner-1")

    with pytest.raises(DurableAnnualPositionError, match="not current"):
        repository.execute_local_tax_data_erasure(
            authenticated_user_id=owner, audit_reference="audit:rejected-local-erasure",
            legal_hold_clearance=legal, backup_expiry_clearance=backup,
        )
    with db._connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?", (owner,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?", (owner,)).fetchone()[0] == 1


def test_local_tax_data_erasure_is_disabled_without_external_verifier(prepared_db):
    owner = _user()
    legal = _clearance(owner, "legal_hold_clear")
    backup = _clearance(owner, "backup_expiry_confirmed")
    repository = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1", lifecycle_issuer_reference="lifecycle:approved-v1",
    )
    with pytest.raises(DurableAnnualPositionError, match="operation is disabled"):
        repository.execute_local_tax_data_erasure(
            authenticated_user_id=owner, audit_reference="audit:disabled-local-erasure",
            legal_hold_clearance=legal, backup_expiry_clearance=backup,
        )


def _create_v11_fixture(path):
    """Create a minimal on-disk v11 application database, not a fresh v12 one."""
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version VALUES (11);
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clerk_user_id TEXT NOT NULL UNIQUE,
                email TEXT,
                display_name TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def _v12_schema_objects(path):
    with sqlite3.connect(path) as conn:
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        objects = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE name IN "
                "('owner_business_memberships','annual_position_records','annual_position_evidence_references',"
                "'annual_position_lifecycle_events','annual_position_read_audit','annual_position_one_current_head')"
            )
        }
    return version, objects


def test_v11_upgrade_failure_does_not_stamp_and_retry_completes(tmp_path, monkeypatch):
    path = tmp_path / "v11-upgrade.db"
    _create_v11_fixture(path)
    monkeypatch.setattr(db, "_DB_FILE", path)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    bad = list(db._MIGRATIONS[12])
    bad[2] = "CREATE INDEX invalid annual_position_fail"
    with monkeypatch.context() as scoped:
        scoped.setitem(db._MIGRATIONS, 12, bad)
        with pytest.raises(sqlite3.OperationalError):
            db.init_db()
    assert _v12_schema_objects(path)[0] == 11
    db.init_db()
    version, objects = _v12_schema_objects(path)
    assert version == db._SCHEMA_VERSION == 15
    assert objects == {
        "owner_business_memberships", "annual_position_records", "annual_position_evidence_references",
        "annual_position_lifecycle_events", "annual_position_read_audit", "annual_position_one_current_head",
    }
    with sqlite3.connect(path) as conn:
        membership_columns = {row[1] for row in conn.execute("PRAGMA table_info(owner_business_memberships)")}
    assert "authority_expires_at" in membership_columns


def test_fresh_schema_has_v12_current_head_control(prepared_db):
    version, objects = _v12_schema_objects(prepared_db)
    with sqlite3.connect(prepared_db) as conn:
        index = conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='annual_position_one_current_head'").fetchone()[0]
    assert version == db._SCHEMA_VERSION == 15
    assert objects == {
        "owner_business_memberships", "annual_position_records", "annual_position_evidence_references",
        "annual_position_lifecycle_events", "annual_position_read_audit", "annual_position_one_current_head",
    }
    with sqlite3.connect(prepared_db) as conn:
        membership_columns = {row[1] for row in conn.execute("PRAGMA table_info(owner_business_memberships)")}
    assert "authority_expires_at" in membership_columns
    assert "WHERE state = 'current'" in index


def test_serialized_paye_snapshot_blocks_revocation_then_later_snapshot_fails(prepared_db, monkeypatch):
    owner = _user("snapshot-owner")
    active = _membership(owner)
    revoked = _membership(owner, state="revoked")
    repository = _repository(memberships=(active, revoked))
    repository.register_owner_business_membership(
        user_id=owner, business_reference="business-1", membership_authority=active,
        audit_reference="audit:snapshot-membership",
    )
    record, _ = _record(user_id=owner)
    repository.create_or_read(authenticated_user_id=owner, business_reference="business-1",
                              record=record, audit_reference="audit:snapshot-create")
    _insert_paye_row(owner, evidence_id="paye-snapshot-1")

    entered, release, revoked_done = threading.Event(), threading.Event(), threading.Event()
    original = DurableAnnualPositionRepository._active_membership
    calls = {"count": 0}

    def hold_first(conn, user_id, business_reference):
        original(conn, user_id, business_reference)
        calls["count"] += 1
        if calls["count"] == 1:
            entered.set()
            assert release.wait(5)

    monkeypatch.setattr(DurableAnnualPositionRepository, "_active_membership", staticmethod(hold_first))
    output = []

    def read_snapshot():
        output.append(repository.read_current_paye_snapshot(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27",
            nation="England", record_purpose="annual_cash_position_durable_projection",
            audit_reference="audit:snapshot-read",
        ))

    def revoke():
        repository.revoke_owner_business_membership(
            user_id=owner, business_reference="business-1", membership_authority=revoked,
            audit_reference="audit:snapshot-revoke",
        )
        revoked_done.set()

    reader = threading.Thread(target=read_snapshot)
    reader.start(); assert entered.wait(5)
    revoker = threading.Thread(target=revoke)
    revoker.start()
    assert not revoked_done.wait(0.2)
    release.set(); reader.join(5); revoker.join(5)
    assert len(output) == 1 and revoked_done.is_set()
    with pytest.raises(DurableAnnualPositionError, match="membership"):
        repository.read_current_paye_snapshot(
            authenticated_user_id=owner, business_reference="business-1", tax_year="2026/27",
            nation="England", record_purpose="annual_cash_position_durable_projection",
            audit_reference="audit:snapshot-after-revoke",
        )
