"""Checks on an answer and its coding that code can make without a model: warnings for the writer and the check to
weigh against the documents, never refusals.

    quantifiers   a word of quantity beside a cited count agrees with it ("most" beside 4 of 12 does not)
    speakers      a quotation cited in the answer is the respondent's words, not the interviewer's
    word cuts     a quotation starts and ends on a word boundary in its document
    person words  the answer calls nobody "he" or "she" where the documents it cites never do
    coverage      which documents the answer never cites or names, and which groups of documents no citation comes from
    code values   a value a code step's nominal column allows that no passage was coded with, or that rests on one case

The pure checks take plain data (offsets, texts, counts), so the private harness calls them on its own records
(`rubicon/rubicon/coordinator/audits.py`) and a recount calls them on an open run (`audit_run`). Each check says how
many things it looked at, so an empty list of findings reads as "looked and found nothing", never as "did not look".

Two checks of the harness's audit are not here because the open record does not hold what they read: a quotation read
both as saying an item and as denying it (a coded passage carries no status, and one passage may properly sit in two
rows with different values), and a codebook built from few documents or never piloted (a group step records neither
which documents built the codebook nor a pilot).
"""
from __future__ import annotations

import re
from collections import Counter

from . import locator
from . import steps as S
from .workflow import value_key

#: Words of quantity, longest first, each with the test a share must pass to be called so.
QUANTIFIERS = [
    (r"nearly all|almost all|virtually all|almost every", lambda v, n: n and v / n >= 0.75, "at least three quarters"),
    (r"the (?:great |large |vast )?majority|most", lambda v, n: n and v / n > 0.5, "more than half"),
    (r"about half|around half|half", lambda v, n: n and 0.4 <= v / n <= 0.6, "about half"),
    (r"a minority|only a few|a few|a handful|few", lambda v, n: n and v / n < 0.5, "fewer than half"),
    (r"none|no one|nobody|not one", lambda v, n: v == 0, "none"),
    (r"all|every(?:one)?", lambda v, n: n and v == n, "all"),
]
QUANT_RE = re.compile(r"\b(" + "|".join(p for p, _, _ in QUANTIFIERS) + r")\b", re.I)
GENDERED = {"female": {"she", "her", "hers", "herself", "woman", "women"},
            "male": {"he", "him", "his", "himself", "man", "men"}}
PRONOUNS = {"she", "her", "hers", "herself", "he", "him", "his", "himself"}
#: A quotation in the answer, whose words are the speaker's and not the answer's.
QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
#: A turn's label in a transcript: `Interviewer:`, `User:`, `R2:`.
SPEAKER = re.compile(r"^[ \t]*([A-Z][A-Za-z0-9 .'\-]{0,30}?)[ \t]*:[ \t]+\S", re.M)


#: Most labels a transcript of one respondent has: the respondent's, and the interviewer's, which one transcript may
#: write two ways ("Assistant:" first, "AI:" after).
INTERVIEW_LABELS = 3


def speaker_at(text: str, offset: int) -> dict | None:
    """Who is speaking at `offset` in a transcript, and whether it is the respondent (whoever first answers the
    opener). None where the document is not a transcript, or has more speakers than an interview of one respondent
    has, such as a focus group, where who speaks first does not say who interviews."""
    turns = [(m.start(), m.group(1).strip()) for m in SPEAKER.finditer(text)]
    labels = Counter(label for _, label in turns)
    if not 2 <= len({k for k, n in labels.items() if n >= 2}) <= INTERVIEW_LABELS:
        return None
    opener = turns[0][1]
    respondent = next((lab for _, lab in turns if lab != opener), None)
    before = [lab for s, lab in turns if s <= offset]
    if not before:
        return {"speaker": None, "respondent": False}
    return {"speaker": before[-1], "respondent": before[-1] == respondent}


def _superlative(text: str, m: re.Match) -> bool:
    """"The most common use" ranks things and says nothing about how many people; "most interviewees" does."""
    if m.group(1).lower() != "most":
        return False
    after = text[m.end():].split()
    nxt = after[0].lower().strip(",.;:()") if after else ""
    return (text[:m.start()].rstrip().lower().endswith("the")
            or nxt.endswith("ly") or nxt in {"common", "often", "frequent", "cited", "mentioned",
                                             "popular", "important", "useful", "used", "valued"})


def quantifiers(text: str, refs: list[dict]) -> dict:
    """Each count cited in `text` (`refs`: its `start` in the text, the words it `said`, its `value` and `out_of`)
    against the word of quantity that governs it."""
    findings = []
    for ref in refs:
        got = (ref["value"], ref["out_of"])
        # The word of quantity nearest before the count, within its clause.
        before = re.split(r"[.;:\n]", text[max(0, ref["start"] - 80):ref["start"]])[-1]
        # Only a word that governs the count: close before it ("most interviewees ([[count]])"),
        # neither a superlative nor the group the sentence is about ("across everyone").
        words = [w for w in QUANT_RE.finditer(before) if not _superlative(before, w)
                 and len(re.findall(r"[A-Za-z]+", before[w.end():])) <= 4
                 and not re.search(r"\b(across|among|of|for|from|to)\s*$", before[:w.start()], re.I)]
        if not words:
            continue
        word = words[-1].group(1)
        for pattern, ok, needs in QUANTIFIERS:
            if re.fullmatch(pattern, word, re.I):
                if not ok(*got):
                    findings.append({"said": f"{word} {ref['said']}", "count": f"{got[0]} of {got[1]}",
                                     "problem": f'"{word}" needs {needs}; the count is {got[0]} of {got[1]}'})
                break
    return {"looked_at": len(refs), "findings": findings}


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


def word_cuts(cited: list[dict], text_of) -> dict:
    findings, looked = [], 0
    for c in cited:
        if not c["at"]:
            continue
        looked += 1
        text, s, e = text_of(c["document"]), c["at"]["start"], c["at"]["end"]
        cut_start = s > 0 and text[s - 1].isalnum() and text[s].isalnum()
        cut_end = e < len(text) and text[e - 1].isalnum() and text[e].isalnum()
        if cut_start or cut_end:
            findings.append({"document": c["document"], "quote": c["quote"][:100],
                             "problem": "it starts inside a word" if cut_start and not cut_end
                             else "it ends inside a word" if cut_end and not cut_start
                             else "it starts and ends inside words"})
    return {"looked_at": looked, "findings": findings}


def person_words(sentences: list[dict], text_of) -> dict:
    """A sentence of the answer's own words (quotations left out) that calls someone he or she. Each of `sentences` is
    {sentence, docs (the documents it cites), own (the sentence without its quotations and citations)}.

    A pronoun names one person, and a document that uses "her" somewhere may use it of somebody else, so every pronoun
    is found, cited or not, for the evaluator to check against the person's own words. A word for a group ("women") is
    found only where none of the documents the sentence cites uses a word of that gender."""
    findings = []
    for s in sentences:
        said = {w.lower() for w in re.findall(r"[A-Za-z]+", s["own"])}
        for gender, words in GENDERED.items():
            pronouns = said & words & PRONOUNS
            nouns = said & (words - PRONOUNS)
            if nouns and s["docs"] and not any(
                    words & {w.lower() for w in re.findall(r"[A-Za-z]+", text_of(d))} for d in s["docs"]):
                pronouns |= nouns
            if pronouns:
                findings.append({"documents": s["docs"], "said": sorted(pronouns), "sentence": s["sentence"].strip()[:160],
                                 "problem": f"calls someone {'/'.join(sorted(pronouns))}; a participant is "
                                            f"'they' unless their own words give their gender"})
    return {"looked_at": len(sentences), "findings": findings}


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
    """One line per check: what it looked at and what it found."""
    out = []
    for name, r in got.items():
        if not isinstance(r, dict):
            continue
        n, f = r.get("looked_at", 0), r.get("findings", [])
        out.append(f"{name.replace('_', ' ')}: looked at {n}, found {len(f)}"
                   + (": " + "; ".join(x["problem"] for x in f[:3]) if f else ""))
    return out


# What follows reads an open run: its answer, its code steps' rows and its corpus.

#: A count cited as {<id>} (steps.COUNT_ID), whose words are "n of base" in the recount's counts.
COUNT_ID = re.compile(r"\{(" + S.COUNT_ID + r")\}")
OF = re.compile(r"(\d+) of (\d+)")
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")


def _code_index(text: str, u16: int) -> int:
    """A UTF-16 offset, as the locator counts, as an index into the Python string."""
    return len(text.encode("utf-16-le")[:2 * u16].decode("utf-16-le", errors="ignore"))


def place(run: S.Run, wanted: list[tuple[list[str], str]]) -> list[dict | None]:
    """Each quotation placed in the first of its documents that holds all its parts word for word (a quotation may
    join passages with an ellipsis), with one call of the locator for each document; None where none does."""
    parts = [[p for p in ELLIPSIS.split(q) if len(p.strip()) >= 4] or [q] for _, q in wanted]
    out: list[dict | None] = [None] * len(wanted)
    order: list[str] = []
    for docs, _ in wanted:
        order += [d for d in docs if d not in order and d in run.corpus.documents]
    for d in order:
        todo = [i for i in range(len(wanted)) if out[i] is None and d in wanted[i][0]]
        if not todo:
            continue
        text = run.corpus.text(d)
        hits = locator.locate_all(text, [p for i in todo for p in parts[i]])
        k = 0
        for i in todo:
            mine, k = hits[k:k + len(parts[i])], k + len(parts[i])
            if all(h is not None and h.tier in locator.SNAP_TIERS for h in mine):
                out[i] = {"document": d, "start": _code_index(text, mine[0].start), "end": _code_index(text, mine[-1].end)}
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
    refs = []
    for m in COUNT_ID.finditer(answer):
        n = OF.fullmatch(str(counts.get(m.group(1), "")))
        if n:
            refs.append({"start": m.start(), "said": m.group(0), "value": int(n.group(1)), "out_of": int(n.group(2))})
    got["quantifiers"] = quantifiers(answer, refs)

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

    sentences = []  # a sentence never ends inside a quotation, which may hold several
    for sentence, _ in S._sentences_with_scope(answer):
        own = QUOTED.sub(" ", re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", sentence))
        sentences.append({"sentence": sentence, "docs": _cited_documents(run, sentence, rows), "own": own})
    got["person_words"] = person_words(sentences, text_of)

    # a document is cited by a row or a bracketed id, and named where its id stands in the prose as a word of its own
    prose = QUOTED.sub(" ", re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", answer))
    named = {d for d in run.corpus.documents
             if not d.isdigit() and re.search(rf"(?<![\w.-]){re.escape(d)}(?![\w-])", prose)}
    cited_docs = set(_cited_documents(run, answer, rows)) | named
    read = {d for rec in run.out.values() if rec.get("kind") == "code" for d in rec.get("documents") or []}
    # the documents the coding read, where a sample drew some of the corpus
    in_play = {d: v for d, v in run.corpus.documents.items() if d in read} or run.corpus.documents
    got["coverage"] = coverage(in_play, run.corpus.columns, cited_docs, read)
    return got
