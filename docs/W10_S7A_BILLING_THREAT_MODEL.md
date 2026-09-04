# W10-S7A October billing threat/control/gap register

**Status:** evidence candidate for independent review; W10-specific delta only;
not security assurance, launch assurance, provider acceptance or activation.

**Evidence cut-off:** 4 September 2026 at integration commit
`f9412b36adeb75dc7d5d5af56824c87235f28ce7`, tree
`1b648be16bdc2bc41311f7968f6d402a63d4c8a9`.

## Scope and interpretation

This register covers the subscription-billing threats introduced by W10. It
references, but does not reproduce, W9's general identity, custody, privacy,
monitoring, incident, outage, target-runtime, retention and activation model.
W9 controls are inherited dependencies, not evidence that the billing-specific
delta has been closed.

Every row is open and has one current control statement, one fail-closed state,
an exact missing-evidence list and named future slice owners. “Implemented
control” includes local contract or preview behavior only where the source
actually implements it. Contract, inventory and reconciliation evidence is not
runtime enforcement. Absence of a provider path prevents a billing side effect
today but is not proof that the future path is safe.

Founder questions **Q1** (refund promise/full-refund access), **Q2** (exact paid
surface) and **Q3** (verified post-settlement loss/restoration consequence)
remain unanswered. VAT/invoice treatment and owner-bound no-transfer recovery
remain specialist gates, not new Founder questions. No provider semantics are
inferred beyond accepted S2C/S4A evidence.

## Machine-readable register

The block below is the normative finite denominator. SHA-256 values bind the
exact repository evidence inspected. `live` bindings intentionally fail if an
implementation control drifts. `historical_at_cutoff` bindings verify the exact
Git blob at this evidence cut-off so later truthful planning reconciliation
does not rewrite historical provenance.

<!-- W10-S7A-REGISTER-BEGIN -->
```json
{
  "schema_version": "W10-S7A/2026-09-04/v1",
  "repository_head": "f9412b36adeb75dc7d5d5af56824c87235f28ce7",
  "repository_tree": "1b648be16bdc2bc41311f7968f6d402a63d4c8a9",
  "scope": "october_subscription_billing_security_privacy_operations_delta",
  "w9_general_model_reproduced": false,
  "threat_denominator": 21,
  "threat_ids": [
    "BT-01", "BT-02", "BT-03", "BT-04", "BT-05", "BT-06", "BT-07",
    "BT-08", "BT-09", "BT-10", "BT-11", "BT-12", "BT-13", "BT-14",
    "BT-15", "BT-16", "BT-17", "BT-18", "BT-19", "BT-20", "BT-21"
  ],
  "founder_questions": {
    "Q1": "unanswered_refund_and_confirmed_full_refund_access_consequence",
    "Q2": "unanswered_exact_paid_access_surface",
    "Q3": "unanswered_verified_post_settlement_loss_and_restoration_consequence"
  },
  "specialist_gates_not_new_founder_questions": [
    "tax_invoicing_and_additional_vat_presentation",
    "owner_bound_no_transfer_billing_account_recovery"
  ],
  "security_assurance": false,
  "launch_assurance": false,
  "provider_activation_authority": false,
  "sources": [
    {
      "id": "SRC-01",
      "path": "FOUNDER_DECISIONS.md",
      "accepted_commit": "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
      "sha256": "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-02",
      "path": "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
      "accepted_commit": "f9412b36adeb75dc7d5d5af56824c87235f28ce7",
      "sha256": "cd17168c04ed5c3b05044322daae2480973d57220f05c0419f539f6fdf14977d",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-03",
      "path": "reserved/billing/contracts.py",
      "accepted_commit": "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
      "sha256": "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
      "binding": "live"
    },
    {
      "id": "SRC-04",
      "path": "reserved/billing/provider_lifecycle_authority.py",
      "accepted_commit": "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
      "sha256": "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
      "binding": "live"
    },
    {
      "id": "SRC-05",
      "path": "reserved/billing/fail_closed_launch_defaults.py",
      "accepted_commit": "1033c9fbef008dcd33125a0b14e7fb18b8846d19",
      "sha256": "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
      "binding": "live"
    },
    {
      "id": "SRC-06",
      "path": "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
      "accepted_commit": "a07348976321df65bbd95c9170c906bcddd5baa5",
      "sha256": "db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-07",
      "path": "reserved/billing/entitlement_core.py",
      "accepted_commit": "94bd87f019dc226ec8c73f32515229189500cf06",
      "sha256": "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
      "binding": "live"
    },
    {
      "id": "SRC-08",
      "path": "reserved/billing/event_inbox_contract.py",
      "accepted_commit": "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
      "sha256": "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
      "binding": "live"
    },
    {
      "id": "SRC-09",
      "path": "reserved/billing/stripe_disabled_first_contract.py",
      "accepted_commit": "2ad4a63dd1f10ba38859050b47245c28390667d8",
      "sha256": "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
      "binding": "live"
    },
    {
      "id": "SRC-10",
      "path": "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
      "accepted_commit": "9c0760192bb2420b90e57ec7313f69bbe52cbf74",
      "sha256": "abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-11",
      "path": "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
      "accepted_commit": "051ae665a0cc94f6e9cdbbc728c621825c7769fe",
      "sha256": "d1b8a3b836006bba8e688f0c9388b6855f61784a4a0acb18d20a3a215c7b92a1",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-12",
      "path": "reserved/services/w10_billing_presentation.py",
      "accepted_commit": "45ade8e356716b320b0f984cf33882abf505fb7d",
      "sha256": "2812f2e2bccd968b7286c47c59a1b881f6b6a4b9913250019ff3eb416f2e1c88",
      "binding": "live"
    },
    {
      "id": "SRC-13",
      "path": "reserved/services/w10_billing_page.py",
      "accepted_commit": "23d04a6eec09909b1315797adc4fd1aa5ba9bdd0",
      "sha256": "cbfa21ff44bece691b0049c29dbcd33bc7ae4b15216bdbd3e5a2fd1631bec8b4",
      "binding": "live"
    },
    {
      "id": "SRC-14",
      "path": "docs/W10_S6C_AUTHENTICATED_PLAN_QUOTE_EVIDENCE.md",
      "accepted_commit": "3e05fb7f3149ee7030be768909eb6fe4f50e0b75",
      "sha256": "c424c0ca999ef18568dfc1b86f79d9f0e27af1d05e7f9167ef9de43b344b3bb1",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-15",
      "path": "docs/W10_S6D_PLAN_SELECTION_PREVIEW_EVIDENCE.md",
      "accepted_commit": "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
      "sha256": "d7306da9e1e163420e345567800c6789d8422619ceaf9b91d925458d0a136790",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-16",
      "path": "reserved/web/v2.py",
      "accepted_commit": "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
      "sha256": "d91434e2fcf804c74a4154716cab5b1f4ac1642b8f3c90f895a7cf23428b0ca0",
      "binding": "live"
    },
    {
      "id": "SRC-17",
      "path": "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
      "accepted_commit": "587828337e01f269320048847b3250a690ce6133",
      "sha256": "8dd542319b301da6153b5695d3fcfc64f1f30794972d8324967dc1b55880fe92",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-18",
      "path": "docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md",
      "accepted_commit": "587828337e01f269320048847b3250a690ce6133",
      "sha256": "4d57107306bf78e5bf32ee2f2de24bf49531abbc1cb2dddf20595ae907893647",
      "binding": "historical_at_cutoff"
    },
    {
      "id": "SRC-19",
      "path": "docs/W9_SECURITY_DECISION_DOSSIER.md",
      "accepted_commit": "587828337e01f269320048847b3250a690ce6133",
      "sha256": "8828333aa53c92899f02df0ca9a64c04b3e7811b51fb3f154a01f2882da7446c",
      "binding": "historical_at_cutoff"
    }
  ],
  "threats": [
    {
      "id": "BT-01",
      "title": "price_plan_or_currency_tamper",
      "assets": ["catalogue_authority", "quoted_total", "selected_plan"],
      "attack_or_failure": "Browser or mutable runtime data substitutes a plan, price, cadence, currency or VAT wording between quote, selection and future checkout.",
      "current_evidence": ["SRC-01", "SRC-03", "SRC-12", "SRC-13", "SRC-14", "SRC-15", "SRC-16"],
      "control_id": "BC-01",
      "implemented_control": "Closure-bound S1 authority and S6 pure presentation/preview paths validate exact supported plan facts and produce no charge or provider request.",
      "control_strength": "local_contract_and_noncharging_preview_only",
      "current_fail_closed_state": "Unsupported or tampered plan input is rejected/unsupported and the preview cannot create checkout or payment.",
      "gap_id": "BG-01",
      "exact_missing_evidence": ["server_rederivation_of_price_plan_currency_and_catalogue_version_at_checkout", "signed_or_server_bound_checkout_line_items", "target_negative_tests_for_browser_price_plan_currency_and_vat_tamper"],
      "closure_owner_slices": ["W10-S3", "W10-S4", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-02",
      "title": "promotion_discount_or_partner_offer_tamper",
      "assets": ["offer_definition", "eligibility", "charged_total", "entitlement"],
      "attack_or_failure": "A client, provider configuration or stale offer applies an unauthorised discount, stacks offers, changes eligibility or grants access.",
      "current_evidence": ["SRC-03", "SRC-05", "SRC-06"],
      "control_id": "BC-02",
      "implemented_control": "S2B keeps promotions inactive, partner offers disabled/unsupported and all offer facts non-entitling.",
      "control_strength": "implemented_fail_closed_policy_contract_only",
      "current_fail_closed_state": "There is no active October offer path; provider or browser defaults cannot authorise one.",
      "gap_id": "BG-02",
      "exact_missing_evidence": ["versioned_server_side_offer_registry_if_offers_are_enabled", "eligibility_duration_stacking_and_exact_money_tests", "provider_configuration_and_target_reconciliation_evidence"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S4", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-03",
      "title": "checkout_return_or_session_confusion",
      "assets": ["authenticated_owner", "checkout_intent", "return_state", "billing_account"],
      "attack_or_failure": "An attacker swaps checkout/session identifiers, replays a return, forges success in the browser or uses an open redirect to confuse completion.",
      "current_evidence": ["SRC-03", "SRC-09", "SRC-10", "SRC-14", "SRC-15", "SRC-16"],
      "control_id": "BC-03",
      "implemented_control": "S4A is disabled and S6 exposes only authenticated noncharging previews; S5A records that no checkout/session/return route exists.",
      "control_strength": "absence_of_runtime_path_plus_contract_boundary",
      "current_fail_closed_state": "No browser return can create a charge, billing fact or entitlement because checkout is not implemented.",
      "gap_id": "BG-03",
      "exact_missing_evidence": ["owner_bound_single_use_checkout_intent_and_csrf_state", "server_verified_checkout_completion_independent_of_return_parameters", "fixed_allowlisted_return_destinations", "sandbox_and_target_swap_replay_open_redirect_and_false_success_tests"],
      "closure_owner_slices": ["W10-S3", "W10-S4", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-04",
      "title": "customer_portal_or_billing_recovery_confusion",
      "assets": ["reserved_owner", "owner_billing_mapping", "provider_management_session"],
      "attack_or_failure": "Billing email, provider customer ID, subscription ID, redirect input or support action selects another owner's billing account or bypasses Reserved login.",
      "current_evidence": ["SRC-06", "SRC-08", "SRC-09", "SRC-10"],
      "control_id": "BC-04",
      "implemented_control": "S2C defines the no-transfer owner-rooted fail-closed baseline, S3B models only detached owner-bound records, and S4A remains unable to create portal sessions.",
      "control_strength": "specialist_baseline_and_structural_contract_only",
      "current_fail_closed_state": "Portal/recovery stays disabled; email/customer identifiers and provider defaults are not login or owner authority.",
      "gap_id": "BG-04",
      "exact_missing_evidence": ["authenticated_reserved_owner_adapter", "durable_unique_owner_to_billing_account_mapping", "atomic_freshness_replay_and_idempotency_control", "support_least_privilege_and_identity_recovery_evidence", "target_cross_owner_email_collision_session_swap_and_return_integrity_tests"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S4", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-05",
      "title": "webhook_authenticity_bypass",
      "assets": ["raw_webhook_body", "signature", "provider_event_namespace", "billing_observation"],
      "attack_or_failure": "A forged, wrongly signed, wrong-endpoint, wrong-account or incorrectly parsed event is accepted as provider-authentic.",
      "current_evidence": ["SRC-08", "SRC-09"],
      "control_id": "BC-05",
      "implemented_control": "S4A records raw-body/signature/secret requirements and is disabled; S3B producer issuance explicitly is not provider authenticity.",
      "control_strength": "disabled_provider_edge_contract_only",
      "current_fail_closed_state": "No webhook endpoint or verification adapter exists, so no inbound event is admitted as authentic.",
      "gap_id": "BG-05",
      "exact_missing_evidence": ["exact_raw_body_signature_verification_before_parsing", "endpoint_account_mode_api_version_and_event_namespace_binding", "safe_timestamp_tolerance_and_secret_rotation_overlap", "sandbox_and_target_forged_signature_wrong_secret_wrong_mode_and_parser_differential_tests"],
      "closure_owner_slices": ["W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-06",
      "title": "webhook_replay_duplicate_or_idempotency_failure",
      "assets": ["provider_event_identity", "event_inbox", "receipt", "side_effect"],
      "attack_or_failure": "A replay, duplicate delivery or retry creates duplicate observations, charges, entitlement transitions or operational work.",
      "current_evidence": ["SRC-07", "SRC-08", "SRC-09"],
      "control_id": "BC-06",
      "implemented_control": "S3A transition identity and S3B detached receipt classifications model replay/idempotency outcomes with no direct entitlement effect.",
      "control_strength": "pure_contract_no_durable_deduplication",
      "current_fail_closed_state": "No provider event is persisted or applied; duplicate structural candidates cannot directly mutate entitlement.",
      "gap_id": "BG-06",
      "exact_missing_evidence": ["durable_unique_provider_event_namespace_and_id_constraint", "atomic_inbox_receipt_disposition_and_side_effect_transaction", "retry_crash_concurrency_and_duplicate_delivery_tests", "provider_reconciliation_after_lost_acknowledgement"],
      "closure_owner_slices": ["W10-S3", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-07",
      "title": "event_order_object_or_subscription_substitution",
      "assets": ["billing_account", "subscription", "provider_object", "event_order", "entitlement_transition"],
      "attack_or_failure": "An out-of-order or substituted object/event is applied to the wrong owner, account, subscription, paid period or lifecycle version.",
      "current_evidence": ["SRC-04", "SRC-07", "SRC-08", "SRC-09"],
      "control_id": "BC-07",
      "implemented_control": "S3A requires exact owner/account/subscription matching and monotonic transitions; S3B models secondary duplicates, older observations and reconciliation-only dispositions.",
      "control_strength": "pure_transition_and_structural_contracts_only",
      "current_fail_closed_state": "Unknown, conflicting, substituted or non-monotonic facts have no direct access effect and require reconciliation.",
      "gap_id": "BG-07",
      "exact_missing_evidence": ["provider_object_to_internal_owner_account_subscription_binding", "durable_versioned_compare_and_set_transition", "out_of_order_same_timestamp_object_reuse_and_subscription_replacement_tests", "authoritative_provider_snapshot_reconciliation"],
      "closure_owner_slices": ["W10-S3", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-08",
      "title": "cross_owner_billing_account_mapping",
      "assets": ["reserved_users_id", "billing_account", "subscription", "management_access"],
      "attack_or_failure": "A stale, duplicate, email-derived, browser-supplied or support-modified mapping exposes or administers another owner's billing account.",
      "current_evidence": ["SRC-06", "SRC-08", "SRC-10", "SRC-17", "SRC-18"],
      "control_id": "BC-08",
      "implemented_control": "S2C fixes current authenticated Reserved owner as sole root and S3B records exact positive users.id ownership structurally; no durable billing mapping exists.",
      "control_strength": "owner_binding_contract_and_missing_runtime_path",
      "current_fail_closed_state": "Missing, stale, duplicate, ambiguous and cross-owner mapping must deny; no portal or billing-account recovery route exists.",
      "gap_id": "BG-08",
      "exact_missing_evidence": ["durable_unique_owner_mapping_schema_and_migration", "foreign_key_or_equivalent_owner_integrity_and_atomic_update", "no_email_lookup_no_transfer_merge_or_delegation_enforcement", "cross_owner_enumeration_deletion_recreation_and_support_misuse_tests"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-09",
      "title": "unauthorised_entitlement_grant",
      "assets": ["canonical_entitlement", "paid_surface", "paid_period"],
      "attack_or_failure": "Browser state, provider status, checkout return, unverified event, support action or stale cache grants or extends paid access.",
      "current_evidence": ["SRC-04", "SRC-05", "SRC-07", "SRC-08", "SRC-09", "SRC-10"],
      "control_id": "BC-09",
      "implemented_control": "S2A/S3A state that provider labels are observations, S2B disables manual override, S3B gives unresolved events zero effect and S4A cannot emit entitlement.",
      "control_strength": "contract_only_no_server_side_paid_gate",
      "current_fail_closed_state": "Billing inputs cannot grant entitlement today; however authenticated product routes remain auth-only, so this absence blocks launch rather than proving paid isolation.",
      "gap_id": "BG-09",
      "exact_missing_evidence": ["durable_canonical_entitlement_projection_from_verified_ordered_facts", "server_side_default_deny_gate_on_every_Q2_approved_surface", "cache_invalidation_direct_url_api_and_stale_unknown_state_tests", "audited_non_override_correction_path"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S5", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-10",
      "title": "entitlement_revocation_recovery_or_concurrency_race",
      "assets": ["entitlement_version", "paid_period", "recovery_state", "route_access"],
      "attack_or_failure": "Concurrent payment, cancellation, expiry, recovery or correction observations produce lost updates, stale grants or incorrect suspension/restoration.",
      "current_evidence": ["SRC-04", "SRC-07", "SRC-08", "SRC-10"],
      "control_id": "BC-10",
      "implemented_control": "S3A models versioned transition preconditions and S3B models append-only candidate/disposition facts; neither is durable or enforced.",
      "control_strength": "optimistic_transition_contract_only",
      "current_fail_closed_state": "Conflicting or stale structural inputs reject/reconcile with no direct entitlement mutation; no paid-route enforcement exists.",
      "gap_id": "BG-10",
      "exact_missing_evidence": ["atomic_entitlement_compare_and_set_and_append_only_audit", "concurrent_webhook_reconciliation_cancellation_and_expiry_tests", "cache_and_multi_worker_revocation_propagation", "crash_retry_and_manual_correction_recovery"],
      "closure_owner_slices": ["W10-S3", "W10-S5", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-11",
      "title": "payment_recovery_deadline_extension_or_clock_abuse",
      "assets": ["first_verified_failure_time", "seven_calendar_day_deadline", "recovery_access"],
      "attack_or_failure": "Duplicate failures, clock/timezone drift, reordered events or mutable deadlines extend recovery access or suspend it early.",
      "current_evidence": ["SRC-01", "SRC-04", "SRC-07", "SRC-08"],
      "control_id": "BC-11",
      "implemented_control": "FD-W10-003/S2A/S3A fix recovery to the first verified failed-renewal observation plus seven calendar days, non-extendable by duplicates.",
      "control_strength": "settled_policy_and_pure_transition_contract_only",
      "current_fail_closed_state": "No runtime recovery deadline or access continuation is created; ambiguous/unverified observations have no transition effect.",
      "gap_id": "BG-11",
      "exact_missing_evidence": ["durable_immutable_first_verified_failure_timestamp", "canonical_utc_calendar_deadline_and_trusted_clock_policy", "duplicate_reorder_dst_leap_boundary_and_worker_race_tests", "target_scheduler_monitoring_and_missed_deadline_reconciliation"],
      "closure_owner_slices": ["W10-S3", "W10-S4", "W10-S5", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-12",
      "title": "refund_state_amount_or_access_ambiguity",
      "assets": ["refund_request", "exact_money", "provider_refund_state", "paid_access"],
      "attack_or_failure": "Pending, failed, partial, duplicated or wrong-payment refund facts are treated as succeeded, exceed paid amount or silently alter access.",
      "current_evidence": ["SRC-01", "SRC-05", "SRC-06", "SRC-08", "SRC-09"],
      "control_id": "BC-12",
      "implemented_control": "S2C requires owner-bound exact-money idempotent reconciliation and preserves Q1; S3B refund observations have zero direct entitlement effect.",
      "control_strength": "policy_evidence_and_zero_effect_contract_only",
      "current_fail_closed_state": "No ordinary automated/support refund is enabled; mandatory-rights requests require the approved manual legal path, and provider observations do not change access.",
      "gap_id": "BG-12",
      "exact_missing_evidence": ["answered_Q1", "accepted_uk_legal_finance_tax_refund_and_credit_note_treatment", "owner_payment_period_amount_currency_and_aggregate_limit_binding", "provider_sandbox_pending_failed_partial_duplicate_and_recovery_matrix", "customer_copy_support_authority_and_target_tests"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S4", "W10-S5", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-13",
      "title": "dispute_chargeback_or_reversal_consequence_ambiguity",
      "assets": ["settlement_observation", "provider_case_state", "funds_loss_or_restoration", "paid_access"],
      "attack_or_failure": "Open, partial, withdrawn, reinstated, won/lost or out-of-order post-settlement events are collapsed into an invented access consequence.",
      "current_evidence": ["SRC-01", "SRC-06", "SRC-07", "SRC-08", "SRC-09"],
      "control_id": "BC-13",
      "implemented_control": "S3B records these kinds as reconciliation-only zero-effect observations; S2C preserves Q3 and forbids inference from provider labels.",
      "control_strength": "zero_effect_observation_contract_only",
      "current_fail_closed_state": "Ambiguous or post-settlement observations neither grant nor extend access; no suspension/restoration rule is implemented.",
      "gap_id": "BG-13",
      "exact_missing_evidence": ["answered_Q3", "accepted_legal_finance_fraud_support_and_customer_notice_treatment", "exact_provider_case_event_and_money_matrix", "sandbox_out_of_order_partial_loss_reinstatement_and_appeal_tests", "target_reconciliation_and_restoration_runbook"],
      "closure_owner_slices": ["W10-S2", "W10-S3", "W10-S4", "W10-S5", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-14",
      "title": "admin_support_correction_or_override_abuse",
      "assets": ["founder_session", "support_role", "billing_record", "entitlement", "audit"],
      "attack_or_failure": "A privileged user bypasses owner verification, transfers an account, grants access, rewrites billing history or performs an unaudited correction.",
      "current_evidence": ["SRC-05", "SRC-06", "SRC-08", "SRC-10", "SRC-11", "SRC-17", "SRC-18"],
      "control_id": "BC-14",
      "implemented_control": "S2B disables manual entitlement override; S3B permits append-only structural dispositions only; S5B preserves Founder-only route boundaries as evidence but implements no billing admin tool.",
      "control_strength": "disabled_override_contract_and_route_evidence_only",
      "current_fail_closed_state": "No billing support/admin correction or transfer path exists; existing Founder routes remain separate and cannot grant billing entitlement.",
      "gap_id": "BG-14",
      "exact_missing_evidence": ["named_least_privilege_support_and_security_roles", "strong_reauthentication_owner_verification_and_dual_control_for_sensitive_actions", "append_only_reason_evidence_before_after_and_actor_audit", "no_transfer_merge_manual_grant_and_cross_owner_negative_tests", "break_glass_alert_review_and_revocation_runbook"],
      "closure_owner_slices": ["W10-S3", "W10-S5", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-15",
      "title": "billing_credentials_signing_secret_or_key_rotation_failure",
      "assets": ["provider_api_key", "webhook_secret", "encryption_key", "rotation_state"],
      "attack_or_failure": "Credentials leak, cross environments/accounts, remain valid after compromise, rotate non-atomically or cannot be recovered safely.",
      "current_evidence": ["SRC-09", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-15",
      "implemented_control": "S4A contains no credential and remains disabled; W9 records opaque-reference/custody requirements and unresolved key ownership.",
      "control_strength": "no_credential_runtime_plus_inherited_w9_requirements",
      "current_fail_closed_state": "No subscription provider credential is read and configuration alone cannot activate the edge.",
      "gap_id": "BG-15",
      "exact_missing_evidence": ["approved_target_secret_store_kms_or_equivalent_and_named_custodian", "environment_account_scope_and_least_privilege", "dual_secret_rotation_overlap_revocation_and_wrong_key_behavior", "access_audit_break_glass_backup_restore_and_incident_drill", "provider_sandbox_and_target_rotation_evidence"],
      "closure_owner_slices": ["W9-S2", "W9-S4", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-16",
      "title": "billing_log_pii_payload_or_secret_leakage",
      "assets": ["owner_identity", "billing_email", "provider_payload", "payment_metadata", "credentials", "audit"],
      "attack_or_failure": "Raw webhooks, provider objects, customer data, tokens or signatures enter logs, traces, errors, metrics, exports or long-lived evidence.",
      "current_evidence": ["SRC-08", "SRC-09", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-16",
      "implemented_control": "S3B retains only sanitised identifiers/digests/evidence references and prohibits raw payload/signature/secret retention; S4A exposes redacted structural fingerprints only.",
      "control_strength": "field_minimisation_contract_only",
      "current_fail_closed_state": "No webhook/provider runtime produces billing logs today; structural contracts reject credential-shaped retained fields.",
      "gap_id": "BG-16",
      "exact_missing_evidence": ["field_level_billing_data_and_log_allowlist", "application_worker_proxy_apm_metrics_and_support_export_redaction_tests", "error_and_malformed_payload_no_echo_tests", "retention_access_and_erasure_rules_for_audit_and_observability", "target_log_sink_review_and_secret_scanning"],
      "closure_owner_slices": ["W9-S3", "W9-S4", "W10-S3", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-17",
      "title": "event_inbox_database_integrity_or_concurrency_failure",
      "assets": ["billing_account", "subscription", "event_inbox", "receipt", "disposition", "entitlement_version"],
      "attack_or_failure": "Missing constraints, torn transactions, mutable history, worker races or migration drift lose, duplicate, corrupt or cross-link billing facts.",
      "current_evidence": ["SRC-07", "SRC-08", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-17",
      "implemented_control": "S3A/S3B define immutable structural identities, receipts, append-only dispositions and optimistic transition semantics only in memory.",
      "control_strength": "datastore_neutral_contract_no_database",
      "current_fail_closed_state": "There is no durable billing schema or event inbox to accept production data; structural ambiguity has zero direct effect.",
      "gap_id": "BG-17",
      "exact_missing_evidence": ["approved_w9_datastore_encryption_key_custody_retention_and_migration_decisions", "physical_owner_bound_schema_constraints_and_authenticated_integrity", "atomic_inbox_receipt_disposition_entitlement_transaction", "multi_worker_compare_and_set_deadlock_retry_and_crash_tests", "migration_rollback_restore_and_corruption_detection_evidence"],
      "closure_owner_slices": ["W9-S2", "W9-S3", "W10-S3", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-18",
      "title": "provider_outage_backlog_or_reconciliation_failure",
      "assets": ["checkout_availability", "event_backlog", "provider_ledger", "local_ledger", "customer_state"],
      "attack_or_failure": "Timeouts, delayed/missing events, backlog poison, provider outage or recovery order create false success, stale access or unreconciled money/state.",
      "current_evidence": ["SRC-08", "SRC-09", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-18",
      "implemented_control": "S4A is disabled and models provider facts as non-entitling; W9 has general local/synthetic outage contracts, but no billing-specific runtime or exercise.",
      "control_strength": "disabled_billing_edge_plus_inherited_general_outage_patterns",
      "current_fail_closed_state": "No checkout is offered and delayed/unknown structural observations cannot grant access; this is not a billing outage runbook.",
      "gap_id": "BG-18",
      "exact_missing_evidence": ["named_billing_operational_owner_alert_route_and_service_levels", "bounded_queue_backpressure_poison_isolation_retry_and_replay", "scheduled_provider_local_ledger_and_entitlement_reconciliation", "sandbox_outage_timeout_delayed_event_and_recovery_order_exercise", "target_tabletop_backlog_recovery_and_customer_copy"],
      "closure_owner_slices": ["W9-S4", "W10-S3", "W10-S4", "W10-S6", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-19",
      "title": "billing_deletion_retention_legal_hold_or_backup_expiry_failure",
      "assets": ["billing_account", "subscription", "invoice_receipt_reference", "event_audit", "provider_data", "backup"],
      "attack_or_failure": "Billing data is over-retained, prematurely deleted, incompletely erased, restored after deletion or held without approved authority.",
      "current_evidence": ["SRC-02", "SRC-08", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-19",
      "implemented_control": "S3B lists prohibited retention and future lifecycle gates; W9 records unresolved field-level retention, erasure, legal-hold and backup-expiry decisions.",
      "control_strength": "explicit_gap_only_no_durable_billing_data",
      "current_fail_closed_state": "No durable billing store is authorised; persistence must not begin before lifecycle and custody decisions.",
      "gap_id": "BG-19",
      "exact_missing_evidence": ["field_by_field_purpose_lawful_basis_retention_and_access_register", "tax_accounting_consumer_dispute_and_provider_retention_reconciliation", "approved_erasure_exception_legal_hold_and_audit_semantics", "idempotent_cross_store_provider_deletion_and_retry_tests", "backup_expiry_restore_exclusion_and_key_retirement_evidence"],
      "closure_owner_slices": ["W9-S2", "W9-S3", "W9-S5", "W10-S3", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-20",
      "title": "direct_url_api_or_route_classification_bypass",
      "assets": ["paid_surface_inventory", "server_route", "api", "entitlement_gate", "admin_boundary"],
      "attack_or_failure": "A user bypasses client hiding, reaches an unclassified/legacy/internal route, changes method/content negotiation or exploits inconsistent entitlement enforcement.",
      "current_evidence": ["SRC-06", "SRC-10", "SRC-11", "SRC-14", "SRC-15", "SRC-16"],
      "control_id": "BC-20",
      "implemented_control": "S5A inventories exact registered routes and S5B reconciles 11 unknown entries as evidence; S6C/D routes require authentication but not paid entitlement.",
      "control_strength": "source_bound_inventory_and_auth_only_preview",
      "current_fail_closed_state": "No paid boundary is approved or enforced; internal/legacy treatments remain recommendations, so existing auth-only reachability blocks launch rather than proving access control.",
      "gap_id": "BG-20",
      "exact_missing_evidence": ["answered_Q2_against_accepted_S5A_inventory", "implemented_S5B_route_hardening_with_refreshed_inventory", "central_server_side_default_deny_entitlement_guard", "all_method_direct_url_api_content_type_feature_flag_and_conditional_registration_tests", "admin_customer_separation_and_target_bypass_review"],
      "closure_owner_slices": ["W10-S2", "W10-S5", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    },
    {
      "id": "BT-21",
      "title": "unsafe_target_provider_or_production_activation",
      "assets": ["provider_mode", "credentials", "webhook_endpoint", "production_routes", "release_authority"],
      "attack_or_failure": "Configuration, credential presence, a green local suite or partial evidence silently enables charges, webhooks, portal, paid gating or production release.",
      "current_evidence": ["SRC-01", "SRC-02", "SRC-09", "SRC-17", "SRC-18", "SRC-19"],
      "control_id": "BC-21",
      "implemented_control": "S4A activation is disabled and configuration is not authority; W9/W10 maps preserve separate target, provider, independent-review, residual-risk and Founder release gates.",
      "control_strength": "disabled_contract_and_governance_gate_only",
      "current_fail_closed_state": "No billing provider SDK, credential, checkout, webhook, portal, charge or paid-access activation exists.",
      "gap_id": "BG-21",
      "exact_missing_evidence": ["immutable_launch_candidate_target_and_configuration_identity", "accepted_provider_terms_dpa_fees_account_mode_and_sandbox_matrix", "credential_webhook_route_database_monitoring_incident_and_recovery_target_evidence", "independent_security_privacy_legal_finance_tax_and_integrated_review", "residual_risk_disposition_and_explicit_founder_activation_release_go_live_authority"],
      "closure_owner_slices": ["W9-S5", "W10-S4", "W10-S7", "W10-S8"],
      "status": "open_not_security_or_launch_assurance"
    }
  ]
}
```
<!-- W10-S7A-REGISTER-END -->

## Cross-cutting closure sequence

The register does not reorder the W10 map. S2 must first obtain the applicable
specialist evidence and answers to Q1/Q2/Q3. S3 then needs the W9 datastore,
custody, minimisation, retention/erasure/backup and migration decisions before
durable billing state. S4 must authenticate provider observations at a
disabled-first edge. S5 must enforce only the approved Q2 boundary and preserve
independent admin controls. S6 must provide truthful failure/recovery journeys.
S7 must exercise the billing-specific operational controls in this register.
S8 must bind all evidence to the intended target and exact launch candidate.

The smallest present S7A outcome is this reviewable register and its integrity
test. It changes no runtime and closes no row. Each row remains
`open_not_security_or_launch_assurance` until its listed evidence is implemented,
exercised and independently accepted where required.

## Non-authority statement

This candidate performs no authentication, database or network access and uses
no credentials, provider account, customer data or production system. It does
not implement or expose checkout, portal, webhook, billing recovery, refund,
admin, entitlement or paid-route behavior. It does not select a datastore,
retention duration, key custodian, target runtime or provider configuration. It
does not answer Q1, Q2 or Q3, amend Founder Decisions or completion maps, close
W10-S7, assert security assurance, approve residual risk, authorise release or
make Reserved launch-ready.
