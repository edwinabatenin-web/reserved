# W9-S3E — authenticated owner-to-business membership contract

## Outcome

This package supplies the smallest target-neutral, non-durable membership
boundary missing after W9-S3D. It reads the current signed-session `users.id`
and checks one requested internal business reference against an immutable
in-memory fake. It has no runtime, persistence or production authority and is
not W9-S3 completion.

Exact paths:

- `reserved/owner_business_membership_contract.py`
- `tests/test_owner_business_membership_contract.py`
- `docs/W9_S3E_OWNER_BUSINESS_MEMBERSHIP_CONTRACT.md`

Base: authoritative integration commit
`030da8a2928473b9b5af35a158ea6ad5c5ad8e49`.

## Authority and safe default

The only owner input is Reserved's already-authenticated signed-session
`users.id`, read once from the existing authentication boundary. The Flask
session proxy and exact session-user key are captured at module import, matching
W9-S3D's namespace-integrity boundary. Later rebinding of either name is an
error, and an out-of-request dictionary or other synthetic session cannot
provide owner authority. There is no public owner argument. A client-supplied
business string is only a selector against the immutable membership snapshot;
possession or guessing of that string cannot create membership.
No provider organisation identifier can grant access. Tenant, realm and company
values are absent from the public call shape.

The contract is owner-only: a business reference cannot be shared by two
Reserved users in one valid snapshot. It grants no collaboration, delegation,
support impersonation or cross-account access. One owner may have multiple
distinct businesses, preserving the already-settled correct-business-selection
journey without creating a sharing model.

Every result is an immutable deterministic value with an unkeyed content
identity. Each fake also has an identity over its complete constructor-sealed
record content and exact positive snapshot version. The digest detects changed
local state only; it is not a signature, MAC, repository credential or writer
proof. Even an active match fixes current-snapshot, sharing, runtime access,
persistence and production authority to `false`.

All authority metadata and reference values require exact `str` instances;
subclasses are rejected. Business and membership references containing the
same secret-shaped markers rejected by W9-S3A/S3B are invalid, including
`secret`, `token`, `password`, `credential`, API-key, bearer, private-key and
live/test-key forms.

## Fail-closed decisions

The evaluator returns an explicit denial for:

- unavailable or malformed authenticated `users.id`;
- invalid requested business syntax or type;
- `membership_missing`, including cross-owner requests;
- `membership_revoked`; and
- `membership_ambiguous`, including active-plus-revoked duplicate state.

Cross-owner requests deliberately return `membership_missing` and expose no
foreign membership reference. Duplicate membership identifiers and one
business reference shared across owners make the fake snapshot invalid.
Construction copies every record into a private canonical tuple and seals
whole-snapshot identity and uniqueness. Later `object.__setattr__` changes to
supplied records or public fake fields, including owner, status, business,
duplicate/cross-owner state, version or identity, cannot change an evaluation.
Seal registration is strictly first-write for each live record and snapshot.
Calling a public `__post_init__` again is rejected before it can replace the
original canonical state or rewrite snapshot identity, including after
low-level mutation. Registry entries hold weak references and are removed when
their objects are genuinely collected, so later object-ID reuse cannot inherit
a stale seal.

An allowed result is deliberately detached. Structural validation verifies its
content identity but never claims it is current. The separate
`assert_allowed_membership_decision_current` check requires the exact current
snapshot version and whole-snapshot identity and the same one active canonical
membership. It therefore rejects an earlier allowed result after a revoked or
replacement snapshot. This freshness check still grants no runtime authority.

## In-memory fake and I/O boundary

`InMemoryOwnerBusinessMembershipFake` accepts only an exact tuple of exact,
immutable records. It is a test and contract vehicle, not a datastore adapter.
No database, filesystem, network, environment or credential I/O exists. The
module does not create, update, revoke, retain or delete a membership; separate
snapshots model those states without claiming lifecycle execution.

## Verification

The focused suite covers authenticated success, exact owner typing, missing
request context, session/key rebinding and synthetic-session rejection,
single-read session behaviour, client-string-only denial, cross-owner
non-enumeration, explicit revocation, ambiguous duplicates, constructor-sealed
owner/status/business/cross-owner mutation, whole-snapshot identity, stale
allowed decisions after revocation/replacement, first-write live seal
registration, record/snapshot re-registration attacks, weak-reference cleanup,
secret-shaped references, exact-string subclasses, decision tamper, absent
provider/owner arguments, bounded imports and the exact three-path package.

Run:

```bash
python3 -m pytest tests/test_owner_business_membership_contract.py -q
python3 -m pytest \
  tests/test_annual_position_persistence_contract.py \
  tests/test_annual_position_repository_contract.py \
  tests/test_annual_position_projection_repository_adapter.py \
  tests/test_annual_position_authenticated_owner_adapter.py \
  tests/test_owner_business_membership_contract.py \
  -q -k 'not test_candidate_changes_only_the_three_new_w9_s3c_paths and not test_candidate_changes_only_the_three_authorised_paths'
python3 -m py_compile reserved/owner_business_membership_contract.py
git diff --check
```

Observed: the focused suite passes all 58 tests. The combined functional
W9-S3A through S3E run passes all 227 applicable tests. The two excluded tests
are older S3C/S3D worktree-local path assertions whose allowlists intentionally
contain only their own historical three-file candidates; when included, those
two assertions reject the newer S3E paths and all other 227 tests still pass.

## Residual gates

This contract does not establish the authoritative source or lifecycle for a
real internal business record. W9-S3 still requires a reviewed physical
membership repository; target datastore/schema/migration; authenticated
integrity and atomic reads; creation, revocation, disconnect and deletion
execution; access audit; lifecycle, lawful-basis, retention, legal-hold and
backup-expiry rules; target cross-owner and recovery evidence; and independent
privacy/security review.

A later separately reviewed adapter must obtain a decision from the physical
repository, re-establish the signed-session `users.id`, current snapshot/version
and owner-only business binding, then supply the authorised business reference
to W9-S3D. This package does not wire that adapter, alter S3A-S3D, or authorise
any durable write, migration, provider access, production activation, release
or go-live.
