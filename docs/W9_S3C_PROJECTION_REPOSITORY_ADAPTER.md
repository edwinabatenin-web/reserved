# W9-S3C — admitted projection to detached repository-candidate adapter

**Status:** bounded, pure adapter candidate for independent review; no
datastore, no migration, no persistence authority, and not W9-S3 completion.
It is not security or launch assurance.

**Candidate base:** integration commit
`1d91526d11b5291d5388c78940682ca02edeb61e`, tree
`e2fc725961f816d80eed9e5373d738e5e21a024c`.

## Purpose

FD-W9-001 authorises a durable minimised structured annual tax and cash
position, while retaining separate gates for exact lifecycle, lawful basis,
datastore, migration, encryption/key custody, target evidence and activation.
The accepted W9 completion map therefore calls for a separately reviewed
adapter between:

- W9-S3A's live, admission-validated minimised projection; and
- W9-S3B's detached, exact-primitive structural candidate.

This package supplies only that pure boundary. It accepts an exact live S3A
projection, validates it through the captured S3A identity/integrity graph,
requires the exact admission bit, binds the projection's user and business to
explicit current authenticated-owner inputs, enforces its declared freshness
horizon and copies only the already-minimised S3A fields into S3B.

The adapter produces a deterministic structural operation and candidate. The
source admission is not transferred. S3B continues to set
`annual_cash_identity_admitted = false` and `persistence_authority = false`.
The operation is structurally reproducible and carries no issuer credential;
its validation proves shape and identity, not a durable writer identity.
Its source-projection identity is deterministically recomputed from the exact
candidate content using S3A's content-identity semantics; a merely well-formed
or independently substituted digest is rejected.

## Exact accepted source identities

| Boundary | Accepted commit | SHA-256 |
|---|---|---|
| `reserved/annual_position_persistence_contract.py` (W9-S3A) | `c489c25bab669c64e1c11d28caf29fcde9678fdd` | `da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469` |
| `reserved/annual_position_repository_contract.py` (W9-S3B) | `110a90043dfc770c70059482be9d7b7e237749a6` | `fa033039500b97bab04f3a047c07ad661c14c49d6167d65396d4d9ab0227053e` |
| `FOUNDER_DECISIONS.md` through current base | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` |

These are design and review provenance. They are not signatures, credentials,
datastore selection or activation authority.

## Call boundary

`adapt_admitted_projection_to_structural_candidate` accepts exactly six named
inputs:

1. `projection` — an exact live W9-S3A projection;
2. `authenticated_user_id` — exact current Reserved owner reference;
3. `authenticated_business_id` — exact current business boundary;
4. `evaluated_on` — exact current evaluation date;
5. `previous_projection` — `None` for version 1, otherwise the exact admitted
   S3A predecessor; and
6. `previous_structural_candidate` — `None` for version 1, otherwise the exact
   S3B candidate corresponding to that predecessor.

The owner/business inputs are binding facts supplied by a future authenticated
runtime owner adapter. This pure package does not establish a web session or
authenticate a customer by itself. Exact equality prevents a supplied owner or
business from crossing the boundary, but the real authentication adapter and
its target evidence remain required.

The projection must be current at `evaluated_on`. A future-dated projection and
a projection observed after `as_of + stale_after_days` fail closed. The exact
end of the declared horizon remains accepted. This is an admission freshness
check, not a retention clock.

## Admission and mutation resistance

The adapter captures the exact S3A/S3B classes, slot descriptors, functions and
recursive closure graph at module construction. Each invocation checks that
the captured functions, code, defaults and closure-cell contents have not been
replaced. It reads retained S3A state through the original slot descriptors,
validates before and after detachment, and rejects a changed identity or
admission state.

Consequently, public reconstruction, `dataclasses.replace`, pickle decoding,
duck types, subclasses, class-property masking, exported-name rebinding,
mutable-default injection, code replacement and closure-cell substitution do
not recreate the accepted live-projection boundary.

This remains an in-process contract rather than a cryptographic writer proof.
There is no mutable issuer registry, token or handle state. Even a copied or
forged structurally valid operation has every authority flag fixed to false and
cannot recreate producer authority. Authenticated durable writer integrity is
a later target-specific gate.

## Detachment and minimisation

The adapter preserves only the S3A/S3B common minimised facts:

- record version and purpose;
- owner, business, tax year and supported nation;
- annual/cash and W8 customer-result identities;
- qualified-local-estimate classification;
- canonical two-decimal annual liability, dated obligations and adjustments;
- funding classification and exact amount boundary;
- ordered evidence references, ruleset, as-of date and staleness horizon;
- fixed customer-result limitations and prohibited uses;
- every unresolved lifecycle/target input;
- honest not-deleted/unresolved-erasure state; and
- exact supersession identities.

No rendered copy, raw payslip, provider payload, credential, secret, environment
state, database object or mutable application object enters the candidate.
Dates and money become canonical strings; the complete S3B candidate graph is
made only of exact built-in tuples, strings, integers, booleans and `None`.
Operation validation rejects subclasses at every fixed provenance, status and
identity boundary and returns a freshly rebuilt exact-primitive graph rather
than caller-owned tuple objects. A caller that recomputes a coherent structural
operation still gains no producer or persistence authority: every authority
flag remains false and validation remains structural rather than issuer proof.

## Supersession

For a successor, both predecessor inputs are mandatory. The adapter:

1. revalidates the current and previous live admitted S3A projections;
2. uses S3A's finite-chain validator to prove the exact content predecessor,
   version progression and owner/business/tax-year/nation/purpose boundary;
3. validates that the supplied previous S3B candidate is the exact detached
   representation of that S3A predecessor; and
4. links the new S3B candidate to the previous structural-candidate identity.

The detached operation carries that minimum prior structural candidate so its
validator can recompute both the prior S3A content identity and prior S3B
structural identity. It also enforces exact version progression and unchanged
record-purpose, owner, business, tax-year and nation boundaries. Consequently,
neither predecessor field is accepted merely because it contains a correctly
shaped, freely recomputable digest.

This preserves the two distinct identity domains rather than substituting an
S3A content digest where S3B requires a structural identity. The adapter does
not query a repository or prove that either candidate was stored. Atomic target
CAS and complete durable-chain reconciliation remain later work.

## Explicit non-authority

Every adapter operation fixes all of these to false:

- source-admission transfer;
- persistence and storage authority;
- migration authority;
- retention or deletion authority;
- legal, credential, encryption or key-custody authority;
- target, activation, release or production authority.

In short, it grants no retention or deletion authority and no legal,
credential, encryption or key-custody authority. It also grants no target,
activation, release or production authority.

There is no database, filesystem, environment, network, SDK, provider,
credential, migration, deletion executor, backup executor, commit, release or
production behavior in the module.

## Verification

`tests/test_annual_position_projection_repository_adapter.py` covers:

- exact S3A/S3B commit and source-hash bindings;
- successful version-1 and successor detachment;
- exact owner/business/provenance/uncertainty/minimisation preservation;
- exact primitive output and deterministic identities;
- rejection of reconstructed, decoded, duck-typed, subclassed, tampered,
  cross-owner, cross-business, future, stale and malformed inputs;
- rejection of missing, mismatched and unadmitted predecessor state;
- S3A content-chain to S3B structural-chain translation;
- detached predecessor-content binding, immediate version/boundary checks and
  rejection of source/structural predecessor substitution;
- tampered operation, identity, owner, date and authority flags;
- exact-string subclass/equality attacks, regex-valid source substitutions,
  candidate/source recomputation mismatch and canonical output detachment;
- exported-name, class-descriptor, callable-default, upstream-code and closure
  mutation attacks;
- absence of a mutable issuer registry and local mutable global resolution;
- bounded imports/no I/O; and
- exact three-path package ownership.

Focused S3A/S3B tests remain the authoritative coverage of their respective
contracts; this package does not silently broaden or duplicate them.

## Residual gates

W9-S3 still requires all applicable accepted completion-map evidence,
including:

1. approved field-by-field lifecycle, purpose and lawful-basis evidence;
2. approved retention periods, legal-hold exceptions and deletion semantics;
3. selected and verified target datastore, encryption and key custody;
4. a physical schema and migration;
5. durable read/write, atomic target CAS and authenticated integrity;
6. authenticated runtime owner adapter and access audit;
7. whole-account erasure and backup expiry evidence;
8. provable raw-payslip deletion without payload retention or logging;
9. target failure/recovery, corruption and rollback evidence;
10. independent security/privacy/legal/operations and integrated acceptance;
11. explicit production, activation, release and go-live authority.

This adapter closes only the missing pure S3A-to-S3B detachment boundary. It is
not W9-S3 completion, not durable persistence, not security or launch
assurance, and not evidence that any target may write, retain or delete data.
