from __future__ import annotations

import copy
import pickle
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

import reserved.billing.contracts as contract
from reserved.billing import (
    AUTHORITY_VERSION,
    FOUNDER_DECISION_DATE,
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


def _complete_register() -> BillingPolicyRegister:
    return BillingPolicyRegister(
        tuple(_decision(key, index) for index, key in enumerate(REQUIRED_BILLING_POLICY_KEYS, 1))
    )


class _InvalidPlanPicklePayload:
    def __reduce__(self):
        return (PlanPrice, (PlanKey.MONTHLY, Decimal("30"), Currency.GBP))


class _PlaceholderDecisionPicklePayload:
    def __reduce__(self):
        return (
            BillingPolicyDecision,
            (BillingPolicyKey.REFUNDS, "Provider default.", _provenance()),
        )


def test_authority_is_exactly_bound_to_fd_w10_001():
    authority = INITIAL_BILLING_AUTHORITY
    assert FOUNDER_DECISION_ID == "FD-W10-001"
    assert FOUNDER_DECISION_DATE.isoformat() == "2026-09-02"
    assert AUTHORITY_VERSION == "FD-W10-001/2026-09-02/v1"
    assert authority.decision_id == FOUNDER_DECISION_ID
    assert authority.decision_date == FOUNDER_DECISION_DATE
    assert authority.authority_version == AUTHORITY_VERSION
    assert authority.launch_model is LaunchModel.PAID_SUBSCRIPTION


def test_catalogue_has_stable_keys_and_exact_gbp_decimal_amounts():
    assert tuple(plan.key for plan in INITIAL_BILLING_AUTHORITY.plans) == (
        PlanKey.MONTHLY,
        PlanKey.SIX_MONTH,
        PlanKey.YEARLY,
    )
    assert tuple(plan.amount for plan in INITIAL_BILLING_AUTHORITY.plans) == (
        Decimal("29"),
        Decimal("156"),
        Decimal("288"),
    )
    assert all(type(plan.amount) is Decimal for plan in INITIAL_BILLING_AUTHORITY.plans)
    assert all(plan.currency is Currency.GBP for plan in INITIAL_BILLING_AUTHORITY.plans)


def test_plan_lookup_accepts_only_internal_enum_keys():
    assert INITIAL_BILLING_AUTHORITY.plan(PlanKey.SIX_MONTH).amount == Decimal("156")
    with pytest.raises(TypeError, match="exact PlanKey"):
        INITIAL_BILLING_AUTHORITY.plan("six_month")  # type: ignore[arg-type]


def test_vat_price_metadata_does_not_determine_rate_or_applicability():
    authority = INITIAL_BILLING_AUTHORITY
    assert authority.vat_price_statement is VatPriceStatement.INCLUSIVE_WHERE_APPLICABLE
    authority_fields = {field.name for field in fields(authority)}
    assert authority_fields.isdisjoint({"vat_rate", "vat_applies", "vat_amount", "tax_rate"})


def test_price_change_and_offer_rules_preserve_only_founder_authority():
    authority = INITIAL_BILLING_AUTHORITY
    assert (
        authority.price_change_rule
        is PriceChangeRule.INITIAL_CHANGEABLE_ONLY_BY_LATER_FOUNDER_DECISION
    )
    assert (
        authority.offer_capability_rule
        is OfferCapabilityRule.REQUIRED_WITHOUT_CALCULATION_OR_ACCESS_AUTHORITY
    )
    for forbidden in (
        "calculate_discount",
        "discount_amount",
        "offer_price",
        "access_granted",
        "grant_access",
        "activate",
    ):
        assert not hasattr(authority, forbidden)
        assert not hasattr(contract, forbidden)


@pytest.mark.parametrize("amount", [True, False, 29, 29.0, "29", None])
def test_plan_rejects_non_decimal_amounts(amount):
    with pytest.raises(TypeError, match="exact Decimal"):
        PlanPrice(PlanKey.MONTHLY, amount, Currency.GBP)


@pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_plan_rejects_non_finite_decimal_amounts(amount):
    with pytest.raises(ValueError, match="finite"):
        PlanPrice(PlanKey.MONTHLY, amount, Currency.GBP)


@pytest.mark.parametrize(
    ("key", "amount"),
    [
        (PlanKey.MONTHLY, Decimal("29.01")),
        (PlanKey.MONTHLY, Decimal("156")),
        (PlanKey.SIX_MONTH, Decimal("155.99")),
        (PlanKey.YEARLY, Decimal("287.99")),
    ],
)
def test_plan_rejects_altered_or_cross_assigned_amounts(key, amount):
    with pytest.raises(ValueError, match="does not match"):
        PlanPrice(key, amount, Currency.GBP)


@pytest.mark.parametrize(
    ("key", "currency", "error"),
    [
        ("monthly", Currency.GBP, TypeError),
        (PlanKey.MONTHLY, "GBP", ValueError),
        (PlanKey.MONTHLY, "USD", ValueError),
    ],
)
def test_plan_rejects_non_exact_keys_and_currency(key, currency, error):
    with pytest.raises(error):
        PlanPrice(key, Decimal("29"), currency)


def test_authority_rejects_missing_duplicate_reordered_and_non_tuple_plans():
    plans = INITIAL_BILLING_AUTHORITY.plans
    with pytest.raises(ValueError, match="each settled key exactly once"):
        replace(INITIAL_BILLING_AUTHORITY, plans=plans[:-1])
    with pytest.raises(ValueError, match="each settled key exactly once"):
        replace(INITIAL_BILLING_AUTHORITY, plans=(plans[0], plans[0], plans[2]))
    with pytest.raises(ValueError, match="each settled key exactly once"):
        replace(INITIAL_BILLING_AUTHORITY, plans=tuple(reversed(plans)))
    with pytest.raises(TypeError, match="exact tuple"):
        replace(INITIAL_BILLING_AUTHORITY, plans=list(plans))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("decision_id", "FD-W10-999"),
        ("decision_date", datetime(2026, 9, 2, tzinfo=timezone.utc)),
        ("authority_version", "latest"),
        ("launch_model", "paid_subscription"),
        ("vat_price_statement", "inclusive_of_vat_where_applicable"),
        ("price_change_rule", "changeable"),
        ("offer_capability_rule", True),
    ],
)
def test_dataclasses_replace_cannot_alter_authority(field, value):
    with pytest.raises((TypeError, ValueError)):
        replace(INITIAL_BILLING_AUTHORITY, **{field: value})


def test_authority_and_plan_reject_provider_vat_discount_and_access_fields():
    plan = INITIAL_BILLING_AUTHORITY.plans[0]
    for name, value in (
        ("provider_product_id", "prod_123"),
        ("provider_price_id", "price_123"),
        ("vat_rate", Decimal("0.20")),
        ("vat_applies", True),
        ("discount_algorithm", object()),
        ("access_granted", True),
    ):
        with pytest.raises(TypeError):
            replace(plan, **{name: value})
        with pytest.raises(TypeError):
            replace(INITIAL_BILLING_AUTHORITY, **{name: value})


def test_authority_objects_are_frozen():
    with pytest.raises(FrozenInstanceError):
        INITIAL_BILLING_AUTHORITY.authority_version = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        INITIAL_BILLING_AUTHORITY.plans[0].amount = Decimal("30")  # type: ignore[misc]


def test_authority_copy_deepcopy_pickle_and_replace_revalidate():
    values = (INITIAL_BILLING_AUTHORITY, *INITIAL_BILLING_AUTHORITY.plans)
    for value in values:
        for rebuilt in (copy.copy(value), copy.deepcopy(value), pickle.loads(pickle.dumps(value))):
            assert rebuilt == value
            assert type(rebuilt) is type(value)
            hash(rebuilt)
    assert replace(INITIAL_BILLING_AUTHORITY) == INITIAL_BILLING_AUTHORITY
    assert replace(INITIAL_BILLING_AUTHORITY.plans[0]) == INITIAL_BILLING_AUTHORITY.plans[0]


def test_copy_and_pickle_reject_a_forged_invalid_plan_state():
    forged = replace(INITIAL_BILLING_AUTHORITY.plans[0])
    object.__setattr__(forged, "amount", Decimal("30"))
    with pytest.raises(ValueError, match="does not match"):
        copy.copy(forged)
    with pytest.raises(ValueError, match="does not match"):
        copy.deepcopy(forged)
    with pytest.raises(ValueError, match="does not match"):
        pickle.dumps(forged)
    with pytest.raises(ValueError, match="does not match"):
        forged.__reduce__()
    with pytest.raises(ValueError, match="does not match"):
        pickle.loads(pickle.dumps(_InvalidPlanPicklePayload()))


def test_copy_and_pickle_reject_a_forged_invalid_authority_state():
    forged = replace(INITIAL_BILLING_AUTHORITY)
    object.__setattr__(forged, "authority_version", "unversioned")
    with pytest.raises(ValueError, match="bind exactly"):
        copy.copy(forged)
    with pytest.raises(ValueError, match="bind exactly"):
        copy.deepcopy(forged)
    with pytest.raises(ValueError, match="bind exactly"):
        pickle.dumps(forged)
    with pytest.raises(ValueError, match="bind exactly"):
        forged.__reduce__()


def test_required_policy_inventory_is_exact_and_complete():
    assert REQUIRED_BILLING_POLICY_KEYS == (
        BillingPolicyKey.BILLING_PROVIDER,
        BillingPolicyKey.RENEWAL_BEHAVIOUR,
        BillingPolicyKey.CANCELLATION_TIMING,
        BillingPolicyKey.FAILED_PAYMENT_AND_GRACE,
        BillingPolicyKey.ENTITLEMENT_START_AND_END,
        BillingPolicyKey.REFUNDS,
        BillingPolicyKey.TAX_INVOICING_AND_ADDITIONAL_PRESENTATION,
        BillingPolicyKey.PROMOTION_AND_DISCOUNT_MECHANICS,
        BillingPolicyKey.PARTNER_OFFER_HANDLING,
        BillingPolicyKey.PAID_ACCESS_SURFACE,
        BillingPolicyKey.TRIAL_AND_FREE_ACCESS,
        BillingPolicyKey.PLAN_CHANGES_AND_PRORATION,
        BillingPolicyKey.BILLING_ACCOUNT_RECOVERY,
        BillingPolicyKey.MANUAL_OVERRIDES,
        BillingPolicyKey.POST_SETTLEMENT_DISPUTE_CHARGEBACK_REVERSAL,
    )
    assert len(REQUIRED_BILLING_POLICY_KEYS) == 15
    assert len(set(REQUIRED_BILLING_POLICY_KEYS)) == 15


def test_empty_and_partial_registers_fail_closed_without_lifecycle_defaults():
    empty = BillingPolicyRegister()
    assert empty.decisions == ()
    assert empty.status is PolicyCompletenessStatus.POLICY_INCOMPLETE
    assert empty.missing_policy_keys == REQUIRED_BILLING_POLICY_KEYS

    provider_only = BillingPolicyRegister((_decision(BillingPolicyKey.BILLING_PROVIDER),))
    assert provider_only.status is PolicyCompletenessStatus.POLICY_INCOMPLETE
    assert provider_only.decision_for(BillingPolicyKey.BILLING_PROVIDER) is not None
    assert provider_only.decision_for(BillingPolicyKey.RENEWAL_BEHAVIOUR) is None
    assert BillingPolicyKey.RENEWAL_BEHAVIOUR in provider_only.missing_policy_keys
    assert BillingPolicyKey.POST_SETTLEMENT_DISPUTE_CHARGEBACK_REVERSAL in (
        provider_only.missing_policy_keys
    )


def test_all_explicit_traced_inputs_are_complete_for_policy_inputs_only():
    register = _complete_register()
    assert register.status is PolicyCompletenessStatus.POLICY_INPUTS_COMPLETE
    assert register.missing_policy_keys == ()
    assert len(register.decisions) == len(REQUIRED_BILLING_POLICY_KEYS)
    for forbidden in ("access_granted", "launch_ready", "activate", "entitlement"):
        assert not hasattr(register, forbidden)


def test_explicit_not_applicable_policy_can_be_traced_without_becoming_implicit():
    decision = BillingPolicyDecision(
        BillingPolicyKey.TRIAL_AND_FREE_ACCESS,
        "No trial or free access is supported under decision W10-POL-010.",
        _provenance(10),
    )
    register = BillingPolicyRegister((decision,))
    assert register.decision_for(BillingPolicyKey.TRIAL_AND_FREE_ACCESS) == decision
    assert register.status is PolicyCompletenessStatus.POLICY_INCOMPLETE


@pytest.mark.parametrize(
    "bad_key",
    ["billing_provider", "unknown_policy", None, 1, True],
)
def test_policy_decision_and_lookup_reject_unknown_or_non_exact_keys(bad_key):
    with pytest.raises(TypeError, match="exact BillingPolicyKey"):
        BillingPolicyDecision(bad_key, "Explicit outcome", _provenance())
    with pytest.raises(TypeError, match="exact BillingPolicyKey"):
        BillingPolicyRegister().decision_for(bad_key)


def test_policy_register_rejects_duplicates_non_tuple_and_unknown_values():
    decision = _decision(BillingPolicyKey.BILLING_PROVIDER)
    with pytest.raises(ValueError, match="duplicate"):
        BillingPolicyRegister((decision, decision))
    with pytest.raises(TypeError, match="exact tuple"):
        BillingPolicyRegister([decision])
    with pytest.raises(TypeError, match="only exact BillingPolicyDecision"):
        BillingPolicyRegister((decision, object()))


@pytest.mark.parametrize(
    "outcome",
    [
        "", " ", "TBD", "TBD.", "TBD,", "tBd!!!", "T.B.D.", "T. B. D.",
        "T . B . D .", "T. B. C.", "T . B . C .", "T .B .D", "t b d", "pending",
        "Pending decision.", "decision   pending...", "unknown", "Provider default.",
        "provider-default.",
        "provider's default!", "Use provider default.", "use provider's default?",
        "not yet decided.", "To be determined:", "to be confirmed;", "x\n",
    ],
)
def test_policy_decision_rejects_missing_placeholder_or_malformed_outcomes(outcome):
    with pytest.raises(ValueError):
        BillingPolicyDecision(BillingPolicyKey.RENEWAL_BEHAVIOUR, outcome, _provenance())


def test_placeholder_filter_does_not_search_inside_legitimate_prose():
    for outcome in (
        "The provider default is rejected; renew only under the recorded policy.",
        "The T . B . D . label is prohibited; use the recorded renewal policy.",
    ):
        decision = BillingPolicyDecision(
            BillingPolicyKey.RENEWAL_BEHAVIOUR,
            outcome,
            _provenance(),
        )
        assert decision.outcome == outcome


def test_policy_decision_requires_exact_provenance_type():
    with pytest.raises(TypeError, match="exact DecisionProvenance"):
        BillingPolicyDecision(
            BillingPolicyKey.RENEWAL_BEHAVIOUR,
            "Explicit renewal outcome",
            {"decision_id": "W10-POL-001"},
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"decision_id": "policy-1"},
        {"decision_id": "W10-POL"},
        {"decided_by": ""},
        {"decided_by": " billing-owner"},
        {"decided_by": "billing\nowner"},
        {"decided_at": datetime(2026, 9, 3, 9, 0)},
        {"decided_at": datetime(2026, 9, 3, 9, 0, tzinfo=timezone(timedelta(hours=1)))},
        {"decided_at": "2026-09-03T09:00:00Z"},
        {"record_reference": "docs/W10_BILLING_POLICY.md"},
        {"record_reference": "https://provider.example/decision#one"},
        {"record_reference": "docs/policy.md#bad section"},
        {"record_reference": "../secret.md#x"},
        {"record_reference": "docs/../secret.md#x"},
        {"record_reference": "./policy.md#x"},
        {"record_reference": "docs/./policy.md#x"},
    ],
)
def test_provenance_rejects_malformed_or_non_utc_values(changes):
    with pytest.raises((TypeError, ValueError)):
        replace(_provenance(), **changes)


def test_policy_types_are_frozen_and_replace_revalidates():
    provenance = _provenance()
    decision = _decision(BillingPolicyKey.REFUNDS)
    register = BillingPolicyRegister((decision,))
    with pytest.raises(FrozenInstanceError):
        provenance.decided_by = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        decision.outcome = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        register.decisions = ()  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(decision, outcome="TBD")
    with pytest.raises(ValueError):
        replace(provenance, record_reference="missing-anchor")
    with pytest.raises(ValueError):
        replace(register, decisions=(decision, decision))


def test_policy_copy_deepcopy_pickle_and_replace_preserve_validated_values():
    values = (_provenance(), _decision(BillingPolicyKey.REFUNDS), _complete_register())
    for value in values:
        for rebuilt in (copy.copy(value), copy.deepcopy(value), pickle.loads(pickle.dumps(value))):
            assert rebuilt == value
            assert type(rebuilt) is type(value)
            hash(rebuilt)
        assert replace(value) == value


def test_copy_and_pickle_reject_forged_invalid_policy_state():
    forged = _decision(BillingPolicyKey.REFUNDS)
    object.__setattr__(forged, "outcome", "TBD")
    with pytest.raises(ValueError, match="explicit"):
        copy.copy(forged)
    with pytest.raises(ValueError, match="explicit"):
        copy.deepcopy(forged)
    with pytest.raises(ValueError, match="explicit"):
        pickle.dumps(forged)
    with pytest.raises(ValueError, match="explicit"):
        forged.__reduce__()
    with pytest.raises(ValueError, match="explicit"):
        pickle.loads(pickle.dumps(_PlaceholderDecisionPicklePayload()))


def test_copy_and_pickle_reject_forged_provenance_and_register_state():
    provenance = _provenance()
    object.__setattr__(provenance, "record_reference", "missing-anchor")
    register = BillingPolicyRegister((_decision(BillingPolicyKey.REFUNDS),))
    object.__setattr__(register, "decisions", (register.decisions[0], register.decisions[0]))

    for operation in (
        lambda value: copy.copy(value),
        lambda value: copy.deepcopy(value),
        lambda value: pickle.dumps(value),
        lambda value: value.__reduce__(),
    ):
        with pytest.raises(ValueError, match="local record and section"):
            operation(provenance)
        with pytest.raises(ValueError, match="duplicate"):
            operation(register)


def test_authority_recursively_rejects_forged_nested_plan_at_every_boundary():
    forged_plan = replace(INITIAL_BILLING_AUTHORITY.plans[0])
    object.__setattr__(forged_plan, "amount", Decimal("30"))
    forged_authority = object.__new__(BillingAuthority)
    for field in fields(BillingAuthority):
        value = getattr(INITIAL_BILLING_AUTHORITY, field.name)
        if field.name == "plans":
            value = (forged_plan, *INITIAL_BILLING_AUTHORITY.plans[1:])
        object.__setattr__(forged_authority, field.name, value)

    with pytest.raises(ValueError, match="does not match"):
        BillingAuthority(
            INITIAL_BILLING_AUTHORITY.decision_id,
            INITIAL_BILLING_AUTHORITY.decision_date,
            INITIAL_BILLING_AUTHORITY.authority_version,
            INITIAL_BILLING_AUTHORITY.launch_model,
            (forged_plan, *INITIAL_BILLING_AUTHORITY.plans[1:]),
            INITIAL_BILLING_AUTHORITY.vat_price_statement,
            INITIAL_BILLING_AUTHORITY.price_change_rule,
            INITIAL_BILLING_AUTHORITY.offer_capability_rule,
        )
    with pytest.raises(ValueError, match="does not match"):
        replace(INITIAL_BILLING_AUTHORITY, plans=(
            forged_plan, *INITIAL_BILLING_AUTHORITY.plans[1:],
        ))
    for operation in (
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
        lambda value: value.__reduce__(),
        lambda value: replace(value),
        lambda value: value.plan(PlanKey.MONTHLY),
    ):
        with pytest.raises(ValueError, match="does not match"):
            operation(forged_authority)


def test_policy_composites_recursively_reject_forged_nested_state():
    forged_provenance = _provenance()
    object.__setattr__(forged_provenance, "record_reference", "missing-anchor")
    with pytest.raises(ValueError, match="local record and section"):
        BillingPolicyDecision(
            BillingPolicyKey.REFUNDS,
            "Explicit refund outcome",
            forged_provenance,
        )

    forged_decision = _decision(BillingPolicyKey.REFUNDS)
    object.__setattr__(forged_decision.provenance, "record_reference", "missing-anchor")
    with pytest.raises(ValueError, match="local record and section"):
        BillingPolicyRegister((forged_decision,))
    for operation in (copy.copy, copy.deepcopy, pickle.dumps, lambda value: value.__reduce__()):
        with pytest.raises(ValueError, match="local record and section"):
            operation(forged_decision)
    forged_register = object.__new__(BillingPolicyRegister)
    object.__setattr__(forged_register, "decisions", (forged_decision,))
    for operation in (
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
        lambda value: value.__reduce__(),
        lambda value: replace(value),
        lambda value: value.missing_policy_keys,
        lambda value: value.status,
        lambda value: value.decision_for(BillingPolicyKey.REFUNDS),
    ):
        with pytest.raises(ValueError, match="local record and section"):
            operation(forged_register)


def test_missing_and_subclassed_nested_state_fails_closed():
    missing_plan = object.__new__(PlanPrice)
    with pytest.raises(ValueError, match="incomplete"):
        copy.copy(missing_plan)
    with pytest.raises(ValueError, match="incomplete"):
        missing_plan.__reduce__()

    missing_provenance = object.__new__(DecisionProvenance)
    with pytest.raises(ValueError, match="incomplete"):
        BillingPolicyDecision(
            BillingPolicyKey.REFUNDS,
            "Explicit refund outcome",
            missing_provenance,
        )

    class PlanPriceSubclass(PlanPrice):
        pass

    with pytest.raises(TypeError, match="exact PlanPrice"):
        PlanPriceSubclass(PlanKey.MONTHLY, Decimal("29"), Currency.GBP)
    subclassed = object.__new__(PlanPriceSubclass)
    object.__setattr__(subclassed, "key", PlanKey.MONTHLY)
    object.__setattr__(subclassed, "amount", Decimal("29"))
    object.__setattr__(subclassed, "currency", Currency.GBP)
    with pytest.raises(TypeError, match="exact PlanPrice"):
        replace(INITIAL_BILLING_AUTHORITY, plans=(
            subclassed, *INITIAL_BILLING_AUTHORITY.plans[1:],
        ))


def test_each_complete_register_key_rejects_a_placeholder_variant():
    variants = (
        "T . B . D .",
        "T . B . C .",
        "T .B .D",
        "Provider default.",
        "Provider   default . .",
        "Use provider default.",
        "PENDING DECISION",
        "Not yet decided.",
        "decision pending;",
        "To be determined?",
        "to be confirmed:",
        "UNKNOWN.",
        "DEFAULT!",
        "provider's default.",
        "use provider's default!",
    )
    assert len(variants) == len(REQUIRED_BILLING_POLICY_KEYS) == 15
    for target_index, variant in enumerate(variants):
        decisions = [
            _decision(key, index)
            for index, key in enumerate(REQUIRED_BILLING_POLICY_KEYS, 1)
        ]
        object.__setattr__(decisions[target_index], "outcome", variant)
        with pytest.raises(ValueError, match="explicit"):
            BillingPolicyRegister(tuple(decisions))
        forged_register = object.__new__(BillingPolicyRegister)
        object.__setattr__(forged_register, "decisions", tuple(decisions))
        with pytest.raises(ValueError, match="explicit"):
            _ = forged_register.status


def test_public_contract_has_no_provider_io_persistence_or_execution_surface():
    forbidden = {
        "checkout",
        "create_customer",
        "create_subscription",
        "grant_access",
        "handle_webhook",
        "save",
        "select_provider",
    }
    assert forbidden.isdisjoint(contract.__all__)
    assert {field.name for field in fields(BillingAuthority)}.isdisjoint(
        {"provider", "provider_price_id", "provider_product_id", "vat_rate", "vat_applies"}
    )
