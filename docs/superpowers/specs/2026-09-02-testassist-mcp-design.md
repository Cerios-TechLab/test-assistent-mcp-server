# Test Assistant MCP Server — Design

**Datum**: 2026-09-02
**Status**: goedgekeurd
**Locatie repo**: `/root/testassist-mcp`

## Doel

Een knowledge/tools MCP-server voor OpenCode die klassieke testtechnieken én testheuristieken als tools aanbiedt aan de agent. De server genereert of adviseert — hij genereert/uitvoert geen testbestanden in een repo (dat doet de agent zelf met de aangeleverde kennis).

De server is **self-contained** na een eenmalige harvest: kennis wordt verwerkt tot een eigen lokale kennisbank, daarna werkt alles zonder externe ophaal-afhankelijkheden.

## Scope

- **Kennis**: klassieke testtechnieken (BVA, equivalence partitioning, decision tables, pairwise, state transition, use case, error guessing, e.a.) én testheuristieken/mnemonics (op verzoek van de gebruiker: SFDPOT, FEW HICCUPPS, RCRCRC, plus quality criteria catalog, bug heuristics, test tours en enkele gangbare mnemonics).
- **Gebruik**: zowel testcase-generatie als catalogi/advies/checklists.
- **Stack**: Python + FastMCP (consistent met de bestaande `visio-mcp`-server).
- **Registratie**: eigen git-repo + lokale stdio-registratie in `/root/.config/opencode/opencode.json`.

## Architectuur

```
testassist-mcp/
├── server/
│   └── testassist_mcp_server.py      # FastMCP-server met 5 tools
├── knowledge/
│   ├── techniques/                   # JSON per klassieke techniek
│   ├── heuristics/                   # JSON per heuristiekenlijst
│   └── guides/                       # markdown voor langere uitleg
├── scripts/
│   └── harvest.py                    # eenmalig extern ophalen → normaliseren
├── pyproject.toml                    # deps: mcp
└── README.md
```

De kennis is **los van de code** opgeslagen (JSON per techniek/heuristiek, markdown voor langere uitleg). De server leest de kennisbank in en biedt de tools aan. Kennis uitbreiden = een JSON-bestand toevoegen, zonder servercode aan te passen.

### Kennisbank

- **`knowledge/techniques/`** — klassieke technieken, per techniek een JSON met:
  - `name`, `description`, `when_to_use`, `steps`, `example`
  - gepland: `boundary_value_analysis.json`, `equivalence_partitioning.json`, `decision_table.json`, `pairwise_testing.json`, `state_transition.json`, `use_case.json`, `error_guessing.json`, e.v.t. meer.
- **`knowledge/heuristics/`** — heuristieken/mnemonics, per lijst een JSON met:
  - `name`, `source`, `category`, `when_to_use`, `letters` (map letter → uitleg/vraag), `example`
  - gepland:
    - `sfdpot.json` (product-elementen): Structure, Function, Data, Platform, Operations, Time
    - `few_hiccupps.json` (oracle-heuristieken): Familiarity, Explainability, World, History, Image, Comparable products, Claims, User Desires, Product, Purpose, Statutes & Standards
    - `rcrcrc.json` (regressie): Recent, Core, Risky, Configuration sensitive, Repaired, Chronic
    - `quality_criteria_catalog.json`, `bug_heuristics.json`, `test_tours.json`, en een paar mnemonics (Goldilocks, I SLICED UP FUN, VADER/POISED).
- **`knowledge/guides/`** — markdown met langere uitleg waar nuttig.

### Tools (5)

1. **`catalog_techniques()`** — overzicht van alle technieken uit de kennisbank (naam, korte beschrijving, wanneer te gebruiken).
2. **`catalog_heuristics()`** — overzicht van alle heuristiekenlijsten (naam, bron, categorie, wanneer te gebruiken).
3. **`generate_test_cases(technique, inputs)`** — gestructureerde input → concrete testcases. Retourneert **alleen de testcases** (beschrijving, input, verwacht resultaat); de agent verwerkt ze zelf verder (tot testcode/uitvoering). Voorbeeld BVA-input: `{"field": "leeftijd", "min": 0, "max": 150, "type": "int"}` → boundary-testcases.
4. **`advise_technique(description)`** — beschrijf een functie/bug/context; trefwoord-analyse over de kennisbank → welke techniek en/of heuristiek het best pasten.
5. **`checklist_for(context)`** — genereert een aanbevolen test-checklist voor een doel/context (bv. "regressietest na bugfix" → RCRCRC-checklist; "nieuwe API" → API-technieken/heuristieken).

## Harvest (eenmalig)

`scripts/harvest.py` haalt erkende open/public-domain bronnen op en normaliseert ze naar de JSON-kennisbank. De relevante bronnen zijn in kaart gebracht tijdens het brainstormsessie:
- HTSM (Heuristic Test Strategy Model, James Bach / Satisfice) — voor product elements (SFDPOT) en quality criteria.
- DevelopSense-blogs (Michael Bolton) — FEW HICCUPPS (oracle-heuristieken).
- Bronnen voor RCRCRC (regressie-prioriteringsheuristiek).
- Public-domain/testheuristiek-cheatsheets (Test Heuristics Cheat Sheet e.a.) voor quality criteria, bug heuristics en mnemonics.

**Belangrijk**: de kennis wordt **verwerkt tot een eigen kennisbank** (eigen formulering, gestructureerd JSON) — geen letterlijke kopie van auteursrechtelijk materiaal. Na de harvest is de server fully self-contained.

## Registratie

Als lokale stdio-server in `/root/.config/opencode/opencode.json`, op dezelfde manier als `visio-mcp`:
```json
"testassist": {
  "type": "local",
  "command": ["/root/testassist-mcp/.venv/bin/python", "/root/testassist-mcp/server/testassist_mcp_server.py"],
  "enabled": true
}
```

## Dataflow

1. Agent roept een MCP-tool aan.
2. Server leest het relevante JSON uit de kennisbank.
3. Server retourneert een gestructureerd antwoord.
4. Agent verwerkt de kennis verder (testcode genereren, uitvoeren, rapporteren).

## Foutafhandeling

- Onbekende techniek of heuristiek naam → duidelijke foutmelding plus lijst van beschikbare namen.
- Kennisbank-JSON's worden bij serverstart gevalideerd; een kapot JSON-bestand → duidelijke fout ipv. stille mislukking.

## Testen & verificatie

- **Unit-tests** (`pytest`): elke tool met representatieve input; controle op welgevormde uitvoer.
- **Kennisbank-validatie**: schema-check per JSON, geen duplicaten/typo's in techniek/heuristiek-namen.
- **Kwaliteitspoort**: `python -m pytest` in de repo; bestand-formatter/bootstrap via `pyproject.toml`.
- De MCP-server wordt lokaal gestart met een stdio-smoke-test (tool-listing) als verificatie.

## Niet in scope (YAGNI)

- Actieve testbestand-generatie of -uitvoering in een repo.
- Live/real-time extern ophalen bij elke aanvraag (alleen eenmalige harvest).
- Externe kennis-API's of copyright-gevoelige brochures letterlijk inlezen.
