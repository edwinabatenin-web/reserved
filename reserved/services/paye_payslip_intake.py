"""Disabled-first, local raw-payslip intake boundary.

The existing extraction-confirmation contract deliberately accepts only a
typed, redacted extraction candidate.  This module is the narrow, private
boundary before that contract: it accepts an already-authenticated owner's
small, recognised document, stores it under a server-generated name, and
deletes it deterministically when it is consumed or cancelled.

It has no Flask route, no database integration, no OCR implementation, and no
network/provider imports.  Extraction is an injected adapter and is fail-closed
when absent.  This is deliberately not a claim that backups, external OCR
providers, or any wider account erasure have completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import re
import secrets
from typing import Protocol

from reserved.engines.paye_extraction_confirmation import (
    PayeExtractionCandidate,
    PayeExtractionConfirmation,
    confirm_paye_extraction,
)


MAX_PAYSLIP_BYTES = 10 * 1024 * 1024
_TAX_YEAR = re.compile(r"[0-9]{4}/[0-9]{2}\Z")
_SESSION = re.compile(r"[A-Za-z0-9_-]{16,256}\Z")
_STORAGE_ID = re.compile(r"[0-9a-f]{64}\Z")
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
    session_binding: str
    tax_year: str
    content_type: str
    path: Path


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
        self._enabled = enabled
        self._extraction_adapter = extraction_adapter
        self._records: dict[str, _StoredPayslip] = {}

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

    @staticmethod
    def _year(value: object) -> str:
        if type(value) is not str or _TAX_YEAR.fullmatch(value) is None:
            raise PayslipIntakeError("tax year is invalid")
        return value

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise PayslipIntakeError("payslip intake is disabled")

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

    def _path_for(self, intake_id: str, content_type: str) -> Path:
        if _STORAGE_ID.fullmatch(intake_id) is None:
            raise PayslipIntakeError("payslip storage identity is invalid")
        suffix = _TYPES[content_type][0]
        path = self._root / f"{intake_id}.{suffix}"
        # The id and suffix are server-controlled; the resolve check also
        # rejects a hostile filesystem substitution before any I/O.
        if path.parent != self._root or path.resolve().parent != self._root:
            raise PayslipIntakeError("payslip storage path is unsafe")
        return path

    def _write(self, path: Path, document_bytes: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = None
        created = False
        try:
            fd = os.open(path, flags, 0o600)
            created = True
            with os.fdopen(fd, "wb") as output:
                fd = None
                output.write(document_bytes)
                output.flush()
                os.fsync(output.fileno())
        except OSError as exc:
            if created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise PayslipIntakeError("payslip document could not be stored") from exc
        finally:
            if fd is not None:
                os.close(fd)
            if path.is_symlink():
                raise PayslipIntakeError("payslip storage path is unsafe")

    def _delete(self, intake_id: str, record: _StoredPayslip) -> None:
        # Reconstruct and validate the path rather than trusting retained input.
        expected = self._path_for(intake_id, record.content_type)
        if record.path != expected or record.path.is_symlink():
            raise PayslipIntakeError("payslip storage path is unsafe")
        try:
            record.path.unlink(missing_ok=True)
        except OSError as exc:
            raise PayslipIntakeError("payslip document could not be deleted") from exc
        self._records.pop(intake_id, None)

    def _owned_record(self, *, handle: PayslipIntakeHandle, authenticated_user_id: object,
                      session_binding: object, tax_year: object) -> tuple[str, _StoredPayslip]:
        self._require_enabled()
        if type(handle) is not PayslipIntakeHandle or _STORAGE_ID.fullmatch(handle.intake_id) is None:
            raise PayslipIntakeError("payslip intake handle is invalid")
        owner = self._owner(authenticated_user_id)
        session = self._session(session_binding)
        year = self._year(tax_year)
        if handle.tax_year != year:
            raise PayslipIntakeError("payslip intake tax year does not match")
        record = self._records.get(handle.intake_id)
        if record is None or (record.owner_user_id != owner or record.session_binding != session
                              or record.tax_year != year):
            raise PayslipIntakeError("payslip intake is unavailable")
        return handle.intake_id, record

    def begin(self, *, authenticated_user_id: int, session_binding: str, tax_year: str,
              content_type: str, document_bytes: bytes) -> PayslipIntakeHandle:
        """Store one bounded raw payslip under a server-generated identity."""
        self._require_enabled()
        owner, session, year = self._owner(authenticated_user_id), self._session(session_binding), self._year(tax_year)
        content_type, document_bytes = self._validate_document(content_type, document_bytes)
        intake_id = secrets.token_hex(32)
        path = self._path_for(intake_id, content_type)
        self._write(path, document_bytes)
        self._records[intake_id] = _StoredPayslip(owner, session, year, content_type, path)
        return PayslipIntakeHandle(intake_id=intake_id, tax_year=year)

    def cancel(self, *, handle: PayslipIntakeHandle, authenticated_user_id: int,
               session_binding: str, tax_year: str) -> None:
        """Delete one still-pending raw file for its exact owner/session/year."""
        intake_id, record = self._owned_record(
            handle=handle, authenticated_user_id=authenticated_user_id,
            session_binding=session_binding, tax_year=tax_year,
        )
        self._delete(intake_id, record)

    def confirm(self, *, handle: PayslipIntakeHandle, authenticated_user_id: int,
                session_binding: str, tax_year: str, decisions, confirmation_id: str,
                consumed_candidate_digests=frozenset()) -> PayeExtractionConfirmation:
        """Extract and confirm once, always deleting the raw file afterwards."""
        intake_id, record = self._owned_record(
            handle=handle, authenticated_user_id=authenticated_user_id,
            session_binding=session_binding, tax_year=tax_year,
        )
        try:
            if self._extraction_adapter is None:
                raise PayslipIntakeError("payslip extraction adapter is not configured")
            document_bytes = record.path.read_bytes()
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

    def erase_owner_session(self, *, authenticated_user_id: int, session_binding: str) -> int:
        """Delete all pending raw files for one owner and one signed session only."""
        self._require_enabled()
        owner, session = self._owner(authenticated_user_id), self._session(session_binding)
        owned = tuple((intake_id, record) for intake_id, record in self._records.items()
                      if record.owner_user_id == owner and record.session_binding == session)
        for intake_id, record in owned:
            self._delete(intake_id, record)
        return len(owned)


__all__ = [
    "MAX_PAYSLIP_BYTES",
    "PayslipExtractionAdapter",
    "PayslipIntakeBoundary",
    "PayslipIntakeError",
    "PayslipIntakeHandle",
]
