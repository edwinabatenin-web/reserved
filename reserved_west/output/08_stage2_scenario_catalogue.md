# Stage 2 Scenario Catalogue
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06
**Total scenarios:** 150

## Group overview

| Group | Description | Scenario range | Count |
|---|---|---|---|
| REP | Representative user profiles | RW-S2-001–RW-S2-015 | 15 |
| THR | Material threshold boundaries | RW-S2-016–RW-S2-045 | 30 |
| SL | Student loan 2025/26 | RW-S2-046–RW-S2-060 | 15 |
| SL2 | Student loan 2026/27 | RW-S2-061–RW-S2-075 | 15 |
| PEN | Pension Relief at Source | RW-S2-076–RW-S2-090 | 15 |
| CGT | Capital Gains Tax | RW-S2-091–RW-S2-115 | 25 |
| SEQ | Sequential journeys | RW-S2-116–RW-S2-135 | 20 |
| EDG | Edge cases | RW-S2-136–RW-S2-150 | 15 |

## Threshold matrix

Each material threshold is exercised at 3 boundary points:

| Threshold | Value | Boundary points |
|---|---|---|
| Personal Allowance (PA) | £12,570 | below, at, crosses (RW-S2-016–018) |
| Basic Rate Limit (BRL) | £50,270 | below, at, crosses (RW-S2-019–021) |
| Additional Rate Threshold (ART) | £125,140 | below, at, crosses (RW-S2-022–024) |
| PA Taper Start (ANI £100k) | £100,000 | below, at, enters (RW-S2-025–027) |
| PA Taper Midpoint (ANI £112,570) | £112,570 | below, at, crosses (RW-S2-028–030) |
| PA Elimination (ANI £125,140) | £125,140 | below, at, crosses (RW-S2-031–033) |
| NI Lower Profits Limit | £12,570 | below, at, crosses (RW-S2-034–036) |
| NI Upper Profits Limit | £50,270 | below, at, crosses (RW-S2-037–039) |
| Combined salary+freelance BRL | £50,270 | below, at, crosses (RW-S2-040–042) |
| Pension eBRL cap at ART | £125,140 | within, at, exceeds cap (RW-S2-043–045) |

## Student loan threshold matrix

| Plan | 2025/26 threshold | 2026/27 threshold | Scenarios |
|---|---|---|---|
| Plan 1 | £24,990 | £26,900 | RW-S2-046–048, RW-S2-061–063 |
| Plan 2 | £28,470 | £29,385 | RW-S2-049–051, RW-S2-064–066 |
| Plan 4 | £32,745 | £33,795 | RW-S2-052–054, RW-S2-067–069 |
| Plan 5 | £25,000 | £25,000 | RW-S2-055–057, RW-S2-070–072 |
| Postgraduate | £21,000 | £21,000 | RW-S2-058–060, RW-S2-073–075 |

## ID assignment

Scenario IDs are permanent.  Do not re-use or renumber.
Stage 1 IDs: RW-S1-001 through RW-S1-030.
Stage 2 IDs: RW-S2-001 through RW-S2-150.
Stage 3 IDs will begin at RW-S3-001.

## Full scenario list

| ID | Group | Title | Tax Year | Type |
|---|---|---|---|---|
| RW-S2-001 | REP | Junior sole trader — first invoice year | 2026/27 | income_tax |
| RW-S2-002 | REP | Junior sole trader — invoice crosses PA and NI LPL | 2026/27 | income_tax |
| RW-S2-003 | REP | Mid-career freelancer — basic rate, Plan 2 | 2026/27 | income_tax |
| RW-S2-004 | REP | Senior freelancer — higher rate band, no loans | 2026/27 | income_tax |
| RW-S2-005 | REP | High earner below PA taper — £95k YTD total | 2026/27 | income_tax |
| RW-S2-006 | REP | PA taper zone — invoice enters taper (EL-001 family) | 2026/27 | income_tax |
| RW-S2-007 | REP | PA taper zone — invoice fully within taper (EL-001 family) | 2026/27 | income_tax |
| RW-S2-008 | REP | Six-figure earner — invoice crosses PA elimination (EL-001 fam | 2026/27 | income_tax |
| RW-S2-009 | REP | Additional rate payer — invoice fully at 45% | 2026/27 | income_tax |
| RW-S2-010 | REP | Pension saver — RaS extends BRL, saves higher-rate IT | 2026/27 | income_tax |
| RW-S2-011 | REP | Graduate — Plan 2 + Postgraduate, dual repayment | 2026/27 | income_tax |
| RW-S2-012 | REP | Very high earner — invoice at top marginal rate | 2026/27 | income_tax |
| RW-S2-013 | REP | Gabriel canonical 2026/27 | 2026/27 | income_tax |
| RW-S2-014 | REP | Gabriel canonical 2025/26 | 2025/26 | income_tax |
| RW-S2-015 | REP | Sole trader — all four bands in one year (large invoice) | 2026/27 | income_tax |
| RW-S2-016 | THR | PA boundary — invoice ends below PA | 2026/27 | income_tax |
| RW-S2-017 | THR | PA boundary — invoice ends exactly at PA | 2026/27 | income_tax |
| RW-S2-018 | THR | PA boundary — invoice crosses PA | 2026/27 | income_tax |
| RW-S2-019 | THR | BRL boundary — invoice ends below BRL | 2026/27 | income_tax |
| RW-S2-020 | THR | BRL boundary — invoice ends exactly at BRL | 2026/27 | income_tax |
| RW-S2-021 | THR | BRL boundary — invoice crosses BRL | 2026/27 | income_tax |
| RW-S2-022 | THR | ART boundary — invoice ends just below ART | 2026/27 | income_tax |
| RW-S2-023 | THR | ART boundary — invoice ends exactly at ART | 2026/27 | income_tax |
| RW-S2-024 | THR | ART boundary — invoice crosses ART | 2026/27 | income_tax |
| RW-S2-025 | THR | Taper start — invoice ends below taper (ANI < £100k) | 2026/27 | income_tax |
| RW-S2-026 | THR | Taper start — invoice ends exactly at taper start (ANI = £100k | 2026/27 | income_tax |
| RW-S2-027 | THR | Taper start — invoice enters taper zone (EL-001 family) | 2026/27 | income_tax |
| RW-S2-028 | THR | Taper midpoint — invoice ends below midpoint | 2026/27 | income_tax |
| RW-S2-029 | THR | Taper midpoint — invoice ends at midpoint (PA = £6,285) | 2026/27 | income_tax |
| RW-S2-030 | THR | Taper midpoint — invoice crosses midpoint | 2026/27 | income_tax |
| RW-S2-031 | THR | PA zero boundary — invoice ends just below PA elimination | 2026/27 | income_tax |
| RW-S2-032 | THR | PA zero boundary — invoice ends exactly at PA elimination | 2026/27 | income_tax |
| RW-S2-033 | THR | PA zero boundary — invoice crosses PA elimination into 45% | 2026/27 | income_tax |
| RW-S2-034 | THR | NI LPL — freelance profit ends below LPL | 2026/27 | income_tax |
| RW-S2-035 | THR | NI LPL — freelance profit ends exactly at LPL | 2026/27 | income_tax |
| RW-S2-036 | THR | NI LPL — freelance profit crosses LPL | 2026/27 | income_tax |
| RW-S2-037 | THR | NI UPL — freelance profit ends below UPL | 2026/27 | income_tax |
| RW-S2-038 | THR | NI UPL — freelance profit ends exactly at UPL | 2026/27 | income_tax |
| RW-S2-039 | THR | NI UPL — freelance profit crosses UPL | 2026/27 | income_tax |
| RW-S2-040 | THR | Combined — salary near BRL, freelance crosses to higher rate | 2026/27 | income_tax |
| RW-S2-041 | THR | Combined — salary at BRL, entire invoice at higher rate | 2026/27 | income_tax |
| RW-S2-042 | THR | Combined — salary in PA taper zone, freelance extends (EL-001  | 2026/27 | income_tax |
| RW-S2-043 | THR | Combined — salary + pension keeps ANI below taper | 2026/27 | income_tax |
| RW-S2-044 | THR | Combined — invoice at ART, pension extends eBRL past ART (cap  | 2026/27 | income_tax |
| RW-S2-045 | THR | Combined — very large pension caps eBRL at ART | 2026/27 | income_tax |
| RW-S2-046 | SL | SL Plan 1 2025/26 — income ends below threshold | 2025/26 | income_tax |
| RW-S2-047 | SL | SL Plan 1 2025/26 — income crosses threshold | 2025/26 | income_tax |
| RW-S2-048 | SL | SL Plan 1 2025/26 — income starts above threshold | 2025/26 | income_tax |
| RW-S2-049 | SL | SL Plan 2 2025/26 — income ends below threshold | 2025/26 | income_tax |
| RW-S2-050 | SL | SL Plan 2 2025/26 — income crosses threshold | 2025/26 | income_tax |
| RW-S2-051 | SL | SL Plan 2 2025/26 — income starts above threshold | 2025/26 | income_tax |
| RW-S2-052 | SL | SL Plan 4 2025/26 — income ends below threshold | 2025/26 | income_tax |
| RW-S2-053 | SL | SL Plan 4 2025/26 — income crosses threshold | 2025/26 | income_tax |
| RW-S2-054 | SL | SL Plan 4 2025/26 — income starts above threshold | 2025/26 | income_tax |
| RW-S2-055 | SL | SL Plan 5 2025/26 — income ends below threshold | 2025/26 | income_tax |
| RW-S2-056 | SL | SL Plan 5 2025/26 — income crosses threshold | 2025/26 | income_tax |
| RW-S2-057 | SL | SL Plan 5 2025/26 — income starts above threshold | 2025/26 | income_tax |
| RW-S2-058 | SL | SL Postgraduate 2025/26 — income ends below threshold | 2025/26 | income_tax |
| RW-S2-059 | SL | SL Postgraduate 2025/26 — income crosses threshold | 2025/26 | income_tax |
| RW-S2-060 | SL | SL Postgraduate 2025/26 — income starts above threshold | 2025/26 | income_tax |
| RW-S2-061 | SL | SL Plan 1 2026/27 — income ends below threshold | 2026/27 | income_tax |
| RW-S2-062 | SL | SL Plan 1 2026/27 — income crosses threshold | 2026/27 | income_tax |
| RW-S2-063 | SL | SL Plan 1 2026/27 — income starts above threshold | 2026/27 | income_tax |
| RW-S2-064 | SL | SL Plan 2 2026/27 — income ends below threshold | 2026/27 | income_tax |
| RW-S2-065 | SL | SL Plan 2 2026/27 — income crosses threshold | 2026/27 | income_tax |
| RW-S2-066 | SL | SL Plan 2 2026/27 — income starts above threshold | 2026/27 | income_tax |
| RW-S2-067 | SL | SL Plan 4 2026/27 — income ends below threshold | 2026/27 | income_tax |
| RW-S2-068 | SL | SL Plan 4 2026/27 — income crosses threshold | 2026/27 | income_tax |
| RW-S2-069 | SL | SL Plan 4 2026/27 — income starts above threshold | 2026/27 | income_tax |
| RW-S2-070 | SL | SL Plan 5 2026/27 — income ends below threshold | 2026/27 | income_tax |
| RW-S2-071 | SL | SL Plan 5 2026/27 — income crosses threshold | 2026/27 | income_tax |
| RW-S2-072 | SL | SL Plan 5 2026/27 — income starts above threshold | 2026/27 | income_tax |
| RW-S2-073 | SL | SL Postgraduate 2026/27 — income ends below threshold | 2026/27 | income_tax |
| RW-S2-074 | SL | SL Postgraduate 2026/27 — income crosses threshold | 2026/27 | income_tax |
| RW-S2-075 | SL | SL Postgraduate 2026/27 — income starts above threshold | 2026/27 | income_tax |
| RW-S2-076 | PENSION | Pension — basic rate payer, RaS raises refund (no band extensi | 2026/27 | income_tax |
| RW-S2-077 | PENSION | Pension — extends BRL, saving 20% on part of invoice | 2026/27 | income_tax |
| RW-S2-078 | PENSION | Pension — large enough to keep entire invoice at 20% | 2026/27 | income_tax |
| RW-S2-079 | PENSION | Pension — reduces ANI to just below taper start (PA preserved) | 2026/27 | income_tax |
| RW-S2-080 | PENSION | Pension — prevents PA taper at start but invoice crosses into  | 2026/27 | income_tax |
| RW-S2-081 | PENSION | Pension — eliminates PA taper effect entirely | 2026/27 | income_tax |
| RW-S2-082 | PENSION | Pension — large contribution with Plan 2 loan | 2026/27 | income_tax |
| RW-S2-083 | PENSION | Pension — contribution exactly extends eBRL to BRL | 2026/27 | income_tax |
| RW-S2-084 | PENSION | Pension — contribution that nearly reaches ART eBRL cap | 2026/27 | income_tax |
| RW-S2-085 | PENSION | Pension — exactly caps eBRL at ART | 2026/27 | income_tax |
| RW-S2-086 | PENSION | Pension — zero contribution, baseline for pension comparison | 2026/27 | income_tax |
| RW-S2-087 | PENSION | Pension — small contribution (£1,000) basic rate saver | 2026/27 | income_tax |
| RW-S2-088 | PENSION | Pension — higher rate saver, large contribution | 2026/27 | income_tax |
| RW-S2-089 | PENSION | Pension — PGL holder with large pension | 2026/27 | income_tax |
| RW-S2-090 | PENSION | Pension — all plans + pension combined | 2026/27 | income_tax |
| RW-S2-091 | CGT | CGT — gain exactly equals AEA (£3,000) | 2026/27 | cgt |
| RW-S2-092 | CGT | CGT — gain just above AEA | 2026/27 | cgt |
| RW-S2-093 | CGT | CGT — gain just below AEA | 2026/27 | cgt |
| RW-S2-094 | CGT | CGT — entire gain at basic rate (18%) | 2026/27 | cgt |
| RW-S2-095 | CGT | CGT — entire gain at higher rate (24%) | 2026/27 | cgt |
| RW-S2-096 | CGT | CGT — split basic/higher rate | 2026/27 | cgt |
| RW-S2-097 | CGT | CGT — gain exactly fills remaining BRL | 2026/27 | cgt |
| RW-S2-098 | CGT | CGT — brought-forward losses reduce taxable gains | 2026/27 | cgt |
| RW-S2-099 | CGT | CGT — brought-forward losses eliminate taxable gain | 2026/27 | cgt |
| RW-S2-100 | CGT | CGT — two disposals, combined gain | 2026/27 | cgt |
| RW-S2-101 | CGT | CGT — three disposals, one at a loss (offsets gains) | 2026/27 | cgt |
| RW-S2-102 | CGT | CGT — all disposals result in a loss (no CGT) | 2026/27 | cgt |
| RW-S2-103 | CGT | CGT — crypto disposal, gain within basic rate | 2026/27 | cgt |
| RW-S2-104 | CGT | CGT — 2025/26 tax year (rates same; AEA same) | 2025/26 | cgt |
| RW-S2-105 | CGT | CGT — high income, entire gain at higher rate, 2025/26 | 2025/26 | cgt |
| RW-S2-106 | CGT | CGT — income below PA; basic rate applied from £0 | 2026/27 | cgt |
| RW-S2-107 | CGT | CGT — large gain spanning basic and higher entirely | 2026/27 | cgt |
| RW-S2-108 | CGT | CGT — income exactly at BRL; entire gain at higher rate | 2026/27 | cgt |
| RW-S2-109 | CGT | CGT — partial tax already paid reduces outstanding | 2026/27 | cgt |
| RW-S2-110 | CGT | CGT — gain exactly equals AEA in 2025/26 (AEA same) | 2025/26 | cgt |
| RW-S2-111 | CGT | CGT — four disposals, mixed gains and losses | 2026/27 | cgt |
| RW-S2-112 | CGT | CGT — gain split by tax year boundary effect on BRL | 2026/27 | cgt |
| RW-S2-113 | CGT | CGT — other asset type | 2026/27 | cgt |
| RW-S2-114 | CGT | CGT — BF losses + current losses combined | 2026/27 | cgt |
| RW-S2-115 | CGT | CGT — very large gain (£100,000), all at higher rate | 2026/27 | cgt |
| RW-S2-116 | SEQ | SEQ Journey A — Invoice 1 of 4 (YTD=0, below PA) | 2026/27 | income_tax |
| RW-S2-117 | SEQ | SEQ Journey A — Invoice 2 of 4 (YTD=5k, crosses PA) | 2026/27 | income_tax |
| RW-S2-118 | SEQ | SEQ Journey A — Invoice 3 of 4 (YTD=15k, basic rate) | 2026/27 | income_tax |
| RW-S2-119 | SEQ | SEQ Journey A — Invoice 4 of 4 (YTD=25k, basic rate) | 2026/27 | income_tax |
| RW-S2-120 | SEQ | SEQ Journey B — Invoice 1 of 4 (YTD=0, £40k invoice, crosses B | 2026/27 | income_tax |
| RW-S2-121 | SEQ | SEQ Journey B — Invoice 2 of 4 (YTD=40k, higher rate) | 2026/27 | income_tax |
| RW-S2-122 | SEQ | SEQ Journey B — Invoice 3 of 4 (YTD=60k, near taper, EL-001 fa | 2026/27 | income_tax |
| RW-S2-123 | SEQ | SEQ Journey B — Invoice 4 of 4 (YTD=110k, crosses PA eliminati | 2026/27 | income_tax |
| RW-S2-124 | SEQ | SEQ Journey C — Invoice 1 of 4 (employed £40k, first freelance | 2026/27 | income_tax |
| RW-S2-125 | SEQ | SEQ Journey C — Invoice 2 of 4 (YTD=5k) | 2026/27 | income_tax |
| RW-S2-126 | SEQ | SEQ Journey C — Invoice 3 of 4 (YTD=15k) | 2026/27 | income_tax |
| RW-S2-127 | SEQ | SEQ Journey C — Invoice 4 of 4 (YTD=25k) | 2026/27 | income_tax |
| RW-S2-128 | SEQ | SEQ Journey D — Invoice 1 of 4 (pension saver, £50k salary) | 2026/27 | income_tax |
| RW-S2-129 | SEQ | SEQ Journey D — Invoice 2 of 4 (YTD=5k) | 2026/27 | income_tax |
| RW-S2-130 | SEQ | SEQ Journey D — Invoice 3 of 4 (YTD=10k, EL-001 watch zone) | 2026/27 | income_tax |
| RW-S2-131 | SEQ | SEQ Journey D — Invoice 4 of 4 (YTD=15k) | 2026/27 | income_tax |
| RW-S2-132 | SEQ | SEQ Journey E — 2025/26 early invoice | 2025/26 | income_tax |
| RW-S2-133 | SEQ | SEQ Journey E — 2026/27 same invoice (higher threshold) | 2026/27 | income_tax |
| RW-S2-134 | SEQ | SEQ Journey E — 2025/26 later invoice (well above threshold) | 2025/26 | income_tax |
| RW-S2-135 | SEQ | SEQ Journey E — 2026/27 same later invoice | 2026/27 | income_tax |
| RW-S2-136 | EDG | EDG — zero invoice (validation boundary) | 2026/27 | income_tax |
| RW-S2-137 | EDG | EDG — £1 invoice below PA (no tax) | 2026/27 | income_tax |
| RW-S2-138 | EDG | EDG — £0.01 invoice (penny, no tax) | 2026/27 | income_tax |
| RW-S2-139 | EDG | EDG — very large invoice (£500,000) from zero | 2026/27 | income_tax |
| RW-S2-140 | EDG | EDG — invoice amount with pence (£1,000.50) | 2026/27 | income_tax |
| RW-S2-141 | EDG | EDG — all components at once: IT + NI + SL + pension | 2026/27 | income_tax |
| RW-S2-142 | EDG | EDG — salary exactly at PA (no IT on salary) | 2026/27 | income_tax |
| RW-S2-143 | EDG | EDG — salary exactly at BRL | 2026/27 | income_tax |
| RW-S2-144 | EDG | EDG — salary exactly at ART | 2026/27 | income_tax |
| RW-S2-145 | EDG | EDG — very small invoice in higher rate band (£0.50) | 2026/27 | income_tax |
| RW-S2-146 | EDG | EDG — invoice at exact ART boundary (£0.50 at 45%) | 2026/27 | income_tax |
| RW-S2-147 | EDG | EDG — multiple SL plans, one irrelevant (income below threshol | 2026/27 | income_tax |
| RW-S2-148 | EDG | EDG — all five SL plans simultaneously | 2026/27 | income_tax |
| RW-S2-149 | EDG | EDG — 2025/26 and 2026/27 comparison (same scenario) | 2026/27 | income_tax |
| RW-S2-150 | EDG | EDG — same scenario in 2025/26 (lower Plan 2 threshold) | 2025/26 | income_tax |