"""MCP client for the demo: spawn the real Test Assistent MCP server over stdio
and consult its tools (advise_technique, generate_test_cases) for the FO.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

ROOT = Path(__file__).resolve().parents[1]
# Run the server with the project venv (has the mcp SDK the server needs).
SERVER = [str(ROOT / ".venv" / "bin" / "python"), "-m", "server.testassist_mcp_server"]


def _payload(res: Any) -> Any:
    if getattr(res, "structuredContent", None):
        return res.structuredContent
    for c in res.content:
        if getattr(c, "text", None):
            try:
                return json.loads(c.text)
            except Exception:
                return c.text
    return None


async def _run(fo: str, specs: dict[str, Any]):
    used: list[str] = []
    params = StdioServerParameters(command=SERVER[0], args=SERVER[1:])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            advice = None
            try:
                adv = await s.call_tool("advise_technique", {"description": fo})
                advice = _payload(adv)
                used.append("advise_technique")
            except Exception:
                advice = None

            bva_raw = None
            field = specs["fields"][0] if specs["fields"] else None
            if field and field.get("min") is not None and field.get("max") is not None:
                bva = await s.call_tool(
                    "generate_test_cases",
                    {
                        "technique": "Boundary Value Analysis",
                        "inputs": {
                            "field": field["name"],
                            "min": field["min"],
                            "max": field["max"],
                        },
                    },
                )
                bva_raw = _payload(bva)
                used.append("generate_test_cases")

    return advice, bva_raw, used


def consult_server(fo: str, specs: dict[str, Any]):
    """Synchronous entry point used by the Streamlit app."""
    return asyncio.run(_run(fo, specs))


if __name__ == "__main__":
    from demo.fo_parser import parse_fo

    sample = (
        "FO-FR014 — Leeftijdscontrole bij registratie\n"
        "Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.\n"
        "Bij leeftijd < 18 wordt registratie geweigerd met de melding "
        "'Je moet 18 jaar of ouder zijn.'\n"
        "Bij leeftijd >= 18 wordt het account aangemaakt.\n"
        "Je mag niet jonger zijn dan 0 jaar.\n"
        "Geen account aanmaken als je een alcoholist bent."
    )
    sp = parse_fo(sample)
    advice, bva, used = consult_server(sample, sp)
    print("used:", used)
    print("advice:", json.dumps(advice, ensure_ascii=False)[:300])
    print("bva:", json.dumps(bva, ensure_ascii=False)[:400])
