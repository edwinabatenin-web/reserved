"""
Reserved West — Stage 1 Scenario Library (Smoke Tests, ~30 scenarios)

Scenario IDs: RW-S1-001 … RW-S1-030

Design matrix:
  Representative (001–008) — typical users across all rate bands
  Boundary (009–016)       — PA, BRL, PA-taper zone, ART, zero/tiny/large
  Student loan (017–023)   — all plans and dual repayment
  Pension RaS (024–026)    — band extension, taper elimination, no-effect
  CGT (027–030)            — below AEA, basic rate, split rate, BF losses

Each scenario carries pre-computed NOTES for traceability but the runner
always recomputes expected values from the independent reference calculator.
"""

# ── Income-tax scenario template ──────────────────────────────────────────────
# inputs keys:
#   invoice_amount, profile {day_job_salary, ytd_freelance_profit,
#   personal_pension_contributions, student_loan_plans}, tax_year
#
# ── CGT scenario template ─────────────────────────────────────────────────────
# inputs keys:
#   disposals (list of dicts with proceeds/allowable_cost),
#   taxable_income_before_gains, brought_forward_losses, tax_already_paid,
#   tax_year

STAGE_1: list[dict] = [

    # ── Representative ────────────────────────────────────────────────────────

    {
        "scenario_id": "RW-S1-001",
        "title": "Basic rate salary, invoice well within basic rate band",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £30,000, no prior freelance, £5,000 invoice. "
            "Entire invoice taxed at 20%; no NI (profit below LPL)."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "30000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=0, Total=1000
    },

    {
        "scenario_id": "RW-S1-002",
        "title": "Invoice straddles basic-rate / higher-rate boundary",
        "groups": ["representative", "boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £46,000, £10,000 invoice. Start £46k, end £56k. "
            "£4,270 at 20% (to BRL 50,270) and £5,730 at 40% (above BRL)."
        ),
        "inputs": {
            "invoice_amount": "10000",
            "profile": {
                "day_job_salary": "46000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=3146, NI=0, Total=3146
    },

    {
        "scenario_id": "RW-S1-003",
        "title": "Higher rate payer — invoice fully at higher rate",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £60,000, £5,000 invoice. Both start and end in higher "
            "rate band (50,270–125,140). IT = 5,000 × 40% = £2,000."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "60000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=2000, NI=0, Total=2000
    },

    {
        "scenario_id": "RW-S1-004",
        "title": "Additional rate payer — invoice fully at 45%",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £130,000, £5,000 invoice. Both above ART (£125,140). "
            "IT = 5,000 × 45% = £2,250."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "130000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=2250, NI=0, Total=2250
    },

    {
        "scenario_id": "RW-S1-005",
        "title": "Pure freelancer — invoice crosses PA and NI LPL",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "No salary, no prior YTD, £20,000 invoice. Crosses both PA "
            "(£12,570) and NI LPL (£12,570). "
            "IT = (20000-12570)×20% = £1,486. NI = (20000-12570)×6% = £445.80."
        ),
        "inputs": {
            "invoice_amount": "20000",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1486, NI=445.80, Total=1931.80
    },

    {
        "scenario_id": "RW-S1-006",
        "title": "Pure freelancer — invoice crosses NI upper profits limit",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "No salary, YTD profit £55,000, £5,000 invoice. Profit goes "
            "55k→60k, crossing NI UPL (£50,270). "
            "IT = 5,000×40% = £2,000. NI: main rate exhausted; (60k-55k)×2% = £100."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "55000",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=2000, NI=100, Total=2100
    },

    {
        "scenario_id": "RW-S1-007",
        "title": "Salary + prior YTD + invoice, NI crosses LPL",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £20,000, YTD profit £10,000, £8,000 invoice. "
            "Total income goes 30k→38k (all basic rate). "
            "Freelance profit 10k→18k crosses NI LPL (12,570). "
            "IT = 8,000×20% = £1,600. NI = (18k-12570)×6% = £325.80."
        ),
        "inputs": {
            "invoice_amount": "8000",
            "profile": {
                "day_job_salary": "20000",
                "ytd_freelance_profit": "10000",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1600, NI=325.80, Total=1925.80
    },

    {
        "scenario_id": "RW-S1-008",
        "title": "Gabriel persona (canonical)",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £45,000, YTD profit £3,000, £5,000 invoice, pension £2,000 "
            "gross (RaS), Plan 2 SL, 2026/27. "
            "Pension extends BRL to £52,270. Marginal IT straddles extended BRL. "
            "Plan 2 threshold £29,385; SL on marginal income."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "45000",
                "ytd_freelance_profit": "3000",
                "personal_pension_contributions": "2000",
                "student_loan_plans": [2],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1146, NI=0, SL=450, Total=1596
    },

    # ── Boundary ──────────────────────────────────────────────────────────────

    {
        "scenario_id": "RW-S1-009",
        "title": "Invoice crosses Personal Allowance from zero",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "No salary, no YTD, £15,000 invoice. Income crosses PA (£12,570). "
            "IT = (15000-12570)×20% = £486. NI = (15000-12570)×6% = £145.80."
        ),
        "inputs": {
            "invoice_amount": "15000",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=486, NI=145.80, Total=631.80
    },

    {
        "scenario_id": "RW-S1-010",
        "title": "Invoice starts exactly at basic-rate limit",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary exactly £50,270 (= BRL). £5,000 invoice. "
            "Entire invoice above BRL. IT = 5,000×40% = £2,000. NI = 0."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "50270",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=2000, NI=0, Total=2000
    },

    {
        "scenario_id": "RW-S1-011",
        "title": "Pure freelancer — NI straddles main/upper rate boundary",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "No salary, YTD profit £48,000, £5,000 invoice. Profit goes "
            "48k→53k, crossing NI UPL (£50,270). "
            "IT: straddles BRL too. NI splits at UPL."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "48000",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref):
        # IT: total_it(53000)-total_it(48000)
        #   = [(50270-12570)×0.2 + (53000-50270)×0.4] - [(48000-12570)×0.2]
        #   = [7540+1092] - 7086 = 8632 - 7086 = 1546
        # NI: total_ni(53000)-total_ni(48000)
        #   = [(50270-12570)×0.06 + (53000-50270)×0.02] - [(48000-12570)×0.06]
        #   = [2262+54.60] - 2127 = 2316.60 - 2127 = 189.60
        # Total: 1735.60
    },

    {
        "scenario_id": "RW-S1-012",
        "title": "Invoice enters PA taper zone (EL-001 expected)",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £99,000, £5,000 invoice. ANI goes 99k→104k, crossing "
            "PA taper start (£100,000). Engine uses end-state PA for full range "
            "(EL-001). Reference correctly applies different PAs at each point. "
            "Expected variance: £400 (reference > engine)."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "99000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Reference: IT=2400, NI=0, Total=2400
        # Engine (EL-001): IT=2000, Total=2000
        # Variance: -400 (engine underestimates)
    },

    {
        "scenario_id": "RW-S1-013",
        "title": "Invoice fully within PA taper zone (EL-001 expected)",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £105,000, £5,000 invoice. Both start and end in PA taper "
            "zone (100k–125,140). Each £1 of income costs £0.60 effective rate "
            "(40% on invoice + 20% on newly-exposed PA). "
            "EL-001 variance expected: £500."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "105000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Reference: IT=2500, NI=0, Total=2500
        # Engine (EL-001): IT=2000, Total=2000
        # Variance: -500
    },

    {
        "scenario_id": "RW-S1-014",
        "title": "Income crosses PA elimination threshold (EL-001 expected)",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £122,000, £10,000 invoice. Start in taper zone (PA=£1,570), "
            "end past taper zone (PA=£0, income=132k > 125,140 → also into "
            "additional rate). EL-001 variance expected: £314."
        ),
        "inputs": {
            "invoice_amount": "10000",
            "profile": {
                "day_job_salary": "122000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Reference: IT=4657, NI=0, Total=4657
        # Engine (EL-001): IT=4343, Total=4343
        # Variance: -314
    },

    {
        "scenario_id": "RW-S1-015",
        "title": "Tiny invoice — below PA, no tax",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "No prior income, £100 invoice. Income stays well below PA. "
            "IT = 0, NI = 0, Total = 0."
        ),
        "inputs": {
            "invoice_amount": "100",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=0, NI=0, Total=0
    },

    {
        "scenario_id": "RW-S1-016",
        "title": "Very large invoice crossing all bands from zero",
        "groups": ["boundary"],
        "envelope": "extended",
        "scenario_type": "income_tax",
        "description": (
            "No prior income, £150,000 invoice. Crosses PA, BRL, PA taper, "
            "ART. Start_income=0 so no EL-001 divergence (total_it(0)=0). "
            "Tests arithmetic across all four bands simultaneously."
        ),
        "inputs": {
            "invoice_amount": "150000",
            "profile": {
                "day_job_salary": "0",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref):
        # ANI=150000, PA=0 (fully tapered)
        # IT: 50270×0.2 + 74870×0.4 + 24860×0.45 = 10054+29948+11187 = 51189
        # NI: (50270-12570)×0.06 + (150000-50270)×0.02 = 2262+1994.60 = 4256.60
        # Total: 55445.60
    },

    # ── Student loan ──────────────────────────────────────────────────────────

    {
        "scenario_id": "RW-S1-017",
        "title": "Plan 2 SL — income below threshold, no repayment",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 2 active. Salary £20,000, £5,000 invoice → end £25,000. "
            "Plan 2 threshold 2026/27 = £29,385. No SL repayment."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "20000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [2],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=0, Total=1000
    },

    {
        "scenario_id": "RW-S1-018",
        "title": "Plan 2 SL — invoice crosses threshold",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 2 active. Salary £27,000, £5,000 invoice → end £32,000. "
            "Threshold £29,385. SL = (32000-29385)×9% = £235.35."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "27000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [2],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=235.35, Total=1235.35
    },

    {
        "scenario_id": "RW-S1-019",
        "title": "Plan 1 SL — invoice crosses threshold (2026/27)",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 1 active. Salary £24,000, £5,000 invoice → end £29,000. "
            "Plan 1 threshold 2026/27 = £26,900. SL = (29000-26900)×9% = £189."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "24000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [1],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=189, Total=1189
    },

    {
        "scenario_id": "RW-S1-020",
        "title": "Plan 4 SL — invoice crosses threshold (2026/27)",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 4 active. Salary £31,000, £5,000 invoice → end £36,000. "
            "Plan 4 threshold 2026/27 = £33,795. SL = (36000-33795)×9% = £198.45."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "31000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [4],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=198.45, Total=1198.45
    },

    {
        "scenario_id": "RW-S1-021",
        "title": "Plan 5 SL — invoice crosses threshold",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 5 active. Salary £24,000, £2,000 invoice → end £26,000. "
            "Plan 5 threshold = £25,000 (fixed). SL = (26000-25000)×9% = £90."
        ),
        "inputs": {
            "invoice_amount": "2000",
            "profile": {
                "day_job_salary": "24000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [5],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=400, NI=0, SL=90, Total=490
    },

    {
        "scenario_id": "RW-S1-022",
        "title": "Postgraduate loan — invoice crosses threshold",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "PGL active. Salary £20,000, £3,000 invoice → end £23,000. "
            "PGL threshold = £21,000 (fixed). SL = (23000-21000)×6% = £120."
        ),
        "inputs": {
            "invoice_amount": "3000",
            "profile": {
                "day_job_salary": "20000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": ["postgraduate"],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=600, NI=0, SL=120, Total=720
    },

    {
        "scenario_id": "RW-S1-023",
        "title": "Plan 2 + postgraduate loan — dual simultaneous repayment",
        "groups": ["interaction"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Plan 2 and PGL both active. Salary £27,000, £5,000 invoice → "
            "end £32,000. Plan 2 SL = £235.35 (threshold 29,385). "
            "PGL = (32000-21000)-(27000-21000) = £300. Total SL = £535.35."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "27000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0",
                "student_loan_plans": [2, "postgraduate"],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, SL=535.35, Total=1535.35
    },

    # ── Pension RaS ───────────────────────────────────────────────────────────

    {
        "scenario_id": "RW-S1-024",
        "title": "Pension RaS extends basic-rate band, saves higher-rate tax",
        "groups": ["interaction"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £52,000, £5,000 invoice, pension £5,000 gross. "
            "Without pension: invoice at 40%. With pension: eBRL = 55,270; "
            "income 52k→57k straddles eBRL. Tax saved vs no-pension = £654."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "52000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "5000",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1346, NI=0, Total=1346
        # (without pension would be IT=2000; saving = 654)
    },

    {
        "scenario_id": "RW-S1-025",
        "title": "Large pension keeps ANI at PA taper boundary, no EL-001",
        "groups": ["interaction", "boundary"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £103,000, £5,000 invoice, pension £8,000 gross. "
            "ANI(start) = 95,000; ANI(end) = 100,000 (exactly at taper start). "
            "PA is NOT tapered at either point. No EL-001 divergence. "
            "eBRL = 58,270. Invoice fully in higher rate band."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "103000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "8000",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=2000, NI=0, Total=2000
    },

    {
        "scenario_id": "RW-S1-026",
        "title": "Pension RaS — basic rate payer, no band extension benefit",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "income_tax",
        "description": (
            "Salary £30,000, £5,000 invoice, pension £3,000. "
            "eBRL = 53,270. End income = 35,000 << eBRL. "
            "Pension has no effect on marginal rate. IT = £1,000."
        ),
        "inputs": {
            "invoice_amount": "5000",
            "profile": {
                "day_job_salary": "30000",
                "ytd_freelance_profit": "0",
                "personal_pension_contributions": "3000",
                "student_loan_plans": [],
            },
            "tax_year": "2026/27",
        },
        # Expected (ref): IT=1000, NI=0, Total=1000 (same as RW-S1-001)
    },

    # ── CGT ───────────────────────────────────────────────────────────────────

    {
        "scenario_id": "RW-S1-027",
        "title": "CGT — disposal gain below Annual Exempt Amount",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "cgt",
        "description": (
            "Single share disposal with gain £2,000. AEA = £3,000. "
            "Net gains (£2,000) < AEA (£3,000). Taxable gains = £0. CGT = £0."
        ),
        "inputs": {
            "disposals": [{"proceeds": "7000", "allowable_cost": "5000",
                           "gain_or_loss": "2000", "description": "Shares A"}],
            "taxable_income_before_gains": "17430",
            "brought_forward_losses": "0",
            "tax_already_paid": "0",
            "tax_year": "2026/27",
        },
        # Expected (ref): taxable_gains=0, estimated_cgt=0
    },

    {
        "scenario_id": "RW-S1-028",
        "title": "CGT — disposal above AEA, basic rate taxpayer",
        "groups": ["representative"],
        "envelope": "intended",
        "scenario_type": "cgt",
        "description": (
            "Gain £8,000. AEA £3,000. Taxable gains = £5,000. "
            "Taxpayer income (after PA) = £17,430; basic band remaining = £32,840. "
            "All gains at basic rate (18%): CGT = 5,000×18% = £900."
        ),
        "inputs": {
            "disposals": [{"proceeds": "18000", "allowable_cost": "10000",
                           "gain_or_loss": "8000", "description": "Shares B"}],
            "taxable_income_before_gains": "17430",
            "brought_forward_losses": "0",
            "tax_already_paid": "0",
            "tax_year": "2026/27",
        },
        # Expected (ref): taxable_gains=5000, estimated_cgt=900
    },

    {
        "scenario_id": "RW-S1-029",
        "title": "CGT — basic / higher rate split",
        "groups": ["boundary"],
        "envelope": "intended",
        "scenario_type": "cgt",
        "description": (
            "Gain £10,000. AEA £3,000. Taxable gains = £7,000. "
            "Taxable income = £45,000; basic band remaining = £5,270. "
            "Basic slice: £5,270 × 18% = £948.60. "
            "Higher slice: £1,730 × 24% = £415.20. CGT = £1,363.80."
        ),
        "inputs": {
            "disposals": [{"proceeds": "30000", "allowable_cost": "20000",
                           "gain_or_loss": "10000", "description": "Crypto C"}],
            "taxable_income_before_gains": "45000",
            "brought_forward_losses": "0",
            "tax_already_paid": "0",
            "tax_year": "2026/27",
        },
        # Expected (ref): taxable_gains=7000, estimated_cgt=1363.80
    },

    {
        "scenario_id": "RW-S1-030",
        "title": "CGT — brought-forward losses reduce taxable gains",
        "groups": ["interaction"],
        "envelope": "intended",
        "scenario_type": "cgt",
        "description": (
            "Gain £15,000. Brought-forward losses £7,000. "
            "Net gains = 15,000-7,000 = £8,000. AEA £3,000. "
            "Taxable gains = £5,000 at basic rate (18%) = £900."
        ),
        "inputs": {
            "disposals": [{"proceeds": "25000", "allowable_cost": "10000",
                           "gain_or_loss": "15000", "description": "Shares D"}],
            "taxable_income_before_gains": "17430",
            "brought_forward_losses": "7000",
            "tax_already_paid": "0",
            "tax_year": "2026/27",
        },
        # Expected (ref): taxable_gains=5000, estimated_cgt=900
    },
]
