# HMRC/PAYE fallback S1 evidence

Date: 1 September 2026
Status: independently reviewed engineering candidate; not integrated or launch-approved

## Boundary and local authority

S1 implements a network-inert structured capture and normalisation boundary.
The local sources used were:

- `FOUNDER_DECISIONS.md`: resolved PAYE current-position proposition, October
  external-integration boundary, external-data freshness/completeness, PAYE
  evidence/uncertainty, temporary payslip processing/minimisation, and the
  validation-pending PAYE evidence operating parameters;
- `docs/HMRC_PAYE_RECONCILIATION.md`;
- `docs/RW3_PAYE_EVIDENCE_FORMAL_REVIEW.md`;
- `reserved/engines/paye_reconciliation.py` and
  `tests/test_paye_reconciliation.py`.

No network source, provider, SDK, credential, production datum, or external
tool was used.

## Encoded facts and conservative decisions

Encoded facts are: separate source-document and manual routes; payslip/P45/P60
document types; stable evidence and employment IDs; tax year; exact cumulative
gross pay and tax paid; tax code; pay frequency; explicit pension/salary-
sacrifice treatment including unknown; effective and observation dates;
optional immutable supersession reference; document/manual provenance mapping;
and employment-cumulative representation.

The conservative implementation decision is `Completeness.PARTIAL` for every
normalised item. Minimum source-specific completeness parameters still require
validation, so S1 makes no `COMPLETE_FOR_REPRESENTATION` claim. This preserves
truthful uncertainty while remaining compatible with the existing consumer.
Source reference is a bounded category (`customer_confirmed:<document-type>` or
`customer_confirmed:structured_manual`), not a production identifier.

The boundary rejects raw bytes/text, paths, credentials, NINOs, bank data and
production identifiers by having no fields for them and by rejecting extra
constructor arguments. It rejects unsupported source shapes, wrong runtime
enum/date types, blank/ambiguous identifiers, booleans, floats, non-finite or
negative money, ambiguous numeric strings, and precision beyond two decimal
places. Missing remains `None`; exact zero becomes `Decimal("0.00")`.

## Tests run

All commands set `PYTHONDONTWRITEBYTECODE=1` and disabled the pytest cache with
`-p no:cacheprovider`. An existing local virtual environment supplied pytest;
nothing was installed.

1. `tests/test_paye_evidence_capture.py`: **67 passed** after the focused
   independent-review correction added exact leading/trailing space, tab, and
   newline tax-code regressions while preserving an accepted internal-space form.
2. `tests/test_paye_evidence_capture.py tests/test_paye_reconciliation.py`:
   **80 passed**. This directly checked the unchanged reconciliation consumer,
   including conflict retention, stale evidence, and apparent-overpayment
   behaviour.
3. Complete repository suite: **1,885 passed, 11 failed, 84 errors, 7 subtests
   passed**. All failures/errors were caused by the existing artefact-assurance
   dirty-source guard refusing to build while
   `reserved/engines/paye_evidence_capture.py` is uncommitted. The task forbids
   commit and changes to that assurance system, so the guard was not bypassed.

## Limitations and residual gates

This evidence does not cover upload/OCR, extraction, confirmation UI,
persistence, retention/deletion execution, access controls, account deletion,
backup deletion, usability, HMRC contracts/adapters/sandbox/production access,
integrated E2E, privacy, security, operations, or launch enablement. It neither
calculates PAYE nor chooses evidence precedence. The owning Codex reviewer
independently inspected the exact candidate, identified and routed one focused
correction for tax-code edge whitespace, and reran the 80 focused and unchanged
reconciliation-consumer tests. The full-suite dirty-tree guard remains a bounded
verification limitation until the authorised downstream commit/review workflow
can test the committed tree.

No new Founder decision is required for this pure conservative slice. Founder
or product validation is still required before approving source-specific
minimum completeness parameters.

## Changed paths and integrity

- `reserved/engines/paye_evidence_capture.py` —
  `f1e0a6830e20887768fee40e345f635d310ba65ca15142b49b647d8116c615e1`
- `tests/test_paye_evidence_capture.py` —
  `44b997f9e04e66410085e3d919a35565e5937a82f96c40e0cb0e05a32c38c622`
- `docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` —
  `3aff4381fa4daaa00fbf4d7a25bab3c0883f280702fb7058e5fd064aa90fe7be`
- `docs/HMRC_PAYE_FALLBACK_S1_EVIDENCE.md` — recorded in the completion report;
  a file cannot contain its own final SHA-256 without changing that value

SHA-256 values are over the final file bytes. No stage, commit, merge, push,
release, deployment, or enablement was performed.
