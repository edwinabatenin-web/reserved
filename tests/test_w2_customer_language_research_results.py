"""Adversarial tests for the pure W2 research-result structural validator."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_w2_customer_language_research_results.py"
HASH = "a" * 64


def _module():
    spec = importlib.util.spec_from_file_location("w2_result_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _opaque(prefix, number):
    return f"{prefix}-{number:032x}"


def _finding(number=1, code="wording_friction_or_hesitation", severity="minor", reviewed=False):
    return {
        "finding_id": _opaque("fid", number), "interpretation_code": code,
        "severity": severity, "evidence_mode": "distinct_finding_evidence",
        "evidence_reference": _opaque("fev", number),
        "second_researcher_reviewed": reviewed,
    }


def _bundle(module, session_count=1):
    sessions = []
    for session_number in range(1, session_count + 1):
        observations = []
        for case_number, case_id in enumerate(module.CASE_IDS, 1):
            observation = {
                "case_id": case_id,
                "observation_evidence_reference": _opaque(
                    "obs", session_number * 100 + case_number
                ),
                "findings": [],
            }
            observation.update({field: False for field in module.PROTOCOL_STOP_FIELDS})
            observations.append(observation)
        sessions.append({
            "session_id": _opaque("sid", session_number),
            "session_record_reference": _opaque("srec", session_number),
            "observations": observations,
        })
    return {
        "bundle_version": module.BUNDLE_VERSION,
        "fixture": {"version": module.FIXTURE_VERSION, "sha256": module.FIXTURE_SHA256},
        "gallery": {"sha256": HASH, "case_order": list(module.CASE_IDS)},
        "sessions": sessions,
    }


def _validate(module, bundle):
    return module.validate_research_results(
        json.dumps(bundle), expected_gallery_sha256=HASH,
        expected_case_order=module.CASE_IDS,
    )


def _codes(result):
    return [reason["code"] for reason in result["reasons"]]


def test_complete_bundle_is_structural_only_and_external_states_never_close():
    module = _module()
    result = _validate(module, _bundle(module))
    assert result["status"] == "structurally_complete"
    assert result["structurally_valid"] is result["bundle_structure_complete"] is True
    assert "evidence_complete" not in result
    assert result["evidence_status"] == result["acceptance_status"] == "external_not_established"
    assert all(value is False for value in result["claims"].values())
    limitations = " ".join(result["external_limitations"])
    for term in ("consent", "existence", "authenticity", "pseudonymisation",
                 "representative sampling", "protocol coverage", "evidence truth"):
        assert term in limitations


def test_no_finding_observation_still_requires_traceable_evidence():
    module = _module(); bundle = _bundle(module)
    del bundle["sessions"][0]["observations"][0]["observation_evidence_reference"]
    assert "missing_field" in _codes(_validate(module, bundle))


@pytest.mark.parametrize("payload", ["[]", "null", '"record"', "1", "true"])
def test_non_object_json_roots_fail_closed(payload):
    module = _module()
    result = module.validate_research_results(
        payload, expected_gallery_sha256=HASH, expected_case_order=module.CASE_IDS
    )
    assert result["status"] == "structurally_invalid"
    assert result["reasons"][0]["code"] == "wrong_type"


def test_duplicate_json_keys_are_rejected_without_echo():
    module = _module(); hostile = "HOSTILE_SECRET_KEY"
    payload = '{"%s":1,"%s":2}' % (hostile, hostile)
    result = module.validate_research_results(
        payload, expected_gallery_sha256=HASH, expected_case_order=module.CASE_IDS
    )
    assert result["reasons"] == [{
        "code": "invalid_json", "path": "$",
        "message": "payload is not valid unique-key JSON",
    }]
    assert hostile not in json.dumps(result)


def test_unknown_fields_and_hostile_case_values_are_never_echoed():
    module = _module(); bundle = _bundle(module)
    hostile_key = "HOSTILE_KEY_person@example.com"
    hostile_value = "HOSTILE_CASE_<script>alert(1)</script>"
    bundle[hostile_key] = "secret"
    bundle["sessions"][0]["observations"][0]["case_id"] = hostile_value
    result = _validate(module, bundle); output = json.dumps(result)
    assert hostile_key not in output and hostile_value not in output
    assert {"unknown_field", "unknown_case_id"} <= set(_codes(result))


def test_fixture_gallery_and_order_are_exact():
    module = _module(); bundle = _bundle(module)
    bundle["fixture"]["sha256"] = "0" * 64
    assert "fixture_identity_mismatch" in _codes(_validate(module, bundle))
    bundle = _bundle(module); bundle["gallery"]["sha256"] = "b" * 64
    assert "gallery_identity_mismatch" in _codes(_validate(module, bundle))
    bundle = _bundle(module); bundle["sessions"][0]["observations"].reverse()
    assert "observation_order_mismatch" in _codes(_validate(module, bundle))
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        module.validate_research_results(
            "{}", expected_gallery_sha256=True, expected_case_order=module.CASE_IDS
        )


def test_missing_duplicate_and_unknown_case_coverage_fails_closed():
    module = _module(); bundle = _bundle(module)
    observations = bundle["sessions"][0]["observations"]
    observations[1]["case_id"] = observations[0]["case_id"]
    observations[-1]["case_id"] = "not-a-case"
    result = _validate(module, bundle)
    assert {"duplicate_case_observation", "missing_case_observation", "unknown_case_id"} <= set(_codes(result))
    assert result["reasons"] == sorted(
        result["reasons"], key=lambda item: (item["path"], item["code"], item["message"])
    )


@pytest.mark.parametrize("field", ["session_id", "session_record_reference"])
def test_session_identities_are_bundle_globally_unique(field):
    module = _module(); bundle = _bundle(module, 2)
    bundle["sessions"][1][field] = bundle["sessions"][0][field]
    assert f"duplicate_{field}" in _codes(_validate(module, bundle))


@pytest.mark.parametrize("target", ["observation", "finding_id", "finding_evidence"])
def test_observation_and_finding_identities_are_bundle_globally_unique(target):
    module = _module(); bundle = _bundle(module, 2)
    if target == "observation":
        field = "observation_evidence_reference"
        bundle["sessions"][1]["observations"][0][field] = bundle["sessions"][0]["observations"][0][field]
        expected = "duplicate_observation_evidence_reference"
    else:
        first, second = _finding(1), _finding(2)
        if target == "finding_id":
            second["finding_id"] = first["finding_id"]
        else:
            second["evidence_reference"] = first["evidence_reference"]
        bundle["sessions"][0]["observations"][0]["findings"] = [first]
        bundle["sessions"][1]["observations"][0]["findings"] = [second]
        expected = "duplicate_finding_id" if target == "finding_id" else "duplicate_finding_evidence_reference"
    assert expected in _codes(_validate(module, bundle))


def test_finding_may_explicitly_cite_only_its_enclosing_observation_evidence():
    module = _module(); bundle = _bundle(module)
    observation = bundle["sessions"][0]["observations"][0]
    finding = _finding(); finding["evidence_mode"] = "enclosing_observation_evidence"
    finding["evidence_reference"] = observation["observation_evidence_reference"]
    observation["findings"] = [finding]
    assert _validate(module, bundle)["structurally_valid"] is True
    finding["evidence_reference"] = bundle["sessions"][0]["observations"][1]["observation_evidence_reference"]
    assert "evidence_relationship_mismatch" in _codes(_validate(module, bundle))


@pytest.mark.parametrize("field,value", [
    ("session_id", "sid-Jane-Smith"), ("session_id", "sid-AB123456C"),
    ("session_id", "sid-1234567890"), ("session_id", "sid-" + "a" * 31),
    ("session_record_reference", "srec-jane-smith"),
    ("session_record_reference", "srec-1234567890"),
])
def test_opaque_formats_reject_names_nino_utr_and_malformed_values(field, value):
    module = _module(); bundle = _bundle(module); bundle["sessions"][0][field] = value
    result = _validate(module, bundle)
    assert "invalid_opaque_identifier" in _codes(result)
    assert value not in json.dumps(result)


@pytest.mark.parametrize("field", [
    "name", "email", "phone", "address", "date_of_birth", "utr", "nino",
    "raw_record", "verbatim_answer", "participant", "demographics",
])
def test_direct_identifier_and_raw_record_fields_are_rejected_without_echo(field):
    module = _module(); bundle = _bundle(module); bundle["sessions"][0][field] = "forbidden"
    result = _validate(module, bundle)
    assert "unknown_field" in _codes(result) and field not in json.dumps(result)


@pytest.mark.parametrize("field,stop_code", [
    ("wording_prompts_real_payment", "wording_prompts_real_payment"),
    ("wording_prompts_real_transfer", "wording_prompts_real_transfer"),
    ("wording_prompts_real_filing", "wording_prompts_real_filing"),
    ("prompts_disclosure_real_tax_data", "prompts_disclosure_real_tax_data"),
    ("participant_distress", "participant_distress"),
    ("privacy_incident", "privacy_incident"),
    ("safeguarding_incident", "safeguarding_incident"),
    ("moderator_intervention_required", "moderator_intervention_required"),
    ("accessibility_barrier_prevented_completion", "accessibility_barrier_prevented_completion"),
])
def test_every_protocol_immediate_stop_is_closed_typed_and_forced(field, stop_code):
    module = _module(); bundle = _bundle(module)
    bundle["sessions"][0]["observations"][0][field] = True
    bundle["summary"] = {"stop": False, "severity": "minor"}
    result = _validate(module, bundle)
    assert result["stop_condition_exists"] is True
    assert any(stop["code"] == stop_code for stop in result["stop_conditions"])
    assert "unknown_field" in _codes(result)


@pytest.mark.parametrize("value", [0, 1, "false", None])
def test_protocol_stop_booleans_reject_coercion(value):
    module = _module(); bundle = _bundle(module)
    bundle["sessions"][0]["observations"][0]["privacy_incident"] = value
    assert "wrong_type" in _codes(_validate(module, bundle))


def test_critical_and_recurring_major_stops_ignore_caller_severity():
    module = _module(); bundle = _bundle(module, 2)
    bundle["sessions"][0]["observations"][0]["findings"] = [
        _finding(1, "estimate_as_hmrc_bill", "minor", True)
    ]
    bundle["sessions"][0]["observations"][1]["findings"] = [
        _finding(2, "misses_gap", "minor", False)
    ]
    bundle["sessions"][1]["observations"][1]["findings"] = [
        _finding(3, "misses_gap", "minor", False)
    ]
    result = _validate(module, bundle)
    assert {"severity_mismatch", "second_review_missing"} <= set(_codes(result))
    stop_codes = [stop["code"] for stop in result["stop_conditions"]]
    assert "critical_finding" in stop_codes
    assert stop_codes.count("recurring_major_finding") == 2


def test_stop_records_use_safe_paths_and_never_echo_identifiers():
    module = _module(); bundle = _bundle(module)
    observation = bundle["sessions"][0]["observations"][0]
    observation["privacy_incident"] = True
    observation["findings"] = [_finding(99, "estimate_as_hmrc_bill", "critical", True)]
    result = _validate(module, bundle); output = json.dumps(result)
    values = (
        bundle["sessions"][0]["session_id"],
        bundle["sessions"][0]["session_record_reference"],
        observation["observation_evidence_reference"],
        observation["findings"][0]["finding_id"],
        observation["findings"][0]["evidence_reference"],
    )
    assert all(value not in output for value in values)
    assert all(set(stop) <= {"code", "path", "interpretation_code"}
               for stop in result["stop_conditions"])


def test_output_is_deterministic_and_input_is_not_mutated():
    module = _module(); bundle = _bundle(module); original = copy.deepcopy(bundle)
    assert _validate(module, bundle) == _validate(module, bundle)
    assert bundle == original


def test_source_is_network_inert_read_only_and_explicitly_bounded():
    source = SCRIPT.read_text(encoding="utf-8")
    prohibited = (
        "open(", "pathlib", "os.environ", "getenv", "requests", "urllib", "http.client",
        "socket", "subprocess", "sleep(", "logging", "print(", "write_text", "write_bytes",
        "sqlite", "database", "persistence",
    )
    assert not [term for term in prohibited if term in source.lower()]
    for phrase in (
        "not representative-user validation", "UX acceptance", "W2 completion",
        "assurance", "launch readiness", "cannot establish consent", "pseudonymisation",
        "evidence truth",
    ):
        assert phrase in source
