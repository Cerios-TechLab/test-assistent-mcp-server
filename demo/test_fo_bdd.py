"""Tests for the FO demo (parser heuristics + OpenCode client smoke)."""

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
    assert any(r["expected"] == "rejected" and not r.get("qualitative") for r in f["rules"])
    assert any(r.get("qualitative") for r in f["rules"])


def test_opencode_client_smoke():
    """Requires /root/.opencode/bin/opencode and network to the model provider."""
    import shutil

    from demo.opencode_client import ask

    if not shutil.which("/root/.opencode/bin/opencode") and not __import__("os").path.exists(
        "/root/.opencode/bin/opencode"
    ):
        return  # skip silently if opencode is not installed
    r = ask("Reply with exactly: PONG", model="opencode/big-pickle",
            cwd="/root", title="fo-bdd-test", timeout=180)
    assert "PONG" in r["text"], f"unexpected text: {r['text']!r}"
    assert isinstance(r["tools"], list)
