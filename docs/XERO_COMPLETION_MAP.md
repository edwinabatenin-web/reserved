# Xero workstream completion map

Evidence cut-off: **1 September 2026**. Endpoint: a disabled Xero adapter that
can read reviewed invoice data into the provider-neutral accounting boundary,
with secure OAuth/tenant handling and launch evidence. This map does not enable
Xero or expand invoice semantics without official evidence.

| Slice | Minimum outcome | Dependency / sequencing | State |
|---|---|---|---|
| X-S1 | Network-inert OAuth, rotating token-set and organisation-selection contract | Supplied official facts plus existing callback/custody contracts | Locally integrated in the isolated integration history |
| X-S2 | Reviewer-readable invoice schema capture and pure fail-closed mapping into provider-neutral observations | Supplied official invoice facts and reviewed neutral v3 contracts | Uncommitted corrected candidate; independent re-review and checkpoint pending |
| X-S3 | Bounded HTTP adapter for token exchange/refresh, connections and paginated invoice reads | X-S1, X-S2, credentials and sandbox access; serial integration | Planned |
| X-S4 | Route/journey integration while preserving disabled-by-default exposure | Reviewed X-S3 and product/UX decision | Planned |
| X-S5 | Sandbox evidence, security/privacy/operations review, integrated regression and launch decision | X-S4, independent reviewer and release authority | Planned |

Progress denominator: **2 of 5 implementation slices implemented (40%); 1 of
5 independently reviewed; 1 of 5 locally integrated in the isolated integration
history; 0 of 5 launch-evidence-complete; not launch-ready.** X-S2 remains only
an uncommitted corrected candidate after addressing four independent-review
findings; re-review is still pending. Independent review is not integration or
launch assurance.

Dependencies genuinely external to this package are credentials/sandbox access,
product/UX decisions, independent review, and release authority. X-S2 now has
reviewer-readable supplied invoice evidence; X-S3 transport preparation may
proceed only in separately owned files after the applicable review gate; shared
contracts, the protected `xero.py`, routes, and enablement remain serial gates.

## Terminal Xero gate

Xero is complete only when all five slices are implemented and independently
reviewed; exact OAuth/tenant, invoice completeness/pagination, canonical
provenance and fail-closed tests pass; sandbox evidence demonstrates the
reviewed journey without credential leakage; security/privacy/operations and
customer-language evidence are accepted; the adapter remains disabled until an
explicit launch decision; and integrated full-suite/release assurance passes.
Only then may release authority mark Xero launch-ready.

Out of scope for X-S2: HTTP and retries, pagination execution/completeness,
credentials/custody, callback replay logic, routes/UI, deletion or revocation,
provider enablement, production data/calls, tax/payment decisions, merge,
release, and deployment. Immediate next action: independent re-review of the
exact four-path corrected X-S2 candidate followed by separately authorised
checkpointing. Do not commit this candidate without that authority.
