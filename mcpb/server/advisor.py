"""Keyword-based advice and checklist logic over the knowledge base."""
from __future__ import annotations

from typing import Any

from server.knowledge_base import KnowledgeBase

_TECHNIQUE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Boundary Value Analysis": ("range", "boundary", "edge", "min", "max", "limit"),
    "Equivalence Partitioning": ("partition", "invalid", "valid", "class", "group"),
    "Decision Table": ("condition", "rule", "combination", "business rule", "if then"),
    "Pairwise Testing": ("pair", "combination", "parameter", "matrix"),
    "State Transition": ("state", "transition", "event", "sequence", "workflow"),
    "Use Case Testing": ("use case", "actor", "flow", "user journey", "happy path"),
    "Error Guessing": ("error", "crash", "null", "empty", "duplicate", "guessing"),
}

_HEURISTIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "SFDPOT": ("unfamiliar", "survey", "product elements", "cover all"),
    "FEW HICCUPPS": ("spec", "no specification", "oracle", "expected behavior", "consistency"),
    "RCRCRC": ("regression", "bug fix", "fix", "recent change", "risk"),
    "Quality Criteria Catalog": ("quality", "good enough", "criteria", "ship"),
    "Bug Heuristics": ("bug ideas", "failure", "explore", "crash"),
    "Test Tours": ("exploratory", "tour", "wander", "discover"),
}


def advise(kb: KnowledgeBase, text: str) -> dict[str, Any]:
    """Return matching technique and heuristic names for a free-text description."""
    lowered = text.lower()
    techniques = [name for name, kw in _TECHNIQUE_KEYWORDS.items() if any(k in lowered for k in kw)]
    heuristics = [name for name, kw in _HEURISTIC_KEYWORDS.items() if any(k in lowered for k in kw)]
    reasoning = (
        f"Matched {len(techniques)} technique(s) and {len(heuristics)} heuristic(s) "
        f"by keyword analysis of the description."
    )
    return {"techniques": techniques, "heuristics": heuristics, "reasoning": reasoning}


def checklist(kb: KnowledgeBase, context: str) -> dict[str, Any]:
    """Return a checklist for a context by picking the best-matching heuristic."""
    lowered = context.lower()
    best = None
    best_score = 0
    for name, kw in _HEURISTIC_KEYWORDS.items():
        score = sum(1 for k in kw if k in lowered)
        if score > best_score:
            best_score = score
            best = name
    if best is None or best_score == 0:
        return {"heuristic": None, "items": []}
    heuristic = kb.get_heuristic(best)
    items = [f"{entry['letter']} — {entry['description']}" for entry in heuristic["letters"]]
    return {"heuristic": best, "items": items}
