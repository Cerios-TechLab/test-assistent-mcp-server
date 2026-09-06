"""Property-based test data generation engine."""
from __future__ import annotations

import hashlib
import math
import random
import string
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Seedable RNG wrapper
# ---------------------------------------------------------------------------

class _RNG:
    """Deterministic RNG seeded from a string or integer."""

    def __init__(self, seed: int | str | None = None) -> None:
        if seed is None:
            self._rng = random.Random()
        elif isinstance(seed, str):
            h = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % (2**64)
            self._rng = random.Random(h)
        else:
            self._rng = random.Random(seed)

    def randint(self, lo: int, hi: int) -> int:
        return self._rng.randint(lo, hi)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: list) -> Any:
        return self._rng.choice(seq)

    def sample(self, seq: list, k: int) -> list:
        return self._rng.sample(seq, min(k, len(seq)))

    def uniform(self, lo: float, hi: float) -> float:
        return self._rng.uniform(lo, hi)


# ---------------------------------------------------------------------------
# Boundary generators per type
# ---------------------------------------------------------------------------

_INT_BOUNDARIES = [
    -2**31, -2**31 + 1, -1, 0, 1,
    2**31 - 2, 2**31 - 1, 2**31,
]

_FLOAT_BOUNDARIES = [
    -1e308, -1.0, -1e-10, 0.0, 1e-10, 1.0, 1e308,
    float("-inf"), float("inf"),
]

_STRING_EDGE_CASES = [
    "", " ", "\t", "\n", "\r\n",
    "a", "A",
    "0",
    "!" * 256,
    "🔥",
    "café",
    "<script>alert(1)</script>",
    "'; DROP TABLE users; --",
    "\x00",
    "日本語テスト",
]


def _int_boundaries(constraints: dict) -> list[int]:
    lo = constraints.get("min", -2**31)
    hi = constraints.get("max", 2**31 - 1)
    extras = [lo - 1, lo, lo + 1, hi - 1, hi, hi + 1, 0, -1, 1]
    if lo > 0:
        extras.append(lo)
    if hi < 0:
        extras.append(hi)
    return sorted(set(int(v) for v in extras if isinstance(v, (int, float)) and math.isfinite(v)))


def _float_boundaries(constraints: dict) -> list[float]:
    lo = constraints.get("min", -1e308)
    hi = constraints.get("max", 1e308)
    extras = [lo - 1, lo, lo + 1e-10, hi - 1e-10, hi, hi + 1, 0.0, -0.0, 1e-10, -1e-10]
    return sorted(set(float(v) for v in extras if math.isfinite(v)))


def _string_boundaries(constraints: dict) -> list[str]:
    max_len = constraints.get("max_length", 255)
    min_len = constraints.get("min_length", 0)
    result = [s for s in _STRING_EDGE_CASES if min_len <= len(s) <= max_len]
    if not result:
        result = ["", "a"]
    return result


def _date_boundaries(constraints: dict) -> list[str]:
    today = date.today()
    boundaries = [
        "1970-01-01",
        "1999-12-31",
        "2000-01-01",
        "2024-12-31",
        today.isoformat(),
        (today - timedelta(days=1)).isoformat(),
        (today + timedelta(days=1)).isoformat(),
    ]
    if "min" in constraints:
        boundaries.append(constraints["min"])
    if "max" in constraints:
        boundaries.append(constraints["max"])
    return sorted(set(boundaries))


# ---------------------------------------------------------------------------
# Constraint satisfaction check
# ---------------------------------------------------------------------------

def _satisfies(value: Any, field_type: str, constraints: dict) -> bool:
    """Check if a generated value satisfies all constraints."""
    if field_type == "integer":
        v = int(value)
        if "min" in constraints and v < constraints["min"]:
            return False
        if "max" in constraints and v > constraints["max"]:
            return False
    elif field_type == "float":
        v = float(value)
        if "min" in constraints and v < constraints["min"]:
            return False
        if "max" in constraints and v > constraints["max"]:
            return False
    elif field_type == "string":
        v = str(value)
        if "min_length" in constraints and len(v) < constraints["min_length"]:
            return False
        if "max_length" in constraints and len(v) > constraints["max_length"]:
            return False
        if "pattern" in constraints:
            import re
            if not re.search(constraints["pattern"], v):
                return False
    elif field_type == "date":
        v = str(value)
        try:
            d = date.fromisoformat(v)
        except ValueError:
            return False
        if "min" in constraints and v < constraints["min"]:
            return False
        if "max" in constraints and v > constraints["max"]:
            return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_boundary_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate boundary value test cases for a field.

    spec: {field, type, constraints: {min, max, ...}}
    Returns: [{input: {field: value}, expected: "valid"|"boundary", edge: true}]
    """
    field = spec["field"]
    field_type = spec.get("type", "integer")
    constraints = spec.get("constraints", {})

    if field_type == "integer":
        candidates = _int_boundaries(constraints)
    elif field_type == "float":
        candidates = _float_boundaries(constraints)
    elif field_type == "string":
        candidates = _string_boundaries(constraints)
    elif field_type == "date":
        candidates = _date_boundaries(constraints)
    else:
        candidates = []

    cases = []
    for i, value in enumerate(candidates):
        ok = _satisfies(value, field_type, constraints)
        cases.append({
            "id": f"BV-{i + 1}",
            "input": {field: value},
            "expected": "valid" if ok else "boundary",
            "edge": True,
        })
    return cases


def generate_with_property(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate test cases from a property definition.

    spec: {
        field, type,
        constraints: {min, max, min_length, max_length, pattern, ...},
        count: N,
        seed: optional,
        include_invalid: True  # also generate constraint-violating values
    }
    Returns: [{input: {field: value}, expected: "valid"|"invalid", source: "boundary"|"random"}]
    """
    field = spec["field"]
    field_type = spec.get("type", "integer")
    constraints = spec.get("constraints", {})
    count = spec.get("count", 10)
    seed = spec.get("seed")
    include_invalid = spec.get("include_invalid", True)

    rng = _RNG(seed)
    cases: list[dict[str, Any]] = []

    # Phase 1: boundary cases
    boundary_spec = {"field": field, "type": field_type, "constraints": constraints}
    boundary_cases = generate_boundary_cases(boundary_spec)
    cases.extend(boundary_cases)

    # Phase 2: random valid values
    needed = max(0, count - len(cases))
    attempts = 0
    max_attempts = needed * 20
    while len(cases) < count + (len(boundary_cases) if include_invalid else 0) and attempts < max_attempts:
        attempts += 1
        value = _random_value(field_type, constraints, rng)
        ok = _satisfies(value, field_type, constraints)
        if ok or include_invalid:
            cases.append({
                "id": f"RNG-{len(cases) + 1}",
                "input": {field: value},
                "expected": "valid" if ok else "invalid",
                "source": "random",
            })

    return cases[:count + (10 if include_invalid else 0)]


def generate_random(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Constrained random data generation.

    spec: {fields: [{field, type, constraints}], count: N, seed: optional}
    Returns: [{input: {field: value, ...}, expected: "valid"}]
    """
    fields = spec.get("fields", [])
    count = spec.get("count", 10)
    seed = spec.get("seed")
    rng = _RNG(seed)

    cases = []
    for i in range(count):
        row = {}
        for f in fields:
            row[f["field"]] = _random_value(f.get("type", "string"), f.get("constraints", {}), rng)
        cases.append({
            "id": f"RND-{i + 1}",
            "input": row,
            "expected": "valid",
        })
    return cases


def _random_value(field_type: str, constraints: dict, rng: _RNG) -> Any:
    """Generate a single random value of the given type."""
    if field_type == "integer":
        lo = constraints.get("min", -1000)
        hi = constraints.get("max", 1000)
        return rng.randint(int(lo), int(hi))
    elif field_type == "float":
        lo = constraints.get("min", -1000.0)
        hi = constraints.get("max", 1000.0)
        return round(rng.uniform(float(lo), float(hi)), 6)
    elif field_type == "string":
        max_len = constraints.get("max_length", 50)
        min_len = constraints.get("min_length", 0)
        length = rng.randint(min_len, max(min_len, max_len))
        charset = string.ascii_letters + string.digits
        return "".join(rng.choice(charset) for _ in range(length))
    elif field_type == "boolean":
        return rng.choice([True, False])
    elif field_type == "date":
        lo = constraints.get("min", "2000-01-01")
        hi = constraints.get("max", "2030-12-31")
        d_lo = date.fromisoformat(lo)
        d_hi = date.fromisoformat(hi)
        delta = (d_hi - d_lo).days
        if delta <= 0:
            return d_lo.isoformat()
        d = d_lo + timedelta(days=rng.randint(0, delta))
        return d.isoformat()
    else:
        return "unknown"
