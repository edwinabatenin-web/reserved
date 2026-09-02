# HMRC Individual Income 1.2 — disabled literal contract evidence

Observation date: **1 September 2026**. Status: **network-inert literal
request/response contract implemented; sandbox use, integration and activation
remain gated**.

This document records the implementation decisions for
`reserved/providers/hmrc_individual_income_contract.py` and its tests. It is a
companion to `docs/HMRC_INDIVIDUAL_INCOME_1_2_ENDPOINT_EVIDENCE.md`, which is
the only endpoint-specific authority used here. No HMRC API was called and no
credential, test user, UTR, sandbox fixture or production data was accessed.

## Authority boundary

This package treats the reviewed endpoint evidence as authority only for the
facts it states. It does not transfer authority from any other OH+DS lane and
does not invent endpoint fields or semantics. The documented operation is:

`GET /individual-income/sa/{utr}/annual-summary/{taxYear}`

with `Accept: application/vnd.hmrc.1.2+json` and OAuth scope
`read:individual-income`.

## Implemented contract surface

The module exposes the smallest useful surface:

- exact constants: API name `individual-income`, version `1.2`, HTTP method
  `GET`, sandbox origin `https://test-api.service.hmrc.gov.uk`, path template
  `/individual-income/sa/{utr}/annual-summary/{taxYear}`, Accept header
  `application/vnd.hmrc.1.2+json`, OAuth scope `read:individual-income`, and
  success/error JSON content type `application/json`;
- the documented immutable status-to-code mapping
  `HMRC_INDIVIDUAL_INCOME_ERROR_STATUS_CODES` and the nested frozensets
  `HMRC_INDIVIDUAL_INCOME_400_CODES`, `HMRC_INDIVIDUAL_INCOME_401_CODES` and
  `HMRC_INDIVIDUAL_INCOME_404_CODES`;
- `build_individual_income_request(*, utr, tax_year)`;
- `observe_individual_income_response(request, *, status_code, content_type, payload)`.

The request intent `IndividualIncomeRequestIntent` is a frozen dataclass that
is not, does not inherit from, and does not convert by default into the generic
sendable `ProviderRequest`. It owns no HTTP client, transport, credential,
authorization header, persistence, routing, provider-to-canonical mapping,
production origin or activation path.

## Request validation and UTR discard

`IndividualIncomeRequestIntent` has exactly one construction boundary:
`IndividualIncomeRequestIntent(utr=..., tax_year=...)`. The UTR is validated as
exactly ten ASCII digits using `[0-9]{10}` and discarded immediately. The
character class is ASCII-only, so `str.isdigit()`/`isdecimal()`/`isnumeric()`
semantics are never used and full-width or Arabic-Indic Unicode digits are
rejected. The tax year is validated against the captured exact regex
`^[0-9]{4}-[0-9]{2}$`.

Method, sandbox origin, path template, Accept header, scope and redacted path
are all derived internally (`init=False`), so they cannot be supplied to the
constructor, forged with `dataclasses.replace`, or assigned on the frozen
instance. The redacted path is computed by replacing the UTR placeholder with
the literal marker `[UTR-REDACTED]` and the tax year placeholder with the
validated tax year. No UTR-bearing path or recoverable equivalent is retained
in ordinary, private, name-mangled, copied, equality/hash, representation or
conversion state. Request repr is unconditionally non-value-bearing, while
custom equality and hash validate the exact complete request state before
using any retained value. Two requests built from different UTRs and the same
tax year compare equal and leave identical retained state. Copy and deepcopy
validate that state and return the same immutable instance. Reduction and
pickle validate the complete source and carry only the seven-field canonical
UTR-free retained snapshot. Reconstruction revalidates that snapshot and does
not manufacture, retain or serialize a UTR.
`build_individual_income_request(*, utr, tax_year)` remains a thin keyword-only
convenience over the validated construction boundary.

## Number boundary

The decoded JSON-number boundary accepts only exact built-in `int` and exact
`Decimal` values. `bool` (a subclass of `int`), `float`, `str`, every numeric
subclass (including `IntEnum`, `Fraction`, and `int`/`Decimal` subclasses),
`NaN` and infinities are rejected. Values must be finite.

The exact value is retained as `int | Decimal` without quantising, rounding,
sign change (including negative zero) or exponent change. `Decimal("-0.000")`
is retained with sign `1` and exponent `-3`. Upstream float parsing is outside
this offline package; a later transport must decode JSON floats with
`parse_float=Decimal`.

### Reserved defensive numeric bounds (not endpoint facts)

The endpoint schema declares money only as `type: number` and states no
minimum, maximum, sign, scale, `multipleOf` or rounding rule. The following
finite bounds are Reserved defensive policy, labelled and boundary-tested, and
are not endpoint sign/precision/magnitude facts:

- maximum magnitude `10**18` for `int` and `Decimal`;
- maximum `12` fractional places for `Decimal`;
- maximum `38` significant digits (retained as a clearly labelled bound; with
  the magnitude and scale bounds above it is not independently reachable).

## Literal response and error rules

HTTP 200 requires exact `application/json` and an exact built-in `dict` payload
containing both `employments` and `pensionsAnnuitiesAndOtherStateBenefits`.
`employments` is an exact built-in `list` of zero or more exact built-in `dict`
items; each item requires an exact built-in string `employerPayeReference` and a
numeric `payFromEmployment` on the number boundary. No employer identity, date,
tax-deducted amount, currency, sign, precision, ordering, uniqueness or join
authority is inferred. The pensions/benefits container is an exact built-in
`dict` whose four documented members are optional numbers; omission is `None`
and is never coerced to zero, while explicit `null` is rejected.

An empty `employments` list and empty benefits object are preserved as
shape-valid but completeness-unverified (`UNVERIFIED`). Neither means universal
zero income.

For HTTP 400, 401 and 404 the module requires exact `application/json`, exact
built-in string `code` and `message`, and the documented immutable
status/code pairings:

- 400: `SA_UTR_INVALID` or `TAX_YEAR_INVALID`;
- 401: `UNAUTHORIZED`;
- 404: `NOT_FOUND`.

HTTP 404 is retained as unavailable evidence, not as an authoritative empty or
zero-income record. Undocumented statuses, media types, codes, malformed
bodies, explicit nulls and mismatched status/code pairs fail closed.

The raw response payload and the error `message` are never retained. Among the
provider error-body facts, the error observation keeps only `status_code` and
`code`; it also carries the UTR-free request context and derived annual
identity described below. The `message` is validated as a string (Reserved
length bound only) and then discarded. Validation failures raise
`HMRCIndividualIncomeContractError` with constant, non-echoing messages.

## Unknown names and defensive key bounds

Bounded safe additive unknown names are accepted for forward compatibility, but
unknown values are never retained, traversed, copied, stringified, compared,
hashed, logged or otherwise inspected. Before classification at top-level,
employment-item, benefits and error-body levels the module requires exact
built-in string keys and applies the following clearly labelled Reserved
defensive bounds:

- maximum object members per JSON object: `64`;
- maximum additive unknown keys per object: `32`;
- maximum key-name length: `256` characters;
- maximum retained string-value length: `4096` characters;
- maximum employment items per response: `10_000`.

Keys are retained only when every character is outside Unicode general category
`C`. The rule `unicodedata.category(character).startswith("C")` rejects ASCII
and C1 controls (`Cc`), format/bidi/zero-width controls (`Cf`), surrogates
(`Cs`), private-use (`Co`) and unassigned/noncharacter code points (`Cn`) before
unknown-name retention at top-level, employment-item, benefits and error-body
levels. Ordinary international letters, combining marks, CJK, emoji, spaces and
Unicode separator whitespace remain accepted where otherwise within bounds.
Empty names, oversized names, mixed/non-string keys and excessive objects fail
closed before any value is dereferenced or iterated.

## Deep immutability of observations

The nested literal-fact observation classes remain frozen dataclasses whose
`__post_init__` revalidates their full package invariants:

- `EmploymentItemObservation` revalidates the exact built-in bounded string
  `employer_paye_reference`, the exact built-in `int`/`Decimal`
  `pay_from_employment`, and an exact bounded `frozenset` of safe unknown names;
- `PensionsBenefitsObservation` requires `present_fields` and `absent_fields`
  to be exact disjoint frozensets that are exhaustive over the four documented
  benefit names, and each optional numeric value to be non-`None` exactly when
  its provider field is present.

The top-level success and error response observations are frozen dataclasses
created by private parser factories with an exact immutable source context.
Every retained field is non-init. Public construction and top-level
`dataclasses.replace`, including unchanged or apparently unrelated fact-field
replacement, are intentionally unsupported. This preserves provenance because
standard dataclass replacement can only carry source state through an
`init=True` field, which callers could then substitute. The success factory
requires an exact tuple of exact
`EmploymentItemObservation` items, an exact `PensionsBenefitsObservation`,
bounded safe unknown names and exact `UNVERIFIED` completeness. The error
factory requires an exact built-in status/code on a documented pairing and
bounded safe unknown names.

No current compatibility consumer requires top-level response replacement;
the package tests were the only consumer asserting that convenience. The
nested literal-fact dataclasses retain their ordinary validated replacement
semantics. Validated copy and deepcopy of top-level responses return the same
deeply immutable object. Reduction and pickle validate complete source state
and serialize only canonical UTR-free state. Before copy, deepcopy,
equality, hash, reduction or pickle uses a top-level
observation, the complete exact observation, nested request, nested literal
observations, private parser-established source context and request-binding
coherence are revalidated. Raw response mappings and unknown values are never
retained.

## Reserved request-binding correction

This revision corrects one bounded association defect. Previously the observer
validated a request before parsing, but its returned observations did not
retain any request-derived annual context. The corrected object records the
request context supplied to the offline observation boundary. It does not prove
that a network response was produced by HMRC or by that request; authenticity,
transport correlation and live/sandbox evidence remain outside this module.

The correction retains the exact canonical UTR-free request intent, a private
parser-established source context, an immutable tuple snapshot of all seven
canonical retained request fields, and a derived `tax_year` on every success
(`IndividualIncomeAnnualSummaryObservation`) and documented 400/401/404 error
(`IndividualIncomeErrorObservation`) observation created by the parser boundary.
The tax year is derived solely from the private source context and is never
accepted as public constructor or replacement input:

- both response classes mark every field non-init; parser factories supply a
  separate private source context from which request, immutable
  canonical-state snapshot and tax year are assigned and against which they
  are validated;
- `dataclasses.replace` cannot reconstruct either top-level response, whether
  the caller omits or supplies source context. Incomplete or incoherent
  low-level mutation — including substitution of request, private binding and
  year while the parser-established source context remains unchanged, or
  substitution of that context alone — fails validation for success and every
  documented error pairing;
- construction revalidates the full exact request intent — exact
  `IndividualIncomeRequestIntent` type, exact built-in `__dict__`, exact key
  set, exact derived constants and a redacted path coherent with the validated
  tax year — rather than trusting the request's construction history;
- request copy and deepcopy validate complete state before returning the same
  immutable instance; request reduction/pickle validates before emitting a
  UTR-free canonical reconstruction recipe;
- observation copy and deepcopy validate their exact complete state,
  the complete nested request, every retained nested employment/benefits
  observation, and coherence among the original binding, retained request and
  derived tax year before returning; observation reduction/pickle validates
  first and emits only a UTR-free reconstruction recipe;
- request and response repr are constant and non-value-bearing. Custom equality
  and hash validate complete state before using retained values, so a raw UTR
  injected by bypassing frozen assignment is neither rendered nor consumed as
  valid state;
- the raw UTR remains absent from ordinary retained state, equality/hash, repr,
  copy, deepcopy and pickle. Requests built from different UTRs for the same
  tax year remain observationally indistinguishable.

### Enforceable Python threat-model boundary

The value objects enforce their invariants at public construction, observation,
copy/deepcopy, equality/hash, reduction/pickle and every
`dataclasses.replace` route. They also detect missing, extra, malformed or
partially/incoherently mutated retained state before those protocol surfaces
use it.

They do not claim to detect arbitrary coordinated in-process memory rewriting.
Python code with permission to call `object.__setattr__` can replace every
mutually coherent public and private field, including the source context, from
another already-valid peer. At that point no independent state remains inside
the object from which to distinguish the rewrite. Preventing such code is a
process isolation, code-review and code-trust responsibility; it is not a
property this immutable value object can truthfully provide. This limitation
does not reopen any public constructor or replacement route.

No employer join, source precedence, provider completeness, canonical mapping,
PAYE evidence, tax, cash, persistence, transport, cross-endpoint join or
activation surface is added by this correction. Only the canonical UTR-free
request context asserted at the offline parser boundary and its derived annual
identity are retained.

## String values: no evidenced minLength

The documented schemas declare no `minLength`. Empty and whitespace-only
`employerPayeReference` and error `message` values are therefore accepted as
schema-valid but semantically unverified. Only the Reserved string-length bound
is applied; no minimum length or non-whitespace requirement is invented.

## Explicitly kept out of scope

This package does not emit or imply `PayeEvidence`, canonical accounting
evidence, annual-tax inputs, cash-obligation inputs, customer presentation data,
provider completeness, production readiness or cross-endpoint matching
authority. The State Pension lump-sum reference `267/LS500` is a literal
provider fact only; no special downstream tax or identity behaviour is attached
to it. Completeness remains `UNVERIFIED`.

## Remaining gates (fail closed)

The following remain unresolved and are not implemented or authorized here:

- Reserved application subscription and access approval;
- approved encrypted credential/key custody and token lifecycle;
- exact Individual PAYE Test Support 2.1 fixture contract and retained-evidence
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

This is a review-ready, uncommitted candidate limited to the exact three
modified paths in this package. It does not claim approval, independent
assurance, integration, launch readiness or production/contractual authority.
