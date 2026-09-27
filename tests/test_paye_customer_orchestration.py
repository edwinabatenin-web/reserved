"""Focused owner-bound tests for the structured manual PAYE fallback journey."""
from datetime import datetime, timezone
import importlib
import threading

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.services.paye_customer_orchestration import (
    admit_manual_entry, annual_position_boundary_state, customer_read_model,
)


route = importlib.import_module("reserved.web.v2")
URL = "/v2/paye/manual"


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 4, 12, tzinfo=timezone.utc)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "paye.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setattr(route, "datetime", Clock)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("PAYE_MANUAL_JOURNEY_ENABLED", "1")
    app = create_app()
    app.config.update(TESTING=True)
    owner = db.get_or_create_user("paye-owner", email="owner@example.test")
    other = db.get_or_create_user("paye-other", email="other@example.test")
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return client, owner, other


def facts(**changes):
    value = {
        "employment_slot": "1", "gross_pay_to_date": "12000.00", "tax_paid_to_date": "2100.00",
        "tax_code": "1257L", "pay_frequency": "monthly", "pension_treatment": "net_pay",
        "effective_through": "2026-08-31", "confirmation": "yes",
    }
    value.update(changes)
    return value


def csrf(client):
    html = client.get(URL).get_data(as_text=True)
    return html.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]


def post(client, data):
    return client.post(URL, data=data, headers={"X-CSRFToken": csrf(client)})


def test_multiple_employments_are_owner_bound_and_replacement_is_slot_local(env):
    client, owner, _ = env
    assert post(client, facts()).status_code == 302
    assert post(client, facts(employment_slot="2", gross_pay_to_date="8000", tax_paid_to_date="900")).status_code == 302
    current = db.list_active_paye_manual_entries(owner, "2026/27")
    assert [(row["employment_slot"], row["tax_paid_to_date"]) for row in current] == [(1, "2100.00"), (2, "900.00")]
    assert post(client, facts(tax_paid_to_date="2200.00")).status_code == 302
    current = db.list_active_paye_manual_entries(owner, "2026/27")
    assert [(row["employment_slot"], row["tax_paid_to_date"]) for row in current] == [(1, "2200.00"), (2, "900.00")]


def test_missing_zero_stale_and_provisional_boundary_are_distinct(env):
    client, owner, _ = env
    assert post(client, facts(gross_pay_to_date="", tax_paid_to_date="")).status_code == 302
    entry = customer_read_model(db.list_active_paye_manual_entries(owner, "2026/27"), as_of=Clock.now().date())[0]
    assert entry["gross"] == entry["tax_paid"] == "Unknown"
    assert entry["missing"] == ("gross pay", "tax deducted")
    assert "cannot safely" in annual_position_boundary_state(db.list_active_paye_manual_entries(owner, "2026/27"))
    assert post(client, facts(employment_slot="2", gross_pay_to_date="0", tax_paid_to_date="0")).status_code == 302
    current = customer_read_model(db.list_active_paye_manual_entries(owner, "2026/27"), as_of=Clock.now().date())
    assert current[1]["gross"] == current[1]["tax_paid"] == "£0.00"


def test_deletion_never_discloses_or_deletes_another_owner_entry(env):
    client, owner, other = env
    assert post(client, facts()).status_code == 302
    evidence_id = db.list_active_paye_manual_entries(owner, "2026/27")[0]["evidence_id"]
    with client.session_transaction() as session:
        session[_SK_USER_ID] = other
    response = client.post(f"{URL}/entries/{evidence_id}/delete", data={}, headers={"X-CSRFToken": csrf(client)})
    assert response.status_code == 302
    assert len(db.list_active_paye_manual_entries(owner, "2026/27")) == 1
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    assert client.post(f"{URL}/entries/{evidence_id}/delete", data={}, headers={"X-CSRFToken": csrf(client)}).status_code == 302
    assert db.list_active_paye_manual_entries(owner, "2026/27") == []
    with db._connection() as connection:
        retained = connection.execute(
            "SELECT gross_to_date, tax_paid_to_date, deleted_at FROM paye_manual_entries "
            "WHERE user_id=? AND evidence_id=?", (owner, evidence_id),
        ).fetchone()
    assert retained["gross_to_date"] == "12000.00"
    assert retained["tax_paid_to_date"] == "2100.00"
    assert retained["deleted_at"] is not None
    assert "Remove this entry from your current PAYE view" not in client.get(URL).get_data(as_text=True)


def test_customer_copy_describes_soft_removal_not_erasure(env):
    client, _, _ = env
    assert post(client, facts()).status_code == 302
    html = client.get(URL).get_data(as_text=True)
    assert "Remove this entry from your current PAYE view" in html
    assert "Delete this entry" not in html


@pytest.mark.parametrize("change", [
    {"employment_slot": "0"}, {"employment_slot": "21"}, {"employment_slot": "1;drop"},
    {"gross_pay_to_date": "1e3"}, {"tax_paid_to_date": "-1"}, {"confirmation": "no"},
])
def test_hostile_or_unconfirmed_entry_is_rejected_without_write(env, change):
    client, owner, _ = env
    response = post(client, facts(**change))
    assert response.status_code == 400
    assert db.list_active_paye_manual_entries(owner, "2026/27") == []


def test_admission_retains_only_minimised_structured_facts():
    record = admit_manual_entry(facts(), tax_year="2026/27", observed_on=Clock.now().date())
    assert record["source_kind"] == "customer_confirmed_manual"
    assert record["provenance"] == "customer_confirmed_manual_cumulative_entry"
    assert record["completeness"] == "partial"
    assert not any("document" in key or "employer" in key or "national" in key for key in record)


@pytest.mark.parametrize(("field", "invalid"), [
    ("provenance", "employer:Acme Payroll"),
    ("source_kind", "payslip_upload"),
    ("gross_to_date", "1e3"),
    ("tax_paid_to_date", "-1.00"),
    ("effective_through", "2027-04-06"),
    ("observed_on", "not-a-date"),
    ("evidence_id", "employee-Acme-Payroll"),
])
def test_storage_revalidates_admission_and_rejects_internal_bypass(env, field, invalid):
    _, owner, _ = env
    record = admit_manual_entry(facts(), tax_year="2026/27", observed_on=Clock.now().date())
    record[field] = invalid
    with pytest.raises(ValueError):
        db.save_paye_manual_entry(owner, record)
    assert db.list_active_paye_manual_entries(owner, "2026/27") == []


def test_active_employment_slot_is_unique_and_replacement_is_transactional(env):
    _, owner, _ = env
    first = admit_manual_entry(facts(), tax_year="2026/27", observed_on=Clock.now().date())
    second = admit_manual_entry(facts(tax_paid_to_date="2200.00"), tax_year="2026/27", observed_on=Clock.now().date())
    db.save_paye_manual_entry(owner, first)
    db.save_paye_manual_entry(owner, second)
    active = db.list_active_paye_manual_entries(owner, "2026/27")
    assert len(active) == 1 and active[0]["evidence_id"] == second["evidence_id"]
    with db._connection() as connection:
        active_count = connection.execute(
            "SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=? AND tax_year=? "
            "AND employment_slot=1 AND replaced_at IS NULL AND deleted_at IS NULL",
            (owner, "2026/27"),
        ).fetchone()[0]
    assert active_count == 1


def test_manual_write_is_serialized_before_erasure_and_cannot_resurrect(env, monkeypatch):
    _, owner, _ = env
    record = admit_manual_entry(facts(), tax_year="2026/27", observed_on=Clock.now().date())
    checked, release, erasure_done = threading.Event(), threading.Event(), threading.Event()
    failures = []
    original = db.require_local_tax_writes_open

    def hold_after_barrier_read(conn, user_id):
        original(conn, user_id)
        checked.set()
        assert release.wait(2)

    monkeypatch.setattr(db, "require_local_tax_writes_open", hold_after_barrier_read)

    def save():
        try:
            db.save_paye_manual_entry(owner, record)
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    def erase():
        try:
            db.block_local_tax_data_writes(owner)
            with db._connection() as conn:
                conn.execute("DELETE FROM paye_manual_entries WHERE user_id=?", (owner,))
            db.complete_local_tax_data_erasure(owner)
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)
        finally:
            erasure_done.set()

    writer = threading.Thread(target=save); writer.start()
    assert checked.wait(2)
    eraser = threading.Thread(target=erase); eraser.start()
    assert not erasure_done.wait(0.1)
    release.set(); writer.join(2); eraser.join(2)
    assert failures == [] and erasure_done.is_set()
    assert db.list_active_paye_manual_entries(owner, "2026/27") == []

    monkeypatch.setattr(db, "require_local_tax_writes_open", original)
    with pytest.raises(ValueError, match="lifecycle"):
        db.save_paye_manual_entry(
            owner, admit_manual_entry(facts(employment_slot="2"), tax_year="2026/27",
                                      observed_on=Clock.now().date()),
        )
    db.block_local_tax_data_writes(owner)
    with db._connection() as conn:
        assert conn.execute(
            "SELECT state FROM local_tax_data_erasure_states WHERE user_id=?", (owner,)
        ).fetchone()["state"] == "erased"


def test_user_account_deletion_cascades_structured_paye_rows(env):
    _, owner, _ = env
    db.save_paye_manual_entry(
        owner, admit_manual_entry(facts(), tax_year="2026/27", observed_on=Clock.now().date())
    )
    with db._connection() as connection:
        connection.execute("DELETE FROM users WHERE id=?", (owner,))
        remaining = connection.execute(
            "SELECT COUNT(*) FROM paye_manual_entries WHERE user_id=?", (owner,)
        ).fetchone()[0]
    assert remaining == 0
