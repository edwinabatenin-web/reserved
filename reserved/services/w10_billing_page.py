"""Pure, fail-closed supported renderer for the W10 billing-plan fragment.

The standalone template is an internal composition detail. Rendering it with a
caller-created ``model`` is not a supported application or security boundary.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.services.w10_billing_presentation import (
    W10BillingPresentation,
    w10_billing_presentation_authority_version,
    w10_billing_presentation_source_identity,
)

_AVAILABLE = "available"
_REVIEW_REQUIRED = "review_required"
_PRESENTATION_CONTRACT_VERSION = "reserved-w10-billing-presentation/1.0"
_EXPECTED_AUTHORITY_VERSION = "FD-W10-001/2026-09-02/v1"
_EXPECTED_SOURCE_IDENTITY = (
    "w10-billing-source:sha256-"
    "ff07c995665ba95c1953c0f1c72c0747d8c020091865430f295c383de48e6f4e"
)
_EXPECTED_LABELS = (
    "£29 per month",
    "£156 for six months",
    "£288 per year",
)
_VAT_QUALIFICATION = "Prices include VAT where applicable."


class W10BillingPageContext:
    """Detached immutable data accepted by the billing-plan template."""

    __slots__ = (
        "status",
        "contract_version",
        "plan_labels",
        "vat_qualification",
        "_authority_version",
        "_source_identity",
    )

    def __init__(
        self,
        status: str,
        contract_version: str | None = None,
        plan_labels: tuple[str, ...] = (),
        vat_qualification: str | None = None,
        *,
        _authority_version: str | None = None,
        _source_identity: str | None = None,
    ) -> None:
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "contract_version", contract_version)
        object.__setattr__(self, "plan_labels", plan_labels)
        object.__setattr__(self, "vat_qualification", vat_qualification)
        object.__setattr__(self, "_authority_version", _authority_version)
        object.__setattr__(self, "_source_identity", _source_identity)
        _validate_context(self)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("W10BillingPageContext is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("W10BillingPageContext is immutable")

    def __repr__(self) -> str:
        try:
            _validate_context(self)
        except Exception:
            return "W10BillingPageContext(<invalid-state>)"
        return f"W10BillingPageContext({self.status!r})"

    def __copy__(self) -> W10BillingPageContext:
        _validate_context(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> W10BillingPageContext:
        _validate_context(self)
        memo[id(self)] = self
        return self


def _validate_context(value: object) -> W10BillingPageContext:
    if type(value) is not W10BillingPageContext:
        raise TypeError("context must be an exact W10BillingPageContext")
    status = object.__getattribute__(value, "status")
    contract_version = object.__getattribute__(value, "contract_version")
    plan_labels = object.__getattribute__(value, "plan_labels")
    vat_qualification = object.__getattribute__(value, "vat_qualification")
    authority_version = object.__getattribute__(value, "_authority_version")
    source_identity = object.__getattribute__(value, "_source_identity")
    if type(status) is not str:
        raise TypeError("status must be an exact string")
    if status == _REVIEW_REQUIRED:
        if (
            contract_version is not None
            or type(plan_labels) is not tuple
            or len(plan_labels) != 0
            or vat_qualification is not None
            or authority_version is not None
            or source_identity is not None
        ):
            raise ValueError("unsupported closed rendering context")
        return value
    if status != _AVAILABLE:
        raise ValueError("unsupported rendering status")
    if (
        type(contract_version) is not str
        or type(plan_labels) is not tuple
        or type(vat_qualification) is not str
        or type(authority_version) is not str
        or type(source_identity) is not str
        or len(plan_labels) != len(_EXPECTED_LABELS)
        or any(type(item) is not str for item in plan_labels)
    ):
        raise TypeError("rendering context values must have exact types")
    if (
        contract_version != _PRESENTATION_CONTRACT_VERSION
        or plan_labels != _EXPECTED_LABELS
        or vat_qualification != _VAT_QUALIFICATION
        or authority_version != _EXPECTED_AUTHORITY_VERSION
        or source_identity != _EXPECTED_SOURCE_IDENTITY
    ):
        raise ValueError("unsupported billing rendering context")
    return value


def _bind_rendering_boundary(
    context_type: type = W10BillingPageContext,
    presentation_type: type = W10BillingPresentation,
    authority_accessor: object = w10_billing_presentation_authority_version,
    source_accessor: object = w10_billing_presentation_source_identity,
    available: str = _AVAILABLE,
    contract_version: str = _PRESENTATION_CONTRACT_VERSION,
    labels: tuple[str, ...] = _EXPECTED_LABELS,
    vat_qualification: str = _VAT_QUALIFICATION,
    authority_version: str = _EXPECTED_AUTHORITY_VERSION,
    source_identity: str = _EXPECTED_SOURCE_IDENTITY,
    review_required: str = _REVIEW_REQUIRED,
):
    """Bind trusted types, operations and copy before public globals can change."""
    closed_model = (False, (), None)
    available_model = (True, labels, vat_qualification)

    def make_context(
        status: str,
        actual_contract: str | None = None,
        actual_labels: tuple[str, ...] = (),
        actual_vat: str | None = None,
        actual_authority: str | None = None,
        actual_source: str | None = None,
    ) -> W10BillingPageContext:
        value = object.__new__(context_type)
        object.__setattr__(value, "status", status)
        object.__setattr__(value, "contract_version", actual_contract)
        object.__setattr__(value, "plan_labels", actual_labels)
        object.__setattr__(value, "vat_qualification", actual_vat)
        object.__setattr__(value, "_authority_version", actual_authority)
        object.__setattr__(value, "_source_identity", actual_source)
        return value

    def exact_context(value: object) -> bool:
        if type(value) is not context_type:
            return False
        try:
            status = object.__getattribute__(value, "status")
            actual_contract = object.__getattribute__(value, "contract_version")
            actual_labels = object.__getattribute__(value, "plan_labels")
            actual_vat = object.__getattribute__(value, "vat_qualification")
            actual_authority = object.__getattribute__(value, "_authority_version")
            actual_source = object.__getattribute__(value, "_source_identity")
            if (
                type(status) is not str
                or type(actual_contract) is not str
                or type(actual_labels) is not tuple
                or type(actual_vat) is not str
                or type(actual_authority) is not str
                or type(actual_source) is not str
                or len(actual_labels) != len(labels)
                or any(type(item) is not str for item in actual_labels)
            ):
                return False
            return (
                status == available
                and actual_contract == contract_version
                and actual_labels == labels
                and actual_vat == vat_qualification
                and actual_authority == authority_version
                and actual_source == source_identity
            )
        except Exception:
            return False

    def render_model(value: object) -> tuple[bool, tuple[str, ...], str | None]:
        """Return only a canonical immutable template model, else the fixed closure."""
        return available_model if exact_context(value) else closed_model

    def page_context(value: object) -> W10BillingPageContext:
        """Copy a bound exact S6A presentation, otherwise return one closed state."""
        if type(value) is not presentation_type:
            return make_context(review_required)
        try:
            actual_authority = authority_accessor(value)  # type: ignore[operator]
            actual_source = source_accessor(value)  # type: ignore[operator]
            actual_contract = object.__getattribute__(value, "contract_version")
            plans = object.__getattribute__(value, "plans")
            actual_vat = object.__getattribute__(value, "vat_qualification")
            if type(plans) is not tuple:
                return make_context(review_required)
            actual_labels = tuple(object.__getattribute__(card, "label") for card in plans)
            context = make_context(
                available,
                actual_contract,
                actual_labels,
                actual_vat,
                actual_authority,
                actual_source,
            )
            return context if exact_context(context) else make_context(review_required)
        except Exception:
            return make_context(review_required)

    return page_context, render_model


_w10_billing_page_context, _w10_billing_page_render_model = _bind_rendering_boundary()


def _bind_supported_renderer(
    sanitizer: object = _w10_billing_page_context,
    projection: object = _w10_billing_page_render_model,
    environment_type: type = Environment,
    loader_type: type = FileSystemLoader,
    autoescape_selector: object = select_autoescape,
    template_root: Path = Path(__file__).resolve().parents[1] / "templates",
):
    """Bind the complete supported boundary against public-global rebinding."""

    def render_w10_billing_plans_fragment(value: object) -> str:
        """Render an untrusted S6A presentation, failing closed for all others."""
        context = sanitizer(value)  # type: ignore[operator]
        model = projection(context)  # type: ignore[operator]
        environment = environment_type(
            loader=loader_type(template_root),
            autoescape=autoescape_selector(("html",)),  # type: ignore[operator]
        )
        return environment.get_template("v2/_w10_billing_plans.html").render(model=model)

    return render_w10_billing_plans_fragment


render_w10_billing_plans_fragment = _bind_supported_renderer()


__all__ = (
    "render_w10_billing_plans_fragment",
)
