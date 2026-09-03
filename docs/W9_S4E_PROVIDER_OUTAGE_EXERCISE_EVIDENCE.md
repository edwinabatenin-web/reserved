# W9-S4E — local provider-outage exercise evidence

## Scope

This package adds a deterministic, synthetic and network-inert exercise over
the independently reviewed W9-S4A–D contracts. It covers every bounded outage
event, the required two-stage fresh-observation recovery, multi-route
precedence and customer-safe presentation. It records only bounded vocabulary
and boolean verification facts.

The package does **not** call or emulate a provider API. It does not add route
wiring, monitoring, alerting, retries, scheduling, persistence, configuration,
credentials, named operational ownership or activation. It therefore does not
close `OUTAGE-01`, W9-S4 or any target-runtime/launch gate.

## Evidence boundary

`run_provider_outage_exercise()` uses fixed synthetic identities and aware UTC
timestamps internally. Its issued result is an opaque, no-data process-local
handle. The closure-bound `as_provider_outage_exercise_summary()` projector
accepts only a genuinely issued live handle and returns canonical evidence
containing neither identities nor timestamps. It records:

- one fixed-vocabulary outcome for every existing `OutageEvent`;
- proof that every degraded state refused current use;
- `RECOVERY_PENDING` followed by `AVAILABLE` only after fresh receipt and
  explicit required-field/schema verification;
- the reviewed multi-provider precedence, canonical action order and
  customer-safe presentation behavior;
- exercised fail-closed controls for stale/future observations, cross-owner,
  subtype, low-level mutation, replay and duplicate routes.

The function captures its reviewed collaborators and exact expected
state/action/message/presentation semantics at import. The result is immutable,
non-serialisable and producer-issued. A private constructor authority is never
stored on it; a process-local weak-reference issuance registry binds the live
object identity to the one canonical immutable result. Class-method rebinding
cannot alter the closure-bound projector. Errors and invalid `repr` are
constant and do not echo identifiers, payloads, timestamps or exception
details.

## Assurance and limitations

Focused tests verify the complete deterministic matrix, recovery invariant,
negative controls, exact S4D heading/body/guidance/actions, redaction,
mutation/reconstruction rejection, collaborator binding, upstream mapping
mutation rejection and that this package introduces no filesystem, network,
route, persistence, configuration, credential, logging or scheduling calls.
The captured S4D presentation module loads its existing Jinja template at
module-import time. This package performs no request-time I/O and makes no
claim that its upstream import graph is filesystem-free.

Still required outside this local package are real sandbox/target outage and
recovery exercises, customer-journey acceptance, target monitoring and alert
routing, retry/backoff operation, named service/tax/API/security ownership,
backup/restore, rollback, incident/support exercises, privacy/security
acceptance and separate Founder release/activation authority.

Ordinary trusted Python code in the same process can replace imported module
objects; module privacy is not a security sandbox. The package instead ensures
that its own supported entry point and result validation do not consult mutable
module collaborators after binding.
