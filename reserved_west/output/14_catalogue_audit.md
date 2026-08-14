# Scenario Catalogue Audit — Pre-Stage 3
**Document:** RW-CA-001
**Assurance cycle:** Reserved West Initiative 001
**Scope:** All Stage 1 and Stage 2 scenarios (180 total)
**Date:** 2026-08-06
**Status:** ✅ CONFIRMED — All scenarios contain sufficient information for independent reproduction

---

## 1. Audit scope and methodology

Every Stage 1 scenario (RW-S1-001 – RW-S1-030) and every Stage 2 scenario
(RW-S2-001 – RW-S2-150) was reviewed against the reproducibility checklist
defined in the pre-Stage 3 verification brief.

For each scenario, the following fields were assessed:

| Field | Required for IT scenarios | Required for CGT scenarios |
|---|---|---|
| Scenario ID | ✅ | ✅ |
| Purpose (title + description) | ✅ | ✅ |
| Tax year | ✅ | ✅ |
| Starting tax position (salary + YTD) | ✅ | n/a |
| Income components | ✅ | n/a |
| Pension contributions | ✅ | n/a |
| Student loan plan(s) | ✅ | n/a |
| Capital gains inputs (disposals) | n/a | ✅ |
| Brought-forward losses, tax paid | n/a | ✅ |
| Expected outcome (runtime-computed) | ✅ | ✅ |
| HMRC reference(s) | Centralized | Centralized |
| Scenario status | Evidence register | Evidence register |

---

## 2. Field completeness — programmatic verification

The following was verified programmatically across all 180 scenarios:

| Check | Stage 1 (30) | Stage 2 (150) | Result |
|---|---|---|---|
| Scenario ID present and unique | 30/30 | 150/150 | ✅ |
| Title present | 30/30 | 150/150 | ✅ |
| Description present | 30/30 | 150/150 | ✅ |
| Tax year present in inputs | 30/30 | 150/150 | ✅ |
| Scenario type declared | 30/30 | 150/150 | ✅ |
| Inputs dict complete for type | 30/30 | 150/150 | ✅ |
| Groups declared | 30/30 | 150/150 | ✅ |
| Envelope declared | 30/30 | 150/150 | ✅ |

**No scenario was found with missing or incomplete information.**

---

## 3. Income tax scenario structure (per scenario)

Every income tax scenario contains:

```
scenario_id:    RW-Sx-NNN               — permanent unique identifier
title:          <one-line summary>       — purpose
description:    <prose>                  — income pattern, expected effect, boundary context
inputs:
  invoice_amount:                        — gross invoice amount (starting point for calculation)
  profile:
    day_job_salary:                      — total employment income for the tax year
    ytd_freelance_profit:               — cumulative freelance income before this invoice
    personal_pension_contributions:     — gross pension contribution (0 if not applicable)
    student_loan_plans:                 — list of plan identifiers (empty if not applicable)
  tax_year:                             — "2025/26" or "2026/27"
groups:                                 — design matrix tags (e.g. ["stage2", "rep"])
envelope:                               — "income_tax" or "cgt"
scenario_type:                          — "income_tax" or "cgt"
```

The `profile` dict maps directly to the engine's `estimate_incremental_liability()`
interface and the reference calculator's `ref_estimate()` interface, so no transformation
is required to reproduce the result.

**Starting tax position** is the combined `day_job_salary + ytd_freelance_profit`.
An independent reviewer can reproduce every income tax scenario with only:
- HMRC rates for the declared tax year (available from doc 02)
- The inputs dict above
- A total-then-differential income tax calculation

---

## 4. CGT scenario structure (per scenario)

Every CGT scenario contains:

```
scenario_id:    RW-Sx-NNN
title, description, groups, envelope, scenario_type: (as above)
inputs:
  tax_year:                             — "2025/26" or "2026/27"
  disposals:
    - asset_type:                       — "shares", "crypto", "other"
      description:                      — human-readable label
      disposal_date:                    — ISO date
      proceeds:                         — gross disposal proceeds
      allowable_cost:                   — allowable acquisition cost
  taxable_income_before_gains:         — IT taxable income before adding gains (for rate split)
  brought_forward_losses:              — prior year capital losses (0 if not applicable)
  tax_already_paid:                    — any CGT instalment payments (0 if not applicable)
```

An independent reviewer can reproduce every CGT scenario with only:
- AEA (£3,000), basic rate (18%), higher rate (24%), BRL (£50,270)
- The inputs dict above

---

## 5. Expected outcome

Expected outcomes are **not pre-set** in scenario definitions. They are computed at runtime
by the independent reference calculator (`ref_estimate()` / `ref_cgt()`). This is a
deliberate independence property (see doc 00, Task A).

For audit purposes, the computed expected values for every scenario are recorded in the
evidence registers:

- Stage 1: `03_evidence_register.csv` — columns `expected_*`
- Stage 2: `09_stage2_evidence_register.csv` — columns `expected_*`

These CSV files constitute the permanent record of expected values for Stages 1 and 2
and are sufficient for independent reproduction.

---

## 6. HMRC references

HMRC legislative references are **centralized** in the HMRC Reference Register (doc 02)
rather than duplicated per scenario. This is by design: each scenario's tax year and
income/CGT type determines which rows of the Reference Register apply.

The mapping is straightforward:

| Scenario type | Applicable Reference Register sections |
|---|---|
| Income tax (no pension, no SL) | Income tax section |
| Income tax (with pension) | Income tax section + Pension Relief at Source section |
| Income tax (with student loan) | Income tax section + Student loans section |
| Income tax (PA taper zone) | Income tax section — PA taper rows |
| CGT | Capital Gains Tax section |
| Combined | All applicable sections |

An independent reviewer can construct the full legislative basis for any scenario by
reading the Reference Register alongside the scenario's declared tax year and type.

---

## 7. Scenario status

Scenario execution status is not a field on scenario definitions; it is tracked in the
evidence registers:

- `03_evidence_register.csv` — Stage 1 outcomes (PASS / PASS_PENNY / FAIL / etc.)
- `09_stage2_evidence_register.csv` — Stage 2 outcomes

Current status of all 180 scenarios: **PASS** (149 exact PASS + 30 Stage 1 PASS +
1 UNSUPPORTED_EXPECTED for zero-invoice validation boundary RW-S2-136).

---

## 8. Enrichment: scenario notes by group

The audit identified no missing required fields. The following group-level notes
are added to the catalogue as enrichment for Stage 3 readers.

### Stage 1 groups

| Group | Scenarios | HMRC focus |
|---|---|---|
| Representative | RW-S1-001–008 | All four rate bands; income profiles covering PA, BRL, higher rate, additional rate |
| Boundary | RW-S1-009–016 | PA boundary from zero; BRL straddling; PA taper entry; ART crossing; zero/tiny/large |
| Student loan | RW-S1-017–023 | All five plans (1, 2, 4, 5, Postgraduate); dual repayment |
| Pension RaS | RW-S1-024–026 | BRL extension; taper elimination; no-effect below BRL |
| CGT | RW-S1-027–030 | Below AEA; basic rate; split rate; brought-forward losses |

### Stage 2 groups

| Group | Scenarios | HMRC focus |
|---|---|---|
| REP | RW-S2-001–015 | 15 representative profiles; includes EL-001 zone, all bands, all SL, pension |
| THR | RW-S2-016–045 | 10 material thresholds × 3 boundary points; NI limits; pension eBRL cap |
| SL 2025/26 | RW-S2-046–060 | All 5 plans; below/crosses/above threshold; correct 2025/26 thresholds |
| SL 2026/27 | RW-S2-061–075 | All 5 plans; below/crosses/above threshold; correct 2026/27 thresholds |
| PEN | RW-S2-076–090 | 15 pension scenarios; BRL extension; ANI taper interaction; eBRL cap |
| CGT | RW-S2-091–115 | 25 CGT scenarios; AEA; basic/higher split; BF losses; two tax years |
| SEQ | RW-S2-116–135 | 4 multi-invoice journeys; year comparison; cumulative YTD effect |
| EDG | RW-S2-136–150 | Zero invoice (UNSUPPORTED_EXPECTED); penny; £500k; all-5-plans; exact boundaries |

---

## 9. EL-001 zone coverage

Scenarios covering the Personal Allowance taper zone (ANI £100,000 – £125,140),
which constitute the EL-001 permanent regression family:

**Stage 1:** RW-S1-012, RW-S1-013, RW-S1-014 (3 scenarios)
**Stage 2:** RW-S2-006, RW-S2-007, RW-S2-008, RW-S2-027, RW-S2-028, RW-S2-029,
RW-S2-030, RW-S2-031, RW-S2-032, RW-S2-033, RW-S2-042, RW-S2-079, RW-S2-080,
RW-S2-081, RW-S2-122, RW-S2-123, RW-S2-130 (17 scenarios)

**Total EL-001 zone scenarios: 20 (all PASS)**

All EL-001 zone scenarios are fully described with income values that make the
taper interaction explicit in their descriptions.

---

## 10. Audit conclusion

All 180 Stage 1 and Stage 2 scenarios contain sufficient information for an independent
reviewer to reproduce every result without access to the engine source code. Specifically:

- All inputs required for reproduction are present in the scenario definition.
- Expected values are reproducible via the reference calculator or via direct HMRC calculation.
- HMRC legislative sources are fully documented in the Reference Register.
- Scenario execution status is documented in the evidence registers.
- No scenario was found with missing, incomplete, or ambiguous information.

**The Scenario Catalogue is cleared for Stage 3.**
