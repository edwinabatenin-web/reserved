# W10-S5B internal route reconciliation evidence

## Status and boundary

**Evidence cut-off:** 4 September 2026

**Repository HEAD:** `5612f7a33f27f09d1fa988f15dfdffbe77a72705`

**Repository tree:** `4786614d7ea428e3aea1d61a72dc74d9aad6bd92`

**Disposition:** local evidence candidate; independent review and integration
required.

This package reconciles the eleven routes classified
`internal_admin_unknown_requiring_reconciliation` by the accepted W10-S5A
inventory. It records their present registration, methods, observed guard, CSRF
posture, source, reachability, intended October category and smallest
fail-closed treatment. It changes no route or runtime behavior.

This is not a paid-surface decision, entitlement design or access-control
implementation. It does not expose a route, approve a current guard, weaken
authentication or CSRF, activate a provider, access credentials or data, or
make W10-S5 started or complete. The strict W10 completion denominator remains
0/8 and W10-S5 implementation remains **not started**.

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
this reconciliation.

## Exact accepted evidence

W10-S5A was introduced and independently accepted at
`9c0760192bb2420b90e57ec7313f69bbe52cbf74`. Its inventory is an exact snapshot
of integration commit `6edf3cd6b96090f25036688e83da1d3b5295b098`, tree
`0d77f1853cc22a8c1e923552425478b7b9155cb2`. The present integration
reconciliation at `5612f7a...` records S5A as accepted and directs S5B to
reconcile these eleven entries; it does not change the bound route sources.

| Evidence | SHA-256 | Use |
|---|---|---|
| `docs/W10_S5A_PAID_SURFACE_INVENTORY.md` | `abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8` | Exact accepted route/method/guard/CSRF inventory and existing paid-boundary question. |
| `tests/test_w10_paid_surface_inventory.py` | `0d1bec99ea12496a747906b69619df0d60cd339b870042573b7dc60158c060f6` | Inventory/source/registry freshness assurance. |
| `docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md` | `7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d` | Current W10 state and explicit S5B next action. |
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
  "schema_version": "W10-S5B/2026-09-04/v1",
  "repository_head": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
  "repository_tree": "4786614d7ea428e3aea1d61a72dc74d9aad6bd92",
  "accepted_s5a_commit": "9c0760192bb2420b90e57ec7313f69bbe52cbf74",
  "reconciliation_status": "evidence_only_no_runtime_change",
  "s5_status": "not_started",
  "paid_boundary_status": "unresolved_existing_s5a_founder_question",
  "new_founder_question_required": false,
  "source_sha256": {
    "FOUNDER_DECISIONS.md": "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
    "docs/API_CONTRACT_GAP_REPORT.md": "b0eeeea6357e88dd1db59dd5ddf2d4e4e712f79f73d3a61c52838cda390ac85f",
    "docs/TECHNICAL_ARCHITECTURE.md": "7307e93ff4a169516041a86485a1e994c52ed0afd2e120631257041b3fa09e79",
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8",
    "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d",
    "reserved/__init__.py": "5f35d6d88542218cd8d5dbdac9662ef6711768ae5a3749a92d779325b42a2f34",
    "reserved/providers/banking/yapily.py": "885d021f20f8a76b5f2d26ed692f1e2cae4a7c9764c885da286a61c1c2b68475",
    "reserved/security.py": "73a5d20f1aa69fafda1ab4a9d6c01668fc9a465686e2d8198f8649364e43ae2b",
    "reserved/templates/connections.html": "e58bf5d92892dd5c88f4df1dce6dc7b91b2fea30ebbe9878b8240e22262511e6",
    "reserved/templates/dashboard.html": "0bc3e2b3be86c3636eb811cb4ef20d56e9f51c24c01467ba6b6be8ae90757b8e",
    "reserved/templates/settings.html": "9a225d441ce4d055b982728836b54df46914ba6329f099c28a9c709c46e554e7",
    "reserved/templates/tax_assurance.html": "ea7e838a32da6738be947892b6280b6e16367b369c43f85dc9dee74ce007b83e",
    "reserved/templates/v2/sandbox_checklist.html": "dad35c55d8557e114db120e9dfd8108503e3b8d5c834b0a48f5edb2bda1f6d38",
    "reserved/web/founder.py": "f0568a760771f9847aeaa6f7e3349b7bda3a2fe861808f4ab3e856e40b90f67b",
    "reserved/web/routes.py": "cfe006a96c16c781db707bcf5c7e1d55250176a09bb02356ccc51b3abeaf91fa",
    "reserved/web/v2.py": "d91434e2fcf804c74a4154716cab5b1f4ac1642b8f3c90f895a7cf23428b0ca0",
    "tests/test_w10_paid_surface_inventory.py": "0d1bec99ea12496a747906b69619df0d60cd339b870042573b7dc60158c060f6"
  },
  "routes": [
    {
      "endpoint": "web.calculate",
      "rule": "/calculate",
      "methods": ["POST"],
      "registration": "always",
      "current_guard": "none",
      "csrf": "global",
      "source": "reserved/web/routes.py",
      "handler": "calculate",
      "current_reachability": "public_post_with_valid_csrf_reaches_legacy_calculation",
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
      "current_guard": "none",
      "csrf": "not_applicable",
      "source": "reserved/web/routes.py",
      "handler": "connections",
      "current_reachability": "public_get_renders_legacy_illustrative_connections",
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
      "current_guard": "none",
      "csrf": "global",
      "source": "reserved/web/routes.py",
      "handler": "settings",
      "current_reachability": "public_get_and_valid_csrf_post_updates_session_or_authenticated_owner_profile",
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
      "current_guard": "none",
      "csrf": "not_applicable",
      "source": "reserved/web/routes.py",
      "handler": "tax_assurance",
      "current_reachability": "public_get_reads_local_assurance_metadata_and_renders_internal_page",
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
      "current_guard": "customer_session",
      "csrf": "not_applicable",
      "source": "reserved/web/v2.py",
      "handler": "sandbox_checklist",
      "current_reachability": "any_authenticated_customer_can_view_provider_mode_and_secret_presence_booleans",
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

`web.calculate` is an always-registered public POST. Global CSRF protects the
method, but there is no customer-session guard. The handler accepts an invoice
amount, resolves the legacy profile/default, calculates and renders the legacy
dashboard. The current root redirects to the authenticated V2 entry, so this
orphaned action is not needed as a separate October surface. It is not proven to
be the separately Founder-authorised Simplified Tax Health Check and must not be
relabelled as that tool. Remove its registration or make it production-404 until
it is deliberately authenticated and classified against the paid boundary.

`web.connections` publicly renders hard-coded illustrative connection states,
including account labels and balances. The separately authenticated
`v2.connections` is already the canonical product candidate. The legacy GET
should contain no independent content: redirect it into the authenticated V2
path, where the still-unresolved paid-surface decision will apply.

`web.settings` publicly renders and accepts profile fields. A valid-CSRF
unauthenticated POST writes session state; an authenticated POST may also write
the current owner's profile. The authenticated `v2.settings_page` is the
canonical product candidate. Redirect the legacy GET to that authenticated path
and disable the legacy POST so it cannot bypass later entitlement enforcement or
maintain a second validation/persistence contract.

These are fail-closed engineering cleanups. They do not decide whether their
canonical authenticated counterparts require paid entitlement.

### Explicitly excluded or internal-only routes

`web.capital_gains` aborts with 404 before its dormant implementation. Capital
Gains is explicitly outside the Founder-settled October calculation and
customer-facing scope. Preserve the leading hard-404. Moving the abort or
reactivating the dormant body requires a later Founder scope decision; keeping
it closed does not.

`web.tax_assurance` is labelled internal/dev-only in source and presentation,
but is currently a public GET. It reads local assurance metadata and renders
test counts, release status, scope assumptions and a reference persona. It is
not customer product or launch assurance. Return 404 in production. In a
non-production environment, expose it only through a separately reviewed
staff/internal authentication boundary; if none exists, keep it 404.

`v2.sandbox_checklist` has customer-session authentication but no staff or
non-production gate. It constructs a network-inert `YapilyClient` for mode and
credential-presence booleans and presents provider activation steps. It does
not expose secret values, but customer authentication is not internal-operator
authorisation. Return 404 in production. Outside production, require separate
staff/internal access or keep it 404. Never treat this page, a credential-presence
indicator or its checklist as provider/target readiness authority.

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

The eventual cleanup must preserve one-owner-at-a-time control over the route
modules and shared templates. In particular:

- do not edit the accepted S5A inventory as a substitute for changing code;
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

After independent review, the smallest implementation package is a route-only
fail-closed cleanup: preserve Capital Gains 404 and the five Founder guards;
retire or redirect the three legacy public routes without creating a paid-
surface answer; and production-404 the two internal pages. That package must
enumerate route/template ownership, preserve current security controls, add
negative runtime tests, and refresh the accepted inventories. It remains
separate from entitlement enforcement and launch activation.

## Assurance method and limits

The accompanying test parses the accepted S5A and S5B JSON records, binds every
reviewed source hash, requires the exact eleven-entry set, and fixes every
route/method/guard/CSRF/category/treatment/decision tuple. Static AST/source
checks confirm the route and guard decorators plus the critical hard-404,
session, export, no-store and provider-presence behaviors. It imports no Reserved
runtime module and creates no app or request. No database, network, environment
credential or provider code path is exercised.

Passing proves that this evidence still matches the exact source snapshot. It
does not prove target reachability, current deployment settings, privileged
credential custody, a paid-boundary decision, entitlement enforcement, provider
readiness, customer journey quality or launch readiness.
