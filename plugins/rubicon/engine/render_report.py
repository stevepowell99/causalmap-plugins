"""Draw a Rubicon run folder as a report to read and click through, the same report for Word, and the run as a zip.

    python render_report.py <run folder> [--date "6 October 2026"] [--fragment] [--page <url of rubicon.html>]
    python render_report.py <run .zip>   [the same options]

The three files share one name, made from the question and the day: `<question>-<yyyy-mm-dd>.html`, `.doc` and
`.zip`. The zip is the recounted run in the open format (`recount/`: `workflow.json`, `run.json`, `steps/*.json`,
`corpus/` and `background/`), which the Rubicon page's "Open a downloaded run (.zip)" reads in the browser and
never saves. It holds the documents, because the page needs them to show each quotation in its place, and
`answer.md`, `counts.json` and `report.json`, so that given the zip in place of a folder this draws the report again
from the zip alone, into a folder beside it named after it (`unpack`).

Reads only what the run already holds (answer.md with its cell ids, recount/steps/*.json, recount/report.json,
corpus/index.csv and the corpus text for context around each quotation). Makes no model call, so it costs nothing
and draws the same report every time. Standard library and Node only.

In answer.md, a line holding only {{figure <table id>}} draws that table as a chart at that point. A table by the two
ends of a code step's causal links draws as a causal map, with Graphviz under Node (rubicon_open/draw_map.mjs).
--fragment writes the page without <html>/<head>/<body>, for publishing as an Artifact.

The report carries its zip, and its "Open in Causal Map" button hands the run to the Rubicon page in the reader's own
browser (`webapp/rubicon/js/receive.js` says how), so nobody downloads or uploads anything. --page points the button
at another copy of the page, such as a local one for testing.
"""
import base64, csv, datetime, html, json, re, shutil, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import node
from rubicon_open.corpus import INDEX_FIELDS

DRAW_MAP = Path(__file__).resolve().parent / "rubicon_open" / "draw_map.mjs"
PAGE = "https://app.causalmap.app/rubicon.html"
#: Whether a report offers to open its run on the Rubicon page (PAGE). Off until the live site, which serves `main`,
#: has the page that receives a run; `--page <url>` turns it on for one report, such as against the dev site.
#: `rubicon/plugin/build.py` reads this line, and leaves the skill's hand-over bullet out while it is off.
HANDOFF = False
CONTEXT = 420  # characters of the document shown either side of a quotation


def name_of(R):
    """The name the run's files share: the agreed question, cut to its first words, and today's date."""
    words, slug = re.findall(r"[a-z0-9]+", re.sub(r"['\u2019]", "", R["workflow"].get("question_as_agreed", "").lower())), ""
    for w in words:
        if len(slug) + len(w) > 50:
            break
        slug = f"{slug}-{w}" if slug else w
    return f"{slug or 'rubicon'}-{datetime.date.today().isoformat()}"


def bundle(run, out):
    """The recounted run as one zip, as the Rubicon page opens it."""
    rec = run / "recount"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("workflow.json", "run.json", "counts.json", "report.json"):
            z.write(rec / name, name)
        # The answer as written, cell ids and figure lines and all, so the zip alone rebuilds the report (`unpack`)
        z.write(run / "answer.md", "answer.md")
        for sub in ("steps", "corpus", "background"):
            for p in sorted((rec / sub).rglob("*")) if (rec / sub).is_dir() else []:
                if p.is_file():
                    z.write(p, p.relative_to(rec).as_posix())
        # The second reading: the check's record and the second coder's own rows, beside the run they checked
        for p in [run / "check.md"] + [run / "recode" / f for f in ("disagreements.md", "unclear.md")] \
                + sorted((run / "recode" / "coded").glob("*.json")):
            if p.is_file():
                z.write(p, "check/" + p.relative_to(run).as_posix().removeprefix("recode/"))


def unpack(zipped, run):
    """A run's zip laid out again as the run folder it was made from, so the report can be drawn from the zip alone:
    the recount at `recount/`, the answer, the check and the second coder's rows where they were, and the workflow and
    documents at the top as `load` reads them."""
    if run.exists():
        sys.exit(f"{run} already exists; move it, or draw the report from that folder instead")
    with zipfile.ZipFile(zipped) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            to = (run / n if n == "answer.md" else run / n.removeprefix("check/") if n == "check/check.md"
                  else run / "recode" / n.removeprefix("check/") if n.startswith("check/") else run / "recount" / n)
            to.parent.mkdir(parents=True, exist_ok=True)
            to.write_bytes(z.read(n))
    if not (run / "answer.md").exists():
        shutil.rmtree(run)
        sys.exit(f"{zipped.name} was made before a run's zip carried its answer, so the report cannot be drawn from it "
                 "alone; draw it from the run's folder instead")
    shutil.copy2(run / "recount" / "workflow.json", run / "workflow.json")
    shutil.copytree(run / "recount" / "corpus", run / "corpus")


def esc(s):
    return html.escape(str(s), quote=True)


def label(v):
    return str(v).replace("_", " ").strip().capitalize()


def load(run):
    steps = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (run / "recount/steps").glob("*.json")}
    with open(run / "corpus/index.csv", encoding="utf-8") as f:
        index = list(csv.DictReader(f))
    texts = {}
    for d in index:
        p = run / "corpus" / (d.get("file") or f"{d['id']}.txt")
        texts[d["id"]] = p.read_text(encoding="utf-8") if p.exists() else ""
    return {
        "workflow": json.loads((run / "workflow.json").read_text(encoding="utf-8")),
        "steps": steps,
        "counts": json.loads((run / "recount/counts.json").read_text(encoding="utf-8")),
        "report": json.loads((run / "recount/report.json").read_text(encoding="utf-8")),
        "answer": (run / "answer.md").read_text(encoding="utf-8"),
        "index": index,
        "texts": texts,
        "check": (run / "check.md").read_text(encoding="utf-8") if (run / "check.md").exists() else "",
    }


def group_column(index):
    cols = [c for c in index[0].keys() if c not in INDEX_FIELDS] if index else []
    return cols[0] if cols else None


def build_data(R):
    """Everything the page's script needs: rows with context, cells, documents."""
    gcol = group_column(R["index"])
    docs = {d["id"]: {"group": d.get(gcol, ""), "title": d.get("title", d["id"])} for d in R["index"]}
    rows, cells, defs = {}, {}, {}
    for sid, s in R["steps"].items():
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
                rows[r["row"]] = {"doc": r["document"], "step": sid, "ctx": ctx, "codes": codes}
        elif s.get("kind") == "tabulate":
            for c in s.get("cells", []):
                cells[c["id"]] = {"values": c["values"], "n": c["n"], "base": c.get("base", s.get("of")),
                                  "docs": c.get("documents", []), "rows": c.get("rows", []), "step": sid}
    return {"docs": docs, "rows": rows, "cells": cells, "defs": defs, "group": gcol}


# ---------- the answer: markdown with cell ids and row citations ----------

CITE = re.compile(r"\[([a-z][\w]*\.[a-z0-9]+(?:\s*,\s*[a-z][\w]*\.[a-z0-9]+)*)\]")
CELL = re.compile(r"\{([a-z][\w]*\.(?:c\d+|of)(?:\.within\.[\w]+)?)\}")
FIG = re.compile(r"^\{\{figure\s+([\w]+)\}\}$")


def inline(text, R, cite_no, static):
    out = esc(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)

    def cell(m):
        cid = m.group(1)
        txt = R["counts"].get(cid, cid)
        if static:
            return esc(txt)
        base = re.sub(r"\.within\..*$", "", cid)
        return f'<button class="n" data-cell="{esc(base)}">{esc(txt)}</button>'

    def cite(m):
        ids = [i.strip() for i in m.group(1).split(",")]
        chips = []
        for i in ids:
            if i not in cite_no:
                cite_no[i] = len(cite_no) + 1
            k = cite_no[i]
            chips.append(f"<sup>{k}</sup>" if static else f'<button class="cite" data-row="{esc(i)}" aria-label="Passage {k}">{k}</button>')
        return "".join(chips)

    out = CELL.sub(cell, out)
    out = CITE.sub(cite, out)
    return out


def figure(tid, R, D):
    s = R["steps"].get(tid)
    if not s or s.get("kind") != "tabulate":
        R.setdefault("missing_figures", []).append(tid)
        return ""
    by = s["by"]
    if len(by) > 2:  # a chart shows two columns at most; drawing the first two would drop the rest and mislead
        R.setdefault("wide_figures", []).append(tid)
        return ""
    cells = [c for c in s["cells"]]
    if len(by) == 2 and by == link_ends(s, R):
        return causal_map(s, cells)
    if len(by) == 1:
        rows = sorted(cells, key=lambda c: -c["n"])
        mx = max([c.get("base") or s["of"] for c in rows] + [1])
        bars = "".join(
            f'<div class="bar-row"><span class="bar-label">{esc(label(c["values"][by[0]]))}</span>'
            f'<span class="bar-track"><button class="bar" data-cell="{esc(c["id"])}" style="width:{100*c["n"]/mx:.1f}%"></button></span>'
            f'<span class="bar-n">{c["n"]}</span></div>' for c in rows)
        return f'<figure class="fig"><div class="bars">{bars}</div><figcaption>Documents, out of {s["of"]}. Click a bar for its passages.</figcaption></figure>'
    a, b = by[0], by[1]
    avals = list(dict.fromkeys(c["values"][a] for c in cells))
    bvals = list(dict.fromkeys(c["values"][b] for c in cells))
    look = {(c["values"][a], c["values"][b]): c for c in cells}
    if set(bvals) <= {"yes", "no"}:  # a binary split: two bars a value, never stacked, as one document can be in both
        avals.sort(key=lambda v: -sum(look.get((v, x), {"n": 0})["n"] for x in ("yes", "no")))
        yes_l = label(b) + " for this reason"
        out = []
        for v in avals:
            pair = ""
            for x, cls in (("yes", "yes"), ("no", "no")):
                c = look.get((v, x))
                n = c["n"] if c else 0
                w = 100 * n / s["of"]
                btn = f'<button class="bar {cls}" data-cell="{esc(c["id"])}" style="width:{w:.1f}%"></button>' if c and n else ""
                pair += f'<span class="bar-track thin">{btn}</span><span class="bar-n">{n}</span>'
            out.append(f'<div class="bar-row pair"><span class="bar-label">{esc(label(v))}</span><span class="pair-bars">{pair}</span></div>')
        legend = (f'<span class="key yes"></span>{esc(yes_l)} <span class="key no"></span>Raised, not tied to that')
        return (f'<figure class="fig"><div class="legend">{legend}</div><div class="bars">{"".join(out)}</div>'
                f'<figcaption>Interviewees, out of {s["of"]}. Click a bar for the passages behind it.</figcaption></figure>')
    # two nominal columns: a grid of counts within each column of b
    avals.sort(key=lambda v: -sum(look.get((v, x), {"n": 0})["n"] for x in bvals))
    head = "".join(f"<th>{esc(label(x))}</th>" for x in bvals)
    body = ""
    for v in avals:
        tds = ""
        for x in bvals:
            c = look.get((v, x))
            n, base = (c["n"], c.get("base") or s["of"]) if c else (0, 1)
            shade = n / base if base else 0
            tds += (f'<td><button class="cellbtn" data-cell="{esc(c["id"])}" style="--a:{shade:.2f}">{n}<small> of {base}</small></button></td>'
                    if c and n else '<td class="zero">0</td>')
        body += f"<tr><th>{esc(label(v))}</th>{tds}</tr>"
    return f'<figure class="fig"><div class="scroll"><table class="grid"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div><figcaption>Interviewees in each group. Click a count for its passages.</figcaption></figure>'


def link_ends(s, R):
    """The two ends of the causal links a tabulation counts, when its input is a code step that names them."""
    src = next((w for w in R["workflow"].get("steps", []) if w.get("id") == s.get("input")), {})
    links = src.get("links") or {}
    return [links["from"], links["to"]] if links else None


def causal_map(s, cells):
    a, b = s["by"]
    edges = [{"id": c["id"], "from": c["values"][a], "to": c["values"][b], "n": c["n"]} for c in cells if c["n"]]
    svg = node.call(DRAW_MAP, {"edges": edges}, "map drawing")["svg"]
    svg = svg[svg.index("<svg"):]
    return (f'<figure class="fig map">{svg}<figcaption>Each arrow is a causal link, numbered by the documents that '
            f'mention it. Click an arrow for its passages.</figcaption></figure>')


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


def synthetic(R):
    """A notice that the report rests on made-up documents, wherever the index marks any as synthetic."""
    n = sum(1 for d in R["index"] if (d.get("synthetic") or "").strip().lower() == "yes")
    if not n:
        return ""
    of = "All" if n == len(R["index"]) else f"{n} of the {len(R['index'])}"
    return (f'<p class="synthetic"><b>Synthetic documents.</b> {of} documents were written by Claude to test the method. '
            'They are not records of real people, and nothing in this report is evidence about anyone.</p>')


def answer_html(R, D, static=False):
    lines = R["answer"].splitlines()
    title, lead, parts, cite_no = "", "", [], {}
    para, items, rows = [], [], []

    def flush():
        nonlocal para, items, rows
        if rows:
            cells = [[inline(c.strip(), R, cite_no, static) for c in r.strip().strip("|").split("|")] for r in rows
                     if not re.fullmatch(r"[\s|:-]+", r)]
            head, body = cells[0], cells[1:]
            parts.append('<table class="md"><thead><tr>' + "".join(f"<th>{c}</th>" for c in head) + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>")
        if para:
            parts.append(f"<p>{inline(' '.join(para), R, cite_no, static)}</p>")
        if items:
            parts.append("<ul>" + "".join(f"<li>{inline(i, R, cite_no, static)}</li>" for i in items) + "</ul>")
        para, items, rows = [], [], []

    for ln in lines:
        s = ln.rstrip()
        if s.startswith("# "):
            flush(); title = s[2:]; continue
        if s.startswith("## "):
            flush(); parts.append(f"<h2>{inline(s[3:], R, cite_no, static)}</h2>"); continue
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
    # the first paragraph is the short answer
    if parts and parts[0].startswith("<p>"):
        lead = parts.pop(0)
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
            body += f"<tr><th class=\"doc\">{esc(did)}</th>{tds}</tr>"
    key = (f'<span class="dot own k"></span>{esc(label(binary["name"]))} for this reason'
           ' <span class="dot raised k"></span>Raised, not tied to that') if binary else ""
    return (f'<div class="legend small">{key}</div><div class="scroll"><table class="matrix"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ---------- the annex: how it was made ----------

def annex(R, D):
    wf = R["workflow"]
    out = []
    n = len(R["index"])
    gcounts = {}
    for d in R["index"]:
        gcounts[d.get(D["group"], "")] = gcounts.get(d.get(D["group"], ""), 0) + 1
    out.append("<h3>What was read</h3><p>All " + str(n) + " documents, read in full: "
               + ", ".join(f"{v} {esc(label(k).lower())}" for k, v in gcounts.items()) + ".</p>")
    for st in wf["steps"]:
        if st["kind"] == "code":
            s = R["steps"].get(st["id"], {})
            unit = "one row for each document, read whole" if st.get("per_document") else "one row for each passage that fits"
            out.append(f'<h3>Coding: {esc(label(st["id"].removeprefix("c_")))}</h3>'
                       f'<p class="small">{esc(unit)}; {len(s.get("rows", []))} rows.</p>'
                       f'<details><summary>The instruction a second coder would follow</summary><blockquote>{esc(st.get("prompt",""))}</blockquote></details>')
            for col in st["columns"]:
                out.append(f'<h4>{esc(label(col["name"]))}</h4><p>{esc(col.get("means",""))}</p>')
                if col.get("values"):
                    trs = "".join(f'<tr><th>{esc(label(v["name"]))}</th><td>{esc(v.get("means",""))}</td>'
                                  f'<td>{esc(v.get("counts",""))}</td><td>{esc(v.get("does_not_count",""))}</td></tr>' for v in col["values"])
                    out.append(f'<div class="scroll"><table class="codebook"><thead><tr><th>Code</th><th>Means</th><th>Counts</th><th>Does not count</th></tr></thead><tbody>{trs}</tbody></table></div>')
    tabs = [st for st in wf["steps"] if st["kind"] == "tabulate"]
    if tabs:
        lis = "".join(f'<li>{esc(label(st.get("count", "documents")))} by {esc(" and ".join(label(b).lower() for b in st["by"]))}'
                      f' <span class="small">({esc(st["id"])})</span></li>' for st in tabs)
        out.append(f"<h3>What was counted</h3><ul>{lis}</ul>")
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
        counts = next((b.strip() for b in R["check"].split("\n\n") if b.strip() and not b.lstrip().startswith("#")), "")
        out.append("<h3>The second reading</h3><p>A second coder coded the documents afresh to the same definitions "
                   "without seeing the first coding. A fresh reader then ruled on every place the two differed, and "
                   "checked every sentence and quotation of the answer against the documents, correcting the coding and "
                   "the answer where they were wrong. Its record is <code>check.md</code>, in the run's zip with the "
                   "second coder's rows.</p>" + (f'<p class="small">{esc(counts)}</p>' if counts else ""))
    return "\n".join(out)


def passages(R, D):
    step = next((s for s in R["steps"].values() if s.get("kind") == "code" and len(s.get("rows", [])) > len(s.get("documents", []))), None)
    if not step:
        return ""
    nominal = next((c for c in step["columns"] if c["type"] == "nominal"), None)
    out = []
    for v in nominal["values"]:
        rs = [r for r in step["rows"] if r[nominal["name"]] == v["name"]]
        if not rs:
            continue
        lis = "".join(f'<li><button class="rowlink" data-row="{esc(r["row"])}">{esc(r["document"])}</button> {esc(r["quote"])}</li>' for r in rs)
        out.append(f'<details><summary>{esc(label(v["name"]))} <span class="small">{len(rs)} passages</span></summary><ul class="quotes">{lis}</ul></details>')
    return "\n".join(out)


def further(R):
    """What comes after this draft: making sense of it with stakeholders, the run's zip, and help from Causal Map."""
    return ('<p>Treat this report as a draft. Before it is final, make sense of it with the people it concerns, such as '
            'programme staff and participants: whether the findings ring true, what they leave out, and what to do about '
            'them. Their responses can go back into a revised answer.</p>'
            f'<p><b>{esc(R["zip"])}</b>, saved beside this report, holds the whole run: the documents, the coded '
            'passages and the workflow that recounts every number. Keep it, or pass it on to people allowed to read '
            'the documents.</p>'
            + (handoff(R) if R.get("page") else '') +
            '<p>Causal Map also runs workshops and consultancy on '
            'analysing qualitative evidence for evaluation: '
            '<a href="https://causalmap.app/?utm_source=rubicon-plugin&amp;utm_medium=report">causalmap.app</a>.</p>')


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


def page(R, fragment=False):
    D = build_data(R)
    title, lead, body, cite_no = answer_html(R, D)
    nrows = sum(len(s.get("rows", [])) for s in R["steps"].values() if s.get("kind") == "code")
    a = R["report"].get("answer", {})
    data = json.dumps(D, ensure_ascii=False).replace("</", "<\\/")
    css = (Path(__file__).parent / "report.css").read_text(encoding="utf-8")
    js = (Path(__file__).parent / "report.js").read_text(encoding="utf-8")
    groups = {}
    for d in R["index"]:
        groups[d.get(D["group"], "")] = 1
    content = f"""<title>{esc(heading(R, title))}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap">
<style>{css}</style>
<div class="wrap">
<main>
<header class="cover">
  <p class="eyebrow">Rubicon report</p>
  <h1>{esc(heading(R, title))}</h1>
  {asked(R)}
  {synthetic(R)}
  <div class="lead">{lead}</div>
  <p class="meta">{len(R["index"])} interviews in {len(groups)} groups · {nrows} passages coded · {esc(R.get("date",""))}</p>
  <ul class="checks">
    <li><b>{a.get("counts_written_by_id",0)}</b> numbers, every one counted by code. Click any number to see who it counts.</li>
    <li><b>{nrows}</b> quotations, every one found word for word in its interview. Click a numbered marker to read it in place.</li>
  </ul>
</header>
<article class="answer">{body}</article>
<section class="evidence" id="evidence">
  <h2>Every interview at a glance</h2>
  <p class="small">Each row is one interview, each column a reason as the coding defines it. Click a mark to read the passages.</p>
  {matrix(R, D)}
</section>
<section class="annex" id="method">
  <h2>How this was made</h2>
  <p>The analysis was written down as a workflow before it was counted: what to look for, how to code it, what to count. Code then counted it from the coded passages, so anyone can check a number, and another coder can follow the same definitions and code the interviews afresh.</p>
  {annex(R, D)}
  <h3>All coded passages</h3>
  {passages(R, D)}
</section>
<aside class="next">
  <h2>What next</h2>
  {further(R)}
</aside>
</main>
<aside class="panel" id="panel" hidden><button class="close" id="panel-close" aria-label="Close">×</button><div id="panel-body"></div></aside>
</div>
<script>const RUN = {data};{run_zip(R)}</script>
<script>{js}</script>
"""
    if fragment:
        return content
    head, body = content.split('<div class="wrap">', 1)
    return f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{head}</head><body><div class="wrap">{body}</body></html>'


def word(R):
    """The same report for Word: figures as text, citations as numbered notes with their quotations."""
    D = build_data(R)
    title, lead, body, cite_no = answer_html(R, D, static=True)
    notes = "".join(f'<p class="note"><sup>{k}</sup> {esc(D["rows"].get(rid, {}).get("doc",""))}: "{esc(D["rows"].get(rid, {}).get("ctx", ["","",""])[1])}"</p>'
                    for rid, k in sorted(cite_no.items(), key=lambda x: x[1]))
    return ('<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" '
            'xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8">'
            f'<title>{esc(heading(R, title))}</title><!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->'
            '<style>body,p,li,td{font-family:Cambria,Georgia,serif;font-size:11pt;line-height:1.35;color:#17130f}'
            'h1,h2,h3{font-family:Cambria,Georgia,serif;font-weight:normal;color:#8c1912}h1{font-size:20pt}h2{font-size:14pt}'
            'p.note{font-size:9pt}td,th{border:1px solid #e4dcd0;padding:3pt 5pt;font-size:9pt;vertical-align:top}table{border-collapse:collapse}</style></head><body>'
            f'<p style="color:#8b7f72;font-size:9pt">RUBICON REPORT</p><h1>{esc(heading(R, title))}</h1>'
            f'{asked(R, static=True)}{synthetic(R)}{lead}{body}<h2>How this was made</h2>{annex(R, D)}<h2>Passages cited</h2>{notes}'
            f'<h2>What next</h2>{further(R)}</body></html>')


if __name__ == "__main__":
    run = Path(sys.argv[1])
    if run.suffix.lower() == ".zip":  # a run's zip opens as the folder beside it, named after it
        unpack(run, run.with_suffix(""))
        run = run.with_suffix("")
    R = load(run)
    name = name_of(R)
    R["zip"] = f"{name}.zip"
    R["date"] = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else ""
    frag = "--fragment" in sys.argv
    R["page"] = sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else PAGE if HANDOFF else None
    out = run / f"{name}{'.fragment' if frag else ''}.html"
    bundle(run, run / R["zip"])
    if R["page"]:
        R["folder"] = str(run.resolve())
        R["zip_b64"] = base64.b64encode((run / R["zip"]).read_bytes()).decode("ascii")
    out.write_text(page(R, frag), encoding="utf-8")
    (run / f"{name}.doc").write_text(word(R), encoding="utf-8")
    print(f"wrote {out.name}, {name}.doc and {R['zip']} in {run}")
    if R.get("missing_figures"):
        print("figure lines naming no table, left out: " + ", ".join(sorted(set(R["missing_figures"]))))
    if R.get("wide_figures"):
        print("figure lines naming a table of more than two columns, which no chart shows, left out: "
              + ", ".join(sorted(set(R["wide_figures"]))) + "; write that comparison as a table of its cell ids instead")
