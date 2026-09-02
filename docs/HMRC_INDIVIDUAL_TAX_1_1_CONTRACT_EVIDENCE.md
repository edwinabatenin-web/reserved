# HMRC Individual Tax 1.1 — disabled literal contract evidence

Observation date: **1 September 2026**. Status: **network-inert literal
request/response contract implemented; sandbox use, integration and activation
remain gated**.

This document records the implementation decisions for
`reserved/providers/hmrc_individual_tax_contract.py` and its tests. It is a
companion to `docs/HMRC_INDIVIDUAL_TAX_1_1_ENDPOINT_EVIDENCE.md`, which is the
only endpoint-specific authority used here. No HMRC API was called and no
credential, test user, UTR, sandbox fixture or production data was accessed.

This document separates five concerns:

1. authoritative endpoint facts;
2. the Reserved request-binding correction;
3. defensive/fail-closed policy;
4. bounded inference;
5. unresolved provider, transport, cross-endpoint, completeness, privacy,
   security and activation gates.

## 1. Authoritative endpoint facts

The reviewed endpoint evidence is authority only for the facts it states. This
package does not transfer authority from any other OH+DS lane and does not
invent endpoint fields or semantics. The documented operation is:

`GET /individual-tax/sa/{utr}/annual-summary/{taxYear}`

with `Accept: application/vnd.hmrc.1.1+json` and OAuth scope
`read:individual-tax`.

The module exposes the smallest useful, non-sendable surface:

- exact documentation constants only: API version `1.1`, HTTP method `GET`,
  path template `/individual-tax/sa/{utr}/annual-summary/{taxYear}`, sandbox
  origin `https://test-api.service.hmrc.gov.uk` (metadata only), Accept header
  value `application/vnd.hmrc.1.1+json`, OAuth scope label
  `read:individual-tax` (metadata only), and success/error JSON content type
  `application/json`;
- the documented immutable status-to-code mapping
  `HMRC_INDIVIDUAL_TAX_ERROR_STATUS_CODES` and the nested frozensets
  `HMRC_INDIVIDUAL_TAX_400_CODES`, `HMRC_INDIVIDUAL_TAX_401_CODES` and
  `HMRC_INDIVIDUAL_TAX_404_CODES`;
- `build_individual_tax_request(*, utr, tax_year)`;
- `observe_individual_tax_response(request, *, status_code, content_type, payload)`.

The module owns no HTTP client, transport, credential, token, authorization
header, persistence, routing, provider-to-canonical mapping, production origin
or activation path. No production origin is encoded.

## 2. Reserved request-binding correction

This section records the Reserved correction that binds every observation to
the exact validated request intent that produced it, retaining the tax year
only as request-derived identity.

### Request intent

`IndividualTaxRequestIntent` is a frozen, slotted, keyword-only dataclass with
exactly one construction boundary: `IndividualTaxRequestIntent(utr=...,
tax_year=...)` (and its thin convenience wrapper
`build_individual_tax_request(*, utr, tax_year)`).

The raw `utr` is a construction-only value: it is validated as exactly ten
ASCII digits using `[0-9]{10}` and immediately discarded. The character class
is ASCII-only, so `str.isdigit()`/`isdecimal()`/`isnumeric()` semantics are
never used and full-width or Arabic-Indic Unicode digits are rejected.

The tax year is the only request-derived identity retained. It is validated
against `^[0-9]{4}-[0-9]{2}$`. The remaining retained fields are derived
internally from documented constants and can never be supplied, forged or
replaced through the public constructor, `dataclasses.replace`, copy, deepcopy
or pickle:

- `method` (`GET`),
- `sandbox_origin` (`https://test-api.service.hmrc.gov.uk`),
- `path_template` (`/individual-tax/sa/{utr}/annual-summary/{taxYear}`),
- `accept` (`application/vnd.hmrc.1.1+json`),
- `scope` (`read:individual-tax`),
- `redacted_path` (the path template with `{utr}` replaced by the
  `[UTR-REDACTED]` marker and `{taxYear}` replaced by the validated tax year).

The request additionally retains a private, non-init `_tax_year_binding`
snapshot of the originally validated tax year. It is excluded from
representation, equality and hashing and contains no UTR. Full-state validation
requires the public `tax_year`, the derived redacted path and this original
snapshot to remain mutually coherent, so a coordinated post-construction change
of both public year-bearing fields is rejected at observation, copy, deepcopy
and pickle boundaries rather than being accepted as a different-year request.

The raw UTR is never present in any field, so it cannot leak through ordinary,
private, name-mangled, serialized, copied, equality/hash, representation or
conversion state. The intent is a slotted class with no `__dict__`; `vars()` and
attribute access to `__dict__` fail. The detailed `repr` exposes only the
constant-derived descriptors, the validated tax year and the redacted path, and
never the raw UTR. `copy.copy` / `copy.deepcopy` return the same deeply
immutable instance. `__reduce__` reconstructs through
`_rebuild_individual_tax_request_intent(tax_year)`, which re-validates the tax
year and recomputes every constant-derived descriptor, so a forged pickle cannot
inject an unvalidated retained field or an incoherent redacted path.

`dataclasses.replace` cannot inject or alter the tax year independently. The
only accepted re-entry is through the validated `utr`/`tax_year` boundary;
attempting to replace a derived field (`method`, `sandbox_origin`,
`path_template`, `accept`, `scope`, `redacted_path`) or to omit the required
`utr` raises `TypeError`. A valid different-year request always recomputes the
redacted path and never produces mixed-year state.

### Observation binding

`observe_individual_tax_response` accepts only an exact
`IndividualTaxRequestIntent`; subclasses and lookalikes fail closed before any
status code, content type or hostile payload is touched. The observer fully
revalidates the request's exact retained state (method, sandbox origin, path
template, Accept value, scope, tax year and the tax-year-derived redacted path)
rather than trusting construction history.

Every returned HTTP 200 (`IndividualTaxAnnualSummaryObservation`) and documented
400/401/404 (`IndividualTaxErrorObservation`) retains the exact validated
request in a `request` field, and derives a public `tax_year` field equal to
`request.tax_year` during `__post_init__`. `tax_year` is a genuinely derived
non-init field: it cannot be supplied to the constructor or to
`dataclasses.replace` (both raise `TypeError`), and it is always recomputed from
the retained request. Each observation also retains a private `_request_binding`:
an independently reconstructed, UTR-free immutable snapshot of the producing
request intent, rather than an alias of the public `request` object. Construction
and full-state validation require the derived `tax_year`, retained `request` and
independent `_request_binding` to be mutually coherent, so neither a coordinated
`replace(observation, request=..., tax_year=...)` nor a direct rebuilder can
substitute a different request/year while retaining the original response facts.
The binding is UTR-free: it is the validated request intent, never the raw UTR.
Identical payloads observed under different request tax years remain
distinguishable by annual identity, while requests built from different UTRs
for the same year remain observationally indistinguishable and UTR-free.

## 3. Defensive/fail-closed policy

Validation failures raise `HMRCIndividualTaxContractError` with constant,
non-echoing messages. The raw response payload and the error `message` are never
retained. The error observation keeps only `status_code` and `code`; the
`message` is validated as a string (Reserved length bound only) and then
discarded.

### Unknown names and defensive key bounds

Bounded safe additive unknown names are accepted for forward compatibility, but
unknown values are never retained, traversed, copied, stringified, compared,
hashed, logged or otherwise inspected. Before classification at top-level,
employment-item, pensions/benefits, refunds and error-body levels the module
requires exact built-in string keys and applies the following clearly labelled
Reserved defensive bounds:

- maximum object members per JSON object: `64`;
- maximum additive unknown keys per object: `32`;
- maximum key-name length: `256` characters;
- maximum retained string-value length: `4096` characters;
- maximum employment items per response: `10_000`.

Keys are retained only when every character is outside Unicode general category
`C`. The rule `unicodedata.category(character).startswith("C")` rejects ASCII
and C1 controls (`Cc`), format/bidi/zero-width controls (`Cf`), surrogates
(`Cs`), private-use (`Co`) and unassigned/noncharacter code points (`Cn`) before
unknown-name retention. Ordinary international letters, combining marks, CJK,
emoji, spaces and Unicode separator whitespace remain accepted where otherwise
within bounds. Empty names, oversized names, mixed/non-string keys and excessive
objects fail closed before any value is dereferenced or iterated. Hostile
unknown values whose `repr`, `str`, `hash`, equality and iteration hooks all
raise are never inspected at any level. Container subclasses are rejected on
every documented field that is actually traversed; no global depth, node,
aggregate, alias or cycle traversal is promised or performed for ignored unknown
values, because decoded JSON cannot contain aliases/cycles and retained
immutable observations keep no source-container references.

### Reserved defensive numeric bounds (not endpoint facts)

The endpoint schema declares money only as `type: number` and states no
minimum, maximum, sign, scale, `multipleOf` or rounding rule. The following
finite bounds are Reserved defensive policy, labelled and boundary-tested, and
are not endpoint sign/precision/magnitude facts:

- maximum magnitude `10**18` for `int` and `Decimal`;
- maximum `12` fractional places for `Decimal`;
- maximum `38` significant digits (with the magnitude and scale bounds above it
  is not independently reachable).

## 4. Bounded inference

### Number boundary

The decoded JSON-number boundary accepts only exact built-in `int` and exact
`Decimal` values. `bool` (a subclass of `int`), `float`, `str`, every numeric
subclass (including `IntEnum`, `Fraction`, and `int`/`Decimal` subclasses),
`NaN` and infinities are rejected. Values must be finite.

The exact value is retained as `int | Decimal` without quantising, rounding,
sign change (including negative zero) or exponent change. `Decimal("-0.000")`
is retained with sign `1` and exponent `-3`. Upstream float parsing is outside
this offline package; a later transport must decode JSON floats with
`parse_float=Decimal`.

### Literal response and error rules

HTTP 200 requires exact `application/json` and an exact built-in `dict` payload
containing all three of `employments`,
`pensionsAnnuitiesAndOtherStateBenefits` and `refunds`. `employments` is an
exact built-in `list` of zero or more exact built-in `dict` items; each item
requires an exact built-in string `employerPayeReference` and a numeric
`taxTakenOffPay` on the number boundary. An empty `employments` list is
shape-valid but never evidence of zero tax deducted; completeness remains
exactly `UNVERIFIED`. No employer identity, date, currency, sign, precision,
ordering, uniqueness or join authority is inferred.

The pensions/benefits container is an exact built-in `dict` whose two documented
members (`otherPensionsAndRetirementAnnuities`, `incapacityBenefit`) are
optional numbers; omission is `None` and is never coerced to zero, while
explicit `null` is rejected. The `refunds` container is an exact built-in `dict`
whose single documented member `taxRefundedOrSetOff` is an optional number with
the same omission-versus-null rule. Optional presence is tracked explicitly in
`present_fields`/`absent_fields` frozensets; missing is not null and not zero.

For HTTP 400, 401 and 404 the module requires exact `application/json`, exact
built-in string `code` and `message`, and the documented immutable status/code
pairings:

- 400: `SA_UTR_INVALID` or `TAX_YEAR_INVALID`;
- 401: `UNAUTHORIZED`;
- 404: `NOT_FOUND`.

Only the exact documented `404` + `NOT_FOUND` pair is endpoint no-data. An
unknown, generic or differently coded 404 remains unclassified and fails
closed; it is never converted to no-data, zero, an empty summary or
completeness. Undocumented statuses, media types, codes, malformed bodies,
explicit nulls and mismatched status/code pairs fail closed.

### String values: no evidenced minLength

The documented schemas declare no `minLength`. Empty and
separator-whitespace-only `employerPayeReference` and error `message` values are
therefore accepted as schema-valid but semantically unverified. Only the
Reserved string-length bound is applied; no minimum length or non-whitespace
requirement is invented. Retained `employerPayeReference` strings additionally
apply Unicode category `C` rejection while preserving all other exact content
without trimming or normalising. The error `message` is validated with the
length bound only and then discarded, with no invented Unicode semantics.

### Deep immutability and forgery resistance

Every public observation class is a frozen dataclass whose `__post_init__`
revalidates the full package invariants, so direct construction and
`dataclasses.replace` cannot create an incoherent instance:

- `EmploymentItemObservation` revalidates the exact built-in bounded,
  Unicode-safe string `employer_paye_reference`, the exact built-in
  `int`/`Decimal` `tax_taken_off_pay`, and an exact bounded `frozenset` of safe
  unknown names;
- `PensionsBenefitsObservation` requires `present_fields` and `absent_fields`
  to be exact disjoint frozensets that are exhaustive over the two documented
  benefit names, and each optional numeric value to be non-`None` exactly when
  its provider field is present;
- `RefundsObservation` applies the same present/absent coherence to the single
  `taxRefundedOrSetOff` member;
- `IndividualTaxAnnualSummaryObservation` requires an exact tuple of exact
  `EmploymentItemObservation` items, an exact `PensionsBenefitsObservation`, an
  exact `RefundsObservation`, bounded safe unknown names, the exact
  `UNVERIFIED` completeness value, an exact validated
  `IndividualTaxRequestIntent`, and a derived `tax_year` and retained
  `_request_binding` both equal to that request;
- `IndividualTaxErrorObservation` requires an exact built-in integer status, an
  exact built-in string code on the documented status/code pairing, bounded
  safe unknown names, an exact validated `IndividualTaxRequestIntent`, and a
  derived `tax_year` and retained `_request_binding` both equal to that
  request.

The employment-item, pensions/benefits and refunds observations also require an
exact class and exact declared instance-key set whenever they are constructed,
copied, deep-copied or reduced. Missing or undeclared nested state therefore
fails closed directly and when reached through an annual-summary preservation
boundary; it is never silently retained or stripped during reconstruction.

Every public object additionally defines `__copy__` and `__deepcopy__` to
revalidate complete state (including nested request state and the independently
reconstructed UTR-free producing binding) before returning the same deeply
immutable instance,
and `__reduce__` to reconstruct through a module-level validated rebuild
boundary that carries and re-checks the binding. Copy, deepcopy and pickle
therefore preserve the frozen, coherent, exact-type objects and the bound
request/tax-year relationship for legitimate observations, while any altered,
missing, substituted or incoherent state (a forged nested request, a coordinated
year/request change, a deleted derived year or a missing/substituted binding)
raises `HMRCIndividualTaxContractError` instead of being rehabilitated. Mutable
lists, dicts and sets, subclasses, unbounded values, invalid completeness,
arbitrary status/code pairings, lookalike or subclass requests, and mutable
nested observation state are rejected at construction, on
`dataclasses.replace`, and on rebuild. Raw mappings and unknown values are never
retained.

### Explicitly kept out of scope

This package does not emit or imply `PayeEvidence`, canonical accounting
evidence, annual-tax inputs, cash-obligation inputs, customer presentation data,
provider completeness, production readiness or cross-endpoint matching
authority. Deducted amounts (`employments[].taxTakenOffPay` and the
pensions/benefits numbers) and `refunds.taxRefundedOrSetOff` remain separate
literals; no netting, sign interpretation, aggregation, total, credit, cash or
reserve position is derived. The State Pension lump-sum reference `267/LS500`
is a literal provider fact only; no special downstream tax or identity behaviour
is attached to it. Completeness remains `UNVERIFIED`.

## 5. Remaining gates (fail closed)

The following remain unresolved and are not implemented or authorized here:

- endpoint-specific rate limits, retry timing, idempotency and pagination;
- fraud-prevention-header applicability and the exact connection-method header
  set for this endpoint;
- Reserved application subscription and access approval;
- approved encrypted credential/key custody and token lifecycle;
- exact Individual PAYE Test Support 2.1 fixture contract and retained-evidence
  controls;
- HTTP client, OAuth, callback and route implementation;
- live and sandbox execution evidence;
- cross-endpoint identity resolution and ambiguity handling;
- provider-to-canonical mapping, decimal/sign/refund policy, persistence and
  source priority;
- privacy, security, operational monitoring, independent integration and launch
  assurance; and
- production activation and release authority.

This is a review-ready, uncommitted candidate limited to the exact three
tracked, modified paths listed in the change request. It does not claim
approval, independent assurance, integration, launch readiness or
production/contractual authority.
