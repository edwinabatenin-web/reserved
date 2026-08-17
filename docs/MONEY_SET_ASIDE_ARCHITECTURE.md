# Money set-aside architecture

## Status

Founder decision (15 August 2026): v1 includes customer-authorised payment
initiation (PIS) from the customer's current account to a designated account
owned by that customer. No money moves without the customer's explicit approval
and bank authentication, and Reserved does not hold customer funds. The exact
provider solution remains **TBC** and conditional on acceptable Yapily
commercials, consent/status handling, same-owner destination controls, security
review and launch assurance. Until that conditional journey is implemented and
approved, Reserved estimates and tracks an amount and must not initiate a
payment or imply that a provider has been selected.

## Decision boundary

Keep these capabilities independent:

1. tax calculation;
2. tax already paid/deducted reconciliation;
3. amount the user records as set aside;
4. read-only account information (AIS);
5. optional, separately authorised payment initiation (PIS).

Yapily AIS consent cannot be reused as payment consent. PIS/VRP introduces a
separate customer journey, provider product, bank coverage, licensing and risk
assessment. Stripe is one historical option, not an architectural default.

## Reversible design

`MoneyMovementProvider` is an optional boundary; `TrackOnlyProvider` remains the
safe current state until the conditional v1 customer-authorised PIS journey is
implemented and approved. Adapters implement customer-authorised one-off bank
payment (v1 PIS) or, post-v1, sweeping VRP or another approved mechanism,
without changing the tax engine.

Core records use provider-neutral identifiers and states. Provider credentials,
account identifiers and consent tokens must not enter tax calculation payloads.
Every payment-capable implementation must require explicit user authorisation,
idempotency, status reconciliation, auditable events and tested failure flows.

## Current prohibitions

- no automatic transfers;
- no payment initiation using AIS consent;
- no assumption that Reserved holds customer funds or supplies an account;
- no production credentials or real bank accounts in testing;
- no Stripe/Yapily-specific columns in the core set-aside record;
- no claim that an estimated remainder is available or safe to spend.

