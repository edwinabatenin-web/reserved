# W10 local admitted scheduled-cancellation panel

Candidate for independent review, not acceptance, activation or W10-S6 closure.

## Bounded request composition

Explicit `install_local_billing_cancellation_view` installs a non-production
context supplier on the existing authenticated `GET /v2/plans` route and
template. It registers no route or action, changes no entitlement, contacts no
provider, and is never installed by default.

The supplier starts from independent authenticated-user membership and an
opaque live scheduled-cancellation fact. That fact reauthenticates the exact
durable lifecycle head and its paid lineage before projecting the already
admitted owner, billing account, subscription, paid-period start, cancellation
verification time and exclusive paid-through end. Membership, fact identity
and projected bytes are resolved twice; a changed source or scope suppresses
the panel. A current runtime-entitlement projection alone cannot create the
claim.

Only when the same owner/account/subscription and full paid+cancellation control
remain current does the supplier invoke the unchanged S6F builder and validator.
The request instant must be exact UTC and lie from cancellation verification
through, but not including, the paid-period end. Fixed S6F copy alone enters the
template. Receipt/fact identities, provider material and authority flags do not.

Missing, stale, withdrawn, conflicting, cross-owner or changed evidence, an
ended boundary, production, route ambiguity, a late/duplicate install or any
dependency failure yields no panel. The page retains its existing prices,
purchasing-unavailable notice, authentication and no-store behavior.

## Verification boundary

Hostile Flask tests exercise actual signed local initial-payment and scheduled-
cancellation admission, authenticated requests, exact boundary instants,
membership/source changes, deletion, malformed clocks, production refusal and
a later full withdrawal invalidating the prior cancellation handle. Existing
scheduled-cancellation tests also bind the new projection to the unchanged
durable receipt.

This is local executable evidence only. It is not provider-backed production
status, customer/browser/human acceptance, cancellation authority, refund or
entitlement authority, notification, deployment, activation or release. W10-S6
and the October subscription-billing blocker remain open.
