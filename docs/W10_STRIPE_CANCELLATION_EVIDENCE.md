# W10 Stripe scheduled-cancellation runtime evidence

Review candidate prepared on 5 September 2026. This is bounded local synthetic
evidence only. It is not provider validation, activation authority, production
assurance, release authority, or overall W10 completion.

## Authority and immutable baseline

- Branch: `sol/w10-stripe-scheduled-cancellation`
- Base commit: `fee273c0789eaa0faf46016f33bbb87086390785`
- Base tree: `4d9ad12bcfbf267a48fb82a61a911987025bc2ec`
- Runtime authority SHA-256:
  `04f668a90c2e973658dcd11c49b050b9bd7221928d2dcba4c5860c979cde727a`
- Source annex SHA-256:
  `573e549a8c5067a41a56a042854979116ae3d764b9e8ab287741ad713e6acf13`
- Source-review acceptance SHA-256:
  `4508299845427be9684e523781195ef211c3fb00a3adc27fdd10f18d9d384e50`

The worktree matched the exact branch, commit and tree and was clean before the
candidate was changed.

## Bounded implementation

The existing signed local Stripe ingress now exposes one additional entry,
`ingest_scheduled_cancellation`. It accepts only a signed Basil
`customer.subscription.updated` false-to-true `cancel_at_period_end` transition
with a non-null request ID, exact `cancellation_requested` reason, separately
retrieved agreeing subscription, the already-bound one-item/quantity-one price
and identities, and an item interval exactly equal to the current authenticated
paid receipt. Every supported absence predicate must be explicitly present with
its exact `None`, empty-list or false type in both objects, including offer,
discount, promotion and item-proration fields. New admission must complete
strictly before the paid end.

Newly created cancellation-capable stores use exact metadata/store-format version
`reserved-paid-lineage-provenance/3`. Version-two stores are rejected without
mutation, migration or adoption, so a prior v2 reader cannot open a new store and
ignore cancellation. The existing table DDL and paid receipt/MAC meaning remain
unchanged. The authenticated bounded disposition table stores at most one
scope-keyed lifecycle-control receipt using new domain-separated receipt/fact/head
identities and MAC material. The paid lineage and paid current-head row remain
unchanged. The repository transaction compares the exact paid/lifecycle
predecessor before inserting the control; sequence-two renewal checks the same
table inside its transaction, so renewal and cancellation have one atomic winner.
All live paid decisions authenticate both the paid lineage and current lifecycle
head.

The process-local authority reserves the exact proposal before repository work
and publishes only after durable readback. Known rollback can retry only that
reserved proposal. Unknown outcomes consume the attempt unless exact durable
readback proves the control. Unresolved rollback poisons and closes the
repository. Already-durable exact replay is resolved before the current-time
boundary check, reuses the identical live fact, and preserves receipt material,
verification time, authority revision, boundary, paid head and lifecycle head.
That evidence replay remains available at/after the end while actual paid access
remains denied.

An authorised reopen of the same physical v3 store rebinds the original opaque
fact's live reader using the authenticated `(store_id, path, device, inode)`
identity rather than Python repository-object identity. The fact remains the
same object and every subsequent projection reauthenticates durable state through
the reopened reader. A copied/forked store has a different physical identity and
is refused before cache rebinding; wrong authority, changed fact material, stale
revision/head, metadata tamper and stale handles remain fail-closed.

The control effect is only
`subscription_scheduled_to_end_at_paid_period_boundary`. It does not shorten or
extend the paid interval and contains no actor attribution. `request.id`, reason,
metadata, Stripe `created`, and `canceled_at` never select the access boundary.

## Frozen code and test artefacts

SHA-256 values before adding this evidence document:

| Path | Lines | Bytes | SHA-256 |
|---|---:|---:|---|
| `reserved/billing/local_stripe_initial_payment.py` | 977 | 53,696 | `e767ad6df8793bed682de1d0e9031e90ec7f5cc1154d0bc0df8ba04f60745012` |
| `reserved/billing/local_billing_provenance_repository.py` | 426 | 22,220 | `76fe8302d41ac540aa13606ae110bc3e2b63809acc5ecefd8ff67a72d6a8dee5` |
| `tests/test_w10_stripe_cancellation.py` | 420 | 22,499 | `11b9e8cb410b081171737891941f48565bc7beb745d92216b104d981c88b1a9d` |
| `tests/test_w10_billing_provenance_cancellation.py` | 203 | 9,913 | `a224ebda960cdf7e70815487f5ea7b4e3a89b2b99d2e8adf7137ae292eb9e3fd` |
| `tests/test_w10_exact_utc_cancellation.py` | 185 | 9,444 | `79e0713732f1a514642434a10852d9d38a27cd1f39992d2b258bc8b587681e95` |
| `tests/test_w10_billing_provenance_successful_renewal.py` | 190 | 9,148 | `d720dfddd4cdc974a1a001ae83de95b88caf110be514cd6dce0187e1a70da378` |

The deterministic binary-capable combined diff of those six paths, ordered as
the two runtime paths, three new test paths and exact existing-test correction,
has SHA-256
`7b8781078f67c8d68cb53c8b03142d1c631d994abb9f18167f0c7cdac8c2d1cf`.
The delivery report must separately freeze this document and the complete
seven-path combined diff, avoiding a recursive self-hash claim.

## Verification

- New cancellation suites: 106 passed.
- Natural focused superset combining the new suites with accepted Stripe
  initial/renewal, provenance, signature, exact-UTC, paid-surface, dashboard and
  auth suites: 616 passed.
- Focused unchanged Stripe initial/renewal, provenance, signature, exact-UTC,
  paid-surface, dashboard and auth suites, including the exact authorised
  successful-renewal version regression: 510 passed.
- Broad W10/auth/HICBC affected matrix: 2,487 passed in the final run, with
  six historical candidate-path self-tests deselected because their assertions
  deliberately allow only the paths of their own earlier packages.
- Python bytecode compilation and `git diff --check`: passed.

Coverage includes initial and sequence-two paid periods; monthly, six-month and
annual arbitrary-second boundaries including month-end/leap cases; null and exact
`cancel_at`; before/at/after the exclusive end; the actual signed-session settings
GET and CSRF POST/save path; replay, changed duplicate, concurrent duplicate,
competing proposal and renewal/cancellation race; source/signature/binding and
unsupported-state negatives; transaction, rollback, readback and publication
failures; durable tamper, physical-store replacement, revocation, authority loss
and forged/stale handles. Reviewer reproductions cover missing and mistyped
absence fields, offers, item discounts/proration, v2 refusal without mutation,
and identical exact replay at the exclusive boundary with access still denied.
The reopen reproduction additionally freezes identical replay before, exactly at
and after the boundary through the same physical reopened store, and refuses a
byte-identical copied store.

## Residual limits

No network or live Stripe call was made. No account, endpoint, key set, API
version, Customer Portal configuration, credentials or customer data was
validated. There is no production datastore, migration, activation, restart
authority recovery, schedule removal, immediate cancellation, terminal deletion,
sequence-three renewal, failed-renewal recovery, refund, withdrawal, dispute,
chargeback, restoration, release or go-live work in this candidate.

The six historical path-self-tests are not product-behavior failures and cannot
accept this separately authorised seven-path package without changing protected
tests. They remain unchanged and are the only known broad-matrix exclusions.
