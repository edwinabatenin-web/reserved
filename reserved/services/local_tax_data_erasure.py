"""Disabled-first HTTP composition seam for bounded local tax-data erasure.

This module deliberately has no import-time route registration.  A future
composition root must inject the reviewed repository, raw-payslip boundary and
clearance provider explicitly.  It neither deletes a user identity nor makes a
claim about backups, quarantine, or a whole-account erasure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from flask import Flask, abort, jsonify, request

from reserved.auth import current_user_id, require_auth
from reserved.config import local_tax_data_erasure_enabled
from reserved import database
from reserved.services.paye_payslip_intake import PayslipIntakeError


_RULE = "/v2/account/local-tax-data-erasure"
_ENDPOINT = "v2.local_tax_data_erasure"
_AUDIT_REFERENCE = "audit:local-tax-data-erasure"
_KEY = "reserved.local_tax_data_erasure"


class LocalTaxDataErasureInstallationError(ValueError):
    """Installation was rejected before changing the Flask application."""


@dataclass(frozen=True, slots=True)
class LocalTaxDataErasureRuntime:
    """Complete server-owned dependencies for the dormant erasure route."""

    durable_repository: object
    payslip_boundary: object
    clearance_provider: object

    def __post_init__(self) -> None:
        _require_dependencies(
            self.durable_repository, self.payslip_boundary, self.clearance_provider,
        )


def _complete_structured(owner: int, callback):
    result = callback()
    database.complete_local_tax_data_erasure(owner)
    return result


def _require_dependencies(repository, payslip_boundary, clearance_provider) -> None:
    from reserved.annual_position_durable_repository import DurableAnnualPositionRepository
    from reserved.services.paye_payslip_intake import PayslipIntakeBoundary

    if type(repository) is not DurableAnnualPositionRepository:
        raise LocalTaxDataErasureInstallationError("exact durable repository is required")
    if type(payslip_boundary) is not PayslipIntakeBoundary:
        raise LocalTaxDataErasureInstallationError("exact payslip boundary is required")
    for value, method in ((repository, "assert_account_erasure_clearances"),
                          (repository, "execute_local_tax_data_erasure"),
                          (payslip_boundary, "erase_owner_for_account_lifecycle_then")):
        if not callable(getattr(value, method, None)):
            raise LocalTaxDataErasureInstallationError("local tax-data erasure dependency is unavailable")
    if not callable(clearance_provider):
        raise LocalTaxDataErasureInstallationError("local tax-data erasure clearance provider is unavailable")


def _route_is_available(app) -> bool:
    return (_ENDPOINT not in app.view_functions
            and all(rule.rule != _RULE for rule in app.url_map.iter_rules()))


def install_local_tax_data_erasure(app, *, durable_repository, payslip_boundary,
                                   clearance_provider: Callable[..., tuple]) -> None:
    """Install the POST-only dormant route after validating all dependencies.

    The application's ordinary CSRF protection remains global; this installer
    deliberately adds no exemption.  Invalid installation attempts leave the
    Flask application untouched.
    """
    if type(app) is not Flask or app._got_first_request or _KEY in app.extensions:
        raise LocalTaxDataErasureInstallationError("exact pre-request Flask installation is required")
    _require_dependencies(durable_repository, payslip_boundary, clearance_provider)
    if not _route_is_available(app):
        raise LocalTaxDataErasureInstallationError("local tax-data erasure route collision")

    @require_auth
    def erase_local_tax_data():
        # Keep these cheap gates before consulting any authority provider.
        if not local_tax_data_erasure_enabled():
            abort(404)
        owner = current_user_id()
        if type(owner) is not int or owner <= 0:
            abort(403)
        if (request.args or request.files or request.mimetype != "application/x-www-form-urlencoded"
                or set(request.form.keys()) != {"csrf_token"}
                or len(request.form.getlist("csrf_token")) != 1):
            abort(400)

        try:
            clearances = clearance_provider(authenticated_user_id=owner)
            if type(clearances) is not tuple or len(clearances) != 2:
                abort(403)
            legal_hold_clearance, backup_expiry_clearance = clearances
            # This public assertion is non-mutating.  The execute call below
            # repeats it immediately before structured-row deletion.
            durable_repository.assert_account_erasure_clearances(
                authenticated_user_id=owner,
                legal_hold_clearance=legal_hold_clearance,
                backup_expiry_clearance=backup_expiry_clearance,
            )
            def erase_structured():
                # Reverify at the only point that can delete structured rows;
                # the raw boundary retains the owner admission barrier through
                # this callback, so a new raw intake cannot race in-between.
                durable_repository.assert_account_erasure_clearances(
                    authenticated_user_id=owner,
                    legal_hold_clearance=legal_hold_clearance,
                    backup_expiry_clearance=backup_expiry_clearance,
                )
                return durable_repository.execute_local_tax_data_erasure(
                    authenticated_user_id=owner,
                    audit_reference=_AUDIT_REFERENCE,
                    legal_hold_clearance=legal_hold_clearance,
                    backup_expiry_clearance=backup_expiry_clearance,
                )

            raw_files, result = payslip_boundary.erase_owner_for_account_lifecycle_then(
                authenticated_user_id=owner,
                before_raw_erasure=lambda: database.block_local_tax_data_writes(owner),
                after_raw_erasure=lambda: _complete_structured(owner, erase_structured),
            )
        except PayslipIntakeError:
            abort(409)
        except Exception:
            # An authority or durable-store failure never permits a partial
            # structured deletion.  The raw boundary has already preserved its
            # own metadata on failure.
            abort(403)

        return jsonify({
            "status": "local_tax_data_erased",
            "scope": "local_tax_data_only",
            "raw_payslip_files_deleted": raw_files,
            "annual_position_records_deleted": result.annual_position_records,
            "paye_manual_entries_deleted": result.paye_manual_entries,
            "backup_erasure": "not_asserted",
            "identity_erasure": "not_asserted",
            "quarantine_erasure": "not_asserted",
        })

    app.add_url_rule(_RULE, endpoint=_ENDPOINT, view_func=erase_local_tax_data,
                     methods=["POST"])
    app.extensions[_KEY] = object()


def install_local_tax_data_erasure_runtime(
    app: Flask, runtime: LocalTaxDataErasureRuntime,
) -> None:
    """Install only one exact, fully validated dependency bundle."""
    if type(runtime) is not LocalTaxDataErasureRuntime:
        raise LocalTaxDataErasureInstallationError(
            "exact local tax-data erasure runtime is required"
        )
    install_local_tax_data_erasure(
        app,
        durable_repository=runtime.durable_repository,
        payslip_boundary=runtime.payslip_boundary,
        clearance_provider=runtime.clearance_provider,
    )


__all__ = [
    "LocalTaxDataErasureInstallationError", "LocalTaxDataErasureRuntime",
    "install_local_tax_data_erasure", "install_local_tax_data_erasure_runtime",
]
