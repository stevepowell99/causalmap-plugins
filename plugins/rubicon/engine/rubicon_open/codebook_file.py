"""A run's codebook as files other software reads: every column the run coded, with its codes and what each means.

Two forms, both made from the workflow and its records and nothing else:

- `qdc`: a REFI-QDA codebook (the `.qdc` exchange file of the QDA software vendors' standard, XML in the namespace
  `urn:QDA-XML:codebook:1.0`). A column is a code; a column with a list of codes is a code that is not itself applied,
  holding one code for each value. A code's description is what it means, then what counts and what does not, as the
  report's own codebook tables give them.
- `csv_text`: the same as a table, one line a column and one a code, for a spreadsheet.

A column of free text or of numbers holds what a passage says rather than a code, so it is left out. A column whose
codes are a group step's items takes them from that step's record. Two columns with one name and the same codes are one
codebook, given once; two with one name and different codes are told apart by their step. Each code's identifier is
made from its step, column and name, so a report recreated from its zip holds the same file.
"""
from __future__ import annotations

import csv
import io
import uuid
from xml.sax.saxutils import escape, quoteattr

from .workflow import codebook_of, combining, value_key

NAMESPACE = "urn:QDA-XML:codebook:1.0"
#: The space the identifiers are drawn in: fixed, so the same code is the same identifier in every copy
_IDS = uuid.UUID("6f1c0e6a-2b1d-5d0a-9a57-7f1f5c0f2a11")
#: Column types that hold what a passage says, not a code
UNCODED = ("free_text", "numeric")


def near_misses(v) -> str:
    """What an item does not count, as written: a sentence, or the grouper's near misses, each with where it goes."""
    if isinstance(v, list):
        return "; ".join(str(n.get("text", "")) + (f" (goes to {n['goes_to']})" if n.get("goes_to") else "") if isinstance(n, dict)
                         else str(n) for n in v)
    return str(v or "")


def codes_of(col: dict, records: dict) -> list[dict]:
    """A coded column's codes, each {"name", "means", "counts", "does_not_count"}: its own list, or where its values are
    `codebook:<group step id>`, that group step's items; none for a column without a list."""
    g = codebook_of(col)
    if g:
        return [{"name": it.get("id"), "means": it.get("means", ""), "counts": it.get("counts", ""),
                 "does_not_count": it.get("does_not_count", "")}
                for it in (records.get(g, {}).get("codebook") or {}).get("items", [])]
    return [v if isinstance(v, dict) else {"name": str(v)} for v in col.get("values") or [] if isinstance(col.get("values"), list)]


def columns(steps: list[dict], records: dict, title=lambda sid: sid) -> list[dict]:
    """Every coded column of the workflow's code steps, in order: {"step", "name", "means", "codes"}, each code
    {"name", "means", "counts", "does_not_count"} with the last as one sentence. `title(step id)` names a step where two
    columns of one name hold different codes."""
    out, before, seen = [], {}, set()
    for st in steps:
        if st.get("kind") == "code" and not combining(st, before):
            for col in st.get("columns") or []:
                if not isinstance(col, dict) or not col.get("name") or col.get("type") in UNCODED:
                    continue
                codes = [{"name": str(c.get("name") or ""), "means": str(c.get("means") or ""), "counts": str(c.get("counts") or ""),
                          "does_not_count": near_misses(c.get("does_not_count"))} for c in codes_of(col, records)]
                same = (value_key(col["name"]), str(col.get("means") or ""), tuple(tuple(c.values()) for c in codes))
                if same in seen:
                    continue
                seen.add(same)
                out.append({"step": st.get("id"), "name": str(col["name"]), "means": str(col.get("means") or ""), "codes": codes})
        before[st.get("id")] = st
    names = [value_key(c["name"]) for c in out]
    for c in out:
        c["said"] = f"{c['name']} ({title(c['step'])})" if names.count(value_key(c["name"])) > 1 else c["name"]
    return out


def described(code: dict) -> str:
    """What a code means, then what counts and what does not, as one description."""
    return "\n".join(x for x in (code.get("means"), f"Counts: {code['counts']}" if code.get("counts") else "",
                                 f"Does not count: {code['does_not_count']}" if code.get("does_not_count") else "") if x)


def _guid(*parts) -> str:
    return str(uuid.uuid5(_IDS, "\0".join(str(p) for p in parts))).upper()


def _clean(text: str) -> str:
    """Text as XML 1.0 may hold it: without the control characters it has no way to write."""
    return "".join(ch for ch in str(text) if ch in "\t\n\r" or ord(ch) >= 0x20)


def qdc(cols: list[dict], origin: str) -> str:
    """The codebook as a REFI-QDA `.qdc` file (module docstring)."""
    def code(guid, name, text, codable, inner=""):
        said = f"<Description>{escape(_clean(text))}</Description>" if text else ""
        return (f'<Code guid={quoteattr(guid)} name={quoteattr(_clean(name))} isCodable="{"true" if codable else "false"}"'
                + (f">{said}{inner}</Code>" if said or inner else "/>"))
    body = "".join(code(_guid(c["step"], c["name"]), c["said"], c["means"], not c["codes"],
                        "".join(code(_guid(c["step"], c["name"], k["name"]), k["name"], described(k), True) for k in c["codes"]))
                   for c in cols)
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<CodeBook xmlns="{NAMESPACE}" origin={quoteattr(_clean(origin))}>'
            f"<Codes>{body}</Codes></CodeBook>\n")


CSV_HEAD = ("Column", "Code", "Means", "Counts", "Does not count")


def csv_text(cols: list[dict]) -> str:
    """The codebook as a table: a line for each column, with what it records, then one for each of its codes."""
    buf = io.StringIO()
    out = csv.writer(buf, lineterminator="\r\n")
    out.writerow(CSV_HEAD)
    for c in cols:
        out.writerow([c["said"], "", c["means"], "", ""])
        for k in c["codes"]:
            out.writerow([c["said"], k["name"], k["means"], k["counts"], k["does_not_count"]])
    return buf.getvalue()
