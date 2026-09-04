"""Adversarial tests for W10-S6H initial-paid copy candidates."""

from __future__ import annotations

import ast
from collections import UserDict
from pathlib import Path
from types import MappingProxyType

import pytest

from reserved.billing import initial_paid_presentation as subject


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved/billing/initial_paid_presentation.py"
ALLOWED_PATHS = {
    "docs/W10_S6H_INITIAL_PAID_PRESENTATION_EVIDENCE.md",
    "reserved/billing/initial_paid_presentation.py",
    "tests/test_w10_initial_paid_presentation.py",
}
TOP_KEYS = (
    "schema_version",
    "classification",
    "kind",
    "fact_status",
    "payment_verified_at_utc",
    "entitlement_effective_at_utc",
    "paid_through_exclusive_utc",
    "next_renewal_at_utc",
    "evaluated_at_utc",
    "structural_references",
    "structural_confirmations",
    "copy",
    "authority",
)
REFERENCE_KEYS = (
    "owner_reference",
    "subscription_reference",
    "plan_reference",
)
CONFIRMATION_KEYS = (
    "successful_payment_observation_reconciled",
    "canonical_entitlement_state_observed",
    "renews_automatically",
)
COPY_KEYS = (
    "heading",
    "summary",
    "renewal_message",
    "renewal_boundary_label",
    "renewal_boundary_display",
    "paid_through_exclusive_utc",
    "access_message",
    "renewal_caveat",
)
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
        "schema_version": "reserved-w10-initial-paid-structural-facts/1.0",
        "owner_reference": "owner-41",
        "subscription_reference": "subscription-41",
        "plan_reference": "plan-monthly-29",
        "state": "initial_payment_verified_paid",
        "successful_payment_observation_reconciled": True,
        "canonical_entitlement_state_observed": True,
        "renews_automatically": True,
        "payment_verified_at_utc": "2026-10-01T12:00:00Z",
        "entitlement_effective_at_utc": "2026-10-01T12:00:01Z",
        "paid_through_exclusive_utc": "2026-11-01T12:00:01Z",
        "next_renewal_at_utc": "2026-11-01T12:00:01Z",
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
    return subject.build_initial_paid_presentation(
        facts=facts() if value is None else value,
        **expected,
    )


def top(value):
    return dict(subject.project_initial_paid_presentation(value))


def copy_values(value):
    return dict(top(value)["copy"])


def replace_field(value, field, replacement):
    return tuple((key, replacement if key == field else item) for key, item in value)


def test_fixed_copy_uses_exact_exclusive_renewal_boundary_and_caveats():
    result = top(build())
    assert tuple(result) == TOP_KEYS
    assert result["kind"] == "initial_payment_verified_paid"
    assert result["fact_status"] == "unauthenticated_structural_facts_only"
    assert copy_values(tuple(result.items())) == {
        "heading": "Your subscription payment is verified",
        "summary": "Your paid subscription has started.",
        "renewal_message": (
            "Your selected plan is set to renew automatically at "
            "1 November 2026 at 12:00:01 UTC."
        ),
        "renewal_boundary_label": "Next renewal boundary",
        "renewal_boundary_display": "1 November 2026 at 12:00:01 UTC",
        "paid_through_exclusive_utc": "2026-11-01T12:00:01Z",
        "access_message": "Access remains subject to Reserved's entitlement checks.",
        "renewal_caveat": (
            "Automatic renewal does not guarantee that a future payment will succeed."
        ),
    }


def test_output_is_detached_and_every_runtime_authority_is_exact_false():
    source = facts()
    result = build(source)
    projected = top(result)
    assert type(result) is tuple
    assert projected["classification"] == "detached_zero_authority_copy_candidate"
    confirmations = dict(projected["structural_confirmations"])
    assert tuple(confirmations) == CONFIRMATION_KEYS
    assert all(type(value) is bool and value is True for value in confirmations.values())
    authority = dict(projected["authority"])
    assert tuple(authority) == AUTHORITY_KEYS
    assert all(type(value) is bool and value is False for value in authority.values())
    assert subject.validate_initial_paid_presentation(result) == result
    assert subject.copy_initial_paid_presentation(result) == result
    assert subject.copy_initial_paid_presentation(result) is not result

    source["state"] = "checkout_complete"
    source["owner_reference"] = "owner-forged"
    source["paid_through_exclusive_utc"] = "2099-01-01T00:00:00Z"
    assert top(result)["kind"] == "initial_payment_verified_paid"
    assert dict(top(result)["structural_references"])["owner_reference"] == "owner-41"


def test_independent_reconstruction_validates_without_registry_or_identity():
    original = build()
    reconstructed = tuple(
        (key, tuple(tuple(pair) for pair in value) if type(value) is tuple else value)
        for key, value in original
    )
    assert reconstructed == original
    assert reconstructed is not original
    assert subject.validate_initial_paid_presentation(reconstructed) == original


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
        "checkout_complete",
        "browser_returned",
        "initial_payment_confirmed",
        "provider_paid",
        "payment_recovery",
        "initial_payment_pending",
        "",
        True,
        1,
        None,
    ),
)
def test_checkout_browser_provider_and_unknown_paid_labels_are_rejected(state):
    with pytest.raises(ValueError, match="state must be exactly"):
        build(facts(state=state))


@pytest.mark.parametrize("field", CONFIRMATION_KEYS)
@pytest.mark.parametrize("value", (False, 1, 0, "true", None))
def test_all_structural_confirmations_must_be_exact_true(field, value):
    with pytest.raises(ValueError, match=f"{field} must be exact true"):
        build(facts(**{field: value}))


def test_cancelled_paid_posture_cannot_build_automatic_renewal_copy():
    with pytest.raises(ValueError, match="renews_automatically must be exact true"):
        build(
            facts(
                renews_automatically=False,
                state="initial_payment_verified_paid",
                canonical_entitlement_state_observed=True,
                paid_through_exclusive_utc="2026-11-01T12:00:01Z",
                next_renewal_at_utc="2026-11-01T12:00:01Z",
            )
        )


def test_extra_status_or_changed_fact_order_fails_closed():
    injected = facts()
    injected["provider_status"] = "paid"
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(injected)
    reordered = dict(reversed(tuple(facts().items())))
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(reordered)


@pytest.mark.parametrize(
    ("verified", "effective", "evaluated", "accepted"),
    (
        (
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:00Z",
            True,
        ),
        (
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:04:59Z",
            "2026-10-01T12:04:59Z",
            True,
        ),
        (
            "2026-10-01T12:00:01Z",
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:01Z",
            False,
        ),
        (
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:02Z",
            "2026-10-01T12:00:01Z",
            False,
        ),
        (
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:01Z",
            "2026-10-01T12:05:00Z",
            False,
        ),
    ),
)
def test_verified_effective_evaluated_order_and_five_minute_window(
    verified, effective, evaluated, accepted
):
    value = facts(
        payment_verified_at_utc=verified,
        entitlement_effective_at_utc=effective,
        evaluated_at_utc=evaluated,
    )
    if accepted:
        assert top(build(value))["evaluated_at_utc"] == evaluated
    else:
        with pytest.raises(ValueError, match="out of order|stale"):
            build(value)


@pytest.mark.parametrize(
    ("paid_through", "accepted"),
    (
        ("2026-10-01T12:05:00Z", True),
        ("2026-10-01T12:04:59Z", False),
        ("2026-10-01T12:04:58Z", False),
    ),
)
def test_paid_through_boundary_must_be_exactly_future_not_derived(
    paid_through, accepted
):
    value = facts(
        paid_through_exclusive_utc=paid_through,
        next_renewal_at_utc=paid_through,
    )
    if accepted:
        assert top(build(value))["paid_through_exclusive_utc"] == paid_through
    else:
        with pytest.raises(ValueError, match="exact and future"):
            build(value)


def test_next_renewal_must_be_independently_supplied_and_equal_paid_through():
    with pytest.raises(ValueError, match="must match exactly"):
        build(facts(next_renewal_at_utc="2026-11-01T12:00:02Z"))
    with pytest.raises(ValueError, match="must match exactly"):
        build(facts(next_renewal_at_utc="2026-10-31T12:00:01Z"))


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-10-01",
        "2026-10-01T12:00:00",
        "2026-10-01T12:00:00+00:00",
        "2026-10-01T12:00:00.000Z",
        "2026-10-01t12:00:00z",
        "2026-02-30T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-10-01T24:00:00Z",
        20261001,
        True,
        None,
    ),
)
def test_invalid_noncanonical_and_nonexact_timestamps_fail_closed(timestamp):
    with pytest.raises(ValueError, match="timestamp"):
        build(facts(payment_verified_at_utc=timestamp))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("owner_reference", "sk_live_secret"),
        ("subscription_reference", "sub_providerobject"),
        ("plan_reference", "plan-client-secret-value"),
    ),
)
def test_secret_and_provider_object_shaped_supplied_references_fail_closed(field, value):
    with pytest.raises(ValueError, match="secret-shaped|provider object"):
        build(facts(**{field: value}))


@pytest.mark.parametrize(
    ("expected_name", "value"),
    (
        ("expected_owner_reference", "cus_customer"),
        ("expected_subscription_reference", "subscription-access-token-value"),
        ("expected_plan_reference", "price_liveplan"),
    ),
)
def test_secret_and_provider_object_shaped_expected_references_fail_closed(
    expected_name, value
):
    with pytest.raises(ValueError, match="secret-shaped|provider object"):
        build(**{expected_name: value})


def test_reconstructed_output_rejects_secret_and_provider_object_references():
    result = build()
    references = dict(top(result)["structural_references"])
    references["subscription_reference"] = "sub_forged"
    forged = replace_field(result, "structural_references", tuple(references.items()))
    with pytest.raises(ValueError, match="provider object"):
        subject.validate_initial_paid_presentation(forged)

    references["subscription_reference"] = "subscription-client-secret-value"
    forged = replace_field(result, "structural_references", tuple(references.items()))
    with pytest.raises(ValueError, match="secret-shaped"):
        subject.validate_initial_paid_presentation(forged)


def test_copy_does_not_invent_vat_invoice_refund_or_provider_mechanics():
    joined = " ".join(copy_values(build()).values()).lower()
    for forbidden in (
        "stripe",
        "provider",
        "vat",
        "tax",
        "invoice",
        "refund",
        "cancel",
        "chargeback",
        "guaranteed renewal",
        "access granted",
        "owner-41",
        "subscription-41",
        "plan-monthly-29",
    ):
        assert forbidden not in joined


def test_builder_requires_exact_keywords_and_exact_dicts():
    builder = subject.build_initial_paid_presentation
    kwargs = {
        "facts": facts(),
        "expected_owner_reference": "owner-41",
        "expected_subscription_reference": "subscription-41",
        "expected_plan_reference": "plan-monthly-29",
    }
    with pytest.raises(TypeError, match="exact keywords"):
        builder(facts(), **{key: value for key, value in kwargs.items() if key != "facts"})
    with pytest.raises(TypeError, match="exact keywords"):
        builder(**kwargs, provider_status="paid")
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(UserDict(facts()))
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(MappingProxyType(facts()))


def test_exact_container_key_and_scalar_types_are_required():
    class tuple_subclass(tuple):
        pass

    class string_subclass(str):
        pass

    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_initial_paid_presentation(tuple_subclass(build()))
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_initial_paid_presentation(
            replace_field(build(), "kind", string_subclass("initial_payment_verified_paid"))
        )
    with pytest.raises(ValueError, match="non-exact built-in"):
        confirmations = tuple(
            (key, 1 if key == CONFIRMATION_KEYS[0] else value)
            for key, value in top(build())["structural_confirmations"]
        )
        subject.validate_initial_paid_presentation(
            replace_field(build(), "structural_confirmations", confirmations)
        )


def test_reconstructed_output_preserves_renewal_posture_and_boundary_equality():
    original = build()
    confirmations = tuple(
        (key, False if key == "renews_automatically" else value)
        for key, value in top(original)["structural_confirmations"]
    )
    with pytest.raises(ValueError, match="exact true"):
        subject.validate_initial_paid_presentation(
            replace_field(original, "structural_confirmations", confirmations)
        )
    with pytest.raises(ValueError, match="boundaries are inconsistent"):
        subject.validate_initial_paid_presentation(
            replace_field(original, "next_renewal_at_utc", "2026-11-01T12:00:02Z")
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("classification", "trusted_copy"),
        ("kind", "paid"),
        ("fact_status", "authenticated"),
        ("payment_verified_at_utc", "2026-10-01T12:05:00Z"),
        ("entitlement_effective_at_utc", "2026-10-01T11:59:59Z"),
        ("paid_through_exclusive_utc", "2026-10-01T12:04:59Z"),
        ("next_renewal_at_utc", "2026-11-01T12:00:02Z"),
        ("evaluated_at_utc", "2026-10-01T12:05:00Z"),
        ("copy", (("heading", "Payment succeeded"),)),
        ("authority", tuple((key, key == "access_authority") for key in AUTHORITY_KEYS)),
    ),
)
def test_reconstructed_output_tampering_fails_closed(field, replacement):
    with pytest.raises(ValueError):
        subject.validate_initial_paid_presentation(replace_field(build(), field, replacement))


def test_module_has_no_io_network_clock_or_runtime_adapter_imports():
    tree = ast.parse(MODULE.read_text())
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports <= {"__future__", "datetime", "re"}
    forbidden_names = {
        "open",
        "print",
        "input",
        "requests",
        "socket",
        "subprocess",
        "time",
        "date_today",
        "datetime_now",
        "utcnow",
        "stripe",
    }
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not (used_names & forbidden_names)


def test_no_registry_identity_capability_or_mutable_module_state():
    source = MODULE.read_text().lower()
    for forbidden in (
        "registry",
        "weakref",
        "id(",
        "uuid",
        "token_hex",
        "compare_digest",
        "hmac",
    ):
        assert forbidden not in source
    public_mutable = {
        name: value
        for name, value in vars(subject).items()
        if not name.startswith("_") and type(value) in (dict, list, set)
    }
    assert public_mutable == {}


def test_diff_is_confined_to_exact_package_paths():
    import subprocess

    changed = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    changed_paths = {line[3:] for line in changed if line}
    assert changed_paths <= ALLOWED_PATHS
