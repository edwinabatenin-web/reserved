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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reserved_west.release_gate import (  # noqa: E402
    CANONICAL_COMPONENTS,
    NARROW_GATE_FAILED,
    NARROW_GATE_PASSED,
    OCTOBER_CALCULATION_FAMILIES,
    OCTOBER_LAUNCH_COMPONENTS,
    canonical_result_digest,
    compute_assurance_identity,
    validate_inventory_matches_canonical,
)

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


def _validate_canonical_result(result: dict) -> list[str]:
    """Independently verify the complete canonical result (fail-closed).

    Metadata consumption must not rely on the gate runner having validated the
    result earlier.  This recomputes the authoritative identities and the exact
    inventory, verifies every mandatory component has exactly one coherent
    result, and checks that the overall decision follows from the complete
    component results.
    """
    errors: list[str] = []

    if result.get("schema") != RESULT_SCHEMA:
        errors.append(f"unrecognised canonical gate result schema: {result.get('schema')!r}")

    required = ("overall_decision", "status", "production_source", "verified_artefact",
                "component_inventory", "components", "assurance_implementation_identity",
                "october_launch_candidate")
    for key in required:
        if key not in result:
            errors.append(f"canonical gate result is missing field: {key}")

    # Status vocabulary must be exactly the purpose-specific narrow-gate values.
    if result.get("status") not in (NARROW_GATE_PASSED, NARROW_GATE_FAILED):
        errors.append(f"unknown canonical status: {result.get('status')!r}")

    # A4: reject a result produced by an older or differently defined gate.
    expected_assurance = compute_assurance_identity()
    if result.get("assurance_implementation_identity") != expected_assurance:
        errors.append("assurance implementation identity mismatch (older/different gate)")

    # Production-source identity: complete and equal to the current source.
    ps = result.get("production_source") or {}
    if not ps.get("source_path") or not ps.get("source_commit"):
        errors.append("incomplete production-source identity")
    recorded_files = ps.get("source_files")
    if not isinstance(recorded_files, dict) or not recorded_files:
        errors.append("canonical gate result has no production source_files identity")
    elif recorded_files != current_production_source_files():
        errors.append("canonical gate result is stale: production source has changed")

    # Verified-artefact identity: complete.
    artefact = result.get("verified_artefact") or {}
    if not artefact.get("content_hash") or not artefact.get("source_commit"):
        errors.append("canonical gate result has no verified-artefact identity")
    if not artefact.get("engine_version") or not artefact.get("rules_version"):
        errors.append("canonical gate result has no engine/rules version identity")
    if not isinstance(artefact.get("provenance"), dict):
        errors.append("canonical gate result has no artefact provenance")

    # A1/A3: the recorded inventory must exactly match the authoritative
    # canonical component definitions (complete, ordered, unaltered).
    inventory = result.get("component_inventory")
    if not isinstance(inventory, list):
        errors.append("component_inventory is not a list")
    else:
        errors.extend(validate_inventory_matches_canonical(inventory))

    # A3: exactly one coherent result per mandatory component; no unknown or
    # duplicate results; counts internally coherent; zero-test can never pass.
    comps = result.get("components")
    canonical_ids = [c["id"] for c in CANONICAL_COMPONENTS]
    if not isinstance(comps, list):
        errors.append("components is not a list")
    else:
        comp_ids = [c.get("id") for c in comps]
        if len(comp_ids) != len(set(comp_ids)):
            errors.append("duplicate component result")
        for cid in [i for i in canonical_ids if i not in comp_ids]:
            errors.append(f"missing component result: {cid}")
        for cid in [i for i in comp_ids if i not in canonical_ids]:
            errors.append(f"unknown component result: {cid}")
        if len(comps) != len(CANONICAL_COMPONENTS):
            errors.append(f"component result count {len(comps)} != canonical {len(CANONICAL_COMPONENTS)}")

        by_id = {c.get("id"): c for c in comps}
        for canonical in CANONICAL_COMPONENTS:
            comp = by_id.get(canonical["id"])
            if comp is None:
                continue
            if comp.get("kind") != canonical["kind"]:
                errors.append(f"component {canonical['id']!r} result kind mismatch")
            if comp.get("status") not in ("pass", "fail"):
                errors.append(f"component {canonical['id']!r} has no valid status")
            if canonical["kind"] == "pytest":
                counts = (comp.get("passed"), comp.get("failed"),
                          comp.get("errors"), comp.get("skipped"))
                if not all(isinstance(x, int) and x >= 0 for x in counts):
                    errors.append(f"component {canonical['id']!r} has invalid counts")
                elif comp.get("collected") != sum(counts):
                    errors.append(f"component {canonical['id']!r} counts are incoherent")
                if comp.get("status") == "pass" and (comp.get("passed", 0) <= 0):
                    errors.append(f"component {canonical['id']!r} passes with zero tests")
            else:  # rw3
                if "gate_passed" not in comp:
                    errors.append(f"component {canonical['id']!r} has no gate_passed")

    # A3: the overall decision must follow from the complete component results.
    overall = result.get("overall_decision")
    if overall not in ("pass", "fail"):
        errors.append(f"unknown overall_decision: {overall!r}")
    elif isinstance(comps, list):
        all_pass = all(c.get("status") == "pass" for c in comps)
        if overall == "pass" and not all_pass:
            errors.append("overall pass with a failing/missing component")
        if overall == "pass" and not result.get("artefact_unchanged"):
            errors.append("overall pass with artefact_unchanged falsy")
        if overall == "fail" and result.get("status") != NARROW_GATE_FAILED:
            errors.append("fail decision with non-failing status")
        if overall == "pass" and result.get("status") != NARROW_GATE_PASSED:
            errors.append("pass decision with non-passing status")

    # A5: complete, fail-closed October blocker inventory.
    octo = result.get("october_launch_candidate")
    if not isinstance(octo, dict):
        errors.append("october_launch_candidate is missing")
    else:
        if octo.get("status") != "not_ready":
            errors.append("october status is not not_ready")
        blockers = octo.get("blocking_components")
        if blockers != [dict(c) for c in OCTOBER_LAUNCH_COMPONENTS]:
            errors.append("october blocker inventory does not match authoritative definitions")
        if octo.get("blocker_count") != len(OCTOBER_LAUNCH_COMPONENTS):
            errors.append("october blocker_count mismatch")
        if octo.get("supported_calculation_families") != list(OCTOBER_CALCULATION_FAMILIES):
            errors.append("october calculation families mismatch")

    return errors


def load_canonical_result(path: Path | str = RESULT_PATH) -> dict:
    """Load and independently validate the canonical gate result (fail closed)."""
    path = Path(path)
    if not path.exists():
        raise RuntimeError(f"canonical gate result is missing: {path}")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"canonical gate result is malformed: {exc}") from exc

    errors = _validate_canonical_result(result)
    if errors:
        raise RuntimeError("canonical gate result is invalid: " + "; ".join(errors))
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
        "assurance_implementation_identity": result.get("assurance_implementation_identity"),
        "canonical_result_digest": canonical_result_digest(result),
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
