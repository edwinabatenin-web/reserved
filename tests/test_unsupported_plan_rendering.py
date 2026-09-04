"""Rendered tripwires for unsupported annual-SA loan-plan inputs."""

import re
from importlib import import_module

import pytest

import reserved.database as db
from reserved import create_app
routes = import_module("reserved.web.routes")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "unsupported-render.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


def _profile(plans):
    return {
        "first_name": "Synthetic",
        "day_job_salary": "30000",
        "ytd_freelance_profit": "5000",
        "personal_pension_contributions": "0",
        "student_loan_plans": plans,
    }


def _unsupported_panel(response):
    html = response.get_data(as_text=True)
    match = re.search(r'<section class="panel" role="status".*?</section>', html, re.S)
    assert match, "formal unsupported status must be the rendered content path"
    return html, match.group(0)


@pytest.mark.parametrize("plans", [["mystery"], [1, 2]])
def test_legacy_calculate_hard_404s_before_rendering_unsupported_plans(app, monkeypatch, plans):
    def forbidden_profile_read():
        raise AssertionError(f"legacy calculation read profile for {plans!r}")

    monkeypatch.setattr(routes, "_get_profile", forbidden_profile_read)
    response = app.test_client().post("/calculate", data={"invoice_amount": "5000"})
    assert response.status_code == 404
    assert 'role="status"' not in response.get_data(as_text=True)


@pytest.mark.parametrize("plans", [["mystery"], [1, 2]])
def test_v2_dashboard_renders_verification_without_money_allocation_or_reserve(app, monkeypatch, plans):
    monkeypatch.setattr(routes, "_get_profile", lambda: (_profile(plans), False))
    client = app.test_client()
    client.get("/v2/demo-login")
    response = client.get("/v2/dashboard")
    html, panel = _unsupported_panel(response)
    assert response.status_code == 200
    assert html.index('role="status"') < html.index("HMRC or a qualified tax adviser")
    assert "No student-loan amount, total, allocation or set-aside figure" in panel
    assert "£" not in panel
