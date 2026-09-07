"""Tests for the FO -> BDD demo pipeline (parser + builder)."""

from __future__ import annotations

FO = """FO-FR014 — Leeftijdscontrole bij registratie
Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.
Bij leeftijd < 18 wordt registratie geweigerd met de melding 'Je moet 18 jaar of ouder zijn.'
Bij leeftijd >= 18 wordt het account aangemaakt.
Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout."""


def test_parse_finds_field_and_range():
    from demo.fo_parser import parse_fo

    specs = parse_fo(FO)
    assert specs["fields"], "expected at least one field"
    f = specs["fields"][0]
    assert f["name"] == "leeftijd"
    assert f["type"] == "integer"
    assert f["min"] == 0 and f["max"] == 120
    assert any(r["expected"] == "rejected" for r in f["rules"])
    assert any(r["expected"] == "validation error" for r in f["rules"])


def test_bdd_contains_gherkin_and_key_values():
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import build_bdd

    specs = parse_fo(FO)
    gherkin, used = build_bdd(FO, specs)

    assert "Functionaliteit:" in gherkin
    assert "Gegeven" in gherkin and "Als" in gherkin and "Dan" in gherkin
    # boundary + rule values from the example
    for val in ("17", "18", "0", "120", "121"):
        assert val in gherkin, f"expected value {val} in scenarios"
    assert "generate_boundary_value_analysis" in used


def test_non_numeric_rule_scenario():
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import build_bdd

    specs = parse_fo(FO)
    gherkin, _ = build_bdd(FO, specs)
    assert "validatiefout" in gherkin
