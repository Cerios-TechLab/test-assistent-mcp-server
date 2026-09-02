import json
from pathlib import Path

import pytest

from server.knowledge_base import KnowledgeBase

FIXTURE = {
    "techniques": {
        "boundary_value_analysis.json": {
            "name": "Boundary Value Analysis",
            "description": "Tests at the edges of input ranges.",
            "when_to_use": "When inputs have defined ranges.",
            "steps": ["Find boundaries", "Test at and around them"],
            "example": "Age 0..150",
        }
    },
    "heuristics": {
        "rcrcrc.json": {
            "name": "RCRCRC",
            "source": "Karen N. Johnson",
            "category": "regression",
            "when_to_use": "Planning regression tests.",
            "letters": {"R": "Recent", "C": "Core"},
            "example": "Recent changes are risk-prone.",
        }
    },
}


@pytest.fixture
def kb(tmp_path: Path):
    for sub, files in FIXTURE.items():
        d = tmp_path / sub
        d.mkdir(parents=True, exist_ok=True)
        for fname, data in files.items():
            (d / fname).write_text(json.dumps(data))
    return KnowledgeBase(tmp_path)


def test_lists_techniques_and_heuristics(kb):
    assert kb.list_techniques() == [FIXTURE["techniques"]["boundary_value_analysis.json"]]
    assert kb.list_heuristics() == [FIXTURE["heuristics"]["rcrcrc.json"]]


def test_get_by_name(kb):
    assert kb.get_technique("Boundary Value Analysis")["description"].startswith("Tests at the edges")
    assert kb.get_heuristic("RCRCRC")["source"] == "Karen N. Johnson"


def test_unknown_name_raises_keyerror(kb):
    with pytest.raises(KeyError):
        kb.get_technique("Nonexistent")
    with pytest.raises(KeyError):
        kb.get_heuristic("Nonexistent")


def test_missing_directory_raises(kb, tmp_path):
    with pytest.raises(FileNotFoundError):
        KnowledgeBase(tmp_path / "does_not_exist")
