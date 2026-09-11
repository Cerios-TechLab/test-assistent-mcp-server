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


def generate_decision_table(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Decision Table. spec: {conditions, actions, rules: [{when, then}]}."""
    cases = []
    for i, rule in enumerate(spec.get("rules", [])):
        cases.append({
            "id": f"DT-{i + 1}",
            "input": rule.get("when", {}),
            "expected": ", ".join(rule.get("then", [])),
        })
    return cases


def generate_state_transition(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """State Transition. spec: {states, events, transitions: [{state, event, next}]}."""
    cases = []
    for i, t in enumerate(spec.get("transitions", [])):
        cases.append({
            "id": f"ST-{i + 1}",
            "input": {"state": t.get("state"), "event": t.get("event")},
            "expected": t.get("next"),
        })
    return cases


def generate_use_case(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Use Case Testing. spec: {name, steps, expected (parallel)}."""
    steps = spec.get("steps", [])
    expected = spec.get("expected", [])
    cases = []
    for i, step in enumerate(steps):
        exp = expected[i] if i < len(expected) else "step completes successfully"
        cases.append({"id": f"UC-{i + 1}", "input": {"step": step}, "expected": exp})
    return cases


def generate_error_guessing(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Error Guessing. spec: {field, input, pitfalls}. One negative case per pitfall."""
    field = spec.get("field", "input")
    cases = []
    for i, pitfall in enumerate(spec.get("pitfalls", [])):
        cases.append({
            "id": f"EG-{i + 1}",
            "input": {field: pitfall},
            "expected": f"invalid (rejected) -- guessed: {pitfall}",
        })
    return cases
