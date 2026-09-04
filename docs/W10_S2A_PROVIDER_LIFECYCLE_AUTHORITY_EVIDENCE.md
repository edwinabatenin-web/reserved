# W10-S2A provisional provider and lifecycle authority evidence

## Disposition

**Local implementation candidate — independent review and integration required.**

This package encodes the six billing-policy inputs settled by `FD-W10-002` and
`FD-W10-003`. It does not close W10-S2, activate a provider, grant entitlement,
calculate a recovery deadline, persist state or accept provider/legal terms.

## Authority and provenance

- Immutable source base: `9e8f94a9906f0c9d5c85b47223d20c34be499e1c`
  (tree `0351fc341ebe4220c173da064c4aaf8db143b394`).
- Source authority: corrected and independently reviewed `FD-W10-001` contract
  in `reserved/billing/contracts.py`.
- Added authority: `FD-W10-002` and `FD-W10-003`, both dated 4 September 2026.
- Exact S1 policy denominator: 15 keys.

The S2A runtime module does not trust mutable S1 module objects. Instead it binds
its provenance to the exact accepted S1 integration commit, authority version
and `contracts.py` SHA-256 above. The build/assurance test independently reads
that exact artifact, exercises the corrected S1 validate/project protocol and
compares S2A's six/nine partition to the exact ordered 15-key S1 denominator.
This keeps pre-import S1 helper/global rebinding out of the runtime authority
graph. It does not duplicate S1 plan prices or create provider price/product
identifiers. Changing S1 requires a reviewed provenance refresh; it cannot
silently alter S2A at runtime.

## Six settled policy keys

1. `billing_provider`: provisional disabled-first Stripe Billing, Stripe
   Checkout and Stripe Customer Portal; explicitly not Stripe Connect.
2. `renewal_behaviour`: automatic renewal for the selected paid plan.
3. `cancellation_timing`: future renewal stops; ordinary access continues to the
   end of the already-paid period.
4. `failed_payment_and_grace`: the first verified failed renewal enters the
   explicit `payment_recovery` state for exactly seven calendar days; duplicate
   or repeated failures cannot extend the period; unresolved expiry suspends
   ordinary access.
5. `entitlement_start_and_end`: verified successful initial payment is required
   to start access; verified, idempotent and order-safe recovery returns to paid;
   paid-period or unresolved-recovery expiry ends ordinary access.
6. `trial_and_free_access_if_applicable`: no October free trial or free tier.

`payment_recovery` is intentionally distinct from ordinary paid state. Provider
status labels and events remain observations for a later owner-bound reconciler,
never direct entitlement flags.

## Nine unresolved keys

- refunds;
- tax invoicing and additional VAT presentation;
- promotion/discount mechanics;
- partner-offer handling;
- exact paid-access surface;
- plan changes/proration;
- billing-account recovery;
- manual overrides; and
- post-settlement dispute/chargeback/reversal consequences.

The full S1 register therefore remains `policy_incomplete`; W10-S2 remains
partial and the stable eight-slice denominator remains unchanged at 0/8 complete.

## Integrity boundary

The public authority value is an opaque producer-issued handle. Direct
construction and unregistered `object.__new__` values fail validation. The
authoritative projection is rebuilt from closure-captured canonical state and
contains exact immutable built-in values only. Authoritative validate/project/
copy function objects retain their captured protocol even if public module names
or class copy/pickle metadata are rebound. Ordinary serialization is rejected;
an unregistered reconstructed handle fails validation.

The S1 source binding is an artifact/build-time provenance assertion rather than
a runtime claim that two mutable Python reexports authenticate one another.

This is a same-process authority-integrity boundary, not a defence against a
hostile process with arbitrary memory/code execution.

## Non-activation and residual gates

There are no provider IDs, account IDs, price IDs, credentials, SDK calls,
network endpoints, webhooks, routes, persistence writes or access grants in this
package. Provider terms/DPA/fees, Stripe documentation/sandbox evidence,
credentials, VAT/invoice treatment, the nine unresolved policies, datastore and
retention/custody design, target assurance and all production/payment/release
gates remain open.
