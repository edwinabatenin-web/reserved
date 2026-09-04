"""W10-S2B fail-closed launch-default authority.

This producer-issued, immutable contract records four ordinary engineering
defaults already supported by the accepted W10 authority lineage.  It does not
represent a separate Founder decision, close the remaining five policy keys, or
implement billing, persistence, provider, access, or entitlement behaviour.

Trusting consumers must retain the issued handle and use the captured
``validate_*`` and ``project_*`` functions.  Public globals, class metadata,
copy/pickle hooks, descriptors, and registry contents are not authority.
"""

from __future__ import annotations

import copy as _copy_module
import weakref as _weakref_module


def _build_fail_closed_launch_defaults():
    """Build the closure-bound, runtime-neutral S2B contract."""

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
    _weakref_ref = _weakref_module.ref

    _contract_version = "W10-S2B/2026-09-04/v1"
    _integration_head = "5bc29bcb30c95ea7a5a9430104653b366d709eb6"

    # Build-time provenance literals for the exact accepted integration lineage.
    # The module performs no file I/O; assurance tests compare these digests with
    # the sources at the integration identity above.
    _accepted_sources = (
        (
            "W10-S1",
            "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
            "reserved/billing/contracts.py",
            "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
            "FD-W10-001/2026-09-02/v1",
        ),
        (
            "W10-S2A",
            "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
            "reserved/billing/provider_lifecycle_authority.py",
            "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
            "FD-W10-002+FD-W10-003/2026-09-04/v1",
        ),
        (
            "W10-S3A",
            "94bd87f019dc226ec8c73f32515229189500cf06",
            "reserved/billing/entitlement_core.py",
            "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
            "reserved-w10-entitlement-transition/1.0",
        ),
        (
            "W10-S3B",
            "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
            "reserved/billing/event_inbox_contract.py",
            "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
            "reserved-w10-event-inbox-contract/1.0",
        ),
        (
            "W10-S4A",
            "2ad4a63dd1f10ba38859050b47245c28390667d8",
            "reserved/billing/stripe_disabled_first_contract.py",
            "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
            "W10-S4A/2026-09-04/v1",
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
    _founder_settled_keys = (
        "billing_provider",
        "renewal_behaviour",
        "cancellation_timing",
        "failed_payment_and_grace",
        "entitlement_start_and_end",
        "trial_and_free_access_if_applicable",
    )
    _fail_closed_policy_keys = (
        "promotion_and_discount_mechanics",
        "partner_offer_handling",
        "plan_changes_and_proration",
        "manual_overrides",
    )
    _unresolved_policy_keys = (
        "refunds",
        "tax_invoicing_and_additional_presentation",
        "paid_access_surface",
        "billing_account_recovery",
        "post_settlement_dispute_chargeback_reversal_consequences",
    )
    if _set(
        _founder_settled_keys + _fail_closed_policy_keys + _unresolved_policy_keys
    ) != _set(_policy_denominator):
        raise _RuntimeError("W10-S2B policy partition does not match S1")

    _engineering_defaults = (
        (
            "promotion_and_discount_mechanics",
            (
                ("capability_reserved", True),
                ("active", False),
                ("promotion_codes_enabled", False),
                ("promotion_codes", ()),
                ("eligibility_rules", ()),
                ("duration_rules", ()),
                ("stacking_rules", ()),
                ("discounted_prices", ()),
                ("direct_entitlement_effect", False),
            ),
        ),
        (
            "partner_offer_handling",
            (
                ("enabled", False),
                ("supported", False),
                ("offer_definitions", ()),
                ("marketplace_or_reseller_path_enabled", False),
                ("direct_entitlement_effect", False),
            ),
        ),
        (
            "plan_changes_and_proration",
            (
                (
                    "scope",
                    "ordinary_product_customer_plan_change_and_cancellation_behaviour",
                ),
                ("mid_cycle_plan_changes_enabled", False),
                ("proration_enabled", False),
                ("immediate_cancellation_enabled", False),
                ("paid_period_end_cancellation_preserved", True),
                (
                    "paid_period_end_cancellation_outcome",
                    "stop_future_renewal_keep_access_through_already_paid_period",
                ),
                ("mandatory_statutory_and_consumer_rights_override", True),
                ("direct_entitlement_effect", False),
            ),
        ),
        (
            "manual_overrides",
            (
                ("manual_entitlement_override_enabled", False),
                ("direct_entitlement_mutation_enabled", False),
                (
                    "permitted_correction_path",
                    "append_only_observation_and_reconciliation",
                ),
                ("correction_direct_entitlement_effect", False),
            ),
        ),
    )
    _authority_basis = (
        ("founder_decision_lineage", ("FD-W10-001", "FD-W10-002", "FD-W10-003")),
        (
            "classification",
            "ordinary_engineering_fail_closed_defaults_not_separately_founder_settled",
        ),
        ("provider_defaults_are_policy_authority", False),
        ("provider_observations_are_entitlement_decisions", False),
    )
    _scope_exclusions = (
        "provider_sdk_or_network",
        "credentials_or_provider_activation",
        "database_persistence_or_io",
        "route_or_paid_access_enforcement",
        "entitlement_mutation",
        "refund_policy_or_action",
        "tax_invoice_or_additional_vat_outcome",
        "billing_account_recovery",
        "post_settlement_access_consequence",
    )
    _projection = (
        ("contract_version", _contract_version),
        ("integration_head", _integration_head),
        ("accepted_sources", _accepted_sources),
        ("authority_basis", _authority_basis),
        ("source_policy_denominator", _policy_denominator),
        ("founder_settled_policy_keys", _founder_settled_keys),
        ("fail_closed_policy_keys", _fail_closed_policy_keys),
        ("unresolved_policy_keys", _unresolved_policy_keys),
        ("engineering_defaults", _engineering_defaults),
        ("policy_status", "policy_incomplete"),
        ("scope_exclusions", _scope_exclusions),
        (
            "assurance_status",
            "contract_only_not_s2_completion_or_runtime_implementation",
        ),
    )

    def _clone_builtin(value):
        if _type(value) is _tuple:
            return _tuple(_clone_builtin(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("launch-default projection contains a non-built-in value")

    class FailClosedLaunchDefaultsHandle:
        """Opaque identity issued only by this contract producer."""

        __slots__ = ("__weakref__",)

        def __new__(cls, _producer_token=None):
            if _producer_token is not _token:
                raise _TypeError("launch-default handles are producer-issued only")
            return _object_new(cls)

        def __copy__(self):
            return copy_fail_closed_launch_defaults(self)

        def __deepcopy__(self, memo):
            return copy_fail_closed_launch_defaults(self)

        def __reduce__(self):
            raise _TypeError("launch-default handles are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("launch-default handles are not serialisable")

    _Handle = FailClosedLaunchDefaultsHandle
    _token = _object()
    _registry = {}
    _live_references = {}

    def _issue_handle():
        handle = _object_new(_Handle)
        identity = _id(handle)

        def _remove_collected(reference, _identity=identity):
            # Object ids may be reused.  An older callback may remove only the
            # exact reference and binding still current for its generation.
            current = _live_references.get(_identity)
            if _type(current) is not _tuple or _len(current) != 2:
                return
            current_reference, current_binding = current
            if current_reference is not reference:
                return
            _live_references.pop(_identity, None)
            if _registry.get(_identity) is current_binding:
                _registry.pop(_identity, None)

        reference = _weakref_ref(handle, _remove_collected)
        binding = (_projection, reference)
        _registry[identity] = binding
        _live_references[identity] = (reference, binding)
        return handle

    def _validate(value):
        if _type(value) is not _Handle:
            raise _TypeError(
                "value must be an exact producer-issued launch-default handle"
            )
        identity = _id(value)
        current = _live_references.get(identity)
        if _type(current) is not _tuple or _len(current) != 2:
            raise _ValueError("launch-default handle is not producer-issued or is stale")
        reference, binding = current
        if reference() is not value:
            raise _ValueError("launch-default handle is not producer-issued or is stale")
        if (
            _type(binding) is not _tuple
            or _len(binding) != 2
            or binding[0] is not _projection
            or binding[1] is not reference
            or _registry.get(identity) is not binding
        ):
            raise _ValueError("launch-default registry binding is invalid")
        return _clone_builtin(_projection)

    def validate_fail_closed_launch_defaults(value):
        return _validate(value)

    def project_fail_closed_launch_defaults(value):
        return _clone_builtin(_validate(value))

    def copy_fail_closed_launch_defaults(value):
        _validate(value)
        return _issue_handle()

    contract = _issue_handle()
    copy_probe = _copy(contract)
    validate_fail_closed_launch_defaults(copy_probe)
    del copy_probe
    deepcopy_probe = _deepcopy(contract)
    validate_fail_closed_launch_defaults(deepcopy_probe)
    del deepcopy_probe

    return (
        _contract_version,
        _fail_closed_policy_keys,
        _unresolved_policy_keys,
        FailClosedLaunchDefaultsHandle,
        contract,
        validate_fail_closed_launch_defaults,
        project_fail_closed_launch_defaults,
        copy_fail_closed_launch_defaults,
    )


(
    CONTRACT_VERSION,
    FAIL_CLOSED_POLICY_KEYS,
    UNRESOLVED_POLICY_KEYS,
    FailClosedLaunchDefaultsHandle,
    FAIL_CLOSED_LAUNCH_DEFAULTS,
    validate_fail_closed_launch_defaults,
    project_fail_closed_launch_defaults,
    copy_fail_closed_launch_defaults,
) = _build_fail_closed_launch_defaults()

FailClosedLaunchDefaultsHandle.__module__ = __name__
FailClosedLaunchDefaultsHandle.__qualname__ = FailClosedLaunchDefaultsHandle.__name__

__all__ = (
    "CONTRACT_VERSION",
    "FAIL_CLOSED_POLICY_KEYS",
    "UNRESOLVED_POLICY_KEYS",
    "FailClosedLaunchDefaultsHandle",
    "FAIL_CLOSED_LAUNCH_DEFAULTS",
    "validate_fail_closed_launch_defaults",
    "project_fail_closed_launch_defaults",
    "copy_fail_closed_launch_defaults",
)
