from pathlib import Path

from server.testassist_mcp_server import _build_tools
from server.knowledge_base import KnowledgeBase


def test_build_tools_exposes_five():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    tools = _build_tools(kb)
    assert set(tools) == {"catalog_techniques", "catalog_heuristics",
                          "generate_test_cases", "advise_technique", "checklist_for"}


def test_generate_test_cases_bva():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    tools = _build_tools(kb)
    out = tools["generate_test_cases"]("Boundary Value Analysis", {"field": "age", "min": 0, "max": 150})
    assert out["technique"] == "Boundary Value Analysis"
    assert len(out["testcases"]) >= 6


def test_advise_technique_smoke():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    tools = _build_tools(kb)
    out = tools["advise_technique"]("regression after a bug fix")
    assert "RCRCRC" in out["heuristics"]


def test_checklist_for_regression():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    tools = _build_tools(kb)
    out = tools["checklist_for"]("regression")
    assert out["heuristic"] == "RCRCRC"
    assert out["items"]
