"""The two third-party assets a report needs to look and draw as designed, carried inside the report so that a single
file opens on a network that reaches nothing: the typefaces and Graphviz (Viz.js).

They live in `rubicon/open/rubicon_open/vendor/`, each with its licence, at the version and hash `vendor/README.md` records; a test
holds the hash. A report asks for the font faces (`fonts_css`) and, where it has a map, the Graphviz script
(`graphviz_script`), and writes them into the page. Nothing here fetches anything.
"""
import base64
import re
from functools import lru_cache
from pathlib import Path

from rubicon_open.corpus import as_read

VENDOR = Path(__file__).resolve().with_name("vendor")


@lru_cache(maxsize=None)
def fonts_css():
    """The @font-face rules of `vendor/fonts/fonts.css`, each file it names written in as a data URI."""
    folder = VENDOR / "fonts"
    css = as_read((folder / "fonts.css").read_text(encoding="utf-8"))
    return re.sub(r"url\(([\w.-]+\.woff2)\)",
                  lambda m: "url(data:font/woff2;base64," + base64.b64encode((folder / m.group(1)).read_bytes()).decode("ascii") + ")",
                  css)


@lru_cache(maxsize=None)
def graphviz_script():
    """Graphviz as a script element: Viz.js's own distribution file, with its WebAssembly inside it, so it needs no
    second file and no address. Line endings are made one newline (`as_read`) so a Windows checkout and any other give
    the same report; the file holds no `</script` or `<!--`, which `vendor/README.md` says and a test checks."""
    return "<script>" + as_read((VENDOR / "graphviz" / "viz-global.js").read_text(encoding="utf-8")) + "</script>"
