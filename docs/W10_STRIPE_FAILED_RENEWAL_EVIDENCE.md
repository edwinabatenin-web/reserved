# W10 Stripe failed-renewal runtime evidence

Status: uncommitted implementation candidate for fresh independent review. This
document is not activation, production, provider-validation or self-assurance.

## Frozen authority

- Base/HEAD before implementation: `f3b622df74569cb2ced5a3f11c1cae1235483e1c`
- Base tree: `a5cc557e447eaf0c57761e3bff14eaac6d55503c`
- Branch: `sol/w10-stripe-failed-renewal`
- Runtime authority SHA-256:
  `23f95e9688770643bcc67f72cda27110e1eda641a891ee0b2bc87b4c0154b20f`
- Accepted source-annex SHA-256:
  `f0234d3bfb10e6c09f66a5a7ee4dc3ab6665b8e665c60d452dc30acdb130edc4`
- Founder Decisions SHA-256:
  `78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`

No network, credential, provider, customer-data, route-registration, migration,
commit, merge, push, deployment or production operation is part of this package.

## Implemented boundary

The signed synthetic ingress admits only `invoice.payment_failed` for the exact
ordinary recurring successor period after an authenticated paid sequence one or
two. It verifies the fixed Basil version, signature/account/mode/owner bindings,
event and retrieved Invoice agreement, one exact non-prorated line, one bound
subscription item and approved price, explicit absence/empty predicates, and one
of three closed payment-artifact shapes:

1. no InvoicePayment and explicit-null Invoice/Subscription defaults;
2. one open zero-paid InvoicePayment and `requires_payment_method` PaymentIntent
   with a present-null `latest_charge`; or
3. the same unresolved PaymentIntent with one exact failed, unpaid, uncaptured,
   unrefunded and undisputed Charge.

Absent is never treated as null, booleans are never integers, and every other
PaymentIntent/Charge status, direct/multiple/mixed artifact, offer, discount,
proration, cancellation, period, identity, amount, pagination or retrieval shape
refuses or reconciles without moving the lifecycle head.

## Shared durable lifecycle

New disposable repositories use `reserved-paid-lineage-provenance/4`. Version
four preserves initial and successful-renewal paid units at sequences one and two
and adds one domain-separated `paid-lineage-lifecycle-scope/2` control row.
Scheduled cancellation and failed renewal contend for that same row/head in the
same SQLite transaction domain. Failed renewal is never a paid sequence three and
there is no parallel recovery store.

The failed-renewal transaction authenticates the source-owned proposal and exact
durable predecessor/head/replay state before sampling `failure_verified_at_utc`
at the lifecycle-admission boundary. The same instant is committed with the
receipt, determines both receipt/fact identities and fixes the exact `+7 days`
deadline. Exact replay returns the durable instant without resampling it. The
receipt, MAC and lifecycle-head identity also bind the exact artifact-shape tag,
each required/nullable artifact identity, source digest, paid predecessor,
physical store and authority epoch/revision. Old v1/v2/v3 metadata is rejected
without mutation or migration. Reopen succeeds only for the same physical file
under the retained live authority; copied/replaced stores, stale handles,
key/authority loss, tamper, rollback uncertainty and forked-process reuse fail
closed.

## Exact-instant runtime and access

The existing date-based `/1.0` runtime admission and paid-access guard remain
available with their accepted behavior. Failed renewal uses separate exact
versions:

- `reserved-owner-bound-billing-recovery-fact/2.0`
- `reserved-w10-runtime-entitlement-admission/2.0`
- `reserved-runtime-payment-recovery-decision/2.0`
- `reserved-paid-access-guard/2.0`

The v2 runtime carries authenticated durable source fact, paid predecessor and
shared lifecycle-head identities. It permits paid-surface access only on the
half-open interval
`failure_verified_at_utc <= evaluated_at_utc < recovery_deadline_exclusive_at_utc`,
where the deadline is exactly seven days after the arbitrary-second admission
instant. Existing v1 readers reject v2 handles and v2 readers reject v1 handles.
The concrete signed-session settings route is allowed before the deadline and
denied exactly at and after it; public plans remain outside the paid boundary.
The four v2 opaque-handle registries use identity-checked weakref callbacks:
collection removes only the exact stored weakref, never a newer reused-ID row,
while live runtime handles retain their source fact and admission authority.

## Replay and exclusions

Exact replay returns the original opaque fact, receipt, fact identity, lifecycle
head, authority revision, verification instant and deadline before, at or after
expiry, including after authorized close/reopen of the same physical store.
Replay never restores expired access or extends the deadline. Changed bytes,
later attempts, competing success/cancellation and stale/out-of-order evidence
reconcile or refuse on the same head.

A later successful retry/recovery, retry scheduling, communications, cancellation
policy, withdrawal, refund, dispute, support override, production custody and
activation remain explicitly unimplemented.

## Verification

All commands below were rerun from the frozen worktree after the corrections.

Direct failed-renewal matrix — `75 passed`:

```text
python3 -m pytest -o addopts='' -q tests/test_w10_stripe_failed_renewal.py tests/test_w10_billing_provenance_failed_renewal.py tests/test_w10_exact_utc_failed_renewal.py tests/test_w10_runtime_entitlement_failed_renewal.py
```

Independent-review regression probes — `3 passed`:

```text
python3 -m pytest -q tests/test_w10_billing_provenance_failed_renewal.py::test_two_day_delay_inside_commit_starts_full_atomic_recovery_interval tests/test_w10_runtime_entitlement_failed_renewal.py::test_repeated_allowed_and_expired_requests_release_all_v2_registry_rows tests/test_w10_runtime_entitlement_failed_renewal.py::test_v2_registry_callbacks_preserve_live_and_reused_identity_entries
```

Exact sixteen-suite focused matrix — `624 passed, 2 deselected`:

```text
python3 -m pytest -o addopts='' -q tests/test_w10_stripe_failed_renewal.py tests/test_w10_billing_provenance_failed_renewal.py tests/test_w10_exact_utc_failed_renewal.py tests/test_w10_runtime_entitlement_failed_renewal.py tests/test_w10_stripe_initial_payment_ingress.py tests/test_w10_stripe_successful_renewal.py tests/test_w10_billing_provenance_repository.py tests/test_w10_billing_provenance_successful_renewal.py tests/test_w10_stripe_cancellation.py tests/test_w10_billing_provenance_cancellation.py tests/test_w10_exact_utc_entitlement.py tests/test_w10_exact_utc_successful_renewal.py tests/test_w10_exact_utc_cancellation.py tests/test_w10_runtime_entitlement_admission.py tests/test_w10_paid_access_guard.py tests/test_w10_stripe_signature_verifier.py --deselect tests/test_w10_runtime_entitlement_admission.py::test_candidate_or_source_checkpoint_is_exactly_scoped_to_declared_base --deselect tests/test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base
```

The same focused command without deselection reported `624 passed, 2 failed`.
Those two historical package-local sentinels are:

```text
tests/test_w10_runtime_entitlement_admission.py::test_candidate_or_source_checkpoint_is_exactly_scoped_to_declared_base
tests/test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base
```

Natural affected matrix (no suppression) — `2,976 passed, 7 failed`:

```text
python3 -m pytest -q tests/test_w10_*.py tests/test_auth*.py tests/test_hicbc*.py
```

Every failure is a historical package-local dirty-path sentinel; the exact node
IDs are:

```text
tests/test_w10_completion_map.py::test_candidate_is_confined_to_the_authorised_map_and_dedicated_test
tests/test_w10_initial_paid_presentation.py::test_diff_is_confined_to_exact_package_paths
tests/test_w10_initial_payment_presentation.py::test_git_diff_is_limited_to_exact_authorised_paths
tests/test_w10_internal_route_hardening.py::test_candidate_changes_only_authorised_route_and_test_paths
tests/test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base
tests/test_w10_q1_q2_policy_closure.py::test_candidate_is_confined_to_three_new_non_colliding_paths
tests/test_w10_runtime_entitlement_admission.py::test_candidate_or_source_checkpoint_is_exactly_scoped_to_declared_base
```

Behavioral rerun with only those exact seven node IDs deselected — `2,976
passed, 7 deselected`:

```text
python3 -m pytest -o addopts='' -q tests/test_w10_*.py tests/test_auth*.py tests/test_hicbc*.py --deselect tests/test_w10_completion_map.py::test_candidate_is_confined_to_the_authorised_map_and_dedicated_test --deselect tests/test_w10_initial_paid_presentation.py::test_diff_is_confined_to_exact_package_paths --deselect tests/test_w10_initial_payment_presentation.py::test_git_diff_is_limited_to_exact_authorised_paths --deselect tests/test_w10_internal_route_hardening.py::test_candidate_changes_only_authorised_route_and_test_paths --deselect tests/test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base --deselect tests/test_w10_q1_q2_policy_closure.py::test_candidate_is_confined_to_three_new_non_colliding_paths --deselect tests/test_w10_runtime_entitlement_admission.py::test_candidate_or_source_checkpoint_is_exactly_scoped_to_declared_base
```

No behavior, integrity, boundary or compatibility failure is suppressed. The
natural dirty-path sentinels remain visible; only the exact seven IDs above were
deselected for the behavioral rerun.

Compilation of every changed Python path and the canonical whitespace/error
check both completed successfully:

```text
python3 -m py_compile reserved/billing/local_billing_provenance_repository.py reserved/billing/local_paid_surface_access.py reserved/billing/local_stripe_initial_payment.py reserved/billing/paid_access_guard.py reserved/billing/runtime_entitlement_admission.py tests/test_w10_billing_provenance_cancellation.py tests/test_w10_billing_provenance_successful_renewal.py tests/test_w10_exact_utc_cancellation.py tests/test_w10_paid_access_guard.py tests/test_w10_runtime_entitlement_admission.py tests/test_w10_billing_provenance_failed_renewal.py tests/test_w10_exact_utc_failed_renewal.py tests/test_w10_runtime_entitlement_failed_renewal.py tests/test_w10_stripe_failed_renewal.py
git diff --check
```
