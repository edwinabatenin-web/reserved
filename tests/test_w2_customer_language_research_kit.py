"""Focused safety and determinism tests for the synthetic W2 research kit."""
from __future__ import annotations

import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_w2_customer_language_research_kit.py"
FIXTURE = ROOT / "docs" / "fixtures" / "W2_CUSTOMER_LANGUAGE_RESEARCH_CASES.json"


def _module():
    spec = importlib.util.spec_from_file_location("w2_research_kit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _all_ids(module):
    return [case["id"] for case in module.load_fixture()["cases"]]


def _render_all(module, output_path, case_ids=None):
    module.render_gallery(output_path, case_ids or _all_ids(module))


def test_fixture_is_versioned_wholly_synthetic_and_valid():
    module = _module()
    fixture = module.load_fixture()
    assert fixture["fixture_version"] == "w2-customer-language-research-cases/1.0"
    assert fixture["synthetic"] is True and fixture["production_use"] is False
    assert len(fixture["cases"]) == 7
    assert len({case["id"] for case in fixture["cases"]}) == 7


def test_fixture_covers_required_evidence_funding_claim_and_closed_states():
    cases = json.loads(FIXTURE.read_text())["cases"]
    assert {case["evidence"] for case in cases} >= {
        "hmrc_confirmed_exact", "qualified_local_estimate", None,
    }
    assert {case["funding"] for case in cases} >= {"gap", "exact", "surplus", None}
    claims = {case["claim_to_reduce"] for case in cases}
    assert claims >= {"review_ready", "customer_confirmation_required", "no_reduction", "review_required"}
    closed = next(case for case in cases if case["status"] == "review_required")
    assert closed["annual_liability"] is not None and closed["obligations"]


def test_render_is_deterministic_and_every_case_is_visibly_synthetic(tmp_path):
    module = _module()
    first = tmp_path / "first.html"
    second = tmp_path / "second.html"
    _render_all(module, first)
    _render_all(module, second)
    assert first.read_bytes() == second.read_bytes()
    output = first.read_text()
    case_count = len(module.load_fixture()["cases"])
    assert output.count("Synthetic research case · Non-production") == case_count
    assert output.count("What, if anything, does this page tell you?") == case_count
    assert output.count("Would you rely on any of these figures? Why or why not?") == case_count
    assert "Which figures would you rely on" not in output
    assert "No case represents a real person" in output
    assert [f"<h2>Case {letter}</h2>" in output for letter in "ABCDEFG"] == [True] * 7
    for case in module.load_fixture()["cases"]:
        assert case["moderator_label"] not in output
        assert case["id"] not in output


def test_gallery_contains_all_required_customer_language(tmp_path):
    module = _module()
    output_path = tmp_path / "gallery.html"
    _render_all(module, output_path)
    output = output_path.read_text()
    for phrase in (
        "HMRC-recorded cash obligations",
        "Local estimate — not confirmed by HMRC",
        "must not be read as your current HMRC bill",
        "Set-aside gap",
        "Exact set-aside coverage",
        "Set-aside surplus",
        "not available cash",
        "You have prepared a claim for your review and submission to HMRC",
        "only after you confirm your proposed amounts",
        "separate action you initiate with HMRC",
        "Reducing Payments on Account too far may lead to interest",
    ):
        assert phrase in output


def test_fail_closed_case_suppresses_unsafe_money(tmp_path):
    module = _module()
    output_path = tmp_path / "gallery.html"
    _render_all(module, output_path)
    output = output_path.read_text()
    start = output.index('data-case="case-g"')
    closed_card = output[start:output.index("</article>", start)]
    assert "Review required" in closed_card
    assert "£" not in closed_card
    assert "9999.99" not in closed_card and "3333.33" not in closed_card


def test_gallery_has_no_action_controls_or_action_authority(tmp_path):
    module = _module()
    output_path = tmp_path / "gallery.html"
    _render_all(module, output_path)
    output = output_path.read_text().lower()
    assert "does not authorise a payment or transfer" in output
    for tag in ("<button", "<form", "<input", "<select", "<textarea", "<a "):
        assert tag not in output
    for authority in ("pay now", "file now", "submit now", "transfer now"):
        assert authority not in output


def test_output_is_explicit_outside_repository_and_parent_must_exist(tmp_path):
    module = _module()
    with pytest.raises(ValueError, match="outside the repository"):
        module.render_gallery(ROOT / "research-gallery.html", ["hmrc-exact-gap"])
    with pytest.raises(ValueError, match="already exist"):
        module.render_gallery(tmp_path / "missing" / "gallery.html", ["hmrc-exact-gap"])
    assert not (ROOT / "research-gallery.html").exists()


def test_existing_output_fails_closed_without_changing_bytes(tmp_path):
    module = _module()
    output_path = tmp_path / "existing.html"
    original = b"pre-existing research evidence\x00must survive"
    output_path.write_bytes(original)
    with pytest.raises(ValueError, match="must not already exist"):
        module.render_gallery(output_path, ["hmrc-exact-gap"])
    assert output_path.read_bytes() == original


def test_explicit_selection_preserves_order_and_rejects_unknown_duplicates(tmp_path):
    module = _module()
    chosen = ["claim-review-ready", "hmrc-exact-gap"]
    module.render_gallery(tmp_path / "ordered.html", chosen)
    output = (tmp_path / "ordered.html").read_text()
    assert 'data-selected-order="case-d,case-a"' in output
    assert output.index('data-case="case-d"') < output.index('data-case="case-a"')
    with pytest.raises(ValueError, match="explicit case id"):
        module.render_gallery(tmp_path / "none.html", [])
    with pytest.raises(ValueError, match="unknown case id"):
        module.render_gallery(tmp_path / "unknown.html", ["not-a-case"])
    with pytest.raises(ValueError, match="must not be duplicated"):
        module.render_gallery(tmp_path / "duplicate.html", ["hmrc-exact-gap"] * 2)


class _IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if "aria-labelledby" in attributes:
            self.references.extend(attributes["aria-labelledby"].split())


def test_html_ids_are_unique_and_aria_labelledby_targets_exist_once(tmp_path):
    module = _module()
    output_path = tmp_path / "gallery.html"
    _render_all(module, output_path)
    parsed = _IdCollector()
    parsed.feed(output_path.read_text())
    assert len(parsed.ids) == len(set(parsed.ids))
    assert parsed.references
    assert all(parsed.ids.count(target) == 1 for target in parsed.references)


@pytest.mark.parametrize("bad_date", ["2027-01", "2027-W01-1", "2027-1-01", 20270101])
def test_fixture_rejects_noncanonical_due_dates(monkeypatch, tmp_path, bad_date):
    module = _module()
    fixture = json.loads(FIXTURE.read_text())
    fixture["cases"][0]["obligations"][0]["due_date"] = bad_date
    bad_fixture = tmp_path / "bad.json"
    bad_fixture.write_text(json.dumps(fixture))
    monkeypatch.setattr(module, "FIXTURE", bad_fixture)
    with pytest.raises(ValueError, match="due date must be"):
        module.load_fixture()


def test_fixture_rejects_duplicate_json_keys(monkeypatch, tmp_path):
    module = _module()
    bad_fixture = tmp_path / "duplicate.json"
    bad_fixture.write_text('{"fixture_version":"a","fixture_version":"b"}')
    monkeypatch.setattr(module, "FIXTURE", bad_fixture)
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        module.load_fixture()


@pytest.mark.parametrize("root", ["[]", "null", '"text"'])
def test_fixture_rejects_non_object_root_with_controlled_value_error(monkeypatch, tmp_path, root):
    module = _module()
    bad_fixture = tmp_path / "root.json"
    bad_fixture.write_text(root)
    monkeypatch.setattr(module, "FIXTURE", bad_fixture)
    with pytest.raises(ValueError, match="fixture root must be an object"):
        module.load_fixture()


def test_renderer_has_no_network_persistence_route_or_engine_coupling():
    source = SCRIPT.read_text()
    prohibited = (
        "reserved.engines", "reserved.web", "reserved.api", "reserved.database",
        "requests", "urllib", "http.client", "socket", "flask", "sqlalchemy",
    )
    assert not [term for term in prohibited if term in source.lower()]
    assert source.count("write_text(") == 1
    assert "add_argument(\"output\"" in source


def test_protocol_does_not_claim_completed_research_or_gate_closure():
    protocol = (ROOT / "docs" / "W2_CUSTOMER_LANGUAGE_REPRESENTATIVE_TEST_PROTOCOL.md").read_text()
    assert "No session or representative-user validation is claimed" in protocol
    assert "Gate 12 may close only after" in protocol
    assert "Otherwise gate 12 remains open" in protocol
    assert "not UX approval, assurance, W2 completion or launch readiness" in protocol
    assert "Would you rely on any of these figures? Why or why not?" in protocol
    assert "Which figures would you rely on" not in protocol
    assert "moderator-only" in protocol and "must not be displayed" in protocol
