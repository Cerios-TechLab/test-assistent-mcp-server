"""Streamlit demo: stuur een stuk FO naar OpenCode (big-pickle), die de Test Assistent
MCP-server (testassist) raadpleegt, en toon het antwoord terug in de GUI."""

from __future__ import annotations

import re
import subprocess

import streamlit as st

try:
    from demo.opencode_client import ask, DEFAULT_MODEL
except ImportError:
    from opencode_client import ask, DEFAULT_MODEL

DEFAULT_FO = """FO-FR014 — Leeftijdscontrole bij registratie

Als geregistreerde gebruiker wil ik bij registratie mijn leeftijd opgeven,
zodat alleen bezoekers van 18 jaar of ouder een account kunnen aanmaken.

•  Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.
•  Bij leeftijd < 18 wordt registratie geweigerd met de melding
      'Je moet 18 jaar of ouder zijn.'
•  Bij leeftijd >= 18 wordt het account aangemaakt.
•  Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout."""

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

OUTPUT_BDD = "BDD-scenario's (Gherkin)"
OUTPUT_CHARTER = "Exploratory Test Charter"


def build_prompt(fo: str, technique: str, output: str) -> str:
    if output == OUTPUT_BDD:
        return (
            "You have access to the Test Assistent MCP server (tools are named "
            "testassist_advise_technique, testassist_generate_test_cases, "
            "testassist_catalog_heuristics, etc.). Use them to analyze the "
            "Functionele Omschrijving (FO) below and produce Gherkin BDD scenarios "
            "(Functionaliteit / Scenario / Gegeven / Als / Dan / En), in Dutch.\n\n"
            "Required tool calls:\n"
            "1. testassist_advise_technique with the FO as the description.\n"
            "2. testassist_generate_test_cases with technique 'Boundary Value "
            "Analysis' and inputs {field, min, max} derived from the FO.\n"
            f"(Selected technique context: {technique}.)\n\n"
            "Output: ONLY the final Gherkin inside a single ```gherkin code block. "
            "No commentary, no headings outside the code block.\n\n"
            f"FO:\n{fo}"
        )
    return (
        "You have access to the Test Assistent MCP server (tools named "
        "testassist_catalog_heuristics, testassist_advise_technique, etc.). "
        "Use them to produce an Exploratory Test Charter (RST: SFDPOT "
        "decomposition × FEW HICCUPPS oracles) for the FO below, in Dutch.\n\n"
        f"Selected heuristic: {technique}.\n\n"
        "Required tool calls:\n"
        "1. testassist_catalog_heuristics (no arguments) for reference.\n"
        "2. testassist_advise_technique with the FO as the description.\n\n"
        "Output: the charter as Markdown. Do NOT wrap it in a code block. "
        "Do NOT add preamble or explanation outside the charter.\n\n"
        f"FO:\n{fo}"
    )


def render_answer(text: str, output: str):
    """Display the model's answer; prefer a Gherkin code block when present."""
    if output == OUTPUT_BDD:
        m = re.search(r"```(?:gherkin)?\s*([\s\S]+?)```", text)
        if m:
            body = m.group(1).strip("\n")
            st.code(body, language="gherkin")
            st.download_button("Download BDD", body, file_name="bdd-scenarios.txt")
            return
    st.markdown(text)
    ext = "bdd.txt" if output == OUTPUT_BDD else "test-charter.md"
    st.download_button("Download antwoord", text, file_name=ext)


def main() -> None:
    st.set_page_config(page_title="FO → BDD / Charter (via OpenCode)", layout="wide")
    st.title("FO → BDD scenario's of Exploratory Test Charter")
    st.caption(
        "Stuurt de Functionele Omschrijving naar OpenCode (model "
        f"`{DEFAULT_MODEL}`), die de Test Assistent MCP-server raadpleegt. "
        "Het antwoord wordt hier teruggegeven."
    )

    col1, col2 = st.columns(2)
    technique = col1.selectbox("Techniek / heuristiek", TECHNIQUES, index=0)
    output = col2.radio(
        "Output-type", [OUTPUT_BDD, OUTPUT_CHARTER], horizontal=True,
    )

    if "fo_text" not in st.session_state:
        st.session_state.fo_text = DEFAULT_FO
    uploaded = st.file_uploader("Of laad een FO-bestand (.txt)", type="txt")
    if uploaded is not None:
        st.session_state.fo_text = uploaded.read().decode("utf-8")

    fo = st.text_area(
        "Functionele Omschrijving (FO)",
        value=st.session_state.fo_text,
        height=280,
        key="fo",
    )

    label = "Genereer BDD-scenario's" if output == OUTPUT_BDD else "Genereer Test Charter"
    if st.button(label + " via OpenCode", type="primary"):
        if not fo.strip():
            st.error("Vul eerst een FO in.")
            return
        prompt = build_prompt(fo, technique, output)
        with st.spinner(
            f"OpenCode ({DEFAULT_MODEL}) raadpleegt de MCP-server…"
        ):
            try:
                res = ask(prompt, model=DEFAULT_MODEL, cwd="/root",
                          title="fo-bdd-demo", timeout=600)
            except subprocess.TimeoutExpired:
                st.error("OpenCode duurde te lang (timeout).")
                return
            except FileNotFoundError as exc:
                st.error(f"OpenCode binary niet gevonden: {exc}")
                return
            except Exception as exc:  # noqa: BLE001
                st.error(f"OpenCode-call mislukt: {exc}")
                return

        st.subheader("Antwoord van OpenCode")
        render_answer(res["text"], output)

        used = res["tools"]
        if used:
            st.info("Geraadpleegde MCP-tools (door OpenCode): " + ", ".join(used))
        else:
            st.warning(
                "OpenCode gaf geen tool-aanroepen terug — het model heeft de "
                "MCP-server mogelijk niet gebruikt. Probeer de prompt te "
                "verduidelijken of de timebox te verhogen."
            )
        if res.get("session"):
            st.caption(f"OpenCode-sessie: {res['session']}")
        if res["returncode"] != 0:
            with st.expander("OpenCode stderr"):
                st.code(res["stderr_tail"])


if __name__ == "__main__":
    main()
