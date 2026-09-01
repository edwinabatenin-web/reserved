# QuickBooks Q-S1 OAuth contract evidence

## Status and authority

Observation date: 1 September 2026. Q-S1 is a pure, network-inert candidate
based only on reviewer-supplied observations of these official Intuit pages:

- <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0>
- <https://developer.intuit.com/app/developer/qbo/docs/learn/scopes>
- <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-openid-discovery-doc>

This run did not browse or re-observe those pages. It encodes the supplied
facts; it does not claim fresh source verification.

## Documented Intuit facts encoded

- The authorization endpoint is
  `https://appcenter.intuit.com/connect/oauth2`; the token endpoint is
  `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`; and the
  revocation endpoint is
  `https://developer.api.intuit.com/v2/oauth2/tokens/revoke`, with host casing
  normalised from the discovery example.
- The sole Q-S1 scope is `com.intuit.quickbooks.accounting`. Q-S1 does not
  request payment, `openid`, `profile`, `email`, `phone`, or `address` scopes.
- Authorization requests require `client_id`, `scope`, `redirect_uri`,
  `response_type=code`, and `state`. Intuit requires the redirect to match its
  registration including casing, scheme, and trailing slash.
- Successful callbacks contain `code`, `state`, and `realmId`; the code maximum
  is 512 characters. `realmId` uniquely identifies the QuickBooks Online
  company and is used in later API URLs. Returned state must match original
  state. Documented errors include `access_denied` and `invalid_scope` and are
  not successful bindings.
- Code exchange form data has `grant_type=authorization_code`, `code`, and
  `redirect_uri`. Client authentication belongs to a later HTTP/custody layer.
- Minimum token response fields are `access_token`, `refresh_token`,
  `expires_in`, `x_refresh_token_expires_in`, and `token_type`. Conditional
  `x_refresh_token_hard_expires_in` is present when explicitly requested;
  additive response fields are not errors.
- `token_type` is `bearer`; access-token lifetime begins at 3,600 seconds; the
  access-token maximum length is 4,096 characters; and the refresh-token
  maximum length is 512 characters.
- Refresh form data has `grant_type=refresh_token` and the latest refresh token
  returned by the most recent response. Refresh tokens have a rolling 100-day
  expiry and each latest returned refresh token replaces its predecessor.
  Q-S1 records replacement semantics but implements no custody or persistence.
- Later API use sends `Authorization: bearer {AccessToken}`. Q-S1 does not
  construct that header or any HTTP request and redacts token-set
  representations.

## Reserved inferences and fail-closed rules

These are bounded Reserved security/typing decisions, not Intuit claims:

- Redirects must be absolute HTTPS URIs with a host and no userinfo, fragment,
  or malformed/out-of-range explicit port. A valid explicit HTTPS port is
  preserved. This is necessary to prevent ambiguous or unsafe destinations in
  a pure builder that cannot consult the registered-URI configuration.
- The complete authorization URL is canonical: the exact five fields occur
  once in documented order, use canonical form encoding, and permit no blank,
  duplicate, extra, reordered, endpoint, origin, path, port, userinfo, fragment,
  scope, or response-type drift. Canonical order/encoding is a deterministic,
  reviewable fail-closed rule, not a provider interoperability claim.
- Callback inputs must be singular strings and contain exactly either the
  documented success shape or one of the two supplied documented error shapes.
  Unknown/additive callback parameters fail closed because Q-S1 has no supplied
  evidence assigning them safe meaning. Token responses differ: their additive
  fields are expressly accepted without meaning.
- Token lifetime values must be positive exact integers, excluding booleans,
  floats, and numeric strings. Positivity and exact runtime typing are necessary
  to make the immutable internal value unambiguous; Q-S1 does not assert that
  every positive value is issued by Intuit. The documented 3,600-second access
  lifetime is recorded but not enforced as the only valid response value.
- User IDs, realm IDs, and opaque credential references must be non-blank, and
  both user and realm must match before a binding is reused. This is the local
  ownership boundary needed to reject accidental cross-user or cross-realm
  substitution.

## Q-S1 boundary

Q-S1 validates exact constants; deterministic authorization construction;
redirect safety; state equality; disjoint success/error callbacks; code and
realm presence; code/token length limits; user/realm/credential-reference
binding; form-body data; exact token primitive types; conditional hard expiry;
redacted representation; and complete latest-token-set replacement.

The realm/user/token ownership boundary is explicit: an authenticated Reserved
user ID and callback realm ID are bound to an opaque credential reference.
Tokens are absent from that binding. A later custody layer must own the tokens,
atomically replace the prior complete token set after refresh, and associate
the opaque reference with exactly that user/realm pair. Q-S1 neither stores nor
retrieves credentials.

## Explicit absences and remaining work

Q-S1 contains no network or SDK client, HTTP request, environment/configuration
read, client authentication, secret, credential access, route, state store,
token store, logging, provider call, revocation execution, invoice/query fact,
normalisation, pagination, tax logic, sandbox host/evidence, provider
enablement, integration, operational assurance, or launch assurance.

Q-S2 through Q-S6 in `QUICKBOOKS_COMPLETION_MAP.md` remain unimplemented.
Nothing in Q-S1 demonstrates provider connectivity, credential safety in an
integrated system, accounting correctness, sandbox success, or launch
readiness.
