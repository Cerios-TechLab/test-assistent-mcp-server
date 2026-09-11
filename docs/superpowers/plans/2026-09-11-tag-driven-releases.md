# Tag-Driven Releases via glama-build-gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een `v*`-tag die door de volledige glama-build-gate komt, publiceert automatisch een GitHub release (versie-tracker).

**Architecture:** De bestaande `glama-build-gate.yml`-workflow krijgt een tag-filter (`v*`) op de push-trigger plus een nieuwe `release`-job die na de `verify`-job draait. De release-job checkt dat de tag-versie gelijk is aan de package-versie in `pyproject.toml` en maakt dan `gh release create` aan met automatisch gegenereerde notes. De gate blijft de enige kwaliteitspoort.

**Tech Stack:** GitHub Actions, `gh` CLI (voorgeïnstalleerd op runners), `GITHUB_TOKEN` (auto), YAML, shell.

## Global Constraints

- De `verify`-job mag inhoudelijk niet veranderen; een tag-release moet door de volledige bestaande gate.
- `permissions: contents: write` mag alleen op de `release`-job; de rest blijft `contents: read`.
- Release wordt alleen aangemaakt bij pushes van `refs/tags/v*` (exacte prefix `v`).
- Tag-versie (zonder `v`-prefix) moet gelijk zijn aan `version` in `pyproject.toml`, anders faalt de release zonder release aan te maken.
- Geen artefact-upload; `--generate-notes` voor de release-notes.
- De workflow blijft op main-push en pull_request draaien precies zoals nu.

---

### Task 1: Tag-filter + release-job in glama-build-gate.yml

**Files:**
- Modify: `.github/workflows/glama-build-gate.yml`

**Interfaces:**
- Consumes: bestaande `verify`-job (naam, taken — onveranderd).
- Produces: `release`-job die afhankelijk is van `verify` en bij succes de GitHub release publiceert.

- [ ] **Step 1: Tag-filter toevoegen aan de trigger**

Voeg `tags: ["v*"]` toe aan de `push`-trigger:

```yaml
on:
  push:
    branches: [main]
    tags: ["v*"]
    paths-ignore: ["docs/**", "README.md"]
```

Let op YAML: `tags` tussen `branches` en `paths-ignore`. Een tag-push matcht `tags` (paths-ignore wordt niet geëvalueerd voor tag-pushes), main-push matcht `branches`.

- [ ] **Step 2: YAML-validatie**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/glama-build-gate.yml')); print('YAML OK')"` vanuit de repo-root.
Expected: `YAML OK` (foutmelding bij ongeldig YAML).

- [ ] **Step 3: Release-job toevoegen**

Voeg aan het einde van de workflow (na de `verify`-job, op index-niveau van `jobs:`) toe:

```yaml
  release:
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    needs: verify
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7

      - name: Verify tag matches package version
        run: |
          TAG="${GITHUB_REF_NAME#v}"
          PKG_VERSION="$(sed -n 's/^version = "\([^"]*\)".*/\1/p' pyproject.toml | head -1)"
          echo "tag=${TAG} package=${PKG_VERSION}"
          if [ -z "$PKG_VERSION" ]; then
            echo "::error::Could not read version from pyproject.toml"
            exit 1
          fi
          if [ "$TAG" != "$PKG_VERSION" ]; then
            echo "::error::Tag version '${TAG}' does not match package version '${PKG_VERSION}'"
            exit 1
          fi

      - name: Create GitHub Release
        run: gh release create "$GITHUB_REF_NAME" --generate-notes
```

Belangrijk: `permissions` van de werkflow bovenaan (regel 11-12) blijft `contents: read`; de `release`-job overschrijft dit alleen voor zichzelf.

- [ ] **Step 4: YAML-validatie opnieuw**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/glama-build-gate.yml')); print('YAML OK')"`.
Expected: `YAML OK`.

- [ ] **Step 5: Versie-extractielogica lokaal verifiëren**

Run: `TAG="0.1.0"; PKG_VERSION="$(sed -n 's/^version = "\([^"]*\)".*/\1/p' pyproject.toml | head -1)"; echo "tag=$TAG package=$PKG_VERSION"; [ "$TAG" = "$PKG_VERSION" ] && echo MATCH`
Expected: `tag=0.1.0 package=0.1.0` en `MATCH` (huidige pyproject-versie is 0.1.0).

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/glama-build-gate.yml
git commit -m "ci: create GitHub release on green v*-tag (tag-driven releases)"
```

---

### Task 2: End-to-end verificatie met een echte tag

**Files:** geen wijzigingen — test-only.

**Interfaces:**
- Consumes: het resultaat van Task 1 (workflow met tag-filter + release-job).
- Produces: bewijs dat de gate + release-pipeline werkt vanuit een echte tag.

- [ ] **Step 1: Tag aanmaken en pushen**

```bash
git tag v0.1.0
git push origin v0.1.0
```

Expected: push slaagt; `gh run list --repo Cerios-TechLab/test-assistent-mcp-server` toont een nieuwe run van `glama-build-gate` (niet van `smithery-deploy` — die filtert op `branches: [main]`).

- [ ] **Step 2: Wacht op de workflow en controleer succes**

```bash
sleep 60
gh run list --repo Cerios-TechLab/test-assistent-mcp-server --limit 3
```

Expected: de run voor de tag-push is `completed success`. Beide jobs (`verify` + `release`) zijn groen. Controleer desgewenst de job-details: `gh run view <run-id> --repo Cerios-TechLab/test-assistent-mcp-server`.

- [ ] **Step 3: Release bestaat op GitHub**

```bash
gh release list --repo Cerios-TechLab/test-assistent-mcp-server
```

Expected: een release `v0.1.0` zichtbaar. `gh release view v0.1.0 --repo Cerios-TechLab/test-assistent-mcp-server` toont auto-gegenereerde notes uit de commit-historie (eerste release → volledige historie).

- [ ] **Step 4: Negatieve test → tag-versie mismatch**

Verifieer de fail-path zonder de echte repo te vervuilen: bouw het mislukte pad lokaal na.

```bash
TAG="9.9.9"; PKG_VERSION="$(sed -n 's/^version = "\([^"]*\)".*/\1/p' pyproject.toml | head -1)"; echo "tag=$TAG package=$PKG_VERSION"; [ "$TAG" != "$PKG_VERSION" ] && echo "RELEASE BLOCKED (mismatch)"
```

Expected: `tag=9.9.9 package=0.1.0` en `RELEASE BLOCKED (mismatch)`.

Echte push van een mismatchen tag (`v9.9.9`) is optioneel; de `if: startsWith(github.ref, 'refs/tags/v')`-guard en de versiecheck zijn de bescherming. Niks committen/verwijderen.

- [ ] **Step 5: Afronden**

Bevestig dat de main-tak ongemoeid is: `git status` schoon, `git log --oneline -1` toont de Task 1-commit. Push van de tag heeft geen code-commit gemaakt.

---

## Acceptatiecriteria (uit de spec)

1. `v0.2.0` met `version = "0.2.0"` → volledige gate groen + GitHub release met notes. (Task 2 met `v0.1.0` is de eerste proof; latere versies volgen hetzelfde pad.)
2. Tag-versie ≠ package-versie → release faalt met duidelijke melding, geen release. (Task 2 Step 4; beschermd door de versiecheck in Task 1.)
3. Push op `main` zonder tag → ongewijzigd gedrag (gate, geen release). (Workflow wijzigt de main-push-trigger niet.)
4. `gh release list` toont de release; notes bevatten de commits. (Task 2 Step 3.)