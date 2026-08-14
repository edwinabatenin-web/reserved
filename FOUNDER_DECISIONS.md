# Founder decisions

## Resolved: v1 tax scope (12 August 2026)

V1 covers England, Wales and Northern Ireland and includes PAYE/multiple employment, sole trade, dividends, savings, UK and foreign property, student loans, HICBC and MTD readiness. Scottish Income Tax, Capital Gains Tax and full MTD filing are post-v1. See `docs/V1_TAX_SCOPE.md`.

This is no longer an open decision. Any change should be recorded as a new founder scope decision rather than inferred from dormant code.

## Resolved: simultaneous undergraduate Student Loan treatment (13 August 2026)

Reserved v1 may calculate at most one undergraduate plan, optionally plus a
postgraduate loan. Where simultaneous undergraduate plans or an unknown plan
value is supplied, the annual Self Assessment treatment is
`unsupported_for_decision`: no loan amount, partial total, allocation, reserve
or set-aside may be shown, and the customer must verify the applicable treatment
with HMRC or a qualified tax adviser. This is a bounded product-scope decision,
not approval of the three pending arithmetic fixtures.

## Money set-aside scope for v1

**QUESTION**  
Will v1 calculate and track amounts only, support user-authorised one-off transfers, or automate transfers?

**WHY IT MATTERS**  
Payment initiation has different consent, provider, security and regulatory requirements from read-only bank data.

**RECOMMENDED DEFAULT**  
V1 calculates and tracks the estimated amount to set aside. Keep money movement provider-neutral and out of launch scope until separately approved.

**ALTERNATIVES**  
Manual transfer guidance; Yapily single payment initiation; Yapily sweeping VRP; another regulated provider.

**CAN DEVELOPMENT CONTINUE WITHOUT IT?**  
Yes. Tax estimation, tracking, AIS and provider-neutral interfaces can continue.

**WHAT IS BLOCKED?**  
Payment initiation implementation and its final customer journey.

## Customer-facing “Optimise” terminology

**QUESTION**  
Should the feature be renamed to “Tax scenarios” or “Explore tax effects”?

**WHY IT MATTERS**  
“Optimise” and “opportunity” may imply a recommendation rather than a factual calculation.

**RECOMMENDED DEFAULT**  
Use “Tax scenarios” and factual descriptions of calculated effects.

**ALTERNATIVES**  
Retain “Optimise” with stricter explanatory copy; remove the feature from v1.

**CAN DEVELOPMENT CONTINUE WITHOUT IT?**  
Yes. Internal compatibility names can remain while customer copy is separated.

**WHAT IS BLOCKED?**  
Final navigation and page naming.

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

## PAYE uncertainty operating parameters

**DECISIONS STILL REQUIRED**

- Materiality: the absolute and/or percentage difference that triggers a user warning.
- Recency: evidence-type and tax-year-stage windows; there will be no unexplained universal cutoff.
- Completeness: minimum fields for HMRC cumulative observations, P60s, P45s and payslips.
- Representation and identity: when an aggregate can be compared with or preferred to employment-level evidence.
- Conflict display: when to show a range, a qualified point estimate or “effect not determinable”.
- Customer labels: the exact evidence-quality vocabulary and explanations.
- Overpayment: how to describe a possible overpayment without implying a confirmed refund.

**RECOMMENDED IMPLEMENTATION DEFAULT**  
Keep these values explicit and configurable. Until approved, preserve the
evidence and conflict, use conservative factual wording, and avoid treating a
policy-dependent point estimate as independently validated.

## Annual liability and deduction presentation

**QUESTION**  
Should Reserved present statutory annual liabilities, evidenced PAYE/student-loan deductions and the resulting estimated remaining position as separate lines, and under what conditions may they be combined?

**WHY IT MATTERS**  
Annual Self Assessment student-loan liability is not the same calculation as payroll-period deductions. PAYE and payroll deductions are evidence that may be incomplete, stale or later corrected. Combining them without explicit provenance could imply more certainty than the inputs support.

**RECOMMENDED DEFAULT**  
Keep calculated annual liabilities and evidenced deductions visibly separate,
show their dates/sources, and label each subtraction as an estimated
reconciliation. For v1, do not use a single combined amount as the primary or
only figure. A secondary combined estimated remaining position may be shown only
when all included components use compatible periods/bases, provenance is
available, material conflicts are resolved or visibly bounded, excluded
liabilities are named, and the components remain immediately visible. Otherwise
show the separate figures and state that a combined effect cannot yet be
determined reliably.

**CAN DEVELOPMENT CONTINUE WITHOUT IT?**  
Yes. Independent statutory fixtures, evidence capture and separate reconciliation arithmetic can continue.

**WHAT IS BLOCKED?**  
HMX-001 and HMX-002 are now admitted for their narrow pre-FTCR component
purposes; HMX-003 remains excluded. Final combined-position display and
customer wording remain blocked, as does any use of the current composition
prototype for persistence, API publication or customer presentation because
its independent review found material provenance and uncertainty loss.

**FOUNDER INPUT NEEDED NOW?**  
No. Development can proceed safely using separate component lines and blocking
the combined customer total. Founder approval is needed before enabling a
combined v1 presentation or finalising its wording.
