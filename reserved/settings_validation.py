"""Validation for untrusted settings form input, independent of tax logic."""

from decimal import Decimal, InvalidOperation


_NUMERIC_FIELDS = {
    "day_job_salary": "Annual PAYE salary",
    "ytd_freelance_profit": "Freelance profit to date",
    "pension": "Personal pension contributions",
    "child_benefit_annual": "Child Benefit annual total",
}

_CHOICES = {
    "entity_type": {"sole_trader", "limited_company"},
    "student_loan": {"none", "plan_1", "plan_2", "plan_4", "plan_5", "postgraduate"},
    "accounting_method": {"cash_basis", "traditional_accounting"},
    "vat_status": {"not_vat_registered", "vat_registered"},
}


def settings_field_errors(form) -> dict[str, str]:
    """Return field-keyed errors without normalising or mutating input."""
    errors: dict[str, str] = {}
    for field, label in _NUMERIC_FIELDS.items():
        raw = str(form.get(field, "") or "").strip()
        if field == "child_benefit_annual" and not raw:
            continue
        try:
            value = Decimal(raw or "0")
            if not value.is_finite() or value < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errors[field] = f"{label} must be a valid amount of zero or more."

    for field, allowed in _CHOICES.items():
        if str(form.get(field, "")) not in allowed:
            errors[field] = "This selected setting is not recognised."

    children = str(form.get("child_benefit_children", "0") or "0")
    if children not in {"0", "1", "2", "3", "4", "5"}:
        errors["child_benefit_children"] = (
            "Number of children in the Child Benefit claim must be between 0 and 5."
        )
    return errors


def validate_settings_form(form) -> list[str]:
    """Return human-readable errors for callers that do not need field keys."""
    return list(settings_field_errors(form).values())


def settings_error_values(form, existing: dict) -> dict:
    """Preserve submitted values for correction without normalising them."""
    values = dict(existing)
    for field in (
        "first_name", "trading_name", "entity_type", "day_job_salary",
        "ytd_freelance_profit", "pension", "student_loan",
        "accounting_method", "vat_status", "child_benefit_annual",
    ):
        if field in form:
            values[field] = form.get(field, "")
    raw_children = str(form.get("child_benefit_children", "0") or "0")
    values["child_benefit_children"] = int(raw_children) if raw_children.isdigit() else raw_children
    return values
