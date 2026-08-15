"""Regression tests for the metadata generator that consumes the canonical result."""
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


def test_generated_on_honours_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert GEN.generated_on() == "1970-01-01T00:00:00Z"


def test_current_production_source_files_is_nonempty():
    files = GEN.current_production_source_files()
    assert "income_tax.py" in files
    assert "tax_config.py" in files


def _sample_result():
    from reserved_west import release_gate as rg

    return rg.run_canonical_gate(
        components=[{"id": "mandatory_rw3_gate", "kind": "rw3"}],
        build_artefact=False,
    )


def _write_result(tmp_path, result):
    path = tmp_path / "release_gate_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return path


def test_load_canonical_result_rejects_missing(tmp_path):
    with pytest.raises(RuntimeError, match="missing"):
        GEN.load_canonical_result(tmp_path / "does_not_exist.json")


def test_load_canonical_result_rejects_malformed(tmp_path):
    path = tmp_path / "r.json"
    path.write_text("{not json")
    with pytest.raises(RuntimeError, match="malformed"):
        GEN.load_canonical_result(path)


def test_load_canonical_result_rejects_wrong_schema(tmp_path):
    result = _sample_result()
    result["schema"] = "not-a-known-schema"
    path = _write_result(tmp_path, result)
    with pytest.raises(RuntimeError, match="schema"):
        GEN.load_canonical_result(path)


def test_load_canonical_result_rejects_stale(tmp_path):
    result = _sample_result()
    result["production_source"]["source_files"]["income_tax.py"] = "0" * 64
    path = _write_result(tmp_path, result)
    with pytest.raises(RuntimeError, match="stale"):
        GEN.load_canonical_result(path)


def test_load_canonical_result_accepts_valid(tmp_path):
    result = _sample_result()
    path = _write_result(tmp_path, result)
    loaded = GEN.load_canonical_result(path)
    assert loaded["overall_decision"] == "pass"
    assert loaded["status"] == "deterministic_engine_remediation_gate_passed"


def test_build_metadata_records_identity_and_october_status():
    result = _sample_result()
    meta = GEN.build_metadata(result)
    assert meta["status"] == "deterministic_engine_remediation_gate_passed"
    assert meta["october_launch_candidate"]["status"] == "not_ready"
    assert meta["engine_version"] == "4.0.0"
    assert meta["rules_version"] == "uk-2026-27-v4"
    assert meta["period_of_assessment"] == "2026/27"
    assert len(meta["engine_artefact"]["content_hash"]) == 64
    assert meta["engine_artefact"]["source_commit"]
    assert meta["production_source"]["source_files"]
    assert meta["rw3_fixture_gate"]["gate_passed"] is True
    assert meta["rw3_fixture_gate"]["classification_counts"]["mandatory_executable"] == 43
    assert meta["rw3_fixture_gate"]["classification_counts"]["pending_unsupported_fail_closed"] == 3
    assert meta["component_inventory"]
