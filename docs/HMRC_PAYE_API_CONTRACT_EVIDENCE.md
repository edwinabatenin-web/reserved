# HMRC PAYE API contract evidence

Observation date: **1 September 2026**. Status: **documentation-only evidence;
adapter implementation remains blocked**.

This record captures only current public HMRC Developer Hub material for the
first proposed PAYE read. No HMRC API was called, no account was used, and no
credential, test user, NINO, sandbox fixture or production data was accessed.
The endpoint specification is dynamically rendered and did not expose
reviewable endpoint-level content through the available text capture. Missing
facts below therefore remain unresolved rather than being reconstructed from
API names, examples elsewhere, source code or memory.

## Evidence hierarchy and sources

Only these official pages were used, each accessed on 1 September 2026:

- [Individual Employment API 1.2 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2)
- [Individual Employment API 1.2 endpoint specification page](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2/oas/page)
- [User-restricted endpoint authorisation](https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/user-restricted-endpoints)
- [HMRC Developer Hub tutorials](https://developer.service.hmrc.gov.uk/api-documentation/docs/tutorials)
- [HMRC API reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)
- [Testing in the sandbox](https://developer.service.hmrc.gov.uk/api-documentation/docs/testing)
- [Test users, test data and stateful behaviour](https://developer.service.hmrc.gov.uk/api-documentation/docs/testing/test-users-test-data-stateful-behaviour)
- [Individual PAYE Test Support API 2.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1)
- [Send fraud prevention data](https://developer.service.hmrc.gov.uk/guides/fraud-prevention/)

The service overview and generic platform guidance are authoritative for the
facts they state. They are not substitutes for the Individual Employment 1.2
endpoint specification. An example on a generic OAuth page is not treated as
proof of this endpoint's scope or schema.

## Documented OAuth platform contract

The current user-restricted guidance documents these generic platform facts:

- user-restricted endpoints use OAuth 2.0 Authorization Code Grant; PKCE is
  supported but described as optional;
- the sandbox authorisation syntax shown on that page uses
  `https://test-www.tax.service.gov.uk/oauth/authorize`, while the sandbox token
  endpoint is `https://test-api.service.hmrc.gov.uk/oauth/token`;
- the authorisation request uses `response_type=code`, `client_id`, a
  URL-encoded space-delimited `scope`, and `redirect_uri`; `state` is described
  as optional by HMRC but is the tamper-prevention round-trip value;
- optional PKCE requires `code_challenge_method=S256`; `code_challenge` and
  `code_challenge_method` require each other, and `code_verifier` is required at
  exchange when a challenge was sent;
- the redirect URI must match a URI registered for the application and the same
  URI must be used at authorisation and code exchange;
- the callback is an HTTP GET. Success supplies `code`; failure supplies
  `error=access_denied`, `error_description` and an unstable `error_code`.
  `state` is returned on success or failure;
- an authorisation code is single-use and expires after 10 minutes;
- code exchange is a form-encoded POST body containing `client_secret`,
  `client_id`, `grant_type=authorization_code`, the same `redirect_uri`, and
  `code`, plus `code_verifier` when PKCE was used;
- the documented token response contains `access_token`, `token_type`,
  `expires_in`, `refresh_token` and `scope`. Access tokens last four hours;
- refresh is a form-encoded POST with `grant_type=refresh_token`. Refresh tokens
  are single-use, successful refresh returns a replacement refresh token, and
  the original access token is invalidated immediately if it is still live;
- authorisation lasts up to 18 months unless revoked or invalidated. An expired
  refresh token returns HTTP 400 with `invalid_grant` and requires the user to
  repeat the authorisation journey;
- an API call presents the access token as an OAuth Bearer token. The endpoint's
  required scope remains owned by its own endpoint documentation.

The current generic tutorial elsewhere on the Developer Hub shows an
authorisation URL under `test-api.service.hmrc.gov.uk`, whereas the current
user-restricted guidance above shows `test-www.tax.service.gov.uk`. This record
does not adjudicate that official-source conflict. A later implementation must
obtain one current reviewed endpoint/authentication contract and pin the exact
origin before constructing an authorisation URL.

## Individual Employment 1.2: documented service boundary

The current overview establishes:

- product/version: **Individual Employment API 1.2 beta**, last updated
  13 July 2026;
- environments: Sandbox and Production;
- sandbox API base URL: `https://test-api.service.hmrc.gov.uk`;
- purpose: employment history for a given tax year as reported by employers
  through PAYE, primarily to pre-populate an individual's Self Assessment tax
  return;
- example information categories: employer PAYE reference, employer name and,
  when available, an off-payroll work flag;
- the API is stateful in the sandbox and its test data is set up through the
  Individual PAYE Test Support API.

These facts support selection of one employment-history read as the first
provider journey. They do **not** establish the endpoint path, required scope,
request identifiers or response object contract.

## Endpoint facts that remain unresolved

The endpoint specification page was located but its endpoint-level content was
not available in a reviewable text representation. The following therefore
remain hard implementation blockers:

- exact HTTP method and path;
- exact placement, spelling, format and validation rules for NINO, tax year and
  any other path/query parameters;
- exact OAuth scope for the selected read. The generic OAuth page contains an
  example token response with `read:employment`, but a generic example is not
  endpoint authority;
- exact `Accept` media type. The generic versioning rule suggests the pattern
  `application/vnd.hmrc.[version]+json`, but this record does not derive an
  Individual Employment literal from that pattern;
- any other mandatory request or correlation headers;
- the full success schema, field types, cardinalities, identifiers, optionality,
  nullability, empty/no-data representation and forward-compatible extension
  rules;
- endpoint-specific error codes, meanings and retry/non-retry behaviour;
- exact rate-limit or pagination behaviour, if any;
- the endpoint's exact fraud-prevention-header applicability;
- the exact Individual PAYE Test Support fixture endpoint and payload needed to
  create the smallest one-employment, one-tax-year test state.

No parser, request builder, source schema or provider-specific transport may be
implemented until those facts are captured and independently reviewed.

## Generic platform error and data facts

The reference guide documents generic error bodies with machine-readable
`code` and human-readable `message`, with possible additional fields or an
`errors` collection. Common platform outcomes include missing/invalid
credentials (401), unsubscribed application, insufficient scope or forbidden
tax identifier (403), missing endpoint (404), invalid method (405), invalid
`Accept` header (406), throttling (429), and platform/server failures
(500/501/503/504). These are platform facts only; they do not replace the
endpoint-specific error table.

The same guide states that dates use `YYYY-MM-DD`, timestamps use ISO 8601 with
an offset, and a NINO has the documented generic form. It also states that
sandbox APIs use `https://test-api.service.hmrc.gov.uk`, APIs require TLS, and
the platform does not support browser-side CORS. A future server-side adapter
must still validate the exact endpoint contract rather than treating these
generic formats as a complete schema.

## Sandbox and test-support gate

The current sandbox guidance says user-restricted testing requires a generated
test user, that the same generated tax identifiers must be used for the API
calls, and that mismatched identifiers should be tested as failures. Stateful
APIs may use an accompanying test-support API to create data that a GET API can
read back.

The current Individual PAYE Test Support overview now identifies **2.1 beta**,
last updated 21 August 2026, as the latest version and lists versions 2.1, 2.0
and 1.0 in Sandbox. It says the API sets up test data for Individual Benefits,
Individual Employment, Individual Income and Individual Tax. This supersedes
the historical 13 August 2026 statements in `EXTERNAL_DEPENDENCIES.md` and
`docs/HMRC_PAYE_RECONCILIATION.md` that select 2.0 or describe 2.1 as alpha and
unavailable. Those references must be reconciled before any later HMRC package;
they are not authority to downgrade this dated source capture. This does
not prove that Reserved's application is subscribed, identify a fixture path or
payload, or authorise a sandbox run.

## Fraud-prevention boundary

The fraud-prevention guide says some HMRC APIs require HTTP fraud prevention
headers and expressly identifies VAT (MTD) and Income Tax Self Assessment (MTD)
APIs as legally mandatory examples. The generic reference guide says wider
coverage is expected and recommends designing for it. The accessible Individual
Employment 1.2 overview does not state whether this endpoint is currently in
scope or which connection-method headers apply. Applicability therefore remains
unresolved and must be confirmed before any call; no header set is inferred.

## Fact, inference and decision summary

| Item | Classification | Consequence |
|---|---|---|
| OAuth Authorization Code, callback, exchange and refresh lifecycle above | Documented generic HMRC platform fact | Reusable only after endpoint-specific origin/scope review and approved custody |
| Individual Employment 1.2 purpose, version, environments and high-level information categories | Documented service fact | Supports the selected first read, not a wire contract |
| Employment identity before income/tax amounts | Reserved implementation sequencing inference | Preserve as proposed ordering; do not represent it as HMRC-mandated |
| `read:employment` as the exact endpoint scope | Unresolved | Do not encode from the generic OAuth example |
| Individual Employment endpoint, request and response schema | Unresolved | Hard blocker for request builder, parser and adapter |
| Individual PAYE Test Support 2.1 beta as latest listed sandbox version | Documented current service fact | Re-review exact fixture contract and application subscription before use |
| Fraud-prevention headers for the selected read | Unresolved | No sandbox or production call until applicability and exact headers are reviewed |

## Terminal decision

This evidence package advances the generic OAuth and service-selection
prerequisites, corrects the current test-support version, and identifies the
remaining exact gaps. It does not make the HMRC adapter implementation-ready.

The next safe package is a fresh, reviewable capture of the Individual
Employment 1.2 endpoint specification (including exact scope, request, schema,
endpoint errors and test fixture). Only after that capture and separate
authority may a network-inert HMRC request/response contract be proposed.
Encrypted credential custody, application subscription, synthetic sandbox
identity/data, provider calls, activation and production access remain later
independent gates.
