"""What Rubicon's main plugin tells Causal Map about a run, once a conversation after a hand-over: the keys of the one
address it fetches, and the fixed set of values each key may take.

`usage.py` works each value out from the run's own files by fixed rules, and the relay that receives the address
(`rubicon/usage-relay/` in Rubicon's own repo) passes on only an address that `check` accepts, so nothing outside these
sets travels further. The database function that stores the row checks the same sets again
(`supabase/migrations/20261114180000_rubicon_plugin_runs.sql`), and a test holds the three level.

- `v`: the engine's version, as a build stamps it;
- `e`: what was just handed over (`EVENTS`);
- `m`: the model family, one lowercase word as the skill names it, since this engine names no model;
- `run`: a random code the run keeps among its working files and never shows a reader, the same for every hand-over
  of one run, so a run's report and its revisions are counted as one run, and no row can be matched to a report;
- `docs`, `words`: how many documents were read and about how many words they hold, in bands;
- `q`: how many questions the run answered, exactly;
- `taken`: how the questions were taken (`TAKEN`);
- one key for each kind of step (`KINDS`): how many steps of that kind the workflow has, exactly;
- `passages`: how many passages the coding steps coded, in bands;
- `second`: the second reading (`SECOND`);
- `minutes`: from the run's first agreement to this hand-over, in bands;
- `tied`: the share of the answer's sentences that the recount read for a tie to the passages and found tied, in bands.
"""
from __future__ import annotations

import re

from .workflow import KINDS

EVENTS = ("report", "revision", "combined")
#: One question; several in one run; a run for each question; or a shared reading first, then a run for each question
TAKEN = ("single", "together", "one-at-a-time", "shared-first")
#: No second reading; a check of the coding; a second coding to the same definitions; or, across a combined report's
#: runs, more than one of these
SECOND = ("none", "check", "recode", "mixed")
#: A model family as the skill names it: one lowercase word, so nothing else can travel in its place
FAMILY = re.compile(r"[a-z]{1,12}")
#: The version a build stamps: the release, then the first twelve characters of the commit it was built from
VERSION = re.compile(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,4}\+[0-9a-f]{12}")
#: The run's code, or `none` for a combined report of no run
RUN = re.compile(r"[0-9a-f]{16}|none")
#: Exact counts, of questions and of steps of each kind, capped at 99
COUNT = re.compile(r"[0-9]{1,2}")
CAP = 99
#: Each banded key: (upper bound of the band, its name), lowest first; above the last bound, the last name
BANDS = {"docs": ((1, "1"), (5, "2-5"), (10, "6-10"), (25, "11-25"), (50, "26-50"), (100, "51-100"), (250, "101-250"),
                  (None, "over-250")),
         "words": ((4_999, "under-5k"), (19_999, "5k-20k"), (49_999, "20k-50k"), (149_999, "50k-150k"),
                   (499_999, "150k-500k"), (None, "over-500k")),
         "passages": ((0, "0"), (10, "1-10"), (50, "11-50"), (200, "51-200"), (1_000, "201-1000"), (5_000, "1001-5000"),
                      (None, "over-5000")),
         "minutes": ((9, "under-10"), (29, "10-30"), (59, "30-60"), (119, "60-120"), (239, "120-240"), (479, "240-480"),
                     (None, "over-480")),
         # a whole percentage, rounded down, so only an answer with every sentence tied is 100
         "tied": ((49, "under-50"), (79, "50-79"), (89, "80-89"), (99, "90-99"), (None, "100"))}
#: The value a banded key takes where the run's files cannot say
UNKNOWN = {"passages": "unknown", "minutes": "unknown", "tied": "none"}
#: The address's keys, in order, and nothing else
OUTLINE = ("v", "e", "m", "run", "docs", "words", "q", "taken", *KINDS, "passages", "second", "minutes", "tied")


def band(key: str, n: int) -> str:
    for top, name in BANDS[key]:
        if top is None or n <= top:
            return name
    raise AssertionError(key)


def values(key: str) -> tuple[str, ...] | None:
    """The fixed set a key takes, or None for a key checked by its pattern instead."""
    if key in BANDS:
        return tuple(([UNKNOWN[key]] if key in UNKNOWN else []) + [name for _, name in BANDS[key]])
    return {"e": EVENTS, "taken": TAKEN, "second": SECOND}.get(key)


def allowed(key: str, value: str) -> bool:
    fixed = values(key)
    if fixed is not None:
        return value in fixed
    pattern = {"v": VERSION, "m": FAMILY, "run": RUN}.get(key, COUNT if key == "q" or key in KINDS else None)
    return pattern is not None and pattern.fullmatch(value) is not None


def check(pairs) -> dict[str, str] | None:
    """The address's values as one dict where it holds every key of `OUTLINE` once, each with a value from its set;
    otherwise None, and nothing of it should go further."""
    pairs = list(pairs or ())
    keys = [k for k, _ in pairs]
    if sorted(keys) != sorted(OUTLINE):
        return None
    got = dict(pairs)
    return got if all(isinstance(v, str) and allowed(k, v) for k, v in got.items()) else None
