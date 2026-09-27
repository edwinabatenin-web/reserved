"""Template-only arbitration for independently supplied local billing copy."""

from __future__ import annotations

from itertools import combinations

import pytest
from flask import render_template
from markupsafe import Markup

import reserved.database as db
from reserved import create_app


CONTEXTS = (
    ("local_billing_initial_paid_copy", "initial"),
    ("local_billing_cancellation_copy", "cancellation"),
    ("local_billing_full_withdrawal_copy", "withdrawal"),
    ("local_billing_later_period_restoration_copy", "restoration"),
    ("local_billing_successful_renewal_copy", "renewal"),
    ("local_billing_recovery_copy", "recovery"),
)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "arbitration.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


def _copy(name):
    """A harmless complete copy shape; the template selects fields by context."""
    return {
        "heading": f"lifecycle-heading-{name}",
        "summary": f"lifecycle-summary-{name}",
        "verification_label": "Verified",
        "verification_utc": "2026-11-01T00:00:00Z",
        "verification_display": "1 November 2026 at 00:00:00 UTC",
        "paid_period_message": "Paid-period message.",
        "renewal_caveat": "Renewal caveat.",
        "access_message": "Access message.",
        "renewal_message": "Renewal message.",
        "paid_through_label": "Paid through",
        "paid_through_exclusive_utc": "2026-12-01T00:00:00Z",
        "paid_through_display": "1 December 2026 at 00:00:00 UTC",
        "boundary_message": "Boundary message.",
        "rights_message": "Rights message.",
        "interval_label": "Access interval",
        "access_start_utc": "2026-11-01T00:00:00Z",
        "interval_display": "1 November 2026 at 00:00:00 UTC",
        "verified_label": "Verified",
        "verified_utc": "2026-11-01T00:00:00Z",
        "verified_display": "1 November 2026 at 00:00:00 UTC",
        "scope_caveat": "Scope caveat.",
        "deadline_label": "Deadline",
        "deadline_exclusive_utc": "2026-11-08T00:00:00Z",
        "deadline_display": "8 November 2026 at 00:00:00 UTC",
        "deadline_consequence": "Deadline consequence.",
        "verified_recovery_consequence": "Verified recovery consequence.",
    }


def _supplied(names):
    return {context: _copy(label) for context, label in CONTEXTS if context in names}


def _direct(app, supplied):
    with app.test_request_context("/v2/plans"):
        return render_template(
            "v2/plans.html", billing_plans_fragment=Markup("<p>unrelated-plan-fragment</p>"),
            **supplied,
        )


def _route(app, supplied):
    app.context_processor(lambda: dict(supplied))
    client = app.test_client()
    assert client.get("/v2/demo-login").status_code == 302
    response = client.get("/v2/plans")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _assert_visibility(body, expected):
    for context, label in CONTEXTS:
        heading = f"lifecycle-heading-{label}"
        assert (heading in body) is (context == expected)
    assert "Purchasing a plan or changing access is not available in this preview." in body


@pytest.mark.parametrize("renderer", (_direct, _route), ids=("template", "route"))
@pytest.mark.parametrize("context,label", CONTEXTS)
def test_each_single_lifecycle_context_renders_only_its_existing_panel(
        app, renderer, context, label):
    body = renderer(app, _supplied((context,)))
    _assert_visibility(body, context)
    assert f"lifecycle-summary-{label}" in body


@pytest.mark.parametrize("renderer", (_direct, _route), ids=("template", "route"))
@pytest.mark.parametrize("pair", tuple(combinations((context for context, _ in CONTEXTS), 2)))
def test_every_lifecycle_context_pair_suppresses_all_customer_status_panels(
        app, renderer, pair):
    body = renderer(app, _supplied(pair))
    _assert_visibility(body, None)


@pytest.mark.parametrize("renderer", (_direct, _route), ids=("template", "route"))
def test_withdrawal_and_restoration_are_an_explicit_conflict(app, renderer):
    body = renderer(app, _supplied((
        "local_billing_full_withdrawal_copy",
        "local_billing_later_period_restoration_copy",
    )))
    _assert_visibility(body, None)


@pytest.mark.parametrize("renderer", (_direct, _route), ids=("template", "route"))
def test_no_lifecycle_context_or_unrelated_context_leaves_panels_absent(app, renderer):
    body = renderer(app, {"unrelated_context": {"heading": "unrelated-only"}})
    _assert_visibility(body, None)
    assert "unrelated-only" not in body
    if renderer is _direct:
        assert "unrelated-plan-fragment" in body
    else:
        assert "£29 per month" in body
