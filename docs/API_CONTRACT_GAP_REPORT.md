# Reserved HTTP API and contract gap report

**Inventory date:** 13 August 2026  
**Status:** implementation-derived; not a promise of a public or partner API

## Executive finding

Reserved does not currently expose a general tax-calculation API. The only
route mounted below `/api` is the service/database health probe. The other
machine-consumed endpoints are implementation details of the browser
application and currently sit below `/`, `/v2`, or `/founder`.

`docs/openapi.json` documents the routes for which the current code establishes
a concrete HTTP request/response contract. It must not be read as a commitment
that those routes are stable or available to third parties.

## HTTP route inventory

| Area | Routes | Current contract |
|---|---|---|
| Service probe | `GET /api/health` | JSON; database-backed readiness and liveness combined |
| Public forms | `POST /feedback`, `POST /early-access` | Form input, JSON output, CSRF and Turnstile protected, IP-rate-limited |
| Public HTML | `GET /`, `/connections`, `/about`, `/privacy`, `/future`, `/tax-assurance`, `/robots.txt`; `GET/POST /settings`, `/capital-gains`; `POST /calculate` | Browser pages or redirects, not an API. Capital Gains always returns 404 in v1 |
| User authentication | `GET /v2/login`, `/v2/demo-login`, `/v2/logout`; `POST /v2/auth/verify` | Browser/session flow. Only `auth/verify` has JSON input/output; it is Clerk-JWT protected and CSRF-exempt |
| Authenticated pages | `GET /v2/`, `/v2/dashboard`, `/v2/connections`, `/v2/sandbox-checklist`, `/v2/transactions`, `/v2/invoices`, `/v2/settings`, `/v2/review`, `/v2/optimise` | HTML or redirects; session-authenticated |
| Yapily browser integration | `POST /v2/yapily/connect`, `GET /v2/yapily/callback`, `POST /v2/yapily/disconnect`, `POST /v2/yapily/refresh` | Browser/session endpoints. Connect, disconnect and refresh return JSON; callback redirects. This is not a provider-neutral banking API |
| Demo data | `POST /v2/invoices/seed`, `POST /v2/transactions/seed` | Session-authenticated browser actions; redirects; synthetic data only |
| Tax scenario UI | `POST /v2/optimise/calculate`, `/v2/optimise/save-scenario`; `DELETE /v2/optimise/saved/{scenario_id}` | Session-authenticated JSON endpoints. They are UI-private, CSRF-exempt and not a full annual tax API |
| Founder area | `GET/POST /founder/login`, `GET /founder/`, `POST /founder/logout`, `GET /founder/export/feedback`, `/founder/export/early-access` | Password/session-protected HTML and CSV; not included as a public API contract |

## Provider-neutral internal contracts

These are Python boundaries, not HTTP endpoints:

- `reserved/providers/accounting/contracts.py` defines provider names,
  capabilities, businesses, invoices, entries, pages and sync status.
- `reserved/providers/accounting/base.py` defines the connector operations.
- `reserved/providers/payments/base.py` defines set-aside instructions,
  statuses and the optional money-movement provider boundary.
- `reserved/models/schemas.py` contains an older `CanonicalInvoice` shape.

The accounting contracts deliberately omit access and refresh tokens. The
payment boundary does not itself initiate movement and `TrackOnlyProvider`
accepts track-only instructions only.

## Material gaps before calling this a supported API

1. **No versioned product API namespace.** There is no `/api/v1` resource model
   or compatibility policy.
2. **No annual-position endpoint.** Tax inputs, results, provenance, rule
   versions, limitations and reconciliation evidence have no HTTP contract.
3. **No HTTP accounting contract.** Provider-neutral Python dataclasses exist,
   but OAuth, sync jobs, pagination, idempotency and normalised resources are
   not exposed over Reserved HTTP.
4. **No provider-neutral banking HTTP contract.** Current `/v2/yapily/*` routes
   are coupled to one browser journey and should not be generalised until the
   official sandbox contract is verified.
5. **Inconsistent error media types.** Local JSON errors coexist with global
   HTML error handlers for 400/403/404/429/500.
6. **No formal stability designation.** The JSON `/v2` routes are UI-private,
   but this is not represented by a version or deprecation mechanism.
7. **Authentication is browser-oriented.** Session cookies and Clerk token
   exchange exist; there is no service-client authentication or documented
   OAuth scope model for a Reserved API.
8. **CSRF policy needs consolidation.** Some authenticated JSON routes are
   explicitly exempt. Authentication alone is not a general substitute for
   CSRF protection when cookie-backed sessions are used.
9. **No standard error object or request identifier.** Errors are generally
   `{ok:false,error:string}` but are not universal or assigned stable codes.
10. **No idempotency contract.** Mutating endpoints do not accept an explicit
    idempotency key.
11. **No generated conformance tests.** The specification is currently checked
    for structural and source-route consistency, not runtime schema compliance.
12. **Duplicate invoice vocabulary.** `CanonicalInvoice` and
    `AccountingInvoice` overlap and should be reconciled before publishing a
    stable external schema.

## Recommended documentation boundary

Treat `docs/openapi.json` as an **internal, implementation-derived inventory**.
Before publishing an API, separately design `/api/v1`, select the intended
audience, define authentication and consent, standardise error and idempotency
behaviour, and add request/response conformance tests. Provider APIs must only
be represented after their current official contracts and Reserved's permitted
use have been confirmed.

