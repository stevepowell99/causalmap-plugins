"""Keep the list of every question Rubicon has answered on this computer, across all the folders it answered from.

    python register.py <report .html> [--data <plugin data folder>]
    python register.py --list --data <plugin data folder> --out <page .html>
    python register.py --find <folder> --data <plugin data folder>

Each documents folder already keeps its own record of the runs answered from it, `rubicon-runs.md` beside `corpus/`,
one line per handed-over report linking its report, Word copy and zip. The register is only the list of those folders,
`folders.txt` in the plugin's own data folder (`${CLAUDE_PLUGIN_DATA}`), so nothing about a run is kept twice: what a
run asked, when, and its fingerprint are read from its zip whenever the list is drawn.

Given a handed-over report, this writes its line in `rubicon-runs.md`, creating the file where it is missing, and adds
the documents folder to the register. It refuses a report whose zip is missing, broken, or not the zip the report names.
`--list` draws every listed folder's runs as one page, newest first, saying of each folder and file whether it is still
where the record says. `--find` searches a folder for `rubicon-runs.md` files and adds the folders holding them, which
rebuilds the register where the plugin's data folder was lost. Makes no model call. Standard library only.
"""
import datetime, hashlib, html, json, os, re, sys, urllib.parse, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubicon_open.seal import seal_broken

RUNS = "rubicon-runs.md"
FOLDERS = "folders.txt"
REPORT = re.compile(r"\]\(([^)]+?-[0-9a-f]{8}\.html)\)")


def run_of(report):
    """What a report's zip says of the run: its question, date and fingerprint, or why it cannot be read."""
    zipped = report.with_suffix(".zip")
    if not zipped.is_file():
        return {"fault": "its zip is missing"}
    with zipfile.ZipFile(zipped) as z:
        broken = seal_broken(z)
        if broken:
            return {"fault": "its zip is not as it was made"}
        fingerprint = hashlib.sha256(z.read("SHA256SUMS")).hexdigest()
        workflow = json.loads(z.read("workflow.json").decode("utf-8"))
        render = json.loads(z.read("render.json").decode("utf-8"))
    if not report.stem.endswith(fingerprint[:8]):
        return {"fault": "its zip is not the one the report names"}
    # The day in the files' own name, which code wrote when it drew them, rather than the date given to print
    m = re.search(r"\d{4}-\d{2}-\d{2}", report.stem)
    day = datetime.date.fromisoformat(m.group(0)) if m else datetime.date.min
    return {"question": workflow.get("question_as_agreed", "").strip(), "day": day,
            "date": f"{day.day} {day:%B %Y}" if m else "", "fingerprint": fingerprint, "revision": "-revision-" in report.stem}


def folders(data):
    p = data / FOLDERS
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


def remember(data, *documents):
    """Add documents folders to the register, each once, and say which were new."""
    known = folders(data)
    new = [str(d.resolve()) for d in documents if str(d.resolve()) not in known]
    if new:
        data.mkdir(parents=True, exist_ok=True)
        (data / FOLDERS).write_text("".join(f"{f}\n" for f in known + new), encoding="utf-8")
    return new


def add(report, data):
    report = report.resolve()
    run = run_of(report)
    if "fault" in run:
        sys.exit(f"{report.name} is not listed: {run['fault']}.")
    run_folder = report.parent
    documents = run_folder.parent  # the folder holding corpus/, as render_report.py takes it
    runs = documents / RUNS
    text = runs.read_text(encoding="utf-8") if runs.is_file() else "# Rubicon runs\n\n"
    rel = report.relative_to(documents).as_posix()
    if f"]({urllib.parse.quote(rel)})" not in text:
        q = " ".join(run["question"].split())
        link = lambda kind, label: f"[{label}]({urllib.parse.quote(report.with_suffix(kind).relative_to(documents).as_posix())})"
        text = text.rstrip("\n") + ("\n" if "\n- " in text else "\n\n") + (f"- {run['date']}: {q} {link('.html', 'report')}, {link('.doc', 'Word')}, "
                                           f"{link('.zip', 'zip')}, fingerprint {run['fingerprint'][:8]}\n")
        runs.write_text(text, encoding="utf-8")
    print(f"listed {report.name} in {runs}")
    if not data:
        print("No plugin data folder was given, so the folder is not added to the list of every folder Rubicon has "
              "answered from on this computer.")
        return
    new = remember(data, documents)
    print(f"{documents} {'added to' if new else 'already in'} the register, {data / FOLDERS}")


def find(root, data):
    root = root.resolve()
    found, searched = [], 0
    for here, dirs, files in os.walk(root):
        searched += 1
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "corpus", "recount", "coded")]
        if RUNS in files:
            found.append(Path(here))
    new = remember(data, *found)
    print(f"searched {searched} folders under {root}; {len(found)} hold {RUNS}, {len(new)} of them new to the register")
    for f in new:
        print(f"  added {f}")


def n(k, noun):
    return f"{k} {noun}{'' if k == 1 else 's'}"


def file_url(p):
    return Path(p).as_uri()


def page(data):
    """Every listed folder's runs, as one page."""
    rows, lost = [], []
    for f in folders(data):
        documents = Path(f)
        runs = documents / RUNS
        if not runs.is_file():
            lost.append(f)
            continue
        for line in runs.read_text(encoding="utf-8").splitlines():
            for rel in REPORT.findall(line):
                report = documents / urllib.parse.unquote(rel)
                run = run_of(report) if report.is_file() else {"fault": "the report is no longer there"}
                rows.append((documents, report, run))
    rows.sort(key=lambda r: r[2].get("day", datetime.date.min), reverse=True)
    esc = html.escape
    body = []
    for documents, report, run in rows:
        ask = urllib.parse.quote(f"About my Rubicon run in {report.parent.name}: ")
        continue_in = (f'<a href="claude://cowork/new?folder={urllib.parse.quote(str(documents))}&amp;q={ask}">Cowork</a> '
                       f'<a href="claude://code/new?folder={urllib.parse.quote(str(documents))}&amp;q={ask}">Claude Code</a>')
        if "fault" in run:
            what = f'<span class="fault">{esc(report.name)}: {esc(run["fault"])}</span>'
            files = ""
        else:
            what = esc(run["question"]) + (' <span class="small">(revision)</span>' if run["revision"] else "")
            files = (f'<a href="{file_url(report)}">report</a> <a href="{file_url(report.with_suffix(".doc"))}">Word</a> '
                     f'<a href="{file_url(report.with_suffix(".zip"))}">zip</a> '
                     f'<span class="small fp">{run["fingerprint"][:8]}</span>')
        body.append(f'<tr><td>{esc(run.get("date", ""))}</td><td>{what}</td><td>{files}</td>'
                    f'<td class="small">{esc(str(documents))}</td><td>{continue_in}</td></tr>')
    missing = "".join(f"<li>{esc(f)}</li>" for f in lost)
    return ("<!doctype html><html lang=\"en-GB\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\"><title>Rubicon runs</title><style>"
            "body{font-family:Georgia,serif;color:#17130f;background:#fffdf9;margin:24px 16px;max-width:1100px}"
            "h1{font-weight:normal;color:#8c1912}table{border-collapse:collapse;width:100%}"
            "td,th{border-bottom:1px solid #e4dcd0;padding:6px 8px;text-align:left;vertical-align:top}"
            "th{font-weight:normal;color:#8b7f72;font-size:.85em}.small{font-size:.85em;color:#8b7f72}"
            ".fp{font-family:monospace}.fault{color:#8c1912}a{color:#1d5c3a;margin-right:.5em}"
            ".wrap{overflow-x:auto}</style></head><body><p class=\"small\">RUBICON</p><h1>Rubicon runs</h1>"
            f"<p>Every question Rubicon has answered on this computer, newest first: {n(len(rows), 'report')} from "
            f"{n(len(folders(data)), 'documents folder')}.</p>"
            + (f"<p class=\"fault\">These folders are no longer where the list says:</p><ul>{missing}</ul>" if lost else "")
            + "<div class=\"wrap\"><table><tr><th>Date</th><th>Question</th><th>Files</th><th>Documents folder</th>"
              "<th>Continue in</th></tr>" + "".join(body) + "</table></div></body></html>\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    opt = lambda k: args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else None
    data = Path(opt("--data")) if opt("--data") and "${" not in opt("--data") else None
    if "--list" in args:
        if not data or not opt("--out"):
            sys.exit(__doc__.split("\n\n")[1])
        out = Path(opt("--out"))
        out.write_text(page(data), encoding="utf-8")
        print(f"wrote {out}: {len(folders(data))} documents folders listed in {data / FOLDERS}")
    elif "--find" in args:
        if not data or not opt("--find"):
            sys.exit(__doc__.split("\n\n")[1])
        find(Path(opt("--find")), data)
    elif args and not args[0].startswith("--"):
        add(Path(args[0]), data)
    else:
        sys.exit(__doc__.split("\n\n")[1])
