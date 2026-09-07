"""Heuristic FO parser: extract testable field specs from a Functional Description.

Dutch-keyword heuristics only. Returns a spec dict the BDD builder can consume.
This is intentionally simple — enough for the live demo, not a full NLP parser.
It now also picks up extra constraint lines such as "niet jonger dan N",
"niet ouder dan N" and qualitative business rules ("geen ... als ...").
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

    # Field name: word directly before "veld" (with or without hyphen),
    # else "het <woord> accepteert".
    field = None
    fm = re.search(r"(\w+?)veld", text, re.I)
    if fm:
        field = fm.group(1)
    else:
        fm = re.search(r"(\w+-veld)", text, re.I)
        if fm:
            field = fm.group(1)
        else:
            fm = re.search(r"het\s+([\w-]+)\s+accepteert", text, re.I)
            if fm:
                field = fm.group(1)
    if not field:
        field = "veld"
    field = field.lower().replace("-veld", "").rstrip("s")  # "aantal-veld" -> "aantal"

    ftype = _detect_type(text)

    # Range: "tussen X en Y" or "X tot Y".
    rng = re.search(r"tussen\s+(\d+)\s+en\s+(\d+)", text, re.I) or re.search(
        r"(\d+)\s+tot\s+(\d+)", text, re.I
    )
    fmin = int(rng.group(1)) if rng else None
    fmax = int(rng.group(2)) if rng else None

    # Extra constraints expressed without an operator.
    for mm in re.finditer(r"niet\s+jonger\s+dan\s+(\d+)", text, re.I):
        n = int(mm.group(1))
        fmin = n if fmin is None else max(fmin, n)
    for mm in re.finditer(r"niet\s+ouder\s+dan\s+(\d+)", text, re.I):
        n = int(mm.group(1))
        fmax = n if fmax is None else min(fmax, n)
    for mm in re.finditer(r"jonger\s+dan\s+(\d+)", text, re.I):
        n = int(mm.group(1))
        fmax = (n - 1) if fmax is None else min(fmax, n - 1)
    for mm in re.finditer(r"ouder\s+dan\s+(\d+)", text, re.I):
        n = int(mm.group(1))
        fmin = (n + 1) if fmin is None else max(fmin, n + 1)

    # Rules: "< N" / ">= N" with surrounding reject/accept wording + quoted message.
    # The numeric comparison is attached as a rule for the (single) field regardless
    # of the exact preceding word. We inspect a SHORT window right after the
    # condition for explicit accept/reject verbs (so a later line's wording like
    # "niet-numerieke" does not misclassify this rule), but a LARGER window for
    # the quoted message (which may extend past the verb window).
    rules: list[dict[str, Any]] = []
    for rm in re.finditer(r"(\w+)\s*(<|>=|<=|>|==)\s*(\d+)", text):
        field_token, op, thr = rm.group(1), rm.group(2), int(rm.group(3))
        verb_win = text[rm.end(): rm.end() + 35]
        msg_win = text[rm.end(): rm.end() + 130]
        if re.search(r"geweigerd|afgewezen", verb_win, re.I):
            rejected = True
        elif re.search(r"aangemaakt|akkoord|toegestaan|geaccepteerd|geld", verb_win, re.I):
            rejected = False
        else:
            rejected = op == "<"
        msg = None
        qm = re.search(r"['\"]([^'\"]+)['\"]", msg_win)
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

    # Qualitative business rules: "geen ... als ...", "niet ... als ...",
    # "alleen ... als ..." and "als je een ... bent".
    for line in text.splitlines():
        ls = line.strip("•-\t ").strip()
        if not ls:
            continue
        if re.search(r"[<>]=?\s*\d+", ls):
            continue  # already captured as a numeric rule
        if re.search(r"\b(geen|niet|alleen)\b.*\bals\b", ls, re.I) or re.search(
            r"als je een .+ bent", ls, re.I
        ):
            rules.append(
                {
                    "condition": ls,
                    "expected": "rejected",
                    "message": ls,
                    "qualitative": True,
                }
            )

    # General requirement in the goal sentence, e.g. "ze een man zijn".
    # The negative test ("De bezoeker is geen <noun>") is what we want to assert.
    for m in re.finditer(r"\been\s+(\w+)\s+(zijn|bent|is)\b", text, re.I):
        noun = m.group(1).lower()
        if noun in {"geheel", "heel", "geheel"}:
            continue  # "een geheel getal" is not a requirement
        rules.append(
            {
                "condition": f"een {noun}",
                "expected": "rejected",
                "message": f"De bezoeker is geen {noun}",
                "qualitative": True,
            }
        )

    # De-duplicate rules by message (fallback condition) so the same rule is not
    # captured twice (e.g. once as a bullet and once via the general detector).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rules:
        key = (r.get("message") or r["condition"]).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    rules = deduped

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
        "Een niet-numerieke of ontbrekende leeftijd geeft een validatiefout.\n"
        "Je mag niet jonger zijn dan 0 jaar.\n"
        "Geen account aanmaken als je een alcoholist bent."
    )
    print(json.dumps(parse_fo(sample), indent=2, ensure_ascii=False))
