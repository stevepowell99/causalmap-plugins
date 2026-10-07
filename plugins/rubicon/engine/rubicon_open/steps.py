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

from . import locator, node
from .corpus import Corpus
from .judge import level_counts
from .workflow import canonical, codebook_of, column_values, resolve_step, value_key


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

    def attribute(self, doc: str, name: str):
        return attribute_of(self.corpus, doc, name)

    def is_attribute(self, name: str) -> bool:
        return name.lower() in {c.lower() for c in self.corpus.columns}

    def table(self, sid: str) -> list[dict]:
        """The rows a step stands for: a code step's, or those of the group step that assigned them items."""
        rec = self.out[sid]
        if rec.get("table") is not None:
            return rec["table"]
        assigned = [r for r in self.out.values() if r.get("kind") == "group" and r.get("input") == sid and r.get("table")]
        return assigned[-1]["table"] if assigned else rec["rows"]


def attribute_of(corpus: Corpus, doc: str, name: str):
    """A document's value of one column of the document list, the column named in any case."""
    cols = corpus.documents[doc]["columns"]
    return next((v for k, v in cols.items() if k.lower() == name.lower()), None)


def draw(corpus: Corpus, s: dict, pool: list[str] | None = None) -> dict:
    """The documents a sample step takes, worked out the same way for the run and for its price, from `pool`, the
    documents of the sample it draws from, or every document where it draws from the documents. A fixed list
    (`documents`) is taken as it stands, an id the corpus lacks said. Otherwise `where` ({column: value or list of
    values}) keeps the documents the question concerns, and a seeded draw of `n` among them, spread across the values
    of `stratify_by` in turn where it is set, takes them all where `n` is not given or is at least as many."""
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
    n = len(docs) if s["n"] is None else min(int(s["n"]), len(docs))
    if n == len(docs):
        return {"documents": docs, **({"where": s["where"]} if s["where"] else {})}
    rng = random.Random(s["seed"])
    if s["stratify_by"]:
        strata = defaultdict(list)
        for d in docs:
            strata[str(attribute_of(corpus, d, s["stratify_by"]) or "")].append(d)
        for v in strata.values():
            rng.shuffle(v)
        chosen, order = [], sorted(strata)
        while len(chosen) < n:
            for v in order:
                if strata[v] and len(chosen) < n:
                    chosen.append(strata[v].pop())
    else:
        chosen = rng.sample(docs, n)
    return {"documents": sorted(chosen), **({"where": s["where"]} if s["where"] else {})}


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
    return sorted(run.corpus.documents) if "documents" in ins else sorted({d for i in ins for d in run.out[i]["documents"]})


def place_rows(run: Run, s: dict, docs: list[str], cols: list[dict], results: list[tuple]) -> dict:
    """The rows each reading of a section gave, placed: each quotation found in its document (and dropped, and listed,
    where it is not), each row given its id, and each value stored in its column's one spelling. `results` holds one
    (document, section index, rows, error or None, read again) per reading."""
    allowed = values_allowed(run, cols)
    rows, dropped, unread, off, missing, unquoted = [], [], [], 0, 0, 0
    by_doc = defaultdict(list)
    retried = [{"document": d, "section": i + 1, "read": not err} for d, i, _, err, again in results if again]
    for d, i, got, err, _ in results:
        if err:
            unread.append({"document": d, "section": i + 1, "error": err})
        quoted = [(i, r) for r in got if isinstance(r, dict) and str(r.get("quote") or "").strip()]
        unquoted += len(got) - len(quoted)
        by_doc[d] += quoted
    for d in docs:
        found = locator.locate_all(run.corpus.text(d), [str(r["quote"]) for _, r in by_doc[d]])
        # in the order the passages stand in the document, which is the order the page shows a step's rows in
        for (i, r), h in sorted(zip(by_doc[d], found), key=lambda x: -1 if x[1] is None else x[1].start):
            if h is None:
                dropped.append({"document": d, "quote": r["quote"]})
                continue
            quote = h.quote
            row = {"row": row_id(s["id"], d, h.start, h.end, {r["row"] for r in rows}), "document": d, "section": i + 1, "quote": quote, "tier": h.tier,
                   "start": h.start, "end": h.end}
            for c in cols:
                v = row[c["name"]] = canonical(r.get(c["name"]), allowed[c["name"]])
                if v in (None, ""):
                    missing += 1
                elif allowed[c["name"]] and v not in allowed[c["name"]]:
                    off += 1
            rows.append(row)
    return {"rows": rows, "sections_unread": unread, "sections_retried": retried, "quotations_dropped": dropped,
            "values_off_the_list": off, "values_missing": missing, "rows_without_a_quotation": unquoted}


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
    filtered = None
    if s["filters"]:
        rows, filtered = filter_links(run, src, rows, s["filters"])
    by, count = s["by"], s["count"]
    cells = _paths(run, rows, by) if s["paths"] else _combinations(run, rows, by)
    # every combination the columns allow is a cell, so a count of none is stated as 0 rather than left out; a sparse
    # table, such as causal links from one factor list crossed with itself, lists only the combinations that occur
    in_rows = {k for r in rows for k in r}
    sparse = s["sparse"] or s["paths"] or bool(s["filters"])  # a filter can rename a factor, so no codebook lists its values
    if not sparse:
        domains = [_domain(run, src, c, read, c in in_rows) or sorted({k[i] for k in cells} - {"(blank)"}) for i, c in enumerate(by)]
        for cmb in itertools.product(*domains):
            cells.setdefault(cmb, {"documents": set(), "rows": []})
    # a cell's base is the documents read that share its values on every column describing a document, so a count by
    # kind of submitter is out of that kind; counting the document list itself, every cell is out of all those read
    listing = src == "documents" or run.out.get(src, {}).get("kind") == "sample"
    whole = [] if listing else [i for i, c in enumerate(by) if c == "document" or (c not in in_rows and run.is_attribute(c))]

    def of_doc(d, c):
        v = d if c == "document" else run.attribute(d, c)
        return "(blank)" if v in (None, "") else str(v)

    def base(cmb):
        return sum(all(of_doc(d, by[i]) == cmb[i] for i in whole) for d in read) if count == "documents" else None

    # a count can also be stated within the group a coded column defines ("of those improved, 13 of 15"): its base is
    # then the documents with that value in that column, as well as the cell's values on the columns describing a document
    def docs_with(i, v):
        return {d for (k, c) in cells.items() if k[i] == v for d in c["documents"]}
    coded = [i for i, c in enumerate(by) if i not in whole and re.fullmatch(r"[\w-]+", c)] if count == "documents" and len(by) > 1 else []
    marginal = {(i, k[i]): docs_with(i, k[i]) for k in cells for i in coded}

    def within(cmb):
        return {by[i]: sum(all(of_doc(d, by[j]) == cmb[j] for j in whole) for d in marginal[(i, cmb[i])]) for i in coded}
    out = [{"values": dict(zip(by, k)), "n": len(v["documents"]) if count == "documents" else len(v["rows"]), "base": base(k),
            "within": within(k), "documents": sorted(v["documents"]), "rows": v["rows"]} for k, v in cells.items()]
    out.sort(key=lambda c: (-c["n"], list(c["values"].values())))
    for k, c in enumerate(out, 1):  # an id per count, which the answer writes in place of the number
        c["id"] = f"{s['id']}.c{k}"
    return {"input": src, "by": by, "count": count, "of": len(read), "sparse": sparse, "paths": s["paths"],
            **({"filters": s["filters"], "filtered": filtered} if filtered else {}), "cells": out}


FILTER_SHIM = Path(__file__).resolve().parent / "filter_links.mjs"


def filter_links(run: Run, src: str, rows: list[dict], filters: list[dict]) -> tuple[list[dict], dict]:
    """A code step's rows as Causal Map links, put through Causal Map's own filters in order (`cm/`, run under Node),
    and back as rows with the two ends as the filters left them. The conversion is `link-rows.js`, which the Rubicon
    page refilters a map with too: each row gives a link for every pair of its two link-end values (the code step's
    `links`), with its document as the link's source and the document's facts on the source, so a filter reads
    `s_<fact>` for one. Returns the rows and what the filtering did."""
    ends = next(st.get("links") for st in run.steps if st.get("id") == src)
    docs = sorted({r["document"] for r in rows})
    attributes = {d: dict(run.corpus.documents.get(d, {}).get("columns") or {}) for d in docs}
    got = node.call(FILTER_SHIM, {"rows": rows, "ends": ends, "filters": filters, "attributes": attributes},
                    "link filters")
    if got["unsupported"]:
        raise ValueError(f"{', '.join(got['unsupported'])}: not a filter Causal Map's filter engine applies")
    return got["rows"], got["filtered"]


def _combinations(run: Run, rows: list[dict], by: list[str]) -> dict[tuple, dict]:
    """The combinations of the `by` columns' values the rows have, each holding its documents and rows: a row with a
    list in a column counts once under each of its values."""
    cells: dict[tuple, dict] = {}
    for r in rows:
        values = []
        for c in by:
            v = r.get(c) if c in r else (r["document"] if c == "document" else run.attribute(r["document"], c) if run.is_attribute(c) else None)
            values.append(v if isinstance(v, list) else [v])
        combos = [()]
        for vs in values:
            combos = [cmb + ("(blank)" if v in (None, "") else str(v),) for cmb in combos for v in vs]
        for cmb in combos:
            cell = cells.setdefault(cmb, {"documents": set(), "rows": []})
            cell["documents"].add(r["document"])
            cell["rows"].append(r["row"])
    return cells


def _paths(run: Run, rows: list[dict], by: list[str]) -> dict[tuple, dict]:
    """The paths each document's own links make: a cell for every pair of values of the first two `by` columns (a
    link's two ends) where the second can be reached from the first by following that document's links, directly or
    through other values, holding the documents that make it and the links on those paths. The links are joined
    within a document and never across documents; any further `by` columns describe the document."""
    start, end, rest = by[0], by[1], by[2:]

    def ends(r, c):
        v = r.get(c)
        return [str(x) for x in (v if isinstance(v, list) else [v]) if x not in (None, "")]

    per_doc: dict[str, list] = defaultdict(list)
    for r in rows:
        per_doc[r["document"]] += [(a, b, r["row"]) for a in ends(r, start) for b in ends(r, end) if a != b]
    cells: dict[tuple, dict] = {}
    for d, links in per_doc.items():
        nxt: dict[str, set] = defaultdict(set)
        for a, b, _ in links:
            nxt[a].add(b)
        reach: dict[str, set] = {}
        for x in list(nxt):  # every value reachable from x by one link or more
            seen, todo = set(), [x]
            while todo:
                for y in nxt[todo.pop()] - seen:
                    seen.add(y)
                    todo.append(y)
            reach[x] = seen
        of_doc = [[d if c == "document" else (str(v) if (v := run.attribute(d, c)) not in (None, "") else "(blank)")] for c in rest]
        for x, ys in reach.items():
            for y in ys - {x}:
                # a link is on a path from x to y if x reaches its cause and its effect reaches y, and it neither
                # leaves y nor returns to x
                on = [rid for a, b, rid in links if (a == x or a in ys) and (b == y or y in reach.get(b, ())) and a != y and b != x]
                for cmb in itertools.product(*of_doc):
                    cell = cells.setdefault((x, y) + cmb, {"documents": set(), "rows": []})
                    cell["documents"].add(d)
                    cell["rows"] += [rid for rid in on if rid not in cell["rows"]]
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
    if column == "item" and groups:
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


def _markdown(tab: dict, sid: str) -> str:
    traced = (f"Paths: each row is a {tab['by'][0]} from which the {tab['by'][1]} can be reached by following one document's own "
              "coded links, directly or through others, counted by the documents whose links make it; the links are joined "
              "within a document, not told as one chain, so read them before calling a path a story.\n") if tab.get("paths") else ""
    by_document = "document" in tab["by"]  # the documents behind a cell are then its own, so not listed again
    head = (traced + f"Documents read: {tab['of']}, written {{{sid}.of}}, which reads \"{tab['of']}\"\n" + _within_said(tab)
            + "| id | " + " | ".join(tab["by"]) + " | reads as |" + ("" if by_document else " which |") + "\n|"
            + "---|" * (len(tab["by"]) + (2 if by_document else 3)))
    return head + "\n" + "\n".join(f"| {{{c['id']}}} | " + " | ".join(c["values"].values()) + f" | \"{stated(tab, c)}\" |"
                                   + ("" if by_document else f" {', '.join(c['documents'])} |") for c in tab["cells"])


def _within_said(tab: dict) -> str:
    """How a count is stated within the group one of the table's columns defines, said once for the table: the id to
    write, and each group's base, which is the same for every cell in the group, so it is not repeated on each line."""
    cols = list(dict.fromkeys(col for c in tab["cells"] for col in (c.get("within") or {})))
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
                   f"reads as the cell's count out of the documents with its {' and '.join([col, *whole])}: "
                   + "; ".join(f"{k}, of {b}" for k, b in bases.items()))
    return "A count within a group one column defines:\n" + "\n".join(out) + "\n"


def _base(tab: dict, cell: dict) -> int | None:
    """What a cell's count is out of: its own base, or for a record made before cells carried one, the documents read.
    None where the count is of passages rather than documents."""
    return cell.get("base", tab["of"] if tab.get("count", "documents") == "documents" else None)


def stated(tab: dict, cell: dict) -> str:
    """A cell's count as an answer states it, always with what it is out of, so that a bare count cannot be written."""
    b = _base(tab, cell)
    return f"{cell['n']} passages" if b is None else f"{cell['n']} of {b}"


def counts_of(run: Run, inputs: list[str]) -> dict[str, int | str]:
    """Every count code made that an answer may state, by the id the answer writes in its place: each tabulation cell
    and each rule the judge applied as "n of base", and each tabulation's documents read on their own."""
    out = {}
    for i in inputs:
        rec = run.out[i]
        if rec.get("kind") == "tabulate":
            out[f"{i}.of"] = rec["of"]
            out.update({c["id"]: stated(rec, c) for c in rec["cells"] if "id" in c})
            out.update({f"{c['id']}.within.{col}": f"{c['n']} of {b}" for c in rec["cells"] if "id" in c
                        for col, b in (c.get("within") or {}).items()})
        elif rec.get("kind") == "judge":
            for c in rec.get("criteria") or []:
                # a stated number is a count only where its quotation was found in its document
                if c.get("kind") == "rule":
                    for k, x in level_counts(i, c).items():
                        out[k], out[f"{k}.of"] = f"{x['n']} of {x['base']}", x["base"]
                elif c.get("kind") == "stated" and c.get("start") is not None:
                    out[f"{i}.{c['id']}"], out[f"{i}.{c['id']}.of"] = f"{c['n']} of {c['base']}", c["base"]
    return out


def put_counts(answer: str, counts: dict[str, int | str], names=()) -> tuple[str, list[str], list[str], list[str]]:
    """The answer with each {count id} replaced by its count; the ids used, those that name no count, and the numerals
    written bare in the prose (outside quotations, citations and the documents' `names`), which no count stands behind. Numerals only: a number
    written in words is in some language, and a list of one language's number words is no check on another's."""
    used, unknown = [], []

    def one(m):
        used.append(m.group(1))
        if m.group(1) in counts:
            return str(counts[m.group(1)])
        unknown.append(m.group(1))
        return f"[no such count: {m.group(1)}]"
    text = re.sub(r"\{([\w-]+\.[\w.-]+)\}", one, answer)
    prose = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", answer)
    for q in quotations(prose):
        prose = prose.replace(q, " ")
    for n in sorted(names, key=len, reverse=True):  # a document called MNX-1 is a name, not a count of one
        prose = re.sub(rf"(?<![\w-]){re.escape(n)}(?![\w-])", " ", prose)
    bare = re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.]*\d)", prose)
    return text, used, unknown, [b for b in bare if not re.fullmatch(r"(19|20)\d\d", b)]


def quoted_elsewhere(run: Run, text: str, row_documents: dict[str, str]) -> list[str]:
    """The quotations in `text` that none of the documents it cites holds, a row cited standing for its document: a
    quotation cited to a source that does not hold it is not backed by that source. Text citing no document or row
    has none here, since the trail already reads it as citing nothing."""
    cites = citation_ids(text)
    docs = {row_documents[c] for c in cites if row_documents.get(c)} | {d for c in cites if (d := cited_document(run, c))}
    out = []
    for q in quotations(text) if docs else []:
        parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", q) if len(p.strip()) >= 4] or [q]
        if not any(all(h is not None for h in locator.locate_all(run.corpus.text(d), parts)) for d in docs):
            out.append(q)
    return out


def quotations(text: str) -> list[str]:
    """Quotations of twelve characters or more, with straight and curly marks paired separately, so that the text
    between one quotation's closing mark and the next one's opening mark is never taken for a quotation."""
    return re.findall(r'"([^"\n]{12,}?)"', text) + re.findall(r"“([^”\n]{12,}?)”", text)


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


def citation_ids(text: str) -> list[str]:
    """Every id cited in square brackets, a group's ids separated by commas or semicolons."""
    return [c.strip() for g in re.findall(r"\[([^\]]+)\]", text) for c in re.split(r"[,;]", g) if c.strip()]


def _sentences_with_scope(answer: str) -> list[tuple[str, str]]:
    """Each sentence with the text its evidence is read from: the sentence itself, or, for a sentence that ends in a
    colon and introduces a list, the sentence and the list beneath it, since its claim is the list's to show."""
    out, lines = [], answer.splitlines()
    for n, raw in enumerate(lines):
        line = raw.lstrip("-*• ").strip()
        if not line or line.startswith(("#", "|")):
            continue
        first = len(out)
        # a sentence ends at . ! or ? followed by a space, never inside a quotation, which may hold several
        cur, inside = "", False
        for i, ch in enumerate(line):
            cur += ch
            if ch in "“”" or (ch == '"'):
                inside = (not inside) if ch == '"' else (ch == "“")
            nxt = line[i + 1:i + 3]
            ends = ch in ".!?" or (ch in '"”' and line[i - 1:i] in (".", "!", "?"))  # or a quotation closing one
            if not inside and ends and nxt[:1] == " " and re.match(r" [A-Z\"“*(]", nxt):
                out.append(cur.strip())
                cur = ""
        if cur.strip():
            out.append(cur.strip())
        out[first:] = [(x, x) for x in out[first:]]
        if out[first:] and out[-1][0].endswith(":"):
            bullet = re.compile(r"(\s*)([-*•]|\d+[.)])\s")
            # beneath a bullet, the list is the bullets indented under it; beneath a paragraph, any list that follows
            floor = len(m.group(1)) if (m := bullet.match(raw)) else -1
            items = []
            for nxt in lines[n + 1:]:
                if not nxt.strip() and not items:
                    continue
                if not (m := bullet.match(nxt)) or len(m.group(1)) <= floor:
                    break
                items.append(nxt.strip())
            out[-1] = (out[-1][0], "\n".join([out[-1][0], *items]))
    return [(x, scope) for x, scope in out if len(x.split()) >= 4]
