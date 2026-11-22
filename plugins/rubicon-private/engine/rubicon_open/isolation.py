"""The second coder's own folder, and what fixed rules record of what each helper of the second reading was given and
opened, so that a report states who did the second reading from records the engine writes, never from the analyst's word.

`isolate.py <run> open` makes `recode/`, the second coder's folder, holding only the documents (`corpus/`), the
workflow's definitions (`workflow.json`), the format (`contract/pieces.md`, where the run holds it) and the brief
(`brief.md`, or one per batch in `briefs/`), with `{{folder}}` standing for the folder's own path, which the prompt it
prints fills in. It writes `recode/given.json`: the parts of the second reading the run will hold (`PARTS`), each file
given with its SHA-256 and its kind (`KINDS`), the SHA-256 of the brief as the plugin ships it, and whether the helpers'
log was opened. The log opens where the plugin's data folder is named: the run is added to `OPEN` there, and while it is
listed the plugin's hook (`helper_log.mjs`, on SubagentStart and SubagentStop only, so no ordinary tool call waits on
it) writes a note of each helper that starts or stops, naming the transcript Claude Code keeps of that helper: the prompt
it was started with and every tool call it made.

Each second coder, one for the whole corpus or one for each batch of it, writes its rows into a part of its own,
`batches/<name>/<step id>.json`, one file for every step it codes (an empty list where its documents hold nothing for
it), so that no coder's rows replace another's. `isolate.py <run> join` joins the parts into `coded/` by fixed rules and
records each in `joined.json`. It refuses, writing nothing, where a part is missing a step's file, a row names a
document outside its batch, or a step with one row per document leaves one of its batch's documents out
(`join_faults`), so a lost batch stops the second reading rather than reading as documents the second coder found
nothing in. `compare.py` makes the same check, and refuses rows in `coded/` that are not what the join wrote
(`joined_faults`).

`isolate.py <run> close` reads those notes and transcripts and writes `recode/helpers.json`: whether the log is whole
(`LOG`), and for each helper its type, how its prompt compares with each brief (`PROMPT`), and each tool call with the
file it names relative to the run, placed in the second coder's folder, outside it, or naming no folder (`WHERE`), which
counts as outside: a search given no path searches wherever the session is. It writes `recode/readers.json` from them,
for each part given: "separate" where a helper's call wrote that part's record (rows in `recode/batches/`, or `check.md`),
"same" where the analyst says it did that part itself, and "unrecorded" otherwise; absence of a helper is never read as
the analyst's own work. Neither file holds an absolute path, so a zip can be shared.

What a report says from these records is `told`: the folder the second coder was given, from `given.json`, and, only
where the log is whole and shows helpers writing the rows, what their tools did, each as a count: how many of the files
given they read, out of all given, so that a reader sees whether every one was read; any other file they read in the
folder; the files they wrote there; and what they opened outside it, so that "nothing outside it" stands beside what
they did open. The engine's own records in the folder (`RECORDS`) count as none of these. Where the log is absent or partial it says only what the folder held
and that the run does not record what was opened. Nothing here reads words: prompts are compared whole, and tools and
paths are the fields Claude Code gives them.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from . import claims
from . import workflow as W

#: The parts a second reading can hold, as `readers.json` names them
PARTS = ("second_coding", "check")
#: What each file given to the second coder is, by where it came from
KINDS = ("documents", "definitions", "format", "brief")
#: The helpers' log as close found it: no note at all, a helper started without a stop or a readable transcript, or whole
LOG = ("absent", "partial", "complete")
#: How a helper's prompt compares with a brief: the brief and nothing else, the brief with more around it, or neither
PROMPT = ("alone", "within", "other")
#: Where a tool call reaches: inside the second coder's folder, outside it, or naming no folder (counted as outside)
WHERE = ("in", "out", "none")
#: The tools that write the file they name; every other call that names a file opens it
WRITES = ("Write", "Edit", "MultiEdit", "NotebookEdit")
#: The fields in which Claude Code's tools name the file or folder they act on
PATH_FIELDS = ("file_path", "notebook_path", "path")
#: The searches whose target is a folder, searched wherever the session is when none is given
SEARCHES = ("Glob", "Grep")
#: The list of open runs in the plugin's data folder, which the hook reads before anything else
OPEN = "isolating.json"
#: How long a run stays listed for the hook when it is never closed
STALE_MS = 2 * 24 * 3600 * 1000
#: Where the brief names the coder's folder, and its own part of the coding, which `open_folder` fills in
FOLDER, BATCH = "{{folder}}", "{{batch}}"
#: Each coder's part of the second coding, within its folder, and the join's record of them
BATCHES, JOINED = "batches", "joined.json"
#: The engine's own records in the second coder's folder, which a coder reading or writing is not counted as reading
#: or writing a file it was given or made
RECORDS = ("given.json", "helpers.json", "readers.json", JOINED)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _norm(text: str) -> str:
    """A prompt as compared with a brief: its runs of whitespace one space each, whatever line endings or wrapping it
    passed through on its way to the Agent tool."""
    return " ".join(text.split())


def _key(run: Path) -> str:
    return _sha(os.path.normcase(os.path.abspath(run)).encode("utf-8"))[:16]


def _data(data: str | None) -> Path | None:
    """The plugin's data folder, or None where it was not named or not filled in, as where a skill's `${...}` was
    passed on unexpanded."""
    return Path(data) if data and "${" not in data else None


def _write_json(p: Path, obj) -> None:
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def _documents(run: Path) -> list[str]:
    with open(run / "corpus" / "index.csv", encoding="utf-8", newline="") as fh:
        return [r["id"] for r in csv.DictReader(fh)]


def open_folder(run: Path, brief: Path, data: str | None = None, parts: tuple = PARTS, batches: int = 1) -> list[str]:
    """Make the second coder's folder and open the helpers' log; return the prompt for each helper, in batch order
    (none where the second reading is the check alone)."""
    run = Path(os.path.abspath(run))
    recode = run / "recode"
    if (recode / "given.json").exists():
        raise SystemExit(f"{recode / 'given.json'} exists: this second reading was opened already. Remove recode/ to "
                         "start it again, or run close.")
    unknown = [p for p in parts if p not in PARTS]
    if unknown or not parts:
        raise SystemExit(f"parts must be among {PARTS}, not {unknown or 'none'}")
    files, prompts, template, given_batches = {}, [], b"", []
    if "second_coding" in parts:
        if recode.exists() and any(recode.iterdir()):
            raise SystemExit(f"{recode} already holds files; the second coder's folder must hold only what it is given")
        recode.mkdir(exist_ok=True)
        shutil.copytree(run / "corpus", recode / "corpus")
        shutil.copy2(run / "workflow.json", recode / "workflow.json")
        if (run / "contract" / "pieces.md").is_file():
            (recode / "contract").mkdir()
            shutil.copy2(run / "contract" / "pieces.md", recode / "contract" / "pieces.md")
        template = brief.read_bytes()
        text = template.decode("utf-8").replace("\r\n", "\n")
        if missing := [p for p in (FOLDER, BATCH) if p not in text]:
            shutil.rmtree(recode)
            raise SystemExit(f"{brief} does not name {' or '.join(missing)}, so the second coder's folder or its own part of "
                             "the coding would go unnamed")
        docs = _documents(run)
        n = max(1, min(batches, len(docs)))
        size = -(-len(docs) // n)
        groups = [docs[i:i + size] for i in range(0, len(docs), size)]
        names = ["brief.md"] if len(groups) == 1 else [f"briefs/{i + 1}.md" for i in range(len(groups))]
        for i, (name, group) in enumerate(zip(names, groups), 1):
            filled = text.replace("{{documents}}", "all of them" if len(groups) == 1 else "these: " + ", ".join(group))
            filled = filled.replace(BATCH, str(i))
            (recode / name).parent.mkdir(exist_ok=True)
            (recode / name).write_text(filled, encoding="utf-8", newline="\n")
            prompts.append(filled.replace(FOLDER, str(recode)))
            given_batches.append({"name": str(i), "brief": name, "documents": group})
        for p in sorted(recode.rglob("*")):
            if p.is_file():
                rel = p.relative_to(recode).as_posix()
                kind = ("documents" if rel.startswith("corpus/") else "definitions" if rel == "workflow.json"
                        else "format" if rel.startswith("contract/") else "brief")
                files[rel] = {"sha256": _sha(p.read_bytes()), "kind": kind}
    else:
        recode.mkdir(exist_ok=True)
    folder = _data(data)
    given = {"parts": list(parts), "files": files, "brief_shipped": {"sha256": _sha(template)} if template else None,
             "batches": given_batches, "opened": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "log_opened": folder is not None}
    _write_json(recode / "given.json", given)
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
        listed = _read_open(folder)
        listed["runs"][_key(run)] = {"opened": int(time.time() * 1000), "events": str(folder / "helper-events" / _key(run))}
        _write_json(folder / OPEN, listed)
    return prompts


def steps_to_code(workflow: dict) -> list[dict]:
    """The code steps each second coder writes a part of: those whose rows are coded from the documents
    (`workflow.coded_from_documents`), as the recount reads them from `coded/`."""
    return W.coded_from_documents(workflow.get("steps") or [])


def _read_by(s: dict, documents: list[str]) -> list[str] | None:
    """Those of a batch's documents a code step reads, where fixed rules can say so from the definitions alone: all of
    them for a step reading the documents, less any the earlier run it takes its definitions from never read
    (`steps.code_documents`); None for a step reading a sample, whose documents only the recount draws."""
    if "documents" not in (s.get("inputs") or []):
        return None
    there = s["from"].get("documents") if isinstance(s.get("from"), dict) else None
    return [d for d in documents if there is None or d in there]


def _given(recode: Path) -> dict:
    p = recode / "given.json"
    if not p.is_file():
        raise SystemExit(f"{p} does not exist: run open before the second reading")
    return json.loads(p.read_text(encoding="utf-8"))


def join_faults(recode: Path, given: dict | None = None) -> list[str]:
    """Why the second coding's parts cannot be joined into one coding of every document it was given, one line each,
    or nothing: a part missing a step's file, a file that is not a list of rows, a row naming a document outside its
    batch, or a step with one row per document that leaves out one of its batch's documents it reads (`_read_by`)."""
    given = given or _given(recode)
    workflow = json.loads((recode / "workflow.json").read_text(encoding="utf-8"))
    faults = []
    if not given.get("batches"):
        return [f"{recode / 'given.json'} lists no batch of documents to join"]
    for b in given["batches"]:
        mine = set(b["documents"])
        for s in steps_to_code(workflow):
            p = recode / BATCHES / b["name"] / f"{s['id']}.json"
            where = f"batch {b['name']} ({len(mine)} document{'' if len(mine) == 1 else 's'}), step {s['id']}"
            if not p.is_file():
                faults.append(f"{where}: {p.relative_to(recode).as_posix()} is missing, so its documents have no second coding")
                continue
            try:
                rows = json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                faults.append(f"{where}: {p.relative_to(recode).as_posix()} is not JSON ({e})")
                continue
            if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
                faults.append(f"{where}: {p.relative_to(recode).as_posix()} is not a list of rows")
                continue
            outside = sorted({str(r.get("document")) for r in rows} - mine)
            if outside:
                faults.append(f"{where}: rows name documents outside the batch: {', '.join(outside)}")
            named = {r.get("document") for r in rows}
            if s.get("per_document") and (left := [d for d in _read_by(s, b["documents"]) or [] if d not in named]):
                faults.append(f"{where}: one row per document, but none for {', '.join(left)}")
    return faults


def join(run: Path) -> dict:
    """Join the second coding's parts into `recode/coded/`, each step's rows in batch order, and their notes on unclear
    passages into `recode/unclear.md`; record each part and each joined file in `recode/joined.json`. Refuses, writing
    nothing, on any of `join_faults`, or where `coded/` holds rows the join did not write."""
    recode = Path(os.path.abspath(run)) / "recode"
    given = _given(recode)
    if "second_coding" not in given.get("parts", []):
        raise SystemExit("this second reading is the check alone: there is no second coding to join")
    if (recode / "coded").exists() and not (recode / JOINED).is_file():
        raise SystemExit(f"{recode / 'coded'} holds rows the join did not write; each second coder writes its part under "
                         f"{BATCHES}/, as its brief says, and the join alone writes coded/")
    if faults := join_faults(recode, given):
        raise SystemExit("the second coding was not joined, since it would not cover every document it was given:\n- "
                         + "\n- ".join(faults))
    workflow = json.loads((recode / "workflow.json").read_text(encoding="utf-8"))
    record = {"batches": {}, "coded": {}, "joined": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (recode / "coded").mkdir(exist_ok=True)
    notes = []
    for b in given["batches"]:
        part = recode / BATCHES / b["name"]
        record["batches"][b["name"]] = {s["id"]: _sha((part / f"{s['id']}.json").read_bytes()) for s in steps_to_code(workflow)}
        if (part / "unclear.md").is_file():
            notes.append((part / "unclear.md").read_text(encoding="utf-8").strip())
    for s in steps_to_code(workflow):
        rows = [r for b in given["batches"] for r in json.loads((recode / BATCHES / b["name"] / f"{s['id']}.json").read_text(encoding="utf-8"))]
        out = recode / "coded" / f"{s['id']}.json"
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        record["coded"][s["id"]] = {"rows": len(rows), "sha256": _sha(out.read_bytes())}
    if any(notes):
        (recode / "unclear.md").write_text("\n\n".join(n for n in notes if n) + "\n", encoding="utf-8", newline="\n")
    _write_json(recode / JOINED, record)
    return record


def joined_faults(recode: Path) -> list[str]:
    """For a second reading `isolate.py` opened, why its `coded/` is not the joined coding of every document it was
    given: the join never ran, a part no longer passes `join_faults`, or a file in `coded/` is not what the join wrote.
    Nothing for a run whose second reading was not opened by `isolate.py`, or is the check alone."""
    if not (recode / "given.json").is_file():
        return []
    given = _given(recode)
    if "second_coding" not in given.get("parts", []):
        return []
    if not (recode / JOINED).is_file():
        return [f"the second coding was never joined: run isolate.py join, which writes {recode / 'coded'} from each "
                f"coder's part under {BATCHES}/"]
    faults = join_faults(recode, given)
    record = json.loads((recode / JOINED).read_text(encoding="utf-8"))
    written = {p.stem for p in (recode / "coded").glob("*.json")}
    for sid in sorted(written | set(record["coded"])):
        p = recode / "coded" / f"{sid}.json"
        if sid not in record["coded"]:
            faults.append(f"coded/{sid}.json was not written by the join")
        elif not p.is_file() or _sha(p.read_bytes()) != record["coded"][sid]["sha256"]:
            faults.append(f"coded/{sid}.json is not what the join wrote; run isolate.py join again")
    return faults


def _read_open(folder: Path) -> dict:
    try:
        listed = json.loads((folder / OPEN).read_text(encoding="utf-8"))
        return listed if isinstance(listed.get("runs"), dict) else {"runs": {}}
    except (OSError, ValueError, AttributeError):
        return {"runs": {}}


def transcript(path: Path) -> dict:
    """A helper's transcript as Claude Code writes it: the prompt it was started with (its first user message) and each
    tool call it made, once each, with the folder the session was in."""
    raw = path.read_bytes()
    prompt, cwd, calls, seen = None, None, [], set()
    for line in raw.decode("utf-8", "replace").splitlines():
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if not isinstance(x, dict):
            continue
        m = x.get("message") if isinstance(x.get("message"), dict) else {}
        c = m.get("content")
        if prompt is None and x.get("type") == "user":
            prompt = c if isinstance(c, str) else "".join(b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text")
            cwd = x.get("cwd")
        if x.get("type") == "assistant" and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in seen:
                    seen.add(b.get("id"))
                    calls.append({"tool": b.get("name"), "input": b.get("input") if isinstance(b.get("input"), dict) else {},
                                  "cwd": x.get("cwd") or cwd})
    return {"prompt": prompt, "calls": calls, "sha256": _sha(raw), "lines": raw.count(b"\n")}


def _abs(p: str, cwd: str | None) -> Path:
    q = Path(p)
    return Path(os.path.normcase(os.path.abspath(q if q.is_absolute() or not cwd else Path(cwd) / q)))


def _within(p: Path, folder: Path) -> bool:
    return p == folder or folder in p.parents


def placed(call: dict, run: Path, recode: Path) -> dict:
    """One tool call as the log keeps it: the tool, whether it writes, the file or folder it names relative to the run
    (none outside the run), and where it reaches (`WHERE`). A search's pattern that climbs out of its folder, or is a
    path of its own, is placed by where it reaches."""
    run, recode = (_abs(str(x), None) for x in (run, recode))
    named = next((call["input"][f] for f in PATH_FIELDS if isinstance(call["input"].get(f), str) and call["input"][f]), None)
    where, target = "none", None
    if named is not None:
        target = _abs(named, call.get("cwd"))
        where = "in" if _within(target, recode) else "out"
        # Glob's pattern, and Grep's file glob, are paths too: one that climbs out or starts afresh reaches elsewhere
        pattern = call["input"].get("pattern" if call["tool"] == "Glob" else "glob") if call["tool"] in SEARCHES else None
        if where == "in" and isinstance(pattern, str) and (Path(pattern).is_absolute() or ".." in Path(pattern).parts):
            reach = _abs(pattern if Path(pattern).is_absolute() else str(target / pattern), None)
            where = "in" if _within(reach, recode) else "out"
    rel = target.relative_to(run).as_posix() if target is not None and _within(target, run) and target != run else None
    return {"tool": call["tool"], "writes": call["tool"] in WRITES, "path": rel, "where": where}


def _prompt(prompt: str | None, briefs: dict[str, str]) -> dict:
    p = _norm(prompt or "")
    for name, text in briefs.items():
        b = _norm(text)
        if p == b:
            return {"as": "alone", "brief": name, "more": 0, "chars": len(p), "sha256": _sha(p.encode("utf-8"))}
        if b and b in p:
            return {"as": "within", "brief": name, "more": len(p) - len(b), "chars": len(p), "sha256": _sha(p.encode("utf-8"))}
    return {"as": "other", "brief": None, "more": None, "chars": len(p), "sha256": _sha(p.encode("utf-8"))}


def _writes_rows(call: dict) -> bool:
    """Whether a placed tool call wrote a second coder's rows: a file in its part of the coding, under `batches/`."""
    return call["writes"] and (call["path"] or "").startswith(f"recode/{BATCHES}/")


def _agent_calls(path: Path) -> list[dict]:
    """The Agent tool's calls in the session's own transcript, each with the prompt it gave."""
    try:
        return [c for c in transcript(path)["calls"] if c["tool"] in ("Agent", "Task")]
    except OSError:
        return []


def close(run: Path, data: str | None = None, same: tuple = ()) -> dict:
    """Write `recode/helpers.json` and `recode/readers.json` from the helpers' log, and take the run off the hook's list.
    Returns what `helpers.json` holds."""
    run = Path(os.path.abspath(run))
    recode = run / "recode"
    given_p = recode / "given.json"
    if not given_p.is_file():
        raise SystemExit(f"{given_p} does not exist: run open before the second reading, then close after it")
    given = json.loads(given_p.read_text(encoding="utf-8"))
    if bad := [p for p in same if p not in given["parts"]]:
        raise SystemExit(f"--same names {bad}, which this second reading does not hold ({given['parts']})")
    folder = _data(data)
    listed = _read_open(folder) if folder else {"runs": {}}
    entry = listed["runs"].get(_key(run))
    if entry is None and (recode / "helpers.json").is_file():
        print(f"{recode / 'helpers.json'} was written when this second reading closed; nothing changed")
        return json.loads((recode / "helpers.json").read_text(encoding="utf-8"))
    notes = []
    events = Path(entry["events"]) if entry else None
    if events and events.is_dir():
        for p in sorted(events.glob("*.json")):
            try:
                notes.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    briefs = {p.relative_to(recode).as_posix(): p.read_text(encoding="utf-8").replace(FOLDER, str(recode))
              for p in [recode / "brief.md", *sorted((recode / "briefs").glob("*.md"))] if p.is_file()}
    # each helper of a session in this run's folder, or above it, or in it: a helper of an unrelated session is not listed
    here = os.path.normcase(str(run))
    def related(n):
        cwd = os.path.normcase(os.path.abspath(n["cwd"])) if n.get("cwd") else None
        return cwd is not None and (here == cwd or here.startswith(cwd.rstrip("\\/") + os.sep) or cwd.startswith(here + os.sep))
    by = {}
    for n in notes:
        if n.get("agent_id") and related(n):
            h = by.setdefault(n["agent_id"], {"agent": n["agent_id"], "type": n.get("agent_type"), "started": False,
                                              "stopped": False, "_transcript": None, "_session": None})
            h["started"] |= n.get("event") == "SubagentStart"
            if n.get("event") == "SubagentStop":
                h["stopped"], h["_transcript"] = True, n.get("agent_transcript_path")
                h["_session"] = n.get("transcript_path")
            h["type"] = h["type"] or n.get("agent_type")
    helpers, whole = [], bool(by)
    agent_calls = {}
    for h in by.values():
        t = None
        if h["_transcript"]:
            try:
                t = transcript(Path(h["_transcript"]))
            except OSError:
                t = None
        whole &= h["stopped"] and t is not None
        if h["_session"] and h["_session"] not in agent_calls:
            agent_calls[h["_session"]] = _agent_calls(Path(h["_session"]))
        out = {"agent": h["agent"], "type": h["type"], "started": h["started"], "stopped": h["stopped"],
               "transcript": {"sha256": t["sha256"], "lines": t["lines"]} if t else None,
               "prompt": _prompt(t["prompt"], briefs) if t else None,
               "calls": [placed(c, run, recode) for c in t["calls"]] if t else None}
        if t:  # the Agent call that started it, matched by its prompt, never by order
            p = _norm(t["prompt"] or "")
            out["agent_calls"] = sum(1 for c in agent_calls.get(h["_session"], []) if _norm(str(c["input"].get("prompt") or "")) == p)
        helpers.append(out)
    log = "absent" if not by else "complete" if whole else "partial"
    record = {"log": log, "helpers": helpers}
    _write_json(recode / "helpers.json", record)
    wrote = {"second_coding": _writes_rows, "check": lambda c: c["writes"] and c["path"] == "check.md"}
    readers = {}
    for part in given["parts"]:
        by_helper = log == "complete" and any(any(wrote[part](c) for c in h["calls"] or []) for h in helpers)
        readers[part] = "separate" if by_helper else "same" if part in same else "unrecorded"
    _write_json(recode / "readers.json", readers)
    if folder and entry:
        listed["runs"].pop(_key(run), None)
        if listed["runs"]:
            _write_json(folder / OPEN, listed)
        else:
            (folder / OPEN).unlink(missing_ok=True)
        if events:
            shutil.rmtree(events, ignore_errors=True)
    return record


# What a report says from these records ---------------------------------------------------------------------------

def recorded(R: dict) -> bool:
    """Whether the run's second reading was opened by `isolate.py`, so that what a report says of who did it comes from
    these records rather than from `readers.json` alone."""
    return bool(R.get("given"))


def _coders(R: dict) -> list[dict]:
    """The helpers the log shows writing the second coding's rows, where the log is whole."""
    H = R.get("helpers") or {}
    if H.get("log") != "complete":
        return []
    return [h for h in H.get("helpers") or [] if any(_writes_rows(c) for c in h.get("calls") or [])]


def _in_folder(call: dict) -> str | None:
    """The file a placed tool call names inside the second coder's folder, relative to that folder, or None."""
    path = call["path"] or ""
    return path.removeprefix("recode/") if call["where"] == "in" and path.startswith("recode/") else None


def figures(R: dict) -> dict:
    """The figures the statements below give, each read by fixed rules from `given.json` and `helpers.json`."""
    given, coders = R.get("given") or {}, _coders(R)
    calls = [c for h in coders for c in h.get("calls") or []]
    # outside the folder, a file or folder named by any call counts as opened, a folder searched too, and a call
    # outside the run, whose path is not kept, as one each
    opened = lambda where: len({c["path"] or f"#{i}" for i, c in enumerate(calls)
                                if c["where"] == where and (where == "out" or c["tool"] not in SEARCHES)})
    # inside it, a file is read by a call that names it without writing it, and written by one that writes it; the
    # engine's own records there (`RECORDS`) are neither, since they were not given to the coder to code from
    named = lambda writes: {f for c in calls if c["writes"] == writes and c["tool"] not in SEARCHES
                            and (f := _in_folder(c)) and f not in RECORDS}
    read, given_files = named(False), set(given.get("files") or {})
    alone = sum(1 for h in coders if (h.get("prompt") or {}).get("as") == "alone")
    single = (coders[0].get("prompt") or {}) if len(coders) == 1 else {}
    return {
        "files given to the second coder": len(given.get("files") or {}),
        "kinds given to the second coder": sorted({f["kind"] for f in (given.get("files") or {}).values()}, key=KINDS.index),
        "helpers' log": (R.get("helpers") or {}).get("log") or "absent",
        "second coders the log shows": len(coders),
        "second coders started with their brief alone": alone,
        "second coder prompt beyond its brief": single.get("more") if single.get("as") == "within" else None,
        "second coder prompt as its brief": single.get("as"),
        "files given that the second coders read": len(read & given_files),
        "other files the second coders read in their folder": len(read - given_files),
        "files the second coders wrote in their folder": len(named(True)),
        "files the second coders opened outside their folder": opened("out"),
        "second coder calls naming no folder": sum(1 for c in calls if c["where"] == "none"),
        "check made by a helper the log shows": (R.get("helpers") or {}).get("log") == "complete" and any(
            c["writes"] and c["path"] == "check.md" for h in (R.get("helpers") or {}).get("helpers") or [] for c in h.get("calls") or []),
    }


_SOURCE = "the second coder's folder and the helpers' log, check/given.json and check/helpers.json"
for _name in ("files given to the second coder", "kinds given to the second coder", "helpers' log",
              "second coders the log shows", "second coders started with their brief alone",
              "second coder prompt beyond its brief", "second coder prompt as its brief",
              "files given that the second coders read", "other files the second coders read in their folder",
              "files the second coders wrote in their folder", "files the second coders opened outside their folder",
              "second coder calls naming no folder", "check made by a helper the log shows"):
    claims.measure(_name, "fixed rules", _SOURCE, (lambda n: lambda R, D=None: figures(R)[n])(_name))
del _name

#: How the folder's contents are named, by kind, in a report
KIND_SAID = {"documents": "the documents", "definitions": "the definitions", "format": "the format", "brief": "the brief"}


def _listed(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _files(n: int) -> str:
    return f"{n} file" if n == 1 else f"{n} files"


def told(R: dict, parts: list[str], analyst: dict) -> list[tuple]:
    """Who did each part of the second reading, as (sentence, part, mark) pieces for the procedure in words; `analyst`
    gives `procedure`'s own reading of what the analyst said of a part it did itself (True where it says so)."""
    F = figures(R)
    pieces = []
    if "second_coding" in parts:
        held = _listed([KIND_SAID[k] for k in F["kinds given to the second coder"]])
        n, k = F["files given to the second coder"], F["second coders the log shows"]
        base = {"files given to the second coder": n, "kinds given to the second coder": F["kinds given to the second coder"],
                "helpers' log": F["helpers' log"], "second coders the log shows": k}
        if k:
            read, other, wrote, outside, none = (F[x] for x in (
                "files given that the second coders read", "other files the second coders read in their folder",
                "files the second coders wrote in their folder", "files the second coders opened outside their folder",
                "second coder calls naming no folder"))
            alone, more, as_ = (F["second coders started with their brief alone"], F["second coder prompt beyond its brief"],
                                F["second coder prompt as its brief"])
            # several coders are each said to have had a share of their own only where each prompt held a different brief
            shares = len({(h.get("prompt") or {}).get("brief") for h in _coders(R)} - {None}) == k
            who = ("A separate coder did the second coding" if k == 1 else f"{k} separate coders did the second coding"
                   + (", each on its own share of the documents" if shares else ""))
            if alone == k:
                start = "it was started with the brief alone" if k == 1 else "each was started with its brief alone"
            elif k == 1 and as_ == "within":
                start = f"it was started with the brief and {more} characters more"
            elif k == 1:
                start = "it was started with a prompt other than the brief"
            else:
                start = f"{alone} of the {k} started with its brief alone"
            them, its, was = ("it", "its", "was") if k == 1 else ("they", "their", "were")
            # what was read is given out of what was given, so a reader sees whether every file given was read
            did = [f"read {read} of the {n} files {them} {was} given"
                   + (f" and {other} other {'file' if other == 1 else 'files'} in {its} folder" if other else ""),
                   f"wrote {_files(wrote)} in {its} folder"]
            if outside or not none:
                place = "file or folder" if outside == 1 else "files or folders"
                did.append(f"opened {outside} {place} outside it" if outside else "opened nothing outside it")
            opened = f", and the run's log of {its} tools shows {them} {_listed(did)}"
            if none:
                opened += f", and {none} of {its} calls named no folder, so they are counted as outside it"
            sentence = f" {who}, in a folder of {its} own holding only {held}, {n} files in all; {start}{opened}."
            figs = {**base, "second coders started with their brief alone": alone,
                    "files given that the second coders read": read,
                    "other files the second coders read in their folder": other,
                    "files the second coders wrote in their folder": wrote,
                    "files the second coders opened outside their folder": outside,
                    "second coder calls naming no folder": none}
            if k == 1:
                figs["second coder prompt as its brief"] = as_
                if as_ == "within":
                    figs["second coder prompt beyond its brief"] = more
            pieces.append((sentence, "second_coding", {"kind": "record", "is": figs}))
        else:
            sentence = (f" The second coder was given a folder of its own holding only {held}, {n} files in all; the run "
                        "does not record what it opened")
            mark = {"kind": "record", "is": base}
            if analyst.get("second_coding"):
                sentence += "; the analyst's record says it did the second coding itself, so that coding is not independent of the first"
                mark = {"kind": "reader", "is": {**base, "second coder separate": False}}
            pieces.append((sentence + ".", "second_coding", mark))
    if "check" in parts:
        if F["check made by a helper the log shows"]:
            pieces.append((" A separate reader made the check, as the run's log of its helpers shows.", "check",
                           {"kind": "record", "is": {"check made by a helper the log shows": True}}))
        elif analyst.get("check"):
            pieces.append((" The analyst's record says it made the check itself.", "check",
                           {"kind": "reader", "is": {"check reader separate": False}}))
        else:
            pieces.append((" The run does not record who made the check.", "check",
                           {"kind": "record", "is": {"check made by a helper the log shows": False}}))
    return pieces
