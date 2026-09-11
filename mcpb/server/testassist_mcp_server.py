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
            cases = generate_random_fn(payload)
            return {"strategy": "random", "count": len(cases), "cases": cases}
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