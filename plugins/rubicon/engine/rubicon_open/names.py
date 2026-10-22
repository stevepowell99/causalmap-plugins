"""How a report names a step, a column or a value to its reader: the one place a workflow's ids become words.

A workflow's ids (`c_pay`, `t_conc_size`, `k`) are keys for the code that counts, never words for the reader, so
wherever the report, its Word copy, the side panel or the procedure meets a step it asks `step_name`, which takes the
name from what the workflow already says:

- a code step is named for its id without the prefix that marks its kind (`c_concern` is "Concern"), or for its first
  column where that leaves fewer than three letters,
- a tabulation for the step it counts and the columns it counts by ("Concern by size"), or for its `description` where it
  reads no step; the description is shown beneath the heading as the paragraph it is,
- a grouping for the step it groups where its own id is a single letter,
- the claims step "Key claims",
- any other step for its id without the one-letter prefix (`j_welfare` is "Welfare") that marks its kind.

A column or a value is named by `label`: underscores as spaces and a first capital. `in_words` does the same for the
ids inside text a model wrote (a claim's `found_by`), and touches nothing else in the sentence.
"""
import re

#: What each kind of step is called where a reader meets it, in the annex's headings and the side panel's step buttons
KIND_SAID = {"code": "Coding", "profile": "Profiling", "tabulate": "Counting", "judge": "Judging", "claims": "Tagging claims",
             "write": "Writing", "sample": "Sampling",
             "group": "Grouping", "recode": "Second coding", "check": "Checking"}


def label(v):
    """A value as a reader sees it: underscores as spaces and the first letter capitalised, the rest left as coded, so
    an acronym such as AI keeps its capitals. A factor's opposite pole keeps its leading ~, as Causal Map writes it
    ("~Hygiene and sanitation"); `named` marks the ~ in a page (report.js `label` and `named` say the same). The leading
    # Causal Map's export puts on a document's column ("#Age of the main respondent") is dropped, being a mark of where
    the column came from."""
    s = str(v).replace("_", " ").strip().removeprefix("#").strip()
    pole = s.startswith("~")
    s = s[1:].strip() if pole else s
    return ("~" if pole else "") + s[:1].upper() + s[1:]


def lowered(name):
    """A name for the middle of a sentence: its first letter lowered unless it opens with an acronym."""
    return name if name[:2].isupper() else name[:1].lower() + name[1:]


def made_of(made, name):
    """What a step made, as a reader sees it: "rows of label", or the step's own name where that already says what it
    made ("Answer", "Key claims"), rather than "answer of answer"."""
    return name if made.lower() in lowered(name).lower().split() else f"{made} of {lowered(name)}"


def bare(sid):
    """A step's id as words, without the one-letter prefix its id may carry for its kind (c_, t_, j_)."""
    return label(re.sub(r"^[a-z]_", "", str(sid)))


def inputs_of(st):
    """The steps a workflow step reads."""
    return list(st.get("inputs") or ([st["input"]] if st.get("input") else []))


def step_name(sid, specs, _via=()):
    """A step's name as a reader sees it, from what the workflow says of it. `specs` is {step id: step} for the
    workflow; a step it does not hold is named for its id."""
    st = specs.get(sid) or {}
    kind = st.get("kind", "")
    if kind == "claims":
        return "Key claims"
    cols = [c["name"] for c in st.get("columns") or [] if isinstance(c, dict) and c.get("name")]
    if kind == "code" and cols and len(bare(sid)) < 3:
        return label(cols[0])
    reads = [i for i in inputs_of(st) if i in specs and i not in _via and i != sid]
    if kind == "tabulate":
        of = step_name(reads[0], specs, _via + (sid,)) if reads else ""
        said = str(st.get("description") or "").strip().rstrip(".").strip()
        if said and not of:
            return label(said)
        by = " and ".join(label(b).lower() for b in st.get("by") or [] if label(b).lower() != of.lower())
        # the rows it keeps, so two counts of one coding by the same columns are told apart ("… (barrier, own)")
        where = st.get("where") if isinstance(st.get("where"), dict) else {}
        kept = ", ".join(" or ".join(lowered(label(x)) for x in (v if isinstance(v, list) else [v])) for v in where.values())
        named = label(" by ".join(x for x in (of, by) if x)) if of or by else bare(sid)
        return f"{named} ({kept})" if kept else named
    if kind == "group" and len(bare(sid)) < 2 and len(reads) == 1:
        return step_name(reads[0], specs, _via + (sid,))
    return bare(sid)


def step_said(sid, specs):
    """A step as an annex heading and the side panel's step buttons give it: its kind in words, then its name."""
    kind = (specs.get(sid) or {}).get("kind", "")
    if kind == "claims":
        return step_name(sid, specs)
    return f"{KIND_SAID.get(kind, label(kind))}: {step_name(sid, specs)}" if kind else step_name(sid, specs)


def specs_of(workflow):
    """{step id: step} for a workflow."""
    return {st["id"]: st for st in (workflow or {}).get("steps", []) if isinstance(st, dict) and st.get("id")}


def in_words(text, specs):
    """Text a model wrote with the workflow's ids in it, with each id given the name a reader sees and the rest of the
    sentence left as written. Only an id holding an underscore is read as one, since another is an ordinary word; a
    row's id (`c_pay.jcxkf`) is left alone. A step id followed by one of its own columns ("c_pay payment") becomes the
    column alone, since the step is named for its column."""
    text = str(text or "")
    ids = sorted((i for i in specs if "_" in i), key=len, reverse=True)
    if ids:
        step = re.compile(r"(?<![\w.{])("+ "|".join(map(re.escape, ids)) + r")(?!\w)(?!\.\w)(?:(\s+)(\w+))?")

        def one(m):
            sid, gap, word = m.group(1), m.group(2), m.group(3)
            own = {c.get("name") for c in specs[sid].get("columns") or [] if isinstance(c, dict)}
            if word in own:
                return lowered(label(word))
            return lowered(step_name(sid, specs)) + (gap + word if word else "")
        text = step.sub(one, text)
    cols = sorted({c["name"] for st in specs.values() for c in st.get("columns") or [] if isinstance(c, dict) and "_" in c.get("name", "")},
                  key=len, reverse=True)
    if cols:
        text = re.sub(r"(?<![\w.{\[])("+ "|".join(map(re.escape, cols)) + r")(?!\w)", lambda m: lowered(label(m.group(1))), text)
    return text
