"""BDD builder: turn parsed FO specs into Gherkin, reusing MCP-server logic."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# Make the repo root importable so `server.*` resolves regardless of cwd.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.generators import generate_boundary_value_analysis  # noqa: E402


def _classify(value: int, f: dict[str, Any]):
    """Return (accepted, reasons). Reasons explain why a value is rejected."""
    reasons: list[str] = []
    if f.get("min") is not None and (value < f["min"] or value > f["max"]):
        reasons.append("bereik")
    for r in f.get("rules", []):
        if r["expected"] == "rejected":
            m = re.match(r"(<|>=|<=|>)\s*(\d+)", r["condition"])
            if m and (m.group(1) in ("<", ">=") and value < int(m.group(2))):
                reasons.append(f"regel:{r.get('message', '')}")
    return len(reasons) == 0, reasons


def _rule_thresholds(f: dict[str, Any]) -> set[int]:
    vals: set[int] = set()
    for r in f.get("rules", []):
        m = re.match(r"(<|>=|<=|>)\s*(\d+)", r["condition"])
        if m and m.group(1) in ("<", ">="):
            thr = int(m.group(2))
            vals.add(thr)
            vals.add(thr - 1)
    return vals


def build_bdd(text: str, specs: dict[str, Any]):
    """Return (gherkin_str, used_tools_list)."""
    used: list[str] = []
    out: list[str] = []
    feature = specs.get("feature") or "Registratie"
    out.append(f"Functionaliteit: {feature}")
    out.append("")

    for f in specs["fields"]:
        values: set[int] = set()
        if f.get("min") is not None and f.get("max") is not None:
            cases = generate_boundary_value_analysis(
                {"field": f["name"], "min": f["min"], "max": f["max"]}
            )
            used.append("generate_boundary_value_analysis")
            for c in cases:
                values.add(c["input"][f["name"]])
        values |= _rule_thresholds(f)

        # Non-numeric / missing -> validation error scenario.
        for r in f.get("rules", []):
            if r["expected"] == "validation error":
                out.append(f"  Scenario: Ongeldig type voor {f['name']}")
                out.append(f"    Gegeven een bezoeker vult een niet-numerieke {f['name']} in")
                out.append(f"    Als de registratie wordt verzonden")
                out.append(f"    Dan verschijnt een validatiefout")
                out.append("")

        for v in sorted(values):
            accepted, reasons = _classify(v, f)
            out.append(f"  Scenario: {f['name']} = {v}")
            out.append(f"    Gegeven een bezoeker vult {f['name']} {v} in")
            out.append(f"    Als de registratie wordt verzonden")
            if accepted:
                out.append(f"    Dan wordt het account aangemaakt")
            else:
                msg = ""
                for rs in reasons:
                    if rs.startswith("regel:"):
                        msg = rs.split(":", 1)[1]
                if msg:
                    out.append(f"    Dan verschijnt '{msg}'")
                else:
                    out.append(
                        f"    Dan verschijnt een melding over het bereik {f['min']}-{f['max']}"
                    )
                out.append(f"    En wordt er geen account aangemaakt")
            out.append("")

    gherkin = "\n".join(out).rstrip() + "\n"
    return gherkin, used


if __name__ == "__main__":
    from demo.fo_parser import parse_fo

    sample = (
        "FO-FR014 — Leeftijdscontrole bij registratie\n"
        "Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.\n"
        "Bij leeftijd < 18 wordt registratie geweigerd met de melding "
        "'Je moet 18 jaar of ouder zijn.'\n"
        "Bij leeftijd >= 18 wordt het account aangemaakt.\n"
        "Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout."
    )
    g, used = build_bdd(sample, parse_fo(sample))
    print(g)
    print("used:", used)
