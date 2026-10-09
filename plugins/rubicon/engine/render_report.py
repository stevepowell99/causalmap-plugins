"""Draw a Rubicon run folder as a report to read and click through, the same report for Word, and the run as a zip.

    python render_report.py <run folder> [--date "6 October 2026"] [--fragment] [--page <url of rubicon.html>]
    python render_report.py <run .zip>   [the same options]

The three files share one name, made from the question, the day and the first eight characters of the run's
fingerprint: `<question>-<yyyy-mm-dd>-<fingerprint>.html`, `.doc` and `.zip`, with `-revision-<n>` before the
fingerprint once the run has been revised (`revisions.md`), so a report and its zip are seen to match by their names. The zip is the recounted run in the open format (`recount/`: `workflow.json`, `run.json`, `steps/*.json`,
`corpus/` and `background/`), which the Rubicon page's "Open a downloaded run (.zip)" reads in the browser and
never saves. It holds the documents, because the page needs them to show each quotation in its place, and
`answer.md`, `counts.json` and `report.json`, so that given the zip in place of a folder this draws the report again
from the zip alone, into a folder beside it named after it (`unpack`), under the name and date it was first drawn with.

The report is drawn from the zip and from nothing else: given a folder, this makes the zip first, then reads only the
zip (`load`), so a report cannot say anything its zip does not hold. The zip is sealed: `SHA256SUMS` lists the SHA-256
of every other file in it, and the SHA-256 of that list is the run's fingerprint, printed in the report. `render.json`
in the zip gives the name, date and page the report is drawn under and the engine that drew it, and its files carry a
fixed date, so the same run always makes the same zip and the same zip the same report, byte for byte. Nothing is drawn
from a zip whose seal is broken, or whose recount a fresh recount of its own coded rows and answer would change
(`problems`). `verify.py` says whether a given report was drawn from a given zip.

Reads only what the run already holds (answer.md with its cell ids, recount/steps/*.json, recount/report.json,
corpus/index.csv and the corpus text for context around each quotation). Makes no model call, so it costs nothing
and draws the same report every time. Standard library and Node only.

In answer.md, a line holding only {{figure <table id>}} draws that table as a chart at that point. A table by the two
ends of a code step's causal links draws as a causal map: the report carries its DOT (rubicon_open/draw_map.mjs) and
Graphviz draws it in the reader's browser, loaded at a fixed version from jsDelivr and checked against its hash (`GRAPHVIZ`).
--fragment writes the page without <html>/<head>/<body>, for publishing as an Artifact.

The report carries its zip, and its "Open in Causal Map" button hands the run to the Rubicon page in the reader's own
browser (`webapp/rubicon/js/receive.js` says how), so nobody downloads or uploads anything. --page points the button
at another copy of the page, such as a local one for testing.
"""
import base64, csv, datetime, gzip, hashlib, html, io, json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import locator, node
from rubicon_open.corpus import INDEX_FIELDS, as_read
from rubicon_open.run_id import clean as run_id_of
from rubicon_open.seal import engine_fingerprint, engine_version, listed, seal_broken
from rubicon_open.steps import ROW_ID, base_of, cited_as, group_ids, stated
from rubicon_open.workflow import arrow_parts, loop_markers, sign_of, value_key

ENGINE = Path(__file__).resolve().parent
DRAW_MAP = ENGINE / "rubicon_open" / "draw_map.mjs"
#: Every file in a zip carries this date, so the same run always makes the same zip, byte for byte
STAMP = (1980, 1, 1, 0, 0, 0)
PAGE = "https://app.causalmap.app/rubicon.html"
#: Whether a report offers to open its run on the Rubicon page (PAGE). Off until the live site, which serves `main`,
#: has the page that receives a run; `--page <url>` turns it on for one report, such as against the dev site.
#: `rubicon/plugin/build.py` reads this line, and leaves the skill's hand-over bullet out while it is off.
HANDOFF = False
CONTEXT = 420  # characters of the document shown either side of a quotation


def name_of(workflow, revisions):
    """The name the run's files share: the agreed question, cut to its first words, and today's date, then the revision
    number where the run has been revised, so a revised report never overwrites the one before it."""
    words, slug = re.findall(r"[a-z0-9]+", re.sub(r"['\u2019]", "", workflow.get("question_as_agreed", "").lower())), ""
    for w in words:
        if len(slug) + len(w) > 50:
            break
        slug = f"{slug}-{w}" if slug else w
    revised = sum(1 for l in revisions.splitlines() if l.strip().startswith("- "))
    return f"{slug or 'rubicon'}-{datetime.date.today().isoformat()}" + (f"-revision-{revised}" if revised else "")


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
        for sub in ("corpus", "background", "coded"):
            if (run / sub).is_dir():
                shutil.copytree(run / sub, fresh / sub)
        done = subprocess.run([sys.executable, "-I", "-S", str(ENGINE / "recount.py"), str(fresh), "--answer",
                               str(fresh / "answer.md")], capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            return ["the recount itself, which failed: " + done.stderr.strip()[-400:]]
        old, new = recorded(run / "recount"), recorded(fresh / "recount")
        return sorted(n for n in old.keys() | new.keys() if n not in old or n not in new or not same(n, old[n], new[n]))


def same(name, a, b):
    """Whether two copies of a recount file are the same. `run.json` is compared without its `chat`, which names the
    chat that first recounted the run and so is never what a fresh recount, run in whatever chat verifies it, would write."""
    if name == "run.json":
        try:
            drop = lambda p: {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k != "chat"}
            return drop(a) == drop(b)
        except (OSError, ValueError, AttributeError):
            pass
    return a.read_bytes() == b.read_bytes()


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
    files.update({n: p for n, p in recorded(rec).items() if n.startswith(("steps/", "corpus/", "background/"))})
    # The analyst's audit trail: the scripts, their output, the table of what each document holds, and the procedure
    for p in sorted((run / "work").rglob("*")) if (run / "work").is_dir() else []:
        if p.is_file() and "__pycache__" not in p.parts:
            files["work/" + p.relative_to(run / "work").as_posix()] = p
    # The second reading: the check's record and the second coder's own rows, beside the run they checked
    for p in [run / "check.md"] + [run / "recode" / f for f in ("disagreements.md", "unclear.md")] \
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
        sys.exit(f"{run} already exists; move it, or draw the report from that folder instead")
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
        if broken:
            sys.exit(f"{zipped.name} is not as it was made, so no report is drawn from it: " + "; ".join(broken))
        for n in z.namelist():
            if n.endswith("/"):
                continue
            to = (run / n if n in ("answer.md", "revisions.md", "render.json", "SHA256SUMS") or n.startswith(("coded/", "work/"))
                  else run / n.removeprefix("check/") if n == "check/check.md"
                  else run / "recode" / n.removeprefix("check/") if n.startswith("check/") else run / "recount" / n)
            to.parent.mkdir(parents=True, exist_ok=True)
            to.write_bytes(z.read(n))
    shutil.copy2(run / "recount" / "workflow.json", run / "workflow.json")
    for sub in ("corpus", "background"):
        if (run / "recount" / sub).is_dir():
            shutil.copytree(run / "recount" / sub, run / sub)
    return json.loads((run / "render.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s), quote=True)


def label(v):
    """A value as a reader sees it: underscores as spaces and the first letter capitalised, the rest left as coded, so
    an acronym such as AI keeps its capitals."""
    s = str(v).replace("_", " ").strip()
    return s[:1].upper() + s[1:]


def load(zipped):
    """Everything a report draws, read from the run's sealed zip and from nothing else, so a report can say nothing its
    zip does not hold: the counts, rows and checks of the recount, the answer as written, the documents, the second
    reading, the revisions, and from `render.json` the name, date and page it is drawn under."""
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
            "recoded": {n[len("check/coded/"):-len(".json")]: json.loads(text(n)) for n in sorted(names)
                        if re.fullmatch(r"check/coded/[^/]+\.json", n)},
            "revisions": text("revisions.md"),
            # The files' own name carries the fingerprint's first characters, so a report and its zip are seen to match
            "name": f"{render['name']}-{fingerprint[:8]}", "zip": f"{render['name']}-{fingerprint[:8]}.zip",
            "date": render["date"], "page": render.get("page"),
            "folder": render.get("folder", ""), "version": render.get("version"), "engine": render.get("engine"),
            "fingerprint": fingerprint,
            # The run the report hands to the page: the zip re-made from its own contents in its own order, so how the
            # zip was packed, by this engine or by any other tool, never changes the report
            "zip_b64": base64.b64encode(sealed([(n, z.read(n)) for n in listed(z)])).decode("ascii")
                       if render.get("page") else "",
        }


def problems(zipped):
    """Why no report may be drawn from this zip: its seal is broken, or its recount is not what a fresh recount of its
    own coded rows and answer gives. Empty means the zip is as it was made and every number in it follows from its
    coded passages."""
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
    if broken:
        return [f"{zipped.name} is not as it was made: " + "; ".join(broken)]
    with tempfile.TemporaryDirectory() as t:
        run = Path(t) / "run"
        unpack(zipped, run)
        differs = recount_differs(run)
    return ([f"its recount does not follow from its coded rows and its answer: {', '.join(differs)} would change. "
             "Recount with recount.py <folder> --answer answer.md, then draw again"] if differs else [])


def group_column(index):
    cols = [c for c in index[0].keys() if c not in INDEX_FIELDS] if index else []
    return cols[0] if cols else None


def second_reading(step, recoded, texts, rows):
    """What the second coder, coding blind, made of each of this step's passages: whether any passage of theirs
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


def build_data(R):
    """Everything the page's script needs: rows with context, cells, documents."""
    gcol = group_column(R["index"])
    docs = {d["id"]: {"group": d.get(gcol, ""), "title": d.get("title", d["id"]),
                      "file": "corpus/" + (d.get("file") or f"{d['id']}.txt")} for d in R["index"]}
    rows, cells, defs = {}, {}, {}
    for sid, s in sorted(R["steps"].items(), key=lambda kv: kv[1].get("kind") != "code"):  # rows before the cells that read them
        if s.get("kind") == "code":
            for col in s.get("columns", []):
                for v in col.get("values", []) or []:
                    defs[f"{col['name']}={v['name']}"] = v.get("means", "")
            for r in s.get("rows", []):
                t = R["texts"].get(r["document"], "")
                a, b = r.get("start"), r.get("end")
                if a is not None and t:
                    lo, hi = max(0, a - CONTEXT), min(len(t), b + CONTEXT)
                    ctx = [("…" if lo else "") + t[lo:a], t[a:b], t[b:hi] + ("…" if hi < len(t) else "")]
                else:
                    ctx = ["", r["quote"], ""]
                codes = {c["name"]: r.get(c["name"]) for c in s.get("columns", [])}
                rows[r["row"]] = {"doc": r["document"], "step": sid, "ctx": ctx, "codes": codes,
                                  **({"weak": True} if r.get("weak") else {})}
                if a is not None and t:
                    rows[r["row"]]["at"] = [a, b]
            if sid in R.get("recoded", {}):
                second_reading(s, R["recoded"][sid], R["texts"], rows)
        elif s.get("kind") == "tabulate":
            weak = {x: r["doc"] for x, r in rows.items() if r.get("weak")}
            for c in s.get("cells", []):
                # the documents a cell holds only through weak rows, which its count leaves out (steps.tabulate)
                firm = {rows[x]["doc"] for x in c.get("rows", []) if x in rows and x not in weak}
                cells[c["id"]] = {"values": c["values"], "n": c["n"], "base": base_of(s, c), "said": stated(s, c),
                                  "within": c.get("within") or {}, "docs": c.get("documents", []),
                                  "weak_docs": sorted({weak[x] for x in c.get("rows", []) if x in weak} - firm),
                                  "rows": c.get("rows", []), "step": sid}
            # {<step>.of}, the documents the tabulation read, as the engine takes them from its input step
            src = R["steps"].get(s.get("input"), {})
            read = src.get("documents") or R["steps"].get(src.get("input"), {}).get("documents") or sorted(docs)
            cells[f"{sid}.of"] = {"values": {}, "n": s.get("of"), "base": s.get("of"), "said": f'{s.get("of")} of {s.get("of")}', "within": {},
                                  "docs": sorted(read), "rows": [], "step": sid}
    return {"docs": docs, "rows": rows, "cells": cells, "defs": defs, "group": gcol, "zip": R.get("zip", "")}


# ---------- the answer: markdown with cell ids and row citations ----------

#: [<row id>, <row id>; ...]: a group of row ids as the engine reads one (`steps.group_ids`); a bracket holding anything
#: else is left as written
CITE = re.compile(r"\[([^\[\]]+)\]")
#: {<id>}: any count the engine made (steps.counts_of is the one list of them); one it did not make is left as written,
#: and a report still holding one is not drawn
CELL = re.compile(r"\{([a-z][\w]*(?:\.[\w]+)+)\}")


def cell_of(cid):
    """The table cell a count is read from, for the page to open its passages: none for a judge's count."""
    base = re.sub(r"\.(?:within\.[\w]+|weak)$", "", cid)
    return base if re.fullmatch(r"[a-z][\w]*\.(?:c\d+|of)", base) else None
FIG = re.compile(r"^\{\{figure\s+([\w]+)\}\}$")
#: [§ A heading]: a claim that builds on a finding stated in that section of the answer, which is how a revision follows
#: what rests on what (stale.py)
SEE = re.compile(r"\[§\s*([^\]]+)\]")


def anchor(heading):
    return "s-" + "-".join(re.findall(r"[a-z0-9]+", heading.lower()))


#: a count as steps.stated writes it: "n of base", or "n passages" where it counts passages and has no base
SAID = re.compile(r"(\d+) (?:of (\d+)|passages?)")


def heat(pairs):
    """How a table shows its counts, from each count's (n, base), base None for a count of passages: a shade for each
    count, and the line said once beneath where every count shares one base (plain numbers, shaded by share) or none
    has one (plain numbers, shaded against the largest); the line is None where the bases differ, and each count then
    says its own."""
    top = max([n for n, b in pairs if b is None] + [1])
    bases = {b for _, b in pairs}
    note = None
    if len(pairs) > 1 and len(bases) == 1:
        b = bases.pop()
        note = f"Each number is out of {b}." if b else "Each number counts coded passages, not documents."
    return (lambda n, b: n / (b or top)), note


def inline(text, R, D, cite_no, static, plain=False):
    out = esc(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)

    def cell(m):
        cid = m.group(1)
        if cid not in R["counts"]:
            return m.group(0)
        txt = R["counts"][cid]
        if plain:
            txt = SAID.fullmatch(txt).group(1)
        base = cell_of(cid)
        if R.get("finding") is not None:
            # a count with no cell behind it, such as a judgement's, still names the step that made it
            R["finding"].setdefault("cells" if base else "steps", []).append(base or cid.split(".")[0])
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
            return "(" + "; ".join(said(i) for i in ids) + ")"
        chips = [f'<button class="cite" data-row="{esc(rs[0])}"' if len(rs) == 1 else
                 f'<button class="cite" data-rows="{esc(",".join(rs))}"' for rs in by_doc.values()]
        return "(" + ", ".join(f'{c} title="{esc(quoted(d, rs, D))}">{esc(d)}</button>'
                                for c, (d, rs) in zip(chips, by_doc.items())) + ")"

    def see(m):
        h = html.unescape(m.group(1)).strip()
        if h not in R.get("sections", ()):
            R.setdefault("missing_sections", []).append(h)
        shown = R.get("renamed", {}).get(h, h)
        return f"(see “{esc(shown)}”)" if static else f'<a class="see" href="#{anchor(h)}">§ {esc(shown)}</a>'

    out = CELL.sub(cell, out)
    while (merged := ADJACENT.sub(joined, out)) != out:
        out = merged
    out = CITE.sub(cite, out)
    out = SEE.sub(see, out)
    return out if static else linked_sources(out, D)


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
        return causal_map(s, s["cells"], by)
    if len(by) > 2:  # a chart shows two columns at most; drawing the first two would drop the rest and mislead
        R.setdefault("wide_figures", []).append(tid)
        return ""
    cells = [c for c in s["cells"]]
    if len(by) == 1:
        rows = sorted(cells, key=lambda c: -c["n"])
        mx = max([base_of(s, c) or c["n"] for c in rows] + [1])
        bars = "".join(
            f'<div class="bar-row"><span class="bar-label">{esc(label(c["values"][by[0]]))}</span>'
            f'<span class="bar-track"><button class="bar" data-cell="{esc(c["id"])}" style="width:{100*c["n"]/mx:.1f}%"></button></span>'
            f'<span class="bar-n">{c["n"]}</span></div>' for c in rows)
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
                pair += f'<span class="bar-track thin">{btn}</span><span class="bar-n">{n}</span>'
            out.append(f'<div class="bar-row pair"><span class="bar-label">{esc(label(v))}</span><span class="pair-bars">{pair}</span></div>')
        legend = (f'<span class="key yes"></span>{esc(yes_l)} <span class="key no"></span>Raised, not tied to that')
        return (f'<figure class="fig"><div class="legend">{legend}</div><div class="bars">{"".join(out)}</div>'
                f'<figcaption>{caption(s)} Click a bar for the passages behind it.</figcaption></figure>')
    # two nominal columns: a grid of counts within each column of b
    avals.sort(key=lambda v: -sum(look.get((v, x), {"n": 0})["n"] for x in bvals))
    head = "".join(f"<th>{esc(label(x))}</th>" for x in bvals)
    body = ""
    shade, note = heat([(c["n"], base_of(s, c)) for c in cells if c["n"]])
    for v in avals:
        tds = ""
        for x in bvals:
            c = look.get((v, x))
            if c and c["n"]:
                n, base = c["n"], base_of(s, c)
                tds += (f'<td><button class="cellbtn" data-cell="{esc(c["id"])}" style="--a:{shade(n, base):.2f}">{n}'
                        f'{"" if note else f"<small> of {base}</small>"}</button></td>')
            else:
                tds += '<td class="zero">0</td>'
        body += f"<tr><th>{esc(label(v))}</th>{tds}</tr>"
    return (f'<figure class="fig"><div class="scroll"><table class="grid"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<figcaption>{caption(s)} Click a count for its passages.</figcaption></figure>')


def caption(s):
    """What a figure's counts are, and the base they all share where they share one."""
    note = heat([(c["n"], base_of(s, c)) for c in s["cells"] if c["n"]])[1]
    what = "Documents in each group" if s.get("count", "documents") == "documents" else "Coded passages in each group"
    return f"{what}. {note}" if note else f"{what}."


def link_ends(s, R):
    """The two ends of the causal links a tabulation counts, and their sign where the links are signed, when its input
    is a code step that names them."""
    src = next((w for w in R.get("workflow", {}).get("steps", []) if w.get("id") == s.get("input")), {})
    links = src.get("links") or {}
    return [links["from"], links["to"]] + ([links["sign"]] if links.get("sign") else []) if links else None


#: Graphviz for the reader's browser, at one version and held to its hash, loaded only by a report that has a map
GRAPHVIZ = ('<script src="https://cdn.jsdelivr.net/npm/@viz-js/viz@3.31.0/dist/viz-global.js" '
            'integrity="sha384-iX6VK6ib27dxYB4T470zbHOsDDoLewuYvrIgv2B3XXe8kgfKsGMf8QIleFy6VPi4" crossorigin="anonymous"></script>')


def graph(drawn):
    """A map's DOT, carried in the report for Graphviz to draw in the reader's browser (report.js), with the words a
    reader sees until it is drawn or if it cannot be."""
    return (f'<div class="graph"><pre class="dot" data-engine="{esc(drawn["engine"])}" hidden>{esc(drawn["dot"])}</pre>'
            f'<p class="small drawing">Drawing the map with Graphviz, which loads from the internet the first time a '
            f'report is opened.</p></div>')


def causal_map(s, cells, by):
    a, b = by[:2]
    edges = [{"id": c["id"], "from": c["values"][a], "to": c["values"][b], "n": c["n"],
              **({"sign": sign_of(c["values"][by[2]])} if len(by) == 3 else {}),
              **({"flipped": {**c["flipped"], "of": len(c["rows"])}} if "flipped" in c else {})} for c in cells if c["n"]]
    svg = graph(node.call(DRAW_MAP, {"edges": edges}, "map drawing"))
    signs = (" The sign at each arrowhead says whether the two move the same way (+), opposite ways (\u2212) or the "
             "source did not say (?).") if len(by) == 3 else ""
    opposites = (" Opposites are combined: a factor coded as the opposite of another, written with a leading ~, is drawn "
                 "as that other factor. Each arrow runs from blue to red at its tail as more of its passages concern the "
                 "opposite of its cause, and at its head as more concern the opposite of its effect; a factor's border "
                 "is coloured the same way.") if any(e.get("flipped") for e in edges) else ""
    return (f'<figure class="fig map">{svg}<figcaption>Each arrow is a causal link, numbered by the documents that '
            f'mention it.{signs}{opposites} Click an arrow or a factor for its passages.</figcaption></figure>')


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
        told = f'<button class="n" data-cell="{esc(whole["id"])}">{whole["n"]} of {s["of"]}</button>'
        out.append(f'<figure class="fig map loop">{svg}<figcaption>{esc(markers[lp])}: '
                   f'{esc(POLARITY_SAID[whole["values"]["polarity"]])}, told whole in {told} documents. Each arrow is '
                   f'numbered by the documents telling that link; a dashed box is a variable outside the loop that drives '
                   f'it. Click an arrow or a factor for its passages.</figcaption></figure>')
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
    return last if re.search(r"(?i)\blimit", last) else None


def answer_html(R, D, static=False):
    lines = R["answer"].splitlines()
    heads = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    R["sections"] = set(heads)
    renamed = R["renamed"] = {h: LIMITATIONS for h in [limitations_of(heads)] if h}
    # The answer's sections, for the report's contents: anchor and heading as the reader sees it
    R["toc"] = [(anchor(h), renamed.get(h, re.sub(r"[*`]", "", h))) for h in heads]
    title, lead, parts, cite_no = "", "", [], {}
    para, items, rows = [], [], []
    # What each finding rests on, the short answer and each section, for its "based on" button (report.js)
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
                         + ("" if static else f'<button class="based" data-based="{key}">based on</button>') + "</h2>")
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
            lead = lead[:-4] + ' <button class="based" data-based="short">based on</button></p>'
    for key, f in list(based.items()):
        for k in f:
            f[k] = list(dict.fromkeys(f[k]))
        if not f:
            del based[key]
            parts = [p.replace(f'<button class="based" data-based="{key}">based on</button>', "") for p in parts]
    R["unfilled"] = sorted(set(CELL.findall(title + lead + "".join(parts))))
    return title, lead, "\n".join(parts), cite_no


# ---------- the evidence matrix: every document against every value of the first passage-level code ----------

def matrix(R, D):
    step = next((s for s in R["steps"].values() if s.get("kind") == "code" and len(s.get("rows", [])) > len(s.get("documents", []))), None)
    if not step:
        return ""
    nominal = next((c for c in step["columns"] if c["type"] == "nominal"), None)
    binary = next((c for c in step["columns"] if c["type"] == "binary"), None)
    if not nominal:
        return ""
    vals = [v["name"] for v in nominal["values"]]
    by = {}
    for r in step["rows"]:
        by.setdefault((r["document"], r[nominal["name"]]), []).append(r)
    vals.sort(key=lambda v: -len({d for (d, x) in by if x == v}))
    groups = {}
    for d in R["index"]:
        groups.setdefault(d.get(D["group"], ""), []).append(d["id"])
    head = "".join(f'<th><span>{esc(label(v))}</span></th>' for v in vals)
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
                rid = ",".join(r["row"] for r in rs)
                tds += (f'<td><button class="dot {"own" if own else "raised"}" data-rows="{esc(rid)}" '
                        f'aria-label="{esc(did)}: {esc(label(v))}, {len(rs)} passage{"s" if len(rs) > 1 else ""}">'
                        f'{len(rs) if len(rs) > 1 else ""}</button></td>')
            body += (f'<tr><th class="doc"><button class="doclink" data-doc="{esc(did)}" title="Read {esc(did)} whole">'
                     f'{esc(did)}</button></th>{tds}</tr>')
    key = (f'<span class="dot own k"></span>{esc(label(binary["name"]))} for this reason'
           ' <span class="dot raised k"></span>Raised, not tied to that') if binary else ""
    return (f'<div class="legend small">{key}</div><div class="scroll"><table class="matrix"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ---------- the annex: how it was made ----------

#: What each kind of step makes, as the Rubicon page names a step's result (webapp/rubicon/js/model.js PIECE_MADE)
MADE = {"sample": "documents drawn", "code": "rows", "group": "codebook", "tabulate": "table", "judge": "verdicts",
        "write": "answer", "recode": "rows", "check": "record"}


def record_html(text):
    """A plain record such as check.md, which cites no counts and no rows, as paragraphs, lists and headings."""
    out, para, items = [], [], []
    def flush():
        nonlocal para, items
        if para:
            out.append(f"<p>{esc(' '.join(para))}</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>")
        para, items = [], []
    for ln in text.splitlines():
        t = ln.strip()
        if t.startswith("#"):
            flush()
            if not t.startswith("# "):
                out.append(f"<h4>{esc(t.lstrip('#').strip())}</h4>")
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
    """The workflow's steps, and for a checked run the check's own two after them: the second coder's blind coding,
    and the check that ruled on where the two codings differ and corrected the rows and the answer, which the answer
    reads. The second coder's rows count as made only where the zip holds them. The Rubicon page adds the same two to a run it opens from its zip (`model.piecesFromBundle`)."""
    steps = R["workflow"].get("steps", [])
    if not R.get("check"):
        return steps
    second = {"id": "second_coding", "kind": "recode", "inputs": []}
    check = {"id": "check", "kind": "check", "inputs": [st["id"] for st in steps if st.get("kind") == "code"] + ["second_coding"]}
    inputs = lambda st: list(st.get("inputs") or ([st["input"]] if st.get("input") else []))
    return [dict(st, inputs=inputs(st) + ["check"]) if st.get("kind") == "write" else st for st in steps] + [second, check]


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
    return nodes + edges


def passages_of(step):
    """A code step's passages, folded by the values of its first nominal column."""
    nominal = next((c for c in step.get("columns", []) if c["type"] == "nominal"), None)
    if not nominal:
        lis = "".join(f'<li><button class="rowlink" data-row="{esc(r["row"])}">{esc(r["document"])}</button> {esc(r["quote"])}</li>' for r in step.get("rows", []))
        return f'<ul class="quotes">{lis}</ul>'
    out = []
    for v in nominal["values"]:
        rs = [r for r in step["rows"] if r[nominal["name"]] == v["name"]]
        if rs:
            lis = "".join(f'<li><button class="rowlink" data-row="{esc(r["row"])}">{esc(r["document"])}</button> {esc(r["quote"])}</li>' for r in rs)
            out.append(f'<details><summary>{esc(label(v["name"]))} <span class="small">{len(rs)} passages</span></summary><ul class="quotes">{lis}</ul></details>')
    return "\n".join(out)


def table_of(sid, s, static=False):
    """A tabulate step's table: one row per cell, each count a button that opens who it counts, or for Word the count."""
    by = s.get("by", [])
    head = "".join(f"<th>{esc(label(b))}</th>" for b in by)
    trs = "".join("<tr>" + "".join(f'<td>{esc(label(c["values"].get(b, "")))}</td>' for b in by)
                  + (f'<td>{c["n"]}' if static else f'<td><button class="num" data-cell="{esc(c["id"])}">{c["n"]}</button>')
                  + (f' of {b}' if (b := base_of(s, c)) is not None else '') + '</td></tr>'
                  for c in s.get("cells", []))
    return (f'<div class="scroll"><table class="codebook"><thead><tr>{head}<th>{esc(label(s.get("count", "documents")))}</th>'
            f'</tr></thead><tbody>{trs}</tbody></table></div>')


def annex(R, D, static=False):
    wf = R["workflow"]
    out = []
    n = len(R["index"])
    gcounts = {}
    for d in R["index"]:
        gcounts[d.get(D["group"], "")] = gcounts.get(d.get(D["group"], ""), 0) + 1
    out.append("<h3>What was read</h3><p>All " + str(n) + " documents, read in full: "
               + ", ".join(f"{v} {esc(label(k).lower())}" for k, v in gcounts.items()) + ".</p>")
    # One block per step and one fold per step's result, each carrying the node the margin map names (report-map.js)
    for st in wf["steps"]:
        sid, kind = st["id"], st.get("kind", "")
        s = R["steps"].get(sid, {})
        body = []
        if kind == "code":
            unit = "one row for each document, read whole" if st.get("per_document") else "one row for each passage that fits"
            body.append(f'<h3>Coding: {esc(label(sid.removeprefix("c_")))}</h3>'
                        f'<p class="small">{esc(unit)}; {len(s.get("rows", []))} rows.</p>'
                        f'<details><summary>The instruction a second coder would follow</summary><blockquote>{esc(st.get("prompt",""))}</blockquote></details>')
            for col in st["columns"]:
                body.append(f'<h4>{esc(label(col["name"]))}</h4><p>{esc(col.get("means",""))}</p>'
                            + (f'<p class="small">Weak: {esc(col["weak"])}</p>' if col.get("weak") else ""))
                if col.get("values"):
                    trs = "".join(f'<tr><th>{esc(label(v["name"]))}</th><td>{esc(v.get("means",""))}</td>'
                                  f'<td>{esc(v.get("counts",""))}</td><td>{esc(v.get("does_not_count",""))}</td></tr>' for v in col["values"])
                    body.append(f'<div class="scroll"><table class="codebook"><thead><tr><th>Code</th><th>Means</th><th>Counts</th><th>Does not count</th></tr></thead><tbody>{trs}</tbody></table></div>')
            if s.get("rows") and not static:
                body.append(f'<div class="rb-block" data-node="asset:{esc(sid)}"><details><summary>The coded passages '
                            f'<span class="small">{len(s["rows"])} rows</span></summary>{passages_of(s)}</details></div>')
        elif kind == "tabulate":
            body.append(f'<h3>Counting: {esc(label(s.get("count", st.get("count", "documents"))))} by '
                        f'{esc(" and ".join(label(b).lower() for b in st.get("by", [])))} <span class="small">({esc(sid)})</span></h3>')
            if s.get("cells"):
                body.append(f'<div class="rb-block" data-node="asset:{esc(sid)}"><details><summary>The table '
                            f'<span class="small">{len(s["cells"])} cells</span></summary>{table_of(sid, s, static)}</details></div>')
        elif kind == "write":
            body.append(f'<h3>Writing the answer</h3><details><summary>The instruction the answer was written to</summary>'
                        f'<blockquote>{esc(st.get("instructions", ""))}</blockquote></details>')
        else:
            body.append(f'<h3>{esc(label(kind))}: {esc(label(sid))}</h3>')
        out.append(f'<section class="rb-block" data-node="step:{esc(sid)}">{"".join(body)}</section>')
    rp = R["report"]
    coded = rp.get("coding", {})
    nrows = sum(v.get("rows", 0) for v in coded.values())
    notfound = sum(len(v.get("quotations_not_found", [])) for v in coded.values())
    a = rp.get("answer", {})
    out.append("<h3>The checks code ran</h3><ul>"
               f"<li>{nrows - notfound} of {nrows} quotations found word for word in their document.</li>"
               f"<li>{a.get('counts_written_by_id',0)} numbers in the answer, every one counted by code; {len(a.get('numbers_written_bare',[]))} written by hand.</li>"
               f"<li>{len(a.get('citations_to_no_row',[]))} citations to passages that do not exist; {len(a.get('quotations_not_in_what_they_cite',[]))} quotations not in the passage they cite.</li></ul>")
    if R.get("check"):
        # The check's two steps, as the margin map draws them after the workflow's own (`drawn_steps`)
        counts = next((b.strip() for b in R["check"].split("\n\n") if b.strip() and not b.lstrip().startswith("#")), "")
        lis = "".join(f"<li>{esc(label(sid.removeprefix('c_')))}: {len(rows)} rows</li>" for sid, rows in R["recoded"].items())
        out.append('<section class="rb-block" data-node="step:second_coding"><h3>Second coding</h3><p>A second coder '
                   "coded the documents afresh to the same definitions, without seeing the first coding."
                   + ("" if R.get("recoded") else " The second coder's rows were not kept in this run's zip.") + "</p>"
                   + ("" if static or not R.get("recoded") else '<div class="rb-block" data-node="asset:second_coding">'
                      "<details><summary>The second coder's rows</summary>"
                      f'<ul>{lis}</ul><p class="small">In the run\'s zip, under <code>check/coded/</code>.</p></details></div>')
                   + "</section>")
        out.append('<section class="rb-block" data-node="step:check"><h3>The check</h3><p>A fresh reader ruled on every '
                   "place the two codings differed, and checked every sentence and quotation of the answer against the "
                   "documents, correcting the coding and the answer where they were wrong. The answer above is the "
                   "corrected one, recounted after the check.</p>"
                   + (f'<p class="small">{esc(counts)}</p>' if static and counts else "" if static else
                      '<div class="rb-block" data-node="asset:check"><details><summary>The check\'s record '
                      f'<span class="small">check.md</span></summary><div class="record">{record_html(R["check"])}</div></details></div>')
                   + "</section>")
    if R.get("fingerprint"):
        out.append("<h3>The record</h3><p>"
                   + (f"This is run <code>{esc(R['run_id'])}</code>. Its ID stays the same through every revision, and the "
                      "zip's fingerprint, below, names this version of it. " if R.get("run_id") else "")
                   + f"Code drew this report from the run's zip, {esc(R['zip'])}"
                   + (f", with Rubicon {esc(R['version'])}" if R.get("version") else "") + ". The zip's fingerprint is "
                   f'<code class="fingerprint">{R["fingerprint"]}</code>. It is the SHA-256 of the zip\'s SHA256SUMS '
                   "file, which lists the SHA-256 of every other file in the zip, so changing any file breaks the match. "
                   "To check that the zip is the one this report was drawn from, unzip it, run <code>sha256sum -c "
                   "SHA256SUMS</code>, then <code>sha256sum SHA256SUMS</code>, and compare the result with the "
                   "fingerprint above. Rubicon's own code, which is public, checks the rest: <code>python verify.py "
                   "&lt;report&gt; &lt;zip&gt;</code> recounts every number from the coded passages in the zip, draws "
                   "the report again from the zip and says whether it matches this one exactly.</p>")
    revised = [l.strip()[2:] for l in R.get("revisions", "").splitlines() if l.strip().startswith("- ")]
    if revised:
        out.append("<h3>Revisions</h3><p>Changes made after the first report, each recounted and checked before this "
                   "version was drawn. Earlier versions keep their own files.</p><ul>"
                   + "".join(f"<li>{esc(l)}</li>" for l in revised) + "</ul>")
    return "\n".join(out)


def further(R):
    """What comes after this draft: making sense of it with stakeholders, or, for a test on made-up documents,
    what the test's result calls for; the run's zip; and help from Causal Map."""
    test = bool(R["index"]) and n_synthetic(R) == len(R["index"])
    causal_map = ('<p>The Rubicon plugin for Claude is provided for free by Causal Map Ltd. Causal Map also runs '
                  'workshops and consultancy on analysing qualitative evidence for evaluation: '
                  '<a href="https://causalmap.app/contact/?utm_source=rubicon-plugin&amp;utm_medium=report">get in touch</a>, '
                  'or follow <a href="https://www.linkedin.com/company/causalmap/">Causal Map on LinkedIn</a>.'
                  + ('' if R.get("page") else ' Coming soon: continue your Rubicon work at the Rubicon website.') + '</p>')
    if test:
        return ('<p>This report is one half of a test of the workflow on made-up documents, and what it says about them '
                'matters only as a result of that test. Compare its verdict, and the other test set\'s, with the verdicts '
                'the documents were written to reach. If both match, save the workflow as it stands, with its date, and '
                'run it unchanged on the real documents. If either does not, find whether a document, the plan the '
                'documents were written from or the workflow went wrong, and correct that before testing again.</p>'
                f'<p><b>{esc(R["zip"])}</b>, saved beside this report, holds the whole run: the documents, the coded '
                'passages and the workflow that recounts every number. Keep it with the test\'s plan as the record of '
                'what was tested.</p>'
                + (handoff(R) if R.get("page") else '') + causal_map)
    return ('<p><b>For the evaluator:</b> Treat this report as a draft. Before it is final, make sense of it with the '
            'people it concerns, such as programme staff and participants: whether the findings ring true, what they '
            'leave out, and what to do about them. You can then use the Rubicon plugin to work their responses back into a '
            'revised answer.</p>'
            f'<p><b>For evaluation commissioners:</b> Parallel to this report is a zip file ({esc(R["zip"])}), saved in '
            'the same folder, which contains the whole run: the documents, the coded passages and the workflow that '
            'recounts every number. Its fingerprint, under How this was made, ties it to this report: change a file in '
            'either and they no longer match. With it, anyone can check every number against the coded passages, and code the '
            'documents again to the same definitions without Rubicon or any other particular software. A fresh coding '
            'will not reproduce this report word for word, because AI models are unpredictable, but it should come '
            'close.</p>'
            + (handoff(R) if R.get("page") else '') + causal_map)


#: Characters of documents a report carries for reading them whole; above this a reader opens them from the run's zip
TEXTS_CARRIED = 5_000_000


def packed_texts(R):
    """The documents, for reading one whole with every passage this run coded in it marked (report.js): gzipped JSON
    in base64, which the reader's browser unpacks only when a document is opened, or "" for a corpus too large
    to carry, whose documents the reader opens from the run's zip instead. Compressed by the same zlib that makes the
    zip, so the report is as deterministic as its zip."""
    if sum(map(len, R["texts"].values())) > TEXTS_CARRIED:
        return ""
    return base64.b64encode(gzip.compress(json.dumps(R["texts"], ensure_ascii=False).encode("utf-8"), mtime=0)).decode("ascii")


def texts(R):
    return f' const TEXTS = "{packed_texts(R)}";'


def run_zip(R):
    """The run itself, for the button to hand over (report.js), only where the report offers it."""
    if not R.get("page"):
        return ""
    folder = json.dumps(R.get("folder", "")).replace("</", "<\\/")
    return (f' const RUN_ZIP = {{name: {json.dumps(R["zip"])}, folder: {folder}, page: {json.dumps(R["page"])}, '
            f'zip: "{R.get("zip_b64", "")}"}};')


def handoff(R):
    """The button that opens the run on the Rubicon page, and what the report records so it can."""
    return ('<p><button class="open-cm" id="open-in-cm">Open in Causal Map</button> to explore the run in your browser, '
            'with every document in full and the workflow drawn. It needs a free Causal Map account. The run goes '
            'straight from this report to the page and is not saved to Causal Map.</p>'
            '<p class="small">This report also records where the run sits on this computer, '
            f'<code>{esc(R.get("folder", ""))}</code>, so that the page can offer to ask Claude about it. Anyone you '
            'send the report to can read that path, which may include your user name.</p>'
            '<p id="open-in-cm-said" class="small" hidden></p>')


def margin_map(R):
    """The margin map's script: the Rubicon page's own words.js, minimap.js and minimap-mount.js (copies kept
    identical to the page's) made one plain script, the map's elements, and report-map.js, which mounts the map beside the annex."""
    plain = lambda name: re.sub(r"^import .*$", "", (ENGINE / "rubicon_open" / name).read_text(encoding="utf-8"),
                                flags=re.M).replace("\nexport ", "\n")
    elements = json.dumps(map_elements(R), ensure_ascii=False).replace("</", "<\\/")
    return ("(() => {\n" + plain("words.js") + plain("minimap.js") + plain("minimap-mount.js")
            + f"\nconst ELEMENTS = {elements};\n" + (ENGINE / "report-map.js").read_text(encoding="utf-8") + "\n})();")


def sentences(md):
    """The answer's sentences, headings left out: what the check read one by one."""
    text = " ".join(l.strip().removeprefix("- ") for l in md.splitlines() if l.strip() and not l.lstrip().startswith(("#", "|", "{{")))
    return [t for t in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(*])", text) if t.strip()]


def summary(R, a, nrows):
    """The box under the short answer: what in this report can be checked, and, for a checked run, how many of its
    findings the check read against the documents."""
    out = ['<li class="head">Verification in this report:</li>',
           f"<li><b>{a.get('counts_written_by_id', 0)}</b> numbers, every one counted by code."
           '<span class="click"> Click any number to see who it counts.</span></li>',
           f"<li><b>{nrows}</b> quotations, every one found word for word in its interview."
           '<span class="click"> Click an interview\'s ID beside a quotation to read it in place.</span></li>']
    if R.get("check"):
        heads = sum(1 for l in R["answer"].splitlines() if l.startswith("## "))
        out.append(f"<li><b>{len(sentences(R['answer']))}</b> findings and <b>{heads}</b> high-level findings, every one "
                   "checked against the interviews after a second coder coded them blind.</li>")
    return "".join(out)


def facts(R, D):
    """The line under the short answer saying what the run read, and the box of what in it can be checked."""
    nrows = sum(len(s.get("rows", [])) for s in R["steps"].values() if s.get("kind") == "code")
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
    js = (Path(__file__).parent / "report.js").read_text(encoding="utf-8")
    map_js = margin_map(R)
    annexed = annexes(f"""<section class="evidence" id="evidence">
  <h2>Every interview at a glance</h2>
  <p class="small">Each row is one interview, each column a reason as the coding defines it. Click a mark to read the passages.</p>
  {matrix(R, D)}
</section>
<section class="annex" id="method">
  <h2>How this was made</h2>
  <p>The analysis was written down as a workflow before it was counted: what to look for, how to code it, what to count. Code then counted it from the coded passages, so anyone can check a number, and another coder can follow the same definitions and code the interviews afresh.</p>
  <div class="wf-gutter"></div>
  {annex(R, D)}
</section>
<aside class="next" id="next">
  <h2>What next</h2>
  {further(R)}
</aside>""")
    content = f"""<title>{esc(heading(R, title))}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap">
<style>{css}</style>
<div class="wrap">
{contents([("top", "Short answer")] + R["toc"], annexed)}
<main>
<header class="cover" id="top">
  <p class="eyebrow">Rubicon report</p>
  <h1>{esc(heading(R, title))}</h1>
  {asked(R)}
  {synthetic(R)}
  <div class="lead">{lead}</div>
  {facts(R, D)}
</header>
<article class="answer rb-block" data-node="asset:answer">{body}</article>
{annexed}
</main>
<aside class="panel" id="panel" hidden><button class="close" id="panel-close" aria-label="Close">×</button><div id="panel-body"></div></aside>
</div>
<script>const RUN = {data};{texts(R)}{run_zip(R)}</script>
{GRAPHVIZ if '<pre class="dot"' in body + map_js else ""}<script>{js}</script>
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
            f'{asked(R, static=True)}{synthetic(R)}{lead}{body}<h1 class="pb">{ANNEXES}</h1><h2>How this was made</h2>{annex(R, D, static=True)}<h2>Passages cited</h2>{notes}'
            f'<h2>What next</h2>{further(R)}</body></html>')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # a Windows console is not UTF-8, and the output names documents and arrows
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
        name = name_of(workflow, revisions)
        runs = folder.resolve().parent / "rubicon-runs.md"
        if not frag and runs.is_file() and re.search(rf"{re.escape(name)}-[0-9a-f]{{8}}\.html", runs.read_text(encoding="utf-8")):
            sys.exit(f"{name}-….html is already listed in {runs.name} as handed over, so it is not overwritten. A revision "
                     "adds its line to revisions.md first, and the report is then written under a new -revision- name.")
        page_url = sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else PAGE if HANDOFF else None
        render = {"name": name, "date": sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else "",
                  "page": page_url, "engine": engine_fingerprint(ENGINE), "version": engine_version(ENGINE)}
        if page_url:
            render["folder"] = str(folder.resolve())
        zipped = folder / f"{name}.zip.part"  # named once its fingerprint is known
        bundle(folder, zipped, render)
    refused = problems(zipped)
    if refused:
        zipped.unlink()
        sys.exit("No report is drawn: " + "; ".join(refused) + ".")
    # From here on the report reads the zip and nothing else
    R = load(zipped)
    zipped = zipped.replace(folder / R["zip"])
    if R["engine"] != engine_fingerprint(ENGINE):
        print(f"This engine is not the one that made the zip (Rubicon {R['version'] or 'of unknown version'}), so the "
              "report drawn here may differ from the one drawn when the zip was made.")
    out = folder / f"{R['name']}{'.fragment' if frag else ''}.html"
    drawn, doc = page(R, frag), word(R)
    if R["unfilled"]:
        sys.exit("No report is drawn: the answer writes " + ", ".join("{" + u + "}" for u in R["unfilled"])
                 + ", which no count in the run is called, so a reader would see the braces. Write a count's id as the "
                 "answer's tables give it, or the number in words.")
    out.write_text(drawn, encoding="utf-8")
    (folder / f"{R['name']}.doc").write_text(doc, encoding="utf-8")
    print(f"wrote {out.name}, {R['name']}.doc and {R['zip']} in {folder}")
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
