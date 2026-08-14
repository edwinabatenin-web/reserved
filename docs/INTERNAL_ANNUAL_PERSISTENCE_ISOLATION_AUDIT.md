# Internal annual components — persistence isolation audit

Audit date: 13 August 2026  
Decision: **PASS — isolated; no persistence or exposure connection found**

## Scope

Reviewed the internal annual-position calculator, annual loan reconciliation,
reference-only composition, and strict internal snapshot contract against the
database/schema layer, models, API, web routes, customer services, templates,
static scripts and OpenAPI inventory.

## Findings

- No database or model imports any of the four internal modules or their result
  types/functions.
- No database table or write/read path stores an annual-position result, annual
  loan reconciliation, composition, snapshot payload or snapshot version.
- No API or web route imports, serializes, returns or accepts these internal
  results or snapshots.
- No customer service, template or static script consumes these contracts.
- The only production imports among these modules are their intended internal
  dependencies: composition references the annual producers, and the snapshot
  codec references the three approved internal result graphs.
- Existing Optimise scenario JSON persistence and legacy profile/student-plan
  storage are separate legacy paths; they do not store or serialize the new
  annual results or snapshots.

No leakage was found.

## Tripwire

`tests/test_internal_tax_boundary.py` now scans database, models, API, web,
services, templates and static code for module names, public functions and
result-type markers. It also checks the database schema for likely snapshot
storage names and retains the OpenAPI exclusion check. A future persistence,
API or customer connection will fail this test and requires a deliberate
approval and migration/assurance change rather than occurring incidentally.

## Boundary

This audit establishes current technical isolation only. It does not approve
persistence, schema design, retention, refresh, migration, API exposure or
customer use of the snapshot or producer results.
