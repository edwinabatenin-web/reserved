"""Regression tests for the hardened assurance-metadata generator."""
import importlib.util
import os
from pathlib import Path

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


def test_parse_counts_all_passed():
    assert GEN.parse_counts("1003 passed in 11.16s\n") == (1003, 0, 0)


def test_parse_counts_failed_and_passed():
    assert GEN.parse_counts("2 failed, 1001 passed in 12.00s\n") == (1001, 2, 0)


def test_parse_counts_error_failed_passed():
    assert GEN.parse_counts("1 error, 2 failed, 1000 passed in 13.00s\n") == (1000, 2, 1)


def test_parse_counts_ignores_subtests():
    # "7 subtests passed" must not be double-counted.
    assert GEN.parse_counts("1003 passed, 7 subtests passed in 11.16s\n") == (1003, 0, 0)


def test_parse_counts_empty_output():
    assert GEN.parse_counts("") == (0, 0, 0)


def test_verified_date_honours_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert GEN.verified_date() == "1970-01-01T00:00:00Z"


def test_engine_metadata_records_provenance():
    meta = GEN.engine_metadata()
    assert meta["engine_version"] == "3.0.0"
    assert meta["rules_version"] == "uk-2026-27-v3"
    assert meta["tax_year"] == "2026/27"
    assert len(meta["engine_artefact"]["content_hash"]) == 64
    assert meta["engine_artefact"]["source_commit"]
