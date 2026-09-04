"""Evidence-contract test for the W9-S1A package.

This test is deterministic and repository-local. It fails when any mandatory
October flow, trust boundary, threat class, unresolved decision owner field,
canonical blocker reference, current safe-default field, or explicit
non-activation statement disappears from the two package documents. It also
proves the package does not modify readiness, release, configuration,
credential, persistence, adapter, route or template files.

The assertions target stable structured headings/IDs/fields and exact path
boundaries — never brittle prose-wide snapshots.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
DATA_FLOW_DOC = DOCS / "W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md"
DECISION_DOC = DOCS / "W9_SECURITY_DECISION_DOSSIER.md"
TEST_FILE = Path(__file__).resolve()

ALLOWED_NEW_PATHS = {
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "docs/W9_SECURITY_DECISION_DOSSIER.md",
    "tests/test_w9_security_evidence.py",
}

# ── Mandatory structured IDs ──────────────────────────────────────────────────

FLOW_IDS = [f"FLOW-{i:02d}" for i in range(1, 16)]
TRUST_BOUNDARY_IDS = [f"TB-{i:02d}" for i in range(1, 15)]
THREAT_IDS = [f"TH-{i:02d}" for i in range(1, 22)]
DECISION_IDS = [f"DEC-{i:02d}" for i in range(1, 15)]

FLOW_FIELDS = [
    "Data class",
    "Subject/owner",
    "Source",
    "Trust boundary crossed",
    "Processing purpose",
    "Allowed destination",
    "Present storage behaviour",
    "Unresolved target storage/retention/deletion",
    "Existing control",
    "Threat/failure mode",
    "Current fail-closed state",
    "Exact closure evidence",
    "Canonical blocker/reference",
]

DECISION_FIELDS = [
    "Decision ID",
    "Accountable decision owner/authority",
    "Why it blocks implementation or activation",
    "Current safe default",
    "Options",
    "Trade-offs/risks",
    "Existing constraints/evidence",
    "Exact evidence required to decide",
    "Downstream packages affected",
    "Gating",
]

CANONICAL_BLOCKER_REFERENCES = [
    "FD-W10-001",
    "FD-W10-002",
    "FD-W10-003",
    "FD-W9-001",
    "W9_COMPLETION_MAP.md",
    "W9_SECURITY_OPERATIONS_GAP_REGISTER.md",
    "W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md",
    "STRIPE_CONNECT_SPEC.md",
    "W9_PROVIDER_OUTAGE_DEGRADATION_CONTRACT.md",
    "W9_S4C_MULTI_PROVIDER_OUTAGE_EVIDENCE.md",
    "HICBC_PARTNER_SUPPORT.md",
    "MTD_SCOPE_INDICATION_EVIDENCE.md",
    "MTD_SCOPE_INDICATION_PRESENTATION_EVIDENCE.md",
    "W8_S3_GEOGRAPHY_ADMISSION_EVIDENCE.md",
    "W8_S3B_GEOGRAPHY_PROVENANCE_HANDOFF_EVIDENCE.md",
    "reserved/billing/contracts.py",
    "reserved/providers/payments/stripe_connect.py",
    "reserved_west/release_gate.py",
    "AUTHENTICATION_READINESS.md",
    "PROVIDER_BOUNDARY_ADOPTION.md",
    "PROVIDER_PRE_INDEPENDENT_AUDIT_READINESS.md",
    "INTERNAL_ANNUAL_POSITION_PERSISTENCE_READINESS.md",
    "HMRC_PAYE_FALLBACK_COMPLETION_MAP.md",
    "CUST-01",
    "CUST-02",
    "PERSIST-01",
    "PERSIST-02",
    "DATA-01",
    "DATA-02",
    "DATA-03",
    "PAYSLIP-01",
    "AUTH-01",
    "AUTH-02",
    "AUTH-03",
    "MON-01",
    "OUTAGE-01",
    "INC-01",
    "RUNTIME-01",
    "ACT-01",
    "ACT-02",
    "ACT-03",
    "RELEASE-01",
]

# Immutable reconciliation base and its stale ancestor.  The correction must
# reconcile both documents to the actual immutable candidate base without
# rewriting the historical W9-S1A introducing base.
RECONCILIATION_BASE = "10fb93e2e6ab567a72d2370c1603768a7ac04bb5"
STALE_RECONCILIATION_BASE = "79351eb02c0b82b19063689d5da460f3f07394b4"
INTRODUCING_BASE = "dd98c4421707f54eb0b564a85ee77d3ed286d79d"

# Structured semantic invariants that must survive the correction.  These are
# checked as stable tokens/fragments, not incidental prose, so the test fails on
# lost reconciliation of newly settled Founder authority, the implemented
# linked-HICBC surface, the integrated MTD core/renderer, the reviewed geography
# admission and their remaining gates.
REQUIRED_SEMANTIC_MARKERS = [
    "provisional disabled-first subscription baseline",
    "not Stripe Connect",
    "Stripe Billing, Checkout and Customer Portal",
    "payment_recovery",
    "non-extendable seven-day",
    "continuing access",
    "not provider-default behaviour",
    "observations, not entitlement authority",
    "W9-S4A",
    "provider-neutral W10",
    "FD-W9-001",
    "FD-W10-002",
    "FD-W10-003",
    # Linked-HICBC implemented surface: mutual permission, audit, withdrawal/
    # unlinking, anti-probing and minimisation.
    "hicbc_links",
    "hicbc_link_invitations",
    "hicbc_link_consents",
    "hicbc-notice-v1",
    "withdrawn_at",
    "delete_all_hicbc_links_for_user",
    "mutual affirmative permission",
    "auditable notice/version/who/when",
    "withdrawal/unlinking",
    "anti-probing",
    "minimisation",
    # MTD indication versus formal HMRC determination plus source/residence/
    # cessation/timing/exclusion boundaries.
    "formal determination",
    "source/residence/cessation/timing/exclusion",
    "gross-before-expenses",
    # E/W/NI-only geography admission with Scotland/Ireland exclusion.
    "E/W/NI",
    "Scotland and Ireland",
    "England, Wales and Northern Ireland",
]

# Bind the newly reconciled semantics to the exact structured sections that
# assert them.  A global marker search is insufficient: a section could be
# replaced with plausible placeholder prose while the same words survived in
# another part of either document.
SECTION_SEMANTIC_MARKERS = {
    "FLOW-13": [
        "version, who, when",
        "Two authenticated customers separately enabling linked HICBC",
        "minimum partner evidence",
        "withdrawal/unlinking",
        "anti-probing",
        "delete_all_hicbc_links_for_user",
    ],
    "FLOW-14": [
        "gross income before expenses",
        "formal determination",
        "source/residence/cessation/timing/exclusion",
        "authenticated routing",
        "recheck scheduling",
    ],
    "FLOW-15": [
        "England, Wales and Northern Ireland",
        "Scotland and Ireland",
        "annual tax, cash, reserve and customer presentation",
        "Customer-source acquisition",
    ],
    "TB-12": [
        "affirmative consent from both users",
        "data minimisation",
        "anti-probing controls",
        "notice/withdrawal/unlinking",
    ],
    "TB-13": [
        "gross income before expenses",
        "residence/source/Self Assessment/",
        "exemption/cessation/timing boundaries",
        "never presented as HMRC's formal",
    ],
    "TB-14": [
        "England, Wales and Northern Ireland only",
        "Scottish Income Tax",
        "Ireland/other non-UK jurisdictions",
    ],
    "TH-19": [
        "mutual affirmative consent from both users",
        "owner-scoped minimal",
        "HICBC-relevant partner evidence",
        "hypothetical/comparative/band probing",
        "withdrawal/unlinking",
    ],
    "TH-20": [
        "qualified, forward-looking indication",
        "gross income before expenses",
        "thresholds/start dates and exclusions",
        'no "MTD ready" customer language',
    ],
    "TH-21": [
        "England/Wales/Northern Ireland admission guard",
        "Scotland and Ireland excluded",
        "foreign income/SEPA-ready models do not imply geography support",
    ],
}

# Stale local-evidence claims that must never reappear after this correction.
STALE_CLAIM_FRAGMENTS = [
    "none yet implemented",
    "no provider is selected",
    "explicitly non-selected placeholder",
    "No billing provider is selected",
    "outage exercise and degraded-customer tests",
    "unresolved billing provider",
    "disabled placeholder",
    # Stale reconciliation ancestor and false current-state claims.
    STALE_RECONCILIATION_BASE,
    "No linked-HICBC persistence is wired",
    "lifecycle policy (renewal, cancellation, recovery, suspension)",
    "unresolved lifecycle policies",
    "lifecycle/refund/VAT policies",
]

NON_ACTIVATION_PHRASE = (
    "does not activate a provider, permit credentials, prove target operation, "
    "close W9, declare launch readiness, or authorise merge/release/go-live"
)


def _normalise_whitespace(value: str) -> str:
    return " ".join(value.split())

# ── Protected path categories (the package must not touch) ───────────────────

_PROTECTED_PREFIXES = (
    "reserved/providers/",
    "reserved/web/",
    "reserved/api/",
    "reserved/templates/",
    "reserved/static/",
    "reserved/auth.py",
    "reserved/database.py",
    "reserved/config.py",
    "reserved/__init__.py",
    "reserved_west/",
    "reserved/assurance_metadata.json",
    "scripts/",
    ".github/",
)

_PROTECTED_SUBSTRINGS = (
    "readiness",
    "release_gate",
    "oauth_",
    "FOUNDER_DECISIONS",
    "COMPLETION_MAP",
    "GAP_REGISTER",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    return _read(DATA_FLOW_DOC) + "\n" + _read(DECISION_DOC)


def _section_ids(text: str, prefix: str) -> list[str]:
    return re.findall(rf"^###\s+({prefix}-\d{{2}})\b", text, flags=re.MULTILINE)


def _section_blocks(text: str, prefix: str) -> dict[str, str]:
    """Return a mapping of section id -> block text (until the next heading)."""
    headings = list(re.finditer(rf"^###\s+({prefix}-\d{{2}})\b.*$", text, flags=re.MULTILINE))
    blocks: dict[str, str] = {}
    for index, match in enumerate(headings):
        section_id = match.group(1)
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        blocks[section_id] = text[start:end]
    return blocks


def _field_value(block: str, label: str) -> str | None:
    match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*(.*?)\s*\|", block, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


# ── Document presence and structure ───────────────────────────────────────────

def test_package_files_exist_and_are_the_only_new_paths():
    for path in ALLOWED_NEW_PATHS:
        assert (REPO_ROOT / path).exists(), f"missing package file: {path}"


def test_mandatory_flows_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "FLOW")
    missing = [i for i in FLOW_IDS if i not in ids]
    assert not missing, f"missing mandatory October flow(s): {missing}"


def test_each_flow_records_all_mandatory_fields():
    blocks = _section_blocks(_read(DATA_FLOW_DOC), "FLOW")
    for flow_id in FLOW_IDS:
        assert flow_id in blocks, f"missing flow block: {flow_id}"
        for label in FLOW_FIELDS:
            value = _field_value(blocks[flow_id], label)
            assert value, f"{flow_id} is missing a non-empty '{label}' field"


def test_mandatory_trust_boundaries_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "TB")
    missing = [i for i in TRUST_BOUNDARY_IDS if i not in ids]
    assert not missing, f"missing mandatory trust boundary(ies): {missing}"


def test_mandatory_threat_classes_are_present():
    text = _read(DATA_FLOW_DOC)
    ids = _section_ids(text, "TH")
    missing = [i for i in THREAT_IDS if i not in ids]
    assert not missing, f"missing mandatory threat class(es): {missing}"


def test_mandatory_decisions_are_present():
    text = _read(DECISION_DOC)
    ids = _section_ids(text, "DEC")
    missing = [i for i in DECISION_IDS if i not in ids]
    assert not missing, f"missing mandatory decision entry(ies): {missing}"


def test_each_decision_records_all_mandatory_fields_including_owner_and_safe_default():
    blocks = _section_blocks(_read(DECISION_DOC), "DEC")
    for decision_id in DECISION_IDS:
        assert decision_id in blocks, f"missing decision block: {decision_id}"
        for label in DECISION_FIELDS:
            value = _field_value(blocks[decision_id], label)
            assert value, f"{decision_id} is missing a non-empty '{label}' field"


def test_canonical_blocker_references_are_present():
    text = _combined()
    missing = [ref for ref in CANONICAL_BLOCKER_REFERENCES if ref not in text]
    assert not missing, f"missing canonical blocker reference(s): {missing}"


def test_no_duplicate_or_unexpected_section_ids():
    expected = {
        "FLOW": FLOW_IDS,
        "TB": TRUST_BOUNDARY_IDS,
        "TH": THREAT_IDS,
        "DEC": DECISION_IDS,
    }
    doc_for_prefix = {
        "FLOW": _read(DATA_FLOW_DOC),
        "TB": _read(DATA_FLOW_DOC),
        "TH": _read(DATA_FLOW_DOC),
        "DEC": _read(DECISION_DOC),
    }
    for prefix, expected_ids in expected.items():
        ids = _section_ids(doc_for_prefix[prefix], prefix)
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        unexpected = sorted(set(ids) - set(expected_ids))
        assert not duplicates, f"duplicate {prefix} section id(s): {duplicates}"
        assert not unexpected, (
            f"unexpected {prefix} section id(s): {unexpected}; "
            f"expected exactly {expected_ids}"
        )


def test_reconciled_semantic_markers_are_present():
    text = _combined()
    missing = [marker for marker in REQUIRED_SEMANTIC_MARKERS if marker not in text]
    assert not missing, f"missing reconciled semantic marker(s): {missing}"


def test_new_reconciled_sections_bind_their_own_semantics():
    data_flow = _read(DATA_FLOW_DOC)
    blocks = {}
    for prefix in ("FLOW", "TB", "TH"):
        blocks.update(_section_blocks(data_flow, prefix))

    for section_id, required_markers in SECTION_SEMANTIC_MARKERS.items():
        assert section_id in blocks, f"missing reconciled section: {section_id}"
        missing = [
            marker for marker in required_markers if marker not in blocks[section_id]
        ]
        assert not missing, (
            f"{section_id} lost section-bound semantic marker(s): {missing}"
        )


def test_stale_local_evidence_claims_are_absent():
    text = _combined()
    present = [frag for frag in STALE_CLAIM_FRAGMENTS if frag in text]
    assert not present, (
        f"stale local-evidence claim(s) still present after reconciliation: {present}"
    )


def test_reconciliation_base_is_the_immutable_candidate_base():
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        text = _read(path)
        assert RECONCILIATION_BASE in text, (
            f"{path.name} is not reconciled to the immutable candidate base "
            f"{RECONCILIATION_BASE}"
        )
        assert STALE_RECONCILIATION_BASE not in text, (
            f"{path.name} still reconciles to the stale ancestor "
            f"{STALE_RECONCILIATION_BASE}"
        )
        assert INTRODUCING_BASE in text, (
            f"{path.name} lost the historical W9-S1A introducing base "
            f"{INTRODUCING_BASE}"
        )


def test_explicit_non_activation_statement_is_present_in_both_documents():
    normalised_phrase = _normalise_whitespace(NON_ACTIVATION_PHRASE)
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        text = _normalise_whitespace(_read(path))
        assert normalised_phrase in text, (
            f"{path.name} is missing the explicit non-activation statement"
        )


# ── Exact path boundary: the package must not modify protected files ─────────

def _package_introducing_commit() -> str:
    """Return the unique commit that introduced this test file."""
    introduced = subprocess.run(
        [
            "git", "-C", str(REPO_ROOT), "log", "--diff-filter=A",
            "--format=%H", "--", "tests/test_w9_security_evidence.py",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    commits = [line.strip() for line in introduced.stdout.splitlines() if line.strip()]
    assert len(commits) == 1, (
        "W9-S1A package introducing commit is missing or ambiguous: "
        f"found {len(commits)} candidates"
    )
    return commits[0]


def _changed_paths_for_commit(commit: str) -> list[str]:
    """Return the NUL-separated path set changed by a single commit."""
    changed = subprocess.run(
        [
            "git", "-C", str(REPO_ROOT), "diff-tree", "--no-commit-id",
            "--name-only", "-r", "-z", commit,
        ],
        capture_output=True,
        check=True,
    )
    return [
        raw.decode("utf-8", errors="strict")
        for raw in changed.stdout.split(b"\0")
        if raw
    ]


def _git_changed_paths() -> list[str]:
    """Return the immutable path set of the W9-S1A introducing commit.

    A worktree status describes whichever later package happens to be under
    review, not the historical W9-S1A package.  Bind this guard to the unique
    commit that introduced its own test file so it remains valid after
    cherry-picks and while unrelated candidates are uncommitted.
    """
    commit = _package_introducing_commit()

    identity = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-list", "--parents", "-n", "1", commit],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert len(identity) == 2, "W9-S1A package commit must have exactly one parent"

    return _changed_paths_for_commit(commit)


def _package_history_commits() -> list[str]:
    """Return every commit that touched the package since its introduction.

    Includes the introducing commit and every later commit (through HEAD) that
    changed at least one authorised package path.  This is the complete
    correction-history surface over which scope drift must be rejected.
    """
    introduced = _package_introducing_commit()
    commits = [introduced]
    later = subprocess.run(
        [
            "git", "-C", str(REPO_ROOT), "log", "--format=%H",
            f"{introduced}..HEAD", "--",
        ]
        + sorted(ALLOWED_NEW_PATHS),
        capture_output=True,
        text=True,
        check=True,
    )
    commits.extend(
        line.strip() for line in later.stdout.splitlines() if line.strip()
    )
    return commits


def _is_protected(path: str) -> bool:
    if path in ALLOWED_NEW_PATHS:
        return False
    if path.startswith(_PROTECTED_PREFIXES):
        return True
    lowered = path.lower()
    return any(sub.lower() in lowered for sub in _PROTECTED_SUBSTRINGS)


def test_package_does_not_modify_readiness_release_config_or_source_files():
    changed = set(_git_changed_paths())
    missing = sorted(ALLOWED_NEW_PATHS - changed)
    unexpected = sorted(changed - ALLOWED_NEW_PATHS)
    assert not missing and not unexpected, (
        "W9-S1A package path boundary mismatch: "
        f"missing={missing}, unexpected={unexpected}"
    )


def test_package_does_not_touch_protected_files():
    changed = _git_changed_paths()
    protected = [p for p in changed if _is_protected(p)]
    assert not protected, f"W9-S1A package touched protected files: {protected}"


def test_no_scope_drift_across_package_history():
    """Every package-touching commit stays inside the three authorised paths.

    A correction commit that touches a readiness/release/completion map or a
    source/configuration file is scope drift and must fail the package, even if
    the introducing commit was clean.
    """
    for commit in _package_history_commits():
        changed = set(_changed_paths_for_commit(commit))
        drift = sorted(changed - ALLOWED_NEW_PATHS)
        assert not drift, (
            f"scope drift in package commit {commit}: {drift}; "
            f"only {sorted(ALLOWED_NEW_PATHS)} may change"
        )
