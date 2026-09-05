# Xero workstream completion map

Evidence cut-off: **1 September 2026**. Endpoint: a disabled Xero adapter that
can read reviewed invoice data into the provider-neutral accounting boundary,
with secure OAuth/tenant handling and launch evidence. This map does not enable
Xero or expand invoice semantics without official evidence.

| Slice | Minimum outcome | Dependency / sequencing | State |
|---|---|---|---|
| X-S1 | Network-inert OAuth, rotating token-set and organisation-selection contract | Supplied official facts plus existing callback/custody contracts | Locally integrated in the isolated integration history |
| X-S2 | Reviewer-readable invoice schema capture and pure fail-closed mapping into provider-neutral observations | Supplied official invoice facts and reviewed neutral v3 contracts | Independently reviewed, checkpointed at `856abd9874134cf04e42f80565ec2f4ef80e9bf7`, and locally integrated |
| X-S3 | Bounded HTTP adapter for token exchange/refresh, connections and paginated invoice reads | X-S1, X-S2; explicit injected-test split below, with live custody/credentials/sandbox still gated | Injected executable candidate pending independent review; full X-S3 incomplete |
| X-S4 | Route/journey integration while preserving disabled-by-default exposure | Reviewed X-S3 and product/UX decision | Planned |
| X-S5 | Sandbox evidence, security/privacy/operations review, integrated regression and launch decision | X-S4, independent reviewer and release authority | Planned |

Progress denominator: **2 of 5 implementation slices implemented (40%); 2 of
5 independently reviewed; 2 of 5 locally integrated in the isolated integration
history; 0 of 5 launch-evidence-complete; not launch-ready.** Independent review
and local integration are not launch assurance.

Dependencies genuinely external to the remaining work are credentials/sandbox
access, product/UX decisions, independent review, and release authority. X-S2
has reviewer-readable supplied invoice evidence; X-S3 transport preparation may
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
release, and deployment. The original live X-S3 entry requirement remains:
credential, custody and sandbox gates are not inferred from X-S2 acceptance.
The separately authorised injected execution component below does not waive them.

## Injected X-S3 execution candidate — 5 September 2026

Authority `work/xero-read-runtime-authority.md` explicitly separates synthetic
execution against injected custody/binding fixtures from authenticated live
transport. W9-S2 permits adapter work against opaque references. Immutable base
`bd68ab48e4394b06470c20c6035384b6f78cd1a4`, tree
`2a8f3b6d0078c92f807fef8360440497a65cf146`; original X-S1/X-S2 history above
remains unchanged.

The new `xero_read_runtime.py` executes validated callback/token exchange/store,
complete refresh replacement, explicit auth-event/tenant/connection selection,
and bounded detailed invoice pages through accepted X-S2 and the unchanged
normaliser. It is not a new source mapper, live credential store or registered
provider. Its new tests execute actual request objects against synthetic
responses: 113 focused and 1,876 affected pass after the independent-review
operation-clock correction. One baseline now spans initial binding/state,
requests and post-store/finalization; the original passing candidate was not
acceptance, and corrected re-review remains pending. The new
`docs/XERO_READ_RUNTIME_EVIDENCE.md` records exact source facts, conservative
decoding/header restrictions, fixture trust, failure and snapshot limitations.
Only those three new files and this map belong to the candidate.

This is uncommitted implementation pending different independent review, not
X-S3 completion or acceptance. No real network, provider, credentials, default
database, routes, registry changes or enablement are supplied. Live custody,
authenticated owner/tenant membership, real response compatibility, sandbox,
X-S4 customer journeys and X-S5 privacy/security/target/launch gates remain open.
**2/5 implemented/reviewed/integrated and 0/5 launch-evidence-complete remain
unchanged.** Root alone owns checkpoint/integration and release decisions.
