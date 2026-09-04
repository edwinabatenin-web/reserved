# W10-S5A exact paid-surface inventory evidence

## Status and boundary

This is an exact route inventory at clean integration commit
`6edf3cd6b96090f25036688e83da1d3b5295b098` (tree
`0d77f1853cc22a8c1e923552425478b7b9155cb2`). It is evidence for the still
unresolved W10 paid-access-surface decision. It does not decide which customer
product surfaces require paid entitlement, change any existing route or guard,
or make W10-S5 implemented. W10-S5 remains **not started**; S5A is inventory
evidence only.

The registry has 44 always-registered rules. Enabling the disabled-by-default
HICBC feature gate adds 8 owner-authenticated rules, producing 52 total. Flask's
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
- `internal_admin_unknown_requiring_reconciliation`: privileged/internal,
  dormant or legacy unguarded product behavior that cannot safely be assigned
  to either side of a customer paid boundary without reconciliation.

`guard` records the observed route-level access mechanism. `csrf` records the
global state-changing-request protection or an explicit exemption; it is not an
entitlement decision. `registration=hicbc_feature_enabled` means the rule exists
only when `HICBC_ENABLED` is explicitly enabled.

## Machine-checkable inventory

<!-- W10-S5A-INVENTORY-BEGIN -->
```json
{
  "schema_version": "W10-S5A/2026-09-04/v1",
  "integration_commit": "6edf3cd6b96090f25036688e83da1d3b5295b098",
  "integration_tree": "0d77f1853cc22a8c1e923552425478b7b9155cb2",
  "inventory_status": "evidence_only_no_paid_boundary_decision",
  "s5_status": "not_started",
  "paid_boundary_status": "unresolved_founder_decision",
  "enforcement_changes": false,
  "route_counts": {
    "always": 44,
    "hicbc_feature_enabled_additional": 8,
    "hicbc_feature_enabled_total": 52
  },
  "classification_counts": {
    "public_infrastructure_auth_legal_support": 14,
    "authenticated_product_candidate_pending_founder_decision": 25,
    "billing_purchase_return_recovery_candidate": 2,
    "internal_admin_unknown_requiring_reconciliation": 11
  },
  "source_sha256": {
    "reserved/__init__.py": "5f35d6d88542218cd8d5dbdac9662ef6711768ae5a3749a92d779325b42a2f34",
    "reserved/api/routes.py": "9d865764b222c0985b27c23707a7cea8a8327152795deb14e91a27feef081364",
    "reserved/auth.py": "adfe50a348a94e1f1a7405a41d92ec39b5d1a9db8c92b64222410701af39ae91",
    "reserved/config.py": "707e8fedb9b647fe86eff3158befed28d837640b46e84636369d9cdeffb9194a",
    "reserved/extensions.py": "ef35d3ec969e299a1c8221b5636bcf44590189175b0ad0c83e88d38ded35b2a0",
    "reserved/web/founder.py": "f0568a760771f9847aeaa6f7e3349b7bda3a2fe861808f4ab3e856e40b90f67b",
    "reserved/web/hicbc.py": "5eb230d3a894a70881b3d46e66c26eee67c1cd077529179229375ebb0ec2efa0",
    "reserved/web/routes.py": "cfe006a96c16c781db707bcf5c7e1d55250176a09bb02356ccc51b3abeaf91fa",
    "reserved/web/v2.py": "d91434e2fcf804c74a4154716cab5b1f4ac1642b8f3c90f895a7cf23428b0ca0"
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
      "guard": "none",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Legacy unguarded calculation product action; paid-boundary treatment is ambiguous."
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
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Legacy unguarded product page; reconcile with authenticated V2 equivalent."
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
      "guard": "none",
      "csrf": "global",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Legacy unguarded product settings; reconcile with authenticated V2 equivalent."
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
      "guard": "none",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Source identifies this as internal, but it has no route-level guard."
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
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "internal_admin_unknown_requiring_reconciliation",
      "note": "Source identifies this as an internal sandbox checklist."
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
      "methods": ["GET"],
      "registration": "hicbc_feature_enabled",
      "guard": "customer_session",
      "csrf": "not_applicable",
      "classification": "authenticated_product_candidate_pending_founder_decision",
      "note": "Feature-gated authenticated linked-account product candidate."
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

Reconciliation is mandatory for:

- legacy unguarded product routes `/calculate`, `/connections` and `/settings`;
- the registered but always-404 `/capital-gains` route;
- the unguarded source-labelled internal `/tax-assurance` route;
- all `/founder` administration/authentication/export routes; and
- the authenticated but source-labelled internal `/v2/sandbox-checklist`.

This class does not recommend exposing, removing or paid-gating those routes. It
prevents them from becoming an accidental exception by omission.

## Minimal Founder decision

**Recommended default:** once a paid-entitlement boundary exists, enforce it
server-side on every route classified
`authenticated_product_candidate_pending_founder_decision`, including the HICBC
routes whenever their separate feature gate is enabled. Keep
`public_infrastructure_auth_legal_support` and
`billing_purchase_return_recovery_candidate` outside the paid-entitlement gate
while preserving every current authentication, token, feature, rate-limit and
CSRF control. Do not treat `internal_admin_unknown_requiring_reconciliation` as
customer access in either direction until each route is separately reconciled.

The consequence is that customer-session authentication alone would no longer
authorise product access: a future server-side S5 implementation would also need
an approved, owner-bound entitlement decision and would fail closed for missing,
unknown, stale or unreconciled entitlement. Public/auth/legal/support and future
purchase/return/recovery paths would remain reachable enough to authenticate,
buy or recover, but would not gain product entitlement. Client-side hiding would
never substitute for server enforcement.

The exact minimal question is:

> For the October launch, approve server-side paid-entitlement enforcement on
> every route in `authenticated_product_candidate_pending_founder_decision`,
> while routes in `public_infrastructure_auth_legal_support` and
> `billing_purchase_return_recovery_candidate` remain outside that gate but keep
> their existing controls, and
> `internal_admin_unknown_requiring_reconciliation` remains excluded from
> customer access pending route-by-route reconciliation? If not, identify the
> exact route exceptions and intended treatment.

## Assurance and limits

The accompanying tests parse this JSON, compare it with Flask's real route
registry with HICBC disabled and enabled, bind all route/auth/config/CSRF source
hashes, assert the exact endpoint membership and count of every classification,
and cross-check exact guard labels, route decorators and explicit CSRF
exemptions. App construction stubs database initialisation; tests call no route,
database, provider, network or credential path.

This inventory must be regenerated and reviewed whenever any bound source or
registered route changes. Passing its tests proves inventory freshness only. It
does not approve the recommended default, decide entitlement, implement an
access gate, complete W10-S5, or provide launch evidence.
