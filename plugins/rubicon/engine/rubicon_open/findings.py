"""The sensitivity of each finding an answer states from its counts, worked out by fixed rules: whether it holds,
and its fragility index.

A finding that rests on counts says something of them: that one is larger than another, that a count reaches a share
of its base, that none or all of a group did something. Its words are the writer's, in any language, and fixed rules
never read them. What a finding says of its counts is recorded as data, in `judged/findings.json`:

    {"<finding id>": {"says": "<the finding, in a line>", "where": "<the heading it is set out under>",
                      "holds": [<each comparison the finding needs, all of which must hold>]}}

A comparison names a count by the id the answer writes for it, and what it is compared with:

    {"count": "<id>", "op": ">", "than": "<id>"}      two counts, as shares of their bases ("as": "n" compares the counts)
    {"count": "<id>", "op": ">=", "n": 3}             a count against a number
    {"count": "<id>", "op": ">=", "share": 0.5}       a count against a share of its own base

`op` is one of `OPS`. "None of them" is `{"op": "==", "n": 0}`, "all of them" `{"op": "==", "share": 1}`. A finding that
says nothing a comparison can state, such as how something works, is a key claim (a claims step), not a finding here.

For each finding the recount says whether every comparison holds, and its margin: the fewest of the units counted
(documents, cases, or whatever the table counts) placed otherwise that would make one of its comparisons fail, each
count's base held, out of the units in the bases of the counts it compares, each once (`out_of`). A unit placed otherwise
moves one count by one, in or out; where the two counts are cells of one table that differ only in a column their
bases are not taken within, and no unit is in both, moving a unit from one to the other is one placement and moves
both (`_one_placement`). This is the margin of the knowledge page
`probative-value.md` (the fragility index of medical trials), taken to the answer's own findings: it says how many
placements a finding turns on, not how likely any of them is to be wrong, and a finding whose comparison does not hold
says more than its counts.

The file lives in `judged/` so that a run's zip carries it and a recount from the zip alone works out the same
margins; a step may therefore not be called `findings`.
"""
from __future__ import annotations

import json
import operator
from fractions import Fraction
from pathlib import Path

from .units import _one

FILE = "findings.json"
OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}
#: How many of the nearest ways to end a finding are listed, and up to which margin the units each would move are named
SHOWN, NAMED_UP_TO = 4, 2
#: How many units placed otherwise are tried at most: a finding that more would be needed to end is robust on any
#: reading, and the report says that more than this many would be needed rather than giving a number
SEARCHED = 60


def read(folder: Path, steps: list[dict]) -> tuple[dict | None, list[str]]:
    """The findings recorded for a run, and what is wrong with the file as a whole; None where there is no file."""
    f = folder / "judged" / FILE
    if not f.is_file():
        return None, []
    if any(s.get("id") == FILE.removesuffix(".json") for s in steps):
        return None, [f"a step is called {FILE.removesuffix('.json')}, so judged/{FILE} is read as that step's and no "
                      "finding's margin is worked out: rename the step"]
    try:
        got = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, [f"judged/{FILE} is not JSON: {e}"]
    if not isinstance(got, dict):
        return None, [f"judged/{FILE} is an object of findings by id, not a {type(got).__name__}"]
    return got, []


def parts(run) -> dict[str, dict]:
    """Every count a finding can name, by the id an answer writes for it (`steps.counts_of`): its count, its base, the
    units it holds where the record lists them, which units its base is made of (`members`, None where that is not
    worked out), and for a table's cell, the table, the cell's values and the columns its base is taken within
    (`steps.recorded_base_columns`), which say whether a unit can move between two cells as one placement. A count
    within one of a cell's columns ({<id>.within.<column>}) is out of the units with that column's value, so moving a
    unit to another value of that column would change its base, and it never moves as one."""
    from .judge import level_counts, unit_of
    from .steps import base_of, recorded_base_columns, unit_of_table
    out = {}
    for sid, rec in run.out.items():
        if rec.get("kind") == "tabulate":
            cols = recorded_base_columns(rec, run.out, run.corpus.columns)
            held, noun, members = set(cols), unit_of_table(rec), _base_members(run, rec, cols)
            for c in rec["cells"]:
                if "id" not in c:
                    continue
                units = list(c.get("cases") or c.get("documents") or [])
                out[c["id"]] = {"n": c["n"], "base": base_of(rec, c), "units": units, "table": sid,
                                "values": c.get("values") or {}, "held": held, "noun": noun, "members": members(c)}
                for col, b in (c.get("within") or {}).items():
                    out[f"{c['id']}.within.{col}"] = {"n": c["n"], "base": b, "units": units, "table": sid,
                                                      "values": c.get("values") or {}, "held": held | {col}, "noun": noun,
                                                      "members": None}
        elif rec.get("kind") == "judge":
            for c in rec.get("criteria") or []:
                if c.get("kind") == "rule":
                    for k, x in level_counts(sid, c).items():
                        own = k == f"{sid}.{c['id']}"
                        out[k] = {"n": x["n"], "base": x["base"], "units": list(c.get("documents") or []) if own else [],
                                  "noun": unit_of(c), "members": None}
    return out


def _base_members(run, rec: dict, cols: list[str]):
    """Which units each cell of a tabulation is out of, worked out as `steps.tabulate` works out its base: the units it
    read whose documents take the cell's value in every column the base is taken within (`cols`). None for a count of
    passages, and for a cell where the units found here do not number its recorded base, so that a finding is never
    said to be out of a set its own count is not out of."""
    from .steps import base_of, rows_read, unit_values, units
    src, count = rec.get("input"), rec.get("count", "documents")
    if count == "rows" or not src:
        return lambda c: None
    try:
        rows, read = rows_read(run, src)
    except (KeyError, ValueError):
        return lambda c: None
    listing = src == "documents" or run.out.get(src, {}).get("kind") == "sample"
    held, _ = units(run, count, read, [] if listing else rows, run.out.get(src, {}).get("kind") == "profile")

    def members(c):
        values = c.get("values") or {}
        got = frozenset(u for u, docs in held.items() if all(values.get(k) in unit_values(run, docs, k) for k in cols))
        return got if len(got) == base_of(rec, c) else None
    return members


def out_of(f: dict, known: dict) -> int | None:
    """How many units the counts a finding compares are out of, each counted once: the units in the base of any count
    one of its comparisons names, which are the units whose coding the finding turns on. None where the base of one of
    them is not worked out (`parts`)."""
    ids = {c[k] for c in f["holds"] for k in ("count", "than") if k in c}
    sets = [known[i].get("members") for i in ids]
    return len(frozenset().union(*sets)) if sets and all(s is not None for s in sets) else None


def _operand(comp: dict, known: dict) -> tuple[str, object] | str:
    """What a comparison compares its count with, or why it cannot be read."""
    given = [k for k in ("than", "n", "share") if k in comp]
    if len(given) != 1:
        return "names exactly one of than, n and share"
    k = given[0]
    v = comp[k]
    if k == "than":
        return ("than", v) if v in known else f"compares with {v!r}, which no cell or rule makes"
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return f"gives {k} as {v!r}, not a number"
    if k == "share" and not 0 <= v <= 1:
        return f"gives a share of {v}, outside 0 to 1"
    return k, v


def _fault(comp, known: dict) -> str | None:
    if not isinstance(comp, dict):
        return "is not an object"
    if comp.get("count") not in known:
        return f"names the count {comp.get('count')!r}, which no cell or rule makes"
    if comp.get("op") not in OPS:
        return f"has op {comp.get('op')!r}, not one of {' '.join(OPS)}"
    if comp.get("as", "share") not in ("share", "n"):
        return f"has as {comp['as']!r}, not share or n"
    o = _operand(comp, known)
    if isinstance(o, str):
        return o
    if o[0] == "share" and not known[comp["count"]]["base"]:
        return "compares a share of a count that has no base"
    return None


def _as(comp: dict, known: dict) -> str:
    """Whether two counts are compared as shares or as counts: as shares unless the finding says counts, or either
    count has no base."""
    return comp.get("as", "share") if known[comp["count"]]["base"] and known[comp["than"]]["base"] else "n"


def _holds(comp: dict, known: dict, n: dict) -> bool:
    a = known[comp["count"]]
    kind, v = _operand(comp, known)
    if kind == "than":
        b, as_ = known[v], _as(comp, known)
        left = Fraction(n[comp["count"]], a["base"]) if as_ == "share" else Fraction(n[comp["count"]])
        right = Fraction(n[v], b["base"]) if as_ == "share" else Fraction(n[v])
        return OPS[comp["op"]](left, right)
    left = Fraction(n[comp["count"]], a["base"]) if kind == "share" else Fraction(n[comp["count"]])
    return OPS[comp["op"]](left, Fraction(v).limit_denominator(10 ** 6))


def _one_placement(a: dict, b: dict) -> bool:
    """Whether a unit can move from one count to the other as one placement: two cells of one table with the same base
    that differ in the value of one column, which is not a column their bases are taken within (a column of the
    document list, which nobody places, or one that defines the group they are out of), and that share no unit."""
    if "table" not in a or a.get("table") != b.get("table") or a["base"] != b["base"] or set(a["values"]) != set(b["values"]):
        return False
    differ = [k for k in a["values"] if a["values"][k] != b["values"][k]]
    return (len(differ) == 1 and differ[0] not in a["held"] | b["held"]
            and not set(a["units"]) & set(b["units"]))


def _fewest(comp: dict, known: dict) -> tuple[int, list[dict]] | tuple[None, int] | None:
    """The fewest units placed otherwise that would make a comparison that holds fail, and the ways of doing it with
    that many: each as the counts that gain or lose units (`singles`) and, where a unit can move between the two counts
    as one placement, how many move and which way (`between`). None where no placement of the units could end it, and
    (None, `SEARCHED`) where none of up to `SEARCHED` would, though more might."""
    ids = [comp["count"]] + ([comp["than"]] if "than" in comp and comp["than"] != comp["count"] else [])
    n0 = {i: known[i]["n"] for i in ids}
    top = {i: known[i]["base"] for i in ids}
    room = sum(b for b in top.values() if b is not None) if all(b is not None for b in top.values()) else None
    limit = min(SEARCHED, room) if room is not None else SEARCHED
    two = len(ids) == 2
    moving = two and _one_placement(known[ids[0]], known[ids[1]])
    whole = {i: x["n"] for i, x in known.items()}
    for k in range(1, limit + 1):
        found = []
        for t in range(0, k + 1) if moving else (0,):
            for frm, to in ((ids[0], ids[1]), (ids[1], ids[0])) if t else ((None, None),):
                s = k - t
                for da in range(-s, s + 1):
                    rest = s - abs(da)
                    for db in ({rest, -rest} if two else ({0} if rest == 0 else set())):
                        singles = {ids[0]: da, **({ids[1]: db} if two else {})}
                        n = dict(singles)
                        if t:
                            n[frm] -= t
                            n[to] += t
                        n = {i: n0[i] + n[i] for i in ids}
                        if any(n[i] < 0 or (top[i] is not None and n[i] > top[i]) for i in ids):
                            continue
                        if not _holds(comp, known, {**whole, **n}):
                            way = {"singles": {i: d for i, d in singles.items() if d},
                                   **({"between": {"from": frm, "to": to, "units": t}} if t else {})}
                            if way not in found:
                                found.append(way)
        if found:
            return k, found
    return None if limit == room else (None, limit)


def assess(found: dict, known: dict) -> tuple[list[dict], list[str]]:
    """Each finding recorded, with whether each of its comparisons holds and its margin; and what in the file cannot be
    read, by finding. A finding with a comparison that cannot be read is not assessed at all, so that a margin is never
    worked out from part of what the finding needs."""
    out, faults = [], []
    whole = {i: x["n"] for i, x in known.items()}
    for fid, f in found.items():
        if not isinstance(f, dict) or not isinstance(f.get("holds"), list) or not f["holds"]:
            faults.append(f"finding {fid} gives no comparisons under holds")
            continue
        bad = [(i, why) for i, c in enumerate(f["holds"]) if (why := _fault(c, known))]
        if bad:
            faults += [f"finding {fid}, comparison {i + 1}, {why}" for i, why in bad]
            continue
        comps = []
        for c in f["holds"]:
            ok = _holds(c, known, whole)
            near = _fewest(c, known) if ok else None
            comps.append({**c, "holds_now": ok,
                          **({"margin": near[0], "nearest": near[1][:SHOWN]} if near and near[0] is not None
                             else {"margin_over": near[1]} if near else {})})
        holding = all(c["holds_now"] for c in comps)
        # the comparison nearest to failing sets the finding's margin, and names what its units are
        nearest = (min((c for c in comps if "margin" in c), key=lambda c: c["margin"], default=None)
                   or min((c for c in comps if "margin_over" in c), key=lambda c: c["margin_over"], default=None))
        of = out_of(f, known) if holding and nearest else None
        out.append({"id": str(fid), "says": str(f.get("says", "")), "where": str(f.get("where", "")), "comparisons": comps,
                    "holds": holding,
                    **({"margin": nearest["margin"]} if holding and nearest and "margin" in nearest
                       else {"margin_over": nearest["margin_over"]} if holding and nearest else {}),
                    **({"noun": known[nearest["count"]].get("noun") or "units"} if holding and nearest else {}),
                    **({"of": of} if of is not None else {})})
    return out, faults


def counts(assessed: list[dict]) -> dict[str, str]:
    """The margins an answer may state, by the id it writes for each, as for any count."""
    return {f"findings.{a['id']}.margin": str(a["margin"]) for a in assessed if "margin" in a}


def _said(i: str, known: dict) -> str:
    x = known[i]
    return f"{i} ({x['n']}" + (f" of {x['base']})" if x["base"] is not None else ")")


def _comparison_in_words(c: dict, known: dict) -> str:
    if "than" in c:
        return (f"{_said(c['count'], known)} {c['op']} {_said(c['than'], known)}, "
                f"as {'shares' if _as(c, known) == 'share' else 'counts'}")
    return f"{_said(c['count'], known)} {c['op']} " + (f"a share of {c['share']}" if "share" in c else str(c["n"]))


def _units(i: str, known: dict, k: int) -> str:
    return f" (one of {', '.join(known[i]['units'])})" if k <= NAMED_UP_TO and known[i]["units"] else ""


def _way_in_words(way: dict, known: dict, k: int) -> str:
    said = []
    if "between" in way:
        b = way["between"]
        said.append(f"{b['units']} moved from {b['from']} to {b['to']}{_units(b['from'], known, k)}")
    for i, d in way["singles"].items():
        said.append(f"{abs(d)} {'fewer' if d < 0 else 'more'} in {i}" + (_units(i, known, k) if d < 0 else ""))
    return " and ".join(said)


def _under_second(fid: str, second: dict) -> str:
    """What the second coder's rows say of one finding (`second` as the recount gives it)."""
    if "error" in second:
        return "not worked out, since the recount of those rows failed"
    if fid in second.get("not_assessed", []):
        return "not read, since a count it names is not in that coding"
    if fid in second.get("not_holding", []):
        return "DOES NOT HOLD"
    e = next((e for e in second.get("each", []) if e["id"] == fid), {})
    if "margin" in e:
        return f"holds, with a margin of {e['margin']}"
    if "margin_over" in e:
        return f"holds, and none of up to {e['margin_over']} placed otherwise would end it"
    return "holds, and no placement of the units would end it"


def markdown(assessed: list[dict], faults: list[str], known: dict, second: dict | None = None) -> str:
    """The findings as the check reads them in `recount/tables.md`: each comparison, whether it holds, and the margin
    by the id an answer writes for it, with the nearest ways to end the finding and, for a margin of one or two, the
    units each would move; and where a second coder coded the documents apart from the first, whether the finding
    holds on that coder's rows (`second`)."""
    lines = ["## Findings", "",
             f"Each finding recorded in judged/{FILE}, with whether each comparison it needs holds, and its margin: the fewest "
             "units placed otherwise, each count's base held, that would end it."
             + (f" Each also says whether it holds on the rows the second coder coded apart from the first, counted in "
                f"place of the first coder's for {', '.join(second['steps'])}." if second else ""), ""]
    for a in assessed:
        lines.append(f"- **{a['id']}**" + (f" (under \"{a['where']}\")" if a["where"] else "") + (f": {a['says']}" if a["says"] else ""))
        for c in a["comparisons"]:
            state = "holds" if c["holds_now"] else "DOES NOT HOLD, so the finding says more than its counts"
            if "margin" in c:
                state += (f"; {c['margin']} {_one(c['margin'], known[c['count']].get('noun') or 'units')} placed otherwise "
                          "would end it: "
                          + "; or ".join(_way_in_words(w, known, c["margin"]) for w in c["nearest"]))
            elif "margin_over" in c:
                state += f"; none of up to {c['margin_over']} placed otherwise would end it"
            elif c["holds_now"]:
                state += "; no placement of the units would end it"
            lines.append(f"    - {_comparison_in_words(c, known)}: {state}")
        if "margin" in a:
            lines.append(f"    - Margin: {{findings.{a['id']}.margin}} ({a['margin']})")
        if second:
            lines.append(f"    - On the second coder's rows: {_under_second(a['id'], second)}")
    lines += [f"- Not read: {x}" for x in faults]
    return "\n".join(lines)


#: What `report` gives of each finding assessed, so that a report can show them without the comparisons
EACH = ("id", "says", "where", "holds", "margin", "margin_over", "noun", "of")


def report(found: dict, assessed: list[dict], faults: list[str]) -> dict:
    """What the recount's report says of the findings: how many were recorded and assessed, which say more than
    their counts, each margin, what could not be read, and each finding assessed, in the order recorded, with its
    words, whether it holds, its margin (`margin`, or `margin_over` where none of that many units would end it, or
    neither where no placement could), what the units of its margin are (`noun`) and how many units its counts are
    out of (`of`, from `out_of`, where that is worked out)."""
    return {"recorded": len(found), "assessed": len(assessed),
            "not_holding": [a["id"] for a in assessed if not a["holds"]],
            "margins": {a["id"]: a["margin"] for a in assessed if "margin" in a},
            "each": [{k: a[k] for k in EACH if k in a} for a in assessed],
            **({"not_read": faults} if faults else {})}
