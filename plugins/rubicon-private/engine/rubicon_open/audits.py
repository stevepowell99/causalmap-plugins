"""Checks on an answer and its coding that code can make without a model: warnings for the writer and the check to
weigh against the documents, never refusals.

    speakers      a quotation cited in the answer is the respondent's words, not the interviewer's
    word cuts     a quotation starts and ends on a word boundary in its document, where the document's text marks one
    coverage      which documents the answer never cites or names, and which groups of documents no citation comes from
    code values   a value a code step's nominal column allows that no passage was coded with, or that rests on one case

Two checks are not run by code, and say so: whether a word of quantity beside a count agrees with it ("most" beside 4
of 12), and whether the answer gives a participant a gender their own words do not. Each turns on what a sentence's
words mean, in whatever language the answer is written, so a model reads it as its reader would; a list of one
language's words would pass every answer in another without having looked (`rubicon/CLAUDE.md`, "Quality levers never
depend on English").

The pure checks take plain data (offsets, texts, counts), so the private harness calls them on its own records
(`rubicon/rubicon/coordinator/audits.py`) and a recount calls them on an open run (`audit_run`). Each check says how
many things it looked at, so an empty list of findings reads as "looked and found nothing", never as "did not look",
and one that could not look says "not run" and why.

Two checks of the harness's audit are not here because the open record does not hold what they read: a quotation read
both as saying an item and as denying it (a coded passage carries no status, and one passage may properly sit in two
rows with different values), and a codebook built from few documents or never piloted (a group step records neither
which documents built the codebook nor a pilot).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from functools import cache

from . import locator
from . import steps as S
from . import text as T
from .workflow import value_key

#: The checks code does not make, and why: what a sentence's words mean is read by a model, in any language.
NOT_RUN = {
    "quantifiers": "whether a word for how many agrees with the count beside it is read by a model, in the answer's own "
                   "language, not by fixed rules",
    "person_words": "whether the answer gives a participant a gender their own words do not is read by a model, in the "
                    "answer's own language, not by fixed rules",
}
#: A quotation in the answer, whose words are the speaker's and not the answer's.
QUOTED = T.QUOTATION


def not_run(name: str) -> dict:
    """A check code does not make (`NOT_RUN`), recorded as not run rather than left out, so nobody reads its absence
    as a pass."""
    return {"not_run": NOT_RUN[name]}


@cache
def _speaker() -> re.Pattern:
    """A turn's label in a transcript, in any script: `Interviewer:`, `User:`, `R2:`, `受访者：`. It opens with a letter
    that is not lowercase (a capital, or a letter of a script without case) and runs to a colon, a full-width one too,
    with any space before it, the no-break space French sets there included."""
    w = T.word_pattern()
    return re.compile(rf"^[^\S\r\n]*((?:{w})(?:{w}|[ .'’\-]){{0,30}}?)[^\S\r\n]*[:：][^\S\r\n]*(?=\S)", re.M)


def turns(text: str) -> list[tuple[int, str]]:
    """Where each turn of a transcript starts, with its speaker's label."""
    return [(m.start(), m.group(1).strip()) for m in _speaker().finditer(text)
            if unicodedata.category(m.group(1)[0]) != "Ll"]


#: Most labels a transcript of one respondent has: the respondent's, and the interviewer's, which one transcript may
#: write two ways ("Assistant:" first, "AI:" after).
INTERVIEW_LABELS = 3


def speaker_at(text: str, offset: int) -> dict | None:
    """Who is speaking at `offset` in a transcript, and whether it is the respondent (whoever first answers the
    opener). None where the document is not a transcript, or has more speakers than an interview of one respondent
    has, such as a focus group, where who speaks first does not say who interviews."""
    turned = turns(text)
    labels = Counter(label for _, label in turned)
    if not 2 <= len({k for k, n in labels.items() if n >= 2}) <= INTERVIEW_LABELS:
        return None
    opener = turned[0][1]
    respondent = next((lab for _, lab in turned if lab != opener), None)
    before = [lab for s, lab in turned if s <= offset]
    if not before:
        return {"speaker": None, "respondent": False}
    return {"speaker": before[-1], "respondent": before[-1] == respondent}


def speakers(cited: list[dict], text_of) -> dict:
    """`cited`: quotations placed in their documents, each {quote, document, at: {start, end}} or `at` None; `text_of`
    gives a document's text, in which `at` is a Python index."""
    findings, looked = [], 0
    for c in cited:
        if not c["at"]:
            continue
        who = speaker_at(text_of(c["document"]), c["at"]["start"])
        if who is None:
            continue
        looked += 1
        if not who["respondent"]:
            findings.append({"document": c["document"], "quote": c["quote"][:100],
                             "problem": f"these are the words of {who['speaker'] or 'the opening'}, "
                                        "not the respondent's"})
    return {"looked_at": looked, "findings": findings}


#: How far either side of a quotation's end the text is read for a space, which says whether it separates its words.
WORD_GAP = 20


def word_cuts(cited: list[dict], text_of) -> dict:
    """Each quotation's start and end, where its document separates words with spaces around it: a script written
    without them, such as Chinese, shows no word boundary to check, so a quotation there is not looked at, and where no
    quotation could be the check says it was not run."""
    findings, looked, unseen = [], 0, 0
    for c in cited:
        if not c["at"]:
            continue
        text, s, e = text_of(c["document"]), c["at"]["start"], c["at"]["end"]
        # a space between words, not a line break, which a text without spaces has too
        spaced = [bool(re.search(r"[^\S\r\n]", text[max(0, i - WORD_GAP):i + WORD_GAP])) for i in (s, e)]
        if not any(spaced):
            unseen += 1
            continue
        looked += 1
        cut_start = spaced[0] and s > 0 and text[s - 1].isalnum() and text[s].isalnum()
        cut_end = spaced[1] and e < len(text) and text[e - 1].isalnum() and text[e].isalnum()
        if cut_start or cut_end:
            findings.append({"document": c["document"], "quote": c["quote"][:100],
                             "problem": "it starts inside a word" if cut_start and not cut_end
                             else "it ends inside a word" if cut_end and not cut_start
                             else "it starts and ends inside words"})
    if unseen and not looked:
        return {"not_run": f"the documents do not separate words with spaces where the {unseen} quotations placed in "
                           "them start and end, so no word boundary shows"}
    return {"looked_at": looked, "findings": findings, **({"not_looked_at": unseen} if unseen else {})}


def _number(v) -> bool:
    try:
        float(str(v).replace(",", ""))
        return True
    except ValueError:
        return False


def coverage(documents: dict[str, dict], columns: list[str], cited_docs: set[str], read: set[str]) -> dict:
    """`documents`: id -> {"columns": {...}}; `cited_docs`: the documents the answer cites; `read`: those logged read."""
    docs = set(documents)
    silent_groups = {}
    for col in columns:
        values = {documents[d]["columns"].get(col) for d in docs} - {None, ""}
        # A group is a category; a column of numbers (a length, a count of turns) is not one.
        if not 1 < len(values) <= 8 or all(_number(v) for v in values):
            continue
        cited_values = {documents[d]["columns"].get(col) for d in cited_docs}
        missing = sorted(values - cited_values)
        if missing and cited_docs:
            silent_groups[col] = missing
    return {"looked_at": len(docs), "documents": len(docs), "read_logged": len(read),
            "cited": len(cited_docs), "never_cited": sorted(docs - cited_docs)[:50],
            "groups_never_cited": silent_groups,
            "findings": [{"problem": f"no quotation comes from {col} {', '.join(v)}"}
                         for col, v in silent_groups.items()]}


def item_use(items: list[tuple[str, str]], used: dict[tuple, set]) -> dict:
    """`items`: (list's name, item) for every item of every codebook or value list; `used`: the cases each was used for."""
    findings = []
    for name, item in items:
        cases = used.get((name, item), set())
        if not cases:
            findings.append({"codebook": name, "item": item, "problem": "never used"})
        elif len(cases) == 1:
            findings.append({"codebook": name, "item": item,
                             "problem": f"rests on one case, {next(iter(cases))}"})
    return {"looked_at": len(items), "findings": findings}


def in_words(got: dict) -> list[str]:
    """One line per check: what it looked at and what it found, or that it was not run and why."""
    out = []
    for name, r in got.items():
        if not isinstance(r, dict):
            continue
        if "not_run" in r:
            out.append(f"{name.replace('_', ' ')}: not run, since {r['not_run']}")
            continue
        n, f = r.get("looked_at", 0), r.get("findings", [])
        out.append(f"{name.replace('_', ' ')}: looked at {n}, found {len(f)}"
                   + (f" ({r['not_looked_at']} more not looked at)" if r.get("not_looked_at") else "")
                   + (": " + "; ".join(x["problem"] for x in f[:3]) if f else ""))
    return out


# What follows reads an open run: its answer, its code steps' rows and its corpus.



def _code_index(text: str, u16: int) -> int:
    """A UTF-16 offset, as the locator counts, as an index into the Python string."""
    return len(text.encode("utf-16-le")[:2 * u16].decode("utf-16-le", errors="ignore"))


def place(run: S.Run, wanted: list[tuple[list[str], str]]) -> list[dict | None]:
    """Each quotation placed in the first of its documents that holds it word for word (`locator.locate_quoted`, at
    one of `locator.AS_QUOTED`), with one call of the locator for each document; None where none does."""
    out: list[dict | None] = [None] * len(wanted)
    order: list[str] = []
    for docs, _ in wanted:
        order += [d for d in docs if d not in order and d in run.corpus.documents]
    for d in order:
        todo = [i for i in range(len(wanted)) if out[i] is None and d in wanted[i][0]]
        if not todo:
            continue
        text = run.corpus.text(d)
        for i, h in zip(todo, locator.locate_quoted(text, [wanted[i][1] for i in todo])):
            if h is not None and h.tier in locator.AS_QUOTED:
                out[i] = {"document": d, "start": _code_index(text, h.start), "end": _code_index(text, h.end)}
    return out


def _cited_documents(run: S.Run, scope: str, rows: dict[str, dict]) -> list[str]:
    """The documents a stretch of the answer cites, in the order it cites them: a row's own document, the documents of
    the rows a tagged claim rests on and those against it (`judge.claims`), or a document named in the brackets."""
    claims = {f"{sid}.{c['id']}": c["rows"] + c["against"] for sid, rec in run.out.items() if rec.get("kind") == "claims"
              for c in rec["claims"]}
    out: list[str] = []
    for c in S.citation_ids(scope):
        for d in ([rows[c]["document"]] if c in rows else [rows[x]["document"] for x in claims[c] if x in rows] if c in claims
                  else [S.cited_document(run, c)]):
            if d and d in run.corpus.documents and d not in out:
                out.append(d)
    return out


def _value_cases(run: S.Run) -> tuple[list[tuple[str, str]], dict[tuple, set]]:
    """The values of every code step's nominal columns that the workflow fixes, and the cases each was coded for.
    A column naming a link's ends or sign takes its values from the factors, so a factor used only as an effect is not
    a fault of the list; a yes/no column's "no" is an absence, not a use; a combined table's rows are its inputs' own."""
    items, used = [], {}
    for sid, rec in run.out.items():
        if rec.get("kind") != "code" or rec.get("combines"):
            continue
        step = next((s for s in run.steps if s.get("id") == sid), {})
        links = {v for v in (step.get("links") or {}).values() if isinstance(v, str)}
        for col in rec.get("columns") or []:
            vals = col.get("values")
            if col.get("type") != "nominal" or col["name"] in links or not isinstance(vals, list) or not vals:
                continue
            names = [str(v.get("name") or v.get("id") or "") if isinstance(v, dict) else str(v) for v in vals]
            book = f"{sid}.{col['name']}"
            keyed = {value_key(n): n for n in names}
            for r in rec["rows"]:
                n = keyed.get(value_key(r.get(col["name"])))
                if n is not None:
                    used.setdefault((book, n), set()).add(run.corpus.case_of(r["document"], r.get("case")))
            items += [(book, n) for n in names]
    return items, used


def audit_run(run: S.Run, answer: str | None, counts: dict) -> dict:
    """Every check on a recounted run. `answer` is the writer's `answer.md` (None for a recount without one, which
    leaves the checks of the answer out and says so); `counts` is the recount's counts, by id."""
    items, used = _value_cases(run)
    got: dict = {"answer": bool(answer), "code_values": item_use(items, used)}
    if not answer:
        return got
    rows = {r["row"]: r for rec in run.out.values() if rec.get("kind") == "code" for r in rec["rows"]}
    got["quantifiers"], got["person_words"] = not_run("quantifiers"), not_run("person_words")

    # each quotation with the documents its sentence (or the list it introduces) cites
    wanted, seen = [], set()
    for _, scope in S._sentences_with_scope(answer):
        docs = _cited_documents(run, scope, rows)
        for q in S.quotations(scope):
            if docs and (q, tuple(docs)) not in seen:
                seen.add((q, tuple(docs)))
                wanted.append((docs, q))
    placed = place(run, wanted) if wanted else []
    cited = [{"quote": q, "document": hit["document"] if hit else docs[0], "at": hit}
             for (docs, q), hit in zip(wanted, placed)]
    text_of = run.corpus.text
    got["speakers"] = speakers(cited, text_of)
    got["word_cuts"] = word_cuts(cited, text_of)

    # a document is cited by a row or a bracketed id, and named where its id stands in the prose as a word of its own
    prose = T.without_quotations(re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", answer))
    named = {d for d in run.corpus.documents
             if not d.isdigit() and re.search(rf"(?<![\w.-]){re.escape(d)}(?![\w-])", prose)}
    cited_docs = set(_cited_documents(run, answer, rows)) | named
    read = {d for rec in run.out.values() if rec.get("kind") == "code" for d in rec.get("documents") or []}
    # the documents the coding read, where a sample drew some of the corpus
    in_play = {d: v for d, v in run.corpus.documents.items() if d in read} or run.corpus.documents
    got["coverage"] = coverage(in_play, run.corpus.columns, cited_docs, read)
    return got
