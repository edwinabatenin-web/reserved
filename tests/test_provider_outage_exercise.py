from __future__ import annotations

import ast
import copy
import pickle
from pathlib import Path
from types import MappingProxyType

import pytest

import reserved.assurance.provider_outage_exercise as exercise
import reserved.providers.operational_resilience as resilience


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved/assurance/provider_outage_exercise.py"
EXPECTED_CASES = (
    ("timeout", "temporarily_unavailable", "retry_later", "temporarily_unavailable", "recovery_pending", "available"),
    ("temporarily_unavailable", "temporarily_unavailable", "retry_later", "temporarily_unavailable", "recovery_pending", "available"),
    ("authorisation_expired", "authorisation_required", "reconnect", "reconnect_required", "recovery_pending", "available"),
    ("authorisation_revoked", "authorisation_required", "reconnect", "reconnect_required", "recovery_pending", "available"),
    ("schema_incompatible", "schema_incompatible", "none", "data_format_changed", "recovery_pending", "available"),
    ("required_fields_missing", "evidence_inadequate", "provide_evidence", "information_incomplete", "recovery_pending", "available"),
    ("required_fields_invalid", "evidence_inadequate", "provide_evidence", "information_incomplete", "recovery_pending", "available"),
    ("evidence_stale", "stale", "refresh", "information_out_of_date", "recovery_pending", "available"),
)


def summary():
    result = exercise.run_provider_outage_exercise()
    return result, exercise.as_provider_outage_exercise_summary(result)


def test_exact_complete_canonical_matrix_recovery_aggregate_and_controls():
    _result, evidence = summary()
    assert type(evidence) is MappingProxyType
    assert evidence == {
        "schema_version": "w9-s4e-provider-outage-exercise-v1",
        "event_results": EXPECTED_CASES,
        "recovery_states": ("recovery_pending", "available"),
        "aggregate_projection": (
            "temporarily_unavailable", "temporarily_unavailable",
            "retry_later,reconnect",
        ),
        "negative_controls": (
            "stale_observation", "future_observation", "cross_owner",
            "subtyped_status", "mutated_status", "replayed_event",
            "duplicate_route",
        ),
        "safe_presentation_verified": True,
        "all_invariants_verified": True,
    }


def test_result_is_opaque_immutable_nonserialisable_and_token_not_stored():
    result, evidence = summary()
    assert not hasattr(result, "__dict__")
    assert result.__slots__ == ("__weakref__",)
    assert repr(result) == "ProviderOutageExerciseResult([ISSUED])"
    assert copy.copy(result) is result
    assert copy.deepcopy(result) is result
    assert not any("authority" in name or "binding" in name for name in dir(result))
    with pytest.raises(exercise.ProviderOutageExerciseError):
        exercise.ProviderOutageExerciseResult()
    with pytest.raises(exercise.ProviderOutageExerciseError):
        exercise.ProviderOutageExerciseResult(_authority=object())
    forged = object.__new__(exercise.ProviderOutageExerciseResult)
    with pytest.raises(exercise.ProviderOutageExerciseError):
        exercise.as_provider_outage_exercise_summary(forged)
    with pytest.raises(exercise.ProviderOutageExerciseError):
        pickle.dumps(result)
    assert exercise.as_provider_outage_exercise_summary(result) == evidence
    with pytest.raises(TypeError):
        evidence["all_invariants_verified"] = False


def test_projector_rejects_canonical_content_lookalikes_and_subtypes():
    class Lookalike:
        def public_summary(self):
            return {"all_invariants_verified": True, "production_enabled": True}
    class ResultSubtype(exercise.ProviderOutageExerciseResult):
        pass
    for candidate in (Lookalike(), object.__new__(ResultSubtype)):
        with pytest.raises(exercise.ProviderOutageExerciseError, match="^provider outage exercise failed closed$"):
            exercise.as_provider_outage_exercise_summary(candidate)


def test_class_method_and_module_projector_rebinding_cannot_change_genuine_projector(monkeypatch):
    result = exercise.run_provider_outage_exercise()
    genuine_projector = exercise.as_provider_outage_exercise_summary
    monkeypatch.setattr(
        exercise.ProviderOutageExerciseResult, "public_summary",
        lambda self: {"production_enabled": True}, raising=False,
    )
    monkeypatch.setattr(
        exercise, "as_provider_outage_exercise_summary",
        lambda result: {"target_runtime_verified": True},
    )
    evidence = genuine_projector(result)
    assert evidence["all_invariants_verified"] is True
    assert "production_enabled" not in evidence
    assert "target_runtime_verified" not in evidence


@pytest.mark.parametrize("mapping_name", ["_ACTION_BY_STATE", "_MESSAGE_BY_STATE"])
def test_in_place_upstream_semantic_mutation_fails_closed(mapping_name):
    mapping = getattr(resilience, mapping_name)
    original = dict(mapping)
    try:
        if mapping_name == "_ACTION_BY_STATE":
            mapping[resilience.OperationalState.TEMPORARILY_UNAVAILABLE] = resilience.CustomerAction.NONE
        else:
            mapping[resilience.OperationalState.TEMPORARILY_UNAVAILABLE] = resilience.CustomerMessage.AVAILABLE
        with pytest.raises(exercise.ProviderOutageExerciseError, match="^provider outage exercise failed closed$"):
            exercise.run_provider_outage_exercise()
    finally:
        mapping.clear()
        mapping.update(original)


def test_exact_presentation_is_part_of_the_exercise_contract(monkeypatch):
    genuine = exercise.run_provider_outage_exercise
    assert exercise.as_provider_outage_exercise_summary(genuine())["safe_presentation_verified"] is True
    # The bound renderer is not affected by ordinary module collaborator rebinding.
    monkeypatch.setattr(exercise, "render_coordinated_provider_outage_status", lambda **kwargs: "wrong")
    assert exercise.as_provider_outage_exercise_summary(genuine())["safe_presentation_verified"] is True


def test_security_collaborators_and_builtins_are_closure_bound(monkeypatch):
    genuine_run = exercise.run_provider_outage_exercise
    genuine_project = exercise.as_provider_outage_exercise_summary
    expected = genuine_project(genuine_run())
    for name in (
        "EvidenceRouteIdentity", "EvidenceRouteStatus", "OperationalState",
        "OutageEvent", "RecoveryObservation", "classify_outage",
        "begin_recovery", "complete_recovery", "coordinate_provider_outage",
        "render_coordinated_provider_outage_status", "ProviderOutageExerciseError",
    ):
        monkeypatch.setattr(exercise, name, object())
    monkeypatch.setattr(exercise, "enumerate", lambda value: (), raising=False)
    monkeypatch.setattr(exercise, "range", lambda value: (), raising=False)
    assert genuine_project(genuine_run()) == expected


def test_no_sensitive_synthetic_values_are_projected_or_echoed():
    result, evidence = summary()
    rendered = repr(evidence)
    for forbidden in (
        "synthetic-owner", "other-owner", "synthetic-a", "synthetic-b",
        "annual-evidence", "business-evidence", "2026-01-01",
    ):
        assert forbidden not in rendered
    forged = object.__new__(exercise.ProviderOutageExerciseResult)
    with pytest.raises(exercise.ProviderOutageExerciseError) as caught:
        exercise.as_provider_outage_exercise_summary(forged)
    assert str(caught.value) == "provider outage exercise failed closed"
    assert "synthetic" not in str(caught.value)


def test_source_introduces_no_io_or_prohibited_runtime_surfaces():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    prohibited_imports = {
        "requests", "httpx", "urllib", "socket", "subprocess", "os", "flask",
        "sqlalchemy", "logging", "pathlib", "sqlite3", "redis", "boto3",
    }
    imports, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    assert not imports.intersection(prohibited_imports)
    assert not calls.intersection({
        "open", "connect", "request", "post", "put", "delete", "commit",
        "save", "write_text", "write_bytes",
    })


def test_public_surface_is_minimal_and_projector_has_no_token_defaults():
    assert exercise.__all__ == (
        "ProviderOutageExerciseError", "ProviderOutageExerciseResult",
        "run_provider_outage_exercise", "as_provider_outage_exercise_summary",
    )
    assert exercise.run_provider_outage_exercise.__defaults__ is None
    assert exercise.run_provider_outage_exercise.__kwdefaults__ is None
    assert exercise.as_provider_outage_exercise_summary.__defaults__ is None
    assert exercise.as_provider_outage_exercise_summary.__kwdefaults__ is None
