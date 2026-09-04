"""Pure, provider-neutral W10-S5D paid-access decision kernel.

This module does not authenticate a customer, admit an entitlement, contact a
provider, persist anything, or wire a Flask route.  It can only evaluate a
runtime-entitlement value through a validator and projector explicitly bound by
the future composition root.  The bound pair must agree on one exact canonical
projection, and this kernel then independently checks its owner, admission,
authority, prior/current sequence, state, validity interval, withdrawal
derivation and content identity. Detached W10-S3A candidates are therefore not
runtime authority.

The runtime-decision protocol below is deliberately a provisional integration
seam.  Binding functions is not evidence that the future adapter, datastore,
provider reconciliation, or route enforcement exists or has been assured.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re as _re
import types as _types
import weakref as _weakref
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import time as _time
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone


CONTRACT_VERSION = "reserved-paid-access-guard/1.0"
RUNTIME_DECISION_PROTOCOL_VERSION = "reserved-runtime-entitlement-decision/1.0"
RUNTIME_ADMISSION_STATUS = "authoritative_runtime_entitlement_admitted"
FD_W10_004 = "FD-W10-004"
RECOVERY_DAYS = 7

# Exact S5A class settled by W10-S2F Q2.  Public/auth/legal/support,
# purchase/return/recovery, and internal/admin/closed routes are absent.
PAID_ENDPOINTS = (
    "v2.index",
    "v2.connections",
    "v2.dashboard_view",
    "v2.paye_manual_baseline",
    "v2.invoices",
    "v2.invoices_seed",
    "v2.optimise_view",
    "v2.optimise_calculate",
    "v2.optimise_save_scenario",
    "v2.optimise_delete_scenario",
    "v2.review_queue",
    "v2.settings_page",
    "v2.transactions",
    "v2.transactions_seed",
    "v2.yapily_callback",
    "v2.yapily_connect",
    "v2.yapily_disconnect",
    "v2.yapily_refresh",
    "hicbc.index",
    "hicbc.delete_estimate",
    "hicbc.save_estimate",
    "hicbc.link_page",
    "hicbc.link_accept",
    "hicbc.link_invite",
    "hicbc.link_revoke",
    "hicbc.result_json",
    "hicbc.annual_preview",
)


class PaidAccessGuardError(ValueError):
    """The guard handle or one of its own decisions is malformed."""


def _build_guard_kernel():
    typ, object_new = type, object.__new__
    T, S, B, D, Set = tuple, str, bool, dict, set
    length, id_fn, any_fn, zip_fn = len, id, any, zip
    function_type = _types.FunctionType
    date_type = _date
    datetime_type, time_type, timedelta_type, utc = (
        _datetime,
        _time,
        _timedelta,
        _timezone.utc,
    )
    recovery_days = RECOVERY_DAYS
    sha256, dumps = _hashlib.sha256, _json.dumps
    weakref_ref = _weakref.ref
    error, type_error, value_error, exception_type = (
        PaidAccessGuardError,
        TypeError,
        ValueError,
        Exception,
    )
    compile_re = _re.compile

    contract_version = CONTRACT_VERSION
    protocol_version = RUNTIME_DECISION_PROTOCOL_VERSION
    admission_status = RUNTIME_ADMISSION_STATUS
    paid_endpoints = PAID_ENDPOINTS
    paid_endpoint_set = frozenset(paid_endpoints)
    allowed_states = frozenset(("paid", "payment_recovery"))
    known_denied_states = frozenset(("no_entitlement", "suspended"))
    preservation_kinds = frozenset(
        (
            "existing_derived_access",
            "withdrawal_open",
            "withdrawal_partial",
            "withdrawal_ambiguous",
            "withdrawal_contradictory",
            "withdrawal_unresolved",
        )
    )
    uncertain_withdrawal_kinds = preservation_kinds - {"existing_derived_access"}
    restoration_reasons = {
        "verified_reinstatement": "allowed_verified_reinstatement",
        "verified_reversal_success": "allowed_verified_reversal_success",
        "verified_replacement_payment": "allowed_verified_replacement_payment",
    }
    ordinary_entitlement_reasons = {
        "verified_initial_payment": "allowed_initial_payment",
        "verified_renewal_payment": "allowed_renewal_payment",
        "verified_renewal_failure": "allowed_payment_recovery",
    }
    known_derivation_kinds = frozenset(
        preservation_kinds
        | set(restoration_reasons)
        | set(ordinary_entitlement_reasons)
        | {"verified_full_withdrawal"}
    )
    withdrawal_attributions = frozenset(
        ("not_applicable", "current_subscription_period", "other_period", "unknown")
    )
    owner_pattern = compile_re(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
    identity_pattern = compile_re(r"runtime-entitlement:sha256-[0-9a-f]{64}\Z")
    secret_markers = (
        "secret",
        "token",
        "password",
        "credential",
        "api_key",
        "apikey",
        "private_key",
        "sk_live",
        "sk_test",
        "bearer",
    )

    runtime_keys = (
        "protocol_version",
        "decision_identity",
        "admission_status",
        "authenticated",
        "runtime_access_authority",
        "owner_id",
        "decision_sequence",
        "predecessor_identity",
        "state",
        "ordinary_access",
        "valid_from_inclusive",
        "valid_until_exclusive",
        "transition_effective_at_utc",
        "recovery_deadline_exclusive_at_utc",
        "predecessor_entitled_access",
        "predecessor_owner_id",
        "derivation_kind",
        "withdrawal_attribution",
    )
    decision_keys = (
        "contract_version",
        "endpoint",
        "authenticated_owner_id",
        "runtime_entitlement_identity",
        "state",
        "allowed",
        "reason",
        "evaluated_at_utc",
        "provider_contacted",
        "persisted",
        "route_wiring_active",
    )
    reasons = frozenset(
        (
            "allowed_initial_payment",
            "allowed_renewal_payment",
            "allowed_payment_recovery",
            "allowed_existing_derived_access",
            "allowed_preserved_withdrawal_uncertainty",
            "allowed_verified_reinstatement",
            "allowed_verified_reversal_success",
            "allowed_verified_replacement_payment",
            "endpoint_not_in_paid_boundary",
            "authenticated_owner_unavailable",
            "runtime_entitlement_missing",
            "runtime_entitlement_invalid",
            "runtime_entitlement_projection_disagrees",
            "runtime_entitlement_not_admitted",
            "runtime_entitlement_unauthenticated",
            "runtime_access_authority_missing",
            "cross_owner_entitlement",
            "runtime_entitlement_stale",
            "suspended_entitlement",
            "no_entitlement",
            "unknown_entitlement_state",
            "ordinary_access_denied",
            "verified_full_current_period_withdrawal",
            "withdrawal_consequence_invalid",
            "preservation_boundary_invalid",
            "restoration_boundary_invalid",
            "runtime_entitlement_order_invalid",
            "runtime_entitlement_temporal_order_invalid",
            "predecessor_lineage_invalid",
            "unknown_derivation_kind",
            "bound_runtime_authority_changed",
        )
    )
    allow_reasons = frozenset(
        (
            "allowed_initial_payment",
            "allowed_renewal_payment",
            "allowed_payment_recovery",
            "allowed_existing_derived_access",
            "allowed_preserved_withdrawal_uncertainty",
            "allowed_verified_reinstatement",
            "allowed_verified_reversal_success",
            "allowed_verified_replacement_payment",
        )
    )

    guard_registry = {}
    decision_registry = {}

    class PaidAccessGuardHandle:
        """Opaque capability binding for one future runtime-entitlement pair."""

        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("paid-access guard handles are binder-issued only")

        def __copy__(self):
            raise type_error("paid-access guard handles are not copyable")

        def __deepcopy__(self, memo):
            raise type_error("paid-access guard handles are not copyable")

        def __reduce__(self):
            raise type_error("paid-access guard handles are not serialisable")

    Handle = PaidAccessGuardHandle

    class PaidAccessDecisionHandle:
        """Opaque, producer-issued result; validate it to obtain primitive data."""

        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("paid-access decisions are evaluator-issued only")

        def __copy__(self):
            raise type_error("paid-access decisions are not copyable")

        def __deepcopy__(self, memo):
            raise type_error("paid-access decisions are not copyable")

        def __reduce__(self):
            raise type_error("paid-access decisions are not serialisable")

    Decision = PaidAccessDecisionHandle

    def bounded_owner(value):
        if typ(value) is not S or owner_pattern.fullmatch(value) is None:
            return None
        lowered = value.casefold()
        if any_fn(marker in lowered for marker in secret_markers):
            return None
        return value

    def exact_pairs(value, keys, label):
        if typ(value) is not T or length(value) != length(keys):
            raise value_error(f"{label} must be an exact ordered tuple")
        parsed = []
        for index, expected_key in enumerate(keys):
            pair = value[index]
            if (
                typ(pair) is not T
                or length(pair) != 2
                or typ(pair[0]) is not S
                or pair[0] != expected_key
            ):
                raise value_error(f"{label} field boundary is invalid")
            parsed.append(pair[1])
        return D(zip_fn(keys, parsed, strict=True))

    def canonical_identity(values):
        material = (
            values["protocol_version"],
            values["admission_status"],
            values["authenticated"],
            values["runtime_access_authority"],
            values["owner_id"],
            values["decision_sequence"],
            values["predecessor_identity"],
            values["state"],
            values["ordinary_access"],
            values["valid_from_inclusive"].isoformat(),
            values["valid_until_exclusive"].isoformat(),
            values["transition_effective_at_utc"].isoformat(),
            (
                None
                if values["recovery_deadline_exclusive_at_utc"] is None
                else values["recovery_deadline_exclusive_at_utc"].isoformat()
            ),
            values["predecessor_entitled_access"],
            values["predecessor_owner_id"],
            values["derivation_kind"],
            values["withdrawal_attribution"],
        )
        payload = dumps(material, ensure_ascii=True, separators=(",", ":"))
        return "runtime-entitlement:sha256-" + sha256(payload.encode("ascii")).hexdigest()

    def exact_utc_datetime(value, label):
        if (
            typ(value) is not datetime_type
            or value.tzinfo is not utc
            or value.utcoffset() != timedelta_type(0)
        ):
            raise type_error(f"{label} must be an exact timezone-aware UTC datetime")
        return value

    def parse_runtime(value):
        values = exact_pairs(value, runtime_keys, "runtime-entitlement decision")
        if typ(values["protocol_version"]) is not S:
            raise value_error("runtime-entitlement protocol is invalid")
        if typ(values["decision_identity"]) is not S:
            raise value_error("runtime-entitlement identity is invalid")
        if typ(values["admission_status"]) is not S:
            raise value_error("runtime-entitlement admission status is invalid")
        if typ(values["authenticated"]) is not B:
            raise value_error("runtime-entitlement authentication flag is invalid")
        if typ(values["runtime_access_authority"]) is not B:
            raise value_error("runtime-access authority flag is invalid")
        if bounded_owner(values["owner_id"]) is None:
            raise value_error("runtime-entitlement owner is invalid")
        if typ(values["decision_sequence"]) is not int or values["decision_sequence"] <= 0:
            raise value_error("runtime-entitlement sequence is invalid")
        predecessor = values["predecessor_identity"]
        if predecessor is not None and (
            typ(predecessor) is not S or identity_pattern.fullmatch(predecessor) is None
        ):
            raise value_error("runtime-entitlement predecessor is invalid")
        if typ(values["state"]) is not S or not values["state"]:
            raise value_error("runtime-entitlement state is invalid")
        if typ(values["ordinary_access"]) is not B:
            raise value_error("runtime-entitlement access flag is invalid")
        if (
            typ(values["valid_from_inclusive"]) is not date_type
            or typ(values["valid_until_exclusive"]) is not date_type
            or values["valid_from_inclusive"] >= values["valid_until_exclusive"]
        ):
            raise value_error("runtime-entitlement validity interval is invalid")
        transition_at = values["transition_effective_at_utc"]
        try:
            exact_utc_datetime(transition_at, "runtime-entitlement transition time")
        except type_error as exc:
            raise value_error("runtime-entitlement transition time is not exact UTC") from exc
        deadline = values["recovery_deadline_exclusive_at_utc"]
        if deadline is not None:
            try:
                exact_utc_datetime(deadline, "runtime-entitlement recovery deadline")
            except type_error as exc:
                raise value_error(
                    "runtime-entitlement recovery deadline is not exact UTC"
                ) from exc
        if typ(values["predecessor_entitled_access"]) is not B:
            raise value_error("runtime-entitlement predecessor access flag is invalid")
        predecessor_owner = values["predecessor_owner_id"]
        if predecessor_owner is not None and bounded_owner(predecessor_owner) is None:
            raise value_error("runtime-entitlement predecessor owner is invalid")
        if values["predecessor_entitled_access"]:
            if predecessor is None or predecessor_owner != values["owner_id"]:
                raise value_error("runtime-entitlement predecessor authority is inconsistent")
        elif predecessor_owner is not None:
            raise value_error("non-entitled predecessor must not carry an owner")
        if typ(values["derivation_kind"]) is not S or not values["derivation_kind"]:
            raise value_error("runtime-entitlement derivation kind is invalid")
        if values["derivation_kind"] == "verified_renewal_failure":
            if (
                deadline is None
                or transition_at.time() != time_type.min
                or deadline.time() != time_type.min
                or deadline != transition_at + timedelta_type(days=recovery_days)
                or values["valid_until_exclusive"] != deadline.date()
            ):
                raise value_error("payment-recovery interval must be exactly seven UTC days")
        elif deadline is not None:
            raise value_error("non-recovery derivation must not carry a recovery deadline")
        if not (
            values["valid_from_inclusive"]
            <= transition_at.date()
            < values["valid_until_exclusive"]
        ):
            raise value_error("runtime-entitlement transition is outside its validity interval")
        if (
            typ(values["withdrawal_attribution"]) is not S
            or values["withdrawal_attribution"] not in withdrawal_attributions
        ):
            raise value_error("runtime-entitlement withdrawal attribution is invalid")
        if identity_pattern.fullmatch(values["decision_identity"]) is None:
            raise value_error("runtime-entitlement identity grammar is invalid")
        if values["decision_identity"] != canonical_identity(values):
            raise value_error("runtime-entitlement identity does not match its content")
        return values

    def function_snapshot(fn):
        if typ(fn) is not function_type:
            raise type_error("runtime-entitlement dependencies must be exact functions")
        cells = []
        for cell in fn.__closure__ or ():
            try:
                value = cell.cell_contents
            except value_error:
                value = cell
            cells.append((cell, value))
        return (fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__, T(cells))

    def function_unchanged(snapshot):
        fn, code, defaults, kwdefaults, contents = snapshot
        if (
            typ(fn) is not function_type
            or fn.__code__ is not code
            or fn.__defaults__ is not defaults
            or fn.__kwdefaults__ is not kwdefaults
        ):
            return False
        cells = fn.__closure__ or ()
        if length(cells) != length(contents):
            return False
        for cell, expected in zip_fn(cells, contents, strict=True):
            expected_cell, expected_value = expected
            if cell is not expected_cell:
                return False
            try:
                value = cell.cell_contents
            except value_error:
                value = cell
            if value is not expected_value:
                return False
        return True

    def guard_state(handle):
        if typ(handle) is not Handle:
            raise error("value must be an exact paid-access guard handle")
        binding = guard_registry.get(id_fn(handle))
        if typ(binding) is not T or length(binding) != 3:
            raise error("paid-access guard handle was not issued by this binder")
        validator_snapshot, projector_snapshot, reference = binding
        if reference() is not handle:
            raise error("paid-access guard handle is stale")
        return validator_snapshot, projector_snapshot

    def bind_paid_access_guard(*, validate_runtime_entitlement, project_runtime_entitlement):
        validator_snapshot = function_snapshot(validate_runtime_entitlement)
        projector_snapshot = function_snapshot(project_runtime_entitlement)
        if validate_runtime_entitlement is project_runtime_entitlement:
            raise value_error("runtime-entitlement validator and projector must be distinct")
        handle = object_new(Handle)
        identity = id_fn(handle)

        def remove(reference, expected_identity=identity):
            current = guard_registry.get(expected_identity)
            if typ(current) is T and length(current) == 3 and current[2] is reference:
                guard_registry.pop(expected_identity, None)

        reference = weakref_ref(handle, remove)
        guard_registry[identity] = (
            validator_snapshot,
            projector_snapshot,
            reference,
        )
        return handle

    def validate_decision_values(value):
        values = exact_pairs(value, decision_keys, "paid-access decision")
        if values["contract_version"] != contract_version:
            raise error("paid-access decision contract is invalid")
        if values["endpoint"] is not None and typ(values["endpoint"]) is not S:
            raise error("paid-access decision endpoint is invalid")
        if values["authenticated_owner_id"] is not None and bounded_owner(
            values["authenticated_owner_id"]
        ) is None:
            raise error("paid-access decision owner is invalid")
        identity = values["runtime_entitlement_identity"]
        if identity is not None and (
            typ(identity) is not S or identity_pattern.fullmatch(identity) is None
        ):
            raise error("paid-access decision identity is invalid")
        if typ(values["state"]) is not S or not values["state"]:
            raise error("paid-access decision state is invalid")
        if typ(values["allowed"]) is not B:
            raise error("paid-access decision flag is invalid")
        if typ(values["reason"]) is not S or values["reason"] not in reasons:
            raise error("paid-access decision reason is invalid")
        try:
            exact_utc_datetime(values["evaluated_at_utc"], "paid-access evaluation")
        except type_error as exc:
            raise error("paid-access decision evaluation time is invalid") from exc
        for name in ("provider_contacted", "persisted", "route_wiring_active"):
            if typ(values[name]) is not B or values[name] is not False:
                raise error(f"paid-access decision must carry zero {name}")
        if values["allowed"]:
            if (
                values["endpoint"] not in paid_endpoint_set
                or values["authenticated_owner_id"] is None
                or identity is None
                or values["state"] not in allowed_states
                or values["reason"] not in allow_reasons
            ):
                raise error("allowed paid-access decision is inconsistent")
        elif values["reason"] in allow_reasons:
            raise error("denied paid-access decision has an allow reason")
        return T((key, values[key]) for key in decision_keys)

    def decision(
        *, endpoint, owner, identity, state, allowed, reason, evaluated_at_utc
    ):
        endpoint_value = endpoint if typ(endpoint) is S else None
        owner_value = owner if bounded_owner(owner) is not None else None
        result = (
            ("contract_version", contract_version),
            ("endpoint", endpoint_value),
            ("authenticated_owner_id", owner_value),
            ("runtime_entitlement_identity", identity),
            ("state", state),
            ("allowed", allowed),
            ("reason", reason),
            ("evaluated_at_utc", evaluated_at_utc),
            ("provider_contacted", False),
            ("persisted", False),
            ("route_wiring_active", False),
        )
        validated = validate_decision_values(result)
        handle = object_new(Decision)
        handle_identity = id_fn(handle)

        def remove(reference, expected_identity=handle_identity):
            current = decision_registry.get(expected_identity)
            if typ(current) is T and length(current) == 2 and current[1] is reference:
                decision_registry.pop(expected_identity, None)

        reference = weakref_ref(handle, remove)
        decision_registry[handle_identity] = (validated, reference)
        return handle

    def evaluate_paid_access(
        guard,
        *,
        endpoint,
        authenticated_owner_id,
        prior_runtime_entitlement,
        current_runtime_entitlement,
        evaluated_at_utc,
    ):
        evaluated_at = exact_utc_datetime(evaluated_at_utc, "paid-access evaluation")
        evaluation_day = evaluated_at.date()
        validator_snapshot, projector_snapshot = guard_state(guard)
        owner = bounded_owner(authenticated_owner_id)
        if typ(endpoint) is not S or endpoint not in paid_endpoint_set:
            return decision(
                endpoint=endpoint,
                owner=owner,
                identity=None,
                state="unknown",
                allowed=False,
                reason="endpoint_not_in_paid_boundary",
                evaluated_at_utc=evaluated_at,
            )
        if owner is None:
            return decision(
                endpoint=endpoint,
                owner=None,
                identity=None,
                state="unknown",
                allowed=False,
                reason="authenticated_owner_unavailable",
                evaluated_at_utc=evaluated_at,
            )
        if current_runtime_entitlement is None:
            return decision(
                endpoint=endpoint,
                owner=owner,
                identity=None,
                state="unknown",
                allowed=False,
                reason="runtime_entitlement_missing",
                evaluated_at_utc=evaluated_at,
            )
        if not function_unchanged(validator_snapshot) or not function_unchanged(
            projector_snapshot
        ):
            return decision(
                endpoint=endpoint,
                owner=owner,
                identity=None,
                state="unknown",
                allowed=False,
                reason="bound_runtime_authority_changed",
                evaluated_at_utc=evaluated_at,
            )
        validator, projector = validator_snapshot[0], projector_snapshot[0]

        def admitted_values(value):
            try:
                source = validator(value)
                projected = projector(value)
                source_values = parse_runtime(source)
                projected_values = parse_runtime(projected)
            except exception_type:
                return None, "runtime_entitlement_invalid"
            if source != projected or source_values != projected_values:
                return None, "runtime_entitlement_projection_disagrees"
            return projected_values, None

        current, current_error = admitted_values(current_runtime_entitlement)
        prior, prior_error = (
            (None, None)
            if prior_runtime_entitlement is None
            else admitted_values(prior_runtime_entitlement)
        )
        if not function_unchanged(validator_snapshot) or not function_unchanged(
            projector_snapshot
        ):
            return decision(
                endpoint=endpoint,
                owner=owner,
                identity=None,
                state="unknown",
                allowed=False,
                reason="bound_runtime_authority_changed",
                evaluated_at_utc=evaluated_at,
            )
        if current_error is not None or prior_error is not None:
            return decision(
                endpoint=endpoint,
                owner=owner,
                identity=None,
                state="unknown",
                allowed=False,
                reason=current_error or prior_error,
                evaluated_at_utc=evaluated_at,
            )

        def authority_failure(values, *, require_fresh):
            if values["protocol_version"] != protocol_version:
                return "runtime_entitlement_invalid"
            if values["admission_status"] != admission_status:
                return "runtime_entitlement_not_admitted"
            if values["authenticated"] is not True:
                return "runtime_entitlement_unauthenticated"
            if values["runtime_access_authority"] is not True:
                return "runtime_access_authority_missing"
            if values["owner_id"] != owner:
                return "cross_owner_entitlement"
            if require_fresh and not (
                values["valid_from_inclusive"]
                <= evaluation_day
                < values["valid_until_exclusive"]
            ):
                return "runtime_entitlement_stale"
            return None

        identity = current["decision_identity"]
        state = current["state"]
        reason = authority_failure(current, require_fresh=False)
        if reason is not None:
            pass
        elif prior is None:
            if (
                current["decision_sequence"] != 1
                or current["predecessor_identity"] is not None
            ):
                reason = "runtime_entitlement_order_invalid"
        elif (
            current["predecessor_identity"] != prior["decision_identity"]
            or current["decision_sequence"] != prior["decision_sequence"] + 1
        ):
            reason = "runtime_entitlement_order_invalid"
        elif authority_failure(prior, require_fresh=False) is not None:
            reason = authority_failure(prior, require_fresh=False)
        elif (
            current["predecessor_entitled_access"]
            is not (prior["state"] in allowed_states and prior["ordinary_access"] is True)
            or current["predecessor_owner_id"]
            != (prior["owner_id"] if current["predecessor_entitled_access"] else None)
        ):
            reason = "predecessor_lineage_invalid"

        if reason is not None:
            pass
        elif prior is None:
            if current["transition_effective_at_utc"] > evaluated_at:
                reason = "runtime_entitlement_temporal_order_invalid"
        elif not (
            prior["transition_effective_at_utc"]
            <= current["transition_effective_at_utc"]
            <= evaluated_at
        ):
            reason = "runtime_entitlement_temporal_order_invalid"

        if reason is None:
            reason = authority_failure(current, require_fresh=True)

        if reason is not None:
            pass
        elif current["derivation_kind"] not in known_derivation_kinds:
            reason = "unknown_derivation_kind"
        elif current["derivation_kind"] == "verified_full_withdrawal":
            if current["withdrawal_attribution"] == "current_subscription_period":
                if (
                    prior is not None
                    and current["predecessor_entitled_access"] is True
                    and current["state"] == "suspended"
                    and current["ordinary_access"] is False
                ):
                    reason = "verified_full_current_period_withdrawal"
                else:
                    reason = "withdrawal_consequence_invalid"
            elif current["withdrawal_attribution"] == "not_applicable":
                reason = "withdrawal_consequence_invalid"
            else:
                reason = None
        elif current["derivation_kind"] in preservation_kinds:
            if (
                current["derivation_kind"] in uncertain_withdrawal_kinds
                and current["withdrawal_attribution"] == "not_applicable"
            ) or (
                current["derivation_kind"] == "existing_derived_access"
                and current["withdrawal_attribution"] != "not_applicable"
            ):
                reason = "withdrawal_consequence_invalid"
            else:
                reason = None
        elif current["withdrawal_attribution"] != "not_applicable":
            reason = "withdrawal_consequence_invalid"

        def preserved_access():
            if prior is None:
                return False
            prior_failure = authority_failure(prior, require_fresh=True)
            return (
                prior_failure is None
                and prior["state"] in allowed_states
                and prior["ordinary_access"] is True
                and current["state"] == prior["state"]
                and current["ordinary_access"] is True
                and current["valid_from_inclusive"] >= prior["valid_from_inclusive"]
                and current["valid_until_exclusive"] <= prior["valid_until_exclusive"]
            )

        derivation = current["derivation_kind"]
        if reason is not None:
            pass
        elif derivation in preservation_kinds or (
            derivation == "verified_full_withdrawal"
            and current["withdrawal_attribution"] != "current_subscription_period"
        ):
            if not preserved_access():
                reason = "preservation_boundary_invalid"
            elif derivation == "existing_derived_access":
                reason = "allowed_existing_derived_access"
            else:
                reason = "allowed_preserved_withdrawal_uncertainty"
        elif derivation in restoration_reasons:
            prior_failure = (
                None if prior is None else authority_failure(prior, require_fresh=False)
            )
            if (
                prior is None
                or prior_failure is not None
                or prior["decision_sequence"] <= 1
                or prior["predecessor_identity"] is None
                or prior["predecessor_entitled_access"] is not True
                or prior["predecessor_owner_id"] != prior["owner_id"]
                or prior["derivation_kind"] != "verified_full_withdrawal"
                or prior["withdrawal_attribution"] != "current_subscription_period"
                or prior["state"] != "suspended"
                or prior["ordinary_access"] is not False
                or current["state"] not in allowed_states
                or current["ordinary_access"] is not True
            ):
                reason = "restoration_boundary_invalid"
            else:
                reason = restoration_reasons[derivation]
        elif derivation == "verified_initial_payment":
            if (
                prior is not None
                or current["state"] != "paid"
                or current["ordinary_access"] is not True
            ):
                reason = "restoration_boundary_invalid"
            else:
                reason = ordinary_entitlement_reasons[derivation]
        elif derivation == "verified_renewal_payment":
            prior_failure = (
                None if prior is None else authority_failure(prior, require_fresh=False)
            )
            if (
                prior is None
                or prior_failure is not None
                or prior["state"] not in allowed_states
                or current["state"] != "paid"
                or current["ordinary_access"] is not True
            ):
                reason = "restoration_boundary_invalid"
            else:
                reason = ordinary_entitlement_reasons[derivation]
        elif derivation == "verified_renewal_failure":
            prior_failure = (
                None if prior is None else authority_failure(prior, require_fresh=False)
            )
            if (
                prior is None
                or prior_failure is not None
                or prior["state"] != "paid"
                or prior["ordinary_access"] is not True
                or current["state"] != "payment_recovery"
                or current["ordinary_access"] is not True
                or current["transition_effective_at_utc"].date()
                != prior["valid_until_exclusive"]
                or current["valid_from_inclusive"] != prior["valid_from_inclusive"]
            ):
                reason = "restoration_boundary_invalid"
            else:
                reason = ordinary_entitlement_reasons[derivation]
        elif state == "suspended":
            reason = "suspended_entitlement"
        elif state == "no_entitlement":
            reason = "no_entitlement"
        elif state not in allowed_states and state not in known_denied_states:
            reason = "unknown_entitlement_state"
        elif current["ordinary_access"] is not True:
            reason = "ordinary_access_denied"
        else:
            reason = "unknown_derivation_kind"

        allowed = reason in allow_reasons
        return decision(
            endpoint=endpoint,
            owner=owner,
            identity=identity,
            state=state,
            allowed=allowed,
            reason=reason,
            evaluated_at_utc=evaluated_at,
        )

    def validate_paid_access_decision(value):
        if typ(value) is not Decision:
            raise error("value must be an exact paid-access decision handle")
        binding = decision_registry.get(id_fn(value))
        if typ(binding) is not T or length(binding) != 2 or binding[1]() is not value:
            raise error("paid-access decision was not issued by this evaluator")
        return validate_decision_values(binding[0])

    return (
        PaidAccessGuardHandle,
        PaidAccessDecisionHandle,
        bind_paid_access_guard,
        evaluate_paid_access,
        validate_paid_access_decision,
    )


(
    PaidAccessGuardHandle,
    PaidAccessDecisionHandle,
    bind_paid_access_guard,
    evaluate_paid_access,
    validate_paid_access_decision,
) = _build_guard_kernel()
del _build_guard_kernel


__all__ = (
    "CONTRACT_VERSION",
    "FD_W10_004",
    "PAID_ENDPOINTS",
    "RECOVERY_DAYS",
    "RUNTIME_ADMISSION_STATUS",
    "RUNTIME_DECISION_PROTOCOL_VERSION",
    "PaidAccessGuardError",
    "PaidAccessGuardHandle",
    "PaidAccessDecisionHandle",
    "bind_paid_access_guard",
    "evaluate_paid_access",
    "validate_paid_access_decision",
)
