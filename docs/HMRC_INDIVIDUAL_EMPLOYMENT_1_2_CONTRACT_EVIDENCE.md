# HMRC Individual Employment 1.2 literal contract — evidence

Observation date: **1 September 2026**. Status: **network-inert literal
contract implemented; disabled, non-sendable and not activation evidence**.

This record documents the tightly bounded, offline-only provider contract in
`reserved/providers/hmrc_individual_employment_contract.py` and its tests in
`tests/test_hmrc_individual_employment_contract.py`. It is the literal
request/response contract slice that
`HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md` described as the next
eligible engineering slice. It is **not** a transport adapter, a parser of the
full OpenAPI document, a sandbox fixture, or a step toward production.

## Authority and evidence boundary

The constants and validation rules below come from the already captured,
reviewed official facts in
`HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md` (resolved Individual
Employment 1.2 OpenAPI specification, observed 1 September 2026). No new HMRC
source was read for this package, no HMRC API was called, no application or
account was used, and no credential, test user, UTR, fixture or production data
was accessed.

This package makes no claim of completeness, approval, assurance, integration,
launch readiness, or contractual/production authority. It only makes the
documented read contract deterministically checkable in code.

## Exact documented contract surface

The module exposes only these documented constants:

- API name: `Individual Employment`, version `1.2`;
- sandbox-only origin: `https://test-api.service.hmrc.gov.uk` (production
  `https://api.service.hmrc.gov.uk` is intentionally absent);
- GET path template:
  `/individual-employment/sa/{utr}/annual-summary/{taxYear}`;
- request `Accept`: `application/vnd.hmrc.1.2+json`;
- user-restricted OAuth scope: `read:individual-employment`;
- documented response `Content-Type`: `application/json`;
- success status `200`;
- documented error statuses `{400, 401, 404}` with the exact endpoint codes:
  - `400` → `SA_UTR_INVALID`, `TAX_YEAR_INVALID`;
  - `401` → `UNAUTHORIZED`;
  - `404` → `NOT_FOUND`;
- required employment fields `{employerPayeReference, employerName}` and
  optional field `{offPayrollWorkFlag}`;
- completeness constant `UNVERIFIED`.

## Request intent is frozen, redacted and non-sendable

`build_individual_employment_request(*, utr, tax_year)` returns a frozen
`IndividualEmploymentRequestIntent`. The intent:

- is not, and cannot become, a `ProviderRequest`; it has no `method`, `url`,
  `headers`, `body`, authorisation header or redacted-summary surface;
- validates a 10-digit SA UTR (`^[0-9]{10}$`) and the documented tax-year form
  (`^[0-9]{4}-[0-9]{2}$`) before storing anything;
- discards the UTR after validation: no raw UTR, UTR-bearing path, name-mangled
  private attribute or recoverable equivalent is retained on the object;
- exposes only the non-sensitive, validated `tax_year`;
- is immutable: attribute assignment and deletion raise.

Error text for a malformed UTR or tax year is constant and never echoes the
supplied value.

## Fail-closed response validation

`observe_individual_employment_response(request, *, status_code, content_type,
payload)` returns either an `EmploymentHistoryObservation` (200) or an
`EmploymentErrorObservation` (400/401/404), and raises a controlled
`HMRCIndividualEmploymentContractError` for anything else.

Rules applied in order:

1. The request must be exactly an `IndividualEmploymentRequestIntent` (subclasses
   rejected).
2. `status_code` must be exactly a built-in `int` (bool and `int` subclasses
   rejected) and one of `{200, 400, 401, 404}`.
3. `content_type` must be exactly `application/json`.
4. A 200 payload must be a built-in `dict` (dict subclasses rejected), contain
   `employments`, where `employments` is a built-in `list` that is non-empty.
5. Every employment must be a built-in `dict` with exact built-in string
   `employerPayeReference` and `employerName` (str subclasses rejected). These
   fields are OpenAPI `type: string` with no evidenced `minLength`, so empty and
   separator-whitespace-only strings are schema-valid; they are retained as
   schema-valid but semantically unverified values and are not promoted into
   downstream evidence. Retained employer strings are additionally checked
   against the same Unicode general-category `C` predicate used for member
   names: control (including tab/newline), format, surrogate, private-use and
   unassigned characters are rejected, while ordinary letters, combining marks,
   numbers, punctuation, symbols, emoji and separator whitespace are preserved.
   `offPayrollWorkFlag`, when present, must be an exact built-in `bool`
   (bool-as-int `1`/`0`, bool subclasses, and every other non-bool rejected).
6. Absence of the optional `offPayrollWorkFlag` is valid and recorded in
   `absent_fields`; the field is `None` only when absent. The captured schema
   does not declare this field nullable, so explicit `null` is invalid and
   fails closed; exact built-in `true`/`false` are the only accepted present
   values. No coercion is applied.
7. An error payload must be a built-in `dict` with exact built-in string `code`
   and `message`. `message` is OpenAPI `type: string` with no evidenced
   `minLength`, so empty and whitespace-only strings are schema-valid but
   semantically unverified. `code` must match the frozen documented set for
   that status. The provider `message` is validated for structure but never
   retained or exposed because it may echo the submitted UTR/tax year; only the
   constant `error_code` is retained. Because `message` is never retained, it
   is intentionally not passed through the retained-string Unicode-safety
   predicate and keeps only its current exact-string and Reserved size checks.
8. Open-schema member names at every level (top-level, employment record and
   error body) are bounded and type-checked before known/unknown
   classification: keys must be exact built-in `str`, and any character in
   Unicode general category `C` — control, format, surrogate, private-use and
   unassigned — is rejected, as are unsafe/oversized names, excessive object
   member counts and excessive unknown-key counts. Bounded safe unknown names
   are accepted for forward compatibility and recorded in `unknown_fields`, but
   their values are never dereferenced, traversed, copied, stringified,
   compared, hashed or logged.

## Reserved defensive policy bounds (NOT HMRC wire facts)

HMRC's documented Individual Employment 1.2 schemas state no maximum for the
`employments` array, the employer identifier/name/message strings, the number
of object members, or the length/number of unknown member names. The following
local safety limits are Reserved defensive policy only; they are not provider
facts and must not be presented as such:

- `RESERVED_DEFENSIVE_MAX_EMPLOYMENTS = 1000`;
- `RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH = 512`;
- `RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH = 64`;
- `RESERVED_DEFENSIVE_MAX_ERROR_CODE_LENGTH = 64`;
- `RESERVED_DEFENSIVE_MAX_ERROR_MESSAGE_LENGTH = 1024`;
- `RESERVED_DEFENSIVE_MAX_OBJECT_MEMBERS = 1000`;
- `RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH = 256`;
- `RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS = 64`.

Each bound, and every member-name and retained employer-string type/length and
Unicode-category check, is applied before any documented field is dereferenced
or any member name is classified, so unbounded or hostile input is rejected
before it can be inspected. The single constant, non-echoing predicate uses
`unicodedata.category(character).startswith("C")`.

## Product boundary

- No `PayeEvidence`, canonical accounting evidence, annual tax inputs,
  cash-obligation inputs or customer-presentation data is created or emitted.
- `EmploymentHistoryObservation.completeness` is always `UNVERIFIED`. The
  annual-summary read is an observation, not proof of a complete current
  position.
- The raw response payload is not retained; observations keep only validated
  scalars and field-name sets.
- All observation objects are frozen and their `repr` is `[REDACTED]`.

## Prohibited surfaces

The module contains no HTTP client, token store, credential hook, authorisation
header, configurable production origin, routing, persistence, activation or
provider-call path. Downstream tax/cash/customer use, persistence, activation
and provider calls remain prohibited in code and documentation.

## Remaining gates (unchanged)

Nothing here resolves, or is evidence toward resolving, any of the gates in
`HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md`:

- endpoint-specific rate limits and retry timing;
- fraud-prevention-header applicability and connection-method header set;
- Reserved application subscription and access approval;
- Individual PAYE Test Support 2.1 fixture endpoint/payload/scenarios;
- approved encrypted credential custody and external key management;
- sandbox callback, test-user and retained-evidence controls;
- live or sandbox execution evidence;
- source-to-canonical field mapping, transport, persistence, routes and
  provider enablement;
- privacy, security, operations, independent integration and launch assurance.

`ProviderSpec("hmrc")` remains `implementation_enabled=False`.
