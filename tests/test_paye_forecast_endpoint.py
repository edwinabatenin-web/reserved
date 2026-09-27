"""Hostile real-request coverage for the disabled current PAYE forecast read."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

import reserved.database as db
import reserved.annual_position_durable_repository as durable_repository_module
import reserved.paye_durable_forecast_bridge as forecast_bridge
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.paye_reconciliation import make_paye_reconciliation_policy
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition, annual_to_cash_position_identity,
)
from reserved.paye_forecast_endpoint import (
    DurablePayeForecastEndpointError, DurablePayeForecastRuntime,
    RepositoryFuturePayFactsProvider,
    install_durable_paye_forecast_endpoint,
)
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayFrequency, FuturePaySource,
    PeriodCompleteness, make_future_pay_forecast_policy,
)
from reserved.annual_position_durable_repository import DurableAnnualPositionRepository
from reserved.annual_position_durable_repository import DurableAnnualPositionError
from tests.test_annual_position_durable_repository import _governance, _policy
from tests.test_paye_annual_bridge import durable_annual
from tests.test_annual_to_cash_integration import (
    annual_position_with_plan_2, compose as another_live_annual,
)
from tests.test_billing_composition import paid_event, runtime as billing_runtime


TODAY = date(2026, 10, 1)


def _entry():
    return {
        "tax_year": "2026/27", "employment_slot": 1,
        "evidence_id": "paye-manual-00000000000000000000000000000001",
        "source_kind": "customer_confirmed_manual",
        "provenance": "customer_confirmed_manual_cumulative_entry",
        "gross_to_date": "10000.00", "tax_paid_to_date": "1200.00", "tax_code": "1257L",
        "pay_frequency": "monthly", "pension_treatment": "none",
        "effective_through": "2026-09-30", "observed_on": "2026-10-01",
        "completeness": "partial",
    }


def _fact(owner, **changes):
    values = dict(
        source=FuturePaySource.CUSTOMER_CONFIRMED, fact_id="future-pay-1",
        source_evidence_id="confirmation-1", source_evidence_digest="a" * 64,
        owner_id=str(owner), business_id="business-1", tax_year="2026-27",
        employment_id="manual-employment-1", gross_pay="5000.00",
        expected_tax_deduction="750.00", pay_date=date(2026, 10, 31),
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        confirmed_on=TODAY, frequency=FuturePayFrequency.MONTHLY,
        period_completeness=PeriodCompleteness.COMPLETE,
    )
    values.update(changes)
    return ConfirmedFuturePayFact(**values)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "forecast-endpoint.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("PAYE_DURABLE_FORECAST_ENABLED", raising=False)
    monkeypatch.setattr(forecast_bridge, "_server_date", lambda: TODAY)
    monkeypatch.setattr(
        durable_repository_module, "_utc_now",
        lambda: "2026-10-01T09:30:00+00:00",
    )
    billing = billing_runtime(tmp_path / "primary")
    app = create_app(billing_runtime=billing); app.config.update(TESTING=True)
    owner = db.get_or_create_user("forecast-owner", email="forecast@example.test")
    other = db.get_or_create_user("forecast-other", email="other@example.test")
    annual, repository = durable_annual(owner)
    db.save_paye_manual_entry(owner, _entry())
    paid_event(billing, owner)
    return app, owner, other, annual, repository, tmp_path


def _runtime(annual, repository, *, scope=None, annual_provider=None, future_provider=None):
    return DurablePayeForecastRuntime(
        repository=repository,
        annual_position_provider=annual_provider or (lambda *_: annual),
        future_facts_provider=future_provider or (lambda owner, *_: (_fact(owner),)),
        owner_scope_resolver=scope or (lambda _: ("business-1", "2026/27", "England")),
        reconciliation_policy=make_paye_reconciliation_policy(45, Decimal("1.00")),
        future_pay_policy=make_future_pay_forecast_policy(30, Decimal("100.00")),
    )


def _install(app, annual, repository, **kwargs):
    return install_durable_paye_forecast_endpoint(
        app, _runtime(annual, repository, **kwargs)
    )


def _paid_app(tmp_path, name, owner):
    billing = billing_runtime(tmp_path / name)
    app = create_app(billing_runtime=billing)
    app.config.update(TESTING=True)
    paid_event(billing, owner)
    return app


def _client(app, owner):
    value = app.test_client()
    with value.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return value


def test_disabled_and_preflight_failures_do_not_call_providers(prepared, monkeypatch):
    app, owner, other, annual, repository, _ = prepared
    calls = []
    _install(app, annual, repository,
             annual_provider=lambda *args: calls.append(("annual", args)) or annual,
             future_provider=lambda *args: calls.append(("future", args)) or (_fact(owner),))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    assert _client(app, other).get("/v2/paye/current-forecast").status_code == 403
    assert _client(app, owner).get("/v2/paye/current-forecast?year=2020").status_code == 404
    assert _client(app, owner).post("/v2/paye/current-forecast", json={}).status_code == 405
    assert calls == []
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    response = _client(app, owner).get("/v2/paye/current-forecast")
    assert response.status_code == 200
    assert [name for name, _ in calls] == ["annual", "future"]


def test_unauthenticated_no_adapter_and_invalid_annual_never_reach_future_provider(prepared, monkeypatch):
    app, owner, _, annual, repository, tmp_path = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    calls = []
    _install(app, annual, repository,
             annual_provider=lambda *args: calls.append("annual") or None,
             future_provider=lambda *args: calls.append("future") or (_fact(owner),))
    # Shared signed-session middleware redirects unauthenticated clients before
    # this endpoint can evaluate any injected provider.
    assert app.test_client().get("/v2/paye/current-forecast").status_code == 302
    assert calls == []
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    assert calls == ["annual"]
    # A repository with no independently configured verifier is preflighted
    # before either injected provider.
    no_adapter = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
    )
    app2 = _paid_app(tmp_path, "no-adapter", owner)
    no_adapter_calls = []
    _install(app2, annual, no_adapter,
             annual_provider=lambda *args: no_adapter_calls.append("annual") or annual,
             future_provider=lambda *args: no_adapter_calls.append("future") or (_fact(owner),))
    assert _client(app2, owner).get("/v2/paye/current-forecast").status_code == 404
    assert no_adapter_calls == []


@pytest.mark.parametrize("invalid_annual,assert_distinct_identity", [
    (lambda: another_live_annual(annual=annual_position_with_plan_2("England")), True),
    (lambda: object.__new__(AnnualToCashPosition), False),
])
def test_unbound_or_forged_annual_is_rejected_before_future_provider(
    prepared, monkeypatch, invalid_annual, assert_distinct_identity,
):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    calls = []
    candidate = invalid_annual()
    if assert_distinct_identity:
        assert annual_to_cash_position_identity(candidate) != annual_to_cash_position_identity(annual)
    _install(app, annual, repository,
             annual_provider=lambda *args: calls.append("annual") or candidate,
             future_provider=lambda *args: calls.append("future") or (_fact(owner),))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    assert calls == ["annual"]


def test_success_is_minimal_and_never_claims_liability_or_actions(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    _install(app, annual, repository)
    response = _client(app, owner).get("/v2/paye/current-forecast")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {
        "tax_year", "as_of", "forecast_status", "coverage_scope", "confirmed_fact_count",
        "reconciled_paye_tax_paid", "expected_future_tax_deduction",
        "projected_tax_deducted_total", "material_threshold_reached", "uncertainties",
    }
    assert body["tax_year"] == "2026-27"
    assert body["as_of"] == "2026-10-01"
    assert body["projected_tax_deducted_total"] == "1950.00"
    forbidden = {"owner", "business", "source", "provenance", "gross", "liability", "refund",
                 "reserve", "payment", "transfer", "filing", "action"}
    assert not forbidden.intersection(body)


def test_bad_scope_or_invalid_provider_output_is_value_free(prepared, monkeypatch):
    app, owner, _, annual, repository, tmp_path = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    _install(app, annual, repository, scope=lambda _: ("business-1", "2025/26", "England"))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    app2 = _paid_app(tmp_path, "invalid-provider", owner)
    _install(app2, annual, repository, future_provider=lambda *_: [])
    assert _client(app2, owner).get("/v2/paye/current-forecast").status_code == 404


def test_invalid_installation_does_not_mutate_flask(prepared):
    app, _, _, annual, repository, _ = prepared
    rules, extensions = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()), dict(app.extensions)
    with pytest.raises(DurablePayeForecastEndpointError):
        DurablePayeForecastRuntime(
            repository=repository, annual_position_provider=lambda *_: annual,
            future_facts_provider=lambda *_: (), owner_scope_resolver=lambda _: ("business-1", "2026/27", "England"),
            reconciliation_policy=object(), future_pay_policy=object(),
        )
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == rules
    assert app.extensions == extensions


def test_route_and_endpoint_collisions_do_not_mutate_flask(prepared):
    app, _, _, annual, repository, _ = prepared
    _install(app, annual, repository)
    rules, extensions = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()), dict(app.extensions)
    with pytest.raises(DurablePayeForecastEndpointError):
        _install(app, annual, repository)
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == rules
    assert app.extensions == extensions


def test_direct_install_without_active_paid_boundary_is_refused(prepared):
    _, _, _, annual, repository, _ = prepared
    app = create_app()
    with pytest.raises(DurablePayeForecastEndpointError, match="paid-surface"):
        install_durable_paye_forecast_endpoint(app, _runtime(annual, repository))
    assert "reserved.paye.durable_forecast_endpoint" not in app.extensions


def test_application_factory_composes_only_complete_paid_forecast_runtime(
    prepared, monkeypatch,
):
    _, owner, _, annual, repository, tmp_path = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    billing = billing_runtime(tmp_path / "factory")
    app = create_app(
        billing_runtime=billing,
        paye_forecast_runtime=_runtime(annual, repository),
    )
    app.config.update(TESTING=True)
    client = _client(app, owner)
    assert "reserved.paye.durable_forecast_endpoint" in app.extensions
    assert client.get("/v2/paye/current-forecast").status_code == 403
    paid_event(billing, owner)
    assert client.get("/v2/paye/current-forecast").status_code == 200


def test_repository_backed_confirmed_period_can_be_updated_deleted_and_forecast(
    prepared, monkeypatch,
):
    _app, owner, _other, annual, repository, tmp_path = prepared
    source = "future-source:employment-1"
    assert repository.save_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity=source,
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        expected_gross_pay=Decimal("5000.00"),
        expected_tax_deducted=Decimal("750.00"),
        audit_reference="audit:future-pay-create",
    ) == source
    facts = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert len(facts) == 1
    assert facts[0].gross_pay == Decimal("5000.00")
    assert facts[0].expected_tax_deduction == Decimal("750.00")
    assert facts[0].source is FuturePaySource.CUSTOMER_CONFIRMED

    repository.save_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity=source,
        period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
        expected_gross_pay=Decimal("2000.00"),
        expected_tax_deducted=Decimal("300.00"),
        audit_reference="audit:future-pay-second-period",
    )
    two_periods = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert len(two_periods) == 2
    assert len({fact.source_evidence_id for fact in two_periods}) == 2
    assert {fact.employment_id for fact in two_periods} == {source}

    with pytest.raises(DurableAnnualPositionError, match="periods overlap"):
        repository.save_confirmed_future_pay_period(
            authenticated_user_id=owner, business_reference="business-1",
            tax_year="2026/27", source_identity=source,
            period_start=date(2026, 10, 20), period_end=date(2026, 11, 10),
            expected_gross_pay=Decimal("2500.00"),
            expected_tax_deducted=Decimal("375.00"),
            audit_reference="audit:future-pay-overlap-create",
        )
    unchanged = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert len(unchanged) == 2

    repository.save_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity=source,
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        expected_gross_pay=Decimal("5100.00"),
        expected_tax_deducted=Decimal("765.00"),
        audit_reference="audit:future-pay-update",
    )
    updated = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert [fact.expected_tax_deduction for fact in updated] == [
        Decimal("765.00"), Decimal("300.00"),
    ]

    with pytest.raises(DurableAnnualPositionError, match="periods overlap"):
        repository.save_confirmed_future_pay_period(
            authenticated_user_id=owner, business_reference="business-1",
            tax_year="2026/27", source_identity=source,
            period_start=date(2026, 10, 31), period_end=date(2026, 11, 2),
            expected_gross_pay=Decimal("300.00"),
            expected_tax_deducted=Decimal("45.00"),
            audit_reference="audit:future-pay-overlap-update",
        )
    still_updated = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert [fact.expected_tax_deduction for fact in still_updated] == [
        Decimal("765.00"), Decimal("300.00"),
    ]

    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    billing = billing_runtime(tmp_path / "repository-backed")
    runtime = _runtime(
        annual, repository,
        future_provider=RepositoryFuturePayFactsProvider(repository),
    )
    app = create_app(billing_runtime=billing, paye_forecast_runtime=runtime)
    app.config.update(TESTING=True)
    paid_event(billing, owner)
    body = _client(app, owner).get("/v2/paye/current-forecast").get_json()
    assert body["expected_future_tax_deduction"] == "1065.00"
    assert body["confirmed_fact_count"] == 2

    assert repository.delete_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity=source,
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        audit_reference="audit:future-pay-delete",
    ) is True
    remaining = repository.read_confirmed_future_pay_facts(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", nation="England", annual_position=annual,
    )
    assert len(remaining) == 1
    assert remaining[0].period_start == date(2026, 11, 1)


def test_future_pay_store_is_minimum_field_only_owner_bound_and_rejects_raw_content(
    prepared,
):
    _app, owner, other, annual, repository, _tmp_path = prepared
    with db._connection() as conn:
        columns = tuple(
            row[1] for row in conn.execute(
                "PRAGMA table_info(paye_confirmed_future_periods)"
            ).fetchall()
        )
    assert columns == (
        "user_id", "business_reference", "tax_year", "source_identity",
        "period_start", "period_end", "expected_gross_pay",
        "expected_tax_deducted", "confirmed_at",
    )
    values = dict(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity="future-source:employment-minimum",
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        expected_gross_pay=Decimal("5000.00"),
        expected_tax_deducted=Decimal("750.00"),
        audit_reference="audit:future-pay-minimum",
    )
    with pytest.raises(TypeError):
        repository.save_confirmed_future_pay_period(
            **values, raw_payslip=b"prohibited",
        )
    with pytest.raises(TypeError):
        repository.save_confirmed_future_pay_period(
            **values, free_text="prohibited",
        )
    with pytest.raises(TypeError):
        repository.save_confirmed_future_pay_period(
            **values, confirmed_at=datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc),
        )
    with pytest.raises(DurableAnnualPositionError, match="source identity"):
        repository.save_confirmed_future_pay_period(
            **(values | {"source_identity": "secret:raw-payslip"}),
        )
    with pytest.raises(DurableAnnualPositionError, match="active owner-to-business"):
        repository.save_confirmed_future_pay_period(
            **(values | {"authenticated_user_id": other}),
        )
    repository.save_confirmed_future_pay_period(**values)
    with pytest.raises(DurableAnnualPositionError):
        repository.read_confirmed_future_pay_facts(
            authenticated_user_id=other, business_reference="business-1",
            tax_year="2026/27", nation="England", annual_position=annual,
        )


def test_repository_future_provider_must_share_the_runtime_repository(prepared):
    _app, _owner, _other, annual, repository, _tmp_path = prepared
    other_repository = DurableAnnualPositionRepository(
        _governance(), evidence_reference_policy=_policy(),
        membership_issuer_reference="membership:approved-v1",
        lifecycle_issuer_reference="lifecycle:approved-v1",
    )
    with pytest.raises(DurablePayeForecastEndpointError, match="does not match"):
        _runtime(
            annual, repository,
            future_provider=RepositoryFuturePayFactsProvider(other_repository),
        )


def test_repository_future_facts_are_rechecked_after_composition(prepared, monkeypatch):
    _app, owner, _other, annual, repository, tmp_path = prepared
    source = "future-source:race-check"
    repository.save_confirmed_future_pay_period(
        authenticated_user_id=owner, business_reference="business-1",
        tax_year="2026/27", source_identity=source,
        period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
        expected_gross_pay=Decimal("5000.00"),
        expected_tax_deducted=Decimal("750.00"),
        audit_reference="audit:future-pay-race-create",
    )
    original = repository.read_confirmed_future_pay_facts
    reads = []

    def read_then_change(**kwargs):
        result = original(**kwargs)
        reads.append(result)
        if len(reads) == 1:
            repository.delete_confirmed_future_pay_period(
                authenticated_user_id=owner, business_reference="business-1",
                tax_year="2026/27", source_identity=source,
                period_start=date(2026, 10, 2), period_end=date(2026, 10, 31),
                audit_reference="audit:future-pay-race-delete",
            )
        return result

    monkeypatch.setattr(repository, "read_confirmed_future_pay_facts", read_then_change)
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    billing = billing_runtime(tmp_path / "repository-race")
    app = create_app(
        billing_runtime=billing,
        paye_forecast_runtime=_runtime(
            annual, repository,
            future_provider=RepositoryFuturePayFactsProvider(repository),
        ),
    )
    app.config.update(TESTING=True)
    paid_event(billing, owner)
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    assert len(reads) == 2 and reads[0] and reads[1] == ()


def test_forecast_runtime_without_billing_or_with_invalid_shape_remains_closed(
    prepared, monkeypatch,
):
    _, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    app = create_app(paye_forecast_runtime=_runtime(annual, repository))
    app.config.update(TESTING=True)
    assert "reserved.paye.durable_forecast_endpoint" not in app.extensions
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    invalid = create_app(paye_forecast_runtime=object())
    invalid.config.update(TESTING=True)
    assert "reserved.paye.durable_forecast_endpoint" not in invalid.extensions
    assert _client(invalid, owner).get("/v2/paye/current-forecast").status_code == 404


class _TupleSubclass(tuple):
    pass


@pytest.mark.parametrize("factory", [
    lambda owner: (),
    lambda owner: [],
    lambda owner: _TupleSubclass((_fact(owner),)),
    lambda owner: (object.__new__(ConfirmedFuturePayFact),),
    lambda owner: (_fact(owner + 1),),
    lambda owner: (_fact(owner, tax_year="2025-26", pay_date=date(2025, 10, 31),
                         period_start=date(2025, 10, 2), period_end=date(2025, 10, 31),
                         confirmed_on=date(2025, 10, 1)),),
    lambda owner: (_fact(owner, business_id="other-business"),),
    lambda owner: (_fact(owner, confirmed_on=date(2026, 8, 1)),),
    lambda owner: (_fact(owner, period_completeness=PeriodCompleteness.PARTIAL),),
])
def test_invalid_future_fact_shapes_and_bindings_are_value_free(prepared, monkeypatch, factory):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    _install(app, annual, repository, future_provider=lambda current, *_: factory(current))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404


def test_duplicate_future_fact_identity_provenance_and_period_overlap_are_value_free(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    duplicate_id = _fact(owner, fact_id="future-pay-2", source_evidence_id="confirmation-2",
                         source_evidence_digest="b" * 64)
    same_id = _fact(owner, fact_id="future-pay-2", source_evidence_id="confirmation-3",
                    source_evidence_digest="c" * 64, employment_id="manual-employment-2")
    _install(app, annual, repository, future_provider=lambda *_: (duplicate_id, same_id))
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404


def test_switch_is_independent_and_response_uncertainties_are_fixed(prepared, monkeypatch):
    app, owner, _, annual, repository, _ = prepared
    monkeypatch.setenv("PAYE_DURABLE_COMPOSITION_ENABLED", "1")
    _install(app, annual, repository)
    assert _client(app, owner).get("/v2/paye/current-forecast").status_code == 404
    monkeypatch.setenv("PAYE_DURABLE_FORECAST_ENABLED", "1")
    body = _client(app, owner).get("/v2/paye/current-forecast").get_json()
    assert body["uncertainties"] == [
        "future_pay_is_confirmed_input_not_observed_payment",
        "expected_tax_deduction_is_explicit_input_not_payroll_calculation",
        "forecast_does_not_establish_final_tax_liability",
    ]
    assert "annual_liability" not in body
