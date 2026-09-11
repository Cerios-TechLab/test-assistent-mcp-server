"""Tool-registry and schema-shape tests for the 6-tool testassist server."""
import asyncio
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

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
    cases_adapter = TypeAdapter(TechniqueCasesInput)
    for spec in [
        {"technique": "Boundary Value Analysis", "field": "age", "min": 0, "max": 150},
        {"technique": "Equivalence Partitioning", "field": "email", "valid": ["a@b.c"], "invalid": [""]},
        {"technique": "Decision Table", "conditions": ["pay"], "actions": ["ship"], "rules": [{"when": {"pay": "yes"}, "then": ["ship"]}]},
        {"technique": "Pairwise Testing", "values": {"browser": ["c", "f"], "os": ["linux", "win"]}},
        {"technique": "State Transition", "states": ["open"], "events": ["close"], "transitions": [{"state": "open", "event": "close", "next": "closed"}]},
        {"technique": "Use Case Testing", "name": "login", "steps": ["fill", "submit"], "expected": ["ok"]},
        {"technique": "Error Guessing", "field": "email", "input": "a@b.c", "pitfalls": ["", None]},
    ]:
        out = tools["generate_test_cases"](cases_adapter.validate_python(spec))
        assert out["technique"] == spec["technique"]
        assert out["testcases"], f"no cases for {spec['technique']}"


def test_generate_test_data_random_and_property():
    tools = _build_tools(KB)
    data_adapter = TypeAdapter(TestDataInput)
    rnd = tools["generate_test_data"](data_adapter.validate_python(
        {"strategy": "random",
         "fields": [{"field": "age", "type": "integer", "constraints": {"min": 0, "max": 10}}],
         "count": 3, "seed": "s"}))
    assert rnd["strategy"] == "random"
    assert len(rnd["cases"]) == 3
    prop = tools["generate_test_data"](data_adapter.validate_python(
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