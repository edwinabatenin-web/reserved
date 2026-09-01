# HMRC Individual Tax 1.1 endpoint evidence

Observation date: **1 September 2026**. Status: **official endpoint contract
captured; implementation, sandbox use and activation remain gated**.

This is a documentation-only record of the current public HMRC Developer Hub
material for the Individual Tax 1.1 annual-summary read. No HMRC API was
called, no application or account was used, and no credential, test user, UTR,
sandbox fixture or production data was accessed.

## 1. Scope and retrieval identity

- Package/workstream: `reserved-hmrc-individual-tax-1.1-endpoint-evidence`.
- Branch: `ohds/hmrc-it-1.1-endpoint-evidence`.
- Immutable base: `af53bd007f77efee68a3377bb7515b836a399e43`.
- Single new file: `docs/HMRC_INDIVIDUAL_TAX_1_1_ENDPOINT_EVIDENCE.md`.
- Retrieval date: **1 September 2026**.
- Scope: exactly one documented read operation,
  `GET /individual-tax/sa/{utr}/annual-summary/{taxYear}`. This package does
  not implement code or tests, does not broaden to any other operation, and
  does not authorise an adapter, a sandbox run, a provider call or activation.

## 2. Official source register

The following official HMRC sources were reviewed on 1 September 2026. Only
`developer.service.hmrc.gov.uk` was used as authority.

- [Individual Tax API 1.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-tax/1.1)
- [Individual Tax API 1.1 resolved OpenAPI specification](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-tax/1.1/oas/resolved)
- [HMRC API reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)
- [Individual PAYE Test Support API 2.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1)

The resolved OpenAPI document was readable through the Developer Hub, but this
package did not retain a byte-for-byte local export. There is therefore no
durable source-file checksum for this capture; no checksum is invented. The
URL, observation date and literal contract facts below are retained for
independent comparison.

The endpoint-specific OpenAPI specification is authority only for the endpoint
facts it states. Generic platform guidance is labelled separately and does not
fill endpoint-specific omissions. Reserved implementation rules and proposed
uses are also labelled separately and are not represented as provider facts.

## 3. Operation matrix

The resolved Individual Tax 1.1 OpenAPI specification documents exactly one
path and one operation. No additional operation is documented.

| Aspect | Documented value |
|---|---|
| API name / version / status | Individual Tax, version **1.1 beta**, last updated **13 July 2026** |
| Method / path | `GET /individual-tax/sa/{utr}/annual-summary/{taxYear}` |
| `operationId` | `getTaxSummary` |
| Summary | `Get tax summary` |
| `utr` | path, required, `type: string`, described as "The 10 digit self-assessment UTR for the individual." The schema does **not** state a regex, `minLength` or `maxLength`. Example `2234567890` |
| `taxYear` | path, required, `type: string`, `pattern: ^[0-9]{4}-[0-9]{2}$`. Example `2016-17` |
| `Accept` | header, required, `enum: [application/vnd.hmrc.1.1+json]` |
| `Authorization` | header, required, "An OAuth 2.0 Bearer Token … with the `read:individual-tax` scope." |
| Environments | Sandbox `https://test-api.service.hmrc.gov.uk`; Production `https://api.service.hmrc.gov.uk` |

The security scheme is `user-restricted` OAuth 2.0, authorization-code flow.
The OpenAPI authorization definition carries production authorization URLs
(`/oauth/authorize`, `/oauth/token`, `/oauth/refresh` on
`https://api.service.hmrc.gov.uk`) and the scope description
`read:individual-tax` = "Access personal and employment-related tax
information". It does not, by itself, establish a sandbox authorization-host
contract, application subscription, or credential custody.

## 4. Success-schema matrix

HTTP 200 uses `application/json`. The response is an object requiring all
three of:

- `employments`;
- `pensionsAnnuitiesAndOtherStateBenefits`; and
- `refunds`.

The schema does **not** set `additionalProperties: false` at any level, and no
field is declared `nullable`. These are therefore open, non-nullable schemas:
the source does not establish a closed world, and an omitted optional field is
distinct from an explicit JSON `null`.

### `employments`

An unordered array of **zero or more** objects "for which the taxpayer had tax
deducted in the given tax year". Each object requires:

- `employerPayeReference`: `type: string`. "The employer's PAYE reference. A
  value of `267/LS500` indicates a State Pension lump sum." Example `123/AB456`.
- `taxTakenOffPay`: `type: number`. "The amount of UK tax deducted from pay
  under this employment (or State Pension lump sum)." Example `890.35`.

### `pensionsAnnuitiesAndOtherStateBenefits`

A required object described as "Tax deducted from pensions, annuities and other
state benefits". Its documented children are all optional numbers:

- `otherPensionsAndRetirementAnnuities`: "The amount of tax deducted from
  pensions (other than State Pension), retirement annuities and taxable
  trivial payments." Example `36.5`.
- `incapacityBenefit`: "The amount of tax deducted from Incapacity Benefit."
  Example `980.45`.

### `refunds`

A required object (`title: refunds`) with one optional number child:

- `taxRefundedOrSetOff`: "The amount of Income Tax refunded or set off by HMRC
  or Jobcentre Plus." Example `325`.

The `refunds` object itself is required, but `taxRefundedOrSetOff` is not in a
`required` list, so it is optional within that container.

## 5. Documented error matrix

The documented HTTP 400, 401 and 404 bodies use `application/json`. Every
documented error body requires string `code` and string `message`.

| Status | Documented code(s) | Documented example `message` |
|---|---|---|
| 400 Bad Request | `SA_UTR_INVALID` | `The provided SA UTR is invalid` |
| 400 Bad Request | `TAX_YEAR_INVALID` | `The provided Tax Year is invalid` |
| 401 Unauthorized | `UNAUTHORIZED` | `Bearer token is missing or not authorized` |
| 404 Not Found | `NOT_FOUND` | `Resource was not found` |

Unavailable UTR/tax-year evidence is specifically the documented `404` +
`NOT_FOUND` pair; the 404 example description refers the reader to the
data-availability section. An unknown, generic or differently coded 404
response is not that documented pair and must remain unclassified and fail
closed, not converted to endpoint no-data or zero. The generic reference guide
additionally documents platform-wide 401/403/404/405/406/429/500/501/503/504
codes (for example
`MISSING_CREDENTIALS`, `INVALID_CREDENTIALS`, `RESOURCE_FORBIDDEN`,
`INVALID_SCOPE`, `MATCHING_RESOURCE_NOT_FOUND`, `ACCEPT_HEADER_INVALID`,
`MESSAGE_THROTTLED_OUT`). Those are generic platform facts, not
endpoint-specific Individual Tax 1.1 errors, and do not replace the table
above.

## 6. Cross-API / linking and double-count boundaries

The endpoint returns **tax-deducted** amounts plus separately represented
refund/set-off evidence, not income amounts. Individual Income 1.2 returns the
corresponding income amounts and Individual Employment 1.2 returns employment
identity; this capture does not join those responses.

**Local reviewed-context register for cross-API comparison** (not official
sources for the Individual Tax endpoint itself):

- `docs/HMRC_INDIVIDUAL_INCOME_1_2_ENDPOINT_EVIDENCE.md`
- `docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md`

These local reviewed records support only the comparison of visible
fields/categories across APIs; they do **not** establish a cross-API join
contract.

- No aggregate "total tax deducted" field is documented. The response is a
  collection of per-employment `taxTakenOffPay`, per-category pension/benefit
  tax amounts, and a separate `refunds.taxRefundedOrSetOff`. A later
  implementation must not invent a total and must not net the refund/set-off
  amount against deducted amounts.
- `employments[].taxTakenOffPay` and the
  `pensionsAnnuitiesAndOtherStateBenefits.*` values are distinct categories. A
  State Pension lump sum is documented to appear in `employments` under PAYE
  reference `267/LS500`, not in the pensions object.
- `refunds.taxRefundedOrSetOff` is described as a refund **or** set-off,
  which the overview expands to include a repayment of CIS deductions, PAYE tax
  or tax paid on savings income, and may also be an amount HMRC reallocated to
  an existing debt. It must not be treated as additional tax deducted, netted
  against deducted amounts, or applied to Reserved obligations without exact
  reviewed semantics.
- The literal string `employerPayeReference` (and the marker `267/LS500`)
  appears in Individual Tax and Individual Income, but no field, path or
  documentation in the Individual Tax 1.1 specification establishes it as a
  unique, immutable or sufficient cross-endpoint join key. Any later link must
  be justified by separately reviewed provider evidence and must fail closed on
  ambiguity. No documented link exists here to Individual Employment 1.2 or
  Individual Income 1.2.

## 7. Fact / defensive-policy / inference / unresolved register

| Classification | Retained conclusion |
|---|---|
| Endpoint fact | Method, path, `operationId`, required path parameters, exact `Accept` value, OAuth scope, required response containers, field names/types/cardinality and endpoint error codes are recorded literally from the resolved 1.1 specification. |
| Endpoint fact | Data is available only for Self Assessment-registered taxpayers and only after PAYE reconciliation; reconciliation starts on or around 6 June and is usually complete by the end of November, with P11D-dependent start/re-run and loss of data after the corresponding SA return is processed. |
| Generic platform fact | The reference guide documents common environment, money (GBP, two decimal places unless expressly documented otherwise), date/timestamp, error, rate-limit (3 requests/second per application) and fraud-prevention conventions; the endpoint OAS does not specialise all of them. |
| Reserved inference, not yet authorised | Individual Tax 1.1 is a candidate historic/reconciled tax-deducted-and-refund evidence source and may later be compared with Individual Income and Individual Employment. It is not yet a canonical mapping or join contract. |
| Reserved defensive policy, not a provider fact | A later contract may bound array/string lengths, unknown-key counts and Unicode-safety, and may choose exact-money/decimal/sign policy; none of that is authorised by this evidence and none is stated here. |
| Unresolved | Sign, endpoint-enforced precision, negative/adjustment/refund semantics, cross-endpoint identity, endpoint-specific rate-limit/retry/fraud-header requirements, and exact Test Support fixtures remain unknown. |

At endpoint-schema level every monetary-looking value is only `type: number`.
The OpenAPI specification does not state a currency field, minimum, maximum,
sign, precision, scale, `multipleOf` or rounding rule, and does not document
whether credits/repayments/refunds/adjustments appear as negative numbers. The
generic two-decimal-place GBP rule is a platform fact, not an
endpoint-enforced JSON Schema restriction.

Presence and completeness: the response schema documents no completeness field
and no "zero tax" sentinel. Unavailable UTR/tax-year evidence is specifically
the documented `404` + `NOT_FOUND` pair and must not be converted to zero; an
unknown, generic or differently coded 404 must remain unclassified and fail
closed. A valid HTTP 200 with `employments: []` is shape-valid but
does not prove zero tax deducted across all sources, and an omitted optional
numeric child does not acquire a documented completeness meaning.

The tax year is the only represented period in the request; no effective date,
reconciliation timestamp, source-update timestamp or sub-period field is
documented in the response. Retrieval time must not be relabelled as source
time.

## 8. Later literal-contract acceptance criteria

If a separate, authorised package later encodes a network-inert literal
contract for only this operation, its acceptance should require that it:

- pin exactly `GET /individual-tax/sa/{utr}/annual-summary/{taxYear}`,
  `Accept: application/vnd.hmrc.1.1+json`, and scope `read:individual-tax`;
- validate a 10-digit UTR and `^[0-9]{4}-[0-9]{2}$` tax year;
- accept HTTP 200 with the three required containers and the documented
  required/optional fields above, without treating omission as `null` or zero;
- accept HTTP 400 (`SA_UTR_INVALID`, `TAX_YEAR_INVALID`), 401
  (`UNAUTHORIZED`) and the documented 404 (`NOT_FOUND`) with `code`/`message`,
  treating only that documented `404` + `NOT_FOUND` pair as no-data; any
  unknown, generic or differently coded 404 must remain unclassified and fail
  closed, not converted to no-data or zero;
- preserve `refunds.taxRefundedOrSetOff` separately from deducted amounts and
  perform no netting, signing or aggregation;
- retain open-schema forward extensions as undecoded/unknown (or fail closed
  per a separately reviewed rule), never inventing a closed schema; and
- emit no `PayeEvidence`, canonical tax input, cash-obligation input or
  customer-presentation data, with completeness `UNVERIFIED`.

## 9. Explicit gates and out-of-scope items

The following remain unresolved and fail closed:

- endpoint-specific rate limits, retry timing, idempotency and pagination;
- fraud-prevention-header applicability and the exact connection-method header
  set for this endpoint;
- Reserved application subscription and access approval;
- approved encrypted credential/key custody and token lifecycle;
- exact Individual PAYE Test Support 2.1 fixture endpoint, payload, scenarios,
  visibility timing and cleanup/reset behaviour;
- HTTP client, OAuth, callback and route implementation;
- live and sandbox execution evidence;
- cross-endpoint identity resolution and ambiguity handling;
- provider-to-canonical field mapping, decimal/sign/refund policy, persistence
  and source priority;
- privacy, security, operational monitoring, independent integration and
  launch assurance; and
- production activation and release authority.

Out of scope here: no code, tests, commit, merge, push, release, deploy,
credential use, authenticated/live/sandbox call, customer-data use or
activation-state change. The existing repository retains no equivalent
endpoint contract for Individual Tax; this capture does not claim assurance,
implementation completion, integration or launch readiness.

One cross-document version discrepancy remains explicit and is not silently
corrected here: `docs/EXTERNAL_DATA_SPECIFICATIONS.md` names Individual PAYE
Test Support 2.0, whereas the current official service page reviewed for this
capture identifies **2.1 beta**, updated **21 August 2026**, in Sandbox. The
older statement must be reconciled before a Test Support package.

## 10. Recommended next package

Evidence is sufficient for the next package to be a network-inert literal
request/response contract for only the documented
`GET /individual-tax/sa/{utr}/annual-summary/{taxYear}` operation, mirroring
the existing Individual Employment 1.2 literal-contract slice. It must remain
disabled, non-sendable and out of any transport/activation path. Any sandbox
or live journey stays behind the subscription, custody, test-support,
fraud-header, privacy, security and activation gates above.
