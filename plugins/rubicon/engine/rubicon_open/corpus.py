"""The documents a run reads: `corpus/index.csv` and one text file per document, with the project's background
documents beside them."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

CORPUS = "corpus"
BACKGROUND = "background"


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
            self._texts[doc] = path.read_text(encoding="utf-8")
        return self._texts[doc]

    def background_texts(self) -> dict[str, str]:
        return {d: self.text(d) for d in self.background}

    def case_of(self, doc: str) -> str:
        return self.documents[doc].get("case") or doc

    @property
    def cases(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for d in self.documents:
            out.setdefault(self.case_of(d), []).append(d)
        return out

    def case_column(self, case: str, column: str) -> str | None:
        """A case's value of a document column, where all its documents agree on it."""
        values = {self.documents[d]["columns"].get(column) for d in self.cases.get(case, [])}
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
