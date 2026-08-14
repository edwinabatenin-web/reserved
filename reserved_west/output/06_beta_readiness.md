# October Beta Readiness Assessment
**Assurance cycle:** Reserved West Initiative 001 (Stage 1 only)
**Engine version:** 2.0.0
**Date:** 2026-08-06

## Overall verdict
**🟡 Conditionally Ready (October Beta)**

The engine passes all Stage 1 smoke tests with no defects or unexpected variances. EL-001 (PA taper methodology) was resolved in engine v2.0.0: all taper-zone scenarios now return exact results. Further assurance stages (2–4) are required before a final readiness verdict. Based on Stage 1 evidence, the engine is fit for an October beta.

---

## Stage 1 findings

**Scenarios executed:** 30
**Passing (exact):** 30
**Passing (±1p rounding):** 0
**PA taper zone scenarios:** 4 — all PASS (EL-001 resolved v2.0.0)
**Defects:** 0

### Strengths confirmed by Stage 1

1. **Core arithmetic is correct** across all four income tax bands (0%, 20%, 40%, 45%).
2. **Band boundaries are handled correctly**: basic rate limit (£50,270),
   additional rate threshold (£125,140), and the PA floor at £0.
3. **Personal Allowance taper is correct** (EL-001 resolved): the engine now uses
   `total_tax(end) − total_tax(start)`, independently computing the correct PA at
   each income level. All three taper-zone scenarios return zero variance.
4. **Class 4 NI** (main 6% and upper 2%) is calculated accurately on
   freelance profit; correctly zero for employment-only invoices.
5. **All five student loan plans** calculate correctly at their
   respective 2026/27 thresholds; dual repayment sums correctly.
6. **Pension RaS** correctly extends the basic-rate band and reduces ANI.
   The saving for a £52k salary payer with £5k pension was verified.
7. **CGT** correctly applies the AEA (£3,000), handles brought-forward
   losses, and splits gains across basic/higher bands.
8. **Zero-income edge case** is handled (£100 invoice → £0 tax below PA).
9. **Large invoice from zero** (£150,000) produces correct cross-band result.

---

## Pending assurance (Stages 2–4)

Stage 1 provides confidence in the happy path.  Before a final verdict:

**Stage 2 — Representative & Boundary (~150 scenarios)**
- Edge cases at every threshold (£12,570, £50,270, £100,000, £125,140)
- YTD income near each threshold
- All student loan plans in 2025/26 (different thresholds)
- Pension contributions at various levels
- Zero, negative (validation), and very large inputs

**Stage 3 — Interaction scenarios**
- Salary + YTD + pension + student loan combined
- Multiple invoices in sequence (cumulative YTD effect)
- Pension large enough to push eBRL > ART
- Student loan + pension combination at higher rate

**Stage 4 — Tolerance**
- Extremely large invoices
- Pension > BRL (eBRL capped at ART)
- Multiple plan simultaneous repayment at different thresholds
- Invalid input validation

---

## Recommendation

**Proceed to Stage 2.** Gate 1 is passed. The engine is arithmetically
sound for the core use cases. EL-001 is fully resolved and regression-pinned.
Before October beta, complete at least Stage 2 to confirm boundary-case reliability.