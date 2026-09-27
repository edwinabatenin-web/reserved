# W10 local verified-initial-payment panel

Candidate for independent review, not acceptance, production activation,
S6H completion or W10-S6 closure.

## Bounded request composition

Explicit `install_local_billing_initial_paid_view` installs a disabled-by-
default, non-production context supplier on the existing authenticated
`GET /v2/plans` route and template. It registers no route and performs no
payment or access action.

The supplier requires independent authenticated membership and an opaque live
exact-UTC paid fact. That fact reauthenticates one and only one durable initial-
payment receipt, with no successor, lifecycle control or reconciliation
conflict. The receipt and live fact jointly bind owner, account, subscription,
approved plan, verification time, paid-period start, access start and exclusive
paid-through end. Membership, live fact identity, projection and conflict state
are rechecked before fixed copy enters the template.

The copy confirms only that the initial payment was verified for the exact
plan and states its verified paid-period bounds. It expressly does not confirm
automatic renewal or any future payment. It does not reuse S6H's automatic-
renewal copy and does not treat Checkout `pending` or
`recorded_pending_reconciliation` as a verified payment state.

Missing, stale, changed, conflicting, cross-owner, ended, non-initial or
controlled lifecycle evidence, production, absent installation or route
ambiguity yields no panel. Receipt/fact identities, source objects and provider
material never enter the template.

This is local executable evidence only. It does not initiate payment, change or
grant access, promise renewal, contact a provider, adjudicate refund or
cancellation, notify a customer, deploy, activate or release. S6G and S6H remain
separate accepted detached components; this panel does not claim either is
complete as an integrated journey. W10-S6 and the October subscription-billing
blocker remain open.
