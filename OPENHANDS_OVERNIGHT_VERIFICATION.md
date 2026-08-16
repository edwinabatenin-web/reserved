> **⚠ SUPERSEDED — historical verification snapshot.**
> Produced 2026-08-14 at commit `dd08b48` on `main`, before the
> `remediation/assurance-drift` remediation.  `reserved_west/reference_calculator.py`
> (described below as "independent") is now classified as historical /
> shared-lineage regression evidence and is excluded from the current independent
> RW3 accuracy corpus — do not treat it, or this harness description, as current
> independent accuracy evidence.  The body below is preserved unchanged as a
> historical output report.

# Reserved — Overnight Repository-Wide Verification Report

Date: 2026-08-14 (UTC)
Author: OpenHands (independent read-only verification pass)
Scope: whole repository (`/workspace`)

---

## 1. Executive summary

The primary test suite passes cleanly: **995 passed + 7 unittest subtests passed, 0 failures, 0 errors, 0 skipped** in ~4.6 s. Two additional, separately-configured verification suites **fail**, and both failures are caused by stale expected values in *assurance/reference* artefacts rather than by defects in the production engine:

- `reserved-engine-2.0.0/tests/` — **21 failures** (165 collected). The bundle engine was corrected to the v3.0.0 `£37,700` basic-rate-band model, but its own tests still assert the old `£50,270`-ceiling values.
- `reserved-optimise-assurance/tests/` — **7 failures** (136 collected). Two are stale PA-taper/pension expected values (old `£50,270` model); five are HICBC rounding/Child-Benefit-rate drift between the assurance reference and the product.

In addition, the bundled engine copy `reserved-engine-2.0.0/reserved_engine` diverges from production on student-loan behaviour (fail-open on simultaneous/unknown plans, no whole-pound flooring, no `student_loan_basis`) while declaring `ENGINE_VERSION = "3.0.0"`. This bundle is what the Reserved West assurance harness and the root `tests/test_el003_regression.py` actually exercise.

No production source, tests, fixtures, assurance/reference code, documentation, configuration, or Git history was modified. The only repository change is this report.

---

## 2. Exact baseline commit

- Commit SHA: `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb`
- Subject: `Baseline before OpenHands DeepSeek audit`
- Branch: `main`
- Initial working tree: **clean** (`nothing to commit, working tree clean`)

---

## 3. Environment details

- OS: Linux (container hostname `d63b7cb858e0`)
- Interpreter: Python `3.13.14` (`/usr/local/bin/python3`)
- pip: `26.1.2`; `uv` `0.11.24` also present (not used for installs)
- Isolated venv: `/tmp/reserved-venv` (created fresh; kept outside the repo to avoid polluting the working tree)

Installed (from `requirements.txt` + `pytest`):

| Package | Version |
|---|---|
| Flask | 3.1.1 |
| Flask-WTF | 1.2.2 |
| gunicorn | 23.0.0 |
| PyJWT | 2.13.0 |
| cryptography | 50.0.0 |
| requests | 2.34.2 |
| WTForms | 3.2.2 |
| pytest | 9.1.1 |

No external provider API calls were made. No secrets were read or emitted.

---

## 4. Officially configured commands (identified)

**Test commands (declared):**

- Root suite: `python -m pytest` / `python -m pytest -q` — `pyproject.toml` sets `testpaths = ["tests"]`, `addopts = "-q --tb=short"`.
- Engine-only subset: `python -m pytest -m engine` (marker declared in `pyproject.toml`).
- Reproduction steps in `RESERVED_NEW_AGENT_HANDOVER.md`:
  `python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest -q`

**Additional configured verification:**

- `reserved-engine-2.0.0/` — its own `pyproject.toml` (`testpaths = ["tests"]`); a second, independent test suite for the bundled engine.
- `reserved-optimise-assurance/` — `pytest.ini` + `conftest.py`; gate tests run as:
  `PYTHONPATH=reserved-optimise-assurance:. pytest reserved-optimise-assurance/tests/ -v`
- `reserved_west/literal_fixture_runner.py` — formula-free fixture runner for the RW3 fixture corpus (`docs/fixtures/WP7_ASSURANCE_CORPUS.json`); exercised by `tests/test_literal_fixture_runner.py`.
- `reserved_west/run_assurance.py` / `run_stage2.py` / `run_stage3.py` / `run_stage4.py` — Reserved West assurance harness entry points. **Not executed directly** because they write deliverables under `reserved_west/output/` (tracked files). Their comparison logic was executed in-memory instead (see §6).
- `scripts/generate_assurance_metadata.py` — CI-gate-style wrapper that runs pytest and writes `reserved/assurance_metadata.json` (a tracked file). **Not executed** to avoid modifying a tracked file.

**Formatting / linting / type-checking / static analysis:**

- `[tool.ruff] line-length = 100` is present in both `pyproject.toml` files, but **`ruff` is not declared as a dependency and no lint command is documented**. No `ruff.toml`, `.flake8`, `.pylintrc`, or CI workflow exists.
- **No type-checker is configured** (no `mypy`/`pyright`/`pytype` config or command).
- **No CI configuration** exists (no `.github/`, no GitLab/Bitbucket pipelines, no `tox.ini`/`Makefile`).

Net: formatting/linting/type-checking/static-analysis are **configured as metadata fragments only** and are not executable as configured.

---

## 5. Commands and results

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `git rev-parse HEAD` | 0 | `dd08b48…` |
| 2 | `python3 -m venv /tmp/reserved-venv` | 0 | venv created |
| 3 | `pip install -r requirements.txt pytest` | 0 | deps installed |
| 4 | `python -m pytest -q` (root, run 1) | 0 | all pass |
| 5 | `python -m pytest -ra --tb=short -p no:cacheprovider` (root, run 2) | 0 | 995 passed + 7 subtests passed |
| 6 | `python -m pytest -q -p no:cacheprovider` (bundle) | 1 | 21 failed / 165 collected |
| 7 | `PYTHONPATH=reserved-optimise-assurance:. pytest reserved-optimise-assurance/tests/ -v -p no:cacheprovider` | 1 | 7 failed / 129 passed / 136 collected |
| 8 | Reserved West harness (in-memory, `-B`) | 0 | 292 scenarios, 2 `UNSUPPORTED_EXPECTED` (expected) |
| 9 | Bundle student-loan recheck (in-memory, `-B`) | 0 | divergence confirmed (see §7) |

`-B` (no bytecode) and `-p no:cacheprovider` were used for the verification runs to keep the working tree clean.

---

## 6. Complete test-suite outcome

### 6.1 Primary suite — `tests/` (root)

- Result: **995 passed, 7 subtests passed** in 4.63 s
- Failures: 0 · Errors: 0 · Skipped: 0 · Xfails: 0
- Warnings: none reported (no pytest "warnings summary" section)
- Exit code: 0

### 6.2 Bundled engine suite — `reserved-engine-2.0.0/tests/`

- Result: **144 passed, 21 failed** (165 collected) — exit code 1
- All 21 failures are `AssertionError` on stale expected values (old `£50,270`-as-band-ceiling model). Representative failures:

| Test | Expected (stale) | Actual (correct) |
|---|---|---|
| `test_el001_case_a_99k_to_104k` | 2400.00 | 2800.00 |
| `test_el001_case_c_122k_to_132k` | 4657.00 | 4971.00 |
| `test_pa_fully_tapered_at_art` | 40002.00 | 42516.00 |
| `test_it_invoice_crossing_art` | 4757.00 | 5271.00 |
| `TestEL003CoreCase::test_rws3_011_income_tax` | 2215.00 | 1000.00 |
| `TestEL003AdditionalRateRestored::test_additional_rate_non_zero_above_art` | 4500.00 | 4060.50 |

### 6.3 Optimise assurance suite — `reserved-optimise-assurance/tests/`

- Result: **129 passed, 7 failed** (136 collected) — exit code 1
- Failure groups:
  - **PA-taper / pension stale expected values (2):** `test_it_saving_in_taper_zone` (expected 3000.00, actual 4000.00) and `test_el003_ebrl_cap_defect_not_reintroduced` (expected 58201.00, actual 59046.50). Both use the superseded `£50,270` model.
  - **HICBC reference drift (5):** `test_position_hicbc_matches`, `test_product_matches_reference_at_70k`, `test_product_hicbc_matches_reference`, `test_full_hicbc_elimination`, `test_hicbc_reduction_matches_reference`. The assurance reference (`reference/common.py::hicbc_ref`) rounds to the penny and uses Child-Benefit weekly rates `£26.60/£17.60`, whereas the product uses staged whole-pound rounding (ITEPA 2003 s.681C(3)) and `£27.05/£17.90` — the latter matching the approved `RW3-HICBC-*` fixtures.

### 6.4 Reserved West harness (executed in-memory, read-only)

The harness compares the bundled engine against `reserved_west/reference_calculator.py`.

| Stage | Scenarios | PASS | Other |
|---|---|---|---|
| Stage 1 | 30 | 30 | — |
| Stage 2 | 150 | 149 | 1 `UNSUPPORTED_EXPECTED` (RW-S2-136) |
| Stage 3 | 80 | 80 | — |
| Stage 4 | 32 | 31 | 1 `UNSUPPORTED_EXPECTED` (RW-S4-027) |

`UNSUPPORTED_EXPECTED` is a recognised, expected outcome in the harness, not a failure.

---

## 7. Confirmed defects

### D1 — `reserved-engine-2.0.0/tests/` is stale and red (21 failures)
The bundle's `income_tax.py` applies the corrected `£37,700` basic-rate band, but the bundle's own test files still assert the superseded `£50,270`-ceiling values. The bundle's own test gate therefore fails. Evidence: §6.2 (all 21 failures are stale-value `AssertionError`s; the "actual" values match production and the approved `RW3-IT-*` fixtures).

### D2 — `reserved-optimise-assurance` reference/tests are stale (7 failures)
Two independent drifts:
1. Gate tests `gate1::test_it_saving_in_taper_zone` and `gate4::test_el003_ebrl_cap_defect_not_reintroduced` hard-code expected values from the superseded `£50,270` model, even though their reference `common.py::income_tax_total_ref` already uses `£37,700`.
2. The HICBC reference (`common.py::hicbc_ref` + `reference/hicbc_reference.py` CB rates `£26.60/£17.60`) has not been updated to the product's staged whole-pound rounding and `£27.05/£17.90` rates. Evidence: §6.3, and approved fixtures `RW3-HICBC-004/005/006/012/013`.

### D3 — Bundled engine diverges from production on student loans (fail-open)
`reserved-engine-2.0.0/reserved_engine/income_tax.py` lacks `UnsupportedStudentLoanPlanCombination`, whole-pound (`ROUND_FLOOR`) annual-SA flooring, and the `student_loan_basis` field, while `__init__.py` reports `ENGINE_VERSION = "3.0.0"`. Confirmed this session:

- `student_loan_plans=[1, 2]` → `student_loan=2134.35` (charges both plans; production raises fail-closed).
- `student_loan_plans=["mystery"]` → `student_loan=0.00` (silently drops unknown plan; production raises).
- `student_loan_plans=[2]`, invoice `29386` → `student_loan=0.09` (penny; production returns `0.00` whole-pound floor).
- No `student_loan_basis` field emitted.

This violates the founder decision in `FOUNDER_DECISIONS.md` ("no loan amount … may be shown" for simultaneous/unknown plans). The bundle is what `reserved_west/runner.py`, `reserved_west/run_assurance.py`, and root `tests/test_el003_regression.py` import and exercise, so the assurance harness and one regression test are validating a stale, fail-open copy.

---

## 8. Suspected defects requiring reproduction

### S1 — `scripts/generate_assurance_metadata.py` result parsing is fragile
The script parses the pytest summary line with a hand-rolled regex and a fallback word-scan. It was **not executed** (it writes the tracked `reserved/assurance_metadata.json`). Against pytest 9.x the parsing may mis-handle the `"N passed, M failed"` / `"N passed, M subtests passed"` format and the `addopts = "-q --tb=short"` quiet output. *Confirm by running it in a throwaway copy and comparing `test_counts` to the real totals.*

### S2 — `annual_income_tax` fixture adapter has no Python wiring
`docs/fixtures/RW3_CORE_FIXTURES.json` fixtures reference `"adapter": "annual_income_tax"`, but no Python mapping from that adapter name to `reserved.engines.income_tax._total_income_tax` exists anywhere in the repo. `literal_fixture_runner.compare_fixture` returns `ERROR: No adapter` unless an external caller supplies the adapter dict. *Confirm by locating the intended adapter registry or documenting it as an external harness contract.*

---

## 9. Rejected false positives

- The **production** engine's income-tax band model (`£37,700` basic band; higher to `£125,140`; 45 % above) is correct and matches `RW3-IT-001…011` and `test_pa_taper_band_regression.py`. The `£50,270`-as-band-ceiling defect is genuinely resolved in production.
- The **production** HICBC staged whole-pound rounding and `£27.05/£17.90` Child-Benefit rates are correct and match `RW3-HICBC-*`. The penny/`26.60` behaviour is the stale reference, not the product.
- The **production** student-loan fail-closed and whole-pound flooring are correct and match `RW3-SL-*` and the founder decision.
- The **Reserved West** `UNSUPPORTED_EXPECTED` outcomes (RW-S2-136, RW-S4-027) are expected harness states, not defects.
- No provider/network failures were encountered (no network calls made).

---

## 10. Environmental blockers

- No CI, lint runner, type-checker, or formatter is actually installed/executable; `[tool.ruff]` and the handover reproduction command are the only guidance. This is a tooling gap, not a test failure.
- `reserved_west/run_assurance.py` and `scripts/generate_assurance_metadata.py` were deliberately not run because they write tracked files (`reserved_west/output/*`, `reserved/assurance_metadata.json`).
- No provider sandbox credentials or network access were used (and none are present in this copy), so no external journeys were attempted.

---

## 11. Untested / weakly tested launch-critical paths

1. **Provider sandbox end-to-end journeys** — HMRC PAYE/MTD, FreeAgent, Xero, QuickBooks, Yapily AIS, Google/Apple sign-in. All provider definitions remain `configured_not_implemented` and network-disabled; there are no live sandbox tests, only contract/boundary tests (`test_provider_http_boundary.py`, `test_provider_readiness.py`, `test_freeagent_oauth_contract.py`, `test_oauth_contracts.py`). This is the largest launch-evidence gap (per `EXTERNAL_DEPENDENCIES.md`).
2. **Bundle↔production consistency** — no test asserts that `reserved-engine-2.0.0/reserved_engine` and `reserved/engines` agree on student-loan fail-closed/flooring behaviour. The two have silently diverged (D3).
3. **`reserved-optimise-assurance` reference drift** — the reference calculators are not gated against the approved RW3 fixtures, so they can (and did) drift from the product without the root suite noticing.
4. **`annual_income_tax` fixture execution** — the RW3 income-tax fixtures cannot be run end-to-end in-repo (S2).
5. **`scripts/generate_assurance_metadata.py`** — the metadata gate is unverified in the current pytest version (S1).
6. **Manual/browser evidence** — authentication, session/cookie/CSP headers, responsive layouts, keyboard/screen-reader, contrast, error paths, provider redirects remain outstanding (noted in `RESERVED_NEW_AGENT_HANDOVER.md` §9).

---

## 12. Files likely to require changes (if remediated)

- `reserved-engine-2.0.0/tests/test_income_tax.py`, `test_income_tax_boundaries.py`, `test_el001_regression.py`, `test_el003_regression.py` — update stale expected values to the corrected `£37,700` model (D1).
- `reserved-engine-2.0.0/reserved_engine/income_tax.py` and `tax_config.py` — add fail-closed student-loan handling, whole-pound flooring, `student_loan_basis`, and correct `rules_version`, **or** delete the bundle and repoint the harness at `reserved.engines` (D3).
- `reserved_west/runner.py`, `run_assurance.py`, `run_stage2.py`, `run_stage3.py`, `run_stage4.py`, and root `tests/test_el003_regression.py` — repoint imports from the bundle to `reserved.engines` if the single-source-of-truth route is chosen (D3).
- `reserved-optimise-assurance/reference/hicbc_reference.py`, `reference/common.py`, and the gate tests `gate1_isolation.py`, `gate2_archetypes.py`, `gate3_interactions.py`, `gate4_extremes.py` — align HICBC rounding/rates and the two PA/pension expected values with production and RW3 fixtures (D2).
- `scripts/generate_assurance_metadata.py` — if retained, make result parsing robust against current pytest summary output (S1).
- Adapter wiring for `"annual_income_tax"` (S2) — document or implement.

---

## 13. Recommended remediation order

1. Resolve the bundle single-source-of-truth question (delete `reserved-engine-2.0.0` or fully sync it), because the assurance harness and one regression test currently validate a stale copy (D3 — highest impact, touches "unsupported states leak money").
2. Refresh the stale expected values in `reserved-engine-2.0.0/tests/` (D1) so its gate is green.
3. Re-align `reserved-optimise-assurance` HICBC reference and the two PA/pension gate expectations with production + RW3 fixtures (D2).
4. Add a bundle↔production parity test and wire the `annual_income_tax` adapter (S2).
5. Harden or retire `scripts/generate_assurance_metadata.py` (S1).
6. Schedule provider sandbox/manual evidence work separately (blocked on external credentials, not on this repo).

---

## 14. Founder decisions required

1. **Single source of truth for the engine.** Keep `reserved-engine-2.0.0` as a first-class (fully synced) artefact, or delete it and make `reserved.engines` the only engine the Reserved West harness and regression tests exercise?
2. **Assurance-reference ownership.** Should `reserved-optimise-assurance/reference/` and the RW3 fixture corpus be treated as authoritative and kept in lockstep with the product via a gate, or is drift acceptable as long as the root suite passes?
3. **HICBC rounding / Child-Benefit rate canonical values.** Confirm that staged whole-pound rounding (ITEPA 2003 s.681C(3)) and `£27.05/£17.90` weekly rates are the approved 2026/27 values (they match RW3 fixtures), superseding the assurance reference's `£26.60/£17.60` penny figures.
4. **Provider sandbox evidence** — confirm the roadmap/timeline for HMRC/FreeAgent/Xero/QuickBooks/Yapily/social sign-in sandbox completion, since this is the dominant remaining launch gap.

---

## 15. Final Git status

- Branch: `main`
- `git status --porcelain=v1`: empty
- `git status`: `nothing to commit, working tree clean`
- Commit unchanged: `dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb`

---

## 16. Confirmation of unchanged tracked files

No tracked file other than the new report (`OPENHANDS_OVERNIGHT_VERIFICATION.md`) changed. The working tree was clean at the start and clean at the end (post-report creation, only this untracked file is added). All verification used an isolated venv in `/tmp`, `-B` (no bytecode), and `-p no:cacheprovider` (no pytest cache), and no writing harness/script was executed.
