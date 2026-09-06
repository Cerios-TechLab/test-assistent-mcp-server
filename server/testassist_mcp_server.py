"""FastMCP server exposing test-knowledge tools to OpenCode agents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from server.advisor import advise, checklist
from server.generate import (
    generate_boundary_cases as generate_boundary_cases_fn,
    generate_random as generate_random_fn,
    generate_with_property as generate_with_property_fn,
)
from server.generators import (
    generate_boundary_value_analysis,
    generate_equivalence_partitioning,
    generate_pairwise,
)
from server.knowledge_base import KnowledgeBase

mcp = FastMCP("testassist-mcp")

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
_TECHNIQUE_GENERATORS: dict[str, Callable[[dict], list[dict]]] = {
    "Boundary Value Analysis": generate_boundary_value_analysis,
    "Equivalence Partitioning": generate_equivalence_partitioning,
    "Pairwise Testing": generate_pairwise,
}


def _load_kb() -> KnowledgeBase:
    override = os.environ.get("TESTASSIST_KNOWLEDGE_DIR")
    base = Path(override) if override else _DEFAULT_KNOWLEDGE_DIR
    return KnowledgeBase(base)


def _build_tools(kb: KnowledgeBase) -> dict[str, Callable[..., Any]]:
    def catalog_techniques() -> dict[str, Any]:
        """List all classic test techniques (BVA, equivalence partitioning, decision table, pairwise, state transition, use case, error guessing)."""
        return {"techniques": kb.list_techniques()}

    def catalog_heuristics() -> dict[str, Any]:
        """List all test heuristics (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours)."""
        return {"heuristics": kb.list_heuristics()}

    def generate_test_cases(technique: str, inputs: dict) -> dict[str, Any]:
        """Generate concrete testcases for a supported technique. Only returns testcases; the agent does the rest."""
        generator = _TECHNIQUE_GENERATORS.get(technique)
        if generator is None:
            supported = ", ".join(sorted(_TECHNIQUE_GENERATORS))
            raise ValueError(
                f"Technique '{technique}' is not auto-generable here. "
                f"Supported: {supported}. Others are available via catalog_techniques."
            )
        cases = generator(inputs)
        return {"technique": technique, "testcases": cases}

    def advise_technique(description: str) -> dict[str, Any]:
        """Recommend techniques and heuristics for a described testing context via keyword analysis."""
        return advise(kb, description)

    def checklist_for(context: str) -> dict[str, Any]:
        """Produce a recommended test checklist (items) for a context, e.g. RCRCRC for regression."""
        return checklist(kb, context)

    def generate_with_property(spec: dict) -> dict[str, Any]:
        """Property-based test data generation. Defines a field with type, constraints, and count, returns test cases including boundary values and random data."""
        cases = generate_with_property_fn(spec)
        return {"field": spec.get("field"), "type": spec.get("type", "string"), "cases": cases}

    def generate_boundary_cases(spec: dict) -> dict[str, Any]:
        """Generate boundary value test cases for a field. Supports int, float, string, date types with automatic edge case discovery."""
        cases = generate_boundary_cases_fn(spec)
        return {"field": spec.get("field"), "type": spec.get("type", "integer"), "cases": cases}

    def generate_random(spec: dict) -> dict[str, Any]:
        """Generate constrained random test data for multiple fields with optional seed for reproducibility."""
        cases = generate_random_fn(spec)
        return {"cases": cases}

    return {
        "catalog_techniques": catalog_techniques,
        "catalog_heuristics": catalog_heuristics,
        "generate_test_cases": generate_test_cases,
        "generate_with_property": generate_with_property,
        "generate_boundary_cases": generate_boundary_cases,
        "generate_random": generate_random,
        "advise_technique": advise_technique,
        "checklist_for": checklist_for,
    }


_tools = _build_tools(_load_kb())

for _tool_name, _tool_fn in _tools.items():
    mcp.tool()(_tool_fn)


if __name__ == "__main__":
    mcp.run(transport="stdio")
