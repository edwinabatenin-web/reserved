# Tax-rule monitoring and controlled adoption

Rule monitoring informs people; it does not change tax calculations automatically.

## Workflow

1. **Detect** — periodically compare recorded rules with current primary HMRC/GOV.UK publications, including Budget and Finance Bill announcements.
2. **Flag** — create a review item containing the tax year, old value, published value, source and publication date.
3. **Assess** — a competent reviewer confirms commencement, territorial and income-type scope, transitional provisions, and whether legislation is final.
4. **Test** — add or revise boundary, interaction and regression cases in a new rules version.
5. **Approve** — record named approval and effective tax year. Announcements and draft legislation cannot be silently promoted to active rules.
6. **Deploy** — release through normal reviewed deployment and retain the prior version for reproducibility.

`reserved.assurance.tax_rule_monitor` implements the safe detect/flag boundary. It accepts structured observations gathered from authoritative sources and returns discrepancies. It has no write path to the calculation configuration.

## Source hierarchy

Use enacted legislation and HMRC/GOV.UK technical material first; then official Budget/Finance Bill material for planned changes. Store the direct URL and observed publication date. Search-engine summaries, articles and model-generated recollections are not rule sources.

## Operating cadence

- scheduled monthly review outside fiscal-event periods;
- review within two working days of a Budget, Autumn Statement, Finance Bill publication or relevant HMRC update;
- pre-tax-year completeness review and post-6-April confirmation;
- urgent review where an official correction affects an active year.

