"""Exploratory Test Charter builder (RST: SFDPOT decomposition x FEW HICCUPPS oracles)."""

from __future__ import annotations

from typing import Any


def _split_rules(rules: list[dict[str, Any]]):
    rej = [r for r in rules if r["expected"] == "rejected" and not r.get("qualitative")]
    qual = [r for r in rules if r.get("qualitative")]
    val = [r for r in rules if r["expected"] == "validation error"]
    return rej, qual, val


def build_charter(
    fo: str,
    specs: dict[str, Any],
    heuristic_items: list[dict[str, Any]] | None,
    used_tools: list[str],
    technique: str = "SFDPOT",
) -> str:
    f = (
        specs["fields"][0]
        if specs["fields"]
        else {"name": "veld", "type": "string", "min": None, "max": None, "rules": []}
    )
    name = f["name"]
    fmin, fmax, ftype = f.get("min"), f.get("max"), f.get("type")
    rej, qual, val = _split_rules(f.get("rules", []))

    md: list[str] = []
    md.append(f"# Exploratory Test Charter — {specs.get('feature', 'Registratie')}")
    md.append("")
    md.append(f"**Target:** {name}-veld in {specs.get('feature', 'Registratie')}")
    md.append("**Methode:** SFDPOT (decompositie) × FEW HICCUPPS (orakels)")
    md.append(f"**Geselecteerde heuristiek:** {technique}")
    md.append("**Timebox:** 90 minuten")
    md.append("")
    md.append("## Productdecompositie (SFDPOT)")
    md.append(
        "- **S – Structure:** validatieregels + MCP-server-tools "
        "(generate_test_cases, advise_technique, catalog_heuristics)."
    )
    md.append(
        f"- **F – Function:** accepteer geldige {name} (binnen {fmin}–{fmax}); "
        "weiger ongeldige."
    )
    md.append(
        f"- **D – Data:** type={ftype}; bereik={fmin}–{fmax}; "
        "grenswaarden via Boundary Value Analysis (6 waarden)."
    )
    md.append("- **P – Platform:** web / stdio; geen platform-specifieke aannames.")
    md.append("- **O – Operations:** rol = bezoeker; geen auth-state in FO.")
    md.append("- **T – Time:** geen tijdsafhankelijkheid vermeld in de FO.")
    md.append("")
    md.append("## Orakels (FEW HICCUPPS)")
    md.append("- **User Expectations:** duidelijke, tijdige foutmelding bij ongeldige invoer.")
    md.append("- **Claims:** gedrag exact zoals letterlijk beschreven in de FO.")
    md.append("- **Comparable Products:** standaard webformulier-validatie.")
    md.append("- **Purpose:** het veld dient ter bescherming (leeftijd, limiet, etc.).")
    md.append("")
    md.append("## Exploratory scenario's")

    md.append("### Scenario 1: BVA-grenswaarden")
    md.append("**Koppeling:** D (Data) × Claims")
    md.append(
        f"**Actie:** Voer de zes BVA-grenswaarden in "
        f"({fmin - 1}, {fmin}, {fmin + 1}, {fmax - 1}, {fmax}, {fmax + 1}); "
        "observeer accept/reject en de meldingsteksten."
    )
    md.append("**Risico:** off-by-one; verkeerde melding bij precies de grens.")
    md.append(
        "**Orakel:** de laagste en hoogste geldige waarden worden geaccepteerd; "
        "waarden erbuiten worden geweigerd met een passende melding."
    )
    md.append("")

    if rej:
        r = rej[0]
        md.append(f"### Scenario 2: Bedrijfsregel-drempel ({r['condition']})")
        md.append("**Koppeling:** F (Function) × Claims")
        md.append(
            "**Actie:** Voer waarden net onder en op de drempel in; "
            "valideer melding en accountactie."
        )
        md.append("**Risico:** drempel verkeerd (≤ vs <) of melding verwisseld.")
        md.append("**Orakel:** reject/accept exact conform de FO-tekst.")
        md.append("")

    if qual:
        md.append("### Scenario 3: Kwalitatieve bedrijfsregel")
        md.append("**Koppeling:** F × User Expectations")
        md.append(
            f"**Actie:** Activeer de voorwaarde "
            f"('{(qual[0].get('message') or qual[0]['condition'])[:80]}') "
            "en probeer door te gaan."
        )
        md.append(
            "**Risico:** kwalitatieve regel wordt niet gehandhaafd of is onbereikbaar."
        )
        md.append("**Orakel:** actie wordt geweigerd met consistente melding.")
        md.append("")

    if val:
        md.append("### Scenario 4: Ongeldig datatype")
        md.append("**Koppeling:** D × Standards")
        md.append(
            "**Actie:** Voer niet-numerieke / lege waarde in; herlaad; "
            "voer extremen in (whitespace, emoji, SQL-achtig)."
        )
        md.append("**Risico:** crash, XSS, ongedefinieerd gedrag.")
        md.append("**Orakel:** schone validatiefout, geen crash, geen code-executie.")
        md.append("")

    if heuristic_items:
        md.append("## Server-referentie (catalog_heuristics)")
        for h in heuristic_items:
            desc = (h.get("description") or "")[:140]
            md.append(f"- **{h.get('name')}** — {desc}")
        md.append("")

    md.append("## Gebruikte MCP-tools")
    md.append(", ".join(used_tools) if used_tools else "(geen)")
    return "\n".join(md)


if __name__ == "__main__":
    from demo.fo_parser import parse_fo
    from demo.mcp_client import consult_server

    sample = (
        "FO-FR014 — Leeftijdscontrole bij registratie\n"
        "Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.\n"
        "Bij leeftijd < 18 wordt registratie geweigerd met de melding "
        "'Je moet 18 jaar of ouder zijn.'\n"
        "Bij leeftijd >= 18 wordt het account aangemaakt.\n"
        "Geen account aanmaken als je een alcoholist bent."
    )
    sp = parse_fo(sample)
    adv, bva, heuristics, used = consult_server(sample, sp)
    print(build_charter(sample, sp, (heuristics or {}).get("heuristics"), used))
