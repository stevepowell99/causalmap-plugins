"""The quote gate: does this quote really appear in the source, and where?

Every claim Rubicon makes rests on a quote, so this is the one check that decides
whether the audit trail holds. The matching itself is not reimplemented here. It
runs `text-match.js` beside this file, which is Causal Map's own matcher (the one the
browser and the ai-writeback edge function use, `webapp/js/text-match.js`, kept
byte-identical by `tests/rubicon-open-text-match-twin.test.mjs`), through a small node
shim, because a second implementation of a five-tier matcher would drift from the first
within a month.

The policy copies DataService.Links.insertAI, deliberately:

  exact / canonical / gapped  ->  snap the quote to the verbatim source slice and
                                  keep the offsets. The model's wording is replaced
                                  by what the document actually says.
  fuzzy                       ->  keep the model's text and the approximate offsets,
                                  and record the tier so a reader can weigh it.
  no match                    ->  drop the row. A quote that cannot be placed is a
                                  likely hallucination, and one unplaceable quote is
                                  cheaper to lose than a judgement resting on it.

The dropped rows are returned, never merely counted, so a caller can say what it
threw away instead of reporting a clean pass over a silent loss.

That policy is for a passage whose quotation the trail replaces with its document's
words. A quotation a reader is shown as written, such as one in an answer, is held to
`locate_quoted` instead: each part either side of an ellipsis found in one run of the
document. A gapped placement skips words of the document the quotation leaves out
without marking them, which may be the "not" that reverses it.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import node, text as T

SHIM = Path(__file__).resolve().parent / "locate_quotes.mjs"

SNAP_TIERS = ("exact", "canonical", "gapped")
#: The tiers at which a quotation a reader is shown is found as written (`locate_quoted`): in one run of its document,
#: its letters and digits the document's, give or take case, spacing, punctuation and the shape of quotation marks and
#: dashes. Fuzzy is approximate.
AS_QUOTED = ("exact", "canonical")
#: An ellipsis, where a quotation marks words of its document it leaves out, bracketed or not: "...", "…", "……", "⋯",
#: "[…]", "(...)".
ELLIPSIS = re.compile(r"\s*[\[(]?\s*(?:\.{3,}|[…⋯]+)\s*[\])]?\s*")
_LOOSENESS = {"exact": 0, "canonical": 1, "fuzzy": 2}


@dataclass
class Located:
    quote: str
    tier: str
    start: int | None
    end: int | None


def _utf16_slice(text: str, start: int, end: int) -> str:
    return text.encode("utf-16-le")[2 * start:2 * end].decode("utf-16-le", errors="replace")


def locate_all(source_text: str, quotes: list[str], wide_gap: bool = False) -> list[Located | None]:
    """Locate every quote against the FULL source text. None means no match."""
    if not quotes:
        return []
    # A broken matcher must never look like "nothing matched", or a whole run of dropped quotes reads as a
    # conservative model; `node.call` raises rather than returning nothing.
    results = node.call(SHIM, {"sourceText": source_text, "quotes": quotes, "wideGap": bool(wide_gap)},
                        "quote locator")["results"]

    out: list[Located | None] = []
    for quote, hit in zip(quotes, results):
        if not hit:
            out.append(None)
            continue
        start, end = hit["start"], hit["end"]  # UTF-16 units, as the page counts; Python indexes code points
        tier = hit["tier"]
        text = _utf16_slice(source_text, start, end) if tier in SNAP_TIERS else quote
        out.append(Located(quote=text, tier=tier, start=start, end=end))
    return out


def quoted_parts(quote: str) -> list[str]:
    """The parts of a quotation either side of its ellipses, each four or more wide (`text.width`, a Chinese character
    counting two); the whole quotation where it has no ellipsis."""
    return [p for p in ELLIPSIS.split(quote) if T.width(p.strip()) >= 4] or [quote]


def _letters(text: str) -> str:
    """The letters, digits and combining marks of `text`, in any script, in Unicode's composed form and case-folded:
    what a quotation must share with its document to be found as written."""
    return "".join(ch for ch in unicodedata.normalize("NFC", text).casefold() if unicodedata.category(ch)[0] in "LNM")


def _skipped(quote: str, passage: str) -> list[str]:
    """The stretches of `passage` that `quote` leaves out or writes otherwise, found by aligning their characters, so
    in any script: each holding a letter or digit, so that a space or a hyphen the quotation writes otherwise is no
    stretch."""
    gaps = [" ".join(passage[j1:j2].split()) for op, _, _, j1, j2 in
            difflib.SequenceMatcher(None, quote.casefold(), passage.casefold(), autojunk=False).get_opcodes()
            if op in ("insert", "replace") and j2 > j1]
    return [g for g in gaps if any(ch.isalnum() for ch in g)]


def _as_written(part: str, hit: Located | None) -> Located | None:
    """A part of a quotation as the matcher placed it, if it is found as written: the passage it spans holds the same
    letters and digits (`_letters`). The matcher's canonical tier also strips accents ("ano" for "año"), and its gapped
    tier skips words of the passage (a "not"), and neither is the document's words as written; a gap of only spacing or
    punctuation, such as "set-up" for "set up", is."""
    if hit is None or hit.tier not in ("canonical", "gapped"):
        return hit
    return Located(hit.quote, "canonical", hit.start, hit.end) if _letters(part) == _letters(hit.quote) else None


def locate_quoted(source_text: str, quotes: list[str]) -> list[Located | None]:
    """Each quotation a reader is shown as written, placed in `source_text`: every part either side of an ellipsis
    found in one run of the text, its letters and digits the text's (`_as_written`), at the loosest of its parts'
    tiers, from the first part's start to the last part's end. A part that leaves out or changes letters or digits of
    the text places nothing, since the quotation would read as the speaker's words when they are not, and `left_out`
    says how it differs. One call of the matcher for all. `quote` is the text's own words for a quotation of one part
    found as written, else the quotation as given."""
    parts = [quoted_parts(q) for q in quotes]
    flat = [p for ps in parts for p in ps]
    hits = [_as_written(p, h) for p, h in zip(flat, locate_all(source_text, flat))]
    out: list[Located | None] = []
    k = 0
    for q, ps in zip(quotes, parts):
        mine, k = hits[k:k + len(ps)], k + len(ps)
        if any(h is None or h.tier not in _LOOSENESS for h in mine):
            out.append(None)
            continue
        tier = max((h.tier for h in mine), key=_LOOSENESS.get)
        out.append(Located(quote=mine[0].quote if len(ps) == 1 and tier in AS_QUOTED else q, tier=tier,
                           start=min(h.start for h in mine), end=max(h.end for h in mine)))
    return out


def left_out(source_text: str, quotes: list[str]) -> list[Located | None]:
    """For each quotation `locate_quoted` cannot place, the passage of `source_text` the matcher reads it as, where it
    skips or changes the passage's words (its gapped or canonical tier), with those words (`_skipped`): a Located whose
    `quote` is the passage, and whose `skipped` lists each stretch the quotation leaves out or writes otherwise. None
    for a quotation found as written, or not found even so."""
    out: list[Located | None] = []
    for q, hit, found in zip(quotes, locate_all(source_text, quotes), locate_quoted(source_text, quotes)):
        if found is not None or hit is None or hit.tier not in ("gapped", "canonical"):
            out.append(None)
            continue
        out.append(Skipped(quote=hit.quote, tier=hit.tier, start=hit.start, end=hit.end, skipped=_skipped(q, hit.quote)))
    return out


@dataclass
class Skipped(Located):
    skipped: list[str]

