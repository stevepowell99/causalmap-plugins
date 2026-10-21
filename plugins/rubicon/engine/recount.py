"""Recount a Free+W folder with Rubicon's own pieces, by code alone.

    python recount.py <folder> [--answer answer.md]

The folder holds `corpus/` (the documents and `index.csv`), `workflow.json` (a workflow of pieces: sample, code,
group, tabulate, judge, write) and `coded/<code step id>.json`, the rows the analyst coded for each code step: a JSON list of
{"document", "quote", <each column>: value}. Each code step places the analyst's rows exactly as a run places a
model's (`steps.code_given`), so every quotation is found in its document (and dropped, and listed, where it is not),
every value is checked against its column's values and stored in one spelling, and a per-document step's values become
document attributes. The tabulate and judge steps then
run as they do in any run. Nothing calls a model: a judge step's reading criteria, which weigh coded rows against
each level's descriptor, are the analyst's readings recorded in `judged/<judge step id>.json`, an object of
{criterion id: {"verdict": a level, or "between" with "between": [two levels], "rows": [row ids it rests on],
"against": [row ids that pull the other way], "why": a sentence}}, checked as a model's reading is checked. A claims
step's claims, the answer's key claims that rest on no count, are the writer's, recorded in `judged/<claims step id>.json`
as {claim id: {"says", "rows", "against", "found_by", "why"}} and checked the same way (`judge.evidence`); the answer
cites one as [<claims step id>.<claim id>]. A group step's codebook, which the analyst draws from the open labels a
code step coded, is recorded in `judged/<group step id>.json` in the hosted grouping model's format, each item naming the
labels it gathers in `from_labels` (`steps.group_given`); code gives every row its item by its label, checks that every
label is placed or left over, and where the step assigns, tables count by `item`; a later code step whose column's
values are `codebook:<group step id>` is coded against its items.

Writes `recount/`: `steps/<id>.json`, `rows.md` (every row with its id), `tables.md` (every table and verdict with
the ids of its cells), `counts.json`, `report.json`. With `--answer`, the answer's {cell ids} are replaced with their
counts as the write step does, and its [row ids] with each row's document and the opening words of its quotation,
linked to the row (`answer.resolved.md`); and the report adds ids naming no cell, numbers written bare, numbers stated beside a count's id that differ from it,
row citations naming no row, quotations found in no document, quotations not in what they cite, the claims cited and
where each sentence stands that nothing ties to the passages. The report also holds an
`audit` (`rubicon_open/audits.py`): warnings from checks code makes without a model, which a writer and a check weigh
against the documents and which never stop a recount. `recount/` is then
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
from rubicon_open import console  # noqa: E402
from rubicon_open.corpus import load_corpus
from rubicon_open import audits, earlier, legacy_weak, locator
from rubicon_open import steps as S
from rubicon_open import workflow as W
from rubicon_open.guidance import NoModel
from rubicon_open.judge import claims, judge, markdown as judge_markdown

console.utf8()
ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--answer")
a = ap.parse_args()
folder = Path(a.folder).resolve()
out = folder / "recount"
out.mkdir(exist_ok=True)
try:  # the workflow the last recount ran, which says how it named its cells
    before = json.loads((out / "workflow.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    before = None
# whether the run was made before the weak mark was retired, read before the last recount's records are cleared
earlier_records = legacy_weak.records_in(out / "steps")
for p in out.iterdir():  # a recount starts clean, so nothing from an earlier one outlives an edited row
    shutil.rmtree(p) if p.is_dir() else p.unlink()
(out / "steps").mkdir()
for sub in ("corpus", "background"):
    if (folder / sub).exists():
        shutil.copytree(folder / sub, out / sub)
corpus = load_corpus(out)
# a step taken from an earlier run is filled in from that run's sealed zip, so the recount's workflow says what ran
wf, taken_rows, taken_faults, taken = earlier.resolve(folder, json.loads((folder / "workflow.json").read_text(encoding="utf-8")), corpus)
# How the tabulations name their cells (`steps.CELL_IDS`): as the workflow says; else as the last recount of this folder
# did, where that was made before the workflow recorded it (positional); else by coordinates. The recount records it in
# the workflow it writes, so a zip recounts under the naming it was made with.
cell_ids = wf.get("cell_ids") or (before.get("cell_ids") or "positional" if before is not None else "coordinates")
wf = {**wf, "cell_ids": cell_ids}
# a run made before 15 October 2026 keeps its rows' weak marks (`legacy_weak`), recorded as cell_ids is
legacy = legacy_weak.marked(wf, earlier_records) or legacy_weak.marked(before, [])
wf = legacy_weak.flag(wf, legacy)
(out / "workflow.json").write_text(json.dumps(wf, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
wf = W.normalise(wf)
if any(W.combining(st, {x.get("id"): x for x in wf["steps"][:k]}) for k, st in enumerate(wf["steps"])):
    # a step that puts codings together has the columns and links they share filled in, which the report and the page read
    (out / "workflow.json").write_text(json.dumps(wf, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
report: dict = {"workflow_faults": taken_faults + W.check(wf, W.attribute_sizes(corpus), len(corpus.documents))
                + ([] if cell_ids in S.CELL_IDS else [f"cell_ids is {cell_ids!r}; it is one of {', '.join(S.CELL_IDS)}"])}
if taken:
    report["earlier_runs"] = taken
report["workflow_faults"] = [f for f in report["workflow_faults"] if "does not end by writing" not in f or not wf.get("steps")]

given: dict[str, dict[str, list]] = {}


def no_model(step: str, *_args, **_kwargs) -> str:
    raise NoModel(f"{step} asks a model, and a recount calls none: count it from coded rows, or record the reading in judged/{step}.json")


readings: dict[str, dict] = {}
for s in wf.get("steps", []):
    f = folder / "judged" / f"{s.get('id')}.json"
    if s.get("kind") in ("judge", "claims") and f.exists():
        got = json.loads(f.read_text(encoding="utf-8"))
        readings[s["id"]] = got if isinstance(got, dict) else {}
        if s["kind"] == "claims":
            continue
        named = {c.get("id") for c in s.get("criteria") or [] if c.get("kind") == "reading"}
        stray = sorted(set(readings[s["id"]]) - named)
        if stray:
            report.setdefault("readings_for_no_reading_criterion", {})[s["id"]] = stray
if (folder / "judged").exists():
    shutil.copytree(folder / "judged", out / "judged")
run = S.Run(folder=out, corpus=corpus, question=wf.get("question_as_agreed") or "", ask=no_model, steps=wf.get("steps", []),
            readings=readings, cell_ids=cell_ids, legacy_weak=legacy)
missing_coding, missing_codebook, skipped = [], [], []
for s in wf.get("steps", []):
    sid, kind = s.get("id"), s.get("kind")
    if kind == "code" and S.combines(run, s):  # the rows of other code steps put together; nothing is coded for it
        lacking = [i for i in s["inputs"] if i not in run.out]
        if lacking:
            skipped.append(f"{sid} (code, puts together {', '.join(lacking)}, which {'was' if len(lacking) == 1 else 'were'} not recounted)")
            continue
        rec = S.combined(run, s)
    elif kind == "code":
        f = folder / "coded" / f"{sid}.json"
        unmade = [g for c in s.get("columns") or [] if isinstance(c, dict) and (g := W.codebook_of(c)) and g not in run.out]
        if unmade:  # coded against a codebook no group step here made
            skipped.append(f"{sid} (code, takes its values from {', '.join(unmade)}, which was not recounted)")
            continue
        took = isinstance(s.get("from"), dict) and (s["from"].get("take") or "rows") == "rows"
        if took and sid in taken_rows:  # coded and checked in the earlier run, placed again here as any rows are
            given[sid] = taken_rows[sid]
        elif took or not f.exists() or isinstance(s.get("from"), dict) and not s.get("columns"):
            missing_coding.append(sid)
            continue
        else:
            rows = json.loads(f.read_text(encoding="utf-8"))
            given[sid] = {}
            for r in rows if isinstance(rows, list) else []:
                if isinstance(r, dict):
                    given[sid].setdefault(str(r.get("document")), []).append(r)
        unknown = sorted(set(given[sid]) - set(corpus.documents))
        if unknown:
            report.setdefault("documents_not_in_the_corpus", {})[sid] = unknown
        rec = S.code_given(run, s, given[sid])
        if isinstance(s.get("from"), dict):  # the earlier run it was taken from, which the report and the page name
            rec["from"] = s["from"]
    elif kind == "group":  # the codebook the analyst drew from the open labels, placed and checked by code
        f = folder / "judged" / f"{sid}.json"
        src = (s.get("inputs") or [None])[0]
        if src not in run.out:
            skipped.append(f"{sid} (group, rests on {src}, which was not recounted)")
            continue
        if not f.exists():
            missing_codebook.append(sid)
            continue
        book = json.loads(f.read_text(encoding="utf-8"))
        rec = S.group_given(run, s, book if isinstance(book, dict) else {})
    elif kind in ("sample", "profile", "tabulate", "judge", "claims"):
        try:
            rec = {"sample": S.sample, "profile": S.profile, "tabulate": S.tabulate, "judge": judge, "claims": claims}[kind](
                run, W.resolve_step(s, kind) if kind not in ("judge", "claims") else s)
        except KeyError as e:  # a step resting on one with no rows to count from: said, rather than a crash
            if e.args and e.args[0] in missing_coding + missing_codebook + [x.split(" ")[0] for x in skipped]:
                skipped.append(f"{sid} ({kind}, rests on {e.args[0]}, which was not recounted)")
                continue
            raise
    else:
        skipped.append(f"{sid} ({kind})")
        continue
    rec = {"id": sid, "kind": kind, **rec}
    run.out[sid] = rec
    (out / "steps" / f"{sid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")

report["code_steps_without_coded_rows"] = missing_coding
if missing_codebook:
    report["group_steps_without_a_codebook"] = missing_codebook
for sid, rec in run.out.items():  # each reading criterion: placed or not, and any row it cites that it does not read
    for c in rec.get("criteria") or [] if rec["kind"] == "judge" else []:
        if c["kind"] != "reading":
            continue
        if c.get("read_by") == "none":
            report.setdefault("readings_not_recorded", []).append(f"{sid}.{c['id']}")
        elif c["verdict"] is None and not c.get("between"):
            report.setdefault("readings_not_placed", []).append(f"{sid}.{c['id']}: {c['why']}")
        if c.get("rows_cited_that_do_not_exist"):
            report.setdefault("readings_citing_rows_they_do_not_read", {})[f"{sid}.{c['id']}"] = c["rows_cited_that_do_not_exist"]
    for c in rec.get("claims") or [] if rec["kind"] == "claims" else []:  # each claim: what it rests on, checked
        if c["rows_cited_that_do_not_exist"]:
            report.setdefault("claims_citing_rows_they_do_not_read", {})[f"{sid}.{c['id']}"] = c["rows_cited_that_do_not_exist"]
        if not c["rows"]:
            report.setdefault("claims_resting_on_no_row", []).append(f"{sid}.{c['id']}")
report["steps_not_recounted"] = skipped
for sid, rec in run.out.items():
    if rec["kind"] == "code":
        report.setdefault("coding", {})[sid] = {
            "rows": len(rec["rows"]), "quotations_not_found": [f"{d['document']}: {d['quote'][:80]}" for d in rec["quotations_dropped"]],
            "quotations_placed_approximately": sum(r.get("tier") not in locator.SNAP_TIERS for r in rec["rows"] if r.get("tier")),
            "values_off_the_list": rec["values_off_the_list"], "values_missing": rec["values_missing"],
            **({"values_not_mapped": rec["values_not_mapped"]} if rec.get("values_not_mapped") else {}),
            **({k: rec[k] for k in ("combines", "rows_by_coding", "documents_not_read_by_every_coding", "columns_not_in_every_coding",
                                    "values_off_the_list_by") if rec.get(k)} if rec.get("combines") else {}),
            **({"sections_unread": [f"{u['document']}: {u.get('error', '')[:200]}" for u in rec["sections_unread"]]}
               if rec.get("sections_unread") else {}),
            **({"documents_without_a_row": rec["document_attributes"]["documents_without_a_row"]}
               if rec.get("document_attributes") else {})}

for sid, rec in run.out.items():
    if rec["kind"] == "group":
        report.setdefault("grouping", {})[sid] = rec["checks"]

(out / "rows.md").write_text("\n".join(S.row_line(r) for rec in run.out.values() if rec["kind"] == "code" and not rec.get("combines")
                                       for r in rec["rows"]) + "\n", encoding="utf-8", newline="\n")  # a combined table's rows are its inputs' own
tables = [f"## {sid}\n\n" + (f"{rec['description']}\n\n" if rec.get("description") else "")
          + (S._markdown(rec, sid) if rec["kind"] == "tabulate" else judge_markdown({**rec, "id": sid}, margins=True))
          for sid, rec in run.out.items() if rec["kind"] in ("tabulate", "judge")]
(out / "tables.md").write_text("\n\n".join(tables) + "\n", encoding="utf-8", newline="\n")
counts = S.counts_of(run, [sid for sid, rec in run.out.items() if rec["kind"] in ("tabulate", "judge")])
(out / "counts.json").write_text(json.dumps(counts, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")

if a.answer:
    text = Path(a.answer).read_text(encoding="utf-8")
    whole = "\n".join(corpus.text(d) for d in corpus.documents)
    resolved, used, unknown, bare = S.put_counts(text, counts, run.corpus.documents, whole)
    rows = {r["row"]: r for rec in run.out.values() if rec["kind"] == "code" for r in rec["rows"]}
    tagged = {f"{sid}.{c['id']}": c for sid, rec in run.out.items() if rec["kind"] == "claims" for c in rec["claims"]}
    cited = [c for c in S.citation_ids(text) if re.fullmatch(r"[\w-]+\.[\w.-]+", c) and c not in corpus.documents]
    quoted = S.quotations(text)
    # word for word in one document, each part either side of an ellipsis included; else perhaps approximately anywhere
    exact = audits.place(run, [(corpus.documents, q) for q in quoted]) if quoted else []
    rough = [q for q, h in zip(quoted, exact) if h is None]
    rough = dict(zip(rough, locator.locate_all(whole, rough))) if rough else {}
    placed = [h or rough.get(q) for q, h in zip(quoted, exact)]
    report["answer"] = {
        "counts_written_by_id": len(used), "ids_naming_no_count": sorted(set(unknown)), "numbers_written_bare": bare,
        # where each stands in answer.md, years too, so the report can mark it as the writer's own (render_report.unchecked)
        "numbers_written_bare_at": S.numbers_written_bare(text, run.corpus.documents, whole, years=True),
        "stated_counts_that_differ": S.stated_counts_that_differ(text, counts, run.corpus.documents, whole),
        # how many of the counts the writer also stated as a number beside the reference; a run recounted before this
        # was recorded wrote one beside every count (procedure.stated_beside_all)
        "counts_stated_beside": len(S.stated_beside(text, run.corpus.documents, whole)),
        "citations_to_no_row": sorted({c for c in cited if c not in rows and c not in counts and c not in tagged}),
        # the claims the answer cites, and those recorded that it never cites, which no reader would be shown
        "claims_cited": len({c for c in cited if c in tagged}),
        "claims_never_cited": sorted(set(tagged) - set(cited)),
        # each sentence that nothing ties to the passages, out of those read for one, which the report marks lightly
        "sentences_read_for_a_tag": len(S.sentences_read_for_a_tag(text)),
        "sentences_untagged_at": S.sentences_untagged_at(text),
        # how many the check looked at, so a report can say "all 40 found" rather than "none missing"
        "quotations_in_the_answer": len(quoted),
        "quotations_found_in_no_document": [q for q, h in zip(quoted, placed) if h is None],
        "quotations_placed_approximately": [q for q, h in zip(quoted, exact) if h is None and rough.get(q) is not None],
        "quotations_not_in_what_they_cite": [q for _, scope in S._sentences_with_scope(text)
                                             for q in S.quoted_elsewhere(run, scope, {k: r["document"] for k, r in rows.items()},
                                                                         {k: c["rows"] + c["against"] for k, c in tagged.items()})]}
    resolved = S.readable_citations(resolved, rows)
    (out / "answer.resolved.md").write_text(resolved, encoding="utf-8", newline="\n")
    # the write step's record as the runner keeps it, with the checks named as the page reads them
    a_ = report["answer"]
    for s in wf.get("steps", []):
        if s.get("kind") == "write":
            (out / "steps" / f"{s['id']}.json").write_text(json.dumps({
                "id": s["id"], "kind": "write", "answer": resolved, "model_answer": text,
                "checks": {"counts": len(used), "counts_to_no_cell": a_["ids_naming_no_count"],
                           "numbers_written_bare": bare, "citations_to_no_row": a_["citations_to_no_row"],
                           "quotations_not_found": a_["quotations_found_in_no_document"]}},
                indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")

# code-only audits of the coding and the answer: warnings to weigh against the documents, never faults to clear
try:
    report["audit"] = {"about": "Warnings from checks that fixed rules can make without a model. Weigh each against the document "
                                "it names; none is a fault the report must clear, and a finding may be right.",
                       **audits.audit_run(run, text if a.answer else None, counts)}
except Exception as e:  # a broken audit must not lose the recount, and must say it did not run
    report["audit"] = {"error": f"the audit did not run: {type(e).__name__}: {e}"}
(out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
(out / "run.json").write_text(json.dumps({"question": wf.get("question_as_agreed") or "", "recounted_from": "free+w"},
                                         indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
print(json.dumps(report, indent=1, ensure_ascii=False))
for t_ in taken:  # said here and not kept in the report, which must read the same however many revisions follow
    for later in earlier.revised_since(folder, t_["run_id"], t_["fingerprint"]):
        print(f"\nEARLIER RUN REVISED: {t_['step']} is taken from run {t_['run_id']} as it was at {t_['fingerprint'][:8]}, "
              f"and {later} holds a later revision of it. Bring this run up to date as a substantive revision: point "
              "the step's from at the later fingerprint, recount, and run stale.py.")
if missing_coding:
    print(f"\nNot recounted: {', '.join(f'coded/{m}.json' for m in missing_coding)} missing. A recount counts from the rows "
          "each code step was coded with; a run's zip made before 7 October 2026 holds them only as the rows in "
          "steps/<id>.json: copy each step's \"rows\" from there into coded/<id>.json and recount again.")
audit_lines = [x for x in audits.in_words(report["audit"]) if not x.endswith("found 0")] if "error" not in report["audit"] else [report["audit"]["error"]]
if audit_lines:
    print("\nAUDIT WARNINGS, for you to weigh against the documents (none is a fault to clear; recount/report.json holds them in full):")
    print("\n".join(f"- {x}" for x in audit_lines))
print(f"\nwritten: {out / 'tables.md'}, {out / 'rows.md'}, {out / 'counts.json'}" + (f", {out / 'answer.resolved.md'}" if a.answer else ""))
if a.answer and report["answer"]["quotations_found_in_no_document"]:
    print("\nQUOTATIONS IN THE ANSWER FOUND IN NO DOCUMENT, so no report will be created until each is copied word for word "
          "from its document or its quotation marks are removed:\n" + "\n".join(f"- \"{q}\"" for q in report["answer"]["quotations_found_in_no_document"]))
if a.answer and report["answer"]["ids_naming_no_count"]:
    # an error, not a note: the answer states a count of a cell the tables no longer hold (a value recoded or renamed, a
    # step removed), so its sentence would stand without the number it was written for
    gone = report["answer"]["ids_naming_no_count"]
    sys.exit(f"ERROR: the answer cites {len(gone)} count{'' if len(gone) == 1 else 's'} that no cell or rule now makes: "
             + "; ".join("{" + g + "}" for g in gone) + f". {out / 'tables.md'} lists the ids that exist; cite one of them, "
             "or rewrite the sentence if the cell it counted is gone.")
