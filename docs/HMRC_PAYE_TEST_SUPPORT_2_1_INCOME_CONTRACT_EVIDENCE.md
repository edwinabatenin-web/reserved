# HMRC Individual PAYE Test Support 2.1 — annual income fixture literal contract evidence

Observation date: **2 September 2026**. Status: **network-inert literal
request/response contract implemented; sandbox use, integration and activation
remain gated**.

This document records the implementation decisions for
`reserved/providers/hmrc_paye_test_support_income_contract.py` and its tests. It
is a companion to `docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`, which
is the only endpoint-specific authority used here. No HMRC API was called and no
credential, test user, UTR, sandbox fixture or production data was accessed.

## Authority boundary

This package treats the reviewed endpoint evidence as authority only for the
facts it states about one documented create operation. It does not transfer
authority from any other lane and does not invent endpoint fields, errors,
scopes, retry/idempotency, retention, ordering or completeness semantics.

- operation ID `createAnnualIncomeSummaryTestData`;
- `POST /individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}`;
- API 2.1 beta, Sandbox-only;
- required `Accept: application/vnd.hmrc.2.1+json` and
  `Content-Type: application/json`;
- application-restricted OAuth 2.0 Client Credentials with an empty scope map,
  so no named OAuth scope is recorded or invented;
- a required JSON object body whose `scenario` member is itself not
  schema-required; when present it is exactly `HAPPY_PATH_1` or `HAPPY_PATH_2`;
- exactly one documented response: HTTP 201 `application/json`.

## Implemented contract surface

The module exposes a minimal, network-inert surface:

- exact constants: operation ID, API identifier `individual-paye-test-support`,
  version `2.1`, HTTP method `POST`, sandbox origin
  `https://test-api.service.hmrc.gov.uk`, path template
  `/individual-paye-test-support/sa/{utr}/income/annual-summary/{taxYear}`,
  Accept header `application/vnd.hmrc.2.1+json`, JSON content type
  `application/json`, success status `201`, the OAuth Client Credentials grant
  type and the empty scope frozenset, and the two scenario literals;
- `build_create_annual_income_summary_request(*, utr, tax_year, scenario=...)`;
- `observe_create_annual_income_summary_response(request, *, status_code,
  content_type, payload)`.

The request intent `CreateAnnualIncomeSummaryRequestIntent` is an immutable,
slot-backed value that is not, does not inherit from, and does not convert by default
into the sendable `ProviderRequest`. It owns no HTTP client, transport,
credential, token, authorization header, persistence, routing, provider mapping,
production origin or activation path, and it exposes no rendered URL/path.

## Request validation, UTR discard and scenario presence

`CreateAnnualIncomeSummaryRequestIntent` retains one private canonical binding.
It contains a fresh 256-bit opaque correlation identity for each construction,
the exact tax year, exact scenario omission/presence/value, and the fixed
operation, method, sandbox origin, path-template, API, version, media, grant and
empty-scope facts above. The identity is random and is not derived from the
UTR. Read-only properties expose tax year and scenario state. The UTR is validated as exactly
ten ASCII digits using `[0-9]{10}` and discarded immediately. The character
class is ASCII-only, so `str.isdigit()`/`isdecimal()`/`isnumeric()` semantics
are never used and full-width or Arabic-Indic Unicode digits are rejected. The
tax year is validated against the captured regex `^[0-9]{4}-[0-9]{2}$`. No UTR
surrogate, rendered URL/path, credential, Authorization header, token, header
map or body is retained in ordinary, private, name-mangled, serialized, copied,
equality/hash, representation or conversion state. Independently constructed
requests remain distinct even when their semantic request fields and returned
sandbox fixture payloads are identical.

Scenario omission is distinguished from presence. The retained `scenario` is
`None` with `scenario_present=False` when the scenario is absent, and one of the
two literal built-in strings with `scenario_present=True` when present.
`build_create_annual_income_summary_request` uses a private sentinel default so
that omitting `scenario` records absence while an explicit `None` (JSON null)
fails closed. The frozen dataclass uses the same private sentinel default at the
direct-construction boundary, so omission is available only through the genuine
sentinel/default path and an explicit `None` fails closed there too.
`dataclasses.replace` is not a construction boundary for this non-dataclass
identity type. A present scenario is accepted
only as the exact built-in `str` `HAPPY_PATH_1` or `HAPPY_PATH_2`; subclasses,
custom objects, bytes, booleans, integers, whitespace, Unicode lookalikes, empty
strings, wrong case and undocumented identifiers are rejected. No other scenario
or fixture variant is accepted.

## Literal 201 response rules

HTTP 201 requires exact `application/json` and an exact built-in `dict` payload
containing both `employments` and `pensionsAnnuitiesAndOtherStateBenefits`.

- `employments`: an exact built-in `list` of zero or more exact built-in `dict`
  items; each item requires an exact built-in string `employerPayeReference` and
  an exact JSON numeric `payFromEmployment`. Array order has no semantic
  meaning; no pagination, uniqueness, identity, join or chronology authority is
  inferred.
- `pensionsAnnuitiesAndOtherStateBenefits`: an exact built-in `dict` whose four
  documented members (`otherPensionsAndRetirementAnnuities`,
  `incapacityBenefit`, `jobseekersAllowance`, `seissNetPaid`) are all optional
  numbers; none is required. Omission is `None` and is never coerced to zero;
  explicit JSON `null` fails closed.

An empty `employments` list and an empty benefits container are preserved as
shape-valid but completeness-unverified (`UNVERIFIED`). Neither proves no
income or completeness.

## Number boundary

The decoded JSON-number boundary accepts only exact built-in `int` and exact
`Decimal` values. `bool` (a subclass of `int`), `float`, `str`, every numeric
subclass (including `IntEnum`, `Fraction`, and `int`/`Decimal` subclasses),
`NaN` and infinities are rejected. Values must be finite.

The exact value is retained as `int | Decimal` without quantising, rounding,
sign change (including negative zero) or exponent change. `Decimal("-0.000")`
is retained with sign `1` and exponent `-3`. Upstream float parsing is outside
this offline package; a later transport must decode JSON floats with
`parse_float=Decimal`. Sign, precision, adjustment/refund and source-priority
semantics remain unresolved and are never interpreted, totalled, netted,
converted to annual tax, cash obligation or customer output.

### Reserved defensive numeric bounds (not endpoint facts)

The endpoint schema declares the numerics only as `type: number` and states no
minimum, maximum, sign, scale, `multipleOf` or rounding rule. The following
finite bounds are Reserved defensive policy, labelled and boundary-tested, and
are not endpoint sign/precision/magnitude facts:

- maximum magnitude `10**18` for `int` and `Decimal`;
- maximum `12` fractional places for `Decimal`;
- maximum `38` significant digits.

## Open schema, nullability and unknown names

The response schema is open (no `additionalProperties: false`) and non-nullable
(no field declared `nullable`). Omitted optional members are distinct from
explicit null; the latter fails closed and is never coerced.

Bounded safe additive unknown member names are accepted for forward
compatibility, but unknown values are never retained, traversed, copied,
stringified, compared, hashed, logged or otherwise inspected. Before
classification at top-level, employment-item and benefits levels the module
requires exact built-in string keys and applies these clearly labelled Reserved
defensive bounds:

- maximum object members per JSON object: `64`;
- maximum additive unknown keys per object: `32`;
- maximum key-name length: `256` characters;
- maximum retained string-value length: `4096` characters;
- maximum employment items per response: `10_000`.

Keys are retained only when every character is outside Unicode general category
`C` (`unicodedata.category(character).startswith("C")`), rejecting ASCII and C1
controls (`Cc`), format/bidi/zero-width controls (`Cf`), surrogates (`Cs`),
private-use (`Co`) and unassigned/noncharacter code points (`Cn`) before
unknown-name retention at every level. Ordinary international letters,
combining marks, CJK, emoji, spaces and Unicode separator whitespace remain
accepted where otherwise within bounds. Empty names, oversized names,
mixed/non-string keys and excessive objects fail closed before any value is
dereferenced or iterated.

Unknown-name sets retained by the public observation constructors are also
required to be disjoint from each object's documented member names: employment
observations must not contain `employerPayeReference` or `payFromEmployment`,
benefits observations must not contain any of the four documented benefit
names, and the top-level observation must not contain `employments` or
`pensionsAnnuitiesAndOtherStateBenefits`.

The documented schemas declare no `minLength`, so empty and ordinary-space-only
`employerPayeReference` strings are accepted as schema-valid but semantically
unverified; no minimum length or non-whitespace requirement is invented.
Retained `employerPayeReference` values must be exact built-in bounded strings
whose every character is outside Unicode general category `C` (`Cc` control,
`Cf` format/bidi/zero-width, `Cs` surrogate, `Co` private-use and `Cn`
unassigned/noncharacter). Unsafe category-C characters (for example U+200B
zero-width space) are rejected without trimming or normalising valid strings.

## Producing-request binding and process-local integrity

Only `observe_create_annual_income_summary_response` creates a supported
successful observation. It validates the exact request and canonical binding,
parses the exact 201 response, then retains the request, request binding, source
binding, tax year, scenario presence/value, status and all semantic response
state. A deterministic SHA-256 coherence digest covers that complete binding,
employment ordering and every employment value and unknown name, every benefit
value and exact presence/absence set, benefit and top-level unknown names, and
`UNVERIFIED` completeness. Decimal sign, coefficient digits and exponent are
encoded separately.

`validate_annual_income_summary_observation` is the public read-only validator.
It checks exact type and exact built-in `__dict__` keys before retained values;
revalidates every nested type, value, name and presence/absence invariant;
requires request, retained binding and source binding equality; recomputes the
digest; and requires a matching process-local issuance record for that exact
object. Coordinated wholesale replacement with another valid observation's
request, source, tax year, scenario and integrity therefore fails because the
object's issuance record remains bound to its original request instance.

This is process-local coherence and mutation/substitution detection only. It is
not provider authenticity, durable provenance, authorization, attestation or
replay prevention. Python module privacy is not a security boundary; code with
arbitrary module-internal access is trusted. A validated pickle contains only
the UTR-free canonical identity and semantic state. Unpickling revalidates its
arguments, reconstructs a request/observation, and registers the new object in
the receiving process. A valid pickle can therefore replay an earlier accepted
observation, including across processes, and is not freshness or replay
protection. Untrusted pickle bytes must never be loaded.

No error observation is invented: all non-201 responses still fail before an
observation exists, so request relabelling cannot convert them into negative,
zero-income or successful evidence.

## Deep immutability of observations

The nested semantic value classes are frozen dataclasses whose `__post_init__`
revalidates local invariants. The aggregate observation is a frozen exact-state
dataclass with `init=False`; direct construction and `dataclasses.replace` fail
closed, and only the validated observer/reconstructor issues supported values:

- `AnnualIncomeEmploymentObservation` revalidates the exact built-in bounded
  category-C-free string `employer_paye_reference`, the exact built-in
  `int`/`Decimal` `pay_from_employment`, and an exact bounded `frozenset` of
  safe unknown names disjoint from `_EMPLOYMENT_NAMES`;
- `AnnualIncomePensionsBenefitsObservation` requires `present_fields` and
  `absent_fields` to be exact disjoint frozensets that are exhaustive over the
  four documented benefit names, each optional numeric value to be non-`None`
  exactly when its provider field is present, and bounded safe unknown names
  disjoint from `_BENEFITS_NAMES`;
- the aggregate validator requires an exact tuple of exact
  employment observations, an exact `AnnualIncomePensionsBenefitsObservation`,
  bounded safe unknown names disjoint from `_TOP_LEVEL_NAMES`, and the exact
  `UNVERIFIED` completeness value.

Mutable lists, dicts and sets, subclasses, missing/extra/shadow state, unbounded
values, invalid completeness and low-level mutation fail validation. Request,
nested observation and aggregate equality, hash, repr, properties, copy,
deepcopy and pickle enter exact-state validation without first dispatching to attacker-controlled
instance equality, hash, repr, string, boolean, iteration or subtraction hooks.
Copy/deepcopy return each validated immutable object. Nested pickle round-trips
revalidate exact semantic state; aggregate pickle reconstruction structurally
preflights every field before canonical comparison, set operations, sorting,
digesting or construction, then revalidates semantics and registers a new
coherent aggregate. Raw mappings and unknown values are never retained.

## Non-201 fail-close and isolation

Every non-201 status fails closed as unclassified. Its arbitrary body is never
parsed, echoed, retained, classified or turned into a no-data/zero/success
record. No per-operation error responses are documented for this operation, so
no endpoint-specific error code or body shape is invented.

The module imports no HTTP, network, process, generic provider HTTP boundary,
environment/config, persistence, route, provider-activation, production-origin,
OAuth-token/credential or customer/canonical/tax/cash surface. Static tests
confirm the absence of those imports and of the production origin string,
`PayeEvidence`, `urlopen` and `http.client` in the module source. No dependency
or I/O is authorised.

## Non-interpretation and no downstream evidence

This package does not emit or imply `PayeEvidence`, canonical accounting
evidence, annual-tax inputs, cash-obligation inputs, customer presentation
data, provider completeness, production readiness or cross-endpoint matching
authority. The literal string `employerPayeReference` is not treated as a
unique, immutable or sufficient cross-endpoint join key. Completeness remains
`UNVERIFIED`.

## Remaining gates (fail closed)

The following remain unresolved and are not implemented or authorized here:

- Reserved application subscription and access approval;
- approved encrypted client-credential custody and token lifecycle;
- exact visibility timing after a create, and re-POST replacement behaviour;
- any clear-down/reset/deletion semantics (none are documented);
- endpoint-specific rate-limit/retry and fraud-header requirements;
- the stateful sandbox create/read companion model and its identity linkage
  beyond the literal UTR/NINO-plus-tax-year keys;
- cross-API identity resolution and double-counting policy;
- provider-to-canonical mapping, decimal/sign policy, persistence and source
  priority;
- privacy, security, operational monitoring, independent integration and launch
  assurance; and
- production activation and release authority.

This is a review-ready, uncommitted candidate limited to exactly the three
modified paths specified for this hardening. It does not claim approval, independent assurance,
integration, enablement, launch readiness or production/contractual authority.
