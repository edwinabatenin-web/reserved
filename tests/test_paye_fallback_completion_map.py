"""Structural and provenance checks for the PAYE fallback completion map."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs/HMRC_PAYE_FALLBACK_COMPLETION_MAP.md"
TEXT = MAP.read_text(encoding="utf-8")

SOURCE_CHECKPOINT = "3496a31c1ebcfece7e81ee593301a7c2e9370460"
INTEGRATION_CHECKPOINT = "0c8de58ad2abfe9f600b29cc71fd9e1efa51bcdb"
ACCEPTED_PARENT = "74ba3b743864cd4efbcb8df2041c095f49da1d47"
ACCEPTED_TREE = "8f2d8e103b4f60943cef89d0261766edc0761590"
ACCEPTED_PATHS = (
    "docs/PAYE_FUTURE_PAY_FORECAST_EVIDENCE.md",
    "reserved/services/paye_future_pay_forecast.py",
    "tests/test_paye_future_pay_forecast.py",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_forecast_row_preserves_delivery_state_denominator():
    row = (
        "| Explicit-confirmed-period future-pay forecast composition "
        "(detached) | Yes | Yes | Yes | No |"
    )
    assert TEXT.count(row) == 1
    assert TEXT.count("| S1 structured capture/minimisation boundary |") == 1
    assert TEXT.count("| Integrated E2E, privacy, security, operations, and launch enablement |") == 1


def test_forecast_provenance_is_exact_and_accepted_paths_are_unchanged():
    assert SOURCE_CHECKPOINT in TEXT
    assert INTEGRATION_CHECKPOINT in TEXT
    assert ACCEPTED_TREE in TEXT

    for commit in (SOURCE_CHECKPOINT, INTEGRATION_CHECKPOINT):
        identity = git("show", "--format=%H%n%T%n%P", "-s", commit).splitlines()
        assert identity == [commit, ACCEPTED_TREE, ACCEPTED_PARENT]
        paths = tuple(
            line
            for line in git("show", "--format=", "--name-only", commit).splitlines()
            if line
        )
        assert paths == ACCEPTED_PATHS


def test_map_preserves_fail_closed_forecast_limitations():
    required = (
        "submitted_confirmed_periods_only",
        "not_customer_authoritative",
        "not_established_requires_authenticated_orchestration",
        "authenticated_owner_business_reconciliation_binding_required",
        "does **not** close the canonical",
        "`paye_evidence_and_forecasting` blocker",
        "adds no provider or HMRC access",
        "persistence",
        "customer presentation",
        "tax-liability",
        "payment authority",
    )
    for phrase in required:
        assert phrase in TEXT


def test_map_does_not_overstate_coverage_or_authority():
    section = TEXT.split(
        "## Explicit-confirmed-period future-pay forecast boundary", maxsplit=1
    )[1]
    prohibited_claims = (
        "whole-year coverage is complete",
        "customer-authoritative",
        "owner/business binding is established",
        "provider access is authorised",
        "persistence is implemented",
        "launch-ready forecast",
    )
    for claim in prohibited_claims:
        assert claim not in section
