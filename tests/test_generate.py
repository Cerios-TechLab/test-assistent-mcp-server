"""Tests for the property-based generate module."""
import pytest
from server.generate import (
    generate_boundary_cases,
    generate_random,
    generate_with_property,
)


class TestGenerateBoundaryCases:
    def test_int_boundaries(self):
        result = generate_boundary_cases({
            "field": "age",
            "type": "integer",
            "constraints": {"min": 0, "max": 150},
        })
        assert len(result) > 0
        values = {c["input"]["age"] for c in result}
        assert 0 in values
        assert 150 in values
        assert -1 in values
        assert 151 in values
        for c in result:
            assert c["edge"] is True
            assert c["expected"] in ("valid", "boundary")

    def test_float_boundaries(self):
        result = generate_boundary_cases({
            "field": "score",
            "type": "float",
            "constraints": {"min": 0.0, "max": 100.0},
        })
        assert len(result) > 0
        values = {c["input"]["score"] for c in result}
        assert 0.0 in values
        assert 100.0 in values

    def test_string_boundaries(self):
        result = generate_boundary_cases({
            "field": "name",
            "type": "string",
            "constraints": {"min_length": 1, "max_length": 100},
        })
        assert len(result) > 0
        values = {c["input"]["name"] for c in result}
        # Empty string excluded by min_length=1
        assert "" not in values
        assert "a" in values

    def test_date_boundaries(self):
        result = generate_boundary_cases({
            "field": "created",
            "type": "date",
            "constraints": {},
        })
        assert len(result) > 0
        # Should include 1970-01-01
        values = {c["input"]["created"] for c in result}
        assert "1970-01-01" in values


class TestGenerateWithProperty:
    def test_int_property(self):
        result = generate_with_property({
            "field": "age",
            "type": "integer",
            "constraints": {"min": 0, "max": 150},
            "count": 5,
            "include_invalid": False,
        })
        assert len(result) >= 5
        for c in result:
            assert "input" in c
            assert "age" in c["input"]
            assert c["expected"] in ("valid", "boundary")

    def test_with_seed(self):
        r1 = generate_with_property({
            "field": "x",
            "type": "integer",
            "constraints": {"min": -100, "max": 100},
            "count": 5,
            "seed": "test123",
        })
        r2 = generate_with_property({
            "field": "x",
            "type": "integer",
            "constraints": {"min": -100, "max": 100},
            "count": 5,
            "seed": "test123",
        })
        assert r1 == r2

    def test_different_seeds(self):
        r1 = generate_with_property({
            "field": "x",
            "type": "integer",
            "constraints": {"min": -1000, "max": 1000},
            "count": 20,
            "seed": "aaa",
        })
        r2 = generate_with_property({
            "field": "x",
            "type": "integer",
            "constraints": {"min": -1000, "max": 1000},
            "count": 20,
            "seed": "bbb",
        })
        # With enough count, random values will differ
        vals1 = [c["input"]["x"] for c in r1]
        vals2 = [c["input"]["x"] for c in r2]
        assert vals1 != vals2


class TestGenerateRandom:
    def test_multi_field(self):
        result = generate_random({
            "fields": [
                {"field": "name", "type": "string", "constraints": {"min_length": 1, "max_length": 10}},
                {"field": "age", "type": "integer", "constraints": {"min": 0, "max": 120}},
            ],
            "count": 3,
            "seed": 42,
        })
        assert len(result) == 3
        for c in result:
            assert "name" in c["input"]
            assert "age" in c["input"]
            assert c["expected"] == "valid"

    def test_reproducible(self):
        spec = {
            "fields": [{"field": "v", "type": "integer", "constraints": {}}],
            "count": 5,
            "seed": "hello",
        }
        assert generate_random(spec) == generate_random(spec)

    def test_boolean_field(self):
        result = generate_random({
            "fields": [{"field": "active", "type": "boolean"}],
            "count": 20,
        })
        values = {c["input"]["active"] for c in result}
        assert True in values
        assert False in values

    def test_date_field(self):
        result = generate_random({
            "fields": [{"field": "d", "type": "date", "constraints": {"min": "2024-01-01", "max": "2024-12-31"}}],
            "count": 5,
        })
        for c in result:
            assert c["input"]["d"].startswith("2024-")
