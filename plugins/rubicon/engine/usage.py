"""The one address Rubicon's main plugin fetches once a conversation: the run's size and outline, never its content.

    python usage.py <run folder or documents folder> --event report|revision|combined --model <family> --to <address>

Prints `--to` with a query string of the keys `rubicon_open/outline.py` lists and nothing else, each value from its
fixed set, worked out by fixed rules from the folder's own files:

- the run's code: sixteen random hexadecimal characters, made the first time the run tells Causal Map anything and kept
  in `usage-code.txt` at the top of the run's folder (`CODE_FILE`), so every later hand-over of the run gives the same
  one. Nothing about the run goes into it, and it is kept outside everything the run's zip, report and Word copy are
  made from, so a row cannot be matched to a report anyone is shown;
- documents and words: the documents the run read and the words they hold (`text.words_in`, in any script), in bands;
- questions: the lines of the settled question;
- how they were taken: from `rubicon-plan.md` beside the documents where it has rows (a `shared` row, a shared reading
  first; more than one question row, a run for each), and otherwise from the run's own questions;
- steps of each kind: as `workflow.json` lists them;
- passages: the rows of the coding steps that code documents themselves (not those that put other steps' rows
  together), as the recount read them, in bands;
- the second reading: a second coding where `recode/readers.json` names one or `recode/coded/` holds rows; a check where
  the run records one; otherwise none;
- minutes: from the earliest agreement in `work/agreements.json` to now, in bands;
- tied: of the answer's sentences the recount read for a tie to the passages (`recount/report.json`), the share it found
  tied, in bands.

A documents folder (one holding `corpus/`, for a combined report) gives its whole corpus and every run folder in it
together: their questions and steps added up, the earliest start, the second reading where all agree (else `mixed`), and
a code made from their codes together. No question text, document or folder name, passage, code value or label, and
nothing about the person or the computer, goes into the address. The script writes nothing but a run's code, opens no
connection and names no address of its own: Claude fetches what it prints with its own web fetch tool, and an address
printed by a tool can be fetched where one Claude wrote itself may be refused.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import random
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open import console, plan  # noqa: E402
from rubicon_open.corpus import find_documents, load_corpus  # noqa: E402
from rubicon_open.outline import CAP, EVENTS, FAMILY, KINDS, OUTLINE, UNKNOWN, band, check  # noqa: E402
from rubicon_open.text import words_in  # noqa: E402


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


#: Where a run keeps its code: at the top of its folder, where nothing the zip, the report or the Word copy is made from
#: lies (`render_report.bundle` takes named files and `work/`)
CODE_FILE = "usage-code.txt"


def code_of(run: Path) -> str:
    """The run's code, made at random the first time it is asked for and kept in `CODE_FILE`."""
    held = run / CODE_FILE
    try:
        code = held.read_text(encoding="utf-8").strip()
    except OSError:
        code = ""
    if re.fullmatch(r"[0-9a-f]{16}", code):
        return code
    code = f"{random.SystemRandom().getrandbits(64):016x}"  # the operating system's randomness, as run_id.py draws IDs
    held.write_text(code + "\n", encoding="utf-8")
    return code


def code_for(runs: list[Path]) -> str:
    """One run's code; for several, a code made from theirs, so a combined report's row matches no single run's."""
    codes = sorted(code_of(r) for r in runs)
    if len(codes) == 1:
        return codes[0]
    return hashlib.sha256(("rubicon-runs " + ",".join(codes)).encode("utf-8")).hexdigest()[:16] if codes else "none"


def questions(wf: dict) -> int:
    asked = wf.get("question_as_agreed") or ""
    return max(1, sum(1 for line in asked.splitlines() if line.strip()))


def taken(documents: Path, n_questions: int, n_runs: int = 1) -> str:
    rows = plan.read(documents, every=True)
    if any(r["role"] == "shared" for r in rows):
        return "shared-first"
    if sum(r["role"] == "question" for r in rows) > 1 or n_runs > 1:
        return "one-at-a-time"
    return "together" if n_questions > 1 else "single"


def passages(run: Path, wf: dict) -> int | None:
    """The rows of the code steps that code documents, as the recount read them; None where it has not run."""
    if not (run / "recount" / "steps").is_dir():
        return None
    n = 0
    for s in wf.get("steps") or []:
        if s.get("kind") == "code" and not s.get("combining") and not (s.get("settings") or {}).get("combining"):
            rec = _json(run / "recount" / "steps" / f"{s.get('id')}.json") or {}
            n += len(rec.get("rows") or [])
    return n


def second_reading(run: Path) -> str:
    readers = _json(run / "recode" / "readers.json") or {}
    coded = run / "recode" / "coded"
    if "second_coding" in readers or (coded.is_dir() and any(coded.iterdir())):
        return "recode"
    return "check" if "check" in readers or (run / "check.md").is_file() else "none"


def started(run: Path) -> datetime.datetime | None:
    stamps = []
    for a in _json(run / "work" / "agreements.json") or []:
        try:
            at = datetime.datetime.fromisoformat(str(a.get("at")))
        except (TypeError, ValueError, AttributeError):
            continue
        if at.tzinfo is not None:
            stamps.append(at)
    return min(stamps) if stamps else None


def tied(run: Path) -> tuple[int, int] | None:
    """(sentences read for a tie, those found untied), from the recount; None where it has not run."""
    a = (_json(run / "recount" / "report.json") or {}).get("answer")
    if not isinstance(a, dict) or "sentences_read_for_a_tag" not in a:
        return None
    return int(a["sentences_read_for_a_tag"]), len(a.get("sentences_untagged_at") or [])


def outline(folder: Path, event: str, model: str, version: str, now: datetime.datetime | None = None) -> dict[str, str]:
    """The run's size and outline, every value from its fixed set."""
    if event not in EVENTS or not FAMILY.fullmatch(model):
        raise SystemExit(f"--event takes one of {EVENTS} and --model one lowercase word")
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if (folder / "workflow.json").is_file():
        runs, documents = [folder], folder.parent
        corpus = load_corpus(folder)
        n_docs, n_words = len(corpus.documents), sum(words_in(corpus.text(d)) for d in corpus.documents)
    elif (folder / "corpus").is_dir():
        runs, documents = sorted(w.parent for w in folder.glob("*/workflow.json")), folder
        _, rows, found = find_documents(folder)
        n_docs = len(rows)
        n_words = sum(words_in(p.read_text(encoding="utf-8", errors="replace")) for p in found.values() if p)
    else:
        raise SystemExit(f"{folder} is neither a run's folder (workflow.json) nor a documents folder (corpus/)")
    wfs = {r: _json(r / "workflow.json") or {} for r in runs}
    n_q = sum(questions(w) for w in wfs.values()) or 1
    kinds = collections.Counter(s.get("kind") for w in wfs.values() for s in w.get("steps") or [])
    coded = [passages(r, w) for r, w in wfs.items()]
    seconds = {second_reading(r) for r in runs}
    starts = [t for t in (started(r) for r in runs) if t]
    ties = [t for t in (tied(r) for r in runs) if t]
    read, untied = sum(t[0] for t in ties), sum(t[1] for t in ties)
    got = {"v": version, "e": event, "m": model, "run": code_for(runs),
           "docs": band("docs", n_docs), "words": band("words", n_words), "q": str(min(CAP, n_q)),
           "taken": taken(documents, n_q, len(runs)),
           **{k: str(min(CAP, kinds[k])) for k in KINDS},
           "passages": band("passages", sum(coded)) if coded and None not in coded else UNKNOWN["passages"],
           "second": seconds.pop() if len(seconds) == 1 else "mixed",
           "minutes": band("minutes", max(0, int((now - min(starts)).total_seconds() // 60))) if starts else UNKNOWN["minutes"],
           "tied": band("tied", (read - untied) * 100 // read) if read else UNKNOWN["tied"]}
    if check(got.items()) is None:  # never print what the relay would refuse
        raise SystemExit(f"a value outside its set: {got}")
    return got


def address(to: str, values: dict[str, str]) -> str:
    return to + "?" + urllib.parse.urlencode([(k, values[k]) for k in OUTLINE])


def main(argv=None) -> None:
    console.utf8()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="the run's folder, or the documents folder for a combined report")
    ap.add_argument("--event", required=True, choices=EVENTS)
    ap.add_argument("--model", required=True, help="the model family, one lowercase word as the skill names it")
    ap.add_argument("--to", required=True, help="the address to fetch, which the skill gives")
    a = ap.parse_args(argv)
    if not a.to.startswith("https://") or "?" in a.to:
        raise SystemExit("--to takes an https address without a query string")
    held = Path(__file__).resolve().parent / "VERSION"
    if not held.is_file():
        raise SystemExit(f"{held} is missing: this engine was not built into a plugin")
    print(address(a.to, outline(a.folder.resolve(), a.event, a.model, held.read_text(encoding="utf-8").strip())))


if __name__ == "__main__":
    main()
