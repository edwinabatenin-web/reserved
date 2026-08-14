# RW3 PAYE evidence fixture pack — formal independent re-review

Review date: 13 August 2026  
Reviewer: Codex independent second-person re-review stream  
Artifact: `docs/fixtures/RW3_PAYE_EVIDENCE_FIXTURES.json`  
Decision: **APPROVED — independent validation within bounded policy scope**

## Review boundary

All six remediated fixtures were freshly reviewed under `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`, `docs/HMRC_PAYE_RECONCILIATION.md` and `docs/ESTIMATE_UNCERTAINTY_STANDARD.md`. The review checked fixed evidence-policy propositions, provenance, representation, completeness, arithmetic, missing-versus-zero semantics, conflict handling, ranges, stale effects and apparent overpayment treatment.

This is not approval of statutory tax arithmetic, PAYE payroll calculation, API transport, the supplied annual-liability estimates, production wording, recency thresholds, materiality thresholds or refund entitlement. HMRC API documentation supports the existence and granularity of fields only. No production calculation helper, West reference calculator, Optimise helper or shared expected-result formula was used as an oracle, and the reconciliation implementation/tests were not used as correctness evidence or edited during this re-review.

## Policy basis applied

- HMRC has no unconditional precedence. Identity, representation, effective period, observation time, recency and completeness govern evidence use.
- Provenance-bearing candidates remain visible; a selection or exclusion requires a stated scope reason.
- Aggregate and entity evidence can be treated as overlapping only when the aggregate explicitly identifies the covered entities and period.
- Missing evidence is unknown, not observed zero. A zero-paid figure can appear only as a separately labelled conservative assumption.
- A material conflict without an approved multidimensional tie-break remains unresolved and produces alternatives or a bounded range.
- Stale evidence remains usable only within its represented period; unknown later-period effects must not be implied to fall inside a complete range.
- A negative reconciliation difference can be described only as an apparent overpayment, not a confirmed or available refund.
- Pending recency, materiality, label and warning-severity decisions may remain policy-pending when the fixture fails closed and makes no consequential decision by implication.

## Fixture decisions

| Fixture | Decision | Independent finding |
|---|---|---|
| RW3-PAYE-001 | Supportable | Two stable evidence IDs identify distinct employment-cumulative representations, each complete through 10 August. £1,800 + £700 = £2,500; £10,000 − £2,500 = £7,500. Selection and completeness are expressly bounded to the two declared employments and do not claim whole-person completeness. |
| RW3-PAYE-002 | Supportable | The aggregate explicitly covers the same two employment IDs and effective-through date as the entity observations. Excluding the two entity items prevents declared overlap from being counted twice; equivalence is established by representation metadata rather than equal totals alone. £6,000 − £2,000 = £4,000. No source-precedence rule is asserted. |
| RW3-PAYE-003 | Supportable | Both stable candidates and their £100 difference are retained. Recency does not choose a winner: tax paid and point remaining liability are null, status is `conflict_requires_review`, and the known alternatives are correctly £3,900 and £4,000. The range is expressly limited to the identified conflict. |
| RW3-PAYE-004 | Supportable | With no evidence, tax paid and reconciled remaining liability are null and status is `insufficient_facts`. The £0 paid/£6,000 remaining figures are separately and accurately labelled as a conservative assumption, with a partial range and indeterminable actual-deduction effect. |
| RW3-PAYE-005 | Supportable | The selected evidence is provenance-, representation-, period- and completeness-bearing. £1,200 − £1,000 = £200; remaining liability is correctly floored at £0. The £200 is separately labelled an apparent overpayment requiring review and expressly not a confirmed or available refund. |
| RW3-PAYE-006 | Supportable | 1 June to 12 August is 72 days. The sole evidence item is selected only for a conservative bounded reconciliation, not as current-to-date truth. £6,000 − £2,000 = £4,000 and the known use-versus-exclusion effect is £2,000. The range is partial, later deductions are indeterminable, and the precise recency threshold remains configuration-pending. |

## Prior rejection findings

The prior blockers are closed:

1. Stable IDs, representations, effective-through dates and bounded completeness facts are present.
2. Aggregate/entity overlap in PAYE-002 is explicit.
3. PAYE-003 no longer applies a newest-wins rule.
4. PAYE-004 preserves unknown separately from a conservative zero assumption.
5. PAYE-005 exposes the apparent £200 excess and prohibits refund interpretation.
6. PAYE-006 discloses partial coverage and indeterminable later-period effects.
7. Unsupported legacy confidence/evidence-quality labels were removed from expected results.
8. This fresh review is independent of the remediation implementation work.

## Limitations and residual policy decisions

The fixtures deliberately do not approve quantitative recency/materiality thresholds, source-specific completeness criteria beyond the synthetic facts, customer-facing quality labels, warning severity, conflict tie-breaks, refund treatment or evidence acquisition wording. Those remain founder/product decisions where consequential. This does not block these fixtures because each pending parameter is surfaced, conservatively bounded or causes a fail-closed status rather than an overclaim.

Approval establishes the six fixed propositions only. It does not establish that an evidence set contains every employment, that a provider record is current beyond its effective-through date, or that an annual liability estimate is correct.

## Pack verdict

**APPROVED FOR INDEPENDENT VALIDATION WITHIN BOUNDED POLICY SCOPE.** All six fixture literals and statuses are supportable under the founder-approved evidence and uncertainty principles. The pack and fixtures may be promoted to `independent_validation`, with review metadata and its integrity hash deliberately refreshed. No wider WP7 or tax-accuracy gate is decided by this approval.
