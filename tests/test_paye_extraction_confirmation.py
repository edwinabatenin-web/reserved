"""Adversarial tests for the S2A extraction-confirmation contract.

These are independently derived synthetic tests. They exercise only the public
boundary and its redaction/immutability properties. No document, network,
provider, credential, or production datum is used.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
import copy
import inspect
import pickle
import re

import pytest

from reserved.engines.paye_extraction_confirmation import (
    Decision,
    Disposition,
    FieldDecision,
    FieldName,
    PayeExtractionCandidate,
    PayeExtractionConfirmation,
    candidate_digest,
    confirm_paye_extraction,
)
from reserved.engines.paye_evidence_capture import (
    PayFrequency,
    PensionTreatment,
    SourceDocumentType,
    normalise_paye_evidence,
)
from reserved.engines.paye_reconciliation import (
    Completeness,
    EvidenceKind,
    EvidenceRepresentation,
    reconcile_paye,
)


AS_OF = date(2026, 8, 20)
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


def candidate(**changes):
    values = dict(
        candidate_id="cand-1",
        document_id="doc-1",
        evidence_id="ev-1",
        document_type=SourceDocumentType.PAYSLIP,
        supersedes_evidence_id=None,
        tax_year="2026-27",
        employment_id="emp-A",
        gross_pay_to_date="12345.67",
        tax_paid_to_date="2345.60",
        tax_code="1257L",
        pay_frequency=PayFrequency.MONTHLY,
        pension_treatment=PensionTreatment.UNKNOWN,
        effective_through=date(2026, 8, 18),
        observed_on=AS_OF,
    )
    values.update(changes)
    return PayeExtractionCandidate(**values)


def all_accept():
    return tuple(FieldDecision(f, Decision.ACCEPT) for f in FieldName)


def flip(decisions, field, value):
    return tuple(
        FieldDecision(d.field, Decision.CORRECT, value) if d.field is field else d
        for d in decisions
    )


def confirm(c, decisions=None, confirmation_id="conf-1", **kwargs):
    return confirm_paye_extraction(
        c, all_accept() if decisions is None else decisions, confirmation_id, **kwargs
    )


# ── Hostile objects whose dunder hooks raise ──────────────────────────────────

class Hostile:
    def __str__(self):
        raise RuntimeError("str hook invoked")

    def __repr__(self):
        raise RuntimeError("repr hook invoked")

    def __eq__(self, other):
        raise RuntimeError("eq hook invoked")

    def __hash__(self):
        raise RuntimeError("hash hook invoked")

    def __iter__(self):
        raise RuntimeError("iter hook invoked")

    def __bool__(self):
        raise RuntimeError("bool hook invoked")

    def __float__(self):
        raise RuntimeError("float hook invoked")

    def __int__(self):
        raise RuntimeError("int hook invoked")


class HostileStr(str):
    def __str__(self):
        raise RuntimeError("str hook invoked")


class HostileDecimal(Decimal):
    def __str__(self):
        raise RuntimeError("str hook invoked")


# ── Digest stability, separation, and coverage ────────────────────────────────

def test_candidate_digest_is_stable_lowercase_sha256():
    first = candidate()
    second = candidate()
    assert first == second
    assert candidate_digest(first) == candidate_digest(second)
    assert _DIGEST_RE.fullmatch(candidate_digest(first))


def test_candidate_and_confirmation_domains_are_separated():
    result = confirm(candidate())
    assert _DIGEST_RE.fullmatch(result.candidate_digest)
    assert _DIGEST_RE.fullmatch(result.confirmation_digest)
    assert result.candidate_digest != result.confirmation_digest


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", "cand-2"),
        ("document_id", "doc-2"),
        ("evidence_id", "ev-2"),
        ("supersedes_evidence_id", "ev-0"),
        ("tax_year", "2025-26"),
        ("employment_id", "emp-B"),
        ("gross_pay_to_date", "12345.68"),
        ("tax_paid_to_date", "2345.61"),
        ("tax_code", "1258L"),
        ("pay_frequency", PayFrequency.WEEKLY),
        ("pension_treatment", PensionTreatment.NONE),
        ("effective_through", date(2026, 8, 19)),
        ("observed_on", date(2026, 8, 21)),
    ],
)
def test_candidate_digest_changes_for_every_retained_field(field, value):
    base = candidate()
    changed = replace(base, **{field: value})
    assert candidate_digest(base) != candidate_digest(changed)


def test_candidate_digest_preserves_missing_versus_exact_zero():
    missing = candidate(gross_pay_to_date=None, tax_paid_to_date=None, tax_code=None)
    zero = candidate(gross_pay_to_date="0.00", tax_paid_to_date=0, tax_code="0T")
    assert candidate_digest(missing) != candidate_digest(zero)
    assert missing.gross_pay_to_date is None
    assert zero.gross_pay_to_date == Decimal("0.00")
    assert zero.tax_paid_to_date == Decimal("0.00")


def test_candidate_digest_is_unaffected_by_confirmation_only_changes():
    c = candidate()
    first = confirm(c, all_accept(), "conf-1")
    second = confirm(c, flip(all_accept(), FieldName.TAX_CODE, "1258L"), "conf-2")
    assert first.candidate_digest == second.candidate_digest == candidate_digest(c)
    assert first.confirmation_digest != second.confirmation_digest


@pytest.mark.parametrize("field", list(FieldName))
def test_confirmation_digest_changes_on_accept_correct_flip(field):
    c = candidate()
    base = confirm(c, all_accept(), "conf-1")
    corrected = confirm(c, flip(all_accept(), field, getattr(c, field.value)), "conf-1")
    assert base.confirmation_digest != corrected.confirmation_digest
    assert base.candidate_digest == corrected.candidate_digest


def test_confirmation_digest_changes_on_corrected_value_change():
    c = candidate()
    first = confirm(c, flip(all_accept(), FieldName.GROSS_PAY_TO_DATE, "100.00"))
    second = confirm(c, flip(all_accept(), FieldName.GROSS_PAY_TO_DATE, "200.00"))
    assert first.confirmation_digest != second.confirmation_digest
    assert first.candidate_digest == second.candidate_digest


def test_confirmation_digest_changes_on_confirmation_id_change():
    c = candidate()
    assert confirm(c, all_accept(), "conf-1").confirmation_digest != confirm(
        c, all_accept(), "conf-2"
    ).confirmation_digest


def test_confirmation_digest_binds_candidate_digest():
    first = confirm(candidate(evidence_id="ev-1"))
    second = confirm(candidate(evidence_id="ev-2"))
    assert first.candidate_digest != second.candidate_digest
    assert first.confirmation_digest != second.confirmation_digest


def test_alternate_disposition_fails_closed():
    good = confirm(candidate())
    with pytest.raises(TypeError):
        PayeExtractionConfirmation(
            candidate_digest=good.candidate_digest,
            confirmation_digest=good.confirmation_digest,
            confirmation_id="conf-1",
            disposition="deleted",
            capture=good.capture,
        )
    assert not hasattr(Disposition, "DELETED")


# ── Exact type/date/enum behaviour and hostile rejection ──────────────────────

def test_candidate_normalises_money_and_preserves_exact_types():
    c = candidate(gross_pay_to_date="12345.6", tax_paid_to_date=42)
    assert type(c.gross_pay_to_date) is Decimal
    assert c.gross_pay_to_date == Decimal("12345.60")
    assert c.tax_paid_to_date == Decimal("42.00")
    assert type(c.effective_through) is date
    assert type(c.pay_frequency) is PayFrequency


@pytest.mark.parametrize("value", [True, False, 1.2, float("nan"), float("inf"), -1, "1.001"])
def test_candidate_rejects_bool_float_and_ambiguous_money(value):
    with pytest.raises((TypeError, ValueError)):
        candidate(gross_pay_to_date=value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("pay_frequency", "monthly"),
        ("pension_treatment", "unknown"),
        ("document_type", "payslip"),
        ("effective_through", "2026-08-18"),
        ("observed_on", "2026-08-20"),
    ],
)
def test_candidate_rejects_wrong_runtime_enum_and_date_types(field, value):
    with pytest.raises(TypeError):
        candidate(**{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", HostileStr("cand-1")),
        ("document_id", HostileStr("doc-1")),
        ("evidence_id", HostileStr("ev-1")),
        ("employment_id", HostileStr("emp-A")),
        ("gross_pay_to_date", HostileDecimal("1.00")),
        ("tax_code", HostileStr("1257L")),
    ],
)
def test_candidate_rejects_hostile_subclasses(field, value):
    with pytest.raises((TypeError, ValueError)):
        candidate(**{field: value})


def test_candidate_rejects_hostile_object_without_invoking_hooks():
    with pytest.raises(TypeError):
        candidate(gross_pay_to_date=Hostile())


def test_correction_rejects_hostile_object_without_invoking_hooks():
    with pytest.raises(TypeError):
        FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, Hostile())


@pytest.mark.parametrize("field", list(FieldName))
@pytest.mark.parametrize("value", [True, 1.2, Hostile()])
def test_correction_rejects_bool_float_and_hostile_values(field, value):
    with pytest.raises((TypeError, ValueError)):
        FieldDecision(field, Decision.CORRECT, value)


# ── Exactly one explicit decision per confirmable field ───────────────────────

def test_exactly_one_decision_per_field_is_required():
    c = candidate()
    for field in FieldName:
        missing = tuple(d for d in all_accept() if d.field is not field)
        with pytest.raises(ValueError, match="exactly one"):
            confirm(c, missing)


def test_duplicate_decision_fails_closed():
    c = candidate()
    duplicated = all_accept() + (FieldDecision(FieldName.TAX_YEAR, Decision.ACCEPT),)
    with pytest.raises(ValueError, match="duplicate"):
        confirm(c, duplicated)


def test_unknown_decision_fails_closed():
    c = candidate()
    with pytest.raises(ValueError):
        FieldName("evidence_id")
    with pytest.raises(TypeError):
        FieldDecision("evidence_id", Decision.ACCEPT)
    with pytest.raises(TypeError):
        confirm(c, (Hostile(),))


def test_non_tuple_decisions_fail_closed():
    c = candidate()
    with pytest.raises(TypeError):
        confirm(c, list(all_accept()))
    with pytest.raises(TypeError):
        confirm(c, Hostile())


# ── Identity/coherence: splicing and mismatches fail closed ───────────────────

def test_supplied_candidate_digest_mismatch_fails_closed():
    c = candidate()
    with pytest.raises(ValueError, match="does not match"):
        confirm(c, candidate_digest="0" * 64)
    with pytest.raises(ValueError):
        confirm(c, candidate_digest="not-a-digest")


def test_effective_through_outside_tax_year_fails_closed():
    c = candidate(tax_year="2026-27", effective_through=date(2025, 5, 1))
    with pytest.raises(ValueError, match="failed validation"):
        confirm(c)


def test_observed_on_before_effective_through_fails_closed():
    c = candidate(effective_through=date(2026, 8, 18), observed_on=date(2026, 8, 17))
    with pytest.raises(ValueError, match="failed validation"):
        confirm(c)


def test_supersedes_self_fails_closed():
    c = candidate(evidence_id="ev-1", supersedes_evidence_id="ev-1")
    with pytest.raises(ValueError, match="failed validation"):
        confirm(c)


def test_corrected_cross_field_mismatch_fails_closed():
    c = candidate()
    bad_tax_year = flip(all_accept(), FieldName.TAX_YEAR, "2025-26")
    with pytest.raises(ValueError, match="failed validation"):
        confirm(c, bad_tax_year)


# ── P45 and P60 fail closed ───────────────────────────────────────────────────

@pytest.mark.parametrize("document_type", [SourceDocumentType.P45, SourceDocumentType.P60])
def test_p45_and_p60_fail_closed(document_type):
    with pytest.raises(ValueError, match="payslip"):
        candidate(document_type=document_type)


# ── Replay honesty without claiming storage ───────────────────────────────────

def test_consumed_digests_must_be_exact_frozenset():
    c = candidate()
    with pytest.raises(TypeError):
        confirm(c, consumed_candidate_digests={"a" * 64})
    with pytest.raises(TypeError):
        confirm(c, consumed_candidate_digests=["a" * 64])


@pytest.mark.parametrize("bad", ["abc", "A" * 64, "0" * 63, "0" * 65, 123, None])
def test_consumed_digests_reject_malformed_members(bad):
    c = candidate()
    with pytest.raises(ValueError, match="lowercase hexadecimal SHA-256"):
        confirm(c, consumed_candidate_digests=frozenset({bad}))


def test_consumed_digest_rejects_current_candidate_reuse():
    c = candidate()
    digest = candidate_digest(c)
    with pytest.raises(ValueError, match="already been consumed"):
        confirm(c, consumed_candidate_digests=frozenset({digest}))


def test_consumed_digest_accepts_distinct_prior_digest():
    c = candidate()
    assert confirm(c, consumed_candidate_digests=frozenset({"0" * 64})).candidate_digest == candidate_digest(c)


# ── Immutability, redaction, and non-echoing errors ───────────────────────────

def test_result_and_candidate_are_immutable():
    result = confirm(candidate())
    c = candidate()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.confirmation_id = "changed"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        c.gross_pay_to_date = Decimal("1.00")


def test_repr_never_echoes_identifiers_values_or_digests():
    result = confirm(candidate(tax_code="SENSITIVE-CODE"))
    rendered = repr(result)
    for secret in (
        "cand-1", "doc-1", "ev-1", "emp-A", "conf-1",
        "SENSITIVE-CODE", "12345.67", "2345.60", "1257L",
        result.candidate_digest, result.confirmation_digest,
    ):
        assert secret not in rendered

    c = candidate(tax_code="SENSITIVE-CODE")
    cand_rendered = repr(c)
    for secret in ("SENSITIVE-CODE", "12345.67", "cand-1", "ev-1", "emp-A"):
        assert secret not in cand_rendered


def test_field_decision_repr_never_echoes_corrected_value():
    rendered = repr(FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, "999.99"))
    assert "999.99" not in rendered
    assert "gross_pay_to_date" in rendered
    assert "correct" in rendered


def test_errors_never_echo_source_values():
    c = candidate()
    with pytest.raises(ValueError) as exc_info:
        confirm(c, flip(all_accept(), FieldName.GROSS_PAY_TO_DATE, "SENSITIVE-AMOUNT"))
    assert "SENSITIVE-AMOUNT" not in str(exc_info.value)


def test_candidate_digest_requires_exact_candidate_type():
    with pytest.raises(TypeError):
        candidate_digest({"candidate_id": "x"})


# ── No forbidden content or I/O surface ───────────────────────────────────────

@pytest.mark.parametrize(
    "forbidden",
    [
        "raw_document", "document_bytes", "document_text", "ocr_text",
        "filesystem_path", "nino", "bank_account", "provider_account",
        "credentials", "token", "metadata",
    ],
)
def test_forbidden_content_is_not_accepted_or_exposed(forbidden):
    c = candidate()
    result = confirm(c)
    with pytest.raises(TypeError):
        candidate(**{forbidden: "sensitive"})
    assert not hasattr(c, forbidden)
    assert not hasattr(result, forbidden)


def test_no_deletion_or_io_attributes_are_exposed():
    result = confirm(candidate())
    assert result.disposition is Disposition.SECURE_DELETION_REQUIRED
    assert result.disposition.value == "secure_deletion_required"
    assert result.secure_deletion_required is True
    assert not hasattr(result, "deleted")
    for name in ("delete", "unlink", "remove", "open", "write", "persist", "upload"):
        assert not callable(getattr(result, name, None))


def test_module_has_no_io_or_provider_surface():
    import reserved.engines.paye_extraction_confirmation as module

    source = inspect.getsource(module)
    for forbidden in (
        "import os", "import sys", "import subprocess", "import socket",
        "import logging", "import shutil", "import pathlib", "import tempfile",
        "import io", "import requests", "import urllib", "import http",
        "os.", "sys.", "subprocess.", "socket.", "logging.", "shutil.",
        "pathlib.", "requests.", "urllib.", "http.", "open(", ".unlink(",
        ".remove(", ".rmdir(", ".mkdir(", ".write(", ".read(", "print(",
        "input(", "time.sleep(", "os.environ",
    ):
        assert forbidden not in source

    for name in ("os", "sys", "subprocess", "socket", "logging", "pathlib", "shutil", "requests"):
        assert not hasattr(module, name)


# ── S1 and reconciliation compatibility ───────────────────────────────────────

def test_output_normalises_to_partial_document_employment_cumulative():
    result = confirm(candidate())
    item = normalise_paye_evidence(result.capture)
    assert item.kind is EvidenceKind.DOCUMENT
    assert item.representation is EvidenceRepresentation.EMPLOYMENT_CUMULATIVE
    assert item.completeness is Completeness.PARTIAL
    assert item.evidence_id == "ev-1"
    assert item.employment_id == "emp-A"
    assert item.effective_through == date(2026, 8, 18)
    assert item.observed_on == AS_OF
    assert result.capture.source.value == "source_document"
    assert result.capture.document_type is SourceDocumentType.PAYSLIP


def test_output_remains_compatible_with_reconciliation():
    result = confirm(candidate())
    item = normalise_paye_evidence(result.capture)
    reconciled = reconcile_paye("6000", [item], tax_year="2026-27", as_of=AS_OF)
    assert reconciled.tax_paid_to_date == Decimal("2345.60")
    assert reconciled.selected_kind is EvidenceKind.DOCUMENT


# ── Defect 1: confirmation result has no public forging/splicing boundary ─────

def test_confirmation_cannot_be_constructed_directly():
    good = confirm(candidate())
    with pytest.raises(TypeError, match="cannot be constructed directly"):
        PayeExtractionConfirmation(
            candidate_digest=good.candidate_digest,
            confirmation_digest=good.confirmation_digest,
            confirmation_id=good.confirmation_id,
            disposition=good.disposition,
            capture=good.capture,
        )


def test_confirmation_replace_cannot_forge_or_splice():
    good = confirm(candidate(evidence_id="ev-1"))
    other = confirm(candidate(evidence_id="ev-2"))
    with pytest.raises(TypeError):
        replace(good)
    with pytest.raises((TypeError, ValueError)):
        replace(good, capture=other.capture)
    with pytest.raises((TypeError, ValueError)):
        replace(good, disposition=Disposition.SECURE_DELETION_REQUIRED)


def test_confirmation_copy_and_deepcopy_return_same_instance():
    good = confirm(candidate())
    assert copy.copy(good) is good
    assert copy.deepcopy(good) is good


def test_confirmation_cannot_be_pickled():
    good = confirm(candidate())
    with pytest.raises(TypeError):
        pickle.dumps(good)


def test_confirmation_public_boundary_rejects_spliced_state():
    first = confirm(candidate(evidence_id="ev-1"))
    other = confirm(candidate(evidence_id="ev-2"))
    with pytest.raises(TypeError):
        PayeExtractionConfirmation(
            candidate_digest=first.candidate_digest,
            confirmation_digest=first.confirmation_digest,
            confirmation_id=first.confirmation_id,
            disposition=first.disposition,
            capture=other.capture,
        )
    with pytest.raises((TypeError, ValueError)):
        replace(first, capture=other.capture)


# ── Defect 2: FieldDecision validates and normalises at construction ──────────

def test_accept_decision_cannot_carry_a_corrected_value():
    for value in ("1257L", Decimal("1.00"), None):
        with pytest.raises(ValueError):
            FieldDecision(FieldName.TAX_CODE, Decision.ACCEPT, value)


def test_correct_decision_requires_a_corrected_value():
    with pytest.raises(ValueError):
        FieldDecision(FieldName.TAX_CODE, Decision.CORRECT)


def test_correction_normalises_corrected_value_at_construction():
    gross = FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, "999.9")
    assert type(gross.corrected_value) is Decimal
    assert gross.corrected_value == Decimal("999.90")

    tax_paid = FieldDecision(FieldName.TAX_PAID_TO_DATE, Decision.CORRECT, 42)
    assert type(tax_paid.corrected_value) is Decimal
    assert tax_paid.corrected_value == Decimal("42.00")


def test_correction_rejects_hostile_subclass_at_construction():
    with pytest.raises(TypeError):
        FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, HostileDecimal("1.00"))
    with pytest.raises(ValueError):
        FieldDecision(FieldName.TAX_CODE, Decision.CORRECT, HostileStr("1257L"))


# ── Defect 3: ASCII tax years and Reserved defensive numeric bounds ───────────

_NON_ASCII_TAX_YEARS = ["٢٠٢٦-٢٧", "２０２６-２７"]


@pytest.mark.parametrize("tax_year", _NON_ASCII_TAX_YEARS)
def test_candidate_rejects_non_ascii_digit_tax_years(tax_year):
    with pytest.raises(ValueError, match="ASCII YYYY-YY"):
        candidate(tax_year=tax_year)


@pytest.mark.parametrize("tax_year", _NON_ASCII_TAX_YEARS)
def test_correction_rejects_non_ascii_digit_tax_years(tax_year):
    with pytest.raises(ValueError, match="ASCII YYYY-YY"):
        FieldDecision(FieldName.TAX_YEAR, Decision.CORRECT, tax_year)
    with pytest.raises(ValueError):
        confirm(candidate(), flip(all_accept(), FieldName.TAX_YEAR, tax_year))


def test_extreme_positive_exponent_decimal_rejected():
    with pytest.raises(ValueError, match="magnitude bound"):
        candidate(gross_pay_to_date=Decimal("1E+999999999"))
    with pytest.raises(ValueError, match="magnitude bound"):
        FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, Decimal("1E+999999999"))


def test_oversized_integer_rejected():
    with pytest.raises(ValueError, match="magnitude bound"):
        candidate(gross_pay_to_date=10**40)
    with pytest.raises(ValueError, match="magnitude bound"):
        FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, 10**40)


def test_oversized_numeric_string_rejected():
    with pytest.raises(ValueError, match="length bound"):
        candidate(gross_pay_to_date="9" * 1000)
    with pytest.raises(ValueError, match="length bound"):
        FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, "9" * 1000)


def test_exact_accepted_boundary_amounts():
    for value in (
        Decimal("1000000000000000000.00"),
        1_000_000_000_000_000_000,
        "1000000000000000000.00",
    ):
        c = candidate(gross_pay_to_date=value)
        assert c.gross_pay_to_date == Decimal("1000000000000000000.00")


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1000000000000000000.01"),
        1_000_000_000_000_000_001,
        "1000000000000000000.01",
    ],
)
def test_just_over_bound_amounts_rejected(value):
    with pytest.raises(ValueError, match="magnitude bound"):
        candidate(gross_pay_to_date=value)


def test_over_limit_consumed_digests_rejected():
    c = candidate()
    over_limit = frozenset(f"{i:064x}" for i in range(10_001))
    with pytest.raises(ValueError, match="maximum count"):
        confirm(c, consumed_candidate_digests=over_limit)


def test_new_boundary_errors_never_echo_source_values():
    cases = [
        (lambda: candidate(tax_year="٢٠٢٦-٢٧"), "٢٠٢٦-٢٧"),
        (lambda: candidate(gross_pay_to_date=Decimal("1E+999999999")), "1E+999999999"),
        (lambda: candidate(gross_pay_to_date=10**40), str(10**40)),
        (lambda: candidate(gross_pay_to_date="9" * 1000), "9" * 1000),
        (lambda: FieldDecision(FieldName.GROSS_PAY_TO_DATE, Decision.CORRECT, "9" * 1000), "9" * 1000),
    ]
    for factory, secret in cases:
        with pytest.raises((TypeError, ValueError)) as exc_info:
            factory()
        assert secret not in str(exc_info.value)
