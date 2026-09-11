# Tool-redesign testassist (TDQSB-fix) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hermodel de 8 overlapping testassist-tools naar 6 scherpe tools met Pydantic discriminated-union schemas (TDQSB 3.2→hoger) en maak alle 7 technieken genereerbaar.

**Architecture:** `server/schemas.py` (nieuw) definieert Pydantic-v2 modellen met `Field(discriminator=...)`-unions. `generators.py` krijgt 4 nieuwe pure generators. `testassist_mcp_server.py` (tool-laag) draait om van kale `dict`-params naar getypeerde union-params; interne helpers in `generate.py` blijven onveranderd.

**Tech Stack:** Python 3.11, FastMCP (`mcp==1.29.0`), Pydantic 2.13.5, pytest. Workflow `.github/workflows/glama-build-and-release-gate.yml` (tag-driven).

## Global Constraints

- Package naam `testassist-mcp`; Python-requirement `>=3.11`; enige runtime-dep `mcp==1.29.0`, dev-dep `pytest`.
- Technieknamen (Literal-waarden) moeten exact matchen met de knowledgebase-namen: `Boundary Value Analysis`, `Decision Table`, `Equivalence Partitioning`, `Error Guessing`, `Pairwise Testing`, `State Transition`, `Use Case Testing`.
- Nieuwe toolset (6 tools): `catalog_techniques`, `catalog_heuristics`, `generate_test_cases`, `generate_test_data`, `advise_technique`, `checklist_for`. Verwijderd als publiek: `generate_with_property`, `generate_boundary_cases`, `generate_random` (blijven interne helpers in `generate.py`).
- Aanroepvorm wordt `{"input": {...}}` (één param `input` van het union-type) voor `generate_test_cases` en `generate_test_data`.
- Smoke-test verwacht **6** tools (was 8).
- Alle velden in de Pydantic-modellen krijgen `Field(description=...)` — dit is de TDQSB-winst (schemas).
- Geen comments in code tenzij gevraagd.
- Run de suite altijd met `.venv/bin/python -m pytest`.

---

### Task 1: `server/schemas.py` — Pydantic modellen met discriminated unions

**Files:**
- Create: `server/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces: `TestDataInput = Annotated[Union[RandomDataSpec, PropertyDataSpec], Field(discriminator="strategy")]`; `TechniqueCasesInput = Annotated[Union[BoundaryValueSpec, EquivalenceSpec, DecisionTableSpec, PairwiseSpec, StateTransitionSpec, UseCaseSpec, ErrorGuessingSpec], Field(discriminator="technique")]`. Alle sub-modellen erfden van `BaseModel` en hebben de discriminator als required `Literal`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError

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
    rnd = TestDataInput.model_validate({"strategy": "random", "fields": [
        {"field": "age", "type": "integer", "constraints": {"min": 0, "max": 150}}]})
    assert isinstance(rnd, RandomDataSpec)
    prop = TestDataInput.model_validate(
        {"strategy": "property", "field": "age", "type": "integer"})
    assert isinstance(prop, PropertyDataSpec)


def test_bad_strategy_rejected():
    with pytest.raises(ValidationError):
        TestDataInput.model_validate({"strategy": "bogus", "field": "x"})


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
        parsed = TechniqueCasesInput.model_validate(spec)
        assert isinstance(parsed, expected), f"{spec['technique']} -> {type(parsed).__name__}"


def test_bad_technique_rejected():
    with pytest.raises(ValidationError):
        TechniqueCasesInput.model_validate({"technique": "Zombie Testing", "field": "x"})


def test_all_model_fields_have_descriptions():
    from server.schemas import RandomDataSpec as R
    schema = R.model_json_schema()
    props = schema["properties"]
    assert props["fields"]["description"]
    assert props["strategy"]["description"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest tests/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.schemas'`

- [ ] **Step 3: Write minimal implementation — `server/schemas.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest tests/test_schemas.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd /root/testassist-mcp
git add server/schemas.py tests/test_schemas.py
git commit -m "feat: add pydantic discriminated-union tool schemas"
```

---

### Task 2: 4 nieuwe technique-generators in `server/generators.py`

**Files:**
- Modify: `server/generators.py` (append 4 functies)
- Test: `tests/test_generators.py`

**Interfaces:**
- Consumes: `server/schemas.py` (niets — deze functies nemen plain dicts, Model-instances worden in de tool-laag omgezet).
- Produces: `generate_decision_table(spec) -> list[dict]`, `generate_state_transition(spec) -> list[dict]`, `generate_use_case(spec) -> list[dict]`, `generate_error_guessing(spec) -> list[dict]`. Id-reeksen: `DT-`/`ER-`/`UC-`/`EG-` prefixen.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generators.py — append:
def test_decision_table_one_case_per_rule():
    spec = {
        "conditions": ["pays", "member"],
        "actions": ["ship", "charge", "waive"],
        "rules": [
            {"when": {"pays": "yes", "member": "no"}, "then": ["ship", "charge"]},
            {"when": {"pays": "yes", "member": "yes"}, "then": ["ship"]},
        ],
    }
    cases = generate_decision_table(spec)
    assert len(cases) == 2
    assert all(c["id"].startswith("DT-") for c in cases)
    assert cases[0]["input"] == {"pays": "yes", "member": "no"}
    assert cases[0]["expected"] == "ship, charge"


def test_state_transition_one_case_per_transition():
    spec = {
        "states": ["idle", "active"],
        "events": ["start", "stop"],
        "transitions": [
            {"state": "idle", "event": "start", "next": "active"},
            {"state": "active", "event": "stop", "next": "idle"},
        ],
    }
    cases = generate_state_transition(spec)
    assert len(cases) == 2
    assert all(c["id"].startswith("ST-") for c in cases)
    assert cases[0]["input"] == {"state": "idle", "event": "start"}
    assert cases[0]["expected"] == "active"


def test_use_case_one_case_per_step_and_fallback_expected():
    cases = generate_use_case({
        "name": "login",
        "steps": ["open page", "submit credentials"],
        "expected": ["page opens"],
    })
    assert len(cases) == 2
    assert all(c["id"].startswith("UC-") for c in cases)
    assert cases[0]["expected"] == "page opens"
    assert cases[1]["expected"]  # fallback not empty


def test_error_guessing_one_negative_case_per_pitfall():
    cases = generate_error_guessing({
        "field": "email",
        "input": "a@b.c",
        "pitfalls": ["", "x", "<script>"],
    })
    assert len(cases) == 3
    assert all(c["id"].startswith("EG-") for c in cases)
    for c in cases:
        assert "email" in c["input"]
    assert cases[0]["expected"] != cases[1]["expected"]  # elke valkuil heeft eigen expected (payload = pitfall)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest tests/test_generators.py -v`
Expected: FAIL with `ImportError: cannot import name 'generate_decision_table'`

- [ ] **Step 3: Append the generators to `server/generators.py`**

```python
def generate_decision_table(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Decision Table. spec: {conditions, actions, rules: [{when, then}]}."""
    cases = []
    for i, rule in enumerate(spec.get("rules", [])):
        cases.append({
            "id": f"DT-{i + 1}",
            "input": rule.get("when", {}),
            "expected": ", ".join(rule.get("then", [])),
        })
    return cases


def generate_state_transition(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """State Transition. spec: {states, events, transitions: [{state, event, next}]}."""
    cases = []
    for i, t in enumerate(spec.get("transitions", [])):
        cases.append({
            "id": f"ST-{i + 1}",
            "input": {"state": t.get("state"), "event": t.get("event")},
            "expected": t.get("next"),
        })
    return cases


def generate_use_case(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Use Case Testing. spec: {name, steps, expected (parallel)}."""
    steps = spec.get("steps", [])
    expected = spec.get("expected", [])
    cases = []
    for i, step in enumerate(steps):
        exp = expected[i] if i < len(expected) else "step completes successfully"
        cases.append({"id": f"UC-{i + 1}", "input": {"step": step}, "expected": exp})
    return cases


def generate_error_guessing(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Error Guessing. spec: {field, input, pitfalls}. One negative case per pitfall."""
    field = spec.get("field", "input")
    cases = []
    for i, pitfall in enumerate(spec.get("pitfalls", [])):
        cases.append({
            "id": f"EG-{i + 1}",
            "input": {field: pitfall},
            "expected": f"invalid (rejected) -- guessed: {pitfall}",
        })
    return cases
```

- [ ] **Step 4: Update the import in the test file**

Top of `tests/test_generators.py`, change the import line to:

```python
from server.generators import (
    generate_boundary_value_analysis,
    generate_decision_table,
    generate_equivalence_partitioning,
    generate_error_guessing,
    generate_pairwise,
    generate_state_transition,
    generate_use_case,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest tests/test_generators.py -v`
Expected: PASS (8 tests: 4 bestaand + 4 nieuw)

- [ ] **Step 6: Commit**

```bash
cd /root/testassist-mcp
git add server/generators.py tests/test_generators.py
git commit -m "feat: add decision table, state transition, use case, error guessing generators"
```

---

### Task 3: Tool-laag naar 6 tools met union-params

**Files:**
- Modify: `server/testassist_mcp_server.py`
- Test: `tests/test_mcp_tools.py` (herschrijven)

**Interfaces:**
- Consumes: `TestDataInput`, `TechniqueCasesInput` (Task 1), 7 generators uit `generators.py` (bestaand register + 4 nieuw), interne helpers `generate_random_fn`, `generate_with_property_fn` uit `server.generate`.
- Produces: `_build_tools(kb)` geeft dict met exact de 6 tools; `generate_test_cases(input: TechniqueCasesInput)`, `generate_test_data(input: TestDataInput)`.

- [ ] **Step 1: Write the failing tests (herschrijf `tests/test_mcp_tools.py`)**

```python
"""Tool-registry and schema-shape tests for the 6-tool testassist server."""
import asyncio
from pathlib import Path

import pytest

from server.knowledge_base import KnowledgeBase
from server.schemas import TechniqueCasesInput, TestDataInput
from server.testassist_mcp_server import _build_tools, mcp

KB = KnowledgeBase(Path(__file__).resolve().parents[1] / "server" / "knowledge")

EXPECTED_TOOLS = {
    "catalog_techniques",
    "catalog_heuristics",
    "generate_test_cases",
    "generate_test_data",
    "advise_technique",
    "checklist_for",
}


def test_build_tools_exposes_six():
    tools = _build_tools(KB)
    assert set(tools) == EXPECTED_TOOLS


def test_generate_test_cases_all_techniques():
    tools = _build_tools(KB)
    for spec in [
        {"technique": "Boundary Value Analysis", "field": "age", "min": 0, "max": 150},
        {"technique": "Equivalence Partitioning", "field": "email", "valid": ["a@b.c"], "invalid": [""]},
        {"technique": "Decision Table", "conditions": ["pay"], "actions": ["ship"], "rules": [{"when": {"pay": "yes"}, "then": ["ship"]}]},
        {"technique": "Pairwise Testing", "values": {"browser": ["c", "f"], "os": ["linux", "win"]}},
        {"technique": "State Transition", "states": ["open"], "events": ["close"], "transitions": [{"state": "open", "event": "close", "next": "closed"}]},
        {"technique": "Use Case Testing", "name": "login", "steps": ["fill", "submit"], "expected": ["ok"]},
        {"technique": "Error Guessing", "field": "email", "input": "a@b.c", "pitfalls": ["", None]},
    ]:
        out = tools["generate_test_cases"](TechniqueCasesInput.model_validate(spec))
        assert out["technique"] == spec["technique"]
        assert out["testcases"], f"no cases for {spec['technique']}"


def test_generate_test_data_random_and_property():
    tools = _build_tools(KB)
    rnd = tools["generate_test_data"](TestDataInput.model_validate(
        {"strategy": "random",
         "fields": [{"field": "age", "type": "integer", "constraints": {"min": 0, "max": 10}}],
         "count": 3, "seed": "s"}))
    assert rnd["strategy"] == "random"
    assert len(rnd["cases"]) == 3
    prop = tools["generate_test_data"](TestDataInput.model_validate(
        {"strategy": "property", "field": "age", "type": "integer",
         "constraints": {"min": 0, "max": 10}, "count": 3}))
    assert prop["strategy"] == "property"
    assert prop["cases"]


def test_advise_technique_smoke():
    tools = _build_tools(KB)
    out = tools["advise_technique"]("regression after a bug fix")
    assert "RCRCRC" in out["heuristics"]


def test_checklist_for_regression():
    tools = _build_tools(KB)
    out = tools["checklist_for"]("regression")
    assert out["heuristic"] == "RCRCRC"
    assert out["items"]


def test_tool_schemas_use_discriminators():
    tool_by_name = {t.name: t for t in asyncio.run(mcp.list_tools())}
    gtc = tool_by_name["generate_test_cases"].inputSchema
    disc = gtc["properties"]["input"]["discriminator"]
    assert disc["propertyName"] == "technique"
    assert len(disc["mapping"]) == 7
    gtd = tool_by_name["generate_test_data"].inputSchema
    disc2 = gtd["properties"]["input"]["discriminator"]
    assert disc2["propertyName"] == "strategy"
    assert len(disc2["mapping"]) == 2
    assert len(tool_by_name) == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest tests/test_mcp_tools.py -v`
Expected: FAIL (5 asserts vermelden de oude 8-tool set / oude signature)

- [ ] **Step 3: Rewrite the tool layer in `server/testassist_mcp_server.py`**

Vervang het import-blok en `_build_tools` en het registratieblok. Nieuwe inhoud:

```python
"""FastMCP server exposing test-knowledge tools to OpenCode agents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from server.advisor import advise, checklist
from server.generate import (
    generate_random as generate_random_fn,
    generate_with_property as generate_with_property_fn,
)
from server.generators import (
    generate_boundary_value_analysis,
    generate_decision_table,
    generate_equivalence_partitioning,
    generate_error_guessing,
    generate_pairwise,
    generate_state_transition,
    generate_use_case,
)
from server.knowledge_base import KnowledgeBase
from server.schemas import TechniqueCasesInput, TestDataInput

mcp = FastMCP("testassist-mcp")

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
_REPO_ROOT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
_TECHNIQUE_GENERATORS: dict[str, Callable[[dict], list[dict]]] = {
    "Boundary Value Analysis": generate_boundary_value_analysis,
    "Equivalence Partitioning": generate_equivalence_partitioning,
    "Decision Table": generate_decision_table,
    "Pairwise Testing": generate_pairwise,
    "State Transition": generate_state_transition,
    "Use Case Testing": generate_use_case,
    "Error Guessing": generate_error_guessing,
}


def _load_kb() -> KnowledgeBase:
    override = os.environ.get("TESTASSIST_KNOWLEDGE_DIR")
    if override:
        base = Path(override)
    elif _DEFAULT_KNOWLEDGE_DIR.is_dir():
        base = _DEFAULT_KNOWLEDGE_DIR
    else:
        base = _REPO_ROOT_KNOWLEDGE_DIR
    return KnowledgeBase(base)


def _build_tools(kb: KnowledgeBase) -> dict[str, Callable[..., Any]]:
    def catalog_techniques() -> dict[str, Any]:
        """List all classic test techniques (BVA, equivalence partitioning, decision table, pairwise, state transition, use case, error guessing)."""
        return {"techniques": kb.list_techniques()}

    def catalog_heuristics() -> dict[str, Any]:
        """List all test heuristics (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours)."""
        return {"heuristics": kb.list_heuristics()}

    def generate_test_cases(input: TechniqueCasesInput) -> dict[str, Any]:
        """Generate concrete test cases using a classic test technique (Boundary Value Analysis, Equivalence Partitioning, Decision Table, Pairwise Testing, State Transition, Use Case Testing, Error Guessing). Each call targets exactly one technique. For raw typed test data (random rows or property-based), use generate_test_data instead."""
        generator = _TECHNIQUE_GENERATORS.get(input.technique)
        if generator is None:  # pragma: no cover — pydantic discriminator bewaakt dit
            raise ValueError(f"Unknown technique: {input.technique}")
        payload = input.model_dump(exclude={"technique"})
        return {"technique": input.technique, "testcases": generator(payload)}

    def generate_test_data(input: TestDataInput) -> dict[str, Any]:
        """Generate raw test data (values), not technique-driven test cases. strategy='random' produces N seeded rows across multiple fields; strategy='property' produces boundary + random + invalid values for a single typed field. For classic techniques with expected outcomes, use generate_test_cases."""
        if input.strategy == "random":
            payload = {
                "fields": [f.model_dump() for f in input.fields],
                "count": input.count,
                "seed": input.seed,
            }
            return {"strategy": "random", "count": len(generate_random_fn(payload)), "cases": generate_random_fn(payload)}
        payload = {
            "field": input.field,
            "type": input.type,
            "constraints": input.constraints,
            "count": input.count,
            "seed": input.seed,
            "include_invalid": input.include_invalid,
        }
        return {"strategy": "property", "field": input.field, "type": input.type, "cases": generate_with_property_fn(payload)}

    def advise_technique(description: str) -> dict[str, Any]:
        """Recommend techniques and heuristics for a described testing context via keyword analysis."""
        return advise(kb, description)

    def checklist_for(context: str) -> dict[str, Any]:
        """Produce a recommended test checklist (items) for a context, e.g. RCRCRC for regression."""
        return checklist(kb, context)

    return {
        "catalog_techniques": catalog_techniques,
        "catalog_heuristics": catalog_heuristics,
        "generate_test_cases": generate_test_cases,
        "generate_test_data": generate_test_data,
        "advise_technique": advise_technique,
        "checklist_for": checklist_for,
    }


_tools = _build_tools(_load_kb())

for _tool_name, _tool_fn in _tools.items():
    mcp.tool()(_tool_fn)


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

- [ ] **Step 4: Run test-suite text (volledige suite)**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest`
Expected: ALL PASS. (test_mcp_tools.py 6 tests + test_schemas.py 5 + rest ongewijzigd groen)

- [ ] **Step 5: Commit**

```bash
cd /root/testassist-mcp
git add server/testassist_mcp_server.py tests/test_mcp_tools.py
git commit -m "feat: consolidate to 6 distinct tools with typed union-schema inputs"
```

---

### Task 4: Smoke-test en workflow verwachting 8 → 6

**Files:**
- Modify: `scripts/mcp-smoke.py` (default expected 8→6)
- Modify: `.github/workflows/glama-build-and-release-gate.yml` (arg `8`→`6`)

**Interfaces:**
- Consumes: niets van eerdere tasks; verwijst naar `server.testassist_mcp_server` en het 6-tool resultaat.
- Produces: werkende smoke-run met 6 tools.

- [ ] **Step 1: Change defaults**

In `scripts/mcp-smoke.py`, change:
```python
expected = int(sys.argv[1]) if len(sys.argv) > 1 else 8
```
to:
```python
expected = int(sys.argv[1]) if len(sys.argv) > 1 else 6
```

In `.github/workflows/glama-build-and-release-gate.yml` line 45:
- Change `scripts/mcp-smoke.py 8` → `scripts/mcp-smoke.py 6`.

- [ ] **Step 2: Run the smoke test locally**

Run: `cd /root/testassist-mcp && .venv/bin/python scripts/mcp-smoke.py`
Expected: prints `tools/list returned 6 tools`, lists `catalog_heuristics catalog_techniques checklist_for generate_test_cases generate_test_data advise_technique`, then `smoke test passed`.

- [ ] **Step 3: Commit**

```bash
cd /root/testassist-mcp
git add scripts/mcp-smoke.py .github/workflows/glama-build-and-release-gate.yml
git commit -m "ci: expect 6 tools in gate smoke test"
```

---

### Task 5: Docs, cards en distributie-spiegels syncen

**Files:**
- Modify: `README.md` (tool-tabel r.28-35, voorbeelden r.39-46, "8 tools" r.100+125, test-telling r.173, structuur r.161)
- Modify: `server-card.json` (tool inserted → 6 tools + versie 1.1.0)
- Modify: `.well-known/mcp/server-card.json` (zelfde inhoud)
- Modify: `mcpb/manifest.json` (description, long_description, tools → 6)
- Modify: `mcpb/server/` (kopie van gewijzigde `server/*.py`-bestanden)
- Modify: `make_presentation.py` (tools-lijst r.242-250, titel "8 tools")
- Modify: `mcpb/manifest.json` versie

**Interfaces:**
- Consumes: de 6 tool-namen (Task 3), smoke-verwachting 6 (Task 4).
- Produces: consistentie tussen repo, cards, manifest en presentatie-script.

- [ ] **Step 1: README tool-tabel vervangen (r.28-35)**

Vervang de tabel door:

```markdown
| Tool | Parameters | Beschrijving |
|---|---|---|
| `catalog_techniques` | — | Lijst alle klassieke testtechnieken op. |
| `catalog_heuristics` | — | Lijst alle testheuristieken op. |
| `generate_test_cases` | `input` (technique-union) | Genereert testcases voor één klassieke techniek: BVA, Equivalence Partitioning, Decision Table, Pairwise, State Transition, Use Case, Error Guessing. Geeft alleen testcases terug. |
| `generate_test_data` | `input` (strategy-union) | Genereert ruwe testdata: `random` (N rijen, multi-veld, seed) of `property` (boundary + random + invalid per veld). Niet techniek-gestuurd. |
| `advise_technique` | `description` (str) | Beveelt op basis van sleutelwoorden technieken en heuristieken aan voor een omschreven context. |
| `checklist_for` | `context` (str) | Levert een aanbevolen test-checklist op (items) voor een context, bijv. RCRCRC voor regressie. |
```

- [ ] **Step 2: README voorbeelden vervangen (r.39-46)**

Vervang door:

```markdown
- `catalog_techniques()` → catalogus van alle 7 technieken.
- `catalog_heuristics()` → catalogus van alle 6 heuristieken.
- `generate_test_cases({"technique": "Boundary Value Analysis", "field": "age", "min": 0, "max": 150})` → BVA-testcases rond de grenzen `-1, 0, 1, 149, 150, 151`.
- `generate_test_cases({"technique": "Decision Table", "conditions": ["pays"], "actions": ["ship"], "rules": [{"when": {"pays": "yes"}, "then": ["ship"]}]})` → één case per regel.
- `generate_test_data({"strategy": "property", "field": "age", "type": "integer", "constraints": {"min": 0, "max": 150}, "count": 10})` → boundary + random + invalid.
- `generate_test_data({"strategy": "random", "fields": [{"field": "name", "type": "string"}, {"field": "age", "type": "integer", "constraints": {"min": 0, "max": 120}}], "count": 5, "seed": 42})` → 5 reproduceerbare testrijen.
- `advise_technique("regression after a bug fix")` → beveelt o.a. RCRCRC aan.
- `checklist_for("regression")` → RCRCRC-checklist met items.
```

- [ ] **Step 3: README "8 tools"/test-telling/structuur**

- r.100: "Worden de 8 tools geregistreerd" → "Worden de 6 tools geregistreerd".
- r.125: vervang verwachting door "...`result.tools` 6 tools bevat (catalog_techniques, catalog_heuristics, generate_test_cases, generate_test_data, advise_technique, checklist_for) met non-empty descriptions."
- r.161: "generators.py  # pure testcase-generatie (BVA, EP, pairwise)" → "(7 technieken)".
- r.164: "FastMCP stdio-server die de 8 tools wiret" → "de 6 tools wiret".
- r.173: test-telling bijwerken met het werkelijke aantal: run `cd /root/testassist-mcp && .venv/bin/python -m pytest --collect-only -q | tail -1`, vul het getal in.
- Voeg na de tools-tabel (r.35) één regel toe: "Input-schema's zijn Pydantic discriminated-union-schemas (één `input`-object met `technique`- resp. `strategy`-discriminator); ongeldige technieken/strategies worden door schema-validatie afgewezen."

- [ ] **Step 4: `server-card.json` + `.well-known/mcp/server-card.json`**

Vervang de `tools`-array door 6 entries. De `generate_test_cases`- en `generate_test_data`-entries krijgen `inputSchema` met `discriminator`/`oneOf` zoals gegenereerd door de server (controleer exacte schemas via Task 3/4 tools/list output). Versie 0.2.0 → **1.1.0**. Basisstructuur:

```json
{
  "name": "test-assistent-mcp-server",
  "version": "1.1.0",
  "displayName": "Test Assistent MCP Server",
  "description": "Test assistant MCP server for OpenCode — exposes classic test techniques, test heuristics, and test data generation (random, property) as 6 tools, backed by a local knowledge base.",
  "tools": [
    {
      "name": "catalog_techniques",
      "description": "List all classic test techniques (BVA, equivalence partitioning, decision table, pairwise, state transition, use case, error guessing)."
    },
    {
      "name": "catalog_heuristics",
      "description": "List all test heuristics (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours)."
    },
    {
      "name": "generate_test_cases",
      "description": "Generate concrete test cases using a classic test technique; each call targets exactly one technique. For raw typed test data, use generate_test_data.",
      "inputSchema": { "type": "object", "properties": { "input": { "discriminator": { "propertyName": "technique", "mapping": { "Boundary Value Analysis": "#/$defs/BoundaryValueSpec", "Equivalence Partitioning": "#/$defs/EquivalenceSpec", "Decision Table": "#/$defs/DecisionTableSpec", "Pairwise Testing": "#/$defs/PairwiseSpec", "State Transition": "#/$defs/StateTransitionSpec", "Use Case Testing": "#/$defs/UseCaseSpec", "Error Guessing": "#/$defs/ErrorGuessingSpec" } }, "oneOf": [ { "$ref": "#/$defs/BoundaryValueSpec" }, { "$ref": "#/$defs/EquivalenceSpec" }, { "$ref": "#/$defs/DecisionTableSpec" }, { "$ref": "#/$defs/PairwiseSpec" }, { "$ref": "#/$defs/StateTransitionSpec" }, { "$ref": "#/$defs/UseCaseSpec" }, { "$ref": "#/$defs/ErrorGuessingSpec" } ] } }, "required": ["input"] }
    },
    {
      "name": "generate_test_data",
      "description": "Generate raw test data (values): strategy='random' produces N seeded multi-field rows; strategy='property' produces boundary + random + invalid values for one typed field.",
      "inputSchema": { "type": "object", "properties": { "input": { "discriminator": { "propertyName": "strategy", "mapping": { "random": "#/$defs/RandomDataSpec", "property": "#/$defs/PropertyDataSpec" } }, "oneOf": [ { "$ref": "#/$defs/RandomDataSpec" }, { "$ref": "#/$defs/PropertyDataSpec" } ] } }, "required": ["input"] }
    },
    {
      "name": "advise_technique",
      "description": "Recommend techniques and heuristics for a described testing context via keyword analysis.",
      "inputSchema": { "type": "object", "properties": { "description": { "type": "string", "description": "Free-text description of the testing context or problem" } }, "required": ["description"] }
    },
    {
      "name": "checklist_for",
      "description": "Produce a recommended test checklist (items) for a context, e.g. RCRCRC for regression after a bug fix.",
      "inputSchema": { "type": "object", "properties": { "context": { "type": "string", "description": "The testing context, e.g. 'regression', 'exploratory testing', 'no specification'" } }, "required": ["context"] }
    }
  ]
}
```

Let op: de `$defs`-blokken (volledige subtype-definities met properties + descriptions) voeg je bij beide cards toe rechtstreeks uit de gegeneerde `func_metadata` output (Task 3) — kopieer exact, zodat de cards en de server identieke schemas tonen.

- [ ] **Step 5: `mcpb/manifest.json` en `mcpb/server/`**

- `mcpb/manifest.json`: versie 0.2.0 → 1.1.0; pas `description` en `long_description` aan voor 6 tools en "generate_test_cases (7 techniques) / generate_test_data"; vervang de 8 entries in de `tools`-array door de 6 nieuwe namen.
- `mcpb/server/`: kopieer de gewijzigde bestanden `schemas.py`, `generators.py`, `testassist_mcp_server.py` van `server/` naar `mcpb/server/` (`cp server/schemas.py server/generators.py server/testassist_mcp_server.py mcpb/server/`). Daarna `python -m compileall -q mcpb/server` als sanity-check.

- [ ] **Step 6: `make_presentation.py` (r.240-251)**

- Titel "Wat kan het? — de 8 tools" → "Wat kan het? — de 6 tools".
- Vervang `tools = [...]` (8 entries) door:

```python
tools = [
    ("catalog_techniques", "Lijst alle classieke testtechnieken"),
    ("catalog_heuristics", "Lijst alle test-heuristieken"),
    ("generate_test_cases", "Testcases voor 7 technieken (BVA, EP, DT, pairwise, ...)"),
    ("generate_test_data", "Ruwe testdata: random rijen of property-based"),
    ("advise_technique", "Aanbeveling van techniek op basis van context"),
    ("checklist_for", "Testchecklist voor een context (bijv. RCRCRC)"),
]
```

- [ ] **Step 7: Run tests + smoke + commit**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest && .venv/bin/python scripts/mcp-smoke.py`
Expected: ALL PASS + `smoke test passed` (6 tools).

```bash
cd /root/testassist-mcp
git add README.md server-card.json .well-known/mcp/server-card.json mcpb/manifest.json mcpb/server make_presentation.py
git commit -m "docs: sync README, server-cards, MCPB manifest and presentation to 6-tool redesign"
```

---

### Task 6: Versie 1.1.0, tag v1.1.0, release-gate

**Files:**
- Modify: `pyproject.toml` (`version = "1.1.0"`)
- Modify: `uv.lock` (root package version)
- Modify: `mcpb/manifest.json` + `server-card.json` + `.well-known/mcp/server-card.json` zijn al op 1.1.0 (Task 5)

**Interfaces:**
- Consumes: Task 1-5 commits op `main`; versie in `pyproject.toml` moet matchen met tag `v1.1.0` (workflow-gate).

- [ ] **Step 1: Update version & lock**

In `pyproject.toml`:
- `version = "1.0.1"` → `version = "1.1.0"`

Run: `cd /root/testassist-mcp && .venv/bin/uv lock`

- [ ] **Step 2: Verify**

Run: `cd /root/testassist-mcp && .venv/bin/python -m pytest && .venv/bin/python scripts/mcp-smoke.py`
Expected: ALL PASS; smoke 6 tools.

- [ ] **Step 3: Commit + tag**

```bash
cd /root/testassist-mcp
git add pyproject.toml uv.lock
git commit -m "chore: bump version to 1.1.0"
git tag v1.1.0
```

- [ ] **Step 4: Push main + tag (SSH-URL, zie AGENTS.md)**

```bash
cd /root/testassist-mcp
git push git@github.com:Cerios-TechLab/test-assistent-mcp-server.git main
git push git@github.com:Cerios-TechLab/test-assistent-mcp-server.git v1.1.0
```

- [ ] **Step 5: Controleer gate**

Run: `gh run list --repo Cerios-TechLab/test-assistent-mcp-server --limit 3`
Expected: de v1.1.0-run is `success` (verify incl. mcp-smoke 6 tools + release-job). Controleer daarna de GitHub Release pagina voor v1.1.0.

- [ ] **Step 6: Endpoint-verificatie (optioneel, na sync)**

Nadat Glama de release automatisch heeft gesynct (pattern eerder bevestigd bij quality-coach):
`GET https://glama.ai/endpoints/x032ijfw89/mcp` handshake (initialize → tools/list) en controleer: 6 tools, `generate_test_cases.inputSchema` bevat `discriminator.propertyName == "technique"` met 7 mapping-entries, `generate_test_data` met `strategy` en 2 entries.
```

## Self-Review

**Spec coverage:**
- Overlap-fix 4→2 generatie-tools met rolscheiding in descriptions: Task 3 ✓
- Alle 7 technieken genereerbaar: Task 2 (4 nieuwe) + Task 1 (7 Literal-varianten) ✓
- Rijke schemas (TDQSB): Task 1 (alle velden `Field(description=...)`, unions + discriminator), getest in Task 3 `test_tool_schemas_use_discriminators` ✓
- Verwijderde tools niet meer in registry: Task 3 (6-tool set) ✓
- mcp-smoke/workflow 8→6: Task 4 ✓
- Docs/cards/mcpb/presentatie sync: Task 5 ✓
- Versie 1.1.0 + tag + release-gate: Task 6 ✓
- Bijkomende punt: `config als beschrijving` noemen (Levendige schemas); advies/catalog-ondersteuning in tests gehandhaafd ✓

**Placeholder scan:** geen TBD/TODO; alle code-lijsten concreet. De enige dynamische stap is de test-telling in Task 5 Step 3 en de exacte `$defs`-dump in Step 4 — beide zijn instructies met het exacte commando om de waarde te verkrijgen, geen placeholder.

**Type consistency:** `TestDataInput`/`TechniqueCasesInput`/7 vorgeneratoren namen/`_TECHNIQUE_GENERATORS` keys matchen tussen Task 1/2/3. Literal-waarden = knowledgebase namen. Smoke verwachting 6 overal.