"""Structural regression tests for the release-gate entry point."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "run_release_gate", ROOT / "scripts" / "run_release_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def test_mandatory_suites_cover_all_five_gates():
    suites = GATE.MANDATORY_SUITES
    # root production suite (also hosts the independent RW3 adapter assurance)
    assert "tests/" in suites
    # engine-artefact correctness + production↔artefact parity
    assert "engine-artefact-assurance/tests/" in suites
    # Optimise assurance
    assert "reserved-optimise-assurance/tests/" in suites
    assert len(suites) == 3


def test_historical_bundle_is_not_a_mandatory_suite():
    assert "reserved-engine-2.0.0" not in GATE.MANDATORY_SUITES
    assert not any("run_assurance" in s or "run_stage" in s for s in GATE.MANDATORY_SUITES)


def test_parse_counts_basic():
    assert GATE.parse_counts("1179 passed in 20.00s\n") == (1179, 0, 0)


def test_rw3_gate_is_a_distinct_mandatory_step():
    # The mandatory RW3 fixture gate is a distinct executable step, not a pytest
    # suite and not equivalent to the adapter unit tests inside tests/.
    assert hasattr(GATE, "run_mandatory_rw3")
    assert not any("rw3" in suite.lower() for suite in GATE.MANDATORY_SUITES)


def test_mandatory_rw3_gate_executes_corpus():
    result = GATE.run_mandatory_rw3()
    assert result["gate_passed"] is True
    assert result["mandatory_executable"]["count"] == 43
    assert result["mandatory_executable"]["passed"] == 43
    assert result["classification_counts"]["outside_engine_surface"] == 61
