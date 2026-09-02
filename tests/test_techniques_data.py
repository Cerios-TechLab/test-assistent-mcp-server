from pathlib import Path

from server.knowledge_base import KnowledgeBase

REQUIRED = {"name", "description", "when_to_use", "steps", "example"}
EXPECTED = {"Boundary Value Analysis", "Equivalence Partitioning", "Decision Table",
            "Pairwise Testing", "State Transition", "Use Case Testing", "Error Guessing"}


def test_all_techniques_well_formed():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    names = kb.technique_names()
    assert set(names) == EXPECTED
    for t in kb.list_techniques():
        assert REQUIRED.issubset(t.keys())
        assert isinstance(t["steps"], list) and t["steps"]
        assert isinstance(t["description"], str) and t["description"]
