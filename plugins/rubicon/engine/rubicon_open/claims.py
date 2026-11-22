"""What a report says about the run's own work, written with what each statement rests on, so that fixed rules can
recompute it from the run's zip.

Each such statement is a claim, resting on figures the run's records give, or is said, describing the procedure in
words no record could contradict:

- `claim(inner, kind, figures, names)` marks a claim. `figures` maps named measures (`MEASURES`) to the values the
  statement gives. A measure is a function of the loaded run, registered with `measure` beside the code that already
  owns that figure, and it says who made the figure: fixed rules, or an AI reader in its own record. A measure of one
  step, or of one thing in the run, takes it after an `@`, as `"documents drawn@s_pick"`. `names` are the words in the
  claim that the run's records chose rather than Rubicon (a label, a definition, a question, a verdict), whose digits
  are part of a name and never a number the claim gives.
- `said(inner)` marks a description; `said(inner, "date")`, or "id", "name" or "version", one whose digits are a date,
  an ID, a name or a version rather than a number.
- `CONTAINER` marks an element every statement of which is marked, and `basis` and `plain` give the attribute alone,
  for an element of the caller's own.

The kinds of claim: "count", figures fixed rules made; "record", what the run's records hold or lack, as fixed rules
read them; "reader", a statement any of whose figures is an AI reader's own, which no other kind may carry.

A statement keeps its words. The marks are attributes nobody sees (`data-basis`, `data-said`, `data-claims`), and
`unmarked` takes them out of a Word copy. `refuse` is called on what the renderer has written and stops it where a
claim does not hold: a figure that differs from what the run gives, a number in its words that none of its figures
gives, or an AI reader's figure in a claim of another kind. The claims checker (`rubicon/tools/report_claims.py`) reads
a created report's marks with `marks` and judges each claim with the same `holds`, recomputing from the run's zip.
"""
from __future__ import annotations

import html
import html.parser
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

#: The kinds of claim, as the module's docstring defines them
KINDS = ("count", "record", "reader")
#: Who makes a measure's figure
BY = ("fixed rules", "reader")
#: What a said statement's digits may be; a plain one ("") holds none
SAID = ("", "date", "id", "name", "version")
CONTAINER = ' data-claims=""'
NUMBER = re.compile(r"\d+")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


@dataclass(frozen=True)
class Measure:
    by: str                                   # "fixed rules" or "reader"
    of: str                                   # where in the run the figure is read, for whoever reads a refusal
    get: Callable[..., Any]                   # (the loaded run, `build_data` of it or None[, what]) -> the figure
    takes: bool = False                       # whether it measures one thing named after its `@`


#: Every measure a claim may rest on, by name, filled by `measure` where each figure's code lives
MEASURES: dict[str, Measure] = {}


def measure(name: str, by: str, of: str, get: Callable[..., Any], takes: bool = False) -> None:
    if by not in BY:
        raise ValueError(f"a measure is made by one of {BY}, not {by!r}")
    if "@" in name:
        raise ValueError(f"a measure's name holds no @, which names what it measures: {name!r}")
    MEASURES[name] = Measure(by, of, get, takes)


def _measure(name: str) -> tuple[Measure | None, str | None, str]:
    """The measure a figure names, what it measures where it takes one, and why not where the name is no measure's."""
    base, at, what = name.partition("@")
    m = MEASURES.get(base)
    if m is None:
        return None, None, f"names no measure there is: {name!r}"
    if m.takes != bool(at):
        return None, None, (f"names {base!r} without the thing it measures after an @" if m.takes else
                            f"names {base!r}, which measures the whole run, with {what!r} after an @")
    return m, (what if at else None), ""


def _figures(kind: str, figures: dict, names=()) -> str:
    """The basis as the page carries it, after checking it names a kind and measures that exist, so that a fault in
    writing a claim shows where it is written."""
    if kind not in KINDS:
        raise ValueError(f"a claim's kind is one of {KINDS}, not {kind!r}")
    unknown = [why for n in figures for m, _, why in [_measure(n)] if m is None]
    if unknown:
        raise ValueError("a claim " + "; ".join(unknown))
    readers = [n for n in figures if _measure(n)[0].by == "reader"]
    if readers and kind != "reader":
        raise ValueError(f"{', '.join(readers)} is an AI reader's own figure, which only a reader's claim may give")
    names = [str(x) for x in names if str(x).strip()]
    return json.dumps({"kind": kind, "is": figures, **({"names": names} if names else {})}, ensure_ascii=False, sort_keys=True)


def basis(kind: str, figures: dict, names=()) -> str:
    """The attribute that makes an element of the caller's own a claim."""
    return f' data-basis="{html.escape(_figures(kind, figures, names))}"'


def plain(of: str = "") -> str:
    """The attribute that makes an element of the caller's own a said statement."""
    if of not in SAID:
        raise ValueError(f"a said statement's digits are one of {SAID[1:]}, not {of!r}")
    return f' data-said="{of}"'


def claim(inner: str, kind: str, figures: dict, names=()) -> str:
    """`inner`, written HTML, as a claim resting on `figures`, holding `names` the run chose."""
    return f"<span{basis(kind, figures, names)}>{inner}</span>" if inner else ""


def said(inner: str, of: str = "") -> str:
    """`inner`, written HTML, as a said statement."""
    return f"<span{plain(of)}>{inner}</span>" if inner else ""


def unmarked(page: str) -> str:
    """The same HTML without the marks, for a Word copy: what a reader sees is unchanged."""
    return re.sub(r' data-(?:basis|said|claims)="[^"]*"', "", page)


def _words(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def run_named(R: dict) -> str:
    return R.get("run_id") or R.get("name") or (R.get("workflow") or {}).get("question_as_agreed") or "(a run with no name)"


def holds(basis: dict, text: str, R: dict, D: Any = None) -> list[str]:
    """Why a claim does not hold against the run, one line each, or nothing where it holds. Each line names the claim's
    kind, its words, its basis and the run, so a refused report says what to look at."""
    kind, figures, names = basis.get("kind"), basis.get("is") or {}, basis.get("names") or []
    said_as = (f"the {kind} claim {_words(text)[:200]!r}, resting on {json.dumps(figures, ensure_ascii=False, sort_keys=True)},"
               f" in run {run_named(R)}")
    out = []
    if kind not in KINDS:
        return [f"{said_as} is of no kind a claim can be"]
    for name, value in figures.items():
        m, what, why = _measure(name)
        if m is None:
            out.append(f"{said_as} {why}")
            continue
        if m.by == "reader" and kind != "reader":
            out.append(f"{said_as} gives an AI reader's own figure, {name}, as a {kind}")
        actual = m.get(R, D, what) if m.takes else m.get(R, D)
        if actual != value:
            out.append(f"{said_as} gives {name} as {value!r}, but the run gives {actual!r} ({m.of})")
    # a name's digits are the run's own words, never a number the claim gives; a name its words do not hold is no name.
    # Each name is taken out once, longest first, so one that recurs, or stands inside a longer one, is found each time
    words = _words(text)
    for n in sorted(names, key=lambda n: -len(_words(n))):
        if _words(n) in words:
            words = words.replace(_words(n), " ", 1)
        else:
            out.append(f"{said_as} gives {n!r} as a name in it, which its words do not hold")
    given = {v for v in figures.values() if isinstance(v, int) and not isinstance(v, bool)}
    out += [f"{said_as} writes {n}, which none of its figures gives" for n in NUMBER.findall(words) if int(n) not in given]
    return out


@dataclass
class Mark:
    basis: dict | None       # a claim's basis, or None for a said statement
    said: str | None         # what a said statement's digits may be (`SAID`), or None for a claim
    text: str = ""           # its words, as a reader sees them
    run: int | None = None   # the part of a combined report it belongs to (`data-run`), None outside one


@dataclass
class Marked:
    marks: list = field(default_factory=list)      # every claim and said statement on the page
    loose: list = field(default_factory=list)      # (words, run) inside a container but in no claim or said statement
    containers: int = 0                            # how many elements say every statement in them is marked


class _Reader(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = Marked(), [], 0

    def _run(self):
        return next((f["run"] for f in reversed(self.stack) if f["run"] is not None), None)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self.skip += 1
        if tag in VOID:
            return
        a = dict(attrs)
        frame = {"tag": tag, "mark": None, "container": "data-claims" in a,
                 "run": int(a["data-run"]) if str(a.get("data-run", "")).isdigit() else None}
        self.out.containers += frame["container"]
        self.stack.append(frame)
        run = self._run()
        if "data-basis" in a:
            try:
                b = json.loads(a["data-basis"] or "{}")
            except ValueError:
                b = {"kind": None, "is": {}, "unreadable": a["data-basis"]}
            frame["mark"] = Mark(b, None, run=run)
        elif "data-said" in a:
            frame["mark"] = Mark(None, a["data-said"] or "", run=run)
        if frame["mark"] is not None:
            self.out.marks.append(frame["mark"])

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template"):
            self.skip = max(0, self.skip - 1)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip:
            return
        mark = next((f["mark"] for f in reversed(self.stack) if f["mark"] is not None), None)
        if mark is not None:
            mark.text += data
        elif data.strip() and any(f["container"] for f in self.stack):
            self.out.loose.append((_words(data), self._run()))


def marks(page: str) -> Marked:
    """Every claim and said statement on a page, with the words in its containers that are neither."""
    r = _Reader()
    r.feed(page)
    r.close()
    return r.out


def faults(m: Marked) -> list[str]:
    """What is wrong with the marks themselves, whatever the run: words in a container that are no statement, and a
    plain said statement holding a number, which only a claim may give."""
    out = [f"the words {w[:160]!r} stand in an element whose statements are all to be marked, but are neither a claim "
           "nor said" for w, _ in m.loose]
    out += [f"the said statement {_words(x.text)[:160]!r} holds a number, which only a claim may give"
            for x in m.marks if x.said == "" and NUMBER.search(x.text)]
    out += [f"the said statement {_words(x.text)[:160]!r} is marked as of {x.said!r}, which is none of {SAID[1:]}"
            for x in m.marks if x.basis is None and x.said not in SAID]
    return out


def refuse(written: str, R: dict, D: Any = None) -> str:
    """`written`, unchanged, where every claim in it holds against the run; otherwise no report is created, and the
    message says which claim, on what basis, in which run. Each is a statement Rubicon writes itself, so a refusal is a
    fault in Rubicon, never in the run."""
    wrong = [w for x in marks(written).marks if x.basis is not None for w in holds(x.basis, x.text, R, D)]
    if wrong:
        raise SystemExit("No report is created: " + "; ".join(wrong) + ". Each is a statement Rubicon writes about the "
                         "run's own records, so this is a fault in Rubicon, not in the run")
    return written
