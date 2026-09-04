# HICBC annual/cash handoff — synthetic composition candidate

## Identity and scope

Base: `c118dbdac2b03eeb43b386928c2416aa78fdafd3`.
Founder decisions SHA-256:
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.

This two-file, test-only candidate implements a missing local composition
exercise. It changes no product implementation, authority, feature flag,
completion map, release gate or assurance metadata. It is a candidate for a
different independent reviewer, not an assurance approval by its author.

The new test file is `tests/test_hicbc_annual_cash_handoff_journey.py`. No
applicable `AGENTS.md` was found in the repository or applicable ancestor paths.

## What is now exercised

Each positive case carries the same authentic producer output through:

1. `calculate_annual_position`, including non-zero or supported zero personal HICBC;
2. `compose_cash_ready_annual_position`, with explicit synthetic no-loan evidence;
3. `compose_annual_to_cash_position`, with separately supplied literal local
   prior-return amounts, deductions, prior payments, payment history, manual
   account observations and customer-recorded savings;
4. `compose_w8_annual_cash_customer_handoff`; and
5. `project_w8_annual_cash_presentation`, revalidating the exact source,
   evidence-reference set and as-of context.

No positive result is directly constructed, replaced, mutated or given a
fabricated authenticated owner. Account observations are invented manual
fixtures supplied independently of calculated output; no expected monetary
value is derived by calling a production calculator. None represents real
HMRC, customer, provider or bank evidence.

Earlier tests cover HICBC annual arithmetic and the purpose gate separately.
`test_w8_progressive_assurance_s2.py` uses a no-HICBC mixed annual fixture for
cash composition, while its HICBC cases call `integrate_hicbc` separately.
`test_annual_to_cash_integration.py` and the W8 handoff tests likewise use
non-HICBC annual fixtures. This candidate exercises HICBC-bearing composition,
not just coexistence or a new detached interface.

## Independent literal expectations

The synthetic person has £70,000 employment income and explicit matching
personal ANI, no pension relief, explicit no-BPA facts and complete no-loan
evidence. The settled 2026/27 personal allowance/basic-band values are £12,570
and £37,700 (`reserved/engines/tax_config.py`; existing annual arithmetic
coverage). Income tax is independently worked as £37,700 × 20% + £19,730 × 40%
= £15,432. No rules are read from the implementation to generate expected
values in the test.

The £703 personal HICBC expectation is the existing RW3-HICBC-001 literal at
£70,000 ANI and £1,406.60 Child Benefit, recorded in
`tests/test_integrated_annual_position.py`. The partner-liable comparison uses
the existing £75,000 partner / £1,054 household-charge case in the same suite:
personal HICBC is explicitly zero, not unknown. This test does not derive new
statutory rules or reopen accepted rounding evidence.

| Literal | Person liable | Partner liable |
|---|---:|---:|
| Personal HICBC | £703 | £0 |
| Annual liability | £16,135 | £15,432 |
| Less tax deducted, prior PoA and payment already made | £10,000 + £1,000 + £100 | £10,000 + £1,000 + £100 |
| Balancing amount, 31 January 2028 | £5,035 | £4,332 |
| Separate future PoA instalments | £600 + £600 | £600 + £600 |
| Total cash requirement | £6,235 | £5,532 |
| Less separately allocated savings | £500 | £500 |
| Local funding gap | £5,735 | £5,032 |

Every downstream difference is £703; HICBC and each deduction are counted once.
The separately supplied 2026/27 prior-return basis of £1,200 determines the
2027/28 PoA instalments due in January/July 2028. It is deliberately not copied
from the annual calculation. These separate same-year `LOCAL_ESTIMATE` channels
follow the existing composition contract, which requires matching tax years.
Their deliberately different amounts test channel independence; they do not
demonstrate substantive reconciliation of contradictory real-world annual and
prior-return evidence, nor establish either channel's factual authority.
A further case supplies £2,000 prior-return basis:
the annual liability and £5,035 balancing amount stay unchanged, PoA becomes
£1,000 + £1,000, total requirements £7,035 and funding gap £6,535. These are
local synthetic estimates, not confirmed bills or real completed returns.

## Failure, privacy and authority checks

Four authentic annual-input cases cover incomplete Child Benefit payment facts,
missing partner ANI, contradictory responsibility evidence and an equal-ANI
case with unknown claimant. All withhold personal HICBC and annual liability;
cash readiness remains unresolved, cash composition supplies no balancing or
funding point, and handoff creation returns no presentation. Otherwise complete
cash evidence cannot rescue incomplete annual facts.

The positive paths run for England, Wales and Northern Ireland. Exact tax year,
ruleset, geography, as-of date, annual/prior-return content bindings and opaque
handoff references are asserted. A different authentic HICBC source, wrong
as-of date and altered reference set are rejected by the exact-source projector.
The test inspects fixed W2 wording locally, without rendering a customer page.
Projected facts and wording are checked for the exact fixture partner ANI and
household-charge amounts, and for partner/household/liable-person/ANI field
names. The bounded numeric check recognises raw and comma-grouped values with
zero, one or two decimal places, with or without a currency prefix, without
rewriting or stripping characters from the actual outputs. The partner-liable
fixture explicitly has internal household information to test its exclusion.
This is not a general proof against every possible inferential disclosure.

Independent review found that the initial raw-value assertion missed formatted
ANI such as `£50,000.00`; no production leak was identified. The corrected
candidate adds 48 mutation challenges: both £50,000 and £75,000, 12 ordinary
numeric/currency presentations and both projected facts and fixed language.
Each starts with an authentic accepted handoff, then corrupts a local copy only
and proves that the same privacy assertion used in the positive journey fails.
Copies never re-enter a production composer. Five nonmatching-amount controls
protect against accidentally matching other values such as £150,000.00 or
£50,000.01. Currency characters remain unescaped in inspection serialization,
so an encoding escape cannot obscure the number's boundary.

Payment/transfer, customer-rendering and owner-authoritative restrictions remain
present. The result is a qualified local, owner-unbound handoff. The test does
not invoke the legacy synthetic owner-binding helper, authentication, a route,
provider, persistence adapter, PIS or VRP. It does not connect the manual/linked
HICBC evidence route to the annual engine, infer evidence adequacy from numbers,
or override the separate `integrate_hicbc` payment prohibition.

## Author-run verification, not independent acceptance

Python: `/private/tmp/reserved-venv/bin/python`.

New suite: **65 passed**. Affected matrix: **312 passed**, covering the new suite plus:

- `tests/test_integrated_annual_position.py`
- `tests/test_integrated_hicbc_staged_rounding.py`
- `tests/test_cash_ready_annual_position.py`
- `tests/test_annual_to_cash_integration.py`
- `tests/test_w8_annual_cash_customer_handoff.py`
- `tests/test_w8_progressive_assurance_s2.py`
- `tests/test_hicbc_integration.py`
- `tests/test_w2_customer_language_contract.py`

No full repository gate was rerun for this test-only candidate. The prior
canonical October decision remains not ready, with all 18 blockers unclosed.
This work contributes only local synthetic composition coverage. It does not
close `hicbc_annual_integration_assurance`, manual/linked privacy and retention,
representative human comprehension, owner/business membership, persistence,
provider/target evidence, payment or launch gates. No external evidence or
customer research was obtained or fabricated.
