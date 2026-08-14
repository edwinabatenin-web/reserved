# Student-loan basis and rounding defect

## Finding

The incremental engine applied annual thresholds but returned penny-level amounts. That mixed annual Self Assessment liability semantics with neither the statutory whole-pound annual rounding nor the separate pay-period inputs required for payroll deductions.

## Root cause

The interface did not declare whether it represented annual liability or payroll deductions. Tests copied percentage products such as 9p at one pound above threshold without testing the official rounding rule. Historical Reserved West comparisons shared this assumption and therefore cannot validate it.

The separately packaged `reserved-engine-2.0.0` and historical West runners
remain frozen shared-lineage evidence and are excluded from the WP7 accuracy
corpus. They must not be treated as the launch engine or as an oracle for this
correction. Removing or replacing that duplicate bundle is a later deliberate
architecture task; silently synchronising it would erase useful defect history.

## Correction

The existing annual-income interface is now explicitly an incremental annual Self Assessment liability calculation. For each selected loan component it calculates the rounded-down whole-pound liability at the end and start of the interval, then takes the difference. A postgraduate component remains additional to the single applicable undergraduate component. Payroll-period deductions are not inferred: they require pay frequency, period earnings and period thresholds in a separately bounded model.

## Primary authority

- HMRC 2026/27 Student and Postgraduate Loan deduction tables: whole-pound rounding and pay-period rules.
- HMRC collection-of-student-loans manual CSLM16030: annual thresholds apply where repayments are calculated on total annual income, including self-employment.
- Self Assessment tax-calculation guidance: Student Loan and Postgraduate Loan repayments are entered in whole pounds.
