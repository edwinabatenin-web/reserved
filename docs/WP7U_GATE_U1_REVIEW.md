# WP7U Gate U1 contract-readiness review

Review date: 13 August 2026  
Scope: uncertainty/evidence contract readiness only  
Decision: **PASS**

This review does not assess or certify tax accuracy. It asks whether WP8 can freeze an integrated annual-position contract without losing, conflating or overstating evidence quality and estimate uncertainty.

## 1. Gate decision

Gate U1 now passes. The minimum implementation-independent contract is fixed sufficiently for WP8 to build and freeze a compatible integrated annual-position envelope without conflating arithmetic correctness, evidence quality and local heuristic scores.

The PASS is supported by:

- six supported-purpose enums matching the adopted standard;
- a common provenance-bearing evidence item;
- an expanded uncertainty item with known/uncharacterised state, affected components, customer action and determinable/indeterminable effect;
- a versioned estimate envelope carrying fitness, calculation status, point/range basis, supported and unsupported families, policy and limitation references, and prohibited uses;
- an adopted mapping artifact covering legacy confidence/status meanings, zero/unknown/omitted/not-applicable semantics, restricted pending-policy behavior, ownership, compatibility and migration boundaries;
- synthetic contract tests, including an end-to-end restricted reserve-guidance example and a negative test preventing restricted high-consequence outputs from omitting prohibited uses.

This is a contract-readiness PASS only. It is not a tax-accuracy decision, does not approve WP7 fixtures and does not claim that producers, storage, APIs or customer surfaces have completed migration.

## 2. Current-surface inventory and disposition

| Surface | Current semantics | WP7U purpose mapping | Disposition |
|---|---|---|---|
| Income Tax/NI engine outputs and dashboard “estimated liability” | Deterministic result from supplied profile; generic disclaimer | `personalised_estimate`; only `informational_rule` where using an explicit example | **Wrap** in estimate identity, supported scope, input/evidence assessment and calculation status. Do not add a numeric confidence score. |
| Dashboard/overview “how much to set aside” and “reserve estimate” | Can influence a financial action; inputs and omissions are not specifically surfaced | `reserve_guidance` | **Restrict pending conformance.** Do not imply safe-to-spend or complete reserve guidance until evidence/uncertainty requirements pass. |
| PAYE `Confidence.HIGH/MEDIUM/LOW/INCOMPLETE` | Evidence-source quality reduced for staleness/conflict; not tax certainty | `reconciliation` evidence quality | **Deprecate public name `confidence`.** Map temporarily to `evidence_quality_legacy`; replace with structured completeness, recency, conflict and representation assessments. |
| PAYE selected/considered evidence, conflicts, warnings and remaining-liability bounds | Useful provenance candidates and known-conflict effects | `reconciliation` | **Retain and extend.** Add stable evidence IDs, representation/effective-period/completeness, selection reason and range basis/completeness. |
| Transaction classifier confidence `0.0–1.0` | Rule/model classification score for transaction category | Supporting evidence classification, not an estimate-purpose status | **Keep locally; rename at boundaries** to `classification_confidence`. Never aggregate into estimate evidence quality or tax confidence. Unknown remains distinct. |
| Invoice matching confidence `0–100`, match status and review state | Heuristic strength and human confirmation workflow | Supporting identity/representation evidence | **Keep locally; rename at boundaries** to `match_confidence`. `confirmed` means a reviewed match, not confirmed tax treatment or complete evidence. |
| MTD statuses including `mtd_data_incomplete`, applicability, exemption and source IDs | Eligibility/readiness classification with explicit incompleteness | `eligibility_readiness` | **Retain and map.** `mtd_data_incomplete` maps to `insufficient_facts`; applicability/exemption must remain separate from operational sign-up readiness. |
| Optimise opportunity `available/incomplete/unavailable`, `missing_data` | Scenario availability and missing HICBC/profile facts | Usually `informational_rule`; `personalised_estimate` when based on saved facts | **Rename/map.** Do not use generic `incomplete`; emit affected facts, calculation status and excluded consequence. Scenario wording must not imply advice. |
| Provider readiness states | Configuration and sandbox-call safety, not estimate quality | Not an estimate purpose; operational dependency status | **Keep separate.** Never use as evidence quality. Propagate import absence/incompleteness only when it affects an estimate. |
| Import `CompletenessStatus` and `FitnessStatus` | Pagination/count evidence for a provider import | Evidence completeness supporting multiple purposes | **Retain.** Map manifests to evidence items; `UNVERIFIED` must produce a known uncertainty where material. |
| Profile `income_estimate` and projected income | User-entered or derived forecast without a shared forecast contract | `personalised_estimate` or `reserve_guidance`, depending on use | **Deprecate bare value.** Require observed/forecast distinction, horizon, method class, as-of date and forecast uncertainty/limitation. |
| HICBC opportunity and liability readiness | Calculated liability where facts exist; incomplete near threshold otherwise | `personalised_estimate` or `informational_rule` | **Map.** Missing Child Benefit/partner/ANI facts must produce explicit uncertainty or insufficient facts, not an omitted zero. |
| MTD, PAYE and candidate fixture statuses | Assurance/evidence labels such as review pending | Validation metadata, not customer estimate status | **Keep separate.** Never expose fixture approval as customer evidence quality or vice versa. |
| Generic UI disclaimers (“illustrative estimate”, “not guaranteed”) | Broad limitation with no affected input or determinable effect | All customer purposes | **Insufficient alone.** Retain as background wording, supplemented by structured, specific included/excluded/uncertain facts. |
| OpenAPI and persistence | No demonstrated common estimate/evidence/uncertainty envelope | All API-supported purposes | **Do not freeze.** Add or reserve the U1 contract fields and versioning before WP8 contract freeze. |

## 3. Standard-to-implementation mapping after remediation

| Standard concept | Current closest surface | Readiness |
|---|---|---|
| Supported-purpose classification | `EstimatePurpose` now defines all six standard purposes | **Ready.** The enum is consequence/purpose oriented and mapping documentation prohibits broader implications. |
| Purpose fitness | `PurposeFitness` plus envelope `prohibited_uses` | **Ready for U1.** Higher-consequence restricted outputs are structurally prevented from omitting prohibited uses. |
| Point/range/status | `EstimateEnvelope` and `CalculationStatus` | **Ready.** Point, ordered bounds, mandatory bound basis and seven common statuses are fixed. Range-completeness detail may be added compatibly during U2. |
| Evidence item | `EstimateEvidenceItem` | **Ready.** Stable identity, source/scope, tax/effective period, observation time, representation, completeness, recency, selection/reason, original value and unit are present. |
| Uncertainty item | `EstimateUncertainty` and `EstimateEffect` | **Ready for U1.** Known/uncharacterised state, affected components, customer action and effect are fixed. Severity/message and resolution workflow remain later-gate extensions. |
| Known zero/unknown/omitted | Normative mapping in `WP7U_CONTRACT_MAPPING.md` | **Ready.** Examples cover HICBC, MTD, FTCR and PAYE evidence. |
| Policy parameters/version | Envelope `policy_version`, limitations and prohibited uses; mapping's policy-pending behavior | **Ready.** Unresolved parameters can restrict purpose without blocking the base contract. |
| Included/unsupported families | Envelope `included_families` and `unsupported_families` | **Ready.** |
| Ownership/versioning | Mapping declares contract/policy owners and compatibility rule | **Ready.** |

## 4. Exact eight-item gate check

| # | Required item | Evidence | Result |
|---:|---|---|---|
| 1 | Adopt supported-purpose identity and prohibited-use semantics | Six `EstimatePurpose` values; `EstimateEnvelope.prohibited_uses`; mapping table | **PASS** |
| 2 | Define serialisable logical envelope | Versioned `EstimateEnvelope` with identity, rule/policy versions, status, point/bounds/basis, scope, evidence, uncertainties, limitations and restrictions | **PASS** |
| 3 | Define shared evidence-item minimum | `EstimateEvidenceItem` contains every minimum field and validates required identity/date data | **PASS** |
| 4 | Publish confidence deprecations | Mapping reserves `classification_confidence`, `match_confidence`, and `evidence_quality_legacy`; prohibits universal tax confidence | **PASS** |
| 5 | Map zero, unknown, omitted and not applicable | Dedicated normative mapping and four concrete examples | **PASS** |
| 6 | Record unresolved-policy restrictions | Versioned policy-pending behavior; higher-consequence envelope invariant requires prohibited uses when not adequate | **PASS** |
| 7 | Demonstrate end-to-end example | `test_versioned_envelope_preserves_evidence_scope_uncertainty_and_restriction` preserves evidence, unsupported FTCR, indeterminable omission and prohibited uses | **PASS by inspection** |
| 8 | Assign ownership and versioning | Contract `reserved-estimate-envelope/1.0`, evidence policy version, named owners and 1.x/major compatibility rule | **PASS** |

The test module could not be executed in this review environment because `pytest` is not installed. Its relevant construction and negative invariant tests were inspected directly. This is a verification limitation, not an identified contract defect; the normal test environment should execute them before relying on the broader suite status.

## 5. Items that do not block U1

The following belong to later purpose-specific gates and should not delay contract adoption:

- final quantitative materiality and recency thresholds, provided unresolved states restrict higher-consequence uses;
- final customer-facing wording and accessibility testing;
- every provider sandbox journey;
- full operational monitoring and residual-risk acceptance;
- completed WP7 fixture approval or a tax-accuracy PASS, which is a separate hard gate for supported tax calculation development;
- migration of every legacy internal score, provided boundary names and non-equivalence are fixed.

## 6. Proportional decision

**PASS for Gate U1.** All eight minimum contract-readiness conditions are met. WP8 may use and freeze the versioned envelope as its integration boundary, subject to the separate WP7 deterministic tax-accuracy gate.

Remaining work is correctly deferred:

- WP8 must actually emit the envelope rather than introduce an incompatible public shape;
- WP9–14 must migrate component provenance and uncertainty under U2;
- persistence and APIs must retain evidence IDs, selection reasons, policy versions and limitations before refreshable provider-backed purposes are enabled;
- final policy thresholds, customer wording, accessibility, operational monitoring and residual-risk acceptance remain later purpose-specific gates;
- legacy public `confidence` fields require migration/deprecation, although their non-equivalent meanings are now contractually fixed.

These are not U1 blockers because the adopted versioned boundary prevents silent semantic drift and restricts higher-consequence purposes while migrations remain incomplete.
