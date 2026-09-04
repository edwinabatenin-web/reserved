"""Datastore-neutral W10-S3B billing event-inbox contract candidate.

This module defines immutable structural records and pure admission/reconciliation
invariants for a *future* durable billing boundary.  It performs no I/O, chooses
no datastore, verifies no provider signature, parses no webhook, retains no raw
payload or secret, mutates no entitlement and activates nothing.  Producer
issuance proves only that a record was constructed by this module and satisfies
this contract; it is never provider-authenticity or persistence evidence.
"""

from __future__ import annotations

import copy as _copy_module
import hashlib as _hashlib_module
import json as _json_module
import re as _re_module
import weakref as _weakref_module
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timezone as _timezone


def _build_event_inbox_contract():
    # Capture every acceptance-critical collaborator once.  Public module names,
    # classes and constants are therefore descriptive exports, not authority.
    _type = type
    _id = id
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _dict = dict
    _set = set
    _zip = zip
    _len = len
    _any = any
    _enumerate = enumerate
    _str = str
    _int = int
    _bool = bool
    _bytes = bytes
    _TypeError = TypeError
    _ValueError = ValueError
    _AttributeError = AttributeError
    _copy = _copy_module.copy
    _deepcopy = _copy_module.deepcopy
    _sha256 = _hashlib_module.sha256
    _json_dumps = _json_module.dumps
    _compile = _re_module.compile
    _ignore_case = _re_module.IGNORECASE
    _Date = _date
    _Datetime = _datetime
    _UTC = _timezone.utc
    _WeakValueDictionary = _weakref_module.WeakValueDictionary

    _contract_version = "reserved-w10-event-inbox-contract/1.0"
    _catalogue_authority_version = "FD-W10-001/2026-09-02/v1"
    _record_purpose = "future_owner_bound_billing_event_inbox"
    _structural_trust = "producer_issued_structure_not_provider_verified"
    _no_direct_entitlement = "canonical_candidate_only_no_direct_entitlement_effect"
    _zero_entitlement = "reconciliation_only_zero_entitlement_effect"

    _identifier_pattern = _compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
    _digest_pattern = _compile(r"^sha256:[0-9a-f]{64}$")
    _retained_separator_pattern = _compile(r"[._:/-]+")
    # A bounded lexical defence for every caller-supplied string retained by a
    # future record.  This is deliberately conservative around well-known
    # credential shapes while leaving ordinary identifiers such as
    # ``secretary-record`` and ``tokenization-event`` valid.  It is not a DLP or
    # entropy detector; the approved future allowlist remains a recorded gate.
    _unsafe_retained_pattern = _compile(
        r"(?:^|_)(?:"
        r"(?:sk|rk)_(?:live|test)|"
        r"whsec|"
        r"secret|credential|password|passwd|bearer|authorization|"
        r"api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"private[_-]?key|secret[_-]?key|client[_-]?secret|"
        r"webhook[_-]?secret|endpoint[_-]?secret"
        r")(?:_|$)",
        _ignore_case,
    )
    _plan_keys = ("monthly", "six_month", "yearly")
    _canonical_observation_kinds = (
        "initial_payment_confirmed",
        "renewal_payment_confirmed",
        "renewal_payment_failed",
        "cancellation_confirmed",
    )
    _zero_effect_kinds = (
        "unknown",
        "refund_observed",
        "dispute_observed",
        "chargeback_observed",
        "reversal_observed",
    )
    _observation_kinds = _canonical_observation_kinds + _zero_effect_kinds
    _admission_outcomes = (
        "new_structural_candidate_pending_future_verified_admission",
        "exact_replay",
        "event_identity_conflict_reconciliation_required",
        "object_type_secondary_duplicate_reconciliation_required",
        "older_or_same_day_distinct_reconciliation_required",
        "unresolved_policy_observation_reconciliation_only",
    )
    _disposition_kinds = (
        "pending_future_verified_admission",
        "reconciliation_required",
        "canonical_observation_recorded",
        "correction_recorded",
        "rejected",
    )

    _provenance = (
        ("candidate_base_commit", "3079553c3b4d7f69eede6887a5b199b8cb80caac"),
        ("founder_authority", ("FD-W9-001", "FD-W10-001", "FD-W10-002", "FD-W10-003")),
        ("w9_contract_commit", "c489c25bab669c64e1c11d28caf29fcde9678fdd"),
        ("w10_s1_commit", "9e8f94a9906f0c9d5c85b47223d20c34be499e1c"),
        ("w10_s2a_commit", "5464bfac7bec6b3456d1895b2355a7e8ce86859b"),
        ("w10_s3a_commit", "94bd87f019dc226ec8c73f32515229189500cf06"),
        ("w10_s4a_commit", "2ad4a63dd1f10ba38859050b47245c28390667d8"),
    )
    _unresolved_gates = (
        "approved_datastore_and_migration_rules",
        "approved_encryption_at_rest_authenticated_integrity_and_key_custody",
        "approved_field_level_minimisation_and_sanitised_evidence_allowlist",
        "approved_retention_erasure_legal_hold_and_backup_expiry",
        "approved_provider_source_binding_and_event_namespace",
        "authenticated_raw_body_signature_verification_and_owner_reconciliation",
        "approved_refund_dispute_chargeback_and_reversal_translation_and_consequences",
        "approved_manual_correction_and_override_authority",
        "exclusive_shared_migration_ownership",
        "independent_schema_security_privacy_and_integrated_review",
    )
    _prohibited_retention = (
        "raw_provider_payload",
        "raw_request_body",
        "provider_signature_header",
        "webhook_endpoint_secret",
        "credential_or_api_key",
        "complete_provider_object",
        "provider_status_as_entitlement_flag",
    )
    _scope_exclusions = (
        "database_or_file_persistence",
        "schema_migration",
        "network_or_provider_sdk",
        "credential_or_configuration_access",
        "webhook_parsing_or_signature_verification",
        "provider_authenticity_or_owner_verification",
        "entitlement_mutation_or_route_enforcement",
        "checkout_portal_charge_or_activation",
        "retention_erasure_or_legal_hold_execution",
        "claim_that_an_event_inbox_or_w10_s3_is_implemented",
    )

    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _int, _bool, _Date, _Datetime) or value is None:
            return value
        raise _ValueError("event-inbox contract contains unsupported state")

    def _sanitised_retained_identifier(value, label):
        if _type(value) is not _str or _identifier_pattern.fullmatch(value) is None:
            raise _ValueError(f"invalid {label}")
        # Treat every allowed separator identically before compound-marker
        # matching.  ``api.key``, ``api/key`` and ``api:key`` must never bypass
        # the same guard already applied to ``api_key`` and ``api-key``.
        normalised_for_screening = _retained_separator_pattern.sub("_", value)
        if _unsafe_retained_pattern.search(normalised_for_screening) is not None:
            raise _ValueError(f"unsafe credential-shaped {label} must not be retained")
        return value

    def _internal_record_id(value, label):
        return _sanitised_retained_identifier(value, label)

    def _source_identifier(value, label):
        return _sanitised_retained_identifier(value, label)

    def _source_metadata(value, label):
        return _sanitised_retained_identifier(value, label)

    def _sanitised_evidence_reference(value):
        return _sanitised_retained_identifier(value, "evidence_reference")

    def _digest(value, label):
        if _type(value) is not _str or _digest_pattern.fullmatch(value) is None:
            raise _ValueError(f"invalid {label}")
        return value

    def _utc(value, label):
        # Caller-owned tzinfo implementations are stateful executable objects:
        # repeated utcoffset() calls can change comparisons and projected facts.
        # Retain only exact built-in datetimes bound to the captured UTC singleton.
        if _type(value) is not _Datetime or value.tzinfo is not _UTC:
            raise _ValueError(
                f"{label} must be an exact datetime using the built-in timezone.utc singleton"
            )
        return value

    def _canonical_owner(user_id):
        if _type(user_id) is not _int or user_id <= 0 or user_id > 9223372036854775807:
            raise _ValueError("owner_user_id must be a positive exact users.id integer")
        return _str(user_id)

    def _canonical_json_value(value):
        if _type(value) is _tuple:
            return [_canonical_json_value(item) for item in value]
        if _type(value) is _Datetime:
            return value.isoformat()
        if _type(value) is _Date:
            return value.isoformat()
        if _type(value) in (_str, _int, _bool) or value is None:
            return value
        raise _ValueError("unsupported event fingerprint value")

    def _content_identity(prefix, state):
        encoded = _json_dumps(
            _canonical_json_value(state),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        return f"{prefix}:sha256-{_sha256(encoded).hexdigest()}"

    class EventInboxContractHandle:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _contract_token:
                raise _TypeError("event-inbox contract handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_event_inbox_contract(self)

        def __deepcopy__(self, memo):
            return copy_event_inbox_contract(self)

        def __reduce__(self):
            raise _TypeError("event-inbox contract handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("event-inbox contract handles are not serialisable")

    class BillingAccountRecord:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _record_token:
                raise _TypeError("billing-account records are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_account_record(self)

        def __deepcopy__(self, memo):
            return copy_billing_account_record(self)

        def __reduce__(self):
            raise _TypeError("billing-account records are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("billing-account records are not serialisable")

    class BillingSubscriptionRecord:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _record_token:
                raise _TypeError("billing-subscription records are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_subscription_record(self)

        def __deepcopy__(self, memo):
            return copy_billing_subscription_record(self)

        def __reduce__(self):
            raise _TypeError("billing-subscription records are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("billing-subscription records are not serialisable")

    class BillingEventRecord:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _record_token:
                raise _TypeError("billing-event records are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_event_record(self)

        def __deepcopy__(self, memo):
            return copy_billing_event_record(self)

        def __reduce__(self):
            raise _TypeError("billing-event records are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("billing-event records are not serialisable")

    class BillingEventReceiptRecord:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _record_token:
                raise _TypeError("billing-event receipt records are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_event_receipt_record(self)

        def __deepcopy__(self, memo):
            return copy_billing_event_receipt_record(self)

        def __reduce__(self):
            raise _TypeError("billing-event receipt records are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("billing-event receipt records are not serialisable")

    class BillingEventDispositionRecord:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _record_token:
                raise _TypeError("billing-event disposition records are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_event_disposition_record(self)

        def __deepcopy__(self, memo):
            return copy_billing_event_disposition_record(self)

        def __reduce__(self):
            raise _TypeError("billing-event disposition records are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("billing-event disposition records are not serialisable")

    _Contract = EventInboxContractHandle
    _Account = BillingAccountRecord
    _Subscription = BillingSubscriptionRecord
    _Event = BillingEventRecord
    _Receipt = BillingEventReceiptRecord
    _Disposition = BillingEventDispositionRecord
    _contract_token = _object()
    _record_token = _object()

    _registries = {
        _Contract: {},
        _Account: {},
        _Subscription: {},
        _Event: {},
        _Receipt: {},
        _Disposition: {},
    }
    _live = {
        cls: _WeakValueDictionary()
        for cls in (_Contract, _Account, _Subscription, _Event, _Receipt, _Disposition)
    }

    def _issue(cls, state):
        handle = _object_new(cls)
        identity = _id(handle)
        _registries[cls][identity] = _clone(state)
        _live[cls][identity] = handle
        return handle

    def _validated(value, cls, label):
        if _type(value) is not cls:
            raise _TypeError(f"{label} must be an exact producer-issued record")
        identity = _id(value)
        if _live[cls].get(identity) is not value or identity not in _registries[cls]:
            raise _ValueError(f"{label} is not producer-issued or is stale")
        return _clone(_registries[cls][identity])

    _account_fields = (
        "contract_version",
        "owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "catalogue_authority_version",
        "record_purpose",
        "trust_status",
    )
    _subscription_fields = (
        "contract_version",
        "owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "subscription_id",
        "catalogue_authority_version",
        "plan_key",
        "record_purpose",
        "trust_status",
    )
    _event_fields = (
        "contract_version",
        "owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "subscription_id",
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
        "trust_status",
        "entitlement_semantics",
        "event_fingerprint",
    )
    _receipt_fields = (
        "contract_version",
        "receipt_id",
        "owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "subscription_id",
        "event_identity",
        "event_fingerprint",
        "received_at",
        "outcome",
        "compared_event_fingerprint",
        "entitlement_mutation_allowed",
    )
    _disposition_fields = (
        "contract_version",
        "disposition_id",
        "event_fingerprint",
        "sequence",
        "predecessor_disposition_identity",
        "kind",
        "evidence_reference",
        "recorded_at",
        "correction_of_disposition_identity",
        "entitlement_mutation_allowed",
        "disposition_identity",
    )

    _contract_projection = (
        ("contract_version", _contract_version),
        ("assurance_status", "contract_only_not_persistence_not_event_inbox_not_w10_s3_completion"),
        ("record_purpose", _record_purpose),
        ("authority_provenance", _provenance),
        ("canonical_owner_adapter", "positive_exact_users.id_integer_to_base10_string"),
        ("account_record_fields", _account_fields),
        ("subscription_record_fields", _subscription_fields),
        ("event_record_fields", _event_fields),
        ("receipt_record_fields", _receipt_fields),
        ("disposition_record_fields", _disposition_fields),
        ("canonical_observation_kinds", _canonical_observation_kinds),
        ("zero_entitlement_effect_kinds", _zero_effect_kinds),
        ("admission_outcomes", _admission_outcomes),
        ("unresolved_gates", _unresolved_gates),
        ("prohibited_retention", _prohibited_retention),
        ("scope_exclusions", _scope_exclusions),
    )

    def validate_event_inbox_contract(value):
        return _validated(value, _Contract, "event-inbox contract")

    def project_event_inbox_contract(value):
        return _validated(value, _Contract, "event-inbox contract")

    def copy_event_inbox_contract(value):
        return _issue(_Contract, _validated(value, _Contract, "event-inbox contract"))

    def canonical_owner_id_from_users_id(user_id):
        return _canonical_owner(user_id)

    def issue_billing_account_record(*, owner_user_id, billing_account_id):
        owner_id = _canonical_owner(owner_user_id)
        account_id = _internal_record_id(billing_account_id, "billing_account_id")
        return _issue(
            _Account,
            (
                _contract_version,
                owner_user_id,
                owner_id,
                account_id,
                _catalogue_authority_version,
                _record_purpose,
                _structural_trust,
            ),
        )

    def validate_billing_account_record(value):
        state = _validated(value, _Account, "billing-account record")
        if state != (
            _contract_version,
            state[1],
            _canonical_owner(state[1]),
            _internal_record_id(state[3], "billing_account_id"),
            _catalogue_authority_version,
            _record_purpose,
            _structural_trust,
        ):
            raise _ValueError("billing-account record is inconsistent")
        return state

    def project_billing_account_record(value):
        return _tuple(_zip(_account_fields, validate_billing_account_record(value), strict=True))

    def copy_billing_account_record(value):
        return _issue(_Account, validate_billing_account_record(value))

    def issue_billing_subscription_record(*, account, subscription_id, plan_key):
        account_state = validate_billing_account_record(account)
        if _type(plan_key) is not _str or plan_key not in _plan_keys:
            raise _ValueError("invalid settled plan_key")
        sub_id = _internal_record_id(subscription_id, "subscription_id")
        return _issue(
            _Subscription,
            (
                _contract_version,
                account_state[1],
                account_state[2],
                account_state[3],
                sub_id,
                _catalogue_authority_version,
                plan_key,
                _record_purpose,
                _structural_trust,
            ),
        )

    def validate_billing_subscription_record(value):
        state = _validated(value, _Subscription, "billing-subscription record")
        if state[0] != _contract_version or state[2] != _canonical_owner(state[1]):
            raise _ValueError("billing-subscription owner binding is inconsistent")
        _internal_record_id(state[3], "billing_account_id")
        _internal_record_id(state[4], "subscription_id")
        if state[5] != _catalogue_authority_version or state[6] not in _plan_keys:
            raise _ValueError("billing-subscription catalogue binding is inconsistent")
        if state[7:] != (_record_purpose, _structural_trust):
            raise _ValueError("billing-subscription boundary is inconsistent")
        return state

    def project_billing_subscription_record(value):
        return _tuple(_zip(_subscription_fields, validate_billing_subscription_record(value), strict=True))

    def copy_billing_subscription_record(value):
        return _issue(_Subscription, validate_billing_subscription_record(value))

    def issue_structural_billing_event_record(
        *,
        subscription,
        source_namespace,
        source_event_id,
        source_api_version,
        provider_object_id,
        provider_event_type,
        effective_date,
        paid_through,
        evidence_reference,
        source_event_digest,
        observation_kind,
    ):
        sub = validate_billing_subscription_record(subscription)
        namespace = _source_identifier(source_namespace, "source_namespace")
        event_id = _source_identifier(source_event_id, "source_event_id")
        api_version = _source_metadata(source_api_version, "source_api_version")
        object_id = _source_identifier(provider_object_id, "provider_object_id")
        event_type = _source_metadata(provider_event_type, "provider_event_type")
        evidence = _sanitised_evidence_reference(evidence_reference)
        digest = _digest(source_event_digest, "source_event_digest")
        if _type(effective_date) is not _Date:
            raise _ValueError("effective_date must be an exact date")
        if paid_through is not None and _type(paid_through) is not _Date:
            raise _ValueError("paid_through must be an exact date or None")
        if _type(observation_kind) is not _str or observation_kind not in _observation_kinds:
            raise _ValueError("unsupported observation_kind")
        if observation_kind in ("initial_payment_confirmed", "renewal_payment_confirmed"):
            if paid_through is None or paid_through < effective_date:
                raise _ValueError("confirmed payment requires a current paid period")
        elif paid_through is not None:
            raise _ValueError("non-payment observation must not carry paid_through")
        semantics = (
            _zero_entitlement if observation_kind in _zero_effect_kinds else _no_direct_entitlement
        )
        prefix = (
            _contract_version,
            sub[1],
            sub[2],
            sub[3],
            sub[4],
            namespace,
            event_id,
            api_version,
            object_id,
            event_type,
            effective_date,
            paid_through,
            evidence,
            digest,
            observation_kind,
            _structural_trust,
            semantics,
        )
        return _issue(_Event, prefix + (_content_identity("billing-event", prefix),))

    def validate_billing_event_record(value):
        state = _validated(value, _Event, "billing-event record")
        if _len(state) != _len(_event_fields) or state[0] != _contract_version:
            raise _ValueError("billing-event record contract is inconsistent")
        if state[2] != _canonical_owner(state[1]):
            raise _ValueError("billing-event owner binding is inconsistent")
        for index, label in (
            (3, "billing_account_id"),
            (4, "subscription_id"),
            (5, "source_namespace"),
            (6, "source_event_id"),
            (7, "source_api_version"),
            (8, "provider_object_id"),
            (9, "provider_event_type"),
            (12, "evidence_reference"),
        ):
            if index in (5, 6, 8):
                _source_identifier(state[index], label)
            elif index in (7, 9):
                _source_metadata(state[index], label)
            elif index == 12:
                _sanitised_evidence_reference(state[index])
            else:
                _internal_record_id(state[index], label)
        _digest(state[13], "source_event_digest")
        if _type(state[10]) is not _Date or (state[11] is not None and _type(state[11]) is not _Date):
            raise _ValueError("billing-event dates are invalid")
        if state[14] not in _observation_kinds or state[15] != _structural_trust:
            raise _ValueError("billing-event trust or observation kind is inconsistent")
        expected_semantics = _zero_entitlement if state[14] in _zero_effect_kinds else _no_direct_entitlement
        if state[16] != expected_semantics or state[17] != _content_identity("billing-event", state[:17]):
            raise _ValueError("billing-event fingerprint or entitlement semantics is inconsistent")
        return state

    def project_billing_event_record(value):
        return _tuple(_zip(_event_fields, validate_billing_event_record(value), strict=True))

    def copy_billing_event_record(value):
        return _issue(_Event, validate_billing_event_record(value))

    def classify_event_admission(*, existing_events, candidate, receipt_id, received_at):
        if _type(existing_events) is not _tuple:
            raise _TypeError("existing_events must be an exact tuple")
        candidate_state = validate_billing_event_record(candidate)
        existing = _tuple(validate_billing_event_record(item) for item in existing_events)
        identities = _tuple((item[5], item[6]) for item in existing)
        if _len(identities) != _len(_set(identities)):
            raise _ValueError("existing event set contains a duplicate immutable identity")
        receipt = _internal_record_id(receipt_id, "receipt_id")
        received = _utc(received_at, "received_at")
        outcome = _admission_outcomes[0]
        compared = None
        candidate_identity = (candidate_state[5], candidate_state[6])

        same_identity = _tuple(item for item in existing if (item[5], item[6]) == candidate_identity)
        if same_identity:
            compared = same_identity[0][17]
            outcome = _admission_outcomes[1] if compared == candidate_state[17] else _admission_outcomes[2]
        else:
            secondary = _tuple(
                item
                for item in existing
                if item[5] == candidate_state[5]
                and item[8] == candidate_state[8]
                and item[9] == candidate_state[9]
            )
            if secondary:
                compared = secondary[0][17]
                outcome = _admission_outcomes[3]
            else:
                same_subscription = _tuple(
                    item
                    for item in existing
                    if item[1:5] == candidate_state[1:5]
                )
                if _any(item[10] >= candidate_state[10] for item in same_subscription):
                    outcome = _admission_outcomes[4]
                elif candidate_state[14] in _zero_effect_kinds:
                    outcome = _admission_outcomes[5]

        return _issue(
            _Receipt,
            (
                _contract_version,
                receipt,
                candidate_state[1],
                candidate_state[2],
                candidate_state[3],
                candidate_state[4],
                candidate_identity,
                candidate_state[17],
                received,
                outcome,
                compared,
                False,
            ),
        )

    def validate_billing_event_receipt_record(value):
        state = _validated(value, _Receipt, "billing-event receipt record")
        if _len(state) != _len(_receipt_fields) or state[0] != _contract_version:
            raise _ValueError("billing-event receipt contract is inconsistent")
        _internal_record_id(state[1], "receipt_id")
        if state[3] != _canonical_owner(state[2]):
            raise _ValueError("billing-event receipt owner binding is inconsistent")
        _internal_record_id(state[4], "billing_account_id")
        _internal_record_id(state[5], "subscription_id")
        if _type(state[6]) is not _tuple or _len(state[6]) != 2:
            raise _ValueError("billing-event receipt identity is invalid")
        _source_identifier(state[6][0], "source_namespace")
        _source_identifier(state[6][1], "source_event_id")
        _utc(state[8], "received_at")
        if state[9] not in _admission_outcomes or _type(state[11]) is not _bool or state[11]:
            raise _ValueError("billing-event receipt outcome is invalid")
        return state

    def project_billing_event_receipt_record(value):
        return _tuple(_zip(_receipt_fields, validate_billing_event_receipt_record(value), strict=True))

    def copy_billing_event_receipt_record(value):
        return _issue(_Receipt, validate_billing_event_receipt_record(value))

    def append_event_disposition(
        *,
        existing_dispositions,
        event,
        disposition_id,
        kind,
        evidence_reference,
        recorded_at,
        correction_of_disposition_identity=None,
    ):
        if _type(existing_dispositions) is not _tuple:
            raise _TypeError("existing_dispositions must be an exact tuple")
        event_state = validate_billing_event_record(event)
        previous = _tuple(
            validate_billing_event_disposition_record(item) for item in existing_dispositions
        )
        disposition_ids = _tuple(item[1] for item in previous)
        if _len(disposition_ids) != _len(_set(disposition_ids)):
            raise _ValueError("existing disposition chain must have unique disposition IDs")
        for index, item in _enumerate(previous, start=1):
            expected_predecessor = None if index == 1 else previous[index - 2][10]
            if item[2] != event_state[17] or item[3] != index or item[4] != expected_predecessor:
                raise _ValueError("existing dispositions are not one append-only event chain")
            if index > 1 and item[7] <= previous[index - 2][7]:
                raise _ValueError("existing disposition times must be strictly increasing")
        disposition = _internal_record_id(disposition_id, "disposition_id")
        if disposition in disposition_ids:
            raise _ValueError("disposition_id must be unique within the event chain")
        if _type(kind) is not _str or kind not in _disposition_kinds:
            raise _ValueError("invalid disposition kind")
        evidence = _sanitised_evidence_reference(evidence_reference)
        recorded = _utc(recorded_at, "recorded_at")
        if previous and recorded <= previous[-1][7]:
            raise _ValueError("recorded_at must strictly advance the disposition chain")
        existing_identities = _tuple(item[10] for item in previous)
        if kind == "correction_recorded":
            if correction_of_disposition_identity not in existing_identities:
                raise _ValueError("append-only correction must reference an existing disposition")
        elif correction_of_disposition_identity is not None:
            raise _ValueError("only a correction may reference a prior disposition")
        prefix = (
            _contract_version,
            disposition,
            event_state[17],
            _len(previous) + 1,
            previous[-1][10] if previous else None,
            kind,
            evidence,
            recorded,
            correction_of_disposition_identity,
            False,
        )
        return _issue(_Disposition, prefix + (_content_identity("billing-disposition", prefix),))

    def validate_billing_event_disposition_record(value):
        state = _validated(value, _Disposition, "billing-event disposition record")
        if _len(state) != _len(_disposition_fields) or state[0] != _contract_version:
            raise _ValueError("billing-event disposition contract is inconsistent")
        _internal_record_id(state[1], "disposition_id")
        if _type(state[3]) is not _int or state[3] <= 0 or state[5] not in _disposition_kinds:
            raise _ValueError("billing-event disposition sequence or kind is invalid")
        _sanitised_evidence_reference(state[6])
        _utc(state[7], "recorded_at")
        if _type(state[9]) is not _bool or state[9]:
            raise _ValueError("dispositions cannot authorise entitlement mutation")
        if state[10] != _content_identity("billing-disposition", state[:10]):
            raise _ValueError("billing-event disposition identity is inconsistent")
        return state

    def project_billing_event_disposition_record(value):
        return _tuple(_zip(_disposition_fields, validate_billing_event_disposition_record(value), strict=True))

    def copy_billing_event_disposition_record(value):
        return _issue(_Disposition, validate_billing_event_disposition_record(value))

    event_inbox_contract = _issue(_Contract, _contract_projection)

    return {
        "CONTRACT_VERSION": _contract_version,
        "CATALOGUE_AUTHORITY_VERSION": _catalogue_authority_version,
        "EventInboxContractHandle": _Contract,
        "BillingAccountRecord": _Account,
        "BillingSubscriptionRecord": _Subscription,
        "BillingEventRecord": _Event,
        "BillingEventReceiptRecord": _Receipt,
        "BillingEventDispositionRecord": _Disposition,
        "EVENT_INBOX_CONTRACT": event_inbox_contract,
        "validate_event_inbox_contract": validate_event_inbox_contract,
        "project_event_inbox_contract": project_event_inbox_contract,
        "copy_event_inbox_contract": copy_event_inbox_contract,
        "canonical_owner_id_from_users_id": canonical_owner_id_from_users_id,
        "issue_billing_account_record": issue_billing_account_record,
        "validate_billing_account_record": validate_billing_account_record,
        "project_billing_account_record": project_billing_account_record,
        "copy_billing_account_record": copy_billing_account_record,
        "issue_billing_subscription_record": issue_billing_subscription_record,
        "validate_billing_subscription_record": validate_billing_subscription_record,
        "project_billing_subscription_record": project_billing_subscription_record,
        "copy_billing_subscription_record": copy_billing_subscription_record,
        "issue_structural_billing_event_record": issue_structural_billing_event_record,
        "validate_billing_event_record": validate_billing_event_record,
        "project_billing_event_record": project_billing_event_record,
        "copy_billing_event_record": copy_billing_event_record,
        "classify_event_admission": classify_event_admission,
        "validate_billing_event_receipt_record": validate_billing_event_receipt_record,
        "project_billing_event_receipt_record": project_billing_event_receipt_record,
        "copy_billing_event_receipt_record": copy_billing_event_receipt_record,
        "append_event_disposition": append_event_disposition,
        "validate_billing_event_disposition_record": validate_billing_event_disposition_record,
        "project_billing_event_disposition_record": project_billing_event_disposition_record,
        "copy_billing_event_disposition_record": copy_billing_event_disposition_record,
    }


_kernel = _build_event_inbox_contract()
globals().update(_kernel)

__all__ = tuple(sorted(_kernel))
