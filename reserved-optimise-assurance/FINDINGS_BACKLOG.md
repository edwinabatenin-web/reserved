# Initiative 002 — Findings Backlog

Findings are recorded here when test runs expose defects, divergences, or
open questions.  Each finding is assessed against the gate it affects and
tracked to resolution.

## Finding Status Codes

| Code | Meaning |
|---|---|
| OPEN | Active issue; gate cannot PASS |
| RESOLVED | Fix confirmed; test now passes |
| DEFERRED | Known limitation; documented in scope exclusions |
| WAIVED | Accepted as out-of-scope for this version |

---

## Open Findings

*None at time of writing.*

---

## Resolved Findings

*None at time of writing — tests run after initial implementation.*

---

## Deferred / Waived Findings

| ID | Finding | Status | Notes |
|---|---|---|---|
| F-001 | Gift Aid ANI interaction not modelled | DEFERRED | Planned for a future version; documented in OVERVIEW |
| F-002 | Scottish income tax excluded | WAIVED | Engine explicitly out of scope for Scotland; documented |
| F-003 | Tapered Annual Allowance not modelled | WAIVED | Constraint warning shown; not modelled; documented in caveats |
| F-004 | CB rates 2026/27 are approximate | DEFERRED | Rates uprated ~2% from 2025/26; must verify against HMRC announcement |
| F-005 | Carry-forward of unused AA not modelled | DEFERRED | Shown as constraint; not modelled; future enhancement |

---

## How to Add a Finding

1. Assign the next sequential ID (F-NNN).
2. Describe the finding (which gate, which scenario, what was observed vs expected).
3. Assess severity: BLOCK (gate cannot PASS), WARN (noted but gate may PASS), INFO.
4. Update when resolved: record the fix, re-run tests, move to RESOLVED.
