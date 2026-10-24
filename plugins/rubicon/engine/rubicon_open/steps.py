"""The pieces' work that needs no model (`rubicon/docs/pieces.md`): drawing a sample, placing coded rows in their
documents, tabulating, and checking an answer's counts, citations and quotations against them. Each takes the run and
its step, and returns the step's record.

Every check that can pass by finding nothing says what it looked at: a coding step reports the sections it read and
any whose reply could not be read, and an answer's check reports the citations and quotations it checked.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import legacy_weak, locator, node
from .corpus import Corpus
from .judge import level_counts
from .units import COUNTS, count_said, unit_noun
from .workflow import CODING, LOOP_COLUMNS, order_of, SEQUENCE_COLUMNS, arrow, canonical, codebook_of, column_values, combining, derived, item_columns, key_columns, links_ending, loop_markers, resolve_step, sign_of, value_key


#: How a tabulation names its cells. By coordinates, the id is the step's and the values of its `by` columns in square
#: brackets, joined by commas: `t[income up,MNX]`. It names the same cell whatever its count or place in the table, so
#: a citation survives a revision that reorders the table, and one naming a cell the table no longer holds is refused.
#: A run made before cells were named that way keeps `positional` ids (`t.c3`, the place in the table by count), which
#: only its own recount reproduces.
CELL_IDS = ("coordinates", "positional")
#: What a coordinate keeps as written: letters, digits, space and the few marks that no reader of an answer, markdown or
#: HTML would take for syntax. Anything else is written as its UTF-8 bytes in %XX, so a value holding a comma, a bracket,
#: a full stop (which would end a sentence or open a suffix) or a quotation mark still parses, and `%` itself is escaped.
_PLAIN = re.compile(r"[\w \-~;()/+#→–]")
#: A count's id as an answer writes it between braces: a step's id, then either a dotted name (`t.of`, `j.reach.good`,
#: a positional `t.c3`) or a cell's coordinates with the suffix `.within.<column>` (or, in a run made before 15 October
#: 2026, `.weak`: `legacy_weak`) that follows either form
COUNT_ID = r"[\w-]+(?:\.[\w.-]+|\[[^\[\]{}\n]*\](?:\.[\w.-]+)?)"


def _coordinate(value) -> str:
    out = "".join(ch if _PLAIN.fullmatch(ch) else "".join(f"%{b:02X}" for b in ch.encode("utf-8")) for ch in str(value))
    if out.startswith(" "):
        out = "%20" + out[1:]
    if out.endswith(" "):
        out = out[:-1] + "%20"
    return out


def cell_id(sid: str, by: list[str], values: dict) -> str:
    """A tabulation cell's id by its coordinates: the step's, then the values of its `by` columns in order."""
    return f"{sid}[{','.join(_coordinate(values[b]) for b in by)}]"


def step_of(count_id: str) -> str:
    """The step a count's id belongs to."""
    return re.match(r"[\w-]+", count_id).group()


def reply_list(got) -> list[dict]:
    """A reply asked for as a list of objects, as one: a list as it is, and a lone object as a list of one, which is
    how a reader asked for one object in a list most often answers (a fifth of whole-document readings, 5 October
    2026). Any other shape raises, so the caller records the reading as unread rather than as one that found nothing."""
    if isinstance(got, dict):
        return [got]
    if isinstance(got, list):
        return [g for g in got if isinstance(g, dict)]
    raise ValueError(f"the reply is {type(got).__name__}, not a list of objects")


def parse_json(text: str):
    text = re.sub(r"^```\w*\n|\n```$", "", text.strip())
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not starts:
        raise ValueError("no JSON in the reply")
    return json.JSONDecoder().raw_decode(text[min(starts):])[0]  # the first complete value; anything after it is ignored


@dataclass
class Run:
    folder: Path
    corpus: Corpus
    question: str
    ask: Callable[..., str]
    out: dict[str, dict] = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)  # the workflow, so a step can read what the others define
    # readings the analyst made and recorded, by judge step and criterion id (`judged/<step id>.json`), which a judge
    # takes in place of asking a model, so a run that calls none can still carry a criterion that cannot be counted;
    # and by claims step and claim id, the claims the writer tagged (`judge.claims`)
    readings: dict[str, dict] = field(default_factory=dict)
    # how a tabulation names its cells (`cell_id`): by their coordinates, or, for a run recounted before cells were named
    # that way, by their place in the table (`positional`); a run's workflow records which (`cell_ids`)
    cell_ids: str = "coordinates"
    # a run made before 15 October 2026, whose rows the coder may have marked weak (`legacy_weak`)
    legacy_weak: bool = False

    def attribute(self, doc: str, name: str):
        return attribute_of(self.corpus, doc, name)

    def is_attribute(self, name: str) -> bool:
        return name.lower() in {c.lower() for c in self.corpus.columns}

    def table(self, sid: str) -> list[dict]:
        return table_of(self.out, sid)


def table_of(out: dict[str, dict], sid: str) -> list[dict]:
    """The rows a step stands for, from the records of a run's steps by id (a run's own as it goes, or a recount's as
    recorded): a code step's, or those of the group step that assigned them items."""
    rec = out[sid]
    if rec.get("table") is not None:
        return rec["table"]
    assigned = [r for r in out.values() if r.get("kind") == "group" and r.get("input") == sid and r.get("table")]
    return assigned[-1]["table"] if assigned else rec["rows"]


def attribute_of(corpus: Corpus, doc: str, name: str):
    """A document's value of one column of the document list, the column named in any case."""
    cols = corpus.documents[doc]["columns"]
    return next((v for k, v in cols.items() if k.lower() == name.lower()), None)


def draw(corpus: Corpus, s: dict, pool: list[str] | None = None) -> dict:
    """The documents a sample step takes, worked out the same way for the run and for its price, from `pool`, the
    documents of the sample it draws from, or every document where it draws from the documents. A fixed list
    (`documents`) is taken as it stands, an id the corpus lacks said. Otherwise `where` ({column: value or list of
    values}) keeps the documents the question concerns, and a seeded draw of `n` cases among them (`Corpus.case_of`),
    spread across the values of `stratify_by` in turn where it is set, takes every document of each case drawn, so a
    case is never split; it takes them all where `n` is not given or is at least as many. Where every case is one
    document, as in most corpora, a case is drawn exactly as its document was before cases were drawn."""
    s = resolve_step(s, "sample")
    if s["documents"] is not None:
        return {"documents": sorted(d for d in s["documents"] if d in corpus.documents),
                "documents_not_found": sorted(d for d in s["documents"] if d not in corpus.documents)}
    docs = sorted(corpus.documents if pool is None else pool)
    if s["where"]:
        wanted = {k: {value_key(x) for x in (v if isinstance(v, list) else [v])} for k, v in s["where"].items()}
        docs = [d for d in docs if all(value_key(attribute_of(corpus, d, k)) in vs for k, vs in wanted.items())]
        if not docs:  # a filter that keeps nothing is a fault in the workflow, never an empty answer
            raise ValueError(f"{s.get('id', 'sample')}: no document has {s['where']}")
    of_case: dict[str, list[str]] = {}
    for d in docs:
        of_case.setdefault(corpus.case_of(d) if hasattr(corpus, "case_of") else d, []).append(d)
    cases = sorted(of_case)
    n = len(cases) if s["n"] is None else min(int(s["n"]), len(cases))
    if n == len(cases):
        return {"documents": docs, **({"where": s["where"]} if s["where"] else {})}
    rng = random.Random(s["seed"])
    if s["stratify_by"]:
        strata = defaultdict(list)
        for c in cases:
            values = {str(attribute_of(corpus, d, s["stratify_by"]) or "") for d in of_case[c]}
            strata[values.pop() if len(values) == 1 else ""].append(c)
        for v in strata.values():
            rng.shuffle(v)
        chosen, order = [], sorted(strata)
        while len(chosen) < n:
            for v in order:
                if strata[v] and len(chosen) < n:
                    chosen.append(strata[v].pop())
    else:
        chosen = rng.sample(cases, n)
    # drawn_from: how many cases the seeded draw took these from, which only a draw at random records
    return {"documents": sorted(d for c in chosen for d in of_case[c]), "drawn_from": len(cases),
            **({"where": s["where"]} if s["where"] else {})}


def sample(run: Run, s: dict) -> dict:
    src = s["inputs"][0]
    return draw(run.corpus, s, None if src == "documents" else run.out[src]["documents"])


def _entries(values: list) -> list[dict]:
    """A column's own values as codebook items, in the shape a group step writes; a bare name carries no definition."""
    out = []
    for v in values:
        if isinstance(v, dict):
            name = str(v.get("name") or v.get("id") or "")
            given = v.get("does_not_count") or []
            nots = [n if isinstance(n, dict) else {"text": str(n)} for n in ([given] if isinstance(given, (str, dict)) else given)]
            out.append({"id": name, "label": name, "means": v.get("means", ""), "counts": v.get("counts", ""), "does_not_count": nots})
        else:
            out.append({"id": str(v), "label": str(v)})
    return out


def values_allowed(run: Run, cols: list[dict]) -> dict[str, list[str] | None]:
    """Each column's values, as the rows hold them: a codebook's item ids (with "OTHER" where a group step made it),
    a column's own list, or a binary column's two (`workflow.BINARY`); None where the column takes any value."""
    out = {}
    for c in cols:
        items = codebook_items(run, c)
        out[c["name"]] = ([it["id"] for it in items] + (["OTHER"] if codebook_of(c) else [])) if items is not None else column_values(c)
    return out


def codebook_items(run: Run, column: dict) -> list[dict] | None:
    """What a nominal or ordinal column is coded against: a group step's items, or the column's own values as items."""
    g = codebook_of(column)
    if g:
        return run.out[g]["codebook"]["items"]
    return _entries(column["values"]) if isinstance(column.get("values"), list) else None


#: Letters and digits a row id is written in, without those read for one another (i and l and 1, o and 0).
ROW_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def row_id(step: str, document: str, start, end, taken=()) -> str:
    """A row's id: its step's, then five characters drawn from its document and the span of its passage, so the id
    stays the same when other rows are added, removed or recoded, and an answer's citations keep pointing at the same
    passages. A second row on the same span takes a suffix."""
    n = int.from_bytes(hashlib.sha1(f"{document}\0{start}\0{end}".encode()).digest()[:8], "big")
    base = f"{step}." + "".join(ROW_ALPHABET[(n // len(ROW_ALPHABET) ** i) % len(ROW_ALPHABET)] for i in range(5))
    rid, k = base, 2
    while rid in taken:
        rid, k = f"{base}-{k}", k + 1
    return rid


def code_documents(run: Run, s: dict) -> list[str]:
    """The documents a code step reads: every document, or those its input samples took."""
    ins = s["inputs"]
    docs = sorted(run.corpus.documents) if "documents" in ins else sorted({d for i in ins for d in run.out[i]["documents"]})
    # a step whose rows were taken from an earlier run reads only what that run read, so a document it never read is
    # not counted here as read and found to hold nothing (`earlier.resolve`)
    there = (s.get("from") or {}).get("documents") if isinstance(s.get("from"), dict) else None
    return docs if there is None else sorted(set(docs) & set(there))


def placing(text_of, step: str, docs: list[str], quotes: dict[str, list[str]]):
    """Each quotation of `quotes` (by document, in the order given) placed as a code step's rows are placed: as
    (document, its index in that document's list, where it was found or None, its row id or None), each document's in
    the order its passages stand in it, which is the order the page shows a step's rows in. The one place a row's id
    is given, so a tool that changes a row already cited finds it by the id the engine gave it."""
    taken = set()
    for d in docs:
        found = locator.locate_all(text_of(d), quotes.get(d, []))
        for k, h in sorted(enumerate(found), key=lambda x: -1 if x[1] is None else x[1].start):
            rid = None
            if h is not None:
                rid = row_id(step, d, h.start, h.end, taken)
                taken.add(rid)
            yield d, k, h, rid


def place_rows(run: Run, s: dict, docs: list[str], cols: list[dict], results: list[tuple]) -> dict:
    """The rows each reading of a section gave, placed: each quotation found in its document (and dropped, and listed,
    where it is not), each row given its id, and each value stored in its column's one spelling. A column filled from
    a mapping (`workflow.derived`) takes its value from the column it names, whatever the row gave, and a value of that
    column the mapping does not hold leaves it blank and is listed. `results` holds one (document, section index,
    rows, error or None, read again) per reading."""
    allowed = values_allowed(run, cols)
    maps = {c["name"]: (f[0], {value_key(k): v for k, v in f[1].items()}) for c in cols if (f := derived(c))}
    unmapped: dict[str, set] = defaultdict(set)
    rows, dropped, unread, off, missing, unquoted = [], [], [], 0, 0, 0
    by_doc = defaultdict(list)
    retried = [{"document": d, "section": i + 1, "read": not err} for d, i, _, err, again in results if again]
    for d, i, got, err, _ in results:
        if err:
            unread.append({"document": d, "section": i + 1, "error": err})
        quoted = [(i, r) for r in got if isinstance(r, dict) and str(r.get("quote") or "").strip()]
        unquoted += len(got) - len(quoted)
        by_doc[d] += quoted
    for d, k, h, rid in placing(run.corpus.text, s["id"], docs, {d: [str(r["quote"]) for _, r in by_doc[d]] for d in docs}):
        i, r = by_doc[d][k]
        if h is None:
            dropped.append({"document": d, "quote": r["quote"]})
            continue
        quote = h.quote
        row = {"row": rid, "document": d, "section": i + 1, "quote": quote, "tier": h.tier,
               "start": h.start, "end": h.end}
        if r.get(legacy_weak.MARK) is True and legacy_weak.reads(run):  # the one door for the old mark
            row[legacy_weak.MARK] = True
        if str(r.get("sequence") or "").strip():  # one of the links a speaker tells as one chain, and its place in it
            row["sequence"] = str(r["sequence"]).strip()
            if re.fullmatch(r"\s*\d+\s*", str(r.get("step", ""))):
                row["step"] = int(r["step"])
        for c in cols:
            given = r.get(c["name"])
            if c["name"] in maps:
                src, mapping = maps[c["name"]]
                given = mapping.get(value_key(row.get(src)))
                if given is None and row.get(src) not in (None, ""):
                    unmapped[c["name"]].add(str(row[src]))
            v = row[c["name"]] = canonical(given, allowed[c["name"]])
            if v in (None, ""):
                missing += 1
            elif allowed[c["name"]] and v not in allowed[c["name"]]:
                off += 1
        rows.append(row)
    return {"rows": rows, "sections_unread": unread, "sections_retried": retried, "quotations_dropped": dropped,
            "values_off_the_list": off, "values_missing": missing, "rows_without_a_quotation": unquoted,
            **({"values_not_mapped": {k: sorted(v) for k, v in unmapped.items()}} if unmapped else {})}


def code_record(run: Run, s: dict, docs: list[str], cols: list[dict], placed: dict, sections_read: int,
                reconciled: dict | None = None, checked: dict | None = None) -> dict:
    """A code step's record, from its placed rows (`place_rows`, with whatever a second reading changed in them); a
    per-document step's values are added to the document list for the steps after it."""
    rows, retried = placed["rows"], placed["sections_retried"]
    described = _describe_documents(run, docs, rows, cols) if s["per_document"] else None
    return {**({"document_attributes": described} if described is not None else {}), "documents": docs, "columns": cols, "sections_read": sections_read, "sections_unread": placed["sections_unread"],
            **({"sections_retried": retried} if retried else {}), "rows": rows,
            "quotations_dropped": placed["quotations_dropped"], "values_off_the_list": placed["values_off_the_list"],
            "values_missing": placed["values_missing"], "rows_without_a_quotation": placed["rows_without_a_quotation"],
            **({"values_not_mapped": placed["values_not_mapped"]} if placed.get("values_not_mapped") else {}),
            **({"reconciled": reconciled} if reconciled is not None else {}),
            **({"check": checked} if checked is not None else {})}


def code_given(run: Run, s: dict, given: dict[str, list[dict]]) -> dict:
    """A code step carried out on rows coded elsewhere, `given` holding each document's: placed exactly as a model's
    rows are, with each document counted as one section read."""
    s = resolve_step(s, "code")
    docs = code_documents(run, s)
    cols = s.get("columns") or []
    results = [(d, 0, list(given.get(d, [])), None, False) for d in docs]
    return code_record(run, s, docs, cols, place_rows(run, s, docs, cols, results), len(docs))


def combines(run: Run, s: dict) -> bool:
    """Whether a code step puts other code steps' rows together (`workflow.combining`) rather than coding documents."""
    return combining(s, {st.get("id"): st for st in run.steps})


def combined(run: Run, s: dict) -> dict:
    """A code step whose inputs are code steps: their rows put together as one table, by code, with no model. Every row
    keeps its own id, passage and values and gains `coding`, the step it was coded in, so a citation points at the same
    passage and a count can be followed back through either coding. The columns are those the inputs share
    (`workflow.combined_from`); a row from a coding without one of them has it blank, and the record says which. Values
    are stored in each column's one spelling; one outside a column's list is kept, counted and listed, never dropped
    or recoded: putting two codings' labels on one codebook is a soft recode, a group step's, made over this table. The documents are those
    any input read, and the record lists, for each input, those it did not, since a count out of all of them is then
    out of more than that coding saw."""
    cols = s.get("columns") or []
    allowed = values_allowed(run, cols)
    rows, off, missing, taken = [], defaultdict(int), 0, set()
    read: dict[str, list[str]] = {}
    lacks: dict[str, list[str]] = {}
    for i in s["inputs"]:
        rec = run.out[i]
        own = {c["name"] for c in rec.get("columns") or []}
        read[i] = list(rec.get("documents") or sorted({r["document"] for r in rec["rows"]}))
        for c in cols:
            if c["name"] not in own:
                lacks.setdefault(c["name"], []).append(i)
        for r in rec["rows"]:
            if r["row"] in taken:
                raise ValueError(f"{s['id']}: the row {r['row']} is in two of the codings it puts together, so a citation of it would be ambiguous")
            taken.add(r["row"])
            row = {**r, CODING: i}
            for c in cols:
                if c["name"] not in own:
                    continue
                v = row[c["name"]] = canonical(r.get(c["name"]), allowed[c["name"]])
                if v in (None, ""):
                    missing += 1
                elif allowed[c["name"]] and v not in allowed[c["name"]]:
                    off[(i, c["name"], str(v))] += 1
            rows.append(row)
    every = sorted(set().union(*read.values()))
    return {"combines": list(s["inputs"]), "documents": every, "columns": cols, "sections_read": 0, "sections_unread": [], "rows": rows,
            "rows_by_coding": {i: sum(r[CODING] == i for r in rows) for i in s["inputs"]},
            "documents_not_read_by_every_coding": {i: sorted(set(every) - set(d)) for i, d in read.items() if set(every) - set(d)},
            "columns_not_in_every_coding": lacks,
            "quotations_dropped": [], "values_off_the_list": sum(off.values()),
            "values_off_the_list_by": [{"coding": i, "column": c, "value": v, "rows": n} for (i, c, v), n in sorted(off.items())],
            "values_missing": missing, "rows_without_a_quotation": 0}


# --- group ------------------------------------------------------------------------------------------------------

def label_units(rows: list[dict], keys: list[str]) -> list[dict]:
    """What a group step finds one codebook for: each label a row carries in a key column. With one key column a unit is
    the row itself (its id the row's); with several, such as a link's cause and effect, one row carries a label in each
    and each belongs to its own item, so the unit is the label in its column and its id the row's, an `@` and the column.
    A row with no label in a key column has no unit for it."""
    one = len(keys) == 1
    return [{"unit": r["row"] if one else f"{r['row']}@{k}", "row": r, "column": k, "label": str(r.get(k) or "").strip()}
            for r in rows for k in keys if str(r.get(k) or "").strip()]


def codebook_checks(run: Run, units: list[dict], every: list[dict], book: dict, accounted: set) -> dict:
    """The trail of a codebook, whoever drew it: every unit accounted for (`accounted`, the units it names, placed or
    left over), none named that is not there, every near miss pointing at an item, every example found in its
    document."""
    rows = {u["row"]["row"] for u in units}
    items = {it.get("id"): it for it in book.get("items", [])}
    ids = {u["unit"] for u in units}
    return {"rows": len(rows), "rows_without_this_column": len(every) - len(rows), "labels": len({u["label"] for u in units}),
            "items": len(items), **({"labels_in_all": len(units)} if len({u["column"] for u in units}) > 1 else {}),
            "rows_unaccounted": sorted(ids - accounted),
            "rows_invented": sorted(accounted - ids - {None}),
            "near_misses_pointing_nowhere": [(i, n.get("goes_to")) for i, it in items.items()
                                             for n in it.get("does_not_count", []) if isinstance(n, dict)
                                             and n.get("goes_to") not in items and n.get("goes_to") is not None],
            "examples_not_found": [e.get("quote") for it in items.values() for e in it.get("examples", [])
                                   if e.get("document") not in run.corpus.documents
                                   or locator.locate_all(run.corpus.text(e["document"]), [e.get("quote", "")])[0] is None]}


def assigned_table(units: list[dict], rows: list[dict], keys: list[str], items: set, got: dict) -> list[dict]:
    """The rows carrying a label, each with its item beside the label (a soft recode), `got` giving each unit's
    {"item", and where a model placed it, "fit"}: in `item` for one key column, "none" where it has no item; for several
    in `<column>_item` for each, left blank where it has none, since a table of links traced through its items must not
    join every unplaced label as one factor called "none"."""
    if len(keys) > 1:
        by_unit = {(u["row"]["row"], u["column"]): got[u["unit"]] for u in units}
        return [{**r, **{f"{k}_item": (by_unit[r["row"], k]["item"] if by_unit[r["row"], k]["item"] in items else None)
                         for k in keys if (r["row"], k) in by_unit}} for r in rows]
    return [{**r, "item": got[r["row"]]["item"], **({"fit": got[r["row"]]["fit"]} if "fit" in got[r["row"]] else {})} for r in rows]


def group_given(run: Run, s: dict, book: dict) -> dict:
    """A group step carried out on a codebook drawn elsewhere, by the analyst who coded the open labels, as `code_given`
    carries out a code step on rows coded elsewhere; nothing is asked of a model. `book` is the hosted grouping model's
    codebook, {"items": [{"id", "label", "means", "counts", "does_not_count": [{"text", "goes_to"}], "examples", ...}],
    "unplaced", "notes"}, with each item naming the open labels it gathers in `from_labels`, and any single row placed
    apart from the rest of its label in `from_rows`. A label left over goes in "unplaced" as {"label", "reason"}.
    Each unit (`label_units`) takes the item its row names, else the item its label is listed under; a label or row
    listed under two items takes neither and is said. An example may name its row alone; its document and quotation are
    then that row's. Each item's `from_rows` and `documents` are then the units it holds, as code placed them. Where the
    step assigns, the table is its input's rows with each one's item (`assigned_table`)."""
    s = resolve_step(s, "group")
    src = s["inputs"][0]
    keys = key_columns(s)
    every = run.table(src)
    units = label_units(every, keys)
    rows = list({u["row"]["row"]: u["row"] for u in units}.values())
    by_row = {r["row"]: r for r in every}
    items = [dict(it) for it in book.get("items", []) if isinstance(it, dict) and it.get("id")]
    ids = {it["id"] for it in items}
    unplaced = [u for u in book.get("unplaced", []) if isinstance(u, dict)]
    by_label, by_unit = defaultdict(set), defaultdict(set)
    for it in items:
        for lab in it.get("from_labels") or []:
            by_label[value_key(lab)].add(it["id"])
        for uid in it.get("from_rows") or []:
            by_unit[uid].add(it["id"])
    left_labels = {value_key(u["label"]) for u in unplaced if u.get("label")}
    left_units = {u["row"] for u in unplaced if u.get("row")}
    carried = {value_key(u["label"]) for u in units}
    got, accounted, two = {}, set(), set()
    for u in units:
        lab = value_key(u["label"])
        placed = by_unit.get(u["unit"]) or by_label.get(lab) or set()
        if u["unit"] in by_unit or lab in by_label or u["unit"] in left_units or lab in left_labels:
            accounted.add(u["unit"])
        if len(placed) > 1:
            two.add(u["unit"] if u["unit"] in by_unit else u["label"])
        got[u["unit"]] = {"item": next(iter(placed)) if len(placed) == 1 else "none"}
    accounted |= (set(by_unit) | left_units) - {u["unit"] for u in units}  # named, but no such unit: invented
    for it in items:
        held = [u for u in units if got[u["unit"]]["item"] == it["id"]]
        it["from_rows"] = [u["unit"] for u in held]
        it["documents"] = len({u["row"]["document"] for u in held})
        it["examples"] = [{**e, "document": by_row[e["row"]]["document"], "quote": by_row[e["row"]]["quote"]}
                          if not e.get("quote") and str(e.get("row", "")).split("@")[0] in by_row else e
                          for e in (it.get("examples") or []) if isinstance(e, dict)]
    book = {**book, "items": items}
    checks = codebook_checks(run, units, every, book, accounted)
    checks.update({"labels_unaccounted": sorted({u["label"] for u in units if u["unit"] not in accounted}),
                   "labels_invented": sorted({lab for it in items for lab in it.get("from_labels") or []
                                              if value_key(lab) not in carried}
                                             | {u["label"] for u in unplaced if u.get("label") and value_key(u["label"]) not in carried}),
                   "placed_under_two_items": sorted(two),
                   "items_pointing_at_no_item": sorted(it["id"] for it in items if it.get("opposite_of") not in (None, "", *ids))})
    rec = {"input": src, "codebook": book, "checks": checks, "table": None}
    if s["assign"]:
        rec["table"] = assigned_table(units, rows, keys, ids, got)
        sizes = defaultdict(int)
        for g in got.values():
            sizes[g["item"]] += 1
        rec["checks"]["assigned"] = {"rows_given_an_item": sum(g["item"] in ids for g in got.values()),
                                     "largest_item_share": round(max(sizes.values()) / len(got), 2) if got else 0,
                                     **({"labels_given_no_item": sum(g["item"] not in ids for g in got.values())} if len(keys) > 1 else {})}
        if len(keys) > 1:  # one key column's is `item`, as every record has always said
            rec["item_columns"] = item_columns(s)
    return rec


def links_of(run: Run, sid: str) -> dict | None:
    """The link ends of what a tabulation reads (`workflow.links_ending`): the workflow says them, so a group step that
    assigns items is read the same here, in the procedure and in the report."""
    return links_ending(run.steps, sid)


def _describe_documents(run: Run, docs: list[str], rows: list[dict], cols: list[dict]) -> dict:
    """A per-document step's values, added to the document list for the steps after it: each document takes its first
    row's value in each column. A document without a row is left blank, which a tabulation counts as "(blank)", and one
    with rows that disagree is listed, so neither passes as a document the coder placed."""
    first: dict[str, dict] = {}
    disagree = set()
    for r in rows:
        if r["document"] in first:
            if any(str(r.get(c["name"])) != str(first[r["document"]].get(c["name"])) for c in cols):
                disagree.add(r["document"])
            continue
        first[r["document"]] = r
    names = [c["name"] for c in cols]
    for name in names:
        if name.lower() not in {c.lower() for c in run.corpus.columns}:
            run.corpus.columns.append(name)
    for d in docs:
        for name in names:
            v = first.get(d, {}).get(name)
            run.corpus.documents[d]["columns"][name] = None if v in (None, "") else str(v)
    return {"columns": names, "values": {d: {n: run.corpus.documents[d]["columns"][n] for n in names} for d in docs},
            "documents_without_a_row": sorted(set(docs) - set(first)), "documents_with_rows_that_disagree": sorted(disagree)}


def in_context(run: Run, r: dict, width: int = 700) -> str:
    """A coded passage in the text around it, the passage marked, so a reader can see who, when and in answer to what."""
    text, a, b = run.corpus.text(r["document"]), r["start"], r["end"]
    return ("…" + locator._utf16_slice(text, max(0, a - width), a) + ">>>" + locator._utf16_slice(text, a, b) + "<<<"
            + locator._utf16_slice(text, b, b + width) + "…")


def _unit_of_row(run: Run, count: str, r: dict):
    """The unit a row belongs to, for a tabulation counting `count`: its document, its case (`Corpus.case_of`), or for
    a count by a column of the document list that column's value for its document, None where it has none. A
    profile's row is its own unit."""
    if "key" in r:
        return r["key"]
    if count == "documents":
        return r["document"]
    if count in ("cases", "rows"):
        # a run given no document list (a test's, say) has no cases but its documents
        return run.corpus.case_of(r["document"], r.get("case")) if hasattr(run.corpus, "case_of") else r["document"]
    v = run.attribute(r["document"], count)
    return None if v in (None, "") else str(v)


def units(run: Run, count: str, read, rows: list[dict]) -> tuple[dict[str, set[str]], dict[str, str]]:
    """The units a tabulation counts among the documents `read`, each with the documents it appears in, and the unit
    of each of `rows` (the input code step's, by row id). Cases come from `Corpus.cases_held`; a count by a column of
    the document list has a case for each of its values among the documents read, a document with none in none."""
    unit_of = {r["row"]: _unit_of_row(run, count, r) for r in rows}
    if rows and "key" in rows[0]:  # a profile's units, each with those of its documents among `read`
        read = set(read)
        return {r["key"]: set(r["documents"]) & read for r in rows if not r["documents"] or set(r["documents"]) & read}, unit_of
    if count == "documents" or count == "rows":
        return {d: {d} for d in read}, unit_of
    if count == "cases" and hasattr(run.corpus, "cases_held"):
        return run.corpus.cases_held(read, rows), unit_of
    if count == "cases":
        return {d: {d} for d in read}, unit_of
    held: dict[str, set[str]] = {}
    for d in read:
        if (u := _unit_of_row(run, count, {"document": d})) is not None:
            held.setdefault(u, set()).add(d)
    return held, unit_of


def tabulate(run: Run, s: dict) -> dict:
    s = resolve_step(s, "tabulate")
    src = s["inputs"][0]
    if src == "documents" or run.out.get(src, {}).get("kind") == "sample":  # the document list, one row a document
        docs = sorted(run.corpus.documents) if src == "documents" else run.out[src]["documents"]
        rows = [{"row": d, "document": d} for d in docs]
        read = docs
    else:
        rows = run.table(src)
        rec = run.out[src]  # "of" is the documents the coding read, including those that gave no row
        read = rec.get("documents") or run.out.get(rec.get("input"), {}).get("documents") or {r["document"] for r in rows}
    profiled = run.out.get(src, {}).get("kind") == "profile"  # a profile's rows are its units, each built from passages
    coded_rows = rows  # every row the input coded, before any filter: the cases read are worked out from them
    if s.get("where"):  # only the rows the step names are counted; the cases read, and so every base, are all of them
        listed = values_allowed(run, (run.out.get(src) or {}).get("columns") or [])
        rows = rows_where(run, rows, s["where"], s.get("id", "tabulate"), listed)
    filtered = None
    filters = s["filters"]
    if filters or is_map(run, src, s):
        # a map of causal links combines opposites by default; where no end was flipped and the step set no filters
        # of its own, the rows are counted as they were coded, so a table without opposites is unchanged
        got, applied, did = filter_links(run, src, rows, filters, map=is_map(run, src, s))
        if filters or any(r.get("flipped_cause") or r.get("flipped_effect") for r in got):
            rows, filtered, filters = got, did, applied
    by, count = s["by"], s["count"]
    # legacy_weak: in a run made before 15 October 2026, a cell counts its firm rows, or the units with one; rows the
    # coder marked weak are counted beside them, as the units (or rows) the cell holds only through weak rows. In a new
    # run every row is firm, and a column called weak is a column like any other.
    weak = {r["row"] for r in rows if legacy_weak.carries(legacy_weak.reads(run), r)}
    if s["loops"]:
        ends = links_of(run, src)
        by, cells = list(LOOP_COLUMNS), _loops(rows, ends, s["loop_links"], s["through"], weak)
    elif s.get("sequences"):
        by, cells = list(SEQUENCE_COLUMNS), _sequences(rows, by, weak)
    else:
        cells = _paths(run, rows, by, weak) if s["paths"] else _combinations(run, rows, by)
    # every combination the columns allow is a cell, so a count of none is stated as 0 rather than left out; a sparse
    # table, such as causal links from one factor list crossed with itself, lists only the combinations that occur
    in_rows = {k for r in rows for k in r}
    sparse = s["sparse"] or s["paths"] or s["loops"] or s.get("sequences") or bool(filtered)  # a filter can rename a factor, so no codebook lists its values
    if not sparse:
        domains = [_domain(run, src, c, read, c in in_rows) or sorted({k[i] for k in cells} - {"(blank)"}) for i, c in enumerate(by)]
        for cmb in itertools.product(*domains):
            cells.setdefault(cmb, {"documents": set(), "rows": []})
    # what the table counts (`units`): a cell's count is of the units its rows belong to, and its base the units among
    # those read that share its values on every column describing a document, so a count by kind of submitter is out of
    # that kind; counting the document list itself, every cell is out of all those read
    listing = src == "documents" or run.out.get(src, {}).get("kind") == "sample"
    whole = base_columns(by, in_rows, run.is_attribute, listing, bool(s["loops"] or s.get("sequences")))
    held, unit_of = units(run, count, read, [] if listing else coded_rows)
    unit_of.update({r["row"]: unit_of.get(r["row"], _unit_of_row(run, count, r)) for r in rows})

    def of_unit(u, c):
        docs = held[u]
        if c == "document":
            return docs
        vs = {run.attribute(d, c) for d in docs}
        v = vs.pop() if len(vs) == 1 else None
        return {"(blank)" if v in (None, "") else str(v)}

    def matches(u, cmb, cols):
        return all(cmb[i] in of_unit(u, by[i]) for i in cols)

    def base(cmb):
        return None if count == "rows" else sum(matches(u, cmb, whole) for u in held)

    def of_rows(ids):
        return list(ids) if count == "rows" else {unit_of[x] for x in ids if unit_of.get(x) is not None}

    def firm(v):  # a composite cell (path, told chain, loop) names the rows that make it firm itself: it is as firm as its weakest link
        return of_rows([x for x in v["rows"] if (x in v["firm"] if "firm" in v else x not in weak)])

    # a count can also be stated within the group a coded column defines ("of those improved, 13 of 15"): its base is
    # then the units with that value in that column, as well as the cell's values on the columns describing a document
    def units_with(i, v):
        return {u for (k, c) in cells.items() if k[i] == v for u in firm(c)}
    coded = [i for i, c in enumerate(by) if i not in whole and re.fullmatch(r"[\w-]+", c)] if count != "rows" and len(by) > 1 and not s["loops"] else []
    marginal = {(i, k[i]): units_with(i, k[i]) for k in cells for i in coded}

    def within(cmb):
        return {by[i]: sum(matches(u, cmb, whole) for u in marginal[(i, cmb[i])]) for i in coded}
    # where opposites were combined, a cell says how many of its rows had each end coded at the opposite pole, which
    # the map colours the arrow's tail and head by
    flips = {(r["row"], *(str(r.get(c)) for c in by)): r for r in rows if r.get("flipped_cause") or r.get("flipped_effect")} if filtered else {}

    def flipped(k, v):
        hit = [flips.get((x, *k), {}) for x in v["rows"]]
        return {"flipped": {"cause": sum(bool(f.get("flipped_cause")) for f in hit),
                            "effect": sum(bool(f.get("flipped_effect")) for f in hit)}} if flips else {}
    out = [{"values": dict(zip(by, k)), "n": len(firm(v)), "base": base(k), "within": within(k),
            **({"weak": len(of_rows(v["rows"])) - len(firm(v))} if weak else {}),
            **flipped(k, v), "documents": sorted(v["documents"]),
            **({"firm_rows": v["firm"]} if "firm" in v else {}),
            **({"cases": sorted(of_rows(v["rows"]))} if count not in ("documents", "rows") else {}), "rows": v["rows"]}
           for k, v in cells.items()]
    if not s["loops"]:  # a loop's cells stay together, the loop's own first, in the order the loops were ranked
        out.sort(key=lambda c: (-c["n"], list(c["values"].values())))
    if profiled:  # a cell walks back to the passages its units were built from, as any cell does
        built = {r["row"]: r["rows"] for r in coded_rows}
        for c in out:
            c["rows"] = list(dict.fromkeys(x for p in c["rows"] for x in built.get(p, [])))
    for k, c in enumerate(out, 1):  # an id per count, which the answer writes in place of the number
        c["id"] = f"{s['id']}.c{k}" if run.cell_ids == "positional" else cell_id(s["id"], by, c["values"])
    alone = count == "documents" or all(len(ds) == 1 for ds in held.values()) and len(held) == len(read)
    return {"input": src, "by": by, "count": count, "unit": unit_noun(count, s.get("unit"), alone),
            **({"description": s["description"]} if s.get("description") else {}),
            **({"cases_are_documents": alone} if count == "cases" else {}),
            "of": len(held) if count != "rows" else len(read), "sparse": sparse, "paths": s["paths"],
            **({"loops": True} if s["loops"] else {}), **({"sequences": True} if s.get("sequences") else {}),
            **({"filters": filters, "filtered": filtered} if filtered else {}), **({"where": s["where"]} if s.get("where") else {}),
            "cells": out}


PROFILE_KINDS = ("holds", "values", "distinct", "first", "last")


def profile_kind(column: dict) -> str | None:
    """Which of the profile's kinds of column a definition is: the one of `PROFILE_KINDS` it names, None for none or
    several."""
    named = [k for k in PROFILE_KINDS if k in column]
    return named[0] if len(named) == 1 else None


def profile_columns(run: Run, src: str, s: dict, read) -> list[dict]:
    """A profile's columns as a coded column is defined, so a tabulation counts them as it counts any column: `holds`
    binary, `values`, `first` and `last` taking the values of the column they read (`_domain`), `distinct` a number."""
    out = []
    for c in s["columns"]:
        k = profile_kind(c)
        if k == "holds":
            out.append({"name": c["name"], "type": "binary"})
        elif k == "distinct":
            out.append({"name": c["name"], "type": "numeric"})
        else:
            dom = _domain(run, src, c[k], read, True)
            out.append({"name": c["name"], "type": "nominal" if dom else "free_text", **({"values": dom} if dom else {})})
    return out


def profile(run: Run, s: dict) -> dict:
    """One row for each unit a key names, described by what that unit's coded rows hold together, by code and with no
    model, so a count can span passages: a case whose context and outcome are told in different passages, a claim
    reported by more than one kind of source, an actor named in several documents. The key is the case (the default,
    `Corpus.case_of`), the document, a column of the document list, or a column the input coded, such as an actor or a
    group step's item. Every unit among the documents read is a row, so one with no coded row is a row of noes and
    counts as a zero; a key the input coded has a row for every value its column can take. Each column is one of
    `holds` (yes where any of the unit's rows has the values a `where` names), `values` (the values the unit's rows
    hold in a column, a list), `distinct` (how many different values of a column, coded or of the document list, the
    unit's rows carry), and `first` and `last` (a column's value in the unit's first and last row, ordered by the
    column `order` names, else by where the rows stand in the text). Each row carries its documents and the passages
    it was built from, so a count of profiled units walks back to quotations as a count of passages does."""
    s = resolve_step(s, "profile")
    src = s["inputs"][0]
    rows = run.table(src)
    rec = run.out[src]
    read = sorted(rec.get("documents") or run.out.get(rec.get("input"), {}).get("documents") or {r["document"] for r in rows})
    key = s["key"]
    keyed: dict[str, list[dict]] = {}
    docs_of: dict[str, set[str]] = {}
    if key == "case":
        for c, ds in run.corpus.cases_held(read, rows).items():
            keyed[c], docs_of[c] = [], set(ds)
        for r in rows:
            keyed[run.corpus.case_of(r["document"], r.get("case"))].append(r)
    elif key == "document" or (run.is_attribute(key) and not any(key in r for r in rows)):
        for d in read:
            u = d if key == "document" else run.attribute(d, key)
            if u not in (None, ""):
                keyed.setdefault(str(u), [])
                docs_of.setdefault(str(u), set()).add(d)
        for r in rows:
            u = r["document"] if key == "document" else run.attribute(r["document"], key)
            if u not in (None, ""):
                keyed[str(u)].append(r)
    else:
        for u in _domain(run, src, key, read, True) or []:
            keyed[str(u)], docs_of[str(u)] = [], set()
        for r in rows:
            for u in value_of(run, r, key):
                if u not in (None, ""):
                    keyed.setdefault(str(u), []).append(r)
                    docs_of.setdefault(str(u), set()).add(r["document"])
    cols = s["columns"]
    listed = values_allowed(run, (run.out.get(src) or {}).get("columns") or [])
    wanted = {}
    for c in cols:  # a value no row holds and the column cannot take is a fault in the workflow, as in any where
        if profile_kind(c) == "holds":
            rows_where(run, rows, c["holds"], s["id"], listed)
            wanted[c["name"]] = {k: {value_key(x) for x in (v if isinstance(v, list) else [v])} for k, v in c["holds"].items()}

    def in_text(r):
        return (r["document"], r.get("start") or 0)

    def described(u, rs):
        out = {}
        for c in cols:
            k = profile_kind(c)
            if k == "holds":
                out[c["name"]] = "yes" if holding(run, rs, wanted[c["name"]]) else "no"
            elif k == "values":
                out[c["name"]] = sorted({str(v) for r in rs for v in value_of(run, r, c["values"]) if v not in (None, "")})
            elif k == "distinct":
                out[c["name"]] = str(len({value_key(v) for r in rs for v in value_of(run, r, c["distinct"]) if v not in (None, "")}))
            else:
                placed = rs
                if c.get("order"):
                    ranks = order_of([v for r in rs for v in value_of(run, r, c["order"])], _column(run, src, c["order"]))
                    at = dict(ranks[1]) if ranks else {}
                    placed = [r for r in rs if str(value_of(run, r, c["order"])[0]) in at]
                    placed.sort(key=lambda r: (at[str(value_of(run, r, c["order"])[0])], in_text(r)))
                else:
                    placed = sorted(rs, key=in_text)
                pick = placed[0] if k == "first" and placed else placed[-1] if placed else None
                v = None if pick is None else value_of(run, pick, c[k])[0]
                out[c["name"]] = None if v in (None, "") else str(v)
        return out
    table = []
    for i, u in enumerate(sorted(keyed), 1):
        rs = keyed[u]
        table.append({"row": f"{s['id']}.k{i}", "key": u, key: u, "documents": sorted(docs_of.get(u, set())),
                      "rows": [r["row"] for r in rs], **described(u, rs)})
    return {"input": src, "key": key, "columns": profile_columns(run, src, s, read), "documents": read, "rows": table,
            "checks": {"units": len(table), "units_with_no_row": sum(not t["rows"] for t in table)}}


def _column(run: Run, src: str, name: str) -> dict | None:
    """A column as the code step behind `src` defines it."""
    rec = run.out.get(src, {})
    coded = rec.get("input") if rec.get("kind") == "group" else src
    return next((c for c in run.out.get(coded, {}).get("columns") or [] if c.get("name") == name), None)


def value_of(run: Run, r: dict, c: str) -> list:
    """A row's values in column `c`, a list where it holds several: its own, else its document's id for `document`, else
    its document's value in the document list. A profile's row stands for its `documents`: their ids, and a value of
    the document list where they all agree."""
    docs = [r["document"]] if "document" in r else r.get("documents") or []
    if c in r:
        v = r[c]
    elif c == "document":
        v = docs if "document" not in r else r["document"]
    elif run.is_attribute(c):
        vs = {run.attribute(d, c) for d in docs}
        v = vs.pop() if len(vs) == 1 else None
    else:
        v = None
    return v if isinstance(v, list) else [v]


def rows_where(run: Run, rows: list[dict], where: dict, sid: str, listed: dict | None = None) -> list[dict]:
    """The rows whose value in each column `where` names ({column: value or list of values}) is one it gives, compared
    by `value_key`. A value the column can take (`listed`, from its definition) counts none where no row holds it; a
    value it neither lists nor holds is a fault in the workflow, since a table counting nothing would read as a finding
    of none."""
    wanted = {c: {value_key(x) for x in (v if isinstance(v, list) else [v])} for c, v in where.items()}
    for c, vs in wanted.items():
        if not (c == "document" or run.is_attribute(c) or c in ((listed or {}).keys()) or any(c in r for r in rows)):
            raise ValueError(f"{sid}: where names {c!r}, which its input does not have")
        held = {value_key("" if x is None else x) for r in rows for x in value_of(run, r, c)}
        held |= {value_key(x) for x in ((listed or {}).get(c) or [])}
        if missing := sorted(vs - held):
            raise ValueError(f"{sid}: where names {', '.join(map(repr, missing))} in {c!r}, which no passage holds")
    return holding(run, rows, wanted)


def holding(run: Run, rows: list[dict], wanted: dict[str, set[str]]) -> list[dict]:
    """The rows whose value in each column of `wanted` ({column: set of `value_key`s}) is one of its values."""
    return [r for r in rows if all(any(value_key("" if x is None else x) in vs for x in value_of(run, r, c))
                                   for c, vs in wanted.items())]


FILTER_SHIM = Path(__file__).resolve().parent / "filter_links.mjs"


def is_map(run: Run, src: str, s: dict) -> bool:
    """Whether a tabulation is a causal map: counted by the two ends of a code step's unsigned links and nothing else.
    A causal loop diagram's links carry a sign instead, and paths, told sequences and loops trace the links as coded."""
    ends = links_of(run, src)
    return bool(ends and not ends.get("sign") and list(s["by"]) == [ends["from"], ends["to"]]
                and not (s["paths"] or s["loops"] or s.get("sequences")))


def filter_links(run: Run, src: str, rows: list[dict], filters: list[dict], map: bool = False) -> tuple[list[dict], list[dict], dict]:
    """A code step's rows as Causal Map links, put through Causal Map's own filters in order (`cm/`, run under Node),
    and back as rows with the two ends as the filters left them. The conversion is `link-rows.js`, which the Rubicon
    page refilters a map with too: each row gives a link for every pair of its two link-end values (the code step's
    `links`), with its document as the link's source and the document's facts on the source, so a filter reads
    `s_<fact>` for one. With `map`, opposites are combined unless the filters already say how (`filter_links.mjs`).
    Returns the rows, the filters applied and what the filtering did."""
    ends = links_of(run, src)
    docs = sorted({r["document"] for r in rows})
    attributes = {d: dict(run.corpus.documents.get(d, {}).get("columns") or {}) for d in docs}
    got = node.call(FILTER_SHIM, {"rows": rows, "ends": ends, "filters": filters, "attributes": attributes, "map": map},
                    "link filters")
    if got["unsupported"]:
        raise ValueError(f"{', '.join(got['unsupported'])}: not a filter Causal Map's filter engine applies")
    return got["rows"], got["filters"], got["filtered"]


def _combinations(run: Run, rows: list[dict], by: list[str]) -> dict[tuple, dict]:
    """The combinations of the `by` columns' values the rows have, each holding its documents and rows: a row with a
    list in a column counts once under each of its values."""
    cells: dict[tuple, dict] = {}
    for r in rows:
        values = [value_of(run, r, c) for c in by]
        combos = [()]
        for vs in values:
            combos = [cmb + ("(blank)" if v in (None, "") else str(v),) for cmb in combos for v in vs]
        for cmb in combos:
            cell = cells.setdefault(cmb, {"documents": set(), "rows": []})
            cell["documents"].update([r["document"]] if "document" in r else r["documents"])
            cell["rows"].append(r["row"])
    return cells


def _paths(run: Run, rows: list[dict], by: list[str], weak: set[str]) -> dict[tuple, dict]:
    """The paths each document's own links make, found by Causal Map's own path tracing with source tracing on, so a
    path is never stitched across documents (`filter_links.mjs`, run under Node): a cell for every pair of values of
    the first two `by` columns (a link's two ends) where the second can be reached from the first by following one
    document's links, directly or through other values, holding the documents that make it and the links on those
    paths. Any further `by` columns describe the document. In a run made before 15 October 2026 (`legacy_weak`), a cell
    also holds `firm`, the links on paths made of unmarked links alone."""
    start, end, rest = by[0], by[1], by[2:]

    def values(r, c):
        return [str(x) for x in (r[c] if isinstance(r[c], list) else [r[c]]) if x not in (None, "")]

    # only the columns the tracing reads go to Node; legacy_weak: a marked row is tagged so a filter can leave it out
    slim = [{"row": r["row"], "document": r["document"], start: r.get(start), end: r.get(end), "tags": "implicit" if r["row"] in weak else ""}
            for r in rows]
    causes = sorted({x for r in slim for x in values(r, start)})
    effects = sorted({y for r in slim for y in values(r, end)})
    longest = max(len(set(causes) | set(effects)), 1)  # a path never repeats a value, so none is longer than the values there are
    pairs = [(x, y) for x in causes for y in effects if x != y]

    def trace(x, y):
        return {"type": "path-tracing", "fromLabels": [x], "toLabels": [y], "maxSteps": longest, "matchMode": "exact", "traceThreads": True}

    chains = [[trace(x, y)] for x, y in pairs]
    has_implicit = any(r["tags"] for r in slim)
    if has_implicit:
        chains += [[{"type": "exclude-tags", "selectedTags": ["implicit"], "matchMode": "exact"}, trace(x, y)] for x, y in pairs]
    got = node.call(FILTER_SHIM, {"rows": slim, "ends": {"from": start, "to": end}, "attributes": {}, "chains": chains}, "path tracing")
    unsupported = sorted({u for e in got["each"] for u in e["unsupported"]})
    if unsupported:
        raise ValueError(f"{', '.join(unsupported)}: not a filter Causal Map's filter engine applies")
    every = got["each"][:len(pairs)]
    firm = got["each"][len(pairs):] if has_implicit else every

    def by_document(kept):  # {document: [the ids of its rows on a path]}
        out: dict[str, list] = defaultdict(list)
        for rid, d in kept["rows"]:
            out[d].append(rid)
        return out

    cells: dict[tuple, dict] = {}
    for (x, y), on, firm_on in zip(pairs, every, firm):
        firm_by = by_document(firm_on)
        for d, ids in by_document(on).items():
            of_doc = [[d if c == "document" else (str(v) if (v := run.attribute(d, c)) not in (None, "") else "(blank)")] for c in rest]
            for cmb in itertools.product(*of_doc):
                cell = cells.setdefault((x, y) + cmb, {"documents": set(), "rows": [], "firm": []})
                cell["documents"].add(d)
                cell["rows"] += [rid for rid in ids if rid not in cell["rows"]]
                cell["firm"] += [rid for rid in firm_by.get(d, []) if rid not in cell["firm"]]
    return cells


def _sequences(rows: list[dict], by: list[str], weak: set[str]) -> dict[tuple, dict]:
    """The chains the speakers tell: the rows one document gives one "sequence", in the order of their "step" (then of
    the passages), written as the factors in the order told, a factor repeated straight after itself said once. A cell
    is one chain, holding the documents that tell it and its rows; chains are never put together across sequences or
    documents, so every cell is a chain somebody told as one."""
    start, end = by[0], by[1]

    def first(r, c):
        v = r.get(c)
        v = v[0] if isinstance(v, list) and v else v
        return None if v in (None, "") else str(v)

    told: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r.get("sequence"):
            told[(r["document"], r.get(CODING, ""), r["sequence"])].append(r)  # a label is one coding's own, never joined with another's
    cells: dict[tuple, dict] = {}
    for (d, _, _), links in sorted(told.items()):
        links.sort(key=lambda r: (r.get("step", 0), r.get("start") or 0))
        names = []
        for r in links:
            for v in (first(r, start), first(r, end)):
                if v and (not names or names[-1] != v):
                    names.append(v)
        cell = cells.setdefault((" → ".join(names),), {"documents": set(), "rows": [], "firm": []})
        cell["documents"].add(d)
        cell["rows"] += [r["row"] for r in links if r["row"] not in cell["rows"]]
        if not any(r["row"] in weak for r in links):  # legacy_weak: a chain is as firm as its weakest link
            cell["firm"] += [r["row"] for r in links if r["row"] not in cell["firm"]]
    return cells


def _loops(rows: list[dict], ends: dict, most: int, through: list[str], weak: set[str]) -> dict[tuple, dict]:
    """The feedback loops the coded links make, all documents' links combined: every loop of up to `most` links that
    visits no variable twice, through one of the variables `through` names where it names any. A link with two signs
    in the coding is two links, so one cycle of variables can be a reinforcing loop and a balancing one. Each loop
    gives a cell for itself, holding the documents whose own links make all of it; a cell for each of its links,
    holding the documents behind that link; and a cell for each link into it from a variable outside it."""
    def vals(r, c):
        v = r.get(c)
        return [str(x) for x in (v if isinstance(v, list) else [v]) if x not in (None, "")]
    edges: dict[tuple, dict] = {}
    for r in rows:
        sign = sign_of(r.get(ends.get("sign"))) if ends.get("sign") else "?"
        for a in vals(r, ends["from"]):
            for b in vals(r, ends["to"]):
                if a != b:
                    e = edges.setdefault((a, b, sign), {"documents": set(), "rows": []})
                    e["documents"].add(r["document"])
                    e["rows"].append(r["row"])
    nxt: dict[str, list] = defaultdict(list)
    for a, b, sign in sorted(edges):
        nxt[a].append((b, sign))
    names = sorted({x for a, b, _ in edges for x in (a, b)})
    rank = {x: i for i, x in enumerate(names)}
    want = {value_key(t) for t in through}
    found = []
    for start in names:  # each loop once, found from its variable that sorts first
        def walk(node, path):
            for b, sign in nxt[node]:
                if b == start:
                    found.append(path + [(node, b, sign)])
                elif rank[b] > rank[start] and len(path) + 1 < most and b not in {x for x, _, _ in path} | {node}:
                    walk(b, path + [(node, b, sign)])
        walk(start, [])
    loops = []
    for links in found:
        on = [x for x, _, _ in links]
        if want and not any(value_key(x) in want for x in on):
            continue
        signs = [sg for _, _, sg in links]
        polarity = "unknown" if "?" in signs else "R" if signs.count("-") % 2 == 0 else "B"
        whole = set.intersection(*(edges[k]["documents"] for k in links))
        loops.append((links, polarity, whole))
    loops.sort(key=lambda lp: (-len(lp[2]), -min(len(edges[k]["documents"]) for k in lp[0]), lp[0]))
    doc_of = {r["row"]: r["document"] for r in rows}
    cells: dict[tuple, dict] = {}
    for links, polarity, whole in loops:
        label = " ".join(f"{a} →{sg}" for a, _, sg in links) + f" {links[0][0]}"
        # a document tells the loop firmly only if every one of the loop's links has a firm row in that document
        firm_docs = {d for d in whole if all(any(doc_of[rid] == d and rid not in weak for rid in edges[k]["rows"]) for k in links)}
        cells[(label, polarity, "whole", "")] = {
            "documents": whole, "rows": [rid for k in links for rid in edges[k]["rows"] if doc_of[rid] in whole],
            "firm": [rid for k in links for rid in edges[k]["rows"] if doc_of[rid] in firm_docs and rid not in weak]}
        for k in links:
            cells[(label, polarity, "link", arrow(k[0], k[2], k[1]))] = {"documents": set(edges[k]["documents"]), "rows": list(edges[k]["rows"])}
        on = {a for a, _, _ in links}
        for k in sorted(k for k in edges if k[1] in on and k[0] not in on):
            cells[(label, polarity, "driver", arrow(k[0], k[2], k[1]))] = {"documents": set(edges[k]["documents"]), "rows": list(edges[k]["rows"])}
    return cells


def _domain(run: Run, src: str, column: str, read, in_rows: bool) -> list[str] | None:
    """Every value a tabulated column can take, as the workflow defines it: a codebook's items, a column's own values,
    true and false, the documents, or a document attribute's values among the documents read. None where the column
    is free text, and only the values found can be counted."""
    if column == "document":
        return sorted(read)
    rec = run.out.get(src, {})
    coded = rec.get("input") if rec.get("kind") == "group" else src
    groups = [g for g, r in run.out.items() if r.get("kind") == "group" and r.get("input") == coded and r.get("table")]
    if groups and column in (run.out[groups[-1]].get("item_columns") or ["item"]):
        return [it["id"] for it in run.out[groups[-1]]["codebook"]["items"]] + ["OTHER"]
    col = next((c for c in run.out.get(coded, {}).get("columns") or [] if c["name"] == column), None)
    if col is not None:
        if col.get("type") == "binary":
            return column_values(col)
        items = codebook_items(run, col)
        return None if items is None else [it["id"] for it in items] + (["OTHER"] if codebook_of(col) else [])
    if not in_rows and run.is_attribute(column):  # the same precedence the counting uses: a row's own value first
        return sorted({str(v) for d in read if (v := run.attribute(d, column)) not in (None, "")})
    return None


CHAIN_EXPLICIT = legacy_weak.CHAIN_EXPLICIT  # legacy_weak


def _markdown(tab: dict, sid: str) -> str:
    looped = ("Loops: the feedback loops all documents' coded links make together, each written as its variables with "
              "each link's sign (+ the two move the same way, - opposite ways, ? unclear), and its polarity, R reinforcing, "
              "B balancing. Each loop has a row for the whole loop, counting the documents whose own explicit links make all of it, "
              "which may be none; a row for each of its links, counting the documents behind that link; and a row for each "
              "link into it from a variable outside it (a driver). A loop nobody tells whole is linked up from separate "
              "accounts, so say so where the answer relies on one. Name a loop by its marker, as the report's diagrams do: "
              + "; ".join(f"{m} is {lp}" for lp, m in loop_markers(tab["cells"]).items()) + ".\n") if tab.get("loops") else ""
    traced = looped + ((f"Paths: each row is a {tab['by'][0]} from which the {tab['by'][1]} can be reached by following one document's own "
              "coded links, directly or through others, counted by the documents whose links make it; the links are joined "
              "within a document, not told as one chain, so read them before calling a path a story.\n") if tab.get("paths") else "")
    traced = traced + (CHAIN_EXPLICIT + " A document that makes one only with an implicit link is listed apart as implicit.\n"  # legacy_weak
                       if (tab.get("paths") or tab.get("sequences") or tab.get("loops")) and any("weak" in c for c in tab["cells"]) else "")
    traced = (("Told sequences: each row is a chain one speaker tells as one, its factors in the order told, counted by the "
               "documents that tell it; nothing is joined across speakers, so a chain here is a story somebody told.\n")
              if tab.get("sequences") else "") + traced
    by_document = "document" in tab["by"]  # the documents behind a cell are then its own, so not listed again
    unit = unit_of_table(tab)
    counted = (f"Each count is of {unit}" + ("" if tab.get("count", "documents") == "rows" else f", out of the {unit} read")
               + "; the sentence that cites one names the unit.\n")
    head = (traced + counted + f"{unit[:1].upper() + unit[1:]} read: {tab['of']}, written {{{sid}.of}}, which reads \"{tab['of']}\"\n" + _within_said(tab)
            + "| id | " + " | ".join(tab["by"]) + " | reads as |" + ("" if by_document else " which |") + "\n|"
            + "---|" * (len(tab["by"]) + (2 if by_document else 3)))
    return head + "\n" + "\n".join(f"| {{{c['id']}}} | " + " | ".join(c["values"].values()) + f" | \"{stated(tab, c)}\""
                                   + (f", and {{{c['id']}.weak}} more only implicitly, \"{c['weak']}\"" if c.get("weak") else "") + " |"
                                   + ("" if by_document else f" {', '.join(c.get('cases', c['documents']))} |") for c in tab["cells"])


def _within_said(tab: dict) -> str:
    """How a count is stated within the group one of the table's columns defines, said once for the table: the id to
    write, and each group's base, which is the same for every cell in the group, so it is not repeated on each line.
    A column is offered only where its group can differ from the cell: beside columns that only describe documents, the
    group a coded column defines is the cell itself, and the count would read n of n for every cell. The count is still
    kept, so a report that stated one still recounts."""
    cols = list(dict.fromkeys(col for c in tab["cells"] for col, b in (c.get("within") or {}).items() if b != c["n"]))
    if not cols:
        return ""
    whole = [b for b in tab["by"] if b not in cols]
    out = []
    for col in cols:
        bases = {}
        for c in tab["cells"]:
            if col in (c.get("within") or {}):
                key = " and ".join(f"{b} {c['values'][b]}" for b in [col, *whole])
                bases.setdefault(key, c["within"][col])
        out.append(f"- within its {col}: write {{<id>.within.{col}}}, such as {{{tab['cells'][0]['id']}.within.{col}}}, which "
                   f"reads as the cell's count out of the {unit_of_table(tab)} with its {' and '.join([col, *whole])}: "
                   + "; ".join(f"{k}, of {b}" for k, b in bases.items()))
    return "A count within a group one column defines:\n" + "\n".join(out) + "\n"


def base_of(tab: dict, cell: dict) -> int | None:
    """What a cell's count is out of: its own base, or for a record made before cells carried one, the units read.
    None where the count is of passages."""
    return cell.get("base", tab["of"] if tab.get("count", "documents") != "rows" else None)


def base_columns(by: list[str], carried, describes: Callable[[str], bool], listing: bool = False,
                 composite: bool = False) -> list[int]:
    """Which of a table's columns its cells' bases are taken within, by their place in `by`, so that a count by kind of
    submitter is out of the units of that kind: the column naming the document, and any column describing documents
    (`describes`: one of the document list's, or one a per-document code step added to it) that the rows counted do not
    carry (`carried`, their columns), whose value is then the document's rather than a passage's. None where the table
    counts the document list itself, or is of loops or told sequences (`composite`): every cell is then out of all the
    units read. The one definition: `tabulate` takes its bases by it, and `recorded_base_columns` reads it off a record."""
    if listing or composite:
        return []
    return [i for i, c in enumerate(by) if c == "document" or (c not in carried and describes(c))]


def recorded_base_columns(tab: dict, out: dict[str, dict], columns) -> list[str]:
    """`base_columns` for a table as its run recorded it, by name: `out` holds the records of the run's steps by id and
    `columns` the document list's columns, to which a per-document code step's record adds its own
    (`document_attributes`), as it added them to the document list when the run was counted."""
    src = tab.get("input")
    listing = src == "documents" or out.get(src, {}).get("kind") == "sample"
    carried = set() if listing or src not in out else {k for r in table_of(out, src) for k in r}
    described = {str(c).lower() for c in columns} | {str(c).lower() for rec in out.values()
                                                     for c in (rec.get("document_attributes") or {}).get("columns") or []}
    by = tab.get("by") or []
    return [by[i] for i in base_columns(by, carried, lambda c: c.lower() in described, listing,
                                        bool(tab.get("loops") or tab.get("sequences")))]


def base_set(tab: dict, cell: dict, grouped: list[str], specs: dict[str, dict]) -> tuple:
    """What a cell's base is out of, apart from its unit, as a key two counts can be compared by: the cell's values on
    the columns its base is taken within (`grouped`, from `base_columns`), and what each sample step the table reads
    through chose its documents by on purpose (its `where`, or its fixed list of `documents`), from `specs`, the run's
    steps by id. A seeded draw of `n` is not a choice of what to count, so two counts out of the same set, one of them
    drawn, keep the same key and their different totals show. Two counts with different keys are out of different sets
    by design, and their totals say nothing of each other."""
    chosen, seen, todo = [], set(), [tab.get("input")]
    while todo:
        sid = todo.pop()
        if sid in seen or sid not in specs:
            continue
        seen.add(sid)
        st = specs[sid]
        if st.get("kind") == "sample":
            chosen += [("where", json.dumps(st["where"], sort_keys=True, default=str))] if st.get("where") else []
            chosen += [("documents", json.dumps(sorted(map(str, st["documents"]))))] if st.get("documents") is not None else []
        todo += [i for i in st.get("inputs") or [] if i != "documents"]
    return tuple(sorted((c, str(cell["values"].get(c))) for c in grouped)), tuple(sorted(chosen))


def unit_of_table(tab: dict) -> str:
    """The plural name of what a tabulation's counts count, as its record gives it or, for a record made before
    records carried one, as its count implies."""
    return tab.get("unit") or unit_noun(tab.get("count", "documents"), None, tab.get("cases_are_documents", True))


def said_with_unit(tab: dict, cell: dict) -> str:
    """A cell's count as a reader sees it outside the answer's sentences, with its unit: "2 of 18 households"."""
    return count_said(cell["n"], base_of(tab, cell), unit_of_table(tab))


def stated(tab: dict, cell: dict) -> str:
    """A cell's count as an answer states it, always with what it is out of, so that a bare count cannot be written."""
    b = base_of(tab, cell)
    return f"{cell['n']} passage{'' if cell['n'] == 1 else 's'}" if b is None else f"{cell['n']} of {b}"


def counts_of(run: Run, inputs: list[str]) -> dict[str, int | str]:
    """Every count code made that an answer may state, by the id the answer writes in its place: each tabulation cell
    and each rule the judge applied as "n of base", and each tabulation's documents read on their own."""
    out = {}
    for i in inputs:
        rec = run.out[i]
        if rec.get("kind") == "tabulate":
            out[f"{i}.of"] = rec["of"]
            out.update({c["id"]: stated(rec, c) for c in rec["cells"] if "id" in c})
            out.update({f"{c['id']}.weak": str(c["weak"]) for c in rec["cells"] if "id" in c and "weak" in c})  # legacy_weak
            out.update({f"{c['id']}.within.{col}": f"{c['n']} of {b}" for c in rec["cells"] if "id" in c
                        for col, b in (c.get("within") or {}).items()})
        elif rec.get("kind") == "judge":
            for c in rec.get("criteria") or []:
                # a stated number is a count only where its quotation was found in its document
                if c.get("kind") == "rule":
                    for k, x in level_counts(i, c).items():
                        out[k], out[f"{k}.of"] = f"{x['n']} of {x['base']}", x["base"]
                    # how many documents coded the other way would move the level, for an answer that says how near it is
                    out.update({f"{i}.{c['id']}.margin.{side}": str(m["documents"]) for side, m in (c.get("margin") or {}).items()})
                elif c.get("kind") == "stated" and c.get("start") is not None:
                    out[f"{i}.{c['id']}"], out[f"{i}.{c['id']}.of"] = f"{c['n']} of {c['base']}", c["base"]
    return out


#: A number the answer states with the reference to its count beside it, as "10 ({t[x]})" or "10 of 15 ({t[x]})"
STATED = re.compile(r"(?<![\w.])(\d+)(?:\s+of\s+(\d+))?\s*\(\s*\{(" + COUNT_ID + r")\}\s*\)")


def is_a_name(before: str, numeral: str, names=(), source: str = "") -> bool:
    """Whether `numeral`, written straight after the text `before`, is part of a name rather than a number: the end of
    a document's name (the 3 of MNY-3), or, with the word before it, a phrase of the documents' own text (`source`),
    such as "Organisation 2" (or the 2 of "Organisation 1/2")."""
    if any(re.search(rf"(?<![\w-]){re.escape(n)}$", before + numeral) for n in names):
        return True
    w = source and re.search(r"([A-Za-z]\w*)\s+(?:\d+\s*(?:/|,|and|or)\s*)*$", before)
    return bool(w and re.search(rf"(?<!\w){re.escape(w.group(1))}\s+{re.escape(numeral)}(?![\w.]*\d)", source))


def stated_beside(answer: str, names=(), source: str = "") -> list[re.Match]:
    """Each number the answer writes beside a count's reference (`STATED`), leaving out a numeral that is part of a
    name (`is_a_name`), as in "MNY-3 ({t[x]})", which states no number. An answer that writes the reference in place of
    the number has none: the count is then said once, as code made it."""
    return [m for m in STATED.finditer(answer)
            if m.group(2) or not is_a_name(answer[:m.start(1)], m.group(1), names, source)]


def stated_counts_that_differ(answer: str, counts: dict[str, int | str], names=(), source: str = "") -> list[str]:
    """Each number the answer states beside a count's reference (`stated_beside`) that differs from the count, or from
    what the count is out of, with what the count reads: a stated number is the writer's, the count is code's, and the
    two must agree."""
    out = []
    for m in stated_beside(answer, names, source):
        got = re.match(r"(\d+)(?:\s+of\s+(\d+))?", str(counts.get(m.group(3), "")))
        if got and (m.group(1) != got.group(1) or (m.group(2) and got.group(2) and m.group(2) != got.group(2))):
            out.append(f"{m.group(0)}, where the count reads {counts[m.group(3)]}")
    return out


def put_counts(answer: str, counts: dict[str, int | str], names=(), source: str = "") -> tuple[str, list[str], list[str], list[str]]:
    """The answer with each {count id} replaced by its count; the ids used, those that name no count, and the numerals
    written bare in the prose (outside quotations, citations and the documents' `names`), which no count stands behind; a
    number stated beside its count's reference (`STATED`) has one behind it, and is checked by `stated_counts_that_differ`. Numerals only: a number
    written in words is in some language, and a list of one language's number words is no check on another's. A numeral
    that is part of a name (`is_a_name`) is not written bare."""
    used, unknown = [], []

    def one(m):
        used.append(m.group(1))
        if m.group(1) in counts:
            return str(counts[m.group(1)])
        unknown.append(m.group(1))
        return f"[no such count: {m.group(1)}]"
    text = re.sub(r"\{(" + COUNT_ID + r")\}", one, answer)
    return text, used, unknown, [answer[a:b] for a, b in numbers_written_bare(answer, names, source)]


def numbers_written_bare(answer: str, names=(), source: str = "", years: bool = False) -> list[tuple[int, int]]:
    """Where in the answer each numeral written bare stands, as (start, end): one in the prose with no count behind it,
    outside quotations, citations, counts' references and names, and not a year unless `years` asks for years too. Such a numeral is the writer's own,
    which code neither made nor checked, so the report marks it lightly and never refuses for it. Everything set aside
    is blanked to the same length, so a position in the prose is the same position in the answer."""
    def blank(m):
        return " " * len(m.group(0))
    # a number stated beside its reference is checked by stated_counts_that_differ; a name's numeral beside one stays
    prose = answer
    for m in stated_beside(answer, names, source):
        prose = prose[:m.start()] + blank(m) + prose[m.end():]
    prose = re.sub(r"\[[^\]]*\]|\{[^}]*\}", blank, prose)
    for q in quotations(prose):
        prose = prose.replace(q, " " * len(q))
    for n in sorted(names, key=len, reverse=True):  # a document called MNX-1 is a name, not a count of one
        prose = re.sub(rf"(?<![\w-]){re.escape(n)}(?![\w-])", blank, prose)
    return [m.span() for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.]*\d)", prose)
            if not is_a_name(prose[:m.start()], m.group(), (), source) and (years or not re.fullmatch(r"(19|20)\d\d", m.group()))]


def quoted_elsewhere(run: Run, text: str, row_documents: dict[str, str], claims: dict[str, list[str]] | None = None) -> list[str]:
    """The quotations in `text` that none of the documents it cites holds, a row cited standing for its document and a
    tagged claim (`claims`, claim id: its row ids) for the documents of its rows: a quotation cited to a source that does
    not hold it is not backed by that source. Text citing no document or row has none here, since the trail already
    reads it as citing nothing."""
    cites = citation_ids(text)
    cites += [r for c in cites for r in (claims or {}).get(c, [])]
    docs = {row_documents[c] for c in cites if row_documents.get(c)} | {d for c in cites if (d := cited_document(run, c))}
    out = []
    for q in quotations(text) if docs else []:
        parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", q) if len(p.strip()) >= 4] or [q]
        if not any(all(h is not None for h in locator.locate_all(run.corpus.text(d), parts)) for d in docs):
            out.append(q)
    return out


def quotations(text: str) -> list[str]:
    """Quotations of twelve characters or more, with straight and curly marks paired separately, so that the text
    between one quotation's closing mark and the next one's opening mark is never taken for a quotation. The marks are
    paired from left to right whatever the length between them and the short ones dropped afterwards: requiring the
    length while pairing took the closing mark of a short quotation ("Improved", "Increased") for an opening one."""
    return [q for q in re.findall(r'"([^"\n]*)"', text) + re.findall(r"“([^”\n]*)”", text) if len(q) >= 12]


#: A row's own bookkeeping, which a model reading it is not shown: its id, document and quotation lead the line instead
ROW_PLACE = {"row", "document", "section", "quote", "tier", "start", "end", "fit"}


def row_line(r: dict) -> str:
    """A coded row as every call that reads rows is shown it: id, document, each coded value, then the quotation."""
    return (f"[{r['row']}] {r['document']} | " + " | ".join(f"{k}: {v}" for k, v in r.items() if k not in ROW_PLACE
                                                            and v not in (None, "")) + f" | \"{r['quote']}\"")


def cited_document(run: Run, ref: str) -> str | None:
    """The document, evidence or background, a citation names: by its id, or a background document by its title or
    its file name, a folder before the file name and an extension after it ignored, each compared by `value_key`.
    None where it names no document."""
    stem = lambda x: value_key(re.sub(r"\.\w{1,4}$", "", str(x).strip().replace("\\", "/").rsplit("/", 1)[-1]))  # noqa: E731
    for d in run.corpus.documents:
        if value_key(ref) == value_key(d):
            return d
    for d, m in run.corpus.background.items():
        if value_key(ref) == value_key(d) or any(n and stem(n) == stem(ref) for n in (m.get("title"), m.get("file"))):
            return d
    return None


def cited_as(document: str, quote: str, words: int = 5, before: str | None = None, after: str = "") -> str:
    """A cited row as a reader sees it: its document and the opening words of its quotation, so the citation says where
    to look without the row id, which stays behind it as the link. Given the document's text either side of the
    passage (`before`, `after`), the words start and end on whole words (`whole_words`)."""
    cut = False
    if before is not None:
        quote, cut = whole_words(quote, before, after)
    w = quote.split()
    return f"{document}, “{' '.join(w[:words]).rstrip(',.;:')}{'…' if len(w) > words or cut else ''}”"


def whole_words(quote: str, before: str, after: str) -> tuple[str, bool]:
    """A passage as a citation shows it: without the part-word its span starts or ends inside, which the document's
    text either side shows to be one, nor the stops and spaces it opens with; and whether its end was cut. The
    passage itself, and so the run, are unchanged."""
    q, cut = quote, False
    if before[-1:].isalnum() and q[:1].isalnum():
        q = re.sub(r"^\w+", "", q, count=1)
    if after[:1].isalnum() and q[-1:].isalnum():
        q, cut = re.sub(r"\w+$", "", q, count=1), True
    q = re.sub(r"^\W+", "", q)
    return (q, cut) if q.strip() else (quote, False)


def readable_citations(text: str, rows: dict[str, dict]) -> str:
    """`text` with each group of row ids in square brackets written as `cited_as` gives them, each a link to its row."""
    def one(m):
        ids = group_ids(m.group(1))
        if not ids or any(i not in rows for i in ids):
            return m.group(0)
        return "(" + "; ".join(f"[{cited_as(rows[i]['document'], rows[i]['quote'])}](#{i})" for i in ids) + ")"
    return re.sub(r"\[([^\]]+)\]", one, text)


#: A row's id as `row_id` makes it: its step's, a stop, five characters, and the suffix a second row on the same span takes
ROW_ID = re.compile(r"[a-z][\w-]*\.[a-z0-9]+(?:-\d+)?")


def group_ids(group: str) -> list[str]:
    """The ids in one square-bracketed group of an answer, separated by commas or semicolons."""
    return [c.strip() for c in re.split(r"[,;]", group) if c.strip()]


def citation_ids(text: str) -> list[str]:
    """Every id cited in square brackets, a group's ids separated by commas or semicolons; a cell's coordinates, which
    are square-bracketed too, belong to the count they name and are not read as citations."""
    text = re.sub(r"\{" + COUNT_ID + r"\}", " ", text)
    return [c for g in re.findall(r"\[([^\]]+)\]", text) for c in group_ids(g)]


def _sentences_with_scope(answer: str) -> list[tuple[str, str]]:
    """Each sentence with the text its evidence is read from: the sentence itself, or, for a sentence that ends in a
    colon and introduces a list, the sentence and the list beneath it, since its claim is the list's to show."""
    return [(x, scope) for x, scope, _ in sentences_placed(answer)]


def sentences_placed(answer: str) -> list[tuple[str, str, tuple[int, int]]]:
    """Each sentence of four words or more outside headings and tables, with its scope (`_sentences_with_scope`) and
    where it stands in the answer, as (start, end)."""
    out, lines = [], answer.splitlines(keepends=True)
    at = 0
    for n, raw in enumerate(lines):
        here, at = at, at + len(raw)
        raw = raw.rstrip("\r\n")
        lead = len(raw) - len(raw.lstrip("-*• "))
        line = raw[lead:].rstrip()
        if not line.strip() or line.startswith(("#", "|")):
            continue
        first = len(out)
        # a sentence ends at . ! or ? followed by a space, never inside a quotation, which may hold several
        start, inside = 0, False
        for i, ch in enumerate(line):
            if ch in "“”" or (ch == '"'):
                inside = (not inside) if ch == '"' else (ch == "“")
            nxt = line[i + 1:i + 3]
            ends = ch in ".!?" or (ch in '"”' and line[i - 1:i] in (".", "!", "?"))  # or a quotation closing one
            if not inside and ends and nxt[:1] == " " and re.match(r" [A-Z\"“*(]", nxt):
                out.append((start, i + 1))
                start = i + 1
        if line[start:].strip():
            out.append((start, len(line)))
        placed = []
        for a, b in out[first:]:  # each without the spaces around it, placed in the whole answer
            a += len(line[a:b]) - len(line[a:b].lstrip())
            b -= len(line[a:b]) - len(line[a:b].rstrip())
            placed.append((line[a:b], line[a:b], (here + lead + a, here + lead + b)))
        out[first:] = placed
        if out[first:] and out[-1][0].endswith(":"):
            bullet = re.compile(r"(\s*)([-*•]|\d+[.)])\s")
            # beneath a bullet, the list is the bullets indented under it; beneath a paragraph, any list that follows
            floor = len(m.group(1)) if (m := bullet.match(raw)) else -1
            items = []
            for nxt in lines[n + 1:]:
                nxt = nxt.rstrip("\r\n")
                if not nxt.strip() and not items:
                    continue
                if not (m := bullet.match(nxt)) or len(m.group(1)) <= floor:
                    break
                items.append(nxt.strip())
            out[-1] = (out[-1][0], "\n".join([out[-1][0], *items]), out[-1][2])
    return [(x, scope, span) for x, scope, span in out if len(x.split()) >= 4]


#: A heading, and whether it heads the answer's closing section on its limits, which `render_report.limitations_of` also reads
HEADING, LIMITS = re.compile(r"(?m)^#{1,6} .*$"), re.compile(r"(?i)\blimit")


def sentences_untagged_at(answer: str) -> list[tuple[int, int]]:
    """Where each sentence stands that nothing ties to the passages, as (start, end): a sentence whose scope holds no
    count's reference, no citation of a row or a claim and no quotation, outside headings, tables, figures and the
    closing section on the answer's limits, and other than a pointer to another section. Such a sentence is the
    writer's own reading. The recount reports where each stands, for measuring how much of an answer is tied to its
    passages; the report leaves it unmarked, since an answer's narrative is mostly such sentences, and marks instead
    what can be checked, each count, citation and tagged claim opening its passages."""
    return [span for _, scope, span in sentences_read_for_a_tag(answer)
            if not (re.search(r"\{[^{}\n]+\}", scope) or citation_ids(scope) or quotations(scope))]


def sentences_read_for_a_tag(answer: str) -> list[tuple[str, str, tuple[int, int]]]:
    """The sentences (`sentences_placed`) that state a finding a tag could tie to the passages: every one outside
    figures, pointers to another section and the closing section on the answer's limits."""
    heads = list(HEADING.finditer(answer))
    end = heads[-1].start() if heads and LIMITS.search(heads[-1].group()) else len(answer)
    return [(x, scope, (a, b)) for x, scope, (a, b) in sentences_placed(answer)
            if a < end and not x.startswith("{{") and not re.fullmatch(r"[(\s]*\[§[^\]]*\][)\s.]*", x)]
