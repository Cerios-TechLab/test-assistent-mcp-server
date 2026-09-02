"""FastMCP server exposing test-knowledge tools to OpenCode agents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from server.advisor import advise, checklist
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
        return {"techniques": kb.list_techniques()}

    def catalog_heuristics() -> dict[str, Any]:
        return {"heuristics": kb.list_heuristics()}

    def generate_test_cases(technique: str, inputs: dict) -> dict[str, Any]:
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
        return advise(kb, description)

    def checklist_for(context: str) -> dict[str, Any]:
        return checklist(kb, context)

    return {
        "catalog_techniques": catalog_techniques,
        "catalog_heuristics": catalog_heuristics,
        "generate_test_cases": generate_test_cases,
        "advise_technique": advise_technique,
        "checklist_for": checklist_for,
    }


_tools = _build_tools(_load_kb())

for _tool_name, _tool_fn in _tools.items():
    mcp.tool()(_tool_fn)


if __name__ == "__main__":
    mcp.run(transport="stdio")
