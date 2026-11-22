"""How a run was done, told in words for a reader new to Rubicon: the procedure the workflow x-ray draws, stage by stage.

Built by code from the run's own records and never written by a model, so it is true of this run and the same every
time it is drawn. It walks the same list of steps the x-ray draws (`render_report.drawn_steps`), so every step the
x-ray shows is told here and the two cannot disagree; `told` refuses a step it has no words for. Each stage is a short
paragraph, and each step it tells links to that step's part of the annex (`anchor`).

A fact a run's records do not hold is left out rather than guessed: an older run without a check record says nothing
about a second coding, and a check record whose counts cannot be read says only what the second coding did.
`INTERNAL` lists the words a reader must never meet here; `tests/test_procedure.py` holds the text to it.
"""
from __future__ import annotations

import re

from . import claims, isolation, legacy_weak
from . import text as T
from .names import step_name
from .steps import unit_of_table
from .workflow import key_columns, links_ending

#: Words internal to Rubicon or to its records, which the explanation never uses: a reader new to Rubicon would have to
#: look each one up. Matched as whole words, case-insensitively, by the test.
INTERNAL = ("tabulate", "tabulation", "tabulations", "judge", "judged", "recount", "recounted", "row", "rows", "seal",
            "sealed", "CLD", "cell", "cells", "step", "steps", "per_document", "weak", "kappa", "zip", "json",
            "asset", "node", "margin map", "workflow map")

#: Above this many coded columns in a run, the coding is summarised by what the columns record rather than each column
#: named with its meaning; above this many tables, the counting says how many tables and maps rather than listing each
MANY_COLUMNS = 4
MANY_TABLES = 4
#: Small counts in words, as a reader would say them
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}

#: Filters a causal map's table can set, in words; one not listed is named by its type
FILTER_SAID = {"combine-opposites": "each factor and its opposite drawn as one"}


def anchor(sid: str) -> str:
    """The id of a step's part of the annex, which each stage's link opens. Begins `s-` so that a combined report,
    which makes each part's section ids its own (`bind.scoped`), does the same for these."""
    return "s-howdone-" + "-".join(T.words(sid.lower()))


def _label(v) -> str:
    """A coded name as a reader sees it, lowercased for the middle of a sentence where it is not an acronym."""
    s = str(v).replace("_", " ").strip().removeprefix("#").strip()
    if s.startswith("~"):  # a factor's opposite pole, which Causal Map writes with a leading ~
        return "the opposite of " + s[1:].strip()
    return s if s[:2].isupper() else s[:1].lower() + s[1:]


def _listed(items: list[str]) -> str:
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def _first_sentence(text: str, most: int = 160) -> str:
    """A definition's opening, which is what a column means in brief: its first sentence, cut at a colon or semicolon
    where that sentence runs long."""
    t = T.after_marks().split(str(text or "").strip(), maxsplit=1)[0].rstrip(T.STOPS)
    if len(t) > most:
        t = re.split(r"[:;]\s|[：；]", t, maxsplit=1)[0]
    return t[:1].lower() + t[1:] if t[:2] != t[:2].upper() else t


def _means(c: dict) -> str:
    return f"{_label(c['name'])} ({_first_sentence(c['means'])})" if c.get("means") else _label(c["name"])


def _short(c: dict) -> str:
    """A column's meaning as a short phrase of what it records, without its name: the definition's opening, its
    asides in brackets left out, a yes-or-no definition ("Yes where ...") said as "whether ..."."""
    t = re.sub(r"\s*\([^()]*\)", "", _first_sentence(c.get("means")) or _label(c["name"]))
    t = re.sub(r"(?i)^yes,? (?:where|if|when) ", "whether ", t).strip(" ,")
    return t[:1].lower() + t[1:] if t[:2] != t[:2].upper() else t


def _recorded(cols: list[dict]) -> str:
    """What a coding recorded, summarised for a run with many columns: what each listed column records, in its own
    definition's words, then the yes-or-no columns by their number, which the codebook in the annex sets out."""
    listed = [_short(c) for c in cols if c.get("type") not in ("binary", "free_text")]
    free = [_short(c) for c in cols if c.get("type") == "free_text"]
    yes_no = [c for c in cols if c.get("type") == "binary"]
    if len(yes_no) == 1:
        listed.append(_short(yes_no[0]))
    said = _listed(listed + free) or "what the question asks"
    if len(yes_no) > 1:
        said += f", with {WORDS.get(len(yes_no), len(yes_no))} yes-or-no codes besides, each defined in the codebook"
    return said


def _coded(cols: list[dict]) -> str:
    """What a coding coded, in brief: each column that takes one of a list of codes with what it means, then the
    yes-or-no columns by name, then those written in the respondent's own words."""
    listed = [_means(c) for c in cols if c.get("type") not in ("binary", "free_text")]
    yes_no = [f"{_label(c['name'])} ({_short(c)})" if c.get("means") else f"{_label(c['name'])} (yes or no)"
              for c in cols if c.get("type") == "binary"]
    free = [_label(c["name"]) for c in cols if c.get("type") == "free_text"]
    parts = listed + yes_no + (
        [f"{_listed(free)} in the respondent's own words"] if free else [])
    return "; ".join(parts[:-1]) + ("; and " if len(parts) > 2 else " and " if len(parts) == 2 else "") + parts[-1]         if parts else "what the question asks"


def _by(b, coded: set) -> str:
    """A column a table counts by: a coded column by its name, a column of the document list as its heading reads."""
    return _label(b) if b in coded else f"“{str(b).removeprefix('#').strip()}”"


def _table(s: dict, links: dict | None, coded: set) -> str:
    """What one table counts, in words, without its unit, which the paragraph says once: its columns, or for a table of
    causal links what its map shows."""
    unit = unit_of_table(s)
    if s.get("loops"):
        through = f" through {_listed([str(t) for t in s['through']])}" if s.get("through") else ""
        return f"the feedback loops of up to {s.get('loop_links', 4)} links{through}"
    if s.get("paths"):
        return "the causal paths told, from one end to the other"
    if s.get("sequences"):
        return "the order in which events are told"
    if links and list(s.get("by") or [])[:2] == [links.get("from"), links.get("to")]:
        fs = s.get("filters") or []
        which = [_filter(f, unit) for f in fs if f.get("type") not in FILTER_SAID]
        drawn = [FILTER_SAID[f["type"]] for f in fs if f.get("type") in FILTER_SAID]
        return "a causal map" + (" of the links " + _listed(which) if which else " of every link") + (
            f" ({_listed(drawn)})" if drawn else "")
    return "by " + _listed([_by(b, coded) for b in s.get("by") or []])


def _filter(f: dict, unit: str) -> str:
    t = f.get("type", "")
    if t == "link-frequency" and f.get("mode", "minimum") == "minimum" and f.get("threshold") is not None:
        return f"told by at least {f['threshold']} {unit}"
    if t == "path-tracing":
        ends = f.get("toLabels") or f.get("fromLabels") or []
        way = "into" if f.get("toLabels") else "out of"
        steps = f.get("maxSteps")
        reach = "directly " if steps == 1 else f"within {steps} links " if steps else ""
        return f"leading {reach}{way} {_listed([_label(e) for e in ends])}"
    return f"kept by the {t.replace('-', ' ')} filter"


#: How each kind of criterion reaches its level, in brief, where a rule mixes kinds
BRIEFLY = {"rule": "counted against the rule's thresholds",
           "stated": "a number a background document states, set against the rule's thresholds",
           "reading": "the coded passages read against each level's description"}


def _times(k: int) -> str:
    return {1: "once", 2: "twice"}.get(k, f"{k} times")


def _parsed(check: str, word: str) -> int | None:
    """A number the check record's counts give after `word`, or None where it gives none."""
    counts = check.split("## Counts", 1)[1].split("\n## ", 1)[0] if "## Counts" in check else ""
    m = re.search(rf"(?i){word}\b[^\d\n]{{0,30}}?(\d+)", counts)
    return int(m.group(1)) if m else None


def sentences_changed(R: dict) -> int | None:
    """How many sentences of the answer the check's reader says, in its record's counts, that it changed."""
    return _parsed(R.get("check") or "", "sentences changed")


def changed_said(R: dict) -> str:
    """What the check says it changed in the answer, as a sentence of its own, or nothing where its record's counts
    give no such number. The number is the reader's own: the zip keeps the answer only as corrected, so fixed rules
    cannot count the changes, and the sentence says whose number it is. The record tells what the check changed, never
    what it read, so no report says a check read every sentence."""
    n = sentences_changed(R)
    if n is None:
        return ""
    if not n:
        return " The reader's own record says it did not change any sentence of the answer."
    return (f" The reader's own record says it changed {n} sentence{'' if n == 1 else 's'} of the answer; fixed rules "
            f"did not count {'them' if n > 1 else 'it'}.")


def _profiled(c: dict) -> str:
    """What one column of a profile records, in words."""
    if "holds" in c:
        coded = _listed([f"{_label(k)} {' or '.join(_label(x) for x in (v if isinstance(v, list) else [v]))}"
                         for k, v in (c.get("holds") or {}).items()])
        return f"whether any passage was coded {coded}"
    if "values" in c:
        return f"every {_label(c['values'])} coded"
    if "distinct" in c:
        return f"how many different values of {_label(c['distinct'])} its passages carry"
    k = "first" if "first" in c else "last"
    return f"its {k} {_label(c.get(k))}" + (f" by {_label(c['order'])}" if c.get("order") else "")


def earlier_said(R: dict, s: dict) -> str:
    """Where a code step's coding came from when it was taken from an earlier run (`earlier.resolve`): the passages
    themselves, coded and checked in that run and not checked again here, or only the definitions, applied afresh."""
    ref = s["from"]
    q = next((e.get("question") for e in (R.get("report") or {}).get("earlier_runs", []) if e.get("step") == s["id"]), "")
    run = f"an earlier run ({ref['run_id']})" if ref.get("run_id") else "an earlier run"
    said = f"{run}, which asked: {q.strip()}" if q.strip() else run
    said += "" if said[-1] in ".?!" else "."
    if (ref.get("take") or "rows") == "definitions":
        return f"The definitions were those of {said} The documents were coded to them afresh here."
    return (f"This coding was taken whole from {said} Its passages were coded and checked in that run, whose report "
            "shows how, and are not checked again here.")


def from_said(passages: str, from_facts: bool) -> str:
    """What the numbers were made from: `passages` ("the coded passages"), and the documents' own facts too where a
    count rests on them (`render_report.counts_from_facts`). Every sentence saying where the numbers come from is built
    from this or from `computed_said`, so none says "passages" of a count that does not rest on one."""
    return f"{passages} or the documents' own facts" if from_facts else passages


def computed_said(from_facts: bool) -> str:
    """How the answer's numbers were made, to follow "every one" or "every number ... was": unchanged where every count
    rests on passages, and naming the documents' own facts as well where some do not."""
    return ("computed by fixed rules from " + from_said("the coded passages", True) + ", rather than written by the AI"
            if from_facts else "computed directly from the coded passages rather than written by the AI")


#: A said piece holding words the run chose (a label, a definition, a question), whose digits are part of them
NAME = "name"


def _count(figures: dict, *names, kind: str = "count") -> dict:
    """A piece's mark as a claim (`claims`): the figures it gives, and the words in it the run chose."""
    names = [str(n) for n in names if str(n or "").strip()]
    return {"kind": kind, "is": figures, **({"names": names} if names else {})}


def _tables_by_kind(steps: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """The workflow's tables as the counting names them, each kind with the measure that counts it: tables, causal maps
    (a table by a coding's two link ends) and tables of feedback loops."""
    tables = [s for s in steps if s.get("kind") == "tabulate"]

    def is_map(s):
        ends = links_ending(steps, (s.get("inputs") or [s.get("input")])[0])
        return bool(ends) and list(s.get("by") or [])[:2] == [ends.get("from"), ends.get("to")] and not s.get("loops")
    return [("table", "plain tables", [s for s in tables if not (is_map(s) or s.get("loops"))]),
            ("causal map", "causal maps", [s for s in tables if is_map(s)]),
            ("table of feedback loops", "tables of feedback loops", [s for s in tables if s.get("loops")])]


def told(R: dict, steps: list[dict], from_facts: bool = False) -> list[dict]:
    """The procedure as stages, each {"title", "steps", "parts"}: `parts` is the paragraph as (text, step id or None)
    pieces, a piece with a step id linking to that step's part of the annex. `steps` is the list the x-ray draws.
    `from_facts` is whether any count rests on the documents' own facts (`render_report.counts_from_facts`)."""
    records = R.get("steps", {})
    by_id = {s["id"]: s for s in steps}
    n = len(R.get("index", []))
    stages, done = [], set()

    def stage(title, parts):
        done.update(p[1] for p in parts if p[1])
        parts = [p for p in parts if p[0]]
        if parts:
            # each piece is (words, step id or None, mark): its mark a claim's basis ({"kind", "is"}, `claims`), what a
            # said piece's digits may be (`claims.SAID`), or None for a piece not yet marked
            parts = [(*p, None) if len(p) == 2 else p for p in parts]
            stages.append({"title": title, "steps": [p[1] for p in parts if p[1]], "parts": parts})

    def of_kind(*kinds):
        return [s for s in steps if s.get("kind") in kinds]

    def rec(s):
        return {**s, **records.get(s["id"], {})}

    tables, codes, judges = of_kind("tabulate"), of_kind("code"), of_kind("judge")

    # What was read: every document, or the sample drawn from them, and what the counts count
    units = {unit_of_table(rec(s)) for s in tables} - {"documents", "passages"}
    alone = all(records.get(s["id"], {}).get("cases_are_documents", True) for s in tables)
    samples = of_kind("sample")
    # a step whose rows the AI cited for an answer it had already written: what it read is not recorded
    cited = any(s.get("cited") for s in codes)
    read = [((f"The AI that wrote the answer was given all {n} documents; what it read of them is recorded only in its own "
              "word, under What each document gave." if R.get("read") is not None else
              f"The AI that wrote the answer was given all {n} documents; what it read of them is not recorded.") if n and cited
             else f"Rubicon read all {n} documents in full." if n and not samples else "", None,
             _count({"documents": n, "writer's record of what it read kept": R.get("read") is not None}, kind="record")
             if n and cited else _count({"documents": n}))]
    for i, s in enumerate(samples):
        drawn = records.get(s["id"], {}).get("documents")
        where = s.get("where") or {}
        # from a profile, the columns are those of its summing-up of each unit, and every document of a unit kept is read
        of_units = records.get(s["id"], {}).get("units") is not None
        kept = ((" as every document of those whose summing-up has " if of_units else " among those with ") + _listed([f"{_by(k, set())} {_listed([str(x) for x in (v if isinstance(v, list) else [v])])}"
                                               for k, v in where.items()])) if where else ""
        how = "chosen by name" if s.get("documents") else "drawn at random" if s.get("n") else "chosen"
        spread = f", spread across {_by(s['stratify_by'], set())}" if s.get("stratify_by") else ""
        count = f"{len(drawn)} of the {n} documents" if drawn is not None and n else "a sample of the documents"
        named = ([_by(k, set()) for k in where] + [str(x) for v in where.values() for x in (v if isinstance(v, list) else [v])]
                 + ([_by(s["stratify_by"], set())] if s.get("stratify_by") else []))
        read.append(((" " if i else "") + f"Rubicon read {count} in full, {how}{kept}{spread}.", s["id"],
                     _count({"documents": n, f"documents drawn@{s['id']}": len(drawn)}, *named) if drawn is not None and n
                     else NAME))
    if len(units) == 1 and alone and n:
        read.append((f" The counts below are of {next(iter(units))}, one document each.", None, NAME))
    stage("What was read", read)

    # The coding: what each coding looked for, in the codebook's own words, each column named where there are few and
    # what they record summarised where there are many
    coding = []
    plain = [c for s in codes for c in s.get("columns") or []
             if c.get("name") not in ((s.get("links") or {}).get(k) for k in ("from", "to", "sign"))]
    what = _recorded if len(plain) > MANY_COLUMNS else (lambda cols: _coded(cols))
    verb = "recorded" if len(plain) > MANY_COLUMNS else "coded"
    for i, s in enumerate(codes):
        cols = s.get("columns") or []
        lead = "It then" if i == 0 else " It also"
        links = s.get("links")
        if records.get(s["id"], {}).get("combines"):  # nothing was coded here: other codings' passages, put together
            coding.append((f"{lead} put the passages coded in {_listed(s['inputs'])} together into one table, each keeping its "
                           "own quotation and the coding it came from.", s["id"], NAME))
            continue
        if s.get("cited"):
            labels = _listed([_label(c.get("name")) for c in cols])
            coding.append((f"{lead} cited, for the numbers in its answer, the passages each rests on, each labelled with its {labels}. "
                           "So every count rests only on the passages cited: fixed rules found each one word for word in its "
                           "document and counted the documents they come from, but did not check that every passage bearing "
                           "on a point was cited, or that each was filed under the right point or speaker.", s["id"], NAME))
            continue
        if links:
            ends = next((c for c in cols if c.get("name") == links.get("from")), {})
            vals = ends.get("values") if isinstance(ends.get("values"), list) else []
            listed = f", each end one of a list of {len(vals)} factors" if vals else ""
            sign = ", and whether the effect goes up or down" if links.get("sign") else ""
            rest = [c for c in cols if c.get("name") not in (links.get("from"), links.get("to"), links.get("sign"))]
            more = f", also {verb} {what(rest)}" if rest else ""
            did = f"{lead} restated the causal claims it found in the documents as links from a cause to an effect{listed}{sign}{more}."
            mark = _count({f"factors listed@{s['id']}": len(vals)}, what(rest) if rest else "") if vals else NAME
        elif s.get("per_document"):
            did, mark = f"{lead} read each document as a whole and {verb} {what(cols)}.", NAME
        else:
            did, mark = f"{lead} marked the passages it found that bear on the question and {verb} {what(cols)}.", NAME
        if isinstance(s.get("from"), dict):
            # where it came from, the earlier run's ID and question being that run's own words
            earlier = earlier_said(R, s)
            did += " " + earlier
            if mark != NAME:
                mark = {**mark, "names": [*mark.get("names", []), earlier]}
        coding.append((did, s["id"], mark))
    for s in of_kind("group"):
        most = f" at most {s['max_items']}" if s.get("max_items") else ""
        key = f" of {' and '.join(_label(k) for k in key_columns(s))}" if s.get("key_column") else ""
        figures = {f"themes at most@{s['id']}": s["max_items"]} if s.get("max_items") else {}
        placed = ""
        if s.get("assign"):
            # how many it placed, as the record counts them, since a row can be given no theme
            given, of = _assigned(R, s["id"])
            what = "labels" if len(key_columns(s)) > 1 else "passages"
            placed = (", and placed passages under them; fixed rules found no count of how many" if given is None else
                      f", and placed all {of} {what} under one of them" if given == of else
                      f", and placed {given} of the {of} {what} under one of them")
            if given is not None:
                figures.update({f"given a theme@{s['id']}": given, f"to be given a theme@{s['id']}": of})
        coding.append((f" It grouped the labels{key} into{most} themes, which became a codebook{placed}.", s["id"],
                       _count(figures, *(_label(k) for k in key_columns(s)) if s.get("key_column") else (),
                              kind="count" if f"given a theme@{s['id']}" in figures else "record") if figures else NAME))
    if legacy_weak.in_report(R) and any(c.get("weak") for s in codes for c in s.get("columns") or []):  # legacy_weak
        coding.append((" A passage that only implies a code, in the way the code's definition names, was marked implicit "
                       "and counted apart from the passages that say it explicitly.", None, ""))
    stage("Coding", coding)

    # The second coding and the check, where the run holds them
    # every piece of it marked (`claims`): a figure from an AI reader's own record, readers.json and check.md alike,
    # makes the piece a reader's claim, and one from what fixed rules compared or found a count or a record's
    second = []
    changed = lambda: [(changed_said(R), "check", {"kind": "reader", "is": {"sentences changed": sentences_changed(R)}})]
    if "second_coding" in by_id:
        second.append((SECOND, "second_coding", {"kind": "reader", "is": {"second coded": True}}))
    if "check" in by_id and not second_coded(R):
        second.append((f"{READER} then read the answer against the passages it cites and the documents, so the coding "
                       "and the answer in this report are the corrected ones, counted again after the check.", "check",
                       {"kind": "reader", "is": {"second coded": False}}))
        second += changed()
    elif "check" in by_id:
        raised, ruled, first, other, unsettled = (MEASURES_OF_THE_CHECK[k](R) for k in (
            "places raised", "places ruled on", "places ruled for the first coding", "places ruled for the second coding",
            "places left unsettled"))
        # agreement is said only where a comparison that looked found nothing, and only of what it compared; a
        # comparison that compared nothing, or none kept, never reads as agreement, nor does a check that ruled on some
        looked, nothing = compared(R)
        free = bool(code_columns(R.get("workflow"))[1])
        # what the reader of the check says of its own rulings, in its record's counts
        ruling = {"places ruled on": ruled, "places ruled for the first coding": first,
                  "places ruled for the second coding": other, "places left unsettled": unsettled}
        lead = " " if second else ""
        if raised:
            took = f", taking them as {ruled} disagreements" if ruled is not None and ruled != raised else ""
            # the places come from compare.py's comparison where the run keeps it, and from the check's own count where not
            kept = bool(R.get("disagreements"))
            said = [(f"{lead}The two codings differed in {raised} places." if kept else
                     f"{lead}The check's own record says the two codings differed in {raised} places.", "check",
                     {"kind": "count", "is": {"places the codings differed": raised}} if kept else
                     {"kind": "reader", "is": {"places the check's record says differed": raised}}),
                    # "each" only beside the record's count of its rulings; without one, what the record backs
                    (f" {READER} ruled on each against the text{took}: {first} for the first coding, {other} for the second"
                     + (f", and {unsettled} that the definitions as written did not settle" if unsettled else "") + "."
                     if ruled is not None else
                     f" {READER} ruled on the places where they differed, against the text, and fixed rules found no "
                     "count of its rulings.", "check", {"kind": "reader", "is": ruling})]
        elif ruled:
            said = [(f"{lead}{READER} compared the two codings passage by passage"
                     + (", since fixed rules could not compare codes written as free text," if nothing else "")
                     + f" and ruled on {ruled} places where they differed: {first} for the first coding, {other} for the second"
                     + (f", and {unsettled} that the definitions as written did not settle" if unsettled else "") + ".", "check",
                     {"kind": "reader", "is": {**ruling, "comparison compared nothing": nothing}})]
        elif looked:
            said = [(lead + ("The two codings agreed on every document and code." if not free else
                             "The two codings agreed on every document and value of the codes fixed rules compare; their codes "
                             "written as free text were not compared."), "check",
                     {"kind": "record", "is": {"comparison looked": True, "places the codings differed": 0, "free-text codes": free}})]
        elif nothing:
            who = READER
            said = [(f"{lead}Fixed rules could not compare the two codings, whose codes are free text, and "
                     + (f"{who[0].lower() + who[1:]} ruled on no place where they differed." if ruled == 0 else
                        "found no count in the check's record of the places it ruled on."), "check",
                     {"kind": "reader", "is": {**ruling, "comparison compared nothing": True}})]
        else:
            # no comparison is kept with the run, so nothing is said of what it found, and without a count of the
            # check's rulings nothing is said of how many it made
            said = [(f"{lead}{READER} ruled on "
                     + ("no place where the two codings differed" if ruled == 0 else
                        "the places where the two codings differed, against the text, and fixed rules found no count of its rulings")
                     + "; the comparison it ruled from is not in the run's record.", "check",
                     {"kind": "reader", "is": {**ruling, "comparison kept": False}})]
        tightened = MEASURES_OF_THE_CHECK["definitions tightened"](R)
        if tightened:
            said.append((f" It tightened {tightened} definition{'s' if tightened > 1 else ''} as a result, and corrected "
                         "the coding to match.", "check", {"kind": "reader", "is": {"definitions tightened": tightened}}))
        if MEASURES_OF_THE_CHECK["omissions searched"](R):
            said.append((" It searched the documents each count leaves out for passages both coders had missed, and added them.",
                         "check", {"kind": "reader", "is": {"omissions searched": True}}))
        said.append((" It also read the answer against the documents, so the coding and the answer in this report are the "
                     "corrected ones, counted again after the check.", "check", ""))
        second += said + changed()
    parts = [p for p in ("second_coding", "check") if p in by_id]
    if parts and isolation.recorded(R):  # who did each part, from what fixed rules recorded of the helpers
        second[1:1] = isolation.told(R, parts, {p: separate(R, p) is False for p in parts})
    elif parts:  # who did each part, said once, after what was done first
        second.insert(1, (readers_said(R, parts), parts[0],
                          {"kind": "reader", "is": {MEASURE_OF_SEPARATE[p]: separate(R, p) for p in parts}}))
    stage("Second coding and check" if "second_coding" in by_id else "Checking", second)

    # The profiles: what each unit's passages hold together, which the tables after them count
    profiled = []
    for s in of_kind("profile"):
        key = s.get("key", "case")
        unit = "case" if key == "case" else "document" if key == "document" else _label(key)
        profiled.append(((" " if profiled else "") + f"Fixed rules brought together, for each {unit}, everything coded in any of its "
                         f"passages and documents, and recorded {_listed([_profiled(c) for c in s.get('columns') or []])}"
                         + (", so a count can join what one person says in different places." if key == "case" else "."), s["id"], NAME))

    # The counting, from the coded passages and the document list, the unit said once where the tables share one: each
    # table listed where there are few, and where there are many, how many tables and maps, each opening its section
    if profiled and not tables:
        stage("Counting", profiled)
    if tables:
        coded = {c.get("name") for s in codes for c in s.get("columns") or []}
        ends_of = lambda s: links_ending(steps, (s.get("inputs") or [s.get("input")])[0])
        shared = {unit_of_table(rec(s)) for s in tables}
        unit = f" {next(iter(shared))}" if len(shared) == 1 else ""
        lead = (unit.strip()[:1].upper() + unit.strip()[1:]) if unit else from_said("The coded passages", from_facts)
        k = len(tables)
        if k > MANY_TABLES:
            kinds = [(name, counted, ss) for name, counted, ss in _tables_by_kind(steps) if ss]
            said = lambda name, ss: f"{WORDS.get(len(ss), len(ss)) if name != 'table' else len(ss)} {name}{'s' if len(ss) > 1 else ''}"
            # each kind's count a claim, in words or digits, on the measure that counts that kind
            told_kind = lambda name, counted, ss: (said(name, ss), ss[0]["id"], _count({counted: len(ss)}))
            parts = [(f"{lead} were then counted in ", None, NAME), told_kind(*kinds[0]),
                     (", compared by these codings", None, "")]
            rest = kinds[1:]
            for j, kind in enumerate(rest):
                sep = ", and drawn in " if j == 0 else " and " if j == len(rest) - 1 else ", "
                parts += [(sep, None, ""), told_kind(*kind)]
            parts.append((". The annex below gives each.", None, ""))
            parts += [("", s["id"]) for s in tables]
        else:
            parts = [(f"{lead} were then counted in {k} table{'s' if k > 1 else ''}: ", None, _count({"tables": k}, lead if unit else ""))]
            for i, s in enumerate(tables):
                said = _table(rec(s), ends_of(s), coded)
                parts.append((said if unit else f"{unit_of_table(rec(s))} {said}", s["id"], NAME))
                parts.append(("." if i == k - 1 else "; ", None, ""))
        stage("Counting", profiled + ([(" ", None, "")] if profiled else []) + parts)

    # The verdicts, each by the rule its criteria set
    if judges:
        sources = {s.get("source", "").strip().rstrip(".") for s in judges}
        one = next(iter(sources))
        source = f" They come from {one[:1].lower() + one[1:]}." if len(sources) == 1 and one else ""
        how = {"rule": "the answer was counted from the tables and set against the thresholds the rule gives",
               "stated": "a number a background document states was set against the thresholds the rule gives",
               "reading": "the coded passages were read against the description of each level the rule gives"}
        parts = [(f"Rubicon reached its verdicts by rules agreed beforehand.{source}", None, NAME)]
        if len(judges) == 1:
            s = judges[0]
            r = records.get(s["id"], {})
            crits = r.get("criteria") or s.get("criteria") or []
            kinds = list(dict.fromkeys(c["kind"] for c in crits if c.get("kind") in how))
            if len(kinds) == 1:
                parts.append((f" For each question the rule asks, {how[kinds[0]]}"
                              + (":" if any(c.get("verdict") for c in crits) else "."), None, ""))
            each = (lambda c: "") if len(kinds) == 1 else (lambda c: f" ({BRIEFLY.get(c.get('kind'), 'as the rule sets out')})")
            asked = [f" “{c['question'].strip()}”{each(c)} reached {c['verdict']}" for c in crits
                     if c.get("question") and c.get("verdict")]
            reached = [c for c in crits if c.get("question") and c.get("verdict")]
            parts.append((";".join(asked) + "." if asked else "", s["id"],
                          _count({f"verdicts@{s['id']}": [c["verdict"] for c in reached]},
                                 *[x for c in reached for x in (c["question"].strip(), c["verdict"])], kind="record")))
            if r.get("overall"):
                parts.append((f" The overall verdict was {r['overall']}.", s["id"],
                              _count({f"overall verdict@{s['id']}": r["overall"]}, r["overall"], kind="record")))
            parts.append(("", s["id"]))
        else:
            crits = [c for s in judges for c in (records.get(s["id"], {}).get("criteria") or s.get("criteria") or [])]
            kinds = list(dict.fromkeys(how[c["kind"]] for c in crits if c.get("kind") in how))
            first = next((c["question"].strip() for c in crits if c.get("question")), "")
            if kinds:
                parts.append((f" For each question a rule asks, such as “{first}”, " + "; ".join(kinds) + ".", None, NAME))
            got = [(records.get(s["id"], {}).get("overall"), s) for s in judges]
            if all(v for v, _ in got):
                parts.append((" The verdicts reached were ", None, ""))
                for i, (v, s) in enumerate(got):
                    parts.append((f"{v} for {_label(step_name(s['id'], by_id))}", s["id"],
                                  _count({f"overall verdict@{s['id']}": v}, v, _label(step_name(s["id"], by_id)), kind="record")))
                    parts.append(("." if i == len(got) - 1 else " and " if i == len(got) - 2 else ", ", None, ""))
            else:
                parts += [("", s["id"]) for s in judges]
        stage("Verdicts", parts)

    # The key claims the writer tagged with their passages, as numbers are tagged (`judge.claims`)
    claimed = [(s, len(records.get(s["id"], {}).get("claims") or [])) for s in of_kind("claims")]
    stage("Claims", [(f"The writer tagged {k} key claim{'' if k == 1 else 's'} that rest{'s' if k == 1 else ''} on no count, as each number is "
                      "tagged: each names the passages for it and against it, how they would be found again and why they "
                      "bear it out, and fixed rules checked that every passage named is one the coding holds." if k else
                      "The writer tagged no claim.", s["id"], _count({f"key claims tagged@{s['id']}": k})) for s, k in claimed])

    # The writing, and what code checked in it
    writing = []
    for s in of_kind("write"):
        made = "counts" + (" and verdicts" if judges else "")
        beside = stated_beside(R)
        writing.append(("The AI wrote the answer before citing it, and fixed rules put beside each number it gave the count its "
                        "citations make, refusing to create the report while any differed." if cited and beside is None else
                        "The AI wrote the answer referring to each count rather than writing the number, and fixed rules put in "
                        "the count its citations make" + (f", checking the {beside} numbers the AI also wrote beside one "
                        "and refusing to create the report while any differed" if beside else "") + "." if cited else
                        f"Rubicon wrote the answer from these {made}, citing for each finding the passages it rests on.",
                        s["id"], _count({"numbers stated beside their count": beside}) if cited and beside else ""))
    rp = R.get("report") or {}
    # the passages as the checks box counts them (`nrows_of`), with those found nowhere, which are dropped from the rows
    quotes = nrows_of(R) + found_nowhere(R)
    exact = nrows_of(R) - placed_approximately(R)
    numbers = (rp.get("answer") or {}).get("counts_written_by_id")
    said = (rp.get("answer") or {}).get("quotations_in_the_answer")
    checked = lambda n: _count({"numbers counted": n or 0, "passages given": quotes,
                                "quotations found word for word": exact, "quotations in the answer": said})
    if numbers == 0:  # an answer that states no count: nothing to say was computed, only what was found
        found = f"all {quotes}" if exact == quotes else f"{exact} of the {quotes}"
        writing.append((" The answer states no count" + (f"; {found} {'cited' if cited else 'coded'} passages were found word "
                        "for word in their documents" if quotes else "")
                        + (f", and every quotation in the answer, {said} in all, was found in the documents" if said else "")
                        + ".", None, checked(0)))
    elif numbers is not None:
        found = f"all {quotes}" if exact == quotes else f"{exact} of the {quotes}"
        writing.append(((f" Every count in the answer, {numbers} in all, was computed directly from {from_said('the cited passages', from_facts)}" if cited
                         else f" Every number in the answer, {numbers} in all, was {computed_said(from_facts)}")
                        + (f", and {found} {'cited' if cited else 'coded'} passages were found word for word in their documents" if quotes else "")
                        + (f"; every quotation in the answer, {said} in all, was found in the documents" if said else "")
                        + ".", None, checked(numbers)))
    stage("Writing and checks", writing)

    revised = [l for l in R.get("revisions", "").splitlines() if l.strip().startswith("- ")]
    if revised:
        stage("Revisions", [(f"The report was revised {_times(len(revised))} after it was first created, and counted and "
                             f"checked again{' each time' if len(revised) > 1 else ''}; the changes are listed at the end of this annex.", "revisions",
                             _count({"revisions": len(revised)}))])

    left = [s["id"] for s in steps if s["id"] not in done]
    if left:
        raise ValueError(f"no words for the steps {', '.join(left)}, so the explanation would leave them out")
    return stages


def stated_beside(R) -> int | None:
    """How many of the answer's counts the writer also wrote as a number beside the count's reference, which code
    checked against it; None where every count was, as in every run recounted before this was recorded."""
    a = (R.get("report") or {}).get("answer") or {}
    n = a.get("counts_stated_beside")
    return None if n is None or n >= a.get("counts_written_by_id", 0) else n


def second_coded(R):
    """Whether the run's check followed a second coding: rows a second coder gave, or a record of who coded a second
    time. A check alone, the evaluator's other choice, records only who checked. A run that records neither is older
    than that choice, when every check followed a second coding."""
    readers = R.get("readers") or {}
    return any(R.get("recoded", {}).values()) or "second_coding" in readers or not readers


def separate(R, part):
    """Whether a separate reader did this part of the second reading ("second_coding" or "check"), as the run records
    it in `readers.json`: True, False where the first reader did it, None where the run does not say. The analyst model
    writes that file, so a report gives it only as the analyst's record, once (`readers_said`)."""
    said = str((R.get("readers") or {}).get(part, "")).strip().lower()
    return True if said == "separate" else False if said == "same" else None


#: The second coding, said alike whoever did it
SECOND = "The same documents were coded again to the same definitions."
#: Whoever made the check, or ruled where the two codings differed
READER = "A reader"
#: Each part of the second reading, by the name a reader sees and the measure of whether a separate reader did it
PART = {"second_coding": "the second coding", "check": "the check"}
MEASURE_OF_SEPARATE = {"second_coding": "second coder separate", "check": "check reader separate"}
#: What the analyst's record says of each part, as `separate` reads it
RECORD_SAYS = {
    True: {"second_coding": "a separate coder did the second coding, briefed not to open the first coding",
           "check": "a separate reader made the check"},
    False: {"second_coding": "it did the second coding itself, so that coding is not independent of the first",
            "check": "it made the check itself"},
    None: {"second_coding": "nothing of who did the second coding", "check": "nothing of who made the check"}}


def readers_said(R: dict, parts: list[str]) -> str:
    """Who did each part of the second reading the run holds ("second_coding", "check"), said once in a report and
    only as the analyst's record: the analyst model writes `readers.json`, and the run does not record anything fixed
    rules could check it against, such as what a helper was given or read."""
    if not R.get("readers"):
        return (f" The run does not record whether a separate reader did {' or '.join(PART[p] for p in parts)}, so "
                + ("it is not" if len(parts) == 1 else "neither is") + " called independent here.")
    seps = [separate(R, p) for p in parts]
    said = " The analyst's record says " + ", and ".join(RECORD_SAYS[s][p] for s, p in zip(seps, parts))
    if True in seps:
        said += "; the run does not record what " + ("either one" if seps.count(True) > 1 else "it") + " read"
    return said + "."
#: How `compare.py`'s disagreements.md names the columns it compared, so a record that lists no difference proves it looked
COMPARED = "Compared by fixed rules:"
#: What it says instead where the two codings share no column it can compare, every coded column being free text
COMPARED_NOTHING = ("Fixed rules compared nothing: every column the two codings share is free text, so the check compares "
                    "their passages by reading.")


def compared_by_rules(column: dict) -> bool:
    """Whether fixed rules compare two codings' values of this column: every type but free text, which no two coders
    write alike. The one test for `compare.py`, the second coder's call on each passage and what the annex says."""
    return column.get("type") != "free_text"


def code_columns(workflow: dict) -> tuple[list[str], list[str]]:
    """The code steps' columns, as `step.column`: those fixed rules compare between two codings, and the free-text
    ones they do not."""
    cols = [(f"{s['id']}.{c['name']}", compared_by_rules(c)) for s in (workflow or {}).get("steps") or []
            if s.get("kind") == "code" for c in s.get("columns") or []]
    return [k for k, y in cols if y], [k for k, y in cols if not y]



def compared(R: dict) -> tuple[bool, bool]:
    """Whether the run's comparison of the two codings (`compare.py`'s disagreements.md) looked, naming what it compared,
    and whether it compared nothing, every column the codings share being free text. A record made before it said what
    it compared compared the workflow's columns fixed rules compare."""
    listed = R.get("disagreements") or ""
    looked, nothing = bool(re.search(rf"(?m)^{COMPARED}", listed)), COMPARED_NOTHING in listed
    if listed and not (looked or nothing):
        comparable = bool(code_columns(R.get("workflow"))[0])
        looked, nothing = comparable, not comparable
    return looked, nothing


def _ruled(R: dict) -> int | None:
    first, other, unsettled = (_parsed(R.get("check") or "", w) for w in ("ruled for the rows", "ruled for the second coder", "unsettled"))
    return None if None in (first, other) else first + other + (unsettled or 0)


#: What the account of the check is told from, each from the run's records: compare.py's comparison where the run
#: keeps it, and otherwise the check's own record, whose counts are its reader's
MEASURES_OF_THE_CHECK = {
    "places raised": lambda R: (len(re.findall(r"(?m)^- \*\*", R["disagreements"])) if R.get("disagreements")
                                else _parsed(R.get("check") or "", "disagreements")),
    "places ruled on": _ruled,
    "places ruled for the first coding": lambda R: _parsed(R.get("check") or "", "ruled for the rows"),
    "places ruled for the second coding": lambda R: _parsed(R.get("check") or "", "ruled for the second coder"),
    "places left unsettled": lambda R: _parsed(R.get("check") or "", "unsettled"),
    "definitions tightened": lambda R: _parsed(R.get("check") or "", "definitions (?:tightened|changed)"),
    "omissions searched": lambda R: bool(re.search(r"(?mi)^## .*omission", R.get("check") or "")),
}

_CHECK_MD = "the check's record, check.md, under its Counts heading"
_READERS = "the run's record of who read it, check/readers.json"
_COMPARE = "compare.py's comparison of the two codings, check/disagreements.md"
for _measure, _maker, _source, _figure in [
    ("sentences changed", "reader", _CHECK_MD, sentences_changed),
    ("places ruled on", "reader", _CHECK_MD, _ruled),
    ("places ruled for the first coding", "reader", _CHECK_MD, MEASURES_OF_THE_CHECK["places ruled for the first coding"]),
    ("places ruled for the second coding", "reader", _CHECK_MD, MEASURES_OF_THE_CHECK["places ruled for the second coding"]),
    ("places left unsettled", "reader", _CHECK_MD, MEASURES_OF_THE_CHECK["places left unsettled"]),
    ("places the check's record says differed", "reader", _CHECK_MD, lambda R: _parsed(R.get("check") or "", "disagreements")),
    ("definitions tightened", "reader", _CHECK_MD, MEASURES_OF_THE_CHECK["definitions tightened"]),
    ("omissions searched", "reader", "the check's record, check.md, a heading on omissions", MEASURES_OF_THE_CHECK["omissions searched"]),
    ("check reader separate", "reader", _READERS, lambda R: separate(R, "check")),
    ("second coder separate", "reader", _READERS, lambda R: separate(R, "second_coding")),
    ("second coded", "reader", "check/readers.json and the second coder's rows, check/coded/", second_coded),
    ("places the codings differed", "fixed rules", _COMPARE,
     lambda R: len(re.findall(r"(?m)^- \*\*", R["disagreements"])) if R.get("disagreements") else None),
    ("comparison kept", "fixed rules", _COMPARE, lambda R: bool(R.get("disagreements"))),
    ("comparison looked", "fixed rules", _COMPARE, lambda R: compared(R)[0]),
    ("comparison compared nothing", "fixed rules", _COMPARE, lambda R: compared(R)[1]),
    ("free-text codes", "fixed rules", "the workflow's code columns", lambda R: bool(code_columns(R.get("workflow"))[1])),
    ("numbers stated beside their count", "fixed rules", "the recount, recount/report.json", stated_beside),
]:
    claims.measure(_measure, _maker, _source, (lambda g: lambda R, D=None: g(R))(_figure))
del _measure, _maker, _source, _figure


def _defined(R: dict, sid: str) -> dict:
    """A step as the run's workflow defines it."""
    return next((s for s in (R.get("workflow") or {}).get("steps") or [] if s.get("id") == sid), {})


def _record(R: dict, sid: str) -> dict:
    """A step's record, as the recount wrote it."""
    return (R.get("steps") or {}).get(sid) or {}


def nrows_of(R: dict) -> int:
    """How many passages the run coded, each counted once: a code step that puts other codings' passages together
    (`combines`) codes nothing, so its rows are its inputs' again. The one count of coded passages, which the checks box,
    the annex's checks and the procedure in words all give."""
    return sum(len(s.get("rows", [])) for s in R["steps"].values() if s.get("kind") == "code" and not s.get("combines"))


def _codings_counted(R: dict) -> list[dict]:
    """The recount's record of each coding but those that only put others together, as `nrows_of` counts them."""
    return [v for v in ((R.get("report") or {}).get("coding") or {}).values() if not v.get("combines")]


def placed_approximately(R: dict) -> int:
    """How many of those passages the recount placed in their document only approximately."""
    return sum(v.get("quotations_placed_approximately", 0) for v in _codings_counted(R))


def found_nowhere(R: dict) -> int:
    """How many passages a coding gave that the recount found in no document, and left out of the rows."""
    return sum(len(v.get("quotations_not_found", [])) for v in _codings_counted(R))


def _drawn(R: dict, sid: str):
    documents = _record(R, sid).get("documents")
    return None if documents is None else len(documents)


def _assigned(R: dict, sid: str) -> tuple:
    """(how many, out of how many) a grouping that assigns gave a theme, as its record counts them: passages, or with
    several key columns each passage's labels; (None, None) where the record holds no count."""
    rec = _record(R, sid)
    a = (rec.get("checks") or {}).get("assigned") or {}
    if "rows_given_an_item" not in a:
        return None, None
    if "labels_given_no_item" in a:
        return a["rows_given_an_item"], a["rows_given_an_item"] + a["labels_given_no_item"]
    return (a["rows_given_an_item"], len(rec["table"])) if isinstance(rec.get("table"), list) else (None, None)


def _factors(R: dict, sid: str):
    s = _defined(R, sid)
    ends = next((c for c in s.get("columns") or [] if c.get("name") == (s.get("links") or {}).get("from")), {})
    return len(ends["values"]) if isinstance(ends.get("values"), list) else 0


def _verdicts(R: dict, sid: str):
    """The verdict on each question a judgement asks, as `told` gives them: the record's criteria, else the workflow's."""
    crits = _record(R, sid).get("criteria") or _defined(R, sid).get("criteria") or []
    return [c["verdict"] for c in crits if c.get("question") and c.get("verdict")]


_WORKFLOW = "the run's workflow, workflow.json"
_STEPS = "the record of each step, recount/steps/"
for _measure, _source, _figure, _takes in [
    ("documents drawn", "the sample's record of the documents it drew, recount/steps/", lambda R, D, sid: _drawn(R, sid), True),
    ("writer's record of what it read kept", "the writer's own record of what it read, work/read.json",
     lambda R, D: R.get("read") is not None, False),
    ("factors listed", _WORKFLOW + ", a link coding's list of factors", lambda R, D, sid: _factors(R, sid), True),
    ("themes at most", _WORKFLOW + ", a grouping's most themes", lambda R, D, sid: _defined(R, sid).get("max_items"), True),
    ("given a theme", _STEPS + ", the rows a grouping gave a theme", lambda R, D, sid: _assigned(R, sid)[0], True),
    ("to be given a theme", _STEPS + ", the rows a grouping placed", lambda R, D, sid: _assigned(R, sid)[1], True),
    ("tables", _WORKFLOW, lambda R, D: len([s for s in (R.get("workflow") or {}).get("steps") or [] if s.get("kind") == "tabulate"]), False),
    *((counted, _WORKFLOW, (lambda c: lambda R, D: len(next(ss for _, k, ss in _tables_by_kind((R.get("workflow") or {}).get("steps") or [])
                                                             if k == c)))(counted), False)
      for _, counted, _ in _tables_by_kind([])),
    ("verdicts", _STEPS + ", a judgement's criteria", lambda R, D, sid: _verdicts(R, sid), True),
    ("overall verdict", _STEPS + ", a judgement's overall verdict", lambda R, D, sid: _record(R, sid).get("overall"), True),
    ("key claims tagged", _STEPS + ", the key claims the writer tagged",
     lambda R, D, sid: len(_record(R, sid).get("claims") or []), True),
    ("revisions", "the run's revisions, revisions.md",
     lambda R, D: len([l for l in (R.get("revisions") or "").splitlines() if l.strip().startswith("- ")]), False),
]:
    claims.measure(_measure, "fixed rules", _source, _figure, takes=_takes)
del _measure, _source, _figure, _takes
