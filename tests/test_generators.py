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
