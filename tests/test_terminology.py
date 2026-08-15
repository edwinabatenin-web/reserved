"""
Negative terminology checks for the active assurance UI and metadata.

Guards the H4 decisions: the active UI/metadata must not claim absolute
"verified" status, must use the customer-facing "tax year" label rather than
"period of assessment", must not carry the stale "Extended BRL" figure, and must
not reference the retired ``reserved-engine-2.0.0`` bundle as active evidence.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = ROOT / "reserved" / "templates" / "tax_assurance.html"
METADATA_PATH = ROOT / "reserved" / "assurance_metadata.json"
ARTEFACT_LOADER = ROOT / "reserved_west" / "artefact.py"


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _metadata() -> dict:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


# ── "verified" over-claiming ─────────────────────────────────────────────────

def test_active_metadata_does_not_overclaim_verified():
    raw = METADATA_PATH.read_text(encoding="utf-8")
    assert '"verified_date"' not in raw
    meta = _metadata()
    assert meta["status"] in {
        "deterministic_engine_remediation_gate_passed",
        "deterministic_engine_remediation_gate_failed",
    }
    assert meta["generated_on"]
    # The status is a gate result, not an absolute "verified" statement.
    assert "verified" not in meta["status"]


def test_active_ui_does_not_label_a_date_as_verified():
    text = _template()
    assert "Last verified" not in text
    assert "tests verified on" not in text


# ── "tax year" label ─────────────────────────────────────────────────────────

def test_active_ui_uses_tax_year_not_period_of_assessment():
    text = _template()
    assert "Tax year" in text
    assert "Period of assessment" not in text
    assert "{{ meta.tax_year }}" in text
    assert "{{ meta.period_of_assessment }}" not in text


def test_active_metadata_uses_tax_year():
    meta = _metadata()
    assert meta["tax_year"] == "2026/27"
    assert "period_of_assessment" not in meta


# ── Stale figure ─────────────────────────────────────────────────────────────

def test_stale_extended_brl_figure_absent_from_active_ui():
    assert "Extended BRL" not in _template()
    assert "Extended higher-rate threshold" in _template()


# ── Retired bundle is not active evidence ────────────────────────────────────

def test_retired_bundle_is_not_imported_by_the_artefact_loader():
    import re
    source = ARTEFACT_LOADER.read_text(encoding="utf-8")
    code_only = re.sub(r'"""(?:.|\n)*?"""', "", source)
    code_only = re.sub(r"#[^\n]*", "", code_only)
    assert "reserved-engine-2.0.0" not in code_only
