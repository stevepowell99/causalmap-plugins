"""The seal that ties a run's zip to its report: what a zip lists of itself, and which engine drew a report.

A run's zip holds `SHA256SUMS`, the SHA-256 of every other file in it in the form `sha256sum -c` reads, and the SHA-256
of that list is the run's fingerprint, which the report prints. `render_report.py` makes the seal and `verify.py` reads it.
"""
import hashlib

from rubicon_open.corpus import as_read


def engine_fingerprint(engine):
    """The SHA-256 of every file of the engine in the folder `engine`, so a zip records exactly which code drew its
    report. Each file is read with its line endings made one newline (`as_read`, the open format's one rule), and the
    files are taken in the order of their relative paths as strings, so the same commit gives the same fingerprint from
    a Windows checkout, which writes CRLF and sorts paths ignoring case, and from any other."""
    h = hashlib.sha256()
    for p in sorted(engine.rglob("*"), key=lambda p: p.relative_to(engine).as_posix()):
        if p.is_file() and "__pycache__" not in p.parts:
            # surrogateescape carries any byte that is not UTF-8 through unchanged, so only line endings are touched
            body = as_read(p.read_bytes().decode("utf-8", "surrogateescape")).encode("utf-8", "surrogateescape")
            h.update(p.relative_to(engine).as_posix().encode() + b"\0" + body + b"\0")
    return h.hexdigest()


def engine_version(engine):
    """The plugin's version, which `rubicon/plugin/build.py` writes into the engine as `VERSION`, or None in the repo."""
    p = engine / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


def seal_broken(z):
    """What in an opened zip no longer matches its own `SHA256SUMS`; empty means nothing in it has changed since it
    was made, nothing has been added and nothing taken away."""
    names = set(z.namelist()) - {"SHA256SUMS"}
    if "SHA256SUMS" not in z.namelist():
        return ["it holds no SHA256SUMS, so it was made before a run's zip was sealed"]
    listed = {n: h for n, h in sums(z)}
    return ([f"{n} is in the zip but not in its SHA256SUMS" for n in sorted(names - listed.keys())]
            + [f"{n} is in its SHA256SUMS but not in the zip" for n in sorted(listed.keys() - names)]
            + [f"{n} has changed since the zip was made" for n in sorted(names & listed.keys())
               if hashlib.sha256(z.read(n)).hexdigest() != listed[n]])


def sums(z):
    """The (name, SHA-256) pairs a zip's `SHA256SUMS` lists, in its order."""
    return [tuple(reversed(l.split("  ", 1))) for l in z.read("SHA256SUMS").decode("utf-8").splitlines() if l]


def listed(z):
    """The names of a sealed zip's files, in the order its seal lists them."""
    return [n for n, _ in sums(z)]
