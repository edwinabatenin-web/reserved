# W2 customer-language representative-user test protocol

Status: planned, non-production research. No session or representative-user validation is claimed. The synthetic gallery supports evidence collection; it does not close W2 terminal gate 12.

## Purpose and participants

Test whether intended customers can correctly distinguish HMRC-confirmed obligations from local estimates, understand set-aside states, and understand the limits and risks of claims to reduce. Recruit participants representative of the intended Self Assessment audience, including a mix of experience with Payments on Account, confidence with tax language, digital confidence, age and accessibility needs. Do not use real tax records; collect only the minimum consented research metadata needed for sampling.

## Moderated session

Obtain research consent and explain that every case is fictional and non-production. Present each case in isolation in a pre-selected, counterbalanced order. Show only the neutral participant heading (`Case A` through `Case G`); fixture `moderator_label` values are moderator-only and must not be displayed, read aloud or explained before the participant has completed their response to that case. Ask the same neutral prompts for every case:

1. What, if anything, does this page tell you?
2. Would you rely on any of these figures? Why or why not?
3. What would you do next, if anything?
4. Is any wording unclear or open to more than one interpretation?

Then use open comprehension checks: “Where did that information come from?”, “How does the set-aside compare with the obligations?”, “What does this say about paying or moving money?”, and, where shown, “Who starts a claim to reduce, and what could happen if it is reduced too far?” Do not correct an answer until that case is complete. Rotate case order and avoid wording that names the expected interpretation.

## Evidence and severity

With consent, capture case order, verbatim answer or faithful contemporaneous note, observed hesitation, requested assistance, browser/device, zoom level, assistive technology, moderator interventions and the participant’s final interpretation. Use pseudonymous session identifiers and the approved research retention process; never put participant data in this fixture or repository.

Classify each observed misinterpretation:

- Critical: treats an estimate as an HMRC bill; treats surplus as spendable cash; believes the view authorises payment/transfer; believes a claim was filed automatically; or acts on suppressed money.
- Major: misses a gap, exact coverage, customer initiation, or the under-reduction interest warning in a way likely to change a decision.
- Minor: wording friction or hesitation that does not alter the final interpretation or intended action.

Record the evidence for each classification and have a second researcher independently review every critical or major finding.

## Accessibility and browser checks

Run the gallery with keyboard only at 200% and 400% zoom/reflow, with a screen reader used by at least one representative participant where feasible, and with forced colours/high contrast where relevant. Cover the supported browser and device matrix, including a narrow mobile viewport. Check reading order, headings, status announcement, focus visibility, text resizing and that meaning does not depend on colour. Record environment and defects; do not infer accessibility from automated checks alone.

## Stopping rules and gate 12

Pause the affected case immediately if wording prompts a participant toward a real payment, transfer, filing, disclosure of real tax data, or distress. Stop the study for any privacy or safeguarding issue. Stop analysis and return the presentation to review if one critical interpretation occurs, the same major interpretation recurs, moderator intervention is needed to obtain the safe meaning, or an accessibility barrier prevents task completion. Do not replace or discount stopped sessions to improve results.

Gate 12 may close only after the pre-agreed representative sample and accessibility/browser coverage are complete, every required state has been tested, no unresolved critical or major misinterpretation remains, findings and counterevidence are traceable to consented session records, and an independent authorised reviewer records acceptance against the W2 completion standard. Otherwise gate 12 remains open, including when sessions are incomplete, the sample is not representative, evidence is synthetic, findings are unresolved, or only internal/team review exists. This kit and its automated tests are preparation evidence only; they are not UX approval, assurance, W2 completion or launch readiness.

## Gallery use

From the repository root, render only to an existing directory outside the repository, for example:

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/render_w2_customer_language_research_kit.py /tmp/w2-customer-language-case.html --case hmrc-exact-gap
```

Repeat `--case` to supply the complete pre-selected order for a session. A subset is suitable for isolated presentation; a seven-case gallery must be a permutation containing every case exactly once. Use a new output path for every render: the renderer refuses to overwrite any existing path. Review the output locally without serving it through an application route. Preserve the fixture version, selected neutral case order and gallery hash alongside the research plan so the tested stimulus is identifiable.
