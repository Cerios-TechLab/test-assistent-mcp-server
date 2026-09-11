"""Pydantic v2 input schemas for the testassist tools.

Discriminated unions give FastMCP rich oneOf/discriminator JSON-schemas in
tools/list, which Glama's TDQSB scores on.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator


class FieldSpec(BaseModel):
    field: str = Field(description="Field name")
    type: Literal["integer", "float", "string", "boolean", "date"] = Field(
        default="string", description="Field data type"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific constraints: min, max, min_length, max_length, pattern",
    )


class RandomDataSpec(BaseModel):
    strategy: Literal["random"] = Field(
        description="Generate N random rows for multiple fields, optionally seeded"
    )
    fields: list[FieldSpec] = Field(description="Fields to generate values for")
    count: int = Field(default=10, ge=1, le=500, description="Number of rows to generate")
    seed: str | int | None = Field(default=None, description="Seed for reproducible output")


class PropertyDataSpec(BaseModel):
    strategy: Literal["property"] = Field(
        description="Generate property-based values for a single field: boundary + random + invalid"
    )
    field: str = Field(description="Field name")
    type: Literal["integer", "float", "string", "boolean", "date"] = Field(
        default="integer", description="Field data type"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific constraints: min, max, min_length, max_length, pattern",
    )
    count: int = Field(default=10, ge=1, le=500, description="Target number of cases")
    seed: str | int | None = Field(default=None, description="Seed for reproducible output")
    include_invalid: bool = Field(
        default=True, description="Also generate constraint-violating values"
    )


TestDataInput = Annotated[Union[RandomDataSpec, PropertyDataSpec], Field(discriminator="strategy")]


class BoundaryValueSpec(BaseModel):
    technique: Literal["Boundary Value Analysis"] = Field(
        description="Generate test cases around and beyond the min/max range edges"
    )
    field: str = Field(description="Field name")
    min: int = Field(description="Inclusive lower boundary")
    max: int = Field(description="Inclusive upper boundary")


class EquivalenceSpec(BaseModel):
    technique: Literal["Equivalence Partitioning"] = Field(
        description="One test case per explicit valid and invalid value"
    )
    field: str = Field(description="Field name")
    valid: list[Any] = Field(description="Values expected to be accepted")
    invalid: list[Any] = Field(description="Values expected to be rejected")


class DecisionTableSpec(BaseModel):
    technique: Literal["Decision Table"] = Field(
        description="Decision table with condition-action rules; one test case per rule"
    )
    conditions: list[str] = Field(description="Condition names")
    actions: list[str] = Field(description="Action names")
    rules: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Rules, each {'when': {cond: value}, 'then': [action, ...]}",
    )


class PairwiseSpec(BaseModel):
    technique: Literal["Pairwise Testing"] = Field(
        description="All-pairs covering set of parameter combinations"
    )
    values: dict[str, list[Any]] = Field(
        description="Map of parameter name to list of values to combine"
    )


class StateTransitionSpec(BaseModel):
    technique: Literal["State Transition"] = Field(
        description="State-event transitions; one test case per transition"
    )
    states: list[str] = Field(description="Possible states")
    events: list[str] = Field(description="Possible events")
    transitions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Transitions, each {'state': s, 'event': e, 'next': n}",
    )


class UseCaseSpec(BaseModel):
    technique: Literal["Use Case Testing"] = Field(
        description="End-to-end use case steps; one test case per step"
    )
    name: str = Field(description="Use case name")
    steps: list[str] = Field(description="Ordered steps of the use case")
    expected: list[str] = Field(
        default_factory=list,
        description="Expected outcomes per step (parallel to steps)",
    )


class ErrorGuessingSpec(BaseModel):
    technique: Literal["Error Guessing"] = Field(
        description="Negative test cases from known error-prone pitfalls"
    )
    field: str = Field(description="Field name")
    input: Any = Field(description="A representative valid value")
    pitfalls: list[Any] = Field(description="Known error-prone values to try")


TechniqueCasesInput = Annotated[
    Union[
        BoundaryValueSpec,
        EquivalenceSpec,
        DecisionTableSpec,
        PairwiseSpec,
        StateTransitionSpec,
        UseCaseSpec,
        ErrorGuessingSpec,
    ],
    Field(discriminator="technique"),
]