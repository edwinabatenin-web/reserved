"""Dependency-free launch-quality regressions for security and accessibility."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "reserved_security_standalone", ROOT / "reserved" / "security.py"
)
_SECURITY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SECURITY)
spreadsheet_safe = _SECURITY.spreadsheet_safe

_VALIDATION_SPEC = importlib.util.spec_from_file_location(
    "reserved_settings_validation_standalone", ROOT / "reserved" / "settings_validation.py"
)
_VALIDATION = importlib.util.module_from_spec(_VALIDATION_SPEC)
_VALIDATION_SPEC.loader.exec_module(_VALIDATION)
validate_settings_form = _VALIDATION.validate_settings_form
settings_error_values = _VALIDATION.settings_error_values
settings_field_errors = _VALIDATION.settings_field_errors


def test_csv_export_neutralises_spreadsheet_formulae():
    for value in ("=1+1", "+cmd", "-2+3", "@SUM(A1:A2)", "  =HYPERLINK(\"x\")"):
        assert spreadsheet_safe(value).startswith("'")
    assert spreadsheet_safe("ordinary feedback") == "ordinary feedback"
    assert spreadsheet_safe(5) == 5


def test_shared_layout_has_keyboard_skip_link_and_main_target():
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    assert 'class="skip-link" href="#main-content"' in base
    assert '<main class="main" id="main-content" tabindex="-1">' in base


def test_privacy_notice_does_not_make_known_false_storage_claims():
    privacy = (ROOT / "reserved" / "templates" / "privacy.html").read_text().lower()
    assert "session data is temporary and is not persisted" not in privacy
    assert "does not contain any personally identifiable information" not in privacy
    assert "<strong>nobody.</strong>" not in privacy
    assert "do not use real financial information in the public preview" in privacy


def test_configured_turnstile_fails_closed_on_verification_outage():
    routes = (ROOT / "reserved" / "web" / "routes.py").read_text()
    assert "resp.raise_for_status()" in routes
    assert "if not secret and not site_key:" in routes
    assert "if not secret:" in routes
    assert 'return False, "The security check is temporarily unavailable.' in routes
    assert "return True, None  # fail open" not in routes


def test_csp_constrains_forms_and_secondary_resource_contexts():
    app_factory = (ROOT / "reserved" / "__init__.py").read_text()
    for directive in (
        '"form-action \'self\'"',
        '"manifest-src \'self\'"',
        '"media-src \'self\'"',
        '"worker-src \'self\'"',
    ):
        assert directive in app_factory


def test_public_modal_results_are_announced_to_assistive_technology():
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    assert 'id="early-access-error" class="form-error-msg" role="alert"' in base
    assert 'id="feedback-error" class="form-error-msg" role="alert"' in base
    assert 'id="early-access-thanks" hidden class="modal-thanks" role="status"' in base
    assert 'id="feedback-thanks" hidden role="status"' in base


def test_public_modals_support_escape_and_focus_restoration():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    assert 'if (e.key === "Escape") {' in app_js
    assert "if (earlyAccessBtn) earlyAccessBtn.focus();" in app_js
    assert "if (feedbackBtn) feedbackBtn.focus();" in app_js


def test_public_modals_contain_keyboard_focus():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    assert "function trapModalFocus(modal, event)" in app_js
    assert 'event.key !== "Tab"' in app_js
    assert "event.shiftKey && document.activeElement === first" in app_js
    assert "!event.shiftKey && document.activeElement === last" in app_js
    assert 'id="early-access-modal" hidden role="dialog" aria-modal="true"' in base
    assert 'aria-describedby="ea-modal-description" tabindex="-1"' in base
    assert 'id="feedback-modal" hidden role="dialog" aria-modal="true"' in base


def test_public_modals_make_background_inert_while_open():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    assert '".app-shell, #rsvd-tour, .action-pill-group"' in app_js
    assert "function syncModalBackground()" in app_js
    assert 'region.setAttribute("inert", "");' in app_js
    assert 'region.setAttribute("aria-hidden", "true");' in app_js
    assert 'region.removeAttribute("inert");' in app_js
    assert 'region.removeAttribute("aria-hidden");' in app_js


def test_public_forms_do_not_overstate_anonymity_or_non_sharing():
    base = (ROOT / "reserved" / "templates" / "base.html").read_text().lower()
    assert "feedback is used anonymously" not in base
    assert "we won't share them with anyone else" not in base
    assert "store limited request context" in base
    assert "service providers described in our" in base


def test_settings_tabs_expose_state_and_support_standard_keyboard_navigation():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    for template in ("settings.html", "v2/settings.html"):
        settings = (ROOT / "reserved" / "templates" / template).read_text()
        assert 'role="tablist" aria-label="Settings sections"' in settings
    assert "function activateSettingsTab(tab, moveFocus = false)" in app_js
    assert 'item.setAttribute("aria-selected"' in app_js
    assert 'tab.setAttribute("aria-controls"' in app_js
    assert 'section.setAttribute("role", "tabpanel")' in app_js
    assert 'event.key === "ArrowRight"' in app_js
    assert 'event.key === "ArrowLeft"' in app_js
    assert 'event.key === "Home"' in app_js
    assert 'event.key === "End"' in app_js


def test_founder_login_error_is_programmatically_associated_with_password():
    login = (ROOT / "reserved" / "templates" / "founder" / "login.html").read_text()
    assert 'aria-invalid="true" aria-describedby="login-error"' in login
    assert 'id="login-error" role="alert"' in login


def test_settings_copy_does_not_claim_all_data_is_session_only_or_unsaved_changes_apply():
    settings = (ROOT / "reserved" / "templates" / "settings.html").read_text().lower()
    assert "settings are saved to your browser session" not in settings
    assert "changes take effect immediately" not in settings
    assert "saved changes are reflected" in settings


def test_primary_navigation_and_flash_messages_expose_semantic_state():
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    assert '<nav class="nav" aria-label="Primary">' in base
    assert base.count('aria-current="page"') >= 8
    assert 'role="{{ \'alert\' if category == \'error\' else \'status\' }}"' in base
    assert 'aria-live="{{ \'assertive\' if category == \'error\' else \'polite\' }}"' in base


def test_public_form_errors_are_announced_associated_and_focused():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    assert "function _eaShowError(msg, field = null)" in app_js
    assert 'field.setAttribute("aria-invalid", "true")' in app_js
    assert 'field.setAttribute("aria-describedby", "early-access-error")' in app_js
    assert '_eaShowError("Please enter your name.", nameField)' in app_js
    assert '_eaShowError("Please enter a valid email address.", emailField)' in app_js
    assert "feedbackError.focus();" in app_js


def test_settings_forms_have_accessible_multi_field_error_handling():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    for template in ("settings.html", "v2/settings.html"):
        settings = (ROOT / "reserved" / "templates" / template).read_text()
        assert "data-settings-form novalidate" in settings
        assert 'class="flash flash-error settings-error-summary" id="settings-error-summary" role="alert"' in settings
        assert 'tabindex="-1"{% if not settings_errors %} hidden' in settings
    assert 'const settingsForm = document.querySelector("[data-settings-form]")' in app_js
    assert ".filter((field) => !field.checkValidity())" in app_js
    assert 'field.setAttribute("aria-invalid", "true")' in app_js
    assert 'field.setAttribute("aria-describedby", "settings-error-summary")' in app_js
    assert "errorSummary.focus();" in app_js
    assert 'invalidFields[0].closest("[data-settings-section]")' in app_js
    assert "if (owningTab) activateSettingsTab(owningTab);" in app_js
    assert "invalidFields[0].focus();" in app_js


def test_settings_server_validation_rejects_invalid_untrusted_values():
    valid = {
        "day_job_salary": "50000", "ytd_freelance_profit": "1200.50",
        "pension": "0", "child_benefit_annual": "", "child_benefit_children": "2",
        "entity_type": "sole_trader", "student_loan": "none",
        "accounting_method": "cash_basis", "vat_status": "not_vat_registered",
    }
    assert validate_settings_form(valid) == []
    for field, bad in (
        ("day_job_salary", "-1"), ("pension", "NaN"),
        ("ytd_freelance_profit", "Infinity"), ("child_benefit_annual", "invalid"),
        ("child_benefit_children", "999"), ("student_loan", "invented"),
    ):
        submission = {**valid, field: bad}
        assert validate_settings_form(submission), field


def test_server_settings_errors_are_rendered_and_focused_accessibly():
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    for template in ("settings.html", "v2/settings.html"):
        settings = (ROOT / "reserved" / "templates" / template).read_text()
        assert "{% if settings_error_fields %}<ul>" in settings
        assert 'data-error-field="{{ field }}"' in settings
        assert "data-server-errors" in settings
    assert 'errorSummary.hasAttribute("data-server-errors")' in app_js


def test_server_settings_errors_are_field_keyed_and_linked_to_controls():
    invalid = {
        "day_job_salary": "NaN", "ytd_freelance_profit": "0", "pension": "0",
        "child_benefit_annual": "", "child_benefit_children": "0",
        "entity_type": "sole_trader", "student_loan": "none",
        "accounting_method": "cash_basis", "vat_status": "not_vat_registered",
    }
    assert settings_field_errors(invalid) == {
        "day_job_salary": "Annual PAYE salary must be a valid amount of zero or more."
    }
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    assert 'settingsForm.elements.namedItem(link.dataset.errorField)' in app_js
    assert 'field.id = `settings-field-${link.dataset.errorField}`' in app_js
    assert 'link.addEventListener("click"' in app_js
    assert "if (tab) activateSettingsTab(tab);" in app_js


def test_sensitive_route_prefixes_are_never_cached():
    app_factory = (ROOT / "reserved" / "__init__.py").read_text()
    assert 'has_sensitive_session = (' in app_factory
    assert '_session.get("_v2_user_id") is not None' in app_factory
    assert '_session.get("_founder_authed") is True' in app_factory
    assert 'if has_sensitive_session or _req.path.startswith(("/v2/", "/founder")):' in app_factory
    assert 'h["Cache-Control"] = "no-store, max-age=0"' in app_factory
    assert 'h["Pragma"] = "no-cache"' in app_factory
    assert 'h["Expires"] = "0"' in app_factory
    assert 'h.add("Vary", "Cookie")' in app_factory


def test_founder_privilege_boundary_clears_session_on_login_and_logout():
    founder = (ROOT / "reserved" / "web" / "founder.py").read_text()
    successful_login = founder.split("if _check_password(password):", 1)[1].split("else:", 1)[0]
    assert successful_login.index("session.clear()") < successful_login.index(
        "session[_SESSION_KEY] = True"
    )
    logout = founder.split("def logout():", 1)[1].split("@founder.get", 1)[0]
    assert "session.clear()" in logout
    assert "session.modified = True" in logout
    assert "session.pop(_SESSION_KEY" not in logout


def test_operational_logs_do_not_retain_raw_ip_fragments_or_email_domains():
    routes = (ROOT / "reserved" / "web" / "routes.py").read_text()
    founder = (ROOT / "reserved" / "web" / "founder.py").read_text()
    for source in (routes, founder):
        assert "ip_prefix" not in source
        assert "ip[:8]" not in source
    assert "email_domain" not in routes


def test_customer_logout_is_csrf_protected_post_not_cross_site_get():
    v2 = (ROOT / "reserved" / "web" / "v2.py").read_text()
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    secondary = (ROOT / "reserved" / "templates" / "v2" / "_nav.html").read_text()
    assert '@v2.post("/logout")' in v2
    assert '@v2.get("/logout")' not in v2
    for template in (base, secondary):
        assert 'method="post" action="{{ url_for(\'v2.logout\') }}"' in template
        assert 'name="csrf_token" value="{{ csrf_token() }}"' in template


def test_disclosure_controls_and_notification_link_are_keyboard_accessible():
    base = (ROOT / "reserved" / "templates" / "base.html").read_text()
    app_js = (ROOT / "reserved" / "static" / "js" / "app.js").read_text()
    assert 'aria-controls="sidebar" aria-expanded="false"' in base
    assert 'aria-controls="notification-panel" aria-expanded="false"' in base
    assert 'id="notification-panel" data-notification-panel hidden' in base
    assert 'id="notif-estimate" hidden role="link" tabindex="0"' in base
    assert "const setNotificationsOpen = (open) =>" in app_js
    assert 'notificationButton.setAttribute("aria-expanded"' in app_js
    assert 'event.key === "Escape" && !notificationPanel.hidden' in app_js
    assert 'e.key === "Enter" || e.key === " "' in app_js
    assert "notifEstimate.dataset.notificationLink" in app_js


def test_invalid_settings_return_preserves_submitted_values_for_correction():
    existing = {"day_job_salary": "50000", "first_name": "Existing"}
    submitted = {
        "day_job_salary": "not-a-number", "first_name": "Updated",
        "child_benefit_children": "invalid",
    }
    values = settings_error_values(submitted, existing)
    assert values["day_job_salary"] == "not-a-number"
    assert values["first_name"] == "Updated"
    assert values["child_benefit_children"] == "invalid"
