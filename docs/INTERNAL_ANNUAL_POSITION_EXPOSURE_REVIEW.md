# Internal annual-position customer-boundary review

Review date: 13 August 2026  
Scope: customer/web/API exposure only; no tax-arithmetic re-review  
Decision: **PASS — currently isolated from customer and public API surfaces**

## Current exposure finding

No current web route, API route, customer service, template or browser script
imports or names:

- `integrated_annual_position` / `calculate_annual_position`;
- `annual_loan_reconciliation` / `reconcile_annual_student_loans`;
- `annual_position_composition` / `compose_internal_annual_position`.

The only non-test cross-import is internal composition importing the other two
internal result types. `reserved/engines/__init__.py` does not export any of the
three modules/functions. The public API blueprint exposes only database health.
The internal OpenAPI inventory contains no marker or result path and explicitly
states that no complete annual tax-position API exists and that the contract is
an internal non-production preview.

The composition result also prohibits customer presentation, reserve guidance,
filing, payment and refund uses. No current route serialises its dataclasses or
passes them into a template. The existing focused boundary/OpenAPI tests pass.

## Legacy customer surfaces are separate

The active dashboard is not using any of the three internal results. It calls
the legacy incremental invoice estimator and constructs a YTD/projected reserve
view in `reserved/services/dashboard.py`. The optimise page separately calls
`reserved.engines.optimise` for pension/taper/HICBC scenarios. These outputs do
not inherit the internal annual-position assurance or evidence contract.

There is nevertheless a material **semantic-collision risk**:

- the dashboard says “Estimated full-year liability” and “Estimated tax to set
  aside” even though its annual target is a run-rate projection of legacy YTD
  incremental liability;
- the guided tour says the calculator provides an “exact split” and refers to
  “real HMRC thresholds”;
- the dashboard service's internal commentary calls its result the “correct
  total reserve amount to hold”;
- optimise describes a projected full-year tax position and total direct
  liability, but it is a separate scenario model and excludes the new evidence-
  aware annual composition/reconciliation contract.

Those statements do not expose internal objects, but customers or reviewers
could mistake them for the assured integrated annual position. No accuracy,
completeness, reconciliation or approval claim for the internal components may
be inferred from those pages. Customer-copy fitness remains a separate product
and WP17/WP20 gate.

The dashboard does contain a useful fail-closed boundary for stored simultaneous
undergraduate plans: it catches the legacy estimator's unsupported-plan error
before allocation, YTD totals or reserve guidance are produced. That is distinct
from exposing the internal annual-loan result.

## Required regression gates

Maintain the current non-customer status with all of these automated gates:

1. **Import graph:** fail if any file under `reserved/web`, `reserved/api`,
   `reserved/services`, `reserved/templates` or `reserved/static` imports,
   references or dynamically loads any internal module/function/type marker.
   Include AST import inspection and string/dynamic-import scanning.
2. **Public export:** assert `reserved.engines.__all__` and package attributes do
   not expose internal functions, result types or composition types.
3. **Route inventory:** enumerate Flask URL rules and assert no endpoint name,
   view module or response content contains internal contract names, including
   `reserved-estimate-envelope/1.0-internal`,
   `reserved-annual-loan-reconciliation/1.0` and
   `reserved-internal-annual-composition/1.0`.
4. **API/OpenAPI:** scan all API blueprints and the OpenAPI document for module,
   function, contract-version and internal result-field markers. Preserve the
   explicit “no complete annual tax-position API” statement.
5. **Serialization:** fail if generic dataclass/JSON serialization of
   `AnnualPositionResult`, `AnnualLoanReconciliation` or
   `InternalAnnualComposition` is introduced in customer layers or response
   helpers.
6. **Template context:** instrument representative legacy and v2 dashboard,
   optimise and API requests and assert no internal result instance or internal
   contract-version string reaches template context or response payloads.
7. **Prohibited-use behavior:** preserve unit tests showing composition never
   emits a combined balance and retains customer-presentation/reserve/payment/
   filing/refund prohibitions for calculated, stale, conflict, missing and
   unsupported cases.
8. **Legacy identity:** response/template contract tests must keep legacy
   dashboard and optimise values explicitly identified as incremental/YTD/run-
   rate or scenario projections, never as the integrated annual position,
   evidence-reconciled balance, approved full bill or confirmed amount due.
9. **Unsupported profile:** retain end-to-end route tests proving simultaneous
   undergraduate profiles show an unavailable/unsupported state with no
   allocation, reserve, annual target or partial monetary fallback.
10. **Approval tripwire:** any deliberate import into a customer/API layer must
    fail these gates until a separate persistence, security/privacy, API,
    uncertainty, customer-copy/accessibility and final launch approval changes
    the internal contract and prohibited uses deliberately.

The existing `tests/test_internal_tax_boundary.py` substantially covers the
first and fourth principles, but its customer roots currently omit
`reserved/api`, and it does not cover public exports, contract-version/result-
field serialization or runtime template/response contexts. Those are required
extensions, not evidence of a present leak.

## Verdict

**PASS for current technical non-exposure.** The three internal annual-position
components cannot presently reach customer/web/API results through the inspected
import and routing graph. This PASS does not approve legacy dashboard/optimise
claims or customer presentation of any internal result. The regression gates
above are the minimum controls required to preserve that status.
