"""
RW3 engine-artefact adapter wiring tests.

These verify that the adapter layer only translates fixture inputs into
engine-artefact calls (never deriving or mutating expected values), that
unsupported states fail closed, and that engine provenance is recorded.
"""
from decimal import Decimal as D

import pytest

from reserved_west.engine_adapters import (
    build_adapters,
    run_engine_evidence,
)
from reserved_west.literal_fixture_runner import (
    compare_fixture,
    load_corpus,
    run_pack,
)


@pytest.fixture(scope="module")
def adapters():
    return build_adapters()


# ── Translation (not derivation) ─────────────────────────────────────────────

def test_annual_income_tax_adapter_returns_engine_output(adapters):
    adapter = adapters[0]["annual_income_tax"]
    actual = adapter({"adapter": "annual_income_tax", "income": "100001", "gross_ras_pension": "0"})
    assert actual["personal_allowance"] == D("12569.5")
    assert actual["income_tax"] == D("27432.60")
    assert actual["adjusted_net_income"] == D("100001")


def test_incremental_liability_adapter_returns_engine_output(adapters):
    adapter = adapters[0]["incremental_liability"]
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0", "student_loan_plans": []}
    actual = adapter({"adapter": "incremental_liability", "invoice_amount": "60000", "profile": profile})
    assert actual["national_insurance"] == D("2456.60")


def test_adapter_does_not_mutate_expected_values(adapters):
    fixture = {
        "id": "RW3-IT-003",
        "family": "pa_taper",
        "status": "independent_validation",
        "inputs": {"adapter": "annual_income_tax", "income": "100001", "gross_ras_pension": "0"},
        "expected": {"personal_allowance": "12569.50", "income_tax": "27432.60"},
        "derivation": ["first principles"],
    }
    compare_fixture(fixture, adapters[0])
    assert fixture["expected"] == {"personal_allowance": "12569.50", "income_tax": "27432.60"}


# ── Fail closed ───────────────────────────────────────────────────────────────

def test_missing_adapter_fails_closed():
    fixture = {
        "id": "RW3-DEMO-901",
        "family": "demo",
        "status": "independent_fixture_review_pending",
        "inputs": {},  # no adapter key
        "expected": {"x": "1"},
        "derivation": ["demo"],
    }
    result = compare_fixture(fixture, {})
    assert result["outcome"] == "ERROR"
    assert "No adapter" in result["error"]


def test_unsupported_student_loan_state_fails_closed(adapters):
    fixture = {
        "id": "RW3-SL-001",
        "family": "multiple_student_loans",
        "status": "independent_fixture_review_pending",
        "inputs": {
            "adapter": "incremental_liability",
            "invoice_amount": "40000",
            "profile": {"day_job_salary": "0", "ytd_freelance_profit": "0",
                        "personal_pension_contributions": "0", "student_loan_plans": [1, 2]},
        },
        "expected": {"student_loan": "1179.00"},
        "derivation": ["charge once at lowest threshold"],
    }
    result = compare_fixture(fixture, adapters[0])
    assert result["outcome"] == "ERROR"
    assert "UnsupportedStudentLoanPlanCombination" in result["error"]
    # No monetary figure may leak through the fail-closed path.
    assert "actual" not in result or result.get("actual") is None


# ── Provenance ────────────────────────────────────────────────────────────────

def test_engine_provenance_recorded():
    _, provenance = build_adapters()
    assert provenance["engine_version"] == "3.0.0"
    assert provenance["rules_version"] == "uk-2026-27-v3"
    assert len(provenance["content_hash"]) == 64
    assert provenance["source_commit"]


def test_run_engine_evidence_records_provenance():
    evidence = run_engine_evidence("docs/fixtures/WP7_ASSURANCE_CORPUS.json")
    assert evidence["engine_provenance"]["engine_version"] == "3.0.0"
    assert evidence["corpus_id"].startswith("RW3-")
    assert evidence["pack_results"]


# ── Corpus wiring ─────────────────────────────────────────────────────────────

def test_core_pack_wires_and_pending_pack_fails_closed(adapters):
    corpus, packs = load_corpus("docs/fixtures/WP7_ASSURANCE_CORPUS.json")
    core = next(p for p in packs if p["pack_id"].startswith("RW3-CORE-"))
    pending = next(p for p in packs if "PENDING" in p["pack_id"])

    core_results = run_pack(core, adapters[0])["results"]
    outcomes = {r["outcome"] for r in core_results}
    assert outcomes <= {"PASS", "FAIL", "ERROR"}

    pending_results = run_pack(pending, adapters[0])["results"]
    assert all(r["outcome"] == "ERROR" for r in pending_results)
    assert all("UnsupportedStudentLoanPlanCombination" in r["error"] for r in pending_results)
