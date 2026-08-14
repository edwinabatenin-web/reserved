"""
Reserved West — Stage 3 Scenario Catalogue

Interaction Assurance (60 scenarios)

Stage 3 tests complex combinations where multiple engine components interact
simultaneously.  Stage 1 verified components in isolation; Stage 2 confirmed
they are correct at all material boundaries.  Stage 3 asks: do components
produce correct results when they interact?

Groups
------
INT  All-component interaction (all IT + NI + SL + pension firing together)
     RW-S3-001 – RW-S3-020
PIG  Pension deep interaction (pension × PA taper × eBRL cap × SL)
     RW-S3-021 – RW-S3-035
SLX  Student-loan cross-plan and cross-year effects
     RW-S3-036 – RW-S3-045
CGX  CGT + income-tax interaction (basic-rate band split, pension, taper)
     RW-S3-046 – RW-S3-055
YTC  Year-to-year comparison (same income pattern, 2025/26 vs 2026/27)
     RW-S3-056 – RW-S3-060

ID assignment is permanent.  Do not re-use or renumber IDs.
"""

# ── Helpers (same conventions as Stage 2) ─────────────────────────────────────

def _it(sid, title, desc, groups, salary, ytd, pension, plans, invoice,
        year="2026/27", **kw):
    return {
        "scenario_id":   sid,
        "title":         title,
        "description":   desc,
        "groups":        ["stage3"] + groups,
        "envelope":      "income_tax",
        "scenario_type": "income_tax",
        "inputs": {
            "invoice_amount": invoice,
            "profile": {
                "day_job_salary":                salary,
                "ytd_freelance_profit":          ytd,
                "personal_pension_contributions": pension,
                "student_loan_plans":             plans,
            },
            "tax_year": year,
        },
        **kw,
    }


def _cgt(sid, title, desc, groups, disposals, tib, bf=0, paid=0,
         year="2026/27"):
    return {
        "scenario_id":   sid,
        "title":         title,
        "description":   desc,
        "groups":        ["stage3"] + groups,
        "envelope":      "cgt",
        "scenario_type": "cgt",
        "inputs": {
            "tax_year":                    year,
            "disposals":                   disposals,
            "taxable_income_before_gains": tib,
            "brought_forward_losses":      bf,
            "tax_already_paid":            paid,
        },
    }


def _d(asset_type, desc, proceeds, cost, date="2026-09-01"):
    return {
        "asset_type":     asset_type,
        "description":    desc,
        "disposal_date":  date,
        "proceeds":       proceeds,
        "allowable_cost": cost,
    }


# ── GROUP INT: All-component interaction ──────────────────────────────────────
# 20 scenarios — RW-S3-001 to RW-S3-020
#
# Every scenario fires at least three of: income tax, Class 4 NI, pension RaS,
# and one or more student-loan plans.  The point is not to test any single
# component — each one has been verified in Stage 2 — but to confirm that the
# interactions between them are handled correctly simultaneously.

INT = [

    _it("RW-S3-001",
        "All five SL plans + pension + salary + invoice crosses BRL and NI LPL",
        "£35k salary, £10k YTD, £3k pension RaS, all five SL plans, £10k invoice, 2026/27. "
        "Income: 35k+10k+10k=55k. eBRL=53,270. Invoice crosses BRL (50,270→53,270 at 20%, "
        "53,270→55k at 40%). NI: YTD profit 10k→20k, crosses LPL (£12,570). "
        "All five plans active at £55k: Plans 1/2/4/5/PGL all above their thresholds. "
        "Tests all components firing together in a realistic profile.",
        ["int", "all_components"],
        salary=35000, ytd=10000, pension=3000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=10000,
    ),

    _it("RW-S3-002",
        "All five SL plans + pension — same profile in 2025/26",
        "Identical inputs to RW-S3-001 but tax year 2025/26. "
        "Income (55k) exceeds all 2025/26 thresholds so marginal SL amounts identical. "
        "IT and NI unchanged (frozen thresholds). Tests year-invariance of components when "
        "all SL thresholds are already exceeded at start of invoice.",
        ["int", "all_components"],
        salary=35000, ytd=10000, pension=3000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=10000,
        year="2025/26",
    ),

    _it("RW-S3-003",
        "All five SL plans + large pension + NI crossing UPL",
        "£0 salary, £40k YTD profit, £10k pension RaS, all five SL plans, £15k invoice, 2026/27. "
        "Income: 40k→55k. eBRL=60,270 so entire invoice at 20%. "
        "NI: profit 40k→55k, crosses UPL (£50,270): main rate to UPL, upper rate above. "
        "ANI_start=30k, ANI_end=45k, both well below taper. "
        "All SL plans exceeded at start; marginal SL = rate × £15k for each plan. "
        "Tests pension eBRL extension shielding invoice from 40% while NI UPL crossing occurs.",
        ["int", "all_components", "ni_upl"],
        salary=0, ytd=40000, pension=10000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=15000,
    ),

    _it("RW-S3-004",
        "Salary + pension + SL Plan 2 — invoice crosses PA taper (EL-001 zone)",
        "£90k salary, £0 YTD, £15k pension RaS, Plan 2 only, £30k invoice, 2026/27. "
        "ANI_start = 90k − 15k = 75k (below taper). "
        "ANI_end = 120k − 15k = 105k (enters taper zone). "
        "Pension preserves PA at start but invoice pushes ANI into taper. EL-001 zone. "
        "SL Plan 2: start 90k > threshold (£29,385); marginal SL = 9% × 30k = £2,700. "
        "eBRL = 65,270 (well below start income). Invoice entirely at 40%.",
        ["int", "el001_family", "pension"],
        salary=90000, ytd=0, pension=15000, plans=[2], invoice=30000,
    ),

    _it("RW-S3-005",
        "Pension keeps ANI at taper start; invoice crosses deep into taper (EL-001)",
        "£115k salary, £0 YTD, £15k pension RaS, no SL, £15k invoice, 2026/27. "
        "ANI_start = 115k − 15k = 100k (exactly at taper start; PA = £12,570). "
        "ANI_end = 130k − 15k = 115k (PA = £12,570 − £7,500 = £5,070). EL-001 zone. "
        "eBRL = 65,270 (pension extension). Both start and end income above ART (£125,140) "
        "on gross income, but ANI is in taper. Tests pension-taper edge interaction.",
        ["int", "el001_family", "pension"],
        salary=115000, ytd=0, pension=15000, plans=[], invoice=15000,
    ),

    _it("RW-S3-006",
        "Salary + pension + SL Plan 1 — invoice enters PA taper from below (EL-001)",
        "£95k salary, £5k YTD, £5k pension RaS, Plan 1 only, £10k invoice, 2026/27. "
        "ANI_start = 100k − 5k = 95k (below taper). "
        "ANI_end = 110k − 5k = 105k (in taper). EL-001 zone. "
        "SL Plan 1 (£26,900): start income 100k > threshold; marginal = 9% × 10k = £900. "
        "Invoice starts at 40% rate (income above BRL) and enters taper zone.",
        ["int", "el001_family", "pension", "student_loan"],
        salary=95000, ytd=5000, pension=5000, plans=[1], invoice=10000,
    ),

    _it("RW-S3-007",
        "Sole trader — all NI bands + Plan 2 + PGL + pension; large invoice from low YTD",
        "£0 salary, £10k YTD, £5k pension RaS, Plan 2 + PGL, £45k invoice, 2026/27. "
        "start_profit=10k (below NI LPL=12,570). end_profit=55k (above NI UPL=50,270). "
        "All three NI bands crossed: below LPL, main (6%), upper (2%). "
        "ANI_start=5k, ANI_end=50k; eBRL=55,270. Invoice crosses PA, LPL, and BRL. "
        "Plan 2 (£29,385): start=10k < threshold; end=55k > threshold. "
        "PGL (£21,000): start=10k < threshold; end=55k > threshold. "
        "Tests NI three-band crossing simultaneously with two SL plan threshold crossings.",
        ["int", "ni_all_bands", "student_loan"],
        salary=0, ytd=10000, pension=5000, plans=[2, "postgraduate"], invoice=45000,
    ),

    _it("RW-S3-008",
        "Near-taper earnings + SL Plan 5 + pension — invoice crosses taper start (EL-001)",
        "£0 salary, £96k YTD, £10k pension RaS, Plan 5 only, £15k invoice, 2026/27. "
        "ANI_start = 86k (below taper). ANI_end = 101k (in taper). EL-001 zone. "
        "NI on freelance: YTD 96k > UPL; end 111k > UPL. NI = 2% × 15k = £300. "
        "Plan 5 (£25,000 fixed): start 96k > threshold; marginal = 9% × 15k = £1,350. "
        "Pension reduces ANI (and taper entry point) but SL is on gross income. "
        "Tests: does pension's ANI effect interact correctly with EL-001 zone detection?",
        ["int", "el001_family", "pension", "student_loan"],
        salary=0, ytd=96000, pension=10000, plans=[5], invoice=15000,
    ),

    _it("RW-S3-009",
        "Plan 2 + PGL + pension — invoice crosses eBRL into higher rate",
        "£40k salary, £7k YTD, £5k pension RaS, Plan 2 + PGL, £10k invoice, 2026/27. "
        "eBRL = 55,270. start_income=47k, end=57k. Crosses eBRL at 55,270. "
        "Below eBRL: at 20%. Above eBRL: at 40%. "
        "NI: YTD profit=7k < LPL. end_profit=17k > LPL. NI = 6% × (17k−12,570) = £265.80. "
        "Plan 2 (£29,385): start=47k > threshold; 9%×10k=£900. "
        "PGL (£21k): start=47k > threshold; 6%×10k=£600. "
        "Tests: pension extension of BRL interacts correctly with both SL plans and NI.",
        ["int", "pension", "student_loan"],
        salary=40000, ytd=7000, pension=5000, plans=[2, "postgraduate"], invoice=10000,
    ),

    _it("RW-S3-010",
        "All five SL plans + pension — sole trader invoice crosses all thresholds from zero",
        "£0 salary, £0 YTD, £8k pension RaS, all five SL plans, £80k invoice, 2026/27. "
        "Traverses: PA (£12,570), NI LPL (£12,570), PGL threshold (£21k), Plan 5 (£25k), "
        "Plan 1 (£26,900), Plan 2 (£29,385), Plan 4 (£33,795), NI UPL (£50,270), "
        "eBRL (£58,270), BRL area (basic→higher transition). "
        "ANI_start=0, ANI_end=72k. No taper. Full multi-threshold traversal. "
        "Tests that all components activate at the correct income points in sequence.",
        ["int", "all_components", "multi_threshold"],
        salary=0, ytd=0, pension=8000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=80000,
    ),

    _it("RW-S3-011",
        "Very large pension caps eBRL at ART; invoice partly at 45%",
        "£120k salary, £5k YTD, £80k pension RaS, no SL, £5k invoice, 2026/27. "
        "eBRL = min(50,270+80,000, 125,140) = 125,140 (capped at ART). "
        "ANI_start = 125k − 80k = 45k (well below taper). "
        "ANI_end = 130k − 80k = 50k (still well below taper). "
        "start_income=125k, end=130k. With eBRL=ART=125,140: some invoice above ART at 45%. "
        "NI on freelance: YTD profit 5k→10k, both below LPL. NI=0. "
        "Tests: when eBRL is capped at ART, the ART band still switches to 45% correctly.",
        ["int", "pension", "ebrl_cap"],
        salary=120000, ytd=5000, pension=80000, plans=[], invoice=5000,
    ),

    _it("RW-S3-012",
        "Salary at BRL + pension extends eBRL + SL Plan 4 + NI crosses LPL",
        "£50,270 salary, £0 YTD, £5k pension RaS, Plan 4 only, £10k invoice, 2026/27. "
        "eBRL = 55,270. Invoice: start=50,270 → end=60,270. Crosses eBRL at 55,270. "
        "SL Plan 4 (£33,795): start=50,270 > threshold; marginal = 9% × 10k = £900. "
        "NI on freelance: YTD=0 < LPL; end_profit=10k < LPL. NI=0. "
        "Tests salary exactly at BRL with pension extension: pension correctly widens "
        "basic-rate band beyond salary level.",
        ["int", "pension", "student_loan"],
        salary=50270, ytd=0, pension=5000, plans=[4], invoice=10000,
    ),

    _it("RW-S3-013",
        "High earner + SL Plan 2 + pension — invoice spans taper into PA elimination (EL-001)",
        "£0 salary, £115k YTD, £5k pension RaS, Plan 2 only, £15k invoice, 2026/27. "
        "ANI_start = 110k (in taper; PA = £2,570). "
        "ANI_end = 125k (approaching PA elimination at £125,140). EL-001 zone. "
        "NI: YTD=115k > UPL; end=130k > UPL. NI = 2% × 15k = £300. "
        "Plan 2: start 115k >> threshold; 9% × 15k = £1,350. "
        "Taper interaction: PA shrinks from £2,570 toward zero during invoice. "
        "Tests: three-way taper + NI upper rate + SL combination.",
        ["int", "el001_family", "pension", "student_loan"],
        salary=0, ytd=115000, pension=5000, plans=[2], invoice=15000,
    ),

    _it("RW-S3-014",
        "Plan 1 crosses threshold + pension + NI crossing LPL + IT at basic rate",
        "£0 salary, £20k YTD, £3k pension RaS, Plan 1 only, £10k invoice, 2026/27. "
        "start_income=20k, end=30k. ANI: 17k→27k. No taper. eBRL=53,270. "
        "IT: basic rate throughout. "
        "NI: YTD=20k > LPL; end_profit=30k. NI = 6% × 10k = £600. "
        "Plan 1 (£26,900): start=20k < threshold; end=30k > threshold. "
        "Marginal SL Plan 1 = 9% × (30k − 26,900) = 9% × 3,100 = £279. "
        "Tests: SL threshold crossing mid-invoice while NI and pension also active.",
        ["int", "student_loan", "ni_main"],
        salary=0, ytd=20000, pension=3000, plans=[1], invoice=10000,
    ),

    _it("RW-S3-015",
        "All five SL plans + no pension — sole trader traverses all bands and thresholds",
        "£0 salary, £0 YTD, no pension, all five SL plans, £150k invoice, 2026/27. "
        "Traverses all IT bands (0%, 20%, 40%, 45%), NI bands (0%, 6%, 2%), "
        "and all five SL thresholds. ANI_end = 150k > ART (£125,140). EL-001 zone. "
        "Tests that all components correctly calculate their marginal contributions "
        "when the full income range is traversed in a single invoice.",
        ["int", "all_components", "el001_family", "multi_threshold"],
        salary=0, ytd=0, pension=0,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=150000,
    ),

    _it("RW-S3-016",
        "Plan 2 + Plan 4 simultaneously + pension — invoice crosses eBRL",
        "£42k salary, £5k YTD, £4k pension RaS, Plan 2 + Plan 4, £8k invoice, 2026/27. "
        "eBRL = 54,270. start_income=47k, end=55k. Crosses eBRL. "
        "NI: YTD=5k < LPL; end_profit=13k > LPL. NI = 6% × (13k − 12,570) = £25.80. "
        "Plan 2 (£29,385): start=47k > threshold; 9% × 8k = £720. "
        "Plan 4 (£33,795): start=47k > threshold; 9% × 8k = £720. Total SL = £1,440. "
        "Tests two simultaneous SL plans while pension extends BRL and NI LPL is crossed.",
        ["int", "student_loan", "pension", "ni_lpl"],
        salary=42000, ytd=5000, pension=4000, plans=[2, 4], invoice=8000,
    ),

    _it("RW-S3-017",
        "All five SL plans + no pension — salary in higher rate + invoice at 40% + NI",
        "£60k salary, £10k YTD, no pension, all five SL plans, £10k invoice, 2026/27. "
        "start_income=70k, end=80k. Entirely above BRL; invoice at 40%. "
        "NI: YTD=10k < LPL; end_profit=20k > LPL. NI = 6% × (20k − 12,570) = £445.80. "
        "All five plans: start=70k > all thresholds; each plan marginal = rate × 10k. "
        "Plans 1/2/4/5 at 9%: 4 × £900 = £3,600. PGL at 6%: £600. Total SL = £4,200. "
        "Tests: all SL plans firing at higher-rate income level with NI LPL crossed.",
        ["int", "all_components"],
        salary=60000, ytd=10000, pension=0,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=10000,
    ),

    _it("RW-S3-018",
        "Plan 1 + Plan 2 cross different thresholds in 2025/26 — two SL crossings in one invoice",
        "£0 salary, £23k YTD, no pension, Plan 1 + Plan 2, £10k invoice, 2025/26. "
        "start_income=23k, end=33k. "
        "Plan 1 (2025/26 threshold £24,990): start=23k < threshold; end=33k > threshold. "
        "Marginal SL Plan 1 = 9% × (33k − 24,990) = 9% × 8,010 = £720.90. "
        "Plan 2 (2025/26 threshold £28,470): start=23k < threshold; end=33k > threshold. "
        "Marginal SL Plan 2 = 9% × (33k − 28,470) = 9% × 4,530 = £407.70. "
        "NI: YTD=23k > LPL; end=33k. NI = 6% × 10k = £600. "
        "Tests two different SL plans each crossing their own threshold mid-invoice (2025/26).",
        ["int", "student_loan", "multi_sl_crossing"],
        salary=0, ytd=23000, pension=0, plans=[1, 2], invoice=10000,
        year="2025/26",
    ),

    _it("RW-S3-019",
        "Plan 1 + Plan 2 — same income pattern in 2026/27 (higher thresholds)",
        "Identical to RW-S3-018 but 2026/27. "
        "Plan 1 (2026/27 threshold £26,900): 9% × (33k − 26,900) = 9% × 6,100 = £549. "
        "Plan 2 (2026/27 threshold £29,385): 9% × (33k − 29,385) = 9% × 3,615 = £325.35. "
        "Total SL £874.35 vs £1,128.60 in 2025/26 — higher thresholds reduce repayments. "
        "IT and NI identical (frozen thresholds). "
        "Tests year-over-year SL threshold effect when both plans cross their thresholds.",
        ["int", "student_loan", "multi_sl_crossing", "year_comparison"],
        salary=0, ytd=23000, pension=0, plans=[1, 2], invoice=10000,
    ),

    _it("RW-S3-020",
        "Extended Gabriel — all five SL plans added to canonical pension profile",
        "Gabriel canonical (RW-S2-013) extended with all five SL plans. "
        "£40k salary, £15k YTD, £5k pension RaS, all five SL plans, £10k invoice, 2026/27. "
        "Income: 55k→65k. eBRL=55,270. Entire invoice above eBRL at 40%. "
        "NI: YTD=15k > LPL; end_profit=25k. NI = 6% × 10k = £600. "
        "All plans: start=55k > all thresholds. "
        "Plans 1/2/4/5: 9%×10k=£900 each = £3,600. PGL: 6%×10k=£600. Total SL=£4,200. "
        "Tests canonical persona with maximum SL complexity.",
        ["int", "all_components", "canonical"],
        salary=40000, ytd=15000, pension=5000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=10000,
    ),

]


# ── GROUP PIG: Pension deep interaction ───────────────────────────────────────
# 15 scenarios — RW-S3-021 to RW-S3-035

PIG = [

    _it("RW-S3-021",
        "Pension keeps ANI just below taper; invoice pushes ANI exactly to taper start",
        "£100k salary, £0 YTD, £5k pension RaS, no SL, £5k invoice, 2026/27. "
        "ANI_start = 100k − 5k = 95k (below taper). "
        "ANI_end = 105k − 5k = 100k (exactly at taper start; PA unchanged at £12,570). "
        "End ANI = £100,000 — not yet in EL-001 zone (PA does not change). "
        "eBRL = 55,270. Invoice entirely at 40% (income well above BRL). "
        "Tests: pension's ANI-reduction effect precisely at the taper boundary.",
        ["pig", "pension", "taper_boundary"],
        salary=100000, ytd=0, pension=5000, plans=[], invoice=5000,
    ),

    _it("RW-S3-022",
        "Pension keeps ANI below taper at start; invoice crosses taper (EL-001)",
        "£100k salary, £0 YTD, £4k pension RaS, no SL, £10k invoice, 2026/27. "
        "ANI_start = 96k (below taper). ANI_end = 106k (in taper). EL-001 zone. "
        "eBRL = 54,270. Income well above BRL; invoice at 40%. "
        "PA at start: £12,570. PA at end: £12,570 − (106k−100k)/2 = £9,570. "
        "Engine v2.0.0 computes IT(end)−IT(start) to handle the PA change correctly.",
        ["pig", "el001_family", "pension"],
        salary=100000, ytd=0, pension=4000, plans=[], invoice=10000,
    ),

    _it("RW-S3-023",
        "Pension reduces ANI through taper midpoint — PA halved (EL-001)",
        "£0 salary, £120k YTD, £10k pension RaS, no SL, £10k invoice, 2026/27. "
        "ANI_start = 110k (PA = £2,570). ANI_end = 120k (PA = £0). EL-001 zone. "
        "Invoice traverses the lower half of the taper where PA shrinks from £2,570 to £0. "
        "NI: YTD=120k > UPL; end=130k. NI = 2% × 10k = £200. "
        "Tests the most sensitive part of the EL-001 zone: near-elimination of PA.",
        ["pig", "el001_family", "pension"],
        salary=0, ytd=120000, pension=10000, plans=[], invoice=10000,
    ),

    _it("RW-S3-024",
        "Very large pension: eBRL capped exactly at ART; all invoice above ART at 45%",
        "£130k salary, £0 YTD, £75k pension RaS, no SL, £10k invoice, 2026/27. "
        "eBRL = min(50,270 + 75,000, 125,140) = 125,140 (cap). "
        "ANI_start = 130k − 75k = 55k (below taper; PA=£12,570). "
        "ANI_end = 140k − 75k = 65k (still below taper). "
        "start_income=130k > ART. Invoice entirely at 45%. "
        "Tests: eBRL capped at ART; invoice still correctly taxed at 45% above ART.",
        ["pig", "pension", "ebrl_cap"],
        salary=130000, ytd=0, pension=75000, plans=[], invoice=10000,
    ),

    _it("RW-S3-025",
        "Large pension + salary in higher rate — pension pulls entire invoice to 20%",
        "£55k salary, £0 YTD, £10k pension RaS, no SL, £10k invoice, 2026/27. "
        "eBRL = 60,270. start_income=55k, end=65k. "
        "Without pension: start above BRL; invoice entirely at 40%. "
        "With pension: eBRL=60,270 > end_income=65k. Invoice stays at 20%. "
        "Tests: pension correctly moves invoice from 40% to 20% via BRL extension.",
        ["pig", "pension", "band_shift"],
        salary=55000, ytd=0, pension=10000, plans=[], invoice=10000,
    ),

    _it("RW-S3-026",
        "Pension extends BRL; invoice straddles eBRL — split between 20% and 40%",
        "£48k salary, £0 YTD, £5k pension RaS, no SL, £10k invoice, 2026/27. "
        "eBRL = 55,270. start_income=48k, end=58k. "
        "Below eBRL: 55,270 − 48,000 = £7,270 at 20%. Above eBRL: £2,730 at 40%. "
        "NI on freelance: YTD=0 < LPL; end_profit=10k < LPL. NI=0. "
        "Tests: invoice correctly split across eBRL boundary with pension extension.",
        ["pig", "pension", "band_straddle"],
        salary=48000, ytd=0, pension=5000, plans=[], invoice=10000,
    ),

    _it("RW-S3-027",
        "Pension reduces ANI for IT but SL is on gross income — decoupled effects",
        "£40k salary, £10k YTD, £15k pension RaS, Plan 2 only, £10k invoice, 2026/27. "
        "eBRL = 65,270. ANI_start = 50k − 15k = 35k. ANI_end = 60k − 15k = 45k. "
        "IT is based on ANI (pension reduces tax); SL Plan 2 is on gross income (no pension deduction). "
        "SL Plan 2 (£29,385): start_income=50k > threshold; 9% × 10k = £900. "
        "NI on freelance: YTD=10k < LPL; end=20k > LPL. NI = 6% × (20k − 12,570) = £445.80. "
        "Tests: pension reduces IT but does not reduce student-loan repayment.",
        ["pig", "pension", "student_loan", "decoupled"],
        salary=40000, ytd=10000, pension=15000, plans=[2], invoice=10000,
    ),

    _it("RW-S3-028",
        "Pension with PGL — income near PGL threshold; pension does not reduce SL",
        "£0 salary, £18k YTD, £5k pension RaS, PGL only, £10k invoice, 2026/27. "
        "start_income=18k, end=28k. PGL threshold=£21k. Crosses PGL mid-invoice. "
        "ANI_start=13k, ANI_end=23k. IT = 20% portion of income above PA. "
        "NI: YTD=18k > LPL; end=28k. NI = 6% × 10k = £600. "
        "PGL marginal = 6% × (28k − 21k) = 6% × 7k = £420. "
        "Tests: pension does NOT reduce SL income (SL is on gross), "
        "even though pension reduces ANI for IT purposes.",
        ["pig", "pension", "student_loan"],
        salary=0, ytd=18000, pension=5000, plans=["postgraduate"], invoice=10000,
    ),

    _it("RW-S3-029",
        "Pension extends eBRL just past BRL — invoice exactly straddles the new eBRL",
        "£45k salary, £0 YTD, £2k pension RaS, no SL, £10k invoice, 2026/27. "
        "eBRL = 52,270. start_income=45k, end=55k. "
        "eBRL splits the invoice: £7,270 at 20%, £2,730 at 40%. "
        "NI on freelance: YTD=0; end_profit=10k < LPL. NI=0. "
        "Tests: small pension contribution correctly extends BRL by exactly the pension amount.",
        ["pig", "pension"],
        salary=45000, ytd=0, pension=2000, plans=[], invoice=10000,
    ),

    _it("RW-S3-030",
        "Pension + PA taper + ART crossing — three-zone income tax interaction (EL-001)",
        "£0 salary, £110k YTD, £15k pension RaS, no SL, £25k invoice, 2026/27. "
        "ANI_start = 95k (below taper). ANI_end = 120k (in taper). EL-001 zone. "
        "Income: 110k→135k. Crosses ART (£125,140) — some at 40%, some at 45%. "
        "NI: YTD=110k > UPL; end=135k. NI = 2% × 25k = £500. "
        "Pension preserves PA at start but invoice crosses into taper and through ART. "
        "Tests: IT computation correctly handles PA change + ART crossing in one invoice.",
        ["pig", "el001_family", "pension", "art_crossing"],
        salary=0, ytd=110000, pension=15000, plans=[], invoice=25000,
    ),

    _it("RW-S3-031",
        "Pension exactly prevents PA taper — ANI stays at £100,000 throughout invoice",
        "£100k salary, £0 YTD, £k pension large enough to reduce ANI to exactly 100k, "
        "no SL, £10k invoice, 2026/27. "
        "Pension = salary − 100,000 = £0 (salary already at taper; need pension to keep below). "
        "Use: £95k salary, £10k pension, £10k invoice. "
        "ANI_start = 95k − 10k = 85k. ANI_end = 105k − 10k = 95k. No taper (both < 100k). "
        "PA = £12,570 throughout. Invoice at 40%. "
        "Tests: pension correctly keeps ANI below taper even as income rises with invoice.",
        ["pig", "pension", "taper_prevention"],
        salary=95000, ytd=0, pension=10000, plans=[], invoice=10000,
    ),

    _it("RW-S3-032",
        "Comparison baseline — no pension, salary in higher rate (for RW-S3-033)",
        "£55k salary, £0 YTD, no pension, no SL, £10k invoice, 2026/27. "
        "Invoice entirely above BRL at 40%. IT = 40% × 10k = £4,000. "
        "This is the baseline against which RW-S3-033 (with pension) is compared. "
        "NI on freelance: YTD=0; end=10k < LPL. NI=0.",
        ["pig", "pension_comparison"],
        salary=55000, ytd=0, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S3-033",
        "Large pension saves entire invoice from higher rate — paired with RW-S3-032",
        "£55k salary, £0 YTD, £15k pension RaS, no SL, £10k invoice, 2026/27. "
        "eBRL = 65,270. start=55k, end=65k. Entire invoice below eBRL. "
        "IT = 20% (not 40%). Saving vs RW-S3-032 baseline: 20% × 10k = £2,000 less tax. "
        "Tests: pension eBRL extension correctly changes band allocation for entire invoice.",
        ["pig", "pension_comparison", "band_shift"],
        salary=55000, ytd=0, pension=15000, plans=[], invoice=10000,
    ),

    _it("RW-S3-034",
        "Pension + EL-001 zone + SL Plan 5 — three-way interaction",
        "£0 salary, £98k YTD, £3k pension RaS, Plan 5 only, £10k invoice, 2026/27. "
        "ANI_start = 95k (below taper). ANI_end = 105k (in taper). EL-001 zone. "
        "Plan 5 (£25,000 fixed): start=98k > threshold; marginal = 9% × 10k = £900. "
        "NI: YTD=98k > UPL; end=108k > UPL. NI = 2% × 10k = £200. "
        "Tests: PA taper interaction with SL and NI upper rate simultaneously.",
        ["pig", "el001_family", "pension", "student_loan"],
        salary=0, ytd=98000, pension=3000, plans=[5], invoice=10000,
    ),

    _it("RW-S3-035",
        "Massive pension contribution — ANI near zero; eBRL capped; no PA taper",
        "£0 salary, £0 YTD, £100k pension RaS, no SL, £50k invoice, 2026/27. "
        "ANI_start = 0 − 100k → max(0, 0) = 0. ANI_end = max(0, 50k − 100k) = 0. "
        "PA = £12,570 (full). eBRL = min(50,270 + 100,000, 125,140) = 125,140 (capped). "
        "IT: income=50k. (50k − 12,570) × 20% = 37,430 × 20% = £7,486. "
        "But this is a £50k invoice from zero. total_IT(50k, 100k) − total_IT(0, 100k) = "
        "7486 − 0 = £7,486. No 40% band applies because eBRL=125,140 > 50,000. "
        "NI: start_profit=0; end_profit=50k. NI = 6%×(50k−12,570) = 6%×37,430 = £2,245.80. "
        "Tests: massive pension correctly zeros ANI while eBRL cap and full PA apply.",
        ["pig", "pension", "ebrl_cap", "large_pension"],
        salary=0, ytd=0, pension=100000, plans=[], invoice=50000,
    ),

]


# ── GROUP SLX: Student-loan cross-plan and cross-year effects ─────────────────
# 10 scenarios — RW-S3-036 to RW-S3-045

SLX = [

    _it("RW-S3-036",
        "Plans 1 + 2 + 4 simultaneously — invoice crosses all three thresholds in 2026/27",
        "£0 salary, £20k YTD, no pension, Plans 1 + 2 + 4, £20k invoice, 2026/27. "
        "start_income=20k, end=40k. "
        "Plan 1 (£26,900): 9% × (40k − 26,900) = 9% × 13,100 = £1,179. "
        "Plan 2 (£29,385): 9% × (40k − 29,385) = 9% × 10,615 = £955.35. "
        "Plan 4 (£33,795): 9% × (40k − 33,795) = 9% × 6,205 = £558.45. "
        "IT: 20% band (basic rate). NI: start=20k > LPL; end=40k. NI = 6% × 20k = £1,200. "
        "Tests three independent SL plan threshold crossings in a single invoice.",
        ["slx", "student_loan", "multi_sl_crossing"],
        salary=0, ytd=20000, pension=0, plans=[1, 2, 4], invoice=20000,
    ),

    _it("RW-S3-037",
        "Plan 5 + PGL simultaneously — both thresholds crossed by invoice",
        "£0 salary, £18k YTD, no pension, Plan 5 + PGL, £10k invoice, 2026/27. "
        "start_income=18k, end=28k. "
        "Plan 5 (£25,000 fixed): 9% × (28k − 25k) = 9% × 3k = £270. "
        "PGL (£21,000 fixed): 6% × (28k − 21k) = 6% × 7k = £420. "
        "NI: start=18k > LPL; end=28k. NI = 6% × 10k = £600. "
        "IT: basic rate. "
        "Tests two fixed-threshold SL plans (no year variation) crossing simultaneously.",
        ["slx", "student_loan"],
        salary=0, ytd=18000, pension=0, plans=[5, "postgraduate"], invoice=10000,
    ),

    _it("RW-S3-038",
        "Plan 1 + pension — pension reduces IT but SL repayment based on gross income",
        "£0 salary, £20k YTD, £8k pension RaS, Plan 1 only, £10k invoice, 2026/27. "
        "start_income=20k. end_income=30k. "
        "ANI_start = 12k. ANI_end = 22k. No taper. "
        "Plan 1 (£26,900): based on gross income (no pension deduction). "
        "SL Plan 1 = 9% × (30k − 26,900) = 9% × 3,100 = £279. "
        "IT: ANI_end=22k, PA=12,570. Some IT at basic rate. "
        "NI: start=20k > LPL; end=30k. NI = 6% × 10k = £600. "
        "Tests: pension correctly reduces IT (via ANI/eBRL) but does NOT reduce SL repayment "
        "(which uses gross income, not ANI).",
        ["slx", "student_loan", "pension", "decoupled"],
        salary=0, ytd=20000, pension=8000, plans=[1], invoice=10000,
    ),

    _it("RW-S3-039",
        "Plan 2 threshold crossing — 2025/26 threshold (£28,470) vs 2026/27 (£29,385)",
        "£0 salary, £27k YTD, no pension, Plan 2 only, £5k invoice, 2025/26. "
        "start_income=27k, end=32k. "
        "Plan 2 (2025/26 threshold £28,470): end=32k > threshold. "
        "Marginal SL Plan 2 = 9% × (32k − 28,470) = 9% × 3,530 = £317.70. "
        "NI: start=27k > LPL; end=32k. NI = 6% × 5k = £300. "
        "IT: basic rate. "
        "If 2026/27 threshold (£29,385) applied: 9% × (32k − 29,385) = £235.35. Difference = £82.35. "
        "Paired with RW-S3-040 to confirm year-threshold difference.",
        ["slx", "student_loan", "year_comparison"],
        salary=0, ytd=27000, pension=0, plans=[2], invoice=5000,
        year="2025/26",
    ),

    _it("RW-S3-040",
        "Plan 2 threshold crossing — same income in 2026/27 (higher threshold = lower repayment)",
        "Identical to RW-S3-039 but 2026/27. "
        "Plan 2 (2026/27 threshold £29,385): 9% × (32k − 29,385) = 9% × 2,615 = £235.35. "
        "Compared to £317.70 in 2025/26: £82.35 lower repayment due to higher threshold. "
        "IT and NI identical (both use frozen 2026/27 thresholds).",
        ["slx", "student_loan", "year_comparison"],
        salary=0, ytd=27000, pension=0, plans=[2], invoice=5000,
    ),

    _it("RW-S3-041",
        "All five plans — income starts below all thresholds, invoice crosses all five",
        "£0 salary, £18k YTD, no pension, all five SL plans, £20k invoice, 2026/27. "
        "start_income=18k (below PGL=21k, Plan5=25k, Plan1=26.9k, Plan2=29.385k, Plan4=33.795k). "
        "end_income=38k (above all thresholds). "
        "PGL: 6%×(38k−21k)=6%×17k=£1,020. Plan 5: 9%×(38k−25k)=9%×13k=£1,170. "
        "Plan 1: 9%×(38k−26,900)=9%×11,100=£999. Plan 2: 9%×(38k−29,385)=9%×8,615=£775.35. "
        "Plan 4: 9%×(38k−33,795)=9%×4,205=£378.45. "
        "NI: start=18k > LPL; end=38k. NI = 6%×20k=£1,200. "
        "Tests: all five SL plans activate at their own thresholds within one invoice.",
        ["slx", "student_loan", "all_plans_activate"],
        salary=0, ytd=18000, pension=0,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=20000,
    ),

    _it("RW-S3-042",
        "Plan 4 — threshold crossing with NI UPL interaction in 2026/27",
        "£0 salary, £45k YTD, no pension, Plan 4 only, £15k invoice, 2026/27. "
        "start_profit=45k, end_profit=60k. NI crosses UPL (£50,270): "
        "main: 6%×(50,270−45,000)=6%×5,270=£316.20. upper: 2%×(60k−50,270)=2%×9,730=£194.60. "
        "Plan 4 (£33,795): start=45k > threshold; 9%×15k=£1,350. "
        "IT: basic rate portion + higher rate portion (BRL=50,270). "
        "Tests: SL Plan 4 active while NI transitions from main to upper rate.",
        ["slx", "student_loan", "ni_upl"],
        salary=0, ytd=45000, pension=0, plans=[4], invoice=15000,
    ),

    _it("RW-S3-043",
        "Plan 5 + Plan 2 — Plan 5 fixed threshold both years; Plan 2 changes year-over-year",
        "£0 salary, £23k YTD, no pension, Plan 5 + Plan 2, £10k invoice, 2025/26. "
        "start_income=23k, end=33k. "
        "Plan 5 (fixed £25,000): 9%×(33k−25k)=9%×8k=£720. "
        "Plan 2 (2025/26 £28,470): 9%×(33k−28,470)=9%×4,530=£407.70. "
        "Compare: if 2026/27, Plan 2 threshold=£29,385: 9%×(33k−29,385)=£325.35. "
        "Plan 5 is identical both years. Plan 2 differs. "
        "Tests the mixture of fixed and variable threshold plans across years.",
        ["slx", "student_loan", "year_comparison"],
        salary=0, ytd=23000, pension=0, plans=[5, 2], invoice=10000,
        year="2025/26",
    ),

    _it("RW-S3-044",
        "PGL (Postgraduate) alone crossing threshold + IT band interaction",
        "£37k salary, £0 YTD, no pension, PGL only, £5k invoice, 2026/27. "
        "start_income=37k, end=42k. "
        "PGL (£21,000 fixed): start=37k > threshold; 6%×5k=£300. "
        "IT: start=37k < BRL (50,270). IT = 20%×5k=£1,000. "
        "NI on freelance: YTD=0; end_profit=5k < LPL. NI=0. "
        "Tests PGL (the rarer plan) in isolation with a salary already above its threshold.",
        ["slx", "student_loan"],
        salary=37000, ytd=0, pension=0, plans=["postgraduate"], invoice=5000,
    ),

    _it("RW-S3-045",
        "Plan 4 + Plan 5 + pension — both SL plans above threshold; pension extends eBRL",
        "£45k salary, £0 YTD, £8k pension RaS, Plan 4 + Plan 5, £10k invoice, 2026/27. "
        "eBRL = 58,270. start_income=45k, end=55k. "
        "Both plans: start=45k > Plan4 (£33,795) and Plan5 (£25k). "
        "SL Plan 4 = 9%×10k=£900. SL Plan 5 = 9%×10k=£900. Total SL=£1,800. "
        "IT: eBRL=58,270 > end=55k. Entire invoice at 20% (pension eBRL extension working). "
        "NI: YTD=0; end_profit=10k < LPL. NI=0. "
        "Tests: two SL plans active while pension correctly prevents band crossing.",
        ["slx", "student_loan", "pension"],
        salary=45000, ytd=0, pension=8000, plans=[4, 5], invoice=10000,
    ),

]


# ── GROUP CGX: CGT + income-tax interaction ───────────────────────────────────
# 10 scenarios — RW-S3-046 to RW-S3-055

CGX = [

    _cgt("RW-S3-046",
        "CGT: high income exhausts BRL — entire gain at higher rate (24%)",
        "Taxable income £50,270 (at BRL). CGT gain £20,000. AEA deducted: £17,000 taxable. "
        "Basic rate band remaining = 50,270 − 50,270 = £0. Entire gain at 24%. "
        "CGT = 24% × 17,000 = £4,080. "
        "Tests: when taxable income is exactly at BRL, no basic-rate band remains for CGT.",
        ["cgx", "cgt"],
        disposals=[_d("shares", "Tech stock", 25000, 5000)],
        tib=50270,
    ),

    _cgt("RW-S3-047",
        "CGT: income below PA — all gain at basic rate (18%); BRL fully available",
        "Taxable income £0 (below PA; no IT). CGT gain £20,000. AEA: £3,000. "
        "Taxable gain = £17,000. BRL remaining = 50,270. All at basic rate 18%. "
        "CGT = 18% × 17,000 = £3,060. "
        "Tests: CGT basic-rate band correctly spans full BRL when taxable income is zero.",
        ["cgx", "cgt"],
        disposals=[_d("shares", "Index fund", 23000, 3000)],
        tib=0,
    ),

    _cgt("RW-S3-048",
        "CGT: pension reduces taxable income; frees BRL for CGT basic rate",
        "Gross income £60k. Pension RaS £15k. ANI=45k. Taxable income before gains = 45k − 12,570 = £32,430. "
        "CGT gain £20,000. AEA: £3,000. Taxable gain £17,000. "
        "BRL remaining = 50,270 − 32,430 = £17,840. Gain fits within basic rate band. "
        "CGT = 18% × 17,000 = £3,060 (all at basic rate). "
        "Without pension: taxable income = 60k − 12,570 = 47,430; BRL remaining = 2,840; "
        "split: 18%×2,840 + 24%×14,160 = 511.20 + 3,398.40 = £3,909.60. "
        "Tests: pension's effect on taxable income changes the CGT rate split.",
        ["cgx", "cgt", "pension_cgt"],
        disposals=[_d("shares", "ETF", 22000, 2000)],
        tib=32430,
    ),

    _cgt("RW-S3-049",
        "CGT: income partially fills BRL — gain split basic/higher rate",
        "Taxable income £35,000. BRL remaining = 50,270 − 35,000 = £15,270. "
        "CGT gain £25,000. AEA £3,000. Taxable gain £22,000. "
        "Basic slice: £15,270 at 18% = £2,748.60. Higher slice: £6,730 at 24% = £1,615.20. "
        "Total CGT = £4,363.80. "
        "Tests: correctly splitting a gain across the basic/higher boundary.",
        ["cgx", "cgt"],
        disposals=[_d("shares", "Mixed portfolio", 30000, 5000)],
        tib=35000,
    ),

    _cgt("RW-S3-050",
        "CGT: taxable income in PA taper zone — reduced PA affects taxable income",
        "Income £110,000. PA = £12,570 − (110k−100k)/2 = £7,570 (taper applies). "
        "Taxable income before gains = 110,000 − 7,570 = £102,430. "
        "BRL remaining = max(0, 50,270 − 102,430) = £0. Entire gain at higher rate (24%). "
        "CGT gain £15,000. AEA £3,000. Taxable gain £12,000. CGT = 24% × 12,000 = £2,880. "
        "Tests: PA taper reduction of taxable income feeds correctly into CGT rate split.",
        ["cgx", "cgt", "el001_family"],
        disposals=[_d("shares", "Growth fund", 20000, 5000)],
        tib=102430,
    ),

    _cgt("RW-S3-051",
        "CGT: two disposals + income in higher rate — both disposals fully at 24%",
        "Taxable income £80,000 (well above BRL). BRL remaining = £0. "
        "Two disposals: Disposal A gain £10,000; Disposal B gain £8,000. "
        "Total gains = £18,000. AEA = £3,000. Taxable gains = £15,000. "
        "CGT = 24% × 15,000 = £3,600. "
        "Tests multiple disposals with income that exhausts basic-rate band.",
        ["cgx", "cgt"],
        disposals=[
            _d("shares", "Portfolio A", 15000, 5000),
            _d("crypto",  "Crypto B",   12000, 4000, date="2026-10-01"),
        ],
        tib=80000,
    ),

    _cgt("RW-S3-052",
        "CGT: brought-forward losses reduce taxable gain to zero; high income",
        "Taxable income £70,000. CGT gain £20,000. BF losses £25,000. "
        "Net gain after BF losses = max(0, 20,000 − 25,000) = £0. "
        "AEA not needed; taxable gain = £0. CGT = £0. "
        "Tests: BF losses correctly eliminating the taxable gain before AEA is applied.",
        ["cgx", "cgt"],
        disposals=[_d("shares", "Growth ETF", 25000, 5000)],
        tib=70000, bf=25000,
    ),

    _cgt("RW-S3-053",
        "CGT: same income and gain in 2025/26 — rates and AEA identical to 2026/27",
        "Taxable income £40,000. CGT gain £15,000. AEA £3,000. "
        "BRL remaining = 50,270 − 40,000 = £10,270. "
        "Taxable gain = £12,000. Basic slice: £10,270 at 18% = £1,848.60. "
        "Higher slice: £1,730 at 24% = £415.20. Total = £2,263.80. "
        "Same calculation in 2025/26 (rates post-Oct 2024, AEA fixed at £3,000). "
        "Tests: CGT rates and AEA are correctly applied in 2025/26 as well as 2026/27.",
        ["cgx", "cgt", "year_comparison"],
        disposals=[_d("shares", "UK equities", 18000, 3000)],
        tib=40000,
        year="2025/26",
    ),

    _cgt("RW-S3-054",
        "CGT: three disposals with mixed gains and losses + income splits BRL",
        "Taxable income £42,000. BRL remaining = 50,270 − 42,000 = £8,270. "
        "Three disposals: gain £18,000, gain £5,000, loss £7,000. "
        "Net current-year gains: 18,000 + 5,000 − 7,000 = £16,000. "
        "AEA £3,000. Taxable gain = £13,000. "
        "Basic slice: £8,270 at 18% = £1,488.60. Higher slice: £4,730 at 24% = £1,135.20. "
        "Total CGT = £2,623.80. "
        "Tests: current-year losses netting correctly against gains before AEA, "
        "with a split rate calculation.",
        ["cgx", "cgt"],
        disposals=[
            _d("shares", "Gain A",   22000, 4000),
            _d("shares", "Gain B",    8000, 3000),
            _d("crypto",  "Loss C",   3000, 10000, date="2026-08-01"),
        ],
        tib=42000,
    ),

    _cgt("RW-S3-055",
        "CGT: very large gain in 2025/26 — all at higher rate; partially paid",
        "Taxable income £80,000 (BRL exhausted). CGT gain £100,000. AEA £3,000. "
        "Taxable gain = £97,000. All at higher rate 24%. CGT = £23,280. "
        "Tax already paid (on account) = £10,000. Outstanding = £13,280. "
        "Tests: large CGT with partial payment in 2025/26.",
        ["cgx", "cgt"],
        disposals=[_d("other", "Business asset", 120000, 20000)],
        tib=80000, paid=10000,
        year="2025/26",
    ),

]


# ── GROUP YTC: Year-to-year comparison ───────────────────────────────────────
# 5 scenarios — RW-S3-056 to RW-S3-060

YTC = [

    _it("RW-S3-056",
        "Plan 1 — income starts below 2025/26 threshold (£24,990); crosses in 2025/26 only",
        "£0 salary, £23k YTD, no pension, Plan 1 only, £5k invoice, 2025/26. "
        "start_income=23k, end=28k. "
        "Plan 1 (2025/26 threshold £24,990): SL = 9% × (28k − 24,990) = 9% × 3,010 = £270.90. "
        "If 2026/27: threshold £26,900; SL = 9% × (28k − 26,900) = 9% × 1,100 = £99. "
        "SL is £171.90 higher in 2025/26. IT and NI the same. "
        "Tests: correct 2025/26 threshold applied when start income is below threshold.",
        ["ytc", "student_loan", "year_comparison"],
        salary=0, ytd=23000, pension=0, plans=[1], invoice=5000,
        year="2025/26",
    ),

    _it("RW-S3-057",
        "Plan 1 — same income in 2026/27 (higher threshold = lower SL repayment)",
        "Identical to RW-S3-056 but 2026/27. "
        "Plan 1 (2026/27 threshold £26,900): SL = 9% × (28k − 26,900) = 9% × 1,100 = £99. "
        "£171.90 less than 2025/26, confirming the 2026/27 threshold uplift effect.",
        ["ytc", "student_loan", "year_comparison"],
        salary=0, ytd=23000, pension=0, plans=[1], invoice=5000,
    ),

    _it("RW-S3-058",
        "Plan 4 — income straddles the 2025/26 threshold (£32,745)",
        "£0 salary, £30k YTD, no pension, Plan 4 only, £8k invoice, 2025/26. "
        "start_income=30k, end=38k. "
        "Plan 4 (2025/26 threshold £32,745): SL = 9% × (38k − 32,745) = 9% × 5,255 = £472.95. "
        "IT: basic rate on invoice. NI: start=30k > LPL; end=38k. NI=6%×8k=£480. "
        "Paired with RW-S3-059 (2026/27 threshold £33,795).",
        ["ytc", "student_loan", "year_comparison"],
        salary=0, ytd=30000, pension=0, plans=[4], invoice=8000,
        year="2025/26",
    ),

    _it("RW-S3-059",
        "Plan 4 — same income in 2026/27 (threshold £33,795 vs £32,745 in 2025/26)",
        "Identical to RW-S3-058 but 2026/27. "
        "Plan 4 (2026/27 threshold £33,795): SL = 9% × (38k − 33,795) = 9% × 4,205 = £378.45. "
        "£94.50 less than 2025/26. IT and NI identical. "
        "Tests the specific Plan 4 threshold uplift from 2025/26 to 2026/27.",
        ["ytc", "student_loan", "year_comparison"],
        salary=0, ytd=30000, pension=0, plans=[4], invoice=8000,
    ),

    _it("RW-S3-060",
        "All plans — profile where Plans 1 and 2 cross thresholds in 2025/26 but not 2026/27",
        "£0 salary, £24k YTD, no pension, all five SL plans, £8k invoice, 2025/26. "
        "start_income=24k, end=32k. "
        "PGL (£21k fixed): 6%×(32k−21k)=6%×11k=£660. "
        "Plan 5 (£25k fixed): 9%×(32k−25k)=9%×7k=£630. "
        "Plan 1 (2025/26 £24,990): start=24k < threshold; 9%×(32k−24,990)=9%×7,010=£630.90. "
        "Plan 2 (2025/26 £28,470): start=24k < threshold; 9%×(32k−28,470)=9%×3,530=£317.70. "
        "Plan 4 (2025/26 £32,745): end=32k < threshold; SL=£0 (income stays below). "
        "In 2026/27: Plan 1 threshold=£26,900 (start=24k still below; end=32k still crosses). "
        "Plan 4 threshold=£33,795 (end=32k still below; SL=0). "
        "Main 2025/26 vs 2026/27 difference: Plan 1 SL changes. "
        "Tests: correct year-specific thresholds applied when income straddles different points.",
        ["ytc", "student_loan", "year_comparison", "all_plans_activate"],
        salary=0, ytd=24000, pension=0,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=8000,
        year="2025/26",
    ),

]


# ── GROUP SEQ: Sequential invoice behaviour under interaction ─────────────────
# 5 scenarios — RW-S3-061 to RW-S3-065
#
# Stage 2 verified sequential invoices for simple profiles (SEQ group).
# These scenarios confirm that the before/after differential remains correct
# when the starting income is already in a complex position: within the PA
# taper zone, straddling eBRL, or at an SL threshold boundary.

SEQ = [

    _it("RW-S3-061",
        "Sequential: second invoice with profile already fully within EL-001 zone",
        "£0 salary, £105k YTD, no pension, no SL, £10k invoice, 2026/27. "
        "Profile is already in the taper after prior invoices. "
        "ANI_start = 105k (PA = £10,070). ANI_end = 115k (PA = £5,070). "
        "Both start and end are within the taper zone — invoice does not enter or exit taper. "
        "NI: profit 105k→115k, entirely above UPL. NI = 2% × 10k = £200. "
        "IT = total_IT(115k,0) − total_IT(105k,0). "
        "Without taper: 40% × 10k = £4,000. Taper cost: PA decrease 7,500 × 20% = £1,500. "
        "Hmm: PA_start = 10,070 (ANI 105k), PA_end = 5,070 (ANI 115k). Decrease = 5,000. "
        "Extra tax = 5,000 × 20% = £1,000. IT = 4,000 + 1,000 = £5,000. "
        "Tests: the engine correctly computes the second invoice when the starting profile "
        "is already in the taper zone, not just entering it.",
        ["seq", "el001_family"],
        salary=0, ytd=105000, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S3-062",
        "Sequential: second invoice straddling eBRL — profile starts exactly at BRL",
        "£45k salary, £5,270 YTD profit, £5k pension RaS, Plan 2, £10k invoice, 2026/27. "
        "YTD chosen so start_income = 45,000 + 5,270 = 50,270 (exactly at BRL). "
        "This simulates a second invoice where the first ended exactly at the BRL. "
        "eBRL = 55,270. Invoice: £5,000 at 20% (50,270→55,270) + £5,000 at 40% (55,270→60,270). "
        "IT = total_IT(60,270, 5k) − total_IT(50,270, 5k) = £3,000. "
        "NI: YTD profit 5,270 (below LPL 12,570); end profit 15,270 (above LPL). "
        "NI = 6% × (15,270 − 12,570) = 6% × 2,700 = £162. "
        "SL Plan 2 (£29,385): start = 50,270 > threshold; 9% × 10k = £900. "
        "Tests: pension eBRL extension splits the invoice correctly when starting exactly at BRL.",
        ["seq", "pension", "student_loan"],
        salary=45000, ytd=5270, pension=5000, plans=[2], invoice=10000,
    ),

    _it("RW-S3-063",
        "Sequential: second invoice crosses SL Plan 1 threshold mid-invoice",
        "£0 salary, £25k YTD, no pension, Plan 1 only, £5k invoice, 2026/27. "
        "YTD = £25k means first invoice(s) have already been raised below the SL threshold. "
        "start_income = 25k (below Plan 1 threshold £26,900). end = 30k (above threshold). "
        "SL Plan 1 = 9% × (30k − 26,900) = 9% × 3,100 = £279. "
        "IT: 20% × 5k = £1,000. NI: profit 25k→30k (above LPL £12,570); 6% × 5k = £300. "
        "Tests: SL Plan 1 was zero on prior invoices; activates correctly on this invoice "
        "as threshold is crossed mid-invoice.",
        ["seq", "student_loan"],
        salary=0, ytd=25000, pension=0, plans=[1], invoice=5000,
    ),

    _it("RW-S3-064",
        "Sequential: second invoice fully within EL-001 zone with pension active",
        "£0 salary, £110k YTD, £5k pension RaS, no SL, £10k invoice, 2026/27. "
        "First invoice has already moved the profile into the taper zone. "
        "ANI_start = 110k − 5k = 105k (PA = £10,070). "
        "ANI_end = 120k − 5k = 115k (PA = £5,070). Both in taper. EL-001 zone. "
        "eBRL = 55,270 (income well above eBRL; invoice at 40% + taper adjustment). "
        "IT = total_IT(120k, 5k) − total_IT(110k, 5k). "
        "PA_start = 10,070; PA_end = 5,070. PA decrease = 5,000. "
        "40% × 10k = 4,000. Taper cost = 5,000 × 20% = 1,000. IT = £5,000. "
        "NI: profit 110k→120k > UPL; 2% × 10k = £200. "
        "Tests: pension correctly adjusts ANI and thus the taper PA for a second-position "
        "invoice where the profile is already in the taper zone.",
        ["seq", "el001_family", "pension"],
        salary=0, ytd=110000, pension=5000, plans=[], invoice=10000,
    ),

    _it("RW-S3-065",
        "Sequential: third-position invoice — all components in their upper bands",
        "£0 salary, £60k YTD, no pension, Plan 2 + PGL, £10k invoice, 2026/27. "
        "YTD = £60k: prior invoices have already taken profit past UPL and all SL thresholds. "
        "start_profit = 60k (above UPL £50,270 and both SL thresholds). "
        "NI: entirely at upper rate. 2% × 10k = £200. "
        "SL Plan 2 (£29,385): 9% × 10k = £900. PGL (£21k): 6% × 10k = £600. Total SL = £1,500. "
        "IT: 40% × 10k = £4,000 (income 60k→70k entirely above BRL). "
        "Tests: a late-in-year invoice where every component is in its upper band applies "
        "upper-band rates correctly without contamination from lower-band calculations.",
        ["seq", "student_loan"],
        salary=0, ytd=60000, pension=0, plans=[2, "postgraduate"], invoice=10000,
    ),

]


# ── GROUP TOL: Tolerance and stress ───────────────────────────────────────────
# 7 scenarios — RW-S3-066 to RW-S3-072
#
# Selected extreme scenarios designed to probe the engine beyond its expected
# operating envelope.  Each targets a specific robustness concern: arithmetic
# at extreme magnitudes, sub-penny rounding, practical user ceiling under all
# components simultaneously, and the joint EL-003 + EL-001 constraint.

TOL = [

    _it("RW-S3-066",
        "Stress: very large invoice from zero — traverses all IT and NI bands",
        "£0 salary, £0 YTD, no pension, no SL, £300k invoice, 2026/27. "
        "Traverses every IT band: PA (0–£12,570 at 0%), basic (£12,570–£50,270 at 20%), "
        "higher (£50,270–£125,140 at 40%), additional (£125,140–£300k at 45%). "
        "ANI_end = £300k > taper elimination. PA = £0. "
        "IT = 50,270×20% + 74,870×40% + 174,860×45% = 10,054 + 29,948 + 78,687 = £118,689. "
        "NI: main = 6%×37,700 = £2,262; upper = 2%×249,730 = £4,994.60. NI = £7,256.60. "
        "Tests: engine handles very large invoice amounts without arithmetic failure, "
        "and all four IT bands are correctly applied in a single invoice from zero.",
        ["tol", "stress"],
        salary=0, ytd=0, pension=0, plans=[], invoice=300000,
    ),

    _it("RW-S3-067",
        "Stress: pension at annual allowance limit (£60k) — entire invoice at 20%",
        "£80k salary, £0 YTD, £60k pension RaS (annual allowance), no SL, £20k invoice, 2026/27. "
        "eBRL = min(50,270 + 60,000, 125,140) = 110,270 (not capped — below ART). "
        "ANI_start = 20k (below taper). ANI_end = 40k (below taper). "
        "Income: 80k→100k. Both below eBRL = 110,270. Invoice entirely at 20%. "
        "IT = 20% × 20k = £4,000. "
        "NI: sole-trader profit 0→20k. 6% × (20k − 12,570) = 6% × 7,430 = £445.80. "
        "Tests: pension at the practical annual allowance ceiling correctly extends "
        "the basic-rate band to shelter an invoice that would otherwise be at 40%.",
        ["tol", "pension", "stress"],
        salary=80000, ytd=0, pension=60000, plans=[], invoice=20000,
    ),

    _it("RW-S3-068",
        "Stress: sub-penny invoice at additional rate — rounding to correct penny",
        "£0 salary, £130k YTD, no pension, no SL, £0.05 invoice, 2026/27. "
        "Invoice entirely above ART (£125,140). IT = 45% × 0.05 = 0.0225 → £0.02 (ROUND_HALF_UP). "
        "NI: sole-trader profit 130k→130,000.05; above UPL. "
        "2% × 0.05 = 0.001 → £0.00. Total = £0.02. "
        "Tests: sub-penny invoice amounts at the 45% rate are correctly rounded and "
        "do not cause arithmetic errors or zero-division failures.",
        ["tol", "stress", "rounding"],
        salary=0, ytd=130000, pension=0, plans=[], invoice="0.05",
    ),

    _it("RW-S3-069",
        "Stress: sub-pound invoice with multiple SL plans — ROUND_HALF_UP on half-penny",
        "£0 salary, £40k YTD, £5k pension RaS, Plan 2 + PGL, £0.50 invoice, 2026/27. "
        "All SL thresholds already exceeded; pension extends eBRL; income in basic-rate band. "
        "IT: 20% × 0.50 = 0.10 → £0.10. "
        "NI: profit 40k→40,000.50; above LPL, below UPL. 6% × 0.50 = 0.03 → £0.03. "
        "SL Plan 2: 9% × 0.50 = 0.045 → £0.05 (ROUND_HALF_UP: 0.045 rounds UP to £0.05). "
        "PGL: 6% × 0.50 = 0.03 → £0.03. Total SL = £0.08. Total = £0.21. "
        "Tests: ROUND_HALF_UP is applied correctly when SL produces a half-penny result; "
        "the total accumulates correctly across multiple independently rounded components.",
        ["tol", "stress", "rounding", "student_loan"],
        salary=0, ytd=40000, pension=5000, plans=[2, "postgraduate"], invoice="0.50",
    ),

    _it("RW-S3-070",
        "Stress: EL-003 cap + EL-001 zone simultaneously — large pension + invoice crosses taper",
        "£120k salary, £60k YTD, £80k pension RaS, no SL, £10k invoice, 2026/27. "
        "Two constraints active simultaneously: "
        "(1) EL-003: pension = £80k > £74,870 → eBRL capped at ART = £125,140. "
        "(2) EL-001: ANI crosses the taper zone during the invoice. "
        "ANI_start = (180k − 80k) = 100k (taper start; PA = £12,570 — no reduction yet). "
        "ANI_end = (190k − 80k) = 110k (in taper; PA = 12,570 − 5,000 = £7,570). "
        "start_income = 180k > ART; end = 190k > ART. Invoice entirely at 45%. "
        "IT = 45% × 10k = £4,500 (additional rate) + 5,000 × 20% = £1,000 (taper cost). "
        "IT = £5,500. NI: profit 60k→70k > UPL; 2% × 10k = £200. Total = £5,700. "
        "Tests: the EL-003 fix (eBRL capped at ART) and EL-001 differential are both "
        "applied correctly in a single invoice where both constraints are simultaneously active.",
        ["tol", "el001_family", "pension", "ebrl_cap", "stress"],
        salary=120000, ytd=60000, pension=80000, plans=[], invoice=10000,
    ),

    _it("RW-S3-071",
        "Stress: practical user ceiling — all components at upper end of Reserved scope",
        "£100k salary, £70k YTD, £60k pension RaS, all five SL plans, £20k invoice, 2026/27. "
        "This is the most complex realistic profile for Reserved's target users. "
        "eBRL = min(50,270 + 60,000, 125,140) = 110,270. "
        "ANI_start = (170k − 60k) = 110k (in taper; PA = £7,570). "
        "ANI_end = (190k − 60k) = 130k (above taper; PA = £0). EL-001 zone. "
        "start = 170k > ART. end = 190k > ART. "
        "IT: additional rate 45% × 20k = £9,000 + taper cost 7,570 × 20% = £1,514. IT = £10,514. "
        "NI: profit 70k→90k > UPL; 2% × 20k = £400. "
        "All SL plans: start = 170k > all thresholds. "
        "Plans 1/2/4/5: 9% × 20k = £1,800 each × 4 = £7,200. PGL: 6% × 20k = £1,200. "
        "Total SL = £8,400. Total = 10,514 + 400 + 8,400 = £19,314. "
        "Tests: all five components at once near the practical ceiling of Reserved's scope.",
        ["tol", "el001_family", "pension", "student_loan", "all_components", "stress"],
        salary=100000, ytd=70000, pension=60000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=20000,
    ),

    _it("RW-S3-072",
        "Stress: pension just below EL-003 cap — eBRL near ART; large invoice crosses ART",
        "£0 salary, £50k YTD, £74k pension RaS, Plan 2, £80k invoice, 2026/27. "
        "eBRL = min(50,270 + 74,000, 125,140) = min(124,270, 125,140) = 124,270. "
        "Pension is just £870 below the EL-003 cap — eBRL is 870 below ART. "
        "ANI_start = max(0, 50k − 74k) = £0 (pension exceeds starting income; ANI floored). "
        "ANI_end = max(0, 130k − 74k) = £56k (below taper; PA = £12,570). "
        "IT = total_IT(130k, 74k) − total_IT(50k, 74k). "
        "total_IT(130k, 74k): basic (124,270−12,570)×20% = £22,340; "
        "higher (125,140−124,270)×40% = £348; additional (130k−125,140)×45% = £2,187; total = £24,875. "
        "total_IT(50k, 74k): ANI=£0, PA=£12,570; basic (50k−12,570)×20% = £7,486; total = £7,486. "
        "IT = £17,389. "
        "NI: profit 50k→130k; main 6%×(50,270−50,000) = £16.20; upper 2%×79,730 = £1,594.60. "
        "NI = £1,610.80. SL Plan 2 (£29,385): start=50k > threshold; 9% × 80k = £7,200. "
        "Total = 17,389 + 1,610.80 + 7,200 = £26,199.80. "
        "Tests: eBRL just below ART creates a small higher-rate slice (£870) above the basic "
        "band — confirming the engine correctly identifies the three-band split near the cap.",
        ["tol", "pension", "student_loan", "stress"],
        salary=0, ytd=50000, pension=74000, plans=[2], invoice=80000,
    ),

]


# ── GROUP CAG: CGT additional interaction ─────────────────────────────────────
# 3 scenarios — RW-S3-073 to RW-S3-075
#
# Extends CGX with pathways not yet covered: pension changing the CGT rate split
# when the gain straddles BRL, gain exactly eliminated by BF losses + AEA,
# and a large BF loss partially offsetting a very large gain in 2025/26.

CAG = [

    _cgt("RW-S3-073",
        "CGT: pension raises BRL remaining — gain split shifts toward basic rate",
        "Gross income £58k. Pension RaS £10k → ANI = £48k → taxable income = £35,430. "
        "BRL remaining = 50,270 − 35,430 = £14,840. "
        "Disposal: proceeds £25k, cost £5k, gain £20k. AEA £3k. Taxable gain £17k. "
        "Basic slice: min(17k, 14,840) = £14,840 at 18% = £2,671.20. "
        "Higher slice: £2,160 at 24% = £518.40. Total CGT = £3,189.60. "
        "Without pension: taxable income = £45,430; BRL remaining = £4,840; "
        "basic £4,840×18% + higher £12,160×24% = £871.20 + £2,918.40 = £3,789.60. "
        "Pension shifts £10k of gain from 24% to 18%, saving £600 in CGT. "
        "This extends RW-S3-048 (where pension kept all gain at 18%) to the case where "
        "the gain is larger and the split changes but does not become all-basic-rate.",
        ["cag", "cgt", "pension_cgt"],
        disposals=[_d("shares", "Growth ETF", 25000, 5000)],
        tib=35430,
    ),

    _cgt("RW-S3-074",
        "CGT: brought-forward losses + AEA exactly cancel the gain — zero liability",
        "Taxable income £70,000 (above BRL; BRL remaining = £0). "
        "Gain = £20,000. AEA = £3,000. Brought-forward losses = £17,000. "
        "Net gain after BF losses: 20,000 − 17,000 = £3,000. "
        "After AEA: 3,000 − 3,000 = £0. CGT = £0. "
        "Tests the specific boundary where BF losses and AEA together exactly eliminate "
        "the taxable gain. Complements RW-S3-052 (where BF losses alone exceeded the gain "
        "before AEA was applied), confirming the ordering: losses first, then AEA.",
        ["cag", "cgt"],
        disposals=[_d("shares", "UK equities", 25000, 5000)],
        tib=70000, bf=17000,
    ),

    _cgt("RW-S3-075",
        "CGT: very large BF loss partially offsets large gain — higher rate throughout (2025/26)",
        "Taxable income £90,000 (above BRL; BRL remaining = £0). "
        "Gain = £50,000. BF losses = £20,000. Net gain = £30,000. AEA = £3,000. "
        "Taxable gain = £27,000. All at higher rate (24%): CGT = £6,480. "
        "Year = 2025/26 (rates identical to 2026/27 post-Oct 2024). "
        "Tests: large BF losses reduce a large gain before AEA is applied; "
        "the remaining taxable gain is entirely at higher rate; "
        "2025/26 produces the correct result confirming year routing for CGT.",
        ["cag", "cgt", "year_comparison"],
        disposals=[_d("shares", "Business sale", 60000, 10000)],
        tib=90000, bf=20000,
        year="2025/26",
    ),

]


# ── GROUP CMP: Combined interaction — remaining gaps ─────────────────────────
# 5 scenarios — RW-S3-076 to RW-S3-080

CMP = [

    _it("RW-S3-076",
        "Combined: EL-001 zone + EL-003 cap + SL — three constraints simultaneously",
        "£0 salary, £180k YTD, £85k pension RaS, Plan 5, £10k invoice, 2026/27. "
        "EL-001: ANI_start = 95k (below taper; PA = £12,570). "
        "ANI_end = 105k (in taper; PA = £10,070). Invoice crosses taper entry. "
        "EL-003: pension = £85k > £74,870 → eBRL capped at ART = £125,140. "
        "start_income = 180k > ART; end = 190k > ART. "
        "IT = total_IT(190k, 85k) − total_IT(180k, 85k). "
        "PA_start = £12,570 (ANI=95k, below taper). PA_end = £10,070 (ANI=105k). "
        "PA decrease = 2,500. 45% × 10k = £4,500. Taper cost = 2,500 × 20% = £500. IT = £5,000. "
        "NI: profit 180k→190k > UPL; 2% × 10k = £200. "
        "SL Plan 5 (£25k fixed): start = 180k > threshold; 9% × 10k = £900. "
        "Total = 5,000 + 200 + 900 = £6,100. "
        "Tests: EL-003 cap and EL-001 zone and SL are all active simultaneously, "
        "with the invoice entering (not already in) the taper zone.",
        ["cmp", "el001_family", "pension", "ebrl_cap", "student_loan"],
        salary=0, ytd=180000, pension=85000, plans=[5], invoice=10000,
    ),

    _it("RW-S3-077",
        "Combined: all five SL plans + pension at annual allowance + income at 45%",
        "£60k salary, £70k YTD, £60k pension RaS, all five SL plans, £10k invoice, 2026/27. "
        "eBRL = min(50,270 + 60,000, 125,140) = 110,270 (not capped). "
        "ANI_start = 70k (below taper; PA = £12,570). ANI_end = 80k (below taper). "
        "start_income = 130k > ART; end = 140k > ART. Invoice entirely at 45%. "
        "IT = total_IT(140k, 60k) − total_IT(130k, 60k) = £4,500. "
        "NI: profit 70k→80k > UPL; 2% × 10k = £200. "
        "All SL: start = 130k > all thresholds. "
        "Plans 1/2/4/5: 9% × 10k = £900 × 4 = £3,600. PGL: 6% × 10k = £600. "
        "Total SL = £4,200. Total = 4,500 + 200 + 4,200 = £8,900. "
        "Tests: all five SL plans and annual-allowance pension with income at 45% rate. "
        "Confirms pension (eBRL extension) does not suppress the 45% rate here, "
        "since income is already above ART regardless of eBRL.",
        ["cmp", "pension", "student_loan", "all_components"],
        salary=60000, ytd=70000, pension=60000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=10000,
    ),

    _it("RW-S3-078",
        "Combined: NI sole-trader UPL + EL-001 zone — independence of NI and PA taper",
        "£0 salary, £100k YTD, no pension, no SL, £15k invoice, 2026/27. "
        "ANI_start = 100k (taper entry; PA = £12,570 — taper applies only above £100k). "
        "ANI_end = 115k (in taper; PA = £5,070). EL-001 zone. "
        "NI: sole-trader profit 100k→115k; all above UPL (£50,270). "
        "NI = 2% × 15k = £300. NI is on gross profit — unaffected by PA taper. "
        "IT = total_IT(115k, 0) − total_IT(100k, 0). "
        "PA_start = £12,570 (ANI=100k, taper not yet applied). "
        "PA_end = £5,070 (ANI=115k). PA decrease = 7,500. "
        "40% × 15k = £6,000. Taper cost = 7,500 × 20% = £1,500. IT = £7,500. "
        "Total = 7,500 + 300 = £7,800. "
        "Tests: Class 4 NI (upper rate) and the PA taper operate independently; "
        "NI is computed on gross profit without any PA taper adjustment.",
        ["cmp", "el001_family"],
        salary=0, ytd=100000, pension=0, plans=[], invoice=15000,
    ),

    _it("RW-S3-079",
        "Combined: SL Plan 4 + EL-001 zone — Scotland-origin loan on gross income, taper on ANI",
        "£0 salary, £105k YTD, no pension, Plan 4 only, £10k invoice, 2026/27. "
        "ANI_start = 105k (PA = £10,070). ANI_end = 115k (PA = £5,070). "
        "Both in taper zone. EL-001 zone. "
        "SL Plan 4 (£33,795): start = 105k > threshold; "
        "9% × 10k = £900 (Plan 4 is on gross income, not ANI). "
        "NI: profit 105k→115k > UPL; 2% × 10k = £200. "
        "IT = total_IT(115k, 0) − total_IT(105k, 0) = £5,000. "
        "Total = 5,000 + 200 + 900 = £6,100. "
        "Tests: SL Plan 4 repayment is correctly computed on gross income without "
        "any PA taper deduction, while income tax correctly applies the taper via the "
        "before/after differential.",
        ["cmp", "el001_family", "student_loan"],
        salary=0, ytd=105000, pension=0, plans=[4], invoice=10000,
    ),

    _it("RW-S3-080",
        "Combined: EL-001 zone + pension + SL in 2025/26 — frozen IT/NI confirmed",
        "£0 salary, £98k YTD, £3k pension RaS, Plan 2 only, £10k invoice, 2025/26. "
        "ANI_start = 95k (below taper; PA = £12,570). "
        "ANI_end = 105k (in taper; PA = £10,070). EL-001 zone. "
        "eBRL = 50,270 + 3,000 = 53,270. Income well above eBRL; invoice at 40%. "
        "PA_start = £12,570; PA_end = £10,070. PA decrease = 2,500. "
        "40% × 10k = £4,000. Taper cost = 2,500 × 20% = £500. IT = £4,500. "
        "NI: profit 98k→108k > UPL; 2% × 10k = £200. "
        "SL Plan 2 (2025/26 threshold £28,470): start = 98k > threshold; 9% × 10k = £900. "
        "Total = 4,500 + 200 + 900 = £5,600. "
        "In 2026/27: IT and NI identical (frozen bands). "
        "SL Plan 2 threshold = £29,385 (start = 98k > threshold); SL = 9% × 10k = £900. "
        "Results are identical in both years for this profile — confirming no regression "
        "from year routing when EL-001 zone + pension + SL are all active in 2025/26.",
        ["cmp", "el001_family", "pension", "student_loan", "year_comparison"],
        salary=0, ytd=98000, pension=3000, plans=[2], invoice=10000,
        year="2025/26",
    ),

]


# ── Assembly ──────────────────────────────────────────────────────────────────

STAGE_3: list[dict] = INT + PIG + SLX + CGX + YTC + SEQ + TOL + CAG + CMP

assert len(STAGE_3) == 80, f"Expected 80 Stage 3 scenarios, got {len(STAGE_3)}"
assert len({s["scenario_id"] for s in STAGE_3}) == len(STAGE_3), "Duplicate scenario IDs"
assert all(s["scenario_id"].startswith("RW-S3-") for s in STAGE_3), "Bad ID prefix"
