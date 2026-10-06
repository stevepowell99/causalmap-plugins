"""Recount a Free+W folder with Rubicon's own pieces, by code alone.

    python recount.py <folder> [--answer answer.md]

The folder holds `corpus/` (the documents and `index.csv`), `workflow.json` (a workflow of pieces: sample, code,
tabulate, judge, write) and `coded/<code step id>.json`, the rows the analyst coded for each code step: a JSON list of
{"document", "quote", <each column>: value}. Each code step places the analyst's rows exactly as a run places a
model's (`steps.code_given`), so every quotation is found in its document (and dropped, and listed, where it is not),
every value is checked against its column's values and stored in one spelling, and a per-document step's values become
document attributes. The tabulate and judge steps then
run as they do in any run. Nothing calls a model.

Writes `recount/`: `steps/<id>.json`, `rows.md` (every row with its id), `tables.md` (every table and verdict with
the ids of its cells), `counts.json`, `report.json`. With `--answer`, the answer's {cell ids} are replaced with their
counts as the write step does (`answer.resolved.md`), and the report adds ids naming no cell, numbers written bare,
row citations naming no row, quotations found in no document and quotations not in what they cite. `recount/` is then
a run's folder in the open format (`rubicon/docs/open-format.md`), with `workflow.json`, `run.json` and the write
step's record beside the others, so the page draws it as it draws any run of pieces.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as the analyst's does
from rubicon_open.corpus import load_corpus
from rubicon_open import locator
from rubicon_open import steps as S
from rubicon_open import workflow as W
from rubicon_open.judge import judge, markdown as judge_markdown

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--answer")
a = ap.parse_args()
folder = Path(a.folder).resolve()
out = folder / "recount"
out.mkdir(exist_ok=True)
for p in out.iterdir():  # a recount starts clean, so nothing from an earlier one outlives an edited row
    shutil.rmtree(p) if p.is_dir() else p.unlink()
(out / "steps").mkdir()
shutil.copy2(folder / "workflow.json", out / "workflow.json")
for sub in ("corpus", "background"):
    if (folder / sub).exists():
        shutil.copytree(folder / sub, out / sub)
corpus = load_corpus(out)
wf = W.normalise(json.loads((folder / "workflow.json").read_text(encoding="utf-8")))
report: dict = {"workflow_faults": W.check(wf, W.attribute_sizes(corpus), len(corpus.documents))}
report["workflow_faults"] = [f for f in report["workflow_faults"] if "does not end by writing" not in f or not wf.get("steps")]

given: dict[str, dict[str, list]] = {}


def no_model(step: str, *_args, **_kwargs) -> str:
    raise RuntimeError(f"{step} asks a model, and a recount calls none: count it from coded rows instead")


run = S.Run(folder=out, corpus=corpus, question=wf.get("question_as_agreed") or "", ask=no_model, steps=wf.get("steps", []))
missing_coding, skipped = [], []
for s in wf.get("steps", []):
    sid, kind = s.get("id"), s.get("kind")
    if kind == "code":
        f = folder / "coded" / f"{sid}.json"
        if not f.exists():
            missing_coding.append(sid)
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        given[sid] = {}
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict):
                given[sid].setdefault(str(r.get("document")), []).append(r)
        unknown = sorted(set(given[sid]) - set(corpus.documents))
        if unknown:
            report.setdefault("documents_not_in_the_corpus", {})[sid] = unknown
        rec = S.code_given(run, s, given[sid])
    elif kind in ("sample", "tabulate", "judge"):
        rec = {"sample": S.sample, "tabulate": S.tabulate, "judge": judge}[kind](run, W.resolve_step(s, kind) if kind != "judge" else s)
    else:
        skipped.append(f"{sid} ({kind})")
        continue
    rec = {"id": sid, "kind": kind, **rec}
    run.out[sid] = rec
    (out / "steps" / f"{sid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

report["code_steps_without_coded_rows"] = missing_coding
report["steps_not_recounted"] = skipped
for sid, rec in run.out.items():
    if rec["kind"] == "code":
        report.setdefault("coding", {})[sid] = {
            "rows": len(rec["rows"]), "quotations_not_found": [f"{d['document']}: {d['quote'][:80]}" for d in rec["quotations_dropped"]],
            "values_off_the_list": rec["values_off_the_list"], "values_missing": rec["values_missing"],
            **({"sections_unread": [f"{u['document']}: {u.get('error', '')[:200]}" for u in rec["sections_unread"]]}
               if rec.get("sections_unread") else {}),
            **({"documents_without_a_row": rec["document_attributes"]["documents_without_a_row"]}
               if rec.get("document_attributes") else {})}

(out / "rows.md").write_text("\n".join(S.row_line(r) for rec in run.out.values() if rec["kind"] == "code"
                                       for r in rec["rows"]) + "\n", encoding="utf-8")
tables = [f"## {sid}\n\n" + (S._markdown(rec, sid) if rec["kind"] == "tabulate" else judge_markdown({**rec, "id": sid}))
          for sid, rec in run.out.items() if rec["kind"] in ("tabulate", "judge")]
(out / "tables.md").write_text("\n\n".join(tables) + "\n", encoding="utf-8")
counts = S.counts_of(run, [sid for sid, rec in run.out.items() if rec["kind"] in ("tabulate", "judge")])
(out / "counts.json").write_text(json.dumps(counts, indent=1, ensure_ascii=False), encoding="utf-8")

if a.answer:
    text = Path(a.answer).read_text(encoding="utf-8")
    resolved, used, unknown, bare = S.put_counts(text, counts, run.corpus.documents)
    rows = {r["row"]: r for rec in run.out.values() if rec["kind"] == "code" for r in rec["rows"]}
    cited = [c for c in S.citation_ids(text) if re.fullmatch(r"[\w-]+\.[\w.-]+", c) and c not in corpus.documents]
    whole = "\n".join(corpus.text(d) for d in corpus.documents)
    report["answer"] = {
        "counts_written_by_id": len(used), "ids_naming_no_count": sorted(set(unknown)), "numbers_written_bare": bare,
        "citations_to_no_row": sorted({c for c in cited if c not in rows and c not in counts}),
        "quotations_found_in_no_document": [q for q in S.quotations(text)
                                            if locator.locate_all(whole, [q])[0] is None],
        "quotations_not_in_what_they_cite": [q for _, scope in S._sentences_with_scope(text)
                                             for q in S.quoted_elsewhere(run, scope, {k: r["document"] for k, r in rows.items()})]}
    (out / "answer.resolved.md").write_text(resolved, encoding="utf-8")
    # the write step's record as the runner keeps it, with the checks named as the page reads them
    a_ = report["answer"]
    for s in wf.get("steps", []):
        if s.get("kind") == "write":
            (out / "steps" / f"{s['id']}.json").write_text(json.dumps({
                "id": s["id"], "kind": "write", "answer": resolved, "model_answer": text,
                "checks": {"counts": len(used), "counts_to_no_cell": a_["ids_naming_no_count"],
                           "numbers_written_bare": bare, "citations_to_no_row": a_["citations_to_no_row"],
                           "quotations_not_found": a_["quotations_found_in_no_document"]}},
                indent=1, ensure_ascii=False), encoding="utf-8")

(out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
(out / "run.json").write_text(json.dumps({"question": wf.get("question_as_agreed") or "", "recounted_from": "free+w"},
                                         indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=1, ensure_ascii=False))
print(f"\nwritten: {out / 'tables.md'}, {out / 'rows.md'}, {out / 'counts.json'}" + (f", {out / 'answer.resolved.md'}" if a.answer else ""))
