# Test Assistant MCP Server

A knowledge/tools MCP server for OpenCode that exposes classic test techniques and test heuristics as tools, backed by a local, self-contained knowledge base.

## Tools

- `catalog_techniques()` — list all classic techniques (BVA, equivalence partitioning, decision table, pairwise, state transition, use case, error guessing).
- `catalog_heuristics()` — list all heuristic lists (SFDPOT, FEW HICCUPPS, RCRCRC, quality criteria catalog, bug heuristics, test tours).
- `generate_test_cases(technique, inputs)` — generate concrete testcases for supported techniques (only testcases; the agent does the rest).
- `advise_technique(description)` — keyword-based recommendation of techniques/heuristics for a described context.
- `checklist_for(context)` — produce a recommended test checklist (e.g. RCRCRC for regression).

## Setup

```bash
/usr/bin/python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run (stdio)

```bash
.venv/bin/python server/testassist_mcp_server.py
```

## Register in OpenCode

Add to `~/.config/opencode/opencode.json` under `mcp`:

```json
"testassist": {
  "type": "local",
  "command": ["/root/testassist-mcp/.venv/bin/python", "/root/testassist-mcp/server/testassist_mcp_server.py"],
  "enabled": true
}
```

## Knowledge base

Knowledge lives in `knowledge/` as one JSON file per technique/heuristic. Add a file to extend the server without code changes. Validate with:

```bash
.venv/bin/python scripts/harvest.py
```

## Test

```bash
.venv/bin/python -m pytest
```
