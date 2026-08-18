# Founder decisions

This document is the governing product and scope authority for Reserved. Where
it conflicts with an older roadmap, handover, implementation note or dormant
code, this document prevails. Planning and implementation agents must read it
before starting work, must flag genuine conflicts, and must not infer a change
to a founder decision from stale documentation. Changes to these decisions must
be recorded here as explicit founder decisions.

## Resolved: v1 tax scope (12 August 2026)

V1 covers England, Wales and Northern Ireland and includes PAYE/multiple
employment, sole trade, dividends, savings, UK and foreign property, student
loans, HICBC and bounded internal MTD readiness. Scottish Income Tax, Capital
Gains Tax, full MTD filing, accounting write-back, VAT expansion and Corporation
Tax remain outside v1. See `docs/V1_TAX_SCOPE.md`. This scope was amended by the
HICBC decisions below on 15 and 17 August 2026.

This is no longer an open decision. Any change should be recorded as a new founder scope decision rather than inferred from dormant code.

## Resolved: customer-facing tax-year terminology (15 August 2026)

Customer-facing language should use **tax year**, not "period of assessment" or
an unexplained calendar-year reference. Compact customer surfaces should show
the tax year applicable to the figure using the conventional label, for example
**2026/27** for a current-year forecast made in October 2026 or **2025/26** for a
completed prior-year reconciliation. The label must be derived from the result's
tax-year context and must not be hard-coded. The full date range need not be
repeated alongside routine figures; it may be explained during onboarding, in
help content, or where the period could genuinely be misunderstood.

The current tax year should be clear throughout onboarding, estimates,
check-ins, evidence requests, transfers and history. Technical or statutory
terms may remain in internal contracts where necessary, but must not displace
clear customer language.

## Superseded: HICBC outside v1 customer scope (15 August 2026)

The 15 August decision to keep HICBC outside the October v1 customer scope was
superseded by the founder decision of 17 August below. It is retained here only
to make the scope change explicit and must not be used for implementation.

Unknown partner and Child Benefit facts must still never be silently treated as
zero.

## Resolved: HICBC is an October v1 launch target (17 August 2026)

HICBC is included in the intended October v1 customer scope. Reserved should
calculate it from the customer's own information plus the partner information
needed to determine responsibility. The single-user HICBC logic has already been
considered in depth, and a bounded manual partner-estimate capability has been
implemented.

October should support two routes for the otherwise missing partner evidence:

1. A solo user may provide an estimate of their partner's ANI, including a
   bounded range where income such as a bonus is uncertain. Reserved must state
   clearly that the result depends on information supplied by the user and may
   change when the partner's actual ANI is known.
2. Two Reserved users may expressly link their accounts for the limited purpose
   of a privacy-preserving HICBC determination. Reserved may use the minimum
   HICBC-relevant information needed behind the scenes, but must not reveal or
   imply either partner's precise ANI, income band, bonus, relative salary or
   calculated personal tax to the other.

Where sufficiently supported by assured evidence, HICBC may contribute to the
customer's estimated total tax, amount still to cover, set-aside recommendation
and related payment journey. Where partner or Child Benefit evidence is missing,
stale, materially uncertain or contradictory, Reserved must preserve that
uncertainty, request the smallest useful additional fact, show a bounded result
where supportable, or exclude HICBC from the actionable total with a clear
explanation. It must not manufacture a point estimate or payment recommendation.

The work is bounded to:

- calculating HICBC from each individual's adjusted net income (ANI), not a
  combined household income;
- a manual partner-estimate journey that collects at most a partner ANI point or
  low/high range plus an observation/confirmation date;
- a narrow, source-neutral, privacy-preserving interface for linked partner
  evidence, with consent, unlinking, relationship-period and access boundaries;
- preserving material uncertainty rather than inventing certainty.

The following prohibitions remain in force and are not overridden by this
decision:

- HICBC must not enter a customer tax total, reserve amount, set-aside
  recommendation or payment flow unless its evidence is adequate for that
  purpose and all applicable assurance gates have passed;
- a linked partner's precise ANI, income band, bonus, relative salary or
  calculated personal tax must never be disclosed or implied to the first user;
- unknown partner or Child Benefit facts must not be treated as zero;
- where the two partners have equal ANI there is no statutory "higher-income"
  person, so responsibility must fail safe as ambiguous rather than inventing a
  tie-break.

The manual partner estimate is third-party personal data. It requires
authenticated owner scoping on every read and write, no cross-user access,
server-side input validation, CSRF protection on state-changing requests,
no-store cache behaviour, deletion and replacement, no raw partner values in
logs/analytics/notifications, and a privacy-notice and retention review before
production activation.

Linked accounts additionally require explicit consent from both users, strict
purpose limitation, revocation and unlinking, safe handling of relationship
changes and periods, prevention of direct and inferential disclosure, and
independent cross-account authorisation and privacy testing. Both the manual and
linked routes are October launch targets, but neither may be activated or counted
as launch-ready until its applicable privacy, retention, legal, security,
customer-evidence and calculation-assurance gates have passed.

## Resolved: linked-HICBC limited inference and mutual permission (18 August 2026)

The linked-account HICBC journey may disclose to each user the minimum outcome
needed to explain that user's own correct HICBC position. This includes the
unavoidable possibility that a user may infer that linked information caused
their own estimate to change, or that HICBC is or is not included in that
estimate. This limited inference is permitted because withholding it would make
the linked-account determination unusable.

This decision clarifies and partially supersedes the broader prohibition above
on implying a partner's position. It does not permit disclosure of the partner's
precise ANI, income, ANI band, income band, bonus, comparative or relative income,
calculated personal tax, underlying evidence, or any other avoidable financial
information. Customer language must describe only the receiving user's own tax
consequence. Reserved must not provide repeated hypothetical calculations,
comparative wording, bands or other probing mechanisms that could be used to
reverse-engineer the partner's finances.

Both partners must separately and affirmatively enable linked HICBC after being
shown a concise explanation that:

- Reserved will use the limited relevant information available in both linked
  accounts to calculate each user's own HICBC position;
- neither person will see the other's income or financial details;
- either person may nevertheless see that their own estimate changed after
  linked information was considered; and
- either person may turn off linked HICBC and unlink the accounts.

The acknowledgement must not be preselected or bundled invisibly into general
terms. Reserved must retain an auditable record of the notice shown, its version,
who agreed, when they agreed, and any subsequent withdrawal or unlinking. When
either partner withdraws permission or unlinks, linked evidence must not be used
in new calculations and the affected result must revert safely to an
indeterminate, manual-evidence or otherwise supported state. Retention or
deletion required for another documented purpose must be handled under its own
stated basis and must not silently preserve linked calculation access.

The mutual product permission described here must not be assumed to settle the
separate UK GDPR lawful-basis analysis. Reserved must document the applicable
lawful basis, transparency information, purpose limitation, data minimisation,
withdrawal, unlinking, deletion and anti-probing controls before activation.

External legal or privacy advice is not an automatic launch prerequisite for
this bounded capability. A documented internal privacy-assurance review is
required before activation. External advice should be obtained if that review
identifies a material unresolved legal or privacy question. This does not relax
any outstanding technical, privacy, retention, security, evidence or calculation
assurance gate, and it does not authorise activation while linked evidence can
appear falsely determinate or actionable.

## Resolved: PAYE current-position proposition for v1 (15 August 2026)

V1 should help PAYE users estimate whether their full-tax-year position is
likely to leave tax still to pay or an apparent excess, including users who are
not registered for Self Assessment or in scope for MTD. The feature must remain
useful when HMRC's available APIs do not provide complete current-year payroll
evidence.

The evidence journey is tiered:

1. Use permissioned HMRC employment and income evidence where the customer and
   selected API are eligible, while respecting its period, latency and scope.
2. Obtain a baseline from at least one suitable payslip, or equivalent manual
   gross-pay, tax-to-date, tax-code, pay-frequency and pension information,
   where current cumulative payroll evidence is otherwise unavailable.
3. Use Open Banking to detect a materially different net employment credit and
   ask a short, targeted question about the cause, such as a bonus, salary
   change, commission, reimbursement, job change or other payment. A bank credit
   is a prompt trigger, not evidence of gross taxable pay or tax deducted.
4. Request an updated payslip only when needed to resolve a material change or
   improve an estimate sufficiently for its stated purpose.

Reserved should calculate the projected annual statutory position, show PAYE
tax evidenced as already deducted, estimate likely remaining payroll deductions
using explicit future-pay assumptions, and present the resulting possible gap
or apparent surplus separately and transparently. It must not promise a refund
or state that an underpayment is confirmed from incomplete evidence.

Salary sacrifice, net-pay pension contributions and relief-at-source pension
contributions must be identified and treated according to their different tax
effects so that relief is not double counted. The result should disclose its
evidence quality, important assumptions and material missing facts. The planned
variable-income check-in decision below extends this approach by seeking known
bonus information before payment.

## Resolved: simultaneous undergraduate Student Loan treatment (13 August 2026)

Reserved v1 may calculate at most one undergraduate plan, optionally plus a
postgraduate loan. Where simultaneous undergraduate plans or an unknown plan
value is supplied, the annual Self Assessment treatment is
`unsupported_for_decision`: no loan amount, partial total, allocation, reserve
or set-aside may be shown, and the customer must verify the applicable treatment
with HMRC or a qualified tax adviser. This is a bounded product-scope decision,
not approval of the three pending arithmetic fixtures.

## Resolved: money set-aside scope for v1 (15 August 2026)

At £29 per month, the intended proposition is not calculate-and-track only.
Helping a customer separate money into a savings account owned by that customer,
potentially an interest-bearing account, is part of the intended value. Reserved
does not hold customer funds.

Sweeping VRP is intended for v1 and the October launch scope, subject to Yapily
feasibility and bank coverage, same-owner destination controls, legal and
regulatory confirmation, acceptable commercials, exact consent and status
handling, security review and launch assurance. No money moves without the
customer's authorisation and the authentication or consent required by the
customer's bank.

Yapily's latest clarification is that VRP and Single Payments sit under the same
Yapily Payments product. Reserved will support both Single Payments/PIS and
sweeping VRP where available, and the customer must choose the payment method.
Single Payment/PIS is the default and primary introductory journey. Sweeping VRP
is an expressly opt-in automation option and must never be enabled, preselected
or implied by default. Both journeys remain subject to Yapily coverage,
same-owner destination controls, consent, legal and regulatory confirmation,
security review and payment assurance.

The quoted commercial information does not identify a separate monthly licence
price for VRP and Single Payments, but any distinct transaction, volume, mandate
or product charges remain to be confirmed against the draft agreement. The
provider boundary must remain portable, and neither Stripe Connect nor any other
historical provider option is the selected v1 architecture unless a later
founder decision says so.

Customers may choose a routine review cadence, including after income arrives,
weekly, fortnightly, monthly after payday or on a chosen date, material events
only, or manual review. A material income change may prompt an exceptional
review independently of that routine cadence.

The customer may accept, edit or skip a recommended amount. Customers may also
choose a routine review cadence, but a cadence or review prompt must not be
misrepresented as consent for a payment. The underlying journey should be able
to support later European payment rails, including SEPA, without coupling tax
logic to a UK-only transfer method.

## Resolved: October external-integration boundary (15 August 2026)

The October scope includes live Yapily account-information access and the
conditionally approved Yapily Payments journeys described above, supported HMRC
connections for eligible customers, a usable payslip/manual PAYE fallback, and
live read-only integrations with FreeAgent, Xero and QuickBooks for relevant
business-income customers.

The accounting integrations should authenticate securely, allow selection of
the correct business, import the information needed for the supported tax
estimate, preserve source and retrieval date, refresh without duplication,
identify incomplete or questionable information, and disconnect cleanly. They
must feed the shared tax-estimation contracts rather than implement separate
provider-specific tax calculations.

FreeAgent, Xero and QuickBooks are October targets. Accounting write-back,
bookkeeping correction, invoice creation, tax-return submission, full MTD
filing, VAT expansion and Corporation Tax are not required for October.
PAYE-only users should not be asked to connect accounting software. A temporary
provider outage should degrade safely and offer refresh or an appropriate
manual fallback rather than disable Reserved as a whole.

HMRC integration is an October target wherever production access, exact API
support and customer eligibility permit. Lack of universal HMRC coverage does
not block the bounded launch if the payslip/manual journey is independently
shown to be usable, but Reserved must not advertise unavailable automation or
imply that partial HMRC data is a complete live PAYE record.

## Resolved: customer-facing “Explore your options” terminology (15 August 2026)

The customer-facing feature name is **Explore your options**. Individual
comparisons should be described as scenarios or illustrations and should show
the factual estimated effects of possible changes.

“Optimise” may remain in internal compatibility names, but should not be the
customer-facing navigation label. Reserved must not present the lowest-tax
scenario as necessarily the best choice for the customer or imply that an
illustrative calculation is personal financial advice. Supporting copy should
make clear that the feature explains possible effects rather than recommends a
course of action.

## Resolved: PAYE evidence and uncertainty principle (13 August 2026)

Reserved does not apply unconditional precedence to HMRC data. It selects the
evidence best supported by characteristics including recency, completeness,
identity and what the source represents, while preserving provenance and
material conflicts.

**WHY IT MATTERS**  
HMRC API documentation establishes what data can be retrieved; it does not establish Reserved's product-policy judgement that one observation should always take precedence over another. A newer P60/P45/payslip may sometimes be more informative than an older HMRC observation. This policy affects customer estimates and review warnings.

Reserved's tax position remains an estimate even when arithmetic is correct,
because inputs may be incomplete, stale, conflicting or omitted. Known material
uncertainty must not be collapsed into certainty. Where reasonably determinable,
its potential numerical effect should be retained and may be communicated.
Confidence labels describe evidence quality, not tax certainty.

## Resolved: planned variable-income check-ins (15 August 2026)

Reserved should ask PAYE users whether they normally receive bonuses,
commission or other variable employment income and, where known, approximately
when the amount is confirmed and when it is paid. Users may provide a specific
month, an approximate period, say that timing varies, or say that they do not
know. This is optional and must not block the core journey.

Where a confirmation period is known, Reserved should schedule a proportionate
check-in asking whether the amount has been confirmed. If the user supplies the
gross amount, Reserved should update the projected full-tax-year position before
payment, distinguish confirmed facts from future-pay assumptions, and show any
recommended additional reserve. It may explain the calculated effect of a
confirmed pension or salary-sacrifice arrangement, but must not present an
illustration as regulated financial advice.

After payday, Reserved should reconcile the forecast against the actual
payslip and available HMRC and bank evidence, then offer any revised,
customer-authorised PIS transfer. If timing is unknown or changes, material
income detection through Open Banking may trigger the fallback check-in, but a
net bank credit must not be treated as proof of gross taxable income or tax
deducted.

The intended sequence is: prepare before confirmation; forecast when confirmed;
verify and offer a transfer after payment; reconcile again at year end. The
purpose is not to guarantee that PAYE underpayment cannot occur, but to maximise
the time available for the customer to understand and fund a plausible future
shortfall, particularly for bonuses paid late in the tax year.

## Resolved: temporary payslip processing and minimisation (15 August 2026)

Reserved is not a general payslip-storage service in v1. An uploaded payslip
should be retained only temporarily while Reserved extracts the fields required
for the supported purpose and the customer checks or corrects them. The original
document should then be securely deleted automatically, including after an
explicitly defined short expiry period if processing or confirmation is
abandoned.

Reserved should retain only the minimum structured fields and provenance needed
to calculate, explain and reconcile the customer's tax estimate. Customers
should be able to see the extracted information, its source and date, and delete
or replace it. Account deletion should initiate deletion of payslip-derived
personal data subject only to specifically documented legal, security and
backup constraints.

Before launch, the privacy and legal workstream must approve the lawful basis,
field-level data inventory, original-document expiry, structured-data retention
schedule, backup deletion behaviour, access controls and customer notices. A
future document-vault feature would require a separate founder decision and
privacy assessment.

## Resolved: customer MTD scope indication (15 August 2026)

Reserved must not use **MTD ready** in customer-facing language. The
customer-facing feature label is **Could Making Tax Digital apply to you?**
Internal engineering and assurance materials may continue to use "MTD
readiness" where its bounded meaning is defined.

For the supported circumstances, Reserved should separately identify gross
income before expenses from sole-trader businesses, UK property and foreign
property, then combine only the sources that count toward the customer's MTD
qualifying income. The calculation must respect relevant residence, source,
Self Assessment, exemption, cessation and timing facts; unknown facts must not
silently be treated as zero.

Reserved may use current-year information to provide an early annualised
indication that the customer may approach or exceed a future threshold. It must
distinguish that planning indication from HMRC's formal determination based on
the applicable return and rules. It should show the income sources included,
state that the test uses gross income before expenses, identify material
exclusions, use the thresholds and start dates applicable at the time, and
recheck as evidence changes.

Where the indication is material, use the calm headline **Worth reviewing** and
say that Making Tax Digital may apply in a future tax year; do not state that it
definitely applies while eligibility facts remain incomplete.

October does not include quarterly-update submission, final declaration,
full MTD filing, agent services or a general claim that Reserved is compatible
filing software. It includes the verified data, evidence and integration
foundations for future MTD workflows and only those read-only customer
capabilities proven against supported production APIs.

## Resolved: customer reassurance and progressive disclosure (15 August 2026)

Reserved should combine direct numerical clarity with calm, proportionate and
non-judgemental reassurance. It should explain what a result appears to mean,
distinguish estimates from confirmed liabilities, state evidence quality and
material uncertainty, indicate urgency, and provide practical next steps.

The primary number and status must remain immediately available to confident
users. Additional explanation, causes, evidence and help should be available
through progressive disclosure. Reassurance must not hide material risks,
promise an outcome, imply that HMRC will waive interest or penalties, or delay
appropriate escalation to HMRC or a qualified professional.

## Resolved: fitness-for-purpose assurance objective (13 August 2026)

Reserved does not attempt to eliminate all uncertainty or prove that available
information is theoretically complete. It must produce a trustworthy and useful
estimate from available information, assess whether that information is adequate
for the estimate's stated purpose, and handle material uncertainty appropriately
where it is not. Adequacy for a qualified planning estimate does not imply
adequacy for filing, payment, refund confirmation or professional advice.

The launch objective is sufficient, evidence-led assurance for a responsible and
explicitly scoped v1—not proof that no defect can exist. This does not lower the
independent correctness standard for deterministic tax calculations where the
facts and applicable rules are known.

**CAN DEVELOPMENT CONTINUE WITHOUT IT?**  
Yes. Arithmetic, evidence preservation and no-double-count controls can continue.

Implementation may proceed under this principle. Operational parameters and
customer wording that still require decisions are listed below.

## Resolved: calm tax-review alerts (15 August 2026)

Reserved should use **Worth reviewing** as the consistent customer-facing
headline for both material changes and tax matters requiring attention. The
underlying system must retain distinct priority and notification states, but
urgency should normally be communicated through a specific reason, timeframe
and next step rather than alarming category names.

Small changes that do not materially affect what the customer should put aside
may wait for the next routine check-in. Material funding changes should prompt a
review at a proportionate time. Deadlines, apparent filing requirements,
penalties, unresolved HMRC requests and potentially misleading missing evidence
should be surfaced promptly, using the applicable date where known. Immediate
security or unauthorised-payment events are outside this calm tax-language rule
and may use direct urgent wording.

Customers may choose **Tell me about important changes**, **Tell me about most
changes**, or **Only interrupt me when action is needed**. The default is **Tell
me about important changes**. Legal deadlines and serious unresolved issues
must still be surfaced regardless of notification preference.

There is no founder-approved universal pound threshold. Materiality should
consider the absolute change, its relative effect on the customer, time
available and whether it changes an amount the customer needs to fund. The
implementation and independent review agents should propose explicit,
configurable defaults for validation rather than embedding an unexplained
cutoff.

## PAYE evidence operating parameters

**TECHNICAL PROPOSALS AND VALIDATION STILL REQUIRED**

- Recency: evidence-type and tax-year-stage windows; there will be no unexplained universal cutoff.
- Completeness: minimum fields for HMRC cumulative observations, P60s, P45s and payslips.
- Representation and identity: when an aggregate can be compared with or preferred to employment-level evidence.
- Conflict display: when to show a range, a qualified point estimate or “effect not determinable”.
- Materiality defaults implementing the founder policy above.

**RECOMMENDED IMPLEMENTATION DEFAULT**  
Keep these values explicit and configurable. Until approved, preserve the
evidence and conflict, use conservative factual wording, and avoid treating a
policy-dependent point estimate as independently validated.

## Resolved: annual tax and amount-to-reserve presentation (15 August 2026)

Reserved should lead with the additional amount the customer should consider
putting aside. The compact customer view should use plain language and show the
supporting figures separately:

- **Estimated total tax for {applicable tax year}**
- **Tax already taken from your pay**
- **Tax we expect to be taken from your future pay**
- **Tax you may still need to cover**
- **Money you've already put aside**
- **Suggested additional amount to put aside**

The first figure is a calculated full-tax-year estimate; the second is an
evidenced historic deduction; the third is a forecast; the fifth is money held
by the customer and not tax paid to HMRC. These categories must remain visibly
distinct and must not be described as interchangeable.

The suggested amount may be the primary actionable figure only when the
included components use compatible periods and bases, their provenance is
available, material conflicts are resolved or visibly bounded, and important
excluded liabilities are named. The underlying figures and assumptions must be
immediately accessible through progressive disclosure.

Where a reliable point estimate is not supportable, Reserved should show a
useful bounded range or ask for the smallest additional fact needed. A possible
overpayment must be described as provisional and not as a confirmed refund.
Customer-facing evidence language should ask **How reliable is this estimate?**
and use plain labels such as **Reliable**, **Fairly reliable**, and **Needs more
information**, while preserving the more precise structured evidence state
internally.

This founder decision does not override the existing assurance blocks on the
current composition prototype. Customer connection, persistence or API
publication still requires the applicable independent technical and provenance
gates to pass.

## Resolved: non-UI October launch-readiness standard (15 August 2026)

Reserved's non-UI product is ready for the bounded October launch only when it
can safely collect and reconcile supported customer information, calculate the
supported full-tax-year position, explain the result, recommend an additional
amount to put aside and complete any customer-approved payment initiation.

October remains the founder's launch target. A staged or private beta may be an
operational step toward launch, but must not silently redefine "October launch"
as a late-October private beta. Any change to the launch target or the meaning
of launch requires an explicit founder decision recorded in this document.

The supported calculation must include PAYE and multiple employments,
sole-trader income, UK property income, foreign property income, dividend
income, savings interest, supported pension treatment, student-loan treatment
and HICBC. It must distinguish tax already taken from pay, tax expected to be
taken from future pay and money the customer has already put aside. Scottish
Income Tax and Capital Gains Tax are outside the October calculation, reserve
recommendation and launch claims.

Every supported calculation area must have complete, independently derived and
approved mandatory assurance coverage. Required RW3 fixtures must be present,
approved and passing. Missing, rejected, excluded or zero-test coverage cannot
contribute to an overall pass. The exact release artefact deployed must be
demonstrably identical to the artefact that passed the canonical release gate,
including its dependencies, build transformations and executable contents.

Reserved must preserve the source, date, period and meaning of customer
evidence; prevent double counting; distinguish known facts from forecasts,
assumptions, missing information and conflicts; and fail safely when a reliable
result cannot be produced. Unknown information must not silently become zero.
Possible overpayments must not be presented as confirmed refunds, and
unsupported calculations must not generate reserve or payment recommendations.

The required October customer journeys must be verified end to end using
production-capable connections for Yapily account information and the approved
VRP and/or Single Payments journey, supported HMRC APIs, payslip extraction and
manual entry, FreeAgent, Xero and QuickBooks. Provider failures, expired consent, duplicate
imports, uncertain payment status, disconnection and recovery must be tested as
well as successful journeys. A provider outage may be an accepted limitation
only where Reserved degrades safely, communicates clearly and offers an
appropriate fallback.

Original payslip documents must be securely deleted after the necessary
information has been extracted and checked. Data retention, privacy, security,
account deletion, payment responsibilities and applicable regulatory boundaries
must be documented, implemented and appropriately reviewed before real customer
data or money movement is enabled.

The October product may show **Could Making Tax Digital apply to you?** using a
clearly qualified, forward-looking indication based on relevant sole-trader,
UK-property and foreign-property gross income. It must not claim that Reserved
is "MTD ready", provide MTD filing, or state that MTD definitely applies when
the customer's eligibility facts remain incomplete.

Launch also requires production monitoring, recoverable backups, tested
restoration and rollback, provider-outage handling, incident response,
customer-support escalation and clear ownership of tax-rule, API and security
updates.

The final launch decision must be one of:

- **Ready for the bounded October launch**
- **Ready subject to explicitly documented and founder-accepted limitations**
- **Not ready**

A limitation cannot be accepted where it undermines a supported tax
calculation, reserve recommendation, payment safety, privacy or security;
conceals missing mandatory assurance coverage; or allows an artefact to pass
without executing the complete required release gate. A green test suite alone
is not evidence of launch readiness.
