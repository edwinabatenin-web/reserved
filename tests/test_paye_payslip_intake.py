"""Hostile tests for the disabled-first raw-payslip intake boundary."""

from __future__ import annotations

from datetime import date
import hashlib
import sqlite3

import pytest

import reserved.database as db
from reserved.engines.paye_evidence_capture import PayFrequency, PensionTreatment, SourceDocumentType
from reserved.engines.paye_extraction_confirmation import (
    Decision,
    FieldDecision,
    FieldName,
    PayeExtractionCandidate,
)
from reserved.services.paye_payslip_intake import (
    MAX_PAYSLIP_BYTES,
    PayslipIntakeBoundary,
    PayslipIntakeError,
    PayslipIntakeHandle,
)


OWNER = 41
OTHER = 42
SESSION = "session-owner-0001"
OTHER_SESSION = "session-other-0002"
YEAR = "2026/27"
PDF = b"%PDF-1.7\nprivate-payroll-document"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "payslip-intake.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    with db._connection() as conn:
        conn.executemany(
            "INSERT INTO users (id,clerk_user_id,email,display_name,created_at) VALUES (?,?,?,?,?)",
            ((OWNER, "owner", "owner@example.test", "owner", "2026-01-01T00:00:00+00:00"),
             (OTHER, "other", "other@example.test", "other", "2026-01-01T00:00:00+00:00")),
        )


def _candidate():
    return PayeExtractionCandidate(
        candidate_id="candidate-1", document_id="document-1", evidence_id="evidence-1",
        document_type=SourceDocumentType.PAYSLIP, supersedes_evidence_id=None,
        tax_year="2026-27", employment_id="employment-1", gross_pay_to_date="12345.67",
        tax_paid_to_date="2345.60", tax_code="1257L", pay_frequency=PayFrequency.MONTHLY,
        pension_treatment=PensionTreatment.UNKNOWN, effective_through=date(2026, 8, 18),
        observed_on=date(2026, 8, 20),
    )


def _decisions():
    return tuple(FieldDecision(field, Decision.ACCEPT) for field in FieldName)


class _WorkingAdapter:
    def __init__(self):
        self.calls = []

    def extract_payslip(self, **kwargs):
        self.calls.append(kwargs)
        return _candidate()


class _FailingAdapter:
    def extract_payslip(self, **kwargs):
        raise RuntimeError("unavailable")


def _boundary(tmp_path, *, enabled=True, adapter=None):
    return PayslipIntakeBoundary(tmp_path / "private-payslips", enabled=enabled, extraction_adapter=adapter)


def _begin(boundary):
    return boundary.begin(
        authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
        content_type="application/pdf", document_bytes=PDF,
    )


def _files(tmp_path):
    root = tmp_path / "private-payslips"
    return tuple(path for path in root.iterdir() if path.is_file())


def _metadata(intake_id):
    with db._connection() as conn:
        return conn.execute("SELECT * FROM paye_payslip_intakes WHERE storage_id=?", (intake_id,)).fetchone()


def test_disabled_boundary_rejects_before_any_file_is_created(tmp_path):
    boundary = _boundary(tmp_path, enabled=False)
    with pytest.raises(PayslipIntakeError, match="disabled"):
        _begin(boundary)
    assert _files(tmp_path) == ()


@pytest.mark.parametrize(
    "content_type, payload, expected",
    (
        ("text/plain", PDF, "content type"),
        ("application/pdf; charset=binary", PDF, "content type"),
        ("application/pdf", b"not-a-pdf", "do not match"),
        ("image/png", PDF, "do not match"),
        ("application/pdf", b"", "non-empty"),
        ("application/pdf", b"%PDF-" + b"x" * MAX_PAYSLIP_BYTES, "size limit"),
    ),
)
def test_hostile_type_and_size_inputs_are_rejected_without_storage(tmp_path, content_type, payload, expected):
    boundary = _boundary(tmp_path)
    with pytest.raises(PayslipIntakeError, match=expected):
        boundary.begin(
            authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
            content_type=content_type, document_bytes=payload,
        )
    assert _files(tmp_path) == ()


@pytest.mark.parametrize("tax_year", ("2026/99", "2026/26", "1999/00", "not-a-year"))
def test_non_consecutive_or_non_uk_tax_year_is_rejected_without_storage(tmp_path, tax_year):
    boundary = _boundary(tmp_path)
    with pytest.raises(PayslipIntakeError, match="tax year"):
        boundary.begin(
            authenticated_user_id=OWNER, session_binding=SESSION, tax_year=tax_year,
            content_type="application/pdf", document_bytes=PDF,
        )
    assert _files(tmp_path) == ()


def test_handle_is_opaque_and_user_controlled_path_traversal_is_rejected(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    assert len(handle.intake_id) == 64
    assert "private-payroll-document" not in repr(handle)
    forged = PayslipIntakeHandle(intake_id="../outside", tax_year=YEAR)
    with pytest.raises(PayslipIntakeError, match="handle"):
        boundary.cancel(
            handle=forged, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
        )
    assert len(_files(tmp_path)) == 1
    boundary.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert _files(tmp_path) == ()


def test_cross_owner_session_and_year_access_fail_without_deleting_owner_file(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    for owner, session, year in ((OTHER, OTHER_SESSION, YEAR), (OWNER, OTHER_SESSION, YEAR), (OWNER, SESSION, "2025/26")):
        with pytest.raises(PayslipIntakeError, match="unavailable|tax year"):
            boundary.cancel(handle=handle, authenticated_user_id=owner, session_binding=session, tax_year=year)
    assert len(_files(tmp_path)) == 1
    boundary.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert _files(tmp_path) == ()


def test_confirmation_passes_raw_bytes_only_to_injected_adapter_then_deletes_file(tmp_path):
    adapter = _WorkingAdapter()
    boundary = _boundary(tmp_path, adapter=adapter)
    handle = _begin(boundary)
    confirmation = boundary.confirm(
        handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
        decisions=_decisions(), confirmation_id="confirmation-1",
    )
    assert confirmation.capture.tax_year == "2026-27"
    assert adapter.calls == [{"document_bytes": PDF, "content_type": "application/pdf", "tax_year": YEAR}]
    assert _files(tmp_path) == ()
    # The returned structured confirmation contains no raw source marker.
    assert "private-payroll-document" not in repr(confirmation)


@pytest.mark.parametrize("adapter", (None, _FailingAdapter()), ids=("missing-adapter", "adapter-failure"))
def test_confirmation_failure_deterministically_cleans_up_raw_file(tmp_path, adapter):
    boundary = _boundary(tmp_path, adapter=adapter)
    handle = _begin(boundary)
    with pytest.raises(PayslipIntakeError):
        boundary.confirm(
            handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
            decisions=_decisions(), confirmation_id="confirmation-1",
        )
    assert _files(tmp_path) == ()
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        boundary.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)


@pytest.mark.parametrize("substitution", ("symlink", "replacement"))
def test_substituted_file_never_reaches_adapter_and_fails_closed(tmp_path, substitution):
    adapter = _WorkingAdapter()
    boundary = _boundary(tmp_path, adapter=adapter)
    handle = _begin(boundary)
    stored = _files(tmp_path)[0]
    stored.unlink()
    if substitution == "symlink":
        foreign = tmp_path / "foreign.pdf"
        foreign.write_bytes(PDF)
        stored.symlink_to(foreign)
    else:
        stored.write_bytes(PDF)
    with pytest.raises(PayslipIntakeError, match="identity changed|could not be read|path is unsafe"):
        boundary.confirm(
            handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
            decisions=_decisions(), confirmation_id="confirmation-1",
        )
    assert adapter.calls == []
    assert stored.exists() or stored.is_symlink()


def test_cancel_does_not_unlink_a_replacement_file(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    stored = _files(tmp_path)[0]
    stored.unlink()
    stored.write_bytes(PDF)
    with pytest.raises(PayslipIntakeError, match="identity changed"):
        boundary.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert stored.read_bytes() == PDF


def test_owner_session_erasure_is_isolated_and_deletes_every_pending_file(tmp_path):
    boundary = _boundary(tmp_path)
    first = _begin(boundary)
    second = boundary.begin(
        authenticated_user_id=OWNER, session_binding=SESSION, tax_year="2025/26",
        content_type="application/pdf", document_bytes=PDF,
    )
    other = boundary.begin(
        authenticated_user_id=OTHER, session_binding=OTHER_SESSION, tax_year=YEAR,
        content_type="application/pdf", document_bytes=PDF,
    )
    assert boundary.erase_owner_session(authenticated_user_id=OWNER, session_binding=SESSION) == 2
    assert len(_files(tmp_path)) == 1
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        boundary.cancel(handle=first, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        boundary.cancel(handle=second, authenticated_user_id=OWNER, session_binding=SESSION, tax_year="2025/26")
    boundary.cancel(handle=other, authenticated_user_id=OTHER, session_binding=OTHER_SESSION, tax_year=YEAR)
    assert _files(tmp_path) == ()


def test_storage_root_symlink_is_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "private-payslips"
    root.symlink_to(target, target_is_directory=True)
    with pytest.raises(PayslipIntakeError, match="symlink"):
        PayslipIntakeBoundary(root, enabled=True)


def test_restart_recovers_only_minimal_owner_bound_pending_handle(tmp_path):
    first = _boundary(tmp_path)
    handle = _begin(first)
    row = _metadata(handle.intake_id)
    assert row["state"] == "pending"
    assert row["session_hash"] != SESSION
    assert row["content_sha256"] == hashlib.sha256(PDF).hexdigest()
    assert {"storage_id", "user_id", "session_hash", "tax_year", "content_type", "file_device", "file_inode", "byte_count", "content_sha256", "state", "created_at", "deletion_started_at"} == set(row.keys())
    with db._connection() as conn:
        foreign_keys = conn.execute("PRAGMA foreign_key_list(paye_payslip_intakes)").fetchall()
    assert [(item["table"], item["on_delete"] ) for item in foreign_keys] == [("users", "NO ACTION")]

    restarted = _boundary(tmp_path)
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        restarted.cancel(handle=handle, authenticated_user_id=OTHER, session_binding=OTHER_SESSION, tax_year=YEAR)
    restarted.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert _files(tmp_path) == ()
    assert _metadata(handle.intake_id) is None


def test_recovery_deletes_exact_durable_deleting_orphan_after_crash(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    intake_id, record = boundary._owned_record(
        handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
    )
    boundary._mark_deleting(intake_id=intake_id, record=record)
    # Simulate a process crash after durable deletion intent but before unlink.
    restarted = _boundary(tmp_path)
    assert _files(tmp_path) == ()
    assert _metadata(handle.intake_id) is None
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        restarted.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)


def test_recovery_finalises_crash_between_unlink_and_metadata_removal(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    intake_id, record = boundary._owned_record(
        handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
    )
    boundary._mark_deleting(intake_id=intake_id, record=record)
    boundary._delete(intake_id, record)
    # The metadata still says deleting; a restart records the completed local deletion.
    assert _metadata(handle.intake_id)["state"] == "deleting"
    _boundary(tmp_path)
    assert _metadata(handle.intake_id) is None


def test_pre_metadata_crash_file_is_preserved_for_operational_disposition(tmp_path):
    boundary = _boundary(tmp_path)
    intake_id = "f" * 64
    path = boundary._path_for(intake_id, "application/pdf")
    boundary._write(intake_id, "application/pdf", PDF)
    # Simulate process death before metadata insertion: no exact durable identity exists.
    restarted = _boundary(tmp_path)
    assert path.exists()
    assert _metadata(intake_id) is None
    forged = PayslipIntakeHandle(intake_id=intake_id, tax_year=YEAR)
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        restarted.cancel(handle=forged, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)


@pytest.mark.parametrize("substitution", ("symlink", "replacement"))
def test_restart_quarantines_substituted_durable_file_without_adapter_input(tmp_path, substitution):
    adapter = _WorkingAdapter()
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    stored = _files(tmp_path)[0]
    stored.unlink()
    if substitution == "symlink":
        foreign = tmp_path / "foreign.pdf"
        foreign.write_bytes(PDF)
        stored.symlink_to(foreign)
    else:
        stored.write_bytes(PDF)
    restarted = _boundary(tmp_path, adapter=adapter)
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        restarted.confirm(
            handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
            decisions=_decisions(), confirmation_id="confirmation-1",
        )
    assert adapter.calls == []
    assert _metadata(handle.intake_id)["state"] == "pending"


def test_pending_or_deleting_raw_intake_blocks_direct_user_deletion(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    with db._connection() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM users WHERE id=?", (OWNER,))
    assert len(_files(tmp_path)) == 1 and _metadata(handle.intake_id)["state"] == "pending"

    intake_id, record = boundary._owned_record(
        handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
    )
    boundary._mark_deleting(intake_id=intake_id, record=record)
    with db._connection() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM users WHERE id=?", (OWNER,))
    assert len(_files(tmp_path)) == 1 and _metadata(handle.intake_id)["state"] == "deleting"


def test_exact_local_cleanup_removes_metadata_before_user_deletion(tmp_path):
    boundary = _boundary(tmp_path)
    handle = _begin(boundary)
    boundary.cancel(handle=handle, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert _files(tmp_path) == () and _metadata(handle.intake_id) is None
    with db._connection() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (OWNER,))
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id=?", (OWNER,)).fetchone()[0] == 0
