# HMRC PAYE Test Support 2.1 Child Benefit contract evidence

Status: **implementation-derived candidate awaiting independent review**.
Date: **2 September 2026**.

## Implemented boundary

This candidate implements a dependency-free, network-inert typed value contract
for the documented request and HTTP 201 response of:

`POST /individual-paye-test-support/sa/{utr}/child-benefit-entitlement/annual-summary/{taxYear}`

Provider facts come only from the authoritative local
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md` capture. The implementation:

- validates a ten-ASCII-digit UTR and `YYYY-YY` tax year, then immediately
  discards the UTR;
- preserves tax year, scenario omission/presence and the three documented
  scenario values in an immutable, non-sendable request intent;
- accepts only an exact built-in integer HTTP status `201`, checking status
  before content type or body;
- requires an exact built-in integer response `expectedStatus` and preserves it
  literally without imposing a scenario-to-response relationship;
- distinguishes omitted `expectedJson` from a present object and rejects an
  explicit null;
- when present, requires exact `childBenefitEntitlement` numeric evidence as a
  built-in `int` or finite `Decimal`, retaining it without coercion or rounding;
- preserves bounded, safe unknown member names at response and `expectedJson`
  layers without retaining or traversing their values; and
- binds every response observation to the validated request intent's retained
  tax-year and scenario facts, including direct construction and replacement;
  the request is required at construction but is not retained; and
- validates every response object member name as an exact built-in string
  before classifying it as documented or unknown.

Local defensive limits reject excessive object members, unknown names, name
lengths, integer magnitude, Decimal coefficient size, Decimal fractional places
and Decimal magnitude. These limits are safety policy only. They are not HMRC
amount, precision, scale, range or sign rules.

All retained value objects validate their invariants in public constructors.
Response `dataclasses.replace` must re-enter through a freshly supplied exact
validated request intent; free-floating request identity fields are not public
constructor or replacement inputs. Standard copy, deep-copy and pickle paths
retain no request or UTR and preserve the already validated retained facts.
Request `replace` must re-enter via a newly supplied, validated UTR because no
UTR is retained.

## Verification performed

Commands used `PYTHONDONTWRITEBYTECODE=1`; pytest used `-p no:cacheprovider`.

- Focused contract suite:
  `python3 -m pytest -p no:cacheprovider tests/test_hmrc_paye_test_support_child_benefit_contract.py -q`
  — **69 passed**.
- Compatibility matrix:
  `python3 -m pytest -p no:cacheprovider tests/test_provider_http_boundary.py tests/test_hicbc_isolation.py tests/test_hicbc_bounded_evidence_adequacy.py tests/test_paye_evidence_capture.py -q`
  — **124 passed**.
- Complete local suite:
  `python3 -m pytest -p no:cacheprovider -q`
  — **4,272 passed** (the exact count was confirmed by collection after the
  successful run; no test suite was rerun to derive it).

The focused tests cover scenario enumeration/default omission, explicit-null
rejection, path shapes and UTR disposal, status typing and non-201 body
non-traversal, request/response binding, optional-object presence, required
members, exact numeric preservation/rejection, both open-schema layers,
hostile unknown values, unsafe names, lifecycle coherence, and absence of
network, credential, persistence, activation and product-engine imports. They
also cover documented-name string subclasses at both object layers, controlled
hostile-name classification, required exact request construction and response
replacement through a supplied exact validated request intent.

## Limitations and activation gates

This candidate is a parser/value contract only. It does not make an HMRC call,
hold credentials, create a test user, persist data, calculate HICBC, map to a
canonical product value, activate a provider, or establish production access.
It supplies no endpoint-specific error body or named OAuth scope. It does not
establish re-POST replacement/reset semantics, visibility timing, read-side
availability, or that an Individual Benefits read will return a created fixture.

No sandbox verification, provider activation, launch readiness or independent
assurance is claimed. Subscription approval, credential custody, transport,
provider execution, read-side verification, operational controls and review of
the exact uncommitted diff remain gated. Independent owning-task review is
required before this evidence can be accepted.
