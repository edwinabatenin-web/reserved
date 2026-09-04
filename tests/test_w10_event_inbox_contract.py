"""Focused adversarial tests for the contract-only W10-S3B candidate."""

from __future__ import annotations

import builtins
import copy
import dis
import inspect
import pickle
from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

import reserved.billing.event_inbox_contract as contract


UTC = timezone.utc
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def projected(value, projector):
    return dict(projector(value))


def account(owner=41, account_id="billing-account-1"):
    return contract.issue_billing_account_record(
        owner_user_id=owner,
        billing_account_id=account_id,
    )


def subscription(owner=41, account_id="billing-account-1", subscription_id="subscription-1"):
    return contract.issue_billing_subscription_record(
        account=account(owner, account_id),
        subscription_id=subscription_id,
        plan_key="monthly",
    )


def event(
    *,
    owner=41,
    account_id="billing-account-1",
    subscription_id="subscription-1",
    event_id="evt-1",
    namespace="stripe-subscription/test-scope",
    api_version="2026-08-27.basil",
    object_id="invoice-1",
    event_type="invoice.paid",
    effective=date(2026, 10, 1),
    digest=DIGEST_A,
    kind="initial_payment_confirmed",
    paid_through=date(2026, 10, 31),
    evidence="evidence/ref-1",
):
    return contract.issue_structural_billing_event_record(
        subscription=subscription(owner, account_id, subscription_id),
        source_namespace=namespace,
        source_event_id=event_id,
        source_api_version=api_version,
        provider_object_id=object_id,
        provider_event_type=event_type,
        effective_date=effective,
        paid_through=paid_through,
        evidence_reference=evidence,
        source_event_digest=digest,
        observation_kind=kind,
    )


def receipt(existing, candidate, receipt_id="receipt-1"):
    return contract.classify_event_admission(
        existing_events=tuple(existing),
        candidate=candidate,
        receipt_id=receipt_id,
        received_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
    )


def disposition(observed=None):
    observed = observed or event()
    return contract.append_event_disposition(
        existing_dispositions=(),
        event=observed,
        disposition_id="disposition-1",
        kind="pending_future_verified_admission",
        evidence_reference="evidence/disposition-1",
        recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
    )


def test_contract_preserves_exact_provenance_gates_and_non_implementation_status():
    facts = projected(contract.EVENT_INBOX_CONTRACT, contract.project_event_inbox_contract)
    provenance = dict(facts["authority_provenance"])
    assert facts["contract_version"] == "reserved-w10-event-inbox-contract/1.0"
    assert facts["assurance_status"] == (
        "contract_only_not_persistence_not_event_inbox_not_w10_s3_completion"
    )
    assert provenance == {
        "candidate_base_commit": "3079553c3b4d7f69eede6887a5b199b8cb80caac",
        "founder_authority": ("FD-W9-001", "FD-W10-001", "FD-W10-002", "FD-W10-003"),
        "w9_contract_commit": "c489c25bab669c64e1c11d28caf29fcde9678fdd",
        "w10_s1_commit": "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
        "w10_s2a_commit": "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
        "w10_s3a_commit": "94bd87f019dc226ec8c73f32515229189500cf06",
        "w10_s4a_commit": "2ad4a63dd1f10ba38859050b47245c28390667d8",
    }
    assert "approved_datastore_and_migration_rules" in facts["unresolved_gates"]
    assert "approved_retention_erasure_legal_hold_and_backup_expiry" in facts["unresolved_gates"]
    assert "raw_provider_payload" in facts["prohibited_retention"]
    assert "provider_signature_header" in facts["prohibited_retention"]
    assert "database_or_file_persistence" in facts["scope_exclusions"]
    assert "entitlement_mutation_or_route_enforcement" in facts["scope_exclusions"]


@pytest.mark.parametrize("bad", [True, False, 0, -1, "41", 1.0, None])
def test_users_id_adapter_accepts_only_positive_exact_integer(bad):
    with pytest.raises((TypeError, ValueError)):
        contract.canonical_owner_id_from_users_id(bad)


def test_users_id_adapter_and_record_chain_preserve_one_owner_boundary():
    assert contract.canonical_owner_id_from_users_id(41) == "41"
    acct = projected(account(), contract.project_billing_account_record)
    sub = projected(subscription(), contract.project_billing_subscription_record)
    observed = projected(event(), contract.project_billing_event_record)
    assert acct["owner_user_id"] == sub["owner_user_id"] == observed["owner_user_id"] == 41
    assert acct["canonical_owner_id"] == sub["canonical_owner_id"] == observed["canonical_owner_id"] == "41"
    assert acct["billing_account_id"] == sub["billing_account_id"] == observed["billing_account_id"]
    assert sub["subscription_id"] == observed["subscription_id"]
    assert acct["catalogue_authority_version"] == "FD-W10-001/2026-09-02/v1"
    assert "not_provider_verified" in observed["trust_status"]


def test_exact_replay_is_distinct_from_reused_identity_with_different_content():
    original = event()
    replay = event()
    replay_result = projected(receipt((original,), replay), contract.project_billing_event_receipt_record)
    assert replay_result["outcome"] == "exact_replay"
    assert replay_result["compared_event_fingerprint"] == replay_result["event_fingerprint"]
    assert replay_result["entitlement_mutation_allowed"] is False

    conflict = event(digest=DIGEST_B)
    conflict_result = projected(
        receipt((original,), conflict, "receipt-2"),
        contract.project_billing_event_receipt_record,
    )
    assert conflict_result["outcome"] == "event_identity_conflict_reconciliation_required"
    assert conflict_result["compared_event_fingerprint"] != conflict_result["event_fingerprint"]
    assert conflict_result["entitlement_mutation_allowed"] is False


def test_provider_object_and_event_type_are_a_secondary_duplicate_check_not_identity():
    original = event()
    possible_duplicate = event(event_id="evt-2", digest=DIGEST_B, evidence="evidence/ref-2")
    result = projected(
        receipt((original,), possible_duplicate),
        contract.project_billing_event_receipt_record,
    )
    assert result["event_identity"] == ("stripe-subscription/test-scope", "evt-2")
    assert result["outcome"] == "object_type_secondary_duplicate_reconciliation_required"


@pytest.mark.parametrize("effective", [date(2026, 9, 30), date(2026, 10, 1)])
def test_older_or_same_day_distinct_event_requires_reconciliation(effective):
    original = event()
    candidate = event(
        event_id="evt-2",
        object_id="invoice-2",
        event_type="customer.subscription.updated",
        effective=effective,
        digest=DIGEST_B,
        kind="cancellation_confirmed",
        paid_through=None,
        evidence="evidence/ref-2",
    )
    result = projected(receipt((original,), candidate), contract.project_billing_event_receipt_record)
    assert result["outcome"] == "older_or_same_day_distinct_reconciliation_required"
    assert result["entitlement_mutation_allowed"] is False


def test_new_canonical_candidate_is_pending_and_never_direct_entitlement_authority():
    candidate = event()
    event_facts = projected(candidate, contract.project_billing_event_record)
    result = projected(receipt((), candidate), contract.project_billing_event_receipt_record)
    assert event_facts["entitlement_semantics"] == (
        "canonical_candidate_only_no_direct_entitlement_effect"
    )
    assert result["outcome"] == "new_structural_candidate_pending_future_verified_admission"
    assert result["entitlement_mutation_allowed"] is False


@pytest.mark.parametrize(
    "kind,event_type",
    [
        ("unknown", "provider.future_event"),
        ("refund_observed", "charge.refunded"),
        ("dispute_observed", "charge.dispute.created"),
        ("chargeback_observed", "charge.dispute.closed"),
        ("reversal_observed", "charge.refund.updated"),
    ],
)
def test_unresolved_observations_have_zero_entitlement_effect(kind, event_type):
    candidate = event(
        kind=kind,
        event_type=event_type,
        paid_through=None,
        effective=date(2026, 11, 1),
    )
    event_facts = projected(candidate, contract.project_billing_event_record)
    result = projected(receipt((), candidate), contract.project_billing_event_receipt_record)
    assert event_facts["entitlement_semantics"] == "reconciliation_only_zero_entitlement_effect"
    assert result["outcome"] == "unresolved_policy_observation_reconciliation_only"
    assert result["entitlement_mutation_allowed"] is False


def test_duplicate_identity_inside_existing_set_fails_closed():
    with pytest.raises(ValueError, match="duplicate immutable identity"):
        receipt((event(), event()), event(event_id="evt-2", object_id="invoice-2"))


def test_dispositions_form_append_only_chain_and_corrections_never_mutate_prior_record():
    observed = event()
    first = contract.append_event_disposition(
        existing_dispositions=(),
        event=observed,
        disposition_id="disposition-1",
        kind="reconciliation_required",
        evidence_reference="evidence/disposition-1",
        recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
    )
    first_before = contract.project_billing_event_disposition_record(first)
    first_identity = dict(first_before)["disposition_identity"]
    correction = contract.append_event_disposition(
        existing_dispositions=(first,),
        event=observed,
        disposition_id="disposition-2",
        kind="correction_recorded",
        evidence_reference="evidence/disposition-2",
        recorded_at=datetime(2026, 10, 1, 14, tzinfo=UTC),
        correction_of_disposition_identity=first_identity,
    )
    corrected = projected(correction, contract.project_billing_event_disposition_record)
    assert contract.project_billing_event_disposition_record(first) == first_before
    assert corrected["sequence"] == 2
    assert corrected["predecessor_disposition_identity"] == first_identity
    assert corrected["correction_of_disposition_identity"] == first_identity
    assert corrected["entitlement_mutation_allowed"] is False

    with pytest.raises(ValueError, match="existing disposition"):
        contract.append_event_disposition(
            existing_dispositions=(first,),
            event=observed,
            disposition_id="disposition-3",
            kind="correction_recorded",
            evidence_reference="evidence/disposition-3",
            recorded_at=datetime(2026, 10, 1, 15, tzinfo=UTC),
            correction_of_disposition_identity="billing-disposition:sha256-missing",
        )


def test_cross_event_or_broken_disposition_chain_fails_closed():
    first_event = event()
    first = contract.append_event_disposition(
        existing_dispositions=(),
        event=first_event,
        disposition_id="disposition-1",
        kind="reconciliation_required",
        evidence_reference="evidence/disposition-1",
        recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
    )
    other_event = event(event_id="evt-2", object_id="invoice-2", digest=DIGEST_B)
    with pytest.raises(ValueError, match="append-only event chain"):
        contract.append_event_disposition(
            existing_dispositions=(first,),
            event=other_event,
            disposition_id="disposition-2",
            kind="reconciliation_required",
            evidence_reference="evidence/disposition-2",
            recorded_at=datetime(2026, 10, 1, 14, tzinfo=UTC),
        )


def test_public_construction_object_new_and_pickle_cannot_forge_records():
    cases = (
        (contract.EventInboxContractHandle, contract.validate_event_inbox_contract),
        (contract.BillingAccountRecord, contract.validate_billing_account_record),
        (contract.BillingSubscriptionRecord, contract.validate_billing_subscription_record),
        (contract.BillingEventRecord, contract.validate_billing_event_record),
        (contract.BillingEventReceiptRecord, contract.validate_billing_event_receipt_record),
        (contract.BillingEventDispositionRecord, contract.validate_billing_event_disposition_record),
    )
    for cls, validator in cases:
        with pytest.raises(TypeError, match="producer-issued"):
            cls()
        forged = object.__new__(cls)
        with pytest.raises(ValueError, match="not producer-issued"):
            validator(forged)

    issued = (
        contract.EVENT_INBOX_CONTRACT,
        account(),
        subscription(),
        event(),
        receipt((), event()),
        disposition(),
    )
    for value in issued:
        with pytest.raises(TypeError, match="not serialisable"):
            pickle.dumps(value)


def test_copy_and_deepcopy_revalidate_and_issue_immutable_aliases():
    values_and_projectors = (
        (contract.EVENT_INBOX_CONTRACT, contract.project_event_inbox_contract),
        (account(), contract.project_billing_account_record),
        (subscription(), contract.project_billing_subscription_record),
        (event(), contract.project_billing_event_record),
        (receipt((), event()), contract.project_billing_event_receipt_record),
        (disposition(), contract.project_billing_event_disposition_record),
    )
    for value, projector in values_and_projectors:
        shallow = copy.copy(value)
        deep = copy.deepcopy(value)
        assert shallow is not value and deep is not value
        assert projector(shallow) == projector(value) == projector(deep)
        with pytest.raises(AttributeError):
            value.extra = "forged"


def test_module_global_and_exported_class_rebinding_cannot_change_captured_acceptance(monkeypatch):
    issued = event()
    expected = contract.project_billing_event_record(issued)
    original_projector = contract.project_billing_event_record
    original_copy = contract.copy_billing_event_record

    for name in ("type", "len", "tuple", "str", "any", "enumerate", "dict", "set"):
        monkeypatch.setattr(contract, name, lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(contract, "BillingEventRecord", object)
    monkeypatch.setattr(contract, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(contract, "copy_billing_event_record", lambda value: object())

    assert original_projector(issued) == expected
    copied = copy.copy(issued)
    assert original_projector(copied) == expected
    assert original_projector(original_copy(issued)) == expected


def test_acceptance_entry_points_and_handle_methods_do_not_resolve_mutable_globals():
    functions = (
        contract.validate_event_inbox_contract,
        contract.canonical_owner_id_from_users_id,
        contract.issue_billing_account_record,
        contract.issue_billing_subscription_record,
        contract.issue_structural_billing_event_record,
        contract.classify_event_admission,
        contract.append_event_disposition,
        contract.EventInboxContractHandle.__copy__,
        contract.BillingEventRecord.__copy__,
        contract.BillingEventRecord.__reduce_ex__,
    )
    for function in functions:
        global_loads = [
            instruction.argval
            for instruction in dis.get_instructions(function)
            if instruction.opname in {"LOAD_GLOBAL", "STORE_GLOBAL", "DELETE_GLOBAL"}
        ]
        assert not global_loads, f"{function.__qualname__} resolves globals: {global_loads}"


def test_event_api_cannot_receive_or_retain_raw_payload_signature_or_secret():
    parameters = tuple(inspect.signature(contract.issue_structural_billing_event_record).parameters)
    assert parameters == (
        "subscription",
        "source_namespace",
        "source_event_id",
        "source_api_version",
        "provider_object_id",
        "provider_event_type",
        "effective_date",
        "paid_through",
        "evidence_reference",
        "source_event_digest",
        "observation_kind",
    )
    fields = projected(event(), contract.project_billing_event_record)
    forbidden = {"raw_payload", "raw_request_body", "signature", "secret", "credential", "api_key"}
    assert forbidden.isdisjoint(fields)
    assert fields["source_event_digest"] == DIGEST_A


@pytest.mark.parametrize(
    "overrides",
    [
        {"evidence": "sk_live_supersecret"},
        {"object_id": "whsec_endpointsecret"},
        {"event_id": "credential_api_key_123"},
        {"namespace": "provider/access_token/customer"},
        {"api_version": "client_secret"},
        {"event_type": "authorization.bearer"},
    ],
)
def test_event_retained_fields_reject_credential_and_secret_shapes(overrides):
    with pytest.raises(ValueError, match="unsafe credential-shaped"):
        event(**overrides)


@pytest.mark.parametrize(
    "source_event_id",
    [
        "api.key-123",
        "access/token/123",
        "refresh:token:123",
        "sk.live.123",
        "rk:test:123",
    ],
)
def test_source_event_id_secret_markers_cannot_bypass_with_any_allowed_separator(
    source_event_id,
):
    with pytest.raises(ValueError, match="unsafe credential-shaped source_event_id"):
        event(event_id=source_event_id)


@pytest.mark.parametrize(
    "overrides",
    [
        {"namespace": "provider/access/token/123"},
        {"api_version": "refresh:token:123"},
        {"object_id": "sk.live.123"},
        {"event_type": "rk:test:123"},
        {"evidence": "evidence/api.key-123"},
    ],
)
def test_all_event_field_families_apply_separator_normalised_screening(overrides):
    with pytest.raises(ValueError, match="unsafe credential-shaped"):
        event(**overrides)


def test_account_subscription_receipt_and_disposition_fields_reject_unsafe_retention():
    with pytest.raises(ValueError, match="unsafe credential-shaped billing_account_id"):
        account(account_id="refresh_token-1")
    with pytest.raises(ValueError, match="unsafe credential-shaped subscription_id"):
        subscription(subscription_id="private_key-1")
    with pytest.raises(ValueError, match="unsafe credential-shaped receipt_id"):
        receipt((), event(), receipt_id="password-1")
    with pytest.raises(ValueError, match="unsafe credential-shaped disposition_id"):
        contract.append_event_disposition(
            existing_dispositions=(),
            event=event(),
            disposition_id="api_key-1",
            kind="pending_future_verified_admission",
            evidence_reference="evidence/disposition-1",
            recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
        )


def test_non_event_field_families_apply_separator_normalised_screening():
    with pytest.raises(ValueError, match="unsafe credential-shaped billing_account_id"):
        account(account_id="access/token/123")
    with pytest.raises(ValueError, match="unsafe credential-shaped subscription_id"):
        subscription(subscription_id="refresh:token:123")
    with pytest.raises(ValueError, match="unsafe credential-shaped receipt_id"):
        receipt((), event(), receipt_id="sk.live.123")
    with pytest.raises(ValueError, match="unsafe credential-shaped disposition_id"):
        contract.append_event_disposition(
            existing_dispositions=(),
            event=event(),
            disposition_id="rk:test:123",
            kind="pending_future_verified_admission",
            evidence_reference="evidence/disposition-1",
            recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="unsafe credential-shaped evidence_reference"):
        contract.append_event_disposition(
            existing_dispositions=(),
            event=event(),
            disposition_id="disposition-1",
            kind="pending_future_verified_admission",
            evidence_reference="evidence/api.key-123",
            recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="unsafe credential-shaped evidence_reference"):
        contract.append_event_disposition(
            existing_dispositions=(),
            event=event(),
            disposition_id="disposition-1",
            kind="pending_future_verified_admission",
            evidence_reference="whsec_endpointsecret",
            recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
        )


def test_lexical_guard_does_not_mechanically_block_innocuous_identifier_substrings():
    observed = event(
        account_id="monkey-account-1",
        subscription_id="access-tokenization-1",
        event_id="tokenization-event-1",
        namespace="public-keyboard/events",
        object_id="secretary-record-1",
        evidence="evidence/credentialed-review-1",
    )
    facts = projected(observed, contract.project_billing_event_record)
    assert facts["billing_account_id"] == "monkey-account-1"
    assert facts["subscription_id"] == "access-tokenization-1"
    assert facts["source_event_id"] == "tokenization-event-1"
    assert facts["provider_object_id"] == "secretary-record-1"


def test_disposition_ids_are_unique_and_recorded_times_strictly_increase():
    observed = event()
    first = contract.append_event_disposition(
        existing_dispositions=(),
        event=observed,
        disposition_id="disposition-1",
        kind="reconciliation_required",
        evidence_reference="evidence/disposition-1",
        recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="disposition_id must be unique"):
        contract.append_event_disposition(
            existing_dispositions=(first,),
            event=observed,
            disposition_id="disposition-1",
            kind="reconciliation_required",
            evidence_reference="evidence/disposition-2",
            recorded_at=datetime(2026, 10, 1, 14, tzinfo=UTC),
        )
    for recorded_at in (
        datetime(2026, 10, 1, 12, tzinfo=UTC),
        datetime(2026, 10, 1, 13, tzinfo=UTC),
    ):
        with pytest.raises(ValueError, match="strictly advance"):
            contract.append_event_disposition(
                existing_dispositions=(first,),
                event=observed,
                disposition_id="disposition-2",
                kind="reconciliation_required",
                evidence_reference="evidence/disposition-2",
                recorded_at=recorded_at,
            )


def test_copied_duplicate_existing_disposition_corrupts_chain_and_fails_closed():
    observed = event()
    first = disposition(observed)
    duplicated = copy.copy(first)
    with pytest.raises(ValueError, match="unique disposition IDs"):
        contract.append_event_disposition(
            existing_dispositions=(first, duplicated),
            event=observed,
            disposition_id="disposition-2",
            kind="reconciliation_required",
            evidence_reference="evidence/disposition-2",
            recorded_at=datetime(2026, 10, 1, 14, tzinfo=UTC),
        )


class StatefulTimezone(tzinfo):
    """Offset changes across calls, reproducing the former mutable-tz bypass."""

    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(0) if self.calls == 1 else timedelta(hours=23)

    def dst(self, dt):
        return timedelta(0)


def test_stateful_custom_tzinfo_cannot_enter_receipts_or_backdate_disposition_chain():
    proof_tz = StatefulTimezone()
    proof_time = datetime(2026, 10, 1, 14, tzinfo=proof_tz)
    # This is the former bypass: the first zero offset could pass admission, then
    # the same retained datetime changed by 23 hours for projection/comparison.
    assert proof_time.utcoffset() == timedelta(0)
    assert proof_time.utcoffset() == timedelta(hours=23)

    hostile_tz = StatefulTimezone()
    hostile_time = datetime(2026, 10, 1, 14, tzinfo=hostile_tz)
    observed = event()

    with pytest.raises(ValueError, match="built-in timezone.utc singleton"):
        contract.classify_event_admission(
            existing_events=(),
            candidate=observed,
            receipt_id="receipt-1",
            received_at=hostile_time,
        )
    assert hostile_tz.calls == 0

    first = disposition(observed)
    with pytest.raises(ValueError, match="built-in timezone.utc singleton"):
        contract.append_event_disposition(
            existing_dispositions=(first,),
            event=observed,
            disposition_id="disposition-2",
            kind="reconciliation_required",
            evidence_reference="evidence/disposition-2",
            recorded_at=hostile_time,
        )
    # Rejection occurs by singleton identity, before executing mutable utcoffset.
    assert hostile_tz.calls == 0


def test_projected_retained_datetimes_are_exact_immutable_builtin_utc_values():
    observed = event()
    received = receipt((), observed)
    recorded = disposition(observed)
    received_at = projected(received, contract.project_billing_event_receipt_record)[
        "received_at"
    ]
    recorded_at = projected(recorded, contract.project_billing_event_disposition_record)[
        "recorded_at"
    ]
    for value in (received_at, recorded_at):
        assert type(value) is datetime
        assert value.tzinfo is timezone.utc
        assert value.utcoffset() == timedelta(0)


def test_supported_operations_remain_pure_when_file_open_is_disabled(monkeypatch):
    def forbidden_open(*args, **kwargs):
        raise AssertionError("contract attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    observed = event()
    receipt_record = receipt((), observed)
    disposition = contract.append_event_disposition(
        existing_dispositions=(),
        event=observed,
        disposition_id="disposition-1",
        kind="pending_future_verified_admission",
        evidence_reference="evidence/disposition-1",
        recorded_at=datetime(2026, 10, 1, 13, tzinfo=UTC),
    )
    assert contract.validate_billing_event_record(observed)
    assert contract.validate_billing_event_receipt_record(receipt_record)
    assert contract.validate_billing_event_disposition_record(disposition)
