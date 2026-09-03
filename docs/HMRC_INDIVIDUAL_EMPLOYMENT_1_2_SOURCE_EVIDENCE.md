# HMRC Individual Employment 1.2 — transport-neutral source-evidence boundary

Observation date: **1 September 2026** (authority capture; this package adds no
new HMRC reading). Status: **network-inert source-evidence boundary
implemented; uncommitted, review-ready candidate only**.

This record documents the tightly bounded, offline-only builder/translator in
`reserved/providers/hmrc_individual_employment_source_evidence.py` and its
adversarial tests in `tests/test_hmrc_individual_employment_source_evidence.py`.
It consumes only an exact, already validated `EmploymentHistoryObservation`
from `reserved/providers/hmrc_individual_employment_contract` and emits a
deeply immutable, redacted, transport-neutral evidence bundle. It is **not** a
transport adapter, a parser of the full OpenAPI document, a sandbox fixture, a
credential store, a provider enabler, or a step toward production or customer
display.

This package makes no claim of provider authenticity beyond receipt of an exact
validated and internally request-bound observation. It makes no claim of provider completeness,
cross-endpoint reconciliation, customer fitness, launch readiness or production
authority.

## Authoritative local source facts

The only source of truth for the consumed observation is
`reserved/providers/hmrc_individual_employment_contract.py` (and its tests),
which itself derives from the reviewed official facts in
`docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md` and
`docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_CONTRACT_EVIDENCE.md`. This package does
not re-read HMRC, does not call HMRC, and does not read any credential, test
user, UTR, sandbox fixture or production data.

The bundle preserves, and only preserves:

- the source API name constant `Individual Employment`;
- the source API version constant `1.2`;
- the validated tax year from the observation;
- each source record's explicit provider `employerPayeReference`;
- each source record's explicit provider `employerName`;
- the off-payroll field's presence/absence and exact value (exact built-in
  `true`/`false` when present, `None` only when absent), together with the
  recorded `absent_fields` omission set;
- safe unknown member names already evidenced at each source layer
  (top-level `unknown_fields` and each record's `unknown_fields`), after
  independent exact validation;
- a caller-supplied opaque evidence/run reference;
- an aware UTC or fixed-offset observation timestamp;
- an optional lowercase 64-character SHA-256 digest of a separately redacted
  source artefact.

Completeness is always exactly `UNVERIFIED`. Source record order and duplicates
are preserved as evidence only: order has no semantic precedence, and matching
employer references or names do not establish identity or a join. The bundle
carries no employment identity, no join key, no deduplication and no precedence
semantics.

Empty or whitespace-only provider strings remain schema-valid only where the
exact source contract allows them (the captured schema has no evidenced
`minLength`). They are preserved exactly, without trimming, normalising or
inferring meaning, and their semantic completeness remains unverified.

## Reserved defensive policy

The source contract already validates the raw response against the documented
schema. This package does not trust that construction history: it re-validates
the entire nested observation before translating. The re-validation applies
exact built-in type checks to every container, scalar and nested object, and
re-checks:

- the source observation's exact type (subclasses and lookalikes rejected);
- the source contract's canonical producing-request binding, including its
  opaque per-request correlation token, tax year, fixed method, endpoint template, API
  name/version, Accept media and scope semantics;
- coherence among the reconstructed request, retained request binding,
  independent source-binding snapshot and binding-derived public tax year;
- the canonical observation-integrity digest over that complete binding and
  every retained semantic observation value, after exact shape/type validation;
- process-local observer/reconstructor issuance identity, so unsupported
  low-level clones and wholesale cross-request transplants are rejected even
  when success payloads or error status/code semantics are identical;
- the exact instance-state shape of the non-slotted source observation and
  every nested record (missing or additional attributes rejected by name
  before field translation, without reading an additional attribute's value);
- `tax_year` exact string and `^[0-9]{4}-[0-9]{2}$` form;
- `status_code` exact built-in `int` equal to the documented success status;
- `completeness` exactly `UNVERIFIED`;
- top-level `absent_fields` empty and top-level `unknown_fields` safe;
- the `employments` tuple exact type, non-empty and within the Reserved
  defensive bound;
- each employment's exact `EmploymentRecordObservation` type, employer-string
  exact type/length/Unicode-safety, off-payroll exact `bool`/`None`, and the
  field-presence/absence coherence (`off_payroll_work_flag is None` if and only
  if `offPayrollWorkFlag` is recorded absent);
- unknown-name safety, length and count bounds and disjointness from documented
  and absent field names.

The translator invokes the contract's full observation validator before it
reads any translatable field. Cross-UTR, cross-year, cross-method, cross-path,
cross-version/media/scope, malformed-binding, observation replacement and
coordinated request/binding substitution therefore fail closed. Hostile or
malformed source objects and metadata fail without invoking comparison, `repr`,
truthiness, hashing, iteration, mapping, attribute or string hooks beyond the
strictly unavoidable built-in operations. Exact built-in state is checked before
equality, so a hostile equality hook is not needed to reject a mismatch. Errors are constant
and non-echoing and never expose a UTR, raw/redacted path, raw payload, provider
message, employer value, evidence reference or digest input. No UTR, request
path, raw payload, provider message, HTTP content/body, secret, credential or
transport state is retained in object state, `repr`, errors or pickle.

The observation-integrity value is an internal, unkeyed deterministic content
digest for mutation/coherence detection. It is not authentication,
authorisation, a credential or an unforgeable seal, and does not claim to stop
trusted in-process code that replaces a complete object graph and recomputes
all public deterministic state. Its boundary is deterministic rejection of
inconsistent or partial state substitution before source translation.
The additional issuance check is process-local identity/coherence state. It
accepts observer-issued objects and validated pickle reconstructions and rejects
unsupported low-level object cloning or coordinated transplantation onto a
different issued instance. It is not durable provenance, authentication,
attestation or an unforgeable boundary against Python code with arbitrary
module-internal access; publicly reconstructible pickle state carries no such
claim.

The additional Reserved defensive bounds used here are local safety limits only,
not provider facts:

- `RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH = 256` (the caller-supplied
  opaque reference);
- the source contract's already labelled defensive bounds are re-applied
  (`RESERVED_DEFENSIVE_MAX_EMPLOYMENTS`,
  `RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH`,
  `RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH`,
  `RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH`,
  `RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS`).

The opaque evidence/run reference is validated as an exact built-in `str`
within the length bound and free of Unicode general-category `C` characters. It
is not interpreted as a path, URL, identifier or anything else. The observation
timestamp must be an exact aware built-in `datetime` carrying a fixed-offset
`datetime.timezone` (`datetime.timezone.utc` or an explicit fixed offset); it is
retained exactly as supplied, and no source chronology is invented. The optional
artifact digest must be an exact lowercase 64-character SHA-256 hex string;
omission is distinct from presence and an explicit `null` is rejected rather
than treated as omission. A private sentinel records omission internally and a
read-only public view reports the optional value as `None`; the sentinel is not
accepted or exposed as public product state. The digest constructor input is
not retained separately from that private presence-aware state.

Direct construction, builder use, `dataclasses.replace`, `copy.copy`,
`copy.deepcopy` and `pickle` cannot bypass the result or source invariants: the
bundle and record dataclasses re-validate in `__post_init__`; the bundle's
explicit constructor distinguishes omission from an explicit `None`; and
`__reduce_ex__` reconstructs through that validating constructor so
copy/deepcopy/pickle round-trips re-validate rather than trusting serialised
state. Omitted and present digest states survive those reconstruction paths;
`dataclasses.replace` preserves either state for unrelated replacements, while
an explicit `None` replacement fails.

## Bounded inference

The only inference recorded is architectural, from Reserved's evidence model,
and is not an HMRC-mandated fact: Individual Employment should precede
Individual Income and Individual Tax so that later income and tax-deduction
evidence can be associated without combining different employments or double
counting an aggregate. This package does not implement that association; it only
preserves the employment source evidence without any identity or join.

## Prohibited surfaces and product boundary

The module imports no `PayeEvidence`, no canonical accounting evidence, no
annual tax inputs, no cash-obligation inputs and no customer-presentation data.
It contains no HTTP client, token store, credential hook, authorisation header,
configurable production origin, routing, persistence, database, provider
initialiser, enablement or production configuration. Money, tax, tax-code,
annual-liability, cash-obligation, canonical accounting, customer, stable
employment identity/join, deduplication and precedence semantics are all out of
scope.

## Unresolved gates

Nothing here resolves, or is evidence toward resolving, any gate in
`docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_ENDPOINT_EVIDENCE.md` or
`docs/HMRC_INDIVIDUAL_EMPLOYMENT_1_2_CONTRACT_EVIDENCE.md`:

- endpoint-specific rate limits and retry timing;
- fraud-prevention-header applicability and connection-method header set;
- Reserved application subscription and access approval;
- Individual PAYE Test Support 2.1 fixture endpoint/payload/scenarios;
- approved encrypted credential custody and external key management;
- sandbox callback, test-user and retained-evidence controls;
- live or sandbox execution evidence;
- source-to-canonical field mapping, transport, persistence, routes and
  provider enablement;
- whether a separately redacted source artefact and its SHA-256 digest are
  approved for retention, and the exact redaction policy for any retained
  artefact;
- privacy, security, operations, independent integration and launch assurance.

`ProviderSpec("hmrc")` remains `implementation_enabled=False`.
