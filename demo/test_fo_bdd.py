"""Tests for the FO -> BDD demo pipeline (parser + real MCP-server consultation)."""

from __future__ import annotations

FO = """FO-FR014 — Leeftijdscontrole bij registratie
Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.
Bij leeftijd < 18 wordt registratie geweigerd met de melding 'Je moet 18 jaar of ouder zijn.'
Bij leeftijd >= 18 wordt het account aangemaakt.
Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout.
Je mag niet jonger zijn dan 0 jaar.
Geen account aanmaken als je een alcoholist bent."""


def test_parse_captures_extra_constraints():
    from demo.fo_parser import parse_fo

    specs = parse_fo(FO)
    f = specs["fields"][0]
    assert f["name"] == "leeftijd"
    assert f["min"] == 0 and f["max"] == 120
    # the "< 18" reject rule
    assert any(r["expected"] == "rejected" and not r.get("qualitative") for r in f["rules"])
    # the qualitative alcoholist rule is captured from the extra FO line
    assert any(r.get("qualitative") for r in f["rules"])
    # "niet jonger dan 0" reinforced the min (still 0)
    assert f["min"] == 0


def test_bdd_uses_mcp_server_output():
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import format_bdd
    from demo.mcp_client import consult_server

    specs = parse_fo(FO)
    advice, bva_raw, heuristics, used = consult_server(FO, specs)
    assert "generate_test_cases" in used
    assert "catalog_heuristics" in used
    assert bva_raw and bva_raw.get("testcases")
    assert heuristics and heuristics.get("heuristics")

    gherkin = format_bdd(specs, bva_raw)
    assert "Functionaliteit:" in gherkin
    assert "Gegeven" in gherkin and "Als" in gherkin and "Dan" in gherkin
    for val in ("17", "18", "0", "120", "121"):
        assert val in gherkin, f"expected value {val} in scenarios"
    assert "alcoholist" in gherkin


def test_charter_generated():
    from demo.fo_parser import parse_fo
    from demo.charter_builder import build_charter
    from demo.mcp_client import consult_server

    specs = parse_fo(FO)
    _, _, heuristics, used = consult_server(FO, specs)
    md = build_charter(FO, specs, heuristics.get("heuristics"), used, technique="SFDPOT")
    assert "Exploratory Test Charter" in md
    assert "SFDPOT" in md
    assert "FEW HICCUPPS" in md
    assert "BVA-grenswaarden" in md
    assert "alcoholist" in md or "kwalitatieve" in md.lower()
