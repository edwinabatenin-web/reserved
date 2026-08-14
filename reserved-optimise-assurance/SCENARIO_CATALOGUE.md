# Initiative 002 — Scenario Catalogue

Reference catalogue of all scenarios exercised across the four gate test files.

## Gate 1: Isolation Scenarios

| ID | Mechanism | Input | Expected | File |
|---|---|---|---|---|
| G1-PA-01 | PA taper | ANI £99,999 | PA = £12,570 | gate1_isolation.py |
| G1-PA-02 | PA taper | ANI £100,000 | PA = £12,570 (threshold inclusive) | gate1_isolation.py |
| G1-PA-03 | PA taper | ANI £100,001 | PA = £12,569.50 | gate1_isolation.py |
| G1-PA-04 | PA taper | ANI £112,570 | PA = £6,285 | gate1_isolation.py |
| G1-PA-05 | PA taper | ANI £125,140 | PA = £0 | gate1_isolation.py |
| G1-PA-06 | PA taper | ANI £150,000 | PA = £0 | gate1_isolation.py |
| G1-PA-07 | PA marginal rate | 40% IT rate | EMR = 60% | gate1_isolation.py |
| G1-PA-08 | PA restoration | ANI £110,000 | Need £10k pension | gate1_isolation.py |
| G1-CB-01 | HICBC | ANI £60,000, 1 child | HICBC = £0 | gate1_isolation.py |
| G1-CB-02 | HICBC | ANI £70,000, 1 child | HICBC = 50% of CB | gate1_isolation.py |
| G1-CB-03 | HICBC | ANI £80,000, 1 child | HICBC = 100% of CB | gate1_isolation.py |
| G1-CB-04 | HICBC | ANI £90,000, 1 child | HICBC = capped at CB | gate1_isolation.py |
| G1-CB-05 | HICBC | ANI £70,000, 0 children | HICBC = £0 | gate1_isolation.py |
| G1-CB-06 | HICBC clearance | ANI £70,000 | Need £10k pension | gate1_isolation.py |
| G1-CB-07 | CB rates | 1 child | £26.60 × 52 = £1,383.20/yr | gate1_isolation.py |
| G1-CB-08 | CB rates | 2 children | £1,383.20 + £915.20 = £2,298.40 | gate1_isolation.py |
| G1-RaS-01 | Pension net/gross | £8,000 net | £10,000 gross | gate1_isolation.py |
| G1-RaS-02 | Pension BRL | £10k pension | BRL extended to £60,270 | gate1_isolation.py |
| G1-RaS-03 | Pension BRL cap | £100k pension | BRL capped at £125,140 | gate1_isolation.py |
| G1-RaS-04 | IT saving at £60k | £5k pension | £1,000 IT saving | gate1_isolation.py |
| G1-RaS-05 | IT saving in taper | £10k pension at £110k | > £5,000 saving | gate1_isolation.py |
| G1-XC-01 | Product vs ref | £110k income, £5k pension | ANI matches | gate1_isolation.py |
| G1-XC-02 | Product vs ref | £110k income, £5k pension | PA matches | gate1_isolation.py |
| G1-XC-03 | Product vs ref | £110k income, £5k pension | IT matches | gate1_isolation.py |
| G1-XC-04 | Product vs ref | £75k, £0, CB2 | HICBC matches | gate1_isolation.py |
| G1-XC-05 | Product vs ref | £115k, £3k, extra £15k | IT reduction matches | gate1_isolation.py |

## Gate 2: Archetype Scenarios

| ID | Archetype | Income | Pension | CB | Key assertion | File |
|---|---|---|---|---|---|---|
| G2-A1 | Below all thresholds | £55,000 | £0 | None | No PA taper, no HICBC | gate2_archetypes.py |
| G2-HICBC-L | HICBC lower | £60,000 ANI | £0 | 1 child | HICBC = £0 | gate2_archetypes.py |
| G2-HICBC-M | HICBC mid | £70,000 ANI | £0 | 1 child | HICBC = 50% CB | gate2_archetypes.py |
| G2-HICBC-U | HICBC upper | £80,000 ANI | £0 | 1 child | HICBC = 100% CB | gate2_archetypes.py |
| G2-PA-L | PA taper entry | £100,001 ANI | £0 | None | PA = £12,569.50 | gate2_archetypes.py |
| G2-PA-M | PA half | £112,570 ANI | £0 | None | PA = £6,285 | gate2_archetypes.py |
| G2-PA-U | PA eliminated | £125,140 ANI | £0 | None | PA = £0 | gate2_archetypes.py |
| G2-BOTH | Combined | £115,000 | £5,000 | 2 children | Both charges, both opportunities | gate2_archetypes.py |
| G2-AA | AA ceiling | £200,000 | £0 | None | Suggestion capped at £60k | gate2_archetypes.py |
| G2-CLEAR-PA | Clear PA taper | £110,000 | £0, + £10k | None | After PA = £12,570 | gate2_archetypes.py |

## Gate 3: Interaction Scenarios

| ID | Family | Description | File |
|---|---|---|---|
| G3-A-01 | Pension + PA | Partial PA restoration | gate3_interactions.py |
| G3-A-02 | Pension + PA | Full PA restoration | gate3_interactions.py |
| G3-A-03 | Pension + PA | Over-contribution (below £100k) | gate3_interactions.py |
| G3-A-04 | Pension + PA | IT reduction matches reference | gate3_interactions.py |
| G3-B-01 | Pension + HICBC | Partial HICBC reduction | gate3_interactions.py |
| G3-B-02 | Pension + HICBC | Full HICBC elimination | gate3_interactions.py |
| G3-B-03 | Pension + HICBC | HICBC reduction matches reference | gate3_interactions.py |
| G3-B-04 | Pension + HICBC | total_benefit = IT + HICBC always | gate3_interactions.py |
| G3-C-01 | Both simultaneously | Both charges apply at £115k ANI | gate3_interactions.py |
| G3-C-02 | Both simultaneously | Large pension eliminates both | gate3_interactions.py |
| G3-C-03 | Both simultaneously | Total benefit covers both savings | gate3_interactions.py |
| G3-C-04 | Both simultaneously | Matches reference oracle | gate3_interactions.py |
| G3-D-01 | Salary sacrifice | No SS in opportunity output | gate3_interactions.py |
| G3-D-02 | Salary sacrifice | No SS parameter in engine | gate3_interactions.py |
| G3-E-01 | Multi-income | PAYE + freelance triggers PA taper | gate3_interactions.py |
| G3-F-01 | YTD projection | YTD that projects above £100k triggers PA_TAPER | gate3_interactions.py |
| G3-F-02 | Override | Income override supersedes YTD | gate3_interactions.py |
| G3-G-01 | Idempotency | calculate_position idempotent | gate3_interactions.py |
| G3-G-02 | Idempotency | model_pension_scenario idempotent | gate3_interactions.py |
| G3-H-01 | Incomplete | Empty profile → £0 income, no opps | gate3_interactions.py |
| G3-H-02 | Incomplete | Near threshold, no CB → incomplete | gate3_interactions.py |
| G3-H-03 | Incomplete | Far from threshold, no CB → no opp | gate3_interactions.py |
| G3-H-04 | Input validation | Negative pension rejected | gate3_interactions.py |

## Gate 4: Extreme and Invariant Scenarios

| ID | Family | Input | Assertion | File |
|---|---|---|---|---|
| G4-EX-01 | Extreme | Income £0 – £1,000,000 (8 values) | No crash, ≥ 0 tax | gate4_extremes.py |
| G4-EX-02 | Extreme | Pension £0 – £100,000 (6 values) | No crash | gate4_extremes.py |
| G4-EX-03 | Extreme | Pension > income | ANI clamped to 0 | gate4_extremes.py |
| G4-EX-04 | Extreme | CB = £999,999 | HICBC capped at CB | gate4_extremes.py |
| G4-EX-05 | Extreme | Income = 0 | All zeros except PA | gate4_extremes.py |
| G4-INV-01 | Non-negativity | it_reduction ≥ 0 (6 scenarios) | Always ≥ 0 | gate4_extremes.py |
| G4-INV-02 | Non-negativity | hicbc_reduction ≥ 0 (3 scenarios) | Always ≥ 0 | gate4_extremes.py |
| G4-INV-03 | Additivity | total = IT + HICBC (4 scenarios) | Exact equality | gate4_extremes.py |
| G4-INV-04 | No double-counting | basic_rate_relief not in total | Verified | gate4_extremes.py |
| G4-INV-05 | Non-negativity | IT ≥ 0 at all tested incomes | Always ≥ 0 | gate4_extremes.py |
| G4-INV-06 | HICBC cap | HICBC ≤ annual_cb always | Verified | gate4_extremes.py |
| G4-INV-07 | Zero pension | 0 extra pension → 0 benefit | Verified | gate4_extremes.py |
| G4-INV-08 | Monotonicity | after IT ≤ before IT always | Verified | gate4_extremes.py |
| G4-ADV-01 | UX invariant | SS not implied as available | Verified | gate4_extremes.py |
| G4-ADV-02 | UX invariant | Incomplete ≠ available | Verified | gate4_extremes.py |
| G4-ADV-03 | UX invariant | Negative pension rejected | Verified | gate4_extremes.py |
| G4-ADV-04 | UX invariant | Caveats present in all results | Verified | gate4_extremes.py |
| G4-ADV-05 | UX invariant | what_to_confirm non-empty | Verified | gate4_extremes.py |
| G4-STAB-01 | Stability | £1,000,000 income, no crash | PA_TAPER detected | gate4_extremes.py |
| G4-STAB-02 | Stability | £60,000 pension (AA limit) | No crash | gate4_extremes.py |
| G4-STAB-03 | Stability | Penny precision maintained | 2dp always | gate4_extremes.py |
| G4-REG-01 | Regression | Basic rate taxpayer £30k | Tax = £3,486 | gate4_extremes.py |
| G4-REG-02 | Regression | Higher rate taxpayer £60k | Tax = £11,432 | gate4_extremes.py |
| G4-REG-03 | Regression | PA taper at £110k | Consistent with reference | gate4_extremes.py |
| G4-REG-04 | Regression | RaS band extension at £60k | £1,000 saving | gate4_extremes.py |
| G4-REG-05 | Regression | Additional rate above £125,140 | 45% on excess | gate4_extremes.py |
| G4-REG-06 | Regression (EL-003) | £200k income, £80k pension | Tax = £58,201 | gate4_extremes.py |
