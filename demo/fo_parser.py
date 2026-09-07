"""Heuristic FO parser: extract testable field specs from a Functional Description.

Dutch-keyword heuristics only. Returns a spec dict the BDD builder can consume.
This is intentionally simple — enough for the live demo, not a full NLP parser.
"""

from __future__ import annotations

import re
from typing import Any


def _detect_type(text: str) -> str:
    if re.search(r"geheel getal|integer|natuurlijk getal|heel getal|teller", text, re.I):
        return "integer"
    if re.search(r"datum|date", text, re.I):
        return "date"
    return "string"


def parse_fo(text: str) -> dict[str, Any]:
    specs: dict[str, Any] = {"feature": "Registratie", "fields": []}

    # Feature name from a "controle/check/validatie" noun in the text.
    m = re.search(r"([a-z]+(?:controle|check|validatie))", text, re.I)
    if m:
        specs["feature"] = m.group(1).capitalize()

    # Field name: word directly before "veld", else "het <woord> accepteert".
    field = None
    fm = re.search(r"(\w+?)veld", text, re.I)
    if fm:
        field = fm.group(1)
    else:
        fm = re.search(r"het\s+(\w+)\s+accepteert", text, re.I)
        if fm:
            field = fm.group(1)
    if not field:
        field = "veld"
    field = field.rstrip("s")  # "leeftijds" -> "leeftijd"

    ftype = _detect_type(text)

    # Range: "tussen X en Y" or "X tot Y".
    rng = re.search(r"tussen\s+(\d+)\s+en\s+(\d+)", text, re.I) or re.search(
        r"(\d+)\s+tot\s+(\d+)", text, re.I
    )
    fmin = int(rng.group(1)) if rng else None
    fmax = int(rng.group(2)) if rng else None

    # Rules: "< N" / ">= N" with surrounding reject/accept wording + quoted message.
    rules: list[dict[str, Any]] = []
    for rm in re.finditer(r"(\w+)\s*(<|>=|<=|>|==)\s*(\d+)", text):
        field_token, op, thr = rm.group(1), rm.group(2), int(rm.group(3))
        if field_token.lower() not in (field, "leeftijd", "age"):
            continue
        seg = text[max(0, rm.start() - 50): rm.end() + 50]
        rejected = op == "<" or bool(
            re.search(r"geweigerd|afgewezen|niet|fout|ongeld", seg, re.I)
        )
        msg = None
        qm = re.search(r"['\"]([^'\"]+)['\"]", seg)
        if qm:
            msg = qm.group(1)
        rules.append(
            {
                "condition": f"{op} {thr}",
                "expected": "rejected" if rejected else "accepted",
                "message": msg,
            }
        )

    # Non-numeric / missing value -> validation error.
    if re.search(r"niet-numeriek|ontbrekend|niet-numerieke|ongeldig", text, re.I):
        rules.append(
            {
                "condition": "non-numeric / missing",
                "expected": "validation error",
                "message": "validatiefout",
            }
        )

    specs["fields"].append(
        {
            "name": field,
            "type": ftype,
            "min": fmin,
            "max": fmax,
            "rules": rules,
        }
    )
    return specs


if __name__ == "__main__":
    import json

    sample = (
        "FO-FR014 — Leeftijdscontrole bij registratie\n"
        "Het leeftijdsveld accepteert een geheel getal tussen 0 en 120.\n"
        "Bij leeftijd < 18 wordt registratie geweigerd met de melding "
        "'Je moet 18 jaar of ouder zijn.'\n"
        "Bij leeftijd >= 18 wordt het account aangemaakt.\n"
        "Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout."
    )
    print(json.dumps(parse_fo(sample), indent=2, ensure_ascii=False))
