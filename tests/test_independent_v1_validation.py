"""Independent, synthetic validation cases for the confirmed Reserved v1 scope.

These expectations are manually worked examples derived from the cited HMRC
rules.  They deliberately do not import tax_config or use a second copy of the
production formula as an oracle.  Every monetary expectation is a literal.

Scope: England, Wales and Northern Ireland; 2026/27; non-savings income only.
No real person, account, credential or production data is used.

Primary sources (retrieved 12 August 2026):
* Income Tax bands and PA taper:
  https://www.gov.uk/government/publications/rates-and-allowances-income-tax/
  income-tax-rates-and-allowances-current-and-past
* Class 4 National Insurance:
  https://www.gov.uk/national-insurance/how-much-you-pay
* 2026/27 student-loan thresholds and rates:
  https://www.gov.uk/government/publications/employer-bulletin-december-2025/
  december-2025-issue-of-the-employer-bulletin
* Multiple student-loan plan treatment:
  https://www.gov.uk/government/publications/student-loans-a-guide-to-terms-and-conditions/
  student-loans-a-guide-to-terms-and-conditions-2026-to-2027
* HICBC thresholds and rate:
  https://www.gov.uk/child-benefit-tax-charge
* 2026/27 Child Benefit rates:
  https://www.gov.uk/government/publications/budget-2025-overview-of-tax-legislation-and-rates-ootlar/
  annex-a-rates-and-allowances
"""

from datetime import date
from decimal import Decimal
import unittest

from reserved.engines.income_tax import (
    UnsupportedStudentLoanPlanCombination,
    estimate_incremental_liability,
)
from reserved.engines.optimise import calculate_position
from reserved.engines.paye_reconciliation import (
    Completeness,
    Confidence,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
    reconcile_paye,
)


D = Decimal
TAX_YEAR = "2026/27"


def incremental(invoice, *, salary="0", profit="0", plans=None):
    return estimate_incremental_liability(
        invoice,
        {
            "day_job_salary": salary,
            "ytd_freelance_profit": profit,
            "personal_pension_contributions": "0",
            "student_loan_plans": plans or [],
        },
        tax_year=TAX_YEAR,
    )


class TestManualIncomeTaxAndSoleTradeFixtures(unittest.TestCase):
    """Literal results independently worked from taxable-income bands."""

    def test_basic_rate_full_position(self):
        # 30,000 - 12,570 = 17,430 taxable; all at 20%.
        result = calculate_position(D("30000"), D("0"))
        self.assertEqual(result.estimated_income_tax, D("3486.00"))

    def test_higher_rate_full_position(self):
        # 37,700 @ 20% + 9,730 @ 40%.
        result = calculate_position(D("60000"), D("0"))
        self.assertEqual(result.estimated_income_tax, D("11432.00"))

    def test_pa_taper_full_position_at_110000(self):
        # PA = 12,570 - (10,000 / 2) = 7,570.
        # Taxable = 102,430: 37,700 @ 20% + 64,730 @ 40% = 33,432.
        result = calculate_position(D("110000"), D("0"))
        self.assertEqual(result.estimated_income_tax, D("33432.00"))

    def test_pa_taper_increment_from_100000_to_110000_is_60_percent(self):
        # £10,000 attracts £4,000 higher-rate tax and loses £5,000 of PA,
        # adding £2,000 tax: total incremental income tax £6,000.
        result = incremental("10000", salary="100000")
        self.assertEqual(result["income_tax"], D("6000.00"))

    def test_pa_is_zero_at_125140_with_taxable_band_width_preserved(self):
        # PA is zero. 37,700 @ 20% + 87,440 @ 40% = 42,516.
        result = calculate_position(D("125140"), D("0"))
        self.assertEqual(result.estimated_income_tax, D("42516.00"))

    def test_class4_ni_crosses_lower_profits_limit(self):
        # Only £430 of the £1,000 invoice is above £12,570; £430 @ 6%.
        result = incremental("1000", profit="12000")
        self.assertEqual(result["national_insurance"], D("25.80"))

    def test_class4_ni_crosses_upper_profits_limit(self):
        # £270 @ 6% (to £50,270), then £730 @ 2%.
        result = incremental("1000", profit="50000")
        self.assertEqual(result["national_insurance"], D("30.80"))


class TestManualStudentLoanFixtures(unittest.TestCase):
    def test_plan2_boundary_and_one_thousand_above(self):
        at_threshold = incremental("1", salary="29384", plans=[2])
        above = incremental("1000", salary="29385", plans=[2])
        self.assertEqual(at_threshold["student_loan"], D("0.00"))
        self.assertEqual(above["student_loan"], D("90.00"))

    def test_multiple_undergraduate_plans_fail_closed_pending_annual_authority(self):
        # Payroll's lowest-threshold rule is not evidence for annual SA plan
        # selection, so no monetary result may be emitted for this state.
        with self.assertRaises(UnsupportedStudentLoanPlanCombination) as caught:
            incremental("5000", salary="25000", plans=[2, 5])
        self.assertEqual(caught.exception.calculation_status, "unsupported_rule")

    def test_undergraduate_and_postgraduate_are_both_due(self):
        # From £30k to £35k: £5,000 @ 9% plus £5,000 @ 6%.
        result = incremental("5000", salary="30000", plans=[2, "postgraduate"])
        self.assertEqual(result["student_loan"], D("750.00"))

    def test_annual_liability_rounds_each_component_down_to_whole_pounds(self):
        plan2_below_one_pound = incremental("29386", plans=[2])
        plan2_one_pound = incremental("29397", plans=[2])
        pgl_below_one_pound = incremental("21001", plans=["postgraduate"])
        pgl_one_pound = incremental("21017", plans=["postgraduate"])
        self.assertEqual(plan2_below_one_pound["student_loan"], D("0.00"))
        self.assertEqual(plan2_one_pound["student_loan"], D("1.00"))
        self.assertEqual(pgl_below_one_pound["student_loan"], D("0.00"))
        self.assertEqual(pgl_one_pound["student_loan"], D("1.00"))
        self.assertEqual(
            plan2_one_pound["student_loan_basis"],
            "annual_self_assessment_liability",
        )


class TestManualHicbcInteractionFixtures(unittest.TestCase):
    # One child: £27.05 x 52 = £1,406.60 annual Child Benefit.
    ANNUAL_CB = D("1406.60")

    def test_hicbc_exact_thresholds_and_midpoint(self):
        self.assertEqual(calculate_position(D("60000"), D("0"), self.ANNUAL_CB).hicbc, D("0"))
        self.assertEqual(calculate_position(D("70000"), D("0"), self.ANNUAL_CB).hicbc, D("703.00"))
        self.assertEqual(calculate_position(D("80000"), D("0"), self.ANNUAL_CB).hicbc, D("1406.00"))

    def test_hicbc_whole_percentage_boundaries(self):
        expected = {
            "60001": "0.00",
            "60199": "0.00",
            "60200": "14.00",
            "60201": "14.00",
            "79999": "1391.00",
            "80000": "1406.00",
            "80001": "1406.00",
        }
        for ani, charge in expected.items():
            with self.subTest(ani=ani):
                result = calculate_position(D(ani), D("0"), self.ANNUAL_CB)
                self.assertEqual(result.hicbc, D(charge))

    def test_pension_reduces_ani_and_hicbc_at_70000(self):
        result = calculate_position(D("70000"), D("10000"), self.ANNUAL_CB)
        self.assertEqual(result.adjusted_net_income, D("60000"))
        self.assertEqual(result.hicbc, D("0"))
        self.assertEqual(result.estimated_income_tax, D("13432.00"))

    def test_pa_taper_and_pension_interaction_at_110000(self):
        # No pension: £33,432. £10k gross RaS pension restores PA and extends
        # the basic-rate band to £47,700, producing £29,432: £4,000 reduction.
        before = calculate_position(D("110000"), D("0"))
        after = calculate_position(D("110000"), D("10000"))
        self.assertEqual(before.estimated_income_tax - after.estimated_income_tax, D("4000.00"))


class TestIndependentPayeEvidenceFixtures(unittest.TestCase):
    def test_two_employments_sum_only_selected_direct_evidence(self):
        evidence = [
            PayeEvidence(EvidenceKind.HMRC, "2026-27", "1800", employment_id="job-a", observed_on=date(2026, 8, 10), effective_through=date(2026, 8, 10), evidence_id="job-a", representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE, completeness=Completeness.COMPLETE_FOR_REPRESENTATION),
            PayeEvidence(EvidenceKind.HMRC, "2026-27", "700", employment_id="job-b", observed_on=date(2026, 8, 10), effective_through=date(2026, 8, 10), evidence_id="job-b", representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE, completeness=Completeness.COMPLETE_FOR_REPRESENTATION),
        ]
        result = reconcile_paye("10000", evidence, tax_year="2026-27", as_of=date(2026, 8, 12))
        self.assertEqual(result.tax_paid_to_date, D("2500.00"))
        self.assertEqual(result.estimated_remaining_liability, D("7500.00"))
        self.assertIs(result.confidence, Confidence.HIGH)

    def test_aggregate_is_not_added_to_employment_level_evidence(self):
        evidence = [
            PayeEvidence(EvidenceKind.DOCUMENT, "2026-27", "2500", observed_on=date(2026, 8, 10), effective_through=date(2026, 8, 10), evidence_id="aggregate", representation=EvidenceRepresentation.EMPLOYMENTS_AGGREGATE_CUMULATIVE, completeness=Completeness.COMPLETE_FOR_REPRESENTATION, covered_employment_ids=("job-a", "job-b")),
            PayeEvidence(EvidenceKind.HMRC, "2026-27", "1800", employment_id="job-a", observed_on=date(2026, 8, 10), effective_through=date(2026, 8, 10), evidence_id="job-a", representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE, completeness=Completeness.COMPLETE_FOR_REPRESENTATION),
            PayeEvidence(EvidenceKind.HMRC, "2026-27", "700", employment_id="job-b", observed_on=date(2026, 8, 10), effective_through=date(2026, 8, 10), evidence_id="job-b", representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE, completeness=Completeness.COMPLETE_FOR_REPRESENTATION),
        ]
        result = reconcile_paye("10000", evidence, tax_year="2026-27", as_of=date(2026, 8, 12))
        self.assertEqual(result.tax_paid_to_date, D("2500.00"))
        self.assertTrue(any("double counting" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
