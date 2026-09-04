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
from reserved_west.rw3_gate import (  # noqa: E402
    CLASSIFICATION_VALUES,
    MANDATORY_EXECUTABLE_FIELDS,
    PENDING_FAIL_CLOSED_FIELDS,
    authoritative_classification_counts,
)

RESULT_PATH = ROOT / "dist" / "release_gate_result.json"
METADATA_PATH = ROOT / "reserved" / "assurance_metadata.json"
RESULT_SCHEMA = "reserved-canonical-gate-result-1"

# Total projection from every canonical October calculation family to its
# human-readable scope group.  Some related families intentionally share one
# label; the separate display order preserves the established metadata order.
OCTOBER_FAMILY_SCOPE_LABELS = {
    "paye_multiple_employment": "PAYE and multiple employments",
    "sole_trade": "Sole-trade income",
    "uk_property": "UK and foreign property income",
    "foreign_property": "UK and foreign property income",
    "dividends": "Dividends and savings interest",
    "savings": "Dividends and savings interest",
    "pension_treatment": "Relief-at-Source pension treatment",
    "student_loan_pgl": "Student and postgraduate loan liability",
    "evidence_reconciliation": "PAYE and multiple employments",
    "hicbc": "High Income Child Benefit Charge (HICBC) — October v1 target (not yet activated)",
    "blind_persons_allowance": "Blind Person's Allowance",
}
OCTOBER_SCOPE_LABEL_ORDER = (
    "PAYE and multiple employments",
    "Sole-trade income",
    "Dividends and savings interest",
    "UK and foreign property income",
    "Student and postgraduate loan liability",
    "Relief-at-Source pension treatment",
    "High Income Child Benefit Charge (HICBC) — October v1 target (not yet activated)",
    "Blind Person's Allowance",
)


def human_readable_in_scope() -> list[str]:
    """Project the complete canonical family inventory into stable UI labels."""
    families = OCTOBER_CALCULATION_FAMILIES
    if type(families) is not list:
        raise RuntimeError(
            "October calculation family inventory must be an exact ordered built-in list"
        )

    expected_families = list(OCTOBER_FAMILY_SCOPE_LABELS)
    if families != expected_families:
        raise RuntimeError(
            "October calculation family ordered human-readable scope projection mismatch: "
            f"actual={families!r}, expected={expected_families!r}"
        )

    projected = {OCTOBER_FAMILY_SCOPE_LABELS[family] for family in families}
    missing_order = projected - set(OCTOBER_SCOPE_LABEL_ORDER)
    if missing_order:
        raise RuntimeError(
            "October calculation family scope labels lack display order: "
            f"{sorted(missing_order)}"
        )

    return [
        "Income tax — England, Wales and Northern Ireland",
        *[label for label in OCTOBER_SCOPE_LABEL_ORDER if label in projected],
        "Bounded Making Tax Digital indication",
    ]


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


def _validate_pytest_component(comp: dict, cid: str, errors: list[str]) -> None:
    """Semantically validate a mandatory pytest component result.

    Syntactic completeness (counts are non-negative ints and sum to
    ``collected``) is necessary but not sufficient: a component must not be
    reported ``pass`` unless its own exit code and counts corroborate it.
    """
    counts = (comp.get("passed"), comp.get("failed"), comp.get("errors"), comp.get("skipped"))
    if not all(isinstance(x, int) and x >= 0 for x in counts):
        errors.append(f"component {cid!r} has invalid counts")
        return
    if comp.get("collected") != sum(counts):
        errors.append(f"component {cid!r} counts are incoherent")
        return

    if comp.get("status") != "pass":
        return

    if comp.get("exit_code") != 0:
        errors.append(f"component {cid!r} passes with exit_code={comp.get('exit_code')!r}")
    if comp.get("zero_test") is not False:
        errors.append(f"component {cid!r} passes with zero_test={comp.get('zero_test')!r}")
    if comp.get("collected") <= 0:
        errors.append(f"component {cid!r} passes with no collected tests")
    if comp.get("passed", 0) <= 0:
        errors.append(f"component {cid!r} passes with zero tests")
    if comp.get("failed", 0) != 0:
        errors.append(f"component {cid!r} passes with {comp.get('failed')} failed tests")
    if comp.get("errors", 0) != 0:
        errors.append(f"component {cid!r} passes with {comp.get('errors')} errored tests")


def _is_nonnegative_int(value) -> bool:
    """True iff ``value`` is an ``int`` (not a bool) and >= 0."""
    return type(value) is int and value >= 0


def _validate_count_section(section, cid: str, label: str, required_fields, errors: list[str]) -> bool:
    """Validate one nested RW3 execution-result section's shape and types.

    Returns ``True`` only when ``section`` is a dict with exactly the required
    fields, every numeric field is a non-negative int (never a bool), and the
    ``failures`` field is a list.  Unknown, missing or malformed fields are
    rejected because they could otherwise hide or obscure a pass decision.
    """
    if not isinstance(section, dict):
        errors.append(f"component {cid!r} {label} is not an object")
        return False

    if set(section) != set(required_fields):
        missing = set(required_fields) - set(section)
        extra = set(section) - set(required_fields)
        if missing:
            errors.append(f"component {cid!r} {label} is missing fields: {sorted(missing)}")
        if extra:
            errors.append(f"component {cid!r} {label} has unknown fields: {sorted(extra)}")

    well_typed = True
    for key in required_fields:
        if key == "failures":
            if not isinstance(section.get(key), list):
                errors.append(f"component {cid!r} {label}.{key} is not a list")
                well_typed = False
        elif not _is_nonnegative_int(section.get(key)):
            errors.append(f"component {cid!r} {label}.{key} is not a non-negative integer")
            well_typed = False
    return well_typed


def _validate_rw3_component(comp: dict, cid: str, errors: list[str], authoritative: dict | None = None) -> None:
    """Validate the complete nested RW3 execution contract.

    A ``pass`` must be derivable from and consistent with every underlying RW3
    field: the classification, the mandatory-executable results, the expected
    fail-closed results, and the top-level gate/classification booleans.
    Contradictory nested evidence (non-zero failure counters, count
    disagreements, unresolved classification, malformed types) is rejected
    rather than overridden by a top-level pass label.

    ``authoritative`` (when provided) is the complete expected classification
    inventory derived independently from the integrity-verified corpus and
    classification manifest; the reported counts must equal it exactly, so an
    omitted, duplicated, moved or offsetting count can never be concealed by an
    unchanged aggregate.
    """
    gate_passed = comp.get("gate_passed")
    classification_complete = comp.get("classification_complete")
    if not isinstance(gate_passed, bool):
        errors.append(f"component {cid!r} has non-boolean gate_passed")
    if not isinstance(classification_complete, bool):
        errors.append(f"component {cid!r} has non-boolean classification_complete")

    # ── Classification counts: exact categories, non-negative ints, mandatory > 0.
    counts = comp.get("classification_counts")
    counts_ok = False
    if not isinstance(counts, dict):
        errors.append(f"component {cid!r} has no classification_counts")
    else:
        counts_ok = True
        if set(counts) != CLASSIFICATION_VALUES:
            missing = CLASSIFICATION_VALUES - set(counts)
            extra = set(counts) - CLASSIFICATION_VALUES
            if missing:
                errors.append(f"component {cid!r} classification_counts is missing categories: {sorted(missing)}")
            if extra:
                errors.append(f"component {cid!r} classification_counts has unknown categories: {sorted(extra)}")
        for key, val in counts.items():
            if not _is_nonnegative_int(val):
                errors.append(f"component {cid!r} classification_counts[{key!r}] is not a non-negative integer")
                counts_ok = False
        if counts_ok and counts.get("mandatory_executable", 0) <= 0:
            errors.append(f"component {cid!r} has no mandatory executable fixtures")
        # Every reported category count must equal the independently derived
        # authoritative count.  Exact per-category equality closes the
        # aggregate-preserving movement/offset defect: a fixture omitted,
        # added, moved or offset between categories changes one or more counts
        # and is therefore rejected even when the total is unchanged.
        if counts_ok and authoritative is not None:
            for key in CLASSIFICATION_VALUES:
                if counts.get(key) != authoritative.get(key):
                    errors.append(
                        f"component {cid!r} classification_counts[{key!r}] "
                        f"{counts.get(key)!r} != authoritative {authoritative.get(key)!r}"
                    )

    # ── Nested execution results: exact shape and types.
    mand = comp.get("mandatory_executable")
    fail = comp.get("pending_unsupported_fail_closed")
    mand_ok = _validate_count_section(mand, cid, "mandatory_executable", MANDATORY_EXECUTABLE_FIELDS, errors)
    fail_ok = _validate_count_section(fail, cid, "pending_unsupported_fail_closed", PENDING_FAIL_CLOSED_FIELDS, errors)

    # ── Classification counts must reconcile with the actual nested counts.
    if counts_ok and mand_ok and counts.get("mandatory_executable") != mand.get("count"):
        errors.append(f"component {cid!r} mandatory count disagrees with classification")
    if counts_ok and fail_ok and counts.get("pending_unsupported_fail_closed") != fail.get("count"):
        errors.append(f"component {cid!r} fail-closed count disagrees with classification")

    if comp.get("status") == "pass":
        if gate_passed is not True:
            errors.append(f"component {cid!r} passes with gate_passed={gate_passed!r}")
        if classification_complete is not True:
            errors.append(f"component {cid!r} passes with incomplete classification")
        if counts_ok:
            if counts.get("applicable_not_executable", 0) != 0 or counts.get("pending_founder_decision", 0) != 0:
                errors.append(f"component {cid!r} passes with unresolved pending/non-executable classification")

        if mand_ok:
            if mand["failed"] != 0:
                errors.append(f"component {cid!r} passes with {mand['failed']} failed mandatory fixtures")
            if mand["missing_adapter"] != 0:
                errors.append(f"component {cid!r} passes with {mand['missing_adapter']} missing mandatory adapters")
            if mand["inventory_mismatch"] != 0:
                errors.append(f"component {cid!r} passes with mandatory inventory mismatch")
            if mand["unexpected_error"] != 0:
                errors.append(f"component {cid!r} passes with {mand['unexpected_error']} unexpected mandatory errors")
            if mand["failures"]:
                errors.append(f"component {cid!r} passes with non-empty mandatory failures")
            if mand["passed"] != mand["count"]:
                errors.append(f"component {cid!r} mandatory passed {mand['passed']} != count {mand['count']}")
            if mand["count"] != mand["expected_fixture_count"]:
                errors.append(f"component {cid!r} mandatory count != expected_fixture_count")

        if fail_ok:
            if fail["unexpected_pass"] != 0:
                errors.append(f"component {cid!r} passes with {fail['unexpected_pass']} unexpected fail-closed passes")
            if fail["monetary_leak"] != 0:
                errors.append(f"component {cid!r} passes with {fail['monetary_leak']} fail-closed monetary leaks")
            if fail["inventory_mismatch"] != 0:
                errors.append(f"component {cid!r} passes with fail-closed inventory mismatch")
            if fail["unexpected_error"] != 0:
                errors.append(f"component {cid!r} passes with {fail['unexpected_error']} unexpected fail-closed errors")
            if fail["failures"]:
                errors.append(f"component {cid!r} passes with non-empty fail-closed failures")
            if fail["expected_fail_closed"] != fail["count"]:
                errors.append(f"component {cid!r} fail-closed expected_fail_closed != count")
            if fail["count"] != fail["expected_fixture_count"]:
                errors.append(f"component {cid!r} fail-closed count != expected_fixture_count")


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

    # Derive the complete authoritative RW3 classification inventory once from
    # the integrity-verified corpus and classification manifest.  The reported
    # counts are evidence to validate, not the source of their own expected
    # values; if those authorities disagree, fail closed.
    authoritative = None
    try:
        authoritative = authoritative_classification_counts()
    except Exception as exc:  # noqa: BLE001 — any authority failure blocks metadata
        errors.append(f"cannot derive authoritative RW3 classification inventory: {exc}")

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
            cid = canonical["id"]
            if comp.get("kind") != canonical["kind"]:
                errors.append(f"component {cid!r} result kind mismatch")
            if comp.get("status") not in ("pass", "fail"):
                errors.append(f"component {cid!r} has no valid status")
            if canonical["kind"] == "pytest":
                _validate_pytest_component(comp, cid, errors)
            else:  # rw3
                _validate_rw3_component(comp, cid, errors, authoritative)

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

    # A6: a passing result must carry no failure evidence.  ``failure_reasons``
    # is the canonical failure inventory; it must be a list, and any non-empty
    # value alongside a pass is contradictory evidence and must be rejected.
    failure_reasons = result.get("failure_reasons")
    if not isinstance(failure_reasons, list):
        errors.append("failure_reasons is not a list")
    elif overall == "pass" and failure_reasons:
        errors.append("overall pass with non-empty failure_reasons")

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
            "in_scope": human_readable_in_scope(),
            "out_of_scope": [
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
