# Workstream completion-map operating rule

Declare a finite endpoint before, or early in, deep execution of each remaining
launch-critical Reserved workstream. This is a rolling control, not a request
to stop engineering and map the whole programme at once.

## When to create or refresh a map

1. Finish the current productive bounded slice.
2. Before the next major tranche, spend roughly 10–20 minutes declaring its
   objective, slices, dependencies, terminal gate and immediate next action.
3. Refresh only when authoritative evidence materially changes the denominator.
4. Continue already-authorised implementation immediately when the next action
   is clear and non-colliding.

Apply this next to the workstream approaching deep execution: remaining W1,
then each provider/HMRC/Yapily tranche, HICBC integration if still required,
UX/user testing, privacy/security/operations, and integrated E2E/release
assurance. Under Founder Decision `FD-W10-001`, the minimum subscription and
billing capability for the paid launch model is launch-critical and requires a
finite W10 completion map before deep execution.

## Minimum map

Each compact map records:

- owned outcome and explicit out-of-scope boundary;
- smallest coherent slices/packages and why each is needed;
- upstream contracts, external access and genuine Founder dependencies;
- parallel work, serial work and shared-file/contract collision rules;
- a finite, testable terminal completion gate;
- separate planned, implemented, locally verified, independently reviewed,
  integrated, launch-evidence-complete and launch-ready states;
- active/elapsed effort ranges, assumptions and critical-path contribution;
- a stable progress denominator and one immediate next action.

Do not convert ordinary package sequencing, local testing or independent review
into a Founder gate. Founder authority remains required for new scope,
consequential decisions, material exceptions, high-risk business judgement,
merge/release/go-live, production access, payment authority, credential/security
changes and destructive or irreversible action.

## Existing structures only

Reuse existing workstream/package metadata, evidence links and Control Plane
lifecycle fields. Engineering repositories and durable test/review evidence
remain the source of engineering truth.

Do not introduce a database, schema family, workflow engine, planning service,
dashboard or orchestration layer. If the current Control Plane fields cannot
hold a compact summary, keep the map as a supporting artefact rather than
redesigning the schema. Any later authoritative Control Plane update must use
its existing validation, locking and revision-controlled compare-and-swap
process.

The governing principle is: declare the endpoint early, then decompose and
execute within it without turning planning into another workstream.
