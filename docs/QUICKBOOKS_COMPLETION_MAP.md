# QuickBooks Online completion map

Status: bounded planning map. QuickBooks remains disabled. Q-S1 and Q-S4 are
independently reviewed, checkpointed, and integrated in the local integration
lineage. Q-S4 is integrated at commit
`e293656ced558ff1d0bb8cc04203995fcaf5e355`. Neither state makes the provider
launch-ready or exercises enablement authority.

The finite endpoint for this provider is a deliberately enabled, monitored,
reversible QuickBooks Online connection and canonical accounting ingestion
path whose OAuth, custody, company ownership, provider observations,
normalisation, operational failure handling, and launch evidence have each
passed independent review.

| Slice | Bounded outcome | Current state |
|---|---|---|
| Q-S1 | Pure OAuth request, callback, rotating token-set, and user/realm/credential-reference contract | Independently reviewed, checkpointed, and integrated in the local integration lineage |
| Q-S2 | HTTP and secret-custody boundary for exchange, refresh, revocation, rotation persistence, and failure handling | Unimplemented |
| Q-S3 | Authenticated callback integration, one-time state lifecycle, realm ownership checks, reconnect/disconnect behaviour, and protected routes | Unimplemented |
| Q-S4 | Evidence-backed, network-inert QuickBooks CompanyInfo and Invoice observation contract, without canonical interpretation; uncommitted Payment/attestation prerequisite candidate | CompanyInfo/Invoice independently reviewed, checkpointed, and integrated at `e293656ced558ff1d0bb8cc04203995fcaf5e355`; compatible observation attestation and Payment extension awaiting independent review |
| Q-S5 | Provider-to-canonical invoice/payment adapter with provenance, pagination/incremental-sync semantics, tax decisions, and adversarial fixtures | Narrow Q-S5A single-line tax-exclusive invoice and single-allocation Payment adapter is locally checkpointed. Q-S5B bounded query/Invoice-CDC mechanics and honest completeness-classification candidate is implemented locally and awaiting independent review; snapshot isolation, continuous CDC, general ingestion, and activation remain unimplemented |
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

The bounded Q-S5B candidate is recorded in
`docs/QUICKBOOKS_QS5_SYNC_EVIDENCE.md`. It validates already-retrieved query
page and Invoice CDC response mechanics while keeping canonical-ingestion
fitness, query snapshot stability, continuous CDC, and historical completeness
unverified. It adds no transport, credential, persistence, activation, or
launch authority.

The UK VAT contract-evidence boundary is recorded in
`docs/QUICKBOOKS_QS5_UK_VAT_CONTRACT_EVIDENCE.md`. Its disposition is:

```
Current official evidence supports the tax-field presence used by the existing conservative Q-S5A representation, but does not prove universal UK emission, exact v75 field history, or broader UK VAT semantics. Intuit's worked override example contains a percentage/arithmetic contradiction that Q-S5A correctly rejects. QBO-01 and all activation gates remain open.
```

This narrows nothing about Q-S5A and does not implement, integrate, launch, or
activate QuickBooks or VAT expansion. Q-S2, Q-S3, and Q-S6 remain open.
