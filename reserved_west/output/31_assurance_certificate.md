# Reserved Engine — Assurance Certificate
> **SUPERSEDED — DO NOT USE AS CURRENT ACCURACY EVIDENCE.** WP7's independent review on 13 August 2026 found that the historical runtime reference shared calculation lineage with the engine, contained incorrect PA-taper, pension and multiple-student-loan evidence, covered engine 2.0.1 rather than 3.0.0, and did not cover confirmed v1. See `docs/RESERVED_WEST_ASSURANCE_REVIEW.md`.

**Certificate reference:** RW-001-CERT
**Date of issue:** 7 August 2026
**Certificate version:** 1.0
**Issued by:** Reserved West Initiative 001

---

## Certified subject

| Item | Detail |
|---|---|
| Product | Reserved™ — freelance tax reserve engine |
| Engine version | 2.0.1 |
| Assurance framework | Reserved West Initiative 001 |
| Framework version | 1.0 (four-stage gate model) |
| Certification date | 7 August 2026 |

---

## Assurance scope

The certificate covers the following computations for England, Wales, and Northern Ireland:

- **Income Tax** — personal allowance; basic (20%), higher (40%), and additional (45%) rates; personal allowance taper when adjusted net income exceeds £100,000
- **National Insurance (Class 4)** — main rate (6%) and upper rate (2%) on freelance profit
- **Pension Relief at Source** — extension of the basic-rate limit and reduction of adjusted net income
- **Student Loan repayments** — Plans 1, 2, 4, 5, and Postgraduate Loan
- **Capital Gains Tax** — post-October 2024 rates (18%/24%); annual exempt amount (£3,000); brought-forward losses; basic/higher-rate split based on taxable income
- **Tax years 2025/26 and 2026/27**

**Explicitly outside scope** (not covered by this certificate):

- Scottish income tax (different rate bands)
- Dividend income and savings income
- Class 1 NI on employment income (assumed handled via PAYE)
- Employer pension contributions and salary sacrifice
- CGT Business Asset Disposal Relief and Investors' Relief
- CGT share pooling and 30-day matching rules
- Non-UK-resident and non-domicile cases
- PAYE coding adjustments

---

## Assurance gates

The programme was conducted in four sequential stages, each subject to a formal gate decision. No gate was passed while any defect was open.

| Gate | Stage | Scenarios | Outcome |
|---|---|---|---|
| Gate 1 | Core calculations — each component in isolation | 30 | ✅ PASSED |
| Gate 2 | Representative and boundary — realistic user profiles; all rate thresholds | 150 | ✅ PASSED |
| Gate 3 | Interaction — multi-component simultaneous; sequential invoices; tolerance | 80 | ✅ PASSED |
| **Final Gate** | **Tolerance, exact boundaries, mathematical invariants, input validation** | **32** | **✅ PASSED** |
| **Total** | | **292** | **✅ All passing** |

---

## Automated test suite

| Suite | Run command | Tests |
|---|---|---|
| Workspace | `pytest tests/` | 547 |
| Engine bundle | `PYTHONPATH=reserved-engine-2.0.0 pytest reserved-engine-2.0.0/tests/` | 165 |
| **Combined** | | **712** |

All tests pass at engine v2.0.1.

---

## Defects found and resolved

All three defects were discovered during Reserved West Initiative 001, resolved before gate passage, and permanently regression-pinned.

| Ref | Description | Resolved in |
|---|---|---|
| EL-001 | Incremental income tax applied end-state Personal Allowance across the full invoice interval — incorrect results when PA changed within the interval | v2.0.0 |
| EL-002 | CGT basic-rate limit read from a module-level constant rather than versioned tax configuration | v1.0.0 |
| EL-003 | Extended basic-rate limit not capped at the Additional Rate Threshold when pension > £74,870 — suppressed 45% rate on all income above £125,140 | v2.0.1 |

---

## Regression families

| Family | Regression tests | Classification |
|---|---|---|
| EL-001 | 18 workspace | Any future variance in PA taper zone → REGRESSION_EL001 (gate-blocking) |
| EL-002 | 1 workspace | Any future CGT BRL mis-sourcing → FAIL |
| EL-003 | 37 (24 workspace + 13 bundle) | Any future variance where pension > £74,870 → REGRESSION_EL003 (gate-blocking) |

---

## Known limitations

The following are not defects; they are documented capability boundaries:

1. **Scottish income tax** — the engine applies England/Wales/NI rates to all inputs regardless of user geography. Scottish-resident users will receive materially incorrect results. A product-level geographic warning is required before serving Scottish users.
2. **Class 1 NI (employment)** — not recalculated; the engine assumes PAYE handles employment-side NI contributions correctly.
3. **Dividend and savings income** — not modelled; affects users who receive dividend income alongside freelance income.
4. **Reference independence** — assurance scenarios are grounded against a reference calculator authored by the Reserved team, not independently verified by HMRC or a third party. Results are HMRC-consistent to the best of the team's knowledge.

---

## Certification statement

Reserved West Initiative 001 has verified that the Reserved engine (v2.0.1) computes income tax, National Insurance, student loan repayments, pension Relief at Source, and capital gains tax correctly across **292 reference-grounded scenarios** and **712 automated tests**, within the scope stated above.

All four assurance gates passed. No defects are open. The engine is certified for use in the **October 2026 private beta**.

**This certificate does not transfer to modified versions of the engine.** Any code change to the income tax, NI, student loan, pension, or CGT modules requires re-certification before the engine may be represented as covered by this certificate.

---

*Reserved West Initiative 001 — Final Gate PASSED — 7 August 2026*
