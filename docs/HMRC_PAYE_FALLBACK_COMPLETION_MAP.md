# HMRC/PAYE fallback completion map

This map separates delivery states. Completion of an earlier row does not imply
integration, independent review, or launch readiness.

| Boundary | S1 implemented | Independently reviewed | Integrated | Launch-ready | Remaining owner/dependency |
|---|---:|---:|---:|---:|---|
| S1 structured capture/minimisation boundary | Yes | Yes | Yes | No | Privacy/security controls, usability and launch assurance remain |
| S2A extraction-confirmation contract (pure, network-inert) | Yes | Yes | Yes | No | Document-processing integration plus privacy/security controls remain |
| Upload, extraction, customer confirmation, and secure raw-document deletion | No | No | No | No | Document-processing integration plus privacy/security controls |
| Customer journey, persistence, replacement/deletion actions, structured retention, account deletion, and backups | No | No | No | No | Product, data, privacy, legal, and platform implementation |
| Independently reviewed usability of the payslip/manual journey | No | No | No | No | Representative journey implementation and independent usability evidence |
| HMRC source contract, adapter, production-access facts, and sandbox work | No | No | No | No | Exact externally gated API contract, access, credentials, eligibility, and sandbox validation |
| Integrated E2E, privacy, security, operations, and launch enablement | No | No | No | No | All preceding boundaries plus the applicable launch-assurance gates |

## S1 boundary

S1 is a pure, dependency-free typed value and normaliser. It validates only
customer-confirmed structured facts, maps document/manual provenance into the
existing `PayeEvidence` contract, and performs no I/O. It does not establish a
source order, calculate PAYE, forecast deductions or liability, infer refunds,
persist data, process documents, or activate a customer capability.

Every S1 item is marked `PARTIAL`. Founder-approved minimum completeness rules
for each document/source type remain validation-pending; S1 therefore does not
claim `COMPLETE_FOR_REPRESENTATION`. `PARTIAL` is both truthful and usable by
the unchanged reconciliation engine, whose existing uncertainty semantics
remain authoritative.

Supersession is an immutable reference from a new capture to an earlier
evidence ID. Nothing is mutated or deleted. Secure original-document deletion,
structured-data retention, customer deletion, account deletion, and backup
behaviour remain later integration/privacy gates.

## S2A boundary

S2A is a pure, dependency-free, network-inert extraction-confirmation contract.
It accepts a typed payslip extraction candidate and exactly one explicit
accept-or-correct decision per customer-confirmable field, then returns an
immutable, redacted result carrying the S1-compatible `PayeEvidenceCapture`
(source `SOURCE_DOCUMENT`, document type `PAYSLIP`, normalised completeness
`PARTIAL`), exact candidate/confirmation digests, the confirmation ID, and the
fixed `secure_deletion_required` disposition.

It never reads, writes, uploads, persists, logs, or deletes anything, and it
never claims the raw document was deleted. P45 and P60 fail closed. Upload,
OCR/extraction, confirmation UI, persistence, retention/deletion execution,
and launch assurance remain later integration/privacy gates.

Independent exact-diff review, focused correction and post-checkpoint
verification accepted this boundary at source checkpoint
`eb419a065afed8f961d037230b5cfe1bb6379b61`. It is integrated on the isolated
local integration lineage at
`af5df09004b3202d77fca0ffa7e74d51268882d6`. That integration passed the
affected PAYE/consumer tests, refreshed canonical release gate and complete
repository suite. Neither checkpoint is merged to main, pushed, released,
deployed, activated or launch-ready.
