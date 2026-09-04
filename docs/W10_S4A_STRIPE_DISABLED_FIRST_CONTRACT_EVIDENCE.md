# W10-S4A disabled-first Stripe edge contract

**Evidence cut-off:** 4 September 2026  
**Candidate base:** `894218d1a0ca8dcd7d534f7d78d4140e69166e08`  
**Authority:** `FD-W10-002`; provisional Stripe Billing, Checkout and Customer
Portal baseline, disabled first. Stripe Connect is excluded.

The contract binds the accepted S2A authority on the integration lineage at
`5464bfac7bec6b3456d1895b2355a7e8ce86859b`, including the exact accepted
`provider_lifecycle_authority.py` SHA-256
`fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a`.

## Outcome

This slice records the smallest evidence-backed provider-edge contract that can
be built without provider credentials, network access, a webhook endpoint,
persistence, charging or activation. It is deliberately network-inert and
cannot create provider sessions, verify a signature, persist an event, grant
access or translate an observation into the W10-S3A entitlement state.

It establishes these boundaries for the later adapter:

- Checkout uses subscription mode, but completion is not payment or entitlement
  authority.
- Customer Portal is provisionally in scope for payment-method, invoice and
  subscription management. The target cancellation behaviour is end-of-paid
  period. Immediate cancellation, plan changes, proration and promotion codes
  remain disabled while their Reserved policies are unresolved.
- A webhook implementation must verify Stripe's signature against the raw
  request body, bind the API version, account owner and subscription, and use a
  durable atomic event inbox before reconciliation.
- Duplicate delivery and out-of-order delivery are normal provider behaviours.
  Event-ID deduplication and the provider-recommended object-ID plus event-type
  duplicate check are required.
- Provider event types and subscription statuses remain observations. They do
  not directly grant, continue, suspend or revoke Reserved access.
- Refund and post-settlement dispute/chargeback/reversal enumeration and access
  consequences remain explicitly unresolved rather than inferred from Stripe.

## Official provider evidence

- [Receive Stripe events](https://docs.stripe.com/webhooks): raw webhook/event
  model, duplicate-event handling, asynchronous processing, retries, and the
  absence of delivery-order guarantees.
- [Resolve webhook signature verification errors](https://docs.stripe.com/webhooks/signature):
  signature verification requires the unmodified raw request body, signature
  header and endpoint secret.
- [Subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks):
  asynchronous subscription/invoice events, payment failures, paid invoices and
  provider status transitions.
- [Subscription object](https://docs.stripe.com/api/subscriptions/object):
  provider statuses including `incomplete`, `active`, `past_due`, `canceled`,
  `unpaid`, `paused` and `incomplete_expired`.
- [Checkout subscriptions](https://docs.stripe.com/payments/checkout/build-subscriptions):
  Checkout subscription mode and the requirement to reconcile customer,
  subscription and status information.
- [Customer Portal](https://docs.stripe.com/customer-management): portal
  capabilities, temporary sessions and configurable subscription-management
  behaviour.

Official documentation describes Stripe's provider behaviour; it does not
settle Reserved's unresolved product, finance/tax, legal, security or
operational policies.

## Explicit exclusions

No Stripe SDK, API call, CLI, credential, webhook endpoint, raw payload,
signature check, database migration, event inbox, customer mapping, checkout
session, Portal session, charge, refund, dispute action, production setting or
provider dashboard change is present. No production or sandbox claim is made.

This component is **contract-only**. It is not a provider adapter, does not
complete W10-S4 and is not activation or launch evidence.
