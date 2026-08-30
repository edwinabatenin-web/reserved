# Reserved v1 tax scope

Status: founder-confirmed 12 August 2026; HICBC scope amended 17 August 2026.

## Included in v1

- England, Wales and Northern Ireland taxpayers
- PAYE income, including multiple employments
- sole-trade income
- dividends and savings interest
- UK and foreign property income
- student and postgraduate loan liability, reconciled with deductions evidenced to date
- Making Tax Digital readiness
- High Income Child Benefit Charge (HICBC), as an October v1 launch target gated
  by the founder decisions of 17 August 2026 (see below and
  `docs/HICBC_PARTNER_SUPPORT.md`)

## Explicitly outside v1

- Scottish Income Tax (post-v1 Reserved West workstream)
- the Republic of Ireland/Ireland and all other non-UK jurisdictions
- Capital Gains Tax
- submission of full MTD returns

Existing Capital Gains and Scottish-tax code must not be treated as v1 scope
merely because it is present in the repository.

On 17 August 2026 the founder brought HICBC inside the October v1 scope with two
evidence routes: a manual partner-estimate journey and a privacy-preserving
linked-account consent.  HICBC may contribute to a customer's estimated total
tax, amount still to cover, set-aside recommendation and related payment journey
only where its evidence is adequate for that purpose and all applicable
assurance gates have passed.  Where partner or Child Benefit evidence is
missing, stale, materially uncertain or contradictory, Reserved must preserve
that uncertainty, request the smallest useful additional fact, show a bounded
result where supportable, or exclude HICBC from the actionable total with a
clear explanation.  Neither the manual nor the linked route may be activated or
counted as launch-ready until its applicable privacy, retention, legal,
security, customer-evidence and calculation-assurance gates have passed.

## Assurance status

The current engine is **not yet Reserved West validated** and must not be described as production-ready. Validation requires an independent reference implementation or manually derived fixtures, boundary and interaction cases, documented sources, and review of discrepancies. Reusing the same formulas in both implementations is not independent validation.
