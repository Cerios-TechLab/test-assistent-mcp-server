# Test Assistant MCP Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python + FastMCP knowledge/tools MCP-server that gives OpenCode agents access to classic test techniques and test heuristics (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria, bug heuristics, test tours) via 5 tools, backed by a local, self-contained knowledge base.

**Architecture:** A FastMCP stdio server (`server/testassist_mcp_server.py`) reads structured JSON from a bundled `knowledge/` directory. The server exposes 5 tools: `catalog_techniques`, `catalog_heuristics`, `generate_test_cases`, `advise_technique`, `checklist_for`. Knowledge lives as JSON—one file per technique/heuristic—so it can be extended without code changes. A one-time `scripts/harvest.py` scaffolds/updates the knowledge base.

**Tech Stack:** Python 3.11, `mcp` package (FastMCP), `pytest`. Mirrors the existing `/root/visio-mcp/` conventions.

## Global Constraints

- Python 3.11 — use `/usr/bin/python3.11` (NOT `python3` which is 3.9). Venv at `.venv`.
- Dependency: `mcp==1.29.0` (same as visio-mcp). FastMCP import: `from mcp.server.fastmcp import FastMCP`. Server entry: `mcp.run(transport="stdio")`.
- Knowledge lives in `knowledge/` as JSON — never hardcode technique/heuristic content into the server code.
- JSON schema for technique entries: keys `name`, `description`, `when_to_use`, `steps` (list), `example` (string).
- JSON schema for heuristic entries: keys `name`, `source`, `category`, `when_to_use`, `letters` (an ordered LIST of `{"letter": str, "description": str}` objects — mnemonics can repeat letters, so a dict would silently drop duplicates), `example`.
- All content is original formulation (own wording) — do NOT copy copyrighted material verbatim.
- Use `pytest` from the venv; tests live under `tests/`.
- Commit after each task with a descriptive message.

---

## File Structure

- `pyproject.toml` — project metadata + deps (`mcp==1.29.0`) + pytest config.
- `server/__init__.py` — package marker.
- `server/knowledge_base.py` — loads and validates all JSON from `knowledge/`; exposes lookups. Pure logic, no MCP dependency, easy to unit test.
- `server/generators.py` — pure testcase-generation logic (BVA, equivalence partitioning, decision table) + checklist builder. Pure functions, no MCP dependency.
- `server/advisor.py` — keyword-based advise/checklist logic over the knowledge base. Pure functions.
- `server/testassist_mcp_server.py` — FastMCP server wiring the 5 tools to the above modules; reads knowledge dir path from env or defaults to repo-relative `knowledge/`.
- `knowledge/techniques/*.json` — one file per technique (BVA, equivalence partitioning, decision tables, pairwise, state transition, use case, error guessing).
- `knowledge/heuristics/*.json` — one file per heuristic list (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours).
- `knowledge/guides/*.md` — optional longer guides (can be added later; not required for the tools).
- `scripts/harvest.py` — one-time scaffold/validation script that (re)generates an index and verifies the knowledge base.
- `tests/` — pytest tests per module.

---

### Task 1: Project scaffolding + knowledge base loader

**Files:**
- Create: `pyproject.toml`
- Create: `server/__init__.py`
- Create: `server/knowledge_base.py`
- Create: `tests/test_knowledge_base.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `KnowledgeBase` class with methods:
    - `list_techniques() -> list[dict]`
    - `list_heuristics() -> list[dict]`
    - `get_technique(name: str) -> dict` (raises `KeyError` if missing)
    - `get_heuristic(name: str) -> dict` (raises `KeyError` if missing)
    - `technique_names() -> list[str]`
    - `heuristic_names() -> list[str]`
  - Constructor: `KnowledgeBase(knowledge_dir: str | Path)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knowledge_base.py
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
            "letters": [
                {"letter": "R", "description": "Recent"},
                {"letter": "C", "description": "Core"},
            ],
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_knowledge_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server'` (no package/tests yet).

- [ ] **Step 3: Create project scaffolding**

`pyproject.toml`:
```toml
[project]
name = "testassist-mcp"
version = "0.1.0"
description = "Test assistant MCP server for OpenCode"
requires-python = ">=3.11"
dependencies = ["mcp==1.29.0"]

[project.optional-dependencies]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`server/__init__.py`:
```python
"""Test assistant MCP server package."""
```

`server/knowledge_base.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_knowledge_base.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Create venv and install deps (first time only)**

Run:
```bash
/usr/bin/python3.11 -m venv /root/testassist-mcp/.venv
/root/testassist-mcp/.venv/bin/pip install -e '.[dev]'
```
Expected: install succeeds, `mcp==1.29.0`, `pytest` present.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml server/ tests/test_knowledge_base.py
git commit -m "feat: scaffold project and knowledge base loader with tests"
```

---

### Task 2: Technique knowledge data

**Files:**
- Create: `knowledge/techniques/boundary_value_analysis.json`
- Create: `knowledge/techniques/equivalence_partitioning.json`
- Create: `knowledge/techniques/decision_table.json`
- Create: `knowledge/techniques/pairwise_testing.json`
- Create: `knowledge/techniques/state_transition.json`
- Create: `knowledge/techniques/use_case_testing.json`
- Create: `knowledge/techniques/error_guessing.json`
- Create: `tests/test_techniques_data.py`

**Interfaces:**
- Consumes: `KnowledgeBase` from Task 1.
- Produces: fully-populated `knowledge/techniques/` such that `KnowledgeBase.list_techniques()` returns 7 well-formed entries. Later tasks (advisory/generation) use these JSON fields (`name`, `when_to_use`, `steps`, `example`).

- [ ] **Step 1: Write the failing data-integrity test**

```python
# tests/test_techniques_data.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_techniques_data.py -v`
Expected: FAIL — empty `knowledge/techniques/` (or missing dir → `FileNotFoundError`).

- [ ] **Step 3: Create the technique JSON files**

`knowledge/techniques/boundary_value_analysis.json`:
```json
{
  "name": "Boundary Value Analysis",
  "description": "Tests are designed at and around the edges of valid input ranges, where defects cluster.",
  "when_to_use": "When an input or output has a defined numeric range, length limit, or count limit.",
  "steps": [
    "Identify each variable's valid range (min/max inclusive).",
    "Select the boundary values: min, max, and one step above/below each.",
    "Also select values just inside the valid range and just outside it.",
    "For each selected value, define the expected outcome."
  ],
  "example": "An age field accepting 0..150: test -1, 0, 1, 149, 150, 151."
}
```

`knowledge/techniques/equivalence_partitioning.json`:
```json
{
  "name": "Equivalence Partitioning",
  "description": "Divide inputs into groups (partitions) that a system is expected to treat the same; test one representative from each valid and invalid partition.",
  "when_to_use": "When input can be grouped into logical classes whose members share expected behavior.",
  "steps": [
    "List all input conditions and their valid/invalid classes.",
    "Define partitions such that values in one partition behave the same.",
    "Pick one representative value per partition.",
    "Design one test per partition, including invalid partitions."
  ],
  "example": "A login accepts an email: valid format, empty, malformed, registered, and unregistered are separate partitions."
}
```

`knowledge/techniques/decision_table.json`:
```json
{
  "name": "Decision Table",
  "description": "A table of conditions (inputs) and actions (outputs) covering all relevant combinations of true/false conditions.",
  "when_to_use": "When business rules depend on combinations of conditions with clear reactions.",
  "steps": [
    "List all conditions as binary (or multi-valued) inputs.",
    "List all possible actions.",
    "Create a column for each relevant combination of conditions.",
    "Mark which actions apply per combination; eliminate unfeasible combinations.",
    "Turn each feasible column into a test."
  ],
  "example": "Order pricing: is member? is discount code valid? → action set for each of the 4 combinations."
}
```

`knowledge/techniques/pairwise_testing.json`:
```json
{
  "name": "Pairwise Testing",
  "description": "Systematically covers all pairs of parameter values rather than all combinations, reducing test count while catching most interaction defects.",
  "when_to_use": "When many parameters with many values make exhaustive combination testing impractical.",
  "steps": [
    "List each parameter and its values.",
    "Generate a subset of value combinations so that every pair of values across parameters appears at least once.",
    "Fill remaining cells to maximize coverage.",
    "Convert each generated row into a test."
  ],
  "example": "Browser (3) x OS (3) x Screen (2) = 18 rows instead of 3*3*2 = 18 full — pairwise keeps it near-minimal while covering every pair."
}
```

`knowledge/techniques/state_transition.json`:
```json
{
  "name": "State Transition",
  "description": "Model a system as states and the events that move it between them; test valid, invalid, and missing transitions.",
  "when_to_use": "When behavior depends on a sequence of events or internal states.",
  "steps": [
    "Identify states, events, and resulting transitions.",
    "Draw or tabulate the transition table.",
    "Design tests for each legitimate transition and each invalid/blocked transition.",
    "Include start-to-end and end-state tests."
  ],
  "example": "A payment goes Active → Processing → Paid; events like timeouts must not move it to Paid."
}
```

`knowledge/techniques/use_case_testing.json`:
```json
{
  "name": "Use Case Testing",
  "description": "Tests derived from use cases, covering the main flow and alternative/exception flows from an actor's perspective.",
  "when_to_use": "When requirements are expressed as use cases or user journeys.",
  "steps": [
    "Identify the primary actor and the use case's main (happy) flow.",
    "Extend to alternative flows and exception flows.",
    "Design a test for each flow.",
    "Include preconditions and postconditions."
  ],
  "example": "For 'Patient books appointment': main flow books successfully; alternative adds insurance; exception covers no slots available."
}
```

`knowledge/techniques/error_guessing.json`:
```json
{
  "name": "Error Guessing",
  "description": "Anticipate likely errors based on experience and intuition about where developers typically make mistakes.",
  "when_to_use": "As a complement after systematic techniques; when testing familiar patterns or past bug areas.",
  "steps": [
    "List inputs and operations the system performs.",
    "Brainstorm failure-prone situations (empty, null, zero, boundary, repeat, divide, concurrent, unauthorized).",
    "Turn each suspicion into a test.",
    "Prioritize by risk of the anticipated failure."
  ],
  "example": "Divide by zero, missing required field, resubmitting a form twice, expired session during a long action."
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_techniques_data.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add knowledge/techniques/ tests/test_techniques_data.py
git commit -m "feat: add classic test technique knowledge entries"
```

---

### Task 3: Heuristic knowledge data

**Files:**
- Create: `knowledge/heuristics/sfdpot.json`
- Create: `knowledge/heuristics/few_hiccupps.json`
- Create: `knowledge/heuristics/rcrcrc.json`
- Create: `knowledge/heuristics/quality_criteria_catalog.json`
- Create: `knowledge/heuristics/bug_heuristics.json`
- Create: `knowledge/heuristics/test_tours.json`
- Create: `tests/test_heuristics_data.py`

**Interfaces:**
- Consumes: `KnowledgeBase` from Task 1.
- Produces: populated `knowledge/heuristics/`. SFDPOT, FEW HICCUPPS, and RCRCRC are required by the user. Later tasks read `name`, `category`, `when_to_use`, and `letters`.

- [ ] **Step 1: Write the failing data-integrity test**

```python
# tests/test_heuristics_data.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_heuristics_data.py -v`
Expected: FAIL — empty `knowledge/heuristics/`.

- [ ] **Step 3: Create the heuristic JSON files**

`knowledge/heuristics/sfdpot.json`:
```json
{
  "name": "SFDPOT",
  "source": "James Bach",
  "category": "product elements",
  "when_to_use": "Survey a product from several angles to generate coverage ideas and surface risk, especially when testing something unfamiliar.",
  "letters": [
    {"letter": "S", "description": "Structure — what the product is made of: files, modules, libraries, state. Can you test it piece by piece?"},
    {"letter": "F", "description": "Function — what the product does: features, error handling, interfaces, non-visible behavior."},
    {"letter": "D", "description": "Data — what it processes and produces: inputs, outputs, formats, defaults, constraints, persistence."},
    {"letter": "P", "description": "Platform — what it depends on: OSes, browsers, third-party libraries, environment configuration."},
    {"letter": "O", "description": "Operations — how it will be used: who uses it, in which roles, for what tasks, realistic usage patterns."},
    {"letter": "T", "description": "Time — any relationship with time: timing, concurrency, fast/slow input, delays, schedule-sensitive behavior."}
  ],
  "example": "For a CSV import feature: Structure=the parser; Function=parse→dedupe→create; Data=encoding/malformed rows; Platform=browser upload; Operations=spreadsheet exports; Time=sync delay vs rows committed."
}
```

`knowledge/heuristics/few_hiccupps.json`:
```json
{
  "name": "FEW HICCUPPS",
  "source": "James Bach & Michael Bolton",
  "category": "oracles",
  "when_to_use": "Recognize problems when there is no spec, or the spec is thin, by checking consistency with known or plausible expectations.",
  "letters": [
    {"letter": "F", "description": "Familiarity — does the system match a pattern of familiar problems?"},
    {"letter": "E", "description": "Explainability — can the behavior be explained clearly to ourselves and others?"},
    {"letter": "W", "description": "World — is it consistent with what we know about the world?"},
    {"letter": "H", "description": "History — is it consistent with past versions of itself?"},
    {"letter": "I", "description": "Image — does it fit the image/brand the organization wants to project?"},
    {"letter": "C", "description": "Comparable products — is it consistent with comparable products or processes?"},
    {"letter": "C", "description": "Claims — is it consistent with what important people say it should do (docs, specs, meetings)?"},
    {"letter": "U", "description": "User Desires — is it consistent with what reasonable users would want?"},
    {"letter": "P", "description": "Product — is each element consistent with comparable elements in the same product?"},
    {"letter": "P", "description": "Purpose — is it consistent with its explicit and implicit purposes?"},
    {"letter": "S", "description": "Statutes & Standards — is it consistent with relevant laws, regulations, and standards?"}
  ],
  "example": "New version changed behavior with no stated reason → History oracle flags a likely problem."
}
```

`knowledge/heuristics/rcrcrc.json`:
```json
{
  "name": "RCRCRC",
  "source": "Karen N. Johnson",
  "category": "regression",
  "when_to_use": "Plan and prioritize regression testing after a change or bug fix.",
  "letters": [
    {"letter": "R", "description": "Recent — what new code or features were recently changed? Test around them."},
    {"letter": "C", "description": "Core — which essential functions must keep working? Prioritize these."},
    {"letter": "R", "description": "Risky — which features or code areas are inherently risky or historically buggy?"},
    {"letter": "C", "description": "Configuration sensitive — what code depends on environment settings and could break?"},
    {"letter": "R", "description": "Repaired — what was changed to fix defects, risking new issues?"},
    {"letter": "C", "description": "Chronic — which areas break repeatedly? Give them more focus."}
  ],
  "example": "After a login fix: Recent=login change; Core=authn must still work; Risky=token refresh; Configuration=env-config timeouts; Repaired=the login fix; Chronic=the auth area that keeps regressing."
}
```

`knowledge/heuristics/quality_criteria_catalog.json`:
```json
{
  "name": "Quality Criteria Catalog",
  "source": "HTSM (James Bach)",
  "category": "quality",
  "when_to_use": "Ask what 'good enough to ship' means for a specific feature, beyond 'it does not crash'.",
  "letters": [
    {"letter": "Capability", "description": "Does it do the job it exists for?"},
    {"letter": "Reliability", "description": "Does it hold up under load, interruption, and failure?"},
    {"letter": "Usability", "description": "Can the intended users operate it effectively?"},
    {"letter": "Performance", "description": "Is it fast and responsive enough?"},
    {"letter": "Security", "description": "Does it protect data and resist misuse?"},
    {"letter": "Compatibility", "description": "Does it work across platforms, browsers, devices?"},
    {"letter": "Maintainability", "description": "Can it be understood, changed, and tested easily?"},
    {"letter": "Accessibility", "description": "Can people with disabilities use it?"}
  ],
  "example": "For an import feature, the weightiest criteria are usually performance, reliability, and data integrity."
}
```

`knowledge/heuristics/bug_heuristics.json`:
```json
{
  "name": "Bug Heuristics",
  "source": "community (RST tradition)",
  "category": "bug discovery",
  "when_to_use": "Generate bug ideas around common failure modes while exploring a feature.",
  "letters": [
    {"letter": "Empty", "description": "What happens with no data, empty fields, or zero results?"},
    {"letter": "Null", "description": "What happens with missing/None values where data is expected?"},
    {"letter": "Zero", "description": "What happens with zero, division by zero, or zero-length input?"},
    {"letter": "Repeat", "description": "What happens when the same operation is done twice?"},
    {"letter": "Boundary", "description": "What happens at the edges of ranges and limits?"},
    {"letter": "Concurrency", "description": "What happens when multiple things happen at once?"},
    {"letter": "Single", "description": "What happens with a single element or single user?"},
    {"letter": "Wrong type", "description": "What happens when input is of the wrong type or format?"},
    {"letter": "Unauthorized", "description": "What happens when access is attempted without permission?"}
  ],
  "example": "Test resubmitting a form after a session expires, or importing an empty CSV file."
}
```

`knowledge/heuristics/test_tours.json`:
```json
{
  "name": "Test Tours",
  "source": "Elisabeth Hendrickson",
  "category": "exploratory",
  "when_to_use": "Explore an application's territory systematically during exploratory testing.",
  "letters": [
    {"letter": "Guidebook", "description": "Follow the documented user path as the company intends it."},
    {"letter": "Money", "description": "Test the parts that generate revenue or handle payments."},
    {"letter": "Landmark", "description": "Head straight for the famous, central, most-used functions."},
    {"letter": "Intellectual", "description": "Stress the complex logic that exercises the developers' minds."},
    {"letter": "Back Alley", "description": "Use the application in ways it was not necessarily designed for."},
    {"letter": "Foreign", "description": "Explore with unexpected data, locales, or user types."},
    {"letter": "Adversarial", "description": "Attack the application's handling of hostile or malicious input."}
  ],
  "example": "Run the Back Alley tour on an admin panel to find undocumented paths and unhandled states."
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_heuristics_data.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add knowledge/heuristics/ tests/test_heuristics_data.py
git commit -m "feat: add test heuristic knowledge entries (SFDPOT, FEW HICCUPPS, RCRCRC, and more)"
```

---

### Task 4: Testcase generation logic

**Files:**
- Create: `server/generators.py`
- Create: `tests/test_generators.py`

**Interfaces:**
- Consumes: nothing (pure logic on given inputs).
- Produces:
  - `generate_boundary_value_analysis(spec: dict) -> list[dict]` — for `{"field": str, "min": int, "max": int, "type": "int"}`.
  - `generate_equivalence_partitioning(spec: dict) -> list[dict]` — for `{"field": str, "valid": list[str|int], "invalid": list[str|int]}`.
  - `generate_pairwise(values: dict[str, list]) -> list[dict[str, str]]` — all-pairs subset.
  - Each generated testcase is a dict `{"id": str, "input": ..., "expected": str}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_generators.py
import itertools

from server.generators import generate_boundary_value_analysis, generate_equivalence_partitioning, generate_pairwise


def test_bva_covers_boundaries():
    spec = {"field": "age", "min": 0, "max": 150}
    cases = generate_boundary_value_analysis(spec)
    values = {c["input"]["age"] for c in cases}
    assert {-1, 0, 1, 149, 150, 151}.issubset(values)


def test_bva_includes_valid_and_invalid_expected():
    spec = {"field": "age", "min": 0, "max": 150}
    cases = generate_boundary_value_analysis(spec)
    for c in cases:
        assert c["id"].startswith("BVA-")
        assert "expected" in c


def test_ep_covers_partitions():
    spec = {
        "field": "email",
        "valid": ["a@b.com"],
        "invalid": ["", "not-an-email"],
    }
    cases = generate_equivalence_partitioning(spec)
    assert len(cases) == 3
    inputs = [c["input"]["email"] for c in cases]
    assert set(inputs) == {"a@b.com", "", "not-an-email"}


def test_pairwise_covers_all_pairs():
    values = {"browser": ["c", "f", "s"], "os": ["lin", "win", "mac"], "screen": ["small", "large"]}
    rows = generate_pairwise(values)
    covered_pairs = set()
    for row in rows:
        for a, b in itertools.combinations(row.items(), 2):
            covered_pairs.add(frozenset([a, b]))
    expected_pairs = set()
    for (ka, va), (kb, vb) in itertools.combinations(values.items(), 2):
        for x in va:
            for y in vb:
                expected_pairs.add(frozenset([((ka, x)), ((kb, y))]))
    assert covered_pairs >= expected_pairs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_generators.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server.generators'`.

- [ ] **Step 3: Implement the generators**

`server/generators.py`:
```python
"""Pure testcase generation logic for classic techniques."""
from __future__ import annotations

import itertools
from typing import Any


def generate_boundary_value_analysis(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Boundary Value Analysis for an int range. spec: {field, min, max}."""
    field = spec["field"]
    lo, hi = int(spec["min"]), int(spec["max"])
    boundaries = [lo - 1, lo, lo + 1, hi - 1, hi, hi + 1]
    cases = []
    for i, value in enumerate(sorted(set(boundaries))):
        valid = lo <= value <= hi
        expected = "valid (accepted)" if valid else "invalid (rejected)"
        cases.append({"id": f"BVA-{i + 1}", "input": {field: value}, "expected": expected})
    return cases


def generate_equivalence_partitioning(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Equivalence Partitioning from explicit valid/invalid lists. spec: {field, valid, invalid}."""
    field = spec["field"]
    cases = []
    for i, value in enumerate(spec["valid"]):
        cases.append({"id": f"EP-valid-{i + 1}", "input": {field: value}, "expected": "valid (accepted)"})
    for i, value in enumerate(spec["invalid"]):
        cases.append({"id": f"EP-invalid-{i + 1}", "input": {field: value}, "expected": "invalid (rejected)"})
    return cases


def generate_pairwise(values: dict[str, list]) -> list[dict[str, str]]:
    """Greedy all-pairs covering set. values: {param: [values]} -> rows of {param: value}."""
    params = list(values)
    rows: list[dict[str, str]] = []
    covered: set[frozenset] = set()
    possible = []
    for combo in itertools.product(*[values[p] for p in params]):
        possible.append(dict(zip(params, combo)))
    for row in possible:
        row_pairs = {frozenset([(k, v) for k, v in row.items() if k in (a, b)]) for a, b in itertools.combinations(params, 2)}
        new_pairs = row_pairs - covered
        if new_pairs or not rows:
            rows.append(row)
            covered |= new_pairs
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_generators.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add server/generators.py tests/test_generators.py
git commit -m "feat: add testcase generation logic (BVA, EP, pairwise)"
```

---

### Task 5: Advice and checklist logic

**Files:**
- Create: `server/advisor.py`
- Create: `tests/test_advisor.py`

**Interfaces:**
- Consumes: `KnowledgeBase` (Task 1).
- Produces:
  - `advise(kb: KnowledgeBase, text: str) -> dict` — returns `{"techniques": [...names], "heuristics": [...names], "reasoning": str}`.
  - `checklist(kb: KnowledgeBase, context: str) -> dict` — returns `{"heuristic": name, "items": [str]}` used to build a checklist; or `{"heuristic": None, "items": []}` when no heuristics match.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_advisor.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_advisor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server.advisor'`.

- [ ] **Step 3: Implement advisor logic**

`server/advisor.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_advisor.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add server/advisor.py tests/test_advisor.py
git commit -m "feat: add advice and checklist logic"
```

---

### Task 6: FastMCP server wiring the tools

**Files:**
- Create: `server/testassist_mcp_server.py`
- Create: `tests/test_mcp_tools.py`

**Interfaces:**
- Consumes: `KnowledgeBase`, `generate_boundary_value_analysis` / `generate_equivalence_partitioning` / `generate_pairwise`, `advise`, `checklist`.
- Produces: a runnable stdio FastMCP server named `"testassist-mcp"` exposing 5 tools. Knowledge dir resolved from env `TESTASSIST_KNOWLEDGE_DIR` or default `knowledge/` relative to the repo root (two levels up from this file).

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_mcp_tools.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_mcp_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server.testassist_mcp_server'`.

- [ ] **Step 3: Implement the server**

`server/testassist_mcp_server.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_mcp_tools.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Smoke-test the stdio server tool listing**

Note: MCP stdio requires an `initialize` handshake before `tools/list`; a bare `tools/list` fails with `-32602 Invalid request parameters`. Send the handshake then the listing:

```bash
{ printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'; printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'; printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'; } | timeout 15 /root/testassist-mcp/.venv/bin/python /root/testassist-mcp/server/testassist_mcp_server.py
```

Expected: a JSON response whose `result.tools` array contains 5 tools (catalog_techniques, catalog_heuristics, generate_test_cases, advise_technique, checklist_for).

- [ ] **Step 6: Commit**

```bash
git add server/testassist_mcp_server.py tests/test_mcp_tools.py
git commit -m "feat: add FastMCP server exposing five test-knowledge tools"
```

---

### Task 7: Harvest script + README + full verification

**Files:**
- Create: `scripts/harvest.py`
- Create: `README.md`
- Modify: none.

**Interfaces:**
- Consumes: `KnowledgeBase` from Task 1.
- Produces: a runnable `scripts/harvest.py` that validates the knowledge base and regenerates an index summary (printed to stdout). CLI: `python scripts/harvest.py` (exit 0 on success, non-zero on invalid knowledge base).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_harvest.py
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "harvest.py"


def test_harvest_script_exists_and_is_loadable():
    assert SCRIPTS.is_file()
    spec = importlib.util.spec_from_file_location("harvest", SCRIPTS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert module


def test_harvest_module_has_main():
    spec = importlib.util.spec_from_file_location("harvest", SCRIPTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "main")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_harvest.py -v`
Expected: FAIL — `scripts/harvest.py` does not exist.

- [ ] **Step 3: Implement the harvest script**

`scripts/harvest.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest tests/test_harvest.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Write README**

`README.md`:
```markdown
# Test Assistant MCP Server

A knowledge/tools MCP server for OpenCode that exposes classic test techniques and test heuristics as tools, backed by a local, self-contained knowledge base.

## Tools

- `catalog_techniques()` — list all classic techniques (BVA, equivalence partitioning, decision table, pairwise, state transition, use case, error guessing).
- `catalog_heuristics()` — list all heuristic lists (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours).
- `generate_test_cases(technique, inputs)` — generate concrete testcases for supported techniques (only testcases; the agent does the rest).
- `advise_technique(description)` — keyword-based recommendation of techniques/heuristics for a described context.
- `checklist_for(context)` — produce a recommended test checklist (e.g. RCRCRC for regression).

## Setup

```bash
/usr/bin/python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run (stdio)

```bash
.venv/bin/python server/testassist_mcp_server.py
```

## Register in OpenCode

Add to `~/.config/opencode/opencode.json` under `mcp`:

```json
"testassist": {
  "type": "local",
  "command": ["/root/testassist-mcp/.venv/bin/python", "/root/testassist-mcp/server/testassist_mcp_server.py"],
  "enabled": true
}
```

## Knowledge base

Knowledge lives in `knowledge/` as one JSON file per technique/heuristic. Add a file to extend the server without code changes. Validate with:

```bash
.venv/bin/python scripts/harvest.py
```

## Test

```bash
.venv/bin/python -m pytest
```
```

- [ ] **Step 6: Run full verification suite**

Run: `/root/testassist-mcp/.venv/bin/python -m pytest -q`
Expected: ALL passing. Then run the harvest script:
Run: `cd /root/testassist-mcp && .venv/bin/python scripts/harvest.py`
Expected: exit 0 and prints all technique/heuristic names.

- [ ] **Step 7: Commit**

```bash
git add scripts/harvest.py tests/test_harvest.py README.md
git commit -m "docs: add README and harvest validation script; full test pass"
```

---

## Self-Review

**Spec coverage:**
- Knowledge base (techniques + heuristics, incl. SFDPOT/FEW HICCUPPS/RCRCRC) → Tasks 2, 3 ✓
- 5 tools → Task 6 ✓
- `generate_test_cases` returns only testcases → Task 6 ✓
- Advice/checklist → Task 5 ✓
- Harvest script → Task 7 ✓
- Self-contained after one-time harvest → all knowledge bundled as JSON ✓
- Error handling (unknown name clear message) → `KnowledgeBase.get_*` raises `KeyError` with available lists; server raises `ValueError` with supported list ✓
- Verification/tests → pytest suite + stdio smoke test ✓
- Registration (opencode.json) → documented in README; final manual step below ✓

**Placeholder scan:** No TBD/TODO/`Similar to Task N`; all code inline. ✓

**Type consistency:** `generate_boundary_value_analysis`/`generate_equivalence_partitioning`/`generate_pairwise` names and signatures match between Task 4 and Task 6. `advise`/`checklist` match between Task 5 and Task 6. `KnowledgeBase` API consistent across all tasks. ✓

## Post-plan manual steps (not tracks in tasks)

After the plan is implemented, register the server in `/root/.config/opencode/opencode.json` under `mcp` with the `testassist` entry (exact JSON shown in README Task 7), then restart the opencode servers for MCP to load:
```bash
systemctl restart opencode-serve-4096 opencode-web-4098
```
