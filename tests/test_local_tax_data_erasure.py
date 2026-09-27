"""Synthetic request tests for the dormant bounded local-erasure installer."""

from __future__ import annotations

from dataclasses import replace
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
    LocalTaxDataErasureInstallationError, LocalTaxDataErasureRuntime,
    install_local_tax_data_erasure,
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
        issuer_reference="evidence-policy:route-test-v1", policy_version="v1",
        allowed_references=("annual:route-test",),
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


def _runtime(repository, boundary, clearances, calls):
    def provider(*, authenticated_user_id):
        calls.append(authenticated_user_id)
        return clearances
    return LocalTaxDataErasureRuntime(repository, boundary, provider)


def _seed_structured(owner, other):
    """Seed only the rows needed to prove route-level physical scope/counts."""
    with db._connection() as conn:
        for user_id, suffix in ((owner, "owner"), (other, "other")):
            conn.execute(
                """INSERT INTO paye_manual_entries
                   (user_id,tax_year,employment_slot,evidence_id,source_kind,provenance,
                    gross_to_date,tax_paid_to_date,tax_code,pay_frequency,pension_treatment,
                    effective_through,observed_on,completeness,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, "2026/27", 1, f"route-paye-{suffix}", "customer_confirmed_manual",
                 "manual-customer-confirmed", "100.00", "10.00", "1257L", "monthly",
                 "net_pay", "2026-09-01", "2026-09-02", "partial",
                 "2026-09-02T00:00:00+00:00"),
            )
            conn.execute(
                """INSERT INTO annual_position_records
                   (record_identity,user_id,business_reference,tax_year,nation,record_purpose,
                    record_version,predecessor_identity,governance_fingerprint,envelope_json,
                    envelope_sha256,state,created_at,deleted_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                (f"annual-position-structural:sha256-{'a' if user_id == owner else 'b'}" + "0" * 63,
                 user_id, f"business-{suffix}", "2026/27", "England", "annual_to_cash_position",
                 1, None, f"governance-{suffix}", "{}", "0" * 64, "current",
                 "2026-09-02T00:00:00+00:00"),
            )


def test_disabled_and_csrf_rejections_never_consult_clearance_provider(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 404
    assert calls == []


def test_application_factory_composes_only_one_exact_disabled_first_runtime(
    prepared, monkeypatch,
):
    _app, owner, _other, repository, boundary, clearances = prepared
    calls = []
    invalid = create_app(erasure_runtime=object())
    invalid.config.update(TESTING=True)
    invalid_client, invalid_token = _client(invalid, owner)
    assert invalid_client.post(
        "/v2/account/local-tax-data-erasure", data={"csrf_token": invalid_token},
    ).status_code == 404

    runtime = _runtime(repository, boundary, clearances, calls)
    composed = create_app(erasure_runtime=runtime)
    composed.config.update(TESTING=True)
    client, token = _client(composed, owner)
    assert client.post(
        "/v2/account/local-tax-data-erasure", data={"csrf_token": token},
    ).status_code == 404
    assert calls == []

    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    response = client.post(
        "/v2/account/local-tax-data-erasure", data={"csrf_token": token},
    )
    assert response.status_code == 200
    assert response.get_json()["scope"] == "local_tax_data_only"
    assert calls == [owner]


def test_erasure_runtime_rejects_incomplete_dependencies_before_app_mutation(prepared):
    _app, _owner, _other, repository, boundary, clearances = prepared
    with pytest.raises(LocalTaxDataErasureInstallationError):
        LocalTaxDataErasureRuntime(object(), boundary, lambda **_: clearances)
    with pytest.raises(LocalTaxDataErasureInstallationError):
        LocalTaxDataErasureRuntime(repository, object(), lambda **_: clearances)
    with pytest.raises(LocalTaxDataErasureInstallationError):
        LocalTaxDataErasureRuntime(repository, boundary, object())


def test_query_or_body_extras_are_rejected_before_provider(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure?x=1", data={"csrf_token": token}).status_code == 400
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token, "x": "1"}).status_code == 400
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
    handle = boundary.begin(authenticated_user_id=owner, session_binding="route_session_0001",
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


def test_route_erases_all_owner_sessions_and_structured_rows_without_crossing_owner(prepared, monkeypatch):
    app, owner, other, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    first = boundary.begin(authenticated_user_id=owner, session_binding="route_session_0011",
                           tax_year="2026/27", content_type="application/pdf",
                           document_bytes=b"%PDF-1.7\nfirst")
    second = boundary.begin(authenticated_user_id=owner, session_binding="route_session_0012",
                            tax_year="2026/27", content_type="application/pdf",
                            document_bytes=b"%PDF-1.7\nsecond")
    foreign = boundary.begin(authenticated_user_id=other, session_binding="route_session_0013",
                             tax_year="2026/27", content_type="application/pdf",
                             document_bytes=b"%PDF-1.7\nforeign")
    _seed_structured(owner, other)
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    response = client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token})
    assert response.status_code == 200
    assert response.get_json()["raw_payslip_files_deleted"] == 2
    assert response.get_json()["annual_position_records_deleted"] == 1
    assert response.get_json()["paye_manual_entries_deleted"] == 1
    with db._connection() as conn:
        for handle in (first, second):
            assert conn.execute("SELECT 1 FROM paye_payslip_intakes WHERE storage_id=?",
                                (handle.intake_id,)).fetchone() is None
        assert conn.execute("SELECT 1 FROM paye_payslip_intakes WHERE storage_id=?",
                            (foreign.intake_id,)).fetchone() is not None
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?",
                            (owner,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?",
                            (owner,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?",
                            (other,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?",
                            (other,)).fetchone()[0] == 1


def test_bad_raw_identity_stops_before_structured_erasure(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, clearances, calls)
    handle = boundary.begin(authenticated_user_id=owner, session_binding="route_session_0002",
                            tax_year="2026/27", content_type="application/pdf", document_bytes=b"%PDF-1.7\nsynthetic")
    _, record = boundary._owned_record(handle=handle, authenticated_user_id=owner,
                                       session_binding="route_session_0002", tax_year="2026/27")
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


@pytest.mark.parametrize("mutate", (
    lambda legal, backup: (_clearance(999, "legal_hold_clear"), backup),
    lambda legal, backup: (replace(legal, state="revoked", revoked_at="2026-09-02T00:00:00+00:00"), backup),
    lambda legal, backup: (legal, replace(backup, expires_at="2020-01-01T00:00:00+00:00")),
    lambda legal, backup: (replace(legal, issuer_reference="lifecycle:forged-v1"), backup),
    lambda legal, backup: (backup, legal),
))
def test_clearance_failures_do_not_report_success(prepared, monkeypatch, mutate):
    app, owner, _, repository, boundary, clearances = prepared
    calls = []; _install(app, repository, boundary, mutate(*clearances), calls)
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 403
    assert calls == [owner]


def test_route_without_external_authority_adapter_fails_closed(prepared, monkeypatch):
    app, owner, _, repository, boundary, clearances = prepared
    unavailable = DurableAnnualPositionRepository(
        repository._governance, evidence_reference_policy=repository._evidence_reference_policy,
        membership_issuer_reference="membership:route-test-v1",
        lifecycle_issuer_reference="lifecycle:route-test-v1",
        external_authority_adapter=None,
    )
    calls = []; _install(app, unavailable, boundary, clearances, calls)
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 403
    assert calls == [owner]


def test_second_clearance_check_failure_never_reports_success(prepared, monkeypatch):
    app, owner, other, repository, boundary, clearances = prepared
    _seed_structured(owner, other)
    calls = []; _install(app, repository, boundary, clearances, calls)
    checks = []
    original = repository.assert_account_erasure_clearances
    def verify_then_fail(**kwargs):
        checks.append(kwargs)
        if len(checks) == 2:
            raise ValueError("clearance changed")
        return original(**kwargs)
    monkeypatch.setattr(repository, "assert_account_erasure_clearances", verify_then_fail)
    monkeypatch.setenv("LOCAL_TAX_DATA_ERASURE_ENABLED", "1")
    client, token = _client(app, owner)
    assert client.post("/v2/account/local-tax-data-erasure", data={"csrf_token": token}).status_code == 403
    assert len(checks) == 2
    with db._connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM annual_position_records WHERE user_id=?",
                            (owner,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?",
                            (owner,)).fetchone()[0] == 1
