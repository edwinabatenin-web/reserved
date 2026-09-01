# HMRC Individual Income 1.2 endpoint evidence

Observation date: **1 September 2026**. Status: **official endpoint contract
captured; implementation, sandbox use and activation remain gated**.

This is a documentation-only record of the current public HMRC Developer Hub
material. No HMRC API was called, no application or account was used, and no
credential, test user, UTR, sandbox fixture or production data was accessed.

## Official sources and evidence boundary

The following official HMRC sources were reviewed on 1 September 2026:

- [Individual Income API 1.2 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income/1.2)
- [Individual Income API 1.2 resolved OpenAPI specification](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income/1.2/oas/resolved)
- [HMRC API reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)
- [Individual PAYE Test Support API 2.1 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.1)

The official resolved OpenAPI document was readable through the Developer Hub,
but this package did not retain a byte-for-byte local export. There is therefore
no durable source-file checksum for this capture. The URL, observation date and
literal contract facts below are retained for independent comparison; no
checksum is invented.

The endpoint-specific OpenAPI specification is authority only for the endpoint
facts it states. Generic platform guidance is labelled separately and does not
fill endpoint-specific omissions. Reserved implementation rules and proposed
uses are also labelled separately and are not represented as provider facts.

## Service purpose, population and availability

The service overview identifies **Individual Income API 1.2 beta**, last
updated **13 July 2026**, in Sandbox and Production. The documented environment
base origins are:

- Sandbox: `https://test-api.service.hmrc.gov.uk`
- Production: `https://api.service.hmrc.gov.uk`

The service provides, for a given tax year:

- employment income reported through PAYE;
- pensions other than State Pension and retirement annuities; and
- other taxable state benefits and grants, including taxable Incapacity
  Benefit, contribution-based Employment and Support Allowance and Self
  Employment Income Support Scheme income.

The stated primary purpose is pre-population of a Self Assessment return. The
API is available only for people registered for Self Assessment. Most data is
available only after PAYE reconciliation, which starts around 6 June, processes
about one million records per night and is usually complete by the end of
November; the documentation states that there is no way to know the completion
date for a particular individual. An expected P11D can delay reconciliation,
and an unexpected P11D can cause it to be rerun. SEISS income is available from
the beginning of the tax year following the claim without waiting for PAYE
reconciliation. Data becomes unavailable after HMRC has received and processed
the corresponding Self Assessment return.

The endpoint is documented for individual and agent users. The documented
agent options restrict available history to two years. This is not generalised
to the individual-user journey.

The source data comes from information provided by employers and pension
providers. HMRC warns that pension income can be reported as employment income
where a pension provider does not identify it as a pension. A State Pension
lump sum is reported in `employments` with PAYE reference `267/LS500`.

These constraints mean that a successful response is population- and
reconciliation-dependent evidence. It is not a live payroll feed, a universal
income record or proof that all income outside this endpoint is absent.

## Exact request contract

The resolved Individual Income 1.2 OpenAPI specification documents:

- method and path:
  `GET /individual-income/sa/{utr}/annual-summary/{taxYear}`;
- `utr`: a required string path parameter described as a 10-digit Self
  Assessment UTR; the schema does not state a regex, minimum length or maximum
  length for this parameter;
- `taxYear`: a required string path parameter matching
  `^[0-9]{4}-[0-9]{2}$`;
- required media version: `Accept: application/vnd.hmrc.1.2+json`; and
- user-restricted OAuth Bearer authorization with scope
  `read:individual-income`.

The OpenAPI authorization definition contains production authorization URLs.
It does not, by itself, establish a sandbox authorization-host contract. This
capture therefore does not resolve existing authorization-host, subscription,
application-registration or credential-custody questions.

## Exact HTTP 200 response contract

HTTP 200 uses `application/json`. The response is an object requiring both:

- `employments`; and
- `pensionsAnnuitiesAndOtherStateBenefits`.

### `employments`

`employments` is an unordered array containing **zero or more** objects. Each
object requires:

- `employerPayeReference`: string. Reference `267/LS500` identifies a State
  Pension lump sum; and
- `payFromEmployment`: number. The description states that this is the pay from
  the employment, or the State Pension lump sum, taken from the P45 or P60.

The documented schema does not define an employer name, employment ID, payment
date, pay-period range, tax-deducted amount or off-payroll flag in this array.
Because the schema is open, this is a statement about the documented contract,
not a claim that an extension can never appear. An undocumented extension does
not acquire field semantics or mapping authority merely by appearing. The
presence of a PAYE reference in both Individual Income and Individual
Employment does not establish that it is unique, immutable or a sufficient
cross-endpoint join key. Any later link between those responses must be
justified by separately reviewed provider evidence and must fail closed on
ambiguity.

### `pensionsAnnuitiesAndOtherStateBenefits`

`pensionsAnnuitiesAndOtherStateBenefits` is a required object. Its documented
children are all optional numbers:

- `otherPensionsAndRetirementAnnuities`: income from pensions other than State
  Pension, retirement annuities and taxable trivial payments;
- `incapacityBenefit`: taxable Incapacity Benefit and contribution-based
  Employment and Support Allowance;
- `jobseekersAllowance`: Jobseeker's Allowance; and
- `seissNetPaid`: income from the Self Employment Income Support Scheme.

No adjustment, correction, repayment, refund, withholding, gross/net split or
negative-value meaning is documented for these fields. The name `seissNetPaid`
is retained literally and is not interpreted as authority to derive a gross
amount, repayment or adjustment. State Pension generally is not represented by
the pensions field; the specifically documented lump-sum case appears in
`employments` as described above.

## Money, sign, precision and period semantics

At endpoint-schema level, every monetary-looking value above is only
`type: number`. The OpenAPI specification does not state:

- a currency field or endpoint-specific currency;
- minimum, maximum, sign or non-negativity;
- precision, scale, `multipleOf` or rounding rule;
- whether credits, repayments, refunds or adjustments can appear as negative
  numbers; or
- whether values are gross, net of tax or net of later corrections, except for
  the literal provider field names and descriptions recorded above.

The generic HMRC reference guide states that money is represented with two
decimal places and in GBP unless expressly documented otherwise. That is a
generic platform fact, not an endpoint-enforced JSON Schema restriction. A
later contract may preserve exact decimal input and enforce an independently
reviewed money policy, but this evidence does not authorize inventing sign,
rounding or adjustment semantics.

The tax year is the only documented represented period in the request. No
effective date, reconciliation-completion timestamp, source update timestamp,
pay date or sub-period field is documented in the response schema. Because the
schema is open, this does not claim that extensions can never appear; any such
field would require fresh provider evidence before it could acquire semantics.
Retrieval time must not be relabelled as source time.

## Presence, nullability and forward extensions

The endpoint schemas do not set `additionalProperties: false` on the top-level
object, employment items or the pensions/benefits object. The official contract
therefore does not establish a closed-world schema. Later parsing must not
invent one; any forward-extension retention or rejection policy is a Reserved
implementation rule requiring separate review.

No field in these endpoint schemas is declared nullable. An omitted optional
benefit field and an explicit JSON `null` are therefore distinct. This evidence
does not authorize coercing either to zero. The two top-level containers are
required: a response with `employments: []` and an empty
`pensionsAnnuitiesAndOtherStateBenefits` object is shape-valid under the literal
schema, but does not prove universal zero income or source completeness.

Array order is not identity, precedence or chronology. No pagination mechanism
is documented for this endpoint; absence of a pagination contract is not proof
that a response covers data outside the documented annual-summary population.

## Exact endpoint errors and no-data handling

The documented HTTP 400, 401 and 404 bodies use `application/json`. Every
documented error body requires string `code` and string `message`.

- HTTP 400: `SA_UTR_INVALID` or `TAX_YEAR_INVALID`;
- HTTP 401: `UNAUTHORIZED`;
- HTTP 404: `NOT_FOUND`, meaning that data is unavailable for the requested UTR
  and tax year.

HTTP 404 must remain unavailable evidence. It must not become an authoritative
empty or zero-income record. A valid HTTP 200 with zero employment items is
different from HTTP 404, but neither establishes that the customer has no
income outside this endpoint.

The endpoint specification does not document endpoint-specific rate limits,
retry timing, idempotency, fraud-prevention-header applicability or a required
fraud-header set. The generic reference guide documents generic errors, rate
limiting and fraud-prevention-header guidance; those do not fill the endpoint
gaps.

## PAYE Test Support dependency

The Individual Income overview describes a stateful sandbox and directs test
data setup to **Individual PAYE Test Support API 2.1 beta**, last updated
**21 August 2026**, in Sandbox only. That establishes the companion service and
environment, but not:

- the exact fixture endpoint or payload needed for this journey;
- available Individual Income scenarios and values;
- subscription or access approval;
- test-user/UTR ownership and visibility timing;
- reset, replay or cleanup behaviour; or
- the evidence that Reserved may safely retain from a sandbox run.

Those details require a separately evidenced sandbox package. They are not
inferred here.

## Provider facts, generic facts and Reserved inference

| Classification | Retained conclusion |
|---|---|
| Endpoint fact | Method, path, required path parameters, exact Accept value, OAuth scope, required response containers, field names/types/cardinality and endpoint error codes are recorded literally from Individual Income 1.2. |
| Endpoint fact | Availability depends on SA registration, reconciliation and return-processing state; a State Pension lump sum can appear as employment with reference `267/LS500`. |
| Generic platform fact | HMRC documents common environment, versioning, error, money, rate-limit and fraud-header conventions, but the endpoint OAS does not specialise all of them. |
| Reserved inference, not yet authorised | Individual Income is a candidate historic/reconciled annual-income source and may later be compared with Individual Employment and other evidence. It is not yet a canonical mapping or join contract. |
| Unresolved | Sign, endpoint-enforced precision, adjustment/refund semantics, cross-endpoint identity, endpoint-specific rate/fraud requirements and exact Test Support fixtures remain unknown. |

This separation is consistent with `docs/EXTERNAL_DATA_SPECIFICATIONS.md`:
Individual Income remains historic/reconciled tax-year evidence and is not a
documented current-payroll feed. Nothing in this capture upgrades its
subscription, sandbox-verification or activation status.

One cross-document version discrepancy remains explicit:
`docs/EXTERNAL_DATA_SPECIFICATIONS.md` names Individual PAYE Test Support 2.0,
whereas the current official service page reviewed for this capture identifies
2.1 beta, updated 21 August 2026. The older statement must be reconciled before
a Test Support package; it is not silently treated as current or corrected by
this one-file evidence capture.

## Hard gates and decision

The following remain unresolved and fail closed:

- Reserved application subscription and access approval;
- approved encrypted credential/key custody and token lifecycle;
- exact Individual PAYE Test Support fixture contract and retained-evidence
  controls;
- HTTP client, OAuth, callback and route implementation;
- live and sandbox execution evidence;
- endpoint-specific rate-limit/retry and fraud-header requirements;
- cross-endpoint identity resolution and ambiguity handling;
- provider-to-canonical mapping, decimal/sign policy, persistence and source
  priority;
- privacy, security, operational monitoring, independent integration and launch
  assurance; and
- production activation and release authority.

This capture closes only the public method/path, parameter, scope,
media-version, literal response-schema, endpoint-error and availability-evidence
gap for Individual Income 1.2. It does not implement or authorize a request
builder, response parser, HTTP transport, credential flow, fixture, provider
call, canonical income record, persistence, callback, sandbox use or production
activation.
