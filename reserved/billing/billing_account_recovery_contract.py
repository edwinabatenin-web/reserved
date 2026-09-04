"""Pure W10-S2D owner-bound billing-account recovery decision contract.

The contract evaluates detached, exact built-in facts supplied by future
authenticated and durable adapters.  It performs no authentication, I/O,
persistence, provider call, session creation, entitlement mutation, transfer,
charge, refund or activation.  A positive result is only a short-lived
structural candidate for a future provider-management-session request for an
already owner-bound internal billing account.

Producer issuance protects the returned contract and decision handles from
ordinary same-process forgery.  Public globals, classes and metadata are not
authority; consumers must capture and retain the validation/projector callables.
"""

from __future__ import annotations

import copy as _copy_module
import hashlib as _hashlib_module
import json as _json_module
import re as _re_module
import weakref as _weakref_module
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone


def _build_billing_account_recovery_contract():
    """Build a closure-bound, provider/runtime-neutral recovery kernel."""

    _type = type
    _id = id
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _dict = dict
    _set = set
    _zip = zip
    _len = len
    _all = all
    _str = str
    _int = int
    _bool = bool
    _min = min
    _TypeError = TypeError
    _ValueError = ValueError
    _copy = _copy_module.copy
    _deepcopy = _copy_module.deepcopy
    _sha256 = _hashlib_module.sha256
    _json_dumps = _json_module.dumps
    _compile = _re_module.compile
    _ignore_case = _re_module.IGNORECASE
    _weakref_ref = _weakref_module.ref
    _Datetime = _datetime
    _Timedelta = _timedelta
    _UTC = _timezone.utc

    _contract_version = "reserved-w10-billing-account-recovery-contract/1.0"
    _base_commit = "26944b22dfc4287287827ee7cdabe849e8906531"
    _base_tree = "a072db4cfb9d22a32a9b41525098dbd110dcfeca"
    _decision_purpose = "manage_existing_owner_bound_subscription_billing"
    _maximum_candidate_lifetime_seconds = 300
    _structural_trust = (
        "structural_candidate_not_authentication_not_persistence_not_provider_authority"
    )
    _authorization = "future_provider_management_session_request_candidate_only"
    _denial = "fail_closed_no_management_session_request"

    _provenance = (
        ("candidate_base_commit", _base_commit),
        ("candidate_base_tree", _base_tree),
        (
            "founder_authority",
            ("FD-OA-001", "FD-W10-001", "FD-W10-002", "FD-W10-003"),
        ),
        ("w10_s2a_commit", "5464bfac7bec6b3456d1895b2355a7e8ce86859b"),
        ("w10_s2b_commit", "1033c9fbef008dcd33125a0b14e7fb18b8846d19"),
        ("w10_s2c_commit", "a07348976321df65bbd95c9170c906bcddd5baa5"),
        ("w10_s3a_commit", "94bd87f019dc226ec8c73f32515229189500cf06"),
        ("w10_s3b_commit", "5bc29bcb30c95ea7a5a9430104653b366d709eb6"),
        ("w10_s4a_commit", "2ad4a63dd1f10ba38859050b47245c28390667d8"),
    )
    _scope_exclusions = (
        "authentication_or_identity_recovery",
        "database_repository_schema_or_migration",
        "provider_sdk_network_or_session_creation",
        "credential_configuration_or_customer_data_access",
        "provider_customer_subscription_or_email_lookup",
        "route_redirect_or_return_url_implementation",
        "billing_account_transfer_merge_delegation_or_sharing",
        "manual_entitlement_grant_or_entitlement_mutation",
        "charge_refund_invoice_or_payment_authority",
        "w10_s2_s3_s5_completion_or_launch_activation",
    )
    _unresolved_gates = (
        "authenticated_reserved_owner_adapter",
        "durable_unique_owner_to_billing_account_repository",
        "atomic_mapping_freshness_replay_and_idempotency_compare_and_set",
        "target_identity_recovery_and_session_assurance",
        "security_privacy_support_and_least_privilege_review",
        "redacted_audit_monitoring_incident_and_outage_runbooks",
        "account_email_change_collision_deletion_and_erasure_behavior",
        "fixed_allowlisted_return_target_and_session_ttl_enforcement",
        "provider_sandbox_and_target_negative_evidence",
        "independent_integrated_review_and_separate_activation_authority",
    )

    _identifier_pattern = _compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
    _evidence_pattern = _compile(r"^evidence:[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$")
    _separator_pattern = _compile(r"[._:/-]+")
    _unsafe_pattern = _compile(
        r"(?:^|_)(?:"
        r"(?:sk|rk)_(?:live|test)|whsec|secret|credential|password|passwd|"
        r"bearer|authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"private[_-]?key|secret[_-]?key|client[_-]?secret|webhook[_-]?secret"
        r")(?:_|$)",
        _ignore_case,
    )
    _provider_identifier_pattern = _compile(
        r"^(?:cus|sub|cs|acct|price|prod|pm|in|pi)_[A-Za-z0-9]+$"
    )

    _authentication_fields = (
        "schema_version",
        "owner_user_id",
        "authentication_reference",
        "authenticated_at",
        "authentication_valid_until",
        "trust_status",
    )
    _mapping_fields = (
        "schema_version",
        "owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "mapping_version",
        "mapping_snapshot_id",
        "mapping_evidence_reference",
        "observed_at",
        "fresh_until",
        "mapping_cardinality",
        "mapping_status",
        "trust_status",
    )
    _initiation_fields = (
        "schema_version",
        "request_id",
        "idempotency_key",
        "requested_at",
        "purpose",
    )
    _replay_fields = (
        "schema_version",
        "mapping_snapshot_id",
        "request_id",
        "idempotency_key",
        "checked_at",
        "status",
        "existing_decision_reference",
    )
    _decision_fields = (
        "contract_version",
        "decision_id",
        "authenticated_owner_user_id",
        "canonical_owner_id",
        "billing_account_id",
        "mapping_snapshot_id",
        "mapping_version",
        "request_id",
        "idempotency_key",
        "evaluated_at",
        "decision_not_after",
        "decision",
        "reason",
        "idempotency_disposition",
        "existing_decision_reference",
        "evidence_references",
        "future_management_session_request_candidate_authorized",
        "provider_session_creation_authority",
        "network_authority",
        "entitlement_mutation_allowed",
        "charge_authority",
        "refund_authority",
        "transfer_merge_delegation_authority",
        "manual_entitlement_grant_authority",
        "activation_required_separately",
        "trust_status",
    )
    _decision_input_fields = (
        "authenticated_owner_user_id",
        "authentication_context",
        "mapping_snapshot",
        "initiation",
        "replay_snapshot",
        "evaluated_at",
    )

    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _int, _bool, _Datetime) or value is None:
            return value
        raise _ValueError("recovery contract contains unsupported state")

    def _exact_dict(value, fields, label):
        if _type(value) is not _dict:
            raise _TypeError(f"{label} must be an exact built-in dict")
        keys = _tuple(value.keys())
        if not _all(_type(key) is _str for key in keys):
            raise _TypeError(f"{label} field names must be exact built-in strings")
        if _set(keys) != _set(fields) or _len(keys) != _len(fields):
            raise _ValueError(f"{label} must contain only the exact contract fields")
        return value

    def _exact_literal(value, expected, label):
        if _type(value) is not _str or value != expected:
            raise _ValueError(f"unsupported {label}")
        return value

    def _safe_identifier(value, label):
        if _type(value) is not _str or _identifier_pattern.fullmatch(value) is None:
            raise _ValueError(f"invalid {label}")
        screened = _separator_pattern.sub("_", value)
        if _unsafe_pattern.search(screened) is not None:
            raise _ValueError(f"unsafe credential-shaped {label}")
        return value

    def _internal_billing_account_id(value):
        value = _safe_identifier(value, "billing_account_id")
        if _provider_identifier_pattern.fullmatch(value) is not None:
            raise _ValueError("provider identifier cannot be an internal billing_account_id")
        return value

    def _evidence_reference(value, label):
        if _type(value) is not _str or _evidence_pattern.fullmatch(value) is None:
            raise _ValueError(f"invalid redacted {label}")
        screened = _separator_pattern.sub("_", value)
        if _unsafe_pattern.search(screened) is not None:
            raise _ValueError(f"unsafe credential-shaped {label}")
        return value

    def _utc(value, label):
        if _type(value) is not _Datetime or value.tzinfo is not _UTC:
            raise _ValueError(
                f"{label} must be an exact datetime using timezone.utc"
            )
        return value

    def _owner_id(value, label="owner_user_id"):
        if _type(value) is not _int or value <= 0 or value > 9223372036854775807:
            raise _ValueError(f"{label} must be a positive exact users.id integer")
        return value

    def _positive_version(value, label):
        if _type(value) is not _int or value <= 0:
            raise _ValueError(f"{label} must be a positive exact integer")
        return value

    def _canonical_json(value):
        if _type(value) is _tuple:
            return [_canonical_json(item) for item in value]
        if _type(value) is _Datetime:
            return value.isoformat()
        if _type(value) in (_str, _int, _bool) or value is None:
            return value
        raise _ValueError("unsupported recovery decision identity value")

    def _content_identity(prefix, state):
        encoded = _json_dumps(
            _canonical_json(state),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        return f"{prefix}:sha256-{_sha256(encoded).hexdigest()}"

    class BillingAccountRecoveryContractHandle:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _contract_token:
                raise _TypeError("recovery contract handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_account_recovery_contract(self)

        def __deepcopy__(self, memo):
            return copy_billing_account_recovery_contract(self)

        def __reduce__(self):
            raise _TypeError("recovery contract handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("recovery contract handles are not serialisable")

    class BillingAccountRecoveryDecision:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _decision_token:
                raise _TypeError("recovery decisions are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_billing_account_recovery_decision(self)

        def __deepcopy__(self, memo):
            return copy_billing_account_recovery_decision(self)

        def __reduce__(self):
            raise _TypeError("recovery decisions are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("recovery decisions are not serialisable")

    _Contract = BillingAccountRecoveryContractHandle
    _Decision = BillingAccountRecoveryDecision
    _contract_token = _object()
    _decision_token = _object()
    _registries = {_Contract: {}, _Decision: {}}
    _live_references = {_Contract: {}, _Decision: {}}

    def _issue(cls, state):
        value = _object_new(cls)
        identity = _id(value)

        def _remove_collected(reference, _cls=cls, _identity=identity):
            if _live_references[_cls].get(_identity) is reference:
                _live_references[_cls].pop(_identity, None)
                _registries[_cls].pop(_identity, None)

        reference = _weakref_ref(value, _remove_collected)
        _registries[cls][identity] = _clone(state)
        _live_references[cls][identity] = reference
        return value

    def _validated(value, cls, label):
        if _type(value) is not cls:
            raise _TypeError(f"{label} must be an exact producer-issued handle")
        identity = _id(value)
        reference = _live_references[cls].get(identity)
        if reference is None or reference() is not value or identity not in _registries[cls]:
            raise _ValueError(f"{label} is not producer-issued or is stale")
        return _clone(_registries[cls][identity])

    _contract_projection = (
        ("contract_version", _contract_version),
        ("candidate_base_commit", _base_commit),
        ("candidate_base_tree", _base_tree),
        ("authority_provenance", _provenance),
        ("authenticated_owner_root", "positive_exact_reserved_users.id_only"),
        ("mapping_source", "future_separately_authenticated_durable_repository"),
        ("decision_purpose", _decision_purpose),
        ("positive_scope", _authorization),
        ("maximum_candidate_lifetime_seconds", _maximum_candidate_lifetime_seconds),
        ("runtime_activation", "disabled"),
        ("scope_exclusions", _scope_exclusions),
        ("unresolved_gates", _unresolved_gates),
        ("authentication_fields", _authentication_fields),
        ("mapping_fields", _mapping_fields),
        ("initiation_fields", _initiation_fields),
        ("replay_fields", _replay_fields),
        ("decision_fields", _decision_fields),
        ("assurance_status", "contract_only_not_w10_s2_s3_s5_completion"),
    )

    def validate_billing_account_recovery_contract(value):
        state = _validated(value, _Contract, "billing-account recovery contract")
        if state != _contract_projection:
            raise _ValueError("billing-account recovery contract is inconsistent")
        return state

    def project_billing_account_recovery_contract(value):
        return validate_billing_account_recovery_contract(value)

    def copy_billing_account_recovery_contract(value):
        return _issue(_Contract, validate_billing_account_recovery_contract(value))

    def _authentication(value):
        value = _exact_dict(value, _authentication_fields, "authentication_context")
        _exact_literal(
            value["schema_version"],
            "reserved-authenticated-owner-context/1.0",
            "authentication context schema",
        )
        owner = _owner_id(value["owner_user_id"])
        reference = _evidence_reference(
            value["authentication_reference"], "authentication_reference"
        )
        authenticated_at = _utc(value["authenticated_at"], "authenticated_at")
        valid_until = _utc(
            value["authentication_valid_until"], "authentication_valid_until"
        )
        if valid_until <= authenticated_at:
            raise _ValueError("authentication validity interval is empty")
        _exact_literal(
            value["trust_status"],
            "supplied_by_future_authenticated_reserved_adapter",
            "authentication context trust status",
        )
        return owner, reference, authenticated_at, valid_until

    def _mapping(value):
        if value is None:
            return None
        value = _exact_dict(value, _mapping_fields, "mapping_snapshot")
        _exact_literal(
            value["schema_version"],
            "reserved-owner-billing-mapping/1.0",
            "mapping schema",
        )
        owner = _owner_id(value["owner_user_id"])
        if _type(value["canonical_owner_id"]) is not _str:
            raise _ValueError("canonical_owner_id must be an exact string")
        if value["canonical_owner_id"] != _str(owner):
            raise _ValueError("mapping canonical owner binding is inconsistent")
        account = _internal_billing_account_id(value["billing_account_id"])
        version = _positive_version(value["mapping_version"], "mapping_version")
        snapshot = _safe_identifier(value["mapping_snapshot_id"], "mapping_snapshot_id")
        evidence = _evidence_reference(
            value["mapping_evidence_reference"], "mapping_evidence_reference"
        )
        observed_at = _utc(value["observed_at"], "mapping observed_at")
        fresh_until = _utc(value["fresh_until"], "mapping fresh_until")
        if fresh_until <= observed_at:
            raise _ValueError("mapping freshness interval is empty")
        cardinality = value["mapping_cardinality"]
        if _type(cardinality) is not _str or cardinality not in (
            "exactly_one",
            "none",
            "multiple",
            "conflicting",
        ):
            raise _ValueError("unsupported mapping_cardinality")
        status = value["mapping_status"]
        if _type(status) is not _str or status not in (
            "active",
            "stale",
            "conflicting",
            "deleted",
        ):
            raise _ValueError("unsupported mapping_status")
        _exact_literal(
            value["trust_status"],
            "supplied_by_future_authenticated_durable_repository",
            "mapping trust status",
        )
        return (
            owner,
            account,
            version,
            snapshot,
            evidence,
            observed_at,
            fresh_until,
            cardinality,
            status,
        )

    def _initiation(value):
        value = _exact_dict(value, _initiation_fields, "initiation")
        _exact_literal(
            value["schema_version"],
            "reserved-billing-recovery-initiation/1.0",
            "initiation schema",
        )
        request_id = _safe_identifier(value["request_id"], "request_id")
        idempotency_key = _safe_identifier(value["idempotency_key"], "idempotency_key")
        requested_at = _utc(value["requested_at"], "requested_at")
        _exact_literal(value["purpose"], _decision_purpose, "recovery purpose")
        return request_id, idempotency_key, requested_at

    def _replay(value):
        value = _exact_dict(value, _replay_fields, "replay_snapshot")
        _exact_literal(
            value["schema_version"],
            "reserved-billing-recovery-replay/1.0",
            "replay schema",
        )
        mapping_snapshot = _safe_identifier(
            value["mapping_snapshot_id"], "replay mapping_snapshot_id"
        )
        request_id = _safe_identifier(value["request_id"], "replay request_id")
        idempotency_key = _safe_identifier(
            value["idempotency_key"], "replay idempotency_key"
        )
        checked_at = _utc(value["checked_at"], "replay checked_at")
        status = value["status"]
        if _type(status) is not _str or status not in (
            "unused_for_request",
            "exact_request_replay",
            "mapping_replayed_for_other_request",
            "idempotency_conflict",
        ):
            raise _ValueError("unsupported replay status")
        existing = value["existing_decision_reference"]
        if status == "unused_for_request":
            if existing is not None:
                raise _ValueError("unused replay state cannot name an existing decision")
        else:
            existing = _safe_identifier(existing, "existing_decision_reference")
        return mapping_snapshot, request_id, idempotency_key, checked_at, status, existing

    def _decision_state(
        *, owner, mapping, request, evaluated_at, decision, reason,
        idempotency_disposition, existing_decision_reference, evidence_references,
        authorized, not_after,
    ):
        # A denial must not echo an ambiguous or cross-owner account selection.
        # Only a positively owner-bound candidate carries the internal mapping.
        mapping_account = mapping[1] if authorized and mapping is not None else None
        mapping_snapshot = mapping[3] if authorized and mapping is not None else None
        mapping_version = mapping[2] if authorized and mapping is not None else None
        prefix = (
            _contract_version,
            owner,
            _str(owner),
            mapping_account,
            mapping_snapshot,
            mapping_version,
            request[0],
            request[1],
            evaluated_at,
            not_after,
            decision,
            reason,
            idempotency_disposition,
            existing_decision_reference,
            evidence_references,
            authorized,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            _structural_trust,
        )
        identity = _content_identity("recovery-decision", prefix)
        return prefix[:1] + (identity,) + prefix[1:]

    def decide_billing_account_recovery(*args, **kwargs):
        if args:
            raise _TypeError(
                "billing-account recovery inputs must be supplied by exact keyword"
            )
        inputs = _exact_dict(
            kwargs,
            _decision_input_fields,
            "billing-account recovery inputs",
        )
        authenticated_owner_user_id = inputs["authenticated_owner_user_id"]
        authentication_context = inputs["authentication_context"]
        mapping_snapshot = inputs["mapping_snapshot"]
        initiation = inputs["initiation"]
        replay_snapshot = inputs["replay_snapshot"]
        evaluated_at = inputs["evaluated_at"]

        owner = _owner_id(authenticated_owner_user_id, "authenticated_owner_user_id")
        authentication = _authentication(authentication_context)
        mapping = _mapping(mapping_snapshot)
        request = _initiation(initiation)
        replay = _replay(replay_snapshot)
        evaluated = _utc(evaluated_at, "evaluated_at")

        evidence = ()
        authentication_matches_owner = authentication[0] == owner
        if authentication_matches_owner:
            evidence = (authentication[1],)
        if (
            authentication_matches_owner
            and mapping is not None
            and mapping[0] == owner
        ):
            evidence = evidence + (mapping[4],)

        decision = _denial
        reason = "mapping_missing"
        disposition = "no_new_request"
        existing_decision_reference = None
        authorized = False
        not_after = None

        if authentication[0] != owner:
            reason = "authenticated_owner_context_conflict"
        elif request[2] > evaluated:
            reason = "request_from_future"
        elif authentication[2] > request[2]:
            reason = "request_predates_authentication"
        elif authentication[3] <= evaluated:
            reason = "authentication_stale_at_evaluation"
        elif mapping is None:
            reason = "mapping_missing"
        elif mapping[0] != owner:
            reason = "cross_owner_mapping_rejected"
        elif mapping[7] != "exactly_one":
            reason = "mapping_ambiguous_or_missing"
        elif mapping[8] != "active":
            reason = "mapping_not_active"
        elif mapping[5] > evaluated:
            reason = "mapping_observation_from_future"
        elif mapping[6] <= evaluated:
            reason = "mapping_stale_at_evaluation"
        elif replay[3] != evaluated:
            reason = "replay_check_not_atomic_with_evaluation"
        elif replay[0] != mapping[3]:
            reason = "replay_mapping_snapshot_conflict"
        elif replay[1] != request[0] or replay[2] != request[1]:
            reason = "replay_request_identity_conflict"
        elif replay[4] == "exact_request_replay":
            reason = "exact_replay_no_new_request"
            disposition = "return_existing_decision_reference_only"
            existing_decision_reference = replay[5]
        elif replay[4] == "mapping_replayed_for_other_request":
            reason = "mapping_replayed_for_other_request"
        elif replay[4] == "idempotency_conflict":
            reason = "idempotency_conflict"
        elif replay[4] != "unused_for_request":
            reason = "unknown_replay_state"
        else:
            decision = _authorization
            reason = "exact_owner_bound_mapping_and_atomic_unused_replay_state"
            disposition = "new_deterministic_request_candidate"
            authorized = True
            not_after = _min(
                authentication[3],
                mapping[6],
                evaluated + _Timedelta(seconds=_maximum_candidate_lifetime_seconds),
            )

        state = _decision_state(
            owner=owner,
            mapping=mapping,
            request=request,
            evaluated_at=evaluated,
            decision=decision,
            reason=reason,
            idempotency_disposition=disposition,
            existing_decision_reference=existing_decision_reference,
            evidence_references=evidence,
            authorized=authorized,
            not_after=not_after,
        )
        return _issue(_Decision, state)

    def validate_billing_account_recovery_decision(value):
        state = _validated(value, _Decision, "billing-account recovery decision")
        if _len(state) != _len(_decision_fields) or state[0] != _contract_version:
            raise _ValueError("billing-account recovery decision shape is inconsistent")
        expected_identity = _content_identity("recovery-decision", state[:1] + state[2:])
        if state[1] != expected_identity:
            raise _ValueError("billing-account recovery decision identity is inconsistent")
        if state[2] != _owner_id(state[2], "authenticated_owner_user_id"):
            raise _ValueError("decision owner is inconsistent")
        if state[3] != _str(state[2]):
            raise _ValueError("decision canonical owner is inconsistent")
        if state[11] not in (_authorization, _denial):
            raise _ValueError("decision outcome is inconsistent")
        if state[16] is not (state[11] == _authorization):
            raise _ValueError("decision authorization flag is inconsistent")
        if state[17:24] != (False, False, False, False, False, False, False):
            raise _ValueError("decision exceeds recovery authority")
        if state[24] is not True or state[25] != _structural_trust:
            raise _ValueError("decision activation/trust boundary is inconsistent")
        if state[16] and state[10] is None:
            raise _ValueError("authorized candidate requires an expiry boundary")
        if not state[16] and state[10] is not None:
            raise _ValueError("denied candidate must not carry an expiry boundary")
        return state

    def project_billing_account_recovery_decision(value):
        return _tuple(
            _zip(
                _decision_fields,
                validate_billing_account_recovery_decision(value),
                strict=True,
            )
        )

    def copy_billing_account_recovery_decision(value):
        return _issue(
            _Decision,
            validate_billing_account_recovery_decision(value),
        )

    contract = _issue(_Contract, _contract_projection)
    validate_billing_account_recovery_contract(_copy(contract))
    validate_billing_account_recovery_contract(_deepcopy(contract))

    return {
        "CONTRACT_VERSION": _contract_version,
        "BillingAccountRecoveryContractHandle": BillingAccountRecoveryContractHandle,
        "BillingAccountRecoveryDecision": BillingAccountRecoveryDecision,
        "BILLING_ACCOUNT_RECOVERY_CONTRACT": contract,
        "validate_billing_account_recovery_contract": validate_billing_account_recovery_contract,
        "project_billing_account_recovery_contract": project_billing_account_recovery_contract,
        "copy_billing_account_recovery_contract": copy_billing_account_recovery_contract,
        "decide_billing_account_recovery": decide_billing_account_recovery,
        "validate_billing_account_recovery_decision": validate_billing_account_recovery_decision,
        "project_billing_account_recovery_decision": project_billing_account_recovery_decision,
        "copy_billing_account_recovery_decision": copy_billing_account_recovery_decision,
    }


_kernel = _build_billing_account_recovery_contract()
globals().update(_kernel)
__all__ = tuple(sorted(_kernel))

BillingAccountRecoveryContractHandle.__module__ = __name__
BillingAccountRecoveryContractHandle.__qualname__ = (
    BillingAccountRecoveryContractHandle.__name__
)
BillingAccountRecoveryDecision.__module__ = __name__
BillingAccountRecoveryDecision.__qualname__ = BillingAccountRecoveryDecision.__name__

del _kernel
