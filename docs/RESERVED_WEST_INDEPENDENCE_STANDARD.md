# Reserved West Independence Standard

Status: mandatory validation standard. Adopted 13 August 2026.

## Rule

Validation-critical reference fixtures and expected results must be derived independently of Reserved's production calculation logic. Shared calculation code, copied formulas, shared helpers, production configuration imports, or expectations generated from production output are prohibited between the engine under test and its oracle.

## Minimum evidence for a validation fixture

Each fixture must record:

- the primary statutory or HMRC/GOV.UK source and applicable tax year;
- the input facts and territorial assumptions;
- a human-reviewable derivation or externally authoritative expected result;
- the expected value as a fixed literal, with rounding treatment stated;
- the author/reviewer and date of derivation;
- any interaction or limitation not covered.

Boundary and interaction fixtures must be selected from the rule itself, not from branches observed in production code.

## Prohibited validation patterns

- importing production calculation functions or constants into the oracle;
- copying a production formula into a reference calculator;
- generating expected values by running the engine and recording its output;
- treating agreement between two implementations with shared lineage as independent validation;
- changing a fixture merely to match a changed engine without re-deriving it from primary authority.

## Permitted uses of shared code

Generic non-calculation infrastructure such as test runners, serialization and display formatting may be shared only where it cannot affect the expected tax result. Money rounding should be stated in the fixture and independently checked at relevant half-penny boundaries.

## Evidence labels

- **Independent validation** — meets this standard and has passed review.
- **Independent fixture, review pending** — derived independently but not yet second-person reviewed.
- **Cross-implementation consistency** — compares implementations but shares logic, configuration or lineage; useful for regression only.
- **Production regression** — protects established behaviour but is not an accuracy oracle.

Only the first label supports a Reserved West accuracy claim. A suite containing solely consistency or regression tests must not be described as independently validated.

## Enforcement

Every validation-critical test must include fixture provenance. Review must reject any oracle with production imports or copied logic. If shared lineage is discovered later, affected evidence is downgraded immediately and prior readiness claims are corrected. The engine change and independent fixture change must be reviewed separately whenever practical.

