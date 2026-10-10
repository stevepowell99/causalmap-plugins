"""What a count counts, in a reader's words: the unit's name and a count stated with it, "2 of 18 households".

The one place a count is worded outside the answer's own sentences. `rubicon/open/report.js` words a count the same way
(`countSaid`), and `tests/rubicon-open-units-twin.test.mjs` holds the two together.
"""
from __future__ import annotations

#: What a tabulation can count, besides a column of the document list, whose values are then its cases.
COUNTS = ("cases", "documents", "rows")
#: The units' names the engine gives itself, which it knows the singular of.
OWN_NOUNS = ("cases", "documents", "passages")


def unit_noun(count: str, unit: str | None = None, cases_are_documents: bool = True) -> str:
    """The plural name of what a count counts: passages for rows, documents for documents, and for cases the
    tabulation's own `unit` where it gives one, else documents where every case is one document and cases where not.
    A count by a column of the document list names its unit (the workflow check refuses one that does not); without
    one it is called by the column."""
    if count == "rows":
        return "passages"
    if count == "documents":
        return "documents"
    if unit:
        return unit
    if count == "cases":
        return "documents" if cases_are_documents else "cases"
    return str(count)


def count_said(n, base, noun: str) -> str:
    """A count with its unit: "n of base noun", or "n passages" for a count with no base. The engine's own nouns are
    made singular where the number they follow is one; a unit a workflow names is left as given, since no rule makes
    every English plural singular."""
    return f"{n} {_one(n, noun)}" if base is None else f"{n} {base_said(base, noun)}"


def base_said(base, noun: str) -> str:
    """What a count is out of, "of 18 households", for a table that shows the number apart from its base."""
    return f"of {base} {_one(base, noun)}"


def _one(k, noun: str) -> str:
    return noun[:-1] if k == 1 and noun in OWN_NOUNS else noun
