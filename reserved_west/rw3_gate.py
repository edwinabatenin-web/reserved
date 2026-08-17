"""
Reserved West — distinct, release-blocking RW3 fixture gate.

This is the *executable* mandatory RW3 assurance gate, distinct from the
adapter unit tests that live inside the root pytest suite.  It loads the
integrity-locked corpus, applies an integrity-locked classification manifest,
executes only the classified mandatory subset against the explicitly identified
release artefact, and requires PASS for every mandatory fixture.

Classification
--------------
Every corpus pack is classified into exactly one of (see the classification
manifest ``docs/fixtures/RW3_ASSURANCE_CLASSIFICATION.json``):

  * ``mandatory_executable``            — current engine surface + adapter;
                                          the gate requires PASS.
  * ``pending_unsupported_fail_closed`` — current engine surface but an
                                          unsupported state; the gate requires
                                          an exact fail-closed ERROR with no
                                          monetary output.
  * ``outside_engine_surface``          — a feature outside the income-tax
                                          work package; excluded and reported,
                                          never counted as a PASS.
  * ``applicable_not_executable``       — in scope but no adapter; blocks any
                                          claim that its pack passes.
  * ``historical``                      — retained evidence, not enforced.
  * ``pending_founder_decision``        — cannot be enforced without a
                                          founder/rules/legal decision.

The gate never treats excluded or non-executable fixtures as passed, and never
says the complete RW3 corpus passed while excluded approved packs remain.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .engine_adapters import build_adapters
from .literal_fixture_runner import compare_fixture, load_corpus

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "docs" / "fixtures"
DEFAULT_CORPUS = FIXTURE_DIR / "WP7_ASSURANCE_CORPUS.json"
DEFAULT_CLASSIFICATION = FIXTURE_DIR / "RW3_ASSURANCE_CLASSIFICATION.json"
DEFAULT_INTEGRITY = FIXTURE_DIR / "WP7_FIXTURE_INTEGRITY.json"

CLASSIFICATION_SCHEMA = "rw3-assurance-classification-1"
CLASSIFICATION_VALUES = {
    "mandatory_executable",
    "pending_unsupported_fail_closed",
    "outside_engine_surface",
    "applicable_not_executable",
    "historical",
    "pending_founder_decision",
}

# Fail-closed unsupported states must surface as this exact engine exception.
UNSUPPORTED_EXCEPTION = "UnsupportedStudentLoanPlanCombination"

# Authoritative nested result shapes produced by ``_run_mandatory`` and
# ``_run_fail_closed`` below.  These are imported by the assurance-metadata
# consumer (``scripts/generate_assurance_metadata.py``) so the producer and the
# consumer cannot drift apart on the RW3 execution contract.
MANDATORY_EXECUTABLE_FIELDS = (
    "count",
    "expected_fixture_count",
    "passed",
    "failed",
    "unexpected_error",
    "missing_adapter",
    "inventory_mismatch",
    "failures",
)

PENDING_FAIL_CLOSED_FIELDS = (
    "count",
    "expected_fixture_count",
    "expected_fail_closed",
    "unexpected_pass",
    "unexpected_error",
    "monetary_leak",
    "inventory_mismatch",
    "failures",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Classification manifest ──────────────────────────────────────────────────

def load_classification(
    path: Path | str = DEFAULT_CLASSIFICATION,
    integrity_path: Path | str = DEFAULT_INTEGRITY,
) -> dict:
    """Load and integrity-verify the classification manifest."""
    path = Path(path)
    integrity_path = Path(integrity_path)
    raw = path.read_bytes()
    manifest = json.loads(integrity_path.read_text(encoding="utf-8"))
    expected = manifest.get("classification_manifest")
    if not isinstance(expected, str) or not expected:
        raise RuntimeError("integrity manifest has no classification_manifest entry")
    if _sha256(raw) != expected:
        raise RuntimeError(f"classification manifest integrity failure: {path.name}")
    classification = json.loads(raw.decode("utf-8"))
    _validate_classification(classification)
    return classification


def _validate_classification(classification: dict) -> None:
    if classification.get("schema") != CLASSIFICATION_SCHEMA:
        raise RuntimeError("classification manifest schema mismatch")
    packs = classification.get("packs")
    if not isinstance(packs, dict) or not packs:
        raise RuntimeError("classification manifest has no packs")
    for filename, entry in packs.items():
        if "/" in filename or "\\" in filename:
            raise RuntimeError(f"classification pack must be a local filename: {filename!r}")
        if not isinstance(entry, dict):
            raise RuntimeError(f"classification entry must be an object: {filename!r}")
        if entry.get("classification") not in CLASSIFICATION_VALUES:
            raise RuntimeError(
                f"unknown classification for {filename!r}: {entry.get('classification')!r}"
            )
        count = entry.get("expected_fixture_count")
        if not isinstance(count, int) or count < 0:
            raise RuntimeError(f"classification expected_fixture_count invalid: {filename!r}")


def derive_expected_classification_counts(
    packs_by_filename: dict, classification: dict
) -> dict[str, int]:
    """Derive the complete expected classification inventory from loaded authorities.

    ``packs_by_filename`` maps corpus filenames to loaded (already validated)
    pack dicts; ``classification`` is the integrity-verified classification
    manifest.  Every corpus pack must be classified exactly once, and each pack's
    ``expected_fixture_count`` must equal the actual number of fixtures in the
    integrity-verified pack.  Returns ``{category: authoritative_fixture_count}``
    over exactly ``CLASSIFICATION_VALUES``.
    """
    classified = classification.get("packs")
    if not isinstance(classified, dict):
        raise RuntimeError("classification manifest has no packs")

    # Exact, duplicate-free, unclassified-free correspondence between the corpus
    # and the classification manifest.  A pack omitted, added, moved or left
    # unclassified is a contradiction, never a silently-tolerable difference.
    if set(packs_by_filename) != set(classified):
        missing = set(packs_by_filename) - set(classified)
        extra = set(classified) - set(packs_by_filename)
        if missing:
            raise RuntimeError(
                f"corpus pack(s) missing from classification manifest: {sorted(missing)}"
            )
        raise RuntimeError(
            f"classification manifest lists pack(s) absent from corpus: {sorted(extra)}"
        )

    counts: dict[str, int] = {value: 0 for value in CLASSIFICATION_VALUES}
    for filename, pack in packs_by_filename.items():
        entry = classified[filename]
        actual = len(pack.get("fixtures", []))
        expected = entry.get("expected_fixture_count")
        if type(expected) is not int or expected < 0:
            raise RuntimeError(f"classification expected_fixture_count invalid: {filename!r}")
        if actual != expected:
            raise RuntimeError(
                f"classification expected_fixture_count mismatch for {filename!r}: "
                f"manifest {expected}, corpus {actual}"
            )
        value = entry.get("classification")
        if value not in counts:
            raise RuntimeError(f"unknown classification for {filename!r}: {value!r}")
        counts[value] += actual
    return counts


def authoritative_classification_counts(
    corpus_path: Path | str = DEFAULT_CORPUS,
    classification_path: Path | str = DEFAULT_CLASSIFICATION,
    integrity_path: Path | str = DEFAULT_INTEGRITY,
) -> dict[str, int]:
    """Derive the complete authoritative classification inventory.

    The reported counts in a canonical result are evidence to validate, not the
    source of their own expected values: this recomputes the expected count for
    every category from the integrity-verified corpus allowlist, the
    integrity-verified classification manifest and the actual per-pack fixture
    counts.
    """
    corpus, packs = load_corpus(corpus_path)
    classification = load_classification(classification_path, integrity_path)
    filenames = corpus["included_fixture_packs"]
    if len(filenames) != len(set(filenames)):
        raise RuntimeError("corpus allowlist contains a duplicate pack filename")
    packs_by_filename = dict(zip(filenames, packs))
    return derive_expected_classification_counts(packs_by_filename, classification)


# ── Gate evaluation (pure, testable) ─────────────────────────────────────────

def evaluate_gate(packs_by_filename: dict, classification: dict, adapters: dict, provenance: dict) -> dict:
    """Evaluate the mandatory RW3 gate over ``{filename: pack}``.

    ``packs_by_filename`` maps corpus filenames to loaded (already validated)
    pack dicts.  ``adapters`` and ``provenance`` describe the exact artefact
    under test.
    """
    mandatory = []
    fail_closed = []
    unclassified = []
    excluded: dict = {value: [] for value in CLASSIFICATION_VALUES}

    for filename, pack in packs_by_filename.items():
        entry = classification["packs"].get(filename)
        if entry is None:
            unclassified.append({"filename": filename, "fixture_count": len(pack["fixtures"])})
            continue
        entry["filename"] = filename
        entry["pack"] = pack
        value = entry["classification"]
        if value == "mandatory_executable":
            mandatory.append(entry)
        elif value == "pending_unsupported_fail_closed":
            fail_closed.append(entry)
        else:
            excluded[value].append(
                {"filename": filename, "pack_id": pack["pack_id"], "fixture_count": len(pack["fixtures"])}
            )

    mandatory_results = _run_mandatory(mandatory, adapters)
    fail_closed_results = _run_fail_closed(fail_closed, adapters)

    provenance_ok = bool(
        provenance.get("content_hash")
        and provenance.get("source_commit")
        and provenance.get("engine_version")
        and provenance.get("rules_version")
    )

    mandatory_ok = (
        len(mandatory) > 0
        and mandatory_results["failed"] == 0
        and mandatory_results["unexpected_error"] == 0
        and mandatory_results["missing_adapter"] == 0
        and mandatory_results["inventory_mismatch"] == 0
    )
    fail_closed_ok = (
        fail_closed_results["monetary_leak"] == 0
        and fail_closed_results["unexpected_pass"] == 0
        and fail_closed_results["unexpected_error"] == 0
        and fail_closed_results["inventory_mismatch"] == 0
    )

    counts = {
        value: sum(entry.get("fixture_count", 0) for entry in excluded[value])
        for value in CLASSIFICATION_VALUES
    }
    counts["mandatory_executable"] = mandatory_results["count"]
    counts["pending_unsupported_fail_closed"] = fail_closed_results["count"]

    classification_complete = (
        len(unclassified) == 0
        and counts["applicable_not_executable"] == 0
        and counts["pending_founder_decision"] == 0
    )

    # An incomplete classification (unclassified packs, applicable-but-not-
    # executable packs, or packs awaiting a founder decision) must never yield
    # a fully passing mandatory gate, even if the classified subset passes.
    gate_passed = mandatory_ok and fail_closed_ok and provenance_ok and classification_complete

    return {
        "gate_passed": bool(gate_passed),
        "provenance_ok": provenance_ok,
        "classification_complete": classification_complete,
        "unclassified_packs": unclassified,
        "corpus_id": classification.get("corpus_id"),
        "artefact": {
            "engine_version": provenance.get("engine_version"),
            "rules_version": provenance.get("rules_version"),
            "source_commit": provenance.get("source_commit"),
            "content_hash": provenance.get("content_hash"),
        },
        "mandatory_executable": mandatory_results,
        "pending_unsupported_fail_closed": fail_closed_results,
        "excluded": excluded,
        "classification_counts": counts,
    }


def _run_mandatory(entries: list, adapters: dict) -> dict:
    count = expected = sum(e["expected_fixture_count"] for e in entries)
    results = []
    for entry in entries:
        for fixture in entry["pack"]["fixtures"]:
            results.append((entry["filename"], compare_fixture(fixture, adapters)))

    actual = len(results)
    passed = sum(1 for _, r in results if r["outcome"] == "PASS")
    failed = sum(1 for _, r in results if r["outcome"] == "FAIL")
    unexpected_error = sum(1 for _, r in results if r["outcome"] == "ERROR" and "No adapter" not in r["error"])
    missing_adapter = sum(1 for _, r in results if r["outcome"] == "ERROR" and "No adapter" in r["error"])
    # Any deviation from the locked inventory (shrink or growth) is a gate
    # failure: the approved mandatory set must match the classification.
    inventory_mismatch = abs(actual - expected)

    return {
        "count": actual,
        "expected_fixture_count": expected,
        "passed": passed,
        "failed": failed,
        "unexpected_error": unexpected_error,
        "missing_adapter": missing_adapter,
        "inventory_mismatch": inventory_mismatch,
        "failures": [
            {"fixture_id": r["id"], "pack": filename, "outcome": r["outcome"], "detail": r.get("error") or r.get("variances")}
            for filename, r in results
            if r["outcome"] != "PASS"
        ],
    }


def _run_fail_closed(entries: list, adapters: dict) -> dict:
    count = expected = sum(e["expected_fixture_count"] for e in entries)
    results = []
    for entry in entries:
        for fixture in entry["pack"]["fixtures"]:
            results.append((entry["filename"], compare_fixture(fixture, adapters)))

    actual = len(results)
    expected_fail_closed = sum(1 for _, r in results if r["outcome"] == "ERROR" and UNSUPPORTED_EXCEPTION in r.get("error", ""))
    unexpected_pass = sum(1 for _, r in results if r["outcome"] == "PASS")
    monetary_leak = sum(1 for _, r in results if r["outcome"] != "ERROR" and r.get("actual"))
    unexpected_error = sum(
        1 for _, r in results
        if r["outcome"] == "ERROR" and UNSUPPORTED_EXCEPTION not in r.get("error", "")
    )
    inventory_mismatch = abs(actual - expected)

    return {
        "count": actual,
        "expected_fixture_count": expected,
        "expected_fail_closed": expected_fail_closed,
        "unexpected_pass": unexpected_pass,
        "unexpected_error": unexpected_error,
        "monetary_leak": monetary_leak,
        "inventory_mismatch": inventory_mismatch,
        "failures": [
            {"fixture_id": r["id"], "pack": filename, "outcome": r["outcome"], "detail": r.get("error")}
            for filename, r in results
            if not (r["outcome"] == "ERROR" and UNSUPPORTED_EXCEPTION in r.get("error", ""))
        ],
    }


# ── Orchestration ────────────────────────────────────────────────────────────

def run_mandatory_rw3_gate(
    corpus_path: Path | str = DEFAULT_CORPUS,
    classification_path: Path | str = DEFAULT_CLASSIFICATION,
) -> dict:
    """Run the distinct mandatory RW3 fixture gate against the current artefact."""
    corpus, packs = load_corpus(corpus_path)
    classification = load_classification(classification_path)
    adapters, provenance = build_adapters()

    # ``load_corpus`` preserves the allowlist order, so zip with the filenames.
    filenames = corpus["included_fixture_packs"]
    if len(filenames) != len(packs):
        raise RuntimeError("corpus allowlist and loaded packs differ in length")
    packs_by_filename = dict(zip(filenames, packs))

    result = evaluate_gate(packs_by_filename, classification, adapters, provenance)
    result["classification_manifest_path"] = str(Path(classification_path))
    return result


def main(argv: list[str] | None = None) -> int:
    result = run_mandatory_rw3_gate()
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
