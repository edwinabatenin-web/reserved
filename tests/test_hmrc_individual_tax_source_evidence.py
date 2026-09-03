"""Adversarial offline tests for Individual Tax 1.1 source evidence."""

import ast
import copy
import pickle
import subprocess
import sys
import textwrap
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from pathlib import Path

import pytest

import reserved.providers.hmrc_individual_tax_contract as contract_module
import reserved.providers.hmrc_individual_tax_source_evidence as evidence_module
from reserved.providers.hmrc_individual_tax_contract import (
    HMRCIndividualTaxContractError,
    IndividualTaxAnnualSummaryObservation,
    build_individual_tax_request,
    observe_individual_tax_response,
)
from reserved.providers.hmrc_individual_tax_source_evidence import (
    HMRC_INDIVIDUAL_TAX_API_NAME,
    HMRCIndividualTaxSourceEvidence,
    HMRCIndividualTaxSourceEvidenceError,
    IndividualTaxEmploymentEvidence,
    IndividualTaxPensionsBenefitsEvidence,
    IndividualTaxRefundEvidence,
    build_hmrc_individual_tax_source_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 3, 11, 45, tzinfo=timezone(timedelta(hours=1)))


def _request(utr="0123456789", tax_year="2025-26"):
    return build_individual_tax_request(utr=utr, tax_year=tax_year)


def _payload(*, employments=None, benefits=None, refunds=None, **unknown):
    value = {
        "employments": [] if employments is None else employments,
        "pensionsAnnuitiesAndOtherStateBenefits": {} if benefits is None else benefits,
        "refunds": {} if refunds is None else refunds,
    }
    value.update(unknown)
    return value


def _observation(**payload):
    return observe_individual_tax_response(
        _request(), status_code=200, content_type="application/json",
        payload=_payload(**payload),
    )


def _evidence(observation=None, **overrides):
    values = {"evidence_reference": "run-tax-1", "collected_at": NOW}
    values.update(overrides)
    return build_hmrc_individual_tax_source_evidence(
        _observation() if observation is None else observation, **values
    )


def _direct(**overrides):
    base = _evidence()
    values = {
        "source_api_name": base.source_api_name,
        "source_api_version": base.source_api_version,
        "tax_year": base.tax_year,
        "employments": base.employments,
        "pensions_benefits": base.pensions_benefits,
        "refunds": base.refunds,
        "top_level_unknown_names": base.top_level_unknown_names,
        "evidence_reference": base.evidence_reference,
        "collected_at": base.collected_at,
        "completeness": base.completeness,
        "source_artifact_sha256": base.source_artifact_sha256,
    }
    values.update(overrides)
    return HMRCIndividualTaxSourceEvidence(**values)


class _Hostile:
    def __repr__(self): raise AssertionError("repr touched")
    def __str__(self): raise AssertionError("str touched")
    def __eq__(self, other): raise AssertionError("eq touched")
    def __hash__(self): raise AssertionError("hash touched")
    def __bool__(self): raise AssertionError("bool touched")
    def __iter__(self): raise AssertionError("iter touched")


class _DecimalSubclass(Decimal):
    pass


class _StrSubclass(str):
    pass


class _DatetimeSubclass(datetime):
    pass


class _TimezoneSubclass(tzinfo):
    def utcoffset(self, value): return timedelta(0)
    def dst(self, value): return timedelta(0)


def test_exact_literal_fidelity_order_duplicates_unknowns_and_negative_zero():
    observed = _observation(
        employments=[
            {"employerPayeReference": "267/LS500", "taxTakenOffPay": Decimal("-0.00"), "futureEmployment": _Hostile()},
            {"employerPayeReference": "267/LS500", "taxTakenOffPay": 0},
        ],
        benefits={"otherPensionsAndRetirementAnnuities": Decimal("10.1200"), "futureBenefit": _Hostile()},
        refunds={"taxRefundedOrSetOff": Decimal("-2.50"), "futureRefund": _Hostile()},
        futureTop=_Hostile(),
    )
    result = _evidence(observed)
    assert result.source_api_name == HMRC_INDIVIDUAL_TAX_API_NAME == "Individual Tax"
    assert result.source_api_version == "1.1"
    assert result.tax_year == "2025-26"
    assert [item.employer_paye_reference for item in result.employments] == ["267/LS500", "267/LS500"]
    assert result.employments[0].tax_taken_off_pay.as_tuple() == Decimal("-0.00").as_tuple()
    assert type(result.employments[1].tax_taken_off_pay) is int
    assert result.employments[0].unknown_names == frozenset({"futureEmployment"})
    assert result.pensions_benefits.other_pensions_and_retirement_annuities.as_tuple() == Decimal("10.1200").as_tuple()
    assert result.pensions_benefits.incapacity_benefit is None
    assert result.pensions_benefits.present_fields == frozenset({"otherPensionsAndRetirementAnnuities"})
    assert result.refunds.tax_refunded_or_set_off == Decimal("-2.50")
    assert result.top_level_unknown_names == frozenset({"futureTop"})
    assert result.completeness == "UNVERIFIED"


def test_empty_employments_and_all_omissions_are_valid_but_unverified():
    result = _evidence()
    assert result.employments == ()
    assert result.pensions_benefits.present_fields == frozenset()
    assert result.pensions_benefits.absent_fields == frozenset({"otherPensionsAndRetirementAnnuities", "incapacityBenefit"})
    assert result.refunds.tax_refunded_or_set_off is None
    assert result.completeness == "UNVERIFIED"


@pytest.mark.parametrize("status,payload", [
    (400, {"code": "SA_UTR_INVALID", "message": "secret-message"}),
    (401, {"code": "UNAUTHORIZED", "message": "secret-message"}),
    (404, {"code": "NOT_FOUND", "message": "secret-message"}),
])
def test_all_error_observations_are_rejected(status, payload):
    error = observe_individual_tax_response(
        _request(), status_code=status, content_type="application/json", payload=payload
    )
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(error)


def test_subtype_lookalike_low_level_clone_and_mutation_fail_closed():
    class SummarySubtype(IndividualTaxAnnualSummaryObservation):
        pass
    for bad in (object(), object.__new__(SummarySubtype)):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            _evidence(bad)
    source = _observation(employments=[{"employerPayeReference": "123/A", "taxTakenOffPay": 1}])
    clone = object.__new__(IndividualTaxAnnualSummaryObservation)
    for name, value in vars(source).items():
        object.__setattr__(clone, name, value)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(clone)
    object.__setattr__(source.employments[0], "tax_taken_off_pay", 2)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


def test_cross_year_request_and_binding_substitution_fail_closed():
    source = _observation()
    other = observe_individual_tax_response(
        _request(utr="9876543210", tax_year="2024-25"), status_code=200,
        content_type="application/json", payload=_payload(),
    )
    object.__setattr__(source, "request", other.request)
    object.__setattr__(source, "_request_binding", other._request_binding)
    object.__setattr__(source, "tax_year", other.tax_year)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


def test_same_year_cross_request_identity_substitution_fails_closed():
    source = _observation()
    other = observe_individual_tax_response(
        _request(utr="9876543210", tax_year="2025-26"), status_code=200,
        content_type="application/json", payload=_payload(),
    )
    object.__setattr__(source, "request", other.request)
    object.__setattr__(source, "_request_binding", other._request_binding)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


@pytest.mark.parametrize("replacement", [Decimal("1.0"), 1])
def test_issuance_fingerprint_rejects_equality_equal_numeric_representation_change(replacement):
    source = _observation(
        employments=[{
            "employerPayeReference": "123/A",
            "taxTakenOffPay": Decimal("1.00"),
        }]
    )
    object.__setattr__(source.employments[0], "tax_taken_off_pay", replacement)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


def test_exact_state_rejects_equality_equal_str_subclass_dict_key():
    source = _observation()
    state = vars(source)
    employments = state.pop("employments")
    state[_StrSubclass("employments")] = employments
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


def test_presence_state_rejects_equality_equal_str_subclass_member():
    source = _observation(
        benefits={"incapacityBenefit": Decimal("1.00")}
    )
    object.__setattr__(
        source.pensions_benefits,
        "present_fields",
        frozenset({_StrSubclass("incapacityBenefit")}),
    )
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(source)


def test_evidence_metadata_exact_and_digest_optional():
    assert _evidence().source_artifact_sha256 is None
    digest = "a" * 64
    result = _evidence(source_artifact_sha256=digest)
    assert result.source_artifact_sha256 == digest
    for bad in (None, "A" * 64, "a" * 63, 1, _Hostile()):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            _evidence(source_artifact_sha256=bad)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _evidence(evidence_reference="")


def test_collection_time_requires_exact_aware_fixed_offset_datetime():
    for bad in (
        datetime(2026, 1, 1),
        _DatetimeSubclass(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=_TimezoneSubclass()),
        "2026-01-01T00:00:00Z",
    ):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            _evidence(collected_at=bad)


def test_direct_construction_rejects_fabricated_constants_types_and_numbers():
    for changes in (
        {"source_api_name": "Other"}, {"source_api_version": "9.9"},
        {"completeness": "VERIFIED"}, {"tax_year": "2025/26"},
        {"employments": []}, {"source_artifact_sha256": "bad"},
    ):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            _direct(**changes)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        IndividualTaxEmploymentEvidence("x", _DecimalSubclass("1.00"), frozenset())


def test_frozen_copy_deepcopy_replace_and_pickle_revalidate_and_preserve():
    value = _evidence(source_artifact_sha256="b" * 64)
    assert copy.copy(value) == value
    assert copy.deepcopy(value) == value
    assert pickle.loads(pickle.dumps(value)) == value
    assert replace(value, evidence_reference="next").evidence_reference == "next"
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        replace(value, completeness="VERIFIED")
    with pytest.raises(FrozenInstanceError):
        value.tax_year = "2024-25"


def test_mutated_nested_employment_fails_copy_deepcopy_and_pickle_protocols():
    value = _evidence(
        _observation(employments=[{
            "employerPayeReference": "123/A", "taxTakenOffPay": 1,
        }])
    ).employments[0]
    object.__setattr__(value, "tax_taken_off_pay", True)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            operation(value)


def test_mutated_benefits_and_refunds_fail_all_reconstruction_protocols():
    result = _evidence(
        _observation(
            benefits={"incapacityBenefit": 1},
            refunds={"taxRefundedOrSetOff": 2},
        )
    )
    for value in (result.pensions_benefits, result.refunds):
        object.__setattr__(value, "present_fields", frozenset())
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
                operation(value)


def test_source_evidence_validates_itself_before_copy_and_serialization():
    result = _evidence(
        _observation(employments=[{
            "employerPayeReference": "123/A", "taxTakenOffPay": 1,
        }])
    )
    object.__setattr__(result.employments[0], "tax_taken_off_pay", True)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
            operation(result)


def test_class_validate_rebinding_cannot_bypass_any_result_security_path(monkeypatch):
    for result_type in (
        IndividualTaxEmploymentEvidence,
        IndividualTaxPensionsBenefitsEvidence,
        IndividualTaxRefundEvidence,
        HMRCIndividualTaxSourceEvidence,
    ):
        monkeypatch.setattr(result_type, "_validate", lambda self: None)

    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        IndividualTaxEmploymentEvidence("123/A", True, frozenset())
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        IndividualTaxPensionsBenefitsEvidence(
            1,
            None,
            frozenset(),
            frozenset({
                "otherPensionsAndRetirementAnnuities", "incapacityBenefit",
            }),
            frozenset(),
        )
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        IndividualTaxRefundEvidence(
            1,
            frozenset(),
            frozenset({"taxRefundedOrSetOff"}),
            frozenset(),
        )

    result = _evidence(
        _observation(
            employments=[{
                "employerPayeReference": "123/A", "taxTakenOffPay": 1,
            }],
            benefits={"incapacityBenefit": 1},
            refunds={"taxRefundedOrSetOff": 2},
        )
    )
    object.__setattr__(result.employments[0], "tax_taken_off_pay", True)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _direct(employments=result.employments)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        _direct(source_api_name="Forged")
    for value in (
        result.employments[0],
        result.pensions_benefits,
        result.refunds,
        result,
    ):
        if value is result.pensions_benefits:
            object.__setattr__(value, "present_fields", frozenset())
        if value is result.refunds:
            object.__setattr__(value, "present_fields", frozenset())
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
                operation(value)


def test_repr_and_errors_never_echo_sensitive_values():
    utr = "9876543210"
    observed = observe_individual_tax_response(
        _request(utr=utr), status_code=200, content_type="application/json",
        payload=_payload(employments=[{"employerPayeReference": "SENSITIVE-EMPLOYER", "taxTakenOffPay": 321}]),
    )
    result = _evidence(observed, evidence_reference="SENSITIVE-REFERENCE", source_artifact_sha256="c" * 64)
    combined = repr(result) + repr(result.employments[0]) + repr(pickle.dumps(result))
    assert utr not in combined
    assert "SENSITIVE-EMPLOYER" not in repr(result)
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError) as caught:
        _evidence(observed, evidence_reference="SENSITIVE\x00REFERENCE")
    text = str(caught.value)
    for secret in (utr, "SENSITIVE-EMPLOYER", "SENSITIVE", "321", "c" * 64):
        assert secret not in text


def test_builder_and_contract_validator_have_no_writable_callable_metadata():
    for callable_value in (
        build_hmrc_individual_tax_source_evidence,
        contract_module.validate_individual_tax_annual_summary_observation,
    ):
        for name in ("__dict__", "__defaults__", "__kwdefaults__", "__wrapped__"):
            assert not hasattr(callable_value, name)


def test_closure_sealing_survives_module_constant_type_regex_class_and_helper_rebinding(monkeypatch):
    source = _observation(employments=[{"employerPayeReference": "123/A", "taxTakenOffPay": Decimal("1.20")}])
    original_result_type = HMRCIndividualTaxSourceEvidence
    original_record_type = IndividualTaxEmploymentEvidence
    monkeypatch.setattr(evidence_module, "HMRC_INDIVIDUAL_TAX_API_NAME", "Forged")
    monkeypatch.setattr(evidence_module, "HMRC_INDIVIDUAL_TAX_API_VERSION", "9.9")
    monkeypatch.setattr(evidence_module, "HMRC_INDIVIDUAL_TAX_COMPLETENESS", "VERIFIED")
    monkeypatch.setattr(evidence_module, "datetime", _DatetimeSubclass)
    monkeypatch.setattr(evidence_module, "timezone", _TimezoneSubclass)
    monkeypatch.setattr(evidence_module, "Decimal", _DecimalSubclass)
    monkeypatch.setattr(evidence_module, "int", bool, raising=False)
    monkeypatch.setattr(evidence_module, "re", object())
    monkeypatch.setattr(evidence_module, "HMRCIndividualTaxSourceEvidence", object)
    monkeypatch.setattr(evidence_module, "IndividualTaxEmploymentEvidence", object)
    monkeypatch.setattr(evidence_module, "validate_individual_tax_annual_summary_observation", lambda value: object())
    result = build_hmrc_individual_tax_source_evidence(source, evidence_reference="sealed", collected_at=NOW)
    assert type(result) is original_result_type
    assert type(result.employments[0]) is original_record_type
    assert result.source_api_name == "Individual Tax"
    assert result.source_api_version == "1.1"
    assert result.completeness == "UNVERIFIED"
    with pytest.raises(HMRCIndividualTaxSourceEvidenceError):
        original_record_type("x", _DecimalSubclass("1"), frozenset())


def test_contract_validator_survives_transitive_helper_type_regex_and_method_rebinding(monkeypatch):
    source = _observation(employments=[{"employerPayeReference": "123/A", "taxTakenOffPay": Decimal("1.20")}])
    validator = contract_module.validate_individual_tax_annual_summary_observation
    monkeypatch.setattr(contract_module, "_require_exact_request_intent", lambda value: object())
    monkeypatch.setattr(contract_module, "_ANNUAL_SUMMARY_STATE_KEYS", frozenset())
    monkeypatch.setattr(contract_module, "Decimal", _DecimalSubclass)
    monkeypatch.setattr(contract_module, "int", bool, raising=False)
    monkeypatch.setattr(contract_module, "_TAX_YEAR_RE", object())
    monkeypatch.setattr(contract_module.IndividualTaxAnnualSummaryObservation, "_validate_state", lambda self: None)
    assert validator(source) is source


def test_fresh_process_transitive_module_shadow_regression():
    program = textwrap.dedent(
        """
        from datetime import datetime, timezone
        from decimal import Decimal
        import reserved.providers.hmrc_individual_tax_contract as c
        import reserved.providers.hmrc_individual_tax_source_evidence as e
        request = c.build_individual_tax_request(utr="0123456789", tax_year="2025-26")
        source = c.observe_individual_tax_response(
            request, status_code=200, content_type="application/json",
            payload={
                "employments": [{
                    "employerPayeReference": "267/LS500",
                    "taxTakenOffPay": Decimal("-0.00"),
                }],
                "pensionsAnnuitiesAndOtherStateBenefits": {},
                "refunds": {},
            },
        )
        builder = e.build_hmrc_individual_tax_source_evidence
        validator = c.validate_individual_tax_annual_summary_observation
        result_type = e.HMRCIndividualTaxSourceEvidence
        record_type = e.IndividualTaxEmploymentEvidence
        c._require_exact_request_intent = lambda value: object()
        c._ANNUAL_SUMMARY_STATE_KEYS = frozenset()
        c.Decimal = type("FakeDecimal", (), {})
        c.int = bool
        c._TAX_YEAR_RE = object()
        c.IndividualTaxAnnualSummaryObservation._validate_state = lambda self: None
        e.HMRC_INDIVIDUAL_TAX_API_NAME = "Forged"
        e.HMRC_INDIVIDUAL_TAX_API_VERSION = "9.9"
        e.HMRC_INDIVIDUAL_TAX_COMPLETENESS = "VERIFIED"
        e.datetime = type("FakeDatetime", (), {})
        e.timezone = type("FakeTimezone", (), {})
        e.Decimal = type("FakeDecimal", (), {})
        e.int = bool
        e.re = object()
        e.HMRCIndividualTaxSourceEvidence = object
        e.IndividualTaxEmploymentEvidence = object
        e.validate_individual_tax_annual_summary_observation = lambda value: object()
        assert validator(source) is source
        result = builder(
            source, evidence_reference="fresh-process",
            collected_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
        )
        assert type(result) is result_type
        assert type(result.employments[0]) is record_type
        assert result.source_api_name == "Individual Tax"
        assert result.source_api_version == "1.1"
        assert result.completeness == "UNVERIFIED"
        assert result.employments[0].tax_taken_off_pay.as_tuple() == Decimal("-0.00").as_tuple()
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert completed.returncode == 0, completed.stderr


def test_ast_has_no_transport_persistence_or_product_mapping_surface():
    path = ROOT / "reserved/providers/hmrc_individual_tax_source_evidence.py"
    tree = ast.parse(path.read_text())
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint({"requests", "httpx", "urllib", "socket", "sqlite3", "sqlalchemy", "flask"})
    text = path.read_text()
    for prohibited in ("PayeEvidence", "annual_tax", "cash_obligation", "ProviderSpec", "OAuth", "Authorization"):
        assert prohibited not in text
