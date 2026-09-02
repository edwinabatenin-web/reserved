# HMRC PAYE Test Support 2.1 benefits contract — implementation evidence

Status: **implementation-derived and awaiting independent review**.

This record describes the local, network-inert implementation candidate for
only `POST /individual-paye-test-support/sa/{utr}/benefits/annual-summary/{taxYear}`
(`createBenefitsSummaryTestData`). Provider facts come only from
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`. No provider call,
sandbox exercise, credential, customer/production data, subscription,
activation, or read-side observation was used.

## Implemented boundary

- The request intent accepts an exact built-in string of ten ASCII UTR digits,
  validates it, and immediately discards it. It retains only a `YYYY-YY` tax
  year and the scenario presence/value facts.
- Scenario omission is retained distinctly from presence. A present value must
  be exactly `HAPPY_PATH_1` or `HAPPY_PATH_2`; explicit null fails closed at
  every public construction path.
- The response observer requires the exact request-intent type. The response
  constructor also requires that intent as a non-retained `InitVar` and derives
  tax year and scenario facts from it. It exposes no free-floating identity
  constructor fields. `dataclasses.replace` consequently requires a fresh
  validated request intent.
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
- All observations are frozen and redacted. Constructors and explicit pickle
  rebuild functions revalidate invariants; immutable copies are coherent.
  Completeness is always exactly `UNVERIFIED`.

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
- request-bound construction and replacement-derived identity;
- zero/one/multiple employment boundaries and required members;
- all eight numeric fields, omission/zero/null, exact int/Decimal preservation,
  Decimal negative zero, and malformed numeric rejection;
- safe unknown-name-only metadata and hostile unknown values;
- documented-name injection, subclasses, unsafe names/references, and limits;
- direct construction, replacement, copy, deepcopy, pickle, immutability, and
  exact `UNVERIFIED` completeness.

All commands used `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`:

- Focused benefits-contract suite: passed.
- Affected matrix: passed. It included the focused suite, all three existing
  PAYE Test Support employment/income/tax contract suites, provider HTTP
  boundary, PAYE evidence capture, PAYE reconciliation, HICBC isolation, and
  HICBC bounded-evidence adequacy.
- Full local suite: passed once.

The exact commands and authorized-file SHA-256 hashes are recorded in the
worker handoff. No suite was repeated merely to obtain a count.

## Hard gates and non-claims

The candidate must finish with the required unchanged branch, HEAD and tree,
exactly the three authorized untracked files, their SHA-256 hashes, and no
bytecode or pytest caches. This document does not claim sandbox verification,
provider activation, read-side visibility, independent assurance, launch
readiness, error-body semantics, reset semantics, replacement semantics at the
provider, or a named OAuth scope.
