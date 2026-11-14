"""Reading an answer in any language: its quotations, its sentences and its words, by Unicode's classes of character
rather than by any one language's (`rubicon/CLAUDE.md`, "Quality levers never depend on English").

    quotations   every pair of double quotation marks or corner brackets in use, so « », „ “, ” ”, 「 」 and " " alike
    sentences    split after any script's sentence-ending mark, before anything but a lowercase letter, and with no
                 space needed after a full-width mark; a sentence's size counted in letters and digits, not in words
    words        runs of letters, digits and the combining marks that belong to them, so a Devanagari or Thai word is
                 one word and not a run of pieces

Every check that pairs quotation marks, splits sentences or reads words takes them from here, so a fix to one is a fix
to all of them.
"""
from __future__ import annotations

import re
import unicodedata
from functools import cache

#: Each opening double quotation mark, with the marks that close it, as the world's writing pairs them. A mark that
#: opens in one convention and closes in another (“, ”, », «) is read as opening only where no quotation is open, so
#: pairing left to right finds each quotation once. Single marks (' ‘ ’ ‚ ‹ ›) are left out: the same characters are
#: apostrophes, and an apostrophe taken for a quotation mark would pair half the answer.
QUOTE_PAIRS = {
    '"': '"',
    "“": "”",
    "„": "“”",
    "”": "”",
    "«": "»",
    "»": "«",
    "「": "」",
    "『": "』",
    "﹁": "﹂",
    "﹃": "﹄",
    "〝": "〞〟",
    "＂": "＂",
}
#: Every quotation, its marks and what they enclose, on one line; group n + 1 holds the words inside the nth pair.
QUOTATION = re.compile("|".join(f"{re.escape(o)}([^{re.escape(c)}\n]*)[{re.escape(c)}]" for o, c in QUOTE_PAIRS.items()))
#: Any mark that opens or closes a quotation.
QUOTE_MARKS = "".join(sorted(set("".join(QUOTE_PAIRS) + "".join(QUOTE_PAIRS.values()))))


def quotation_spans(text: str) -> list[tuple[int, int, int, int]]:
    """Where each quotation stands, as (start, end) of the whole with its marks, then (start, end) of the words between
    them, pairing marks from left to right."""
    return [(m.start(), m.end(), m.start(m.lastindex), m.end(m.lastindex)) for m in QUOTATION.finditer(text)]


def width(s: str) -> int:
    """How long a string is for a floor on length: its characters, a wide one (`_wide`, as in Chinese, Japanese and
    Korean, where one character holds about as much as a short word) counting two, so a floor set on Latin text drops
    no more of a quotation in those scripts than it does in English."""
    return sum(2 if _wide(ch) else 1 for ch in s)


def quotations(text: str, shortest: int = 12) -> list[str]:
    """The words of each quotation `shortest` or more wide (`width`), without the spaces some conventions put inside
    the marks. The marks are paired left to right whatever the length between them, and the short ones dropped
    afterwards: requiring the length while pairing took the closing mark of a short quotation ("Improved",
    "Increased") for an opening one."""
    return [q for *_, a, b in quotation_spans(text) if width(q := text[a:b].strip()) >= shortest]


def without_quotations(text: str, fill: str = " ") -> str:
    """`text` with each quotation, its marks included, replaced by `fill`."""
    return QUOTATION.sub(fill, text)


def cited_quotations(text: str, shortest: int = 4) -> list[dict]:
    """Each quotation followed by a citation in square brackets, as `"words" [document id]` writes one: its words
    (`quote`), what the brackets hold (`ref`), where the quotation and its citation stand together (`span`) and where
    the brackets' contents stand (`ref_span`)."""
    out = []
    for start, end, a, b in quotation_spans(text):
        m = re.compile(r"\s*\[([^\]\n]+)\]").match(text, end)
        if m and width(text[a:b].strip()) >= shortest:
            out.append({"quote": text[a:b].strip(), "ref": m.group(1), "span": (start, m.end()), "ref_span": m.span(1)})
    return out


#: The marks that end a sentence, in the scripts that mark one: Unicode's full stops, question and exclamation marks
#: and dandas, by their names (inverted marks, which open a sentence, left out), and the Myanmar and Khmer signs Unicode
#: lists among its sentence terminals under other names. Thai and other scripts that end a sentence with a space have
#: none, so their sentences run to the end of the line.
TERMINALS = ("!.?;։؞؟۔܁܂߹।॥။።፧᙮᠃᠉។៕᥄᥅‼‽⁇⁈⁉⳹⳺⳻⳾⸼⹓⹔。꓿꘎꘏꛳꛷꣎꣏꩝꩞꩟︒︕︖﹒﹖﹗！．？｡"
             "𐩖𐩗𑁇𑁈𑃀𑃁𑅁𑅂𑅃𑇅𑇆𑈸𑈹𑑋𑑌𑗂𑗃𑙁𑙂𑥄𑱁𑱂𑽃𑽄𖩮𖩯𖫵𖺘𛲟𝪈")


#: The sentence-ending marks that ask a question, in any script: those Unicode names as question marks.
QUESTION_MARKS = "".join(ch for ch in TERMINALS if "QUESTION" in unicodedata.name(ch, "") or ch in "‽⁈⁉")


def asks(sentence: str) -> bool:
    """Whether a sentence ends as a question does, closing marks after its last mark aside."""
    s = sentence.rstrip()
    while s and _closing(s[-1]):
        s = s[:-1].rstrip()
    return bool(s) and s[-1] in QUESTION_MARKS


def _closing(ch: str) -> bool:
    """A mark that may follow a sentence's last mark and still belong to it: a closing quotation mark or bracket."""
    return ch in QUOTE_MARKS or unicodedata.category(ch) in ("Pe", "Pf")


def _wide(ch: str) -> bool:
    """A full-width mark, after which a sentence ends with no space, as in 。 and ？."""
    return unicodedata.east_asian_width(ch) in ("W", "F", "H")


def _opens(ch: str) -> bool:
    """Whether a sentence may start with `ch`: a letter that is not lowercase, so a capital in any script or a letter
    of a script without case, an opening quotation mark, an opening parenthesis, ¿, ¡ or the * of emphasis. A digit, a
    count's { and a citation's [ do not start one."""
    return unicodedata.category(ch) in ("Lu", "Lt", "Lo", "Lm") or ch in QUOTE_PAIRS or ch in "(¿¡*"


def sentence_spans(line: str) -> list[tuple[int, int]]:
    """Where each sentence of one line stands, as (start, end). A sentence ends after a sentence-ending mark, with
    any closing quotation marks after it (not a bracket: "(as one said.) Then" is one), where what follows is a space and then something a sentence may start with; after a
    full-width mark, such as 。, it ends with no space. It never ends inside a quotation, which may hold several
    sentences of its own, but may end with one whose words end the sentence: `He said "I agree." Then`."""
    inside, ends = [False] * len(line), set()
    for _, end, a, b in quotation_spans(line):
        for i in range(a, b):
            inside[i] = True
        if line[a:b].rstrip()[-1:] in TERMINALS and line[a:b].strip():
            ends.add(end - 1)
    out, start, i = [], 0, 0
    while i < len(line):
        if not (i in ends or (not inside[i] and line[i] in TERMINALS)):
            i += 1
            continue
        j = i + 1
        while j < len(line) and (line[j] in TERMINALS or line[j] in QUOTE_MARKS):
            j += 1
        k = j
        while k < len(line) and line[k] in " \t 　":
            k += 1
        spaced = k > j and k < len(line) and _opens(line[k])
        if spaced or (k == j < len(line) and i not in ends and _wide(line[i])):
            out.append((start, j))
            start = j
        i = j
    if line[start:].strip():
        out.append((start, len(line)))
    return out


def sentences(text: str) -> list[str]:
    """The sentences of `text`, line by line (`sentence_spans`), each without the spaces around it."""
    return [line[a:b].strip() for line in text.splitlines() for a, b in sentence_spans(line) if line[a:b].strip()]


#: The sentence-ending marks that neither ask nor exclaim, such as . 。 and ।, which a sentence drops when it is set
#: inside another.
STOPS = "".join(ch for ch in TERMINALS if ch not in QUESTION_MARKS and "EXCLAMATION" not in unicodedata.name(ch, ""))


@cache
def after_marks() -> re.Pattern:
    """Where text may be cut after a sentence-ending mark, whatever follows: the spaces after one, or the point after a
    full-width one, which needs no space. Unlike `sentence_spans` it reads no quotation and no capital, so it cuts
    after "e.g." too: for a cut that need only be near a sentence's end."""
    return re.compile(rf"(?<=[{re.escape(TERMINALS)}])\s+|(?<=[{re.escape(''.join(c for c in TERMINALS if _wide(c)))}])(?=\S)")


def cut_long(line: str, size: int) -> list[str]:
    """A line longer than `size` characters in pieces: after every sentence-ending mark (`after_marks`), and a piece
    still longer than `size`, in a script that ends sentences without marks, at its last space before `size`
    characters, or at `size` characters where it has none."""
    if len(line) <= size:
        return [line]
    out = []
    for piece in after_marks().split(line):
        while len(piece) > size:
            at = piece.rfind(" ", 0, size)
            at = at if at > 0 else size
            out.append(piece[:at])
            piece = piece[at:].lstrip(" ")
        out.append(piece)
    return out


#: How many words (`words_in`) a stretch must hold to be read as a sentence, rather than a fragment such as "Yes.",
#: "Partly." or a stray "e.g.".
SENTENCE_WORDS = 4
#: The letters, a wide character counting `WIDE_LETTERS`, at which a stretch without spaces is longer than any one
#: word, and the letters it then counts as a word: so a script written without spaces between its words, as Chinese
#: and Thai are, counts its words, while no word of a script set with spaces is long enough to count as two.
ONE_WORD, LETTERS_A_WORD, WIDE_LETTERS = 24, 6, 3


def words_in(text: str) -> int:
    """About how many words `text` holds, in any script. Each piece between spaces is one, or, where it holds more
    than any one word could (`ONE_WORD`), one for every `LETTERS_A_WORD`: of all its wide characters, which only a
    script such as Chinese or Japanese writes, and of each run of its other letters (`words`), so that a name, path or
    reference joined by punctuation, such as `{t_role[pupil,yes]}`, is short runs and counts as one."""
    n = 0
    for piece in text.split():
        wide = WIDE_LETTERS * sum(1 for ch in piece if ch.isalnum() and _wide(ch))
        runs = [len(w) for w in words(piece) if not any(_wide(ch) for ch in w)]
        n += max(1, sum(s // LETTERS_A_WORD for s in (wide, *runs) if s >= ONE_WORD))
    return n


@cache
def marks() -> str:
    """The combining marks, as the inside of a regular expression's character class, built once from Unicode's own
    categories."""
    ranges, start = [], None
    for cp in [*range(0x20000), *range(0xE0100, 0xE01F0), 0]:
        mark = cp and unicodedata.category(chr(cp))[0] == "M"
        if mark and start is None:
            start = cp
        elif not mark and start is not None:
            ranges.append(f"{re.escape(chr(start))}-{re.escape(chr(cp - 1))}" if cp - 1 > start else re.escape(chr(start)))
            start = None
    return "".join(ranges)


@cache
def word_pattern() -> str:
    """A regular expression for one character of a word in any script: a letter, a digit, or a combining mark, which
    Python's \\w leaves out, so that it would cut a Devanagari or Thai word at each vowel sign."""
    return r"(?:[^\W_]|[" + marks() + "])"


@cache
def letter_pattern() -> str:
    """A regular expression for one letter in any script, its combining marks included: a word's character
    (`word_pattern`) that is not a digit."""
    return r"(?:[^\W\d_]|[" + marks() + "])"


@cache
def word_re() -> re.Pattern:
    """A word in any script: a run of letters, digits and combining marks (`word_pattern`)."""
    return re.compile(word_pattern() + "+")


def words(text: str) -> list[str]:
    """The words of `text`, in any script that separates them; a script that does not, such as Chinese, gives a whole
    run of its characters as one."""
    return word_re().findall(text)


def slug(text: str, most: int | None = None) -> str:
    """`text` as a name to link or file by: its words (`words`), lowercased in Unicode's way and joined by hyphens,
    apostrophes dropped, so that a title in any script keeps a name of its own. The first `most` words where given."""
    w = words(unicodedata.normalize("NFC", re.sub(r"['’]", "", str(text or ""))).casefold())
    return "-".join(w[:most] if most else w)
