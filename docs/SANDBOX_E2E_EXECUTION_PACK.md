# Synthetic sandbox end-to-end execution pack

**Prepared:** 13 August 2026  
**Boundary:** synthetic provider data only; never production customer data,
live HMRC users, live bank accounts, payments or production credentials

This pack defines the evidence to collect when Reserved's sandbox adapters are
implemented. Configuration readiness is not end-to-end evidence. A provider
passes only when the applicable journey has run against its test environment,
the evidence record validates against `docs/sandbox_evidence.schema.json`, and
no secret or full token is retained in the record.

## Evidence handling rules

- Record UTC times, environment, application build/commit, provider/API
  version, synthetic dataset identifier and redacted request correlation IDs.
- Never record client secrets, authorisation codes, access/refresh tokens,
  consent tokens, account numbers, test-user passwords or full response bodies.
- Record response status, provider request/correlation ID where supplied,
  schema/result counts, pagination state and a cryptographic hash of a
  separately secured redacted artefact if one is retained.
- Each negative test uses a fresh synthetic authorisation where needed and must
  avoid account lockout or provider rate-limit abuse.
- A human records `pass`, `fail`, `blocked` or `not_applicable`; absence of an
  error is not automatically a pass.
- Provider-specific assertions below are evidence requirements, not claims
  that Reserved already implements the capability.

## Common OAuth journey

Apply only where the official provider flow uses browser authorisation.

1. Confirm the fail-closed readiness result without displaying variable values.
2. Confirm the callback URI exactly matches the provider registration.
3. Generate an unpredictable, session-bound `state`; start authorisation.
4. Approve access using a synthetic/test organisation or test user.
5. Reject a mismatched or replayed `state`; do not exchange the code.
6. Exchange a valid, single-use code server-side and persist tokens only in the
   intended secure store.
7. Perform one minimum-scope read and prove tenant/user ownership isolation.
8. Refresh after expiry or via a controlled test mechanism; atomically retain
   the latest refresh token when the provider rotates it.
9. Revoke/disconnect, then demonstrate that subsequent access fails safely and
   Reserved displays a reconnect state without deleting imported evidence.
10. Exercise denial, expired/invalid code, 401, 403, 429 and provider 5xx paths
    where the sandbox supports them; retain redacted outcomes.

## HMRC sandbox

**Current Reserved state:** configuration readiness and PAYE reconciliation
logic exist; no end-to-end HMRC HTTP/OAuth adapter was found in the current
code. Execution is therefore blocked until that adapter is implemented.

Use only an HMRC-created individual test user and HMRC sandbox data. Do not
automate or scrape the OAuth web interface.

Checklist:

- Record the exact subscribed API name, version and endpoint under test. Test
  only endpoints required by Reserved's supported data sources.
- Complete the user-restricted OAuth flow for the synthetic individual; verify
  state, denial, single-use code exchange, refresh and revoked/expired token
  handling.
- Exercise the relevant read endpoints for the intended PAYE evidence journey
  (Individual Employment, Individual Income and Individual Tax only where the
  exact current endpoint documentation confirms the required fields).
- Preserve separate evidence for missing/empty, conflicting and delayed source
  records; do not silently convert absence into zero income or zero tax.
- For MTD endpoints, send fraud-prevention headers for the selected connection
  method and run the Test Fraud Prevention Headers API. Fix errors and review
  advisories; do not call a `Correct` result a certification.
- Confirm `Accept` versioning, documented error codes and rate-limit/retry
  behaviour for each endpoint rather than applying one generic response model.
- Run the supported automated sandbox pack weekly once it exists; do not pin
  HMRC-specific certificates or rely on fixed IP addresses.
- Record unsupported required fields or endpoint restrictions as blockers; do
  not infer a complete “golden source” from partial HMRC records.

Official basis:

- [HMRC API documentation and sandbox entry point](https://developer.service.hmrc.gov.uk/api-documentation)
- [HMRC development practices](https://developer.service.hmrc.gov.uk/api-documentation/docs/development-practices)
- [MTD Income Tax integration and testing requirements](https://developer.service.hmrc.gov.uk/guides/income-tax-mtd-end-to-end-service-guide/documentation/how-to-integrate.html)
- [Fraud-prevention headers](https://developer.service.hmrc.gov.uk/guides/fraud-prevention/)
- [Test Fraud Prevention Headers API](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/txm-fph-validator-api/1.0)

## FreeAgent sandbox

**Current Reserved state:** `FreeAgentProvider` is an explicit placeholder;
OAuth, refresh and reads raise `NotImplementedError`. No end-to-end run is
possible until implementation.

Checklist:

- Use `api.sandbox.freeagent.com` throughout; never mix sandbox approval/token
  endpoints with the production API host.
- Complete setup of the temporary sandbox company before testing.
- Send the registered redirect URI and verify returned `state` even though the
  provider documents it as optional.
- Exchange the short-lived authorisation code server-side using HTTP Basic
  client authentication; store the per-user access and refresh tokens securely.
- Read the company/profile needed to bind the token to the correct sandbox
  company before importing data.
- Read synthetic invoices and the permitted bank accounts/transactions needed
  by the approved Reserved scope; verify permission-denied behaviour for an
  insufficient-access user.
- Page list endpoints using the response `Link` relations rather than guessing
  page counts; reconcile item count with `X-Total-Count`. Test more than the
  default 25 items and remain at or below the documented 100-item `per_page`
  limit.
- Prove decimal/date/currency/status normalisation, duplicate suppression and
  an incremental `updated_since` bank-transaction read using synthetic records.
- Refresh an expired access token, atomically store the returned token pair,
  then revoke or otherwise remove sandbox authorisation and verify reconnect
  handling.

Official basis:

- [FreeAgent OAuth 2.0](https://dev.freeagent.com/docs/oauth)
- [FreeAgent API introduction and pagination](https://dev.freeagent.com/docs/introduction)
- [FreeAgent sandbox quick start](https://dev.freeagent.com/docs/quick_start)
- [FreeAgent bank transactions](https://dev.freeagent.com/docs/bank_transactions)

## Xero demo company

**Current Reserved state:** `XeroProvider` is an explicit placeholder; OAuth,
refresh, tenant discovery and reads are not implemented.

Checklist:

- Use a Xero demo company and a web-app authorization-code flow; request only
  the currently assigned minimum granular scopes plus `offline_access` where
  background refresh is required.
- Verify unique state, denial, the five-minute/single-use code boundary and an
  exact registered redirect URI.
- Exchange tokens server-side. Discover authorised tenants through
  `GET https://api.xero.com/connections`; never assume the first historical
  connection is the tenant selected in the current flow.
- Bind each import to the selected tenant ID and include `xero-tenant-id` on
  accounting API requests; test a wrong/unauthorised tenant ID.
- Import a synthetic organisation, invoices and only the transaction resources
  confirmed by the approved scope; record mapping and rejected/unknown fields.
- Exercise paginated invoices with line-item detail and avoid assuming an
  unpaged response is complete. Record `X-DayLimit-Remaining`,
  `X-MinLimit-Remaining` and `X-AppMinLimit-Remaining` when present.
- On 429, honour `Retry-After` and pause requests for the affected tenant; do
  not busy-retry.
- Refresh and atomically retain both returned tokens. Exercise the documented
  previous-refresh-token grace case without logging either value.
- Delete the test connection and prove subsequent calls fail and local state
  changes to reconnect-required.

Official basis:

- [Xero standard authorization-code flow](https://developer.xero.com/documentation/guides/oauth2/auth-flow/)
- [Xero OAuth scopes](https://developer.xero.com/documentation/guides/oauth2/scopes/)
- [Xero demo-company getting started](https://developer.xero.com/documentation/getting-started-guide/)
- [Xero API limits and pagination](https://developer.xero.com/documentation/guides/oauth2/limits)

## QuickBooks Online sandbox

**Current Reserved state:** `QuickBooksProvider` is an explicit placeholder;
OAuth, refresh, realm binding and reads are not implemented.

Checklist:

- Use a QuickBooks Online sandbox company and the development redirect URI,
  never a production company or production keys.
- Complete the authorization-code flow with state/denial/replay tests and bind
  the callback's `realmId` to the authenticated Reserved user and token set.
- Exchange the code server-side and use the sandbox QBO API base URL selected
  from current official configuration; do not derive environment from a token.
- Read the synthetic CompanyInfo and invoices/transactions explicitly approved
  for v1; test that a realm ID owned by another test connection is rejected
  before a provider request.
- Page queries with `STARTPOSITION` and `MAXRESULTS`, using `COUNT(*)` where an
  independent completeness check is required. Test more than one page and
  stable ordering for incremental imports.
- Prove decimal/date/currency/status mapping and duplicate suppression from
  synthetic records; retain unknown enum values rather than dropping records.
- Exercise access-token expiry/401. Always store and use the latest refresh
  token returned because Intuit rotates refresh-token values; prove safe
  recovery when reauthorisation is required.
- Exercise denial, revoked access, malformed query, 429 and documented service
  errors without logging request credentials or provider payloads containing
  sensitive fields.

Official basis:

- [Intuit OAuth 2.0](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [Intuit OAuth token lifecycle FAQ](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/faq)
- [QuickBooks Online query pagination](https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/data-queries)

## Yapily AIS sandbox

**Current Reserved state:** fixture mode works, but all network-backed methods
raise `NotImplementedError`. The comments and method contracts in
`reserved/providers/banking/yapily.py` describe multiple older/unverified paths
(`account-auth-requests`, consent query parameters and cursor semantics). The
current official Hosted Consent Pages example instead documents
`POST /hosted/consent-requests`. This is a **contract-selection blocker**, not a
ready-to-run integration. The selected contracted product must be confirmed
before changing or executing the client.

Checklist after contract selection and implementation:

- Configure the preconfigured `modelo-sandbox` institution in the Yapily
  Console and authenticate with sandbox application credentials held only in
  the secret store.
- Select one official AIS authorisation journey (for example, current Hosted
  Consent Pages if included in Reserved's contract) and implement its exact
  request, callback/redirect and consent retrieval contract. Do not mix legacy
  paths with current Hosted Pages.
- Request only accounts, balances and account-transactions features needed by
  Reserved; do not request or test payment initiation.
- Bind `applicationUserId` and locally generated anti-forgery state/correlation
  data to the authenticated Reserved test user. Treat an OAuth-style redirect
  as distinct from an authenticated webhook.
- Complete consent against Modelo synthetic accounts, then retrieve the
  accounts and transactions using the current API reference for the selected
  journey. Record actual provider pagination links/metadata before implementing
  traversal; do not assume a `next` cursor.
- Test multiple accounts, empty transactions, pending/booked states, duplicate
  provider transaction IDs, date windows, currencies and consent expiry using
  only sandbox data.
- Exercise rejection, invalid/expired consent, unauthorised account ID, 429 and
  provider error responses. Treat sandbox behaviour as evidence for the tested
  institution, not proof of every bank's live behaviour.
- Revoke/disconnect through the exact contracted API if supported and verify
  local ownership, reconnect state and retention rules.
- Record sandbox limitations: external-bank sandboxes can have static or
  unrealistic transaction/status behaviour; a successful Modelo run is not a
  production-bank certification.

Official basis:

- [Yapily sandbox overview](https://docs.yapily.com/resources/sandbox/overview)
- [Yapily sandbox setup with Modelo](https://docs.yapily.com/getting-started/get-started)
- [Current Hosted Consent Request reference](https://docs.yapily.com/api-reference/hosted-consent-pages/create-hosted-consent-request)
- [Yapily sandbox test cases](https://docs.yapily.com/resources/sandbox/test-cases)

## Google and Apple sign-in through Clerk test instance

**Current Reserved state:** network-free configuration/readiness checks exist,
but neither upstream provider has repository evidence of enablement in the
intended Clerk instance and no browser end-to-end evidence has been retained.
Execution is therefore **later**, after an authorised administrator confirms
the test-instance configuration; it is not executable from this sanitised copy.

Checklist:

- Use only the intended non-production Clerk instance and synthetic identities;
  do not use production customers or production provider credentials.
- Record the clean HTTPS Reserved origin, a redacted Clerk-instance reference,
  upstream provider, registered redirect/origin configuration and build
  reference. Never retain provider secrets, session tokens or raw assertions.
- Complete sign-in, sign-out and fresh sign-in in a supported browser; prove the
  Reserved user is bound to the intended identity and cannot access another
  user's records.
- Reject forged, expired, wrong-issuer and, where applicable, wrong-audience or
  wrong-authorised-party Clerk tokens. Verify expiry, replay/logout behavior and
  safe failure when Clerk/JWKS is unavailable.
- Exercise upstream denial/cancellation and disabled-provider behavior. A Clerk
  publishable key or widget render is not proof of correct provider enablement.
- For Apple, additionally verify the registered web Service ID/domain/return URL
  and the authenticated server-to-server notification/account-deletion path
  required by the approved flow before launch attestation.
- Record keyboard/accessibility behavior for buttons and error states as manual
  browser evidence, separately from token-validation evidence.

Official basis:

- [Clerk social connections](https://clerk.com/docs/authentication/social-connections/overview)
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [Sign in with Apple for the web](https://developer.apple.com/help/account/capabilities/configure-sign-in-with-apple-for-the-web/)
- [Apple server-to-server notifications](https://developer.apple.com/documentation/signinwithapple/processing-changes-for-sign-in-with-apple-accounts)

Evidence records use provider values `google_sign_in` and `apple_sign_in` in
`docs/sandbox_evidence.schema.json`, with environment `test`.

## Exit criteria per provider

A provider is `passed` only when all applicable required cases pass, sensitive
artefacts are absent from evidence, imported counts reconcile across every
page, ownership isolation and reconnect behaviour pass, and open discrepancies
have an owner and severity. Placeholder methods, fixture-only tests, presence
of environment variables or a successful OAuth redirect alone cannot satisfy
the gate.
