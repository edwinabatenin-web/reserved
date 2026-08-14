# Estimate Uncertainty & Evidence Quality Standard

Status: proposed cross-product standard. Implementation-independent. This standard seeks estimates and information that are trustworthy and adequate for a stated purpose. It does not require elimination of uncertainty or proof that no defect exists. Adoption of the core contract is required before the integrated annual-position contract is frozen; unresolved parameters may remain explicit where the supported purpose can still be met safely.

## 1. Placement in the work-package sequence

This is a cross-product work package between WP7 and WP8: **WP7U — Estimate Uncertainty & Evidence Quality**.

WP7U does not replace the WP7 tax-accuracy gate. The two gates answer different questions:

- WP7 establishes whether independently derived expected results can validate tax arithmetic.
- WP7U establishes how Reserved represents the quality, completeness and uncertainty of the facts supplied to that arithmetic, and how uncertainty flows into estimates and customer claims.

WP7U should begin while WP7 fixture approval is completing. Its **minimum contract gate** must pass before WP8 fixes the integrated annual-position data model. Purpose-specific evidence and presentation gates mature with the relevant WP9–14 and WP17 work; they need not all be completed before WP8 implementation begins. WP9 PAYE/student-loan reconciliation must conform to the adopted contract. WPs10–14 must emit compatible evidence and uncertainty records. WP17 owns accessible presentation against the contract, WP18 documents it, WP19 verifies it end to end and WP20 requires proportionate evidence that each launch purpose is supported.

This placement is necessary because current surfaces use incompatible meanings of confidence: PAYE confidence concerns evidence completeness/recency, transaction classification uses numeric model/rule confidence, matching uses scores, MTD uses explicit unknown states, and tax pages mainly use a generic estimate disclaimer. A single numeric “confidence in the tax estimate” would collapse distinct concepts and is prohibited.

## 2. Principles

1. **Arithmetic accuracy and input uncertainty are separate.** Correct arithmetic does not make incomplete facts complete.
2. **Known zero, unknown and omitted are distinct.** Missing data must never silently become zero, false, current or not applicable.
3. **Provenance is retained.** Selection or aggregation never destroys the candidate evidence or the reason it was included or excluded.
4. **No unconditional source precedence.** Evidence selection considers tax year, identity, representation, effective period, observation time, recency and completeness together.
5. **Uncertainty follows the estimate.** Material uncertainty is retained and communicated with its numerical effect where reasonably determinable.
6. **Ranges are bounded claims, not decoration.** A range must state what varies and must not imply that unmodelled uncertainty is inside it.
7. **Unsupported rules fail closed.** A known omission from the calculation is not represented as a low-confidence calculated value.
8. **Customer wording describes evidence quality, not certainty of the final tax bill.**
9. **Assurance is proportional to purpose and consequence.** The evidence required for an educational threshold indication is not identical to that required for a personalised reserve recommendation.
10. **Deterministic correctness is not traded away.** Where facts and supported statutory rules determine a result, uncertainty language must not excuse an arithmetic, ordering, threshold, rounding or tax-year defect.

## 2.1 Fitness for purpose

An estimate is fit only for an explicitly classified purpose. Fitness means that, for the intended user decision and foreseeable consequence:

- deterministic calculations inside the supported scope have passed their applicable independent correctness gate;
- material inputs are sufficiently complete, current and representative for that purpose, or their limitations are visible;
- known uncertainty is communicated with a reasonably determinable effect;
- unsupported or uncharacterised matters are not implied to be included;
- the presentation does not encourage a more consequential decision than the evidence supports;
- residual risk is documented, owned and accepted at the correct level.

Fitness is not a claim that the final tax authority calculation will be identical, that all user facts are true, or that no software defect remains.

### Supported-purpose classification

Every output surface and API field carrying an estimate must declare one of these purposes:

| Classification | Permitted use | Minimum assurance | Prohibited implication |
|---|---|---|---|
| `informational_rule` | Explain a threshold, rate, ordering rule or factual scenario | Correct sourced rule; applicable year/territory; explicit assumptions | Personalised liability or action recommendation |
| `personalised_estimate` | Show an indicative liability using supplied facts | Independently validated supported arithmetic; material input status; included/excluded scope | Final bill or guaranteed completeness |
| `reserve_guidance` | Inform how much a customer may consider setting aside | Personalised-estimate controls plus reconciled evidence quality, conservative handling and visible material uncertainty | Money is safe to spend or exact payment due |
| `reconciliation` | Compare annual liability with evidenced deductions/payments | Separate liability/evidence provenance; representation-aware no-double-counting; conflicts and timing disclosed | Confirmed HMRC balance, refund or collection position |
| `eligibility_readiness` | Indicate MTD or similar readiness state | All decisive eligibility facts known or explicit incomplete/unknown result | Filing completed, exemption granted or authority confirmation |
| `unsupported_for_decision` | Preserve partial information where a supported estimate cannot be made | Clear reason, available facts and next action | A usable point estimate or bounded range |

An output may serve more than one purpose only if it meets the highest applicable assurance level and the purposes are visibly distinguished.

## 3. Contract

Every customer-relevant estimate or reconciliation must be capable of returning the following logical record. Field names may vary by implementation, but meaning may not.

### 3.1 Estimate identity

- `estimate_id` and calculation timestamp;
- tax year and territorial/rule-set version;
- estimate purpose, such as annual liability, liability to date, readiness state or reconciliation;
- included liability families and explicit unsupported/deferred families;
- calculation evidence version or approved fixture/gate version where applicable.

### 3.2 Point, range and status

- `point_estimate`: the calculated value, or null where calculation is not supported;
- `lower_bound` and `upper_bound`: present only where a defensible bounded calculation exists;
- `bound_basis`: the specific uncertain facts varied to obtain the bounds;
- `range_completeness`: `complete_for_identified_uncertainties` or `partial`;
- `calculation_status`: one of:
  - `calculated` — required material facts are present and supported;
  - `calculated_with_material_uncertainty` — a point is shown but material evidence uncertainty remains;
  - `bounded_range` — defensible lower and upper results are available;
  - `insufficient_facts` — a required fact is unknown;
  - `unsupported_rule` — Reserved does not validate the required treatment;
  - `not_applicable` — applicability is affirmatively disproved;
  - `conflict_requires_review` — conflicting material facts cannot be resolved under approved policy.

An absent bound does not mean zero uncertainty. Where an effect cannot reasonably be determined, the contract must say `effect_not_determinable` and identify why.

### 3.3 Evidence item

Each material input must be traceable to one or more evidence items containing:

- stable evidence identifier;
- source kind and source-specific reference;
- subject and employment, business, property, loan or account identity where relevant;
- tax year, effective period and observation/import time;
- representation: `aggregate`, `entity_level`, `periodic`, `year_to_date`, `annual_final`, `forecast`, `manual_assertion` or a documented extension;
- value and unit;
- completeness state: `complete_for_purpose`, `partial`, `unknown` or `not_applicable`;
- recency state evaluated under the applicable policy;
- selection state and reason: selected, aggregated, superseded, excluded to prevent double counting, outside period, incompatible representation or unresolved conflict;
- original value retained even when it is not selected.

Evidence provenance is an audit record. It must not be overwritten when a connection refreshes or a user supplies a different document.

### 3.4 Uncertainty item

Each identified uncertainty has:

- stable uncertainty identifier;
- category: `missing`, `stale`, `conflicting`, `partial`, `forecast`, `classification`, `identity_match`, `representation`, `unsupported_treatment`, `policy_dependent` or `external_timing`;
- affected input and downstream estimate components;
- whether it is **known** or **uncharacterised**;
- materiality status and rationale;
- numerical effect: exact delta, lower/upper delta, alternative results or `effect_not_determinable`;
- required action and whether the customer can resolve it;
- customer message key and severity;
- resolution state and provenance of the resolution.

**Known uncertainty** means Reserved can name the missing, stale, conflicting or omitted fact and explain its effect or why the effect cannot be bounded. **Uncharacterised uncertainty** means risk remains outside the supported model—for example treaty-dependent foreign tax relief. It must be disclosed as an excluded limitation and must never be implied to fall within a displayed range.

## 4. Materiality

Materiality determines escalation and communication, not whether evidence is retained.

### Safe default

Until founder thresholds are adopted, treat an uncertainty as material when any of the following applies:

- it may change applicability, liability family, tax band, allowance, taper, charge percentage, loan plan, MTD state or supported/unsupported status;
- it may change a displayed amount but its maximum effect is not defensibly bounded below the product's display precision;
- it creates a conflict between direct evidence sources;
- it changes whether money is described as deducted, paid, overpaid, refundable or still to set aside;
- it prevents a required provenance or representation match.

This conservative default is safe because it escalates rather than suppresses uncertainty. It does not decide customer notification thresholds or permit a misleading point estimate.

Once quantitative thresholds are approved, materiality must be tested against both an absolute amount and a percentage of the relevant displayed amount, with override rules for status/boundary changes. A small monetary delta can still be qualitatively material.

Materiality is purpose-relative. An uncertainty may be immaterial to an informational illustration but material to reserve guidance or reconciliation. A threshold must never suppress an uncertainty that could change applicability, supported status, customer action, or the meaning of paid, deducted, refundable or outstanding.

## 5. Required behaviour by uncertainty type

### Missing

- Do not substitute zero unless zero is an explicitly justified conservative scenario and is labelled as such.
- If the missing fact is required for applicability or supported calculation, return `insufficient_facts`.
- If bounds are possible, identify the assumed alternatives and return a range.

### Stale

- Retain the evidence and its dates.
- Recency alone does not automatically exclude it or make another source win.
- Evaluate whether the represented period is still complete for the estimate purpose.
- Report the effect of using versus excluding or superseding it when reasonably determinable.

### Conflicting

- Preserve all candidates and the difference.
- Resolve only under an approved selection rule based on identity, representation, effective period, recency and completeness.
- If unresolved and material, return alternative results or a range and `conflict_requires_review`.
- Never silently select HMRC, a user document, a bank record or the newest timestamp solely because of source type or time.

### Omitted or unsupported treatment

- Name the omitted rule or liability and return `unsupported_rule` for that component.
- A total that excludes it must be labelled partial and must not be called a complete annual position.
- Examples include unvalidated Foreign Tax Credit Relief, treaty treatment and residential finance-cost reduction.

### Forecast or projection

- Separate observed-to-date facts from forecast assumptions.
- State the forecast horizon and method class.
- Do not describe a forecast range as capturing rule, evidence and behavioural uncertainty unless each is actually modelled.

## 6. Reconciliation and aggregation

Statutory liabilities, evidenced deductions/payments and estimated remaining amounts are separate concepts.

- Preserve liability by family.
- Preserve each payment or deduction with provenance, period and representation.
- Prevent aggregate evidence from being added to the entity-level observations it represents.
- Label subtraction as an estimated reconciliation.
- Do not infer refund availability from a negative arithmetic difference.
- Do not combine annual student-loan liability with payroll-period deductions without stating their different bases.
- A combined amount may be calculated internally for validation, but customer presentation requires the approved aggregation decision and must retain the component lines.

## 7. Customer communication

Every materially uncertain estimate must answer, in plain language:

1. **What is this?** The tax year, period and estimate purpose.
2. **What is included?** Income, liability and evidence families used.
3. **What is uncertain or excluded?** Specific missing, stale, conflicting, forecast or unsupported facts.
4. **What effect could it have?** Exact difference, range, alternative results or a statement that the effect cannot currently be determined.
5. **What can the customer do?** Supply, refresh, confirm or review the relevant evidence.

Safe presentation defaults:

- use “estimate” and “estimated reconciliation,” not “tax bill,” “accurate,” “confirmed” or “safe to spend”;
- show component values and provenance before a combined total;
- use “evidence quality” for source fitness and completeness;
- do not show a universal percentage confidence in the tax result;
- ensure warnings are textually available, not communicated by colour alone;
- do not hide an uncertainty merely because the customer dismissed its notification.

## 8. Validation gates

### Gate U1 — Contract adoption, before WP8 contract freeze

- logical contract and status vocabulary adopted;
- known zero/unknown/omitted semantics agreed;
- provenance and representation taxonomy agreed;
- current confidence surfaces inventoried and mapped or deprecated;
- every planned output assigned a supported-purpose classification;
- open founder parameters explicitly recorded without implicit high-consequence production behavior.

U1 passes when the data contract can safely preserve and propagate uncertainty for WP8. It does not require final customer wording, every connector policy or all quantitative thresholds where conservative defaults and a limited purpose classification prevent overclaiming.

### Gate U2 — Component conformance, before each WP9–14 integration

- component emits evidence and uncertainty records;
- missing, stale, conflict, duplication and unsupported cases fail safely;
- numerical effects or inability to determine them are tested;
- no source receives unconditional precedence;
- component limitations are visible to downstream aggregation.

### Gate U3 — Independent expected-result assurance

- uncertainty fixtures are derived independently from production selection logic;
- statutory arithmetic fixtures remain separate from product-policy fixtures;
- policy fixtures cite the adopted decision/version;
- boundary cases cover known zero, unknown, stale, material conflict, partial range and unsupported rule;
- fixture authors do not approve their own expected outcomes.

### Gate U4 — Customer and accessibility validation, before WP20

- user testing confirms customers can distinguish liability, evidence, reconciliation and forecast;
- material uncertainty is understandable and actionable;
- ranges do not imply omitted risks are bounded;
- screen-reader and non-colour presentation is verified;
- claims and disclaimers agree across dashboard, settings, connections, API and documentation.

Validation depth is proportional to the supported purpose. Reserve guidance and reconciliation require direct comprehension testing of uncertainty and action consequences. Informational-rule outputs may use focused content/accessibility review where they cannot reasonably drive a financial action.

### Gate U5 — Operational evidence, WP19/WP20

- source refresh and conflict history preserve provenance;
- monitoring detects unknown enum/schema changes and increasing incomplete states;
- sandbox evidence covers delayed, missing, duplicate and conflicting sources;
- the final launch record lists unsupported treatments and unresolved material uncertainty.

Failure of a gate blocks the affected integrated/customer-facing estimate. It does not invalidate independently verified statutory arithmetic that remains correctly scoped and labelled.

### Stopping rule

Assurance for a supported purpose may stop when all of the following are true:

1. deterministic supported-scope correctness gates pass with no unresolved material discrepancy;
2. required purpose-specific scenarios, boundaries and evidence states pass;
3. no known uncertainty is both material to the purpose and silently omitted or misleadingly represented;
4. unsupported matters and uncharacterised uncertainty are disclosed without being implied inside a point or range;
5. remaining findings are either immaterial to the purpose, outside the declared scope, or mitigated by a safe fail-closed/limited-purpose behavior;
6. residual risks have an owner, rationale, review trigger and explicit acceptance;
7. further assurance effort is unlikely to change the fitness decision materially relative to its cost and consequence.

The stopping rule permits a reasoned PASS with residual risk. It does not permit PASS where a deterministic tax defect, material unexplained discrepancy, misleading customer claim or unsupported high-consequence use remains.

### Residual-risk acceptance

Each accepted residual risk must record:

- affected supported purpose and users;
- evidence and uncertainty category;
- plausible consequence and reasonably determinable magnitude/range;
- why current controls make the output adequate for purpose;
- excluded or prohibited uses;
- accountable owner and accepting authority;
- expiry or review trigger, such as rule change, source-schema change, discrepancy rate, customer harm signal or launch-scope expansion;
- monitoring or sampling evidence where applicable.

Safe acceptance authority is proportional:

- documentation owner for low-consequence wording or informational-rule residuals;
- product and domain owner for personalised-estimate limitations;
- founder or delegated accountable launch authority for reserve guidance, reconciliation, refund/overpayment implications or risks capable of materially changing customer action;
- no role may accept a known deterministic correctness defect as “uncertainty.” Such a defect must be fixed, excluded from supported scope or cause gate failure.

## 9. Founder decisions required

These decisions materially change customer outcomes or claims and cannot safely be inferred for higher-consequence purposes. They need not block lower-purpose work where the conservative defaults and purpose restrictions below are adequate:

1. quantitative materiality thresholds and any family-specific overrides;
2. evidence recency windows by source, representation and estimate purpose;
3. minimum completeness criteria for P60, P45, payslip, HMRC, accounting and bank evidence;
4. conflict tie-break rules and when the product shows a point, alternatives or a range;
5. customer-facing evidence-quality labels and warning severity vocabulary;
6. whether and when liability, deductions/payments and remaining position may be combined in presentation;
7. treatment and wording of apparent overpayments and potential refunds;
8. which forecast methods and range claims are acceptable for v1;
9. notification/escalation thresholds for material estimate changes.

## 10. Safe defaults that do not require founder approval

- preserve provenance and conflicting candidates;
- distinguish zero, unknown, omitted and not applicable;
- never give a source unconditional precedence;
- fail closed on missing applicability facts and unsupported rules;
- keep statutory liability separate from deductions and payments;
- label reconciliation and forecasts as estimates;
- disclose known limitations and effect-not-determinable states;
- use the conservative qualitative materiality rule in section 4 pending quantitative thresholds;
- expose source/effective dates and customer actions;
- prevent double counting of aggregate and component evidence;
- retain accessible warnings and audit history;
- keep policy validation fixtures separate from statutory accuracy fixtures.

These defaults permit continued implementation and assurance for `informational_rule`, limited `personalised_estimate` and fail-closed readiness outputs. They do not by themselves authorise customer-facing `reserve_guidance`, combined reconciliation, refund language or claims that a displayed range is comprehensive.

## 10.1 WP20 calibration

WP20 should not require proof of zero uncertainty or zero defects. For each launch purpose it should require:

- a passed deterministic correctness gate for the supported calculation scope;
- a purpose classification and evidence that its minimum assurance level is met;
- no open material finding that makes the purpose misleading or unsafe;
- a residual-risk register with explicit acceptance and review triggers;
- evidence that unsupported purposes are technically or textually prevented;
- operational monitoring proportionate to the likelihood and consequence of evidence degradation.

WP20 may approve some purposes while withholding others. For example, informational explanations and a bounded personalised estimate may launch while combined reconciliation or reserve guidance remains disabled. This is a scoped launch decision, not a partial claim that blocked purposes are validated.

## 11. Initial conformance impact

The following existing surfaces need mapping during WP7U rather than silent reuse:

- PAYE `high`, `medium` and `incomplete` confidence labels;
- transaction-classification numeric confidence;
- invoice matching scores and review states;
- MTD unknown/exempt/readiness statuses;
- tax-profile forecasts and declared income;
- PAYE, payroll deduction, bank and accounting evidence;
- generic dashboard disclaimers that do not identify specific material uncertainty;
- API schemas and persisted records that currently lack evidence representation, selection reason, uncertainty effect or provenance history.

The mapping exercise must not reinterpret existing scores as a probability that the tax estimate is correct.
