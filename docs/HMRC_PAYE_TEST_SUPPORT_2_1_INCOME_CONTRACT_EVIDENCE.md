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

The request intent `CreateAnnualIncomeSummaryRequestIntent` is a frozen
dataclass that is not, does not inherit from, and does not convert by default
into the sendable `ProviderRequest`. It owns no HTTP client, transport,
credential, token, authorization header, persistence, routing, provider mapping,
production origin or activation path, and it exposes no rendered URL/path.

## Request validation, UTR discard and scenario presence

`CreateAnnualIncomeSummaryRequestIntent` retains exactly three fields:
`tax_year`, `scenario` and `scenario_present`. The UTR is validated as exactly
ten ASCII digits using `[0-9]{10}` and discarded immediately. The character
class is ASCII-only, so `str.isdigit()`/`isdecimal()`/`isnumeric()` semantics
are never used and full-width or Arabic-Indic Unicode digits are rejected. The
tax year is validated against the captured regex `^[0-9]{4}-[0-9]{2}$`. No UTR
surrogate, rendered URL/path, credential, Authorization header, token, header
map or body is retained in ordinary, private, name-mangled, serialized, copied,
equality/hash, representation or conversion state. Two requests built from
different UTRs with the same tax year and scenario compare equal and leave
identical retained state.

Scenario omission is distinguished from presence. The retained `scenario` is
`None` with `scenario_present=False` when the scenario is absent, and one of the
two literal built-in strings with `scenario_present=True` when present.
`build_create_annual_income_summary_request` uses a private sentinel default so
that omitting `scenario` records absence while an explicit `None` (JSON null)
fails closed. The frozen dataclass uses the same private sentinel default at the
direct-construction boundary, so omission is available only through the genuine
sentinel/default path and an explicit `None` fails closed there too.
`dataclasses.replace` re-enters the same validated boundary and cannot create a
contradictory `scenario`/`scenario_present` state. A present scenario is accepted
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

## Deep immutability of observations

Every public observation class is a frozen dataclass whose `__post_init__`
revalidates the full package invariants, so direct construction and
`dataclasses.replace` cannot create an incoherent instance:

- `AnnualIncomeEmploymentObservation` revalidates the exact built-in bounded
  category-C-free string `employer_paye_reference`, the exact built-in
  `int`/`Decimal` `pay_from_employment`, and an exact bounded `frozenset` of
  safe unknown names disjoint from `_EMPLOYMENT_NAMES`;
- `AnnualIncomePensionsBenefitsObservation` requires `present_fields` and
  `absent_fields` to be exact disjoint frozensets that are exhaustive over the
  four documented benefit names, each optional numeric value to be non-`None`
  exactly when its provider field is present, and bounded safe unknown names
  disjoint from `_BENEFITS_NAMES`;
- `AnnualIncomeSummaryTestDataObservation` requires an exact tuple of exact
  employment observations, an exact `AnnualIncomePensionsBenefitsObservation`,
  bounded safe unknown names disjoint from `_TOP_LEVEL_NAMES`, and the exact
  `UNVERIFIED` completeness value.

Mutable lists, dicts and sets, subclasses, unbounded values, invalid
completeness and mutable nested observation state are rejected at construction
and on `dataclasses.replace`. Copy, deepcopy and pickle round-trips preserve
the frozen, coherent objects; raw mappings and unknown values are never
retained.

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

This is a review-ready, uncommitted candidate limited to exactly the three new
paths listed below. It does not claim approval, independent assurance,
integration, enablement, launch readiness or production/contractual authority.
