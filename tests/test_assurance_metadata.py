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
                "outside_engine_surface": 61,
                "applicable_not_executable": 0,
                "historical": 0,
                "pending_founder_decision": 0,
            },
            "corpus_id": "wp7-corpus",
            "mandatory_executable": {
                "count": 43, "expected_fixture_count": 43, "passed": 43,
                "failed": 0, "unexpected_error": 0, "missing_adapter": 0,
                "inventory_mismatch": 0, "failures": [],
            },
            "pending_unsupported_fail_closed": {
                "count": 3, "expected_fixture_count": 3, "expected_fail_closed": 3,
                "unexpected_pass": 0, "unexpected_error": 0, "monetary_leak": 0,
                "inventory_mismatch": 0, "failures": [],
            },
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
    assert meta["october_launch_candidate"]["blocker_count"] == 16
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


# ── G2: complete nested RW3 consistency (invariant 2 adversarial) ─────────────
# A pass must be derivable from every nested RW3 execution field; top-level
# pass labels never override contradictory nested evidence.


def _mutate_rw3_nested(result, section, **changes):
    r = copy.deepcopy(result)
    for c in r["components"]:
        if c["id"] == "mandatory_rw3_gate":
            c[section].update(changes)
            return r
    raise AssertionError("mandatory_rw3_gate component not found")


def _mutate_rw3_counts(result, **changes):
    r = copy.deepcopy(result)
    for c in r["components"]:
        if c["id"] == "mandatory_rw3_gate":
            c["classification_counts"].update(changes)
            return r
    raise AssertionError("mandatory_rw3_gate component not found")


def _rw3_component(result):
    for c in result["components"]:
        if c["id"] == "mandatory_rw3_gate":
            return c
    raise AssertionError("mandatory_rw3_gate component not found")


# ── Mandatory-executable failure counters ─────────────────────────────────────

@pytest.mark.parametrize(
    "field,msg",
    [
        ("failed", "failed mandatory"),
        ("missing_adapter", "missing mandatory adapters"),
        ("inventory_mismatch", "mandatory inventory mismatch"),
        ("unexpected_error", "unexpected mandatory errors"),
    ],
)
def test_rejects_each_mandatory_failure_counter(canonical_result, tmp_path, field, msg):
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", **{field: 1})
    with pytest.raises(RuntimeError, match=msg):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Fail-closed failure counters ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "field,msg",
    [
        ("unexpected_pass", "unexpected fail-closed passes"),
        ("monetary_leak", "fail-closed monetary leaks"),
        ("inventory_mismatch", "fail-closed inventory mismatch"),
        ("unexpected_error", "unexpected fail-closed errors"),
    ],
)
def test_rejects_each_fail_closed_counter(canonical_result, tmp_path, field, msg):
    result = _mutate_rw3_nested(canonical_result, "pending_unsupported_fail_closed", **{field: 1})
    with pytest.raises(RuntimeError, match=msg):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Expected / actual / passed / classified counts ────────────────────────────

def test_rejects_mandatory_passed_mismatch(canonical_result, tmp_path):
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", passed=42)
    with pytest.raises(RuntimeError, match="mandatory passed"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_mandatory_count_expected_mismatch(canonical_result, tmp_path):
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", expected_fixture_count=44)
    with pytest.raises(RuntimeError, match="count != expected_fixture_count"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_fail_closed_expected_mismatch(canonical_result, tmp_path):
    result = _mutate_rw3_nested(canonical_result, "pending_unsupported_fail_closed", expected_fail_closed=2)
    with pytest.raises(RuntimeError, match="expected_fail_closed"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_fail_closed_count_expected_mismatch(canonical_result, tmp_path):
    result = _mutate_rw3_nested(canonical_result, "pending_unsupported_fail_closed", expected_fixture_count=4)
    with pytest.raises(RuntimeError, match="count != expected_fixture_count"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_classification_mandatory_disagreement(canonical_result, tmp_path):
    result = _mutate_rw3_counts(canonical_result, mandatory_executable=44)
    with pytest.raises(RuntimeError, match="disagree"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_classification_fail_closed_disagreement(canonical_result, tmp_path):
    result = _mutate_rw3_counts(canonical_result, pending_unsupported_fail_closed=2)
    with pytest.raises(RuntimeError, match="disagree"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Nested sections removed / replaced ────────────────────────────────────────

def test_rejects_missing_mandatory_section(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    del _rw3_component(r)["mandatory_executable"]
    with pytest.raises(RuntimeError, match="mandatory_executable"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_missing_fail_closed_section(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    del _rw3_component(r)["pending_unsupported_fail_closed"]
    with pytest.raises(RuntimeError, match="pending_unsupported_fail_closed"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_mandatory_section_replaced_with_non_object(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    _rw3_component(r)["mandatory_executable"] = "not-an-object"
    with pytest.raises(RuntimeError, match="not an object"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


# ── Missing / extra fields ────────────────────────────────────────────────────

def test_rejects_missing_nested_field(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    del _rw3_component(r)["mandatory_executable"]["failed"]
    with pytest.raises(RuntimeError, match="missing fields"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_extra_nested_field(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    _rw3_component(r)["mandatory_executable"]["sneaky"] = 0
    with pytest.raises(RuntimeError, match="unknown fields"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


# ── Types: boolean / negative / string / float / null / object counts ─────────

@pytest.mark.parametrize("bad", [-1, True, "43", 43.0, None, {"x": 1}])
def test_rejects_non_int_count_values(canonical_result, tmp_path, bad):
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", failed=bad)
    with pytest.raises(RuntimeError):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_boolean_classification_count(canonical_result, tmp_path):
    result = _mutate_rw3_counts(canonical_result, outside_engine_surface=True)
    with pytest.raises(RuntimeError, match="non-negative integer"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_non_list_failures(canonical_result, tmp_path):
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", failures="no")
    with pytest.raises(RuntimeError, match="failures is not a list"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Non-empty failure lists ───────────────────────────────────────────────────

def test_rejects_nonempty_mandatory_failures(canonical_result, tmp_path):
    result = _mutate_rw3_nested(
        canonical_result, "mandatory_executable",
        failures=[{"fixture_id": "x", "pack": "CORE", "outcome": "FAIL"}],
    )
    with pytest.raises(RuntimeError, match="non-empty mandatory failures"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_nonempty_fail_closed_failures(canonical_result, tmp_path):
    result = _mutate_rw3_nested(
        canonical_result, "pending_unsupported_fail_closed",
        failures=[{"fixture_id": "x"}],
    )
    with pytest.raises(RuntimeError, match="non-empty fail-closed failures"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── failure_reasons type/shape ────────────────────────────────────────────────

def test_rejects_failure_reasons_missing(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    del r["failure_reasons"]
    with pytest.raises(RuntimeError, match="failure_reasons is not a list"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_failure_reasons_null(canonical_result, tmp_path):
    result = _mutated(canonical_result, failure_reasons=None)
    with pytest.raises(RuntimeError, match="failure_reasons is not a list"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_failure_reasons_string(canonical_result, tmp_path):
    result = _mutated(canonical_result, failure_reasons="all good")
    with pytest.raises(RuntimeError, match="failure_reasons is not a list"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_failure_reasons_object(canonical_result, tmp_path):
    result = _mutated(canonical_result, failure_reasons={"n": 0})
    with pytest.raises(RuntimeError, match="failure_reasons is not a list"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── Classification categories missing / added / zero mandatory ────────────────

def test_rejects_missing_classification_category(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    del _rw3_component(r)["classification_counts"]["historical"]
    with pytest.raises(RuntimeError, match="missing categories"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_added_classification_category(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    _rw3_component(r)["classification_counts"]["sneaky"] = 0
    with pytest.raises(RuntimeError, match="unknown categories"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_zero_mandatory_fixtures(canonical_result, tmp_path):
    # Zero mandatory fixtures (with a coherent nested count) must never pass.
    r = copy.deepcopy(canonical_result)
    c = _rw3_component(r)
    c["classification_counts"]["mandatory_executable"] = 0
    c["mandatory_executable"]["count"] = 0
    c["mandatory_executable"]["passed"] = 0
    c["mandatory_executable"]["expected_fixture_count"] = 0
    with pytest.raises(RuntimeError, match="no mandatory executable"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


# ── Aggregate-cancelling and top-level-vs-nested contradictions ───────────────

def test_rejects_aggregate_cancelling_mutations(canonical_result, tmp_path):
    # failed=1 with passed=42 keeps passed+failed == count == 43; the failure must
    # not be hidden by the aggregate remaining consistent.
    result = _mutate_rw3_nested(canonical_result, "mandatory_executable", failed=1, passed=42)
    with pytest.raises(RuntimeError, match="failed mandatory"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_top_level_pass_with_nested_failure(canonical_result, tmp_path):
    # Keep every top-level pass flag intact but flip one nested fail-closed counter.
    result = _mutate_rw3_nested(canonical_result, "pending_unsupported_fail_closed", unexpected_pass=1)
    with pytest.raises(RuntimeError, match="unexpected fail-closed passes"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


# ── G3: authoritative RW3 classification completeness (invariant 1 adversarial) ─
# Reported category counts are evidence to validate, not the source of their own
# expected values.  Every reported count must equal the independently derived
# authoritative inventory from the integrity-verified corpus + classification
# manifest; movement, omission, offsetting and aggregate-preserving drift are
# rejected.


@pytest.mark.parametrize(
    "category",
    ["outside_engine_surface", "historical", "applicable_not_executable", "pending_founder_decision"],
)
def test_rejects_incorrect_excluded_category_count(canonical_result, tmp_path, category):
    result = _mutate_rw3_counts(canonical_result, **{category: 1})
    with pytest.raises(RuntimeError, match="authoritative"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_mandatory_count_drift_with_consistent_nested_section(canonical_result, tmp_path):
    # Mutate the classification count AND the nested section consistently so only
    # the independent authoritative comparison catches the disagreement.
    r = copy.deepcopy(canonical_result)
    c = _rw3_component(r)
    c["classification_counts"]["mandatory_executable"] = 42
    c["mandatory_executable"]["count"] = 42
    c["mandatory_executable"]["passed"] = 42
    c["mandatory_executable"]["expected_fixture_count"] = 42
    with pytest.raises(RuntimeError, match="authoritative"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_fail_closed_count_drift_with_consistent_nested_section(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    c = _rw3_component(r)
    c["classification_counts"]["pending_unsupported_fail_closed"] = 4
    c["pending_unsupported_fail_closed"]["count"] = 4
    c["pending_unsupported_fail_closed"]["expected_fail_closed"] = 4
    c["pending_unsupported_fail_closed"]["expected_fixture_count"] = 4
    with pytest.raises(RuntimeError, match="authoritative"):
        GEN.load_canonical_result(_write_result(tmp_path, r))


def test_rejects_offsetting_category_changes(canonical_result, tmp_path):
    # The exact independent reproduction: outside 61→60 with historical 0→1 keeps
    # the aggregate total but moves a fixture between excluded categories.
    result = _mutate_rw3_counts(
        canonical_result, outside_engine_surface=60, historical=1,
    )
    with pytest.raises(RuntimeError, match="authoritative"):
        GEN.load_canonical_result(_write_result(tmp_path, result))


def test_rejects_correct_aggregate_with_incorrect_distribution(canonical_result, tmp_path):
    r = copy.deepcopy(canonical_result)
    c = _rw3_component(r)
    total = sum(c["classification_counts"].values())
    c["classification_counts"]["outside_engine_surface"] -= 2
    c["classification_counts"]["historical"] += 2
    assert sum(c["classification_counts"].values()) == total  # aggregate unchanged
    with pytest.raises(RuntimeError, match="authoritative"):
        GEN.load_canonical_result(_write_result(tmp_path, r))

