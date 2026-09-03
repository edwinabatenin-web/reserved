"""Adversarial acceptance for the customer MTD scope indication."""

from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal
import pickle

import pytest

from reserved.engines import mtd_readiness as engine
from reserved.engines.mtd_readiness import (
    IncomeKind,
    IncomeSource,
    MtdReadiness,
    MtdStatus,
)
from reserved.services.mtd_scope_indication import (
    CONTRACT_VERSION,
    FEATURE_LABEL,
    MtdScopeCompleteness,
    MtdScopeIndication,
    as_mtd_scope_mapping,
    present_mtd_scope_indication,
)


COMPLETE = MtdScopeCompleteness(True, True, True, True, True)


def source(
    source_id="trade",
    kind=IncomeKind.SOLE_TRADE,
    gross=Decimal("0.00"),
    *,
    business_id=None,
    complete=True,
):
    return IncomeSource(source_id, kind, gross, business_id, complete)


def present(
    sources=(),
    *,
    year="2024-25",
    completeness=COMPLETE,
    registered=None,
    exempt=None,
):
    return present_mtd_scope_indication(
        sources,
        assessment_tax_year=year,
        completeness=completeness,
        registered_for_self_assessment=registered,
        exemption_applies=exempt,
    )


def mapping(value):
    return as_mtd_scope_mapping(value)


def assert_more_information(value):
    result = mapping(value)
    assert result["feature_label"] == FEATURE_LABEL
    assert result["headline"] == "More information needed"
    assert result["information_complete"] is False
    assert result["filing_action_available"] is False
    assert result["qualifying_income"] is None
    assert result["distance_from_threshold"] is None


@pytest.mark.parametrize(
    "year,threshold,mandatory_from,effective_start",
    [
        ("2024-25", Decimal("50000"), "2026-27", "2026-04-06"),
        ("2025-26", Decimal("30000"), "2027-28", "2027-04-06"),
        ("2026-27", Decimal("20000"), "2028-29", "2028-04-06"),
    ],
)
def test_exact_threshold_is_material_and_exposes_rule_derived_start_date(
    year, threshold, mandatory_from, effective_start
):
    result = mapping(present((source(gross=threshold),), year=year))
    assert result["contract_version"] == CONTRACT_VERSION
    assert result["feature_label"] == "Could Making Tax Digital apply to you?"
    assert result["headline"] == "Worth reviewing"
    assert result["summary"] == "Making Tax Digital may apply in a future tax year."
    assert result["assessment_tax_year"] == year
    assert result["mandatory_from_tax_year"] == mandatory_from
    assert result["effective_start_date"] == effective_start
    assert result["qualifying_income"] == threshold.quantize(Decimal("0.01"))
    assert result["threshold"].as_tuple() == threshold.as_tuple()
    assert result["distance_from_threshold"] == Decimal("0.00")


@pytest.mark.parametrize(
    "year,threshold",
    [
        ("2024-25", Decimal("50000")),
        ("2025-26", Decimal("30000")),
        ("2026-27", Decimal("20000")),
    ],
)
def test_one_penny_over_each_threshold_is_worth_reviewing(year, threshold):
    result = mapping(
        present(
            (source(gross=threshold + Decimal("0.01")),),
            year=year,
            registered=True,
            exempt=False,
        )
    )
    assert result["headline"] == "Worth reviewing"
    assert result["summary"] == "Making Tax Digital may apply in a future tax year."
    assert result["distance_from_threshold"] == Decimal("-0.01")
    assert result["filing_action_available"] is False


def test_explicit_completeness_is_required_before_empty_inventory_means_zero():
    unknown = present_mtd_scope_indication(
        (), assessment_tax_year="2024-25", completeness=None
    )
    assert_more_information(unknown)
    assert mapping(unknown)["included_source_count"] is None

    confirmed = mapping(present(()))
    assert confirmed["headline"] == "Not currently indicated"
    assert confirmed["qualifying_income"] == Decimal("0.00")
    assert confirmed["included_source_count"] == 0
    assert confirmed["excluded_source_count"] == 0


@pytest.mark.parametrize("field", range(5))
@pytest.mark.parametrize("invalid", [False, None, 1])
def test_each_completeness_confirmation_must_be_exact_true(field, invalid):
    values = [True, True, True, True, True]
    values[field] = invalid
    assert_more_information(present((source(),), completeness=MtdScopeCompleteness(*values)))


def test_completeness_subtype_and_post_construction_mutation_fail_closed(monkeypatch):
    class CompletenessSubtype(MtdScopeCompleteness):
        pass

    assert_more_information(
        present((source(),), completeness=CompletenessSubtype(True, True, True, True, True))
    )
    facts = MtdScopeCompleteness(True, True, True, True, True)
    object.__setattr__(facts, "cessation_facts_complete", False)
    monkeypatch.setattr(
        MtdScopeCompleteness,
        "cessation_facts_complete",
        property(lambda self: True),
    )
    assert_more_information(present((source(),), completeness=facts))


def test_multiple_sources_use_safe_categories_and_counts_not_internal_ids():
    sources = (
        source("opaque:trade:alpha", IncomeKind.SOLE_TRADE, Decimal("12000.00"), business_id="secret:biz:a"),
        source("opaque:trade:beta", IncomeKind.SOLE_TRADE, Decimal("9000.00"), business_id="secret:biz:b"),
        source("opaque:uk", IncomeKind.UK_PROPERTY, Decimal("5000.00"), business_id="secret:uk"),
        source("opaque:foreign", IncomeKind.FOREIGN_PROPERTY, Decimal("5000.00"), business_id="secret:foreign"),
        source("opaque:paye", IncomeKind.PAYE_EMPLOYMENT, Decimal("80000.00")),
        source("opaque:dividend", IncomeKind.DIVIDENDS, Decimal("10000.00")),
        source("opaque:savings", IncomeKind.SAVINGS_INTEREST, Decimal("5000.00")),
        source("opaque:gains", IncomeKind.CAPITAL_GAINS, Decimal("50000.00")),
    )
    result = mapping(
        present(sources, year="2025-26", registered=True, exempt=False)
    )
    assert result["qualifying_income"] == Decimal("31000.00")
    assert result["included_source_categories"] == (
        "Self-employment", "UK property", "Foreign property"
    )
    assert result["included_source_count"] == 4
    assert result["included_business_count"] == 4
    assert result["excluded_source_categories"] == (
        "Employment income", "Dividend income", "Savings interest", "Capital gains"
    )
    assert result["excluded_source_count"] == 4
    projection_text = repr(dict(result))
    assert "opaque:" not in projection_text
    assert "secret:" not in projection_text
    assert result["gross_income_basis"] == (
        "The threshold uses qualifying gross income before expenses."
    )
    assert result["determination_basis"] == (
        "This is a local planning indication, not HMRC's formal determination."
    )


def test_below_material_position_is_qualified_and_never_promises_exclusion():
    result = mapping(present((source(gross=Decimal("10000.00")),)))
    assert result["headline"] == "Not currently indicated"
    assert "does not currently indicate" in result["summary"]
    assert "not a promise of exemption or future non-applicability" in result["summary"]
    assert result["information_complete"] is True


def test_over_threshold_unregistered_nonexempt_position_is_still_material():
    result = mapping(
        present(
            (source(gross=Decimal("50000.01")),),
            registered=False,
            exempt=False,
        )
    )
    assert result["headline"] == "Worth reviewing"
    assert result["summary"] == "Making Tax Digital may apply in a future tax year."


@pytest.mark.parametrize("registered", [True, False])
def test_confirmed_exemption_keeps_over_threshold_position_qualified(registered):
    result = mapping(
        present(
            (source(gross=Decimal("50000.01")),),
            registered=registered,
            exempt=True,
        )
    )
    assert result["headline"] == "Not currently indicated"
    assert "not a promise" in result["summary"]
    assert result["qualifying_income"] == Decimal("50000.01")


@pytest.mark.parametrize(
    "sources,registered,exempt",
    [
        ((source(gross=None),), None, None),
        ((source(gross=Decimal("51000.00"), complete=False),), True, False),
        ((source(gross=Decimal("51000.00")),), None, None),
        ((source(gross=Decimal("51000.00")),), True, None),
    ],
)
def test_incomplete_or_unknown_material_facts_hide_partial_point_conclusions(
    sources, registered, exempt
):
    result = mapping(present(sources, registered=registered, exempt=exempt))
    assert result["headline"] == "More information needed"
    assert result["qualifying_income"] is None
    assert result["distance_from_threshold"] is None
    assert result["threshold"] == Decimal("50000")
    assert result["included_source_categories"] == ("Self-employment",)


@pytest.mark.parametrize(
    "sources",
    [
        [],
        iter(()),
        (source("duplicate"), source("duplicate")),
        (source("one", business_id="same"), source("two", business_id="same")),
        (source("bad id", gross=Decimal("1.00")),),
        (source(gross=Decimal("NaN")),),
        (source(gross=Decimal("Infinity")),),
        (source(gross=Decimal("-1.00")),),
        (source(gross=True),),
        (source(complete=1),),
    ],
)
def test_invalid_input_graphs_fail_to_generic_non_actionable_copy(sources):
    value = present_mtd_scope_indication(
        sources,
        assessment_tax_year="2024-25",
        completeness=COMPLETE,
        registered_for_self_assessment=True,
        exemption_applies=False,
    )
    result = mapping(value)
    assert_more_information(value)
    assert result["assessment_tax_year"] is None
    assert result["threshold"] is None
    assert result["included_source_count"] is None


def test_source_subclass_and_hostile_field_are_rejected_without_hooks():
    calls = []

    class HostileSource(IncomeSource):
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("hook dispatched")

    assert_more_information(present((object.__new__(HostileSource),)))

    class HostileAmount:
        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("hook dispatched")

        def __str__(self):
            calls.append("str")
            raise AssertionError("hook dispatched")

    assert_more_information(present((source(gross=HostileAmount()),)))
    assert calls == []


def test_low_level_missing_or_extra_source_state_is_rejected():
    missing = object.__new__(IncomeSource)
    object.__setattr__(missing, "source_id", "trade")
    object.__setattr__(missing, "kind", IncomeKind.SOLE_TRADE)
    object.__setattr__(missing, "gross_income", Decimal("100.00"))
    object.__setattr__(missing, "business_id", None)
    assert_more_information(present((missing,)))

    extra = source(gross=Decimal("100.00"))
    object.__setattr__(extra, "attacker_state", "forged")
    assert_more_information(present((extra,)))


def test_structurally_valid_source_is_detached_before_engine_use():
    original = source(gross=Decimal("50000.01"))
    copied = pickle.loads(pickle.dumps(copy.deepcopy(original)))
    result = present((copied,), registered=True, exempt=False)
    object.__setattr__(copied, "gross_income", Decimal("0.00"))
    assert mapping(result)["qualifying_income"] == Decimal("50000.01")


@pytest.mark.parametrize(
    "year,registered,exempt",
    [
        ("2027-28", None, None),
        ("2024/25", None, None),
        (1, None, None),
        ("2024-25", 1, None),
        ("2024-25", None, 0),
    ],
)
def test_unsupported_period_or_nonexact_eligibility_facts_fail_closed(
    year, registered, exempt
):
    value = present(
        (source(gross=Decimal("50001.00")),),
        year=year,
        registered=registered,
        exempt=exempt,
    )
    assert_more_information(value)
    assert mapping(value)["assessment_tax_year"] is None


def test_engine_rule_or_result_tampering_cannot_emit_partial_conclusion(monkeypatch):
    captured = present_mtd_scope_indication
    rule = engine.MTD_THRESHOLD_RULES["2024-25"]
    monkeypatch.setitem(
        engine.MTD_THRESHOLD_RULES,
        "2024-25",
        replace(rule, threshold=Decimal("1")),
    )
    value = captured(
        (source(gross=Decimal("50001.00")),),
        assessment_tax_year="2024-25",
        completeness=COMPLETE,
        registered_for_self_assessment=True,
        exemption_applies=False,
    )
    assert_more_information(value)


def test_engine_result_representation_is_revalidated(monkeypatch):
    real_init = MtdReadiness.__init__

    def forged_init(self, **values):
        real_init(self, **values)
        object.__setattr__(self, "qualifying_income", Decimal("50001"))
        object.__setattr__(self, "distance_from_threshold", Decimal("-1"))

    monkeypatch.setattr(MtdReadiness, "__init__", forged_init)
    assert_more_information(
        present(
            (source(gross=Decimal("50001.00")),),
            registered=True,
            exempt=False,
        )
    )


def test_forged_expected_next_status_is_not_accepted(monkeypatch):
    real_init = MtdReadiness.__init__

    def forged_init(self, **values):
        real_init(self, **values)
        object.__setattr__(self, "status", MtdStatus.EXPECTED_NEXT_TAX_YEAR)

    monkeypatch.setattr(MtdReadiness, "__init__", forged_init)
    value = present((source(gross=Decimal("45000.00")),))
    assert_more_information(value)
    assert mapping(value)["assessment_tax_year"] is None


def test_module_global_rebinding_cannot_change_boundary_or_projection(monkeypatch):
    import reserved.services.mtd_scope_indication as module

    captured_present = present_mtd_scope_indication
    captured_mapping = as_mtd_scope_mapping
    for name, replacement in {
        "CONTRACT_VERSION": "forged",
        "FEATURE_LABEL": "forged",
        "MtdScopeCompleteness": object(),
        "Decimal": object(),
        "MappingProxyType": object(),
        "weakref": object(),
        "_engine": object(),
        "MtdScopeIndication": object(),
        "present_mtd_scope_indication": lambda *args, **kwargs: None,
        "as_mtd_scope_mapping": lambda value: {"headline": "forged"},
        "type": lambda value: object,
        "object": object(),
        "str": object(),
        "int": object(),
        "float": object(),
        "bool": object(),
        "tuple": object(),
        "dict": object(),
        "len": lambda value: 0,
        "all": lambda values: False,
        "any": lambda values: True,
        "set": lambda values=(): set(),
        "sum": lambda values, start=0: start,
        "zip": lambda *values: (),
        "ValueError": RuntimeError,
        "TypeError": RuntimeError,
    }.items():
        monkeypatch.setattr(module, name, replacement, raising=False)
    value = captured_present(
        (source(gross=Decimal("50000.01")),),
        assessment_tax_year="2024-25",
        completeness=COMPLETE,
        registered_for_self_assessment=True,
        exemption_applies=False,
    )
    result = captured_mapping(value)
    assert result["feature_label"] == FEATURE_LABEL
    assert result["headline"] == "Worth reviewing"


def test_opaque_handle_has_no_raw_customer_fields_and_cannot_be_reconstructed():
    value = present(
        (source(gross=Decimal("50000.01")),), registered=True, exempt=False
    )
    with pytest.raises(AttributeError):
        _ = value.headline
    with pytest.raises(AttributeError):
        object.__setattr__(value, "headline", "forged")
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(value)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(value)
    with pytest.raises(TypeError, match="cannot be reconstructed"):
        pickle.dumps(value)
    with pytest.raises(TypeError, match="private"):
        MtdScopeIndication()
    with pytest.raises(TypeError):
        mapping(value)["headline"] = "changed outside"
    detached = dict(mapping(value))
    detached["headline"] = "changed outside"
    assert mapping(value)["headline"] == "Worth reviewing"


def test_captured_projector_ignores_public_class_method_rebinding(monkeypatch):
    value = present((source(gross=Decimal("45000.00")),))
    captured = as_mtd_scope_mapping
    monkeypatch.setattr(
        MtdScopeIndication,
        "as_mapping",
        lambda self: {"headline": "forged"},
        raising=False,
    )
    assert captured(value)["headline"] == "Worth reviewing"


def test_low_level_reconstruction_and_hostile_equality_never_gain_validity():
    valid = present(())
    forged = object.__new__(MtdScopeIndication)
    with pytest.raises(ValueError, match="valid live presentation"):
        as_mtd_scope_mapping(forged)

    calls = []

    class Hostile(MtdScopeIndication):
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("hook dispatched")

    hostile = object.__new__(Hostile)
    with pytest.raises(TypeError, match="type is invalid"):
        valid != hostile
    assert calls == []


def test_customer_mapping_contains_only_approved_safe_copy():
    result = mapping(
        present(
            (source(gross=Decimal("50000.01")),),
            registered=True,
            exempt=False,
        )
    )
    assert tuple(result) == (
        "contract_version",
        "feature_label",
        "headline",
        "summary",
        "gross_income_basis",
        "determination_basis",
        "assessment_tax_year",
        "mandatory_from_tax_year",
        "effective_start_date",
        "qualifying_income",
        "threshold",
        "distance_from_threshold",
        "included_source_categories",
        "included_source_count",
        "included_business_count",
        "excluded_source_categories",
        "excluded_source_count",
        "information_complete",
        "filing_action_available",
    )
    customer_text = " ".join(str(value) for value in result.values()).lower()
    assert "mtd ready" not in customer_text
    assert "compatible software" not in customer_text
    assert "definitely applies" not in customer_text
    assert "tax advice" not in customer_text
    assert "provider" not in customer_text
    assert "submit" not in customer_text
    assert "file now" not in customer_text
