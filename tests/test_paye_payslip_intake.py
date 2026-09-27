"""Hostile tests for the disabled-first raw-payslip intake boundary."""

from __future__ import annotations

from datetime import date

import pytest

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
