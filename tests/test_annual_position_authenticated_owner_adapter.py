"""Adversarial acceptance tests for the pure W9-S3D owner adapter."""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import date, timedelta
from pathlib import Path

import pytest
from flask import Flask, globals as flask_globals

import reserved.auth as auth
import reserved.annual_position_authenticated_owner_adapter as subject
import reserved.annual_position_projection_repository_adapter as s3c
import reserved.billing.event_inbox_contract as owner_contract
from reserved.annual_position_persistence_contract import (
    admit_annual_position_projection,
    supersede_annual_position_projection,
)
from reserved.annual_position_projection_repository_adapter import (
    extract_structural_candidate,
)
from tests.test_annual_to_cash_integration import compose
from tests.test_w8_annual_cash_customer_handoff import project


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved" / "annual_position_authenticated_owner_adapter.py"
DOCUMENT = ROOT / "docs" / "W9_S3D_AUTHENTICATED_OWNER_ADAPTER.md"
OWNED_PATHS = {
    "reserved/annual_position_authenticated_owner_adapter.py",
    "tests/test_annual_position_authenticated_owner_adapter.py",
    "docs/W9_S3D_AUTHENTICATED_OWNER_ADAPTER.md",
}
MISSING = object()


@pytest.fixture
def app():
    application = Flask(__name__)
    application.config.update(SECRET_KEY="synthetic-w9-s3d-only", TESTING=True)
    return application


def admitted(*, user_id="41", business_id="business-41"):
    annual = compose()
    result = project(annual, user_id=user_id, business_id=business_id)
    assert result is not None
    return annual, result, admit_annual_position_projection(annual, result)


def adapt(projection, *, business=MISSING, evaluated_on=MISSING,
          previous_projection=None, previous_candidate=None):
    return subject.adapt_authenticated_owner_projection(
        projection=projection,
        authenticated_business_reference=(
            projection.business_id if business is MISSING else business
        ),
        evaluated_on=projection.as_of if evaluated_on is MISSING else evaluated_on,
        previous_projection=previous_projection,
        previous_structural_candidate=previous_candidate,
    )


def session(app, owner=41):
    context = app.test_request_context("/")
    context.push()
    auth.set_user_session(owner, f"user_{owner}")
    return context


def test_exact_source_identities_and_current_base_are_bound():
    import subprocess

    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip() == "8fdcc0414c72393c4f575f7597bd30850b707d35"
    expected = {
        "reserved/annual_position_projection_repository_adapter.py": (
            subject.SOURCE_S3C_SHA256
        ),
        "reserved/auth.py": subject.SOURCE_AUTH_SHA256,
        "reserved/billing/event_inbox_contract.py": (
            subject.SOURCE_OWNER_MAPPER_SHA256
        ),
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_authenticated_session_users_id_is_canonicalised_and_bound(app):
    _, _, projection = admitted()
    context = session(app)
    try:
        operation = adapt(projection)
    finally:
        context.pop()
    mapped = dict(s3c.validate_projection_repository_adapter_operation(operation))
    candidate = dict(extract_structural_candidate(operation))
    assert mapped["authenticated_user_id"] == "41"
    assert mapped["authenticated_business_id"] == "business-41"
    assert candidate["user_id"] == "41"
    assert candidate["business_id"] == "business-41"
    assert mapped["persistence_authority"] is False
    assert mapped["production_activation_authority"] is False


def test_no_request_context_and_no_authenticated_session_fail_closed(app):
    _, _, projection = admitted()
    with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="snapshot is unavailable"):
        adapt(projection)
    with app.test_request_context("/"):
        with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="exact positive"):
            adapt(projection)


@pytest.mark.parametrize("owner", [True, False, 0, -1, "41", 1.0])
def test_runtime_owner_must_be_exact_positive_users_id(app, owner):
    _, _, projection = admitted()
    context = session(app, owner)
    try:
        with pytest.raises(
            subject.AuthenticatedOwnerAdapterError, match="exact positive users.id"
        ):
            adapt(projection)
    finally:
        context.pop()


def test_cross_owner_and_noncanonical_owner_projection_fail_closed(app):
    context = session(app, 41)
    try:
        for projection in (admitted(user_id="42")[2], admitted(user_id="041")[2]):
            with pytest.raises(
                subject.AuthenticatedOwnerAdapterError, match="failed closed"
            ):
                adapt(projection)
    finally:
        context.pop()


class Text(str):
    pass


class Day(date):
    pass


def test_business_reference_and_evaluation_date_require_exact_types(app):
    _, _, projection = admitted()
    context = session(app)
    try:
        with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="exact string"):
            adapt(projection, business=Text("business-41"))
        with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="exact date"):
            adapt(projection, evaluated_on=Day(2026, 4, 5))
    finally:
        context.pop()


def test_missing_and_mismatched_business_references_fail(app):
    _, _, projection = admitted()
    context = session(app)
    try:
        for business in ("", "business-42", None, True, 41):
            with pytest.raises(subject.AuthenticatedOwnerAdapterError):
                adapt(projection, business=business)
    finally:
        context.pop()


@pytest.mark.parametrize("business", ["spending-ltd", "defaulting-ltd"])
def test_opaque_business_identifiers_receive_no_substring_policy(app, business):
    _, _, projection = admitted(business_id=business)
    context = session(app)
    try:
        mapped = dict(adapt(projection, business=business))
    finally:
        context.pop()
    assert mapped["authenticated_business_id"] == business


def test_upstream_contract_still_rejects_secret_shaped_business_identifier():
    with pytest.raises(ValueError):
        admitted(business_id="tokenworks")


def test_stale_future_and_reconstructed_projection_provenance_fail(app):
    _, _, projection = admitted()
    context = session(app)
    try:
        with pytest.raises(subject.AuthenticatedOwnerAdapterError):
            adapt(
                projection,
                evaluated_on=projection.as_of
                + timedelta(days=projection.stale_after_days + 1),
            )
        with pytest.raises(subject.AuthenticatedOwnerAdapterError):
            adapt(projection, evaluated_on=projection.as_of - timedelta(days=1))
        reconstructed = dataclasses.replace(projection)
        with pytest.raises(subject.AuthenticatedOwnerAdapterError):
            adapt(reconstructed)
    finally:
        context.pop()


def test_successor_path_preserves_s3a_and_s3b_predecessors(app):
    annual, result, previous = admitted()
    context = session(app)
    try:
        previous_operation = adapt(previous)
        previous_candidate = extract_structural_candidate(previous_operation)
        successor = supersede_annual_position_projection(previous, annual, result)
        operation = adapt(
            successor,
            previous_projection=previous,
            previous_candidate=previous_candidate,
        )
    finally:
        context.pop()
    mapped = dict(s3c.validate_projection_repository_adapter_operation(operation))
    assert mapped["source_predecessor_structural_candidate"] == previous_candidate
    assert dict(mapped["structural_candidate"])["record_version"] == 2


def test_missing_or_substituted_successor_inputs_fail_closed(app):
    annual, result, previous = admitted()
    successor = supersede_annual_position_projection(previous, annual, result)
    context = session(app)
    try:
        with pytest.raises(subject.AuthenticatedOwnerAdapterError):
            adapt(successor)
        previous_candidate = extract_structural_candidate(adapt(previous))
        other = admitted(business_id="business-42")[2]
        with pytest.raises(subject.AuthenticatedOwnerAdapterError):
            adapt(
                successor,
                previous_projection=other,
                previous_candidate=previous_candidate,
            )
    finally:
        context.pop()


def test_public_dependency_rebinding_cannot_change_captured_boundary(app, monkeypatch):
    _, _, projection = admitted()
    monkeypatch.setattr(owner_contract, "canonical_owner_id_from_users_id", lambda _: "999")
    monkeypatch.setattr(s3c, "adapt_admitted_projection_to_structural_candidate", lambda **_: ())
    context = session(app, 41)
    try:
        mapped = dict(adapt(projection))
    finally:
        context.pop()
    assert mapped["authenticated_user_id"] == "41"


def test_auth_session_proxy_and_key_rebinding_fail_closed(app, monkeypatch):
    _, _, projection = admitted()
    original_session_proxy = auth.session
    context = session(app)
    try:
        monkeypatch.setattr(auth, "session", object())
        with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="altered"):
            adapt(projection)
    finally:
        context.pop()
    monkeypatch.setattr(auth, "session", original_session_proxy)

    context = session(app)
    try:
        monkeypatch.setattr(auth, "_SK_USER_ID", "_redirected_user_id")
        with pytest.raises(subject.AuthenticatedOwnerAdapterError, match="altered"):
            adapt(projection)
    finally:
        context.pop()


def test_session_owner_is_read_once_and_cannot_redirect_between_reads(app):
    _, _, projection = admitted()

    class ChangingSession(dict):
        calls = 0

        def get(self, key, default=None):
            self.calls += 1
            return 41 if self.calls == 1 else 999

    context = app.test_request_context("/")
    context.push()
    backend = ChangingSession()
    flask_globals._cv_request.get().session = backend
    try:
        mapped = dict(adapt(projection))
    finally:
        context.pop()
    assert backend.calls == 1
    assert mapped["authenticated_user_id"] == "41"


@pytest.mark.parametrize("raised", [LookupError("private-backend-detail"), OSError("private-path")])
def test_ordinary_session_access_errors_are_normalised_without_leakage(
    app, monkeypatch, raised
):
    _, _, projection = admitted()

    class FailingSession(dict):
        def get(self, key, default=None):
            raise raised

    context = app.test_request_context("/")
    context.push()
    flask_globals._cv_request.get().session = FailingSession()
    try:
        with pytest.raises(subject.AuthenticatedOwnerAdapterError) as caught:
            adapt(projection)
    finally:
        context.pop()
    assert str(caught.value) == "current signed-session owner snapshot is unavailable"
    assert caught.value.__cause__ is None


def test_session_base_exceptions_are_not_swallowed(app):
    _, _, projection = admitted()

    class InterruptedSession(dict):
        def get(self, key, default=None):
            raise KeyboardInterrupt("stop-now")

    context = app.test_request_context("/")
    context.push()
    flask_globals._cv_request.get().session = InterruptedSession()
    try:
        with pytest.raises(KeyboardInterrupt, match="stop-now"):
            adapt(projection)
    finally:
        context.pop()


def test_exact_named_call_shape_rejects_missing_extra_and_positional(app):
    _, _, projection = admitted()
    context = session(app)
    try:
        with pytest.raises(TypeError, match="exact named"):
            subject.adapt_authenticated_owner_projection(projection)
        with pytest.raises(TypeError, match="exact named"):
            subject.adapt_authenticated_owner_projection(
                projection=projection,
                authenticated_business_reference="business-41",
                evaluated_on=projection.as_of,
                previous_projection=None,
            )
        with pytest.raises(TypeError, match="exact named"):
            subject.adapt_authenticated_owner_projection(
                projection=projection,
                authenticated_business_reference="business-41",
                evaluated_on=projection.as_of,
                previous_projection=None,
                previous_structural_candidate=None,
                unexpected=True,
            )
    finally:
        context.pop()


def test_module_is_non_durable_and_has_no_database_network_or_filesystem_io():
    source = MODULE.read_text(encoding="utf-8")
    for token in (
        "import os", "import socket", "import subprocess", "import requests",
        "import sqlite3", "import pathlib", "import tempfile", "import urllib",
        "open(", "os.environ", "getenv(", ".execute(", ".commit(",
    ):
        assert token not in source, token


def test_candidate_changes_only_the_three_authorised_paths():
    import subprocess

    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True
    ).splitlines()
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert set(changed + untracked) <= OWNED_PATHS


def test_evidence_preserves_non_authority_and_business_mapping_gap():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    for phrase in (
        "signed-session `users.id`",
        "does not authenticate a token",
        "does not establish business ownership",
        "no datastore",
        "no persistence authority",
        "no access authority",
        "no retention, deletion, encryption or key-custody authority",
        "not W9-S3 completion",
        "not security, privacy or launch assurance",
    ):
        assert phrase in text


def test_public_api_exports_no_authentication_or_authority_minter():
    assert subject.__all__ == [
        "ADAPTER_VERSION", "AUTHORITY_STATUS", "SOURCE_S3C_COMMIT",
        "SOURCE_S3C_INTEGRATION_COMMIT", "SOURCE_S3C_SHA256",
        "SOURCE_AUTH_COMMIT", "SOURCE_AUTH_SHA256",
        "SOURCE_OWNER_MAPPER_COMMIT", "SOURCE_OWNER_MAPPER_SHA256",
        "AuthenticatedOwnerAdapterError", "adapt_authenticated_owner_projection",
    ]
    assert not hasattr(subject, "authenticate")
    assert not hasattr(subject, "persist")
    assert not hasattr(subject, "write")
    assert not hasattr(subject, "activate")
