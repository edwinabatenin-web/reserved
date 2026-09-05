# W10 Stripe successful-full-refund runtime evidence

This non-production package implements only the frozen successful-full-refund
shape for Stripe API `2025-03-31.basil`. A signed `charge.refunded` event is a
retrieval trigger, never access authority. The immutable current paid receipt
selects the Charge, and two complete fresh Charge plus exact
`/v1/refunds?charge=<id>&limit=100` passes must produce the same closed
canonical projection.

Admission requires a fully refunded, undisputed, succeeded and captured Charge
and one through 100 unique succeeded Refunds with exact Charge, PaymentIntent,
currency and non-null balance-transaction identities. Their positive integer
amounts must sum exactly to the paid receipt's captured amount. Pagination,
partial or changing evidence and every dispute, chargeback, reversal, failure,
reinstatement or restoration label has no new entitlement effect.

The fresh version-five disposable store refuses older metadata and appends one
authenticated terminal withdrawal control either to the paid head or to one
compatible scheduled-cancellation head. The Reserved verification instant is
sampled exactly once inside the durable CAS transaction after source and
predecessor validation. Exact replay returns the original receipt, fact, head
and instant. No migration, restoration, provider contact, credential use,
customer data, refund execution, activation or production custody is supplied.

The distinct version-three withdrawal fact, runtime decision and paid-access
guard deny all 28 accepted paid endpoints at the transition while retaining the
existing route registration and handler wrappers. Existing paid, cancellation
and failed-renewal protocols remain separately versioned and fail closed on the
withdrawal shapes.

## Independent-review correction

The first review's four reproduced defects are corrected without widening the
source or runtime outcome. An unknown commit now consumes the live withdrawal
attempt unless the repository independently authenticates the exact durable
control from that attempt. `current_fact` and validation of already issued paid
facts both refuse a terminal withdrawal head, so an older reader cannot mint or
retain a paid capability after withdrawal.

Authenticated reconciliation dispositions now consume the scoped event ID and
raw digest. Exact replay returns the same zero-effect
`reconciliation_required` result, while changed bytes or a changed object key
under that event ID fail closed before admission. A valid trigger naming an
authenticated ancestor paid Charge after renewal creates that same durable
zero-effect disposition against the current head instead of being discarded as
an unbounded refusal. The disposition MAC, canonical body, identity, store and
binding are verified before the event ID is trusted.

The corrected five-suite direct set passes 48 tests. The complete affected set
passes all 879 tests without deselection. The broad W10/authentication/HICBC
selection naturally reports 3,026 passes and
five historical dirty-path-only sentinel failures; the final frozen rerun keeps
those node IDs explicit. The full repository naturally reports 10,018 passes and
seven historical dirty-path-only sentinel failures, adding two older annual-
position package sentinels and no behavioral failure. Six focused reviewer
regressions pass, covering all four findings plus independently durable
post-commit resolution and conflict-MAC authentication. No behavioral failure
is excluded.
