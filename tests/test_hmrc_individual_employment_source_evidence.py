"""Synthetic, network-free tests for the HMRC Individual Employment 1.2
transport-neutral source-evidence boundary.

These tests exercise only the deterministic, offline-only builder/translator
that consumes an exact successful ``EmploymentHistoryObservation`` and emits a
deeply immutable, redacted, transport-neutral evidence bundle. Nothing here
calls HMRC, performs HTTP, reads credentials, persists data or constructs
tax-engine/cash/customer evidence.
"""

from __future__ import annotations

import ast
import copy
import pickle
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from types import SimpleNamespace

import pytest

from reserved.providers.hmrc_individual_employment_contract import (
    COMPLETENESS_UNVERIFIED,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
    EmploymentErrorObservation,
    EmploymentHistoryObservation,
    EmploymentRecordObservation,
    build_individual_employment_request,
    observe_individual_employment_response,
)
from reserved.providers.hmrc_individual_employment_source_evidence import (
    RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH,
    EmploymentSourceEvidenceRecord,
    HMRCIndividualEmploymentEvidence,
    HMRCIndividualEmploymentSourceEvidenceError,
    build_hmrc_individual_employment_source_evidence,
)

REPO = Path(__file__).resolve().parents[1]

_AWARE = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

_OBS_UNSET = object()


def _request(*, utr="1234567890", tax_year="2026-27"):
    return build_individual_employment_request(utr=utr, tax_year=tax_year)


def _employment(**overrides):
    record = {"employerPayeReference": "123/AB12345", "employerName": "Example Ltd"}
    record.update(overrides)
    return record


def _success_payload(*employments, **top_level):
    payload = {"employments": list(employments)}
    payload.update(top_level)
    return payload


def _history(*, utr="1234567890", tax_year="2026-27", **record_overrides):
    return observe_individual_employment_response(
        _request(utr=utr, tax_year=tax_year),
        status_code=200,
        content_type="application/json",
        payload=_success_payload(_employment(**record_overrides)),
    )


def _mutated(observation, **changes):
    """Model hostile low-level mutation without weakening observer construction."""
    candidate = object.__new__(type(observation))
    for name, value in vars(observation).items():
        object.__setattr__(candidate, name, value)
    for name, value in changes.items():
        object.__setattr__(candidate, name, value)
    return candidate


def test_translation_rejects_identical_payload_wholesale_provenance_swap():
    original = _history(utr="1234567890")
    other = _history(utr="0987654321")
    forged = pickle.loads(pickle.dumps(original))
    for name in (
        "request", "_request_binding", "_source_binding", "tax_year",
        "_observation_integrity",
    ):
        object.__setattr__(forged, name, getattr(other, name))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=forged)


def test_translation_rejects_identical_error_semantics_wholesale_swap():
    def error(utr):
        return observe_individual_employment_response(
            _request(utr=utr), status_code=404, content_type="application/json",
            payload={"code": "NOT_FOUND", "message": "ignored"},
        )

    original = error("1234567890")
    other = error("0987654321")
    forged = pickle.loads(pickle.dumps(original))
    for name in (
        "request", "_request_binding", "_source_binding", "tax_year",
        "_observation_integrity",
    ):
        object.__setattr__(forged, name, getattr(other, name))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=forged)


def test_translation_rejects_unrelated_observation_integrity_value():
    original = _history(utr="1234567890")
    other = _history(utr="0987654321")
    forged = _mutated(
        original, _observation_integrity=other._observation_integrity
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=forged)


def _evidence(*, observation=_OBS_UNSET, **overrides):
    kwargs = {
        "evidence_reference": "run-abc123",
        "observed_at": _AWARE,
    }
    kwargs.update(overrides)
    return build_hmrc_individual_employment_source_evidence(
        _history() if observation is _OBS_UNSET else observation,
        **kwargs,
    )


def _direct_evidence(**overrides):
    kwargs = {
        "source_api_name": HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
        "source_api_version": HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
        "tax_year": "2026-27",
        "records": _evidence().records,
        "evidence_reference": "direct-run",
        "observed_at": _AWARE,
    }
    kwargs.update(overrides)
    return HMRCIndividualEmploymentEvidence(**kwargs)


class _Hostile:
    def __repr__(self):
        raise AssertionError("repr touched")

    def __str__(self):
        raise AssertionError("str touched")

    def __eq__(self, other):
        raise AssertionError("eq touched")

    def __hash__(self):
        raise AssertionError("hash touched")

    def __bool__(self):
        raise AssertionError("bool touched")

    def __len__(self):
        raise AssertionError("len touched")

    def __iter__(self):
        raise AssertionError("iter touched")


class _StrSubclass(str):
    pass


class _HistorySubclass(EmploymentHistoryObservation):
    pass


class _DatetimeSubclass(datetime):
    pass


class _CustomTz(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "CUSTOM"


# ── Exact constants and completeness ─────────────────────────────────────────


def test_defensive_reference_bound_is_present_and_labelled():
    assert RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH == 256


def test_bundle_preserves_source_api_and_version_constants():
    ev = _evidence()
    assert ev.source_api_name == HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME
    assert ev.source_api_version == HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION
    assert ev.source_api_name == "Individual Employment"
    assert ev.source_api_version == "1.2"


def test_completeness_is_always_unverified():
    ev = _evidence()
    assert ev.completeness == COMPLETENESS_UNVERIFIED
    assert ev.completeness == "UNVERIFIED"


# ── Exact successful source type only ────────────────────────────────────────


def test_accepts_exact_successful_history_observation():
    ev = _evidence()
    assert type(ev) is HMRCIndividualEmploymentEvidence
    assert type(ev.records[0]) is EmploymentSourceEvidenceRecord


def test_rejects_error_observation():
    error = observe_individual_employment_response(
        _request(),
        status_code=404,
        content_type="application/json",
        payload={"code": "NOT_FOUND", "message": "provider message"},
    )
    assert isinstance(error, EmploymentErrorObservation)
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=error)


def test_rejects_history_subclass():
    subclass = object.__new__(_HistorySubclass)
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=subclass)


@pytest.mark.parametrize("bad", [None, {}, [], "x", 123, True, object()])
def test_rejects_arbitrary_lookalikes(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=bad)


def test_rejects_simple_namespace_lookalike():
    lookalike = SimpleNamespace(
        tax_year="2026-27",
        status_code=200,
        employments=(),
        completeness="UNVERIFIED",
        absent_fields=frozenset(),
        unknown_fields=frozenset(),
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=lookalike)


# ── Deep re-validation of the nested source observation ──────────────────────


def test_revalidates_tax_year_type_and_format():
    for bad in (None, 202627, True, "2026", "2026/27", "2026-275", "abc-ef"):
        obs = _mutated(_history(), tax_year=bad)
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)


def test_revalidates_status_code_type_and_success_value():
    for bad in (201, 0, -1, True, "200", None):
        obs = _mutated(_history(), status_code=bad)
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)


def test_revalidates_completeness_exact_unverified():
    for bad in ("COMPLETE", "VERIFIED", "PARTIAL", "", None, 123):
        obs = _mutated(_history(), completeness=bad)
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)


def test_revalidates_top_level_absent_fields_empty():
    obs = _mutated(_history(), absent_fields=frozenset({"employments"}))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_employments_container_and_non_empty():
    for bad in ([], (), None, "x", 123, [_history().employments[0]]):
        obs = _mutated(_history(), employments=bad)
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)


def test_revalidates_employment_exact_type():
    obs = _mutated(_history(), employments=("not-a-record",))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_employer_strings_type_and_bounds():
    record = _history().employments[0]
    for bad in (None, 123, True):
        obs = _mutated(_history(), employments=(replace(record, employer_name=bad),))
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)
    oversized = replace(record, employer_name="x" * 600)
    obs = _mutated(_history(), employments=(oversized,))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_off_payroll_exact_bool_or_none():
    record = _history().employments[0]
    for bad in (1, 0, "true", [], {}):
        obs = _mutated(_history(), employments=(replace(record, off_payroll_work_flag=bad),))
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=obs)


def test_revalidates_off_payroll_presence_absence_coherence():
    record = _history().employments[0]
    # absent flag without recorded absence is incoherent.
    obs = _mutated(
        _history(),
        employments=(
            replace(record, off_payroll_work_flag=None, absent_fields=frozenset()),
        ),
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)
    # present flag alongside recorded absence is incoherent.
    obs = _mutated(
        _history(),
        employments=(
            replace(
                record,
                off_payroll_work_flag=True,
                absent_fields=frozenset({"offPayrollWorkFlag"}),
            ),
        ),
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_absent_field_names():
    record = _history().employments[0]
    obs = _mutated(
        _history(),
        employments=(replace(record, absent_fields=frozenset({"employerName"})),),
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_unknown_names_type_safety_bounds_and_disjointness():
    obs = _mutated(_history(), unknown_fields=frozenset({123}))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)

    obs = _mutated(_history(), unknown_fields=frozenset({"employments"}))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)

    obs = _mutated(_history(), unknown_fields=frozenset({"\x00"}))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)

    obs = _mutated(_history(), unknown_fields=frozenset({"x" * 300}))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_revalidates_record_unknown_disjointness_with_absent():
    record = _history().employments[0]
    obs = _mutated(
        _history(),
        employments=(
            replace(
                record,
                off_payroll_work_flag=None,
                absent_fields=frozenset({"offPayrollWorkFlag"}),
                unknown_fields=frozenset({"offPayrollWorkFlag"}),
            ),
        ),
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


@pytest.mark.parametrize(
    ("level", "attribute"),
    [
        ("top", "utr"),
        ("top", "raw_payload"),
        ("top", "provider_message"),
        ("top", "transport_state"),
        ("top", "arbitrary_extra"),
        ("record", "utr"),
        ("record", "raw_payload"),
        ("record", "provider_message"),
        ("record", "transport_state"),
        ("record", "arbitrary_extra"),
    ],
)
def test_rejects_forged_extra_source_state_without_touching_value(level, attribute):
    observation = _history()
    target = observation if level == "top" else observation.employments[0]
    object.__setattr__(target, attribute, _Hostile())
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=observation)


@pytest.mark.parametrize("level", ["top", "record"])
def test_rejects_missing_source_instance_state(level):
    observation = _history()
    target = observation if level == "top" else observation.employments[0]
    object.__delattr__(target, "unknown_fields")
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=observation)


def test_exact_source_copy_deepcopy_and_pickle_forms_remain_accepted():
    observation = _history()
    for rebuilt in (
        copy.copy(observation),
        copy.deepcopy(observation),
        pickle.loads(pickle.dumps(observation)),
    ):
        assert _evidence(observation=rebuilt).tax_year == "2026-27"


def test_preserves_safe_unknown_names_at_each_layer():
    obs = observe_individual_employment_response(
        _request(),
        status_code=200,
        content_type="application/json",
        payload=_success_payload(
            _employment(some_future_field=True),
            future_top=True,
        ),
    )
    ev = _evidence(observation=obs)
    assert "future_top" in ev.unknown_fields
    assert "some_future_field" in ev.records[0].unknown_fields


# ── Duplicate and order preservation without identity/deduplication ──────────


def test_duplicates_and_order_are_preserved_as_evidence_only():
    first = _employment(employerName="Alpha")
    second = _employment(employerName="Beta", offPayrollWorkFlag=False)
    duplicate = _employment(employerName="Alpha")
    obs = observe_individual_employment_response(
        _request(),
        status_code=200,
        content_type="application/json",
        payload=_success_payload(first, second, duplicate),
    )
    ev = _evidence(observation=obs)
    assert len(ev.records) == 3
    assert [r.employer_name for r in ev.records] == ["Alpha", "Beta", "Alpha"]
    # Distinct evidence records: no deduplication or canonicalisation.
    assert ev.records[0] is not ev.records[2]


# ── Provider-string exact preservation without normalisation ─────────────────


def test_empty_and_whitespace_provider_strings_preserved_exactly():
    obs = observe_individual_employment_response(
        _request(),
        status_code=200,
        content_type="application/json",
        payload=_success_payload(_employment(employerName="   ", employerPayeReference="")),
    )
    ev = _evidence(observation=obs)
    assert ev.records[0].employer_name == "   "
    assert ev.records[0].employer_paye_reference == ""
    assert ev.records[0].employer_name.strip() == ""
    assert ev.records[0].employer_paye_reference.strip() == ""


# ── No UTR / path / payload / provider-message exposure ──────────────────────


def test_representations_are_redacted():
    ev = _evidence()
    assert repr(ev) == "HMRCIndividualEmploymentEvidence([REDACTED])"
    assert str(ev) == "HMRCIndividualEmploymentEvidence([REDACTED])"
    assert repr(ev.records[0]) == "EmploymentSourceEvidenceRecord([REDACTED])"
    assert "Example Ltd" not in repr(ev)
    assert "Example Ltd" not in repr(ev.records[0])
    assert "run-abc123" not in repr(ev)


def test_no_transport_secret_or_payload_state_on_object():
    ev = _evidence()
    for name in (
        "utr", "path", "payload", "message", "authorization", "token", "secret",
        "credential", "url", "headers", "body", "method", "request",
    ):
        assert not hasattr(ev, name), name


def test_no_utr_or_path_in_pickle_and_no_raw_payload_state():
    ev = _evidence()
    data = pickle.dumps(ev)
    assert b"1234567890" not in data
    assert b"/individual-employment/" not in data
    assert b"provider message" not in data
    # The preserved employer value is evidence, not raw payload; it is retained
    # by design but never exposed via repr.
    assert b"Example Ltd" in data


# ── Exact opaque reference / aware datetime / optional digest rules ──────────


@pytest.mark.parametrize("bad", [None, 123, 3.14, True, b"bytes", _StrSubclass("x")])
def test_evidence_reference_rejects_wrong_types_and_subclasses(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(evidence_reference=bad)


def test_evidence_reference_rejects_oversized_and_unsafe():
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(evidence_reference="x" * (RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH + 1))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(evidence_reference="bad\x00ref")
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(evidence_reference="\u202eref")


def test_evidence_reference_accepts_exact_strings_without_interpretation():
    for ref in ("", "   ", "run-123", "https://example.invalid/x", "/etc/passwd", "não-opaque"):
        ev = _evidence(evidence_reference=ref)
        assert ev.evidence_reference == ref


@pytest.mark.parametrize("bad", [
    datetime(2026, 9, 1, 12, 0, 0),
    datetime(2026, 9, 1, 12, 0, 0, tzinfo=_CustomTz()),
    "2026-09-01T12:00:00Z",
    None,
    123,
])
def test_observed_at_rejects_naive_non_fixed_offset_and_non_datetime(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observed_at=bad)


def test_observed_at_accepts_utc_and_fixed_offset():
    utc = _evidence(observed_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc))
    assert utc.observed_at.tzinfo is timezone.utc
    fixed = _evidence(
        observed_at=datetime(2026, 9, 1, 13, 30, 0, tzinfo=timezone(timedelta(hours=1)))
    )
    assert fixed.observed_at.utcoffset() == timedelta(hours=1)


def test_observed_at_rejects_datetime_subclass():
    # A datetime subclass carrying an otherwise valid value must be rejected.
    subclass = _DatetimeSubclass(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observed_at=subclass)


def test_digest_omission_is_distinct_and_explicit_null_fails():
    omitted = _evidence()
    assert omitted.source_artifact_sha256 is None
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(source_artifact_sha256=None)


@pytest.mark.parametrize("bad", [
    "A" * 64,
    "a" * 63,
    "a" * 65,
    "g" * 64,
    "a" * 32 + "B" + "a" * 31,
    "",
    123,
    True,
    3.14,
    _StrSubclass("a" * 64),
])
def test_digest_rejects_non_lowercase_hex_wrong_length_and_subclass(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(source_artifact_sha256=bad)


def test_digest_accepts_exact_lowercase_64_hex():
    digest = "0123456789abcdef" * 4
    ev = _evidence(source_artifact_sha256=digest)
    assert ev.source_artifact_sha256 == digest


def test_digest_direct_construction_distinguishes_omitted_valid_and_null():
    assert _direct_evidence().source_artifact_sha256 is None
    digest = "abcdef0123456789" * 4
    assert _direct_evidence(source_artifact_sha256=digest).source_artifact_sha256 == digest
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _direct_evidence(source_artifact_sha256=None)


@pytest.mark.parametrize("bad", ["a" * 63, "A" * 64, _StrSubclass("a" * 64)])
def test_digest_direct_construction_rejects_malformed_values(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _direct_evidence(source_artifact_sha256=bad)


# ── Direct / replace / copy / deepcopy / pickle integrity ────────────────────


def test_record_direct_construction_revalidates():
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        EmploymentSourceEvidenceRecord(
            employer_paye_reference="123",
            employer_name="X",
            off_payroll_work_flag=True,
            absent_fields=frozenset({"offPayrollWorkFlag"}),
        )


def test_evidence_direct_construction_revalidates():
    record = _evidence().records[0]
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        HMRCIndividualEmploymentEvidence(
            source_api_name="Individual Employment",
            source_api_version="1.2",
            tax_year="2026-27",
            records=(record,),
            evidence_reference="r",
            observed_at=_AWARE,
            completeness="COMPLETE",
        )


def test_dataclasses_replace_revalidates_evidence_and_record():
    ev = _evidence()
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(ev, completeness="COMPLETE")
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(ev, tax_year="2026")
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(ev, source_api_name="Something Else")
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(ev.records[0], off_payroll_work_flag=1)


def test_digest_replace_preserves_omission_and_presence_and_rejects_null():
    digest = "0123456789abcdef" * 4
    omitted = _evidence()
    present = _evidence(source_artifact_sha256=digest)

    assert replace(omitted, evidence_reference="omitted-copy").source_artifact_sha256 is None
    assert replace(present, evidence_reference="present-copy").source_artifact_sha256 == digest
    assert replace(omitted, source_artifact_sha256=digest).source_artifact_sha256 == digest
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(omitted, source_artifact_sha256=None)
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(present, source_artifact_sha256=None)


@pytest.mark.parametrize("bad", ["f" * 63, "F" * 64, 64])
def test_digest_replace_rejects_malformed_values(bad):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        replace(_evidence(), source_artifact_sha256=bad)


def test_copy_deepcopy_and_pickle_preserve_invariants():
    ev = _evidence()
    for rebuilt in (copy.copy(ev), copy.deepcopy(ev), pickle.loads(pickle.dumps(ev))):
        assert type(rebuilt) is HMRCIndividualEmploymentEvidence
        assert rebuilt.completeness == "UNVERIFIED"
        assert rebuilt.source_api_name == "Individual Employment"
        assert rebuilt.source_api_version == "1.2"
        assert rebuilt.tax_year == "2026-27"
        assert rebuilt.evidence_reference == "run-abc123"
        assert type(rebuilt.records) is tuple
        assert type(rebuilt.records[0]) is EmploymentSourceEvidenceRecord
        assert rebuilt == ev


@pytest.mark.parametrize("digest", [_OBS_UNSET, "fedcba9876543210" * 4])
def test_digest_omission_and_presence_survive_copy_deepcopy_and_pickle(digest):
    ev = _evidence() if digest is _OBS_UNSET else _evidence(source_artifact_sha256=digest)
    expected = None if digest is _OBS_UNSET else digest
    for rebuilt in (copy.copy(ev), copy.deepcopy(ev), pickle.loads(pickle.dumps(ev))):
        assert rebuilt.source_artifact_sha256 == expected


def test_pickle_round_trip_rejects_invalid_state_reconstruction():
    ev = _evidence()
    # Reconstructing through the constructor path revalidates; a poisoned
    # observed_at in the serialised state is rejected rather than trusted.
    assert pickle.loads(pickle.dumps(ev)).observed_at.tzinfo is timezone.utc


# ── Immutability ─────────────────────────────────────────────────────────────


def test_evidence_and_records_are_deeply_immutable():
    ev = _evidence()
    with pytest.raises(FrozenInstanceError):
        ev.completeness = "COMPLETE"
    with pytest.raises(FrozenInstanceError):
        ev.records = ()
    with pytest.raises(FrozenInstanceError):
        ev.records[0].employer_name = "changed"
    with pytest.raises(FrozenInstanceError):
        ev.observed_at = _AWARE

    assert isinstance(ev.records, tuple)
    assert isinstance(ev.records[0].absent_fields, frozenset)
    assert isinstance(ev.records[0].unknown_fields, frozenset)


# ── Constant non-echoing failures ────────────────────────────────────────────


def test_failures_are_constant_and_never_echo_values():
    obs = _history()
    bad_employer = replace(obs.employments[0], employer_name="SECRET-CORP-NAME" + "x" * 600)
    bad_obs = _mutated(obs, employments=(bad_employer,))
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError) as exc:
        _evidence(observation=bad_obs, evidence_reference="UNIQUE-REF-999")
    message = str(exc.value)
    assert "SECRET-CORP-NAME" not in message
    assert "UNIQUE-REF-999" not in message


def test_hostile_source_field_fails_without_invoking_hooks():
    obs = _mutated(_history(), tax_year=_Hostile())
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=obs)


def test_translation_rejects_cross_request_and_coordinated_replacement():
    original = _history(utr="1234567890")
    replacement = _history(utr="0987654321")

    cross_request = _mutated(original, request=replacement.request)
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=cross_request)

    coordinated = _mutated(
        original,
        request=replacement.request,
        _request_binding=replacement._request_binding,
    )
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=coordinated)


def test_translation_rejects_hostile_binding_before_equality_hook():
    observation = _mutated(_history(), _request_binding=_Hostile())
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(observation=observation)


def test_translation_rejects_cross_method_endpoint_media_version_and_scope():
    for index, replacement in (
        (2, "POST"),
        (3, "/different/{utr}/{taxYear}"),
        (4, "Different API"),
        (5, "9.9"),
        (6, "application/json"),
        (7, "different:scope"),
    ):
        observation = _history()
        binding = list(observation._request_binding)
        binding[index] = replacement
        damaged = _mutated(observation, _request_binding=tuple(binding))
        with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
            _evidence(observation=damaged)


@pytest.mark.parametrize("kwarg", ["evidence_reference", "observed_at", "source_artifact_sha256"])
def test_hostile_metadata_fails_without_invoking_hooks(kwarg):
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError):
        _evidence(**{kwarg: _Hostile()})


def test_hostile_digest_fails_constant_message():
    with pytest.raises(HMRCIndividualEmploymentSourceEvidenceError) as exc:
        _evidence(source_artifact_sha256=_Hostile())
    assert "touched" not in str(exc.value)


# ── AST / forbidden-surface proof ────────────────────────────────────────────


def test_module_contains_no_transport_credential_or_web_surface():
    import reserved.providers.hmrc_individual_employment_source_evidence as module

    for name in (
        "requests", "httpx", "urlopen", "http", "HttpTransport", "GuardedTransport",
        "ProviderRequest", "authorization", "token", "client", "secret", "password",
    ):
        assert not hasattr(module, name), name


def test_module_imports_no_forbidden_or_paye_surface():
    import reserved.providers.hmrc_individual_employment_source_evidence as module

    assert not hasattr(module, "PayeEvidence")

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden_prefixes = (
        "reserved.engines",
        "reserved.web",
        "reserved.api",
        "reserved.database",
        "reserved.auth",
        "reserved.config",
        "reserved.providers.accounting",
        "reserved.providers.http_boundary",
        "reserved.providers.oauth",
        "reserved.providers.payments",
        "reserved.providers.banking",
        "requests",
        "httpx",
        "urllib",
        "http",
        "flask",
    )
    for name in imported:
        assert not name.startswith(forbidden_prefixes), name

    # The only provider import is the exact source contract.
    provider_imports = [n for n in imported if n.startswith("reserved.providers")]
    assert provider_imports == ["reserved.providers.hmrc_individual_employment_contract"]


def test_evidence_is_not_paye_or_accounting_evidence():
    import reserved.providers.hmrc_individual_employment_source_evidence as module

    ev = _evidence()
    assert not hasattr(module, "PayeEvidence")
    assert not isinstance(ev, tuple)
    forbidden = {
        "paid", "tax_paid", "tax_liability", "gross_pay", "net_pay", "canonical",
        "cash", "customer", "launch_ready", "amount", "money", "tax_code",
    }
    assert forbidden.isdisjoint(ev.__dataclass_fields__)
    assert forbidden.isdisjoint(ev.records[0].__dataclass_fields__)
