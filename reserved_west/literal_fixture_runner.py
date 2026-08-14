"""Formula-free runner for immutable Reserved West literal fixtures.

The runner is execution infrastructure, not an oracle: it dispatches inputs to
the engine and compares returned fields with fixed expected strings. It must
never calculate an expected tax result or import the historical West reference
calculator.
"""
from decimal import Decimal
from datetime import date
import hashlib
import json
from pathlib import Path
import re


FIXTURE_ID_PATTERN = re.compile(r"^RW3-[A-Z]+-[0-9]{3}$")


def _valid_date(value):
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def load_pack(path):
    return json.loads(Path(path).read_text())


def validate_pack(pack):
    """Validate the enforcement-critical subset of the published pack schema."""
    required = {
        "pack_id", "status", "tax_year", "territory", "derived_by",
        "derived_on", "review", "rounding", "sources", "fixtures",
    }
    missing = required - set(pack)
    if missing:
        raise ValueError(f"Fixture pack missing fields: {sorted(missing)}")
    allowed_pack = required | {"purpose"}
    unexpected = set(pack) - allowed_pack
    if unexpected:
        raise ValueError(f"Fixture pack has unexpected fields: {sorted(unexpected)}")
    if pack["status"] not in {"independent_fixture_review_pending", "independent_validation"}:
        raise ValueError("Invalid fixture pack status")
    if pack["tax_year"] != "2026/27" or pack["territory"] != "England, Wales and Northern Ireland":
        raise ValueError("Fixture pack tax year or territory is outside the WP7 schema")
    if not isinstance(pack["pack_id"], str) or not pack["pack_id"]:
        raise ValueError("Fixture pack id must be a non-empty string")
    if not isinstance(pack["derived_by"], str) or not pack["derived_by"]:
        raise ValueError("Fixture pack derived_by must be a non-empty string")
    if not _valid_date(pack["derived_on"]):
        raise ValueError("Fixture pack derived_on must be an ISO date")
    if not isinstance(pack["rounding"], str) or not pack["rounding"]:
        raise ValueError("Fixture pack rounding must be a non-empty string")
    if not isinstance(pack["sources"], list) or not isinstance(pack["fixtures"], list):
        raise ValueError("Fixture pack sources and fixtures must be arrays")
    if not pack["sources"] or not pack["fixtures"]:
        raise ValueError("Fixture pack rounding, sources and fixtures must be populated")
    for source in pack["sources"]:
        if not isinstance(source, dict):
            raise ValueError("Each source must be an object")
        if set(source) != {"title", "url", "supports"}:
            raise ValueError("Each source requires exactly title, url and supports")
        if not all(isinstance(source[field], str) and source[field] for field in source):
            raise ValueError("Fixture source fields must be non-empty strings")
        if not source["url"].startswith("https://"):
            raise ValueError("Fixture source URLs must use HTTPS")
    review = pack["review"]
    if not isinstance(review, dict) or set(review) != {"reviewer", "reviewed_on", "decision", "notes"}:
        raise ValueError("Fixture review metadata does not match the published schema")
    if review["decision"] not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid fixture review decision")
    if not isinstance(review["notes"], str):
        raise ValueError("Fixture review notes must be a string")
    if pack["status"] == "independent_fixture_review_pending":
        if review["decision"] != "pending" or review["reviewer"] is not None or review["reviewed_on"] is not None:
            raise ValueError("Review-pending packs cannot contain completed approval metadata")
    if pack["status"] == "independent_validation":
        if review.get("decision") != "approved" or not review.get("reviewer") or not review.get("reviewed_on"):
            raise ValueError("Independent validation requires completed approval metadata")
        if not isinstance(review["reviewer"], str) or not _valid_date(review["reviewed_on"]):
            raise ValueError("Independent validation review metadata is invalid")
        if review["reviewer"] == pack["derived_by"]:
            raise ValueError("Fixture author cannot approve their own validation pack")
    ids = set()
    for fixture in pack["fixtures"]:
        if not isinstance(fixture, dict):
            raise ValueError("Each fixture must be an object")
        for field in ("id", "family", "status", "inputs", "expected", "derivation"):
            if field not in fixture:
                raise ValueError(f"Fixture missing {field}")
        if not isinstance(fixture["id"], str) or not FIXTURE_ID_PATTERN.fullmatch(fixture["id"]):
            raise ValueError(f"Invalid fixture id: {fixture['id']}")
        if fixture["id"] in ids:
            raise ValueError(f"Duplicate fixture id: {fixture['id']}")
        ids.add(fixture["id"])
        allowed_fixture = {"id", "family", "status", "inputs", "expected", "derivation", "limitations"}
        if set(fixture) - allowed_fixture:
            raise ValueError(f"Fixture has unexpected fields: {fixture['id']}")
        if fixture["status"] != pack["status"]:
            raise ValueError(f"Fixture status differs from pack: {fixture['id']}")
        if not isinstance(fixture["family"], str) or not fixture["family"]:
            raise ValueError(f"Fixture family must be populated: {fixture['id']}")
        if not isinstance(fixture["inputs"], dict) or not isinstance(fixture["expected"], dict) or not fixture["expected"]:
            raise ValueError(f"Fixture inputs/expected must be objects: {fixture['id']}")
        if not isinstance(fixture["derivation"], list) or not fixture["derivation"] or not all(
            isinstance(item, str) and item for item in fixture["derivation"]
        ):
            raise ValueError(f"Fixture derivation must contain text: {fixture['id']}")
        if "limitations" in fixture and (
            not isinstance(fixture["limitations"], list)
            or not all(isinstance(item, str) for item in fixture["limitations"])
        ):
            raise ValueError(f"Fixture limitations must be text: {fixture['id']}")
    return True


def _normalise(value):
    """Normalise values for comparison without calculating an expectation."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except Exception:
            return value
    return value


def compare_fixture(fixture, adapters):
    adapter_name = fixture["inputs"]["adapter"]
    if adapter_name not in adapters:
        return {"id": fixture["id"], "outcome": "ERROR", "error": f"No adapter: {adapter_name}"}
    actual = adapters[adapter_name](fixture["inputs"])
    variances = {}
    for field, expected_value in fixture["expected"].items():
        if field not in actual:
            return {"id": fixture["id"], "outcome": "ERROR", "error": f"Missing actual field: {field}"}
        expected_normal = _normalise(expected_value)
        actual_normal = _normalise(actual[field])
        if isinstance(expected_normal, Decimal) and isinstance(actual_normal, Decimal):
            variances[field] = str(actual_normal - expected_normal)
        else:
            variances[field] = None if actual_normal == expected_normal else {
                "expected": expected_value, "actual": actual[field]
            }
    outcome = "PASS" if all(value in ("0", "0.0", "0.00", None) for value in variances.values()) else "FAIL"
    return {
        "id": fixture["id"],
        "fixture_status": fixture["status"],
        "outcome": outcome,
        "expected": fixture["expected"],
        "actual": {
            field: (None if actual[field] is None else str(actual[field]))
            for field in fixture["expected"]
        },
        "variances": variances,
    }


def run_pack(pack, adapters):
    validate_pack(pack)
    return {
        "pack_id": pack["pack_id"],
        "pack_status": pack["status"],
        "derived_by": pack["derived_by"],
        "derived_on": pack["derived_on"],
        "review": pack["review"],
        "sources": pack["sources"],
        "results": [compare_fixture(fixture, adapters) for fixture in pack["fixtures"]],
    }


def load_corpus(corpus_path, *, require_approved=False):
    """Load only the explicitly allowlisted accuracy packs in a corpus file."""
    corpus_path = Path(corpus_path)
    corpus = json.loads(corpus_path.read_text())
    allowed = corpus.get("included_fixture_packs", [])
    if not allowed or any("/" in name or "\\" in name for name in allowed):
        raise ValueError("Corpus pack entries must be explicit local filenames")
    manifest = json.loads((corpus_path.parent / "WP7_FIXTURE_INTEGRITY.json").read_text())
    if set(allowed) != set(manifest.get("files", {})):
        raise ValueError("Corpus allowlist and integrity manifest differ")
    packs = []
    for name in allowed:
        path = corpus_path.parent / name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != manifest["files"][name]:
            raise ValueError(f"Fixture integrity failure: {name}")
        pack = load_pack(path)
        validate_pack(pack)
        if require_approved and pack["status"] != "independent_validation":
            raise ValueError(f"Fixture pack is not independently approved: {name}")
        packs.append(pack)
    return corpus, packs


def assess_corpus(corpus_path):
    """Report integrity-checked approval progress without implying accuracy."""
    corpus, packs = load_corpus(corpus_path)
    approved = [pack for pack in packs if pack["status"] == "independent_validation"]
    pending = [pack for pack in packs if pack["status"] != "independent_validation"]
    return {
        "corpus_id": corpus["corpus_id"],
        "gate_ready": not pending,
        "pack_count": len(packs),
        "approved_pack_ids": [pack["pack_id"] for pack in approved],
        "pending_pack_ids": [pack["pack_id"] for pack in pending],
        "fixture_count": sum(len(pack["fixtures"]) for pack in packs),
        "approved_fixture_count": sum(len(pack["fixtures"]) for pack in approved),
        "pending_fixture_count": sum(len(pack["fixtures"]) for pack in pending),
    }
