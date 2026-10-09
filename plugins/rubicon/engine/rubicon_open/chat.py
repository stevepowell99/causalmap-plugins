"""Which chat produced a run, as the environment of the chat that recounted it names it.

`recount.py` writes it into `run.json` as `chat`, once: a later recount of the same run, from another chat, leaves the
first chat's entry as it was. It is a note for whoever made the run, to find the conversation again; it is never a key,
since the run is matched by its `run_id` and the zip's fingerprint, and a run recounted where no chat names itself
(a test, a script) has no entry.

What each environment says, as measured: Claude Code in a terminal names `CLAUDE_CODE_SESSION_ID`, and `claude --resume
<id>` reopens it; a Claude Code session on the web also names `CLAUDE_CODE_BRIDGE_SESSION_ID`, and
`https://claude.ai/code/<that id>` was opened in a browser and showed the session; Cowork names
`CLAUDE_CODE_REMOTE_SESSION_ID` (`cse_<rest>`) and `CLAUDE_CODE_ENTRYPOINT=remote_cowork`, and
`https://claude.ai/code/session_<rest>` was clicked by its owner and opened that Cowork chat. A link is written only
for the kind of ID whose link has been shown to open (`LINKED`); add another kind there once it has.
Earlier chats cannot be opened from inside a chat (Cowork has only memory notes, and a Code session no tool for it),
so this link is the only way back to the chat a run came from.
"""
import os
import re

#: Each field of the entry, the variable it is read from, and the shape a value must have to be written: a value of any
#: other shape is left out, so nothing a variable happens to hold is carried into a zip someone else will read.
FIELDS = {
    "entrypoint": ("CLAUDE_CODE_ENTRYPOINT", re.compile(r"[a-z][a-z0-9_]{1,31}")),
    "session_id": ("CLAUDE_CODE_SESSION_ID", re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")),
    "remote_session_id": ("CLAUDE_CODE_REMOTE_SESSION_ID", re.compile(r"cse_[A-Za-z0-9]{8,64}")),
    "bridge_session_id": ("CLAUDE_CODE_BRIDGE_SESSION_ID", re.compile(r"session_[A-Za-z0-9]{8,64}")),
}
#: The kinds of ID whose link has been opened in a browser and shown the chat, and how each becomes that link.
LINKED = {"bridge_session_id": lambda v: f"https://claude.ai/code/{v}",
          "remote_session_id": lambda v: f"https://claude.ai/code/session_{v.removeprefix('cse_')}"}


def chat_from_env(env=None) -> dict:
    """The entry for the chat this process runs in: every ID the environment names that has the shape of one, the
    entrypoint beside them, and the link of the first kind of ID that has one. Empty where no ID is named."""
    env = os.environ if env is None else env
    found = {key: env[var].strip() for key, (var, shape) in FIELDS.items()
             if env.get(var) and shape.fullmatch(env[var].strip())}
    if not any(k.endswith("session_id") for k in found):
        return {}
    for key, link in LINKED.items():
        if key in found:
            found.setdefault("url", link(found[key]))
    return found
