# W10-S6C authenticated plan quote evidence

## Boundary

W10-S6C adds one authenticated, read-only `GET /v2/plans` page. It completes
the already-reviewed W10 chain from settled `FD-W10-001` authority through the
S6A presentation and S6B supported renderer into an authenticated preview page.

The route captures the exact settled authority, presenter and renderer at
module initialisation. The zero-argument route handler keeps the trusted
fragment supplier and template renderer in private closure state rather than
exposing either as callable defaults. Altering function defaults, keyword
defaults or dictionaries does not replace the registered handler's
collaborators. The otherwise mutable `functools.wraps` `__wrapped__` pointer is
removed from this registered route because Flask does not require it; adding a
hostile metadata value later is inert. The route accepts no plan, price,
discount, VAT, provider or payment input from the request. Query parameters are
inert. Only the fixed S6B fragment is marked as trusted internal HTML; the page
template does not use a general `safe` filter.

## Customer output

The available state contains exactly, in canonical order:

1. `£29 per month`
2. `£156 for six months`
3. `£288 per year`
4. `Prices include VAT where applicable.`

If the captured upstream authority or presentation cannot be validated, the
existing S6B fixed review-required fragment is rendered and no price or VAT
copy is shown.

The page states that purchasing a plan or changing access is unavailable in
the preview. It contains no checkout, payment, portal, lifecycle, discount,
entitlement or provider action. The dashboard adds exactly one price-free link
to the page.

## Security and side effects

The route uses the existing `require_auth` boundary. Unsupported modifying
methods are rejected by Flask routing. The application-wide `/v2/` security
policy supplies no-store, no-cache, expiry, cookie-vary, anti-sniffing,
clickjacking, permissions and CSP headers. Rendering performs no persistence,
network access, provider action or financial calculation in the billing/domain
boundary. As with other authenticated HTML pages, the shared Flask/Jinja CSRF
helper may initialise the session's `csrf_token` during the first rendered GET;
the focused regression explicitly enables CSRF and permits only that expected
session delta and no other change.

## Verification

`tests/test_w10_billing_plan_route.py` covers authentication, exact ordered
copy, query inertness, unsupported methods, security/cache headers, module
rebinding, tampered upstream fail-close behaviour, trusted-fragment handling,
decorated-function metadata substitution, dashboard-link uniqueness, absence
of billing/domain state or network actions, the narrowly expected CSRF session
initialisation, and prohibited billing controls/calculations.

The candidate remains uncommitted pending independent review.
