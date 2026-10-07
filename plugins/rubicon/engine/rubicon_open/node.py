"""Run one of the engine's own Node scripts on a JSON payload and read its JSON reply.

The engine reaches Causal Map's code (the quote matcher, the link filters) through copies kept in this folder, run under
Node, so the plugin carries one implementation of each rather than a Python twin."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def call(script: Path, payload: dict, what: str):
    proc = subprocess.run(["node", str(script)], input=json.dumps(payload), capture_output=True, text=True,
                          encoding="utf-8", cwd=str(script.parent))
    if proc.returncode != 0:
        # A broken script must never look like "nothing matched" or "nothing survived".
        raise RuntimeError(f"{what} failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)
