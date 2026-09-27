"""Focused hostile tests for the ephemeral 2026-27 MTD planning indication."""

from datetime import date, datetime, timezone
from decimal import Decimal
import importlib
import re

import pytest

import reserved.database as db
from reserved.engines.mtd_readiness import MtdStatus, assess_mtd_readiness
from reserved.services import mtd_manual_source_admission as admission
from reserved.services.mtd_scope_indication import as_mtd_scope_mapping
from tests.test_mtd_production_paid_boundary import _admit_paid_event, _production_app


route = importlib.import_module("reserved.web.v2")
URL = "/v2/mtd/scope-indication"
AS_OF = date(2026, 9, 5)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 5, 12, tzinfo=timezone.utc)


def current_facts(**changes):
    values = {
        "assessment_year": "2026-27",
        "submitted_on": "",
        "source_basis": "year_to_date",
        "return_revision": "original_unamended",
        "registered_for_sa": "yes",
        "acting_capacity": "own_individual",
        "relevant_tax_region": "england",
        "residence": "ordinary_uk",
        "ni_held_before_boundary": "yes",
        "hmrc_exemption_position": "none_known",
        "prior_mtd_position": "not_previously_enrolled_or_under_an_earlier_requirement",
        "all_sources_once": "yes",
        "own_shares": "yes",
        "vat_or_special_treatment": "no",
        "source_version_conflict": "no",
        "source_1_kind": "sole_trade",
        "source_1_gross_income": "100.00",
        "source_1_period_start": "2026-04-06",
        "source_1_period_end": "2026-09-05",
        "source_1_lifecycle": "active_throughout_and_still_continuing",
        "source_1_amount_basis": "own_gross_before_expenses",
    }
    values.update({
        f"{name}_{year}": "no"
        for year in admission.SCREEN_YEARS
        for name, _label in admission.SPECIAL_FACTS
    })
    values.update(changes)
    return values


def current_mapping(**changes):
    handle, supported = admission.admit_manual_mtd(current_facts(**changes), as_of=AS_OF)
    return as_mtd_scope_mapping(handle), supported


def test_current_year_annualises_only_derived_decimal_amounts_and_rounds_half_up(monkeypatch):
    seen = []
    real_issue = admission._issue

    def issue(sources, **kwargs):
        seen.extend(sources)
        return real_issue(sources, **kwargs)

    monkeypatch.setattr(admission, "_issue", issue)
    result, supported = current_mapping(source_1_gross_income="100.00")
    assert supported is True
    assert seen[0].kind.value == "sole_trade"
    assert seen[0].gross_income == Decimal("238.56")
    assert result["qualifying_income"] == Decimal("238.56")
    assert admission.annualise_current_year_gross("100.00", as_of=AS_OF) == Decimal("238.56")


def test_current_year_day_boundaries_and_leap_safe_day_helper():
    assert admission.tax_year_day_counts(assessment_year="2026-27", as_of=date(2026, 4, 6)) == (1, 365)
    assert admission.annualise_current_year_gross("1.00", as_of=date(2026, 4, 6)) == Decimal("365.00")
    assert admission.tax_year_day_counts(assessment_year="2026-27", as_of=date(2027, 4, 5)) == (365, 365)
    assert admission.annualise_current_year_gross("1.00", as_of=date(2027, 4, 5)) == Decimal("1.00")
    elapsed, total = admission.tax_year_day_counts(assessment_year="2027-28", as_of=date(2028, 2, 29))
    assert elapsed > 0 and total == 366


@pytest.mark.parametrize("gross,headline", [
    ("20000.00", "Worth reviewing", MtdStatus.APPROACHING_MTD_THRESHOLD),
    ("20000.01", "Worth reviewing", MtdStatus.MTD_APPLIES),
])
def test_year_end_threshold_equality_and_one_penny_are_deterministic(gross, headline, status, monkeypatch):
    seen = []
    real_issue = admission._issue

    def issue(sources, **kwargs):
        seen.extend(sources)
        return real_issue(sources, **kwargs)

    monkeypatch.setattr(admission, "_issue", issue)
    facts = current_facts(source_1_gross_income=gross, source_1_period_end="2027-04-05")
    handle, supported = admission.admit_manual_mtd(facts, as_of=date(2027, 4, 5))
    result = as_mtd_scope_mapping(handle)
    assert supported is True
    assert result["qualifying_income"] == Decimal(gross)
    assert result["headline"] == headline
    assert assess_mtd_readiness(
        seen, assessment_tax_year="2026-27", registered_for_self_assessment=True,
        exemption_applies=False,
    ).status is status


@pytest.mark.parametrize("changes", [
    {"source_1_period_start": "2026-04-07"},  # partial/new coverage
    {"source_1_period_end": "2026-09-04"},    # stale evidence
    {"source_1_period_end": "2026-09-06"},    # future evidence
    {"source_1_lifecycle": "started_or_ceased"},
    {"source_1_lifecycle": "unknown"},
    {"source_1_amount_basis": "whole_joint_or_net"},
    {"all_sources_once": "unknown"},
    {"vat_or_special_treatment": "yes"},
    {"source_version_conflict": "yes"},
    {"sa109_2026-27": "yes"},
    {"source_basis": "submitted_return"},
    {"submitted_on": "2026-09-05"},
])
def test_current_year_partial_stale_future_or_unresolved_evidence_fails_closed(changes):
    result, supported = current_mapping(**changes)
    assert supported is False
    assert result["information_complete"] is False
    assert result["qualifying_income"] is None


def test_current_year_duplicate_property_grouping_and_unsupported_year_fail_closed():
    duplicate = current_facts(
        source_1_kind="uk_property",
        source_2_kind="uk_property",
        source_2_gross_income="1.00",
        source_2_period_start="2026-04-06",
        source_2_period_end="2026-09-05",
        source_2_lifecycle="active_throughout_and_still_continuing",
        source_2_amount_basis="own_gross_before_expenses",
    )
    handle, supported = admission.admit_manual_mtd(duplicate, as_of=AS_OF)
    assert supported is False
    assert as_mtd_scope_mapping(handle)["information_complete"] is False
    handle, supported = admission.admit_manual_mtd(current_facts(assessment_year="2027-28"), as_of=AS_OF)
    assert supported is False
    assert as_mtd_scope_mapping(handle)["information_complete"] is False
    with pytest.raises(ValueError):
        admission.tax_year_day_counts(assessment_year="2026-27", as_of=date(2027, 4, 6))


def _csrf(html):
    matched = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert matched
    return matched.group(1)


def test_paid_production_owner_gets_current_year_indication_without_persisting_evidence(tmp_path, monkeypatch):
    client, runtime, owner_id = _production_app(tmp_path, monkeypatch, enabled=True)
    monkeypatch.setattr(route, "datetime", Clock)
    assert client.get(URL).status_code == 403
    _admit_paid_event(runtime, owner_id)
    page = client.get(URL)
    assert page.status_code == 200
    token = _csrf(page.get_data(as_text=True))
    with db._connection() as connection:
        before = tuple(connection.iterdump())
    response = client.post(URL, data={**current_facts(), "csrf_token": token})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Early annualised planning indication" in html
    assert "Included source totals" in html
    assert "£238.56" in html
    with db._connection() as connection:
        assert tuple(connection.iterdump()) == before
