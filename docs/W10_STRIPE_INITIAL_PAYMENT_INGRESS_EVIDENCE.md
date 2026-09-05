# Local Stripe initial ingress — review candidate

Immutable base `5592bf804bd82f9db0b3d8b7e2fe437356c0b98d`, tree
`809d3841888851ba3e7b9a8a11a4fd0a5424549b`; branch
`astra/w10-stripe-initial-ingress`. No staging, checkpoint, integration or
activation is performed by this implementation candidate.

Owning authority is `work/w10-stripe-initial-ingress-authority.md`, including its
narrow ninth-path verifier-inventory amendment, SHA-256
`1baf5232c8e459b93d83ad856f73488846616147cc990dc26f53c7143e05eca1`.
Source specification SHA-256:
`3871de7c302053d679c8f9f87768567ac54b32bb13c36f77382909a3b038ec75`.
Founder FD-W10-001/002/003/004 SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
`2025-03-31.basil` is the authorised synthetic parser pin, not a provider setting
or latest-version claim. This package does not select the recovery anchor.

## Actual executable chain

Explicit `SyntheticInitialAuthority` binds the independently supplied synthetic
user/owner/account/subscription/customer/item/approved price and ordinary plan,
endpoint/account/version/test mode and concrete retrieval function. An explicit
pristine-eligibility assertion is required; empty storage alone cannot supply it.
The binding locks a freshly created physical store and immutable instance/epoch.
A process-local source-account/subscription tombstone prevents duplicate bindings
or resetting consumed/revoked scope under another owner, epoch or empty store.

`ingest_initial_payment` calls the unchanged raw-byte verifier before JSON parsing.
It rejects duplicate keys, nonfinite/fractional JSON numbers, oversized/nested
inputs and unsupported events. Source retrieval uses fixed paths and queries on
one origin, with exact request-object correlation. It does not follow response
URLs. Two complete bounded passes reconcile the invoice, line, subscription/item,
approved price, InvoicePayment, PaymentIntent and captured card Charge; changed
observations or binding refuse publication. Separate fetches are not claimed to
be a provider-atomic snapshot.

Only positive, completely paid, one-line/one-item/one-allocation ordinary GBP
initial invoices are supported. Customer/subscription/item/price, mode, version,
automatic collection, quantity, currency, amount, interval and period relationships
must match. Source paid/creation timestamps must be coherent with the signed
success event. Partial, out-of-band, credit-funded, discounted, prorated, disputed,
refunded, unlinked, uncaptured, missing or incomplete evidence cannot admit. Source
capture is not irreversible settlement or bank payout. No provider tax policy is
inferred from the payment objects.

One SQLite transaction commits the minimised receipt, exact fact, initial
disposition and head. Receipt/source event/verification completion timestamps
are separate. Access begins at `max(service_start, verification_completed_at)`
and ends at the exact exclusive purchased end, without date truncation. Distinct
fact, receipt and head identities remain separate. A domain-separated MAC under
an independently supplied receipt key authenticates the complete canonical
receipt; webhook and receipt key identities and effective HMAC-SHA256 key blocks
must differ across every rotation and receipt key. Effective blocks include SHA256
reduction above 64 bytes and zero padding to 64 bytes. Raw bodies,
complete objects, card details and keys are never durable fields.

The schema and implicit uniqueness indexes are checked exactly on open and use;
unexpected triggers, tables, altered constraints or duplicate units refuse.
Creation uses exclusive file creation; schema and metadata commit together.
No migration or legacy-store adoption occurs. Exact physical identity is bound
independently, so copying authentic bytes to another/replaced file is not a new
authorised store. Secondary/different-byte conflicts record a bounded minimised
MAC-protected reconciliation disposition while preserving the accepted unit.

After commit, a private operation-local publication step CASes the captured RAM
revision to the exact store/receipt/fact/head, then rechecks persisted state and
the live witness before issuing a fact. It is not an exported accepted-head
setter. SQLite and RAM are not one atomic domain: postcommit failure returns
`committed_but_unadmitted`; uncertain readback returns `commit_outcome_unknown`.
Only repository-observed successful rollback establishes a failed transaction as
known noncommit and permits the reserved retry. An arbitrary delegate exception
with an empty readback is unknown, not proof of noncommit. A retained post-CAS witness can reconstruct
only the same receipt. A postcommit/pre-CAS retry repeats source reconciliation
and preserves original verification time and head. It cannot refresh access.

Before the external commit attempt, a revision-checked RAM reservation consumes
pristine eligibility and fixes the exact canonical proposed receipt, but publishes
no accepted head or live fact. Postcommit CAS uses that reserved revision.
Precommit retry may write only the same reserved record; after a commit was
observed or its outcome is unknown, loss of the unit denies rather than recreating
a new initial record. Successful COMMIT is recorded before the repository readback;
readback loss therefore remains committed even before control returns to ingress.
This reservation covers the committed-before-readback and before-CAS row-loss paths without
pretending RAM/SQLite cross-domain atomicity or adding a durable witness store.

Every actual paid request resolves the current signed-session user, matches the
concrete independent membership, authenticates/rechecks the stored unit, admits
the opaque exact-UTC fact, and performs final witness/store checks. The last
successful witness check is the access-decision linearization point, not an
atomic promise about later arbitrary handler effects. Full immutable fact
meaning, including interval and canonical receipt, must match persisted authority
even if an attacker calls exposed private issuance symbols with altered input.
Forged/copied/stale handles cannot pass; revocation and clock rollback deny.

`install_local_exact_utc_paid_surface_access` uses the existing exact 28-endpoint
registration inventory and original decorated handlers. It has no arbitrary
allow callback and leaves the date-based installer unchanged. Plans/recovery,
public and support exclusions remain unchanged. Legacy dashboard/paid conflicts,
late/duplicate installation and production deny; auth, feature and CSRF controls
remain intact. It is never installed by default.

## Executed assurance and honest scope

Tests construct synthetic wire objects and independent HMAC vectors; the genuine
source reconciler, repository, witness and exact admission execute before actual
settings GET/token/POST/save. Monthly, six-month and annual cases use non-midnight
service bounds. All 28 paid endpoints have pre-handler denial tripwires without
admitted source. Existing local settings CSRF and old admission-race suites remain.

Dedicated tests challenge source identities/types/signatures, incomplete and
multiple payments, capture/refund/discount complications, changed retrieval,
event/secondary conflicts, delayed/future/expired/rollback timing, concurrent
claims, pre/postcommit and pre/post-CAS interruption, revoked/lost authority,
new-store reset, physical replacement, exact-schema corruption, altered receipt,
head/key changes, copied/altered live handles, reopen with retained witness and
request-time revocation. Publication-failure tests use tracing interruptions,
not successful admission substitutions.

This is executable local Flask assurance, not browser, human or provider evidence.
All DBs and users are disposable fixtures. Hostile arbitrary Python/module-state,
frame/closure introspection or wholesale code replacement is outside isolation
claims; private naming alone is not presented as an integrity boundary. Ordinary
public APIs, forged handles and changed stored evidence are explicitly challenged.
No secure memory erasure or production restart/custody assurance is claimed.

## Verification disposition

Commands use `PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m
pytest`, `-o addopts='' -q -p no:cacheprovider`.

- Final P1-corrected three new suites plus existing signature, local dashboard,
  paid-set and recovery suites: 410 passed in 5.64 seconds.
- Final P1-corrected affected matrix (same command/globs below): 2,338 passed and
  the same six unsuppressed historical dirty-path sentinel failures in 27.05 seconds;
  no errors/skips reported. Tracked and all seven new-file whitespace checks
  emitted no errors; the candidate remains confined to the nine authorised paths.
- Original reviewed freeze: focused 400 passed in 5.07 seconds; affected
  `tests/test_w10*.py tests/test_auth.py tests/test_auth_claims.py
  tests/test_ws7.py tests/test_hicbc*.py` reported 2,328 passed and six unsuppressed
  historical dirty-path sentinel failures in 26.19 seconds. Those results did
  not establish acceptance: independent review required the two corrections below.
- Before the root-authorised ninth-path amendment, the focused matrix reported
  388 passed and one historical verifier no-caller assertion failure; affected
  reported 2,316 passed and seven failures (that assertion plus six historical
  dirty-path sentinels). These failures were surfaced without suppression.
- The amendment preserves all verifier dependency/crypto/API checks and replaces
  only the obsolete global no-caller assertion with the single exact relative
  caller/import/call inventory. Hostile other paths, alias/star/absolute/dynamic
  import forms and extra references are tested; no directory exemption or import
  obfuscation is used.
- The six protected historical dirty-path sentinels remain unsuppressed:
  completion map, initial paid presentation, initial payment presentation,
  internal route hardening, paid-access guard and Q1/Q2 policy closure suites.
  They still require their older package-specific candidate paths.

Final nine-path hashes and combined diff are provided separately. No full
canonical or clean-checkpoint result is claimed by this candidate.

## Independent correction history

The original nine-path freeze received CORRECTION REQUIRED, two P2 findings:
COMMIT followed by row deletion at entry to the repository's readback incorrectly
reported noncommit and allowed recreation; raw-distinct HMAC keys admitted
trailing-zero and long-key/digest equivalence across signing/receipt or rotations.
The corrected tests trace the actual readback window, independently observe the
committed row with another SQLite connection, delete it (with and without a
readback exception), and require consumed state and refusal to recreate. A genuine
in-transaction precommit interruption proves rollback and exact reserved retry.
The old arbitrary-exception/empty-read test now requires unknown outcome and no
reset, rather than falsely asserting rollback. Existing postcommit/CAS cases remain.
Four independently HMAC-demonstrated equivalence negatives and two genuinely
distinct short/long rotation-plus-receipt positive cases exercise key validation.

That first correction froze with combined diff SHA-256
`2f7a3afd6ebec2275a6c5884297bb47c26f1ceb449bbab916d9aaf416bf602d9`,
409 focused passes and 2,337 affected passes plus the same six unsuppressed
historical dirty-path sentinels. A second independent review rejected that freeze
for one P1: a pre-COMMIT interruption combined with authorizer-denied ROLLBACK
left the SQLite connection in its unresolved transaction. Its own subsequent
read/retry could see the uncommitted inserted unit and admit an actual settings
request although an independent connection saw zero durable units.

The final correction permanently poisons and closes that repository instance
when rollback cannot establish known noncommit. No later public read, conflict
publication, commit retry, authorizer reset or rollback can restore trust in the
connection, and close remains safe and idempotent. The exact regression interrupts
on the COMMIT line after independently confirming INSERT visibility on the local
transaction, denies ROLLBACK through SQLite's authorizer, requires unknown/None,
consumed authority, refusal of exact retry and actual signed-session settings GET,
and independently confirms zero committed units. Successful rollback still
permits only the exact reserved receipt with its original verification time;
post-COMMIT readback/row-loss remains honestly committed-but-unadmitted. This is
fail-closed local transaction handling, not cross-domain atomicity.

Original combined diff SHA-256:
`929b28299b0d0cd5b1a7f5508551e7b0215d6ab7e083fe9332a453489d2af1e9`.
Original file SHA-256 identities (historical, not the corrected candidate):

```text
1926931b31984f08e6968cecce433276524b19778dc5538fc78b6ed359b6dd19  reserved/billing/local_stripe_initial_payment.py
8eb01d76154a6099bc7af1524d7c02d77073fa3cfa9b42b74d366312b174569d  reserved/billing/local_billing_provenance_repository.py
ccb7be39c31b6699adc42fe170cd46d13b43b82188f46569b2e665aa60bc4c03  reserved/billing/exact_utc_entitlement.py
27f70374c9287f8773331f84f21024482289fb668df4305ecf49f92c36b12691  reserved/billing/local_paid_surface_access.py
453459f4fcf830bf1dd16f1a01c709f984c020a1ea1ea13108cea2ceeb4800ca  tests/test_w10_stripe_initial_payment_ingress.py
cbafe8fe885bd2b025aeafc4da696a380e352c51f3b19e8d2bb821c461b41cb6  tests/test_w10_billing_provenance_repository.py
9e2f6e8f23fa0d93fecb802cdcdfe23888c1a0b7c246448da7b698099d8badbb  tests/test_w10_exact_utc_entitlement.py
6801a14b422f4bcf81c662d4e1a9f49372836370c90ab6466b5fc0ff21091d07  docs/W10_STRIPE_INITIAL_PAYMENT_INGRESS_EVIDENCE.md
789d790928ba6a4d8d1eea685fedafdab1f930656178cc0f3a73a25672e48960  tests/test_w10_stripe_signature_verifier.py
```

## Remaining mandatory gates

Initial-only means incomplete launch billing, not permission to remove discounts
or offers. Renewals, recovery, cancellation, verified full-withdrawal provider
classification/restoration and broader payment methods remain open. Local
revocation tests do not implement those provider lifecycle classifications.
Real membership/history completeness, provider validation, durable authority
recovery, credentials/custody, legal/finance, target environment and activation
remain gated. Losing the RAM witness denies, even with authentic receipts; there
is no durable witness reconstruction or second witness database. Root retains
independent-review, checkpoint and integration decisions.
