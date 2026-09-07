"""Streamlit demo: FO -> BDD scenarios OR Exploratory Test Charter, by consulting
the REAL Test Assistent MCP server (advise_technique, generate_test_cases,
catalog_heuristics)."""

from __future__ import annotations

import streamlit as st

try:
    from demo.fo_parser import parse_fo
    from demo.bdd_builder import format_bdd
    from demo.charter_builder import build_charter
    from demo.mcp_client import consult_server
except ImportError:
    from fo_parser import parse_fo
    from bdd_builder import format_bdd
    from charter_builder import build_charter
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

TECHNIQUES = [
    "Auto (advise_technique)",
    "Boundary Value Analysis",
    "Equivalence Partitioning",
    "Pairwise Testing",
    "SFDPOT",
    "FEW HICCUPPS",
    "RCRCRC",
    "Quality Criteria Catalog",
    "Bug Heuristics",
    "Test Tours",
]


def main() -> None:
    st.set_page_config(page_title="FO → BDD / Charter demo", layout="wide")
    st.title("FO → BDD scenario's of Exploratory Test Charter")
    st.caption(
        "Genereert BDD (Gherkin) of een Exploratory Test Charter (RST) uit een "
        "Functionele Omschrijving, door de échte Test Assistent MCP-server te "
        "raadplegen (advise_technique, generate_test_cases, catalog_heuristics)."
    )

    col1, col2 = st.columns(2)
    technique = col1.selectbox(
        "Techniek / heuristiek", TECHNIQUES, index=0,
        help="Voor BDD wordt automatisch BVA gebruikt; kies 'Charter' voor de overige.",
    )
    output = col2.radio(
        "Output-type",
        ["BDD-scenario's (Gherkin)", "Exploratory Test Charter"],
        horizontal=True,
    )

    if "fo_text" not in st.session_state:
        st.session_state.fo_text = DEFAULT_FO
    uploaded = st.file_uploader("Of laad een FO-bestand (.txt)", type="txt")
    if uploaded is not None:
        st.session_state.fo_text = uploaded.read().decode("utf-8")

    fo = st.text_area(
        "Functionele Omschrijving (FO)",
        value=st.session_state.fo_text,
        height=300,
        key="fo",
    )

    label = "Genereer BDD-scenario's" if output.startswith("BDD") else "Genereer Test Charter"
    if st.button(label + " (via MCP-server)", type="primary"):
        specs = parse_fo(fo)
        if not specs["fields"]:
            st.error(
                "Geen veldspecificaties herkend in de FO. Voeg bijv. een bereik "
                "toe (bijv. 'tussen 0 en 120') of vul een veld handmatig in."
            )
            return

        with st.spinner("MCP-server wordt geraadpleegd…"):
            try:
                advice, bva_raw, heuristics, used = consult_server(fo, specs)
            except Exception as exc:
                st.error(f"Kon de MCP-server niet raadplegen: {exc}")
                return

        st.subheader("Geëxtraheerde veld-specificaties")
        st.json(specs, expanded=False)

        if advice:
            st.subheader("Advies van de MCP-server (advise_technique)")
            st.json(advice, expanded=False)

        if output.startswith("BDD"):
            if technique not in ("Auto (advise_technique)", "Boundary Value Analysis"):
                st.warning(
                    "BDD wordt automatisch gegenereerd op basis van Boundary Value "
                    "Analysis. Voor andere technieken kies 'Exploratory Test Charter'."
                )
            gherkin = format_bdd(specs, bva_raw)
            st.subheader("BDD-scenario's (Gherkin)")
            st.code(gherkin, language="gherkin")
            st.download_button(
                "Download BDD (.txt)",
                gherkin,
                file_name="bdd-scenarios.txt",
                mime="text/plain",
            )
        else:
            charter = build_charter(
                fo,
                specs,
                (heuristics or {}).get("heuristics"),
                used,
                technique=technique,
            )
            st.subheader(f"Exploratory Test Charter — {technique}")
            st.markdown(charter)
            st.download_button(
                "Download Charter (.md)",
                charter,
                file_name="test-charter.md",
                mime="text/markdown",
            )

        if used:
            st.info("Geraadpleegde MCP-tools: " + ", ".join(used))


if __name__ == "__main__":
    main()
