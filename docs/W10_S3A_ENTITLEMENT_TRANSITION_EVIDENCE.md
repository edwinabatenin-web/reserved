# W10-S3A — provider-neutral entitlement transition evidence

## Scope

This bounded package implements a pure, provider-neutral transition projection
for the lifecycle settled by FD-W10-003. It consumes the accepted W10-S2A
semantics integrated at `5464bfac7bec6b3456d1895b2355a7e8ce86859b`.

It does not contact Stripe, verify provider signatures, ingest webhooks,
persist records, grant route access, charge money, configure credentials or
activate billing. It stops before the unresolved refund, dispute, chargeback,
reversal, override, proration, promotion, partner-offer, invoice/VAT and exact
paid-surface policies.

## Settled lifecycle represented

- Initial ordinary paid access can begin only from a confirmed initial-payment
  observation carrying a current paid-through date. Access is false before the
  initial observation's policy-effective date and after the paid-through date.
- A confirmed renewal must advance the paid period and may return a bounded
  recovery state to ordinary `paid`.
- The first reconciled failed-renewal observation enters the distinct
  `payment_recovery` state.
- Its deadline is the supplied policy-effective date plus exactly seven
  calendar days, represented as an exclusive date.
- Duplicate events are idempotent. A distinct repeated failure may add evidence
  but cannot alter the first recovery start or deadline.
- Idempotency requires an exact canonical event fingerprint. Reuse of an event
  ID with different owner, subscription, kind, dates or evidence fails closed.
- The access projection remains ordinary-access-true before the exclusive
  deadline, but only from the actual first-failure recovery start. If a
  reconciled failure arrives after the paid period, any intervening dates remain
  a truthful no-access gap; recovery is never backdated to fill it.
- Cancellation turns automatic renewal off but preserves ordinary access to
  the already-paid period. Cancellation while recovery is already active is
  not inferred and requires later reconciliation policy.
- Paid-period and recovery expiry can be materialised as `suspended` by a pure
  time-boundary projection; trusted clock/persistence ownership belongs later.

## Fail-closed boundaries

Owner, billing-account and subscription identity must match exactly. A replayed
event ID is a no-op only when its complete fingerprint matches. An older or
same-policy-date distinct event is rejected for
reconciliation because this date-level contract cannot prove an order between
it and the last applied observation. A renewal cannot create initial access,
and a confirmed renewal cannot shorten or merely repeat a paid period. A failed
renewal dated inside an existing already-paid period is rejected rather than
silently truncating that customer's paid access.

Transition state is held behind an exact producer-issued in-memory handle. The
kernel validates the handle against private live-object and canonical-state
registries before every transition or access projection; callers cannot create
or mutate a handle into a paid state. The immutable built-in projection is for
review and later persistence design only and carries no provider authenticity.

`ReconciledBillingObservation` validates canonical shape only. Its constructor
is deliberately not represented as provider authenticity. S3's event inbox and
S4's provider adapter must separately establish signature, source, owner,
ordering and replay evidence before applying this transition. Likewise,
`AccessProjection` is a policy projection, not S5 server-side enforcement.

## Remaining completion work

W10-S3 remains incomplete. It still needs the durable owner-bound billing
account/subscription/event-inbox/audit/reconciliation model, storage and
concurrency semantics, and authenticated integrity/retention/key-custody
evidence. W10-S4 must translate current Stripe sandbox observations at a
disabled-first edge. W10-S5 must enforce the accepted decision on an enumerated
paid-surface inventory. None of those claims are made by this package.
