# Reserved West Initiative 001 — Final Summary
**Document reference:** RW-001-SUM
**Date:** 7 August 2026
**Status:** CLOSED

---

## Objectives

Reserved West Initiative 001 was a structured independent assurance programme for the Reserved freelance tax engine, conducted ahead of the October 2026 private beta launch.

Three objectives:

1. Verify that each supported tax component produces correct results in isolation.
2. Verify that components interact correctly across realistic, boundary, and extreme scenarios.
3. Establish a permanent regression framework to protect correct behaviour against future code changes.

---

## What was built

**Assurance framework** (`reserved_west/`): a bespoke four-stage gate model implemented in Python. Components include a reference calculator that does not share code with the production engine, scenario catalogues, a runner with formal gate-pass logic, and 32 output documents.

**Scenario coverage**: 292 scenarios across four stages, each with an independently calculated reference answer. Coverage spans every supported tax component and rate band, all key thresholds and both sides of each boundary, multi-component interaction, sequential invoice sequences, tolerance and stress inputs, mathematical invariants, rounding rules, and input validation.

**Automated regression suite**: 712 pytest tests (547 workspace, 165 engine-bundle) including permanent regression families for all three discovered defects, EL-001 through EL-003.

---

## Defects discovered and resolved

| Ref | Description | Severity | Engine version | Discovered |
|---|---|---|---|---|
| EL-001 | Incremental income tax applied the end-state Personal Allowance across the full invoice interval — wrong when PA changed mid-invoice (taper zone) | Medium → High | v2.0.0 | Stage 1 |
| EL-002 | CGT basic-rate limit sourced from a module-level constant rather than versioned tax configuration | Low | v1.0.0 | Pre-Stage 1 code review |
| EL-003 | Extended basic-rate limit not capped at the Additional Rate Threshold — pension contributions above £74,870 suppressed the 45% rate on all income above £125,140 | High | v2.0.1 | Stage 3 |

All three defects were found by the assurance process before production exposure, resolved, and permanently regression-pinned.

---

## Assurance methodology

**Gate model**: four stages with formal gate-pass criteria. No stage proceeds until the preceding gate passes. No gate passes while any Critical or High severity defect is open.

**Reference grounding**: every scenario carries an independently computed reference answer from a calculator that does not import the production engine. The runner automatically flags any variance above £0.01 as a FAIL.

**Outcome classification**: the runner distinguishes PASS, PASS_PENNY (≤1p tolerance), UNSUPPORTED_EXPECTED, FAIL, REGRESSION_EL001, REGRESSION_EL003, and ERROR. Each classification carries a defined gate consequence.

**Permanent regression families**: EL-001 and EL-003 are archived as permanent families. Any future variance in those zones is immediately gate-blocking regardless of severity at the time.

---

## Final evidence base

| Measure | Count |
|---|---|
| Assurance scenarios | 292 |
| Automated tests — workspace | 547 |
| Automated tests — engine bundle | 165 |
| Automated tests — combined | 712 |
| Defects discovered | 3 |
| Defects resolved | 3 |
| Defects open at closure | 0 |
| Gate failures | 0 |
| Scenarios: FAIL or REGRESSION | 0 |

---

## Lessons learned

**1. Incremental calculations are the highest-risk pattern.** EL-001 arose because the engine assumed that the Personal Allowance was constant across an invoice interval. The correct approach — computing full tax at the end position and subtracting full tax at the start position — is now the permanent engine architecture. Any future refactor that reintroduces interval-based assumptions must be treated as a potential EL-001 regression.

**2. Threshold caps require explicit code enforcement.** EL-003 arose because the extended basic-rate limit (`BRL + pension`) had no cap at the Additional Rate Threshold. When the extended limit exceeded ART, the 45% band was silently absorbed into the 20% slice. Every variable that must not exceed a physical threshold needs that cap enforced in code, not assumed by callers.

**3. Reference calculators must not share code with the engine under test.** The Reserved West reference calculator was written specifically for the assurance programme and does not import the production engine. Agreement is therefore genuine rather than circular.

**4. Test and scenario counts must always be labelled with their run command.** An audit during Initiative 001 (RW-AUDIT-001) identified a combined count that had been misattributed as a workspace-only count. The corrected reporting convention requires workspace, bundle, combined, and scenario counts to be reported separately and explicitly.

---

## Overall outcome

**Reserved West Initiative 001 is complete and successful.**

All four gates passed. Three defects were discovered by the assurance process — not in production — and all were resolved before gate passage and permanently regression-pinned. The Reserved engine v2.0.1 is certified for the October 2026 private beta. The assurance framework, scenario catalogue, and regression suite remain active for future development cycles.

---

*Reserved West Initiative 001 — CLOSED — 7 August 2026*
