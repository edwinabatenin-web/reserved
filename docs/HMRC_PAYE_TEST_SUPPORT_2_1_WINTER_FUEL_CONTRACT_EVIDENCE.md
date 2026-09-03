# HMRC PAYE Test Support 2.1 Winter Fuel literal contract evidence

Status: **disabled local fixture support only; completeness UNVERIFIED**. This
contract is offline and network-inert. It does not establish production
provider availability, customer eligibility, canonical completeness, tax
treatment, calculation relevance or activation authority.

## 1. Exact retained endpoint facts

The local authority is
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`, especially sections
3–8.6 and 9–14. It retains exactly one operation here:

- HMRC Individual PAYE Test Support API 2.1, Sandbox-only;
- application-restricted OAuth client credentials with an empty scope set;
- `POST /individual-paye-test-support/{nino}/winter-fuel-payment-amount/annual-summary/{taxYear}`;
- operation ID `createWinterFuelPaymentAmountTestData`;
- NINO pattern `^[A-Z]{2}[0-9]{6}[A-Z]$` and tax-year pattern `^[0-9]{4}-[0-9]{2}$`;
- optional scenario values `HAPPY_PATH_1` (default), `HAPPY_PATH_2` (HTTP 404
  example) and `UNHAPPY_PATH_500` (HTTP 500 example);
- HTTP 201 `application/json` response requiring numeric `expectedStatus`, with
  optional object `expectedJson` that, when present, requires numeric
  `winterFuelPaymentAmount`; and
- open, non-nullable schemas. No per-operation error response body is documented.

The examples do not establish a rule coupling scenario to `expectedStatus` or
to the presence or value of `expectedJson`. No such coupling is implemented.

## 2. Reserved defensive implementation policy

The public request builder is keyword-only. Exact built-in strings are required;
scenario omission is distinct from presence and explicit null fails closed. The
NINO is validated first and discarded completely. No raw NINO, hash, suffix,
mask or enumerable NINO derivative is retained by any value or reconstruction
surface. The frozen, non-sendable request instead receives a fresh random
process-local correlation identity unrelated to NINO and binds operation,
method, path template, API version and media types, client-credentials grant,
empty scope, Sandbox-only state, tax year, and scenario presence/value/default
semantics.

The observer accepts only an exact validated request intent. HTTP 201 requires
exact `application/json` and exact built-in dictionaries. Numbers remain exact
built-in `int` or finite `Decimal`; bool, float, subclasses, null and coercion
are rejected. Defensive limits are 64 members per object, 32 unknown names, 256
characters per name, integer/Decimal magnitude at most 10^18, 38 Decimal
coefficient digits, 12 fractional places and a 38-digit Decimal integer shape
(`max(1, coefficient digits + exponent)`). These are Reserved safety bounds,
not HMRC sign, magnitude, scale, rounding, precision or exponent facts.

All names are validated before classification. Only safe, bounded unknown names
are retained; unknown values are untouched. A success binds its exact producing
request and the entire retained observation: `expectedStatus`, optional
`expectedJson` presence, exact Winter Fuel amount including int-versus-Decimal
and Decimal sign/exponent/digits, both levels of unknown names, and
`UNVERIFIED` completeness. Non-201 responses bind only the exact integer status
and producing request; media type and body are neither inspected nor retained.

Every public value and protocol surface revalidates exact type/layout through
an exact observation-kind dispatcher that directly invokes the corresponding
contract-class validator,
request/source/context coherence, retained semantics, an integrity digest and a
weak process-local issuance record. Copy and deepcopy return the validated
immutable value; pickle reconstruction structurally preflights all arguments,
rebuilds validated values, and creates new process-local issuance records.
Observation construction branches only over the two exact supported classes.
Subclasses and missing, extra, transplanted or low-level-mutated state fail
closed before unpacking, mutation, hostile keys, containers, members or
overridden validation/protocol hooks can run.

## 3. Bounded inference

The sole bounded inference is that the retained schema is sufficient for a
disabled local fixture intent/observation contract. The guarantee is only
process-local coherence plus mutation/substitution detection. It is not
provider authenticity, durable provenance, authorisation, attestation, secrecy,
replay prevention, evidence that any scenario outcome is complete, evidence
that a fixture becomes visible, or evidence that a Winter Fuel amount has
accounting, tax, cash, eligibility or product meaning. Python module privacy is
not a security boundary.

## 4. Unresolved gates

Application subscription/access, credential custody, visibility timing,
re-POST/replacement behaviour, reset/deletion, endpoint-specific retry/rate and
fraud-header requirements, NINO-to-UTR linkage, sandbox execution evidence,
production availability, canonical mapping, calculation relevance, customer
experience and activation remain unresolved and fail closed. No provider call,
test-user creation, persistence, join, total, HICBC rule or Scotland/VAT/product
behaviour is authorised by this candidate.
