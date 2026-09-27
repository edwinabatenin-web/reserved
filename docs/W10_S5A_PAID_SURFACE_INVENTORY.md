# W10-S5A exact paid-surface inventory evidence

## Status and boundary

This is an exact live route inventory refreshed after the accepted linked-HICBC
mutual-permission lifecycle at integration commit
`91cb4c2f14bce089db1f92f656c8cbc1d85639b7` (tree
`a68a1120dfcc98295839bbea1f1c65c223376ec0`). It preserves the historical
inventory classification while recording the exact current route surface. The
later accepted W10-S2F policy settles the paid-access class. This inventory
itself does not decide which customer product surfaces require paid entitlement
or implement an entitlement gate.
The S5C prerequisite route hardening is implemented and remains pinned to its
historical product checkpoint `3c63e64e478957ce04ee1154363c2eae94b82b30`;
the paid-boundary policy is settled by accepted W10-S2F and the route-less S5D
guard kernel is implemented. The authoritative runtime adapter, route wiring
and live paid-entitlement enforcement remain **not started**, and W10-S5
remains incomplete. S5A is inventory evidence only.

The registry has 50 always-registered rules. Enabling the disabled-by-default
HICBC feature gate adds 10 owner-authenticated rules, producing 60 total. The
annual-preview rule additionally requires its own strict switch and denies
production; its paid classification does not wire runtime entitlement. Flask's
implicit `HEAD` and `OPTIONS` methods are omitted; the listed methods are the
declared customer-visible method set.

Every rule is assigned exactly one provisional evidence class:

- `public_infrastructure_auth_legal_support`: clearly public entry,
  infrastructure, authentication, legal/information or feedback/early-access
  support; this classification does not weaken its existing authentication,
  token, rate-limit or CSRF control.
- `authenticated_product_candidate_pending_founder_decision`: currently
  customer-session-guarded product behavior that is a candidate for the paid
  boundary, not a conclusion that access is free or paid.
- `billing_purchase_return_recovery_candidate`: a route that must remain
  reachable as appropriate to buy, return from, or recover billing access; the
  current registry contains only authenticated plan-preview/selection routes,
  not checkout, return, portal or billing recovery.
- `internal_admin_unknown_requiring_reconciliation`: the original provisional
  S5A class for privileged/internal, dormant or legacy product behavior. S5B
  has now reconciled all eleven entries and S5C hardened the five affected
  routes, but the class name and membership remain fixed so this refresh does
  not silently recategorise any route after the accepted W10-S2F policy closure.

`guard` records the observed route-level access mechanism. `csrf` records the
global state-changing-request protection or an explicit exemption; it is not an
entitlement decision. `registration=hicbc_feature_enabled` means the rule exists
only when `HICBC_ENABLED` is explicitly enabled.

## Machine-checkable inventory

<!-- W10-S5A-INVENTORY-BEGIN -->
```json
{
  "schema_version": "W10-S5A/2026-09-04/v3",
  "integration_commit": "91cb4c2f14bce089db1f92f656c8cbc1d85639b7",
  "integration_tree": "a68a1120dfcc98295839bbea1f1c65c223376ec0",
  "inventory_status": "evidence_only_paid_boundary_settled_elsewhere",
  "s5_status": "incomplete_guard_kernel_implemented_route_enforcement_not_started",
  "paid_boundary_status": "settled_by_w10_s2f",
  "paid_entitlement_enforcement_status": "guard_kernel_only_runtime_adapter_and_route_wiring_not_started",
  "route_hardening_changes": true,
  "route_counts": {
    "always": 50,
    "hicbc_feature_enabled_additional": 10,
    "hicbc_feature_enabled_total": 60
  },
  "classification_counts": {
    "public_infrastructure_auth_legal_support": 14,
    "authenticated_product_candidate_pending_founder_decision": 33,
    "billing_purchase_return_recovery_candidate": 2,
    "internal_admin_unknown_requiring_reconciliation": 11
  },
  "source_sha256": {
    "reserved/__init__.py": "d3ce81ff94f3bfe21329d5a678251319d2f021d36a618effd5a49d9426e051ad",
    "reserved/api/routes.py": "9d865764b222c0985b27c23707a7cea8a8327152795deb14e91a27feef081364",
    "reserved/auth.py": "adfe50a348a94e1f1a7405a41d92ec39b5d1a9db8c92b64222410701af39ae91",
    "reserved/config.py": "dd35367653820e5162aa7bdba6cdaeac47614ac072b5bceba0772c6f1c8374be",
    "reserved/extensions.py": "ef35d3ec969e299a1c8221b5636bcf44590189175b0ad0c83e88d38ded35b2a0",
    "reserved/web/founder.py": "f0568a760771f9847aeaa6f7e3349b7bda3a2fe861808f4ab3e856e40b90f67b",
    "reserved/web/hicbc.py": "efe0e59d6bd88ce44ae1f48a59aad9e01594b382c4b211a9a916508af6acd2f2",
    "reserved/web/routes.py": "cbac0af6c8e7fa7ef43017ba54dab0186330b556a6c9dd946e8cfcbd3fa0e9fd",
    "reserved/web/v2.py": "e2940b780b73fe8e583142fc35cbef53c983f2a0abdb2271bfd90e76e5ac6d16"
  },
  "routes": [
    {
      "endpoint": "web.dashboard",
      "rule": "/",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public entry redirect to the authenticated V2 entry flow."
    },
    {
      "endpoint": "web.about",
      "rule": "/about",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public product information."
    },
    {
      "endpoint": "api.health",
      "rule": "/api/health",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Infrastructure liveness/readiness probe."
    },
    {
      "endpoint": "web.calculate",
      "rule": "/calculate",
      "methods": ["POST"],
      "registration": "always",
      "guard": "always_404",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Retired legacy calculation action; valid-CSRF POST reaches an unconditional 404 before profile, calculation or rendering."
    },
    {
      "endpoint": "web.capital_gains",
      "rule": "/capital-gains",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "always_404",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Registered but deliberately dormant and outside current v1 scope."
    },
    {
      "endpoint": "web.connections",
      "rule": "/connections",
      "methods": ["GET"],
      "registration": "always",
      "guard": "redirect_to_customer_session_guarded_v2_equivalent",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Legacy GET contains no product content and redirects exactly to authenticated /v2/connections."
    },
    {
      "endpoint": "web.early_access",
      "rule": "/early-access",
      "methods": ["POST"],
      "registration": "always",
      "guard": "none",
      "csrf": "global",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public early-access/support registration."
    },
    {
      "endpoint": "favicon",
      "rule": "/favicon.ico",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public static infrastructure."
    },
    {
      "endpoint": "web.feedback",
      "rule": "/feedback",
      "methods": ["POST"],
      "registration": "always",
      "guard": "none",
      "csrf": "global",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public feedback/support submission."
    },
    {
      "endpoint": "founder.dashboard",
      "rule": "/founder/",
      "methods": ["GET"],
      "registration": "always",
      "guard": "founder_session",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Privileged Founder administration, not a customer entitlement surface."
    },
    {
      "endpoint": "founder.export_early_access",
      "rule": "/founder/export/early-access",
      "methods": ["GET"],
      "registration": "always",
      "guard": "founder_session",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Privileged export of registrations."
    },
    {
      "endpoint": "founder.export_feedback",
      "rule": "/founder/export/feedback",
      "methods": ["GET"],
      "registration": "always",
      "guard": "founder_session",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Privileged export of feedback."
    },
    {
      "endpoint": "founder.login",
      "rule": "/founder/login",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "founder_password_and_rate_limit",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Privileged administration authentication boundary."
    },
    {
      "endpoint": "founder.logout",
      "rule": "/founder/logout",
      "methods": ["POST"],
      "registration": "always",
      "guard": "founder_session",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Privileged administration session termination."
    },
    {
      "endpoint": "web.future",
      "rule": "/future",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public future-feature information."
    },
    {
      "endpoint": "web.privacy",
      "rule": "/privacy",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public privacy notice."
    },
    {
      "endpoint": "web.robots_txt",
      "rule": "/robots.txt",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Public crawler-control infrastructure."
    },
    {
      "endpoint": "web.settings",
      "rule": "/settings",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "get_redirect_to_customer_session_guarded_v2_equivalent_post_always_404",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Legacy GET redirects exactly to authenticated /v2/settings; valid-CSRF legacy POST unconditionally 404s before mutation."
    },
    {
      "endpoint": "static",
      "rule": "/static/<path:filename>",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Flask public static asset handler."
    },
    {
      "endpoint": "web.tax_assurance",
      "rule": "/tax-assurance",
      "methods": ["GET"],
      "registration": "always",
      "guard": "always_404",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Internal assurance page unconditionally 404s before reading metadata or rendering in every environment and auth state."
    },
    {
      "endpoint": "v2.index",
      "rule": "/v2/",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated product overview candidate."
    },
    {
      "endpoint": "v2.auth_verify",
      "rule": "/v2/auth/verify",
      "methods": ["POST"],
      "registration": "always",
      "guard": "clerk_session_token",
      "csrf": "exempt",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Authentication exchange; exemption relies on verified Clerk session token."
    },
    {
      "endpoint": "v2.connections",
      "rule": "/v2/connections",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated bank-connections product candidate."
    },
    {
      "endpoint": "v2.dashboard_view",
      "rule": "/v2/dashboard",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated dashboard product candidate."
    },
    {
      "endpoint": "v2.paye_manual_baseline",
      "rule": "/v2/paye/manual-baseline",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Independent strict switch and production denial; existing-user manual partial capture/review only. Paid classification, not runtime entitlement enforcement."
    },
    {
      "endpoint": "v2.paye_manual_journey",
      "rule": "/v2/paye/manual",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Disabled-by-default owner-bound structured manual PAYE evidence journey. Ordinary paid product surface."
    },
    {
      "endpoint": "v2.delete_paye_manual_journey_entry",
      "rule": "/v2/paye/manual/entries/<evidence_id>/delete",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Owner-bound deletion within the disabled-by-default manual PAYE journey. Ordinary paid product surface."
    },
    {
      "endpoint": "v2.paye_durable_current_position",
      "rule": "/v2/paye/current-position",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Disabled-first owner-bound structured manual PAYE current-position evidence read. A complete injected PAYE runtime supplies server-owned scope and annual inputs; the settled paid-access boundary remains independently mandatory."
    },
    {
      "endpoint": "v2.paye_durable_current_forecast",
      "rule": "/v2/paye/current-forecast",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Disabled-first owner-bound forecast over explicit confirmed future-pay inputs only. A complete injected forecast runtime supplies server-owned scope, annual position and future facts; the settled paid-access boundary remains independently mandatory."
    },
    {
      "endpoint": "hicbc.durable_current_annual_position",
      "rule": "/v2/hicbc/current-annual-position",
      "methods": ["GET"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Disabled-first owner-bound HICBC annual-position read. A complete injected durable HICBC runtime supplies server-owned scope and live annual inputs; the settled paid-access boundary remains independently mandatory."
    },
    {
      "endpoint": "v2.mtd_manual_scope",
      "rule": "/v2/mtd/scope-indication",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Independent strict disabled-first switch; existing-user self-reported unsaved manual scope indication only. Production-shaped access requires the separately installed owner-bound paid-entitlement runtime."
    },
    {
      "endpoint": "v2.demo_login",
      "rule": "/v2/demo-login",
      "methods": ["GET"],
      "registration": "always",
      "guard": "nonproduction_only",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Authentication helper disabled by the production dual lock."
    },
    {
      "endpoint": "v2.invoices",
      "rule": "/v2/invoices",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated invoice-matching product candidate, not subscription billing."
    },
    {
      "endpoint": "v2.invoices_seed",
      "rule": "/v2/invoices/seed",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated demo invoice-data action."
    },
    {
      "endpoint": "v2.login",
      "rule": "/v2/login",
      "methods": ["GET"],
      "registration": "always",
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "Customer authentication entry."
    },
    {
      "endpoint": "v2.logout",
      "rule": "/v2/logout",
      "methods": ["POST"],
      "registration": "always",
      "guard": "none",
      "csrf": "global",
      "classification": "public_infrastructure_auth_legal_support",
      "note": "CSRF-protected session clearing; no separate auth decorator."
    },
    {
      "endpoint": "v2.optimise_view",
      "rule": "/v2/optimise",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated optimisation product candidate."
    },
    {
      "endpoint": "v2.optimise_calculate",
      "rule": "/v2/optimise/calculate",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "exempt",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated optimisation calculation action; existing explicit CSRF exemption requires reconciliation."
    },
    {
      "endpoint": "v2.optimise_save_scenario",
      "rule": "/v2/optimise/save-scenario",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "exempt",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated scenario persistence action; existing explicit CSRF exemption requires reconciliation."
    },
    {
      "endpoint": "v2.optimise_delete_scenario",
      "rule": "/v2/optimise/saved/<int:scenario_id>",
      "methods": ["DELETE"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "exempt",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated scenario deletion; owner checks and existing CSRF exemption require preservation/review."
    },
    {
      "endpoint": "v2.billing_plans",
      "rule": "/v2/plans",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "billing_purchase_return_recovery_candidate",
      "note": "Authenticated inert plan preview; no checkout or provider action."
    },
    {
      "endpoint": "v2.billing_plan_selection",
      "rule": "/v2/plans/<path:plan_key>",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "billing_purchase_return_recovery_candidate",
      "note": "Authenticated inert plan-selection preview; no purchase or entitlement action."
    },
    {
      "endpoint": "v2.review_queue",
      "rule": "/v2/review",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated matching-review product candidate."
    },
    {
      "endpoint": "v2.sandbox_checklist",
      "rule": "/v2/sandbox-checklist",
      "methods": ["GET"],
      "registration": "always",
      "guard": "production_404_nonproduction_customer_session",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Production requests 404 before customer-session handling; non-production retains the existing customer-session guard."
    },
    {
      "endpoint": "v2.settings_page",
      "rule": "/v2/settings",
      "methods": ["GET", "POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated customer settings product candidate."
    },
    {
      "endpoint": "v2.transactions",
      "rule": "/v2/transactions",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated transaction product candidate."
    },
    {
      "endpoint": "v2.transactions_seed",
      "rule": "/v2/transactions/seed",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated demo transaction-data action."
    },
    {
      "endpoint": "v2.yapily_callback",
      "rule": "/v2/yapily/callback",
      "methods": ["GET"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Bank-consent callback, not a subscription billing return."
    },
    {
      "endpoint": "v2.yapily_connect",
      "rule": "/v2/yapily/connect",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated bank-consent action, not billing checkout."
    },
    {
      "endpoint": "v2.yapily_disconnect",
      "rule": "/v2/yapily/disconnect",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated bank-disconnection action."
    },
    {
      "endpoint": "v2.yapily_refresh",
      "rule": "/v2/yapily/refresh",
      "methods": ["POST"],
      "registration": "always",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Authenticated bank-refresh action."
    },
    {
      "endpoint": "hicbc.index",
      "rule": "/v2/hicbc/",
      "methods": ["GET"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated HICBC product candidate."
    },
    {
      "endpoint": "hicbc.delete_estimate",
      "rule": "/v2/hicbc/delete",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated HICBC deletion action."
    },
    {
      "endpoint": "hicbc.save_estimate",
      "rule": "/v2/hicbc/estimate",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated HICBC estimate action."
    },
    {
      "endpoint": "hicbc.link_page",
      "rule": "/v2/hicbc/link",
      "methods": ["GET", "POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated linked-account display and mutual-permission submission; the state-changing POST remains globally CSRF-protected."
    },
    {
      "endpoint": "hicbc.link_accept",
      "rule": "/v2/hicbc/link/accept",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated linked-account acceptance."
    },
    {
      "endpoint": "hicbc.link_invite",
      "rule": "/v2/hicbc/link/invite",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated linked-account invitation."
    },
    {
      "endpoint": "hicbc.link_revoke",
      "rule": "/v2/hicbc/link/revoke",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated linked-account revocation."
    },
    {
      "endpoint": "hicbc.result_json",
      "rule": "/v2/hicbc/result",
      "methods": ["GET"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated HICBC result API."
    },
    {
      "endpoint": "hicbc.annual_preview",
      "rule": "/v2/hicbc/annual-preview",
      "methods": ["POST"],
      "registration": "hicbc_feature_enabled",
      "guard": "production_404_nonproduction_customer_session",
      "csrf": "global",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Separate strict annual-preview switch; active linked accounts refused. No runtime paid guard or annual-total publication."
    }
  ]
}
```
<!-- W10-S5A-INVENTORY-END -->

## Observed gaps and ambiguous routes

There is no registered subscription checkout/session-creation route, billing
success/pending/failure return, Customer Portal route, billing webhook, invoice
or receipt route for Reserved's own subscription, billing-account recovery route,
or paid-entitlement enforcement hook. The two `/v2/plans` routes are inert
authenticated previews and do not purchase, charge or grant access. Yapily
routes concern bank-data consent and are not billing purchase/return routes;
the V2 invoice routes concern a customer's business invoices, not Reserved
subscription invoices.

The S5B reconciliation and S5C hardening now record:

- retired/hardened legacy product routes `/calculate`, `/connections` and
  `/settings`;
- the preserved always-404 `/capital-gains` route;
- the now always-404 internal `/tax-assurance` route;
- unchanged `/founder` administration/authentication/export boundaries; and
- production-404 plus non-production customer-session behavior for the
  internal `/v2/sandbox-checklist`.

This retained class does not expose or paid-gate those routes. It prevents them
from becoming an accidental exception by omission and is not a paid-boundary
decision.

## Settled paid-boundary policy and remaining engineering boundary

The formerly proposed default is now settled by accepted W10-S2F: enforce paid
entitlement server-side on every route classified
`authenticated_product_candidate_pending_founder_decision`, including the HICBC
routes whenever their separate feature gate is enabled. Keep
`public_infrastructure_auth_legal_support` and
`billing_purchase_return_recovery_candidate` outside the paid-entitlement gate
while preserving every current authentication, token, feature, rate-limit and
CSRF control. Treat `internal_admin_unknown_requiring_reconciliation` according
to its accepted S5B/S5C route-specific fail-closed treatment, never as an
implicit paid or free customer class.

The consequence is that customer-session authentication alone would no longer
authorise product access: a future server-side S5 implementation would also need
an approved, owner-bound entitlement decision and would fail closed for missing,
unknown, stale or unreconciled entitlement. Public/auth/legal/support and future
purchase/return/recovery paths would remain reachable enough to authenticate,
buy or recover, but would not gain product entitlement. Client-side hiding would
never substitute for server enforcement.

That Founder question is closed. The accepted S5D kernel represents the policy
without route authority. Remaining work is engineering: supply an authoritative
runtime-entitlement adapter and wire the guard to this exact paid route set,
with independent review and integrated assurance. No live enforcement claim is
made here.

## Assurance and limits

The accompanying tests parse this JSON, compare it with Flask's real route
registry with HICBC disabled and enabled, bind all route/auth/config/CSRF source
hashes, assert the exact endpoint membership and count of every classification,
and cross-check exact guard labels, route decorators and explicit CSRF
exemptions. App construction stubs database initialisation; tests call no route,
database, provider, network or credential path.

This inventory was regenerated after S5C because its bound route sources and
guards changed. It must be regenerated and reviewed again whenever any bound
source or registered route changes. Passing its tests proves inventory
freshness only. It does not independently settle policy, supply the runtime
adapter, wire or activate a paid-access gate, complete W10-S5, or provide launch
evidence.
