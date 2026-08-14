# October Beta Readiness Assessment — Updated after Stage 2
**Assurance cycle:** Reserved West Initiative 001 (Stages 1 and 2)
**Engine version:** 2.0.0
**Date:** 2026-08-06

## Overall verdict
**🟡 Conditionally Ready (October Beta)**

The engine passes all 150 Stage 2 representative and boundary scenarios with zero variance. Combined with 30 Stage 1 scenarios, the engine is confirmed correct on 180 independent reference-grounded scenarios. EL-001 is fully resolved; no defects found. Stages 3 and 4 are recommended before a final readiness verdict, but based on Stage 1+2 evidence, the engine is fit for an October beta.

---

## Stage 1 + Stage 2 combined evidence

| Stage | Scenarios | Result |
|---|---|---|
| Stage 1 — Smoke tests | 30 | ✅ All PASS — Gate 1 passed |
| Stage 2 — Representative & Boundary | 150 | ✅ All PASS — Gate 2 passed |
| **Combined** | **180** | **✅ No defects across 180 scenarios** |

---

## Confirmed strengths (Stage 2)

1. **Income tax band arithmetic** — All boundaries (PA, BRL, ART) exact at 3 measurement points each.
2. **Personal Allowance taper (EL-001 resolved)** — All taper-zone scenarios PASS including:
   - 20 Stage 2 EL-001 zone scenarios: zero variance each
   - Stage 1: 3 EL-001 zone scenarios (RW-S1-012, 013, 014): zero variance
   - 16 permanent EL-001 regression tests: all passing
3. **Class 4 NI** — Confirmed at LPL, UPL, and all representative income levels.
4. **Student loans** — All 5 plans (1, 2, 4, 5, PGL) in both 2025/26 and 2026/27; threshold differences confirmed.
5. **Pension RaS** — Band extension and ANI reduction confirmed across 15 scenarios including near-taper cases.
6. **CGT** — AEA, basic/higher rate split, brought-forward losses, multiple disposals, both tax years.
7. **Sequential journeys** — Cumulative YTD handling correct across 4-invoice journey scenarios.
8. **Stability at extremes** — Zero invoice, penny invoice, £500k invoice: all stable.

---

## Remaining assurance (Stages 3–4)

Stage 1 + Stage 2 provides confidence across the wide representational surface.
Before a **final production readiness verdict**:

**Stage 3 — Interaction scenarios**
- Complex combinations: salary + YTD + pension + all SL plans simultaneously
- Multiple invoices triggering different thresholds in sequence
- Pension large enough to interact with multiple taper boundaries
- CGT combined with high-income income tax

**Stage 4 — Tolerance and stress**
- Input validation (negative invoices, unsupported tax years)
- Very large pension contributions
- Floating-point precision stress at sub-penny amounts
- Year-boundary edge cases

---

## Recommendation

**October beta: APPROVED on current evidence.** Gate 1 and Gate 2 both passed. The engine is arithmetically sound across all representative and boundary scenarios. EL-001 is permanently pinned by 16 regression tests. Proceed with Stage 3 in parallel with beta preparations; any Gate 3 findings should be addressed before general availability.