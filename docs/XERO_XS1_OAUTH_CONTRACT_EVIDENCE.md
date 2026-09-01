# Xero X-S1 OAuth and tenant contract evidence

Evidence observation date: **2026-09-01**. This is a reviewer-readable capture
of the exact official facts supplied by independent pre-flight; this CLI run did
not browse or contact Xero.

## Official sources and captured facts

- [Authorization flow](https://developer.xero.com/documentation/guides/oauth2/auth-flow/): web-server apps use authorization code. Authorization is at
  `https://login.xero.com/identity/connect/authorize` with required
  `response_type=code`, `client_id`, `scope`, and `redirect_uri`. Xero calls
  `state` optional; Reserved requires a non-empty value. Registered redirects
  use HTTPS. Xero's localhost test exception is deliberately absent here. An
  approved callback returns the supplied `state` and a single-use code expiring
  after five minutes; a denial/error callback uses `error`.
- [Scopes](https://developer.xero.com/documentation/guides/oauth2/scopes/): this
  slice fixes the minimum provider-data scopes to `accounting.invoices.read`
  and `offline_access`. The latter obtains a refresh token. Deprecated broad
  transaction scopes, write scopes, and OpenID/profile/email scopes are not
  accepted.
- [Authorization flow](https://developer.xero.com/documentation/guides/oauth2/auth-flow/): token exchange is a Basic-authenticated POST to
  `https://identity.xero.com/connect/token`, with form fields
  `grant_type=authorization_code`, `code`, and the same `redirect_uri`. The
  documented response has `access_token`, positive integer `expires_in`, exact
  `token_type=Bearer`, and (for `offline_access`) `refresh_token`. Access tokens
  expire after 30 minutes and refresh tokens after 60 days. Refresh posts to
  the same endpoint with `grant_type=refresh_token` and `refresh_token`; it
  returns new access and refresh tokens. Later custody must retain both
  atomically. The previous refresh token has a documented 30-minute grace
  period when the response was not received or saved.
- [Tenants/connections](https://developer.xero.com/documentation/guides/oauth2/tenants/): discovery is Bearer-authenticated `GET
  https://api.xero.com/connections`; optional `authEventId` filters the current
  authorization event. A connection documents `id`, `authEventId`, `tenantId`,
  `tenantType`, null or non-empty string `tenantName`, `createdDateUtc`, and `updatedDateUtc`.
  Types include `ORGANISATION`, `PRACTICEMANAGER`, and `PRACTICE`; Reserved
  accepts only `ORGANISATION`. Identity/date fields remain non-empty strings;
  no timestamp format is inferred. Multiple connections require explicit event
  matching and either explicit tenant matching or return of all matches for
  caller selection—never implicit first-item selection.
- [Tenants/connections](https://developer.xero.com/documentation/guides/oauth2/tenants/): later accounting calls require Bearer authorization and
  `xero-tenant-id: tenantId`. Connection deletion identifies the connection by
  `id`, not `tenantId`; revocation is separate. These are later-slice evidence,
  not behavior here.
- [Limits](https://developer.xero.com/documentation/guides/oauth2/limits): current
  limits and pagination belong to later invoice-read work. X-S1 implements no
  retries, pagination, HTTP client, queue, or live call.

## Ownership and unknown/later boundary

The existing provider-neutral callback/state layer owns expiry and replay
enforcement; its token-store boundary owns atomic rotation. X-S1 only models
the returned token set. HTTP execution, Basic/Bearer header construction,
credential custody, routes, provider enablement, connection deletion,
revocation, invoice fields/mapping, pagination, sandbox/live execution, and
production operations are later. Any detail not stated above or already fixed
by an exact local contract remains unknown/later.
