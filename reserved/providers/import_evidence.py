"""Provider-neutral provenance and completeness evidence for imports.

No provider payloads, tokens, URLs or account details are stored here. Provider
adapters supply opaque business references and counts obtained through their
documented contracts. A complete verdict requires positive termination
evidence; returning some records is never sufficient by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import re


class EvidenceContractError(ValueError):
    pass


class CompletenessStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    UNVERIFIED = "unverified"


class FitnessStatus(str, Enum):
    SUFFICIENT_FOR_PURPOSE = "sufficient_for_purpose"
    UNVERIFIED = "unverified"
    INADEQUATE = "inadequate"


_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _safe_reference(value: str, field: str) -> str:
    if not _SAFE_REFERENCE.fullmatch(value):
        raise EvidenceContractError(
            f"{field} must be an opaque identifier without whitespace or URL/query characters"
        )
    return value


@dataclass(frozen=True)
class ImportScope:
    provider: str
    environment: str
    business_reference: str
    resource: str
    window_start: date | None = None
    window_end: date | None = None

    def __post_init__(self) -> None:
        _safe_reference(self.provider, "provider")
        _safe_reference(self.business_reference, "business_reference")
        _safe_reference(self.resource, "resource")
        if self.environment not in {"sandbox", "test", "demo"}:
            raise EvidenceContractError("Evidence environment must be non-live")
        if self.window_start and self.window_end and self.window_start > self.window_end:
            raise EvidenceContractError("Import window start must not follow its end")


@dataclass(frozen=True)
class ImportManifest:
    run_id: str
    scope: ImportScope
    started_at: datetime
    completed_at: datetime
    page_count: int
    fetched_count: int
    unique_count: int
    terminal_page_observed: bool
    source_total_count: int | None = None
    source_watermark: datetime | None = None
    redacted_artifact_sha256: str | None = None

    def __post_init__(self) -> None:
        _safe_reference(self.run_id, "run_id")
        for name in ("started_at", "completed_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise EvidenceContractError(f"{name} must be timezone-aware")
        if self.completed_at < self.started_at:
            raise EvidenceContractError("Import completion precedes start")
        for name in ("page_count", "fetched_count", "unique_count"):
            if getattr(self, name) < 0:
                raise EvidenceContractError(f"{name} cannot be negative")
        if self.page_count == 0 and self.fetched_count != 0:
            raise EvidenceContractError("Records cannot be evidenced without an observed page")
        if self.unique_count > self.fetched_count:
            raise EvidenceContractError("Unique count cannot exceed fetched count")
        if self.source_total_count is not None and self.source_total_count < 0:
            raise EvidenceContractError("Source total count cannot be negative")
        if self.source_watermark is not None and (
            self.source_watermark.tzinfo is None or self.source_watermark.utcoffset() is None
        ):
            raise EvidenceContractError("Source watermark must be timezone-aware")
        if self.redacted_artifact_sha256 is not None and not _SHA256.fullmatch(
            self.redacted_artifact_sha256
        ):
            raise EvidenceContractError("Artifact digest must be a lowercase SHA-256 value")

    @property
    def status(self) -> CompletenessStatus:
        if not self.terminal_page_observed:
            return CompletenessStatus.INCOMPLETE
        if self.unique_count != self.fetched_count:
            return CompletenessStatus.INCOMPLETE
        if self.source_total_count is None:
            # Terminal pagination is positive evidence for this request, but
            # without a provider total there is no independent count check.
            return CompletenessStatus.UNVERIFIED
        if self.source_total_count != self.fetched_count:
            return CompletenessStatus.INCOMPLETE
        return CompletenessStatus.COMPLETE

    def evidence_summary(self) -> dict:
        """Return a serialisable summary containing no provider payload data."""
        return {
            "run_id": self.run_id,
            "provider": self.scope.provider,
            "environment": self.scope.environment,
            "business_reference": self.scope.business_reference,
            "resource": self.scope.resource,
            "window_start": self.scope.window_start.isoformat() if self.scope.window_start else None,
            "window_end": self.scope.window_end.isoformat() if self.scope.window_end else None,
            "started_at": self.started_at.astimezone(timezone.utc).isoformat(),
            "completed_at": self.completed_at.astimezone(timezone.utc).isoformat(),
            "page_count": self.page_count,
            "fetched_count": self.fetched_count,
            "unique_count": self.unique_count,
            "terminal_page_observed": self.terminal_page_observed,
            "source_total_count": self.source_total_count,
            "source_watermark": (
                self.source_watermark.astimezone(timezone.utc).isoformat()
                if self.source_watermark else None
            ),
            "redacted_artifact_sha256": self.redacted_artifact_sha256,
            "completeness_status": self.status.value,
        }


@dataclass(frozen=True)
class ImportPurpose:
    """Evidence requirements for one named downstream use.

    Requirements must be selected before reviewing the result. They describe
    what that use needs; they must not be relaxed after an import fails.
    """

    purpose_id: str
    require_terminal_page: bool = True
    require_unique_records: bool = True
    require_source_total: bool = False
    require_source_watermark: bool = False

    def __post_init__(self) -> None:
        _safe_reference(self.purpose_id, "purpose_id")


@dataclass(frozen=True)
class FitnessAssessment:
    purpose_id: str
    status: FitnessStatus
    reasons: tuple[str, ...]


def assess_fitness(manifest: ImportManifest, purpose: ImportPurpose) -> FitnessAssessment:
    """Assess evidence against predeclared needs, without inventing certainty."""
    inadequate: list[str] = []
    unverified: list[str] = []

    if purpose.require_terminal_page and not manifest.terminal_page_observed:
        inadequate.append("terminal_page_not_observed")
    if purpose.require_unique_records and manifest.unique_count != manifest.fetched_count:
        inadequate.append("duplicate_or_unidentified_records")
    if (
        manifest.source_total_count is not None
        and manifest.source_total_count != manifest.fetched_count
    ):
        # A contradiction in available evidence is inadequate for every use,
        # even where the use did not require the provider to expose a total.
        inadequate.append("source_total_mismatch")
    if purpose.require_source_total and manifest.source_total_count is None:
        unverified.append("source_total_unavailable")
    if purpose.require_source_watermark and manifest.source_watermark is None:
        unverified.append("source_watermark_unavailable")

    if inadequate:
        return FitnessAssessment(purpose.purpose_id, FitnessStatus.INADEQUATE, tuple(inadequate))
    if unverified:
        return FitnessAssessment(purpose.purpose_id, FitnessStatus.UNVERIFIED, tuple(unverified))
    return FitnessAssessment(
        purpose.purpose_id,
        FitnessStatus.SUFFICIENT_FOR_PURPOSE,
        ("declared_requirements_satisfied",),
    )
