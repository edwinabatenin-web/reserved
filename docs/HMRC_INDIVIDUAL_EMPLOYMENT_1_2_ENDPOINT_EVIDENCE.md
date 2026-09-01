# HMRC Individual Employment 1.2 endpoint evidence

Observation date: **1 September 2026**. Status: **official endpoint contract
captured; implementation, sandbox use and activation remain gated**.

This is a documentation-only record of the current public HMRC Developer Hub
material. No HMRC API was called, no application or account was used, and no
credential, test user, UTR, sandbox fixture or production data was accessed.

## Official sources and evidence boundary

The following official HMRC sources were reviewed on 1 September 2026:

- [Individual Employment API 1.2 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2)
- [Individual Employment API 1.2 resolved OpenAPI specification](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2/oas/resolved)
- [HMRC API reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)
- [Individual PAYE Test Support API 2.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1)

The official resolved OpenAPI document was readable through the Developer Hub,
but this package did not retain a byte-for-byte local export. There is therefore
no durable source-file checksum for this capture. The URL, observation date and
literal contract facts below are retained for independent comparison; no
checksum is invented.

The endpoint-specific OpenAPI specification is authority only for the endpoint
facts it states. Generic platform guidance is labelled separately and does not
fill endpoint-specific omissions.

## Service and data-availability facts

The service overview identifies **Individual Employment API 1.2 beta**, last
updated **13 July 2026**, in Sandbox and Production. The sandbox and production
API base origins are respectively:

- `https://test-api.service.hmrc.gov.uk`
- `https://api.service.hmrc.gov.uk`

The service provides employment history for a tax year as reported through
PAYE, primarily to pre-populate Self Assessment. Data is available only where
the individual is registered for Self Assessment and had employment in the
requested year. Availability follows PAYE reconciliation, usually by the end of
November; P11D processing may delay or re-run reconciliation. The employment
history is unavailable after the corresponding Self Assessment return has been
processed.

The endpoint is documented for individual and agent users. The documented
agent option limits available history to two years. That constraint is retained
as a provider fact and is not generalised to individual-user history.

The sandbox is stateful and directs test-data setup to **Individual PAYE Test
Support API 2.1 beta**, last updated **21 August 2026**, in Sandbox only. This
identifies the companion product; it does not establish its fixture endpoints,
payloads, subscription status or authority to create test data.

## Exact endpoint contract

The resolved Individual Employment 1.2 OpenAPI specification documents:

- method and path: `GET /individual-employment/sa/{utr}/annual-summary/{taxYear}`;
- `utr`: a required path parameter containing a 10-digit Self Assessment UTR;
- `taxYear`: a required path parameter matching `^[0-9]{4}-[0-9]{2}$`;
- request media version: `Accept: application/vnd.hmrc.1.2+json`;
- authorization: user-restricted OAuth Bearer access with scope
  `read:individual-employment`;
- success: HTTP 200 with a required `employments` array containing one or more
  unordered employment records;
- each employment requires string `employerPayeReference` and string
  `employerName`;
- `offPayrollWorkFlag` is an optional boolean;
- reference `267/LS500` identifies a State Pension lump sum;
- HTTP 400 endpoint errors: `SA_UTR_INVALID` and `TAX_YEAR_INVALID`;
- HTTP 401 endpoint error: `UNAUTHORIZED`;
- HTTP 404 endpoint error: `NOT_FOUND`, meaning the requested data is not
  available;
- the documented HTTP 200, 400, 401 and 404 response bodies use
  `application/json`; and
- every documented error body requires string `code` and string `message`.

The OpenAPI schemas do not set `additionalProperties: false`, so the source does
not establish a closed-world object schema. A later parser must not invent one.
No field in these endpoint schemas is declared nullable: an omitted optional
field and an explicit JSON `null` therefore remain distinct, and this evidence
does not authorize coercing one to the other. How a future implementation
retains or rejects forward extensions is a Reserved implementation rule to be
decided and reviewed in that later package, not a provider fact established
here.

The ordered position of an employment is not an identity or precedence signal.
The exact provider fields must remain source evidence; this capture does not
decide how employer names, PAYE references, off-payroll flags or the State
Pension lump-sum reference map into Reserved's canonical model.

## Generic platform facts, not endpoint additions

The HMRC reference guide establishes TLS, environment base URLs, media-type
versioning, generic error envelopes, generic rate-limit behaviour and generic
fraud-prevention-header guidance. Those facts do not establish an
endpoint-specific rate limit, pagination contract, retry policy or required
fraud-prevention header set for Individual Employment 1.2.

No pagination mechanism is inferred from the unordered `employments` array.
No missing optional field is converted to `false`, `null`, an empty string or
another value. HTTP 404 is retained as unavailable data, not silently converted
into an authoritative empty employment history.

## Unresolved gates

The following remain unresolved and fail closed:

- endpoint-specific rate limits and retry timing;
- whether fraud-prevention headers apply to this endpoint and the exact
  connection-method header set;
- Reserved application subscription and access approval;
- exact Individual PAYE Test Support 2.1 fixture endpoint, payload, scenarios,
  visibility timing and cleanup/reset behaviour;
- approved encrypted credential custody and external key management;
- sandbox callback, test-user and retained-evidence controls;
- live or sandbox execution evidence;
- source-to-canonical field mapping, transport, persistence, routes and
  provider enablement;
- privacy, security, operations, independent integration and launch assurance.

## Decision

This capture closes the previously unresolved method/path, path-parameter,
scope, media-version, minimum success-schema and endpoint-error evidence gap for
the first Individual Employment read. It does not implement or authorize a
request builder, parser, HTTP transport, credential flow, sandbox fixture,
provider call or activation.

After fresh independent source review and separate package authority, the next
eligible engineering slice is a network-inert literal request/response contract
for only this endpoint. Any sandbox or live journey remains behind the
subscription, custody, test-support, fraud-header, privacy and security gates
above.
