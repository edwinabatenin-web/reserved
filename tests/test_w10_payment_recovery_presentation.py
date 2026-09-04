"""Adversarial tests for the detached W10-S6E recovery-copy candidate."""

from __future__ import annotations

import gc
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from reserved.billing import payment_recovery_presentation as subject


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved/billing/payment_recovery_presentation.py"
ALLOWED_PATHS = {
    "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md",
    "reserved/billing/payment_recovery_presentation.py",
    "tests/test_w10_payment_recovery_presentation.py",
}
AUTHORITY_KEYS = (
    "upstream_admission_authority",
    "customer_render_authority",
    "delivery_authority",
    "notification_authority",
    "entitlement_authority",
    "provider_authority",
    "persistence_authority",
    "activation_authority",
)


def facts(**updates):
    value = {
        "schema_version": "reserved-w10-payment-recovery-structural-facts/1.0",
        "owner_reference": "owner-41",
        "billing_account_reference": "billing-41",
        "subscription_reference": "subscription-41",
        "state": "payment_recovery",
        "recovery_started_at_utc": "2026-10-01T00:00:00Z",
        "recovery_deadline_exclusive_utc": "2026-10-08T00:00:00Z",
        "evaluated_at_utc": "2026-10-03T12:00:00Z",
    }
    value.update(updates)
    return value


def build(value=None, *, owner="owner-41"):
    return subject.build_payment_recovery_presentation(
        facts=facts() if value is None else value,
        expected_owner_reference=owner,
    )


def top(value):
    return dict(subject.project_payment_recovery_presentation(value))


def copy_values(value):
    return dict(top(value)["copy"])


def test_exact_copy_uses_unambiguous_exclusive_boundary_language():
    copy = copy_values(build())
    assert copy == {
        "heading": "Your subscription payment is being recovered",
        "summary": (
            "We could not verify your renewal payment. Your subscription is in "
            "payment recovery."
        ),
        "access_message": (
            "You can continue using Reserved only before 8 October 2026 at "
            "00:00:00 UTC during this recovery period."
        ),
        "deadline_label": "Ordinary access continues before",
        "deadline_display": "8 October 2026 at 00:00:00 UTC",
        "deadline_exclusive_utc": "2026-10-08T00:00:00Z",
        "deadline_consequence": (
            "Starting 8 October 2026 at 00:00:00 UTC, ordinary access is suspended "
            "unless payment recovery has been verified."
        ),
        "verified_recovery_consequence": (
            "If payment recovery is verified, the subscription can return to "
            "its paid state after reconciliation."
        ),
    }
    joined = " ".join(copy.values()).lower()
    assert " until " not in joined
    assert " by 8 october" not in joined
    assert "normally paid" not in joined
    assert "active" not in joined


def test_result_is_detached_structural_data_with_every_authority_false():
    result = build()
    projected = top(result)
    assert type(result) is tuple
    assert projected["classification"] == "detached_zero_authority_copy_candidate"
    assert projected["kind"] == "payment_recovery"
    authority = dict(projected["authority"])
    assert tuple(authority) == AUTHORITY_KEYS
    assert all(type(value) is bool and value is False for value in authority.values())
    assert subject.validate_payment_recovery_presentation(result) == result
    assert subject.copy_payment_recovery_presentation(result) == result
    assert subject.copy_payment_recovery_presentation(result) is not result


def test_detached_reconstruction_is_valid_without_registry_or_identity():
    original = build()
    reconstructed = tuple(
        (key, tuple(tuple(pair) for pair in value) if type(value) is tuple else value)
        for key, value in original
    )
    assert reconstructed == original
    assert reconstructed is not original
    assert subject.validate_payment_recovery_presentation(reconstructed) == original


def test_mutating_input_after_build_cannot_change_detached_copy():
    source = facts()
    result = build(source)
    source["state"] = "paid"
    source["owner_reference"] = "owner-99"
    source["recovery_deadline_exclusive_utc"] = "2099-01-01T00:00:00Z"
    assert copy_values(result)["deadline_exclusive_utc"] == "2026-10-08T00:00:00Z"
    assert top(result)["kind"] == "payment_recovery"


def test_no_identity_provider_or_unsettled_policy_leaks_into_copy():
    joined = " ".join(copy_values(build()).values()).lower()
    for forbidden in (
        "owner-41",
        "billing-41",
        "subscription-41",
        "stripe",
        "provider",
        "refund",
        "dispute",
        "chargeback",
        "paid surface",
        "<",
        ">",
        "&",
    ):
        assert forbidden not in joined


@pytest.mark.parametrize(
    ("evaluated", "accepted"),
    (
        ("2026-10-01T00:00:00Z", True),
        ("2026-10-07T23:59:59Z", True),
        ("2026-09-30T23:59:59Z", False),
        ("2026-10-08T00:00:00Z", False),
        ("2026-10-08T00:00:01Z", False),
    ),
)
def test_structural_evaluation_window_is_start_inclusive_deadline_exclusive(
    evaluated, accepted
):
    value = facts(evaluated_at_utc=evaluated)
    if accepted:
        assert copy_values(build(value))["deadline_exclusive_utc"] == (
            "2026-10-08T00:00:00Z"
        )
    else:
        with pytest.raises(ValueError, match="stale or not effective"):
            build(value)


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-10-08",
        "2026-10-08T00:00:00",
        "2026-10-08T00:00:00+00:00",
        "2026-10-08T00:00:00.000Z",
        "2026-10-08t00:00:00z",
        "2026-02-30T00:00:00Z",
        "0000-01-01T00:00:00Z",
        "2026-10-08T24:00:00Z",
        20261008,
        None,
    ),
)
def test_invalid_or_noncanonical_timestamps_fail_closed(timestamp):
    with pytest.raises(ValueError, match="timestamp"):
        build(facts(recovery_deadline_exclusive_utc=timestamp))


def test_contradictory_or_zero_length_window_fails_closed():
    with pytest.raises(ValueError, match="contradictory"):
        build(
            facts(
                recovery_started_at_utc="2026-10-08T00:00:00Z",
                recovery_deadline_exclusive_utc="2026-10-08T00:00:00Z",
                evaluated_at_utc="2026-10-08T00:00:00Z",
            )
        )
    with pytest.raises(ValueError, match="contradictory"):
        build(
            facts(
                recovery_started_at_utc="2026-10-09T00:00:00Z",
                recovery_deadline_exclusive_utc="2026-10-08T00:00:00Z",
            )
        )


@pytest.mark.parametrize(
    "deadline",
    (
        "2026-10-07T23:59:59Z",
        "2026-10-08T00:00:01Z",
        "2026-10-07T00:00:00Z",
        "2026-10-09T00:00:00Z",
        "9999-12-31T23:59:59Z",
    ),
)
def test_non_seven_day_or_extreme_future_window_fails_closed(deadline):
    with pytest.raises(ValueError, match="exactly seven calendar days"):
        build(facts(recovery_deadline_exclusive_utc=deadline))


def test_exact_seven_calendar_day_recorded_interval_is_accepted_not_derived():
    result = copy_values(
        build(
            facts(
                recovery_started_at_utc="2026-12-29T17:42:19Z",
                recovery_deadline_exclusive_utc="2027-01-05T17:42:19Z",
                evaluated_at_utc="2027-01-05T17:42:18Z",
            )
        )
    )
    assert result["deadline_exclusive_utc"] == "2027-01-05T17:42:19Z"
    assert result["deadline_display"] == "5 January 2027 at 17:42:19 UTC"


@pytest.mark.parametrize("second", (1, 19, 59))
def test_non_zero_deadline_seconds_are_rendered_exactly(second):
    suffix = f"{second:02d}"
    result = copy_values(
        build(
            facts(
                recovery_started_at_utc=f"2026-10-01T00:00:{suffix}Z",
                recovery_deadline_exclusive_utc=f"2026-10-08T00:00:{suffix}Z",
                evaluated_at_utc="2026-10-08T00:00:00Z",
            )
        )
    )
    display = f"8 October 2026 at 00:00:{suffix} UTC"
    assert result["deadline_display"] == display
    assert display in result["access_message"]
    assert result["deadline_consequence"].startswith(f"Starting {display},")


def test_exact_state_owner_references_schema_and_order_are_required():
    with pytest.raises(ValueError, match="exactly payment_recovery"):
        build(facts(state="paid"))
    with pytest.raises(ValueError, match="expected owner"):
        build(owner="owner-42")
    with pytest.raises(ValueError, match="bounded exact string"):
        build(facts(subscription_reference=""))
    with pytest.raises(ValueError, match="unsupported characters"):
        build(facts(billing_account_reference="billing 41"))
    with pytest.raises(ValueError, match="unsupported.*version"):
        build(facts(schema_version="forged"))
    string_subclass = type("StringSubclass", (str,), {})
    with pytest.raises(ValueError, match="unsupported.*version"):
        build(facts(schema_version=string_subclass(subject.FACTS_VERSION)))
    reordered = dict(reversed(tuple(facts().items())))
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(reordered)
    subclass = type("DictSubclass", (dict,), {})(facts())
    with pytest.raises(TypeError, match="ordered structural-facts"):
        build(subclass)


def test_call_metadata_cannot_supply_or_replace_inputs(monkeypatch):
    builder = subject.build_payment_recovery_presentation
    monkeypatch.setattr(builder, "__defaults__", (facts(),))
    monkeypatch.setattr(
        builder, "__kwdefaults__", {"expected_owner_reference": "owner-41"}
    )
    with pytest.raises(TypeError, match="exact keyword"):
        builder(facts(), expected_owner_reference="owner-41")
    with pytest.raises(TypeError, match="exact keyword"):
        builder(facts=facts())
    with pytest.raises(TypeError, match="exact keyword"):
        builder(
            facts=facts(),
            expected_owner_reference="owner-41",
            provider_status="active",
        )
    assert top(builder(facts=facts(), expected_owner_reference="owner-41"))["kind"] == (
        "payment_recovery"
    )


def test_mutable_public_version_metadata_cannot_rewrite_captured_contract(monkeypatch):
    monkeypatch.setattr(subject, "FACTS_VERSION", "forged-facts")
    monkeypatch.setattr(subject, "PRESENTATION_VERSION", "forged-presentation")
    result = top(build())
    assert result["schema_version"] == (
        "reserved-w10-payment-recovery-presentation/2.0"
    )


def test_tampered_detached_copy_or_authority_is_rejected():
    original = build()
    tampered_copy = tuple(
        (
            key,
            tuple(
                (
                    copy_key,
                    "Access continues forever"
                    if copy_key == "access_message"
                    else value,
                )
                for copy_key, value in nested
            )
            if key == "copy"
            else nested,
        )
        for key, nested in original
    )
    with pytest.raises(ValueError, match="copy is inconsistent"):
        subject.validate_payment_recovery_presentation(tampered_copy)

    tampered_authority = tuple(
        (
            key,
            tuple(
                (
                    authority_key,
                    True if authority_key == "delivery_authority" else value,
                )
                for authority_key, value in nested
            )
            if key == "authority"
            else nested,
        )
        for key, nested in original
    )
    with pytest.raises(ValueError, match="authority must remain exact false"):
        subject.validate_payment_recovery_presentation(tampered_authority)


def test_mutable_nested_values_and_subclasses_are_rejected_recursively():
    value = list(build())
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_payment_recovery_presentation(value)
    value = tuple(build()) + (("extra", "field"),)
    with pytest.raises(ValueError, match="invalid shape"):
        subject.validate_payment_recovery_presentation(value)
    subclass = type("StringSubclass", (str,), {})
    value = tuple(
        (key, subclass(nested) if key == "kind" else nested)
        for key, nested in build()
    )
    with pytest.raises(ValueError, match="non-exact built-in"):
        subject.validate_payment_recovery_presentation(value)


def test_coherent_preimport_entitlement_export_substitution_has_no_effect(monkeypatch):
    import reserved.billing.entitlement_core as entitlement_core
    import reserved.billing.provider_lifecycle_authority as provider_authority

    fake_projection = type("FakeProjection", (), {})
    monkeypatch.setattr(entitlement_core, "EntitlementTransitionProjection", fake_projection)
    monkeypatch.setattr(
        entitlement_core,
        "project_entitlement_transition",
        lambda value: (
            ("owner_id", "owner-41"),
            ("state", "payment_recovery"),
            ("recovery_deadline_exclusive", "2099-01-01T00:00:00Z"),
        ),
    )
    monkeypatch.setattr(provider_authority, "AUTHORITY_VERSION", "forged")
    monkeypatch.setattr(
        provider_authority,
        "project_provider_lifecycle_authority",
        lambda value: (
            ("recovery_state", "payment_recovery"),
            ("customer_render_authority", True),
        ),
    )
    name = "reserved.billing._s6e_preimport_substitution_probe"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        result = module.build_payment_recovery_presentation(
            facts=facts(), expected_owner_reference="owner-41"
        )
        assert dict(dict(result)["copy"])["deadline_exclusive_utc"] == (
            "2026-10-08T00:00:00Z"
        )
    finally:
        sys.modules.pop(name, None)


def test_combined_registry_injection_cannot_create_admission(monkeypatch):
    monkeypatch.setattr(subject, "_registry", {1: "authoritative"}, raising=False)
    monkeypatch.setattr(subject, "_live", {1: object()}, raising=False)
    monkeypatch.setattr(subject, "_admitted", {"owner-41": True}, raising=False)
    result = top(build())
    assert result["classification"] == "detached_zero_authority_copy_candidate"
    assert all(value is False for _, value in result["authority"])


def test_module_has_no_registry_handle_or_lingering_per_result_state():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in ("weakref", "_registry", "_live", "producer-issued", "handle"):
        assert forbidden not in source
    baseline_keys = tuple(subject.__dict__)
    for second in range(1, 40):
        build(facts(evaluated_at_utc=f"2026-10-03T12:00:{second:02d}Z"))
    gc.collect()
    assert tuple(subject.__dict__) == baseline_keys
    assert not any(
        type(value) in (dict, list, set)
        and name not in {"__builtins__"}
        for name, value in subject.__dict__.items()
    )


def test_module_has_no_upstream_admission_or_runtime_side_effect_surface():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "entitlement_core",
        "provider_lifecycle",
        "requests",
        "urllib",
        "stripe",
        "open(",
        "subprocess",
        "os.environ",
        "datetime.now",
        "datetime.utcnow",
        "send_notification",
        "notify(",
    ):
        assert forbidden not in source


def test_evidence_binds_exact_authority_and_baseline_without_claiming_admission():
    evidence = (
        ROOT / "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md"
    ).read_text(encoding="utf-8")
    expected = {
        "FOUNDER_DECISIONS.md": (
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
        ),
        "reserved/billing/entitlement_core.py": (
            "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b"
        ),
        "reserved/billing/provider_lifecycle_authority.py": (
            "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a"
        ),
    }
    for relative_path, expected_sha256 in expected.items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == (
            expected_sha256
        )
        assert expected_sha256 in evidence
    for required in (
        "detached",
        "untrusted structural facts",
        "not upstream admission",
        "not live customer presentation",
        "every authority flag is exact `false`",
    ):
        assert required in evidence.lower()


def test_package_scope_is_bounded_before_and_after_checkpoint():
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    candidate_paths = set(changed + untracked)
    if candidate_paths:
        assert candidate_paths <= ALLOWED_PATHS
        assert all((ROOT / path).is_file() for path in ALLOWED_PATHS)
        return

    introduction_commits = {
        subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "-1",
                "--format=%H",
                "--",
                path,
            ],
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
