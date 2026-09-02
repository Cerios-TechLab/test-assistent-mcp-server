"""Load and validate the test-knowledge base from structured JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeBase:
    """Loads technique and heuristic JSON files from a knowledge directory."""

    def __init__(self, knowledge_dir: str | Path) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self._techniques: list[dict[str, Any]] = self._load_dir("techniques")
        self._heuristics: list[dict[str, Any]] = self._load_dir("heuristics")
        self._techniques_by_name = {t["name"]: t for t in self._techniques}
        self._heuristics_by_name = {h["name"]: h for h in self._heuristics}

    def _load_dir(self, sub: str) -> list[dict[str, Any]]:
        d = self.knowledge_dir / sub
        if not d.is_dir():
            raise FileNotFoundError(f"Missing knowledge directory: {d}")
        items = []
        for path in sorted(d.glob("*.json")):
            with path.open(encoding="utf-8") as f:
                items.append(json.load(f))
        return items

    def list_techniques(self) -> list[dict[str, Any]]:
        return self._techniques

    def list_heuristics(self) -> list[dict[str, Any]]:
        return self._heuristics

    def technique_names(self) -> list[str]:
        return list(self._techniques_by_name)

    def heuristic_names(self) -> list[str]:
        return list(self._heuristics_by_name)

    def get_technique(self, name: str) -> dict[str, Any]:
        try:
            return self._techniques_by_name[name]
        except KeyError:
            raise KeyError(f"Unknown technique '{name}'. Available: {sorted(self._techniques_by_name)}")

    def get_heuristic(self, name: str) -> dict[str, Any]:
        try:
            return self._heuristics_by_name[name]
        except KeyError:
            raise KeyError(f"Unknown heuristic '{name}'. Available: {sorted(self._heuristics_by_name)}")
