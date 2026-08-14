# WP7 assurance remediation plan

Status: in progress. This plan repairs the evidence framework; it does not change production tax calculations.

## Separation of roles and artifacts

1. **Fixture derivation** uses primary authority and manual, reviewable workings. It must not read production or West calculation code or execute either calculator.
2. **Fixture review** checks sources, applicability, arithmetic, rounding and scope. The reviewer must be different from the engine implementer and, wherever practical, different from the fixture author.
3. **Fixture execution** is a generic adapter that supplies fixture inputs to the engine and compares output with immutable literals. It may know field names but must contain no tax formula.
4. **Engine implementation** may read approved fixture inputs and expected outputs but must not alter them. Disagreements become findings.
5. **Gate review** audits provenance and coverage before considering pass/fail counts.

The fixture schema is `docs/fixtures/WP7_FIXTURE_SCHEMA.json`. A fixture cannot be labelled `independent_validation` until the review decision is approved and reviewer identity/date are present.

`docs/fixtures/WP7_FIXTURE_INTEGRITY.json` pins every draft pack by SHA-256. Any fixture edit must fail structural checks until the affected result is re-derived/reviewed as appropriate and the manifest is deliberately updated. A checksum proves change control, not tax correctness.

## Required evidence tranches

| Tranche | Families | Minimum coverage before WP7 PASS |
|---|---|---|
| A | Non-savings Income Tax, PA taper, pension RaS/ANI | Representative; every statutory boundary ± £1; full taper; additional rate; pension crossing each ANI boundary; sequential differential |
| B | Class 4 NI, individual and multiple student loans | Every threshold ± £1; rate changes; multiple undergraduate selection; undergraduate + PGL; liability/deduction distinction |
| C | PAYE evidence reconciliation | Multiple employments; representation-aware selection; aggregate vs employment evidence; provenance-preserving conflicts; stale/missing data; quantified uncertainty effect where determinable; overpayment; no double counting |
| D | HICBC | £60k/£80k ± £1/£200; child count; partial year; partner/highest-income facts; pension ANI interaction; deductions/elections limitations |
| E | Savings and dividends | Required ordering; starting-rate erosion; PSA class change; dividend allowance; band crossings; PA taper and ANI inclusion |
| F | UK and foreign property | UK property profit/loss inputs; finance-cost boundary if supported; foreign-property gross/net inputs; residence assumption; foreign tax recorded; relief explicitly excluded until separately validated |
| G | MTD readiness | Prior-return year; gross qualifying income; combined trade/property; exact threshold vs over threshold; excluded income; exemptions/unknown state |
| H | Major mixed-income interactions | PAYE + trade + property + savings/dividends; PA allocation/ordering; taper; pension; HICBC; student-loan liability and deductions |

Current artifacts cover initial examples in every tranche except the full H interaction matrix. The core pack has been expanded at the basic/higher boundary, taper, additional rate, pension/ANI crossings, Class 4 and annual student-loan boundaries. Savings and dividend coverage now includes starting-rate, PSA, allowance and rate-band transitions. Formal second-person review has approved the 53-fixture v1 pre-implementation pack; the core and PAYE-evidence packs remain pending, so coverage and approval are not yet sufficient for PASS.

## Gate rules

WP7 remains NOT FIT until:

- all v1 families have an explicit supported, limited or deferred evidence classification;
- every supported validation-critical family has approved independent fixtures;
- no expected result is runtime-generated;
- automated lineage checks find no production/West imports in fixture artifacts or derivation tooling;
- representative manual samples are independently rechecked;
- known historical incorrect evidence is excluded from pass counts;
- the rebuilt runner reports fixture identity and provenance rather than a mutable reference-calculator version;
- material discrepancies are resolved or cause a NOT FIT decision.

## Deliberate limitations

Foreign Tax Credit Relief is treaty- and fact-dependent. Initial foreign-property fixtures may validate gross UK tax before credit and evidence capture only. Reserved must not calculate or claim validated FTCR until a separately bounded rule set and independent fixtures exist.

PAYE and student-loan payroll deductions are evidence/reconciliation problems as well as annual-liability calculations. Fixtures must not treat annual liability and periodic deductions as interchangeable.
