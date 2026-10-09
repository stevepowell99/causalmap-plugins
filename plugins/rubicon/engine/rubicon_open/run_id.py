"""A run's ID: the date it was made and four characters, such as `2026-10-09-k7q2`.

Minted once, when the run's folder is made, named in the folder and recorded in `workflow.json` as `run_id`, so the
folder, the report, the Word copy and the zip are matched by it. It stays the same through every revision of the run,
whereas the zip's fingerprint changes with each version and names that version alone. A run made before IDs existed
has none, and nothing is drawn for it.
"""
from __future__ import annotations

import datetime
import re
import secrets

#: Letters and digits that cannot be mistaken for each other when read aloud or copied by eye.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
ID = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9]{4}")


def new_run_id(today: datetime.date | None = None) -> str:
    return f"{(today or datetime.date.today()).isoformat()}-" + "".join(secrets.choice(ALPHABET) for _ in range(4))


def clean(value) -> str:
    """The ID as recorded, or an empty string where the run has none or what it holds is not an ID, so that nothing
    unlike an ID is ever drawn as one."""
    value = str(value or "").strip()
    return value if ID.fullmatch(value) else ""
