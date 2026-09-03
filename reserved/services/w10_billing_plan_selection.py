"""Fail-closed W10-S6D renderer for one selected settled billing plan.

The public renderer accepts an untrusted S6A presentation and one untrusted
path key. It emits either one exact settled label plus the exact VAT
qualification or one fixed value-free unavailable state. It creates no action,
identifier, calculation, policy, persistence, provider or network boundary.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.services.w10_billing_presentation import (
    W10BillingPresentation,
    w10_billing_presentation_authority_version,
    w10_billing_presentation_source_identity,
)


_EXPECTED_CONTRACT = "reserved-w10-billing-presentation/1.0"
_EXPECTED_AUTHORITY = "FD-W10-001/2026-09-02/v1"
_EXPECTED_SOURCE = (
    "w10-billing-source:sha256-"
    "ff07c995665ba95c1953c0f1c72c0747d8c020091865430f295c383de48e6f4e"
)
_EXPECTED_LABELS = (
    "£29 per month",
    "£156 for six months",
    "£288 per year",
)
_EXPECTED_VAT = "Prices include VAT where applicable."
_PLAN_KEYS = ("monthly", "six_month", "yearly")


def _bind_selection_model(
    presentation_type: type,
    authority_accessor: object,
    source_accessor: object,
    expected_contract: str,
    expected_authority: str,
    expected_source: str,
    expected_labels: tuple[str, ...],
    expected_vat: str,
    plan_keys: tuple[str, ...],
):
    unavailable = (False, None, None)

    def selection_model(value: object, plan_key: object) -> tuple[bool, str | None, str | None]:
        if type(plan_key) is not str or plan_key not in plan_keys:
            return unavailable
        if type(value) is not presentation_type:
            return unavailable
        try:
            contract = object.__getattribute__(value, "contract_version")
            plans = object.__getattribute__(value, "plans")
            vat = object.__getattribute__(value, "vat_qualification")
            authority = authority_accessor(value)  # type: ignore[operator]
            source = source_accessor(value)  # type: ignore[operator]
            if (
                type(contract) is not str
                or type(plans) is not tuple
                or type(vat) is not str
                or type(authority) is not str
                or type(source) is not str
                or len(plans) != len(expected_labels)
            ):
                return unavailable
            labels = tuple(object.__getattribute__(card, "label") for card in plans)
            if (
                any(type(label) is not str for label in labels)
                or contract != expected_contract
                or labels != expected_labels
                or vat != expected_vat
                or authority != expected_authority
                or source != expected_source
            ):
                return unavailable
            return (True, labels[plan_keys.index(plan_key)], expected_vat)
        except Exception:
            return unavailable

    return selection_model


_selection_model = _bind_selection_model(
    W10BillingPresentation,
    w10_billing_presentation_authority_version,
    w10_billing_presentation_source_identity,
    _EXPECTED_CONTRACT,
    _EXPECTED_AUTHORITY,
    _EXPECTED_SOURCE,
    _EXPECTED_LABELS,
    _EXPECTED_VAT,
    _PLAN_KEYS,
)


def _bind_selection_renderer(
    projector: object,
    environment_type: type,
    loader_type: type,
    autoescape_selector: object,
    template_root: Path,
):
    def render_w10_billing_plan_selection_fragment(value: object, plan_key: object) -> str:
        model = projector(value, plan_key)  # type: ignore[operator]
        environment = environment_type(
            loader=loader_type(template_root),
            autoescape=autoescape_selector(("html",)),  # type: ignore[operator]
        )
        return environment.get_template(
            "v2/_w10_billing_plan_selection.html"
        ).render(model=model)

    return render_w10_billing_plan_selection_fragment


render_w10_billing_plan_selection_fragment = _bind_selection_renderer(
    _selection_model,
    Environment,
    FileSystemLoader,
    select_autoescape,
    Path(__file__).resolve().parents[1] / "templates",
)


__all__ = ("render_w10_billing_plan_selection_fragment",)
