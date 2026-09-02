"""Evidence-contract test for the W9-S1A package.

This test is deterministic and repository-local. It fails when any mandatory
October flow, trust boundary, threat class, unresolved decision owner field,
canonical blocker reference, current safe-default field, or explicit
non-activation statement disappears from the two package documents. It also
proves the package does not modify readiness, release, configuration,
credential, persistence, adapter, route or template files.

The assertions target stable structured headings/IDs/fields and exact path
boundaries — never brittle prose-wide snapshots.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
DATA_FLOW_DOC = DOCS / "W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md"
DECISION_DOC = DOCS / "W9_SECURITY_DECISION_DOSSIER.md"
TEST_FILE = Path(__file__).resolve()

ALLOWED_NEW_PATHS = {
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "docs/W9_SECURITY_DECISION_DOSSIER.md",
    "tests/test_w9_security_evidence.py",
}

# ── Mandatory structured IDs ──────────────────────────────────────────────────

FLOW_IDS = [f"FLOW-{i:02d}" for i in range(1, 13)]
TRUST_BOUNDARY_IDS = [f"TB-{i:02d}" for i in range(1, 12)]
THREAT_IDS = [f"TH-{i:02d}" for i in range(1, 19)]
DECISION_IDS = [f"DEC-{i:02d}" for i in range(1, 12)]

FLOW_FIELDS = [
    "Data class",
    "Subject/owner",
    "Source",
    "Trust boundary crossed",
    "Processing purpose",
    "Allowed destination",
    "Present storage behaviour",
    "Unresolved target storage/retention/deletion",
    "Existing control",
    "Threat/failure mode",
    "Current fail-closed state",
    "Exact closure evidence",
    "Canonical blocker/reference",
]

DECISION_FIELDS = [
    "Decision ID",
    "Accountable decision owner/authority",
    "Why it blocks implementation or activation",
    "Current safe default",
    "Options",
    "Trade-offs/risks",
    "Existing constraints/evidence",
    "Exact evidence required to decide",
    "Downstream packages affected",
    "Gating",
]

CANONICAL_BLOCKER_REFERENCES = [
    "FD-W10-001",
    "W9_COMPLETION_MAP.md",
    "W9_SECURITY_OPERATIONS_GAP_REGISTER.md",
    "reserved_west/release_gate.py",
    "AUTHENTICATION_READINESS.md",
    "PROVIDER_BOUNDARY_ADOPTION.md",
    "PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md",
    "INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md",
    "HMRC_PAYE_FALLBACK_COMPLETION_MAP.md",
    "CUST-01",
    "CUST-02",
    "PERSIST-01",
    "PERSIST-02",
    "DATA-01",
    "DATA-02",
    "DATA-03",
    "PAYSLIP-01",
    "AUTH-01",
    "AUTH-02",
    "AUTH-03",
    "MON-01",
    "OUTAGE-01",
    "INC-01",
    "RUNTIME-01",
    "ACT-01",
    "ACT-02",
    "ACT-03",
    "RELEASE-01",
]

NON_ACTIVATION_PHRASE = (
    "does not activate a provider, permit credentials, prove target operation, "
    "close W9, declare launch readiness, or authorise merge/release/go-live"
)


def _normalise_whitespace(value: str) -> str:
    return " ".join(value.split())

# ── Protected path categories (the package must not touch) ───────────────────

_PROTECTED_PREFIXES = (
    "reserved/providers/",
    "reserved/web/",
    "reserved/api/",
    "reserved/templates/",
    "reserved/static/",
    "reserved/auth.py",
    "reserved/database.py",
    "reserved/config.py",
    "reserved/__init__.py",
    "reserved_west/",
    "reserved/assurance_metadata.json",
    "scripts/",
    ".github/",
)

_PROTECTED_SUBSTRINGS = (
    "readiness",
    "release_gate",
    "oauth_",
    "FOUNDER_DECISIONS",
    "COMPLETION_MAP",
    "GAP_REGISTER",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    return _read(DATA_FLOW_DOC) + "\n" + _read(DECISION_DOC)


def _section_ids(text: str, prefix: str) -> list[str]:
    return re.findall(rf"^###\s+({prefix}-\d{{2}})\b", text, flags=re.MULTILINE)


def _section_blocks(text: str, prefix: str) -> dict[str, str]:
    """Return a mapping of section id -> block text (until the next heading)."""
    headings = list(re.finditer(rf"^###\s+({prefix}-\d{{2}})\b.*$", text, flags=re.MULTILINE))
    blocks: dict[str, str] = {}
    for index, match in enumerate(headings):
        section_id = match.group(1)
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        blocks[section_id] = text[start:end]
    return blocks


def _field_value(block: str, label: str) -> str | None:
    match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*(.*?)\s*\|", block, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


# ── Document presence and structure ───────────────────────────────────────────

def test_package_files_exist_and_are_the_only_new_paths():
    for path in ALLOWED_NEW_PATHS:
        assert (REPO_ROOT / path).exists(), f"missing package file: {path}"


def test_mandatory_flows_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "FLOW")
    missing = [i for i in FLOW_IDS if i not in ids]
    assert not missing, f"missing mandatory October flow(s): {missing}"


def test_each_flow_records_all_mandatory_fields():
    blocks = _section_blocks(_read(DATA_FLOW_DOC), "FLOW")
    for flow_id in FLOW_IDS:
        assert flow_id in blocks, f"missing flow block: {flow_id}"
        for label in FLOW_FIELDS:
            value = _field_value(blocks[flow_id], label)
            assert value, f"{flow_id} is missing a non-empty '{label}' field"


def test_mandatory_trust_boundaries_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "TB")
    missing = [i for i in TRUST_BOUNDARY_IDS if i not in ids]
    assert not missing, f"missing mandatory trust boundary(ies): {missing}"


def test_mandatory_threat_classes_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "TH")
    missing = [i for i in THREAT_IDS if i not in ids]
    assert not missing, f"missing mandatory threat class(es): {missing}"


def test_mandatory_decisions_are_present():
    text = _read(DECISION_DOC)
    ids = _section_ids(text, "DEC")
    missing = [i for i in DECISION_IDS if i not in ids]
    assert not missing, f"missing mandatory decision entry(ies): {missing}"


def test_each_decision_records_all_mandatory_fields_including_owner_and_safe_default():
    blocks = _section_blocks(_read(DECISION_DOC), "DEC")
    for decision_id in DECISION_IDS:
        assert decision_id in blocks, f"missing decision block: {decision_id}"
        for label in DECISION_FIELDS:
            value = _field_value(blocks[decision_id], label)
            assert value, f"{decision_id} is missing a non-empty '{label}' field"


def test_canonical_blocker_references_are_present():
    text = _combined()
    missing = [ref for ref in CANONICAL_BLOCKER_REFERENCES if ref not in text]
    assert not missing, f"missing canonical blocker reference(s): {missing}"


def test_explicit_non_activation_statement_is_present_in_both_documents():
    normalised_phrase = _normalise_whitespace(NON_ACTIVATION_PHRASE)
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        text = _normalise_whitespace(_read(path))
        assert normalised_phrase in text, (
            f"{path.name} is missing the explicit non-activation statement"
        )


# ── Exact path boundary: the package must not modify protected files ─────────

def _git_changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # Format: "XY path" or "XY old -> new" (rename); take the last token.
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        paths.append(path)
    return paths


def _is_cache_or_generated(path: str) -> bool:
    return path.startswith((".pytest_cache/", "__pycache__/", ".cache/", "instance/", ".venv/")) or path.endswith(".pyc")


def _is_protected(path: str) -> bool:
    if path in ALLOWED_NEW_PATHS:
        return False
    if path.startswith(_PROTECTED_PREFIXES):
        return True
    lowered = path.lower()
    return any(sub.lower() in lowered for sub in _PROTECTED_SUBSTRINGS)


def test_package_does_not_modify_readiness_release_config_or_source_files():
    changed = [p for p in _git_changed_paths() if not _is_cache_or_generated(p)]
    unexpected = [p for p in changed if p not in ALLOWED_NEW_PATHS]
    assert not unexpected, (
        "W9-S1A package modified unexpected files (readiness/release/config/"
        f"credential/persistence/adapter/route/template): {unexpected}"
    )


def test_package_does_not_touch_protected_files():
    changed = [p for p in _git_changed_paths() if not _is_cache_or_generated(p)]
    protected = [p for p in changed if _is_protected(p)]
    assert not protected, f"W9-S1A package touched protected files: {protected}"
