# Tag-driven GitHub releases via glama-build-gate

Datum: 2026-09-11
Status: goedgekeurd (brainstorm)

## Doel

De versie van de testassist-mcp-server traceerbaar maken. Elke gepubliceerde
versie ontstaat uit een tag die door de volledige bestaande kwaliteitsgate is
gekomen. De release fungeert als versie-tracker: aan elke release is precies
duidelijk welke code en welke package-versie erop Glama/Smithery draait.

## Beslissingen (uit brainstorm)

- **Doel**: versie-tracker, geen installatie-artefacten.
- **Trigger**: tag-driven. Een handmatig geprikte tag `v*` (b.v. `v0.2.0`)
  triggert de release.
- **Integratie**: de bestaande `glama-build-gate`-workflow wordt uitgebreid;
  de gate blijft de enige kwaliteitspoort. Geen aparte release-workflow.

## Werkingsmechanisme

### Trigger

Aan `on.push` in `glama-build-gate.yml` wordt een tag-filter toegevoegd:

```yaml
on:
  push:
    branches: [main]
    tags: ["v*"]
    paths-ignore: ["docs/**", "README.md"]
```

- Push op `main` blijft de gate draaien (ongewijzigd gedrag).
- Push van een `v*`-tag (b.v. `v0.2.0`) draait dezelfde gate én, bij succes,
  wordt een GitHub release aangemaakt.

### Verificatie (ongewijzigd)

De bestaande taken blijven identiek:

1. unit tests (`python -m pytest tests/ -q`)
2. lint Dockerfile (`hadolint`)
3. `docker build`
4. MCP smoke-test in de image (8 tools via stdio)

Een tag-release moet dus door de volledige gate.

### Release-emissie (nieuw, laatste job)

Een nieuwe job `release` die alleen draait bij een `v*`-tag:

```yaml
  release:
    if: startsWith(github.ref, 'refs/tags/v')
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - name: Verify tag matches package version
        run: ...
      - name: Create GitHub Release
        run: gh release create "$GITHUB_REF_NAME" --generate-notes
```

- `permissions: contents: write` geldt alleen voor de release-job; de
  verificatie-jobs blijven `contents: read`.
- `gh release create` genereert release-notes automatisch uit de
  commit-historie sinds de vorige tag. Zonder vorige tag vallen de notes terug
  op de volledige historie (eerste release werkt dus ook).
- Geen artefacten (wheels etc.) worden geüpload. Doel is versie-tracker, geen
  distributie.

### Versie-consistentiecheck

Vóór het publiceren controleert de release-job dat de tag-versie en de
package-versie overeenkomen:

- Tag `v0.2.0` ⇒ pakket-versie in `pyproject.toml` is `0.2.0`.
- Bij mismatch faalt de release met een duidelijke melding, zodat een tag
  nooit een andere versie "released" dan de code die erbij hoort.

## Foutafhandeling

- Falen in een verificatietaak → geen release; de gate blijft de poort.
- Falen in de release-job zelf → geen release; de tag blijft staan en de
  workflow kan veilig opnieuw gedraaid worden (`workflow_dispatch` is al
  beschikbaar). Geen tag-verplaatsing nodig.

## Buiten scope

- Automatische versie-hoog in code (geen automatische bumps).
- Artifact-upload of distributie naar PyPI/Smithery.
- Automatische release bij elke push naar `main`.

## Nieuw te schrijven / wijzigen

- `glama-build-gate.yml`: tag-filter in trigger + job `release`.
- Geen Python-wijzigingen aan de server; release-logica is pure werkflow.

## Acceptatiecriteria

1. Push van `v0.2.0` (met `version = "0.2.0"` in pyproject.toml) loopt de
   volledige gate groen en maakt een GitHub release met release-notes.
2. Tag-versie ≠ package-versie → release faalt met duidelijke melding, geen
   release aangemaakt.
3. Push op `main` zonder tag → ongewijzigd gedrag (gate, geen release).
4. `gh release list` toont de release; notes bevatten de commits sinds de
   vorige release (of volledige historie bij de eerste).