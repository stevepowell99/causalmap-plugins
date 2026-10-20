"""Start a run beside its documents: give it its ID and its folder, holding the documents as they are now.

    python start.py <documents folder> --name "<a few words of the question>" --question <file holding the question>
                    [--copy <folder> ...]

The documents are those `corpus/index.csv` in the documents folder lists, each file found in `corpus/` or, where the
documents are already plain-text files in the folder itself, beside it, so a document is never written out again only
to add a fact about it. The run's folder, `<name>-<run id>` in the documents folder, gets its own `corpus/` with every
document copied whole and an index naming the copies, a `workflow.json` holding the question as agreed and the run's
ID, and a copy of each folder `--copy` names, under its own name, such as the plugin's step format and method notes
for the run's readers.
Prints the run's ID and folder as JSON. Refuses a document the index names that neither place holds, and a folder that
already exists, so a run is never started twice under one ID or over another run.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import console  # noqa: E402
from rubicon_open.corpus import BACKGROUND, CORPUS  # noqa: E402
from rubicon_open.run_id import new_run_id  # noqa: E402

def slug(words: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", re.sub(r"['’]", "", words.lower()))[:8]) or "run"


def start(docs: Path, name: str, question: str, copy: list[Path] = ()) -> dict:
    index = docs / CORPUS / "index.csv"
    if not index.is_file():
        raise SystemExit(f"{index} does not exist: write the documents' index first")
    with index.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = list(reader.fieldnames or []), list(reader)
    if not rows or "id" not in fields:
        raise SystemExit(f"{index} lists no documents: it needs an id column and a row for each document")
    found, missing = {}, []
    for r in rows:
        file = (r.get("file") or "").strip() or f"{r['id']}.txt"
        src = next((p for p in (docs / CORPUS / file, docs / file) if p.is_file()), None)
        if src is None:
            missing.append(file)
        found[r["id"]] = src
    if absent := [str(c) for c in copy if not c.is_dir()]:
        raise SystemExit(f"--copy names folders that do not exist: {', '.join(absent)}")
    if missing:
        raise SystemExit(f"{index} names documents found neither in {docs / CORPUS} nor in {docs}: {', '.join(missing)}")
    run_id = new_run_id()
    run = docs / f"{slug(name)}-{run_id}"
    if run.exists():
        raise SystemExit(f"{run} already exists")
    (run / CORPUS).mkdir(parents=True)
    out = []
    for r in rows:
        file = found[r["id"]].name
        shutil.copy2(found[r["id"]], run / CORPUS / file)
        out.append({**r, "file": file})
    if (docs / BACKGROUND).is_dir():
        shutil.copytree(docs / BACKGROUND, run / BACKGROUND)
    columns = fields + ([] if "file" in fields else ["file"])
    with (run / CORPUS / "index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    for c in copy:
        shutil.copytree(c, run / c.name)
    (run / "workflow.json").write_text(json.dumps({"question_as_agreed": question.strip(), "run_id": run_id, "steps": []},
                                                  indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {"run_id": run_id, "folder": str(run), "documents": len(rows)}


if __name__ == "__main__":
    console.utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("documents", type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--question", type=Path, required=True)
    ap.add_argument("--copy", type=Path, nargs="*", default=[])
    a = ap.parse_args()
    print(json.dumps(start(a.documents.resolve(), a.name, a.question.read_text(encoding="utf-8"), [c.resolve() for c in a.copy])))
