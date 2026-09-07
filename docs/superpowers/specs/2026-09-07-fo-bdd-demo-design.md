# Design: FO → BDD demo-app

**Date:** 2026-09-07
**Status:** Approved ("Prima voor nu")

## Doel
Tijdens een live demo plakt de gebruiker een stuk Functionele Omschrijving (FO) in een
browser, klikt "Genereer", en ziet direct de BDD-scenario's (Gegeven/Als/Dan) verschijnen.
Er worden **geen** `.feature`-bestanden weggeschreven — alleen Gherkin-tekst in beeld, met
een kopieer-/downloadknop.

## Vorm
- **Streamlit web-app** (browser-UI, voor live demo).
- **Hergebruik van server-logica**: de app importeert de bestaande generator-functies uit
  de MCP-server (`server.generators.generate_boundary_value_analysis`,
  optioneel `server.advisor.advise`) en formatteert de uitvoer naar Gherkin. Er draait
  **geen** MCP-server tijdens de demo.

## Componenten (map `demo/`)
- `fo_parser.py` — heuristische regex-parser die uit FO-vrije tekst haalt: veldnaam, type
  (integer/string/date), bereik (`tussen X en Y`), drempels (`< N`, `>= N`,
  "niet-numeriek", "ontbrekend"). Geeft een lijst veld-specificaties terug.
- `bdd_builder.py` — roept `generate_boundary_value_analysis` aan per veld/bereik en zet de
  uitvoer om in Gherkin (`Functionaliteit:` / `Scenario:` / `Gegeven`/`Als`/`Dan`/`En`),
  aangevuld met regel-scenario's (`<18` geweigerd met melding, `>=18` akkoord,
  niet-numeriek → validatiefout). Geeft de Gherkin-string + gebruikte MCP-tools terug.
- `app.py` — Streamlit-UI: titel + uitleg, tekstvak **voor-ingevuld met het
  leeftijd-registratie FO-voorbeeld**, "Genereer"-knop, daarna getoonde geëxtraheerde
  veld-specs (transparantie), Gherkin in een code-block, downloadknop, en een regel
  "gebruikte MCP-tools".
- `requirements.txt` — `streamlit`.
- `test_fo_bdd.py` — pytest op het leeftijd-voorbeeld (parser + builder).

## Dataflow
FO-tekst → `fo_parser` → specs → `bdd_builder` (server-generators) → Gherkin-string → UI.

## Bewust niet in scope
Echte NLP, wegschrijven naar `.feature`-bestanden, de draaiende MCP-server aanroepen via
MCP, meertaligheid buiten Nederlandse sleutelwoorden.

## Veiligheid voor de demo
Geen externe server nodig (logica lokaal geïmporteerd), voorbeeld-FO standaard ingevuld,
foutafhandeling als de parser niets vindt (vriendelijk bericht + handmatig veld toevoegen).
