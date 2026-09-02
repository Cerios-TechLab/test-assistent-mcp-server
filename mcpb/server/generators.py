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
