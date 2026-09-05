# Local Stripe ordinary successful renewal — review candidate

This uncommitted candidate is based exactly on
`961168dd5c17fbef7ba96ac1599a7f5888af1db3`, tree
`a7788d5d9fd5c11034045694df25eb8681ab86d0`, on branch
`sol/w10-stripe-successful-renewal`. Its authority is
`work/w10-stripe-successful-renewal-authority.md`. Founder Decisions SHA-256 is
unchanged at `78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
No staging, commit, integration, network, provider data, credential, payment,
activation, release or deployment is performed here.

## Exact bounded outcome

The existing `SyntheticInitialAuthority`, process-wide scope tombstone and
physical repository binding now support exactly one ordinary successor. The
same source module has two public entries, fixing `subscription_create` sequence
one and `subscription_cycle` sequence two. Both enter one private raw-byte signed
ingress and one shared paid-invoice reconciler. The existing signature verifier
has one and only one runtime call site. The accepted paid-surface installer is
unchanged and is reused for all actual request tests.

Sequence-two reconciliation repeats the complete invoice, line,
subscription/item, approved price, InvoicePayment, PaymentIntent and captured
Charge evidence pass twice. It preserves the same owner, billing account,
subscription, customer, item, price, plan, endpoint, account, API version and
test mode. Its purchased start must equal the authenticated predecessor's stored
exclusive service end; the boundary is never derived from the newly fetched
subscription as predecessor authority. Overlap, gap, skipped/repeated period,
scope or plan change, discounts, credits, proration, zero/partial/multiple or
out-of-band payment, object reuse and sequence three refuse without changing the
accepted head.

The successor end is independently rederived from the accepted catalogue cadence:
one calendar month, six calendar months or one calendar year from the exact UTC
predecessor end. The day and time are retained where possible; when the day does
not exist in the target month it clamps to that month's final day, including 29
February in leap years and 28 February otherwise. This is a bounded Reserved
validation rule for the fixed catalogue, not a claim about general Stripe anchor
semantics. Shorter, longer and otherwise cadence-mismatched positive intervals
refuse before authority reservation or repository mutation.

The independent RAM authority reserves the exact canonical successor against
the captured revision, accepted predecessor and store identity, incrementing
revision before any access publication. The repository atomically inserts the
immutable successor and compare-and-swaps the current head from the exact
authenticated predecessor. RAM publication then compare-and-swaps only the
reserved revision to the exact durable receipt/fact/head and rechecks both
domains. Known repository-observed rollback permits only the identical reserved
proposal. Unknown outcome consumes the attempt and poisons/closes an unresolved
repository. A committed successor with failed RAM publication denies both the
successor and stale-predecessor fallback until durable state proves the exact
reserved successor on retry.
The binding snapshot and reservation are published as one immutable tuple under
the authority lock. No exception can expose an incremented/consumed snapshot
without its exact canonical material, predecessor tuple and reservation revision.

## Repository and exact-UTC currentness

New stores have exact metadata version
`reserved-paid-lineage-provenance/2`. The exact checked schema contains immutable
period units keyed by binding and sequence plus a separately readable
`current_heads` record. Event, invoice/object, line, InvoicePayment allocation,
PaymentIntent, Charge, receipt, fact and chained-head identities are unique.
Every public read authenticates every receipt MAC, both lineage links and the
sole current head. Exact v1 metadata is rejected byte-for-byte without migration,
adoption or bootstrap. The historical sequence-one receipt meaning remains
`reserved-initial-receipt/1`; the store schema, MAC/head domain and successor
receipt are versioned separately.

A live exact-UTC fact binds its selected immutable period to the independently
current lineage head and authority revision. Any reservation, publication,
revocation or head change stales an earlier fact. Before the predecessor's
exclusive end, a newly resolved fact can select it only as an authenticated
ancestor of the accepted successor. At that end, only an effective verified
successor can pass. Delayed verification sets
`access_start=max(service_start, verification_completed_at)` and never backfills
the intervening gap. Every signed-session request still resolves the database
user, checks complete lineage/current head, performs exact-UTC admission and
rechecks authority and the persisted head at its final access-decision point.

## Executed assurance

All commands used `PYTHONDONTWRITEBYTECODE=1`, the existing isolated Python
environment, pytest `-o addopts='' -q -p no:cacheprovider`, and disposable test
databases only.

- Three new renewal suites plus the complete accepted initial, signature,
  provenance, exact-UTC, local-dashboard, paid-surface and recovery suites:
  **561 passed** after correction.
- Targeted cadence and reservation-publication hostile selection: **9 passed,
  17 deselected**.
- Affected `tests/test_w10*.py`, auth, claims, WS7 and HICBC matrix:
  **2,391 passed and six failures** after correction. The six failures are the unchanged historical
  dirty-worktree sentinels in completion-map, initial-paid-presentation,
  initial-payment-presentation, internal-route-hardening, paid-access-guard and
  Q1/Q2-policy-closure suites. Each rejects this authorised uncommitted package
  because its own older candidate-path allowlist is intentionally narrower.
  They are not suppressed and this result is not called green.
- Before the independent correction, the complete canonical inventory (run
  without persisting a release result into a protected path) reported root
  **9,333 passed and eight dirty-worktree sentinel
  failures**, artefact correctness **13 passed**, production/artefact parity
  **23 passed**, mandatory RW3 true, and options assurance **138 passed**.
  The two additional root-only sentinels are the annual-position authenticated-
  owner and projection-repository candidate-path checks. Canonical result digest
  was `aeea1c5b8cca1937d70e84c60a7bd6a603e67aa5e087e35fb164f784119c7db9`.
  It is historical evidence for the first freeze, not a post-correction
  canonical result. This uncommitted corrected candidate is explicitly not
  called canonical-green; October remains `not_ready` with 18 blockers.

The genuine Flask tests perform a separately signed initial event, actual
settings GET/form-token/CSRF POST/save, separately signed renewal, and renewed
GET/form-token/CSRF POST/save. Monthly, six-month and yearly plans use
non-midnight instants and exercise immediately-before/exact exclusive end,
early and delayed verification, expired predecessor, replay, contention,
transaction/CAS interruption, revocation, reopen/loss and stored-lineage tamper.

## Independent-review correction

The first freeze received `CORRECTION REQUIRED` for two reproduced defects. It
accepted arbitrary positive successor lengths and assigned the incremented RAM
snapshot before assigning reservation material. This correction adds exact
catalogue-calendar validation before mutation and replaces the two RAM fields
with one lock-published snapshot/reservation tuple. Targeted hostile tests prove
one-second and exact ten-year monthly periods leave revision, reservation,
repository, head and access unchanged; exact monthly/six-month/yearly cases cover
ordinary dates, month ends, leap February and leap-day annual rollover. Tracing
interruptions immediately before and after the atomic publication prove there is
no partial state and that, once published, only the first exact event/evidence
proposal can retry. No unrelated lifecycle or provider behavior was added.

## Candid boundary

This proves a local synthetic initial payment and exactly one ordinary successful
renewal. It does not claim general recurring-cycle support. Sequence three,
failed-renewal recovery or its seven-day anchor, cancellation/races, withdrawal,
refund, dispute, chargeback, restoration, discounts/promotions/partner offers,
real ownership, provider validation, credentials/custody, sandbox/production
access, durable authority recovery, production datastore/migration, customer or
provider evidence, activation, release and overall W10 completion remain refused
or open. Losing the RAM authority still denies authentic rows. Separate Stripe
fetches are not claimed to be an atomic provider snapshot.

The final seven-path SHA-256 manifest and reproducible combined-diff SHA-256 are
frozen after verification and supplied with this candidate for independent
review; the evidence file cannot truthfully embed its own final hash.
