# W9-S4D — multi-provider outage presentation evidence

## Scope

This package adds only the pure, owner-bound HTML presentation of the reviewed
W9-S4C multi-route outage coordination result. It does not add a route, retry,
reconnect operation, provider call, persistence, monitoring, logging, incident
workflow, activation path or production claim. W9-S4 and `OUTAGE-01` remain
partial.

Writable paths were limited to this document, the new service, its new
template and its focused tests. The existing W9-S4A single-route contract,
W9-S4B presentation and W9-S4C coordinator were inspected as authoritative
compatibility consumers and were not edited.

## Contract

`render_coordinated_provider_outage_status(*, routes, owner, as_of=None) -> str`
invokes the import-bound `coordinate_provider_outage` operation directly. The
coordinator remains the sole authority for exact route type/integrity, owner,
duplicate, provenance, precedence, action ordering and coordination-time
validation.

The renderer accepts only an exact, coordinator-issued
`ProviderOutageCoordination` and its exact three-field bounded projection. All
available routes produce the empty string. A degraded aggregate renders fixed
copy for the precedence-winning message and preserves every distinct action in
the S4C canonical order. Refusal, malformed input, integrity failure or an
unknown projection always produces one byte-identical generic unavailable
fragment.

Guidance is derived only from that final canonical action tuple: any action
list uses the fixed instruction to follow each applicable step, while an empty
action tuple uses the fixed no-action guidance. Consequently a no-action
precedence winner cannot contradict a lower-precedence route that contributes
an applicable customer action.

The coordinator, result projection method, fixed vocabulary and compiled
template are captured at import. Request-time execution is filesystem- and
network-inert. No owner, provider, route, timestamp, URL, payload, provenance,
credential, secret, exception text or action target reaches HTML.

## Assurance boundary

Focused tests cover every aggregate state, mixed-state precedence, all distinct
actions and canonical ordering, all-available empty output, owner and input
refusal, future/naive time, hostile subtype/reconstruction/mutation, coordinator
result issuance, collaborator rebinding, fixed refusal, escaping, accessibility,
public/import boundaries and I/O exclusions.

Still external or later: real provider outage exercises, target monitoring and
alerting, named operational ownership, runbooks, route wiring, customer UX
acceptance, staging/production evidence and release approval.

## Verification

- Focused S4D suite: `27 passed`.
- Affected W9-S4A/B/C/D plus W9 security-evidence matrix: `182 passed`.
- Full repository suite: `5,855 passed`.
- Python syntax compilation passed for the new service and tests.
