"""Disabled-first, local raw-payslip intake boundary.

The existing extraction-confirmation contract deliberately accepts only a
typed, redacted extraction candidate.  This module is the narrow, private
boundary before that contract: it accepts an already-authenticated owner's
small, recognised document, stores it under a server-generated name, and
deletes it deterministically when it is consumed or cancelled.

It has no Flask route, OCR implementation, or network/provider imports.
Extraction is an injected adapter and is fail-closed when absent.  Its SQLite
metadata contains only redacted owner/session/file identity sufficient for
crash recovery, never raw content or a client filename.  This is deliberately
not a claim that backups, external OCR providers, or any wider account erasure
have completed.  It is supported only where the private 0700 storage directory
is custody-controlled and has no hostile same-UID mutator.  Portable
Python/macOS does not offer unlink-by-inode, so same-UID namespace races remain
outside this disabled-first boundary's supported threat model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Protocol

from reserved import database
from reserved.engines.paye_extraction_confirmation import (
    PayeExtractionCandidate,
    PayeExtractionConfirmation,
    confirm_paye_extraction,
)


MAX_PAYSLIP_BYTES = 10 * 1024 * 1024
_TAX_YEAR = re.compile(r"[0-9]{4}/[0-9]{2}\Z")
_SESSION = re.compile(r"[A-Za-z0-9_-]{16,256}\Z")
_STORAGE_ID = re.compile(r"[0-9a-f]{64}\Z")
_DOCUMENT_NAME = re.compile(r"([0-9a-f]{64})\.(pdf|png|jpg)\Z")
_DELETING_NAME = re.compile(r"\.deleting-([0-9a-f]{64})\.(pdf|png|jpg)\Z")
_TYPES = {
    "application/pdf": ("pdf", b"%PDF-"),
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
}


class PayslipIntakeError(ValueError):
    """An intake request is unavailable or unsafe; callers must fail closed."""


class PayslipExtractionAdapter(Protocol):
    """An explicitly supplied, local extraction adapter; never a default OCR."""

    def extract_payslip(self, *, document_bytes: bytes, content_type: str,
                        tax_year: str) -> PayeExtractionCandidate: ...


@dataclass(frozen=True, slots=True)
class PayslipIntakeHandle:
    """Opaque identifier only; raw bytes and storage paths are never exposed."""

    intake_id: str
    tax_year: str


@dataclass(frozen=True, slots=True)
class _StoredPayslip:
    owner_user_id: int
    session_hash: str
    tax_year: str
    content_type: str
    path: Path
    device: int
    inode: int
    byte_count: int
    content_sha256: str


class PayslipIntakeBoundary:
    """Private raw-document lifecycle bound to one owner, session and tax year."""

    def __init__(self, storage_root: Path, *, enabled: bool = False,
                 extraction_adapter: PayslipExtractionAdapter | None = None):
        if type(enabled) is not bool:
            raise TypeError("payslip intake enabled flag must be boolean")
        root = Path(storage_root)
        if root.exists() and root.is_symlink():
            raise PayslipIntakeError("payslip storage root must not be a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise PayslipIntakeError("payslip storage root is unavailable")
        self._root = root.resolve()
        if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
            raise PayslipIntakeError("payslip storage platform protections are unavailable")
        root_fd = -1
        try:
            root_fd = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
                raise PayslipIntakeError("payslip storage root is unavailable")
        except (OSError, PayslipIntakeError) as exc:
            if root_fd >= 0:
                os.close(root_fd)
            if isinstance(exc, PayslipIntakeError):
                raise
            raise PayslipIntakeError("payslip storage root is unavailable") from exc
        self._root_fd = root_fd
        try:
            os.mkdir(".quarantine", 0o700, dir_fd=self._root_fd)
        except FileExistsError:
            pass
        try:
            self._quarantine_fd = os.open(".quarantine", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                          dir_fd=self._root_fd)
            qstat = os.fstat(self._quarantine_fd)
            if not stat.S_ISDIR(qstat.st_mode) or qstat.st_mode & 0o077:
                raise PayslipIntakeError("payslip quarantine is unavailable")
        except (OSError, PayslipIntakeError) as exc:
            self.close()
            if isinstance(exc, PayslipIntakeError):
                raise
            raise PayslipIntakeError("payslip quarantine is unavailable") from exc
        self._enabled = enabled
        self._extraction_adapter = extraction_adapter
        self._records: dict[str, _StoredPayslip] = {}
        database.init_db()
        self._recover_after_restart()

    def close(self) -> None:
        """Release the private directory handle when the composed runtime stops."""
        for name in ("_quarantine_fd", "_root_fd"):
            fd = getattr(self, name, -1)
            setattr(self, name, -1)
            if fd >= 0:
                os.close(fd)

    def __del__(self):  # pragma: no cover - best-effort interpreter cleanup
        try:
            self.close()
        except OSError:
            pass

    @staticmethod
    def _owner(value: object) -> int:
        if type(value) is not int or value <= 0:
            raise PayslipIntakeError("authenticated owner is invalid")
        return value

    @staticmethod
    def _session(value: object) -> str:
        if type(value) is not str or _SESSION.fullmatch(value) is None:
            raise PayslipIntakeError("authenticated session binding is invalid")
        return value

    @classmethod
    def _session_hash(cls, value: object) -> str:
        session = cls._session(value)
        return hashlib.sha256(b"reserved:payslip-session:v1\0" + session.encode("ascii")).hexdigest()

    @staticmethod
    def _year(value: object) -> str:
        if type(value) is not str or _TAX_YEAR.fullmatch(value) is None:
            raise PayslipIntakeError("tax year is invalid")
        start_year, end_year = int(value[:4]), int(value[5:])
        if not 2000 <= start_year <= 2999 or end_year != (start_year + 1) % 100:
            raise PayslipIntakeError("tax year is not a consecutive UK tax-year span")
        return value

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise PayslipIntakeError("payslip intake is disabled")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _require_registered_owner(owner_user_id: int) -> None:
        with database._connection() as conn:
            if conn.execute("SELECT 1 FROM users WHERE id=?", (owner_user_id,)).fetchone() is None:
                raise PayslipIntakeError("authenticated owner is unavailable")

    @staticmethod
    def _validate_document(content_type: object, document_bytes: object) -> tuple[str, bytes]:
        if type(content_type) is not str or content_type not in _TYPES:
            raise PayslipIntakeError("unsupported payslip content type")
        if type(document_bytes) is not bytes or not document_bytes:
            raise PayslipIntakeError("payslip document must be non-empty bytes")
        if len(document_bytes) > MAX_PAYSLIP_BYTES:
            raise PayslipIntakeError("payslip document exceeds the size limit")
        if not document_bytes.startswith(_TYPES[content_type][1]):
            raise PayslipIntakeError("payslip bytes do not match the declared content type")
        return content_type, document_bytes

    def _filename_for(self, intake_id: str, content_type: str) -> str:
        if _STORAGE_ID.fullmatch(intake_id) is None:
            raise PayslipIntakeError("payslip storage identity is invalid")
        suffix = _TYPES[content_type][0]
        return f"{intake_id}.{suffix}"

    def _path_for(self, intake_id: str, content_type: str) -> Path:
        # This is retained for diagnostics/tests only.  All filesystem I/O uses
        # the persistent private directory descriptor, never this path string.
        return self._root / self._filename_for(intake_id, content_type)

    def _quarantine_filename(self, intake_id: str, content_type: str) -> str:
        return ".deleting-" + self._filename_for(intake_id, content_type)

    def _write(self, intake_id: str, content_type: str, document_bytes: bytes) -> tuple[int, int, int, str]:
        filename = self._filename_for(intake_id, content_type)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= os.O_NOFOLLOW
        fd = None
        created = False
        try:
            fd = os.open(filename, flags, 0o600, dir_fd=self._root_fd)
            created = True
            with os.fdopen(fd, "wb") as output:
                fd = None
                output.write(document_bytes)
                output.flush()
                os.fsync(output.fileno())
                metadata = os.fstat(output.fileno())
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(document_bytes):
                    raise PayslipIntakeError("payslip storage write could not be verified")
                return (
                    metadata.st_dev,
                    metadata.st_ino,
                    metadata.st_size,
                    hashlib.sha256(document_bytes).hexdigest(),
                )
        except (OSError, PayslipIntakeError) as exc:
            if created:
                try:
                    os.unlink(filename, dir_fd=self._root_fd)
                except OSError:
                    pass
            if isinstance(exc, PayslipIntakeError):
                raise
            raise PayslipIntakeError("payslip document could not be stored") from exc
        finally:
            if fd is not None:
                os.close(fd)
            pass

    @staticmethod
    def _matches(record: _StoredPayslip, metadata: os.stat_result) -> bool:
        return (stat.S_ISREG(metadata.st_mode) and metadata.st_dev == record.device
                and metadata.st_ino == record.inode and metadata.st_size == record.byte_count
                and 0 < metadata.st_size <= MAX_PAYSLIP_BYTES)

    def _read_verified(self, intake_id: str, record: _StoredPayslip) -> bytes:
        expected = self._path_for(intake_id, record.content_type)
        if record.path != expected:
            raise PayslipIntakeError("payslip storage path is unsafe")
        flags = os.O_RDONLY
        flags |= os.O_NOFOLLOW
        fd = None
        try:
            fd = os.open(self._filename_for(intake_id, record.content_type), flags, dir_fd=self._root_fd)
            before = os.fstat(fd)
            if not self._matches(record, before):
                raise PayslipIntakeError("payslip storage identity changed")
            with os.fdopen(fd, "rb") as source:
                fd = None
                document_bytes = source.read(MAX_PAYSLIP_BYTES + 1)
                after = os.fstat(source.fileno())
            if (not self._matches(record, after) or len(document_bytes) != record.byte_count
                    or hashlib.sha256(document_bytes).hexdigest() != record.content_sha256
                    or not document_bytes.startswith(_TYPES[record.content_type][1])):
                raise PayslipIntakeError("payslip storage integrity check failed")
            return document_bytes
        except PayslipIntakeError:
            raise
        except OSError as exc:
            raise PayslipIntakeError("payslip document could not be read") from exc
        finally:
            if fd is not None:
                os.close(fd)

    def _delete(self, intake_id: str, record: _StoredPayslip) -> None:
        """Use verified private-directory transitions before local deletion.

        The pre-delete checks and directory descriptor fail closed for ordinary
        corruption/substitution.  They are not an inode-bound unlink primitive:
        this boundary therefore requires a custody-controlled 0700 directory
        with no hostile same-UID mutator and remains disabled pending target
        custody review.
        """
        expected = self._path_for(intake_id, record.content_type)
        if record.path != expected:
            raise PayslipIntakeError("payslip storage path is unsafe")
        filename = self._filename_for(intake_id, record.content_type)
        quarantine = self._quarantine_filename(intake_id, record.content_type)
        try:
            metadata = os.stat(filename, dir_fd=self._root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return self._delete_quarantined_or_finish(intake_id, record, quarantine)
        except OSError as exc:
            raise PayslipIntakeError("payslip storage path is unavailable") from exc
        if not self._matches(record, metadata):
            raise PayslipIntakeError("payslip storage identity changed")
        try:
            os.rename(filename, quarantine, src_dir_fd=self._root_fd, dst_dir_fd=self._root_fd)
        except OSError as exc:
            raise PayslipIntakeError("payslip document could not enter deletion quarantine") from exc
        return self._delete_quarantined_or_finish(intake_id, record, quarantine)

    def _delete_quarantined_or_finish(self, intake_id: str, record: _StoredPayslip, quarantine: str) -> None:
        try:
            metadata = os.stat(quarantine, dir_fd=self._root_fd, follow_symlinks=False)
        except FileNotFoundError:
            self._records.pop(intake_id, None)
            return
        except OSError as exc:
            raise PayslipIntakeError("payslip deletion quarantine is unavailable") from exc
        if not self._matches(record, metadata):
            raise PayslipIntakeError("payslip deletion quarantine identity changed")
        try:
            os.unlink(quarantine, dir_fd=self._root_fd)
        except OSError as exc:
            raise PayslipIntakeError("payslip document could not be deleted") from exc
        self._records.pop(intake_id, None)

    def _persist_pending(self, intake_id: str, record: _StoredPayslip) -> None:
        """Persist only redacted file identity after the private write succeeds."""
        try:
            with database._connection() as conn:
                conn.execute(
                    """INSERT INTO paye_payslip_intakes
                       (storage_id,user_id,session_hash,tax_year,content_type,file_device,file_inode,
                        byte_count,content_sha256,state,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,'pending',?)""",
                    (intake_id, record.owner_user_id, record.session_hash, record.tax_year,
                     record.content_type, record.device, record.inode, record.byte_count,
                     record.content_sha256, self._timestamp()),
                )
        except Exception as exc:
            # This is the ordinary non-crash failure path between file write and
            # metadata commit: delete only the exact file we just verified.
            self._delete(intake_id, record)
            raise PayslipIntakeError("payslip intake metadata could not be stored") from exc

    def _mark_deleting(self, *, intake_id: str, record: _StoredPayslip) -> None:
        with database._connection() as conn:
            changed = conn.execute(
                """UPDATE paye_payslip_intakes
                   SET state='deleting', deletion_started_at=?
                   WHERE storage_id=? AND user_id=? AND session_hash=? AND tax_year=? AND state='pending'""",
                (self._timestamp(), intake_id, record.owner_user_id, record.session_hash, record.tax_year),
            ).rowcount
        if changed != 1:
            raise PayslipIntakeError("payslip intake is unavailable")

    def _remove_completed_metadata(self, intake_id: str) -> None:
        with database._connection() as conn:
            conn.execute(
                "DELETE FROM paye_payslip_intakes WHERE storage_id=? AND state='deleting'",
                (intake_id,),
            )

    def _record_from_row(self, row) -> tuple[str, _StoredPayslip] | None:
        try:
            intake_id = row["storage_id"]
            if type(intake_id) is not str or _STORAGE_ID.fullmatch(intake_id) is None:
                return None
            owner = self._owner(row["user_id"])
            session_hash = row["session_hash"]
            year = self._year(row["tax_year"])
            content_type = row["content_type"]
            if type(session_hash) is not str or re.fullmatch(r"[0-9a-f]{64}", session_hash) is None or content_type not in _TYPES:
                return None
            device, inode, byte_count, content_sha256 = (
                row["file_device"], row["file_inode"], row["byte_count"], row["content_sha256"],
            )
            if (type(device) is not int or type(inode) is not int or type(byte_count) is not int
                    or not 0 < byte_count <= MAX_PAYSLIP_BYTES
                    or type(content_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", content_sha256) is None):
                return None
            path = self._path_for(intake_id, content_type)
            return intake_id, _StoredPayslip(owner, session_hash, year, content_type, path,
                                              device, inode, byte_count, content_sha256)
        except (KeyError, PayslipIntakeError, TypeError):
            return None

    def _receipt(self, *, storage_id: str | None, filename_class: str, reason: str,
                 metadata: os.stat_result | None) -> None:
        device = None if metadata is None else metadata.st_dev
        inode = None if metadata is None else metadata.st_ino
        size = None if metadata is None else metadata.st_size
        key = hashlib.sha256(
            f"reserved:payslip-quarantine:v1\0{storage_id or ''}\0{filename_class}\0{reason}\0{device}\0{inode}\0{size}".encode("ascii")
        ).hexdigest()
        with database._connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO paye_payslip_quarantine_receipts
                   (receipt_key,storage_id,filename_class,reason,observed_at,file_device,file_inode,byte_count,content_sha256)
                   VALUES (?,?,?,?,?,?,?,?,NULL)""",
                (key, storage_id, filename_class, reason, self._timestamp(), device, inode, size),
            )

    def _inventory_startup(self, rows) -> None:
        """Quarantine unknown regular files without reading or deleting content."""
        expected = {}
        for row in rows:
            decoded = self._record_from_row(row)
            if decoded is not None:
                intake_id, record = decoded
                expected[(intake_id, _TYPES[record.content_type][0], row["state"])] = record
        for name in os.listdir(self._root_fd):
            if name == ".quarantine":
                continue
            match = _DOCUMENT_NAME.fullmatch(name) or _DELETING_NAME.fullmatch(name)
            deletion_name = name.startswith(".deleting-")
            filename_class = "deletion_quarantine" if deletion_name else "server_document" if match else "malformed"
            storage_id = match.group(1) if match else None
            try:
                metadata = os.stat(name, dir_fd=self._root_fd, follow_symlinks=False)
            except OSError:
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="unavailable", metadata=None)
                continue
            if not match:
                self._receipt(storage_id=None, filename_class="malformed", reason="malformed_name", metadata=metadata)
                continue
            if stat.S_ISLNK(metadata.st_mode):
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="symlink", metadata=metadata)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="non_regular", metadata=metadata)
                continue
            state = "deleting" if deletion_name else "pending"
            record = expected.get((storage_id, match.group(2), state))
            if record is not None and self._matches(record, metadata):
                continue
            if record is not None:
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="identity_mismatch", metadata=metadata)
                continue
            if any(key[0] == storage_id and key[1] == match.group(2) for key in expected):
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="lifecycle_state_mismatch", metadata=metadata)
                continue
            # Persist a sanitized receipt first: if the process crashes before
            # rename, the next inventory pass retries; after rename it is idempotent.
            self._receipt(storage_id=storage_id, filename_class=filename_class, reason="untracked_regular", metadata=metadata)
            destination = f"{filename_class}-{storage_id}-{metadata.st_dev}-{metadata.st_ino}.{match.group(2)}"
            try:
                os.stat(destination, dir_fd=self._quarantine_fd, follow_symlinks=False)
            except FileNotFoundError:
                try:
                    os.rename(name, destination, src_dir_fd=self._root_fd, dst_dir_fd=self._quarantine_fd)
                except OSError:
                    self._receipt(storage_id=storage_id, filename_class=filename_class, reason="quarantine_move_failed", metadata=metadata)
            except OSError:
                self._receipt(storage_id=storage_id, filename_class=filename_class, reason="quarantine_unavailable", metadata=metadata)

    def _recover_after_restart(self) -> None:
        """Recover only records whose durable file identity still matches.

        A pre-metadata crash leaves no durable identity, so its unknown file is
        preserved for operational quarantine/disposition rather than guessed at
        or deleted.  A
        ``deleting`` record has such an identity and may be deleted on recovery
        only after the same device/inode/size checks used at runtime.
        """
        with database._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM paye_payslip_intakes WHERE state IN ('pending', 'deleting')"
            ).fetchall()
        self._inventory_startup(rows)
        for row in rows:
            decoded = self._record_from_row(row)
            if decoded is None:
                continue
            intake_id, record = decoded
            try:
                metadata = os.stat(
                    self._filename_for(intake_id, record.content_type),
                    dir_fd=self._root_fd, follow_symlinks=False,
                )
            except FileNotFoundError:
                if row["state"] == "deleting":
                    try:
                        self._delete(intake_id, record)
                    except PayslipIntakeError:
                        continue
                    self._remove_completed_metadata(intake_id)
                else:
                    self._remove_missing_metadata(intake_id)
                continue
            except OSError:
                continue
            if not self._matches(record, metadata):
                continue
            if row["state"] == "deleting":
                try:
                    self._delete(intake_id, record)
                except PayslipIntakeError:
                    continue
                self._remove_completed_metadata(intake_id)
            else:
                self._records[intake_id] = record

    def _remove_missing_metadata(self, intake_id: str) -> None:
        with database._connection() as conn:
            conn.execute(
                "DELETE FROM paye_payslip_intakes WHERE storage_id=? AND state='pending'",
                (intake_id,),
            )

    def _owned_record(self, *, handle: PayslipIntakeHandle, authenticated_user_id: object,
                      session_binding: object, tax_year: object) -> tuple[str, _StoredPayslip]:
        self._require_enabled()
        if type(handle) is not PayslipIntakeHandle or _STORAGE_ID.fullmatch(handle.intake_id) is None:
            raise PayslipIntakeError("payslip intake handle is invalid")
        owner = self._owner(authenticated_user_id)
        session_hash = self._session_hash(session_binding)
        year = self._year(tax_year)
        if handle.tax_year != year:
            raise PayslipIntakeError("payslip intake tax year does not match")
        record = self._records.get(handle.intake_id)
        if record is None or (record.owner_user_id != owner or record.session_hash != session_hash
                              or record.tax_year != year):
            raise PayslipIntakeError("payslip intake is unavailable")
        return handle.intake_id, record

    def begin(self, *, authenticated_user_id: int, session_binding: str, tax_year: str,
              content_type: str, document_bytes: bytes) -> PayslipIntakeHandle:
        """Store one bounded raw payslip under a server-generated identity."""
        self._require_enabled()
        owner, session_hash, year = self._owner(authenticated_user_id), self._session_hash(session_binding), self._year(tax_year)
        self._require_registered_owner(owner)
        content_type, document_bytes = self._validate_document(content_type, document_bytes)
        intake_id = secrets.token_hex(32)
        path = self._path_for(intake_id, content_type)
        device, inode, byte_count, content_sha256 = self._write(intake_id, content_type, document_bytes)
        record = _StoredPayslip(owner, session_hash, year, content_type, path, device, inode, byte_count, content_sha256)
        self._persist_pending(intake_id, record)
        self._records[intake_id] = record
        return PayslipIntakeHandle(intake_id=intake_id, tax_year=year)

    def cancel(self, *, handle: PayslipIntakeHandle, authenticated_user_id: int,
               session_binding: str, tax_year: str) -> None:
        """Delete one still-pending raw file for its exact owner/session/year."""
        intake_id, record = self._owned_record(
            handle=handle, authenticated_user_id=authenticated_user_id,
            session_binding=session_binding, tax_year=tax_year,
        )
        self._mark_deleting(intake_id=intake_id, record=record)
        self._delete(intake_id, record)
        self._remove_completed_metadata(intake_id)

    def confirm(self, *, handle: PayslipIntakeHandle, authenticated_user_id: int,
                session_binding: str, tax_year: str, decisions, confirmation_id: str,
                consumed_candidate_digests=frozenset()) -> PayeExtractionConfirmation:
        """Extract and confirm once, always deleting the raw file afterwards."""
        intake_id, record = self._owned_record(
            handle=handle, authenticated_user_id=authenticated_user_id,
            session_binding=session_binding, tax_year=tax_year,
        )
        self._mark_deleting(intake_id=intake_id, record=record)
        try:
            if self._extraction_adapter is None:
                raise PayslipIntakeError("payslip extraction adapter is not configured")
            document_bytes = self._read_verified(intake_id, record)
            candidate = self._extraction_adapter.extract_payslip(
                document_bytes=document_bytes, content_type=record.content_type, tax_year=record.tax_year,
            )
            if type(candidate) is not PayeExtractionCandidate or candidate.tax_year != record.tax_year.replace("/", "-"):
                raise PayslipIntakeError("payslip extraction result is unavailable")
            return confirm_paye_extraction(
                candidate, decisions, confirmation_id,
                consumed_candidate_digests=consumed_candidate_digests,
            )
        except PayslipIntakeError:
            raise
        except Exception as exc:
            raise PayslipIntakeError("payslip extraction or confirmation failed") from exc
        finally:
            self._delete(intake_id, record)
            self._remove_completed_metadata(intake_id)

    def erase_owner_session(self, *, authenticated_user_id: int, session_binding: str) -> int:
        """Delete all pending raw files for one owner and one signed session only."""
        self._require_enabled()
        owner, session_hash = self._owner(authenticated_user_id), self._session_hash(session_binding)
        owned = tuple((intake_id, record) for intake_id, record in self._records.items()
                      if record.owner_user_id == owner and record.session_hash == session_hash)
        for intake_id, record in owned:
            self._mark_deleting(intake_id=intake_id, record=record)
            self._delete(intake_id, record)
            self._remove_completed_metadata(intake_id)
        return len(owned)


__all__ = [
    "MAX_PAYSLIP_BYTES",
    "PayslipExtractionAdapter",
    "PayslipIntakeBoundary",
    "PayslipIntakeError",
    "PayslipIntakeHandle",
]
