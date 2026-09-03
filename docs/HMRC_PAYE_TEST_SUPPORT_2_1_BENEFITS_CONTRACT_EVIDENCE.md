# HMRC PAYE Test Support 2.1 benefits contract — implementation evidence

Status: **implementation-derived and awaiting independent review**.

This record describes the local, network-inert implementation candidate for
only `POST /individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}`
(`createBenefitsSummaryTestData`). Provider facts come only from
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`. No provider call,
sandbox exercise, credential, customer/production data, subscription,
activation, or read-side observation was used.

## Implemented boundary

- The request builder accepts an exact built-in string of ten ASCII UTR digits,
  validates it, and discards it before retained construction. It never hashes,
  serializes, or derives another identifier from the UTR.
- The retained request identity is a canonical immutable tuple containing only
  the fixed `POST` method, Sandbox origin, documented path-template meaning,
  request Accept and Content-Type, response Content-Type, API version, tax year,
  and exact scenario presence/value. The path remains a template: it contains
  no substituted UTR.
- Scenario omission is retained distinctly from presence. A present value must
  be exactly `HAPPY_PATH_1` or `HAPPY_PATH_2`; explicit null fails closed at
  every public construction path.
- The response observer requires an exact, fully revalidated request-intent
  type before it examines status, content type, or payload. The observation
  retains the exact canonical identity and an independently checkable canonical
  binding tuple.
  Public tax-year/scenario properties are derived from that retained context;
  no free-floating copies exist. `dataclasses.replace` cannot rebind an
  observation.
- A non-201 status fails before content type or body access. Success requires
  exact built-in integer `201` and exact built-in string `application/json`.
- `employments` is required and must be a bounded, non-empty exact list. Source
  order is preserved only as shape; no identity, chronology, or precedence is
  attached. Each item requires an exact safe built-in string
  `employerPayeReference`; empty and ordinary-space strings are permitted.
- All eight documented benefit members are optional. Presence is recorded in a
  frozenset, so omission remains distinct from exact zero. Explicit null fails.
  Values are preserved without coercion or rounding only when their exact type
  is built-in `int`, or built-in finite `Decimal` within Reserved limits. No
  sign, scale, or business amount rule is inferred.
- Open-schema extensions retain only bounded, immutable, validated unknown
  member names at top and employment levels. Every key is exact-validated
  before classification. Unknown values are not fetched, traversed, copied,
  retained, stringified, or represented.
- Requests, employments, and observations are frozen and redacted. Exact-type
  and exact-state validators reject subclasses, missing/extra state, malformed
  built-in values, low-level edits, and descriptor/year/scenario substitution
  before instance-controlled hooks are read. Exact state-dictionary keys and
  retained frozenset members are type-checked by iteration before hashing,
  equality, membership, or subset operations can dispatch their hooks. Tuple
  members are likewise exact-type-checked before tuple comparison. Public
  properties and repr/equality/hash/copy/deepcopy/pickle paths dispatch only to
  trusted class-level validators after exact layout checking; injected
  validator/helper callables and an injected `present_fields.__rsub__` hook are
  never invoked.
  A deterministic SHA-256 integrity
  digest covers every retained request, binding, payload, response-contract,
  unknown-name, and completeness field. Coordinated transplantation, mutation,
  and reconstruction with a digest from different state therefore fail closed.
  Pickle reconstruction validates the serialized digest and never issues a new
  one. Equality, hashing, copy, deepcopy, and pickle are coherent. Completeness
  remains exactly `UNVERIFIED`.

## Reserved safety limits (not provider rules)

The implementation defensively bounds objects to 64 members, unknown names to
32 per object, member names to 256 characters, employer references to 4096
characters, and employments to 10,000 items. Category-C Unicode characters are
rejected in retained strings and names. Integers are bounded to absolute
`10^18`; Decimals are finite and bounded to 38 coefficient/integer digits, 12
decimal places, and absolute `10^18`. These are local safety limits only.

## Focused test evidence

`tests/test_hmrc_paye_test_support_benefits_contract.py` independently covers:

- constants, path, operation, Sandbox-only and network/product isolation;
- UTR/tax-year validation and UTR non-retention;
- both scenario values, omission, and explicit-null rejection;
- exact status/media type and non-201 content/body non-traversal;
- request-bound construction and replacement rejection;
- exact omitted/`HAPPY_PATH_1`/`HAPPY_PATH_2` request-to-observation binding;
- cross-scenario, cross-year, fixed-descriptor, and coordinated substitution;
- direct construction/reconstruction, replace, subclasses, missing/extra state, low-level
  mutation, and malformed built-in state without hostile-hook invocation;
- request, employment, and observation repr, left/right equality, hash, copy,
  deepcopy, pickle, and property access under validator/helper shadowing, with
  zero hostile-hook invocation (including armed colliding state keys,
  `present_fields`/`absent_fields`, and unknown-name frozenset members);
- request and observation equality/hash/copy/deepcopy/pickle reconstruction;
- raw UTR and UTR-derived identity absence from retained state, integrity
  digest, repr, constant errors, and pickle bytes;
- zero/one/multiple employment boundaries and required members;
- all eight numeric fields, omission/zero/null, exact int/Decimal preservation,
  Decimal negative zero, and malformed numeric rejection;
- safe unknown-name-only metadata and hostile unknown values;
- documented-name injection, subclasses, unsafe names/references, and limits;
- direct construction, replacement, copy, deepcopy, pickle, immutability, and
  exact `UNVERIFIED` completeness.

The exact validation commands, outcomes, and final authorized-file SHA-256
hashes are recorded in the review handoff produced with this candidate.

## Hard gates and non-claims

The candidate must finish with the required unchanged branch and HEAD and only
the three authorized modified paths. The digest is deterministic consistency
checking, not cryptographic authenticity, origin attestation, or unforgeable
provenance: Python module internals are accessible and a caller deliberately
recomputing a digest can construct internally consistent synthetic state. This
document does not claim sandbox verification, provider activation, read-side
visibility, independent assurance, launch readiness, error-body semantics,
reset semantics, replacement semantics at the provider, or a named OAuth scope.
