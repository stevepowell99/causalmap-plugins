"""The open format: what a run's folder, its workflow and its zip hold, written once for a reader outside Rubicon, with
the schema a workflow is checked against and the check itself.

`readme` writes the format's README and `schema` its `workflow.schema.json`. Both are made from what this engine
defines (`workflow.KINDS`, `workflow.settings_of`, `workflow.resolve_step`, `workflow.TYPES`, `steps.CELL_IDS`) and
from the meanings below, which `rubicon/tests/test_the_open_format.py` holds to those definitions, so the format cannot
fall behind the engine: a setting the engine reads and this file does not define fails the suite, and so does a
schema that differs from the newest published version. `faults` checks a workflow against the schema with the
standard library alone; `recount.py` runs it on every workflow it recounts and reports what it finds, as `format` in
`recount/report.json`. A published version lives under `webapp/rubicon/spec/<version>/` in the repository, written by
`rubicon/tools/publish_format.py`, and never changes.

The defaults the README gives are this engine's standing alone, as a recount runs: a harness that calls models names
them when it loads (`models.py`), so `readme` refuses to run once one has, rather than publish one harness's choices
as the format's.
"""
from __future__ import annotations

import json
import re

from . import models, workflow as W
from .run_id import ID as RUN_ID
from .steps import CELL_IDS

#: The version of the format this engine reads and writes, which is the newest published one.
VERSION = "0.4"
#: Where the published versions are served, each under its own number.
BASE = "https://app.causalmap.app/rubicon/spec"

STR, BOOL, INT = {"type": "string"}, {"type": "boolean"}, {"type": "integer"}
STRS = {"type": "array", "items": STR}
#: {column: value or list of values}, as a `where` or a `holds` gives it
WHERE = {"type": "object", "additionalProperties": {"type": ["string", "number", "boolean", "array"]}}

#: The top level of a workflow: each key, its schema and what it holds.
TOP = {
    "question_as_agreed": (STR, "The question the run answers, in the evaluator's words as agreed with them, one question "
                                "a line where there are several. The report takes its title and file name from it."),
    "run_id": ({"type": "string", "pattern": f"^{RUN_ID.pattern}$"},
               "The run's ID, such as `2026-10-09-k7q2`: the date the run started and four characters, given once and "
               "kept through every revision. A run made before IDs were given has none."),
    "cell_ids": ({"enum": list(CELL_IDS)},
                 "How the tables name their cells (see Cells and their ids). The recount records it in the workflow it "
                 "writes. A workflow without it is read as `coordinates` in a folder never recounted before, and "
                 "otherwise as the last recount read it, `positional` where that recorded nothing."),
    "legacy_weak_rows": (BOOL, "Present only in a run made before 15 October 2026 whose rows carry a `weak` mark: "
                               "those rows are then counted beside each cell, as `<cell id>.weak`, as they were when "
                               "the run was made."),
    "steps": ({"type": "array", "items": {"$ref": "#/$defs/step"}}, "The steps, in the order they run."),
}

#: What each kind of step does.
KIND = {
    "sample": "Chooses the documents later steps read, from all the documents or from an earlier sample: those the "
              "document list's attributes pick (`where`) or a fixed list (`documents`), then how many cases of those "
              "to draw (`n`), each case drawn with all its documents. A `where` that keeps no document stops the run.",
    "code": "A table of coded passages: one row for each quotation, with the columns the step defines. The rows are coded by "
            "whoever carries out the run and recorded in `coded/<step id>.json`; the recount finds each quotation in its "
            "document, drops and lists one it cannot find, gives each row its id and stores each value in the one "
            "spelling its column lists. With `per_document`, each document gets one row and each column becomes a "
            "document attribute for the steps after it. A code step may instead take its rows from an earlier run "
            "(`from`), or name two or more earlier code steps as its `inputs` and code nothing: their rows are then "
            "put together as one table, each keeping its id and gaining a `coding` column naming the step it came "
            "from, with the columns and `links` the inputs share.",
    "group": "A codebook drawn from the open labels of a free-text column, recorded in `judged/<step id>.json`, each "
             "item naming the labels it gathers. The recount gives every row the item its label is gathered into and "
             "reports any label placed nowhere or under two items; with `assign`, the table it hands on is its input's "
             "rows with each one's item.",
    "profile": "One row for each unit a key names (a case, a document, a value of a document attribute or of a coded "
               "column), describing what all that unit's coded rows hold together, so that a count can span passages. "
               "Every unit among the documents read is a row, one without a coded row a row of noes.",
    "tabulate": "Counts a table by fixed rules: by any of its columns, by the item a group step assigned or by a document "
                "attribute, counting cases, documents, passages or the values of a document attribute. Every "
                "combination the columns allow is a cell, a count of none included, and each cell carries its own base "
                "and the rows behind it. With `paths`, `sequences` or `loops`, the cells are chains of causal links "
                "rather than combinations of values.",
    "judge": "Applies the evaluator's rubric to the tables: each criterion is a rule (a count in a table's cells against "
             "the thresholds the standard states), a stated number (a count and its base quoted from a background "
             "document) or a reading (the rows weighed against each level's descriptor, recorded in "
             "`judged/<step id>.json`), and the criteria combine into the overall verdict by rules, never an average. "
             "Every level says whether it is the evaluator's, with the words of the standard it rests on, or proposed, "
             "and a proposed level waits until the evaluator accepts it.",
    "claims": "The answer's key claims that do not rest on a count, recorded in `judged/<step id>.json`, each with the rows it "
              "rests on and those against it. The answer cites one as `[<step id>.<claim id>]`, and "
              "a claim that does not cite a row, or cites a row its inputs do not hold, stops the report.",
    "write": "Says that the answer is written, and from which steps; the answer itself is `answer.md`. Its settings are "
             "instructions to whoever writes it, and a runner that writes with a model reads the rest. The recount "
             "checks the answer, never how it was written.",
}

#: Every setting each kind of step has, beside `id`, `kind` and `inputs`: its schema and what it does. Settings whose
#: meaning begins "Where a runner" are read only by a runner that calls models; a recount reads none of them.
_RUNNER = "Where a runner calls models: "
SETTINGS = {
    "sample": {
        "n": ({"type": "integer", "minimum": 1}, "How many cases to draw from the documents chosen, each with all its "
                                                 "documents; left out, every one of them."),
        "seed": (INT, "The seed of the random draw, so that the same sample is drawn again."),
        "stratify_by": (STR, "A document attribute the draw is spread across; null draws without strata."),
        "documents": (STRS, "A fixed list of document ids, taken as they stand; an id the corpus lacks is listed."),
        "where": (WHERE, "{attribute: value or list of values}: only the documents whose attributes hold those values."),
    },
    "code": {
        "prompt": (STR, "The coding instructions in full, as whoever codes reads them before each document."),
        "columns": ({"type": "array", "items": {"$ref": "#/$defs/column"}},
                    "The columns each row carries beside its document and quotation (see Columns)."),
        "per_document": (BOOL, "True where the columns describe each document as a whole: one row for each document, each "
                               "column then a document attribute for later steps."),
        "links": ({"$ref": "#/$defs/links"}, "The two columns that are a causal link's ends, and for a causal loop "
                                             "diagram the column giving its sign, so that each row is a link that "
                                             "tabulations can trace, filter and count."),
        "section_chars": (INT, "How many characters a coder reads at a time; at or above the longest document's "
                               "length, each document is read whole."),
        "from": ({"$ref": "#/$defs/from"}, "The earlier run this step is taken from, in place of coding it here (see "
                                           "Steps taken from an earlier run)."),
        "cited": (BOOL, "True where the rows were not coded from the documents but cited afterwards, by whoever wrote "
                        "the answer, for the numbers it gives: what was read is then not recorded, and every count "
                        "rests only on the passages cited."),
        "prompt_note": (STR, "Text added to the first coder's instructions alone."),
        "model": (STR, _RUNNER + "the model that codes."),
        "thinking": (STR, _RUNNER + "the reasoning effort the coding model runs at; null, its family's own."),
        "second_coder": ({"type": ["string", "boolean"]},
                         _RUNNER + "a model of another family that codes every document as well, where every column "
                                   "has a fixed list of values; true names the runner's own, false or null none."),
        "second_prompt_note": (STR, _RUNNER + "text added to the second coder's instructions alone."),
        "second_thinking": (STR, _RUNNER + "the second coder's reasoning effort; null, its provider's own."),
        "second_section_chars": (INT, _RUNNER + "how much the second coder reads at a time; null, as the first."),
        "second_retry_thinking": (STR, _RUNNER + "the effort a second coder's section is read at again when its reply "
                                                 "ran out; null, never read again."),
        "adjudicator": (STR, _RUNNER + "the model that rules on each value only one of the two coders placed."),
        "adjudicator_thinking": (STR, _RUNNER + "the adjudicator's reasoning effort."),
        "check": (BOOL, _RUNNER + "true to have a second model read every coded passage in its context and keep, "
                                  "recode or drop it."),
        "check_model": (STR, _RUNNER + "the model that makes that check."),
    },
    "group": {
        "key_column": ({"type": ["string", "array"], "items": STR},
                       "The free-text column whose labels the codebook gathers, or a list of them, such as a link's "
                       "cause and effect, which then share one codebook."),
        "assign": (BOOL, "True to give every row of the input its item: in a column `item`, or with several key "
                         "columns in `<column>_item` beside each (a soft recode). False for the codebook alone, as a "
                         "hard recode, which codes the documents again against it, needs."),
        "granularity": ({"enum": list(W.GRANULARITY)}, "How fine the items are: headline, standard or detailed."),
        "max_items": (INT, "The most items the codebook holds."),
        "direction": ({"enum": list(W.DIRECTION)},
                      "How the direction of a change is kept: `column`, as a column of its own, so that helped and "
                      "harmed share an item; `items`, one item for each side; `none`, not kept."),
        "multi": (BOOL, "True where one row may take several items."),
        "item_is": (STR, "What one item is, as whoever draws the codebook is told."),
        "practice": ({"type": ["array", "string"], "items": STR, "pattern": "^all$"},
                     "The guidance pages whoever draws the codebook reads, by name, or `all`."),
        "model": (STR, _RUNNER + "the model that draws the codebook."),
        "thinking": (STR, _RUNNER + "its reasoning effort."),
        "assign_model": (STR, _RUNNER + "the model that gives each row its item."),
    },
    "profile": {
        "key": (STR, "What one row is: `case` (a document, or a whole case where the document list's `case` column "
                     "groups several documents or the rows carry a `case` column), `document`, a column of the "
                     "document list, or a column the input coded, such as `item`."),
        "columns": ({"type": "array", "items": {"$ref": "#/$defs/profile_column"}},
                    "What each row says of its unit (see Profile columns)."),
    },
    "tabulate": {
        "by": (STRS, "The columns counted by: columns of the input table, `item` where a group step assigned items, "
                     "or document attributes."),
        "count": (STR, "What one count counts: `cases`, `documents`, `rows` (the coded passages, which says how much "
                       "was said and never how many said it), or a column of the document list, each of whose values "
                       "among the documents read is one case."),
        "unit": (STR, "The plural a reader is given for what is counted, such as households; left out, documents "
                      "where each case is one document and cases where not."),
        "description": (STR, "One sentence saying what the table counts and out of what, shown above it."),
        "where": (WHERE, "{column: value or list of values}: only the rows holding those values are counted, in a coded "
                         "column or a column of the document list, and every count stays out of all the cases read. A "
                         "value the column neither lists nor holds stops the run rather than reading as none."),
        "sparse": (BOOL, "True to list only the combinations that occur, as an edge list, rather than every "
                         "combination with its zeros."),
        "paths": (BOOL, "True where the first two `by` columns are a link's two ends: a cell is a pair where the second "
                        "is reached from the first by following one document's own links, directly or through others, "
                        "counted by the documents whose links make it. Links are never joined across documents."),
        "sequences": (BOOL, "True where `by` is a link's two ends: each cell is one chain a speaker told as one, built "
                            "from the rows one document gives the same `sequence` in the order of their `step`."),
        "loops": (BOOL, "True where the input's `links` name a sign: the cells are the feedback loops all documents' "
                        "signed links make together, each with its polarity, the documents telling it whole, each of "
                        "its links and each link into it."),
        "loop_links": (INT, "The most links a loop may have."),
        "through": (STRS, "Only the loops through one of these variables."),
        "filters": ({"type": "array", "items": {"$ref": "#/$defs/filter"}},
                    "Link filters applied in order to the input's links before anything is counted, such as path "
                    "tracing, zoom, collapse, combining opposites and frequency, each `{\"type\", ...its settings}` "
                    "as Causal Map stores them."),
    },
    "judge": {
        "source": (STR, "Whose standard it is, or the document it is quoted from."),
        "verdicts": ({"type": "array", "items": {"$ref": "#/$defs/verdict"}}, "The overall verdicts, best first."),
        "criteria": ({"type": "array", "items": {"$ref": "#/$defs/criterion"}}, "The criteria (see Rubrics)."),
        "combine": ({"anyOf": [{"title": "weakest, best or separate", "enum": ["weakest", "best", "separate"]},
                               {"title": "a list of the evaluator's rules", "type": "array", "items": {"type": "object"}}]},
                    "How the criteria give the overall verdict: `weakest` (every criterion must hold), `best` (either "
                    "route will do), `separate`, or the standard's own rules, tried in order, each `{\"verdict\", "
                    "\"when\": {criterion id: level or list of levels}}`, the last with no `when`."),
        "accepted": ({"type": ["string", "boolean"]},
                     "When the evaluator accepted the proposed levels, as `agree.py` records it (the date, such as "
                     "`2026-10-09`, or `for a test` and a date), or true where the date was not recorded; the recount "
                     "places no proposed level until this is given."),
        "model": (STR, _RUNNER + "the model that makes the readings."),
    },
    "claims": {},
    "write": {
        "instructions": (STR, "What the answer covers, and in which order."),
        "words": (INT, "About how long the answer is, in words."),
        "practice": ({"type": ["array", "string"], "items": STR, "pattern": "^all$"},
                     "The guidance pages whoever writes reads, by name, or `all`."),
        "workings": (BOOL, "True to append every table of counts, in plain labels, under the answer."),
        "documents": (BOOL, _RUNNER + "true to give the writer the documents in full as well as the rows."),
        "skim": (BOOL, _RUNNER + "true to give the writer a short map of every document."),
        "reading_tokens": (INT, _RUNNER + "the most one write call reads, in tokens."),
        "rows_per_cell": (INT, _RUNNER + "how many rows the writer reads from each cell; null, every row."),
        "picker_model": (STR, _RUNNER + "the model that picks those rows."),
        "review": (BOOL, _RUNNER + "true for a second call that rewrites the draft against the same material."),
        "review_model": (STR, _RUNNER + "the model that reviews."),
        "trail": (BOOL, _RUNNER + "true to say what each finding rests on and list those resting on nothing."),
        "trail_model": (STR, _RUNNER + "the model that tells findings from framing."),
        "trail_repair": (BOOL, _RUNNER + "true for one round that cites, quotes or cuts each unsourced finding."),
        "repair_model": (STR, _RUNNER + "the model of that round."),
        "model": (STR, _RUNNER + "the model that writes."),
        "thinking": (STR, _RUNNER + "the reasoning effort of the writing calls; null, each model family's own."),
    },
}

#: A code step's column: each key, its schema and what it holds.
COLUMN = {
    "name": (STR, "The column's name, which a row gives its value under."),
    "type": ({"enum": list(W.TYPES)}, "`free_text` (a label in the coder's words), `binary` (yes or no), `nominal` "
                                      "(one value from a list), `ordinal` (one value from an ordered list) or `numeric`."),
    "means": (STR, "What the column records, written for a reader of the answer."),
    "values": ({"type": ["array", "string"], "items": {"$ref": "#/$defs/value"}, "pattern": "^codebook:"},
               "The values a nominal or ordinal column takes, each a name or `{\"name\", \"means\", \"counts\", "
               "\"does_not_count\"}`, best or first first for an ordinal; or `codebook:<group step id>`, the items of "
               "that step's codebook."),
    "from": (STR, "A column of the same step, listed before this one, whose value fills this one through `map`, "
                  "so that it is never coded."),
    "map": ({"type": "object", "additionalProperties": {"type": ["string", "number"]}},
            "{value of the `from` column: value of this one}; a row whose value the map does not hold is left blank "
            "and listed."),
    "weak": (STR, "In a run carrying `legacy_weak_rows` only: what a weak row of this column meant."),
}
#: A column value given as an object.
VALUE = {
    "name": (STR, "The value as rows hold it."),
    "id": (STR, "The value's id, where it has no name."),
    "means": (STR, "What it means."),
    "counts": (STR, "What counts as it."),
    "does_not_count": (STR, "What does not count as it, and where such a passage goes instead."),
}
#: A profile step's column, with one of `holds`, `values`, `distinct`, `first` and `last`.
PROFILE_COLUMN = {
    "name": (STR, "The column's name."),
    "holds": (WHERE, "{column: value or list}: yes where any of the unit's rows has those values, no otherwise."),
    "values": (STR, "A column: the values the unit's rows hold in it, as a list."),
    "distinct": (STR, "A column, coded or of the document list: how many different values the unit's rows carry."),
    "first": (STR, "A column: its value in the unit's first row."),
    "last": (STR, "A column: its value in the unit's last row."),
    "order": (STR, "For `first` and `last`, the column the rows are ordered by; left out, where they stand in the text."),
}
LINKS = {
    "from": (STR, "The column holding a link's cause."),
    "to": (STR, "The column holding its effect."),
    "sign": (STR, "For a causal loop diagram, a nominal column whose values are plus, minus and unclear, over variables "
                  "each named positively."),
}
FROM = {
    "run_id": ({"type": ["string", "null"]}, "The earlier run's ID, null where it has none."),
    "fingerprint": (STR, "The fingerprint the earlier run's report prints: the first eight characters are enough where "
                         "they name one zip, and the recount writes the whole of it into the workflow it ran."),
    "step": (STR, "The code step's id there, which must be this step's id too, so that every row keeps its id."),
    "take": ({"enum": ["rows", "definitions"]}, "`rows` (the default: the earlier run's coded and checked rows) or "
                                                "`definitions` (its columns only, coded afresh here)."),
    "documents": (STRS, "The documents the earlier run's rows come from, which the recount writes in."),
}
VERDICT = {"name": (STR, "The verdict."), "means": (STR, "What it means.")}

#: The files of a run's folder: each path, who writes it, and what it holds. `<id>` is a step's id.
FOLDER = [
    ("corpus/index.csv", "when the run starts",
     "One row for each document: `id`, `file` (its text file in `corpus/`) and optionally `title`, `case` (documents sharing a "
     "case are one case, such as one person interviewed twice), `characters` and `synthetic`. Every other column is a "
     "document attribute, which a step can sample by, count by or base a count on."),
    ("corpus/<file>", "when the run starts", "Each document's text, copied whole. Its line endings are read as one newline."),
    ("background/", "when the run starts", "A project's background documents, such as a programme description or a "
                                           "monitoring record, with an `index.csv` giving each `id`, `title` and "
                                           "`file`: quoted, never coded or counted."),
    ("workflow.json", "the analyst", "The workflow (see The workflow)."),
    ("coded/<id>.json", "the analyst", "The rows a code step was coded with (see Coded rows)."),
    ("judged/<id>.json", "the analyst", "A group step's codebook, a judge step's readings or a claims step's claims "
                                        "(see Recorded judgements)."),
    ("answer.md", "the analyst", "The answer (see The answer)."),
    ("work/agreements.json", "the analyst, through `agree.py`",
     "Each thing put to the evaluator to agree, as a list of `{what, held, asked, via, action, answers, changes, at, "
     "rows_cited_before}`: `held` keeps what the run held of it then, `answers` each question put with its options "
     "and what was chosen, and `rows_cited_before` how many rows had been coded by then, which shows whether it was "
     "agreed before the documents were coded."),
    ("work/", "the analyst", "The rest of the audit trail: scripts and their output, the briefs given to helpers and "
                             "what they returned, and `procedure.md`, an account of how the run was carried out."),
    ("recode/", "a second coder", "A second, blind coding of the same workflow: `coded/`, its own recount, "
                                  "`unclear.md` (where the second coder found a definition unclear), "
                                  "`disagreements.md` (each value one coder placed and the other did not, with both "
                                  "coders' passages, written by `compare.py`) and `readers.json`, which says whether "
                                  "the second coding and the check were made by a reader separate from the analyst."),
    ("check.md", "the checker", "The check: a fresh reader's reading of the answer against the passages it cites and "
                                "the documents, its ruling on each disagreement, and what it corrected."),
    ("earlier/<zip>", "the recount", "The sealed zip of each earlier run a step is taken from."),
    ("revisions.md", "the analyst", "Each revision of the finished run, dated: what was asked, and what changed in the "
                                    "workflow, the coding and the answer."),
    ("recount/", "the recount", "What fixed rules recount from the files above (see The recount)."),
    ("recount-before/", "the analyst", "The recount as it stood before a substantive revision, which `stale.py` "
                                       "compares with the new one."),
    ("`<question>-<date>-<fingerprint>.html`, `.doc` and `.zip`", "`render_report.py`",
     "The report, its Word copy and the run's sealed zip, sharing one name; `-revision-<n>` comes before the "
     "fingerprint once the run has been revised, and each earlier revision's three files stay beside them."),
]

#: What `recount/` holds.
RECOUNT = [
    ("workflow.json", "The workflow as recounted: `cell_ids` recorded, each step taken from an earlier run filled in "
                      "from that run, and, on a code step that puts others together, the columns and links they share."),
    ("steps/<id>.json", "Each step's record: a code step's rows with their ids, places and values, the quotations "
                        "dropped and the values off the list; a group step's codebook and checks; a tabulation's cells, "
                        "each with its count, base, documents and rows; a judge step's verdicts with every count tested; "
                        "and the write step's answer with its checks."),
    ("rows.md", "Every coded row, with its id."),
    ("tables.md", "Every table and verdict, with the id of every cell."),
    ("counts.json", "Every count, by its id."),
    ("report.json", "What every check found: the workflow's faults, the coding of each code step, the answer's counts, "
                    "citations and quotations, and warnings to weigh against the documents (`audit`)."),
    ("answer.resolved.md", "The answer with its ids replaced by their counts and its row citations by each row's document "
                           "and the opening words of its quotation."),
    ("run.json", "The question, and that the run was recounted."),
    ("corpus/, background/, judged/", "Copies of the run's own."),
]

#: What a run's zip holds, by its path there, and where in the run folder it comes from. Each pattern is matched
#: against every file of every committed example zip by the test.
ZIP = [
    ("workflow.json", "`recount/workflow.json`"),
    ("run.json", "`recount/run.json`"),
    ("counts.json", "`recount/counts.json`"),
    ("report.json", "`recount/report.json`"),
    ("steps/<id>.json", "`recount/steps/`"),
    ("corpus/<file>", "`recount/corpus/`"),
    ("background/<file>", "`recount/background/`"),
    ("answer.md", "`answer.md`, as written, cell ids and all"),
    ("revisions.md", "`revisions.md`"),
    ("coded/<id>.json", "`coded/`"),
    ("judged/<id>.json", "`judged/`"),
    ("earlier/<zip>", "`earlier/`"),
    ("work/<path>", "`work/`"),
    ("check/check.md", "`check.md`"),
    ("check/disagreements.md, check/unclear.md, check/readers.json", "`recode/`"),
    ("check/coded/<id>.json", "`recode/coded/`, the second coder's rows"),
    ("render.json", "The name and date the report was created under, and the fingerprint and version of the engine "
                    "that created it"),
    ("SHA256SUMS", "The seal: the SHA-256 of every other file, in the form `sha256sum -c` reads"),
]


def _with_null(s: dict) -> dict:
    """A setting's schema allowing null, since a step that gives null for a setting takes its default."""
    if "type" in s:
        t = s["type"] if isinstance(s["type"], list) else [s["type"]]
        return {**s, "type": t + ["null"]}
    if "enum" in s:
        return {**s, "enum": s["enum"] + [None]}
    if "anyOf" in s:
        return {**s, "anyOf": s["anyOf"] + [{"title": "null", "type": "null"}]}
    return {"anyOf": [s, {"title": "null", "type": "null"}]}


def _properties(table: dict, null: bool = False) -> dict:
    return {k: {**(_with_null(s) if null else s), "description": meaning} for k, (s, meaning) in table.items()}


def schema() -> dict:
    """The JSON Schema (2020-12) a workflow is checked against: the keys the format defines at every level and no
    others, since a key the engine does not read would leave the workflow saying one thing and doing another."""
    step = {"type": "object", "required": ["id", "kind", "inputs"],
            "properties": {"kind": {"enum": list(W.KINDS)}},
            "allOf": [{"if": {"properties": {"kind": {"const": k}}, "required": ["kind"]},
                       "then": {"$ref": f"#/$defs/{k}"}} for k in W.KINDS]}
    common = {"id": {**STR, "description": "The step's id, unique in the workflow; the ids of its rows, cells and "
                                           "claims begin with it."},
              "inputs": {**STRS, "description": "The ids of the earlier steps it reads, or `documents` for all of them."}}
    kinds = {}
    for k in W.KINDS:
        own = _properties(SETTINGS[k], null=True)
        kinds[k] = {"type": "object", "description": KIND[k], "additionalProperties": False,
                    "properties": {**common, "kind": {"const": k},
                                   "settings": {"type": "object", "additionalProperties": False, "properties": own,
                                                "description": "Settings may sit here rather than on the step itself."},
                                   **own}}

    def obj(table, required=()):
        return {"type": "object", "additionalProperties": False, "properties": _properties(table),
                **({"required": list(required)} if required else {})}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}/{VERSION}/workflow.schema.json",
        "title": f"A Rubicon workflow, open format {VERSION}",
        "description": "The steps a run carried out to answer one evaluation question from a folder of documents. "
                       f"The format's README, {BASE}/{VERSION}/, says what each key means.",
        "type": "object", "required": ["steps"], "additionalProperties": False, "properties": _properties(TOP),
        "$defs": {"step": step, **kinds,
                  "column": obj(COLUMN, ("name", "type")),
                  "value": {"type": ["string", "number", "object"], "additionalProperties": False,
                            "properties": _properties(VALUE)},
                  "profile_column": obj(PROFILE_COLUMN, ("name",)),
                  "links": obj(LINKS, ("from", "to")),
                  "from": obj(FROM, ("fingerprint", "step")),
                  "verdict": obj(VERDICT, ("name",)),
                  "criterion": {"type": "object", "required": ["id", "kind"],
                                "properties": {"id": STR, "kind": STR},
                                "description": "A criterion as the rubric check reads it: `id`, `question`, `kind` "
                                               "(rule, stated or reading) and `levels`, with the settings its kind "
                                               "reads (see Rubrics)."},
                  "filter": {"type": "object", "required": ["type"], "properties": {"type": STR}}}}


# The check, for the parts of JSON Schema `schema` uses: type, enum, const, pattern, minimum, properties, required,
# additionalProperties, items, anyOf, allOf with if/then, and $ref within the document.
_JSON = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _JSON[t])


def _kind_of(v) -> str:
    return next(t for t in ("null", "boolean", "integer", "number", "string", "array", "object") if _is(v, t))


def _errors(v, s: dict, root: dict, path: str) -> list[str]:
    if "$ref" in s:
        s = {**root["$defs"][s["$ref"].rsplit("/", 1)[1]], **{k: x for k, x in s.items() if k != "$ref"}}
    out: list[str] = []
    if "type" in s:
        types = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is(v, t) for t in types):
            return [f"{path} is {_kind_of(v)}, where the format has {' or '.join(types)}"]
    if "const" in s and v != s["const"]:
        out.append(f"{path} is {json.dumps(v)}, where the format has {json.dumps(s['const'])}")
    if "enum" in s and v not in s["enum"]:
        return [f"{path} is {json.dumps(v, ensure_ascii=False)}, which is not one of "
                + ", ".join(json.dumps(x) for x in s["enum"])]
    if "anyOf" in s and not any(not _errors(v, a, root, path) for a in s["anyOf"]):
        return [f"{path} is {json.dumps(v, ensure_ascii=False)[:80]}, which is none of: "
                + "; ".join(a.get("title", "") for a in s["anyOf"])]
    if isinstance(v, str) and "pattern" in s and not re.search(s["pattern"], v):
        out.append(f"{path} is {json.dumps(v, ensure_ascii=False)[:80]}, not of the form {s['pattern']}")
    if _is(v, "number") and "minimum" in s and v < s["minimum"]:
        out.append(f"{path} is {v}, below its least, {s['minimum']}")
    if isinstance(v, dict):
        props = s.get("properties", {})
        out += [f"{path} has no {k!r}" for k in s.get("required", []) if k not in v]
        for k, x in v.items():
            if k in props:
                out += _errors(x, props[k], root, f"{path}.{k}")
            elif s.get("additionalProperties") is False:
                out.append(f"{path}.{k} is not in the open format {VERSION}")
            elif isinstance(s.get("additionalProperties"), dict):
                out += _errors(x, s["additionalProperties"], root, f"{path}.{k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            out += _errors(x, s["items"], root, f"{path}[{i}]")
    for a in s.get("allOf", []):
        if "if" in a and not _errors(v, a["if"], root, path):
            out += _errors(v, a["then"], root, path)
    return out


def faults(wf) -> list[str]:
    """Where a workflow departs from the format's schema, each said once, with the step's id where it is in a step.
    Empty means it conforms."""
    found = _errors(wf, schema(), schema(), "workflow")
    steps = wf.get("steps") if isinstance(wf, dict) else None

    def named(m: str) -> str:  # "workflow.steps[3].by" read as "step t_bar (steps[3]): by"
        got = re.match(r"workflow\.steps\[(\d+)\]\.?", m)
        if not got or not isinstance(steps, list):
            return m.removeprefix("workflow.") if m.startswith("workflow.") else m
        st = steps[int(got.group(1))]
        sid = st.get("id") if isinstance(st, dict) else None
        rest = m[got.end():]
        return f"step {sid or '?'} (steps[{got.group(1)}])" + (f": {rest}" if rest and not rest.startswith(" ") else rest)
    return [named(m) for m in found]


def checked(wf) -> dict:
    """The check as a recount records it: against which version and schema, how many steps it read, and what it found."""
    return {"version": VERSION, "schema": f"{BASE}/{VERSION}/workflow.schema.json",
            "steps_checked": len(wf.get("steps") or []) if isinstance(wf, dict) else 0, "faults": faults(wf)}


# The README.

#: The least of each kind of step: what a step must say for itself, so that everything else shows its default.
_STUBS = {"sample": {"n": 10}, "code": {"prompt": "...", "columns": [{"name": "c", "type": "nominal", "values": ["a"]}]},
          "group": {"key_column": "<key column>"}, "profile": {"columns": []}, "tabulate": {},
          "judge": {"source": "...", "verdicts": [], "criteria": []}, "claims": {}, "write": {}}
#: The switch each dependent setting is read under, shown with it.
_SWITCHES = {"code": {"second_coder": "a second coder", "check": True}, "group": {"assign": True},
             "write": {"review": True, "trail_repair": True}}


def _shown(v) -> str:
    return "none" if v is None else str(v).lower() if isinstance(v, bool) else f"`{json.dumps(v, ensure_ascii=False)}`"


def _defaults(kind: str) -> dict[str, str]:
    """Each setting's default as the README gives it, from `resolve_step` itself."""
    stub = {"id": "s", "kind": kind, "inputs": [], **_STUBS[kind]}
    base = W.resolve_step(stub)
    out = {k: _shown(v) for k, v in base.items()}
    for switch, value in _SWITCHES.get(kind, {}).items():
        on = W.resolve_step({**stub, switch: value})
        out.update({k: f"{_shown(v)} where `{switch}` is set" for k, v in on.items() if k not in base})
    if kind == "group":
        out["max_items"] = ", ".join(f"{W.resolve_step({**stub, 'granularity': g})['max_items']} ({g})" for g in W.GRANULARITY)
    for k in W.GIVEN.get(kind, ()):  # what a step gives for itself, or leaves out to the effect its meaning says
        out[k] = "no default"
    return out


def _table(head: tuple, rows) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows])


def _keys(table: dict) -> str:
    return _table(("Key", "What it holds"), ((f"`{k}`", m) for k, (_, m) in table.items()))


def readme(status: str = "Draft of the next version, not yet published: anything here may change.") -> str:
    """The format's README for this engine, under `status` (the line saying which version it is)."""
    if models.CODER is not None:
        raise RuntimeError("a harness has named the models, so the defaults are its own: write the format from the "
                           "engine standing alone (python -I, with only rubicon/open on the path)")
    kinds = []
    for k in W.KINDS:
        d = _defaults(k)
        rows = [(f"`{s}`", d.get(s, "none"), m) for s, (_, m) in SETTINGS[k].items()]
        kinds.append(f"### {k}\n\n{KIND[k]}\n\n" + (_table(("Setting", "Default", "What it does"), rows) if rows
                                                     else "It has no settings beside `id`, `kind` and `inputs`."))
    return f"""<!-- Generated by rubicon/open/rubicon_open/format.py (readme). Edit that file, never this one. -->
# The Rubicon open format

{status}

Reader: anyone who wants to read, check, recount or produce a run without Rubicon: an evaluator's analyst, a commissioner's adviser, or the builder of another tool.

A run answers an evaluation question from a folder of documents, and is kept as plain files: the documents, a workflow of steps, the rows coded for each coding step, the codebooks, readings and claims recorded for the steps that need a judgement, and the answer. Fixed rules then recount every number from those files and check every quotation against its document. The whole run is handed over as one zip, sealed so that anyone can tell whether a file in it has changed. The files are JSON, CSV, markdown and plain text, so none of this needs Rubicon to read, and a workflow can be checked against [`workflow.schema.json`](workflow.schema.json) with any JSON Schema validator.

The analyst is whoever carries out the run, a person or an AI model, and the evaluator is the person whose question it answers and who agrees its definitions and standard.

## A run's folder

Every path is relative to the run's folder; `<id>` is a step's id.

{_table(("Path", "Written by", "What it holds"), ((p if p.startswith("`") else f"`{p}`", w, m) for p, w, m in FOLDER))}

## The workflow

`workflow.json` is one JSON object:

{_keys(TOP)}

Each step has an `id`, a `kind` and `inputs` (the ids of earlier steps, or `"documents"` for all the documents), and the settings its kind has, on the step itself or under `"settings"`. A setting a step leaves out takes the default below, and so does one it gives as null, except {", ".join(f"`{s}`" for s in W.OFF_BY_NULL)}, for which null is a value of its own: off, none, or as the setting says. A key the format does not define is a fault, since nothing would act on it. A step reads only steps before it.

## The kinds of step

The kinds are {", ".join(f"`{k}`" for k in W.KINDS)}. A setting whose meaning begins "Where a runner calls models" is read only by a runner that codes, groups, reads or writes with models; a recount does not read any of them, and its default here is none because the engine on its own does not name a model.

{(chr(10) * 2).join(kinds)}

## Columns

A code step's `columns` are each an object:

{_keys(COLUMN)}

A value given as an object holds:

{_keys(VALUE)}

Values are compared ignoring case, surrounding space and the difference between a hyphen, an underscore and a space, and true or yes, false or no, are one value each, so "True", true and "YES" match; each is stored in the spelling its column lists. A binary column's values are `yes` and `no`. A row holding a value off its column's list keeps it, and the recount counts it among the values off the list.

### Causal links

A code step's `links` names its columns that are a link's ends:

{_keys(LINKS)}

In a causal map a factor's opposite pole is the factor's label with a leading `~`, such as `~Employment`. Where one speaker tells several links as one chain, each link is its own row, and the rows of that chain carry the same `sequence` (a short label, different for each chain in a document) and their place in it as `step` (1, 2, 3).

### Profile columns

A profile step's `columns` are each an object with `name` and one of `holds`, `values`, `distinct`, `first` and `last`:

{_keys(PROFILE_COLUMN)}

## Rubrics

A judge step's `verdicts` are each `{{"name", "means"}}`, best first. Each of its `criteria` has an `id`, a `question`, a `kind` and `levels`, tried in order, the last without a threshold, and optionally `scale`, its own level names best first where the standard rates it on a scale of its own:

- **rule**: `table` (a tabulate step among the inputs), `where` (the cells counted, as {{column: value}} over that table's columns), optionally `base` ({{document attribute: value or list}}, the documents counted over) and `base_where` (cells of the same table that narrow the base, so that a share can be of those the coding found doing something); each level is `{{"verdict"}}` with one of `at_least`, `at_most`, `share_at_least` and `share_at_most`, and may name its own `where`.
- **stated**: `document` (a background document's id), `quote` (its words holding both numbers, copied exactly), `n` and `base` (the two numbers as it states them), with levels as a rule's.
- **reading**: `rows_from` (a code step, or a group step that assigned items), optionally `where`, and levels each `{{"verdict", "descriptor"}}`.

Every level, and every rule in `combine`, also says whose it is: `"from": "evaluator"` with `quote`, the words of the standard it rests on, which the recount finds in the question; or `"from": "proposed"`, which waits until `accepted` is given. A level whose `verdict` is null is the standard's own test for when no rating can be given. The recount reports as a fault a rubric with blanks, or a threshold no count could reach.

## Steps taken from an earlier run

A code step may carry `from` in place of its own coding, taking its rows or its definitions from an earlier run's sealed zip:

{_keys(FROM)}

The zip is looked for in the run's `earlier/` and then in the run folders beside it, and is copied into `earlier/`, so the run's own zip recounts from itself alone. It is refused unless its seal holds, its fingerprint is the one named and, for `take: rows`, every document its rows come from reads the same in both runs; and refused where the earlier run takes, however far back, from this one. Everything else about the step comes from the earlier run's workflow, which the recount writes into its own.

## Coded rows

`coded/<id>.json` is a JSON list of the rows a code step was coded with, each `{{"document": its id, "quote": the passage word for word, and a value for each column}}`, with `sequence` and `step` on the links one speaker tells as one chain. A document that may hold several cases, such as a focus group, carries a free-text column named `case` saying which case each passage is about.

The recount gives each row an id: the step's id, a full stop and five characters drawn from its document and the span of its passage, such as `f.k3m9q`, so the id stays the same when other rows are added, removed or recoded; a second row on the same span adds `-2`.

## Recorded judgements

`judged/<id>.json` holds what the analyst decided for a step that needs a judgement, which the recount places and checks:

- **For a group step**, the codebook: `{{"items": [...], "unplaced": [...], "notes"}}`, each item `{{"id", "label", "means", "counts", "does_not_count": [{{"text", "goes_to"}}], "examples", "from_labels"}}`, naming in `from_labels` the open labels it gathers and in `from_rows` any row placed apart from the rest of its label; each label left over goes in `unplaced` as `{{"label", "reason"}}`. The recount reports a label placed nowhere, placed under two items, or named but carried by no row.
- **For a judge step**, a reading of each criterion of kind reading: `{{criterion id: {{"verdict": a level, or "between" with "between": [two levels], "rows": [the row ids it rests on], "against": [those that pull the other way], "why": a sentence}}}}`. A verdict that is not one of the criterion's levels leaves it unplaced, and a cited row the criterion does not read is listed.
- **For a claims step**, the claims: `{{claim id: {{"says", "rows", "against", "found_by", "why"}}}}`, saying what it claims, the rows it rests on and those against it, how another reader would find those passages again and why they bear it out.

## Cells and their ids

A tabulation names each cell by its coordinates: the step's id, then the values of its `by` columns in square brackets, joined by commas, such as `t[income up,MNX]`. The id is the same whatever the cell's count or place in the table, so a citation survives a revision that reorders the table, and a recount refuses an answer citing a cell the table no longer holds. A value is written as it is, except that any character an answer, markdown or HTML would read as syntax (a comma, a full stop, brackets and braces, a quotation mark and the like) is written as its UTF-8 bytes in `%XX`, so `a, b` is `a%2C b`; `recount/tables.md` gives every cell's id to copy. Where a table is by more than one column, `<cell id>.within.<column>` states the same count out of the cases with that cell's value in that column. Beside its cells, a tabulation's `<step id>.of` is how many it counted over. A judge step's rule is `<step id>.<criterion id>`, the count tested against the level it met, with `.<verdict>` added for each level tested on cells of its own, and a stated number is `<step id>.<criterion id>` too; `.of` after either gives its base alone.

A run made before cells were named by coordinates has `positional` ids, by place in the table (`t.c3`), which the workflow records in `cell_ids`; a zip whose workflow records nothing is read as positional.

## The answer

`answer.md` is markdown. Its first `# ` heading is the report's title, and in it:

- `{{<cell id>}}` stands for a count, which the recount writes in with what it is out of, such as "8 of 12", so that every number in the answer is a count; a numeral written bare is listed, and one stated beside a count that differs from it stops the report.
- `[<row id>]` cites a passage, and `[<claims step id>.<claim id>]` a key claim; a citation that does not name a row stops the report.
- A quotation in double quotation marks is found word for word in a document, each part either side of an ellipsis; one no document holds stops the report.
- `{{{{figure <tabulate step id>}}}}`, alone on a line, shows that table as a chart.
- `[§ <heading>]` after a sentence says that its claim builds on a finding stated under that heading, so that a revision can follow what each change undermines.

## The recount

`python recount.py <run folder> --answer answer.md` recounts the run by fixed rules alone, without calling a model, and writes `recount/`:

{_table(("Path", "What it holds"), ((f"`{p}`" if "," not in p else p, m) for p, m in RECOUNT))}

`report.json` holds `format`, this check of the workflow against the schema: the version and schema checked against, how many steps it read, and every place the workflow departs from it.

## The zip and its seal

The zip holds the recounted run, the files it was recounted from and the audit trail:

{_table(("In the zip", "From"), ((", ".join(f"`{x}`" for x in p.split(", ")), w) for p, w in ZIP))}

`SHA256SUMS` lists the SHA-256 of every other file in the zip, and the SHA-256 of that list is the run's fingerprint, which the report prints. So `sha256sum -c SHA256SUMS`, then `sha256sum SHA256SUMS`, checks a zip's seal with nothing but `sha256sum`. Its files carry a fixed date, so the same run always makes the same zip, byte for byte. `python verify.py <report> <zip>` says whether a report was created from a zip: the zip is as it was made, the report names it and, where the same engine created the report, a fresh recount of the zip's own coded rows and answer creates the same report again, byte for byte.
"""
