"""Production-shaped composition for the durable structured manual PAYE read."""

from decimal import Decimal

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.paye_durable_endpoint import DurablePayeRuntime
from tests.test_billing_composition import paid_event, runtime as billing_runtime
from tests.test_paye_annual_bridge import durable_annual, entry


def prepared(tmp_path, monkeypatch, *, paye=True, billing=True, production=True):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "app.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "production" if production else "development")
    if production:
        monkeypatch.setenv("SESSION_SECRET", "synthetic-production-secret-for-tests")
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    db.init_db()
    owner = db.get_or_create_user("paye-runtime-owner", email="owner@example.test")
    annual, repository = durable_annual(owner)
    stored = entry(1, "1200.00", user_id=owner)
    stored.pop("user_id")
    db.save_paye_manual_entry(owner, stored)
    complete_paye = DurablePayeRuntime(
        repository=repository,
        annual_position_provider=lambda *_: annual,
        owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
    )
    complete_billing = billing_runtime(tmp_path)
    app = create_app(
        billing_runtime=complete_billing if billing else None,
        paye_runtime=complete_paye if paye else None,
    )
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return app, client, owner, complete_billing


def test_complete_paye_runtime_remains_closed_without_billing_runtime(tmp_path, monkeypatch):
    _, client, _, _ = prepared(tmp_path, monkeypatch, billing=False, production=False)
    assert client.get("/v2/paye/current-position").status_code == 404


def test_paid_owner_can_read_bounded_current_position(tmp_path, monkeypatch):
    app, client, owner, billing = prepared(tmp_path, monkeypatch)
    assert "reserved.paye.durable_endpoint" in app.extensions
    assert client.get("/v2/paye/current-position").status_code == 403
    paid_event(billing, owner)
    response = client.get("/v2/paye/current-position")
    assert response.status_code == 200
    assert response.get_json() == {
        "future_pay_status": "unknown",
        "paye_evidence_status": "calculated",
        "tax_paid_known": True,
        "tax_year": "2026/27",
    }


def test_paid_owner_still_gets_no_result_without_paye_runtime(tmp_path, monkeypatch):
    _, client, owner, billing = prepared(tmp_path, monkeypatch, paye=False)
    paid_event(billing, owner)
    assert client.get("/v2/paye/current-position").status_code == 404


def test_invalid_paye_injection_cannot_open_route(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "invalid.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "synthetic-production-secret-for-tests")
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    app = create_app(paye_runtime=object())
    app.config.update(TESTING=True)
    owner = db.get_or_create_user("invalid-paye-runtime")
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    assert "reserved.paye.durable_endpoint" not in app.extensions
    assert client.get("/v2/paye/current-position").status_code == 404
