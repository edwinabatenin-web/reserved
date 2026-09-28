"""Pure disabled-first W10-S4B Checkout request-candidate contract.

This module does not authenticate a user, call Stripe, create a Checkout
Session, persist or consume an intent, charge money, or grant entitlement.  It
accepts only detached exact primitive facts, rederives the settled catalogue
values locally, and returns an immutable structural candidate whose every
runtime/provider/entitlement authority flag is false.

There is deliberately no producer-handle registry.  A structurally valid
projection is never admission or action authority; a future authenticated,
durable, atomic adapter must revalidate and consume it before constructing its
own provider request.
"""

from __future__ import annotations

import hashlib as _hashlib_module
import json as _json_module
import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timedelta as _timedelta_type
from datetime import timezone as _timezone_type


def _build_checkout_intent_contract():
    _type = type
    _tuple = tuple
    _dict = dict
    _set = set
    _len = len
    _str = str
    _int = int
    _bool = bool
    _all = all
    _any = any
    _TypeError = TypeError
    _ValueError = ValueError
    _Datetime = _datetime_type
    _Timedelta = _timedelta_type
    _UTC = _timezone_type.utc
    _sha256 = _hashlib_module.sha256
    _json_dumps = _json_module.dumps
    _identifier = _re_module.compile(
        r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$"
    ).fullmatch
    _digest = _re_module.compile(r"^sha256:[0-9a-f]{64}$").fullmatch
    _separator = _re_module.compile(r"[._:/-]+").sub

    _contract_version = "reserved-w10-checkout-intent-contract/1.0"
    _candidate_base_commit = "1d91526d11b5291d5388c78940682ca02edeb61e"
    _candidate_base_tree = "e2fc725961f816d80eed9e5373d738e5e21a024c"
    _catalogue_authority_version = "FD-W10-001/2026-09-02/v1"
    _candidate_schema = "reserved-checkout-request-candidate/1.0"
    _authentication_schema = "reserved-authenticated-owner-context/1.0"
    _replay_schema = "reserved-checkout-intent-replay-snapshot/1.0"
    _authentication_trust = (
        "future_authenticated_reserved_owner_adapter_structural_input_only"
    )
    _candidate_status = (
        "structural_candidate_not_authenticated_persisted_provider_or_entitlement_admitted"
    )
    _return_destination = "reserved_billing_return_reconciliation"
    _gross_price_statement = "inclusive_of_vat_where_applicable"
    _max_lifetime = _Timedelta(minutes=5)

    _catalogue = (
        ("monthly", 2900, "GBP", "month", 1),
        ("six_month", 15600, "GBP", "month", 6),
        ("yearly", 28800, "GBP", "year", 1),
    )
    _source_bindings = (
        (
            "founder_authority",
            "FOUNDER_DECISIONS.md",
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
            "FD-W10-001+FD-W10-002+FD-W10-003",
        ),
        (
            "catalogue_authority",
            "reserved/billing/contracts.py",
            "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
            "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
        ),
        (
            "entitlement_transition_contract",
            "reserved/billing/entitlement_core.py",
            "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
            "94bd87f019dc226ec8c73f32515229189500cf06",
        ),
        (
            "event_inbox_contract",
            "reserved/billing/event_inbox_contract.py",
            "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
            "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
        ),
        (
            "disabled_stripe_edge",
            "reserved/billing/stripe_disabled_first_contract.py",
            "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
            "2ad4a63dd1f10ba38859050b47245c28390667d8",
        ),
        (
            "authenticated_plan_quote_evidence",
            "docs/W10_S6C_AUTHENTICATED_PLAN_QUOTE_EVIDENCE.md",
            "c424c0ca999ef18568dfc1b86f79d9f0e27af1d05e7f9167ef9de43b344b3bb1",
            "3e05fb7f3149ee7030be768909eb6fe4f50e0b75",
        ),
        (
            "plan_selection_preview_evidence",
            "docs/W10_S6D_PLAN_SELECTION_PREVIEW_EVIDENCE.md",
            "d7306da9e1e163420e345567800c6789d8422619ceaf9b91d925458d0a136790",
            "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
        ),
    )
    _lifecycle_boundary = (
        ("canonical_recovery_state", "payment_recovery"),
        ("recovery_period_calendar_days", 7),
        ("initial_checkout_starts_access", False),
        ("browser_return_starts_access", False),
        ("provider_status_copied_into_reserved_state", False),
        (
            "future_entitlement_source",
            "verified_idempotent_order_safe_owner_bound_provider_observations_only",
        ),
    )
    _authority_flags = (
        ("authentication_authority", False),
        ("intent_persistence_authority", False),
        ("intent_single_use_consumed", False),
        ("stripe_sdk_or_network_authority", False),
        ("stripe_credential_authority", False),
        ("checkout_session_creation_authority", False),
        ("charge_authority", False),
        ("browser_return_payment_authority", False),
        ("provider_status_entitlement_authority", False),
        ("entitlement_grant_or_mutation_authority", False),
        ("sandbox_activation_authority", False),
        ("production_activation_authority", False),
    )
    _activation_gates = (
        "real_authenticated_reserved_owner_adapter",
        "durable_owner_bound_single_use_intent_repository_and_atomic_consume",
        "approved_provider_price_product_and_account_configuration",
        "approved_credentials_custody_rotation_and_runtime_secret_injection",
        "reviewed_fixed_https_return_url_resolution_and_csrf_session_integrity",
        "provider_sandbox_negative_replay_failure_and_reconciliation_evidence",
        "verified_webhook_event_inbox_and_entitlement_reconciliation",
        "target_security_privacy_finance_tax_operations_and_accessibility_evidence",
        "separate_founder_provider_production_release_and_go_live_authority",
    )
    _create_fields = (
        "authentication_context",
        "owner_user_id",
        "catalogue_authority_version",
        "plan_key",
        "intent_id",
        "idempotency_key",
        "requested_at",
        "evaluated_at",
        "valid_until",
        "return_destination_id",
        "replay_snapshot",
        "evidence_reference",
    )
    _authentication_fields = (
        "schema_version",
        "owner_user_id",
        "authentication_reference",
        "authenticated_at",
        "authentication_valid_until",
        "trust_status",
    )
    _replay_fields = (
        "schema_version",
        "owner_user_id",
        "intent_id",
        "idempotency_key_digest",
        "state",
        "checked_at",
        "existing_candidate_identity",
    )
    _candidate_fields = (
        "schema_version",
        "candidate_status",
        "candidate_identity",
        "authenticated_owner_user_id",
        "owner_reference",
        "authentication_reference",
        "authentication_runtime_verified",
        "catalogue_authority_version",
        "plan_key",
        "unit_amount_minor",
        "currency",
        "recurring_interval",
        "recurring_interval_count",
        "checkout_mode",
        "quantity",
        "gross_price_statement",
        "intent_id",
        "idempotency_key_digest",
        "requested_at",
        "evaluated_at",
        "valid_until",
        "return_destination_id",
        "replay_guard_status",
        "lifecycle_boundary",
        "authority_flags",
        "activation_gates",
        "evidence_reference",
    )
    _secret_markers = (
        "secret",
        "credential",
        "password",
        "passwd",
        "bearer",
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "private_key",
        "client_secret",
        "endpoint_secret",
        "webhook_secret",
        "sk_live",
        "sk_test",
        "rk_live",
        "rk_test",
        "whsec",
    )

    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _int, _bool) or value is None:
            return value
        raise _ValueError("contract projection contains a non-primitive value")

    def _exact_call(args, kwargs, positional_count, named_fields, context):
        if _type(args) is not _tuple or _len(args) != positional_count:
            raise _TypeError(
                f"{context} requires exactly {positional_count} positional input(s)"
            )
        if _type(kwargs) is not _dict:
            raise _TypeError(f"{context} named facts must be an exact dict")
        keys = _tuple(kwargs.keys())
        if not _all(_type(key) is _str for key in keys):
            raise _TypeError(f"{context} names must be exact strings")
        supplied = _set(keys)
        expected = _set(named_fields)
        unexpected = _tuple(key for key in keys if key not in expected)
        if unexpected:
            raise _TypeError(f"{context} received unsupported fact {unexpected[0]}")
        if _len(keys) != _len(named_fields) or supplied != expected:
            raise _TypeError(f"{context} requires the exact complete named fact set")
        return args, _tuple(kwargs[field] for field in named_fields)

    def _exact_mapping(value, fields, context):
        if _type(value) is not _dict:
            raise _TypeError(f"{context} must be an exact dict")
        keys = _tuple(value.keys())
        if (
            not _all(_type(key) is _str for key in keys)
            or _len(keys) != _len(fields)
            or _set(keys) != _set(fields)
        ):
            raise _ValueError(f"{context} must contain only the exact fields")
        return _tuple(value[field] for field in fields)

    def _owner(value, label):
        if _type(value) is not _int or _type(value) is _bool:
            raise _TypeError(f"{label} must be an exact positive users.id integer")
        if value <= 0 or value > 9223372036854775807:
            raise _ValueError(f"{label} must be a positive users.id integer")
        return value

    def _safe_identifier(value, label, prefix=None):
        if _type(value) is not _str:
            raise _TypeError(f"{label} must be an exact string")
        if _identifier(value) is None:
            raise _ValueError(f"{label} is not a bounded opaque identifier")
        normalised = _separator("_", value.casefold())
        padded = f"_{normalised}_"
        if _any(f"_{marker}_" in padded for marker in _secret_markers):
            raise _ValueError(f"{label} must not contain secret-shaped material")
        if prefix is not None and not value.startswith(prefix):
            raise _ValueError(f"{label} must use the required namespace")
        return value

    def _evidence(value, label):
        return _safe_identifier(value, label, "evidence:")

    def _utc(value, label):
        if _type(value) is not _Datetime or value.tzinfo is not _UTC:
            raise _TypeError(
                f"{label} must be an exact datetime using timezone.utc"
            )
        return value

    def _timestamp(value):
        return (
            f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
            f"T{value.hour:02d}:{value.minute:02d}:{value.second:02d}."
            f"{value.microsecond:06d}Z"
        )

    def _parse_timestamp(value, label):
        if _type(value) is not _str:
            raise _TypeError(f"{label} must be an exact string")
        try:
            parsed = _Datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=_UTC
            )
        except ValueError as exc:
            raise _ValueError(f"{label} must be a canonical UTC timestamp") from exc
        if _timestamp(parsed) != value:
            raise _ValueError(f"{label} must be a canonical UTC timestamp")
        return parsed

    def _plan(plan_key, authority_version):
        if (
            _type(authority_version) is not _str
            or authority_version != _catalogue_authority_version
        ):
            raise _ValueError("catalogue authority version is unsupported")
        if _type(plan_key) is not _str:
            raise _TypeError("plan_key must be an exact string")
        for item in _catalogue:
            if item[0] == plan_key:
                return item
        raise _ValueError("plan_key is not in the accepted initial catalogue")

    def _idempotency_digest(value):
        value = _safe_identifier(value, "idempotency_key", "checkout_idempotency:")
        return "sha256:" + _sha256(value.encode("ascii")).hexdigest()

    def _identity(state_without_identity):
        payload = _json_dumps(
            state_without_identity,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        return "checkout-intent:sha256-" + _sha256(payload).hexdigest()

    def _static_contract():
        return (
            ("contract_version", _contract_version),
            ("candidate_base_commit", _candidate_base_commit),
            ("candidate_base_tree", _candidate_base_tree),
            ("candidate_schema", _candidate_schema),
            ("catalogue_authority_version", _catalogue_authority_version),
            ("candidate_status", _candidate_status),
            ("source_bindings", _source_bindings),
            ("gross_catalogue", _catalogue),
            ("return_destination_allowlist", (_return_destination,)),
            ("maximum_candidate_lifetime_seconds", 300),
            ("lifecycle_boundary", _lifecycle_boundary),
            ("authority_flags", _authority_flags),
            ("activation_gates", _activation_gates),
            (
                "assurance_status",
                "contract_only_not_checkout_provider_entitlement_s4_or_launch_assurance",
            ),
        )

    def project_checkout_intent_contract(*args, **kwargs):
        _exact_call(args, kwargs, 0, (), "contract projection")
        return _clone(_static_contract())

    def create_checkout_request_candidate(*args, **kwargs):
        positional, facts = _exact_call(
            args, kwargs, 1, _create_fields, "checkout candidate creation"
        )
        authenticated_owner = _owner(
            positional[0], "authenticated_owner_user_id"
        )
        (
            authentication_context,
            owner_user_id,
            authority_version,
            plan_key,
            intent_id,
            idempotency_key,
            requested_at,
            evaluated_at,
            valid_until,
            return_destination_id,
            replay_snapshot,
            evidence_reference,
        ) = facts
        owner_user_id = _owner(owner_user_id, "owner_user_id")
        if owner_user_id != authenticated_owner:
            raise _ValueError("owner does not match the authenticated owner root")

        auth_values = _exact_mapping(
            authentication_context, _authentication_fields, "authentication_context"
        )
        (
            auth_schema,
            auth_owner,
            authentication_reference,
            authenticated_at,
            authentication_valid_until,
            trust_status,
        ) = auth_values
        if (
            _type(auth_schema) is not _str
            or auth_schema != _authentication_schema
            or _type(trust_status) is not _str
            or trust_status != _authentication_trust
        ):
            raise _ValueError("authentication context is not the exact structural shape")
        if _owner(auth_owner, "authentication owner") != authenticated_owner:
            raise _ValueError("authentication context is cross-owner")
        authentication_reference = _evidence(
            authentication_reference, "authentication_reference"
        )
        authenticated_at = _utc(authenticated_at, "authenticated_at")
        authentication_valid_until = _utc(
            authentication_valid_until, "authentication_valid_until"
        )

        requested_at = _utc(requested_at, "requested_at")
        evaluated_at = _utc(evaluated_at, "evaluated_at")
        valid_until = _utc(valid_until, "valid_until")
        if not authenticated_at <= requested_at <= evaluated_at:
            raise _ValueError("authentication/request/evaluation ordering is invalid")
        if not evaluated_at < valid_until <= evaluated_at + _max_lifetime:
            raise _ValueError("candidate is stale or exceeds the five-minute bound")
        if valid_until > authentication_valid_until:
            raise _ValueError("candidate outlives the authentication context")

        plan = _plan(plan_key, authority_version)
        intent_id = _safe_identifier(intent_id, "intent_id", "checkout_intent:")
        idempotency_key_digest = _idempotency_digest(idempotency_key)
        evidence_reference = _evidence(evidence_reference, "evidence_reference")
        if (
            _type(return_destination_id) is not _str
            or return_destination_id != _return_destination
        ):
            raise _ValueError("return destination is not in the fixed allowlist")

        replay_values = _exact_mapping(
            replay_snapshot, _replay_fields, "replay_snapshot"
        )
        (
            replay_schema,
            replay_owner,
            replay_intent_id,
            replay_idempotency_digest,
            replay_state,
            checked_at,
            existing_candidate_identity,
        ) = replay_values
        if _type(replay_schema) is not _str or replay_schema != _replay_schema:
            raise _ValueError("replay snapshot schema is unsupported")
        if _owner(replay_owner, "replay owner") != authenticated_owner:
            raise _ValueError("replay snapshot is cross-owner")
        _safe_identifier(replay_intent_id, "replay intent_id", "checkout_intent:")
        if replay_intent_id != intent_id:
            raise _ValueError("replay snapshot names another intent")
        if (
            _type(replay_idempotency_digest) is not _str
            or _digest(replay_idempotency_digest) is None
            or replay_idempotency_digest != idempotency_key_digest
        ):
            raise _ValueError("replay snapshot has an idempotency conflict")
        if _utc(checked_at, "replay checked_at") != evaluated_at:
            raise _ValueError("replay snapshot is stale or time-of-check is ambiguous")
        if (
            _type(replay_state) is not _str
            or replay_state != "unused"
            or existing_candidate_identity is not None
        ):
            raise _ValueError("intent is replayed, used, ambiguous or conflicting")

        state_without_identity = (
            ("schema_version", _candidate_schema),
            ("candidate_status", _candidate_status),
            ("authenticated_owner_user_id", authenticated_owner),
            ("owner_reference", f"users:{authenticated_owner}"),
            ("authentication_reference", authentication_reference),
            ("authentication_runtime_verified", False),
            ("catalogue_authority_version", _catalogue_authority_version),
            ("plan_key", plan[0]),
            ("unit_amount_minor", plan[1]),
            ("currency", plan[2]),
            ("recurring_interval", plan[3]),
            ("recurring_interval_count", plan[4]),
            ("checkout_mode", "subscription"),
            ("quantity", 1),
            ("gross_price_statement", _gross_price_statement),
            ("intent_id", intent_id),
            ("idempotency_key_digest", idempotency_key_digest),
            ("requested_at", _timestamp(requested_at)),
            ("evaluated_at", _timestamp(evaluated_at)),
            ("valid_until", _timestamp(valid_until)),
            ("return_destination_id", _return_destination),
            ("replay_guard_status", "future_atomic_consume_required"),
            ("lifecycle_boundary", _lifecycle_boundary),
            ("authority_flags", _authority_flags),
            ("activation_gates", _activation_gates),
            ("evidence_reference", evidence_reference),
        )
        candidate_identity = _identity(state_without_identity)
        candidate = (
            state_without_identity[0],
            state_without_identity[1],
            ("candidate_identity", candidate_identity),
            *state_without_identity[2:],
        )
        return _clone(candidate)

    def _validate_candidate(value):
        if _type(value) is not _tuple or _len(value) != _len(_candidate_fields):
            raise _TypeError("candidate must be an exact complete tuple")
        if not _all(
            _type(item) is _tuple and _len(item) == 2 for item in value
        ):
            raise _ValueError("candidate fields must be exact pairs")
        if _tuple(item[0] for item in value) != _candidate_fields:
            raise _ValueError("candidate field order is invalid")
        view = _dict(value)
        if view["schema_version"] != _candidate_schema:
            raise _ValueError("candidate schema is unsupported")
        if view["candidate_status"] != _candidate_status:
            raise _ValueError("candidate status cannot confer authority")
        owner = _owner(
            view["authenticated_owner_user_id"], "authenticated_owner_user_id"
        )
        if view["owner_reference"] != f"users:{owner}":
            raise _ValueError("candidate owner binding is invalid")
        _evidence(view["authentication_reference"], "authentication_reference")
        if view["authentication_runtime_verified"] is not False:
            raise _ValueError("candidate cannot assert runtime authentication")
        plan = _plan(view["plan_key"], view["catalogue_authority_version"])
        if (
            _type(view["unit_amount_minor"]) is not _int
            or _type(view["unit_amount_minor"]) is _bool
            or view["unit_amount_minor"] != plan[1]
            or view["currency"] != plan[2]
            or view["recurring_interval"] != plan[3]
            or _type(view["recurring_interval_count"]) is not _int
            or _type(view["recurring_interval_count"]) is _bool
            or view["recurring_interval_count"] != plan[4]
            or view["checkout_mode"] != "subscription"
            or _type(view["quantity"]) is not _int
            or view["quantity"] != 1
            or view["gross_price_statement"] != _gross_price_statement
        ):
            raise _ValueError("candidate catalogue projection is invalid")
        _safe_identifier(view["intent_id"], "intent_id", "checkout_intent:")
        if _type(view["idempotency_key_digest"]) is not _str or _digest(
            view["idempotency_key_digest"]
        ) is None:
            raise _ValueError("candidate idempotency digest is invalid")
        requested_at = _parse_timestamp(view["requested_at"], "requested_at")
        evaluated_at = _parse_timestamp(view["evaluated_at"], "evaluated_at")
        valid_until = _parse_timestamp(view["valid_until"], "valid_until")
        if not requested_at <= evaluated_at < valid_until:
            raise _ValueError("candidate timestamps are invalid")
        if valid_until > evaluated_at + _max_lifetime:
            raise _ValueError("candidate lifetime exceeds the local bound")
        if view["return_destination_id"] != _return_destination:
            raise _ValueError("candidate return destination is invalid")
        if view["replay_guard_status"] != "future_atomic_consume_required":
            raise _ValueError("candidate cannot assert single-use consumption")
        if view["lifecycle_boundary"] != _lifecycle_boundary:
            raise _ValueError("candidate lifecycle boundary is invalid")
        if view["authority_flags"] != _authority_flags or _any(
            _type(flag) is not _bool or flag is not False
            for _, flag in view["authority_flags"]
        ):
            raise _ValueError("candidate authority flags must remain false")
        if view["activation_gates"] != _activation_gates:
            raise _ValueError("candidate activation gates are invalid")
        _evidence(view["evidence_reference"], "evidence_reference")
        state_without_identity = _tuple(
            item for item in value if item[0] != "candidate_identity"
        )
        if view["candidate_identity"] != _identity(state_without_identity):
            raise _ValueError("candidate identity does not match its exact content")
        return _clone(value)

    def validate_checkout_request_candidate(*args, **kwargs):
        positional, _ = _exact_call(
            args, kwargs, 1, (), "checkout candidate validation"
        )
        return _validate_candidate(positional[0])

    return (
        _contract_version,
        _catalogue_authority_version,
        project_checkout_intent_contract,
        create_checkout_request_candidate,
        validate_checkout_request_candidate,
    )


(
    CONTRACT_VERSION,
    CATALOGUE_AUTHORITY_VERSION,
    project_checkout_intent_contract,
    create_checkout_request_candidate,
    validate_checkout_request_candidate,
) = _build_checkout_intent_contract()


__all__ = (
    "CONTRACT_VERSION",
    "CATALOGUE_AUTHORITY_VERSION",
    "project_checkout_intent_contract",
    "create_checkout_request_candidate",
    "validate_checkout_request_candidate",
)
