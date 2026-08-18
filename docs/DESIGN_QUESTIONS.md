# Reserved — Design Questions

**Purpose:** central register of unresolved questions requiring external
confirmation or additional evidence before a design or implementation choice is
finalised. Resolved answers flow into the applicable specification and backlog;
only founder-level policy choices flow into `FOUNDER_DECISIONS.md`.

**Status vocabulary:** `open`, `sent`, `answered`, `closed`. Do not create a new
row when an existing question covers the uncertainty; update that row instead.

## HMRC questions

### HMRC-01 — PAYE YTD submission timestamp

- **Why it matters:** Reserved cannot classify the freshness of
  `taxablePayToDate` and `totalTaxToDate` reliably without knowing the employer
  submission/effective time represented by the values.
- **Current assumption:** retrieval time is not an FPS submission time; no
  confirmed timestamp field has been found alongside these values.
- **External party:** HMRC Software Development Support Team.
- **Exact question to send:** Does Individuals Employments Income (MTD) 2.0
  expose, directly or through a related public user-authorised endpoint, the
  employer FPS submission/effective timestamp corresponding to
  `taxablePayToDate` and `totalTaxToDate`? If so, identify the exact field and
  semantics.
- **Evidence checked:** Individuals Employments Income (MTD) 2.0 employment
  financial-details journey; HMRC Tax Logic descriptions of the two fields.
- **Status:** open.
- **Launch impact:** high; payslip/manual fallback is required until resolved.
- **Answer:** pending.
- **Consequent action:** update HMRC temporal mapping, freshness policy and
  sandbox cases; do not infer freshness from retrieval time.

### HMRC-02 — FPS-to-API latency

- **Why it matters:** even with correct YTD fields, Reserved needs to know when
  accepted payroll information normally becomes observable.
- **Current assumption:** no guaranteed or expected latency has been verified.
- **External party:** HMRC Software Development Support Team.
- **Exact question to send:** What latency does HMRC guarantee, target or
  normally expect between acceptance of an employer FPS and the corresponding
  `taxablePayToDate` and `totalTaxToDate` values becoming available through
  Individuals Employments Income (MTD) 2.0?
- **Evidence checked:** current API/service documentation and validated review.
- **Status:** open.
- **Launch impact:** high; HMRC data cannot be an unqualified current source.
- **Answer:** pending.
- **Consequent action:** set evidence-age rules and lagged-data tests from the
  confirmed service behaviour.

### HMRC-03 — 2026/27 production-access window

- **Why it matters:** the closed quarterly-update product window may affect
  production credentials for read/reconciliation features even though Reserved
  is not launching as a quarterly-filing product.
- **Current assumption:** the public warning does not establish whether the
  restriction applies to Reserved's proposed read-only use.
- **External party:** HMRC Developer Hub onboarding/product team.
- **Exact question to send:** Reserved is not intending to launch in October
  2026 as a new 2026/27 quarterly-update filing product. Does the closed 2026/27
  quarterly-update product market window prevent production credentials for a
  read/reconciliation-only application using relevant MTD employment,
  calculation or status APIs?
- **Evidence checked:** current Developer Hub product-window warning and the
  proposed API subscription list.
- **Status:** open.
- **Launch impact:** potential launch blocker for features dependent on those
  production APIs; the general calculation must retain non-HMRC fallbacks.
- **Answer:** pending.
- **Consequent action:** revise launch API scope and product claims; do not
  enable affected live journeys before written confirmation/onboarding.

### HMRC-04 — View Self Assessment Account controlled beta

- **Why it matters:** this API may provide a stronger general SA reconciliation
  source than the MTD-specific accounts API, but production onboarding is
  controlled.
- **Current assumption:** useful workaround exists through manual evidence and
  other scoped HMRC sources; production access is not established.
- **External party:** HMRC View Self Assessment Account product/onboarding team.
- **Exact question to send:** Can Whip Smart Technologies Ltd obtain production
  access to the controlled-beta View Self Assessment Account 1.0 API for a
  user-authorised read-only reconciliation journey, and what eligibility,
  assurance and onboarding criteria apply?
- **Evidence checked:** service guide and GET account-breakdown documentation.
- **Status:** open.
- **Launch impact:** important, but workaround available.
- **Answer:** pending.
- **Consequent action:** add or defer the general SA account adapter and its
  acceptance tests according to the confirmed access route.

### HMRC-05 — current estimated annual employment pay

- **Why it matters:** HMRC's current employment-pay estimate could improve
  in-year PAYE forecasting, but a similarly named calculation field must not be
  substituted without semantic proof.
- **Current assumption:** no verified public user-authorised API field exposes
  HMRC's employer-specific current estimated annual pay.
- **External party:** HMRC Software Development Support Team.
- **Exact question to send:** Is HMRC's current estimated annual employment pay,
  as used operationally for PAYE coding, exposed through any public
  user-authorised API? If so, identify the endpoint, field, population and
  temporal semantics.
- **Evidence checked:** employment, individual calculation and legacy PAYE API
  documentation; `totalEstimatedIncome` was not treated as equivalent.
- **Status:** open.
- **Launch impact:** useful but non-blocking; Reserved can forecast locally.
- **Answer:** pending.
- **Consequent action:** add the exact mapping if confirmed; otherwise retain a
  local evidence-based forecast with explicit assumptions.

### HMRC-06 — future MTD mandation event

- **Why it matters:** customers must not confuse Reserved's early forecast with
  a formal HMRC determination.
- **Current assumption:** Reserved may infer likely future scope from qualifying
  income before HMRC records a mandated status; the precise transition event is
  not established.
- **External party:** HMRC MTD Income Tax product/API team.
- **Exact question to send:** At what precise system event, and through which
  field/status in Self Assessment Individual Details (MTD) 2.0, does HMRC expose
  future MTD mandation? Please distinguish this from a taxpayer who merely
  appears likely to meet the statutory threshold based on an earlier return.
- **Evidence checked:** Self Assessment Individual Details (MTD) 2.0 and MTD
  eligibility/mandation guidance reviewed to date.
- **Status:** open.
- **Launch impact:** important for correct customer messaging; not a blocker to
  a clearly labelled Reserved forecast.
- **Answer:** pending.
- **Consequent action:** update status reconciliation, customer labels and the
  forecast-to-formal-status transition tests.

+## Accounting-software questions

### FREEAGENT-01 — effective-dated accounting-method election

- **Why it matters:** recognition cannot be chosen safely without a per-business, effective-dated method.
- **Current assumption:** Reserved must obtain customer confirmation unless the current schema proves the election and its effective period.
- **External party:** FreeAgent.
- **Exact question to send:** Does the current company/API schema expose an effective-dated Income Tax cash-vs-traditional election, or must Reserved obtain it from the customer?
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high; blocks automatic recognition selection, with customer confirmation as fallback.
- **Answer:** pending.
- **Consequent action:** map the exact field/history or implement confirmed customer evidence.

### FREEAGENT-02 — jointly owned landlord-property share

- **Why it matters:** access to a property record does not establish the taxable ownership share.
- **Current assumption:** unknown share remains unknown and never defaults to 100%.
- **External party:** FreeAgent.
- **Exact question to send:** Is ownership percentage represented anywhere for jointly owned landlord properties, or must it be separately confirmed?
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for joint-property calculations; customer confirmation is a fallback.
- **Answer:** pending.
- **Consequent action:** map exact evidence or require effective-dated customer confirmation.

### FREEAGENT-03 — CIS field direction and lifecycle

- **Why it matters:** misreading CIS direction across corrections can reverse or duplicate deductions.
- **Current assumption:** no CIS field enters calculations before sandbox lifecycle proof.
- **External party:** FreeAgent.
- **Exact question to send:** Confirm exact CIS field direction/lifecycle across invoice, bill, credit and refund cases using current sandbox schemas.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for CIS journeys; non-CIS scope can proceed independently.
- **Answer:** pending.
- **Consequent action:** capture schemas and add lifecycle fixtures before enabling CIS mapping.

### XERO-01 — UK CIS fields and resource applicability

- **Why it matters:** fields may vary by resource and granted granular scopes.
- **Current assumption:** no UK CIS mapping is relied on until verified in Reserved's assigned schema.
- **External party:** Xero.
- **Exact question to send:** Confirm exact current UK CIS fields/resource applicability in Reserved’s assigned granular-scope schema.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for CIS; otherwise scoped/non-blocking.
- **Answer:** pending.
- **Consequent action:** pin field/resource/scope mappings and sandbox tests.

### XERO-02 — Cash Validation / Bank Statements Plus availability

- **Why it matters:** reconciliation design must not assume premium data or an unavailable app tier.
- **Current assumption:** access is absent unless explicitly contracted and enabled.
- **External party:** Xero.
- **Exact question to send:** Confirm what Cash Validation or Bank Statements Plus would expose for the intended app tier if considered necessary; do not assume access.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** medium; reconciliation can remain explicitly incomplete.
- **Answer:** pending.
- **Consequent action:** decide whether the feature is necessary and design a fallback.

### XERO-03 — assigned granular scopes

- **Why it matters:** implementation and field availability depend on the scopes actually assigned.
- **Current assumption:** documentation examples do not prove Reserved's production grants.
- **External party:** Xero developer support.
- **Exact question to send:** Confirm precise granular scopes assigned to the existing Reserved developer application.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for Xero adapter scope.
- **Answer:** pending.
- **Consequent action:** freeze the minimum-scope matrix before adapter implementation.

### QBO-01 — UK VAT fields and optionality

- **Why it matters:** VAT-exclusive/inclusive meaning and missing fields affect taxable amounts.
- **Current assumption:** all VAT fields remain optional until proven for a pinned minor version.
- **External party:** Intuit QuickBooks.
- **Exact question to send:** Confirm current UK VAT fields/optionality for the selected supported minor version.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for VAT-registered customers.
- **Answer:** pending.
- **Consequent action:** pin the version and add inclusive/exclusive/missing fixtures.

### QBO-02 — UK CIS/subcontractor deductions

- **Why it matters:** standard API availability and exact direction are unverified.
- **Current assumption:** CIS is unsupported until exact standard-API fields are confirmed.
- **External party:** Intuit QuickBooks.
- **Exact question to send:** Confirm whether UK CIS/subcontractor deductions are exposed through the standard QBO Accounting API and through which exact fields.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** high for CIS, non-blocking for customers outside CIS.
- **Answer:** pending.
- **Consequent action:** add a supported mapping or retain an explicit unsupported state.

### QBO-03 — class/location/project/custom-field editions

- **Why it matters:** property and business allocation cannot rely on edition-specific dimensions.
- **Current assumption:** availability varies and customer confirmation/manual allocation remains necessary.
- **External party:** Intuit QuickBooks.
- **Exact question to send:** Confirm which class/location/project/custom-field features are available in intended UK customer editions.
- **Evidence checked:** independent accounting-software semantics review.
- **Status:** open.
- **Launch impact:** medium; manual canonical allocation is a fallback.
- **Answer:** pending.
- **Consequent action:** document the edition matrix and supported allocation evidence.

### YAP-ACC-01 — contracted AIS matching identifiers

- **Why it matters:** stable cross-source bank/accounting-event matching depends on the selected flow and available identifiers.
- **Current assumption:** identifiers are matching evidence, never a sole deduplication key.
- **External party:** Yapily.
- **Exact question to send:** Confirm selected contracted AIS flow and identifiers/metadata available for stable bank-event matching.
- **Evidence checked:** accounting-software review and Yapily identity findings.
- **Status:** open.
- **Launch impact:** high for automated bank/accounting corroboration; ambiguous events can be held unresolved.
- **Answer:** pending.
- **Consequent action:** pin the contracted flow and matching evidence matrix before implementation.


## Yapily / banking questions

### YAP-01 — Data Plus commercial coverage

- **Why it matters:** Data Plus Categorisation could reduce customer friction,
  but Reserved must not make it a hard dependency if it is not included in the
  agreed commercial package or cannot be enabled consistently.
- **Current assumption:** categorisation is optional enrichment only; Reserved's
  canonical classification and calculation paths must continue to work without
  it.
- **External party:** Yapily / Cristian.
- **Exact question to send:** Is Data Plus Categorisation included in Whip Smart
  Technologies' agreed Yapily startup package, and can the required
  categorisation scope and categorisation webhooks be enabled for both the
  sandbox and production applications? Please identify any commercial,
  onboarding or technical constraints that apply.
- **Evidence checked:** first-pass Yapily banking-data review and current Data
  Plus enablement requirements.
- **Status:** open.
- **Launch impact:** medium; non-blocking if unavailable.
- **Answer:** pending.
- **Consequent action:** confirm the launch feature flag and fallback journey;
  keep provider categorisation outside calculation correctness dependencies.

### YAP-02 — transaction statuses across UK launch institutions

- **Why it matters:** institution-specific status behaviour could cause a
  pending or otherwise unsettled transaction to be treated as settled, changing
  calculation inputs and tax recognition.
- **Current assumption:** preserve the provider status exactly and keep pending
  transactions distinct from booked/settled evidence; no complete UK launch
  status matrix has yet been confirmed.
- **External party:** Yapily.
- **Exact question to send:** What complete set of transaction status values can
  Reserved receive through Yapily across the UK institutions in its proposed
  launch coverage, and are there institution-specific status meanings,
  transitions or behaviours that affect whether a transaction should be
  treated as settled? Please identify any institutions for which status alone
  is insufficient.
- **Evidence checked:** first-pass Yapily transaction-field review and identified
  pending-to-booked variation.
- **Status:** open.
- **Launch impact:** high.
- **Answer:** pending.
- **Consequent action:** define the canonical status mapping, institution
  exceptions and settled-evidence acceptance tests.

### YAP-03 — booking-date and value-date semantics

- **Why it matters:** selecting the wrong transaction date can change the tax
  period in which cash is treated as received or paid.
- **Current assumption:** preserve booking date, value date, generic transaction
  date and status separately; do not choose a universal recognition date in the
  Yapily adapter without verified semantics.
- **External party:** Yapily.
- **Exact question to send:** For UK AIS transactions used in cash-received and
  cash-paid use cases, does Yapily recommend a consistent rule for choosing
  between booking date/time and value date/time, or must Reserved treat their
  meanings as institution-specific and preserve both? Please identify known
  exceptions, missing-field behaviour and institution-specific guidance.
- **Evidence checked:** first-pass Yapily date-field review and documented bank
  variation.
- **Status:** open.
- **Launch impact:** high because the answer affects tax recognition dates.
- **Answer:** pending.
- **Consequent action:** finalise the canonical temporal mapping and recognition
  rules, then add cross-institution date tests.

### YAP-04 — programmatic historical-coverage metadata

- **Why it matters:** an incomplete transaction-history window could silently
  understate income even when every returned page has been processed.
- **Current assumption:** Reserved must retrieve history immediately after
  consent, exhaust pagination and record the earliest/latest successfully
  observed dates; this does not prove the maximum available history.
- **External party:** Yapily.
- **Exact question to send:** Is there a reliable programmatic field, endpoint
  or institution capability indicator that states the actual or maximum
  transaction-history window available for a particular consent and
  institution, beyond Reserved observing the earliest returned transaction,
  pagination results and retrieval errors? If so, what are its exact semantics
  and limitations?
- **Evidence checked:** first-pass history and pagination review, including
  institution-dependent availability.
- **Status:** open.
- **Launch impact:** high because incomplete history could understate income.
- **Answer:** pending.
- **Consequent action:** define the coverage-completeness state, onboarding
  retrieval controls and customer fallback for unavailable periods.

### YAP-05 — transaction identity and mutation

- **Why it matters:** pending-to-booked transitions and changed provider
  representations can create duplicate or omitted economic events.
- **Current assumption:** neither provider transaction ID nor transaction hash
  is sufficient alone; Reserved should use multi-signal, confidence-based
  matching and preserve ambiguous records separately.
- **External party:** Yapily.
- **Exact question to send:** Beyond Yapily's provider transaction ID and
  transaction hash, what matching strategy does Yapily recommend for linking a
  pending transaction to its later booked representation, or for identifying a
  transaction whose representation mutates between retrievals? Please describe
  expected identifier/hash stability and known institution-specific patterns.
- **Evidence checked:** first-pass transaction ID, transaction-hash and
  pending-to-booked review.
- **Status:** open.
- **Launch impact:** high because incorrect matching creates duplication or
  omission risk.
- **Answer:** pending.
- **Consequent action:** finalise the deduplication/mutation policy and its
  confidence thresholds, exception handling and regression tests.

### YAP-06 — joint-account holder and ownership metadata

- **Why it matters:** account access or a joint-account label does not establish
  the customer's economic ownership share or the correct allocation of income.
- **Current assumption:** use available holder metadata as supporting evidence
  only and obtain customer confirmation where reliable ownership information is
  absent.
- **External party:** Yapily.
- **Exact question to send:** What reliable account-holder, joint-account or
  ownership metadata is available through Yapily's UK AIS endpoints, what does
  each field establish, and how does availability or meaning vary across UK
  institutions? In particular, can any field establish an economic ownership
  percentage, or should Reserved always obtain that separately?
- **Evidence checked:** first-pass UK AIS account and joint-account review.
- **Status:** open.
- **Launch impact:** medium; a customer-confirmation fallback exists.
- **Answer:** pending.
- **Consequent action:** finalise the account-ownership evidence hierarchy and
  customer-confirmation journey.

### YAPILY-01 — minimum evidence for historical calculation reproducibility

- **Why it matters:** Reserved must be able to reproduce, explain and challenge
  a historical tax calculation after the relevant Yapily/Open Banking
  connection is no longer available, without unnecessarily retaining the
  customer's full raw bank history.
- **Current assumption:** retain a minimised, immutable calculation-evidence
  snapshot rather than full raw transaction history; the exact fields and
  retention period are not yet decided.
- **External party:** internal product/assurance and legal/privacy.
- **Exact question to send:** What minimum source evidence must Reserved retain
  to reproduce, explain and challenge a historical tax calculation after an
  external-data connection, including Yapily/Open Banking, is no longer
  available?
- **Evidence checked:** Yapily history, consent-revocation and transaction-hash
  findings; current canonical provenance contract; product requirement for
  historical calculation reproducibility and challenge.
- **Status:** open.
- **Launch impact:** high, but a workaround/design exists through a minimised
  calculation-evidence snapshot.
- **Answer:** pending.
- **Consequent action:** update the External Data Specifications and retention
  schedule once resolved.

## Legal and privacy questions

### LEGAL-01 — lawful basis after Open Banking consent ends

- **Why it matters:** Open Banking consent may expire or be revoked before
  Reserved needs to reproduce or explain a calculation that relied on the
  previously obtained transaction data.
- **Current assumption:** cessation of future account access does not by itself
  settle whether minimised transaction-derived calculation evidence may be
  retained; Reserved needs a separately documented lawful basis and purpose.
- **External party:** legal/privacy counsel.
- **Exact question to send:** What lawful basis should Whip Smart rely on for
  retaining transaction-derived evidence after Open Banking consent is revoked
  or expires, where that evidence is needed to reproduce or explain prior
  Reserved calculations? Please assess contract, legitimate interests, legal
  obligation and any other appropriate basis, and whether special-category
  inferences from transaction data change the analysis.
- **Evidence checked:** current calculation-evidence proposal, Open Banking
  consent-revocation findings and the canonical provenance contract.
- **Status:** open.
- **Launch impact:** high, but a minimised evidence design and configurable
  retention controls provide a design route while advice is obtained.
- **Answer:** pending.
- **Consequent action:** document the lawful basis by evidence class and update
  the privacy notice, retention schedule and processing records.

### LEGAL-02 — proportionate retention periods by evidence class

- **Why it matters:** raw bank data, canonical records and calculation audit
  evidence have different purposes and privacy risks; applying one blanket
  period could undermine either auditability or storage limitation.
- **Current assumption:** different retention periods and deletion or
  anonymisation triggers are likely to be appropriate for different evidence
  classes; no periods are yet approved.
- **External party:** legal/privacy counsel.
- **Exact question to send:** What retention periods are proportionate and
  defensible for (a) raw Yapily/Open Banking transaction data, (b) canonical
  transaction records, (c) calculation-evidence snapshots, (d) source
  references, hashes and IDs, and (e) calculation audit logs? Should different
  periods apply by evidence class, and what deletion or anonymisation triggers
  should Whip Smart use?
- **Evidence checked:** proposed operational-source-data versus
  calculation-evidence distinction and current Reserved provenance fields.
- **Status:** open.
- **Launch impact:** high, but configurable class-based retention and a
  short-retention default for raw data provide a design route.
- **Answer:** pending.
- **Consequent action:** approve and implement the retention schedule, deletion
  jobs, anonymisation rules and evidence-class tests.

### LEGAL-03 — effect of Open Banking consent revocation

- **Why it matters:** Reserved needs a clear boundary between stopping future
  access and handling data already obtained, together with accurate customer
  disclosures and controls.
- **Current assumption:** revocation stops further Open Banking access, but the
  treatment of previously obtained data depends on purpose, lawful basis,
  retention rules and applicable customer rights.
- **External party:** legal/privacy counsel.
- **Exact question to send:** On revocation of Open Banking consent, what data
  must cease to be accessed, what previously obtained data may lawfully be
  retained, and what customer disclosures and controls are required in the
  privacy notice and consent journey?
- **Evidence checked:** Yapily consent-revocation findings and the proposed
  separation of operational source data from calculation evidence.
- **Status:** open.
- **Launch impact:** high, but access can fail closed and retained evidence can
  be quarantined under configurable policy until the rules are confirmed.
- **Answer:** pending.
- **Consequent action:** update disconnect/revocation behaviour, privacy copy,
  customer controls, deletion handling and acceptance tests.

### LEGAL-04 — minimising special-category exposure in transaction data

- **Why it matters:** merchant names and raw transaction narratives may reveal
  or support inferences about health, religion, politics, trade-union
  membership, sex life and other highly sensitive matters unrelated to the tax
  calculation.
- **Current assumption:** after canonical tax evidence has been created,
  Reserved should avoid retaining merchant descriptions and raw narratives
  unless a specific evidenced purpose makes them necessary.
- **External party:** legal/privacy counsel.
- **Exact question to send:** What data-minimisation approach is appropriate
  given that bank transaction data may reveal or allow inference of
  special-category data, including health, religion, politics, trade-union
  membership and sex life? Should Reserved avoid retaining merchant
  descriptions and raw narratives once canonical tax evidence has been
  created, and what exceptions or safeguards would be defensible?
- **Evidence checked:** proposed calculation-evidence snapshot, current
  canonical provenance fields and identified sensitivity of transaction
  descriptions and merchant data.
- **Status:** open.
- **Launch impact:** high, but field-level minimisation, redaction and short raw
  data retention provide a design route.
- **Answer:** pending.
- **Consequent action:** define the permitted evidence fields, redaction rules,
  exceptional-retention controls and privacy/security tests.

## Other providers

Add unresolved Xero, QuickBooks/Intuit, FreeAgent, Stripe or other specialist
questions here using the same fields. Provider facts that have already been
validated belong in `EXTERNAL_DATA_SPECIFICATIONS.md`, not here.
