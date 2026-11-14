"""How a speaker stands to what a reading recorded: one list, for mentions and cells alike.

A mention's status says how the case stands to what its passage recorded. A cell's status is
the first of this list that applies to its case and item, and its `also` holds every other one
that applies too, so nothing true of the case is lost to the order: a count naming any of its
statuses finds it. A cell
made from mentions takes the strongest of them as its status and the rest as `also`. The order
is the one a reader takes the first that applies in, and what "strongest" means
(`guidance/record-format.md` tells the readers).

`near_miss` is the speaker speaking, from their own experience, of something the item's
definition lists under `does_not_count`. It is tied to the one item it nearly is, so a strict
number never reads it and a broad number names it.
"""
from __future__ import annotations

#: The statuses a reader gives, strongest first.
ORDER = ("first_hand", "prompted", "denied", "about_others", "hypothetical", "wish",
         "near_miss", "mentioned", "dont_know", "not_raised")

#: What each means, as a reader is told it.
MEANS = {
    "first_hand": "the speaker's own experience, view or action of what is recorded, as its "
                  "definition has it",
    "prompted": "only agreeing with the interviewer's own suggestion, adding nothing of their own",
    "denied": "the speaker says it did not happen to them or does not apply to them",
    "about_others": "what the speaker does not vouch for: other people's experience, or another "
                    "party's claim passed on as theirs",
    "hypothetical": "only a guess or a conditional about what might happen",
    "wish": "only a suggestion, a recommendation or a wish for how it should be",
    "near_miss": "the speaker's own experience of something the definition lists as not "
                 "counting: close to it, and not it",
    "mentioned": "spoken of from the speaker's own experience without saying it helped or "
                 "hindered, or only in passing",
    "dont_know": "the speaker says they do not know, or has only a vague or second-hand "
                 "impression",
    "not_raised": "the case does not speak to it as defined",
}

#: Set by the code, never given by a reader, never counted and never a zero.
UNPLACED, NOT_READ = "unplaced", "not_read"
BY_THE_CODE = (UNPLACED, NOT_READ)

#: What a number reads unless it says otherwise.
STRICT = ("first_hand",)

#: Every status a reader may give, and every status a record may hold.
READER = ORDER
ALL = ORDER + BY_THE_CODE
#: What `status: any` reads: every way of speaking to a thing, and none of the silences. A
#: cell recorded as not raised, or one the reader never answered, is not a case raising it,
#: and counting it would make a number of cases that raised an item equal to its base.
SILENCES = ("not_raised", *BY_THE_CODE)
ANY = tuple(s for s in ALL if s not in SILENCES)

_RANK = {s: i for i, s in enumerate(ALL)}


def rank(status: str | None) -> int:
    """Where a status stands, strongest first; anything unknown stands after all of them."""
    return _RANK.get(status, len(ALL))


def strongest(statuses) -> str | None:
    """The strongest of several statuses, or None where there are none."""
    held = [s for s in statuses if s is not None]
    return min(held, key=rank) if held else None


def arrange(status, also=()) -> tuple[str | None, list[str]]:
    """A status and the others that also apply, put in order: the strongest is the status and
    the rest, strongest first and each once, are `also`. A silence is dropped once anything is
    said, and an unknown name is kept for the record's check to report."""
    held = [s for s in [status, *(also or [])] if s is not None]
    spoken = [s for s in held if s not in SILENCES]
    held = spoken or held
    ordered = sorted(dict.fromkeys(held), key=rank)
    return (ordered[0], ordered[1:]) if ordered else (None, [])


def of_cell(cell: dict) -> tuple[str, ...]:
    """Every status a cell holds: its status and its `also`."""
    return tuple(s for s in [cell.get("status"), *(cell.get("also") or [])] if s is not None)


def named(want) -> tuple[str, ...]:
    """The statuses a number names, as a tuple: one, several, or `any` for all of them.

    An unknown name is refused rather than read as matching nothing, since a misspelt
    status would otherwise turn a count into a silent nought."""
    if want in (None, ""):
        return STRICT
    if want == "any":
        return ANY
    want = [want] if isinstance(want, str) else list(want)
    unknown = [s for s in want if s not in _RANK]
    if unknown:
        raise ValueError(f"{unknown} is not a status. The statuses are {list(ALL)}, or `any`.")
    return tuple(want)
