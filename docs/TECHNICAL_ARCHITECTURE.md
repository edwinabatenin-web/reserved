# Reserved™ Technical Architecture

## October launch scope

Reserved presents a factual view of recorded income, estimated liabilities and
the estimated amount reserved for tax so far. The launch version combines the former
“Alpha” and “Beta” labels into one controlled private-beta release.

## Architectural layers

- `web/`: HTML routes and presentation.
- `api/`: JSON endpoints.
- `engines/`: deterministic liability calculations.
- `services/`: product workflows and composition.
- `providers/`: external banking, payments and accounting adapters.
- `models/`: canonical data structures.
- `repositories/`: database boundaries.
- `templates/` and `static/`: the Reserved design system and user interface.

## Launch modules

- Sole-trader income estimate.
- Income Tax, Class 4 National Insurance and student-loan estimate.
- Tax-reserved-so-far allocation presentation; no claim about disposable income.
- Capital Gains code is dormant and excluded from customer-facing v1 scope.
- Documented connection surfaces for Yapily and Stripe.
- Documented placeholders for FreeAgent, Xero and QuickBooks.

## Explicitly not implied by the preview

- Tax filing or professional advice.
- Automatic CGT calculations for complex share or crypto matching.
- Live transfer or safeguarding functionality.
- Active accounting-provider synchronisation.
