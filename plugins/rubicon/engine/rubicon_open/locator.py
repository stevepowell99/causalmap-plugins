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
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import node

SHIM = Path(__file__).resolve().parent / "locate_quotes.mjs"

SNAP_TIERS = ("exact", "canonical", "gapped")


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

