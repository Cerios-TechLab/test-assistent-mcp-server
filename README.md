# Test Assistant MCP Server

Een MCP-server (Model Context Protocol) voor OpenCode die klassieke testtechnieken en testheuristieken als tools beschikbaar stelt aan agenten, ondersteund door een lokale, zelfstandige kennisbasis.

De server is tool-based: hij **adviseert en genereert** testcases, maar voert zelf geen tests uit. Het is de agent (bijv. OpenCode) die de keuzes maakt en de technieken toepast op het systeem dat wordt getest.

## Functionaliteit / Wat het doet

De server ontsluit twee soorten kennis:

- **Testtechnieken** (7): Boundary Value Analysis, Equivalence Partitioning, Decision Table, Pairwise Testing, State Transition, Use Case Testing, Error Guessing.
- **Testheuristieken** (6): SFDPOT, FEW HICCUPPS, RCRCRC, Quality Criteria Catalog, Bug Heuristics, Test Tours.

Een agent kan hieruit:

- technieken en heuristieken **catalogiseren**;
- **testcases genereren** voor de ondersteunde technieken (BVA, EP, pairwise);
- advies vragen over welke techniek/heuristiek past bij een omschreven context;
- een concrete **checklist** ontvangen (bijv. RCRCRC voor regressietesten).

Al deze kennis leeft als JSON in de map `knowledge/` en wordt gelezen door de server — uitbreiden kan zonder code te wijzigen.

## Tools

| Tool | Parameters | Beschrijving |
|---|---|---|
| `catalog_techniques` | — | Lijst alle klassieke testtechnieken op. |
| `catalog_heuristics` | — | Lijst alle testheuristieken op. |
| `generate_test_cases` | `technique` (str), `inputs` (dict) | Genereert concrete testcases voor BVA, Equivalence Partitioning en Pairwise Testing. Geeft alleen testcases terug; de agent doet de rest. |
| `advise_technique` | `description` (str) | Beveelt op basis van sleutelwoorden technieken en heuristieken aan voor een omschreven context. |
| `checklist_for` | `context` (str) | Levert een aanbevolen test-checklist op (items) voor een context, bijv. RCRCRC voor regressie. |

### Voorbeelden van gebruik

- `catalog_techniques()` → catalogus van alle 7 technieken.
- `catalog_heuristics()` → catalogus van alle 6 heuristieken.
- `generate_test_cases("Boundary Value Analysis", {"field": "age", "min": 0, "max": 150})` → BVA-testcases rond de grenzen `-1, 0, 1, 149, 150, 151`.
- `advise_technique("regression after a bug fix")` → beveelt o.a. RCRCRC aan.
- `checklist_for("regression")` → RCRCRC-checklist met items.

## Installatie

### Vereisten

- Python **3.11** (gebruik `/usr/bin/python3.11`, niet een ouder `python3`).
- venv-ondersteuning en `pip`.

### Via Smithery (aanbevolen)

```bash
npx -y smithery mcp add djsteavy/test-assistent-mcp-server
```

Dit installeert de server via de Smithery registry. De server draait lokaal als stdio-proces.

### Via GitHub clone

```bash
# 1. Kloon of ga naar de repo
git clone git@github.com:Cerios-TechLab/test-assistent-mcp-server.git
cd test-assistent-mcp-server

# 2. Maak een virtuele omgeving aan (Python 3.11)
/usr/bin/python3.11 -m venv .venv

# 3. Installeer het pakket (incl. dev-tools voor tests)
.venv/bin/pip install -e '.[dev]'
```

De enige runtime-afhankelijkheid is `mcp>=1.29.0,<2` (pinned wegens FastMCP API-wijziging in 2.x); `pytest` is een dev-afhankelijkheid.

### Smithery registry

De server is gepubliceerd op Smithery: https://smithery.ai/servers/djsteavy/test-assistent-mcp-server

Het MCPB-distributieformaat (in `mcpb/`) is bedoeld voor toekomstige Smithery CLI-ondersteuning.

## Werking

### Starten (stdio)

De server werkt over stdio en wordt één-op-één gestart per MCP-client:

```bash
.venv/bin/python server/testassist_mcp_server.py
```

Bij het starten:

1. Wordt de kennisbasis geladen vanuit `knowledge/` (of uit `TESTASSIST_KNOWLEDGE_DIR` als die omgevingsvariabele is gezet).
2. Worden de 5 tools geregistreerd op de FastMCP-server.
3. Wacht de server op JSON-RPC-berichten over stdin en antwoordt over stdout.

### Registeren in OpenCode

Voeg onder `mcp` in `~/.config/opencode/opencode.json` toe:

```json
"testassist": {
  "type": "local",
  "command": ["/root/testassist-mcp/.venv/bin/python", "/root/testassist-mcp/server/testassist_mcp_server.py"],
  "enabled": true
}
```

Nadat de opencode-servers opnieuw zijn gestart (bijv. `systemctl restart opencode-serve-4096 opencode-web-4098`), hebben OpenCode-agenten de tools tot hun beschikking.

### Manual verificatie van de server

Omdat MCP-stdio eerst een `initialize`-handshake vereist vóór `tools/list`, test je de tool-listing als volgt:

```bash
{ printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'; printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'; printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'; } | timeout 15 .venv/bin/python server/testassist_mcp_server.py
```

Je verwacht een JSON-antwoord waarvan `result.tools` 5 tools bevat (catalog_techniques, catalog_heuristics, generate_test_cases, advise_technique, checklist_for) met non-empty descriptions.

## Kennisbasis

Kennis leeft in `knowledge/` als JSON, één bestand per techniek of heuristiek:

```
knowledge/
├── techniques/    # boundary_value_analysis.json, equivalence_partitioning.json, decision_table.json, ...
└── heuristics/    # sfdpot.json, few_hiccupps.json, rcrcrc.json, ...
```

Elk bestand bevat gestructureerde velden. Techniekbestanden gebruiken `name`, `description`, `when_to_use`, `steps` en `example`; heuristiekbestanden gebruiken `name`, `source`, `category`, `when_to_use`, `letters` en `example`. Bij de heuristieken is `letters` een geordende lijst van `{"letter": ..., "description": ...}`-objecten, zodat mnemonics met herhaalde letters (zoals RCRCRC en FEW HICCUPPS) volledig behouden blijven.

**Uitbreiden:** voeg een nieuw JSON-bestand toe in de juiste map en de server biedt het automatisch aan — geen code-wijziging nodig.

**Valideren en samenstellen** kan met het harvest-script (print een index en is handig als sanity-check):

```bash
.venv/bin/python scripts/harvest.py
```

Dit eindigt met exit-code 0 bij een geldige kennisbasis en met een fout bij een ongeldige.

## Testen

```bash
.venv/bin/python -m pytest
```

## Projectstructuur

```
test-assistent-mcp-server/
├── server/
│   ├── knowledge_base.py          # laadt en ontsluit de JSON-kennisbasis
│   ├── generators.py             # pure testcase-generatie (BVA, EP, pairwise)
│   ├── advisor.py                # keyword-gebaseerde advise/checklist-logica
│   └── testassist_mcp_server.py # FastMCP stdio-server die de 5 tools wiret
├── knowledge/
│   ├── techniques/               # 7 techniekbestanden (JSON)
│   └── heuristics/              # 6 heuristiekbestanden (JSON)
├── mcpb/                        # Smithery MCPB distributie-bundle
│   ├── manifest.json            # MCPB v0.4 manifest
│   └── server/                  # kopie van server/ + knowledge/ voor distributie
├── scripts/
│   └── harvest.py               # valideert kennisbasis en print index
└── tests/                        # pytest-suite
```
