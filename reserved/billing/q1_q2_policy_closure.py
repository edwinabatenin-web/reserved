"""Detached W10 policy closure for refund and paid-surface defaults.

This contract records two ordinary October engineering policies supported by
the existing Founder authority.  It performs no I/O and has no runtime,
provider, persistence, refund, route, or entitlement effect.  In particular it
does not decide post-settlement dispute, chargeback, or reversal consequences.

Trusting consumers must retain the issued handle and captured validator and
projector.  The projection contains only exact immutable built-in values.
"""

from __future__ import annotations


def _build_q1_q2_policy_closure():
    """Build the closure-bound, provider-neutral policy record."""

    _type = type
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _str = str
    _int = int
    _bool = bool
    _TypeError = TypeError
    _ValueError = ValueError
    _RuntimeError = RuntimeError

    _contract_version = "W10-S2F-Q1-Q2/2026-09-04/v1"
    _source_commit = "030da8a2928473b9b5af35a158ea6ad5c5ad8e49"
    _source_tree = "7e7430c7f3fe3dd80aeec6c06a8860f48728b520"

    # Exact immutable blobs at the authoritative source commit.  They are
    # build-time provenance only; this module never reads the repository.
    _accepted_sources = (
        (
            "founder_authority",
            "FOUNDER_DECISIONS.md",
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
        ),
        (
            "prior_engineering_defaults",
            "reserved/billing/fail_closed_launch_defaults.py",
            "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
        ),
        (
            "prior_engineering_defaults_evidence",
            "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md",
            "617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703",
        ),
        (
            "historical_policy_classification",
            "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
            "838e6c649f9925e86aca280da6917cc7e650860880204cf06b34a8fc4aa2572f",
        ),
        (
            "accepted_paid_surface_inventory",
            "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
            "5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601",
        ),
        (
            "accepted_internal_route_reconciliation",
            "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
            "4ba7324883e6aa27081e47ffa6f1c0a1fde99a5f175375a4aae289ce5b7a5917",
        ),
        (
            "accepted_internal_route_hardening",
            "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md",
            "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5",
        ),
    )

    _policy_denominator = (
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
    _previously_closed_policy_keys = (
        "billing_provider",
        "renewal_behaviour",
        "cancellation_timing",
        "failed_payment_and_grace",
        "entitlement_start_and_end",
        "promotion_and_discount_mechanics",
        "partner_offer_handling",
        "trial_and_free_access_if_applicable",
        "plan_changes_and_proration",
        "manual_overrides",
    )
    _newly_closed_policy_keys = ("refunds", "paid_access_surface")
    _remaining_policy_keys = (
        "tax_invoicing_and_additional_presentation",
        "billing_account_recovery",
        "post_settlement_dispute_chargeback_reversal_consequences",
    )
    if set(
        _previously_closed_policy_keys
        + _newly_closed_policy_keys
        + _remaining_policy_keys
    ) != set(_policy_denominator):
        raise _RuntimeError("W10-S2F policy partition does not match S1")

    _refund_policy = (
        ("scope", "october_fail_closed_baseline"),
        ("discretionary_refund_promise", False),
        ("automated_refunds_enabled", False),
        ("support_discretionary_refunds_enabled", False),
        ("mandatory_statutory_and_consumer_rights_override", True),
        ("mandatory_remedy_requires_accepted_specialist_treatment", True),
        ("legally_required_request_escalation_path_required", True),
        ("request_must_be_authenticated_to_current_reserved_owner", True),
        ("payment_subscription_and_period_binding_required", True),
        ("exact_money_and_aggregate_limit_validation_required", True),
        ("idempotency_required", True),
        ("provider_outcome_reconciliation_required", True),
        (
            "distinct_outcome_states",
            ("requested", "pending", "requires_action", "succeeded", "failed"),
        ),
        ("pending_or_failed_is_succeeded", False),
        ("provider_refund_observation_direct_entitlement_effect", False),
        (
            "access_consequence",
            "not_invented_apply_only_separately_accepted_legal_policy_outcome",
        ),
        ("refund_action_implemented", False),
    )

    _paid_surface_policy = (
        ("scope", "october_paid_subscription_without_free_tier"),
        ("inventory_source", "accepted_w10_s5a_exact_inventory"),
        (
            "authenticated_product_candidate_pending_founder_decision",
            "paid_entitlement_required",
        ),
        (
            "public_infrastructure_auth_legal_support",
            "outside_paid_gate_existing_controls_preserved",
        ),
        (
            "billing_purchase_return_recovery_candidate",
            "outside_paid_gate_existing_controls_preserved",
        ),
        (
            "required_exit_and_privacy_controls",
            "outside_paid_gate_existing_controls_preserved",
        ),
        (
            "internal_admin_unknown_requiring_reconciliation",
            "separate_or_closed_exactly_as_reconciled_by_s5b_and_s5c",
        ),
        ("customer_product_free_exception_created", False),
        ("client_side_hiding_is_enforcement", False),
        ("future_server_side_entitlement_enforcement_required", True),
        ("runtime_paid_entitlement_enforcement_implemented", False),
    )

    _authority_basis = (
        ("founder_decision_lineage", ("FD-W10-001", "FD-W10-003", "FD-OA-001")),
        (
            "classification",
            "ordinary_engineering_policy_under_paid_launch_and_no_free_tier_authority",
        ),
        ("new_or_changed_product_scope", False),
        ("provider_defaults_are_policy_authority", False),
        ("provider_observations_are_entitlement_decisions", False),
    )
    _scope_exclusions = (
        "discretionary_refund_promise",
        "provider_or_refund_action",
        "mandatory_remedy_legal_or_finance_outcome",
        "refund_access_consequence_not_separately_accepted",
        "runtime_paid_access_enforcement",
        "route_authentication_or_csrf_change",
        "provider_sdk_network_credentials_or_activation",
        "database_persistence_or_migration",
        "post_settlement_dispute_chargeback_reversal_consequence",
        "founder_production_release_or_go_live_authority",
    )
    _projection = (
        ("contract_version", _contract_version),
        ("source_commit", _source_commit),
        ("source_tree", _source_tree),
        ("accepted_sources", _accepted_sources),
        ("authority_basis", _authority_basis),
        ("source_policy_denominator", _policy_denominator),
        ("previously_closed_policy_keys", _previously_closed_policy_keys),
        ("newly_closed_policy_keys", _newly_closed_policy_keys),
        ("remaining_policy_keys", _remaining_policy_keys),
        ("refund_policy", _refund_policy),
        ("paid_surface_policy", _paid_surface_policy),
        ("policy_status", "policy_incomplete_three_keys_remaining"),
        ("q3_status", "unresolved_requires_founder_decision"),
        ("scope_exclusions", _scope_exclusions),
        (
            "assurance_status",
            "detached_policy_contract_not_runtime_provider_or_launch_assurance",
        ),
    )

    def _clone_builtin(value):
        if _type(value) is _tuple:
            return _tuple(_clone_builtin(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("Q1/Q2 projection contains a non-built-in value")

    class Q1Q2PolicyClosureHandle:
        """Opaque handle issued only by this contract producer."""

        __slots__ = ()

        def __new__(cls, _producer_token=None):
            if _producer_token is not _token:
                raise _TypeError("Q1/Q2 policy handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            raise _TypeError("Q1/Q2 policy handles are not copyable")

        def __deepcopy__(self, memo):
            raise _TypeError("Q1/Q2 policy handles are not copyable")

        def __reduce__(self):
            raise _TypeError("Q1/Q2 policy handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("Q1/Q2 policy handles are not serialisable")

    _Handle = Q1Q2PolicyClosureHandle
    _token = _object()
    _handle = _object_new(_Handle)

    def _validate(value):
        if _type(value) is not _Handle:
            raise _TypeError("value must be an exact Q1/Q2 policy handle")
        if value is not _handle:
            raise _ValueError("Q1/Q2 policy handle is not producer-issued")
        return _clone_builtin(_projection)

    def validate_q1_q2_policy_closure(value):
        return _validate(value)

    def project_q1_q2_policy_closure(value):
        return _clone_builtin(_validate(value))

    return (
        _contract_version,
        _newly_closed_policy_keys,
        _remaining_policy_keys,
        Q1Q2PolicyClosureHandle,
        _handle,
        validate_q1_q2_policy_closure,
        project_q1_q2_policy_closure,
    )


(
    CONTRACT_VERSION,
    NEWLY_CLOSED_POLICY_KEYS,
    REMAINING_POLICY_KEYS,
    Q1Q2PolicyClosureHandle,
    Q1_Q2_POLICY_CLOSURE,
    validate_q1_q2_policy_closure,
    project_q1_q2_policy_closure,
) = _build_q1_q2_policy_closure()

Q1Q2PolicyClosureHandle.__module__ = __name__
Q1Q2PolicyClosureHandle.__qualname__ = Q1Q2PolicyClosureHandle.__name__

__all__ = (
    "CONTRACT_VERSION",
    "NEWLY_CLOSED_POLICY_KEYS",
    "REMAINING_POLICY_KEYS",
    "Q1Q2PolicyClosureHandle",
    "Q1_Q2_POLICY_CLOSURE",
    "validate_q1_q2_policy_closure",
    "project_q1_q2_policy_closure",
)
