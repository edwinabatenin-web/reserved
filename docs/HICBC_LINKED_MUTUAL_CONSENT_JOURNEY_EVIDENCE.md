# HICBC linked mutual-permission journey — bounded implementation evidence

This document records the local implementation boundary for the Founder-approved
linked-HICBC mutual-permission journey. It is engineering evidence, not production
activation, legal approval, privacy assurance or a claim that linked evidence is
actionable.

## Authority and customer boundary

Invitation acceptance creates only a link. It never creates permission. Each
authenticated participant must separately submit the unchecked affirmative
control on `/v2/hicbc/link` after the page displays the exact four disclosures in
`FOUNDER_DECISIONS.md`.

The POST is protected by the global CSRF control. A short-lived opaque token is
issued with the form; only its hash is stored, bound to the exact active link,
permission cycle, authenticated participant, tax year and server-owned
`HICBC_NOTICE_VERSION`. The consent write validates that complete binding in the
same transaction as the current-link check and permission record. Stale-cycle,
cross-link, cross-user, cross-tax-year, expired or tampered replay therefore
fails closed. The customer status contains no partner identity, income,
financial detail, consent timestamp or lifecycle history.
The minimal page status and binding are produced in one database transaction.
Consequently, a concurrent unlink/re-link cannot render status from one cycle
while issuing a usable token for another. Link identity, permission cycle and
partner identity remain server-side and are not included in the rendered form.
Authenticated HICBC responses retain the global `no-store` policy and the entire
blueprint remains disabled unless `HICBC_ENABLED` is explicitly true.

## Current authority and durable history

Current cross-account calculation authority is deliberately fail closed:

- exactly one active HICBC link must exist for the participant and tax year;
- both participants must have a current, non-withdrawn permission row;
- both rows must match the authoritative notice version;
- lifecycle events are evidence only and cannot establish permission.

The permission cycle increments on re-link. Re-linking atomically invalidates any
legacy or current unwithdrawn rows before the link becomes usable, so both users
must consent again. Unlinking atomically invalidates current permission and records
the acting participant's withdrawal (where one existed) plus the unlink event.

Lifecycle events are bounded to consent, withdrawal, unlink and re-link, with
link identity, cycle, actor, timestamp and authoritative notice version.
Transition uniqueness includes the immutable notice version. Repeating the same
acceptance is idempotent, while each later authoritative notice acceptance in
the same cycle remains separately auditable. Account-deletion hooks continue to
remove the link and its cascading permission, form-binding and event history.

## Verification boundary

Focused tests cover invitation-only, one-sided and two-sided states; malformed
acknowledgement/version; authentication, CSRF, no-store and anti-probing controls;
stale-cycle/cross-context/tampered binding replay; idempotent and concurrent
retries; multiple notice-version acceptances; immediate revocation; re-link
non-revival; legacy unwithdrawn rows; multi-cycle event history; account deletion; and the
existing rule that profile-derived linked ANI remains partial, unconfirmed and
non-actionable.

The package does not activate HICBC, access a provider or production system,
change payment/filing behaviour, or satisfy the remaining privacy, retention,
security, customer-evidence and calculation-assurance gates.
