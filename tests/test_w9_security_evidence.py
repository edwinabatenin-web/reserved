"""Evidence-contract test for the W9-S1A model and W9-S1B reconciliation.

This test is deterministic and repository-local. It fails when any mandatory
October flow, trust boundary, threat class, unresolved decision owner field,
canonical blocker reference, current safe-default field, exact source binding,
or explicit non-activation statement disappears from the evidence documents. It also
proves the package does not modify readiness, release, configuration,
credential, persistence, adapter, route or template files.

The assertions target stable structured headings/IDs/fields and exact path
boundaries — never brittle prose-wide snapshots.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
DATA_FLOW_DOC = DOCS / "W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md"
DECISION_DOC = DOCS / "W9_SECURITY_DECISION_DOSSIER.md"
GAP_DOC = DOCS / "W9_SECURITY_OPERATIONS_GAP_REGISTER.md"
TEST_FILE = Path(__file__).resolve()

S1A_INTRODUCING_PATHS = {
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "docs/W9_SECURITY_DECISION_DOSSIER.md",
    "tests/test_w9_security_evidence.py",
}
S1_EVIDENCE_PATHS = S1A_INTRODUCING_PATHS | {
    "docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md",
}
LIVE_PROVENANCE_RECONCILIATION_PATHS = {
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
    "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
    "docs/W10_S7A_BILLING_THREAT_MODEL.md",
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "tests/test_w10_billing_threat_model.py",
    "tests/test_w10_internal_route_reconciliation.py",
    "tests/test_w10_paid_surface_inventory.py",
    "tests/test_w9_security_evidence.py",
}
LIVE_PROVENANCE_RECONCILIATION_COMMIT = (
    "794fd29481ac40e54fd07406601736d5f1e038e8"
)
LIVE_PROVENANCE_RECONCILIATION_PARENT = (
    "c5e560045ed3d62f02c894e931464c3d7294e99f"
)
S5C_EVIDENCE_REFRESH_PARENT = "3c63e64e478957ce04ee1154363c2eae94b82b30"
CURRENT_ROUTES_COMMIT = "c5e560045ed3d62f02c894e931464c3d7294e99f"
CURRENT_ROUTES_TREE = "bcdbec9108c3c0904139eca278c03fe0f6914db2"
HISTORICAL_S5C_ROUTES_SHA256 = (
    "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed"
)
S5C_EVIDENCE_REFRESH_PATHS = {
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
    "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
    "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md",
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "docs/W9_SECURITY_DECISION_DOSSIER.md",
    "tests/test_w10_internal_route_reconciliation.py",
    "tests/test_w10_paid_surface_inventory.py",
    "tests/test_w10_s2c_policy_evidence.py",
    "tests/test_w9_security_evidence.py",
}
ENTITLEMENT_EVIDENCE_RECONCILIATION_COMMIT = (
    "4e1f226e2109257e46e5865fe471564df1758246"
)
ENTITLEMENT_EVIDENCE_RECONCILIATION_PARENT = (
    "48a97042fc0e17997bf2d23a4687e79c20b74b9e"
)
ENTITLEMENT_EVIDENCE_RECONCILIATION_PATHS = {
    "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md",
    "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
    "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md",
    "docs/W10_S4B_CHECKOUT_INTENT_CONTRACT.md",
    "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md",
    "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md",
    "docs/W10_S7A_BILLING_THREAT_MODEL.md",
    "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
    "tests/test_w10_billing_account_recovery_contract.py",
    "tests/test_w10_billing_threat_model.py",
    "tests/test_w10_checkout_intent_contract.py",
    "tests/test_w10_fail_closed_launch_defaults.py",
    "tests/test_w10_payment_recovery_presentation.py",
    "tests/test_w10_portal_intent_contract.py",
    "tests/test_w10_s2c_policy_evidence.py",
    "tests/test_w10_tax_invoice_prerequisite_contract.py",
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

# Immutable reconciliation base and its stale ancestors.  The correction must
# reconcile all three evidence documents to the exact current integration without
# rewriting the historical W9-S1A introducing base.
RECONCILIATION_BASE = "81ae02044cccd921d98a0d1fc2360e1c4a983ab1"
RECONCILIATION_TREE = "ac5922e7aae0016a54f78a8645a244ac83eae0d2"
STALE_RECONCILIATION_BASES = (
    "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
    "79351eb02c0b82b19063689d5da460f3f07394b4",
)
INTRODUCING_BASE = "dd98c4421707f54eb0b564a85ee77d3ed286d79d"

INTEGRATED_COMMIT_IDENTITIES = {
    "W9-S3A": "c489c25bab669c64e1c11d28caf29fcde9678fdd",
    "W9-S3B": "110a90043dfc770c70059482be9d7b7e237749a6",
    "W9-S4A": "58fb28267afb5a7b766d8f1e7bbcdbda8d517e81",
    "W9-S4B": "2cb3d43fbc59d75226c7b5d1a4f5f77addd24319",
    "W9-S4C": "43e4671a3ac59edd3620a950157b2f483e8e209a",
    "W9-S4D": "8f26ee74138432f00398eaa4297f8a7ef5817734",
    "W9-S4E": "1a277b60f3bc9da02d52fd1a869f91a35ce303fe",
    "W10-S2A": "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
    "W10-S2B": "1033c9fbef008dcd33125a0b14e7fb18b8846d19",
    "W10-S3A": "b990d514a929c37b3f999137a0e383d05c37f0df",
    "W10-S3B": "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
    "W10-S4A": "2ad4a63dd1f10ba38859050b47245c28390667d8",
    "W10-S5A": "9c0760192bb2420b90e57ec7313f69bbe52cbf74",
    "W10-S5B": "051ae665a0cc94f6e9cdbbc728c621825c7769fe",
    "W10-S5C": "3c63e64e478957ce04ee1154363c2eae94b82b30",
}

SOURCE_SHA256 = {
    "reserved/annual_position_persistence_contract.py": "da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469",
    "reserved/annual_position_repository_contract.py": "fa033039500b97bab04f3a047c07ad661c14c49d6167d65396d4d9ab0227053e",
    "reserved/providers/operational_resilience.py": "2ce9c42402fd79bbada2c2e28bc0594d377fe1cbec8825e4d44967c34d2739de",
    "reserved/services/provider_outage_presentation.py": "bd16596d6d63cffead6539e8e810949863b3902affb018b75b913e56e7d6192f",
    "reserved/services/provider_outage_coordination.py": "aa91dcb6aa24a63aeb8c3248e08478d5c0b3b612c879d6cfc2cdaac4582419af",
    "reserved/services/provider_outage_coordination_presentation.py": "93679ad3daac25de54fa60dc980a574a0859e1352b71bd8b59b79ceaba3c8f1a",
    "reserved/assurance/provider_outage_exercise.py": "4f6acc2e688fdd20e7e723bb8eeaf5e8d6928baa10acc69503489f6d4d4cc61f",
    "reserved/billing/provider_lifecycle_authority.py": "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
    "reserved/billing/fail_closed_launch_defaults.py": "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
    "reserved/billing/entitlement_core.py": "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415",
    "reserved/billing/event_inbox_contract.py": "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
    "reserved/billing/stripe_disabled_first_contract.py": "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "64894dbfb74b0faa16b8b4c824f79b021675caf57a391c9a19c269a0f914c7c9",
    "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md": "3cbf1325ef388412dee1a766c13965a00347ba0f517417318b33338f6d261f56",
    "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md": "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5",
    "reserved/web/routes.py": "cbac0af6c8e7fa7ef43017ba54dab0186330b556a6c9dd946e8cfcbd3fa0e9fd",
    "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
    "docs/W9_S1_INDEPENDENT_REVIEW_EVIDENCE.md": "b824cdd5d493fadcb3c3cb476da78fd12265fe9b6d5fb0b3de4051cd569f663b",
}

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
    "W9-S3A",
    "W9-S3B",
    "Provider-neutral W10",
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
    "five exact policy keys",
    "provider authenticity",
    "no physical schema",
    "W10_S5A_PAID_SURFACE_INVENTORY.md",
    "W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
    "W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md",
    "legacy/internal route hardening",
    "paid-entitlement enforcement remain **not started**",
]

# Bind the newly reconciled semantics to the exact structured sections that
# assert them.  A global marker search is insufficient: a section could be
# replaced with plausible placeholder prose while the same words survived in
# another part of either document.
SECTION_SEMANTIC_MARKERS = {
    "FLOW-06": [
        "reserved/annual_position_persistence_contract.py",
        "reserved/annual_position_repository_contract.py",
        "upstream-admission and persistence authority",
        "physical schema, migration, durable repository or database I/O",
    ],
    "FLOW-07": [
        "admitted S3A/S3B annual/cash contract boundary",
        "no durable repository",
        "do not authorise storage",
    ],
    "FLOW-09": [
        "S2B",
        "S3B",
        "S5A",
        "five exact policy keys",
        "no provider authenticity, persistence or entitlement authority",
        "remains inventory evidence",
        "accepted S5C",
        "closes or redirects the reviewed legacy/internal paths",
        "without paid-entitlement enforcement",
        "billing-account recovery",
        "post-settlement dispute/chargeback/reversal consequences",
    ],
    "TB-03": [
        "W9-S3A",
        "W9-S3B",
        "physical schema, migration, durable repository or database I/O",
        "upstream-admission and persistence authority",
    ],
    "TB-08": [
        "W10 S1/S2A/S2B/S3A/S3B",
        "S5A/S5B/S5C route evidence",
        "reviewed legacy/internal route bypasses",
        "provider authenticity",
        "durable billing inbox",
        "paid-surface enforcement",
    ],
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
    "TH-06": [
        "W9-S3A",
        "W9-S3B",
        "No physical schema, durable repository or database I/O",
    ],
    "TH-09": [
        "immutable event identity",
        "exact replay versus identity conflict",
        "zero direct entitlement effect",
        "No webhook ingress, signature verification",
    ],
    "TH-14": [
        "integrated W9-S4A–E",
        "local/synthetic",
        "named ownership",
        "accepted production runbook",
        "tabletop evidence",
        "sandbox/real-provider outage",
    ],
}

DECISION_SEMANTIC_MARKERS = {
    "DEC-03": [
        "W9-S3A",
        "W9-S3B",
        "No physical schema, database I/O or durable annual-position write",
        "denies upstream-admission and persistence authority",
    ],
    "DEC-04": [
        "S3B's in-memory deletion decision is not a deletion executor",
        "legal-hold exceptions",
        "backup expiry",
    ],
    "DEC-11": [
        "S2B closes four ordinary defaults only",
        "Five exact keys remain unresolved",
        "tax invoicing/additional VAT presentation",
        "exact paid-access surface",
        "billing-account recovery",
        "post-settlement dispute/chargeback/reversal consequences",
        "S5A `W10_S5A_PAID_SURFACE_INVENTORY.md`",
        "S5C hardens only the reviewed legacy/internal routes",
        "without deciding paid access",
    ],
}

GAP_SEMANTIC_MARKERS = {
    "PERSIST-01": [
        "W9-S3A integrates",
        "not an approved field-by-field lifecycle",
        "physical schema",
    ],
    "PERSIST-02": [
        "W9-S3B integrates a detached structural candidate",
        "no physical schema/migration",
        "durable repository/database I/O",
        "deletion executor",
    ],
    "ACT-01": [
        "W9-S1B evidence-only reconciliation",
        "not assurance authority",
        "fresh independent acceptance",
    ],
    "OUTAGE-01": [
        "W9-S4A–E are integrated",
        "local/synthetic",
        "named ownership",
        "accepted production runbook",
        "tabletop evidence",
        "sandbox/real-provider",
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
    *STALE_RECONCILIATION_BASES,
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


def _git_blob_sha256(commit: str, relative_path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def _combined() -> str:
    return _read(DATA_FLOW_DOC) + "\n" + _read(DECISION_DOC) + "\n" + _read(GAP_DOC)


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


def _gap_row(text: str, gap_id: str) -> str:
    match = re.search(
        rf"^\|\s*{re.escape(gap_id)}\s*\|.*$", text, flags=re.MULTILINE
    )
    assert match is not None, f"missing gap row: {gap_id}"
    return match.group(0)


# ── Document presence and structure ───────────────────────────────────────────

def test_package_evidence_files_exist():
    for path in S1_EVIDENCE_PATHS:
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
        block = _normalise_whitespace(blocks[section_id])
        missing = [
            marker for marker in required_markers if marker not in block
        ]
        assert not missing, (
            f"{section_id} lost section-bound semantic marker(s): {missing}"
        )


def test_reconciled_decisions_bind_contract_evidence_without_closing_gates():
    blocks = _section_blocks(_read(DECISION_DOC), "DEC")
    for section_id, required_markers in DECISION_SEMANTIC_MARKERS.items():
        block = _normalise_whitespace(blocks[section_id])
        missing = [
            marker for marker in required_markers if marker not in block
        ]
        assert not missing, (
            f"{section_id} lost decision-bound semantic marker(s): {missing}"
        )


def test_reconciled_gap_rows_preserve_exact_remaining_gates():
    text = _read(GAP_DOC)
    for gap_id, required_markers in GAP_SEMANTIC_MARKERS.items():
        row = _gap_row(text, gap_id)
        missing = [marker for marker in required_markers if marker not in row]
        assert not missing, f"{gap_id} lost gap-bound marker(s): {missing}"


def test_all_preexisting_unnamed_decision_owners_remain_unnamed():
    blocks = _section_blocks(_read(DECISION_DOC), "DEC")
    owners = [
        _field_value(blocks[decision_id], "Accountable decision owner/authority")
        for decision_id in DECISION_IDS
    ]
    assert sum("to be named" in (owner or "") for owner in owners) == 13


def test_stale_local_evidence_claims_are_absent():
    text = _combined()
    present = [frag for frag in STALE_CLAIM_FRAGMENTS if frag in text]
    assert not present, (
        f"stale local-evidence claim(s) still present after reconciliation: {present}"
    )


def test_reconciliation_base_and_tree_are_the_exact_current_integration_identity():
    for path in (DATA_FLOW_DOC, DECISION_DOC, GAP_DOC):
        text = _read(path)
        assert RECONCILIATION_BASE in text, (
            f"{path.name} is not reconciled to the immutable candidate base "
            f"{RECONCILIATION_BASE}"
        )
        assert RECONCILIATION_TREE in text, (
            f"{path.name} is not bound to exact tree {RECONCILIATION_TREE}"
        )
        for stale_base in STALE_RECONCILIATION_BASES:
            assert stale_base not in text, (
                f"{path.name} still reconciles to stale ancestor {stale_base}"
            )
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        assert INTRODUCING_BASE in _read(path), (
            f"{path.name} lost historical W9-S1A base {INTRODUCING_BASE}"
        )


def test_exact_current_source_hashes_match_and_are_recorded():
    data_flow = _read(DATA_FLOW_DOC)
    for relative_path, expected_hash in SOURCE_SHA256.items():
        actual_hash = hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"source drift for {relative_path}: {actual_hash} != {expected_hash}"
        )
        assert relative_path in data_flow, f"missing source binding: {relative_path}"
        assert expected_hash in data_flow, f"missing SHA-256 binding: {relative_path}"


def test_live_routes_binding_is_distinct_from_historical_s5c_blob():
    path = "reserved/web/routes.py"
    live_hash = SOURCE_SHA256[path]
    data_flow = _read(DATA_FLOW_DOC)

    assert CURRENT_ROUTES_COMMIT in data_flow
    assert CURRENT_ROUTES_TREE in data_flow
    assert hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() == live_hash
    assert _git_blob_sha256(S5C_EVIDENCE_REFRESH_PARENT, path) == (
        HISTORICAL_S5C_ROUTES_SHA256
    )
    assert live_hash != HISTORICAL_S5C_ROUTES_SHA256


def test_integrated_slice_identities_are_exactly_bound():
    data_flow = _read(DATA_FLOW_DOC)
    for slice_name, commit in INTEGRATED_COMMIT_IDENTITIES.items():
        assert commit in data_flow, f"missing exact {slice_name} identity: {commit}"


def test_independent_review_is_findings_input_not_assurance_authority():
    for path in (DATA_FLOW_DOC, DECISION_DOC, GAP_DOC):
        text = _normalise_whitespace(_read(path))
        assert "findings" in text
        assert "not assurance authority" in text
        assert "W9-S1" in text


def test_reconciliation_does_not_claim_missing_completion_or_acceptance():
    gap_register = _normalise_whitespace(_read(GAP_DOC))
    required_non_claims = [
        "does not prove target/provider operation",
        "human acceptance",
        "durable annual-position storage",
        "billing activation",
        "W9-S1 completion",
        "launch readiness",
    ]
    missing = [marker for marker in required_non_claims if marker not in gap_register]
    assert not missing, f"missing explicit non-authority boundary(ies): {missing}"
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        assert "Strict W9 completion remains **0/5**" in _normalise_whitespace(
            _read(path)
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


def _worktree_changed_paths() -> set[str]:
    """Return tracked and untracked candidate paths relative to the worktree."""
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "-z", "HEAD"],
        capture_output=True,
        check=True,
    ).stdout
    untracked = subprocess.run(
        [
            "git", "-C", str(REPO_ROOT), "ls-files", "--others",
            "--exclude-standard", "-z",
        ],
        capture_output=True,
        check=True,
    ).stdout
    return {
        raw.decode("utf-8", errors="strict")
        for raw in (tracked + untracked).split(b"\0")
        if raw
    }


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
        + sorted(S1_EVIDENCE_PATHS),
        capture_output=True,
        text=True,
        check=True,
    )
    commits.extend(
        line.strip() for line in later.stdout.splitlines() if line.strip()
    )
    return commits


def _is_protected(path: str) -> bool:
    if path in S1_EVIDENCE_PATHS:
        return False
    if path.startswith(_PROTECTED_PREFIXES):
        return True
    lowered = path.lower()
    return any(sub.lower() in lowered for sub in _PROTECTED_SUBSTRINGS)


def test_package_does_not_modify_readiness_release_config_or_source_files():
    changed = set(_git_changed_paths())
    missing = sorted(S1A_INTRODUCING_PATHS - changed)
    unexpected = sorted(changed - S1A_INTRODUCING_PATHS)
    assert not missing and not unexpected, (
        "W9-S1A package path boundary mismatch: "
        f"missing={missing}, unexpected={unexpected}"
    )


def test_package_does_not_touch_protected_files():
    changed = _git_changed_paths()
    protected = [p for p in changed if _is_protected(p)]
    assert not protected, f"W9-S1A package touched protected files: {protected}"


def test_current_candidate_has_no_scope_drift():
    changed = _worktree_changed_paths()
    allowed = (
        S1_EVIDENCE_PATHS
        if changed <= S1_EVIDENCE_PATHS
        else LIVE_PROVENANCE_RECONCILIATION_PATHS
    )
    drift = sorted(changed - allowed)
    assert not drift, f"current evidence candidate changed unauthorised paths: {drift}"


def test_reconciliation_scope_truthfully_includes_the_gap_register():
    obsolete = "the gap register, or the canonical release gate"
    required = "It amends the gap register only for this"
    for path in (DATA_FLOW_DOC, DECISION_DOC):
        text = path.read_text(encoding="utf-8")
        assert obsolete not in text
        assert required in text
        assert "authorised evidence-only current-state reconciliation" in text
        assert "does not convert" in text


def _is_exact_live_provenance_reconciliation(
    commit: str, changed: set[str], identity: list[str]
) -> bool:
    return (
        commit == LIVE_PROVENANCE_RECONCILIATION_COMMIT
        and changed == LIVE_PROVENANCE_RECONCILIATION_PATHS
        and identity
        == [
            LIVE_PROVENANCE_RECONCILIATION_COMMIT,
            LIVE_PROVENANCE_RECONCILIATION_PARENT,
        ]
    )


def test_live_provenance_generation_allowance_rejects_scope_or_topology_drift():
    commit = LIVE_PROVENANCE_RECONCILIATION_COMMIT
    paths = set(LIVE_PROVENANCE_RECONCILIATION_PATHS)
    identity = [commit, LIVE_PROVENANCE_RECONCILIATION_PARENT]

    assert _is_exact_live_provenance_reconciliation(commit, paths, identity)
    assert not _is_exact_live_provenance_reconciliation(
        commit, paths - {"docs/W10_S5A_PAID_SURFACE_INVENTORY.md"}, identity
    )
    assert not _is_exact_live_provenance_reconciliation(
        commit, paths | {"reserved/web/routes.py"}, identity
    )
    assert not _is_exact_live_provenance_reconciliation(
        commit, paths, [commit, "0" * 40]
    )
    assert not _is_exact_live_provenance_reconciliation(
        "0" * 40, paths, identity
    )


def test_no_scope_drift_across_package_history():
    """Every package-touching commit stays inside authorised evidence paths.

    A correction commit that touches a readiness/release/completion map or a
    source/configuration file is scope drift and must fail the package, even if
    the introducing commit was clean.
    """
    for commit in _package_history_commits():
        changed = set(_changed_paths_for_commit(commit))
        drift = sorted(changed - S1_EVIDENCE_PATHS)
        if not drift:
            continue
        identity = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-list", "--parents", "-n", "1", commit],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        is_s5c_refresh = changed == S5C_EVIDENCE_REFRESH_PATHS and identity == [
            commit,
            S5C_EVIDENCE_REFRESH_PARENT,
        ]
        is_entitlement_reconciliation = (
            commit == ENTITLEMENT_EVIDENCE_RECONCILIATION_COMMIT
            and changed == ENTITLEMENT_EVIDENCE_RECONCILIATION_PATHS
            and identity == [
                ENTITLEMENT_EVIDENCE_RECONCILIATION_COMMIT,
                ENTITLEMENT_EVIDENCE_RECONCILIATION_PARENT,
            ]
        )
        is_live_provenance_reconciliation = _is_exact_live_provenance_reconciliation(
            commit, changed, identity
        )
        assert (
            is_s5c_refresh
            or is_entitlement_reconciliation
            or is_live_provenance_reconciliation
        ), (
            f"scope drift in package commit {commit}: {drift}; expected either "
            f"W9 evidence-only paths {sorted(S1_EVIDENCE_PATHS)} or the exact "
            "one-generation S5C evidence-dependency refresh or the exact "
            "accepted W9/W10 entitlement evidence reconciliation or the exact "
            "accepted live provenance reconciliation"
        )
