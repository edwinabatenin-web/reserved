# Annual student-loan reconciliation — definitive independent sign-off

Review date: 13 August 2026  
Artifacts: `reserved/engines/annual_loan_reconciliation.py` and focused tests  
Decision: **PASS — bounded internal reconciliation purpose**

## Supported purpose

The component is fit to calculate independently supported 2026/27 annual Self
Assessment Plan 2 and postgraduate loan components from a caller-confirmed,
provenance-bearing annual income basis, then reconcile each component separately
with complete, declared-employment cumulative deduction evidence.

It supports internal evidence-aware component calculation and reconciliation,
including material conflict, missing, stale and apparent-excess states. This PASS
does not approve a customer bill, combined loan balance, filing/payment/refund
instruction, payroll-period calculation, complete annual tax position or reserve
guidance.

## Independent findings

- HMX-002 arithmetic is correct: Plan 2
  `floor((£103,000 − £29,385) × 9%) = £6,625`; PGL
  `floor((£103,000 − £21,000) × 6%) = £4,920`. Each component is floored before
  its own evidenced deduction is subtracted.
- A non-empty declared employment scope is mandatory. Incomplete scope leaves
  deductions and residual null with `insufficient_facts`.
- Effective and observation dates are coherent with 2026/27 and the explicit
  as-of date. Future/outside-period/incoherent evidence is excluded and retained
  in structured decisions.
- Selected, superseded, conflict and excluded evidence retain ID, original
  amount, period, observation time, employment, source, completeness and reason.
- Same-period material conflicts select no candidate and return candidate
  values, difference and residual alternatives. Multi-employment bounds include
  undisputed deductions and are independent of input ordering.
- Missing deduction evidence never becomes zero; the supported annual liability
  remains visible but the remaining amount is null.
- Apparent excess deductions floor the residual at zero and are explicitly not
  described as a confirmed refund.
- Stale evidence is retained, flagged as material uncertainty and reports the
  actual use-versus-exclusion effect after accounting for fresh deductions and
  the zero floor. Adversarial checks passed where fresh deductions consumed none,
  part, all and more than the liability.
- Plan 2 and PGL remain separate. No combined residual field is emitted, and
  customer combined balance, filing, payment and refund uses are prohibited.
- Simultaneous multiple-undergraduate and other unsupported plan inputs return no
  income basis, components or plausible partial liability.

## Verification

All 15 focused tests pass. Additional independent adversarial checks confirmed:

- all six orderings of a two-employment conflict produced the same £2,625–£2,725
  residual range and £100 difference;
- for a £155 liability and £50 stale deduction, stale effects were £50, £10, £0
  and £0 when fresh deductions were respectively £0, £145, £155 and £200;
- incomplete declared scope, future observation, observation-before-effective,
  apparent excess and simultaneous undergraduate inputs all fail safely.

## Limitations and operational gates

- Only 2026/27 Plan 2 and postgraduate components are supported.
- The caller remains responsible for establishing and evidencing the annual
  Self Assessment loan income basis, including qualifying pension relief and
  taxable-income scope.
- Declared employment completeness is an input assertion that must itself be
  established by the acquisition/integration boundary; this component does not
  discover employers.
- `stale_after_days` is a policy parameter. Customer wording and severity remain
  subject to the approved evidence policy and presentation testing.
- Conflict ranges are complete only for identified conflicts; stale results are
  explicitly partial where later deductions may exist.
- Simultaneous undergraduate plans, Plan 1, Plan 4, Plan 5 and unknown plans are
  unsupported here and must continue to fail closed.
- Component outputs must not be combined or presented for any prohibited use
  without a separate approved product-policy and customer-presentation gate.

## Verdict

**PASS within the bounded internal purpose above.** The credible historical
defect set is closed and no material discrepancy remains in the reviewed scope.
This sign-off does not broaden launch scope or approve customer-facing combined
reconciliation.
