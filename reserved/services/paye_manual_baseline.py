"""Ephemeral manual PAYE capture/review; no annual calculation or persistence."""
from datetime import date
import re
from uuid import uuid4

from reserved.engines.paye_evidence_capture import (
    CaptureSource, PayeEvidenceCapture, PayFrequency, PensionTreatment,
    normalise_paye_evidence,
)
from reserved.engines.paye_reconciliation import Completeness, EvidenceKind, EvidenceRepresentation
from reserved.tax_year_context import resolve_tax_year


FIELDS = frozenset({"gross_pay_to_date", "tax_paid_to_date", "tax_code", "pay_frequency",
                    "pension_treatment", "effective_through", "confirmation"})


def review_manual_baseline(values, *, tax_year, observed_on):
    """Admit exact form strings and return only an explicit own-field review."""
    if type(values) is not dict or set(values) - FIELDS:
        raise ValueError("Unsupported fields")
    if any(type(value) is not str or len(value) > 64 for value in values.values()):
        raise ValueError("Invalid field")
    if values.get("confirmation") != "yes":
        raise ValueError("Confirmation required")
    year = resolve_tax_year(context_tax_year=tax_year)
    if year is None or re.fullmatch(r"[0-9]{4}/[0-9]{2}", year) is None:
        raise ValueError("Unsupported tax year")
    effective_text = values.get("effective_through", "")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", effective_text) is None:
        raise ValueError("Effective date required")
    effective = date.fromisoformat(effective_text)
    if type(observed_on) is not date or effective > observed_on:
        raise ValueError("Future effective date")
    money = {}
    for name in ("gross_pay_to_date", "tax_paid_to_date"):
        raw = values.get(name, "")
        if raw and re.fullmatch(r"(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,2})?", raw) is None:
            raise ValueError("Invalid amount")
        money[name] = raw or None
    capture = PayeEvidenceCapture(
        source=CaptureSource.MANUAL, evidence_id="manual-" + uuid4().hex,
        employment_id="ephemeral-" + uuid4().hex, tax_year=year.replace("/", "-"),
        gross_pay_to_date=money["gross_pay_to_date"], tax_paid_to_date=money["tax_paid_to_date"],
        tax_code=values.get("tax_code") or None,
        pay_frequency=PayFrequency(values.get("pay_frequency") or "unknown"),
        pension_treatment=PensionTreatment(values.get("pension_treatment") or "unknown"),
        effective_through=effective, observed_on=observed_on,
    )
    evidence = normalise_paye_evidence(capture)
    if (evidence.kind is not EvidenceKind.MANUAL
            or evidence.representation is not EvidenceRepresentation.EMPLOYMENT_CUMULATIVE
            or evidence.completeness is not Completeness.PARTIAL):
        raise ValueError("Unexpected evidence classification")
    amount = lambda value: "Unknown" if value is None else "£" + format(value, ".2f")
    return (
        ("Tax year", year),
        ("Cumulative gross pay", amount(evidence.gross_pay_to_date)),
        ("Cumulative tax deducted", amount(evidence.tax_paid_to_date)),
        ("Tax code", evidence.tax_code or "Unknown"),
        # The normalizer intentionally does not retain these two capture fields.
        ("Pay frequency", capture.pay_frequency.value.replace("_", " ").capitalize()),
        ("Pension treatment", capture.pension_treatment.value.replace("_", " ").capitalize()),
        ("Figures effective through", evidence.effective_through.isoformat()),
        ("Entered and confirmed on", evidence.observed_on.isoformat()),
        ("Source", "Manual — information you supplied"),
        ("Representation", "One employment's cumulative figures"),
        ("Evidence status", "Partial"),
    )
