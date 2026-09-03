# W10-S6D plan-selection preview evidence

## Boundary

W10-S6D adds authenticated, read-only selected-plan previews at:

- `/v2/plans/monthly`
- `/v2/plans/six_month`
- `/v2/plans/yearly`

The existing `/v2/plans` catalogue remains unchanged in its three exact prices,
VAT qualification and preview-only limitation. It adds three price-free links
in canonical catalogue order.

## Fail-closed derivation

The selection renderer revalidates the exact S6A presentation type, complete
ordered label set, exact VAT qualification, authority version and source
identity before selecting one label from an exact path-key allowlist. A valid
selection displays only that selected settled label and the exact VAT
qualification.

Malformed, case-changed, encoded or extra path input, presentation subtypes,
reconstructed or mutated presentations and helper rebinding all produce one
fixed value-free state: `Plan unavailable — review required.` Query parameters
are inert.

Because WSGI `PATH_INFO` is already decoded and raw-URI extension fields are
not guaranteed, a selection is accepted only when at least one of `RAW_URI` or
`REQUEST_URI` is present as an exact built-in string and its path before the
query exactly equals `/v2/plans/` plus the decoded canonical key. When both are
present, both paths must agree. Missing, non-string, subtype, percent-bearing,
mismatched or contradictory raw evidence fails closed; decoded text alone is
never treated as proof that the request used a canonical unencoded path.

The route and renderer hold security-critical collaborators in private closure
state, expose no callable defaults or keyword defaults, and remove the
authenticated route's unnecessary mutable `__wrapped__` pointer. Only the
internal fixed selection fragment is marked trusted; the page template has no
general `safe` filter.

## Exclusions and side effects

The preview contains no checkout, payment, portal, lifecycle, discount,
entitlement, provider action, price calculation, derived policy or operational
identifier. It performs no billing/domain persistence, database operation,
provider call or network action. The shared base template may initialise only
Flask's expected `csrf_token` in the authenticated session on first render.

Application-wide `/v2/` no-store and security headers remain in force. No
existing S6A, S6B or S6C contract or renderer file is changed.

The candidate remains uncommitted pending independent review.
