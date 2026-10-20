"""Steps taken from an earlier run: a code step whose result comes from another run's sealed zip.

A code step may carry `"from": {"run_id", "fingerprint", "step", "take"}` in place of its own coding. `fingerprint` is
the one the earlier report prints (the SHA-256 of its zip's `SHA256SUMS`), `step` the id of the code step there (the first 8 characters of the fingerprint, as `rubicon-runs.md` lists them,
are enough where they name one zip, and the recount writes the whole of it into the workflow it ran), which
must be this step's id too, so that every row keeps its id and a citation means the same passage in both runs, and
`take` is `rows` (the default: the earlier run's coded and checked rows) or `definitions` (its columns only, coded
afresh here into `coded/<id>.json`).

The zip is looked for in this run's `earlier/` and then in the run folders beside this one, and is copied into
`earlier/`, so this run's own zip holds it and recounts from itself alone. It is refused unless its seal holds, its
fingerprint is the one named and, for `take: rows`, every document its rows come from reads the same here as in it.
It is refused too where the earlier run takes, however far back, from this run itself, since a loop of runs reading
each other has no first run to recount from: what two questions share belongs in a run both of them read.
Everything else about the step, its columns and settings, comes from the earlier run's workflow, so the recount's
`workflow.json` says what ran.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import zipfile
from pathlib import Path

from .corpus import as_read
from .seal import seal_broken

TAKES = ("rows", "definitions")


def fingerprint_of(path: Path) -> str | None:
    """The fingerprint of a run's zip, None for a file that is not a sealed zip."""
    try:
        with zipfile.ZipFile(path) as z:
            return hashlib.sha256(z.read("SHA256SUMS")).hexdigest()
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


def candidates(folder: Path) -> list[Path]:
    """The zips an earlier run may be in: this run's own `earlier/`, then every run folder beside this one."""
    return sorted((folder / "earlier").glob("*.zip")) + sorted(p for p in folder.parent.glob("*/*.zip")
                                                               if folder not in p.parents)


def found(folder: Path, fingerprint: str) -> dict[str, Path]:
    """Each zip beside this run whose fingerprint starts with the one given (the whole 64 characters, or the first 8 or
    more that `rubicon-runs.md` and a report's file name carry), by its whole fingerprint."""
    out: dict[str, Path] = {}
    for p in candidates(folder):
        fp = fingerprint_of(p)
        if fp and fp.startswith(fingerprint) and fp not in out:
            out[fp] = p
    return out


def find(folder: Path, fingerprint: str) -> Path | None:
    hit = found(folder, fingerprint)
    return next(iter(hit.values())) if len(hit) == 1 else None


def revision_of(z: zipfile.ZipFile) -> int:
    """Which revision of its run a zip holds: 0 for the first report, n for `-revision-n`."""
    try:
        name = json.loads(z.read("render.json").decode("utf-8")).get("name", "")
    except (KeyError, ValueError):
        return 0
    m = re.search(r"-revision-(\d+)$", name)
    return int(m.group(1)) if m else 0


def revised_since(folder: Path, run_id: str, fingerprint: str) -> list[str]:
    """The zips beside this run holding a later revision of the earlier run named, by file name: each is a reason to
    bring this run up to date through a substantive revision."""
    here = find(folder, fingerprint)
    if not here or not run_id:
        return []
    with zipfile.ZipFile(here) as z:
        mine = revision_of(z)
    out = []
    for p in candidates(folder):
        try:
            with zipfile.ZipFile(p) as z:
                wf = json.loads(z.read("workflow.json").decode("utf-8"))
                if wf.get("run_id") == run_id and revision_of(z) > mine:
                    out.append(p.name)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            continue
    return sorted(set(out))


def ancestors(z: zipfile.ZipFile) -> set[str]:
    """The run ids a run's zip takes from, followed through the earlier zips it carries as far back as they go."""
    out = set()
    try:
        wf = json.loads(z.read("workflow.json").decode("utf-8"))
    except (KeyError, ValueError):
        return out
    out |= {str(s["from"]["run_id"]) for s in wf.get("steps", [])
            if isinstance(s.get("from"), dict) and s["from"].get("run_id")}
    for name in z.namelist():
        if name.startswith("earlier/") and name.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(z.read(name))) as e:
                    out |= ancestors(e)
            except zipfile.BadZipFile:
                continue
    return out


def _documents(z: zipfile.ZipFile) -> dict[str, str]:
    """Each document's text in an earlier run's zip, by id."""
    index = csv.DictReader(io.StringIO(z.read("corpus/index.csv").decode("utf-8"), newline=""))
    out = {}
    for d in index:
        name = "corpus/" + (d.get("file") or f"{d['id']}.txt")
        if name in z.namelist():
            out[d["id"]] = as_read(z.read(name).decode("utf-8"))
    return out


def resolve(folder: Path, wf: dict, corpus) -> tuple[dict, dict[str, dict[str, list]], list[str], list[dict]]:
    """The workflow with each taken step filled in from its earlier run; the rows each `take: rows` step takes, by
    document; the faults that stop a step being taken; and what was taken, for the report and the page.

    A step that cannot be taken keeps its `from` and gains no columns, so the recount names it as not recounted rather
    than counting it from nothing."""
    steps, given, faults, taken = [], {}, [], []
    for s in wf.get("steps", []):
        ref = s.get("from")
        if not isinstance(ref, dict):
            steps.append(s)
            continue
        sid, take = s.get("id"), ref.get("take") or "rows"
        fp, there = str(ref.get("fingerprint") or "").lower(), ref.get("step") or s.get("id")

        def fault(why):
            faults.append(f"{sid}: taken from an earlier run, but {why}")
            steps.append(s)

        if s.get("kind") != "code":
            fault("only a code step can be taken; tabulate, judge or map again here from the rows it takes")
            continue
        if take not in TAKES:
            fault(f"take is {take!r}, where it can be {' or '.join(TAKES)}")
            continue
        if there != sid:
            fault(f"it is called {sid!r} here and {there!r} there; give it the earlier id, so each row keeps its id")
            continue
        if not re.fullmatch(r"[0-9a-f]{8,64}", fp):
            fault("its fingerprint is not the one the earlier report prints, or its first 8 characters or more")
            continue
        hit = found(folder, fp)
        if len(hit) != 1:
            fault(f"{'no zip' if not hit else 'more than one zip'} with the fingerprint {fp[:8]}… is in earlier/ or in a "
                  "run folder beside this one" + ("; give more of it" if hit else ""))
            continue
        (fp, path), = hit.items()
        with zipfile.ZipFile(path) as z:
            if broken := seal_broken(z):
                fault(f"{path.name} is not as it was made: " + "; ".join(broken))
                continue
            up = json.loads(z.read("workflow.json").decode("utf-8"))
            mine = wf.get("run_id")
            if mine and (up.get("run_id") == mine or mine in ancestors(z)):
                fault(f"run {up.get('run_id')} already takes from this run ({mine}), so the two would read each other; "
                      "put what both need into a run of its own that both take from")
                continue
            step = next((x for x in up.get("steps", []) if x.get("id") == there), None)
            rec_name = f"steps/{there}.json"
            if not step or step.get("kind") != "code" or rec_name not in z.namelist():
                fault(f"the earlier run has no coded step {there!r}")
                continue
            rec = json.loads(z.read(rec_name).decode("utf-8"))
            texts = _documents(z) if take == "rows" else {}
        stored = folder / "earlier" / f"{up.get('run_id') or 'run'}-{fp[:8]}.zip"
        if path.resolve() != stored.resolve():
            stored.parent.mkdir(exist_ok=True)
            shutil.copy2(path, stored)
        ref = {"run_id": up.get("run_id"), "fingerprint": fp, "step": there, "take": take}
        filled = {k: v for k, v in step.items() if k not in ("from", "inputs", "input")}
        filled.update({"id": sid, "inputs": s.get("inputs") or ["documents"], "from": ref})
        if take == "rows":
            rows = [r for r in rec.get("rows", []) if isinstance(r, dict)]
            read_there = set(rec.get("documents") or {r["document"] for r in rows})
            differ = sorted(d for d in read_there if d in corpus.documents and texts.get(d) != corpus.text(d))
            lacks = sorted(d for d in read_there if d not in corpus.documents)
            if differ or lacks:
                fault("the documents differ: " + "; ".join(
                    ([f"{', '.join(differ)} read differently here"] if differ else [])
                    + ([f"{', '.join(lacks)} not in this run's corpus"] if lacks else [])))
                continue
            given[sid] = {}
            for r in rows:
                given[sid].setdefault(str(r.get("document")), []).append(r)
            ref["documents"] = sorted(read_there)
        steps.append(filled)
        taken.append({"step": sid, "run_id": up.get("run_id"), "fingerprint": fp, "take": take,
                      "question": up.get("question_as_agreed") or "", "zip": f"earlier/{stored.name}"})
    return {**wf, "steps": steps}, given, faults, taken
