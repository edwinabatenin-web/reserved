from __future__ import annotations

import copy
import pickle

import pytest

import reserved.billing.stripe_disabled_first_contract as stripe_contract


def _projection():
    return dict(
        stripe_contract.project_stripe_disabled_first_contract(
            stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
        )
    )


def test_contract_is_exactly_disabled_first_and_excludes_connect():
    projection = _projection()
    assert projection["contract_version"] == "W10-S4A/2026-09-04/v1"
    authority = dict(projection["authority"])
    assert authority["founder_decision"] == "FD-W10-002"
    assert authority["provider_family"] == "stripe_subscription"
    assert authority["provider_status"] == "provisional_disabled_first"
    assert authority["stripe_connect_excluded"] is True
    assert (
        authority["source_provider_authority_commit"]
        == "5464bfac7bec6b3456d1895b2355a7e8ce86859b"
    )
    assert (
        authority["source_provider_authority_sha256"]
        == "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a"
    )


def test_runtime_boundary_cannot_call_charge_activate_or_grant():
    runtime = dict(_projection()["runtime_boundary"])
    assert runtime == {
        "enabled": False,
        "network_calls_allowed": False,
        "credentials_accepted": False,
        "checkout_creation_available": False,
        "portal_session_creation_available": False,
        "webhook_ingress_available": False,
        "provider_sdk_required": False,
        "production_activation_authorised": False,
        "charge_authority": False,
        "entitlement_authority": False,
    }
    for forbidden in ("charge", "activate", "grant_access", "verify_signature"):
        assert not hasattr(stripe_contract, forbidden)


def test_checkout_and_portal_capabilities_preserve_unresolved_policy():
    capability = dict(_projection()["capability_boundary"])
    assert capability["checkout_mode"] == "subscription"
    assert capability["checkout_completion_is_payment_authority"] is False
    assert capability["portal_cancel_at_period_end_target"] is True
    assert capability["portal_immediate_cancellation_enabled"] is False
    assert capability["portal_plan_change_enabled"] is False
    assert capability["portal_proration_enabled"] is False
    assert capability["portal_promotion_codes_enabled"] is False


def test_webhook_contract_requires_authentication_deduplication_and_order_safety():
    webhook = dict(_projection()["webhook_boundary"])
    assert webhook["raw_request_body_required"] is True
    assert webhook["provider_signature_verification_required"] is True
    assert webhook["signature_verification_implemented_here"] is False
    assert webhook["event_order_guaranteed"] is False
    assert webhook["duplicate_delivery_expected"] is True
    assert webhook["event_id_deduplication_required"] is True
    assert webhook["object_id_plus_event_type_duplicate_check_required"] is True
    assert webhook["api_version_binding_required"] is True
    assert webhook["owner_and_subscription_binding_required"] is True
    assert webhook["provider_event_is_entitlement"] is False


def test_event_meanings_never_become_direct_payment_or_access_authority():
    events = dict(_projection()["evidenced_events"])
    assert "not_payment_or_entitlement_authority" in events["checkout.session.completed"]
    assert "requires_subscription_status_and_owner_reconciliation" in events["invoice.paid"]
    assert "requires_initial_vs_renewal_reconciliation" in events["invoice.payment_failed"]
    assert "not_direct_access_revocation" in events["customer.subscription.deleted"]


def test_all_provider_statuses_remain_observations():
    statuses = dict(_projection()["subscription_status_boundary"])
    assert set(statuses) == {
        "active",
        "past_due",
        "unpaid",
        "canceled",
        "incomplete",
        "incomplete_expired",
        "trialing",
        "paused",
    }
    assert statuses["active"] == "provider_observation_not_proof_all_invoices_paid"
    assert statuses["trialing"] == "not_authorised_for_october_product"
    assert all("entitlement" not in value or "not" in value for value in statuses.values())


def test_unresolved_and_activation_gates_are_explicit():
    projection = _projection()
    unresolved = projection["unresolved_boundary"]
    gates = projection["activation_gates"]
    assert "refund_translation_and_access_consequence" in unresolved
    assert "dispute_chargeback_reversal_event_enumeration_and_access_consequence" in unresolved
    assert "provider_terms_dpa_fees_and_security_acceptance" in unresolved
    assert "authenticated_raw_body_signature_verification" in gates
    assert "durable_owner_bound_event_inbox_and_reconciliation" in gates
    assert "separate_founder_production_activation_and_release_authority" in gates


def test_contract_projection_contains_only_exact_builtins_and_is_detached():
    first = stripe_contract.project_stripe_disabled_first_contract(
        stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
    )
    second = stripe_contract.project_stripe_disabled_first_contract(
        stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
    )
    assert first == second
    assert first is not second
    assert type(first) is tuple
    assert all(type(item) is tuple for item in first)


def test_handles_are_producer_issued_copyable_and_not_serialisable():
    original = stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
    for clone in (copy.copy(original), copy.deepcopy(original)):
        assert clone is not original
        assert stripe_contract.validate_stripe_disabled_first_contract(clone) == _projection_tuple()
    with pytest.raises(TypeError, match="producer-issued"):
        stripe_contract.StripeDisabledFirstContractHandle()
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(original)
    with pytest.raises(TypeError, match="exact producer-issued"):
        stripe_contract.validate_stripe_disabled_first_contract(object())


def _projection_tuple():
    return stripe_contract.project_stripe_disabled_first_contract(
        stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
    )


def test_public_rebinding_cannot_change_captured_contract():
    original_version = stripe_contract.CONTRACT_VERSION
    original_handle = stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT
    original_projection = _projection_tuple()
    try:
        stripe_contract.CONTRACT_VERSION = "forged"
        stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT = object()
        assert stripe_contract.project_stripe_disabled_first_contract(original_handle) == original_projection
        assert dict(original_projection)["contract_version"] == original_version
    finally:
        stripe_contract.CONTRACT_VERSION = original_version
        stripe_contract.STRIPE_DISABLED_FIRST_CONTRACT = original_handle


def test_contract_has_no_provider_runtime_dependencies():
    source = open(stripe_contract.__file__, encoding="utf-8").read()
    assert "import stripe" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "subprocess" not in source
    assert "os.environ" not in source
