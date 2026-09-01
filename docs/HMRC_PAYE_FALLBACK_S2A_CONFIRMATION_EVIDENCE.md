# HMRC/PAYE fallback S2A confirmation evidence

Date: 1 September 2026
Status: uncommitted engineering candidate; not independently reviewed, integrated, or launch-approved

## Boundary and local authority

S2A implements a pure, network-inert extraction-confirmation boundary between an
untrusted structured payslip extraction candidate and an explicit
customer-confirmed `PayeEvidenceCapture`. The local sources used were:

- `FOUNDER_DECISIONS.md`: PAYE current-position proposition, temporary payslip
  processing/minimisation (secure raw-document deletion after extraction and
  check), and the validation-pending PAYE evidence operating parameters;
- `reserved/engines/paye_evidence_capture.py` (S1) and
  `tests/test_paye_evidence_capture.py`;
- `reserved/engines/paye_reconciliation.py` and
  `tests/test_paye_reconciliation.py`;
- `docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` and
  `docs/HMRC_PAYE_FALLBACK_S1_EVIDENCE.md`.

No network source, provider, SDK, credential, production datum, or external
tool was used. No S1 capture/reconciliation contract, provider code,
route/template, persistence, fixture, Founder Decision, configuration,
credential, or integration metadata was modified.

## Encoded facts and conservative decisions

The candidate accepts only structured, bounded, exact-runtime-type fields and
rejects raw bytes, OCR/raw text, paths, NINO, bank/provider account identifiers,
credentials, tokens, and arbitrary metadata. The only allowed identifiers are the
enumerated opaque candidate ID, document ID, evidence ID, employment ID,
confirmation ID, and optional supersession reference; every identifier is
redacted from errors and `repr`.

The candidate digest hashes only the immutable candidate and every retained
presence/absence state. A separate confirmation digest hashes the candidate
digest plus the exact per-field decisions, corrected values, confirmation ID,
the fixed `secure_deletion_required` disposition, and its own domain/schema
version. A supplied candidate-digest mismatch is rejected. Canonicalisation uses
a fixed field order, domain/schema tag, exact enum values, ISO dates, canonical
two-decimal money, explicit missing tags distinct from exact zero, and
length-prefixed encoding produced only after exact-type validation. It never
invokes attacker-controlled string, numeric, equality, or hashing hooks.

Exactly one explicit accept-or-correct decision is required for each of the nine
customer-confirmable fields: `tax_year`, `employment_id`, `gross_pay_to_date`,
`tax_paid_to_date`, `tax_code`, `pay_frequency`, `pension_treatment`,
`effective_through`, and `observed_on`. Corrections pass the existing S1
validators. Candidate ID, document ID, evidence ID, `SOURCE_DOCUMENT`, `PAYSLIP`,
candidate digest, confirmation ID, and any retained supersession reference are
bound but not customer-correctable. Unknown, duplicate, missing, and
system-field-targeting decisions fail closed. P45 and P60 fail closed.

For one-candidate/one-confirmation semantics the contract accepts only an exact
`frozenset[str]` of previously consumed candidate digests, validates every member
as lowercase hexadecimal SHA-256, and rejects the current candidate digest when
present. This is honest replay protection only; it claims no persistence or
universal prevention.

The result states `secure_deletion_required` and never states or implies that the
raw document was deleted. It exposes no deletion function, file operation, path,
upload, OCR, persistence, logging, or I/O. The only successful output is an
in-memory S1-compatible `PayeEvidenceCapture` whose source is `SOURCE_DOCUMENT`,
document type is exactly `PAYSLIP`, and normalised completeness is
`Completeness.PARTIAL`.

## Fail-closed corrections in this revision

The candidate was hardened at three independently identified fail-closed
boundaries without redesigning S1, reconciliation, persistence, upload/OCR,
deletion execution, UI, or providers.

1. **Public construction boundary.** A successful
   `PayeExtractionConfirmation` is producible only by the validated
   `confirm_paye_extraction` path. Direct public construction always raises;
   `dataclasses.replace` cannot forge or splice a result; `copy`/`deepcopy`
   return the same deeply immutable instance; and pickling is explicitly
   disabled. This does not protect against deliberate `object.__new__` or
   private-implementation import by malicious code.
2. **`FieldDecision` validates at construction.** For `Decision.CORRECT`, the
   corrected value is validated against its exact `FieldName` and normalised
   immediately; arbitrary objects and hostile subclasses are rejected without
   being retained. `Decision.ACCEPT` cannot carry a corrected value, and `None`
   is permitted only where the S1 contract permits absence. Errors are constant
   and non-echoing. The already-normalised value is revalidated during final
   confirmation as defence in depth.
3. **ASCII tax years and Reserved defensive numeric bounds.** Tax years must be
   exact ASCII `YYYY-YY` before canonical encoding, for both candidate and
   corrected values. Amounts pass a clearly labelled Reserved defensive
   magnitude/length bound before the inherited S1 validator; extreme integer,
   `Decimal` and string magnitudes are rejected before expensive conversion or
   quantisation while exact non-negative two-decimal S1 semantics are preserved.
   `consumed_candidate_digests` has a finite labelled maximum count. These are
   defensive resource limits, not HMRC or statutory amount limits.

## Tests run

All commands set `PYTHONDONTWRITEBYTECODE=1` and disabled the pytest cache with
`-p no:cacheprovider`. An existing local environment supplied pytest; nothing was
installed.

1. `tests/test_paye_extraction_confirmation.py`: **140 passed**.
2. `tests/test_paye_extraction_confirmation.py tests/test_paye_evidence_capture.py
   tests/test_paye_reconciliation.py`: **220 passed**. This directly checked the
   unchanged S1 capture and reconciliation consumers.
3. `tests/test_release_gate.py`: **29 passed, 1 failed**. The single failure is
   the existing artefact-assurance dirty-source guard refusing to build while
   `reserved/engines/paye_extraction_confirmation.py` is uncommitted. The task
   forbids commit and forbids changing that assurance system, so the guard was
   not bypassed.
4. Complete repository suite: **3,435 passed, 11 failed, 84 errors, 7 subtests
   passed**. All failures/errors are caused by the same dirty-source guard (the
   artefact/assurance/release-gate/RW3-gate/engine-adapter tests refuse to build
   from an uncommitted source). No failure or error originates in the new
   contract or in the S1/reconciliation suites.

## Limitations and residual gates

This evidence does not cover upload/OCR, extraction execution, confirmation UI,
persistence, retention/deletion execution, access controls, account deletion,
backup deletion, usability, HMRC contracts/adapters/sandbox/production access,
integrated E2E, privacy, security, operations, or launch enablement. It neither
calculates PAYE nor chooses evidence precedence. The contract performs no I/O
and never executes deletion; it only records that secure deletion is required.

Replay protection is limited to an in-memory `frozenset[str]` of previously
consumed candidate digests; persistence and universal one-time consumption are
out of scope for a pure function. Syntax validation of opaque identifiers does
not prove they did not originate in production. The full-suite dirty-tree guard
remains a bounded verification limitation until the authorised downstream
commit/review workflow can test the committed tree.

No new Founder decision is required for this pure conservative slice. Founder or
product validation is still required before approving source-specific minimum
completeness parameters and the deletion/retention integration behaviour.

## Changed paths and integrity

- `reserved/engines/paye_extraction_confirmation.py` —
  `ca707a270ef4462e6e4f0bec3abed569b5b550c21cefd6943dc2590a99a93d12`
- `tests/test_paye_extraction_confirmation.py` —
  `72862f92e69d884a9b0a078e26d25dff3f6a12a05e4f4e575af329763ad4de7e`
- `docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md` —
  `0b73d24598e65f2b9d10426fae308f1d108dc0e0df95003bba689d8e0e8740ba`
- `docs/HMRC_PAYE_FALLBACK_S2A_CONFIRMATION_EVIDENCE.md` — recorded in the
  completion report; a file cannot contain its own final SHA-256 without
  changing that value.

SHA-256 values are over the final file bytes. No stage, commit, merge, push,
release, deployment, or enablement was performed.
