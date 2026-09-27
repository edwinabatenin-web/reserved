# HMRC/PAYE fallback completion map

This map separates delivery states. Completion of an earlier row does not imply
integration, independent review, or launch readiness.

| Boundary | S1 implemented | Independently reviewed | Integrated | Launch-ready | Remaining owner/dependency |
|---|---:|---:|---:|---:|---|
| S1 structured capture/minimisation boundary | Yes | Yes | Yes | No | Privacy/security controls, usability and launch assurance remain |
| S2A extraction-confirmation contract (pure, network-inert) | Yes | Yes | Yes | No | Document-processing integration plus privacy/security controls remain |
| PAYE reconciliation trust, explicit-policy issuance and authoritative projection | Yes | Yes | Yes | No | Integrated at `c23d343`; customer orchestration, persistence, UX/security evidence and launch assurance remain |
| Customer-safe PAYE reconciliation evidence presentation | Yes | Yes | Yes | No | Paid authenticated durable current-position route accepted at `c6f5e4a`; target UX/security evidence remains |
| Explicit-confirmed-period future-pay forecast composition (detached) | Yes | Yes | Yes | No | Authenticated owner/business orchestration, persistence, customer-safe presentation, full-period coverage and launch assurance remain |
| Authenticated paid durable confirmed-input forecast route | Yes | Yes | Yes | No | Product integration at `318fe2d`; evidence bindings refreshed at `4160155`; durable customer fact capture/update/supply, required-period/source coverage and target launch evidence remain |
| Authenticated manual multi-employment cumulative entry, durable replacement/deletion and partial review | Yes | Yes | Yes | No | Durable paid composition accepted at `c6f5e4a`; target custody, retention/backup, privacy/security and representative journey evidence remain |
| Upload, extraction, customer confirmation, and secure raw-document deletion | No | No | No | No | Document-processing integration plus privacy/security controls |
| Customer journey, persistence, replacement/deletion actions, structured retention, account deletion, and backups | Partial | Partial | Partial | No | Manual PAYE persistence/replacement/deletion exists; target retention, account deletion, backups and wider product evidence remain |
| Independently reviewed usability of the payslip/manual journey | No | No | No | No | Representative journey implementation and independent usability evidence |
| HMRC source contract, adapter, production-access facts, and sandbox work | No | No | No | No | Exact externally gated API contract, access, credentials, eligibility, and sandbox validation |
| Integrated E2E, privacy, security, operations, and launch enablement | No | No | No | No | All preceding boundaries plus the applicable launch-assurance gates |

The manual entry/review row records a sub-boundary of the broader customer
journey, not a new completion denominator or completion of that composite row.
The existing customer-journey/lifecycle row remains incomplete; it must not be
read as saying that no manual customer interface exists. The accepted paid
current-position route now invokes the durable reconciliation bridge, while raw
payslip upload/extraction remains outside the authorised manual October scope.

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

## Reconciliation trust and presentation sub-boundaries

The independently reviewed reconciliation trust boundary is integrated at
local checkpoint `c23d343032a3bfd94e8ba1bda45cc5361b3fff40`. It requires an
explicit factory-issued policy, validates source-neutral evidence, preserves
missing-versus-zero and aggregate anti-double-counting semantics, and exposes
closure-bound immutable projectors as the authoritative read surface. It does
not acquire evidence, set a universal operating policy, forecast payroll,
persist state, render customer copy or establish release readiness.

The presentation consumes only the captured authoritative
`project_paye_reconciliation` output from an exact live result. It validates
the current ordered projection, suppresses unsafe point values for bank
inference and conflicts, and renders fixed autoescaped customer HTML. It adds
no route, authentication, source orchestration, upload/deletion, persistence,
provider access, payment action, activation or launch claim. Fresh independent
review and controlled integration were completed at local
checkpoint `14cc0d8c6a3723c5b2e3c654103a71ea043ecc8b`. Its table state remains
not launch-ready because target UX/security evidence is still outstanding. The
later paid authenticated route composition is recorded below.

## Durable structured-manual PAYE composition — 27 September 2026

The exact integrated correction commit `c6f5e4ad36da8c37e946b7a0b5d9913f95e01b22`
binds the existing owner-scoped durable manual entries and admitted annual
position to `GET /v2/paye/current-position`. Installation requires the exact
active paid-access wrapper. The route uses only server-owned owner/business/year
scope and a producer-issued annual freshness horizon; missing, future or expired
evidence fails closed. The bounded response exposes status only and never raw
PAYE, payment, refund, liability or provider data.

Independent technical and security/privacy re-review both returned ACCEPT.
Focused PAYE/billing tests passed 24/24, followed by a clean canonical gate with
10,394 root tests plus all mandatory artefact, parity, RW3 and options checks.
This makes the local manual current-position path executable. The later
product integration at `318fe2d` makes the separately bounded future-pay composer
available through an authenticated paid route, but does not supply its durable
customer-confirmed facts or establish required-period/source coverage. Because
the canonical row combines evidence and forecasting, it remains
`not_executable`. The distinct structured-manual journey row advances to
`evidence_missing`; neither row is complete or launch-ready.

## Explicit-confirmed-period future-pay forecast boundary

The independently reviewed forecast composer is accepted at source checkpoint
`3496a31c1ebcfece7e81ee593301a7c2e9370460` and integrated on the isolated
local integration lineage at
`0c8de58ad2abfe9f600b29cc71fd9e1efa51bcdb`. Both commits have the exact tree
`8f2d8e103b4f60943cef89d0261766edc0761590`; the accepted three-path package is
`docs/PAYE_FUTURE_PAY_FORECAST_EVIDENCE.md`,
`reserved/services/paye_future_pay_forecast.py`, and
`tests/test_paye_future_pay_forecast.py`.

This is a detached composition boundary, not a payroll predictor. It combines
an exact live unambiguous reconciliation projection only with explicit,
individually dated and complete future-pay periods. It retains expected gross
pay and expected tax as separate confirmed inputs; it does not expand a pay
frequency, fill unconfirmed periods, calculate PAYE, or infer a whole-year
forecast. Immutable producer issuance, ordered source identities and SHA-256
digests, exact owner/business/tax-year matching across future facts, represented
period uniqueness/non-overlap, confirmation recency, reconciliation chronology,
exact-money validation and caller-supplied materiality thresholds are
revalidated on composition and projection. The accepted correction set also
fails closed on mutated or forged issued objects, cross-boundary evidence-ID
collisions, partial periods, duplicate facts, stale confirmations and future or
overlapping chronology.

Every accepted output remains explicitly limited to
`submitted_confirmed_periods_only`, is `not_customer_authoritative`, and states
`not_established_requires_authenticated_orchestration` for owner/business
authentication. The accepted reconciliation input has no owner/business field,
so matching the future facts to caller-supplied identifiers cannot prove that
the reconciliation belongs to that owner and business. The exact outstanding
requirement is
`authenticated_owner_business_reconciliation_binding_required`.

The package adds no provider or HMRC access, capture authority, persistence,
route/authentication boundary, customer presentation, tax-liability
determination, reserve recommendation, refund decision or payment authority.
Accordingly, it does **not** close the canonical
`paye_evidence_and_forecasting` blocker. The combined row remains
`not_executable`. Customer orchestration and
owner/business binding, durable lifecycle/persistence, safe presentation,
coverage of the required periods and sources, target UX/security evidence,
integrated end-to-end assurance and launch enablement remain outstanding.

The limitations above describe the accepted detached source package and remain
part of its durable provenance. The product integration at exact local checkpoint
`318fe2dabcef359dd4066fc207ad8a07395bbefd` composes it into the static
authenticated `GET /v2/paye/current-forecast` route. Installation requires the
exact active paid-access wrapper; owner, business and tax year are server-owned;
the route accepts no request facts; missing, invalid or disabled dependencies
fail closed; and the response is bounded to the accepted forecast projection.
This resolves the route/authentication orchestration gap without changing the
accepted composer or adding provider access, HMRC access, payroll prediction,
tax authority or payment authority.

The later checkpoint `4160155ad50eacb0d38f6a8084744aeb2f945c3c`
refreshes the integrated route's exact source bindings; it is evidence
reconciliation, not the product integration commit.

The accepted local candidate at `d49a540d3e898f16b56acb69851fd269f5fa50d5`
now adds the minimum durable store and a paid, authenticated, CSRF-protected
customer create, exact-update, list and delete journey inside the existing
manual-PAYE page. Browser input cannot select owner, business, tax year,
nation, source identity or confirmation time. A validated employment slot maps
to the same canonical employment identity as current evidence. Required
employment/period/source coverage, representative customer-language/usability
acceptance and target privacy, retention, datastore, operational and release
evidence remain absent. The canonical `paye_evidence_and_forecasting` row
therefore remains `not_executable`; the local journey does not close a launch
blocker by itself.

## Accepted manual entry/review reconciliation — 5 September 2026

The accepted 13-path manual baseline package is source checkpoint and local
integration `f29a5a8d4acde639fb108f8f9eeaaa833b59dc4b`, tree
`cd5293096cc592b0fd05d1d0c93d2811496daa6a`, with parent
`f3729c21b681cf4e6b2d70ba63421f2d3a3dee7d`. Its implementation evidence is
`docs/PAYE_MANUAL_BASELINE_EVIDENCE.md`; the owning acceptance, independent
review and browser record is `work/paye-manual-baseline-checkpoint.md` in the
parent workspace. The earlier candidate-pending language and dirty-suite
results in implementation evidence are historical, not the final checkpoint
disposition. The reviewed 13-path diff SHA-256 was
`51812e9e2bd19873925cf241d0f647f68738bd5103e1677e749b064e6b918908`.

The actual dashboard link leads to authenticated GET/POST
`/v2/paye/manual-baseline`. `reserved/web/v2.py` requires an existing user,
the exact independent enable switch and non-production operation; global CSRF
and existing no-store controls remain in force. The bounded form passes manual
cumulative facts through `reserved/services/paye_manual_baseline.py` into the
existing `PayeEvidenceCapture` and `normalise_paye_evidence`, then renders an
escaped review in `reserved/templates/v2/paye_manual_baseline.html`.
Known zero remains distinct from unknown. Output is explicitly MANUAL,
employment-cumulative and PARTIAL, not a reconciled or annual result.

Correction/re-entry returns a blank form; it does not replace or delete a saved
record. Request-local source/employment labels establish no persistent
owner/business/source binding. The route adds no saved financial state,
calculation, future-pay forecast, provider access or production activation.
Paid-surface classification is recorded, but runtime paid-entitlement enforcement
is not supplied by this package.

Recorded owning browser evidence used disposable synthetic users/database,
loopback-only execution and observation date 4 September 2026: dashboard-to-form
discovery, CSRF POST and all supplied review fields; blank correction/reset;
blank/unconfirmed 400; and affirmative zero gross with omitted tax/code and
unknown frequency/pension still shown as unknown. This is bounded engineering
browser evidence, not independent human usability or accessibility acceptance.
The focused route suite passed 60 tests. Clean source-checkpoint affected tests
passed 738, including the unchanged historical S5D dirty-scope sentinel.

The initial integrated canonical run recorded 8,025 root passes and two S7A
source-binding failures, not a green gate. Separately reviewed binding-only
reconciliation `54fe97224780b2d03212f4834c706da991bbd435`, tree
`de134ff0e6060bdc1fbde9ae2352a1202bb3491b`, preserved historical S5C evidence
and bound the accepted PAYE source. Its owning record is
`work/paye-live-v2-binding-checkpoint.md`. Clean affected tests passed 224;
the integrated canonical run then passed 8,028 root, 13 artifact, 23 parity
and 138 options tests, with RW3 true. These are immutable historical run
identities, not a requirement that current HEAD equal either checkpoint.

The Founder-approved structured manual path does not require raw-document
upload/extraction. The remaining broader gates are complete multi-employment
and required-period/source coverage; minimum-completeness and recency evidence;
production retention, account-deletion/backup and datastore proof;
representative privacy/legal/security/customer-language and target evidence;
provider access where separately required; and launch assurance. The canonical
`paye_evidence_and_forecasting` blocker is not closed by this manual sub-boundary.
