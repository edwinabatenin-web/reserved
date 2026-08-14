# Initiative 002 — Gate Decisions

Gate decisions are recorded after each full gate-test run.  A gate
PASS requires all test functions in the corresponding file to pass
without error.

Run command (from workspace root):
```
cd reserved-optimise-assurance && \
  PYTHONPATH=/path/to/workspace/reserved-optimise-assurance:/path/to/workspace \
  /path/to/workspace/.venv/bin/python -m pytest tests/ -v --override-ini="addopts="
```

---

## Gate 1 — Isolation

**Status: PASS**  
Date: 10 August 2026  
Result: 37 passed, 0 failed  
Notes: One test was initially wrong (IT saving in taper zone asserted > £5k;
correct value is £3k — corrected with explanation of BRL mechanics).

---

## Gate 2 — Archetypes

**Status: PASS**  
Date: 10 August 2026  
Result: 24 passed, 0 failed  
Notes: One test initially used the wrong pension amount for the combined
PA+HICBC scenario (£15k does not reduce HICBC since ANI remains above £80k);
corrected to £35k to bring ANI below £80k and produce a partial HICBC reduction.

---

## Gate 3 — Interactions

**Status: PASS**  
Date: 10 August 2026  
Result: 24 passed, 0 failed  
Notes: All interaction families passed on first run.

---

## Gate 4 — Extremes

**Status: PASS**  
Date: 10 August 2026  
Result: 51 passed, 0 failed  
Notes: One regression test corrected: £10k pension at £60k income saves £1,946
(not £1,000); clean £1k saving verified with £5k pension.

---

## Overall Initiative 002 Decision

**Status: PASS — ALL FOUR GATES GREEN**  
Date: 10 August 2026  
Total: 136 passed, 0 failed across all four gates

The Optimise engine (`reserved/engines/optimise.py` v1.0.0) is certified
for the 2026/27 tax year (England / Wales / Northern Ireland).

**Pre-launch checklist:**
- [ ] Verify 2026/27 Child Benefit rates against HMRC official announcement
- [ ] Confirm HICBC threshold unchanged at £60k/£80k for 2026/27
- [ ] Ship alongside Settings update (HICBC fields) and nav entry
