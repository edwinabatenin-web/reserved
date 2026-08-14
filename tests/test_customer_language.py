"""Regression checks for Reserved's factual, non-advisory customer language."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_SURFACES = (
    ROOT / "reserved" / "templates",
    ROOT / "reserved" / "static" / "js",
)
PROHIBITED = (
    "safe to spend",
    "safe-to-spend",
    "truly yours",
    "yours to spend",
    "free to spend",
    "you should invest",
    "we recommend that you",
    "tax estimates and recommendations",
)


def test_customer_surfaces_do_not_use_prohibited_financial_claims():
    findings = []
    for surface in CUSTOMER_SURFACES:
        for path in surface.rglob("*"):
            if not path.is_file() or path.suffix not in {".html", ".js"}:
                continue
            text = path.read_text(encoding="utf-8").lower()
            for phrase in PROHIBITED:
                if phrase in text:
                    findings.append(f"{path.relative_to(ROOT)}: {phrase}")
    assert not findings, "Prohibited customer language found:\n" + "\n".join(findings)


def test_dashboard_contract_does_not_emit_deprecated_safe_to_spend_remainder():
    dashboard_source = (ROOT / "reserved" / "services" / "dashboard.py").read_text().lower()
    assert '"safe_to_spend"' not in dashboard_source
    base_template = (ROOT / "reserved" / "templates" / "base.html").read_text().lower()
    assert 'value="safe_to_spend"' not in base_template


def test_legacy_dashboard_explicitly_names_incremental_scope_and_missing_families():
    for name in ("dashboard.html", "v2/dashboard.html"):
        text = (ROOT / "reserved" / "templates" / name).read_text().lower()
        assert "limited" in text
        assert "not a complete annual tax position" in text
        for family in ("savings", "dividends", "property", "hicbc", "tax already paid"):
            assert family in text


def test_optimise_is_labelled_as_a_limited_scenario_not_complete_advice():
    text = (ROOT / "reserved" / "templates" / "v2" / "optimise.html").read_text().lower()
    assert "illustrative comparisons" in text
    assert "not a complete annual position or recommendation" in text
    for family in ("savings", "dividends", "property", "tax already paid", "student loans"):
        assert family in text
    assert "modelled amount to remove this trigger" in text
    assert "available allowance is not established" in text


def test_duplicate_marketing_tour_meta_and_accessibility_copy_matches_limited_scope():
    files = {
        "base": ROOT / "reserved/templates/base.html",
        "about": ROOT / "reserved/templates/about.html",
        "overview": ROOT / "reserved/templates/v2/overview.html",
        "tour": ROOT / "reserved/static/js/app.js",
        "login": ROOT / "reserved/templates/v2/login.html",
    }
    text = {name: path.read_text().lower() for name, path in files.items()}
    assert "explore limited tax estimates" in text["base"]
    assert "explore limited tax estimates" in text["login"]
    assert "not a complete annual tax position" in text["about"]
    assert "not a complete annual tax position or assured set-aside figure" in text["overview"]
    assert "not a complete bill or assured set-aside amount" in text["tour"]
    assert "exact split" not in text["tour"]
    for name in ("overview", "about", "tour"):
        for family in ("savings", "dividends", "property", "hicbc", "tax already paid"):
            assert family in text[name]


def test_dashboard_accessibility_labels_do_not_call_limited_output_reserved_tax():
    for name in ("dashboard.html", "v2/dashboard.html"):
        text = (ROOT / "reserved/templates" / name).read_text().lower()
        assert "per cent of income reserved for tax" not in text
        assert "attributed by the limited model" in text


def test_both_dashboards_explain_unsupported_multiple_plan_verification_without_money():
    for name in ("dashboard.html", "v2/dashboard.html"):
        text = (ROOT / "reserved/templates" / name).read_text().lower()
        assert "estimate unavailable for this loan-plan combination" in text
        assert "cannot verify the annual self assessment treatment" in text
        assert "no student-loan amount, total, allocation or set-aside figure" in text
