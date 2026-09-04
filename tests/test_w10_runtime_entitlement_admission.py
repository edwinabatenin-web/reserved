"""Hostile focused tests for W10-S3C runtime-entitlement admission."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import pickle
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import reserved.billing.entitlement_core as detached_s3a
import reserved.billing.event_inbox_contract as detached_s3b
import reserved.billing.paid_access_guard as s5d
import reserved.billing.runtime_entitlement_admission as subject


ROOT = Path(__file__).resolve().parents[1]
BASE = "91cb4c2f14bce089db1f92f656c8cbc1d85639b7"
BASE_TREE = "a68a1120dfcc98295839bbea1f1c65c223376ec0"
SOURCE_CHECKPOINT = "b458f2df20aa29aa73b1cc56de2126cb1c26405a"
SOURCE_SENTINEL_CORRECTION_MESSAGE = "Bind W10 S3C source checkpoint identity"
INTEGRATION_BASE = "05134e536d0428e0bcdfab96a109d64f46d2d9a4"
INTEGRATION_SOURCE_CHECKPOINT = "be417aed05a99199ee2bc54679ca598551947f95"
INTEGRATION_SENTINEL_CHECKPOINT = "e145e43631f9a03df70a378ac1eafbdf3974afa9"
INTEGRATION_LINEAGE_CORRECTION_MESSAGE = (
    "Bind W10 S3C integration checkpoint identity"
)
OWNED_PATHS = {
    "docs/W10_S3C_RUNTIME_ENTITLEMENT_ADMISSION.md",
    "reserved/billing/runtime_entitlement_admission.py",
    "tests/test_w10_runtime_entitlement_admission.py",
}
FACT_KEYS = (
    "protocol_version",
    "fact_identity",
    "admission_status",
    "authenticated",
    "billing_fact_authority",
    "provider_observation_direct_authority",
    "owner_id",
    "billing_account_id",
    "subscription_id",
    "decision_sequence",
    "predecessor_fact_identity",
    "state",
    "valid_from_inclusive",
    "valid_until_exclusive",
    "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc",
    "derivation_kind",
    "withdrawal_attribution",
)


def git_text(*args):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def fact_identity(values):
    material = (
        values["protocol_version"],
        values["admission_status"],
        values["authenticated"],
        values["billing_fact_authority"],
        values["provider_observation_direct_authority"],
        values["owner_id"],
        values["billing_account_id"],
        values["subscription_id"],
        values["decision_sequence"],
        values["predecessor_fact_identity"],
        values["state"],
        values["valid_from_inclusive"].isoformat(),
        values["valid_until_exclusive"].isoformat(),
        values["transition_effective_at_utc"].isoformat(),
        (
            None
            if values["recovery_deadline_exclusive_at_utc"] is None
            else values["recovery_deadline_exclusive_at_utc"].isoformat()
        ),
        values["derivation_kind"],
        values["withdrawal_attribution"],
    )
    payload = json.dumps(material, ensure_ascii=True, separators=(",", ":"))
    return "billing-fact:sha256-" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def fact_view(**changes):
    values = {
        "protocol_version": subject.BILLING_FACT_PROTOCOL_VERSION,
        "fact_identity": "",
        "admission_status": subject.BILLING_FACT_ADMISSION_STATUS,
        "authenticated": True,
        "billing_fact_authority": True,
        "provider_observation_direct_authority": False,
        "owner_id": "users:17",
        "billing_account_id": "billing:17",
        "subscription_id": "subscription:17",
        "decision_sequence": 1,
        "predecessor_fact_identity": None,
        "state": "paid",
        "valid_from_inclusive": date(2026, 9, 1),
        "valid_until_exclusive": date(2026, 10, 1),
        "transition_effective_at_utc": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "recovery_deadline_exclusive_at_utc": None,
        "derivation_kind": "verified_initial_payment",
        "withdrawal_attribution": "not_applicable",
    }
    values.update(changes)
    if "fact_identity" not in changes:
        values["fact_identity"] = fact_identity(values)
    return tuple((key, values[key]) for key in FACT_KEYS)


def successor(prior, **changes):
    values = dict(prior)
    values.update(
        decision_sequence=values["decision_sequence"] + 1,
        predecessor_fact_identity=values["fact_identity"],
        fact_identity="",
        transition_effective_at_utc=datetime(2026, 9, 15, tzinfo=timezone.utc),
        derivation_kind="existing_derived_access",
        withdrawal_attribution="not_applicable",
    )
    values.update(changes)
    if "fact_identity" not in changes:
        values["fact_identity"] = fact_identity(values)
    return tuple((key, values[key]) for key in FACT_KEYS)


class LiveBillingFact:
    __slots__ = ("view",)

    def __init__(self, view):
        self.view = view


def authority(*, validator_transform=None, projector_transform=None):
    live = set()

    def issue(view):
        fact = LiveBillingFact(view)
        live.add(id(fact))
        return fact

    def validate(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return validator_transform(value.view) if validator_transform else value.view

    def project(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return projector_transform(value.view) if projector_transform else value.view

    binding = subject.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )
    return binding, issue


def two_bindings_same_authority():
    live = set()

    def issue(view):
        fact = LiveBillingFact(view)
        live.add(id(fact))
        return fact

    def validate(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return value.view

    def project(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return value.view

    kwargs = {
        "validate_admitted_billing_fact": validate,
        "project_admitted_billing_fact": project,
    }
    return (
        subject.bind_runtime_entitlement_admission(**kwargs),
        subject.bind_runtime_entitlement_admission(**kwargs),
        issue,
    )


def admit(
    binding,
    fact,
    *,
    prior=None,
    owner="users:17",
    account="billing:17",
    subscription="subscription:17",
    at=None,
):
    return subject.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=owner,
        billing_account_id=account,
        subscription_id=subscription,
        prior_runtime_entitlement=prior,
        admitted_billing_fact=fact,
        evaluated_at_utc=at or datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )


def replace_pair(value, key, replacement):
    return tuple((name, replacement if name == key else item) for name, item in value)


def s5d_result(prior, current, *, at=None):
    guard = s5d.bind_paid_access_guard(
        validate_runtime_entitlement=subject.validate_runtime_entitlement,
        project_runtime_entitlement=subject.project_runtime_entitlement,
    )
    decision = s5d.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id="users:17",
        prior_runtime_entitlement=prior,
        current_runtime_entitlement=current,
        evaluated_at_utc=at
        or datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    return dict(s5d.validate_paid_access_decision(decision))


def test_candidate_or_source_checkpoint_is_exactly_scoped_to_declared_base():
    head = git_text("rev-parse", "HEAD")
    changed = git_text("diff", "--name-only", "HEAD").splitlines()
    untracked = git_text("ls-files", "--others", "--exclude-standard").splitlines()
    if head == BASE:
        assert set(changed + untracked) <= OWNED_PATHS
        assert git_text("rev-parse", "HEAD^{tree}") == BASE_TREE
        return
    if head == SOURCE_CHECKPOINT:
        assert git_text("rev-parse", "HEAD^") == BASE
        assert set(
            git_text(
                "diff", "--name-only", f"{BASE}..{SOURCE_CHECKPOINT}"
            ).splitlines()
        ) == OWNED_PATHS
        if changed or untracked:
            assert changed == ["tests/test_w10_runtime_entitlement_admission.py"]
            assert untracked == []
        return
    if head == INTEGRATION_SENTINEL_CHECKPOINT:
        assert git_text("rev-parse", "HEAD^") == INTEGRATION_SOURCE_CHECKPOINT
        assert git_text("rev-parse", "HEAD^^") == INTEGRATION_BASE
        assert set(
            git_text(
                "diff",
                "--name-only",
                f"{INTEGRATION_BASE}..{INTEGRATION_SOURCE_CHECKPOINT}",
            ).splitlines()
        ) == OWNED_PATHS
        assert git_text("show", "-s", "--format=%s", "HEAD") == (
            SOURCE_SENTINEL_CORRECTION_MESSAGE
        )
        assert git_text(
            "diff", "--name-only", f"{INTEGRATION_SOURCE_CHECKPOINT}..HEAD"
        ).splitlines() == ["tests/test_w10_runtime_entitlement_admission.py"]
        if changed or untracked:
            assert changed == ["tests/test_w10_runtime_entitlement_admission.py"]
            assert untracked == []
        return
    if git_text("rev-parse", "HEAD^") == INTEGRATION_SENTINEL_CHECKPOINT:
        assert len(git_text("rev-list", "--parents", "-n", "1", "HEAD").split()) == 2
        assert git_text("show", "-s", "--format=%s", "HEAD") == (
            INTEGRATION_LINEAGE_CORRECTION_MESSAGE
        )
        assert git_text(
            "diff", "--name-only", f"{INTEGRATION_SENTINEL_CHECKPOINT}..HEAD"
        ).splitlines() == ["tests/test_w10_runtime_entitlement_admission.py"]
        assert changed == []
        assert untracked == []
        return
    assert git_text("rev-parse", "HEAD^") == SOURCE_CHECKPOINT
    assert len(git_text("rev-list", "--parents", "-n", "1", "HEAD").split()) == 2
    assert git_text("show", "-s", "--format=%s", "HEAD") == (
        SOURCE_SENTINEL_CORRECTION_MESSAGE
    )
    assert git_text("diff", "--name-only", f"{SOURCE_CHECKPOINT}..HEAD").splitlines() == [
        "tests/test_w10_runtime_entitlement_admission.py"
    ]
    assert changed == []
    assert untracked == []


def test_exact_call_shapes_are_keyword_only_and_pair_is_s5d_compatible():
    assert str(inspect.signature(subject.bind_runtime_entitlement_admission)) == (
        "(*, validate_admitted_billing_fact, project_admitted_billing_fact)"
    )
    assert str(inspect.signature(subject.admit_runtime_entitlement)) == (
        "(admission, *, authenticated_owner_id, billing_account_id, subscription_id, prior_runtime_entitlement, "
        "admitted_billing_fact, evaluated_at_utc)"
    )
    assert subject.RUNTIME_DECISION_PROTOCOL_VERSION == s5d.RUNTIME_DECISION_PROTOCOL_VERSION
    assert subject.RUNTIME_ADMISSION_STATUS == s5d.RUNTIME_ADMISSION_STATUS
    assert subject.validate_runtime_entitlement is not subject.project_runtime_entitlement


def test_initial_payment_issues_opaque_runtime_handle_and_allows_s5d():
    binding, issue = authority()
    runtime = admit(binding, issue(fact_view()))
    projection = dict(subject.validate_runtime_entitlement(runtime))
    assert projection["state"] == "paid"
    assert projection["ordinary_access"] is True
    assert projection["decision_sequence"] == 1
    assert projection["predecessor_identity"] is None
    guard = s5d.bind_paid_access_guard(
        validate_runtime_entitlement=subject.validate_runtime_entitlement,
        project_runtime_entitlement=subject.project_runtime_entitlement,
    )
    decision = s5d.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id="users:17",
        prior_runtime_entitlement=None,
        current_runtime_entitlement=runtime,
        evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    assert dict(s5d.validate_paid_access_decision(decision))["reason"] == (
        "allowed_initial_payment"
    )


def test_full_current_period_withdrawal_suspends_at_next_admission_and_s5d_denies():
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    withdrawal_fact = successor(
        paid_fact,
        state="suspended",
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
    )
    suspended = admit(binding, issue(withdrawal_fact), prior=paid)
    view = dict(subject.project_runtime_entitlement(suspended))
    assert view["state"] == "suspended"
    assert view["ordinary_access"] is False
    assert view["predecessor_entitled_access"] is True
    guard = s5d.bind_paid_access_guard(
        validate_runtime_entitlement=subject.validate_runtime_entitlement,
        project_runtime_entitlement=subject.project_runtime_entitlement,
    )
    decision = s5d.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id="users:17",
        prior_runtime_entitlement=paid,
        current_runtime_entitlement=suspended,
        evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    result = dict(s5d.validate_paid_access_decision(decision))
    assert result["allowed"] is False
    assert result["reason"] == "verified_full_current_period_withdrawal"


def test_same_binding_can_advance_verified_renewal_payment_and_s5d_accepts_it():
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    renewal_fact = successor(
        paid_fact,
        derivation_kind="verified_renewal_payment",
        valid_until_exclusive=date(2026, 11, 1),
    )
    renewed = admit(binding, issue(renewal_fact), prior=paid)
    guard = s5d.bind_paid_access_guard(
        validate_runtime_entitlement=subject.validate_runtime_entitlement,
        project_runtime_entitlement=subject.project_runtime_entitlement,
    )
    decision = s5d.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id="users:17",
        prior_runtime_entitlement=paid,
        current_runtime_entitlement=renewed,
        evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    result = dict(s5d.validate_paid_access_decision(decision))
    assert result["allowed"] is True
    assert result["reason"] == "allowed_renewal_payment"


@pytest.mark.parametrize(
    ("derivation", "attribution", "expected_reason"),
    (
        (
            "existing_derived_access",
            "not_applicable",
            "allowed_existing_derived_access",
        ),
        (
            "withdrawal_open",
            "unknown",
            "allowed_preserved_withdrawal_uncertainty",
        ),
        (
            "withdrawal_partial",
            "current_subscription_period",
            "allowed_preserved_withdrawal_uncertainty",
        ),
        (
            "withdrawal_ambiguous",
            "unknown",
            "allowed_preserved_withdrawal_uncertainty",
        ),
        (
            "withdrawal_contradictory",
            "unknown",
            "allowed_preserved_withdrawal_uncertainty",
        ),
        (
            "withdrawal_unresolved",
            "unknown",
            "allowed_preserved_withdrawal_uncertainty",
        ),
        (
            "verified_full_withdrawal",
            "other_period",
            "allowed_preserved_withdrawal_uncertainty",
        ),
    ),
)
def test_same_binding_preservation_paths_are_structurally_accepted_by_s5d(
    derivation, attribution, expected_reason
):
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    preserved_fact = successor(
        paid_fact,
        derivation_kind=derivation,
        withdrawal_attribution=attribution,
    )
    preserved = admit(binding, issue(preserved_fact), prior=paid)
    result = s5d_result(paid, preserved)
    assert result["allowed"] is True
    assert result["reason"] == expected_reason


@pytest.mark.parametrize(
    "derivation",
    (
        "withdrawal_open",
        "withdrawal_partial",
        "withdrawal_ambiguous",
        "withdrawal_contradictory",
        "withdrawal_unresolved",
    ),
)
def test_uncertain_withdrawal_preserves_but_never_extends_valid_predecessor(derivation):
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    uncertain_fact = successor(
        paid_fact,
        derivation_kind=derivation,
        withdrawal_attribution="unknown",
        valid_from_inclusive=date(2026, 9, 2),
        valid_until_exclusive=date(2026, 9, 30),
    )
    preserved = admit(binding, issue(uncertain_fact), prior=paid)
    assert dict(subject.project_runtime_entitlement(preserved))["ordinary_access"] is True
    extending = replace_pair(
        uncertain_fact, "valid_until_exclusive", date(2026, 10, 2)
    )
    extending = replace_pair(extending, "fact_identity", fact_identity(dict(extending)))
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="cannot create, extend"):
        admit(binding, issue(extending), prior=paid)


@pytest.mark.parametrize(
    "derivation",
    (
        "verified_renewal_payment",
        "verified_renewal_failure",
        "withdrawal_open",
        "withdrawal_partial",
        "withdrawal_ambiguous",
        "withdrawal_contradictory",
        "withdrawal_unresolved",
        "verified_full_withdrawal",
        "verified_reinstatement",
        "verified_reversal_success",
        "verified_replacement_payment",
    ),
)
def test_no_originless_renewal_recovery_withdrawal_or_restoration(derivation):
    changes = {
        "derivation_kind": derivation,
        "withdrawal_attribution": (
            "current_subscription_period"
            if "withdrawal" in derivation
            else "not_applicable"
        ),
        "state": "suspended" if derivation == "verified_full_withdrawal" else "paid",
    }
    if derivation == "verified_renewal_failure":
        changes.update(
            state="payment_recovery",
            transition_effective_at_utc=datetime(2026, 9, 1, tzinfo=timezone.utc),
            valid_until_exclusive=date(2026, 9, 8),
            recovery_deadline_exclusive_at_utc=datetime(
                2026, 9, 8, tzinfo=timezone.utc
            ),
        )
    binding, issue = authority()
    with pytest.raises(subject.RuntimeEntitlementAdmissionError):
        admit(binding, issue(fact_view(**changes)), at=datetime(2026, 9, 2, tzinfo=timezone.utc))


def test_exact_seven_calendar_day_recovery_binds_and_repeated_failure_cannot_extend():
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    recovery_fact = successor(
        paid_fact,
        state="payment_recovery",
        valid_from_inclusive=date(2026, 9, 1),
        valid_until_exclusive=date(2026, 10, 8),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(2026, 10, 8, tzinfo=timezone.utc),
        derivation_kind="verified_renewal_failure",
    )
    recovery = admit(
        binding,
        issue(recovery_fact),
        prior=paid,
        at=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    assert dict(subject.project_runtime_entitlement(recovery))["state"] == "payment_recovery"
    recovery_result = s5d_result(
        paid,
        recovery,
        at=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    assert recovery_result["allowed"] is True
    assert recovery_result["reason"] == "allowed_payment_recovery"
    repeated = successor(
        recovery_fact,
        state="payment_recovery",
        valid_until_exclusive=date(2026, 10, 15),
        transition_effective_at_utc=datetime(2026, 10, 8, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(2026, 10, 15, tzinfo=timezone.utc),
        derivation_kind="verified_renewal_failure",
    )
    with pytest.raises(subject.RuntimeEntitlementAdmissionError):
        admit(
            binding,
            issue(repeated),
            prior=recovery,
            at=datetime(2026, 10, 9, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    "restoration_kind",
    (
        "verified_reinstatement",
        "verified_reversal_success",
        "verified_replacement_payment",
    ),
)
def test_only_verified_admitted_outcomes_restore_full_withdrawal(restoration_kind):
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    withdrawal_fact = successor(
        paid_fact,
        state="suspended",
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
    )
    suspended = admit(binding, issue(withdrawal_fact), prior=paid)
    restored_fact = successor(
        withdrawal_fact,
        state="paid",
        derivation_kind=restoration_kind,
        withdrawal_attribution="not_applicable",
        transition_effective_at_utc=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    restored = admit(
        binding,
        issue(restored_fact),
        prior=suspended,
        at=datetime(2026, 9, 16, 12, tzinfo=timezone.utc),
    )
    assert dict(subject.project_runtime_entitlement(restored))["ordinary_access"] is True
    result = s5d_result(
        suspended,
        restored,
        at=datetime(2026, 9, 16, 12, tzinfo=timezone.utc),
    )
    assert result["allowed"] is True
    assert result["reason"] in {
        "allowed_verified_reinstatement",
        "allowed_verified_reversal_success",
        "allowed_verified_replacement_payment",
    }


@pytest.mark.parametrize(
    "successor_kind",
    (
        "verified_renewal_payment",
        "verified_renewal_failure",
        "existing_derived_access",
        "withdrawal_open",
        "withdrawal_partial",
        "withdrawal_ambiguous",
        "withdrawal_contradictory",
        "withdrawal_unresolved",
        "verified_full_withdrawal",
    ),
)
def test_fresh_binding_cannot_advance_another_bindings_runtime_lineage(successor_kind):
    binding_a, binding_b, issue = two_bindings_same_authority()
    paid_fact = fact_view()
    paid = admit(binding_a, issue(paid_fact))
    changes = {"derivation_kind": successor_kind}
    if successor_kind == "verified_renewal_payment":
        changes["valid_until_exclusive"] = date(2026, 11, 1)
    elif successor_kind == "verified_renewal_failure":
        changes.update(
            state="payment_recovery",
            valid_until_exclusive=date(2026, 10, 8),
            transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
            recovery_deadline_exclusive_at_utc=datetime(
                2026, 10, 8, tzinfo=timezone.utc
            ),
        )
    elif successor_kind.startswith("withdrawal_"):
        changes["withdrawal_attribution"] = "unknown"
    elif successor_kind == "verified_full_withdrawal":
        changes.update(
            state="suspended",
            withdrawal_attribution="current_subscription_period",
        )
    candidate = successor(paid_fact, **changes)
    evaluated = (
        datetime(2026, 10, 2, tzinfo=timezone.utc)
        if successor_kind == "verified_renewal_failure"
        else datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
    )
    with pytest.raises(
        subject.RuntimeEntitlementAdmissionError,
        match="crossed admission authority",
    ):
        admit(binding_b, issue(candidate), prior=paid, at=evaluated)


@pytest.mark.parametrize(
    "restoration_kind",
    (
        "verified_reinstatement",
        "verified_reversal_success",
        "verified_replacement_payment",
    ),
)
def test_fresh_binding_cannot_restore_another_bindings_suspension(restoration_kind):
    binding_a, binding_b, issue = two_bindings_same_authority()
    paid_fact = fact_view()
    paid = admit(binding_a, issue(paid_fact))
    withdrawal_fact = successor(
        paid_fact,
        state="suspended",
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
    )
    suspended = admit(binding_a, issue(withdrawal_fact), prior=paid)
    restored_fact = successor(
        withdrawal_fact,
        state="paid",
        derivation_kind=restoration_kind,
        withdrawal_attribution="not_applicable",
        transition_effective_at_utc=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    with pytest.raises(
        subject.RuntimeEntitlementAdmissionError,
        match="crossed admission authority",
    ):
        admit(
            binding_b,
            issue(restored_fact),
            prior=suspended,
            at=datetime(2026, 9, 16, 12, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ("transition", "evaluated", "accepted"),
    (
        (
            datetime(2026, 8, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
            datetime(2026, 9, 15, tzinfo=timezone.utc),
            False,
        ),
        (
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc),
            datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            False,
        ),
    ),
)
def test_transition_is_inside_exact_half_open_validity_interval(
    transition, evaluated, accepted
):
    binding, issue = authority()
    candidate = fact_view(transition_effective_at_utc=transition)
    if accepted:
        runtime = admit(binding, issue(candidate), at=evaluated)
        projected = subject.project_runtime_entitlement(runtime)
        assert dict(projected)["transition_effective_at_utc"] == transition
        guard = s5d.bind_paid_access_guard(
            validate_runtime_entitlement=subject.validate_runtime_entitlement,
            project_runtime_entitlement=subject.project_runtime_entitlement,
        )
        decision = s5d.evaluate_paid_access(
            guard,
            endpoint="v2.index",
            authenticated_owner_id="users:17",
            prior_runtime_entitlement=None,
            current_runtime_entitlement=runtime,
            evaluated_at_utc=evaluated,
        )
        assert dict(s5d.validate_paid_access_decision(decision))["reason"] == (
            "allowed_initial_payment"
        )
    else:
        with pytest.raises(
            subject.RuntimeEntitlementAdmissionError,
            match="outside its validity interval",
        ):
            admit(binding, issue(candidate), at=evaluated)


@pytest.mark.parametrize(
    ("key", "replacement", "message"),
    (
        ("owner_id", "users:18", "owner boundary"),
        ("billing_account_id", "billing:18", "selected account or subscription"),
        ("subscription_id", "subscription:18", "selected account or subscription"),
        ("decision_sequence", 8, "predecessor or sequence"),
        ("predecessor_fact_identity", "billing-fact:sha256-" + "0" * 64, "predecessor or sequence"),
    ),
)
def test_successor_cross_owner_account_subscription_and_lineage_fail(key, replacement, message):
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    candidate = successor(paid_fact)
    candidate = replace_pair(candidate, key, replacement)
    candidate = replace_pair(candidate, "fact_identity", fact_identity(dict(candidate)))
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match=message):
        admit(binding, issue(candidate), prior=paid)


def test_stale_replayed_out_of_order_and_future_facts_fail_closed():
    binding, issue = authority()
    paid_fact = fact_view()
    paid = admit(binding, issue(paid_fact))
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="stale"):
        admit(
            binding,
            issue(successor(paid_fact)),
            prior=paid,
            at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="predecessor or sequence"):
        admit(binding, issue(paid_fact), prior=paid)
    later_paid_fact = fact_view(
        transition_effective_at_utc=datetime(2026, 9, 10, tzinfo=timezone.utc)
    )
    later_paid = admit(
        binding,
        issue(later_paid_fact),
        at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    earlier = successor(
        later_paid_fact,
        transition_effective_at_utc=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="out-of-order"):
        admit(binding, issue(earlier), prior=later_paid)
    future = successor(
        paid_fact,
        transition_effective_at_utc=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="future"):
        admit(binding, issue(future), prior=paid)


@pytest.mark.parametrize(
    ("key", "replacement"),
    (
        ("protocol_version", "future"),
        ("admission_status", "provider_observed"),
        ("authenticated", False),
        ("authenticated", 1),
        ("billing_fact_authority", False),
        ("provider_observation_direct_authority", True),
        ("decision_sequence", True),
        ("fact_identity", "billing-fact:sha256-" + "0" * 64),
    ),
)
def test_malformed_unauthenticated_provider_or_identity_facts_fail(key, replacement):
    binding, issue = authority()
    candidate = replace_pair(fact_view(), key, replacement)
    with pytest.raises(subject.RuntimeEntitlementAdmissionError):
        admit(binding, issue(candidate))


def test_validator_projector_agreement_and_identity_are_recomputed():
    original = fact_view()
    lied = successor(original)
    for kwargs in (
        {"validator_transform": lambda _view: lied},
        {"projector_transform": lambda _view: lied},
    ):
        binding, issue = authority(**kwargs)
        with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="disagree"):
            admit(binding, issue(original))
    tampered = replace_pair(original, "state", "suspended")
    binding, issue = authority()
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="identity"):
        admit(binding, issue(tampered))


def test_detached_s3a_s3b_and_primitive_views_are_not_admission():
    binding, issue = authority()
    structural = detached_s3a.empty_entitlement(
        owner_id="users:17",
        billing_account_id="billing:17",
        subscription_id="subscription:17",
    )
    for value in (structural, (), fact_view()):
        with pytest.raises(subject.RuntimeEntitlementAdmissionError):
            admit(binding, value)
    assert detached_s3b.CONTRACT_VERSION != subject.BILLING_FACT_PROTOCOL_VERSION
    runtime = admit(binding, issue(fact_view()))
    primitive = subject.project_runtime_entitlement(runtime)
    with pytest.raises(subject.RuntimeEntitlementAdmissionError):
        subject.validate_runtime_entitlement(primitive)


def test_handles_are_exact_issued_noncopyable_nonserialisable():
    binding, issue = authority()
    runtime = admit(binding, issue(fact_view()))
    with pytest.raises(TypeError, match="binder-issued"):
        subject.RuntimeEntitlementAdmissionHandle()
    with pytest.raises(TypeError, match="adapter-issued"):
        subject.RuntimeEntitlementHandle()
    forged_binding = object.__new__(subject.RuntimeEntitlementAdmissionHandle)
    forged_runtime = object.__new__(subject.RuntimeEntitlementHandle)
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="not issued"):
        admit(forged_binding, issue(fact_view()))
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="not issued"):
        subject.project_runtime_entitlement(forged_runtime)
    for handle in (binding, runtime):
        with pytest.raises(TypeError, match="not copyable"):
            copy.copy(handle)
        with pytest.raises(TypeError, match="not copyable"):
            copy.deepcopy(handle)
        with pytest.raises(TypeError, match="not serialisable"):
            pickle.dumps(handle)


def test_exact_types_subtypes_and_non_utc_times_fail():
    class Text(str):
        pass

    binding, issue = authority()
    for candidate in (
        replace_pair(fact_view(), "owner_id", Text("users:17")),
        replace_pair(fact_view(), "valid_from_inclusive", datetime(2026, 9, 1)),
        replace_pair(
            fact_view(),
            "transition_effective_at_utc",
            datetime(2026, 9, 1),
        ),
        replace_pair(
            fact_view(),
            "transition_effective_at_utc",
            datetime(2026, 9, 1, tzinfo=timezone(timedelta(hours=1))),
        ),
    ):
        with pytest.raises(subject.RuntimeEntitlementAdmissionError):
            admit(binding, issue(candidate))


def test_reordered_extra_duplicate_and_hostile_call_shapes_fail():
    binding, issue = authority()
    exact = fact_view()
    for candidate in (
        tuple(reversed(exact)),
        exact + (("extra", True),),
        exact[:-1] + (exact[-2],),
    ):
        with pytest.raises(subject.RuntimeEntitlementAdmissionError):
            admit(binding, issue(candidate))
    with pytest.raises(TypeError):
        subject.admit_runtime_entitlement(
            binding,
            "users:17",
            "billing:17",
            "subscription:17",
            None,
            issue(exact),
            datetime(2026, 9, 15, tzinfo=timezone.utc),
        )


def test_late_bound_authority_rebinding_and_public_monkeypatch_fail_closed():
    live = set()
    enabled = True

    def issue(view):
        value = LiveBillingFact(view)
        live.add(id(value))
        return value

    def validate(value):
        if enabled and id(value) in live:
            return value.view
        raise ValueError

    def project(value):
        if enabled and id(value) in live:
            return value.view
        raise ValueError

    binding = subject.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )
    enabled = False
    with pytest.raises(subject.RuntimeEntitlementAdmissionError, match="authority changed"):
        admit(binding, issue(fact_view()))

    # Existing opaque runtime validation does not depend on rebound module helpers.
    binding2, issue2 = authority()
    runtime = admit(binding2, issue2(fact_view()))
    original = subject.RuntimeEntitlementAdmissionError
    subject.RuntimeEntitlementAdmissionError = RuntimeError
    try:
        assert dict(subject.validate_runtime_entitlement(runtime))["state"] == "paid"
    finally:
        subject.RuntimeEntitlementAdmissionError = original


def test_module_has_no_io_provider_route_config_auth_session_or_database_surface():
    tree = ast.parse(
        (ROOT / "reserved/billing/runtime_entitlement_admission.py").read_text()
    )
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"__future__", "datetime", "hashlib", "json", "re", "types", "weakref"}
    assert set(subject.__all__) == {
        "BILLING_FACT_ADMISSION_STATUS",
        "BILLING_FACT_PROTOCOL_VERSION",
        "CONTRACT_VERSION",
        "FD_W10_003",
        "FD_W10_004",
        "RECOVERY_DAYS",
        "RUNTIME_ADMISSION_STATUS",
        "RUNTIME_DECISION_PROTOCOL_VERSION",
        "RuntimeEntitlementAdmissionError",
        "RuntimeEntitlementAdmissionHandle",
        "RuntimeEntitlementHandle",
        "admit_runtime_entitlement",
        "bind_runtime_entitlement_admission",
        "project_runtime_entitlement",
        "validate_runtime_entitlement",
    }


def test_evidence_records_exact_non_authority_and_founder_boundaries():
    text = (ROOT / "docs/W10_S3C_RUNTIME_ENTITLEMENT_ADMISSION.md").read_text()
    for phrase in (
        "provider-neutral",
        "route-less",
        "non-durable",
        "FD-W10-003",
        "FD-W10-004",
        "current subscription period",
        "seven UTC calendar days",
        "never create, restore, extend, prolong or strengthen",
        "Detached S3A/S3B tuples",
        "does not authenticate provider evidence",
        "does not complete W10-S3 or W10-S5",
        "reserved-runtime-entitlement-decision/1.0",
    ):
        assert phrase in text
