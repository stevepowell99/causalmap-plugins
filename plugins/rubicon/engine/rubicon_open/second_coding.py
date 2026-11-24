"""The run's coding beside the second coder's, by fixed rules, so that a reader can recount from the run's zip how far
two coders working apart agreed and what the check did with each place they differed.

A place is one value of one compared column (`procedure.compared_by_rules`) in one document: a coding applies it where
one of its rows in that document carries the value. Three codings of each code step the second coder coded are set
side by side: the first coder's rows as they were when the two codings were compared (`recode/first/<step>.json`, kept
by `compare.py`), the second coder's (`recode/coded/<step>.json`) and the rows the answer rests on after the check
(`coded/<step>.json`). Agreement is counted over the places where either of two codings applies a value, never over
every document and value, which would count as agreement each value neither coder had any reason to apply.

At each place the first two differ, the rows as they stand place it as exactly one of them did, so fixed rules say
from the rows alone how many differences the check settled each way (`followed`). Where the check also records its
ruling on each place in `recode/rulings.json`, a list of `{"step", "column", "document", "value", "ruled", "why"}`,
`ruled` being one of `RULED` ("first" keeps the first coder's placement, "second" takes the second coder's, "open"
leaves it unsettled), fixed rules say whether every difference is ruled once and whether the rows carry each ruling out.
They also count the places the two coders placed alike that the rows as they stand place otherwise
(`changed_where_alike`), as where the check added a row both coders missed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .procedure import compared_by_rules
from .workflow import value_key

#: The rulings a check records on a place the two coders differ, in the one spelling `ruled_as` gives each
RULED = ("first", "second", "open")
FIRST, RULINGS = "first", "rulings.json"


def ruled_as(v) -> str | None:
    """A ruling as one of `RULED`, however it was written; None for anything else."""
    k = value_key(v)
    return k if k in RULED else None


def held(rows: list[dict], column: str) -> set[tuple[str, str]]:
    """The places a coding applies a column's values: (document, value) for each row carrying a value."""
    return {(r["document"], value_key(r.get(column))) for r in rows if r.get(column) not in (None, "")}


def compared(workflow: dict) -> list[tuple[str, str]]:
    """Each code step's columns that fixed rules compare between two codings, as (step id, column name)."""
    return [(s["id"], c["name"]) for s in workflow.get("steps") or [] if s.get("kind") == "code"
            for c in s.get("columns") or [] if compared_by_rules(c)]


def _rows(p: Path) -> list[dict] | None:
    if not p.is_file():
        return None
    got = json.loads(p.read_text(encoding="utf-8"))
    return got.get("rows") if isinstance(got, dict) else got


def alike(a: set, b: set) -> dict:
    """How far two codings agree over the places either applies a value: how many either applies, and how many both."""
    return {"either": len(a | b), "both": len(a & b)}


def _place(sc: str, d: str, v: str) -> list[str]:
    return [sc, d, v]


def accounted(folder: Path, workflow: dict) -> dict | None:
    """The second coding beside the run's, as `report.json` holds it under `second_coding`; None where the run has no
    second coding."""
    rec = folder / "recode"
    if not (rec / "coded").is_dir():
        return None
    out: dict = {"columns": {}}
    kept_first = (rec / FIRST).is_dir()
    rulings = None
    if (rec / RULINGS).is_file():
        try:
            rulings = json.loads((rec / RULINGS).read_text(encoding="utf-8"))
        except ValueError as e:
            out["rulings_faults"] = [f"recode/{RULINGS} is not JSON: {e}"]
        else:
            if not isinstance(rulings, list):
                out["rulings_faults"] = [f"recode/{RULINGS} is a list of rulings, not a {type(rulings).__name__}"]
                rulings = None
    ruling: dict[tuple[str, str, str], str] = {}
    faults: list[str] = list(out.get("rulings_faults", []))
    for k, r in enumerate(rulings or []):
        place = (f"{r.get('step')}.{r.get('column')}", str(r.get("document")), value_key(r.get("value"))) \
            if isinstance(r, dict) else None
        how = ruled_as(r.get("ruled")) if isinstance(r, dict) else None
        if place is None or how is None:
            faults.append(f"ruling {k + 1} is not read: it names a step, column, document and value, and rules "
                          f"{', '.join(RULED)}")
        elif place in ruling:
            faults.append(f"ruling {k + 1} rules again on {' '.join(place)}")
        else:
            ruling[place] = how
    totals = {"after": {"either": 0, "both": 0}}
    if kept_first:
        totals["before"] = {"either": 0, "both": 0}
    counted, alike_changed = {RULED[0]: 0, RULED[1]: 0, RULED[2]: 0}, {"added": 0, "removed": 0}
    # at each place the two coders differed, the rows as they stand place it as exactly one of them did
    followed = {RULED[0]: 0, RULED[1]: 0}
    not_ruled, not_carried_out, differences = [], [], set()
    for sid, col in compared(workflow):
        second = _rows(rec / "coded" / f"{sid}.json")
        final = _rows(folder / "coded" / f"{sid}.json")
        if second is None or final is None:
            continue
        sc = f"{sid}.{col}"
        hs, hf = held(second, col), held(final, col)
        row = {"after": alike(hf, hs)}
        first = _rows(rec / FIRST / f"{sid}.json") if kept_first else None
        if first is not None:
            h1 = held(first, col)
            row["before"] = alike(h1, hs)
            for d, v in sorted(h1 ^ hs):
                differences.add((sc, d, v))
                followed["first" if ((d, v) in hf) == ((d, v) in h1) else "second"] += 1
                how = ruling.get((sc, d, v))
                if how is None:
                    not_ruled.append(_place(sc, d, v))
                    continue
                counted[how] += 1
                # a ruling for one coder leaves the rows as they stand placing it as that coder did
                if how != "open" and (((d, v) in hf) != ((d, v) in (h1 if how == "first" else hs))):
                    not_carried_out.append(_place(sc, d, v) + [how])
            # where the two coders placed a value alike, any change is the check's own, as for a row both missed
            for d, v in sorted((h1 ^ hf) - (h1 ^ hs)):
                alike_changed["added" if (d, v) in hf else "removed"] += 1
        out["columns"][sc] = row
        for k in row:
            totals[k] = {x: totals[k][x] + row[k][x] for x in ("either", "both")}
    out.update(totals)
    if kept_first and rulings is not None:
        out["rulings"] = {**counted, "not_ruled": not_ruled, "not_carried_out": not_carried_out,
                          "on_no_difference": [list(p) for p in sorted(set(ruling) - differences)]}
    if kept_first:
        out["followed"] = followed
        out["changed_where_alike"] = alike_changed
    if faults:
        out["rulings_faults"] = faults
    return out
