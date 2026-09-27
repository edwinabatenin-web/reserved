"""Authenticated manual PAYE orchestration over minimised structured evidence.

This is deliberately not a payroll calculator. It admits customer-confirmed,
employment-scoped cumulative facts, makes replacement and deletion explicit,
and supplies a safe read model for the shared annual-position boundary. It
never accepts a raw payslip, calls HMRC, selects a retention period, or turns
incomplete PAYE evidence into a confirmed underpayment, overpayment or refund.
"""

from __future__ import annotations

from datetime import date
import re
from uuid import uuid4

from reserved.engines.paye_reconciliation import Completeness
from reserved.services.paye_manual_baseline import FIELDS, capture_manual_baseline


_ENTRY_FIELDS = FIELDS | {"employment_slot"}
_SLOTS = frozenset(str(number) for number in range(1, 21))
_PROVENANCE = "customer_confirmed_manual_cumulative_entry"
_EVIDENCE_ID = re.compile(r"paye-manual-[0-9a-f]{32}\Z")


def admit_manual_entry(values: dict, *, tax_year: str, observed_on: date) -> dict:
    """Validate one customer-confirmed, opaque employment-slot entry for storage."""
    if type(values) is not dict or set(values) != _ENTRY_FIELDS:
        raise ValueError("Unsupported PAYE entry fields")
    slot = values.get("employment_slot")
    if type(slot) is not str or slot not in _SLOTS:
        raise ValueError("Choose an employment slot")
    baseline_values = {name: values[name] for name in FIELDS}
    evidence_id = "paye-manual-" + uuid4().hex
    capture, evidence = capture_manual_baseline(
        baseline_values,
        tax_year=tax_year,
        observed_on=observed_on,
        evidence_id=evidence_id,
        employment_id="manual-employment-" + slot,
    )
    if evidence.completeness is not Completeness.PARTIAL:
        raise ValueError("Unexpected PAYE completeness")
    admitted = {
        "tax_year": tax_year,
        "employment_slot": int(slot),
        "evidence_id": evidence_id,
        "source_kind": "customer_confirmed_manual",
        "provenance": _PROVENANCE,
        "gross_to_date": None if evidence.gross_pay_to_date is None else format(evidence.gross_pay_to_date, ".2f"),
        "tax_paid_to_date": None if evidence.tax_paid_to_date is None else format(evidence.tax_paid_to_date, ".2f"),
        "tax_code": evidence.tax_code,
        "pay_frequency": capture.pay_frequency.value,
        "pension_treatment": capture.pension_treatment.value,
        "effective_through": evidence.effective_through.isoformat(),
        "observed_on": evidence.observed_on.isoformat(),
        "completeness": "partial",
    }
    validate_admitted_manual_entry(admitted)
    return admitted


def validate_admitted_manual_entry(value: dict) -> None:
    """Reproduce admission before any structured PAYE record is persisted.

    Storage callers cannot bypass the public form boundary by constructing a
    same-shaped dictionary: fixed provenance, opaque identity, exact enums,
    dates, amounts and the complete canonical representation are rechecked.
    """
    required = {
        "tax_year", "employment_slot", "evidence_id", "source_kind", "provenance",
        "gross_to_date", "tax_paid_to_date", "tax_code", "pay_frequency",
        "pension_treatment", "effective_through", "observed_on", "completeness",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("Invalid admitted PAYE entry shape")
    slot = value.get("employment_slot")
    evidence_id = value.get("evidence_id")
    if type(slot) is not int or not 1 <= slot <= 20:
        raise ValueError("Invalid admitted PAYE employment slot")
    if type(evidence_id) is not str or _EVIDENCE_ID.fullmatch(evidence_id) is None:
        raise ValueError("Invalid admitted PAYE evidence identity")
    if (value.get("source_kind") != "customer_confirmed_manual"
            or value.get("provenance") != _PROVENANCE
            or value.get("completeness") != "partial"):
        raise ValueError("Invalid admitted PAYE provenance")
    try:
        observed_on = date.fromisoformat(value["observed_on"])
    except (TypeError, ValueError):
        raise ValueError("Invalid admitted PAYE observation date") from None
    inverse = {
        "gross_pay_to_date": value["gross_to_date"] or "",
        "tax_paid_to_date": value["tax_paid_to_date"] or "",
        "tax_code": value["tax_code"] or "",
        "pay_frequency": value["pay_frequency"],
        "pension_treatment": value["pension_treatment"],
        "effective_through": value["effective_through"],
        "confirmation": "yes",
    }
    capture, evidence = capture_manual_baseline(
        inverse, tax_year=value["tax_year"], observed_on=observed_on,
        evidence_id=evidence_id, employment_id=f"manual-employment-{slot}",
    )
    canonical = {
        "tax_year": value["tax_year"], "employment_slot": slot,
        "evidence_id": evidence_id, "source_kind": "customer_confirmed_manual",
        "provenance": _PROVENANCE,
        "gross_to_date": None if evidence.gross_pay_to_date is None else format(evidence.gross_pay_to_date, ".2f"),
        "tax_paid_to_date": None if evidence.tax_paid_to_date is None else format(evidence.tax_paid_to_date, ".2f"),
        "tax_code": evidence.tax_code, "pay_frequency": capture.pay_frequency.value,
        "pension_treatment": capture.pension_treatment.value,
        "effective_through": evidence.effective_through.isoformat(),
        "observed_on": evidence.observed_on.isoformat(), "completeness": "partial",
    }
    if value != canonical:
        raise ValueError("PAYE entry is not the canonical admitted record")


def customer_read_model(entries: list[dict], *, as_of: date) -> tuple[dict, ...]:
    """Return safe presentation facts without making a tax or refund determination."""
    if type(as_of) is not date:
        raise TypeError("PAYE read model requires an exact date")
    result = []
    for row in entries:
        if type(row) is not dict:
            raise ValueError("Invalid PAYE stored entry")
        observed = date.fromisoformat(row["observed_on"])
        effective = date.fromisoformat(row["effective_through"])
        gross = row["gross_to_date"]
        tax = row["tax_paid_to_date"]
        result.append({
            "employment_slot": row["employment_slot"],
            "evidence_id": row["evidence_id"],
            "source": "Information you confirmed manually",
            "provenance": row["provenance"],
            "effective_through": effective.isoformat(),
            "observed_on": observed.isoformat(),
            "completeness": "Partial — this does not establish full-year coverage",
            "gross": "Unknown" if gross is None else "£" + gross,
            "tax_paid": "Unknown" if tax is None else "£" + tax,
            "tax_code": row["tax_code"] or "Unknown",
            "state": "needs-update" if (as_of - effective).days > 45 else "current",
            "missing": tuple(name for name, value in (("gross pay", gross), ("tax deducted", tax)) if value is None),
        })
    return tuple(result)


def annual_position_boundary_state(entries: list[dict]) -> str:
    """State the honest bridge condition; never invent an annual liability input."""
    if not entries:
        return "Add at least one confirmed PAYE entry before an annual position can use PAYE evidence."
    if any(row.get("tax_paid_to_date") is None for row in entries):
        return "Some tax-deducted figures are unknown, so PAYE cannot safely contribute a point amount."
    return (
        "Your PAYE evidence is available for the shared annual position when its separate "
        "tax calculation and assurance inputs are available. It is still provisional, not a confirmed tax bill or refund."
    )
