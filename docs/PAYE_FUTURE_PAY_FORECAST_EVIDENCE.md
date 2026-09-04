# PAYE future-pay forecast composition evidence

## Status and exact boundary

This is an uncommitted, bounded implementation candidate based on clean local
integration checkpoint `74ba3b743864cd4efbcb8df2041c095f49da1d47`.
It is not independently reviewed, checkpointed, integrated, launch-ready, or a
claim that the wider PAYE blocker is closed.

The candidate adds one pure composition service. It accepts:

1. a live, producer-issued, unambiguous PAYE reconciliation from the accepted
   `reserved.engines.paye_reconciliation` boundary;
2. one exact tuple of explicit, individually dated future-pay facts; and
3. exact caller-supplied owner, business, tax-year, as-of, recency and
   materiality controls.

It returns a detached, immutable candidate that keeps reconciled historical tax
deducted, explicit future gross pay, explicit expected future tax deduction,
dates, source identities/digests, technical materiality and fixed uncertainty
statements separate. It does not return or retain any source object.

## Authoritative sources used

The package was derived only from current local authority and accepted code:

- `FOUNDER_DECISIONS.md`, specifically the resolved PAYE current-position,
  evidence/uncertainty, variable-income check-in, annual tax/reserve
  presentation and October launch-readiness decisions;
- `docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md`;
- `docs/HMRC_PAYE_RECONCILIATION.md`;
- `docs/HMRC_PAYE_FALLBACK_S1_EVIDENCE.md`;
- `docs/PAYE_RECONCILIATION_TRUST_AND_POLICY_EVIDENCE.md`;
- `reserved/engines/paye_reconciliation.py` and its accepted projector.

No network, provider, credential, customer datum or external factual claim was
used. The service does not treat HMRC or any other source kind as inherently
authoritative.

## Encoded acceptance rules

- Every future-pay fact is explicitly source-, source-evidence-, owner-,
  business-, tax-year- and employment-bound.
- Gross pay must be strictly positive. Expected tax deduction may be exact zero
  but must be present. Both are finite, non-negative, bounded exact money with
  no float, bool, exponent, sign, excess precision or implicit rounding. An
  expected deduction may equal but must not exceed its explicit gross pay.
- Each fact names an exact represented period, future payment date,
  confirmation date, exact supported frequency and complete-period state.
- Partial periods fail closed. The composer does not fill gaps, expand a
  recurrence, multiply by pay frequency, or infer any future amount from
  historical evidence.
- The represented period must be wholly within the selected tax year, end no
  later than the pay date, start after the latest selected reconciled evidence
  period and have a payment date after the forecast date.
- Confirmation must exist by the forecast date and be no older than the exact
  caller-supplied recency threshold. Boundary equality is accepted; one day
  beyond it is rejected.
- Fact IDs, source-evidence IDs, source-evidence SHA-256 digests and represented
  payment keys must be unique. Duplicates fail closed rather than being
  silently deduplicated. Overlapping represented periods for the same
  employment also fail closed to prevent double counting; identical dates for
  distinct employments remain separate facts.
- No future-fact source-evidence ID may equal an ID selected by the upstream
  reconciliation. This cross-boundary collision fails closed, preventing one
  evidence identity from being represented as both historic and future.
- The reconciliation must be a live exact issued result with exact schema,
  matching tax year, known tax paid, selected evidence and the unambiguous
  `calculated` status. Missing, conflicting, stale or materially uncertain
  reconciliation states fail closed.
- Every selected reconciliation evidence observation and effective-through
  date must be no later than this composition's forecast date. Equality is
  accepted. A future observation and a future effective period are rejected as
  distinct failures even if an upstream reconciliation was produced with a
  later as-of date.
- The material tax threshold is a mandatory exact caller input. Equality is
  material. The threshold only classifies the fully retained explicit total; it
  never filters facts or changes an amount.
- The output includes an SHA-256 identity of the accepted reconciliation
  projection, its ordered selected evidence IDs/source categories/dates, and
  ordered detached future-fact source provenance.

`ConfirmedFuturePayFact` is a validated structural boundary, not independent
proof that a human, employer or document really confirmed the represented
facts. A future authenticated capture/confirmation journey must establish that
real-world authority before creating these inputs. The service revalidates
exact type, immutable state and process-local issuance on every composition and
rejects mutation, low-level forgery and re-sealing.

The accepted PAYE reconciliation contract does not itself contain an owner or
business identifier. This service therefore enforces the caller-supplied
owner/business binding across every future fact and copies it into the detached
candidate, but it cannot independently prove that the upstream reconciliation
belongs to that owner. The future authenticated orchestration boundary must
verify that association before calling this service; this candidate does not
claim to close that gate.

## Fixed limitations retained in every result

Every successful candidate states that:

- future pay is a confirmed input, not an observed payment;
- expected future tax deduction is an explicit input, not a payroll
  calculation; and
- the forecast does not establish final tax liability.

The runtime result—not only this evidence note—also carries the following fixed
machine-readable limitations:

- coverage is `submitted_confirmed_periods_only`;
- owner/business authentication is
  `not_established_requires_authenticated_orchestration`;
- the result is `not_customer_authoritative`; and
- `authenticated_owner_business_reconciliation_binding_required` remains the
  orchestration requirement.

These fields are immutable producer-issued state and cannot be replaced with a
customer-authoritative or whole-year claim.

The service does not calculate PAYE from gross pay or a tax code, predict
salary, infer bonuses, derive payment schedules from frequency, calculate the
annual statutory position, determine a refund, recommend a reserve, persist,
route, render, call HMRC/a provider, process a document, perform authentication,
move money, or grant any authority. It cannot establish provider, customer,
privacy, security, UX, operational, E2E, release or launch evidence.

## Changed paths

- `reserved/services/paye_future_pay_forecast.py`
- `tests/test_paye_future_pay_forecast.py`
- `docs/PAYE_FUTURE_PAY_FORECAST_EVIDENCE.md`

No existing production, test, documentation, configuration, generated,
assurance, decision or completion-map path is modified by this candidate.
