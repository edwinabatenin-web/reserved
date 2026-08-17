"""Structural enforcement for validation-critical fixture independence."""
import json
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from reserved_west.literal_fixture_runner import validate_pack


ROOT = Path(__file__).parents[1]
FIXTURE_DIR = ROOT / "docs" / "fixtures"
PROHIBITED_TEXT = (
    "reserved.engines",
    "reserved_engine",
    "reserved_west.reference_calculator",
    "reserved-optimise-assurance",
)


def test_fixture_artifacts_do_not_reference_calculation_implementations():
    paths = list(FIXTURE_DIR.glob("RW3_*_FIXTURES.json")) + [
        FIXTURE_DIR / "WP7_INDEPENDENT_SAMPLE.json"
    ]
    for path in paths:
        text = path.read_text().lower()
        for prohibited in PROHIBITED_TEXT:
            assert prohibited.lower() not in text, f"{path} contains {prohibited}"


def test_independent_sample_contains_only_fixed_literals():
    document = json.loads((FIXTURE_DIR / "WP7_INDEPENDENT_SAMPLE.json").read_text())
    assert document["status"] == "independent_fixture_review_pending"
    for fixture in document["fixtures"]:
        assert fixture["id"].startswith("WP7-")
        assert isinstance(fixture["expected"], dict) and fixture["expected"]
        for value in fixture["expected"].values():
            assert isinstance(value, str)


def test_review_pending_sample_cannot_be_called_independent_validation():
    document = json.loads((FIXTURE_DIR / "WP7_INDEPENDENT_SAMPLE.json").read_text())
    assert document["status"] != "independent_validation"


def test_historical_runtime_oracle_is_not_a_validation_fixture():
    fixture_names = {path.name for path in FIXTURE_DIR.glob("*.json")}
    assert "reference_calculator.py" not in fixture_names


def test_rw3_packs_have_provenance_and_coherent_review_state():
    for path in FIXTURE_DIR.glob("RW3_*_FIXTURES.json"):
        pack = json.loads(path.read_text())
        assert pack["status"] in {
            "independent_fixture_review_pending",
            "independent_validation",
        }
        if pack["status"] == "independent_validation":
            assert pack["review"]["decision"] == "approved"
            assert pack["review"]["reviewer"]
            assert pack["review"]["reviewed_on"]
        else:
            assert pack["review"]["decision"] == "pending"
            assert pack["review"]["reviewer"] is None
            assert pack["review"]["reviewed_on"] is None
        assert pack["derived_by"] and pack["derived_on"]
        assert pack["sources"]
        source_urls = {source["url"] for source in pack["sources"]}
        assert all(
            url.startswith("https://www.gov.uk/")
            or url.startswith("https://developer.service.hmrc.gov.uk/")
            or url.startswith("https://www.legislation.gov.uk/")
            for url in source_urls
        )
        for fixture in pack["fixtures"]:
            assert fixture["status"] == pack["status"]
            assert fixture["inputs"] and fixture["expected"] and fixture["derivation"]


def test_preimplementation_pack_covers_each_missing_v1_family():
    pack = json.loads((FIXTURE_DIR / "RW3_V1_PREIMPLEMENTATION_FIXTURES.json").read_text())
    families = {fixture["family"] for fixture in pack["fixtures"]}
    assert {
        "savings_starting_rate",
        "dividend_ordering",
        "uk_property_non_savings",
        "foreign_property_pre_credit",
        "hicbc_liability",
        "mtd_readiness",
        "mixed_income_ordering",
    } <= families


def test_tranche_h_admission_is_narrow_and_excludes_hmx_003():
    pack = json.loads((FIXTURE_DIR / "RW3_TRANCHE_H_FIXTURES.json").read_text())
    assert pack["status"] == "independent_validation"
    assert {fixture["id"] for fixture in pack["fixtures"]} == {
        "RW3-HMX-001",
        "RW3-HMX-002",
    }
    assert "pre-FTCR" in pack["purpose"]
    assert "complete annual bill" in pack["purpose"]
    limitations = " ".join(
        limitation
        for fixture in pack["fixtures"]
        for limitation in fixture.get("limitations", [])
    )
    assert "Foreign Tax Credit Relief is deliberately not calculated" in limitations
    assert "multiple-undergraduate-plan" in limitations


def test_fixture_integrity_manifest_detects_changes():
    manifest = json.loads((FIXTURE_DIR / "WP7_FIXTURE_INTEGRITY.json").read_text())
    assert manifest["algorithm"] == "sha256"
    fixture_files = {path.name for path in FIXTURE_DIR.glob("RW3_*_FIXTURES.json")}
    assert set(manifest["files"]) == fixture_files
    for filename, expected_hash in manifest["files"].items():
        actual_hash = hashlib.sha256((FIXTURE_DIR / filename).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"{filename} changed: re-derive/review affected fixtures and deliberately update manifest"
        )


def test_accuracy_corpus_excludes_historical_shared_lineage():
    corpus = json.loads((FIXTURE_DIR / "WP7_ASSURANCE_CORPUS.json").read_text())
    integrity = json.loads((FIXTURE_DIR / "WP7_FIXTURE_INTEGRITY.json").read_text())
    assert set(corpus["included_fixture_packs"]) == set(integrity["files"])
    assert corpus["status"] == "not_fit_review_pending"
    excluded = " ".join(corpus["excluded_from_accuracy_pass_counts"])
    assert "reserved_west/reference_calculator.py" in excluded
    assert "reserved_west/output/**" in excluded
    assert "reserved-optimise-assurance/reference/**" in excluded
    assert all("RW3_" in name for name in corpus["included_fixture_packs"])


def test_runner_enforces_published_schema_shapes_and_pending_review_state():
    valid = json.loads((
        FIXTURE_DIR / "RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json"
    ).read_text())
    assert validate_pack(valid)

    invalid_cases = []
    bad = deepcopy(valid)
    bad["derived_on"] = "13/08/2026"
    invalid_cases.append(bad)
    bad = deepcopy(valid)
    bad["review"]["reviewer"] = "Premature reviewer"
    invalid_cases.append(bad)
    bad = deepcopy(valid)
    bad["sources"][0]["supports"] = ""
    invalid_cases.append(bad)
    bad = deepcopy(valid)
    bad["fixtures"][0]["id"] = "not-a-valid-id"
    invalid_cases.append(bad)
    bad = deepcopy(valid)
    bad["fixtures"][0]["derivation"] = []
    invalid_cases.append(bad)

    for invalid in invalid_cases:
        with pytest.raises(ValueError):
            validate_pack(invalid)


def test_rw3_gate_implementation_does_not_import_reference_calculator():
    """The mandatory RW3 gate executes fixtures against the engine artefact,
    never against the historical shared-lineage reference calculator."""
    gate_impl_files = [
        "reserved_west/release_gate.py",
        "reserved_west/rw3_gate.py",
        "reserved_west/artefact.py",
        "reserved_west/engine_adapters.py",
        "reserved_west/literal_fixture_runner.py",
    ]
    for rel in gate_impl_files:
        text = (ROOT / rel).read_text()
        assert "reference_calculator" not in text, f"{rel} references reference_calculator"
        assert "ref_estimate" not in text, f"{rel} references ref_estimate"


def test_metadata_does_not_describe_reference_calculator_as_independent():
    """The persisted assurance metadata must not name the historical reference
    calculator as current independent accuracy evidence."""
    meta = json.loads((ROOT / "reserved" / "assurance_metadata.json").read_text())
    blob = json.dumps(meta)
    assert "reference_calculator" not in blob
    assert "ref_estimate" not in blob
    for comp in meta.get("component_inventory", []):
        assert "reference_calculator" not in comp.get("id", "")
        assert "reference_calculator" not in comp.get("description", "")
