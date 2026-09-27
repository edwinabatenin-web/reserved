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

Exact-contract enforcement
--------------------------
The production gate executes **exactly** the authoritative
``CANONICAL_COMPONENTS`` inventory.  A caller-supplied inventory (for example
an RW3-only or root-only list) can never receive a canonical pass: the
production entry point does not accept an inventory argument at all, and the
canonical result records an ``assurance_implementation_identity`` so the
metadata consumer can reject a result produced by a different/older gate.

An explicitly non-canonical helper (``evaluate_components_adhoc``) exists for
tests that need to exercise an arbitrary component collection.  It never emits
canonical status, never writes a canonical result file and is rejected by
metadata generation by construction (different schema, no canonical status).
"""
from __future__ import annotations

import copy
import hashlib
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
# a precise non-passing state and never reported as passing.  The list is the
# complete founder-required blocker inventory; omission is enforced (see
# ``validate_october_inventory``), never silently made to look closer to ready.
OCTOBER_LAUNCH_COMPONENTS = [
    {"id": "paye_evidence_and_forecasting", "state": "not_executable",
     "note": "A disabled-first authenticated endpoint now consumes one transaction-serialized snapshot of current membership, the durable annual record and owner/year PAYE rows with exact session, annual identity and tax-year binding; activation, independently supplied future-pay facts, external authority composition and target-runtime evidence remain absent."},
    {"id": "paye_payslip_manual_evidence_journey", "state": "not_executable",
     "note": "Structured manual PAYE and a disabled-first raw-payslip boundary now provide owner/session/year isolation, fail-closed injected extraction, crash-durable minimal lifecycle metadata, startup quarantine inventory and verified local cleanup; authenticated route wiring, a reviewed extraction adapter, custody-controlled private target storage, quarantine disposition policy and retention/backup evidence remain absent."},
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
    {"id": "mtd_indication", "state": "evidence_missing",
     "note": "The disabled-first indication route is executable with owner-bound paid access in a production-shaped synthetic process; complete-current-evidence, representative customer-language and target identity/provider evidence remain missing."},
    {"id": "poa_sa_cash_obligation_customer_language", "state": "evidence_missing",
     "note": "The Founder-required Payments on Account/Self Assessment cash-obligation capability lacks the representative customer-language/UX evidence required by W2 terminal check 12."},
    {"id": "evidence_persistence_and_deletion", "state": "evidence_missing",
     "note": "Owner-bound durable annual-position storage, versioning and audit are implemented locally, together with physical local deletion of owned PAYE and annual-position rows after independently verified clearances; approved retention/lawful-basis policy, the external authority verifier, target datastore/key custody, and target backup/restore deletion evidence remain missing."},
    {"id": "privacy_security_review", "state": "evidence_missing",
     "note": "Privacy/security review evidence is not yet produced."},
    {"id": "target_environment_testing", "state": "evidence_missing",
     "note": "Suite has not been repeated in the target runtime."},
    {"id": "operational_readiness", "state": "not_implemented",
     "note": "Monitoring, backups, incident response and rollback are not evidenced."},
    {"id": "subscription_billing", "state": "not_executable",
     "note": "A disabled-first owner-bound Stripe runtime now implements durable idempotency, signed-event reconciliation, entitlement transitions and paid-surface enforcement locally; real provider client/reconciler, credentials/key custody, provider behavior, production datastore and target evidence remain open."},
    {"id": "hicbc_manual_privacy_retention_legal", "state": "privacy_retention_review_required",
     "note": "The mandatory internal privacy/retention review for the HICBC manual partner-estimate journey is not yet accepted; external legal/privacy advice is required only if that review identifies a material unresolved issue."},
    {"id": "hicbc_linked_consent_privacy_security", "state": "privacy_retention_review_required",
     "note": "HICBC linked-account consent, cross-account authorisation and privacy/security evidence await independent review."},
    {"id": "hicbc_annual_integration_assurance", "state": "not_executable",
     "note": "HICBC annual-total/reserve/payment integration is not yet independently assured."},
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
    "hicbc",
    "blind_persons_allowance",
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


# ── Exact canonical contract ─────────────────────────────────────────────────

# Fields that form the recorded execution/display contract of a component.
# Altering any of them changes what the gate executes or records.
_COMPONENT_CONTRACT_FIELDS = ("id", "kind", "path", "description")


def _canonical_component_projection(components: list) -> list[dict]:
    """Project a component list onto its recorded contract fields, preserving order."""
    return [
        {field: comp.get(field) for field in _COMPONENT_CONTRACT_FIELDS}
        for comp in components
    ]


def validate_inventory_matches_canonical(components: list) -> list[str]:
    """Return errors unless ``components`` is *exactly* the canonical inventory.

    This enforces, in production (not merely in a test), that the mandatory
    component inventory is complete, ordered as recorded, free of duplicates,
    and that every id/kind/path/description matches the authoritative
    definitions.  Shape-only validation (``validate_inventory``) is not
    sufficient: an RW3-only or root-only list is rejected here.
    """
    errors = validate_inventory(components)
    if errors:
        return errors

    canonical_ids = [c["id"] for c in CANONICAL_COMPONENTS]
    actual_ids = [c.get("id") for c in components]

    missing = [cid for cid in canonical_ids if cid not in actual_ids]
    extra = [cid for cid in actual_ids if cid not in canonical_ids]
    for cid in missing:
        errors.append(f"missing mandatory component: {cid}")
    for cid in extra:
        errors.append(f"additional/unknown component: {cid}")

    if len(components) != len(CANONICAL_COMPONENTS):
        errors.append(
            f"component count {len(components)} != canonical {len(CANONICAL_COMPONENTS)}"
        )

    if _canonical_component_projection(components) != _canonical_component_projection(CANONICAL_COMPONENTS):
        errors.append("component inventory does not match the authoritative definitions (order/fields)")

    return errors


# ── October blocker-inventory integrity ──────────────────────────────────────

_VALID_OCTOBER_STATES = {
    "not_executable",
    "externally_blocked",
    "not_implemented",
    "evidence_missing",
    "privacy_retention_review_required",
}


def validate_october_inventory() -> list[str]:
    """Return errors if the authoritative October inventory is malformed.

    The complete founder-required blocker inventory must be present and must
    contain only precise non-passing states.  A missing, duplicate or unknown
    blocker (or a blocker that silently looked passing) is a defect.
    """
    errors: list[str] = []
    if not OCTOBER_LAUNCH_COMPONENTS:
        errors.append("october launch component inventory is empty")
    if not OCTOBER_CALCULATION_FAMILIES:
        errors.append("october calculation families inventory is empty")

    ids = [c.get("id") for c in OCTOBER_LAUNCH_COMPONENTS]
    if len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
        errors.append("october launch components have duplicate or missing ids")
    for c in OCTOBER_LAUNCH_COMPONENTS:
        if c.get("state") not in _VALID_OCTOBER_STATES:
            errors.append(
                f"october blocker {c.get('id')!r} has invalid/non-fail-closed state {c.get('state')!r}"
            )

    fam = OCTOBER_CALCULATION_FAMILIES
    if len(set(fam)) != len(fam) or any(not isinstance(f, str) or not f for f in fam):
        errors.append("october calculation families have duplicate or missing ids")
    return errors


# ── Deterministic identities ─────────────────────────────────────────────────

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_json(value) -> str:
    """Canonical JSON serialization used by every identity/digest in this module.

    ``sort_keys`` orders object keys deterministically while list order is
    preserved (so inventory order remains part of the contract); the compact
    separators and ``ensure_ascii=False`` keep the serialization byte-stable.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_result_json(result: dict) -> str:
    """Serialize a canonical result exactly as it is digested."""
    return _stable_json(result)


def canonical_result_digest(result: dict) -> str:
    """Deterministic digest of the complete canonical-result document."""
    return _sha256_bytes(canonical_result_json(result).encode("utf-8"))


# Assurance-implementation identity inputs: any change to these files, the
# authoritative inventories, the adapters or the fixture manifests could alter
# collection, execution, classification or the final decision.
ASSURANCE_IDENTITY_INPUTS = [
    "reserved_west/release_gate.py",
    "reserved_west/rw3_gate.py",
    "reserved_west/artefact.py",
    "reserved_west/engine_adapters.py",
    "reserved_west/literal_fixture_runner.py",
    "scripts/build_engine_artefact.py",
    "scripts/run_release_gate.py",
    "scripts/generate_assurance_metadata.py",
    "docs/fixtures/RW3_ASSURANCE_CLASSIFICATION.json",
    "docs/fixtures/WP7_FIXTURE_INTEGRITY.json",
    "docs/fixtures/WP7_ASSURANCE_CORPUS.json",
]


def compute_assurance_identity() -> str:
    """Deterministic identity over the maintained assurance implementation.

    This is distinct from the repository HEAD, from the maintained production
    engine-source identity, and from the built artefact content identity.  It
    identifies *which* gate implementation produced a result so a result from
    an older or differently defined gate is rejected.
    """
    parts: list[str] = []
    for rel in ASSURANCE_IDENTITY_INPUTS:
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"assurance identity input missing: {rel}")
        parts.append(f"FILE:{rel}")
        parts.append(_sha256_bytes(path.read_bytes()))
    parts.append("CANONICAL_COMPONENTS")
    parts.append(_sha256_bytes(_stable_json(CANONICAL_COMPONENTS).encode("utf-8")))
    parts.append("OCTOBER_LAUNCH_COMPONENTS")
    parts.append(_sha256_bytes(_stable_json(OCTOBER_LAUNCH_COMPONENTS).encode("utf-8")))
    parts.append("OCTOBER_CALCULATION_FAMILIES")
    parts.append(_sha256_bytes(_stable_json(OCTOBER_CALCULATION_FAMILIES).encode("utf-8")))
    return _sha256_bytes("\n".join(parts).encode("utf-8"))


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


def _execute_components(components: list, *, build_artefact: bool) -> dict:
    """Build/verify the artefact once and execute the supplied components.

    Returns the raw execution (component results, identities, artefact
    unchanged flag) without emitting any canonical status or schema.  This is
    the shared execution core; the canonical gate and the ad-hoc test helper
    both build on it.
    """
    from .artefact import load_engine, verify_artefact

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

    return {
        "production_source": production_source,
        "verified_artefact": artefact,
        "component_results": component_results,
        "artefact_unchanged": artefact_unchanged,
    }


def run_canonical_gate(*, build_artefact: bool = True) -> dict:
    """Run the authoritative canonical gate and return the one canonical result.

    The production entry point takes **no** caller-supplied inventory: it always
    executes exactly ``CANONICAL_COMPONENTS`` and enforces the exact contract
    before running anything.  An empty, partial, reordered, duplicate or altered
    inventory therefore can never produce a canonical pass through any
    production entry point.
    """
    components = [dict(c) for c in CANONICAL_COMPONENTS]
    inventory_errors = validate_inventory_matches_canonical(components)
    if inventory_errors:
        return {
            "schema": "reserved-canonical-gate-result-1",
            "overall_decision": "fail",
            "status": NARROW_GATE_FAILED,
            "inventory_errors": inventory_errors,
            "component_inventory": [],
            "components": [],
            "october_launch_candidate": october_launch_candidate(),
            "failure_reasons": ["invalid mandatory-component inventory"] + inventory_errors,
        }

    base = _execute_components(components, build_artefact=build_artefact)
    failures = [c["id"] for c in base["component_results"] if c["status"] != "pass"]
    overall_decision = "pass" if (not failures and base["artefact_unchanged"]) else "fail"

    return {
        "schema": "reserved-canonical-gate-result-1",
        "overall_decision": overall_decision,
        "status": NARROW_GATE_PASSED if overall_decision == "pass" else NARROW_GATE_FAILED,
        "assurance_implementation_identity": compute_assurance_identity(),
        "component_inventory": _canonical_component_projection(components),
        "production_source": base["production_source"],
        "verified_artefact": base["verified_artefact"],
        "components": base["component_results"],
        "artefact_unchanged": base["artefact_unchanged"],
        "failure_reasons": failures,
        "october_launch_candidate": october_launch_candidate(),
    }


def evaluate_components_adhoc(components: list, *, build_artefact: bool = False) -> dict:
    """Non-canonical, explicitly test-only evaluation of an arbitrary inventory.

    This exists so tests can exercise arbitrary component collections without
    being able to obtain a canonical pass.  It:

      * uses a different schema (``reserved-gate-adhoc-evaluation-1``);
      * never emits ``status`` / ``deterministic_engine_remediation_gate_passed``;
      * never records an assurance-implementation identity;
      * never writes a canonical result file or metadata.

    Metadata generation rejects this document by construction.
    """
    components = [dict(c) for c in components]
    inventory_errors = validate_inventory(components)
    if inventory_errors:
        return {
            "schema": "reserved-gate-adhoc-evaluation-1",
            "canonical": False,
            "inventory_errors": inventory_errors,
            "components": [],
        }

    base = _execute_components(components, build_artefact=build_artefact)
    failures = [c["id"] for c in base["component_results"] if c["status"] != "pass"]
    overall_decision = "pass" if (not failures and base["artefact_unchanged"]) else "fail"

    return {
        "schema": "reserved-gate-adhoc-evaluation-1",
        "canonical": False,
        "overall_decision": overall_decision,
        "components": base["component_results"],
        "artefact_unchanged": base["artefact_unchanged"],
        "failure_reasons": failures,
    }


def october_launch_candidate() -> dict:
    """Founder-scoped October readiness: truthfully ``not_ready``.

    The narrow deterministic-engine gate does not establish October readiness.
    Every supported-but-unfinished October area is recorded with a precise
    non-passing state and never reported as passing.  A malformed authoritative
    inventory fails closed rather than looking closer to readiness.
    """
    inventory_errors = validate_october_inventory()
    if inventory_errors:
        return {
            "status": "not_ready",
            "inventory_errors": inventory_errors,
            "blocker_count": 0,
            "supported_calculation_families": [],
            "blocking_components": [],
        }
    blocked = [dict(c) for c in OCTOBER_LAUNCH_COMPONENTS]
    return {
        "status": "not_ready",
        "blocker_count": len(blocked),
        "supported_calculation_families": list(OCTOBER_CALCULATION_FAMILIES),
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
    if result.get("assurance_implementation_identity"):
        lines.append(f"  assurance impl     {result['assurance_implementation_identity'][:16]}")

    octo = result["october_launch_candidate"]
    lines.append(f"\n[OCTOBER LAUNCH CANDIDATE]  status = {octo['status']}  blockers = {octo.get('blocker_count', len(octo.get('blocking_components', [])))}")
    for b in octo["blocking_components"]:
        lines.append(f"  {b['state']:<18} {b['id']}")

    lines.append("\n" + "─" * 68)
    lines.append(f"RESULT: {'PASSED' if result['overall_decision'] == 'pass' else 'FAILED'} ({result['status']})")
    lines.append("═" * 68)
    return "\n".join(lines)
