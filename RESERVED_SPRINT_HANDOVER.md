# Reserved sprint handover

Updated: 13 August 2026

## Executive outcome

The repository is safer and its scope is now materially more honest, but Reserved v1 is **not feature-complete or production-ready**. A material student-loan error and incorrect 2026/27 Child Benefit inputs were corrected. The public UI no longer offers the out-of-scope Capital Gains preview or claims independent validation that has not been demonstrated. Tax rules are centrally versioned more completely, and a monitoring boundary can flag discrepancies without silently changing calculations.

The preparation phase is adequately complete for handover to a new independent
reviewing agent. Remaining material gaps are explicit, bounded, fail closed
where applicable, or require external/runtime evidence. This is a sound
handover point, not an official audit, certification or launch approval.

## Completed

- Removed customer-facing “safe to spend” language while retaining a deprecated compatibility field internally.
- Corrected saved-profile resolution and clarified illustrative bank data.
- Added PAYE reconciliation, MTD readiness, provider-neutral money-movement and accounting-provider contract components with synthetic checks.
- Verified that relevant HMRC APIs exist and replaced the earlier “no HMRC API” assumption with a capability matrix.
- Recorded the founder-confirmed v1 scope and explicitly classified Scotland, CGT and full MTD filing as post-v1.
- Audited central 2026/27 rules; corrected Child Benefit, multiple-undergraduate-plan handling and HICBC statutory rounding; added dividend, savings and HICBC configuration.
- Added a read-only rule-change detector and controlled adoption process.
- Removed v1 CGT entry points and an unsupported independent-validation statement from customer surfaces.
- Removed the deprecated arithmetic remainder from active dashboard and invoice-allocation response contracts; the legacy allocation helper retains it only as an explicitly deprecated compatibility detail.
- Converted customer logout to a CSRF-protected POST and updated both navigation surfaces and regression coverage.
- Selected FreeAgent as the first accounting-adapter candidate while keeping it disabled until exact official contracts and synthetic sandbox evidence support implementation.

## Validation performed

- The full application suite is green: **995 tests pass** in an isolated temporary environment created from the repository's pinned requirements.
- This run exposed six stale expectations rather than six product defects: four repeated the superseded gross-band coordinate, one expected the pre-v3 rules label, and one expected an animated value as visible static text. Each was reconciled against the corrected behaviour before the green run.
- Reserved West enforcement, provider-boundary and launch-quality standalone checks also pass.

A green regression suite is not Reserved West accuracy validation. Of the 107 admitted fixtures, 104 are now independently approved; only three simultaneous-multiple-undergraduate annual-SA fixtures remain pending.

## Material work remaining

0. WP7 now has a **SCOPED PASS** for calculations covering at most one undergraduate plan plus optional PGL. The repaired methodology is fit and 104 of 107 admitted arithmetic fixtures are approved. Three simultaneous-multiple-undergraduate annual-SA candidates remain pending and excluded because explicit annual selection authority was not found; they contribute no accuracy evidence. Known and unknown unsupported plan combinations now produce no monetary total, allocation, reserve or set-aside, emit `unsupported_for_decision`/`NOT_DETERMINABLE` with provenance and prohibitions, and require HMRC or qualified-adviser verification. This is not approval of simultaneous-plan arithmetic.
0U. **WP7U Gate U1 has passed independent contract-readiness review.** The versioned envelope, common evidence item, purpose/fitness/status vocabulary, confidence deprecations, zero/unknown/omitted mapping, policy restrictions and ownership rules are fixed. Later purpose-specific conformance and presentation gates mature with WPs9–14 and WP17. U1 permits the compatible internal WP8 contract; it does not override WP7's promotion/customer-reliance gate.
1. Continue the isolated integrated annual-position calculation. The first approved-evidence tranche now covers dividends, savings, UK/foreign property pre-limitation treatment, Class 4 and sufficiently evidenced HICBC, including ordering and ANI. It is not customer-connected and withholds total liability where FTCR, residential finance costs or required facts are unsupported/incomplete.
2. Reconcile calculated student-loan liability with evidenced PAYE/self-assessment deductions rather than showing liability alone.
3. Validate PAYE, sole-trade, pension and multi-source interactions with genuinely independent fixtures and boundary cases.
4. Implement reviewed provider-specific adapters, then complete sandbox OAuth and synthetic end-to-end tests for HMRC, Yapily AIS, FreeAgent, Xero and QuickBooks. Credentials must remain in secret storage. Configuration alone now explicitly reports `configured_not_implemented` and cannot enable networking.
5. Complete Google and Apple authentication assurance if those sign-in methods remain launch scope.
6. Repeat the now-green full suite in the target Replit environment and complete manual security, accessibility and failure-path testing.
7. The customer-facing name for “Optimise” is “Explore your options” (resolved 15 August 2026). Founder decision (15 August 2026): v1 includes customer-authorised payment initiation (PIS) from the customer's current account to a designated account owned by that customer — no money moves without the customer's explicit approval and bank authentication, Reserved does not hold customer funds, and sweeping VRP/automatic transfers are post-v1. PIS remains conditional on acceptable Yapily commercials, consent/status handling, same-owner controls, security review and launch assurance.

## Reserved West Independence Standard

Adopt and enforce `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`: validation-critical fixtures must be independently derived, and shared calculation code or copied production logic between the engine and oracle is prohibited. Existing evidence with shared lineage is regression/consistency evidence only and must be regenerated before supporting an accuracy claim.

The first independent WP7 review and subsequent framework re-review are recorded in `docs/RESERVED_WEST_ASSURANCE_REVIEW.md`. The methodology is fit and the later founder-authorised scoped gate passes for at most one undergraduate plan plus optional PGL; the three simultaneous-plan arithmetic fixtures remain pending/excluded. The historical RW-001 certificate is superseded.

Remediation artifacts now include `docs/WP7_ASSURANCE_REMEDIATION_PLAN.md`, `docs/fixtures/WP7_FIXTURE_SCHEMA.json`, five integrity-locked RW3 packs, an explicit assurance-corpus allowlist and `reserved_west/literal_fixture_runner.py`. The runner enforces the published pack shapes, IDs, dates, source metadata and coherent approval state. Passing comparisons against review-pending fixtures are not independent validation until those fixtures receive separate approval. The HICBC defect record is in `docs/HICBC_ROUNDING_DEFECT.md`.

Formal review of the original 46 core fixtures found and corrected one 5p pension/additional-rate candidate error. Subsequent source review and deliberate split promoted the 43 supportable fixtures; three simultaneous-multiple-undergraduate annual-SA fixtures remain unchanged in a separate pending pack because direct annual selection authority is absent. See `docs/RW3_CORE_FORMAL_REVIEW.md` and `docs/ANNUAL_STUDENT_LOAN_SOURCE_AUTHORITY.md`.

Formal second-person review approved all 53 v1 pre-implementation fixtures and promoted that pack with a deliberate integrity-manifest update. The exact fixture decisions are in `docs/RW3_V1_PREIMPLEMENTATION_FORMAL_REVIEW.md`.

The first formal PAYE review rejected all six evidence fixtures. They were then remediated to preserve representation/completeness, conflicts, missing-versus-zero, apparent-overpayment and stale-period uncertainty. Fresh independent review approved the bounded policy propositions and promoted the pack. See `docs/RW3_PAYE_EVIDENCE_FORMAL_REVIEW.md`.

The initial Tranche H review held all three candidates. Subsequent official-source research, supplemental review and a separate deliberate admission step approved HMX-001 and HMX-002 within narrow pre-FTCR purposes. HMX-003 remains excluded because its provenance/presentation policy is unresolved. See `docs/TRANCHE_H_INDEPENDENT_ASSURANCE_REVIEW.md`, `docs/TRANCHE_H_SOURCE_AUTHORITY_NOTE.md` and `docs/ANNUAL_STUDENT_LOAN_SOURCE_AUTHORITY.md`.

The integrity-checked corpus assessment reports approval progress directly from pack metadata. The current position is 104 approved fixtures and three pending multiple-undergraduate annual-SA fixtures, with the unqualified arithmetic corpus `gate_ready=false`. The separate scoped product gate passes only because those cases are expressly unsupported-for-decision and fail closed; it does not promote them.

A fresh scoped-gate review refused to treat those three cases as an optional launch exclusion: simultaneous undergraduate-plan handling remains in founder-confirmed v1 scope. The legacy incremental calculator and the new WP9 reconciliation component now both fail closed for that combination; neither returns a partial or zero amount. WP9 safely supports approved Plan 2 plus postgraduate reconciliation internally, but fail-closed safety does not satisfy the unimplemented v1 capability. See `docs/WP7_SCOPED_GATE_REVIEW.md`.

The legacy incremental calculator and dashboard have now also been corrected to fail closed for simultaneous or unknown undergraduate-plan combinations. They withhold affected totals, allocation and reserve figures rather than returning zero, partial liability or retrying, and require external verification. This implements the founder-authorised bounded scope but does not approve the three pending arithmetic fixtures.

The WP9 component underwent repeated independent review and remediation of evidence-scope, conflict-range, provenance, timeline and mixed stale/fresh-effect defects. Definitive review now **PASSES** it for bounded internal 2026/27 Plan 2/PGL component reconciliation. It remains prohibited for customer combined balances, reserve guidance, filing, payment, refund and payroll-period use.

WP9 now also **PASSES WP7U Gate U2** through a disconnected per-component mapping into the shared evidence/uncertainty envelope. The mapping preserves complete structured income-basis and deduction provenance, configured recency, item-specific selection reasons, missing/stale/conflict/excess effects, bounds, policy and prohibitions. It emits no combined customer balance and does not expand the underlying Plan 2/PGL scope.

The integrated annual-position engine now independently **PASSES** for isolated internal calculation within its approved literal scope. The remediated composition boundary separately **PASSES** for bounded ephemeral internal linking while preserving producer evidence, ranges/effects, scope, rulesets and prohibitions without aggregating money. Neither pass authorises customer connection. Composition is not approved for persistence, serialization, API publication, the public WP8 contract freeze or use as the final EstimateEnvelope.

Technical non-exposure has independently passed: none of these internal components is imported or serialized by routes, services, templates, static assets or the OpenAPI inventory. After adversarial remediation and re-review, the strict internal snapshot format **PASSES** for lossless decoded ephemeral handoff only; it is not persistence/API approval. The legacy dashboard and Optimise surfaces remain separate engines and must not be described as inheriting integrated-position assurance.

Persistence remains deliberately disconnected. An isolation audit found no leakage into the database, models, routes, customer services or public contracts and added regression tripwires. A separate readiness review concluded **NOT READY FOR PERSISTENCE**: do not reuse the current `tax_calculations` stub or write snapshots to files, caches, queues or a database until a purpose-built, independently reviewed contract addresses ownership isolation, data minimisation, provenance and uncertainty, encryption/key custody, retention/deletion, migration, integrity and auditability.

Legacy dashboard and Optimise copy now explicitly states their limited model inputs and omitted families rather than implying an assured integrated annual position, exact split or recommendation. Snapshot semantic validation has also been strengthened after independent adversarial rejection and now passes for decoded ephemeral internal handoff only.

That semantic copy is now consistent across duplicate legacy/v2 dashboards, overview, tour, metadata, login/about/review, accessibility labels and service documentation. Snapshot limitation, typed-reference, status, prohibition and tax-year/ruleset bypasses are regression-tested and closed; persistence, API and customer use remain expressly unapproved.

## Founder decisions/actions

- Finalise the commercials, consent/status handling, same-owner destination controls, security review and launch assurance on which customer-authorised PIS remains conditional.
- The customer-facing label for “Optimise” is “Explore your options” (resolved 15 August 2026).
- No credentials need to be shared in chat. The five sandbox credentials already stored in Replit should be exercised only with synthetic accounts/data.
- The founder has approved the overarching evidence policy: HMRC has no unconditional precedence; selection uses recency, completeness, identity and representation; provenance and material uncertainty are preserved; evidence quality is not tax certainty. Operational materiality/recency/completeness thresholds and customer wording still require approval.
- No immediate founder input is needed for liability/deduction presentation. The safe v1 default is separate, provenance-bearing component lines; a combined customer total remains disabled until its compatibility, completeness, uncertainty and wording conditions are approved.

## External blockers

See `EXTERNAL_DEPENDENCIES.md`. Sandbox credentials appear to be available in Replit, but redirect URIs, enabled scopes/APIs and synthetic test tenants still need verification. Production access, real users, live bank/HMRC accounts, deployment and production credentials remain expressly outside this sprint.

The HMRC adapter is deliberately not implemented from partial local notes. Exact official endpoint paths/methods, OAuth scopes and lifecycle, media types, mandatory/fraud headers, schemas and error contracts must be captured first. The selected first journey is a synthetic Individual Employment 1.2 identity read for one tax year, followed separately by Income and Tax evidence.

The FreeAgent adapter is likewise deliberately disabled. Current official evidence now supports a network-inert OAuth success-path contract, including sandbox endpoints and core authorisation/code/refresh/token fields. Error/denial/revocation behaviour, secure custody, company identity, invoice-schema, payment/status and pagination semantics still require exact evidence before implementation or enablement. See `docs/FREEAGENT_ADAPTER_IMPLEMENTATION_DECISION.md`.

## 31 August 2026 assessment

The target is **possible but at significant risk**, with 19 calendar days remaining. It is credible only for a tightly controlled v1 if integrated tax work begins immediately, scope remains frozen, sandbox journeys work without prolonged provider review, and independent tax validation plus the full test suite receive sustained attention. A production-ready claim should not be tied to the date if material calculation discrepancies, missing multi-income interactions, security issues or provider approvals remain unresolved. The appropriate launch gate is evidence, not elapsed time.

Assurance is calibrated to responsible launch by supported purpose, not proof of
zero uncertainty or zero defects. A lower-consequence informational or qualified
estimate purpose may pass with owned residual risk while reconciliation or
reserve-guidance purposes remain disabled. Known deterministic tax defects still
fail the applicable gate and cannot be accepted as ordinary uncertainty.

## Key records

- `docs/V1_TAX_SCOPE.md`
- `docs/TAX_RULE_AUDIT_2026_27.md`
- `docs/TAX_RULE_MONITORING.md`
- `docs/ESTIMATE_UNCERTAINTY_STANDARD.md`
- `FOUNDER_DECISIONS.md`
- `EXTERNAL_DEPENDENCIES.md`
- `SPRINT_LOG.md`
