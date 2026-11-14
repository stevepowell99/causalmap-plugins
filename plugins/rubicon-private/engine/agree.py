"""Record what the evaluator answered when something was put to them to agree, beside what the run held of it then.

    python agree.py <run folder> --what "<what was put to them>" --about <name> [<name> ...] --via "question cards"|chat
                    --answers <JSON file> [--changes "<their words>"]

`--about` names what in the run they agreed: `question` (the question as agreed in `workflow.json`), `documents`
(the ids `corpus/index.csv` lists), `answer` (`answer.md` as it stands) or a step of `workflow.json` by its id, such as
a code step whose columns are the definitions or a judge step holding the rubric. Each is kept as the run holds it now,
in the form the report reads it from the zip, so the report shows what was agreed from the run itself, never from words
the model typed again, and says where it changed afterwards (`render_report.agreed`). A name the run holds nothing
under is refused, so a thing is put in the run before it is asked about. A judge step named is marked as accepted on
the day, which its proposed levels wait on (`judge.py`). `--answers` is a JSON list of each question put to them, as
{"question", "options": [...], "chosen": the option or the words they gave}. The record is added to
`work/agreements.json`, stamped with the time and with how many rows were coded by then, which shows whether it was
agreed before the documents were coded. Prints the record as JSON.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import console  # noqa: E402
from rubicon_open import workflow as W  # noqa: E402

#: How the evaluator's answer reached the run: the question cards the host app gives the model, or the chat
VIA = ("question cards", "chat")
#: What an agreement can name besides a step of the workflow (`render_report.HELD_SAID`)
NAMES = ("question", "documents", "answer")


def read_json(path: Path, empty):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty


def held(run: Path, about: list[str]) -> dict:
    """What the run holds now of each name, as the report will read it: a step as the recount normalises it."""
    wf = read_json(run / "workflow.json", {})
    steps = {s.get("id"): s for s in W.normalise(wf).get("steps", [])}
    out = {}
    for name in about:
        if name == "question":
            value = wf.get("question_as_agreed")
        elif name == "documents":
            with (run / "corpus" / "index.csv").open(encoding="utf-8", newline="") as fh:
                value = [d["id"] for d in csv.DictReader(fh)]
        elif name == "answer":
            value = (run / "answer.md").read_text(encoding="utf-8") if (run / "answer.md").is_file() else None
        else:
            value = steps.get(name)
        if not value:
            raise SystemExit(f"the run holds no {name!r} yet: put it in the run before asking (the definitions as a code "
                             "step's columns and a rubric as a judge step in workflow.json, a draft answer in answer.md); "
                             f"--about names {', '.join(NAMES)} or a step's id in workflow.json")
        out[name] = value
    return out


def agree(run: Path, what: str, about: list[str], via: str, answers: list, changes: str = "") -> dict:
    if via not in VIA:
        raise SystemExit(f"--via is one of {', '.join(VIA)}")
    if not answers or not all(isinstance(a, dict) and a.get("question") and isinstance(a.get("options"), list)
                              and a.get("chosen") for a in answers):
        raise SystemExit('--answers is a JSON list, each {"question", "options": [...], "chosen": the option or words they gave}')
    shown = held(run, about)
    at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    judged = [n for n, v in shown.items() if isinstance(v, dict) and v.get("kind") == "judge"]
    if judged:  # the levels the evaluator has now answered are accepted, on this day
        wf = read_json(run / "workflow.json", {})
        for s in wf.get("steps", []):
            if s.get("id") in judged:
                s["accepted"] = at[:10]
        (run / "workflow.json").write_text(json.dumps(wf, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    rows = sum(len(read_json(p, [])) for p in sorted((run / "coded").glob("*.json"))) if (run / "coded").is_dir() else 0
    record = {"what": what, "held": shown, "asked": True, "via": via, "action": "accept",
              "answers": [{k: a[k] for k in ("question", "options", "chosen")} for a in answers], "changes": changes,
              "at": at, "rows_cited_before": rows}
    (run / "work").mkdir(exist_ok=True)
    records = read_json(run / "work" / "agreements.json", [])
    (run / "work" / "agreements.json").write_text(json.dumps(records + [record], indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8", newline="\n")
    return record


if __name__ == "__main__":
    console.utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--what", required=True)
    ap.add_argument("--about", nargs="+", required=True)
    ap.add_argument("--via", required=True)
    ap.add_argument("--answers", type=Path, required=True)
    ap.add_argument("--changes", default="")
    a = ap.parse_args()
    rec = agree(a.run.resolve(), a.what, a.about, a.via, json.loads(a.answers.read_text(encoding="utf-8")), a.changes)
    print(json.dumps({"recorded": rec["what"], "held": sorted(rec["held"]), "at": rec["at"]}))
