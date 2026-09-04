# W10-S4C — owner-bound Customer Portal intent contract

## Result and authority boundary

This package is a pure, disabled-first structural contract under FD-W10-002
and FD-W10-003. It prepares no Stripe request and performs no authentication,
route, browser redirect, SDK/network call, credential access, portal-session
creation, database write, charge, refund, recovery action, entitlement change,
sandbox activation or production activation. It does not complete W10-S4 or
provide launch assurance.

Candidate base: `5f5a948891e1e812a5c74ff6c7266d153bb492fa`
(tree `639369d06a8da75e8318bec7933993c26e39ace6`).

The accepted sources are the current Founder Decisions, the integrated S2D
owner-bound billing-account recovery contract, the S4A disabled Stripe edge,
the S4B Checkout intent boundary and the S3A entitlement lifecycle. Their
exact hashes and accepted commits are embedded in the contract projection.

## Exact input and minimisation

The creator requires one exact positive `users.id` owner root and a complete
named set containing:

- a structural authentication context for that same owner;
- exactly one active owner-bound internal billing-account mapping observation;
- redacted evidence references for the mapping and provider customer/email
  observations, never raw provider identifiers or email addresses;
- the sole purpose `manage_existing_owner_bound_subscription_billing`;
- namespaced intent and idempotency identifiers;
- exact `timezone.utc` request, evaluation and expiry times;
- the sole logical return destination
  `reserved_billing_portal_return_reconciliation`; and
- an owner/account/mapping/intent-bound unused replay snapshot checked at the
  exact evaluation instant.

The mapping must be current, active and `exactly_one`. Missing, multiple,
conflicting, deleted, stale, future, cross-owner, replayed or substituted
mapping facts fail closed. The candidate expires after at most five minutes
and the request itself may be no more than five minutes old at evaluation; the
candidate never extends beyond authentication or mapping freshness. Raw idempotency material
is not retained; only its SHA-256 digest is projected. Secret- and
credential-shaped input is rejected.

Provider customer and email identifiers are observations, never
authentication, account-selection or entitlement authority. This package does
not accept their raw values: only redacted evidence references are accepted,
and embedded Stripe object identifiers (including case or separator disguises)
fail closed. It cannot enumerate accounts, choose among
accounts, transfer, merge, delegate or share a billing account.

The functions capture their ordinary validation helpers and use no mutable
admission registry. They do **not** claim producer integrity against a hostile
party that can rewrite Python function code or closure cells inside the same
interpreter. Such a claim is not technically enforceable here. This is why both
created and independently reconstructed outputs remain detached zero-authority
structural candidates; a later authenticated, isolated runtime boundary must
revalidate facts before any provider action.

## Return, replay and lifecycle

Only a logical return destination is retained; URLs are not accepted. A future
reviewed adapter must resolve that ID to one fixed HTTPS destination and must
provide CSRF and session-integrity controls. A browser return is zero authority
for payment, policy or entitlement.

The unused replay snapshot is structural input only. The candidate explicitly
says a future durable repository must atomically consume a single-use intent.
Repeated pure evaluation is deterministic but is not proof of persistence or
consumption.

The `payment_recovery` state remains distinct, lasts seven calendar days from
the first verified failed-renewal observation and is non-extendable by Portal
activity. Portal creation, use or return has no refund, cancellation-policy,
recovery-deadline or entitlement effect. Provider labels never become Reserved
access flags.

## Zero authority and residual gates

Every runtime, mapping-selection, persistence, SDK/network, credential, Portal
Session, route/return, charge, refund/policy, recovery, entitlement and
activation authority is fixed false. A structurally valid tuple therefore
remains a zero authority candidate.

Real Portal operation still requires a live authenticated-owner adapter, a
durable unique owner/account mapping, atomic intent consumption, reviewed
Stripe customer and Portal configuration, credential custody, fixed HTTPS
return resolution, sandbox negative/replay evidence, webhook and entitlement
reconciliation, target security/privacy/support/finance/tax/accessibility
evidence, and separate provider/production/release/go-live authority.

Q1 refunds, Q2 paid-surface boundaries and Q3 post-settlement consequences
remain open. This package neither answers them nor treats Customer Portal as
authority to change them.

No Stripe SDK or non-standard provider dependency is imported.
