# WP7U minimum contract mapping

Status: adopted contract mapping candidate for Gate U1 review. This fixes
meanings and boundaries before WP8; it does not claim that all producers,
storage or customer surfaces have migrated.

## Version and ownership

- Contract: `reserved-estimate-envelope/1.0`
- Evidence policy: `evidence-policy/2026-08-13`
- Contract owner: Reserved engineering
- Evidence-policy owner: Reserved product/founder, with tax-domain review where statutory interpretation is involved
- Compatibility rule: additive optional fields may be introduced within 1.x;
  changed meanings, required fields, enum removal or weaker fail-closed behavior
  require a major version and migration evidence.

## Boundary vocabulary

`reserved/evidence_uncertainty.py` defines the serialisable logical contract:

- six supported purposes: informational rule, personalised estimate, reserve
  guidance, reconciliation, eligibility/readiness and unsupported for decision;
- purpose fitness: adequate, adequate with material uncertainty, or inadequate;
- calculation status: calculated, calculated with material uncertainty, bounded
  range, insufficient facts, unsupported rule, not applicable, or conflict
  requiring review;
- point/range and bound basis;
- included and unsupported liability families;
- provenance-bearing evidence items;
- characterised or uncharacterised uncertainty and its determinable effect;
- policy/limitation versions and prohibited uses.

## Evidence item minimum

Every selected or competing material input can retain: stable evidence ID,
source and opaque reference, subject/scope, tax year, effective period,
observation time, representation, completeness, recency, selection state/reason,
original value and unit. Selection never deletes the competing item.

## Existing confidence/status mapping

| Existing value | Boundary name | Meaning | Must not mean |
|---|---|---|---|
| PAYE high/medium/low/incomplete | `evidence_quality_legacy` pending structured migration | Fitness/completeness of PAYE evidence | Probability tax is correct |
| Transaction 0–1 confidence | `classification_confidence` | Strength of transaction category classification | Evidence completeness or tax confidence |
| Invoice match 0–100 | `match_confidence` | Strength of invoice/transaction identity match | Confirmed tax treatment |
| MTD incomplete/unknown | `insufficient_facts` | Decisive eligibility facts are missing | Not mandated or exempt |
| Import complete/unverified/incomplete | import evidence status plus purpose fitness | Pagination/count evidence for declared import use | Provider truth or whole-tax-position completeness |
| Provider configured/disabled | operational readiness | Whether an adapter may make a sandbox call | Evidence quality or integration success |
| Fixture review pending/approved | assurance metadata | Whether expected-result evidence may count at a gate | Customer data quality |

A universal percentage confidence in the tax result is prohibited.

## Zero, unknown, omitted and not applicable

- `0`: affirmative supported evidence/calculation establishes zero.
- `null` plus `insufficient_facts`: a required fact is unknown; zero must not be substituted.
- `unsupported_rule`: Reserved knows the relevant treatment is outside its
  validated scope; a partial total names the exclusion.
- omitted input: an uncertainty item records the potentially omitted fact and
  either its bounded effect or `not_determinable`.
- `not_applicable`: affirmative facts establish that a family/rule does not apply.

Examples: missing Child Benefit partner facts are insufficient facts, not zero
HICBC; MTD missing registration/exemption facts are unknown, not not-mandated;
unvalidated Foreign Tax Credit Relief is unsupported, not £0; absent PAYE
evidence is incomplete evidence, not confirmed £0 paid.

## Restricted pending-policy behavior

Unresolved materiality, recency, completeness, conflict or aggregation
parameters use a versioned policy-pending reference. Informational or qualified
personalised estimates may proceed under the conservative defaults where fit.
Reserve guidance and reconciliation that are not adequate must declare
prohibited uses and cannot be presented as filing, payment, refund or confirmed
balance outputs.

## End-to-end contract example

The synthetic test `test_versioned_envelope_preserves_evidence_scope_uncertainty_and_restriction`
demonstrates a reserve-guidance-shaped result that preserves a selected dated
employment evidence item, identifies unsupported Foreign Tax Credit Relief,
records uncharacterised possibly omitted income with an indeterminable effect,
and prohibits filing/payment interpretations. It intentionally reports
`adequate_with_material_uncertainty`, not tax confidence.

## Migration boundary

WP8 must produce the envelope rather than freeze another incompatible public
shape. WP9–14 migrate component evidence under Gate U2. WP17 validates customer
communication and accessibility. Persistence must retain evidence IDs,
selection reasons, policy versions and limitations before any refreshable
provider-backed purpose is enabled. These migrations are later-gate work and do
not need to be falsely represented as complete at U1.
