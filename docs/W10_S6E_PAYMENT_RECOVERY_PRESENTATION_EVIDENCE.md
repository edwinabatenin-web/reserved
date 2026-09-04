# W10-S6E detached payment-recovery copy candidate

## Bounded outcome

This slice produces deterministic, recursively detached structural copy from
untrusted structural facts describing a `payment_recovery` window. It is a
zero-authority candidate for later customer-language work. It is not upstream admission
and not live customer presentation, and it is not evidence that the
supplied owner, state, timestamps, provider event or entitlement is authentic.

The fixed copy says that the subscription payment is being recovered, that
ordinary access continues only **before** the supplied exclusive deadline, that
ordinary access is suspended **starting** at that deadline unless recovery has
been verified, and that verified recovery can return the subscription to its
paid state after reconciliation. It never says that recovery is normally paid
or active.

## Exact authority and source baseline

**Integration base:** `23f4d3dc742474d3a672388a1ebe99962505b234`

**Integration tree:** `b85207f9c7dd50042206a0aa43391300f69374b6`

| Source | Last integrated checkpoint | SHA-256 at the base | Use |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | `FD-W10-003` wording and exclusive seven-day recovery policy only |
| `reserved/billing/entitlement_core.py` | `94bd87f019dc226ec8c73f32515229189500cf06` | `b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b` | A separate upstream contract whose mutable public exports are deliberately not imported or treated as authority here |
| `reserved/billing/provider_lifecycle_authority.py` | `5464bfac7bec6b3456d1895b2355a7e8ce86859b` | `fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a` | A separate lifecycle authority source, not an admission mechanism for this candidate |

The hashes bind the reviewed design context. They do not make a caller-supplied
facts dictionary authoritative. A future authenticated owner-bound adapter must
validate and project admitted canonical state into an equally reviewed customer
render/delivery boundary.

## Detached structural boundary

The builder accepts only an exact, ordered built-in dictionary containing:

- schema version;
- owner, billing-account and subscription references;
- the exact literal state `payment_recovery`;
- a supplied recovery-start timestamp;
- a supplied exclusive recovery-deadline timestamp; and
- a supplied evaluation timestamp.

References are validated and owner-matched locally but are never rendered.
Timestamps must be exact UTC-second strings, the supplied recorded deadline
must be exactly seven calendar days after the supplied recorded start, and the
evaluation must lie in the start-inclusive/deadline-exclusive window. Comparing
the two supplied timestamps validates the recorded interval; it does not derive,
replace or authorise either timestamp. These are local consistency checks, not
provenance or admission. The supplied validated deadline is the deadline that
is formatted; it is not recomputed, extended or inferred from provider status.
The customer-facing deadline always includes the exact supplied second in
`HH:MM:SS UTC` form, so the exclusive boundary remains unambiguous even when
the recorded deadline is not minute-aligned.

The output contains only recursively exact `tuple`, `str` and `bool` values. It
contains no mutable registry, handle, weak-reference admission, retained input,
per-result state or object-identity requirement. An independently reconstructed
identical tuple validates identically, which is intentional evidence that this
is detached data rather than an authority-bearing object.

Every authority flag is exact `false`:

- upstream admission;
- customer rendering;
- delivery;
- notification;
- entitlement;
- provider;
- persistence; and
- activation.

## Fail-closed local validation

The candidate rejects malformed schema/state/reference fields, cross-owner
facts, mutable/subclass inputs, non-canonical timestamps, non-seven-day,
contradictory or stale windows, altered fixed copy, altered deadline display,
missing/reordered/extra fields, and any non-false authority flag.

It contains no import from the entitlement or provider-lifecycle modules.
Coherent substitution of their public classes/projectors before this module is
loaded therefore cannot manufacture admission. This does not prove the future
authenticated adapter; it merely removes the earlier false admission claim.

## Explicit exclusions

This slice provides no authenticated adapter, canonical-state provenance,
route, template, HTML renderer, email/SMS/push delivery, notification scheduling,
clock, network call, Stripe/provider integration, signature verification,
persistence, entitlement transition, entitlement enforcement, payment, refund,
support override, production activation or launch assurance.

It does not answer W10 Q1/Q2/Q3, close W10-S6, close any S7A threat or W9 gate,
or close any provider, legal, finance/tax, security, target-runtime, activation,
release or go-live gate.

## Candidate ownership

Only these new paths are authorised:

- `reserved/billing/payment_recovery_presentation.py`
- `tests/test_w10_payment_recovery_presentation.py`
- `docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md`

The candidate must stop uncommitted for fresh independent re-review.
