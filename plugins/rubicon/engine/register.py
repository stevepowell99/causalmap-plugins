"""Keep the list of every question Rubicon has answered on this computer, across all the folders it answered from.

    python register.py <report .html> [--data <plugin data folder>]
    python register.py --list --out <page .html> [--folder <this documents folder>] [--data <plugin data folder>]
    python register.py --find <folder> --data <plugin data folder>

Each documents folder already keeps its own record of the runs answered from it, `rubicon-runs.md` beside `corpus/`,
one line per handed-over report linking its report, Word copy and zip. The register is only the list of those folders,
`folders.txt` in the plugin's own data folder (`${CLAUDE_PLUGIN_DATA}`), so nothing about a run is kept twice: what a
run asked, when, and its fingerprint are read from its zip whenever the list is drawn.

Given a handed-over report, this writes its line in `rubicon-runs.md`, creating the file where it is missing, and adds
the documents folder to the register. It refuses a report whose zip is missing, broken, or not the zip the report names.
`--list` draws Rubicon Central: one page listing every run of every listed folder, whether its `rubicon-runs.md` links
it or it only lies in one of the folder's run folders, with each report carried inside it, so choosing a run shows its report beside the list and the page needs no link to any other file. `--folder` adds the folder this chat has open, so the page shows its runs even where the plugin
data folder was lost. `--find` searches a folder for `rubicon-runs.md` files and run folders and adds the documents folders holding them, which
rebuilds the register where the plugin's data folder was lost. Makes no model call. Standard library only.
"""
import datetime, hashlib, html, json, os, re, sys, urllib.parse, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubicon_open.seal import seal_broken

RUNS = "rubicon-runs.md"
FOLDERS = "folders.txt"
REPORT = re.compile(r"\]\(([^)]+?\.html)\)")
SEALED = re.compile(r"-[0-9a-f]{8}$")


def run_of(report):
    """What a report's zip says of the run: its question, date and fingerprint, or why it cannot be read. A report
    whose name carries no fingerprint was drawn before reports were sealed to their zip: it is read for its question
    and date and marked `unsealed`, since there is no seal to check it against."""
    zipped = report.with_suffix(".zip")
    if not SEALED.search(report.stem):
        return unsealed(report)
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


def unsealed(report):
    """What can be read of a report drawn before reports were sealed: the question from its zip where the zip holds
    one, otherwise the report's own title, and the day in its name."""
    question = ""
    try:
        with zipfile.ZipFile(report.with_suffix(".zip")) as z:
            question = json.loads(z.read("workflow.json").decode("utf-8")).get("question_as_agreed", "").strip()
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        pass
    if not question:
        m = re.search(r"<title>(.*?)</title>", report.read_text(encoding="utf-8", errors="replace"), re.S)
        question = html.unescape(m.group(1)).strip() if m else report.stem
    m = re.search(r"\d{4}-\d{2}-\d{2}", report.stem)
    day = datetime.date.fromisoformat(m.group(0)) if m else datetime.date.fromtimestamp(report.stat().st_mtime)
    return {"question": question, "day": day, "date": f"{day.day} {day:%B %Y}", "revision": "-revision-" in report.stem,
            "unsealed": "drawn before reports were sealed to their zip, so not checked against it"}


def folders(data):
    p = data / FOLDERS
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


def remember(data, *documents):
    """Add documents folders to the register, each once, and say which were new."""
    known = folders(data)
    new = [str(d.resolve()) for d in documents if str(d.resolve()) not in known]
    if new:
        data.mkdir(parents=True, exist_ok=True)
        (data / FOLDERS).write_text("".join(f"{f}\n" for f in known + new), encoding="utf-8", newline="\n")
    return new


def add(report, data):
    report = report.resolve()
    run = run_of(report)
    if "fault" in run or "unsealed" in run:
        sys.exit(f"{report.name} is not listed: {run.get('fault') or run['unsealed']}.")
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
        runs.write_text(text, encoding="utf-8", newline="\n")
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
        if "workflow.json" in files:  # a run folder, whose documents folder is the one above it; nothing below it is another
            found.append(Path(here).parent)
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("node_modules", "appdata")]
        if RUNS in files:
            found.append(Path(here))
    found = [f for f in dict.fromkeys(found) if runs_in(f)]  # a folder that holds no report adds nothing to the page
    new = remember(data, *found)
    print(f"searched {searched} folders under {root}; {len(found)} hold Rubicon runs, {len(new)} of them new to the register")
    for f in new:
        print(f"  added {f}")


def n(k, noun):
    return f"{k} {noun}{'' if k == 1 else 's'}"


def runs_in(documents):
    """Every run of a documents folder, each as (report path, what its zip says): the reports its `rubicon-runs.md`
    links, and every report in its run folders (those holding a `workflow.json`), which a report drawn but never handed over, or a `rubicon-runs.md`
    written by hand, would otherwise leave out. A report is an .html beside a zip or Word copy of the same name."""
    runs = documents / RUNS
    linked = [documents / urllib.parse.unquote(rel) for rel in REPORT.findall(runs.read_text(encoding="utf-8"))] if runs.is_file() else []
    drawn = sorted(p for p in documents.glob("*/*.html") if (p.parent / "workflow.json").is_file()
                   and not p.name.endswith(".fragment.html") and (p.with_suffix(".zip").is_file() or p.with_suffix(".doc").is_file()))
    out = []
    for report in dict.fromkeys(linked + drawn):
        out.append((report, run_of(report) if report.is_file() else {"fault": "the report is no longer there"}))
    return out


def page(listed):
    """Rubicon Central: every run in the given documents folders on one page, each report carried inside it, so that
    choosing a run in the list shows its report beside the list with no link to follow. A folder this computer cannot
    read now is named with the reason, rather than left out."""
    esc = html.escape
    groups, reports, lost, empty = [], [], [], []
    for f in listed:
        documents = Path(f)
        if not documents.is_dir():
            lost.append(f)
            continue
        runs = sorted(runs_in(documents), key=lambda r: r[1].get("day", datetime.date.min), reverse=True)
        if not runs:
            empty.append(f)
            continue
        items = []
        for report, run in runs:
            if "fault" in run:
                items.append(f'<li class="gone">{esc(report.name)}<br><span class="small">{esc(run["fault"])}</span></li>')
                continue
            reports.append(report.read_text(encoding="utf-8"))
            items.append(f'<li><button data-i="{len(reports) - 1}"><span class="small">{esc(run["date"])}'
                         f'{" &middot; revision" if run["revision"] else ""}</span>{esc(run["question"])}'
                         + (f'<span class="small">{esc(run["unsealed"])}</span>' if "unsealed" in run else "")
                         + '</button></li>')
        groups.append(f'<h2>{esc(documents.name)}</h2><p class="small path">{esc(str(documents))}</p><ul>{"".join(items)}</ul>')
    total = len(reports)
    carried = json.dumps(reports, ensure_ascii=False).replace("</", "<\\/")
    missing = "".join(f"<li>{esc(f)}</li>" for f in lost)
    return ("<!doctype html><html lang=\"en-GB\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\"><title>Rubicon Central</title><style>"
            "*{box-sizing:border-box}html,body{height:100%;margin:0}"
            "body{font-family:Georgia,serif;color:#17130f;background:#fffdf9;display:flex}"
            "nav{width:300px;flex:none;overflow-y:auto;border-right:1px solid #e4dcd0;padding:16px}"
            "main{flex:1;min-width:0;display:flex}iframe{flex:1;border:0;width:100%;background:#fff}"
            "h1{font-weight:normal;color:#8c1912;font-size:1.4em;margin:0 0 4px}"
            "h2{font-weight:normal;font-size:1.05em;margin:18px 0 0}.small{font-size:.8em;color:#8b7f72}"
            ".path{margin:0 0 6px;overflow-wrap:anywhere}ul{list-style:none;padding:0;margin:0}"
            "button{display:block;width:100%;text-align:left;font:inherit;font-size:.92em;color:inherit;background:none;"
            "border:0;border-left:3px solid transparent;padding:6px 8px;cursor:pointer;line-height:1.3}"
            "button:hover{background:#f4eee5}button[aria-current]{border-left-color:#8c1912;background:#f4eee5}"
            "button .small{display:block}.gone{padding:6px 8px;color:#8b7f72;font-size:.85em;overflow-wrap:anywhere}"
            ".fault{color:#8c1912}.empty{padding:24px}"
            "@media (max-width:700px){body{display:block}nav{width:auto;border-right:0;border-bottom:1px solid #e4dcd0}"
            "main{height:100vh}}</style></head><body><nav><p class=\"small\">RUBICON</p><h1>Rubicon Central</h1>"
            f"<p class=\"small\">{n(total, 'report')} from {n(len(groups), 'documents folder')}, newest first in each. "
            "Choose one to read it here.</p>"
            + (f"<p class=\"small fault\">Not reachable from here, so not shown:</p><ul class=\"small\">{missing}</ul>" if lost else "")
            + "".join(groups)
            + (f"<p class=\"small path\">No report in {', '.join(esc(f) for f in empty)}.</p>" if empty else "")
            + "</nav><main>"
            + ("<iframe title=\"Report\" id=\"report\"></iframe>" if total else
               ("<p class=\"empty\">No report found in " + ("these folders" if groups else "any folder: Rubicon has no folder on its list here, and none was given") + ".</p>"))
            + "</main><script type=\"application/json\" id=\"reports\">" + carried + "</script><script>"
              "const R=JSON.parse(document.getElementById('reports').textContent),f=document.getElementById('report'),"
              "b=[...document.querySelectorAll('button[data-i]')];"
              "function show(x,go){b.forEach(y=>y.removeAttribute('aria-current'));x.setAttribute('aria-current','true');"
              "f.srcdoc=R[+x.dataset.i];if(go&&innerWidth<=700)f.scrollIntoView();}"
              "b.forEach(x=>x.addEventListener('click',()=>show(x,true)));if(b.length)show(b[0]);"
              "</script></body></html>\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    opt = lambda k: args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else None
    data = Path(opt("--data")) if opt("--data") and "${" not in opt("--data") else None
    if "--list" in args:
        if not opt("--out"):
            sys.exit(__doc__.split("\n\n")[1])
        here = [Path(opt("--folder")).resolve()] if opt("--folder") else []
        if data and here:
            remember(data, *here)
        listed = list(dict.fromkeys((folders(data) if data else []) + [str(h) for h in here]))
        out = Path(opt("--out"))
        out.write_text(page(listed), encoding="utf-8", newline="\n")
        print(f"wrote {out}: {n(len(listed), 'documents folder')}"
              + (f", from {data / FOLDERS}" if data else ", with no plugin data folder, so only the folder given"))
    elif "--find" in args:
        if not data or not opt("--find"):
            sys.exit(__doc__.split("\n\n")[1])
        find(Path(opt("--find")), data)
    elif args and not args[0].startswith("--"):
        add(Path(args[0]), data)
    else:
        sys.exit(__doc__.split("\n\n")[1])
