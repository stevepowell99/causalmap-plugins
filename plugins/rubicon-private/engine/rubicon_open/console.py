"""How an engine script writes to the console it is run from."""
from __future__ import annotations

import sys


def utf8() -> None:
    """Both output streams in UTF-8, whatever the console's code page. The scripts print document ids, arrows and
    quotation marks, and a refusal goes out on stderr through `sys.exit`, so a stream left in a Windows code page
    writes bytes that a reader expecting UTF-8 cannot decode. Every entry script calls this before it prints."""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
