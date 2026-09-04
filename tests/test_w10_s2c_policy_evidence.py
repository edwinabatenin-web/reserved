"""Integrity checks for the W10-S2C evidence-only dossier."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs" / "W10_S2C_POLICY_EVIDENCE_DOSSIER.md"
TEXT = DOSSIER.read_text(encoding="utf-8")

BASE = "5612f7a33f27f09d1fa988f15dfdffbe77a72705"
TREE = "4786614d7ea428e3aea1d61a72dc74d9aad6bd92"
S5A_COMMIT = "9c0760192bb2420b90e57ec7313f69bbe52cbf74"
S5A_TREE = "9b6c8891d0ab91e703f55a6a92b9d47b1f62aeac"
UNRESOLVED = (
    "refunds",
    "tax_invoicing_and_additional_presentation",
    "paid_access_surface",
    "billing_account_recovery",
    "post_settlement_dispute_chargeback_reversal_consequences",
)
REPO_SOURCES = {
    "FOUNDER_DECISIONS.md": (
        "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
    ),
    "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md": (
        "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d"
    ),
    "docs/W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md": (
        "e5911c70199727beba888175f5f31a208a4418eb16cae7978e8b52fa57d688ce"
    ),
    "docs/W10_S2A_PROVIDER_LIFECYCLE_AUTHORITY_EVIDENCE.md": (
        "48cefde6e995f160f6d0d0199cc287c4d7359f4c891e88ca251a65a661b75544"
    ),
    "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md": (
        "617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703"
    ),
    "docs/W10_S3A_ENTITLEMENT_TRANSITION_EVIDENCE.md": (
        "07fced7c7ca2f2ecb48541bb2e25db177651ecfb13dd75bda21b08a084e3bda8"
    ),
    "docs/W10_S3B_EVENT_INBOX_CONTRACT.md": (
        "4e28d354dcff1bb5e44f7c01fa17a7712c209df3010fbb722bb8fbf28ac88182"
    ),
    "docs/W10_S4A_STRIPE_DISABLED_FIRST_CONTRACT_EVIDENCE.md": (
        "da9881c5625cf1f338b8f2626d0b6c4806594508784f84c64a0160c94706111a"
    ),
}
HISTORICAL_S5A_SOURCES = {
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": (
        "abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8"
    ),
    "tests/test_w10_paid_surface_inventory.py": (
        "0d1bec99ea12496a747906b69619df0d60cd339b870042573b7dc60158c060f6"
    ),
}

HISTORICAL_MAP = "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md"
HISTORICAL_FOUNDER_DECISIONS = "FOUNDER_DECISIONS.md"
HISTORICAL_FOUNDER_DECISIONS_COMMIT = "10fb93e2e6ab567a72d2370c1603768a7ac04bb5"
HISTORICAL_ENTITLEMENT_EVIDENCE = "docs/W10_S3A_ENTITLEMENT_TRANSITION_EVIDENCE.md"
HISTORICAL_ENTITLEMENT_COMMIT = "94bd87f019dc226ec8c73f32515229189500cf06"
WRONG_MAP_COMMIT = "81ae02044cccd921d98a0d1fc2360e1c4a983ab1"


def git_blob_sha256(commit: str, relative_path: str) -> str:
    """Hash the exact repository blob reviewed at ``commit``."""

    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def assert_historical_hash(commit: str, relative_path: str, expected_hash: str):
    actual_hash = git_blob_sha256(commit, relative_path)
    assert actual_hash == expected_hash, (
        f"stale historical S2C source: {commit}:{relative_path}"
    )


def assert_live_hash(path: Path, expected_hash: str):
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual_hash == expected_hash, f"stale live S2C source: {path}"


def test_exact_base_tree_date_and_non_authority_status_are_explicit():
    assert BASE in TEXT
    assert TREE in TEXT
    assert "4 September 2026" in TEXT
    assert "candidate specialist-evidence and decision record" in TEXT
    assert "does not answer a Founder question" in TEXT
    assert "does not close or round up any key" in TEXT
    assert "strict W10 denominator remains **0/8**" in TEXT


def test_exact_integrated_repository_sources_remain_hash_bound():
    for relative_path, expected_hash in REPO_SOURCES.items():
        assert relative_path in TEXT
        assert expected_hash in TEXT
        if relative_path == HISTORICAL_MAP:
            assert_historical_hash(BASE, relative_path, expected_hash)
        elif relative_path == HISTORICAL_FOUNDER_DECISIONS:
            assert_historical_hash(
                HISTORICAL_FOUNDER_DECISIONS_COMMIT,
                relative_path,
                expected_hash,
            )
        elif relative_path == HISTORICAL_ENTITLEMENT_EVIDENCE:
            assert_historical_hash(
                HISTORICAL_ENTITLEMENT_COMMIT, relative_path, expected_hash
            )
        else:
            assert_live_hash(ROOT / relative_path, expected_hash)
    assert "fafd93c1a8fa65428bd3af19c1f35e9b47b10f38f68312721e6f2a5e14943f0d" in TEXT
    assert hashlib.sha256((ROOT / HISTORICAL_FOUNDER_DECISIONS).read_bytes()).hexdigest() != (
        REPO_SOURCES[HISTORICAL_FOUNDER_DECISIONS]
    )


def test_live_source_drift_still_fails_closed(tmp_path):
    relative_path = "docs/W10_S2A_PROVIDER_LIFECYCLE_AUTHORITY_EVIDENCE.md"
    source = ROOT / relative_path
    assert_live_hash(source, REPO_SOURCES[relative_path])

    altered = tmp_path / source.name
    altered.write_bytes(source.read_bytes() + b"\nsynthetic-drift\n")
    with pytest.raises(AssertionError, match="stale live S2C source"):
        assert_live_hash(altered, REPO_SOURCES[relative_path])


def test_only_changed_s3a_evidence_uses_exact_historical_checkpoint():
    expected_hash = REPO_SOURCES[HISTORICAL_ENTITLEMENT_EVIDENCE]
    assert_historical_hash(
        HISTORICAL_ENTITLEMENT_COMMIT,
        HISTORICAL_ENTITLEMENT_EVIDENCE,
        expected_hash,
    )
    assert hashlib.sha256(
        (ROOT / HISTORICAL_ENTITLEMENT_EVIDENCE).read_bytes()
    ).hexdigest() == "fafd93c1a8fa65428bd3af19c1f35e9b47b10f38f68312721e6f2a5e14943f0d"
    assert expected_hash != hashlib.sha256(
        (ROOT / HISTORICAL_ENTITLEMENT_EVIDENCE).read_bytes()
    ).hexdigest()


def test_historical_map_provenance_survives_reconciliation_but_rejects_forgery():
    expected_hash = REPO_SOURCES[HISTORICAL_MAP]
    live_hash = hashlib.sha256((ROOT / HISTORICAL_MAP).read_bytes()).hexdigest()

    assert live_hash != expected_hash
    assert_historical_hash(BASE, HISTORICAL_MAP, expected_hash)

    try:
        assert_historical_hash(BASE, HISTORICAL_MAP, "0" * 64)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("an incorrect historical S2C digest was accepted")

    try:
        assert_historical_hash(WRONG_MAP_COMMIT, HISTORICAL_MAP, expected_hash)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("an incorrect historical S2C commit was accepted")


def test_accepted_s5a_sources_are_verified_from_the_exact_historical_commit():
    assert S5A_COMMIT == "9c0760192bb2420b90e57ec7313f69bbe52cbf74"
    assert S5A_TREE == "9b6c8891d0ab91e703f55a6a92b9d47b1f62aeac"
    resolved_tree = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"{S5A_COMMIT}^{{tree}}"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert resolved_tree == S5A_TREE
    for relative_path, expected_hash in HISTORICAL_S5A_SOURCES.items():
        assert relative_path in TEXT
        assert expected_hash in TEXT
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{S5A_COMMIT}:{relative_path}"],
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(blob).hexdigest() == expected_hash


def test_exact_five_key_denominator_and_one_section_per_key():
    for index, key in enumerate(UNRESOLVED, start=1):
        assert TEXT.count(f"## Key {index} — `{key}`") == 1
    assert "Exactly five S2 keys remain unresolved" not in TEXT
    assert TEXT.count("`refunds`") >= 2
    assert "sixth unresolved" not in TEXT.lower()


def test_only_three_exact_founder_questions_and_no_vat_or_recovery_question():
    questions = re.findall(r"^### Q([1-3]) — ", TEXT, flags=re.MULTILINE)
    assert questions == ["1", "2", "3"]
    assert "### Q1 — discretionary refunds" in TEXT
    assert "### Q2 — exact paid-access class boundary" in TEXT
    assert "### Q3 — verified post-settlement loss and restoration" in TEXT
    assert "no Founder question for tax-invoice implementation" in TEXT
    assert "No Founder question is posed" in TEXT


def test_paid_surface_is_bound_to_accepted_evidence_but_is_not_authority():
    assert (
        "abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8"
        in TEXT
    )
    assert (
        "0d1bec99ea12496a747906b69619df0d60cd339b870042573b7dc60158c060f6"
        in TEXT
    )
    assert S5A_COMMIT in TEXT
    assert S5A_TREE in TEXT
    assert "accepted S5A evidence" in TEXT
    assert "S5 implementation not started" in TEXT
    assert "active, separate W10-S5A candidate" not in TEXT
    assert "unintegrated" not in TEXT
    assert "does not reproduce its routes" in TEXT
    assert "Satisfied local evidence" in TEXT
    assert "S5A is accepted local evidence" in TEXT
    assert "independent acceptance of the exact S5A inventory" not in TEXT
    assert "under the approved paid-surface boundary" not in TEXT
    assert "future approved paid-surface boundary" in TEXT
    assert '"routes": [' not in TEXT
    assert "`/v2/" not in TEXT


def test_primary_sources_and_claim_matrix_are_present():
    required_hosts = (
        "https://docs.stripe.com/refunds",
        "https://docs.stripe.com/customer-management",
        "https://docs.stripe.com/disputes/how-disputes-work",
        "https://www.legislation.gov.uk/uksi/2013/3134/regulation/29",
        "https://www.legislation.gov.uk/ukpga/2015/15/section/44",
        "https://www.gov.uk/invoicing-and-taking-payment-from-customers/",
        "https://www.gov.uk/guidance/record-keeping-for-vat-notice-70021",
        "https://competitionandmarkets.blog.gov.uk/2026/04/17/",
    )
    for url in required_hosts:
        assert url in TEXT
    for claim in range(1, 15):
        assert f"C-{claim:02d}:" in TEXT


def test_fail_closed_and_non_activation_boundaries_are_explicit():
    normalized = " ".join(TEXT.split())
    required = (
        "no ordinary automated or support refund is enabled",
        "never add an unannounced VAT amount",
        "billing email as login identity",
        "Unknown/contradictory cases reconcile without direct effect",
        "No route, entitlement, account, persistence, provider setting or customer data",
        "There is no SDK or network integration",
        "Provider configuration, runtime implementation and activation remain separate",
    )
    for phrase in required:
        assert phrase in normalized


def test_dossier_does_not_modify_or_claim_runtime_policy():
    assert "recommendation is not adopted" in TEXT
    assert "do not answer a Founder question" not in TEXT
    assert "W10-S2 remains **incomplete**" in TEXT
    assert "No Stripe SDK" not in TEXT  # Scope is described generically, not implemented.
