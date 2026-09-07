"""OpenCode client: spawn the local opencode run (model big-pickle, default config
at /root) and ask it to consult the Test Assistent MCP server (testassist).

The opencode.json at /root/.config/opencode already registers the testassist
MCP server, so a local `opencode run` session has access to all 8 tools.
We capture the JSON event stream to extract the final assistant text and the
MCP tools that were actually invoked.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

OPENCODE_BIN = "/root/.opencode/bin/opencode"
DEFAULT_MODEL = "opencode/big-pickle"
DEFAULT_CWD = "/root"


def ask(
    prompt: str,
    model: str = DEFAULT_MODEL,
    cwd: str = DEFAULT_CWD,
    title: str = "fo-bdd-demo",
    timeout: int = 600,
) -> dict[str, Any]:
    cmd = [
        OPENCODE_BIN,
        "run",
        "-m",
        model,
        "--format",
        "json",
        "--auto",
        "--dir",
        cwd,
        "--title",
        title,
        prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    texts: list[str] = []
    tools: list[str] = []
    session: str | None = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if session is None and ev.get("sessionID"):
            session = ev["sessionID"]
        part = ev.get("part") or {}
        if ev.get("type") == "text":
            txt = part.get("text")
            if txt:
                texts.append(txt)
        elif ev.get("type") in ("tool", "tool_use"):
            tn = part.get("tool") or part.get("name")
            if tn:
                tools.append(tn)

    return {
        "text": "".join(texts),
        "tools": list(dict.fromkeys(tools)),
        "session": session,
        "returncode": proc.returncode,
        "stderr_tail": proc.stderr[-400:] if proc.stderr else "",
    }


if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: PONG"
    r = ask(prompt, timeout=120)
    print("text:", repr(r["text"])[:300])
    print("tools:", r["tools"])
    print("session:", r["session"])
    if r["returncode"] != 0:
        print("stderr tail:", r["stderr_tail"])
