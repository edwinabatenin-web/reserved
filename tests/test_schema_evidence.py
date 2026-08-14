from reserved.providers.schema_evidence import (
    SchemaContractError,
    SchemaFitness,
    SourceSchema,
    observe_schema,
)


def schema():
    return SourceSchema(
        mapping_version="synthetic-invoice-v1",
        required_fields=frozenset({"id", "amount", "currency"}),
        known_fields=frozenset({"id", "amount", "currency", "status"}),
        expected_kinds={
            "id": frozenset({"string"}),
            "amount": frozenset({"string", "number", "integer"}),
            "currency": frozenset({"string"}),
        },
    )


def test_reviewed_shape_is_accepted_and_may_normalise():
    result = observe_schema({"id": "1", "amount": "12.00", "currency": "GBP"}, schema())
    assert result.fitness is SchemaFitness.ACCEPTED
    assert result.may_normalise


def test_unknown_additive_field_is_recorded_without_storing_value():
    secret_value = "source-value-must-not-appear"
    result = observe_schema(
        {"id": "1", "amount": 12.0, "currency": "GBP", "new_field": secret_value},
        schema(),
    )
    assert result.fitness is SchemaFitness.ACCEPTED_WITH_UNKNOWN_FIELDS
    assert result.unknown_fields == ("new_field",)
    assert secret_value not in repr(result)
    assert result.may_normalise


def test_missing_required_field_quarantines_record():
    result = observe_schema({"id": "1", "currency": "GBP"}, schema())
    assert result.fitness is SchemaFitness.QUARANTINED
    assert result.missing_required_fields == ("amount",)
    assert not result.may_normalise


def test_required_field_kind_change_quarantines_record():
    result = observe_schema({"id": "1", "amount": {"value": 12}, "currency": "GBP"}, schema())
    assert result.fitness is SchemaFitness.QUARANTINED
    assert result.incompatible_required_fields == ("amount",)


def test_boolean_is_not_silently_accepted_as_integer_amount():
    result = observe_schema({"id": "1", "amount": True, "currency": "GBP"}, schema())
    assert result.fitness is SchemaFitness.QUARANTINED


def test_invalid_schema_declarations_fail_closed():
    invalid = (
        dict(mapping_version="v1", required_fields=frozenset({"id"}), known_fields=frozenset(), expected_kinds={}),
        dict(mapping_version="v1", required_fields=frozenset(), known_fields=frozenset({"id"}), expected_kinds={"other": frozenset({"string"})}),
        dict(mapping_version="v1", required_fields=frozenset(), known_fields=frozenset({"id"}), expected_kinds={"id": frozenset({"decimal"})}),
    )
    for values in invalid:
        try:
            SourceSchema(**values)
        except SchemaContractError:
            pass
        else:
            raise AssertionError("Invalid source schema accepted")


def test_non_object_and_invalid_field_names_are_rejected():
    for record in (["not", "object"], {"": "empty-name"}, {1: "numeric-name"}):
        try:
            observe_schema(record, schema())
        except SchemaContractError:
            pass
        else:
            raise AssertionError("Invalid provider record accepted")

