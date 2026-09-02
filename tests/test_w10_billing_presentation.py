"""Adversarial acceptance for the W10-S6A customer price-presentation boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
from dataclasses import FrozenInstanceError, asdict, fields, replace
from decimal import Decimal
from pathlib import Path

import pytest

import reserved.services.w10_billing_presentation as present
from reserved.services.w10_billing_presentation import (
    CONTRACT_VERSION,
    VAT_QUALIFICATION,
    PlanCard,
    W10BillingPresentation,
    present_w10_billing_presentation,
    w10_billing_presentation_authority_version,
    w10_billing_presentation_source_identity,
)
from reserved.billing.contracts import (
    AUTHORITY_VERSION,
    INITIAL_BILLING_AUTHORITY,
    BillingAuthority,
    Currency,
    PlanKey,
    PlanPrice,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE = (ROOT / "reserved" / "services" / "w10_billing_presentation.py").read_text()

_EXPECTED_LABELS = ("£29 per month", "£156 for six months", "£288 per year")


class _StringSubclass(str):
    """A hostile string subtype that compares equal to canonical text."""


class _TupleSubclass(tuple):
    """A hostile tuple subtype that compares equal to canonical tuples."""


class _AuthoritySubclass(BillingAuthority):
    """A billing authority subtype used to prove exact-type enforcement."""


class _PlanPriceSubclass(PlanPrice):
    """A plan-price subtype used to prove exact-type enforcement."""


class _InvalidPlanCardPicklePayload:
    def __reduce__(self):
        return (PlanCard, ("Free plan",))


class _InvalidViewPicklePayload:
    def __reduce__(self):
        return (
            W10BillingPresentation,
            (CONTRACT_VERSION, (PlanCard("£29 per month"),), VAT_QUALIFICATION),
        )


def _view() -> W10BillingPresentation:
    view = present_w10_billing_presentation(INITIAL_BILLING_AUTHORITY)
    assert view is not None
    return view


def _fresh_plans() -> tuple[PlanPrice, ...]:
    return tuple(
        PlanPrice(plan.key, plan.amount, plan.currency)
        for plan in INITIAL_BILLING_AUTHORITY.plans
    )


def _authority_values() -> dict:
    return {
        "decision_id": INITIAL_BILLING_AUTHORITY.decision_id,
        "decision_date": INITIAL_BILLING_AUTHORITY.decision_date,
        "authority_version": INITIAL_BILLING_AUTHORITY.authority_version,
        "launch_model": INITIAL_BILLING_AUTHORITY.launch_model,
        "plans": _fresh_plans(),
        "vat_price_statement": INITIAL_BILLING_AUTHORITY.vat_price_statement,
        "price_change_rule": INITIAL_BILLING_AUTHORITY.price_change_rule,
        "offer_capability_rule": INITIAL_BILLING_AUTHORITY.offer_capability_rule,
    }


def _forged_authority(*, drop: tuple[str, ...] = (), **changes) -> BillingAuthority:
    """Build a forged authority that bypasses the dataclass constructor validation."""
    values = _authority_values()
    values.update(changes)
    obj = object.__new__(BillingAuthority)
    for name, value in values.items():
        if name in drop:
            continue
        object.__setattr__(obj, name, value)
    return obj


def _forged_plan(*, drop: tuple[str, ...] = (), **changes) -> PlanPrice:
    """Build a forged plan that bypasses the dataclass constructor validation."""
    plan = INITIAL_BILLING_AUTHORITY.plans[0]
    values = {"key": plan.key, "amount": plan.amount, "currency": plan.currency}
    values.update(changes)
    obj = object.__new__(PlanPrice)
    for name, value in values.items():
        if name in drop:
            continue
        object.__setattr__(obj, name, value)
    return obj


def _expected_source_identity() -> str:
    components = (
        INITIAL_BILLING_AUTHORITY.decision_id,
        INITIAL_BILLING_AUTHORITY.decision_date.isoformat(),
        INITIAL_BILLING_AUTHORITY.authority_version,
        INITIAL_BILLING_AUTHORITY.launch_model.value,
        tuple(
            (plan.key.value, str(plan.amount.to_integral_value()), plan.currency.value)
            for plan in INITIAL_BILLING_AUTHORITY.plans
        ),
        INITIAL_BILLING_AUTHORITY.vat_price_statement.value,
        INITIAL_BILLING_AUTHORITY.price_change_rule.value,
        INITIAL_BILLING_AUTHORITY.offer_capability_rule.value,
    )
    payload = json.dumps(components, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"w10-billing-source:sha256-{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


# ── 1. Exact plan order, copy and VAT wording ────────────────────────────────

def test_presentation_has_exact_ordered_plan_cards_and_vat_copy():
    view = _view()
    assert view.contract_version == CONTRACT_VERSION
    assert tuple(card.label for card in view.plans) == _EXPECTED_LABELS
    assert view.vat_qualification == VAT_QUALIFICATION
    assert view.vat_qualification == "Prices include VAT where applicable."


def test_plan_cards_are_frozen_slotted_and_exact_strings():
    view = _view()
    assert hasattr(PlanCard, "__slots__")
    for card in view.plans:
        assert type(card) is PlanCard
        assert type(card.label) is str
        with pytest.raises((FrozenInstanceError, AttributeError)):
            card.label = "changed"  # type: ignore[misc]


# ── 2. Exact source authority/version binding ────────────────────────────────

def test_presentation_binds_exact_source_authority_and_version():
    view = _view()
    assert w10_billing_presentation_authority_version(view) == AUTHORITY_VERSION
    assert w10_billing_presentation_authority_version(view) == "FD-W10-001/2026-09-02/v1"
    assert w10_billing_presentation_source_identity(view) == _expected_source_identity()


def test_source_identity_is_deterministic_across_builds():
    assert w10_billing_presentation_source_identity(_view()) == (
        w10_billing_presentation_source_identity(_view())
    )


# ── 3. No derived savings/equivalents/VAT/offer/provider/action/access fields ─

def test_presentation_has_no_derived_or_provider_fields():
    view = _view()
    view_field_names = set(W10BillingPresentation.__slots__)
    card_field_names = {f.name for f in fields(PlanCard)}
    forbidden = {
        "savings",
        "monthly_equivalent",
        "yearly_equivalent",
        "equivalent",
        "discount",
        "discount_amount",
        "offer",
        "offer_price",
        "vat_rate",
        "vat_applies",
        "vat_amount",
        "tax_rate",
        "provider",
        "provider_id",
        "provider_product_id",
        "provider_price_id",
        "checkout",
        "checkout_url",
        "action",
        "access_granted",
        "grant_access",
        "entitlement",
        "renewal",
        "cancellation",
        "refund",
    }
    assert view_field_names.isdisjoint(forbidden)
    assert card_field_names.isdisjoint(forbidden)
    for name in forbidden:
        assert not hasattr(view, name)
        assert not hasattr(present, name)


# ── 4. Altered, missing, extra, duplicated or reordered plans fail closed ────

@pytest.mark.parametrize(
    "plans",
    [
        INITIAL_BILLING_AUTHORITY.plans[:-1],
        (INITIAL_BILLING_AUTHORITY.plans[0], INITIAL_BILLING_AUTHORITY.plans[1]),
        (
            INITIAL_BILLING_AUTHORITY.plans[0],
            INITIAL_BILLING_AUTHORITY.plans[0],
            INITIAL_BILLING_AUTHORITY.plans[2],
        ),
        INITIAL_BILLING_AUTHORITY.plans + (INITIAL_BILLING_AUTHORITY.plans[0],),
        tuple(reversed(INITIAL_BILLING_AUTHORITY.plans)),
        list(INITIAL_BILLING_AUTHORITY.plans),
        _TupleSubclass(INITIAL_BILLING_AUTHORITY.plans),
    ],
)
def test_altered_missing_extra_duplicated_reordered_or_mutable_plans_fail(plans):
    assert present_w10_billing_presentation(_forged_authority(plans=plans)) is None


def test_missing_authority_state_fails_closed():
    assert present_w10_billing_presentation(_forged_authority(drop=("plans",))) is None
    assert present_w10_billing_presentation(_forged_authority(drop=("decision_id",))) is None
    assert present_w10_billing_presentation(_forged_authority(drop=("authority_version",))) is None


# ── 5. Wrong amount, currency, term, version, VAT or offer rule fails closed ─

@pytest.mark.parametrize(
    "plan",
    [
        _forged_plan(amount=Decimal("30")),
        _forged_plan(amount=Decimal("29.01")),
        _forged_plan(amount=Decimal("156")),
        _forged_plan(key=PlanKey.SIX_MONTH),
        _forged_plan(key="monthly"),
        _forged_plan(currency="USD"),
        _forged_plan(currency="GBP"),
    ],
)
def test_wrong_amount_currency_or_term_fails_closed(plan):
    assert present_w10_billing_presentation(
        _forged_authority(plans=(plan, *INITIAL_BILLING_AUTHORITY.plans[1:]))
    ) is None


@pytest.mark.parametrize(
    "change",
    [
        {"authority_version": "latest"},
        {"authority_version": "FD-W10-001/2026-09-02/v2"},
        {"decision_id": "FD-W10-999"},
        {"decision_date": "2026-09-02"},
        {"vat_price_statement": "inclusive_of_vat_where_applicable"},
        {"price_change_rule": "changeable"},
        {"offer_capability_rule": True},
        {"launch_model": "paid_subscription"},
    ],
)
def test_forged_version_vat_offer_or_decision_identity_fails_closed(change):
    assert present_w10_billing_presentation(_forged_authority(**change)) is None


# ── 6. bool, float, non-finite, subclass, spoofed, mutable and mutated fail ──

@pytest.mark.parametrize(
    "amount",
    [True, False, 29, 29.0, "29", None, Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_bool_float_non_finite_and_non_decimal_amounts_fail_closed(amount):
    assert present_w10_billing_presentation(
        _forged_authority(plans=(_forged_plan(amount=amount), *INITIAL_BILLING_AUTHORITY.plans[1:]))
    ) is None


def test_subclass_authority_and_plan_fail_closed():
    subclassed_authority = object.__new__(_AuthoritySubclass)
    values = _authority_values()
    for name, value in values.items():
        object.__setattr__(subclassed_authority, name, value)
    assert present_w10_billing_presentation(subclassed_authority) is None

    subclassed_plan = object.__new__(_PlanPriceSubclass)
    plan = INITIAL_BILLING_AUTHORITY.plans[0]
    object.__setattr__(subclassed_plan, "key", plan.key)
    object.__setattr__(subclassed_plan, "amount", plan.amount)
    object.__setattr__(subclassed_plan, "currency", plan.currency)
    assert present_w10_billing_presentation(
        _forged_authority(plans=(subclassed_plan, *INITIAL_BILLING_AUTHORITY.plans[1:]))
    ) is None


def test_duck_typed_spoofed_authority_fails_closed():
    spoofed = type("SpoofedAuthority", (), {})()
    for name, value in _authority_values().items():
        setattr(spoofed, name, value)
    assert present_w10_billing_presentation(spoofed) is None


@pytest.mark.parametrize("value", [None, object(), {}, [], "FD-W10-001", 42, True])
def test_non_authority_inputs_fail_closed(value):
    assert present_w10_billing_presentation(value) is None


def test_partial_post_construction_nested_mutation_fails_closed():
    forged = _forged_authority()
    object.__setattr__(forged.plans[0], "amount", Decimal("30"))
    assert present_w10_billing_presentation(forged) is None


# ── 7. Equality/hash/copy/deepcopy/repr and reconstruction validate state ────

def test_valid_view_protocols_preserve_state_without_leaking_values():
    view = _view()
    assert view == view
    assert view != object()
    assert view != _StringSubclass("anything")
    assert hash(view) == hash(view)
    assert copy.copy(view) is view
    assert copy.deepcopy(view) is view
    assert repr(view) == "W10BillingPresentation(<validated>)"
    rebuilt = pickle.loads(pickle.dumps(view))
    assert rebuilt == view
    assert rebuilt is not view
    assert hash(rebuilt) == hash(view)
    with pytest.raises(TypeError, match="dataclass"):
        replace(view)
    assert replace(view.plans[0]) == view.plans[0]


def test_copy_and_pickle_reject_forged_invalid_plan_card():
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", "Free plan")
    for operation in (copy.copy, copy.deepcopy, pickle.dumps, lambda value: value.__reduce__()):
        with pytest.raises(ValueError, match="settled plan labels"):
            operation(forged)
    with pytest.raises(ValueError, match="settled plan labels"):
        pickle.loads(pickle.dumps(_InvalidPlanCardPicklePayload()))


def test_copy_and_pickle_reject_forged_invalid_view_state():
    view = _view()
    object.__setattr__(view, "plans", view.plans[:-1])
    for operation in (copy.copy, copy.deepcopy, pickle.dumps, hash, lambda value: value == _view()):
        with pytest.raises(ValueError):
            operation(view)
    with pytest.raises(ValueError):
        pickle.loads(pickle.dumps(_InvalidViewPicklePayload()))


def test_forged_internal_binding_mutation_fails_closed():
    view = _view()
    object.__setattr__(view, "_authority_version", "stale")
    for operation in (copy.copy, copy.deepcopy, pickle.dumps, hash):
        with pytest.raises(ValueError):
            operation(view)
    assert repr(view) == "W10BillingPresentation(<invalid-state>)"
    view = _view()
    object.__setattr__(view, "_source_identity", "w10-billing-source:sha256-" + "0" * 64)
    with pytest.raises(ValueError):
        w10_billing_presentation_source_identity(view)


def test_plan_card_rejects_string_subclass_and_undeclared_state():
    with pytest.raises(TypeError):
        PlanCard(_StringSubclass("£29 per month"))
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", _StringSubclass("£29 per month"))
    with pytest.raises(TypeError):
        copy.copy(forged)


def test_view_rejects_string_subclass_label_even_when_text_matches():
    view = _view()
    forged_card = object.__new__(PlanCard)
    object.__setattr__(forged_card, "label", _StringSubclass("£29 per month"))
    with pytest.raises(TypeError):
        W10BillingPresentation(
            CONTRACT_VERSION,
            (forged_card, *view.plans[1:]),
            VAT_QUALIFICATION,
        )


def test_view_is_immutable_via_normal_assignment_and_deletion():
    view = _view()
    with pytest.raises(AttributeError):
        view.contract_version = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del view.plans  # type: ignore[misc]


def test_plan_card_repr_is_categorical_and_never_discloses_values():
    card = _view().plans[0]
    assert repr(card) == "PlanCard(<validated>)"
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", "Pay £999 now")
    rendered = repr(forged)
    assert rendered == "PlanCard(<invalid-state>)"
    assert "£" not in rendered
    assert "999" not in rendered
    assert "Pay" not in rendered


def test_plan_card_equality_and_hash_validate_state_without_echoing_values():
    card = _view().plans[0]
    assert card == PlanCard(card.label)
    assert hash(card) == hash(PlanCard(card.label))
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", "Free plan")
    for operation in (hash, lambda value: value == card, lambda value: card == value):
        with pytest.raises(ValueError, match="settled plan labels"):
            operation(forged)


def test_plan_card_rejects_string_subclass_in_equality_and_hash():
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", _StringSubclass("£29 per month"))
    card = _view().plans[0]
    with pytest.raises(TypeError):
        hash(forged)
    with pytest.raises(TypeError):
        forged == card
    with pytest.raises(TypeError):
        card == forged


def test_view_asdict_and_replace_are_structurally_unavailable():
    view = _view()
    with pytest.raises(TypeError, match="dataclass"):
        asdict(view)
    with pytest.raises(TypeError, match="dataclass"):
        replace(view)


def test_view_iteration_mapping_conversion_and_vars_expose_no_authority():
    view = _view()
    with pytest.raises(TypeError):
        iter(view)
    with pytest.raises(TypeError):
        dict(view)
    with pytest.raises(TypeError):
        vars(view)


def test_mutated_view_cannot_be_laundered_by_replacement_or_reduction():
    view = _view()
    object.__setattr__(view, "_authority_version", "stale")
    with pytest.raises(TypeError, match="dataclass"):
        replace(view)
    with pytest.raises(TypeError, match="dataclass"):
        asdict(view)
    with pytest.raises(ValueError):
        pickle.dumps(view)
    with pytest.raises(ValueError):
        view.__reduce__()
    assert repr(view) == "W10BillingPresentation(<invalid-state>)"


def test_mutated_plan_card_cannot_be_laundered_by_replacement_or_reduction():
    forged = object.__new__(PlanCard)
    object.__setattr__(forged, "label", "Free plan")
    with pytest.raises(ValueError, match="settled plan labels"):
        replace(forged)
    with pytest.raises(ValueError, match="settled plan labels"):
        pickle.dumps(forged)
    with pytest.raises(ValueError, match="settled plan labels"):
        forged.__reduce__()


# ── 8. Invalid authority never produces a partial or price-bearing view ─────

def test_invalid_authority_never_produces_a_partial_or_price_bearing_view():
    for forged in (
        _forged_authority(plans=INITIAL_BILLING_AUTHORITY.plans[:-1]),
        _forged_authority(plans=tuple(reversed(INITIAL_BILLING_AUTHORITY.plans))),
        _forged_authority(authority_version="latest"),
        _forged_authority(
            plans=(
                _forged_plan(amount=Decimal("30")),
                *INITIAL_BILLING_AUTHORITY.plans[1:],
            ),
        ),
    ):
        assert present_w10_billing_presentation(forged) is None


def test_repr_is_categorical_and_never_leaks_prices_or_hostile_text():
    view = _view()
    assert repr(view) == "W10BillingPresentation(<validated>)"
    object.__setattr__(view, "vat_qualification", "Pay hostile amount £999 now")
    rendered = repr(view)
    assert rendered == "W10BillingPresentation(<invalid-state>)"
    assert "£" not in rendered
    assert "hostile" not in rendered
    assert "FD-W10-001" not in rendered
    assert "sha256" not in rendered


# ── 9. Imports remain limited to safe stdlib plus billing contracts ──────────

def test_module_imports_only_safe_stdlib_and_billing_contracts():
    forbidden = (
        "reserved.engines",
        "reserved.providers",
        "reserved.database",
        "reserved.web",
        "reserved.models",
        "reserved.auth",
        "reserved.config",
        "reserved.services.w2_customer_language",
        "reserved.services.w8_customer_result",
        "import requests",
        "import urllib",
        "import socket",
        "import subprocess",
        "import flask",
        "import stripe",
    )
    assert not [token for token in forbidden if token in MODULE_SOURCE]
    assert "reserved.billing.contracts" in MODULE_SOURCE


def test_module_contains_no_binary_float_arithmetic():
    assert "float(" not in MODULE_SOURCE
    assert "0.0" not in MODULE_SOURCE
    assert "INITIAL_BILLING_AUTHORITY" in MODULE_SOURCE
