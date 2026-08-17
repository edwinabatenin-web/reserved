"""
Tests for the distinct mandatory RW3 fixture gate (``reserved_west.rw3_gate``).

These verify the gate is a real, release-blocking execution of the classified
mandatory corpus — not a re-export of the adapter unit tests — and that it
fails on every failure mode it is required to detect.
"""
from pathlib import Path

import pytest

from reserved.engines.income_tax import UnsupportedStudentLoanPlanCombination
from reserved_west.rw3_gate import (
    CLASSIFICATION_VALUES,
    authoritative_classification_counts,
    derive_expected_classification_counts,
    evaluate_gate,
    load_classification,
    run_mandatory_rw3_gate,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "docs" / "fixtures"


# ── Test doubles (smallest synthetic corpus) ─────────────────────────────────

def _fixture(fid, adapter, inputs, expected, status="independent_validation"):
    return {
        "id": fid,
        "family": "test",
        "status": status,
        "inputs": {"adapter": adapter, **inputs},
        "expected": expected,
        "derivation": ["test"],
    }


def _pack(fixtures, status="independent_validation"):
    return {"pack_id": "PK", "status": status, "fixtures": fixtures}


def _classification(packs):
    return {"corpus_id": "C", "packs": packs}


def _provenance(**overrides):
    p = {
        "content_hash": "a" * 64,
        "source_commit": "c" * 40,
        "engine_version": "4.0.0",
        "rules_version": "uk-2026-27-v4",
    }
    p.update(overrides)
    return p


def _ok(value):
    return lambda inputs: value


def _wrong():
    return lambda inputs: {"income_tax": "999999.00"}


def _boom():
    def f(inputs):
        raise RuntimeError("boom")

    return f


def _unsupported():
    def f(inputs):
        raise UnsupportedStudentLoanPlanCombination("simultaneous plans")

    return f


# ── Positive gate behaviour against the real corpus ──────────────────────────

def test_mandatory_rw3_gate_passes_current_corpus():
    result = run_mandatory_rw3_gate()
    assert result["gate_passed"] is True
    assert result["provenance_ok"] is True
    assert result["artefact"]["engine_version"] == "4.0.0"
    assert result["artefact"]["rules_version"] == "uk-2026-27-v4"
    assert result["artefact"]["source_commit"]
    assert len(result["artefact"]["content_hash"]) == 64


def test_gate_reports_mandatory_fail_closed_and_excluded_counts():
    result = run_mandatory_rw3_gate()
    m = result["mandatory_executable"]
    assert m["count"] == 43
    assert m["passed"] == 43
    assert m["failed"] == 0
    assert m["unexpected_error"] == 0
    assert m["missing_adapter"] == 0
    assert m["inventory_mismatch"] == 0

    fc = result["pending_unsupported_fail_closed"]
    assert fc["count"] == 3
    assert fc["expected_fail_closed"] == 3
    assert fc["unexpected_pass"] == 0
    assert fc["monetary_leak"] == 0

    counts = result["classification_counts"]
    assert counts["outside_engine_surface"] == 61
    assert counts["applicable_not_executable"] == 0
    assert counts["mandatory_executable"] == 43
    assert counts["pending_unsupported_fail_closed"] == 3


def test_gate_never_counts_excluded_as_passed():
    result = run_mandatory_rw3_gate()
    # 43 mandatory + 61 outside-surface + 3 pending = the full 107-fixture corpus.
    counts = result["classification_counts"]
    assert counts["mandatory_executable"] + counts["outside_engine_surface"] + counts["pending_unsupported_fail_closed"] == 107
    # The mandatory PASS figure must be the mandatory subset only, never inflated
    # by the excluded approved fixtures.
    assert result["mandatory_executable"]["passed"] == 43


# ── Classification manifest ──────────────────────────────────────────────────

def test_classification_manifest_loads_and_validates():
    classification = load_classification()
    assert classification["schema"] == "rw3-assurance-classification-1"
    assert set(classification["packs"]) == {
        "RW3_CORE_FIXTURES.json",
        "RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json",
        "RW3_PAYE_EVIDENCE_FIXTURES.json",
        "RW3_TRANCHE_H_FIXTURES.json",
        "RW3_V1_PREIMPLEMENTATION_FIXTURES.json",
    }
    for entry in classification["packs"].values():
        assert entry["classification"] in CLASSIFICATION_VALUES


def test_classification_manifest_integrity_locked(tmp_path):
    src = FIXTURE_DIR / "RW3_ASSURANCE_CLASSIFICATION.json"
    integrity = FIXTURE_DIR / "WP7_FIXTURE_INTEGRITY.json"
    tampered = tmp_path / "classification.json"
    tampered.write_text(src.read_text().replace("mandatory_executable", "mandatory_executable"))
    # The replacement is a no-op, so mutate the actual content.
    tampered.write_text(src.read_text().replace('"expected_fixture_count": 43', '"expected_fixture_count": 44'))
    with pytest.raises(RuntimeError, match="integrity failure"):
        load_classification(tampered, integrity)


def test_classification_manifest_rejects_unknown_classification():
    from reserved_west.rw3_gate import _validate_classification

    classification = load_classification()
    classification["packs"]["RW3_CORE_FIXTURES.json"]["classification"] = "bogus"
    with pytest.raises(RuntimeError, match="unknown classification"):
        _validate_classification(classification)


# ── Failure modes (mandatory subset) ─────────────────────────────────────────

def test_mandatory_fixture_fail_fails_gate():
    fixture = _fixture("RW3-TST-001", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _wrong()}
    packs = {"CORE.json": _pack([fixture])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["failed"] == 1


def test_mandatory_unexpected_error_fails_gate():
    fixture = _fixture("RW3-TST-002", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _boom()}
    packs = {"CORE.json": _pack([fixture])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["unexpected_error"] == 1


def test_mandatory_missing_adapter_fails_gate():
    fixture = _fixture("RW3-TST-003", "nonexistent_adapter", {"income": "1"}, {"income_tax": "100.00"})
    packs = {"CORE.json": _pack([fixture])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    result = evaluate_gate(packs, classification, {}, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["missing_adapter"] == 1


def test_empty_mandatory_set_fails_gate():
    packs = {}
    classification = _classification({})
    result = evaluate_gate(packs, classification, {}, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["count"] == 0


def test_mandatory_inventory_mismatch_fails_gate():
    fixture = _fixture("RW3-TST-004", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _ok({"income_tax": "100.00"})}
    packs = {"CORE.json": _pack([fixture])}
    # Classification expects two mandatory fixtures, but only one is present.
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 2}})
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["inventory_mismatch"] == 1


def test_expected_value_mutation_fails_gate():
    # Mutating an expected value (in memory) makes the fixture FAIL against the
    # correct engine output; the gate must fail rather than pass silently.
    fixture = _fixture("RW3-TST-005", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _ok({"income_tax": "100.00"})}
    fixture["expected"]["income_tax"] = "101.00"  # mutated
    packs = {"CORE.json": _pack([fixture])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is False
    assert result["mandatory_executable"]["failed"] == 1


# ── Failure modes (pending unsupported fail-closed subset) ───────────────────

def _gate_with_mandatory_pass(adapters, pending_fixture=None, pending_count=1):
    """Build a gate that passes the mandatory subset, isolating pending failures."""
    mandatory = _fixture("RW3-TST-000", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})
    adapters = dict(adapters)
    adapters["annual_income_tax"] = _ok({"income_tax": "0.00"})
    packs = {"CORE.json": _pack([mandatory])}
    classification = _classification({
        "CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1},
    })
    if pending_fixture is not None:
        packs["PENDING.json"] = _pack([pending_fixture])
        classification["packs"]["PENDING.json"] = {
            "classification": "pending_unsupported_fail_closed",
            "expected_fixture_count": pending_count,
        }
    return evaluate_gate(packs, classification, adapters, _provenance())


def test_pending_monetary_leak_fails_gate():
    # A pending-unsupported fixture that (wrongly) returns monetary output must
    # fail the gate: unsupported states cannot leak liability.
    pending = _fixture("RW3-TST-006", "incremental_liability", {"invoice_amount": "1"}, {"national_insurance": "0.00"})
    adapters = {"incremental_liability": _ok({"national_insurance": "0.00"})}
    result = _gate_with_mandatory_pass(adapters, pending)
    assert result["gate_passed"] is False
    assert result["pending_unsupported_fail_closed"]["unexpected_pass"] == 1
    assert result["pending_unsupported_fail_closed"]["monetary_leak"] == 1


def test_pending_unexpected_error_fails_gate():
    # A pending fixture that errors with the wrong exception is not a valid
    # fail-closed result.
    pending = _fixture("RW3-TST-007", "incremental_liability", {"invoice_amount": "1"}, {"national_insurance": "0.00"})
    adapters = {"incremental_liability": _boom()}
    result = _gate_with_mandatory_pass(adapters, pending)
    assert result["gate_passed"] is False
    assert result["pending_unsupported_fail_closed"]["unexpected_error"] == 1


def test_pending_inventory_mismatch_fails_gate():
    pending = _fixture("RW3-TST-008", "incremental_liability", {"invoice_amount": "1"}, {"national_insurance": "0.00"})
    adapters = {"incremental_liability": _unsupported()}
    result = _gate_with_mandatory_pass(adapters, pending, pending_count=2)
    assert result["gate_passed"] is False
    assert result["pending_unsupported_fail_closed"]["inventory_mismatch"] == 1


def test_pending_correct_fail_closed_passes():
    pending = _fixture("RW3-TST-009", "incremental_liability", {"invoice_amount": "1"}, {"national_insurance": "0.00"})
    mandatory = _fixture("RW3-TST-009A", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})
    adapters = {
        "incremental_liability": _unsupported(),
        "annual_income_tax": _ok({"income_tax": "0.00"}),
    }
    packs = {"PENDING.json": _pack([pending]), "CORE.json": _pack([mandatory])}
    classification = _classification({
        "PENDING.json": {"classification": "pending_unsupported_fail_closed", "expected_fixture_count": 1},
        "CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1},
    })
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is True
    assert result["pending_unsupported_fail_closed"]["expected_fail_closed"] == 1
    assert result["pending_unsupported_fail_closed"]["monetary_leak"] == 0


# ── Provenance ───────────────────────────────────────────────────────────────

def test_missing_provenance_fails_gate():
    fixture = _fixture("RW3-TST-010", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _ok({"income_tax": "100.00"})}
    packs = {"CORE.json": _pack([fixture])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    result = evaluate_gate(packs, classification, adapters, {})
    assert result["gate_passed"] is False
    assert result["provenance_ok"] is False


def test_unclassified_pack_fails_gate():
    # A pack present in the corpus but absent from the classification manifest
    # is a completeness failure: the gate must not claim a clean pass.
    fixture = _fixture("RW3-TST-011", "annual_income_tax", {"income": "1"}, {"income_tax": "100.00"})
    adapters = {"annual_income_tax": _ok({"income_tax": "100.00"})}
    packs = {"UNKNOWN.json": _pack([fixture])}
    classification = _classification({})  # no classification for UNKNOWN.json
    result = evaluate_gate(packs, classification, adapters, _provenance())
    assert result["gate_passed"] is False
    assert result["classification_complete"] is False
    assert result["unclassified_packs"] == [{"filename": "UNKNOWN.json", "fixture_count": 1}]


# ── Classification completeness blocks the gate ─────────────────────────────

def _gate_with_pass_and_excluded(classification_value):
    """A gate whose mandatory subset passes, plus one pack with ``classification_value``."""
    mandatory = _fixture("RW3-TST-100", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})
    other = _fixture("RW3-TST-101", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})
    adapters = {"annual_income_tax": _ok({"income_tax": "0.00"})}
    packs = {"CORE.json": _pack([mandatory]), "OTHER.json": _pack([other])}
    classification = _classification({
        "CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1},
        "OTHER.json": {"classification": classification_value, "expected_fixture_count": 1},
    })
    return evaluate_gate(packs, classification, adapters, _provenance())


def test_pending_founder_decision_classification_blocks_gate():
    result = _gate_with_pass_and_excluded("pending_founder_decision")
    assert result["classification_complete"] is False
    assert result["classification_counts"]["pending_founder_decision"] == 1
    assert result["gate_passed"] is False


def test_applicable_not_executable_classification_blocks_gate():
    result = _gate_with_pass_and_excluded("applicable_not_executable")
    assert result["classification_complete"] is False
    assert result["classification_counts"]["applicable_not_executable"] == 1
    assert result["gate_passed"] is False


def test_outside_engine_surface_classification_does_not_block_gate():
    # A legitimately excluded pack (outside_engine_surface) does not make the
    # classification incomplete and must not block an otherwise-passing gate.
    result = _gate_with_pass_and_excluded("outside_engine_surface")
    assert result["classification_complete"] is True
    assert result["classification_counts"]["outside_engine_surface"] == 1
    assert result["gate_passed"] is True


# ── Authoritative classification completeness (invariant 1) ───────────────────

def test_authoritative_classification_counts_matches_current_corpus():
    counts = authoritative_classification_counts()
    assert counts == {
        "mandatory_executable": 43,
        "pending_unsupported_fail_closed": 3,
        "outside_engine_surface": 61,
        "applicable_not_executable": 0,
        "historical": 0,
        "pending_founder_decision": 0,
    }


def test_derive_counts_maps_packs_to_categories():
    packs = {
        "CORE.json": _pack([_fixture("RW3-TST-001", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})]),
        "PENDING.json": _pack([_fixture("RW3-TST-002", "incremental_liability", {"invoice_amount": "1"}, {"national_insurance": "0.00"})]),
        "OUT.json": _pack([
            _fixture("RW3-TST-003", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"}),
            _fixture("RW3-TST-004", "annual_income_tax", {"income": "2"}, {"income_tax": "0.00"}),
        ]),
    }
    classification = _classification({
        "CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1},
        "PENDING.json": {"classification": "pending_unsupported_fail_closed", "expected_fixture_count": 1},
        "OUT.json": {"classification": "outside_engine_surface", "expected_fixture_count": 2},
    })
    counts = derive_expected_classification_counts(packs, classification)
    assert counts["mandatory_executable"] == 1
    assert counts["pending_unsupported_fail_closed"] == 1
    assert counts["outside_engine_surface"] == 2
    assert counts["applicable_not_executable"] == 0
    assert counts["historical"] == 0
    assert counts["pending_founder_decision"] == 0


def test_derive_counts_rejects_omitted_pack():
    packs = {"CORE.json": _pack([_fixture("RW3-TST-001", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})])}
    classification = _classification({})  # CORE.json left unclassified
    with pytest.raises(RuntimeError, match="missing from classification"):
        derive_expected_classification_counts(packs, classification)


def test_derive_counts_rejects_added_pack():
    packs = {"CORE.json": _pack([_fixture("RW3-TST-001", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})])}
    classification = _classification({
        "CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1},
        "GHOST.json": {"classification": "historical", "expected_fixture_count": 0},
    })
    with pytest.raises(RuntimeError, match="absent from corpus"):
        derive_expected_classification_counts(packs, classification)


def test_derive_counts_rejects_expected_count_mismatch():
    packs = {"CORE.json": _pack([_fixture("RW3-TST-001", "annual_income_tax", {"income": "1"}, {"income_tax": "0.00"})])}
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 2}})
    with pytest.raises(RuntimeError, match="mismatch"):
        derive_expected_classification_counts(packs, classification)


def test_authoritative_rejects_duplicate_allowlist(monkeypatch):
    import reserved_west.rw3_gate as rwg

    corpus = {"included_fixture_packs": ["CORE.json", "CORE.json"]}
    packs = [{}, {}]
    classification = _classification({"CORE.json": {"classification": "mandatory_executable", "expected_fixture_count": 1}})
    monkeypatch.setattr(rwg, "load_corpus", lambda *a, **k: (corpus, packs))
    monkeypatch.setattr(rwg, "load_classification", lambda *a, **k: classification)
    with pytest.raises(RuntimeError, match="duplicate"):
        rwg.authoritative_classification_counts()

