"""What a revision makes stale: the paragraphs of an answer that rest on a count or a coded row that changed.

    python stale.py <old recount folder> <new recount folder> <answer.md>

A revision that changes a definition, a step or a coded row is recounted into a new `recount/` folder. This compares
the two folders' `counts.json` and `rows.md`, lists every count and row that changed, appeared or went, and every
count id that now names a different cell of its table, and names each
paragraph of the answer that cites one of them by its {count id} or [row id]. A paragraph whose claim builds on a
finding stated in another section says so with [§ That heading], and it is stale when anything in that section is,
followed through as many sections as the chain runs. Stale paragraphs are read again against the new figures. The
answer's opening paragraph states its conclusion, which rests on everything below it, so it is named whenever anything
moved. A count or row that is only new makes nothing stale, since nothing could cite it before. Exits 1 when anything is stale or a [§ ] reference names no section.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubicon_open.steps import citation_ids


def counts(folder: Path) -> dict:
    return json.loads((folder / "counts.json").read_text(encoding="utf-8"))


def rows(folder: Path) -> dict[str, str]:
    out = {}
    for line in (folder / "rows.md").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\[([^\]]+)\] ", line):
            out[m.group(1)] = line[m.end():]
    return out


def moved(old: dict, new: dict) -> dict[str, str]:
    """Each id whose value changed, appeared or went, with what happened to it."""
    out = {}
    for k in sorted(old.keys() | new.keys()):
        if k not in new:
            out[k] = "gone"
        elif k not in old:
            out[k] = "new"
        elif old[k] != new[k]:
            out[k] = f"{old[k]} → {new[k]}" if not isinstance(old[k], str) or len(str(old[k])) < 40 else "changed"
    return out


def cells(folder: Path) -> dict[str, dict]:
    """What each tabulation cell id stands for: the values that define the cell. An id is a cell's place in its table,
    ordered by count, so the same id can come to name a different cell when counts shift."""
    out = {}
    for f in sorted((folder / "steps").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        for c in rec.get("cells") or [] if rec.get("kind") == "tabulate" else []:
            if "id" in c:
                out[c["id"]] = c.get("values")
    return out


def renamed(old: Path, new: Path, ids) -> dict[str, str]:
    """Each count id, of those given, whose cell now stands for different values, even where its count is the same."""
    was, now = cells(old), cells(new)
    out = {}
    for k in ids:
        cell = next((c for c in was if k == c or k.startswith(c + ".")), None)
        if cell and was.get(cell) != now.get(cell):
            out[k] = f"now counts {now.get(cell)}, was {was[cell]}"
    return out


def paragraphs(text: str) -> list[tuple[str, str]]:
    """Each paragraph with the heading of the section it sits in ("" before the first)."""
    out, section = [], ""
    for p in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not p:
            continue
        if p.startswith("## "):
            section = p.splitlines()[0][3:].strip()
            p = "\n".join(p.splitlines()[1:]).strip()
            if not p:
                continue
        out.append((section, p))
    return out


def stale(old: Path, new: Path, answer: str) -> tuple[dict[str, str], list[tuple[int, str, list[str]]], list[str]]:
    """What moved; each stale paragraph with what made it stale; and [§ ] references naming no section.

    A paragraph is stale when it cites a count or row that moved, or refers with [§ Heading] to a section holding a
    stale paragraph, however many sections deep the chain runs; the opening conclusion is stale whenever anything is."""
    changes = {**moved(counts(old), counts(new)), **moved(rows(old), rows(new))}
    changes = {**renamed(old, new, counts(old).keys() | counts(new).keys()), **changes}
    # a count or row that is only new cannot have been cited before, so it makes nothing stale: it is what a revision
    # adds, and the paragraph citing it is the revision's own
    moving = {k: v for k, v in changes.items() if v != "new"}
    paras = [(sec, p) for sec, p in paragraphs(answer) if not p.startswith("# ")]
    sections = {sec for sec, _ in paras if sec} | {ln[3:].strip() for ln in answer.splitlines() if ln.startswith("## ")}
    why: dict[int, list[str]] = {}
    for n, (_, p) in enumerate(paras):
        ids = set(re.findall(r"\{([\w-]+\.[\w.-]+)\}", p)) | {c for c in citation_ids(p) if not c.startswith("§")}
        if hit := sorted(i for i in ids if i in moving):
            why[n] = hit
    refs = {n: {r.strip() for r in re.findall(r"\[§\s*([^\]]+)\]", p)} for n, (_, p) in enumerate(paras)}
    while True:  # follow claims built on claims until nothing more turns stale
        stale_sections = {paras[n][0] for n in why if paras[n][0]}
        more = {n: [f"§ {r}" for r in sorted(refs[n] & stale_sections)] for n in refs
                if n not in why and refs[n] & stale_sections}
        if not more:
            break
        why.update(more)
    if moving and paras and 0 not in why:
        why[0] = []
    broken = sorted({r for rs in refs.values() for r in rs} - sections)
    return changes, [(n, paras[n][1], why[n]) for n in sorted(why)], broken


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # a Windows console is not UTF-8, and the output names documents and arrows
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    changes, hits, broken = stale(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).read_text(encoding="utf-8"))
    print(f"{len(changes)} counts or rows moved" + (":" if changes else "; nothing in the answer is stale."))
    for k, v in changes.items():
        print(f"  {k}: {v}")
    for n, p, hit in hits:
        why = (f"rests on {', '.join(hit)}" if hit else "the conclusion, which rests on everything below it")
        print(f"\nSTALE paragraph {n + 1} ({why}):\n  {p[:160]}{'…' if len(p) > 160 else ''}")
    for r in broken:
        print(f"\n[§ {r}] names no section of the answer, so what rests on it cannot be followed: fix the reference.")
    sys.exit(1 if hits or broken else 0)
