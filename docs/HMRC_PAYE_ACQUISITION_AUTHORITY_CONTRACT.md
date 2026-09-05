# HMRC PAYE acquisition-authority contract — prerequisite specification

Status: **prerequisite specification only; not implemented, independently
assured, integrated, provider-tested, enabled or launch-ready**.

Specification date: **5 September 2026**. Frozen source lineage:
`c54be2e103e39d0504022f19541c4bcfd3f3bff5`, tree
`61f3471d23c29354d3ee5477d41f9af9b00074d8`.

This document freezes the smallest deferred contract required between a future
authenticated HMRC acquisition producer and the accepted, network-inert PAYE
mapping-eligibility boundary. It is not product code, provider evidence, an
HMRC access claim, a canonical mapping, or authority to call, persist, enable
or activate any provider capability.

## 1. Existing authority and exact gap

The accepted local boundaries establish only the following:

- Individual Employment 1.2, Individual Income 1.2 and Individual Tax 1.1
  literal contracts validate documented request/response shapes and retain
  process-local request/observation coherence;
- their source-evidence builders preserve validated source values, tax year,
  caller-supplied opaque evidence references, caller-supplied collection times
  and optional digests of separately redacted artefacts; and
- `project_hmrc_paye_mapping_eligibility` validates a narrow one-record-per-
  source structural subset and returns
  `structurally_eligible_non_authoritative`, with mapping completeness and
  currentness `UNKNOWN`, every authority flag false, and no `PayeEvidence`.

None of the retained fields closes an authority gap:

- API names and versions are local contract constants, not proof of issuer;
- an evidence/run reference is caller-supplied opaque text, not a run receipt;
- `observed_at` and `collected_at` are caller-supplied retrieval metadata, not
  HMRC event, effective, reconciliation-completion or source-update times;
- an optional SHA-256 is an unkeyed integrity reference to a separately
  redacted artefact, not authentication or approval to retain that artefact;
- request correlation and observation issuance are process-local coherence,
  not authenticated transport or durable provenance;
- raw UTRs are deliberately discarded, and no shared subject or acquisition-
  run identity survives across all three source bundles;
- equal tax years prove only annual compatibility; and
- equal `employerPayeReference` values, employer names, item positions or
  cardinality do not prove a unique employment or a cross-endpoint join.

The future producer must therefore establish authority before this contract
can be implemented. No current source/request/evidence field may be promoted
to substitute for that producer.

## 2. Deferred public operation

The deferred public operation is conceptually:

`bind_hmrc_paye_acquisition_authority(envelope, /)`

It must accept exactly one positional-only input and no keyword, default,
variadic or conversion input. The input must be the exact producer-issued
`AuthenticatedHMRCPayeAcquisitionEnvelope` type owned by a separately reviewed
authenticated acquisition boundary. Subclasses, protocols, mappings,
dataclasses, caller-built lookalikes and duck-typed objects must fail before
their attributes or protocol hooks are inspected.

This specification does not authorise creation of that producer or type. The
operation must not exist until the producer's exact authentication, consent,
owner/business membership, request construction, transport, response
correlation and redaction evidence has been accepted.

## 3. Exact envelope facts required

The envelope must be issued only after the producer has established all of the
following from its own trusted state. None may be accepted as a caller-supplied
boolean or free-form assertion:

1. **Provider issuer** — the three responses were received from the verified
   HMRC environment through the reviewed transport, not merely parsed by the
   offline observation functions.
2. **Authenticated consent** — the reads used the applicable user-restricted
   OAuth consent and exact scopes for Individual Employment 1.2, Individual
   Income 1.2 and Individual Tax 1.1.
3. **Owner and business context** — the acquisition is bound to the exact
   authenticated Reserved owner and the approved owner/business context under
   the separately reviewed membership rule. This specification does not
   choose that rule or relabel a PAYE employer as the customer's business.
4. **Same subject** — all three request receipts were constructed from the same
   validated subject/UTR within the trusted producer. The producer may retain
   an opaque subject binding, but neither the envelope's public projection nor
   this contract may retain a raw, masked, suffix, plaintext-hashed or otherwise
   enumerable UTR derivative.
5. **Same acquisition run** — all three request/response receipts belong to one
   immutable producer-issued run identity. Equal caller references or times do
   not satisfy this requirement.
6. **Request/response correlation** — each success observation is bound to the
   exact request actually sent and the response actually received for that
   operation. Parser invocation alone is insufficient.
7. **Annual context** — every request and observation carries the same exact
   consecutive ASCII `YYYY-YY` tax year.
8. **Exact operations** — one successful receipt each for:
   - `GET /individual-employment/sa/{utr}/annual-summary/{taxYear}`, Individual
     Employment `1.2`, scope `read:individual-employment`;
   - `GET /individual-income/sa/{utr}/annual-summary/{taxYear}`, Individual
     Income `1.2`, scope `read:individual-income`; and
   - `GET /individual-tax/sa/{utr}/annual-summary/{taxYear}`, Individual Tax
     `1.1`, scope `read:individual-tax`.

Each receipt must expose to this boundary only a captured, immutable authority
projection and the exact successful request-bound observation required by the
existing source builder. It must expose no access token, refresh token, client
secret, authorisation header, cookie, raw request path, raw UTR, raw payload or
provider error message.

The producer must supply a bounded opaque evidence reference, exact acquisition
time and any approved optional redacted-artefact digest to the existing source
builders. Those values remain provenance metadata; they acquire no independent
issuer, subject, run, currentness or completeness authority.

## 4. Source derivation and output

The deferred operation, not its caller, must invoke the exact accepted source-
evidence builders on the envelope's three validated observations and then
invoke the unchanged accepted structural mapper. Supplying preconstructed
source bundles is not an input path.

On success it returns one detached immutable tuple projection with exactly
these top-level entries in this order:

1. `schema_version = "hmrc_paye_acquisition_authority.v1"`;
2. `result_kind = "authenticated_acquisition_bound_noncanonical"`;
3. `environment` — the exact producer-projected HMRC environment;
4. `tax_year` — the shared validated annual context;
5. `owner_binding_reference` — a bounded opaque non-secret reference;
6. `business_binding_reference` — a bounded opaque non-secret reference under
   the separately approved membership semantics;
7. `subject_binding_reference` — a bounded opaque non-enumerable producer
   reference, never a UTR or UTR derivative;
8. `acquisition_run_reference` — the producer-issued opaque run reference;
9. `employment_source` — the mapper's exact detached employment branch;
10. `income_source` — the mapper's exact detached income branch;
11. `tax_source` — the mapper's exact detached tax branch;
12. `mapping_completeness = "UNKNOWN"`;
13. `currentness = "UNKNOWN"`; and
14. `authority_flags` — the exact ordered flags below.

The only flags this boundary may set true are:

- `provider_issuer_authority = true`;
- `same_subject_authority = true`;
- `acquisition_run_authority = true`;
- `request_response_binding_authority = true`;
- `owner_scope_authority = true`; and
- `transport_authority = true`.

Those true values report only what the accepted producer envelope has proved.
They must never be derived from source values, matching references, local
constants, timestamps, digests, narrative or mapper eligibility.

The following exact flags remain false in every successful result:

- `employment_identity_authority = false`;
- `currentness_authority = false`;
- `completeness_authority = false`;
- `persistence_authority = false`;
- `customer_evidence_authority = false`;
- `canonical_evidence_authority = false`;
- `production_authority = false`;
- `activation_authority = false`; and
- `paye_evidence_emitted = false`.

The operation must not construct, import, retain or return `PayeEvidence`, a
PAYE reconciliation, a future-pay fact or forecast, a customer result, an
annual-tax/cash input, a persistence record or a provider request. It performs
no employment join, aggregation, netting, deduplication, source precedence,
currentness, completeness, tax, refund, liability, forecast, reserve or
payment inference.

## 5. Exact refusal precedence

Every failure raises one fixed contract error carrying only the first
applicable category below. Validation must short-circuit in this exact order:

1. `invalid_acquisition_envelope` — wrong exact type, non-issued object,
   malformed immutable state or failed integrity validation;
2. `unsupported_provider_contract` — provider, environment, API, version,
   operation, method, path template, media type or scope differs from the exact
   supported set;
3. `unauthenticated_transport` — verified HMRC issuer, applicable consent or
   request/response transport evidence is absent or invalid;
4. `owner_scope_unproven` — authenticated owner, approved business context or
   owner-to-business membership is absent, mismatched or invalid;
5. `same_subject_unproven` — one producer-issued subject binding does not cover
   all three receipts;
6. `acquisition_run_unproven` — one producer-issued run binding does not cover
   all three receipts;
7. `request_response_binding_unproven` — any observation is not correlated to
   the exact sent request and received response;
8. `invalid_source_observation` — any exact accepted source-contract success
   validator refuses its observation;
9. source derivation and the accepted structural mapper, preserving its own
   existing precedence and exact categories:
   1. `invalid_source_bundle`;
   2. `unsupported_source_contract`;
   3. `unsupported_source_cardinality`;
   4. `invalid_tax_year`;
   5. `unsupported_schema_extension`;
   6. `unsupported_pension_benefit_or_refund_set_off`;
   7. `unsupported_state_pension_lump_sum`; and
   8. `unsupported_money`.

The envelope and receipt checks must validate exact shape, type and defensive
bounds before reading nested values. No error may echo or expose an owner,
business, subject, run, consent or evidence reference; UTR; employer name or
PAYE reference; amount; path; payload; provider message; digest; token; secret;
credential; header; cookie; or hostile object representation. No refusal may
be converted to empty, zero, partial success or a lower-evidence success.

## 6. Evidence hierarchy

Authority must be evaluated in this strict order:

1. the separately reviewed producer-issued authenticated acquisition envelope;
2. its exact transport-correlated request-bound success observations;
3. source bundles derived inside this operation through the exact accepted
   source builders; and
4. the accepted structural mapping-eligibility projection.

Lower layers may validate and preserve facts but cannot grant authority missing
from a higher layer. Documentation prose, array order, cardinality, equal tax
years, API-name constants, employer names, matching PAYE references, caller
evidence references, caller timestamps, optional digests and Test Support
fixture observations have zero authority to establish provider issuer, same
subject, same run, owner/business scope, authenticated transport, employment
identity, currentness, completeness, persistence, canonical evidence,
production or activation.

## 7. Deferred acceptance tests

An authorised implementation package must use exactly three paths: a new
contract module, its tests and its implementation-evidence record. The path
names and ownership must be approved after the producer exists; this
prerequisite does not reserve or authorise them.

Its local acceptance matrix must prove at least:

- exactly one positional-only exact envelope is accepted; every other call
  shape, subtype, lookalike and hostile protocol object refuses first;
- only producer-issued, integrity-valid envelopes are accepted; direct
  construction, low-level cloning, mutation, replacement, cross-process replay
  and reconstruction outside the documented producer boundary fail closed;
- provider/environment/API/version/operation/method/path/media/scope
  substitutions fail with the exact precedence above;
- missing/expired/mismatched consent and unauthenticated or uncorrelated
  transport refuse without inspecting later source values;
- cross-owner, cross-business, invalid-membership, cross-subject, cross-run,
  cross-tax-year, cross-request and cross-response transplants refuse;
- identical payloads under distinct requests/runs/subjects remain distinct and
  cannot be swapped;
- equal PAYE references cannot rescue a subject, run, request, response or
  owner mismatch, while unequal PAYE references cannot by themselves create or
  remove authority;
- equal caller evidence references, timestamps or digests cannot satisfy any
  authority check, and unequal values do not invent failure semantics;
- the exact existing source validators/builders and mapper are used, with the
  mapper's cardinality, year, schema-extension, excluded-category, State
  Pension marker and money refusals preserved in order;
- the output is immutable, detached, deterministic for its exact admitted
  projection and contains only the allowed true and required false flags;
- `mapping_completeness` and `currentness` remain `UNKNOWN` and no
  `PayeEvidence` is emitted even when all three PAYE references match;
- no raw, masked, suffix, plaintext-hashed or enumerable UTR derivative and no
  credential, token, authorisation header, cookie, raw path, payload or provider
  message appears in output, state, representation, errors, copy, serialization,
  logs or test artefacts; and
- static isolation excludes provider calls, network clients, environment or
  credential reads, routes, controllers, persistence, databases, reconciliation,
  forecasts, customer presentation, provider enablement and activation.

Synthetic unit fixtures may test only contract mechanics. They must never be
reported as provider, sandbox, target, customer or production evidence.

## 8. External, sandbox and target boundary

Implementation remains blocked until independent evidence accepts the exact
authenticated producer and its input facts. At minimum that evidence must cover
HMRC application/API access, the applicable consent and scopes, approved secret
and token custody, verified origin and TLS transport, request construction,
same-subject and same-run correlation, owner/business membership, response
correlation, redaction, replay/error/recovery behaviour and safe logging.

Sandbox acceptance must exercise the three exact read operations through the
real reviewed producer, including mismatched subject/run/request negative cases,
without recording credentials or personal identifiers. Test Support creates or
synthetic parser calls do not substitute for read-path acquisition evidence.

Target acceptance must separately prove the immutable target identity and
configuration, custody, authenticated owner/business boundary, negative and
recovery paths, privacy/security controls, monitoring and redacted evidence.
Sandbox success does not prove production access, currentness, completeness,
employment identity, persistence, customer fitness, production activation or
launch readiness.

Even after this acquisition contract is implemented, a later separately
authorised mapping decision must establish a non-ambiguous employment identity
or supported aggregate representation, source effective/currentness semantics,
completeness policy and canonical field mapping before `PayeEvidence` may be
constructed. Persistence, reconciliation/forecast orchestration, customer-safe
presentation, privacy/security/operations, provider enablement, release and
go-live remain independent gates.

## 9. Stopping state

The authorised work at this checkpoint is this one documentation path only.
There is no product implementation, test implementation, route, provider call,
credential access, persistence, canonical evidence, activation, completion-map
change or Founder Decision change. The specification requires fresh independent
review and grants no self-assurance or authority to begin the deferred contract
before its producer dependency is accepted.
