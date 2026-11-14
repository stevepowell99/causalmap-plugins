"""A ballpark of the carbon a run cost, as kilometres driven by an average UK car, from what the run's zip holds.

No step of a plugin run records its tokens, since the run happens in the evaluator's own Claude. So the estimate is
made from the run's size: the characters of every document, read in full once by each code step, once more by the
second coder and once more by the check where the run was checked; the tables and workflow the writer read; and
everything the run wrote (coded rows, answer, the check's record, the analyst's scripts). Characters become tokens at
`chars_per_token`. The range then runs from the low energy rates applied to that once, to the high rates applied with
the agent's overhead (`overhead_high`), which is the larger of the two uncertainties.

A revised run covers every iteration. The zip holds only the latest state, so each revision is counted from it: at
the low end as rereading the answer and tables and writing the answer again, at the high end as a whole run again.

Constants, with their sources, are in `footprint.json`, the one place they are kept.
"""
import json
from pathlib import Path

K = json.loads((Path(__file__).with_name("footprint.json")).read_text(encoding="utf-8"))


def sizes(names, read, index_files, has_check, n_code):
    """(characters read, characters written, characters a revision rereads at least) for one full iteration."""
    size = lambda n: len(read(n).decode("utf-8", errors="replace"))
    docs = sum(size("corpus/" + f) for f in index_files if "corpus/" + f in names)
    passes = n_code + (2 if has_check else 0)
    tables = sum(size(n) for n in names if n.startswith("steps/")) + size("workflow.json")
    written = sum(size(n) for n in names if n.startswith(("coded/", "check/", "work/"))) + size("answer.md")
    answer = size("answer.md")
    return docs * passes + tables, written, tables + answer, answer


def wh(read_chars, written_chars, low):
    t_in, t_out = read_chars / K["chars_per_token"] / 1000, written_chars / K["chars_per_token"] / 1000
    rate = (t_in * K["wh_per_1k_input_high"] * (1 if low else K["overhead_high"]) + t_out * K["wh_per_1k_output_high"])
    return rate / K["low_divisor"] if low else rate


def km(watt_hours):
    return watt_hours / 1000 * K["grid_kg_per_kwh"] / K["car_kg_per_km"]


def estimate(z, index, workflow, revisions):
    """The range for a run's zip: {'low', 'high'} in kilometres and Wh, the iterations covered, and what it is made from."""
    names = set(z.namelist())
    files = [d.get("file") or f"{d['id']}.txt" for d in index]
    steps = workflow.get("steps", [])
    codes = {s.get("id") for s in steps if s.get("kind") == "code"}  # a code step reading code steps reads no document
    n_code = sum(1 for s in steps if s.get("kind") == "code" and not (s.get("inputs") and all(i in codes for i in s["inputs"])))
    has_check = "check/check.md" in names
    read_c, wrote_c, reread_c, answer_c = sizes(names, z.read, files, has_check, n_code)
    n_rev = sum(1 for l in revisions.splitlines() if l.strip().startswith("- "))
    low = wh(read_c, wrote_c, True) + n_rev * wh(reread_c, answer_c, True)
    high = (1 + n_rev) * wh(read_c, wrote_c, False)
    return {"low_wh": low, "high_wh": high, "low_km": km(low), "high_km": km(high), "revisions": n_rev,
            "documents": len(files), "code_steps": n_code, "checked": has_check,
            "read_tokens": round(read_c / K["chars_per_token"]), "written_tokens": round(wrote_c / K["chars_per_token"])}


def combined(estimates):
    """Several runs' ranges summed, as a combined report gives them."""
    keys = ("low_wh", "high_wh", "low_km", "high_km", "revisions", "read_tokens", "written_tokens")
    return {k: sum(e[k] for e in estimates) for k in keys} | {"parts": len(estimates)}


def distance(x):
    """Kilometres in words, for either end of a range: two significant figures however small (12, 6.8, 0.034,
    0.00061, 130), never rounded to nought. `webapp/js/ai-footprint.js` carries the same rule, and `km_examples` in
    footprint.json holds the cases both are tested against."""
    if not x > 0:
        return "0"
    r = float(f"{x:.2g}")
    if r >= 10:
        return f"{r:.0f}"
    said = f"{x:.{max(0, 1 - int(f'{x:.1e}'.split('e')[1]))}f}"
    return said.rstrip("0").rstrip(".") if "." in said else said


def headline(low_km, high_km, combined=False):
    """The carbon line's text: always both ends of the range, in kilometres."""
    unit = "km driven in an average UK family car"
    return f"Carbon cost of this {'combined report' if combined else 'report'}: Between {distance(low_km)} and {distance(high_km)} {unit}"


def covers(n_rev):
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    return "" if not n_rev else " It covers the first run and its revision." if n_rev == 1 else (f" It covers the first run and its {words.get(n_rev, n_rev)} "
                                 "revisions.")
