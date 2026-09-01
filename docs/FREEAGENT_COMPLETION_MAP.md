# FreeAgent workstream completion map

Evidence cut-off: 1 September 2026. This map declares the finite endpoint of
the October-target FreeAgent workstream and identifies the first slice, FA-S1,
which captures the current official read-only company, invoice-list and
pagination contract as a network-inert source validator. It does not expand
FreeAgent scope, alter Founder Decisions, enable the provider, access any
account, or establish launch readiness.

## Owned outcome

Deliver a disabled-first FreeAgent read-only adapter whose source facts are
taken verbatim from the current official FreeAgent developer documentation,
validated network-inert, then mapped into the provider-neutral canonical
accounting pipeline only where the source explicitly supports the mapping. Raw
provider assertions never become tax decisions, and the provider remains
disabled until the declared terminal gate is met.

Explicit out of scope: live HTTP adapter enablement in default configuration,
token custody implementation, customer account access, sandbox execution,
production deployment, canonical tax decisions derived from provider
assertions, and launch-readiness claims.

## Declared implementation slices

| Slice | Owned outcome | Status |
|---|---|---|
| FA-S1 | Official company, invoice-list and pagination contract captured as a network-inert source validator (exact API-origin + per-field schema validation) with synthetic tests | Implemented, independently reviewed and locally integrated on the isolated overnight branch at `76b9b6c`; not merged to main, pushed, deployed or enabled |
| FA-S2 | Encrypted token custody and authenticated user/company binding | Not started |
| FA-S3 | Disabled-first read-only adapter and canonical invoice mapping | Not started |
| FA-S4 | Pagination, refresh, disconnect, error and resilience handling | Network-inert contract sub-slice independently reviewed, checkpointed at `d096177b493ac341f15072e5d1daa5e5ca6d7c7f` and locally integrated; HTTP/secret-custody portions remain in FA-S2/FA-S3 |
| FA-S5 | Synthetic sandbox execution and independent evidence review | Not started |
| FA-S6 | Customer/target-environment integration and launch assurance | Not started |

FA-S1 is the only fully complete implementation slice. The network-inert
contract sub-slice of FA-S4 is also independently reviewed, checkpointed and
locally integrated; the remaining FA-S2, FA-S3, FA-S5 and FA-S6 work (and the
HTTP/secret-custody portions of FA-S4) are declared future slices, not open
items of that checkpoint.

## FA-S1 scope and checkpoint

FA-S1 owns only:

- `docs/FREEAGENT_INVOICE_CONTRACT_EVIDENCE.md` — dated evidence record
  separating documented fact from inference.
- `reserved/providers/accounting/freeagent_invoice_contract.py` — pure
  validators/constants for the company read, invoice list and pagination
  metadata, with exact `api.freeagent.com` origin validation and a per-field
  schema layer for every documented field; no HTTP client, credentials,
  storage, adapter enablement or tax decision.
- `tests/test_freeagent_invoice_contract.py` — synthetic positive and
  fail-closed tests for every encoded fact.
- `docs/FREEAGENT_COMPLETION_MAP.md` — this map.

FA-S1 does not touch `freeagent.py`, `freeagent_oauth_contract.py`, the shared
accounting contracts, normalisation, readiness/configuration, Founder Decisions
or Control Plane state.

## FA-S4 scope and checkpoint (network-inert contract sub-slice only)

This change owns only the network-inert FA-S4 contract sub-slice:

- `reserved/providers/accounting/freeagent_resilience.py` — pure
  pagination-decision, refresh-rotation-decision, connection-state,
  rate-limit and conservative error-classification functions over
  already-validated inputs; no HTTP client, credential access, secret storage,
  persistence, sleeping, retry loop, provider enablement, payment action or
  canonical accounting mapping. Pagination fails closed when a next page is
  claimed at the configured maximum page limit, and `old_reference` is a strict
  non-secret opaque identifier (never a token or a storage handle).
- `tests/test_freeagent_resilience.py` — synthetic positive, negative,
  adversarial and property tests.
- `docs/FREEAGENT_RESILIENCE_EVIDENCE.md` — dated evidence separating
  documented FreeAgent facts, existing Reserved invariants and bounded
  implementation inference.
- `docs/FREEAGENT_COMPLETION_MAP.md` — this map.

This sub-slice does **not** complete FA-S2 secret custody, FA-S3 HTTP/canonical
mapping, provider-side revocation, sandbox execution, customer integration,
security/privacy assurance, enablement or launch readiness. Those remain owned
by their declared slices. It does not touch `freeagent.py`, the shared
accounting contracts, normalisation, readiness/configuration, Founder Decisions
or Control Plane state.

## Dependencies and parallelism

| Item | Depends on | External dependency | Sequencing |
|---|---|---|---|
| FA-S1 | Already-captured OAuth contract (`freeagent_oauth_contract.py`) | Official FreeAgent documentation only | Complete and locally integrated on the isolated overnight branch at `76b9b6c`; not merged to main or activated |
| FA-S2 | FA-S1 identity facts | External key management decision | Sequential after FA-S1 review |
| FA-S3 | FA-S1 schema facts | None beyond FA-S1 | Sequential after FA-S2 binding |
| FA-S4 | FA-S1 pagination facts, existing OAuth contract (`freeagent_oauth_contract.py`), shared sync contracts | None | Network-inert contract sub-slice reviewed, checkpointed and locally integrated; full HTTP/secret-custody portion sequential after FA-S2/FA-S3 |
| FA-S5 | FA-S2/FA-S3/FA-S4 | Sandbox access and independent reviewer | After adapter slices |
| FA-S6 | FA-S5 | Customer/target environment and reviewer | Final gate |

Shared-file rule: FA-S1 may not edit the shared accounting contracts,
normalisation, `freeagent.py`, the OAuth contract, readiness/configuration or
Control Plane state. Later slices own those files under their own reviewed
changes.

## Terminal FreeAgent completion gate

FreeAgent is complete only when all of the following are true:

1. Official company, invoice-list and pagination facts are captured with source
   URL and observation date, and documented fact is separated from inference.
2. A network-inert validator origin-validates FreeAgent API identities and
   pagination links, rejects incompatible shapes for every documented field,
   and preserves missing/null/zero, exact identity, dates and amount
   representation.
3. Encrypted token custody and user/company binding are implemented and
   reviewed.
4. The read-only adapter maps only source-supported facts into the canonical
   pipeline and remains disabled in default configuration.
5. Pagination, refresh, disconnect, error and resilience handling follow the
   documented contract and fail closed.
6. Synthetic sandbox execution is independently evidence-reviewed.
7. Customer/target-environment integration and launch assurance are complete.
8. The FreeAgent provider is enabled only under explicit sandbox configuration
   after all prior gates pass.

Current gate position: items 1–2 are addressed by the independently reviewed,
locally integrated FA-S1 checkpoint. Item 5 is advanced only by the reviewed,
locally integrated network-inert FA-S4 contract sub-slice (pure
pagination/refresh/disconnect/error decisions); the HTTP and
secret-custody execution of item 5 remains with FA-S2/FA-S3. Items 3–4 and
6–8 are not started. This is 1 of 6 declared implementation slices complete
(17%), plus a network-inert FA-S4 sub-slice, and 2 of 8 terminal checks
addressed (with item 5 partially advanced, not closed). These are denominators,
not launch-readiness claims. The FA-S1 checkpoint has been assembled only onto
the isolated overnight integration branch; no merge to main, push, deployment,
credential change or enablement has occurred.

## Out of scope

FreeAgent does not own general UI, Self Assessment filing, autonomous payment
or allocation, production activation, professional tax advice, or the canonical
tax engine. Dependencies on token custody, key management and sandbox access
are separate workstreams and do not move their implementation into FreeAgent.

## Immediate action

Preserve FA-S1 and the FA-S4 network-inert contract sub-slice as independently
reviewed local integrations. The next declared slice is FA-S2 (encrypted token
custody and user/company binding); starting it requires its own bounded package,
authority and external custody decision.
