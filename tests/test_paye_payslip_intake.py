"""Hostile tests for the disabled-first raw-payslip intake boundary."""

from __future__ import annotations

from datetime import date
import hashlib
import os
import sqlite3
import threading

import pytest

import reserved.database as db
import reserved.services.paye_payslip_intake as intake_module
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


def _receipts():
    with db._connection() as conn:
        return conn.execute("SELECT * FROM paye_payslip_quarantine_receipts ORDER BY receipt_key").fetchall()


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


def test_preexisting_permissive_or_foreign_storage_root_is_rejected(tmp_path, monkeypatch):
    permissive = tmp_path / "permissive-payslips"
    permissive.mkdir(mode=0o700)
    permissive.chmod(0o755)
    with pytest.raises(PayslipIntakeError, match="root is unavailable"):
        PayslipIntakeBoundary(permissive, enabled=True)

    owned = tmp_path / "owned-payslips"
    owned.mkdir(mode=0o700)
    monkeypatch.setattr(intake_module.os, "geteuid", lambda: os.stat(owned).st_uid + 1)
    with pytest.raises(PayslipIntakeError, match="root is unavailable"):
        PayslipIntakeBoundary(owned, enabled=True)


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
    assert not path.exists()
    quarantined = tuple((tmp_path / "private-payslips" / ".quarantine").iterdir())
    assert len(quarantined) == 1
    assert _metadata(intake_id) is None
    receipts = _receipts()
    assert len(receipts) == 1 and receipts[0]["storage_id"] == intake_id
    assert receipts[0]["reason"] == "untracked_regular" and receipts[0]["content_sha256"] is None
    forged = PayslipIntakeHandle(intake_id=intake_id, tax_year=YEAR)
    with pytest.raises(PayslipIntakeError, match="unavailable"):
        restarted.cancel(handle=forged, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)


def test_startup_inventory_is_idempotent_and_preserves_known_cross_record(tmp_path):
    boundary = _boundary(tmp_path)
    known = _begin(boundary)
    unknown_id = "f" * 64
    boundary._write(unknown_id, "application/pdf", PDF)
    restarted = _boundary(tmp_path)
    assert _metadata(known.intake_id)["state"] == "pending"
    assert len(_receipts()) == 1
    _boundary(tmp_path)
    assert len(_receipts()) == 1
    restarted.cancel(handle=known, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR)
    assert _metadata(known.intake_id) is None


def test_startup_inventory_surfaces_symlink_and_malformed_entries_without_moving_them(tmp_path):
    boundary = _boundary(tmp_path)
    intake_id = "a" * 64
    path = boundary._path_for(intake_id, "application/pdf")
    foreign = tmp_path / "foreign.pdf"
    foreign.write_bytes(PDF)
    path.symlink_to(foreign)
    malformed = tmp_path / "private-payslips" / "unexpected.tmp"
    malformed.write_bytes(PDF)
    _boundary(tmp_path)
    reasons = {(row["filename_class"], row["reason"], row["storage_id"]) for row in _receipts()}
    assert ("server_document", "symlink", intake_id) in reasons
    assert ("malformed", "malformed_name", None) in reasons
    assert path.is_symlink() and malformed.exists()


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


def test_account_lifecycle_cleanup_covers_all_owner_sessions_but_not_other_owner(tmp_path):
    boundary = _boundary(tmp_path)
    first = _begin(boundary)
    second = boundary.begin(
        authenticated_user_id=OWNER, session_binding="session-owner-other", tax_year=YEAR,
        content_type="application/pdf", document_bytes=PDF,
    )
    foreign = boundary.begin(
        authenticated_user_id=OTHER, session_binding=OTHER_SESSION, tax_year=YEAR,
        content_type="application/pdf", document_bytes=PDF,
    )

    assert boundary.erase_owner_for_account_lifecycle(authenticated_user_id=OWNER) == 2
    assert _metadata(first.intake_id) is None and _metadata(second.intake_id) is None
    assert _metadata(foreign.intake_id) is not None
    assert len(_files(tmp_path)) == 1


def test_account_lifecycle_cleanup_stops_and_preserves_metadata_on_replacement(tmp_path):
    boundary = _boundary(tmp_path)
    first, second = _begin(boundary), _begin(boundary)
    _, record = boundary._owned_record(
        handle=first, authenticated_user_id=OWNER, session_binding=SESSION, tax_year=YEAR,
    )
    path = record.path
    path.unlink()
    path.write_bytes(PDF)

    with pytest.raises(PayslipIntakeError, match="identity"):
        boundary.erase_owner_for_account_lifecycle(authenticated_user_id=OWNER)
    assert _metadata(first.intake_id) is not None
    assert _metadata(second.intake_id) is not None
    assert len(_files(tmp_path)) == 2


def test_account_lifecycle_barrier_makes_concurrent_intake_post_linearization(tmp_path):
    boundary = _boundary(tmp_path)
    _begin(boundary)
    callback_started, release_callback, upload_done = threading.Event(), threading.Event(), threading.Event()
    erased, uploaded = [], []

    def erase():
        erased.append(boundary.erase_owner_for_account_lifecycle_then(
            authenticated_user_id=OWNER,
            after_raw_erasure=lambda: (callback_started.set(), release_callback.wait(2), "structured")[2],
        ))

    def upload():
        uploaded.append(boundary.begin(
            authenticated_user_id=OWNER, session_binding="session-owner-later", tax_year=YEAR,
            content_type="application/pdf", document_bytes=PDF,
        ))
        upload_done.set()

    first = threading.Thread(target=erase); first.start()
    assert callback_started.wait(2)
    second = threading.Thread(target=upload); second.start()
    assert not upload_done.wait(0.1)
    release_callback.set(); first.join(2); second.join(2)
    assert erased == [(1, "structured")]
    assert len(uploaded) == 1 and upload_done.is_set() and len(_files(tmp_path)) == 1


def test_real_v15_upgrade_uses_no_action_intake_foreign_key(tmp_path, monkeypatch):
    """Exercise v16 migration itself, without fresh-schema DDL precreating it."""
    legacy = tmp_path / "real-v15.db"
    with sqlite3.connect(legacy) as conn:
        conn.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version VALUES (15);
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clerk_user_id TEXT NOT NULL UNIQUE,
                email TEXT,
                display_name TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE paye_manual_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                tax_year TEXT NOT NULL,
                employment_slot INTEGER NOT NULL CHECK(employment_slot BETWEEN 1 AND 20),
                evidence_id TEXT NOT NULL UNIQUE,
                source_kind TEXT NOT NULL CHECK(source_kind = 'customer_confirmed_manual'),
                provenance TEXT NOT NULL,
                gross_to_date TEXT, tax_paid_to_date TEXT, tax_code TEXT,
                pay_frequency TEXT NOT NULL, pension_treatment TEXT NOT NULL,
                effective_through TEXT NOT NULL, observed_on TEXT NOT NULL,
                completeness TEXT NOT NULL CHECK(completeness IN ('partial', 'unknown')),
                replaced_at TEXT, deleted_at TEXT, created_at TEXT NOT NULL,
                UNIQUE(user_id, tax_year, evidence_id)
            );
            """
        )
    monkeypatch.setattr(db, "_DB_FILE", legacy)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path / "legacy-instance")
    # init_db normally installs current DDL before migrations.  Suppress only
    # that bootstrap here so this proves the version-16 migration definition.
    monkeypatch.setattr(db, "_DDL", "")
    db.init_db()
    with db._connection() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == 17
        foreign_keys = conn.execute("PRAGMA foreign_key_list(paye_payslip_intakes)").fetchall()
        assert [(item["table"], item["on_delete"] ) for item in foreign_keys] == [("users", "NO ACTION")]
        conn.execute(
            "INSERT INTO users (id,clerk_user_id,email,display_name,created_at) VALUES (70,'v15-owner','o@example.test','owner','2026-01-01T00:00:00+00:00')"
        )
        conn.execute(
            """INSERT INTO paye_payslip_intakes
               (storage_id,user_id,session_hash,tax_year,content_type,file_device,file_inode,
                byte_count,content_sha256,state,created_at)
               VALUES (?,70,?,'2026/27','application/pdf',1,2,5,?,'pending','2026-01-01T00:00:00+00:00')""",
            ("a" * 64, "b" * 64, "c" * 64),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM users WHERE id=70")
