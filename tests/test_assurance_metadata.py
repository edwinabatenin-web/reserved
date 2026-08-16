"""Regression tests for the metadata generator that consumes the canonical result."""
import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "assurance_metadata_generator",
        ROOT / "scripts" / "generate_assurance_metadata.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_generator()


@pytest.fixture
def canonical_result(monkeypatch):
    """Produce a complete canonical result with instant fake component execution."""
    from reserved_west import release_gate as rg

    def fake_pytest(comp, artefact_path):
        return {
            "id": comp["id"], "kind": "pytest", "status": "pass",
            "passed": 10, "failed": 0, "errors": 0, "skipped": 0,
            "collected": 10, "zero_test": False, "exit_code": 0, "output": "",
        }

    def fake_rw3():
        return {
            "id": "mandatory_rw3_gate", "kind": "rw3", "status": "pass",
            "gate_passed": True, "classification_complete": True,
            "classification_counts": {
                "mandatory_executable": 43,
                "pending_unsupported_fail_closed": 3,
            },
            "corpus_id": "wp7-corpus",
            "mandatory_executable": {}, "pending_unsupported_fail_closed": {},
        }

    monkeypatch.setattr(rg, "_run_pytest_component", fake_pytest)
    monkeypatch.setattr(rg, "_run_rw3_component", fake_rw3)
    return rg.run_canonical_gate(build_artefact=False)


def _write_result(tmp_path, result):
    path = tmp_path / "release_gate_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return path


def _mutated(result, **changes):
    r = copy.deepcopy(result)
    for key, value in changes.items():
        r[key] = value
    return r


def test_generated_on_honours_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert GEN.generated_on() == "1970-01-01T00:00:00Z"


def test_current_production_source_files_is_nonempty():
    files = GEN.current_production_source_files()
    assert "income_tax.py" in files
    assert "tax_config.py" in files


# ── Basic rejection paths ────────────────────────────────────────────────────

def test_load_canonical_result_rejects_missing(tmp_path):
    with pytest.raises(RuntimeError, match="missing"):
        GEN.load_canonical_result(tmp_path / "does_not_exist.json")


def test_load_canonical_result_rejects_malformed(tmp_path):
    path = tmp_path / "r.json"
    path.write_text("{not json")
    with pytest.raises(RuntimeError, match="malformed"):
        GEN.load_canonical_result(path)


def test_load_canonical_result_rejects_wrong_schema(canonical_result, tmp_path):
    result = _mutated(canonical_result, schema="not-a-known-schema")
    with pytest.raises(RuntimeError, match="schema"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_stale(canonical_result, tmp_path):
    result = copy.deepcopy(canonical_result)
    result["production_source"]["source_files"]["income_tax.py"] = "0" * 64
    with pytest.raises(RuntimeError, match="stale"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_accepts_valid(canonical_result, tmp_path):
    loaded = GEN.load_canonical_result(_write_result(tmp_path, canonical_result))
    assert loaded["overall_decision"] == "pass"
    assert loaded["status"] == "deterministic_engine_remediation_gate_passed"


# ── A3: independent completeness (inventory + component results) ─────────────

def test_load_canonical_result_rejects_rw3_only_inventory(canonical_result, tmp_path):
    from reserved_west import release_gate as rg
    rw3 = [c for c in canonical_result["component_inventory"] if c["id"] == "mandatory_rw3_gate"]
    result = _mutated(canonical_result, component_inventory=rw3)
    with pytest.raises(RuntimeError, match="missing mandatory component"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_reordered_inventory(canonical_result, tmp_path):
    inv = list(canonical_result["component_inventory"])
    inv[0], inv[1] = inv[1], inv[0]
    result = _mutated(canonical_result, component_inventory=inv)
    with pytest.raises(RuntimeError):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_changed_path(canonical_result, tmp_path):
    inv = copy.deepcopy(canonical_result["component_inventory"])
    inv[0]["path"] = "tests_evil/"
    result = _mutated(canonical_result, component_inventory=inv)
    with pytest.raises(RuntimeError):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_missing_component_result(canonical_result, tmp_path):
    comps = [c for c in canonical_result["components"] if c["id"] != "root_production_suite"]
    result = _mutated(canonical_result, components=comps)
    with pytest.raises(RuntimeError, match="missing component result"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_unknown_component_result(canonical_result, tmp_path):
    comps = list(canonical_result["components"]) + [{"id": "extra", "kind": "rw3", "status": "pass"}]
    result = _mutated(canonical_result, components=comps)
    with pytest.raises(RuntimeError, match="unknown component result"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_duplicate_component_result(canonical_result, tmp_path):
    comps = list(canonical_result["components"])
    comps.append(copy.deepcopy(comps[0]))
    result = _mutated(canonical_result, components=comps)
    with pytest.raises(RuntimeError, match="duplicate component result"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_nominal_pass_with_failing_component(canonical_result, tmp_path):
    comps = copy.deepcopy(canonical_result["components"])
    comps[0]["status"] = "fail"
    result = _mutated(canonical_result, components=comps)
    with pytest.raises(RuntimeError, match="overall pass with a failing"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_unknown_status(canonical_result, tmp_path):
    result = _mutated(canonical_result, status="deterministic_engine_remediation_gate_passed_EXTRA")
    with pytest.raises(RuntimeError, match="unknown canonical status"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_zero_test_pass(canonical_result, tmp_path):
    comps = copy.deepcopy(canonical_result["components"])
    for c in comps:
        if c["kind"] == "pytest":
            c["passed"] = 0
            c["collected"] = 0
    result = _mutated(canonical_result, components=comps)
    with pytest.raises(RuntimeError, match="passes with zero tests"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── A4: assurance-implementation identity ────────────────────────────────────

def test_load_canonical_result_rejects_stale_assurance_identity(canonical_result, tmp_path):
    result = _mutated(canonical_result, assurance_implementation_identity="0" * 64)
    with pytest.raises(RuntimeError, match="assurance implementation identity mismatch"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_build_metadata_records_canonical_result_digest(canonical_result):
    meta = GEN.build_metadata(canonical_result)
    assert meta["canonical_result_digest"] == GEN.canonical_result_digest(canonical_result)
    assert len(meta["canonical_result_digest"]) == 64


def test_build_metadata_records_assurance_identity(canonical_result):
    from reserved_west import release_gate as rg
    meta = GEN.build_metadata(canonical_result)
    assert meta["assurance_implementation_identity"] == rg.compute_assurance_identity()


# ── A5: October blocker inventory ────────────────────────────────────────────

def test_load_canonical_result_rejects_missing_october(canonical_result, tmp_path):
    result = _mutated(canonical_result, october_launch_candidate=None)
    with pytest.raises(RuntimeError, match="october_launch_candidate is missing"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_october_blocker_removed(canonical_result, tmp_path):
    octo = copy.deepcopy(canonical_result["october_launch_candidate"])
    octo["blocking_components"] = octo["blocking_components"][:-1]
    octo["blocker_count"] = len(octo["blocking_components"])
    result = _mutated(canonical_result, october_launch_candidate=octo)
    with pytest.raises(RuntimeError, match="october blocker inventory"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_load_canonical_result_rejects_october_pass_status(canonical_result, tmp_path):
    octo = copy.deepcopy(canonical_result["october_launch_candidate"])
    octo["status"] = "ready"
    result = _mutated(canonical_result, october_launch_candidate=octo)
    with pytest.raises(RuntimeError, match="october status"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Ad-hoc result must never be accepted as canonical metadata ───────────────

def test_adhoc_result_is_rejected_by_metadata(monkeypatch, tmp_path):
    from reserved_west import release_gate as rg

    def fake_rw3():
        return {"id": "mandatory_rw3_gate", "kind": "rw3", "status": "pass",
                "gate_passed": True, "classification_complete": True,
                "classification_counts": {}, "corpus_id": "x"}
    monkeypatch.setattr(rg, "_run_rw3_component", fake_rw3)
    adhoc = rg.evaluate_components_adhoc([{"id": "mandatory_rw3_gate", "kind": "rw3"}], build_artefact=False)
    with pytest.raises(RuntimeError, match="schema"):
        GEN.load_canonical_result(_write_result(tmp_path, adhoc))


# ── Metadata content ─────────────────────────────────────────────────────────

def test_build_metadata_records_identity_and_october_status(canonical_result):
    meta = GEN.build_metadata(canonical_result)
    assert meta["status"] == "deterministic_engine_remediation_gate_passed"
    assert meta["october_launch_candidate"]["status"] == "not_ready"
    assert meta["october_launch_candidate"]["blocker_count"] == 13
    assert meta["engine_version"] == "4.0.0"
    assert meta["rules_version"] == "uk-2026-27-v4"
    assert meta.get("period_of_assessment") is None  # removed in favour of tax_year
    assert meta["tax_year"] == "2026/27"
    assert len(meta["engine_artefact"]["content_hash"]) == 64
    assert meta["engine_artefact"]["source_commit"]
    assert meta["production_source"]["source_files"]
    assert meta["rw3_fixture_gate"]["gate_passed"] is True
    assert meta["rw3_fixture_gate"]["classification_counts"]["mandatory_executable"] == 43
    assert meta["rw3_fixture_gate"]["classification_counts"]["pending_unsupported_fail_closed"] == 3
    assert meta["component_inventory"]
    assert meta["assurance_implementation_identity"]
    assert meta["canonical_result_digest"]


# ── F2: semantic validation of canonical evidence ─────────────────────────────

def _mutate_component(result, comp_id, **changes):
    r = copy.deepcopy(result)
    for c in r["components"]:
        if c["id"] == comp_id:
            c.update(changes)
            return r
    raise AssertionError(f"component {comp_id!r} not found")


def test_rejects_pytest_nonzero_exit_code_pass(canonical_result, tmp_path):
    result = _mutate_component(canonical_result, "root_production_suite", exit_code=1)
    with pytest.raises(RuntimeError, match="exit_code"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_pytest_zero_test_flag_pass(canonical_result, tmp_path):
    result = _mutate_component(canonical_result, "root_production_suite", zero_test=True)
    with pytest.raises(RuntimeError, match="zero_test"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_no_collected_tests_pass(canonical_result, tmp_path):
    result = _mutate_component(
        canonical_result, "root_production_suite",
        collected=0, passed=0, failed=0, errors=0, skipped=0,
    )
    with pytest.raises(RuntimeError, match="no collected tests"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_all_skipped_pass(canonical_result, tmp_path):
    result = _mutate_component(
        canonical_result, "root_production_suite",
        collected=10, passed=0, failed=0, errors=0, skipped=10,
    )
    with pytest.raises(RuntimeError, match="zero tests"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_failed_test_count_pass(canonical_result, tmp_path):
    result = _mutate_component(
        canonical_result, "root_production_suite",
        collected=11, passed=10, failed=1, errors=0, skipped=0,
    )
    with pytest.raises(RuntimeError, match="failed tests"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_errored_test_count_pass(canonical_result, tmp_path):
    result = _mutate_component(
        canonical_result, "root_production_suite",
        collected=11, passed=10, failed=0, errors=1, skipped=0,
    )
    with pytest.raises(RuntimeError, match="errored tests"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_rw3_gate_passed_false_pass(canonical_result, tmp_path):
    result = _mutate_component(canonical_result, "mandatory_rw3_gate", gate_passed=False)
    with pytest.raises(RuntimeError, match="gate_passed=False"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_rw3_incomplete_classification_pass(canonical_result, tmp_path):
    result = _mutate_component(canonical_result, "mandatory_rw3_gate", classification_complete=False)
    with pytest.raises(RuntimeError, match="incomplete classification"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_rw3_unresolved_pending_pass(canonical_result, tmp_path):
    result = copy.deepcopy(canonical_result)
    for c in result["components"]:
        if c["id"] == "mandatory_rw3_gate":
            c["classification_counts"]["applicable_not_executable"] = 5
    with pytest.raises(RuntimeError, match="unresolved pending"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_rw3_inconsistent_counts(canonical_result, tmp_path):
    result = copy.deepcopy(canonical_result)
    for c in result["components"]:
        if c["id"] == "mandatory_rw3_gate":
            c["classification_counts"]["mandatory_executable"] = 0
    with pytest.raises(RuntimeError, match="no mandatory executable"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_overall_pass_with_failure_reasons(canonical_result, tmp_path):
    result = _mutated(canonical_result, failure_reasons=["root_production_suite"])
    with pytest.raises(RuntimeError, match="non-empty failure_reasons"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_component_kind_mismatch(canonical_result, tmp_path):
    result = _mutate_component(canonical_result, "root_production_suite", kind="rw3")
    with pytest.raises(RuntimeError, match="kind mismatch"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_missing_artefact_identity(canonical_result, tmp_path):
    result = copy.deepcopy(canonical_result)
    result["verified_artefact"]["content_hash"] = ""
    with pytest.raises(RuntimeError, match="verified-artefact identity"):
        GEN.load_canonical_result(_write_result(tmp_path, result))
