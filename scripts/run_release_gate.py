#!/usr/bin/env python3
"""
Reserved — release gate.

A single entry point that separates the three assurance categories so a
release decision is defensible and reproducible:

  MANDATORY   — must pass; a failure blocks release (non-zero exit).
  DIAGNOSTIC  — informational; run and reported, but never blocks.
  HISTORICAL  — retained evidence; not executed by this gate.

MANDATORY (each covers one or more of the five release gates)
  * root production suite            ``tests/``
  * current engine-artefact suite    ``engine-artefact-assurance/tests/``
      - correctness (Package C)
      - production↔artefact parity (Package B)
  * current Optimise assurance       ``reserved-optimise-assurance/tests/``
  * distinct mandatory RW3 fixture gate (``reserved_west.rw3_gate``), which
    executes the classified mandatory executable corpus against the release
    artefact and requires PASS — separate from the adapter unit tests in
    ``tests/``.

DIAGNOSTIC (reported, never blocking)
  * Reserved West historical harness pointed at the current artefact.  It is
    expected to show Student Loan divergences because its reference calculator
    still uses penny rounding and fail-open simultaneous plans, whereas the
    current product uses annual Self Assessment whole-pound flooring and
    fail-closed unsupported states.

HISTORICAL (retained, not executed)
  * ``reserved-engine-2.0.0`` bundle
  * ``reserved_west/output/`` deliverable documents
  * ``reserved_west/run_assurance.py`` and ``run_stage*.py`` evidence generators
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANDATORY_SUITES = [
    "tests/",
    "engine-artefact-assurance/tests/",
    "reserved-optimise-assurance/tests/",
]


def parse_counts(output: str) -> tuple[int, int, int]:
    passed = failed = errors = 0
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        matches = re.findall(r"(\d+)\s+(passed|failed|error|errors)\b", line)
        if matches:
            for count_text, kind in matches:
                count = int(count_text)
                if kind == "failed":
                    failed = count
                elif kind in ("error", "errors"):
                    errors = count
                elif kind == "passed":
                    passed = count
            return passed, failed, errors
    return passed, failed, errors


def run_suite(suite: str) -> tuple[int, int, int, bool]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", suite, "-o", "addopts=", "-q", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    passed, failed, errors = parse_counts(result.stdout + result.stderr)
    # A mandatory suite must collect and pass at least one test.  Exit code 0
    # alone is insufficient: a zero-collected suite (pytest exit 5) and an
    # all-skipped suite (exit 0) both report zero passed and must block release.
    ok = result.returncode == 0 and passed > 0
    return passed, failed, errors, ok


def run_mandatory_rw3() -> dict:
    """Run the distinct mandatory RW3 fixture gate against the artefact."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from reserved_west.rw3_gate import run_mandatory_rw3_gate

    return run_mandatory_rw3_gate()


def run_diagnostic() -> dict:
    """Run the Reserved West historical harness (non-blocking)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from collections import Counter

    from reserved_west.runner import run_all
    from reserved_west.scenarios import STAGE_1
    from reserved_west.scenarios_stage2 import STAGE_2
    from reserved_west.scenarios_stage3 import STAGE_3
    from reserved_west.scenarios_stage4 import STAGE_4

    tally: dict = {}
    for name, stage in (("STAGE_1", STAGE_1), ("STAGE_2", STAGE_2),
                        ("STAGE_3", STAGE_3), ("STAGE_4", STAGE_4)):
        results = run_all(stage)
        tally[name] = dict(Counter(r["outcome"] for r in results))
    return tally


def main() -> int:
    print("═" * 68)
    print("Reserved — release gate")
    print("═" * 68)

    mandatory_ok = True
    total = {"passed": 0, "failed": 0, "errors": 0}
    print("\n[MANDATORY]")
    for suite in MANDATORY_SUITES:
        passed, failed, errors, ok = run_suite(suite)
        total["passed"] += passed
        total["failed"] += failed
        total["errors"] += errors
        mandatory_ok = mandatory_ok and ok
        status = "PASS" if ok else "FAIL"
        print(f"  {status:<4} {suite:<42} {passed} passed, {failed} failed, {errors} errors")

    print("\n[MANDATORY — RW3 fixture gate]")
    try:
        rw3 = run_mandatory_rw3()
        m = rw3["mandatory_executable"]
        fc = rw3["pending_unsupported_fail_closed"]
        counts = rw3["classification_counts"]
        rw3_ok = bool(rw3["gate_passed"])
        mandatory_ok = mandatory_ok and rw3_ok
        print(f"  {'PASS' if rw3_ok else 'FAIL':<4} mandatory approved fixtures "
              f"{m['passed']}/{m['count']} passed, {m['failed']} failed, "
              f"{m['unexpected_error']} unexpected-error, {m['missing_adapter']} missing-adapter")
        print(f"       expected fail-closed {fc['expected_fail_closed']}/{fc['count']}; "
              f"excluded: outside-surface {counts['outside_engine_surface']}, "
              f"applicable-not-executable {counts['applicable_not_executable']}")
        print(f"       artefact engine {rw3['artefact']['engine_version']} "
              f"rules {rw3['artefact']['rules_version']} "
              f"content {rw3['artefact']['content_hash'][:16]}")
    except Exception as exc:  # noqa: BLE001 — a broken gate must block release
        mandatory_ok = False
        print(f"  FAIL  RW3 fixture gate raised: {exc}")

    print("\n[DIAGNOSTIC]  (reported, non-blocking)")
    try:
        diag = run_diagnostic()
        for name, tally in diag.items():
            print(f"  INFO  {name:<8} {tally}")
        print("  NOTE  Reserved West reference uses penny Student Loan rounding and")
        print("        fail-open simultaneous plans; divergences from the current")
        print("        artefact (whole-pound floor, fail-closed) are expected.")
    except Exception as exc:  # noqa: BLE001 — diagnostics must never fail the gate
        print(f"  INFO  diagnostic unavailable: {exc}")

    print("\n[HISTORICAL] (retained, not executed)")
    print("  reserved-engine-2.0.0 bundle")
    print("  reserved_west/output/ deliverable documents")
    print("  reserved_west/run_assurance.py, run_stage*.py evidence generators")

    print("\n" + "─" * 68)
    print(f"MANDATORY total: {total['passed']} passed, "
          f"{total['failed']} failed, {total['errors']} errors")
    if mandatory_ok:
        print("RESULT: mandatory gate PASSED")
    else:
        print("RESULT: mandatory gate FAILED")
    print("═" * 68)
    return 0 if mandatory_ok else 1


if __name__ == "__main__":
    sys.exit(main())
