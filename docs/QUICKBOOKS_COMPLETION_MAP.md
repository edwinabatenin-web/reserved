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
| Q-S4 | Evidence-backed, network-inert QuickBooks CompanyInfo and Invoice observation contract, without canonical interpretation | Independently reviewed, checkpointed, and integrated at `e293656ced558ff1d0bb8cc04203995fcaf5e355` |
| Q-S5 | Provider-to-canonical invoice/payment adapter with provenance, pagination/incremental-sync semantics, tax decisions, and adversarial fixtures | Unimplemented |
| Q-S6 | End-to-end sandbox evidence, operational monitoring/recovery, privacy/security review, independent assurance, deliberate enablement, and launch decision | Unimplemented |

“Implemented” means code exists in its bounded slice. “Independently reviewed”
requires a separate review outcome. “Integrated” requires deliberate adoption
by protected application boundaries. “Launch-ready” requires all slices,
operational and sandbox evidence, security/privacy assurance, and explicit
enablement authority. None of those later labels follows from Q-S1 or the Q-S4
integration. Q-S4 observes payloads already retrieved by an authorised caller.
It does not substitute for Q-S2 transport/custody, Q-S3 callback and route
integration, Q-S5 canonical normalisation, or Q-S6 sandbox/activation.

The Q-S4 evidence is recorded in
`docs/QUICKBOOKS_QS4_OBSERVATION_EVIDENCE.md`. It supplies immutable source
evidence bound to Q-S1 identity but grants no authority to query Intuit,
perform HTTP, read or store credentials, make ownership/accounting/tax/payment
decisions, parse response envelopes, or enable QuickBooks. It observes direct
entity payloads already retrieved by an authorised caller. Q-S2, Q-S3, Q-S5,
and Q-S6 remain open.

The dated official-facts package in `docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md`
is pre-Q-S5 evidence, not a new implementation or launch slice. It grants no
network, credential, production, sandbox, enablement, or deployment authority;
all existing activation gates remain unchanged.
