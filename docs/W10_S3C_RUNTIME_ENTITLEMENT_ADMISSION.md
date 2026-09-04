# W10-S3C runtime-entitlement admission

## Boundary

`reserved/billing/runtime_entitlement_admission.py` is a provider-neutral,
route-less and non-durable composition boundary. It does not discover or
authenticate provider evidence. Instead, a future composition root must bind
two distinct functions from an independently authenticated, admitted,
owner-bound billing-fact authority. The adapter does not authenticate provider evidence.
The validator and projector must agree on
one exact, content-identified billing-fact projection before this adapter can
issue an opaque runtime-entitlement handle.

Detached S3A/S3B tuples, provider observations, caller-created primitive
tuples, copied values and forged handles are not admission. This module does
not authenticate provider evidence, call a provider, read configuration, bind
a session, access a database, persist state or wire a route. It does not claim
that a future source is authentic merely because its functions are bound.
Every issued runtime handle also retains the exact opaque admission capability
that issued it. A different binding cannot advance, preserve, suspend or
restore that lineage, even if its primitive fact identifiers happen to match.
This authority identity is never projected as a serialisable field.

## Exact seams

The input projection protocol is
`reserved-owner-bound-billing-fact/1.0`. It binds:

- exact authenticated owner, billing-account and subscription identities;
- an admitted billing-fact identity recomputed from canonical content;
- exact decision sequence and predecessor-fact identity;
- a timezone-aware UTC transition instant;
- a bounded date interval and, only for recovery, its exact UTC deadline;
- one closed derivation and withdrawal-attribution vocabulary; and
- an explicit false value for provider-observation direct authority.

The output projection is exactly
`reserved-runtime-entitlement-decision/1.0`, including the content-derived
runtime decision identity expected by W10-S5D. Only the opaque handle is live
authority. The public validator and projector independently expose the same
immutable primitive view for W10-S5D's agreement check.

## Founder-decision consequences

`FD-W10-003` is enforced as follows:

- a verified initial payment may establish the first paid decision only;
- a verified renewal payment requires and advances an admitted predecessor;
- a verified renewal failure requires a current admitted paid predecessor and
  creates exactly seven UTC calendar days of `payment_recovery`;
- recovery cannot be created without an entitled predecessor or extended by a
  repeated failure; and
- restoration after withdrawal is limited to an admitted verified
  reinstatement, successful reversal or replacement payment.

`FD-W10-004` is enforced at the admission boundary. A verified full withdrawal
attributable to the current subscription period produces `suspended` with no
ordinary paid access at the next admission. It does not delete the account,
data, billing history or subscription, because this module has no such
capability. A full withdrawal attributed to another period cannot change the
current valid access interval.

Open, partial, ambiguous, contradictory or unresolved withdrawal evidence may
preserve only a valid existing entitled predecessor. It must
never create, restore, extend, prolong or strengthen entitlement. Unknown attribution for a
claimed verified full withdrawal fails closed; it must instead be represented
through the applicable uncertainty category until reconciled.

## Lineage and temporal safety

Every successor must match the exact owner, billing account and subscription
of its opaque predecessor, advance the billing-fact sequence by one, and name
the predecessor fact identity. The emitted runtime decision independently
advances its own sequence and names the predecessor runtime identity. Replay,
wrong predecessor, cross-owner/account/subscription use, future facts,
out-of-order transitions, cross-binding lineage and stale facts fail closed.

The half-open runtime validity interval must contain both the exact UTC
transition date and the admission evaluation day. A
payment-recovery transition and deadline must both be exact UTC midnight, the
deadline must be seven days after transition, and the output interval must end
on that deadline. Ordinary preservation can only narrow an existing interval.

## Explicit non-authority

This candidate has no I/O, provider, network, configuration, authentication,
session, database, route, persistence, checkpoint, release or production
authority. It neither creates nor verifies provider events and cannot establish
the globally latest durable billing state. It supplies only the route-less
runtime composition seam that W10-S5D can evaluate after future independently
assured billing-fact admission exists.

Accordingly, this package does not complete W10-S3 or W10-S5. Durable billing
facts, authenticated provider ingress, persistence and atomic ordering,
multi-worker reconciliation, route wiring, target-environment assurance and
release activation remain separate gates.
