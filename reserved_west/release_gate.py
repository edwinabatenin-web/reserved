"""
Canonical release gate — one mandatory-component inventory, one structured result.

This module is the single source of truth for the gate.  The release-gate CLI
(``scripts/run_release_gate.py``) runs it and renders the result; the metadata
generator (``scripts/generate_assurance_metadata.py``) consumes the persisted
result and does *not* re-implement the inventory, re-run tests or re-derive the
decision.

Two distinct statuses are produced, so a narrow deterministic-engine pass can
never be mistaken for October launch readiness:

* ``deterministic_engine_remediation_gate_passed`` — the bounded, deterministic
  income-tax engine + artefact/loader + RW3 fixture gate.
* ``october_launch_candidate`` — the founder-scoped October product, which is
  ``not_ready`` until every supported calculation family and required customer
  journey is mandatory, executable, independently approved and passing.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Canonical mandatory-component inventory ──────────────────────────────────
# Each component has a distinct id.  An empty, duplicate, malformed or unknown
# inventory must fail before any test executes.
CANONICAL_COMPONENTS = [
    {
        "id": "root_production_suite",
        "kind": "pytest",
        "path": "tests/",
        "description": "Maintained production source (reserved/) test suite.",
    },
    {
        "id": "artefact_correctness",
        "kind": "pytest",
        "path": "engine-artefact-assurance/tests/test_artefact_correctness.py",
        "description": "Verified-artefact correctness against independently derived values.",
    },
    {
        "id": "production_artefact_parity",
        "kind": "pytest",
        "path": "engine-artefact-assurance/tests/test_parity.py",
        "description": "Production-to-artefact parity for the identified source and artefact.",
    },
    {
        "id": "mandatory_rw3_gate",
        "kind": "rw3",
        "description": "Mandatory RW3 fixture execution and classification.",
    },
    {
        "id": "explore_your_options_assurance",
        "kind": "pytest",
        "path": "reserved-optimise-assurance/tests/",
        "description": "Scenario/Explore-your-options assurance applicable to the bounded gate.",
    },
]

VALID_KINDS = {"pytest", "rw3"}

# ── October launch-candidate inventory (founder-scoped, truthful non-passing) ─
# These are the supported-but-unfinished October areas.  They are recorded with
# a precise non-passing state and never reported as passing.
OCTOBER_LAUNCH_COMPONENTS = [
    {"id": "paye_payslip_manual_evidence_journey", "state": "not_executable",
     "note": "Payslip extraction and manual PAYE fallback are not yet end-to-end verified."},
    {"id": "hmrc_integration", "state": "externally_blocked",
     "note": "No production-capable HMRC connection has been end-to-end verified."},
    {"id": "freeagent_integration", "state": "not_implemented",
     "note": "Read-only FreeAgent integration is not implemented/verified."},
    {"id": "xero_integration", "state": "not_implemented",
     "note": "Read-only Xero integration is not implemented/verified."},
    {"id": "quickbooks_integration", "state": "not_implemented",
     "note": "Read-only QuickBooks integration is not implemented/verified."},
    {"id": "yapily_ais", "state": "externally_blocked",
     "note": "Yapily account-information access is not end-to-end verified."},
    {"id": "yapily_pis", "state": "externally_blocked",
     "note": "Customer-authorised payment initiation is not end-to-end verified."},
    {"id": "mtd_indication", "state": "not_executable",
     "note": "Customer MTD indication is not independently assured for October."},
    {"id": "evidence_persistence_and_deletion", "state": "not_implemented",
     "note": "Evidence persistence/deletion controls are not implemented."},
    {"id": "privacy_security_review", "state": "evidence_missing",
     "note": "Privacy/security review evidence is not yet produced."},
    {"id": "target_environment_testing", "state": "evidence_missing",
     "note": "Suite has not been repeated in the target runtime."},
    {"id": "operational_readiness", "state": "not_implemented",
     "note": "Monitoring, backups, incident response and rollback are not evidenced."},
]

# Supported October calculation families: these must be mandatory, executable
# and passing to claim an October pass.  Their current deterministic-engine
# status is recorded separately below.
OCTOBER_CALCULATION_FAMILIES = [
    "paye_multiple_employment",
    "sole_trade",
    "uk_property",
    "foreign_property",
    "dividends",
    "savings",
    "pension_treatment",
    "student_loan_pgl",
    "evidence_reconciliation",
]

# Narrow gate status strings (purpose-specific, never "release_gate_passed").
NARROW_GATE_PASSED = "deterministic_engine_remediation_gate_passed"
NARROW_GATE_FAILED = "deterministic_engine_remediation_gate_failed"


def validate_inventory(components: list) -> list[str]:
    """Return a list of inventory errors; empty means the inventory is valid."""
    errors: list[str] = []
    if not components:
        errors.append("component inventory is empty")
        return errors
    seen: set[str] = set()
    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            errors.append(f"component[{i}] is not an object")
            continue
        cid = comp.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"component[{i}] has no string id")
            continue
        if cid in seen:
            errors.append(f"duplicate component id: {cid}")
        seen.add(cid)
        kind = comp.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"unknown component kind for {cid!r}: {kind!r}")
            continue
        if kind == "pytest":
            path = comp.get("path")
            if not isinstance(path, str) or not path:
                errors.append(f"pytest component {cid!r} has no path")
    return errors


def parse_counts(output: str) -> dict:
    """Return collected/passed/failed/errors/skipped from a pytest summary."""
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        matches = re.findall(r"(\d+)\s+(passed|failed|error|errors|skipped|deselected)\b", line)
        if matches:
            for count_text, kind in matches:
                count = int(count_text)
                if kind == "failed":
                    counts["failed"] = count
                elif kind in ("error", "errors"):
                    counts["errors"] = count
                elif kind == "passed":
                    counts["passed"] = count
                elif kind == "skipped":
                    counts["skipped"] = count
            break
    counts["collected"] = (
        counts["passed"] + counts["failed"] + counts["errors"] + counts["skipped"]
    )
    return counts


def _run_pytest_component(comp: dict, artefact_path: str) -> dict:
    env = dict(os.environ)
    env["RESERVED_ENGINE_ARTEFACT"] = artefact_path
    result = subprocess.run(
        [sys.executable, "-m", "pytest", comp["path"], "-o", "addopts=", "-q", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    counts = parse_counts(result.stdout + result.stderr)
    # A mandatory suite must collect and pass at least one test.
    ok = result.returncode == 0 and counts["passed"] > 0
    return {
        "id": comp["id"],
        "kind": "pytest",
        "status": "pass" if ok else "fail",
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": counts["errors"],
        "skipped": counts["skipped"],
        "collected": counts["collected"],
        "zero_test": counts["collected"] == 0,
        "exit_code": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def _run_rw3_component() -> dict:
    from .rw3_gate import run_mandatory_rw3_gate

    rw3 = run_mandatory_rw3_gate()
    return {
        "id": "mandatory_rw3_gate",
        "kind": "rw3",
        "status": "pass" if rw3["gate_passed"] else "fail",
        "gate_passed": bool(rw3["gate_passed"]),
        "classification_complete": bool(rw3["classification_complete"]),
        "classification_counts": rw3["classification_counts"],
        "mandatory_executable": rw3["mandatory_executable"],
        "pending_unsupported_fail_closed": rw3["pending_unsupported_fail_closed"],
        "corpus_id": rw3["corpus_id"],
    }


def run_canonical_gate(components=None, *, build_artefact: bool = True) -> dict:
    """Build/verify the artefact once, run every component, return one result."""
    from .artefact import load_engine, verify_artefact

    if components is None:
        components = list(CANONICAL_COMPONENTS)

    inventory_errors = validate_inventory(components)
    if inventory_errors:
        return {
            "overall_decision": "fail",
            "status": NARROW_GATE_FAILED,
            "inventory_errors": inventory_errors,
            "components": [],
            "october_launch_candidate": {"status": "not_ready"},
            "failure_reasons": ["invalid mandatory-component inventory"] + inventory_errors,
        }

    # Build and verify the artefact exactly once; record its identity and the
    # maintained production-source identity it was built from.
    module, prov = load_engine(rebuild=build_artefact)
    artefact_path = os.environ.get("RESERVED_ENGINE_ARTEFACT") or str(ROOT / "dist" / "reserved_engine")

    production_source = {
        "source_path": prov.get("source_path"),
        "source_commit": prov.get("source_commit"),
        # Defensive copy: consumers must not be able to mutate the cached
        # provenance through the returned result.
        "source_files": dict(prov.get("source_files") or {}),
    }
    artefact = {
        "path": artefact_path,
        "content_hash": prov.get("content_hash"),
        "source_commit": prov.get("source_commit"),
        "engine_version": prov.get("engine_version"),
        "rules_version": prov.get("rules_version"),
        "tax_year": getattr(module, "tax_config", None) and getattr(module.tax_config, "TAX_YEAR", None),
        "provenance": copy.deepcopy(prov),
    }

    component_results = []
    for comp in components:
        if comp["kind"] == "pytest":
            component_results.append(_run_pytest_component(comp, artefact_path))
        else:
            component_results.append(_run_rw3_component())

    # Fail closed if any component silently rebuilt or altered the artefact.
    artefact_unchanged = True
    try:
        verify_artefact(Path(artefact_path))
    except Exception:  # noqa: BLE001 — any change to the artefact blocks release
        artefact_unchanged = False

    failures = [
        c["id"] for c in component_results if c["status"] != "pass"
    ]
    overall_decision = "pass" if (not failures and artefact_unchanged) else "fail"

    result = {
        "schema": "reserved-canonical-gate-result-1",
        "overall_decision": overall_decision,
        "status": NARROW_GATE_PASSED if overall_decision == "pass" else NARROW_GATE_FAILED,
        "component_inventory": [{"id": c["id"], "kind": c["kind"], "description": c.get("description")} for c in components],
        "production_source": production_source,
        "verified_artefact": artefact,
        "components": component_results,
        "artefact_unchanged": artefact_unchanged,
        "failure_reasons": failures,
        "october_launch_candidate": october_launch_candidate(),
    }
    return result


def october_launch_candidate() -> dict:
    """Founder-scoped October readiness: truthfully ``not_ready``.

    The narrow deterministic-engine gate does not establish October readiness.
    Every supported-but-unfinished October area is recorded with a precise
    non-passing state and never reported as passing.
    """
    blocked = [c for c in OCTOBER_LAUNCH_COMPONENTS if c["state"] != "not_applicable"]
    return {
        "status": "not_ready",
        "supported_calculation_families": OCTOBER_CALCULATION_FAMILIES,
        "blocking_components": blocked,
    }


def render_result(result: dict) -> str:
    """Human-readable rendering of a canonical result."""
    lines = ["═" * 68, "Reserved — canonical release gate", "═" * 68]
    if result.get("inventory_errors"):
        lines.append("INVENTORY INVALID:")
        lines.extend(f"  - {e}" for e in result["inventory_errors"])
        lines.append("RESULT: FAILED")
        return "\n".join(lines)

    lines.append("\n[MANDATORY COMPONENTS]")
    for c in result["components"]:
        if c["kind"] == "pytest":
            line = (
                f"  {'PASS' if c['status'] == 'pass' else 'FAIL':<4} {c['id']:<36} "
                f"{c['passed']} passed, {c['failed']} failed, "
                f"{c['errors']} errors, {c['skipped']} skipped"
            )
        else:
            line = (
                f"  {'PASS' if c['status'] == 'pass' else 'FAIL':<4} {c['id']:<36} "
                f"gate_passed={c['gate_passed']}"
            )
        lines.append(line)

    va = result["verified_artefact"]
    lines.append("\n[IDENTITIES]")
    lines.append(f"  production source  {result['production_source']['source_path']} @ {result['production_source']['source_commit'][:12]}")
    lines.append(f"  verified artefact  {va['content_hash'][:16]} (engine {va['engine_version']}, rules {va['rules_version']})")

    octo = result["october_launch_candidate"]
    lines.append(f"\n[OCTOBER LAUNCH CANDIDATE]  status = {octo['status']}")
    for b in octo["blocking_components"]:
        lines.append(f"  {b['state']:<18} {b['id']}")

    lines.append("\n" + "─" * 68)
    lines.append(f"RESULT: {'PASSED' if result['overall_decision'] == 'pass' else 'FAILED'} ({result['status']})")
    lines.append("═" * 68)
    return "\n".join(lines)
