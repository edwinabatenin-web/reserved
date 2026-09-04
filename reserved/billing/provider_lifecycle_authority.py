"""Provider-neutral W10-S2A authority for the settled launch lifecycle.

This module records only the six policy inputs settled by FD-W10-002 and
FD-W10-003.  It is network-inert, persistence-free and deliberately unable to
grant entitlement.  Provider events are observations for a later reconciler;
they are never access flags.

Trusting consumers must retain the producer-issued handle and use the captured
``validate_*``/``project_*`` functions.  The projection contains built-in
immutable values only.  Public names, class attributes and ordinary copy or
pickle protocol hooks are not authority.
"""

from __future__ import annotations

import copy as _copy_module
import weakref as _weakref_module


def _build_provider_lifecycle_authority():
    """Build the closure-bound S2A authority from reviewed provenance facts.

    Runtime S1 module objects are intentionally not trust inputs.  The build and
    assurance tests bind these provenance facts to the exact corrected S1
    artifact and exercise its authoritative projector.  This prevents mutable
    pre-import S1 globals from becoming an authority-substitution path.
    """

    _type = type
    _id = id
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _len = len
    _set = set
    _str = str
    _int = int
    _bool = bool
    _TypeError = TypeError
    _ValueError = ValueError
    _RuntimeError = RuntimeError
    _copy = _copy_module.copy
    _deepcopy = _copy_module.deepcopy
    _WeakValueDictionary = _weakref_module.WeakValueDictionary

    # Exact accepted S1 provenance.  No S1 price or runtime helper is copied.
    _source_integration_commit = "9e8f94a9906f0c9d5c85b47223d20c34be499e1c"
    _source_contract_sha256 = (
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b"
    )
    _s1_authority_version = "FD-W10-001/2026-09-02/v1"
    _expected_denominator_values = (
        "billing_provider",
        "renewal_behaviour",
        "cancellation_timing",
        "failed_payment_and_grace",
        "entitlement_start_and_end",
        "refunds",
        "tax_invoicing_and_additional_presentation",
        "promotion_and_discount_mechanics",
        "partner_offer_handling",
        "paid_access_surface",
        "trial_and_free_access_if_applicable",
        "plan_changes_and_proration",
        "billing_account_recovery",
        "manual_overrides",
        "post_settlement_dispute_chargeback_reversal_consequences",
    )

    _authority_version = "FD-W10-002+FD-W10-003/2026-09-04/v1"
    _decision_records = (
        ("FD-W10-001", "2026-09-02"),
        ("FD-W10-002", "2026-09-04"),
        ("FD-W10-003", "2026-09-04"),
    )

    _settled_keys = (
        "billing_provider",
        "renewal_behaviour",
        "cancellation_timing",
        "failed_payment_and_grace",
        "entitlement_start_and_end",
        "trial_and_free_access_if_applicable",
    )
    _unresolved_keys = (
        "refunds",
        "tax_invoicing_and_additional_presentation",
        "promotion_and_discount_mechanics",
        "partner_offer_handling",
        "paid_access_surface",
        "plan_changes_and_proration",
        "billing_account_recovery",
        "manual_overrides",
        "post_settlement_dispute_chargeback_reversal_consequences",
    )
    _denominator_values = _expected_denominator_values
    if _set(_settled_keys + _unresolved_keys) != _set(_denominator_values):
        raise _RuntimeError("W10-S2A policy partition does not match S1")

    _provider = (
        ("family", "stripe_subscription"),
        ("status", "provisional_disabled_first"),
        ("capabilities", ("billing", "checkout", "customer_portal")),
        ("excluded", ("stripe_connect",)),
        ("portable_provider_boundary_required", True),
    )
    _lifecycle = (
        ("initial_access", "after_verified_successful_initial_payment_only"),
        ("renewal", "automatic_for_selected_paid_plan"),
        (
            "cancellation",
            "stop_future_renewal_keep_access_through_already_paid_period",
        ),
        ("ordinary_paid_state", "paid"),
        ("recovery_state", "payment_recovery"),
        ("recovery_access", "ordinary_access_continues_during_bounded_recovery"),
        ("recovery_days", 7),
        (
            "recovery_deadline_origin",
            "first_verified_failed_renewal_observation",
        ),
        ("recovery_deadline_extendable", False),
        (
            "duplicate_or_repeated_failure_effect",
            "must_not_extend_recovery_deadline",
        ),
        (
            "verified_recovery_effect",
            "return_to_ordinary_paid_state_after_idempotent_order_safe_reconciliation",
        ),
        (
            "unresolved_recovery_expiry_effect",
            "suspend_ordinary_access",
        ),
        ("paid_period_expiry_effect", "end_ordinary_access"),
        ("trial", "no_october_free_trial"),
        ("free_tier", "no_october_free_tier"),
        (
            "untrusted_observation_effect",
            "fail_closed_reconciliation_input_never_access_grant",
        ),
        ("provider_status_is_entitlement", False),
    )
    _policy_outcomes = (
        (
            "billing_provider",
            "provisional_stripe_billing_checkout_customer_portal_disabled_first_not_stripe_connect",
            "FD-W10-002",
        ),
        (
            "renewal_behaviour",
            "automatic_renewal_for_selected_paid_plan",
            "FD-W10-003",
        ),
        (
            "cancellation_timing",
            "stop_future_renewal_keep_access_through_already_paid_period",
            "FD-W10-003",
        ),
        (
            "failed_payment_and_grace",
            "payment_recovery_first_verified_failure_plus_7_calendar_days_non_extendable_then_suspend",
            "FD-W10-003",
        ),
        (
            "entitlement_start_and_end",
            "verified_initial_payment_start_verified_recovery_paid_period_or_recovery_expiry_end",
            "FD-W10-003",
        ),
        (
            "trial_and_free_access_if_applicable",
            "no_october_free_trial_or_free_tier",
            "FD-W10-003",
        ),
    )

    _canonical_projection = (
        ("authority_version", _authority_version),
        ("source_authority_version", _s1_authority_version),
        ("source_integration_commit", _source_integration_commit),
        ("source_contract_sha256", _source_contract_sha256),
        ("source_policy_denominator", _expected_denominator_values),
        ("founder_decisions", _decision_records),
        ("settled_policy_keys", _settled_keys),
        ("unresolved_policy_keys", _unresolved_keys),
        ("policy_status", "policy_incomplete"),
        ("provider", _provider),
        ("lifecycle", _lifecycle),
        ("policy_outcomes", _policy_outcomes),
    )

    def _clone_builtin(value):
        if _type(value) is _tuple:
            return _tuple(_clone_builtin(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("authority projection contains a non-built-in value")

    class ProviderLifecycleAuthorityHandle:
        """Opaque producer-issued authority identity; direct construction fails."""

        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _token:
                raise _TypeError("authority handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_provider_lifecycle_authority(self)

        def __deepcopy__(self, memo):
            return copy_provider_lifecycle_authority(self)

        def __reduce__(self):
            raise _TypeError("authority handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("authority handles are not serialisable")

    _Handle = ProviderLifecycleAuthorityHandle
    _token = _object()
    _registry = {}
    _live_handles = _WeakValueDictionary()

    def _issue_handle():
        # Bypass mutable class construction dispatch.  Only this closure can
        # register an instance as producer-issued.
        handle = _object_new(_Handle)
        identity = _id(handle)
        _registry[identity] = _canonical_projection
        _live_handles[identity] = handle
        return handle

    def _validate_handle(value):
        if _type(value) is not _Handle:
            raise _TypeError("value must be an exact producer-issued authority handle")
        identity = _id(value)
        if _live_handles.get(identity) is not value:
            raise _ValueError("authority handle is not producer-issued or is stale")
        projection = _registry.get(identity)
        if projection is not _canonical_projection:
            raise _ValueError("authority handle registry binding is invalid")
        return _clone_builtin(projection)

    def validate_provider_lifecycle_authority(value):
        return _validate_handle(value)

    def project_provider_lifecycle_authority(value):
        return _clone_builtin(_validate_handle(value))

    def copy_provider_lifecycle_authority(value):
        _validate_handle(value)
        return _issue_handle()

    authority = _issue_handle()

    # Exercise ordinary copy protocols now, before public class metadata can be
    # rebound.  Both must yield separately registered producer handles.
    validate_provider_lifecycle_authority(_copy(authority))
    validate_provider_lifecycle_authority(_deepcopy(authority))

    return (
        _authority_version,
        _settled_keys,
        _unresolved_keys,
        ProviderLifecycleAuthorityHandle,
        authority,
        validate_provider_lifecycle_authority,
        project_provider_lifecycle_authority,
        copy_provider_lifecycle_authority,
    )


(
    AUTHORITY_VERSION,
    SETTLED_POLICY_KEYS,
    UNRESOLVED_POLICY_KEYS,
    ProviderLifecycleAuthorityHandle,
    PROVIDER_LIFECYCLE_AUTHORITY,
    validate_provider_lifecycle_authority,
    project_provider_lifecycle_authority,
    copy_provider_lifecycle_authority,
) = _build_provider_lifecycle_authority()

ProviderLifecycleAuthorityHandle.__module__ = __name__
ProviderLifecycleAuthorityHandle.__qualname__ = ProviderLifecycleAuthorityHandle.__name__

__all__ = (
    "AUTHORITY_VERSION",
    "PROVIDER_LIFECYCLE_AUTHORITY",
    "SETTLED_POLICY_KEYS",
    "UNRESOLVED_POLICY_KEYS",
    "ProviderLifecycleAuthorityHandle",
    "copy_provider_lifecycle_authority",
    "project_provider_lifecycle_authority",
    "validate_provider_lifecycle_authority",
)
