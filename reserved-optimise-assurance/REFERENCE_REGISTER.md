# Initiative 002 — Reference Register

All statutory sources used to construct the independent reference implementations.

## Primary Statutory Sources

| Mechanism | Source | Description |
|---|---|---|
| Income tax rates and bands | ITEPA 2003 Part 2; Income Tax Act 2007 s.35 | Rates 20%/40%/45%; threshold freeze through 2027/28 per Finance Act 2022 |
| Personal Allowance | ITEPA 2003 s.35 | £12,570 (frozen) |
| PA taper | Finance (No.2) Act 2015; ITEPA 2003 s.35 | £1 per £2 ANI above £100,000; zero at £125,140 |
| Additional Rate Threshold | Finance (No.2) Act 2015 | £125,140 (effective 2023/24 onwards) |
| Basic Rate Limit | ITA 2007 s.10 | £50,270 (frozen through 2027/28) |
| HICBC | Finance Act 2012 ss.681A-681H | 1% per £200 ANI above £60,000 (revised threshold, Finance Act 2024) |
| HICBC — 2024 reform | Finance Act 2024 | Threshold raised from £50,000 to £60,000, full reclaim at £80,000 |
| Pension Relief at Source | Finance Act 2004 s.192; HMRC PTM044100 | Net contribution × 1.25 = gross; BRL extended by gross contribution |
| Pension Annual Allowance | Finance Act 2004 s.214; Finance (No.3) Act 2023 | £60,000 gross standard AA restored 2023/24 |
| MPAA | Finance (No.3) Act 2023 | £10,000 if pension flexibly accessed |
| CB rates 2026/27 | HMRC Child Benefit rate table | Eldest: £26.60/week; additional: £17.60/week (approximate, uprate ~2%) |

## HMRC Manual References

| Reference | Topic |
|---|---|
| HMRC EIM05100 | Personal Allowance reduction for high earners |
| HMRC CH2300C | High Income Child Benefit Charge overview |
| HMRC PTM044100 | Relief at Source pension mechanism |
| HMRC HS290 | Business Asset Disposal Relief (not in scope for optimise) |

## Out-of-Scope Items (Documented for Completeness)

| Item | Reason out of scope |
|---|---|
| Scottish income tax | Engine explicitly excludes Scottish bands |
| Salary sacrifice | Never available without employer confirmation; must not be assumed |
| Gift Aid ANI interaction | Planned for future version |
| Marriage Allowance | Not modelled |
| Dividend income priority ordering | Omitted; sole-trader model |
| Tapered Annual Allowance | Constraint warning only; not modelled |
| Carry-forward of unused allowances | Constraint warning only; not modelled |

## Reference Implementation Files

| File | Purpose |
|---|---|
| `reference/common.py` | Shared arithmetic: PA, income tax, HICBC formulas |
| `reference/pa_taper_reference.py` | PA taper: effective marginal rate, restoration amounts |
| `reference/hicbc_reference.py` | HICBC: standard CB rates, charge formula, elimination amount |
| `reference/pension_reference.py` | RaS mechanics: net/gross, BRL extension, IT saving |
| `reference/scenario_reference.py` | End-to-end independent scenario runner |
