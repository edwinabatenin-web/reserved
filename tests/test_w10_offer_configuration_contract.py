"""Hostile tests for the disabled-first W10-S4D offer contract."""

from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import importlib
import inspect
import json
import math
import os
import pickle
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from types import FunctionType

import pytest

import reserved.billing.checkout_intent_contract as checkout
import reserved.billing.local_stripe_initial_payment as stripe_ingress
import reserved.billing.offer_configuration_contract as subject


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved" / "billing" / "offer_configuration_contract.py"
DOC = ROOT / "docs" / "W10_S4D_OFFER_CONFIGURATION_CONTRACT.md"
BASE = "961168dd5c17fbef7ba96ac1599a7f5888af1db3"
TREE = "a7788d5d9fd5c11034045694df25eb8681ab86d0"
CATALOGUE_VERSION = "FD-W10-001/2026-09-02/v1"

EXPECTED_SOURCES = (
    (
        "current_founder_authority",
        "FOUNDER_DECISIONS.md",
        "78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f",
        BASE,
    ),
    (
        "current_completion_map",
        "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
        "c38aa651bcfb617fc5c77cb233d3043815ddc687bf2839cdd506504c4220b939",
        BASE,
    ),
    (
        "accepted_w10_s1_source",
        "reserved/billing/contracts.py",
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
        "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
    ),
    (
        "accepted_w10_s1_tests",
        "tests/test_billing_contracts.py",
        "0344c7e098f20f02fbf91fa43457ec5c24ddd7825f9fc32706103c7652992abf",
        BASE,
    ),
    (
        "accepted_w10_s2b_source",
        "reserved/billing/fail_closed_launch_defaults.py",
        "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
        "1033c9fbef008dcd33125a0b14e7fb18b8846d19",
    ),
    (
        "accepted_w10_s2b_tests",
        "tests/test_w10_fail_closed_launch_defaults.py",
        "cb40ef6f6d6967e6c99a586a87e49c91bf7c1507acf1c869da3220f3db667dab",
        BASE,
    ),
    (
        "accepted_w10_s4a_source",
        "reserved/billing/stripe_disabled_first_contract.py",
        "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
        "2ad4a63dd1f10ba38859050b47245c28390667d8",
    ),
    (
        "accepted_w10_s4a_tests",
        "tests/test_w10_stripe_disabled_first_contract.py",
        "d032ea88bc7845fa92dc200f60edad4b26324ad97c14d1be78a131a4de2aac11",
        BASE,
    ),
    (
        "accepted_w10_s4b_source",
        "reserved/billing/checkout_intent_contract.py",
        "ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0",
        "23f4d3dc742474d3a672388a1ebe99962505b234",
    ),
    (
        "accepted_w10_s4b_tests",
        "tests/test_w10_checkout_intent_contract.py",
        "93b4a0b9363464eeb3b5d9dc10c92aacb90c60f549c7cdda1550355ac1cf6b91",
        BASE,
    ),
)


def policy_provenance(now=None, **overrides):
    now = now or datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    values = {
        "schema_version": "reserved-offer-policy-provenance/1.0",
        "decision_id": "W10-OFFER-POLICY-001",
        "policy_version": "offer_policy:future.synthetic.v1",
        "decided_by": "synthetic-policy-owner",
        "decided_at": now,
        "record_reference": "docs/FUTURE_OFFER_POLICY.md#synthetic-offer-1",
        "record_sha256": "sha256:" + "1" * 64,
    }
    values.update(overrides)
    return tuple(values.items())


def candidate_facts(now=None, **overrides):
    now = now or datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    values = {
        "offer_configuration_id": "offer_config:future.synthetic.001",
        "offer_policy_version": "offer_policy:future.synthetic.v1",
        "catalogue_authority_version": CATALOGUE_VERSION,
        "base_plan_key": "monthly",
        "proposed_unit_amount_minor": 2800,
        "currency": "GBP",
        "availability_starts_at": now + timedelta(days=1),
        "availability_ends_at": now + timedelta(days=31),
        "duration_count": 1,
        "duration_unit": "billing_periods",
        "eligibility_policy_reference": (
            "docs/FUTURE_OFFER_POLICY.md#synthetic-eligibility"
        ),
        "stacking_policy_reference": "docs/FUTURE_OFFER_POLICY.md#synthetic-stacking",
        "policy_provenance": policy_provenance(now - timedelta(hours=1)),
        "evaluated_at": now,
        "evidence_reference": "evidence:offer.synthetic.001",
    }
    values.update(overrides)
    return values


def make_candidate(**overrides):
    return subject.create_unadmitted_offer_configuration_candidate(
        **candidate_facts(**overrides)
    )


TEXT_CARRIERS = (
    "offer_configuration_id",
    "offer_policy_version",
    "eligibility_policy_reference",
    "stacking_policy_reference",
    "provenance_decision_id",
    "provenance_decided_by",
    "provenance_record_reference",
    "evidence_reference",
)


def prohibited_semantic_overrides(carrier, semantic, reference_location="filename"):
    if carrier == "offer_configuration_id":
        return {carrier: f"offer_config:{semantic}"}
    if carrier == "offer_policy_version":
        version = f"offer_policy:{semantic}.v1"
        return {
            carrier: version,
            "policy_provenance": policy_provenance(policy_version=version),
        }
    if carrier in (
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "provenance_record_reference",
    ):
        if reference_location == "anchor":
            reference = f"docs/OFFER_POLICY.md#{semantic}"
        else:
            reference = f"docs/{semantic}-POLICY.md#general-rules"
        if carrier == "provenance_record_reference":
            return {
                "policy_provenance": policy_provenance(
                    record_reference=reference
                )
            }
        return {carrier: reference}
    if carrier == "provenance_decision_id":
        decision_id = f"W10-{semantic.upper()}-001"
        return {
            "policy_provenance": policy_provenance(decision_id=decision_id)
        }
    if carrier == "provenance_decided_by":
        return {
            "policy_provenance": policy_provenance(
                decided_by=f"{semantic}-policy-owner"
            )
        }
    if carrier == "evidence_reference":
        return {carrier: f"evidence:{semantic}"}
    raise AssertionError(f"unsupported test carrier: {carrier}")


def projection(candidate=None):
    return dict(subject.project_offer_configuration_candidate(candidate or make_candidate()))


def exact_builtin_walk(value):
    if type(value) is tuple:
        for item in value:
            exact_builtin_walk(item)
        return
    assert type(value) in (str, int, bool)


def test_exact_base_sources_and_bounded_assurance_claim():
    contract = dict(subject.project_offer_configuration_contract())
    assert subject.CONTRACT_VERSION == "reserved-w10-offer-configuration-contract/1.0"
    assert subject.CATALOGUE_AUTHORITY_VERSION == CATALOGUE_VERSION
    assert contract["candidate_base_commit"] == BASE
    assert contract["candidate_base_tree"] == TREE
    assert contract["source_bindings"] == EXPECTED_SOURCES
    for _source_id, path, expected_hash, _accepted_at in EXPECTED_SOURCES:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash
    assert contract["assurance_status"] == (
        "contract_only_not_offer_policy_runtime_provider_checkout_entitlement_or_s4_completion"
    )


def test_exact_current_state_is_empty_disabled_and_partner_unsupported():
    state = dict(dict(subject.project_offer_configuration_contract())["accepted_operating_state"])
    assert state == {
        "offer_capability_required": True,
        "operational_offer_registry": (),
        "promotions_active": False,
        "promotion_codes_enabled": False,
        "promotion_codes": (),
        "eligibility_rules": (),
        "duration_rules": (),
        "stacking_rules": (),
        "discounted_prices": (),
        "partner_offers_enabled": False,
        "partner_offers_supported": False,
        "partner_offer_definitions": (),
    }


def test_static_and_candidate_authority_flags_are_all_exact_false():
    static_flags = dict(dict(subject.project_offer_configuration_contract())["authority_flags"])
    candidate_flags = dict(projection()["authority_flags"])
    expected = {
        "runtime_authority",
        "provider_authority",
        "provider_mapping_authority",
        "price_authority",
        "eligibility_decision_authority",
        "checkout_authority",
        "charge_authority",
        "entitlement_authority",
        "approval_authority",
        "activation_authority",
        "persistence_authority",
        "display_authority",
        "reconciliation_authority",
    }
    assert set(static_flags) == set(candidate_flags) == expected
    assert set(static_flags.values()) == set(candidate_flags.values()) == {False}


@pytest.mark.parametrize(
    ("plan_key", "base_amount", "proposed_amount"),
    (
        ("monthly", 2900, 2800),
        ("six_month", 15600, 15000),
        ("yearly", 28800, 28000),
    ),
)
def test_complete_future_policy_facts_form_only_an_unadmitted_candidate(
    plan_key, base_amount, proposed_amount
):
    view = projection(
        make_candidate(
            base_plan_key=plan_key,
            proposed_unit_amount_minor=proposed_amount,
        )
    )
    assert view["candidate_status"] == "unadmitted_offer_configuration_candidate"
    assert view["policy_acceptance_status"] == (
        "later_accepted_policy_version_authority_required"
    )
    assert view["base_plan_key"] == plan_key
    assert view["base_unit_amount_minor"] == base_amount
    assert view["proposed_unit_amount_minor"] == proposed_amount
    assert view["currency"] == "GBP"
    assert view["operational_registry_entry_created"] is False
    assert dict(view["accepted_operating_state"])["operational_offer_registry"] == ()


def test_candidate_represents_policy_references_without_evaluating_a_customer():
    view = projection()
    assert view["duration_count"] == 1
    assert view["duration_unit"] == "billing_periods"
    assert view["eligibility_policy_reference"].endswith("#synthetic-eligibility")
    assert view["stacking_policy_reference"].endswith("#synthetic-stacking")
    candidate_fields = set(view)
    for forbidden in (
        "customer_id",
        "customer_segment",
        "is_eligible",
        "eligibility_result",
        "discount_percentage",
        "discount_algorithm",
        "promotion_code",
        "entitlement_granted",
    ):
        assert forbidden not in candidate_fields


def test_candidate_identity_is_deterministic_but_handles_are_distinct_and_opaque():
    first = make_candidate()
    second = make_candidate()
    assert first is not second
    assert type(first) is subject.OfferConfigurationCandidate
    assert subject.validate_offer_configuration_candidate(first) == (
        subject.validate_offer_configuration_candidate(second)
    )
    first_projection = subject.project_offer_configuration_candidate(first)
    second_projection = subject.project_offer_configuration_candidate(first)
    assert first_projection == second_projection
    assert first_projection is not second_projection
    assert dict(first_projection)["content_identity"].startswith(
        "offer-configuration:sha256-"
    )
    exact_builtin_walk(first_projection)
    assert "future.synthetic.001" not in repr(first)


def test_policy_provenance_and_candidate_output_are_fully_detached():
    facts = candidate_facts()
    provenance = facts["policy_provenance"]
    candidate = subject.create_unadmitted_offer_configuration_candidate(**facts)
    replaced = tuple(
        (key, "forged") if key == "decided_by" else item for item in provenance for key in [item[0]]
    )
    facts["policy_provenance"] = replaced
    facts["base_plan_key"] = "yearly"
    view = projection(candidate)
    assert dict(view["policy_provenance"])["decided_by"] == "synthetic-policy-owner"
    assert view["base_plan_key"] == "monthly"


@pytest.mark.parametrize(
    "amount",
    (
        True,
        False,
        0,
        -1,
        2900,
        3000,
        28.0,
        float("nan"),
        float("inf"),
        "2800",
        None,
    ),
)
def test_money_is_exact_minor_unit_gbp_and_never_percentage_or_algorithm(amount):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(proposed_unit_amount_minor=amount)
    if type(amount) is float:
        assert math.isnan(amount) or math.isinf(amount) or amount == 28.0


@pytest.mark.parametrize(
    "overrides",
    (
        {"catalogue_authority_version": "latest"},
        {"base_plan_key": "MONTHLY"},
        {"base_plan_key": "weekly"},
        {"currency": "gbp"},
        {"currency": "USD"},
        {"duration_count": True},
        {"duration_count": 0},
        {"duration_count": 1.0},
        {"duration_unit": "forever"},
    ),
)
def test_unknown_catalogue_plan_currency_and_malformed_duration_fail(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


class StatefulTimezone(tzinfo):
    def utcoffset(self, value):
        return timedelta(0)

    def dst(self, value):
        return timedelta(0)


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "availability_ends_at": datetime(
                2026, 10, 1, 10, 0, tzinfo=timezone.utc
            )
        },
        {
            "availability_starts_at": datetime(
                2026, 11, 1, 10, 0, tzinfo=timezone.utc
            )
        },
        {"evaluated_at": datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)},
        {
            "evaluated_at": datetime(
                2026, 10, 1, 10, 0, tzinfo=StatefulTimezone()
            )
        },
        {"duration_count": IntSubclass(1)},
        {"duration_unit": StringSubclass("billing_periods")},
    ),
)
def test_contradictory_times_and_subtyped_fixed_facts_fail_closed(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


def test_future_dated_or_wrong_version_policy_provenance_fails_closed():
    now = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    for provenance in (
        policy_provenance(now + timedelta(seconds=1)),
        policy_provenance(policy_version="offer_policy:other.v1"),
        policy_provenance(decision_id="offer-policy-1"),
        policy_provenance(decision_id="SK-LIVE-123"),
        policy_provenance(record_reference="https://provider.example/policy#one"),
        policy_provenance(record_sha256="sha256:" + "A" * 64),
    ):
        with pytest.raises((TypeError, ValueError)):
            make_candidate(now=now, policy_provenance=provenance)


@pytest.mark.parametrize(
    "value",
    (
        "offer_config:partner.synthetic",
        "offer_config:reseller-synthetic",
        "offer_config:affiliate.synthetic",
        "offer_config:marketplace.synthetic",
    ),
)
def test_partner_and_reseller_configurations_are_rejected(value):
    with pytest.raises(ValueError, match="excluded|unsupported"):
        make_candidate(offer_configuration_id=value)


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "eligibility_policy_reference": (
                "docs/PARTNER_OFFERS.md#eligible"
            )
        },
        {"stacking_policy_reference": "docs/ReSeLlEr-RuLeS.md#stacking"},
        {
            "policy_provenance": policy_provenance(
                record_reference="docs/AFFILIATE_OFFER.md#one"
            )
        },
        {
            "policy_provenance": policy_provenance(
                decision_id="W10-MARKETPLACE-POLICY"
            )
        },
        {
            "policy_provenance": policy_provenance(
                decided_by="Coupon Policy Owner"
            )
        },
        {"offer_configuration_id": "offer_config:promotion-code-SAVE10"},
        {"evidence_reference": "evidence:PrOmOtIoN.CoDe.SAVE10"},
        {"eligibility_policy_reference": "customers/7.md#eligible"},
        {"eligibility_policy_reference": "docs/CUSTOMER-7.md#eligible"},
        {"stacking_policy_reference": "docs/SEGMENTS.md#stacking"},
    ),
)
def test_every_alternate_identifier_reference_provenance_and_evidence_carrier_rejects(
    overrides,
):
    with pytest.raises(ValueError, match="excluded|customer-specific|policy namespace"):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    ("policy_version", "configuration_id"),
    (
        (
            "offer_policy:PaRtNeR.LaUnCh.v1",
            "offer_config:future.standard.001",
        ),
        (
            "offer_policy:future.standard.v1",
            "offer_config:ReSeLlEr/launch.001",
        ),
        (
            "offer_policy:future.standard.v1",
            "offer_config:AfFiLiAtE-launch.001",
        ),
        (
            "offer_policy:future.standard.v1",
            "offer_config:marketPlace_launch.001",
        ),
        (
            "offer_policy:future.promo-code.v1",
            "offer_config:future.standard.001",
        ),
    ),
)
def test_mixed_case_separator_variants_and_matching_complete_provenance_fail(
    policy_version, configuration_id
):
    with pytest.raises(ValueError, match="excluded"):
        make_candidate(
            offer_configuration_id=configuration_id,
            offer_policy_version=policy_version,
            policy_provenance=policy_provenance(policy_version=policy_version),
        )


@pytest.mark.parametrize("carrier", TEXT_CARRIERS)
@pytest.mark.parametrize(
    "semantic",
    (
        "partnerACME",
        "resellerACME",
        "affiliateACME",
        "marketplaceACME",
        "couponACME",
        "promotioncodeACME",
    ),
)
def test_exact_48_concatenated_offer_semantic_reproduction_fails_closed(
    semantic, carrier
):
    with pytest.raises(ValueError, match="excluded"):
        make_candidate(**prohibited_semantic_overrides(carrier, semantic))


@pytest.mark.parametrize("carrier", TEXT_CARRIERS)
@pytest.mark.parametrize(
    "semantic",
    (
        "PaRtNeR-ACME",
        "ReSeLlEr-42",
        "AfFiLiAtE-acme",
        "MaRkEtPlAcE-acme",
        "CoUpOn-acme",
        "PrOmOtIoN-CoDe-SAVE10",
    ),
)
def test_mixed_case_separator_offer_semantics_fail_across_all_text_carriers(
    semantic, carrier
):
    with pytest.raises(ValueError, match="excluded"):
        make_candidate(**prohibited_semantic_overrides(carrier, semantic))


@pytest.mark.parametrize(
    "carrier",
    (
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "provenance_record_reference",
    ),
)
@pytest.mark.parametrize(
    "semantic",
    (
        "partnerACME",
        "resellerACME",
        "affiliateACME",
        "marketplaceACME",
        "couponACME",
        "promotioncodeSAVE10",
    ),
)
def test_concatenated_offer_semantics_fail_in_every_reference_anchor(
    semantic, carrier
):
    with pytest.raises(ValueError, match="excluded"):
        make_candidate(
            **prohibited_semantic_overrides(
                carrier, semantic, reference_location="anchor"
            )
        )


@pytest.mark.parametrize(
    "semantic",
    ("partnerACME", "ReSeLlEr42", "promotioncodeSAVE10"),
)
def test_fully_coherent_concatenated_prohibited_configuration_fails_closed(semantic):
    policy_version = f"offer_policy:{semantic}.v1"
    with pytest.raises(ValueError, match="excluded"):
        make_candidate(
            offer_configuration_id=f"offer_config:{semantic}",
            offer_policy_version=policy_version,
            eligibility_policy_reference=(
                f"docs/{semantic}-POLICY.md#general-rules"
            ),
            stacking_policy_reference=f"docs/OFFER_POLICY.md#{semantic}",
            policy_provenance=policy_provenance(
                decision_id=f"W10-{semantic.upper()}-001",
                policy_version=policy_version,
                decided_by=f"{semantic}-policy-owner",
                record_reference=f"docs/{semantic}-POLICY.md#general-rules",
            ),
            evidence_reference=f"evidence:{semantic}",
        )


@pytest.mark.parametrize("carrier", TEXT_CARRIERS)
@pytest.mark.parametrize(
    "split_root",
    (
        "par-tner",
        "res-eller",
        "affil-iate",
        "market-place",
        "cou-pon",
        "cus-tomer",
        "acc-ount",
        "mem-ber",
        "us-er",
        "seg-ment",
    ),
)
def test_full_80_case_hyphen_split_prohibited_root_matrix_fails_closed(
    split_root, carrier
):
    with pytest.raises(ValueError, match="excluded|customer-specific"):
        make_candidate(**prohibited_semantic_overrides(carrier, split_root))


@pytest.mark.parametrize(
    "carrier",
    (
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "provenance_record_reference",
    ),
)
@pytest.mark.parametrize(
    "split_root",
    (
        "PaR.TnEr",
        "rEs_ElLeR",
        "AfFiL:iaTe",
        "MaRkEt-PlAcE",
        "CoU.PoN",
        "CuS_ToMeR",
        "aCc:OuNt",
        "MeM.BeR",
        "uS_eR",
        "SeG-MeNt",
    ),
)
def test_mixed_separator_case_split_roots_fail_in_every_reference_anchor(
    split_root, carrier
):
    with pytest.raises(ValueError, match="excluded|customer-specific"):
        make_candidate(
            **prohibited_semantic_overrides(
                carrier, split_root, reference_location="anchor"
            )
        )


@pytest.mark.parametrize("carrier", TEXT_CARRIERS)
@pytest.mark.parametrize("neutral_word", ("accounting", "accountability"))
def test_exact_neutral_account_vocabulary_remains_accepted_across_text_carriers(
    neutral_word, carrier
):
    candidate = make_candidate(
        **prohibited_semantic_overrides(carrier, neutral_word)
    )
    assert set(dict(projection(candidate)["authority_flags"]).values()) == {False}


def test_ordinary_provider_neutral_policy_references_remain_structurally_accepted():
    candidate = make_candidate(
        offer_configuration_id="offer_config:future.standard.001",
        offer_policy_version="offer_policy:future.standard.v1",
        eligibility_policy_reference=(
            "docs/CUSTOMER_ELIGIBILITY_POLICY.md#general-rules"
        ),
        stacking_policy_reference="docs/STACKING_POLICY.md#general-rules",
        policy_provenance=policy_provenance(
            policy_version="offer_policy:future.standard.v1",
            record_reference="docs/OFFER_POLICY.md#future-standard",
        ),
        evidence_reference="evidence:offer.standard.001",
    )
    view = projection(candidate)
    assert view["eligibility_policy_reference"] == (
        "docs/CUSTOMER_ELIGIBILITY_POLICY.md#general-rules"
    )
    assert view["stacking_policy_reference"] == (
        "docs/STACKING_POLICY.md#general-rules"
    )
    assert set(dict(view["authority_flags"]).values()) == {False}


@pytest.mark.parametrize(
    "reference",
    (
        "docs/CUSTOMER_ELIGIBILITY_7.md#policy",
        "docs/customer-eligibility-policy.md#account-7",
        "docs/USER_ACCESS_POLICY.md#account-acme",
        "docs/MEMBER_POLICY_ACME.md#eligibility",
        "docs/Customer.Eligibility.Policy.Acme.md#GENERAL_RULES",
        "docs/USER-ACCESS-POLICY.md#member-7",
        "docs/OFFER_POLICY.md#customer-acme",
        "docs/OFFER_POLICY.md#ACCOUNT_7",
        "docs/customer7-eligibility-policy.md#general-rules",
        "docs/cus-tomer-7-policy.md#general-rules",
        "docs/OFFER_POLICY.md#useracme",
        "docs/OFFER_POLICY.md#account7",
    ),
)
@pytest.mark.parametrize(
    "carrier",
    (
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "provenance_record_reference",
    ),
)
def test_customer_specific_suffix_anchor_id_and_name_variants_fail_in_every_reference_carrier(
    reference, carrier
):
    if carrier == "provenance_record_reference":
        overrides = {
            "policy_provenance": policy_provenance(record_reference=reference)
        }
    else:
        overrides = {carrier: reference}
    with pytest.raises(ValueError, match="customer-specific"):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    "concatenated_subject",
    (
        "customeracme",
        "UsEr42",
        "memberACME",
        "ACCOUNT7",
        "segmentVIP",
    ),
)
@pytest.mark.parametrize("location", ("filename", "anchor"))
@pytest.mark.parametrize(
    "carrier",
    (
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "provenance_record_reference",
    ),
)
def test_concatenated_subject_roots_fail_in_filename_and_anchor_across_every_reference_carrier(
    concatenated_subject, location, carrier
):
    if location == "filename":
        reference = f"docs/{concatenated_subject}-policy.md#general-rules"
    else:
        reference = f"docs/OFFER_POLICY.md#{concatenated_subject}"
    if carrier == "provenance_record_reference":
        overrides = {
            "policy_provenance": policy_provenance(record_reference=reference)
        }
    else:
        overrides = {carrier: reference}
    with pytest.raises(ValueError, match="customer-specific"):
        make_candidate(**overrides)


@pytest.mark.parametrize("carrier", TEXT_CARRIERS)
@pytest.mark.parametrize(
    "concatenated_subject",
    ("customeracme", "UsEr42", "memberACME", "ACCOUNT7", "segmentVIP"),
)
def test_concatenated_subject_roots_fail_across_all_text_carriers(
    concatenated_subject, carrier
):
    with pytest.raises(ValueError, match="customer-specific"):
        make_candidate(
            **prohibited_semantic_overrides(carrier, concatenated_subject)
        )


@pytest.mark.parametrize(
    "reference",
    (
        "docs/CUSTOMER_ELIGIBILITY_POLICY.md#general-rules",
        "docs/customer.eligibility.policy.md#GENERAL_RULES",
        "docs/User-Access-Policy.md#standard_policy",
    ),
)
def test_narrow_generic_subject_policy_reference_grammar_remains_accepted(reference):
    candidate = make_candidate(
        eligibility_policy_reference=reference,
        stacking_policy_reference=reference,
        policy_provenance=policy_provenance(record_reference=reference),
    )
    view = projection(candidate)
    assert view["eligibility_policy_reference"] == reference
    assert view["stacking_policy_reference"] == reference
    assert dict(view["policy_provenance"])["record_reference"] == reference


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("offer_configuration_id", "offer_config:sk_live_123"),
        ("offer_policy_version", "offer_policy:client_secret_value"),
        ("eligibility_policy_reference", "docs/sk_test_value.md#eligibility"),
        ("stacking_policy_reference", "docs/POLICY.md#price_123"),
        ("evidence_reference", "evidence:whsec_value"),
    ),
)
def test_provider_identifier_and_secret_shaped_material_fail_closed(field, value):
    with pytest.raises(ValueError, match="secret-shaped|provider identifier"):
        make_candidate(**{field: value})


@pytest.mark.parametrize(
    "extra",
    (
        {"active": True},
        {"approved": True},
        {"promotion_code": "SAVE10"},
        {"partner_offer": False},
        {"eligible": True},
        {"access_granted": True},
        {"entitlement": "paid"},
        {"discount_percentage": 10},
        {"discount_algorithm": "percent"},
        {"provider_price_id": "price_123"},
        {"checkout_session_id": "cs_123"},
    ),
)
def test_enabling_decision_provider_and_algorithm_fields_are_never_accepted(extra):
    with pytest.raises(TypeError, match="unsupported fact"):
        subject.create_unadmitted_offer_configuration_candidate(
            **(candidate_facts() | extra)
        )


def test_exact_partial_extra_reordered_and_mutable_records_fail_closed():
    facts = candidate_facts()
    with pytest.raises(TypeError, match="exact ordered complete"):
        subject.create_unadmitted_offer_configuration_candidate(
            **{key: value for key, value in facts.items() if key != "currency"}
        )
    reordered = dict(reversed(tuple(facts.items())))
    with pytest.raises(TypeError, match="ordered"):
        subject.create_unadmitted_offer_configuration_candidate(**reordered)
    with pytest.raises(TypeError, match="exact complete tuple"):
        make_candidate(policy_provenance=dict(policy_provenance()))
    with pytest.raises(TypeError, match="exact complete tuple"):
        make_candidate(policy_provenance=list(policy_provenance()))
    malformed = policy_provenance()[:-1]
    with pytest.raises(TypeError, match="exact complete tuple"):
        make_candidate(policy_provenance=malformed)
    reordered_provenance = tuple(reversed(policy_provenance()))
    with pytest.raises(ValueError, match="reordered"):
        make_candidate(policy_provenance=reordered_provenance)


def test_callable_defaults_and_positional_substitution_supply_no_facts():
    create = subject.create_unadmitted_offer_configuration_candidate
    validate = subject.validate_offer_configuration_candidate
    original_create_defaults = create.__defaults__
    original_create_kwdefaults = create.__kwdefaults__
    original_validate_defaults = validate.__defaults__
    try:
        create.__defaults__ = (candidate_facts(),)
        create.__kwdefaults__ = candidate_facts()
        validate.__defaults__ = (make_candidate(),)
        with pytest.raises(TypeError, match="exactly 0 positional"):
            create(object(), **candidate_facts())
        with pytest.raises(TypeError, match="exact ordered complete"):
            create()
        with pytest.raises(TypeError, match="exactly 1 positional"):
            validate()
    finally:
        create.__defaults__ = original_create_defaults
        create.__kwdefaults__ = original_create_kwdefaults
        validate.__defaults__ = original_validate_defaults


def test_direct_construction_subclass_reconstruction_copy_and_pickle_fail_closed():
    with pytest.raises(TypeError, match="producer-issued"):
        subject.OfferConfigurationCandidate()
    forged = object.__new__(subject.OfferConfigurationCandidate)
    with pytest.raises(ValueError, match="not producer-issued"):
        subject.validate_offer_configuration_candidate(forged)

    class CandidateSubclass(subject.OfferConfigurationCandidate):
        pass

    subclassed = object.__new__(CandidateSubclass)
    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_offer_configuration_candidate(subclassed)
    candidate = make_candidate()
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError, match="not reconstructable|not serialisable"):
            operation(candidate)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX fork is unavailable")
def test_inherited_fork_lineage_retains_only_the_same_unadmitted_zero_authority_handle():
    candidate = make_candidate()
    saved_validate = subject.validate_offer_configuration_candidate
    read_fd, write_fd = os.pipe()
    child_pid = os.fork()
    if child_pid == 0:
        os.close(read_fd)
        try:
            view = dict(saved_validate(candidate))
            valid = (
                view["candidate_status"] == "unadmitted_offer_configuration_candidate"
                and set(dict(view["authority_flags"]).values()) == {False}
            )
            os.write(write_fd, b"inherited-unadmitted-zero" if valid else b"invalid")
        except BaseException:
            os.write(write_fd, b"error")
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    try:
        result = os.read(read_fd, 128)
    finally:
        os.close(read_fd)
    waited_pid, status = os.waitpid(child_pid, 0)
    assert waited_pid == child_pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert result == b"inherited-unadmitted-zero"


def test_reload_rejects_old_handle_while_saved_old_validator_retains_old_seal():
    candidate = make_candidate()
    saved_validate = subject.validate_offer_configuration_candidate
    expected = saved_validate(candidate)
    reloaded = importlib.reload(subject)

    with pytest.raises(TypeError, match="exact producer-issued"):
        reloaded.validate_offer_configuration_candidate(candidate)
    assert saved_validate(candidate) == expected
    new_candidate = reloaded.create_unadmitted_offer_configuration_candidate(
        **candidate_facts()
    )
    assert reloaded.validate_offer_configuration_candidate(new_candidate)
    with pytest.raises(TypeError, match="exact producer-issued"):
        saved_validate(new_candidate)


def _closure_objects(root):
    pending = [root]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        if isinstance(current, FunctionType) and current.__closure__:
            pending.extend(cell.cell_contents for cell in current.__closure__)


_PROJECTION_SLOT = "_OfferConfigurationCandidate__projection"
_SEAL_SLOT = "_OfferConfigurationCandidate__seal"
_INTEGRITY_IDENTITY_SLOT = "_OfferConfigurationCandidate__integrity_identity"


def _handle_integrity_parts(candidate):
    return tuple(
        object.__getattribute__(candidate, name)
        for name in (_PROJECTION_SLOT, _SEAL_SLOT, _INTEGRITY_IDENTITY_SLOT)
    )


def test_coherent_cross_candidate_substitution_cannot_authorize_candidate_a_as_b():
    candidate_a = make_candidate(offer_configuration_id="offer_config:future.a.001")
    candidate_b = make_candidate(
        offer_configuration_id="offer_config:future.b.001",
        evidence_reference="evidence:offer.b.001",
    )
    projection_b, seal_b, integrity_identity_b = _handle_integrity_parts(candidate_b)

    object.__setattr__(candidate_a, _PROJECTION_SLOT, projection_b)
    object.__setattr__(candidate_a, _SEAL_SLOT, seal_b)
    object.__setattr__(candidate_a, _INTEGRITY_IDENTITY_SLOT, integrity_identity_b)

    with pytest.raises(ValueError, match="handle identity"):
        subject.validate_offer_configuration_candidate(candidate_a)


def test_forged_handle_cannot_enrol_by_copying_coherent_issued_integrity_parts():
    issued = make_candidate()
    forged = object.__new__(subject.OfferConfigurationCandidate)
    projection_value, seal, integrity_identity = _handle_integrity_parts(issued)
    object.__setattr__(forged, _PROJECTION_SLOT, projection_value)
    object.__setattr__(forged, _SEAL_SLOT, seal)
    object.__setattr__(forged, _INTEGRITY_IDENTITY_SLOT, integrity_identity)

    with pytest.raises(ValueError, match="handle identity"):
        subject.project_offer_configuration_candidate(forged)


def test_issuance_closures_contain_no_mutable_registry_authority():
    for function in (
        subject.create_unadmitted_offer_configuration_candidate,
        subject.validate_offer_configuration_candidate,
        subject.project_offer_configuration_candidate,
    ):
        mutable_authority = [
            value
            for value in _closure_objects(function)
            if type(value) in (dict, list, set)
        ]
        assert mutable_authority == []


def test_candidate_and_integrity_seal_reject_ordinary_mutation():
    candidate = make_candidate()
    _projection, seal, _integrity_identity = _handle_integrity_parts(candidate)
    with pytest.raises(TypeError, match="producer-issued"):
        type(seal)()
    with pytest.raises(TypeError, match="immutable"):
        candidate.anything = "forged"
    with pytest.raises(TypeError, match="immutable"):
        del candidate._OfferConfigurationCandidate__seal
    with pytest.raises(TypeError, match="item assignment"):
        seal[0] = object()


def _recompute_identity(candidate_projection):
    without_identity = tuple(
        item for item in candidate_projection if item[0] != "content_identity"
    )
    payload = json.dumps(
        without_identity, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")
    identity = "offer-configuration:sha256-" + hashlib.sha256(payload).hexdigest()
    return tuple(
        (key, identity if key == "content_identity" else value)
        for key, value in candidate_projection
    )


def test_reconstructed_or_recomputed_identity_never_becomes_issued_authority():
    candidate = make_candidate()
    projected = subject.project_offer_configuration_candidate(candidate)
    recreated = tuple(tuple(item) for item in projected)
    assert recreated == projected and recreated is not projected
    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_offer_configuration_candidate(recreated)

    forged = tuple(
        (
            key,
            tuple((name, True if name == "price_authority" else flag) for name, flag in value)
            if key == "authority_flags"
            else value,
        )
        for key, value in projected
    )
    forged = _recompute_identity(forged)
    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_offer_configuration_candidate(forged)


def test_saved_protocol_resists_public_global_helper_and_descriptor_rebinding(monkeypatch):
    create = subject.create_unadmitted_offer_configuration_candidate
    validate = subject.validate_offer_configuration_candidate
    project = subject.project_offer_configuration_candidate
    project_contract = subject.project_offer_configuration_contract
    candidate = make_candidate()
    expected = project(candidate)
    forged = object.__new__(subject.OfferConfigurationCandidate)

    monkeypatch.setattr(subject, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(subject, "CATALOGUE_AUTHORITY_VERSION", "forged")
    monkeypatch.setattr(subject, "hashlib", object(), raising=False)
    monkeypatch.setattr(subject, "json", object(), raising=False)
    monkeypatch.setattr(subject, "tuple", list, raising=False)
    monkeypatch.setattr(subject, "any", lambda values: False, raising=False)
    monkeypatch.setattr(subject, "project_offer_configuration_candidate", lambda value: ())
    monkeypatch.setattr(
        subject.OfferConfigurationCandidate,
        _PROJECTION_SLOT,
        property(lambda self: "offer-configuration:sha256-" + "0" * 64),
    )
    monkeypatch.setattr(
        subject.OfferConfigurationCandidate,
        _SEAL_SLOT,
        property(lambda self: object()),
    )
    monkeypatch.setattr(
        subject.OfferConfigurationCandidate,
        "__new__",
        staticmethod(lambda cls, *args, **kwargs: forged),
    )
    monkeypatch.setattr(
        subject.OfferConfigurationCandidate,
        "__reduce_ex__",
        lambda self, protocol: (object, ()),
    )

    assert project(candidate) == expected
    assert validate(candidate) == expected
    assert create(**candidate_facts()) is not forged
    assert dict(project_contract())["catalogue_authority_version"] == CATALOGUE_VERSION
    with pytest.raises(ValueError, match="not producer-issued"):
        validate(subject.OfferConfigurationCandidate())
    reconstructed = pickle.loads(pickle.dumps(candidate))
    with pytest.raises(TypeError, match="exact producer-issued"):
        validate(reconstructed)


def test_supported_protocol_performs_no_file_io(monkeypatch):
    create = subject.create_unadmitted_offer_configuration_candidate
    project = subject.project_offer_configuration_candidate
    project_contract = subject.project_offer_configuration_contract

    def forbidden_open(*args, **kwargs):
        raise AssertionError("offer contract attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    candidate = create(**candidate_facts())
    assert projection(candidate)["candidate_status"].startswith("unadmitted_")
    assert dict(project_contract())["accepted_operating_state"]


def test_candidate_cannot_be_consumed_as_checkout_or_stripe_ingress_authority():
    candidate = make_candidate()
    checkout_facts = {
        "authentication_context": {},
        "owner_user_id": 7,
        "catalogue_authority_version": CATALOGUE_VERSION,
        "plan_key": "monthly",
        "intent_id": "checkout_intent:intent.001",
        "idempotency_key": "checkout_idempotency:intent.001",
        "requested_at": datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        "evaluated_at": datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        "valid_until": datetime(2026, 10, 1, 10, 5, tzinfo=timezone.utc),
        "return_destination_id": "reserved_billing_return_reconciliation",
        "replay_snapshot": {},
        "evidence_reference": "evidence:intent.001",
        "offer_configuration_candidate": candidate,
    }
    with pytest.raises(TypeError, match="unsupported fact"):
        checkout.create_checkout_request_candidate(7, **checkout_facts)
    assert stripe_ingress.allows_paid_request(
        candidate,
        object(),
        user_id=7,
        now=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
    ) is False
    ingress_source = (ROOT / "reserved/billing/local_stripe_initial_payment.py").read_text()
    assert "invoice['discounts'] != []" in ingress_source
    assert "line['discounts'] != []" in ingress_source
    assert "subscription['discounts'] != []" in ingress_source
    assert hashlib.sha256(ingress_source.encode()).hexdigest() == (
        "719b31b20cc19fcfcc002caffcad8502bf78c3f74c881a7f104e8c08c186dce3"
    )


def test_module_is_stdlib_only_has_exact_small_surface_and_no_action_verbs():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports == {"__future__", "datetime", "hashlib", "json", "re"}
    assert subject.__all__ == (
        "CONTRACT_VERSION",
        "CATALOGUE_AUTHORITY_VERSION",
        "OfferConfigurationCandidate",
        "project_offer_configuration_contract",
        "create_unadmitted_offer_configuration_candidate",
        "validate_offer_configuration_candidate",
        "project_offer_configuration_candidate",
    )
    forbidden = {
        "activate",
        "approve",
        "persist",
        "display",
        "price",
        "apply",
        "reconcile",
        "checkout",
        "charge",
        "grant_access",
        "map_to_provider",
    }
    assert forbidden.isdisjoint(subject.__all__)
    for name in subject.__all__[3:]:
        function = getattr(subject, name)
        assert tuple(inspect.signature(function).parameters) == ("args", "kwargs")
        assert function.__defaults__ is None
        assert function.__kwdefaults__ is None


def test_document_truthfully_preserves_scope_and_residual_limits():
    text = DOC.read_text(encoding="utf-8").casefold()
    for phrase in (
        BASE,
        TREE,
        "fd-w10-001",
        "operational offer registry remains empty",
        "unadmitted_offer_configuration_candidate",
        "later accepted policy/version authority",
        "partner and reseller configurations are rejected",
        "no actual offer",
        "existing stripe ingress continues to reject non-empty discount data",
        "does not complete w10-s4",
        "inherited process lineage",
        "posix fork",
        "reloaded module validator rejects an old handle",
        "0/8",
        "0/13",
    ):
        assert phrase in text
