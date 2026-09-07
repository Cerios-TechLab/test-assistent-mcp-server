"""Streamlit demo: FO -> BDD scenario generator (reuses MCP-server logic)."""

from __future__ import annotations

import streamlit as st

try:
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import build_bdd
except ImportError:  # when run with cwd == demo/
    from fo_parser import parse_fo
    from bdd_builder import build_bdd

DEFAULT_FO = """FO-FR014 — Leeftijdscontrole bij registratie

Als geregistreerde gebruiker wil ik bij registratie mijn leeftijd opgeven,
zodat alleen bezoekers van 18 jaar of ouder een account kunnen aanmaken.

•  Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.
•  Bij leeftijd < 18 wordt registratie geweigerd met de melding
      'Je moet 18 jaar of ouder zijn.'
•  Bij leeftijd >= 18 wordt het account aangemaakt.
•  Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout."""


def main() -> None:
    st.set_page_config(page_title="FO → BDD demo", layout="wide")
    st.title("FO → BDD scenario generator")
    st.caption(
        "Genereert Gherkin BDD-scenario's uit een stuk Functionele Omschrijving, "
        "met hergebruik van de Test Assistent MCP-server logica."
    )

    fo = st.text_area("Functionele Omschrijving (FO)", DEFAULT_FO, height=300)

    if st.button("Genereer BDD-scenario's", type="primary"):
        specs = parse_fo(fo)
        if not specs["fields"]:
            st.error(
                "Geen veldspecificaties herkend in de FO. Voeg bijv. een bereik "
                "toe (bijv. 'tussen 0 en 120') of vul een veld handmatig in."
            )
            return

        gherkin, used = build_bdd(fo, specs)

        st.subheader("Geëxtraheerde veld-specificaties")
        st.json(specs, expanded=False)

        st.subheader("BDD-scenario's (Gherkin)")
        st.code(gherkin, language="gherkin")
        st.download_button(
            "Download als tekst",
            gherkin,
            file_name="bdd-scenarios.txt",
            mime="text/plain",
        )
        if used:
            st.info("Gebruikte MCP-server logica: " + ", ".join(used))


if __name__ == "__main__":
    main()
