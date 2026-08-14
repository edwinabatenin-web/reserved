"""
Reserved West — Stage 4 Scenario Catalogue

Tolerance, Stress, Boundary, Invariant, and Validation Assurance (32 scenarios)

Stage 4 is the Final Gate.  Stages 1–3 verified the engine is arithmetically
correct under typical, boundary, and interaction conditions.  Stage 4 asks:

  1. Does the engine remain correct at extreme magnitudes (EXT)?
  2. Does it land correctly on exact threshold boundaries (BND)?
  3. Do mathematical invariants hold unconditionally (INV)?
  4. Does it handle edge-case and validation inputs correctly (VAL)?

Groups
------
EXT  Extreme valid inputs                   RW-S4-001 – RW-S4-008
BND  Exact boundary conditions              RW-S4-009 – RW-S4-018
INV  Mathematical invariants                RW-S4-019 – RW-S4-026
VAL  Validation and edge-case inputs        RW-S4-027 – RW-S4-032

ID assignment is permanent.  Do not re-use or renumber IDs.
Stage 5 IDs (if needed) begin at RW-S5-001.
"""

# ── Helpers (same conventions as Stages 2 and 3) ──────────────────────────────

def _it(sid, title, desc, groups, salary, ytd, pension, plans, invoice,
        year="2026/27", **kw):
    return {
        "scenario_id":   sid,
        "title":         title,
        "description":   desc,
        "groups":        ["stage4"] + groups,
        "envelope":      "income_tax",
        "scenario_type": "income_tax",
        "inputs": {
            "invoice_amount": invoice,
            "profile": {
                "day_job_salary":                 salary,
                "ytd_freelance_profit":           ytd,
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
        "groups":        ["stage4"] + groups,
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


# ── GROUP EXT: Extreme valid inputs ───────────────────────────────────────────
# 8 scenarios — RW-S4-001 to RW-S4-008
#
# These scenarios use inputs well beyond the typical user profile to confirm
# the engine scales correctly without arithmetic failures or silent truncation.
# All are arithmetically valid; no rejection is expected.

EXT = [

    _it("RW-S4-001",
        "Extreme: £1,000,000 invoice from zero — all IT and NI bands at maximum scale",
        "£0 salary, £0 YTD, no pension, no SL, £1,000,000 invoice, 2026/27. "
        "The largest plausible single invoice in Reserved's scope. "
        "ANI_end = £1,000,000 (PA = £0). All four IT bands traversed. "
        "PA band: £0 (PA eliminated). Basic: £50,270 × 20% = £10,054. "
        "Higher: £74,870 × 40% = £29,948. Additional: £874,860 × 45% = £393,687. "
        "IT = £433,689. "
        "NI: main 6% × £37,700 = £2,262; upper 2% × £949,730 = £18,994.60. NI = £21,256.60. "
        "Total = £454,945.60. "
        "Tests: engine handles seven-figure invoice amounts without arithmetic failure "
        "and applies PA elimination, all three positive-rate IT bands, and both NI rates correctly.",
        ["ext", "stress"],
        salary=0, ytd=0, pension=0, plans=[], invoice=1000000,
    ),

    _it("RW-S4-002",
        "Extreme: £500k YTD, £50k invoice — entirely at ceiling rates with PA already gone",
        "£0 salary, £500,000 YTD, no pension, no SL, £50,000 invoice, 2026/27. "
        "Profile is already well above ART (£125,140). ANI > taper elimination. PA = £0. "
        "IT = 45% × £50,000 = £22,500 (flat additional rate throughout). "
        "NI: profit £500k→£550k entirely above UPL. 2% × £50,000 = £1,000. "
        "Total = £23,500. "
        "Tests: engine applies the ceiling rate (45% IT, 2% NI) consistently across "
        "a large invoice when the starting position is already at extreme income.",
        ["ext", "stress"],
        salary=0, ytd=500000, pension=0, plans=[], invoice=50000,
    ),

    _it("RW-S4-003",
        "Extreme: pension far exceeds total income — ANI floored to zero throughout",
        "£0 salary, £10,000 YTD, £100,000 pension RaS, no SL, £30,000 invoice, 2026/27. "
        "Pension exceeds both start and end total income: "
        "ANI_start = max(0, 10,000 − 100,000) = £0 (PA = £12,570). "
        "ANI_end   = max(0, 40,000 − 100,000) = £0 (PA = £12,570). "
        "eBRL = min(50,270 + 100,000, 125,140) = £125,140 (EL-003 cap applied). "
        "IT: total_IT(40,000, 100k) − total_IT(10,000, 100k). "
        "Both have ANI = 0, PA = £12,570, eBRL = £125,140. "
        "total_IT(10k, 100k): income 10k < PA 12,570 → IT = £0. "
        "total_IT(40k, 100k): basic (40k − 12,570) × 20% = £5,486. IT = £5,486. "
        "NI: profit £10k→£40k (below UPL £50,270). 6% × (40k − 12,570) = £1,645.80. "
        "Total = £7,131.80. "
        "Tests: ANI floor at zero is correctly applied at both start and end; "
        "the engine never returns negative ANI or negative IT.",
        ["ext", "stress", "pension", "ebrl_cap"],
        salary=0, ytd=10000, pension=100000, plans=[], invoice=30000,
    ),

    _it("RW-S4-004",
        "Extreme: £500k day-job salary + invoice — freelance NI at basic rate, IT at 45%",
        "£500,000 salary, £0 YTD, no pension, no SL, £20,000 invoice, 2026/27. "
        "Salary alone far exceeds ART (£125,140). ANI_start = £500k (PA = £0). "
        "ANI_end = £520k (PA = £0). Invoice entirely at 45% IT. "
        "IT = total_IT(520k, 0) − total_IT(500k, 0) = 45% × £20,000 = £9,000. "
        "NI: sole-trader profit £0→£20,000 (salary NI is Class 1; only profit NI computed here). "
        "6% × (£20,000 − £12,570) = 6% × £7,430 = £445.80. "
        "Total = £9,445.80. "
        "Tests: very large salary pushes IT to 45% on the first pound of freelance income; "
        "NI on freelance profit is still computed on the basis of profit alone (not salary).",
        ["ext", "stress"],
        salary=500000, ytd=0, pension=0, plans=[], invoice=20000,
    ),

    _it("RW-S4-005",
        "Extreme: all five SL plans + pension at annual allowance + £50k invoice crossing PA elimination",
        "£60k salary, £100k YTD, £60k pension RaS, all five SL plans, £50k invoice, 2026/27. "
        "eBRL = min(50,270 + 60,000, 125,140) = £110,270. "
        "ANI_start = (160k − 60k) = £100k (taper entry; PA = £12,570 — no reduction yet). "
        "ANI_end   = (210k − 60k) = £150k (above elimination; PA = £0). EL-001 zone. "
        "start = £160k > ART; end = £210k > ART. Invoice entirely at 45%. "
        "IT = total_IT(210k, 60k) − total_IT(160k, 60k). "
        "PA_start = £12,570 (ANI=100k, taper not yet applied). PA_end = £0 (ANI=150k). "
        "Invoice at 45% = 50k×45% = £22,500. PA exposure cost = 12,570 × 20% = £2,514. "
        "IT = £25,014. "
        "NI: profit £100k→£150k > UPL. 2% × £50k = £1,000. "
        "All SL (start £160k > all thresholds): Plans 1/2/4/5 each 9% × £50k = £1,800 × 4 = £7,200. "
        "PGL: 6% × £50k = £3,000. Total SL = £21,000. "
        "Total = 25,014 + 1,000 + 21,000 = £47,014. "
        "Tests: all five SL plans + annual-allowance pension + EL-001 zone + 45% band in one invoice.",
        ["ext", "el001_family", "pension", "student_loan", "all_components", "stress"],
        salary=60000, ytd=100000, pension=60000,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=50000,
    ),

    _it("RW-S4-006",
        "Extreme: all five SL plans + £200k invoice from zero — maximum SL exposure",
        "£0 salary, £0 YTD, no pension, all five SL plans, £200,000 invoice, 2026/27. "
        "All SL plans start with zero income, so each threshold must be crossed during the invoice. "
        "IT: PA = £0 (ANI_end = £200k). basic £50,270 × 20% = £10,054; "
        "higher £74,870 × 40% = £29,948; additional £74,860 × 45% = £33,687. IT = £73,689. "
        "NI: main 6% × £37,700 = £2,262; upper 2% × £149,730 = £2,994.60. NI = £5,256.60. "
        "SL (marginal for this invoice, each plan active above its threshold): "
        "Plan 1 (£26,900): 9% × £173,100 = £15,579.00. "
        "Plan 2 (£29,385): 9% × £170,615 = £15,355.35. "
        "Plan 4 (£33,795): 9% × £166,205 = £14,958.45. "
        "Plan 5 (£25,000): 9% × £175,000 = £15,750.00. "
        "PGL  (£21,000): 6% × £179,000 = £10,740.00. "
        "Total SL = £72,382.80. "
        "Total = 73,689 + 5,256.60 + 72,382.80 = £151,328.40. "
        "Tests: all five SL plans from zero income; maximum SL exposure in a single invoice; "
        "each threshold correctly splits the repayment.",
        ["ext", "student_loan", "stress"],
        salary=0, ytd=0, pension=0,
        plans=[1, 2, 4, 5, "postgraduate"], invoice=200000,
    ),

    _it("RW-S4-007",
        "Extreme: £1 invoice at the top of the 40% band — last penny before ART",
        "£0 salary, £125,139 YTD, no pension, no SL, £1 invoice, 2026/27. "
        "ANI_end = £125,140 (exactly the ART elimination threshold; PA = £0). "
        "The invoice of £1 spans the last pound of the 40% higher-rate band. "
        "IT: total_IT(125,140, 0) − total_IT(125,139, 0). "
        "Both have ANI ≥ taper elimination → PA = £0. "
        "total_IT(125,139, 0): basic 50,270×20% = £10,054; higher (125,139−50,270)×40% = 74,869×40% = £29,947.60; total = £40,001.60. "
        "total_IT(125,140, 0): basic £10,054; higher 74,870×40% = £29,948; total = £40,002. "
        "IT = £40,002 − £40,001.60 = £0.40. "
        "NI: profit £125,139→£125,140 > UPL. 2% × £1 = £0.02. "
        "Total = £0.42. "
        "Tests: the engine correctly applies 40% to the last pound of the higher-rate band "
        "and does not prematurely switch to 45%.",
        ["ext", "stress"],
        salary=0, ytd=125139, pension=0, plans=[], invoice=1,
    ),

    _it("RW-S4-008",
        "Extreme: £1 invoice at the ART boundary — first pound of 45% additional rate",
        "£0 salary, £125,140 YTD, no pension, no SL, £1 invoice, 2026/27. "
        "ANI_start = £125,140 (PA = £0). Invoice is entirely in the 45% additional-rate band. "
        "IT = 45% × £1 = £0.45. "
        "NI: profit £125,140→£125,141 > UPL. 2% × £1 = £0.02. "
        "Total = £0.47. "
        "Tests: the additional rate activates on the first pound above ART (£125,140); "
        "no off-by-one in the ART boundary condition.",
        ["ext", "stress"],
        salary=0, ytd=125140, pension=0, plans=[], invoice=1,
    ),

]


# ── GROUP BND: Exact boundary conditions ──────────────────────────────────────
# 10 scenarios — RW-S4-009 to RW-S4-018
#
# Each scenario is constructed so that one or more tax thresholds are hit
# exactly.  Off-by-one errors in boundary detection would produce wrong results
# that the reference calculator would immediately detect.

BND = [

    _it("RW-S4-009",
        "Boundary: invoice ends exactly at BRL/UPL (£50,270) — no higher-rate IT, no upper NI",
        "£0 salary, £0 YTD, no pension, no SL, £50,270 invoice, 2026/27. "
        "Income starts at £0 and ends exactly at BRL = UPL = £50,270. "
        "(In 2026/27 both the Basic Rate Limit and the Upper Profits Limit are £50,270.) "
        "IT: basic only. (50,270 − 12,570) × 20% = 37,700 × 20% = £7,540. "
        "NI: profit £50,270 ends exactly at UPL — no upper rate applies. "
        "6% × (50,270 − 12,570) = 6% × 37,700 = £2,262. "
        "Total = £9,802. "
        "Tests: BRL and UPL exact-boundary detection — no higher-rate IT or upper NI "
        "applied at the threshold itself.",
        ["bnd"],
        salary=0, ytd=0, pension=0, plans=[], invoice=50270,
    ),

    _it("RW-S4-010",
        "Boundary: invoice starts exactly at BRL/UPL — entire invoice at 40% IT and 2% NI",
        "£0 salary, £50,270 YTD, no pension, no SL, £10,000 invoice, 2026/27. "
        "Starting income equals BRL = UPL = £50,270. "
        "IT: entire invoice at 40% higher rate. 40% × £10,000 = £4,000. "
        "NI: profit £50,270→£60,270 entirely above UPL. 2% × £10,000 = £200. "
        "Total = £4,200. "
        "Tests: when the starting income is exactly at the BRL/UPL threshold, "
        "the engine correctly applies the upper rates from the first pound.",
        ["bnd"],
        salary=0, ytd=50270, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S4-011",
        "Boundary: invoice straddles BRL and UPL simultaneously (both at £50,270)",
        "£0 salary, £45,270 YTD, no pension, no SL, £10,000 invoice, 2026/27. "
        "Invoice straddles the BRL/UPL threshold: £5,000 below and £5,000 above. "
        "IT: 20% × £5,000 (below BRL) + 40% × £5,000 (above BRL) = £1,000 + £2,000 = £3,000. "
        "NI: 6% × £5,000 (below UPL) + 2% × £5,000 (above UPL) = £300 + £100 = £400. "
        "Total = £3,400. "
        "Tests: when income crosses BRL/UPL mid-invoice, the split is computed correctly "
        "with exactly £5,000 at each side of the threshold.",
        ["bnd"],
        salary=0, ytd=45270, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S4-012",
        "Boundary: invoice ends exactly at ART (£125,140) from zero — PA eliminated, no 45%",
        "£0 salary, £0 YTD, no pension, no SL, £125,140 invoice, 2026/27. "
        "Income runs from £0 to exactly £125,140 (the ART threshold). "
        "ANI_end = £125,140 → PA = max(0, 12,570 − 12,570) = £0 (exactly eliminated). "
        "IT: PA = £0. Basic £50,270 × 20% = £10,054. Higher £74,870 × 40% = £29,948. "
        "Additional: £0 (income ends exactly at ART, not above it). IT = £40,002. "
        "NI: main 6% × £37,700 = £2,262; upper 2% × £74,870 = £1,497.40. NI = £3,759.40. "
        "Total = £43,761.40. "
        "Tests: ART boundary — no additional-rate IT applied at exactly £125,140; "
        "PA taper elimination is complete at this exact income level.",
        ["bnd", "el001_family"],
        salary=0, ytd=0, pension=0, plans=[], invoice=125140,
    ),

    _it("RW-S4-013",
        "Boundary: invoice starts exactly at ART — entire invoice at 45% additional rate",
        "£0 salary, £125,140 YTD, no pension, no SL, £10,000 invoice, 2026/27. "
        "Starting income equals ART = £125,140. PA = £0. "
        "IT = 45% × £10,000 = £4,500. "
        "NI: profit £125,140→£135,140 entirely above UPL. 2% × £10,000 = £200. "
        "Total = £4,700. "
        "Tests: the additional rate (45%) applies correctly from the first pound "
        "when starting income is exactly at ART.",
        ["bnd"],
        salary=0, ytd=125140, pension=0, plans=[], invoice=10000,
    ),

    _it("RW-S4-014",
        "Boundary: invoice from zero ends exactly at taper entry (ANI = £100,000) — PA still £12,570",
        "£0 salary, £0 YTD, no pension, no SL, £100,000 invoice, 2026/27. "
        "ANI_end = £100,000. The PA taper applies when ANI > £100,000; at exactly £100,000, PA = £12,570. "
        "IT: basic (50,270−12,570) × 20% = £7,540; higher (100,000−50,270) × 40% = £19,892. IT = £27,432. "
        "NI: main 6% × £37,700 = £2,262; upper 2% × (100,000−50,270) = 2% × £49,730 = £994.60. NI = £3,256.60. "
        "Total = £30,688.60. "
        "Tests: PA is still £12,570 when ANI is exactly £100,000; the taper does not apply "
        "at the boundary itself (it applies only above £100,000).",
        ["bnd", "el001_family"],
        salary=0, ytd=0, pension=0, plans=[], invoice=100000,
    ),

    _it("RW-S4-015",
        "Boundary: pension sets eBRL exactly at ART — EL-003 cap at exact boundary",
        "£0 salary, £50,270 YTD, £74,870 pension RaS, no SL, £10,000 invoice, 2026/27. "
        "eBRL = min(50,270 + 74,870, 125,140) = min(125,140, 125,140) = £125,140 exactly. "
        "Pension is positioned so eBRL lands exactly on the ART cap. "
        "ANI_start = max(0, 50,270 − 74,870) = £0 (PA = £12,570). "
        "ANI_end   = max(0, 60,270 − 74,870) = £0 (PA = £12,570). "
        "IT: total_IT(60,270, 74,870) − total_IT(50,270, 74,870). "
        "Both have ANI=0, PA=£12,570, eBRL=£125,140. "
        "total_IT(50,270, 74,870): basic (50,270−12,570) × 20% = £7,540. "
        "total_IT(60,270, 74,870): basic (60,270−12,570) × 20% = £9,540. "
        "IT = £2,000. (Invoice entirely at 20%, sheltered by eBRL at ART.) "
        "NI: profit £50,270→£60,270 > UPL. 2% × £10,000 = £200. "
        "Total = £2,200. "
        "Tests: eBRL cap exactly at ART is handled correctly; the engine applies the cap "
        "and the invoice is entirely at the basic rate as expected.",
        ["bnd", "pension", "ebrl_cap"],
        salary=0, ytd=50270, pension=74870, plans=[], invoice=10000,
    ),

    _it("RW-S4-016",
        "Boundary: SL Plan 2 — invoice starts exactly at threshold (£29,385)",
        "£0 salary, £29,385 YTD, no pension, Plan 2, £1,000 invoice, 2026/27. "
        "YTD positions income exactly at the Plan 2 threshold (£29,385). "
        "SL_start = 9% × max(0, £29,385 − £29,385) = £0. "
        "SL_end   = 9% × max(0, £30,385 − £29,385) = 9% × £1,000 = £90. "
        "SL = £90. IT = 20% × £1,000 = £200. NI = 6% × £1,000 = £60. "
        "Total = £350. "
        "Tests: SL repayment activates from the first pound above the threshold "
        "when income starts exactly at the threshold.",
        ["bnd", "student_loan"],
        salary=0, ytd=29385, pension=0, plans=[2], invoice=1000,
    ),

    _it("RW-S4-017",
        "Boundary: SL Plan 5 — invoice straddles fixed threshold (£25,000) exactly",
        "£0 salary, £24,500 YTD, no pension, Plan 5 only, £1,000 invoice, 2026/27. "
        "Invoice starts £500 below the Plan 5 threshold (£25,000) and ends £500 above. "
        "SL = 9% × (£25,500 − £25,000) = 9% × £500 = £45. "
        "IT = 20% × £1,000 = £200. NI = 6% × £1,000 = £60. "
        "Total = £305. "
        "Tests: Plan 5 fixed threshold split is applied correctly mid-invoice; "
        "only the portion above £25,000 attracts repayment.",
        ["bnd", "student_loan"],
        salary=0, ytd=24500, pension=0, plans=[5], invoice=1000,
    ),

    _it("RW-S4-018",
        "Boundary: income ends exactly at PA = LPL = £12,570 — IT = 0, NI = 0",
        "£0 salary, £0 YTD, no pension, no SL, £12,570 invoice, 2026/27. "
        "Income 0→£12,570. PA = £12,570 (nil-rate band exactly). LPL = £12,570 (NI threshold). "
        "IT: income = PA exactly → all income in nil-rate band. IT = £0. "
        "NI: profit = LPL exactly → no profit above the lower-profits limit. NI = £0. "
        "Total = £0.00. "
        "Tests: the joint PA/LPL boundary at £12,570; both IT and NI produce zero "
        "when income ends at exactly this threshold.",
        ["bnd"],
        salary=0, ytd=0, pension=0, plans=[], invoice=12570,
    ),

]


# ── GROUP INV: Mathematical invariants ────────────────────────────────────────
# 8 scenarios — RW-S4-019 to RW-S4-026
#
# Each scenario targets a specific mathematical property the engine must
# satisfy unconditionally.  A passing scenario is evidence that the property
# holds; a failure would indicate a structural engine defect.

INV = [

    _it("RW-S4-019",
        "Invariant: non-negativity — pension > income, ANI = 0; IT must not be negative",
        "£0 salary, £5,000 YTD, £50,000 pension RaS, no SL, £10,000 invoice, 2026/27. "
        "Pension greatly exceeds total income; ANI = max(0, 15k−50k) = £0 throughout. "
        "eBRL = min(50,270+50,000, 125,140) = £100,270. PA = £12,570. "
        "total_IT(15,000, 50k): basic (15,000−12,570)×20% = £486. "
        "total_IT(5,000, 50k): income < PA = £0. "
        "IT = £486 (NOT negative — floored correctly at the engine level). "
        "NI: profit £5k→£15k (below UPL). 6% × (15,000−12,570) = £145.80. "
        "Total = £631.80. "
        "Invariant confirmed: IT is always ≥ £0; pension can reduce IT to near-zero "
        "but never produces a negative liability.",
        ["inv", "pension"],
        salary=0, ytd=5000, pension=50000, plans=[], invoice=10000,
    ),

    _it("RW-S4-020",
        "Invariant: SL is independent of pension — pension reduces IT/ANI but not SL income",
        "£0 salary, £25,000 YTD, £5,000 pension RaS, Plan 2, £10,000 invoice, 2026/27. "
        "Pension reduces ANI and extends eBRL, but per HMRC rules SL is computed on "
        "total income (salary + profit) not on ANI. "
        "IT: eBRL = £55,270. Both start/end below eBRL. "
        "total_IT(35,000, 5k): basic (35k−12,570)×20% = £4,486. "
        "total_IT(25,000, 5k): basic (25k−12,570)×20% = £2,486. IT = £2,000. "
        "NI: 6% × £10,000 = £600. "
        "SL Plan 2 (£29,385): SL_on(25,000)=£0; SL_on(35,000)=9%×(35,000−29,385)=9%×£5,615=£505.35. "
        "Total = 2,000 + 600 + 505.35 = £3,105.35. "
        "Invariant confirmed: pension contribution does not suppress SL repayment; "
        "SL is on gross income, not net-of-pension income.",
        ["inv", "pension", "student_loan"],
        salary=0, ytd=25000, pension=5000, plans=[2], invoice=10000,
    ),

    _it("RW-S4-021",
        "Invariant: NI is independent of pension — NI on gross profit, pension affects IT only",
        "£0 salary, £40,000 YTD, £30,000 pension RaS, no SL, £15,000 invoice, 2026/27. "
        "Pension affects ANI (and thus IT) but NI is computed on gross freelance profit. "
        "eBRL = min(50,270+30,000, 125,140) = £80,270. "
        "IT: ANI_start = max(0, 40k−30k) = £10,000 (PA=£12,570); "
        "ANI_end = max(0, 55k−30k) = £25,000 (PA=£12,570). "
        "Income £40k→£55k fully below eBRL=£80,270; entirely at 20%. IT = 20%×£15,000 = £3,000. "
        "NI: profit £40,000→£55,000 straddles UPL (£50,270). "
        "main = 6%×(50,270−40,000) = 6%×£10,270 = £616.20; "
        "upper = 2%×(55,000−50,270) = 2%×£4,730 = £94.60. NI = £710.80. "
        "Total = 3,000 + 710.80 = £3,710.80. "
        "Invariant confirmed: the NI upper-rate split at UPL is on gross profit "
        "regardless of pension contributions; pension does not shift the NI UPL boundary.",
        ["inv", "pension"],
        salary=0, ytd=40000, pension=30000, plans=[], invoice=15000,
    ),

    _it("RW-S4-022",
        "Invariant: zero-tax floor — income below all thresholds produces zero total tax",
        "£0 salary, £0 YTD, £0 pension, Plan 2, £5,000 invoice, 2026/27. "
        "End income = £5,000. IT: income < PA (£12,570) → IT = £0. "
        "NI: profit < LPL (£12,570) → NI = £0. "
        "SL Plan 2: income < threshold (£29,385) → SL = £0. "
        "Total = £0.00. "
        "Invariant confirmed: when income is below all thresholds (PA, LPL, all SL plans), "
        "every component produces zero. No component produces a negative amount.",
        ["inv", "student_loan"],
        salary=0, ytd=0, pension=0, plans=[2], invoice=5000,
    ),

    _it("RW-S4-023",
        "Invariant: ROUND_HALF_UP for IT at 20% — £0.005 rounds UP to £0.01",
        "£0 salary, £20,000 YTD, no pension, no SL, £0.025 invoice, 2026/27. "
        "IT = 20% × £0.025 = £0.005. ROUND_HALF_UP: £0.005 → £0.01 (not £0.00). "
        "NI = 6% × £0.025 = £0.0015 → £0.00. "
        "Total = £0.01. "
        "Invariant confirmed: ROUND_HALF_UP is applied to IT at the 20% rate; "
        "the half-penny rounds up (ROUND_HALF_EVEN would give £0.00 — incorrect).",
        ["inv", "rounding"],
        salary=0, ytd=20000, pension=0, plans=[], invoice="0.025",
    ),

    _it("RW-S4-024",
        "Invariant: ROUND_HALF_UP for NI at 2% upper rate — £0.005 rounds UP to £0.01",
        "£0 salary, £200,000 YTD, no pension, no SL, £0.25 invoice, 2026/27. "
        "Income entirely above ART. NI = 2% × £0.25 = £0.005 → £0.01 (ROUND_HALF_UP). "
        "IT = 45% × £0.25 = £0.1125 → £0.11. "
        "Total = £0.12. "
        "Invariant confirmed: ROUND_HALF_UP is applied to NI at the 2% upper rate; "
        "the half-penny rounds up correctly.",
        ["inv", "rounding"],
        salary=0, ytd=200000, pension=0, plans=[], invoice="0.25",
    ),

    _it("RW-S4-025",
        "Invariant: ROUND_HALF_UP for SL at 9% — £0.045 rounds UP to £0.05",
        "£0 salary, £30,000 YTD, no pension, Plan 1 only, £0.50 invoice, 2026/27. "
        "start = £30,000 > Plan 1 threshold (£26,900). "
        "SL = 9% × £0.50 = £0.045 → £0.05 (ROUND_HALF_UP). "
        "IT = 20% × £0.50 = £0.10. NI = 6% × £0.50 = £0.03. "
        "Total = £0.18. "
        "Invariant confirmed: ROUND_HALF_UP is applied to SL (9% rate) correctly; "
        "ROUND_HALF_EVEN would give £0.04 — incorrect.",
        ["inv", "rounding", "student_loan"],
        salary=0, ytd=30000, pension=0, plans=[1], invoice="0.50",
    ),

    _it("RW-S4-026",
        "Invariant: component additivity — IT + NI + SL equals the reported Total",
        "£0 salary, £30,000 YTD, £5,000 pension RaS, Plan 2, £10,000 invoice, 2026/27. "
        "This scenario is chosen to produce non-trivial, non-zero values for all three "
        "components: IT, NI, and SL (Plan 2). "
        "eBRL = £55,270. ANI_start = £25,000 (below taper). ANI_end = £35,000. "
        "IT: total_IT(40,000, 5k) − total_IT(30,000, 5k). "
        "Both below eBRL and BRL: 20% × £10,000 = £2,000. "
        "NI: 6% × £10,000 = £600. "
        "SL Plan 2 (£29,385): SL_on(30k) = £0; SL_on(40k) = 9% × (40k−29,385) = 9% × £10,615 = £955.35. "
        "Components: IT £2,000 + NI £600 + SL £955.35 = £3,555.35. "
        "Invariant confirmed: the engine's Total field exactly equals the sum of its components; "
        "there is no independent 'total' computation that could drift from the parts.",
        ["inv", "pension", "student_loan"],
        salary=0, ytd=30000, pension=5000, plans=[2], invoice=10000,
    ),

]


# ── GROUP VAL: Validation and edge-case inputs ────────────────────────────────
# 6 scenarios — RW-S4-027 to RW-S4-032
#
# These scenarios probe the engine's behaviour at the edges of valid input space,
# including the single known UNSUPPORTED case (zero invoice) already verified in
# Stage 2 (RW-S2-136) and here re-confirmed at the Final Gate.

VAL = [

    _it("RW-S4-027",
        "Validation: zero invoice — engine must reject; UNSUPPORTED_EXPECTED",
        "£0 salary, £0 YTD, no pension, no SL, £0 invoice, 2026/27. "
        "A zero-amount invoice is meaningless; the engine must raise a ValueError or "
        "equivalent rejection. This was first confirmed at Stage 2 (RW-S2-136). "
        "Re-confirmed here at the Final Gate to ensure no regression in validation. "
        "Expected outcome: UNSUPPORTED_EXPECTED.",
        ["val"],
        salary=0, ytd=0, pension=0, plans=[], invoice=0,
        **{"expected_outcome": "unsupported",
           "notes": "Engine validates invoice_amount > 0; zero invoice is an out-of-scope input. Confirmed at Stage 2 (RW-S2-136) and re-confirmed at Final Gate."},
    ),

    _it("RW-S4-028",
        "Validation: single-penny invoice entirely within PA — all components zero",
        "£0 salary, £0 YTD, no pension, no SL, £0.01 invoice, 2026/27. "
        "End income = £0.01. All thresholds unmet: "
        "IT: income £0.01 < PA £12,570 → IT = £0.00. "
        "NI: profit £0.01 < LPL £12,570 → NI = £0.00. "
        "Total = £0.00. "
        "Tests: the smallest valid non-zero invoice, entirely within the nil-rate band, "
        "produces no tax liability. The engine must not produce negative values.",
        ["val"],
        salary=0, ytd=0, pension=0, plans=[], invoice="0.01",
    ),

    _it("RW-S4-029",
        "Validation: pension far exceeds income — ANI = 0; no negative tax",
        "£0 salary, £0 YTD, £200,000 pension RaS, no SL, £50,000 invoice, 2026/27. "
        "Pension (£200k) vastly exceeds total income (£50k). "
        "ANI_start = max(0, 0−200,000) = £0 (PA=£12,570). "
        "ANI_end   = max(0, 50,000−200,000) = £0 (PA=£12,570). "
        "eBRL = min(50,270+200,000, 125,140) = £125,140 (EL-003 cap). "
        "IT: total_IT(50,000, 200k): basic (50,000−12,570)×20% = £7,486. "
        "total_IT(0, 200k): IT = £0 (income=£0). IT = £7,486. "
        "NI: profit £0→£50,000. 6% × (50,000−12,570) = 6% × £37,430 = £2,245.80. "
        "Total = £9,731.80. "
        "Tests: extreme pension never produces negative ANI, negative PA, or negative IT. "
        "The engine correctly floors ANI at zero and applies EL-003 cap on eBRL.",
        ["val", "pension", "ebrl_cap"],
        salary=0, ytd=0, pension=200000, plans=[], invoice=50000,
    ),

    _cgt("RW-S4-030",
        "Validation: CGT — gain exactly equals AEA; zero taxable gain, zero CGT",
        "Taxable income before gains = £60,000 (above BRL; BRL remaining = £0). "
        "Gain = £3,000. AEA = £3,000. BF losses = £0. "
        "Taxable gain = £3,000 − £3,000 = £0. CGT = £0. "
        "Tests: the exact-AEA boundary; gain is fully absorbed by the annual exempt amount "
        "and no CGT liability arises. The engine must not produce a negative or non-zero CGT.",
        ["val", "cgt"],
        disposals=[_d("shares", "UK growth fund", 8000, 5000)],
        tib=60000,
    ),

    _cgt("RW-S4-031",
        "Validation: CGT — all gain at 18% basic rate when taxable income is zero",
        "Taxable income before gains = £0 (no other income; full BRL available). "
        "Gain = £20,000. AEA = £3,000. BF losses = £0. Taxable gain = £17,000. "
        "BRL remaining = £50,270 − £0 = £50,270 (> £17,000). All gain at 18% basic rate. "
        "CGT = 18% × £17,000 = £3,060. "
        "Tests: when taxable income is zero, the entire AEA-reduced gain qualifies for "
        "the 18% basic rate (not the 24% higher rate), confirming the BRL split logic "
        "at its extreme lower boundary.",
        ["val", "cgt"],
        disposals=[_d("shares", "Tech fund", 25000, 5000)],
        tib=0,
    ),

    _cgt("RW-S4-032",
        "Validation: CGT — brought-forward losses exceed gain; net gain = 0; CGT = 0",
        "Taxable income before gains = £80,000 (above BRL; BRL remaining = £0). "
        "Gain = £5,000. BF losses = £10,000. "
        "Net gain after BF losses = max(0, £5,000 − £10,000) = £0. "
        "After AEA: max(0, £0 − £3,000) = £0. CGT = £0. "
        "Tests: the engine correctly applies BF losses before the AEA; "
        "when BF losses fully absorb the gain, CGT is zero regardless of any remaining AEA.",
        ["val", "cgt"],
        disposals=[_d("shares", "European equities", 12000, 7000)],
        tib=80000, bf=10000,
    ),

]


# ── Assembly ──────────────────────────────────────────────────────────────────

STAGE_4: list[dict] = EXT + BND + INV + VAL

assert len(STAGE_4) == 32, f"Expected 32 Stage 4 scenarios, got {len(STAGE_4)}"
assert len({s["scenario_id"] for s in STAGE_4}) == len(STAGE_4), "Duplicate scenario IDs"
assert all(s["scenario_id"].startswith("RW-S4-") for s in STAGE_4), "Bad ID prefix"
