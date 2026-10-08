"""Say whether a Rubicon report was drawn from a given run's zip, and stop at the first thing that says it was not.

    python verify.py <report .html or .doc> <run .zip>

A PDF or other converted copy is not read: it carries the same file name and prints the same fingerprint, which a
reader compares by eye, and its .html or .doc is what this checks.

Four checks, in order, each of which the next relies on:

1. The zip is as it was made: every file in it matches its own `SHA256SUMS`, and nothing is added or missing.
2. The report names this zip: the fingerprint printed in the report is the SHA-256 of the zip's `SHA256SUMS`.
3. This is the engine that drew the report: the zip records the engine's own fingerprint and its version. Where it
   differs, the report cannot be compared word for word here, and the answer says which version to check it with.
4. The report is what the zip draws: the zip is laid out in a scratch folder, recounted from its coded passages and its
   answer (a recount that would change anything stops there), drawn again under the name and date it recorded, and the
   new report compared with the given one byte for byte.

Exit status 0 means all four held; 1 means the report and zip do not match, and says where; 2 means the zip is the one
the report names but was drawn by another version of the engine. Makes no model call.
"""
import hashlib, json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
from rubicon_open.seal import engine_fingerprint, seal_broken


def verdict(report, zipped):
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
        if broken:
            return 1, f"NO MATCH: {zipped.name} is not as it was made: " + "; ".join(broken) + "."
        fingerprint = hashlib.sha256(z.read("SHA256SUMS")).hexdigest()
        render = json.loads(z.read("render.json").decode("utf-8"))
    if report.suffix.lower() not in (".html", ".doc"):
        return 1, (f"CANNOT CHECK: verify.py reads a report's .html or .doc. A {report.suffix} copy is tied to its zip by "
                   "its file name and by the fingerprint printed under How this was made, which a reader compares by eye; "
                   "check the .html or .doc it was converted from instead.")
    named = re.findall(r'class="fingerprint">([0-9a-f]{64})<', report.read_text(encoding="utf-8", errors="replace"))
    if not named:
        return 1, f"NO MATCH: {report.name} carries no fingerprint, so it names no zip."
    if set(named) != {fingerprint}:
        return 1, (f"NO MATCH: {report.name} names the zip {named[0]}, and {zipped.name} is {fingerprint}. The report "
                   "was drawn from another zip, or one of the two has been changed.")
    if render.get("engine") != engine_fingerprint(ENGINE):
        return 2, (f"SAME ZIP, OTHER ENGINE: {zipped.name} is the zip {report.name} names, untouched, but it was drawn "
                   f"by Rubicon {render.get('version') or 'of another version'}, not by this engine. Check it with that "
                   "version's verify.py to compare the report word for word.")
    with tempfile.TemporaryDirectory() as t:
        copy = Path(t) / zipped.name
        shutil.copy2(zipped, copy)
        done = subprocess.run([sys.executable, "-I", "-S", str(ENGINE / "render_report.py"), str(copy)],
                              capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            return 1, f"NO MATCH: the zip does not draw a report: {done.stderr.strip()}"
        drawn = copy.with_suffix("") / f"{render['name']}-{fingerprint[:8]}{report.suffix}"
        if not drawn.is_file():
            return 1, f"NO MATCH: the zip draws no {report.suffix} file."
        a, b = report.read_bytes(), drawn.read_bytes()
        if a != b:
            line = next((i for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1) if x != y),
                        min(len(a.splitlines()), len(b.splitlines())) + 1)
            return 1, (f"NO MATCH: {report.name} names this zip, but is not the report the zip draws: they first "
                       f"differ at line {line}, so the report has been changed since it was drawn.")
    return 0, (f"MATCH: {report.name} was drawn from {zipped.name}, fingerprint {fingerprint}, by this engine. Every "
               "file in the zip is as it was made, every number recounts from its coded passages, and the zip draws "
               "this report byte for byte.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__.split("\n\n")[1])
    code, said = verdict(Path(sys.argv[1]), Path(sys.argv[2]))
    print(said)
    sys.exit(code)
