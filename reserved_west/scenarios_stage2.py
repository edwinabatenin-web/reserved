"""
Reserved West — Stage 2 Scenario Catalogue

Representative and Boundary Assurance (~150 scenarios)

Groups
------
REP  Representative user profiles                  RW-S2-001 – RW-S2-015
THR  Material threshold boundaries (3 pts each)   RW-S2-016 – RW-S2-045
SL   Student loan 2025/26 (all 5 plans, 3 pts)   RW-S2-046 – RW-S2-060
SL2  Student loan 2026/27 (all 5 plans, 3 pts)   RW-S2-061 – RW-S2-075
PEN  Pension Relief at Source                      RW-S2-076 – RW-S2-090
CGT  Capital Gains Tax                             RW-S2-091 – RW-S2-115
SEQ  Sequential journey (multi-invoice)            RW-S2-116 – RW-S2-135
EDG  Edge cases                                    RW-S2-136 – RW-S2-150

Threshold abbreviations
-----------------------
PA   = £12,570  Personal Allowance
BRL  = £50,270  Basic Rate Limit
ART  = £125,140 Additional Rate Threshold
TPS  = £100,000 PA Taper Start (ANI)
TPM  = £112,570 PA Taper Midpoint (ANI; PA halved to £6,285)
TPZ  = £125,140 PA Taper Zero (ANI; PA → £0; coincides with ART)
LPL  = £12,570  NI Lower Profits Limit
UPL  = £50,270  NI Upper Profits Limit

Student loan thresholds
-----------------------
            2025/26    2026/27
Plan 1      £24,990    £26,900
Plan 2      £28,470    £29,385
Plan 4      £32,745    £33,795
Plan 5      £25,000    £25,000 (fixed)
PGL         £21,000    £21,000 (fixed)

ID assignment is permanent.  Do not re-use or renumber IDs.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _it(sid, title, desc, groups, salary, ytd, pension, plans, invoice, year="2026/27", **kw):
    return {
        "scenario_id":   sid,
        "title":         title,
        "description":   desc,
        "groups":        ["stage2"] + groups,
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


def _cgt(sid, title, desc, groups, disposals, tib, bf=0, paid=0, year="2026/27"):
    return {
        "scenario_id":   sid,
        "title":         title,
        "description":   desc,
        "groups":        ["stage2"] + groups,
        "envelope":      "cgt",
        "scenario_type": "cgt",
        "inputs": {
            "tax_year":                      year,
            "disposals":                     disposals,
            "taxable_income_before_gains":   tib,
            "brought_forward_losses":        bf,
            "tax_already_paid":              paid,
        },
    }


def _d(asset_type, desc, proceeds, cost, date="2026-09-01"):
    return {
        "asset_type":    asset_type,
        "description":   desc,
        "disposal_date": date,
        "proceeds":      proceeds,
        "allowable_cost": cost,
    }


# ── GROUP REP: Representative user profiles ───────────────────────────────────
# 15 scenarios — RW-S2-001 to RW-S2-015

REP = [

    _it("RW-S2-001", "Junior sole trader — first invoice year",
        "Pure freelancer, no prior income this year, single £8k invoice. "
        "All income below PA; no IT, no NI, no SL.",
        ["rep"],
        salary=0, ytd=0, pension=0, plans=[], invoice=8000,
    ),

    _it("RW-S2-002", "Junior sole trader — invoice crosses PA and NI LPL",
        "Pure freelancer, prior YTD of £8k. £6k invoice takes total to £14k. "
        "Crosses PA (£12,570): some IT at 20%. NI: 6%×(14k−12570)=85.80.",
        ["rep"],
        salary=0, ytd=8000, pension=0, plans=[], invoice=6000,
    ),

    _it("RW-S2-003", "Mid-career freelancer — basic rate, Plan 2",
        "£35k employment + £8k YTD + £10k invoice → £53k total. "
        "Crosses BRL slightly; Plan 2 repayment applies.",
        ["rep"],
        salary=35000, ytd=8000, pension=0, plans=[2], invoice=10000,
    ),

    _it("RW-S2-004", "Senior freelancer — higher rate band, no loans",
        "£60k employment + £20k YTD + £10k invoice → £90k. "
        "Entire invoice at 40% IT. NI: 2%×10k=£200.",
        ["rep"],
        salary=60000, ytd=20000, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S2-005", "High earner below PA taper — £95k YTD total",
        "£80k salary + £5k YTD + £10k invoice → ANI £95k. "
        "Just below PA taper; full PA applies (IT at 40%).",
        ["rep"],
        salary=80000, ytd=5000, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S2-006", "PA taper zone — invoice enters taper (EL-001 family)",
        "£90k salary + £8k YTD + £5k invoice → ANI £103k. "
        "Invoice causes entry into PA taper. Tests EL-001 regression zone.",
        ["rep", "el001_family"],
        salary=90000, ytd=8000, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-007", "PA taper zone — invoice fully within taper (EL-001 family)",
        "£0 salary + £105k YTD + £10k invoice → ANI £115k. "
        "Start and end both within taper (ANI 105k→115k). EL-001 regression zone.",
        ["rep", "el001_family"],
        salary=0, ytd=105000, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S2-008", "Six-figure earner — invoice crosses PA elimination (EL-001 family)",
        "£120k total YTD + £8k invoice → ANI £128k, crossing £125,140. "
        "PA goes to zero during invoice; 45% above ART. EL-001 regression zone.",
        ["rep", "el001_family"],
        salary=0, ytd=120000, pension=0, plans=[], invoice=8000,
    ),

    _it("RW-S2-009", "Additional rate payer — invoice fully at 45%",
        "£130k salary + £20k YTD + £5k invoice → ANI £155k. "
        "PA is zero; entire invoice taxed at 45%.",
        ["rep"],
        salary=130000, ytd=20000, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-010", "Pension saver — RaS extends BRL, saves higher-rate IT",
        "£50k salary + £5k pension + £5k invoice → ANI 50k. "
        "eBRL = 50270+5000 = 55270, so more invoice remains at 20% not 40%.",
        ["rep", "pension"],
        salary=50000, ytd=0, pension=5000, plans=[], invoice=5000,
    ),

    _it("RW-S2-011", "Graduate — Plan 2 + Postgraduate, dual repayment",
        "£40k salary + £5k YTD + £10k invoice → £55k. "
        "Plan 2 repayment on £55k−£29,385=£25,615 at 9%=£2,305.35. "
        "PGL on £55k−£21k=£34k at 6%=£2,040. Dual repayment confirmed.",
        ["rep", "student_loan"],
        salary=40000, ytd=5000, pension=0, plans=[2, "postgraduate"], invoice=10000,
    ),

    _it("RW-S2-012", "Very high earner — invoice at top marginal rate",
        "£200k total YTD + £20k invoice → ANI £220k. "
        "No PA; no SL; no pension. Pure 45% marginal.",
        ["rep"],
        salary=0, ytd=200000, pension=0, plans=[], invoice=20000,
    ),

    _it("RW-S2-013", "Gabriel canonical 2026/27",
        "Primary benchmark persona: £40k salary, £15k YTD, £5k pension RaS, "
        "£10k invoice, Plan 2, 2026/27. Expected: IT £3946, NI £600, SL £900, total £5446.",
        ["rep", "canonical"],
        salary=40000, ytd=15000, pension=5000, plans=[2], invoice=10000,
    ),

    _it("RW-S2-014", "Gabriel canonical 2025/26",
        "Same as RW-S2-013 but 2025/26. Plan 2 threshold £28,470 vs £29,385. "
        "Same total because income (£55k→£65k) already well above both thresholds. "
        "Expected: IT £3946, NI £600, SL £900, total £5446.",
        ["rep", "canonical"],
        salary=40000, ytd=15000, pension=5000, plans=[2], invoice=10000,
        year="2025/26",
    ),

    _it("RW-S2-015", "Sole trader — all four bands in one year (large invoice)",
        "Pure freelancer. £0 prior income. £130k invoice traverses 0%, 20%, 40%, 45% bands.",
        ["rep"],
        salary=0, ytd=0, pension=0, plans=[], invoice=130000,
    ),
]

# ── GROUP THR: Threshold boundaries (3 points × 10 thresholds) ───────────────
# 30 scenarios — RW-S2-016 to RW-S2-045

THR = [

    # ── PA: Personal Allowance (£12,570) ─────────────────────────────────────

    _it("RW-S2-016", "PA boundary — invoice ends below PA",
        "YTD=10,000 + invoice=2,000 → end=12,000. "
        "End income below PA £12,570. IT=£0.",
        ["thr", "thr_pa"],
        salary=0, ytd=10000, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-017", "PA boundary — invoice ends exactly at PA",
        "YTD=10,570 + invoice=2,000 → end=12,570 = PA. "
        "End income exactly equals PA. IT=£0.",
        ["thr", "thr_pa"],
        salary=0, ytd=10570, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-018", "PA boundary — invoice crosses PA",
        "YTD=11,570 + invoice=2,000 → end=13,570. "
        "Crosses PA: 20%×(13,570−12,570)=20%×1,000=£200.",
        ["thr", "thr_pa"],
        salary=0, ytd=11570, pension=0, plans=[], invoice=2000,
    ),

    # ── BRL: Basic Rate Limit (£50,270) ──────────────────────────────────────

    _it("RW-S2-019", "BRL boundary — invoice ends below BRL",
        "YTD=47,770 + invoice=2,000 → end=49,770. "
        "Below BRL; entire invoice at 20%. IT=20%×2,000=£400.",
        ["thr", "thr_brl"],
        salary=0, ytd=47770, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-020", "BRL boundary — invoice ends exactly at BRL",
        "YTD=48,270 + invoice=2,000 → end=50,270. "
        "Exactly at BRL; last £2,000 all at 20%. IT=20%×2,000=£400.",
        ["thr", "thr_brl"],
        salary=0, ytd=48270, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-021", "BRL boundary — invoice crosses BRL",
        "YTD=49,270 + invoice=2,000 → end=51,270. "
        "Crosses BRL: 20%×(50,270−49,270) + 40%×(51,270−50,270) = 20%×1,000 + 40%×1,000 = £600.",
        ["thr", "thr_brl"],
        salary=0, ytd=49270, pension=0, plans=[], invoice=2000,
    ),

    # ── ART: Additional Rate Threshold (£125,140) ─────────────────────────────

    _it("RW-S2-022", "ART boundary — invoice ends just below ART",
        "ANI YTD=122,640 + invoice=2,000 → end=124,640. "
        "Below ART; invoice in 40% band (PA near zero in taper). EL-001 family.",
        ["thr", "thr_art", "el001_family"],
        salary=0, ytd=122640, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-023", "ART boundary — invoice ends exactly at ART",
        "ANI YTD=123,140 + invoice=2,000 → end=125,140 = ART. "
        "Exactly at ART; last £2,000 at 40% (PA fully eliminated at this point). EL-001 family.",
        ["thr", "thr_art", "el001_family"],
        salary=0, ytd=123140, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-024", "ART boundary — invoice crosses ART",
        "ANI YTD=124,140 + invoice=2,000 → end=126,140. "
        "Crosses ART: higher-rate on portion below ART, 45% above. EL-001 family.",
        ["thr", "thr_art", "el001_family"],
        salary=0, ytd=124140, pension=0, plans=[], invoice=2000,
    ),

    # ── PA taper start (ANI £100,000) ─────────────────────────────────────────

    _it("RW-S2-025", "Taper start — invoice ends below taper (ANI < £100k)",
        "ANI YTD=97,000 + invoice=2,000 → ANI end=99,000. "
        "Below PA taper; full PA applies. IT at 40% on invoice.",
        ["thr", "thr_tps"],
        salary=0, ytd=97000, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-026", "Taper start — invoice ends exactly at taper start (ANI = £100k)",
        "ANI YTD=98,000 + invoice=2,000 → ANI end=100,000. "
        "Exactly at taper start; PA not yet reduced. IT at 40%.",
        ["thr", "thr_tps"],
        salary=0, ytd=98000, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-027", "Taper start — invoice enters taper zone (EL-001 family)",
        "ANI YTD=99,000 + invoice=2,000 → ANI end=101,000. "
        "Crosses taper start; PA begins reducing. EL-001 regression zone.",
        ["thr", "thr_tps", "el001_family"],
        salary=0, ytd=99000, pension=0, plans=[], invoice=2000,
    ),

    # ── PA taper midpoint (ANI £112,570; PA = £6,285) ─────────────────────────

    _it("RW-S2-028", "Taper midpoint — invoice ends below midpoint",
        "ANI YTD=110,000 + invoice=2,000 → ANI=112,000. "
        "Entirely within taper zone; PA reducing throughout. EL-001 family.",
        ["thr", "thr_tpm", "el001_family"],
        salary=0, ytd=110000, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-029", "Taper midpoint — invoice ends at midpoint (PA = £6,285)",
        "ANI YTD=110,570 + invoice=2,000 → ANI=112,570. "
        "End is exactly at PA taper midpoint; PA = 12,570−6,285 = £6,285. EL-001 family.",
        ["thr", "thr_tpm", "el001_family"],
        salary=0, ytd=110570, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-030", "Taper midpoint — invoice crosses midpoint",
        "ANI YTD=111,570 + invoice=2,000 → ANI=113,570. "
        "Crosses midpoint; PA varies from £6,785 at start to £5,785 at end. EL-001 family.",
        ["thr", "thr_tpm", "el001_family"],
        salary=0, ytd=111570, pension=0, plans=[], invoice=2000,
    ),

    # ── PA taper zero / ART (ANI £125,140) ───────────────────────────────────

    _it("RW-S2-031", "PA zero boundary — invoice ends just below PA elimination",
        "ANI YTD=122,140 + invoice=2,000 → ANI=124,140. "
        "PA = max(0, 12,570−(124,140−100,000)/2) = 12,570−12,070 = £500. "
        "End still has residual PA. EL-001 family.",
        ["thr", "thr_tpz", "el001_family"],
        salary=0, ytd=122140, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-032", "PA zero boundary — invoice ends exactly at PA elimination",
        "ANI YTD=123,140 + invoice=2,000 → ANI=125,140. "
        "PA exactly zero at end; ART exactly met. EL-001 family.",
        ["thr", "thr_tpz", "el001_family"],
        salary=0, ytd=123140, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-033", "PA zero boundary — invoice crosses PA elimination into 45%",
        "ANI YTD=124,140 + invoice=2,000 → ANI=126,140. "
        "Invoice crosses both PA elimination and ART; 45% applies on excess. EL-001 family.",
        ["thr", "thr_tpz", "el001_family"],
        salary=0, ytd=124140, pension=0, plans=[], invoice=2000,
    ),

    # ── NI LPL (£12,570) ─────────────────────────────────────────────────────

    _it("RW-S2-034", "NI LPL — freelance profit ends below LPL",
        "YTD=10,000 + invoice=2,000 → total_profit=12,000. "
        "Below NI LPL £12,570; NI=£0.",
        ["thr", "thr_lpl"],
        salary=0, ytd=10000, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-035", "NI LPL — freelance profit ends exactly at LPL",
        "YTD=10,570 + invoice=2,000 → total_profit=12,570. "
        "Exactly at NI LPL; NI=£0 (LPL is the lower boundary, not chargeable).",
        ["thr", "thr_lpl"],
        salary=0, ytd=10570, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-036", "NI LPL — freelance profit crosses LPL",
        "YTD=11,570 + invoice=2,000 → total_profit=13,570. "
        "Crosses NI LPL: 6%×(13,570−12,570)=6%×1,000=£60.",
        ["thr", "thr_lpl"],
        salary=0, ytd=11570, pension=0, plans=[], invoice=2000,
    ),

    # ── NI UPL (£50,270) ─────────────────────────────────────────────────────

    _it("RW-S2-037", "NI UPL — freelance profit ends below UPL",
        "YTD=47,770 + invoice=2,000 → total_profit=49,770. "
        "Below NI UPL; NI=6%×(49,770−12,570)=6%×37,200=£2,232 cumulative → incremental.",
        ["thr", "thr_upl"],
        salary=0, ytd=47770, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-038", "NI UPL — freelance profit ends exactly at UPL",
        "YTD=48,270 + invoice=2,000 → total_profit=50,270. "
        "Exactly at NI UPL; last £2,000 at 6%.",
        ["thr", "thr_upl"],
        salary=0, ytd=48270, pension=0, plans=[], invoice=2000,
    ),

    _it("RW-S2-039", "NI UPL — freelance profit crosses UPL",
        "YTD=49,270 + invoice=2,000 → total_profit=51,270. "
        "Crosses UPL: 6%×1,000 + 2%×1,000 = £60+£20 = £80.",
        ["thr", "thr_upl"],
        salary=0, ytd=49270, pension=0, plans=[], invoice=2000,
    ),

    # ── Salary + freelance combined threshold (employment not taxed here) ─────

    _it("RW-S2-040", "Combined — salary near BRL, freelance crosses to higher rate",
        "£48k salary + £0 YTD + £5k invoice → £53k total. "
        "Invoice straddles BRL: £2,270 at 20%, £2,730 at 40%. "
        "NI: £0 (no freelance profit below LPL? No — YTD=0, profit=5k. 6%×(5k-12570)... hmm negative). "
        "Wait: total freelance = invoice=5000 which is below NI LPL=12570. NI=0. "
        "IT crosses BRL because salary already at £48k.",
        ["thr", "thr_brl", "combined"],
        salary=48000, ytd=0, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-041", "Combined — salary at BRL, entire invoice at higher rate",
        "£50,270 salary + £0 YTD + £5k invoice → £55,270. "
        "Salary exactly at BRL; entire £5k invoice at 40%.",
        ["thr", "thr_brl", "combined"],
        salary=50270, ytd=0, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-042", "Combined — salary in PA taper zone, freelance extends (EL-001 family)",
        "£95k salary + £3k YTD + £5k invoice → ANI £103k (no pension). "
        "Invoice enters PA taper zone. EL-001 regression zone.",
        ["thr", "thr_tps", "el001_family", "combined"],
        salary=95000, ytd=3000, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-043", "Combined — salary + pension keeps ANI below taper",
        "£95k salary + £0 YTD + £8k pension + £5k invoice → ANI=92k. "
        "Pension lowers ANI below £100k; full PA applies throughout.",
        ["thr", "thr_tps", "pension", "combined"],
        salary=95000, ytd=0, pension=8000, plans=[], invoice=5000,
    ),

    _it("RW-S2-044", "Combined — invoice at ART, pension extends eBRL past ART (cap test)",
        "£120k salary + £10k pension + £5k invoice → ANI=115k. "
        "eBRL = min(50270+10000, 125140) = min(60270, 125140) = 60270. "
        "Invoice at 40% (between eBRL and ART). EL-001 family.",
        ["thr", "thr_art", "pension", "el001_family", "combined"],
        salary=120000, ytd=0, pension=10000, plans=[], invoice=5000,
    ),

    _it("RW-S2-045", "Combined — very large pension caps eBRL at ART",
        "£60k salary + £80k pension → eBRL = min(50270+80000, 125140) = 125140 (capped). "
        "Engine must not produce eBRL > ART. Invoice=£5k at ART boundary.",
        ["thr", "pension", "combined"],
        salary=60000, ytd=0, pension=80000, plans=[], invoice=5000,
    ),
]

# ── GROUP SL: Student loan 2025/26 (5 plans × 3 points) ──────────────────────
# 15 scenarios — RW-S2-046 to RW-S2-060

SL_2526 = [

    # Plan 1 threshold 2025/26 = £24,990
    _it("RW-S2-046", "SL Plan 1 2025/26 — income ends below threshold",
        "YTD=22,000 + invoice=2,000 → end=24,000. Below Plan 1 threshold £24,990. SL=0.",
        ["sl", "sl_plan1", "sl_2526"],
        salary=0, ytd=22000, pension=0, plans=[1], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-047", "SL Plan 1 2025/26 — income crosses threshold",
        "YTD=23,990 + invoice=2,000 → end=25,990. "
        "Crosses £24,990: 9%×(25,990−24,990)=9%×1,000=£90.",
        ["sl", "sl_plan1", "sl_2526"],
        salary=0, ytd=23990, pension=0, plans=[1], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-048", "SL Plan 1 2025/26 — income starts above threshold",
        "YTD=25,990 + invoice=2,000 → end=27,990. "
        "Start and end both above £24,990: 9%×2,000=£180.",
        ["sl", "sl_plan1", "sl_2526"],
        salary=0, ytd=25990, pension=0, plans=[1], invoice=2000, year="2025/26",
    ),

    # Plan 2 threshold 2025/26 = £28,470
    _it("RW-S2-049", "SL Plan 2 2025/26 — income ends below threshold",
        "YTD=25,000 + invoice=2,000 → end=27,000. Below Plan 2 threshold £28,470. SL=0.",
        ["sl", "sl_plan2", "sl_2526"],
        salary=0, ytd=25000, pension=0, plans=[2], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-050", "SL Plan 2 2025/26 — income crosses threshold",
        "YTD=27,470 + invoice=2,000 → end=29,470. "
        "Crosses £28,470: 9%×(29,470−28,470)=9%×1,000=£90.",
        ["sl", "sl_plan2", "sl_2526"],
        salary=0, ytd=27470, pension=0, plans=[2], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-051", "SL Plan 2 2025/26 — income starts above threshold",
        "YTD=29,470 + invoice=2,000 → end=31,470. "
        "Start and end both above £28,470: 9%×2,000=£180.",
        ["sl", "sl_plan2", "sl_2526"],
        salary=0, ytd=29470, pension=0, plans=[2], invoice=2000, year="2025/26",
    ),

    # Plan 4 threshold 2025/26 = £32,745
    _it("RW-S2-052", "SL Plan 4 2025/26 — income ends below threshold",
        "YTD=30,000 + invoice=2,000 → end=32,000. Below Plan 4 threshold £32,745. SL=0.",
        ["sl", "sl_plan4", "sl_2526"],
        salary=0, ytd=30000, pension=0, plans=[4], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-053", "SL Plan 4 2025/26 — income crosses threshold",
        "YTD=31,745 + invoice=2,000 → end=33,745. "
        "Crosses £32,745: 9%×(33,745−32,745)=9%×1,000=£90.",
        ["sl", "sl_plan4", "sl_2526"],
        salary=0, ytd=31745, pension=0, plans=[4], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-054", "SL Plan 4 2025/26 — income starts above threshold",
        "YTD=33,745 + invoice=2,000 → end=35,745. "
        "Start and end both above £32,745: 9%×2,000=£180.",
        ["sl", "sl_plan4", "sl_2526"],
        salary=0, ytd=33745, pension=0, plans=[4], invoice=2000, year="2025/26",
    ),

    # Plan 5 threshold 2025/26 = £25,000 (fixed)
    _it("RW-S2-055", "SL Plan 5 2025/26 — income ends below threshold",
        "YTD=22,000 + invoice=2,000 → end=24,000. Below Plan 5 threshold £25,000. SL=0.",
        ["sl", "sl_plan5", "sl_2526"],
        salary=0, ytd=22000, pension=0, plans=[5], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-056", "SL Plan 5 2025/26 — income crosses threshold",
        "YTD=24,000 + invoice=2,000 → end=26,000. "
        "Crosses £25,000: 9%×(26,000−25,000)=9%×1,000=£90.",
        ["sl", "sl_plan5", "sl_2526"],
        salary=0, ytd=24000, pension=0, plans=[5], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-057", "SL Plan 5 2025/26 — income starts above threshold",
        "YTD=26,000 + invoice=2,000 → end=28,000. "
        "Start and end both above £25,000: 9%×2,000=£180.",
        ["sl", "sl_plan5", "sl_2526"],
        salary=0, ytd=26000, pension=0, plans=[5], invoice=2000, year="2025/26",
    ),

    # Postgraduate Loan threshold 2025/26 = £21,000 (fixed)
    _it("RW-S2-058", "SL Postgraduate 2025/26 — income ends below threshold",
        "YTD=18,000 + invoice=2,000 → end=20,000. Below PGL threshold £21,000. SL=0.",
        ["sl", "sl_pgl", "sl_2526"],
        salary=0, ytd=18000, pension=0, plans=["postgraduate"], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-059", "SL Postgraduate 2025/26 — income crosses threshold",
        "YTD=20,000 + invoice=2,000 → end=22,000. "
        "Crosses £21,000: 6%×(22,000−21,000)=6%×1,000=£60.",
        ["sl", "sl_pgl", "sl_2526"],
        salary=0, ytd=20000, pension=0, plans=["postgraduate"], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-060", "SL Postgraduate 2025/26 — income starts above threshold",
        "YTD=22,000 + invoice=2,000 → end=24,000. "
        "Start and end both above £21,000: 6%×2,000=£120.",
        ["sl", "sl_pgl", "sl_2526"],
        salary=0, ytd=22000, pension=0, plans=["postgraduate"], invoice=2000, year="2025/26",
    ),
]

# ── GROUP SL2: Student loan 2026/27 (5 plans × 3 points) ─────────────────────
# 15 scenarios — RW-S2-061 to RW-S2-075

SL_2627 = [

    # Plan 1 threshold 2026/27 = £26,900
    _it("RW-S2-061", "SL Plan 1 2026/27 — income ends below threshold",
        "YTD=23,900 + invoice=2,000 → end=25,900. Below Plan 1 threshold £26,900. SL=0.",
        ["sl", "sl_plan1", "sl_2627"],
        salary=0, ytd=23900, pension=0, plans=[1], invoice=2000,
    ),

    _it("RW-S2-062", "SL Plan 1 2026/27 — income crosses threshold",
        "YTD=25,900 + invoice=2,000 → end=27,900. "
        "Crosses £26,900: 9%×(27,900−26,900)=9%×1,000=£90.",
        ["sl", "sl_plan1", "sl_2627"],
        salary=0, ytd=25900, pension=0, plans=[1], invoice=2000,
    ),

    _it("RW-S2-063", "SL Plan 1 2026/27 — income starts above threshold",
        "YTD=27,900 + invoice=2,000 → end=29,900. "
        "Both above £26,900: 9%×2,000=£180.",
        ["sl", "sl_plan1", "sl_2627"],
        salary=0, ytd=27900, pension=0, plans=[1], invoice=2000,
    ),

    # Plan 2 threshold 2026/27 = £29,385
    _it("RW-S2-064", "SL Plan 2 2026/27 — income ends below threshold",
        "YTD=26,385 + invoice=2,000 → end=28,385. Below Plan 2 threshold £29,385. SL=0.",
        ["sl", "sl_plan2", "sl_2627"],
        salary=0, ytd=26385, pension=0, plans=[2], invoice=2000,
    ),

    _it("RW-S2-065", "SL Plan 2 2026/27 — income crosses threshold",
        "YTD=28,385 + invoice=2,000 → end=30,385. "
        "Crosses £29,385: 9%×(30,385−29,385)=9%×1,000=£90.",
        ["sl", "sl_plan2", "sl_2627"],
        salary=0, ytd=28385, pension=0, plans=[2], invoice=2000,
    ),

    _it("RW-S2-066", "SL Plan 2 2026/27 — income starts above threshold",
        "YTD=30,385 + invoice=2,000 → end=32,385. "
        "Both above £29,385: 9%×2,000=£180.",
        ["sl", "sl_plan2", "sl_2627"],
        salary=0, ytd=30385, pension=0, plans=[2], invoice=2000,
    ),

    # Plan 4 threshold 2026/27 = £33,795
    _it("RW-S2-067", "SL Plan 4 2026/27 — income ends below threshold",
        "YTD=30,795 + invoice=2,000 → end=32,795. Below Plan 4 threshold £33,795. SL=0.",
        ["sl", "sl_plan4", "sl_2627"],
        salary=0, ytd=30795, pension=0, plans=[4], invoice=2000,
    ),

    _it("RW-S2-068", "SL Plan 4 2026/27 — income crosses threshold",
        "YTD=32,795 + invoice=2,000 → end=34,795. "
        "Crosses £33,795: 9%×(34,795−33,795)=9%×1,000=£90.",
        ["sl", "sl_plan4", "sl_2627"],
        salary=0, ytd=32795, pension=0, plans=[4], invoice=2000,
    ),

    _it("RW-S2-069", "SL Plan 4 2026/27 — income starts above threshold",
        "YTD=34,795 + invoice=2,000 → end=36,795. "
        "Both above £33,795: 9%×2,000=£180.",
        ["sl", "sl_plan4", "sl_2627"],
        salary=0, ytd=34795, pension=0, plans=[4], invoice=2000,
    ),

    # Plan 5 threshold 2026/27 = £25,000 (fixed; same as 2025/26)
    _it("RW-S2-070", "SL Plan 5 2026/27 — income ends below threshold",
        "YTD=22,000 + invoice=2,000 → end=24,000. Below Plan 5 threshold £25,000. SL=0.",
        ["sl", "sl_plan5", "sl_2627"],
        salary=0, ytd=22000, pension=0, plans=[5], invoice=2000,
    ),

    _it("RW-S2-071", "SL Plan 5 2026/27 — income crosses threshold",
        "YTD=24,000 + invoice=2,000 → end=26,000. "
        "Crosses £25,000: 9%×1,000=£90.",
        ["sl", "sl_plan5", "sl_2627"],
        salary=0, ytd=24000, pension=0, plans=[5], invoice=2000,
    ),

    _it("RW-S2-072", "SL Plan 5 2026/27 — income starts above threshold",
        "YTD=26,000 + invoice=2,000 → end=28,000. "
        "Both above £25,000: 9%×2,000=£180.",
        ["sl", "sl_plan5", "sl_2627"],
        salary=0, ytd=26000, pension=0, plans=[5], invoice=2000,
    ),

    # Postgraduate Loan threshold 2026/27 = £21,000 (fixed)
    _it("RW-S2-073", "SL Postgraduate 2026/27 — income ends below threshold",
        "YTD=18,000 + invoice=2,000 → end=20,000. Below PGL threshold £21,000. SL=0.",
        ["sl", "sl_pgl", "sl_2627"],
        salary=0, ytd=18000, pension=0, plans=["postgraduate"], invoice=2000,
    ),

    _it("RW-S2-074", "SL Postgraduate 2026/27 — income crosses threshold",
        "YTD=20,000 + invoice=2,000 → end=22,000. "
        "Crosses £21,000: 6%×1,000=£60.",
        ["sl", "sl_pgl", "sl_2627"],
        salary=0, ytd=20000, pension=0, plans=["postgraduate"], invoice=2000,
    ),

    _it("RW-S2-075", "SL Postgraduate 2026/27 — income starts above threshold",
        "YTD=22,000 + invoice=2,000 → end=24,000. "
        "Both above £21,000: 6%×2,000=£120.",
        ["sl", "sl_pgl", "sl_2627"],
        salary=0, ytd=22000, pension=0, plans=["postgraduate"], invoice=2000,
    ),
]

# ── GROUP PEN: Pension Relief at Source ───────────────────────────────────────
# 15 scenarios — RW-S2-076 to RW-S2-090

PEN = [

    _it("RW-S2-076", "Pension — basic rate payer, RaS raises refund (no band extension effect)",
        "£30k salary + £5k pension + £5k invoice. "
        "All income within basic rate; no band extension effect. "
        "Pension reduces ANI; no impact on tax bands here.",
        ["pension"],
        salary=30000, ytd=0, pension=5000, plans=[], invoice=5000,
    ),

    _it("RW-S2-077", "Pension — extends BRL, saving 20% on part of invoice",
        "£45k salary + £8k pension + £8k invoice → ANI=45k. "
        "eBRL=50270+8000=58270. Invoice (£45k→£53k) straddles BRL without pension; "
        "with pension (eBRL=58270) more stays at 20%.",
        ["pension"],
        salary=45000, ytd=0, pension=8000, plans=[], invoice=8000,
    ),

    _it("RW-S2-078", "Pension — large enough to keep entire invoice at 20%",
        "£48k salary + £10k pension + £5k invoice → ANI=43k. "
        "eBRL=50270+10000=60270. Invoice ends at £53k < eBRL; all at 20%.",
        ["pension"],
        salary=48000, ytd=0, pension=10000, plans=[], invoice=5000,
    ),

    _it("RW-S2-079", "Pension — reduces ANI to just below taper start (PA preserved)",
        "£97k salary + £0 YTD + £10k pension + £8k invoice → ANI=97k+8k−10k=95k. "
        "Wait — ANI = (salary + profit) − pension. ANI = (97k+8k) − 10k = 95k < 100k. "
        "Full PA; no taper. eBRL = min(50270+10000, 125140) = 60270.",
        ["pension", "thr_tps"],
        salary=97000, ytd=0, pension=10000, plans=[], invoice=8000,
    ),

    _it("RW-S2-080", "Pension — prevents PA taper at start but invoice crosses into taper",
        "£95k salary + £8k pension + £8k invoice → ANI goes from 95k to 103k. "
        "Start ANI (95k) < 100k — PA ok. End ANI (103k) in taper. EL-001 family.",
        ["pension", "thr_tps", "el001_family"],
        salary=95000, ytd=0, pension=8000, plans=[], invoice=8000,
    ),

    _it("RW-S2-081", "Pension — eliminates PA taper effect entirely",
        "£110k salary + £15k pension + £5k invoice → ANI=110k+5k−15k=100k exactly. "
        "eBRL=50270+15000=65270. ANI=100k → PA=12570 (taper starts at 100k, not above). "
        "Invoice end ANI=100k; full PA preserved.",
        ["pension", "thr_tps"],
        salary=110000, ytd=0, pension=15000, plans=[], invoice=5000,
    ),

    _it("RW-S2-082", "Pension — large contribution with Plan 2 loan",
        "£40k salary + £10k pension + £10k invoice, Plan 2. "
        "eBRL=50270+10000=60270. ANI=40k+10k−10k=40k. "
        "SL on total income (not ANI): 9%×(50k−29385)=9%×20615=£1855.35.",
        ["pension", "student_loan"],
        salary=40000, ytd=0, pension=10000, plans=[2], invoice=10000,
    ),

    _it("RW-S2-083", "Pension — contribution exactly extends eBRL to BRL",
        "Zero pension: eBRL=50270. With pension=£5k: eBRL=55270. "
        "£50k salary + £5k pension + £5k invoice → ANI=50k. "
        "With eBRL=55270, invoice from 50k to 55k is entirely within eBRL=55270. All at 20%.",
        ["pension"],
        salary=50000, ytd=0, pension=5000, plans=[], invoice=5000,
    ),

    _it("RW-S2-084", "Pension — contribution that nearly reaches ART eBRL cap",
        "£60k salary + £60k pension + £5k invoice. "
        "eBRL = min(50270+60000, 125140) = min(110270, 125140) = 110270. "
        "Not yet capped. ANI = 65k − 60k = 5k (well below taper). ",
        ["pension"],
        salary=60000, ytd=0, pension=60000, plans=[], invoice=5000,
    ),

    _it("RW-S2-085", "Pension — exactly caps eBRL at ART",
        "£60k salary + £75k pension + £5k invoice. "
        "eBRL = min(50270+75000, 125140) = min(125270, 125140) = 125140 (capped at ART). "
        "Engine must apply ART as ceiling on eBRL.",
        ["pension"],
        salary=60000, ytd=0, pension=75000, plans=[], invoice=5000,
    ),

    _it("RW-S2-086", "Pension — zero contribution, baseline for pension comparison",
        "£45k salary + £0 pension + £8k invoice. "
        "No pension; baseline for comparison with RW-S2-077.",
        ["pension"],
        salary=45000, ytd=0, pension=0, plans=[], invoice=8000,
    ),

    _it("RW-S2-087", "Pension — small contribution (£1,000) basic rate saver",
        "£40k salary + £1k pension + £5k invoice. "
        "Modest pension; eBRL=51270. Some basic-rate saving vs no pension.",
        ["pension"],
        salary=40000, ytd=0, pension=1000, plans=[], invoice=5000,
    ),

    _it("RW-S2-088", "Pension — higher rate saver, large contribution",
        "£80k salary + £20k pension + £10k invoice. "
        "ANI = 80k+10k−20k = 70k. eBRL=70270. Invoice from 80k to 90k. "
        "Both start and end above eBRL; 40% on full invoice.",
        ["pension"],
        salary=80000, ytd=0, pension=20000, plans=[], invoice=10000,
    ),

    _it("RW-S2-089", "Pension — PGL holder with large pension",
        "£25k salary + £3k pension + £5k invoice, Postgraduate Loan. "
        "ANI=27k. eBRL=53270. PGL: 6%×(30k−21k)=6%×9k=£540.",
        ["pension", "student_loan"],
        salary=25000, ytd=0, pension=3000, plans=["postgraduate"], invoice=5000,
    ),

    _it("RW-S2-090", "Pension — all plans + pension combined",
        "£30k salary + £5k pension + £5k invoice. Plans 2 and PGL. "
        "ANI=30k. eBRL=55270. SL Plan 2: 9%×(35k−29385)=£505.35. "
        "PGL: 6%×(35k−21k)=6%×14k=£840.",
        ["pension", "student_loan"],
        salary=30000, ytd=0, pension=5000, plans=[2, "postgraduate"], invoice=5000,
    ),
]

# ── GROUP CGT: Capital Gains Tax ──────────────────────────────────────────────
# 25 scenarios — RW-S2-091 to RW-S2-115

CGT = [

    _cgt("RW-S2-091", "CGT — gain exactly equals AEA (£3,000)",
         "Single disposal. Gain = £3,000 = AEA. Taxable gains = £0. CGT = £0.",
         ["cgt"],
         disposals=[_d("shares", "Gain = AEA", 13000, 10000)],
         tib=30000,
    ),

    _cgt("RW-S2-092", "CGT — gain just above AEA",
         "Single disposal. Gain = £3,100. Taxable gains = £100. "
         "tib=30,000 → in basic rate band. CGT = 18%×100 = £18.",
         ["cgt"],
         disposals=[_d("shares", "Gain = AEA+100", 13100, 10000)],
         tib=30000,
    ),

    _cgt("RW-S2-093", "CGT — gain just below AEA",
         "Single disposal. Gain = £2,900 < AEA. Taxable gains = £0. CGT = £0.",
         ["cgt"],
         disposals=[_d("shares", "Gain below AEA", 12900, 10000)],
         tib=30000,
    ),

    _cgt("RW-S2-094", "CGT — entire gain at basic rate (18%)",
         "Taxable income £20,000. Remaining BRL = 50,270−20,000 = 30,270. "
         "Gain = £5,000 (after AEA). All within basic rate band.",
         ["cgt"],
         disposals=[_d("shares", "Basic rate gain", 18000, 10000)],
         tib=20000,
    ),

    _cgt("RW-S2-095", "CGT — entire gain at higher rate (24%)",
         "Taxable income = £55,000 (above BRL). "
         "Gain = £5,000 (after AEA). No basic-rate capacity. CGT = 24%×5,000 = £1,200.",
         ["cgt"],
         disposals=[_d("shares", "Higher rate gain", 18000, 10000)],
         tib=55000,
    ),

    _cgt("RW-S2-096", "CGT — split basic/higher rate",
         "Taxable income = £47,000. Basic remaining = 50,270−47,000 = 3,270. "
         "Taxable gains = £6,000. Basic slice: 3,270@18%. Higher: 2,730@24%.",
         ["cgt"],
         disposals=[_d("shares", "Split rate", 19000, 10000)],
         tib=47000,
    ),

    _cgt("RW-S2-097", "CGT — gain exactly fills remaining BRL",
         "tib=47,270. Remaining BRL = 50,270−47,270 = 3,000. Gain = £6,000 (after AEA = £3,000). "
         "Taxable gains = £3,000 = exactly fills BRL. All at 18%. CGT = 18%×3,000 = £540.",
         ["cgt"],
         disposals=[_d("shares", "Fills BRL exactly", 16000, 10000)],
         tib=47270,
    ),

    _cgt("RW-S2-098", "CGT — brought-forward losses reduce taxable gains",
         "Gain = £8,000. BF losses = £3,000. "
         "Net gains = 8,000. After BF losses: 8,000−3,000 = 5,000. After AEA: 5,000−3,000 = 2,000. "
         "CGT = 18%×2,000 = £360.",
         ["cgt"],
         disposals=[_d("shares", "BF loss reduction", 18000, 10000)],
         tib=20000, bf=3000,
    ),

    _cgt("RW-S2-099", "CGT — brought-forward losses eliminate taxable gain",
         "Gain = £5,000. BF losses = £5,000. "
         "Net gains after BF = 0. AEA unused. CGT = £0.",
         ["cgt"],
         disposals=[_d("shares", "BF losses eliminate gain", 15000, 10000)],
         tib=20000, bf=5000,
    ),

    _cgt("RW-S2-100", "CGT — two disposals, combined gain",
         "Two disposals: gain £4,000 + gain £3,000 = £7,000 total. "
         "After AEA £3,000: taxable = £4,000. tib=20,000. CGT=18%×4,000=£720.",
         ["cgt"],
         disposals=[
             _d("shares", "Disposal A", 14000, 10000),
             _d("shares", "Disposal B", 13000, 10000),
         ],
         tib=20000,
    ),

    _cgt("RW-S2-101", "CGT — three disposals, one at a loss (offsets gains)",
         "Disposal A: gain £5,000. Disposal B: gain £3,000. Disposal C: loss £2,000. "
         "Net = 5,000+3,000−2,000 = 6,000. After AEA: 3,000. CGT at 18%=£540.",
         ["cgt"],
         disposals=[
             _d("shares", "Gain A",  15000, 10000),
             _d("shares", "Gain B",  13000, 10000),
             _d("shares", "Loss C",   8000, 10000),
         ],
         tib=20000,
    ),

    _cgt("RW-S2-102", "CGT — all disposals result in a loss (no CGT)",
         "Disposal: proceeds £8,000, cost £10,000. Net loss = −£2,000. "
         "No taxable gain; CGT = £0.",
         ["cgt"],
         disposals=[_d("shares", "Capital loss", 8000, 10000)],
         tib=30000,
    ),

    _cgt("RW-S2-103", "CGT — crypto disposal, gain within basic rate",
         "Crypto asset disposal. Gain = £5,000. After AEA = £2,000. "
         "tib=£25,000 → basic rate. CGT=18%×2,000=£360.",
         ["cgt"],
         disposals=[_d("crypto", "Crypto disposal", 15000, 10000)],
         tib=25000,
    ),

    _cgt("RW-S2-104", "CGT — 2025/26 tax year (rates same; AEA same)",
         "Same as RW-S2-094 but in 2025/26. Rates and AEA unchanged. "
         "Expected: same CGT £360.",
         ["cgt"],
         disposals=[_d("shares", "2025/26 basic rate", 18000, 10000)],
         tib=20000, year="2025/26",
    ),

    _cgt("RW-S2-105", "CGT — high income, entire gain at higher rate, 2025/26",
         "tib=£60,000 (above BRL). Gain after AEA = £5,000. CGT=24%×5,000=£1,200.",
         ["cgt"],
         disposals=[_d("shares", "Higher rate 2025/26", 18000, 10000)],
         tib=60000, year="2025/26",
    ),

    _cgt("RW-S2-106", "CGT — income below PA; basic rate applied from £0",
         "tib=£0 (income below PA; no taxable income). "
         "BRL capacity = 50,270. Gain after AEA = £5,000. All at 18%=£900.",
         ["cgt"],
         disposals=[_d("shares", "Below PA income", 18000, 10000)],
         tib=0,
    ),

    _cgt("RW-S2-107", "CGT — large gain spanning basic and higher entirely",
         "tib=£40,000. Remaining BRL=10,270. Gain=£20,000. After AEA=£17,000. "
         "Basic: 10,270@18%=£1,848.60. Higher: 6,730@24%=£1,615.20. Total=£3,463.80.",
         ["cgt"],
         disposals=[_d("shares", "Large spanning gain", 30000, 10000)],
         tib=40000,
    ),

    _cgt("RW-S2-108", "CGT — income exactly at BRL; entire gain at higher rate",
         "tib=£50,270 (exactly at BRL). Remaining BRL=0. "
         "All taxable gains at 24%. Gain=£5,000 after AEA. CGT=24%×5,000=£1,200.",
         ["cgt"],
         disposals=[_d("shares", "tib at BRL", 18000, 10000)],
         tib=50270,
    ),

    _cgt("RW-S2-109", "CGT — partial tax already paid reduces outstanding",
         "Gain after AEA = £5,000. CGT at 18% = £900. Tax already paid = £200. "
         "Outstanding reserve = £900−£200 = £700.",
         ["cgt"],
         disposals=[_d("shares", "Partial paid", 18000, 10000)],
         tib=20000, paid=200,
    ),

    _cgt("RW-S2-110", "CGT — gain exactly equals AEA in 2025/26 (AEA same)",
         "AEA is £3,000 in both years (fixed). Gain=£3,000. Taxable=£0. CGT=£0.",
         ["cgt"],
         disposals=[_d("shares", "AEA exact 2025/26", 13000, 10000)],
         tib=30000, year="2025/26",
    ),

    _cgt("RW-S2-111", "CGT — four disposals, mixed gains and losses",
         "Gains: £5,000 + £4,000 = 9,000. Losses: −£1,000 + −£2,000 = −3,000. "
         "Net = 6,000. After AEA = 3,000. tib=25,000. CGT=18%×3,000=£540.",
         ["cgt"],
         disposals=[
             _d("shares", "Gain A",  15000, 10000),
             _d("shares", "Gain B",  14000, 10000),
             _d("shares", "Loss C",   9000, 10000),
             _d("shares", "Loss D",   8000, 10000),
         ],
         tib=25000,
    ),

    _cgt("RW-S2-112", "CGT — gain split by tax year boundary effect on BRL",
         "tib=£49,000 in 2026/27. Remaining BRL=1,270. Gain after AEA=£5,000. "
         "Basic: 1,270@18%=£228.60. Higher: 3,730@24%=£895.20. Total=£1,123.80.",
         ["cgt"],
         disposals=[_d("shares", "Split near BRL", 18000, 10000)],
         tib=49000,
    ),

    _cgt("RW-S2-113", "CGT — other asset type",
         "Asset type 'other'. Gain=£5,000. After AEA=£2,000. tib=20,000. "
         "Same rates as shares: 18%×2,000=£360.",
         ["cgt"],
         disposals=[_d("other", "Other asset", 15000, 10000)],
         tib=20000,
    ),

    _cgt("RW-S2-114", "CGT — BF losses + current losses combined",
         "Disposal A: gain £4,000. Disposal B: loss £1,000. "
         "BF losses £2,000. Net = 4,000−1,000−2,000 = 1,000. After AEA: £0 (AEA>1000). "
         "Wait: AEA=3,000. After current-year losses: gain=4,000−1,000=3,000. "
         "After BF losses: 3,000−2,000=1,000. After AEA: 1,000 (AEA=3,000; use min AEA needed). "
         "Actually AEA applies after BF: max(0, 1,000−3,000) = 0. CGT=£0.",
         ["cgt"],
         disposals=[
             _d("shares", "Gain", 14000, 10000),
             _d("shares", "Loss", 9000, 10000),
         ],
         tib=25000, bf=2000,
    ),

    _cgt("RW-S2-115", "CGT — very large gain (£100,000), all at higher rate",
         "tib=£60,000. Gain=£103,000. After AEA=£100,000. "
         "No BRL capacity. CGT=24%×100,000=£24,000.",
         ["cgt"],
         disposals=[_d("shares", "Very large gain", 110000, 10000)],
         tib=60000,
    ),
]

# ── GROUP SEQ: Sequential journeys ────────────────────────────────────────────
# 20 scenarios — RW-S2-116 to RW-S2-135
# Represents a freelancer receiving multiple invoices across the year.
# Each scenario is one invoice event; YTD reflects invoices already received.

SEQ = [

    # Journey A — junior freelancer, 4 invoices, plain basic rate
    _it("RW-S2-116", "SEQ Journey A — Invoice 1 of 4 (YTD=0, below PA)",
        "Freelancer. No prior income. £5k invoice → end=5k. Below PA. IT=0, NI=0.",
        ["seq", "journey_a"],
        salary=0, ytd=0, pension=0, plans=[], invoice=5000,
    ),
    _it("RW-S2-117", "SEQ Journey A — Invoice 2 of 4 (YTD=5k, crosses PA)",
        "YTD=5k. £10k invoice → end=15k. Crosses PA (£12,570). IT=20%×2,430=£486. NI=6%×2,430=£145.80.",
        ["seq", "journey_a"],
        salary=0, ytd=5000, pension=0, plans=[], invoice=10000,
    ),
    _it("RW-S2-118", "SEQ Journey A — Invoice 3 of 4 (YTD=15k, basic rate)",
        "YTD=15k. £10k invoice → end=25k. All within basic rate. IT=20%×10k=£2,000. NI=6%×10k=£600.",
        ["seq", "journey_a"],
        salary=0, ytd=15000, pension=0, plans=[], invoice=10000,
    ),
    _it("RW-S2-119", "SEQ Journey A — Invoice 4 of 4 (YTD=25k, basic rate)",
        "YTD=25k. £10k invoice → end=35k. Basic rate. IT=£2,000. NI=£600.",
        ["seq", "journey_a"],
        salary=0, ytd=25000, pension=0, plans=[], invoice=10000,
    ),

    # Journey B — higher earner, 4 invoices, crosses BRL then ART
    _it("RW-S2-120", "SEQ Journey B — Invoice 1 of 4 (YTD=0, £40k invoice, crosses BRL)",
        "£40k invoice from zero. Crosses PA and BRL. Mixed 0%/20%/40% bands.",
        ["seq", "journey_b"],
        salary=0, ytd=0, pension=0, plans=[], invoice=40000,
    ),
    _it("RW-S2-121", "SEQ Journey B — Invoice 2 of 4 (YTD=40k, higher rate)",
        "YTD=40k. £20k invoice → end=60k. All in higher rate band.",
        ["seq", "journey_b"],
        salary=0, ytd=40000, pension=0, plans=[], invoice=20000,
    ),
    _it("RW-S2-122", "SEQ Journey B — Invoice 3 of 4 (YTD=60k, near taper, EL-001 family)",
        "YTD=60k. £50k invoice → ANI end=110k. Enters PA taper. EL-001 family.",
        ["seq", "journey_b", "el001_family"],
        salary=0, ytd=60000, pension=0, plans=[], invoice=50000,
    ),
    _it("RW-S2-123", "SEQ Journey B — Invoice 4 of 4 (YTD=110k, crosses PA elimination + ART, EL-001)",
        "YTD=110k. £20k invoice → ANI end=130k. Crosses £125,140. EL-001 family.",
        ["seq", "journey_b", "el001_family"],
        salary=0, ytd=110000, pension=0, plans=[], invoice=20000,
    ),

    # Journey C — employed + freelance with Plan 2, 4 invoices
    _it("RW-S2-124", "SEQ Journey C — Invoice 1 of 4 (employed £40k, first freelance invoice)",
        "£40k salary. YTD=0. £5k invoice → £45k. Basic rate; SL Plan2: 9%×(45k−29385).",
        ["seq", "journey_c", "student_loan"],
        salary=40000, ytd=0, pension=0, plans=[2], invoice=5000,
    ),
    _it("RW-S2-125", "SEQ Journey C — Invoice 2 of 4 (YTD=5k)",
        "£40k salary. YTD=5k. £10k invoice → £55k. Crosses BRL. SL Plan 2.",
        ["seq", "journey_c", "student_loan"],
        salary=40000, ytd=5000, pension=0, plans=[2], invoice=10000,
    ),
    _it("RW-S2-126", "SEQ Journey C — Invoice 3 of 4 (YTD=15k)",
        "£40k salary. YTD=15k. £10k invoice → £65k. Higher rate. SL Plan 2.",
        ["seq", "journey_c", "student_loan"],
        salary=40000, ytd=15000, pension=0, plans=[2], invoice=10000,
    ),
    _it("RW-S2-127", "SEQ Journey C — Invoice 4 of 4 (YTD=25k)",
        "£40k salary. YTD=25k. £10k invoice → £75k. Higher rate. SL Plan 2.",
        ["seq", "journey_c", "student_loan"],
        salary=40000, ytd=25000, pension=0, plans=[2], invoice=10000,
    ),

    # Journey D — pension-aware freelancer, 4 invoices
    _it("RW-S2-128", "SEQ Journey D — Invoice 1 of 4 (pension saver, £50k salary)",
        "£50k salary. YTD=0. £8k pension. £5k invoice → total=55k. eBRL=58270.",
        ["seq", "journey_d", "pension"],
        salary=50000, ytd=0, pension=8000, plans=[], invoice=5000,
    ),
    _it("RW-S2-129", "SEQ Journey D — Invoice 2 of 4 (YTD=5k)",
        "£50k salary. YTD=5k. £8k pension. £5k invoice → total=60k. Higher rate.",
        ["seq", "journey_d", "pension"],
        salary=50000, ytd=5000, pension=8000, plans=[], invoice=5000,
    ),
    _it("RW-S2-130", "SEQ Journey D — Invoice 3 of 4 (YTD=10k, EL-001 watch zone)",
        "£50k salary. YTD=10k. £8k pension. £5k invoice → ANI=57k. Below taper. "
        "eBRL=58270. IT: portion above eBRL at 40%.",
        ["seq", "journey_d", "pension"],
        salary=50000, ytd=10000, pension=8000, plans=[], invoice=5000,
    ),
    _it("RW-S2-131", "SEQ Journey D — Invoice 4 of 4 (YTD=15k)",
        "£50k salary. YTD=15k. £8k pension. £10k invoice → ANI=67k. Higher rate.",
        ["seq", "journey_d", "pension"],
        salary=50000, ytd=15000, pension=8000, plans=[], invoice=10000,
    ),

    # Journey E — year comparison: same journey, two tax years
    _it("RW-S2-132", "SEQ Journey E — 2025/26 early invoice",
        "£0 salary. YTD=24,000 (2025/26). £2k invoice → 26k. "
        "Plan 1 2025/26 threshold £24,990: 9%×(26k−24990)=9%×1010=£90.90.",
        ["seq", "journey_e", "student_loan", "sl_2526"],
        salary=0, ytd=24000, pension=0, plans=[1], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-133", "SEQ Journey E — 2026/27 same invoice (higher threshold)",
        "£0 salary. YTD=24,000 (2026/27). £2k invoice → 26k. "
        "Plan 1 2026/27 threshold £26,900: 26k < 26,900 → SL=0. Different from 2025/26.",
        ["seq", "journey_e", "student_loan", "sl_2627"],
        salary=0, ytd=24000, pension=0, plans=[1], invoice=2000, year="2026/27",
    ),

    _it("RW-S2-134", "SEQ Journey E — 2025/26 later invoice (well above threshold)",
        "£0 salary. YTD=28,000 (2025/26). £2k invoice → 30k. "
        "Plan 1 2025/26 threshold £24,990: 9%×2,000=£180.",
        ["seq", "journey_e", "student_loan", "sl_2526"],
        salary=0, ytd=28000, pension=0, plans=[1], invoice=2000, year="2025/26",
    ),

    _it("RW-S2-135", "SEQ Journey E — 2026/27 same later invoice",
        "£0 salary. YTD=28,000 (2026/27). £2k invoice → 30k. "
        "Plan 1 2026/27 threshold £26,900: 9%×(30k−26900)=9%×3100=£279.",
        ["seq", "journey_e", "student_loan", "sl_2627"],
        salary=0, ytd=28000, pension=0, plans=[1], invoice=2000, year="2026/27",
    ),
]

# ── GROUP EDG: Edge cases ─────────────────────────────────────────────────────
# 15 scenarios — RW-S2-136 to RW-S2-150

EDG = [

    _it("RW-S2-136", "EDG — zero invoice (validation boundary)",
        "Invoice = £0. Engine correctly rejects zero invoices with a validation error. "
        "Zero does not represent a real payment event; UNSUPPORTED_EXPECTED.",
        ["edg"],
        salary=40000, ytd=10000, pension=0, plans=[2], invoice=0,
        **{"expected_outcome": "unsupported",
           "notes": "Engine validates invoice_amount > 0; zero invoice is an out-of-scope input."},
    ),

    _it("RW-S2-137", "EDG — £1 invoice below PA (no tax)",
        "YTD=0. Invoice=£1. End=£1. Well below PA. IT=0, NI=0, SL=0.",
        ["edg"],
        salary=0, ytd=0, pension=0, plans=[], invoice=1,
    ),

    _it("RW-S2-138", "EDG — £0.01 invoice (penny, no tax)",
        "Smallest meaningful invoice. End=£0.01. All taxes = £0.",
        ["edg"],
        salary=0, ytd=0, pension=0, plans=[], invoice=0.01,
    ),

    _it("RW-S2-139", "EDG — very large invoice (£500,000) from zero",
        "Pure freelancer. Invoice=£500,000 from zero. "
        "Traverses all bands including 45%. "
        "Tests stability and precision at large values.",
        ["edg"],
        salary=0, ytd=0, pension=0, plans=[], invoice=500000,
    ),

    _it("RW-S2-140", "EDG — invoice amount with pence (£1,000.50)",
        "Fractional invoice. Tests ROUND_HALF_UP rounding behaviour.",
        ["edg"],
        salary=30000, ytd=0, pension=0, plans=[], invoice=1000.50,
    ),

    _it("RW-S2-141", "EDG — all components at once: IT + NI + SL + pension",
        "£40k salary + £10k pension + £15k YTD + £10k invoice. "
        "Plan 2 + Postgraduate. All components active simultaneously.",
        ["edg"],
        salary=40000, ytd=15000, pension=10000, plans=[2, "postgraduate"], invoice=10000,
    ),

    _it("RW-S2-142", "EDG — salary exactly at PA (no IT on salary)",
        "£12,570 salary + £0 YTD + £10k invoice. "
        "Salary exactly equals PA. Invoice all at 20%.",
        ["edg"],
        salary=12570, ytd=0, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S2-143", "EDG — salary exactly at BRL",
        "£50,270 salary + £0 YTD + £5k invoice. "
        "Salary exactly at BRL; entire invoice at 40%.",
        ["edg"],
        salary=50270, ytd=0, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-144", "EDG — salary exactly at ART",
        "£125,140 salary + £0 YTD + £5k invoice. "
        "Salary at ART; PA=0; entire invoice at 45%.",
        ["edg"],
        salary=125140, ytd=0, pension=0, plans=[], invoice=5000,
    ),

    _it("RW-S2-145", "EDG — very small invoice in higher rate band (£0.50)",
        "YTD=100,000. Invoice=£0.50. All at 40%. IT=40%×0.50=£0.20.",
        ["edg"],
        salary=0, ytd=100000, pension=0, plans=[], invoice=0.50,
    ),

    _it("RW-S2-146", "EDG — invoice at exact ART boundary (£0.50 at 45%)",
        "YTD=£125,140 (PA=0). Invoice=£0.50. At 45%. IT=45%×0.50=£0.23 (ROUND_HALF_UP).",
        ["edg"],
        salary=0, ytd=125140, pension=0, plans=[], invoice=0.50,
    ),

    _it("RW-S2-147", "EDG — multiple SL plans, one irrelevant (income below threshold)",
        "YTD=0. Invoice=£15,000. Plans [2, 4]. "
        "Plan 2 threshold £29,385 > £15k → SL=0. Plan 4 threshold £33,795 → SL=0. "
        "All SL=0.",
        ["edg", "student_loan"],
        salary=0, ytd=0, pension=0, plans=[2, 4], invoice=15000,
    ),

    _it("RW-S2-148", "EDG — all five SL plans simultaneously",
        "£0 salary + £0 YTD + £40k invoice. All five plans simultaneously. "
        "Plan 1 (£26,900): 9%×13,100=£1,179. Plan 2 (£29,385): 9%×10,615=£955.35. "
        "Plan 4 (£33,795): 9%×6,205=£558.45. Plan 5 (£25,000): 9%×15,000=£1,350. "
        "PGL (£21,000): 6%×19,000=£1,140. Total SL=£5,182.80.",
        ["edg", "student_loan"],
        salary=0, ytd=0, pension=0, plans=[1, 2, 4, 5, "postgraduate"], invoice=40000,
    ),

    _it("RW-S2-149", "EDG — 2025/26 and 2026/27 comparison (same scenario)",
        "£30k salary + £5k invoice. Plan 2. "
        "2026/27: Plan 2 threshold £29,385, income £35k, SL=9%×5,615=£505.35.",
        ["edg", "student_loan"],
        salary=30000, ytd=0, pension=0, plans=[2], invoice=5000,
    ),

    _it("RW-S2-150", "EDG — same scenario in 2025/26 (lower Plan 2 threshold)",
        "£30k salary + £5k invoice. Plan 2 2025/26. "
        "2025/26 threshold £28,470, income £35k, SL=9%×(35k−28470)=9%×6,530=£587.70. "
        "Verifies threshold difference between years.",
        ["edg", "student_loan"],
        salary=30000, ytd=0, pension=0, plans=[2], invoice=5000, year="2025/26",
    ),
]

# ── Master list ───────────────────────────────────────────────────────────────

STAGE_2 = REP + THR + SL_2526 + SL_2627 + PEN + CGT + SEQ + EDG

assert len(STAGE_2) == 150, f"Expected 150 Stage 2 scenarios, got {len(STAGE_2)}"

# Verify IDs are unique and in sequence
_ids = [s["scenario_id"] for s in STAGE_2]
assert len(_ids) == len(set(_ids)), f"Duplicate scenario IDs: {[x for x in _ids if _ids.count(x) > 1]}"

# Verify all expected IDs are present
_expected = {f"RW-S2-{i:03d}" for i in range(1, 151)}
_missing = _expected - set(_ids)
assert not _missing, f"Missing IDs: {sorted(_missing)}"
