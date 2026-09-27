"""Synthetic request tests for the dormant bounded local-erasure installer."""

from __future__ import annotations

import pytest
from flask import session
from flask_wtf.csrf import generate_csrf

from reserved import create_app
import reserved.database as db
from reserved.auth import _SK_USER_ID
from reserved.annual_position_durable_repository import (
    AccountErasureClearance, ApprovedEvidenceReferencePolicy,
    DurableAnnualPositionRepository, DurableGovernance, ExternalAuthorityAdapter,
)
from reserved.services.local_tax_data_erasure import (
    LocalTaxDataErasureInstallationError, install_local_tax_data_erasure,
)
from reserved.services.paye_payslip_intake import PayslipIntakeBoundary


class _Authority(ExternalAuthorityAdapter):
    authority_identity = "authority:route-test-v1"

    def __init__(self, clearances, policy):
        self.clearances, self.policy = set(clearances), policy

    def verify_membership_authority(self, evidence):
        return False

    def verify_account_erasure_clearance(self, clearance):
        return clearance in self.clearances

    def verify_evidence_reference_policy(self, policy):
        return policy == self.policy


def _clearance(owner, kind):
    return AccountErasureClearance(
        issuer_reference="lifecycle:route-test-v1", clearance_kind=kind,
        purpose="account_erasure", owner_user_id=owner, account_reference=str(owner),
        state="current", issued_at="2026-09-01T00:00:00+00:00",
        expires_at="2030-01-01T00:00:00+00:00",
    )


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "route.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("LOCAL_TAX_DATA_ERASURE_ENABLED", raising=False)
    app = create_app(); app.config.update(TESTING=True)
    owner = db.get_or_create_user("route-owner", email="owner@example.test")
    other = db.get_or_create_user("route-other", email="other@example.test")
    legal, backup = _clearance(owner, "legal_hold_clear"), _clearance(owner, "backup_expiry_confirmed")
    policy = ApprovedEvidenceReferencePolicy(
        issuer_reference="evidence-policy:route-test-v1", policy_version="v1", allowed_references=(),
    )
    repository = DurableAnnualPositionRepository(
        DurableGovernance("retention:route-test-v1", "erasure:route-test-v1", "crypto:route-test-v1", "target:route-test-v1"),
        evidence_reference_policy=policy, membership_issuer_reference="membership:route-test-v1",
        lifecycle_issuer_reference="lifecycle:route-test-v1",
        external_authority_adapter=_Authority((legal, backup), policy),
    )
    boundary = PayslipIntakeBoundary(tmp_path / "payslips", enabled=True)
    return app, owner, other, repository, boundary, (legal, backup)


def _client(app, owner):
    client = app.test_client()
    with app.test_request_context():
        token = generate_csrf()
        secret = session["csrf_token"]
    with client.session_transaction() as stored:
        stored[_SK_USER_ID] = owner
        stored["csrf_token"] = secret
    return client, token


def _install(app, repository, boundary, clearances, calls):
    def provider(*, authenticated_user_id):
        calls.append(authenticated_user_id)
        return clearances
    install_local_tax_data_erasure(
        app, durable_repository=repository, payslip_boundary=boundary, clearance_provider=provider,
    )


def test_disabled_and_csrf_rejections_never_consult_clearance_provider(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 404
    assert calls == []

    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    # A route with no CSRF token is stopped by the application's global guard.
    client2 = app.test_client()
    with client2.session_transaction() as stored:
        stored[_SK_USER_ID] = owner
    assert client2.post("/v2/account/local-tax-data-erasure", data={}).status_code == 400
    assert calls == []


def test_enabled_route_erases_owned_raw_first_and_reports_only_local_scope(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    handle = boundary.begin(authenticated_user_id=owner, session_binding="route-session-1",
                            tax_year="2026/27", content_type="application/pdf", document_bytes=b"%PDF-1.7\nsynthetic")
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    response = client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token})
    assert response.status_code == 200
    assert calls == [owner]
    assert response.get_json() == {
        "status": "local_tax_data_erased", "scope": "local_tax_data_only",
        "raw_payslip_files_deleted": 1, "annual_position_records_deleted": 0,
        "paye_manual_entries_deleted": 0, "backup_erasure": "not_asserted",
        "identity_erasure": "not_asserted", "quarantine_erasure": "not_asserted",
    }
    with db._connection() as conn:
        assert conn.execute("SELECT 1 FROM paye_payslip_intakes WHERE storage_id=?", (handle.intake_id,)).fetchone() is None


def test_bad_raw_identity_stops_before_structured_erasure(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    handle = boundary.begin(authenticated_user_id=owner, session_binding="route-session-2",
                            tax_year="2026/27", content_type="application/pdf", document_bytes=b"%PDF-1.7\nsynthetic")
    _, record = boundary._owned_record(handle=handle, authenticated_user_id=owner,
                                       session_binding="route-session-2", tax_year="2026/27")
    path = record.path
    path.unlink(); path.write_bytes(b"%PDF-1.7\nreplacement")
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 409
    assert calls == [owner]
    with db._connection() as conn:
        assert conn.execute("SELECT 1 FROM paye_payslip_intakes WHERE storage_id=?", (handle.intake_id,)).fetchone() is not None


def test_invalid_or_duplicate_installation_does_not_mutate_app(prepared):
    app, _, _, repository, boundary, clearances = prepared
    before = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules())
    with pytest.raises(LocalTaxDataErasureInstallationError):
        install_local_tax_data_erasure(app, durable_repository=object(), payslip_boundary=boundary,
                                       clearance_provider=lambda **_: clearances)
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == before
    _install(app, repository, boundary, clearances, [])
    with pytest.raises(LocalTaxDataErasureInstallationError):
        _install(app, repository, boundary, clearances, [])
