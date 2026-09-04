# HICBC manual annual-preview frontend — implementation candidate

Base `0e842e750daa30f94adb3f18b1e1b4f91b424aee`; branch
`astra/hicbc-annual-preview-frontend`. Founder Decisions remain unchanged,
SHA-256 `78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
This implements the owner's exact eight-path frontend authority within the
existing October manual HICBC journey. It is pending a different independent
reviewer, not self-acceptance, activation or a new W8 slice.

## Actual customer path

The existing authenticated `/v2/hicbc/` page conditionally includes the new form
and its same-origin script. Eligibility is derived server-side from both existing
HICBC switches and the existing production detector. The panel/script are absent
when either switch denies or either production signal is present. No route,
flag, authentication rule, CSRF exemption or runtime paid-access wiring is added.
The existing preview POST handler and linked refusal are unchanged.

The form is visibly separate from the legacy profile-based current estimate and
the existing saved Child Benefit/partner controls. It says that the new entries
do not update that estimate, are not saved as an annual position, and do not
provide total tax, money-to-put-aside, payment or filing guidance. It collects
only first-person annual facts, not partner operands, owner IDs or destination
URLs. Existing saved manual partner and Child Benefit evidence remain the source
for responsibility determination and retain their limitations.

All twelve existing canonical monetary fields start blank. Explicit zero is
required when irrelevant; missing, negative, over-precise, exponent, padded or
otherwise noncanonical strings do not submit. Geography is explicitly chosen.
Four initially unticked confirmations cover the full tax year including known
future amounts, UK residency, employment/pension basis, and no other unresolved
ANI adjustments plus the stated residential-finance meaning. Unsupported or
uncertain answers produce an accessible non-result, not automatic zero or an
inferred confirmation. The server remains authoritative for admissibility.
Configured tax-year context is used rather than a hard-coded display year.

On keyboard/form submission the script sends unchanged monetary strings as the
existing canonical JSON schema to the fixed same-origin annual-preview endpoint
with the real Flask-WTF token. It has no financial browser storage, logging,
analytics, provider call or new persistence. Browser-managed form restoration
and ordinary in-memory inputs are not secure erasure guarantees; autocomplete
is disabled and navigation clears the displayed result.

The corrected renderer admits the exact existing customer-view field set,
bounded types and producer status/amount relationships, then displays only year,
headline, own charge or bounded possible charge,
and existing messages through text nodes. Existing determinate results may
carry identical low/high bounds; those are preserved without inventing another
calculation. Internal annual results, own ANI, raw request/error bodies and
extra response fields are not rendered. Non-JSON, redirect, malformed, failed
and network responses clear the result and produce fixed non-echoing feedback.
The producer's existing enum combinations are checked: determinate calculated
results need matching point/bounds, partner-liable calculated results and
not-applicable no-charge results have zero own charge, and material uncertainty
or ambiguity cannot carry a point. Insufficient facts legitimately permits
either no amounts or the existing zero-to-possible-charge range; it is not
incorrectly reduced to an all-null-only rule. Ranges must be ordered, using exact
integer comparison of already-formatted pence, not tax arithmetic. The fresh
endpoint has no previous-result household transition. Headline text is bound to
the existing producer mapping, not newly authored policy. HTTP 409 must match
the existing canonical closed-view statuses, null amounts, no partner-evidence
claim and original missing-own-income message. A merely nulled determinate view
cannot render. There is no alternate endpoint or linked manual fallback.

Input/change/reset/navigation and new submissions clear prior results. An abort
attempt plus a monotonically changing request generation prevents older fetch
or JSON completions from reviving results after edits, newer requests or failure.
An already delivered result is not a continuously synchronised link-status feed:
subsequent linked/refusal and revocation decisions remain enforced by the
unchanged server's transaction boundary, not by new frontend policy.

## Author-run verification

`tests/test_hicbc_annual_preview_frontend.py`: **60 passed**.
Tests parse the actual Flask-rendered form, execute the actual production
JavaScript in a persistent Node process, capture its generated request, dispatch
that request with its actual CSRF token through Flask's synthetic test client,
then feed the actual response back into the same JavaScript process to exercise
rendering. This is not a server-only or source-string substitute.

The intentionally small DOM/event harness is not a browser. It implements the
used text-node and event APIs, rejects unsafe HTML writes and storage access,
and deliberately ignores abort so stale-generation behavior is independently
exercised. It does not prove browser layout, native form behavior, assistive
technology behavior, WCAG conformance or customer comprehension. Bundled Node
is available; bundled Playwright has no installed Chromium binary and no local
Chrome was found. Nothing was installed and no real browser/visual acceptance
is claimed in this candidate.

Synthetic tests establish blank inputs, exact strings and confirmations,
unknown/unsupported refusal, live switches and production signals, auth and
CSRF, unchanged legacy distinction, actual mixed-input £703 own-charge result,
£0–£703 range, missing evidence, no database mutation, raw/formatted operand
exclusion from new presentation, hostile text escaping and extra-field refusal.
The original 35 cases remain, with the hostile-text escaping fixture moved from
headline to messages because forged headlines now fail admission. Added
executable hostile fixtures reject status/amount contradictions, unknown enums,
reversed actual bounded ranges, mismatched point/bounds, forged headlines and
noncanonical 409 presentation. Positive actual producer fixtures preserve
no-charge, partner-liable, materially uncertain and insufficient-facts ranges.
Blank-after-success clears on an input event and also on submission when a
programmatic value change has emitted no input event. The form uses `novalidate`
and its own submit listener, so native constraint validation does not pre-empt
that clear/refusal behavior; no production clearing change was necessary.

Tests exercise active-link refusal without consent, revocation, relinking,
out-of-order fetch, delayed JSON, edits, reset/navigation, and network/error
non-results. Existing runtime tests independently retain the fuller consent,
partial-evidence, owner/year isolation and transactional race coverage.

The £703 expectation reuses the accepted literal fixture: mixed annual facts
produce £70,000 own ANI and £1,406.60 Child Benefit produces the already settled
£703 charge. The frontend performs no tax arithmetic or new legal interpretation.

Requested affected matrix: **326 passed, zero failed**:

```text
tests/test_hicbc_annual_preview_frontend.py
tests/test_hicbc_annual_source_runtime.py
tests/test_internal_tax_boundary.py
tests/test_w8_progressive_assurance_s2.py
tests/test_hicbc_partner_privacy.py
tests/test_hicbc_linked_account.py
tests/test_hicbc_linked_corrections.py
tests/test_w10_paid_surface_inventory.py
tests/test_w10_internal_route_reconciliation.py
```

Run with `/private/tmp/reserved-venv/bin/python -m pytest` followed by those paths.
The harness uses `node` on PATH or the existing bundled local runtime. It does
not skip executable checks or install dependencies. S5A changes only the current
`hicbc.py` hash; S5B changes only its current S5A hash references. All historical
source pins, route counts/classes, completion states and denominators remain.
The full canonical gate was not rerun; this matrix is not that gate.

## Unclosed gates

Independent implementation/privacy/security review, actual customer language
and journey evidence, accessibility/browser/target evidence, privacy notice,
retention and lawful-basis/legal review, and explicit production activation
remain open. This introduces no consent or retention policy. Linked annual-source
and anti-probing engineering remain unresolved; existing linked evidence stays
partial and the manual preview refuses any active link. No annual/reserve/payment
publication, durable owner-bound annual position, provider integration, paid
entitlement or October/W8 launch-readiness claim follows from this package.

A separate existing source limitation was observed during fixture preparation:
saved claimant `none` is forwarded by the web helper but rejected by the engine's
person/partner/None claimant validator, so the annual endpoint returns its closed
400 view even with zero benefit. This is not a frontend regression or fixed by
this package; it was reported to the owner for separate disposition. The valid
zero-benefit/person producer shape positively covers no-charge rendering here.
