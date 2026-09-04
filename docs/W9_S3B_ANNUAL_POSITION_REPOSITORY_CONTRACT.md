# W9-S3B — detached structural repository/schema contract

## Outcome

This package is a disabled-first, datastore-neutral logical record and
repository-operation contract. It is review-ready structural evidence only.

It does **not** import, inspect, authenticate, trust or accept a W9-S3A runtime
projection. Python classes, public exports, functions, code objects and closure
cells from the S3A module are outside its acceptance boundary. This is
intentional: a contract-only module in a mutable shared interpreter cannot
establish that an object retains upstream admission authority.

Instead, W9-S3B accepts only an ordered tuple of ordered `(field, value)` pairs
whose complete value graph consists of exact built-in primitives. It validates
the detached shape using local rules and labels it:

```text
authority_status = structural_candidate_not_upstream_admitted
annual_cash_identity_admitted = false
persistence_authority = false
```

No public path can emit `annual_cash_identity_admitted = true` or persistence
authority. A separately reviewed future adapter must authenticate and validate
genuine S3A output, detach the permitted fields, and meet the target datastore
and governance requirements before any durable write.

Exact paths:

- `reserved/annual_position_repository_contract.py`
- `tests/test_annual_position_repository_contract.py`
- `docs/W9_S3B_ANNUAL_POSITION_REPOSITORY_CONTRACT.md`

No database, SQL, SQLite, filesystem, network, environment, credential,
migration, deployment, KMS/vendor, retention clock, deletion executor, backup
or production behavior is introduced.

## S3A design provenance, not runtime authority

The structural design is pinned to:

| Binding | Exact value |
|---|---|
| Accepted integration commit | `c489c25bab669c64e1c11d28caf29fcde9678fdd` |
| Design source path | `reserved/annual_position_persistence_contract.py` |
| Design source SHA-256 | `da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469` |
| Design schema label | `reserved-annual-position-persistence/1.0` |
| Record purpose | `annual_cash_position_durable_projection` |

These values identify the reviewed design source. They are neither a signature
nor evidence that a runtime object came from S3A. They never grant admission or
persistence authority. The focused test recomputes the source hash for review;
the module performs no repository or file I/O.

The previous runtime closure/code-fingerprint approach has been removed. A
clean-process regression installs arbitrary S3A classes, functions, exports and
mutated closure cells and proves that they are irrelevant because W9-S3B never
imports or consumes them.

## Detached structural candidate

`make_structural_candidate` accepts explicit primitive fields and emits the
canonical ordered candidate. `prepare_annual_position_record` will also accept
that exact detached tuple directly. Both paths independently validate:

- fixed candidate version, S3A design schema label and record purpose;
- mandatory non-admitted/non-authoritative status;
- positive exact-integer record version;
- distinct, syntax-valid owner and business references;
- coherent `YYYY/YY` tax year and supported UK nation;
- exact annual-cash and customer-result identity syntax;
- supported evidence and funding classifications;
- canonical non-negative two-decimal money strings, never binary floats;
- ordered obligation and adjustment tuple shapes, supported unique kinds and
  valid ISO dates;
- unique, syntax-valid evidence references;
- ruleset, as-of date and non-negative staleness horizon;
- exact limitations, prohibited uses and unresolved-governance markers;
- no claimed deletion or erasure outcome; and
- initial-versus-successor predecessor/version rules.

The locally copied minimisation rules were reconciled line by line against the
pinned S3A design source:

| Primitive invariant | Exact detached rule |
|---|---|
| Evidence classification | Only `qualified_local_estimate`; `hmrc_confirmed_exact` is rejected |
| Owner/business grammar | `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}` and no S3A secret marker |
| Secret markers | `secret`, `token`, `password`, `credential`, `apikey`, `api_key`, `bearer`, `private_key`, `sk_live`, `sk_test`, `access_key` |
| Evidence-reference grammar | `[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}` |
| Evidence provenance | Digest-shaped `[a-z-]+:sha256-<64 lowercase hex>` references are rejected as a provenance mismatch |
| Funding | `exact` has no amount; `gap`/`surplus` require canonical, strictly non-zero money |
| Ruleset version | Exact S3A reference grammar `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`; slash is not allowed |
| Staleness | Exact integer `>= 0`; zero is intentionally accepted to match S3A |

Table-driven tests cover every rejection and the important accepted boundaries,
including zero staleness, positive gap/surplus amounts, the 160-character
evidence-reference limit and a valid colon-bearing ruleset reference.

Objects, subclasses, dictionaries, lists, reordered or duplicate fields,
non-primitive values, fabricated admission flags, malformed money, unsupported
enums and changed fixed restrictions fail closed.

The candidate identity is independently computed as
`annual-position-structural:sha256-…` over the exact canonical primitive tuple.
It is a deterministic structural identity, not an S3A content identity,
signature, MAC, writer identity or admission proof.

## Logical row and evidence rows

The annual-position row carries:

- W9-S3B contract version and the non-authoritative status;
- `persistence_authority = false`;
- S3A commit/hash provenance labels;
- the independently computed structural identity;
- every locally validated candidate field; and
- four opaque governance references.

Evidence references are separate ordered logical rows:

```text
(structural_identity, ordinal, user_id, business_id, evidence_reference)
```

Ordinals must be contiguous from zero and every row must match the record
identity, owner, business and candidate reference order. Missing, duplicate,
reordered or cross-boundary evidence fails reconstruction. Raw source evidence,
payloads and credentials are absent.

The row and evidence rows use a versioned envelope with an unkeyed deterministic
digest. This detects accidental changes only. It is not authentication,
encryption or target-writer evidence. Even after a digest is recomputed, local
schema, identity, owner, evidence and authority validations still run.

## Governance gate

Every prepare, decode, create, supersession, read and deletion-plan boundary
requires a producer-issued governance handle with four non-placeholder opaque
references:

| Reference | Namespace | External fact still required |
|---|---|---|
| retention policy version | `retention:` | Accepted legal/privacy retention policy |
| erasure disposition | `erasure:` | Accepted erasure/exception disposition |
| crypto/key version | `crypto:` | Accepted encryption and key-custody profile |
| target profile | `target:` | Verified target/runtime capability profile |

Completeness is shape validation only. It is not legal, privacy, security,
Founder, operations or launch approval. Every governance projection continues
to state no persistence, storage or activation authority.

## Repository decisions

All decisions operate only over finite caller-supplied in-memory snapshots and
perform no I/O.

Initial creation returns `insert_structural_candidate` only when no matching
logical key exists. An exact repeat is `idempotent_existing`. A different
structural identity at the same owner/business/year/nation/purpose/version key,
duplicate snapshot identities or non-unique keys fail closed. No insert occurs.

Supersession requires the same immutable boundary, exact next version and exact
current structural predecessor identity. Its compare-and-swap result is
`cas_apply_contract_only` or `cas_conflict`; neither mutates state or grants
persistence authority.

Owned reads require exactly one matching structural identity and matching owner.
Missing, duplicate and cross-owner results are equally unavailable. A read
reconstructs only the original primitive structural candidate, still explicitly
non-admitted and non-authoritative.

Deletion planning verifies ownership, enumerates record/evidence keys and binds
the opaque erasure disposition and redacted `audit:` reference. It always says:

```text
deletion_performed = false
backup_deletion_claimed = false
persistence_authority = false
storage_authority = false
```

## Opaque-handle lifecycle

Governance, record, operation, read and deletion values use opaque
producer-issued handles. State is keyed only by `id(handle)` and dispatch also
requires `live[id] is handle`; handle equality and hashing are never consulted.

Each issuance has a dedicated weak-reference generation token. On collection,
the callback removes state, the weak live entry and the retained reference only
if that callback is still the current generation for the numeric identity. A
late callback cannot erase a newer identity-reused generation.

Constructor and `object.__new__` forgeries fail. Mutated `__hash__`, `__eq__`,
constructors and descriptors cannot alias handles. Copy/deepcopy issue a fresh
validated capability; pickle/reduction is rejected. Tests create and collect
100 copies for each of the five families, prove registry counts return to
baseline, and simulate the stale-callback/id-reuse boundary.

## Still gated

This package does not choose or implement a datastore, relational DDL, SQL
dialect, transaction isolation, database-native CAS, authentication adapter,
AEAD/integrity mechanism, key custody, IAM, retention duration, lawful basis,
legal hold, deletion execution, backup expiry, hosting target, region,
monitoring, restore, migration, credentials, routes, release or activation.

The next persistence adapter must independently prove genuine S3A source
authentication, field translation/minimisation, atomic CAS, tenant isolation,
authenticated integrity, retention/erasure behavior, backup lifecycle and exact
target behavior. W9-S3B makes none of those claims.

## Verification

```bash
python3 -m pytest tests/test_annual_position_repository_contract.py -q
python3 -m pytest tests/test_annual_position_persistence_contract.py tests/test_annual_position_repository_contract.py -q
python3 -m py_compile reserved/annual_position_repository_contract.py
git diff --check
```

The full repository suite is regression evidence, not persistence or launch
evidence.
