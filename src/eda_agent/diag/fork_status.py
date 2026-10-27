# SPDX-License-Identifier: Apache-2.0
"""Report exact Git synchronization points for an eda-agent fork.

The report is read-only unless ``fetch`` is requested. A fork can have
independently ported features, so commit counts are Git history counts,
never a count of missing capabilities.
"""

from __future__ import annotations

import subprocess
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=60, check=False,
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip()
                           or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _github_repo(url: str) -> str:
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url.strip(), re.I)
    if not match:
        raise ValueError(f"not a GitHub remote: {url}")
    return f"{match.group(1)}/{match.group(2)}"


def _github_forks(repo: str) -> list[dict[str, Any]]:
    """Fetch every page of GitHub's default-branch fork inventory."""
    forks: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/forks?per_page=100&page={page}"
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "eda-agent-fork-status",
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise RuntimeError(f"GitHub returned no fork list for {repo}")
        forks.extend(batch)
        if len(batch) < 100:
            return forks
        page += 1


def verify_fork_tips(root: Path, *, max_workers: int = 10,
                     all_branches: bool = False) -> dict[str, Any]:
    """Read live default-branch tips of direct upstream and origin forks.

    This neither fetches commit history nor changes refs. A matching tip
    proves freshness of that cached branch, not feature equivalence.
    """
    root = Path(root).resolve()
    remote_names = _git(root, "remote").splitlines()
    remote_repos = {
        _github_repo(_git(root, "remote", "get-url", name)).casefold(): name
        for name in remote_names
    }
    parents = []
    for name in ("upstream", "origin"):
        if name not in remote_names:
            raise RuntimeError(f"{name} remote is required for fork-tip verification")
        parents.append(_github_repo(_git(root, "remote", "get-url", name)))
    cached = dict(line.split("\t", 1) for line in _git(
        root, "for-each-ref", "--format=%(refname:short)%09%(objectname)",
        "refs/remotes/forks", *(f"refs/remotes/{name}" for name in remote_names)
    ).splitlines())

    seen: set[str] = set()
    candidates = []
    for parent in parents:
        for fork in _github_forks(parent):
            full_name = fork["full_name"]
            if full_name.casefold() in seen:
                continue
            seen.add(full_name.casefold())
            candidates.append((parent, fork))

    def check(item: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        parent, fork = item
        branch = fork["default_branch"]
        owner = fork["owner"]["login"].casefold()
        name = fork["full_name"]
        configured = remote_repos.get(name.casefold())
        ref = f"{configured}/{branch}" if configured else f"forks/{owner}/{branch}"
        try:
            branch_spec = "refs/heads/*" if all_branches else f"refs/heads/{branch}"
            proc = subprocess.run(
                ["git", "ls-remote", fork["clone_url"], branch_spec],
                capture_output=True, text=True, timeout=25, check=False,
            )
            remote_branches = {
                line.split("\t", 1)[1].removeprefix("refs/heads/"): line.split("\t", 1)[0]
                for line in proc.stdout.splitlines() if "\trefs/heads/" in line
            } if proc.returncode == 0 else {}
            tip = remote_branches.get(branch, "")
            error = (proc.stderr or "branch not found").strip() if not tip else ""
        except (OSError, subprocess.TimeoutExpired) as exc:
            tip = ""
            error = str(exc)
            remote_branches = {}
        result = {"repo": name, "parent": parent, "branch": branch,
                  "ref": ref, "remote_tip": tip, "cached_tip": cached.get(ref)}
        result["fresh"] = bool(tip and tip == result["cached_tip"])
        if not tip:
            result["error"] = error
        if all_branches:
            result["branches"] = []
            for branch_name, branch_tip in sorted(remote_branches.items()):
                branch_ref = (f"{configured}/{branch_name}" if configured else
                              f"forks/{owner}/{branch_name}")
                result["branches"].append({
                    "branch": branch_name, "ref": branch_ref,
                    "remote_tip": branch_tip, "cached_tip": cached.get(branch_ref),
                    "fresh": branch_tip == cached.get(branch_ref),
                })
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        entries = list(pool.map(check, candidates))
    report = {"parents": parents, "checked": len(entries),
              "fresh": sum(entry["fresh"] for entry in entries),
              "forks": entries}
    if all_branches:
        rows = [branch for entry in entries for branch in entry["branches"]]
        report["checked_branches"] = len(rows)
        report["fresh_branches"] = sum(row["fresh"] for row in rows)
    return report


def fork_status(root: Path, *, remotes: tuple[str, ...] =
                ("origin", "upstream", "morembedded"),
                fetch: bool = False,
                cached_forks: bool = False) -> dict[str, Any]:
    """Return HEAD, each remote tip, all merge bases and ahead/behind counts."""
    root = Path(root).resolve()
    head = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "branch", "--show-current")
    configured = set(_git(root, "remote").splitlines())
    sources: dict[str, Any] = {}
    for remote in dict.fromkeys(remotes):
        if remote not in configured:
            sources[remote] = {"available": False, "reason": "remote not configured"}
            continue
        entry: dict[str, Any] = {"available": True, "refreshed": False}
        if fetch:
            try:
                _git(root, "fetch", "--no-tags", "--quiet", remote, "main")
                entry["refreshed"] = True
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                entry["fetch_error"] = str(exc)
        ref = f"{remote}/main"
        try:
            entry["tip"] = _git(root, "rev-parse", "--verify", ref)
            bases = _git(root, "merge-base", "--all", "HEAD", ref)
            entry["merge_bases"] = bases.splitlines()
            counts = _git(root, "rev-list", "--left-right", "--count",
                          f"HEAD...{ref}").split()
            entry["ahead"], entry["behind"] = map(int, counts)
            entry["tip_in_head"] = entry["tip"] == head or (
                entry["behind"] == 0)
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            entry["available"] = False
            entry["reason"] = str(exc)
        sources[remote] = entry
    report = {"root": str(root), "branch": branch, "head": head,
              "fetch_requested": fetch, "sources": sources}
    if cached_forks:
        refs = _git(root, "for-each-ref", "--format=%(refname:short)%09%(objectname)",
                    "refs/remotes/forks")
        forks: dict[str, Any] = {}
        for line in refs.splitlines():
            ref, tip = line.split("\t", 1)
            entry: dict[str, Any] = {"tip": tip}
            try:
                entry["merge_bases"] = _git(
                    root, "merge-base", "--all", "HEAD", ref).splitlines()
                counts = _git(root, "rev-list", "--left-right", "--count",
                              f"HEAD...{ref}").split()
                entry["ahead"], entry["behind"] = map(int, counts)
                entry["tip_in_head"] = entry["behind"] == 0
            except (RuntimeError, OSError, ValueError,
                    subprocess.TimeoutExpired) as exc:
                entry["reason"] = str(exc)
            forks[ref] = entry
        report["cached_forks"] = forks
        report["cached_forks_note"] = (
            "Local refs only; --fetch refreshes configured remotes, "
            "not refs/remotes/forks. Git divergence is not a missing-feature count.")
    return report


def format_fork_status(report: dict[str, Any]) -> str:
    lines = [f"{report['branch'] or '(detached)'} {report['head']}",
             f"remote data: {'fetched now' if report['fetch_requested'] else 'local refs (use --fetch to refresh)'}"]
    for name, item in report["sources"].items():
        if not item["available"]:
            lines.append(f"{name}: unavailable ({item['reason']})")
            continue
        bases = ", ".join(item["merge_bases"]) or "none"
        lines.append(f"{name}: {item['tip']}; ahead {item['ahead']}, behind {item['behind']}; merge-base {bases}")
        if item.get("fetch_error"):
            lines.append(f"  fetch failed: {item['fetch_error']}; counts use cached refs")
    if "cached_forks" in report:
        lines.append(f"cached fork branch refs: {len(report['cached_forks'])} "
                     "(local refs; not refreshed by --fetch)")
        for name, item in report["cached_forks"].items():
            if "reason" in item:
                lines.append(f"{name}: {item['tip']}; unavailable ({item['reason']})")
                continue
            bases = ", ".join(item["merge_bases"]) or "none"
            lines.append(f"{name}: {item['tip']}; ahead {item['ahead']}, "
                         f"behind {item['behind']}; merge-base {bases}")
    if "fork_tip_check" in report:
        check = report["fork_tip_check"]
        lines.append(f"live fork default branches: {check['fresh']}/{check['checked']} "
                     "match local refs")
        if "checked_branches" in check:
            lines.append(f"live fork branches: {check['fresh_branches']}/"
                         f"{check['checked_branches']} match local refs")
        for item in check["forks"]:
            if not item["fresh"]:
                lines.append(f"{item['repo']} {item['branch']}: "
                             f"remote {item['remote_tip'] or 'unavailable'}, "
                             f"local {item['cached_tip'] or 'missing'} "
                             f"({item['ref']})"
                             + (f"; {item['error']}" if item.get("error") else ""))
            for branch in item.get("branches", []):
                if not branch["fresh"] and branch["branch"] != item["branch"]:
                    lines.append(f"{item['repo']} {branch['branch']}: "
                                 f"remote {branch['remote_tip']}, "
                                 f"local {branch['cached_tip'] or 'missing'} "
                                 f"({branch['ref']})")
    return "\n".join(lines)
