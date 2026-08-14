# Reserved West — User Manual, Maintenance & Release Guide

**Document reference:** RW-001-MAN  
**Document version:** 1.0 (first draft — for editorial refinement)  
**Assurance programme:** Reserved West Initiative 001  
**Engine version at time of writing:** 2.0.1  
**Date:** 2026-08-07  
**Intended audience:** Future developers maintaining Reserved West  

---

## 1. Purpose

Reserved West is the independent assurance programme for the Reserved tax engine. Its purpose is to verify, before each beta or production release, that the engine produces arithmetically correct results across the supported set of UK tax calculations.

Reserved West is not a unit test suite. It is a structured multi-stage gate framework that:

- runs scenarios through both the Reserved engine and an independent reference calculator;
- compares results field-by-field using decimal arithmetic;
- classifies each scenario with a formal outcome code;
- writes a set of numbered deliverable documents that constitute the permanent evidence record;
- evaluates formal gate decisions at the end of each stage.

The framework was built for and executed during Initiative 001. It is designed to be re-run for future engine versions.

---

## 2. Intended audience

This manual is written for developers who will:

- run Reserved West for a new engine version;
- add scenarios to an existing stage catalogue;
- add support for new legislation or tax years;
- update regression suites after a defect is resolved;
- diagnose a runner failure or unexpected outcome code;
- understand the relationship between assurance stages, gate criteria, and the pytest test suites.

The document assumes familiarity with Python and with the structure of the Reserved workspace.

---

## 3. Repository structure

```
reserved_west/
├── __init__.py                     Package declaration and description
├── reference_calculator.py         Independent HMRC-grounded reference calculator
├── runner.py                       Scenario execution engine and outcome classifier
├── scenarios.py                    Stage 1 scenario catalogue (30 scenarios)
├── scenarios_stage2.py             Stage 2 scenario catalogue (150 scenarios)
├── scenarios_stage3.py             Stage 3 scenario catalogue (80 scenarios)
├── scenarios_stage4.py             Stage 4 scenario catalogue (32 scenarios)
├── run_assurance.py                Stage 1 runner — produces output docs 01–07
├── run_stage2.py                   Stage 2 runner — produces output docs 08–14
├── run_stage3.py                   Stage 3 runner — produces output docs 15–23
├── run_stage4.py                   Stage 4 runner — produces output docs 25–30
└── output/
    ├── 00_independence_assurance.md
    ├── 01_capability_register.md
    ├── 02_hmrc_reference_register.md
    ├── 03_evidence_register.csv
    ├── 04_defect_backlog.md
    ├── 05_gate_decisions.md
    ├── 06_beta_readiness.md
    ├── 07_decision_log.md
    ├── 08_stage2_scenario_catalogue.md
    ├── 09_stage2_evidence_register.csv
    ├── 10_stage2_component_summary.md
    ├── 11_stage2_findings.md
    ├── 12_gate2_decisions.md
    ├── 13_beta_readiness_stage2.md
    ├── 14_catalogue_audit.md
    ├── 15_pre_stage3_baseline.md
    ├── 16_regression_integrity.md
    ├── 17_stage3_readiness.md
    ├── 18_stage3_scenario_catalogue.md
    ├── 19_stage3_evidence_register.csv
    ├── 20_stage3_component_summary.md
    ├── 21_stage3_findings.md
    ├── 22_gate3_decisions.md
    ├── 23_beta_readiness_stage3.md
    ├── 24_test_count_audit.md
    ├── 25_stage4_scenario_catalogue.md
    ├── 26_stage4_evidence_register.csv
    ├── 27_stage4_component_summary.md
    ├── 28_stage4_findings.md
    ├── 29_final_gate_decision.md
    ├── 30_beta_readiness_final.md
    ├── 31_assurance_certificate.md
    ├── 32_initiative_summary.md
    └── 33_user_manual.md           (this document)
```

The `output/` directory is written by the runners at runtime. All files in it should be treated as generated artefacts for a given engine version. Historical outputs from Initiative 001 are the permanent evidence base and should not be overwritten without creating a new initiative.

---

## 4. Major components

### 4.1 Reference calculator (`reference_calculator.py`)

The reference calculator is the ground truth against which the engine is measured. It deliberately does not import anything from the Reserved engine or from `reserved/engines/`. All HMRC thresholds and rates are hard-coded with inline citations to HMRC primary sources.

The reference calculator implements:

- `ref_estimate(invoice_amount, profile, tax_year)` — income tax, Class 4 NI, and student loan for a single invoice
- `ref_cgt(disposals, taxable_income_before_gains, ...)` — capital gains tax for a set of disposals
- `in_el001_zone(invoice_amount, profile)` — returns True if the Personal Allowance changes between starting and ending income positions; used to annotate results for the EL-001 regression family

The income tax algorithm is total-then-differential: compute complete tax at end income, compute complete tax at start income, return the difference. The reference independently determines the correct Personal Allowance at each income point. This is the correct algorithm; it differs from the range-based approach used in engine v1.0.0 (see EL-001).

The reference has its own HMRC rate configuration (`_IT_CFG`, `_CGT_CFG`) that must be updated whenever a new tax year is supported. The reference configuration is cross-checked against the engine's `tax_config.py` during assurance. Any discrepancy between them is a finding.

### 4.2 Runner (`runner.py`)

The runner dispatches each scenario to the appropriate execution function, compares engine and reference outputs field-by-field using `Decimal` arithmetic, and classifies the outcome.

**Dispatch logic:**

- If `scenario["envelope"] == "out_of_scope"` or `scenario["expected_outcome"] == "unsupported"`, the runner returns UNSUPPORTED_EXPECTED without calling either calculator.
- If `scenario_type == "income_tax"`, calls `_run_income_tax()`.
- If `scenario_type == "cgt"`, calls `_run_cgt()`.
- Any other `scenario_type` produces UNSUPPORTED_EXPECTED.

**Income tax comparison fields:** `income_tax`, `national_insurance`, `student_loan`, `total`.

**CGT comparison fields:** `taxable_gains`, `estimated_cgt`, `outstanding_reserve`.

**EL-001 zone detection:** `in_el001_zone()` is called for every income-tax scenario. The result is stored in the `el001_zone` field of the result dict for annotation purposes. If a variance is detected in an EL-001 zone scenario, the outcome is `REGRESSION_EL001` rather than `FAIL`.

### 4.3 Scenario catalogues (`scenarios.py`, `scenarios_stage2.py`, etc.)

Each stage has its own catalogue file. Stage 1 uses a flat list of dicts (`STAGE_1`). Stages 2–4 use a helper function (`_it()` or equivalent) that constructs scenario dicts from keyword arguments, making the catalogues more compact.

The scenario dict schema is documented in section 7.

### 4.4 Stage runners (`run_assurance.py`, `run_stage2.py`, `run_stage3.py`, `run_stage4.py`)

Each stage runner:

1. Loads the stage's scenario catalogue.
2. Calls `runner.run_all(scenarios)`.
3. Tallies outcomes and prints a summary to stdout.
4. Evaluates gate criteria against the results.
5. Writes the stage's deliverable documents to `output/`.
6. Prints the gate verdict to stdout.

Each runner contains a hardcoded `ENGINE_VERSION` constant that must be updated when the engine version changes.

The runners are independent programs with no shared state. Running Stage 2 does not require Stage 1 to have run first (though doing so out of sequence defeats the gate model).

---

## 5. Assurance stages

### Stage 1 — Core calculations (Gate 1)

**Runner:** `run_assurance.py`  
**Scenarios:** 30 (RW-S1-001–030)  
**Catalogue:** `scenarios.py`  
**Output docs:** 01–07  

Covers: each supported tax component in isolation; the EL-001 taper zone (three scenarios); basic CGT pathways. Intended as smoke tests — coverage is representative, not exhaustive.

### Stage 2 — Representative and boundary (Gate 2)

**Runner:** `run_stage2.py`  
**Scenarios:** 150 (RW-S2-001–150)  
**Catalogue:** `scenarios_stage2.py`  
**Output docs:** 08–14  

Covers: realistic user profiles across all income levels; all key threshold boundaries from both sides; all student loan plans and tax years; pension contributions at multiple levels; edge cases (zero income, large invoices, £0.01 invoices).

### Stage 3 — Interaction (Gate 3)

**Runner:** `run_stage3.py`  
**Scenarios:** 80 (RW-S3-001–080)  
**Catalogue:** `scenarios_stage3.py`  
**Output docs:** 15–23  

Covers: multi-component simultaneous interactions (pension + SL + NI + IT); sequential invoice sequences (cumulative YTD effect); EL-003 boundary (pension extending eBRL to ART); sub-penny rounding; stress and tolerance cases; CGT additions.

### Stage 4 — Tolerance, boundary, invariant, validation (Final Gate)

**Runner:** `run_stage4.py`  
**Scenarios:** 32 (RW-S4-001–032)  
**Catalogue:** `scenarios_stage4.py`  
**Output docs:** 25–30  

Groups:
- **EXT** (001–008): extreme valid inputs — invoices to £1,000,000, salaries to £500,000, pension exceeding income, all five SL plans on £200k.
- **BND** (009–018): exact threshold conditions — BRL/UPL at £50,270, ART at £125,140, PA taper entry at £100,000, PA/LPL joint zero at £12,570, eBRL cap exactly at ART (EL-003 boundary), SL Plan 2 and Plan 5 straddles.
- **INV** (019–026): mathematical invariants — non-negativity, SL independence from pension, NI independence from pension, zero-tax floor, ROUND_HALF_UP at three rates, component additivity.
- **VAL** (027–032): validation — zero invoice rejection, sub-threshold single penny, extreme pension with EL-003 cap, three CGT edge cases.

### Close-out documents (Initiative 001 only)

Docs 31 (`31_assurance_certificate.md`) and 32 (`32_initiative_summary.md`) were written manually at initiative close-out. They are not produced by a runner. This document (33) is also a manual production. These are permanent records for Initiative 001 and should not be regenerated by a future initiative.

---

## 6. Gate process

### Gate criteria

Each gate is a binary pass/fail decision evaluated against the results of the corresponding stage.

**Gate 1 (Stage 1):** No FAIL, no REGRESSION_EL001, no ERROR outcomes. PASS_PENNY and UNSUPPORTED_EXPECTED are acceptable.

**Gate 2 (Stage 2):** Same criteria as Gate 1, applied to Stage 2 results. Additionally, all EL-001 zone scenarios must PASS (zero variance).

**Gate 3 (Stage 3):** Same criteria. All EL-001 zone scenarios must PASS.

**Final Gate (Stage 4):** Seven explicit criteria evaluated in `run_stage4.write_final_gate()`:
1. No REGRESSION_EL001 outcomes.
2. All EL-001 zone scenarios PASS.
3. No unexplained FAIL outcomes.
4. No ERROR outcomes.
5. At least one EL-003 boundary scenario (`ebrl_cap` group tag) present and all passing.
6. All rounding invariant scenarios (`rounding` group tag) passing.
7. At least one UNSUPPORTED_EXPECTED outcome (zero-invoice rejection confirmed).

The Final Gate criterion set is hardcoded in `run_stage4.py`. If criteria need to change for a future initiative, update that function.

### Gate failure

If a gate fails, the runner prints the failing scenarios to stdout, writes the deliverable documents with the failing state, and exits. The next stage must not be started until all blocking findings are resolved and the current stage re-run.

Defects found during a stage are recorded in the active defects section of `04_defect_backlog.md` (which is overwritten by the Stage 1 runner on each run) or in the stage-specific findings document (e.g., `28_stage4_findings.md`).

---

## 7. Scenario schema

Each scenario is a Python dict with the following keys:

| Key | Type | Required | Description |
|---|---|---|---|
| `scenario_id` | str | Yes | Permanent unique ID, format RW-SN-NNN. Never re-use or renumber. |
| `title` | str | Yes | Short description for display in evidence registers. |
| `groups` | list[str] | Yes | Grouping tags (e.g., `["representative"]`, `["ext", "ebrl_cap"]`). Runners use these for component summaries and gate criteria. |
| `envelope` | str | Yes | `"intended"`, `"extended"`, or `"out_of_scope"`. Only `"out_of_scope"` has runner-level meaning (triggers UNSUPPORTED_EXPECTED). In Stage 2 some scenarios use the scenario type as the envelope value — this is a convention inconsistency and has no functional effect. |
| `scenario_type` | str | Yes | `"income_tax"` or `"cgt"`. |
| `description` | str | Yes | Human-readable description used in the decision log and findings documents. |
| `inputs` | dict | Yes | See below. |
| `expected_outcome` | str | No | Set to `"unsupported"` to trigger UNSUPPORTED_EXPECTED regardless of envelope. Required for scenarios where the engine is expected to raise a validation error (e.g., zero invoice). |
| `notes` | str | No | Returned as the error message for UNSUPPORTED_EXPECTED scenarios. |

**Income-tax `inputs` keys:**

| Key | Description |
|---|---|
| `invoice_amount` | Gross invoice value. String or numeric; converted to Decimal internally. |
| `profile` | Dict containing `day_job_salary`, `ytd_freelance_profit`, `personal_pension_contributions`, `student_loan_plans` (list of plan identifiers: 1, 2, 4, 5, or `"postgraduate"`). |
| `tax_year` | `"2025/26"` or `"2026/27"`. Unsupported years cause a KeyError in both runner and reference. |

The `profile` dict also accepts the legacy singular key `student_loan_plan` (not a list) for backwards compatibility, but new scenarios should always use `student_loan_plans`.

**CGT `inputs` keys:**

| Key | Description |
|---|---|
| `disposals` | List of dicts with `proceeds`, `allowable_cost`, and optionally `gain_or_loss` (pre-computed). If `gain_or_loss` is absent, it is computed as `proceeds − allowable_cost`. |
| `taxable_income_before_gains` | Total taxable income after Personal Allowance, before adding gains. |
| `brought_forward_losses` | Optional; defaults to 0. |
| `tax_already_paid` | Optional; defaults to 0. |
| `tax_year` | `"2025/26"` or `"2026/27"`. |

---

## 8. Outcome codes

Defined in `runner.py` (see module docstring for the authoritative description).

| Code | Gate-blocking | Meaning |
|---|---|---|
| `PASS` | No | All monetary variances exactly £0.00. |
| `PASS_PENNY` | No | Maximum absolute variance ≤ £0.01. Acceptable per rounding policy DL-004. |
| `REGRESSION_EL001` | **Yes** | Variance detected in an EL-001 zone scenario. Indicates the moving-PA defect has re-appeared. Must not be softened to KNOWN_LIMITATION. |
| `FAIL` | **Yes** | Variance > £0.01 in a non-EL-001 scenario. |
| `UNSUPPORTED_EXPECTED` | No | Scenario declared out of scope or invalid; unsupported outcome is the expected result. |
| `ERROR` | **Yes** | Unexpected exception raised during execution. |

`KNOWN_LIMITATION` is not an outcome code. It was used in engine v1.0.0 for EL-001 zone scenarios before that defect was resolved. It has been permanently retired and must not be reintroduced.

---

## 9. Regression families

Two permanent regression families are in force.

### EL-001 — Moving Personal Allowance

**Root cause:** An incremental calculation that fixed the Personal Allowance at its end-state value across the full income interval. Invalid when the PA changed mid-interval (taper zone).

**Resolution:** Engine v2.0.0. The engine now computes `total_tax(end) − total_tax(start)`, independently determining the correct PA at each income point.

**Runner classification:** Any variance in a scenario where `in_el001_zone()` returns True produces `REGRESSION_EL001`, which is gate-blocking.

**Zone definition:** `in_el001_zone()` returns True if the Personal Allowance differs between starting and ending income positions. This covers all three EL-001 cases:
- Invoice crosses the PA taper start (ANI crosses £100,000 upward).
- Invoice remains wholly within the taper zone.
- Invoice crosses the PA elimination threshold (ANI crosses £125,140).

**Permanent tests:** `tests/test_el001_regression.py` — 18 workspace-side tests. Run with `pytest tests/`.

**Assurance coverage:** 23 scenarios across Stages 2, 3, and 4 are in the EL-001 zone; all pass with zero variance at engine v2.0.1.

### EL-003 — Extended BRL not capped at ART

**Root cause:** `extended_basic_rate_limit = BRL + pension` lacked a cap at the Additional Rate Threshold. When pension > £74,870, the uncapped eBRL exceeded £125,140, causing the 45% rate to be silently absorbed into the 20% slice.

**Resolution:** Engine v2.0.1. Fix: `extended_basic_rate_limit = min(BRL + pension, ART)`, applied identically in both the workspace engine and the bundle.

**Runner classification:** There is no dedicated `REGRESSION_EL003` outcome code in `runner.py`. EL-003-related failures would produce `FAIL`. The EL-003 regression family is enforced through the pytest test suites, not through a runner classification.

**Boundary group tag:** Stage 4 scenarios that test the EL-003 cap carry the group tag `"ebrl_cap"`. The Final Gate criteria require at least one `ebrl_cap` scenario to pass.

**Permanent tests:** `tests/test_el003_regression.py` (24 workspace tests) and `reserved-engine-2.0.0/tests/test_el003_regression.py` (13 bundle tests). Total: 37 tests.

### EL-002 — CGT BRL from module constant

**Root cause:** `capital_gains.py` sourced `BASIC_RATE_LIMIT` from a module-level constant instead of the versioned `tax_config` dictionary.

**Resolution:** Engine v1.0.0. No dedicated runner classification or regression test family; the fix is verified implicitly by all CGT scenarios.

---

## 10. Evidence generation

Running a stage runner overwrites the output documents for that stage. The documents for Initiative 001 are the permanent historical record and should not be overwritten for future initiatives without first archiving or renaming them.

### Document map

| Stage | Run command | Output documents |
|---|---|---|
| Stage 1 | `python -m reserved_west.run_assurance` | 01–07 |
| Stage 2 | `python -m reserved_west.run_stage2` | 08–14 |
| Stage 3 | `python -m reserved_west.run_stage3` | 15–23 |
| Stage 4 | `python -m reserved_west.run_stage4` | 25–30 |
| Close-out | Written manually | 31–32 (this document: 33) |

Note: document numbers 24 (`24_test_count_audit.md`) was written manually during Initiative 001 to record the RW-AUDIT-001 test count reconciliation. It is not generated by any runner.

### Evidence register schema

Each stage produces a CSV evidence register with the following columns:

`Scenario ID`, `Title`, `Groups`, `Envelope`, `Type`, `Tax Year`, `Engine Version`, `Reference Version`, `Expected (Total/CGT)`, `Actual (Total/CGT)`, `Primary Variance`, `Outcome`, `EL-001 Zone`, `Notes`.

For income-tax scenarios, `Expected` and `Actual` are the `total` field. For CGT scenarios, they are the `estimated_cgt` field. `Primary Variance` is `engine value − reference value`; negative values indicate the engine underestimates.

---

## 11. Interpreting outputs

### Reading the console output

Each runner prints a summary table of outcomes immediately after running, followed by detailed per-scenario results, followed by the gate verdict. A gate failure ends with `❌ [STAGE] FAILED`.

The detailed results table columns are: `ID`, `Outcome`, `PrimaryVar`, `EL001`, `Title`. `PrimaryVar` is the engine-minus-reference variance for the primary comparison field. `[✓]` in the `EL001` column marks EL-001 zone scenarios.

### Reading the evidence register CSV

Each row represents one scenario. Sort by `Outcome` to surface failures first. Non-zero values in `Primary Variance` are the starting point for investigating any FAIL or REGRESSION_EL001 outcome.

### Reading the findings document

Each stage produces a `_findings.md` document (e.g., `28_stage4_findings.md`). If all scenarios pass, the document contains a single finding (`S4-F0: All scenarios pass`) with a narrative summary. If failures exist, each is listed with severity, outcome code, primary variance, and per-field variances.

### Distinguishing PASS_PENNY from FAIL

PASS_PENNY (≤ £0.01 variance) is acceptable. It arises from intermediate rounding differences between the reference and engine approaches. At whole-pound integer inputs, PASS_PENNY did not occur in Initiative 001 — all scenarios that were intended to pass produced exactly zero variance. PASS_PENNY is more likely to appear in scenarios with fractional inputs or threshold straddles at non-integer amounts. It is not a defect unless it is systematic or grows above £0.01.

---

## 12. Normal release workflow

The following workflow applies when assessing a new engine version. Do not skip stages or run them out of order.

### Prerequisites

1. The new engine version is deployed to the bundle at `reserved-engine-2.0.0/`. The runner imports from the bundle, not from the workspace `reserved/engines/` copy.
2. The workspace engine and bundle are byte-identical for `income_tax.py`, `capital_gains.py`, `national_insurance.py`, and `student_loan.py`.
3. Both pytest suites pass at the new version:
   - `pytest tests/` (workspace — currently 547 tests)
   - `PYTHONPATH=reserved-engine-2.0.0 pytest reserved-engine-2.0.0/tests/` (bundle — currently 165 tests)

### Step 1 — Update ENGINE_VERSION

Update the `ENGINE_VERSION` constant in each of the four runner files:

```
reserved_west/run_assurance.py
reserved_west/run_stage2.py
reserved_west/run_stage3.py
reserved_west/run_stage4.py
```

All four must use the same version string. This is a hardcoded constant; there is no automatic version detection.

### Step 2 — Run stages sequentially

```bash
cd /home/runner/workspace

# Stage 1
PYTHONPATH=. .venv/bin/python -m reserved_west.run_assurance

# If Gate 1 passes, proceed to Stage 2
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage2

# If Gate 2 passes, proceed to Stage 3
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage3

# If Gate 3 passes, proceed to Stage 4
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage4
```

`PYTHONPATH=.` is required. Without it, `import reserved_west` will fail because Python will not find the package in the workspace root.

### Step 3 — Review output documents

After each stage, review the findings document and gate decision document before proceeding. The evidence register CSV and component summary provide supporting detail.

### Step 4 — Handle gate failures

If a gate fails:

1. Read the findings document to identify all failing scenarios and their variances.
2. Determine the root cause in the engine.
3. Fix the engine. Update both the workspace copy and the bundle copy.
4. Bump `ENGINE_VERSION` in all four runners.
5. Re-run both pytest suites to confirm the fix and no regressions.
6. Re-run the failing stage from the beginning. Do not skip to the next stage.

If the failure is in the EL-001 zone, treat it as `REGRESSION_EL001` and investigate before doing anything else.

### Step 5 — Close-out

If all four gates pass:

1. Update `reserved-engine-2.0.0/MANIFEST.json` fields for the new engine version and verification date.
2. Update `reserved_west/output/01_capability_register.md` if any capabilities changed.
3. Write updated close-out documents (equivalent to docs 29–32 for Initiative 001) as permanent records for the new initiative or release cycle.

---

## 13. Versioning

### Engine version

The engine version is stored in:
- `reserved/engines/__init__.py` (`ENGINE_VERSION` constant)
- `reserved-engine-2.0.0/reserved_engine/__init__.py` (same constant)
- `reserved-engine-2.0.0/MANIFEST.json` (`_engine_version` field)
- Each Reserved West runner file (`ENGINE_VERSION` constant, hardcoded)

When a new engine version is released, all four locations must be updated. The bundle directory name `reserved-engine-2.0.0/` does not change with patch versions; it reflects the major.minor version of the initial bundle release.

### Scenario IDs

Scenario IDs are permanent. Once assigned, they must never be changed or reused. This ensures that references in evidence registers, defect backlogs, and external documents remain valid.

Stage continuation:
- Stage 1: RW-S1-001 through RW-S1-030
- Stage 2: RW-S2-001 through RW-S2-150
- Stage 3: RW-S3-001 through RW-S3-080
- Stage 4: RW-S4-001 through RW-S4-032
- Stage 5 (if needed): RW-S5-001 onward

### Reference calculator version

The reference calculator identifies itself via a `rules_version` field in its output (e.g., `"ref-2026/27-v1.0"`). This version string is constructed from the tax year at call time; there is no top-level version constant in `reference_calculator.py` itself.

---

## 14. Maintenance activities

### Updating HMRC rates for a new tax year

1. Add a new entry to `_IT_CFG` in `reference_calculator.py`, following the existing pattern. All values must be `Decimal` literals. Cite the HMRC source for each threshold or rate in a comment.
2. Add a corresponding entry to `_CGT_CFG` if CGT rates change.
3. Add the new year to the engine's `tax_config.py` in both workspace and bundle copies.
4. Update the Student Loan threshold table with SLC Annual Threshold Notice values for the new year. Plans 5 and Postgraduate Loan currently have fixed thresholds; confirm whether these change.
5. Cross-check: run all existing scenarios for the new year (if any) to confirm zero variance. If existing scenarios hard-code the previous year, add new scenarios for the new year rather than changing existing ones.
6. Update `SUPPORTED_TAX_YEARS` — this is derived automatically from `sorted(_IT_CFG)`, so adding the new key is sufficient.

### Adding a new supported tax component

For example, adding Scottish income tax or dividend income:

1. Implement the calculation in both the workspace engine and the bundle.
2. Implement the same calculation in `reference_calculator.py` using HMRC primary sources. Do not share code between reference and engine.
3. Add a new scenario type constant if needed, and update the runner dispatch in `runner.py`.
4. Add scenarios to an appropriate stage catalogue. New components should begin with at least a Stage 1 treatment (core, in isolation) before being included in interaction scenarios.
5. Update `01_capability_register.md` to reflect the new supported capability.

### Adding new scenarios to an existing stage

1. Determine the correct stage for the new scenario. Stage 1 is for basic smoke tests; Stage 2 for boundary and representative; Stage 3 for interactions; Stage 4 for invariants and extreme cases.
2. Add the scenario dict (or `_it()` call) to the end of the corresponding catalogue file.
3. Assign the next sequential ID for that stage.
4. Re-run the corresponding stage runner to verify the new scenario passes and to regenerate the output documents.
5. If adding to Stage 4, ensure the new scenario carries appropriate group tags for the component summary and gate criteria (e.g., `"ebrl_cap"` for EL-003 boundary scenarios, `"rounding"` for rounding invariant scenarios).

Do not insert scenarios into the middle of a catalogue (this shifts subsequent IDs) and do not renumber existing scenarios.

### Updating regression suites

#### EL-001 regression tests

`tests/test_el001_regression.py` contains 18 tests covering the three EL-001 cases. If the EL-001 zone definition is updated (e.g., because PA taper thresholds change), update both the test file and `in_el001_zone()` in `reference_calculator.py`.

#### EL-003 regression tests

`tests/test_el003_regression.py` contains 24 workspace-side tests.  
`reserved-engine-2.0.0/tests/test_el003_regression.py` contains 13 bundle-native tests.

If the eBRL cap logic changes, update both test files. Both must always pass.

#### Adding a new regression family

When a new defect is resolved and permanently regression-pinned:

1. Create `tests/test_ELNNN_regression.py` in the workspace test suite.
2. Create a corresponding file in `reserved-engine-2.0.0/tests/` if the defect is in engine code that appears in the bundle.
3. If the defect has a specific zone (analogous to EL-001's taper zone), consider whether to add a runner-level classification code in `runner.py`.
4. Add the defect to `01_capability_register.md` and `04_defect_backlog.md` under defect history.
5. Document the trigger condition and fix precisely, following the pattern of the EL-003 entry in `04_defect_backlog.md`.

---

## 15. Common operational pitfalls

**1. Missing PYTHONPATH.**  
Running `python -m reserved_west.run_assurance` without `PYTHONPATH=.` fails with `ModuleNotFoundError: No module named 'reserved_west'`. Always prefix with `PYTHONPATH=.` or set it in the environment.

**2. Testing the workspace engine instead of the bundle.**  
The runner inserts `reserved-engine-2.0.0/` into `sys.path` and imports from `reserved_engine` (the bundle package). It does not import from `reserved/engines/`. If the workspace engine is modified but the bundle is not updated, the runner will continue testing the old bundle. Keep both copies in sync.

**3. ENGINE_VERSION constant not updated after a patch.**  
The `ENGINE_VERSION` string in each runner is hardcoded. If not updated after an engine patch, the output documents will report the old version string and the evidence register will contain incorrect version information. Update all four runner files.

**4. UNSUPPORTED_EXPECTED scenarios written without the trigger.**  
A scenario intended to produce UNSUPPORTED_EXPECTED must include either `"envelope": "out_of_scope"` or `"expected_outcome": "unsupported"` (or both). If neither is present and the engine raises a `ValueError` (as it does for zero invoices), the runner catches the exception and produces `ERROR` instead. This was the root cause of the S4-027 ERROR during Initiative 001.

**5. Scenario IDs reused or renumbered.**  
If an existing scenario dict is removed from a catalogue and a new one is appended, the new scenario must receive a new ID — not the ID of the removed scenario. Removed scenarios should be commented out, not deleted, if their historical record needs to be preserved.

**6. Combined test count reported without labelling.**  
Initiative 001 experienced a test count audit (RW-AUDIT-001) when a combined workspace+bundle count was misattributed as a workspace-only count. Always report counts with their exact run command and label: workspace (547), bundle (165), combined (712). Do not aggregate without explicit labelling.

**7. EL-001 zone threshold hardcoded to 2026/27.**  
`in_el001_zone()` uses `_IT_CFG["2026/27"]` for its taper threshold check. This is intentional (thresholds are frozen under Finance Act 2022 through 2028), but if a future Budget changes the taper thresholds, both `in_el001_zone()` and the hardcoded reference must be updated.

**8. Output documents overwritten with a failed state.**  
Each runner overwrites its output documents regardless of gate outcome. If a stage fails and the runner is re-run during investigation, the output documents will reflect the state at each run. Keep a record of the final state that was gate-assessed, particularly for the evidence register CSV.

---

## 16. Known operational assumptions

The following assumptions are embedded in the current implementation. Future maintainers should verify these before running Reserved West for a new engine version.

1. **The bundle is the engine under test.** The runner imports from `reserved-engine-2.0.0/reserved_engine/`, not from `reserved/engines/`. The workspace copy is not tested by the runner.

2. **Both engine copies must be byte-identical.** The workspace and bundle copies of `income_tax.py`, `capital_gains.py`, `national_insurance.py`, and `student_loan.py` must be identical. The framework does not enforce this; it is a maintenance convention.

3. **ROUND_HALF_UP throughout.** Both the engine and the reference calculator use `ROUND_HALF_UP` for all monetary rounding. Any change to the rounding policy requires a complete re-run of all stages.

4. **Before-and-after differential is the correct incremental algorithm.** The engine must compute incremental tax as `total_tax(end_position) − total_tax(start_position)`. Interval-based or range-based approaches are incorrect whenever any allowance, relief, or threshold changes between start and end. This is the core lesson of EL-001.

5. **All thresholds are frozen through 2028.** The Personal Allowance (£12,570), Basic Rate Limit (£50,270), and Class 4 NI limits are frozen under Finance Act 2022. The reference calculator and engine both rely on this. A future Budget change would require updating both, and re-running all stages.

6. **Student loan thresholds change annually.** Plans 1, 2, and 4 have variable thresholds confirmed each year by SLC Annual Threshold Notice. Plans 5 and Postgraduate Loan currently have fixed thresholds (confirmed through at least April 2027). Verify SLC notices each year before extending support for a new tax year.

7. **The reference calculator is not independently verified by HMRC.** All reference calculator thresholds and rates are sourced from HMRC publications and cross-checked by the development team. They have not been independently reviewed by HMRC. The assurance programme confirms internal consistency between the engine and the reference calculator; it does not constitute HMRC certification.

8. **Scottish income tax is out of scope.** There is no geography parameter in the engine or the runner. A Scottish-resident user would receive England/Wales/NI results without error. This is a product limitation, not an engine error, but it is worth noting because a future initiative that adds Scottish support would need to add a geography field to the scenario schema, reference calculator, and runner dispatch.

---

## Appendix A — Run commands reference

```bash
# From workspace root. Always use PYTHONPATH=.

# Stage 1 — Core calculations (Gate 1)
PYTHONPATH=. .venv/bin/python -m reserved_west.run_assurance

# Stage 2 — Representative and boundary (Gate 2)
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage2

# Stage 3 — Interaction (Gate 3)
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage3

# Stage 4 — Final Gate
PYTHONPATH=. .venv/bin/python -m reserved_west.run_stage4

# Workspace pytest suite (547 tests)
.venv/bin/python -m pytest tests/

# Engine bundle pytest suite (165 tests)
PYTHONPATH=reserved-engine-2.0.0 .venv/bin/python -m pytest reserved-engine-2.0.0/tests/
```

---

## Appendix B — Output document index

| Doc | Filename | Producer | Contents |
|---|---|---|---|
| 00 | `00_independence_assurance.md` | Manual | Independence declaration for reference calculator |
| 01 | `01_capability_register.md` | Stage 1 runner | Supported capabilities, defect history, out-of-scope catalogue |
| 02 | `02_hmrc_reference_register.md` | Stage 1 runner | HMRC sources for each rate and threshold |
| 03 | `03_evidence_register.csv` | Stage 1 runner | Stage 1 per-scenario results |
| 04 | `04_defect_backlog.md` | Stage 1 runner | Active and historical defects |
| 05 | `05_gate_decisions.md` | Stage 1 runner | Gate 1 decision and status of Gates 2–4 |
| 06 | `06_beta_readiness.md` | Stage 1 runner | Beta readiness after Stage 1 |
| 07 | `07_decision_log.md` | Stage 1 runner | Key assurance decisions and rationale |
| 08 | `08_stage2_scenario_catalogue.md` | Stage 2 runner | Stage 2 scenario listing by group |
| 09 | `09_stage2_evidence_register.csv` | Stage 2 runner | Stage 2 per-scenario results |
| 10 | `10_stage2_component_summary.md` | Stage 2 runner | Stage 2 results by component |
| 11 | `11_stage2_findings.md` | Stage 2 runner | Stage 2 findings |
| 12 | `12_gate2_decisions.md` | Stage 2 runner | Gate 2 decision |
| 13 | `13_beta_readiness_stage2.md` | Stage 2 runner | Beta readiness after Stage 2 |
| 14 | `14_catalogue_audit.md` | Stage 2 runner | Scenario coverage audit |
| 15 | `15_pre_stage3_baseline.md` | Stage 3 runner | Pre-Stage 3 baseline snapshot |
| 16 | `16_regression_integrity.md` | Stage 3 runner | Regression test integrity check |
| 17 | `17_stage3_readiness.md` | Stage 3 runner | Stage 3 readiness assessment |
| 18 | `18_stage3_scenario_catalogue.md` | Stage 3 runner | Stage 3 scenario listing by group |
| 19 | `19_stage3_evidence_register.csv` | Stage 3 runner | Stage 3 per-scenario results |
| 20 | `20_stage3_component_summary.md` | Stage 3 runner | Stage 3 results by component |
| 21 | `21_stage3_findings.md` | Stage 3 runner | Stage 3 findings |
| 22 | `22_gate3_decisions.md` | Stage 3 runner | Gate 3 decision |
| 23 | `23_beta_readiness_stage3.md` | Stage 3 runner | Beta readiness after Stage 3 |
| 24 | `24_test_count_audit.md` | Manual | RW-AUDIT-001: test count reconciliation |
| 25 | `25_stage4_scenario_catalogue.md` | Stage 4 runner | Stage 4 scenario listing by group |
| 26 | `26_stage4_evidence_register.csv` | Stage 4 runner | Stage 4 per-scenario results |
| 27 | `27_stage4_component_summary.md` | Stage 4 runner | Stage 4 results by component, invariant checklist |
| 28 | `28_stage4_findings.md` | Stage 4 runner | Stage 4 findings |
| 29 | `29_final_gate_decision.md` | Stage 4 runner | Final Gate decision and certification |
| 30 | `30_beta_readiness_final.md` | Stage 4 runner | Final beta readiness assessment |
| 31 | `31_assurance_certificate.md` | Manual | External-facing assurance certificate |
| 32 | `32_initiative_summary.md` | Manual | Permanent historical record of Initiative 001 |
| 33 | `33_user_manual.md` | Manual | This document |

---

*Reserved West Initiative 001 — Document 33 — First draft — 2026-08-07*
