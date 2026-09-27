"""Exact paid-route consequence for later-period restoration."""
from datetime import timedelta

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import paid_access_guard as guard
from reserved.billing import runtime_entitlement_admission as runtime
from reserved.billing import local_paid_surface_access as local_surfaces
from tests import test_w10_local_paid_surface_access as existing_surfaces
from tests import test_w10_local_dashboard_access as dashboard
from tests.test_w10_stripe_later_period_restoration import RestorationHarness

app = existing_surfaces.app


def test_all_31_paid_routes_deny_before_access_then_allow_until_exclusive_end(tmp_path):
    h = RestorationHarness(tmp_path/'routes.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); result = h.restore()
        admission = runtime.bind_later_period_restoration_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_later_period_restoration_fact,
            project_admitted_billing_fact=source.project_later_period_restoration_fact)
        entitlement = runtime.admit_later_period_restoration_runtime_entitlement(
            admission, authenticated_owner_id='synthetic-owner',
            billing_account_id='synthetic-billing', subscription_id='sub_Synthetic',
            admitted_billing_fact=result.fact, evaluated_at_utc=h.initial_end)
        boundary = guard.bind_later_period_restoration_paid_access_guard(
            validate_runtime_entitlement=
                runtime.validate_later_period_restoration_runtime_entitlement,
            project_runtime_entitlement=
                runtime.project_later_period_restoration_runtime_entitlement)
        assert len(guard.PAID_ENDPOINTS) == 31
        details = source.later_period_restoration_fact_details(result.fact)
        from datetime import datetime
        end = datetime.fromisoformat(details['service_end'])
        for endpoint in guard.PAID_ENDPOINTS:
            outcomes = []
            for instant in (h.initial_end - timedelta(microseconds=1),
                            h.initial_end, end - timedelta(microseconds=1), end):
                decision = guard.evaluate_later_period_restoration_paid_access(
                    boundary, endpoint=endpoint,
                    authenticated_owner_id='synthetic-owner',
                    current_runtime_entitlement=entitlement,
                    evaluated_at_utc=instant)
                outcomes.append(dict(
                    guard.validate_later_period_restoration_paid_access_decision(
                        decision))['allowed'])
            assert outcomes == [False, True, True, False]
    finally:
        h.repo.close()


def test_exact_27_non_paid_routes_retain_existing_functions_and_controls(app, tmp_path):
    client, uid = dashboard._authenticated_client(app)
    h = RestorationHarness(tmp_path/'installed.db', uid=uid)
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); assert h.restore().disposition == 'admitted'
        before = dict(app.view_functions)
        non_paid = {name for name in before if name not in guard.PAID_ENDPOINTS}
        assert len(guard.PAID_ENDPOINTS) == 31 and len(non_paid) == 27
        local_surfaces.install_local_exact_utc_paid_surface_access(
            app, authority=h.authority, repository=h.repo, clock=lambda: h.initial_end)
        assert all(app.view_functions[name] is before[name] for name in non_paid)
        assert client.get('/about').status_code == 200
        assert app.test_client().get('/v2/settings').status_code == 302
    finally:
        h.repo.close()
