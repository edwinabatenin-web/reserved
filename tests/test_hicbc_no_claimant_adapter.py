"""Synthetic real-request regression for the UI/storage-none engine boundary."""
import pytest

import reserved.database as db
from reserved.auth import _SK_USER_ID
from tests.test_hicbc_annual_preview_frontend import env, Frontend, FormParser


def token(client):
    page = client.get("/v2/hicbc/")
    assert page.status_code == 200
    return FormParser(page.get_data(as_text=True)).token


def save(client, **changes):
    data = dict(child_benefit_claimant="none", child_benefit_children="0",
                child_benefit_weeks_entitled="", child_benefit_annual="",
                has_relevant_partner="no", relationship_covers_full_year="yes",
                tax_year="2026/27", csrf_token=token(client))
    data.update(changes)
    return client.post("/v2/hicbc/estimate", data=data)


def source(**changes):
    from tests.test_hicbc_annual_source_runtime import facts
    return facts(**changes)


def annual(client, **changes):
    return client.post("/v2/hicbc/annual-preview", json=source(**changes),
                       headers={"X-CSRFToken": token(client)})


def profile(owner):
    db.save_profile_by_user(owner, dict(income_estimate=70000, pension_contribution=0,
                                       tax_year="2026/27"))


def stored_none(owner, **changes):
    row = dict(tax_year="2026/27", child_benefit_claimant="none", receives_child_benefit=0,
               child_benefit_annual=None, child_benefit_children=0, child_benefit_weeks_entitled=None,
               has_relevant_partner=0, relationship_covers_full_year=1,
               partner_status_period_semantics="status_answer_full_year")
    row.update(changes)
    children = row["child_benefit_children"]
    row["child_benefit_children"] = 0
    db.save_hicbc_estimate(owner, row)
    # Corrupt legacy rows can exist even though the current writer int-casts
    # counts. Inject only into this disposable synthetic database.
    with db._connection() as conn:
        conn.execute("UPDATE hicbc_estimates SET child_benefit_children = ? WHERE user_id = ? AND tax_year = ?",
                     (children, owner, "2026/27"))


def assert_closed(response):
    assert response.status_code == 200
    assert response.json["responsibility_status"] == "insufficient_facts"
    assert response.json["projected_user_hicbc"] is None
    assert response.json["possible_charge_low"] is None
    assert response.json["possible_charge_high"] is None


@pytest.mark.parametrize("annual_amount", ["", "0", "0.00"])
def test_actual_save_page_result_annual_and_frontend_zero(env, annual_amount):
    _, client, owner, _ = env
    profile(owner)
    response = save(client, child_benefit_annual=annual_amount)
    assert response.status_code == 302
    row = dict(db.get_hicbc_estimate(owner, "2026/27"))
    assert row["child_benefit_claimant"] == "none"
    page = client.get(response.location)
    assert page.status_code == 200
    assert 'value="none" selected' in page.get_data(as_text=True)
    with db._connection() as conn:
        before = tuple(conn.iterdump())
    response = client.get("/v2/hicbc/result")
    assert response.json["projected_user_hicbc"] == "0.00"
    assert response.json["responsibility_status"] == "no_charge"
    ui = Frontend(page.get_data(as_text=True))
    try:
        ui.fill()
        request = ui.submit()["requests"][0]
        response = client.post(request["url"], data=request["body"], headers=request["headers"])
        assert response.status_code == 200
        assert response.json["projected_user_hicbc"] == "0.00"
        state = ui.deliver(response)
        assert "Estimated charge that may apply to you: £0.00" in state["result"]
        assert not state["error"]
    finally:
        ui.close()
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("changes", [
    {"child_benefit_annual": "1406.60"}, {"child_benefit_annual": "-1"},
    {"child_benefit_annual": "bad-private-amount"}, {"child_benefit_annual": "NaN"},
    {"child_benefit_annual": "Infinity"}, {"child_benefit_children": 1},
    {"child_benefit_children": "bad-private-count"}, {"child_benefit_children": -1},
    {"child_benefit_children": "0.5"}, {"child_benefit_weeks_entitled": 52},
    {"child_benefit_weeks_entitled": -1}, {"child_benefit_weeks_entitled": 54},
    {"child_benefit_weeks_entitled": "bad-private-weeks"}, {"receives_child_benefit": 1},
    {"receives_child_benefit": "malformed"},
    {"child_benefit_annual": "0", "child_benefit_children": 1, "child_benefit_weeks_entitled": 0},
    {"child_benefit_children": 0, "child_benefit_weeks_entitled": 52},
])
def test_none_conflicting_or_malformed_entitlement_fails_closed_without_mutation(env, changes, caplog):
    _, client, owner, _ = env
    profile(owner)
    stored_none(owner, **changes)
    with db._connection() as conn:
        before = tuple(conn.iterdump())
    page = client.get("/v2/hicbc/")
    assert page.status_code == 200
    assert_closed(client.get("/v2/hicbc/result"))
    response = annual(client)
    assert_closed(response)
    assert "bad-private" not in response.get_data(as_text=True) + caplog.text
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == before
    assert caplog.text == ""


@pytest.mark.parametrize("changes", [dict(child_benefit_annual="1406.60"),
    dict(child_benefit_children="1", child_benefit_weeks_entitled="52")])
def test_actual_save_conflict_remains_saved_but_result_is_non_actionable(env, changes):
    _, client, owner, _ = env
    profile(owner)
    response = save(client, **changes)
    assert response.status_code == 302
    assert client.get(response.location).status_code == 200
    assert_closed(client.get("/v2/hicbc/result"))
    assert_closed(annual(client))
    row = db.get_hicbc_estimate(owner, "2026/27")
    assert row["child_benefit_claimant"] == "none"
    for key, value in changes.items():
        assert str(row[key]) == value


@pytest.mark.parametrize("changes", [dict(child_benefit_annual="NaN"),
    dict(child_benefit_annual="-1"), dict(child_benefit_children="bad"),
    dict(child_benefit_weeks_entitled="-1")])
def test_malformed_form_refused_before_write(env, changes):
    _, client, owner, _ = env
    before = dict(db.get_hicbc_estimate(owner, "2026/27"))
    assert save(client, **changes).status_code == 400
    assert dict(db.get_hicbc_estimate(owner, "2026/27")) == before


def test_unknown_own_ani_and_unknown_claimant_or_amount_are_not_zero(env):
    _, client, owner, _ = env
    stored_none(owner)
    assert_closed(client.get("/v2/hicbc/result"))  # no own profile evidence
    assert annual(client).json["projected_user_hicbc"] == "0.00"  # own annual facts are explicit
    profile(owner)
    for changes in (dict(child_benefit_claimant=None, receives_child_benefit=None),
                    dict(child_benefit_claimant="unknown", receives_child_benefit=None),
                    dict(child_benefit_claimant="person", receives_child_benefit=1)):
        stored_none(owner, **changes)
        assert_closed(client.get("/v2/hicbc/result"))
        assert_closed(annual(client))


def test_legacy_zero_preserves_existing_normalisation_not_partner_inference(env):
    _, client, owner, _ = env
    profile(owner)
    stored_none(owner, child_benefit_claimant=None)
    assert annual(client).json["responsibility_status"] == "no_charge"
    assert db.get_hicbc_estimate(owner, "2026/27")["child_benefit_claimant"] is None
    stored_none(owner, child_benefit_claimant=None, child_benefit_annual="1406.60")
    assert_closed(annual(client))


@pytest.mark.parametrize("claimant,partner_ani,expected", [("person", "50000", "703.00"),
    ("partner", "75000", "0.00"), ("partner", "50000", "703.00")])
def test_positive_claimant_contracts_unchanged(env, claimant, partner_ani, expected):
    _, client, owner, _ = env
    profile(owner)
    row = dict(db.get_hicbc_estimate(owner, "2026/27"))
    row.update(child_benefit_claimant=claimant, partner_ani_point=partner_ani)
    db.save_hicbc_estimate(owner, row)
    assert annual(client).json["projected_user_hicbc"] == expected
    assert client.get("/v2/hicbc/result").json["projected_user_hicbc"] == expected


def test_link_auth_csrf_privacy_and_owner_boundaries_unchanged(env, caplog):
    _, client, owner, other = env
    stored_none(owner)
    invitation = db.create_hicbc_link_invitation(owner, "2026/27")
    assert db.accept_hicbc_link_invitation(other, invitation, "2026/27")
    response = annual(client)
    assert response.status_code == 409 and response.json["projected_user_hicbc"] is None
    assert "no-store" in response.headers["Cache-Control"]
    assert "Cookie" in response.headers["Vary"]
    for value in ("70000", "70,000", "50000", "50,000", "user_id", "evidence_id"):
        assert value not in response.get_data(as_text=True) + caplog.text
    assert client.post("/v2/hicbc/estimate", data={"child_benefit_claimant": "none"}).status_code == 400
    csrf = token(client)
    with client.session_transaction() as session:
        session[_SK_USER_ID] = other
    db.revoke_hicbc_link(other, "2026/27")
    assert_closed(annual(client))  # cannot use first owner's saved none
    with client.session_transaction() as session:
        session.pop(_SK_USER_ID)
    response = client.post("/v2/hicbc/annual-preview", json=source(), headers={"X-CSRFToken": csrf})
    assert response.status_code == 302
