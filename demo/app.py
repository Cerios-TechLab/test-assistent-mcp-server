"""Streamlit demo: FO -> BDD scenario generator that consults the REAL
Test Assistent MCP server over the MCP protocol (stdio)."""

from __future__ import annotations

import streamlit as st

try:
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import format_bdd
    from demo.mcp_client import consult_server
except ImportError:  # when run with cwd == demo/
    from fo_parser import parse_fo
    from bdd_builder import format_bdd
    from mcp_client import consult_server

DEFAULT_FO = """FO-FR014 — Leeftijdscontrole bij registratie

Als geregistreerde gebruiker wil ik bij registratie mijn leeftijd opgeven,
zodat alleen bezoekers van 18 jaar of ouder een account kunnen aanmaken.

•  Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.
•  Bij leeftijd < 18 wordt registratie geweigerd met de melding
      'Je moet 18 jaar of ouder zijn.'
•  Bij leeftijd >= 18 wordt het account aangemaakt.
•  Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout.
- Je mag niet jonger zijn dan 0 jaar
- Geen account aanmaken als je een alcoholist bent"""


def main() -> None:
    st.set_page_config(page_title="FO → BDD demo", layout="wide")
    st.title("FO → BDD scenario generator")
    st.caption(
        "Genereert Gherkin BDD-scenario's uit een stuk Functionele Omschrijving, "
        "door de échte Test Assistent MCP-server te raadplegen (advise_technique + "
        "generate_test_cases via het MCP-protocol)."
    )

    fo = st.text_area("Functionele Omschrijving (FO)", DEFAULT_FO, height=320)

    if st.button("Genereer BDD-scenario's (via MCP-server)", type="primary"):
        specs = parse_fo(fo)
        if not specs["fields"]:
            st.error(
                "Geen veldspecificaties herkend in de FO. Voeg bijv. een bereik "
                "toe (bijv. 'tussen 0 en 120') of vul een veld handmatig in."
            )
            return

        with st.spinner("MCP-server wordt geraadpleegd…"):
            try:
                advice, bva_raw, used = consult_server(fo, specs)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Kon de MCP-server niet raadplegen: {exc}")
                return

        gherkin = format_bdd(specs, bva_raw)

        st.subheader("Geëxtraheerde veld-specificaties")
        st.json(specs, expanded=False)

        if advice:
            st.subheader("Advies van de MCP-server (advise_technique)")
            st.json(advice, expanded=False)

        st.subheader("BDD-scenario's (Gherkin)")
        st.code(gherkin, language="gherkin")
        st.download_button(
            "Download als tekst",
            gherkin,
            file_name="bdd-scenarios.txt",
            mime="text/plain",
        )
        if used:
            st.info("Geraadpleegde MCP-tools: " + ", ".join(used))


if __name__ == "__main__":
    main()
