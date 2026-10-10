"""The documents a run reads: `corpus/index.csv` and one text file per document, with the project's background
documents beside them."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

CORPUS = "corpus"
BACKGROUND = "background"


def as_read(text: str) -> str:
    """A document as every offset in the open format counts it: each Windows (CRLF) or old Mac (CR) line ending made
    one newline, the same as reading the file in text mode. The rule is written here once; the Rubicon page's bundle
    reader and writer mirror it in `webapp/rubicon/js/model.js` (`asRead`), and `tests/rubicon-open-as-read-twin.test.mjs`
    holds the two together."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


class RecordError(ValueError):
    """A count or a record file that cannot be read as written."""


@dataclass
class Corpus:
    """The documents a run may read: `corpus/index.csv` and one text file per document, and beside them the project's
    background documents (`background/index.csv`), which are quoted and never coded or counted, so they are kept out of
    `documents`."""
    folder: Path
    documents: dict[str, dict] = field(default_factory=dict)
    columns: list[str] = field(default_factory=list)
    background: dict[str, dict] = field(default_factory=dict)
    _texts: dict[str, str] = field(default_factory=dict)

    def text(self, doc: str) -> str:
        if doc not in self._texts:
            if doc in self.documents:
                path = self.folder / self.documents[doc]["file"]
            else:
                path = self.folder.parent / BACKGROUND / self.background[doc]["file"]
            with path.open(encoding="utf-8", newline="") as fh:
                self._texts[doc] = as_read(fh.read())
        return self._texts[doc]

    def background_texts(self) -> dict[str, str]:
        return {d: self.text(d) for d in self.background}

    def case_of(self, doc: str, row_case=None) -> str:
        """The case a passage belongs to: the one its row names, within its document's case, so that "Participant 1"
        of two focus groups are two cases and one person across two documents of one case is one; else its document's
        case, the index's `case` column where it gives one, else the document itself."""
        own = self.documents[doc].get("case") or doc
        named = "" if row_case is None else str(row_case).strip()
        return f"{own} / {named}" if named else own

    def cases_held(self, docs, rows=()) -> dict[str, set[str]]:
        """Every case among the documents `docs`, with the documents each appears in, for a count made from `rows`
        (one code step's; a `case` on a row attributes it). A document holds the cases its rows name, and its own case
        as well where one of its rows names none or none of them names one. The cases of different code steps are
        never pooled: each may attribute passages to a different kind of case."""
        named: dict[str, set[str]] = {}
        unnamed: set[str] = set()
        for r in rows:
            c = self.case_of(r["document"], r.get("case"))
            if c == self.case_of(r["document"]):
                unnamed.add(r["document"])
            else:
                named.setdefault(r["document"], set()).add(c)
        out: dict[str, set[str]] = {}
        for d in docs:
            for c in named.get(d, set()) | ({self.case_of(d)} if d in unnamed or d not in named else set()):
                out.setdefault(c, set()).add(d)
        return out

    @property
    def cases(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for d in self.documents:
            out.setdefault(self.case_of(d), []).append(d)
        return out

    def case_column(self, case: str, column: str, docs=None) -> str | None:
        """A case's value of a document column, where all its documents (`docs`, else the index's grouping) agree."""
        values = {self.documents[d]["columns"].get(column) for d in (docs if docs is not None else self.cases.get(case, []))}
        return values.pop() if len(values) == 1 else None


#: The index columns that are the document's identity rather than a property of it.
INDEX_FIELDS = ("id", "title", "file", "case", "characters", "synthetic")


def load_corpus(run: Path) -> Corpus:
    folder = run / CORPUS
    index = folder / "index.csv"
    if not index.exists():
        raise RecordError(f"the corpus has no index: {index} is missing")
    c = Corpus(folder=folder)
    with index.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        c.columns = [k for k in (reader.fieldnames or []) if k not in INDEX_FIELDS]
        for row in reader:
            doc = row["id"]
            c.documents[doc] = {"title": row.get("title") or doc,
                                "file": row.get("file") or f"{doc}.txt",
                                "case": row.get("case") or doc,
                                "columns": {k: row.get(k) for k in c.columns}}
    bg = run / BACKGROUND / "index.csv"
    if bg.exists():
        with bg.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                c.background[row["id"]] = {"title": row.get("title") or row["id"], "file": row["file"]}
    return c
