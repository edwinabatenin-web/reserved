# Annual-position composition — independent assurance review

Review date: 13 August 2026  
Artifacts: `reserved/engines/annual_position_composition.py` and
`tests/test_annual_position_composition.py`  
Decision: **NOT FIT as the WP7U-compatible internal composition contract**

## Boundary

This was a review-only assessment against the adopted WP7U contract mapping and
the bounded annual-tax and annual-loan component contracts. No production code,
test, fixture, manifest or shared sprint record was edited. The composition was
assessed as an internal, non-customer boundary only; no customer, reserve,
filing, payment or refund use was considered permissible.

## Controls that pass

- Tax-year mismatch and blank references fail closed.
- The two stable references are retained without embedding or recomputing their
  source results.
- Annual-tax money and each loan component remain separate. There is no combined
  balance, amount-due field or arithmetic aggregation.
- Source calculation statuses, tax unsupported-family names, tax limitations,
  loan-component evidence IDs and component uncertainties are copied literally.
- Completeness is conservative: only a calculated tax total plus non-empty,
  fully calculated loan components with evidenced deductions and residuals can
  produce `components_available`.
- The top-level contract expressly prohibits customer presentation, reserve
  guidance, filing, payment and refund use.
- Existing tests cover the happy path, unsupported annual tax, missing loan
  evidence, absence of combined money, prohibited customer presentation,
  tax-year mismatch and blank tax reference.

These controls make the object safer than a combined-balance DTO, but they do
not make it a sufficient WP7U composition boundary.

## Material blockers

### 1. Loan evidence provenance is discarded

The source reconciliation carries basis evidence IDs, retained evidence IDs,
structured decisions for selected/superseded/conflicting/excluded observations,
selection reasons, original values, source references, effective/observation
dates and completeness. Composition retains only selected evidence IDs and a
free-text uncertainty tuple. A persisted or refreshed composition therefore
cannot reconstruct why evidence was selected, what was rejected, or whether a
different representation was considered. That fails WP7U's minimum evidence-
item and selection-retention boundary.

### 2. Known ranges and determinable uncertainty effects are discarded

The source loan component can expose conflict candidate amounts, conflict
difference, residual low/high bounds, range completeness, apparent excess and
stale-selected amount. None survives composition. `conflict_requires_review`
or `calculated_with_material_uncertainty` is preserved as a label, but the known
effect and range basis are lost. WP7U requires determinable effects and bounds
to remain distinct from uncharacterised uncertainty.

### 3. Source scope and prohibitions are not propagated completely

The composed loan wrapper omits `unsupported_plans`, basis evidence IDs,
ruleset version, as-of date, declared employment scope and the source
`prohibited_uses`. The top-level prohibition is conservative, and its
`customer_presentation` plus no-combined-balance limitation broadly covers the
source's `customer_combined_balance` restriction, but exact source restrictions
and scope are validation-critical metadata and should not depend on semantic
equivalence inferred by consumers.

The annual-tax wrapper similarly omits the ruleset version and included-family
list. It retains unsupported families, but a consumer cannot distinguish the
full declared included scope from the selected money fields alone.

### 4. Composition status is too coarse for an integration boundary

Every state other than fully calculated becomes `component_set_incomplete`.
The nested producer statuses prevent outright concealment, but the top level
does not distinguish insufficient facts, unsupported rule, conflict requiring
review or calculated-with-material-uncertainty. This is not compatible with the
adopted common calculation-status vocabulary and makes safe downstream routing
need producer-specific inspection.

### 5. Stable-reference validation is minimal

References are required to be non-blank, which is useful, but there is no test
or invariant that tax and loan references are distinct, typed/namespace-bound,
or immutable identifiers rather than mutable display labels. This is a smaller
blocker than the provenance loss but prevents the current check from proving
stable identity semantics.

## Test and verification gaps

Focused execution was not possible in this environment because the available
Python lacks Flask (and pytest). Static review found no tests for:

1. unsupported loan-plan propagation;
2. source prohibition and ruleset/scope retention;
3. conflict ranges and evidence-decision retention;
4. stale or excess-deduction effects;
5. `calculated_with_material_uncertainty` propagation;
6. blank loan reference (only blank tax reference is exercised); or
7. distinct/type-stable references.

## Verdict

**NOT FIT as an internal WP7U-compatible composition contract.** It is
appropriately non-customer-facing, does not combine money and fails closed on
basic completeness. However, it strips validation-critical provenance, known
uncertainty effects, scope, exact restrictions and status semantics at the
point they most need to be preserved for integration.

It may remain an isolated prototype object, but it must not be persisted,
served, used as the WP8 contract freeze, or described as a complete internal
annual-position envelope. A revised boundary should either compose the adopted
`EstimateEnvelope` directly or losslessly reference/retain each producer's
evidence, uncertainty, scope, policy/ruleset and prohibition metadata, with
focused tests for every non-calculated state. No customer or reserve use is
permitted before separate re-review.

---

## Supplemental independent re-review after remediation — 13 August 2026

**Decision: PASS for bounded, ephemeral internal component linking only.**

This supplement independently rechecked the remediated implementation against
each blocker above and adversarially inspected complete, insufficient,
unsupported, conflict and material-uncertainty paths. It did not edit or use the
implementation's outputs as validation fixtures. The focused test module was
executed in the repository's isolated test environment: **11 passed**.

### Closure of prior blockers

1. **Evidence provenance — closed.** Each referenced loan component now retains
   selected and retained evidence IDs, selection reasons and every structured
   `LoanEvidenceDecision`. Those decisions preserve original amount, source
   kind/reference, effective and observation dates, employment identity,
   completeness, decision and reason. Basis evidence IDs are also retained.
2. **Ranges and effects — closed.** Conflict candidates/difference, residual
   low/high bounds, range completeness, apparent excess and stale
   reconciliation effect are copied without recomputation. The conflict test
   verifies candidate-linked decisions and exact bounds; the stale/excess test
   verifies both known effects survive.
3. **Scope and prohibitions — closed for this purpose.** Loan ruleset, unsupported
   plans, as-of date, declared employment scope, limitations and exact producer
   prohibitions survive. Tax ruleset, included/unsupported families and
   limitations survive. The composition adds stricter top-level prohibitions
   covering customer presentation, reserve guidance, filing, payment and
   refund, while the source's `customer_combined_balance` prohibition remains
   present at the loan boundary.
4. **Status propagation — closed.** The top-level status now distinguishes
   conflict, unsupported rule/plan combination, insufficient facts and
   calculated-with-material-uncertainty, using fail-closed precedence. Literal
   producer statuses remain nested. Only two fully calculated, populated
   component sets yield `components_available`.
5. **Reference identity — closed for an in-process link.** References require
   distinct namespaces (`annual-position:` and `loan-reconciliation:`), a
   non-empty restricted immutable-ID syntax and a maximum identifier length.
   Wrong namespaces, display-label whitespace, empty identifiers and malformed
   cross-type references fail closed.

### Adversarial result

- Unsupported annual FTCR preserves the pre-limitation amount and named
  unsupported family but withholds the tax total and complete-set status.
- Unsupported multiple-undergraduate loans preserve the exact unsupported plan
  state, expose no partial loan components and produce top-level
  `unsupported_rule`.
- Missing deduction evidence preserves annual loan liability but keeps
  deductions/residual null and propagates `insufficient_facts`.
- Conflicting evidence remains unselected and reconstructable from decision
  records and bounds; composition performs no choice or arithmetic.
- Stale/excess evidence retains its material-uncertainty status and determinate
  numerical effects; it cannot be promoted to `components_available`.
- Tax-year mismatch and invalid typed references fail before composition.
- No combined balance, amount due, reserve, refund, filing or payment field is
  introduced.

### Bounded purpose and stopping criterion

The PASS permits this object to link two already-produced results **ephemerally
inside non-customer code** so a caller can inspect their separate components,
scope, provenance and limitations. It does not approve either producer's tax or
reconciliation correctness and does not override their own assurance gates.

This is deliberately not a PASS for persistence, serialisation, API publication,
WP8 public contract freeze or customer presentation. The composition is not the
adopted `EstimateEnvelope`: it has no purpose-fitness decision, calculated-at/
policy identity or common serialised evidence/uncertainty vocabulary. Those are
not defects for the bounded internal link, provided the object remains ephemeral
and prohibited uses are enforced. Before any persistence, API or customer use,
map it losslessly into the adopted WP7U envelope and obtain a separate schema,
purpose-fitness and presentation review.

**Stopping criterion met:** all defects from the first review are closed for
the bounded internal purpose, every currently representable non-calculated
producer state fails closed, and further work would belong to the separate
envelope/persistence/presentation gate rather than this component linker.
