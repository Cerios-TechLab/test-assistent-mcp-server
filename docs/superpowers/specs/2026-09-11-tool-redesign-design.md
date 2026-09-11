# Design — Tool-redesign testassist-mcp voor Glama tool-design-score (TDQSB)

Datum: 2026-09-11
Status: goedgekeurd door Steavy

## Probleem

Glama's tool-design-beoordeling (TDQSB) gaf 3.2/5.0 op 2026-09-09. Feedback over
de generatie-tools:

> The catalog, advice, and checklist tools are clearly distinct, but the
> generation tools overlap heavily: generate_test_cases, generate_boundary_cases,
> generate_with_property, and generate_random all produce test cases or test
> data. Boundary value analysis is both a technique and a boundary-data
> generation mode, making tool selection ambiguous without very close reading.

Daarnaast zijn de input-schemas van `spec`/`inputs`-params kale `{"type":
"object"}` — FastMCP bouwt die uit de `dict`-annotatie zonder eigenschappen,
wat score kost op schema-kwaliteit.

## Doel

1. Overlap oplossen: 4 onderscheidende generatie-tools → 2 met elk een unieke
   verantwoordelijkheid.
2. Generatie versterken: alle 7 technieken uit de kennisbank automatisch
   genereerbaar, niet alleen BVA/EP/Pairwise.
3. Rijke JSON-schema's: via Pydantic discriminated unions zodat `tools/list`
   beschreven eigenschappen toont.

## Huidige tool-set (8)

| Tool | Input | Output | Rol |
|---|---|---|---|
| `catalog_techniques` | – | technieken | kennis |
| `catalog_heuristics` | – | heuristieken | kennis |
| `generate_test_cases` | technique, inputs | testcases (alleen BVA/EP/pairwise) | generatie |
| `generate_with_property` | spec | property-data (boundary+random) | generatie |
| `generate_boundary_cases` | spec | grensgevallen per type | generatie |
| `generate_random` | spec | random data | generatie |
| `advise_technique` | description | aanbevelingen | advies |
| `checklist_for` | context | checklist | advies |

## Nieuwe tool-set (6)

Onveranderd:

| Tool | Rol |
|---|---|
| `catalog_techniques()` | alle 7 technieken |
| `catalog_heuristics()` | alle 6 heuristieken |
| `advise_technique(description)` | aanbeveling obv sleutelwoorden |
| `checklist_for(context)` | checklist per heuristiek |

Samengevoegd/nieuw:

| Tool | Rol | Scheidslijn in beschrijving |
|---|---|---|
| `generate_test_cases` | techniek-gestuurd: alle 7 technieken → testcases met expected outcomes | "technique-driven; niet voor ruwe data" |
| `generate_test_data` | data-gestuurd: typed fields + constraints → waarden | "raw test data; gebruik generate_test_cases voor BVA/EP etc." |

Verwijderd als publiek: `generate_with_property`, `generate_boundary_cases`,
`generate_random` (code blijft als interne helpers in `generate.py`).

## Pydantic discriminated-union schemas

FastMCP 1.29.0 (v1.29.0-mcp) bouwt per-param een pydantic `arguments_model` met
de letterlijke annotatie; een `Annotated[Union[...], Field(discriminator=...)]`
wordt direct het JSON-schema in `tools/list` (oneOf per variant).

### `generate_test_data(input: TestDataInput)`

```python
TestDataInput = Annotated[
    Union[RandomDataSpec, PropertyDataSpec],
    Field(discriminator="strategy"),
]
```

- `RandomDataSpec`: `{strategy:"random", fields:[{field,type,constraints}], count, seed}`
- `PropertyDataSpec`: `{strategy:"property", field, type, constraints, count, seed, include_invalid}`

### `generate_test_cases(input: TechniqueCasesInput)`

```python
TechniqueCasesInput = Annotated[
    Union[
        BoundaryValueSpec,     # {technique:"Boundary Value Analysis", field, min, max}
        EquivalenceSpec,       # {technique:"Equivalence Partitioning", field, valid[], invalid[]}
        DecisionTableSpec,     # {technique:"Decision Table", conditions[], actions[], rules[]}
        PairwiseSpec,          # {technique:"Pairwise Testing", values{}}
        StateTransitionSpec,   # {technique:"State Transition", states[], events[], transitions[]}
        UseCaseSpec,           # {technique:"Use Case Testing", name, steps[], expected[]}
        ErrorGuessingSpec,     # {technique:"Error Guessing", field, input, pitfalls[]}
    ],
    Field(discriminator="technique"),
]
```

Foute `technique`/`strategy` → pydantic validatefout; geen `ValueError`-pad meer.

## Nieuwe technique-generators (`generators.py`)

Het register `_TECHNIQUE_GENERATORS` groeit van 3 naar 7:

| Techniek | Input | Output |
|---|---|---|
| BVA | `{field, min, max}` | grenzen met valid/invalid (bestaand) |
| Equivalence Partitioning | `{field, valid[], invalid[]}` | cases (bestaand) |
| Pairwise | `{values:{}}` | all-pairs-rijen (bestaand) |
| **Decision Table** | `{conditions[], actions[], rules[]}` | conditie-actie-regels per case |
| **State Transition** | `{states[], events[], transitions[]}` | state-event-transition cases |
| **Use Case** | `{name, steps[], expected[]}` | happy path + varianten |
| **Error Guessing** | `{field, input, pitfalls[]}` | negatieve cases per valkuil |

Alle 7 via dezelfde `generate_test_cases`-aanroep; blijven pure functies
(`dict → list[dict]`).

## Bestanden

| Bestand | Actie |
|---|---|
| `server/schemas.py` (nieuw) | Pydantic modellen + unions |
| `server/generators.py` | +4 generators |
| `server/generate.py` | ongewijzigd (helpers blijven intern) |
| `server/testassist_mcp_server.py` | 6 tools, pydantic params |
| `tests/test_generators.py` | +tests nieuwe generators |
| `tests/test_mcp_tools.py` | 6 tools, nieuwe aanroepvorm, schema-asserts |
| `scripts/mcp-smoke.py` | verwacht 8 → 6 |
| `README.md`, `server-card.json`, `.well-known/mcp/server-card.json`, `mcpb/manifest.json`, `make_presentation.py` | tool-lists syncen |
| `mcpb/server/*` | spiegel-sync |
| `pyproject.toml` + `uv.lock` | version 1.1.0 |

## Tests

- `test_generate.py` en `test_knowledge_base.py` blijven groen (interne API
  ongewijzigd).
- Nieuw: schema-shape-test (technique/strategy-discriminator zichtbaar in
  tools/list), alle 7 technieken via één `generate_test_cases`-aanroep, beide
  `generate_test_data`-strategieën.

## Versie & release

- Version: 1.0.1 → **1.1.0** (feature + breaking tool-surface; geen 2.0.0, pre-stabiel, geen externe consumers).
- Release-flow: commit → bump → tag `v1.1.0` → glama-build-and-release-gate
  (tests + smoke 6 tools) → release → Glama rescore automatisch (bevestigd:
  Glama maakt automatisch een Glama-release bij een GitHub-release en
  vervangt de draaiende build).