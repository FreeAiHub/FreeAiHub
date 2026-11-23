"""Fill the STATS block of README.md with live facts about the featured repositories."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
OWNER = "FreeAiHub"
START, END = "<!-- STATS:START -->", "<!-- STATS:END -->"
FEATURED_ROW = re.compile(rf"^\| \[([\w.-]+)\]\(https://github\.com/{OWNER}/\1\)", re.M)


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "FreeAiHub-profile-stats")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def ci_status(repo, branch):
    runs = api(f"/repos/{OWNER}/{repo}/actions/runs?branch={branch}&per_page=1")["workflow_runs"]
    if not runs:
        return "no CI"
    run = runs[0]
    result = run["conclusion"] or run["status"]
    return f"[{result}]({run['html_url']})"


def repo_row(repo):
    meta = api(f"/repos/{OWNER}/{repo}")
    languages = ", ".join(list(api(f"/repos/{OWNER}/{repo}/languages"))[:3]) or "—"
    return (
        f"| [{repo}]({meta['html_url']}) | {meta['pushed_at'][:10]} "
        f"| {ci_status(repo, meta['default_branch'])} | {languages} |"
    )


def render(repos):
    lines = [
        "### Live status",
        "",
        "| Repository | Last push | Latest CI run | Languages |",
        "|---|---|---|---|",
        *(repo_row(r) for r in repos),
        "",
        "_Updated daily by [a workflow](.github/workflows/update-stats.yml) from the GitHub API._",
    ]
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    repos = FEATURED_ROW.findall(text.split(START, 1)[0])
    if not repos:
        sys.exit("No featured repositories found in README.md")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(f"{before}{START}\n{render(repos)}\n{END}{after}", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as err:
        sys.exit(f"GitHub API error: {err.code} {err.reason}")
