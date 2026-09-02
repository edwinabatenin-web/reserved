# W8-S3 — Geography admission evidence

## Status

`W8-S3 CORRECTED CANDIDATE — INDEPENDENT RE-REVIEW REQUIRED`

The fail-closed geography-admission boundary is implemented. The one stale
W8-S2 compatibility test that asserted the pre-fix silent-ignore behaviour now
requires the W8-S3 rejection. This package is a frozen four-path candidate for
fresh independent review; it is not yet an accepted checkpoint, integrated
assurance result or customer-launch claim.

## Starting identity

- Branch: `ohds/w8-s3-geography-admission`
- HEAD: `8eec5d8 Add W9 launch threat model and decision dossier`
- Working tree at start: clean.

## Consumers of `calculate_annual_position` enumerated

There is no production caller of `calculate_annual_position` in the repository.
Every direct caller is currently a test. Direct test consumers include the
integrated annual-position, pension, composition, internal snapshot, BPA,
HICBC, cash-ready, annual-to-cash and W8 assurance suites.

`reserved/api/routes.py` exposes only `/health`; it has no annual-position route
and does not import or call `calculate_annual_position`.
`reserved/engines/cash_ready_annual_position.py` consumes an already-produced
`AnnualPositionResult`; it does not call the annual calculator.
`reserved/engines/annual_loan_reconciliation.py` and
`reserved/engines/annual_loan_wp7u.py` operate on annual-loan result types and
are composed with annual-position results elsewhere; neither calls
`calculate_annual_position`.

No production or customer handoff supplies a geography fact today. The boundary
therefore preserves geography-free internal/test compatibility, but its absence
from a production handoff remains an explicit launch-evidence gap rather than
positive supported-nation evidence.

## Geography-like facts in provider/canonical contracts

- Provider canonical (`Account`/`CompanyInfoObservation` dataclasses):
  `country_code` (business address ISO country code) and `country`
  (country name). These are provider canonical fields, not the engine's
  `calculate_annual_position` fact vocabulary; they are not wired into the
  annual-position calculation.
- Provider wire level: FreeAgent company JSON exposes `country`
  (e.g. `"country": "GB"`). This is a whole-UK ISO-3166-1 umbrella code, not a
  supported-nation code, so under this boundary it is deliberately **not**
  positive supported-nation evidence.
- No `jurisdiction`, `territory` or `tax_regime` field exists in provider or
  canonical contracts today.

The five aliases enforced here (`jurisdiction`, `country`, `country_code`,
`territory`, `tax_regime`) come from the W8-S2 evidence cases, not from current
production contracts.

## Exact four-path candidate

1. `reserved/engines/integrated_annual_position.py` — 55 inserted lines:
   - `_GEOGRAPHY_ALIASES` (5 aliases).
   - `_GEOGRAPHY_NATION_ALIASES` (6 canonical spellings → 3 nations).
   - `_normalise_geography(raw)` — fail-closed single-fact normalisation.
   - `_enforce_geography_admission(facts)` — fail-closed multi-fact validation.
   - One call site inserted in `calculate_annual_position`, after the
     `tax_year` guard and before `get_config` / any arithmetic.
2. `tests/test_w8_geography_admission.py` — new adversarial geography suite.
3. `tests/test_w8_progressive_assurance_s2.py` — one mechanical compatibility
   update: the prior silent-ignore assertion now requires fail-closed rejection.
4. `docs/W8_S3_GEOGRAPHY_ADMISSION_EVIDENCE.md` — this evidence record.

Mechanical compatibility: the change is self-contained in the existing module
(small private helpers, no new imports), the call site is a single statement
placed before all arithmetic, the geography test and evidence files are
additive, and the existing W8-S2 test receives only the required assertion
inversion. No production consumer, provider mapping, route, template, tax rule
or Founder Decision is edited.

## Accepted vocabulary

Canonical supported nations and their bounded spellings/codes (whitespace- and
case-normalised):

| Canonical nation | Accepted spellings/codes |
| --- | --- |
| `england` | `England`, `GB-ENG` |
| `wales` | `Wales`, `GB-WLS` |
| `northern_ireland` | `Northern Ireland`, `GB-NIR` |

Accepted only when a fact resolves unambiguously to one of the three nations.

## Rejected vocabulary / inputs

Fail closed (raise `ValueError`) on:

- Scotland / Scottish / `GB-SCT` (any case).
- Ireland / Republic of Ireland / `IE` and any other non-UK jurisdiction.
- Unknown variants (e.g. `France`, `Germany`, `US`, `Channel Islands`,
  `Isle of Man`).
- Umbrella/ambiguous labels: `UK`, `GB`, `United Kingdom` (any case) — these are
  never treated as proof of a supported nation.
- Non-string values: booleans, numbers, containers (list/dict/tuple).
- Empty or whitespace-only strings.
- Missing text (a string that does not resolve to a supported nation).

## Contradiction and hostile-input behaviour

- Multiple supplied geography facts must resolve to the same canonical nation.
  Agreeing aliases (e.g. `country="England"` + `country_code="GB-ENG"`) pass.
  Cross-nation contradictions (e.g. `country="England"` +
  `country_code="GB-WLS"`) fail closed with a generic "conflicting geography"
  message.
- Supported/unsupported contradictions (e.g. `country="England"` +
  `territory="Scotland"`) fail closed.
- Rejected values are **never** echoed in exception messages or repr; both
  error paths use fixed, value-free messages.
- A `None` geography fact is treated as absent (not a positive claim and not a
  rejection), consistent with `dict.get` presence semantics and the requirement
  that absence must not invent geography for legacy/internal callers.

## Verification

- Focused geography plus W8-S2 compatibility suites: 86 passed.
- Affected annual-position, composition, BPA, HICBC, cash and student-loan
  matrix: 540 passed.
- `git diff --check` returns 0 (no whitespace errors).
- Bytecode/test caches disabled via `PYTHONDONTWRITEBYTECODE=1`, `-B`,
  `-p no:cacheprovider`.
- The full suite result is 4,514 passed, 12 failed and 84 errors (plus 7 passed
  subtests) from 4,610 collected tests. Artefact/release-gate tests account for
  11 failures and all 84 errors because their safety guard refuses to build
  from the intentionally uncommitted
  `reserved/engines/integrated_annual_position.py`; this is expected for an
  uncommitted engine candidate and is not treated as a pass.
- The full suite also exposes the unrelated package-local W9 guard
  `tests/test_w9_security_evidence.py::test_package_does_not_modify_readiness_release_config_or_source_files`,
  which is the remaining failure and rejects any working-tree path outside its
  own W9 package. No W9 path is changed under W8-S3 authority.

## File hashes (SHA-256)

- `reserved/engines/integrated_annual_position.py`:
  `3a5e20597bf953c533615a31a1d452fbe952effb8a0399dd8efbff1b3e0aa855`
- `tests/test_w8_geography_admission.py`:
  `536e13b17eba13cbbe85f30c5a504db6622c2832cb2430e5e191a9fcd505dcbe`
- `tests/test_w8_progressive_assurance_s2.py`:
  `e298588e0f8763e25b970c04296d2239fcff53d4d31bbd68a849f67ccb78909f`

The evidence-document hash, aggregate candidate-tree identity and complete-diff
identity are deliberately recorded by the fresh independent review rather than
inside this self-referential file.

## Remaining W8 geography-to-customer handoff evidence

No customer/provider path currently supplies a geography fact into
`calculate_annual_position`. Therefore the enforced boundary is correct and
fail-closed but **unexercised in production**. The remaining handoff obligation
is to prove, at customer-integration time, that a customer's supported nation
is captured and forwarded as a validated geography fact (or that scope is
explicitly confined to England/Wales/Northern Ireland) before any customer-facing
launch claim about supported nations is made. Absence of a geography fact is
**not** positive launch evidence and must not be presented as such.

Plan 4 remains a student-loan plan and is accepted by the existing
student-loan boundary (`estimate_incremental_liability`); it is not
misclassified as Scottish Income Tax evidence.
