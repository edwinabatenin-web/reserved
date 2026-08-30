# Reserved v1 work-package sequence

Updated 13 August 2026. The order below is mandatory for tax-engine work.

| WP | Work package | Gate/status |
|---:|---|---|
| 1 | Scope and architecture audit | Complete |
| 2 | Customer language and claims | Substantially complete |
| 3 | 2026/27 rule audit | Core audit complete |
| 4 | Existing tax-engine correction | Complete for identified defects |
| 5 | Personal Allowance taper investigation and regression | Complete |
| 6 | Reserved West independence repair and standard | Standard adopted; affected evidence downgraded pending reassessment |
| **7** | **Reserved West Assurance Review** | **SCOPED PASS for at-most-one undergraduate plan plus optional PGL; 104/107 arithmetic fixtures approved; three multi-plan candidates remain pending and excluded as unsupported-for-decision** |
| **7U** | **Estimate Uncertainty & Evidence Quality** | **Gate U1 PASS; purpose-specific Gates U2–U5 continue with later packages** |
| 8 | Integrated annual tax position | Independently passed for isolated internal approved-scope calculation; customer promotion/reliance blocked |
| 9 | PAYE and student-loan reconciliation | Internal Plan 2/PGL reconciliation and its WP7U U2 mapping independently passed; multi-undergraduate fails closed; customer use blocked |
| 10 | HICBC liability and scenarios | Integrated liability passed internally; disconnected explicit-fact scenario component implemented, independent review pending |
| 11 | MTD readiness | Core component complete; eligibility/exemption state now fails closed |
| 12 | HMRC integration | Foundations complete; sandbox journey outstanding |
| 13 | Accounting integrations | Foundations complete; sandbox journeys outstanding |
| 14 | Yapily/banking | Foundations complete; sandbox journey outstanding |
| 15 | Google and Apple authentication | In progress as a non-overlapping parallel stream |
| 16 | Security and privacy | In progress as a non-overlapping parallel stream |
| 17 | Accessibility and UX | In progress as a non-overlapping parallel stream |
| 18 | API specification and technical documentation | In progress as a non-overlapping parallel stream |
| 19 | Full regression and sandbox verification | Local suite green at record time (historical 995-test count, now superseded); target-environment and sandbox journeys externally blocked/outstanding |
| 20 | Final launch gate and handover | Ongoing records; final decision outstanding |

Historical readiness-gate reasoning is recorded in `docs/CLAUDE_AUDIT_GATE.md`.
The governing new-agent handover is `RESERVED_NEW_AGENT_HANDOVER.md`. The
handover is **ADEQUATE** for independent review; this is not an official audit,
certification or the final launch gate.

## WP7 — Reserved West Assurance Review

WP7 is separate from WP6. WP6 repairs the independence methodology and labels; WP7 independently assesses whether the repaired framework is fit to assure subsequent tax-engine development.

WP7 must:

1. reconstruct the original West scope and inventory evidence across all confirmed v1 calculation families;
2. classify every relevant evidence family as genuinely independent, shared-lineage/regression-only, or inadequate/missing;
3. independently recalculate a representative sample without production helpers, West helpers, copied formulas, shared configuration or West's own independence assertions;
4. assess boundary, ordering, taper, pension, threshold and mixed-income coverage;
5. document gaps, remediation and a reasoned **PASS** or **NOT FIT** decision.

WP8 implementation may proceed incrementally while WP7 approval completes,
provided each implemented family is based on independently approved
pre-implementation fixtures, production and validation logic remain separate,
and unapproved evidence is not treated as validated. WP7 remains a hard gate
for promoting the integrated engine to customer reliance, claiming accuracy,
or passing the launch gate. Core, PAYE and Tranche H outputs whose evidence is
pending or rejected must remain explicitly unvalidated and disabled from any
customer-facing reliance purpose.

WP7U is a separate cross-product contract gate. It may progress while WP7
approval completes, but Gate U1 in `docs/ESTIMATE_UNCERTAINTY_STANDARD.md` must
pass before WP8 freezes its integrated data model or customer output. WP7 tests
tax arithmetic; WP7U ensures the facts supplied to that arithmetic do not create
misleading certainty. Neither gate substitutes for the other.

During WP8, major expected-result fixtures must be independently derived and
approved alongside or before their implementation tranche under the Reserved
West Independence Standard. Engine output cannot be used to backfill or amend
expected values. Discrepancies return to WP7 review; implementation work does
not create approval evidence.

WP7 assurance and WP8 implementation may run concurrently only with explicit
file ownership: assurance reviewers do not edit production tax calculations,
and implementation streams do not edit validation-critical fixtures or their
expected values. Overlapping tax-engine changes are sequenced and reconciled
deliberately. Other unrelated work may continue in parallel.
