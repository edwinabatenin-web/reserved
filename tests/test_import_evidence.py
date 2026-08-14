from datetime import date, datetime, timezone

from reserved.providers.import_evidence import (
    CompletenessStatus,
    EvidenceContractError,
    FitnessStatus,
    ImportManifest,
    ImportPurpose,
    ImportScope,
    assess_fitness,
)


UTC = timezone.utc


def manifest(**overrides):
    values = {
        "run_id": "xero-run-20260813-001",
        "scope": ImportScope("xero", "demo", "opaque-business-001", "invoices", date(2026, 4, 6), date(2027, 4, 5)),
        "started_at": datetime(2026, 8, 13, 1, 0, tzinfo=UTC),
        "completed_at": datetime(2026, 8, 13, 1, 1, tzinfo=UTC),
        "page_count": 2,
        "fetched_count": 101,
        "unique_count": 101,
        "terminal_page_observed": True,
        "source_total_count": 101,
        "source_watermark": datetime(2026, 8, 12, 23, 59, tzinfo=UTC),
        "redacted_artifact_sha256": "a" * 64,
    }
    values.update(overrides)
    return ImportManifest(**values)


def test_complete_requires_terminal_page_unique_records_and_matching_source_total():
    assert manifest().status is CompletenessStatus.COMPLETE


def test_missing_provider_total_is_explicitly_unverified_not_complete():
    assert manifest(source_total_count=None).status is CompletenessStatus.UNVERIFIED


def test_missing_terminal_or_count_mismatch_is_incomplete():
    assert manifest(terminal_page_observed=False).status is CompletenessStatus.INCOMPLETE
    assert manifest(source_total_count=102).status is CompletenessStatus.INCOMPLETE
    assert manifest(unique_count=100).status is CompletenessStatus.INCOMPLETE


def test_evidence_summary_excludes_payload_tokens_urls_and_account_details():
    summary = manifest().evidence_summary()
    rendered = repr(summary)
    for forbidden in ("access_token", "refresh_token", "https://", "account_number", "payload"):
        assert forbidden not in rendered
    assert summary["completeness_status"] == "complete"


def test_references_reject_urls_queries_whitespace_and_embedded_credentials():
    for unsafe in (
        "https://provider.example/business/1",
        "business?id=1",
        "business with spaces",
        "user:secret@business",
    ):
        try:
            ImportScope("xero", "demo", unsafe, "invoices")
        except EvidenceContractError:
            pass
        else:
            raise AssertionError(f"Unsafe evidence reference accepted: {unsafe}")


def test_live_environment_and_reversed_window_are_rejected():
    for kwargs in (
        {"environment": "production"},
        {"window_start": date(2027, 4, 5), "window_end": date(2026, 4, 6)},
    ):
        values = {"provider": "xero", "environment": "demo", "business_reference": "business", "resource": "invoices"}
        values.update(kwargs)
        try:
            ImportScope(**values)
        except EvidenceContractError:
            pass
        else:
            raise AssertionError("Unsafe import scope accepted")


def test_manifest_rejects_impossible_counts_times_and_digest():
    cases = (
        {"page_count": 0, "fetched_count": 1, "unique_count": 1},
        {"fetched_count": 1, "unique_count": 2, "source_total_count": 1},
        {"completed_at": datetime(2026, 8, 12, tzinfo=UTC)},
        {"redacted_artifact_sha256": "not-a-digest"},
    )
    for overrides in cases:
        try:
            manifest(**overrides)
        except EvidenceContractError:
            pass
        else:
            raise AssertionError(f"Invalid manifest accepted: {overrides}")


def test_manifest_requires_timezone_aware_times():
    try:
        manifest(started_at=datetime(2026, 8, 13, 1, 0))
    except EvidenceContractError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("Naive timestamp accepted")


def test_terminal_unique_import_can_be_sufficient_when_purpose_does_not_need_total():
    evidence = manifest(source_total_count=None)
    purpose = ImportPurpose("dashboard_recent_invoices", require_source_total=False)
    result = assess_fitness(evidence, purpose)
    assert evidence.status is CompletenessStatus.UNVERIFIED
    assert result.status is FitnessStatus.SUFFICIENT_FOR_PURPOSE
    assert result.reasons == ("declared_requirements_satisfied",)


def test_missing_total_is_unverified_when_reconciliation_purpose_requires_it():
    result = assess_fitness(
        manifest(source_total_count=None),
        ImportPurpose("invoice_count_reconciliation", require_source_total=True),
    )
    assert result.status is FitnessStatus.UNVERIFIED
    assert result.reasons == ("source_total_unavailable",)


def test_missing_required_watermark_is_unverified_for_incremental_sync():
    result = assess_fitness(
        manifest(source_watermark=None),
        ImportPurpose("incremental_invoice_sync", require_source_watermark=True),
    )
    assert result.status is FitnessStatus.UNVERIFIED
    assert "source_watermark_unavailable" in result.reasons


def test_contradictory_or_unterminated_evidence_is_inadequate_not_merely_unverified():
    relaxed = ImportPurpose("display_preview", require_source_total=False)
    mismatch = assess_fitness(manifest(source_total_count=102), relaxed)
    unterminated = assess_fitness(manifest(terminal_page_observed=False), relaxed)
    assert mismatch.status is FitnessStatus.INADEQUATE
    assert mismatch.reasons == ("source_total_mismatch",)
    assert unterminated.status is FitnessStatus.INADEQUATE
    assert unterminated.reasons == ("terminal_page_not_observed",)


def test_non_unique_records_are_inadequate_for_normal_import_purpose():
    result = assess_fitness(
        manifest(unique_count=100, source_total_count=None),
        ImportPurpose("normalised_invoice_import"),
    )
    assert result.status is FitnessStatus.INADEQUATE
    assert result.reasons == ("duplicate_or_unidentified_records",)
