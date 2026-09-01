#!/usr/bin/env python3
"""Pure structural validator for pseudonymous W2 research-result bundles.

Identifiers use closed, opaque namespaces: ``sid-``, ``srec-``, ``obs-``,
``fid-`` and ``fev-``, each followed by exactly 32 lowercase hexadecimal
characters. Syntax validation cannot establish consent, pseudonymisation,
record/evidence existence or authenticity, representative sampling, protocol
coverage, or evidence truth.

A successful result is not representative-user validation, UX acceptance, W2 completion,
assurance, or launch readiness. The closed schema excludes raw
notes, participant attributes, direct identifiers, and caller-authored summaries.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Sequence

BUNDLE_VERSION = "w2-customer-language-research-results/1.0"
FIXTURE_VERSION = "w2-customer-language-research-cases/1.0"
FIXTURE_SHA256 = "85d872a85d3d6960e58b15780c84f71249bdcc7a32f9fdee17ad52b1ef6b56c8"
CASE_IDS = (
    "hmrc-exact-gap", "local-estimate-exact", "hmrc-surplus", "claim-review-ready",
    "claim-customer-confirmation", "claim-no-reduction", "review-required-suppression",
)
CRITICAL_CODES = frozenset({
    "estimate_as_hmrc_bill", "surplus_as_spendable_cash",
    "view_authorises_payment_or_transfer", "claim_believed_auto_filed",
    "acts_on_suppressed_money",
})
MAJOR_CODES = frozenset({
    "misses_gap", "misses_exact_coverage", "misses_customer_initiation",
    "misses_under_reduction_interest_warning",
})
MINOR_CODES = frozenset({"wording_friction_or_hesitation"})
CODE_SEVERITY = {
    **{code: "critical" for code in CRITICAL_CODES},
    **{code: "major" for code in MAJOR_CODES},
    **{code: "minor" for code in MINOR_CODES},
}
PROTOCOL_STOP_FIELDS = {
    "wording_prompts_real_payment": "wording_prompts_real_payment",
    "wording_prompts_real_transfer": "wording_prompts_real_transfer",
    "wording_prompts_real_filing": "wording_prompts_real_filing",
    "prompts_disclosure_real_tax_data": "prompts_disclosure_real_tax_data",
    "participant_distress": "participant_distress",
    "privacy_incident": "privacy_incident",
    "safeguarding_incident": "safeguarding_incident",
    "moderator_intervention_required": "moderator_intervention_required",
    "accessibility_barrier_prevented_completion": "accessibility_barrier_prevented_completion",
}
ROOT_FIELDS = frozenset({"bundle_version", "fixture", "gallery", "sessions"})
FIXTURE_FIELDS = frozenset({"version", "sha256"})
GALLERY_FIELDS = frozenset({"sha256", "case_order"})
SESSION_FIELDS = frozenset({"session_id", "session_record_reference", "observations"})
OBSERVATION_FIELDS = frozenset({
    "case_id", "observation_evidence_reference", "findings", *PROTOCOL_STOP_FIELDS,
})
FINDING_FIELDS = frozenset({
    "finding_id", "interpretation_code", "severity", "evidence_mode",
    "evidence_reference", "second_researcher_reviewed",
})
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
OPAQUE_RES = {
    "session_id": re.compile(r"sid-[0-9a-f]{32}\Z"),
    "session_record_reference": re.compile(r"srec-[0-9a-f]{32}\Z"),
    "observation_evidence_reference": re.compile(r"obs-[0-9a-f]{32}\Z"),
    "finding_id": re.compile(r"fid-[0-9a-f]{32}\Z"),
    "finding_evidence_reference": re.compile(r"fev-[0-9a-f]{32}\Z"),
}
EVIDENCE_MODES = frozenset({"distinct_finding_evidence", "enclosing_observation_evidence"})


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reason(reasons: list[dict[str, str]], code: str, path: str, message: str) -> None:
    reasons.append({"code": code, "path": path, "message": message})


def _exact_fields(value: Any, fields: frozenset[str], path: str,
                  reasons: list[dict[str, str]]) -> bool:
    if not isinstance(value, dict):
        _reason(reasons, "wrong_type", path, "must be an object")
        return False
    if set(value) - fields:
        _reason(reasons, "unknown_field", path, "one or more fields are not permitted")
    for key in sorted(fields - set(value)):
        _reason(reasons, "missing_field", f"{path}.{key}", "required field is missing")
    return fields <= set(value)


def _string(value: Any, path: str, reasons: list[dict[str, str]]) -> bool:
    if not isinstance(value, str):
        _reason(reasons, "wrong_type", path, "must be a string")
        return False
    return True


def _boolean(value: Any, path: str, reasons: list[dict[str, str]]) -> bool:
    if type(value) is not bool:
        _reason(reasons, "wrong_type", path, "must be a boolean")
        return False
    return True


def _opaque(value: Any, kind: str, path: str, reasons: list[dict[str, str]]) -> bool:
    if not _string(value, path, reasons):
        return False
    if not OPAQUE_RES[kind].fullmatch(value):
        _reason(reasons, "invalid_opaque_identifier", path, f"must use the closed {kind} format")
        return False
    return True


def _ordered_strings(value: Any, path: str, reasons: list[dict[str, str]]) -> list[str] | None:
    if not isinstance(value, list):
        _reason(reasons, "wrong_type", path, "must be an array")
        return None
    if any(not isinstance(item, str) for item in value):
        _reason(reasons, "wrong_type", path, "every item must be a string")
        return None
    return list(value)


def _validate_expected(expected_gallery_sha256: str,
                       expected_case_order: Sequence[str]) -> tuple[str, tuple[str, ...]]:
    if not isinstance(expected_gallery_sha256, str) or not SHA256_RE.fullmatch(expected_gallery_sha256):
        raise ValueError("expected_gallery_sha256 must be a lowercase SHA-256 string")
    if isinstance(expected_case_order, (str, bytes)) or not isinstance(expected_case_order, Sequence):
        raise ValueError("expected_case_order must be an explicit sequence")
    order = tuple(expected_case_order)
    if any(not isinstance(item, str) for item in order):
        raise ValueError("expected_case_order must contain strings")
    if len(order) != len(CASE_IDS) or len(set(order)) != len(order) or set(order) != set(CASE_IDS):
        raise ValueError("expected_case_order must contain every fixture case exactly once")
    return expected_gallery_sha256, order


def validate_research_results(payload: str | bytes, *, expected_gallery_sha256: str,
                              expected_case_order: Sequence[str]) -> dict[str, Any]:
    """Return a deterministic, non-echoing structural result without I/O."""
    expected_hash, expected_order = _validate_expected(expected_gallery_sha256, expected_case_order)
    reasons: list[dict[str, str]] = []
    stops: list[dict[str, str]] = []
    major_occurrences: list[tuple[str, str]] = []
    global_seen = {kind: set() for kind in OPAQUE_RES}
    session_count = observation_count = 0

    if not isinstance(payload, (str, bytes)):
        _reason(reasons, "wrong_type", "$", "payload must be JSON text or bytes")
        data: Any = None
    else:
        try:
            data = json.loads(payload, object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            _reason(reasons, "invalid_json", "$", "payload is not valid unique-key JSON")
            data = None

    parse_failed = bool(reasons and reasons[0]["code"] == "invalid_json")
    if not parse_failed and _exact_fields(data, ROOT_FIELDS, "$", reasons):
        if _string(data["bundle_version"], "$.bundle_version", reasons) and data["bundle_version"] != BUNDLE_VERSION:
            _reason(reasons, "unsupported_version", "$.bundle_version", "unsupported bundle version")
        if _exact_fields(data["fixture"], FIXTURE_FIELDS, "$.fixture", reasons):
            for field, expected in (("version", FIXTURE_VERSION), ("sha256", FIXTURE_SHA256)):
                path = f"$.fixture.{field}"
                if _string(data["fixture"][field], path, reasons) and data["fixture"][field] != expected:
                    _reason(reasons, "fixture_identity_mismatch", path, "does not identify the authoritative fixture")
        if _exact_fields(data["gallery"], GALLERY_FIELDS, "$.gallery", reasons):
            gallery_hash = data["gallery"]["sha256"]
            if _string(gallery_hash, "$.gallery.sha256", reasons):
                if not SHA256_RE.fullmatch(gallery_hash):
                    _reason(reasons, "invalid_sha256", "$.gallery.sha256", "must be a lowercase SHA-256 string")
                elif gallery_hash != expected_hash:
                    _reason(reasons, "gallery_identity_mismatch", "$.gallery.sha256", "does not match the reviewed gallery")
            declared_order = _ordered_strings(data["gallery"]["case_order"], "$.gallery.case_order", reasons)
            if declared_order is not None:
                unknown = set(declared_order) - set(CASE_IDS)
                missing = set(CASE_IDS) - set(declared_order)
                duplicates = any(count > 1 for count in Counter(declared_order).values())
                if unknown:
                    _reason(reasons, "unknown_case_id", "$.gallery.case_order", "contains an unknown case id")
                if missing:
                    _reason(reasons, "missing_case_id", "$.gallery.case_order", "omits a required case id")
                if duplicates:
                    _reason(reasons, "duplicate_case_id", "$.gallery.case_order", "contains a duplicate case id")
                if not unknown and not missing and not duplicates and tuple(declared_order) != expected_order:
                    _reason(reasons, "case_order_mismatch", "$.gallery.case_order", "does not match the reviewed gallery order")

        sessions = data["sessions"]
        if not isinstance(sessions, list):
            _reason(reasons, "wrong_type", "$.sessions", "must be an array")
        else:
            session_count = len(sessions)
            if not sessions:
                _reason(reasons, "incomplete_structure", "$.sessions", "at least one submitted session is required")
            for si, session in enumerate(sessions):
                spath = f"$.sessions[{si}]"
                if not _exact_fields(session, SESSION_FIELDS, spath, reasons):
                    continue
                for field in ("session_id", "session_record_reference"):
                    path, value = f"{spath}.{field}", session[field]
                    if _opaque(value, field, path, reasons):
                        if value in global_seen[field]:
                            _reason(reasons, f"duplicate_{field}", path, "identifier must be bundle-globally unique")
                        global_seen[field].add(value)
                observations = session["observations"]
                if not isinstance(observations, list):
                    _reason(reasons, "wrong_type", f"{spath}.observations", "must be an array")
                    continue
                observation_count += len(observations)
                observed_ids: list[str] = []
                for oi, observation in enumerate(observations):
                    opath = f"{spath}.observations[{oi}]"
                    if not _exact_fields(observation, OBSERVATION_FIELDS, opath, reasons):
                        continue
                    case_id = observation["case_id"]
                    if _string(case_id, f"{opath}.case_id", reasons):
                        observed_ids.append(case_id)
                        if case_id not in CASE_IDS:
                            _reason(reasons, "unknown_case_id", f"{opath}.case_id", "case id is outside the closed fixture vocabulary")
                    observation_evidence = observation["observation_evidence_reference"]
                    if _opaque(observation_evidence, "observation_evidence_reference", f"{opath}.observation_evidence_reference", reasons):
                        seen = global_seen["observation_evidence_reference"]
                        if observation_evidence in seen:
                            _reason(reasons, "duplicate_observation_evidence_reference", f"{opath}.observation_evidence_reference", "reference must be bundle-globally unique")
                        seen.add(observation_evidence)
                    for field, stop_code in PROTOCOL_STOP_FIELDS.items():
                        if _boolean(observation[field], f"{opath}.{field}", reasons) and observation[field]:
                            stops.append({"code": stop_code, "path": opath})
                    findings = observation["findings"]
                    if not isinstance(findings, list):
                        _reason(reasons, "wrong_type", f"{opath}.findings", "must be an array")
                        continue
                    for fi, finding in enumerate(findings):
                        fpath = f"{opath}.findings[{fi}]"
                        if not _exact_fields(finding, FINDING_FIELDS, fpath, reasons):
                            continue
                        finding_id = finding["finding_id"]
                        if _opaque(finding_id, "finding_id", f"{fpath}.finding_id", reasons):
                            if finding_id in global_seen["finding_id"]:
                                _reason(reasons, "duplicate_finding_id", f"{fpath}.finding_id", "identifier must be bundle-globally unique")
                            global_seen["finding_id"].add(finding_id)
                        mode = finding["evidence_mode"]
                        mode_valid = _string(mode, f"{fpath}.evidence_mode", reasons)
                        if mode_valid and mode not in EVIDENCE_MODES:
                            _reason(reasons, "unknown_evidence_mode", f"{fpath}.evidence_mode", "mode is outside the closed vocabulary")
                            mode_valid = False
                        evidence = finding["evidence_reference"]
                        if mode_valid and mode == "enclosing_observation_evidence":
                            if not _string(evidence, f"{fpath}.evidence_reference", reasons) or evidence != observation_evidence:
                                _reason(reasons, "evidence_relationship_mismatch", f"{fpath}.evidence_reference", "must equal the enclosing observation evidence reference")
                        elif mode_valid and _opaque(evidence, "finding_evidence_reference", f"{fpath}.evidence_reference", reasons):
                            if evidence in global_seen["finding_evidence_reference"]:
                                _reason(reasons, "duplicate_finding_evidence_reference", f"{fpath}.evidence_reference", "reference must be bundle-globally unique")
                            global_seen["finding_evidence_reference"].add(evidence)
                        code, severity = finding["interpretation_code"], finding["severity"]
                        valid_code = _string(code, f"{fpath}.interpretation_code", reasons)
                        valid_severity = _string(severity, f"{fpath}.severity", reasons)
                        derived = CODE_SEVERITY.get(code) if valid_code else None
                        if valid_code and derived is None:
                            _reason(reasons, "unknown_interpretation_code", f"{fpath}.interpretation_code", "code is outside the protocol vocabulary")
                        if derived is not None and valid_severity and severity != derived:
                            _reason(reasons, "severity_mismatch", f"{fpath}.severity", "severity does not match the protocol code")
                        reviewed = finding["second_researcher_reviewed"]
                        valid_reviewed = _boolean(reviewed, f"{fpath}.second_researcher_reviewed", reasons)
                        if derived in {"critical", "major"} and valid_reviewed and not reviewed:
                            _reason(reasons, "second_review_missing", f"{fpath}.second_researcher_reviewed", "critical and major findings require independent review")
                        if derived == "critical":
                            stops.append({"code": "critical_finding", "path": fpath, "interpretation_code": code})
                        elif derived == "major":
                            major_occurrences.append((code, fpath))
                duplicates = any(count > 1 for count in Counter(observed_ids).values())
                unknown = set(observed_ids) - set(CASE_IDS)
                missing = set(expected_order) - set(observed_ids)
                if duplicates:
                    _reason(reasons, "duplicate_case_observation", f"{spath}.observations", "contains a duplicate case observation")
                if missing:
                    _reason(reasons, "missing_case_observation", f"{spath}.observations", "omits a required case observation")
                if not duplicates and not unknown and not missing and tuple(observed_ids) != expected_order:
                    _reason(reasons, "observation_order_mismatch", f"{spath}.observations", "observations do not match the reviewed gallery order")

    major_counts = Counter(item[0] for item in major_occurrences)
    for code, path in major_occurrences:
        if major_counts[code] >= 2:
            stops.append({"code": "recurring_major_finding", "path": path, "interpretation_code": code})
    reasons.sort(key=lambda item: (item["path"], item["code"], item["message"]))
    stops.sort(key=lambda item: (item["code"], item["path"], item.get("interpretation_code", "")))
    structurally_valid = not reasons
    return {
        "validator_version": BUNDLE_VERSION,
        "status": "structurally_invalid" if reasons else ("stop_condition" if stops else "structurally_complete"),
        "structurally_valid": structurally_valid,
        "bundle_structure_complete": structurally_valid,
        "evidence_status": "external_not_established",
        "acceptance_status": "external_not_established",
        "external_limitations": [
            "consent cannot be established by this validator",
            "record and evidence existence or authenticity cannot be established by this validator",
            "pseudonymisation cannot be established by this validator",
            "representative sampling cannot be established by this validator",
            "protocol coverage cannot be established by this validator",
            "evidence truth cannot be established by this validator",
        ],
        "stop_condition_exists": bool(stops), "reasons": reasons,
        "stop_conditions": stops,
        "counts": {"sessions": session_count, "observations": observation_count},
        "claims": {
            "representative_user_validation": False, "ux_acceptance": False,
            "w2_completion": False, "assurance": False, "launch_readiness": False,
        },
    }


__all__ = ["BUNDLE_VERSION", "CASE_IDS", "FIXTURE_SHA256", "FIXTURE_VERSION",
           "PROTOCOL_STOP_FIELDS", "validate_research_results"]
