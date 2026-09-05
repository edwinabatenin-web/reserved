# W10 Stripe later-period restoration runtime evidence

Status: uncommitted implementation candidate for fresh independent review.

This candidate is bound to commit
`d4bb9a579c40e0f06710c84654efd98495513370`, tree
`0726d0376133f6e5ba7e27ce4cd396b8a9d0414e`, and accepted source-annex
SHA-256
`24b2a81aa8adf1e1416e9645846d3df6756daeb9076e178153a6145c842fd1c3`.
It is not a checkpoint, independent acceptance, provider activation, release,
or go-live decision.

## First freeze and focused correction

The first uncommitted freeze had canonical binary-diff SHA-256
`9e4b9ab81e461d89f6c4dc43981e793a1b514c88b86954e2581c007a52979d1a`.
Independent review rejected that freeze for one reproducible transaction-
consistency defect: an arbitrary exception before the repository method entered
its transaction returned `commit_outcome_unknown`, but absence of a proven
durable sequence-two successor did not poison the still-reusable repository
handle. An identical retry could therefore append and publish the successor
despite the earlier unknown outcome.

The focused correction permits arbitrary-exception recovery only when an
authenticated `read_sequence(binding, 2, key)` proves the exact reserved
proposal and exact receipt/head. Otherwise the existing repository fail-closed
state is engaged and the handle is poisoned and closed before the unknown
outcome is returned. The separate `CommitOutcomeError(False)` known-rollback
path remains usable and is not converted to uncertainty.

The exact regression interrupting before repository transaction entry, the
known-rollback test, and committed-but-unpublished recovery test passed together:
`3 passed in 0.36s`. The corrected candidate remains uncommitted and requires a
fresh independent review.

The second uncommitted freeze had canonical binary-diff SHA-256
`044502b8c1b6fe16b432dce6b9c57c3ef6d02d4dce47a1f6baf00294ed3ae8af`.
Fresh review required two further focused corrections. First, an exact
repository-observed rollback was being treated like an ordinary reconciliation
failure and tombstoned, preventing the retained exact reservation from retrying.
Second, admission checked a tombstone only by event ID, not by its authenticated
consumed `object_key`, and did not preflight restoration event-ID reuse against
the authenticated paid and lifecycle-control history.

The focused correction preserves `CommitOutcomeError(False)` as a
`committed=False` refusal without recording a conflict. Its reservation may be
retried only by the same raw event and exact source proposal; changed bytes or
source remain refused. Before retrieval/reservation, the runtime now
authenticates every bounded conflict record for the binding, refuses reuse of a
tombstoned Invoice/type object key by a different event, and refuses an event ID
already consumed by the paid lineage or lifecycle controls. The full-withdrawal
event ID therefore cannot become a restoration event. Ordinary fresh,
non-colliding restoration remains supported.

The third uncommitted freeze had canonical binary-diff SHA-256
`0e3c564d194da0c21460a09967e3f050319501752ebdc09263a075797cfda3e9`
and exact size 141,342 bytes. Fresh review reproduced one remaining
transaction-ordering defect: a second event could complete an empty conflict
preflight, pause while a first event durably tombstoned the same Invoice/type
object key, and then resume and commit sequence two because the repository did
not re-authenticate conflict rows at its transaction serialization point.

The third focused correction re-authenticates every bounded conflict row with
the independent receipt key inside `BEGIN IMMEDIATE`, before lifecycle-head CAS
or insert, and refuses a same-binding row that has consumed either the proposal
event ID or Invoice/type object key. A deterministic regression inserts the
authenticated disposition immediately after ingress preflight and covers an
event-ID collision, an object-key collision, and an unrelated disposition that
must not block the valid proposal; a forged disposition MAC also refuses before
CAS. The original coordinated two-ingest
reproduction now leaves the first reconciliation disposition durable, refuses
the second event, and creates no sequence-two row. This remains an implementer-
produced correction requiring fresh independent review.

## Implemented closed member

The only positive member is an authenticated sequence-one initial paid unit,
followed by its admitted full-withdrawal control, followed by a newly collected
`invoice.payment_succeeded` payment for the exact contiguous sequence-two
catalogue period. The event is only a reconciliation trigger. Admission requires
two complete fixed-origin source passes through Invoice, Invoice line,
Subscription/item, Price, InvoicePayment, PaymentIntent, and captured Charge.

The canonical two-pass projection contains only the accepted fields and
distinguishes absent optional list metadata from present metadata. Both Invoice
and InvoicePayment paid instants are independently checked against the signed
event instant and retained in the projection and durable receipt.

The repository protocol is explicitly version six. It preserves the immutable
sequence-one paid unit and full-withdrawal control, compare-and-swaps the exact
withdrawal head, and atomically installs one sequence-two restoration unit as
the paid and lifecycle head. Old version-five stores refuse without migration.
The independently held publication advances accepted and lifecycle heads
together only after exact durable readback.

The access boundary is the half-open interval
`[max(new_service_start, restoration_verified_at_utc), new_service_end)`. A
dedicated owner-bound fact, detached runtime admission, and paid-route guard
revalidate the current source and lifecycle before any of the existing 28 paid
routes is eligible. The existing 27 non-paid routes retain their prior controls.

## Deliberately unsupported

There is no same-period replacement, refund reversal, dispute reinstatement,
failed-renewal recovery, cancellation override, catch-up, gap, overlap,
proration, credit, discount, plan change, sequence-three restoration, provider
status authority, live provider access, production migration, or activation.
Exact replay can return only the already admitted result; it does not refetch,
resample time, extend access, or create a second grant.

## Verification evidence

All verification used synthetic signed events, injected retrieval, and
disposable local stores. No network, credential, provider, customer, or
production system was used.

The direct restoration suites cover catalogue periods and exact time
boundaries, trigger/signature/binding refusal, full fresh payment-chain refusal,
complete singleton/list semantics, two-pass changes and ignored unknown fields,
both paid instants, exact replay, changed bytes, identity reuse, cancelled and
withdrawn predecessors, sequence-three refusal, exact proposal/receipt key
sets, transaction rollback, committed-but-unpublished recovery, store
reopen/copy behavior, tamper, detached runtime admission, and every paid and
non-paid route boundary.

The affected W10/authentication/HICBC matrix completed with 3,073 behavioural
passes and five expected pre-existing package-specific dirty-worktree scope
sentinel failures before the final replay and hostile-source additions. The
complete repository run after those additions completed with 10,091 passes,
seven expected dirty-worktree scope sentinel failures, and two verifier-call-site
compatibility failures. Those two real compatibility failures were corrected;
the verifier plus restoration suites then passed 152 tests. The canonical
release gate subsequently reported 10,093 passing root tests and only the seven
dirty-worktree scope sentinel failures. Its other mandatory components passed:
13 artefact-correctness tests, 23 production-parity tests, the RW3 gate, and 138
Explore Your Options assurance tests. The gate correctly remained failed and
the candidate is not described as canonical-green.

The second corrected five direct restoration suites passed 77 tests, and the focused
accepted-behaviour/signature compatibility matrix passed 307 tests. Exact candidate
identities are recorded in the owning review handoff after the candidate is
frozen.

The complete repository suite after the first focused correction passed 10,094 tests
and seven subtests. Its only seven failures were the explicitly preserved
package-specific dirty-worktree scope sentinels; there were no behavioural,
signature, lifecycle, runtime, route, or compatibility failures.

After the second focused correction, the complete repository suite passed
10,097 tests and seven subtests. Its only seven failures remained the same
deliberate dirty-worktree scope sentinels.

After the third focused correction, the five direct restoration files passed
81 tests. The 879-test affected initial/renewal/cancellation/failure/withdrawal/
runtime/access/signature/authentication compatibility matrix passed. The full
W10 matrix passed 2,521 behavioural tests; its only five failures were the
pre-existing package-specific dirty-worktree scope sentinels. The focused
transaction and prior-correction regression selection passed seven tests, and the
coordinated synthetic race ended with no sequence-two successor.

## Residual boundaries for review

Fresh independent review should challenge the exact canonical source projection,
replay signature semantics, current-head/lifecycle-head atomicity, rollback and
publication uncertainty, version-six compatibility, exact-key enforcement,
route inventory, and the absence of any same-period or sequence-three path.
Deployment/provider validation, real credential custody, production storage and
migration, payment execution, activation, external evidence, and overall W10 or
launch completion remain outside this candidate.
