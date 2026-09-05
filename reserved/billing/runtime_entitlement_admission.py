"""Route-less W10-S3C admission of owner-bound billing facts.

This provider-neutral adapter is deliberately not a billing-fact source.  A
future composition root must bind two distinct functions belonging to an
independently authenticated, admitted billing-fact authority.  Both functions
must accept the same live fact and return one exact canonical projection.

Only this adapter can issue the opaque runtime-entitlement handles accepted by
its validator/projector pair.  The projected primitive protocol is the exact
``reserved-runtime-entitlement-decision/1.0`` seam consumed by W10-S5D.  No
provider observation, detached S3A/S3B tuple, route, datastore or caller-made
tuple is itself runtime access authority.
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


CONTRACT_VERSION = "reserved-w10-runtime-entitlement-admission/1.0"
BILLING_FACT_PROTOCOL_VERSION = "reserved-owner-bound-billing-fact/1.0"
BILLING_FACT_ADMISSION_STATUS = "authoritative_owner_bound_billing_fact_admitted"
RUNTIME_DECISION_PROTOCOL_VERSION = "reserved-runtime-entitlement-decision/1.0"
RUNTIME_ADMISSION_STATUS = "authoritative_runtime_entitlement_admitted"
EXACT_INSTANT_CONTRACT_VERSION = "reserved-w10-runtime-entitlement-admission/2.0"
EXACT_INSTANT_BILLING_FACT_PROTOCOL_VERSION = "reserved-owner-bound-billing-recovery-fact/2.0"
EXACT_INSTANT_BILLING_FACT_ADMISSION_STATUS = (
    "authoritative_owner_bound_billing_recovery_fact_admitted"
)
EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION = (
    "reserved-runtime-payment-recovery-decision/2.0"
)
EXACT_INSTANT_RUNTIME_ADMISSION_STATUS = (
    "authoritative_exact_instant_runtime_entitlement_admitted"
)
FD_W10_003 = "FD-W10-003"
FD_W10_004 = "FD-W10-004"
RECOVERY_DAYS = 7


class RuntimeEntitlementAdmissionError(ValueError):
    """The admission binding, billing fact or runtime handle failed closed."""


def _build_admission_kernel():
    typ, object_new = type, object.__new__
    T, S, I, B, D = tuple, str, int, bool, dict
    length, id_fn, zip_fn, any_fn = len, id, zip, any
    function_type = _types.FunctionType
    date_type, datetime_type, time_type = _date, _datetime, _time
    timedelta_type, utc = _timedelta, _timezone.utc
    sha256, dumps = _hashlib.sha256, _json.dumps
    weakref_ref = _weakref.ref
    compile_re = _re.compile
    error, type_error, value_error, exception_type = (
        RuntimeEntitlementAdmissionError,
        TypeError,
        ValueError,
        Exception,
    )

    contract_version = CONTRACT_VERSION
    billing_protocol = BILLING_FACT_PROTOCOL_VERSION
    billing_admission = BILLING_FACT_ADMISSION_STATUS
    runtime_protocol = RUNTIME_DECISION_PROTOCOL_VERSION
    runtime_admission = RUNTIME_ADMISSION_STATUS
    recovery_days = RECOVERY_DAYS

    identifier_rx = compile_re(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
    fact_identity_rx = compile_re(r"billing-fact:sha256-[0-9a-f]{64}\Z")
    runtime_identity_rx = compile_re(r"runtime-entitlement:sha256-[0-9a-f]{64}\Z")
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

    fact_keys = (
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

    allowed_states = frozenset(("paid", "payment_recovery"))
    uncertain_withdrawals = frozenset(
        (
            "withdrawal_open",
            "withdrawal_partial",
            "withdrawal_ambiguous",
            "withdrawal_contradictory",
            "withdrawal_unresolved",
        )
    )
    preservation_kinds = uncertain_withdrawals | {"existing_derived_access"}
    restoration_kinds = frozenset(
        (
            "verified_reinstatement",
            "verified_reversal_success",
            "verified_replacement_payment",
        )
    )
    ordinary_kinds = frozenset(
        (
            "verified_initial_payment",
            "verified_renewal_payment",
            "verified_renewal_failure",
        )
    )
    derivation_kinds = (
        preservation_kinds
        | restoration_kinds
        | ordinary_kinds
        | {"verified_full_withdrawal"}
    )
    withdrawal_attributions = frozenset(
        ("not_applicable", "current_subscription_period", "other_period", "unknown")
    )

    admission_registry = {}
    runtime_registry = {}

    class RuntimeEntitlementAdmissionHandle:
        """Opaque binding to one independently supplied billing-fact authority."""

        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("runtime-entitlement admission handles are binder-issued only")

        def __copy__(self):
            raise type_error("runtime-entitlement admission handles are not copyable")

        def __deepcopy__(self, memo):
            raise type_error("runtime-entitlement admission handles are not copyable")

        def __reduce__(self):
            raise type_error("runtime-entitlement admission handles are not serialisable")

    AdmissionHandle = RuntimeEntitlementAdmissionHandle

    class RuntimeEntitlementHandle:
        """Opaque admitted runtime entitlement; primitive tuples have no authority."""

        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("runtime-entitlement handles are adapter-issued only")

        def __copy__(self):
            raise type_error("runtime-entitlement handles are not copyable")

        def __deepcopy__(self, memo):
            raise type_error("runtime-entitlement handles are not copyable")

        def __reduce__(self):
            raise type_error("runtime-entitlement handles are not serialisable")

    RuntimeHandle = RuntimeEntitlementHandle

    def bounded_identifier(value, label):
        if typ(value) is not S or identifier_rx.fullmatch(value) is None:
            raise error(f"{label} is invalid")
        lowered = value.casefold()
        if any_fn(marker in lowered for marker in secret_markers):
            raise error(f"{label} is secret-shaped")
        return value

    def exact_pairs(value, keys, label):
        if typ(value) is not T or length(value) != length(keys):
            raise error(f"{label} must be an exact ordered tuple")
        parsed = []
        for index, expected_key in enumerate(keys):
            pair = value[index]
            if (
                typ(pair) is not T
                or length(pair) != 2
                or typ(pair[0]) is not S
                or pair[0] != expected_key
            ):
                raise error(f"{label} field boundary is invalid")
            parsed.append(pair[1])
        return D(zip_fn(keys, parsed, strict=True))

    def exact_utc(value, label):
        if (
            typ(value) is not datetime_type
            or value.tzinfo is not utc
            or value.utcoffset() != timedelta_type(0)
        ):
            raise error(f"{label} must be an exact timezone-aware UTC datetime")
        return value

    def canonical_fact_identity(values):
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
        payload = dumps(material, ensure_ascii=True, separators=(",", ":"))
        return "billing-fact:sha256-" + sha256(payload.encode("ascii")).hexdigest()

    def canonical_runtime_identity(values):
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

    def parse_fact(value):
        values = exact_pairs(value, fact_keys, "owner-bound billing fact")
        if values["protocol_version"] != billing_protocol:
            raise error("billing-fact protocol is invalid")
        if values["admission_status"] != billing_admission:
            raise error("billing fact is not authoritatively admitted")
        if typ(values["authenticated"]) is not B or values["authenticated"] is not True:
            raise error("billing fact is not authenticated")
        if (
            typ(values["billing_fact_authority"]) is not B
            or values["billing_fact_authority"] is not True
        ):
            raise error("billing-fact authority is absent")
        if (
            typ(values["provider_observation_direct_authority"]) is not B
            or values["provider_observation_direct_authority"] is not False
        ):
            raise error("provider observations cannot directly authorise entitlement")
        for name in ("owner_id", "billing_account_id", "subscription_id"):
            bounded_identifier(values[name], f"billing-fact {name}")
        if typ(values["decision_sequence"]) is not I or values["decision_sequence"] <= 0:
            raise error("billing-fact decision sequence is invalid")
        predecessor = values["predecessor_fact_identity"]
        if predecessor is not None and (
            typ(predecessor) is not S or fact_identity_rx.fullmatch(predecessor) is None
        ):
            raise error("billing-fact predecessor identity is invalid")
        if typ(values["state"]) is not S or values["state"] not in (
            "paid",
            "payment_recovery",
            "suspended",
        ):
            raise error("billing-fact state is invalid")
        if (
            typ(values["valid_from_inclusive"]) is not date_type
            or typ(values["valid_until_exclusive"]) is not date_type
            or values["valid_from_inclusive"] >= values["valid_until_exclusive"]
        ):
            raise error("billing-fact validity interval is invalid")
        exact_utc(values["transition_effective_at_utc"], "billing-fact transition")
        deadline = values["recovery_deadline_exclusive_at_utc"]
        if deadline is not None:
            exact_utc(deadline, "billing-fact recovery deadline")
        derivation = values["derivation_kind"]
        if typ(derivation) is not S or derivation not in derivation_kinds:
            raise error("billing-fact derivation is invalid")
        attribution = values["withdrawal_attribution"]
        if typ(attribution) is not S or attribution not in withdrawal_attributions:
            raise error("billing-fact withdrawal attribution is invalid")
        if typ(values["fact_identity"]) is not S or fact_identity_rx.fullmatch(
            values["fact_identity"]
        ) is None:
            raise error("billing-fact identity is invalid")
        if values["fact_identity"] != canonical_fact_identity(values):
            raise error("billing-fact identity does not match its content")
        return values

    def function_snapshot(fn):
        if typ(fn) is not function_type:
            raise type_error("billing-fact dependencies must be exact functions")
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

    def admission_state(handle):
        if typ(handle) is not AdmissionHandle:
            raise error("value must be an exact runtime-entitlement admission handle")
        state = admission_registry.get(id_fn(handle))
        if typ(state) is not T or length(state) != 3 or state[2]() is not handle:
            raise error("runtime-entitlement admission handle was not issued here")
        if not function_unchanged(state[0]) or not function_unchanged(state[1]):
            raise error("bound billing-fact authority changed")
        return state[0], state[1]

    def runtime_state(handle):
        if typ(handle) is not RuntimeHandle:
            raise error("value must be an exact runtime-entitlement handle")
        state = runtime_registry.get(id_fn(handle))
        if typ(state) is not T or length(state) != 8 or state[7]() is not handle:
            raise error("runtime-entitlement handle was not issued here")
        projection = exact_pairs(state[0], runtime_keys, "runtime-entitlement decision")
        if projection["decision_identity"] != canonical_runtime_identity(projection):
            raise error("runtime-entitlement registry identity is inconsistent")
        return state

    def bind_runtime_entitlement_admission(
        *, validate_admitted_billing_fact, project_admitted_billing_fact
    ):
        validator = function_snapshot(validate_admitted_billing_fact)
        projector = function_snapshot(project_admitted_billing_fact)
        if validate_admitted_billing_fact is project_admitted_billing_fact:
            raise value_error("billing-fact validator and projector must be distinct")
        handle = object_new(AdmissionHandle)
        identity = id_fn(handle)

        def remove(reference, expected=identity):
            current = admission_registry.get(expected)
            if typ(current) is T and length(current) == 3 and current[2] is reference:
                admission_registry.pop(expected, None)

        reference = weakref_ref(handle, remove)
        admission_registry[identity] = (validator, projector, reference)
        return handle

    def issue_runtime(projection, fact, admission):
        handle = object_new(RuntimeHandle)
        identity = id_fn(handle)

        def remove(reference, expected=identity):
            current = runtime_registry.get(expected)
            if typ(current) is T and length(current) == 8 and current[7] is reference:
                runtime_registry.pop(expected, None)

        reference = weakref_ref(handle, remove)
        runtime_registry[identity] = (
            projection,
            fact["billing_account_id"],
            fact["subscription_id"],
            fact["fact_identity"],
            fact["decision_sequence"],
            fact["transition_effective_at_utc"],
            admission,
            reference,
        )
        return handle

    def admit_runtime_entitlement(
        admission,
        *,
        authenticated_owner_id,
        billing_account_id,
        subscription_id,
        prior_runtime_entitlement,
        admitted_billing_fact,
        evaluated_at_utc,
    ):
        owner = bounded_identifier(authenticated_owner_id, "authenticated owner")
        account = bounded_identifier(billing_account_id, "billing account")
        subscription = bounded_identifier(subscription_id, "subscription")
        evaluated_at = exact_utc(evaluated_at_utc, "runtime-entitlement evaluation")
        validator_snapshot, projector_snapshot = admission_state(admission)
        validator, projector = validator_snapshot[0], projector_snapshot[0]
        try:
            validated_projection = validator(admitted_billing_fact)
            projected_projection = projector(admitted_billing_fact)
            validated = parse_fact(validated_projection)
            projected = parse_fact(projected_projection)
        except exception_type as exc:
            if typ(exc) is error:
                raise
            raise error("billing-fact validation failed") from exc
        if not function_unchanged(validator_snapshot) or not function_unchanged(
            projector_snapshot
        ):
            raise error("bound billing-fact authority changed during admission")
        if validated_projection != projected_projection or validated != projected:
            raise error("billing-fact validator and projector disagree")
        fact = projected
        if fact["owner_id"] != owner:
            raise error("billing fact crossed the authenticated owner boundary")
        if (
            fact["billing_account_id"] != account
            or fact["subscription_id"] != subscription
        ):
            raise error("billing fact crossed the selected account or subscription boundary")
        if fact["transition_effective_at_utc"] > evaluated_at:
            raise error("future billing facts cannot be admitted")
        if not (
            fact["valid_from_inclusive"]
            <= fact["transition_effective_at_utc"].date()
            < fact["valid_until_exclusive"]
        ):
            raise error("billing-fact transition is outside its validity interval")
        if not (
            fact["valid_from_inclusive"]
            <= evaluated_at.date()
            < fact["valid_until_exclusive"]
        ):
            raise error("stale billing facts cannot be admitted")

        if prior_runtime_entitlement is None:
            prior_state = None
            if fact["decision_sequence"] != 1 or fact["predecessor_fact_identity"] is not None:
                raise error("originless billing-fact sequence is invalid")
        else:
            prior_state = runtime_state(prior_runtime_entitlement)
            if prior_state[6] is not admission:
                raise error("runtime-entitlement lineage crossed admission authority")
            prior_projection = exact_pairs(
                prior_state[0], runtime_keys, "prior runtime-entitlement decision"
            )
            if (
                prior_projection["owner_id"] != owner
                or prior_state[1] != account
                or prior_state[2] != subscription
            ):
                raise error("billing fact crossed owner, account or subscription lineage")
            if (
                fact["decision_sequence"] != prior_state[4] + 1
                or fact["predecessor_fact_identity"] != prior_state[3]
            ):
                raise error("billing-fact predecessor or sequence is invalid")
            if fact["transition_effective_at_utc"] < prior_state[5]:
                raise error("out-of-order billing facts cannot be admitted")

        derivation = fact["derivation_kind"]
        attribution = fact["withdrawal_attribution"]
        deadline = fact["recovery_deadline_exclusive_at_utc"]
        if derivation == "verified_renewal_failure":
            if (
                deadline is None
                or fact["transition_effective_at_utc"].time() != time_type.min
                or deadline.time() != time_type.min
                or deadline
                != fact["transition_effective_at_utc"]
                + timedelta_type(days=recovery_days)
                or fact["valid_until_exclusive"] != deadline.date()
            ):
                raise error("payment recovery must be exactly seven UTC calendar days")
        elif deadline is not None:
            raise error("non-recovery billing facts cannot carry a recovery deadline")

        prior_projection = None if prior_state is None else exact_pairs(
            prior_state[0], runtime_keys, "prior runtime-entitlement decision"
        )
        prior_structurally_entitled = (
            prior_projection is not None
            and prior_projection["state"] in allowed_states
            and prior_projection["ordinary_access"] is True
        )
        prior_entitled_at_transition = (
            prior_structurally_entitled
            and prior_projection["valid_from_inclusive"]
            <= fact["transition_effective_at_utc"].date()
            <= prior_projection["valid_until_exclusive"]
        )
        prior_entitled_now = (
            prior_structurally_entitled
            and prior_projection["valid_from_inclusive"]
            <= evaluated_at.date()
            < prior_projection["valid_until_exclusive"]
        )

        if derivation == "verified_initial_payment":
            if prior_projection is not None or fact["state"] != "paid":
                raise error("initial payment cannot replace or derive from an entitlement")
            ordinary_access = True
        elif derivation == "verified_renewal_payment":
            if (
                not prior_structurally_entitled
                or fact["state"] != "paid"
                or fact["valid_from_inclusive"] != prior_projection["valid_from_inclusive"]
                or fact["valid_until_exclusive"] <= prior_projection["valid_until_exclusive"]
            ):
                raise error("renewal payment must advance an admitted entitlement")
            ordinary_access = True
        elif derivation == "verified_renewal_failure":
            if (
                not prior_entitled_at_transition
                or prior_projection["state"] != "paid"
                or fact["state"] != "payment_recovery"
                or fact["transition_effective_at_utc"].date()
                != prior_projection["valid_until_exclusive"]
                or fact["valid_from_inclusive"] != prior_projection["valid_from_inclusive"]
            ):
                raise error("renewal failure cannot create or extend originless recovery")
            ordinary_access = True
        elif derivation in preservation_kinds:
            if not prior_entitled_now:
                raise error("preservation requires a currently valid entitled predecessor")
            if (
                fact["state"] != prior_projection["state"]
                or fact["valid_from_inclusive"] < prior_projection["valid_from_inclusive"]
                or fact["valid_until_exclusive"] > prior_projection["valid_until_exclusive"]
                or deadline != prior_projection["recovery_deadline_exclusive_at_utc"]
            ):
                raise error("preservation cannot create, extend or strengthen entitlement")
            if derivation == "existing_derived_access":
                if attribution != "not_applicable":
                    raise error("ordinary preservation cannot carry withdrawal attribution")
            elif attribution == "not_applicable":
                raise error("uncertain withdrawal evidence requires explicit attribution")
            ordinary_access = True
        elif derivation == "verified_full_withdrawal":
            if not prior_entitled_at_transition:
                raise error("withdrawal cannot operate without a valid predecessor")
            if attribution == "current_subscription_period":
                if fact["state"] != "suspended":
                    raise error("verified current-period full withdrawal must suspend")
                ordinary_access = False
            elif attribution == "other_period":
                if (
                    fact["state"] != prior_projection["state"]
                    or fact["valid_from_inclusive"] < prior_projection["valid_from_inclusive"]
                    or fact["valid_until_exclusive"] > prior_projection["valid_until_exclusive"]
                ):
                    raise error("other-period withdrawal cannot change current entitlement")
                ordinary_access = True
            else:
                raise error("full withdrawal requires exact current/other-period attribution")
        elif derivation in restoration_kinds:
            if (
                prior_projection is None
                or prior_projection["state"] != "suspended"
                or prior_projection["ordinary_access"] is not False
                or prior_projection["derivation_kind"] != "verified_full_withdrawal"
                or prior_projection["withdrawal_attribution"]
                != "current_subscription_period"
                or prior_projection["predecessor_entitled_access"] is not True
                or fact["state"] != "paid"
                or attribution != "not_applicable"
            ):
                raise error("restoration requires an admitted verified withdrawal lineage")
            ordinary_access = True
        else:
            raise error("billing-fact derivation is unsupported")

        if derivation not in uncertain_withdrawals | {"verified_full_withdrawal"}:
            if attribution != "not_applicable":
                raise error("non-withdrawal facts cannot carry withdrawal attribution")

        decision_sequence = 1 if prior_projection is None else prior_projection[
            "decision_sequence"
        ] + 1
        predecessor_identity = (
            None if prior_projection is None else prior_projection["decision_identity"]
        )
        predecessor_entitled_access = bool(
            prior_projection is not None
            and prior_projection["state"] in allowed_states
            and prior_projection["ordinary_access"] is True
        )
        predecessor_owner = owner if predecessor_entitled_access else None
        runtime_values = {
            "protocol_version": runtime_protocol,
            "decision_identity": "",
            "admission_status": runtime_admission,
            "authenticated": True,
            "runtime_access_authority": True,
            "owner_id": owner,
            "decision_sequence": decision_sequence,
            "predecessor_identity": predecessor_identity,
            "state": fact["state"],
            "ordinary_access": ordinary_access,
            "valid_from_inclusive": fact["valid_from_inclusive"],
            "valid_until_exclusive": fact["valid_until_exclusive"],
            "transition_effective_at_utc": fact["transition_effective_at_utc"],
            "recovery_deadline_exclusive_at_utc": deadline,
            "predecessor_entitled_access": predecessor_entitled_access,
            "predecessor_owner_id": predecessor_owner,
            "derivation_kind": derivation,
            "withdrawal_attribution": attribution,
        }
        runtime_values["decision_identity"] = canonical_runtime_identity(runtime_values)
        projection = T((key, runtime_values[key]) for key in runtime_keys)
        return issue_runtime(projection, fact, admission)

    def validate_runtime_entitlement(value):
        return runtime_state(value)[0]

    def project_runtime_entitlement(value):
        return runtime_state(value)[0]

    return (
        RuntimeEntitlementAdmissionHandle,
        RuntimeEntitlementHandle,
        bind_runtime_entitlement_admission,
        admit_runtime_entitlement,
        validate_runtime_entitlement,
        project_runtime_entitlement,
    )


(
    RuntimeEntitlementAdmissionHandle,
    RuntimeEntitlementHandle,
    bind_runtime_entitlement_admission,
    admit_runtime_entitlement,
    validate_runtime_entitlement,
    project_runtime_entitlement,
) = _build_admission_kernel()
del _build_admission_kernel


# The v1 adapter above remains unchanged for existing date-based facts. This
# separate v2 kernel admits only the exact failed-renewal live-fact protocol.
_EXACT_FACT_KEYS = (
    "protocol_version", "fact_identity", "admission_status", "authenticated",
    "billing_fact_authority", "provider_observation_direct_authority", "owner_id",
    "billing_account_id", "subscription_id", "source_fact_id",
    "predecessor_paid_fact_id", "lifecycle_head", "state",
    "transition_effective_at_utc", "recovery_deadline_exclusive_at_utc",
    "derivation_kind",
)
_EXACT_RUNTIME_KEYS = (
    "protocol_version", "decision_identity", "admission_status", "authenticated",
    "runtime_access_authority", "owner_id", "billing_account_id", "subscription_id",
    "source_fact_id", "predecessor_paid_fact_id", "lifecycle_head", "state",
    "ordinary_access", "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc", "derivation_kind",
)
_EXACT_IDENTIFIER = _re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
_EXACT_FACT_ID = _re.compile(r"billing-recovery-fact/2:[0-9a-f]{64}\Z")
_EXACT_SOURCE_ID = _re.compile(r"failed-renewal-fact/1:[0-9a-f]{64}\Z")
_EXACT_PAID_ID = _re.compile(
    r"(?:exact-initial-fact/1|exact-paid-period-fact/2):[0-9a-f]{64}\Z"
)
_EXACT_HEAD = _re.compile(r"paid-lineage-failed-renewal-head/1:[0-9a-f]{64}\Z")
_EXACT_RUNTIME_ID = _re.compile(r"runtime-recovery-entitlement/2:[0-9a-f]{64}\Z")
_EXACT_SECRET_MARKERS = (
    "secret", "token", "password", "credential", "api_key", "apikey",
    "private_key", "sk_live", "sk_test", "bearer",
)
_EXACT_BINDINGS = {}
_EXACT_RUNTIMES = {}


class ExactInstantRuntimeEntitlementAdmissionHandle:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("exact-instant admission handles are binder-issued only")

    def __reduce__(self):
        raise TypeError("exact-instant admission handles are not serialisable")


class ExactInstantRuntimeEntitlementHandle:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("exact-instant runtime handles are adapter-issued only")

    def __reduce__(self):
        raise TypeError("exact-instant runtime handles are not serialisable")


def _exact_pairs(value, keys, label):
    if type(value) is not tuple or len(value) != len(keys):
        raise RuntimeEntitlementAdmissionError(label + " must be an exact ordered tuple")
    result = {}
    for pair, key in zip(value, keys, strict=True):
        if type(pair) is not tuple or len(pair) != 2 or pair[0] != key:
            raise RuntimeEntitlementAdmissionError(label + " field boundary is invalid")
        result[key] = pair[1]
    return result


def _exact_utc_v2(value, label):
    if (type(value) is not _datetime or value.tzinfo is not _timezone.utc
            or value.utcoffset() != _timedelta(0)):
        raise RuntimeEntitlementAdmissionError(label + " must be exact UTC")
    return value


def _exact_function_snapshot(fn):
    if type(fn) is not _types.FunctionType:
        raise TypeError("exact-instant billing-fact dependencies must be exact functions")
    return (fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
            tuple((cell, cell.cell_contents) for cell in fn.__closure__ or ()))


def _exact_function_unchanged(snapshot):
    fn, code, defaults, kwdefaults, cells = snapshot
    if (type(fn) is not _types.FunctionType or fn.__code__ is not code
            or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kwdefaults
            or len(fn.__closure__ or ()) != len(cells)):
        return False
    return all(cell is expected_cell and cell.cell_contents is expected_value
               for cell, (expected_cell, expected_value)
               in zip(fn.__closure__ or (), cells, strict=True))


def _exact_identity(domain, material):
    normalized = tuple(value.isoformat() if type(value) is _datetime else value
                       for value in material)
    payload = _json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    return domain + ":" + _hashlib.sha256(payload).hexdigest()


def _parse_exact_fact(value):
    fact = _exact_pairs(value, _EXACT_FACT_KEYS, "exact-instant billing fact")
    for name in ("owner_id", "billing_account_id", "subscription_id"):
        if (type(fact[name]) is not str or _EXACT_IDENTIFIER.fullmatch(fact[name]) is None
                or any(marker in fact[name].casefold() for marker in _EXACT_SECRET_MARKERS)):
            raise RuntimeEntitlementAdmissionError("exact-instant billing identity is invalid")
    transition = _exact_utc_v2(fact["transition_effective_at_utc"], "recovery transition")
    deadline = _exact_utc_v2(
        fact["recovery_deadline_exclusive_at_utc"], "recovery deadline")
    if (fact["protocol_version"] != EXACT_INSTANT_BILLING_FACT_PROTOCOL_VERSION
            or fact["admission_status"] != EXACT_INSTANT_BILLING_FACT_ADMISSION_STATUS
            or fact["authenticated"] is not True or fact["billing_fact_authority"] is not True
            or fact["provider_observation_direct_authority"] is not False
            or type(fact["fact_identity"]) is not str
            or _EXACT_FACT_ID.fullmatch(fact["fact_identity"]) is None
            or type(fact["source_fact_id"]) is not str
            or _EXACT_SOURCE_ID.fullmatch(fact["source_fact_id"]) is None
            or type(fact["predecessor_paid_fact_id"]) is not str
            or _EXACT_PAID_ID.fullmatch(fact["predecessor_paid_fact_id"]) is None
            or type(fact["lifecycle_head"]) is not str
            or _EXACT_HEAD.fullmatch(fact["lifecycle_head"]) is None
            or fact["state"] != "payment_recovery"
            or fact["derivation_kind"] != "verified_renewal_failure"
            or deadline != transition + _timedelta(days=RECOVERY_DAYS)):
        raise RuntimeEntitlementAdmissionError("invalid exact-instant recovery fact")
    material = tuple(fact[name] for name in _EXACT_FACT_KEYS if name != "fact_identity")
    if fact["fact_identity"] != _exact_identity("billing-recovery-fact/2", material):
        raise RuntimeEntitlementAdmissionError("recovery fact identity mismatch")
    return fact


def _parse_exact_runtime(value):
    runtime = _exact_pairs(value, _EXACT_RUNTIME_KEYS, "exact-instant runtime entitlement")
    transition = _exact_utc_v2(runtime["transition_effective_at_utc"], "runtime transition")
    deadline = _exact_utc_v2(runtime["recovery_deadline_exclusive_at_utc"], "runtime deadline")
    if (runtime["protocol_version"] != EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION
            or runtime["admission_status"] != EXACT_INSTANT_RUNTIME_ADMISSION_STATUS
            or runtime["authenticated"] is not True
            or runtime["runtime_access_authority"] is not True
            or runtime["state"] != "payment_recovery" or runtime["ordinary_access"] is not True
            or runtime["derivation_kind"] != "verified_renewal_failure"
            or deadline != transition + _timedelta(days=RECOVERY_DAYS)
            or type(runtime["decision_identity"]) is not str
            or _EXACT_RUNTIME_ID.fullmatch(runtime["decision_identity"]) is None):
        raise RuntimeEntitlementAdmissionError("invalid exact-instant runtime entitlement")
    for name in ("owner_id", "billing_account_id", "subscription_id"):
        if (type(runtime[name]) is not str
                or _EXACT_IDENTIFIER.fullmatch(runtime[name]) is None
                or any(marker in runtime[name].casefold()
                       for marker in _EXACT_SECRET_MARKERS)):
            raise RuntimeEntitlementAdmissionError("exact-instant runtime identity is invalid")
    if (type(runtime["source_fact_id"]) is not str
            or _EXACT_SOURCE_ID.fullmatch(runtime["source_fact_id"]) is None
            or type(runtime["predecessor_paid_fact_id"]) is not str
            or _EXACT_PAID_ID.fullmatch(runtime["predecessor_paid_fact_id"]) is None
            or type(runtime["lifecycle_head"]) is not str
            or _EXACT_HEAD.fullmatch(runtime["lifecycle_head"]) is None):
        raise RuntimeEntitlementAdmissionError("exact-instant runtime lineage is invalid")
    material = tuple(runtime[name] for name in _EXACT_RUNTIME_KEYS if name != "decision_identity")
    if runtime["decision_identity"] != _exact_identity("runtime-recovery-entitlement/2", material):
        raise RuntimeEntitlementAdmissionError("runtime recovery identity mismatch")
    return runtime


def bind_exact_instant_runtime_entitlement_admission(
        *, validate_admitted_billing_fact, project_admitted_billing_fact):
    validator = _exact_function_snapshot(validate_admitted_billing_fact)
    projector = _exact_function_snapshot(project_admitted_billing_fact)
    if validate_admitted_billing_fact is project_admitted_billing_fact:
        raise ValueError("exact-instant validator and projector must be distinct")
    handle = object.__new__(ExactInstantRuntimeEntitlementAdmissionHandle)
    identity = id(handle)

    def remove(reference, expected=identity):
        current = _EXACT_BINDINGS.get(expected)
        if type(current) is tuple and len(current) == 3 and current[2] is reference:
            _EXACT_BINDINGS.pop(expected, None)

    reference = _weakref.ref(handle, remove)
    _EXACT_BINDINGS[identity] = (validator, projector, reference)
    return handle


def admit_exact_instant_runtime_entitlement(admission, *, authenticated_owner_id,
        billing_account_id, subscription_id, admitted_billing_fact, evaluated_at_utc):
    _exact_utc_v2(evaluated_at_utc, "runtime evaluation")
    binding = _EXACT_BINDINGS.get(id(admission))
    if (type(admission) is not ExactInstantRuntimeEntitlementAdmissionHandle
            or type(binding) is not tuple or binding[2]() is not admission
            or not _exact_function_unchanged(binding[0])
            or not _exact_function_unchanged(binding[1])):
        raise RuntimeEntitlementAdmissionError("invalid exact-instant admission binding")
    try:
        validated = binding[0][0](admitted_billing_fact)
        projected = binding[1][0](admitted_billing_fact)
    except Exception as exc:
        raise RuntimeEntitlementAdmissionError("billing recovery fact unavailable") from exc
    if validated != projected:
        raise RuntimeEntitlementAdmissionError("billing recovery projection disagrees")
    fact = _parse_exact_fact(validated)
    if (fact["owner_id"] != authenticated_owner_id
            or fact["billing_account_id"] != billing_account_id
            or fact["subscription_id"] != subscription_id):
        raise RuntimeEntitlementAdmissionError("cross-scope recovery fact")
    runtime = dict(protocol_version=EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION,
        decision_identity="", admission_status=EXACT_INSTANT_RUNTIME_ADMISSION_STATUS,
        authenticated=True, runtime_access_authority=True, owner_id=fact["owner_id"],
        billing_account_id=fact["billing_account_id"], subscription_id=fact["subscription_id"],
        source_fact_id=fact["source_fact_id"],
        predecessor_paid_fact_id=fact["predecessor_paid_fact_id"],
        lifecycle_head=fact["lifecycle_head"], state="payment_recovery", ordinary_access=True,
        transition_effective_at_utc=fact["transition_effective_at_utc"],
        recovery_deadline_exclusive_at_utc=fact["recovery_deadline_exclusive_at_utc"],
        derivation_kind="verified_renewal_failure")
    material = tuple(runtime[name] for name in _EXACT_RUNTIME_KEYS if name != "decision_identity")
    runtime["decision_identity"] = _exact_identity("runtime-recovery-entitlement/2", material)
    projection = tuple((name, runtime[name]) for name in _EXACT_RUNTIME_KEYS)
    handle = object.__new__(ExactInstantRuntimeEntitlementHandle)
    identity = id(handle)

    def remove(reference, expected=identity):
        current = _EXACT_RUNTIMES.get(expected)
        if type(current) is tuple and len(current) == 4 and current[3] is reference:
            _EXACT_RUNTIMES.pop(expected, None)

    reference = _weakref.ref(handle, remove)
    _EXACT_RUNTIMES[identity] = (projection, admitted_billing_fact, admission, reference)
    return handle


def validate_exact_instant_runtime_entitlement(value):
    state = _EXACT_RUNTIMES.get(id(value))
    if (type(value) is not ExactInstantRuntimeEntitlementHandle or type(state) is not tuple
            or state[3]() is not value):
        raise RuntimeEntitlementAdmissionError("not an exact-instant runtime entitlement")
    binding = _EXACT_BINDINGS.get(id(state[2]))
    if (type(binding) is not tuple or binding[2]() is not state[2]
            or not _exact_function_unchanged(binding[0])
            or not _exact_function_unchanged(binding[1])):
        raise RuntimeEntitlementAdmissionError("exact-instant admission authority changed")
    validated = binding[0][0](state[1])
    projected = binding[1][0](state[1])
    fact = _parse_exact_fact(validated)
    if validated != projected:
        raise RuntimeEntitlementAdmissionError("billing recovery projection disagrees")
    runtime = _parse_exact_runtime(state[0])
    if (runtime["source_fact_id"] != fact["source_fact_id"]
            or runtime["lifecycle_head"] != fact["lifecycle_head"]
            or runtime["transition_effective_at_utc"] != fact["transition_effective_at_utc"]
            or runtime["recovery_deadline_exclusive_at_utc"] !=
                fact["recovery_deadline_exclusive_at_utc"]):
        raise RuntimeEntitlementAdmissionError("runtime recovery source changed")
    return state[0]


def project_exact_instant_runtime_entitlement(value):
    return validate_exact_instant_runtime_entitlement(value)


# The successful-full-withdrawal protocol is versioned separately so accepted
# recovery readers continue to reject it and its no-deadline meaning.
WITHDRAWAL_CONTRACT_VERSION = 'reserved-w10-runtime-entitlement-admission/3.0'
WITHDRAWAL_BILLING_FACT_PROTOCOL_VERSION = 'reserved-owner-bound-billing-withdrawal-fact/3.0'
WITHDRAWAL_BILLING_FACT_ADMISSION_STATUS = (
    'authoritative_owner_bound_billing_withdrawal_fact_admitted')
WITHDRAWAL_RUNTIME_DECISION_PROTOCOL_VERSION = 'reserved-runtime-withdrawal-decision/3.0'
WITHDRAWAL_RUNTIME_ADMISSION_STATUS = 'authoritative_withdrawal_runtime_entitlement_admitted'
_WITHDRAWAL_FACT_KEYS = (
    'protocol_version', 'fact_identity', 'admission_status', 'authenticated',
    'billing_fact_authority', 'provider_observation_direct_authority', 'owner_id',
    'billing_account_id', 'subscription_id', 'source_fact_id',
    'predecessor_paid_fact_id', 'lifecycle_head', 'state', 'ordinary_access',
    'transition_effective_at_utc', 'recovery_deadline_exclusive_at_utc',
    'derivation_kind', 'withdrawal_attribution',
)
_WITHDRAWAL_RUNTIME_KEYS = (
    'protocol_version', 'decision_identity', 'admission_status', 'authenticated',
    'runtime_access_authority', 'owner_id', 'billing_account_id', 'subscription_id',
    'source_fact_id', 'predecessor_paid_fact_id', 'lifecycle_head', 'state',
    'ordinary_access', 'transition_effective_at_utc',
    'recovery_deadline_exclusive_at_utc', 'derivation_kind', 'withdrawal_attribution',
)
_WITHDRAWAL_BINDINGS = {}
_WITHDRAWAL_RUNTIMES = {}


class FullWithdrawalRuntimeAdmissionHandle:
    __slots__ = ('__weakref__',)
    def __new__(cls, *args, **kwargs):
        raise TypeError('full-withdrawal admission handles are binder-issued only')
    def __copy__(self):
        raise TypeError('not copyable')
    def __deepcopy__(self, memo):
        raise TypeError('not copyable')
    def __reduce__(self):
        raise TypeError('not serialisable')


class FullWithdrawalRuntimeEntitlementHandle:
    __slots__ = ('__weakref__',)
    def __new__(cls, *args, **kwargs):
        raise TypeError('full-withdrawal runtime handles are adapter-issued only')
    def __copy__(self):
        raise TypeError('not copyable')
    def __deepcopy__(self, memo):
        raise TypeError('not copyable')
    def __reduce__(self):
        raise TypeError('not serialisable')


def _parse_withdrawal_fact(value):
    fact = _exact_pairs(value, _WITHDRAWAL_FACT_KEYS, 'full-withdrawal billing fact')
    transition = _exact_utc_v2(fact['transition_effective_at_utc'], 'withdrawal transition')
    if (fact['protocol_version'] != WITHDRAWAL_BILLING_FACT_PROTOCOL_VERSION
            or fact['admission_status'] != WITHDRAWAL_BILLING_FACT_ADMISSION_STATUS
            or fact['authenticated'] is not True or fact['billing_fact_authority'] is not True
            or fact['provider_observation_direct_authority'] is not False
            or fact['state'] != 'suspended' or fact['ordinary_access'] is not False
            or fact['recovery_deadline_exclusive_at_utc'] is not None
            or fact['derivation_kind'] != 'verified_full_withdrawal'
            or fact['withdrawal_attribution'] != 'current_subscription_period'
            or type(fact['fact_identity']) is not str
            or not _re.fullmatch(r'billing-withdrawal-fact/3:[0-9a-f]{64}', fact['fact_identity'])
            or type(fact['source_fact_id']) is not str
            or not _re.fullmatch(r'full-withdrawal-fact/1:[0-9a-f]{64}', fact['source_fact_id'])
            or type(fact['predecessor_paid_fact_id']) is not str
            or _EXACT_PAID_ID.fullmatch(fact['predecessor_paid_fact_id']) is None
            or type(fact['lifecycle_head']) is not str
            or not _re.fullmatch(r'paid-lineage-full-withdrawal-head/1:[0-9a-f]{64}',
                                 fact['lifecycle_head'])):
        raise RuntimeEntitlementAdmissionError('invalid full-withdrawal fact')
    for name in ('owner_id', 'billing_account_id', 'subscription_id'):
        if (type(fact[name]) is not str or _EXACT_IDENTIFIER.fullmatch(fact[name]) is None
                or any(marker in fact[name].casefold() for marker in _EXACT_SECRET_MARKERS)):
            raise RuntimeEntitlementAdmissionError('invalid full-withdrawal scope')
    material = tuple(fact[name] for name in _WITHDRAWAL_FACT_KEYS if name != 'fact_identity')
    if fact['fact_identity'] != _exact_identity('billing-withdrawal-fact/3', material):
        raise RuntimeEntitlementAdmissionError('full-withdrawal fact identity mismatch')
    return fact


def _parse_withdrawal_runtime(value):
    runtime = _exact_pairs(value, _WITHDRAWAL_RUNTIME_KEYS, 'full-withdrawal runtime')
    _exact_utc_v2(runtime['transition_effective_at_utc'], 'withdrawal runtime transition')
    if (runtime['protocol_version'] != WITHDRAWAL_RUNTIME_DECISION_PROTOCOL_VERSION
            or runtime['admission_status'] != WITHDRAWAL_RUNTIME_ADMISSION_STATUS
            or runtime['authenticated'] is not True
            or runtime['runtime_access_authority'] is not True
            or runtime['state'] != 'suspended' or runtime['ordinary_access'] is not False
            or runtime['recovery_deadline_exclusive_at_utc'] is not None
            or runtime['derivation_kind'] != 'verified_full_withdrawal'
            or runtime['withdrawal_attribution'] != 'current_subscription_period'
            or any(type(runtime[name]) is not str
                   or _EXACT_IDENTIFIER.fullmatch(runtime[name]) is None
                   or any(marker in runtime[name].casefold()
                          for marker in _EXACT_SECRET_MARKERS)
                   for name in ('owner_id', 'billing_account_id', 'subscription_id'))
            or type(runtime['source_fact_id']) is not str
            or _re.fullmatch(r'full-withdrawal-fact/1:[0-9a-f]{64}',
                             runtime['source_fact_id']) is None
            or type(runtime['predecessor_paid_fact_id']) is not str
            or _EXACT_PAID_ID.fullmatch(runtime['predecessor_paid_fact_id']) is None
            or type(runtime['lifecycle_head']) is not str
            or _re.fullmatch(r'paid-lineage-full-withdrawal-head/1:[0-9a-f]{64}',
                             runtime['lifecycle_head']) is None
            or type(runtime['decision_identity']) is not str
            or not _re.fullmatch(r'runtime-withdrawal-entitlement/3:[0-9a-f]{64}',
                                 runtime['decision_identity'])):
        raise RuntimeEntitlementAdmissionError('invalid full-withdrawal runtime')
    material = tuple(runtime[name] for name in _WITHDRAWAL_RUNTIME_KEYS
                     if name != 'decision_identity')
    if runtime['decision_identity'] != _exact_identity(
            'runtime-withdrawal-entitlement/3', material):
        raise RuntimeEntitlementAdmissionError('full-withdrawal runtime identity mismatch')
    return runtime


def bind_full_withdrawal_runtime_entitlement_admission(
        *, validate_admitted_billing_fact, project_admitted_billing_fact):
    validator = _exact_function_snapshot(validate_admitted_billing_fact)
    projector = _exact_function_snapshot(project_admitted_billing_fact)
    if validate_admitted_billing_fact is project_admitted_billing_fact:
        raise ValueError('full-withdrawal validator and projector must be distinct')
    handle = object.__new__(FullWithdrawalRuntimeAdmissionHandle)
    identity_value = id(handle)
    def remove(reference, expected=identity_value):
        current = _WITHDRAWAL_BINDINGS.get(expected)
        if type(current) is tuple and len(current) == 3 and current[2] is reference:
            _WITHDRAWAL_BINDINGS.pop(expected, None)
    reference = _weakref.ref(handle, remove)
    _WITHDRAWAL_BINDINGS[identity_value] = (validator, projector, reference)
    return handle


def admit_full_withdrawal_runtime_entitlement(admission, *, authenticated_owner_id,
        billing_account_id, subscription_id, admitted_billing_fact, evaluated_at_utc):
    _exact_utc_v2(evaluated_at_utc, 'withdrawal evaluation')
    binding = _WITHDRAWAL_BINDINGS.get(id(admission))
    if (type(admission) is not FullWithdrawalRuntimeAdmissionHandle
            or type(binding) is not tuple or binding[2]() is not admission
            or not _exact_function_unchanged(binding[0])
            or not _exact_function_unchanged(binding[1])):
        raise RuntimeEntitlementAdmissionError('invalid full-withdrawal admission binding')
    try:
        validated = binding[0][0](admitted_billing_fact)
        projected = binding[1][0](admitted_billing_fact)
    except Exception as exc:
        raise RuntimeEntitlementAdmissionError(
            'full-withdrawal billing fact unavailable') from exc
    if validated != projected:
        raise RuntimeEntitlementAdmissionError('full-withdrawal projection disagrees')
    fact = _parse_withdrawal_fact(validated)
    if tuple(fact[name] for name in ('owner_id', 'billing_account_id', 'subscription_id')) != (
            authenticated_owner_id, billing_account_id, subscription_id):
        raise RuntimeEntitlementAdmissionError('cross-scope full-withdrawal fact')
    runtime = dict(protocol_version=WITHDRAWAL_RUNTIME_DECISION_PROTOCOL_VERSION,
        decision_identity='', admission_status=WITHDRAWAL_RUNTIME_ADMISSION_STATUS,
        authenticated=True, runtime_access_authority=True, owner_id=fact['owner_id'],
        billing_account_id=fact['billing_account_id'], subscription_id=fact['subscription_id'],
        source_fact_id=fact['source_fact_id'],
        predecessor_paid_fact_id=fact['predecessor_paid_fact_id'],
        lifecycle_head=fact['lifecycle_head'], state='suspended', ordinary_access=False,
        transition_effective_at_utc=fact['transition_effective_at_utc'],
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind='verified_full_withdrawal',
        withdrawal_attribution='current_subscription_period')
    material = tuple(runtime[name] for name in _WITHDRAWAL_RUNTIME_KEYS
                     if name != 'decision_identity')
    runtime['decision_identity'] = _exact_identity('runtime-withdrawal-entitlement/3', material)
    projection = tuple((name, runtime[name]) for name in _WITHDRAWAL_RUNTIME_KEYS)
    handle = object.__new__(FullWithdrawalRuntimeEntitlementHandle)
    identity_value = id(handle)
    def remove(reference, expected=identity_value):
        current = _WITHDRAWAL_RUNTIMES.get(expected)
        if type(current) is tuple and len(current) == 4 and current[3] is reference:
            _WITHDRAWAL_RUNTIMES.pop(expected, None)
    reference = _weakref.ref(handle, remove)
    _WITHDRAWAL_RUNTIMES[identity_value] = (projection, admitted_billing_fact,
                                            admission, reference)
    return handle


def validate_full_withdrawal_runtime_entitlement(value):
    state = _WITHDRAWAL_RUNTIMES.get(id(value))
    if (type(value) is not FullWithdrawalRuntimeEntitlementHandle
            or type(state) is not tuple or state[3]() is not value):
        raise RuntimeEntitlementAdmissionError('not a full-withdrawal runtime entitlement')
    binding = _WITHDRAWAL_BINDINGS.get(id(state[2]))
    if (type(binding) is not tuple or binding[2]() is not state[2]
            or not _exact_function_unchanged(binding[0])
            or not _exact_function_unchanged(binding[1])):
        raise RuntimeEntitlementAdmissionError('full-withdrawal authority changed')
    try:
        validated = binding[0][0](state[1])
        projected = binding[1][0](state[1])
    except Exception as exc:
        raise RuntimeEntitlementAdmissionError(
            'full-withdrawal billing fact unavailable') from exc
    if validated != projected:
        raise RuntimeEntitlementAdmissionError('full-withdrawal projection disagrees')
    fact = _parse_withdrawal_fact(validated)
    runtime = _parse_withdrawal_runtime(state[0])
    if (runtime['source_fact_id'] != fact['source_fact_id']
            or runtime['lifecycle_head'] != fact['lifecycle_head']
            or runtime['transition_effective_at_utc'] != fact['transition_effective_at_utc']):
        raise RuntimeEntitlementAdmissionError('full-withdrawal source changed')
    return state[0]


def project_full_withdrawal_runtime_entitlement(value):
    return validate_full_withdrawal_runtime_entitlement(value)


__all__ = (
    "BILLING_FACT_ADMISSION_STATUS",
    "BILLING_FACT_PROTOCOL_VERSION",
    "CONTRACT_VERSION",
    "EXACT_INSTANT_BILLING_FACT_ADMISSION_STATUS",
    "EXACT_INSTANT_BILLING_FACT_PROTOCOL_VERSION",
    "EXACT_INSTANT_CONTRACT_VERSION",
    "EXACT_INSTANT_RUNTIME_ADMISSION_STATUS",
    "EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION",
    "ExactInstantRuntimeEntitlementAdmissionHandle",
    "ExactInstantRuntimeEntitlementHandle",
    "FD_W10_003",
    "FD_W10_004",
    "RECOVERY_DAYS",
    "RUNTIME_ADMISSION_STATUS",
    "RUNTIME_DECISION_PROTOCOL_VERSION",
    "RuntimeEntitlementAdmissionError",
    "RuntimeEntitlementAdmissionHandle",
    "RuntimeEntitlementHandle",
    "admit_runtime_entitlement",
    "admit_exact_instant_runtime_entitlement",
    "bind_exact_instant_runtime_entitlement_admission",
    "bind_runtime_entitlement_admission",
    "project_runtime_entitlement",
    "project_exact_instant_runtime_entitlement",
    "validate_runtime_entitlement",
    "validate_exact_instant_runtime_entitlement",
    "WITHDRAWAL_CONTRACT_VERSION",
    "WITHDRAWAL_BILLING_FACT_PROTOCOL_VERSION",
    "WITHDRAWAL_BILLING_FACT_ADMISSION_STATUS",
    "WITHDRAWAL_RUNTIME_DECISION_PROTOCOL_VERSION",
    "WITHDRAWAL_RUNTIME_ADMISSION_STATUS",
    "FullWithdrawalRuntimeAdmissionHandle",
    "FullWithdrawalRuntimeEntitlementHandle",
    "bind_full_withdrawal_runtime_entitlement_admission",
    "admit_full_withdrawal_runtime_entitlement",
    "validate_full_withdrawal_runtime_entitlement",
    "project_full_withdrawal_runtime_entitlement",
)
