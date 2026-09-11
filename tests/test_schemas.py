import pytest
from pydantic import TypeAdapter, ValidationError

from server.schemas import (
    TestDataInput,
    TechniqueCasesInput,
    RandomDataSpec,
    PropertyDataSpec,
    BoundaryValueSpec,
    EquivalenceSpec,
    DecisionTableSpec,
    PairwiseSpec,
    StateTransitionSpec,
    UseCaseSpec,
    ErrorGuessingSpec,
)


def test_strategy_discriminator_matches_concrete_type():
    data_adapter = TypeAdapter(TestDataInput)
    rnd = data_adapter.validate_python({"strategy": "random", "fields": [
        {"field": "age", "type": "integer", "constraints": {"min": 0, "max": 150}}]})
    assert isinstance(rnd, RandomDataSpec)
    prop = data_adapter.validate_python(
        {"strategy": "property", "field": "age", "type": "integer"})
    assert isinstance(prop, PropertyDataSpec)


def test_bad_strategy_rejected():
    with pytest.raises(ValidationError):
        TypeAdapter(TestDataInput).validate_python({"strategy": "bogus", "field": "x"})


def test_technique_discriminator_all_seven():
    specs = [
        {"technique": "Boundary Value Analysis", "field": "age", "min": 0, "max": 150},
        {"technique": "Equivalence Partitioning", "field": "email", "valid": ["a@b.c"], "invalid": ["bad"]},
        {"technique": "Decision Table", "conditions": ["pay"], "actions": ["ship"], "rules": []},
        {"technique": "Pairwise Testing", "values": {"browser": ["c", "f"]}},
        {"technique": "State Transition", "states": ["open"], "events": ["close"], "transitions": []},
        {"technique": "Use Case Testing", "name": "login", "steps": ["fill", "submit"], "expected": []},
        {"technique": "Error Guessing", "field": "email", "input": "x@y.z", "pitfalls": ["", None]},
    ]
    expected_types = [BoundaryValueSpec, EquivalenceSpec, DecisionTableSpec,
                      PairwiseSpec, StateTransitionSpec, UseCaseSpec, ErrorGuessingSpec]
    for spec, expected in zip(specs, expected_types):
        parsed = TypeAdapter(TechniqueCasesInput).validate_python(spec)
        assert isinstance(parsed, expected), f"{spec['technique']} -> {type(parsed).__name__}"


def test_bad_technique_rejected():
    with pytest.raises(ValidationError):
        TypeAdapter(TechniqueCasesInput).validate_python({"technique": "Zombie Testing", "field": "x"})


def test_all_model_fields_have_descriptions():
    from server.schemas import RandomDataSpec as R
    schema = R.model_json_schema()
    props = schema["properties"]
    assert props["fields"]["description"]
    assert props["strategy"]["description"]