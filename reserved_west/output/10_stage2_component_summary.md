# Stage 2 Component-Level Variance Summary
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.0
**Date:** 2026-08-06

## Summary by component

| Component | Scenarios | Passing | Failing | Pass rate |
|---|---|---|---|---|
| Income Tax (non-taper) | 40 | 39 | 0 | 97% |
| Income Tax (EL-001 zone) | 20 | 20 | 0 | 100% |
| NI (Class 4) | 125 | 124 | 0 | 99% |
| Student Loan | 43 | 43 | 0 | 100% |
| Pension RaS | 22 | 22 | 0 | 100% |
| CGT | 25 | 25 | 0 | 100% |

## EL-001 zone detail

All scenarios in the EL-001 regression family (PA taper zone) must return PASS.
Any failure in this group is classified REGRESSION_EL001 — a gate-blocking defect.

EL-001 zone scenarios in Stage 2: 20

| ID | Title | Outcome |
|---|---|---|
| RW-S2-006 | PA taper zone — invoice enters taper (EL-001 family) | PASS |
| RW-S2-007 | PA taper zone — invoice fully within taper (EL-001 fami | PASS |
| RW-S2-008 | Six-figure earner — invoice crosses PA elimination (EL- | PASS |
| RW-S2-015 | Sole trader — all four bands in one year (large invoice | PASS |
| RW-S2-022 | ART boundary — invoice ends just below ART | PASS |
| RW-S2-023 | ART boundary — invoice ends exactly at ART | PASS |
| RW-S2-024 | ART boundary — invoice crosses ART | PASS |
| RW-S2-027 | Taper start — invoice enters taper zone (EL-001 family) | PASS |
| RW-S2-028 | Taper midpoint — invoice ends below midpoint | PASS |
| RW-S2-029 | Taper midpoint — invoice ends at midpoint (PA = £6,285) | PASS |
| RW-S2-030 | Taper midpoint — invoice crosses midpoint | PASS |
| RW-S2-031 | PA zero boundary — invoice ends just below PA eliminati | PASS |
| RW-S2-032 | PA zero boundary — invoice ends exactly at PA eliminati | PASS |
| RW-S2-033 | PA zero boundary — invoice crosses PA elimination into  | PASS |
| RW-S2-042 | Combined — salary in PA taper zone, freelance extends ( | PASS |
| RW-S2-044 | Combined — invoice at ART, pension extends eBRL past AR | PASS |
| RW-S2-122 | SEQ Journey B — Invoice 3 of 4 (YTD=60k, near taper, EL | PASS |
| RW-S2-123 | SEQ Journey B — Invoice 4 of 4 (YTD=110k, crosses PA el | PASS |
| RW-S2-139 | EDG — very large invoice (£500,000) from zero | PASS |
| RW-S2-145 | EDG — very small invoice in higher rate band (£0.50) | PASS |

## Variance distribution

| Outcome | Count | Percentage |
|---|---|---|
| PASS | 149 | 99% |
| UNSUPPORTED_EXPECTED | 1 | 0% |