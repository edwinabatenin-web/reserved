# HMRC Individual PAYE Test Support 2.1 endpoint evidence

Observation date: **2 September 2026**. Status: **official endpoint contract
captured; sandbox use, subscription and activation remain gated**.

This is a documentation-only record of the current public HMRC Developer Hub
material for the **Individual PAYE Test Support API 2.1 beta**. No HMRC API was
called, no application or account was used, and no credential, test user, SA
UTR, NINO, sandbox fixture or production data was accessed.

## 1. Scope and retrieval identity

- Package/workstream: `reserved-hmrc-paye-test-support-2.1-evidence`.
- Branch: `ohds/hmrc-paye-test-support-2.1-evidence`.
- Immutable base: `af5df09004b3202d77fca0ffa7e74d51268882d6`.
- Single new file: `docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`.
- Retrieval date: **2 September 2026**.
- Scope: the six documented create (POST) operations of version 2.1 only. This
  package does not implement code or tests, does not broaden to any other
  product, and does not authorise an adapter, a sandbox run, a provider call,
  subscription, credential custody or activation.

## 2. Official source register and evidence boundary

The following official HMRC sources were reviewed on **2 September 2026**. Only
`developer.service.hmrc.gov.uk` was used as provider authority.

- [Individual PAYE Test Support API 2.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1)
- [Individual PAYE Test Support API 2.1 resolved OpenAPI specification](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1/oas/resolved)
- [Individual PAYE Test Support API 2.1 raw OpenAPI specification](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1/oas/file)
- [Application-restricted endpoints](https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/application-restricted-endpoints)
- [Test users, test data and stateful behaviour](https://developer.service.hmrc.gov.uk/api-documentation/docs/testing/test-users-test-data-stateful-behaviour)
- [HMRC API reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)

The official resolved OpenAPI document was readable through the Developer Hub
and was inspected in full, but this package did not retain a byte-for-byte local
export. There is therefore no durable source-file checksum for this capture; no
checksum is invented. The URL, observation date and literal contract facts below
are retained for independent comparison.

The endpoint-specific OpenAPI specification is authority only for the endpoint
facts it states. Generic platform guidance is labelled separately and does not
fill endpoint-specific omissions. Existing local Reserved documents are context
only and are not relabelled as provider authority.

## 3. Service identity, lifecycle and environments

The overview page identifies **Individual PAYE Test Support API**, API type
**REST**, latest version **2.1 beta**, last updated **21 August 2026**. The
overview states the API "lets you set up test data for the Individual PAYE
APIs: Individual Benefits, Individual Employment, Individual Income and
Individual Tax."

The overview page displays a generic Sandbox base URL
`https://test-api.service.hmrc.gov.uk` and a generic Production base URL
`https://api.service.hmrc.gov.uk`, but its version/endpoint listing shows every
version — **2.1 beta**, **2.0 beta**, **1.0 beta** — in **Sandbox** only. The
resolved OpenAPI document lists a single server URL:
`https://test-api.service.hmrc.gov.uk`. This package therefore records the API
as **Sandbox-only** and does not infer production availability, subscription or
activation.

The service identifier in the URL is `paye-des-stub`. This is recorded as the
Developer Hub path identifier only; it is not treated as a separate product, and
no "DES" behaviour is inferred from it.

## 4. Exact operation matrix

The resolved 2.1 OpenAPI specification documents exactly **six** paths, each
with a single `post` operation. No GET, PUT, PATCH or DELETE operation is
documented anywhere in the specification. This matters for the deletion/reset
fail-closed requirement below: the specification provides **no** clear-down,
reset or deletion operation.

| # | Operation | `operationId` | Purpose (literal) |
|---|---|---|---|
| 1 | `POST /individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}` | `createBenefitsSummaryTestData` | "Supports the Individual Benefits API by creating benefits summary test data." |
| 2 | `POST /individual-paye-test-support/sa/{utr}/child-benefit-entitlement/annual-summary/{taxYear}` | `createChildBenefitEntitlementTestData` | "Supports the Individual Benefits API by creating Child Benefit entitlement test data." |
| 3 | `POST /individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}` | `createEmploymentHistoryTestData` | "Supports the Individual Employment API by creating employment history test data." |
| 4 | `POST /individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}` | `createAnnualIncomeSummaryTestData` | "Supports the Individual Income API by creating annual income test data." |
| 5 | `POST /individual-paye-test-support/sa/{utr}/tax/annual-summary/{taxYear}` | `createTaxSummaryTestData` | "Supports the Individual Tax API by creating annual tax test data." |
| 6 | `POST /individual-paye-test-support/{nino}/winter-fuel-payment-amount/annual-summary/{taxYear}` | `createWinterFuelPaymentAmountTestData` | "Supports the Individual Benefits API by creating Winter Fuel Payment test data." |

Operations 1–5 are keyed by **SA UTR** (`{utr}`). Operation 6 is keyed by
**National Insurance number** (`{nino}`). The operation-6 description states:
"Unlike the other endpoints in this API, this endpoint is keyed by National
Insurance number rather than Unique Taxpayer Reference. The Individual Benefits
API is called with a Self Assessment Unique Taxpayer Reference. You will
therefore need to take note of both IDs when you create a test user." This is a
literal endpoint fact and is not generalised to the other operations.

## 5. Authentication and authorisation

The OpenAPI security scheme is named `application-restricted`, `type: oauth2`,
with a single `clientCredentials` flow whose `tokenUrl` is
`https://test-api.service.hmrc.gov.uk/oauth/token` and whose `scopes` map is
**empty** (`{}`). Every one of the six operations declares
`security: [{"application-restricted": []}]`.

This is an **application-restricted** (OAuth 2.0 Client Credentials Grant)
endpoint, not a user-restricted one. This is an endpoint fact established by the
OpenAPI specification. The generic application-restricted guidance states that
application-restricted endpoints do not require end-user authorisation, do not
give access to sensitive personal data, use the Client Credentials Grant, and
issue an access token that lasts four hours. That is generic platform guidance,
not an endpoint-specific statement, and it does not establish Reserved
application subscription, client credentials, key custody or scope.

Because the OpenAPI `scopes` map is empty and each operation binds an empty
scope list, the resolved specification does **not** document any named OAuth
scope for these operations. A later implementation must not invent a scope.

## 6. Exact parameters

All six operations share the same header parameters. Path parameters differ as
shown.

### Shared header parameters (all six operations)

| Parameter | In | Required | Literal constraint |
|---|---|---|---|
| `Accept` | header | yes | `enum: [application/vnd.hmrc.2.1+json]` |
| `Content-Type` | header | yes | `enum: [application/json]` |
| `Authorization` | header | yes | string, "An OAuth 2.0 Bearer Token"; example `Bearer 59fc92c1cdf0b8ef1f138a702effdbd2` |

The `Authorization` example value is an illustrative placeholder in the
official document, not a credential. No credential is copied or used here.

### Path parameters

| Parameter | Operations | Required | Literal constraint |
|---|---|---|---|
| `utr` | 1–5 | yes | `type: string`, "The 10 digit self assessment UTR for the individual." Example `2234567890`. The schema does **not** state a regex, `minLength` or `maxLength`. |
| `taxYear` | 1–6 | yes | `type: string`, `pattern: ^[0-9]{4}-[0-9]{2}$`. Examples `2016-17` (operations 1,3,4,5) and `2025-26` (operations 2,6). |
| `nino` | 6 only | yes | `type: string`, `pattern: ^[A-Z]{2}[0-9]{6}[A-Z]$`. Example `SA123456A`. |

The operation-2 `taxYear` description adds: "Although production data will only
be available for a portion of the current Self Assessment year, that policy is
not enforced for the data that is created in the sandbox environment by this
operation." This is a literal endpoint fact limited to the Child Benefit
entitlement operation.

The `nino` pattern `^[A-Z]{2}[0-9]{6}[A-Z]$` is an endpoint fact. The generic
reference guide describes a NINO as "2 letters, 6 numbers and a letter (A, B,
C, or D)" with example `QQ123456A`; the endpoint pattern permits any final
uppercase letter. This is recorded as an endpoint-specific constraint that is
not silently overridden by the generic description.

## 7. Request-body contract

`requestBody` is `required: true` for all six operations and uses
`application/json`.

The request-body object schema is the same shape for all six operations: a
single property `scenario` and no top-level `required` list, so the object
schema does not mark `scenario` itself required (although the request body is
required and every documented example populates `scenario`).

The containing request schema is `type: object`. Its `scenario` property has no
separate `type` declaration, but each `oneOf` reference resolves to a
`type: string` schema with one literal enum value. Every documented request
example likewise carries a string value, for example
`{"scenario": "HAPPY_PATH_1"}`. The effective documented property contract is
therefore one of the referenced string enum schemas; the literal enumerations
below are the only documented scenario identifiers.

### Documented scenario identifiers per operation

| Operation | Documented `scenario` enum values |
|---|---|
| `createBenefitsSummaryTestData` | `HAPPY_PATH_1` ("Standard happy path test scenario (default)"), `HAPPY_PATH_2` ("Happy path test scenario with only mandatory fields") |
| `createChildBenefitEntitlementTestData` | `HAPPY_PATH_1` (default), `HAPPY_PATH_2` ("Happy path test scenario for HTTP 404 response"), `UNHAPPY_PATH_500` ("Unhappy path test scenario for HTTP 500 response") |
| `createEmploymentHistoryTestData` | `HAPPY_PATH_1` (default), `HAPPY_PATH_2` ("…only mandatory fields") |
| `createAnnualIncomeSummaryTestData` | `HAPPY_PATH_1` (default), `HAPPY_PATH_2` ("…only mandatory fields") |
| `createTaxSummaryTestData` | `HAPPY_PATH_1` (default), `HAPPY_PATH_2` ("…only mandatory fields") |
| `createWinterFuelPaymentAmountTestData` | `HAPPY_PATH_1` (default), `HAPPY_PATH_2` ("…HTTP 404 response"), `UNHAPPY_PATH_500` ("…HTTP 500 response") |

`HAPPY_PATH_1`, `HAPPY_PATH_2` and `UNHAPPY_PATH_500` are the complete set of
scenario identifiers documented anywhere in this specification. No other
scenario or fixture variant is documented. The request examples for the
`HAPPY_PATH_2` and `UNHAPPY_PATH_500` cases on operations 2 and 6 are the
`requestHappyPath404` and `requestUnhappyPath500` examples respectively; their
literal payload values are `{"scenario": "HAPPY_PATH_2"}` and
`{"scenario": "UNHAPPY_PATH_500"}`.

## 8. Success-response contract (HTTP 201)

Every operation documents exactly one response: **HTTP 201** with
`application/json`. No other HTTP response code is documented per operation.
The literal response object returned by a create operation reflects the data
that the corresponding read API is expected to return for that scenario (see
the stateful model in section 11).

### 8.1 `createBenefitsSummaryTestData` — HTTP 201

Response object requires `employments`. `employments` is an array described as
"An unordered list of one or more employments for which the taxpayer reported
any benefits for the given tax year". Each item requires string
`employerPayeReference` (example `123/AB456`) and may include the following
optional `number` fields: `companyCarsAndVansBenefit`,
`fuelForCompanyCarsAndVansBenefit`, `privateMedicalDentalInsurance`,
`vouchersCreditCardsExcessMileageAllowance`, `goodsEtcProvidedByEmployer`,
`accommodationProvidedByEmployer`, `otherBenefits`,
`expensesPaymentsReceived`.

### 8.2 `createChildBenefitEntitlementTestData` — HTTP 201

Response object requires `expectedStatus` (a `number`, "The HTTP response
status code that should be expected from the Individual Benefits API in the
specified scenario", example `200`). It may include `expectedJson`, an object
that requires `childBenefitEntitlement` (a `number`, "The amount of Child
Benefit entitlement", example `450.99`). The `HAPPY_PATH_2` example returns
`{"expectedStatus": 404}` and `UNHAPPY_PATH_500` returns
`{"expectedStatus": 500}`.

### 8.3 `createEmploymentHistoryTestData` — HTTP 201

Response object requires `employments`, an array described as "An unordered
list of one or more employments which the taxpayer had in the given tax year."
Each item requires string `employerName` and string `employerPayeReference`
(example `123/AB456`) and may include optional boolean `offPayrollWorkFlag`.

### 8.4 `createAnnualIncomeSummaryTestData` — HTTP 201

Response object requires both `employments` and
`pensionsAnnuitiesAndOtherStateBenefits`.

- `employments`: array described as "An unordered list of zero or more
  employments for which the taxpayer received an income in the given tax year."
  Each item requires string `employerPayeReference` and number
  `payFromEmployment`.
- `pensionsAnnuitiesAndOtherStateBenefits`: an object whose documented children
  are all optional numbers — `otherPensionsAndRetirementAnnuities`,
  `incapacityBenefit`, `jobseekersAllowance`, `seissNetPaid`. The object has no
  `required` list.

### 8.5 `createTaxSummaryTestData` — HTTP 201

Response object requires `employments`,
`pensionsAnnuitiesAndOtherStateBenefits` and `refunds`.

- `employments`: array described as "An unordered list of zero or more
  employments for which the taxpayer had tax deducted in the given tax year."
  Each item requires string `employerPayeReference` and number
  `taxTakenOffPay`.
- `pensionsAnnuitiesAndOtherStateBenefits`: object with optional number
  children `otherPensionsAndRetirementAnnuities` and `incapacityBenefit`; no
  `required` list.
- `refunds`: object (title `refunds`) with one optional number child
  `taxRefundedOrSetOff`; the object is required but has no `required` list.

### 8.6 `createWinterFuelPaymentAmountTestData` — HTTP 201

Response object requires `expectedStatus` (number, example `200`). It may
include `expectedJson`, an object that requires `winterFuelPaymentAmount`
(number, "The Winter Fuel Payment amount", example `250.15`). The
`HAPPY_PATH_2` example returns `{"expectedStatus": 404}` and
`UNHAPPY_PATH_500` returns `{"expectedStatus": 500}`.

### Open/closed schema and nullability

The specification sets `additionalProperties: false` nowhere and declares no
field `nullable`. Every response schema is therefore an **open, non-nullable**
schema. A later parser must not invent a closed-world object, and must treat an
omitted optional field as distinct from an explicit JSON `null`. This evidence
does not authorise coercing one to the other.

Array order is not identity, precedence or chronology. No pagination mechanism
is documented.

## 9. Documented error statuses, codes and body shapes

The resolved specification documents **no per-operation error responses**. Each
operation defines only the HTTP 201 success response. There are no documented
400/401/403/404/409/429/500 response bodies in this specification, and no
endpoint-specific error `code` values (unlike the read APIs, which document
`SA_UTR_INVALID`, `TAX_YEAR_INVALID`, `UNAUTHORIZED`, `NOT_FOUND`).

The generic reference guide documents platform-wide error envelopes (a
machine-readable string `code` plus a human-readable string `message`, with
possible additional error-specific information) and generic status codes such
as 429 `MESSAGE_THROTTLED_OUT`, 500 `INTERNAL_SERVER_ERROR`, 501
`NOT_IMPLEMENTED` and 503 service-unavailable codes. Those are generic platform
facts, not endpoint-specific Individual PAYE Test Support 2.1 errors, and do
not replace the absent per-operation error table. A later contract must not
invent endpoint-specific error codes for this API.

## 10. Stateful-testing model and identity linkage

The Test Support API is a write-side companion: its POST operations create test
data that the corresponding read API returns. The read API targeted by each
operation is stated in its description (Individual Benefits for operations 1,
2, 6; Individual Employment for operation 3; Individual Income for operation 4;
Individual Tax for operation 5). The create response body mirrors the data the
read API is expected to return, and for operations 2 and 6 the response carries
an `expectedStatus`/`expectedJson` pair describing the read API's expected
outcome for the chosen scenario.

Identity/tax-year linkage is by **SA UTR** plus **tax year** for operations 1–5,
and by **NINO** plus **tax year** for operation 6. The operation-6 description
explicitly notes the NINO/UTR split and requires both identifiers to be
recorded for a test user. No other identity linkage, correlation rule or
cross-API join authority is documented.

Visibility timing is **not** documented in this specification: there is no
statement of when created data becomes readable by the read API. The generic
stateful-behaviour page states that stateful sandbox APIs "let you send test
data through create (POST) or update (PUT) requests and then read back that same
data through retrieval (GET) requests", but it does not state a delay, a
per-product visibility latency or a completeness guarantee. This package does
not infer immediate or eventual visibility.

Replacement/reset/deletion semantics are **not** documented by this
specification. There is no DELETE, PUT, clear-down or reset operation, and no
replacement rule is stated for re-POSTing the same UTR/NINO and tax year. The
generic stateful-behaviour page states: "For stateful APIs where there is no way
to clear down test data, the best way to start anew is to create a new test
user." That is generic platform guidance and is **not** asserted here as the
documented reset behaviour for Individual PAYE Test Support 2.1. Re-POST
behaviour and clear-down remain unresolved and must fail closed.

## 11. Retention, expiry, cleanup, throttling, idempotency and ordering

- **Retention/expiry/cleanup**: not documented for this API in the OpenAPI
  specification or its overview. The generic testing page states that test users
  not tested against within a three-month period are automatically deleted, and
  that test users can be reused and shared across applications. Those are
  generic platform facts about test users, not this API's data-retention
  contract.
- **Throttling/rate limit**: the generic reference guide states a standard limit
  of 3 requests per second per application with HTTP 429
  `MESSAGE_THROTTLED_OUT`. No endpoint-specific rate limit is documented for
  this API.
- **Idempotency**: no idempotency key, idempotency behaviour or safe-retry
  semantics are documented for any of the six operations.
- **Ordering**: no ordering guarantee, sequence requirement or dependency among
  the six create operations is documented. Array order inside responses is
  explicitly not a semantic signal.

## 12. Literal fact / generic platform fact / Reserved inference / unresolved matrix

| Classification | Retained conclusion |
|---|---|
| Endpoint fact | API name, version 2.1 beta, Sandbox-only listing, six POST paths, `operationId`s, path/header parameters, scenario enums, request-body shape and HTTP 201 response schemas are recorded literally from the resolved 2.1 specification. |
| Endpoint fact | Authentication is `application-restricted` OAuth 2.0 client-credentials with an empty scope map and sandbox token URL `https://test-api.service.hmrc.gov.uk/oauth/token`. |
| Endpoint fact | No per-operation error responses and no reset/delete/clear-down operation are documented. |
| Endpoint fact | Each request is an object whose optional `scenario` property uses `oneOf` references to literal string enum schemas; the documented examples also use those string values. |
| Generic platform fact | OAuth client-credentials lifecycle (four-hour access token), generic error envelope, 3 req/s rate limit, money/timestamp/NINO formats and the stateful/create-read companion pattern are documented in generic HMRC guidance and are not this API's endpoint-specific additions. |
| Reserved inference, not yet authorised | This API is a candidate write-side fixture source for later Individual Employment 1.2, Individual Income 1.2 and Individual Tax 1.1 sandbox tests. It is not yet a canonical mapping, join, persistence or activation contract. |
| Unresolved | Application subscription and access approval; exact visibility timing; re-POST replacement and clear-down/reset behaviour; endpoint-specific rate/fraud requirements; encrypted credential/key custody; and live or sandbox execution evidence remain unknown and fail closed. |

## 13. Double-counting and identity boundary for later read-API sandbox tests

This package does not join or aggregate any read-API responses. It records the
following boundary so that later Individual Employment 1.2, Individual Income
1.2 and Individual Tax 1.1 sandbox tests do not double-count or fabricate a
cross-API identity link:

- Each create operation is keyed by exactly one identity axis (SA UTR for
  operations 1–5, NINO for operation 6) plus a tax year. The same SA UTR and tax
  year are the only documented linkage between a Test Support create and a
  subsequent read of the corresponding read API.
- The literal string `employerPayeReference` is not established by this
  specification as a unique, immutable or sufficient cross-endpoint join key.
  No join authority is inferred from similarly named fields.
- Employment-history, income and tax are three distinct read products with
  distinct create operations and distinct response field sets (`employerName` /
  `offPayrollWorkFlag`; `payFromEmployment`; `taxTakenOffPay` plus `refunds`).
  A later sandbox test must treat these as separate categories and must not
  aggregate, net or total them across operations without separately reviewed
  authority.
- The operation-6 NINO/UTR split means a Winter Fuel Payment fixture cannot be
  assumed to be reachable by the same SA-UTR key as the other five operations;
  both identifiers must be recorded per test user.

## 14. Disposition

The resolved 2.1 specification supplies the exact method/path/operation
identifiers, parameters, scenario enumerations, request-body shape,
authentication model and HTTP 201 response schemas for all six documented
create operations. That is sufficient to author a **network-inert literal
request/response test-support contract** for the next slice.

The following are **not** established here and must fail closed before any
sandbox or live journey:

- Reserved application subscription and access approval;
- approved encrypted client-credential custody and token lifecycle;
- exact visibility timing after a create, and re-POST replacement behaviour;
- any clear-down/reset/deletion semantics (none are documented);
- endpoint-specific rate-limit/retry and fraud-prevention-header applicability;
- cross-API identity resolution and double-counting policy beyond the literal
  UTR/NINO-plus-tax-year keys above; and
- live or sandbox execution evidence.

## 15. Hard gates and out-of-scope items

Out of scope here: no code, tests, commit, merge, push, release, deploy,
credential use, authenticated/live/sandbox call, test-user creation, customer
data use or activation-state change.

Cross-document version discrepancies remain explicit and are not silently
corrected here: `docs/EXTERNAL_DATA_SPECIFICATIONS.md` and
`docs/HMRC_PAYE_RECONCILIATION.md` name Individual PAYE Test Support 2.0 or
describe 2.1 as alpha, whereas the current official overview reviewed for this
capture identifies **2.1 beta**, updated **21 August 2026**, in Sandbox. Those
older statements must be reconciled before a Test Support package; they are not
authority to downgrade this dated source capture.
