"""
Negative terminology checks for the active assurance UI and metadata.

Guards the H4 decisions: the active UI/metadata must not claim absolute
"verified" status, must use "period of assessment" rather than the ambiguous
"tax year" label, must not carry the stale "Extended BRL" figure, and must not
reference the retired ``reserved-engine-2.0.0`` bundle as active evidence.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = ROOT / "reserved" / "templates" / "tax_assurance.html"
METADATA_PATH = ROOT / "reserved" / "assurance_metadata.json"
ROUTES = ROOT / "reserved" / "web" / "routes.py"
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
    assert meta["status"] in {"release_gate_passed", "release_gate_failed"}
    assert meta["generated_on"]
    # The status is a gate result, not an absolute "verified" statement.
    assert "verified" not in meta["status"]


def test_active_ui_does_not_label_a_date_as_verified():
    text = _template()
    assert "Last verified" not in text
    assert "tests verified on" not in text


# ── "tax year" vs "period of assessment" ─────────────────────────────────────

def test_active_ui_uses_period_of_assessment_not_tax_year_label():
    text = _template()
    assert "Period of assessment" in text
    assert ">Tax year<" not in text  # the metric label is renamed
    assert "{{ meta.period_of_assessment }}" in text
    assert "{{ meta.tax_year }}" not in text


def test_active_metadata_uses_period_of_assessment():
    meta = _metadata()
    assert meta["period_of_assessment"] == "2026/27"
    assert "tax_year" not in meta


# ── Stale figure ─────────────────────────────────────────────────────────────

def test_stale_extended_brl_figure_absent_from_active_ui():
    assert "Extended BRL" not in _template()
    assert "Extended higher-rate threshold" in _template()


# ── Retired bundle is not active evidence ────────────────────────────────────

def test_retired_bundle_is_not_imported_by_the_artefact_loader():
    import re
    source = ARTEFACT_LOADER.read_text(encoding="utf-8")
    # Strip docstrings and comments, then require the retired bundle to be
    # absent from the remaining executable code — it may only be named in
    # documentation and must never be added to sys.path or imported.
    code_only = re.sub(r'"""(?:.|\n)*?"""', "", source)
    code_only = re.sub(r"#[^\n]*", "", code_only)
    assert "reserved-engine-2.0.0" not in code_only
