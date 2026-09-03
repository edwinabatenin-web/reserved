# HMRC Individual Tax 1.1 — transport-neutral source evidence

Observation date: **1 September 2026** (the existing authority capture; this
package performs no new HMRC reading). Status: **network-inert implementation
candidate, pending independent review**.

## Boundary

`reserved/providers/hmrc_individual_tax_source_evidence.py` consumes only an
exact, intact, observer-issued and fully revalidated successful
`IndividualTaxAnnualSummaryObservation` from the reviewed Individual Tax 1.1
contract. It emits a deeply immutable, redacted, transport-neutral evidence
bundle. The source contract and this translator are grounded only in:

- `docs/HMRC_INDIVIDUAL_TAX_1_1_ENDPOINT_EVIDENCE.md`;
- `docs/HMRC_INDIVIDUAL_TAX_1_1_CONTRACT_EVIDENCE.md`; and
- the current disabled literal contract.

The bundle preserves exactly:

- source API name `Individual Tax` and version `1.1`;
- the request-bound tax year;
- employment records in source order, including duplicates;
- each literal `employerPayeReference` and exact `taxTakenOffPay` value;
- pensions/benefits and refund/set-off values with exhaustive present/absent
  sets;
- safe unknown member names at every represented source layer, never their
  values;
- completeness exactly `UNVERIFIED`;
- a non-empty bounded opaque evidence/run reference;
- an exact aware `datetime` with built-in fixed-offset `timezone`; and
- optionally, a lowercase SHA-256 digest of a separately redacted artefact.

Exact built-in `int` and `Decimal` types are preserved. A Decimal's sign,
coefficient digits and exponent are not normalised, including negative zero.
An explicit zero remains different from an absent field. Empty employments and
omitted optional fields are valid shapes but remain `UNVERIFIED`; they do not
mean zero, complete or current.

`employerPayeReference`, including the literal `267/LS500`, is provider text
only. It is not an identity, join key, pension classification or cross-endpoint
association.

## Defensive validation

The public contract validator is a narrow callable whose genuine type,
constant, regex, primitive and complete nested-state checks are captured in
closure state. It has no function defaults, keyword defaults, writable
instance dictionary or `__wrapped__` seam. Successful observations are also
registered by identity with an immutable process-local, type-tagged exact
fingerprint when the observer creates them. The fingerprint records exact
instance-key types, string types, ordered tuples, set-member types, `int`
versus `Decimal`, and each Decimal's sign/digits/exponent representation.
Equality-equal mutation, unsupported low-level cloning and reconstruction
outside the observer boundary therefore fail closed.

The evidence builder captures that validator and all genuine result classes,
exact types, regex matchers, constants, Unicode classifier and validation
primitives in its own closure. It then independently checks the copied nested
state. Ordinary rebinding of module helpers, exported classes, constants,
`datetime`, `timezone`, `Decimal`, `int`, regex names or the public validator
does not change an already-bound builder. Direct constructors and
`dataclasses.replace` enforce the captured result invariants. Every public
result validates itself before copy, deepcopy or pickle reduction, and the
top-level bundle validates its complete nested graph before emitting serialized
state. Constructors and all reconstruction paths call closure-held validators
directly rather than dispatching through a mutable class method; the public
`_validate` methods are compatibility wrappers only, so rebinding them cannot
bypass enforcement. Rebinding a pickle-addressable class/rebuilder name causes
pickle to fail rather than selecting a substitute.

All errors and reprs are constant and non-echoing. The evidence bundle retains
no source observation, request object, UTR, raw/redacted request path, raw
payload, provider error message, credential, transport state or unknown value.
The optional digest is merely an integrity reference to a separately redacted
artefact: it neither proves provider authenticity nor approves retention of
that artefact. `collected_at` is caller-supplied collection metadata, not an
HMRC event time or currentness assertion.

The process-local issuance/fingerprint mechanism is mutation detection and
coherence evidence only. It is not durable attestation, authentication or a
security boundary against arbitrary trusted Python code capable of rewriting
closure cells, type dictionaries, interpreter state or the complete object and
registry graph. Distinct observer-issued request objects, including otherwise
identical same-tax-year requests, are distinguished by process-local identity
so substitution fails closed. Because the raw UTR is intentionally discarded
by the source contract, that distinction is not a durable UTR identity and this
package neither recreates nor retains the identifier.

## Explicit non-capabilities

This package performs no totals, aggregation, netting, refund/credit/liability
or cash/reserve inference; no currency, sign or rounding interpretation; no
identity, join, deduplication or precedence; no currentness or universal-zero
conclusion; and no canonical, PAYE, annual-tax or customer mapping.

It imports and exposes no HTTP client, OAuth/token/credential mechanism,
provider call, route, persistence, configuration, provider enablement,
production origin or network behaviour. HTTP 400, 401 and 404 observations are
all rejected, including `NOT_FOUND`; none becomes empty source evidence.

The module does not alter `ProviderSpec("hmrc")`, resolve access/rate-limit or
fraud-prevention-header questions, authorise a redaction/retention policy, or
provide sandbox/production execution evidence. Transport, persistence,
cross-endpoint association, canonical mapping, privacy/security/operations,
independent integration and activation remain separate gated work.
