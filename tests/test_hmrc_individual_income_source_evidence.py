"""Adversarial offline tests for Individual Income 1.2 source evidence."""

from __future__ import annotations

import ast
import copy
import importlib
import pickle
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.providers.hmrc_individual_income_contract import (
    HMRC_INDIVIDUAL_INCOME_API,
    HMRC_INDIVIDUAL_INCOME_API_VERSION,
    HMRC_INDIVIDUAL_INCOME_COMPLETENESS,
    IndividualIncomeAnnualSummaryObservation,
    IndividualIncomeErrorObservation,
    build_individual_income_request,
    observe_individual_income_response,
)
from reserved.providers.hmrc_individual_income_source_evidence import (
    RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH,
    HMRCIndividualIncomeSourceEvidence,
    HMRCIndividualIncomeSourceEvidenceError,
    IndividualIncomeEmploymentSourceEvidence,
    IndividualIncomePensionsBenefitsSourceEvidence,
    build_hmrc_individual_income_source_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
UTR = "0123456789"
NOW = datetime(2026, 9, 3, 12, 30, tzinfo=timezone(timedelta(hours=1)))
UNSET = object()


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

    def __iter__(self):
        raise AssertionError("iter touched")


class _StrSubclass(str):
    pass


class _IntSubclass(int):
    pass


class _DecimalSubclass(Decimal):
    pass


class _DatetimeSubclass(datetime):
    pass


class _CustomTimezone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


class _ObservationSubclass(IndividualIncomeAnnualSummaryObservation):
    pass


def _request(*, utr=UTR, tax_year="2023-24"):
    return build_individual_income_request(utr=utr, tax_year=tax_year)


def _payload(*, employments=None, benefits=None, **unknown):
    value = {
        "employments": [] if employments is None else employments,
        "pensionsAnnuitiesAndOtherStateBenefits": {} if benefits is None else benefits,
    }
    value.update(unknown)
    return value


def _observation(*, payload=None, request=None):
    return observe_individual_income_response(
        request or _request(),
        status_code=200,
        content_type="application/json",
        payload=_payload() if payload is None else payload,
    )


def _error():
    return observe_individual_income_response(
        _request(),
        status_code=404,
        content_type="application/json",
        payload={"code": "NOT_FOUND", "message": "never retained"},
    )


def _evidence(*, observation=UNSET, **overrides):
    kwargs = {"evidence_reference": "run-income-123", "observed_at": NOW}
    kwargs.update(overrides)
    return build_hmrc_individual_income_source_evidence(
        _observation() if observation is UNSET else observation,
        **kwargs,
    )


def _mutated(value, **changes):
    candidate = object.__new__(type(value))
    for name, item in vars(value).items():
        object.__setattr__(candidate, name, item)
    for name, item in changes.items():
        object.__setattr__(candidate, name, item)
    return candidate


def test_exact_source_constants_tax_year_completeness_and_metadata():
    evidence = _evidence()
    assert evidence.source_api_name == HMRC_INDIVIDUAL_INCOME_API == "individual-income"
    assert evidence.source_api_version == HMRC_INDIVIDUAL_INCOME_API_VERSION == "1.2"
    assert evidence.tax_year == "2023-24"
    assert evidence.completeness == HMRC_INDIVIDUAL_INCOME_COMPLETENESS == "UNVERIFIED"
    assert evidence.evidence_reference == "run-income-123"
    assert evidence.observed_at is NOW
    assert RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH == 256


def test_nonempty_shape_preserves_exact_order_duplicates_numbers_and_unknown_names():
    negative_zero = Decimal("-0.00")
    payload = _payload(
        employments=[
            {"employerPayeReference": "123/AB", "payFromEmployment": 7, "futureA": _Hostile()},
            {"employerPayeReference": "123/AB", "payFromEmployment": negative_zero, "futureB": _Hostile()},
        ],
        benefits={
            "otherPensionsAndRetirementAnnuities": Decimal("10.500"),
            "incapacityBenefit": 0,
            "futureBenefit": _Hostile(),
        },
        futureTop=_Hostile(),
    )
    evidence = _evidence(observation=_observation(payload=payload))
    assert tuple(item.employer_paye_reference for item in evidence.employments) == (
        "123/AB", "123/AB",
    )
    assert evidence.employments[0].pay_from_employment == 7
    retained_zero = evidence.employments[1].pay_from_employment
    assert type(retained_zero) is Decimal and retained_zero.as_tuple() == negative_zero.as_tuple()
    assert evidence.employments[0].unknown_names == frozenset({"futureA"})
    assert evidence.employments[1].unknown_names == frozenset({"futureB"})
    benefits = evidence.pensions_benefits
    assert benefits.other_pensions_and_retirement_annuities.as_tuple() == Decimal("10.500").as_tuple()
    assert benefits.incapacity_benefit == 0 and type(benefits.incapacity_benefit) is int
    assert benefits.present_fields == frozenset({
        "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
    })
    assert benefits.unknown_names == frozenset({"futureBenefit"})
    assert evidence.unknown_names == frozenset({"futureTop"})


@pytest.mark.parametrize("reference", ("", "  ", "A\nB", "\u202ePAYE"))
def test_source_valid_employer_reference_is_preserved_literally(reference):
    evidence = _evidence(observation=_observation(payload=_payload(
        employments=[{
            "employerPayeReference": reference,
            "payFromEmployment": 1,
        }]
    )))
    assert evidence.employments[0].employer_paye_reference == reference


def test_empty_employments_and_all_omitted_benefits_are_valid_but_unverified():
    evidence = _evidence()
    assert evidence.employments == ()
    benefits = evidence.pensions_benefits
    assert benefits.present_fields == frozenset()
    assert benefits.absent_fields == frozenset({
        "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
        "jobseekersAllowance", "seissNetPaid",
    })
    assert all(getattr(benefits, name) is None for name in (
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "jobseekers_allowance", "seiss_net_paid",
    ))
    assert evidence.completeness == "UNVERIFIED"


def test_absence_is_distinct_from_explicit_zero():
    absent = _evidence().pensions_benefits
    zero = _evidence(observation=_observation(payload=_payload(
        benefits={"jobseekersAllowance": 0}
    ))).pensions_benefits
    assert absent.jobseekers_allowance is None
    assert "jobseekersAllowance" in absent.absent_fields
    assert zero.jobseekers_allowance == 0
    assert "jobseekersAllowance" in zero.present_fields
    assert absent != zero


def test_error_subtype_lookalike_and_incomplete_source_are_rejected():
    assert isinstance(_error(), IndividualIncomeErrorObservation)
    for source in (_error(), object(), {}, _ObservationSubclass.__new__(_ObservationSubclass),
                   object.__new__(IndividualIncomeAnnualSummaryObservation)):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            _evidence(observation=source)


@pytest.mark.parametrize("field,replacement", (
    ("tax_year", "2024-25"),
    ("completeness", "COMPLETE"),
    ("employments", []),
    ("unknown_names", set()),
    ("_request_binding", ("forged",)),
    ("request", _request(tax_year="2024-25")),
))
def test_full_source_mutations_fail_closed(field, replacement):
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        _evidence(observation=_mutated(_observation(), **{field: replacement}))


def test_nested_mutation_and_coordinated_partial_request_substitution_fail():
    source = _observation(payload=_payload(
        employments=[{"employerPayeReference": "A", "payFromEmployment": Decimal("1.00")}]
    ))
    bad_item = copy.copy(source.employments[0])
    object.__setattr__(bad_item, "pay_from_employment", Decimal("1e-20"))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        _evidence(observation=_mutated(source, employments=(bad_item,)))
    source = _observation(payload=_payload(
        employments=[{"employerPayeReference": "A", "payFromEmployment": Decimal("1.00")}]
    ))
    other = _observation(request=_request(tax_year="2024-25"))
    coordinated = _mutated(
        source,
        request=other.request,
        _request_binding=other._request_binding,
        tax_year=other.tax_year,
    )
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        _evidence(observation=coordinated)


def test_source_nested_subclasses_are_rejected():
    source = _observation(payload=_payload(
        employments=[{"employerPayeReference": "A", "payFromEmployment": 1}]
    ))
    item = replace(source.employments[0])
    object.__setattr__(item, "employer_paye_reference", _StrSubclass("A"))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        _evidence(observation=_mutated(source, employments=(item,)))


def test_utr_request_path_payload_and_error_message_are_not_retained():
    evidence = _evidence()
    snapshot = repr(evidence) + repr(vars(evidence)) + repr(pickle.dumps(evidence))
    assert UTR not in snapshot
    for forbidden in ("request", "path", "payload", "message", "utr"):
        assert forbidden not in evidence.__dataclass_fields__
    assert not hasattr(evidence, "request") and not hasattr(evidence, "utr")


def test_digest_omission_is_distinct_and_explicit_none_or_malformed_rejected():
    absent = _evidence()
    present = _evidence(source_artifact_sha256="a" * 64)
    assert absent.source_artifact_sha256 is None
    assert present.source_artifact_sha256 == "a" * 64
    assert absent != present
    for value in (None, "A" * 64, "a" * 63, _StrSubclass("a" * 64), _Hostile()):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            _evidence(source_artifact_sha256=value)


@pytest.mark.parametrize("reference", ("", "x" * 257, "bad\nref", _StrSubclass("run"), _Hostile()))
def test_evidence_reference_is_exact_bounded_opaque_and_non_echoing(reference):
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError) as exc:
        _evidence(evidence_reference=reference)
    assert "bad\nref" not in str(exc.value)
    assert "x" * 50 not in str(exc.value)


@pytest.mark.parametrize("value", (
    datetime(2026, 1, 1),
    _DatetimeSubclass(2026, 1, 1, tzinfo=timezone.utc),
    datetime(2026, 1, 1, tzinfo=_CustomTimezone()),
    "2026-01-01T00:00:00Z",
))
def test_observed_at_requires_exact_aware_fixed_offset_datetime(value):
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        _evidence(observed_at=value)


def test_deep_immutability_copy_deepcopy_pickle_replace_and_validation():
    evidence = _evidence(observation=_observation(payload=_payload(
        employments=[{"employerPayeReference": "A", "payFromEmployment": Decimal("1.20")}]
    )))
    with pytest.raises(FrozenInstanceError):
        evidence.tax_year = "2024-25"
    with pytest.raises(FrozenInstanceError):
        evidence.employments[0].pay_from_employment = 9
    assert copy.copy(evidence) is evidence
    assert copy.deepcopy(evidence) is evidence
    rebuilt = pickle.loads(pickle.dumps(evidence))
    assert rebuilt == evidence and rebuilt is not evidence
    changed = replace(evidence, evidence_reference="another-run")
    assert changed.evidence_reference == "another-run"
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        replace(evidence, completeness="COMPLETE")


def test_protocols_reject_low_level_mutated_evidence_state():
    evidence = _evidence()
    object.__setattr__(evidence, "completeness", "COMPLETE")
    assert repr(evidence) == "HMRCIndividualIncomeSourceEvidence([REDACTED])"
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            operation(evidence)


def test_direct_result_constructors_reject_wrong_types_bounds_and_presence():
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomeEmploymentSourceEvidence("A", _IntSubclass(1))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomeEmploymentSourceEvidence("A", _DecimalSubclass("1"))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomeEmploymentSourceEvidence("A", Decimal("1e-20"))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomePensionsBenefitsSourceEvidence(
            jobseekers_allowance=0,
            present_fields=frozenset(),
            absent_fields=frozenset({
                "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
                "jobseekersAllowance", "seissNetPaid",
            }),
        )


def test_benefit_presence_sets_require_exact_documented_string_members():
    documented = {
        "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
        "jobseekersAllowance", "seissNetPaid",
    }
    subclass_name = _StrSubclass("jobseekersAllowance")
    invalid_present = frozenset({subclass_name})
    invalid_absent = frozenset(documented - {"jobseekersAllowance"})
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomePensionsBenefitsSourceEvidence(
            jobseekers_allowance=0,
            present_fields=invalid_present,
            absent_fields=invalid_absent,
        )
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomePensionsBenefitsSourceEvidence(
            present_fields=frozenset(),
            absent_fields=frozenset(
                _StrSubclass(name) if name == "jobseekersAllowance" else name
                for name in documented
            ),
        )

    valid = _evidence().pensions_benefits
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        replace(
            valid,
            absent_fields=frozenset(
                _StrSubclass(name) if name == "jobseekersAllowance" else name
                for name in valid.absent_fields
            ),
        )

    damaged = copy.copy(valid)
    object.__setattr__(
        damaged,
        "absent_fields",
        frozenset(
            _StrSubclass(name) if name == "jobseekersAllowance" else name
            for name in valid.absent_fields
        ),
    )
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            operation(damaged)


def test_unknown_values_are_never_traversed_and_unknown_name_limits_apply():
    source = _observation(payload=_payload(
        employments=[{"employerPayeReference": "A", "payFromEmployment": 1, "future": _Hostile()}],
        benefits={"futureBenefit": _Hostile()},
        futureTop=_Hostile(),
    ))
    evidence = _evidence(observation=source)
    assert evidence.unknown_names == frozenset({"futureTop"})
    too_many = frozenset(f"future{i}" for i in range(33))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        replace(evidence, unknown_names=too_many)


def test_builder_module_helper_and_callable_metadata_rebinding_cannot_promote_invalid_source(monkeypatch):
    module = importlib.import_module(
        "reserved.providers.hmrc_individual_income_source_evidence"
    )
    builder = build_hmrc_individual_income_source_evidence
    invalid = object.__new__(IndividualIncomeAnnualSummaryObservation)
    attack = lambda value: value
    for name in (
        "validate_individual_income_annual_summary_observation",
        "_evidence_reference", "_observed_at", "_digest",
    ):
        monkeypatch.setattr(module, name, attack)
    assert builder.__defaults__ is None and builder.__kwdefaults__ is None
    monkeypatch.setattr(builder, "__defaults__", (attack,))
    monkeypatch.setattr(builder, "__kwdefaults__", {"validator": attack})
    monkeypatch.setitem(builder.__dict__, "validator", attack)
    monkeypatch.setitem(builder.__dict__, "__wrapped__", attack)
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        builder(invalid, evidence_reference="run", observed_at=NOW)


def test_source_boundary_snapshots_constants_types_regex_and_primitives(monkeypatch):
    module = importlib.import_module(
        "reserved.providers.hmrc_individual_income_source_evidence"
    )
    builder = build_hmrc_individual_income_source_evidence
    source = _observation()

    class _AlwaysMatches:
        @staticmethod
        def fullmatch(value):
            return object()

    monkeypatch.setattr(module, "HMRC_INDIVIDUAL_INCOME_API", "attacker-api")
    monkeypatch.setattr(module, "HMRC_INDIVIDUAL_INCOME_API_VERSION", "9.9")
    monkeypatch.setattr(module, "HMRC_INDIVIDUAL_INCOME_COMPLETENESS", "COMPLETE")
    monkeypatch.setattr(module, "datetime", _DatetimeSubclass)
    monkeypatch.setattr(module, "timezone", _CustomTimezone)
    monkeypatch.setattr(module, "Decimal", _DecimalSubclass)
    monkeypatch.setattr(module, "int", _IntSubclass, raising=False)
    monkeypatch.setattr(module, "_SHA256_RE", _AlwaysMatches())
    monkeypatch.setattr(module, "_TAX_YEAR_RE", _AlwaysMatches())
    monkeypatch.setattr(module, "_UNSET", object())
    monkeypatch.setattr(module, "type", lambda value: object, raising=False)
    monkeypatch.setattr(module, "len", lambda value: 0, raising=False)
    monkeypatch.setattr(module, "set", lambda *args: set(), raising=False)
    monkeypatch.setattr(module, "any", lambda values: False, raising=False)
    monkeypatch.setattr(module, "enumerate", lambda values: (), raising=False)
    for name in ("str", "tuple", "dict", "frozenset", "bool"):
        monkeypatch.setattr(module, name, object, raising=False)

    evidence = builder(source, evidence_reference="run", observed_at=NOW)
    assert evidence.source_api_name == HMRC_INDIVIDUAL_INCOME_API
    assert evidence.source_api_version == HMRC_INDIVIDUAL_INCOME_API_VERSION
    assert evidence.completeness == HMRC_INDIVIDUAL_INCOME_COMPLETENESS
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        builder(
            source,
            evidence_reference="run",
            observed_at=NOW,
            source_artifact_sha256="not-a-digest",
        )
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        HMRCIndividualIncomeSourceEvidence(
            HMRC_INDIVIDUAL_INCOME_API,
            HMRC_INDIVIDUAL_INCOME_API_VERSION,
            "2023-24",
            (),
            evidence.pensions_benefits,
            "run",
            _DatetimeSubclass(2026, 1, 1, tzinfo=timezone.utc),
        )
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
        IndividualIncomeEmploymentSourceEvidence("A", _DecimalSubclass("1"))


def test_direct_results_and_protocols_ignore_rebound_module_helpers_and_classes(monkeypatch):
    module = importlib.import_module(
        "reserved.providers.hmrc_individual_income_source_evidence"
    )
    evidence = _evidence(source_artifact_sha256="a" * 64)
    original_class = HMRCIndividualIncomeSourceEvidence
    for name in (
        "_fail", "_safe_text", "_source_string", "_unknown_names", "_number",
        "_observed_at", "_digest", "_exact_state", "_restore_evidence",
    ):
        monkeypatch.setattr(module, name, lambda value, *args, **kwargs: value)
    assert copy.copy(evidence) is evidence
    assert copy.deepcopy(evidence) is evidence
    assert evidence.source_artifact_sha256 == "a" * 64
    rebuilt = pickle.loads(pickle.dumps(evidence))
    assert type(rebuilt) is original_class and rebuilt == evidence
    assert replace(evidence, evidence_reference="next").evidence_reference == "next"

    monkeypatch.setattr(module, "HMRCIndividualIncomeSourceEvidence", object)
    monkeypatch.setattr(module, "IndividualIncomeEmploymentSourceEvidence", object)
    monkeypatch.setattr(module, "IndividualIncomePensionsBenefitsSourceEvidence", object)
    assert copy.copy(evidence) is evidence
    assert replace(evidence, evidence_reference="next").evidence_reference == "next"
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(evidence)

    damaged = copy.copy(evidence)
    object.__setattr__(damaged, "completeness", "COMPLETE")
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            operation(damaged)


def test_builder_rejects_positional_metadata_missing_and_extra_options():
    source = _observation()
    for args, kwargs in (
        (("run", NOW), {}),
        ((), {"observed_at": NOW}),
        ((), {"evidence_reference": "run"}),
        ((), {"evidence_reference": "run", "observed_at": NOW, "extra": True}),
    ):
        with pytest.raises(HMRCIndividualIncomeSourceEvidenceError):
            build_hmrc_individual_income_source_evidence(source, *args, **kwargs)


def test_errors_and_repr_never_echo_sensitive_values():
    source = _observation(payload=_payload(
        employments=[{"employerPayeReference": "SECRET-EMPLOYER", "payFromEmployment": 999999}]
    ))
    with pytest.raises(HMRCIndividualIncomeSourceEvidenceError) as exc:
        _evidence(observation=source, evidence_reference="SECRET-RUN\n")
    message = str(exc.value)
    for secret in (UTR, "SECRET-EMPLOYER", "999999", "SECRET-RUN"):
        assert secret not in message
    assert "SECRET" not in repr(_evidence(observation=source))


def test_no_transport_persistence_canonical_customer_or_tax_surface():
    module = importlib.import_module(
        "reserved.providers.hmrc_individual_income_source_evidence"
    )
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = (
        "flask", "requests", "httpx", "urllib", "reserved.database",
        "reserved.web", "reserved.api", "reserved.engines", "reserved.auth",
        "reserved.providers.oauth", "reserved.providers.payments",
    )
    assert not any(name.startswith(forbidden) for name in imported)
    evidence = _evidence()
    forbidden_fields = {
        "canonical", "customer", "liability", "cash", "currency", "join",
        "identity", "aggregate", "total", "current_income", "provider_call",
    }
    assert forbidden_fields.isdisjoint(evidence.__dataclass_fields__)


def test_public_surface_is_narrow():
    module = importlib.import_module(
        "reserved.providers.hmrc_individual_income_source_evidence"
    )
    assert module.__all__ == (
        "RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH",
        "HMRCIndividualIncomeSourceEvidenceError",
        "IndividualIncomeEmploymentSourceEvidence",
        "IndividualIncomePensionsBenefitsSourceEvidence",
        "HMRCIndividualIncomeSourceEvidence",
        "build_hmrc_individual_income_source_evidence",
    )
