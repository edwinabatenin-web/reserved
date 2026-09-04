"""Disabled-first Stripe edge contract for W10-S4A.

This module is deliberately network-inert.  It does not import Stripe, accept
credentials, verify signatures, parse webhook payloads, create Checkout or
Portal sessions, persist events, or produce entitlement decisions.  It records
the exact provider-edge constraints that a later authenticated adapter must
satisfy before it may emit a provider-neutral billing observation.

The contract is an opaque producer-issued handle.  Trusting consumers must use
the captured validation/projector functions rather than module globals or class
metadata, which are not authority.
"""

from __future__ import annotations

import copy as _copy_module
import weakref as _weakref_module


def _build_stripe_disabled_first_contract():
    _type = type
    _id = id
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _str = str
    _int = int
    _bool = bool
    _TypeError = TypeError
    _ValueError = ValueError
    _RuntimeError = RuntimeError
    _copy = _copy_module.copy
    _deepcopy = _copy_module.deepcopy
    _WeakValueDictionary = _weakref_module.WeakValueDictionary

    _contract_version = "W10-S4A/2026-09-04/v1"
    _authority = (
        ("founder_decision", "FD-W10-002"),
        ("provider_family", "stripe_subscription"),
        ("provider_status", "provisional_disabled_first"),
        ("stripe_connect_excluded", True),
        (
            "source_provider_authority_commit",
            "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
        ),
        (
            "source_provider_authority_sha256",
            "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
        ),
    )
    _runtime_boundary = (
        ("enabled", False),
        ("network_calls_allowed", False),
        ("credentials_accepted", False),
        ("checkout_creation_available", False),
        ("portal_session_creation_available", False),
        ("webhook_ingress_available", False),
        ("provider_sdk_required", False),
        ("production_activation_authorised", False),
        ("charge_authority", False),
        ("entitlement_authority", False),
    )
    _capability_boundary = (
        ("provisional_products", ("stripe_billing", "stripe_checkout", "stripe_customer_portal")),
        ("checkout_mode", "subscription"),
        ("checkout_completion_is_payment_authority", False),
        ("portal_customer_binding_required", True),
        ("portal_plan_change_enabled", False),
        ("portal_proration_enabled", False),
        ("portal_promotion_codes_enabled", False),
        ("portal_cancel_at_period_end_target", True),
        ("portal_immediate_cancellation_enabled", False),
    )
    _webhook_boundary = (
        ("raw_request_body_required", True),
        ("provider_signature_verification_required", True),
        ("signature_verification_implemented_here", False),
        ("endpoint_secret_required_for_activation", True),
        ("asynchronous_processing_required", True),
        ("event_order_guaranteed", False),
        ("duplicate_delivery_expected", True),
        ("event_id_deduplication_required", True),
        ("object_id_plus_event_type_duplicate_check_required", True),
        ("api_version_binding_required", True),
        ("owner_and_subscription_binding_required", True),
        ("atomic_event_inbox_required", True),
        ("replay_safe_reconciliation_required", True),
        ("provider_event_is_entitlement", False),
    )
    _evidenced_events = (
        (
            "checkout.session.completed",
            "checkout_completion_observation_only_not_payment_or_entitlement_authority",
        ),
        (
            "invoice.paid",
            "successful_invoice_observation_requires_subscription_status_and_owner_reconciliation",
        ),
        (
            "invoice.payment_failed",
            "payment_failure_observation_requires_initial_vs_renewal_reconciliation",
        ),
        (
            "customer.subscription.updated",
            "subscription_or_cancellation_change_observation_requires_full_state_reconciliation",
        ),
        (
            "customer.subscription.deleted",
            "subscription_end_observation_not_direct_access_revocation",
        ),
    )
    _status_boundary = (
        ("active", "provider_observation_not_proof_all_invoices_paid"),
        ("past_due", "provider_recovery_observation_not_direct_access_rule"),
        ("unpaid", "provider_terminal_delinquency_observation"),
        ("canceled", "provider_cancellation_observation"),
        ("incomplete", "initial_payment_not_yet_verified"),
        ("incomplete_expired", "initial_payment_not_verified_terminal_provider_state"),
        ("trialing", "not_authorised_for_october_product"),
        ("paused", "provider_pause_observation_not_reserved_entitlement_rule"),
    )
    _unresolved_boundary = (
        "refund_translation_and_access_consequence",
        "dispute_chargeback_reversal_event_enumeration_and_access_consequence",
        "plan_change_and_proration",
        "promotion_and_discount_mechanics",
        "tax_invoice_and_additional_vat_presentation",
        "customer_portal_configuration_acceptance",
        "provider_terms_dpa_fees_and_security_acceptance",
        "credential_custody_and_rotation",
        "sandbox_and_target_runtime_evidence",
    )
    _activation_gates = (
        "accepted_provider_terms_and_data_processing_boundary",
        "approved_provider_credentials_and_custody",
        "authenticated_raw_body_signature_verification",
        "durable_owner_bound_event_inbox_and_reconciliation",
        "accepted_unresolved_policy_outcomes",
        "sandbox_failure_replay_ordering_and_recovery_evidence",
        "independent_security_privacy_finance_tax_and_operational_review",
        "separate_founder_production_activation_and_release_authority",
    )
    _sources = (
        ("stripe_webhooks", "https://docs.stripe.com/webhooks"),
        (
            "stripe_subscription_webhooks",
            "https://docs.stripe.com/billing/subscriptions/webhooks",
        ),
        (
            "stripe_subscription_object",
            "https://docs.stripe.com/api/subscriptions/object",
        ),
        (
            "stripe_checkout_subscriptions",
            "https://docs.stripe.com/payments/checkout/build-subscriptions",
        ),
        ("stripe_customer_portal", "https://docs.stripe.com/customer-management"),
        (
            "stripe_webhook_signatures",
            "https://docs.stripe.com/webhooks/signature",
        ),
    )
    _projection = (
        ("contract_version", _contract_version),
        ("authority", _authority),
        ("runtime_boundary", _runtime_boundary),
        ("capability_boundary", _capability_boundary),
        ("webhook_boundary", _webhook_boundary),
        ("evidenced_events", _evidenced_events),
        ("subscription_status_boundary", _status_boundary),
        ("unresolved_boundary", _unresolved_boundary),
        ("activation_gates", _activation_gates),
        ("official_sources", _sources),
        ("assurance_status", "contract_only_not_provider_adapter_or_s4_completion"),
    )

    def _clone_builtin(value):
        if _type(value) is _tuple:
            return _tuple(_clone_builtin(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("Stripe contract contains a non-built-in value")

    class StripeDisabledFirstContractHandle:
        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _token:
                raise _TypeError("Stripe contract handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_stripe_disabled_first_contract(self)

        def __deepcopy__(self, memo):
            return copy_stripe_disabled_first_contract(self)

        def __reduce__(self):
            raise _TypeError("Stripe contract handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("Stripe contract handles are not serialisable")

    _Handle = StripeDisabledFirstContractHandle
    _token = _object()
    _registry = {}
    _live_handles = _WeakValueDictionary()

    def _issue_handle():
        handle = _object_new(_Handle)
        identity = _id(handle)
        _registry[identity] = _projection
        _live_handles[identity] = handle
        return handle

    def _validate(value):
        if _type(value) is not _Handle:
            raise _TypeError("value must be an exact producer-issued Stripe contract handle")
        identity = _id(value)
        if _live_handles.get(identity) is not value:
            raise _ValueError("Stripe contract handle is not producer-issued or is stale")
        if _registry.get(identity) is not _projection:
            raise _ValueError("Stripe contract registry binding is invalid")
        return _clone_builtin(_projection)

    def validate_stripe_disabled_first_contract(value):
        return _validate(value)

    def project_stripe_disabled_first_contract(value):
        return _clone_builtin(_validate(value))

    def copy_stripe_disabled_first_contract(value):
        _validate(value)
        return _issue_handle()

    contract = _issue_handle()
    validate_stripe_disabled_first_contract(_copy(contract))
    validate_stripe_disabled_first_contract(_deepcopy(contract))

    return (
        _contract_version,
        StripeDisabledFirstContractHandle,
        contract,
        validate_stripe_disabled_first_contract,
        project_stripe_disabled_first_contract,
        copy_stripe_disabled_first_contract,
    )


(
    CONTRACT_VERSION,
    StripeDisabledFirstContractHandle,
    STRIPE_DISABLED_FIRST_CONTRACT,
    validate_stripe_disabled_first_contract,
    project_stripe_disabled_first_contract,
    copy_stripe_disabled_first_contract,
) = _build_stripe_disabled_first_contract()


__all__ = (
    "CONTRACT_VERSION",
    "StripeDisabledFirstContractHandle",
    "STRIPE_DISABLED_FIRST_CONTRACT",
    "validate_stripe_disabled_first_contract",
    "project_stripe_disabled_first_contract",
    "copy_stripe_disabled_first_contract",
)
