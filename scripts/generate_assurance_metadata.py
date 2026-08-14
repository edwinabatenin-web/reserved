#!/usr/bin/env python3
"""
Generate tax-assurance metadata for the Reserved dev-tools page.

Runs the full current release gate and writes
``reserved/assurance_metadata.json`` so the /tax-assurance route can display
live verification statistics, engine version and engine-artefact provenance.

The gate
--------
1. root production suite            ``tests/``
2. current engine artefact suite    ``engine-artefact-assurance/tests/``
   (correctness + production↔artefact parity)
3. current Optimise assurance       ``reserved-optimise-assurance/tests/``

(The independent RW3 fixture-adapter assurance runs inside ``tests/``.)

Usage
-----
    python scripts/generate_assurance_metadata.py

Exit code is non-zero if any gate suite fails, so this can be used as a CI gate.

The ``verified_date`` is deterministic: it honours ``SOURCE_DATE_EPOCH`` and
falls back to the current git commit timestamp.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GATE_SUITES = [
    "tests/",
    "engine-artefact-assurance/tests/",
    "reserved-optimise-assurance/tests/",
]


def parse_counts(output: str) -> tuple[int, int, int]:
    """Return ``(passed, failed, errors)`` from a pytest ``-q`` summary."""
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


def _git(args: list[str], default: str | None = None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return default
    return proc.stdout.strip() if proc.returncode == 0 else default


def verified_date() -> str:
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


def engine_metadata() -> dict:
    """Engine version and release-artefact provenance (from the artefact)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from reserved_west.artefact import load_engine

    engine, provenance = load_engine()
    return {
        "engine_version": engine.ENGINE_VERSION,
        "rules_version": engine.tax_config.RULES_VERSION,
        "tax_year": engine.tax_config.TAX_YEAR,
        "engine_artefact": provenance,
    }


def run_gate() -> dict:
    """Run each gate suite separately and aggregate the results.

    Suites are run separately (rather than in a single pytest invocation)
    because ``reserved-optimise-assurance`` uses its own ``pytest.ini`` with
    ``python_files = gate*.py``; a single invocation would apply only the root
    config and silently skip those gate-named files.
    """
    total = {"passed": 0, "failed": 0, "errors": 0}
    all_passed = True
    outputs: list[str] = []
    for suite in GATE_SUITES:
        # `-o addopts=` clears the repo's default `-q` so the gate flags are
        # fully explicit and never double up into a summary-less quiet mode.
        result = subprocess.run(
            [sys.executable, "-m", "pytest", suite, "-o", "addopts=", "-q", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        passed, failed, errors = parse_counts(result.stdout + result.stderr)
        total["passed"] += passed
        total["failed"] += failed
        total["errors"] += errors
        all_passed = all_passed and (result.returncode == 0)
        outputs.append(result.stdout + result.stderr)

    total["all_passed"] = all_passed
    total["pytest_output"] = "\n".join(outputs).strip()
    return total


def build_metadata() -> dict:
    test_summary = run_gate()
    eng = engine_metadata()
    metadata = {
        "tax_year": eng["tax_year"],
        "rules_version": eng["rules_version"],
        "engine_version": eng["engine_version"],
        "engine_artefact": eng["engine_artefact"],
        "verified_date": verified_date(),
        "test_counts": {
            "passed": test_summary["passed"],
            "failed": test_summary["failed"],
            "errors": test_summary["errors"],
        },
        "all_tests_passed": test_summary["all_passed"],
        "scope": {
            "in_scope": [
                "Income tax — England/Wales/NI sole traders",
                "Class 4 National Insurance",
                "Student loan Plans 1, 2, 4, 5 and Postgraduate",
                "Pension Relief at Source (basic-rate band extension)",
                "Capital Gains Tax — basic/higher rate split",
                "Annual Exempt Amount offset",
                "Brought-forward loss relief",
            ],
            "out_of_scope": [
                "Scottish income tax",
                "Dividend and savings income",
                "PAYE coding interactions",
                "VAT-registered traders",
                "Residential property CGT rates",
                "BADR / Investors' Relief",
                "Share pooling and same-day/30-day matching",
            ],
        },
        "assumptions": [
            "Illustrative sole-trader estimate only; not a tax return or professional advice.",
            "Scottish income tax, dividend tax, and savings income are outside scope.",
            "Pension contributions are treated as Relief at Source (gross figure expected).",
        ],
    }
    return metadata, test_summary


def main() -> int:
    print("Running release gate…")
    metadata, test_summary = build_metadata()

    out_path = ROOT / "reserved" / "assurance_metadata.json"
    out_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Written → {out_path.relative_to(ROOT)}")

    if test_summary["all_passed"]:
        print(f"✓ {test_summary['passed']} tests passed.")
    else:
        print(
            f"✗ {test_summary['failed']} failed, "
            f"{test_summary['errors']} errors, "
            f"{test_summary['passed']} passed."
        )
        print(test_summary["pytest_output"])

    return 0 if test_summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
