"""A workflow of pieces, and the check that a runner could carry it out (`rubicon/docs/pieces.md`).

A workflow is JSON: `question_as_agreed`, `document_attributes`, `cannot_answer`, `steps` and `reasons`. Each step
has an `id`, a `kind` (sample, code, group, tabulate, judge, write), `inputs` (earlier step ids, or "documents") and its
settings, which may sit on the step itself or under `settings`; `normalise` puts them on the step.
"""
from __future__ import annotations

import json
import re

KINDS = ("sample", "code", "group", "tabulate", "judge", "write")
TYPES = ("free_text", "binary", "nominal", "ordinal", "numeric")
GRANULARITY = ("headline", "standard", "detailed")
DIRECTION = ("column", "items", "none")

#: The characters a coder reads at once. On one long-interview corpus (30 September 2026), a cheap reader found 81 to 86% of a strong model's findings in
#: sections of 2,000 to 8,000 characters and 55% in whole accounts of about 27,000.
SECTION_CHARS = 8000


def normalise(wf: dict) -> dict:
    """The workflow with every step's settings on the step itself."""
    steps = [{**{k: v for k, v in s.items() if k != "settings"}, **(s.get("settings") or {})} for s in wf.get("steps", [])]
    return {**wf, "steps": steps}


#: A binary column's two values, as its rows hold them, its tables count them and a workflow names them.
BINARY = ("yes", "no")


def value_key(v) -> str:
    """The form in which any two values are compared, wherever one is matched against another: a coder's reply against
    a column's values, a workflow's `where` or `base` against a table or the document list. Case, surrounding space
    and the difference between a hyphen, an underscore and a space are ignored, and true or yes, false or no, in any
    case or as JSON, are one value each, so "True", true and "YES" match. The one place this is decided."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return BINARY[0] if v else BINARY[1]
    s = re.sub(r"[\s_-]+", " ", str(v)).strip().lower()
    return {"true": BINARY[0], "false": BINARY[1]}.get(s, s)


def canonical(v, values: list[str] | None):
    """A value as the rows hold it: the name among `values` it matches by `value_key`, or the value as it came where
    it matches none (counted off the list by the caller) or there is no list."""
    if values is None or v in (None, "") or isinstance(v, list):
        return v
    return next((x for x in values if value_key(x) == value_key(v)), v)


def column_values(column: dict) -> list[str] | None:
    """The values a column can take where the workflow itself fixes them: a binary column's two, or a column's own
    list. None for free text, numbers, and a codebook a group step has yet to make."""
    if column.get("type") == "binary":
        return list(BINARY)
    v = column.get("values")
    if isinstance(v, list) and v:
        return [str(x.get("name") or x.get("id") or "") if isinstance(x, dict) else str(x) for x in v]
    return None


def value_faults(said: str, where, known: dict[str, list[str] | None]) -> list[str]:
    """Each value a `{column: value or list}` names that its column can never take, by `value_key`, where `known`
    (column name in lower case: its values, or None where they are not fixed) says what the column takes: a test that
    can match nothing would count none and read as a finding."""
    out = []
    for k, v in (where.items() if isinstance(where, dict) else []):
        vals = known.get(str(k).lower())
        for x in ((v if isinstance(v, list) else [v]) if vals else []):
            if not any(value_key(x) == value_key(y) for y in vals):
                out.append(f"{said} {k} {x!r}, a value {k} never takes (it takes {', '.join(vals)})")
    return out


#: A loop table's columns: the loop, written as its variables with each link's sign; its polarity; which part of it a
#: cell counts (`PARTS`); and, for a link or a driver, that link.
LOOP_COLUMNS = ("loop", "polarity", "part", "link")
#: A told-sequence table's one column: each chain one speaker tells, written as its factors in the order told.
SEQUENCE_COLUMNS = ("chain",)
#: The parts of a loop a cell counts: the whole loop told in one document's own links, one of its links, and a link
#: into the loop from a variable outside it.
PARTS = ("whole", "link", "driver")
#: A loop's polarity: reinforcing (an even number of minus links), balancing (odd), or unknown (a link's sign unclear).
POLARITIES = ("R", "B", "unknown")
#: A link's sign as the coding gives it, written into a loop as it is drawn; any other value is unclear.
SIGNS = {"plus": "+", "minus": "-"}


def sign_of(v) -> str:
    """A coded sign as `+`, `-` or `?`: the one place a sign's spelling is read."""
    return next((mark for name, mark in SIGNS.items() if value_key(v) in (value_key(name), value_key(mark))), "?")



def arrow(a: str, sign: str, b: str) -> str:
    """A signed link as a loop table writes it, such as `income →+ reinvestment`; `arrow_parts` reads one back."""
    return f"{a} →{sign} {b}"


def arrow_parts(text: str) -> tuple[str, str, str]:
    a, _, rest = str(text).partition(" →")
    return a, rest[:1], rest[2:]


def loop_markers(cells: list[dict]) -> dict[str, str]:
    """Each loop of a loop table with its marker, R1, R2, B1 or ?1, numbered by polarity in the table's order, so the
    answer and the report's diagrams name a loop the same way."""
    out, seen = {}, {}
    for c in cells:
        loop, polarity = c["values"]["loop"], c["values"]["polarity"]
        if loop not in out:
            seen[polarity] = seen.get(polarity, 0) + 1
            out[loop] = f"{'?' if polarity == 'unknown' else polarity}{seen[polarity]}"
    return out


def has_values(column: dict) -> bool:
    """Whether a column is coded against a list of values: its own, or a group step's codebook."""
    return bool(codebook_of(column) or (isinstance(column.get("values"), list) and column["values"]))


#: Settings whose null is a value of its own rather than "use the default": off, or for the second coder's, the
#: provider's own effort, the first coder's section size and the first coder's prompt unchanged; for either coder's
#: prompt note, nothing added.
OFF_BY_NULL = ("second_coder", "check", "stratify_by", "documents", "where", "n", "second_thinking", "second_section_chars",
               "second_retry_thinking", "prompt_note", "second_prompt_note", "rows_per_cell", "picker_model", "links")


def resolve_step(s: dict, kind: str | None = None) -> dict:
    """The step with every setting its piece reads filled in: the step's own value where it gives one, the default
    where it does not or gives null (null means off for `OFF_BY_NULL`). This is the one place the defaults live; each
    piece resolves its step before reading it, and a run writes its workflow resolved, so the run folder says what
    ran whatever the defaults later become. `kind` is the piece's own, where the step does not say."""
    from . import models as C

    def fill(defaults: dict, given: dict) -> dict:  # the step's own settings first, then the defaults it left out
        out = {k: v for k, v in given.items() if v is not None or k in OFF_BY_NULL}
        return {**out, **{k: v for k, v in defaults.items() if k not in out}}
    k = kind or s.get("kind")
    if k == "sample":
        return fill({"seed": 30, "n": None, "stratify_by": None, "documents": None, "where": None}, s)
    if k == "code":
        cols = s.get("columns") or []
        out = fill({"model": C.CODER, "second_coder": C.SECOND_CODER if cols and all(map(has_values, cols)) else None,
                    "check": False, "section_chars": SECTION_CHARS, "prompt_note": None, "per_document": False,
                    "links": None}, s)  # links: {"from": column, "to": column, "sign": column}, a link's two ends and, for
        # a causal loop diagram, the column giving its sign (plus or minus)
        if isinstance(out["second_coder"], bool):  # true asks for the default second coder, false for none
            out["second_coder"] = C.SECOND_CODER if out["second_coder"] else None
        if out["second_coder"]:  # second_thinking null: the provider's own effort; second_section_chars null: the first's;
            # second_retry_thinking: the effort a second-coder section is read at again when it ran out of output, null never;
            # second_prompt_note: text added to the second coder's prompt only, so the two coders can read differently, null none
            out = fill({"adjudicator": C.ADJUDICATOR, "adjudicator_thinking": C.ADJUDICATOR_THINKING, "second_thinking": None, "second_section_chars": None,
                        "second_retry_thinking": C.SECOND_RETRY_THINKING, "second_prompt_note": None}, out)
        out = fill({"check_model": C.CODER}, out) if out["check"] else out
        out["thinking"] = C.thinking_for(out.get("model"), out.get("thinking"))  # last: a fill drops a null it is given
        return out
    if k in ("group", "write"):  # the pages it reads, notes or method pages by name, or "all" notes; by default its own craft's
        from . import guidance
        s = fill({"practice": guidance.notes_for(k)}, s)
    if k == "group":
        out = fill({"model": C.GROUPER, "granularity": "standard", "direction": "column", "multi": False, "assign": False,
                    "item_is": f"a kind of {s.get('key_column')} that bears on the question"}, s)
        out = fill({"max_items": {"headline": 8, "standard": 15, "detailed": 30}[out["granularity"]]}, out)
        out["thinking"] = C.thinking_for(out.get("model"), out.get("thinking") or C.GROUP_THINKING.get((out.get("model") or "").split("-")[0]))
        return fill({"assign_model": C.ASSIGNER}, out) if out["assign"] else out
    if k == "tabulate":
        # sparse: only the combinations that occur are cells, as an edge list (from, to, count) rather than a grid;
        # paths: the first two `by` columns are a link's two ends, and a cell is a path traced in one document's links;
        # filters: Causal Map's link filters, in order, applied to the links its input coded before anything is counted;
        # loops: the cells are the feedback loops of up to loop_links links that all documents' signed links make
        # together, through one of the variables `through` names where it names any; sequences: the cells are the chains
        # the speakers tell, each built from the rows one document gives one "sequence", in the order of their "step"
        # count: what a cell counts, "cases" (`Corpus.case_of`), "documents", "rows" (passages) or a column of the
        # document list whose values are its cases; unit: the plural name a reader is given for it
        return fill({"by": [], "count": "cases", "unit": None, "sparse": False, "paths": False, "filters": [], "loops": False,
                     "loop_links": 4, "through": [], "sequences": False}, s)
    if k == "judge":
        return fill({"model": C.JUDGE, "combine": "weakest"}, s)
    if k == "write":
        out = fill({"model": C.WRITER, "instructions": "the question as agreed", "words": 800, "documents": False, "skim": False,
                    "reading_tokens": C.WRITER_READING_TOKENS, "rows_per_cell": ROWS_PER_CELL, "picker_model": C.CODER, "review": False, "trail": True, "trail_model": C.CODER,
                    "workings": False}, s)  # workings: code appends every table of counts in plain labels, under the answer
        # review: a second strong-model call that rewrites the draft, off by default since the writer applies the
        # review's tests itself (measured 3 October 2026); the repair round attaches evidence, on a cheap model
        out = fill({"trail_repair": out["trail"]}, out)
        out = fill({"review_model": C.REVIEWER}, out) if out["review"] else out
        out = fill({"repair_model": C.REPAIRER}, out) if out["trail_repair"] else out
        # last, as a fill drops a null: the effort of the draft, review and repair calls, null each model's family default
        return {**out, "thinking": s.get("thinking")}
    return dict(s)


#: The settings a step must give for itself, beside every setting `resolve_step` fills in.
GIVEN = {"sample": {"n", "documents"}, "code": {"prompt", "columns"}, "group": {"key_column"}, "tabulate": set(),
         "judge": {"source", "verdicts", "criteria", "accepted"}, "write": set()}


#: The settings the designer is not told of (`guidance/pieces/design.md`), each for a reason: the models and their
#: effort are chosen by their price in production, never by the workflow's author; `accepted` is the evaluator's act;
#: the rest are settings measured in testing and set by test profiles. Every other setting a piece reads is described in
#: the designer's prompt, which a test asserts, so the prompt cannot fall behind what the pieces can do.
NOT_FOR_THE_DESIGNER = {
    "sample": {"seed"},
    "code": {"model", "thinking", "adjudicator", "adjudicator_thinking", "second_thinking", "second_section_chars",
             "second_retry_thinking", "prompt_note", "second_prompt_note", "check", "check_model"},
    "group": {"model", "thinking", "assign_model", "item_is"},
    "tabulate": set(),
    "judge": {"model", "accepted"},
    "write": {"model", "thinking", "documents", "picker_model", "reading_tokens", "review", "review_model", "rows_per_cell", "skim",
              "trail", "trail_model", "trail_repair", "repair_model", "workings"},
}


def settings_of(kind: str) -> set[str]:
    """Every setting a piece of this kind reads: what a step gives, and everything `resolve_step` fills in with each
    switch on, so the list cannot drift from the defaults."""
    switches = {"code": {"columns": [{"name": "x", "type": "nominal", "values": ["a"]}], "check": True},
                "group": {"assign": True}, "write": {"review": True, "trail": True}}.get(kind, {})
    return {"id", "kind", "inputs"} | GIVEN.get(kind, set()) | set(resolve_step(switches, kind))


def resolve(wf: dict) -> dict:
    """The workflow with every step resolved (`resolve_step`)."""
    wf = normalise(wf)
    return {**wf, "steps": [resolve_step(s) for s in wf["steps"]]}


def parse(text: str) -> dict:
    """The workflow in a model's reply: the last fenced ```json block holding steps, since a reply that corrects
    itself puts the correction last; otherwise the last fenced block, or the reply itself."""
    got = []
    for b in re.findall(r"```json\s*\n(.*?)\n```", text, re.S):
        try:
            got.append(json.loads(b))
        except ValueError:
            continue
    whole = [g for g in got if isinstance(g, dict) and "steps" in g]
    return normalise((whole or got or [json.loads(text)])[-1])


def codebook_of(column: dict) -> str | None:
    """The group step a nominal or ordinal column takes its values from, if it names one."""
    v = column.get("values")
    return v.split(":", 1)[1] if isinstance(v, str) and v.startswith("codebook:") else None


#: The settings that name a model.
MODEL_SETTINGS = ("model", "second_coder", "adjudicator", "check_model", "assign_model", "picker_model", "review_model",
                  "trail_model", "repair_model")


def _shape_faults(sid, kind: str, s: dict) -> list[str]:
    """The settings the check reads that are not of the shape it reads them in, such as a list of columns written
    as a sentence pointing at another step's."""
    out: list[str] = []

    def list_of(key: str, typ: type, what: str) -> bool:
        v = s.get(key)
        ok = v is None or (isinstance(v, list) and all(isinstance(x, typ) for x in v))
        if not ok:
            out.append(f"{sid}: {key} is not a list of {what}")
        return ok and v is not None

    list_of("inputs", str, "step ids")
    for key in MODEL_SETTINGS:  # a model is named, or left to its default; anything else would only fail at run time
        v = s.get(key)
        if v is not None and not isinstance(v, str) and not (key == "second_coder" and isinstance(v, bool)):
            out.append(f"{sid}: {key} is not a model's name")
    if kind == "code" and s.get("second_coder") not in (None, False) and any(
            isinstance(c, dict) and not has_values(c) for c in (s.get("columns") or [])):
        out.append(f"{sid}: a second coder needs every column to have fixed values, and this step has a free-text column")
    if kind == "sample" and s.get("stratify_by") is not None and not isinstance(s["stratify_by"], str):
        out.append(f"{sid}: stratify_by is not a column name")
    if kind == "code" and list_of("columns", dict, "column definitions"):
        for c in s["columns"]:
            if c.get("values") is not None and not isinstance(c["values"], (list, str)):
                out.append(f"{sid}: column {c.get('name')!r} has values that are neither a list nor a codebook")
    if kind == "code" and s.get("links") is not None and not (
            isinstance(s["links"], dict) and all(isinstance(s["links"].get(k), str) for k in ("from", "to"))
            and isinstance(s["links"].get("sign", ""), str)):
        out.append(f"{sid}: links is not {{\"from\": column, \"to\": column}}, with \"sign\": column where links are signed")
    if kind == "tabulate":
        list_of("by", str, "column names")
        list_of("through", str, "variable names")
        if list_of("filters", dict, "filters") and not all(isinstance(f.get("type"), str) for f in s["filters"]):
            out.append(f"{sid}: a filter does not say its type")
    if kind == "judge":
        list_of("verdicts", dict, "verdicts")
        list_of("criteria", dict, "criteria")
    return out


def attribute_sizes(corpus) -> dict[str, int]:
    """Each column of a corpus's document list with the number of values it takes, for sizing a table before a run."""
    return {a: len({d["columns"].get(a) for d in corpus.documents.values()}) for a in corpus.columns}


#: A table cell as the write step reads it (`steps._markdown`: its id, values, count and the documents behind it, with
#: each within-group base said once a table rather than on every line): 76 characters a cell and 694 a table, about
#: 25 tokens a cell, fitted 5 October 2026 over 601 tables of test runs from October 2026.
TABLE_CELL_TOKENS = 25


#: A sparse table holds only the combinations that occur, which no design can know before the run, so it is sized
#: as at most this many cells a document read. Measured 3 October 2026 over 215 real tables of several columns on
#: corpora of six documents or more, the cells that occur a document read: median 0.44, 90th percentile 1.56,
#: highest 8.4; the bound sits above the 90th percentile, and the check's half of the writer's budget is the margin.
SPARSE_CELLS_PER_DOCUMENT = 4

#: How many rows the writer reads from each cell of its tables, chosen by the picker (null: every row). On a stored
#: run on a long-interview corpus the writer read all 805 coded rows, about 107,000 tokens, to cite 125 of them, and its citations sat all
#: through each cell, so a rule by order or length would have dropped most of them (3 October 2026).
#: Off by default: a cheap picker offered the writer 68% and 27% of the rows it chose itself on two such runs, saved
#: nothing and 26% of the write step once its own call was paid, and the judges could not tell the answers apart.
ROWS_PER_CELL = None


def document_attributes(wf: dict) -> dict[str, int | None]:
    """The columns a `per_document` code step adds to the document list, each with how many values it takes (None for
    free text or numbers): later steps may tabulate by them, base a judge's count on them or sample by them, as by any
    attribute the document list records."""
    out: dict[str, int | None] = {}
    for s in normalise(wf).get("steps", []):
        if s.get("kind") == "code" and s.get("per_document"):
            for c in s.get("columns") or []:
                if isinstance(c, dict) and c.get("name"):
                    vals = column_values(c)
                    out[c["name"]] = len(vals) if vals else None
    return out


def drawn(wf: dict, corpus) -> dict[str, list[str]]:
    """The documents each sample step will take (`steps.draw`), in order, so a step drawing from an earlier sample
    draws from its documents; a `where` that keeps nothing takes none here and fails the run itself."""
    from .steps import draw
    coded = {a.lower() for a in document_attributes(wf)}  # unknown before the run, so not filtered on: an upper bound
    out: dict[str, list[str]] = {}
    for s in normalise(wf).get("steps", []):
        if s.get("kind") == "sample":
            src = (s.get("inputs") or ["documents"])[0]
            if isinstance(s.get("where"), dict):
                s = {**s, "where": {k: v for k, v in s["where"].items() if k.lower() not in coded} or None}
            try:
                out[s["id"]] = draw(corpus, s, None if src == "documents" else out.get(src, []))["documents"]
            except (ValueError, KeyError, TypeError):
                out[s["id"]] = []
    return out


def table_sizes(wf: dict, attributes, n_documents: int | None = None,
                sampled: dict[str, list[str]] | None = None) -> dict[str, int | None]:
    """Every tabulate step's cell count: every combination of its `by` columns' values is a cell, a count of none
    included; None where a column's size is not known (a free-text or numeric column, or an attribute given by
    name only). A column's size is its own value list, a codebook group's `max_items`, an attribute's distinct
    values (from `attribute_sizes`), or for "document" the count of documents the table counts: those its sample
    took (`sampled`, from `drawn`), or every document. The one place this is worked out, so
    `check` (which faults a write step whose tables alone could fill more than half its reading budget) and
    `run.estimate` (which prices a write step's reading by the same tables) size a table the same way."""
    wf = normalise(wf)
    attr_sizes = {a.lower(): n for a, n in attributes.items()} if isinstance(attributes, dict) else {}
    attr_sizes.update({a.lower(): n for a, n in document_attributes(wf).items() if n})
    made: dict[str, dict] = {}
    sizes: dict[tuple, int | None] = {}  # (code step, column): how many values it can take, where that is known
    base: dict[str, int | None] = {"documents": n_documents}  # step id: how many documents its output covers

    def cells(table, by, docs):
        n = 1
        for c in by:
            k = (docs if c == "document" else attr_sizes.get(c.lower()) if (table, c) not in sizes
                 else sizes[(table, c)])
            if not k:
                return None
            n *= k
        return n

    out: dict[str, int | None] = {}
    for s in wf.get("steps", []):
        sid, kind, ins = s.get("id"), s.get("kind"), s.get("inputs") or []
        src = [made[made[i]["table"]] if made.get(i, {}).get("table") else made.get(i) for i in ins if i in made]
        base[sid] = (len(sampled[sid]) if kind == "sample" and sampled and sid in sampled
                     else base.get(ins[0], n_documents) if ins else n_documents)
        if kind == "code":
            for c in s.get("columns") or []:
                if not isinstance(c, dict):  # a shape fault (reported by check's own _shape_faults); size nothing
                    continue
                vals = column_values(c)
                sizes[(sid, c.get("name"))] = len(vals) if vals else made.get(codebook_of(c) or "", {}).get("max_items")
            made[sid] = {"kind": kind}
        elif kind == "group":
            max_items = resolve_step(s, "group")["max_items"]
            made[sid] = {"kind": kind, "max_items": max_items}
            if s.get("assign") and len(src) == 1 and src[0] and src[0].get("kind") == "code":
                made[sid] = {"kind": kind, "table": ins[0], "max_items": max_items}
                sizes[(ins[0], "item")] = max_items
        elif kind == "tabulate":
            by = s.get("by")
            by = by if isinstance(by, list) else []
            if ins == ["documents"] or (len(src) == 1 and src[0] and src[0].get("kind") == "sample"):
                out[sid] = cells(None, by, base[sid])
            else:
                table = made[ins[0]].get("table", ins[0]) if ins and ins[0] in made else None
                out[sid] = cells(table, by, base[sid])
            if s.get("loops"):  # a loop table's cells are its loops' parts, which no design can know before the run
                out[sid] = base[sid] * SPARSE_CELLS_PER_DOCUMENT if base[sid] else out[sid]
            elif (s.get("sparse") or s.get("paths") or s.get("filters")) and out[sid] and base[sid]:
                out[sid] = min(out[sid], base[sid] * SPARSE_CELLS_PER_DOCUMENT)
            made[sid] = {"kind": kind}
        else:
            made[sid] = {"kind": kind}
    return out


def count_faults(sid: str, s: dict, attrs) -> list[str]:
    """What is wrong with what a tabulation counts: a count that is none of cases, documents, rows or a column of the
    document list, or a count by such a column that does not name its unit for a reader."""
    from .units import COUNTS
    count = s.get("count", "cases")
    if not isinstance(count, str) or (count not in COUNTS and count.lower() not in attrs):
        return [f"{sid}: count {count!r} is not cases, documents, rows or a column of the document list"]
    if count not in COUNTS and not s.get("unit"):
        return [f"{sid}: counts by {count!r}, so it names its unit for a reader, such as \"unit\": \"{count}s\""]
    return []


def check_against(wf: dict, corpus, standard_text: str | None = None) -> list[str]:
    """`check` against a run's corpus: its columns with their sizes, its documents, and its background documents."""
    return check(wf, attribute_sizes(corpus), len(corpus.documents), standard_text, corpus.background_texts(),
                 sampled=drawn(wf, corpus))


def check(wf: dict, attributes, n_documents: int | None = None, standard_text: str | None = None,
          background: dict[str, str] | None = None, sampled: dict[str, list[str]] | None = None) -> list[str]:
    """Every fault that would stop a runner carrying the workflow out, not only the first. `attributes` are the
    columns the corpus's document list really has, as names or (from `attribute_sizes`) with how many values each
    takes, and `n_documents` how many documents it lists. With the sizes, every table is sized before the run (by
    `table_sizes`): a write step whose tables alone could fill more than half its reading budget is a fault.
    `background` is the background documents' texts (`Corpus.background_texts`), which a judge's stated number is
    checked against."""
    from .judge import check_rubric
    wf = normalise(wf)
    given = {a.lower() for a in attributes}
    added = document_attributes(wf)
    attrs = given | {a.lower() for a in added}
    table_cells = table_sizes(wf, attributes, n_documents, sampled)
    faults: list[str] = [f"a per-document code step names a column {a!r}, which the document list already has"
                         for a in added if a.lower() in given]
    coded = {str(c.get("name")).lower(): column_values(c) for s in wf.get("steps", []) if s.get("kind") == "code" and s.get("per_document")
             for c in s.get("columns") or [] if isinstance(c, dict)}  # the values each coded document attribute takes
    made: dict[str, dict] = {}
    used: set[str] = set()
    steps = wf.get("steps", [])
    for s in steps:
        sid, kind, ins = s.get("id"), s.get("kind"), s.get("inputs") or []
        if kind not in KINDS:
            faults.append(f"{sid}: unknown kind {kind!r}")
            continue
        bad = _shape_faults(sid, kind, s)
        if bad:
            # a setting of the wrong shape is a fault to report, not a reason for the check to fail
            faults += bad
            made[sid] = {"kind": kind, "columns": {}}
            used.update(i for i in ins if isinstance(i, str))
            continue
        if sid in made:
            faults.append(f"{sid}: id used twice")
        for i in ins:
            if i != "documents" and i not in made:
                faults.append(f"{sid}: input {i!r} is not an earlier step")
            used.add(i)
        # a group step that assigns stands for its input table with the item column added
        src = [made[made[i]["table"]] if made.get(i, {}).get("table") else made[i] for i in ins if i in made]

        # a setting no piece of this kind reads would leave the workflow saying one thing and doing another
        faults += [f"{sid}: {k!r} is not a setting a {kind} step reads, so nothing would act on it"
                   for k in s if k not in settings_of(kind)]
        if kind in ("group", "write") and s.get("practice") not in (None, "all"):
            p = s["practice"]
            if not (isinstance(p, list) and all(isinstance(x, str) for x in p)):
                faults.append(f"{sid}: practice is not a list of page names")
            else:
                from . import guidance
                known = guidance.page_names()
                faults += [f"{sid}: practice names {x!r}, which is neither a practice note nor a method page"
                           for x in p if known is not None and x not in known]
        if kind == "sample":
            if ins != ["documents"] and not (len(ins) == 1 and made.get(ins[0], {}).get("kind") == "sample"):
                faults.append(f"{sid}: a sample draws from the documents or from one earlier sample")
            if s.get("documents") is not None:
                if not (isinstance(s["documents"], list) and s["documents"] and all(isinstance(d, str) for d in s["documents"])):
                    faults.append(f"{sid}: documents is not a list of document ids")
                if s.get("where") is not None:
                    faults.append(f"{sid}: a fixed list of documents and a where cannot both choose them")
            elif s.get("n") is None and not s.get("where"):
                faults.append(f"{sid}: says neither how many documents (n), which (documents) nor what they share (where)")
            elif s.get("n") is not None and (not isinstance(s["n"], int) or s["n"] < 1):
                faults.append(f"{sid}: n is not a positive whole number")
            if s.get("where") is not None:
                w = s["where"]
                if not (isinstance(w, dict) and w and all(isinstance(v, (str, int, float)) or (isinstance(v, list) and v)
                                                            for v in w.values())):
                    faults.append(f"{sid}: where is not {{column: value or list of values}}")
                else:
                    faults += [f"{sid}: where names {k!r}, which the document list does not have"
                               for k in w if k.lower() not in attrs]
                    faults += value_faults(f"{sid}: where names", w, coded)
            if s.get("stratify_by") and s["stratify_by"].lower() not in attrs:
                faults.append(f"{sid}: stratifies by {s['stratify_by']!r}, which the document list does not have")
            made[sid] = {"kind": kind}
        elif kind == "code":
            if not ins or any(i != "documents" and made.get(i, {}).get("kind") != "sample" for i in ins):
                faults.append(f"{sid}: a code step reads the documents or a sample")
            if not str(s.get("prompt", "")).strip():
                faults.append(f"{sid}: no coding prompt")
            cols = {}
            for c in s.get("columns") or []:
                t = c.get("type")
                if t not in TYPES:
                    faults.append(f"{sid}: column {c.get('name')!r} has type {t!r}")
                if t in ("nominal", "ordinal"):
                    g = codebook_of(c)
                    if g is not None:
                        if made.get(g, {}).get("kind") != "group":
                            faults.append(f"{sid}: column {c.get('name')!r} takes its codebook from {g!r}, not an earlier group step")
                        used.add(g)
                    elif not (isinstance(c.get("values"), list) and c["values"]):
                        faults.append(f"{sid}: column {c.get('name')!r} is {t} without values")
                    elif any(isinstance(v, dict) and not (v.get("name") or v.get("id")) for v in c["values"]):
                        faults.append(f"{sid}: column {c.get('name')!r} has a value without a name")
                cols[c.get("name")] = t
            if not cols:
                faults.append(f"{sid}: no columns")
            links = s.get("links")
            if links:
                faults += [f"{sid}: links names {links[k]!r} as a link's {k} end, which is not one of its columns"
                           for k in ("from", "to") if links[k] not in cols]
                if links.get("sign") and links["sign"] not in cols:
                    faults.append(f"{sid}: links names {links['sign']!r} as a link's sign, which is not one of its columns")
            made[sid] = {"kind": kind, "columns": cols, "links": links,
                         "values": {str(c.get("name")).lower(): column_values(c) for c in s.get("columns") or [] if isinstance(c, dict)}}
        elif kind == "group":
            made[sid] = {"kind": kind, "max_items": resolve_step(s, "group")["max_items"]}
            if len(src) != 1 or src[0]["kind"] != "code":
                faults.append(f"{sid}: a group step reads one code step")
                continue
            if src[0]["columns"].get(s.get("key_column")) != "free_text":
                faults.append(f"{sid}: key column {s.get('key_column')!r} is not a free-text column of {ins[0]}")
            for k, allowed in (("granularity", GRANULARITY), ("direction", DIRECTION)):
                if s.get(k) is not None and s[k] not in allowed:
                    faults.append(f"{sid}: {k} {s[k]!r}")
            if s.get("assign"):
                made[sid] = {"kind": kind, "table": ins[0], "max_items": resolve_step(s, "group")["max_items"]}
                made[ins[0]]["assigned"] = True
        elif kind == "tabulate" and (ins == ["documents"] or (len(src) == 1 and src[0]["kind"] == "sample")):
            # the document list itself, counted by its attributes
            for c in s.get("by") or []:
                if c.lower() not in attrs and c != "document":
                    faults.append(f"{sid}: counts the documents by {c!r}, which the document list does not have")
            faults += count_faults(sid, s, attrs)
            made[sid] = {"kind": kind, "by": s.get("by") or [], "cells": table_cells.get(sid),
                         "values": {str(c).lower(): coded.get(str(c).lower()) for c in s.get("by") or []}}
        elif kind == "tabulate":
            if len(src) != 1 or src[0]["kind"] != "code":
                faults.append(f"{sid}: a tabulate step reads one code step's table, or a group step that assigned items")
            else:
                for c in s.get("by") or []:
                    ok = (c in src[0]["columns"] or (c == "item" and src[0].get("assigned"))
                          or c.lower() in attrs or c == "document")
                    if not ok:
                        faults.append(f"{sid}: counts by {c!r}, which its input does not have")
            faults += count_faults(sid, s, attrs)
            if s.get("paths"):
                by = s.get("by") or []
                ends = src[0]["columns"] if len(src) == 1 and src[0]["kind"] == "code" else {}
                if len(by) < 2 or any(c not in ends for c in by[:2]):
                    faults.append(f"{sid}: traces paths, so its first two by columns are the two ends of a link its input coded")
                faults += [f"{sid}: traces paths, so {c!r} after a link's two ends must describe a document"
                           for c in by[2:] if c != "document" and (c.lower() not in attrs or c in ends)]
                if s.get("count", "cases") not in ("cases", "documents"):
                    faults.append(f"{sid}: traces paths, which are counted by the cases or documents whose links make them")
            if s.get("sequences"):
                links = src[0].get("links") if len(src) == 1 and src[0]["kind"] == "code" else None
                if not links:
                    faults.append(f"{sid}: lists told sequences, so its input must be a code step that names its links' two ends")
                elif list(s.get("by") or []) != [links["from"], links["to"]]:
                    faults.append(f"{sid}: lists told sequences, so it counts by its links' two ends, {links['from']!r} and {links['to']!r}, and nothing else")
                if s.get("paths") or s.get("loops"):
                    faults.append(f"{sid}: lists told sequences, so it neither traces paths nor finds loops")
                if s.get("count", "cases") not in ("cases", "documents"):
                    faults.append(f"{sid}: lists told sequences, which are counted by the cases or documents that tell them")
            if s.get("filters") and not (len(src) == 1 and src[0]["kind"] == "code" and src[0].get("links")):
                faults.append(f"{sid}: filters links, so its input must be a code step that names its links' two ends")
            own = src[0].get("values", {}) if len(src) == 1 and src[0] else {}  # a row's own value first, as the counting takes it
            made[sid] = {"kind": kind, "by": s.get("by") or [], "cells": table_cells.get(sid),
                         "values": {str(c).lower(): own[str(c).lower()] if str(c).lower() in own else coded.get(str(c).lower())
                                    for c in s.get("by") or []}}
            if s.get("loops"):
                links = src[0].get("links") if len(src) == 1 and src[0]["kind"] == "code" else None
                if not (links and links.get("sign")):
                    faults.append(f"{sid}: finds loops, so its input must be a code step whose links name their two ends and their sign")
                elif list(s.get("by") or []) != [links["from"], links["to"]]:
                    faults.append(f"{sid}: finds loops, so it counts by its links' two ends, {links['from']!r} and {links['to']!r}, and nothing else")
                if s.get("paths"):
                    faults.append(f"{sid}: finds loops or traces paths, not both")
                if s.get("count", "cases") not in ("cases", "documents"):
                    faults.append(f"{sid}: finds loops, which are counted by cases or documents")
                if not (isinstance(s.get("loop_links", 4), int) and 2 <= s.get("loop_links", 4) <= 6):
                    faults.append(f"{sid}: loop_links {s.get('loop_links')!r}; a loop has between 2 and 6 links")
                made[sid].update({"by": list(LOOP_COLUMNS), "values": {"polarity": list(POLARITIES), "part": list(PARTS)}})
            if s.get("sequences"):
                made[sid].update({"by": list(SEQUENCE_COLUMNS), "values": {}})
        elif kind == "judge":
            faults += check_rubric(sid, s, made, attrs, n_documents, standard_text, background, coded)
            made[sid] = {"kind": kind}
        elif kind == "write":
            # a code step's rows are a table too: one summary row a document is the simplest
            if not any(made.get(i, {}).get("kind") in ("tabulate", "judge", "code", "group") for i in ins):
                faults.append(f"{sid}: writes from no table, tabulation or verdict")
            n = sum(made[i].get("cells") or 0 for i in ins if made.get(i, {}).get("kind") == "tabulate")
            budget = resolve_step(s, "write")["reading_tokens"]
            if n * TABLE_CELL_TOKENS > budget / 2:
                faults.append(f"{sid}: its tables could hold up to {n:,} cells, about {n * TABLE_CELL_TOKENS:,} tokens, more than "
                              f"half the {budget:,} it reads; count by fewer columns, each table answering one comparison, or set sparse on a table whose combinations mostly cannot occur")
            made[sid] = {"kind": kind}
    if not steps or steps[-1].get("kind") != "write":
        faults.append("the workflow does not end by writing")
    for k, s in enumerate(steps):  # a per-document step is used where a later step names one of its columns
        if s.get("kind") == "code" and s.get("per_document"):
            names = {c.get("name", "").lower() for c in s.get("columns") or [] if isinstance(c, dict)}
            later = json.dumps(steps[k + 1:]).lower()
            if any(f'"{n}"' in later for n in names if n):
                used.add(s.get("id"))
    for s in steps[:-1]:
        if s.get("id") not in used:
            faults.append(f"{s.get('id')}: its output is never used")
    return faults


def sections(text: str, size: int = SECTION_CHARS) -> list[str]:
    """The text in parts of about `size` characters, cut at line breaks, and a line longer than `size` at sentence
    ends. (Cutting at blank lines alone left transcripts that have almost none in parts of 27,000 characters.)"""
    pieces: list[str] = []
    for line in text.split("\n"):
        pieces += re.split(r"(?<=[.!?])\s+", line) if len(line) > size else [line]
    parts, cur = [], ""
    for piece in pieces:
        if cur and len(cur) + len(piece) > size:
            parts.append(cur)
            cur = ""
        cur += piece + "\n"
    return parts + [cur] if cur.strip() else parts
