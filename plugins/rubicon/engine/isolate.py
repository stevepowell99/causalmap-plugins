"""Open and close a run's second reading, so that fixed rules record what the second coder was given and what each
helper opened (`rubicon_open/isolation.py` holds the rules).

    python isolate.py <run> open --brief <the plugin's briefs/recode.md> --data <the plugin's data folder> [--batches <n>]
    python isolate.py <run> open --check-only --data <the plugin's data folder>
    python isolate.py <run> join
    python isolate.py <run> close --data <the plugin's data folder> [--same second_coding] [--same check]

`open` makes `recode/`, the second coder's folder, writes `recode/given.json`, opens the helpers' log, and prints the
prompt to start each second coder with; `--check-only` opens the log for a check made without a second coding. `join`
joins each second coder's part, `recode/batches/<n>/`, into `recode/coded/`, and refuses where a part is missing or
does not cover its documents, so a lost batch stops the second reading rather than passing unseen. `close`
writes `recode/helpers.json` and `recode/readers.json` from the log; `--same` names a part the analyst did itself.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubicon_open import isolation  # noqa: E402


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("action", choices=("open", "join", "close"))
    ap.add_argument("--brief")
    ap.add_argument("--data")
    ap.add_argument("--batches", type=int, default=1)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--same", action="append", default=[], choices=isolation.PARTS)
    a = ap.parse_args(argv)
    run = Path(a.run)
    if a.action == "open":
        if not a.check_only and not a.brief:
            sys.exit("open needs --brief, the plugin's briefs/recode.md, unless the second reading is --check-only")
        prompts = isolation.open_folder(run, Path(a.brief) if a.brief else None, a.data,
                                        ("check",) if a.check_only else isolation.PARTS, a.batches)
        log = "opened" if isolation._data(a.data) else "not opened, since no plugin data folder was named"
        print(f"recode/given.json written; the helpers' log is {log}.")
        for i, p in enumerate(prompts, 1):
            print(f"\n=== prompt for second coder {i} of {len(prompts)}: give it exactly as below, with nothing added ===\n{p}\n=== end of prompt {i} ===")
        return
    if a.action == "join":
        joined = isolation.join(run)
        rows = ", ".join(f"{sid} {c['rows']} rows" for sid, c in joined["coded"].items())
        print(f"recode/coded/ joined from {len(joined['batches'])} parts, each with a file for every step and no row outside "
              f"its documents: {rows}.")
        return
    record = isolation.close(run, a.data, tuple(a.same))
    R = {"given": isolation.json.loads((run / "recode" / "given.json").read_text(encoding="utf-8")), "helpers": record,
         "readers": isolation.json.loads((run / "recode" / "readers.json").read_text(encoding="utf-8"))}
    parts = R["given"]["parts"]
    said = "".join(t for t, *_ in isolation.told(R, parts, {p: R["readers"].get(p) == "same" for p in parts}))
    print(f"recode/helpers.json and recode/readers.json written; the helpers' log is {record['log']}, "
          f"{len(record['helpers'])} helpers in it. The report will say:{said}")


if __name__ == "__main__":
    main()
