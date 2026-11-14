"""Causal Map's sources as Rubicon reads them: a project's source rows, from wherever they were read, shaped into
the documents a run takes. No reading happens here, so the private package's database reader (`cm_read.get_sources`,
`sandbox.documents_from_project`) and the hosted server's reader, which reads with the signed-in person's own token
(`rubicon/mcp/hosted_cm.py`), share one shaping and cannot drift apart.

Source custom columns live at `sources.metadata.custom_columns` and are the closest thing cm4 has to respondent
attributes. They are surfaced with the same `s_` prefix the app uses, and with their typographic punctuation written as
keyboard characters (`typeable`).
"""
from __future__ import annotations

#: The columns of `public.sources` a run reads, in the order both readers select them
SOURCE_COLUMNS = ("id", "project_name", "filename", "title", "type", "size", "content", "source_prompt", "metadata")
#: How a document from Rubicon's own table (`rubicon.project_documents`) is named wherever a source id is expected;
#: the page's `webapp/rubicon/js/model.js` uses the same prefix.
HUB_PREFIX = "doc:"


#: Columns a person might have typed the flag into. Case is ignored, so one spelling each.
BACKGROUND_COLUMNS = ("background", "reference", "background document", "is background",
                      "is_background", "background_document", "document role", "doc role")
TRUE_ISH = ("yes", "y", "true", "t", "1", "background", "reference",
            "background document", "context", "standard")


def is_background(source: dict) -> bool:
    """Does this Causal Map source's own column say it is the standard rather than the evidence?

    The column route, and one of two homes a background document has. Steve, 2 September
    2026: a theory of change, a funder's standards document or a terms of reference should
    not be a separate class of thing attached to a run, but held at project level, so
    one library serves every question asked of that project. One way of doing that is a
    source with a flag typed into a custom column, which is read here. The other is
    Rubicon's own table, written from the project hub, and `documents.is_background` is the
    question every consumer asks, across both.

    The flag is read from the source's own custom columns, because the source belongs to
    Causal Map and this is a property of the source rather than of any run. Several
    spellings are accepted, since the column is typed by a person.

    **The value decides, and every candidate column is read.** Until 9 September 2026 this
    returned on the first column that merely EXISTED, and `Reference` was third in the
    list. So a corpus whose importer writes a reference on every source, which is the shape
    the worked importers all have, answered the question with a value like `oral-2020-09-23`
    and came back false for every document it held. `uk-research-funding-agency` has a terms
    of reference and 113 submissions and reported no background documents at all, silently,
    for a week: the flag was not missing, it was being read off the wrong column and the
    answer looked exactly like a project where nobody had set one.

    So an unrecognised value is not an answer. A column is consulted and, where what it
    holds means nothing here, the next one is tried, and a source with no true-ish value
    anywhere is evidence. That is the same shape as the rest of the codebase: a check that
    can pass by finding nothing has to have looked.
    """
    for key, value in source.items():
        if not isinstance(key, str) or not key.startswith("s_"):
            continue
        if key[2:].strip().lower().replace("-", " ") not in BACKGROUND_COLUMNS:
            continue
        if value is True:
            return True
        if value is False or value is None:
            continue
        if str(value).strip().lower() in TRUE_ISH:
            return True
    return False


#: Punctuation a spreadsheet types for you and a model will not type back.
_TYPOGRAPHIC = str.maketrans({
    **dict.fromkeys(map(chr, (0x2018, 0x2019, 0x201A, 0x201B)), "'"),  # curly single quotes
    **dict.fromkeys(map(chr, (0x201C, 0x201D, 0x201E)), '"'),  # curly double quotes
    chr(0x2026): "...",  # ellipsis
    **dict.fromkeys(map(chr, (0x2013, 0x2014)), "-"),  # en and em dash
    chr(0x00A0): " ",  # non-breaking space
})


def typeable(text):
    """A column name or value as somebody would type it on a keyboard.

    A model names a column by typing it back, and writes `household's` for `household’s`
    whatever it was shown, so `get_sources` makes the custom columns' names and values
    typeable on the way in. Only the custom columns: the source text is quoted, and a
    quote must be the words as they stand.
    """
    return text.translate(_TYPOGRAPHIC) if isinstance(text, str) else text


def shaped(rows: list[dict], project_name: str) -> list[dict]:
    """A project's source rows, each with its custom columns flattened to `s_` keys.

    Two columns whose names differ only in their punctuation are refused, because made
    typeable they are one name, and a reader naming either would read whichever came
    last. It is a sentence for a person to act on rather than a case to engineer.
    """
    spellings: dict[str, set] = {}
    for r in rows:
        for key in ((r.get("metadata") or {}).get("custom_columns") or {}):
            spellings.setdefault(typeable(key), set()).add(key)
    clash = sorted(sorted(names) for names in spellings.values() if len(names) > 1)
    if clash:
        raise ValueError(
            f"project {project_name!r} has columns that differ only in their punctuation: "
            f"{clash}. Ruby could not tell them apart, so rename one of each pair in "
            "Causal Map."
        )
    for r in rows:
        meta = r.get("metadata") or {}
        for key, value in (meta.get("custom_columns") or {}).items():
            r[f"s_{typeable(key)}"] = typeable(value)
        for key, value in meta.items():
            if key != "custom_columns" and not isinstance(value, (dict, list)):
                r[f"source_{key}"] = value
    return rows


def hub_documents_of(rows: list[tuple]) -> list[dict]:
    """The background documents added on the project hub, from rows of (id, title, content), oldest first. Each is
    filed under its title, which is unique on the project and the name the hub shows."""
    return [{"id": f"{HUB_PREFIX}{r[0]}", "title": r[1], "name": r[1], "text": r[2] or "",
             "characters": len(r[2] or "")} for r in rows]


def documents_of(sources: list[dict], hub: list[dict]) -> tuple[list[dict], list[str], list[dict]]:
    """The evidence, its columns, and the background documents from both of their homes: Causal Map sources flagged
    by a column, and Rubicon's own table that the project hub writes."""
    columns = sorted({k[2:] for s in sources for k in s if k.startswith("s_")})
    docs, background = [], []
    for s in sources:
        text = s.get("content") or ""
        d = {"id": str(s["id"]), "title": s.get("title") or s.get("filename") or str(s["id"]),
             "case": str(s["id"]), "text": text, "characters": len(text),
             "columns": {c: s.get(f"s_{c}", "") or "" for c in columns}}
        (background if is_background(s) else docs).append(d)
    return docs, columns, background + hub
