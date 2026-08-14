# October 2026 Beta Readiness — Final Assessment
**Assurance cycle:** Reserved West Initiative 001 (all four stages)
**Engine version:** 2.0.1
**Date:** 2026-08-07

## Final verdict
**✅ Ready — October 2026 Beta Approved**

All four assurance gates have passed. The engine has been verified across 292 independent reference-grounded scenarios, covering core calculations, boundary conditions, complex interactions, extreme inputs, and mathematical invariants. No defects remain open. The engine is certified for the October 2026 private beta.

---

## Complete assurance evidence

| Stage | Scenarios | Gate | Key coverage |
|---|---|---|---|
| Stage 1 — Core calculations | 30 | ✅ PASSED | Each component in isolation; basic smoke tests |
| Stage 2 — Representative & boundary | 150 | ✅ PASSED | Realistic profiles; all threshold boundaries |
| Stage 3 — Interaction | 80 | ✅ PASSED | Multi-component simultaneous; sequential invoices |
| Stage 4 — Final Gate | 32 | ✅ PASSED | Extreme inputs; exact boundaries; invariants; validation |
| **Total** | **292** | **✅** | |

---

## Confirmed strengths (all stages combined)

1. **Core arithmetic** — All IT bands, NI rates, and SL plans compute correctly in isolation (Stage 1) and in interaction (Stage 3).
2. **Boundary precision** — No off-by-one errors at BRL/UPL (£50,270), ART (£125,140), PA taper entry (£100,000), or PA/LPL joint zero (£12,570). Confirmed at Stage 2 and 4.
3. **EL-001 resolved and regression-pinned** — 18 regression tests + 23 assurance scenarios across Stages 2–4 all confirm zero variance in the taper zone.
4. **EL-003 resolved and regression-pinned** — 37 regression tests + 2 Stage 4 scenarios confirm the eBRL cap (min(BRL+pension, ART)) is applied correctly.
5. **Pension interactions** — RaS correctly reduces ANI (IT), extends eBRL (IT), but does NOT reduce SL income or NI profit. Confirmed across Stages 2, 3, and 4.
6. **Rounding** — ROUND_HALF_UP confirmed at 20%, 40%, 45% (IT), 6%/2% (NI), 9% (SL), and 18%/24% (CGT). Stage 3 sub-penny scenarios + Stage 4 half-penny invariants all PASS.
7. **Extreme scale** — Engine handles £1,000,000 invoices and £500,000 YTD positions without arithmetic failure (Stage 4 EXT group).
8. **Input validation** — Zero invoice correctly rejected at every stage tested.
9. **CGT** — Basic/higher split, AEA, BF losses, and 2025/26 year routing all correct.
10. **Year routing** — 2025/26 and 2026/27 thresholds applied correctly for all SL plans with variable thresholds; Plans 5 and PGL confirmed identical across years.

---

## Regression families in force

| Family | Defect | Tests | Assurance scenarios |
|---|---|---|---|
| EL-001 | Moving Personal Allowance | 18 workspace | 23 across Stages 2–4 |
| EL-002 | CGT BRL from versioned config | 1 workspace | Implicit in all CGT scenarios |
| EL-003 | eBRL not capped at ART | 37 (24+13) | 2 in Stage 4 (BND+VAL) |

---

## Open items (not engine defects)

The following are known limitations, not defects, and are documented in the Capability Register (01_capability_register.md):

- Scottish income tax rates (different band rates; out of scope)
- Class 1 NI on employment income (assumed handled via PAYE)
- Employer pension / salary sacrifice
- Dividend income and savings income
- CGT — BADR / Investors' Relief
- CGT — share pooling and 30-day matching rules

---

## Recommendation

**October 2026 private beta: APPROVED.**

The Reserved engine v2.0.1 has passed all four assurance gates under Reserved West Initiative 001. The engine is arithmetically correct across 292 independent scenarios, regression-pinned against all three historical defect families, and confirmed correct at extreme inputs, exact boundaries, and half-penny rounding.

Proceed with October beta launch.