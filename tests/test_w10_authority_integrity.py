"""W10-S1 authority-integrity regressions.

These tests exercise the authoritative consumer boundary -- the public
``validate_*``/``project_*``/``copy_*`` functions and ordinary construction
paths -- and prove that the frozen Founder authority is not weakened by routine
in-process rebinding of module constants, module validators/helpers, class
methods, callable default/container state, or slot attribute descriptors, nor by
low-level ``object.__setattr__`` mutation of authority leaves.  Ordinary
``copy.copy``/``copy.deepcopy``/``pickle`` remain best-effort only and are
deliberately excluded from the authoritative boundary.
"""

from __future__ import annotations

import copy
import dis
import pickle
import types
from dataclasses import fields, replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

import reserved.billing.contracts as contract
from reserved.billing.contracts import (
    AUTHORITY_VERSION,
    FOUNDER_DECISION_ID,
    INITIAL_BILLING_AUTHORITY,
    REQUIRED_BILLING_POLICY_KEYS,
    BillingAuthority,
    BillingPolicyDecision,
    BillingPolicyKey,
    BillingPolicyRegister,
    Currency,
    DecisionProvenance,
    LaunchModel,
    OfferCapabilityRule,
    PlanKey,
    PlanPrice,
    PolicyCompletenessStatus,
    PriceChangeRule,
    VatPriceStatement,
    copy_billing_authority,
    copy_billing_policy_decision,
    copy_billing_policy_register,
    copy_decision_provenance,
    copy_plan_price,
    project_billing_authority,
    project_billing_policy_decision,
    project_billing_policy_register,
    project_decision_provenance,
    project_plan_price,
    validate_billing_authority,
    validate_billing_policy_decision,
    validate_billing_policy_register,
    validate_decision_provenance,
    validate_plan_price,
)


def _provenance(index: int = 1) -> DecisionProvenance:
    return DecisionProvenance(
        decision_id=f"W10-POL-{index:03d}",
        decided_by="billing-policy-owner",
        decided_at=datetime(2026, 9, 3, 9, index % 60, tzinfo=timezone.utc),
        record_reference=f"docs/W10_BILLING_POLICY.md#decision-{index}",
    )


def _decision(key: BillingPolicyKey, index: int = 1) -> BillingPolicyDecision:
    return BillingPolicyDecision(
        key=key,
        outcome=f"Explicit recorded outcome for {key.value}",
        provenance=_provenance(index),
    )


def _forged_plan(**overrides) -> PlanPrice:
    source = INITIAL_BILLING_AUTHORITY.plans[0]
    forged = object.__new__(PlanPrice)
    for field in fields(PlanPrice):
        object.__setattr__(forged, field.name, overrides.get(field.name, getattr(source, field.name)))
    return forged


def _forged_authority(**overrides) -> BillingAuthority:
    forged = object.__new__(BillingAuthority)
    for field in fields(BillingAuthority):
        object.__setattr__(
            forged, field.name, overrides.get(field.name, getattr(INITIAL_BILLING_AUTHORITY, field.name))
        )
    return forged


# ── Exact frozen authority remains unchanged ─────────────────────────────────


def test_exact_gbp_amounts_and_vat_offer_authority_are_unchanged():
    assert AUTHORITY_VERSION == "FD-W10-001/2026-09-02/v1"
    assert FOUNDER_DECISION_ID == "FD-W10-001"
    assert tuple(plan.key for plan in INITIAL_BILLING_AUTHORITY.plans) == (
        PlanKey.MONTHLY,
        PlanKey.SIX_MONTH,
        PlanKey.YEARLY,
    )
    assert tuple(str(plan.amount) for plan in INITIAL_BILLING_AUTHORITY.plans) == (
        "29",
        "156",
        "288",
    )
    assert all(plan.currency is Currency.GBP for plan in INITIAL_BILLING_AUTHORITY.plans)
    assert (
        INITIAL_BILLING_AUTHORITY.vat_price_statement
        is VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE
    )
    assert (
        INITIAL_BILLING_AUTHORITY.offer_capability_rule
        is OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY
    )
    assert (
        INITIAL_BILLING_AUTHORITY.price_change_rule
        is PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION
    )


def test_no_provider_or_lifecycle_default_appears():
    authority_fields = {field.name for field in fields(BillingAuthority)}
    plan_fields = {field.name for field in fields(PlanPrice)}
    register_fields = {field.name for field in fields(BillingPolicyRegister)}
    assert authority_fields.isdisjoint(
        {"provider", "provider_price_id", "provider_product_id", "vat_rate", "vat_applies"}
    )
    assert plan_fields.isdisjoint({"provider_product_id", "provider_price_id"})
    assert "default" not in register_fields
    assert "provider" not in register_fields
    for forbidden in ("checkout", "select_provider", "create_subscription", "grant_access", "save"):
        assert forbidden not in contract.__all__


# ── Module constant rebinding ────────────────────────────────────────────────


def test_rebinding_authority_version_constant_cannot_reauthorise_forged_state(monkeypatch):
    monkeypatch.setattr(contract, "AUTHORITY_VERSION", "forged-version")
    # The captured authority still validates and projects the settled singleton.
    assert validate_billing_authority(INITIAL_BILLING_AUTHORITY)[2] == "FD-W10-001/2026-09-02/v1"
    assert project_billing_authority(INITIAL_BILLING_AUTHORITY) == INITIAL_BILLING_AUTHORITY
    # A forged version is still rejected.
    with pytest.raises(ValueError, match="bind exactly"):
        replace(INITIAL_BILLING_AUTHORITY, authority_version="forged-version")
    with pytest.raises(ValueError, match="bind exactly"):
        validate_billing_authority(_forged_authority(authority_version="forged-version"))


def test_rebinding_founder_decision_id_constant_cannot_weaken_authority(monkeypatch):
    monkeypatch.setattr(contract, "FOUNDER_DECISION_ID", "FD-W10-999")
    assert validate_billing_authority(INITIAL_BILLING_AUTHORITY)[0] == "FD-W10-001"
    with pytest.raises(ValueError, match="bind exactly"):
        validate_billing_authority(_forged_authority(decision_id="FD-W10-999"))


def test_rebinding_required_policy_keys_constant_does_not_change_denominator(monkeypatch):
    monkeypatch.setattr(contract, "REQUIRED_BILLING_POLICY_KEYS", ())
    register = BillingPolicyRegister()
    assert register.missing_policy_keys == REQUIRED_BILLING_POLICY_KEYS
    assert len(register.missing_policy_keys) == 15
    assert register.status is PolicyCompletenessStatus.POLICY_INCOMPLETE


# ── Module validator/helper rebinding ────────────────────────────────────────


def test_rebinding_plan_validator_cannot_weaken_constructor_or_projection(monkeypatch):
    monkeypatch.setattr(contract, "validate_plan_price", lambda value: (PlanKey.MONTHLY, Decimal("999"), Currency.GBP))
    with pytest.raises(ValueError, match="does not match"):
        PlanPrice(PlanKey.MONTHLY, Decimal("30"), Currency.GBP)
    with pytest.raises(ValueError, match="does not match"):
        project_plan_price(_forged_plan(amount=Decimal("30")))
    # Legitimate values still validate/project through the captured validator.
    assert validate_plan_price(INITIAL_BILLING_AUTHORITY.plans[0])[1] == Decimal("29")


def test_rebinding_authority_validator_cannot_weaken_constructor_or_projection(monkeypatch):
    monkeypatch.setattr(contract, "validate_billing_authority", lambda value: ())
    with pytest.raises(ValueError, match="bind exactly"):
        replace(INITIAL_BILLING_AUTHORITY, authority_version="forged-version")
    with pytest.raises(ValueError, match="bind exactly"):
        project_billing_authority(_forged_authority(authority_version="forged-version"))


def test_rebinding_provenance_validator_cannot_weaken_policy_decision_validation(monkeypatch):
    monkeypatch.setattr(contract, "validate_decision_provenance", lambda value: (None, None, None, None))
    with pytest.raises(ValueError, match="local record and section"):
        BillingPolicyDecision(
            BillingPolicyKey.REFUNDS,
            "Explicit refund outcome",
            replace(_provenance(), record_reference="missing-anchor"),
        )


# ── Class method rebinding ───────────────────────────────────────────────────


def test_rebinding_plan_post_init_cannot_weaken_authoritative_projection(monkeypatch):
    monkeypatch.setattr(PlanPrice, "__post_init__", lambda self: None)
    forged = PlanPrice(PlanKey.MONTHLY, Decimal("30"), Currency.GBP)
    with pytest.raises(ValueError, match="does not match"):
        validate_plan_price(forged)
    with pytest.raises(ValueError, match="does not match"):
        project_plan_price(forged)


def test_rebinding_authority_post_init_cannot_weaken_authoritative_projection(monkeypatch):
    monkeypatch.setattr(BillingAuthority, "__post_init__", lambda self: None)
    forged = BillingAuthority(
        INITIAL_BILLING_AUTHORITY.decision_id,
        INITIAL_BILLING_AUTHORITY.decision_date,
        "forged-version",
        INITIAL_BILLING_AUTHORITY.launch_model,
        INITIAL_BILLING_AUTHORITY.plans,
        INITIAL_BILLING_AUTHORITY.vat_price_statement,
        INITIAL_BILLING_AUTHORITY.price_change_rule,
        INITIAL_BILLING_AUTHORITY.offer_capability_rule,
    )
    with pytest.raises(ValueError, match="bind exactly"):
        validate_billing_authority(forged)
    with pytest.raises(ValueError, match="bind exactly"):
        project_billing_authority(forged)


# ── Descriptor and class-protocol attacks (W10-S1) ───────────────────────────


def test_rebinding_plan_amount_descriptor_cannot_reauthorise_forged_slot(monkeypatch):
    """A rebound public attribute view must not hide the retained raw slot.

    Forge a PlanPrice whose raw slot stores ``Decimal("999")``, then rebind
    ``PlanPrice.amount`` to a property returning ``Decimal("29")``.  The ordinary
    attribute read now reports the forged value, but the authoritative boundary
    reads the captured raw slot descriptor and rejects the retained value.
    """
    forged = _forged_plan(amount=Decimal("999"))
    raw_amount_slot = vars(PlanPrice)["amount"]
    assert raw_amount_slot.__get__(forged, PlanPrice) == Decimal("999")

    monkeypatch.setattr(PlanPrice, "amount", property(lambda self: Decimal("29")))
    assert forged.amount == Decimal("29")
    assert raw_amount_slot.__get__(forged, PlanPrice) == Decimal("999")

    for operation in (validate_plan_price, project_plan_price, copy_plan_price):
        with pytest.raises(ValueError, match="does not match"):
            operation(forged)


def test_rebinding_copy_protocol_methods_cannot_weaken_authoritative_boundary(monkeypatch):
    """Rebindable ``__copy__``/``__deepcopy__`` cannot re-authorise forged state.

    The authoritative copy operation is the closure-bound ``copy_*``; the
    ordinary copy protocol methods are best-effort only.  Rebinding them lets
    forged state through ``copy.copy``/``copy.deepcopy``, but the authoritative
    boundary still reads the captured raw slots and fails closed.
    """
    forged = _forged_plan(amount=Decimal("999"))
    monkeypatch.setattr(PlanPrice, "__copy__", lambda self: self)
    monkeypatch.setattr(PlanPrice, "__deepcopy__", lambda self, memo: self)

    assert copy.copy(forged) is forged
    assert copy.deepcopy(forged) is forged

    for operation in (validate_plan_price, project_plan_price, copy_plan_price):
        with pytest.raises(ValueError, match="does not match"):
            operation(forged)


def test_rebinding_reduce_protocol_method_cannot_reauthorise_forged_pickle(monkeypatch):
    """Rebindable ``__reduce__`` cannot make standard pickle authoritative.

    A rebound ``__reduce__`` can smuggle forged raw state through the standard
    pickle protocol, so pickle is explicitly excluded from the authoritative
    boundary.  The closure-bound validate/project/copy operations still reject
    the retained raw slot.
    """
    forged = _forged_plan(amount=Decimal("999"))
    monkeypatch.setattr(
        PlanPrice, "__reduce__", lambda self: (_reconstruct_forged_plan, ())
    )
    reloaded = pickle.loads(pickle.dumps(forged))
    assert reloaded.amount == Decimal("999")

    for candidate in (forged, reloaded):
        for operation in (validate_plan_price, project_plan_price, copy_plan_price):
            with pytest.raises(ValueError, match="does not match"):
                operation(candidate)


def test_copy_operations_return_fresh_validated_instances():
    """The closure-bound copy operations reproduce legitimate authority values."""
    plan = INITIAL_BILLING_AUTHORITY.plans[0]
    copied_plan = copy_plan_price(plan)
    assert copied_plan == plan
    assert copied_plan is not plan
    assert validate_plan_price(copied_plan) == (
        PlanKey.MONTHLY,
        Decimal("29"),
        Currency.GBP,
    )

    copied_authority = copy_billing_authority(INITIAL_BILLING_AUTHORITY)
    assert copied_authority == INITIAL_BILLING_AUTHORITY
    assert copied_authority is not INITIAL_BILLING_AUTHORITY

    decision = _decision(BillingPolicyKey.REFUNDS)
    copied_decision = copy_billing_policy_decision(decision)
    assert copied_decision == decision
    assert copied_decision is not decision

    register = BillingPolicyRegister((decision,))
    copied_register = copy_billing_policy_register(register)
    assert copied_register == register
    assert copied_register is not register


# ── Callable/default/container mutation ──────────────────────────────────────


def test_authoritative_validators_and_projectors_have_no_writable_default_state():
    public = (
        validate_plan_price,
        validate_billing_authority,
        validate_decision_provenance,
        validate_billing_policy_decision,
        validate_billing_policy_register,
        project_plan_price,
        project_billing_authority,
        project_decision_provenance,
        project_billing_policy_decision,
        project_billing_policy_register,
        copy_plan_price,
        copy_billing_authority,
        copy_decision_provenance,
        copy_billing_policy_decision,
        copy_billing_policy_register,
    )
    for fn in public:
        assert fn.__defaults__ is None
        assert fn.__kwdefaults__ is None


def test_mutating_public_validator_function_attributes_cannot_change_behaviour():
    fn = validate_plan_price
    original_defaults = fn.__defaults__
    original_kwdefaults = fn.__kwdefaults__
    original_dict = dict(fn.__dict__)
    try:
        fn.__defaults__ = (Decimal("999"),)
        fn.__kwdefaults__ = {"expected": Decimal("999")}
        fn.__dict__["expected"] = Decimal("999")
        # The boundary still rejects the forged amount using captured state.
        with pytest.raises(ValueError, match="does not match"):
            project_plan_price(_forged_plan(amount=Decimal("30")))
        assert validate_plan_price(INITIAL_BILLING_AUTHORITY.plans[0])[1] == Decimal("29")
    finally:
        fn.__defaults__ = original_defaults
        fn.__kwdefaults__ = original_kwdefaults
        fn.__dict__.clear()
        fn.__dict__.update(original_dict)


# ── Low-level mutation of authority identity/version/decision reference ──────


def test_low_level_mutation_of_authority_version_and_decision_reference_fails_closed():
    for overrides in (
        {"authority_version": "forged-version"},
        {"decision_id": "FD-W10-999"},
        {"decision_date": datetime(2026, 9, 2, tzinfo=timezone.utc)},
    ):
        forged = _forged_authority(**overrides)
        with pytest.raises((TypeError, ValueError)):
            validate_billing_authority(forged)
        with pytest.raises((TypeError, ValueError)):
            project_billing_authority(forged)
        with pytest.raises((TypeError, ValueError)):
            copy.copy(forged)
        with pytest.raises((TypeError, ValueError)):
            pickle.dumps(forged)


# ── Low-level mutation of each plan key/amount/currency ──────────────────────


@pytest.mark.parametrize("key", list(PlanKey))
def test_low_level_mutation_of_each_plan_amount_fails_closed(key):
    plan = INITIAL_BILLING_AUTHORITY.plan(key)
    forged = object.__new__(PlanPrice)
    object.__setattr__(forged, "key", key)
    object.__setattr__(forged, "amount", Decimal("999"))
    object.__setattr__(forged, "currency", Currency.GBP)
    with pytest.raises(ValueError, match="does not match"):
        validate_plan_price(forged)
    with pytest.raises(ValueError, match="does not match"):
        project_plan_price(forged)
    # Nested inside the authority it is still rejected.
    plans = tuple(
        forged if p.key is key else p for p in INITIAL_BILLING_AUTHORITY.plans
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_billing_authority(_forged_authority(plans=plans))


@pytest.mark.parametrize("key", list(PlanKey))
def test_low_level_mutation_of_each_plan_key_and_currency_fails_closed(key):
    wrong_key = next(k for k in PlanKey if k is not key)
    plan = INITIAL_BILLING_AUTHORITY.plan(key)
    for overrides in (
        {"key": wrong_key},
        {"currency": "GBP"},
        {"currency": "USD"},
    ):
        forged = object.__new__(PlanPrice)
        object.__setattr__(forged, "key", overrides.get("key", plan.key))
        object.__setattr__(forged, "amount", plan.amount)
        object.__setattr__(forged, "currency", overrides.get("currency", plan.currency))
        with pytest.raises((TypeError, ValueError)):
            validate_plan_price(forged)
        with pytest.raises((TypeError, ValueError)):
            project_plan_price(forged)


# ── Low-level mutation of policy completeness / unresolved keys ──────────────


def test_low_level_mutation_of_policy_outcome_fails_closed():
    decision = _decision(BillingPolicyKey.REFUNDS)
    forged = object.__new__(BillingPolicyDecision)
    object.__setattr__(forged, "key", decision.key)
    object.__setattr__(forged, "outcome", "Provider default.")
    object.__setattr__(forged, "provenance", decision.provenance)
    with pytest.raises(ValueError, match="explicit"):
        validate_billing_policy_decision(forged)
    with pytest.raises(ValueError, match="explicit"):
        project_billing_policy_decision(forged)


def test_low_level_mutation_of_register_duplicate_keys_fails_closed():
    decision = _decision(BillingPolicyKey.BILLING_PROVIDER)
    forged = object.__new__(BillingPolicyRegister)
    object.__setattr__(forged, "decisions", (decision, decision))
    with pytest.raises(ValueError, match="duplicate"):
        validate_billing_policy_register(forged)
    with pytest.raises(ValueError, match="duplicate"):
        project_billing_policy_register(forged)
    with pytest.raises(ValueError, match="duplicate"):
        _ = forged.status


def test_low_level_mutation_of_unresolved_key_inventory_is_captured(monkeypatch):
    # Rebinding the public key tuple cannot shrink the captured denominator used
    # by the register's completeness projection.
    monkeypatch.setattr(contract, "REQUIRED_BILLING_POLICY_KEYS", ())
    register = BillingPolicyRegister((_decision(BillingPolicyKey.BILLING_PROVIDER),))
    assert register.missing_policy_keys == REQUIRED_BILLING_POLICY_KEYS[1:]
    assert len(register.missing_policy_keys) == 14


# ── Direct forged construction ───────────────────────────────────────────────


def test_direct_forged_plan_and_authority_construction_fails_closed():
    missing_plan = object.__new__(PlanPrice)
    with pytest.raises(ValueError, match="incomplete"):
        validate_plan_price(missing_plan)
    with pytest.raises(ValueError, match="incomplete"):
        project_plan_price(missing_plan)

    missing_authority = object.__new__(BillingAuthority)
    with pytest.raises(ValueError, match="incomplete"):
        validate_billing_authority(missing_authority)
    with pytest.raises(ValueError, match="incomplete"):
        project_billing_authority(missing_authority)


# ── Legitimate construction/copy/pickle/projection remains valid ─────────────


def test_legitimate_construction_copy_pickle_and_projection_remain_valid():
    authority = INITIAL_BILLING_AUTHORITY
    assert project_billing_authority(authority) == authority
    assert project_billing_authority(authority) is not authority
    assert validate_billing_authority(authority) == (
        authority.decision_id,
        authority.decision_date,
        authority.authority_version,
        authority.launch_model,
        authority.plans,
        authority.vat_price_statement,
        authority.price_change_rule,
        authority.offer_capability_rule,
    )

    for value in (authority, *authority.plans):
        for rebuilt in (copy.copy(value), copy.deepcopy(value), pickle.loads(pickle.dumps(value))):
            assert rebuilt == value
            assert type(rebuilt) is type(value)
            hash(rebuilt)

    plan = authority.plans[0]
    assert project_plan_price(plan) == plan
    assert validate_plan_price(plan) == (plan.key, plan.amount, plan.currency)

    provenance = _provenance()
    decision = _decision(BillingPolicyKey.REFUNDS)
    register = BillingPolicyRegister((decision,))
    assert project_decision_provenance(provenance) == provenance
    assert project_billing_policy_decision(decision) == decision
    assert project_billing_policy_register(register) == register


# ── Builtin shadowing cannot re-authorise forged state ────────────────────────
#
# The reachable validation/projection graph must resolve acceptance-critical
# builtins/primitive from immutable closure bindings, never from mutable module
# aliases.  Rebinding a module name (``contracts.type``, ``contracts.len``,
# ``contracts.set``, ``contracts.any``, ``contracts.object``, ``contracts.tuple``,
# ``contracts.str``, ``contracts.next``, ``contracts.frozenset``, or the
# exception names) must not change what the authoritative boundary accepts.


class _HostileDecimal(Decimal):
    """A Decimal subclass whose comparison/hash lie, yet stays finite."""

    def __eq__(self, other):
        return True

    def __hash__(self):
        return 0

    def is_finite(self):
        return True


def _forged_plan_amount(amount):
    plan = INITIAL_BILLING_AUTHORITY.plans[0]
    forged = object.__new__(PlanPrice)
    object.__setattr__(forged, "key", plan.key)
    object.__setattr__(forged, "amount", amount)
    object.__setattr__(forged, "currency", plan.currency)
    return forged


def _reconstruct_forged_plan() -> PlanPrice:
    """Pickle-reconstruction callable that bypasses the constructor validator."""
    return _forged_plan(amount=Decimal("999"))


def _forged_duplicate_refunds_register():
    decision = _decision(BillingPolicyKey.REFUNDS)
    forged = object.__new__(BillingPolicyRegister)
    object.__setattr__(forged, "decisions", (decision, decision))
    return forged


def test_shadowing_type_cannot_reauthorise_hostile_decimal_subclass(monkeypatch):
    # Independent P1 reproducer 2: a hostile Decimal subclass reported as exact
    # Decimal by a shadowed ``type`` must not cross the authoritative boundary.
    monkeypatch.setattr(contract, "type", lambda value: Decimal, raising=False)
    forged = _forged_plan_amount(_HostileDecimal("999"))
    with pytest.raises(TypeError, match="exact Decimal"):
        validate_plan_price(forged)
    with pytest.raises(TypeError, match="exact Decimal"):
        project_plan_price(forged)


def test_shadowing_len_cannot_reauthorise_duplicate_refunds_register(monkeypatch):
    # Independent P1 reproducer 1: a shadowed ``len`` that collapses every size
    # to 0 must not hide duplicate policy keys.
    monkeypatch.setattr(contract, "len", lambda value: 0, raising=False)
    forged = _forged_duplicate_refunds_register()
    with pytest.raises(ValueError, match="duplicate"):
        validate_billing_policy_register(forged)
    with pytest.raises(ValueError, match="duplicate"):
        project_billing_policy_register(forged)


def test_shadowing_set_cannot_hide_duplicate_policy_keys(monkeypatch):
    monkeypatch.setattr(contract, "set", lambda value: value, raising=False)
    forged = _forged_duplicate_refunds_register()
    with pytest.raises(ValueError, match="duplicate"):
        validate_billing_policy_register(forged)
    with pytest.raises(ValueError, match="duplicate"):
        project_billing_policy_register(forged)


def test_shadowing_any_cannot_reauthorise_dot_segment_provenance(monkeypatch):
    monkeypatch.setattr(contract, "any", lambda value: False, raising=False)
    base = _provenance()
    forged = object.__new__(DecisionProvenance)
    object.__setattr__(forged, "decision_id", base.decision_id)
    object.__setattr__(forged, "decided_by", base.decided_by)
    object.__setattr__(forged, "decided_at", base.decided_at)
    object.__setattr__(forged, "record_reference", "docs/../policy.md#decision-1")
    with pytest.raises(ValueError, match="dot segment"):
        validate_decision_provenance(forged)
    with pytest.raises(ValueError, match="dot segment"):
        project_decision_provenance(forged)


def test_shadowing_object_cannot_weaken_exact_slot_reads(monkeypatch):
    class HostileObject:
        @staticmethod
        def __getattribute__(obj, name):
            raise AssertionError("hostile object.__getattribute__ must not be consulted")

    monkeypatch.setattr(contract, "object", HostileObject, raising=False)
    # Captured object.__getattribute__ still drives legitimate reads...
    assert validate_billing_authority(INITIAL_BILLING_AUTHORITY)[0] == "FD-W10-001"
    assert project_billing_authority(INITIAL_BILLING_AUTHORITY) == INITIAL_BILLING_AUTHORITY
    # ...and still fails closed on incomplete forged state.
    with pytest.raises(ValueError, match="incomplete"):
        validate_billing_authority(object.__new__(BillingAuthority))
    with pytest.raises(ValueError, match="incomplete"):
        project_billing_authority(object.__new__(BillingAuthority))


def test_shadowing_tuple_cannot_reauthorise_wrong_plan_order(monkeypatch):
    canonical = (PlanKey.MONTHLY, PlanKey.SIX_MONTH, PlanKey.YEARLY)
    monkeypatch.setattr(contract, "tuple", lambda value: canonical, raising=False)
    plans = tuple(reversed(INITIAL_BILLING_AUTHORITY.plans))
    forged = _forged_authority(plans=plans)
    with pytest.raises(ValueError, match="canonical order"):
        validate_billing_authority(forged)
    with pytest.raises(ValueError, match="canonical order"):
        project_billing_authority(forged)
    # Legitimate authority still validates/projects through the captured tuple.
    assert project_billing_authority(INITIAL_BILLING_AUTHORITY) == INITIAL_BILLING_AUTHORITY


def test_shadowing_str_cannot_weaken_exact_string_checks(monkeypatch):
    monkeypatch.setattr(contract, "str", bytes, raising=False)
    forged = _forged_authority(decision_id=b"FD-W10-001")
    with pytest.raises(ValueError, match="decision_id must bind exactly"):
        validate_billing_authority(forged)
    with pytest.raises(ValueError, match="decision_id must bind exactly"):
        project_billing_authority(forged)


def test_shadowing_next_cannot_weaken_decision_lookup(monkeypatch):
    monkeypatch.setattr(contract, "next", lambda iterator, default: None, raising=False)
    decision = _decision(BillingPolicyKey.BILLING_PROVIDER)
    register = BillingPolicyRegister((decision,))
    assert register.decision_for(BillingPolicyKey.BILLING_PROVIDER) is decision
    assert register.decision_for(BillingPolicyKey.REFUNDS) is None


def test_shadowing_frozenset_cannot_shrink_placeholder_vocabulary(monkeypatch):
    monkeypatch.setattr(contract, "frozenset", lambda value: frozenset(), raising=False)
    decision = _decision(BillingPolicyKey.REFUNDS)
    forged = object.__new__(BillingPolicyDecision)
    object.__setattr__(forged, "key", decision.key)
    object.__setattr__(forged, "outcome", "default")
    object.__setattr__(forged, "provenance", decision.provenance)
    with pytest.raises(ValueError, match="explicit"):
        validate_billing_policy_decision(forged)
    with pytest.raises(ValueError, match="explicit"):
        project_billing_policy_decision(forged)


@pytest.mark.parametrize(
    ("name", "hostile", "forged", "expected_exc", "match"),
    [
        (
            "ValueError",
            KeyError,
            lambda: _forged_plan_amount(Decimal("999")),
            ValueError,
            "does not match",
        ),
        (
            "TypeError",
            KeyError,
            lambda: _forged_plan_amount(_HostileDecimal("999")),
            TypeError,
            "exact Decimal",
        ),
        (
            "AttributeError",
            KeyError,
            lambda: object.__new__(BillingAuthority),
            ValueError,
            "incomplete",
        ),
    ],
)
def test_shadowing_exception_builtins_cannot_alter_rejection(
    monkeypatch, name, hostile, forged, expected_exc, match
):
    # Rebinding the module alias for an exception name must not change which
    # exception type the boundary raises (validators capture the real builtins).
    monkeypatch.setattr(contract, name, hostile, raising=False)
    value = forged()
    if name == "AttributeError":
        with pytest.raises(expected_exc, match=match):
            validate_billing_authority(value)
        with pytest.raises(expected_exc, match=match):
            project_billing_authority(value)
    else:
        with pytest.raises(expected_exc, match=match):
            validate_plan_price(value)
        with pytest.raises(expected_exc, match=match):
            project_plan_price(value)


# ── Bytecode-level whole-graph closure integrity ──────────────────────────────

_ACCEPTANCE_CRITICAL_BUILTINS = {
    "type",
    "object",
    "tuple",
    "len",
    "set",
    "any",
    "str",
    "next",
    "frozenset",
    "TypeError",
    "ValueError",
    "AttributeError",
}


def _iter_acceptance_functions():
    entry_names = (
        "validate_plan_price",
        "validate_billing_authority",
        "validate_decision_provenance",
        "validate_billing_policy_decision",
        "validate_billing_policy_register",
        "project_plan_price",
        "project_billing_authority",
        "project_decision_provenance",
        "project_billing_policy_decision",
        "project_billing_policy_register",
        "copy_plan_price",
        "copy_billing_authority",
        "copy_decision_provenance",
        "copy_billing_policy_decision",
        "copy_billing_policy_register",
    )
    entries = [getattr(contract, name) for name in entry_names]

    method_names = (
        "__post_init__",
        "__copy__",
        "__deepcopy__",
        "__reduce__",
        "plan",
        "decision_for",
        "missing_policy_keys",
        "status",
    )
    for cls in (
        PlanPrice,
        BillingAuthority,
        DecisionProvenance,
        BillingPolicyDecision,
        BillingPolicyRegister,
    ):
        for name in method_names:
            attr = vars(cls).get(name)
            if isinstance(attr, property):
                attr = attr.fget
            if isinstance(attr, types.FunctionType):
                entries.append(attr)

    seen = set()
    stack = list(entries)
    while stack:
        fn = stack.pop()
        if id(fn) in seen:
            continue
        seen.add(id(fn))
        yield fn
        closure = getattr(fn, "__closure__", None)
        if closure is None:
            continue
        for cell in closure:
            try:
                cell_value = cell.cell_contents
            except ValueError:
                continue
            if isinstance(cell_value, types.FunctionType):
                stack.append(cell_value)


def test_acceptance_critical_graph_never_resolves_builtins_via_load_global():
    violating = []
    for fn in _iter_acceptance_functions():
        for instruction in dis.get_instructions(fn):
            if instruction.opname == "LOAD_GLOBAL":
                if instruction.argval in _ACCEPTANCE_CRITICAL_BUILTINS:
                    violating.append((fn.__name__, instruction.argval))
    assert not violating, (
        "acceptance-critical builtins resolved via LOAD_GLOBAL (module-shadowable): "
        + repr(violating)
    )
