#!/usr/bin/env python3
"""
Generate tax-assurance metadata for the Reserved dev-tools page.

Runs the test suite, counts results, and writes
``reserved/assurance_metadata.json`` so the /tax-assurance route can
display live verification stats without hard-coding anything.

Usage
-----
    python scripts/generate_assurance_metadata.py

Exit code is non-zero if any tests fail, so this can be used as a CI gate.
"""
import json
import subprocess
import sys
from datetime import date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Ensure the project root is on sys.path so `reserved` is importable.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_tests() -> dict:
    """Run pytest and return a summary dict."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "--tb=short",
            "--no-header",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr

    # Parse the summary line, e.g. "67 passed in 1.10s"
    # or "1 failed, 66 passed in 5.66s" or "2 errors in 0.5s"
    import re
    passed = 0
    failed = 0
    errors = 0
    # Match the final short-summary line produced by pytest (no -q flag).
    summary_re = re.compile(
        r"(?:(\d+) failed)?[,\s]*(?:(\d+) error(?:s)?)?[,\s]*(?:(\d+) passed)?",
    )
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        # The summary line ends with e.g. "in 0.38s"
        if "passed" in line or "failed" in line or "error" in line:
            m = summary_re.search(line)
            if m:
                failed  = int(m.group(1) or 0)
                errors  = int(m.group(2) or 0)
                passed  = int(m.group(3) or 0)
            # Also try simple word-before pattern as fallback
            if passed == 0 and failed == 0 and errors == 0:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p in ("passed", "passed,") and i > 0:
                        try: passed = int(parts[i - 1])
                        except ValueError: pass
                    if p in ("failed", "failed,") and i > 0:
                        try: failed = int(parts[i - 1])
                        except ValueError: pass
                    if p in ("error", "errors", "error,", "errors,") and i > 0:
                        try: errors = int(parts[i - 1])
                        except ValueError: pass
            break

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "all_passed": result.returncode == 0,
        "pytest_output": output.strip(),
    }


def main() -> int:
    from reserved.engines import tax_config  # noqa: import here to stay in project venv

    print("Running test suite…")
    test_summary = run_tests()

    metadata = {
        "tax_year": tax_config.TAX_YEAR,
        "rules_version": tax_config.RULES_VERSION,
        "verified_date": date.today().isoformat(),
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

    out_path = ROOT / "reserved" / "assurance_metadata.json"
    out_path.write_text(json.dumps(metadata, indent=2))
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
