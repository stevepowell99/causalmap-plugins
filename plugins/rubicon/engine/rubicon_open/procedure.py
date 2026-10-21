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

from . import legacy_weak
from .steps import unit_of_table
from .workflow import key_columns

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
    return "s-howdone-" + re.sub(r"[^a-z0-9]+", "-", sid.lower()).strip("-")


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
    t = re.split(r"(?<=[.!?])\s", str(text or "").strip(), maxsplit=1)[0].rstrip(".")
    if len(t) > most:
        t = re.split(r"[:;]\s", t, maxsplit=1)[0]
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


def told(R: dict, steps: list[dict]) -> list[dict]:
    """The procedure as stages, each {"title", "steps", "parts"}: `parts` is the paragraph as (text, step id or None)
    pieces, a piece with a step id linking to that step's part of the annex. `steps` is the list the x-ray draws."""
    records = R.get("steps", {})
    by_id = {s["id"]: s for s in steps}
    n = len(R.get("index", []))
    stages, done = [], set()

    def stage(title, parts):
        done.update(p[1] for p in parts if p[1])
        parts = [p for p in parts if p[0]]
        if parts:
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
             else f"Rubicon read all {n} documents in full." if n and not samples else "", None)]
    for i, s in enumerate(samples):
        drawn = records.get(s["id"], {}).get("documents")
        where = s.get("where") or {}
        kept = (" among those with " + _listed([f"{_by(k, set())} {_listed([str(x) for x in (v if isinstance(v, list) else [v])])}"
                                               for k, v in where.items()])) if where else ""
        how = "chosen by name" if s.get("documents") else "drawn at random" if s.get("n") else "chosen"
        spread = f", spread across {_by(s['stratify_by'], set())}" if s.get("stratify_by") else ""
        count = f"{len(drawn)} of the {n} documents" if drawn is not None and n else "a sample of the documents"
        read.append(((" " if i else "") + f"Rubicon read {count} in full, {how}{kept}{spread}.", s["id"]))
    if len(units) == 1 and alone and n:
        read.append((f" The counts below are of {next(iter(units))}, one document each.", None))
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
                           "own quotation and the coding it came from.", s["id"]))
            continue
        if s.get("cited"):
            labels = _listed([_label(c.get("name")) for c in cols])
            coding.append((f"{lead} cited, for the numbers in its answer, the passages each rests on, each labelled with its {labels}. "
                           "So every count rests only on the passages cited: fixed rules found each one word for word in its "
                           "document and counted the documents they come from, but did not check that every passage bearing "
                           "on a point was cited, or that each was filed under the right point or speaker.", s["id"]))
            continue
        if links:
            ends = next((c for c in cols if c.get("name") == links.get("from")), {})
            vals = ends.get("values") if isinstance(ends.get("values"), list) else []
            listed = f", each end one of a list of {len(vals)} factors" if vals else ""
            sign = ", and whether the effect goes up or down" if links.get("sign") else ""
            rest = [c for c in cols if c.get("name") not in (links.get("from"), links.get("to"), links.get("sign"))]
            more = f", also {verb} {what(rest)}" if rest else ""
            did = f"{lead} restated each causal claim the documents make as a link from a cause to an effect{listed}{sign}{more}."
        elif s.get("per_document"):
            did = f"{lead} read each document as a whole and {verb} {what(cols)}."
        else:
            did = f"{lead} marked every passage that bears on the question and {verb} {what(cols)}."
        if isinstance(s.get("from"), dict):
            did += " " + earlier_said(R, s)
        coding.append((did, s["id"]))
    for s in of_kind("group"):
        most = f" at most {s['max_items']}" if s.get("max_items") else ""
        key = f" of {' and '.join(_label(k) for k in key_columns(s))}" if s.get("key_column") else ""
        coding.append((f" It grouped the answers{key} into{most} themes, which became a codebook"
                       + (", and placed each passage under one of them." if s.get("assign") else "."), s["id"]))
    if legacy_weak.in_report(R) and any(c.get("weak") for s in codes for c in s.get("columns") or []):  # legacy_weak
        coding.append((" A passage that only implies a code, in the way the code's definition names, was marked implicit "
                       "and counted apart from the passages that say it explicitly.", None))
    stage("Coding", coding)

    # The second coding and the check, where the run holds them
    second = []
    if "second_coding" in by_id:
        second.append((SECOND_SAID[separate(R, "second_coding")], "second_coding"))
    if "check" in by_id and not second_coded(R):
        second.append((f"{CHECKER_ALONE[separate(R, 'check')]} then read the answer against the passages it cites and "
                       "the documents, and checked every sentence and quotation, so the coding and the answer in this "
                       "report are the corrected ones, counted again after the check.", "check"))
    elif "check" in by_id:
        check, listed = R.get("check", ""), R.get("disagreements", "")
        # the comparison of the two codings, or for an older zip without it the check's own count, where it gives one
        raised = len(re.findall(r"(?m)^- \*\*", listed)) if listed else _parsed(check, "disagreements")
        first, other, unsettled = (_parsed(check, w) for w in ("ruled for the rows", "ruled for the second coder", "unsettled"))
        ruled = None if None in (first, other) else first + other + (unsettled or 0)
        if raised == 0 and (listed or check):
            said = "The two codings agreed on every document and code."
        elif raised:
            took = f", taking them as {ruled} disagreements" if ruled is not None and ruled != raised else ""
            said = (f"The two codings differed in {raised} places. {CHECKER[separate(R, 'check')]} ruled on each against the text{took}"
                    + (f": {first} for the first coding, {other} for the second"
                       + (f", and {unsettled} that the definitions as written did not settle" if unsettled else "")
                       if ruled is not None else "") + ".")
        else:
            said = f"{CHECKER[separate(R, 'check')]} ruled on every place the two codings differed, against the text."
        tightened = _parsed(check, "definitions (?:tightened|changed)")
        if tightened:
            said += (f" It tightened {tightened} definition{'s' if tightened > 1 else ''} as a result, and corrected "
                     "the coding to match.")
        if re.search(r"(?mi)^## .*omission", check):
            said += " It searched the documents each count leaves out for passages both coders had missed, and added them."
        said += (" It also checked every sentence and quotation of the answer against the documents, so the coding and "
                 "the answer in this report are the corrected ones, counted again after the check.")
        second.append(((" " if second else "") + said, "check"))
    stage("Second coding and check" if "second_coding" in by_id else "Checking", second)

    # The profiles: what each unit's passages hold together, which the tables after them count
    profiled = []
    for s in of_kind("profile"):
        key = s.get("key", "case")
        unit = "case" if key == "case" else "document" if key == "document" else _label(key)
        profiled.append(((" " if profiled else "") + f"Fixed rules brought together, for each {unit}, everything coded in any of its "
                         f"passages and documents, and recorded {_listed([_profiled(c) for c in s.get('columns') or []])}"
                         + (", so a count can join what one person says in different places." if key == "case" else "."), s["id"]))

    # The counting, from the coded passages and the document list, the unit said once where the tables share one: each
    # table listed where there are few, and where there are many, how many tables and maps, each opening its section
    if profiled and not tables:
        stage("Counting", profiled)
    if tables:
        coded = {c.get("name") for s in codes for c in s.get("columns") or []}
        links = {s["id"]: s.get("links") for s in codes}
        shared = {unit_of_table(rec(s)) for s in tables}
        unit = f" {next(iter(shared))}" if len(shared) == 1 else ""
        lead = (unit.strip()[:1].upper() + unit.strip()[1:]) if unit else "The coded passages"
        k = len(tables)
        if k > MANY_TABLES:
            def is_map(s):
                ends = links.get((s.get("inputs") or [s.get("input")])[0])
                return bool(ends) and list(s.get("by") or [])[:2] == [ends.get("from"), ends.get("to")] and not s.get("loops")
            kinds = [("table", [s for s in tables if not (is_map(s) or s.get("loops"))]),
                     ("causal map", [s for s in tables if is_map(s)]),
                     ("table of feedback loops", [s for s in tables if s.get("loops")])]
            kinds = [(name, ss) for name, ss in kinds if ss]
            said = lambda name, ss: f"{WORDS.get(len(ss), len(ss)) if name != 'table' else len(ss)} {name}{'s' if len(ss) > 1 else ''}"
            parts = [(f"{lead} were then counted in ", None), (said(*kinds[0]), kinds[0][1][0]["id"]),
                     (", compared by these codings", None)]
            rest = kinds[1:]
            for j, (name, ss) in enumerate(rest):
                sep = ", and drawn in " if j == 0 else " and " if j == len(rest) - 1 else ", "
                parts += [(sep, None), (said(name, ss), ss[0]["id"])]
            parts.append((". The annex below gives each.", None))
            parts += [("", s["id"]) for s in tables]
        else:
            parts = [(f"{lead} were then counted in {k} table{'s' if k > 1 else ''}: ", None)]
            for i, s in enumerate(tables):
                said = _table(rec(s), links.get((s.get("inputs") or [s.get("input")])[0]), coded)
                parts.append((said if unit else f"{unit_of_table(rec(s))} {said}", s["id"]))
                parts.append(("." if i == k - 1 else "; ", None))
        stage("Counting", profiled + ([(" ", None)] if profiled else []) + parts)

    # The verdicts, each by the rule its criteria set
    if judges:
        sources = {s.get("source", "").strip().rstrip(".") for s in judges}
        one = next(iter(sources))
        source = f" They come from {one[:1].lower() + one[1:]}." if len(sources) == 1 and one else ""
        how = {"rule": "the answer was counted from the tables and set against the thresholds the rule gives",
               "stated": "a number a background document states was set against the thresholds the rule gives",
               "reading": "the coded passages were read against the description of each level the rule gives"}
        parts = [(f"Rubicon reached its verdicts by rules agreed beforehand.{source}", None)]
        if len(judges) == 1:
            s = judges[0]
            r = records.get(s["id"], {})
            crits = r.get("criteria") or s.get("criteria") or []
            kinds = list(dict.fromkeys(c["kind"] for c in crits if c.get("kind") in how))
            if len(kinds) == 1:
                parts.append((f" For each question the rule asks, {how[kinds[0]]}"
                              + (":" if any(c.get("verdict") for c in crits) else "."), None))
            each = (lambda c: "") if len(kinds) == 1 else (lambda c: f" ({BRIEFLY.get(c.get('kind'), 'as the rule sets out')})")
            asked = [f" “{c['question'].strip()}”{each(c)} reached {c['verdict']}" for c in crits
                     if c.get("question") and c.get("verdict")]
            parts.append((";".join(asked) + "." if asked else "", s["id"]))
            if r.get("overall"):
                parts.append((f" The overall verdict was {r['overall']}.", s["id"]))
            parts.append(("", s["id"]))
        else:
            crits = [c for s in judges for c in (records.get(s["id"], {}).get("criteria") or s.get("criteria") or [])]
            kinds = list(dict.fromkeys(how[c["kind"]] for c in crits if c.get("kind") in how))
            first = next((c["question"].strip() for c in crits if c.get("question")), "")
            if kinds:
                parts.append((f" For each question a rule asks, such as “{first}”, " + "; ".join(kinds) + ".", None))
            got = [(records.get(s["id"], {}).get("overall"), s) for s in judges]
            if all(v for v, _ in got):
                parts.append((" The verdicts reached were ", None))
                for i, (v, s) in enumerate(got):
                    parts.append((f"{v} for {_label(re.sub(r'^[a-z]_', '', s['id']))}", s["id"]))
                    parts.append(("." if i == len(got) - 1 else " and " if i == len(got) - 2 else ", ", None))
            else:
                parts += [("", s["id"]) for s in judges]
        stage("Verdicts", parts)

    # The key claims the writer tagged with their passages, as numbers are tagged (`judge.claims`)
    claimed = [(s, len(records.get(s["id"], {}).get("claims") or [])) for s in of_kind("claims")]
    stage("Claims", [(f"The writer tagged {k} key claim{'' if k == 1 else 's'} that rest{'s' if k == 1 else ''} on no count, as each number is "
                      "tagged: each names the passages for it and against it, how they would be found again and why they "
                      "bear it out, and fixed rules checked that every passage named is one the coding holds." if k else
                      "The writer tagged no claim.", s["id"]) for s, k in claimed])

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
                        s["id"]))
    rp = R.get("report") or {}
    coding = (rp.get("coding") or {}).values()
    missing = sum(len(v.get("quotations_not_found", [])) for v in coding)
    quotes = sum(v.get("rows", 0) for v in coding) + missing  # a passage found nowhere is dropped from the rows
    exact = quotes - missing - sum(v.get("quotations_placed_approximately", 0) for v in coding)
    numbers = (rp.get("answer") or {}).get("counts_written_by_id")
    said = (rp.get("answer") or {}).get("quotations_in_the_answer")
    if numbers == 0:  # an answer that states no count: nothing to say was computed, only what was found
        found = f"all {quotes}" if exact == quotes else f"{exact} of the {quotes}"
        writing.append((" The answer states no count" + (f"; {found} {'cited' if cited else 'coded'} passages were found word "
                        "for word in their documents" if quotes else "")
                        + (f", and every quotation in the answer, {said} in all, was found in the documents" if said else "")
                        + ".", None))
    elif numbers is not None:
        found = f"all {quotes}" if exact == quotes else f"{exact} of the {quotes}"
        writing.append(((f" Every count in the answer, {numbers} in all, was computed directly from the cited passages" if cited
                         else f" Every number in the answer, {numbers} in all, was computed directly from the coded "
                         "passages rather than written by the AI")
                        + (f", and {found} {'cited' if cited else 'coded'} passages were found word for word in their documents" if quotes else "")
                        + (f"; every quotation in the answer, {said} in all, was found in the documents" if said else "")
                        + ".", None))
    stage("Writing and checks", writing)

    revised = [l for l in R.get("revisions", "").splitlines() if l.strip().startswith("- ")]
    if revised:
        stage("Revisions", [(f"The report was revised {_times(len(revised))} after it was first created, and counted and "
                             f"checked again{' each time' if len(revised) > 1 else ''}; the changes are listed at the end of this annex.", "revisions")])

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
    it in `readers.json`: True, False where the first reader did it, None where the run does not say. Only True lets a
    report call the second coding blind or independent."""
    said = str((R.get("readers") or {}).get(part, "")).strip().lower()
    return True if said == "separate" else False if said == "same" else None


#: The second coding, said as the record of who did it allows
SECOND_SAID = {
    True: "A second coder then coded the same documents again to the same definitions, without seeing the first coding.",
    False: "The reader who made the first coding then coded the same documents again to the same definitions, so this "
           "second coding is not independent of the first.",
    None: "The same documents were coded again to the same definitions; the run does not record whether a separate "
          "coder did it, so it is not called independent here."}
#: Who ruled where the two codings differed
CHECKER = {True: "A third reader", False: "The reader who made the first coding", None: "A reader"}
#: Who checked, where the check was the whole second reading
CHECKER_ALONE = {True: "A separate reader", False: "The reader who made the coding", None: "A reader"}
