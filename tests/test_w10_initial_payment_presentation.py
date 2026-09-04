"""Adversarial tests for W10-S6G initial-payment copy candidates."""

from __future__ import annotations

import ast
from collections import UserDict
from pathlib import Path
from types import MappingProxyType

import pytest

from reserved.billing import initial_payment_presentation as subject


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved/billing/initial_payment_presentation.py"
ALLOWED_PATHS = {
    "docs/W10_S6G_INITIAL_PAYMENT_PRESENTATION_EVIDENCE.md",
    "reserved/billing/initial_payment_presentation.py",
    "tests/test_w10_initial_payment_presentation.py",
}
TOP_KEYS = (
    "schema_version",
    "classification",
    "kind",
    "verification_status",
    "observed_at_utc",
    "evaluated_at_utc",
    "structural_references",
    "copy",
    "authority",
)
REFERENCE_KEYS = (
    "owner_reference",
    "subscription_reference",
    "plan_reference",
)
COPY_KEYS = ("heading", "summary", "access_message", "next_step")
AUTHORITY_KEYS = (
    "upstream_admission_authority",
    "authentication_authority",
    "customer_render_authority",
    "delivery_authority",
    "notification_authority",
    "entitlement_authority",
    "access_authority",
    "provider_authority",
    "charge_authority",
    "refund_authority",
    "persistence_authority",
    "activation_authority",
)


def facts(**updates):
    value = {
        "schema_version": "reserved-w10-initial-payment-structural-facts/1.0",
        "owner_reference": "owner-41",
        "subscription_reference": "subscription-41",
        "plan_reference": "plan-monthly-29",
        "state": "initial_payment_pending",
        "observed_at_utc": "2026-10-01T12:00:00Z",
        "evaluated_at_utc": "2026-10-01T12:04:59Z",
    }
    value.update(updates)
    return value


def build(value=None, **expected_updates):
    expected = {
        "expected_owner_reference": "owner-41",
        "expected_subscription_reference": "subscription-41",
        "expected_plan_reference": "plan-monthly-29",
    }
    expected.update(expected_updates)
    return subject.build_initial_payment_presentation(
        facts=facts() if value is None else value,
        **expected,
    )


def top(value):
    return dict(subject.project_initial_payment_presentation(value))


def copy_values(value):
    return dict(top(value)["copy"])


def replace_field(value, field, replacement):
    return tuple((key, replacement if key == field else item) for key, item in value)


@pytest.mark.parametrize(
    ("state", "status", "expected_copy"),
    (
        (
            "initial_payment_pending",
            "unverified",
            {
                "heading": "We are verifying your subscription payment",
                "summary": "Your initial subscription payment is still being verified.",
                "access_message": "Paid access has not started.",
                "next_step": (
                    "If you need help while verification is pending, contact support."
                ),
            },
        ),
        (
            "initial_payment_failed",
            "failed_verification",
            {
                "heading": "We could not verify your subscription payment",
                "summary": "Your initial subscription payment could not be verified.",
                "access_message": "Paid access has not started.",
                "next_step": "Contact support if you need help.",
            },
        ),
    ),
)
def test_only_two_fixed_customer_safe_states(state, status, expected_copy):
    result = build(facts(state=state))
    projected = top(result)
    assert tuple(projected) == TOP_KEYS
    assert projected["kind"] == state
    assert projected["verification_status"] == status
    assert copy_values(result) == expected_copy
    assert tuple(copy_values(result)) == COPY_KEYS


def test_output_is_recursively_detached_and_every_authority_is_exact_false():
    source = facts()
    result = build(source)
    projected = top(result)
    authority = dict(projected["authority"])
    assert type(result) is tuple
    assert projected["classification"] == "detached_zero_authority_copy_candidate"
    assert tuple(authority) == AUTHORITY_KEYS
    assert all(type(value) is bool and value is False for value in authority.values())
    assert subject.validate_initial_payment_presentation(result) == result
    assert subject.copy_initial_payment_presentation(result) == result
    assert subject.copy_initial_payment_presentation(result) is not result

    source["state"] = "paid"
    source["owner_reference"] = "owner-forged"
    source["observed_at_utc"] = "2099-01-01T00:00:00Z"
    assert top(result)["kind"] == "initial_payment_pending"
    assert dict(top(result)["structural_references"])["owner_reference"] == "owner-41"


def test_independent_reconstruction_validates_without_identity_or_registry():
    original = build()
    reconstructed = tuple(
        (key, tuple(tuple(pair) for pair in value) if type(value) is tuple else value)
        for key, value in original
    )
    assert reconstructed == original
    assert reconstructed is not original
    assert subject.validate_initial_payment_presentation(reconstructed) == original


@pytest.mark.parametrize(
    ("expected_name", "expected_value", "match"),
    (
        ("expected_owner_reference", "owner-42", "owner_reference"),
        ("expected_subscription_reference", "subscription-42", "subscription_reference"),
        ("expected_plan_reference", "plan-yearly-288", "plan_reference"),
    ),
)
def test_cross_owner_subscription_and_plan_facts_fail_closed(
    expected_name, expected_value, match
):
    with pytest.raises(ValueError, match=match):
        build(**{expected_name: expected_value})


@pytest.mark.parametrize(
    "state",
    (
        "paid",
        "active",
        "succeeded",
        "success",
        "initial_payment_confirmed",
        "provider_paid",
        "requires_action",
        "processing",
        "",
        True,
        1,
        None,
    ),
)
def test_unknown_provider_and_paid_success_states_are_never_accepted(state):
    with pytest.raises(ValueError, match="unsupported.*state"):
        build(facts(state=state))


def test_extra_provider_status_or_contradictory_fact_is_rejected():
    injected = facts()
    injected["provider_status"] = "succeeded"
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(injected)
    reversed_facts = dict(reversed(tuple(facts().items())))
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(reversed_facts)


@pytest.mark.parametrize(
    ("observed", "evaluated", "accepted"),
    (
        ("2026-10-01T12:00:00Z", "2026-10-01T12:00:00Z", True),
        ("2026-10-01T12:00:00Z", "2026-10-01T12:04:59Z", True),
        ("2026-10-01T12:00:00Z", "2026-10-01T11:59:59Z", False),
        ("2026-10-01T12:00:00Z", "2026-10-01T12:05:00Z", False),
        ("2026-10-01T12:00:00Z", "2026-10-01T12:05:01Z", False),
    ),
)
def test_structural_freshness_is_observed_inclusive_and_five_minutes_exclusive(
    observed, evaluated, accepted
):
    value = facts(observed_at_utc=observed, evaluated_at_utc=evaluated)
    if accepted:
        assert top(build(value))["evaluated_at_utc"] == evaluated
    else:
        with pytest.raises(ValueError, match="future or out of order|stale"):
            build(value)


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-10-01",
        "2026-10-01T12:00:00",
        "2026-10-01T12:00:00+00:00",
        "2026-10-01T12:00:00.000Z",
        "2026-10-01t12:00:00z",
        "2026-02-30T12:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-10-01T24:00:00Z",
        True,
        1,
        1.0,
        None,
    ),
)
def test_noncanonical_timestamp_and_bool_int_float_tricks_fail_closed(timestamp):
    with pytest.raises(ValueError, match="timestamp"):
        build(facts(evaluated_at_utc=timestamp))


def test_exact_dict_string_and_keyword_call_types_are_required(monkeypatch):
    for hostile_mapping in (
        type("DictSubclass", (dict,), {})(facts()),
        UserDict(facts()),
        MappingProxyType(facts()),
    ):
        with pytest.raises(TypeError, match="exact ordered"):
            build(hostile_mapping)
    string_subclass = type("StringSubclass", (str,), {})
    with pytest.raises(ValueError, match="version"):
        build(facts(schema_version=string_subclass(subject.FACTS_VERSION)))
    with pytest.raises(ValueError, match="bounded exact string"):
        build(expected_owner_reference=string_subclass("owner-41"))

    builder = subject.build_initial_payment_presentation
    monkeypatch.setattr(builder, "__defaults__", (facts(),))
    monkeypatch.setattr(builder, "__kwdefaults__", {"expected_owner_reference": "owner-41"})
    with pytest.raises(TypeError, match="exact keywords"):
        builder(facts())
    with pytest.raises(TypeError, match="exact keywords"):
        builder(facts=facts())
    with pytest.raises(TypeError, match="exact keywords"):
        builder(
            facts=facts(),
            expected_owner_reference="owner-41",
            expected_subscription_reference="subscription-41",
            expected_plan_reference="plan-monthly-29",
            provider_status="paid",
        )


def test_tuple_and_string_subclasses_cannot_enter_validated_output():
    tuple_subclass = type("TupleSubclass", (tuple,), {})
    string_subclass = type("StringSubclassOutput", (str,), {})
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_initial_payment_presentation(tuple_subclass(build()))
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_initial_payment_presentation(
            replace_field(build(), "kind", string_subclass("initial_payment_pending"))
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("schema_version", "forged"),
        ("classification", "authenticated"),
        ("kind", "paid"),
        ("verification_status", "verified"),
        ("observed_at_utc", "2026-10-01T12:05:00Z"),
    ),
)
def test_altered_top_level_fields_fail_validation(field, replacement):
    with pytest.raises(ValueError):
        subject.validate_initial_payment_presentation(replace_field(build(), field, replacement))


def test_altered_copy_kind_relationship_and_authority_fail_validation():
    pending = build()
    failed_copy = top(build(facts(state="initial_payment_failed")))["copy"]
    with pytest.raises(ValueError, match="copy is inconsistent"):
        subject.validate_initial_payment_presentation(
            replace_field(pending, "copy", failed_copy)
        )

    copy_tuple = top(pending)["copy"]
    altered_copy = replace_field(copy_tuple, "access_message", "Paid access has started.")
    with pytest.raises(ValueError, match="copy is inconsistent"):
        subject.validate_initial_payment_presentation(
            replace_field(pending, "copy", altered_copy)
        )

    authority = top(pending)["authority"]
    altered_authority = replace_field(authority, "access_authority", True)
    with pytest.raises(ValueError, match="authority"):
        subject.validate_initial_payment_presentation(
            replace_field(pending, "authority", altered_authority)
        )
    int_authority = replace_field(authority, "access_authority", 0)
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_initial_payment_presentation(
            replace_field(pending, "authority", int_authority)
        )


@pytest.mark.parametrize(
    "dangerous",
    (
        "sk_live_not-a-real-secret",
        "rk-test-not-real",
        "whsec_not-real",
        "owner:client_secret:value",
        "subscription/access-token/example",
        "cus_SecretCustomer41",
        "sub_provider-id-41",
        "price_monthly29",
        "prod_RESERVED41",
        "pm_123ABC",
        "evt_123ABC",
        "seti_123ABC",
    ),
)
@pytest.mark.parametrize(
    ("fact_field", "expected_field"),
    (
        ("owner_reference", "expected_owner_reference"),
        ("subscription_reference", "expected_subscription_reference"),
        ("plan_reference", "expected_plan_reference"),
    ),
)
def test_secret_and_provider_object_shaped_supplied_references_fail_closed(
    dangerous, fact_field, expected_field
):
    with pytest.raises(ValueError, match="secret-shaped|provider object"):
        build(facts(**{fact_field: dangerous}), **{expected_field: dangerous})


@pytest.mark.parametrize(
    ("expected_field", "dangerous"),
    (
        ("expected_owner_reference", "cus_123ABC"),
        ("expected_subscription_reference", "sub_123ABC"),
        ("expected_plan_reference", "sk_live_not-real"),
    ),
)
def test_dangerous_independently_expected_references_fail_before_matching(
    expected_field, dangerous
):
    with pytest.raises(ValueError, match="secret-shaped|provider object"):
        build(**{expected_field: dangerous})


def test_reconstructed_output_cannot_reintroduce_secret_or_provider_references():
    result = build()
    references = top(result)["structural_references"]
    for field, dangerous in (
        ("owner_reference", "cus_123ABC"),
        ("subscription_reference", "sub_provider-id-41"),
        ("plan_reference", "sk_live_not-real"),
    ):
        with pytest.raises(ValueError, match="secret-shaped|provider object"):
            subject.validate_initial_payment_presentation(
                replace_field(
                    result,
                    "structural_references",
                    replace_field(references, field, dangerous),
                )
            )


def test_ordinary_internal_references_remain_structural_and_never_enter_copy():
    result = build()
    rendered_candidate = " ".join(copy_values(result).values()).lower()
    for forbidden in (
        "owner-41",
        "subscription-41",
        "plan-monthly-29",
        "stripe",
        "provider",
        "refund",
        "entitlement",
        "checkout",
        "try again",
        "retry",
    ):
        assert forbidden not in rendered_candidate
    assert dict(top(result)["structural_references"]) == {
        "owner_reference": "owner-41",
        "subscription_reference": "subscription-41",
        "plan_reference": "plan-monthly-29",
    }


def test_source_has_no_runtime_io_clock_upstream_import_or_registry():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    from_imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imports == {"re"}
    assert from_imports == {"__future__", "datetime"}
    for forbidden in (
        "open(",
        "Path(",
        "requests",
        "urllib",
        "socket",
        "subprocess",
        "datetime.now",
        "datetime.utcnow",
        ".today(",
        "entitlement_core",
        "checkout_intent_contract",
        "stripe",
        "weakref",
        "registry",
    ):
        assert forbidden not in source


def test_exported_constants_do_not_mutate_closed_contract(monkeypatch):
    monkeypatch.setattr(subject, "FACTS_VERSION", "forged")
    monkeypatch.setattr(subject, "PRESENTATION_VERSION", "forged")
    monkeypatch.setattr(subject, "STRUCTURAL_FRESHNESS_SECONDS", 999999)
    result = build()
    assert top(result)["schema_version"] == (
        "reserved-w10-initial-payment-presentation/1.0"
    )
    with pytest.raises(ValueError, match="stale"):
        build(facts(evaluated_at_utc="2026-10-01T12:05:00Z"))


def test_git_diff_is_limited_to_exact_authorised_paths():
    import subprocess

    changed = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    paths = {line[3:] for line in changed if line}
    assert paths <= ALLOWED_PATHS
