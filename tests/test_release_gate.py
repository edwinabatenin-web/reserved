"""Structural regression tests for the canonical release gate."""
import subprocess

from reserved_west import release_gate as rg


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


def test_inventory_accepts_valid_components():
    comps = [
        {"id": "rw3", "kind": "rw3"},
        {"id": "suite", "kind": "pytest", "path": "tests/"},
    ]
    assert rg.validate_inventory(comps) == []


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


def test_run_canonical_gate_fails_on_empty_inventory():
    result = rg.run_canonical_gate(components=[])
    assert result["overall_decision"] == "fail"
    assert result["status"] == rg.NARROW_GATE_FAILED
    assert result["inventory_errors"]


def test_run_canonical_gate_minimal_rw3_inventory_passes():
    result = rg.run_canonical_gate(
        components=[{"id": "mandatory_rw3_gate", "kind": "rw3"}],
        build_artefact=False,
    )
    assert result["overall_decision"] == "pass"
    assert result["status"] == rg.NARROW_GATE_PASSED
    assert result["verified_artefact"]["content_hash"]
    assert result["production_source"]["source_files"]
    assert result["october_launch_candidate"]["status"] == "not_ready"


def test_october_launch_candidate_is_not_ready_and_lists_blockers():
    octo = rg.october_launch_candidate()
    assert octo["status"] == "not_ready"
    states = {b["state"] for b in octo["blocking_components"]}
    assert states <= {"not_executable", "externally_blocked", "not_implemented", "evidence_missing"}


def test_render_result_renders_invalid_inventory():
    out = rg.render_result({"inventory_errors": ["component inventory is empty"], "components": []})
    assert "INVENTORY INVALID" in out
    assert "RESULT: FAILED" in out
