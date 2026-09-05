# QuickBooks Online completion map

Status: bounded planning map. QuickBooks remains disabled. Q-S1, Q-S4 and the
bounded Q-S5A/Q-S5B sub-slices are independently reviewed, checkpointed and
integrated in the local integration lineage. Q-S4 is integrated at commit
`e293656ced558ff1d0bb8cc04203995fcaf5e355`. None of those states makes the
provider launch-ready or exercises enablement authority.

The finite endpoint for this provider is a deliberately enabled, monitored,
reversible QuickBooks Online connection and canonical accounting ingestion
path whose OAuth, custody, company ownership, provider observations,
normalisation, operational failure handling, and launch evidence have each
passed independent review.

| Slice | Bounded outcome | Current state |
|---|---|---|
| Q-S1 | Pure OAuth request, callback, rotating token-set, and user/realm/credential-reference contract | Independently reviewed, checkpointed, and integrated in the local integration lineage |
| Q-S2 | HTTP and secret-custody boundary for exchange, refresh, revocation, rotation persistence, and failure handling | Full slice remains open; injected exchange/full-set atomic rotation component independently accepted at `bae7833982706848a210d36831a313288aefd773` and locally integrated at `c935df93f844af86eb820273d691827aac6e1e47`; no real custody or transport |
| Q-S3 | Authenticated callback integration, one-time state lifecycle, realm ownership checks, reconnect/disconnect behaviour, and protected routes | Full slice remains open; accepted/integrated injected component composes consumed state and explicit synthetic realm binding; no authenticated routes or live lifecycle |
| Q-S4 | Evidence-backed, network-inert QuickBooks CompanyInfo, Invoice and Payment observation contract, without canonical interpretation | Independently reviewed, checkpointed and locally integrated, including the compatible attestation and Payment extension at `110fb74dc1461ddb3bc20247177699219d3b0aef` |
| Q-S5 | Provider-to-canonical invoice/payment adapter with provenance, pagination/incremental-sync semantics, tax decisions, and adversarial fixtures | Narrow Q-S5A single-line tax-exclusive invoice/single-allocation Payment adapter and Q-S5B bounded query/Invoice-CDC evidence classifier are independently reviewed, checkpointed and locally integrated; snapshot isolation, continuous CDC, general ingestion, and activation remain unimplemented |
| Q-S6 | End-to-end sandbox evidence, operational monitoring/recovery, privacy/security review, independent assurance, deliberate enablement, and launch decision | Unimplemented |

“Implemented” means code exists in its bounded slice. “Independently reviewed”
requires a separate review outcome. “Integrated” requires deliberate adoption
by protected application boundaries. “Launch-ready” requires all slices,
operational and sandbox evidence, security/privacy assurance, and explicit
enablement authority. None of those later labels follows from Q-S1 or the Q-S4
integration. Q-S4 observes payloads already retrieved by an authorised caller.
It does not substitute for Q-S2 transport/custody, Q-S3 callback and route
integration, Q-S5 canonical normalisation, or Q-S6 sandbox/activation.

The Q-S4 evidence, including the bounded Payment observation prerequisite, is recorded in
`docs/QUICKBOOKS_QS4_OBSERVATION_EVIDENCE.md`. It supplies immutable source
evidence bound to Q-S1 identity but grants no authority to query Intuit,
perform HTTP, read or store credentials, make ownership/accounting/tax/payment,
allocation, or settlement decisions, parse response envelopes, or enable
QuickBooks. It observes direct
entity payloads already retrieved by an authorised caller. Q-S2, Q-S3, Q-S5,
and Q-S6 remain open.

The dated official-facts package in `docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md`
is pre-Q-S5 evidence, not a new implementation or launch slice. It grants no
network, credential, production, sandbox, enablement, or deployment authority;
all existing activation gates remain unchanged.

The narrow Q-S5A candidate and its fact/inference boundary are recorded in
`docs/QUICKBOOKS_QS5_ADAPTER_EVIDENCE.md`. It maps only the reviewed exact
single-line tax-exclusive Invoice and single-Invoice-link Payment shape. It
does not close QBO-01 UK VAT optionality, query/CDC completeness, Q-S2/Q-S3,
broader Q-S5 ingestion, or any Q-S6 activation gate.

The bounded Q-S5B checkpoint is recorded in
`docs/QUICKBOOKS_QS5_SYNC_EVIDENCE.md`. It validates already-retrieved query
page and Invoice CDC response mechanics while keeping canonical-ingestion
fitness, query snapshot stability, continuous CDC, and historical completeness
unverified. Its checkpoint and local integration add no transport, credential,
persistence, activation, or launch authority.

The UK VAT contract-evidence boundary is recorded in
`docs/QUICKBOOKS_QS5_UK_VAT_CONTRACT_EVIDENCE.md`. Its disposition is:

```
Current official evidence supports the tax-field presence used by the existing conservative Q-S5A representation, but does not prove universal UK emission, exact v75 field history, or broader UK VAT semantics. Intuit's worked override example contains a percentage/arithmetic contradiction that Q-S5A correctly rejects. QBO-01 and all activation gates remain open.
```

This narrows nothing about Q-S5A and does not implement, integrate, launch, or
activate QuickBooks or VAT expansion. Q-S2, Q-S3, and Q-S6 remain open.

## Historical injected acquisition candidate

`docs/QUICKBOOKS_READ_RUNTIME_EVIDENCE.md` records the four-path candidate on
immutable base `ea6a0fc217147471b5e247ffd9d9d220e93b37f6`. It executes synthetic
callback/exchange/full-set atomic refresh, bound CompanyInfo and Invoice query
requests through injected fixtures and the actual unchanged Q-S4/Q-S5B code.
Wire digests and optional provider pagination metadata remain distinct from
local request positions/counts. It ends at unverified query-mechanics evidence;
Q-S5B's canonical-ingestion prohibition is unchanged. It is not another
canonical-mapping acceptance, a live authenticated connection or custody proof.

At this original candidate freeze, different independent review and root
checkpoint/integration remained pending; subsequent acceptance is below.
No full slice or launch gate is closed. Q-S2/Q-S3/full Q-S5/Q-S6, QBO-01,
production privacy/security, provider validation and deliberate enablement
remain open. Existing Q-S1/Q-S4/Q-S5A/Q-S5B history above is unchanged.

## Accepted injected acquisition component — 5 September 2026

Source `bae7833982706848a210d36831a313288aefd773`, tree
`951d6a901d97285f16a97a0a0036ebb40aa2a05e`, is independently accepted and locally
integrated at `c935df93f844af86eb820273d691827aac6e1e47`. The owning record
`work/quickbooks-acquisition-checkpoint.md` in the parent workspace records the
initial aliasing finding, focused correction, independent 197 focused/2192
affected passes plus 18 mutation probes, and 2192 committed-source passes.
Detached binding/reference and complete token snapshots prevent dependency
aliases from rewriting expected facts; committed-but-refused writes make no
rollback claim. Historical runtime evidence is preserved, not silently edited.

The exact combined integration tree `ba8ad31114a400dc7f63873d4d0b4e84cb982686`
passed 9003 root, 13 artifact, 23 parity and 138 options tests, with RW3 true.
This is injected acquisition and Q-S4/Q-S5B unverified observation/mechanics
acceptance only. Canonical ingestion remains prohibited; no full slice, QBO-01,
custody, provider, privacy/security or activation gate is closed. October remains
not_ready with 18 blockers; the declared delivery denominator is unchanged.
