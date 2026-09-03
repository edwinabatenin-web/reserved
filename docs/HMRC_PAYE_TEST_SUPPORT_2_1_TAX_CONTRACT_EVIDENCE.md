# HMRC PAYE Test Support 2.1 tax contract — implementation evidence

Status: **UNVERIFIED, Sandbox-only implementation candidate for independent review**.
Date: **3 September 2026**.

## Exact boundary

`reserved/providers/hmrc_paye_test_support_tax_contract.py` represents only the
documented `createTaxSummaryTestData` operation:

`POST /individual-paye-test-support/sa/{utr}/tax/annual-summary/{taxYear}`

The request intent binds Individual PAYE Test Support API 2.1, the documented
path template, `application/vnd.hmrc.2.1+json` Accept media type,
`application/json` request/response media type, application-restricted OAuth
Client Credentials grant metadata with no named scopes, beta/Sandbox-only
status, tax year, and exact scenario omission/presence semantics. A UTR must be
an exact string of ten ASCII digits. It is discarded immediately after
validation; no raw, masked, suffix, digest, or other enumerable UTR derivative
is retained. An omitted scenario records absence and produces the documented
`HAPPY_PATH_1` default response context. Explicit null is rejected. The only
other retained request discriminator is a random process correlation value
which is independent of the UTR.

The intent is frozen, redacted and deliberately non-sendable. It owns no HTTP
client, rendered URL, provider request, headers, body, token, credential,
transport, persistence, routing or activation behaviour.

This intentionally replaces the former public scenario-only
`TaxTestSupportRequest(scenario=...)` constructor: that name now denotes the
UTR/tax-year create intent. Scenario-body callers must migrate to the truthful
public `TaxTestSupportRequestBody` compatibility value; the legacy
`parse_tax_test_support_request()` parser returns that same public type. This is
a documented public API transition, not unchanged constructor compatibility.

## Bound observation

`observe_create_tax_summary_response` is the single request-bound observation
boundary. It first revalidates the exact request state. A non-exact/non-201
status fails before content type or payload access. HTTP 201 then requires exact
`application/json` and the documented payload shape.

The issued `TaxSummaryCreated` binds its producing request identity, a unique
source-observation identity, status/content type, effective scenario and its
presence, `UNVERIFIED` completeness, every employment item and its order, both
pensions/benefits optional members, the refund member, all presence/absence
sets, and bounded unknown member names at every open-schema layer. Unknown
values are never accessed or retained. Integers remain exact built-in integers.
Decimals bind their exact type, sign, coefficient digits and exponent, including
negative zero and trailing fractional zeroes.

The effective scenario is derived canonically from the exact retained request
identity: retained presence must equal request presence, and retained scenario
must equal the explicit request literal or `HAPPY_PATH_1` when omitted. The
invariant is checked before construction, integrity computation, issuance
registration and reconstruction, so contradictory or hostile serialized inputs
fail closed without protocol-hook dispatch.

Every public value/protocol surface revalidates exact type, state keys,
containers and members before equality, hashing, iteration, deepcopy or pickle
hooks can be dispatched. Per-instance nested identities detect substitution by
an independently valid equal-looking nested value. A complete semantic seal and
process-local issuance registry detect mutation, hand-built lookalikes,
cross-request transplantation, coordinated request/source relabelling, and
wholesale provenance/integrity swaps. Copy/deepcopy return the validated frozen
instance. Pickle reconstruction validates all supplied state and registers a
new local instance with the same bound identity.

`parse_tax_summary_created` remains as a body-only compatibility boundary. Its
result is the same public value type but is explicitly exposed as
`request_bound == False`, with `request_identity` and `source_identity` both
`None`. It must not be represented as request-bound or independently assured.
Direct construction and `dataclasses.replace` compatibility for the rewritten
`TaxSummaryCreated` observation is intentionally unavailable; observations are
boundary-constructed or validated through the documented parse compatibility
boundary only.

## Accurate limitations

The binding and seal enforce only process-local coherence plus mutation and
substitution detection. Random correlation values and SHA-256 state digests are
not secrets or provider attestations. This code does **not** establish provider
authenticity, authorization, durable provenance, cryptographic secrecy,
attestation, replay prevention, fixture visibility, subsequent-read completeness
or production suitability.

There is no network call, credential handling, persistence, controller/route,
activation, product-engine conversion, payment, customer UI, metadata change,
or provider authority in this boundary. Provider access, transport, operational
behaviour and any activation decision remain outside scope.

## Verification scope

Focused tests cover malformed request values; omission/default/null behaviour;
UTR non-retention through representation, equality/hash, copy/deepcopy and
pickle; exact request/source binding; full response/numeric/presence/unknown-name
semantics; non-201 short-circuiting; direct and low-level state mutation;
identical-payload cross-request swaps; coordinated relabelling; exact-type,
container, key and member rejection; hostile protocol hooks; truthful legacy
parser status; and continued network/credential/routing/persistence prohibition.
It also covers explicit `HAPPY_PATH_1`/`HAPPY_PATH_2`, omitted/default and
contradictory reconstruction, including hostile scenario/presence inputs with
zero hostile-hook dispatch.

Verification results are recorded in the owning review task output rather than
claimed as permanent provider evidence here.
