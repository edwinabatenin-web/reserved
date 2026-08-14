"""Detect published tax-rule changes without changing calculation rules.

This module deliberately separates detection from adoption.  A detected
change becomes a review item; it cannot mutate ``tax_config`` or activate a
new rules version.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Optional


@dataclass(frozen=True)
class PublishedRule:
    rule_id: str
    tax_year: str
    value: Decimal
    source_url: str
    source_title: str
    published_at: str


@dataclass(frozen=True)
class RuleChange:
    rule_id: str
    tax_year: str
    configured_value: Optional[Decimal]
    published_value: Decimal
    source_url: str
    status: str = "needs_assessment"


def detect_changes(
    configured: Mapping[tuple[str, str], Decimal],
    published: list[PublishedRule],
) -> list[RuleChange]:
    """Return discrepancies for human assessment; never update config."""
    changes = []
    for item in published:
        current = configured.get((item.tax_year, item.rule_id))
        if current != item.value:
            changes.append(
                RuleChange(
                    rule_id=item.rule_id,
                    tax_year=item.tax_year,
                    configured_value=current,
                    published_value=item.value,
                    source_url=item.source_url,
                )
            )
    return changes

