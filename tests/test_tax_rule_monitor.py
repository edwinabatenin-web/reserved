from decimal import Decimal

from reserved.assurance.tax_rule_monitor import PublishedRule, detect_changes


def _published(value="12570", tax_year="2026/27"):
    return PublishedRule(
        rule_id="personal_allowance",
        tax_year=tax_year,
        value=Decimal(value),
        source_url="https://www.gov.uk/income-tax-rates",
        source_title="Income Tax rates and Personal Allowances",
        published_at="2026-04-06",
    )


def test_matching_rule_produces_no_alert():
    configured = {("2026/27", "personal_allowance"): Decimal("12570")}
    assert detect_changes(configured, [_published()]) == []


def test_changed_rule_is_flagged_not_applied():
    configured = {("2026/27", "personal_allowance"): Decimal("12570")}
    changes = detect_changes(configured, [_published("13000")])
    assert configured[("2026/27", "personal_allowance")] == Decimal("12570")
    assert changes[0].status == "needs_assessment"
    assert changes[0].published_value == Decimal("13000")


def test_new_tax_year_is_flagged_for_assessment():
    changes = detect_changes({}, [_published(tax_year="2027/28")])
    assert changes[0].configured_value is None

