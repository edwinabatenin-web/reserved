# W10-S2F Q1/Q2 engineering-policy closure

## Status and boundary

**Authoritative source commit:** `030da8a2928473b9b5af35a158ea6ad5c5ad8e49`  
**Source tree:** `7e7430c7f3fe3dd80aeec6c06a8860f48728b520`  
**Disposition:** uncommitted candidate requiring fresh independent review and
integration.

Q1 and Q2 close as ordinary engineering policies under `FD-W10-001`,
`FD-W10-003` and `FD-OA-001`. This record creates no new Founder decision and
no free product scope. Q3 remains explicitly open for a Founder decision.

This package is a detached immutable policy record only. It performs no I/O.
No runtime paid-entitlement enforcement, route guard, refund action,
provider translation, SDK, network access, credential, persistence, migration,
activation, release or go-live authority.

## Exact source evidence

| Source | SHA-256 at the authoritative source commit | Use |
|---|---|---|
| `FOUNDER_DECISIONS.md` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | Paid October launch, no free tier, policy-versus-Founder boundary and bounded engineering authority. |
| `reserved/billing/fail_closed_launch_defaults.py` | `cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715` | Accepted pattern for disabled, non-entitling engineering defaults. |
| `docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md` | `617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703` | Exact prior ten-closed/five-unresolved partition. |
| `docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md` | `838e6c649f9925e86aca280da6917cc7e650860880204cf06b34a8fc4aa2572f` | Historical candidate classification; it expressly did not amend Founder authority. |
| `docs/W10_S5A_PAID_SURFACE_INVENTORY.md` | `5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601` | Accepted exact route inventory and four evidence classes. |
| `docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md` | `4ba7324883e6aa27081e47ffa6f1c0a1fde99a5f175375a4aae289ce5b7a5917` | Accepted reconciliation of all eleven internal/admin/legacy/unknown entries. |
| `docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md` | `221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5` | Accepted implementation evidence for the five bounded route treatments. |

The new detached contract SHA-256 is
`c758bedb6dd6812c7625a9e49f97eaa6c0440b9ef8e1a78219323f6167f14e04`.
The focused test SHA-256 is
`6d4e60977b824f711676d6a4eef4ccfeedbdc55928c26073fdd381e916b6b5e4`.

## Q1 — fail-closed refund baseline

October makes no discretionary refund promise and enables neither automated
refunds nor support-issued discretionary refunds. Mandatory statutory and
consumer rights remain overriding and require separately accepted specialist
treatment and an approved escalation path.

Any later implementation must authenticate the current Reserved owner; bind
the payment, subscription, paid period and exact money; enforce aggregate
limits and idempotency; distinguish requested, pending, requires-action,
succeeded and failed outcomes; and reconcile a verified outcome. Pending or
failed is not succeeded. A provider refund observation has no direct
entitlement effect. This policy deliberately invents no access consequence:
only a separately accepted legal policy outcome may supply one.

## Q2 — paid product surface

Because October is a paid subscription without a free tier, every route in the
accepted S5A class
`authenticated_product_candidate_pending_founder_decision` requires paid
entitlement. This is the implementation consequence of existing scope, not a
new free-versus-paid product choice.

The other accepted classes retain these exact treatments:

- `public_infrastructure_auth_legal_support` remains outside the paid gate with
  its existing controls;
- `billing_purchase_return_recovery_candidate` remains outside the paid gate
  with its existing controls;
- required exit and privacy controls remain reachable outside the paid gate
  under their existing controls; and
- `internal_admin_unknown_requiring_reconciliation` remains separate or closed
  exactly as reconciled and hardened by S5B/S5C.

No client-side hiding counts as enforcement. A later S5 implementation must
enforce the accepted boundary server-side, but this package does not start that
work.

## Exact policy and map reconciliation

The fifteen-key S1 denominator is unchanged. The six Founder-settled keys and
four earlier S2B engineering defaults remain closed; this package closes only
`refunds` and `paid_access_surface`. Exactly three policy keys remain unresolved:

1. `tax_invoicing_and_additional_presentation` — specialist gate;
2. `billing_account_recovery` — specialist/target gate; and
3. `post_settlement_dispute_chargeback_reversal_consequences` — Q3 Founder gate.

After independent acceptance and integration, the W10 completion map should:

- add the accepted W10-S2F checkpoint, tree, integration identity and exact
  path hashes;
- replace its five-unresolved/three-Founder-question current-state statements
  with three unresolved keys and Q3 as the sole current Founder question;
- record Q1 and Q2 as ordinary engineering policies rather than Founder
  decisions;
- record the S5 paid boundary as policy-settled while paid-entitlement
  enforcement remains not started; and
- keep S2 incomplete, W10 at strict `0/8`, terminal checks at `0/13`, and every
  specialist, provider, target, security, activation, release and go-live gate
  unchanged.

The live completion map is intentionally unchanged in this unreviewed package;
an accepted integration identity does not yet exist and must not be invented.

## Verification and residual gates

Verification on the uncommitted three-path candidate recorded:

- focused contract/evidence: **12 passed**;
- existing S2B/S2C/S5A/S5B/S5C affected set: **97 passed, 1 deselected**;
- expanded billing authority/core/threat/map set: **318 passed, 1
  deselected**; and
- full repository: **7,283 passed, 11 deselected**. The same unfiltered run
  produced only the 11 expected historical package-scope sentinel failures:
  each correctly rejected this other package's three uncommitted paths. Those
  sentinels pass from a clean committed checkpoint; none is a product failure
  or waived assertion.

The verification commands were:

```bash
python3 -m pytest -p no:cacheprovider tests/test_w10_q1_q2_policy_closure.py -q
python3 -m pytest -p no:cacheprovider \
  tests/test_w10_fail_closed_launch_defaults.py \
  tests/test_w10_s2c_policy_evidence.py \
  tests/test_w10_paid_surface_inventory.py \
  tests/test_w10_internal_route_reconciliation.py \
  tests/test_w10_internal_route_hardening.py -q
python3 -m py_compile reserved/billing/q1_q2_policy_closure.py
git diff --check
```

Q3, mandatory-remedy legal/finance treatment, tax/invoice treatment,
billing-account recovery assurance, runtime enforcement, provider behavior,
persistence, target/security evidence and all activation/release gates remain
open. Acceptance of this package closes none of those gates.
