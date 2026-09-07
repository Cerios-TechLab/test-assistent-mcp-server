"""BDD builder: turn parsed FO specs + SERVER-returned BVA cases into Gherkin.

The boundary VALUES come from the MCP server (generate_test_cases / BVA). The
business-rule classification (e.g. age < 18 rejected) comes from the parsed FO
rules, so the demo shows both the server output and the FO-driven logic.
"""

from __future__ import annotations

import re
from typing import Any


def _classify(value: int, f: dict[str, Any]):
    """Return (accepted, reasons). Reasons explain why a value is rejected."""
    reasons: list[str] = []
    if f.get("min") is not None and (value < f["min"] or value > f["max"]):
        reasons.append("bereik")
    for r in f.get("rules", []):
        if r.get("expected") == "rejected" and not r.get("qualitative"):
            m = re.match(r"(<|>=|<=|>)\s*(\d+)", r["condition"])
            if m and (m.group(1) in ("<", ">=") and value < int(m.group(2))):
                reasons.append(f"regel:{r.get('message', '')}")
    return len(reasons) == 0, reasons


def _rule_thresholds(f: dict[str, Any]) -> set[int]:
    vals: set[int] = set()
    for r in f.get("rules", []):
        if r.get("qualitative"):
            continue
        m = re.match(r"(<|>=|<=|>)\s*(\d+)", r["condition"])
        if m and m.group(1) in ("<", ">="):
            thr = int(m.group(2))
            vals.add(thr)
            vals.add(thr - 1)
    return vals


def format_bdd(specs: dict[str, Any], bva_raw: dict[str, Any] | None) -> str:
    out: list[str] = []
    feature = specs.get("feature") or "Registratie"
    out.append(f"Functionaliteit: {feature}")
    out.append("")

    for f in specs["fields"]:
        values: set[int] = set()
        if bva_raw and bva_raw.get("testcases"):
            for c in bva_raw["testcases"]:
                values.add(c["input"][f["name"]])
        values |= _rule_thresholds(f)

        # Qualitative business rules (e.g. "geen account als je een alcoholist bent").
        for r in f.get("rules", []):
            if r.get("qualitative"):
                words = r["message"].split()
                title = " ".join(words[:8]) + ("…" if len(words) > 8 else "")
                out.append(f"  Scenario: {title}")
                out.append(f"    Gegeven {r['message']}")
                out.append(f"    Als de registratie wordt verzonden")
                out.append(f"    Dan wordt er geen account aangemaakt")
                out.append("")

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

    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    import json

    from demo.mcp_client import consult_server
    from demo.fo_parser import parse_fo

    sample = (
        "FO-FR014 — Leeftijdscontrole bij registratie\n"
        "Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.\n"
        "Bij leeftijd < 18 wordt registratie geweigerd met de melding "
        "'Je moet 18 jaar of ouder zijn.'\n"
        "Bij leeftijd >= 18 wordt het account aangemaakt.\n"
        "Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout.\n"
        "Je mag niet jonger zijn dan 0 jaar.\n"
        "Geen account aanmaken als je een alcoholist bent."
    )
    sp = parse_fo(sample)
    advice, bva, used = consult_server(sample, sp)
    print(format_bdd(sp, bva))
    print("used:", used)
