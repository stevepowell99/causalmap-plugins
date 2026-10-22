"""Combine the reports of several Rubicon runs into one combined report: a cover, the questions with their short answers, each answer in
turn, and every run's annex gathered at the end, as a page to read and click through and the same for Word.

    python bind.py <report .html> <report .html> [...] [--title "..."] [--date "9 October 2026"] [--out <folder>]
    python bind.py --folder <documents folder> [the same options]
    ... [--question <report>] [--shared <report>] [--background <report>]

Given reports, it combines them in the order given; given a documents folder, it combines every run listed in its
`rubicon-runs.md` or lying in one of its run folders (`register.runs_in`), each at its latest revision, in the order the
runs were answered. A combined report re-derives nothing. Each part is drawn by `render_report.py`'s own functions from that
run's sealed zip and from nothing else, and a run is refused, and named, when its report does not name its zip, its
zip's seal is broken, or a fresh recount of its coded rows and answer would change its counts (`render_report.problems`),
so every number and quotation in the combined report is one its run's report already carries and can be checked as it can.
Each part names the run it came from: its ID, its zip and fingerprint, and the chat that first recounted it where the
run recorded one.

A part is a question, shared material or background, and what the evaluator agreed says which, never a guess from a run's
name. Where `rubicon-plan.md` beside the documents lists a run (`rubicon_open/plan.py` says how the plan is read), the plan
gives its role and the parts come in its order; `--question`, `--shared` or `--background` before a report names its role
instead, and adds the report to those named where it is not already, in the place it is given. A run the plan does not list
is left out of a `--folder` report, and named in the output, and comes after the listed ones where its report was named.
Where neither says, a run is a question if its answer holds prose and shared material if not (`answers_a_question`).
Shared material and background come before the questions, in the first annexes. A background run is a run with an answer
that is context for the chapter rather than one of its questions: it is titled as background, not counted or numbered
as a question, and its answer is drawn at the head of its annex, beside the shared material.

What the parts share is shown once, in the first annex that has it, and the annexes after it say where it is
(`gather`): a coding step or counting table that shows the same instruction, codebook, passages or cells, the
"every interview at a glance" matrix, the list of documents read, the method and how to check the record. The documents
themselves are packed once for the parts that read the same ones (`share_texts`), and every part's citations open them
there. A run that answers no question (its answer holds no prose: `answers_a_question`) is made to hold steps other runs
share. It is not counted, titled or drawn as a question: it comes first among the annexes, where the questions' annexes
point to what it shows.
What differs stays in its own annex: each part's steps that are its own, its checks, its record and its revisions.

It also warns whoever writes the combined report, in its output and in a `-checks.txt` file beside it, where a value is
counted out of different totals or in different units by tables counted out of their own base, or a column or code has
different words in two parts (`differences`), and says how many values and definitions it compared. The report carries
one line saying the questions were checked and how much was compared, and no list. The warnings read only what each
part's record already holds, and they are warnings: the parts are bound all the same.

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
from rubicon_open import console  # noqa: E402
from rubicon_open import assets, footprint, plan
from rubicon_open.run_id import clean as run_id_of
from rubicon_open.seal import engine_fingerprint
from rubicon_open.steps import base_of, unit_of_table

ENGINE = Path(__file__).resolve().parent
COUNT_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
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


def answers_a_question(answer, workflow):
    """Whether a run answers a question, from what it records: its answer holds prose, more than headings and blanks, and
    it either has a step that writes the answer or an agreed question. A run made to hold the steps other runs share
    has neither, and is shared material in a combined report rather than a question in it."""
    prose = [l for l in answer.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    wrote = any(st.get("kind") == "write" for st in workflow.get("steps", []))
    return bool(prose) and (wrote or bool(workflow.get("question_as_agreed", "").strip()))


def identity(report):
    """What a report's zip says of its run before the whole report is drawn: its run ID, its fingerprint, and whether its
    answer is a question's (`answers_a_question`)."""
    with zipfile.ZipFile(report.with_suffix(".zip")) as z:
        answer = z.read("answer.md").decode("utf-8") if "answer.md" in z.namelist() else ""
        workflow = json.loads(z.read("workflow.json").decode("utf-8"))
        return {"run_id": run_id_of(workflow.get("run_id")), "fingerprint": hashlib.sha256(z.read("SHA256SUMS")).hexdigest(),
                "asks": answers_a_question(answer, workflow)}


def asks(report):
    """`answers_a_question` for a report, read from its zip before the whole report is drawn."""
    return identity(report)["asks"]


def part(k, report, role=None):
    """One run as the combined report draws it: its answer, interactive and for Word, and what names it. Its annex is
    drawn by `gather`, once the parts it shares with are known. A run that answers no question has no answer drawn.
    `role` is `question`, `shared` or `background` (`ROLES`); without one the answer says (`answers_a_question`). A
    question and a background run have an answer to draw, so a run that has none cannot be either; a shared run has its
    answer left out, so one that has an answer cannot be shared. Either is refused, and named."""
    zipped = report.with_suffix(".zip")
    R = RR.load(zipped)
    if R["engine"] != engine_fingerprint(ENGINE):
        print(f"{report.name} was created by another engine (Rubicon {R['version'] or 'of unknown version'}), so its part "
              "here may differ from that report.")
    D = RR.build_data(R)
    answers = answers_a_question(R["answer"], R["workflow"])
    role = role or ("question" if answers else "shared")
    if role not in ROLES:
        sys.exit(f"No combined report is created: {report.name} is given the role {role!r}, which is one of {', '.join(ROLES)}.")
    if role != "shared" and not answers:
        sys.exit(f"No combined report is created: {report.name} is a {role} but its answer holds no prose to show; "
                 "it is shared material if it only holds steps for the others to take.")
    if role == "shared" and answers:
        sys.exit(f"No combined report is created: {report.name} is shared material but its answer holds prose, which would be "
                 "left out; it is a question, or background to the questions.")
    if role == "shared":
        empty = {"title": "", "lead": "", "body": "", "facts": "", "matrix": RR.matrix(R, D), "data": D}
        S = RR.build_data(R)
        return {"k": k, "asks": False, "role": role, "R": R, "D": D, "S": S, "report": report, "heading": SHARED,
                "page": {n: scoped(v, k) if isinstance(v, str) else v for n, v in empty.items()},
                "word": {"lead": "", "body": "", "notes": ""}}
    title, lead, body, _ = RR.answer_html(R, D)
    if R["unfilled"]:
        sys.exit(f"No combined report is created: {report.name} writes " + ", ".join("{" + u + "}" for u in R["unfilled"])
                 + ", which no count in its run is called.")
    figures_left = sorted(set(R.get("missing_figures", []) + R.get("wide_figures", [])))
    if figures_left:
        print(f"{report.name}: figure lines left out, as in its own report: {', '.join(figures_left)}")
    page = {"title": title, "lead": lead, "body": body, "facts": RR.facts(R, D), "matrix": RR.matrix(R, D), "data": D}
    S = RR.build_data(R)
    S["note_prefix"] = f"p{k}x"  # one footnote id for each part's note, so no two parts' notes share one
    stitle, slead, sbody, cite_no = RR.answer_html(R, S, static=True)
    word = {"lead": slead, "body": sbody, "notes": cite_no.listed("h3")}
    said = RR.heading(R, title)
    return {"k": k, "asks": role == "question", "role": role, "R": R, "D": D, "S": S, "report": report,
            "heading": f"{BACKGROUND}: {said}" if role == "background" else said,
            "page": {n: scoped(v, k) if isinstance(v, str) else v for n, v in page.items()}, "word": word}


GLANCE = "<h3>Every interview at a glance</h3>"
SHARED = "Steps the questions share"
BACKGROUND = "Background"
ROLES = plan.ROLES


def number(parts):
    """Gives each part that answers a question its number among the questions (`q`), and each that does not, None."""
    n = 0
    for p in parts:
        n += p["asks"]
        p["q"] = n if p["asks"] else None


def gather(parts):
    """Draws each part's annex, in order, with what an earlier annex already shows left out and pointed to (`annex_keys`
    says what can be shared). Done once the parts are known, since what a part shares depends on the parts before it;
    saying it twice does nothing."""
    number(parts)
    earlier = {}
    for p in parts:
        k, R = p["k"], p["R"]
        if "annex" not in p["page"]:
            shown = lambda inner, static: f"<h3>{RR.HOW_DONE}</h3>" + RR.how_done(R, static=static) + inner
            p["page"]["annex"] = scoped(shown(RR.annex(R, p["D"], earlier=earlier, number=k), False), k)
            p["word"]["annex"] = shown(RR.annex(R, p["S"], static=True, earlier=earlier, number=k), True)
            matrix = p["page"]["matrix"]
            same = earlier.get(RR.hashed("glance", matrix))
            p["page"]["glance"] = "" if not matrix else GLANCE + (
                f'<p class="small shared">The same as in <a href="#annex-{same[0]}">Annex {same[0]}</a>.</p>' if same
                else '<p class="small">Each row is one interview, each column a reason as the coding defines it. '
                     'Click a mark to read the passages.</p>' + matrix)
        for key, sid in RR.annex_keys(R).items():
            earlier.setdefault(key, (k, sid))
        if p["page"]["matrix"]:
            earlier.setdefault(RR.hashed("glance", p["page"]["matrix"]), (k, None))


def background(p, static=False):
    """A background run's answer, drawn at the head of its annex, where the shared material is, since it is context for
    the questions and not one of them; nothing for any other part."""
    if p["role"] != "background":
        return ""
    if static:
        return RR.asked(p["R"], static=True) + p["word"]["lead"] + p["word"]["body"]
    return (f'{RR.asked(p["R"])}<div class="lead">{p["page"]["lead"]}</div>{p["page"]["facts"]}'
            f'<article class="answer">{p["page"]["body"]}</article>')


def basis(tab, cell):
    """What a count is out of, in words: "out of 15 households", or "as passages" where it counts passages."""
    base = base_of(tab, cell)
    return f"out of {base} {unit_of_table(tab)}" if base is not None else f"as {unit_of_table(tab)}"


def questions(ks):
    return ("question " if len(ks) == 1 else "questions ") + ", ".join(map(str, ks))


def own_base(R, st, tab):
    """Whether a table's cells are counted out of their own stated base. Not so in a table of paths, told chains or loops,
    whose total is the households that have the path, nor in a cross-tab by a document attribute (sex, province) with
    something else, whose total is the size of the group: those totals differ by design and say nothing of the value."""
    attributes = {key for d in R["index"] for key in d}
    return not (tab.get("paths") or tab.get("sequences") or tab.get("loops")
                or (len(st.get("by", [])) > 1 and any(c in attributes for c in st.get("by", []))))


def compared(parts):
    """Every value counted and every column and code defined across the parts, each with the places that say it, and how
    many tables and cells were read: what `differences` and `findings` both read, so they cannot disagree. A value (a
    column and one of its values, or the total of documents) maps to each total or unit it is counted on, counting only
    cells counted out of their own base (`own_base`); a column, or a code in its codebook, maps to each wording it is
    given. Only what each part's record already holds is read: its tables' cells and its workflow's columns."""
    counted, defined, tables, cells = {}, {}, 0, 0
    for p in parts:
        k, R = p.get("q", p["k"]) or 0, p["R"]  # the question's number, or 0 for shared steps
        for st in R["workflow"]["steps"]:
            tab = R["steps"].get(st["id"], {})
            if st.get("kind") == "tabulate" and own_base(R, st, tab):
                tables += 1
                for cell in tab.get("cells", []):
                    cells += 1
                    for c, v in (cell.get("values") or {"": ""}).items():
                        counted.setdefault((str(c), str(v)), {}).setdefault(basis(tab, cell), set()).add((k, st["id"]))
            for col in st.get("columns", []) if st.get("kind") == "code" else []:
                told = lambda x: " | ".join(str(x.get(f) or "") for f in ("means", "counts", "does_not_count", "weak"))
                defined.setdefault((col["name"], None), {}).setdefault(told(col), set()).add((k, st["id"]))
                for v in col.get("values") or []:
                    defined.setdefault((col["name"], v["name"]), {}).setdefault(told(v), set()).add((k, st["id"]))
    return counted, defined, tables, cells


def differs(told):
    """Whether a column or code is given different words in more than one part."""
    return len(told) > 1 and len({k for held in told.values() for k, _ in held}) > 1


def listed(items):
    """Words as a list in a sentence: "a", "a and b", "a, b and c"."""
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def named(ks):
    """The parts a finding is about, as a reader names them: "question 2", or "the shared steps"."""
    return listed(("the shared steps" if k == 0 else f"question {k}") for k in sorted(ks))


def findings(parts):
    """What the reader of a combined report is told where the questions do not line up, as two lists of plain sentences:
    the columns defined in different words, and the values counted out of different totals. A line is not repeated for
    each table or column: columns defined in different words in the same parts are one line, and values counted out of the
    same totals in the same parts are one line, naming their columns. Empty where nothing differs."""
    counted, defined, _, _ = compared(parts)
    columns = {}
    for (col, value), told in defined.items():
        if differs(told):
            group = columns.setdefault(col, {"parts": set(), "codes": set()})
            group["parts"] |= {k for held in told.values() for k, _ in held}
            if value is not None:
                group["codes"].add(RR.label(value))
    by_parts = {}
    for col, g in columns.items():
        by_parts.setdefault((tuple(sorted(g["parts"])), tuple(sorted(g["codes"]))), []).append(RR.label(col))
    defs = [(f'The column "{cols[0]}" is' if len(cols) == 1 else f"The columns {listed(chr(34) + c + chr(34) for c in sorted(cols))} are")
            + f" defined in different words in {named(ks)}" + (f" (the codes that differ: {listed(codes)})" if codes else "") + "."
            for (ks, codes), cols in by_parts.items()]
    grouped = {}
    for (c, v), bases in counted.items():
        if len(bases) > 1:
            totals = tuple(sorted((b, tuple(sorted({k for k, _ in held}))) for b, held in bases.items()))
            grouped.setdefault(totals, {}).setdefault(c, set()).add(v)
    counts = []
    for totals, by_column in grouped.items():
        said = " but ".join(f"{b} in {named(ks)}" for b, ks in totals) if len(totals) == 2 else             listed(f"{b} in {named(ks)}" for b, ks in totals)
        if "" in by_column:
            counts.append(f"The total of documents is counted {said}.")
        same_values = {}
        for c, vs in by_column.items():
            if c:
                same_values.setdefault(frozenset(vs), []).append(RR.label(c))
        counts += [f"{listed(sorted(cols))}: {listed(sorted(RR.label(v) for v in vs))} {'is' if len(vs) == 1 else 'are'} counted {said}."
                   for vs, cols in same_values.items()]
    return defs, counts


def differences(parts):
    """What to warn the writer of a combined report about, as plain sentences, and what was looked at, so that no
    warnings can be told from nothing looked at. A value (a column and one of its values, or the total of documents) is
    counted on different terms where its tables, in any parts, give it different totals (the `of`) or units, counting
    only cells counted out of their own base (`own_base`); and a column, or a code in its codebook, is defined
    differently where two parts give the same name different words (what it means, counts, does not count, or what is
    implicit). Only what each part's record already holds is read: its tables' cells and its workflow's columns."""
    counted, defined, tables, cells = compared(parts)
    specs = {}
    for p in parts:  # each question's steps, so that a step is named as the report names it
        specs.setdefault(p.get("q", p["k"]) or 0, {}).update(RR.specs_of(p["R"]["workflow"]))
    def where(held, most=3):
        places = sorted(held)
        shown = ", ".join(f"{RR.step_name(sid, specs.get(k, {}))} ({questions([k]) if k else 'shared steps'})" for k, sid in places[:most])
        return shown + (f" and {len(places) - most} more" if len(places) > most else "")
    out = []
    for (c, v), bases in counted.items():
        if len(bases) > 1:
            name = f"{RR.label(c)}: {RR.label(v)}" if c else "The total of documents"
            out.append(f"{name} is counted " + " but ".join(f"{b} in {where(held)}" for b, held in sorted(bases.items())) + ".")
    for (col, value), told in defined.items():
        if differs(told):
            name = f"{RR.label(col)}: {RR.label(value)}" if value is not None else f"The column {RR.label(col)}"
            out.append(f"{name} is defined differently in " + " and in ".join(where(held) for held in sorted(told.values(), key=min)) + ".")
    looked = (f"Compared {len(counted)} values counted in {cells} cells of {tables} tables and {len(defined)} column and code "
              f"definitions across {len(parts)} questions.")
    return out, looked


def checks_file(out, looked):
    """What `differences` found, for whoever writes and checks the combined report: its counts, then a line for each place."""
    return f"{looked} Found {len(out)} where the questions count or define the same thing differently.\n" + "".join(f"- {d}\n" for d in out)


def note_on(looked, found=((), ()), static=False):
    """The note at the head of the annexes: one line saying the questions were checked and how much was compared, and,
    where `findings` has any, a short list in plain words of the columns defined in different words and the values
    counted out of different totals, for a reader setting numbers from different questions side by side. Nothing but the
    line where nothing differs."""
    line = "Checked for differences between the questions. " + RR.esc(looked)
    items = [*found[0], *found[1]]
    small = "" if static else ' class="small"'
    more = (f"<p{small}>Read these before setting numbers from different questions side by side:</p><ul{small}>"
            + "".join(f"<li>{RR.esc(i)}</li>" for i in items) + "</ul>") if items else ""
    return f"<p>{line}</p>{more}" if static else f'<p class="small" id="annex-differences">{line}</p>{more}'


def share_texts(parts):
    """The documents of every part, packed (`render_report.pack_texts`) once for the parts that read the same ones: a list
    of packed sets, and for each part the set to read its documents from. A part joins the first set whose documents
    agree with its own wherever a document has the same id, and a set is not grown past what a report carries
    (`TEXTS_CARRIED`); a part with too many documents to carry reads them from its run's zip, as in its own report."""
    sets = []
    for i, p in enumerate(parts):
        own = p["R"]["texts"]
        for held in sets:
            joined = {**held["texts"], **own}
            if all(held["texts"].get(d, t) == t for d, t in own.items()) and sum(map(len, joined.values())) <= RR.TEXTS_CARRIED:
                held["texts"] = joined
                held["of"].append(i)
                break
        else:
            sets.append({"texts": dict(own), "of": [i]})
    return [RR.pack_texts(held["texts"]) for held in sets], [next(j for j, held in enumerate(sets) if i in held["of"]) for i in range(len(parts))]


#: A group of citations as `render_report.inline` draws one, and a finding's Evidence button: left out of the index
CHIPS = re.compile(r'\s*\((?:<button class="cite[^"]*"[^>]*>.*?</button>(?:<template[^>]*>.*?</template>)?(?:, |; )?)+\)'
                   r'|<button class="based"[^>]*>.*?</button>', re.S)


def plain(markup):
    """A short answer as the index gives it: its words, without the citations its part carries, and as the words
    themselves (an apostrophe is not `&#x27;`), since the caller escapes them again where it writes them."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", CHIPS.sub("", markup)))).strip()


def provenance(p, static=False):
    """Which report a part was handed over as; its run ID, zip and fingerprint follow under "The record" in its
    annex, as in its own report."""
    return f'<p class="small">Handed over as {RR.esc(p["report"].name)}.</p>'


def about(parts):
    """The cover's opening, for a reader who has never met Rubicon: what the report answers, from how many documents,
    that each answer stands alone, where the numbers and quotations come from, and where the method is. It names no
    folder and uses none of the engine's own words (run, zip, seal, recount, coded), which the annexes keep."""
    held = {}
    for p in parts:  # the documents each documents folder holds, counted once however many of its questions are answered
        run_folder = p["report"].parent
        folder = run_folder.parent
        held[folder] = max(held.get(folder, 0), len(p["R"]["index"]))
    n = sum(p["asks"] for p in parts)
    return (f"<p>This report answers {COUNT_WORDS.get(n, n)} question{'' if n == 1 else 's'} from {sum(held.values())} documents. Each answer was "
            "reached and checked separately. Its numbers were counted from what people said in the documents rather than "
            "estimated by the AI, and every quotation is word for word. How each answer was reached is set out in the "
            "annexes at the end.</p>")


def binder_html(parts, title, date):
    gather(parts)
    esc, n, total = RR.esc, sum(p["asks"] for p in parts), len(parts)
    asked = [(i, p) for i, p in enumerate(parts) if p["asks"]]
    css = (ENGINE / "report.css").read_text(encoding="utf-8") + BINDER_CSS
    js = RR.report_js()
    index = "".join(
        f'<li><a href="#q-{p["k"]}">{esc(p["heading"])}</a>'
        + (f'<span class="qanswer">{esc(plain(p["page"]["lead"]))}</span>' if p["page"]["lead"] else "")
        + f'<span class="small">{"Run " + esc(p["R"]["run_id"]) + " · " if p["R"].get("run_id") else ""}'
          f'<a href="#annex-{p["k"]}">annex</a></span></li>' for _, p in asked)
    sections = "".join(f"""
<section class="part" id="q-{p["k"]}" data-run="{i}">
  <p class="eyebrow">Question {p["q"]} of {n}</p>
  <h2 class="part-title">{esc(p["heading"])}</h2>
  {RR.asked(p["R"])}
  {RR.synthetic(p["R"])}
  <div class="lead">{p["page"]["lead"]}</div>
  {p["page"]["facts"]}
  <article class="answer">{p["page"]["body"]}</article>
  <p class="small"><a href="#annex-{p["k"]}">Annex {p["k"]}: how this answer was reached</a> · <a href="#contents">The questions</a></p>
</section>""" for i, p in asked)
    annexes = RR.annexes(note_on(differences(parts)[1], findings(parts)) + "".join(f"""
<section class="annex part-annex" id="annex-{p["k"]}" data-run="{i}">
  <p class="eyebrow">Annex {p["k"]} of {total}</p>
  <h2 class="part-title">{esc(p["heading"])}</h2>
  {provenance(p)}
  {background(p)}
  {p["page"]["annex"]}
  {p["page"]["glance"]}
  {f'<p class="small"><a href="#q-{p["k"]}">Back to question {p["q"]}</a></p>' if p["asks"] else ""}
</section>""" for i, p in enumerate(parts)))
    toc = RR.contents([("contents", "The questions")] + [(f'q-{p["k"]}', p["heading"]) for _, p in asked], annexes)
    packed, held_in = share_texts(parts)
    data = json.dumps([{"data": p["page"]["data"], "texts": held_in[i]} for i, p in enumerate(parts)],
                      ensure_ascii=False).replace("</", "<\\/")
    texts = json.dumps(packed).replace("</", "<\\/")
    dots = any('<pre class="dot"' in p["page"]["body"] for _, p in asked)
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{assets.fonts_css()}{css}</style></head><body><div class="wrap">
{toc}
<main>
<header class="cover">
  <p class="eyebrow">{RR.site_link("Rubicon combined report")}</p>
  <h1>{esc(title)}</h1>
  <p class="meta">{n} question{"" if n == 1 else "s"} · {esc(date)}</p>
  <div class="about">{about(parts)}</div>
</header>
<nav class="contents" id="contents"><h2>The questions</h2><ol>{index}</ol></nav>
{sections}
{annexes}
{RR.carbon_line(footprint.combined([p["R"]["footprint"] for p in parts]), combined=True)}
{RR.made_with()}
</main>
<aside class="panel" id="panel" hidden><button class="close" id="panel-close" aria-label="Close">×</button><div id="panel-body"></div></aside>
</div>
<script>var TEXTSETS = {texts}; var PARTS = {data}; var RUN = PARTS[0].data, TEXTS = TEXTSETS[PARTS[0].texts], SCOPE = '[data-run="0"]';
// Whatever is clicked inside a part makes that part's run the one report.js reads; the panel keeps the last one
document.addEventListener('click', e => {{
  const p = e.target.closest('[data-run]');
  if (p) {{ const x = PARTS[+p.dataset.run]; RUN = x.data; TEXTS = TEXTSETS[x.texts]; SCOPE = `[data-run="${{p.dataset.run}}"]`; }}
}}, true);</script>
{assets.graphviz_script() if dots else ""}<script>{js}</script>
</body></html>"""


def binder_word(parts, title, date):
    gather(parts)
    esc, n = RR.esc, sum(p["asks"] for p in parts)
    index = "".join(f'<li>{esc(p["heading"])}{": " + esc(plain(p["page"]["lead"])) if p["page"]["lead"] else ""}</li>' for p in parts if p["asks"])
    body = "".join(
        f'<h2>Question {p["q"]} of {n}: {esc(p["heading"])}</h2>{RR.asked(p["R"], static=True)}{RR.synthetic(p["R"])}'
        f'{p["word"]["lead"]}{p["word"]["body"]}' for p in parts if p["asks"])
    annexes = "".join(
        f'<h2>Annex {p["k"]}: {esc(p["heading"])}</h2>{provenance(p, static=True)}{background(p, static=True)}{p["word"]["annex"]}'
        + (p["word"]["notes"] if p["role"] != "shared" else "") for p in parts)
    return ('<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" '
            'xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8">'
            f'<title>{esc(title)}</title><!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->'
            '<style>body,p,li,td{font-family:Cambria,Georgia,serif;font-size:11pt;line-height:1.35;color:#17130f}'
            'h1,h2,h3{font-family:Cambria,Georgia,serif;font-weight:normal;color:#8c1912}h1{font-size:20pt}h2{font-size:14pt}'
            'p.MsoFootnoteText{font-size:9pt;line-height:1.2}.MsoFootnoteReference{vertical-align:super}td,th{border:1px solid #e4dcd0;padding:3pt 5pt;font-size:9pt;vertical-align:top}table{border-collapse:collapse}'
            '.pb{page-break-before:always}</style></head><body>'
            f'<p style="color:#8b7f72;font-size:9pt">RUBICON COMBINED REPORT</p><h1>{esc(title)}</h1>'
            f'<p style="color:#8b7f72;font-size:9pt">{n} question{"" if n == 1 else "s"} · {esc(date)}</p>{about(parts)}'
            f'<h2>The questions</h2><ol>{index}</ol><div class="pb"></div>{body}<h1 class="pb">{RR.ANNEXES}</h1>{note_on(differences(parts)[1], findings(parts), static=True)}{annexes}'
            f'{RR.carbon_line(footprint.combined([p["R"]["footprint"] for p in parts]), combined=True, static=True)}{RR.made_with()}</body></html>')


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


def command_line(argv):
    """The reports named on the command line, in order, and the role given to any of them by `--question`, `--shared` or
    `--background` before it."""
    named, explicit, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--title", "--date", "--out", "--folder"):
            i += 2
        elif a in ROLE_FLAGS:
            if i + 1 >= len(argv):
                sys.exit(f"{a} needs the report it gives the role to.")
            named.append(Path(argv[i + 1]).resolve())
            explicit[named[-1]] = ROLE_FLAGS[a]
            i += 2
        else:
            if not a.startswith("--"):
                named.append(Path(a).resolve())
            i += 1
    return named, explicit


ROLE_FLAGS = {f"--{r}": r for r in ROLES}


def main(argv):
    opt = lambda flag: argv[argv.index(flag) + 1] if flag in argv else None
    named, explicit = command_line(argv)
    left_out = []
    if opt("--folder"):
        folder = Path(opt("--folder")).resolve()
        chosen = latest(register.runs_in(folder))
        reports = [r for r, run in chosen if "fault" not in run and "unsealed" not in run]
        left_out = [(r, run.get("fault") or run["unsealed"]) for r, run in chosen if "fault" in run or "unsealed" in run]
        reports += [r for r in named if r not in reports]  # a report named with a role is bound, discovered or not
    else:
        reports = list(dict.fromkeys(named))
    for report in list(reports):
        why = refused(report)
        if why:
            reports.remove(report)
            left_out.append((report, why))
    # each run's role and place: the plan beside its documents lists it, or the command line names it, or its answer says
    plans, info, place = {}, {}, {}
    for n, report in enumerate(reports):
        info[report] = identity(report)
        run_folder = report.parent  # the run's folder, inside the documents folder that holds corpus/ and the plan
        documents = run_folder.parent
        listed = plans.setdefault(documents, plan.read(documents))
        row = plan.entry_for(listed, info[report]["run_id"], info[report]["fingerprint"])
        if report not in explicit:
            if row and row["role"] is None:
                sys.exit(f"No combined report is created: the plan's row {row['label']!r} names the run of {report.name} but gives it no role. "
                         f"Give rubicon-plan.md a Role column (question, shared or background), or name the report with "
                         f"--question, --shared or --background.")
            if opt("--folder") and listed and not row:
                left_out.append((report, "no row of rubicon-plan.md names its run; add one, or name it with --question, --shared or --background"))
                continue
            explicit[report] = row["role"] if row else None
        place[report] = (0, listed.index(row)) if row else (1, n)
    reports = [r for r in reports if r in place]
    if left_out:
        print("Left out of the combined report:\n" + "\n".join(f"- {r.name}: {why}" for r, why in left_out))
        if not opt("--folder"):
            sys.exit("No combined report is created: every report named has to be combined, so create or recount those again first, "
                     "or leave them out.")
    if len(reports) < 2:
        sys.exit(f"No combined report is created: it combines two or more reports, and {len(reports)} could be combined.")
    # shared material and background first, since the annexes after them point to what they show; then the questions
    reports.sort(key=lambda r: ((explicit[r] or ("question" if info[r]["asks"] else "shared")) == "question", place[r]))
    parts = [part(k, r, explicit[r]) for k, r in enumerate(reports, 1)]
    if not any(p["asks"] for p in parts):
        sys.exit("No combined report is created: none of the runs is a question.")
    number(parts)
    warned, looked = differences(parts)
    run_folders = [p["report"].parent for p in parts]
    folders = list(dict.fromkeys(f.parent for f in run_folders))  # each documents folder, the one holding corpus/
    title = opt("--title") or default_title([p["heading"] for p in parts if p["asks"]])
    date = opt("--date") or f"{datetime.date.today().day} {datetime.date.today():%B %Y}"
    out = Path(opt("--out")).resolve() if opt("--out") else folders[0]
    name = name_for(title, [p["R"]["fingerprint"] for p in parts])
    (out / f"{name}.html").write_text(binder_html(parts, title, date), encoding="utf-8", newline="\n")
    (out / f"{name}.doc").write_text(binder_word(parts, title, date), encoding="utf-8", newline="\n")
    (out / f"{name}-checks.txt").write_text(checks_file(warned, looked), encoding="utf-8", newline="\n")
    print(checks_file(warned, looked).split("\n")[0])
    for warning in warned:
        print(f"Warning: {warning}")
    print(f"wrote {name}.html, {name}.doc and {name}-checks.txt in {out}, binding:\n"
          + "\n".join(f"{p['q'] or p['role']}. {p['heading']} ({p['report'].name})" for p in parts))


if __name__ == "__main__":
    console.utf8()
    main(sys.argv[1:])
