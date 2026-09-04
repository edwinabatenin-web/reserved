# W10-S3A — provider-neutral entitlement decision-candidate evidence

## Scope

This bounded package implements a pure, provider-neutral structural decision
candidate for the lifecycle settled by FD-W10-003. It consumes the accepted
W10-S2A semantics integrated at
`5464bfac7bec6b3456d1895b2355a7e8ce86859b`.

The integrity correction is based on clean integration commit
`5f5a948891e1e812a5c74ff6c7266d153bb492fa` and tree
`639369d06a8da75e8318bec7933993c26e39ace6`. Repository inventory at that
cutoff found no product/runtime importer of the entitlement API: the only
direct importer was `tests/test_w10_entitlement_core.py`. Other W9/W10 files
refer to the accepted historical S3A source/evidence by path, commit or digest.
The correction is therefore confined to:

- `reserved/billing/entitlement_core.py`;
- `tests/test_w10_entitlement_core.py`; and
- this evidence document.

It does not contact Stripe, verify provider signatures, authenticate provider
or event-inbox provenance, ingest webhooks, persist records, grant route
access, charge money, configure credentials or activate billing. It stops
before the unresolved refund, dispute, chargeback, reversal, override,
proration, promotion, partner-offer, invoice/VAT and exact paid-surface
policies.

## Settled lifecycle represented

- Initial ordinary paid access can begin only from a confirmed initial-payment
  observation carrying a current paid-through date. Access is false before the
  initial observation's policy-effective date and after the paid-through date.
- A confirmed renewal must advance the paid period and may return a bounded
  recovery state to ordinary `paid`. If recovery has already expired, the new
  paid interval starts no earlier than that renewal's effective date; it cannot
  backfill the expired no-access gap.
- A renewal received after an ordinary paid period has ended likewise starts a
  new segment at its effective date when there is a gap. A renewal effective on
  the immediately following day remains continuous and invents no gap.
- The first structurally supplied failed-renewal fingerprint enters the distinct
  `payment_recovery` candidate state. It becomes live evidence only after the
  separately authenticated adapter boundary.
- Its deadline is the supplied policy-effective date plus exactly seven
  calendar days, represented as an exclusive date.
- Duplicate events are idempotent. A distinct repeated failure may add evidence
  but cannot alter the first recovery start or deadline.
- Idempotency requires an exact canonical event fingerprint. Reuse of an event
  ID with different owner, subscription, kind, dates or evidence fails closed.
- The structural access candidate remains ordinary-access-true before the
  exclusive deadline, but only from the first-failure recovery start represented
  by its replay-validated event history. If a failure candidate arrives after
  the paid period, any intervening dates remain a truthful no-access gap;
  recovery is never backdated to fill it.
- Cancellation turns automatic renewal off but preserves ordinary access to
  the already-paid period. Cancellation while recovery is already active is
  not inferred and requires later reconciliation policy.
- Paid-period and recovery expiry can be materialised as `suspended` by a pure
  time-boundary projection; trusted clock/persistence ownership belongs later.
- Materialising an expired paid period before applying its first eligible
  failed-renewal fingerprint produces the same seven-day recovery candidate as
  applying that fingerprint first. Owner, replay, event-identity and effective-
  date guards remain identical in both processing orders.

## Fail-closed boundaries

Owner, billing-account and subscription identity must match exactly. A replayed
event ID is a no-op only when its complete fingerprint matches. An older or
same-policy-date distinct event is rejected for
reconciliation because this date-level contract cannot prove an order between
it and the last applied observation. A renewal cannot create initial access,
and a confirmed renewal cannot shorten or merely repeat a paid period. A failed
renewal dated inside an existing already-paid period is rejected rather than
silently truncating that customer's paid access.

## Integrity correction and authority boundary

The former producer-issued-handle claim was not sustainable in a hostile shared
Python interpreter. Its introspectable mutable live-object and state registries
could be coherently populated with an `object.__new__` handle, causing attacker-
selected owner and recovery-deadline values to pass as producer-issued. That
registry model and all retained per-object state have been removed.

Transition and access results are now exact built-in tuples of ordered key/value
pairs containing recursively detached immutable facts. Validation checks exact
shape and primitive types and deterministically replays the complete observation
fingerprint history. A recovery candidate is valid only when the first failed-
renewal fingerprint establishes an exclusive deadline exactly seven calendar
days later; a later failure cannot move it. Reconstructed candidates are
accepted only when they satisfy the same local structural and lifecycle rules.
Both public construction and the captured transition validator require the
observation contract version to be an exact built-in string before comparing
its value; an equality-overriding string subclass cannot select a contract or
reach a paid transition.

Date arithmetic is explicitly bounded. Confirmed-payment paid-through dates
must leave one calendar day available for the exclusive access boundary, and a
failed-renewal effective date must leave exactly seven days available for the
recovery deadline. Unsupported `date.max`/near-maximum inputs fail with a stable
`ValueError`; the latest supported boundaries still project exactly to
`date.max` without leaking `OverflowError`.

Ordinary-access queries are also derived from that exact history at the queried
date, rather than from the final candidate's single current-segment start. Later
restoration therefore cannot erase an earlier legitimate paid or recovery
segment, and cannot retroactively fill an expired or delayed-renewal gap. The
same historical answer is produced whether a time boundary was materialised
before or after the eligible failure or renewal observation.

After replaying observations effective on or before the query date, the access
projection applies the same pure expiry rule as `materialise_time_boundary`.
Consequently an expired paid gap and the recovery deadline itself are reported
as structural `state='suspended'` with access denied, while earlier query dates
retain their historical `paid` or `payment_recovery` state. A later renewal is
reported as `paid` only from its own effective date.

This is deliberately **not admission**. Every transition and access candidate
uses schema `reserved-w10-entitlement-decision-candidate/1.0`, is labelled
`structural_decision_candidate_not_authenticated` and carries exact
false values for provider-observation authentication, provider-provenance
authentication, provider-status authority, persistence authority and
runtime-access authority. Provider labels therefore cannot directly grant
access. Public Python exports and function closures remain mutable to a
sufficiently powerful same-process attacker; this pure module therefore makes
no unforgeability claim.
A separately reviewed, authenticated adapter must establish current provider,
event-inbox, owner and source integrity before any live route or entitlement
consumer may act on these candidates.

`BillingObservationCandidate` validates canonical shape only. The historical
`ReconciledBillingObservation` name remains a compatibility alias and is not
represented as proof that reconciliation occurred. The historical
`apply_reconciled_observation` function name is likewise a compatibility name,
not reconciliation evidence. S3's event inbox and S4's provider adapter must
separately establish signature, source, owner, ordering and replay evidence.
Likewise, the ordinary-access result is a structural policy candidate with
`runtime_access_authority=False`, not S5 server-side enforcement.

The focused regression set covers the former combined registry injection,
recursive closure inspection for retained mutable state, exact detached
reconstruction, coherent public type/state/projector substitution before a
consumer import, owner/history/deadline/authority tampering, tuple subclasses,
non-exact dates, exact contract-version subclasses, maximum-date arithmetic,
observation descriptor substitution, duplicate and conflicting events,
paid-expiry/failure order permutations, late-restoration order permutations and
access during prior paid/recovery segments, inside denied gaps, and at and after
late restoration. Delayed direct renewal and immediately continuous renewal are
both exercised in either materialisation order. These local tests establish
deterministic structure and policy behavior only; they do not establish
provider, target-runtime or production assurance.

## Remaining completion work

W10-S3 remains incomplete. It still needs the durable owner-bound billing
account/subscription/event-inbox/audit/reconciliation model, storage and
concurrency semantics, and authenticated integrity/retention/key-custody
evidence. W10-S4 must translate current Stripe sandbox observations at a
disabled-first edge. W10-S5 must enforce the accepted decision on an enumerated
paid-surface inventory. None of those claims are made by this package.
