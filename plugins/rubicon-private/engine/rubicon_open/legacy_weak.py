"""Reading runs made before 15 October 2026, whose coder marked some rows `weak`.

Until then the engine treated one coding column specially: a row the coder marked `"weak": true` (said to a reader as
"implicit") was counted beside a cell's count rather than in it, as `{cell}.weak`, and a path, told chain or loop counted
for a document only where unmarked rows alone made it. Steve retired that on 15 October 2026: a strength, like any other
quality of a passage, is a column the model defines when the question needs one, and a table splits or filters by it
as by any column. Nothing in the engine knows its name.

Runs made before then still cite `{cell}.weak` counts in their answers, so they keep their reading: a workflow carrying
`KEY` (written by `recount.py` and by `render_report.unpack`, as `cell_ids` is) has its rows' `weak` marks placed and
counted as before, and its report created as before, byte for byte. In any other run `weak` is a column's name like
any other: a coder's `weak` is kept only where a column of that name is defined, as every column's value is, and
nothing reads it as the old mark.

This module is the only door: `steps.place_rows` admits the mark only where `reads(run)` says so, and every reader asks
`carries`, which says no outside such a run. Everything that reads the mark carries the comment `legacy_weak` so it can
be found and deleted with this module once the old runs no longer need recreating: `steps.tabulate`, `_paths`,
`_sequences`, `_loops`, `_markdown` and `counts_of`; `judge._cells` and `judge.markdown`; `procedure.py`;
`render_report.py` and `report.js`/`report.css`; `compare.py`; and the MCP server's column list (`rubicon/mcp/tools.py`).
"""
from __future__ import annotations

import json
from pathlib import Path

#: The workflow's key saying the run was made before the mark was retired
KEY = "legacy_weak_rows"
#: The mark, as a row and a column definition carried it
MARK = "weak"
#: The chain rule in the words the old reports' annex said it in
CHAIN_EXPLICIT = "A path, a chain somebody told or a loop counts as explicit for a document only where explicit links alone can make it."


def reads(run_or_workflow) -> bool:
    """Whether a run (or its workflow) is one made before the mark was retired."""
    if isinstance(run_or_workflow, dict):
        return bool(run_or_workflow.get(KEY))
    return bool(getattr(run_or_workflow, "legacy_weak", False))


def carries(legacy: bool, row: dict) -> bool:
    """Whether a row carries the old mark: only where `legacy` says the run was made before the mark was retired."""
    return bool(legacy) and bool(row.get(MARK))


def in_report(R: dict) -> bool:
    """Whether the run a report is created from (`render_report.load`) was made before the mark was retired."""
    return marked(R.get("workflow"), list((R.get("steps") or {}).values()))


def marked(workflow: dict | None, records: list[dict]) -> bool:
    """Whether a run was made before the mark was retired: its workflow already flagged, or a placed row carrying the
    mark in the step records an earlier recount left (`records`), which only the old engine placed. Where the workflow
    defines a column called `weak`, a row's `weak` is that column's value, and no evidence."""
    if (workflow or {}).get(KEY):
        return True
    if any(isinstance(c, dict) and c.get("name") == MARK for s in (workflow or {}).get("steps") or [] if isinstance(s, dict)
           for c in s.get("columns") or []):
        return False
    return any(r.get(MARK) for rec in records if isinstance(rec, dict) for r in rec.get("rows") or [] if isinstance(r, dict))


def records_in(steps_dir: Path) -> list[dict]:
    """The step records a recount left in `steps_dir`, those that can be read."""
    out = []
    for p in sorted(steps_dir.glob("*.json")) if steps_dir.is_dir() else []:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def flag(workflow: dict, legacy: bool) -> dict:
    """The workflow with `KEY` set where the run is a legacy one, and untouched where it is not."""
    return {**workflow, KEY: True} if legacy else workflow
