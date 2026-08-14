from pathlib import Path


TEMPLATES = Path(__file__).parents[1] / "reserved" / "templates"


def test_v1_navigation_does_not_offer_capital_gains_preview():
    base = (TEMPLATES / "base.html").read_text()
    dashboard = (TEMPLATES / "v2" / "dashboard.html").read_text()
    settings = (TEMPLATES / "v2" / "settings.html").read_text()
    assert "url_for('web.capital_gains')" not in base
    assert "url_for('web.capital_gains')" not in dashboard
    assert "url_for('web.capital_gains')" not in settings


def test_capital_gains_customer_route_is_disabled():
    routes = (Path(__file__).parents[1] / "reserved" / "web" / "routes.py").read_text()
    route_body = routes.split("def capital_gains():", 1)[1].split("@web.", 1)[0]
    assert "abort(404)" in route_body


def test_plan_4_label_is_not_treated_as_scottish_tax_support():
    """Plan 4 is a loan type and remains valid outside Scotland."""
    settings = (TEMPLATES / "v2" / "settings.html").read_text()
    assert 'value="plan_4"' in settings


def test_about_page_does_not_claim_independent_validation():
    about = (TEMPLATES / "about.html").read_text().lower()
    assert "verified against an independent test suite" not in about
    assert "does not estimate capital gains tax or scottish income tax" in about
