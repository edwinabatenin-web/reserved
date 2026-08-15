"""Regression tests for the canonical release gate and its exact-contract enforcement."""
import inspect
import subprocess

from reserved_west import release_gate as rg


# ── Authoritative inventory shape ────────────────────────────────────────────

def test_canonical_inventory_has_five_distinct_components():
    ids = [c["id"] for c in rg.CANONICAL_COMPONENTS]
    assert ids == [
        "root_production_suite",
        "artefact_correctness",
        "production_artefact_parity",
        "mandatory_rw3_gate",
        "explore_your_options_assurance",
    ]
    assert len(set(ids)) == len(ids)


def test_inventory_rejects_empty():
    assert rg.validate_inventory([])


def test_inventory_rejects_duplicate_id():
    comps = [{"id": "a", "kind": "rw3"}, {"id": "a", "kind": "rw3"}]
    assert any("duplicate" in e for e in rg.validate_inventory(comps))


def test_inventory_rejects_unknown_kind():
    comps = [{"id": "a", "kind": "nope"}]
    assert any("unknown component kind" in e for e in rg.validate_inventory(comps))


def test_inventory_rejects_pytest_without_path():
    comps = [{"id": "a", "kind": "pytest"}]
    assert any("no path" in e for e in rg.validate_inventory(comps))


# ── Exact canonical contract ─────────────────────────────────────────────────

def _canonical():
    return [dict(c) for c in rg.CANONICAL_COMPONENTS]


def test_canonical_inventory_matches_itself():
    assert rg.validate_inventory_matches_canonical(_canonical()) == []


def test_exact_contract_rejects_rw3_only():
    errs = rg.validate_inventory_matches_canonical([{"id": "mandatory_rw3_gate", "kind": "rw3"}])
    assert any("missing mandatory component" in e for e in errs)
    assert any("root_production_suite" in e for e in errs)


def test_exact_contract_rejects_root_only():
    comps = [{"id": "root_production_suite", "kind": "pytest", "path": "tests/"}]
    errs = rg.validate_inventory_matches_canonical(comps)
    assert any("missing mandatory component" in e for e in errs)


def test_exact_contract_rejects_empty():
    assert rg.validate_inventory_matches_canonical([])


def test_exact_contract_rejects_additional_component():
    comps = _canonical() + [{"id": "extra", "kind": "rw3"}]
    assert any("additional/unknown component" in e for e in rg.validate_inventory_matches_canonical(comps))


def test_exact_contract_rejects_reorder():
    comps = _canonical()
    comps[0], comps[1] = comps[1], comps[0]
    assert rg.validate_inventory_matches_canonical(comps)


def test_exact_contract_rejects_changed_kind():
    comps = _canonical()
    comps[0]["kind"] = "rw3"
    comps[0].pop("path", None)
    assert rg.validate_inventory_matches_canonical(comps)


def test_exact_contract_rejects_changed_path():
    comps = _canonical()
    comps[0]["path"] = "tests_evil/"
    assert rg.validate_inventory_matches_canonical(comps)


def test_exact_contract_rejects_changed_description():
    comps = _canonical()
    comps[0]["description"] = "altered"
    assert rg.validate_inventory_matches_canonical(comps)


def test_exact_contract_rejects_duplicate_id():
    comps = _canonical()
    comps.append(dict(comps[0]))
    assert rg.validate_inventory_matches_canonical(comps)


# ── October blocker-inventory integrity ──────────────────────────────────────

def test_october_inventory_is_complete_and_fail_closed():
    octo = rg.october_launch_candidate()
    assert octo["status"] == "not_ready"
    assert octo["blocker_count"] == 13
    assert octo["blocker_count"] == len(octo["blocking_components"])
    ids = [b["id"] for b in octo["blocking_components"]]
    for required in (
        "paye_evidence_and_forecasting",
        "paye_payslip_manual_evidence_journey",
        "hmrc_integration",
        "freeagent_integration",
        "xero_integration",
        "quickbooks_integration",
        "yapily_ais",
        "yapily_pis",
        "mtd_indication",
        "evidence_persistence_and_deletion",
        "privacy_security_review",
        "target_environment_testing",
        "operational_readiness",
    ):
        assert required in ids
    assert octo["supported_calculation_families"]


def test_october_inventory_validation_passes():
    assert rg.validate_october_inventory() == []


# ── Deterministic identities ─────────────────────────────────────────────────

def test_compute_assurance_identity_is_stable():
    assert rg.compute_assurance_identity() == rg.compute_assurance_identity()


def test_canonical_result_digest_is_stable_and_content_bound():
    r1 = {"schema": "reserved-canonical-gate-result-1", "a": 1, "b": [1, 2]}
    r2 = {"schema": "reserved-canonical-gate-result-1", "b": [1, 2], "a": 1}
    assert rg.canonical_result_digest(r1) == rg.canonical_result_digest(r2)
    assert rg.canonical_result_digest(r1) != rg.canonical_result_digest({**r1, "a": 2})


# ── parse_counts / component execution ───────────────────────────────────────

def test_parse_counts():
    assert rg.parse_counts("1179 passed in 20.00s\n")["passed"] == 1179
    assert rg.parse_counts("10 passed, 2 skipped in 1.00s\n")["skipped"] == 2


def _fake_pytest(monkeypatch, returncode, stdout):
    fake = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")
    monkeypatch.setattr(rg.subprocess, "run", lambda *a, **k: fake)


def test_pytest_component_rejects_zero_collection(monkeypatch):
    _fake_pytest(monkeypatch, 5, "no tests ran in 0.01s\n")
    r = rg._run_pytest_component({"id": "x", "kind": "pytest", "path": "tests/"}, "/tmp/x")
    assert r["status"] == "fail"
    assert r["zero_test"] is True
    assert r["passed"] == 0


def test_pytest_component_rejects_all_skipped(monkeypatch):
    _fake_pytest(monkeypatch, 0, "100 skipped in 0.01s\n")
    r = rg._run_pytest_component({"id": "x", "kind": "pytest", "path": "tests/"}, "/tmp/x")
    assert r["status"] == "fail"
    assert r["passed"] == 0
    assert r["skipped"] == 100


def test_pytest_component_accepts_passing_suite(monkeypatch):
    _fake_pytest(monkeypatch, 0, "10 passed in 0.01s\n")
    r = rg._run_pytest_component({"id": "x", "kind": "pytest", "path": "tests/"}, "/tmp/x")
    assert r["status"] == "pass"
    assert r["passed"] == 10


# ── Production gate never accepts a caller-supplied inventory ────────────────

def test_run_canonical_gate_has_no_components_parameter():
    assert "components" not in inspect.signature(rg.run_canonical_gate).parameters


def test_run_canonical_gate_fails_on_empty_inventory(monkeypatch):
    monkeypatch.setattr(rg, "CANONICAL_COMPONENTS", [])
    result = rg.run_canonical_gate(build_artefact=False)
    assert result["overall_decision"] == "fail"
    assert result["status"] == rg.NARROW_GATE_FAILED
    assert result["inventory_errors"]


# ── Ad-hoc helper is non-canonical ───────────────────────────────────────────

def _fake_rw3_pass(monkeypatch):
    def fake():
        return {
            "id": "mandatory_rw3_gate", "kind": "rw3", "status": "pass",
            "gate_passed": True, "classification_complete": True,
            "classification_counts": {}, "mandatory_executable": {},
            "pending_unsupported_fail_closed": {}, "corpus_id": "x",
        }
    monkeypatch.setattr(rg, "_run_rw3_component", fake)


def test_adhoc_evaluation_is_not_canonical(monkeypatch):
    _fake_rw3_pass(monkeypatch)
    result = rg.evaluate_components_adhoc(
        [{"id": "mandatory_rw3_gate", "kind": "rw3"}], build_artefact=False
    )
    assert result["schema"] == "reserved-gate-adhoc-evaluation-1"
    assert result["canonical"] is False
    assert "status" not in result
    assert "assurance_implementation_identity" not in result
    assert result["overall_decision"] == "pass"


def test_adhoc_evaluation_rejects_empty(monkeypatch):
    result = rg.evaluate_components_adhoc([], build_artefact=False)
    assert result["schema"] == "reserved-gate-adhoc-evaluation-1"
    assert result["canonical"] is False
    assert result["inventory_errors"]


# ── October/render ───────────────────────────────────────────────────────────

def test_october_launch_candidate_is_not_ready_and_lists_blockers():
    octo = rg.october_launch_candidate()
    assert octo["status"] == "not_ready"
    states = {b["state"] for b in octo["blocking_components"]}
    assert states <= {"not_executable", "externally_blocked", "not_implemented", "evidence_missing"}


def test_render_result_renders_invalid_inventory():
    out = rg.render_result({"inventory_errors": ["component inventory is empty"], "components": []})
    assert "INVENTORY INVALID" in out
    assert "RESULT: FAILED" in out
