"""Provider-neutral, payload-free schema-drift evidence.

Adapters declare the source fields their reviewed mapping requires and the
fields it knows. This contract checks only field names and coarse value kinds;
it stores no source values. Missing required fields or changed required kinds
quarantine the record. Unknown fields are retained as review evidence without
automatically blocking a purpose that does not depend on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class SchemaContractError(ValueError):
    pass


class SchemaFitness(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_UNKNOWN_FIELDS = "accepted_with_unknown_fields"
    QUARANTINED = "quarantined"


_ALLOWED_KINDS = frozenset({"null", "boolean", "integer", "number", "string", "array", "object"})


def _kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return type(value).__name__


@dataclass(frozen=True)
class SourceSchema:
    mapping_version: str
    required_fields: frozenset[str]
    known_fields: frozenset[str]
    expected_kinds: Mapping[str, frozenset[str]]
    request_prerequisites: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.mapping_version.strip():
            raise SchemaContractError("mapping_version is required")
        if not self.required_fields <= self.known_fields:
            raise SchemaContractError("Required fields must be included in known fields")
        if not set(self.expected_kinds) <= self.known_fields:
            raise SchemaContractError("Kinds may be declared only for known fields")
        for field, kinds in self.expected_kinds.items():
            if not kinds or not kinds <= _ALLOWED_KINDS:
                raise SchemaContractError(f"Invalid expected kinds for {field}")
        for prerequisite in self.request_prerequisites:
            if not isinstance(prerequisite, str) or not prerequisite.strip():
                raise SchemaContractError("Request prerequisites must be non-empty strings")

    @property
    def response_required_fields(self) -> frozenset[str]:
        """Fields the official selected response schema itself requires.

        Distinct from ``request_prerequisites``, which are what the adapter must
        request/enrich (for example nested-item expansion) and must not be
        encoded as unconditional response requiredness.
        """
        return self.required_fields


@dataclass(frozen=True)
class SchemaObservation:
    mapping_version: str
    fitness: SchemaFitness
    observed_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    missing_required_fields: tuple[str, ...]
    incompatible_required_fields: tuple[str, ...]

    @property
    def may_normalise(self) -> bool:
        return self.fitness is not SchemaFitness.QUARANTINED


def observe_schema(record: Mapping[str, object], schema: SourceSchema) -> SchemaObservation:
    if not isinstance(record, Mapping):
        raise SchemaContractError("Provider record must be an object")
    if any(not isinstance(name, str) or not name for name in record):
        raise SchemaContractError("Provider field names must be non-empty strings")

    observed = frozenset(record)
    missing = schema.required_fields - observed
    incompatible = {
        field
        for field in schema.required_fields & observed
        if field in schema.expected_kinds and _kind(record[field]) not in schema.expected_kinds[field]
    }
    unknown = observed - schema.known_fields
    if missing or incompatible:
        fitness = SchemaFitness.QUARANTINED
    elif unknown:
        fitness = SchemaFitness.ACCEPTED_WITH_UNKNOWN_FIELDS
    else:
        fitness = SchemaFitness.ACCEPTED
    return SchemaObservation(
        mapping_version=schema.mapping_version,
        fitness=fitness,
        observed_fields=tuple(sorted(observed)),
        unknown_fields=tuple(sorted(unknown)),
        missing_required_fields=tuple(sorted(missing)),
        incompatible_required_fields=tuple(sorted(incompatible)),
    )

