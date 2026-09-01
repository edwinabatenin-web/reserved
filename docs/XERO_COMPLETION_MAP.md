# Xero workstream completion map

Evidence cut-off: **1 September 2026**. Endpoint: a disabled Xero adapter that
can read reviewed invoice data into the provider-neutral accounting boundary,
with secure OAuth/tenant handling and launch evidence. This map does not enable
Xero or expand invoice semantics without official evidence.

| Slice | Minimum outcome | Dependency / sequencing | State |
|---|---|---|---|
| X-S1 | Network-inert OAuth, rotating token-set and organisation-selection contract | Supplied official facts plus existing callback/custody contracts | Implemented and independently reviewed; uncommitted checkpoint candidate |
| X-S2 | Reviewer-readable invoice schema capture and pure fail-closed mapping into provider-neutral observations | Official accessible invoice schema; after X-S1, while HTTP work can prepare separately | Planned |
| X-S3 | Bounded HTTP adapter for token exchange/refresh, connections and paginated invoice reads | X-S1, X-S2, credentials and sandbox access; serial integration | Planned |
| X-S4 | Route/journey integration while preserving disabled-by-default exposure | Reviewed X-S3 and product/UX decision | Planned |
| X-S5 | Sandbox evidence, security/privacy/operations review, integrated regression and launch decision | X-S4, independent reviewer and release authority | Planned |

Progress denominator: **1 of 5 implementation slices implemented (20%); 1 of
5 independently reviewed; 0 of 5 integrated; 0 of 5 launch-evidence-complete;
not launch-ready.** Independent review is not integration or launch assurance.

Dependencies genuinely external to this package are reviewer-readable official
invoice schema evidence, credentials/sandbox access, product/UX decisions,
independent review, and release authority. X-S2 mapping and X-S3 transport
preparation may proceed in parallel only in separate owned files; shared
contracts, the protected `xero.py`, routes, and enablement remain serial gates.

## Terminal Xero gate

Xero is complete only when all five slices are implemented and independently
reviewed; exact OAuth/tenant, invoice completeness/pagination, canonical
provenance and fail-closed tests pass; sandbox evidence demonstrates the
reviewed journey without credential leakage; security/privacy/operations and
customer-language evidence are accepted; the adapter remains disabled until an
explicit launch decision; and integrated full-suite/release assurance passes.
Only then may release authority mark Xero launch-ready.

Out of scope for X-S1: invoice payload/schema mapping, HTTP and retries,
pagination, credentials/custody, callback replay logic, routes/UI, deletion or
revocation, provider enablement, production data/calls, merge, release, and
deployment. Immediate next action: preserve the independently reviewed X-S1
exact diff as an uncommitted checkpoint candidate; do not commit without
separate checkpoint authority. X-S2 must wait for reviewer-readable official
invoice schema evidence.
