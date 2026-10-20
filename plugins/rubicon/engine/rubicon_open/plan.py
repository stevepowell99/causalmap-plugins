"""The design the evaluator agreed, as `rubicon-plan.md` records it beside the documents (the plugin's skill writes it).

A combined report takes its order and each run's role from the plan, never from a run's name or from the order its files
were found in. Of the plan's tables, those with an `Answered by run` column are read: one row for each question, shared
step or background run, in the order the plan lists them.

- The first column labels the row.
- `Role` (or `Kind`) says what the run is, by its first word: `question`, `shared` (steps other runs take, answering
  nothing) or `background` (an answer that is context for the others rather than one of their questions), so "shared, new"
  is shared. Where the table has no such column, a label of the form `Q1`, `Q2` marks a question, and any other label gives
  the row no role, which the caller refuses by name.
- `Answered by run` holds the run's ID (`2026-10-12-xbrj`) and may hold its fingerprint; a row whose cell holds neither has
  not been answered yet and is skipped.
- A column headed `Question`, `Name`, `Title` or `What` gives the row's words, which name a run that has no question of its own.
"""
from __future__ import annotations

import re
from pathlib import Path

from .run_id import ID

PLAN = "rubicon-plan.md"
ROLES = ("question", "shared", "background")
FINGERPRINT = re.compile(r"\b[0-9a-f]{8}\b")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read(documents) -> list[dict]:
    """The plan's rows that name a run, in plan order, each as {label, role, title, runs, fingerprints, line}; empty where
    the folder has no plan or the plan names no run."""
    f = Path(documents) / PLAN
    if not f.is_file():
        return []
    lines, out, i = f.read_text(encoding="utf-8").splitlines(), [], 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            j += 1
        table = [cells(l) for l in lines[i:j]]
        i = j
        head = [h.lower() for h in table[0]]
        run = next((n for n, h in enumerate(head) if "run" in h), None)
        if run is None or len(table) < 3:
            continue
        role = next((n for n, h in enumerate(head) if h in ("role", "kind")), None)
        words = next((n for n, h in enumerate(head) if h.split(" ")[0].strip("(") in ("question", "name", "title", "what")), None)
        for row in table[2:]:
            row = row + [""] * (len(head) - len(row))
            runs, prints = ID.findall(row[run]), FINGERPRINT.findall(row[run])
            if not runs and not prints:
                continue
            label = row[0].replace("*", "").strip()
            said = (re.findall(r"[a-z]+", row[role].lower()) or [""])[0] if role is not None else ""
            out.append({"label": label, "title": row[words] if words is not None else "", "runs": runs, "fingerprints": prints,
                        "role": said if said in ROLES else "question" if role is None and re.fullmatch(r"Q\d+", label) else None})
    return out


def entry_for(entries, run_id: str = "", fingerprint: str = ""):
    """The plan row that names a run: by its ID, which stays the same through every revision, else by a fingerprint it
    names, which only the version it was written for carries."""
    for e in entries:
        if run_id and run_id in e["runs"]:
            return e
    for e in entries:
        if fingerprint and any(fingerprint.startswith(p) for p in e["fingerprints"]):
            return e
    return None
