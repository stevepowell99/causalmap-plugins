"""How closely two codings of the same workflow agree, document by document and value by value.

    python compare.py <first folder> <second folder>

Each folder holds a coding of the same workflow's steps, either recounted (`recount/steps/`, as `recount.py` leaves it)
or run (`steps/`, as the engine's coders leave it): the first is the analyst's, the second the second coder's. For each
code step and column, each document either holds a value (has a row coded with it) or does not, in each of the two
codings: agreement is counted over every document and value, with the documents on which the two differ named. For
each tabulation, the cells whose counts differ, by the same cell ids. Writes compare.json beside the second coding and
prints it, and disagreements.md: each document and value one coder placed and the other did not, and each both placed
but one only weakly (a row marked weak, by the weakness its column's definition names), with the passages each coder
gave for that document, for a reviewer to rule on against the text.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open.workflow import value_key


def steps_of(folder: Path) -> Path:
    return folder / "recount" / "steps" if (folder / "recount" / "steps").is_dir() else folder / "steps"


def compare(a: Path, b: Path) -> dict:
    wf = json.loads(((b if (b / "workflow.json").exists() else a) / "workflow.json").read_text(encoding="utf-8"))
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    sa, sb = steps_of(a), steps_of(b)
    out = {"coding": {}, "tables": {}}
    disagreements: list[str] = []
    for s in wf["steps"]:
        sid = s["id"]
        if s["kind"] == "code":
            ra, rb = load(sa / f"{sid}.json"), load(sb / f"{sid}.json")
            docs = sorted(set(rb.get("documents") or []) | set(ra.get("documents") or [])
                          | {r["document"] for r in ra["rows"] + rb["rows"]})
            for c in s.get("columns") or []:
                if c.get("type") == "free_text":
                    continue
                held = lambda rec: {(r["document"], value_key(r.get(c["name"]))) for r in rec["rows"]
                                    if r.get(c["name"]) not in (None, "")}
                ha, hb = held(ra), held(rb)
                values = sorted({v for _, v in ha | hb})
                cells = [(d, v) for d in docs for v in values]
                both = sum((x in ha) and (x in hb) for x in cells)
                agree = sum((x in ha) == (x in hb) for x in cells)
                pa, pb = len(ha) / len(cells) if cells else 0, len(hb) / len(cells) if cells else 0
                pe = pa * pb + (1 - pa) * (1 - pb)
                for who, mine, theirs, rec, other in (("first coder", ha, hb, ra, rb), ("second coder", hb, ha, rb, ra)):
                    for d, v in sorted(mine - theirs):
                        quotes = [r["quote"] for r in rec["rows"] if r["document"] == d and value_key(r.get(c["name"])) == v]
                        said = [f"{r.get(c['name'])}: \"{r['quote']}\"" for r in other["rows"] if r["document"] == d]
                        disagreements.append(f"- **{sid}.{c['name']} = {v}**, document {d}: coded by the {who} only.\n"
                                             f"    - The {who}'s passages: " + " / ".join(f"\"{q}\"" for q in quotes) + "\n"
                                             f"    - The other coder's rows for {d} in this step: " + (" / ".join(said) or "none"))
                firm = lambda rec: {(r["document"], value_key(r.get(c["name"]))) for r in rec["rows"]
                                    if r.get(c["name"]) not in (None, "") and not r.get("weak")}
                fa, fb = firm(ra), firm(rb)
                strength = sorted(x for x in ha & hb if (x in fa) != (x in fb))
                for d, v in strength:
                    said = lambda rec: " / ".join(f"\"{r['quote']}\"" + (" (weak)" if r.get("weak") else "")
                                                  for r in rec["rows"] if r["document"] == d and value_key(r.get(c["name"])) == v)
                    disagreements.append(f"- **{sid}.{c['name']} = {v}**, document {d}: firm for the "
                                         f"{'first' if (d, v) in fa else 'second'} coder, weak for the "
                                         f"{'second' if (d, v) in fa else 'first'}.\n"
                                         f"    - The first coder's passages: {said(ra)}\n"
                                         f"    - The second coder's passages: {said(rb)}")
                out["coding"][f"{sid}.{c['name']}"] = {
                    "document_value_pairs": len(cells), "agree": agree, "held_by_first": len(ha), "held_by_second": len(hb),
                    "held_by_both": both, "kappa": round((agree / len(cells) - pe) / (1 - pe), 2) if cells and pe < 1 else None,
                    "first_only": sorted(f"{d}: {v}" for d, v in ha - hb), "second_only": sorted(f"{d}: {v}" for d, v in hb - ha),
                    "firm_for_one_weak_for_other": [f"{d}: {v}" for d, v in strength]}
        elif s["kind"] in ("tabulate", "judge") and (sa / f"{sid}.json").exists() and (sb / f"{sid}.json").exists():
            ta, tb = load(sa / f"{sid}.json"), load(sb / f"{sid}.json")
            if s["kind"] == "tabulate":
                ca, cb = {c["id"]: c["n"] for c in ta["cells"] if "id" in c}, {c["id"]: c["n"] for c in tb["cells"] if "id" in c}
                diff = {k: [ca.get(k), cb.get(k)] for k in sorted(set(ca) | set(cb)) if ca.get(k) != cb.get(k)}
                out["tables"][sid] = {"cells": len(set(ca) | set(cb)), "differ": len(diff), "first_vs_second": diff}
            else:
                out["tables"][sid] = {"verdict": [ta.get("verdict"), tb.get("verdict")],
                                      "criteria": {c["id"]: [c.get("level"), d.get("level")]
                                                   for c, d in zip(ta.get("criteria") or [], tb.get("criteria") or [])}}
    (b / "compare.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    (b / "disagreements.md").write_text("\n".join(disagreements) + "\n" if disagreements
                                        else "The two coders placed every document and value alike.\n", encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # a Windows console is not UTF-8, and the output names documents and arrows
    print(json.dumps(compare(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()), indent=1, ensure_ascii=False))
