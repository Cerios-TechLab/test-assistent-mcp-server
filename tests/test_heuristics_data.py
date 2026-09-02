from pathlib import Path

from server.knowledge_base import KnowledgeBase

REQUIRED = {"name", "source", "category", "when_to_use", "letters", "example"}
EXPECTED = {"SFDPOT", "FEW HICCUPPS", "RCRCRC", "Quality Criteria Catalog",
            "Bug Heuristics", "Test Tours"}


def test_all_heuristics_well_formed():
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")
    names = kb.heuristic_names()
    assert set(names) == EXPECTED
    for h in kb.list_heuristics():
        assert REQUIRED.issubset(h.keys())
        assert isinstance(h["source"], str) and isinstance(h["category"], str)
        assert isinstance(h["letters"], list) and h["letters"]
        for entry in h["letters"]:
            assert isinstance(entry, dict) and {"letter", "description"}.issubset(entry)
        assert isinstance(h["example"], str) and h["example"]
        assert isinstance(h["when_to_use"], str) and h["when_to_use"]
