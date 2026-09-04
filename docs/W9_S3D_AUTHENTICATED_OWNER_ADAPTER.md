# W9-S3D — authenticated runtime-owner adapter

**Status:** bounded, pure/non-durable candidate for independent review. It has
no datastore, no persistence authority, no access authority and is not W9-S3
completion. It is not security, privacy or launch assurance.

## Purpose and exact boundary

W9-S3A produces an admitted minimised annual-position projection. W9-S3C
validates that projection and detaches an exact W9-S3B structural candidate,
but its expected owner and business references are caller supplied. S3D closes
only the stable runtime-owner portion of that gap.

`adapt_authenticated_owner_projection` takes one atomic snapshot of Reserved's
current signed-session `users.id` through the existing `reserved.auth`
boundary. The session owner key and session proxy are captured and checked
against later rebinding. The value must be an
exact positive built-in integer. The accepted W10-S3B canonical owner mapper
then converts it to the exact base-10 string used by S3A/S3C. S3C independently
requires that canonical owner to equal the admitted projection owner before it
will return a detached candidate.

This module does not authenticate a token, verify Clerk claims, create a
session, infer identity from email or provider identifiers, or accept a user ID
argument that a route could substitute. Missing request/session state,
unauthenticated state, boolean/string/float/non-positive user IDs and a
projection belonging to another canonical owner all fail closed.

The caller must separately supply `authenticated_business_reference`. It must
be an exact string and S3C requires exact equality with the admitted projection
business boundary. Reserved's current authentication contract does not expose
a stable authenticated owner-to-business membership mapping, so S3D does not
establish business ownership. A production route must obtain that reference
from a separately reviewed owner-authorised business selection/repository
boundary. Passing a caller-selected string is not access authority.

## Sources and provenance

| Source | Accepted identity | SHA-256 |
|---|---|---|
| W9-S3C projection adapter | accepted checkpoint `c9bdaa6538d68c0c64b2dcde97f224a69c089d30`; integrated as `5f5a948891e1e812a5c74ff6c7266d153bb492fa` | `052712341ab06ca1cdabd407bfacc1ee4cd1603ba3c49f7fc95575465311d9dd` |
| Reserved signed-session auth boundary | `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb` | `adfe50a348a94e1f1a7405a41d92ec39b5d1a9db8c92b64222410701af39ae91` |
| Exact `users.id` canonical owner mapper | `5bc29bcb30c95ea7a5a9430104653b366d709eb6` | `4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed` |
| Founder authority | `FD-W9-001`, current base `8fdcc0414c72393c4f575f7597bd30850b707d35` | see authoritative `FOUNDER_DECISIONS.md` |

The commit and digest labels are review provenance, not credentials, signed
attestation or production activation authority. Runtime validation uses the
captured accepted functions and S3C's exact live-projection validation graph.

## Call and result

The public adapter accepts exactly five named inputs:

1. `projection`: exact live admitted S3A projection;
2. `authenticated_business_reference`: exact separately authorised business
   reference;
3. `evaluated_on`: exact built-in date;
4. `previous_projection`: `None` for version 1, otherwise the exact admitted
   predecessor; and
5. `previous_structural_candidate`: `None` for version 1, otherwise its exact
   S3C-detached predecessor candidate.

The adapter has no public owner argument. It reads the current request's signed
session owner exactly once and rejects every non-exact/non-positive
`users.id`, canonicalises it and invokes the captured S3C boundary. S3C then:

- revalidates exact S3A issuance, content identity and admission;
- rejects stale/future or reconstructed projections;
- binds owner and business references;
- validates complete predecessor continuity for successors;
- returns exact primitive detached state; and
- leaves every persistence, storage, migration, retention, deletion,
  credential, target, production and release flag false.

S3D returns that independently revalidated S3C operation. It does not mint a
new authority-bearing envelope or retain mutable identity state.

## Hostile-boundary verification

Focused tests cover:

- absent request context and absent authentication;
- booleans, strings, floats, zero, negative and missing session user IDs;
- cross-owner and noncanonical owner representations;
- business mismatch, invalid business types and string subclasses, while
  preserving the accepted opaque S3A/S3C identifier policy without substring
  interpretation;
- date subclasses, stale/future and structurally reconstructed projections;
- exact S3A/S3B predecessor continuity and substituted predecessor rejection;
- public dependency rebinding, authentication-session proxy/key rebinding,
  changing session backends and normalised ordinary lookup failures;
- exact named call shape and the absence of database, environment, network,
  filesystem, subprocess or credential behaviour; and
- exact three-path ownership.

## Explicit non-authority and residual gates

This supplies one exact current signed-session `users.id` snapshot to S3C. It
does not close owner-to-business membership authorisation, token authentication,
persistence, runtime access, or W9-S3. This package performs no database,
filesystem, network or environment I/O. It
does not choose a datastore, create a physical schema, run a migration, write a
record, audit access, retain or delete data, handle backups, encrypt data, hold
keys, read credentials, activate production, or grant persistence or access.
It supplies no retention, deletion, encryption or key-custody authority.

In addition to the owner-to-business membership boundary above, W9-S3 still
requires the approved field lifecycle and lawful basis; retention/legal-hold
and backup-expiry rules; selected target datastore; physical schema and
migration; authenticated storage integrity; atomic durable reads/writes and
CAS; access audit; whole-account erasure; raw-payslip deletion evidence; target
failure/recovery and rollback; external privacy/security/legal/operations
evidence; and explicit activation/release authority.

Accordingly, S3D narrows one runtime identity gap only. It is not W9-S3
completion, durable persistence, business-membership assurance, or security,
privacy or launch assurance.
