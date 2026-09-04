"""Adversarial tests for the detached W10-S6F cancellation-copy candidate."""

from __future__ import annotations

import gc
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from reserved.billing import cancellation_presentation as subject


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved/billing/cancellation_presentation.py"
ALLOWED_PATHS = {
    "docs/W10_S6F_CANCELLATION_PRESENTATION_EVIDENCE.md",
    "reserved/billing/cancellation_presentation.py",
    "tests/test_w10_cancellation_presentation.py",
}
AUTHORITY_KEYS = (
    "upstream_admission_authority",
    "customer_render_authority",
    "delivery_authority",
    "notification_authority",
    "entitlement_authority",
    "access_decision_authority",
    "provider_authority",
    "cancellation_authority",
    "refund_authority",
    "persistence_authority",
    "activation_authority",
)


def facts(**updates):
    value = {
        "schema_version": "reserved-w10-cancellation-structural-facts/1.0",
        "owner_reference": "owner-61",
        "billing_account_reference": "billing-61",
        "subscription_reference": "subscription-61",
        "state": "cancellation_confirmed_end_of_paid_period",
        "future_renewal_stopped": True,
        "paid_period_started_at_utc": "2026-10-01T00:00:00Z",
        "cancellation_verified_at_utc": "2026-10-12T09:14:07Z",
        "paid_through_exclusive_utc": "2026-11-01T00:00:00Z",
        "cancellation_effective_at_utc": "2026-11-01T00:00:00Z",
        "evaluated_at_utc": "2026-10-12T09:14:07Z",
    }
    value.update(updates)
    return value


def build(value=None, *, owner="owner-61", subscription="subscription-61"):
    return subject.build_cancellation_presentation(
        facts=facts() if value is None else value,
        expected_owner_reference=owner,
        expected_subscription_reference=subscription,
    )


def top(value):
    return dict(subject.project_cancellation_presentation(value))


def copy_values(value):
    return dict(top(value)["copy"])


def test_exact_copy_stops_future_renewal_and_preserves_exclusive_boundary():
    copy = copy_values(build())
    assert copy == {
        "heading": "Your subscription will not renew",
        "summary": (
            "Your cancellation has been recorded for the end of your current "
            "paid period."
        ),
        "renewal_message": "Future automatic renewals are stopped.",
        "paid_period_message": (
            "Subject to Reserved's entitlement checks, you can continue using "
            "Reserved before 1 November 2026 at 00:00:00 UTC under your "
            "already-paid period."
        ),
        "paid_through_label": "Already-paid period ends at",
        "paid_through_display": "1 November 2026 at 00:00:00 UTC",
        "paid_through_exclusive_utc": "2026-11-01T00:00:00Z",
        "boundary_message": (
            "Starting 1 November 2026 at 00:00:00 UTC, this message does not "
            "promise or grant access. Reserved's entitlement policy determines access."
        ),
        "rights_message": (
            "This does not affect any mandatory consumer or statutory rights."
        ),
    }
    joined = " ".join(copy.values()).lower()
    assert "future automatic renewals are stopped" in joined
    assert "before 1 november 2026 at 00:00:00 utc" in joined
    assert "starting 1 november 2026 at 00:00:00 utc" in joined
    assert "mandatory consumer or statutory rights" in joined
    assert "access until" not in joined
    assert "access through" not in joined


def test_result_is_recursively_detached_with_every_authority_false():
    result = build()
    projected = top(result)
    assert type(result) is tuple
    assert projected["classification"] == "detached_zero_authority_copy_candidate"
    assert projected["kind"] == "cancellation_at_paid_period_end"
    authority = dict(projected["authority"])
    assert tuple(authority) == AUTHORITY_KEYS
    assert all(type(value) is bool and value is False for value in authority.values())
    assert subject.validate_cancellation_presentation(result) == result
    copied = subject.copy_cancellation_presentation(result)
    assert copied == result
    assert copied is not result


def test_equal_reconstruction_is_valid_without_identity_or_registry():
    original = build()
    reconstructed = tuple(
        (key, tuple(tuple(pair) for pair in value) if type(value) is tuple else value)
        for key, value in original
    )
    assert reconstructed == original
    assert reconstructed is not original
    assert subject.validate_cancellation_presentation(reconstructed) == original


def test_mutating_input_after_build_cannot_change_result():
    source = facts()
    result = build(source)
    source["owner_reference"] = "owner-elsewhere"
    source["state"] = "active"
    source["paid_through_exclusive_utc"] = "2099-01-01T00:00:00Z"
    assert copy_values(result)["paid_through_exclusive_utc"] == "2026-11-01T00:00:00Z"


def test_owner_and_subscription_are_bound_but_never_rendered():
    with pytest.raises(ValueError, match="expected owner"):
        build(owner="owner-62")
    with pytest.raises(ValueError, match="expected subscription"):
        build(subscription="subscription-62")
    joined = " ".join(copy_values(build()).values()).lower()
    for forbidden in (
        "owner-61",
        "billing-61",
        "subscription-61",
        "stripe",
        "provider",
        "refund approved",
        "chargeback",
        "cus_",
        "sub_",
        "sk_live",
        "<",
        ">",
        "&",
    ):
        assert forbidden not in joined


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-11-01",
        "2026-11-01T00:00:00",
        "2026-11-01T00:00:00+00:00",
        "2026-11-01T00:00:00.000Z",
        "2026-11-01t00:00:00z",
        "2026-02-30T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-11-01T24:00:00Z",
        True,
        False,
        1,
        1.0,
        None,
    ),
)
def test_noncanonical_or_non_exact_timestamps_fail_closed(timestamp):
    with pytest.raises(ValueError, match="timestamp"):
        build(facts(paid_through_exclusive_utc=timestamp))


def test_exact_nonzero_second_is_preserved_in_every_boundary_copy_field():
    result = copy_values(
        build(
            facts(
                paid_through_exclusive_utc="2026-11-01T10:22:37Z",
                cancellation_effective_at_utc="2026-11-01T10:22:37Z",
            )
        )
    )
    display = "1 November 2026 at 10:22:37 UTC"
    assert result["paid_through_display"] == display
    assert display in result["paid_period_message"]
    assert result["boundary_message"].startswith(f"Starting {display},")


def test_cancellation_effective_boundary_must_exactly_equal_paid_through_boundary():
    for effective in ("2026-10-31T23:59:59Z", "2026-11-01T00:00:01Z"):
        with pytest.raises(ValueError, match="must equal paid-through"):
            build(facts(cancellation_effective_at_utc=effective))


def test_paid_period_and_verification_ordering_fail_closed():
    with pytest.raises(ValueError, match="paid period is contradictory"):
        build(facts(paid_period_started_at_utc="2026-11-01T00:00:00Z"))
    with pytest.raises(ValueError, match="verification is outside"):
        build(facts(cancellation_verified_at_utc="2026-09-30T23:59:59Z"))
    with pytest.raises(ValueError, match="verification is outside"):
        build(facts(cancellation_verified_at_utc="2026-11-01T00:00:00Z"))


@pytest.mark.parametrize(
    ("evaluated", "accepted"),
    (
        ("2026-10-12T09:14:06Z", False),
        ("2026-10-12T09:14:07Z", True),
        ("2026-10-31T23:59:59Z", True),
        ("2026-11-01T00:00:00Z", False),
        ("2026-11-01T00:00:01Z", False),
    ),
)
def test_facts_are_current_only_from_verification_to_exclusive_end(evaluated, accepted):
    value = facts(evaluated_at_utc=evaluated)
    if accepted:
        assert copy_values(build(value))["paid_through_exclusive_utc"] == (
            "2026-11-01T00:00:00Z"
        )
    else:
        with pytest.raises(ValueError, match="stale or not effective"):
            build(value)


def test_exact_supported_state_and_exact_true_renewal_stop_are_required():
    for state in (
        "cancelled",
        "active",
        "payment_recovery",
        "cancellation_confirmed",
        "CANCELLATION_CONFIRMED_END_OF_PAID_PERIOD",
    ):
        with pytest.raises(ValueError, match="state is unsupported"):
            build(facts(state=state))
    for stopped in (False, 1, 0, 1.0, "true", None):
        with pytest.raises(ValueError, match="must be exact true"):
            build(facts(future_renewal_stopped=stopped))


def test_exact_schema_order_fields_references_and_dict_type_are_required():
    with pytest.raises(ValueError, match="unsupported.*version"):
        build(facts(schema_version="forged"))
    string_subclass = type("StringSubclass", (str,), {})
    with pytest.raises(ValueError, match="unsupported.*version"):
        build(facts(schema_version=string_subclass(subject.FACTS_VERSION)))
    with pytest.raises(ValueError, match="bounded exact string"):
        build(facts(billing_account_reference=""))
    with pytest.raises(ValueError, match="unsupported characters"):
        build(facts(subscription_reference="subscription 61"))
    reordered = dict(reversed(tuple(facts().items())))
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(reordered)
    extra = facts()
    extra["provider_status"] = "cancelled"
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(extra)
    subclass = type("DictSubclass", (dict,), {})(facts())
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(subclass)


def test_call_shape_cannot_inject_provider_or_authority_fields():
    builder = subject.build_cancellation_presentation
    with pytest.raises(TypeError, match="exact keyword"):
        builder(facts(), "owner-61", "subscription-61")
    with pytest.raises(TypeError, match="exact keyword"):
        builder(facts=facts(), expected_owner_reference="owner-61")
    with pytest.raises(TypeError, match="exact keyword"):
        builder(
            facts=facts(),
            expected_owner_reference="owner-61",
            expected_subscription_reference="subscription-61",
            provider_status="cancelled",
        )


def test_public_version_metadata_mutation_does_not_rewrite_captured_contract(monkeypatch):
    monkeypatch.setattr(subject, "FACTS_VERSION", "forged-facts")
    monkeypatch.setattr(subject, "PRESENTATION_VERSION", "forged-presentation")
    assert top(build())["schema_version"] == "reserved-w10-cancellation-presentation/1.0"


def test_tampered_copy_identity_and_authority_are_rejected():
    original = build()
    tampered_copy = tuple(
        (
            key,
            tuple(
                (
                    copy_key,
                    "Access continues forever" if copy_key == "boundary_message" else value,
                )
                for copy_key, value in nested
            )
            if key == "copy"
            else nested,
        )
        for key, nested in original
    )
    with pytest.raises(ValueError, match="copy is inconsistent"):
        subject.validate_cancellation_presentation(tampered_copy)

    tampered_kind = tuple(
        (key, "payment_recovery" if key == "kind" else value)
        for key, value in original
    )
    with pytest.raises(ValueError, match="kind is not"):
        subject.validate_cancellation_presentation(tampered_kind)

    tampered_authority = tuple(
        (
            key,
            tuple(
                (authority_key, True if authority_key == "entitlement_authority" else value)
                for authority_key, value in nested
            )
            if key == "authority"
            else nested,
        )
        for key, nested in original
    )
    with pytest.raises(ValueError, match="authority must remain exact false"):
        subject.validate_cancellation_presentation(tampered_authority)


def test_mutable_nested_values_and_hostile_subclasses_fail_closed():
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_cancellation_presentation(list(build()))
    subclass = type("TupleSubclass", (tuple,), {})
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_cancellation_presentation(subclass(build()))
    string_subclass = type("StringSubclass", (str,), {})
    hostile = tuple(
        (key, string_subclass(value) if key == "kind" else value)
        for key, value in build()
    )
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_cancellation_presentation(hostile)


def test_coherent_preimport_entitlement_and_portal_substitution_has_no_effect(monkeypatch):
    import reserved.billing.entitlement_core as entitlement_core
    import reserved.billing.portal_intent_contract as portal_contract

    monkeypatch.setattr(
        entitlement_core,
        "project_entitlement_transition",
        lambda value: (("state", "paid"), ("runtime_access_authority", True)),
    )
    monkeypatch.setattr(
        portal_contract,
        "project_portal_intent_contract",
        lambda value: (("provider_authority", True), ("refund_authority", True)),
    )
    name = "reserved.billing._s6f_preimport_substitution_probe"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        result = module.build_cancellation_presentation(
            facts=facts(),
            expected_owner_reference="owner-61",
            expected_subscription_reference="subscription-61",
        )
        assert dict(dict(result)["copy"])["paid_through_exclusive_utc"] == (
            "2026-11-01T00:00:00Z"
        )
        assert all(value is False for _, value in dict(result)["authority"])
    finally:
        sys.modules.pop(name, None)


def test_module_keeps_no_registry_or_lingering_per_result_state():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in ("weakref", "_registry", "_live", "producer-issued", "handle"):
        assert forbidden not in source
    baseline_keys = tuple(subject.__dict__)
    for second in range(1, 40):
        build(
            facts(
                cancellation_verified_at_utc="2026-10-12T09:14:00Z",
                evaluated_at_utc=f"2026-10-12T09:14:{second:02d}Z",
            )
        )
    gc.collect()
    assert tuple(subject.__dict__) == baseline_keys
    assert not any(
        type(value) in (dict, list, set) and name not in {"__builtins__"}
        for name, value in subject.__dict__.items()
    )


def test_module_has_no_io_network_clock_or_upstream_import_side_effect_surface():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import requests",
        "import urllib",
        "import stripe",
        "open(",
        "subprocess",
        "os.environ",
        "datetime.now",
        "datetime.utcnow",
        "send_notification",
        "notify(",
    ):
        assert forbidden not in source


def test_evidence_binds_current_sources_and_historical_checkpoint_identities():
    evidence = (
        ROOT / "docs/W10_S6F_CANCELLATION_PRESENTATION_EVIDENCE.md"
    ).read_text(encoding="utf-8")
    expected = {
        "FOUNDER_DECISIONS.md": (
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
        ),
        "reserved/billing/entitlement_core.py": (
            "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415"
        ),
        "reserved/billing/portal_intent_contract.py": (
            "f3f021bc05233cd5c4714c68e6eb57127f7722cc6685ea56e8c7a6e6de008d33"
        ),
    }
    for relative_path, expected_sha256 in expected.items():
        if relative_path == "FOUNDER_DECISIONS.md":
            content = subprocess.run(
                [
                    "git",
                    "show",
                    f"10fb93e2e6ab567a72d2370c1603768a7ac04bb5:{relative_path}",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
        else:
            content = (ROOT / relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_sha256
        assert expected_sha256 in evidence
    for checkpoint in (
        "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
        "b990d514a929c37b3f999137a0e383d05c37f0df",
        "48a97042fc0e17997bf2d23a4687e79c20b74b9e",
        "b197c987b96dd9fca6296c41bb002baf74099e55",
        "67b52a66805e9d5c1317330b9f7b1f2a19d4172c",
    ):
        assert checkpoint in evidence
    for required in (
        "detached",
        "zero authority",
        "not live customer presentation",
        "mandatory consumer and statutory rights",
        "provider labels have zero direct authority",
    ):
        assert required in evidence.lower()


def test_historical_package_scope_remains_exact_after_checkpoint():
    introduction_commits = {
        subprocess.run(
            ["git", "log", "--diff-filter=A", "-1", "--format=%H", "--", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for path in ALLOWED_PATHS
    }
    assert len(introduction_commits) == 1
    introduction_commit = introduction_commits.pop()
    assert introduction_commit
    introduced_paths = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            introduction_commit,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert set(introduced_paths) == ALLOWED_PATHS
