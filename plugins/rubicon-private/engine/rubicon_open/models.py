"""Which model does which job by default, where a step names none, and the thinking each family runs at. The engine
is published without any: a step it resolves names no model unless the workflow gives one, which is right for coding
done by the analyst. A harness that runs models sets these names when it loads (Rubicon's own does, in
`rubicon/__init__.py`). Callers read them here when they resolve a step (`from . import models as C`, then `C.CODER`),
so a harness that sets them after the engine has loaded is still heard."""
from __future__ import annotations

CODER = GROUPER = ASSIGNER = WRITER = REVIEWER = REPAIRER = JUDGE = None
SECOND_CODER = ADJUDICATOR = None
ADJUDICATOR_THINKING = SECOND_RETRY_THINKING = None
#: What each write call reads at most, in tokens.
WRITER_READING_TOKENS = 200_000
THINKING: dict = {}
GROUP_THINKING: dict = {}


def thinking_for(model: str | None, thinking: str | None = None) -> str | None:
    """The thinking level a call to `model` runs at: the one given, or its family's default."""
    return thinking or next((v for k, v in THINKING.items() if model and model.startswith(k)), None)
