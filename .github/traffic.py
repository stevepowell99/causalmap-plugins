"""Save GitHub's daily clone and view counts for the marketplace repo, which GitHub keeps for 14 days only.

    python .github/traffic.py --save          in the Action: merge the last 14 days into the `traffic` branch
    python .github/traffic.py --print <dir>   anywhere: write the merged files into <dir>, writing nothing to GitHub

Reads `traffic/clones` and `traffic/views` with TRAFFIC_TOKEN (a token that can read the repo's traffic) and, with
`--save`, writes `clones.csv` and `views.csv` on the `traffic` branch through the contents API with GITHUB_TOKEN, so the
job clones nothing and adds no clone of its own. A day GitHub still reports is updated from it, since the latest day is
partial; a day it no longer reports is kept as saved. The repo is GITHUB_REPOSITORY, or stevepowell99/causalmap-plugins.
Standard library only.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "stevepowell99/causalmap-plugins")
BRANCH = "traffic"
#: Each file: the traffic endpoint it is read from, the list in the reply, its two count columns, and what it counts
KINDS = {"clones.csv": ("clones", "clones", "unique_cloners", "clone counts"),
         "views.csv": ("views", "views", "unique_visitors", "page view counts")}
HEAD = ("# GitHub's daily {what} for {repo}, saved once a day by .github/workflows/traffic.yml, since GitHub keeps only the "
        "last 14 days. Each install or update of a plugin from this marketplace is a clone. Our own release, test and "
        "bench runs clone too, so the counts overstate outside use. A day is updated while GitHub still reports it, so "
        "the latest day may be partial. Dates are UTC.\n")


def api(method: str, path: str, token: str, body: dict | None = None) -> dict | None:
    """One GitHub API call; None where the thing asked for does not exist (404)."""
    req = urllib.request.Request(f"https://api.github.com/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise SystemExit(f"{method} {path}: {e.code} {e.read().decode(errors='replace')[:300]}")


def parse(text: str) -> dict[str, tuple[int, int]]:
    rows = {}
    for line in text.splitlines():
        if line and not line.startswith("#") and not line.startswith("date,"):
            day, n, u = line.split(",")
            rows[day] = (int(n), int(u))
    return rows


def merge(saved: dict[str, tuple[int, int]], days: list[dict]) -> dict[str, tuple[int, int]]:
    """The saved days with every day GitHub reports put in as it reports it now."""
    return {**saved, **{d["timestamp"][:10]: (int(d["count"]), int(d["uniques"])) for d in days}}


def render(name: str, rows: dict[str, tuple[int, int]]) -> str:
    _, what, unique, label = KINDS[name]
    out = HEAD.format(what=label, repo=REPO) + f"date,{what},{unique}\n"
    return out + "".join(f"{d},{n},{u}\n" for d, (n, u) in sorted(rows.items()))


def fresh(token: str) -> dict[str, list[dict]]:
    """The last 14 days of each kind; refuses a reply without its list, so a failed read never saves as no traffic."""
    out = {}
    for name, (endpoint, key, *_) in KINDS.items():
        got = api("GET", f"repos/{REPO}/traffic/{endpoint}", token)
        if not got or key not in got:
            raise SystemExit(f"traffic/{endpoint} gave no '{key}': {got}")
        out[name] = got[key]
    return out


def ensure_branch(token: str) -> None:
    """The `traffic` branch, made with a commit of its own and no parent where it does not exist yet, so it holds the
    counts alone."""
    if api("GET", f"repos/{REPO}/git/ref/heads/{BRANCH}", token):
        return
    tree = api("POST", f"repos/{REPO}/git/trees", token, {"tree": [{"path": "README.md", "mode": "100644", "type": "blob",
               "content": "Daily clone and view counts for this repo, saved by .github/workflows/traffic.yml on the "
                          "default branch. Counts only: GitHub's traffic API holds nothing about who cloned.\n"}]})
    commit = api("POST", f"repos/{REPO}/git/commits", token, {"message": "Traffic counts", "tree": tree["sha"], "parents": []})
    api("POST", f"repos/{REPO}/git/refs", token, {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})


def save(read_token: str, write_token: str) -> None:
    got = fresh(read_token)
    ensure_branch(write_token)
    for name, days in got.items():
        stored = api("GET", f"repos/{REPO}/contents/{name}?ref={BRANCH}", write_token)
        before = base64.b64decode(stored["content"]).decode() if stored else ""
        text = render(name, merge(parse(before), days))
        if text == before:
            print(f"{name}: unchanged, {len(parse(text))} days saved")
            continue
        api("PUT", f"repos/{REPO}/contents/{name}", write_token, {
            "message": f"{name}: GitHub's counts to {max(parse(text))}", "branch": BRANCH,
            "content": base64.b64encode(text.encode()).decode(), **({"sha": stored["sha"]} if stored else {})})
        print(f"{name}: {len(days)} days from GitHub, {len(parse(text))} days saved, to {max(parse(text))}")


def print_to(folder: Path, read_token: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, days in fresh(read_token).items():
        f = folder / name
        text = render(name, merge(parse(f.read_text(encoding="utf-8")) if f.is_file() else {}, days))
        f.write_text(text, encoding="utf-8", newline="\n")
        print(f"{f}: {len(parse(text))} days, to {max(parse(text))}")


if __name__ == "__main__":
    read = os.environ.get("TRAFFIC_TOKEN") or sys.exit("TRAFFIC_TOKEN is not set: a token that can read this repo's traffic")
    if sys.argv[1:2] == ["--save"]:
        save(read, os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set"))
    elif sys.argv[1:2] == ["--print"] and len(sys.argv) == 3:
        print_to(Path(sys.argv[2]), read)
    else:
        sys.exit(__doc__)
