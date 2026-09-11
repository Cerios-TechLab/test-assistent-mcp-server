import itertools

from server.generators import (
    generate_boundary_value_analysis,
    generate_decision_table,
    generate_equivalence_partitioning,
    generate_error_guessing,
    generate_pairwise,
    generate_state_transition,
    generate_use_case,
)


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


def test_decision_table_one_case_per_rule():
    spec = {
        "conditions": ["pays", "member"],
        "actions": ["ship", "charge", "waive"],
        "rules": [
            {"when": {"pays": "yes", "member": "no"}, "then": ["ship", "charge"]},
            {"when": {"pays": "yes", "member": "yes"}, "then": ["ship"]},
        ],
    }
    cases = generate_decision_table(spec)
    assert len(cases) == 2
    assert all(c["id"].startswith("DT-") for c in cases)
    assert cases[0]["input"] == {"pays": "yes", "member": "no"}
    assert cases[0]["expected"] == "ship, charge"


def test_state_transition_one_case_per_transition():
    spec = {
        "states": ["idle", "active"],
        "events": ["start", "stop"],
        "transitions": [
            {"state": "idle", "event": "start", "next": "active"},
            {"state": "active", "event": "stop", "next": "idle"},
        ],
    }
    cases = generate_state_transition(spec)
    assert len(cases) == 2
    assert all(c["id"].startswith("ST-") for c in cases)
    assert cases[0]["input"] == {"state": "idle", "event": "start"}
    assert cases[0]["expected"] == "active"


def test_use_case_one_case_per_step_and_fallback_expected():
    cases = generate_use_case({
        "name": "login",
        "steps": ["open page", "submit credentials"],
        "expected": ["page opens"],
    })
    assert len(cases) == 2
    assert all(c["id"].startswith("UC-") for c in cases)
    assert cases[0]["expected"] == "page opens"
    assert cases[1]["expected"]  # fallback not empty


def test_error_guessing_one_negative_case_per_pitfall():
    cases = generate_error_guessing({
        "field": "email",
        "input": "a@b.c",
        "pitfalls": ["", "x", "<script>"],
    })
    assert len(cases) == 3
    assert all(c["id"].startswith("EG-") for c in cases)
    for c in cases:
        assert "email" in c["input"]
    assert cases[0]["expected"] != cases[1]["expected"]  # elke valkuil heeft eigen expected (payload = pitfall)
