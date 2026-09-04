"""Pure disabled-first W10-S4C Customer Portal request-candidate contract.

This module authenticates nobody and performs no I/O.  It converts exact,
detached facts about one current owner-to-billing-account mapping into a
short-lived structural candidate.  The candidate is not a Stripe Customer
Portal Session request and grants no provider, refund, policy, or entitlement
authority.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re as _re
from datetime import datetime as _Datetime
from datetime import timedelta as _Timedelta
from datetime import timezone as _timezone


def _build():
    T, D, S, I, B = tuple, dict, str, int, bool
    typ, length, all_, any_, set_ = type, len, all, any, set
    TE, VE = TypeError, ValueError
    UTC = _timezone.utc
    sha256, dumps = _hashlib.sha256, _json.dumps
    identifier = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$").fullmatch
    digest = _re.compile(r"^sha256:[0-9a-f]{64}$").fullmatch
    provider_identifier = _re.compile(
        r"^(?:cus|sub|cs|acct|price|prod|pm|in|pi|si|seti|src|ch|evt|re|dp|tr|po|ba|txn|li|ii|il|txr|clock|sched|bpc)_[A-Za-z0-9]+$"
    ).fullmatch
    embedded_provider_identifier = _re.compile(
        r"(?:^|_)(?:cus|sub|cs|acct|price|prod|pm|in|pi|si|seti|src|ch|evt|re|dp|tr|po|ba|txn|li|ii|il|txr|clock|sched|bpc)_[a-z0-9]+(?:_|$)"
    ).search
    separator = _re.compile(r"[._:/-]+").sub

    version = "reserved-w10-portal-intent-contract/1.0"
    base_commit = "5f5a948891e1e812a5c74ff6c7266d153bb492fa"
    base_tree = "639369d06a8da75e8318bec7933993c26e39ace6"
    schema = "reserved-portal-request-candidate/1.0"
    auth_schema = "reserved-authenticated-owner-context/1.0"
    mapping_schema = "reserved-owner-billing-mapping/1.0"
    replay_schema = "reserved-portal-intent-replay-snapshot/1.0"
    auth_trust = "supplied_by_future_authenticated_reserved_adapter"
    mapping_trust = "supplied_by_future_authenticated_durable_repository"
    purpose = "manage_existing_owner_bound_subscription_billing"
    destination = "reserved_billing_portal_return_reconciliation"
    status = "structural_candidate_not_authenticated_persisted_provider_or_portal_admitted"
    max_lifetime = _Timedelta(minutes=5)
    source_bindings = (
        ("founder_authority", "FOUNDER_DECISIONS.md", "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4", "FD-W10-002+FD-W10-003"),
        ("owner_mapping_recovery", "reserved/billing/billing_account_recovery_contract.py", "b3bfc4501bdb3631bd87c9dc4aea0984b899fdd3afb535f1414cedd721f4ae06", "509c5360d453e23a0732e4e9d4637385eef20ef6"),
        ("disabled_stripe_edge", "reserved/billing/stripe_disabled_first_contract.py", "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638", "2ad4a63dd1f10ba38859050b47245c28390667d8"),
        ("checkout_separation", "reserved/billing/checkout_intent_contract.py", "ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0", "23f4d3dc742474d3a672388a1ebe99962505b234"),
        ("entitlement_separation", "reserved/billing/entitlement_core.py", "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b", "94bd87f019dc226ec8c73f32515229189500cf06"),
    )
    lifecycle = (
        ("canonical_recovery_state", "payment_recovery"),
        ("recovery_period_calendar_days", 7),
        ("recovery_deadline_extendable_by_portal", False),
        ("portal_return_changes_entitlement", False),
        ("provider_status_changes_entitlement_directly", False),
    )
    flags = (
        ("authentication_authority", False),
        ("mapping_persistence_or_selection_authority", False),
        ("intent_persistence_authority", False),
        ("intent_single_use_consumed", False),
        ("stripe_sdk_or_network_authority", False),
        ("stripe_credential_authority", False),
        ("portal_session_creation_authority", False),
        ("route_or_browser_return_authority", False),
        ("charge_authority", False),
        ("refund_or_policy_authority", False),
        ("entitlement_grant_or_mutation_authority", False),
        ("recovery_execution_authority", False),
        ("sandbox_activation_authority", False),
        ("production_activation_authority", False),
    )
    gates = (
        "real_authenticated_reserved_owner_adapter",
        "durable_unique_owner_to_billing_account_repository",
        "atomic_single_use_intent_consume_and_mapping_freshness",
        "approved_stripe_customer_mapping_and_portal_configuration",
        "approved_credentials_custody_and_runtime_secret_injection",
        "reviewed_fixed_https_return_resolution_and_csrf_session_integrity",
        "provider_sandbox_negative_replay_failure_and_reconciliation_evidence",
        "target_security_privacy_support_finance_tax_and_accessibility_evidence",
        "separate_founder_provider_production_release_and_go_live_authority",
    )
    auth_fields = ("schema_version", "owner_user_id", "authentication_reference", "authenticated_at", "authentication_valid_until", "trust_status")
    mapping_fields = ("schema_version", "owner_user_id", "canonical_owner_id", "billing_account_id", "mapping_version", "mapping_snapshot_id", "mapping_evidence_reference", "observed_at", "fresh_until", "mapping_cardinality", "mapping_status", "trust_status")
    replay_fields = ("schema_version", "owner_user_id", "billing_account_id", "mapping_snapshot_id", "intent_id", "idempotency_key_digest", "state", "checked_at", "existing_candidate_identity")
    create_fields = ("authentication_context", "owner_user_id", "mapping_snapshot", "provider_customer_observation_reference", "provider_email_observation_reference", "purpose", "intent_id", "idempotency_key", "requested_at", "evaluated_at", "valid_until", "return_destination_id", "replay_snapshot", "evidence_reference")
    candidate_fields = ("schema_version", "candidate_status", "candidate_identity", "authenticated_owner_user_id", "owner_reference", "authentication_reference", "authentication_runtime_verified", "billing_account_id", "mapping_version", "mapping_snapshot_id", "mapping_evidence_reference", "provider_customer_observation_reference", "provider_email_observation_reference", "provider_observations_are_authentication", "purpose", "intent_id", "idempotency_key_digest", "requested_at", "evaluated_at", "valid_until", "return_destination_id", "replay_guard_status", "lifecycle_boundary", "authority_flags", "activation_gates", "evidence_reference")
    secret_markers = ("secret", "credential", "password", "passwd", "bearer", "authorization", "api_key", "access_token", "refresh_token", "private_key", "client_secret", "endpoint_secret", "webhook_secret", "sk_live", "sk_test", "rk_live", "rk_test", "whsec")

    def clone(value):
        if typ(value) is T:
            return T(clone(item) for item in value)
        if typ(value) in (S, I, B) or value is None:
            return value
        raise VE("portal contract contains a non-exact primitive")

    def call(args, kwargs, positional, fields, label):
        if typ(args) is not T or length(args) != positional:
            raise TE(f"{label} requires exactly {positional} positional input(s)")
        if typ(kwargs) is not D or not all_(typ(k) is S for k in kwargs):
            raise TE(f"{label} named facts must be an exact dict of exact strings")
        if length(kwargs) != length(fields) or set_(kwargs) != set_(fields):
            unexpected = T(k for k in kwargs if k not in fields)
            if unexpected:
                raise TE(f"{label} received unsupported fact {unexpected[0]}")
            raise TE(f"{label} requires the exact complete named fact set")
        return args, T(kwargs[name] for name in fields)

    def mapping(value, fields, label):
        if typ(value) is not D or length(value) != length(fields) or not all_(typ(k) is S for k in value) or set_(value) != set_(fields):
            raise TE(f"{label} must be an exact complete dict")
        return T(value[name] for name in fields)

    def owner(value, label):
        if typ(value) is not I or typ(value) is B or value <= 0 or value > 9223372036854775807:
            raise VE(f"{label} must be an exact positive users.id integer")
        return value

    def safe(value, label, prefix=None):
        if typ(value) is not S or identifier(value) is None:
            raise VE(f"{label} must be a bounded exact identifier")
        screened = "_" + separator("_", value.casefold()) + "_"
        if any_(f"_{marker}_" in screened for marker in secret_markers):
            raise VE(f"{label} must not contain secret-shaped material")
        if prefix is not None and not value.startswith(prefix):
            raise VE(f"{label} must use the required namespace")
        return value

    def evidence(value, label):
        return safe(value, label, "evidence:")

    def provider_evidence(value, label):
        value = evidence(value, label)
        normalised = separator("_", value.casefold())
        if embedded_provider_identifier(normalised) is not None:
            raise VE(f"{label} must be opaque and must not embed a provider object identifier")
        return value

    def internal_account(value, label="billing_account_id"):
        value = safe(value, label)
        if provider_identifier(value) is not None:
            raise VE("provider identifier cannot be an internal billing account")
        return value

    def utc(value, label):
        if typ(value) is not _Datetime or value.tzinfo is not UTC:
            raise TE(f"{label} must be an exact datetime using timezone.utc")
        return value

    def timestamp(value):
        return f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:{value.minute:02d}:{value.second:02d}.{value.microsecond:06d}Z"

    def parse_timestamp(value, label):
        if typ(value) is not S:
            raise TE(f"{label} must be an exact string")
        try:
            parsed = _Datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        except ValueError as exc:
            raise VE(f"{label} must be a canonical UTC timestamp") from exc
        if timestamp(parsed) != value:
            raise VE(f"{label} must be a canonical UTC timestamp")
        return parsed

    def key_digest(value):
        value = safe(value, "idempotency_key", "portal_idempotency:")
        return "sha256:" + sha256(value.encode("ascii")).hexdigest()

    def identity(state):
        return "portal-intent:sha256-" + sha256(dumps(state, ensure_ascii=True, separators=(",", ":")).encode("ascii")).hexdigest()

    def project_portal_intent_contract(*args, **kwargs):
        call(args, kwargs, 0, (), "contract projection")
        return clone((("contract_version", version), ("candidate_base_commit", base_commit), ("candidate_base_tree", base_tree), ("candidate_schema", schema), ("source_bindings", source_bindings), ("purpose", purpose), ("return_destination_allowlist", (destination,)), ("maximum_candidate_lifetime_seconds", 300), ("lifecycle_boundary", lifecycle), ("authority_flags", flags), ("activation_gates", gates), ("assurance_status", "contract_only_not_portal_provider_entitlement_s4_or_launch_assurance")))

    def create_portal_request_candidate(*args, **kwargs):
        positional, facts = call(args, kwargs, 1, create_fields, "portal candidate creation")
        root = owner(positional[0], "authenticated_owner_user_id")
        auth, named_owner, mapped, provider_customer_ref, provider_email_ref, requested_purpose, intent_id, raw_key, requested_at, evaluated_at, valid_until, return_id, replay, evidence_ref = facts
        if owner(named_owner, "owner_user_id") != root:
            raise VE("owner does not match authenticated owner root")
        av = mapping(auth, auth_fields, "authentication_context")
        if typ(av[0]) is not S or av[0] != auth_schema or owner(av[1], "authentication owner") != root or typ(av[5]) is not S or av[5] != auth_trust:
            raise VE("authentication context is not the exact structural shape")
        auth_ref = evidence(av[2], "authentication_reference")
        auth_at, auth_until = utc(av[3], "authenticated_at"), utc(av[4], "authentication_valid_until")
        mv = mapping(mapped, mapping_fields, "mapping_snapshot")
        if typ(mv[0]) is not S or mv[0] != mapping_schema or owner(mv[1], "mapping owner") != root or typ(mv[2]) is not S or mv[2] != S(root):
            raise VE("mapping is not bound to the authenticated owner")
        account = internal_account(mv[3])
        if typ(mv[4]) is not I or typ(mv[4]) is B or mv[4] <= 0:
            raise VE("mapping_version must be an exact positive integer")
        snapshot = safe(mv[5], "mapping_snapshot_id")
        mapping_ref = evidence(mv[6], "mapping_evidence_reference")
        customer_ref = provider_evidence(provider_customer_ref, "provider_customer_observation_reference")
        email_ref = provider_evidence(provider_email_ref, "provider_email_observation_reference")
        observed, fresh = utc(mv[7], "mapping observed_at"), utc(mv[8], "mapping fresh_until")
        if typ(mv[9]) is not S or mv[9] != "exactly_one" or typ(mv[10]) is not S or mv[10] != "active" or typ(mv[11]) is not S or mv[11] != mapping_trust:
            raise VE("mapping is missing, ambiguous, conflicting, stale or untrusted")
        if typ(requested_purpose) is not S or requested_purpose != purpose:
            raise VE("portal purpose is unsupported")
        intent_id = safe(intent_id, "intent_id", "portal_intent:")
        digest_value = key_digest(raw_key)
        requested, evaluated, expires = utc(requested_at, "requested_at"), utc(evaluated_at, "evaluated_at"), utc(valid_until, "valid_until")
        if not auth_at <= requested <= evaluated or evaluated - requested > max_lifetime or not observed <= evaluated < fresh:
            raise VE("authentication, request, evaluation or mapping freshness is invalid")
        if not evaluated < expires <= evaluated + max_lifetime or expires > auth_until or expires > fresh:
            raise VE("portal candidate is stale or exceeds an authority boundary")
        if typ(return_id) is not S or return_id != destination:
            raise VE("return destination is not in the fixed allowlist")
        rv = mapping(replay, replay_fields, "replay_snapshot")
        if typ(rv[0]) is not S or rv[0] != replay_schema or owner(rv[1], "replay owner") != root or internal_account(rv[2], "replay billing account") != account or safe(rv[3], "replay mapping snapshot") != snapshot or safe(rv[4], "replay intent", "portal_intent:") != intent_id or typ(rv[5]) is not S or digest(rv[5]) is None or rv[5] != digest_value or typ(rv[6]) is not S or rv[6] != "unused" or utc(rv[7], "replay checked_at") != evaluated or rv[8] is not None:
            raise VE("portal intent is replayed, cross-owner, stale, ambiguous or conflicting")
        state = (("schema_version", schema), ("candidate_status", status), ("authenticated_owner_user_id", root), ("owner_reference", f"users:{root}"), ("authentication_reference", auth_ref), ("authentication_runtime_verified", False), ("billing_account_id", account), ("mapping_version", mv[4]), ("mapping_snapshot_id", snapshot), ("mapping_evidence_reference", mapping_ref), ("provider_customer_observation_reference", customer_ref), ("provider_email_observation_reference", email_ref), ("provider_observations_are_authentication", False), ("purpose", purpose), ("intent_id", intent_id), ("idempotency_key_digest", digest_value), ("requested_at", timestamp(requested)), ("evaluated_at", timestamp(evaluated)), ("valid_until", timestamp(expires)), ("return_destination_id", destination), ("replay_guard_status", "future_atomic_consume_required"), ("lifecycle_boundary", lifecycle), ("authority_flags", flags), ("activation_gates", gates), ("evidence_reference", evidence(evidence_ref, "evidence_reference")))
        candidate_id = identity(state)
        return clone((state[0], state[1], ("candidate_identity", candidate_id), *state[2:]))

    def validate_portal_request_candidate(*args, **kwargs):
        positional, _ = call(args, kwargs, 1, (), "portal candidate validation")
        value = positional[0]
        if typ(value) is not T or length(value) != length(candidate_fields) or not all_(typ(x) is T and length(x) == 2 for x in value) or T(x[0] for x in value) != candidate_fields:
            raise VE("portal candidate must be the exact complete ordered tuple")
        view = D(value)
        exact_strings = (("schema_version", schema), ("candidate_status", status), ("owner_reference", f"users:{owner(view['authenticated_owner_user_id'], 'candidate owner')}"), ("purpose", purpose), ("return_destination_id", destination), ("replay_guard_status", "future_atomic_consume_required"))
        if any_(typ(view[k]) is not S or view[k] != expected for k, expected in exact_strings):
            raise VE("portal candidate fixed facts changed")
        evidence(view["authentication_reference"], "authentication_reference")
        internal_account(view["billing_account_id"])
        if typ(view["mapping_version"]) is not I or typ(view["mapping_version"]) is B or view["mapping_version"] <= 0:
            raise VE("candidate mapping version is invalid")
        safe(view["mapping_snapshot_id"], "mapping_snapshot_id")
        evidence(view["mapping_evidence_reference"], "mapping_evidence_reference")
        provider_evidence(view["provider_customer_observation_reference"], "provider_customer_observation_reference")
        provider_evidence(view["provider_email_observation_reference"], "provider_email_observation_reference")
        evidence(view["evidence_reference"], "evidence_reference")
        if view["authentication_runtime_verified"] is not False or view["provider_observations_are_authentication"] is not False:
            raise VE("candidate asserted authentication authority")
        safe(view["intent_id"], "intent_id", "portal_intent:")
        if typ(view["idempotency_key_digest"]) is not S or digest(view["idempotency_key_digest"]) is None:
            raise VE("candidate idempotency digest is invalid")
        requested, evaluated, expires = (parse_timestamp(view[name], name) for name in ("requested_at", "evaluated_at", "valid_until"))
        if (
            not requested <= evaluated < expires
            or evaluated - requested > max_lifetime
            or expires > evaluated + max_lifetime
        ):
            raise VE("candidate time boundary is invalid")
        if view["lifecycle_boundary"] != lifecycle or view["authority_flags"] != flags or view["activation_gates"] != gates:
            raise VE("candidate fixed safety boundary changed")
        if any_(typ(flag) is not B or flag is not False for _, flag in view["authority_flags"]):
            raise VE("candidate authority flags must remain false")
        without = T(item for item in value if item[0] != "candidate_identity")
        if typ(view["candidate_identity"]) is not S or view["candidate_identity"] != identity(without):
            raise VE("candidate identity does not match exact content")
        return clone(value)

    return version, project_portal_intent_contract, create_portal_request_candidate, validate_portal_request_candidate


CONTRACT_VERSION, project_portal_intent_contract, create_portal_request_candidate, validate_portal_request_candidate = _build()

__all__ = ("CONTRACT_VERSION", "project_portal_intent_contract", "create_portal_request_candidate", "validate_portal_request_candidate")
