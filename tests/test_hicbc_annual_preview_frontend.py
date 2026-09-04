"""Rendered Flask form -> executed JS -> actual Flask response -> executed render.

Node runs the production script against a deliberately small DOM/event harness,
not a real browser. No network, dependency install, or live database is used.
"""
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
SCRIPT = ROOT / "reserved/static/js/hicbc_annual_preview.js"
URL = "/v2/hicbc/annual-preview"
MIXED = dict(employment_income="60000", sole_trade_profit="5000", savings_interest="1000",
             dividends="1000", uk_property_receipts="10000", uk_property_allowable_expenses="4000",
             brought_forward_uk_property_loss="1000", foreign_property_gross_receipts="3000",
             foreign_property_allowable_expenses="1000", gross_ras_pension="4000",
             residential_finance_costs="0", foreign_tax_paid="0", country="England")
CONFIRMS = ("full_tax_year_including_known_future", "uk_resident", "employment_basis", "other_ani_adjustments")


class FormParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.controls = {}
        self.year = self.token = None
        self.inside = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "csrf-token":
            self.token = attrs["content"]
        if tag == "form":
            self.inside = attrs.get("id") == "hicbc-annual-form"
            if self.inside:
                self.year = attrs["data-tax-year"]
        if self.inside and tag in ("input", "select"):
            self.controls[attrs["name"]] = dict(value=attrs.get("value", ""), checked="checked" in attrs)

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


HARNESS = r'''
const fs = require('fs'), vm = require('vm'), readline = require('readline');
let state, context, form, result, error, controls, listeners, pending = [], requests = [], jsonPending = [];
function node() {
  return {textContent:'', children:[], hidden:false, disabled:true, attrs:{}, focused:false,
    replaceChildren(){this.children=[];this.textContent='';}, appendChild(n){this.children.push(n);},
    setAttribute(k,v){this.attrs[k]=v;}, removeAttribute(k){delete this.attrs[k];}, focus(){this.focused=true;},
    set innerHTML(v){throw Error('unsafe HTML');}};
}
function init(c) {
  state=c; listeners={}; controls=Object.fromEntries(Object.entries(c.controls).map(([k,v])=>[k,Object.assign(node(),v)]));
  const elements=Object.values(controls);elements.namedItem=k=>controls[k];
  form=Object.assign(node(),{elements,dataset:{taxYear:c.year},addEventListener(k,f){listeners[k]=f;}});
  result=node();error=node(); const submit=node();
  const document={getElementById:k=>({'hicbc-annual-form':form,'annual-result':result,'annual-error':error,'annual-submit':submit}[k]),
    querySelector:()=>c.token ? {content:c.token}:null,createElement:()=>node()};
  const window={addEventListener(k,f){listeners[k]=f;}};
  context={document,window,AbortController,fetch:(url,options)=>new Promise((resolve,reject)=>{
    requests.push({url,method:options.method,headers:options.headers,body:options.body,
      credentials:options.credentials,redirect:options.redirect,cache:options.cache});
    pending.push({resolve,reject}); // Intentionally ignore abort: generation must protect too.
  })};
  for(const key of ['localStorage','sessionStorage']) Object.defineProperty(context,key,{get(){throw Error('storage');}});
  vm.runInNewContext(fs.readFileSync(c.script,'utf8'),context);
}
function snapshot(){return {requests, result:result.children.map(n=>n.textContent),error:error.hidden?'':error.textContent,
  invalid:Object.keys(controls).filter(k=>controls[k].attrs['aria-invalid']==='true'),busy:result.attrs['aria-busy'],focused:error.focused};}
const lines=readline.createInterface({input:process.stdin});
lines.on('line',async line=>{
 try {
  const c=JSON.parse(line);
  if(c.op==='init') init(c);
  if(c.op==='fill') for(const [k,v] of Object.entries(c.values)) {
    if(typeof v==='boolean') controls[k].checked=v;else controls[k].value=v;
  }
  if(c.op==='event') listeners[c.name]({preventDefault(){}});
  if(c.op==='resolve') pending[c.index].resolve({status:c.status,redirected:c.redirected||false,
    headers:{get:()=>c.content_type||'application/json'},json:async()=>{
      if(c.invalid_json) throw Error('synthetic private response');
      if(c.delay_json) return new Promise(resolve=>jsonPending.push(resolve));return c.body;}});
  if(c.op==='json') jsonPending[c.index](c.body);
  if(c.op==='reject') pending[c.index].reject(Error('synthetic private network error'));
  await new Promise(resolve=>setImmediate(resolve));
  process.stdout.write(JSON.stringify(snapshot())+'\n');
 } catch(e) {process.stdout.write(JSON.stringify({harness_error:String(e)})+'\n');}
});
'''


class Frontend:
    def __init__(self, html):
        self.form = FormParser(html)
        assert self.form.year and self.form.token
        self.proc = subprocess.Popen([NODE, "-e", HARNESS], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
        self.send(op="init", controls=self.form.controls, year=self.form.year,
                  token=self.form.token, script=str(SCRIPT))

    def send(self, **command):
        self.proc.stdin.write(json.dumps(command) + "\n")
        self.proc.stdin.flush()
        state = json.loads(self.proc.stdout.readline())
        assert "harness_error" not in state, state
        return state

    def fill(self, **changes):
        values = {**MIXED, **{name: True for name in CONFIRMS}, **changes}
        return self.send(op="fill", values=values)

    def submit(self):
        return self.send(op="event", name="submit")

    def deliver(self, response, index=0):
        return self.send(op="resolve", index=index, status=response.status_code,
                         content_type=response.content_type, body=response.get_json(silent=True))

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        assert self.proc.returncode == 0
        assert self.proc.stderr.read() == ""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "synthetic.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    monkeypatch.setenv("HICBC_ANNUAL_PREVIEW_ENABLED", "1")
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    owner = db.get_or_create_user("frontend-a", email="a@example.test", display_name="A")
    partner = db.get_or_create_user("frontend-b", email="b@example.test", display_name="B")
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    db.save_hicbc_estimate(owner, dict(tax_year="2026/27", child_benefit_claimant="person",
        child_benefit_annual="1406.60", has_relevant_partner=1, relationship_covers_full_year=1,
        partner_status_period_semantics="status_answer_full_year", representation="point",
        partner_ani_point="50000", completeness="complete_for_purpose", recency_state="current"))
    return app, client, owner, partner


@pytest.fixture
def ui(env):
    page = env[1].get("/v2/hicbc/")
    assert page.status_code == 200
    frontend = Frontend(page.get_data(as_text=True))
    yield frontend
    frontend.close()


def actual_post(client, request):
    assert request["url"] == URL
    assert request["credentials"] == "same-origin"
    assert request["redirect"] == "error"
    assert request["cache"] == "no-store"
    return client.post(request["url"], data=request["body"], headers=request["headers"])


def test_rendered_form_executed_request_and_actual_response(env, ui, caplog):
    assert len(ui.form.controls) == 17
    assert all(c == {"value": "", "checked": False} for c in ui.form.controls.values())
    with db._connection() as conn:
        before = tuple(conn.iterdump())
    ui.fill()
    sent = ui.submit()
    payload = json.loads(sent["requests"][0]["body"])
    assert {key: payload[key] for key in MIXED} == MIXED
    assert payload["full_tax_year_including_known_future"] is True
    response = actual_post(env[1], sent["requests"][0])
    assert response.status_code == 200
    assert response.json["projected_user_hicbc"] == "703.00"
    shown = ui.deliver(response)
    assert "Estimated charge that may apply to you: £703.00" in shown["result"], (shown, response.json)
    assert not shown["error"]
    assert "no-store" in response.headers["Cache-Control"]
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == before
    rendered = " ".join(shown["result"]) + caplog.text
    for private in ("60000", "60,000", "70000", "70,000", "50000", "50,000", "partner_ani", "evidence_id"):
        assert private not in rendered
    assert caplog.text == ""


@pytest.mark.parametrize("changes", [{"employment_income": ""}, {"employment_income": " 60000"},
    {"employment_income": "6e4"}, {"employment_income": "-1"}, {"employment_income": "0.001"},
    {"country": "unsupported"}, *[{key: False} for key in CONFIRMS]])
def test_unknown_unsupported_or_invalid_does_not_submit(ui, changes):
    ui.fill(**changes)
    state = ui.submit()
    assert not state["requests"] and not state["result"]
    assert state["invalid"] and state["focused"]
    assert "cannot calculate" in state["error"]


def test_edit_and_out_of_order_responses_cannot_resurrect_results(env, ui):
    ui.fill()
    first = ui.submit()["requests"][0]
    response = actual_post(env[1], first)
    ui.send(op="event", name="input")
    assert ui.deliver(response)["result"] == []
    ui.submit()
    ui.submit()
    state = ui.send(op="reject", index=2)
    assert state["error"] and not state["result"]
    assert ui.deliver(response, index=1)["result"] == []
    ui.submit()
    assert "£703.00" in " ".join(ui.deliver(response, index=3)["result"])
    assert ui.send(op="event", name="change")["result"] == []


@pytest.mark.parametrize("change", [dict(status=302), dict(redirected=True), dict(content_type="text/html"),
    dict(invalid_json=True), dict(body={}), dict(status=500), dict(status=409)])
def test_bad_response_is_non_result(env, ui, change):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    command = dict(op="resolve", index=0, status=200, body=response.json)
    command.update(change)
    state = ui.send(**command)
    assert not state["result"] and state["error"]
    assert "synthetic private" not in state["error"]


def test_hostile_text_is_text_not_html_and_extra_fields_refused(env, ui):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    body = response.json
    body["messages"] = ['<img src=x onerror="alert(1)">']
    state = ui.send(op="resolve", index=0, status=200, body=body)
    assert body["messages"][0] in state["result"]  # textContent only; innerHTML throws in harness.
    ui.submit()
    body["partner_ani"] = "50000"
    state = ui.send(op="resolve", index=1, status=200, body=body)
    assert not state["result"] and state["error"]


def test_link_refusal_revocation_and_relink_actual_responses(env, ui):
    _, client, owner, partner = env
    ui.fill()
    request = ui.submit()["requests"][0]
    invitation = db.create_hicbc_link_invitation(owner, "2026/27")
    assert db.accept_hicbc_link_invitation(partner, invitation, "2026/27")
    response = actual_post(client, request)
    assert response.status_code == 409
    state = ui.deliver(response)
    assert not any("£" in text for text in state["result"])
    assert response.json["headline"] in state["result"]
    db.revoke_hicbc_link(owner, "2026/27")
    ui.submit()
    permitted = actual_post(client, request)
    assert permitted.status_code == 200
    invitation = db.create_hicbc_link_invitation(owner, "2026/27")
    assert db.accept_hicbc_link_invitation(partner, invitation, "2026/27")
    ui.submit()
    closed = actual_post(client, request)
    assert closed.status_code == 409
    ui.deliver(closed, index=2)
    assert not any("£" in text for text in ui.deliver(permitted, index=1)["result"])


@pytest.mark.parametrize("key,value", [("HICBC_ANNUAL_PREVIEW_ENABLED", "0"),
    ("HICBC_ENABLED", "0"), ("FLASK_ENV", "production"), ("CLERK_PUBLISHABLE_KEY", "pk_live_synthetic")])
def test_ui_gate_no_panel_or_script(env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    response = env[1].get("/v2/hicbc/")
    html = response.get_data(as_text=True)
    assert 'id="hicbc-annual-form"' not in html
    assert 'js/hicbc_annual_preview.js' not in html


def test_auth_csrf_and_legacy_distinction(env, ui):
    _, client, _, _ = env
    html = client.get("/v2/hicbc/").get_data(as_text=True)
    assert "does not update the profile-based current estimate" in html
    assert "<noscript>" in html and 'id="annual-submit"' in html
    assert 'action="/v2/hicbc/estimate"' in html  # existing saved controls remain.
    ui.fill()
    request = ui.submit()["requests"][0]
    original = request["headers"].pop("X-CSRFToken")
    assert actual_post(client, request).status_code == 400
    request["headers"]["X-CSRFToken"] = original
    with client.session_transaction() as session:
        session.pop(_SK_USER_ID)
    response = actual_post(client, request)
    assert response.status_code == 302
    assert not ui.deliver(response)["result"]


def test_response_json_finishing_after_edit_is_ignored(env, ui):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    ui.send(op="resolve", index=0, status=200, delay_json=True)
    ui.send(op="event", name="input")
    assert not ui.send(op="json", index=0, body=response.json)["result"]


@pytest.mark.parametrize("event", ["reset", "pagehide"])
def test_reset_and_navigation_clear_visible_result(env, ui, event):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    assert ui.deliver(response)["result"]
    assert not ui.send(op="event", name=event)["result"]


def test_range_and_missing_evidence_use_actual_existing_view(env, ui):
    _, client, owner, _ = env
    row = dict(db.get_hicbc_estimate(owner, "2026/27"))
    row.update(representation="range", partner_ani_point=None, partner_ani_low="65000", partner_ani_high="75000")
    db.save_hicbc_estimate(owner, row)
    ui.fill()
    request = ui.submit()["requests"][0]
    response = actual_post(client, request)
    assert response.json["projected_user_hicbc"] is None
    state = ui.deliver(response)
    assert "Possible charge that may apply to you: between £0.00 and £703.00." in state["result"]
    assert all(value not in " ".join(state["result"]) for value in ("65,000", "75,000", "65000", "75000"))
    db.delete_hicbc_estimate(owner, "2026/27")
    ui.submit()
    response = actual_post(client, request)
    state = ui.deliver(response, index=1)
    assert not any("£" in text for text in state["result"])


@pytest.mark.parametrize("field,value", [("tax_year", "2025/26"), ("country", "Scotland"),
    ("employment_income", ""), ("other_ani_adjustments", "gift_aid")])
def test_server_refusal_of_modified_request_clears_result(env, ui, field, value):
    ui.fill()
    sent = ui.submit()["requests"][0]
    payload = json.loads(sent["body"])
    payload[field] = value
    sent["body"] = json.dumps(payload)
    response = actual_post(env[1], sent)
    assert response.status_code == 400
    state = ui.deliver(response)
    assert state["error"] and not state["result"]


def test_network_error_clears_result_without_echo(ui):
    ui.fill()
    ui.submit()
    state = ui.send(op="reject", index=0)
    assert state["error"] and not state["result"]
    assert "synthetic private" not in state["error"]


@pytest.mark.parametrize("changes,status", [
    ({"responsibility_status": "insufficient_facts", "calculation_status": "insufficient_facts"}, 200),
    ({"projected_user_hicbc": None, "possible_charge_low": "703.00", "possible_charge_high": "0.00"}, 200),
    ({"projected_user_hicbc": None, "possible_charge_low": None, "possible_charge_high": None}, 409),
    ({"calculation_status": "unknown_enum"}, 200),
    ({"responsibility_status": "unknown_enum"}, 200),
    ({"household_change_status": "unknown_enum"}, 200),
    ({"calculation_status": "bounded_range"}, 200),
    ({"calculation_status": "calculated_with_material_uncertainty"}, 200),
    ({"possible_charge_low": None, "possible_charge_high": None}, 200),
    ({"possible_charge_low": "0.00"}, 200),
    ({"possible_charge_high": "999.00"}, 200),
    ({"headline": "A determinate or otherwise forged headline"}, 200),
])
def test_inconsistent_producer_status_amount_or_headline_is_non_result(env, ui, changes, status):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    body = {**response.json, **changes}
    state = ui.send(op="resolve", index=0, status=status, body=body)
    assert not state["result"] and state["error"]


@pytest.mark.parametrize("changes", [
    {"headline": "Your estimated charge may apply"},
    {"based_on_partner_estimate": True},
    {"messages": ["This estimate uses partner information you supplied."]},
    {"messages": []},
    {"household_change_status": "changed"},
])
def test_409_must_be_exact_existing_closed_view(env, ui, changes):
    _, client, owner, partner = env
    token = db.create_hicbc_link_invitation(owner, "2026/27")
    assert db.accept_hicbc_link_invitation(partner, token, "2026/27")
    ui.fill()
    response = actual_post(client, ui.submit()["requests"][0])
    assert response.status_code == 409
    state = ui.send(op="resolve", index=0, status=409, body={**response.json, **changes})
    assert not state["result"] and state["error"]


@pytest.mark.parametrize("row_changes,expected", [
    ({"child_benefit_annual": "0"}, ("no_charge", "not_applicable")),
    ({"partner_ani_point": "75000"}, ("partner_liable", "calculated")),
    ({"recency_state": "stale"}, ("person_liable", "calculated_with_material_uncertainty")),
    ({"partner_ani_point": "75000", "recency_state": "stale"}, ("partner_liable", "calculated_with_material_uncertainty")),
    ({"has_relevant_partner": None}, ("insufficient_facts", "insufficient_facts")),
])
def test_existing_producer_shapes_remain_renderable(env, ui, row_changes, expected):
    _, client, owner, _ = env
    row = dict(db.get_hicbc_estimate(owner, "2026/27"))
    row.update(row_changes)
    db.save_hicbc_estimate(owner, row)
    ui.fill()
    response = actual_post(client, ui.submit()["requests"][0])
    assert (response.json["responsibility_status"], response.json["calculation_status"]) == expected, (response.status_code, response.json["messages"])
    state = ui.deliver(response)
    assert not state["error"] and response.json["headline"] in state["result"]
    if expected[1] in ("insufficient_facts", "calculated_with_material_uncertainty"):
        assert "Possible charge that may apply to you: between £0.00 and £703.00." in state["result"]


@pytest.mark.parametrize("dispatch_input", [True, False])
def test_blank_edit_or_even_programmatic_blank_submit_clears_success(env, ui, dispatch_input):
    ui.fill()
    response = actual_post(env[1], ui.submit()["requests"][0])
    assert "£703.00" in " ".join(ui.deliver(response)["result"])
    ui.send(op="fill", values={"employment_income": ""})
    if dispatch_input:
        assert not ui.send(op="event", name="input")["result"]
    state = ui.submit()
    assert not state["result"] and state["error"] and len(state["requests"]) == 1
    assert "employment_income" in state["invalid"]


def test_reversed_actual_bounded_range_is_non_result(env, ui):
    _, client, owner, _ = env
    row = dict(db.get_hicbc_estimate(owner, "2026/27"))
    row.update(representation="range", partner_ani_point=None, partner_ani_low="65000", partner_ani_high="75000")
    db.save_hicbc_estimate(owner, row)
    ui.fill()
    response = actual_post(client, ui.submit()["requests"][0])
    assert response.json["calculation_status"] == "bounded_range"
    body = response.json
    body["possible_charge_low"], body["possible_charge_high"] = body["possible_charge_high"], body["possible_charge_low"]
    state = ui.send(op="resolve", index=0, status=200, body=body)
    assert not state["result"] and state["error"]
