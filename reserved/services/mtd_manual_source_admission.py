"""Bounded factual admission for a self-reported, unsaved MTD indication.

No threshold calculation, filing, provider verification or durable identities.
Only the existing captured issuer creates the result handle.
"""
from datetime import date
import re
from uuid import uuid4

from reserved.engines.mtd_readiness import IncomeKind, IncomeSource, MTD_THRESHOLD_RULES
from reserved.services.mtd_scope_indication import MtdScopeCompleteness, present_mtd_scope_indication as _issue


YEARS = ("2024-25", "2025-26")
_MANDATORY_YEARS = {year: MTD_THRESHOLD_RULES[year].mandatory_from_tax_year for year in YEARS}
TRI = ("yes", "no", "unknown")
QUESTIONS = (
    ("source_basis", "Basis of the selected year's figures", ("submitted_return", "records_only", "draft_return", "year_to_date", "unknown")),
    ("return_revision", "Position of that submitted return", ("original_unamended", "amended", "conflicting", "unknown")),
    ("registered_for_sa", "Are you registered for Self Assessment?", TRI),
    ("acting_capacity", "Whose affairs are you describing?", ("own_individual", "representative_or_entity", "unknown")),
    ("relevant_tax_region", "Relevant tax region (this does not establish residence)", ("england", "wales", "northern_ireland", "other", "unknown")),
    ("residence", "Residence circumstances for the selected assessment year", ("ordinary_uk", "non_uk", "dual_split_or_special", "unknown")),
    ("ni_held_before_boundary", "Did you already hold a National Insurance number before the boundary shown for your selected year? Do not enter the number.", TRI),
    ("hmrc_exemption_position", "HMRC exemption position", ("none_known", "granted", "pending", "unclear")),
    ("prior_mtd_position", "Existing or previous MTD position", ("not_previously_enrolled_or_under_an_earlier_requirement", "existing_or_previous_requirement", "unknown")),
    ("all_sources_once", "Have you included all qualifying businesses exactly once?", TRI),
    ("own_shares", "Are all figures your own relevant gross share before expenses?", TRI),
    ("vat_or_special_treatment", "Is VAT basis or special-income treatment unresolved?", TRI),
    ("source_version_conflict", "Is there an unresolved source-version conflict?", TRI),
)
SPECIAL_FACTS = (
    ("sa109", "SA109 residence treatments"), ("sa107", "SA107 trust or estate income"),
    ("averaging_care", "Averaging or qualifying-care relief"),
    ("minister_lloyds", "Minister or Lloyd's pages"),
    ("bpa_mca", "Receiving or transferring Blind Person's Allowance or Married Couple's Allowance"),
    ("representative_exemption", "An existing representative-related exemption"),
)
SCREEN_YEARS = ("2024-25", "2025-26", "2026-27")
ROW_FIELDS = ("kind", "gross_income", "period_start", "period_end", "lifecycle", "amount_basis")
ROW_CHOICES = {
    "kind": ("sole_trade", "uk_property", "foreign_property", "unknown"),
    "lifecycle": ("active_throughout_and_still_continuing", "started_or_ceased", "unknown"),
    "amount_basis": ("own_gross_before_expenses", "whole_joint_or_net", "special_or_uncertain", "unknown"),
}
_ENUMS = {name: choices for name, _, choices in QUESTIONS}
_ENUMS.update({f"{name}_{year}": TRI for year in SCREEN_YEARS for name, _ in SPECIAL_FACTS})
_FIXED = frozenset(_ENUMS) | {"assessment_year", "submitted_on"}
_ROW_KEY = re.compile(r"source_([1-9][0-9]?)_(kind|gross_income|period_start|period_end|lifecycle|amount_basis)\Z")


def _date(value):
    if not value:
        return None
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("Invalid date")
    return date.fromisoformat(value)


def manual_year_metadata(as_of):
    """Get start metadata from accepted rule records, never a duplicate threshold."""
    if type(as_of) is not date:
        raise ValueError("Invalid server date")
    rows = []
    for year in YEARS:
        start_year = int(year[:4])
        mandatory = _MANDATORY_YEARS[year]
        start = date(int(mandatory[:4]), 4, 6)
        rows.append((year, date(start_year, 4, 6), date(start_year + 1, 4, 5), start, min(start, as_of)))
    return tuple(rows)


def admit_manual_mtd(values, *, as_of):
    """Return a genuinely issued handle and whether the manual subset is supported."""
    if type(values) is not dict or any(type(k) is not str or type(v) is not str or len(v) > 100 for k, v in values.items()):
        raise ValueError("Invalid bounded fields")
    row_numbers = set()
    for key in values:
        if key in _FIXED:
            continue
        match = _ROW_KEY.fullmatch(key)
        if match is None:
            raise ValueError("Unsupported field")
        row_numbers.add(int(match[1]))
    for name, choices in _ENUMS.items():
        if values.get(name, "") not in ("",) + choices:
            raise ValueError("Invalid categorical answer")
    year = values.get("assessment_year", "")
    if year and re.fullmatch(r"[0-9]{4}-[0-9]{2}", year) is None:
        raise ValueError("Invalid assessment year")
    metadata = {row[0]: row for row in manual_year_metadata(as_of)}
    period = metadata.get(year)
    submitted = _date(values.get("submitted_on", ""))
    timing = bool(period and submitted and period[2] < submitted <= period[4]
                  and period[2] < as_of and values.get("source_basis") == "submitted_return"
                  and values.get("return_revision") == "original_unamended")
    residence = (values.get("acting_capacity") == "own_individual"
                 and values.get("relevant_tax_region") in ("england", "wales", "northern_ireland")
                 and values.get("residence") == "ordinary_uk"
                 and all(values.get(f"{name}_{screen_year}") == "no"
                         for screen_year in SCREEN_YEARS for name, _ in SPECIAL_FACTS))
    eligibility = (values.get("registered_for_sa") == "yes"
                   and values.get("ni_held_before_boundary") == "yes"
                   and values.get("hmrc_exemption_position") == "none_known")
    continuation = values.get("prior_mtd_position") == "not_previously_enrolled_or_under_an_earlier_requirement"
    inventory = (values.get("all_sources_once") == "yes" and values.get("own_shares") == "yes"
                 and values.get("vat_or_special_treatment") == "no"
                 and values.get("source_version_conflict") == "no"
                 and all(number <= 12 for number in row_numbers))
    sources = []
    property_kinds = set()
    for number in sorted(row_numbers):
        row = {key: values.get(f"source_{number}_{key}", "") for key in ROW_FIELDS}
        if not any(row.values()):
            continue
        for name, choices in ROW_CHOICES.items():
            if row[name] not in ("",) + choices:
                raise ValueError("Invalid source category")
        gross = row["gross_income"]
        if gross and re.fullmatch(r"(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,2})?", gross) is None:
            raise ValueError("Invalid gross amount")
        start, end = _date(row["period_start"]), _date(row["period_end"])
        timing = timing and bool(period and start == period[1] and end == period[2])
        continuation = continuation and row["lifecycle"] == "active_throughout_and_still_continuing"
        known_kind = row["kind"] in ("sole_trade", "uk_property", "foreign_property")
        inventory = inventory and known_kind and bool(gross) and row["amount_basis"] == "own_gross_before_expenses"
        if row["kind"] in ("uk_property", "foreign_property"):
            inventory = inventory and row["kind"] not in property_kinds
            property_kinds.add(row["kind"])
        if known_kind and number <= 12:
            identity = "manual-" + uuid4().hex
            sources.append(IncomeSource(identity, IncomeKind(row["kind"]), gross or None, identity, bool(gross)))
    actuals = bool(period and period[2] < as_of and values.get("source_basis") == "submitted_return")
    support = MtdScopeCompleteness(residence and eligibility, inventory, timing, continuation, actuals)
    supported = residence and eligibility and inventory and timing and continuation and actuals
    handle = _issue(tuple(sources), assessment_tax_year=year, completeness=support,
                    registered_for_self_assessment=True if eligibility else None,
                    exemption_applies=False if eligibility else None)
    return handle, supported
