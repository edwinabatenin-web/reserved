"""Adversarial tests for the W8-S1 accounting-to-tax handoff boundary.

Expected values are stated independently from the implementation. The handoff
must consume exact ``CanonicalAccountingTaxInput`` values plus their exact
``SourceObservation`` evidence, derive one supported business-income fact set,
and return immutable, deterministic provenance without leaking hostile values.
"""
import ast
import enum
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal, Inexact, localcontext
from pathlib import Path

import pytest

from reserved.engines.accounting_tax_handoff import (
    AccountingTaxHandoffError,
    AccountingTaxHandoffResult,
    _ACCOUNTING_CONTRACTS_MODULE,
    _derive_contracts_module,
    calculate_annual_position_from_accounting,
)
from reserved.engines.integrated_annual_position import (
    AnnualPositionResult,
    calculate_annual_position,
)
from reserved.providers.accounting.contracts import (
    AccountingProviderName,
    AllowabilityDecision,
    AllowabilityOutcome,
    BusinessType,
    CanonicalAccountingTaxInput,
    DecisionAuthority,
    EvidenceState,
    Provenance,
    SourceIdentity,
    SourceObservation,
)

RETRIEVED_AT = datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc)

_HANDOFF_SOURCE = Path(__file__).resolve().parents[1] / "reserved" / "engines" / "accounting_tax_handoff.py"


# ── Construction helpers (production contracts only, no fixtures) ─────────────

def _identity(*, user_id="user-1", provider=AccountingProviderName.XERO,
              connected_organisation_id="org-1", business_id="business-1",
              import_run_id="run-1"):
    return SourceIdentity(user_id, provider, connected_organisation_id,
                          business_id, import_run_id)


def _provenance(*, record_id="rec-1", **identity_kwargs):
    return Provenance(
        identity=_identity(**identity_kwargs),
        api_name="synthetic",
        api_version="v1",
        resource="invoices",
        record_id=record_id,
        source_fields=("provider_document_id",),
        retrieved_at=RETRIEVED_AT,
        adapter_version="syn-1",
        source_record_digest="digest",
    )


def _observation(observation_id, *, evidence_state=EvidenceState.SELECTED,
                 missing_fields=(), competing_observation_ids=(),
                 record_id=None, **identity_kwargs):
    if record_id is None:
        record_id = observation_id
    return SourceObservation(
        observation_id=observation_id,
        provenance=_provenance(record_id=record_id, **identity_kwargs),
        evidence_state=evidence_state,
        missing_fields=missing_fields,
        competing_observation_ids=competing_observation_ids,
    )


def _allowability(decision_id="decision-allow-1", outcome=AllowabilityOutcome.ALLOWABLE,
                  fraction=None, source_observation_ids=(),
                  authority=DecisionAuthority.RESERVED_RULE):
    return AllowabilityDecision(
        decision_id, outcome, authority, RETRIEVED_AT,
        "business expense", allowable_fraction=fraction,
        source_observation_ids=source_observation_ids,
    )


def _tax_input(*, input_id="i1", economic_event_id="e1", classification="turnover",
               recognised_amount="100.00", business_id="business-1",
               tax_year="2026/27", evidence_observation_ids=("o1",),
               allowability=None, allowability_decision_id=None,
               ownership_adjustment=None, permitted_uses=("tax_estimate",),
               prohibited_uses=("settlement", "write_back")):
    return CanonicalAccountingTaxInput(
        input_id=input_id,
        purpose="income",
        scope="self-assessment",
        business_id=business_id,
        economic_event_id=economic_event_id,
        tax_year=tax_year,
        recognised_amount=Decimal(recognised_amount),
        recognised_date=date(2026, 8, 10),
        classification=classification,
        currency="GBP",
        base_currency="GBP",
        evidence_observation_ids=evidence_observation_ids,
        recognition_decision_id="recognition-1",
        allowability_decision_id=allowability_decision_id,
        policy_version="v1",
        ownership_adjustment=ownership_adjustment,
        allowability=allowability,
        permitted_uses=permitted_uses,
        prohibited_uses=prohibited_uses,
    )


def _calc(business_type, inputs, observations, tax_year="2026/27"):
    return calculate_annual_position_from_accounting(
        tax_year=tax_year,
        business_type=business_type,
        inputs=inputs,
        observations=observations,
    )


def _trade_bundle():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount="10000", evidence_observation_ids=("o1",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o2",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount="2000", evidence_observation_ids=("o2",),
                    allowability=allow, allowability_decision_id="a1")
    return [i1, i2], [o1, o2]


def _property_bundle(receipts="10000", expenses="2000"):
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount=receipts, evidence_observation_ids=("o1",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o2",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount=expenses, evidence_observation_ids=("o2",),
                    allowability=allow, allowability_decision_id="a1")
    return [i1, i2], [o1, o2]


# ── Supported bundles calculate through and retain deterministic provenance ───

def test_trade_bundle_calculates_through_annual_engine():
    inputs, observations = _trade_bundle()
    result = _calc(BusinessType.TRADE, inputs, observations)

    assert isinstance(result, AccountingTaxHandoffResult)
    assert isinstance(result.annual_position, AnnualPositionResult)
    assert result.annual_position.adjusted_net_income == Decimal("8000.00")
    assert result.annual_position.calculation_status == "insufficient_facts"  # BPA absent
    assert result.annual_position.total_liability is None
    assert [f.name for f in result.facts] == ["sole_trade_profit"]
    assert result.facts[0].value == Decimal("8000")


def test_uk_property_bundle_calculates_through_annual_engine():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount="10000", evidence_observation_ids=("o1",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o2",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount="2000", evidence_observation_ids=("o2",),
                    allowability=allow, allowability_decision_id="a1")

    result = _calc(BusinessType.UK_PROPERTY, [i1, i2], [o1, o2])

    assert result.annual_position.uk_property_profit == Decimal("8000.00")
    assert {f.name for f in result.facts} == {
        "uk_property_receipts", "uk_property_allowable_expenses",
    }
    mapping = result.facts_mapping()
    assert mapping["uk_property_receipts"] == Decimal("10000")
    assert mapping["uk_property_allowable_expenses"] == Decimal("2000")


def test_foreign_property_bundle_calculates_through_annual_engine():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount="10000", evidence_observation_ids=("o1",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o2",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount="2000", evidence_observation_ids=("o2",),
                    allowability=allow, allowability_decision_id="a1")

    result = _calc(BusinessType.FOREIGN_PROPERTY, [i1, i2], [o1, o2])

    assert result.annual_position.foreign_property_profit == Decimal("8000.00")
    assert "foreign_property_residence" in result.annual_position.unsupported_families
    assert {f.name for f in result.facts} == {
        "foreign_property_gross_receipts", "foreign_property_allowable_expenses",
    }


# ── Exact Decimal expense treatment ────────────────────────────────────────────

@pytest.mark.parametrize("outcome,fraction,expected_expense", [
    (AllowabilityOutcome.ALLOWABLE, None, Decimal("2000")),
    (AllowabilityOutcome.DISALLOWABLE, None, Decimal("0")),
    (AllowabilityOutcome.MIXED_APPORTIONED, Decimal("0.25"), Decimal("500")),
])
def test_expense_allowability_uses_exact_decimal_arithmetic(outcome, fraction, expected_expense):
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount="10000", evidence_observation_ids=("o1",))
    allow = _allowability("a1", outcome, fraction, source_observation_ids=("o2",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount="2000", evidence_observation_ids=("o2",),
                    allowability=allow, allowability_decision_id="a1")

    result = _calc(BusinessType.TRADE, [i1, i2], [o1, o2])

    assert result.facts[0].value == Decimal("10000") - expected_expense
    contribution = [c for c in result.contributions if c.classification == "expense"][0]
    assert contribution.contributed_amount == expected_expense


# ── Duplicate identity failures ────────────────────────────────────────────────

def test_duplicate_input_id_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i1", economic_event_id="e2", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1])
    assert exc.value.code == "input_id_duplicate"


def test_duplicate_economic_event_id_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e1", evidence_observation_ids=("o2",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == "economic_event_id_duplicate"


def test_duplicate_observation_id_fails():
    o1 = _observation("o1")
    o2 = _observation("o1")  # duplicate id
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == "observation_id_duplicate"


def test_duplicate_evidence_reference_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1", "o1"))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", evidence_observation_ids=("o2",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == "evidence_id_duplicate"


# ── Cross-identity substitution failures ───────────────────────────────────────

@pytest.mark.parametrize("identity_kwargs,expected_code", [
    ({"user_id": "user-2"}, "observation_identity_mismatch"),
    ({"connected_organisation_id": "org-2"}, "observation_identity_mismatch"),
    ({"business_id": "business-2"}, "observation_identity_mismatch"),
    ({"provider": AccountingProviderName.FREEAGENT}, "observation_identity_mismatch"),
])
def test_cross_identity_substitution_fails(identity_kwargs, expected_code):
    o1 = _observation("o1")
    o2 = _observation("o2", **identity_kwargs)
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", evidence_observation_ids=("o2",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == expected_code


def test_input_business_mismatch_with_observation_fails():
    o1 = _observation("o1")  # business-1
    i1 = _tax_input(input_id="i1", economic_event_id="e1", business_id="business-other",
                    evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "business_identity_mismatch"


# ── Observation set completeness / state failures ──────────────────────────────

def test_missing_observation_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1", "o2"))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_missing"


def test_extra_unreferenced_observation_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1, o2])
    assert exc.value.code == "observation_extra"


@pytest.mark.parametrize("evidence_state,expected_code", [
    (EvidenceState.CONFLICTING, "observation_evidence_not_selected"),
    (EvidenceState.SUPERSEDED, "observation_evidence_not_selected"),
    (EvidenceState.UNRESOLVED, "observation_evidence_not_selected"),
    (EvidenceState.EXCLUDED, "observation_evidence_not_selected"),
])
def test_non_selected_observation_state_fails(evidence_state, expected_code):
    o1 = _observation("o1", evidence_state=evidence_state)
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == expected_code


def test_incomplete_observation_missing_fields_fails():
    o1 = _observation("o1", missing_fields=("provider_total",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_evidence_incomplete"


def test_conflicting_observation_competing_ids_fails():
    o1 = _observation("o1", competing_observation_ids=("o9",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_evidence_conflicting"


# ── Mutated / fabricated / subclassed dataclasses fail ─────────────────────────

class _FakeTaxInput(CanonicalAccountingTaxInput):
    pass


class _FakeObservation(SourceObservation):
    pass


def test_subclassed_tax_input_fails():
    o1 = _observation("o1")
    fake = _FakeTaxInput(
        input_id="i1", purpose="income", scope="self-assessment",
        business_id="business-1", economic_event_id="e1", tax_year="2026/27",
        recognised_amount=Decimal("100"), recognised_date=date(2026, 8, 10),
        classification="turnover", currency="GBP", base_currency="GBP",
        evidence_observation_ids=("o1",), recognition_decision_id="r1",
        allowability_decision_id=None, policy_version="v1",
        permitted_uses=("tax_estimate",), prohibited_uses=("settlement", "write_back"),
    )
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [fake], [o1])
    assert exc.value.code == "input_type_invalid"


def test_subclassed_observation_fails():
    fake = _FakeObservation(
        observation_id="o1", provenance=_provenance(record_id="o1"),
        evidence_state=EvidenceState.SELECTED,
    )
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [fake])
    assert exc.value.code == "observation_type_invalid"


def test_mutated_forged_provenance_fails():
    o1 = _observation("o1")
    object.__setattr__(o1, "provenance", "not-a-provenance")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_provenance_invalid"


def test_mutated_evidence_state_fails():
    o1 = _observation("o1")
    object.__setattr__(o1, "evidence_state", "selected")  # forged string, not enum
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_evidence_state_invalid"


# ── Tax-year / business / decision-ID mismatches fail ──────────────────────────

def test_unsupported_tax_year_fails():
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [_tax_input()], [_observation("o1")], tax_year="2099/00")
    assert exc.value.code == "tax_year_unsupported"


def test_input_tax_year_mismatch_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", tax_year="2099/00",
                    evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "tax_year_mismatch"


@pytest.mark.parametrize("business_type,expected_code", [
    (BusinessType.UNKNOWN, "business_type_unsupported"),
    (BusinessType.UNSUPPORTED, "business_type_unsupported"),
    ("trade", "business_type_invalid"),
])
def test_unsupported_or_string_business_type_fails(business_type, expected_code):
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(business_type, [i1], [o1])
    assert exc.value.code == expected_code


def test_allowability_decision_id_contradiction_fails():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o1",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a-different")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_id_contradiction"


# ── Floats / bools / non-finite / hostile containers / strings fail ────────────

def test_mutated_float_amount_fails_without_leakage():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_amount", 123.45)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "recognised_amount_invalid"
    assert "123.45" not in str(exc.value)


def test_mutated_boolean_amount_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_amount", True)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "recognised_amount_invalid"


def test_mutated_non_finite_amount_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_amount", Decimal("NaN"))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "recognised_amount_invalid"


def test_zero_or_negative_amount_fails():
    o1 = _observation("o1")
    for amount in ("0", "-10"):
        i1 = _tax_input(input_id="i1", economic_event_id="e1", recognised_amount=amount,
                        evidence_observation_ids=("o1",))
        with pytest.raises(AccountingTaxHandoffError) as exc:
            _calc(BusinessType.TRADE, [i1], [o1])
        assert exc.value.code == "recognised_amount_invalid"


def test_hostile_container_inputs_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, {"i1": i1}, [o1])
    assert exc.value.code == "inputs_container_invalid"


def test_mutated_evidence_ids_to_list_fails():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "evidence_observation_ids", ["o1"])
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "evidence_observation_ids_invalid"


def test_hostile_classification_string_fails_without_leakage():
    o1 = _observation("o1")
    hostile = "__import__('os').system('rm -rf /')"
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification=hostile,
                    evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "classification_unsupported"
    assert hostile not in str(exc.value)


# ── Credit / refund / write-off / adjustment / ownership fail closed ───────────

@pytest.mark.parametrize("classification", ["credit_note", "refund", "write_off"])
def test_credit_refund_write_off_fail_closed(classification):
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification=classification,
                    evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "classification_unsupported"


def test_adjustment_required_expense_fails_closed():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ADJUSTMENT_REQUIRED, source_observation_ids=("o1",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_outcome_unsupported"


def test_missing_expense_allowability_fails_closed():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "expense_missing_allowability"


def test_ambiguous_ownership_adjustment_fails_closed():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",),
                    ownership_adjustment=Decimal("0.5"))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "ownership_adjustment_unsupported"


# ── Raw provider records rejected ──────────────────────────────────────────────

def test_raw_provider_dictionary_rejected():
    o1 = _observation("o1")
    raw = {"provider_document_id": "doc-1", "provider_total": "100.00"}
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [raw], [o1])
    assert exc.value.code == "input_type_invalid"


def test_freeagent_raw_record_rejected():
    o1 = _observation("o1")
    raw = {"url": "https://api.freeagent.com/v2/invoices/1", "status": "open"}
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [raw], [o1])
    assert exc.value.code == "input_type_invalid"


# ── Double counting of the same economic event is rejected ─────────────────────

def test_same_economic_event_cannot_be_counted_twice():
    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e1", evidence_observation_ids=("o2",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == "economic_event_id_duplicate"


# ── Provenance immutability / determinism ──────────────────────────────────────

def test_provenance_is_immutable_and_deterministic():
    inputs, observations = _trade_bundle()
    r1 = _calc(BusinessType.TRADE, inputs, observations)
    r2 = _calc(BusinessType.TRADE, inputs, observations)

    assert r1.provenance == r2.provenance
    assert r1.provenance.input_ids == ("i1", "i2")
    assert r1.provenance.economic_event_ids == ("e1", "e2")
    assert r1.provenance.observation_ids == ("o1", "o2")
    assert r1.provenance.business_id == "business-1"
    assert r1.provenance.user_id == "user-1"
    assert r1.provenance.connected_organisation_id == "org-1"
    assert r1.provenance.provider == "xero"

    with pytest.raises(AttributeError):
        r1.provenance.business_id = "mutated"


def test_changed_identity_changes_provenance():
    inputs, observations = _trade_bundle()
    r1 = _calc(BusinessType.TRADE, inputs, observations)

    alt_o1 = _observation("o1", business_id="business-alt")
    alt_o2 = _observation("o2", business_id="business-alt")
    alt_i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                        recognised_amount="10000", business_id="business-alt",
                        evidence_observation_ids=("o1",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o2",))
    alt_i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                        recognised_amount="2000", business_id="business-alt",
                        evidence_observation_ids=("o2",), allowability=allow,
                        allowability_decision_id="a1")
    r2 = _calc(BusinessType.TRADE, [alt_i1, alt_i2], [alt_o1, alt_o2])

    assert r1.provenance.business_id == "business-1"
    assert r2.provenance.business_id == "business-alt"
    assert r1.provenance != r2.provenance


def test_facts_mapping_is_read_only():
    inputs, observations = _trade_bundle()
    result = _calc(BusinessType.TRADE, inputs, observations)
    mapping = result.facts_mapping()
    assert mapping["sole_trade_profit"] == Decimal("8000")
    with pytest.raises(TypeError):
        mapping["sole_trade_profit"] = Decimal("1")


# ── Boundary imports no provider/network/persistence/route/UI/config ───────────

def test_handoff_module_imports_no_forbidden_paths():
    module_path = Path(__file__).resolve().parents[1] / "reserved" / "engines" / "accounting_tax_handoff.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "reserved.providers.accounting.freeagent",
        "reserved.providers.accounting.xero",
        "reserved.providers.accounting.quickbooks",
        "reserved.web", "reserved.services", "reserved.api",
        "reserved.database", "reserved.models", "reserved.repositories",
        "requests", "flask",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    for name in imported:
        assert not name.startswith(forbidden_prefixes), f"forbidden import {name}"


# ── Module-identity authority (artefact-safe, no hard-coded module string) ─────

def test_handoff_source_uses_absolute_canonical_contract_import():
    tree = ast.parse(_HANDOFF_SOURCE.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "reserved.providers.accounting.contracts":
            assert node.level == 0, "canonical contract import must be absolute"
            found.extend(alias.name for alias in node.names)
    assert "CanonicalAccountingTaxInput" in found
    assert "SourceObservation" in found


def test_no_hardcoded_contracts_module_string_as_authority():
    tree = ast.parse(_HANDOFF_SOURCE.read_text(encoding="utf-8"))
    authority_assign = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_ACCOUNTING_CONTRACTS_MODULE":
                    authority_assign = node
    assert authority_assign is not None
    assert isinstance(authority_assign.value, ast.Call), (
        "runtime module authority must be derived, not a literal string"
    )
    assert isinstance(authority_assign.value.func, ast.Name)
    assert authority_assign.value.func.id == "_derive_contracts_module"


def test_runtime_module_authority_derived_from_canonical_roots():
    assert _ACCOUNTING_CONTRACTS_MODULE == CanonicalAccountingTaxInput.__module__
    assert _ACCOUNTING_CONTRACTS_MODULE == SourceObservation.__module__
    assert _ACCOUNTING_CONTRACTS_MODULE == "reserved.providers.accounting.contracts"


def test_runtime_identity_table_uses_actual_contract_classes():
    import reserved.engines.accounting_tax_handoff as handoff

    # The trusted enum/dataclass types must be the exact imported canonical
    # classes (identity, not spoofable module/qualname strings).
    assert handoff.BusinessType is BusinessType
    assert handoff.AllowabilityDecision is AllowabilityDecision
    assert handoff.AllowabilityOutcome is AllowabilityOutcome
    assert handoff.DecisionAuthority is DecisionAuthority
    assert handoff.EvidenceState is EvidenceState
    assert handoff.Provenance is Provenance
    assert handoff.SourceIdentity is SourceIdentity
    assert handoff.AccountingProviderName is AccountingProviderName


def test_derive_contracts_module_fails_closed_on_invalid_roots():
    class _RootA:
        pass

    class _RootB:
        pass

    _RootA.__module__ = ""
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _derive_contracts_module(_RootA, _RootB)
    assert exc.value.code == "contract_root_module_invalid"

    _RootA.__module__ = 123
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _derive_contracts_module(_RootA, _RootB)
    assert exc.value.code == "contract_root_module_invalid"

    _RootA.__module__ = "module.one"
    _RootB.__module__ = "module.two"
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _derive_contracts_module(_RootA, _RootB)
    assert exc.value.code == "contract_root_module_mismatch"

    _RootA.__module__ = "module.same"
    _RootB.__module__ = "module.same"
    assert _derive_contracts_module(_RootA, _RootB) == "module.same"


# ── Independently reproduced bypasses fail closed ──────────────────────────────

def test_fabricated_enum_spoofing_module_qualname_fails():
    class FakeBusinessType(enum.Enum):
        TRADE = "trade"

    FakeBusinessType.__module__ = "reserved.providers.accounting.contracts"
    FakeBusinessType.__qualname__ = "BusinessType"

    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(FakeBusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "business_type_invalid"


def test_fabricated_allowability_outcome_enum_fails():
    class FakeOutcome(enum.Enum):
        ALLOWABLE = "allowable"

    FakeOutcome.__module__ = "reserved.providers.accounting.contracts"
    FakeOutcome.__qualname__ = "AllowabilityOutcome"

    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[1].allowability, "outcome", FakeOutcome.ALLOWABLE)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "allowability_outcome_invalid"


def test_fabricated_allowability_decision_shape_fails():
    @dataclass(frozen=True)
    class _SpoofedAllowabilityDecision:
        decision_id: str
        outcome: object
        authority: object
        decided_at: object
        reason: str
        allowable_fraction: object
        provider_assertion: object
        source_observation_ids: object

    _SpoofedAllowabilityDecision.__module__ = "reserved.providers.accounting.contracts"
    _SpoofedAllowabilityDecision.__qualname__ = "AllowabilityDecision"

    o1 = _observation("o1")
    spoof = _SpoofedAllowabilityDecision(
        "a1", AllowabilityOutcome.ALLOWABLE, DecisionAuthority.RESERVED_RULE,
        RETRIEVED_AT, "business expense", None, None, ("o1",),
    )
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=spoof, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_invalid"


def test_fabricated_source_identity_shape_fails():
    @dataclass(frozen=True)
    class _SpoofedSourceIdentity:
        user_id: str
        provider: object
        connected_organisation_id: str
        business_id: str
        import_run_id: str

    _SpoofedSourceIdentity.__module__ = "reserved.providers.accounting.contracts"
    _SpoofedSourceIdentity.__qualname__ = "SourceIdentity"

    inputs, observations = _trade_bundle()
    spoof = _SpoofedSourceIdentity("user-1", AccountingProviderName.XERO, "org-1", "business-1", "run-1")
    object.__setattr__(observations[0].provenance, "identity", spoof)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "observation_identity_invalid"


def test_fabricated_provenance_shape_fails():
    @dataclass(frozen=True)
    class _SpoofedProvenance:
        identity: object

    _SpoofedProvenance.__module__ = "reserved.providers.accounting.contracts"
    _SpoofedProvenance.__qualname__ = "Provenance"

    inputs, observations = _trade_bundle()
    object.__setattr__(observations[0], "provenance", _SpoofedProvenance(object()))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "observation_provenance_invalid"


def test_mutated_source_record_digest_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(observations[0].provenance, "source_record_digest", 12345)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "observation_source_digest_invalid"


def test_mutated_currency_contradiction_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[0], "currency", "EUR")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "currency_base_currency_mismatch"


def test_mutated_allowability_authority_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[1].allowability, "authority", "reserved_rule")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "allowability_authority_invalid"


def test_mutated_allowability_decided_at_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[1].allowability, "decided_at", "2026-08-03T10:00:00Z")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "allowability_decided_at_invalid"


def test_mutated_allowability_source_ids_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[1].allowability, "source_observation_ids", ["o2"])
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "allowability_source_observation_ids_invalid"


def test_incompatible_purpose_fails_closed():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[0], "purpose", "file_payment")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "purpose_unsupported"


def test_incompatible_scope_fails_closed():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[0], "scope", "production_writeback")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "scope_unsupported"


def test_allowability_unbound_to_evidence_fails():
    inputs, observations = _trade_bundle()
    object.__setattr__(inputs[1].allowability, "source_observation_ids", ("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "allowability_evidence_unbound"


# ── Deterministic per-input-to-observation/source-record binding ───────────────

def test_provenance_binds_each_input_to_its_evidence():
    inputs, observations = _trade_bundle()
    result = _calc(BusinessType.TRADE, inputs, observations)
    bindings = {b.input_id: b for b in result.provenance.input_evidence}
    assert set(bindings) == {"i1", "i2"}
    assert bindings["i1"].observation_ids == ("o1",)
    assert bindings["i2"].observation_ids == ("o2",)
    assert bindings["i1"].source_records[0].record_id == "o1"
    assert bindings["i1"].source_records[0].source_record_digest == "digest"
    assert bindings["i2"].source_records[0].record_id == "o2"


def test_swapped_evidence_binding_changes_provenance():
    inputs, observations = _trade_bundle()
    r1 = _calc(BusinessType.TRADE, inputs, observations)

    o1 = _observation("o1")
    o2 = _observation("o2")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="turnover",
                    recognised_amount="10000", evidence_observation_ids=("o2",))
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", classification="expense",
                    recognised_amount="2000", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    r2 = _calc(BusinessType.TRADE, [i1, i2], [o1, o2])

    assert r1.facts == r2.facts
    assert r1.provenance.input_evidence != r2.provenance.input_evidence


def test_changed_source_record_identity_changes_provenance():
    inputs, observations = _trade_bundle()
    r1 = _calc(BusinessType.TRADE, inputs, observations)

    object.__setattr__(observations[1].provenance, "record_id", "rec-changed")
    r2 = _calc(BusinessType.TRADE, inputs, observations)

    assert r1.facts == r2.facts
    assert r1.provenance.input_evidence != r2.provenance.input_evidence


def test_changed_source_record_digest_changes_provenance():
    inputs, observations = _trade_bundle()
    r1 = _calc(BusinessType.TRADE, inputs, observations)

    object.__setattr__(observations[1].provenance, "source_record_digest", "digest-changed")
    r2 = _calc(BusinessType.TRADE, inputs, observations)

    assert r1.facts == r2.facts
    assert r1.provenance.input_evidence != r2.provenance.input_evidence


def test_extra_nested_dataclass_field_fails_categorically():
    inputs, observations = _trade_bundle()
    object.__setattr__(observations[0].provenance, "forged_extra", "leak-me")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "observation_provenance_invalid"
    assert "forged_extra" not in str(exc.value)
    assert "leak-me" not in str(exc.value)


def test_missing_nested_dataclass_field_fails_categorically():
    inputs, observations = _trade_bundle()
    object.__delattr__(observations[0].provenance, "source_record_digest")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "observation_provenance_invalid"


# ── W8-S1 final focused corrections ────────────────────────────────────────────

@pytest.mark.parametrize("authority", [
    DecisionAuthority.PROVIDER_ASSERTION,
    DecisionAuthority.CUSTOMER_CONFIRMATION,
    DecisionAuthority.ADVISER_ADJUSTMENT,
])
def test_non_reserved_authority_fails_closed_even_when_allowable(authority):
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE,
                          source_observation_ids=("o1",), authority=authority)
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_authority_unsupported"


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_equal_non_gbp_currency_pair_fails(currency):
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "currency", currency)
    object.__setattr__(i1, "base_currency", currency)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "currency_unsupported"


@pytest.mark.parametrize("bad_date", [
    date(2026, 4, 5),
    date(2027, 4, 6),
    date(2025, 12, 31),
])
def test_recognition_date_out_of_tax_year_fails(bad_date):
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_date", bad_date)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "recognised_date_out_of_period"


@pytest.mark.parametrize("ok_date", [date(2026, 4, 6), date(2027, 4, 5)])
def test_recognition_date_boundary_inclusive(ok_date):
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_date", ok_date)
    result = _calc(BusinessType.TRADE, [i1], [o1])
    assert result.facts[0].value == Decimal("100.00")


def test_recognition_date_datetime_subclass_rejected():
    class FakeDateTime(datetime):
        pass

    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_date", FakeDateTime(2026, 8, 10, tzinfo=timezone.utc))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "recognised_date_invalid"


@pytest.mark.parametrize("outcome,fraction", [
    (AllowabilityOutcome.ALLOWABLE, Decimal("0.5")),
    (AllowabilityOutcome.ALLOWABLE, Decimal("1")),
    (AllowabilityOutcome.DISALLOWABLE, Decimal("0.5")),
    (AllowabilityOutcome.DISALLOWABLE, Decimal("0")),
])
def test_allowable_disallowable_contradictory_fraction_fails(outcome, fraction):
    o1 = _observation("o1")
    allow = _allowability("a1", outcome, fraction, source_observation_ids=("o1",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_fraction_invalid"


def test_allowable_malformed_fraction_fails():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o1",))
    object.__setattr__(allow, "allowable_fraction", "0.5")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_fraction_invalid"


@pytest.mark.parametrize("fraction", [Decimal("0"), Decimal("1")])
def test_mixed_apportioned_fraction_must_be_strictly_between(fraction):
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.MIXED_APPORTIONED, fraction,
                          source_observation_ids=("o1",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_fraction_invalid"


def test_mixed_apportioned_non_finite_fraction_fails():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.MIXED_APPORTIONED, Decimal("0.5"),
                          source_observation_ids=("o1",))
    object.__setattr__(allow, "allowable_fraction", Decimal("NaN"))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_fraction_invalid"


def test_allowability_source_ids_duplicate_fails():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE,
                          source_observation_ids=("o1", "o1"))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_source_observation_ids_invalid"


def test_allowability_source_ids_reordering_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE,
                          source_observation_ids=("o2", "o1"))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1", "o2"),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1, o2])
    assert exc.value.code == "allowability_evidence_unbound"


def test_allowability_source_ids_missing_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE,
                          source_observation_ids=("o1",))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1", "o2"),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1, o2])
    assert exc.value.code == "allowability_evidence_unbound"


def test_allowability_source_ids_extra_fails():
    o1 = _observation("o1")
    o2 = _observation("o2")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE,
                          source_observation_ids=("o1", "o2"))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1, o2])
    assert exc.value.code == "allowability_evidence_unbound"


def test_naive_retrieved_at_rejected():
    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at", datetime(2026, 8, 3, 10, 0, 0))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"


def test_naive_decided_at_rejected():
    o1 = _observation("o1")
    allow = _allowability("a1", AllowabilityOutcome.ALLOWABLE, source_observation_ids=("o1",))
    object.__setattr__(allow, "decided_at", datetime(2026, 8, 3, 10, 0, 0))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", classification="expense",
                    recognised_amount="200", evidence_observation_ids=("o1",),
                    allowability=allow, allowability_decision_id="a1")
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "allowability_decided_at_invalid"


def test_datetime_subclass_rejected_without_leakage():
    class FakeDateTime(datetime):
        pass

    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       FakeDateTime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"
    assert "FakeDateTime" not in str(exc.value)


# ── Stable source-record deduplication (volatile fields must not split identity) ──

def _same_record_pair():
    o1 = _observation("o1", record_id="rec-shared")
    o2 = _observation("o2", record_id="rec-shared")
    return o1, o2


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda o: object.__setattr__(o.provenance.identity, "import_run_id", "run-2"),
                 id="import_run"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "api_version", "v2"), id="api_version"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "adapter_version", "syn-2"),
                 id="adapter_version"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "source_record_digest", "digest-2"),
                 id="digest"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "revision_id", "rev-2"),
                 id="revision"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "source_schema_id", "schema-2"),
                 id="source_schema"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "retrieved_at",
                                             datetime(2026, 8, 4, tzinfo=timezone.utc)),
                 id="timestamp"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "source_fields", ("other_field",)),
                 id="source_fields"),
    pytest.param(lambda o: object.__setattr__(o.provenance, "source_definitions", ("other_def",)),
                 id="source_definitions"),
])
def test_same_stable_source_record_fails_across_volatile_variations(mutate):
    o1, o2 = _same_record_pair()
    mutate(o2)
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    i2 = _tax_input(input_id="i2", economic_event_id="e2", evidence_observation_ids=("o2",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1, i2], [o1, o2])
    assert exc.value.code == "source_record_duplicate"


# ── Complete categorical downstream boundary ───────────────────────────────────

def test_decimal_inexact_trap_fails_categorically():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1",
                    recognised_amount="100.001", evidence_observation_ids=("o1",))
    with localcontext() as ctx:
        ctx.traps[Inexact] = True
        with pytest.raises(AccountingTaxHandoffError) as exc:
            _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "monetary_value_unrepresentable"


def test_huge_unrepresentable_amount_rejected_categorically():
    o1 = _observation("o1")
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    object.__setattr__(i1, "recognised_amount", Decimal("1e999999"))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "monetary_value_unrepresentable"


def test_annual_engine_exception_collapses_to_fixed_code(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    def boom(facts, tax_year):
        raise ValueError("ANNUAL-ENGINE-SECRET")

    monkeypatch.setattr(handoff, "calculate_annual_position", boom)
    inputs, observations = _trade_bundle()
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "annual_position_engine_failure"
    assert "ANNUAL-ENGINE-SECRET" not in str(exc.value)
    assert "ValueError" not in str(exc.value)


def test_annual_engine_keyboard_interrupt_not_swallowed(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    def boom(facts, tax_year):
        raise KeyboardInterrupt

    monkeypatch.setattr(handoff, "calculate_annual_position", boom)
    inputs, observations = _trade_bundle()
    with pytest.raises(KeyboardInterrupt):
        _calc(BusinessType.TRADE, inputs, observations)


def test_annual_engine_system_exit_not_swallowed(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    def boom(facts, tax_year):
        raise SystemExit(1)

    monkeypatch.setattr(handoff, "calculate_annual_position", boom)
    inputs, observations = _trade_bundle()
    with pytest.raises(SystemExit):
        _calc(BusinessType.TRADE, inputs, observations)


def test_annual_engine_wrong_result_type_fails(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: object())
    inputs, observations = _trade_bundle()
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "annual_position_result_invalid"


def test_annual_engine_non_finite_monetary_result_fails(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _trade_bundle()
    valid = _calc(BusinessType.TRADE, inputs, observations)
    bad = replace(valid.annual_position, adjusted_net_income=Decimal("NaN"))
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: bad)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "annual_position_monetary_invalid"


# ── Annual-result exact type integrity ─────────────────────────────────────────

_ANNUAL_REQUIRED_MONEY_FIELDS = (
    "adjusted_net_income", "personal_allowance", "non_savings_tax", "savings_tax",
    "dividend_tax", "class_4_ni", "personal_savings_allowance", "dividend_allowance",
    "uk_property_profit", "uk_property_loss_to_carry_forward", "foreign_tax_paid_recorded",
)

_ANNUAL_OPTIONAL_MONEY_FIELDS = (
    "blind_persons_allowance", "income_tax_before_limitations", "hicbc",
    "hicbc_household_charge", "child_benefit_amount", "total_liability",
    "foreign_property_profit",
)

_ANNUAL_TEXT_FIELDS = ("contract_version", "tax_year", "ruleset_version", "calculation_status")


def _annual_position_for_bundle():
    inputs, observations = _trade_bundle()
    return _calc(BusinessType.TRADE, inputs, observations).annual_position


def _assert_annual_position_field_fails(monkeypatch, annual, *, code):
    import reserved.engines.accounting_tax_handoff as handoff

    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: annual)
    inputs, observations = _trade_bundle()
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == code
    return exc


@pytest.mark.parametrize("field", _ANNUAL_REQUIRED_MONEY_FIELDS)
def test_annual_result_required_money_non_decimal_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: "not-decimal"})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _ANNUAL_OPTIONAL_MONEY_FIELDS)
def test_annual_result_optional_money_non_decimal_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: "not-decimal"})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _ANNUAL_REQUIRED_MONEY_FIELDS)
def test_annual_result_required_money_non_finite_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: Decimal("NaN")})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _ANNUAL_OPTIONAL_MONEY_FIELDS)
def test_annual_result_optional_money_non_finite_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: Decimal("Infinity")})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _ANNUAL_TEXT_FIELDS)
def test_annual_result_text_field_non_string_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: 42})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("field", _ANNUAL_TEXT_FIELDS)
def test_annual_result_text_field_empty_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: ""})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("field,value", [
    ("contract_version", "forged-contract"),
    ("tax_year", "2025/26"),
    ("ruleset_version", "forged-ruleset"),
    ("calculation_status", "forged-status"),
])
def test_annual_result_text_field_invalid_value_fails(monkeypatch, field, value):
    annual = replace(_annual_position_for_bundle(), **{field: value})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("value", [True, False, 1.5, "50", -1, 101])
def test_annual_result_hicbc_percentage_invalid_fails(monkeypatch, value):
    annual = replace(_annual_position_for_bundle(), hicbc_charge_percentage=value)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_hicbc_percentage_int_subclass_fails(monkeypatch):
    class _IntSubclass(int):
        pass

    annual = replace(_annual_position_for_bundle(), hicbc_charge_percentage=_IntSubclass(50))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("value", [42, "", "attacker", True, b"person"])
def test_annual_result_liable_person_invalid_fails(monkeypatch, value):
    annual = replace(_annual_position_for_bundle(), hicbc_liable_person=value)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("value", [
    ["income_tax", "class_4_ni"],
    ("income_tax", "class_4_ni", "trade"),
    ("class_4_ni", "income_tax"),
    ("income_tax", "class_4_ni", "hicbc", "extra"),
    ("income_tax", 42),
])
def test_annual_result_included_families_invalid_fails(monkeypatch, value):
    annual = replace(_annual_position_for_bundle(), included_families=value)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_included_families_tuple_subclass_fails(monkeypatch):
    class _TupleSubclass(tuple):
        pass

    annual = replace(_annual_position_for_bundle(),
                     included_families=_TupleSubclass(("income_tax", "class_4_ni")))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("value", [
    ["hicbc"],
    (42,),
    ("trade",),
    ("hicbc", "hicbc"),
])
def test_annual_result_unsupported_families_invalid_fails(monkeypatch, value):
    annual = replace(_annual_position_for_bundle(), unsupported_families=value)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


@pytest.mark.parametrize("value", [
    ["paye_reconciliation_not_performed", "student_loan_not_calculated"],
    (42,),
    ("student_loan_not_calculated", "paye_reconciliation_not_performed"),
    ("paye_reconciliation_not_performed", "student_loan_not_calculated", "bogus"),
    ("paye_reconciliation_not_performed", "student_loan_not_calculated",
     "paye_reconciliation_not_performed"),
])
def test_annual_result_limitations_invalid_fails(monkeypatch, value):
    annual = replace(_annual_position_for_bundle(), limitations=value)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_extra_field_fails(monkeypatch):
    annual = _annual_position_for_bundle()
    object.__setattr__(annual, "forged_extra_field", 1)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_result_invalid")


def test_annual_result_missing_field_fails(monkeypatch):
    source = _annual_position_for_bundle()
    forged = AnnualPositionResult.__new__(AnnualPositionResult)
    for name, value in vars(source).items():
        if name != "total_liability":
            object.__setattr__(forged, name, value)
    _assert_annual_position_field_fails(monkeypatch, forged,
                                        code="annual_position_result_invalid")


def test_annual_result_validation_exception_collapses_categorically(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _annual_position_for_bundle()

    def hostile(value):
        raise RuntimeError("DOWNSTREAM-VALIDATION-SECRET")

    monkeypatch.setattr(handoff, "_validate_annual_percentage", hostile)
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: annual)
    inputs, observations = _trade_bundle()
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"
    assert "DOWNSTREAM-VALIDATION-SECRET" not in str(exc.value)
    assert "RuntimeError" not in str(exc.value)


def test_annual_result_validation_keyboard_interrupt_not_swallowed(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _annual_position_for_bundle()

    def hostile(value):
        raise KeyboardInterrupt

    monkeypatch.setattr(handoff, "_validate_annual_percentage", hostile)
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: annual)
    inputs, observations = _trade_bundle()
    with pytest.raises(KeyboardInterrupt):
        _calc(BusinessType.TRADE, inputs, observations)


def test_annual_result_validation_system_exit_not_swallowed(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _annual_position_for_bundle()

    def hostile(value):
        raise SystemExit(1)

    monkeypatch.setattr(handoff, "_validate_annual_percentage", hostile)
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: annual)
    inputs, observations = _trade_bundle()
    with pytest.raises(SystemExit):
        _calc(BusinessType.TRADE, inputs, observations)


def test_genuine_annual_result_validated_unchanged():
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _annual_position_for_bundle()
    assert handoff._validate_annual_position_result(annual) is annual


# ── Annual-result semantic correction (monetary, ordering, coherence) ─────────

_ANNUAL_NON_NEGATIVE_MONEY_FIELDS = tuple(
    field
    for field in (_ANNUAL_REQUIRED_MONEY_FIELDS + _ANNUAL_OPTIONAL_MONEY_FIELDS)
    if field != "foreign_property_profit"
)

_SUB_PENNY_MONEY_FIELDS = (
    "adjusted_net_income", "class_4_ni", "total_liability", "foreign_property_profit",
)

_EXTREME_MONEY_FIELDS = (
    "adjusted_net_income", "income_tax_before_limitations", "total_liability",
    "foreign_property_profit",
)


def _genuine_annual_position(facts):
    return calculate_annual_position(facts, "2026/27")


def _calculated_annual_position():
    return _genuine_annual_position({
        "employment_income": "50000",
        "blind_persons_allowance_entitled": False,
        "blind_persons_allowance_transferred_in": "0",
        "blind_persons_allowance_transferred_out": "0",
    })


@pytest.mark.parametrize("field", _ANNUAL_NON_NEGATIVE_MONEY_FIELDS)
def test_annual_result_negative_money_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: Decimal("-1.00")})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _SUB_PENNY_MONEY_FIELDS)
def test_annual_result_sub_penny_money_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: Decimal("0.001")})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


@pytest.mark.parametrize("field", _EXTREME_MONEY_FIELDS)
def test_annual_result_extreme_unrepresentable_money_fails(monkeypatch, field):
    annual = replace(_annual_position_for_bundle(), **{field: Decimal("1e999999")})
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_monetary_invalid")


def test_annual_result_signed_foreign_property_profit_accepted():
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "2000",
    })
    assert annual.foreign_property_profit < 0
    assert handoff._validate_annual_position_result(annual) is annual


def test_annual_result_calculated_requires_total_liability(monkeypatch):
    annual = replace(_calculated_annual_position(), total_liability=None)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_unsupported_rule_requires_unsupported_family(monkeypatch):
    annual = replace(_annual_position_for_bundle(), calculation_status="unsupported_rule")
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_hicbc_percentage_without_result_fails(monkeypatch):
    annual = replace(_annual_position_for_bundle(), hicbc_charge_percentage=50)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_hicbc_charge_without_liable_person_fails(monkeypatch):
    annual = replace(_annual_position_for_bundle(), hicbc=Decimal("1.00"))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_person_hicbc_mismatched_household_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "has_relevant_partner": False,
    })
    annual = replace(annual, hicbc=Decimal("999.00"))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_partner_hicbc_non_zero_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "person_adjusted_net_income": "60000",
        "partner_adjusted_net_income": "70000",
        "has_relevant_partner": True,
    })
    annual = replace(annual, hicbc=Decimal("1.00"))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_partner_hicbc_without_partner_limitation_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "person_adjusted_net_income": "60000",
        "partner_adjusted_net_income": "70000",
        "has_relevant_partner": True,
    })
    annual = replace(annual, limitations=annual.limitations[:-1])
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_hicbc_unsupported_but_included_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "person_adjusted_net_income": "60000",
        "partner_adjusted_net_income": "60000",
        "has_relevant_partner": True,
    })
    annual = replace(annual, included_families=("income_tax", "class_4_ni", "hicbc"))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_no_payment_with_hicbc_facts_incomplete_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_applicable": True,
    })
    annual = replace(annual, limitations=annual.limitations + ("no_child_benefit_payments_to_charge",))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_no_payment_with_non_zero_benefit_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "has_relevant_partner": False,
    })
    annual = replace(annual, limitations=annual.limitations + ("no_child_benefit_payments_to_charge",))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_genuine_hicbc_shapes_validated():
    import reserved.engines.accounting_tax_handoff as handoff

    shapes = {
        "person": {
            "employment_income": "60000",
            "child_benefit_payments_received": "2000",
            "has_relevant_partner": False,
        },
        "partner_higher": {
            "employment_income": "60000",
            "child_benefit_payments_received": "2000",
            "person_adjusted_net_income": "60000",
            "partner_adjusted_net_income": "70000",
            "has_relevant_partner": True,
        },
        "partner_claimant": {
            "employment_income": "60000",
            "child_benefit_payments_received": "2000",
            "person_adjusted_net_income": "60000",
            "partner_adjusted_net_income": "60000",
            "child_benefit_claimant": "partner",
            "has_relevant_partner": True,
        },
        "ambiguous": {
            "employment_income": "60000",
            "child_benefit_payments_received": "2000",
            "person_adjusted_net_income": "60000",
            "partner_adjusted_net_income": "60000",
            "has_relevant_partner": True,
        },
        "facts_incomplete": {
            "employment_income": "60000",
            "child_benefit_applicable": True,
        },
        "none": {"employment_income": "60000"},
        "no_payment_person": {
            "employment_income": "60000",
            "child_benefit_payments_received": "0",
            "child_benefit_entitlement_retained": True,
            "has_relevant_partner": False,
        },
        "no_payment_ambiguous": {
            "employment_income": "60000",
            "child_benefit_payments_received": "0",
            "child_benefit_entitlement_retained": True,
            "person_adjusted_net_income": "60000",
            "partner_adjusted_net_income": "60000",
            "has_relevant_partner": True,
        },
    }
    for facts in shapes.values():
        annual = _genuine_annual_position(facts)
        assert handoff._validate_annual_position_result(annual) is annual


def test_annual_result_genuine_multi_family_order_validated():
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _genuine_annual_position({
        "employment_income": "50000",
        "residential_finance_costs": "1000",
        "individual_landlord": True,
        "residential_property": True,
        "foreign_tax_paid": "500",
        "child_benefit_payments_received": "2000",
        "person_adjusted_net_income": "50000",
        "partner_adjusted_net_income": "50000",
        "has_relevant_partner": True,
    })
    assert annual.unsupported_families == (
        "residential_finance_cost_reduction", "foreign_tax_credit_relief", "hicbc",
    )
    assert handoff._validate_annual_position_result(annual) is annual


def test_annual_result_unsupported_families_reorder_fails(monkeypatch):
    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "2000",
        "foreign_tax_paid": "500",
    })
    assert annual.unsupported_families == (
        "foreign_property_loss_treatment", "foreign_tax_credit_relief",
    )
    annual = replace(annual, unsupported_families=(
        "foreign_tax_credit_relief", "foreign_property_loss_treatment",
    ))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_limitations_later_stage_before_earlier_fails(monkeypatch):
    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
        "uk_resident": False,
    })
    annual = replace(annual, limitations=(
        "paye_reconciliation_not_performed",
        "student_loan_not_calculated",
        "blind_persons_allowance_facts_incomplete",
        "outside_supported_uk_resident_case",
    ))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_residence_alternatives_mutually_exclusive_fails(monkeypatch):
    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
        "uk_resident": False,
    })
    annual = replace(annual, limitations=(
        "paye_reconciliation_not_performed",
        "student_loan_not_calculated",
        "residence_facts_incomplete",
        "outside_supported_uk_resident_case",
        "blind_persons_allowance_facts_incomplete",
    ))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


# ── Reverse-coherence regressions (status, foreign-property sign, HICBC) ────────

def test_annual_result_calculated_forged_to_insufficient_fails(monkeypatch):
    annual = replace(_calculated_annual_position(),
                     calculation_status="insufficient_facts",
                     total_liability=None)
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_genuine_insufficient_facts_shapes_validated():
    import reserved.engines.accounting_tax_handoff as handoff

    shapes = (
        {"employment_income": "60000"},  # BPA absent only
        {"employment_income": "60000", "child_benefit_applicable": True},
        {"employment_income": "60000", "child_benefit_payments_received": "2000",
         "person_adjusted_net_income": "60000",
         "partner_adjusted_net_income": "60000", "has_relevant_partner": True},
    )
    for facts in shapes:
        annual = _genuine_annual_position(facts)
        assert annual.calculation_status == "insufficient_facts"
        assert handoff._validate_annual_position_result(annual) is annual


def test_annual_result_negative_foreign_profit_without_loss_marker_fails(monkeypatch):
    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "2000",
    })
    assert annual.foreign_property_profit < 0
    annual = replace(annual,
                     unsupported_families=(),
                     limitations=("paye_reconciliation_not_performed",
                                  "student_loan_not_calculated",
                                  "blind_persons_allowance_facts_incomplete"),
                     calculation_status="insufficient_facts")
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_positive_foreign_profit_without_residence_marker_fails(monkeypatch):
    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
    })
    assert annual.foreign_property_profit > 0
    assert "foreign_property_residence" in annual.unsupported_families
    annual = replace(annual,
                     unsupported_families=(),
                     limitations=("paye_reconciliation_not_performed",
                                  "student_loan_not_calculated",
                                  "blind_persons_allowance_facts_incomplete"))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_genuine_foreign_property_shapes_validated():
    import reserved.engines.accounting_tax_handoff as handoff

    shapes = {
        "negative_loss": {
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "2000",
        },
        "residence_incomplete": {
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "0",
        },
        "outside_uk_resident": {
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "0",
            "uk_resident": False,
        },
        "zero": {
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "1000",
        },
        "positive_uk_resident": {
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "0",
            "uk_resident": True,
        },
    }
    for facts in shapes.values():
        annual = _genuine_annual_position(facts)
        assert handoff._validate_annual_position_result(annual) is annual


def test_annual_result_no_hicbc_with_partner_marker_fails(monkeypatch):
    annual = _genuine_annual_position({"employment_income": "60000"})
    assert annual.hicbc_liable_person is None
    annual = replace(annual, limitations=annual.limitations +
                     ("hicbc_liability_belongs_to_higher_ani_partner",))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")


def test_annual_result_person_liable_with_partner_marker_fails(monkeypatch):
    annual = _genuine_annual_position({
        "employment_income": "60000",
        "child_benefit_payments_received": "2000",
        "has_relevant_partner": False,
    })
    assert annual.hicbc_liable_person == "person"
    annual = replace(annual, limitations=annual.limitations +
                     ("hicbc_liability_belongs_to_higher_ani_partner",))
    _assert_annual_position_field_fails(monkeypatch, annual,
                                        code="annual_position_field_invalid")



# ── Complete timestamp normalization guard ─────────────────────────────────────

def test_hostile_utcoffset_runtime_error_fails_without_leakage():
    class HostileTz(tzinfo):
        def utcoffset(self, dt):
            raise RuntimeError("HOSTILE-TZ-SECRET")

    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       datetime(2026, 8, 3, 10, 0, 0, tzinfo=HostileTz()))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"
    assert "HOSTILE-TZ-SECRET" not in str(exc.value)
    assert "RuntimeError" not in str(exc.value)


def test_non_timedelta_utc_offset_fails():
    class BadOffsetTz(tzinfo):
        def utcoffset(self, dt):
            return 3600  # int, not timedelta

    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       datetime(2026, 8, 3, 10, 0, 0, tzinfo=BadOffsetTz()))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"


def test_out_of_range_utc_offset_fails():
    class HugeOffsetTz(tzinfo):
        def utcoffset(self, dt):
            return timedelta(days=2)

    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       datetime(2026, 8, 3, 10, 0, 0, tzinfo=HugeOffsetTz()))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"


def test_datetime_min_positive_offset_underflow_fails():
    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       datetime.min.replace(tzinfo=timezone(timedelta(hours=1))))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"


def test_datetime_max_negative_offset_overflow_fails():
    o1 = _observation("o1")
    object.__setattr__(o1.provenance, "retrieved_at",
                       datetime.max.replace(tzinfo=timezone(timedelta(hours=-1))))
    i1 = _tax_input(input_id="i1", economic_event_id="e1", evidence_observation_ids=("o1",))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, [i1], [o1])
    assert exc.value.code == "observation_retrieved_at_invalid"


# ── Contextual residence coherence regressions ────────────────────────────────

def test_annual_result_uk_resident_foreign_profit_with_pension_not_rejected():
    import reserved.engines.accounting_tax_handoff as handoff

    for pension in ("600", "1000"):
        annual = _genuine_annual_position({
            "foreign_property_gross_receipts": "1000",
            "foreign_property_allowable_expenses": "0",
            "uk_resident": True,
            "gross_ras_pension": pension,
        })
        assert annual.foreign_property_profit == Decimal("1000.00")
        assert annual.adjusted_net_income < annual.foreign_property_profit
        assert handoff._validate_annual_position_result(annual) is annual


@pytest.mark.parametrize("profit", [Decimal("0.00"), Decimal("1000.00")])
def test_annual_result_non_negative_foreign_profit_with_loss_marker_fails(profit):
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "2000",
    })
    annual = replace(annual, foreign_property_profit=profit)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        handoff._validate_annual_position_result(annual)
    assert exc.value.code == "annual_position_field_invalid"


def test_annual_result_zero_foreign_profit_with_residence_marker_fails():
    import reserved.engines.accounting_tax_handoff as handoff

    annual = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
    })
    assert annual.foreign_property_profit > 0
    annual = replace(annual, foreign_property_profit=Decimal("0.00"))
    with pytest.raises(AccountingTaxHandoffError) as exc:
        handoff._validate_annual_position_result(annual)
    assert exc.value.code == "annual_position_field_invalid"


def test_foreign_property_handoff_rejects_forged_residence_stripped(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _property_bundle("10000", "2000")
    genuine = _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
    assert "foreign_property_residence" in genuine.annual_position.unsupported_families
    forged = replace(genuine.annual_position,
                     unsupported_families=(),
                     limitations=("paye_reconciliation_not_performed",
                                  "student_loan_not_calculated",
                                  "blind_persons_allowance_facts_incomplete"))
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: forged)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"


def test_foreign_property_handoff_rejects_forged_loss_marker_stripped(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _property_bundle("1000", "2000")
    genuine = _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
    assert "foreign_property_loss_treatment" in genuine.annual_position.unsupported_families
    forged = replace(genuine.annual_position,
                     unsupported_families=(),
                     limitations=("paye_reconciliation_not_performed",
                                  "student_loan_not_calculated",
                                  "blind_persons_allowance_facts_incomplete"),
                     calculation_status="insufficient_facts")
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: forged)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"


def test_foreign_property_handoff_rejects_forged_outside_uk_residence(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _property_bundle("10000", "2000")
    forged = _genuine_annual_position({
        "foreign_property_gross_receipts": "10000",
        "foreign_property_allowable_expenses": "2000",
        "uk_resident": False,
    })
    assert "outside_supported_uk_resident_case" in forged.limitations
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: forged)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"


def test_trade_handoff_rejects_forged_foreign_property_profit(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _trade_bundle()
    forged = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
    })
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: forged)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.TRADE, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"


def test_uk_property_handoff_rejects_forged_foreign_property_profit(monkeypatch):
    import reserved.engines.accounting_tax_handoff as handoff

    inputs, observations = _property_bundle("10000", "2000")
    forged = _genuine_annual_position({
        "foreign_property_gross_receipts": "1000",
        "foreign_property_allowable_expenses": "0",
    })
    monkeypatch.setattr(handoff, "calculate_annual_position",
                        lambda facts, tax_year: forged)
    with pytest.raises(AccountingTaxHandoffError) as exc:
        _calc(BusinessType.UK_PROPERTY, inputs, observations)
    assert exc.value.code == "annual_position_field_invalid"


def test_foreign_property_handoff_genuine_shapes_accepted():
    for receipts, expenses in (
        ("1000", "2000"),   # negative loss
        ("10000", "2000"),  # positive residence-incomplete
        ("1000", "1000"),   # zero
    ):
        inputs, observations = _property_bundle(receipts, expenses)
        result = _calc(BusinessType.FOREIGN_PROPERTY, inputs, observations)
        assert isinstance(result.annual_position, AnnualPositionResult)
