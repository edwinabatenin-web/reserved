# Reserved v1 — final handover to the new independent reviewing agent

**Status:** ready to provide to the new reviewing agent  
**Prepared:** 13 August 2026  
**Repository:** sanitised local working copy; no secrets or populated customer database  
**Important:** handover readiness is not launch approval or feature completeness

## 1. Purpose and independence

This document gives a new independent agent enough context to understand and
challenge Reserved and the evidence accumulated during the readiness sprint.
It does not prescribe a review method, limit enquiry to known risks, or ask the
agent to confirm previous conclusions. This is not an official audit,
certification or formal assurance engagement. The agent should inspect any architecture,
calculation, assumption, claim, control or evidence it considers relevant.

Previous findings and recommendations are inputs, not instructions. The agent
should substantiate issues, likely consequences and materiality where possible.
Founder decisions may then remediate a valid finding, address it differently,
accept it as residual risk, defer it, or reject it as immaterial for the stated
purpose. Adequacy-for-purpose and proportional materiality guide launch
decisions; they must not restrict what the reviewing agent investigates or reports.

Deterministic tax arithmetic is not relaxed by the uncertainty framework. Where
facts and rules are known, the calculation must be correct. Input uncertainty,
source quality and product-policy limitations must not be disguised as arithmetic
certainty.

## 2. Product and confirmed scope

Reserved is a UK fintech/tax-technology product by Whip Smart Technologies Ltd.
It aims to build an evolving estimate of a user's tax position and estimated
amount to set aside. It must use factual, neutral language and does not provide
regulated financial or investment advice.

Confirmed v1 tax scope:

- England, Wales and Northern Ireland Income Tax;
- PAYE and multiple employments;
- sole-trade income, savings and dividends;
- UK and foreign property within the implemented limitations;
- student and postgraduate loans, including bounded reconciliation; and
- MTD readiness, not full MTD filing.

Post-v1 or disabled: High Income Child Benefit Charge (HICBC), Scottish Income
Tax, Capital Gains Tax and full MTD filing.
Money movement is not yet implemented. Founder decision (15 August 2026): v1
includes customer-authorised payment initiation (PIS) from the customer's
current account to a designated account owned by that customer; no money moves
without the customer's explicit approval and bank authentication, and Reserved
does not hold customer funds. Sweeping VRP and other automatic transfers are
post-v1. Implementation remains conditional on acceptable Yapily commercials,
exact consent and status handling, same-owner destination controls, security
review and launch assurance. Founder Decision `FD-W10-001` (2 September 2026)
now establishes a paid October subscription model with initial customer-facing
prices of £29 monthly, £156 for six months and £288 per year, inclusive of VAT
where applicable, with special discounts and offers supported. Those placeholder
launch prices may be changed by a later Founder Decision; subordinate billing
policies remain separately gated.

## 3. Current handover position

Established current evidence:

- **995/995 local tests pass** in an isolated environment created from pinned
  repository requirements.
- Reserved West's repaired methodology is fit. The integrity-controlled corpus
  contains 107 admitted fixtures: 104 independently approved and three pending.
- WP7 has a **scoped pass** for at most one undergraduate loan plan plus optional
  postgraduate loan. The three simultaneous-undergraduate arithmetic candidates
  remain pending, excluded and contribute no accuracy evidence.
- Integrated annual position passes for its declared bounded internal purpose.
- Annual Plan 2/PGL reconciliation and its WP7U evidence/uncertainty mapping pass
  for bounded internal purposes.
- Annual-position composition and snapshot contracts pass only for bounded
  ephemeral internal linking/handoff.
- Internal calculation components are not connected to persistence, public API,
  customer presentation or reserve guidance; regression tripwires protect that
  boundary.
- The provider boundary is reviewable as an intentionally incomplete, disabled
  state. No provider has meaningful recorded end-to-end sandbox evidence.

These are prior conclusions supported by named records; the reviewing agent is free to
reject them after independent examination.

## 4. Unsupported simultaneous undergraduate plans

A final proportionate official-source search did not locate an explicit annual
Self Assessment rule selecting or allocating between simultaneous undergraduate
plan types. HMRC Tax Logic uses a singular plan type; explicit lowest-threshold
authority located during the sprint was payroll-specific and was not substituted
as annual-SA evidence.

Founder decision: v1 may calculate at most one undergraduate plan, optionally
plus PGL. Simultaneous undergraduate combinations and unknown plan values are
`unsupported_for_decision` and require verification.

Current implemented controls:

- direct estimator, dashboard, annual reconciliation and WP7U boundary fail closed;
- no loan amount, partial total, allocation, reserve or set-aside is emitted;
- exact supplied-plan provenance is retained;
- uncertainty effect is `NOT_DETERMINABLE`;
- rendered legacy and v2 surfaces state that no amount can be calculated and
  direct verification with HMRC or a qualified tax adviser is required; and
- unknown-only, mixed-known/unknown and simultaneous-known cases are distinct.

The three pending fixtures remain unchanged and integrity-checked. This scoped
treatment is not validation of their expected arithmetic. Future explicit HMRC
annual authority or controlled sandbox calculation evidence could reopen them.

## 5. Architecture and trust boundaries

- Flask/Python application under `reserved/`.
- Tax engines: `reserved/engines/`; versioned rules: `tax_config.py`.
- Web/API: `reserved/web/` and `reserved/api/`.
- Provider contracts/placeholders: `reserved/providers/`.
- Current independent fixture packs and integrity manifest: `docs/fixtures/`.
- Historical West implementation: `reserved_west/` and older assurance folders.

The newer integrated annual-position, loan-reconciliation, composition, WP7U
mapping and snapshot components are internal and purpose-limited. They are not
approved persistence schemas or public/customer contracts. A persistence review
found the existing `tax_calculations` stub unsuitable: it lacks the required
ownership, provenance, uncertainty, versioning, retention, integrity and audit
controls. Do not infer readiness from serialisability.

`docs/openapi.json` is an internal, unstable preview inventory. It is not a
public compatibility promise and does not evidence provider implementation.

## 6. Defect and assurance history

This history is included because it reveals failure patterns, not because it
defines all possible defect classes.

### Reserved West shared-lineage failure

Historical West appeared independent because code lived in separate files, but
its reference calculator copied important production concepts and formulas.
Production and oracle therefore agreed on wrong results. Historical certificate
`RW-001-CERT` and related engine 2.0.1 claims are superseded. Historical West
output is regression/consistency evidence only.

The adopted independence standard prohibits production helpers, West helpers,
shared formulas, copied configuration and engine-derived expected values in
validation-critical fixtures. Current literals must be independently derived,
provenance-bearing, reviewed and integrity-controlled.

### Material defects found and repaired

- **Personal Allowance/basic-band coordinate defect:** both production and the
  old oracle treated £50,270 as an absolute gross-income ceiling after PA taper.
  At £110,000 they returned £32,432 rather than £33,432. Root cause, correction
  and £99,999–£125,140+ regressions are recorded.
- **Earlier interval/taper defect:** an end-state PA was used across an income
  interval; corrected using before/after calculation.
- **Pension fixture error:** a £1 gross RaS/additional-rate expected value was 5p
  too high; independently corrected before promotion.
- **Student-loan semantics:** annual Self Assessment amounts floor to whole
  pounds. Payroll and annual-SA evidence were initially conflated. Multiple
  undergraduate treatment was later bounded as described above.
- **HICBC inputs and rounding:** stale Child Benefit rates were corrected. A late
  review then found that benefit must be floored before applying the whole
  percentage, followed by final charge flooring. The defect affected production,
  Optimise and independently approved fixtures. All three active paths and two
  99% fixtures were corrected and independently rechecked.
- **PAYE evidence policy:** early candidates effectively preferred HMRC by origin,
  conflated missing with zero, and lost conflict/staleness meaning. The approved
  policy has no unconditional source precedence and preserves provenance,
  representation, completeness, recency and material uncertainty.
- **WP9/WP7U mapping:** several apparently green implementations lost basis
  provenance, root failure states, configured recency, item-specific reasons or
  conflict-bound meaning. Adversarial review/remediation closed these before U2
  passed.
- **Customer claims:** “safe to spend”, “what is truly yours”, complete/full-year
  implications and unsupported independent-validation language were removed or
  deprecated. Legacy dashboard/Optimise copy now names its limited inputs and
  omissions.
- **Security/privacy/accessibility examples:** CSV formula injection, state-changing
  GET logout, fail-open Turnstile error handling, session-boundary weaknesses,
  raw identifier logging and dialog/tab/form accessibility gaps were remediated.

Do not assume repaired examples exhaust duplicate logic, source/period mismatch,
rounding-order, threshold-coordinate, evidence-loss, fail-open or misleading-copy
risks elsewhere.

## 7. Evidence hierarchy and important records

Governing/current:

- `docs/V1_TAX_SCOPE.md`
- `docs/WORK_PACKAGE_SEQUENCE.md`
- `docs/CLAUDE_AUDIT_GATE.md` (historical readiness-gate reasoning; despite its
  name, the planned activity is not an official audit)
- `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`
- `docs/WP7_SCOPED_GATE_REVIEW.md`
- `docs/ESTIMATE_UNCERTAINTY_STANDARD.md`
- `docs/ANNUAL_LOAN_WP7U_U2_ASSURANCE_REVIEW.md`
- `docs/INTEGRATED_ANNUAL_POSITION_ASSURANCE_REVIEW.md`
- `docs/INTERNAL_HICBC_SCENARIO_ASSURANCE_REVIEW.md`
- `docs/HICBC_ROUNDING_DEFECT.md`
- `docs/fixtures/WP7_FIXTURE_INTEGRITY.json`
- `FOUNDER_DECISIONS.md`
- `EXTERNAL_DEPENDENCIES.md`
- `SPRINT_LOG.md`
- `RESERVED_SPRINT_HANDOVER.md`

Provider/target evidence:

- `docs/PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md`
- `docs/LAUNCH_CANDIDATE_PROVIDER_TARGET_EVIDENCE.md`
- `docs/SANDBOX_E2E_EXECUTION_PACK.md`
- `docs/sandbox_evidence.schema.json`
- provider-specific implementation decision documents under `docs/`
- `docs/AUTHENTICATION_READINESS.md`

Useful history, not current independent accuracy proof:

- `reserved_west/reference_calculator.py`;
- historical `reserved_west/output/` certificates/registers;
- `reserved-optimise-assurance/reference/`; and
- production regressions sharing historical calculation lineage.

Historical documents may retain an original NOT FIT finding followed by a dated
supplemental PASS. Treat the latest explicit verdict as current, while preserving
earlier findings as review history. Any unresolved contradiction should itself be
reported.

## 8. Founder decisions versus findings

Resolved founder policy includes:

- confirmed v1 geographic/tax scope;
- no unconditional precedence for HMRC evidence;
- preserve material uncertainty and assess evidence fitness for its stated purpose;
- responsible-launch assurance rather than proof of theoretical completeness;
- simultaneous/unknown undergraduate-plan combinations are unsupported and
  verification-required instead of a general launch blocker.

Founder decisions still open include:

- execution of customer-authorised PIS remains conditional on acceptable
  Yapily commercials, exact consent/status handling, same-owner destination
  controls, security review and launch assurance;
- quantitative PAYE materiality, recency and completeness policies;
- final evidence-quality/conflict/possible-overpayment wording; and
- conditions for any future combined annual-liability/deduction presentation.

Resolved (15 August 2026): the customer-facing name for “Optimise” is
“Explore your options”; HICBC is outside the v1 customer scope (post-v1); and
customer-facing annual-period language uses “tax year”, not “period of
assessment”.

An independent finding does not automatically resolve these choices. Conversely, a
founder scope decision does not establish arithmetic correctness or control
effectiveness.

## 9. What has not been demonstrated

### Provider sandboxes

No synthetic end-to-end journey has been completed for HMRC, FreeAgent, Xero,
QuickBooks, Yapily AIS, Google sign-in or Apple sign-in. All five financial-data
provider definitions remain `configured_not_implemented` and network-disabled.
Credentials reportedly exist in Replit Secrets but are absent from this copy and
must never be pasted into chat or committed.

The sanitised workspace cannot safely execute these journeys. Exact prerequisites
and evidence capture are in `docs/LAUNCH_CANDIDATE_PROVIDER_TARGET_EVIDENCE.md`.
Fixture/demo success is not provider evidence. Payment initiation is disabled.

### Target environment and manual testing

The 995-test suite has not been repeated in the intended Replit runtime. Manual
browser evidence is outstanding for authentication, session/cookie/cache headers,
responsive layouts, keyboard/screen-reader behaviour, contrast, error paths and
provider redirects. CSP still relies on inline allowances in the current
architecture. Processor/transfer disclosures and deployed log/retention behaviour
require operational/legal confirmation.

These are launch-evidence gaps, not evidence of failure. They must not be marked
passed without retained results from the actual environment.

## 10. Reproduction and handling instructions

From the sanitised repository root:

```text
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

The local sprint used an isolated temporary environment because the host Python
initially lacked Flask/pytest. Record interpreter version, dependency resolution,
test count, failures, duration and environment when repeating in Replit.

Do not access production customer data, live HMRC or bank accounts, initiate
payments, change production credentials or deploy to production. Sandbox testing
must use synthetic users/companies/accounts and redacted evidence conforming to
`docs/sandbox_evidence.schema.json`.

Git CLI was unavailable on the preparation host because Apple command-line tools
were absent. Before review, the recipient should receive a stable copy/archive or
commit identifier generated in an environment where repository tooling works.

## 11. Freedom to review and useful challenges

The following are context, not a required checklist:

- challenge fixture independence and source applicability;
- search for duplicate calculations and inconsistent rounding/threshold logic;
- distinguish income-year, evidence-period, payroll and annual-SA semantics;
- test missing, stale, conflicting, duplicate and omitted evidence;
- test whether unsupported states can leak partial money through alternate routes;
- inspect foreign-property/FTCR, finance-cost, residence and ownership boundaries;
- inspect auth, account linking, tenant isolation, persistence and deletion;
- verify customer wording against actual calculation scope; and
- question whether purpose-limited internal passes justify any proposed launch use.

The agent should pursue other lines of enquiry it considers more important.

## 12. Handover judgement

The handover is adequate for the new independent reviewing agent. The repository is not declared
feature-complete or production-ready. Remaining known gaps are explicit enough
for an independent agent to assess the launch candidate without further
builder-led development first. The appropriate next activity is independent
review, followed by founder triage, remediation or residual-risk decisions, then
provider/target/manual launch evidence and the final launch gate. This handover
does not confer an auditor role or imply a formal audit opinion.
