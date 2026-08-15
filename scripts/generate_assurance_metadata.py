#!/usr/bin/env python3
"""
Generate tax-assurance metadata from the persisted canonical gate result.

This generator consumes the single canonical result written by
``scripts/run_release_gate.py`` (``dist/release_gate_result.json``).  It does
not maintain a second suite inventory, does not re-implement decision logic,
does not re-run tests, does not re-parse a separate pytest regime and does not
rebuild the artefact.  It formats and persists the supplied result and rejects
a missing, malformed, stale or differently identified result.

Exit code matches the canonical result's overall decision, so the CLI, the
metadata status and the process exit status can never disagree.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT_PATH = ROOT / "dist" / "release_gate_result.json"
METADATA_PATH = ROOT / "reserved" / "assurance_metadata.json"
RESULT_SCHEMA = "reserved-canonical-gate-result-1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(args: list[str], default: str | None = None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return default
    return proc.stdout.strip() if proc.returncode == 0 else default


def generated_on() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (ValueError, OSError):
            pass
    commit_epoch = _git(["log", "-1", "--format=%ct"])
    if commit_epoch:
        try:
            return datetime.fromtimestamp(int(commit_epoch), tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (ValueError, OSError):
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_production_source_files() -> dict[str, str]:
    """Recompute the current maintained engine source identity."""
    source = ROOT / "reserved" / "engines"
    files: dict[str, str] = {}
    for path in sorted(source.glob("*.py")):
        files[path.name] = _sha256_bytes(path.read_bytes())
    changelog = source / "CHANGELOG.md"
    if changelog.exists():
        files["CHANGELOG.md"] = _sha256_bytes(changelog.read_bytes())
    return files


def load_canonical_result(path: Path | str = RESULT_PATH) -> dict:
    """Load and validate the canonical gate result (fail closed)."""
    path = Path(path)
    if not path.exists():
        raise RuntimeError(f"canonical gate result is missing: {path}")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"canonical gate result is malformed: {exc}") from exc

    if result.get("schema") != RESULT_SCHEMA:
        raise RuntimeError(f"unrecognised canonical gate result schema: {result.get('schema')!r}")

    required = ("overall_decision", "status", "production_source", "verified_artefact",
                "component_inventory", "components")
    missing = [k for k in required if k not in result]
    if missing:
        raise RuntimeError(f"canonical gate result is missing field(s): {', '.join(missing)}")

    # Reject a stale result: the production source the gate tested must equal the
    # current maintained production source.
    recorded_files = result["production_source"].get("source_files")
    if not isinstance(recorded_files, dict) or not recorded_files:
        raise RuntimeError("canonical gate result has no production source_files identity")
    if recorded_files != current_production_source_files():
        raise RuntimeError("canonical gate result is stale: production source has changed")

    artefact = result["verified_artefact"]
    if not artefact.get("content_hash") or not artefact.get("source_commit"):
        raise RuntimeError("canonical gate result has no verified-artefact identity")

    return result


def rw3_from_result(result: dict) -> dict:
    for comp in result["components"]:
        if comp.get("id") == "mandatory_rw3_gate":
            return {
                "gate_passed": comp.get("gate_passed"),
                "classification_complete": comp.get("classification_complete"),
                "classification_counts": comp.get("classification_counts"),
                "corpus_id": comp.get("corpus_id"),
                "artefact": result["verified_artefact"]["provenance"],
            }
    raise RuntimeError("canonical gate result has no mandatory RW3 component")


def build_metadata(result: dict) -> dict:
    """Format the canonical result into the persisted assurance metadata."""
    artefact = result["verified_artefact"]
    rw3 = rw3_from_result(result)

    passed = sum(c.get("passed", 0) for c in result["components"])
    failed = sum(c.get("failed", 0) for c in result["components"])
    errors = sum(c.get("errors", 0) for c in result["components"])
    skipped = sum(c.get("skipped", 0) for c in result["components"])

    gate_passed = result["overall_decision"] == "pass"
    return {
        "schema": "reserved-assurance-metadata-1",
        "status": result["status"],
        "october_launch_candidate": result["october_launch_candidate"],
        "tax_year": artefact.get("tax_year"),
        "rules_version": artefact.get("rules_version"),
        "engine_version": artefact.get("engine_version"),
        "engine_artefact": artefact.get("provenance"),
        "production_source": result["production_source"],
        "component_inventory": result["component_inventory"],
        "rw3_fixture_gate": rw3,
        "generated_on": generated_on(),
        "test_counts": {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
        },
        "all_tests_passed": gate_passed,
        "scope": {
            "in_scope": [
                "Income tax — England, Wales and Northern Ireland",
                "PAYE and multiple employments",
                "Sole-trade income",
                "Dividends and savings interest",
                "UK and foreign property income",
                "Student and postgraduate loan liability",
                "Relief-at-Source pension treatment",
                "Bounded Making Tax Digital indication",
            ],
            "out_of_scope": [
                "High Income Child Benefit Charge (HICBC) — post-v1",
                "Scottish Income Tax — post-v1",
                "Capital Gains Tax — post-v1",
                "Full MTD filing — post-v1",
            ],
        },
        "assumptions": [
            "An estimate, not a tax return, filing or professional advice.",
            "The £80,000 pension example assumes the gross relief-at-source contribution qualifies for relief; it does not establish annual allowance, carry-forward or personal advice.",
            "Unknown partner and Child Benefit facts are never treated as zero.",
        ],
    }


def main() -> int:
    result = load_canonical_result()
    metadata = build_metadata(result)

    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Written → {METADATA_PATH.relative_to(ROOT)}")
    print(f"status = {metadata['status']}")
    print(f"october_launch_candidate = {metadata['october_launch_candidate']['status']}")
    return 0 if result["overall_decision"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
