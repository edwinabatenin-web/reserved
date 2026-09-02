# HMRC PAYE Test Support 2.1 — Employment fixture literal contract evidence

Observation date: **2 September 2026**. Status: **implementation candidate ready
for independent review; not self-approved**. This document records the bounded,
disabled, offline and network-inert literal request/response contract for exactly
one sandbox operation: `createEmploymentHistoryTestData`.

Primary provider authority is
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md` at immutable base
`3e4bd3777a6aa5c3e0886c395b32ce0cf4d67f39`. This package does not re-verify or
re-author that capture; it encodes only the endpoint facts it establishes.

## 1. Scope and package boundary

- Package: `reserved-hmrc-paye-test-support-2.1-employment-contract`.
- Branch: `ohds/hmrc-paye-test-support-2.1-employment-contract`.
- Exact base: `3e4bd3777a6aa5c3e0886c395b32ce0cf4d67f39`.
- Authorised new files (exactly three):
  - `reserved/providers/hmrc_paye_test_support_employment_contract.py`;
  - `tests/test_hmrc_paye_test_support_employment_contract.py`;
  - `docs/HMRC_PAYE_TEST_SUPPORT_2_1_EMPLOYMENT_CONTRACT_EVIDENCE.md`.
- No existing file, registry, package initialiser, transport, fixture,
  configuration or Founder Decision is modified. No dependency is added. No I/O
  is authorised.

## 2. Exact documented operation facts

Only these endpoint facts are encoded. Nothing below is invented.

| Fact | Exact value |
|---|---|
| operation ID | `createEmploymentHistoryTestData` |
| method | `POST` |
| path template | `/individual-paye-test-support/sa/{utr}/employments/annual-summary/{taxYear}` |
| version | `2.1` |
| lifecycle | beta |
| environment | Sandbox-only |
| request `Accept` | `application/vnd.hmrc.2.1+json` |
| request `Content-Type` | `application/json` |
| authentication | application-restricted OAuth 2.0 Client Credentials Grant (documentation metadata only) |
| named OAuth scope | none — the specification's scope map and operation scope list are empty |
| request body | required; `application/json`; object schema does **not** mark `scenario` required |
| `scenario`, when present | exactly `HAPPY_PATH_1` or `HAPPY_PATH_2` |
| success status | HTTP 201 with `application/json` |
| endpoint-specific errors | none documented (no error responses, no error codes) |

The authentication fact is recorded as a constant string only. It is not a
credential, token, authorisation header or sendable header map. The constant
`HMRC_PAYE_TEST_SUPPORT_EMPLOYMENT_OAUTH_SCOPES` is an empty `frozenset`.

## 3. Scenario omission versus presence

The request body schema marks the request body required but does **not** mark its
`scenario` property required. The construction boundary therefore distinguishes:

- **omission** — `scenario` not supplied; the intent records
  `scenario is None` and `scenario_present is False`;
- **presence** — `scenario` supplied; the intent records the exact literal and
  `scenario_present is True`.

An explicit `scenario=None` is rejected (fail closed), not silently converted
into omission. Present values accept only the two documented literals
`HAPPY_PATH_1` / `HAPPY_PATH_2`.

## 4. Request-intent boundary

The public `build_employment_test_support_request(*, utr, tax_year, scenario=…)`
boundary:

- accepts only an exact built-in ASCII `str` of exactly ten digits for `utr`
  (pattern `[0-9]{10}` fullmatch);
- accepts only an exact built-in `str` matching `^[0-9]{4}-[0-9]{2}$` for
  `tax_year`;
- permits scenario omission distinctly from presence;
- accepts, when present, only an exact built-in `str` equal to one of the two
  documented scenario literals;
- rejects subclasses, custom objects, whitespace, Unicode digit lookalikes,
  signs, delimiters, `None` and other malformed inputs;
- validates `utr` before deriving retained state, then discards it completely.

The resulting `EmploymentTestSupportRequestIntent`:

- retains only the validated tax year and the explicit scenario-presence/value
  facts;
- retains no raw, reversible, recoverable or surrogate UTR;
- exposes no rendered path/URL, no method+origin combination, no
  `Authorization` header, no access token, no credential, no sendable header map
  and no sendable body;
- is frozen (attribute assignment/deletion raise), redacted
  (`repr` is `EmploymentTestSupportRequestIntent([REDACTED])`), and has no
  mutable `__dict__`;
- resists direct construction, mutation, `copy`, `deepcopy`, `pickle` and
  derived-field injection (copy/deepcopy/pickle raise `TypeError`);
- is not, and cannot become, a `ProviderRequest`.

Method/path/header values are recorded as module-level constants only; the
public object never assembles them into a sendable request.

## 5. HTTP 201 response observation

`observe_employment_test_support_response` accepts only an exact built-in
top-level `dict` with required `employments`:

- `employments` must be an exact built-in `list`;
- each element must be an exact built-in `dict`;
- each item requires exact built-in `str` `employerName` and
  `employerPayeReference`;
- optional `offPayrollWorkFlag`, when present, must be an exact built-in `bool`;
- explicit `null` fails closed because the schema declares no nullable field;
- omission of `offPayrollWorkFlag` is preserved distinctly from `false`
  (`off_payroll_work_flag is None` iff the field is absent);
- the provider schema is open (`additionalProperties: false` is not declared),
  so unknown member names are tolerated within Reserved bounds;
- array order has no documented semantic meaning.

The result is an `EmploymentTestSupportResponseObservation` (and per-element
`EmploymentTestSupportRecordObservation`), both frozen and redacted. The raw
payload is never retained.

### Constructor and `replace` exact-coherence invariants

Both observation classes re-run their full parser invariants in `__post_init__`,
so direct construction and `dataclasses.replace` (as well as copy/deepcopy and
pickle round-trips of already-coherent instances) cannot diverge from the
parse-time state; every invalid or contradictory state fails closed.

`EmploymentTestSupportRecordObservation` enforces:

- `employer_name` and `employer_paye_reference` are revalidated with the same
  exact built-in `str`, Reserved maximum-length and Unicode general-category-`C`
  rules used by parsing (unsafe and overlong values are rejected, not merely
  type-checked);
- `off_payroll_work_flag`, when present, is an exact built-in `bool`;
- `absent_fields` and `unknown_fields` are exact built-in `frozenset` values
  containing only exact safe bounded built-in `str` names (no mutable
  containers, wrong types, non-strings, unsafe or overlong names, and no more
  than the Reserved unknown-key bound);
- required documented names (`employerName`, `employerPayeReference`) may never
  be absent;
- `absent_fields` is exactly `{offPayrollWorkFlag}` if and only if
  `off_payroll_work_flag is None`, otherwise exactly empty;
- unknown names are disjoint from all documented employment names.

`EmploymentTestSupportResponseObservation` enforces:

- `tax_year` is the exact validated `YYYY-YY` form;
- `status_code` is an exact built-in `int` equal to 201;
- `employments` is an exact built-in `tuple` with no more than
  `RESERVED_DEFENSIVE_MAX_EMPLOYMENTS`, containing only exact coherent record
  observations (subclasses and non-record values fail closed);
- `completeness` is exactly `UNVERIFIED`;
- top-level `absent_fields` is exactly empty (because `employments` is required);
- top-level `unknown_fields` is exact, safe, bounded and disjoint from
  `employments`.

### Prose "one or more" versus schema constraint

Provider prose describes `employments` as "one or more" employments, but the
captured schema supplies no `minItems`. This package does **not** strengthen the
prose into a schema rule. An empty `employments` array is therefore accepted as
shape-valid but recorded with `COMPLETENESS_UNVERIFIED`; it is semantically
unverified. No non-empty guarantee is fabricated.

## 6. Non-201 fail-closed boundary

The operation documents only HTTP 201. Every non-201 result fails closed as an
unclassified outcome:

- the status is validated as an exact built-in `int` first, and any non-201
  status raises `HMRCPayeTestSupportEmploymentContractError`;
- for a non-201, the body is never parsed, echoed, retained or classified;
- no HMRC error code is fabricated and no failure is converted into success,
  no-data, zero or fixture completeness.

## 7. Reserved defensive bounds (local policy, not HMRC facts)

HMRC's captured schemas state no maximum for array length, retained string
length, object member count or unknown member-name length/count. The following
bounds are local safety limits, clearly labelled `RESERVED_DEFENSIVE_*`, and must
not be presented as provider facts:

| Bound | Value |
|---|---|
| `RESERVED_DEFENSIVE_MAX_EMPLOYMENTS` | 1000 |
| `RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH` | 512 |
| `RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH` | 64 |
| `RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS` | 1000 |
| `RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH` | 256 |
| `RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS` | 64 |

Defensive rules applied to every traversed container/string/member name:

- exact built-in `dict`/`list`/`str`/`bool`/`int` types are required on
  documented fields;
- retained member names containing Unicode general-category `C` characters are
  rejected (control, format, surrogate, private-use, unassigned);
- unknown-key counts and member-name lengths are bounded;
- only safe bounded unknown member names are retained; unknown values are never
  dereferenced, iterated, stringified, represented, hashed, compared, logged,
  copied or otherwise inspected;
- hostile unknown values whose `repr`, `str`, `hash`, equality and iteration
  hooks raise are handled without inspection at top level and employment-item
  level;
- container subclasses and hostile values on documented fields are rejected;
- no raw payload or mutable source-container reference is retained.

Because no provider `minLength` is documented, empty/whitespace-only documented
strings may be shape-valid but semantically unverified. Only bounded length and
unsafe-category rejection are applied as Reserved policy; string content is
otherwise preserved without trim/normalisation.

## 8. Static isolation

The module has no import or reference to HTTP/network/process facilities,
including `requests`, `httpx`, `urllib`, `socket`, `http.client`, `aiohttp`,
`subprocess`, the generic provider HTTP boundary (`reserved.providers.http_boundary`),
environment/configuration reads, persistence, routes, provider activation,
production HMRC origin, OAuth/token machinery or credential handling. Its only
imports are `re`, `unicodedata`, `dataclasses` and `typing`. The test suite
asserts this via in-memory AST import inspection and module-attribute checks.

## 9. No canonical / accounting / tax / cash / customer use

The observation is fixture evidence only. It does not create `PayeEvidence`,
canonical accounting evidence, annual tax input, cash-obligation input,
customer-presentation data, employment identity linkage, or proof that a
subsequent read is complete/current. Completeness is always `UNVERIFIED`.

## 10. Residual gates (not resolved here)

The following remain unresolved and fail closed. This package does not self-approve
any of them and claims no independent assurance, integration, provider enablement,
launch readiness or production authority:

- Reserved application subscription and HMRC access approval;
- encrypted client-credential custody and token lifecycle;
- exact visibility timing after a create;
- re-POST replacement/reset/clear-down semantics (no reset/delete operation is
  documented);
- endpoint-specific rate-limit/retry and fraud-prevention-header applicability;
- cross-API identity resolution and double-counting policy;
- live or sandbox execution evidence;
- privacy/security, transport and mapping of fixture data into downstream
  evidence.

## 11. Verification performed

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider …` across the
  five named test modules (including this package's suite);
- in-memory AST/`compile()` syntax and forbidden-surface checks without
  generating cache files;
- `git diff --check`, including all untracked files;
- exact branch/base and exactly three authorised untracked paths confirmed;
- no `__pycache__`, `.pytest_cache` or other generated path remains;
- SHA-256 reported for all three candidate files.
