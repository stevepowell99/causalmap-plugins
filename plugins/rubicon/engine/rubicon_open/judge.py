"""The judge piece: an evaluator's rubric applied to a workflow's tables (`rubicon/docs/pieces.md`).

The standard comes from a person, in advance and under their name (`guidance/skills/rubrics-and-verdicts/SKILL.md`),
so the step carries it written out and the check refuses one with blanks. A judge step:

    {"id": "j", "kind": "judge", "inputs": ["tab", "code"],
     "source": "whose standard it is, or the document it is quoted from",
     "verdicts": [{"name": "Strong", "means": "..."}, {"name": "Weak", "means": "..."}],     # best first
     "criteria": [
       {"id": "reach", "question": "...", "kind": "rule", "table": "tab", "where": {"item": "TIME"},
        "base": {"role": "attender"},                    # the documents counted over; omitted, all of them
        "base_where": {"item": "DELIVERED"},             # or as well: the documents in these cells of the same table
        "levels": [{"verdict": "Strong", "at_least": 8, "where": {"item": "TIME_AND_BACKING"}},  # a level's own cells
                   {"verdict": "Weak"}]},                                                  # tried in order
       {"id": "fit", "question": "...", "kind": "reading", "rows_from": "code", "where": {"item": "FIT"},
        "levels": [{"verdict": "Strong", "descriptor": "..."}, {"verdict": "Weak", "descriptor": "..."}]},
       {"id": "uptake", "question": "...", "kind": "stated", "document": "doc:<id>",
        "quote": "the background document's exact words holding both numbers", "n": 31, "base": 705,
        "levels": [{"verdict": "Strong", "share_at_least": 0.5}, {"verdict": "Weak"}]},
       {"id": "quality", ..., "scale": ["good", "adequate", "poor"],   # a criterion rated on a scale of its own
        "levels": [{"verdict": None, "share_at_least": 0.5, "where": {...}},   # the standard's "no rating can be given"
                   {"verdict": "good", ...}, ...]}],
     "combine": "weakest" | "best" | "separate"
                | [{"verdict": "Strong", "when": {"reach": ["good", "adequate"], "quality": "good"}}, {"verdict": "Weak"}]}

A rule is applied by code: the documents in the base that appear in the table's cells matching `where`, against the
first level whose threshold they meet (`at_least`, `at_most`, `share_at_least`, `share_at_most`); a level with no
threshold is the one reached when none above it is. The base is every document, narrowed by document attributes (`base`)
and by cells of the same table (`base_where`), so that a share can be out of those the coding found doing something,
such as those who delivered; the count is always of documents inside the base. A level may name its own cells
(`where`), for a standard whose levels test different things (good where most have both time and backing, adequate
where most have backing at all): each level is tested on its own cells in order, and every count tested is kept. A stated criterion is a number a background document states, such
as a monitoring record's count of those who did something out of those who could: code finds the quotation in that
document, refuses it unless both numbers are in it, and applies the levels to them as a rule does to a count, so the
number walks back to the document's own words as a count walks back to its rows. A reading is a model weighing the rows against the descriptors:
it gives a verdict, the rows it relied on and those that pull the other way, or says it cannot place the criterion.
Criteria combine by rules, tried in order, the first whose every condition holds deciding; a rule that would hold but
for a criterion that could not be placed leaves the verdict open rather than passing to a later one. Where the standard
rates each criterion on a scale of its own (`scale`) and says how those ratings make the overall verdict, the combine is
its rules as written. "weakest" (a chain, or "all must hold") and "best" (two routes to one end) are shorthands for
rules on the rubric's own verdicts (`as_rules`), so one path applies them all; never an average. A rule or stated level whose verdict is null is the standard's own
test for when no rating can be given. Each combining rule, like each level, says whose it is.
"""
from __future__ import annotations

import json
import re

from .workflow import resolve_step, value_faults, value_key

THRESHOLDS = ("at_least", "at_most", "share_at_least", "share_at_most")
#: A level whose verdict is null is the standard's own test for when no rating can be given: said so to a reader, and
#: `no-rating` in the id of its count. `webapp/rubicon/js/model.js` says it the same way.
NO_RATING, NO_RATING_ID = "No rating can be given", "no-rating"


def verdict_id(verdict) -> str:
    """A level's verdict as it goes in a count's id: lower case, words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", str(verdict).lower()).strip("-") if verdict is not None else NO_RATING_ID
COMBINE = ("weakest", "best", "separate")
#: How `check_rubric` ends the fault naming a step's proposed levels: a wait on the evaluator rather than a fault in
#: the workflow, which only their acceptance clears (`awaits_evaluator`).
AWAITING = "wait for the evaluator to accept them"
#: The model that makes a reading. Unmeasured against a cheaper one as yet.


def _quoted(quote: str, text: str) -> bool:
    """Whether the evaluator's words hold the quotation, allowing for elision, case, spacing and curly marks."""
    def norm(x):
        return re.sub(r"\s+", " ", x.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')).strip().lower()
    body = norm(text)
    return all(norm(p) in body for p in re.split(r"\s*(?:\.\.\.|\u2026)\s*", quote) if p.strip())


def awaits_evaluator(fault: str) -> bool:
    """Whether a fault `check` names is proposed levels waiting for the evaluator to accept them. Nobody but the
    evaluator can clear it, so it is kept from the repair round, which would otherwise clear it the one way open to a
    model: by relabelling the proposal as the evaluator's own standard."""
    return AWAITING in fault


def _numbers(text: str) -> set[float]:
    """The numerals a text holds, thousands separators dropped: "1,051" is 1051."""
    return {float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text)}


def find_stated(c: dict, background: dict[str, str]) -> tuple[object, list[str]]:
    """A stated criterion's quotation found in its background document, and what is wrong with it: a document that
    is not a background document, words the document does not hold, or numbers the found words do not contain."""
    from . import locator
    doc, quote = c.get("document"), str(c.get("quote") or "").strip()
    if doc not in background:
        return None, [f"names {doc!r}, which is not one of the background documents ({', '.join(background) or 'there are none'})"]
    if not quote:
        return None, ["quotes nothing of the document"]
    got = locator.locate_all(background[doc], [quote])[0]
    if got is None:
        return None, [f"quotes {quote[:80]!r}, which {doc} does not hold"]
    faults = []
    for k in ("n", "base"):
        v = c.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            faults.append(f"{k} is not a number: {v!r}")
        elif float(v) not in _numbers(got.quote):
            faults.append(f"{k} {v} is not among the numbers its quotation holds")
    if not faults and (c["base"] <= 0 or not 0 <= c["n"] <= c["base"]):
        faults.append(f"{c['n']} of {c['base']} is not a count out of a base")
    return got, faults


def _thresholds_faults(cid: str, levels: list[dict], most: int | float | None, of_what: str) -> list[str]:
    faults = []
    for i, lv in enumerate(levels):
        given = {k: lv[k] for k in THRESHOLDS if k in lv}
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in given.values()):
            faults.append(f"{cid}: level {lv.get('verdict')!r} has a threshold that is not a number: {given}")
        if not given and i < len(levels) - 1:
            faults.append(f"{cid}: only the last level may have no threshold")
        for k, v in given.items():
            if isinstance(v, (int, float)) and k.startswith("share") and not 0 <= v <= 1:
                faults.append(f"{cid}: {k} {v} is not a share between 0 and 1")
            if isinstance(v, (int, float)) and k == "at_least" and most is not None and v > most:
                faults.append(f"{cid}: at_least {v} is more than {of_what} ({most}), so no count could reach it")
    return faults


def scale(s: dict, c: dict) -> list:
    """The names a criterion's levels may give, best first: its own `scale` where the standard rates it on one, as most
    rubrics rate each criterion good, adequate or poor before a rule combines them, and otherwise the rubric's verdicts."""
    own = c.get("scale")
    return list(own) if isinstance(own, list) else [v.get("name") for v in s.get("verdicts") or [] if isinstance(v, dict)]


def standard_parts(s: dict):
    """Every part of a judge step's standard that says whose it is: each criterion's levels, as (criterion id, level),
    and each rule of a combine given as rules, as (None, rule). One list, for the check, the reader's account of whose
    the standard is and the evaluator's acceptance alike."""
    for c in s.get("criteria") or []:
        for lv in c.get("levels") or []:
            if isinstance(lv, dict):
                yield c.get("id"), lv
    if isinstance(s.get("combine"), list):
        for r in s["combine"]:
            if isinstance(r, dict):
                yield None, r


def _combine_faults(sid: str, s: dict, names: list, scales: dict) -> list[str]:
    """What stops a rubric's way of combining being applied: the weakest or the best needs every criterion on the
    rubric's own verdicts, since otherwise there is nothing to rank across; rules name the rubric's verdicts and
    criteria, with values on each criterion's scale, tried in order, only the last of them without a condition."""
    combine = s.get("combine", "weakest")
    if isinstance(combine, str):
        if combine not in COMBINE + ("all", "none"):
            return [f"{sid}: combine {combine!r}; it is weakest, best, separate, or a list of the evaluator's rules"]
        own = [str(c.get("id")) for c in s.get("criteria") or [] if c.get("scale") is not None]
        if own and combine != "separate":
            return [f"{sid}: combine {combine!r} ranks the criteria on the rubric's verdicts, but {', '.join(own)} "
                    "have scales of their own; give the evaluator's rules for combining them, or keep them separate"]
        return []
    if not isinstance(combine, list) or not combine:
        return [f"{sid}: combine {combine!r}; it is weakest, best, separate, or a list of the evaluator's rules"]
    faults = []
    for i, r in enumerate(combine):
        if not isinstance(r, dict):
            faults.append(f"{sid}: a combining rule {r!r} is not {{verdict, when}}")
            continue
        if r.get("verdict") not in names:
            faults.append(f"{sid}: a combining rule gives {r.get('verdict')!r}, which is not one of the rubric's verdicts")
        when = r.get("when")
        if when is None:
            if i < len(combine) - 1:
                faults.append(f"{sid}: only the last combining rule may have no condition")
            continue
        if not isinstance(when, dict) or not when:
            faults.append(f"{sid}: the combining rule for {r.get('verdict')!r} has a condition that is not {{criterion: level}}")
            continue
        for k, v in when.items():
            if k not in scales:
                faults.append(f"{sid}: the combining rule for {r.get('verdict')!r} names {k!r}, which is not a criterion")
                continue
            for x in (v if isinstance(v, list) else [v]):
                if x not in scales[k]:
                    faults.append(f"{sid}: the combining rule for {r.get('verdict')!r} asks for {k} {x!r}, which is not on its scale")
    return faults


def check_rubric(sid: str, s: dict, made: dict, attrs: set[str], n_documents: int | None, standard_text: str | None = None,
                 background: dict[str, str] | None = None, attribute_values: dict[str, list[str] | None] | None = None) -> list[str]:
    """Every fault in a judge step's rubric that would stop it being applied as written. Each level says whether the
    evaluator gave it, quoting their words (checked against `standard_text` where it is given), or the workflow
    proposes it; proposed levels wait until the evaluator accepts them (`accepted` on the step). A stated criterion is
    checked against `background`, the background documents' texts; without them it is refused, since a number nobody
    looked for in its document is not checked."""
    faults, proposed = [], []
    if not str(s.get("source") or "").strip():
        faults.append(f"{sid}: the rubric does not say whose standard it is")
    names = [v.get("name") for v in s.get("verdicts") or [] if isinstance(v, dict)]
    if len(names) < 2 or len(set(names)) != len(names):
        faults.append(f"{sid}: the rubric needs two or more verdicts with different names, best first")
    crits = s.get("criteria") or []
    if not crits:
        faults.append(f"{sid}: the rubric has no criteria")
    scales = {c.get("id"): scale(s, c) for c in crits}
    for c in crits:
        cid = f"{sid}.{c.get('id')}"
        if c.get("scale") is not None and (not isinstance(c["scale"], list) or len(c["scale"]) < 2
                                           or len(set(map(str, c["scale"]))) != len(c["scale"])):
            faults.append(f"{cid}: its scale needs two or more names, all different, best first")
        if not c.get("levels"):
            faults.append(f"{cid}: no levels")
        for lv in c.get("levels") or []:
            if lv.get("verdict") is None and c.get("kind") in ("rule", "stated"):
                continue  # the standard's own test for when no rating can be given
            if lv.get("verdict") not in scales[c.get("id")]:
                faults.append(f"{cid}: level {lv.get('verdict')!r} is not on its scale ({', '.join(map(str, scales[c.get('id')]))})")
    faults += _combine_faults(sid, s, names, scales)
    for crit, part in standard_parts(s):
        said = f"{sid}.{crit}: level {part.get('verdict')!r}" if crit else f"{sid}: the overall rule for {part.get('verdict')!r}"
        where = f"{crit} {part.get('verdict')!r}" if crit else f"the overall rule for {part.get('verdict')!r}"
        src, q = part.get("from"), str(part.get("quote") or "").strip()
        if src not in ("evaluator", "proposed"):
            faults.append(f"{said} does not say whether the evaluator gave it or it is proposed")
        elif src == "evaluator" and not q:
            faults.append(f"{said} is marked as the evaluator's but quotes nothing of theirs")
        elif src == "evaluator" and standard_text is not None and not _quoted(q, standard_text):
            faults.append(f"{said} quotes {q!r}, which is not in the evaluator's words")
        elif src == "proposed":
            proposed.append(where)
    for c in crits:
        cid = f"{sid}.{c.get('id')}"
        levels = c.get("levels") or []
        if c.get("kind") == "rule":
            t = c.get("table")
            if made.get(t, {}).get("kind") != "tabulate" or t not in (s.get("inputs") or []):
                faults.append(f"{cid}: a rule reads a tabulation among the step's inputs, not {t!r}")
            else:
                by = set(made[t].get("by") or [])
                picks = [("picks cells", c.get("where")), ("takes its base from cells", c.get("base_where"))]
                picks += [(f"level {lv.get('verdict')!r} picks cells", lv.get("where")) for lv in levels if "where" in lv]
                for said, w in picks:
                    if w is not None and not isinstance(w, dict):
                        faults.append(f"{cid}: {said} by {w!r}, which is not {{column: value}}")
                        continue
                    for k in (w or {}):
                        if k not in by:
                            faults.append(f"{cid}: {said} by {k!r}, which {t} does not count by")
                    faults += value_faults(f"{cid}: {said} by", w, made[t].get("values") or {})
            for k in (c.get("base") or {}):
                if k.lower() not in attrs:
                    faults.append(f"{cid}: its base names {k!r}, which the document list does not have")
            faults += value_faults(f"{cid}: its base names", c.get("base"), attribute_values or {})
            faults += _thresholds_faults(cid, levels, n_documents, "the documents there are")
        elif c.get("kind") == "stated":
            if background is None:
                faults.append(f"{cid}: a stated number cannot be checked here, since the check was not given the background documents")
            else:
                _, wrong = find_stated(c, background)
                faults += [f"{cid}: {w}" for w in wrong]
            base = c.get("base") if isinstance(c.get("base"), (int, float)) else None
            faults += _thresholds_faults(cid, levels, base, "the base the document states")
        elif c.get("kind") == "reading":
            r = c.get("rows_from")
            if made.get(r, {}).get("kind") not in ("code", "group") or r not in (s.get("inputs") or []):
                faults.append(f"{cid}: a reading reads a coding table among the step's inputs, not {r!r}")
            for lv in levels:
                if not str(lv.get("descriptor") or "").strip():
                    faults.append(f"{cid}: level {lv.get('verdict')!r} has no descriptor to read against")
        else:
            faults.append(f"{cid}: kind {c.get('kind')!r}; a criterion is a rule, a stated number or a reading")
        blanks = re.findall(r"_{3,}|\[\s*\]|\bTBD\b|\?\?\?", json.dumps(c))
        if blanks:
            faults.append(f"{cid}: has blanks left for somebody to fill ({', '.join(blanks)})")
    if proposed and not s.get("accepted"):
        faults.append(f"{sid}: these levels are proposed rather than the evaluator's, and {AWAITING}: "
                      + "; ".join(proposed))
    return faults


def _base(run, base: dict | None) -> list[str]:
    docs = sorted(run.corpus.documents)
    for k, v in (base or {}).items():
        allowed = {value_key(x) for x in (v if isinstance(v, list) else [v])}
        docs = [d for d in docs if value_key(run.attribute(d, k)) in allowed]
    return docs


def _cells(tab: dict, where: dict | None) -> tuple[set[str], list[str]]:
    """The documents, and the rows, in a tabulation's cells matching `where` ({column: value or list})."""
    want = {k: {value_key(x) for x in (v if isinstance(v, list) else [v])} for k, v in (where or {}).items()}
    docs, rows = set(), []
    for cell in tab["cells"]:
        if all(value_key(cell["values"].get(k)) in vs for k, vs in want.items()):
            docs |= set(cell["documents"])
            rows += cell["rows"]
    return docs, rows


def _rule(run, c: dict) -> dict:
    """A rule's levels tried in order, each on its own cells where it names them and otherwise the criterion's, every
    count tested kept, and the verdict, count and documents of the first level met."""
    tab = run.out[c["table"]]
    base = set(_base(run, c.get("base")))
    if c.get("base_where") is not None:
        base &= _cells(tab, c["base_where"])[0]
    tested, met = [], None
    for lv in c["levels"]:
        docs, rows = _cells(tab, lv.get("where", c.get("where")))
        hit = sorted(docs & base)
        got, _ = _level([lv], len(hit), len(base), "documents")
        tested.append({"verdict": lv["verdict"], "n": len(hit), "base": len(base), "met": got is not None,
                       "documents": hit, "rows": rows})
        if got:
            met = tested[-1]
            break
    use = met or tested[-1]
    said = "; ".join(f"{x['verdict'] or NO_RATING}: {x['n']} of {x['base']} documents, {'met' if x['met'] else 'not met'}" for x in tested)
    why = (f"the first level met is {met['verdict']} ({said})" if met and met["verdict"] is not None
           else f"not placed: the first level met says no rating can be given ({said})" if met else f"no level is met ({said})")
    return {"verdict": met["verdict"] if met else None, "n": use["n"], "base": use["base"], "documents": use["documents"],
            "rows": use["rows"], "why": why,
            "tested": [{k: x[k] for k in ("verdict", "n", "base", "met")} for x in tested]}


def level_counts(rec_id: str, c: dict) -> dict[str, dict]:
    """A rule's counts by the id an answer writes for each: the criterion's own (`{judge.reach}`, the level met), and
    where its levels were tested on cells of their own, each level's (`{judge.reach.good}`), so that a level not met
    can be stated too."""
    out = {f"{rec_id}.{c['id']}": {"n": c["n"], "base": c["base"]}}
    tested = c.get("tested") or []
    if len({(x["n"], x["base"]) for x in tested}) > 1:
        out.update({f"{rec_id}.{c['id']}.{verdict_id(x['verdict'])}": x for x in tested})
    return out


def _level(levels: list[dict], n: float, base: float, what: str) -> tuple[dict | None, str]:
    """The first level whose thresholds `n` out of `base` meets, and why, said as the verdict table says it."""
    share = n / base if base else 0.0
    for lv in levels:
        tests = [(k, lv[k]) for k in THRESHOLDS if k in lv]
        if all({"at_least": n >= v, "at_most": n <= v, "share_at_least": share >= v, "share_at_most": share <= v}[k] for k, v in tests):
            said = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in lv.items() if k in THRESHOLDS)
            return lv, f"{n:g} of {base:g} {what}; the first level met is {lv['verdict'] or NO_RATING}" + (f" ({said})" if said else "")
    return None, f"{n:g} of {base:g} {what} meet no level"


def _stated(run, c: dict) -> dict:
    """A number a background document states, found in it again at run time, against the levels."""
    got, wrong = find_stated(c, run.corpus.background_texts())
    if wrong:
        return {"verdict": None, "n": c.get("n"), "base": c.get("base"), "document": c.get("document"), "quote": c.get("quote"),
                "start": None, "end": None, "documents": [], "rows": [], "why": "not placed: " + "; ".join(wrong)}
    met, why = _level(c["levels"], c["n"], c["base"], f"as {c['document']} states it")
    return {"verdict": met["verdict"] if met else None, "n": c["n"], "base": c["base"], "document": c["document"],
            "quote": got.quote, "start": got.start, "end": got.end, "documents": [], "rows": [], "why": why}


def _reading(run, s: dict, c: dict) -> dict:
    where = {k: (set(map(str, v)) if isinstance(v, list) else {str(v)}) for k, v in (c.get("where") or {}).items()}
    rows = [r for r in run.table(c["rows_from"]) if all(str(r.get(k)) in vs for k, vs in where.items())]
    from . import guidance
    from .steps import parse_json, row_line
    listing = "\n".join(row_line(r) for r in rows)
    levels = "\n".join(f"- {lv['verdict']}: {lv['descriptor']}" for lv in c["levels"])
    fill = {"n_documents": str(len(run.corpus.documents)), "source": str(s["source"]), "question": run.question,
            "criterion": c["question"], "levels": levels, "rows": listing or "(none)"}
    prompt = re.sub(r"\{(" + "|".join(fill) + r")\}", lambda m: fill[m.group(1)], guidance.prompt_text("judge").rstrip("\n"))
    got = parse_json(run.ask(s["id"], prompt, s["model"], expect_json=True))
    ids = {r["row"] for r in rows}
    names = [lv["verdict"] for lv in c["levels"]]
    verdict = got.get("verdict") if got.get("verdict") in names else None
    between = [b for b in got.get("between") or [] if b in names] if got.get("verdict") == "between" else []
    return {"verdict": verdict, "between": between, "rows_read": len(rows), "rows": [x for x in got.get("rows", []) if x in ids],
            "against": [x for x in got.get("against", []) if x in ids],
            "rows_cited_that_do_not_exist": [x for x in got.get("rows", []) + got.get("against", []) if x not in ids],
            "why": got.get("why", "") if verdict else (f"between {' and '.join(between)}: " if between else "not placed: ") + got.get("why", "")}


def judge(run, s: dict) -> dict:
    s = resolve_step(s, "judge")
    order = [v["name"] for v in s["verdicts"]]
    results = []
    for c in s["criteria"]:
        got = _rule(run, c) if c["kind"] == "rule" else _stated(run, c) if c["kind"] == "stated" else _reading(run, s, c)
        # what a rule counts, as written, kept apart from `n` and `base`, which are its counts
        counted = {"counted": {k: c[k] for k in ("table", "where", "base", "base_where") if k in c}} if c["kind"] == "rule" else {}
        results.append({"id": c["id"], "question": c["question"], "kind": c["kind"], "levels": c["levels"],
                        **({"scale": c["scale"]} if c.get("scale") is not None else {}), **counted, **got})
    combine = s["combine"] if isinstance(s["combine"], list) else {"all": "weakest", "none": "weakest"}.get(s["combine"], s["combine"])
    if combine == "separate":
        overall, why = None, "the rubric keeps its criteria apart"
    else:
        overall, why = _by_rules(as_rules(combine, order, [c["id"] for c in s["criteria"]]), {r["id"]: r["verdict"] for r in results})
    return {"source": s["source"], "verdicts": s["verdicts"], "criteria": results, "combine": combine,
            "overall": overall, "overall_why": why, "accepted": s.get("accepted")}


def as_rules(combine, verdicts: list[str], criteria: list[str]) -> list[dict]:
    """A rubric's way of combining as rules, the one form the judge applies. The weakest is a rule a verdict, each
    holding where every criterion is at that verdict or better; the best is a rule a verdict and criterion, each
    holding where that criterion is at that verdict or better; the worst verdict is what is left. Rules given as rules
    are returned as they are."""
    if isinstance(combine, list):
        return combine
    rules = []
    for i, v in enumerate(verdicts[:-1]):
        at_least = verdicts[:i + 1]
        if combine == "weakest":
            rules.append({"verdict": v, "when": {c: at_least for c in criteria}})
        else:
            rules += [{"verdict": v, "when": {c: at_least}} for c in criteria]
    return rules + [{"verdict": verdicts[-1]}]


def _by_rules(rules: list[dict], got: dict) -> tuple[str | None, str]:
    """The overall verdict by the evaluator's rules, tried in order: the first whose every condition holds. A condition
    on a criterion that could not be placed is unknown, so a rule that would hold but for it might be the deciding one:
    the verdict is given only where every rule that might decide gives the same one, and is otherwise left open."""
    failed, maybe = {}, []  # criteria whose level kept a rule from holding; rules that hold but for an unknown
    decided, why = None, "no rule holds"
    for r in rules:
        when = r.get("when")
        if when is None:
            decided = r["verdict"]
            why = ("no earlier rule holds" + (" (" + "; ".join(f"{k} is {v}" for k, v in failed.items()) + ")" if failed else "")
                   + f", so {decided}")
            break
        unknown = [k for k in when if got.get(k) is None]
        holds = all(got.get(k) in (v if isinstance(v, list) else [v]) for k, v in when.items() if k not in unknown)
        if holds and unknown:
            maybe.append((r["verdict"], unknown))
            continue
        if holds:
            decided, why = r["verdict"], f"the rule for {r['verdict']} holds: " + "; ".join(f"{k} is {got[k]}" for k in when)
            break
        failed.update({k: got[k] for k, v in when.items() if k not in unknown and got[k] not in (v if isinstance(v, list) else [v])})
    open_ = [(v, u) for v, u in maybe if v != decided]
    if open_ or decided is None:
        turns = sorted({k for _, u in open_ for k in u})
        return None, ("no overall verdict: " + (f"it turns on {', '.join(turns)}, which could not be placed" if turns else why))
    return decided, why


def combine_in_words(combine) -> str:
    """How a rubric's criteria combine, said to a reader of the answer."""
    if not isinstance(combine, list):
        return COMBINE_IN_WORDS.get(combine, f"Criteria combined by the {combine}.")
    said = []
    for r in combine:
        when = r.get("when")
        cond = " and ".join(f"{k.replace('_', ' ')} is {' or '.join(map(str, v)) if isinstance(v, list) else v}"
                            for k, v in (when or {}).items())
        said.append(f"{r['verdict']} where {cond}" if when else f"otherwise {r['verdict']}")
    return "The overall verdict follows the evaluator's rules, the first that holds: " + "; ".join(said) + "."


#: How criteria combine, said to a reader of the answer.
COMBINE_IN_WORDS = {"weakest": "The overall verdict is the lowest any criterion reaches, so every criterion must hold.",
                    "best": "The overall verdict is the highest any criterion reaches.",
                    "separate": "Each criterion's verdict is reported on its own, without an overall verdict."}
#: What each kind of criterion is, said to a reader of the answer.
KIND_IN_WORDS = {"rule": "a count of documents, set against the thresholds below",
                 "stated": "a number a background document states, set against the thresholds below",
                 "reading": "judged by a language model reading the coded passages against each level's description"}


def accepted_in_words(accepted: str | None) -> str:
    """Who accepted proposed levels and when, said to a reader who saw none of the planning, with the date written out."""
    if not accepted:
        return ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", accepted)
    when = f" on {int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else ""
    return f"accepted for a test{when}" if accepted.startswith("for a test") else f"accepted by the evaluator{when}"


#: The planning assistant's name. A reader of the answer never meets her, so text the designer wrote about the
#: planning, printed with the standard, says what happened rather than who did it.
ASSISTANT = "Ruby"

#: Who the evaluator is, said once to a reader of the answer. The evaluator runs the analysis and reports to the
#: commissioner, who runs nothing; the commissioner is named only where the record says they set or agreed something.
EVALUATOR = "The evaluator is the person who ran this analysis and wrote the report."


def reader_words(text: str) -> str:
    """Text written during planning, such as a standard's source, as a reader of the answer reads it: the assistant not
    named. A quotation is left word for word."""
    def plain(t):
        t = re.sub(rf"\b(proposed|suggested|drafted|written|set|chosen|offered)\s+by\s+{ASSISTANT}\b", r"\1 during planning", t)
        t = re.sub(rf"\b{ASSISTANT}'s\s+", "the ", t)
        return re.sub(rf"\b{ASSISTANT}\b", "the planning", t)
    return "".join(p if i % 2 else plain(p) for i, p in enumerate(re.split(r'("[^"\n]*")', text)))


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _test(lv: dict, kind: str = "rule") -> str:
    """A level's test in words: its description, or its thresholds as counts and percentages, of documents for a count
    and of the stated base for a stated number."""
    if lv.get("descriptor"):
        return lv["descriptor"]
    said = []
    for k in THRESHOLDS:
        if k in lv:
            side = "at least" if k.endswith("least") else "at most"
            of, unit = ("the stated base", "") if kind == "stated" else ("the documents counted", " documents")
            said.append(f"{side} {lv[k] * 100:g}% of {of}" if k.startswith("share") else f"{side} {lv[k]:g}{unit}")
    return " and ".join(said) or "otherwise"


def provenance(rec: dict) -> str:
    """Whose levels the standard's are, in one sentence a reader of the answer can be given."""
    levels = [lv for _, lv in standard_parts(rec)]
    proposed = [lv for lv in levels if lv.get("from") != "evaluator"]
    if not proposed:
        return "Every level is from the standard as the evaluator gave it."
    return ((f"{len(proposed)} of the {len(levels)} levels {'was' if len(proposed) == 1 else 'were'}" if len(proposed) < len(levels)
             else "Every level was")
            + " proposed during planning, where the standard as given did not settle them"
            + (f", and {accepted_in_words(rec.get('accepted'))}, before any document was read." if rec.get("accepted")
               else ", and none has been accepted."))


def definitions(rec: dict, step_id: str, heading: str = "The standard") -> list[str]:
    """The standard as the workflow applied it, under its own heading, each level marked with whose it is, for a reader
    who saw none of the planning: what a standard is, where this one comes from, how its criteria combine, and each
    level's test."""
    out = [f"### {heading}", "",
           f"A standard is the rule for judging the evidence, set before any document was read. {EVALUATOR} "
           f"Where this one comes from: {reader_words(str(rec['source']).strip().rstrip('.'))}. "
           "Verdicts, best first: "
           + "; ".join(f"{v['name']} ({reader_words(str(v.get('means', '')).strip().rstrip('.'))})" for v in rec["verdicts"]) + ". "
           + (combine_in_words(rec["combine"]) if not isinstance(rec["combine"], list)
              else "The overall verdict follows the evaluator's rules, listed last, the first that holds deciding.")
           + " " + provenance(rec), ""]

    def whose(part):
        return (f"as given in the question: \"{part.get('quote')}\"" if part.get("from") == "evaluator"
                else "proposed during planning" + (f", {accepted_in_words(rec['accepted'])}" if rec.get("accepted") else ", not accepted"))
    for r in rec["criteria"]:
        name = r['id'].replace('_', ' ')
        out.append(f"- **{name[:1].upper() + name[1:]}**, {KIND_IN_WORDS.get(r['kind'], r['kind'])}: {reader_words(r['question'])}"
                   + (f" Rated {', '.join(map(str, r['scale']))}, best first." if r.get("scale") else "")
                   + (f" The number, as the background document {r['document']} states it: \"{r['quote']}\""
                      if r["kind"] == "stated" and r.get("quote") else "")
                   + (f" {counted_in_words(r['counted'])}" if r.get("counted") else ""))
        for lv in r.get("levels") or []:
            cells = f", counting documents coded {_cells_in_words(lv['where'])}" if lv.get("where") is not None else ""
            out.append(f"    - {lv['verdict'] or NO_RATING}: {reader_words(_test(lv, r['kind']))}{cells} ({whose(lv)})")
    if isinstance(rec["combine"], list):
        out.append("- **Overall**, the evaluator's rules for combining the criteria, tried in order:")
        for rule in rec["combine"]:
            when = rule.get("when")
            cond = " and ".join(f"{k.replace('_', ' ')} is {' or '.join(map(str, v)) if isinstance(v, list) else v}"
                                for k, v in (when or {}).items())
            out.append(f"    - {rule['verdict']}: {'where ' + cond if when else 'otherwise'} ({whose(rule)})")
    return out


def _cells_in_words(where: dict | None) -> str:
    said = [f"{k} {' or '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in (where or {}).items()]
    return " and ".join(said) or "anything"


def counted_in_words(r: dict) -> str:
    """What a rule counts and what out of, for a reader of the standard: the cells it counts and its base, both by
    document attribute and by the coding. `r` is the rule as written (a result's `counted`)."""
    of = [f"whose {k} is {' or '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in (r.get("base") or {}).items()]
    if r.get("base_where") is not None:
        of.append(f"coded {_cells_in_words(r['base_where'])}")
    counts = f"It counts documents coded {_cells_in_words(r['where'])}" if r.get("where") else "It counts documents"
    return counts + (", out of the documents " + " and ".join(of) if of else ", out of all the documents") + "."


def markdown(rec: dict) -> str:
    """The verdict table the write step is given, to put beside the verdict."""
    lines = [f"Standard: {reader_words(str(rec['source']))}. Verdicts, best first: " + "; ".join(f"{v['name']} ({v.get('means', '')})" for v in rec["verdicts"]),
             f"Whose levels: {provenance(rec)}",
             "| Criterion | Kind | Verdict | Evidence |", "|---|---|---|---|"]
    for r in rec["criteria"]:
        cid = f"{rec.get('id', 'judge')}.{r['id']}"
        ev = ("; ".join(f"{{{k}}} documents ({x['n']} of {x['base']})" for k, x in level_counts(rec.get('id', 'judge'), r).items())
              if r["kind"] == "rule"
              else f"{{{cid}}} ({r['n']} of {r['base']}), as \"{r['quote']}\" [{r['document']}]" if r["kind"] == "stated"
              else f"rows {', '.join(r['rows'])}; against {', '.join(r['against']) or 'none'}")
        placed = r["verdict"] or (f"between {' and '.join(r['between'])}, for the evaluator" if r.get("between") else "not placed")
        lines.append(f"| {r['id']}: {r['question']} | {r['kind']} | {placed} | {ev}. {r['why']} |")
    lines.append(f"Overall: {rec['overall'] or 'no verdict'}; {rec['overall_why']}. {combine_in_words(rec['combine'])}")
    return "\n".join(lines)
