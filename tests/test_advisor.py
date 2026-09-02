from pathlib import Path

from server.advisor import advise, checklist
from server.knowledge_base import KnowledgeBase

KB = KnowledgeBase(Path(__file__).resolve().parents[1] / "knowledge")


def test_advise_regression_picks_rcrcrc():
    result = advise(KB, "We need to test after a bug fix; regression risk is high")
    assert "RCRCRC" in result["heuristics"]


def test_advise_missing_spec_picks_few_hiccupps():
    result = advise(KB, "There is no specification, we must guess expected behavior")
    assert "FEW HICCUPPS" in result["heuristics"]


def test_advise_data_field_picks_techniques():
    result = advise(KB, "A form field with a numeric range should reject out-of-range values")
    assert "Boundary Value Analysis" in result["techniques"]


def test_checklist_regression_returns_items():
    result = checklist(KB, "regression")
    assert result["heuristic"] == "RCRCRC"
    assert result["items"]
    assert all(isinstance(i, str) for i in result["items"])
