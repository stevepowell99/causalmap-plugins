"""A ballpark, made by fixed rules before a run starts, of the tokens it will use and the time it will take.

    python estimate.py <documents folder> [--questions N] [--causal-map] [--second-reading check|recode|none]
                       [--hard-recode] [--documents N] [--window LABEL=TOKENS ...]

The documents are those `corpus/index.csv` in the documents folder lists, found as `start.py` finds them. Their size
in tokens is their UTF-8 bytes divided by `BYTES_PER_TOKEN`, so a script that takes more bytes to the character counts
for more. The estimate adds:

- what a run spends whatever its documents: settling, the method notes, the writing and the report (`BASE`), larger
  where the documents are coded as causal claims;
- the second reading chosen at settling (`SECOND`): a check by a fresh reader, the default, or a blind recode with the
  check, or none;
- for each token of the documents, what reading them costs (`PER_TOKEN`): once to code, again for the check, again for
  a blind recode or a hard recode. A reader re-reads its context on every turn, so re-read tokens come to many times
  the documents' size;
- for each question beyond the first, a share more of everything a question adds to (`PER_QUESTION`): the base, the
  second reading, and what is written and re-read per token, though not the documents' first reading.

It prints three kinds of token, since a cached re-read is not the same as a fresh one: read fresh (new to a reader,
written to its cache), re-read from that cache, and written by the model. The time follows from what is written
(`MINUTES`). `--documents N` estimates a run on N of the documents, at their average size, as for a sample first.
Each `--window LABEL=TOKENS` divides the tokens read fresh or written by TOKENS, printing how many such windows the run
would take, under that label.

Calibrated on stored runs of this engine over bench corpora from 300 to 907,000 characters, each measured from every
call in its transcripts; method and errors in `rubicon/reconstructions/plan-limits-estimate/result.md` (not part of
the plugin). It is a ballpark: the same task over the same documents has varied by half again from one run to the next.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import console  # noqa: E402
from rubicon_open.corpus import find_documents  # noqa: E402

#: UTF-8 bytes per token: interview transcripts in English measured about 3 characters a token, one byte each
BYTES_PER_TOKEN = 3.0

KINDS = ("fresh", "reread", "written")

#: Tokens a run spends whatever its documents, by what the documents are coded as
BASE = {"themes": (70_000, 1_100_000, 20_000), "causal": (110_000, 2_300_000, 40_000)}

#: Tokens a second reading adds beyond its share per token of the documents; a recode's coder adds a coding pass too
SECOND = {"check": {"themes": (90_000, 1_200_000, 30_000), "causal": (170_000, 3_500_000, 60_000)},
          "none": {"themes": (0, 0, 0), "causal": (0, 0, 0)}}
SECOND["recode"] = {k: tuple(2 * x for x in v) for k, v in SECOND["check"].items()}

#: Tokens per token of the documents, for each pass that reads them, by what the documents are coded as: coding every
#: causal claim writes more rows and takes more turns per document
PER_TOKEN = {"code": {"themes": (3.0, 60.0, 0.9), "causal": (4.5, 90.0, 1.35)},
             "check": {"themes": (1.0, 20.0, 0.2), "causal": (1.0, 20.0, 0.2)}}

#: The share more that each question beyond the first adds to the base, the second reading, and per-token re-reads and
#: writing
PER_QUESTION = 0.25

#: Minutes: a fixed part, and a part per thousand tokens written
MINUTES = {"themes": (3.0, 0.12), "causal": (5.0, 0.18)}


def estimate(docs: Path, questions: int = 1, causal: bool = False, second: str = "check", hard_recode: bool = False,
             documents: int | None = None) -> dict:
    fields, rows, found = find_documents(docs)
    files = [p for p in found.values() if p is not None]
    if not files:
        raise SystemExit(f"{docs / 'corpus' / 'index.csv'} names no document found in {docs / 'corpus'} or {docs}")
    size = sum(p.stat().st_size for p in files)
    chars = sum(len(p.read_text(encoding="utf-8", errors="replace")) for p in files)
    read = len(files) if documents is None else max(1, min(documents, len(files)))
    tokens = size / BYTES_PER_TOKEN * read / len(files)
    kind = "causal" if causal else "themes"
    q = 1 + PER_QUESTION * (max(1, questions) - 1)
    passes = ["code"] + (["code"] if second == "recode" else []) + (["code"] if hard_recode else []) \
        + (["check"] if second != "none" else [])
    out = {}
    for i, k in enumerate(KINDS):
        fixed = (BASE[kind][i] + SECOND[second][kind][i]) * q
        per = sum(PER_TOKEN[p][kind][i] for p in passes) * tokens
        out[k] = fixed + (per if k == "fresh" else per * q)
    lo_fixed, per_k = MINUTES[kind]
    minutes = lo_fixed + per_k * out["written"] / 1000
    return {"documents": len(files), "documents_read": read, "missing": [r.get("id") for r in rows if found.get(r.get("id")) is None],
            "characters": round(chars * read / len(files)), "document_tokens": round(tokens),
            "questions": max(1, questions), "causal_map": causal, "second_reading": second, "hard_recode": hard_recode,
            "tokens": {k: round(v) for k, v in out.items()},
            "fresh_or_written": round(out["fresh"] + out["written"]), "minutes": round(minutes, 1)}


def ballpark(n: float) -> str:
    """Two significant figures, in words above a million, so an estimate never reads as more exact than it is."""
    if n >= 1_000_000:
        return f"{float(f'{n / 1_000_000:.2g}'):g} million"
    return f"{int(float(f'{n:.2g}')):,}"


def describe(e: dict, windows: list[tuple[str, float]] = ()) -> str:
    second = {"check": "a check by a fresh reader", "recode": "a blind recode with the check", "none": "none"}
    t = e["tokens"]
    lines = [f"Documents: {e['documents_read']} of {e['documents']}, about {ballpark(e['characters'])} characters "
             f"and {ballpark(e['document_tokens'])} tokens to read once."
             if e["documents_read"] < e["documents"] else
             f"Documents: {e['documents']}, about {ballpark(e['characters'])} characters and "
             f"{ballpark(e['document_tokens'])} tokens to read once.",
             f"Task: {e['questions']} question{'s' if e['questions'] > 1 else ''}; coded as "
             f"{'causal claims' if e['causal_map'] else 'passages on each part of the question'}; second reading: "
             f"{second[e['second_reading']]}{'; a hard recode' if e['hard_recode'] else ''}.",
             f"Tokens read fresh or written: about {ballpark(e['fresh_or_written'])} "
             f"({ballpark(t['fresh'])} read fresh, {ballpark(t['written'])} written).",
             f"Tokens re-read from the cache, as each reader re-reads its context every turn: about {ballpark(t['reread'])}.",
             f"Time: about {max(5, 5 * round(e['minutes'] * 0.7 / 5))} to {5 * round(e['minutes'] * 1.5 / 5 + 0.5)} minutes."]
    for label, size in windows:
        n = e["fresh_or_written"] / size
        lines.append(f"{label}: about {n:.1g} of one window" if n < 0.95 else f"{label}: about {n:.2g} windows")
    if e["missing"]:
        lines.append(f"Not found, so not counted: {', '.join(e['missing'])}.")
    lines.append("A ballpark from fixed rules: the same task over the same documents has varied by half again between runs.")
    return "\n".join(lines)


def window(s: str) -> tuple[str, float]:
    label, _, size = s.rpartition("=")
    try:
        n = float(size.replace(",", "").replace("_", ""))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--window takes LABEL=TOKENS, such as A=1000000, not {s!r}")
    if not label or n <= 0:
        raise argparse.ArgumentTypeError(f"--window takes LABEL=TOKENS with a positive number, not {s!r}")
    return label, n


def main(argv=None) -> None:
    console.utf8()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docs", type=Path, help="the documents folder, holding corpus/index.csv")
    ap.add_argument("--questions", type=int, default=1, help="how many questions the task holds")
    ap.add_argument("--causal-map", action="store_true", help="the documents are coded as causal claims")
    ap.add_argument("--second-reading", choices=("check", "recode", "none"), default="check")
    ap.add_argument("--hard-recode", action="store_true", help="the documents are read again, closed, against a codebook")
    ap.add_argument("--documents", type=int, help="estimate a run on this many of the documents, as for a sample")
    ap.add_argument("--window", type=window, action="append", default=[], metavar="LABEL=TOKENS")
    ap.add_argument("--json", action="store_true", help="print the estimate as JSON")
    a = ap.parse_args(argv)
    e = estimate(a.docs, a.questions, a.causal_map, a.second_reading, a.hard_recode, a.documents)
    if a.json:
        e["windows"] = {label: round(e["fresh_or_written"] / size, 2) for label, size in a.window}
        print(json.dumps(e, indent=1))
    else:
        print(describe(e, a.window))


if __name__ == "__main__":
    main()
