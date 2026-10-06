"""Where the engine reaches for text it does not carry: the prompts a model is asked with, and the pages of practice
notes and method pages a step may read. The engine is published without them, so a harness that has them sets these
three names when it loads (Rubicon's own does, in `rubicon/pieces/steps.py`); without them, a step reads no pages and
no step that asks a model can run.

Callers look each one up here when they call it (`guidance.prompt_text(...)`, never `from .guidance import ...`), so a
harness that sets them after the engine has loaded is still heard."""
from __future__ import annotations


def notes_for(piece: str) -> list[str]:
    """The practice notes a piece reads by default: none, where no harness has given the engine any."""
    return []


def page_names() -> set[str] | None:
    """Every page a step may be given by name, or None where no harness has given the engine any pages, in which case
    a step's list of pages is not checked against them."""
    return None


def prompt_text(name: str, notes: list[str] | str = "all") -> str:
    """The prompt `name`, with the pages `notes` names where it asks for them."""
    raise RuntimeError(f"the {name!r} step asks a model, and this engine carries no prompts: it recounts coding done "
                       f"elsewhere, and runs no step that needs a model")
