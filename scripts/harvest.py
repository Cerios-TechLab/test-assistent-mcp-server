"""Validate the knowledge base and print an index summary.

Usage: python scripts/harvest.py
Exits 0 if the knowledge base is well-formed, non-zero otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

from server.knowledge_base import KnowledgeBase

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"


def main() -> int:
    kb = KnowledgeBase(KNOWLEDGE_DIR)
    print(f"Knowledge base OK at {KNOWLEDGE_DIR}")
    print(f"  techniques ({len(kb.list_techniques())}):")
    for name in sorted(kb.technique_names()):
        print(f"    - {name}")
    print(f"  heuristics ({len(kb.list_heuristics())}):")
    for name in sorted(kb.heuristic_names()):
        print(f"    - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
