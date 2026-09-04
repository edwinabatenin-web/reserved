# W10-S5B internal route reconciliation evidence

## Status and boundary

**Evidence cut-off:** 4 September 2026

**Live source checkpoint:**
`c5e560045ed3d62f02c894e931464c3d7294e99f` (tree
`bcdbec9108c3c0904139eca278c03fe0f6914db2`)

**Accepted S5C product checkpoint:**
`3c63e64e478957ce04ee1154363c2eae94b82b30`

**Accepted S5C product tree:**
`ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7`

**Product disposition:** independently accepted and integrated. This evidence
refresh remains a local candidate requiring its own independent review and
integration.

This package reconciles the eleven routes classified
`internal_admin_unknown_requiring_reconciliation` by the accepted W10-S5A
inventory. It records their present registration, methods, observed guard, CSRF
posture, source, reachability, intended October category and smallest
fail-closed treatment, including its exact current implementation as the
accepted S5C fail-closed cleanup at the
accepted S5C product checkpoint. This evidence refresh changes no route or
runtime behavior.

This is not a paid-surface decision, entitlement design or access-control
implementation. It does not expose a route, approve a current guard, weaken
authentication or CSRF, activate a provider, access credentials or data, or
make a paid-boundary decision or complete W10-S5. The prerequisite route
hardening is implemented; the paid-boundary decision and paid-entitlement
enforcement remain **not started**, and W10-S5 remains incomplete.

## Result

No additional Founder question is created by these eleven reconciliations:

- five `/founder` endpoints are privileged administration and must remain
  outside the customer subscription boundary while preserving their current
  Founder authentication/session controls;
- `web.capital_gains` is already hard-404 and Capital Gains is expressly outside
  October scope;
- `web.calculate`, `web.connections` and `web.settings` are legacy public
  product paths that must not remain independent paid-gate bypasses;
- `web.tax_assurance` and `v2.sandbox_checklist` are source-labelled internal
  evidence/operations pages and must not be customer-reachable in production.

The accepted S5A Founder question still governs which authenticated customer
product surfaces are paid. This evidence neither answers nor restates that
question. None of the routes below becomes a free or paid customer product by
this reconciliation or by S5C hardening.

## Exact accepted evidence

W10-S5A was introduced and independently accepted at
`9c0760192bb2420b90e57ec7313f69bbe52cbf74`. Its inventory is an exact snapshot
of integration commit `6edf3cd6b96090f25036688e83da1d3b5295b098`, tree
`0d77f1853cc22a8c1e923552425478b7b9155cb2`. The completion-map reconciliation
at `5612f7a...` records S5A as accepted and directs S5B to reconcile these
eleven entries. S5B was independently accepted and integrated at
`051ae665a0cc94f6e9cdbbc728c621825c7769fe`; S5C then implemented and
independently accepted the bounded route treatment at the exact checkpoint
above. The historical completion-map reference remains bound to its Git blob
rather than being silently reinterpreted as current runtime evidence.

| Evidence | SHA-256 | Use |
|---|---|---|
| `docs/W10_S5A_PAID_SURFACE_INVENTORY.md` | `5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601` | Refreshed exact route/method/guard/CSRF inventory; preserves the existing paid-boundary question. |
| `tests/test_w10_paid_surface_inventory.py` | `adf2044d4c72bb7985e4fed90ecb771aa1d88719bb39aac9ce47c70c4371b512` | Refreshed inventory/source/registry freshness assurance. |
| `5612f7a...:docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md` | `7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d` | Historical W10 state and explicit S5B next action, verified from the Git blob. |
| `FOUNDER_DECISIONS.md` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | October scope, paid-subscription authority and ordinary-engineering authority. |
| `docs/TECHNICAL_ARCHITECTURE.md` | `7307e93ff4a169516041a86485a1e994c52ed0afd2e120631257041b3fa09e79` | Capital Gains dormant/out-of-scope and launch-layer boundary. |
| `docs/API_CONTRACT_GAP_REPORT.md` | `b0eeeea6357e88dd1db59dd5ddf2d4e4e712f79f73d3a61c52838cda390ac85f` | Current implementation-derived HTTP classification; Founder area is not a public API. |

Source hashes in the machine record below bind the exact code and presentation
reviewed. Any change requires regeneration and review rather than carrying this
disposition forward by name alone.

## Machine-checkable reconciliation

<!-- W10-S5B-RECONCILIATION-BEGIN -->
```json
{
  "schema_version": "W10-S5B/2026-09-04/v2",
  "repository_head": "c5e560045ed3d62f02c894e931464c3d7294e99f",
  "repository_tree": "bcdbec9108c3c0904139eca278c03fe0f6914db2",
  "accepted_s5a_commit": "9c0760192bb2420b90e57ec7313f69bbe52cbf74",
  "accepted_s5b_commit": "051ae665a0cc94f6e9cdbbc728c621825c7769fe",
  "accepted_s5c_product_checkpoint": "3c63e64e478957ce04ee1154363c2eae94b82b30",
  "accepted_s5c_product_tree": "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7",
  "reconciliation_status": "accepted_reconciliation_with_implemented_s5c_treatments",
  "evidence_refresh_status": "candidate_requires_independent_review",
  "s5_status": "incomplete_prerequisite_route_hardening_implemented",
  "paid_boundary_status": "unresolved_existing_s5a_founder_question",
  "paid_entitlement_enforcement_status": "not_started",
  "new_founder_question_required": false,
  "historical_completion_map_blob": {
    "commit": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
    "path": "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
    "sha256": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d"
  },
  "source_sha256": {
    "FOUNDER_DECISIONS.md": "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
    "docs/API_CONTRACT_GAP_REPORT.md": "b0eeeea6357e88dd1db59dd5ddf2d4e4e712f79f73d3a61c52838cda390ac85f",
    "docs/TECHNICAL_ARCHITECTURE.md": "7307e93ff4a169516041a86485a1e994c52ed0afd2e120631257041b3fa09e79",
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "64894dbfb74b0faa16b8b4c824f79b021675caf57a391c9a19c269a0f914c7c9",
    "reserved/__init__.py": "5f35d6d88542218cd8d5dbdac9662ef6711768ae5a3749a92d779325b42a2f34",
    "reserved/providers/banking/yapily.py": "885d021f20f8a76b5f2d26ed692f1e2cae4a7c9764c885da286a61c1c2b68475",
    "reserved/security.py": "73a5d20f1aa69fafda1ab4a9d6c01668fc9a465686e2d8198f8649364e43ae2b",
    "reserved/templates/connections.html": "e58bf5d92892dd5c88f4df1dce6dc7b91b2fea30ebbe9878b8240e22262511e6",
    "reserved/templates/dashboard.html": "0bc3e2b3be86c3636eb811cb4ef20d56e9f51c24c01467ba6b6be8ae90757b8e",
    "reserved/templates/settings.html": "9a225d441ce4d055b982728836b54df46914ba6329f099c28a9c709c46e554e7",
    "reserved/templates/tax_assurance.html": "ea7e838a32da6738be947892b6280b6e16367b369c43f85dc9dee74ce007b83e",
    "reserved/templates/v2/sandbox_checklist.html": "dad35c55d8557e114db120e9dfd8108503e3b8d5c834b0a48f5edb2bda1f6d38",
    "reserved/web/founder.py": "f0568a760771f9847aeaa6f7e3349b7bda3a2fe861808f4ab3e856e40b90f67b",
    "reserved/web/routes.py": "cbac0af6c8e7fa7ef43017ba54dab0186330b556a6c9dd946e8cfcbd3fa0e9fd",
    "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
    "tests/test_w10_paid_surface_inventory.py": "aa1c40ad19dc737df07ec24cc9304ece57ad27f741694b6b4688400c7e448c87"
  },
  "s5c_implemented_treatments": {
    "web.calculate": {
      "status": "implemented_at_accepted_s5c_product_checkpoint",
      "treatment": "registered_post_hard_404_before_profile_calculation_or_render"
    },
    "web.connections": {
      "status": "implemented_at_accepted_s5c_product_checkpoint",
      "treatment": "get_redirects_exactly_to_customer_session_guarded_v2_connections_with_no_independent_content"
    },
    "web.settings": {
      "status": "implemented_at_accepted_s5c_product_checkpoint",
      "treatment": "get_redirects_exactly_to_customer_session_guarded_v2_settings_and_valid_csrf_post_hard_404s_before_mutation"
    },
    "web.tax_assurance": {
      "status": "implemented_at_accepted_s5c_product_checkpoint",
      "treatment": "hard_404_before_metadata_read_or_render_in_all_environments_and_auth_states"
    },
    "v2.sandbox_checklist": {
      "status": "implemented_at_accepted_s5c_product_checkpoint",
      "treatment": "production_404_before_customer_auth_or_provider_construction_nonproduction_existing_customer_session_guard_preserved"
    }
  },
  "routes": [
    {
      "endpoint": "web.calculate",
      "rule": "/calculate",
      "methods": ["POST"],
      "registration": "always",
      "current_guard": "always_404",
      "csrf": "global",
      "source": "reserved/web/routes.py",
      "handler": "calculate",
      "current_reachability": "valid_csrf_post_is_404_before_profile_calculation_or_render",
      "october_category": "legacy_product_action_not_independent_october_surface",
      "recommended_treatment": "remove_registration_or_production_404_until_separately_authenticated_and_classified",
      "decision_class": "ordinary_fail_closed_engineering_cleanup",
      "collision_security_risks": [
        "customer_authentication_and_future_paid_gate_bypass",
        "duplicate_calculation_and_customer_presentation_contract",
        "orphaned_legacy_form_action_can_be_called_directly"
      ]
    },
    {
      "endpoint": "web.capital_gains",
      "rule": "/capital-gains",
      "methods": ["GET", "POST"],
      "registration": "always",
      "current_guard": "always_404",
      "csrf": "global",
      "source": "reserved/web/routes.py",
      "handler": "capital_gains",
      "current_reachability": "get_is_404_and_post_is_404_after_global_csrf",
      "october_category": "excluded_capital_gains_dormant",
      "recommended_treatment": "keep_dormant_always_404_for_october",
      "decision_class": "settled_founder_scope_preservation",
      "collision_security_risks": [
        "moving_or_removing_leading_abort_would_reactivate_dormant_code",
        "reactivation_would_conflict_with_explicit_october_scope"
      ]
    },
    {
      "endpoint": "web.connections",
      "rule": "/connections",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "redirect_to_customer_session_guarded_v2_equivalent",
      "csrf": "not_applicable",
      "source": "reserved/web/routes.py",
      "handler": "connections",
      "current_reachability": "public_get_redirects_exactly_to_customer_session_guarded_v2_connections",
      "october_category": "legacy_alias_to_authenticated_connections_product",
      "recommended_treatment": "redirect_get_to_customer_authenticated_v2_connections_no_independent_content",
      "decision_class": "ordinary_fail_closed_engineering_cleanup",
      "collision_security_risks": [
        "customer_authentication_and_future_paid_gate_bypass",
        "hard_coded_connected_accounts_and_balances_can_be_misread_as_customer_facts",
        "legacy_provider_copy_can_diverge_from_accepted_october_scope"
      ]
    },
    {
      "endpoint": "web.settings",
      "rule": "/settings",
      "methods": ["GET", "POST"],
      "registration": "always",
      "current_guard": "get_redirect_to_customer_session_guarded_v2_equivalent_post_always_404",
      "csrf": "global",
      "source": "reserved/web/routes.py",
      "handler": "settings",
      "current_reachability": "public_get_redirects_exactly_to_customer_session_guarded_v2_settings_and_valid_csrf_post_is_404_before_mutation",
      "october_category": "legacy_alias_to_authenticated_customer_settings_product",
      "recommended_treatment": "redirect_get_to_customer_authenticated_v2_settings_and_disable_legacy_post",
      "decision_class": "ordinary_fail_closed_engineering_cleanup",
      "collision_security_risks": [
        "customer_authentication_and_future_paid_gate_bypass",
        "unauthenticated_profile_state_mutation",
        "duplicate_validation_persistence_and_customer_presentation_contract"
      ]
    },
    {
      "endpoint": "web.tax_assurance",
      "rule": "/tax-assurance",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "always_404",
      "csrf": "not_applicable",
      "source": "reserved/web/routes.py",
      "handler": "tax_assurance",
      "current_reachability": "get_is_404_before_metadata_read_or_render_in_all_environments_and_auth_states",
      "october_category": "internal_assurance_noncustomer_nonproduction",
      "recommended_treatment": "production_404_and_nonproduction_staff_authenticated_only",
      "decision_class": "ordinary_security_engineering_cleanup",
      "collision_security_risks": [
        "public_internal_release_and_test_metadata_disclosure",
        "stale_local_metadata_can_be_misread_as_launch_assurance",
        "internal_scope_assumptions_and_reference_persona_are_customer_exposed"
      ]
    },
    {
      "endpoint": "founder.dashboard",
      "rule": "/founder/",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "founder_session",
      "csrf": "not_applicable",
      "source": "reserved/web/founder.py",
      "handler": "dashboard",
      "current_reachability": "founder_session_required_otherwise_redirect_to_founder_login",
      "october_category": "founder_only_privileged_administration",
      "recommended_treatment": "keep_founder_only_outside_customer_paid_boundary_and_preserve_no_store",
      "decision_class": "ordinary_privilege_boundary_preservation",
      "collision_security_risks": [
        "customer_subscription_gate_must_not_grant_or_block_founder_privilege",
        "dashboard_contains_personal_feedback_and_registration_data",
        "founder_and_customer_sessions_must_remain_distinct"
      ]
    },
    {
      "endpoint": "founder.export_early_access",
      "rule": "/founder/export/early-access",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "founder_session",
      "csrf": "not_applicable",
      "source": "reserved/web/founder.py",
      "handler": "export_early_access",
      "current_reachability": "founder_session_required_personal_data_csv_download",
      "october_category": "founder_only_sensitive_personal_data_export",
      "recommended_treatment": "keep_founder_only_preserve_no_store_and_spreadsheet_safe_csv",
      "decision_class": "ordinary_privilege_boundary_preservation",
      "collision_security_risks": [
        "personal_registration_data_exfiltration",
        "spreadsheet_formula_injection_if_export_sanitisation_regresses",
        "customer_paid_status_must_never_authorise_export"
      ]
    },
    {
      "endpoint": "founder.export_feedback",
      "rule": "/founder/export/feedback",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "founder_session",
      "csrf": "not_applicable",
      "source": "reserved/web/founder.py",
      "handler": "export_feedback",
      "current_reachability": "founder_session_required_personal_data_csv_download",
      "october_category": "founder_only_sensitive_personal_data_export",
      "recommended_treatment": "keep_founder_only_preserve_no_store_and_spreadsheet_safe_csv",
      "decision_class": "ordinary_privilege_boundary_preservation",
      "collision_security_risks": [
        "personal_feedback_data_exfiltration",
        "spreadsheet_formula_injection_if_export_sanitisation_regresses",
        "customer_paid_status_must_never_authorise_export"
      ]
    },
    {
      "endpoint": "founder.login",
      "rule": "/founder/login",
      "methods": ["GET", "POST"],
      "registration": "always",
      "current_guard": "founder_password_and_rate_limit",
      "csrf": "global",
      "source": "reserved/web/founder.py",
      "handler": "login",
      "current_reachability": "public_login_form_and_valid_csrf_password_post_with_persistent_rate_limit",
      "october_category": "founder_only_privileged_authentication_entry",
      "recommended_treatment": "keep_founder_admin_entry_outside_customer_paid_boundary_preserve_rate_limit_and_clean_session",
      "decision_class": "ordinary_privilege_boundary_preservation",
      "collision_security_risks": [
        "single_privileged_password_and_target_secret_custody_require_separate_assurance",
        "customer_identity_or_entitlement_must_never_substitute_for_founder_authentication",
        "rate_limit_or_session_cleaning_regression_would_weaken_privilege_boundary"
      ]
    },
    {
      "endpoint": "founder.logout",
      "rule": "/founder/logout",
      "methods": ["POST"],
      "registration": "always",
      "current_guard": "founder_session",
      "csrf": "global",
      "source": "reserved/web/founder.py",
      "handler": "logout",
      "current_reachability": "founder_session_and_global_csrf_required_then_entire_session_cleared",
      "october_category": "founder_only_privileged_session_termination",
      "recommended_treatment": "keep_founder_only_post_csrf_full_session_clear_outside_customer_paid_boundary",
      "decision_class": "ordinary_privilege_boundary_preservation",
      "collision_security_risks": [
        "get_or_csrf_exemption_would_enable_cross_site_logout",
        "partial_session_clear_could_mix_founder_customer_or_oauth_state",
        "customer_paid_status_must_not_affect_founder_session_termination"
      ]
    },
    {
      "endpoint": "v2.sandbox_checklist",
      "rule": "/v2/sandbox-checklist",
      "methods": ["GET"],
      "registration": "always",
      "current_guard": "production_404_nonproduction_customer_session",
      "csrf": "not_applicable",
      "source": "reserved/web/v2.py",
      "handler": "sandbox_checklist",
      "current_reachability": "production_404_before_customer_auth_or_provider_construction_nonproduction_customer_session_required",
      "october_category": "internal_provider_assurance_noncustomer_nonproduction",
      "recommended_treatment": "production_404_and_nonproduction_staff_authenticated_only_not_readiness_authority",
      "decision_class": "ordinary_security_engineering_cleanup",
      "collision_security_risks": [
        "customer_authentication_is_not_staff_authorisation",
        "provider_mode_and_credential_presence_disclosure",
        "internal_activation_instructions_can_be_misread_as_approved_readiness_evidence"
      ]
    }
  ]
}
```
<!-- W10-S5B-RECONCILIATION-END -->

## Route findings

### Legacy public product paths

`web.calculate` remains registered as POST so the route shape is stable, with
global CSRF still preceding the handler. A valid-CSRF request now hard-404s
before profile access, calculation or rendering. It is not the separately
Founder-authorised Simplified Tax Health Check and is not an independent
October customer surface.

`web.connections` now contains no independent content. Its GET redirects
exactly to `v2.connections`; that canonical route retains customer-session
authentication and remains subject to the still-unresolved paid-surface
decision.

`web.settings` GET now redirects exactly to authenticated `v2.settings_page`.
The registered legacy POST retains global CSRF and, after a valid token,
hard-404s before session or owner-profile mutation. The legacy route therefore
has no second validation, persistence or customer-presentation contract.

These are fail-closed engineering cleanups. They do not decide whether their
canonical authenticated counterparts require paid entitlement.

### Explicitly excluded or internal-only routes

`web.capital_gains` aborts with 404 before its dormant implementation. Capital
Gains is explicitly outside the Founder-settled October calculation and
customer-facing scope. Preserve the leading hard-404. Moving the abort or
reactivating the dormant body requires a later Founder scope decision; keeping
it closed does not.

`web.tax_assurance` is not customer product or launch assurance. Because no
separately authenticated staff boundary exists, its GET now hard-404s before
metadata access or rendering in production and non-production, for both
unauthenticated and customer-authenticated sessions. Its dormant body grants no
reachability.

`v2.sandbox_checklist` now hard-404s in production through the existing
authoritative production check before customer-session handling or
`YapilyClient` construction. In non-production it retains its existing
customer-session guard and network-inert checklist behavior. That retained
development access is not staff authorisation, provider activation, target
evidence or readiness authority.

### Founder-only administration

The five Founder routes form a separate privileged administration boundary, not
a customer subscription surface:

- `founder.login` is the public entry to password verification, persistent
  IP-rate limiting and a clean Founder session. Preserve global CSRF, constant-
  time password comparison, rate limiting and pre-login session clearing.
- `founder.dashboard` requires the Founder session and renders feedback and
  early-access records.
- `founder.export_feedback` and `founder.export_early_access` require the Founder
  session and export personal data. Preserve the prefix-level no-store headers
  and `spreadsheet_safe_row` sanitisation.
- `founder.logout` remains POST-only, globally CSRF-protected and Founder-
  session-bound, and clears the entire session.

A future customer paid-entitlement gate must neither grant these privileges nor
block the Founder authentication/administration path. Keeping this separation is
ordinary privilege-boundary engineering under `FD-OA-001`, not a product choice.
Target secret custody, stronger privileged authentication, export governance and
operational assurance remain W9/W10-S7/S8 gates; this reconciliation does not
claim they are launch-ready.

## Collision and implementation boundaries

The implemented cleanup and any later paid-boundary work must preserve
one-owner-at-a-time control over route modules and shared templates. In
particular:

- do not treat refreshed S5A/S5B evidence as product authority;
- do not add paid entitlement to Founder routes or use customer subscription
  state as Founder authentication;
- do not implement the unresolved customer paid boundary while retiring legacy
  aliases;
- do not weaken global CSRF, customer authentication, Founder authentication,
  session clearing, no-store headers, rate limiting or CSV sanitisation;
- do not make the assurance/sandbox routes production-visible merely because a
  provider credential or environment flag exists;
- do not reactivate dormant Capital Gains code; and
- regenerate S5A/S5B evidence if any bound route, guard, template or source
  changes.

## Decision and next package

**New Founder action required by S5B: no.** The existing accepted S5A
paid-surface question remains unanswered and is still required before customer
paid-boundary implementation. A new Founder question would arise only if a
future proposal sought to put Capital Gains into October scope, make an internal
assurance route a customer feature, expose Founder administration to customer
identities, or preserve a legacy route as an independent customer product.

The independently accepted route-only S5C package implemented the prerequisite
cleanup: Capital Gains and all Founder boundaries are unchanged; the three
legacy paths are retired or redirected without a paid-surface answer;
`tax-assurance` is closed because no staff boundary exists; and the sandbox
checklist is production-404 while retaining its non-production customer-session
guard. The next S5 implementation package is still gated by Founder Q2 and must
implement server-side paid-entitlement enforcement separately.

## Assurance method and limits

The accompanying test parses the refreshed S5A and S5B JSON records, binds every
reviewed current source hash, verifies the historical completion-map Git blob,
requires the exact eleven-entry set, and fixes every route/method/guard/CSRF/
category/recommendation/decision tuple plus the five implemented treatments.
Static AST/source checks confirm the critical hard-404, redirect, production
gate, session, export and no-store behavior. It imports no Reserved runtime
module and creates no app or request. No database, network, environment
credential or provider code path is exercised.

Passing proves that this evidence matches the accepted S5C product snapshot. It
does not prove target reachability, current deployment settings, privileged
credential custody, a paid-boundary decision, paid-entitlement enforcement,
provider readiness, customer journey quality or launch readiness.
