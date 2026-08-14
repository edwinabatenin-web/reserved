# Reserved West

## Tax Assurance Programme

### Agent Briefing (READ FIRST)

Read this document before any code or analysis.

Objective:
Determine how the Reserved tax engine behaves, identify weaknesses, improve the engine and build a permanent evidence base before the October beta.

Optimise for evidence quality, not scenario count.

## Progressive Assurance

Stage 1 – Smoke Tests (~30 scenarios)
Question: Are the core calculations and reference implementation sound?
Gate 1: Stop only for systemic Critical issues. Investigate, fix and rerun before proceeding.

Stage 2 – Representative & Boundary (~150 scenarios)
Question: Does the engine behave correctly for intended users and key thresholds?
Gate 2: Proceed only if no systemic issue undermines confidence.

Stage 3 – Interaction Scenarios
Question: Do combinations of supported tax dimensions behave correctly?
Expand the library only while new scenarios provide materially new evidence.

Stage 4 – Tolerance
Question: Does the engine remain robust beyond its intended operating envelope?

## Independent Reference

Build an independent reference calculator from HMRC guidance.
Do NOT derive expected results from the Reserved engine.

## Evidence

Every scenario requires:
- Permanent Scenario ID
- Reproducible inputs
- Engine version
- Reference version
- Expected outputs
- Actual outputs
- Variance

Every confirmed defect becomes a permanent regression scenario.

## Autonomy

Do not pause for routine decisions.
Pause only for:
- genuine legislative ambiguity;
- methodology changes;
- significant architectural decisions.

Deliver:
Capability register, HMRC reference register, independent reference calculator,
Scenario Library, Evidence Register, findings, fixes, regression suite and gate decisions.
