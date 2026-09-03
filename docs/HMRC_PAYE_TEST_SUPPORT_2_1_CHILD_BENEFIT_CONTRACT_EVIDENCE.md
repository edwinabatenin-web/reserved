# HMRC PAYE Test Support 2.1 Child Benefit contract evidence

Status: **corrected candidate awaiting independent re-review**.
Date: **3 September 2026**.

## Implemented boundary

This dependency-free, network-inert value contract covers the documented HTTP
201 result of `createChildBenefitEntitlementTestData`. Provider facts remain
grounded in `HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`.

Each request receives a fresh 256-bit process-generated opaque correlation
identity after its ten-ASCII-digit UTR is validated and discarded. The
canonical UTR-free binding contains the exact tax year; scenario
omission/presence/value; operation ID; POST method; sandbox origin; path
template; API version; Accept and JSON media types; client-credentials grant;
and empty-scope fact. Even requests with identical semantic inputs—and requests
whose discarded UTRs differ—therefore have distinct identities.

HTTP observations are observer-constructed only. The observer first fully
revalidates the exact request object, then checks exact built-in status 201
before content type or payload. It retains the exact request and matching
request/source bindings, request facts, HTTP status and content type,
`expectedStatus`, `expectedJson` omission/presence and parsed object,
entitlement numeric type/value/Decimal sign and scale, bounded unknown names at
both object layers, and `UNVERIFIED` completeness. Unknown values are neither
inspected nor retained. Existing literal-status, response-ordering, open-schema
and local defensive-bound semantics remain unchanged; no scenario-to-response
or HICBC/product interpretation is added.

The public `validate_child_benefit_create_response_observation` function checks
exact type and exact low-level state before reading retained fields. Raw state
shape and key types are validated without hashing, equality or iteration over
hostile keys. It then revalidates request/source coherence, all field
invariants, a canonical SHA-256 integrity digest over every retained semantic
value, and a process-local weak issuance record. Equality, hashing,
representation, copying and serialization all enter this validation boundary.
Every public field read re-enters the same boundary, so forged low-level state
is not returned to callers. Direct construction, dataclass replacement,
subclasses, malformed state and unsupported low-level clones fail closed. The
public validator captures the same private `state` collaborator in the
response-observation closure at construction time, so rebinding the
module-global `_state` cannot replace it.

The exported `ChildBenefitExpectedJsonObservation` carries its own canonical
SHA-256 integrity digest and process-local weak issuance record, matching the
enclosing response. Its identity, validation and reconstruction collaborators
are captured in private closure state at construction time, so rebinding the
module-global `_json_identity` (or `_json_state`, `_digest`, `_amount`,
`_names`, `_exact`, `_number`, `_new_json` or `_restore_json`) cannot replace
them. The digest closure likewise captures the genuine `hashlib.sha256` and
`json.dumps` callables (not the `hashlib`/`json` modules), so rebinding
`hashlib`, `json`, `hashlib.sha256` or `json.dumps` cannot substitute a forged
digest or serialization anywhere in the nested validation, equality, hash,
repr, copy, deepcopy, reduce or reconstruction path. Every read, equality in
both operand directions, hash, repr, copy and
deepcopy revalidates raw state shape and key types without hashing, then
recomputes the digest and compares it against the registered issuance. Direct
low-level mutation between two otherwise-valid states (entitlement value,
unknown-name presence or name, or whole-state transplantation) therefore fails
closed before any value is returned. Pickle `__reduce__` revalidates through the
same closure and carries the source's issued integrity; reconstruction then
revalidates that the supplied values match the exact originally issued semantic
identity and refuses to register altered values as a new issuance. Standard
shallow/deep copy validates and returns the same immutable object. These
mechanisms preserve coherence but do not make untrusted pickle data safe.

The exported `ChildBenefitCreateResponseObservation` enforces the same
discipline through its own closure. Its identity, validation and reconstruction
collaborators are captured in private closure state at construction time
(`_exact`, `_integer`, `_names`, `_request_binding`, `_valid_binding`,
`_restore_request`, `_new_observation` and `_restore_observation`), so rebinding
any of those module-global helper names cannot replace them. The request helpers
`_request_binding` and `_restore_request` also capture the genuine
`_valid_binding` collaborator directly, so validating and reconstructing a raw
request binding runs through that bound capability rather than a rebindable
module global. The nested
`ChildBenefitExpectedJsonObservation` collaborators are passed in as the nested
closure's own captured `_json_state`, `_json_canonical` and `_json_identity`
rather than re-read from the module. The digest closure captures the genuine
`hashlib.sha256` and `json.dumps` callables (not the `hashlib`/`json` modules),
so rebinding `hashlib`, `json`, `hashlib.sha256` or `json.dumps` cannot
substitute a forged digest or serialization anywhere in the outer validation,
equality, hash, repr, copy, deepcopy, reduce or reconstruction path. Every
public read, equality in both operand directions, hash, repr, copy and deepcopy
revalidates raw state shape and key types without hashing, then recomputes the
digest and compares it against the registered issuance. Direct low-level
mutation of `expected_status` or any retained outer field between two
otherwise-valid states therefore fails closed before any value is returned.
Pickle `__reduce__` revalidates through the same closure and carries the
source's issued `_observation_integrity`; reconstruction then revalidates that
the supplied binding, status, payload/presence and unknown names match that
exact originally issued outer semantic identity before registration, refusing
altered values as a new issuance.

## Security and provenance limits

The correlation identity is unrelated to, and not derived from, the discarded
UTR. No raw UTR, UTR hash, encoding, path or other deterministic/enumerable UTR
identity is retained. Error messages are constant and do not echo input.

The token, digest and issuance registry provide process-local detection of
mutation, context relabelling and substitution through supported public use.
They are **not** provider authenticity, durable provenance, authorisation,
attestation, replay prevention or a cryptographic trust boundary. Python module
privacy is not a security boundary: arbitrary code trusted with module-internal
access can also alter the registry or call private constructors. Issuance is not
durable across serialization or process boundaries; pickle reconstruction
creates a newly validated process-local issuance record.

This module has no HTTP client, credential handling, persistence, sandbox or
production execution, route, activation surface, payment capability, HICBC
calculation or product mapping. It establishes no subscription, provider access,
fixture visibility, replacement/reset semantics or launch readiness.

## Verification performed

Using `PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`, the focused
Child Benefit suite passed **135 tests**. The affected PAYE Test Support
Income/Employment/Tax/Benefits/Winter Fuel, HICBC isolation/evidence,
PAYE-evidence and provider HTTP-boundary matrix passed **782 tests**. The
focused suite plus that matrix together passed **917 tests**. AST syntax
validation and exact path/status/hash/diff checks also passed.

The focused adversarial suite covers all scenario states, identical and
different request instances, request/source/integrity substitution, all retained
response semantics, exact numeric type and Decimal scale, unknown names,
observer ordering, hostile values/hooks, armed keys, direct low-level reads,
both equality operand directions, lifecycle operations, malformed state,
valid-to-valid low-level mutation and whole-state transplantation, helper/global
rebinding, transitive `hashlib`/`json` module and attribute rebinding, stateful
old/new digest laundering and reconstruction-identity laundering, UTR absence and
architectural isolation.

The complete suite did not pass (`5413 passed, 19 failed, 136 errors,
7 subtests passed`). Its sole root cause was the unrelated active W8 artefact
compatibility gate: the existing
`reserved/engines/accounting_tax_handoff.py` absolute import from
`reserved.providers.accounting.contracts` is rejected as non-self-contained.
That build failure cascaded into artefact, assurance-metadata, engine-adapter,
release-gate and RW3 tests. This candidate does not modify either W8 path and no
metadata was regenerated. Independent review of the exact uncommitted diff
remains required.
