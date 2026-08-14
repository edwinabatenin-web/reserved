# Stripe Connect option assessment (not selected)

The preview does not move money. Stripe is one historical option and is not the
selected reserve mechanism. The provider-neutral boundary in
`reserved/providers/payments/base.py` must remain the application contract.

Before enabling Stripe Connect:

- implement proper user authentication;
- verify onboarding and capability status from Stripe;
- validate webhook signatures;
- use deterministic idempotency keys;
- record payment, transfer and webhook events immutably;
- reconcile provider balances against Reserved's ledger;
- block all simulation routes in production;
- confirm the legal and regulatory funds-flow design.
