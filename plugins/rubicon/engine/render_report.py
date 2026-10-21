"""Draw a Rubicon run folder as a report to read and click through, the same report for Word, and the run as a zip.

    python render_report.py <run folder> [--date "6 October 2026"] [--fragment]
    python render_report.py <run .zip>   [the same options]

The three files share one name, made from the question, the day and the first eight characters of the run's
fingerprint: `<question>-<yyyy-mm-dd>-<fingerprint>.html`, `.doc` and `.zip`, with `-revision-<n>` before the
fingerprint once the run has been revised (`revisions.md`), so a report and its zip are seen to match by their names. The zip is the recounted run in the open format (`recount/`: `workflow.json`, `run.json`, `steps/*.json`,
`corpus/` and `background/`), which the Rubicon page's "Open a downloaded run (.zip)" reads in the browser and
never saves. It holds the documents, because the page needs them to show each quotation in its place, and
`answer.md`, `counts.json` and `report.json`, so that given the zip in place of a folder this draws the report again
from the zip alone, under the name and date it was first drawn with: the run is laid out again in a folder named after the zip (`unpack`), and the
report and its Word copy are written beside the zip. Where the zip's own report is already beside it, nothing is
overwritten: the report is written into that folder instead, and the output says so.

The report is drawn from the zip and from nothing else: given a folder, this makes the zip first, then reads only the
zip (`load`), so a report cannot say anything its zip does not hold. The zip is sealed: `SHA256SUMS` lists the SHA-256
of every other file in it, and the SHA-256 of that list is the run's fingerprint, printed in the report. `render.json`
in the zip gives the name and date the report is drawn under and the engine that drew it, and its files carry a
fixed date, so the same run always makes the same zip and the same zip the same report, byte for byte. Nothing is drawn
from a zip whose seal is broken, whose recount a fresh recount of its own coded rows and answer would change, or whose
answer cites a row the recount does not hold (`problems`). `verify.py` says whether a given report was drawn from a given zip.

Reads only what the run already holds (answer.md with its cell ids, recount/steps/*.json, recount/report.json,
corpus/index.csv and the corpus text for context around each quotation). Makes no model call, so it costs nothing
and draws the same report every time. Standard library and Node only.

In answer.md, a line holding only {{figure <table id>}} draws that table as a chart at that point. A table with a column
whose values have an order (`order_of`) draws along it (`ordered_chart`), as an inline SVG of lines or stacked columns. A table by the two
ends of a code step's causal links draws as a causal map: the report carries its DOT (rubicon_open/draw_map.mjs) and
Graphviz draws it in the reader's browser, from a copy of Viz.js carried inside the report (`assets.graphviz_script`), as are the
typefaces (`assets.fonts_css`), so one report file opens on a network that reaches nothing.
--fragment writes the page without <html>/<head>/<body>, for publishing as an Artifact.
"""
import base64, csv, datetime, gzip, hashlib, html, io, json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import console  # noqa: E402
from rubicon_open import assets, footprint, legacy_weak, locator, node, plan, procedure
from rubicon_open.corpus import INDEX_FIELDS, Corpus, as_read
from rubicon_open.legacy_weak import CHAIN_EXPLICIT
from rubicon_open.run_id import clean as run_id_of
from rubicon_open.seal import engine_fingerprint, engine_version, seal_broken
from rubicon_open.steps import LIMITS, ROW_ID, base_of, cited_as, group_ids, said_with_unit, step_of, unit_of_table
from rubicon_open.units import base_said, count_said
from rubicon_open.workflow import arrow_parts, codebook_of, column_values, derived, loop_markers, normalise, order_of, sign_of, value_key

ENGINE = Path(__file__).resolve().parent
DRAW_MAP = ENGINE / "rubicon_open" / "draw_map.mjs"
#: Every file in a zip carries this date, so the same run always makes the same zip, byte for byte
STAMP = (1980, 1, 1, 0, 0, 0)
CONTEXT = 420  # characters of the document shown either side of a quotation


def name_of(workflow, revisions, date="", titled=""):
    """The name the run's files share: the agreed question, cut to its first words, and the day it is drawn under (the
    `--date` given, so a report drawn again keeps its day, else today), then the revision number where the run has been
    revised, so a revised report never overwrites the one before it. A run that answers no question has no agreed
    question, so it is named from `titled`, the words it goes by (`titled_as`), by the same rule."""
    words, slug = re.findall(r"[a-z0-9]+", re.sub(r"['\u2019]", "", (workflow.get("question_as_agreed", "").strip() or titled).lower())), ""
    for w in words:
        if len(slug) + len(w) > 50:
            break
        slug = f"{slug}-{w}" if slug else w
    revised = sum(1 for l in revisions.splitlines() if l.strip().startswith("- "))
    try:
        day = datetime.datetime.strptime(date.strip(), "%d %B %Y").date()
    except ValueError:
        day = datetime.date.today()
    return f"{slug or 'rubicon'}-{day.isoformat()}" + (f"-revision-{revised}" if revised else "")


def titled_as(folder, workflow):
    """The words a run that answers no question goes by: the `# ` title its answer carries, else its row in the plan
    beside the documents (`plan.read`), found by its run ID; empty where it has neither."""
    answer = Path(folder) / "answer.md"
    for line in answer.read_text(encoding="utf-8").splitlines() if answer.is_file() else []:
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    row = plan.entry_for(plan.read(Path(folder).resolve().parent), run_id_of(workflow.get("run_id")))
    return row["title"] if row else ""


def recorded(rec):
    """What the zip takes from a run's recount, by its name in the zip."""
    files = {n: rec / n for n in ("workflow.json", "run.json", "counts.json", "report.json") if (rec / n).is_file()}
    for sub in ("steps", "corpus", "background"):
        for p in sorted((rec / sub).rglob("*")) if (rec / sub).is_dir() else []:
            if p.is_file():
                files[p.relative_to(rec).as_posix()] = p
    return files


def recount_differs(run):
    """The files of the run's recount that a fresh recount from its coded rows and its answer would not write as they
    stand. Empty means every number, check and table the report draws follows from the coded passages and the answer
    as they are now."""
    with tempfile.TemporaryDirectory() as t:
        fresh = Path(t)
        for name in ("workflow.json", "answer.md"):
            shutil.copy2(run / name, fresh / name)
        # a run made before the weak mark was retired is recounted as it was made (`legacy_weak`)
        wf = json.loads((run / "workflow.json").read_text(encoding="utf-8"))
        if not legacy_weak.reads(wf) and legacy_weak.marked(wf, legacy_weak.records_in(run / "recount" / "steps")):
            (fresh / "workflow.json").write_text(json.dumps(legacy_weak.flag(wf, True), indent=1, ensure_ascii=False),
                                                 encoding="utf-8", newline="\n")
        for sub in ("corpus", "background", "coded", "judged", "earlier"):
            if (run / sub).is_dir():
                shutil.copytree(run / sub, fresh / sub)
        done = subprocess.run([sys.executable, "-I", "-S", str(ENGINE / "recount.py"), str(fresh), "--answer",
                               str(fresh / "answer.md")], capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            return ["the recount itself, which failed: " + done.stderr.strip()[-400:]]
        old, new = recorded(run / "recount"), recorded(fresh / "recount")
        return sorted(n for n in old.keys() | new.keys() if n not in old or n not in new or not same(n, old[n], new[n]))


def same(name, a, b):
    """Whether two copies of a recount file are the same. `run.json` is compared without the `chat` that runs made
    before 10 October 2026 recorded, which no recount now writes, so those runs still draw."""
    if name == "run.json":
        try:
            drop = lambda p: {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k != "chat"}
            return drop(a) == drop(b)
        except (OSError, ValueError, AttributeError):
            pass
    if name.endswith(".json"):
        # A newer engine records more about the same run (a judgement's margin, say), so a recount it makes may add
        # fields the run's own recount never had; it may not change or drop any it has, which is what a report reads
        try:
            old, new = json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8"))
            # a tabulation recounted before cases were counted says it counted documents; where each case is one
            # document, counting cases is the same count
            if isinstance(old, dict) and old.get("count") == "documents" and isinstance(new, dict) and new.get("count") == "cases"                     and new.get("cases_are_documents"):
                old = {**old, "count": "cases"}
            return kept(old, new)
        except (OSError, ValueError):
            pass
    # line endings are the platform's that wrote the file (a recount on Windows writes \r\n), never part of a count
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def kept(old, new):
    """Whether `new` holds everything `old` does, unchanged: every key of each object with the same value, every list
    the same length and each item kept, any key `new` adds left aside."""
    if isinstance(old, dict):
        return isinstance(new, dict) and all(k in new and kept(v, new[k]) for k, v in old.items())
    if isinstance(old, list):
        return isinstance(new, list) and len(old) == len(new) and all(kept(x, y) for x, y in zip(old, new))
    return old == new


def bundle(run, out, render):
    """The recounted run as one zip, as the Rubicon page opens it, sealed: `SHA256SUMS` lists the SHA-256 of every
    other file in it, and the SHA-256 of that list is the run's fingerprint, which the report prints.
    Fixed dates and order make the same run always give the same zip."""
    rec = run / "recount"
    files = {n: p for n, p in recorded(rec).items() if not n.startswith(("steps/", "corpus/", "background/"))}
    # The answer as written, cell ids and figure lines and all, so the zip alone rebuilds the report (`unpack`)
    files["answer.md"] = run / "answer.md"
    if (run / "revisions.md").is_file():
        files["revisions.md"] = run / "revisions.md"
    # The rows each code step was coded with, which is what the recount counts from, so the zip alone recounts
    for p in sorted((run / "coded").glob("*.json")):
        files["coded/" + p.name] = p
    # and the readings the analyst recorded for the criteria that cannot be counted, which the recount applies
    for p in sorted((run / "judged").glob("*.json")):
        files["judged/" + p.name] = p
    # each earlier run a step was taken from, whole and sealed, so the zip alone recounts and verifies both
    for p in sorted((run / "earlier").glob("*.zip")):
        files["earlier/" + p.name] = p
    files.update({n: p for n, p in recorded(rec).items() if n.startswith(("steps/", "corpus/", "background/"))})
    # The analyst's audit trail: the scripts, their output, the table of what each document holds, and the procedure
    for p in sorted((run / "work").rglob("*")) if (run / "work").is_dir() else []:
        if p.is_file() and "__pycache__" not in p.parts:
            files["work/" + p.relative_to(run / "work").as_posix()] = p
    # The second reading: the check's record and the second coder's own rows, beside the run they checked
    for p in [run / "check.md"] + [run / "recode" / f for f in ("disagreements.md", "unclear.md", "readers.json")] \
            + sorted((run / "recode" / "coded").glob("*.json")):
        if p.is_file():
            files["check/" + p.relative_to(run).as_posix().removeprefix("recode/")] = p
    entries = [(n, p.read_bytes()) for n, p in files.items()]
    # How the report was drawn, so the zip alone draws it again under the same name, from the same engine
    entries.append(("render.json", json.dumps(render, indent=1, ensure_ascii=False).encode("utf-8")))
    out.write_bytes(sealed(entries))


def sealed(entries):
    """A zip of (name, bytes) pairs in the order given, with `SHA256SUMS` last, as bytes: the same files always give
    the same bytes, so a zip re-made from another's contents is that zip again."""
    sums = "".join(f"{hashlib.sha256(b).hexdigest()}  {n}\n" for n, b in entries).encode("utf-8")
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        for n, b in entries + [("SHA256SUMS", sums)]:
            info = zipfile.ZipInfo(n, STAMP)
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(info, b)
    return data.getvalue()


def unpack(zipped, run):
    """A run's zip laid out again as the run folder it was made from, so the report can be drawn from the zip alone:
    the recount at `recount/`, the answer, the coded rows, the check and the second coder's rows where they were, and
    the workflow, documents and background at the top as `load` and the recount read them. Refused for a zip whose
    seal is broken, since a report drawn from it would carry a fingerprint the original never had."""
    if run.exists():
        sys.exit(f"{run} already exists; move it, or create the report from that folder instead")
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
        if broken:
            sys.exit(f"{zipped.name} is not as it was made, so no report is created from it: " + "; ".join(broken))
        for n in z.namelist():
            if n.endswith("/"):
                continue
            to = (run / n if n in ("answer.md", "revisions.md", "render.json", "SHA256SUMS") or n.startswith(("coded/", "judged/", "work/", "earlier/"))
                  else run / n.removeprefix("check/") if n == "check/check.md"
                  else run / "recode" / n.removeprefix("check/") if n.startswith("check/") else run / "recount" / n)
            to.parent.mkdir(parents=True, exist_ok=True)
            to.write_bytes(z.read(n))
    wf = json.loads((run / "recount" / "workflow.json").read_text(encoding="utf-8"))
    if "cell_ids" not in wf:  # made before cells were named by their coordinates: its ids are places in the tables
        wf["cell_ids"] = "positional"
    # made before the weak mark was retired: its rows keep their marks when it is recounted (`legacy_weak`)
    wf = legacy_weak.flag(wf, legacy_weak.marked(wf, legacy_weak.records_in(run / "recount" / "steps")))
    (run / "workflow.json").write_text(json.dumps(wf, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    for sub in ("corpus", "background"):
        if (run / "recount" / sub).is_dir():
            shutil.copytree(run / "recount" / sub, run / sub)
    return json.loads((run / "render.json").read_text(encoding="utf-8"))


#: What each kind of step is called where a reader meets it, in the annex's headings and the side panel's step buttons
KIND_SAID = {"code": "Coding", "profile": "Profiling", "tabulate": "Counting", "judge": "Judging", "claims": "Tagging claims",
             "write": "Writing", "sample": "Sampling",
             "group": "Grouping", "recode": "Second coding", "check": "Checking"}


def step_said(sid, kind):
    """A step as a reader sees it, the same under How this was made and in the side panel: its kind in words, then its
    name without the one-letter prefix its id may carry for that kind (c_, t_, j_), which a reader is never told."""
    return f"{KIND_SAID.get(kind, label(kind))}: {label(re.sub(r'^[a-z]_', '', sid))}"


def esc(s):
    return html.escape(str(s), quote=True)


def label(v):
    """A value as a reader sees it: underscores as spaces and the first letter capitalised, the rest left as coded, so
    an acronym such as AI keeps its capitals. A factor's opposite pole keeps its leading ~, as Causal Map writes it
    ("~Hygiene and sanitation"); `named` marks the ~ in a page (report.js `label` and `named` say the same). The leading
    # Causal Map's export puts on a document's column ("#Age of the main respondent") is dropped, being a mark of where
    the column came from."""
    s = str(v).replace("_", " ").strip().removeprefix("#").strip()
    pole = s.startswith("~")
    s = s[1:].strip() if pole else s
    return ("~" if pole else "") + s[:1].upper() + s[1:]


def named(v, col=""):
    """A coded value as HTML: its label, with an opposite pole's ~ marked so that pointing at it, tabbing to it or
    tapping it says what it means (report.js `named` and its popover; `col` lets that find the codebook's meaning)."""
    words = label(v)
    if not words.startswith("~"):
        return esc(words)
    return (f'<span class="tilde" tabindex="0" role="button" data-code="{esc(str(v).strip())}" data-col="{esc(col)}" '
            f'aria-label="The opposite of {esc(words[1:])}">~</span>{esc(words[1:])}')


def codes_of(col, R):
    """A coded column's codes, each {"name", "means", "counts", "does_not_count"}: its own list, or where its values are
    `codebook:<group step id>`, that group step's items; none for a column without a list."""
    g = codebook_of(col)
    if g:
        return [{"name": it.get("id"), "means": it.get("means", ""), "counts": it.get("counts", ""),
                 "does_not_count": it.get("does_not_count", "")}
                for it in (R["steps"].get(g, {}).get("codebook") or {}).get("items", [])]
    return [v if isinstance(v, dict) else {"name": str(v)} for v in col.get("values") or [] if isinstance(col.get("values"), list)]


def near_misses(v):
    """What an item does not count, as written: a sentence, or the grouper's near misses, each with where it goes."""
    if isinstance(v, list):
        return "; ".join(str(n.get("text", "")) + (f" (goes to {n['goes_to']})" if n.get("goes_to") else "") if isinstance(n, dict)
                         else str(n) for n in v)
    return str(v or "")


def code_step(R, sid):
    """The code step whose passages a step reads, through any steps between that only select or group them; None where
    it reads none."""
    seen = set()
    while sid and sid not in seen:
        seen.add(sid)
        s = R["steps"].get(sid, {})
        if s.get("kind") == "code":
            return sid
        sid = s.get("input")
    return None


def code_named(D, step, col, v, static=False):
    """A coded value as `named` draws it, made a link to every passage given that code in its code step (report.js
    `showCode`, which opens the cell of a table counting that code alone, as its count does). Plain where the value is
    not a code of `step`, such as a column of the document list, and in the Word copy."""
    key = f"{step}|{col}|{value_key(v)}"
    if static or not step or key not in (D or {}).get("codes", {}):
        return named(v, col)
    return f'<button class="code-label" data-code="{esc(key)}">{named(v, col)}</button>'


def load(zipped):
    """Everything a report draws, read from the run's sealed zip and from nothing else, so a report can say nothing its
    zip does not hold: the counts, rows and checks of the recount, the answer as written, the documents, the second
    reading, the revisions, and from `render.json` the name and date it is drawn under."""
    with zipfile.ZipFile(zipped) as z:
        names = set(z.namelist())
        text = lambda n: z.read(n).decode("utf-8") if n in names else ""
        index = list(csv.DictReader(io.StringIO(text("corpus/index.csv"), newline="")))
        render = json.loads(text("render.json"))
        fingerprint = hashlib.sha256(z.read("SHA256SUMS")).hexdigest()
        workflow = json.loads(text("workflow.json"))
        return {
            "workflow": workflow,
            # Minted once when the run's folder was made and kept through revisions; a run made before IDs has none
            "run_id": run_id_of(workflow.get("run_id")),
            "steps": {n[len("steps/"):-len(".json")]: json.loads(text(n)) for n in sorted(names)
                      if re.fullmatch(r"steps/[^/]+\.json", n)},
            "counts": json.loads(text("counts.json")),
            "report": json.loads(text("report.json")),
            "answer": text("answer.md"),
            "index": index,
            "texts": {d["id"]: as_read(text("corpus/" + (d.get("file") or f"{d['id']}.txt"))) for d in index},
            "check": text("check/check.md"),
            "disagreements": text("check/disagreements.md"),
            # who did the second coding and the check, as the run recorded it: "separate" or "same" for each
            "readers": json.loads(text("check/readers.json") or "{}"),
            # what was put to the evaluator to agree, and their answer, where the run kept a record of it; None where it kept none
            "agreements": json.loads(text("work/agreements.json")) if "work/agreements.json" in names else None,
            # the documents the AI that wrote the answer says it read and found nothing relevant in, where it said
            "read": json.loads(text("work/read.json")) if "work/read.json" in names else None,
            "recoded": {n[len("check/coded/"):-len(".json")]: json.loads(text(n)) for n in sorted(names)
                        if re.fullmatch(r"check/coded/[^/]+\.json", n)},
            "revisions": text("revisions.md"),
            # The files' own name carries the fingerprint's first characters, so a report and its zip are seen to match
            "name": f"{render['name']}-{fingerprint[:8]}", "zip": f"{render['name']}-{fingerprint[:8]}.zip",
            "date": render["date"], "version": render.get("version"), "engine": render.get("engine"),
            "fingerprint": fingerprint,
            "footprint": footprint.estimate(z, index, workflow, text("revisions.md")),
        }


def problems(zipped):
    """Why no report may be drawn from this zip: its seal is broken, its recount is not what a fresh recount of its
    own coded rows and answer gives, its answer cites a row the recount does not hold, or its answer quotes words no
    document holds, or states a number beside a count that differs from it. Empty means the zip is as it was made, every
    number in it follows from its coded passages, every citation opens one and every quotation is found in a document."""
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
        report = json.loads(z.read("report.json").decode("utf-8")) if "report.json" in z.namelist() and not broken else {}
    if broken:
        return [f"{zipped.name} is not as it was made: " + "; ".join(broken)]
    with tempfile.TemporaryDirectory() as t:
        run = Path(t) / "run"
        unpack(zipped, run)
        differs = recount_differs(run)
    if differs:
        return [f"its recount does not follow from its coded rows and its answer: {', '.join(differs)} would change. "
                "Recount with recount.py <folder> --answer answer.md, then create it again"]
    # The recount is the one place that knows which rows exist; a citation it names as no row would draw as a bare id
    # that opens nothing
    unknown = (report.get("answer") or {}).get("citations_to_no_row") or []
    # A quotation in the answer that no document holds would read as a speaker's words that nobody said
    unquoted = (report.get("answer") or {}).get("quotations_found_in_no_document") or []
    # A number stated beside a count that differs from it would read as "17 (16 of 18)"
    differ = (report.get("answer") or {}).get("stated_counts_that_differ") or []
    # A claim tagged with a row the run does not hold, or with none, would open passages that are not there
    unbacked = sorted({**(report.get("claims_citing_rows_they_do_not_read") or {}),
                       **dict.fromkeys(report.get("claims_resting_on_no_row") or [], [])}.items())
    return ([f"the answer cites {', '.join(unknown)}, which no row of the run is called, so a reader would see a bare id "
             "that opens no passage. Cite each passage by the id recount/rows.md gives it, recount, then create it again"]
            if unknown else []) + \
        ([f"the answer quotes words that no document holds: {'; '.join(chr(34) + q + chr(34) for q in unquoted)}. Copy each "
          "word for word from its document, or remove its quotation marks if it is not a quotation, recount, then create it again"]
         if unquoted else []) + \
        ([f"the answer states numbers that differ from their counts: {'; '.join(differ)}. Correct each to its count, "
          "recount, then create it again"] if differ else []) + \
        ([f"claims rest on rows the run does not hold, or on none: "
          + "; ".join(f"{c} ({', '.join(rs) if rs else 'no row'})" for c, rs in unbacked)
          + ". Tag each claim with the ids recount/rows.md gives its passages, recount, then create it again"] if unbacked else [])


def group_column(index):
    cols = [c for c in index[0].keys() if c not in INDEX_FIELDS] if index else []
    return cols[0] if cols else None


def second_reading(step, recoded, texts, rows):
    """What the second coder made of each of this step's passages: whether any passage of theirs
    overlaps it in the document, placed by the engine's quote matcher, and for each of its codes they did not give that
    place, compared through `value_key`, the values they gave it instead. Read from the zip's `check/coded/`."""
    cols = [c["name"] for c in step.get("columns", []) if c.get("type") != "free_text"]
    by_doc = {}
    for r in recoded:
        by_doc.setdefault(r.get("document"), []).append(r)
    for doc, theirs in by_doc.items():
        text = texts.get(doc, "")
        placed = locator.locate_all(text, [str(r.get("quote", "")) for r in theirs]) if text else []
        spans = [(p.start, p.end, r) for p, r in zip(placed, theirs) if p and p.start is not None]
        for x in step.get("rows", []):
            if x["document"] != doc or x["row"] not in rows:
                continue
            overlap = [r for a, b, r in spans if x.get("start") is not None and a < x["end"] and b > x["start"]]
            at_place = {(c, value_key(r.get(c))) for r in overlap for c in cols if r.get(c) not in (None, "")}
            # only the codes the second coder gave this place otherwise: for each, what they gave it instead
            differ = {c: list(dict.fromkeys(r.get(c) for r in overlap if r.get(c) not in (None, "")))
                      for c in cols if x.get(c) not in (None, "") and (c, value_key(x.get(c))) not in at_place}
            rows[x["row"]]["second"] = {"coded": bool(overlap), "differ": differ if overlap else {}}
    # A passage in a document the second coder gave no passage at all is one they did not code
    for x in step.get("rows", []):
        if x["row"] in rows and "second" not in rows[x["row"]]:
            rows[x["row"]]["second"] = {"coded": False, "differ": {}}


def loop_told(c, markers):
    """What a loop table's cell counts, in words: the documents telling a loop whole, one of its links, or a link that
    drives it from outside, the loop named by the marker the answer and its diagram use."""
    v = c["values"]
    marker = markers.get(v.get("loop"), v.get("loop"))
    if v.get("part") == "whole":
        return f"telling loop {marker} whole, {POLARITY_SAID.get(v.get('polarity'), 'a loop')}: {v.get('loop')}"
    if v.get("part") == "driver":
        return f"telling the link {v.get('link')}, which drives loop {marker} from outside it"
    return f"telling the link {v.get('link')}, one of the links of loop {marker}"


def build_data(R):
    """Everything the page's script needs: rows with context, cells, documents."""
    gcol = group_column(R["index"])
    # each document's own facts ride along for a workbook made for Causal Map (`xlsx_button`), as its index gives them
    docs = {d["id"]: {"group": d.get(gcol, ""), "title": d.get("title", d["id"]),
                      "file": "corpus/" + (d.get("file") or f"{d['id']}.txt"),
                      "facts": {k: v for k, v in d.items() if k not in ("id", "title", "file") and v not in (None, "")}}
            for d in R["index"]}
    # the code steps whose rows are causal links: the columns that are a link's two ends and its sign
    ends = {st["id"]: st["links"] for st in R.get("workflow", {}).get("steps", []) if st.get("kind") == "code" and st.get("links")}
    rows, cells, defs, shared = {}, {}, {}, {}
    old = legacy_weak.in_report(R)  # legacy_weak
    # the cases the passages belong to, as the recount attributed them (`Corpus.case_of`), each with its documents and
    # every passage of it in any code step, for the panel's case view; a case that is one document reads as that document
    corpus = Corpus(folder=Path("."), documents={d["id"]: {"case": d.get("case") or d["id"]} for d in R["index"]})
    cases = {}
    # code steps first, then tabulations, then judgements: rows before the cells that read them
    order = {"code": 0, "tabulate": 1}
    for sid, s in sorted(R["steps"].items(), key=lambda kv: order.get(kv[1].get("kind"), 2)):
        if s.get("kind") == "code":
            for col in s.get("columns", []):
                for v in codes_of(col, R):
                    defs[f"{col['name']}={v['name']}"] = v.get("means", "")
            # a combined table's rows are its inputs' own, drawn once there under the step they were coded in
            for r in [] if s.get("combines") else s.get("rows", []):
                t = R["texts"].get(r["document"], "")
                a, b = r.get("start"), r.get("end")
                if a is not None and t:
                    lo, hi = max(0, a - CONTEXT), min(len(t), b + CONTEXT)
                    ctx = [("…" if lo else "") + t[lo:a], t[a:b], t[b:hi] + ("…" if hi < len(t) else "")]
                else:
                    ctx = ["", r["quote"], ""]
                codes = {c["name"]: r.get(c["name"]) for c in s.get("columns", [])}
                case = corpus.case_of(r["document"], r.get("case")) if r["document"] in corpus.documents else r["document"]
                rows[r["row"]] = {"doc": r["document"], "step": sid, "ctx": ctx, "codes": codes, "case": case,
                                  **({"weak": True} if legacy_weak.carries(old, r) else {})}
                if sid in ends:  # a link's sign as Causal Map reads one: 1, -1, or 0 for unclear or unsigned
                    sign = sign_of(r.get(ends[sid]["sign"])) if ends[sid].get("sign") else "?"
                    rows[r["row"]]["sentiment"] = {"+": 1, "-": -1}.get(sign, 0)
                held = cases.setdefault(case, {"docs": [], "rows": []})
                held["rows"].append(r["row"])
                if r["document"] not in held["docs"]:
                    held["docs"].append(r["document"])
                if a is not None and t:
                    rows[r["row"]]["at"] = [a, b]
                # each code the passage was given, as the key of every passage given the same code in this step, for
                # its chip to open them; a free-text value is kept only where a table counts it alone (pruned below)
                for c in s.get("columns", []):
                    v = r.get(c["name"])
                    if v in (None, ""):
                        continue
                    key = f"{sid}|{c['name']}|{value_key(v)}"
                    code = shared.setdefault(key, {"step": sid, "col": c["name"], "value": v, "rows": [], "cell": None,
                                                   **({"free": True} if c.get("type") == "free_text" else {})})
                    code["rows"].append(r["row"])
                    rows[r["row"]].setdefault("keys", {})[c["name"]] = key
            if sid in R.get("recoded", {}):
                second_reading(s, R["recoded"][sid], R["texts"], rows)
        elif s.get("kind") == "group" and s.get("table") is not None:  # what each item a row was given means
            for col in s.get("item_columns") or ["item"]:
                for it in (s.get("codebook") or {}).get("items", []):
                    defs[f"{col}={it.get('id')}"] = it.get("means", "")
        elif s.get("kind") == "tabulate":
            weak = {x: r["doc"] for x, r in rows.items() if r.get("weak")}
            # a table by one code of its step's passages, unfiltered, holds in each cell every passage given that code,
            # so that code's chip opens the cell itself
            markers = loop_markers(s["cells"]) if s.get("loops") else {}
            plain = len(s.get("by", [])) == 1 and not (s.get("filtered") or s.get("loops") or s.get("paths") or s.get("sequences"))
            for c in s.get("cells", []):
                # legacy_weak: the documents a cell holds only through weak rows, which its count leaves out (steps.tabulate)
                # (a paths cell names its firm rows itself: a path is firm only if firm links alone make it)
                held = set(c["firm_rows"]) if "firm_rows" in c else None
                weak_in = {x: rows[x]["doc"] for x in c.get("rows", []) if x in rows and (x not in held if held is not None else x in weak)}
                firm = {rows[x]["doc"] for x in c.get("rows", []) if x in rows and x not in weak_in}
                cells[c["id"]] = {"values": c["values"], "n": c["n"], "base": base_of(s, c), "said": said_with_unit(s, c),
                                  "unit": unit_of_table(s),
                                  "within": c.get("within") or {}, "docs": c.get("documents", []),
                                  "weak_docs": sorted(set(weak_in.values()) - firm),
                                  "rows": c.get("rows", []), "step": sid,
                                  **({"weak_rows": sorted(weak_in)} if held is not None else {}),
                                  **({"cases": c["cases"]} if "cases" in c else {})}
                if s.get("loops"):
                    cells[c["id"]]["told"] = loop_told(c, markers)
                if plain:
                    col = s["by"][0]
                    code = shared.get(f"{s.get('input')}|{col}|{value_key(c['values'].get(col))}")
                    if code and not code["cell"] and set(code["rows"]) == set(c.get("rows", [])):
                        code["cell"] = c["id"]
            # {<step>.of}, the documents the tabulation read, as the engine takes them from its input step
            src = R["steps"].get(s.get("input"), {})
            read = src.get("documents") or R["steps"].get(src.get("input"), {}).get("documents") or sorted(docs)
            cells[f"{sid}.of"] = {"values": {}, "n": s.get("of"), "base": s.get("of"), "unit": unit_of_table(s),
                                  "said": f'{s.get("of")} {unit_of_table(s)} read', "within": {},
                                  "docs": sorted(read), "rows": [], "step": sid}
            if s.get("count") == "cases" and not s.get("cases_are_documents"):
                cells[f"{sid}.of"]["cases"] = sorted(corpus.cases_held([d for d in read if d in corpus.documents], src.get("rows", [])))
        elif s.get("kind") == "judge":
            # a rule's count opens the passages it was counted from, as a table's cell does, with the rule's question
            for c in s.get("criteria") or []:
                cid = f"{sid}.{c.get('id')}"
                if c.get("kind") != "rule" or cid not in R["counts"] or "rows" not in c:
                    continue
                where = (c.get("counted") or {}).get("where") or {}
                weak = set(c.get("weak") or [])
                cells[cid] = {"values": {k: " or ".join(map(str, v)) if isinstance(v, list) else v for k, v in where.items()},
                              "n": c.get("n"), "base": c.get("base"), "unit": c.get("unit") or "documents",
                              "said": count_said(c.get("n"), c.get("base"), c.get("unit") or "documents"), "within": {},
                              "docs": [d for d in c.get("documents", []) if d not in weak] + sorted(weak),
                              "weak_docs": sorted(weak), "rows": c["rows"], "step": sid, "question": c.get("question", ""),
                              **({"cases": c["cases"]} if "cases" in c else {})}
    # a free-text value is a code to open only where a table counts it alone, as the claims an answer cites are
    shared = {k: c for k, c in shared.items() if not c.pop("free", False) or c["cell"]}
    for r in rows.values():
        if "keys" in r:
            r["keys"] = {col: k for col, k in r["keys"].items() if k in shared}
    # each value a table's cell is counted by that is a code, so the panel can name it as a link to the code's passages
    for c in cells.values():
        src = code_step(R, c["step"]) if R["steps"].get(c["step"], {}).get("kind") == "tabulate" else None
        keys = {col: f"{src}|{col}|{value_key(v)}" for col, v in c["values"].items()} if src else {}
        if any(k in shared for k in keys.values()):
            c["codes"] = {col: k for col, k in keys.items() if k in shared}
    steps = {st["id"]: step_said(st["id"], st.get("kind", "")) for st in R.get("workflow", {}).get("steps", [])}
    # each claim the writer tagged, by the id the answer cites it with, with the passages for it and against it
    claims = {f"{sid}.{c['id']}": {k: c.get(k) for k in ("says", "rows", "against", "found_by", "why")}
              for sid, s in R["steps"].items() if s.get("kind") == "claims" for c in s.get("claims") or []}
    # a case held by one document and named after it is that document, which its own link opens whole
    cases = {k: v for k, v in cases.items() if not (v["docs"] == [k])}
    return {"docs": docs, "rows": rows, "cells": cells, "codes": shared, "cases": cases, "steps": steps, "defs": defs, "claims": claims,
            # whether the passage notes may call the second coder blind: only where the run records a separate one
            "second_blind": procedure.separate(R, "second_coding") is True,
            "group": gcol, "zip": R.get("zip", ""), "ends": ends}


# ---------- the answer: markdown with cell ids and row citations ----------

#: [<row id>, <row id>; ...]: a group of row ids as the engine reads one (`steps.group_ids`); a bracket holding anything
#: else is left as written
CITE = re.compile(r"\[([^\[\]]+)\]")
#: {<id>}: any count the engine made (steps.counts_of is the one list of them); one it did not make is left as written,
#: and a report still holding one is not drawn
CELL = re.compile(r"\{([a-z]\w*(?:(?:\.\w+)+|\[[^\[\]{}\n]*\](?:\.\w+)*))\}")


def cell_of(cid):
    """The table cell a count is read from, for the page to open its passages: none for a judge's count, whose rule
    `build_data` gives a cell of its own where it was counted from passages."""
    base = re.sub(r"\.(?:within\.[\w]+|weak)$", "", cid)
    return base if re.fullmatch(r"[a-z]\w*(?:\.(?:c\d+|of)|\[[^\[\]{}\n]*\])", base) else None
FIG = re.compile(r"^\{\{figure\s+([\w]+)\}\}$")
#: [§ A heading]: a claim that builds on a finding stated in that section of the answer, which is how a revision follows
#: what rests on what (stale.py)
SEE = re.compile(r"\[§\s*([^\]]+)\]")


def anchor(heading):
    return "s-" + "-".join(re.findall(r"[a-z0-9]+", heading.lower()))


#: a count as steps.stated writes it: "n of base", or "n passages" where it counts passages and has no base
SAID = re.compile(r"(\d+) (?:of (\d+)|passages?)")


def heat(pairs, unit="documents"):
    """How a table shows its counts, from each count's (n, base), base None for a count of passages: a shade for each
    count, and the line said once beneath where every count shares one base (plain numbers, shaded by share) or none
    has one (plain numbers, shaded against the largest); the line is None where the bases differ, and each count then
    says its own."""
    top = max([n for n, b in pairs if b is None] + [1])
    bases = {b for _, b in pairs}
    note = None
    if len(pairs) > 1 and len(bases) == 1:
        b = bases.pop()
        note = f"Each number is out of {b} {unit}." if b else "Each number counts coded passages, not documents."
    return (lambda n, b: n / (b or top)), note


#: what emphasis never reaches into, in escaped text: a quotation, a count or citation in its brackets, code, and a
#: factor written with a leading ~
UNEMPHASISED = re.compile(r"“[^”]*”|&quot;.*?&quot;|\{[^{}]*\}|\[[^\[\]]*\]|`[^`]*`|~[^\s,;.]+")
#: *words*, tight against the asterisks on both sides, so that "3 * 4" or a lone * stays as written
EMPHASIS = re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?![\w*])")


def emphasised(out):
    """Escaped text with each *phrase* in italics, leaving quotations, counts, citations, code and ~labels as written."""
    kept = UNEMPHASISED.findall(out)
    return "".join(EMPHASIS.sub(r"<em>\1</em>", part) + (kept[i] if i < len(kept) else "")
                   for i, part in enumerate(UNEMPHASISED.split(out)))


def marked(out):
    """Escaped text with markdown's **strong** and *emphasis* set, the one place the report reads either, for the
    answer, the plain records in the annexes and the map's caption alike."""
    return emphasised(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out))


def inline(text, R, D, cite_no, static, plain=False):
    out = marked(esc(text))
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)

    def cell(m):
        cid = m.group(1)
        if cid not in R["counts"]:
            return m.group(0)
        txt = R["counts"][cid]
        if plain:
            txt = SAID.fullmatch(txt).group(1)
        # a table's cell, or a judgement's rule counted from passages (build_data), opens them
        base = cell_of(cid) or (cid if cid in D.get("cells", {}) else None)
        if R.get("finding") is not None:
            # a count with no cell behind it, such as a judgement's, still names the step that made it
            R["finding"].setdefault("cells" if base else "steps", []).append(base or step_of(cid))
        if static or base not in D.get("cells", {}) or cid.endswith(".weak"):
            return esc(txt)
        col = cid.partition(".within.")[2]
        within = f' data-within="{esc(col)}"' if col else ""
        return f'<button class="n" data-cell="{esc(base)}"{within}>{esc(txt)}</button>'

    def cite(m):
        # On the page, each document cited once by its id, opening its passages in the side panel, where the quotation
        # and the way into the whole interview are; for Word, with the opening words of each quotation
        ids = group_ids(m.group(1))
        if not ids or not all(ROW_ID.fullmatch(i) for i in ids):
            return m.group(0)
        tags = [i for i in ids if i in D.get("claims", {})]  # a claim the writer tagged, opening its passages for and against
        ids = [i for i in ids if i not in tags]
        for k in tags:
            if R.get("finding") is not None:
                R["finding"].setdefault("rows", []).extend(D["claims"][k]["rows"])
        if static:
            tagged = [cited_as(D["rows"].get(i, {}).get("doc", i), D["rows"].get(i, {}).get("ctx", ["", "", ""])[1])
                      for k in tags for i in D["claims"][k]["rows"]]
        else:
            tagged = [f'<button class="cite claim" data-claim="{esc(k)}" title="{esc(CLAIM_SAID)}: {esc(D["claims"][k]["says"])}">'
                      f'{esc(claim_docs(D["claims"][k], D))}</button>' for k in tags]
        if not ids:
            return "(" + "; ".join(esc(x) for x in tagged) + ")" if static else bracketed(tagged)
        by_doc = {}
        for i in ids:
            cite_no.setdefault(i, len(cite_no) + 1)
            if R.get("finding") is not None:
                R["finding"].setdefault("rows", []).append(i)
            by_doc.setdefault(D["rows"].get(i, {}).get("doc", i), []).append(i)
        if static:
            def said(i):
                r = D["rows"].get(i, {})
                ctx = r.get("ctx", ["", "", ""])
                return esc(cited_as(r.get("doc", i), ctx[1], before=ctx[0], after=ctx[2]))
            return "(" + "; ".join([said(i) for i in ids] + [esc(x) for x in tagged]) + ")"
        chips = [f'<button class="cite" data-row="{esc(rs[0])}"' if len(rs) == 1 else
                 f'<button class="cite" data-rows="{esc(",".join(rs))}"' for rs in by_doc.values()]
        return bracketed([f'{c} title="{esc(quoted(d, rs, D))}">{esc(d)}</button>'
                          for c, (d, rs) in zip(chips, by_doc.items())] + tagged)

    def see(m):
        h = html.unescape(m.group(1)).strip()
        if h not in R.get("sections", ()):
            R.setdefault("missing_sections", []).append(h)
        shown = R.get("renamed", {}).get(h, h)
        return f"(see “{esc(shown)}”)" if static else f'<a class="see" href="#{anchor(h)}">§ {esc(shown)}</a>'

    out = CELL.sub(cell, out)
    while (merged := ADJACENT.sub(joined, out)) != out:
        out = merged
    out = NAMED_THEN_CITED.sub(lambda m: named_once(m, D), out)
    out = CITE.sub(cite, out)
    out = SEE.sub(see, out)
    out = UNCHECKED.sub(r"\1" if static else rf'<span class="unchecked" title="{UNCHECKED_SAID}">\1</span>', out)
    return out if static else linked_sources(out, D)


def bracketed(chips):
    """A citation's chips in round brackets, the opening bracket held on the line with the first chip and the closing
    one with the last, so a line never ends on a bare "(" or starts on a bare ")"."""
    if len(chips) == 1:
        return f'<span class="nw">({chips[0]})</span>'
    return (f'<span class="nw">({chips[0]},</span> ' + "".join(f"{c}, " for c in chips[1:-1])
            + f'<span class="nw">{chips[-1]})</span>')


#: The writer's own document ids in round brackets directly before a citation, as "(d01) [c.ab12c]"
NAMED_THEN_CITED = re.compile(r"\(([^()\[\]{}\n]+)\)\s*(?=\[([^\[\]]+)\])")


def named_once(m, D):
    """The writer's round-bracketed document ids left out where the citation after them names exactly those
    documents, which it shows as clickable ids of its own, so a reader never sees "(d01) (d01)"; kept otherwise."""
    named = {x.strip() for x in m.group(1).split(",")}
    ids = group_ids(m.group(2))
    if not named <= set(D.get("docs", {})) or not all(i in D["rows"] or i in D.get("claims", {}) for i in ids):
        return m.group(0)
    cited = {D["rows"][i]["doc"] for i in ids if i in D["rows"]}
    cited |= {D["rows"][r]["doc"] for i in ids if i in D.get("claims", {}) for r in D["claims"][i]["rows"] if r in D["rows"]}
    return "" if named == cited else m.group(0)


#: Two groups of row ids side by side, which a reader sees as one citation
ADJACENT = re.compile(r"\[([^\[\]]+)\]\s*\[([^\[\]]+)\]")


def joined(m):
    """Two groups of row ids written side by side, as one group; anything else as written."""
    a, b = group_ids(m.group(1)), group_ids(m.group(2))
    if a and b and all(ROW_ID.fullmatch(i) for i in a + b):
        return f"[{', '.join(a + b)}]"
    return m.group(0)


def quoted(doc, rows, D):
    """What a citation's id says when pointed at: the opening words of the passages it opens."""
    def one(i):
        ctx = D["rows"].get(i, {}).get("ctx", ["", "", ""])
        return cited_as(doc, ctx[1], before=ctx[0], after=ctx[2]).split(", ", 1)[1]
    return "; ".join(one(i) for i in rows)


#: What a claim's tag is, said where a reader points at it and over the passages it opens
CLAIM_SAID = "A claim the writer tagged with the passages for it and against it"


def claim_docs(c, D):
    """A tagged claim's chip: the documents its passages for it come from, as a citation names them."""
    return ", ".join(dict.fromkeys(D["rows"].get(i, {}).get("doc", i) for i in c["rows"])) or "no passage"


#: Markup a source's id is never linked inside: a button or link, or a tag itself
MARKUP = re.compile(r"(<button\b[^>]*>.*?</button>|<a\b[^>]*>.*?</a>|<[^>]+>)", re.S)


def linked_sources(out, D):
    """The answer's text with every id of a whole source that it names outside a citation, such as a list of who fell
    in a group, a link to that source read whole. Only ids holding a digit are read as ids, so a source named with a
    plain word is never mistaken in running prose."""
    ids = sorted((d for d in D.get("docs", {}) if re.search(r"\d", d)), key=len, reverse=True)
    if not ids:
        return out
    named = re.compile(r"(?<![\w-])(" + "|".join(re.escape(esc(d)) for d in ids) + r")(?![\w-])")
    link = lambda m: (f'<button class="src" data-doc="{m.group(1)}" title="Read {m.group(1)} whole">{m.group(1)}</button>')
    return "".join(p if k % 2 else named.sub(link, p) for k, p in enumerate(MARKUP.split(out)))


def figure(tid, R, D):
    s = R["steps"].get(tid)
    if not s or s.get("kind") != "tabulate":
        R.setdefault("missing_figures", []).append(tid)
        return ""
    if s.get("loops"):
        return loop_diagrams(tid, s, R)
    by = s["by"]
    ends = link_ends(s, R)
    if ends and by in (ends[:2], ends):
        return causal_map(s, s["cells"], by, tid)
    if len(by) > 2:  # a chart shows two columns at most; drawing the first two would drop the rest and mislead
        R.setdefault("wide_figures", []).append(tid)
        return ""
    src = code_step(R, tid)  # its values that are codes name themselves as links to their passages (`code_named`)
    drawn = ordered_chart(s, R, D, src)
    if drawn:
        return drawn
    cells = [c for c in s["cells"]]
    if len(by) == 1:
        rows = sorted(cells, key=lambda c: -c["n"])
        mx = max([base_of(s, c) or c["n"] for c in rows] + [1])
        bars = "".join(
            f'<div class="bar-row"><span class="bar-label">{code_named(D, src, by[0], c["values"][by[0]])}</span>'
            f'<span class="bar-track"><button class="bar" data-cell="{esc(c["id"])}" style="width:{100*c["n"]/mx:.1f}%"></button>'
            + (f'<button class="bar implicit" data-cell="{esc(c["id"])}" style="width:{100*implicit_of(c)/mx:.1f}%"></button>' if implicit_of(c) else "")
            + f'</span><span class="bar-n">{c["n"]}{implicit_said(c, word=False)}</span></div>' for c in rows)
        return f'<figure class="fig"><div class="bars">{bars}</div><figcaption>{caption(s)} Click a bar for its passages.</figcaption></figure>'
    a, b = by[0], by[1]
    avals = list(dict.fromkeys(c["values"][a] for c in cells))
    bvals = list(dict.fromkeys(c["values"][b] for c in cells))
    look = {(c["values"][a], c["values"][b]): c for c in cells}
    if set(bvals) <= {"yes", "no"}:  # a binary split: two bars a value, never stacked, as one document can be in both
        top = max([c["n"] for c in cells] + [1])
        avals.sort(key=lambda v: -sum(look.get((v, x), {"n": 0})["n"] for x in ("yes", "no")))
        yes_l = label(b) + " for this reason"
        out = []
        for v in avals:
            pair = ""
            for x, cls in (("yes", "yes"), ("no", "no")):
                c = look.get((v, x))
                n = c["n"] if c else 0
                w = 100 * n / (base_of(s, c) or top) if c else 0
                btn = f'<button class="bar {cls}" data-cell="{esc(c["id"])}" style="width:{w:.1f}%"></button>' if c and n else ""
                pair += f'<span class="bar-track thin">{btn}</span><span class="bar-n">{n}{implicit_said(c, word=False) if c else ""}</span>'
            out.append(f'<div class="bar-row pair"><span class="bar-label">{code_named(D, src, a, v)}</span><span class="pair-bars">{pair}</span></div>')
        legend = (f'<span class="key yes"></span>{esc(yes_l)} <span class="key no"></span>Raised, not tied to that')
        return (f'<figure class="fig"><div class="legend">{legend}</div><div class="bars">{"".join(out)}</div>'
                f'<figcaption>{caption(s)} Click a bar for the passages behind it.</figcaption></figure>')
    # two nominal columns: a grid of counts within each column of b
    avals.sort(key=lambda v: -sum(look.get((v, x), {"n": 0})["n"] for x in bvals))
    head = "".join(f"<th>{code_named(D, src, b, x)}</th>" for x in bvals)
    body = ""
    shade, note = heat([(c["n"], base_of(s, c)) for c in cells if c["n"]], unit_of_table(s))
    for v in avals:
        tds = ""
        for x in bvals:
            c = look.get((v, x))
            if c and (c["n"] or implicit_of(c)):
                n, base = c["n"], base_of(s, c)
                tds += (f'<td><button class="cellbtn" data-cell="{esc(c["id"])}" style="--a:{shade(n, base) if n else 0:.2f}">{n}'
                        f'{"" if note else f"<small> {esc(base_said(base, unit_of_table(s)))}</small>"}{implicit_said(c, word=False)}</button></td>')
            else:
                tds += '<td class="zero">0</td>'
        body += f"<tr><th>{code_named(D, src, a, v)}</th>{tds}</tr>"
    return (f'<figure class="fig"><div class="scroll"><table class="grid"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<figcaption>{caption(s)} Click a count for its passages.</figcaption></figure>')


#: The most groups a chart along an ordered column draws, one line or one band of columns each; a table with more
#: draws as the grid of counts
MOST_SERIES = 6


def column_def(s, col, R):
    """A tabulated column as the code step it was coded in defines it, or None for a column of the document list."""
    steps = {w.get("id"): w for w in normalise(R.get("workflow", {})).get("steps", [])}
    st = steps.get(s.get("input"), {})
    if st.get("kind") == "group":
        st = steps.get((st.get("inputs") or [None])[0], {})
    return next((c for c in st.get("columns") or [] if isinstance(c, dict) and c.get("name") == col), None)


def wilson(n, base, z=1.96):
    """The 95% interval of a share n of base (Wilson's), which stays inside 0 to 1 and widens as the base shrinks."""
    p, k = n / base, z * z / base
    mid, half = (p + k / 2) / (1 + k), z * ((p * (1 - p) + k / 4) / base) ** .5 / (1 + k)
    return max(0.0, mid - half), min(1.0, mid + half)


def nice_top(m):
    """The top of a count axis: the smallest 1, 2 or 5 times a power of ten at or above the largest count."""
    step = 1
    while True:
        for f in (1, 2, 5):
            if f * step >= m:
                return f * step
        step *= 10


def drawn_from(s, R):
    """How many documents the table's documents were drawn from at random, where a sample step upstream of it drew
    them (`steps.draw` records it); None where they are all the documents there were, or ones chosen on purpose, so
    that no interval suggests they stand for documents nobody read."""
    steps = {w.get("id"): w for w in normalise(R.get("workflow", {})).get("steps", [])}
    sid = s.get("input")
    while sid in steps:
        if R["steps"].get(sid, {}).get("drawn_from"):
            return R["steps"][sid]["drawn_from"]
        sid = (steps[sid].get("inputs") or [None])[0]
    return None


def ordered_chart(s, R, D=None, src=None):
    """A table along an ordered column (`order_of`) drawn in that order: a line a group of the other column, each point
    a cell's share of its own base, with its 95% interval only where the documents were drawn at random (`drawn_from`),
    or its count where the table counts passages; or, where the groups divide the units at each point between them,
    columns stacked to 100% by group, each with how many units it divides. None where no column is ordered, a table of
    one column has fewer than three values, or the groups are more than `MOST_SERIES`, which draw as before."""
    by, cells = s["by"], s["cells"]
    orders = [None if b == "document" else order_of([c["values"][b] for c in cells], column_def(s, b, R)) for b in by]
    i = next((k for k, o in enumerate(orders) if o), None)
    if i is None:
        return None
    kind, xs = orders[i]
    x, g = by[i], (by[1 - i] if len(by) == 2 else None)
    if g is None and len(xs) < 3:
        return None
    look = {(c["values"][x], c["values"][g] if g else None): c for c in cells}
    if g is None:
        groups = [None]
    elif len(orders) == 2 and orders[1 - i]:
        groups = [v for v, _ in orders[1 - i][1]]
    else:
        total = {}
        for c in cells:
            total[c["values"][g]] = total.get(c["values"][g], 0) + c["n"]
        groups = sorted((v for v in total if v != "(blank)"), key=lambda v: -total[v])
    unit = unit_of_table(s)
    share = all(base_of(s, c) is not None for c in cells)
    at = {v: [c for c in cells if c["values"][x] == v] for v, _ in xs}

    def split_whole(v):
        here = [look[(v, gv)] for gv in groups if (v, gv) in look]
        return not here or (len({base_of(s, c) for c in here}) == 1 and sum(c["n"] for c in here) == base_of(s, here[0]))
    # the groups divide the units at each point where their counts there add up to its base, or where every unit of a
    # table with one base is counted once, so that the units at a point are its cells' counts added up, blanks included
    bases = {base_of(s, c) for c in cells}
    once = len(bases) == 1 and sum(c["n"] for c in cells) == min(bases)
    stacked = bool(share and g and (once or all(split_whole(v) for v, _ in xs)))
    if stacked and once and any(c["n"] for c in cells if c["values"][g] == "(blank)"):
        groups.append("(blank)")
    if len(groups) > MOST_SERIES:
        return None
    total_at = {v: sum(c["n"] for c in at[v]) if once else next((base_of(s, c) for c in at[v]), 0) for v in at}
    pool = drawn_from(s, R) if share and not stacked else None
    # drawn small and scaled to fit, its text sized in report.css for a phone, where a character is about 8 units wide
    W, H, L, RM, T, B = 480, 266, 40, 10, 16, 44
    pw, ph = W - L - RM, H - T - B
    even = stacked or kind == "ordinal"
    lo, hi = xs[0][1], xs[-1][1]
    slot = pw / len(xs)
    dodge = 0 if stacked or len(groups) < 2 else 9  # a point's width apart, so equal shares stay apart
    inset = 10 + dodge * (len(groups) - 1) / 2
    px = {v: L + (slot * (k + .5) if even else inset + (p - lo) / (hi - lo) * (pw - 2 * inset)) for k, (v, p) in enumerate(xs)}
    top = 1.0 if share else nice_top(max([c["n"] for c in cells] + [1]))
    py = lambda y: T + ph - y / top * ph
    ticks = [top * k / 4 for k in range(5)] if share or top % 4 == 0 else [top * k / 5 for k in range(6)]
    tick_said = (lambda y: f"{round(100 * y)}%") if share else (lambda y: f"{y:g}")
    out = []
    for y in ticks:
        out.append(f'<line class="rule" x1="{L}" x2="{W - RM}" y1="{py(y):.1f}" y2="{py(y):.1f}"/>'
                   f'<text x="{L - 5}" y="{py(y) + 4:.1f}" text-anchor="end">{tick_said(y)}</text>')
    every = max(1, -(-len(xs) // 8))
    room = max(4, int((slot if even else pw / len(xs)) / 8))
    for k, (v, _) in enumerate(xs):
        if k % every and k != len(xs) - 1:
            continue
        said = label(v)
        short = said if len(said) <= room else said[:room - 1] + "…"
        out.append(f'<text x="{px[v]:.1f}" y="{T + ph + 15}" text-anchor="middle"><title>{esc(said)}</title>{esc(short)}</text>')
    out.append(f'<text class="axis-name" x="{L + pw / 2:.1f}" y="{H - 8}" text-anchor="middle">{esc(label(x))}</text>')

    def point_said(c, gv, v):
        said = count_said(c["n"], total_at[v], unit) if stacked else said_with_unit(s, c)
        return esc(f'{label(gv) + ", " if gv else ""}{label(v)}: {said}')
    if stacked:
        width = min(44.0, slot * .62)
        for v, _ in xs:
            if not total_at[v]:
                continue
            out.append(f'<text x="{px[v]:.1f}" y="{T - 2}" text-anchor="middle">{total_at[v]}</text>')
            y0 = 0.0
            for j, gv in enumerate(groups):
                c = look.get((v, gv))
                if not c or not c["n"]:
                    continue
                h = c["n"] / total_at[v]
                out.append(f'<g class="s{j + 1}" data-cell="{esc(c["id"])}" tabindex="0" role="button" aria-label="{point_said(c, gv, v)}">'
                           f'<title>{point_said(c, gv, v)}</title><rect class="seg" x="{px[v] - width / 2:.1f}" y="{py(y0 + h):.1f}" '
                           f'width="{width:.1f}" height="{py(y0) - py(y0 + h):.1f}"/></g>')
                y0 += h
    else:
        hits, dots = [], []
        for j, gv in enumerate(groups):
            dx = (j - (len(groups) - 1) / 2) * dodge
            pts = [(v, look[(v, gv)]) for v, _ in xs if (v, gv) in look and (not share or base_of(s, look[(v, gv)]))]
            y = lambda c: c["n"] / base_of(s, c) if share else c["n"]
            line = " ".join(f"{px[v] + dx:.1f},{py(y(c)):.1f}" for v, c in pts)
            for v, c in pts:
                cx, cy = px[v] + dx, py(y(c))
                ci = ""
                if pool:
                    a, b = wilson(c["n"], base_of(s, c))
                    ci = (f'<line class="ci" x1="{cx:.1f}" x2="{cx:.1f}" y1="{py(a):.1f}" y2="{py(b):.1f}"/>'
                          f'<line class="ci" x1="{cx - 3:.1f}" x2="{cx + 3:.1f}" y1="{py(a):.1f}" y2="{py(a):.1f}"/>'
                          f'<line class="ci" x1="{cx - 3:.1f}" x2="{cx + 3:.1f}" y1="{py(b):.1f}" y2="{py(b):.1f}"/>')
                # a wide target under every point, so a point is easy to press, and the points above every target, so a
                # point pressed opens its own cell where another series' target reaches it
                hits.append(f'<g data-cell="{esc(c["id"])}"><title>{point_said(c, gv, v)}</title>'
                            f'<circle class="hit" cx="{cx:.1f}" cy="{cy:.1f}" r="11"/></g>')
                dots.append(f'<g class="s{j + 1}" data-cell="{esc(c["id"])}" tabindex="0" role="button" aria-label="{point_said(c, gv, v)}">'
                            f'<title>{point_said(c, gv, v)}</title><circle class="pt" cx="{cx:.1f}" cy="{cy:.1f}" r="4.5"/></g>')
                out.append(f'<g class="s{j + 1}">{ci}</g>')
            out.insert(len(out) - len(pts), f'<polyline class="line s{j + 1}" points="{line}"/>')
        out += hits + dots
    legend = ("" if g is None else '<div class="legend">' + "".join(
        f'<span><span class="key s{j + 1}"></span>{code_named(D, src, g, gv)}</span>' for j, gv in enumerate(groups)) + "</div>")
    if stacked:
        what = (f"Each column shows how the {esc(unit)} at one {esc(label(x).lower())} divide by {esc(label(g).lower())}; "
                f"the number above it is how many there are.")
    elif pool:
        what = (f"Each point is the share of {esc(unit)} in its group, with its 95% interval (Wilson), since the documents "
                f"were drawn at random from {pool}; the interval is wide where a group holds few {esc(unit)}.")
    elif share:
        what = f"Each point is the share of {esc(unit)} in its group."
    else:
        what = "Each point counts coded passages, not documents."
    if any(implicit_of(c) for c in cells):
        what += " Those that say it only implicitly are left out of the count and not drawn; the table under How this was made gives them."
    aria = esc(f"Chart by {label(x)}" + (f" and {label(g)}" if g else ""))
    return (f'<figure class="fig chart">{legend}<svg viewBox="0 0 {W} {H}" role="img" aria-label="{aria}">{"".join(out)}</svg>'
            f'<figcaption>{what} Point at a {"column" if stacked else "point"} for its count; click it for its passages.</figcaption></figure>')


def implicit_of(c):
    """How many more a cell holds only through implicit passages, which its count leaves out (steps.tabulate): a run
    made before 15 October 2026 only (legacy_weak)."""
    k = c.get("weak")
    return k if isinstance(k, int) and not isinstance(k, bool) else 0


def implicit_said(c, word=True):
    """A cell's implicit count said beside its count, never in it: " +2 implicit", or "" where there are none."""
    k = implicit_of(c)
    return f' <span class="implicit">+{k}{" implicit" if word else ""}</span>' if k else ""


IMPLICIT_KEY = "Paler, and + beside a count: those that say it only implicitly, which the count leaves out."


def caption(s):
    """What a figure's counts are, and the base they all share where they share one, after the sentence its author
    wrote saying what the table counts, where there is one."""
    unit = unit_of_table(s)
    note = heat([(c["n"], base_of(s, c)) for c in s["cells"] if c["n"]], unit)[1]
    what = f"{unit[:1].upper() + unit[1:]} in each group" if s.get("count", "documents") != "rows" else "Coded passages in each group"
    out = f"{what}. {note}" if note else f"{what}."
    out = f"{s['description'].rstrip()} {out}" if s.get("description") else out
    return out + (" " + IMPLICIT_KEY if any(implicit_of(c) for c in s["cells"]) else "")


def link_ends(s, R):
    """The two ends of the causal links a tabulation counts, and their sign where the links are signed, when its input
    is a code step that names them."""
    steps = {w.get("id"): w for w in R.get("workflow", {}).get("steps", [])}
    src = steps.get(s.get("input"), {})
    if src.get("kind") == "group":  # a grouped table has the links of the code step it groups
        src = steps.get((src.get("inputs") or [None])[0], {})
    links = src.get("links") or {}
    return [links["from"], links["to"]] + ([links["sign"]] if links.get("sign") else []) if links else None


#: What a workbook for Causal Map holds, said on every button that makes one
XLSX_SAID = ("These links, with the documents they come from and each document's full text, as a workbook Causal "
             "Map's Import XLSX reads. Made in this browser from what the report holds; nothing is sent anywhere. "
             "On a free Causal Map plan an imported project is public, documents included.")


def xlsx_button(step=None, cells=None, title=""):
    """A button beside a links-shaped table that downloads its links and their documents for Causal Map (report.js
    makes the workbook with rubicon_open/causal-map-xlsx.js): every coded row behind a step's table, or behind the
    cells named. The file is named after the report and the first words of the table's title (the step's name as a
    reader sees it, or the loop's), so a report's several downloads keep apart."""
    which = f'data-xlsx-step="{esc(step)}"' if step else f'data-xlsx-cells="{esc("|".join(cells))}"'
    words = re.findall(r"[a-z0-9]+", (title or label(re.sub(r"^[a-z]_", "", step or "loop"))).lower())[:5]
    which += f' data-xlsx-name="{esc("-".join(words) or "links")}"'
    return (f'<p class="xlsx-row"><button class="xlsx" type="button" {which} title="{esc(XLSX_SAID)}">'
            f'Download for Causal Map (.xlsx)</button> <span class="small">holds the documents’ full text</span></p>')


def graph(drawn):
    """A map's DOT, carried in the report for Graphviz to draw in the reader's browser (report.js), with the words a
    reader sees until it is drawn or if it cannot be."""
    return (f'<div class="graph"><pre class="dot" data-engine="{esc(drawn["engine"])}" hidden>{esc(drawn["dot"])}</pre>'
            f'<p class="small drawing">Drawing the map with Graphviz.</p></div>')


def causal_map(s, cells, by, tid):
    a, b = by[:2]
    edges = [{"id": c["id"], "from": c["values"][a], "to": c["values"][b], "n": c["n"],
              **({"sign": sign_of(c["values"][by[2]])} if len(by) == 3 else {}),
              **({"flipped": {**c["flipped"], "of": len(c["rows"])}} if "flipped" in c else {})} for c in cells
             # a row with no cause or no effect is not a link, whatever else it was coded for
             if c["n"] and "(blank)" not in (c["values"][a], c["values"][b])]
    drawn = node.call(DRAW_MAP, {"edges": edges}, "map drawing")
    # the caption's words are map-dot.js's, which the page's map says too
    return (f'<figure class="fig map">{graph(drawn)}<figcaption>{marked(esc(drawn["caption"]))}</figcaption>'
            f'{xlsx_button(step=tid)}</figure>')


#: The most loops one figure line draws, each as its own small diagram
MOST_LOOPS = 6
POLARITY_SAID = {"R": "a reinforcing loop", "B": "a balancing loop", "unknown": "a loop whose polarity is unknown, since a link's sign is unclear"}


def loop_diagrams(tid, s, R):
    """A loop table drawn as causal loop diagrams, one a loop: the loops the answer cites, or else the first in the
    table, up to `MOST_LOOPS`, each named by the marker the answer reads in the table."""
    loops = {}
    for c in s["cells"]:
        loops.setdefault(c["values"]["loop"], []).append(c)
    markers = loop_markers(s["cells"])
    cited = {cell_of(m) for m in CELL.findall(R.get("answer", ""))}
    chosen = [lp for lp, cs in loops.items() if any(c["id"] in cited for c in cs)] or list(loops)
    out = []
    for lp in chosen[:MOST_LOOPS]:
        cs = loops[lp]
        whole = next(c for c in cs if c["values"]["part"] == "whole")

        def edge(c):
            a, sign, b = arrow_parts(c["values"]["link"])
            return {"id": c["id"], "from": a, "to": b, "sign": sign, "n": c["n"]}
        loop = {"marker": markers[lp], "links": [edge(c) for c in cs if c["values"]["part"] == "link"],
                "drivers": [edge(c) for c in cs if c["values"]["part"] == "driver"]}
        svg = graph(node.call(DRAW_MAP, {"loop": loop}, "loop drawing"))
        unit = esc(unit_of_table(s))
        told = f'<button class="n" data-cell="{esc(whole["id"])}">{whole["n"]} of {s["of"]}</button>'
        out.append(f'<figure class="fig map loop">{svg}<figcaption>{esc(markers[lp])}: '
                   f'{esc(POLARITY_SAID[whole["values"]["polarity"]])}, told whole in {told} {unit}. Each arrow is '
                   f'numbered by the {unit} telling that link; a dashed box is a variable outside the loop that drives '
                   f'it. Click an arrow or a factor for its passages.</figcaption>'
                   f'{xlsx_button(cells=[c["id"] for c in cs], title=markers[lp])}</figure>')
    if len(chosen) > MOST_LOOPS:
        R.setdefault("loops_left_out", []).append(f"{tid} ({len(chosen) - MOST_LOOPS} more)")
    return "".join(out)


def heading(R, title):
    """The report's heading, a few words: the answer's own `# ` title, else the agreed question up to its first stop,
    cut to ten words. The question in full goes under it at reading size (`asked`)."""
    if title:
        return title
    q = R["workflow"].get("question_as_agreed", "").strip()
    first = re.split(r"(?<=[?.:;])\s", q, maxsplit=1)[0].rstrip(".:;")
    words = first.split()
    return " ".join(words[:10]) + ("\u2026" if len(words) > 10 else "") or "Rubicon report"


def asked(R, static=False):
    """The agreed question in full, under the heading: shown whole when short, folded after its first sentence when long."""
    q = R["workflow"].get("question_as_agreed", "").strip()
    if not q:
        return ""
    if static or len(q) <= 240:
        return f'<p class="asked"><b>Question</b> {esc(q)}</p>'
    first = re.split(r"(?<=[?.])\s", q, maxsplit=1)
    rest = first[1] if len(first) > 1 else ""
    return (f'<details class="asked"><summary><b>Question</b> {esc(first[0])}</summary>'
            f'<p>{esc(rest)}</p></details>' if rest else f'<p class="asked"><b>Question</b> {esc(q)}</p>')


def n_synthetic(R):
    return sum(1 for d in R["index"] if (d.get("synthetic") or "").strip().lower() == "yes")


def synthetic(R):
    """A notice that the report rests on made-up documents, wherever the index marks any as synthetic."""
    n = n_synthetic(R)
    if not n:
        return ""
    of = "All" if n == len(R["index"]) else f"{n} of the {len(R['index'])}"
    return (f'<p class="synthetic"><b>Synthetic documents.</b> {of} documents were written by Claude to test the method. '
            'They are not records of real people, and nothing in this report is evidence about anyone.</p>')


#: The answer's closing section, on what limits how far it can be relied on, is headed this whatever the writer called it
LIMITATIONS = "Limitations"
#: The heading over everything the report adds after the answer: the evidence matrix, how it was made and what next
ANNEXES = "Annexes"


def limitations_of(headings):
    """The writer's heading for the answer's closing section on its limits, if its last section is one, so the report
    heads it `LIMITATIONS` without changing the answer the zip holds."""
    last = headings[-1] if headings else ""
    return last if LIMITS.search(last) else None


#: Around a numeral written bare in the answer while it is drawn (`unchecked`), and turned into its mark by `inline`
UNCHECKED = re.compile("([^]*)")
UNCHECKED_SAID = "The writer's own number, not counted by fixed rules"


def unchecked(R):
    """The answer with each numeral the recount found written bare (`numbers_written_bare_at`) set between markers,
    outside headings, which `inline` draws as a light mark: a number code neither made nor checked, never a fault."""
    text = R["answer"].replace("\r\n", "\n")
    at = ((R.get("report") or {}).get("answer") or {}).get("numbers_written_bare_at") or []
    heads = [m.span() for m in re.finditer(r"(?m)^#{1,6} .*$", text)]
    for a, b in sorted(at, reverse=True):
        if not any(h0 <= a < h1 for h0, h1 in heads) and re.fullmatch(r"[\d.%]+", text[a:b]):
            text = text[:a] + "\ue000" + text[a:b] + "\ue001" + text[b:]
    return text


def answer_html(R, D, static=False):
    lines = unchecked(R).splitlines()
    heads = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    R["sections"] = set(heads)
    renamed = R["renamed"] = {h: LIMITATIONS for h in [limitations_of(heads)] if h}
    # The answer's sections, for the report's contents: anchor and heading as the reader sees it
    R["toc"] = [(anchor(h), renamed.get(h, re.sub(r"[*`]", "", h))) for h in heads]
    title, lead, parts, cite_no = "", "", [], {}
    para, items, rows = [], [], []
    # What each finding rests on, the short answer and each section, for its Evidence button (report.js)
    based = D.setdefault("based", {})
    R["finding"] = based.setdefault("short", {})

    def flush():
        nonlocal para, items, rows
        if rows:
            raw = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows if not re.fullmatch(r"[\s|:-]+", r)]
            # a cell that is one count alone; where all of them share a base, each shows its number shaded by its share
            alone = {(i, j): (int(s.group(1)), s.group(2) and int(s.group(2))) for i, r in enumerate(raw[1:]) for j, c in enumerate(r)
                     if (m := CELL.fullmatch(c)) and (s := SAID.fullmatch(str(R["counts"].get(m.group(1), ""))))}
            shade, note = heat(list(alone.values()))

            def td(i, j, c):
                if not (note and (i, j) in alone):
                    return f"<td>{inline(c, R, D, cite_no, static)}</td>"
                return f'<td class="heat" style="--a:{shade(*alone[i, j]):.2f}">{inline(c, R, D, cite_no, static, plain=True)}</td>'
            parts.append('<table class="md"><thead><tr>' + "".join(f"<th>{inline(c, R, D, cite_no, static)}</th>" for c in raw[0])
                         + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(td(i, j, c) for j, c in enumerate(r)) + "</tr>" for i, r in enumerate(raw[1:]))
                         + "</tbody></table>" + (f'<p class="small">{note}</p>' if note else ""))
        if para:
            parts.append(f"<p>{inline(' '.join(para), R, D, cite_no, static)}</p>")
        if items:
            parts.append("<ul>" + "".join(f"<li>{inline(i, R, D, cite_no, static)}</li>" for i in items) + "</ul>")
        para, items, rows = [], [], []

    for ln in lines:
        s = ln.rstrip()
        if s.startswith("# "):
            flush(); title = s[2:]; continue
        if s.startswith("## "):
            flush()
            key = anchor(s[3:].strip())
            R["finding"] = based.setdefault(key, {})
            shown = esc(renamed[s[3:].strip()]) if s[3:].strip() in renamed else inline(s[3:], R, D, cite_no, static)
            parts.append(f'<h2 id="{key}">{shown}'
                         + ("" if static else f'<button class="based" data-based="{key}">Evidence</button>') + "</h2>")
            continue
        m = FIG.match(s.strip())
        if m:
            flush(); parts.append("" if static else figure(m.group(1), R, D)); continue
        if s.lstrip().startswith("|"):
            if para or items:
                flush()
            rows.append(s); continue
        if rows:
            flush()
        if s.startswith("- "):
            if para:
                flush()
            items.append(s[2:]); continue
        if not s.strip():
            flush(); continue
        if items:
            items[-1] += " " + s.strip()
        else:
            para.append(s.strip())
    flush()
    R["finding"] = None
    # the first paragraph is the short answer
    if parts and parts[0].startswith("<p>"):
        lead = parts.pop(0)
        if based["short"] and not static:
            lead = lead[:-4] + ' <button class="based" data-based="short">Evidence</button></p>'
    for key, f in list(based.items()):
        for k in f:
            f[k] = list(dict.fromkeys(f[k]))
        if not f:
            del based[key]
            parts = [p.replace(f'<button class="based" data-based="{key}">Evidence</button>', "") for p in parts]
    R["unfilled"] = sorted(set(CELL.findall(title + lead + "".join(parts))))
    return title, lead, "\n".join(parts), cite_no


# ---------- the evidence matrix: every document against every value of the first passage-level code ----------

def matrix(R, D):
    step_id, step = next(((k, s) for k, s in R["steps"].items() if s.get("kind") == "code" and len(s.get("rows", [])) > len(s.get("documents", []))), (None, None))
    if not step:
        return ""
    nominal = next((c for c in step["columns"] if c["type"] == "nominal"), None)
    binary = next((c for c in step["columns"] if c["type"] == "binary"), None)
    if not nominal:
        return ""
    vals = list(column_values(nominal) or [])
    old = legacy_weak.in_report(R)  # legacy_weak
    by = {}
    for r in step["rows"]:
        by.setdefault((r["document"], r[nominal["name"]]), []).append(r)
    vals.sort(key=lambda v: -len({d for (d, x) in by if x == v}))
    groups = {}
    for d in R["index"]:
        groups.setdefault(d.get(D["group"], ""), []).append(d["id"])
    head = "".join(f'<th><span>{code_named(D, step_id, nominal["name"], v)}</span></th>' for v in vals)
    body = ""
    for g, ids in groups.items():
        body += f'<tr class="band"><th colspan="{len(vals)+1}">{esc(label(g))}</th></tr>'
        for did in ids:
            tds = ""
            for v in vals:
                rs = by.get((did, v), [])
                if not rs:
                    tds += "<td></td>"; continue
                own = binary and any(r.get(binary["name"]) == "yes" for r in rs)
                implicit = all(legacy_weak.carries(old, r) for r in rs)  # legacy_weak: held only through implicit passages
                rid = ",".join(r["row"] for r in rs)
                why = f"Coded {label(nominal['name'])}: {label(v)} in {did}" + (", only implicitly" if implicit else "")
                tds += (f'<td><button class="dot {"own" if own else "raised"}{" implicit" if implicit else ""}" data-rows="{esc(rid)}" data-why="{esc(why)}" '
                        f'aria-label="{esc(did)}: {esc(label(v))}, {len(rs)} passage{"s" if len(rs) > 1 else ""}{", implicit" if implicit else ""}">'
                        f'{len(rs) if len(rs) > 1 else ""}</button></td>')
            body += (f'<tr><th class="doc"><button class="doclink" data-doc="{esc(did)}" title="Read {esc(did)} whole">'
                     f'{esc(did)}</button></th>{tds}</tr>')
    key = (f'<span class="dot own k"></span>{esc(label(binary["name"]))} for this reason'
           ' <span class="dot raised k"></span>Raised, not tied to that') if binary else ""
    if any(legacy_weak.carries(old, r) for r in step["rows"]):  # legacy_weak
        key += (" " if key else "") + '<span class="dot raised implicit k"></span>Only implicitly, so left out of the counts'
    return (f'<div class="legend small">{key}</div><div class="scroll"><table class="matrix"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ---------- the annex: how it was made ----------

#: What each kind of step makes, as the Rubicon page names a step's result (webapp/rubicon/js/model.js PIECE_MADE)
MADE = {"sample": "documents drawn", "code": "rows", "group": "codebook", "profile": "profile", "tabulate": "table", "judge": "verdicts",
        "claims": "claims",
        "write": "answer", "recode": "rows", "check": "record"}


def record_html(text):
    """A plain record such as check.md, which cites no counts and no rows, as paragraphs, lists and headings."""
    out, para, items = [], [], []
    def flush():
        nonlocal para, items
        if para:
            out.append(f"<p>{marked(esc(' '.join(para)))}</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{marked(esc(i))}</li>" for i in items) + "</ul>")
        para, items = [], []
    for ln in text.splitlines():
        t = ln.strip()
        if t.startswith("#"):
            flush()
            if not t.startswith("# "):
                out.append(f"<h5>{marked(esc(t.lstrip('#').strip()))}</h5>")
        elif t.startswith("- "):
            if para:
                flush()
            items.append(t[2:])
        elif not t:
            flush()
        elif items:
            items[-1] += " " + t
        else:
            para.append(t)
    flush()
    return "".join(out)


def drawn_steps(R):
    """The workflow's steps, and for a checked run the check's own after them: the second coder's blind coding, where
    the run had one (`procedure.second_coded`), and the check that ruled on where the two codings differ, or read the
    answer against the documents where it was the whole second reading, and corrected the rows and the answer, which the
    answer reads. The second coder's rows count as made only where the zip holds them. The Rubicon page adds the same to a run it opens from its zip (`model.piecesFromBundle`)."""
    steps = R["workflow"].get("steps", [])
    if not R.get("check"):
        return steps
    second = [{"id": "second_coding", "kind": "recode", "inputs": []}] if procedure.second_coded(R) else []
    check = {"id": "check", "kind": "check", "inputs": [st["id"] for st in steps if st.get("kind") == "code"] + [s["id"] for s in second]}
    inputs = lambda st: list(st.get("inputs") or ([st["input"]] if st.get("input") else []))
    return [dict(st, inputs=inputs(st) + ["check"]) if st.get("kind") == "write" else st for st in steps] + second + [check]


def map_elements(R):
    """The workflow as the margin map draws it: a node for each step and one for its result, an edge from each result
    a step reads to that step and from each step to its result. The same elements the Rubicon page builds for a run
    opened from its zip (model.piecesOf's view through graph.elementsFor), so the map in the report and the map on the
    page are one picture."""
    steps = drawn_steps(R)
    ids = {st["id"] for st in steps}
    made = set(R["steps"]) | ({"check"} | ({"second_coding"} if R.get("recoded") else set()) if R.get("check") else set())
    def reads(st):
        cols = [c.get("values")[9:] for c in st.get("columns", []) if str(c.get("values", "")).startswith("codebook:")]
        return [i for i in dict.fromkeys(list(st.get("inputs") or ([st["input"]] if st.get("input") else [])) + cols) if i in ids]
    eaten = {i for st in steps for i in reads(st)}
    nodes, edges, seen = [], [], set()
    def asset(st_id, kind):
        if st_id in seen:
            return
        seen.add(st_id)
        # A result not made is named and typed as the page names one, by its step alone
        there = st_id in made
        nodes.append({"data": {"id": f"asset:{st_id}", "label": f"{MADE.get(kind, kind)} of {st_id}" if there
                               else st_id.replace("_", " "), "kind": "asset",
                               "type": kind if there else "", "quotes": 0, "missing": not there, "coming": 0,
                               "answer": st_id in made and st_id not in eaten}})
    kinds = {st["id"]: st.get("kind", "") for st in steps}
    for st in steps:
        nodes.append({"data": {"id": f"step:{st['id']}", "label": st["id"].replace("_", " "), "kind": "step",
                               "type": st.get("kind", ""),
                               "status": "succeeded" if st["id"] in made or st["id"] == "second_coding" else "not run",
                               "declaredId": st["id"]}})
        for i in reads(st):
            asset(i, kinds[i])
            edges.append({"data": {"id": f"e:{i}->{st['id']}", "source": f"asset:{i}", "target": f"step:{st['id']}"}})
        asset(st["id"], st.get("kind", ""))
        edges.append({"data": {"id": f"e:{st['id']}->{st['id']}", "source": f"step:{st['id']}", "target": f"asset:{st['id']}"}})
    # each earlier run a step was taken from, one node above the steps taken from it, as the Rubicon page draws one
    for st in steps:
        ref = st.get("from") if isinstance(st.get("from"), dict) else None
        if ref and ref.get("fingerprint"):
            rid = f"run:{ref['fingerprint']}"
            if not any(n["data"]["id"] == rid for n in nodes):
                nodes.append({"data": {"id": rid, "label": f"earlier run\n{ref.get('run_id') or ref['fingerprint'][:8]}",
                                       "kind": "run", "runId": ref["fingerprint"]}})
            edges.append({"data": {"id": f"e:{rid}->{st['id']}", "source": rid, "target": f"step:{st['id']}"}})
    return nodes + edges


def passages_of(step):
    """A code step's passages, folded by the values of its first nominal column."""
    nominal = next((c for c in step.get("columns", []) if c["type"] == "nominal"), None)
    if not nominal:
        lis = "".join(f'<li><button class="rowlink" data-row="{esc(r["row"])}">{esc(r["document"])}</button> {esc(r["quote"])}</li>' for r in step.get("rows", []))
        return f'<ul class="quotes">{lis}</ul>'
    out = []
    for v in column_values(nominal) or []:
        rs = [r for r in step["rows"] if r[nominal["name"]] == v]
        if rs:
            lis = "".join(f'<li><button class="rowlink" data-row="{esc(r["row"])}">{esc(r["document"])}</button> {esc(r["quote"])}</li>' for r in rs)
            out.append(f'<details><summary>{named(v)} <span class="small">{len(rs)} passages</span></summary><ul class="quotes">{lis}</ul></details>')
    return "\n".join(out)


def table_of(sid, s, D, R, static=False):
    """A tabulate step's table: one row per cell, each count a button that opens who it counts, or for Word the count."""
    by = s.get("by", [])
    head = "".join(f"<th>{esc(label(b))}</th>" for b in by)
    # each count shaded by its share of its base, or against the largest where it counts passages, as every other
    # table of counts in the report is (`heat`); Word gets the plain numbers
    shade = heat([(c["n"], base_of(s, c)) for c in s.get("cells", [])])[0]
    src = code_step(R, sid)
    trs = "".join("<tr>" + "".join(f'<td>{code_named(D, src, b, c["values"].get(b, ""), static)}</td>' for b in by)
                  + (f'<td>{c["n"]}' if static else f'<td><button class="num" data-cell="{esc(c["id"])}" '
                     f'style="--a:{shade(c["n"], base_of(s, c)):.2f}">{c["n"]}</button>')
                  + (f' of {b}' if (b := base_of(s, c)) is not None else '') + implicit_said(c) + '</td></tr>'
                  for c in s.get("cells", []))
    return (f'<div class="scroll"><table class="codebook"><thead><tr>{head}<th>{esc(label(unit_of_table(s)))}</th>'
            f'</tr></thead><tbody>{trs}</tbody></table></div>')


def grouped(sid, st, s, step_link):
    """A group step's codebook: each item with what it means, counts and does not count and the open labels it gathers,
    then the labels left over with why, and what the recount found unplaced or named twice."""
    book = s.get("codebook") or {}
    items = [it for it in book.get("items", []) if isinstance(it, dict)]
    ch = s.get("checks") or {}
    keys = st.get("key_column") if isinstance(st.get("key_column"), list) else [st.get("key_column")]
    gathered = {}
    for row in s.get("table") or []:  # the labels each item holds, as code placed them
        for k in keys:
            item = row.get("item") if len(keys) == 1 else row.get(f"{k}_item")
            if row.get(k):
                gathered.setdefault(item, []).append(str(row[k]))
    out = [f'<h4>{esc(step_said(sid, "group"))}</h4>'
           f'<p class="small">The {esc(" and ".join(label(k).lower() for k in keys if k))} labels of {step_link(s.get("input"))}, '
           f'{ch.get("labels", 0)} distinct labels on {ch.get("rows", 0)} passages, drawn into {len(items)} items'
           + (", and each passage given the item its label is listed under." if s.get("table") is not None else ".") + "</p>"]
    trs = "".join(f'<tr><th>{esc(label(str(it.get("id", ""))))}<div class="small">{esc(it.get("label", ""))}</div></th>'
                  f'<td>{esc(it.get("means", ""))}</td><td>{esc(it.get("counts", ""))}</td><td>{esc(near_misses(it.get("does_not_count", "")))}</td>'
                  f'<td>{esc(", ".join(dict.fromkeys(gathered.get(it.get("id")) or it.get("from_labels") or [])))}</td></tr>' for it in items)
    out.append('<div class="scroll"><table class="codebook"><thead><tr><th>Item</th><th>Means</th><th>Counts</th><th>Does not count</th>'
               f'<th>Open labels it gathers</th></tr></thead><tbody>{trs}</tbody></table></div>')
    left = [u for u in book.get("unplaced", []) if isinstance(u, dict)]
    if left:
        out.append("<p>Left in no item: " + "; ".join(esc(str(u.get("label") or u.get("row") or "")) + (f" ({esc(u['reason'])})" if u.get("reason") else "")
                                                     for u in left) + ".</p>")
    said = [(ch.get("labels_unaccounted"), "Labels the codebook neither places nor leaves over"),
            (ch.get("placed_under_two_items"), "Labels or passages listed under two items, so given neither"),
            (ch.get("labels_invented"), "Labels the codebook names that no passage carries")]
    out += [f'<p class="small">{what}: {esc("; ".join(map(str, got)))}.</p>' for got, what in said if got]
    if book.get("notes"):
        out.append(f'<details><summary>What the grouping merged, split or left alone</summary><p>{esc(str(book["notes"]))}</p></details>')
    return "".join(out)


def judged(sid, s, D, static=False):
    """A judgement's block under How this was made: where its rule came from, each criterion's question with its count
    (opening the passages it was counted from) and the level it reached, the verdict and why, and the levels in full."""
    def count(c):
        cid = f"{sid}.{c.get('id')}"
        said = ("" if c.get("n") is None
                else f"{c['n']} of {c['base']}, as {c.get('document')} states it" if c.get("kind") == "stated"
                else count_said(c["n"], c["base"], c.get("unit") or "documents"))
        return said if static or cid not in D["cells"] else f'<button class="num" data-cell="{esc(cid)}">{esc(said)}</button>'
    def rows(ids):
        return rowlinks(ids, D, static)

    def reading(c):
        # a reading has no count to open: it shows why it reached its level and the passages it weighed, each opening
        if c.get("kind") != "reading":
            return ""
        out = f'<br><span class="small">{esc(c.get("why", ""))}'
        out += f' Rests on: {rows(c["rows"])}.' if c.get("rows") else ""
        out += f' Against: {rows(c["against"])}.' if c.get("against") else ""
        return out + "</span>"

    crits = "".join(f'<li>{esc(c.get("question", c.get("id", "")))} {count(c)}'
                    + (f' <span class="small">· level met: {esc(c["verdict"])}</span>' if c.get("verdict") not in (None, "") else "")
                    + reading(c) + "</li>"
                    for c in s.get("criteria") or [])
    levels = "".join(f'<tr><th>{esc(v.get("name", ""))}</th><td>{esc(v.get("means", ""))}</td></tr>' for v in s.get("verdicts") or [])
    return (f'<h4>{esc(step_said(sid, "judge"))}</h4>'
            + (f'<p class="small">{esc(s["source"])}</p>' if s.get("source") else "")
            + (f"<ul>{crits}</ul>" if crits else "")
            + (f'<p>Verdict: <b>{esc(s["overall"])}</b>' + (f', since {esc(s["overall_why"])}' if s.get("overall_why") else "") + ".</p>"
               if s.get("overall") else "")
            + (f'<details><summary>The verdicts the rule could reach</summary><div class="scroll"><table class="codebook">'
               f'<tbody>{levels}</tbody></table></div></details>' if levels and not static else ""))


def rowlinks(ids, D, static=False):
    """Passages by id, each named by its document and opening it, as a reading or a claim lists what it rests on."""
    if static:
        return ", ".join(esc(D["rows"].get(i, {}).get("doc", i)) for i in ids)
    return ", ".join(f'<button class="rowlink" data-row="{esc(i)}">{esc(D["rows"].get(i, {}).get("doc", i))}</button>' for i in ids)


def tagged(sid, s, D, static=False):
    """A claims step's block under How this was made: each claim the writer tagged, what it says, the passages for it
    and against it, how they would be found again and why they bear it out."""
    def one(c):
        out = f'<li>{esc(c.get("says") or c.get("id", ""))}<br><span class="small">{esc(c.get("why", ""))}'
        out += f' Rests on: {rowlinks(c["rows"], D, static)}.' if c.get("rows") else ""
        out += f' Against: {rowlinks(c["against"], D, static)}.' if c.get("against") else ""
        out += f' Found by: {esc(c["found_by"])}' + ("" if c["found_by"].rstrip().endswith(".") else ".") if c.get("found_by") else ""
        return out + "</span></li>"
    items = "".join(one(c) for c in s.get("claims") or [])
    return f'<h4>{esc(step_said(sid, "claims"))}</h4>' + (f"<ul>{items}</ul>" if items else '<p class="small">No claim was tagged.</p>')


METHOD_INTRO = ("The analysis was written down as a workflow before it was counted: what to look for, how to code it, what to "
                "count. It was then counted directly from the coded passages rather than by the AI, so anyone can check a "
                "number, and another coder can follow the same definitions and code the interviews afresh.")
#: The same, for a run whose passages were cited by the AI for an answer it had already written (a code step's `cited`)
CITED_INTRO = ("The answer was written first, and the passages each of its numbers rests on were cited afterwards. Each count "
               "was then made directly from the passages cited rather than by the AI, so anyone can check a number against "
               "the passages behind it. Whether the passages cited are all that the documents hold on each point is not checked.")


def cited(R) -> bool:
    """Whether the run's passages were cited for an answer already written rather than coded from the documents."""
    return any(st.get("cited") for st in (R.get("workflow") or {}).get("steps", []) if st.get("kind") == "code")

RECORD_CHECK = ("It is the SHA-256 of the zip's SHA256SUMS file, which lists the SHA-256 of every other file in the zip, so "
                "changing any file breaks the match. To check that the zip is the one this report was created from, unzip it, run "
                "<code>sha256sum -c SHA256SUMS</code>, then <code>sha256sum SHA256SUMS</code>, and compare the result with the "
                "fingerprint above. Rubicon's own fixed rules check the rest: <code>python verify.py "
                "&lt;report&gt; &lt;zip&gt;</code> recounts every number from the coded passages in the zip, creates "
                "the report again from the zip and says whether it matches this one exactly.")


def hashed(*shown):
    return hashlib.sha256(json.dumps(shown, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def step_key(st, s):
    """What a step shows in the annex, as a key, or None where it shows nothing a combined report could draw once. It is
    what the step shows (its instruction, columns, passages or cells), not its name or the steps that feed it, so two
    runs that coded the same documents the same way share one."""
    if st.get("kind") == "code" and s.get("rows"):
        return hashed("code", st.get("prompt"), st.get("per_document"), st.get("columns"), s.get("combines"),
                      s.get("rows_by_coding"), s["rows"])
    if st.get("kind") == "tabulate" and s.get("cells"):
        return hashed("tabulate", st.get("count"), st.get("unit"), st.get("by"), s["cells"])
    return None


def column_key(col):
    """A coded column's codebook as a key, or None for a column without a list of codes, which is a line and not a table."""
    return hashed("codebook", col) if col.get("values") else None


def annex_keys(R):
    """What this annex shows that another annex of a combined report (bind.py) may show too, as {key: step id, or None
    for a section that is not a step}: its steps (`step_key`) and the sections that say the same in every run that read
    the same documents. `annex` draws a key once and points to it from the annexes that follow."""
    keys = {}
    for st in R["workflow"]["steps"]:
        for key in [step_key(st, R["steps"].get(st["id"], {}))] + [column_key(c) for c in st.get("columns", [])]:
            if key:
                keys.setdefault(key, st["id"])
    keys[hashed("read", [d["id"] for d in R["index"]], *(["cited"] if cited(R) else []))] = None
    keys[hashed("method", *(["cited"] if cited(R) else []))] = None
    keys[hashed("record")] = None
    return keys


def gave(R):
    """What each document gave a run whose passages were cited for an answer already written: the documents with a
    passage cited, those the AI marked as read with nothing bearing on the question, in its own word, which code
    cannot check, and those neither."""
    docs = [d["id"] for d in R["index"]]
    held = {r["document"] for s in R["steps"].values() if s.get("kind") == "code" for r in s.get("rows", [])}
    said = set((R.get("read") or {}).get("nothing_relevant", [])) - held
    neither = [d for d in docs if d not in held and d not in said]
    lines = [f"{len([d for d in docs if d in held])} of {len(docs)} with a passage cited."]
    if R.get("read") is not None:
        lines.append(f"{len(said)} marked by the AI that wrote the answer as read, with nothing in them bearing on the "
                     f"question: its own word, which the fixed rules do not check{': ' + esc(', '.join(sorted(said))) if said else ''}.")
    lines.append(f"{len(neither)} neither cited nor marked{': ' + esc(', '.join(neither)) if neither else ''}."
                 if R.get("read") is not None or neither else "")
    return "<h4>What each document gave</h4><p>" + " ".join(x for x in lines if x) + "</p>"


#: What an agreement can name of the run besides a declared step (`tools.held` in the MCP server), as a reader sees it
HELD_SAID = {"question": "The question", "documents": "The documents", "definitions": "The definitions",
             "answer": "The answer as drafted"}


def held_now(R, name):
    """What the run's zip holds under a name an agreement gives, in the form the server kept it then (`tools.held`)."""
    steps = {s.get("id"): s for s in R["workflow"].get("steps", [])}
    return {"question": lambda: R["workflow"].get("question_as_agreed"), "documents": lambda: [d["id"] for d in R["index"]],
            "definitions": lambda: steps.get("c", {}).get("columns") or [],
            "answer": lambda: R["answer"]}.get(name, lambda: steps.get(name))()


def unchanged(name, then, now):
    """Whether what the evaluator agreed is still what the run holds: a column defined since is no change to the
    definitions agreed, whether they were agreed as the definitions or as the code step that holds them, and nor is
    the date written into a judge step once its rubric is agreed."""
    def columns_kept(then_cols, now_cols):
        now_cols = {c.get("name"): c for c in now_cols or []}
        return all(now_cols.get(c.get("name")) == c for c in then_cols or [])
    if name == "definitions":
        return columns_kept(then, now)
    if isinstance(then, dict):
        rest = lambda s: {k: v for k, v in (s or {}).items() if k not in ("accepted", "columns")}
        return rest(then) == rest(now) and columns_kept(then.get("columns"), (now or {}).get("columns"))
    return then == now


def as_agreed(name, then):
    """What the run held when the evaluator agreed it, for where it has changed since."""
    if name == "definitions":
        return "<ul>" + "".join(f'<li><b>{esc(label(c.get("name", "")))}</b>: {esc(c.get("means", ""))}'
                                + ("".join(f'<br>{esc(label(v.get("name", v) if isinstance(v, dict) else v))}'
                                           + (f': {esc(v["means"])}' if isinstance(v, dict) and v.get("means") else "")
                                           for v in c.get("values") or [])) + "</li>" for c in then) + "</ul>"
    if isinstance(then, list):
        return f"<p>{esc(', '.join(map(str, then)))}</p>"
    if isinstance(then, dict):
        return f'<pre class="small">{esc(json.dumps(then, indent=1, ensure_ascii=False))}</pre>'
    return f'<blockquote>{esc(then).replace(chr(10), "<br>")}</blockquote>'


def agreed(records, R=None, static=False):
    """Each thing put to the evaluator to agree, with their answer as the record holds it. What they agreed is shown
    from the run: where it is unchanged, by pointing to where this report shows it, and where it changed afterwards, as
    the run held it then. A record a run of pieces keeps, or one the plugin kept before 16 October 2026, holds instead
    the words it was put in (`text`), shown as they are."""
    kinds = {s.get("id"): s.get("kind", "") for s in ((R or {}).get("workflow") or {}).get("steps", [])}
    def link(sid, said):
        return said if static else f'<a href="#{procedure.anchor(sid)}">{said}</a>'
    where = {"question": "as shown at the head of this report", "documents": "as shown under What was read",
             "answer": "as this report gives it"}
    def shown(a):
        if "held" not in a:
            return f'<blockquote>{esc(a.get("text", "")).replace(chr(10), "<br>")}</blockquote>'
        out = []
        for name, then in (a.get("held") or {}).items():
            said = esc(HELD_SAID.get(name) or step_said(name, kinds.get(name, "")))
            if R is not None and unchanged(name, then, held_now(R, name)):
                out.append(f"<li>{link(name, said)}, as this report shows it.</li>" if name not in HELD_SAID else
                           f"<li>{said}, {where[name]}.</li>" if name in where else
                           f"<li>{said}, as shown under {link('c', esc(step_said('c', kinds.get('c', 'code'))))}.</li>")
            else:
                out.append(f"<li>{said}, since changed. As they agreed it:{as_agreed(name, then)}</li>")
        how = ("" if not out else
               " Their app showed them each, as the run held it, in a panel the server drew; they were asked to answer in the chat."
               if a.get("shown_in") == "app view" else "" if not a.get("asked") else
               " Each was set out to them only by the AI that asked, so that it was shown is the AI's word."
               if a.get("via") else " The form their app showed them gave each as the run held it.")
        return f'<ul class="small">{"".join(out)}</ul>' + (f'<p class="small">{how.strip()}</p>' if how else "") if out else ""
    def answer(a):
        if not a.get("asked"):
            return "The app the evaluator used could not show them the question, so no answer of theirs is recorded."
        said = ({"question cards": "Put to the evaluator in question cards their app showed them; their answer is as the AI "
                                   "that asked recorded it. ",
                 "chat": "Put to the evaluator in the chat; their answer is as the AI that asked recorded it. "}.get(a.get("via"))
                or "Put to the evaluator in a form their own app showed them, outside the AI's chat. ")
        if a.get("action") == "decline":
            return said + "They declined to agree."
        if a.get("action") != "accept":
            return said + "They closed it without answering."
        changes = (a.get("changes") or "").strip()
        asked = f" They asked for this change: {esc(changes.rstrip('.'))}." if changes else ""
        if "answers" in a:  # one choice for each question put to them
            return said + "They answered: " + "; ".join(
                f'{esc(q.get("question", ""))} <i>{esc(q.get("chosen") or "no choice")}</i>' for q in a["answers"]) + "." + asked
        return said + (("They agreed" if a.get("agree") else "They did not agree") + (f", asking for this change: {esc(changes.rstrip('.'))}" if changes else
                (" as it stood" if a.get("agree") else "")) + ".")
    return "".join(f'<p><b>{esc(a.get("what", ""))}</b> ({esc(a.get("at", ""))}). {answer(a)}</p>{shown(a)}' for a in records)


def annex(R, D, static=False, earlier=None, number=None):
    """The annex: how the answer was made, step by step, and the record of the run. In a combined report `earlier` is
    {key: (annex number, step id)} for what the annexes before this one already show (`annex_keys`), and `number` is this
    annex's: a step, codebook or section drawn identically there, or above in this annex, is not drawn again, and says
    where it is. Passages a step only puts together from other steps (`combines`) are listed under those."""
    wf = R["workflow"]
    old = legacy_weak.in_report(R)  # legacy_weak
    out = []
    n = len(R["index"])
    combined = earlier is not None
    seen = dict(earlier or {})  # what is drawn so far: the earlier annexes' and this one's own
    kinds = {st["id"]: st.get("kind", "") for st in wf["steps"]}
    def step_link(sid):
        name = esc(step_said(sid, kinds.get(sid, "code")))
        return name if static else f'<a href="#{procedure.anchor(sid)}">{name}</a>'
    def again(key, what):
        """A pointer to where this is drawn already, or None where it is drawn here."""
        if key not in seen:
            return None
        j, sid = seen[key]
        if j == number:
            where = step_link(sid)
        else:
            where = f"Annex {j}"
            if not static:
                where = f'<a href="#p{j}-{procedure.anchor(sid)}">{where}</a>' if sid else f'<a href="#annex-{j}">{where}</a>'
        return f'<p class="small shared">{what} {where}.</p>'
    gcounts = {}
    for d in R["index"]:
        gcounts[d.get(D["group"], "")] = gcounts.get(d.get(D["group"], ""), 0) + 1
    gutter = "" if static else '<div class="wf-gutter"></div>'
    said = again(hashed("method", *(["cited"] if cited(R) else [])), "The method is the same as in")
    out.append(f'<div class="method" id="method"><h3>{STEP_BY_STEP}</h3>' + (said or f"<p>{CITED_INTRO if cited(R) else METHOD_INTRO}</p>") + gutter)
    given = "given to the AI that wrote the answer" if cited(R) else "read in full"
    said = again(hashed("read", [d["id"] for d in R["index"]], *(["cited"] if cited(R) else [])), f"The same {n} documents, {given}, as in")
    out.append("<h4>What was read</h4>" + (said or f"<p>All {n} documents, {given}: "
               + ", ".join(f"{v} {esc(label(k).lower())}" for k, v in gcounts.items()) + ".</p>"))
    # One block per step and one fold per step's result, each carrying the node the margin map names (report-map.js)
    said_chain = False
    for st in wf["steps"]:
        sid, kind = st["id"], st.get("kind", "")
        s = R["steps"].get(sid, {})
        body = []
        key = step_key(st, s)
        same = again(key, "The instruction, the codebook and the coded passages are the same as in" if kind == "code"
                     else "The table is the same as in") if key else None  # drawn in full already
        if kind == "code":
            unit = "one row for each document, read whole" if st.get("per_document") else "one row for each passage that fits"
            if s.get("combines"):  # nothing was coded here: the passages of other codings, put together
                held = s.get("rows_by_coding") or {}
                body.append(f'<h4>{esc(step_said(sid, kind))}</h4>'
                            f'<p class="small">The passages coded in {esc(" and ".join(s["combines"]))} put together, each keeping its own '
                            f'identity and the coding it came from: {len(s.get("rows", []))} rows ({esc(", ".join(f"{n} from {i}" for i, n in held.items()))}).</p>')
            else:
                body.append(f'<h4>{esc(step_said(sid, kind))}</h4>'
                            f'<p class="small">{esc(unit)}; {len(s.get("rows", []))} rows.</p>'
                            + ("" if same else f'<details><summary>The instruction a second coder would follow</summary><blockquote>{esc(st.get("prompt",""))}</blockquote></details>'))
            if isinstance(st.get("from"), dict):
                body.append(f'<p class="earlier">{esc(procedure.earlier_said(R, st))}</p>')
            if same:
                body.append(same)
            for col in ([] if same else st["columns"]):
                body.append(f'<h5>{esc(label(col["name"]))}</h5><p>{esc(col.get("means",""))}</p>'
                            + (f'<p class="small">Implicit: {esc(col["weak"])}</p>' if old and col.get("weak") else ""))  # legacy_weak
                if derived(col):  # filled from another column by a mapping, which a reader can check row by row
                    trs = "".join(f'<tr><td>{esc(str(k))}</td><td>{esc(str(v))}</td></tr>' for k, v in col["map"].items())
                    body.append(f'<p class="small">Not coded passage by passage: each passage takes the value its '
                                f'{esc(label(col["from"]))} gives, by this mapping. A passage whose value the mapping '
                                f'does not hold is left blank.</p><div class="scroll"><table class="codebook"><thead><tr>'
                                f'<th>{esc(label(col["from"]))}</th><th>{esc(label(col["name"]))}</th></tr></thead>'
                                f'<tbody>{trs}</tbody></table></div>')
                shared = again(column_key(col), "The codebook is the same as in") if column_key(col) else None
                if shared:
                    body.append(shared)
                elif codebook_of(col):  # coded against a group step's codebook, drawn with that step
                    body.append(f'<p class="small">Coded against the codebook of {step_link(codebook_of(col))}, whose items are its values.</p>')
                elif col.get("values"):
                    trs = "".join(f'<tr><th>{code_named(D, sid, col["name"], v["name"], static)}</th><td>{esc(v.get("means",""))}</td>'
                                  f'<td>{esc(v.get("counts",""))}</td><td>{esc(near_misses(v.get("does_not_count","")))}</td></tr>'
                                  for v in codes_of(col, R))
                    body.append(f'<div class="scroll"><table class="codebook"><thead><tr><th>Code</th><th>Means</th><th>Counts</th><th>Does not count</th></tr></thead><tbody>{trs}</tbody></table></div>')
            if same:
                pass
            elif combined and s.get("combines"):  # its rows are those of the steps it puts together, under the same identities
                body.append('<p class="small shared">Its passages are those of ' + " and ".join(step_link(c) for c in s["combines"])
                            + ", listed under those steps.</p>")
            elif s.get("rows") and not static:
                body.append(f'<div class="rb-block" data-node="asset:{esc(sid)}"><details><summary>The coded passages '
                            f'<span class="small">{len(s["rows"])} rows</span></summary>{passages_of(s)}</details>'
                            + (xlsx_button(step=sid) if st.get("links") and not s.get("combines") else "") + '</div>')
        elif kind == "tabulate":
            body.append(f'<h4>{esc(step_said(sid, kind))}</h4><p class="small">{esc(label(unit_of_table(s if s.get("count") else {"count": st.get("count", "cases"), "unit": st.get("unit")})))} by '
                        f'{esc(" and ".join(label(b).lower() for b in st.get("by", [])))}</p>')
            if s.get("description") or st.get("description"):
                body.append(f'<p class="table-said">{esc(s.get("description") or st.get("description"))}</p>')
            if (s.get("paths") or s.get("sequences") or s.get("loops")) and any("weak" in c for c in s.get("cells", [])) and not said_chain:
                said_chain = True  # legacy_weak: said once, where the first chain table counts implicit passages apart
                body.append(f'<p class="small chain-said">{CHAIN_EXPLICIT}</p>')
            if same:
                body.append(same)
            elif s.get("cells"):
                body.append(f'<div class="rb-block" data-node="asset:{esc(sid)}"><details><summary>The table '
                            f'<span class="small">{len(s["cells"])} cells</span></summary>{table_of(sid, s, D, R, static)}</details>'
                            + ("" if static or not link_ends(s, R) else xlsx_button(step=sid)) + '</div>')
        elif kind == "group" and s:
            body.append(grouped(sid, st, s, step_link))
        elif kind == "judge" and s:
            body.append(judged(sid, s, D, static))
        elif kind == "claims" and s:
            body.append(tagged(sid, s, D, static))
        elif kind == "write":
            body.append(f'<h4>{esc(step_said(sid, kind))}</h4><details><summary>The instruction the answer was written to</summary>'
                        f'<blockquote>{esc(st.get("instructions", ""))}</blockquote></details>')
        else:
            body.append(f'<h4>{esc(step_said(sid, kind))}</h4>')
        out.append(f'<section class="rb-block" id="{procedure.anchor(sid)}" data-node="step:{esc(sid)}">{"".join(body)}</section>')
        if combined:
            for shown in [key] + [column_key(c) for c in st.get("columns", [])]:
                if shown:
                    seen.setdefault(shown, (number, sid))
    rp = R["report"]
    if rp.get("earlier_runs"):
        lis = "".join(f'<li>{esc(e.get("question") or "")} Run <code>{esc(e.get("run_id") or "")}</code>, fingerprint '
                      f'<code>{esc(e["fingerprint"])}</code>, held in this run\'s zip as <code>{esc(e.get("zip") or "")}</code>; '
                      f'{"its definitions" if e.get("take") == "definitions" else "its coded passages"} for '
                      f'{esc(step_said(e["step"], "code").lower())}.</li>' for e in rp["earlier_runs"])
        out.append("<h4>Earlier runs this one builds on</h4><ul>" + lis + "</ul><p>Passages taken from an earlier run "
                   "were coded and checked in that run and are not checked again here. Where this answer agrees with an "
                   "earlier one on passages taken from it, the two do not corroborate each other, because one coding "
                   "lies under both.</p>")
    coded = rp.get("coding", {})
    nrows = sum(v.get("rows", 0) for v in coded.values())
    notfound = sum(len(v.get("quotations_not_found", [])) for v in coded.values())
    rough = sum(v.get("quotations_placed_approximately", 0) for v in coded.values())
    a = rp.get("answer", {})
    # the answer's own quotations, which a reader sees; a run recounted before 14 October 2026 did not count them
    said = a.get("quotations_in_the_answer")
    said_rough = len(a.get("quotations_placed_approximately", []))
    said_found = (said or 0) - len(a.get("quotations_found_in_no_document", []))
    if R.get("agreements") is not None:
        out.append("<h4>What the evaluator was asked to agree</h4>" + (agreed(R["agreements"], R, static) or
                   "<p>Nothing was put to the evaluator to agree before the answer was written.</p>"))
    if cited(R):
        out.append(gave(R))
    out.append("<h4>The checks that were run</h4><ul>"
               f"<li>{nrows - rough} of {nrows + notfound} coded passages found word for word in their document"
               + (f", {rough} more only approximately" if rough else "")
               + (f"; {notfound} found nowhere and left out of every count" if notfound else "") + ".</li>"
               + (f"<li>{said_found - said_rough} of {said} quotations in the answer found word for word in the documents"
                  + (f", {said_rough} more only approximately" if said_rough else "")
                  + " (a quotation of under twelve characters, such as one word, is not checked).</li>" if said is not None else "") +
               f"<li>{a.get('counts_written_by_id',0)} numbers in the answer, "
               + (counted_said(R, "each written by the AI beside the count the fixed rules made from the passages it cited, and equal to it")
                  if cited(R) else "every one computed directly from the coded passages rather than written by the AI")
               + f"; {len(a.get('numbers_written_bare',[]))} written by the AI without a count behind them.</li>"
               f"<li>{len(a.get('citations_to_no_row',[]))} citations to passages that do not exist; {len(set(a.get('quotations_not_in_what_they_cite',[])))} quotations not in the passage they cite.</li></ul>")
    if R.get("check"):
        # The check's two steps, as the margin map draws them after the workflow's own (`drawn_steps`)
        counts = next((b.strip() for b in R["check"].split("\n\n") if b.strip() and not b.lstrip().startswith("#")), "")
        lis = "".join(f"<li>{esc(label(sid.removeprefix('c_')))}: {len(rows)} rows</li>" for sid, rows in R["recoded"].items())
        alone = not procedure.second_coded(R)
        out.append("" if alone else f'<section class="rb-block" id="{procedure.anchor("second_coding")}" data-node="step:second_coding"><h4>Second coding</h4><p>'
                   + procedure.SECOND_SAID[procedure.separate(R, "second_coding")]
                   + ("" if R.get("recoded") else " The second coder's rows were not kept in this run's zip.") + "</p>"
                   + ("" if static or not R.get("recoded") else '<div class="rb-block" data-node="asset:second_coding">'
                      "<details><summary>The second coder's rows</summary>"
                      f'<ul>{lis}</ul><p class="small">In the run\'s zip, under <code>check/coded/</code>.</p></details></div>')
                   + "</section>")
        out.append(f'<section class="rb-block" id="{procedure.anchor("check")}" data-node="step:check"><h4>The check</h4><p>'
                   + (f"{procedure.CHECKER_ALONE[procedure.separate(R, 'check')]} read the answer against the passages it "
                      "cites and the documents" if alone else
                      f"{procedure.CHECKER[procedure.separate(R, 'check')]} ruled on every place the two codings differed")
                   + ", and checked every sentence and quotation of the answer against the "
                   "documents, correcting the coding and the answer where they were wrong. The answer above is the "
                   "corrected one, recounted after the check.</p>"
                   + (record_html(counts) if static and counts else "" if static else
                      '<div class="rb-block" data-node="asset:check"><details><summary>The check\'s record '
                      f'<span class="small">check.md</span></summary><div class="record">{record_html(R["check"])}</div></details></div>')
                   + "</section>")
    out.append("</div>")
    if R.get("fingerprint"):
        checked = again(hashed("record"), "How that fingerprint is made, and how to check the zip against it and the report against the zip, is told under The record in")
        out.append("<h3>The record</h3><p>"
                   + (f"This is run <code>{esc(R['run_id'])}</code>. Its ID stays the same through every revision, and the "
                      "zip's fingerprint, below, names this version of it. " if R.get("run_id") else "")
                   + f"This report was created directly from the run's zip, {esc(R['zip'])}"
                   + (f", with Rubicon {esc(R['version'])}" if R.get("version") else "") + ". The zip's fingerprint is "
                   f'<code class="fingerprint">{R["fingerprint"]}</code>.' + ("</p>" + checked if checked else f" {RECORD_CHECK}</p>"))
    revised = [l.strip()[2:] for l in R.get("revisions", "").splitlines() if l.strip().startswith("- ")]
    if revised:
        out.append(f'<h3 id="{procedure.anchor("revisions")}">Revisions</h3><p>'
                   "Changes made after the first report, each recounted and checked before this "
                   "version was created. Earlier versions keep their own files.</p><ul>"
                   + "".join(f"<li>{marked(esc(l))}</li>" for l in revised) + "</ul>")
    return "\n".join(out)


SITE = "rubicon.causalmap.app"


def site_link(text=None):
    """A link to the Rubicon site, opening in a new tab: the header's name for the report, and the foot's address."""
    return f'<a class="site" href="https://{SITE}" target="_blank" rel="noopener">{text or SITE}</a>'


def made_with():
    """The page's last line: what made the report, with the site's address spelled out as the link's own text."""
    return f'<p class="madewith">Made with Rubicon, free for Claude: {site_link()}</p>'


def carbon_line(F, combined=False, static=False):
    """The carbon the making of a report cost, at its foot: a headline that is only the range, in kilometres driven in
    an average UK car, and behind it, shut until opened, the watt-hours, how they were estimated and their sources.
    Word cannot fold, so `static` prints the headline and then the same details as plain paragraphs."""
    headline = f'<span class="flame">\U0001F525</span> {footprint.headline(F["low_km"], F["high_km"], combined)}'
    if static:
        return f'<p class="carbon"><b>{headline}</b></p>{carbon_details(F, combined)}'
    return f'<details class="carbon"><summary>{headline}</summary>{carbon_details(F, combined)}</details>'


def carbon_details(F, combined=False):
    """What stands behind the carbon headline: the electricity, how the range was estimated, and where each rate comes from."""
    K = footprint.K
    what = "combined report" if combined else "report"
    made = (f"It is the sum of the {F['parts']} answers' own estimates, each made from the size of its run: the "
            "documents read in full by each coding step, the tables the writer read, and everything the run wrote."
            if combined else
            f"The {F['documents']} documents were read in full once by each of the {F['code_steps']} coding steps"
            + (", by the second coder and by the check" if F["checked"] else "")
            + ", and the writer read the tables; everything the run wrote counts as output.")
    revised = (" " + footprint.covers(F["revisions"]).strip() + " The zip holds only the latest state, so each revision "
               "is counted at the low end as rereading the tables and writing the answer again, and at the high end as "
               "a whole run again." if F["revisions"] else "")
    return (f'<div class="carbon-more"><p>Making this {what} used between {F["low_wh"]:.1f} and {F["high_wh"]:.0f} '
            "watt-hours of electricity, which is the carbon of driving an average UK family car for that distance. A "
            "ballpark only: Anthropic publishes no energy figures, and the run, made in the evaluator's own Claude, "
            f"records no token counts, so the estimate is made from the run's size. {made} That comes to about "
            f"{F['read_tokens']:,} tokens read and {F['written_tokens']:,} written, at {K['chars_per_token']} "
            f"characters a token.{revised}</p><ul>"
            f"<li>High: {K['wh_per_1k_input_high']} Wh per thousand tokens read and {K['wh_per_1k_output_high']} per "
            f"thousand written, with what was read counted {K['overhead_high']} times over for the agent's own "
            f"overhead. {esc(K['high_source'])} {esc(K['overhead_source'])}</li>"
            f"<li>Low: the same rates divided by {K['low_divisor']}, what was read counted once. {esc(K['low_source'])}</li>"
            f"<li>{K['grid_kg_per_kwh']} kg CO2e per kWh. {esc(K['grid_source'])}</li>"
            f"<li>{K['car_kg_per_km']} kg CO2e per km. {esc(K['car_source'])}</li></ul></div>")


#: The heading of the first annex, which opens with the procedure in words (`procedure.told`) for a newcomer and goes
#: on to the record of each step (`annex`), headed STEP_BY_STEP
HOW_DONE = "How this report was written"
STEP_BY_STEP = "Step by step"


def how_done(R, static=False):
    """The procedure this run followed, in words, for a reader new to Rubicon: a short paragraph a stage, each step it
    tells linking to that step further down the same annex. Told from the same steps the workflow x-ray draws."""
    def piece(text, sid):
        return esc(text) if static or not sid else f'<a class="step" href="#{procedure.anchor(sid)}">{esc(text)}</a>'
    paras = "".join(f'<p><b>{esc(st["title"])}.</b> ' + "".join(piece(t, sid) for t, sid in st["parts"]) + "</p>"
                    for st in procedure.told(R, drawn_steps(R)))
    return paras + ("" if static else f'<p class="small">The workflow x-ray beside {STEP_BY_STEP}, below, draws the same '
                    "procedure, a box for each stage and what it made.</p>")


def further(R):
    """What comes after this draft: making sense of it with stakeholders, or, for a test on made-up documents,
    what the test's result calls for; the run's zip; and help from Causal Map."""
    test = bool(R["index"]) and n_synthetic(R) == len(R["index"])
    causal_map = ('<p>The Rubicon plugin for Claude is provided for free by Causal Map Ltd. Causal Map also runs '
                  'workshops and consultancy on analysing qualitative evidence for evaluation: '
                  '<a href="https://causalmap.app/contact/?utm_source=rubicon-plugin&amp;utm_medium=report">get in touch</a>, '
                  'or follow <a href="https://www.linkedin.com/company/causalmap/">Causal Map on LinkedIn</a>.'
                  ' Coming soon: continue your Rubicon work at the Rubicon website.</p>')
    if test:
        return ('<p>This report is one half of a test of the workflow on made-up documents, and what it says about them '
                'matters only as a result of that test. Compare its verdict, and the other test set\'s, with the verdicts '
                'the documents were written to reach. If both match, save the workflow as it stands, with its date, and '
                'run it unchanged on the real documents. If either does not, find whether a document, the plan the '
                'documents were written from or the workflow went wrong, and correct that before testing again.</p>'
                f'<p><b>{esc(R["zip"])}</b>, saved beside this report, holds the whole run: the documents, the coded '
                'passages and the workflow that recounts every number. Keep it with the test\'s plan as the record of '
                'what was tested.</p>' + causal_map)
    return ('<p><b>For the evaluator:</b> Treat this report as a draft. Before it is final, make sense of it with the '
            'people it concerns, such as programme staff and participants: whether the findings ring true, what they '
            'leave out, and what to do about them. You can then use the Rubicon plugin to work their responses back into a '
            'revised answer.</p>'
            f'<p><b>For evaluation commissioners:</b> Parallel to this report is a zip file ({esc(R["zip"])}), saved in '
            'the same folder, which contains the whole run: the documents, the coded passages and the workflow that '
            f'recounts every number. Its fingerprint, under {HOW_DONE}, ties it to this report: change a file in '
            'either and they no longer match. With it, anyone can check every number against the coded passages, and code the '
            'documents again to the same definitions without Rubicon or any other particular software. A fresh coding '
            'will not reproduce this report word for word, because AI models are unpredictable, but it should come '
            'close.</p>' + causal_map)


#: Characters of documents a report carries for reading them whole; above this a reader opens them from the run's zip
TEXTS_CARRIED = 5_000_000


def packed_texts(R):
    """The documents, for reading one whole with every passage this run coded in it marked (report.js): gzipped JSON
    in base64, which the reader's browser unpacks only when a document is opened, or "" for a corpus too large
    to carry, whose documents the reader opens from the run's zip instead. Compressed by the same zlib that makes the
    zip, so the report is as deterministic as its zip."""
    return pack_texts(R["texts"])


def pack_texts(by_id):
    """Documents (id to text) as `packed_texts` carries them; a combined report packs once the documents of several runs."""
    if sum(map(len, by_id.values())) > TEXTS_CARRIED:
        return ""
    return base64.b64encode(gzip.compress(json.dumps(by_id, ensure_ascii=False).encode("utf-8"), mtime=0)).decode("ascii")


def texts(R):
    return f' const TEXTS = "{packed_texts(R)}";'


def plain_script(name):
    """One of the engine's ES modules as plain script, its imports and exports dropped, for inlining in a report."""
    return re.sub(r"^import .*$", "", (ENGINE / "rubicon_open" / name).read_text(encoding="utf-8"),
                  flags=re.M).replace("\nexport ", "\n")


def report_js():
    """The report's script: report.js, after the workbook writer for Causal Map and the link rule it uses, kept in a
    scope of their own so a binder of several runs carries them once."""
    return ("var CausalMapXlsx = (() => {\n" + plain_script("link-rows.js") + plain_script("causal-map-xlsx.js")
            + "\nreturn { causalMapWorkbook, linksOfRows };\n})();\n"
            # a map's arrows carry their cell's id encoded for the drawing (map-dot.js), which a click decodes to find the cell
            + "var MapIds = (() => {\n" + plain_script("map-dot.js") + "\nreturn { cellOfEdgeDomId };\n})();\n"
            + (ENGINE / "report.js").read_text(encoding="utf-8"))


def margin_map(R):
    """The margin map's script: the Rubicon page's own words.js, minimap.js and minimap-mount.js (copies kept
    identical to the page's) made one plain script, the map's elements, and report-map.js, which mounts the map beside the annex."""
    plain = plain_script
    elements = json.dumps(map_elements(R), ensure_ascii=False).replace("</", "<\\/")
    return ("(() => {\n" + plain("words.js") + plain("minimap.js") + plain("minimap-mount.js")
            + f"\nconst ELEMENTS = {elements};\n" + (ENGINE / "report-map.js").read_text(encoding="utf-8") + "\n})();")


def sentences(md):
    """The answer's sentences, headings left out: what the check read one by one."""
    text = " ".join(l.strip().removeprefix("- ") for l in md.splitlines() if l.strip() and not l.lstrip().startswith(("#", "|", "{{")))
    return [t for t in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(*])", text) if t.strip()]


def counted_said(R, every_beside):
    """How the answer's counts came from the passages the AI cited: `every_beside` where the AI wrote a number beside
    each (`procedure.stated_beside`), else code's count put where the AI referred to it."""
    beside = procedure.stated_beside(R)
    if beside is None:
        return every_beside
    return ("each counted by fixed rules from the passages the AI cited and put where the AI referred to it"
            + (f", {beside} of them also written by the AI beside it and equal to it" if beside else ""))


def summary(R, a, nrows):
    """The box under the short answer: what code checked in this report, and, for a checked run, how many of the
    answer's sentences a second AI reader read against the documents; then what nothing checked."""
    counted = (f"<li><b>{a['counts_written_by_id']}</b> numbers, "
               + (counted_said(R, "each written by the AI and shown beside the count the fixed rules made from the passages it cited, which it must equal") + "."
                  if cited(R) else "every one computed directly from the coded passages rather than written by the AI.")
               + '<span class="click"> Click any number to see who it counts.</span></li>') if a.get("counts_written_by_id") else (
        "<li>No counts: the answer states no number computed from the coded passages, so its findings rest on the "
        "passages cited and quoted beside them.</li>")
    out = [f'<li class="head"><span class="vb-t">{BOX_TITLE}<small>{VERIFIED_WHEN}</small></span></li>', counted,
           f"<li><b>{nrows}</b> quotations, every one found word for word in its interview."
           '<span class="click"> Click an interview\'s ID beside a quotation to read it in place.</span></li>']
    if a.get("claims_cited"):
        out.append(f"<li><b>{a['claims_cited']}</b> key claims tagged as numbers are, each with the passages for it and "
                   'against it and why they bear it out.<span class="click"> Click a claim\'s tag to see them.</span></li>')
    if a.get("numbers_written_bare_at"):
        out.append(f'<li class="unchecked-said">Other numbers in the text, <span class="unchecked">in grey</span>, are the '
                   "writer's own, such as a year or a number quoted from a source, and were not counted by fixed rules.</li>")
    if R.get("check"):
        # the check's record gives how many sentences it corrected only in prose of its own wording, so none is said here
        out.append(f"<li><b>{len(sentences(R['answer']))}</b> sentences of the answer were read against the interviews "
                   + (CHECKED_BY[procedure.separate(R, "check")] if not procedure.second_coded(R)
                      else "by an AI reader, after " + BLIND_SAID[procedure.separate(R, "second_coding")]) + ".</li>")
    out.append(f'<li class="not-checked">{NOT_CHECKED}</li>')
    return "".join(out)


#: The verification box's title, the line under it, and its last line, on what nothing checked
BOX_TITLE = "What was automatically checked in this report"
NOT_CHECKED = ("<b>Not checked:</b> whether the passages cited are all the documents hold on each point, "
               "or whether each is labelled correctly.")
VERIFIED_WHEN = "Checked when this report was created"


def word_badge(R, nrows):
    """The verification box for Word, which keeps no class styling: a one-cell table with a red rule, a tick before each
    check and a dash before the line on what was not checked."""
    items = re.findall(r"<li(?: class=\"(?:unchecked-said|not-checked)\")?>(.*?)</li>", summary(R, R["report"].get("answer", {}), nrows))
    items = [re.sub(r'<span class="click">.*?</span>|<span class="unchecked">(.*?)</span>', r"\1", i) for i in items]
    mark = lambda i: ('<span style="color:#7d7166;font-weight:bold">&#8211;</span>' if i.startswith("<b>Not checked:") else
                      '<span style="color:#8c1912;font-weight:bold">&#10003;</span>')
    lines = "".join(f'<p style="margin:3pt 0 3pt 14pt;text-indent:-14pt;font-family:Calibri,Arial,sans-serif;font-size:10pt">'
                    f'{mark(i)}&nbsp;&nbsp;{i}</p>' for i in items)
    return ('<table style="border-collapse:collapse;margin:8pt 0 12pt;width:100%"><tr><td style="border:1px solid #d9b9b2;'
            'border-left:4pt solid #8c1912;background:#fdfbf6;padding:6pt 10pt">'
            '<p style="margin:0;font-family:Cambria,Georgia,serif;font-size:13pt;color:#8c1912">'
            f'{BOX_TITLE}</p>'
            f'<p style="margin:0 0 4pt;font-family:Calibri,Arial,sans-serif;font-size:8.5pt;color:#7d7166">{VERIFIED_WHEN}</p>'
            f'{lines}</td></tr></table>')


#: The verification box's account of the second coding, as the record of who did it allows
BLIND_SAID = {True: "a second AI coder coded the interviews blind",
              False: "the same AI coded the interviews a second time, which is not independent",
              None: "an AI coded the interviews a second time"}
#: The verification box's account of a check that was the whole second reading
CHECKED_BY = {True: "by a second AI reader, separate from the one that wrote them",
              False: "again by the AI that wrote them, which is not independent",
              None: "by a second AI reader; the run does not record whether it was independent"}


def nrows_of(R):
    """How many passages the run coded, each counted once: the quotations the verification box speaks for."""
    return sum(len(s.get("rows", [])) for s in R["steps"].values() if s.get("kind") == "code" and not s.get("combines"))


def facts(R, D):
    """The line under the short answer saying what the run read, and the box of what in it can be checked."""
    nrows = nrows_of(R)
    groups = {d.get(D["group"], "") for d in R["index"]}
    run = f" · Run {esc(R['run_id'])}" if R.get("run_id") else ""
    return (f'<p class="meta">{len(R["index"])} interviews in {len(groups)} groups · {nrows} passages coded · '
            f'{esc(R.get("date", ""))}{run}</p>\n  '
            f'<ul class="checks">{summary(R, R["report"].get("answer", {}), nrows)}</ul>')


def annexes(inner):
    """Everything after the answer, under one heading and on a darker ground, in a report and in a binder alike."""
    return f'<section class="annexes" id="annexes">\n  <h2 class="annexes-title">{ANNEXES}</h2>\n{inner}\n</section>'


#: A section the report draws with an id, and its first heading, which is what the contents list for it
SECTION = re.compile(r'<(?:section|aside)\s[^>]*\bid="([^"]+)"[^>]*>\s*(?:<p\b[^>]*>.*?</p>\s*)?<h2\b[^>]*>(.*?)</h2>', re.S)


def contents(main, annexed):
    """The floating contents (report.css hides it on narrow screens): the main sections, given as (id, heading), then
    the annexes, read off their own markup so the list is never a second copy of their headings."""
    li = lambda i, t: f'<li><a href="#{esc(i)}">{esc(t)}</a></li>'
    annex = [(i, html.unescape(re.sub(r"<[^>]+>", "", t)).strip()) for i, t in SECTION.findall(annexed) if i != "annexes"]
    return ('<nav class="toc" aria-label="Contents"><div><ol>' + "".join(li(i, t) for i, t in main) + "</ol>"
            f'<p class="toc-part"><a href="#annexes">{ANNEXES}</a></p><ol>' + "".join(li(i, t) for i, t in annex)
            + "</ol></div></nav>")


def page(R, fragment=False):
    D = build_data(R)
    title, lead, body, cite_no = answer_html(R, D)
    data = json.dumps(D, ensure_ascii=False).replace("</", "<\\/")
    css = (Path(__file__).parent / "report.css").read_text(encoding="utf-8")
    js = report_js()
    map_js = margin_map(R)
    annexed = annexes(f"""<section class="annex" id="how-done">
  <h2>{HOW_DONE}</h2>
  {how_done(R)}
  {annex(R, D)}
</section>
<section class="evidence" id="evidence">
  <h2>Every interview at a glance</h2>
  <p class="small">Each row is one interview, each column a reason as the coding defines it. Click a mark to read the passages.</p>
  {matrix(R, D)}
</section>
<aside class="next" id="next">
  <h2>What next</h2>
  {further(R)}
</aside>""")
    content = f"""<title>{esc(heading(R, title))}</title>
<style>{assets.fonts_css()}{css}</style>
<div class="wrap">
{contents([("top", "Short answer")] + R["toc"], annexed)}
<main>
<header class="cover" id="top">
  <p class="eyebrow">{site_link("Rubicon report")}</p>
  <h1>{esc(heading(R, title))}</h1>
  {asked(R)}
  {synthetic(R)}
  <div class="lead">{lead}</div>
  {facts(R, D)}
</header>
<article class="answer rb-block" data-node="asset:answer">{body}</article>
{annexed}
{carbon_line(R["footprint"])}
{made_with()}
</main>
<aside class="panel" id="panel" hidden><button class="close" id="panel-close" aria-label="Close">×</button><div id="panel-body"></div></aside>
</div>
<script>const RUN = {data};{texts(R)}</script>
{assets.graphviz_script() if '<pre class="dot"' in body + map_js else ""}<script>{js}</script>
<script>{map_js}</script>
"""
    if fragment:
        return content
    head, body = content.split('<div class="wrap">', 1)
    return f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{head}</head><body><div class="wrap">{body}</body></html>'


def word(R):
    """The same report for Word: figures as text, citations as their documents and opening words, with the passages
    cited in full at the end."""
    D = build_data(R)
    title, lead, body, cite_no = answer_html(R, D, static=True)
    notes = "".join(f'<p class="note">{esc(D["rows"].get(rid, {}).get("doc",""))}: "{esc(D["rows"].get(rid, {}).get("ctx", ["","",""])[1])}"</p>'
                    for rid, k in sorted(cite_no.items(), key=lambda x: x[1]))
    return ('<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" '
            'xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8">'
            f'<title>{esc(heading(R, title))}</title><!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->'
            '<style>body,p,li,td{font-family:Cambria,Georgia,serif;font-size:11pt;line-height:1.35;color:#17130f}'
            'h1,h2,h3{font-family:Cambria,Georgia,serif;font-weight:normal;color:#8c1912}h1{font-size:20pt}h2{font-size:14pt}'
            'p.note{font-size:9pt}td,th{border:1px solid #e4dcd0;padding:3pt 5pt;font-size:9pt;vertical-align:top}table{border-collapse:collapse}'
            '.pb{page-break-before:always}</style></head><body>'
            f'<p style="color:#8b7f72;font-size:9pt">RUBICON REPORT</p><h1>{esc(heading(R, title))}</h1>'
            + (f'<p style="color:#8b7f72;font-size:9pt">Run {esc(R["run_id"])}</p>' if R.get("run_id") else "") +
            f'{asked(R, static=True)}{synthetic(R)}{lead}{word_badge(R, nrows_of(R))}{body}<h1 class="pb">{ANNEXES}</h1><h2>{HOW_DONE}</h2>{how_done(R, static=True)}{annex(R, D, static=True)}<h2>Passages cited</h2>{notes}'
            f'<h2>What next</h2>{further(R)}{carbon_line(R["footprint"], static=True)}{made_with()}</body></html>')


if __name__ == "__main__":
    console.utf8()
    run = Path(sys.argv[1])
    frag = "--fragment" in sys.argv
    if run.suffix.lower() == ".zip":  # a run's zip lays out its run beside it, named after it, and draws as it was drawn
        folder = run.with_suffix("")
        given = unpack(run, folder)
        zipped = folder / f"{given['name']}.zip.part"
        shutil.copy2(run, zipped)
    else:
        folder = run
        workflow = json.loads((folder / "workflow.json").read_text(encoding="utf-8"))
        revisions = (folder / "revisions.md").read_text(encoding="utf-8") if (folder / "revisions.md").is_file() else ""
        date = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else ""
        name = name_of(workflow, revisions, date, titled_as(folder, workflow))
        runs = folder.resolve().parent / "rubicon-runs.md"
        if not frag and runs.is_file() and re.search(rf"{re.escape(name)}-[0-9a-f]{{8}}\.html", runs.read_text(encoding="utf-8")):
            sys.exit(f"{name}-….html is already listed in {runs.name} as handed over, so it is not overwritten. A revision "
                     "adds its line to revisions.md first, and the report is then written under a new -revision- name.")
        render = {"name": name, "date": date,
                  "engine": engine_fingerprint(ENGINE), "version": engine_version(ENGINE)}
        zipped = folder / f"{name}.zip.part"  # named once its fingerprint is known
        bundle(folder, zipped, render)
    refused = problems(zipped)
    if refused:
        zipped.unlink()
        sys.exit("No report is created: " + "; ".join(refused) + ".")
    # From here on the report reads the zip and nothing else
    R = load(zipped)
    if R["engine"] != engine_fingerprint(ENGINE):
        print(f"This engine is not the one that made the zip (Rubicon {R['version'] or 'of unknown version'}), so the "
              "report created here may differ from the one created when the zip was made.")
    out_dir = folder
    if run.suffix.lower() == ".zip":
        # the report is written beside the zip it was drawn from; where that would overwrite the report already there
        # (the same zip draws under the same name), it is written into the folder the run was laid out in, and said
        out_dir = run.resolve().parent
        held = [n for n in (f"{R['name']}{'.fragment' if frag else ''}.html", f"{R['name']}.doc") if (out_dir / n).exists()]
        if held:
            out_dir = folder.resolve()
            print(f"{' and '.join(held)} already beside {run.name}, so left as they are; the report is written into {out_dir} instead.")
        if not (out_dir / R["zip"]).exists():  # the zip it was drawn from stays where it is; a copy goes only where the report's name finds none
            shutil.copy2(zipped, out_dir / R["zip"])
    else:
        zipped = zipped.replace(out_dir / R["zip"])
    out = out_dir / f"{R['name']}{'.fragment' if frag else ''}.html"
    drawn, doc = page(R, frag), word(R)
    if R["unfilled"]:
        sys.exit("No report is created: the answer writes " + ", ".join("{" + u + "}" for u in R["unfilled"])
                 + ", which no count in the run is called, so a reader would see the braces. Write a count's id as the "
                 "answer's tables give it, or the number in words.")
    out.write_text(drawn, encoding="utf-8", newline="\n")
    (out_dir / f"{R['name']}.doc").write_text(doc, encoding="utf-8", newline="\n")
    print(f"wrote {out.name}, {R['name']}.doc and {R['zip']} in {out_dir}")
    if R.get("missing_sections"):
        print("[§ ] references naming no section of the answer: " + ", ".join(sorted(set(R["missing_sections"]))))
    if R.get("missing_figures"):
        print("figure lines naming no table, left out: " + ", ".join(sorted(set(R["missing_figures"]))))
    if R.get("loops_left_out"):
        print(f"loop figures draw at most {MOST_LOOPS} loops, the ones the answer cites or else the first; left out: "
              + ", ".join(sorted(set(R["loops_left_out"]))) + "; cite fewer loops, or narrow the table with through")
    if R.get("wide_figures"):
        print("figure lines naming a table of more than two columns, which no chart shows, left out: "
              + ", ".join(sorted(set(R["wide_figures"]))) + "; write that comparison as a table of its cell ids instead")
