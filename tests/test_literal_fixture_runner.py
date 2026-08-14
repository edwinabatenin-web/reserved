from reserved_west.literal_fixture_runner import (
    assess_corpus,
    compare_fixture,
    load_corpus,
    run_pack,
    validate_pack,
)
from pathlib import Path


def test_runner_compares_literals_without_calculating_expectations():
    fixture = {
        "id": "RW3-DEMO-001",
        "status": "independent_fixture_review_pending",
        "inputs": {"adapter": "demo", "value": "10"},
        "expected": {"result": "12.00"},
    }
    adapter = lambda inputs: {"result": "12.00"}
    result = compare_fixture(fixture, {"demo": adapter})
    assert result["outcome"] == "PASS"
    assert result["fixture_status"] == "independent_fixture_review_pending"


def test_runner_exposes_variance_and_does_not_rewrite_expected():
    fixture = {
        "id": "RW3-DEMO-002",
        "status": "independent_fixture_review_pending",
        "inputs": {"adapter": "demo"},
        "expected": {"result": "12.00"},
    }
    result = compare_fixture(fixture, {"demo": lambda _: {"result": "11.00"}})
    assert result["outcome"] == "FAIL"
    assert result["variances"]["result"] == "-1.00"
    assert fixture["expected"]["result"] == "12.00"


def test_runner_never_promotes_review_pending_pack():
    pack = {
        "pack_id": "draft",
        "status": "independent_fixture_review_pending",
        "tax_year": "2026/27", "territory": "England, Wales and Northern Ireland",
        "derived_by": "author", "derived_on": "2026-08-13",
        "review": {"reviewer": None, "reviewed_on": None, "decision": "pending", "notes": ""},
        "rounding": "pence", "sources": [{"title": "official", "url": "https://www.gov.uk/", "supports": "demo"}],
        "fixtures": [{
            "id": "RW3-DEMO-003", "status": "independent_fixture_review_pending",
            "family": "demo", "inputs": {"adapter": "demo"}, "expected": {"result": "1"}, "derivation": ["fixed"],
        }],
    }
    result = run_pack(pack, {"demo": lambda _: {"result": "1"}})
    assert result["pack_status"] == "independent_fixture_review_pending"
    assert result["results"][0]["outcome"] == "PASS"


def test_runner_supports_string_date_and_null_expected_fields():
    fixture = {
        "id": "RW3-DEMO-004", "status": "independent_fixture_review_pending",
        "inputs": {"adapter": "demo"},
        "expected": {"confidence": "high", "mandatory_from": None, "date": "2026-04-06"},
    }
    actual = {"confidence": "high", "mandatory_from": None, "date": "2026-04-06"}
    assert compare_fixture(fixture, {"demo": lambda _: actual})["outcome"] == "PASS"


def test_approved_pack_requires_different_named_reviewer():
    pack = {
        "pack_id": "approved", "status": "independent_validation", "tax_year": "2026/27",
        "territory": "England, Wales and Northern Ireland", "derived_by": "same-person",
        "derived_on": "2026-08-13", "rounding": "pence", "sources": [{"title": "official", "url": "https://www.gov.uk/", "supports": "demo"}],
        "review": {"reviewer": "same-person", "reviewed_on": "2026-08-13", "decision": "approved", "notes": ""},
        "fixtures": [{"id": "RW3-DEMO-005", "family": "demo", "status": "independent_validation", "inputs": {}, "expected": {"x": "1"}, "derivation": ["fixed"]}],
    }
    try:
        validate_pack(pack)
    except ValueError as exc:
        assert "cannot approve" in str(exc)
    else:
        raise AssertionError("Self-approved pack was accepted")


def test_corpus_loader_uses_only_explicit_rw3_allowlist():
    fixture_dir = Path(__file__).parents[1] / "docs" / "fixtures"
    corpus, packs = load_corpus(fixture_dir / "WP7_ASSURANCE_CORPUS.json")
    assert len(packs) == len(corpus["included_fixture_packs"])
    assert all(pack["pack_id"].startswith("RW3-") for pack in packs)
    assert not any("reference_calculator" in name for name in corpus["included_fixture_packs"])


def test_gate_mode_rejects_review_pending_corpus():
    fixture_dir = Path(__file__).parents[1] / "docs" / "fixtures"
    try:
        load_corpus(fixture_dir / "WP7_ASSURANCE_CORPUS.json", require_approved=True)
    except ValueError as exc:
        assert "not independently approved" in str(exc)
    else:
        raise AssertionError("Review-pending corpus entered gate mode")


def test_corpus_assessment_reports_mixed_approval_without_opening_gate():
    fixture_dir = Path(__file__).parents[1] / "docs" / "fixtures"
    assessment = assess_corpus(fixture_dir / "WP7_ASSURANCE_CORPUS.json")
    assert assessment == {
        "corpus_id": "RW3-WP7-DRAFT-CORPUS-1",
        "gate_ready": False,
        "pack_count": 5,
        "approved_pack_ids": [
            "RW3-CORE-2026-27-DRAFT-1",
            "RW3-PAYE-EVIDENCE-DRAFT-1",
            "RW3-TRANCHE-H-2026-27-ADMITTED-1",
            "RW3-V1-PREIMPLEMENTATION-2026-27-DRAFT-1",
        ],
        "pending_pack_ids": [
            "RW3-CORE-MULTI-UNDERGRADUATE-ANNUAL-SA-PENDING-1"
        ],
        "fixture_count": 107,
        "approved_fixture_count": 104,
        "pending_fixture_count": 3,
    }
