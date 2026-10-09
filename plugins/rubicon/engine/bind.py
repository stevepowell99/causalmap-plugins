"""Combine the reports of several Rubicon runs into one combined report: a cover, the questions with their short answers, each answer in
turn, and every run's annex gathered at the end, as a page to read and click through and the same for Word.

    python bind.py <report .html> <report .html> [...] [--title "..."] [--date "9 October 2026"] [--out <folder>]
    python bind.py --folder <documents folder> [the same options]

Given reports, it combines them in the order given; given a documents folder, it combines every run listed in its
`rubicon-runs.md` or lying in one of its run folders (`register.runs_in`), each at its latest revision, in the order the
runs were answered. A combined report re-derives nothing. Each part is drawn by `render_report.py`'s own functions from that
run's sealed zip and from nothing else, and a run is refused, and named, when its report does not name its zip, its
zip's seal is broken, or a fresh recount of its coded rows and answer would change its counts (`render_report.problems`),
so every number and quotation in the combined report is one its run's report already carries and can be checked as it can.
Each part names the run it came from: its ID, its zip and fingerprint, and the chat that first recounted it where the
run recorded one.

The combined report is titled `--title`, else from its parts' headings (`default_title`). Its two files are written beside the documents (or into `--out`), named from its title, the day and the
first eight characters of its own fingerprint, the SHA-256 of its parts' fingerprints in order, so a combined report of the same
runs always carries the same name for the day. Makes no model call. Standard library and Node only.
"""
import datetime, hashlib, json, re, sys, zipfile
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as render_report.py does
import register
import render_report as RR
from rubicon_open.seal import engine_fingerprint

ENGINE = Path(__file__).resolve().parent
REVISION = re.compile(r"-revision-(\d+)-[0-9a-f]{8}$")


def latest(listed):
    """Each run of a documents folder once, at its latest revision, in the order the runs were first answered. A run
    is its run folder; a report that cannot be bound is kept with its fault, so the caller can name it."""
    by_folder = {}
    for report, run in listed:
        by_folder.setdefault(report.parent, []).append((report, run))
    out = []
    for versions in by_folder.values():
        sound = [(r, x) for r, x in versions if "fault" not in x and "unsealed" not in x]
        rev = lambda r: int(m.group(1)) if (m := REVISION.search(r.stem)) else 0
        out.append(max(sound, key=lambda v: (rev(v[0]), v[1]["day"])) if sound else versions[-1])
    return sorted(out, key=lambda v: (v[1].get("day") or datetime.date.min, v[0].stat().st_mtime if v[0].is_file() else 0))


def refused(report):
    """Why a report cannot be bound, or None: its zip is missing, broken or not the one it names, it was drawn before
    reports were sealed, or its recount does not follow from its own coded rows and answer."""
    run = register.run_of(report) if report.is_file() else {"fault": "the report is not there"}
    if "fault" in run or "unsealed" in run:
        return run.get("fault") or run["unsealed"]
    faults = RR.problems(report.with_suffix(".zip"))
    return "; ".join(faults) if faults else None


def scoped(html, k):
    """A part's markup with its section anchors made its own, since two answers can share a heading."""
    return re.sub(r'(id="|href="#)s-', rf"\1p{k}-s-", html)


def chat_of(zipped):
    """The chat that first recounted the run, as its `run.json` records it, or {}."""
    with zipfile.ZipFile(zipped) as z:
        try:
            return json.loads(z.read("run.json").decode("utf-8")).get("chat") or {}
        except (KeyError, ValueError, AttributeError):
            return {}


def part(k, report):
    """One run as the combined report draws it: its answer and its annex, interactive and for Word, and what names it."""
    zipped = report.with_suffix(".zip")
    R = RR.load(zipped)
    if R["engine"] != engine_fingerprint(ENGINE):
        print(f"{report.name} was drawn by another engine (Rubicon {R['version'] or 'of unknown version'}), so its part "
              "here may differ from that report.")
    D = RR.build_data(R)
    title, lead, body, _ = RR.answer_html(R, D)
    if R["unfilled"]:
        sys.exit(f"No combined report is drawn: {report.name} writes " + ", ".join("{" + u + "}" for u in R["unfilled"])
                 + ", which no count in its run is called.")
    figures_left = sorted(set(R.get("missing_figures", []) + R.get("wide_figures", [])))
    if figures_left:
        print(f"{report.name}: figure lines left out, as in its own report: {', '.join(figures_left)}")
    page = {"title": title, "lead": lead, "body": body, "facts": RR.facts(R, D), "matrix": RR.matrix(R, D),
            "annex": RR.annex(R, D), "data": D, "texts": RR.packed_texts(R)}
    S = RR.build_data(R)
    stitle, slead, sbody, cite_no = RR.answer_html(R, S, static=True)
    notes = "".join(f'<p class="note">{RR.esc(S["rows"].get(rid, {}).get("doc", ""))}: '
                    f'"{RR.esc(S["rows"].get(rid, {}).get("ctx", ["", "", ""])[1])}"</p>'
                    for rid, _ in sorted(cite_no.items(), key=lambda x: x[1]))
    word = {"lead": slead, "body": sbody, "annex": RR.annex(R, S, static=True), "notes": notes}
    return {"k": k, "R": R, "report": report, "heading": RR.heading(R, title), "chat": chat_of(zipped),
            "page": {n: scoped(v, k) if isinstance(v, str) else v for n, v in page.items()}, "word": word}


#: A group of citations as `render_report.inline` draws one, and a finding's "based on" button: left out of the index
CHIPS = re.compile(r'\s*\((?:<button class="cite"[^>]*>.*?</button>(?:, |; )?)+\)|<button class="based"[^>]*>.*?</button>')


def plain(markup):
    """A short answer as the index gives it: its words, without the citations its part carries, and as the words
    themselves (an apostrophe is not `&#x27;`), since the caller escapes them again where it writes them."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", CHIPS.sub("", markup)))).strip()


def provenance(p, static=False):
    """Which report a part was handed over as, and the chat that first recounted its run; its run ID, zip and
    fingerprint follow under "The record" in its annex, as in its own report."""
    url, esc = p["chat"].get("url"), RR.esc
    chat = ((f' Its run was first recounted in <a href="{esc(url)}">this chat</a>.' if not static
             else f" Its run was first recounted in the chat at {esc(url)}.") if url else "")
    return f'<p class="small">Handed over as {esc(p["report"].name)}.{chat}</p>'


def about(parts, documents):
    n = len(parts)
    where = (f"the documents in {RR.esc(documents[0])}" if len(documents) == 1
             else f"documents in {len(documents)} folders ({', '.join(RR.esc(d) for d in documents)})")
    return (f"<p>This combined report brings together {n} Rubicon reports, each answering one question from {where}. Each part "
            "is drawn unchanged from its own run's sealed zip, which was recounted before the reports were combined: every number "
            "in it was counted by code from that run's coded passages, and every quotation found word for word in its "
            "document. The annexes saying how each answer was made, one for each part, are gathered at the end.</p>")


def binder_html(parts, title, date, documents):
    esc, n = RR.esc, len(parts)
    css = (ENGINE / "report.css").read_text(encoding="utf-8") + BINDER_CSS
    js = (ENGINE / "report.js").read_text(encoding="utf-8")
    index = "".join(
        f'<li><a href="#q-{p["k"]}">{esc(p["heading"])}</a>'
        + (f'<span class="qanswer">{esc(plain(p["page"]["lead"]))}</span>' if p["page"]["lead"] else "")
        + f'<span class="small">{"Run " + esc(p["R"]["run_id"]) + " · " if p["R"].get("run_id") else ""}'
          f'<a href="#annex-{p["k"]}">annex</a></span></li>' for p in parts)
    sections = "".join(f"""
<section class="part" id="q-{p["k"]}" data-run="{i}">
  <p class="eyebrow">Question {p["k"]} of {n}</p>
  <h2 class="part-title">{esc(p["heading"])}</h2>
  {RR.asked(p["R"])}
  {RR.synthetic(p["R"])}
  <div class="lead">{p["page"]["lead"]}</div>
  {p["page"]["facts"]}
  <article class="answer">{p["page"]["body"]}</article>
  <p class="small"><a href="#annex-{p["k"]}">Annex {p["k"]}: how this answer was made</a> · <a href="#contents">The questions</a></p>
</section>""" for i, p in enumerate(parts))
    annexes = RR.annexes("".join(f"""
<section class="annex part-annex" id="annex-{p["k"]}" data-run="{i}">
  <p class="eyebrow">Annex {p["k"]} of {n}</p>
  <h2 class="part-title">{esc(p["heading"])}</h2>
  {provenance(p)}
  {"<h3>Every interview at a glance</h3><p class='small'>Each row is one interview, each column a reason as the coding defines it. Click a mark to read the passages.</p>" + p["page"]["matrix"] if p["page"]["matrix"] else ""}
  {p["page"]["annex"]}
  <p class="small"><a href="#q-{p["k"]}">Back to question {p["k"]}</a></p>
</section>""" for i, p in enumerate(parts)))
    toc = RR.contents([("contents", "The questions")] + [(f'q-{p["k"]}', p["heading"]) for p in parts], annexes)
    data = json.dumps([{"data": p["page"]["data"], "texts": p["page"]["texts"]} for p in parts],
                      ensure_ascii=False).replace("</", "<\\/")
    dots = any('<pre class="dot"' in p["page"]["body"] for p in parts)
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap">
<style>{css}</style></head><body><div class="wrap">
{toc}
<main>
<header class="cover">
  <p class="eyebrow">Rubicon combined report</p>
  <h1>{esc(title)}</h1>
  <p class="meta">{n} questions · {esc(date)}</p>
  <div class="about">{about(parts, documents)}</div>
</header>
<nav class="contents" id="contents"><h2>The questions</h2><ol>{index}</ol></nav>
{sections}
{annexes}
</main>
<aside class="panel" id="panel" hidden><button class="close" id="panel-close" aria-label="Close">×</button><div id="panel-body"></div></aside>
</div>
<script>var PARTS = {data}; var RUN = PARTS[0].data, TEXTS = PARTS[0].texts, SCOPE = '[data-run="0"]';
// Whatever is clicked inside a part makes that part's run the one report.js reads; the panel keeps the last one
document.addEventListener('click', e => {{
  const p = e.target.closest('[data-run]');
  if (p) {{ const x = PARTS[+p.dataset.run]; RUN = x.data; TEXTS = x.texts; SCOPE = `[data-run="${{p.dataset.run}}"]`; }}
}}, true);</script>
{RR.GRAPHVIZ if dots else ""}<script>{js}</script>
</body></html>"""


def binder_word(parts, title, date, documents):
    esc, n = RR.esc, len(parts)
    index = "".join(f'<li>{esc(p["heading"])}{": " + esc(plain(p["page"]["lead"])) if p["page"]["lead"] else ""}</li>' for p in parts)
    body = "".join(
        f'<h2>Question {p["k"]} of {n}: {esc(p["heading"])}</h2>{RR.asked(p["R"], static=True)}{RR.synthetic(p["R"])}'
        f'{p["word"]["lead"]}{p["word"]["body"]}' for p in parts)
    annexes = "".join(
        f'<h2>Annex {p["k"]}: {esc(p["heading"])}</h2>{provenance(p, static=True)}{p["word"]["annex"]}'
        f'<h3>Passages cited</h3>{p["word"]["notes"]}' for p in parts)
    return ('<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" '
            'xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8">'
            f'<title>{esc(title)}</title><!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->'
            '<style>body,p,li,td{font-family:Cambria,Georgia,serif;font-size:11pt;line-height:1.35;color:#17130f}'
            'h1,h2,h3{font-family:Cambria,Georgia,serif;font-weight:normal;color:#8c1912}h1{font-size:20pt}h2{font-size:14pt}'
            'p.note{font-size:9pt}td,th{border:1px solid #e4dcd0;padding:3pt 5pt;font-size:9pt;vertical-align:top}table{border-collapse:collapse}'
            '.pb{page-break-before:always}</style></head><body>'
            f'<p style="color:#8b7f72;font-size:9pt">RUBICON COMBINED REPORT</p><h1>{esc(title)}</h1>'
            f'<p style="color:#8b7f72;font-size:9pt">{n} questions · {esc(date)}</p>{about(parts, documents)}'
            f'<h2>The questions</h2><ol>{index}</ol><div class="pb"></div>{body}<h1 class="pb">{RR.ANNEXES}</h1>{annexes}</body></html>')


BINDER_CSS = """
.about p { margin: 0; font-size: .95rem; }
.contents ol { padding-left: 1.4rem; display: grid; gap: .7rem; margin: .6rem 0 0; }
.contents li a { font-family: var(--serif); font-size: 1.1rem; color: var(--ink); }
.contents .qanswer { display: block; color: var(--quiet); font-size: .92rem; margin-top: .15rem; }
.contents .small { display: block; }
.contents .small a, .part > .small a, .part-annex > .small a { color: var(--red); }
.part { display: grid; gap: .8rem; padding-top: 2rem; border-top: 2px solid var(--red); }
.part-title { font-size: clamp(1.4rem, 3.6vw, 1.9rem); margin: 0; }
.part .answer h2 { font-size: 1.25rem; }
.contents h2 { margin: 0; }
.part-annex { padding-top: 1.4rem; border-top: 1px solid var(--line); }
.part-annex > p.eyebrow { font-family: var(--sans); font-size: .75rem; }
"""


def default_title(headings):
    """The title a combined report takes when the evaluator gives none: its parts' own headings, the first three in turn
    and a count of the rest. Never the folder's name, which is the file system's word for the work rather than the reader's."""
    shown = [h.strip() for h in headings if h.strip()][:3]
    rest = len([h for h in headings if h.strip()]) - len(shown)
    return " · ".join(shown) + (f" · and {rest} more question{'s' if rest > 1 else ''}" if rest > 0 else "")


def name_for(title, fingerprints):
    words, slug = re.findall(r"[a-z0-9]+", re.sub(r"['’]", "", title.lower())), ""
    for w in words:
        if len(slug) + len(w) > 50:
            break
        slug = f"{slug}-{w}" if slug else w
    mark = hashlib.sha256("\n".join(fingerprints).encode("ascii")).hexdigest()[:8]
    return f"combined-report-{slug or 'rubicon'}-{datetime.date.today().isoformat()}-{mark}"


def main(argv):
    opt = lambda flag: argv[argv.index(flag) + 1] if flag in argv else None
    named = [Path(a) for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in
                                                                                   ("--title", "--date", "--out", "--folder"))]
    left_out = []
    if opt("--folder"):
        folder = Path(opt("--folder")).resolve()
        chosen = latest(register.runs_in(folder))
        reports = [r for r, run in chosen if "fault" not in run and "unsealed" not in run]
        left_out = [(r, run.get("fault") or run["unsealed"]) for r, run in chosen if "fault" in run or "unsealed" in run]
    else:
        reports = [p.resolve() for p in named]
    for report in list(reports):
        why = refused(report)
        if why:
            reports.remove(report)
            left_out.append((report, why))
    if left_out:
        print("Left out of the combined report:\n" + "\n".join(f"- {r.name}: {why}" for r, why in left_out))
        if not opt("--folder"):
            sys.exit("No combined report is drawn: every report named has to be combined, so draw or recount those again first, "
                     "or leave them out.")
    if len(reports) < 2:
        sys.exit(f"No combined report is drawn: it combines two or more reports, and {len(reports)} could be combined.")
    parts = [part(k, r) for k, r in enumerate(reports, 1)]
    run_folders = [p["report"].parent for p in parts]
    folders = list(dict.fromkeys(f.parent for f in run_folders))  # each documents folder, the one holding corpus/
    # The folders by name alone: a combined report is sent on, and a whole path can carry the user's name
    documents = [f.name for f in folders]
    title = opt("--title") or default_title([p["heading"] for p in parts])
    date = opt("--date") or f"{datetime.date.today().day} {datetime.date.today():%B %Y}"
    out = Path(opt("--out")).resolve() if opt("--out") else folders[0]
    name = name_for(title, [p["R"]["fingerprint"] for p in parts])
    (out / f"{name}.html").write_text(binder_html(parts, title, date, documents), encoding="utf-8")
    (out / f"{name}.doc").write_text(binder_word(parts, title, date, documents), encoding="utf-8")
    print(f"wrote {name}.html and {name}.doc in {out}, binding:\n"
          + "\n".join(f"{p['k']}. {p['heading']} ({p['report'].name})" for p in parts))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
